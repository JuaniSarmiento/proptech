"""H-006 · C11 y C14 a C16: la situación de cobranza es una lectura, respeta el tenant, exige
configuración vigente a la fecha y deja afuera las cuentas de persona (spec `situacion-de-cobranza`,
design D6)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from proptech_core.cuenta_corriente.aplicacion.errores import Conflicto, NoEncontrado

from .._cuenta_corriente import Mundo, sembrar, sesion_app
from .._edificios import BaseDeEdificio
from ._h006 import (
    AGO,
    SEP,
    configurar,
    cuenta_de,
    de_cuenta,
    del_edificio,
    dia,
    emitir,
    leer,
    moroso,
    obl,
    sentencias,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


# --- C11 · Es una lectura ---------------------------------------------------------------------


def test_c11_es_una_lectura_sin_escrituras_ni_candados(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, AGO, [obl(mundo, 0, dia(8, 10), "80000.00")])
        r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10), "85000.00")])
        cuenta = r.cuentas[mundo.unidades[0]]
        vistas = sentencias(s)
        assert moroso(de_cuenta(s, cuenta, dia(9, 30))), "control: la lectura corrió"
        assert del_edificio(s, mundo.complejo, dia(9, 30)), "control: el listado corrió"
        escrituras = [
            x for x in vistas if x.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        ]
        assert escrituras == [], f"la situación escribió: {escrituras[:1]}"
        candados = [
            x
            for x in vistas
            if "FOR UPDATE" in x.upper()
            or "FOR NO KEY UPDATE" in x.upper()
            or "PG_ADVISORY" in x.upper()
        ]
        assert candados == [], f"la situación tomó candados: {candados[:1]}"


# --- C14 · Otra administración ----------------------------------------------------------------


def test_c14_edificio_de_otra_administracion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Edificio de otra administración"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10), "85000.00")])
        assert del_edificio(s, mundo.complejo, dia(9, 30)), "control: A ve su edificio"
    with sesion_app(base_del_edificio, mundo.admin_b) as s_b:
        with pytest.raises(NoEncontrado):
            del_edificio(s_b, mundo.complejo, dia(9, 30))


def test_c14_cuenta_de_otra_administracion(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10), "85000.00")])
        cuenta = r.cuentas[mundo.unidades[0]]
        assert de_cuenta(s, cuenta, dia(9, 30)) is not None, "control: A ve su cuenta"
    with sesion_app(base_del_edificio, mundo.admin_b) as s_b:
        with pytest.raises(NoEncontrado):
            de_cuenta(s_b, cuenta, dia(9, 30))


# --- C15 · Sin configuración vigente a la fecha -----------------------------------------------


def test_c15_sin_configuracion(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Sin configuración"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10), "85000.00")])
        cuenta = r.cuentas[mundo.unidades[0]]
        with pytest.raises(Conflicto) as e:
            del_edificio(s, mundo.complejo, dia(9, 30))
        assert e.value.campo == "configuracion"
        with pytest.raises(Conflicto) as e2:
            de_cuenta(s, cuenta, dia(9, 30))
        assert e2.value.campo == "configuracion"


def test_c15_solo_una_version_futura(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    configurar(base_del_edificio, mundo, desde=dia(10, 1))
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10), "85000.00")])
        cuenta = r.cuentas[mundo.unidades[0]]
        with pytest.raises(Conflicto) as e:
            de_cuenta(s, cuenta, dia(9, 30))
        assert e.value.campo == "configuracion"
        assert moroso(de_cuenta(s, cuenta, dia(10, 31))) is False, (
            "control: con la versión ya vigente, la situación responde"
        )


# --- C16 · Cuentas de persona fuera -----------------------------------------------------------


def test_c16_las_cuentas_de_persona_no_aparecen_en_el_listado(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta_persona, ahora = uuid4(), datetime(2026, 9, 1, 12, tzinfo=UTC)
        s.execute(
            text(
                "INSERT INTO cuenta (id, administracion_id, complejo_id, persona_id, creada_en) "
                "VALUES (:id, :adm, :c, :p, :en)"
            ),
            {
                "id": cuenta_persona,
                "adm": mundo.admin,
                "c": mundo.complejo,
                "p": mundo.persona,
                "en": ahora,
            },
        )
        s.execute(
            text(
                "INSERT INTO obligacion (id, administracion_id, complejo_id, cuenta_id, "
                "operacion_id, periodo, vencimiento, ordinaria, fondo_de_reserva, "
                "extraordinaria, registrada_en) "
                "VALUES (:id, :adm, :c, :cuenta, :op, :p, :v, '100000.00', '0.00', '0.00', :en)"
            ),
            {
                "id": uuid4(),
                "adm": mundo.admin,
                "c": mundo.complejo,
                "cuenta": cuenta_persona,
                "op": uuid4(),
                "p": AGO,
                "v": dia(8, 10),
                "en": ahora,
            },
        )
        s.commit()
        s.begin()
        emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10), "85000.00")])
        listado = del_edificio(s, mundo.complejo, dia(9, 30))
        cuentas = {UUID(str(leer(x, "cuenta_id"))) for x in listado}
        assert cuenta_de(s, mundo.unidades[0]) in cuentas, "control: la cuenta de unidad está"
        assert cuenta_persona not in cuentas, "la cuenta de persona queda fuera (4d)"
