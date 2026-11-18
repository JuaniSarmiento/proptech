"""Informar un pago (E2 a E4, D-163, D-165): el pago queda `informado` y no toca el libro.

Orden de lo que decide la base: el comprobante (422 `comprobante_id`), las unidades (404) y, por
último, el número de operación (409 `repetido`), que frena la propia base con un trigger bajo
candado (D-165): dos pedidos simultáneos con el mismo banco y número no pasan los dos.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.complejos.aplicacion.lectura import cargar_unidad
from proptech_core.pagos.aplicacion.errores import Conflicto, EntradaInvalida, NoEncontrado
from proptech_core.pagos.dominio.pedido import PedidoDePago, PedidoInvalido, pedido_de_pago

#: Las dos restricciones que la base puede levantar al insertar (`0044`).
_NUMERO_REPETIDO = "uq_pago_numero_por_edificio"
_COMPROBANTE_USADO = "uq_pago_comprobante"


def _comprobante_utilizable(
    sesion: Session, identidad: Identidad, complejo_id: UUID, texto: str
) -> UUID:
    """Un comprobante subido por la misma persona, del mismo edificio y todavía sin pago. Si no
    existe, es de otro edificio u otra administración (la RLS ya lo esconde), lo subió otra
    persona o ya se usó: es el mismo 422, sin decir cuál."""
    try:
        comprobante_id = UUID(texto)
    except ValueError:
        raise EntradaInvalida("comprobante_id") from None
    libre = sesion.execute(
        text(
            "SELECT 1 FROM comprobante_de_pago c WHERE c.id = :id AND c.complejo_id = :c "
            "AND c.subido_por = :persona AND NOT EXISTS "
            "(SELECT 1 FROM pago_informado p WHERE p.comprobante_id = c.id)"
        ),
        {"id": comprobante_id, "c": complejo_id, "persona": identidad.persona_id},
    ).first()
    if libre is None:
        raise EntradaInvalida("comprobante_id")
    return comprobante_id


def _verificar_unidades(
    sesion: Session, complejo_id: UUID, pedido: PedidoDePago, permitidas: frozenset[UUID] | None
) -> None:
    for parte in pedido.partes:
        unidad_id = UUID(parte.unidad_id)
        unidad = cargar_unidad(sesion, unidad_id)
        if unidad is None or unidad.complejo_id != complejo_id:
            raise NoEncontrado
        if permitidas is not None and unidad_id not in permitidas:
            raise NoEncontrado


def informar_pago(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    cuerpo: Any,
    hoy: date,
    unidades_permitidas: frozenset[UUID] | None,
) -> UUID:
    """`unidades_permitidas`: las unidades por las que puede informar un vecino; `None` para el
    personal con `confirmar_pago_informado`, que informa por cualquiera del edificio."""
    try:
        pedido = pedido_de_pago(cuerpo, hoy)
    except PedidoInvalido as error:
        raise EntradaInvalida(error.campo) from None
    comprobante_id = _comprobante_utilizable(sesion, identidad, complejo_id, pedido.comprobante_id)
    _verificar_unidades(sesion, complejo_id, pedido, unidades_permitidas)
    try:
        with sesion.begin_nested():
            pago_id = sesion.execute(
                text(
                    "INSERT INTO pago_informado (administracion_id, complejo_id, comprobante_id, "
                    "banco, banco_normalizado, numero_de_operacion, numero_normalizado, "
                    "fecha_de_transferencia, monto, cbu_origen, informado_por) "
                    "VALUES (:adm, :c, :comprobante, :banco, :banco_n, :numero, :numero_n, "
                    ":fecha, CAST(:monto AS numeric), :cbu, :persona) RETURNING id"
                ),
                {
                    "adm": identidad.administracion_id,
                    "c": complejo_id,
                    "comprobante": comprobante_id,
                    "banco": pedido.banco,
                    "banco_n": pedido.banco_normalizado,
                    "numero": pedido.numero_de_operacion,
                    "numero_n": pedido.numero_normalizado,
                    "fecha": pedido.fecha_de_transferencia,
                    "monto": pedido.monto.a_texto(),
                    "cbu": pedido.cbu_origen,
                    "persona": identidad.persona_id,
                },
            ).scalar_one()
            for parte in pedido.partes:
                sesion.execute(
                    text(
                        "INSERT INTO parte_de_pago (administracion_id, complejo_id, pago_id, "
                        "unidad_id, importe) VALUES (:adm, :c, :pago, :unidad, "
                        "CAST(:importe AS numeric))"
                    ),
                    {
                        "adm": identidad.administracion_id,
                        "c": complejo_id,
                        "pago": pago_id,
                        "unidad": UUID(parte.unidad_id),
                        "importe": parte.importe.a_texto(),
                    },
                )
    except IntegrityError as error:
        restriccion = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if restriccion == _NUMERO_REPETIDO:
            raise Conflicto("numero_de_operacion", "repetido") from None
        if restriccion == _COMPROBANTE_USADO:
            raise EntradaInvalida("comprobante_id") from None
        raise
    return UUID(str(pago_id))
