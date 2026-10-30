"""Cargos particulares (R14, D-025): un importe contra una sola unidad,
nunca repartido (D2). Mismo patrón CRUD + auditoría que `gastos.py`.
"""

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
    cargar_unidad,
    cargar_unidad_por_identificador,
)
from proptech_core.gastos.aplicacion.errores import (
    EntradaInvalida,
    ImportacionInvalida,
    NoEncontrado,
    error_de_validacion,
    transaccion,
)
from proptech_core.gastos.dominio.cargo_particular import DatosCargoParticular
from proptech_core.gastos.puertos import FilaCargoImportada, LectorDePlanillaDeCargos

_ESTADOS_EDITABLES = ("borrador",)
_CAMPOS_BLOQUEADOS_SI_APROBADO = ("importe", "unidad_id", "periodo")
_COLUMNAS_CARGO = (
    "id, complejo_id, unidad_id, concepto, importe::text AS importe, periodo, motivo, estado"
)


def cargar_cargo(sesion: Session, cargo_id: UUID) -> dict[str, Any] | None:
    fila = (
        sesion.execute(
            text(f"SELECT {_COLUMNAS_CARGO} FROM cargo_particular WHERE id=:id"),  # noqa: S608
            {"id": cargo_id},
        )
        .mappings()
        .first()
    )
    return None if fila is None else dict(fila)


_SENTENCIA_LISTAR_CARGOS = (
    f"SELECT {_COLUMNAS_CARGO} FROM cargo_particular "  # noqa: S608
    "WHERE complejo_id=:id ORDER BY periodo DESC"
)


def listar_cargos(sesion: Session, complejo_id: UUID) -> list[dict[str, Any]]:
    return [
        dict(f)
        for f in sesion.execute(
            text(_SENTENCIA_LISTAR_CARGOS),
            {"id": complejo_id},
        ).mappings()
    ]


def _validar_unidad(sesion: Session, unidad_id: UUID, complejo_id: UUID) -> None:
    #: R14: a diferencia de categoría/grupo en `gasto` (422), una unidad de
    #: otro edificio da 404 — la unidad es el recurso al que pertenece el
    #: cargo, no una referencia suelta (spec `cargos-particulares`, "Unidad
    #: de otro edificio").
    unidad = cargar_unidad(sesion, unidad_id)
    if unidad is None or unidad.complejo_id != complejo_id:
        raise NoEncontrado()


@accion_sensible(EventoDelGasto.CREAR_CARGO_PARTICULAR)
def crear_cargo_particular(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    datos: dict[str, Any],
    request_id: UUID,
) -> UUID:
    try:
        entrada = DatosCargoParticular.model_validate(datos)
    except ValidationError as error:
        raise error_de_validacion(error) from None
    _validar_unidad(sesion, entrada.unidad_id, complejo_id)
    with transaccion(sesion, {}):
        cargo_id = UUID(
            str(
                sesion.execute(
                    text(
                        "INSERT INTO cargo_particular (administracion_id, complejo_id, "
                        "unidad_id, concepto, importe, periodo, motivo) "
                        "VALUES (:admin, :complejo, :unidad_id, :concepto, :importe, "
                        ":periodo, :motivo) RETURNING id"
                    ),
                    {
                        "admin": identidad.administracion_id,
                        "complejo": complejo_id,
                        "unidad_id": entrada.unidad_id,
                        "concepto": entrada.concepto,
                        "importe": entrada.importe.a_texto(),
                        "periodo": entrada.periodo,
                        "motivo": entrada.motivo,
                    },
                ).scalar_one()
            )
        )
        registrar(
            sesion,
            identidad,
            EventoDelGasto.CREAR_CARGO_PARTICULAR,
            entidad="cargo_particular",
            entidad_id=cargo_id,
            request_id=request_id,
            detalle={"complejo_id": str(complejo_id), "unidad_id": str(entrada.unidad_id)},
        )
    return cargo_id


@accion_sensible(EventoDelGasto.EDITAR_CARGO_PARTICULAR)
def editar_cargo_particular(
    sesion: Session,
    identidad: Identidad,
    *,
    cargo_id: UUID,
    cambios: dict[str, Any],
    request_id: UUID,
) -> None:
    with transaccion(sesion, {}):
        fila = (
            sesion.execute(
                text("SELECT * FROM cargo_particular WHERE id=:id FOR UPDATE"), {"id": cargo_id}
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise NoEncontrado()
        if fila["estado"] not in _ESTADOS_EDITABLES and any(
            campo in cambios for campo in _CAMPOS_BLOQUEADOS_SI_APROBADO
        ):
            raise EntradaInvalida(
                "estado", "un cargo aprobado no puede cambiar importe, unidad ni período"
            )
        valores = {
            "unidad_id": fila["unidad_id"],
            "concepto": fila["concepto"],
            "importe": Dinero(str(fila["importe"])),
            "periodo": fila["periodo"],
            "motivo": fila["motivo"],
            **cambios,
        }
        try:
            entrada = DatosCargoParticular.model_validate(valores)
        except ValidationError as error:
            raise error_de_validacion(error) from None
        _validar_unidad(sesion, entrada.unidad_id, fila["complejo_id"])
        nuevos = {
            "unidad_id": entrada.unidad_id,
            "concepto": entrada.concepto,
            "importe": entrada.importe.a_texto(),
            "periodo": entrada.periodo,
            "motivo": entrada.motivo,
        }
        anteriores = {
            "unidad_id": fila["unidad_id"],
            "concepto": fila["concepto"],
            "importe": Dinero(str(fila["importe"])).a_texto(),
            "periodo": fila["periodo"],
            "motivo": fila["motivo"],
        }
        campos = sorted(k for k, v in nuevos.items() if v != anteriores[k])
        if not campos:
            return
        sesion.execute(
            text(
                "UPDATE cargo_particular SET unidad_id=:unidad_id, concepto=:concepto, "
                "importe=:importe, periodo=:periodo, motivo=:motivo WHERE id=:id"
            ),
            {**nuevos, "id": cargo_id},
        )
        registrar(
            sesion,
            identidad,
            EventoDelGasto.EDITAR_CARGO_PARTICULAR,
            entidad="cargo_particular",
            entidad_id=cargo_id,
            request_id=request_id,
            detalle={"complejo_id": str(fila["complejo_id"]), "campos": campos},
        )


@accion_sensible(EventoDelGasto.APROBAR_CARGO_PARTICULAR)
def aprobar_cargo_particular(
    sesion: Session, identidad: Identidad, *, cargo_id: UUID, request_id: UUID
) -> None:
    with transaccion(sesion, {}):
        fila = (
            sesion.execute(
                text(
                    "SELECT complejo_id, unidad_id, estado FROM cargo_particular "
                    "WHERE id=:id FOR UPDATE"
                ),
                {"id": cargo_id},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise NoEncontrado()
        if fila["estado"] == "aprobado":
            return
        sesion.execute(
            text("UPDATE cargo_particular SET estado='aprobado' WHERE id=:id"), {"id": cargo_id}
        )
        registrar(
            sesion,
            identidad,
            EventoDelGasto.APROBAR_CARGO_PARTICULAR,
            entidad="cargo_particular",
            entidad_id=cargo_id,
            request_id=request_id,
            detalle={"complejo_id": str(fila["complejo_id"]), "unidad_id": str(fila["unidad_id"])},
        )


def cargos_aprobados_del_periodo(
    sesion: Session, complejo_id: UUID, periodo: date
) -> dict[str, Any]:
    """D2: líneas propias por unidad, nunca mezcladas con los gastos por
    grupo, nunca en la base prorrateable de R13."""
    filas = (
        sesion.execute(
            text(
                "SELECT id, unidad_id, concepto, importe::text AS importe FROM cargo_particular "
                "WHERE complejo_id=:complejo AND periodo=:periodo AND estado='aprobado'"
            ),
            {"complejo": complejo_id, "periodo": periodo},
        )
        .mappings()
        .all()
    )
    unidades: dict[str, list[dict[str, Any]]] = {}
    for fila in filas:
        unidades.setdefault(str(fila["unidad_id"]), []).append(
            {"id": str(fila["id"]), "concepto": fila["concepto"], "importe": fila["importe"]}
        )
    return {
        "periodo": periodo.isoformat(),
        "unidades": {
            unidad_id: {
                "cargos": cargos,
                "total": sumar(Dinero(c["importe"]) for c in cargos).a_texto(),
            }
            for unidad_id, cargos in unidades.items()
        },
    }


@accion_sensible(EventoDelGasto.IMPORTAR_CARGOS_PARTICULARES)
def importar_cargos_particulares(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    lector: LectorDePlanillaDeCargos,
    contenido: bytes,
    periodo: date,
    request_id: UUID,
) -> int:
    """D6: todo o nada. El caso de uso no sabe que existe Excel — `lector`
    es el puerto; un test lo dobla con una lista fija de filas."""
    filas_crudas = lector.leer(contenido)
    errores: list[dict[str, object]] = []
    validadas: list[tuple[FilaCargoImportada, DatosCargoParticular, UUID]] = []
    for fila in filas_crudas:
        if not fila.unidad_identificador:
            errores.append({"fila": fila.numero_de_fila, "motivo": "falta la unidad"})
            continue
        unidad = cargar_unidad_por_identificador(sesion, complejo_id, fila.unidad_identificador)
        if unidad is None:
            errores.append(
                {
                    "fila": fila.numero_de_fila,
                    "motivo": f"la unidad '{fila.unidad_identificador}' no existe en este edificio",
                }
            )
            continue
        try:
            entrada = DatosCargoParticular.model_validate(
                {
                    "unidad_id": unidad.id,
                    "concepto": fila.concepto,
                    "importe": fila.importe,
                    "periodo": periodo,
                    "motivo": "importado desde planilla",
                }
            )
        except ValidationError as error:
            campos = sorted({".".join(map(str, e["loc"])) for e in error.errors()})
            errores.append(
                {"fila": fila.numero_de_fila, "motivo": f"dato inválido: {', '.join(campos)}"}
            )
            continue
        validadas.append((fila, entrada, unidad.id))
    if errores:
        raise ImportacionInvalida(errores)
    with transaccion(sesion, {}):
        for _fila, entrada, unidad_id in validadas:
            sesion.execute(
                text(
                    "INSERT INTO cargo_particular (administracion_id, complejo_id, unidad_id, "
                    "concepto, importe, periodo, motivo) VALUES (:admin, :complejo, "
                    ":unidad_id, :concepto, :importe, :periodo, :motivo)"
                ),
                {
                    "admin": identidad.administracion_id,
                    "complejo": complejo_id,
                    "unidad_id": unidad_id,
                    "concepto": entrada.concepto,
                    "importe": entrada.importe.a_texto(),
                    "periodo": entrada.periodo,
                    "motivo": entrada.motivo,
                },
            )
        registrar(
            sesion,
            identidad,
            EventoDelGasto.IMPORTAR_CARGOS_PARTICULARES,
            entidad="complejo",
            entidad_id=complejo_id,
            request_id=request_id,
            detalle={"complejo_id": str(complejo_id), "cantidad": len(validadas)},
        )
    return len(validadas)
