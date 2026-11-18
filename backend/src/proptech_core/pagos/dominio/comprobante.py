"""El comprobante de una transferencia (E2): JPEG, PNG o PDF de hasta 10 MB.

El tipo sale de los primeros bytes (la firma del formato), nunca del nombre del archivo ni del
`content-type` que declara el cliente.
"""

TAMANO_MAXIMO = 10 * 1024 * 1024

_FIRMAS = (
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"%PDF-", "pdf"),
)


class ComprobanteInvalido(ValueError):
    """No es un JPEG, un PNG ni un PDF, está vacío o pasa de 10 MB."""


def tipo_de_comprobante(contenido: bytes) -> str:
    if not contenido or len(contenido) > TAMANO_MAXIMO:
        raise ComprobanteInvalido
    for firma, tipo in _FIRMAS:
        if contenido.startswith(firma):
            return tipo
    raise ComprobanteInvalido
