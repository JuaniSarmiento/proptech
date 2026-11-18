"""Lo que `pagos` pide a la infraestructura: leer el comprobante (H-019, D-164)."""

from collections.abc import Mapping
from typing import Protocol


class LectorDeComprobantes(Protocol):
    def leer(self, contenido: bytes, tipo: str) -> Mapping[str, object]:
        """`tipo` es `image/jpeg`, `image/png` o `application/pdf`. Devuelve la propuesta **cruda**
        (`banco`, `numero_de_operacion`, `fecha`, `monto`, `cbu_origen`); puede lanzar."""
        ...
