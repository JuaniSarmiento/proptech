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
from proptech_core.compartido.porcentaje import Porcentaje, PorcentajeInvalido
from proptech_core.compartido.texto import recortado_sin_control
from proptech_core.compartido.tipos_de_unidad import TIPOS_DE_UNIDAD_VALIDOS

# re.ASCII en _PATRON_CLAVE: por consistencia con el resto del módulo,
# aunque hoy no use `\d` (si alguna vez lo usara, no filtraría dígitos
# Unicode). fullmatch, no match + `^...$`, en los dos: sin re.MULTILINE,
# `$` matchea antes de un `\n` final del string, así que `.match()`
# aceptaba "encargado\n" o "3.00\n" como válidos (auditor, cambio 1b
# vuelta 3; misma familia que L-002).
_PATRON_CLAVE = re.compile(r"^[a-z][a-z0-9_]{0,39}$", re.ASCII)
# El formato de un porcentaje (ASCII, fullmatch, sin signo) lo valida
# `Porcentaje` desde D13 (tarea 2.3); ya no hace falta un patrón propio acá.


class ParametrosInvalidos(Exception):
    """El archivo de parámetros no existe, está mal formado o es inválido."""


def _validador_porcentaje(minimo: str, maximo: str) -> Any:
    minimo_d = Decimal(minimo)
    maximo_d = Decimal(maximo)

    def _validar(valor: Any) -> Decimal:
        # D13 (deuda del 1b con dueño 3, tarea 2.3, L-009): el formato
        # (texto ASCII, fullmatch, sin signo, rechazo de float/bool/NaN/
        # Infinity/dígitos Unicode/`\n` final) lo valida `Porcentaje`, el
        # mismo tipo que usa `semilla.py` para su propio campo — un arreglo
        # ahí arregla los dos lectores (el gemelo de L-009). El mensaje
        # sigue nombrando el rango permitido aunque el problema sea de
        # formato (no sólo de valor): un "-1.00" nunca llega al chequeo de
        # rango de más abajo porque `Porcentaje` no admite signo, y la spec
        # (escenario "Tasa negativa") exige que el rango se mencione
        # siempre (rompedor, cambio 1b vuelta 2).
        try:
            porcentaje = Porcentaje(valor)
        except PorcentajeInvalido:
            raise ValueError(
                f"formato inválido: hasta 2 decimales, sin signo; debe estar entre "
                f"{minimo} y {maximo}"
            ) from None
        decimal = porcentaje.decimal
        if decimal < minimo_d or decimal > maximo_d:
            raise ValueError(f"debe estar entre {minimo} y {maximo}")
        return decimal

    return _validar


def _tipo_de_unidad_valido(valor: str) -> str:
    """D-029 (deuda del 1b con dueño 3, tarea 2.3, nota N9 c de
    `design.md`): sólo los cuatro tipos de unidad fijados por D-029, con la
    misma constante que usa el `CHECK` de la migración de la tarea 3.1."""
    if valor not in TIPOS_DE_UNIDAD_VALIDOS:
        raise ValueError(
            "tipo de unidad desconocido: debe ser uno de "
            + ", ".join(sorted(TIPOS_DE_UNIDAD_VALIDOS))
        )
    return valor


def _nombre_valido(valor: str) -> str:
    # R3A-1/R3A-6 (cambio 3a, vuelta 1 de correcciones): nunca un carácter
    # de control (U+0000 incluido), y recortado en el borde — mismo criterio
    # que el resto de los nombres de la familia (unidad, grupo, categoría).
    recortado = recortado_sin_control(valor)
    if len(recortado) > 80:
        raise ValueError("no puede superar los 80 caracteres")
    return recortado


def _clave_valida(valor: str) -> str:
    if not _PATRON_CLAVE.fullmatch(valor):
        raise ValueError("debe matchear ^[a-z][a-z0-9_]{0,39}$")
    return valor


def _factor_en_rango(valor: Porcentaje) -> Porcentaje:
    """El factor de un estado es un porcentaje 0..100 (mismo rango que el
    fondo de reserva, D6, tarea 6.3). Hasta D13 (tarea 2.3) viajaba con el
    tipo `Dinero` por no existir todavía `Porcentaje`, aunque nunca fue un
    monto; D13 lo corrige."""
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
_ClaveDeTipoDeUnidad = Annotated[_Clave, AfterValidator(_tipo_de_unidad_valido)]
_Tasa = Annotated[Decimal, BeforeValidator(_validador_porcentaje("0", "10"))]
_Porcentaje = Annotated[Decimal, BeforeValidator(_validador_porcentaje("0", "100"))]
_Recargo = Annotated[Decimal, BeforeValidator(_validador_porcentaje("0.01", "20.00"))]
_Factor = Annotated[Porcentaje, AfterValidator(_factor_en_rango)]
_CargoFijo = Annotated[Dinero, AfterValidator(_cargo_fijo_no_negativo)]


class _Base(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class Intereses(_Base):
    tasa_mensual: _Tasa
    dias_de_gracia: int = Field(ge=0, le=31)
    forma_de_calculo: Literal["proporcional_por_dia", "mes_entero"]


class FondoDeReserva(_Base):
    porcentaje: _Porcentaje


class RangoDelRecargo(_Base):
    minimo: _Recargo
    maximo: _Recargo

    @model_validator(mode="after")
    def _ordenado(self) -> RangoDelRecargo:
        if self.minimo > self.maximo:
            raise ValueError("el mínimo no puede superar al máximo")
        return self


class Vencimiento(_Base):
    dia: int = Field(ge=1, le=28)
    modalidad: Literal["unico", "doble"]
    rango_recargo: RangoDelRecargo
    dia_segundo_vencimiento: int | None = Field(default=None, ge=1, le=28)
    recargo_segundo_vencimiento: _Recargo | None = None

    @model_validator(mode="after")
    def _coherente(self) -> Vencimiento:
        segundo, recargo = self.dia_segundo_vencimiento, self.recargo_segundo_vencimiento
        if self.modalidad == "unico":
            valido = segundo is None and recargo is None
        else:
            valido = (
                segundo is not None
                and segundo > self.dia
                and recargo is not None
                and self.rango_recargo.minimo <= recargo <= self.rango_recargo.maximo
            )
        if not valido:
            raise ValueError("vencimiento incoherente: revisar modalidad, segundo día y recargo")
        return self


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
    clave: _ClaveDeTipoDeUnidad
    nombre: _Nombre


class EstadoDeUnidad(_Base):
    clave: _Clave
    nombre: _Nombre
    factor: _Factor
    cargo_fijo: _CargoFijo


class EstadosDeUnidad(_Base):
    habilitados: bool
    estados: list[EstadoDeUnidad] = Field(min_length=1)


class Invitaciones(_Base):
    vencimiento_dias: int = Field(ge=1)


class Parametros(_Base):
    version: Literal[1]
    invitaciones: Invitaciones
    intereses: Intereses
    fondo_de_reserva: FondoDeReserva
    vencimiento: Vencimiento
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

        # R3A-2 (L-018): la base exige
        # UNIQUE (administracion_id, complejo_id, lower(nombre)) — el mismo
        # criterio, sin distinguir mayúsculas, o `crear_edificio` arranca
        # "sano" con un archivo que hace imposible crear un edificio.
        nombres_categoria = [c.nombre.lower() for c in self.categorias_de_gasto]
        if len(nombres_categoria) != len(set(nombres_categoria)):
            problemas.append(
                "categorias_de_gasto: tiene nombres repetidos sin distinguir mayúsculas"
            )

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
