"""H-021 · el ajuste del interés cobrado de más (C01 a C08, N01 a N05). Contrato en `aceptacion/H-021/CONTRATO.md`.

El escenario base (HISTORIAS.md, H-021): `1A` y `1B` deben $100.000 de octubre (vencen el 10/10) y transfieren
$100.000 el 05/11. La emisión de noviembre cobra octubre ($2.100: 21 días al 0,1% diario). `1B` confirma antes de
la de diciembre; `1A`, después. Diciembre le cobra a `1A` noviembre entero sobre $100.000 ($3.000); a `1B`, con su
pago imputado el 05/11 (R04: primero los $2.100 de interés, después $97.900 de capital), $500 + 25 × $2,10 =
$552,50. El ajuste de `1A` es $3.000 − $552,50 = $2.447,50.
"""

from __future__ import annotations

import importlib
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from hypothesis import given, settings
from hypothesis import strategies as st

from ._h021 import (
    NOV,
    OCT,
    Mundo,
    ajustes,
    anular,
    configurar_desde,
    confirmar,
    credito_directo,
    emitir,
    estado,
    informar_ok,
    informar_y_confirmar,
    interes_de,
    ordenes,
    residuales_por_periodo,
)

DIC = date(2026, 12, 1)


def _confirmar_1a(m: Mundo, monto: str = "100000.00", fecha: str = "2026-11-05") -> Any:
    m.como("ana")
    pago = informar_ok(m, {"1A": monto}, fecha=fecha, numero="tarde-1a")
    m.como("admin_principal")
    r = confirmar(m, pago)
    assert r.status_code == 200, f"confirmar: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    return r.json()


def _escenario(m: Mundo, monto: str = "100000.00") -> tuple[UUID, UUID, dict[str, Any]]:
    emitir(m, OCT, {"1A": "100000.00", "1B": "100000.00"})
    noviembre = emitir(m, NOV, {"1A": "1000.00", "1B": "1000.00"})
    informar_y_confirmar(m, {"1B": monto}, fecha="2026-11-05", numero="a-tiempo-1b")
    diciembre = emitir(m, DIC, {"1A": "1000.00", "1B": "1000.00"})
    return noviembre, diciembre, _confirmar_1a(m, monto)


def _sin_negativos(m: Mundo, unidad: str) -> None:
    negativos = {k: v for k, v in residuales_por_periodo(m, unidad).items() if Decimal(v) < 0}
    assert not negativos, f"{unidad} tiene residuales negativos: {negativos}"


def _unico(m: Mundo, unidad: str, tipo: str) -> Any:
    filas = m.filas("SELECT id FROM movimiento WHERE tipo = %s AND cuenta_id = "
                    "(SELECT id FROM cuenta WHERE unidad_id = %s)", (tipo, m.unidades[unidad]))
    assert len(filas) == 1, f"{unidad}: se esperaba un `{tipo}`, hay {len(filas)}"
    return filas[0][0]


# --- C01 y C02 -----------------------------------------------------------------------------------------


def test_c01_pago_confirmado_despues_de_una_emision_que_cobro_interes(mundo: Mundo) -> None:
    """Escenario: Pago confirmado después de una emisión que cobró interés"""
    _, diciembre, respuesta = _escenario(mundo)
    assert ajustes(mundo, "1A") == [("2447.50", interes_de(mundo, "1A", diciembre, OCT))], (
        f"un ajuste de $2.447,50 enlazado al interés de diciembre de la obligación de octubre: {ajustes(mundo, '1A')}"
    )
    assert "ajuste_sin_destino" not in respuesta, respuesta
    papeles = mundo.filas("SELECT papel FROM movimiento_de_pago mp JOIN movimiento mv ON mv.id = mp.movimiento_id "
                          "WHERE mv.tipo = 'ajuste_de_interes' AND mv.cuenta_id = (SELECT id FROM cuenta WHERE "
                          "unidad_id = %s)", (mundo.unidades["1A"],))
    assert [f[0] for f in papeles] == ["ajuste_de_interes"], papeles


def test_c02_queda_igual_que_el_confirmado_a_tiempo(mundo: Mundo) -> None:
    _escenario(mundo)
    a, b = residuales_por_periodo(mundo, "1A"), residuales_por_periodo(mundo, "1B")
    assert a == b, f"1A (con ajuste) y 1B (a tiempo) tienen que quedar iguales: 1A {a}, 1B {b}"
    assert estado(mundo, "1A").deuda == estado(mundo, "1B").deuda


# --- C03: mes entero ---------------------------------------------------------------------------------


def test_c03_mes_entero_usa_lo_guardado_en_los_tramos(mundo: Mundo) -> None:
    configurar_desde(mundo, date(2026, 9, 1), forma="mes_entero")
    emitir(mundo, OCT, {"1A": "100000.00", "1B": "100000.00"})
    informar_y_confirmar(mundo, {"1B": "100000.00"}, fecha="2026-10-31", numero="a-tiempo-1b")
    noviembre = emitir(mundo, NOV, {"1A": "1000.00", "1B": "1000.00"})
    diciembre = emitir(mundo, DIC, {"1A": "1000.00", "1B": "1000.00"})
    _confirmar_1a(mundo, fecha="2026-10-31")
    assert ajustes(mundo, "1A") == [("3000.00", interes_de(mundo, "1A", diciembre, OCT))], (
        "mes entero: noviembre se cobra sobre la base del 01/11, que con el pago del 31/10 es cero; octubre (de la "
        f"emisión de noviembre) no cambia: {ajustes(mundo, '1A')}"
    )
    assert interes_de(mundo, "1A", noviembre, OCT) not in {e for _, e in ajustes(mundo, "1A")}
    assert residuales_por_periodo(mundo, "1A") == residuales_por_periodo(mundo, "1B")


# --- C04: sin emisión de por medio -------------------------------------------------------------------


def test_c04_sin_emision_de_por_medio(mundo: Mundo) -> None:
    """Escenario: Sin emisión de por medio"""
    _escenario(mundo)
    assert ajustes(mundo, "1B") == [], "1B confirmó antes de la emisión de diciembre: no hay nada que ajustar"


# --- C05: el ajuste sigue a su interés ---------------------------------------------------------------


def test_c05_el_ajuste_sigue_a_su_interes(mundo: Mundo) -> None:
    """Escenario: El ajuste sigue a su interés"""
    _, diciembre, _ = _escenario(mundo)
    movimientos = len(mundo.filas("SELECT 1 FROM movimiento"))
    anular(mundo, diciembre)
    assert len(mundo.filas("SELECT 1 FROM movimiento")) == movimientos, "anular no tiene que agregar contra-movimientos"
    ajuste = _unico(mundo, "1A", "ajuste_de_interes")
    assert ajuste not in estado(mundo, "1A").movimientos_que_cuentan, "el ajuste de un interés anulado sigue contando"
    assert residuales_por_periodo(mundo, "1A") == residuales_por_periodo(mundo, "1B")


# --- C06: pago parcial -------------------------------------------------------------------------------


def test_c06_pago_parcial(mundo: Mundo) -> None:
    _, diciembre, _ = _escenario(mundo, "50000.00")
    assert ajustes(mundo, "1A") == [("1197.50", interes_de(mundo, "1A", diciembre, OCT))], (
        f"$3.000 − ($500 + 25 × $52,10): {ajustes(mundo, '1A')}"
    )
    assert residuales_por_periodo(mundo, "1A") == residuales_por_periodo(mundo, "1B")


# --- C07: lo que no entra --------------------------------------------------------------------------


def test_c07_el_ajuste_sin_destino(mundo: Mundo) -> None:
    emitir(mundo, OCT, {"1A": "100000.00"})
    emitir(mundo, NOV, {"1A": "1000.00"})
    emitir(mundo, DIC, {"1A": "1000.00"})
    credito_directo(mundo, "1A", "5100.00", date(2026, 12, 10))
    respuesta = _confirmar_1a(mundo)
    assert ajustes(mundo, "1A") == [], f"el interés ya estaba pagado: no entra ningún ajuste: {ajustes(mundo, '1A')}"
    assert respuesta.get("ajuste_sin_destino") == "2500.00", (
        f"con el pago al capital, a diciembre le correspondían $500: quedan afuera $2.500: {respuesta}"
    )
    _sin_negativos(mundo, "1A")


# --- C08: la función pura ---------------------------------------------------------------------------


def _funcion() -> tuple[Any, Any]:
    try:
        modulo = importlib.import_module("proptech_core.cuenta_corriente.dominio.intereses")
    except ImportError as error:
        raise AssertionError(f"no se importa `intereses`: {error}") from None
    funcion, tramo = getattr(modulo, "diferencia_de_interes", None), getattr(modulo, "TramoGuardado", None)
    assert funcion is not None and tramo is not None, "faltan `diferencia_de_interes` y `TramoGuardado`"
    return funcion, tramo


@settings(max_examples=60, deadline=None)
@given(
    dias=st.integers(min_value=1, max_value=60),
    base=st.integers(min_value=0, max_value=10_000_000),
    baja=st.integers(min_value=0, max_value=10_000_000),
    desde_el=st.integers(min_value=0, max_value=59),
)
def test_c08_la_diferencia_nunca_es_negativa_para_un_pago_que_entra(
    dias: int, base: int, baja: int, desde_el: int
) -> None:
    from proptech_core.compartido.porcentaje import Porcentaje

    funcion, tramo = _funcion()
    desde = date(2026, 11, 1)
    hasta = desde + timedelta(days=dias - 1)
    corte = desde + timedelta(days=desde_el)
    antes = Decimal(base) / 100
    despues_valor = max(Decimal(0), antes - Decimal(baja) / 100)

    def base_antes(_dia: date) -> Decimal:
        return antes

    def base_despues(dia: date) -> Decimal:
        return despues_valor if dia > corte else antes

    tramos = [tramo(desde=desde, hasta=hasta, tasa_mensual=Porcentaje("3.00"), forma_de_calculo="proporcional_por_dia")]
    diferencia = funcion(tramos, base_antes, base_despues)
    assert diferencia.decimal >= 0, f"un pago que entra no puede subir el interés: {diferencia}"
    assert funcion(tramos, base_antes, base_antes).decimal == 0, "con la misma base la diferencia es cero"


# --- N01: la configuración de los tramos ---------------------------------------------------------------


def test_n01_usa_la_tasa_guardada_no_la_de_hoy(mundo: Mundo) -> None:
    emitir(mundo, OCT, {"1A": "100000.00", "1B": "100000.00"})
    emitir(mundo, NOV, {"1A": "1000.00", "1B": "1000.00"})
    informar_y_confirmar(mundo, {"1B": "100000.00"}, fecha="2026-11-05", numero="a-tiempo-1b")
    diciembre = emitir(mundo, DIC, {"1A": "1000.00", "1B": "1000.00"})
    configurar_desde(mundo, DIC, tasa="5.00")
    _confirmar_1a(mundo)
    assert ajustes(mundo, "1A") == [("2447.50", interes_de(mundo, "1A", diciembre, OCT))], (
        f"el ajuste se calcula con el 3% de los tramos de diciembre, no con el 5% vigente después: {ajustes(mundo, '1A')}"
    )


# --- N02: el ajuste va antes que el pago ---------------------------------------------------------------


def test_n02_el_ajuste_se_imputa_antes_que_el_pago(mundo: Mundo) -> None:
    _escenario(mundo)
    ajuste = _unico(mundo, "1A", "ajuste_de_interes")
    pago = _unico(mundo, "1A", "pago")
    assert ordenes(mundo, ajuste) and ordenes(mundo, pago), "el ajuste y el pago tienen que tener imputaciones"
    assert max(ordenes(mundo, ajuste)) < min(ordenes(mundo, pago)), "el pago se imputó antes que el ajuste"


# --- N03: sólo los intereses de emisiones posteriores ---------------------------------------------------


def test_n03_no_ajusta_el_interes_de_noviembre(mundo: Mundo) -> None:
    noviembre, _, _ = _escenario(mundo)
    enlazados = {e for _, e in ajustes(mundo, "1A")}
    assert interes_de(mundo, "1A", noviembre, OCT) not in enlazados, "se ajustó el interés de noviembre (período 01/11)"
    assert len(enlazados) == 1


# --- N04: confirmar dos veces --------------------------------------------------------------------------


def test_n04_confirmar_dos_veces_no_ajusta_dos_veces(mundo: Mundo) -> None:
    emitir(mundo, OCT, {"1A": "100000.00"})
    emitir(mundo, NOV, {"1A": "1000.00"})
    emitir(mundo, DIC, {"1A": "1000.00"})
    mundo.como("ana")
    pago = informar_ok(mundo, {"1A": "100000.00"}, fecha="2026-11-05", numero="dos-veces")
    mundo.como("admin_principal")
    for _ in range(2):
        assert confirmar(mundo, pago).status_code == 200
    assert len(ajustes(mundo, "1A")) == 1, ajustes(mundo, "1A")


# --- N05: sin residuales negativos -----------------------------------------------------------------------


def test_n05_sin_residuales_negativos(mundo: Mundo) -> None:
    _escenario(mundo)
    _sin_negativos(mundo, "1A")
    _sin_negativos(mundo, "1B")
