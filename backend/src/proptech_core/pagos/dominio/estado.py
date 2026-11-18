"""El estado de un pago se deriva de sus eventos (E2): sin eventos está `informado`.

Un pago `reimputado` sigue confirmado (se movió su imputación, no se deshizo); `revertido` y
`rechazado` son finales.
"""

from collections.abc import Sequence

INFORMADO = "informado"
_POR_EVENTO = {
    "confirmado": "confirmado",
    "reimputado": "confirmado",
    "rechazado": "rechazado",
    "revertido": "revertido",
}


def estado_del_pago(tipos_en_orden: Sequence[str]) -> str:
    """`tipos_en_orden`: los tipos de evento del pago, del más viejo al más nuevo."""
    return _POR_EVENTO[tipos_en_orden[-1]] if tipos_en_orden else INFORMADO
