"""Subir una factura y dejar el gasto en borrador con lo que trae su QR de ARCA (R12, H-036, D-169).

El tipo del archivo sale de los primeros bytes. Con un QR legible y válido el borrador lleva el
proveedor (por CUIT, creado si no existe), los cuatro datos de la factura, su fecha, el receptor y
el importe en pesos; sin eso (`sin_qr`, con su motivo) no lleva ningún dato del QR, ni a medias. Lo
que el QR no trae (concepto, categoría, grupo y período) queda vacío: lo completa la IA (H-037) o la
persona, y un gasto así no se aprueba. El archivo se guarda tal como llegó. Nada toca el libro.
"""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.dominio.eventos import EventoDelGasto
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.gastos.aplicacion import proveedores
from proptech_core.gastos.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
    transaccion,
)
from proptech_core.gastos.aplicacion.gastos import _aviso_de_receptor_distinto, cargar_gasto
from proptech_core.gastos.dominio.archivo_de_factura import ArchivoInvalido, tipo_de_archivo
from proptech_core.gastos.dominio.factura_qr import (
    MOTIVO_NO_HAY_QR,
    DatosDelQr,
    QrDescartado,
    interpretar_qr,
)
from proptech_core.gastos.puertos import LectorDeQr

_CONFLICTOS = {"uq_gasto_factura": "factura"}


def _leer_el_qr(lector: LectorDeQr, contenido: bytes, tipo: str) -> tuple[DatosDelQr | None, str]:
    """`(datos, "")` si algún QR del archivo sirve; si no, `(None, motivo)` con el del primero."""
    try:
        textos = lector.leer(contenido, tipo)
    except Exception:
        textos = []
    motivo = MOTIVO_NO_HAY_QR
    for posicion, texto in enumerate(textos):
        try:
            return interpretar_qr(texto), ""
        except QrDescartado as descartado:
            if posicion == 0:
                motivo = descartado.motivo
    return None, motivo


def _id_del_proveedor(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID, cuit: str, request_id: UUID
) -> UUID:
    """El proveedor del edificio con ese CUIT, creado como en el 6 (y auditado) si no existe."""
    consulta = text("SELECT id FROM proveedor WHERE complejo_id=:c AND cuit=:cuit")
    existente = sesion.execute(consulta, {"c": complejo_id, "cuit": cuit}).scalar_one_or_none()
    if existente is not None:
        return UUID(str(existente))
    try:
        return proveedores.crear_proveedor(
            sesion,
            identidad,
            complejo_id=complejo_id,
            datos={"razon_social": f"CUIT {cuit}", "cuit": cuit},
            request_id=request_id,
        )
    except Conflicto:
        # Otro pedido lo creó en el medio: el único por edificio y CUIT lo frena la base.
        return UUID(str(sesion.execute(consulta, {"c": complejo_id, "cuit": cuit}).scalar_one()))


def _ya_esta_cargada(sesion: Session, complejo_id: UUID, datos: DatosDelQr) -> bool:
    return (
        sesion.execute(
            text(
                "SELECT 1 FROM gasto WHERE complejo_id=:c AND cuit_emisor=:cuit "
                "AND punto_de_venta=:pv AND tipo_de_comprobante=:tipo "
                "AND numero_de_comprobante=:numero"
            ),
            {
                "c": complejo_id,
                "cuit": datos.cuit,
                "pv": datos.punto_de_venta,
                "tipo": datos.tipo_de_comprobante,
                "numero": datos.numero_de_comprobante,
            },
        ).first()
        is not None
    )


def subir_factura(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    contenido: bytes,
    lector: LectorDeQr,
    request_id: UUID,
) -> tuple[dict[str, Any], str | None]:
    """`(el gasto en borrador, aviso de receptor distinto)`. 422 si el archivo no es una factura
    subible; 409 si es la misma factura de otro gasto del edificio (`factura`)."""
    try:
        tipo = tipo_de_archivo(contenido)
    except ArchivoInvalido:
        raise EntradaInvalida("archivo") from None
    datos, motivo = _leer_el_qr(lector, contenido, tipo)
    aviso = None
    if datos is not None:
        # Antes de crear el proveedor: la factura repetida no deja nada (el índice único lo frena
        # igual).
        if _ya_esta_cargada(sesion, complejo_id, datos):
            raise Conflicto("factura")
        aviso = _aviso_de_receptor_distinto(sesion, complejo_id, datos.documento_receptor)
    with transaccion(sesion, _CONFLICTOS):
        proveedor_id = (
            None
            if datos is None
            else _id_del_proveedor(
                sesion, identidad, complejo_id=complejo_id, cuit=datos.cuit, request_id=request_id
            )
        )
        gasto_id = UUID(
            str(
                sesion.execute(
                    text(
                        "INSERT INTO gasto (administracion_id, complejo_id, proveedor_id, tipo, "
                        "importe, cuit_emisor, punto_de_venta, tipo_de_comprobante, "
                        "numero_de_comprobante, documento_receptor, fecha_de_factura, origen, "
                        "motivo_sin_qr) VALUES (:admin, :complejo, :proveedor, 'ordinario', "
                        ":importe, :cuit, :pv, :tipo, :numero, :receptor, :fecha, :origen, "
                        ":motivo) RETURNING id"
                    ),
                    {
                        "admin": identidad.administracion_id,
                        "complejo": complejo_id,
                        "proveedor": proveedor_id,
                        "importe": None if datos is None else datos.importe.a_texto(),
                        "cuit": None if datos is None else datos.cuit,
                        "pv": None if datos is None else datos.punto_de_venta,
                        "tipo": None if datos is None else datos.tipo_de_comprobante,
                        "numero": None if datos is None else datos.numero_de_comprobante,
                        "receptor": None if datos is None else datos.documento_receptor,
                        "fecha": None if datos is None else datos.fecha,
                        "origen": "sin_qr" if datos is None else "qr",
                        "motivo": motivo if datos is None else None,
                    },
                ).scalar_one()
            )
        )
        sesion.execute(
            text(
                "INSERT INTO factura_de_gasto (administracion_id, complejo_id, gasto_id, "
                "contenido, sha256, tipo, tamano, subido_por) VALUES (:admin, :complejo, :gasto, "
                ":contenido, :sha, :tipo, :tamano, :persona)"
            ),
            {
                "admin": identidad.administracion_id,
                "complejo": complejo_id,
                "gasto": gasto_id,
                "contenido": contenido,
                "sha": hashlib.sha256(contenido).hexdigest(),
                "tipo": tipo,
                "tamano": len(contenido),
                "persona": identidad.persona_id,
            },
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
    gasto = cargar_gasto(sesion, gasto_id)
    if gasto is None:
        raise NoEncontrado
    return gasto, aviso


def factura_del_gasto(sesion: Session, *, gasto_id: UUID) -> tuple[bytes, str] | None:
    """Los bytes y el tipo de la factura de un gasto, o `None` si no tiene (se cargó a mano) o no
    existe en la administración de la sesión (RLS). Quién puede pedirla lo decide quien llama."""
    fila = sesion.execute(
        text("SELECT contenido, tipo FROM factura_de_gasto WHERE gasto_id = :g"), {"g": gasto_id}
    ).first()
    return None if fila is None else (bytes(fila.contenido), str(fila.tipo))
