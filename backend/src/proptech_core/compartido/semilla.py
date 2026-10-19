"""Semilla validada contra los parámetros y R01 compartida; no abre la base."""

from __future__ import annotations

import os
import sys
import warnings
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from proptech_core.compartido import coeficientes
from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml, leer_archivo
from proptech_core.compartido.superficie import Superficie

if TYPE_CHECKING:
    from proptech_core.compartido.parametros import Parametros


class SemillaInvalida(Exception):
    """El archivo de semilla no existe, está mal formado o es inválido."""


def _coeficiente_valido(valor: Any) -> Decimal:
    # Conserva Decimal en el modelo de la semilla, con el mismo parser que
    # la API (ASCII, fullmatch y rango). R01 tampoco se copia (L-009).
    return coeficientes.Coeficiente(valor).decimal


def _no_vacio(valor: str) -> str:
    if not valor.strip():
        raise ValueError("no puede estar vacío ni en blanco")
    return valor


_Coeficiente = Annotated[Decimal, BeforeValidator(_coeficiente_valido)]
_Texto = Annotated[str, AfterValidator(_no_vacio)]


class _Base(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class Edificio(_Base):
    nombre: _Texto
    localidad: _Texto
    estado_migracion: Literal["pendiente", "confirmada", "sin_saldos_previos"]


def _superficie_positiva(valor: Superficie) -> Superficie:
    """D13 (deuda del 1b con dueño 3, tarea 2.3): `superficie_m2` pasa de
    `Dinero` (un monto, nunca lo que es: una superficie en m², NUMERIC(10,2))
    a `Superficie`, con el mismo patrón ASCII y `fullmatch` (L-008, el
    gemelo de L-009 con `parametros.py`)."""
    if valor.decimal <= 0:
        raise ValueError("debe ser positiva")
    return valor


class Unidad(_Base):
    identificador: _Texto
    tipo: _Texto
    piso: _Texto
    coeficiente: _Coeficiente
    superficie_m2: Annotated[Superficie, AfterValidator(_superficie_positiva)]


class MiembroDeGrupo(_Base):
    identificador: _Texto
    coeficiente: _Coeficiente | None = None


class Grupo(_Base):
    modo: Literal["renormalizado", "propios"] = "renormalizado"
    unidades: list[MiembroDeGrupo]

    @model_validator(mode="before")
    @classmethod
    def abreviaturas(cls, valor: Any) -> Any:
        # Las listas de identificadores del 1b siguen siendo abreviaturas
        # de un grupo renormalizado, al igual que omitir `modo` en un mapa.
        if isinstance(valor, list):
            valor = {"unidades": valor}
        if isinstance(valor, dict) and isinstance(valor.get("unidades"), list):
            return {
                **valor,
                "unidades": [
                    {"identificador": m} if isinstance(m, str) else m for m in valor["unidades"]
                ],
            }
        return valor


class Semilla(_Base):
    version: Literal[1]
    edificio: Edificio
    unidades: list[Unidad] = Field(min_length=1)
    grupos: dict[str, Literal["todas"] | Grupo]


def _ruta_legible(loc: tuple[int | str, ...]) -> str:
    partes: list[str] = []
    for segmento in loc:
        if isinstance(segmento, int):
            partes[-1] = f"{partes[-1]}[{segmento}]"
        else:
            partes.append(str(segmento))
    return ".".join(partes)


def _formatear_errores_pydantic(error: ValidationError) -> list[str]:
    return [f"{_ruta_legible(e['loc'])}: {e['msg']}" for e in error.errors()]


def _informar_suma(
    valores: list[Decimal], campo: str, problemas: list[str], advertencias: list[str]
) -> None:
    informe = coeficientes.informar_coeficientes(coeficientes.Coeficiente(str(v)) for v in valores)
    diferencia = informe["diferencia"]
    if informe["estado"] == "fuera_de_tolerancia":
        problemas.append(f"{campo}: los coeficientes no suman 1; diferencia {diferencia}")
    elif informe["estado"] == "advertencia":
        advertencias.append(f"{campo}: diferencia {diferencia} dentro de la tolerancia de R01")


def _validar_contra_parametros(
    semilla: Semilla, parametros: Parametros
) -> tuple[list[str], list[str]]:
    problemas: list[str] = []
    advertencias: list[str] = []

    tipos_validos = {t.clave for t in parametros.tipos_de_unidad}
    for i, unidad in enumerate(semilla.unidades):
        if unidad.tipo not in tipos_validos:
            problemas.append(f"unidades[{i}].tipo: tipo de unidad desconocido")

    identificadores = [u.identificador for u in semilla.unidades]
    if len(identificadores) != len(set(identificadores)):
        # La spec (specs/datos-semilla, "Semilla validada contra los
        # parámetros") exige rechazar identificadores repetidos
        # **nombrando el campo y la unidad**: decir sólo "hay un
        # identificador repetido" no nombra cuál (auditor, cambio 1b
        # vuelta 3).
        vistos: set[str] = set()
        duplicados: list[str] = []
        for identificador in identificadores:
            if identificador in vistos and identificador not in duplicados:
                duplicados.append(identificador)
            vistos.add(identificador)
        problemas.append(
            "unidades: hay identificadores repetidos: " + ", ".join(repr(d) for d in duplicados)
        )

    _informar_suma([u.coeficiente for u in semilla.unidades], "unidades", problemas, advertencias)

    claves_grupo_validas = {g.clave: g for g in parametros.grupos_de_reparto}
    if "generales" not in semilla.grupos:
        problemas.append("grupos.generales: es obligatorio y debe ser 'todas'")
    for clave_grupo, grupo in semilla.grupos.items():
        if clave_grupo not in claves_grupo_validas:
            problemas.append(f"grupos.{clave_grupo}: grupo de reparto desconocido")
            continue
        if clave_grupo == "generales":
            if grupo != "todas":
                problemas.append("grupos.generales: debe ser 'todas'")
            continue
        if isinstance(grupo, str):
            problemas.append(f"grupos.{clave_grupo}: debe ser una lista de identificadores")
            continue
        campo = f"grupos.{clave_grupo}"
        if grupo.modo == "propios" and claves_grupo_validas[clave_grupo].metodo != "coeficiente":
            problemas.append(f"{campo}.modo: sólo coeficiente admite coeficientes propios")
        vistos_grupo: set[str] = set()
        for indice, miembro in enumerate(grupo.unidades):
            if miembro.identificador in vistos_grupo:
                problemas.append(
                    f"{campo}.unidades: identificador repetido {miembro.identificador!r}"
                )
            vistos_grupo.add(miembro.identificador)
            if miembro.identificador not in identificadores:
                problemas.append(
                    f"{campo}: el identificador {miembro.identificador!r} no existe en unidades"
                )
            if (grupo.modo == "propios") != (miembro.coeficiente is not None):
                problemas.append(f"{campo}.unidades[{indice}].coeficiente: incoherente con el modo")
        propios = [m.coeficiente for m in grupo.unidades if m.coeficiente is not None]
        if grupo.modo == "propios" and len(propios) == len(grupo.unidades):
            _informar_suma(propios, campo, problemas, advertencias)

    return problemas, advertencias


def leer_semilla(ruta: str, parametros: Parametros) -> Semilla:
    """Lee y valida `config/semilla/edificio-ejemplo.yaml` (D10), contra los
    `parametros` ya leídos. No abre conexión a la base."""
    try:
        contenido = leer_archivo(ruta)
        datos = cargar_yaml(contenido)
    except ErrorDeCarga as error:
        raise SemillaInvalida(str(error)) from None

    try:
        semilla = Semilla(**datos)
    except ValidationError as error:
        raise SemillaInvalida(
            "semilla inválida:\n" + "\n".join(_formatear_errores_pydantic(error))
        ) from None

    problemas, advertencias = _validar_contra_parametros(semilla, parametros)
    if problemas:
        raise SemillaInvalida("semilla inválida:\n" + "\n".join(problemas))
    for advertencia in advertencias:
        warnings.warn(advertencia, UserWarning, stacklevel=2)

    return semilla


def _main(argv: list[str]) -> int:
    """`python -m proptech_core.compartido.semilla <ruta>` (código 0 o 1).

    Lee los parámetros desde `PROPTECH_PARAMETROS` (D10). No abre conexión a
    la base: sin variables de PostgreSQL definidas, igual funciona."""
    from proptech_core.compartido.parametros import ParametrosInvalidos, leer_parametros

    if len(argv) != 2:
        print("uso: python -m proptech_core.compartido.semilla <ruta>", file=sys.stderr)
        return 1

    parametros_ruta = os.environ.get("PROPTECH_PARAMETROS")
    if not parametros_ruta:
        print("falta la variable de entorno PROPTECH_PARAMETROS", file=sys.stderr)
        return 1

    try:
        parametros = leer_parametros(parametros_ruta)
        leer_semilla(argv[1], parametros)
    except (ParametrosInvalidos, SemillaInvalida) as error:
        print(str(error), file=sys.stderr)
        return 1
    print("semilla válida")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
