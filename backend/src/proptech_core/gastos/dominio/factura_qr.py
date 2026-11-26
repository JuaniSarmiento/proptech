"""El QR de la factura electrónica de ARCA (R12, H-036, D-169): de su texto a los datos de la
factura.

Dominio puro: recibe el texto que decodificó el lector del QR (`https://<host>/fe/qr/?p=<base64 del
JSON>`) y devuelve los datos validados o dice por qué se descarta. Nunca devuelve datos a medias: o
sirve entero o es un `QrDescartado` con su motivo. Los motivos se evalúan en este orden y vale el
primero: `dominio_ajeno`, `json_invalido`, `version_desconocida`, `importe_invalido`,
`datos_invalidos` (`no_hay_qr` lo dice quien no encontró ningún QR). El dominio se compara por
igualdad exacta con los dos hosts de ARCA, nunca por prefijo ni sufijo. Los números del JSON se leen
como `Decimal` (nunca `float`): el importe en pesos es `importe x ctz` con redondeo medio hacia
arriba (D-117), y todo lo que no sea un entero donde se espera un entero se descarta.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any
from urllib.parse import unquote, urlsplit

from proptech_core.compartido.dinero import Dinero, MontoInvalido
from proptech_core.gastos.dominio.cuit import cuit_valido

MOTIVO_NO_HAY_QR = "no_hay_qr"
MOTIVO_DOMINIO_AJENO = "dominio_ajeno"
MOTIVO_VERSION_DESCONOCIDA = "version_desconocida"
MOTIVO_JSON_INVALIDO = "json_invalido"
MOTIVO_IMPORTE_INVALIDO = "importe_invalido"
MOTIVO_DATOS_INVALIDOS = "datos_invalidos"

_HOSTS = frozenset({"arca.gob.ar", "www.arca.gob.ar", "afip.gob.ar", "www.afip.gob.ar"})
_RUTA = "/fe/qr/"
#: Un QR de factura mide unos 300 caracteres; más que esto no se procesa.
_LARGO_MAXIMO = 8192
_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)
_ENTERO = re.compile(r"[0-9]{1,20}", re.ASCII)
_CENTAVO = Decimal("0.01")


class QrDescartado(Exception):
    """El QR no sirve; `motivo` es uno de los `MOTIVO_*`."""

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo
        super().__init__(motivo)


@dataclass(frozen=True)
class DatosDelQr:
    cuit: str
    punto_de_venta: str
    tipo_de_comprobante: str
    numero_de_comprobante: str
    fecha: date
    #: En pesos: `importe x ctz`.
    importe: Dinero
    documento_receptor: str | None


def _parametro_p(texto: str) -> str | None:
    """El valor de `p` de una URL de ARCA de host y ruta exactos, o `None` si el host es ajeno."""
    try:
        partes = urlsplit(texto.strip())
        host = partes.netloc.lower()
    except ValueError:
        return None
    if partes.scheme != "https" or host not in _HOSTS or partes.path != _RUTA:
        return None
    for par in partes.query.split("&"):
        nombre, _, valor = par.partition("=")
        if nombre == "p":
            return unquote(valor)
    return ""


def _json_del_parametro(valor: str) -> dict[str, Any]:
    if not valor or len(valor) > _LARGO_MAXIMO:
        raise QrDescartado(MOTIVO_JSON_INVALIDO)

    def constante(_nombre: str) -> Any:
        raise ValueError

    relleno = valor + "=" * (-len(valor) % 4)
    try:
        crudo = (
            base64.urlsafe_b64decode(relleno)
            if ("-" in valor or "_" in valor)
            else base64.b64decode(relleno, validate=True)
        )
        datos = json.loads(crudo.decode("utf-8"), parse_float=Decimal, parse_constant=constante)
    except binascii.Error, ValueError, RecursionError:
        raise QrDescartado(MOTIVO_JSON_INVALIDO) from None
    if not isinstance(datos, dict):
        raise QrDescartado(MOTIVO_JSON_INVALIDO)
    return datos


def _es_numero(valor: Any) -> bool:
    return isinstance(valor, int | Decimal) and not isinstance(valor, bool)


def _importe_en_pesos(datos: dict[str, Any]) -> Dinero:
    bruto, bruta_ctz = datos.get("importe"), datos.get("ctz")
    if not _es_numero(bruto) or not _es_numero(bruta_ctz):
        raise QrDescartado(MOTIVO_IMPORTE_INVALIDO)
    importe, cotizacion = Decimal(str(bruto)), Decimal(str(bruta_ctz))
    if not importe.is_finite() or not cotizacion.is_finite() or importe <= 0 or cotizacion <= 0:
        raise QrDescartado(MOTIVO_IMPORTE_INVALIDO)
    try:
        # El importe del comprobante viene en la unidad de la moneda: nunca más de dos decimales.
        if importe != importe.quantize(_CENTAVO):
            raise QrDescartado(MOTIVO_IMPORTE_INVALIDO)
        en_pesos = (importe * cotizacion).quantize(_CENTAVO, rounding=ROUND_HALF_UP)
        resultado = Dinero.desde_decimal(en_pesos)
    except InvalidOperation, MontoInvalido:
        raise QrDescartado(MOTIVO_IMPORTE_INVALIDO) from None
    if resultado <= Dinero("0.00"):
        raise QrDescartado(MOTIVO_IMPORTE_INVALIDO)
    return resultado


def _entero(datos: dict[str, Any], clave: str, maximo: int) -> str:
    valor = datos.get(clave)
    if not isinstance(valor, int) or isinstance(valor, bool) or not 1 <= valor <= maximo:
        raise QrDescartado(MOTIVO_DATOS_INVALIDOS)
    return str(valor)


def _documento_del_receptor(datos: dict[str, Any]) -> str | None:
    valor = datos.get("nroDocRec")
    if valor is None:
        return None
    if isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0:
        return str(valor)
    if isinstance(valor, str) and _ENTERO.fullmatch(valor):
        return str(int(valor))
    raise QrDescartado(MOTIVO_DATOS_INVALIDOS)


def interpretar_qr(texto: str) -> DatosDelQr:
    valor = _parametro_p(texto)
    if valor is None:
        raise QrDescartado(MOTIVO_DOMINIO_AJENO)
    datos = _json_del_parametro(valor)
    version = datos.get("ver")
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        raise QrDescartado(MOTIVO_VERSION_DESCONOCIDA)
    importe = _importe_en_pesos(datos)
    cuit = datos.get("cuit")
    if not isinstance(cuit, int) or isinstance(cuit, bool) or not cuit_valido(str(cuit)):
        raise QrDescartado(MOTIVO_DATOS_INVALIDOS)
    punto_de_venta = _entero(datos, "ptoVta", 99999)
    tipo = _entero(datos, "tipoCmp", 999)
    numero = _entero(datos, "nroCmp", 99999999)
    fecha_texto = datos.get("fecha")
    if not isinstance(fecha_texto, str) or not _FECHA.fullmatch(fecha_texto):
        raise QrDescartado(MOTIVO_DATOS_INVALIDOS)
    try:
        fecha = date.fromisoformat(fecha_texto)
    except ValueError:
        raise QrDescartado(MOTIVO_DATOS_INVALIDOS) from None
    return DatosDelQr(
        cuit=str(cuit),
        punto_de_venta=punto_de_venta,
        tipo_de_comprobante=tipo,
        numero_de_comprobante=numero,
        fecha=fecha,
        importe=importe,
        documento_receptor=_documento_del_receptor(datos),
    )
