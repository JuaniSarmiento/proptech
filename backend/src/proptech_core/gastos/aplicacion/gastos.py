"""El gasto del edificio (R12, R13, R16, D-075): alta, estados y aprobación.

Capa CRUD + reglas propias del gasto; permisos (403) y alcance (404, D7)
viven en el router de `proptech_api`, igual que en `proveedores.py`.
"""

from collections.abc import Callable
from datetime import date
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.eventos import EventoDelGasto
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.complejos.aplicacion.lectura import (
    cargar_categoria,
    cargar_complejo,
    cargar_grupo,
    listar_categorias_obligatorias,
)
from proptech_core.gastos.aplicacion.errores import (
    EntradaInvalida,
    NoEncontrado,
    error_de_validacion,
    transaccion,
)
from proptech_core.gastos.aplicacion.proveedores import cargar_proveedor
from proptech_core.gastos.dominio.gasto import CAMPOS_DE_FACTURA, DatosGasto

#: D8: hasta que exista `liquidacion` (change 7), ningún período puede estar
#: emitido — no hay módulo que lo declare todavía. El puerto real llega con
#: ese change; hasta entonces este default no reabre nada porque nada se
#: cierra nunca (mismo patrón D6 que el lector de planillas: el caso de uso
#: no conoce a quien implementa el puerto).
PeriodoEmitidoFn = Callable[[Session, UUID, date], bool]


def _nada_esta_emitido_todavia(_sesion: Session, _complejo_id: UUID, _periodo: date) -> bool:
    return False


def _primer_dia_del_mes_siguiente(periodo: date) -> date:
    if periodo.month == 12:
        return date(periodo.year + 1, 1, 1)
    return date(periodo.year, periodo.month + 1, 1)


def _primer_periodo_no_emitido(
    sesion: Session, complejo_id: UUID, periodo: date, es_periodo_emitido: PeriodoEmitidoFn
) -> date:
    candidato = periodo
    while es_periodo_emitido(sesion, complejo_id, candidato):
        candidato = _primer_dia_del_mes_siguiente(candidato)
    return candidato


_CONFLICTOS = {"uq_gasto_factura": "factura"}
_ESTADOS_EDITABLES = ("borrador", "sin_ia", "en_revision")
_CAMPOS_BLOQUEADOS_SI_APROBADO = (
    "concepto",
    "categoria_id",
    "grupo_id",
    "periodo",
    "tipo",
    "importe",
    "proveedor_id",
    *CAMPOS_DE_FACTURA,
    "documento_receptor",
)


def _aviso_de_receptor_distinto(
    sesion: Session, complejo_id: UUID, documento_receptor: str | None
) -> str | None:
    """Tarea 3.10: si `complejo.cuit` no tiene valor, no hay nada contra qué
    comparar y no se muestra aviso (ni bloquea, D-019/D-061/D-082: el aviso
    de R12 nunca es bloqueante). Comparación textual simple; no asume
    formato CUIT en `documento_receptor` (texto libre, D7 del design)."""
    if documento_receptor is None:
        return None
    complejo = cargar_complejo(sesion, complejo_id)
    if complejo is None or complejo.cuit is None:
        return None
    if documento_receptor == complejo.cuit:
        return None
    return (
        f"el documento del receptor informado ({documento_receptor}) no coincide "
        f"con el del edificio ({complejo.cuit})"
    )


def _validar_pertenencia(sesion: Session, entrada: DatosGasto, complejo_id: UUID) -> None:
    categoria = cargar_categoria(sesion, entrada.categoria_id)
    if categoria is None or categoria["complejo_id"] != complejo_id:
        raise EntradaInvalida("categoria_id", "no pertenece a este edificio")
    grupo = cargar_grupo(sesion, entrada.grupo_id)
    if grupo is None or grupo["complejo_id"] != complejo_id:
        raise EntradaInvalida("grupo_id", "no pertenece a este edificio")
    if not grupo["activo"]:
        raise EntradaInvalida("grupo_id", "el grupo de reparto está desactivado")
    if entrada.proveedor_id is not None:
        proveedor = cargar_proveedor(sesion, entrada.proveedor_id)
        if proveedor is None or proveedor["complejo_id"] != complejo_id:
            raise EntradaInvalida("proveedor_id", "no pertenece a este edificio")


_COLUMNAS_GASTO = (
    "id, complejo_id, proveedor_id, categoria_id, grupo_id, concepto, "
    "periodo, periodo_de_imputacion, tipo, importe::text AS importe, estado, "
    "cuit_emisor, punto_de_venta, tipo_de_comprobante, numero_de_comprobante, "
    "documento_receptor"
)


_SENTENCIA_LISTAR_GASTOS = (
    f"SELECT {_COLUMNAS_GASTO} FROM gasto WHERE complejo_id=:id ORDER BY periodo DESC"  # noqa: S608
)


def listar_gastos(sesion: Session, complejo_id: UUID) -> list[dict[str, Any]]:
    return [
        dict(f)
        for f in sesion.execute(text(_SENTENCIA_LISTAR_GASTOS), {"id": complejo_id}).mappings()
    ]


def cargar_gasto(sesion: Session, gasto_id: UUID) -> dict[str, Any] | None:
    fila = (
        sesion.execute(
            text(f"SELECT {_COLUMNAS_GASTO} FROM gasto WHERE id=:id"),  # noqa: S608
            {"id": gasto_id},
        )
        .mappings()
        .first()
    )
    return None if fila is None else dict(fila)


@accion_sensible(EventoDelGasto.CREAR_GASTO)
def crear_gasto(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    datos: dict[str, Any],
    request_id: UUID,
) -> tuple[UUID, str | None]:
    try:
        entrada = DatosGasto.model_validate(datos)
    except ValidationError as error:
        raise error_de_validacion(error) from None
    _validar_pertenencia(sesion, entrada, complejo_id)
    aviso = _aviso_de_receptor_distinto(sesion, complejo_id, entrada.documento_receptor)
    with transaccion(sesion, _CONFLICTOS):
        gasto_id = UUID(
            str(
                sesion.execute(
                    text(
                        "INSERT INTO gasto (administracion_id, complejo_id, proveedor_id, "
                        "categoria_id, grupo_id, concepto, periodo, periodo_de_imputacion, "
                        "tipo, importe, cuit_emisor, punto_de_venta, tipo_de_comprobante, "
                        "numero_de_comprobante, documento_receptor) "
                        "VALUES (:admin, :complejo, :proveedor_id, :categoria_id, :grupo_id, "
                        ":concepto, :periodo, :periodo, :tipo, :importe, :cuit_emisor, "
                        ":punto_de_venta, :tipo_de_comprobante, :numero_de_comprobante, "
                        ":documento_receptor) "
                        "RETURNING id"
                    ),
                    {
                        "admin": identidad.administracion_id,
                        "complejo": complejo_id,
                        "proveedor_id": entrada.proveedor_id,
                        "categoria_id": entrada.categoria_id,
                        "grupo_id": entrada.grupo_id,
                        "concepto": entrada.concepto,
                        "periodo": entrada.periodo,
                        "tipo": entrada.tipo,
                        "importe": entrada.importe.a_texto(),
                        "cuit_emisor": entrada.cuit_emisor,
                        "punto_de_venta": entrada.punto_de_venta,
                        "tipo_de_comprobante": entrada.tipo_de_comprobante,
                        "numero_de_comprobante": entrada.numero_de_comprobante,
                        "documento_receptor": entrada.documento_receptor,
                    },
                ).scalar_one()
            )
        )
        registrar(
            sesion,
            identidad,
            EventoDelGasto.CREAR_GASTO,
            entidad="gasto",
            entidad_id=gasto_id,
            request_id=request_id,
            detalle={"complejo_id": str(complejo_id)},
        )
    return gasto_id, aviso


@accion_sensible(EventoDelGasto.EDITAR_GASTO)
def editar_gasto(
    sesion: Session,
    identidad: Identidad,
    *,
    gasto_id: UUID,
    cambios: dict[str, Any],
    request_id: UUID,
) -> None:
    with transaccion(sesion, _CONFLICTOS):
        fila = (
            sesion.execute(text("SELECT * FROM gasto WHERE id=:id FOR UPDATE"), {"id": gasto_id})
            .mappings()
            .first()
        )
        if fila is None:
            raise NoEncontrado()
        if fila["estado"] not in _ESTADOS_EDITABLES and any(
            campo in cambios for campo in _CAMPOS_BLOQUEADOS_SI_APROBADO
        ):
            raise EntradaInvalida(
                "estado", "un gasto aprobado no puede editar importe, grupo, período ni tipo"
            )
        valores = {
            "concepto": fila["concepto"],
            "categoria_id": fila["categoria_id"],
            "grupo_id": fila["grupo_id"],
            "proveedor_id": fila["proveedor_id"],
            "periodo": fila["periodo"],
            "tipo": fila["tipo"],
            "importe": Dinero(str(fila["importe"])),
            "cuit_emisor": fila["cuit_emisor"],
            "punto_de_venta": fila["punto_de_venta"],
            "tipo_de_comprobante": fila["tipo_de_comprobante"],
            "numero_de_comprobante": fila["numero_de_comprobante"],
            "documento_receptor": fila["documento_receptor"],
            **cambios,
        }
        try:
            entrada = DatosGasto.model_validate(valores)
        except ValidationError as error:
            raise error_de_validacion(error) from None
        _validar_pertenencia(sesion, entrada, fila["complejo_id"])
        cambia_importe = entrada.importe.a_texto() != Dinero(str(fila["importe"])).a_texto()
        quita_factura = any(getattr(entrada, campo) is None for campo in CAMPOS_DE_FACTURA) and all(
            fila[campo] is not None for campo in CAMPOS_DE_FACTURA
        )
        if cambia_importe or quita_factura:
            #: R22: toda nota de crédito corrige una factura y su suma nunca
            #: la supera. La fila ya está bloqueada (`FOR UPDATE`), igual que
            #: al cargar una nota, así que las dos operaciones se serializan.
            acreditado = Dinero(
                str(
                    sesion.execute(
                        text(
                            "SELECT COALESCE(SUM(importe), 0)::text FROM nota_de_credito "
                            "WHERE gasto_id=:id"
                        ),
                        {"id": gasto_id},
                    ).scalar_one()
                )
            )
            if quita_factura and acreditado > Dinero("0.00"):
                raise EntradaInvalida(
                    "factura", "no se puede quitar la factura de un gasto con notas de crédito"
                )
            if entrada.importe < acreditado:
                raise EntradaInvalida(
                    "importe",
                    "no puede quedar por debajo de lo acreditado por sus notas de crédito "
                    f"({acreditado.a_texto()})",
                )
        nuevos = {
            "concepto": entrada.concepto,
            "categoria_id": entrada.categoria_id,
            "grupo_id": entrada.grupo_id,
            "proveedor_id": entrada.proveedor_id,
            "periodo": entrada.periodo,
            #: D8: mientras no se aprobó sigue a `periodo`; aprobado, quedó
            #: fijado al aprobar y ninguna edición lo mueve (D-141).
            "periodo_de_imputacion": (
                entrada.periodo
                if fila["estado"] in _ESTADOS_EDITABLES
                else fila["periodo_de_imputacion"]
            ),
            "tipo": entrada.tipo,
            "importe": entrada.importe.a_texto(),
            "cuit_emisor": entrada.cuit_emisor,
            "punto_de_venta": entrada.punto_de_venta,
            "tipo_de_comprobante": entrada.tipo_de_comprobante,
            "numero_de_comprobante": entrada.numero_de_comprobante,
            "documento_receptor": entrada.documento_receptor,
        }
        anteriores = {
            "concepto": fila["concepto"],
            "categoria_id": fila["categoria_id"],
            "grupo_id": fila["grupo_id"],
            "proveedor_id": fila["proveedor_id"],
            "periodo": fila["periodo"],
            "periodo_de_imputacion": fila["periodo_de_imputacion"],
            "tipo": fila["tipo"],
            "importe": Dinero(str(fila["importe"])).a_texto(),
            "cuit_emisor": fila["cuit_emisor"],
            "punto_de_venta": fila["punto_de_venta"],
            "tipo_de_comprobante": fila["tipo_de_comprobante"],
            "numero_de_comprobante": fila["numero_de_comprobante"],
            "documento_receptor": fila["documento_receptor"],
        }
        campos = sorted(k for k, v in nuevos.items() if v != anteriores[k])
        if not campos:
            return
        #: D8: `periodo_de_imputacion` nunca es un campo propio en la
        #: auditoría — es una consecuencia mecánica de `periodo` (que sí
        #: figura), no algo que el usuario edita por su cuenta.
        campos_auditados = [c for c in campos if c != "periodo_de_imputacion"]
        sesion.execute(
            text(
                "UPDATE gasto SET concepto=:concepto, categoria_id=:categoria_id, "
                "grupo_id=:grupo_id, proveedor_id=:proveedor_id, periodo=:periodo, "
                "periodo_de_imputacion=:periodo_de_imputacion, "
                "tipo=:tipo, importe=:importe, cuit_emisor=:cuit_emisor, "
                "punto_de_venta=:punto_de_venta, tipo_de_comprobante=:tipo_de_comprobante, "
                "numero_de_comprobante=:numero_de_comprobante, "
                "documento_receptor=:documento_receptor WHERE id=:id"
            ),
            {**nuevos, "id": gasto_id},
        )
        registrar(
            sesion,
            identidad,
            EventoDelGasto.EDITAR_GASTO,
            entidad="gasto",
            entidad_id=gasto_id,
            request_id=request_id,
            detalle={"complejo_id": str(fila["complejo_id"]), "campos": campos_auditados},
        )


@accion_sensible(EventoDelGasto.APROBAR_GASTO)
def aprobar_gasto(
    sesion: Session,
    identidad: Identidad,
    *,
    gasto_id: UUID,
    request_id: UUID,
    es_periodo_emitido: PeriodoEmitidoFn = _nada_esta_emitido_todavia,
) -> None:
    with transaccion(sesion, {}):
        fila = (
            sesion.execute(
                text("SELECT complejo_id, periodo, estado FROM gasto WHERE id=:id FOR UPDATE"),
                {"id": gasto_id},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise NoEncontrado()
        if fila["estado"] == "aprobado":
            #: Idempotente (D9, "Aprobar dos veces"): ni cambio ni fila nueva,
            #: ni se vuelve a mover `periodo_de_imputacion` (D8: se fija UNA
            #: sola vez, al aprobar).
            return
        #: D8: se fija acá, la única vez — nunca se recalcula después.
        periodo_de_imputacion = _primer_periodo_no_emitido(
            sesion, fila["complejo_id"], fila["periodo"], es_periodo_emitido
        )
        sesion.execute(
            text(
                "UPDATE gasto SET estado='aprobado', "
                "periodo_de_imputacion=:periodo_de_imputacion WHERE id=:id"
            ),
            {"id": gasto_id, "periodo_de_imputacion": periodo_de_imputacion},
        )
        registrar(
            sesion,
            identidad,
            EventoDelGasto.APROBAR_GASTO,
            entidad="gasto",
            entidad_id=gasto_id,
            request_id=request_id,
            detalle={"complejo_id": str(fila["complejo_id"])},
        )


def gastos_aprobados_del_periodo(
    sesion: Session, complejo_id: UUID, periodo: date
) -> dict[str, Any]:
    """D10: una sola lectura, netos de notas de crédito (el neto real llega
    con el bloque 4; hasta entonces, sin notas de crédito, bruto == neto).
    Nunca reparte por unidad (eso es del cambio 7)."""
    filas = (
        sesion.execute(
            text(
                "SELECT grupo_id, categoria_id, tipo, importe::text AS importe FROM gasto "
                "WHERE complejo_id=:complejo AND periodo_de_imputacion=:periodo "
                "AND estado='aprobado'"
            ),
            {"complejo": complejo_id, "periodo": periodo},
        )
        .mappings()
        .all()
    )
    grupos: dict[str, dict[str, dict[str, Dinero]]] = {}
    for fila in filas:
        grupo = grupos.setdefault(str(fila["grupo_id"]), {"ordinario": {}, "extraordinario": {}})
        bloque = grupo[fila["tipo"]]
        clave_categoria = str(fila["categoria_id"])
        bloque[clave_categoria] = bloque.get(clave_categoria, Dinero("0.00")) + Dinero(
            fila["importe"]
        )
    #: D10/R22: neto de notas de crédito. Sólo las que corrigen un gasto ya
    #: `aprobado` (el JOIN lo filtra) y cuyo propio `periodo` (D-082: "se
    #: descuenta en el período en que se carga") es el consultado — nunca el
    #: `periodo_de_imputacion` de la factura, para no reabrir un período ya
    #: emitido.
    notas = (
        sesion.execute(
            text(
                "SELECT g.grupo_id, g.categoria_id, g.tipo, n.importe::text AS importe "
                "FROM nota_de_credito n JOIN gasto g ON g.id = n.gasto_id "
                "WHERE n.complejo_id=:complejo AND n.periodo=:periodo AND g.estado='aprobado'"
            ),
            {"complejo": complejo_id, "periodo": periodo},
        )
        .mappings()
        .all()
    )
    for fila in notas:
        grupo = grupos.setdefault(str(fila["grupo_id"]), {"ordinario": {}, "extraordinario": {}})
        bloque = grupo[fila["tipo"]]
        clave_categoria = str(fila["categoria_id"])
        bloque[clave_categoria] = bloque.get(clave_categoria, Dinero("0.00")) - Dinero(
            fila["importe"]
        )
    resultado_grupos: dict[str, Any] = {}
    total_general = Dinero("0.00")
    for grupo_id, bloques in grupos.items():
        subtotales = {
            tipo: sumar(categorias.values()) if categorias else Dinero("0.00")
            for tipo, categorias in bloques.items()
        }
        total_grupo = sumar(subtotales.values())
        total_general = total_general + total_grupo
        resultado_grupos[grupo_id] = {
            "total": total_grupo.a_texto(),
            "ordinario": {
                "subtotal": subtotales["ordinario"].a_texto(),
                "categorias": {c: m.a_texto() for c, m in bloques["ordinario"].items()},
            },
            "extraordinario": {
                "subtotal": subtotales["extraordinario"].a_texto(),
                "categorias": {c: m.a_texto() for c, m in bloques["extraordinario"].items()},
            },
        }
    return {
        "periodo": periodo.isoformat(),
        "total": total_general.a_texto(),
        "grupos": resultado_grupos,
    }


def obligatorios_faltantes(sesion: Session, complejo_id: UUID, periodo: date) -> dict[str, Any]:
    """D7/D-141: qué categorías de gasto mensual obligatorio no tienen un
    gasto aprobado en este período. Sólo lectura, nunca bloquea nada (D10:
    el control de si eso frena algo es del 7). `periodo_de_imputacion`, no
    `periodo` de origen — es la que efectivamente cubre esa liquidación."""
    obligatorias = listar_categorias_obligatorias(sesion, complejo_id)
    if not obligatorias:
        return {"periodo": periodo.isoformat(), "faltantes": []}
    cubiertas = set(
        sesion.execute(
            text(
                "SELECT DISTINCT categoria_id FROM gasto WHERE complejo_id=:complejo "
                "AND periodo_de_imputacion=:periodo AND estado='aprobado'"
            ),
            {"complejo": complejo_id, "periodo": periodo},
        )
        .scalars()
        .all()
    )
    return {
        "periodo": periodo.isoformat(),
        "faltantes": [
            {"id": str(c["id"]), "nombre": c["nombre"]}
            for c in obligatorias
            if c["id"] not in cubiertas
        ],
    }
