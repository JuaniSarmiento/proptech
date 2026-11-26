"""Los certificados de libre deuda de una unidad y el PDF de cada uno (H-041, C05).

Leer no se audita. El listado pasa por la misma autorización que emitir (404 y 403 de D7); la
descarga por enlace firmado no tiene sesión: el token verificado es la autorización.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.libre_deuda.aplicacion.autorizacion import unidad_autorizada
from proptech_core.libre_deuda.aplicacion.certificado import Certificado


def _lista(valor: Any) -> tuple[dict[str, Any], ...]:
    return tuple(json.loads(valor) if isinstance(valor, str) else valor)


def listar_certificados(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID, unidad_id: UUID
) -> list[Certificado]:
    """El más nuevo primero. No trae los bytes del PDF."""
    unidad_autorizada(sesion, identidad, complejo_id, unidad_id)
    filas = sesion.execute(
        text(
            "SELECT id, unidad_id, fecha_de_corte, emitido_en, saldo::text AS saldo, "
            "capital::text AS capital, intereses::text AS intereses, "
            "interes_corrido::text AS interes_corrido, en_revision, vencen_despues, "
            "en_gestion_judicial, huella FROM certificado_de_libre_deuda "
            "WHERE unidad_id = :unidad ORDER BY emitido_en DESC, id DESC"
        ),
        {"unidad": unidad_id},
    ).all()
    return [
        Certificado(
            id=UUID(str(f.id)),
            unidad_id=UUID(str(f.unidad_id)),
            fecha_de_corte=f.fecha_de_corte,
            emitido_en=f.emitido_en,
            saldo=str(f.saldo),
            capital=str(f.capital),
            intereses=str(f.intereses),
            interes_corrido=str(f.interes_corrido),
            en_revision=_lista(f.en_revision),
            vencen_despues=_lista(f.vencen_despues),
            en_gestion_judicial=bool(f.en_gestion_judicial),
            huella=str(f.huella),
        )
        for f in filas
    ]


def pdf_del_certificado(sesion: Session, *, certificado_id: UUID) -> tuple[bytes, str] | None:
    """Los bytes guardados al emitir y el nombre del archivo, o `None` si no existe (en la
    administración de la sesión)."""
    fila = sesion.execute(
        text("SELECT pdf FROM certificado_de_libre_deuda WHERE id = :id"),
        {"id": certificado_id},
    ).first()
    if fila is None:
        return None
    return bytes(fila.pdf), f"libre-deuda-{certificado_id}.pdf"
