"""H-011 · el interés igual al emitido (C08), la huella (C09) y el orden de los períodos (C10)."""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from ._h011 import (
    DIC,
    MES_ENTERO,
    NOV,
    OCT,
    SEP,
    Mundo,
    anular_libro,
    cargar_base,
    configurar,
    emitir_libro,
    emitir_lo_preliquidado,
    gasto,
    intereses_emitidos_por_unidad,
    nota_de_credito,
    pedir,
    plata,
    preliquidacion,
    sumas_cierran,
    unidad,
)


def _deuda_de_septiembre(m: Mundo, forma: str | None = None) -> None:
    """`1A` debe una ordinaria de septiembre de $100.000 vencida el 10/09; octubre tiene un gasto."""
    if forma:
        configurar(m, fondo="0.00", forma=forma)
    else:
        configurar(m, fondo="0.00")
    emitir_libro(m, SEP, {"1A": ("100000.00", "0.00", "0.00")})
    gasto(m, "1000.00", periodo=OCT)


def _iguales_a_la_emision(m: Mundo, cuerpo: dict) -> None:
    preliquidados = {u["identificador"]: plata(u["intereses"]) for u in cuerpo["unidades"]}
    emitidos = intereses_emitidos_por_unidad(m, emitir_lo_preliquidado(m, cuerpo))
    assert preliquidados == emitidos, (
        f"el interés de la preliquidación {preliquidados} no es el que registró la emisión {emitidos}"
    )


def test_c08_interes_proporcional_igual_al_emitido(mundo: Mundo) -> None:
    """Escenario: Deuda vencida de septiembre"""
    _deuda_de_septiembre(mundo)
    cuerpo = preliquidacion(mundo, OCT)
    assert unidad(cuerpo, "1A")["intereses"] == "2000.00", (
        f"20 días al 0,1% diario de $100.000: {unidad(cuerpo, '1A')['intereses']}"
    )
    assert {unidad(cuerpo, u)["intereses"] for u in ("1B", "2A", "2B")} == {"0.00"}
    assert cuerpo["totales"]["intereses"] == "2000.00"
    sumas_cierran(cuerpo)
    _iguales_a_la_emision(mundo, cuerpo)


def test_c08_interes_mes_entero_igual_al_emitido(mundo: Mundo) -> None:
    _deuda_de_septiembre(mundo, MES_ENTERO)
    cuerpo = preliquidacion(mundo, OCT)
    assert unidad(cuerpo, "1A")["intereses"] == "3000.00", "mes entero: el 3% completo de septiembre"
    _iguales_a_la_emision(mundo, cuerpo)


def test_c08_sin_deuda_el_interes_es_cero_igual_que_al_emitir(mundo: Mundo) -> None:
    cargar_base(mundo)
    cuerpo = preliquidacion(mundo)
    assert cuerpo["totales"]["intereses"] == "0.00"
    _iguales_a_la_emision(mundo, cuerpo)


def test_c09_huella_estable(mundo: Mundo) -> None:
    cargar_base(mundo)
    primera, segunda = preliquidacion(mundo)["huella"], preliquidacion(mundo)["huella"]
    assert isinstance(primera, str) and re.fullmatch(r"[0-9a-f]{64}", primera), (
        f"la huella tiene que ser 64 hexadecimales en minúscula: {primera!r}"
    )
    assert primera == segunda, "dos pedidos sin cambios dan huellas distintas"


def test_c09_la_huella_cambia_con_un_gasto_aprobado(mundo: Mundo) -> None:
    """Escenario: La huella cambia con un gasto aprobado"""
    ids = cargar_base(mundo)
    antes = preliquidacion(mundo)["huella"]
    mundo.ejecutar("UPDATE gasto SET estado = 'aprobado' WHERE id = %s", (ids["borrador"],))
    assert preliquidacion(mundo)["huella"] != antes


def test_c09_la_huella_cambia_con_una_nota_de_credito(mundo: Mundo) -> None:
    ids = cargar_base(mundo)
    antes = preliquidacion(mundo)["huella"]
    nota_de_credito(mundo, ids["limpieza"], "1000.00")
    assert preliquidacion(mundo)["huella"] != antes


def test_c09_la_huella_cambia_con_el_fondo(mundo: Mundo) -> None:
    cargar_base(mundo)
    antes = preliquidacion(mundo)
    configurar(mundo, fondo="10.00", desde=NOV)
    despues = preliquidacion(mundo)
    assert despues["porcentaje_fondo"] == "10.00", "el fondo sale de la versión vigente el 01/11"
    assert despues["huella"] != antes["huella"]


def test_c10_el_primer_periodo_se_preliquida(mundo: Mundo) -> None:
    configurar(mundo)
    gasto(mundo, "1000.00", periodo=DIC)
    assert pedir(mundo, DIC).status_code == 200, "sin emisiones, cualquier período es el primero"


def _conflicto(r: object, motivo: str) -> None:
    assert r.status_code == 409, f"se esperaba 409 {motivo}, llegó {r.status_code}: {r.text[:300]}"  # type: ignore[attr-defined]
    cuerpo = r.json()  # type: ignore[attr-defined]
    assert cuerpo.get("campo") == "periodo" and cuerpo.get("motivo") == motivo, (
        f"se esperaba campo `periodo` y motivo `{motivo}`: {cuerpo}"
    )


def test_c10_el_siguiente_al_emitido(mundo: Mundo) -> None:
    configurar(mundo)
    emitir_libro(mundo, OCT, {"1A": ("100.00", "0.00", "0.00")})
    assert pedir(mundo, NOV).status_code == 200


def test_c10_un_periodo_salteado(mundo: Mundo) -> None:
    """Escenario: Un período salteado"""
    configurar(mundo)
    emitir_libro(mundo, OCT, {"1A": ("100.00", "0.00", "0.00")})
    _conflicto(pedir(mundo, DIC), "periodo_anterior_sin_emitir")


def test_c10_un_periodo_ya_emitido(mundo: Mundo) -> None:
    """Escenario: Un período ya emitido"""
    configurar(mundo)
    emitir_libro(mundo, OCT, {"1A": ("100.00", "0.00", "0.00")})
    _conflicto(pedir(mundo, OCT), "periodo_emitido")


def test_c10_un_periodo_anulado_se_vuelve_a_preliquidar(mundo: Mundo) -> None:
    """Escenario: Un período anulado se vuelve a preliquidar"""
    configurar(mundo)
    emitir_libro(mundo, SEP, {"1A": ("100.00", "0.00", "0.00")})
    octubre = emitir_libro(mundo, OCT, {"1A": ("100.00", "0.00", "0.00")})
    anular_libro(mundo, octubre.emision_id)
    assert pedir(mundo, OCT).status_code == 200, "un período anulado se vuelve a preliquidar"
    _conflicto(pedir(mundo, NOV), "periodo_anterior_sin_emitir")


@pytest.mark.parametrize("periodo", ["2026-13-01", "2026-11-05", "noviembre"])
def test_n03_periodo_mal_escrito(mundo: Mundo, periodo: str) -> None:
    configurar(mundo)
    r = pedir(mundo, periodo)
    assert r.status_code == 422, f"{periodo}: se esperaba 422, llegó {r.status_code}: {r.text[:200]}"


def test_c08_el_total_de_intereses_suma_las_unidades(mundo: Mundo) -> None:
    _deuda_de_septiembre(mundo)
    cuerpo = preliquidacion(mundo, OCT)
    suma = sum((plata(u["intereses"]) for u in cuerpo["unidades"]), Decimal(0))
    assert plata(cuerpo["totales"]["intereses"]) == suma
