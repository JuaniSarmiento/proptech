"""Validación pura de la hoja `Unidades` (design D2, D3, E1 a E5, E7, E14): todo o nada, con todos
los errores juntos y cada uno con hoja, fila, columna y motivo. Sin Excel y sin base: recibe la
plantilla ya leída y lo que hace falta saber del edificio.

Los motivos nunca repiten el valor que escribió la persona.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from proptech_core.compartido.coeficientes import Coeficiente, informar_coeficientes
from proptech_core.compartido.superficie import Superficie
from proptech_core.compartido.texto import sin_caracteres_de_control
from proptech_core.compartido.tipos_de_unidad import TIPOS_DE_UNIDAD_VALIDOS
from proptech_core.importacion.dominio.numeros import NumeroInvalido, leer_decimal
from proptech_core.importacion.dominio.plantilla import (
    ENCABEZADOS_POR_HOJA,
    HOJA_UNIDADES,
    ErrorDeImportacion,
    FilaLeida,
    PlantillaLeida,
)

_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_LARGO_DE_LA_UNIDAD = 40
_SUPERFICIE_MAXIMA = Decimal(10) ** 8
_TOLERANCIA = "±0,0001"


@dataclass(frozen=True)
class ContextoDelEdificio:
    """Lo que la validación necesita saber del edificio: nada de la base."""

    #: Los pisos que acepta el edificio (`vocabulario_de_pisos`), o `None` si todavía no configuró
    #: pisos y subsuelos.
    vocabulario_de_pisos: frozenset[str] | None
    tiene_unidades: bool


@dataclass(frozen=True)
class UnidadAImportar:
    fila: int
    identificador: str
    tipo: str
    piso: str
    coeficiente: Coeficiente
    superficie_m2: Superficie
    propietario: str | None
    email: str | None


@dataclass(frozen=True)
class PadronValidado:
    unidades: tuple[UnidadAImportar, ...]
    advertencias: tuple[ErrorDeImportacion, ...]


class PadronInvalido(Exception):
    def __init__(self, errores: list[ErrorDeImportacion]) -> None:
        super().__init__("; ".join(e.motivo for e in errores))
        self.errores = tuple(errores)


def _error(fila: int | None, columna: str | None, motivo: str) -> ErrorDeImportacion:
    return ErrorDeImportacion(HOJA_UNIDADES, fila, columna, motivo)


def _numero_a_texto(numero: Decimal) -> str:
    return format(numero.normalize(), "f").replace(".", ",")


class _Fila:
    """Valida una fila y junta sus errores (uno por columna), en el orden de la plantilla."""

    def __init__(self, fila: FilaLeida, contexto: ContextoDelEdificio) -> None:
        self.fila = fila
        self.contexto = contexto
        self.errores: list[ErrorDeImportacion] = []

    def falla(self, columna: str, motivo: str) -> None:
        self.errores.append(_error(self.fila.numero, columna, motivo))

    def _celda(self, columna: str) -> str | None:
        """El texto de la celda, o `None` si falta (y entonces ya quedó el error de esa columna)."""
        if columna in self.fila.formulas_sin_cache:
            self.falla(
                columna,
                "la celda es una fórmula sin valor guardado: abrí el archivo en Excel y guardalo",
            )
            return None
        return self.fila.valores.get(columna)

    def _obligatoria(self, columna: str) -> str | None:
        valor = self._celda(columna)
        if valor is None and columna not in self.fila.formulas_sin_cache:
            self.falla(columna, "es obligatoria")
        return valor

    def unidad(self) -> str | None:
        valor = self._obligatoria("Unidad")
        if valor is None:
            return None
        if len(valor) > _LARGO_DE_LA_UNIDAD:
            self.falla("Unidad", f"no puede superar los {_LARGO_DE_LA_UNIDAD} caracteres")
            return None
        try:
            limpio = sin_caracteres_de_control(valor).strip()
        except ValueError:
            self.falla("Unidad", "tiene caracteres que no se pueden usar")
            return None
        if not limpio:
            self.falla("Unidad", "es obligatoria")
            return None
        return limpio

    def tipo(self) -> str | None:
        valor = self._obligatoria("Tipo")
        if valor is None:
            return None
        if valor not in TIPOS_DE_UNIDAD_VALIDOS:
            opciones = ", ".join(sorted(TIPOS_DE_UNIDAD_VALIDOS))
            self.falla("Tipo", f"tiene que ser exactamente uno de: {opciones}")
            return None
        return valor

    def piso(self) -> str | None:
        valor = self._obligatoria("Piso")
        if valor is None:
            return None
        vocabulario = self.contexto.vocabulario_de_pisos
        if vocabulario is not None and valor not in vocabulario:
            self.falla("Piso", "no está entre los pisos del edificio (se compara exacto)")
            return None
        return valor

    def _numero(self, columna: str, decimales: int) -> Decimal | None:
        valor = self._obligatoria(columna)
        if valor is None:
            return None
        try:
            return leer_decimal(valor, decimales=decimales, numerico=columna in self.fila.numericas)
        except NumeroInvalido as error:
            self.falla(columna, str(error))
            return None

    def coeficiente(self) -> Coeficiente | None:
        numero = self._numero("Coeficiente", 6)
        if numero is None:
            return None
        if numero <= 0:
            self.falla("Coeficiente", "tiene que ser mayor que 0")
            return None
        if numero > 1:
            self.falla("Coeficiente", "tiene que ser a lo sumo 1")
            return None
        return Coeficiente(format(numero, "f"))

    def superficie(self) -> Superficie | None:
        numero = self._numero("Superficie m2", 2)
        if numero is None:
            return None
        if numero <= 0:
            self.falla("Superficie m2", "tiene que ser mayor que 0")
            return None
        if numero >= _SUPERFICIE_MAXIMA:
            self.falla("Superficie m2", "es demasiado grande (hasta 99.999.999,99)")
            return None
        return Superficie(format(numero, "f"))

    def propietario(self) -> str | None:
        valor = self._celda("Propietario")
        if valor is None:
            return None
        try:
            return sin_caracteres_de_control(valor).strip() or None
        except ValueError:
            self.falla("Propietario", "tiene caracteres que no se pueden usar")
            return None

    def email(self) -> str | None:
        valor = self._celda("Email")
        if valor is None:
            return None
        try:
            limpio = sin_caracteres_de_control(valor).strip().lower()
        except ValueError:
            limpio = ""
        if not _EMAIL.fullmatch(limpio):
            self.falla("Email", "no es un email válido")
            return None
        return limpio


def _faltan_los_encabezados(plantilla: PlantillaLeida) -> list[ErrorDeImportacion]:
    hoja = plantilla.hojas[HOJA_UNIDADES]
    return [
        _error(None, columna, f"falta la columna {columna} en la fila 1 de la hoja {HOJA_UNIDADES}")
        for columna in ENCABEZADOS_POR_HOJA[HOJA_UNIDADES]
        if columna not in hoja.encabezados
    ]


def validar_padron(plantilla: PlantillaLeida, contexto: ContextoDelEdificio) -> PadronValidado:
    """Devuelve el padrón válido (con su advertencia de coeficientes, si hay) o levanta
    `PadronInvalido` con **todos** los errores."""
    hoja = plantilla.hojas.get(HOJA_UNIDADES)
    if contexto.tiene_unidades:
        if hoja is None or not hoja.filas:
            return PadronValidado(unidades=(), advertencias=())
        raise PadronInvalido(
            [
                _error(
                    fila.numero,
                    None,
                    "el edificio ya tiene unidades: la hoja Unidades tiene que venir sin filas",
                )
                for fila in hoja.filas
            ]
        )
    if hoja is None:
        raise PadronInvalido(
            [
                _error(
                    None,
                    None,
                    "falta la hoja Unidades: es obligatoria si el edificio no tiene unidades",
                )
            ]
        )
    if faltan := _faltan_los_encabezados(plantilla):
        raise PadronInvalido(faltan)
    if not hoja.filas:
        raise PadronInvalido([_error(None, None, "la hoja Unidades no tiene filas de datos")])

    errores: list[ErrorDeImportacion] = []
    if contexto.vocabulario_de_pisos is None:
        errores.append(
            _error(
                None,
                "Piso",
                "el edificio no tiene pisos ni subsuelos configurados: configuralos antes de "
                "importar (piso)",
            )
        )
    unidades: list[UnidadAImportar] = []
    vistas: dict[str, int] = {}
    for leida in hoja.filas:
        fila = _Fila(leida, contexto)
        identificador = fila.unidad()
        if identificador is not None:
            if identificador in vistas:
                fila.falla("Unidad", f"está repetida, ya está en la fila {vistas[identificador]}")
            else:
                vistas[identificador] = leida.numero
        tipo = fila.tipo()
        piso = fila.piso()
        coeficiente = fila.coeficiente()
        superficie = fila.superficie()
        propietario = fila.propietario()
        email = fila.email()
        if (
            email is not None
            and propietario is None
            and "Propietario" not in {e.columna for e in fila.errores}
        ):
            fila.falla("Propietario", "falta el propietario: el email necesita un nombre")
        errores.extend(fila.errores)
        if (
            fila.errores
            or identificador is None
            or tipo is None
            or piso is None
            or coeficiente is None
            or superficie is None
        ):
            continue
        unidades.append(
            UnidadAImportar(
                fila=leida.numero,
                identificador=identificador,
                tipo=tipo,
                piso=piso,
                coeficiente=coeficiente,
                superficie_m2=superficie,
                propietario=propietario,
                email=email,
            )
        )
    if errores:
        raise PadronInvalido(errores)

    informe = informar_coeficientes(u.coeficiente for u in unidades)
    suma = _numero_a_texto(Decimal(informe["suma"]))
    if informe["estado"] == "fuera_de_tolerancia":
        raise PadronInvalido(
            [
                _error(
                    None,
                    "Coeficiente",
                    f"los coeficientes suman {suma}, fuera de la tolerancia de {_TOLERANCIA} "
                    "respecto de 1: el archivo no se carga",
                )
            ]
        )
    advertencias: tuple[ErrorDeImportacion, ...] = ()
    if informe["estado"] == "advertencia":
        advertencias = (
            _error(
                None,
                "Coeficiente",
                f"los coeficientes suman {suma}, no 1 (dentro de la tolerancia de {_TOLERANCIA}): "
                "se carga igual",
            ),
        )
    return PadronValidado(unidades=tuple(unidades), advertencias=advertencias)
