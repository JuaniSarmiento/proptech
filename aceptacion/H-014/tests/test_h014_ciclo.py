"""H-014 · distribuir, anular y el cargo cobrado de menos (C01 a C08, N01 a N07)."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from ._h014 import (
    DIC,
    MOTIVO_ANULACION,
    NOV,
    OCT,
    Mundo,
    anular,
    auditorias,
    cargar_base,
    cargo_api,
    cargo_con_reloj,
    conflicto,
    credito_de_correccion,
    del_libro,
    distribuir,
    emitir_libro,
    emitir_lo_revisado,
    en_paralelo,
    estado_de,
    gasto,
    leer_liquidacion,
    obligacion_del_periodo,
    obligaciones_del_libro,
    ok,
    pagar,
    preliquidacion,
    puerto_de_distribucion,
    ruta_liquidacion,
    saldos,
    sesion_app,
    unidad,
)


# --- Distribuir -----------------------------------------------------------------------------------


def test_c01_distribuir_una_emitida(mundo: Mundo) -> None:
    """Escenario: Distribuir"""
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    antes = auditorias(mundo, "emitir_y_distribuir_liquidacion")
    ok(distribuir(mundo, liquidacion), "distribuida")
    leida = leer_liquidacion(mundo, liquidacion)
    assert leida["estado"] == "distribuida"
    assert leida["distribucion"]["origen"] == "manual" and leida["distribucion"]["en"], leida["distribucion"]
    assert auditorias(mundo, "emitir_y_distribuir_liquidacion") == antes + 1


def test_c02_el_puerto_es_idempotente(mundo: Mundo) -> None:
    """Escenario: Distribuida por dos caminos"""
    cargar_base(mundo)
    cuerpo = emitir_lo_revisado(mundo)
    registrar = puerto_de_distribucion()
    from uuid import UUID

    resultados = []
    for origen in ("portal", "email"):
        with sesion_app(mundo.base, mundo.admin) as s:
            resultados.append(registrar(s, emision_id=UUID(cuerpo["emision_id"]), origen=origen,
                                        persona_id=None, request_id=uuid4()))
            s.commit()
    assert resultados == [True, False], f"el primero registra y el segundo no: {resultados}"
    leida = leer_liquidacion(mundo, cuerpo["liquidacion_id"])
    assert leida["estado"] == "distribuida" and leida["distribucion"]["origen"] == "portal"
    eventos = mundo.uno(
        "SELECT count(*) FROM evento_de_emision WHERE emision_id = %s AND tipo = 'distribuida'",
        (cuerpo["emision_id"],),
    )
    assert eventos == 1


# --- Anular ---------------------------------------------------------------------------------------


def test_c03_anular_deja_la_deuda_como_antes(mundo: Mundo) -> None:
    """Escenario: Anular una emitida"""
    cargar_base(mundo)
    emitir_libro(mundo, OCT, {"1A": ("100000.00", "0.00", "0.00")})
    antes_de_emitir = saldos(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    libro = del_libro(mundo)
    mundo.como("admin_principal")
    ok(anular(mundo, liquidacion), "anulada")
    assert del_libro(mundo) == libro, "anular modificó o borró filas del libro"
    assert saldos(mundo) == antes_de_emitir, "la deuda no quedó como antes de emitir"
    leida = leer_liquidacion(mundo, liquidacion)
    assert leida["estado"] == "anulada"
    assert leida["anulacion"]["motivo"] == MOTIVO_ANULACION
    assert leida["anulacion"]["por"] == str(mundo.personas["admin_principal"])
    assert auditorias(mundo, "anular_liquidacion") == 1


def test_c04_anular_y_volver_a_emitir_no_cobra_dos_veces(mundo: Mundo) -> None:
    """Escenario: Volver a emitir"""
    cargar_base(mundo)
    emitir_libro(mundo, OCT, {"1A": ("100000.00", "0.00", "0.00")})
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    ok(anular(mundo, liquidacion), "anulada")
    emitir_lo_revisado(mundo)
    assert estado_de(mundo, "1A").deuda.a_texto() == "143350.00", (
        "octubre más la expensa de noviembre una sola vez (el interés anulado pasa al corte siguiente)"
    )
    assert len(obligaciones_del_libro(mundo)) == 8, "las 4 anuladas quedan en el libro sin contar"


def test_c05_el_pago_vuelve_con_su_fecha(mundo: Mundo) -> None:
    """Escenario: Pago imputado a una emisión anulada"""
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    pagar(mundo, "1A", "43350.00", date(2026, 11, 5))
    ok(anular(mundo, liquidacion), "anulada")
    e = estado_de(mundo, "1A")
    assert e.credito_a_favor_aplicable.a_texto() == "43350.00", "el pago vuelve como crédito a favor"
    emitir_lo_revisado(mundo)
    e = estado_de(mundo, "1A")
    assert (e.deuda.a_texto(), e.credito_a_favor.a_texto()) == ("0.00", "0.00"), "la re-emisión lo imputa"
    assert unidad(preliquidacion(mundo, DIC), "1A")["intereses"] == "0.00", (
        "pagó el 05/11, antes del vencimiento: no hay interés (P38, fecha de la transferencia)"
    )


def test_c06_d8_el_credito_de_correccion_queda_retenido(mundo: Mundo) -> None:
    """Escenario: Crédito de corrección de una emisión anulada"""
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    credito_de_correccion(mundo, "1A", NOV, "1000.00")
    assert estado_de(mundo, "1A").deuda.a_texto() == "42350.00", "control: la corrección se imputó"
    ok(anular(mundo, liquidacion), "anulada")
    e = estado_de(mundo, "1A")
    assert e.credito_a_favor_retenido.a_texto() == "1000.00", "D8: retenido"
    assert e.credito_a_favor_aplicable.a_texto() == "0.00", "D8: nunca a favor aplicable"
    emitir_lo_revisado(mundo)
    e = estado_de(mundo, "1A")
    assert e.deuda.a_texto() == "43350.00", "la re-emisión no imputa el crédito retenido"
    assert e.credito_a_favor_retenido.a_texto() == "1000.00"


# --- Cargo cobrado de menos -----------------------------------------------------------------------


def test_c07_cargo_cobrado_de_menos(mundo: Mundo) -> None:
    """Escenario: Cargo cobrado de menos"""
    cargar_base(mundo)
    emitir_lo_revisado(mundo)
    origen = obligacion_del_periodo(mundo, "1A", NOV)
    pagar(mundo, "1A", "43350.00", date(2026, 11, 5))
    antes = auditorias(mundo, "corregir_movimiento")
    r = cargo_con_reloj(mundo, "1A", origen, "1500.00", date(2026, 11, 20))
    assert r is not None
    nueva = mundo.filas(
        "SELECT o.ordinaria::text, o.vencimiento, o.emision_id FROM obligacion o JOIN cuenta c ON "
        "c.id = o.cuenta_id WHERE c.unidad_id = %s AND o.id <> %s AND o.periodo = %s",
        (mundo.unidades["1A"], origen, NOV),
    )
    assert [(f[0], f[1], f[2]) for f in nueva] == [("1500.00", date(2026, 11, 20), None)], nueva
    assert auditorias(mundo, "corregir_movimiento") == antes + 1
    assert unidad(preliquidacion(mundo, DIC), "1A")["intereses"] == "15.00", (
        "10 días (21/11 a 30/11) al 0,1% diario de $1.500"
    )


def test_c07_cargo_por_la_api(mundo: Mundo) -> None:
    cargar_base(mundo)
    emitir_lo_revisado(mundo)
    origen = obligacion_del_periodo(mundo, "1A", NOV)
    mundo.como("admin_principal")
    r = cargo_api(mundo, "1A", origen)
    assert r.status_code == 201, f"{r.status_code} {r.text[:300]}"
    cuerpo = r.json()
    for clave in ("cargo_id", "obligacion_id", "obligacion_origen_id", "importe", "componente",
                  "vencimiento", "motivo", "registrado_por", "registrado_en"):
        assert clave in cuerpo, f"el cargo no trae `{clave}`: {cuerpo}"
    assert (cuerpo["obligacion_origen_id"], cuerpo["importe"]) == (str(origen), "1500.00")


# --- Permisos y lectura por rol -------------------------------------------------------------------


def test_c08_permisos_de_anular_y_distribuir(mundo: Mundo) -> None:
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    mundo.como("admin_del_edificio")
    r = anular(mundo, liquidacion)
    assert r.status_code == 403 and r.json()["detail"].get("permiso_faltante") == "anular_liquidacion", r.text
    ok(distribuir(mundo, liquidacion), "distribuida")


def test_c08_el_consejo_no_ve_lo_no_distribuido(mundo: Mundo) -> None:
    """Escenario: El consejo y una liquidación sin distribuir"""
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    lista = f"/api/complejos/{mundo.edificio}/liquidaciones"
    for rol, ve in (("consejo", False), ("contador", True), ("admin_del_edificio", True)):
        mundo.como(rol)
        r = mundo.cliente.get(lista)
        assert r.status_code == 200, f"{rol}: {r.status_code} {r.text[:200]}"
        ids = [x["liquidacion_id"] for x in r.json()]
        assert (liquidacion in ids) is ve, f"{rol} ve {ids}"
        assert (mundo.cliente.get(ruta_liquidacion(mundo, liquidacion)).status_code == 200) is ve
    mundo.como("super_admin")
    ok(distribuir(mundo, liquidacion), "distribuida")
    mundo.como("consejo")
    assert liquidacion in [x["liquidacion_id"] for x in mundo.cliente.get(lista).json()]
    assert mundo.cliente.get(ruta_liquidacion(mundo, liquidacion)).status_code == 200


# --- Lo que tiene que fallar ----------------------------------------------------------------------


def test_n01_anular_una_distribuida(mundo: Mundo) -> None:
    """Escenario: Anular una distribuida"""
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    ok(distribuir(mundo, liquidacion), "distribuida")
    libro = del_libro(mundo)
    conflicto(anular(mundo, liquidacion), "estado", "ya_distribuida")
    assert del_libro(mundo) == libro
    assert leer_liquidacion(mundo, liquidacion)["estado"] == "distribuida"


@pytest.mark.parametrize("motivo", [None, "", "   "], ids=["sin_motivo", "vacio", "en_blanco"])
def test_n02_anular_sin_motivo(mundo: Mundo, motivo: object) -> None:
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    r = anular(mundo, liquidacion, motivo)
    assert r.status_code == 422, f"{motivo!r}: {r.status_code} {r.text[:200]}"
    assert leer_liquidacion(mundo, liquidacion)["estado"] == "emitida"


def test_n03_anular_dos_veces(mundo: Mundo) -> None:
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    ok(anular(mundo, liquidacion), "anulada")
    conflicto(anular(mundo, liquidacion), "estado", "anulada")


def test_n04_no_se_anula_con_el_siguiente_emitido(mundo: Mundo) -> None:
    """Escenario: Anular con el siguiente emitido"""
    cargar_base(mundo)
    octubre = emitir_lo_revisado(mundo, OCT)["liquidacion_id"]
    noviembre = emitir_lo_revisado(mundo)["liquidacion_id"]
    conflicto(anular(mundo, octubre), "periodo", "periodo_siguiente_emitido")
    ok(anular(mundo, noviembre), "anulada")
    ok(anular(mundo, octubre), "anulada")


def test_n05_distribuir_una_anulada_o_dos_veces(mundo: Mundo) -> None:
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    ok(distribuir(mundo, liquidacion), "distribuida")
    conflicto(distribuir(mundo, liquidacion), "estado", "ya_distribuida")
    gasto(mundo, "1000.00", periodo=DIC)
    otra = emitir_lo_revisado(mundo, DIC)["liquidacion_id"]
    ok(anular(mundo, otra), "anulada")
    conflicto(distribuir(mundo, otra), "estado", "anulada")


def test_n06_anular_y_distribuir_a_la_vez(mundo: Mundo) -> None:
    """Escenario: Anular y distribuir a la vez"""
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    r1, r2 = en_paralelo(lambda: anular(mundo, liquidacion), lambda: distribuir(mundo, liquidacion))
    codigos = sorted(getattr(r, "status_code", repr(r)) for r in (r1, r2))
    assert codigos == [200, 409], f"una gana y la otra choca: {codigos}"
    tipos = [f[0] for f in mundo.filas(
        "SELECT e.tipo FROM evento_de_emision e JOIN emision em ON em.id = e.emision_id "
        "WHERE em.complejo_id = %s AND em.periodo = %s", (mundo.edificio, NOV))]
    assert len(tipos) == 1, f"nunca las dos: {tipos}"


@pytest.mark.parametrize(
    ("cambios", "codigo"),
    [({"importe": "0.00"}, 422), ({"importe": "-10.00"}, 422), ({"motivo": "  "}, 422),
     ({"componente": "intereses"}, 422)],
    ids=["importe_cero", "importe_negativo", "sin_motivo", "componente_invalido"],
)
def test_n07_cargo_invalido(mundo: Mundo, cambios: dict[str, str], codigo: int) -> None:
    cargar_base(mundo)
    emitir_lo_revisado(mundo)
    origen = obligacion_del_periodo(mundo, "1A", NOV)
    libro = del_libro(mundo)
    r = cargo_api(mundo, "1A", origen, **cambios)
    assert r.status_code == codigo, f"{cambios}: {r.status_code} {r.text[:200]}"
    assert del_libro(mundo) == libro


def test_n07_cargo_con_origen_ajeno(mundo: Mundo) -> None:
    cargar_base(mundo)
    emitir_lo_revisado(mundo)
    de_1b = obligacion_del_periodo(mundo, "1B", NOV)
    libro = del_libro(mundo)
    r = cargo_api(mundo, "1A", de_1b)
    assert r.status_code == 404 and r.json() == {"detail": "no encontrado"}, f"origen de otra unidad: {r.text[:200]}"
    r = cargo_api(mundo, "1A", uuid4())
    assert r.status_code == 404 and r.json() == {"detail": "no encontrado"}, f"origen inexistente: {r.text[:200]}"
    assert del_libro(mundo) == libro
