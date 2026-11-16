"""Lo emitido, leído tal como se guardó (E2, E14): nunca se recalcula.

Cada lectura sale de las tablas de la `0041`: si después se renombra una categoría, se cambia el
fondo o se le cobra a una unidad, la respuesta no cambia.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero, sumar

_BLOQUES = ("ordinario", "extraordinario")


def _uuid(valor: Any) -> str:
    return str(valor)


def _json(valor: Any) -> Any:
    return json.loads(valor) if isinstance(valor, str) else valor


def liquidacion_de_la_emision(sesion: Session, emision_id: UUID) -> UUID | None:
    """El id de la liquidación de una emisión, o `None` (el replay de emitir)."""
    fila = sesion.execute(
        text("SELECT id FROM liquidacion WHERE emision_id = :e"), {"e": emision_id}
    ).scalar_one_or_none()
    return None if fila is None else UUID(str(fila))


def leer_liquidacion(
    sesion: Session, *, complejo_id: UUID, liquidacion_id: UUID
) -> dict[str, Any] | None:
    """`None` si no existe, es de otro edificio o de otra administración (RLS)."""
    cabecera = (
        sesion.execute(
            text(
                "SELECT id, emision_id, periodo, huella, version_de_configuracion_id, "
                "porcentaje_fondo::text AS porcentaje_fondo, vencimiento, vencimiento_original, "
                "motivo_del_vencimiento, total_gastos::text AS gastos, "
                "total_notas_de_credito::text AS notas_de_credito, "
                "total_fondo_de_reserva::text AS fondo_de_reserva, "
                "total_prorrateado::text AS prorrateado, "
                "total_cargos_particulares::text AS cargos_particulares, "
                "total_intereses::text AS intereses, total::text AS total, emitida_por, "
                "emitida_en FROM liquidacion WHERE id = :id AND complejo_id = :c"
            ),
            {"id": liquidacion_id, "c": complejo_id},
        )
        .mappings()
        .first()
    )
    if cabecera is None:
        return None
    parametros = {"l": liquidacion_id}
    categorias = (
        sesion.execute(
            text(
                "SELECT bloque, categoria_id, nombre, importe::text AS importe, "
                "porcentaje::text AS porcentaje FROM categoria_de_liquidacion "
                "WHERE liquidacion_id = :l ORDER BY bloque, orden"
            ),
            parametros,
        )
        .mappings()
        .all()
    )
    bloques: dict[str, Any] = {}
    for bloque in _BLOQUES:
        propias = [c for c in categorias if c["bloque"] == bloque]
        bloques[bloque] = {
            "subtotal": sumar(Dinero(c["importe"]) for c in propias).a_texto(),
            "categorias": [
                {
                    "categoria_id": _uuid(c["categoria_id"]),
                    "nombre": c["nombre"],
                    "importe": c["importe"],
                    "porcentaje": c["porcentaje"],
                }
                for c in propias
            ],
        }
    composiciones: dict[str, list[dict[str, str]]] = {}
    for c in (
        sesion.execute(
            text(
                "SELECT grupo_id, unidad_id, coeficiente::text AS coeficiente "
                "FROM composicion_de_grupo WHERE liquidacion_id = :l ORDER BY grupo_id, orden"
            ),
            parametros,
        )
        .mappings()
        .all()
    ):
        composiciones.setdefault(_uuid(c["grupo_id"]), []).append(
            {"unidad_id": _uuid(c["unidad_id"]), "coeficiente": c["coeficiente"]}
        )
    grupos = [
        {
            "grupo_id": _uuid(g["grupo_id"]),
            "nombre": g["nombre"],
            "metodo": g["metodo"],
            "ordinario": g["ordinario"],
            "extraordinario": g["extraordinario"],
            "composicion": composiciones.get(_uuid(g["grupo_id"]), []),
        }
        for g in sesion.execute(
            text(
                "SELECT grupo_id, nombre, metodo, ordinario::text AS ordinario, "
                "extraordinario::text AS extraordinario FROM grupo_de_liquidacion "
                "WHERE liquidacion_id = :l ORDER BY orden"
            ),
            parametros,
        )
        .mappings()
        .all()
    ]
    unidades = [
        {
            "unidad_id": _uuid(u["unidad_id"]),
            "identificador": u["identificador"],
            "ordinaria": u["ordinaria"],
            "fondo_de_reserva": u["fondo_de_reserva"],
            "extraordinaria": u["extraordinaria"],
            "cargos_particulares": _json(u["cargos_particulares"]),
            "intereses": u["intereses"],
            "total": u["total"],
            "sin_obligacion": bool(u["sin_obligacion"]),
            "por_grupo": _json(u["por_grupo"]),
            "saldo_anterior": u["saldo_anterior"],
        }
        for u in sesion.execute(
            text(
                "SELECT unidad_id, identificador, ordinaria::text AS ordinaria, "
                "fondo_de_reserva::text AS fondo_de_reserva, "
                "extraordinaria::text AS extraordinaria, "
                "intereses::text AS intereses, total::text AS total, sin_obligacion, "
                "saldo_anterior::text AS saldo_anterior, cargos_particulares, por_grupo "
                "FROM linea_de_liquidacion WHERE liquidacion_id = :l ORDER BY orden"
            ),
            parametros,
        )
        .mappings()
        .all()
    ]
    alertas = [
        {
            "codigo": a["codigo"],
            "aceptada_por": _uuid(a["aceptada_por"]),
            "aceptada_en": a["aceptada_en"].isoformat(),
        }
        for a in sesion.execute(
            text(
                "SELECT codigo, aceptada_por, aceptada_en FROM alerta_aceptada "
                "WHERE liquidacion_id = :l ORDER BY codigo"
            ),
            parametros,
        )
        .mappings()
        .all()
    ]
    original = cabecera["vencimiento_original"]
    return {
        "liquidacion_id": _uuid(cabecera["id"]),
        "emision_id": _uuid(cabecera["emision_id"]),
        "periodo": cabecera["periodo"].isoformat(),
        "estado": "emitida",
        "huella": cabecera["huella"],
        "version_de_configuracion_id": _uuid(cabecera["version_de_configuracion_id"]),
        "porcentaje_fondo": cabecera["porcentaje_fondo"],
        "vencimiento": cabecera["vencimiento"].isoformat(),
        "vencimiento_original": None if original is None else original.isoformat(),
        "motivo_del_vencimiento": cabecera["motivo_del_vencimiento"],
        "emitida_por": _uuid(cabecera["emitida_por"]),
        "emitida_en": cabecera["emitida_en"].isoformat(),
        "totales": {
            clave: cabecera[clave]
            for clave in (
                "gastos",
                "notas_de_credito",
                "fondo_de_reserva",
                "prorrateado",
                "cargos_particulares",
                "intereses",
                "total",
            )
        },
        "bloques": bloques,
        "grupos": grupos,
        "unidades": unidades,
        "alertas_aceptadas": alertas,
    }


def obligaciones_emitidas(liquidada: dict[str, Any]) -> list[dict[str, str]]:
    """Lo que recibió el libro de cada unidad: la ordinaria prorrateada más los cargos
    particulares (E15), el fondo y la extraordinaria; ninguna para una unidad sin obligación."""
    return [
        {
            "unidad_id": u["unidad_id"],
            "identificador": u["identificador"],
            "ordinaria": (
                Dinero(u["ordinaria"])
                + sumar(Dinero(c["importe"]) for c in u["cargos_particulares"])
            ).a_texto(),
            "fondo_de_reserva": u["fondo_de_reserva"],
            "extraordinaria": u["extraordinaria"],
            "vencimiento": liquidada["vencimiento"],
        }
        for u in liquidada["unidades"]
        if not u["sin_obligacion"]
    ]
