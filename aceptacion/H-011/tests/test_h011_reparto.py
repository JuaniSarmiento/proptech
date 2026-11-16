"""H-011 · el reparto por unidad (C01 a C07, N02, N04)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from ._h011 import (
    OCT,
    Mundo,
    cargar_base,
    cargo,
    configurar,
    gasto,
    plata,
    por_grupo,
    preliquidacion,
    sumas_cierran,
    total_de_cargos,
    unidad,
)

BASE = {
    #       ordinaria,   fondo,     extraordinaria, cargos,     total
    "1A": ("27000.00", "1350.00", "15000.00", "0.00", "43350.00"),
    "1B": ("27000.00", "1350.00", "15000.00", "5000.00", "48350.00"),
    "2A": ("47500.00", "2375.00", "12500.00", "0.00", "62375.00"),
    "2B": ("28500.00", "1425.00", "7500.00", "0.00", "37425.00"),
}


def _importes(cuerpo: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    return {
        u["identificador"]: (
            u["ordinaria"], u["fondo_de_reserva"], u["extraordinaria"],
            str(total_de_cargos(u)), u["intereses"], u["total"], str(u["sin_obligacion"]),
        )
        for u in cuerpo["unidades"]
    }


def _grupo_nuevo(m: Mundo, clave: str, nombre: str, metodo: str, miembros: tuple[str, ...]) -> UUID:
    fila = m.ejecutar(
        "INSERT INTO grupo_de_reparto (administracion_id, complejo_id, clave, nombre, metodo) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (m.admin, m.edificio, clave, nombre, metodo),
    )
    grupo = UUID(str(fila[0]))
    for u in miembros:
        m.ejecutar(
            "INSERT INTO grupo_unidad (administracion_id, complejo_id, grupo_id, unidad_id, "
            "modo_de_coeficientes, coeficiente) VALUES (%s, %s, %s, %s, 'renormalizado', NULL)",
            (m.admin, m.edificio, grupo, m.unidades[u]),
        )
    return grupo


def test_c01_la_base_unidad_por_unidad(mundo: Mundo) -> None:
    """Escenario: La base de los ejemplos"""
    cargar_base(mundo)
    cuerpo = preliquidacion(mundo)
    assert [u["identificador"] for u in cuerpo["unidades"]] == ["1A", "1B", "2A", "2B"], (
        "las unidades tienen que venir todas y en orden natural"
    )
    for identificador, (ordinaria, fondo, extra, cargos, total) in BASE.items():
        u = unidad(cuerpo, identificador)
        assert (u["ordinaria"], u["fondo_de_reserva"], u["extraordinaria"]) == (ordinaria, fondo, extra), (
            f"{identificador}: ordinaria, fondo y extraordinaria {u['ordinaria']}, "
            f"{u['fondo_de_reserva']}, {u['extraordinaria']}; se esperaba {ordinaria}, {fondo}, {extra}"
        )
        assert str(total_de_cargos(u)) == cargos, f"{identificador}: cargos {u['cargos_particulares']}"
        assert u["intereses"] == "0.00", f"{identificador}: sin deuda, el interés es 0,00"
        assert u["total"] == total, f"{identificador}: total {u['total']}, se esperaba {total}"
        assert u["sin_obligacion"] is False
        assert u["unidad_id"] == str(mundo.unidades[identificador])
    multa = unidad(cuerpo, "1B")["cargos_particulares"]
    assert multa == [{"concepto": "Multa", "importe": "5000.00"}], f"el cargo de 1B: {multa}"


def test_c01_c04_la_ordinaria_de_2a_y_2b_por_grupo(mundo: Mundo) -> None:
    cargar_base(mundo)
    cuerpo = preliquidacion(mundo)
    esperado = {"2A": ("22500.00", "25000.00"), "2B": ("13500.00", "15000.00")}
    for identificador, (de_generales, de_ascensor) in esperado.items():
        u = unidad(cuerpo, identificador)
        generales = por_grupo(u, mundo.generales)
        ascensor = por_grupo(u, mundo.ascensor)
        assert generales is not None and generales["ordinaria"] == de_generales, (
            f"{identificador} en Generales: {generales}"
        )
        assert ascensor is not None and ascensor["ordinaria"] == de_ascensor, (
            f"{identificador} en Ascensor: {ascensor}"
        )
        assert ascensor["extraordinaria"] == "0.00"


def test_c02_los_totales(mundo: Mundo) -> None:
    cargar_base(mundo)
    cuerpo = preliquidacion(mundo)
    assert cuerpo["totales"] == {
        "gastos": "190000.00",
        "notas_de_credito": "10000.00",
        "fondo_de_reserva": "6500.00",
        "prorrateado": "186500.00",
        "cargos_particulares": "5000.00",
        "intereses": "0.00",
        "total": "191500.00",
    }, f"totales: {cuerpo['totales']}"
    assert cuerpo["porcentaje_fondo"] == "5.00"
    assert cuerpo["vencimiento"] == "2026-11-10"
    assert cuerpo["periodo"] == "2026-11-01"


def test_c03_mayor_resto(mundo: Mundo) -> None:
    """Escenario: Mayor resto"""
    configurar(mundo, fondo="0.00")
    gasto(mundo, "333.33")
    cuerpo = preliquidacion(mundo)
    obtenido = {u["identificador"]: u["ordinaria"] for u in cuerpo["unidades"]}
    assert obtenido == {"1A": "100.00", "1B": "100.00", "2A": "83.33", "2B": "50.00"}, (
        f"mayor resto con desempate por orden natural: {obtenido}"
    )
    sumas_cierran(cuerpo)


def test_c04_grupo_parcial(mundo: Mundo) -> None:
    """Escenario: Grupo parcial"""
    configurar(mundo)
    gasto(mundo, "40000.00", categoria="Ascensor", grupo=mundo.ascensor)
    cuerpo = preliquidacion(mundo)
    for identificador in ("1A", "1B"):
        u = unidad(cuerpo, identificador)
        assert (u["ordinaria"], u["fondo_de_reserva"], u["total"]) == ("0.00", "0.00", "0.00"), (
            f"{identificador} no está en Ascensor y no paga nada: {u}"
        )
        assert u["sin_obligacion"] is True, f"{identificador} en $0 no recibe obligación"
        assert por_grupo(u, mundo.ascensor) is None, f"{identificador} no participa de Ascensor"
    a, b = unidad(cuerpo, "2A"), unidad(cuerpo, "2B")
    assert (a["ordinaria"], a["fondo_de_reserva"]) == ("25000.00", "1250.00"), f"2A: {a}"
    assert (b["ordinaria"], b["fondo_de_reserva"]) == ("15000.00", "750.00"), f"2B: {b}"
    assert a["sin_obligacion"] is False and b["sin_obligacion"] is False
    sumas_cierran(cuerpo)


def test_c05_por_superficie(mundo: Mundo) -> None:
    configurar(mundo, fondo="0.00")
    mundo.ejecutar("UPDATE unidad SET superficie_m2 = '50.00' WHERE id = %s", (mundo.unidades["1A"],))
    mundo.ejecutar("UPDATE unidad SET superficie_m2 = '150.00' WHERE id = %s", (mundo.unidades["2B"],))
    pileta = _grupo_nuevo(mundo, "pileta", "Pileta", "superficie", ("1A", "2B"))
    gasto(mundo, "1000.00", grupo=pileta)
    cuerpo = preliquidacion(mundo)
    assert unidad(cuerpo, "1A")["ordinaria"] == "250.00", "por superficie: 50 de 200 m²"
    assert unidad(cuerpo, "2B")["ordinaria"] == "750.00", "por superficie: 150 de 200 m²"
    assert unidad(cuerpo, "1B")["ordinaria"] == "0.00"
    sumas_cierran(cuerpo)


def test_c05_en_partes_iguales(mundo: Mundo) -> None:
    configurar(mundo, fondo="0.00")
    cocheras = _grupo_nuevo(mundo, "cocheras", "Cocheras", "partes_iguales", ("1A", "1B", "2A"))
    gasto(mundo, "100.00", grupo=cocheras)
    cuerpo = preliquidacion(mundo)
    obtenido = {u["identificador"]: u["ordinaria"] for u in cuerpo["unidades"]}
    assert obtenido == {"1A": "33.34", "1B": "33.33", "2A": "33.33", "2B": "0.00"}, (
        f"en partes iguales, el centavo que sobra va a 1A por orden natural: {obtenido}"
    )
    sumas_cierran(cuerpo)


def test_c06_el_fondo_no_lleva_cargos(mundo: Mundo) -> None:
    """Escenario: Fondo sin cargos"""
    cargar_base(mundo)
    cuerpo = preliquidacion(mundo)
    a, b = unidad(cuerpo, "1A"), unidad(cuerpo, "1B")
    assert a["fondo_de_reserva"] == b["fondo_de_reserva"] == "1350.00", (
        f"la multa de 1B no sube su fondo: 1A {a['fondo_de_reserva']}, 1B {b['fondo_de_reserva']}"
    )
    assert plata(cuerpo["totales"]["fondo_de_reserva"]) == Decimal("6500.00")


def test_c06_con_fondo_cero(mundo: Mundo) -> None:
    configurar(mundo, fondo="0.00")
    gasto(mundo, "100000.00")
    cuerpo = preliquidacion(mundo)
    assert cuerpo["porcentaje_fondo"] == "0.00"
    assert {u["fondo_de_reserva"] for u in cuerpo["unidades"]} == {"0.00"}
    assert cuerpo["totales"]["fondo_de_reserva"] == "0.00"


def test_c07_categorias_por_bloque(mundo: Mundo) -> None:
    cargar_base(mundo)
    mundo.ejecutar(
        "UPDATE categoria_de_gasto SET nombre = 'Limpieza y orden' WHERE id = %s",
        (mundo.categorias["Limpieza"],),
    )
    cuerpo = preliquidacion(mundo)
    ordinario, extra = cuerpo["bloques"]["ordinario"], cuerpo["bloques"]["extraordinario"]
    assert ordinario["subtotal"] == "130000.00" and extra["subtotal"] == "50000.00"
    por_nombre = {c["nombre"]: (c["importe"], c["porcentaje"]) for c in ordinario["categorias"]}
    assert por_nombre == {
        "Limpieza y orden": ("90000.00", "69.23"),
        "Ascensor": ("40000.00", "30.77"),
    }, f"ordinario por categoría, neto de notas y con el nombre vigente: {por_nombre}"
    assert [(c["nombre"], c["importe"], c["porcentaje"]) for c in extra["categorias"]] == [
        ("Pintura", "50000.00", "100.00")
    ]
    for bloque in (ordinario, extra):
        assert sum((plata(c["importe"]) for c in bloque["categorias"]), Decimal(0)) == plata(
            bloque["subtotal"]
        )
    ids = {c["categoria_id"] for c in ordinario["categorias"]}
    assert str(mundo.categorias["Limpieza"]) in ids


def test_n02_lo_que_no_entra_no_cambia_nada(mundo: Mundo) -> None:
    """Escenario: Lo que no entra"""
    cargar_base(mundo, con_lo_que_no_entra=False)
    antes = _importes(preliquidacion(mundo))
    gasto(mundo, "999.00", estado="borrador")
    gasto(mundo, "777.00", estado="sin_ia")
    gasto(mundo, "555.00", estado="en_revision")
    gasto(mundo, "12345.00", periodo=OCT)
    gasto(mundo, "54321.00", complejo=mundo.otro)
    cargo(mundo, "2A", "3000.00", estado="borrador")
    despues = preliquidacion(mundo)
    assert _importes(despues) == antes, "un gasto que no es aprobado del período y del edificio entró"
    assert despues["totales"]["gastos"] == "190000.00"


def test_n04_las_sumas_cierran(mundo: Mundo) -> None:
    cargar_base(mundo)
    sumas_cierran(preliquidacion(mundo))
