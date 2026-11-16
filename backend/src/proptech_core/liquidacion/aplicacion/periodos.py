"""El estado de los períodos de un edificio, para quien lo necesite sin importar el libro.

`es_periodo_emitido` es el adaptador real del puerto `PeriodoEmitidoFn` de `gastos` (P36, D-141):
lee el libro por la `aplicacion` de `cuenta_corriente`. Lo inyecta `proptech_api` en la ruta de
aprobar un gasto, así `gastos` no importa `liquidacion`.
"""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.cuenta_corriente.aplicacion.liquidar import periodos_emitidos


def es_periodo_emitido(sesion: Session, complejo_id: UUID, periodo: date) -> bool:
    """Una emisión sin evento `anulada` en el libro (una anulada no cuenta)."""
    return periodo in periodos_emitidos(sesion, complejo_id=complejo_id)
