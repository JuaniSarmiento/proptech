"""El adaptador real que convierte el HTML de la expensa en PDF (7, H-015, E12): WeasyPrint.

El HTML sale de `dominio/documento.py`, ya escapado y sin recursos externos. Igual se corta
cualquier intento de bajar algo de afuera (una imagen, una hoja de estilos): el PDF de una expensa
se arma sólo con lo guardado, nunca con lo que haya en una dirección.
"""

from typing import Any

from weasyprint import HTML  # type: ignore[import-untyped]


def _sin_recursos_externos(url: str, *_args: Any, **_kwargs: Any) -> Any:
    raise ValueError("el PDF de la expensa no carga recursos externos")


def renderizar_con_weasyprint(html: str) -> bytes:
    contenido = HTML(string=html, url_fetcher=_sin_recursos_externos).write_pdf()
    if contenido is None:  # pragma: no cover - sin `target`, WeasyPrint devuelve los bytes
        raise ValueError("WeasyPrint no devolvió el PDF")
    return bytes(contenido)
