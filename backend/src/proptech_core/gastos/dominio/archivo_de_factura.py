"""El archivo de una factura (H-036, D-169): JPEG, PNG o PDF de hasta 10 MB.

Mismo criterio que el comprobante de un pago (8, E2): el tipo sale de los primeros bytes (la firma
del formato), nunca del nombre del archivo ni del `content-type` que declara el cliente. Se repite
acá y no se importa de `pagos` porque los módulos no se llaman por su dominio (fronteras de
módulos).
"""

from __future__ import annotations

TAMANO_MAXIMO = 10 * 1024 * 1024
TIPOS_MIME = {"jpeg": "image/jpeg", "png": "image/png", "pdf": "application/pdf"}

_FIRMAS = (
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"%PDF-", "pdf"),
)


class ArchivoInvalido(ValueError):
    """No es un JPEG, un PNG ni un PDF, está vacío o pasa de 10 MB."""


def tipo_de_archivo(contenido: bytes) -> str:
    if not contenido or len(contenido) > TAMANO_MAXIMO:
        raise ArchivoInvalido
    for firma, tipo in _FIRMAS:
        if contenido.startswith(firma):
            return tipo
    raise ArchivoInvalido
