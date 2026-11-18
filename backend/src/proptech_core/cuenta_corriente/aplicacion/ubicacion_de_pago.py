"""Dónde está hoy la plata de un pago (H-026): la unidad de la cuenta donde quedó el último crédito.

Sólo lee. El libro es el único que sabe qué movimiento de cada parte está vigente: el crédito `pago`
de una parte lo corrige, al reimputar, un débito `reimputacion` (`corrige_a`), y el crédito que se
acredita en el destino queda enlazado a ese débito (`enlazado_a`). Se sigue esa cadena hasta el
último crédito. Después de revertir, el último crédito sigue siendo el de la última unidad donde
estuvo.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

_IDS = bindparam("ids", type_=ARRAY(PG_UUID(as_uuid=True)))


def unidades_vigentes(sesion: Session, movimiento_ids: Sequence[UUID]) -> dict[UUID, UUID]:
    """De los movimientos de un pago (los `pago` y los `reimputacion`, créditos y débitos), la
    unidad donde está hoy cada parte: `{unidad original: unidad vigente}`."""
    if not movimiento_ids:
        return {}
    filas = sesion.execute(
        text(
            "SELECT m.id, m.tipo, m.sentido, m.corrige_a, m.enlazado_a, c.unidad_id "
            "FROM movimiento m JOIN cuenta c ON c.id = m.cuenta_id WHERE m.id = ANY(:ids)"
        ).bindparams(_IDS),
        {"ids": list(movimiento_ids)},
    ).all()
    debito_que_corrige = {
        UUID(str(f.corrige_a)): UUID(str(f.id))
        for f in filas
        if f.tipo == "reimputacion" and f.sentido == "debito" and f.corrige_a is not None
    }
    # débito de reimputación → (crédito que acreditó el destino, unidad del destino)
    credito_del_destino = {
        UUID(str(f.enlazado_a)): (UUID(str(f.id)), UUID(str(f.unidad_id)))
        for f in filas
        if f.tipo == "reimputacion" and f.sentido == "credito" and f.enlazado_a is not None
    }
    resultado: dict[UUID, UUID] = {}
    for fila in filas:
        if fila.tipo != "pago" or fila.sentido != "credito":
            continue
        origen = actual = UUID(str(fila.unidad_id))
        credito = UUID(str(fila.id))
        while True:
            debito = debito_que_corrige.get(credito)
            destino = None if debito is None else credito_del_destino.get(debito)
            if destino is None:
                break
            credito, actual = destino
        resultado[origen] = actual
    return resultado
