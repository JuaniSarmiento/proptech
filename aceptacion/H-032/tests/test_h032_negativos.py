"""H-032 · lo que no tiene que pasar (N01 a N05).

Cada test arma primero el prorrateo que hoy da 422: falla por aserción en ese 201. Lo que viene después lo
contesta el código existente (la anulación, la emisión, el libro) con el mundo que sembraron los helpers.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from typing import Any
from uuid import UUID

import psycopg
import pytest

from ._h032 import (
    COMPONENTES,
    DIC,
    Mundo,
    anular,
    auditorias,
    cargar_gastos,
    con_prorrateo,
    cuenta_de,
    cuentas_de_persona,
    deuda_de_cuenta,
    el_prorrateo,
    emitir,
    emitir_por_la_api,
    en_el_get,
    movimientos,
    mundo_emitido,
    no_procesable,
    partes_esperadas,
    registrar,
    registrar_ok,
    residuales_anteriores,
    sembrar_anteriores,
    todo,
    total,
    traslados_del_mes,
)

D = Decimal
VENDE = "2026-11-11"


# --- N01: anular un período con prorrateo aplicado ------------------------------------------------------


@pytest.mark.parametrize("via", ["ya_emitido", "al_emitir"])
def test_n01_anular_un_periodo_con_prorrateo_aplicado_da_409(mundo: Mundo, via: str) -> None:
    ana = mundo.personas["ana"]
    cargar_gastos(mundo)
    if via == "ya_emitido":
        emitida = emitir_por_la_api(mundo)
        con_prorrateo(mundo, "1A", [ana], VENDE)
    else:
        con_prorrateo(mundo, "1A", [ana], VENDE)
        emitida = emitir_por_la_api(mundo)
    assert en_el_get(mundo, "1A")[0]["prorrateo"]["estado"] == "aplicado", "precondición: ya está aplicado"
    antes = (todo(mundo), auditorias(mundo, "anular_liquidacion"))
    r = anular(mundo, emitida["liquidacion_id"])
    assert r.status_code == 409, f"se esperaba 409, llegó {r.status_code}: {r.text[:300]}"
    assert (todo(mundo), auditorias(mundo, "anular_liquidacion")) == antes, "no cambia nada, ni auditoría"
    estado = mundo.cliente.get(f"/api/complejos/{mundo.edificio}/liquidaciones/{emitida['liquidacion_id']}")
    assert estado.json()["estado"] == "emitida", "la liquidación sigue emitida"
    assert en_el_get(mundo, "1A")[0]["prorrateo"]["estado"] == "aplicado"


# --- N02: un solo prorrateo por unidad y período --------------------------------------------------------


@pytest.mark.parametrize("emitido", [True, False])
def test_n02_un_segundo_prorrateo_en_la_misma_unidad_y_periodo_da_422(mundo: Mundo, emitido: bool) -> None:
    ana = mundo.personas["ana"]
    cargar_gastos(mundo)
    if emitido:
        emitir_por_la_api(mundo)
    primero = con_prorrateo(mundo, "1A", [ana], VENDE)
    nora = UUID(primero["compradores"][0]["persona_id"])
    antes = todo(mundo)
    otros = [{"nombre": "Otro Comprador", "email": None}]
    no_procesable(registrar(mundo, "1A", [nora], otros, "2026-11-20", expensa_del_mes="prorrateo"))
    assert todo(mundo) == antes, "el rechazo no deja nada: ni cambio, ni persona, ni movimientos"
    registrar_ok(mundo, "1A", [nora], otros, "2026-11-20")  # la expensa entera sí se puede: el 422 era el prorrateo


# --- N03: la parte trasladada no genera interés --------------------------------------------------------


def _intereses(mundo: Mundo, cuenta: UUID) -> Decimal:
    return sum((D(str(m["importe"])) for m in movimientos(mundo, cuenta, "interes")), D("0.00"))


def test_n03_la_parte_trasladada_no_genera_interes_al_emitir_los_periodos_siguientes(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    mundo_emitido(mundo)
    cambio = con_prorrateo(mundo, "1A", [ana], VENDE)
    cuenta = cuentas_de_persona(mundo, ana)[0]
    esperadas = partes_esperadas(mundo, "1A", 10, 30)
    deuda = deuda_de_cuenta(mundo, cuenta)
    assert deuda == total(esperadas) == D(cambio["prorrateo"]["parte_del_vendedor"]), "precondición"
    emitir(mundo, DIC, ("1A", "1B"), {"1A": "10000.00", "1B": "10000.00"})
    assert movimientos(mundo, cuenta, "interes") == [], "el vendedor no recibe interés"
    assert deuda_de_cuenta(mundo, cuenta) == deuda, "su deuda no crece"
    a, testigo = _intereses(mundo, cuenta_de(mundo, "1A")), _intereses(mundo, cuenta_de(mundo, "1B"))
    assert 0 < a < testigo, f"la unidad paga interés sólo por lo que le quedó: {a} contra la testigo {testigo}"
    esperado = testigo * (30 - 10) / 30  # al vendedor le tocaron 10 de 30 días: la unidad conserva 20/30 de la base
    assert abs(a - esperado) <= D("0.05"), f"interés de la unidad {a}, el de lo que le quedó {esperado:.4f}"


# --- N04: todo o nada al emitir ------------------------------------------------------------------------


@contextmanager
def traslados_rotos(mundo: Mundo) -> Iterator[None]:
    """Hace fallar todo `INSERT` de un `traslado` de esta administración, con el superusuario (L-092)."""
    c = mundo.base.contenedor
    with psycopg.connect(host=c.get_container_host_ip(), port=c.get_exposed_port(5432), dbname=mundo.base.nombre,
                         user=c.username, password=c.password, autocommit=True) as conexion:
        conexion.execute(
            "CREATE OR REPLACE FUNCTION public.h032_romper_traslado() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN RAISE EXCEPTION 'traslado roto por la prueba de H-032'; END $$")
        conexion.execute(
            "CREATE TRIGGER h032_romper_traslado BEFORE INSERT ON public.movimiento FOR EACH ROW "
            f"WHEN (NEW.tipo = 'traslado' AND NEW.administracion_id = '{mundo.admin}') "
            "EXECUTE FUNCTION public.h032_romper_traslado()")
        try:
            yield
        finally:
            conexion.execute("DROP TRIGGER IF EXISTS h032_romper_traslado ON public.movimiento")
            conexion.execute("DROP FUNCTION IF EXISTS public.h032_romper_traslado()")


def test_n04_si_el_traslado_falla_al_emitir_la_emision_entera_no_ocurre(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    cargar_gastos(mundo)
    con_prorrateo(mundo, "1A", [ana], VENDE)
    antes = todo(mundo)
    huella = mundo.cliente.get(f"/api/complejos/{mundo.edificio}/periodos/2026-11-01/preliquidacion").json()["huella"]
    cuerpo: dict[str, Any] = {"emision_id": "8d1f6a42-3c57-4b0e-9a11-5e2b7c4d9f30", "huella": huella,
                              "alertas_aceptadas": []}
    with traslados_rotos(mundo):
        try:
            salio = mundo.cliente.post(f"/api/complejos/{mundo.edificio}/periodos/2026-11-01/emision", json=cuerpo)
            fallo = salio.status_code >= 400
        except Exception:  # el cliente de prueba relanza el error del servidor
            fallo = True
        assert fallo, "la emisión no puede salir bien si el traslado falló"
    assert todo(mundo) == antes, "ni emisión, ni liquidación, ni obligaciones, ni nada: todo o nada"
    assert en_el_get(mundo, "1A")[0]["prorrateo"]["estado"] == "pendiente", "el prorrateo sigue pendiente"
    emitir_por_la_api(mundo)  # arreglado el traslado, la misma emisión sale y aplica
    assert en_el_get(mundo, "1A")[0]["prorrateo"]["estado"] == "aplicado"


# --- N05: sólo los tres componentes --------------------------------------------------------------------


def test_n05_el_interes_registrado_no_se_prorratea(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    sembrar_anteriores(mundo)
    mundo_emitido(mundo)
    anteriores = residuales_anteriores(mundo, "1A")
    assert any(k[1] == "interes" for k in anteriores), f"precondición: interés registrado: {anteriores}"
    cambio = con_prorrateo(mundo, "1A", [ana], VENDE)
    assert residuales_anteriores(mundo, "1A") == anteriores, "el interés y el capital anteriores no se mueven"
    traslados = movimientos(mundo, cuenta_de(mundo, "1A"), "traslado")
    assert traslados and {t["componente"] for t in traslados} <= set(COMPONENTES), (
        f"sólo ordinaria, fondo de reserva y extraordinaria: {[t['componente'] for t in traslados]}")
    esperadas = partes_esperadas(mundo, "1A", 10, 30)
    assert deuda_de_cuenta(mundo, cuentas_de_persona(mundo, ana)[0]) == total(esperadas), "el vendedor no debe interés"
    assert traslados_del_mes(mundo, "1A") == esperadas
    assert el_prorrateo(cambio)["parte_del_vendedor"] == format(total(esperadas), ".2f")
