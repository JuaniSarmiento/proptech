"""H-004 · C14: `tramo_de_interes` (design D4) no se edita, no se ve desde otra administración,
no se cuelga de otra cuenta y su CHECK frena los tramos mal formados.

Los movimientos de interés se insertan a mano como fila de libro (igual que la fixture de
`test_cc_correcciones.interes`): este archivo prueba la tabla, no el cálculo.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import errors

from .._cuenta_corriente import Mundo, sembrar, sesion_app
from .._edificios import BaseDeEdificio, fijar_tenant
from ..test_umbral_migracion import arranque
from ._h004 import MES_ENTERO, PROPORCIONAL, SEP, dia, emitir, obl, obligacion_de

pytestmark = pytest.mark.integracion


@dataclass(frozen=True)
class Libro:
    mundo: Mundo
    cuenta_0: UUID
    cuenta_1: UUID
    #: Movimientos de interés de la cuenta 0, uno por corte.
    interes: dict[date, UUID]


@pytest.fixture
def libro(base_del_edificio: BaseDeEdificio) -> Libro:
    mundo = sembrar(base_del_edificio)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10)), obl(mundo, 1, dia(9, 10))])
        c0, c1 = (r.cuentas[mundo.unidades[n]] for n in (0, 1))
        o0 = obligacion_de(s, c0, r.emision_id)
        s.commit()
    movimientos: dict[date, UUID] = {}
    with base_del_edificio.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, mundo.admin)
        for corte in (dia(9, 30), dia(10, 31), dia(11, 30), dia(12, 31)):
            m = uuid4()
            c.execute(
                "INSERT INTO movimiento (id, administracion_id, complejo_id, cuenta_id, tipo, "
                "sentido, importe, fecha_valor, registrado_por, request_id, registrado_en, "
                "obligacion_id, componente, corte) VALUES (%s, %s, %s, %s, 'interes', 'debito', "
                "'2000.00', %s, %s, %s, now(), %s, 'interes', %s)",
                (m, mundo.admin, mundo.complejo, c0, corte, mundo.persona, uuid4(), o0, corte),
            )
            movimientos[corte] = m
        c.commit()
    return Libro(mundo, c0, c1, movimientos)


@pytest.fixture
def app(base_del_edificio: BaseDeEdificio, libro: Libro) -> Iterator[psycopg.Connection]:
    with base_del_edificio.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, libro.mundo.admin)
        try:
            yield c
        finally:
            c.rollback()


def exigir_tabla(c: psycopg.Connection) -> None:
    fila = c.execute("SELECT to_regclass('tramo_de_interes')").fetchone()
    assert fila is not None and fila[0] is not None, "falta la tabla tramo_de_interes (0034)"


def tramo(
    c: psycopg.Connection,
    libro: Libro,
    *,
    movimiento: UUID,
    desde: date,
    hasta: date,
    dias: int,
    cuenta: UUID | None = None,
    base: str = "100000.00",
    forma: str = PROPORCIONAL,
    sentido: str = "debito",
) -> UUID:
    t = uuid4()
    c.execute(
        "INSERT INTO tramo_de_interes (id, administracion_id, complejo_id, cuenta_id, "
        "movimiento_id, sentido_del_movimiento, desde, hasta, dias, base, tasa_mensual, "
        "forma_de_calculo, dias_de_gracia, configuracion_id, registrado_en) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '3.00', %s, 0, %s, now())",
        (
            t,
            libro.mundo.admin,
            libro.mundo.complejo,
            cuenta or libro.cuenta_0,
            movimiento,
            sentido,
            desde,
            hasta,
            dias,
            base,
            forma,
            uuid4(),
        ),
    )
    return t


def valido(c: psycopg.Connection, libro: Libro) -> UUID:
    return tramo(
        c, libro, movimiento=libro.interes[dia(9, 30)], desde=dia(9, 11), hasta=dia(9, 30), dias=20
    )


def test_c14_la_tabla_es_de_solo_agregar(app: psycopg.Connection) -> None:
    exigir_tabla(app)
    from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

    assert "tramo_de_interes" in TABLAS_DE_SOLO_AGREGAR


def test_c14_el_detalle_no_se_edita(
    base_del_edificio: BaseDeEdificio, libro: Libro, app: psycopg.Connection
) -> None:
    """Escenario: El detalle no se edita"""
    exigir_tabla(app)
    t = valido(app, libro)
    app.commit()
    fijar_tenant(app, libro.mundo.admin)
    for sentencia in (
        "UPDATE tramo_de_interes SET dias = dias WHERE id = %s",
        "DELETE FROM tramo_de_interes WHERE id = %s",
    ):
        with pytest.raises(errors.InsufficientPrivilege) as e, app.transaction():
            app.execute(sentencia, (t,))
        assert e.value.sqlstate == "42501"
    with arranque(base_del_edificio) as c:
        for sentencia, args in (
            ("UPDATE tramo_de_interes SET dias = dias WHERE id = %s", (t,)),
            ("DELETE FROM tramo_de_interes WHERE id = %s", (t,)),
            ("TRUNCATE tramo_de_interes", ()),
        ):
            with pytest.raises(errors.RaiseException) as e2, c.transaction():
                c.execute(sentencia, args)
            assert e2.value.sqlstate == "P0001"
        fila = c.execute(
            "SELECT desde, hasta, dias FROM tramo_de_interes WHERE id = %s", (t,)
        ).fetchone()
        assert fila == (dia(9, 11), dia(9, 30), 20), "el tramo cambió"


def test_c14_otra_administracion_no_ve_el_detalle(
    base_del_edificio: BaseDeEdificio, libro: Libro, app: psycopg.Connection
) -> None:
    """Escenario: Otra administración no ve el detalle"""
    exigir_tabla(app)
    t = valido(app, libro)
    app.commit()
    with base_del_edificio.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, libro.mundo.admin)
        assert c.execute(
            "SELECT count(*) FROM tramo_de_interes WHERE id = %s", (t,)
        ).fetchone() == (1,)
        c.rollback()
        fijar_tenant(c, libro.mundo.admin_b)
        assert c.execute("SELECT count(*) FROM tramo_de_interes").fetchone() == (0,)
        c.rollback()


def test_c14_un_tramo_no_se_cuelga_de_otra_cuenta(libro: Libro, app: psycopg.Connection) -> None:
    """Escenario: Un tramo no se cuelga de otra cuenta"""
    exigir_tabla(app)
    with pytest.raises(errors.ForeignKeyViolation), app.transaction():
        tramo(
            app,
            libro,
            movimiento=libro.interes[dia(9, 30)],
            desde=dia(9, 11),
            hasta=dia(9, 30),
            dias=20,
            cuenta=libro.cuenta_1,
        )


INVALIDOS: dict[str, dict[str, Any]] = {
    "dias_incoherentes": {
        "corte": dia(9, 30),
        "desde": dia(9, 11),
        "hasta": dia(9, 30),
        "dias": 19,
    },
    "hasta_antes_de_desde": {
        "corte": dia(9, 30),
        "desde": dia(9, 30),
        "hasta": dia(9, 11),
        "dias": -18,
    },
    "base_cero": {
        "corte": dia(9, 30),
        "desde": dia(9, 11),
        "hasta": dia(9, 30),
        "dias": 20,
        "base": "0.00",
    },
    "mes_entero_de_dos_meses": {
        "corte": dia(10, 31),
        "desde": dia(9, 30),
        "hasta": dia(10, 31),
        "dias": 32,
        "forma": MES_ENTERO,
    },
    "mes_entero_sin_fin_de_mes": {
        "corte": dia(10, 31),
        "desde": dia(10, 1),
        "hasta": dia(10, 30),
        "dias": 30,
        "forma": MES_ENTERO,
    },
    "forma_fuera_del_vocabulario": {
        "corte": dia(9, 30),
        "desde": dia(9, 11),
        "hasta": dia(9, 30),
        "dias": 20,
        "forma": "anual",
    },
}


@pytest.mark.parametrize("caso", sorted(INVALIDOS))
def test_c14_el_check_frena_un_tramo_mal_formado(
    libro: Libro, app: psycopg.Connection, caso: str
) -> None:
    exigir_tabla(app)
    datos = dict(INVALIDOS[caso])
    corte = datos.pop("corte")
    with pytest.raises(errors.CheckViolation), app.transaction():
        tramo(app, libro, movimiento=libro.interes[corte], **datos)


def test_c14_un_mes_entero_bien_formado_entra(libro: Libro, app: psycopg.Connection) -> None:
    """Control de los CHECK de mes entero: el mes calendario completo y la fracción hasta fin de
    mes entran."""
    exigir_tabla(app)
    tramo(
        app,
        libro,
        movimiento=libro.interes[dia(10, 31)],
        desde=dia(10, 1),
        hasta=dia(10, 31),
        dias=31,
        forma=MES_ENTERO,
    )
    tramo(
        app,
        libro,
        movimiento=libro.interes[dia(11, 30)],
        desde=dia(11, 16),
        hasta=dia(11, 30),
        dias=15,
        forma=MES_ENTERO,
    )
