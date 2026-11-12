"""Aceptar las diferencias del borrador de saldos (design D6, D7, E6, E8).

Orden de chequeo (D7 del 2a): alcance (404) -> permiso (403) -> candado del complejo (`FOR UPDATE`,
E8) -> estado de la migración, borrador vigente, aceptación previa y diferencias (409). La
aceptación guarda quién, cuándo y la lista **exacta** de diferencias aceptadas; es de sólo agregar
y una por importación, así que un borrador nuevo (otra importación) no hereda la de uno anterior.
Se audita una vez.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.complejos.aplicacion.errores import Conflicto, NoEncontrado, transaccion
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.importacion.aplicacion.borrador import (
    AceptacionRegistrada,
    DiferenciaAceptada,
    borrador_vigente,
    comparar_importacion,
    leer_aceptacion,
)
from proptech_core.importacion.aplicacion.edificio import edificio_autorizado

__all__ = ["AceptacionRegistrada", "DiferenciaAceptada", "aceptar_diferencias"]


@accion_sensible(Accion.ACEPTAR_DIFERENCIAS_DE_SALDOS)
def aceptar_diferencias(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    importacion_id: UUID,
    reloj: Callable[[], datetime],
    request_id: UUID,
) -> AceptacionRegistrada:
    with transaccion(sesion, {}):
        edificio_autorizado(sesion, identidad, complejo_id, Accion.ACEPTAR_DIFERENCIAS_DE_SALDOS)
        # E8: el candado va antes de leer el estado, y el estado se lee ya con él puesto.
        edificio = cargar_complejo(sesion, complejo_id, bloquear=True)
        if edificio is None:
            raise NoEncontrado()
        if edificio.estado_migracion != "pendiente":
            raise Conflicto("estado_migracion")
        vigente = borrador_vigente(sesion, complejo_id)
        if vigente is None or vigente.importacion_id != importacion_id:
            raise Conflicto("importacion_id")
        if leer_aceptacion(sesion, importacion_id) is not None:
            raise Conflicto("aceptacion")
        comparacion = comparar_importacion(sesion, complejo_id, importacion_id)
        diferencias = tuple(
            DiferenciaAceptada(
                u.unidad, u.borrador.a_texto(), u.control.a_texto(), u.diferencia.a_texto()
            )
            for u in comparacion.unidades
            if u.diferencia.decimal != 0
        )
        if not diferencias:
            raise Conflicto("diferencias")
        aceptada_en = reloj()
        aceptacion_id = UUID(
            str(
                sesion.execute(
                    text(
                        "INSERT INTO aceptacion_de_diferencias (administracion_id, complejo_id, "
                        "importacion_id, aceptada_por, aceptada_en, diferencias) "
                        "VALUES (:administracion, :complejo, :importacion, :persona, :en, "
                        "CAST(:diferencias AS jsonb)) RETURNING id"
                    ),
                    {
                        "administracion": identidad.administracion_id,
                        "complejo": complejo_id,
                        "importacion": importacion_id,
                        "persona": identidad.persona_id,
                        "en": aceptada_en,
                        "diferencias": json.dumps(
                            [
                                {
                                    "unidad": d.unidad,
                                    "borrador": d.borrador,
                                    "control": d.control,
                                    "diferencia": d.diferencia,
                                }
                                for d in diferencias
                            ]
                        ),
                    },
                ).scalar_one()
            )
        )
        registrar(
            sesion,
            identidad,
            Accion.ACEPTAR_DIFERENCIAS_DE_SALDOS,
            entidad="aceptacion_de_diferencias",
            entidad_id=aceptacion_id,
            request_id=request_id,
            detalle={
                "complejo_id": str(complejo_id),
                "importacion_id": str(importacion_id),
                "unidades_con_diferencia": len(diferencias),
            },
        )
    return AceptacionRegistrada(
        aceptacion_id=aceptacion_id,
        diferencias=diferencias,
        aceptada_por=identidad.persona_id,
        aceptada_en=aceptada_en,
    )
