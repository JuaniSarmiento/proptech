"""H-037 (R12, R23, D-169): la validación de lo que propone la IA y el control de importe atípico.

Dominio puro: la IA devuelve valores que no son confiables y cada uno se valida solo contra lo que
existe y está activo en el edificio.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.gastos.dominio.lectura_de_factura import (
    CAMPOS_DE_LA_PROPUESTA,
    FueraDeContrato,
    evaluar_importe,
    validar_propuesta,
)

CATEGORIA, GRUPO = uuid4(), uuid4()
TODOS = frozenset(CAMPOS_DE_LA_PROPUESTA)


def buena(**cambios: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "concepto": "Ascensores, octubre",
        "periodo": "2026-10",
        "categoria_id": str(CATEGORIA),
        "grupo_id": str(GRUPO),
        "importe": "1500.50",
    }
    base.update(cambios)
    return base


def validar(propuesta: Any, completar: frozenset[str] = TODOS):
    return validar_propuesta(propuesta, categorias={CATEGORIA}, grupos={GRUPO}, completar=completar)


def test_una_propuesta_buena_se_aplica_entera() -> None:
    r = validar(buena())
    assert r.concepto == "Ascensores, octubre"
    assert r.periodo == date(2026, 10, 1)
    assert r.categoria_id == CATEGORIA and r.grupo_id == GRUPO
    assert r.importe == Dinero("1500.50")
    assert r.descartados == {}


@pytest.mark.parametrize("propuesta", ["texto", ["l"], 42, None, {}, {"concepto": "x"}])
def test_fuera_de_contrato_si_no_es_un_objeto_o_falta_una_clave(propuesta: Any) -> None:
    with pytest.raises(FueraDeContrato):
        validar(propuesta)


def test_las_claves_de_mas_se_ignoran() -> None:
    r = validar(buena() | {"estado": "aprobado", "proveedor_id": str(uuid4())})
    assert r.descartados == {}


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("periodo", "2026-13"),
        ("periodo", "2026-10-15"),
        ("periodo", "0000-01"),
        ("periodo", 202610),
        ("importe", "1500,50"),
        ("importe", "1500.5"),
        ("importe", "0.00"),
        ("importe", 1500.5),
        ("importe", "1" + "0" * 12 + ".00"),
        ("concepto", "   "),
        ("concepto", "a" * 201),
        ("concepto", "uno\ndos"),
        ("concepto", None),
        ("concepto", 7),
    ],
)
def test_un_campo_invalido_queda_nulo_y_no_tumba_a_los_demas(campo: str, valor: Any) -> None:
    r = validar(buena(**{campo: valor}))
    assert getattr(r, campo) is None
    assert r.descartados == {campo: "invalido"}


def test_el_concepto_se_recorta() -> None:
    assert validar(buena(concepto="  Limpieza  ")).concepto == "Limpieza"


@pytest.mark.parametrize("valor", [str(uuid4()), "no-es-un-uuid", ""])
def test_un_texto_que_no_es_del_edificio_es_fuera_del_vocabulario(valor: str) -> None:
    r = validar(buena(categoria_id=valor, grupo_id=valor))
    assert r.categoria_id is None and r.grupo_id is None
    assert r.descartados == {
        "categoria_id": "fuera_del_vocabulario",
        "grupo_id": "fuera_del_vocabulario",
    }


@pytest.mark.parametrize("valor", [123, None, ["x"], {"id": "x"}])
def test_un_valor_que_no_es_texto_es_invalido(valor: Any) -> None:
    r = validar(buena(categoria_id=valor))
    assert r.descartados == {"categoria_id": "invalido"}


def test_un_id_que_el_edificio_no_ofrece_no_se_aplica_aunque_exista() -> None:
    otro: UUID = uuid4()
    r = validar_propuesta(
        buena(categoria_id=str(otro)), categorias={CATEGORIA}, grupos={GRUPO}, completar=TODOS
    )
    assert r.categoria_id is None


def test_lo_que_ya_tiene_valor_no_se_evalua_ni_se_anota() -> None:
    r = validar(buena(concepto=None, importe="x"), TODOS - {"concepto", "importe"})
    assert r.concepto is None and r.importe is None
    assert r.descartados == {}
    assert r.periodo == date(2026, 10, 1)


# --- R23 ---------------------------------------------------------------------------------------


def historial(*importes: str) -> list[Dinero]:
    return [Dinero(i) for i in importes]


@pytest.mark.parametrize(
    "importe, atipico",
    [
        ("2000.01", True),
        ("2000.00", False),
        ("500.00", False),
        ("499.99", True),
        ("1000.00", False),
    ],
)
def test_atipico_es_estrictamente_mas_del_doble_o_menos_de_la_mitad(
    importe: str, atipico: bool
) -> None:
    r = evaluar_importe(Dinero(importe), historial("1000.00"))
    assert (r is not None) is atipico


def test_el_promedio_es_la_media_aritmetica() -> None:
    r = evaluar_importe(Dinero("4000.01"), historial("1000.00", "1000.00", "4000.00"))
    assert r is not None
    assert r.promedio == Dinero("2000.00") and r.muestras == 3
    assert evaluar_importe(Dinero("4000.00"), historial("1000.00", "1000.00", "4000.00")) is None


def test_el_promedio_se_redondea_medio_hacia_arriba_pero_se_compara_exacto() -> None:
    r = evaluar_importe(Dinero("20.01"), historial("1.00", "1.00", "1.01"))
    assert r is not None
    assert r.promedio == Dinero("1.00")
    assert evaluar_importe(Dinero("0.40"), historial("1.00", "1.00", "1.01")) is not None


def test_sin_historial_no_se_marca() -> None:
    assert evaluar_importe(Dinero("90000.00"), []) is None
