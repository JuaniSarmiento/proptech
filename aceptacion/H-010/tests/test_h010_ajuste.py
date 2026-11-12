"""H-010 · C01 a C07: el ajuste de saldo inicial es una obligación nueva con su motivo (E11, D-155),
genera interés desde el día siguiente a su vencimiento, cuenta en la situación de cobranza y se
repite sin escribir dos veces.
"""

from __future__ import annotations

from datetime import date
from fractions import Fraction
from typing import Any
from uuid import UUID, uuid4

import pytest

from ._h010 import (
    ACCION,
    DIA_DEL_AJUSTE,
    DIC,
    MES_ENTERO,
    MOTIVO,
    NOV,
    OCT,
    PROPORCIONAL,
    TABLA,
    Mundo,
    ajustar,
    ajustar_api,
    ajuste_creado,
    ajustes,
    auditorias,
    cargar_base,
    configurar,
    conflicto,
    conteos,
    cuenta_de,
    emitir,
    en_paralelo,
    estado_de_cuenta,
    exigir_tabla,
    hoy_posibles,
    intereses_de,
    leer,
    movimientos_de,
    obligaciones_de,
    situacion,
)

pytestmark = pytest.mark.integracion

AGOSTO = (date(2026, 8, 1), date(2026, 8, 10), "80000.00", "0.00", "0.00")


def _nueva(
    antes: dict[UUID, tuple[Any, ...]], despues: dict[UUID, tuple[Any, ...]]
) -> tuple[UUID, tuple[Any, ...]]:
    nuevas = {k: v for k, v in despues.items() if k not in antes}
    assert len(nuevas) == 1, f"se espera una sola obligación nueva: {nuevas}"
    return next(iter(nuevas.items()))


# --- C01 · Saldo cargado de menos -----------------------------------------------------------------


def test_c01_saldo_cargado_de_menos(mundo: Mundo) -> None:
    """Escenario: Saldo cargado de menos"""
    cargar_base(mundo)
    antes = obligaciones_de(mundo, "1A")
    assert [v[:5] for v in antes.values()] == [AGOSTO]
    movimientos_antes = movimientos_de(mundo, "1A")
    auditorias_antes = auditorias(mundo)
    r = ajustar(mundo, "1A", "5000.00", dia=DIA_DEL_AJUSTE)
    despues = obligaciones_de(mundo, "1A")
    for clave, valor in antes.items():
        assert despues.get(clave) == valor, "lo cargado antes no cambia (R08)"
    obligacion, (periodo, vencimiento, ordinaria, fondo, extra, emision) = _nueva(antes, despues)
    assert (periodo, vencimiento) == (OCT, DIA_DEL_AJUSTE), (
        "período: el mes de la migración; vencimiento: el día del ajuste (E11)"
    )
    assert (ordinaria, fondo, extra) == ("5000.00", "0.00", "0.00")
    assert emision is None, "la obligación del ajuste no tiene emisión (E11)"
    assert movimientos_de(mundo, "1A") == movimientos_antes, "el ajuste no agrega movimientos"
    assert UUID(str(leer(r, "obligacion_id"))) == obligacion
    assert leer(r, "vencimiento") == DIA_DEL_AJUSTE and leer(r, "periodo") == OCT
    assert str(leer(r, "importe")) == "5000.00" and leer(r, "componente") == "ordinaria"
    filas = ajustes(mundo)
    assert len(filas) == 1, filas
    _id, cuenta, ligada, _operacion, motivo, autor = filas[0]
    assert UUID(str(ligada)) == obligacion and UUID(str(cuenta)) == cuenta_de(mundo, "1A")
    assert motivo == MOTIVO and UUID(str(autor)) == mundo.personas["admin_principal"]
    assert auditorias(mundo) == auditorias_antes + 1, "una auditoría de ajustar_saldo_inicial"


def test_c01_por_la_api(mundo: Mundo) -> None:
    cargar_base(mundo)
    mundo.como("admin_principal")
    operacion = uuid4()
    cuerpo = ajuste_creado(ajustar_api(mundo, "1A", "5000.00", operacion_id=operacion))
    assert cuerpo["operacion_id"] == str(operacion)
    assert cuerpo["unidad_id"] == str(mundo.unidades["1A"])
    assert cuerpo["cuenta_id"] == str(cuenta_de(mundo, "1A"))
    assert (cuerpo["importe"], cuerpo["componente"], cuerpo["motivo"]) == (
        "5000.00",
        "ordinaria",
        MOTIVO,
    )
    assert cuerpo["periodo"] == "2026-10-01"
    assert date.fromisoformat(cuerpo["vencimiento"]) in hoy_posibles(), (
        "por la API el vencimiento es el día del ajuste, no uno retroactivo"
    )
    assert cuerpo["registrado_por"] == str(mundo.personas["admin_principal"])
    assert auditorias(mundo) == 1


@pytest.mark.parametrize(
    ("componente", "columnas"),
    [
        ("fondo_de_reserva", ("0.00", "2500.00", "0.00")),
        ("extraordinaria", ("0.00", "0.00", "2500.00")),
    ],
)
def test_c01_el_importe_va_al_componente_elegido(
    mundo: Mundo, componente: str, columnas: tuple[str, str, str]
) -> None:
    cargar_base(mundo)
    antes = obligaciones_de(mundo, "1A")
    ajuste_creado(ajustar_api(mundo, "1A", "2500.00", componente=componente))
    _obligacion, valores = _nueva(antes, obligaciones_de(mundo, "1A"))
    assert valores[2:5] == columnas, valores


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal"])
def test_c01_los_que_pueden_ajustar(mundo: Mundo, rol: str) -> None:
    """Control de E6: super admin y administrador principal ajustan."""
    cargar_base(mundo)
    mundo.como(rol)
    ajuste_creado(ajustar_api(mundo, "1A"))
    assert auditorias(mundo) == 1


# --- C02 · Unidad en cero -------------------------------------------------------------------------


def test_c02_unidad_en_cero(mundo: Mundo) -> None:
    """Escenario: Unidad en cero"""
    cargar_base(mundo)
    assert cuenta_de(mundo, "5E") is None, "5E se migró sin saldo y no tiene cuenta"
    r = ajustar(mundo, "5E", "2000.00")
    cuenta = cuenta_de(mundo, "5E")
    assert cuenta is not None, "el ajuste crea la cuenta de la unidad"
    assert UUID(str(leer(r, "cuenta_id"))) == cuenta
    valores = list(obligaciones_de(mundo, "5E").values())
    assert [v[:5] for v in valores] == [(OCT, DIA_DEL_AJUSTE, "2000.00", "0.00", "0.00")]
    assert estado_de_cuenta(mundo, "5E").deuda == _dinero("2000.00")


# --- C03 · Unidad con crédito a favor -------------------------------------------------------------


def test_c03_unidad_con_credito_a_favor(mundo: Mundo) -> None:
    """Escenario: Unidad con crédito a favor"""
    cargar_base(mundo)
    antes = estado_de_cuenta(mundo, "4D")
    assert (antes.deuda, antes.credito_a_favor) == (_dinero("0.00"), _dinero("3000.00"))
    ajustar(mundo, "4D", "2000.00")
    despues = estado_de_cuenta(mundo, "4D")
    assert despues.deuda == _dinero("0.00"), "el crédito se imputa a la obligación nueva (R04)"
    assert despues.credito_a_favor == _dinero("1000.00"), "quedan $1.000 a favor"


# --- C04 · El interés del ajuste corre desde el día siguiente -------------------------------------


def _interes_esperado(dias: int, base: str = "5000") -> Fraction:
    return Fraction(base) * Fraction(3, 100) / 30 * dias


def _obligacion_del_ajuste(r: object) -> UUID:
    return UUID(str(leer(r, "obligacion_id")))


def test_c04_interes_del_ajuste(mundo: Mundo) -> None:
    """Escenario: Interés del ajuste"""
    configurar(mundo, PROPORCIONAL)
    cargar_base(mundo)
    r = ajustar(mundo, "1A", "5000.00", dia=DIA_DEL_AJUSTE)
    emitir(mundo, DIC)
    assert _interes_esperado(25) == Fraction(125)
    assert intereses_de(mundo, _obligacion_del_ajuste(r)) == [
        (date(2026, 11, 30), "125.00", [(date(2026, 11, 6), date(2026, 11, 30))])
    ], "25 días, del 06/11 al 30/11, $125,00"


def test_c04_nunca_dias_anteriores_al_ajuste(mundo: Mundo) -> None:
    configurar(mundo, PROPORCIONAL)
    cargar_base(mundo)
    r = ajustar(mundo, "1A", "5000.00", dia=DIA_DEL_AJUSTE)
    emitir(mundo, NOV)  # corte 31/10: el ajuste todavía no venció
    assert intereses_de(mundo, _obligacion_del_ajuste(r)) == [], (
        "el corte del 31/10 no cobra nada del ajuste (vence el 05/11)"
    )
    emitir(mundo, DIC)
    assert [i[:2] for i in intereses_de(mundo, _obligacion_del_ajuste(r))] == [
        (date(2026, 11, 30), "125.00")
    ]


def test_c04_la_gracia_no_corre_el_inicio(mundo: Mundo) -> None:
    """Con 5 días de gracia y el ajuste impago, el interés corre igual desde el 06/11 (R03:
    la gracia decide si corre, no desde cuándo)."""
    configurar(mundo, PROPORCIONAL, gracia=5)
    cargar_base(mundo)
    r = ajustar(mundo, "1A", "5000.00", dia=DIA_DEL_AJUSTE)
    emitir(mundo, DIC)
    assert [i[:2] for i in intereses_de(mundo, _obligacion_del_ajuste(r))] == [
        (date(2026, 11, 30), "125.00")
    ]


# --- C05 · Con mes entero -------------------------------------------------------------------------


def test_c05_mes_entero_cobra_noviembre(mundo: Mundo) -> None:
    configurar(mundo, MES_ENTERO)
    cargar_base(mundo)
    r = ajustar(mundo, "1A", "5000.00", dia=DIA_DEL_AJUSTE)
    emitir(mundo, DIC)
    assert Fraction(5000) * Fraction(3, 100) == Fraction(150)
    assert intereses_de(mundo, _obligacion_del_ajuste(r)) == [
        (date(2026, 11, 30), "150.00", [(date(2026, 11, 6), date(2026, 11, 30))])
    ], "mes entero: la fracción de noviembre cobra el mes, $150,00"


# --- C06 · Cuenta en la situación de cobranza -----------------------------------------------------


def test_c06_cuenta_como_una_liquidacion_cuando_vence(mundo: Mundo) -> None:
    configurar(mundo, PROPORCIONAL)
    cargar_base(mundo)
    ajustar(mundo, "1A", "5000.00", dia=DIA_DEL_AJUSTE)
    el_dia = situacion(mundo, "1A", DIA_DEL_AJUSTE)
    assert el_dia.liquidaciones_vencidas == 1, "el día del vencimiento el ajuste no está vencido"
    assert el_dia.moroso_critico is False
    despues = situacion(mundo, "1A", date(2026, 11, 6))
    assert despues.liquidaciones_vencidas == 2, "agosto y el ajuste: dos liquidaciones vencidas"
    assert despues.moroso_critico is True


# --- C07 · Replay ---------------------------------------------------------------------------------


def test_c07_replay_del_ajuste(mundo: Mundo) -> None:
    """Escenario: Replay del ajuste"""
    cargar_base(mundo)
    operacion = uuid4()
    primero = ajuste_creado(ajustar_api(mundo, "1A", operacion_id=operacion))
    antes = conteos(mundo)
    segundo = ajuste_creado(ajustar_api(mundo, "1A", operacion_id=operacion), codigos=(200, 201))
    assert segundo == primero, "el replay devuelve el mismo ajuste"
    assert conteos(mundo) == antes, "el replay no escribe nada"
    assert len(ajustes(mundo)) == 1 and auditorias(mundo) == 1


def test_c07_replay_por_el_caso_de_uso(mundo: Mundo) -> None:
    cargar_base(mundo)
    operacion = uuid4()
    primero = ajustar(mundo, "1A", operacion_id=operacion)
    antes = conteos(mundo)
    segundo = ajustar(mundo, "1A", operacion_id=operacion)
    assert leer(segundo, "ajuste_id") == leer(primero, "ajuste_id")
    assert conteos(mundo) == antes


def test_c07_dos_pedidos_simultaneos_con_la_misma_operacion(mundo: Mundo) -> None:
    cargar_base(mundo)
    exigir_tabla(mundo)
    operacion = uuid4()
    resultados = en_paralelo(
        lambda: ajustar_api(mundo, "1A", operacion_id=operacion),
        lambda: ajustar_api(mundo, "1A", operacion_id=operacion),
    )
    for r in resultados:
        assert not isinstance(r, BaseException), f"un pedido explotó: {r!r}"
        assert r.status_code in (200, 201), f"los dos devuelven el ajuste: {r.status_code} {r.text}"
    assert resultados[0].json()["ajuste_id"] == resultados[1].json()["ajuste_id"]
    assert len(ajustes(mundo)) == 1, f"un solo ajuste en {TABLA}"
    assert auditorias(mundo, ACCION) == 1


def test_c07_el_mismo_pedido_despues_de_otro_ajuste(mundo: Mundo) -> None:
    """Dos ajustes con operaciones distintas son dos ajustes; repetir el primero no suma nada."""
    cargar_base(mundo)
    operacion = uuid4()
    ajuste_creado(ajustar_api(mundo, "1A", "5000.00", operacion_id=operacion))
    ajuste_creado(ajustar_api(mundo, "1A", "1000.00"))
    antes = conteos(mundo)
    ajuste_creado(ajustar_api(mundo, "1A", "5000.00", operacion_id=operacion), codigos=(200, 201))
    assert conteos(mundo) == antes
    assert len(ajustes(mundo)) == 2
    conflicto(ajustar_api(mundo, "1A", "1000.00", operacion_id=operacion), "operacion_id")


def _dinero(texto: str) -> object:
    from proptech_core.compartido.dinero import Dinero

    return Dinero(texto)
