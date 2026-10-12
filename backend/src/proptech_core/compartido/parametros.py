"""Esquema de config/parametros.yaml y su lector (D6).

Los porcentajes viajan siempre como texto en el YAML; un número YAML (float o
int) es rechazado pidiendo texto. `leer_parametros` junta TODOS los problemas
(de pydantic y de las validaciones cruzadas) en un único `ParametrosInvalidos`,
una línea por problema, identificado por ruta, nunca por el valor recibido.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml, leer_archivo
from proptech_core.compartido.dinero import Dinero

# re.ASCII en _PATRON_CLAVE: por consistencia con el resto del módulo,
# aunque hoy no use `\d` (si alguna vez lo usara, no filtraría dígitos
# Unicode). fullmatch, no match + `^...$`, en los dos: sin re.MULTILINE,
# `$` matchea antes de un `\n` final del string, así que `.match()`
# aceptaba "encargado\n" o "3.00\n" como válidos (auditor, cambio 1b
# vuelta 3; misma familia que L-002).
_PATRON_CLAVE = re.compile(r"^[a-z][a-z0-9_]{0,39}$", re.ASCII)
# re.ASCII: `\d` sin ese flag matchea cualquier dígito Unicode de categoría Nd
# (arábigo-índico, de ancho completo, etc.), no sólo 0-9 (rompedor, cambio 1b
# vuelta 2; mismo problema que `dinero.py`).
_PATRON_PORCENTAJE = re.compile(r"^\d{1,3}(\.\d{1,2})?$", re.ASCII)


class ParametrosInvalidos(Exception):
    """El archivo de parámetros no existe, está mal formado o es inválido."""


def _validador_porcentaje(minimo: str, maximo: str) -> Any:
    minimo_d = Decimal(minimo)
    maximo_d = Decimal(maximo)

    def _validar(valor: Any) -> Decimal:
        if type(valor) is not str:
            raise ValueError(f"debe estar escrito como texto, no {type(valor).__name__}")
        if not _PATRON_PORCENTAJE.fullmatch(valor):
            # El mensaje nombra el rango permitido aunque el problema sea de
            # formato (no sólo de valor): un "-1.00" nunca llega al chequeo de
            # rango de más abajo porque el patrón no admite signo, y la spec
            # (escenario "Tasa negativa") exige que el rango se mencione
            # siempre (rompedor, cambio 1b vuelta 2).
            raise ValueError(
                f"formato inválido: hasta 2 decimales, sin signo; debe estar entre "
                f"{minimo} y {maximo}"
            )
        decimal = Decimal(valor)
        if decimal < minimo_d or decimal > maximo_d:
            raise ValueError(f"debe estar entre {minimo} y {maximo}")
        return decimal

    return _validar


def _nombre_valido(valor: str) -> str:
    if not valor.strip():
        raise ValueError("no puede estar vacío ni en blanco")
    if len(valor) > 80:
        raise ValueError("no puede superar los 80 caracteres")
    return valor


def _clave_valida(valor: str) -> str:
    if not _PATRON_CLAVE.fullmatch(valor):
        raise ValueError("debe matchear ^[a-z][a-z0-9_]{0,39}$")
    return valor


def _factor_en_rango(valor: Dinero) -> Dinero:
    """El factor de un estado es un porcentaje 0..100 (mismo rango que el
    fondo de reserva), aunque viaje con el tipo `Dinero` (D6, tarea 6.3)."""
    if valor.decimal < Decimal("0") or valor.decimal > Decimal("100"):
        raise ValueError("debe estar entre 0 y 100")
    return valor


def _cargo_fijo_no_negativo(valor: Dinero) -> Dinero:
    """El cargo fijo de un estado es un monto válido no negativo (D6, tarea 6.3)."""
    if valor.decimal < Decimal("0"):
        raise ValueError("no puede ser negativo")
    return valor


_Nombre = Annotated[str, AfterValidator(_nombre_valido)]
_Clave = Annotated[str, AfterValidator(_clave_valida)]
_Tasa = Annotated[Decimal, BeforeValidator(_validador_porcentaje("0", "10"))]
_Porcentaje = Annotated[Decimal, BeforeValidator(_validador_porcentaje("0", "100"))]
_Factor = Annotated[Dinero, AfterValidator(_factor_en_rango)]
_CargoFijo = Annotated[Dinero, AfterValidator(_cargo_fijo_no_negativo)]


class _Base(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class Intereses(_Base):
    tasa_mensual: _Tasa
    dias_de_gracia: int = Field(ge=0, le=31)
    forma_de_calculo: Literal["proporcional_por_dia", "mes_entero"]


class FondoDeReserva(_Base):
    porcentaje: _Porcentaje


class CategoriaDeGasto(_Base):
    clave: _Clave
    nombre: _Nombre


class GrupoDeReparto(_Base):
    clave: _Clave
    nombre: _Nombre
    metodo: Literal["coeficiente", "superficie", "partes_iguales"]
    alcance: Literal["todas_las_unidades", "a_elegir"]
    descripcion: str | None = None


class TipoDeUnidad(_Base):
    clave: _Clave
    nombre: _Nombre


class EstadoDeUnidad(_Base):
    clave: _Clave
    nombre: _Nombre
    factor: _Factor
    cargo_fijo: _CargoFijo


class EstadosDeUnidad(_Base):
    habilitados: bool
    estados: list[EstadoDeUnidad] = Field(min_length=1)


class Parametros(_Base):
    version: Literal[1]
    intereses: Intereses
    fondo_de_reserva: FondoDeReserva
    categorias_de_gasto: list[CategoriaDeGasto] = Field(min_length=1)
    grupos_de_reparto: list[GrupoDeReparto] = Field(min_length=1)
    tipos_de_unidad: list[TipoDeUnidad] = Field(min_length=1)
    estados_de_unidad: EstadosDeUnidad

    @model_validator(mode="after")
    def _validar_cruzadas(self) -> Parametros:
        problemas: list[str] = []

        claves_categoria = [c.clave for c in self.categorias_de_gasto]
        if len(claves_categoria) != len(set(claves_categoria)):
            problemas.append("categorias_de_gasto: tiene claves repetidas")

        claves_grupo = [g.clave for g in self.grupos_de_reparto]
        if len(claves_grupo) != len(set(claves_grupo)):
            problemas.append("grupos_de_reparto: tiene claves repetidas")

        generales = next((g for g in self.grupos_de_reparto if g.clave == "generales"), None)
        if generales is None:
            problemas.append("grupos_de_reparto: falta el grupo 'generales'")
        elif generales.metodo != "coeficiente" or generales.alcance != "todas_las_unidades":
            problemas.append(
                "grupos_de_reparto[generales]: debe ser metodo=coeficiente y "
                "alcance=todas_las_unidades"
            )

        claves_tipo = [t.clave for t in self.tipos_de_unidad]
        if len(claves_tipo) != len(set(claves_tipo)):
            problemas.append("tipos_de_unidad: tiene claves repetidas")

        claves_estado = [e.clave for e in self.estados_de_unidad.estados]
        if len(claves_estado) != len(set(claves_estado)):
            problemas.append("estados_de_unidad.estados: tiene claves repetidas")

        if problemas:
            raise ValueError("; ".join(problemas))
        return self


def _ruta_legible(loc: tuple[int | str, ...]) -> str:
    partes: list[str] = []
    for segmento in loc:
        if isinstance(segmento, int):
            partes[-1] = f"{partes[-1]}[{segmento}]"
        else:
            partes.append(str(segmento))
    return ".".join(partes)


def _formatear_errores(error: ValidationError) -> str:
    lineas = [f"{_ruta_legible(e['loc'])}: {e['msg']}" for e in error.errors()]
    return "parámetros inválidos:\n" + "\n".join(lineas)


def leer_parametros(ruta: str) -> Parametros:
    """Lee y valida `config/parametros.yaml` (D6). Nunca incluye valores crudos
    en el mensaje de error: sólo rutas y motivos."""
    try:
        contenido = leer_archivo(ruta)
        datos = cargar_yaml(contenido)
    except ErrorDeCarga as error:
        raise ParametrosInvalidos(str(error)) from None

    try:
        return Parametros(**datos)
    except ValidationError as error:
        raise ParametrosInvalidos(_formatear_errores(error)) from None
    except TypeError as error:
        # p.ej. la raíz es un mapa pero con claves no-string, o algo que
        # pydantic no puede siquiera intentar validar como kwargs.
        raise ParametrosInvalidos(f"parámetros inválidos: {error}") from None
