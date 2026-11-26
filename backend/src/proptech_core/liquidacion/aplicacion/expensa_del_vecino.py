"""La expensa explicada para el vecino (change 11, H-039, D-170): lo emitido, leído tal como se
guardó (R16, E2), recortado a la línea de su unidad y a su vínculo.

El inquilino no ve nada extraordinario (D-170.2): ni el bloque, ni su parte por grupo, ni el
importe, ni la comparación. Nunca sale algo de otra unidad. Sólo cuentan las liquidaciones
emitidas o distribuidas; una anulada, o de otro edificio, no existe para el vecino. La lectura
del detalle distribuye lo que estaba emitido (D-074, D-170.4) por el puerto del 7.
"""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.liquidar import cierres_de_emisiones
from proptech_core.liquidacion.aplicacion.distribucion import registrar_distribucion
from proptech_core.liquidacion.aplicacion.errores import Conflicto, NoEncontrado
from proptech_core.liquidacion.aplicacion.lectura import estado_del_cierre, leer_liquidacion
from proptech_core.liquidacion.dominio.ciclo import ANULADA, DISTRIBUIDA, EMITIDA

INQUILINO = "inquilino"
_VIGENTES = (EMITIDA, DISTRIBUIDA)


def _linea(liquidada: dict[str, Any], unidad_id: UUID) -> dict[str, Any] | None:
    return next((u for u in liquidada["unidades"] if u["unidad_id"] == str(unidad_id)), None)


def _total_de_la_linea(linea: dict[str, Any], vinculo: str) -> Dinero:
    total = Dinero(linea["total"])
    return total - Dinero(linea["extraordinaria"]) if vinculo == INQUILINO else total


def listar_de_la_unidad(
    sesion: Session, *, complejo_id: UUID, unidad_id: UUID, vinculo: str
) -> list[dict[str, str]]:
    """Las emitidas y no anuladas del edificio, la más nueva primero, con el total de la unidad."""
    filas = sesion.execute(
        text(
            "SELECT id, emision_id FROM liquidacion WHERE complejo_id = :c "
            "ORDER BY periodo DESC, emitida_en DESC, id DESC"
        ),
        {"c": complejo_id},
    ).all()
    cierres = cierres_de_emisiones(sesion, [UUID(str(f.emision_id)) for f in filas])
    resultado = []
    for fila in filas:
        if estado_del_cierre(cierres.get(UUID(str(fila.emision_id)))) not in _VIGENTES:
            continue
        liquidada = leer_liquidacion(
            sesion, complejo_id=complejo_id, liquidacion_id=UUID(str(fila.id))
        )
        linea = None if liquidada is None else _linea(liquidada, unidad_id)
        if liquidada is None or linea is None:
            continue
        resultado.append(
            {
                "liquidacion_id": liquidada["liquidacion_id"],
                "periodo": liquidada["periodo"],
                "vencimiento": liquidada["vencimiento"],
                "total": _total_de_la_linea(linea, vinculo).a_texto(),
            }
        )
    return resultado


def _anterior(sesion: Session, *, complejo_id: UUID, periodo: str) -> dict[str, Any] | None:
    """La emitida inmediatamente anterior del edificio: la más reciente de período anterior que no
    está anulada (D-170.3)."""
    filas = sesion.execute(
        text(
            "SELECT id, emision_id FROM liquidacion WHERE complejo_id = :c AND periodo < :p "
            "ORDER BY periodo DESC, emitida_en DESC, id DESC"
        ),
        {"c": complejo_id, "p": date.fromisoformat(periodo)},
    ).all()
    cierres = cierres_de_emisiones(sesion, [UUID(str(f.emision_id)) for f in filas])
    for fila in filas:
        if estado_del_cierre(cierres.get(UUID(str(fila.emision_id)))) != ANULADA:
            return leer_liquidacion(
                sesion, complejo_id=complejo_id, liquidacion_id=UUID(str(fila.id))
            )
    return None


def _comparacion(
    actual: dict[str, Any],
    anterior: dict[str, Any],
    linea_anterior: dict[str, Any] | None,
    total: Dinero,
    vinculo: str,
) -> dict[str, Any]:
    bloques = ("ordinario",) if vinculo == INQUILINO else ("ordinario", "extraordinario")
    total_anterior = (
        Dinero("0.00") if linea_anterior is None else _total_de_la_linea(linea_anterior, vinculo)
    )
    categorias = []
    for bloque in bloques:
        ahora = actual["bloques"][bloque]["categorias"]
        antes = {c["categoria_id"]: c for c in anterior["bloques"][bloque]["categorias"]}
        vistas = set()
        for c in ahora:
            vistas.add(c["categoria_id"])
            previo = antes.get(c["categoria_id"])
            categorias.append(
                (bloque, c, c["importe"], "0.00" if previo is None else previo["importe"])
            )
        for c in anterior["bloques"][bloque]["categorias"]:
            if c["categoria_id"] not in vistas:
                categorias.append((bloque, c, "0.00", c["importe"]))
    return {
        "liquidacion_id": anterior["liquidacion_id"],
        "periodo": anterior["periodo"],
        "total_anterior": total_anterior.a_texto(),
        "diferencia_total": (total - total_anterior).a_texto(),
        "categorias": [
            {
                "categoria_id": c["categoria_id"],
                "nombre": c["nombre"],
                "bloque": bloque,
                "importe": importe,
                "importe_anterior": previo,
                "diferencia": (Dinero(importe) - Dinero(previo)).a_texto(),
            }
            for bloque, c, importe, previo in categorias
        ],
    }


def detalle_de_la_unidad(
    sesion: Session,
    *,
    complejo_id: UUID,
    unidad_id: UUID,
    liquidacion_id: UUID,
    vinculo: str,
    identidad_persona_id: UUID,
    request_id: UUID,
) -> dict[str, Any]:
    """El detalle de la expensa de la unidad. Distribuye al abrir si estaba emitida (origen
    `portal`, idempotente: el primero gana). `NoEncontrado` si no existe, es de otro edificio,
    está anulada o la unidad no figura en ella."""
    liquidada = leer_liquidacion(sesion, complejo_id=complejo_id, liquidacion_id=liquidacion_id)
    if liquidada is None or liquidada["estado"] not in _VIGENTES:
        raise NoEncontrado
    linea = _linea(liquidada, unidad_id)
    if linea is None:
        raise NoEncontrado
    if liquidada["estado"] == EMITIDA:
        try:
            registrar_distribucion(
                sesion,
                emision_id=UUID(liquidada["emision_id"]),
                origen="portal",
                persona_id=identidad_persona_id,
                request_id=request_id,
            )
        except Conflicto:  # se anuló mientras esperaba el candado
            raise NoEncontrado from None
    propietario = vinculo != INQUILINO
    cargos = linea["cargos_particulares"]
    total = _total_de_la_linea(linea, vinculo)
    anterior = _anterior(sesion, complejo_id=complejo_id, periodo=liquidada["periodo"])
    detalle: dict[str, Any] = {
        "liquidacion_id": liquidada["liquidacion_id"],
        "complejo_id": str(complejo_id),
        "unidad_id": str(unidad_id),
        "identificador": linea["identificador"],
        "periodo": liquidada["periodo"],
        "vencimiento": liquidada["vencimiento"],
        "vinculo": vinculo,
        "bloques": {
            b: liquidada["bloques"][b]
            for b in (("ordinario", "extraordinario") if propietario else ("ordinario",))
        },
    }
    partes = {g["grupo_id"]: g for g in linea["por_grupo"]}
    detalle["grupos"] = [
        {
            "grupo_id": g["grupo_id"],
            "nombre": g["nombre"],
            "ordinaria": partes[g["grupo_id"]]["ordinaria"],
            **({"extraordinaria": partes[g["grupo_id"]]["extraordinaria"]} if propietario else {}),
        }
        for g in liquidada["grupos"]
        if g["grupo_id"] in partes
    ]
    detalle["ordinaria"] = linea["ordinaria"]
    detalle["cargos_particulares"] = [
        {"concepto": c["concepto"], "importe": c["importe"]} for c in cargos
    ]
    detalle["fondo_de_reserva"] = linea["fondo_de_reserva"]
    if propietario:
        detalle["extraordinaria"] = linea["extraordinaria"]
    detalle["intereses"] = linea["intereses"]
    detalle["total"] = total.a_texto()
    detalle["comparacion"] = None
    if anterior is not None:
        detalle["comparacion"] = _comparacion(
            liquidada, anterior, _linea(anterior, unidad_id), total, vinculo
        )
    return detalle
