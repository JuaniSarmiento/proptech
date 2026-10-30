"""Notas de crédito (R22, D-061, D-082, D5 del design): el tope se
garantiza con `FOR UPDATE` sobre la factura, no con un `CHECK` — dos
pedidos concurrentes se serializan sobre la misma fila de `gasto`.
"""

from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.eventos import EventoDelGasto
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.gastos.aplicacion.errores import (
    EntradaInvalida,
    NoEncontrado,
    error_de_validacion,
    transaccion,
)
from proptech_core.gastos.dominio.gasto import CAMPOS_DE_FACTURA
from proptech_core.gastos.dominio.nota_de_credito import DatosNotaDeCredito

_CONFLICTOS = {"uq_nota_factura": "factura"}


def cargar_nota_de_credito(sesion: Session, nota_id: UUID) -> dict[str, Any] | None:
    fila = (
        sesion.execute(
            text(
                "SELECT n.id, n.complejo_id, n.gasto_id, n.importe::text AS importe, "
                "n.periodo, g.periodo AS periodo_de_la_factura, n.cuit_emisor, "
                "n.punto_de_venta, n.tipo_de_comprobante, n.numero_de_comprobante "
                "FROM nota_de_credito n JOIN gasto g ON g.id = n.gasto_id "
                "AND g.administracion_id = n.administracion_id WHERE n.id=:id"
            ),
            {"id": nota_id},
        )
        .mappings()
        .first()
    )
    return None if fila is None else dict(fila)


@accion_sensible(EventoDelGasto.CARGAR_NOTA_DE_CREDITO)
def crear_nota_de_credito(
    sesion: Session,
    identidad: Identidad,
    *,
    gasto_id: UUID,
    datos: dict[str, Any],
    request_id: UUID,
) -> UUID:
    try:
        entrada = DatosNotaDeCredito.model_validate(datos)
    except ValidationError as error:
        raise error_de_validacion(error) from None
    with transaccion(sesion, _CONFLICTOS):
        #: D5: bloquea la factura antes de sumar sus notas existentes — la
        #: carrera entre dos notas simultáneas se serializa acá.
        factura = (
            sesion.execute(
                text(
                    "SELECT complejo_id, importe::text AS importe, cuit_emisor, "
                    "punto_de_venta, tipo_de_comprobante, numero_de_comprobante "
                    "FROM gasto WHERE id=:id FOR UPDATE"
                ),
                {"id": gasto_id},
            )
            .mappings()
            .first()
        )
        if factura is None:
            raise NoEncontrado()
        if any(factura[campo] is None for campo in CAMPOS_DE_FACTURA):
            #: Spec: toda nota de crédito corrige un gasto **con factura**.
            raise EntradaInvalida("gasto_id", "el gasto indicado no tiene factura")
        acreditado = Dinero(
            str(
                sesion.execute(
                    text(
                        "SELECT COALESCE(SUM(importe), 0)::text FROM nota_de_credito "
                        "WHERE gasto_id=:id"
                    ),
                    {"id": gasto_id},
                ).scalar_one()
            )
        )
        tope_restante = Dinero(factura["importe"]) - acreditado
        if entrada.importe > tope_restante:
            raise EntradaInvalida(
                "importe",
                f"supera el tope restante de la factura ({tope_restante.a_texto()})",
            )
        nota_id = UUID(
            str(
                sesion.execute(
                    text(
                        "INSERT INTO nota_de_credito (administracion_id, complejo_id, "
                        "gasto_id, importe, periodo, cuit_emisor, punto_de_venta, "
                        "tipo_de_comprobante, numero_de_comprobante) "
                        "VALUES (:admin, :complejo, :gasto_id, :importe, :periodo, "
                        ":cuit_emisor, :punto_de_venta, :tipo_de_comprobante, "
                        ":numero_de_comprobante) RETURNING id"
                    ),
                    {
                        "admin": identidad.administracion_id,
                        "complejo": factura["complejo_id"],
                        "gasto_id": gasto_id,
                        "importe": entrada.importe.a_texto(),
                        "periodo": entrada.periodo,
                        "cuit_emisor": entrada.cuit_emisor,
                        "punto_de_venta": entrada.punto_de_venta,
                        "tipo_de_comprobante": entrada.tipo_de_comprobante,
                        "numero_de_comprobante": entrada.numero_de_comprobante,
                    },
                ).scalar_one()
            )
        )
        registrar(
            sesion,
            identidad,
            EventoDelGasto.CARGAR_NOTA_DE_CREDITO,
            entidad="nota_de_credito",
            entidad_id=nota_id,
            request_id=request_id,
            detalle={"complejo_id": str(factura["complejo_id"]), "gasto_id": str(gasto_id)},
        )
    return nota_id
