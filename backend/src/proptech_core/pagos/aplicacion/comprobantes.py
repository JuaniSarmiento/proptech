"""Subir el comprobante de una transferencia (E2, H-018) y leerlo con IA (E5, H-019, D-164).

El tipo sale de los primeros bytes. Si hay un lector, se le pide la propuesta con un tope: si
falla o se pasa, la lectura es `fallida`; sin lector, `sin_ia`. La propuesta de la IA se valida
campo por campo y nunca crea un pago: quien informa el pago es siempre una persona (E3).
"""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.pagos.aplicacion.errores import EntradaInvalida
from proptech_core.pagos.dominio.comprobante import ComprobanteInvalido, tipo_de_comprobante
from proptech_core.pagos.dominio.propuesta import PROPUESTA_VACIA, validar_propuesta
from proptech_core.pagos.puertos import LectorDeComprobantes

LECTURA_SIN_IA = "sin_ia"
LECTURA_OK = "ok"
LECTURA_FALLIDA = "fallida"
TOPE_DE_LECTURA_S = 20.0
TIPOS_MIME = {"jpeg": "image/jpeg", "png": "image/png", "pdf": "application/pdf"}
#: Los hilos de la lectura: el tope los abandona pero el timeout del cliente HTTP los termina.
_HILOS = ThreadPoolExecutor(max_workers=8, thread_name_prefix="lectura-de-comprobantes")


def _leer_con_ia(
    lector: LectorDeComprobantes | None, contenido: bytes, tipo: str, tope: float, hoy: date
) -> tuple[str, dict[str, str | None] | None]:
    """`(lectura, propuesta validada)`; la propuesta es `None` si no hubo lectura."""
    if lector is None:
        return LECTURA_SIN_IA, None
    try:
        cruda = _HILOS.submit(lector.leer, contenido, TIPOS_MIME[tipo]).result(timeout=tope)
    except Exception:
        return LECTURA_FALLIDA, None
    return LECTURA_OK, validar_propuesta(cruda, hoy)


def guardar_comprobante(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    contenido: bytes,
    lector: LectorDeComprobantes | None = None,
    tope: float = TOPE_DE_LECTURA_S,
    hoy: date,
) -> dict[str, Any]:
    try:
        tipo = tipo_de_comprobante(contenido)
    except ComprobanteInvalido:
        raise EntradaInvalida("archivo") from None
    lectura, propuesta = _leer_con_ia(lector, contenido, tipo, tope, hoy)
    comprobante_id = sesion.execute(
        text(
            "INSERT INTO comprobante_de_pago (administracion_id, complejo_id, contenido, sha256, "
            "tipo, tamano, subido_por, lectura, propuesta) "
            "VALUES (:adm, :c, :contenido, :sha, :tipo, :tamano, :persona, :lectura, "
            "CAST(:propuesta AS jsonb)) RETURNING id"
        ),
        {
            "adm": identidad.administracion_id,
            "c": complejo_id,
            "contenido": contenido,
            "sha": hashlib.sha256(contenido).hexdigest(),
            "tipo": tipo,
            "tamano": len(contenido),
            "persona": identidad.persona_id,
            "lectura": lectura,
            "propuesta": None if propuesta is None else json.dumps(propuesta),
        },
    ).scalar_one()
    return {
        "comprobante_id": str(comprobante_id),
        "lectura": lectura,
        "propuesta": dict(PROPUESTA_VACIA) if propuesta is None else propuesta,
    }
