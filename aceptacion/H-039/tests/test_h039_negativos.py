"""H-039 · lo que no tiene que pasar (N01 a N04). Contrato en `aceptacion/H-039/CONTRATO.md`."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from ._h039 import (
    Mundo,
    anular_liquidacion,
    base_dos_meses,
    del_administrador,
    detalle_de,
    detalle_ok,
    distribuciones,
    emitir_otro_edificio,
    en_paralelo,
    lista_de,
    lista_ok,
    no_encontrado,
)

# --- N01: lo que no es de la persona no existe ----------------------------------------------------------


def test_n01_la_unidad_ajena_del_mismo_edificio_da_404_en_la_lista_y_en_el_detalle(mundo: Mundo) -> None:
    """Escenario: Ana pide la `2A` de Dora"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    assert [f["liquidacion_id"] for f in lista_ok(mundo, "1A")] == [meses.liq_nov, meses.liq_oct], "control: la suya"
    no_encontrado(lista_de(mundo, "2A"), "lista de 2A")
    no_encontrado(detalle_de(mundo, "2A", meses.liq_nov), "detalle de 2A")
    assert del_administrador(mundo, meses.liq_nov)["estado"] == "emitida", "un 404 no distribuye nada"


def test_n01_la_unidad_de_otro_edificio_de_la_administracion_da_404(mundo: Mundo) -> None:
    """Escenario: Beto pide la `9A` del otro edificio"""
    meses = base_dos_meses(mundo)
    mundo.como("beto")
    assert len(lista_ok(mundo, "1B")) == 2, "control: la suya"
    no_encontrado(lista_de(mundo, "9A"), "lista de 9A")
    no_encontrado(detalle_de(mundo, "9A", meses.liq_nov), "detalle de 9A")


def test_n01_la_unidad_de_otra_administracion_o_inexistente_da_404(mundo: Mundo) -> None:
    """Escenario: Ana pide la unidad de otra administración y una que no existe"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    assert len(lista_ok(mundo, "1A")) == 2, "control: la suya"
    for unidad in (mundo.unidad_b, uuid4()):
        no_encontrado(lista_de(mundo, unidad), f"lista de {unidad}")
        no_encontrado(detalle_de(mundo, unidad, meses.liq_nov), f"detalle de {unidad}")


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal", "contador", "consejo"])
def test_n01_el_personal_sin_vinculo_no_tiene_unidades_en_el_portal(mundo: Mundo, rol: str) -> None:
    """Escenario: el personal pide la `1A` por el portal"""
    meses = base_dos_meses(mundo)
    mundo.como(rol)
    no_encontrado(lista_de(mundo, "1A"), f"lista de 1A como {rol}")
    no_encontrado(detalle_de(mundo, "1A", meses.liq_nov), f"detalle de 1A como {rol}")


def test_n01_una_liquidacion_anulada_o_inexistente_da_404_y_no_se_ve_por_otra_unidad(mundo: Mundo) -> None:
    """Escenario: noviembre anulada; una liquidación que no existe; Ana pide la de octubre por la `1A`"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    assert detalle_ok(mundo, "1A", meses.liq_oct)["periodo"] == "2026-10-01", "control: octubre responde"
    mundo.como("super_admin")
    anular_liquidacion(mundo, meses.liq_nov)
    mundo.como("ana")
    no_encontrado(detalle_de(mundo, "1A", meses.liq_nov), "detalle de una anulada")
    no_encontrado(detalle_de(mundo, "1A", str(uuid4())), "detalle de una que no existe")
    assert distribuciones(mundo, str(meses.noviembre["emision_id"])) == [], "una anulada no se distribuye"


def test_n01_la_liquidacion_de_otro_edificio_no_se_ve_por_una_unidad_propia(mundo: Mundo) -> None:
    """Escenario: Ana pide por su `1A` la liquidación del otro edificio (donde tiene la `9A`), y al revés"""
    meses = base_dos_meses(mundo)
    ajena = emitir_otro_edificio(mundo)
    mundo.como("ana")
    assert detalle_ok(mundo, "9A", ajena)["periodo"] == "2026-10-01", "control: por la 9A sí se ve la del otro edificio"
    no_encontrado(detalle_de(mundo, "1A", ajena), "la liquidación del otro edificio por la 1A")
    no_encontrado(detalle_de(mundo, "9A", meses.liq_nov), "la liquidación de la torre por la 9A")
    assert [f["liquidacion_id"] for f in lista_ok(mundo, "1A")] == [meses.liq_nov, meses.liq_oct]
    assert [f["liquidacion_id"] for f in lista_ok(mundo, "9A")] == [ajena]


# --- N02: nunca datos de otra unidad ---------------------------------------------------------------------


def test_n02_el_detalle_no_trae_datos_de_otra_unidad(mundo: Mundo) -> None:
    """Escenario: Ana lee noviembre de su `1A`; ni la composición del grupo, ni las otras unidades ni sus dueños"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    d = detalle_ok(mundo, "1A", meses.liq_nov)
    texto = json.dumps(d, ensure_ascii=False)
    for clave in ("unidades", "composicion", "alertas_aceptadas", "emitida_por", "huella", "saldo_anterior"):
        assert f'"{clave}"' not in texto, f"el detalle trae `{clave}`"
    for otra in ("1B", "2A", "2B"):
        assert str(mundo.unidades[otra]) not in texto, f"el id de la {otra} está en el detalle"
        assert f'"{otra}"' not in texto, f"el identificador {otra} está en el detalle"
    for nombre in ("Carla", "Beto", "Dora", "Multa"):
        assert nombre not in texto, f"`{nombre}` (de otra unidad) está en el detalle"
    assert "65000.00" not in texto and "51500.00" not in texto, "el total de otra unidad está en el detalle"
    assert d["cargos_particulares"] == [], "la multa es de la 1B, no de la 1A"


def test_n02_las_unidades_de_dos_vinculos_no_se_mezclan(mundo: Mundo) -> None:
    """Escenario: Carla (propietaria) y Beto (inquilino) de la `1B` leen lo suyo, sin la unidad de Ana"""
    meses = base_dos_meses(mundo)
    for quien, inquilino in (("carla", False), ("beto", True)):
        mundo.como(quien)
        d = detalle_ok(mundo, "1B", meses.liq_nov, inquilino=inquilino)
        texto = json.dumps(d, ensure_ascii=False)
        assert str(mundo.unidades["1A"]) not in texto and str(mundo.unidades["2B"]) not in texto, texto
        assert "Ana" not in texto and "46500.00" not in texto, texto


# --- N03: el inquilino nunca recibe lo extraordinario ----------------------------------------------------


def test_n03_el_inquilino_no_recibe_nada_extraordinario_ni_en_la_lista_ni_en_el_detalle_ni_en_la_comparacion(
    mundo: Mundo,
) -> None:
    """Escenario: Beto lee noviembre y octubre (los dos tienen Pintura extraordinaria) y su lista"""
    meses = base_dos_meses(mundo)
    mundo.como("beto")
    cuerpos = [json.dumps(lista_ok(mundo, "1B"), ensure_ascii=False)]
    for liquidacion in (meses.liq_nov, meses.liq_oct):
        cuerpos.append(json.dumps(detalle_ok(mundo, "1B", liquidacion, inquilino=True), ensure_ascii=False))
    for texto in cuerpos:
        assert "extraordinari" not in texto.lower(), f"aparece lo extraordinario: {texto[:400]}"
        assert "Pintura" not in texto, f"aparece la categoría extraordinaria: {texto[:400]}"
        for monto in ("15000.00", "6000.00", "50000.00", "51500.00", "31200.00"):
            assert f'"{monto}"' not in texto, f"aparece {monto}: {texto[:400]}"
    nov = json.loads(cuerpos[1])
    assert nov["comparacion"] is not None and all(
        c["bloque"] == "ordinario" for c in nov["comparacion"]["categorias"]), nov["comparacion"]
    assert nov["comparacion"]["total_anterior"] == "25200.00", nov["comparacion"]


# --- N04: dos lecturas a la vez distribuyen una sola vez -------------------------------------------------


def test_n04_dos_lecturas_simultaneas_distribuyen_una_sola_vez(mundo: Mundo) -> None:
    """Escenario: Ana abre noviembre desde dos pantallas a la vez (su `1A` y su `2B`)"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    emision = str(meses.noviembre["emision_id"])
    assert distribuciones(mundo, emision) == [], "control: sin distribuir"
    respuestas = en_paralelo(
        lambda: detalle_de(mundo, "1A", meses.liq_nov),
        lambda: detalle_de(mundo, "2B", meses.liq_nov),
        lambda: detalle_de(mundo, "1A", meses.liq_nov),
    )
    for r in respuestas:
        assert not isinstance(r, BaseException), f"una lectura se rompió: {r!r}"
        assert r.status_code == 200, f"se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    eventos = distribuciones(mundo, emision)
    assert [e[0] for e in eventos] == ["portal"], f"una sola distribución, por el portal: {eventos}"
