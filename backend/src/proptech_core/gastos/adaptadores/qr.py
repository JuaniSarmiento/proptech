"""Lee el QR de una factura (R12, H-036, D-169): `zxing-cpp` sobre una imagen o sobre la primera
página de un PDF rasterizada con `pypdfium2`.

Es el único lugar que conoce a las dos bibliotecas: el caso de uso recibe el puerto `LectorDeQr`.
Nunca levanta: un archivo roto, con un formato que la biblioteca no abre o que declara más píxeles
de los que se aceptan (una bomba de descompresión) da una lista vacía, y el caso de uso lo trata
como `no_hay_qr`.
"""

from __future__ import annotations

import threading
from io import BytesIO

import pypdfium2
import zxingcpp
from PIL import Image

#: Tope de píxeles de una imagen que se decodifica (25 megapíxeles: una foto grande de celular).
MAXIMO_DE_PIXELES = 25_000_000
#: El lado largo al que se rasteriza la primera página de un PDF.
LADO_DE_LA_PAGINA = 2480
_ESCALA_MAXIMA = 4.0
#: PDFium no es seguro entre hilos y los endpoints síncronos corren en un pool.
_CANDADO_DE_PDFIUM = threading.Lock()


def _textos(imagen: Image.Image) -> list[str]:
    leidos = zxingcpp.read_barcodes(imagen, formats=zxingcpp.BarcodeFormat.QRCode)
    return [str(codigo.text) for codigo in leidos]


def _de_imagen(contenido: bytes) -> list[str]:
    with Image.open(BytesIO(contenido)) as imagen:
        ancho, alto = imagen.size
        if ancho <= 0 or alto <= 0 or ancho * alto > MAXIMO_DE_PIXELES:
            return []
        imagen.load()
        return _textos(imagen.convert("RGB"))


def _de_pdf(contenido: bytes) -> list[str]:
    with _CANDADO_DE_PDFIUM:
        documento = pypdfium2.PdfDocument(contenido)
        try:
            if len(documento) == 0:
                return []
            pagina = documento[0]
            ancho, alto = pagina.get_size()
            if ancho <= 0 or alto <= 0:
                return []
            escala = min(_ESCALA_MAXIMA, LADO_DE_LA_PAGINA / max(ancho, alto))
            imagen = pagina.render(scale=escala).to_pil().convert("RGB")
        finally:
            documento.close()
    return _textos(imagen)


class LectorDeQrConZxing:
    def leer(self, contenido: bytes, tipo: str) -> list[str]:
        """Los textos de los QR de la imagen (`jpeg` o `png`) o de la primera página del PDF
        (`pdf`)."""
        try:
            return _de_pdf(contenido) if tipo == "pdf" else _de_imagen(contenido)
        except Exception:
            return []
