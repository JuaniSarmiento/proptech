"""H-008 · C01 a C08, C10 y C11 (backend): el borrador de saldos y su comparación."""

from __future__ import annotations

from datetime import date

import pytest

from ._h008 import (
    AVISO,
    MES_ENTERO,
    PROPORCIONAL,
    Mundo,
    archivo,
    avisos,
    comparacion,
    configurar,
    control_base,
    estado_de,
    filas_del_borrador,
    libro_del_edificio,
    por_unidad,
    saldos_base,
    subir,
)

pytestmark = pytest.mark.integracion


# --- C01 a C03 · Las filas quedan en el borrador -------------------------------------------------


def test_c01_dos_periodos_quedan_en_el_borrador(mundo: Mundo) -> None:
    cuerpo = subir(mundo)
    assert cuerpo["filas_de_saldo"] == 7, f"siete filas de saldo: {cuerpo}"
    filas = [f for f in filas_del_borrador(mundo, cuerpo["importacion_id"]) if f[0] == "1A"]
    assert filas == [
        (
            "1A",
            2,
            "detalle",
            date(2026, 8, 1),
            date(2026, 8, 10),
            "ordinaria",
            "80000.00",
            "4000.00",
        ),
        ("1A", 3, "detalle", date(2026, 9, 1), date(2026, 9, 10), "ordinaria", "85000.00", "0.00"),
    ], f"las dos filas de 1A con su número de fila del Excel: {filas}"


def test_c02_dos_conceptos_del_mismo_periodo(mundo: Mundo) -> None:
    cuerpo = subir(mundo)
    filas = [f for f in filas_del_borrador(mundo, cuerpo["importacion_id"]) if f[0] == "1B"]
    assert filas == [
        ("1B", 4, "detalle", date(2026, 9, 1), date(2026, 9, 10), "ordinaria", "85000.00", "0.00"),
        (
            "1B",
            5,
            "detalle",
            date(2026, 9, 1),
            date(2026, 9, 10),
            "extraordinaria",
            "20000.00",
            "0.00",
        ),
    ], f"dos filas del mismo período, cada una con su concepto: {filas}"


def test_c03_total_unico_y_credito(mundo: Mundo) -> None:
    cuerpo = subir(mundo)
    filas = {f[0]: f for f in filas_del_borrador(mundo, cuerpo["importacion_id"])}
    assert filas["2A"] == ("2A", 6, "total", None, None, None, "50000.00", "2000.00"), filas["2A"]
    assert filas["2B"] == ("2B", 7, "credito", None, None, None, "3000.00", "0.00"), filas["2B"]


# --- C04 · El libro no cambia ---------------------------------------------------------------------


def test_c04_el_borrador_no_toca_el_libro(mundo: Mundo) -> None:
    """Escenario: Borrador sin movimientos"""
    antes = libro_del_edificio(mundo)
    assert antes == (0, 0, 0), f"el edificio arranca sin libro: {antes}"
    subir(mundo)
    assert libro_del_edificio(mundo) == (0, 0, 0), (
        "el borrador creó cuentas, obligaciones o movimientos"
    )


# --- C05 a C07 · La comparación -------------------------------------------------------------------


def test_c05_comparacion_sin_diferencias(mundo: Mundo) -> None:
    """Escenario: Crédito a favor"""
    cuerpo = subir(mundo)
    c = comparacion(mundo)
    assert c["importacion_id"] == cuerpo["importacion_id"]
    assert por_unidad(c) == {
        "1A": ("169000.00", "169000.00", "0.00"),
        "1B": ("105000.00", "105000.00", "0.00"),
        "2A": ("52000.00", "52000.00", "0.00"),
        "2B": ("-3000.00", "-3000.00", "0.00"),
        "4D": ("-3000.00", "-3000.00", "0.00"),
    }, por_unidad(c)
    assert (c["total_borrador"], c["total_control"]) == ("320000.00", "320000.00")
    assert c["unidades_con_diferencia"] == 0
    assert c["requiere_aceptacion"] is False and c["aceptacion"] is None


def test_c06_dos_errores_de_signo_opuesto(mundo: Mundo) -> None:
    """Escenario: Dos errores de signo opuesto"""
    control = control_base()
    control[0][1] = "159000.00"  # 1A: el borrador tiene $10.000 más que su control
    control[2][1] = "62000.00"  # 2A: el borrador tiene $10.000 menos que su control
    subir(mundo, archivo(control=control))
    c = comparacion(mundo)
    assert (c["total_borrador"], c["total_control"]) == ("320000.00", "320000.00"), (
        "los totales coinciden"
    )
    unidades = por_unidad(c)
    assert unidades["1A"] == ("169000.00", "159000.00", "10000.00"), unidades["1A"]
    assert unidades["2A"] == ("52000.00", "62000.00", "-10000.00"), unidades["2A"]
    assert c["unidades_con_diferencia"] == 2
    assert c["requiere_aceptacion"] is True


def test_c07_unidad_con_control_sin_saldo_y_con_saldo_sin_control(mundo: Mundo) -> None:
    """Escenario: Unidad con control y sin saldo"""
    saldos = [*saldos_base(), ["5E", None, None, None, "1000.00", None]]
    control = [*control_base(), ["3C", "5000.00"]]
    subir(mundo, archivo(saldos, control))
    unidades = por_unidad(comparacion(mundo))
    assert unidades["3C"] == ("0.00", "5000.00", "-5000.00"), unidades.get("3C")
    assert unidades["5E"] == ("1000.00", "0.00", "1000.00"), unidades.get("5E")
    assert comparacion(mundo)["unidades_con_diferencia"] == 2


# --- C08 · El aviso de mes entero (E13, E18 del 4c) -----------------------------------------------


def test_c08_mes_entero_avisa_el_mes_de_la_migracion(mundo: Mundo) -> None:
    """Escenario: Mes entero"""
    configurar(mundo, MES_ENTERO)
    subir(mundo)
    a = avisos(comparacion(mundo))
    for unidad in ("1A", "1B", "2A"):
        assert a[unidad] == AVISO, f"{unidad} tiene deuda y debe avisar: {a[unidad]!r}"
    for unidad in ("2B", "4D"):
        assert a[unidad] is None, f"{unidad} sólo tiene crédito: no avisa ({a[unidad]!r})"


def test_c08_proporcional_no_avisa(mundo: Mundo) -> None:
    configurar(mundo, PROPORCIONAL)
    subir(mundo)
    a = avisos(comparacion(mundo))
    assert all(v is None for v in a.values()), f"con proporcional no hay aviso: {a}"


# --- C10 · Un borrador nuevo reemplaza al anterior ------------------------------------------------


def test_c10_un_borrador_nuevo_reemplaza_al_anterior(mundo: Mundo) -> None:
    """Escenario: Un borrador nuevo reemplaza al anterior"""
    primero = subir(mundo)
    control = control_base()
    control[1][1] = "100000.00"  # otro contenido: 1B con $5.000 de diferencia
    segundo = subir(mundo, archivo(control=control))
    assert segundo["importacion_id"] != primero["importacion_id"]
    assert estado_de(mundo, primero["importacion_id"]) == "descartada"
    assert estado_de(mundo, segundo["importacion_id"]) == "borrador"
    c = comparacion(mundo)
    assert c["importacion_id"] == segundo["importacion_id"], "la comparación muestra sólo el nuevo"
    assert por_unidad(c)["1B"] == ("105000.00", "100000.00", "5000.00")
    assert filas_del_borrador(mundo, segundo["importacion_id"]), "el nuevo tiene sus filas"


# --- C11 · Números con coma y con punto -----------------------------------------------------------


def test_c11_importes_con_coma_punto_y_celda_numerica(mundo: Mundo) -> None:
    saldos = [
        ["1A", "2026-09", date(2026, 9, 10), "Ordinaria", "85.000,00", None],
        ["1B", "2026-09", date(2026, 9, 10), "Ordinaria", "85000,00", None],
        ["2A", "2026-09", date(2026, 9, 10), "Ordinaria", "85000.00", None],
        ["2B", "2026-09", date(2026, 9, 10), "Ordinaria", 85000, None],
    ]
    control = [["1A", 85000], ["1B", "85.000,00"], ["2A", "85000,00"], ["2B", "85000.00"]]
    cuerpo = subir(mundo, archivo(saldos, control))
    importes = {f[0]: f[6] for f in filas_del_borrador(mundo, cuerpo["importacion_id"])}
    assert importes == {u: "85000.00" for u in ("1A", "1B", "2A", "2B")}, importes
    unidades = por_unidad(comparacion(mundo))
    for u in ("1A", "1B", "2A", "2B"):
        assert unidades[u] == ("85000.00", "85000.00", "0.00"), (u, unidades[u])
