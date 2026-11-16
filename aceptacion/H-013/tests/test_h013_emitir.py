"""H-013 · emitir lo revisado (C01 a C10)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ._h013 import (
    DIC,
    MOTIVO_VENCIMIENTO,
    NOV,
    OCT,
    SEP,
    Mundo,
    auditorias,
    cargar_base,
    configurar,
    credito_de_correccion,
    cuerpo_de_emision,
    emitida,
    emitir,
    emitir_libro,
    emitir_lo_revisado,
    gasto,
    leer_liquidacion,
    obligacion_de,
    obligaciones_del_libro,
    plata,
    preliquidacion,
    saldo_anterior_del_libro,
    total_de_cargos,
    unidad,
)

ESPERADAS = {
    "1A": ("27000.00", "1350.00", "15000.00"),
    "1B": ("32000.00", "1350.00", "15000.00"),
    "2A": ("47500.00", "2375.00", "12500.00"),
    "2B": ("28500.00", "1425.00", "7500.00"),
}


def test_c01_emitir_la_base(mundo: Mundo) -> None:
    """Escenario: Emitir la base"""
    cargar_base(mundo)
    cuerpo = emitir_lo_revisado(mundo)
    assert cuerpo["periodo"] == "2026-11-01" and cuerpo["vencimiento"] == "2026-11-10"
    for u, (o, f, e) in ESPERADAS.items():
        ob = obligacion_de(cuerpo, u)
        assert ob is not None, f"{u} no tiene obligación en la respuesta"
        assert (ob["ordinaria"], ob["fondo_de_reserva"], ob["extraordinaria"], ob["vencimiento"]) == (
            o, f, e, "2026-11-10"
        ), f"{u}: {ob}"
    libro = obligaciones_del_libro(mundo)
    assert {u: v[:3] for u, v in libro.items()} == ESPERADAS, f"obligaciones del libro: {libro}"
    assert {v[3] for v in libro.values()} == {NOV.replace(day=10)}
    assert auditorias(mundo, "emitir_y_distribuir_liquidacion") == 1


def test_c02_lo_emitido_es_lo_preliquidado(mundo: Mundo) -> None:
    cargar_base(mundo)
    previa = preliquidacion(mundo)
    cuerpo = emitir_lo_revisado(mundo)
    assert cuerpo["huella"] == previa["huella"]
    for u in previa["unidades"]:
        ob = obligacion_de(cuerpo, u["identificador"])
        assert ob is not None
        assert plata(ob["ordinaria"]) == plata(u["ordinaria"]) + total_de_cargos(u)
        assert (ob["fondo_de_reserva"], ob["extraordinaria"]) == (u["fondo_de_reserva"], u["extraordinaria"])


def test_c02_el_interes_emitido_es_el_preliquidado(mundo: Mundo) -> None:
    """Escenario: Interés igual al preliquidado"""
    configurar(mundo, fondo="0.00")
    emitir_libro(mundo, SEP, {"1A": ("100000.00", "0.00", "0.00")})
    gasto(mundo, "1000.00", periodo=OCT)
    previa = preliquidacion(mundo, OCT)
    cuerpo = emitir_lo_revisado(mundo, OCT)
    filas = mundo.filas(
        "SELECT u.identificador, sum(mv.importe) FROM movimiento mv JOIN cuenta c ON c.id = mv.cuenta_id "
        "JOIN unidad u ON u.id = c.unidad_id WHERE mv.tipo = 'interes' AND mv.sentido = 'debito' "
        "AND mv.emision_id = %s GROUP BY u.identificador",
        (cuerpo["emision_id"],),
    )
    emitidos = {f[0]: Decimal(f[1]) for f in filas}
    esperados = {u["identificador"]: plata(u["intereses"]) for u in previa["unidades"] if plata(u["intereses"])}
    assert emitidos == esperados == {"1A": Decimal("2000.00")}, f"emitido {emitidos}, preliquidado {esperados}"


def test_c03_queda_guardado_lo_usado(mundo: Mundo) -> None:
    """Escenario: Lo emitido no cambia"""
    cargar_base(mundo)
    previa = preliquidacion(mundo)
    cuerpo = emitir_lo_revisado(mundo)
    antes = leer_liquidacion(mundo, cuerpo["liquidacion_id"])
    version = mundo.uno(
        "SELECT id FROM configuracion_versionada WHERE complejo_id = %s ORDER BY vigente_desde DESC LIMIT 1",
        (mundo.edificio,),
    )
    assert antes["estado"] == "emitida"
    assert antes["huella"] == previa["huella"] and antes["porcentaje_fondo"] == "5.00"
    assert antes["version_de_configuracion_id"] == str(version)
    assert antes["vencimiento"] == "2026-11-10" and antes["vencimiento_original"] is None
    assert antes["emitida_por"] == str(mundo.personas["super_admin"])
    assert antes["totales"] == previa["totales"]
    nombres = {c["nombre"] for c in antes["bloques"]["ordinario"]["categorias"]}
    assert nombres == {"Limpieza", "Ascensor"}, nombres
    mundo.ejecutar(
        "UPDATE categoria_de_gasto SET nombre = 'Limpieza renombrada' WHERE id = %s",
        (mundo.categorias["Limpieza"],),
    )
    configurar(mundo, fondo="10.00", desde=NOV)
    despues = leer_liquidacion(mundo, cuerpo["liquidacion_id"])
    assert despues == antes, "renombrar una categoría o cambiar el fondo cambió lo emitido"


def test_c04_la_composicion_de_cada_grupo(mundo: Mundo) -> None:
    cargar_base(mundo)
    cuerpo = emitir_lo_revisado(mundo)
    grupos = {g["grupo_id"]: g for g in leer_liquidacion(mundo, cuerpo["liquidacion_id"])["grupos"]}
    ascensor = {c["unidad_id"]: c["coeficiente"] for c in grupos[str(mundo.ascensor)]["composicion"]}
    assert ascensor == {
        str(mundo.unidades["2A"]): "0.625000",
        str(mundo.unidades["2B"]): "0.375000",
    }, ascensor
    generales = {c["unidad_id"]: c["coeficiente"] for c in grupos[str(mundo.generales)]["composicion"]}
    assert generales == {
        str(mundo.unidades[u]): c for u, c in (("1A", "0.300000"), ("1B", "0.300000"),
                                                ("2A", "0.250000"), ("2B", "0.150000"))
    }, generales


def test_c05_la_foto_del_saldo_anterior(mundo: Mundo) -> None:
    """Escenario: Saldo anterior guardado"""
    cargar_base(mundo)
    emitir_libro(mundo, OCT, {"1A": ("100000.00", "0.00", "0.00")})
    cuerpo = emitir_lo_revisado(mundo)
    del_libro = saldo_anterior_del_libro(mundo, cuerpo["emision_id"], "1A")
    guardado = unidad(leer_liquidacion(mundo, cuerpo["liquidacion_id"]), "1A")["saldo_anterior"]
    assert plata(del_libro) >= Decimal("100000.00"), f"control: 1A debe octubre: {del_libro}"
    assert guardado == del_libro, f"guardado {guardado}, el libro al emitir {del_libro}"
    credito_de_correccion(mundo, "1A", OCT, "1000.00")
    assert saldo_anterior_del_libro(mundo, cuerpo["emision_id"], "1A") != del_libro, (
        "control: la corrección tiene que mover el saldo del libro"
    )
    assert unidad(leer_liquidacion(mundo, cuerpo["liquidacion_id"]), "1A")["saldo_anterior"] == guardado


def test_c06_correr_el_vencimiento(mundo: Mundo) -> None:
    """Escenario: Vencimiento corrido"""
    cargar_base(mundo)
    versiones = mundo.uno("SELECT count(*) FROM configuracion_versionada WHERE complejo_id = %s", (mundo.edificio,))
    cuerpo = emitir_lo_revisado(mundo, vencimiento={"fecha": "2026-11-12", "motivo": MOTIVO_VENCIMIENTO})
    assert cuerpo["vencimiento"] == "2026-11-12"
    assert {v[3] for v in obligaciones_del_libro(mundo).values()} == {NOV.replace(day=12)}
    leida = leer_liquidacion(mundo, cuerpo["liquidacion_id"])
    assert (leida["vencimiento"], leida["vencimiento_original"], leida["motivo_del_vencimiento"]) == (
        "2026-11-12", "2026-11-10", MOTIVO_VENCIMIENTO
    ), leida
    assert leida["emitida_por"] == str(mundo.personas["super_admin"]) and leida["emitida_en"]
    assert mundo.uno(
        "SELECT count(*) FROM configuracion_versionada WHERE complejo_id = %s", (mundo.edificio,)
    ) == versiones, "correr el vencimiento cambió la configuración del edificio"
    assert mundo.uno(
        "SELECT dia_de_vencimiento FROM configuracion_versionada WHERE complejo_id = %s "
        "ORDER BY vigente_desde DESC LIMIT 1", (mundo.edificio,)
    ) == 10


def test_c07_aceptar_un_bloqueante(mundo: Mundo) -> None:
    """Escenario: Bloqueante aceptado"""
    cargar_base(mundo, con_lo_que_no_entra=False)
    gasto(mundo, "555.00", estado="en_revision")
    mundo.como("admin_principal")
    cuerpo = emitir_lo_revisado(mundo, aceptadas=["gastos_en_revision"])
    leida = leer_liquidacion(mundo, cuerpo["liquidacion_id"])
    assert [(a["codigo"], a["aceptada_por"]) for a in leida["alertas_aceptadas"]] == [
        ("gastos_en_revision", str(mundo.personas["admin_principal"]))
    ], leida["alertas_aceptadas"]
    assert leida["alertas_aceptadas"][0]["aceptada_en"]
    assert auditorias(mundo, "aceptar_alertas_bloqueantes") == 1


def test_c07_una_advertencia_no_se_acepta(mundo: Mundo) -> None:
    cargar_base(mundo, con_lo_que_no_entra=False)
    gasto(mundo, "777.00", estado="sin_ia")
    cuerpo = emitir_lo_revisado(mundo)
    assert leer_liquidacion(mundo, cuerpo["liquidacion_id"])["alertas_aceptadas"] == []


def test_c08_un_gasto_aprobado_despues_va_al_siguiente(mundo: Mundo) -> None:
    """Escenario: Gasto aprobado después de emitir"""
    cargar_base(mundo)
    emitir_lo_revisado(mundo)
    tarde = gasto(mundo, "800.00", estado="borrador", periodo=NOV)
    r = mundo.cliente.post(f"/api/gastos/{tarde}/aprobar")
    assert r.status_code == 200, f"aprobar el gasto: {r.status_code} {r.text[:300]}"
    imputacion = mundo.uno("SELECT periodo_de_imputacion FROM gasto WHERE id = %s", (tarde,))
    assert imputacion == DIC, f"un gasto de noviembre aprobado con noviembre emitido va a diciembre: {imputacion}"


def test_c09_el_mismo_pedido_dos_veces(mundo: Mundo) -> None:
    """Escenario: Reintento del mismo pedido"""
    cargar_base(mundo)
    pedido = cuerpo_de_emision(preliquidacion(mundo)["huella"])
    primera = emitida(emitir(mundo, pedido))
    segunda = emitida(emitir(mundo, pedido))
    assert segunda["liquidacion_id"] == primera["liquidacion_id"]
    assert segunda["obligaciones"] == primera["obligaciones"]
    assert len(obligaciones_del_libro(mundo)) == 4
    assert auditorias(mundo, "emitir_y_distribuir_liquidacion") == 1


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal", "admin_del_edificio"])
def test_c10_pueden_emitir(mundo: Mundo, rol: str) -> None:
    cargar_base(mundo)
    mundo.como(rol)
    emitir_lo_revisado(mundo)


@pytest.mark.parametrize("rol", ["contador", "consejo", "auxiliar"])
def test_c10_no_pueden_emitir(mundo: Mundo, rol: str) -> None:
    cargar_base(mundo)
    huella = preliquidacion(mundo)["huella"]
    mundo.como(rol)
    r = emitir(mundo, cuerpo_de_emision(huella))
    assert r.status_code == 403, f"{rol}: {r.status_code} {r.text[:300]}"
    assert r.json()["detail"].get("permiso_faltante") == "emitir_y_distribuir_liquidacion"


@pytest.mark.parametrize("quien", ["admin_de_otro_edificio", "administracion_b"])
def test_c10_fuera_de_alcance(mundo: Mundo, quien: str) -> None:
    cargar_base(mundo)
    huella = preliquidacion(mundo)["huella"]
    mundo.como(quien)
    r = emitir(mundo, cuerpo_de_emision(huella))
    assert r.status_code == 404 and r.json() == {"detail": "no encontrado"}, f"{quien}: {r.text[:300]}"


def test_c10_sin_sesion(mundo: Mundo) -> None:
    cargar_base(mundo)
    huella = preliquidacion(mundo)["huella"]
    mundo.sin_sesion()
    assert emitir(mundo, cuerpo_de_emision(huella)).status_code == 401


def test_c10_leer_lo_emitido_por_rol(mundo: Mundo) -> None:
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    ruta = f"/api/complejos/{mundo.edificio}/liquidaciones/{liquidacion}"
    for rol, codigo in (("admin_del_edificio", 200), ("contador", 200), ("auxiliar", 403)):
        mundo.como(rol)
        r = mundo.cliente.get(ruta)
        assert r.status_code == codigo, f"{rol} leyendo la liquidación: {r.status_code} {r.text[:200]}"
    mundo.como("admin_de_otro_edificio")
    assert mundo.cliente.get(ruta).status_code == 404
