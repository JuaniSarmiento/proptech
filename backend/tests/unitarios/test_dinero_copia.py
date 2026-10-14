"""Dinero copiable y serializable (D16). Cambio 1c, tarea 4.3.

`Dinero` es inmutable (`__slots__` + `__setattr__` que bloquea toda
asignación), así que el protocolo por defecto de copia/pickle, que reconstruye
el objeto vacío y le asigna el estado con `setattr`, choca con ese candado.
`__reduce__` reconstruye desde `a_texto()` (pasa de nuevo por la validación),
y `__copy__`/`__deepcopy__` devuelven `self` (un inmutable no necesita copia).

Escenarios de `representacion-de-montos`: Ida y vuelta por pickle; Copia
superficial y profunda; Copia profunda de un modelo con montos; Pickle con un
monto inválido. Lecciones: L-008.
"""

import copy
import pickle

import pytest
from pydantic import BaseModel

from proptech_core.compartido.dinero import Dinero, MontoInvalido


class _ModeloConMonto(BaseModel):
    monto: Dinero


class _PickleDineroInvalido:
    """Fuerza, sin pasar por `Dinero.__init__`, un `REDUCE` hacia
    `Dinero("1e3")`: simula un pickle armado a mano con un texto inválido."""

    def __reduce__(self) -> tuple[type[Dinero], tuple[str]]:
        return (Dinero, ("1e3",))


@pytest.mark.parametrize("protocolo", range(pickle.HIGHEST_PROTOCOL + 1))
def test_ida_y_vuelta_por_pickle_en_cada_protocolo(protocolo: int) -> None:
    original = Dinero("1234.56")
    datos = pickle.dumps(original, protocol=protocolo)
    reconstruido = pickle.loads(datos)  # noqa: S301 (sujeto del test: pickle propio)
    assert reconstruido == original
    assert reconstruido.a_texto() == original.a_texto()


def test_copy_copy_devuelve_el_mismo_objeto() -> None:
    original = Dinero("10.00")
    copia = copy.copy(original)
    assert copia is original


def test_copy_deepcopy_devuelve_el_mismo_objeto() -> None:
    original = Dinero("10.00")
    copia = copy.deepcopy(original)
    assert copia is original


def test_model_copy_deep_de_un_modelo_con_monto() -> None:
    modelo = _ModeloConMonto(monto=Dinero("99.90"))
    copia = modelo.model_copy(deep=True)
    assert copia.monto == modelo.monto
    assert copia.monto.a_texto() == "99.90"


def test_pickle_ida_y_vuelta_de_un_modelo_con_monto() -> None:
    modelo = _ModeloConMonto(monto=Dinero("99.90"))
    reconstruido = pickle.loads(pickle.dumps(modelo))  # noqa: S301
    assert reconstruido.monto == modelo.monto


def test_pickle_armado_a_mano_con_monto_invalido_levanta_monto_invalido() -> None:
    datos = pickle.dumps(_PickleDineroInvalido())
    with pytest.raises(MontoInvalido):
        pickle.loads(datos)  # noqa: S301
