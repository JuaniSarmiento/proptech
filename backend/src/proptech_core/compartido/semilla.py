"""Datos semilla del edificio de ejemplo (D10): archivo versionado, validado
contra los parámetros, que todavía no se inserta en la base (sin tablas de
edificio hasta el cambio 3)."""

from __future__ import annotations

import os
import re
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
)

from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml, leer_archivo
from proptech_core.compartido.dinero import Dinero

if TYPE_CHECKING:
    from proptech_core.compartido.parametros import Parametros

# re.ASCII: mismo problema que `dinero.py` y `parametros.py` (rompedor, cambio
# 1b vuelta 2) — `\d` sin el flag acepta dígitos Unicode no-ASCII.
# fullmatch, no match + `^...$` (usado abajo): mismo problema que los otros
# patrones del cambio — `$` matchea antes de un `\n` final del string, así
# que `.match()` aceptaba "0.400000\n" (auditor, cambio 1b vuelta 3).
_PATRON_COEFICIENTE = re.compile(r"^\d(\.\d{1,6})?$", re.ASCII)


class SemillaInvalida(Exception):
    """El archivo de semilla no existe, está mal formado o es inválido."""


def _coeficiente_valido(valor: Any) -> Decimal:
    if type(valor) is not str:
        raise ValueError(f"debe estar escrito como texto, no {type(valor).__name__}")
    if not _PATRON_COEFICIENTE.fullmatch(valor):
        raise ValueError("formato inválido: hasta 6 decimales, un solo dígito entero")
    decimal = Decimal(valor)
    if decimal <= 0:
        # El patrón admite "0" o "0.000000" como formato válido, pero la spec
        # (specs/datos-semilla, "Semilla validada contra los parámetros")
        # exige texto decimal **positivo**, no sólo no negativo (auditor,
        # cambio 1b vuelta 3).
        raise ValueError("debe ser positivo")
    return decimal


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


def _dinero_positivo(valor: Dinero) -> Dinero:
    if valor.decimal <= 0:
        raise ValueError("debe ser positiva")
    return valor


class Unidad(_Base):
    identificador: _Texto
    tipo: _Texto
    piso: _Texto
    coeficiente: _Coeficiente
    superficie_m2: Annotated[Dinero, AfterValidator(_dinero_positivo)]


class Semilla(_Base):
    version: int
    edificio: Edificio
    unidades: list[Unidad] = Field(min_length=1)
    grupos: dict[str, Any]


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


def _validar_contra_parametros(semilla: Semilla, parametros: Parametros) -> list[str]:
    problemas: list[str] = []

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

    suma = sum((u.coeficiente for u in semilla.unidades), start=Decimal(0))
    if suma != Decimal(1):
        problemas.append(f"unidades: los coeficientes deben sumar exactamente 1 (suman {suma})")

    claves_grupo_validas = {g.clave for g in parametros.grupos_de_reparto}
    for clave_grupo, miembros in semilla.grupos.items():
        if clave_grupo not in claves_grupo_validas:
            problemas.append(f"grupos.{clave_grupo}: grupo de reparto desconocido")
            continue
        if clave_grupo == "generales":
            if miembros != "todas":
                problemas.append("grupos.generales: debe ser 'todas'")
            continue
        if not isinstance(miembros, list):
            problemas.append(f"grupos.{clave_grupo}: debe ser una lista de identificadores")
            continue
        for miembro in miembros:
            if miembro not in identificadores:
                problemas.append(
                    f"grupos.{clave_grupo}: el identificador {miembro!r} no existe en unidades"
                )

    return problemas


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

    problemas = _validar_contra_parametros(semilla, parametros)
    if problemas:
        raise SemillaInvalida("semilla inválida:\n" + "\n".join(problemas))

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
