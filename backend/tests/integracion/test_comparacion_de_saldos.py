"""Tarea 2.3 de `importacion-desde-excel` (parte de la comparación): el borrador vigente contra el
control, unidad por unidad, con el aviso de mes entero (design D6, E13) y el permiso y alcance de
siempre (D7). Contra PostgreSQL real, llamando al caso de uso con la sesión como `proptech_app`.
Datos inventados."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from proptech_core.complejos.aplicacion.errores import NoEncontrado
from proptech_core.importacion.aplicacion.comparar import comparar_borrador
from proptech_core.importacion.aplicacion.errores import SinPermiso

from ._edificios import BaseDeEdificio
from ._importacion import Mundo, con_tenant, sembrar
from ._saldos_importados import (
    AVISO,
    archivo,
    con_diferencias,
    configurar,
    control_base,
    saldos_base,
    subir,
    unidad_de_la_torre,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


@pytest.fixture
def sesion(mundo: Mundo, sesion_edificio: Session) -> Session:
    con_tenant(sesion_edificio, mundo.admin)
    return sesion_edificio


def _por_unidad(c: Any) -> dict[str, tuple[str, str, str]]:
    return {
        u.unidad: (u.borrador.a_texto(), u.control.a_texto(), u.diferencia.a_texto())
        for u in c.unidades
    }


def _comparar(sesion: Session, mundo: Mundo, identidad: Any = None, complejo: Any = None) -> Any:
    return comparar_borrador(
        sesion, identidad or mundo.super_admin, complejo_id=complejo or mundo.torre
    )


# --- Los números ------------------------------------------------------------------------------


def test_sin_diferencias(mundo: Mundo, sesion: Session) -> None:
    resultado = subir(sesion, mundo.super_admin, mundo.torre, archivo())
    c = _comparar(sesion, mundo)
    assert c.importacion_id == resultado.importacion_id
    assert _por_unidad(c) == {
        "1A": ("169000.00", "169000.00", "0.00"),
        "1B": ("105000.00", "105000.00", "0.00"),
        "2A": ("52000.00", "52000.00", "0.00"),
        "2B": ("-3000.00", "-3000.00", "0.00"),
        "C1": ("-3000.00", "-3000.00", "0.00"),
    }
    assert (c.total_borrador.a_texto(), c.total_control.a_texto()) == ("320000.00", "320000.00")
    assert c.unidades_con_diferencia == 0
    assert c.requiere_aceptacion is False and c.aceptacion is None


def test_dos_errores_de_signo_opuesto_coinciden_en_el_total_y_se_ven_por_unidad(
    mundo: Mundo, sesion: Session
) -> None:
    subir(sesion, mundo.super_admin, mundo.torre, con_diferencias())
    c = _comparar(sesion, mundo)
    assert (c.total_borrador.a_texto(), c.total_control.a_texto()) == ("320000.00", "320000.00")
    por_unidad = _por_unidad(c)
    assert por_unidad.get("1A") == ("169000.00", "159000.00", "10000.00")
    assert por_unidad.get("2A") == ("52000.00", "62000.00", "-10000.00")
    assert c.unidades_con_diferencia == 2
    assert c.requiere_aceptacion is True and c.aceptacion is None


def test_una_unidad_con_control_y_sin_saldo_y_otra_con_saldo_y_sin_control(
    mundo: Mundo, sesion: Session
) -> None:
    saldos = [*saldos_base(), ["3C", None, None, None, "1000.00", None]]
    control = [*control_base(), ["2C", "5000.00"]]
    subir(sesion, mundo.super_admin, mundo.torre, archivo(saldos, control))
    por_unidad = _por_unidad(_comparar(sesion, mundo))
    assert por_unidad.get("2C") == ("0.00", "5000.00", "-5000.00")
    assert por_unidad.get("3C") == ("1000.00", "0.00", "1000.00")


def test_cada_unidad_trae_su_id(mundo: Mundo, sesion: Session) -> None:
    subir(sesion, mundo.super_admin, mundo.torre, archivo())
    c = _comparar(sesion, mundo)
    assert {u.unidad: u.unidad_id for u in c.unidades}.get("1A") == unidad_de_la_torre(
        sesion, mundo, "1A"
    )


def test_con_el_padron_existente_compara_contra_sus_unidades(mundo: Mundo, sesion: Session) -> None:
    subir(
        sesion,
        mundo.super_admin,
        mundo.con_padron,
        archivo(
            [["9Z", None, None, None, "700.00", "7.00"]], [["9Z", "700.00"]], con_unidades=False
        ),
    )
    c = _comparar(sesion, mundo, complejo=mundo.con_padron)
    assert _por_unidad(c) == {"9Z": ("707.00", "700.00", "7.00")}


def test_la_comparacion_es_del_borrador_vigente_no_del_descartado(
    mundo: Mundo, sesion: Session
) -> None:
    subir(
        sesion,
        mundo.super_admin,
        mundo.con_padron,
        archivo([["9Z", None, None, None, "100.00", None]], [["9Z", "100.00"]], con_unidades=False),
    )
    segundo = subir(
        sesion,
        mundo.super_admin,
        mundo.con_padron,
        archivo([["9Z", None, None, None, "200.00", None]], [["9Z", "250.00"]], con_unidades=False),
        nombre="corregido.xlsx",
    )
    c = _comparar(sesion, mundo, complejo=mundo.con_padron)
    assert c.importacion_id == segundo.importacion_id
    assert _por_unidad(c) == {"9Z": ("200.00", "250.00", "-50.00")}


def test_sin_un_borrador_vigente_no_hay_comparacion(mundo: Mundo, sesion: Session) -> None:
    with pytest.raises(NoEncontrado):
        _comparar(sesion, mundo)


# --- El aviso de mes entero (E13, E18 del 4c) --------------------------------------------------


def _avisos(c: Any) -> dict[str, str | None]:
    return {u.unidad: u.aviso for u in c.unidades}


def test_mes_entero_avisa_el_mes_de_la_migracion_a_las_unidades_con_deuda(
    mundo: Mundo, sesion: Session
) -> None:
    configurar(sesion, mundo, mundo.torre, "mes_entero", date(2026, 1, 1))
    subir(sesion, mundo.super_admin, mundo.torre, archivo())
    avisos = _avisos(_comparar(sesion, mundo))
    for unidad in ("1A", "1B", "2A"):
        assert avisos.get(unidad) == AVISO, (
            f"{unidad} tiene deuda y debe avisar: {avisos.get(unidad)!r}"
        )
    for unidad in ("2B", "C1"):
        assert avisos.get(unidad) is None, f"{unidad} sólo tiene crédito: no avisa"


def test_proporcional_por_dia_no_avisa(mundo: Mundo, sesion: Session) -> None:
    configurar(sesion, mundo, mundo.torre, "proporcional_por_dia", date(2026, 1, 1))
    subir(sesion, mundo.super_admin, mundo.torre, archivo())
    assert all(a is None for a in _avisos(_comparar(sesion, mundo)).values())


def test_sin_version_de_configuracion_no_avisa(mundo: Mundo, sesion: Session) -> None:
    subir(sesion, mundo.super_admin, mundo.torre, archivo())
    assert all(a is None for a in _avisos(_comparar(sesion, mundo)).values())


def test_vale_la_version_vigente_a_la_fecha_de_migracion_no_la_de_hoy(
    mundo: Mundo, sesion: Session
) -> None:
    """Una versión `mes_entero` que arranca después de la migración (el 01/11) no cuenta."""
    configurar(sesion, mundo, mundo.torre, "proporcional_por_dia", date(2026, 1, 1))
    configurar(sesion, mundo, mundo.torre, "mes_entero", date(2026, 11, 1))
    subir(sesion, mundo.super_admin, mundo.torre, archivo())
    assert all(a is None for a in _avisos(_comparar(sesion, mundo)).values())


def test_el_mes_sale_de_la_fecha_de_migracion_de_la_importacion(
    mundo: Mundo, sesion: Session
) -> None:
    configurar(sesion, mundo, mundo.torre, "mes_entero", date(2026, 1, 1))
    saldos = [["1A", "2026-08", date(2026, 8, 10), "Ordinaria", "80000.00", None]]
    subir(sesion, mundo.super_admin, mundo.torre, archivo(saldos, [["1A", "80000.00"]]),
          fecha=date(2026, 9, 20))  # fmt: skip
    avisos = _avisos(_comparar(sesion, mundo))
    assert avisos.get("1A") == "El primer interés del sistema cubre septiembre de 2026"


# --- Permiso y alcance (D7) ---------------------------------------------------------------------


def test_el_administrador_del_edificio_puede_ver_la_comparacion(
    mundo: Mundo, sesion: Session
) -> None:
    subir(sesion, mundo.super_admin, mundo.torre, archivo())
    assert _comparar(sesion, mundo, mundo.de_la_torre).unidades


@pytest.mark.parametrize("quien", ["contador", "auxiliar"])
def test_sin_permiso_de_importar_no_ve_los_saldos(
    mundo: Mundo, sesion: Session, quien: str
) -> None:
    subir(sesion, mundo.super_admin, mundo.torre, archivo())
    with pytest.raises(SinPermiso):
        _comparar(sesion, mundo, getattr(mundo, quien))


def test_un_administrador_de_otro_edificio_no_lo_ve(mundo: Mundo, sesion: Session) -> None:
    subir(sesion, mundo.super_admin, mundo.torre, archivo())
    with pytest.raises(NoEncontrado):
        _comparar(sesion, mundo, mundo.de_otro)


@pytest.mark.parametrize("quien", ["inexistente", "de_otra_administracion"])
def test_un_edificio_inexistente_o_de_otra_administracion_no_existe(
    mundo: Mundo, sesion: Session, quien: str
) -> None:
    complejo = uuid4() if quien == "inexistente" else mundo.complejo_b
    with pytest.raises(NoEncontrado):
        _comparar(sesion, mundo, complejo=complejo)
