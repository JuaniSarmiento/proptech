"""H-042 · condonar el interés pendiente con motivo (C01 a C04). Contrato en `aceptacion/H-042/CONTRATO.md`."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from ._h042 import (
    CLAVES_PARA_EL_EDIFICIO,
    CLAVES_PARA_EL_VECINO,
    CORTE,
    HOY,
    MONTO,
    OCT,
    SEP,
    Mundo,
    armar_la_deuda,
    auditorias,
    condonaciones_del_edificio,
    condonaciones_del_libro,
    condonaciones_del_vecino,
    condonar_ok,
    fila_de,
    intereses_pendientes,
    morosidad,
    obligacion_de,
    saldo_de,
    situacion,
    situaciones_del_edificio,
    superusuario,
)

# --- C01: un crédito `condonacion` imputado al interés; el recargo sigue en el libro ---------------------------------


def test_c01_condonar_el_interes_de_septiembre_crea_un_credito_y_el_recargo_sigue_en_el_libro(mundo: Mundo) -> None:
    """Escenario: la `1A` debe 510,00 de interés sobre septiembre; el super admin lo condona entero el 18/11"""
    armar_la_deuda(mundo)
    assert intereses_pendientes(mundo, "1A")[SEP] == Decimal("510.00"), "control: lo que el libro registró"
    saldo_antes = saldo_de(mundo, "1A")
    recargos = superusuario(mundo, "SELECT id, importe::text, fecha_valor FROM movimiento WHERE tipo = 'interes' "
                                   "AND administracion_id = %s ORDER BY id", (mundo.admin,))
    c = condonar_ok(mundo, "1A", SEP, "510.00")
    assert (c["unidad_id"], c["obligacion_id"], c["periodo"], c["importe"], c["motivo"], c["fecha_valor"]) == (
        str(mundo.unidades["1A"]), str(obligacion_de(mundo, "1A", SEP)), "2026-09-01", "510.00",
        "El vecino acreditó un error de facturación", "2026-11-18"), c
    assert MONTO.match(c["importe"]) and UUID(c["id"])
    (fila,) = condonaciones_del_libro(mundo)
    assert (str(fila[0]), fila[1], fila[2], fila[3], fila[4], fila[5], fila[6], fila[7]) == (
        c["id"], mundo.unidades["1A"], obligacion_de(mundo, "1A", SEP), "interes", "510.00", HOY,
        "El vecino acreditó un error de facturación", mundo.personas["super_admin"]), fila
    sentido = superusuario(mundo, "SELECT sentido FROM movimiento WHERE id = %s", (c["id"],))[0][0]
    assert sentido == "credito", "la condonación es un crédito"
    assert superusuario(mundo, "SELECT id, importe::text, fecha_valor FROM movimiento WHERE tipo = 'interes' "
                               "AND administracion_id = %s ORDER BY id", (mundo.admin,)) == recargos, (
        "el recargo original no se borra ni se cambia")
    assert intereses_pendientes(mundo, "1A")[SEP] == Decimal("0.00")
    assert intereses_pendientes(mundo, "1A")[OCT] == Decimal("210.00"), "el interés de octubre queda como estaba"
    assert saldo_de(mundo, "1A") == saldo_antes - Decimal("510.00"), "el saldo baja exactamente el importe"


def test_c01_una_condonacion_parcial_deja_el_resto_pendiente_y_la_segunda_completa_el_interes(mundo: Mundo) -> None:
    """Escenario: se condonan 200,00 de los 510,00 y después los 310,00 que quedaban"""
    armar_la_deuda(mundo)
    saldo = saldo_de(mundo, "1A")
    condonar_ok(mundo, "1A", SEP, "200.00")
    assert intereses_pendientes(mundo, "1A")[SEP] == Decimal("310.00")
    assert saldo_de(mundo, "1A") == saldo - Decimal("200.00")
    condonar_ok(mundo, "1A", SEP, "310.00", "Segunda parte del acuerdo con el vecino")
    assert intereses_pendientes(mundo, "1A")[SEP] == Decimal("0.00")
    assert saldo_de(mundo, "1A") == saldo - Decimal("510.00")
    assert [(x[4], x[6]) for x in condonaciones_del_libro(mundo)] == [
        ("200.00", "El vecino acreditó un error de facturación"), ("310.00", "Segunda parte del acuerdo con el vecino")]


def test_c01_la_condonacion_se_imputa_sólo_al_componente_interes_de_la_obligacion_elegida(mundo: Mundo) -> None:
    """Escenario: se condona el interés de octubre; ni el capital ni septiembre se tocan"""
    armar_la_deuda(mundo)
    c = condonar_ok(mundo, "1A", OCT, "210.00")
    imputaciones = superusuario(mundo, "SELECT obligacion_id, componente, importe::text FROM imputacion "
                                       "WHERE movimiento_id = %s", (c["id"],))
    assert [(str(i[0]), i[1], i[2]) for i in imputaciones] == [
        (str(obligacion_de(mundo, "1A", OCT)), "interes", "210.00")], imputaciones
    assert intereses_pendientes(mundo, "1A")[SEP] == Decimal("510.00")
    otras = {u: saldo_de(mundo, u) for u in ("1B", "2A", "2B")}
    assert otras == {"1B": Decimal("40000.00"), "2A": Decimal("15360.00"), "2B": Decimal("24576.00")}, otras


# --- C02: el motivo se ve en la lectura del vecino y en la del consejo ------------------------------------------------


def test_c02_el_vecino_ve_el_motivo_de_las_condonaciones_de_su_unidad_de_la_mas_nueva_a_la_mas_vieja(
        mundo: Mundo) -> None:
    """Escenario: dos condonaciones a la `1A` y una a la `2B`; Ana (dueña de las dos) las lee por unidad"""
    armar_la_deuda(mundo)
    condonar_ok(mundo, "1A", SEP, "200.00", "Primer motivo de la 1A")
    condonar_ok(mundo, "1A", OCT, "50.00", "Segundo motivo de la 1A")
    condonar_ok(mundo, "2B", SEP, "100.00", "Motivo de la 2B")
    mundo.como("ana")
    r = condonaciones_del_vecino(mundo, "1A")
    assert r.status_code == 200, f"se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    lista = r.json()
    assert [set(x) for x in lista] == [CLAVES_PARA_EL_VECINO, CLAVES_PARA_EL_VECINO], lista
    assert [(x["periodo"], x["importe"], x["motivo"], x["fecha_valor"]) for x in lista] == [
        ("2026-10-01", "50.00", "Segundo motivo de la 1A", "2026-11-18"),
        ("2026-09-01", "200.00", "Primer motivo de la 1A", "2026-11-18")]
    otra = condonaciones_del_vecino(mundo, "2B").json()
    assert [(x["importe"], x["motivo"]) for x in otra] == [("100.00", "Motivo de la 2B")]


def test_c02_una_unidad_sin_condonaciones_da_lista_vacia_y_una_ajena_da_404(mundo: Mundo) -> None:
    """Escenario: Ana lee la `2B` (suya, sin condonaciones) y la `1B` (de otro) con la `1A` condonada"""
    armar_la_deuda(mundo)
    condonar_ok(mundo, "1A", SEP, "200.00")
    mundo.como("ana")
    r = condonaciones_del_vecino(mundo, "2B")
    assert r.status_code == 200 and r.json() == [], f"la 2B no tiene condonaciones: {r.status_code} {r.text[:200]}"
    ajena = condonaciones_del_vecino(mundo, "1B")
    assert ajena.status_code == 404 and ajena.json() == {"detail": "no encontrado"}, (ajena.status_code, ajena.text)
    mundo.como("super_admin")
    personal = condonaciones_del_vecino(mundo, "1A")
    assert personal.status_code == 404, "ser personal no da unidades: la lectura del vecino es de sus unidades"


def test_c02_el_consejo_ve_las_condonaciones_del_edificio_con_su_motivo(mundo: Mundo) -> None:
    """Escenario: se condonan 300,00 a la `1A` y 100,00 a la `2B`; el consejo lee las del edificio"""
    armar_la_deuda(mundo)
    primera = condonar_ok(mundo, "1A", SEP, "300.00", "Acuerdo de pago de la 1A")
    segunda = condonar_ok(mundo, "2B", SEP, "100.00", "Error en el cálculo de la 2B")
    mundo.como("consejo")
    r = condonaciones_del_edificio(mundo)
    assert r.status_code == 200, f"se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    lista = r.json()
    assert [set(x) for x in lista] == [CLAVES_PARA_EL_EDIFICIO, CLAVES_PARA_EL_EDIFICIO], lista
    assert [(x["id"], x["unidad"], x["importe"], x["motivo"], x["periodo"], x["fecha_valor"]) for x in lista] == [
        (segunda["id"], "2B", "100.00", "Error en el cálculo de la 2B", "2026-09-01", "2026-11-18"),
        (primera["id"], "1A", "300.00", "Acuerdo de pago de la 1A", "2026-09-01", "2026-11-18")]
    assert lista[1]["unidad_id"] == str(mundo.unidades["1A"])
    assert lista[1]["obligacion_id"] == str(obligacion_de(mundo, "1A", SEP))


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal", "admin_del_edificio", "contador", "consejo"])
def test_c02_los_perfiles_con_alcance_leen_las_condonaciones_del_edificio(mundo: Mundo, rol: str) -> None:
    """Escenario: {rol} pide las condonaciones del edificio"""
    armar_la_deuda(mundo)
    condonar_ok(mundo, "1A", SEP, "200.00")
    mundo.como(rol)
    r = condonaciones_del_edificio(mundo)
    assert r.status_code == 200, f"{rol}: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    assert [x["importe"] for x in r.json()] == ["200.00"]


# --- C03: R20 después de condonar -----------------------------------------------------------------------------------


def test_c03_condonar_todo_el_interes_saca_a_la_unidad_de_deuda_de_intereses(mundo: Mundo) -> None:
    """Escenario: la `1B` pagó tarde y al 05/11 sólo debe 600,00 de interés de octubre"""
    armar_la_deuda(mundo, b_tarde=True)
    antes = situacion(mundo, "1B", CORTE)
    assert (antes.etiqueta, str(antes.total_vencido), str(antes.interes_vencido)) == (
        "deuda_de_intereses", "600.00", "600.00"), "control: deuda de intereses (D-109.4)"
    condonar_ok(mundo, "1B", OCT, "600.00")
    despues = situacion(mundo, "1B", CORTE)
    assert (despues.etiqueta, str(despues.total_vencido), despues.moroso_critico) == (
        "sin_deuda_vencida", "0.00", False), despues
    assert situaciones_del_edificio(mundo, CORTE)["1B"].etiqueta == "sin_deuda_vencida"


def test_c03_una_condonacion_parcial_baja_el_total_vencido_y_puede_dejar_a_la_unidad_bajo_el_umbral(
        mundo: Mundo) -> None:
    """Escenario: de los 600,00 de la `1B` se condonan 50,00 (550,00) y después 150,00 más (400,00 < 500,00)"""
    armar_la_deuda(mundo, b_tarde=True)
    condonar_ok(mundo, "1B", OCT, "50.00")
    uno = situacion(mundo, "1B", CORTE)
    assert (uno.etiqueta, str(uno.total_vencido), str(uno.interes_vencido)) == (
        "deuda_de_intereses", "550.00", "550.00"), uno
    condonar_ok(mundo, "1B", OCT, "150.00")
    dos = situacion(mundo, "1B", CORTE)
    assert (dos.etiqueta, str(dos.total_vencido)) == ("bajo_umbral", "400.00"), "R30: bajo el umbral no cuenta"


def test_c03_condonar_el_interes_no_cambia_que_siga_siendo_moroso_critico_por_el_capital(mundo: Mundo) -> None:
    """Escenario: se condonan los 720,00 de interés de la `1A`, que sigue con 3 liquidaciones vencidas el 18/11"""
    armar_la_deuda(mundo)
    condonar_ok(mundo, "1A", SEP, "510.00")
    condonar_ok(mundo, "1A", OCT, "210.00")
    s = situacion(mundo, "1A", CORTE)
    assert (s.etiqueta, str(s.total_vencido), str(s.capital_vencido), str(s.interes_vencido),
            s.liquidaciones_vencidas) == ("moroso_critico", "20000.00", "20000.00", "0.00", 2), s
    assert situaciones_del_edificio(mundo, CORTE)["1A"].etiqueta == "moroso_critico"
    cuerpo = morosidad(mundo)
    fila = fila_de(cuerpo, "1A")
    assert (fila["etiqueta"], fila["total_vencido"], fila["capital"], fila["intereses"],
            fila["liquidaciones_vencidas"]) == ("moroso_critico", "30000.00", "30000.00", "0.00", 3), fila
    suma = sum((Decimal(f["total_vencido"]) for f in cuerpo["unidades"]), Decimal("0.00"))
    assert cuerpo["resumen"]["total_vencido"] == f"{suma:.2f}", "el resumen suma lo que quedó"


# --- C04: quién condona y la auditoría --------------------------------------------------------------------------------


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal"])
def test_c04_el_super_admin_y_el_administrador_principal_condonan(mundo: Mundo, rol: str) -> None:
    """Escenario: {rol} condona 100,00 del interés de septiembre de la `1A`"""
    armar_la_deuda(mundo)
    mundo.como(rol)
    condonar_ok(mundo, "1A", SEP, "100.00")
    (fila,) = condonaciones_del_libro(mundo)
    assert fila[7] == mundo.personas[rol], "queda a nombre de quien condonó"


def test_c04_cada_condonacion_queda_auditada_con_quien_la_unidad_la_obligacion_el_importe_y_el_motivo(
        mundo: Mundo) -> None:
    """Escenario: el super admin condona 200,00 a la `1A` y la principal 100,00 a la `2B`"""
    armar_la_deuda(mundo)
    uno = condonar_ok(mundo, "1A", SEP, "200.00", "Motivo uno")
    mundo.como("admin_principal")
    dos = condonar_ok(mundo, "2B", OCT, "100.00", "Motivo dos")
    filas = auditorias(mundo, "condonar_intereses")
    assert len(filas) == 2, filas
    assert [(f[0], str(f[1]), f[2]) for f in filas] == [
        ("movimiento", uno["id"], mundo.personas["super_admin"]),
        ("movimiento", dos["id"], mundo.personas["admin_principal"])], filas
    assert filas[0][3] == {"unidad_id": str(mundo.unidades["1A"]), "obligacion_id": str(obligacion_de(mundo, "1A", SEP)),
                           "importe": "200.00", "motivo": "Motivo uno"}, filas[0][3]
    assert filas[1][3] == {"unidad_id": str(mundo.unidades["2B"]), "obligacion_id": str(obligacion_de(mundo, "2B", OCT)),
                           "importe": "100.00", "motivo": "Motivo dos"}, filas[1][3]


def test_c04_leer_las_condonaciones_no_se_audita(mundo: Mundo) -> None:
    """Escenario: Ana, el consejo y el super admin leen; no queda ninguna fila más"""
    armar_la_deuda(mundo)
    condonar_ok(mundo, "1A", SEP, "200.00")
    assert len(auditorias(mundo, "condonar_intereses")) == 1
    for rol in ("ana", "consejo", "super_admin"):
        mundo.como(rol)
        assert condonaciones_del_edificio(mundo).status_code in (200, 403)
        assert condonaciones_del_vecino(mundo, "1A").status_code in (200, 404)
    assert len(auditorias(mundo, "condonar_intereses")) == 1
