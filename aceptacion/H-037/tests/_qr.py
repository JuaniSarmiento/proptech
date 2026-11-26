"""Un codificador de QR mínimo, sin dependencias, para armar las facturas de prueba de H-036.

El entorno no trae `qrcode` ni `segno` (D-169 elige `zxing-cpp` para LEER, que no codifica): este módulo escribe el
símbolo QR del modo byte, corrección de errores M, máscara 0, versiones 1 a 40 (ISO/IEC 18004; la estructura sigue
la del generador de referencia de Nayuki). Verificado el 26/11/2026 decodificando cada fixture de `_h036.py` con
`zxing-cpp` 3.x en un entorno aparte (texto idéntico, PNG, JPEG y PDF rasterizado con `pypdfium2`); donde `zxingcpp`
esté instalado, `_h036.verificar_con_zxing` lo vuelve a comprobar en cada corrida.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image

#: Corrección de errores M: palabras de corrección por bloque y cantidad de bloques, por versión (índice 1 a 40).
_ECC_POR_BLOQUE = [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28,
                   28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28]
_BLOQUES = [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28,
            29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49]


def _modulos_de_datos(version: int) -> int:
    resultado = (16 * version + 128) * version + 64
    if version >= 2:
        alineaciones = version // 7 + 2
        resultado -= (25 * alineaciones - 10) * alineaciones - 55
        if version >= 7:
            resultado -= 36
    return resultado


def _palabras_de_datos(version: int) -> int:
    return _modulos_de_datos(version) // 8 - _ECC_POR_BLOQUE[version] * _BLOQUES[version]


def _multiplicar(x: int, y: int) -> int:
    z = 0
    for i in range(7, -1, -1):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _divisor(grado: int) -> list[int]:
    resultado = [0] * (grado - 1) + [1]
    raiz = 1
    for _ in range(grado):
        for j in range(grado):
            resultado[j] = _multiplicar(resultado[j], raiz)
            if j + 1 < grado:
                resultado[j] ^= resultado[j + 1]
        raiz = _multiplicar(raiz, 0x02)
    return resultado


def _resto(datos: list[int], divisor: list[int]) -> list[int]:
    resultado = [0] * len(divisor)
    for byte in datos:
        factor = byte ^ resultado.pop(0)
        resultado.append(0)
        for i, coef in enumerate(divisor):
            resultado[i] ^= _multiplicar(coef, factor)
    return resultado


def _palabras(texto: bytes, version: int) -> list[int]:
    bits: list[int] = []

    def agregar(valor: int, cantidad: int) -> None:
        bits.extend((valor >> i) & 1 for i in range(cantidad - 1, -1, -1))

    agregar(0b0100, 4)
    agregar(len(texto), 8 if version <= 9 else 16)
    for byte in texto:
        agregar(byte, 8)
    capacidad = _palabras_de_datos(version) * 8
    agregar(0, min(4, capacidad - len(bits)))
    agregar(0, -len(bits) % 8)
    relleno = 0xEC
    while len(bits) < capacidad:
        agregar(relleno, 8)
        relleno ^= 0xEC ^ 0x11
    return [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]


def _con_correccion(datos: list[int], version: int) -> list[int]:
    bloques, largo_ecc = _BLOQUES[version], _ECC_POR_BLOQUE[version]
    crudas = _modulos_de_datos(version) // 8
    cortos = bloques - crudas % bloques
    largo_corto = crudas // bloques
    divisor = _divisor(largo_ecc)
    armados: list[list[int]] = []
    k = 0
    for i in range(bloques):
        largo = largo_corto - largo_ecc + (0 if i < cortos else 1)
        parte = datos[k:k + largo]
        k += largo
        ecc = _resto(parte, divisor)
        if i < cortos:
            parte = parte + [0]
        armados.append(parte + ecc)
    salida: list[int] = []
    for i in range(len(armados[0])):
        for j, bloque in enumerate(armados):
            if i != largo_corto - largo_ecc or j >= cortos:
                salida.append(bloque[i])
    return salida


def matriz(texto: str) -> list[list[bool]]:
    """La matriz de módulos (True = oscuro) del símbolo QR de `texto` en UTF-8."""
    crudo = texto.encode("utf-8")
    version = next(v for v in range(1, 41) if (4 + (8 if v <= 9 else 16) + 8 * len(crudo) + 7) // 8
                   <= _palabras_de_datos(v))
    tam = version * 4 + 17
    mod = [[False] * tam for _ in range(tam)]
    funcion = [[False] * tam for _ in range(tam)]

    def poner(x: int, y: int, oscuro: bool) -> None:
        mod[y][x] = oscuro
        funcion[y][x] = True

    def formato(mascara: int) -> None:
        dato = (0 << 3) | mascara  # nivel M = 00
        resto = dato
        for _ in range(10):
            resto = (resto << 1) ^ ((resto >> 9) * 0x537)
        bits = ((dato << 10) | resto) ^ 0x5412
        for i in range(6):
            poner(8, i, bool((bits >> i) & 1))
        poner(8, 7, bool((bits >> 6) & 1))
        poner(8, 8, bool((bits >> 7) & 1))
        poner(7, 8, bool((bits >> 8) & 1))
        for i in range(9, 15):
            poner(14 - i, 8, bool((bits >> i) & 1))
        for i in range(8):
            poner(tam - 1 - i, 8, bool((bits >> i) & 1))
        for i in range(8, 15):
            poner(8, tam - 15 + i, bool((bits >> i) & 1))
        poner(8, tam - 8, True)

    for i in range(tam):
        poner(6, i, i % 2 == 0)
        poner(i, 6, i % 2 == 0)
    for cx, cy in ((3, 3), (tam - 4, 3), (3, tam - 4)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x, y = cx + dx, cy + dy
                if 0 <= x < tam and 0 <= y < tam:
                    poner(x, y, max(abs(dx), abs(dy)) not in (2, 4))
    if version > 1:
        n = version // 7 + 2
        paso = 26 if version == 32 else (version * 4 + n * 2 + 1) // (n * 2 - 2) * 2
        posiciones = [tam - 7 - i * paso for i in range(n - 1)] + [6]
        posiciones.reverse()
        for i, cx in enumerate(posiciones):
            for j, cy in enumerate(posiciones):
                if (i, j) in ((0, 0), (0, n - 1), (n - 1, 0)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        poner(cx + dx, cy + dy, max(abs(dx), abs(dy)) != 1)
    formato(0)
    if version >= 7:
        resto = version
        for _ in range(12):
            resto = (resto << 1) ^ ((resto >> 11) * 0x1F25)
        bits = (version << 12) | resto
        for i in range(18):
            a, b = tam - 11 + i % 3, i // 3
            poner(a, b, bool((bits >> i) & 1))
            poner(b, a, bool((bits >> i) & 1))

    palabras = _con_correccion(_palabras(crudo, version), version)
    i = 0
    for derecha in range(tam - 1, 0, -2):
        if derecha == 6:
            derecha = 5
        for vert in range(tam):
            for j in range(2):
                x = derecha - j
                y = tam - 1 - vert if ((derecha + 1) & 2) == 0 else vert
                if not funcion[y][x] and i < len(palabras) * 8:
                    mod[y][x] = bool((palabras[i >> 3] >> (7 - (i & 7))) & 1)
                    i += 1
    for y in range(tam):
        for x in range(tam):
            if not funcion[y][x] and (x + y) % 2 == 0:
                mod[y][x] = not mod[y][x]
    formato(0)
    return mod


def imagen_del_qr(texto: str, escala: int = 6, borde: int = 4) -> Image.Image:
    """El QR como imagen en escala de grises, con su zona de silencio."""
    m = matriz(texto)
    tam = len(m) + 2 * borde
    chica = Image.new("L", (tam, tam), 255)
    chica.putdata([0 if 0 <= y - borde < len(m) and 0 <= x - borde < len(m) and m[y - borde][x - borde] else 255
                   for y in range(tam) for x in range(tam)])
    return chica.resize((tam * escala, tam * escala), Image.NEAREST)


def png_del_qr(texto: str) -> bytes:
    salida = BytesIO()
    imagen_del_qr(texto).save(salida, format="PNG")
    return salida.getvalue()
