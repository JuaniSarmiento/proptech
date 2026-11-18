"""Subir el comprobante de una transferencia (E2, H-018): se guarda sin leerlo todavía.

`lectura` queda en `sin_ia` y la propuesta vacía mientras no haya un lector configurado (H-019).
Nada de lo que trae el archivo se interpreta acá: el tipo sale de sus primeros bytes.
"""

import hashlib
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.pagos.aplicacion.errores import EntradaInvalida
from proptech_core.pagos.dominio.comprobante import ComprobanteInvalido, tipo_de_comprobante

LECTURA_SIN_IA = "sin_ia"
_PROPUESTA_VACIA = {
    "banco": None,
    "numero_de_operacion": None,
    "fecha": None,
    "monto": None,
    "cbu_origen": None,
}


def guardar_comprobante(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID, contenido: bytes
) -> dict[str, Any]:
    try:
        tipo = tipo_de_comprobante(contenido)
    except ComprobanteInvalido:
        raise EntradaInvalida("archivo") from None
    comprobante_id = sesion.execute(
        text(
            "INSERT INTO comprobante_de_pago (administracion_id, complejo_id, contenido, sha256, "
            "tipo, tamano, subido_por, lectura) "
            "VALUES (:adm, :c, :contenido, :sha, :tipo, :tamano, :persona, :lectura) RETURNING id"
        ),
        {
            "adm": identidad.administracion_id,
            "c": complejo_id,
            "contenido": contenido,
            "sha": hashlib.sha256(contenido).hexdigest(),
            "tipo": tipo,
            "tamano": len(contenido),
            "persona": identidad.persona_id,
            "lectura": LECTURA_SIN_IA,
        },
    ).scalar_one()
    return {
        "comprobante_id": str(comprobante_id),
        "lectura": LECTURA_SIN_IA,
        "propuesta": dict(_PROPUESTA_VACIA),
    }
