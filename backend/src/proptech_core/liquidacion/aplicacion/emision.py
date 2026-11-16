"""Emitir lo revisado (HU-A5, D-157; E2, E3, E5, E7, E8, E15): una obligación por unidad en el
libro, todo lo usado guardado y la auditoría, en una sola transacción.

Orden de chequeo (el router ya cargó el edificio, 404, y pidió el permiso de emitir, 403): el
pedido (422) -> el candado del período, `FOR UPDATE` sobre la fila de `complejo` **antes** que los
candados de cuentas (E5) -> el replay por `emision_id` -> el orden de períodos (409) -> la
preliquidación recalculada bajo el candado y su huella (409) -> controles duros (422) -> alertas
aceptadas (409) -> permiso de aceptar bloqueantes (403) -> recién ahí las escrituras. Un rechazo no
escribe nada: todo corre dentro de un SAVEPOINT. No commitea: lo hace el llamador.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, puede
from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.complejos.aplicacion.errores import transaccion
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.cuenta_corriente.aplicacion.creditos import ahora_utc
from proptech_core.cuenta_corriente.aplicacion.emisiones import (
    EmisionRegistrada,
    ObligacionAEmitir,
    registrar_emision,
)
from proptech_core.cuenta_corriente.aplicacion.lecturas import fotos_del_edificio
from proptech_core.liquidacion.aplicacion.errores import (
    Conflicto,
    ControlDuro,
    EntradaInvalida,
    NoEncontrado,
    SinPermiso,
)
from proptech_core.liquidacion.aplicacion.lectura import (
    leer_liquidacion,
    liquidacion_de_la_emision,
    obligaciones_emitidas,
)
from proptech_core.liquidacion.aplicacion.preliquidacion import (
    datos_de_la_preliquidacion,
    preliquidar_datos,
)
from proptech_core.liquidacion.dominio.emision import (
    AlertasDistintas,
    ControlDuroActivo,
    PedidoDeEmision,
    PedidoInvalido,
    coeficientes_efectivos,
    pedido_de_emision,
    validar_alertas,
)
from proptech_core.liquidacion.dominio.preliquidacion import DatosDeLaPreliquidacion
from proptech_core.liquidacion.dominio.reparto import pesos_del_grupo

_CERO = Dinero("0.00")


@dataclass(frozen=True)
class EmisionHecha:
    #: `False` cuando el mismo pedido ya estaba emitido: el replay no escribe nada.
    nueva: bool
    respuesta: dict[str, Any]


def _respuesta(sesion: Session, complejo_id: UUID, liquidacion_id: UUID) -> dict[str, Any]:
    emitida = leer_liquidacion(sesion, complejo_id=complejo_id, liquidacion_id=liquidacion_id)
    if emitida is None:  # pragma: no cover - acabamos de leerla o de escribirla
        raise NoEncontrado
    return {
        "liquidacion_id": emitida["liquidacion_id"],
        "emision_id": emitida["emision_id"],
        "periodo": emitida["periodo"],
        "vencimiento": emitida["vencimiento"],
        "huella": emitida["huella"],
        "obligaciones": obligaciones_emitidas(emitida),
    }


def _es_el_mismo_pedido(emitida: dict[str, Any], periodo: date, pedido: PedidoDeEmision) -> bool:
    corrida = pedido.vencimiento
    mismo_vencimiento = (
        emitida["motivo_del_vencimiento"] is None
        if corrida is None
        else (
            emitida["vencimiento"] == corrida.fecha.isoformat()
            and emitida["motivo_del_vencimiento"] == corrida.motivo
        )
    )
    return (
        emitida["periodo"] == periodo.isoformat()
        and emitida["huella"] == pedido.huella
        and mismo_vencimiento
        and Counter(a["codigo"] for a in emitida["alertas_aceptadas"])
        == Counter(pedido.alertas_aceptadas)
    )


def _intereses_por_unidad(
    registrada: EmisionRegistrada, cuenta_a_unidad: Mapping[UUID, UUID]
) -> dict[UUID, Dinero]:
    resultado: dict[UUID, Dinero] = {}
    for cuenta, intereses in registrada.intereses.items():
        unidad = cuenta_a_unidad[cuenta]
        resultado[unidad] = resultado.get(unidad, _CERO) + sumar(i.importe for i in intereses)
    return resultado


def _guardar(
    sesion: Session,
    identidad: Identidad,
    *,
    liquidacion_id: UUID,
    complejo_id: UUID,
    periodo: date,
    emision_id: UUID,
    cuerpo: dict[str, Any],
    datos: DatosDeLaPreliquidacion,
    vencimiento: date,
    corrida: tuple[date, str] | None,
    aceptadas: tuple[str, ...],
    saldos: Mapping[UUID, Dinero],
    request_id: UUID,
    instante: datetime,
) -> None:
    """Las tablas de la `0041`. Lo que se guarda es el cuerpo de la preliquidación que se revisó
    (la misma huella) más lo que sólo existe al emitir: la composición, el saldo anterior, el
    vencimiento corrido y las alertas aceptadas."""
    base = {"adm": identidad.administracion_id, "c": complejo_id, "l": liquidacion_id}
    totales = cuerpo["totales"]
    sesion.execute(
        text(
            "INSERT INTO liquidacion (id, administracion_id, complejo_id, emision_id, periodo, "
            "huella, version_de_configuracion_id, porcentaje_fondo, vencimiento, "
            "vencimiento_original, motivo_del_vencimiento, total_gastos, total_notas_de_credito, "
            "total_fondo_de_reserva, total_prorrateado, total_cargos_particulares, "
            "total_intereses, total, emitida_por, request_id, emitida_en) VALUES (:l, :adm, :c, "
            ":e, :p, :h, :version, :fondo, :v, :original, :motivo, :gastos, :notas, :reserva, "
            ":prorrateado, :cargos, :intereses, :total, :por, :req, :en)"
        ),
        {
            **base,
            "e": emision_id,
            "p": periodo,
            "h": cuerpo["huella"],
            "version": UUID(datos.version_de_configuracion),
            "fondo": cuerpo["porcentaje_fondo"],
            "v": vencimiento,
            "original": None if corrida is None else corrida[0],
            "motivo": None if corrida is None else corrida[1],
            "gastos": totales["gastos"],
            "notas": totales["notas_de_credito"],
            "reserva": totales["fondo_de_reserva"],
            "prorrateado": totales["prorrateado"],
            "cargos": totales["cargos_particulares"],
            "intereses": totales["intereses"],
            "total": totales["total"],
            "por": identidad.persona_id,
            "req": request_id,
            "en": instante,
        },
    )
    categorias = [
        {
            **base,
            "bloque": bloque,
            "orden": orden,
            "cat": UUID(c["categoria_id"]),
            "nombre": c["nombre"],
            "importe": c["importe"],
            "pct": c["porcentaje"],
        }
        for bloque, contenido in cuerpo["bloques"].items()
        for orden, c in enumerate(contenido["categorias"])
    ]
    if categorias:
        sesion.execute(
            text(
                "INSERT INTO categoria_de_liquidacion (administracion_id, complejo_id, "
                "liquidacion_id, bloque, orden, categoria_id, nombre, importe, porcentaje) "
                "VALUES (:adm, :c, :l, :bloque, :orden, :cat, :nombre, :importe, :pct)"
            ),
            categorias,
        )
    unidades = datos.unidades
    posicion = {UUID(u["unidad_id"]): n for n, u in enumerate(cuerpo["unidades"])}
    grupos_del_cuerpo = [
        {
            **base,
            "orden": orden,
            "grupo": UUID(g["grupo_id"]),
            "nombre": g["nombre"],
            "metodo": g["metodo"],
            "ord": g["ordinario"],
            "ext": g["extraordinario"],
        }
        for orden, g in enumerate(cuerpo["grupos"])
    ]
    if grupos_del_cuerpo:
        sesion.execute(
            text(
                "INSERT INTO grupo_de_liquidacion (administracion_id, complejo_id, liquidacion_id, "
                "orden, grupo_id, nombre, metodo, ordinario, extraordinario) "
                "VALUES (:adm, :c, :l, :orden, :grupo, :nombre, :metodo, :ord, :ext)"
            ),
            grupos_del_cuerpo,
        )
    por_id = {g.id: g for g in datos.grupos}
    composicion = [
        {
            **base,
            "grupo": g["grupo"],
            "orden": orden,
            "unidad": unidad,
            "coef": coeficiente,
        }
        for g in grupos_del_cuerpo
        for orden, (unidad, coeficiente) in enumerate(
            sorted(
                coeficientes_efectivos(pesos_del_grupo(por_id[g["grupo"]], unidades)).items(),
                key=lambda par: posicion[par[0]],
            )
        )
    ]
    if composicion:
        sesion.execute(
            text(
                "INSERT INTO composicion_de_grupo (administracion_id, complejo_id, liquidacion_id, "
                "grupo_id, orden, unidad_id, coeficiente) "
                "VALUES (:adm, :c, :l, :grupo, :orden, :unidad, :coef)"
            ),
            composicion,
        )
    sesion.execute(
        text(
            "INSERT INTO linea_de_liquidacion (administracion_id, complejo_id, liquidacion_id, "
            "orden, unidad_id, identificador, ordinaria, fondo_de_reserva, extraordinaria, "
            "intereses, total, sin_obligacion, saldo_anterior, cargos_particulares, por_grupo) "
            "VALUES (:adm, :c, :l, :orden, :unidad, :ident, :ord, :fondo, :ext, :int, :total, "
            ":sin, :saldo, CAST(:cargos AS jsonb), CAST(:grupos AS jsonb))"
        ),
        [
            {
                **base,
                "orden": orden,
                "unidad": UUID(u["unidad_id"]),
                "ident": u["identificador"],
                "ord": u["ordinaria"],
                "fondo": u["fondo_de_reserva"],
                "ext": u["extraordinaria"],
                "int": u["intereses"],
                "total": u["total"],
                "sin": u["sin_obligacion"],
                "saldo": saldos.get(UUID(u["unidad_id"]), _CERO).a_texto(),
                "cargos": json.dumps(u["cargos_particulares"]),
                "grupos": json.dumps(u["por_grupo"]),
            }
            for orden, u in enumerate(cuerpo["unidades"])
        ],
    )
    por_codigo = {c["codigo"]: c for c in cuerpo["controles"]}
    if aceptadas:
        sesion.execute(
            text(
                "INSERT INTO alerta_aceptada (administracion_id, complejo_id, liquidacion_id, "
                "codigo, mensaje, detalle, aceptada_por, aceptada_en) VALUES (:adm, :c, :l, "
                ":codigo, :mensaje, CAST(:detalle AS jsonb), :por, :en)"
            ),
            [
                {
                    **base,
                    "codigo": codigo,
                    "mensaje": por_codigo[codigo]["mensaje"],
                    "detalle": json.dumps(por_codigo[codigo]["detalle"]),
                    "por": identidad.persona_id,
                    "en": instante,
                }
                for codigo in aceptadas
            ],
        )


def emitir_liquidacion(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    periodo: date,
    cuerpo: Mapping[str, Any],
    request_id: UUID,
    reloj: Callable[[], datetime] = ahora_utc,
) -> EmisionHecha:
    try:
        pedido = pedido_de_emision(cuerpo, periodo)
    except PedidoInvalido as error:
        raise EntradaInvalida(error.campo, donde="body") from None
    with transaccion(sesion, {}):
        # E5: el candado del período, antes que cualquier candado de cuentas; todo lo que sigue se
        # lee ya con él puesto (READ COMMITTED: cada sentencia ve lo último confirmado).
        if cargar_complejo(sesion, complejo_id, bloquear=True) is None:
            raise NoEncontrado
        previa = liquidacion_de_la_emision(sesion, pedido.emision_id)
        if previa is not None:
            emitida = leer_liquidacion(sesion, complejo_id=complejo_id, liquidacion_id=previa)
            if emitida is None or not _es_el_mismo_pedido(emitida, periodo, pedido):
                raise Conflicto("emision_id", "emision_id_repetido")
            return EmisionHecha(False, _respuesta(sesion, complejo_id, previa))

        datos = datos_de_la_preliquidacion(sesion, complejo_id=complejo_id, periodo=periodo)
        cuerpo_revisado = preliquidar_datos(datos)
        if cuerpo_revisado["huella"] != pedido.huella:
            raise Conflicto("huella", "preliquidacion_cambio")
        try:
            aceptadas = validar_alertas(cuerpo_revisado["controles"], pedido.alertas_aceptadas)
        except ControlDuroActivo as duro:
            raise ControlDuro(duro.codigos) from None
        except AlertasDistintas:
            raise Conflicto("alertas_aceptadas", "alertas_distintas") from None
        if aceptadas and not puede(
            cargar_asignaciones(sesion, identidad.persona_id),
            Accion.ACEPTAR_ALERTAS_BLOQUEANTES,
            complejo_id,
        ):
            raise SinPermiso(Accion.ACEPTAR_ALERTAS_BLOQUEANTES.value)

        # E8: el de la configuración, o el corrido con su motivo (la configuración no cambia).
        original = date.fromisoformat(cuerpo_revisado["vencimiento"])
        corrida = pedido.vencimiento
        vencimiento = original if corrida is None else corrida.fecha
        unidades = cuerpo_revisado["unidades"]
        instante = reloj()
        registrada = registrar_emision(
            sesion,
            identidad,
            emision_id=pedido.emision_id,
            complejo_id=complejo_id,
            periodo=periodo,
            obligaciones=[
                ObligacionAEmitir(
                    unidad_id=UUID(u["unidad_id"]),
                    vencimiento=vencimiento,
                    # E15: el libro no tiene columna de cargos: los recibe sumados en la ordinaria.
                    ordinaria=Dinero(u["ordinaria"])
                    + sumar(Dinero(c["importe"]) for c in u["cargos_particulares"]),
                    fondo_de_reserva=Dinero(u["fondo_de_reserva"]),
                    extraordinaria=Dinero(u["extraordinaria"]),
                )
                for u in unidades
                if not u["sin_obligacion"]
            ],
            request_id=request_id,
            reloj=lambda: instante,
        )
        # Bajo los candados de todas las cuentas del edificio (los toma el libro): la foto del
        # saldo anterior de cada unidad y el interés que el libro registró de verdad.
        cuenta_a_unidad: dict[UUID, UUID] = {}
        saldos: dict[UUID, Dinero] = {}
        for foto in fotos_del_edificio(sesion, complejo_id):
            if foto.unidad_id is None:
                continue
            cuenta_a_unidad[foto.cuenta_id] = foto.unidad_id
            saldos[foto.unidad_id] = (
                registrada.saldo_anterior[foto.cuenta_id]
                if foto.cuenta_id in registrada.saldo_anterior
                else foto.estado.deuda_sin_emision(pedido.emision_id)
            )
        # E3, E4: un pago entre el recálculo y los candados cambia el interés; lo revisado ya no
        # es lo que se emite, y la emisión entera vuelve con el SAVEPOINT.
        previstos = {
            UUID(u["unidad_id"]): Dinero(u["intereses"])
            for u in unidades
            if Dinero(u["intereses"]) != _CERO
        }
        emitidos = {
            unidad: interes
            for unidad, interes in _intereses_por_unidad(registrada, cuenta_a_unidad).items()
            if interes != _CERO
        }
        if emitidos != previstos:
            raise Conflicto("huella", "preliquidacion_cambio")

        liquidacion_id = uuid4()
        _guardar(
            sesion,
            identidad,
            liquidacion_id=liquidacion_id,
            complejo_id=complejo_id,
            periodo=periodo,
            emision_id=pedido.emision_id,
            cuerpo=cuerpo_revisado,
            datos=datos,
            vencimiento=vencimiento,
            corrida=None if corrida is None else (original, corrida.motivo),
            aceptadas=aceptadas,
            saldos=saldos,
            request_id=request_id,
            instante=instante,
        )
        registrar(
            sesion,
            identidad,
            Accion.EMITIR_Y_DISTRIBUIR_LIQUIDACION,
            entidad="liquidacion",
            entidad_id=liquidacion_id,
            request_id=request_id,
            detalle={
                "complejo_id": str(complejo_id),
                "periodo": periodo.isoformat(),
                "emision_id": str(pedido.emision_id),
            },
        )
        if aceptadas:
            registrar(
                sesion,
                identidad,
                Accion.ACEPTAR_ALERTAS_BLOQUEANTES,
                entidad="liquidacion",
                entidad_id=liquidacion_id,
                request_id=request_id,
                detalle={"complejo_id": str(complejo_id), "codigos": list(aceptadas)},
            )
    return EmisionHecha(True, _respuesta(sesion, complejo_id, liquidacion_id))
