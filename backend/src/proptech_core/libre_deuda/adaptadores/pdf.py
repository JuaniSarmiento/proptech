"""El adaptador real que convierte el HTML del certificado en PDF (H-041): WeasyPrint.

El HTML sale de `dominio/certificado.py`, ya escapado y sin recursos externos. Igual se corta
cualquier intento de bajar algo de afuera: el PDF se arma sólo con lo guardado.
"""

from typing import Any

from weasyprint import HTML  # type: ignore[import-untyped]


def _sin_recursos_externos(url: str, *_args: Any, **_kwargs: Any) -> Any:
    raise ValueError("el PDF del certificado no carga recursos externos")


def renderizar_con_weasyprint(html: str) -> bytes:
    contenido = HTML(string=html, url_fetcher=_sin_recursos_externos).write_pdf()
    if contenido is None:  # pragma: no cover - sin `target`, WeasyPrint devuelve los bytes
        raise ValueError("WeasyPrint no devolvió el PDF")
    return bytes(contenido)
