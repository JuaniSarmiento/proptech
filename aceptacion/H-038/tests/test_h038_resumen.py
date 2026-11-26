"""H-038 · lo que debo (C01 a C03). Contrato en `aceptacion/H-038/CONTRATO.md`."""

from __future__ import annotations

from decimal import Decimal

from ._h038 import (
    HOY,
    OCT,
    UNIDADES,
    Mundo,
    anular_libro,
    base_con_mora,
    base_noviembre,
    bonificar,
    cargar_base,
    del_libro,
    deuda_anterior,
    emitir_libro,
    emitir_lo_revisado,
    id_de,
    mis_unidades,
    morosidad_del_administrador,
    pagar,
    por_unidad,
)

CAMPOS_DE_PLATA = ("total_a_pagar", "intereses", "credito_aplicable", "credito_retenido")


def _suma(unidades: list[dict[str, str]], campo: str) -> str:
    return f"{sum((Decimal(u[campo]) for u in unidades), Decimal('0.00')):.2f}"


# --- C01: todas mis unidades ---------------------------------------------------------------------------


def test_c01_trae_todas_las_unidades_de_la_persona_con_su_vinculo_y_su_edificio(mundo: Mundo) -> None:
    """Escenario: Ana tiene unidades en dos edificios"""
    base_noviembre(mundo)
    mundo.como("ana")
    cuerpo = mis_unidades(mundo)
    assert cuerpo["fecha"] == HOY.isoformat(), cuerpo["fecha"]
    filas = por_unidad(mundo)
    assert set(filas) == {"1A", "2B", "9A"}, sorted(filas)
    for identificador, edificio, complejo in (("1A", "Torre Ficticia", mundo.edificio),
                                              ("2B", "Torre Ficticia", mundo.edificio),
                                              ("9A", "Otro Edificio Ficticio", mundo.otro)):
        fila = filas[identificador]
        assert fila["vinculo"] == "propietario", fila
        assert fila["edificio"] == edificio and fila["complejo_id"] == str(complejo), fila
        assert fila["unidad_id"] == str(id_de(mundo, identificador)), fila
    mundo.como("beto")
    beto = por_unidad(mundo)
    assert set(beto) == {"1B"} and beto["1B"]["vinculo"] == "inquilino", beto
    mundo.como("carla")
    carla = por_unidad(mundo)
    assert set(carla) == {"1B"} and carla["1B"]["vinculo"] == "propietario", carla


def test_c01_quien_no_es_vecino_no_tiene_unidades(mundo: Mundo) -> None:
    """Escenario: El personal no tiene unidades por ser personal"""
    base_noviembre(mundo)
    mundo.como("ana")
    assert mis_unidades(mundo)["unidades"], "control: Ana sí tiene unidades"
    for rol in ("super_admin", "admin_principal", "contador", "consejo", "administracion_b"):
        mundo.como(rol)
        cuerpo = mis_unidades(mundo)
        assert cuerpo["unidades"] == [], f"{rol} no tiene vínculo con ninguna unidad: {cuerpo['unidades']}"
        assert cuerpo["conjunto"] == {c: "0.00" for c in CAMPOS_DE_PLATA}, cuerpo["conjunto"]


def test_c01_sin_nada_emitido_todo_es_cero_y_no_hay_vencimiento(mundo: Mundo) -> None:
    """Escenario: Todavía no se emitió nada"""
    mundo.como("ana")
    filas = por_unidad(mundo)
    assert set(filas) == {"1A", "2B", "9A"}, sorted(filas)
    for identificador, fila in filas.items():
        assert fila["vencimiento"] is None, f"{identificador}: sin deuda no hay vencimiento: {fila}"
        for campo in (*CAMPOS_DE_PLATA, "deuda_anterior"):
            assert fila[campo] == "0.00", f"{identificador}: {campo} debería ser 0.00: {fila}"


# --- C02: los números de la deuda ----------------------------------------------------------------------


def test_c02_noviembre_emitido_sin_mora(mundo: Mundo) -> None:
    """Escenario: Noviembre sin mora (la expensa de H-011)"""
    base_noviembre(mundo)
    mundo.como("ana")
    filas = por_unidad(mundo)
    assert (filas["1A"]["total_a_pagar"], filas["2B"]["total_a_pagar"], filas["9A"]["total_a_pagar"]) == (
        "43350.00", "37425.00", "0.00")
    for u in ("1A", "2B"):
        assert filas[u]["vencimiento"] == "2026-11-10", filas[u]
        assert filas[u]["deuda_anterior"] == "0.00", filas[u]
        assert filas[u]["intereses"] == "0.00", filas[u]
        assert (filas[u]["credito_aplicable"], filas[u]["credito_retenido"]) == ("0.00", "0.00"), filas[u]
    assert mis_unidades(mundo)["conjunto"] == {
        "total_a_pagar": "80775.00", "intereses": "0.00", "credito_aplicable": "0.00", "credito_retenido": "0.00"}
    mundo.como("carla")
    assert por_unidad(mundo)["1B"]["total_a_pagar"] == "48350.00"
    mundo.como("dora")
    assert por_unidad(mundo)["2A"]["total_a_pagar"] == "62375.00"


def test_c02_con_mora_son_los_del_libro_y_el_conjunto_los_suma(mundo: Mundo) -> None:
    """Escenario: Octubre impago en `1A` y `2A`, noviembre emitido"""
    emitida = base_con_mora(mundo)
    mundo.como("ana")
    cuerpo = mis_unidades(mundo)
    filas = {u["identificador"]: u for u in cuerpo["unidades"]}
    for u in ("1A", "2B"):
        esperado = del_libro(mundo, u)
        for campo, valor in esperado.items():
            assert filas[u][campo] == valor, f"{u}: {campo} del portal {filas[u][campo]!r}, del libro {valor!r}"
        assert filas[u]["deuda_anterior"] == deuda_anterior(mundo, str(emitida["emision_id"]), u), filas[u]
    # Los números concretos: octubre impago de `1A` son 10.000,00 más 210,00 de interés (21 días al 3% mensual).
    assert filas["1A"]["intereses"] == "210.00" and filas["2B"]["intereses"] == "0.00", filas
    assert filas["1A"]["deuda_anterior"] == "10210.00" and filas["2B"]["deuda_anterior"] == "0.00", filas
    assert filas["1A"]["total_a_pagar"] == "53560.00", f"43.350,00 de noviembre más 10.210,00 anteriores: {filas['1A']}"
    assert filas["1A"]["vencimiento"] == "2026-10-10" and filas["2B"]["vencimiento"] == "2026-11-10", filas
    assert filas["2B"]["total_a_pagar"] == "37425.00", filas["2B"]
    unidades = list(cuerpo["unidades"])
    assert cuerpo["conjunto"] == {c: _suma(unidades, c) for c in CAMPOS_DE_PLATA}, cuerpo["conjunto"]
    assert cuerpo["conjunto"]["total_a_pagar"] == _suma([filas["1A"], filas["2B"], filas["9A"]], "total_a_pagar")


def test_c02_iguales_a_lo_que_ve_el_administrador(mundo: Mundo) -> None:
    """Escenario: El vecino y el administrador miran la misma deuda"""
    base_con_mora(mundo)
    admin = morosidad_del_administrador(mundo)
    for quien, unidad in (("ana", "1A"), ("ana", "2B"), ("carla", "1B"), ("dora", "2A")):
        mundo.como(quien)
        fila = por_unidad(mundo)[unidad]
        visto = admin[unidad]
        assert fila["total_a_pagar"] == visto["total_vencido"], f"{unidad}: {fila} contra {visto}"
        assert fila["intereses"] == visto["intereses"], f"{unidad}: {fila} contra {visto}"
        assert fila["vencimiento"] == visto["vencida_desde"], f"{unidad}: {fila} contra {visto}"


# --- C03: el crédito ------------------------------------------------------------------------------------


def test_c03_el_credito_retenido_no_descuenta_la_deuda(mundo: Mundo) -> None:
    """Escenario: Una bonificación de octubre anulada queda retenida"""
    mundo.como("super_admin")
    cargar_base(mundo)
    octubre = emitir_libro(mundo, OCT, {u: ("10000.00", "0.00", "0.00") for u in UNIDADES})
    bonificar(mundo, "1A", OCT, "2000.00")
    anular_libro(mundo, octubre.emision_id)
    emitir_lo_revisado(mundo)
    libro = del_libro(mundo, "1A")
    assert (libro["total_a_pagar"], libro["credito_aplicable"], libro["credito_retenido"]) == (
        "43350.00", "0.00", "2000.00"), f"control: el libro no quedó como el ejemplo: {libro}"
    mundo.como("ana")
    cuerpo = mis_unidades(mundo)
    fila = {u["identificador"]: u for u in cuerpo["unidades"]}["1A"]
    assert fila["total_a_pagar"] == "43350.00", f"el retenido no descuenta: {fila}"
    assert (fila["credito_aplicable"], fila["credito_retenido"]) == ("0.00", "2000.00"), fila
    assert cuerpo["conjunto"]["credito_retenido"] == "2000.00", cuerpo["conjunto"]
    assert cuerpo["conjunto"]["total_a_pagar"] == "80775.00", cuerpo["conjunto"]


def test_c03_el_credito_aplicable_se_ve_aparte_de_la_deuda(mundo: Mundo) -> None:
    """Escenario: Ana pagó de más la `2B`"""
    base_noviembre(mundo)
    pagar(mundo, "2B", "50000.00", HOY.replace(day=5))
    assert del_libro(mundo, "2B")["credito_aplicable"] == "12575.00", "control: el libro tiene el crédito libre"
    mundo.como("ana")
    fila = por_unidad(mundo)["2B"]
    assert (fila["total_a_pagar"], fila["credito_aplicable"], fila["credito_retenido"]) == (
        "0.00", "12575.00", "0.00"), fila
    assert fila["vencimiento"] is None, fila
