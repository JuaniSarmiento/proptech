"""H-016 (F2c, D-158): el envoltorio del plazo de `proptech_worker.corte`, sin base."""

from __future__ import annotations

from typing import Any, cast

import pytest
import sqlalchemy.exc

from proptech_core.compartido.reintentos import ErrorPasajero


class _Reloj:
    def __init__(self) -> None:
        self.ahora = 100.0

    def __call__(self) -> float:
        return self.ahora


def test_un_efecto_dentro_del_plazo_pasa() -> None:
    from proptech_worker.corte import envolver_con_plazo

    reloj = _Reloj()
    vistos: list[object] = []

    def efecto(sesion: object) -> None:
        vistos.append(sesion)
        reloj.ahora += 0.4

    envolver_con_plazo(efecto, 0.5, reloj=reloj)(cast(Any, "sesion"))
    assert vistos == ["sesion"]


def test_un_efecto_que_pasa_el_plazo_levanta_corte_antes_de_confirmar() -> None:
    from proptech_worker.corte import CorteDeLaBase, envolver_con_plazo

    reloj = _Reloj()

    def efecto(_sesion: object) -> None:
        reloj.ahora += 0.6

    with pytest.raises(CorteDeLaBase):
        envolver_con_plazo(efecto, 0.5, reloj=reloj)(cast(Any, None))


def test_el_corte_es_pasajero() -> None:
    from proptech_worker.corte import CorteDeLaBase

    assert issubclass(CorteDeLaBase, ErrorPasajero)


def test_un_error_de_conexion_de_la_base_se_traduce_a_corte() -> None:
    from proptech_worker.corte import CorteDeLaBase, traducir_error_de_base

    error = sqlalchemy.exc.OperationalError("SELECT 1", {}, Exception("terminating connection"))
    assert isinstance(traducir_error_de_base(error), CorteDeLaBase)


def test_un_error_de_programacion_no_se_traduce() -> None:
    from proptech_worker.corte import traducir_error_de_base

    error = sqlalchemy.exc.ProgrammingError("SELECT 1", {}, Exception("sintaxis"))
    assert traducir_error_de_base(error) is None
