"""H-009 · C01 a C05: confirmar el borrador carga el saldo inicial del 4c, pasa el edificio y la
importación a `confirmada`, audita, deja cada cosa ligada a su fila del Excel, y el interés corre
desde el día siguiente a la migración.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction
from uuid import uuid4

import pytest

from .._cuenta_corriente import sesion_app
from ._h009 import (
    ACCION,
    ARCHIVO,
    PROPORCIONAL,
    Mundo,
    aceptacion_creada,
    aceptar,
    archivo,
    auditorias,
    cargas,
    configurar,
    confirmacion_creada,
    confirmar,
    control_base,
    estado_de,
    estado_del_edificio,
    movimientos_de,
    obligaciones_de,
    origenes,
    saldos_de_la_spec,
    subir,
)

pytestmark = pytest.mark.integracion

AGO, SEP, OCT, NOV = (date(2026, m, 1) for m in (8, 9, 10, 11))
MIGRACION = date(2026, 10, 15)


def _libro_de_la_base(m: Mundo) -> None:
    """El libro tiene exactamente las obligaciones, intereses importados y créditos del borrador
    de la base."""
    assert obligaciones_de(m, "1A") == {
        AGO: ("80000.00", "0.00", "0.00", date(2026, 8, 10)),
        SEP: ("85000.00", "0.00", "0.00", date(2026, 9, 10)),
    }, obligaciones_de(m, "1A")
    assert obligaciones_de(m, "1B") == {
        SEP: ("85000.00", "0.00", "20000.00", date(2026, 9, 10)),
    }, "las dos filas de septiembre de 1B forman una sola obligación (E16 del 4c)"
    assert obligaciones_de(m, "2A") == {
        OCT: ("50000.00", "0.00", "0.00", MIGRACION),
    }, "el total único vence en la migración, período del mes de la migración"
    assert obligaciones_de(m, "2B") == {} and obligaciones_de(m, "4D") == {}
    assert movimientos_de(m, "1A") == [("interes", "debito", "4000.00", MIGRACION)]
    assert movimientos_de(m, "2A") == [("interes", "debito", "2000.00", MIGRACION)]
    assert movimientos_de(m, "2B") == [("saldo_inicial", "credito", "3000.00", None)]
    assert movimientos_de(m, "4D") == [("saldo_inicial", "credito", "3000.00", None)]
    assert movimientos_de(m, "1B") == [] and obligaciones_de(m, "3C") == {}


# --- C01 · Confirmar sin diferencias --------------------------------------------------------------


def test_c01_confirmar_sin_diferencias(mundo: Mundo) -> None:
    """Escenario: Confirmar sin diferencias"""
    cuerpo = subir(mundo)
    mundo.como("admin_principal")
    antes = datetime.now().astimezone()
    confirmado = confirmacion_creada(confirmar(mundo, cuerpo["importacion_id"]))
    assert confirmado["importacion_id"] == cuerpo["importacion_id"]
    assert confirmado["estado_migracion"] == "confirmada"
    assert confirmado["confirmada_por"] == str(mundo.personas["admin_principal"])
    assert datetime.fromisoformat(confirmado["confirmada_en"]) >= antes.replace(microsecond=0)
    _libro_de_la_base(mundo)
    assert estado_del_edificio(mundo) == "confirmada"
    assert estado_de(mundo, cuerpo["importacion_id"]) == "confirmada"
    assert auditorias(mundo, ACCION) == 1, "una auditoría de confirmar_saldos_iniciales"
    lista = cargas(mundo)
    assert len(lista) == 1, f"una sola carga de saldo inicial: {lista}"
    carga_id, operacion_id, origen, nombre, fecha = lista[0]
    assert str(carga_id) == confirmado["carga_id"]
    assert str(operacion_id) == cuerpo["importacion_id"], (
        "la carga usa el id de la importación como operacion_id (D7)"
    )
    assert (origen, nombre, fecha) == ("importador", ARCHIVO, MIGRACION)


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal"])
def test_c01_los_que_pueden_confirmar(mundo: Mundo, rol: str) -> None:
    """Control de E6: super admin y administrador principal confirman."""
    cuerpo = subir(mundo)
    mundo.como(rol)
    confirmacion_creada(confirmar(mundo, cuerpo["importacion_id"]))
    assert estado_del_edificio(mundo) == "confirmada"


# --- C02 · La suma importada coincide con el archivo ----------------------------------------------


def test_c02_los_totales_son_los_del_borrador(mundo: Mundo) -> None:
    cuerpo = subir(mundo)
    totales = confirmacion_creada(confirmar(mundo, cuerpo["importacion_id"]))["totales"]
    capital = Fraction("80000") + Fraction("85000") + Fraction("85000") + Fraction("20000")
    capital += Fraction("50000")
    assert capital == Fraction("320000")
    assert totales == {
        "capital": "320000.00",
        "interes_importado": "6000.00",
        "credito": "6000.00",
    }, totales


def test_c02_la_suma_importada_coincide_con_el_archivo(mundo: Mundo) -> None:
    """Escenario: La suma importada coincide con el archivo"""
    saldos, control = saldos_de_la_spec()
    capital = sum((Fraction(Decimal(f[4])) for f in saldos if Decimal(f[4]) > 0), start=Fraction(0))
    interes = sum((Fraction(Decimal(f[5])) for f in saldos if f[5]), start=Fraction(0))
    credito = sum(
        (-Fraction(Decimal(f[4])) for f in saldos if Decimal(f[4]) < 0), start=Fraction(0)
    )
    assert (capital, interes, credito) == (Fraction(215300), Fraction(6000), Fraction(3000))
    cuerpo = subir(mundo, archivo(saldos=saldos, control=control))
    totales = confirmacion_creada(confirmar(mundo, cuerpo["importacion_id"]))["totales"]
    assert totales == {
        "capital": "215300.00",
        "interes_importado": "6000.00",
        "credito": "3000.00",
    }, totales


# --- C03 · Con diferencias aceptadas, la carga es la del borrador ---------------------------------


def test_c03_con_diferencias_aceptadas_se_carga_el_borrador(mundo: Mundo) -> None:
    control = control_base()
    control[0][1] = "159000.00"  # 1A según el administrador: $10.000 menos
    control[2][1] = "62000.00"  # 2A según el administrador: $10.000 más
    cuerpo = subir(mundo, archivo(control=control))
    aceptacion_creada(aceptar(mundo, cuerpo["importacion_id"]))
    confirmado = confirmacion_creada(confirmar(mundo, cuerpo["importacion_id"]))
    assert confirmado["totales"]["capital"] == "320000.00", "la carga es la del borrador"
    _libro_de_la_base(mundo)
    assert estado_del_edificio(mundo) == "confirmada"


# --- C04 · Cada cosa queda ligada a su fila del Excel ---------------------------------------------


def test_c04_cada_obligacion_y_credito_queda_ligado_a_su_fila(mundo: Mundo) -> None:
    cuerpo = subir(mundo)
    confirmacion_creada(confirmar(mundo, cuerpo["importacion_id"]))
    esperado = {
        ("1A", 2, "obligacion", AGO),
        ("1A", 2, "interes", AGO),
        ("1A", 3, "obligacion", SEP),
        ("1B", 4, "obligacion", SEP),
        ("1B", 5, "obligacion", SEP),
        ("2A", 6, "obligacion", OCT),
        ("2A", 6, "interes", OCT),
        ("2B", 7, "saldo_inicial", None),
        ("4D", 8, "saldo_inicial", None),
    }
    assert origenes(mundo) == esperado, origenes(mundo)
    assert [(c[2], c[3]) for c in cargas(mundo)] == [("importador", ARCHIVO)], (
        "la carga guarda el nombre del archivo"
    )


# --- C05 · Después de confirmar, el interés corre desde la migración ------------------------------


def test_c05_el_interes_corre_desde_el_dia_siguiente_a_la_migracion(mundo: Mundo) -> None:
    from proptech_core.acceso.dominio.identidad import Identidad
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import emisiones
    from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

    configurar(mundo, PROPORCIONAL)  # 3% mensual proporcional, vigente desde el 01/01/2026
    cuerpo = subir(mundo)
    confirmacion_creada(confirmar(mundo, cuerpo["importacion_id"]))
    identidad = Identidad(mundo.admin, mundo.personas["super_admin"])
    with sesion_app(mundo.base, mundo.admin) as s:
        emisiones.registrar_emision(
            s,
            identidad,
            emision_id=uuid4(),
            complejo_id=mundo.edificio,
            periodo=NOV,
            obligaciones=[
                ObligacionAEmitir(
                    mundo.unidades["5E"],
                    date(2026, 11, 10),
                    Dinero("1.00"),
                    Dinero("0.00"),
                    Dinero("0.00"),
                )
            ],
            request_id=uuid4(),
        )
        s.commit()
    # 16 días (16/10 al 31/10) al 3% mensual / 30 sobre $80.000 y sobre $85.000.
    dias = 16
    agosto = Fraction(80000) * Fraction(3, 100) / 30 * dias
    septiembre = Fraction(85000) * Fraction(3, 100) / 30 * dias
    assert (agosto, septiembre) == (Fraction(1280), Fraction(1360))
    intereses = sorted(
        mundo.filas(
            "SELECT o.periodo, mv.importe::text FROM movimiento mv "
            "JOIN obligacion o ON o.id = mv.obligacion_id JOIN cuenta c ON c.id = mv.cuenta_id "
            "WHERE c.unidad_id = %s AND mv.tipo = 'interes' AND mv.corte = %s",
            (mundo.unidades["1A"], date(2026, 10, 31)),
        )
    )
    assert intereses == [(AGO, "1280.00"), (SEP, "1360.00")], (
        f"el interés de noviembre de 1A corre desde el 16/10, no desde el vencimiento: {intereses}"
    )
