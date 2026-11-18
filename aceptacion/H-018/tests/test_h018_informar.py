"""H-018 · informar un pago (C01 a C07, N01 a N07). Contrato en `aceptacion/H-018/CONTRATO.md`."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import psycopg
import pytest

from .._edificios import fijar_tenant
from ._h018 import (
    EXE,
    JPEG,
    PDF,
    PNG,
    TABLAS,
    Mundo,
    campo_422,
    comprobante,
    cuerpo,
    del_libro,
    filas_de,
    informado,
    informar,
    informar_ok,
    listar,
    rechazar_en_la_base,
    ruta,
    situacion,
    subir,
)

DIEZ_MB = 10 * 1024 * 1024


def _conflicto_repetido(r: Any) -> None:
    assert r.status_code == 409, f"se esperaba 409 repetido, llegó {r.status_code}: {r.text[:300]}"
    datos = r.json()
    assert (datos.get("campo"), datos.get("motivo")) == ("numero_de_operacion", "repetido"), datos


def _no_encontrado(r: Any) -> None:
    assert r.status_code == 404, f"se esperaba 404, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == {"detail": "no encontrado"}, f"un 404 de una ruta que existe: {r.json()}"


def _pagos_creados(m: Mundo) -> int:
    return filas_de(m, "pago_informado")


# --- C01: informar no cambia la deuda --------------------------------------------------------------


def test_c01_informar_no_cambia_la_deuda(mundo: Mundo) -> None:
    """Escenario: Pago informado"""
    antes, libro = situacion(mundo), del_libro(mundo)
    pago = informar_ok(mundo, {"1A": "43350.00"})
    assert situacion(mundo) == antes, "informar un pago cambió la deuda o la situación de una cuenta"
    assert del_libro(mundo) == libro, "informar un pago escribió en el libro"
    vistos = {p["pago_id"]: p for p in listar(mundo)}
    assert pago in vistos and vistos[pago]["estado"] == "informado", vistos
    assert vistos[pago]["monto"] == "43350.00" and vistos[pago]["fecha_de_transferencia"] == "2026-11-05"


# --- C02: reparto entre dos unidades ---------------------------------------------------------------


def test_c02_reparto_entre_dos_unidades(mundo: Mundo) -> None:
    """Escenario: Reparto entre dos unidades"""
    pago = informar_ok(mundo, {"1A": "43350.00", "2B": "37425.00"}, numero="777")
    r = mundo.cliente.get(ruta(mundo, f"/{pago}"))
    assert r.status_code == 200, f"leer el pago: {r.status_code} {r.text[:300]}"
    partes = {p["identificador"]: p["importe"] for p in r.json()["partes"]}
    assert partes == {"1A": "43350.00", "2B": "37425.00"}, f"las partes del pago: {partes}"
    assert r.json()["monto"] == "80775.00"


# --- C03: el administrador informa por el vecino ---------------------------------------------------


@pytest.mark.parametrize("rol", ["admin_principal", "admin_del_edificio"])
def test_c03_el_administrador_informa_por_el_vecino(mundo: Mundo, rol: str) -> None:
    mundo.como(rol)
    informar_ok(mundo, {"1B": "48350.00"}, numero=f"adm-{rol}")
    assert any(p["partes"][0]["identificador"] == "1B" for p in listar(mundo))


# --- C04: el número de operación es único por edificio y banco -------------------------------------


def test_c04_numero_repetido_escrito_distinto(mundo: Mundo) -> None:
    """Escenario: El mismo comprobante dos veces"""
    informar_ok(mundo, {"1A": "43350.00"}, banco="Banco Nación", numero="12-345.678")
    _conflicto_repetido(informar(mundo, cuerpo(mundo, comprobante(mundo), {"1A": "43350.00"},
                                               banco="banco nacion", numero="12345678")))
    _conflicto_repetido(informar(mundo, cuerpo(mundo, comprobante(mundo), {"2B": "37425.00"},
                                               banco=" BANCO  NACIÓN ", numero="12 345 678")))
    assert _pagos_creados(mundo) == 1


def test_c04_repetido_para_otra_unidad_de_otra_persona(mundo: Mundo) -> None:
    informar_ok(mundo, {"1A": "43350.00"}, numero="555")
    mundo.como("beto")
    _conflicto_repetido(informar(mundo, cuerpo(mundo, comprobante(mundo), {"1B": "48350.00"}, numero="555")))


def test_c04_otro_banco_mismo_numero(mundo: Mundo) -> None:
    """Escenario: Otro banco con el mismo número"""
    informar_ok(mundo, {"1A": "43350.00"}, banco="Banco Nación", numero="12345678")
    informar_ok(mundo, {"2B": "37425.00"}, banco="Mercado Pago", numero="12345678")
    assert _pagos_creados(mundo) == 2


def test_c04_el_mismo_numero_en_otro_edificio(mundo: Mundo) -> None:
    informar_ok(mundo, {"1A": "43350.00"}, numero="999")
    mundo.como("super_admin")
    otro = comprobante(mundo, complejo=mundo.otro)
    datos = cuerpo(mundo, otro, {"x": "100.00"}, numero="999")
    datos["partes"] = [{"unidad_id": str(mundo.unidad_otro), "importe": "100.00"}]
    informado(informar(mundo, datos, complejo=mundo.otro))


# --- C05: un rechazado libera su número ------------------------------------------------------------


def test_c05_un_rechazado_libera_su_numero(mundo: Mundo) -> None:
    """Escenario: Un rechazado libera su número"""
    pago = informar_ok(mundo, {"1A": "43350.00"}, numero="321")
    rechazar_en_la_base(mundo, pago)
    nuevo = informar_ok(mundo, {"1A": "43350.00"}, numero="321")
    estados = {p["pago_id"]: (p["estado"], p["motivo"]) for p in listar(mundo)}
    assert estados[pago] == ("rechazado", "Motivo ficticio"), estados
    assert estados[nuevo][0] == "informado", estados


def test_c05_sin_rechazo_el_numero_sigue_ocupado(mundo: Mundo) -> None:
    informar_ok(mundo, {"1A": "43350.00"}, numero="322")
    _conflicto_repetido(informar(mundo, cuerpo(mundo, comprobante(mundo), {"1A": "43350.00"}, numero="322")))


# --- C06: cada uno ve sus pagos --------------------------------------------------------------------


def test_c06_cada_uno_ve_sus_pagos(mundo: Mundo) -> None:
    """Escenario: El vecino ve el estado"""
    de_1a = informar_ok(mundo, {"1A": "43350.00"}, numero="a1")
    de_2b = informar_ok(mundo, {"2B": "37425.00"}, numero="a2")
    mundo.como("beto")
    de_1b = informar_ok(mundo, {"1B": "48350.00"}, numero="b1")
    assert {p["pago_id"] for p in listar(mundo)} == {de_1b}, "Beto ve pagos que no son de 1B"
    mundo.como("ana")
    assert {p["pago_id"] for p in listar(mundo)} == {de_1a, de_2b}, "Ana no ve exactamente los de 1A y 2B"
    for rol in ("admin_principal", "admin_del_edificio", "super_admin"):
        mundo.como(rol)
        assert {p["pago_id"] for p in listar(mundo)} == {de_1a, de_2b, de_1b}, f"{rol} no ve los del edificio"


# --- C07: subir el comprobante -------------------------------------------------------------------


@pytest.mark.parametrize(("contenido", "nombre"), [(PNG, "c.png"), (JPEG, "c.jpg"), (PDF, "c.pdf")],
                         ids=["png", "jpg", "pdf"])
def test_c07_subir_comprobante_sin_ia(mundo: Mundo, contenido: bytes, nombre: str) -> None:
    r = subir(mundo, contenido, nombre)
    assert r.status_code == 201, f"subir {nombre}: {r.status_code} {r.text[:300]}"
    datos = r.json()
    assert datos.get("lectura") == "sin_ia", f"sin clave de IA la lectura es `sin_ia`: {datos}"
    assert datos.get("propuesta") == {"banco": None, "numero_de_operacion": None, "fecha": None,
                                      "monto": None, "cbu_origen": None}, datos
    assert filas_de(mundo, "comprobante_de_pago") == 1


def test_c07_el_limite_de_tamano_entra(mundo: Mundo) -> None:
    contenido = PNG + bytes(DIEZ_MB - len(PNG))
    assert subir(mundo, contenido).status_code == 201, "un comprobante de exactamente 10 MB tiene que entrar"


# --- N01: una unidad ajena -------------------------------------------------------------------------


@pytest.mark.parametrize("unidad", ["1B", "2A"])
def test_n01_una_unidad_ajena(mundo: Mundo, unidad: str) -> None:
    """Escenario: Una unidad ajena"""
    _no_encontrado(informar(mundo, cuerpo(mundo, comprobante(mundo), {unidad: "100.00"})))
    assert _pagos_creados(mundo) == 0


def test_n01_una_parte_ajena_entre_propias(mundo: Mundo) -> None:
    _no_encontrado(informar(mundo, cuerpo(mundo, comprobante(mundo), {"1A": "100.00", "1B": "100.00"})))
    assert _pagos_creados(mundo) == 0 and filas_de(mundo, "parte_de_pago") == 0


def test_n01_unidad_de_otro_edificio_o_inexistente(mundo: Mundo) -> None:
    mundo.como("admin_principal")
    for unidad in (mundo.unidad_otro, uuid4()):
        datos = cuerpo(mundo, comprobante(mundo), {"1A": "100.00"})
        datos["partes"] = [{"unidad_id": str(unidad), "importe": "100.00"}]
        _no_encontrado(informar(mundo, datos))
    assert _pagos_creados(mundo) == 0


# --- N02: los datos del pago -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cambio", "campo"),
    [
        ({"monto": "43350.01"}, "partes"),
        ({"monto": "0.00", "partes": [("1A", "0.00")]}, "monto"),
        ({"monto": "-10.00", "partes": [("1A", "-10.00")]}, "monto"),
        ({"monto": "100.000", "partes": [("1A", "100.000")]}, "monto"),
        ({"monto": 100.5, "partes": [("1A", "100.50")]}, "monto"),
        ({"partes": [("1A", "100.00"), ("1A", "100.00")], "monto": "200.00"}, "partes"),
        ({"partes": []}, "partes"),
        ({"fecha_de_transferencia": "2026-11-19"}, "fecha_de_transferencia"),
        ({"fecha_de_transferencia": "2025-11-17"}, "fecha_de_transferencia"),
        ({"fecha_de_transferencia": "2026-02-30"}, "fecha_de_transferencia"),
        ({"banco": "   "}, "banco"),
        ({"numero_de_operacion": ""}, "numero_de_operacion"),
        ({"numero_de_operacion": "9" * 101}, "numero_de_operacion"),
        ({"cbu_origen": "123"}, "cbu_origen"),
    ],
)
def test_n02_datos_invalidos(mundo: Mundo, cambio: dict[str, Any], campo: str) -> None:
    """Escenario: Partes que no suman"""
    datos = cuerpo(mundo, comprobante(mundo), {"1A": "43350.00"})
    for clave, valor in cambio.items():
        if clave == "partes":
            datos["partes"] = [{"unidad_id": str(mundo.unidades[u]), "importe": i} for u, i in valor]
        else:
            datos[clave] = valor
    assert campo_422(informar(mundo, datos)) == campo
    assert _pagos_creados(mundo) == 0


def test_n02_fecha_futura(mundo: Mundo) -> None:
    """Escenario: Fecha futura"""
    datos = cuerpo(mundo, comprobante(mundo), {"1A": "43350.00"}, fecha="2026-11-19")
    assert campo_422(informar(mundo, datos)) == "fecha_de_transferencia"


def test_n02_los_bordes_de_la_fecha_entran(mundo: Mundo) -> None:
    informar_ok(mundo, {"1A": "100.00"}, fecha="2026-11-18", numero="hoy")
    informar_ok(mundo, {"1A": "100.00"}, fecha="2025-11-18", numero="hace-un-anio")


# --- N03: un archivo que no es comprobante ---------------------------------------------------------


@pytest.mark.parametrize(
    ("contenido", "nombre"),
    [(EXE, "virus.png"), (b"", "vacio.png"), (b"texto plano", "nota.pdf"), (PNG + bytes(DIEZ_MB), "grande.png")],
    ids=["ejecutable", "vacio", "texto", "mas-de-10-mb"],
)
def test_n03_un_archivo_que_no_es_comprobante(mundo: Mundo, contenido: bytes, nombre: str) -> None:
    """Escenario: Un archivo que no es comprobante"""
    r = subir(mundo, contenido, nombre)
    assert campo_422(r) == "archivo"
    assert filas_de(mundo, "comprobante_de_pago") == 0


# --- N04: el comprobante -------------------------------------------------------------------------


def test_n04_el_mismo_comprobante_en_dos_pagos(mundo: Mundo) -> None:
    usado = comprobante(mundo)
    informado(informar(mundo, cuerpo(mundo, usado, {"1A": "43350.00"}, numero="c1")))
    assert campo_422(informar(mundo, cuerpo(mundo, usado, {"2B": "37425.00"}, numero="c2"))) == "comprobante_id"
    assert _pagos_creados(mundo) == 1


def test_n04_comprobante_ajeno(mundo: Mundo) -> None:
    mundo.como("beto")
    de_beto = comprobante(mundo)
    mundo.como("super_admin")
    del_otro_edificio = comprobante(mundo, complejo=mundo.otro)
    mundo.como("ana")
    for comprobante_id in (de_beto, del_otro_edificio, str(uuid4())):
        datos = cuerpo(mundo, comprobante_id, {"1A": "43350.00"})
        assert campo_422(informar(mundo, datos)) == "comprobante_id", comprobante_id
    assert _pagos_creados(mundo) == 0


# --- N05: ver un pago ajeno ------------------------------------------------------------------------


def test_n05_ver_un_pago_ajeno(mundo: Mundo) -> None:
    pago = informar_ok(mundo, {"1A": "43350.00"})
    mundo.como("beto")
    assert pago not in {p["pago_id"] for p in listar(mundo)}
    _no_encontrado(mundo.cliente.get(ruta(mundo, f"/{pago}")))
    _no_encontrado(mundo.cliente.get(ruta(mundo, f"/{uuid4()}")))
    mundo.como("administracion_b")
    _no_encontrado(mundo.cliente.get(ruta(mundo, f"/{pago}")))
    r = mundo.cliente.get(ruta(mundo, complejo=mundo.edificio_b))
    assert r.status_code == 200 and pago not in {p["pago_id"] for p in r.json()}
    mundo.como("admin_de_otro_edificio")
    _no_encontrado(mundo.cliente.get(ruta(mundo, f"/{pago}")))


def test_n05_otra_administracion_no_ve_las_filas(mundo: Mundo) -> None:
    informar_ok(mundo, {"1A": "43350.00"})
    for tabla in ("comprobante_de_pago", "pago_informado", "parte_de_pago"):
        assert mundo.filas(f"SELECT count(*) FROM {tabla}", admin=mundo.admin_b)[0][0] == 0, (  # noqa: S608
            f"la administración B ve filas de {tabla}"
        )


# --- N06: sin permiso ------------------------------------------------------------------------------


@pytest.mark.parametrize("rol", ["consejo", "contador", "auxiliar"])
def test_n06_sin_permiso_no_informa(mundo: Mundo, rol: str) -> None:
    mundo.como(rol)
    r = informar(mundo, cuerpo(mundo, str(uuid4()), {"1A": "43350.00"}))
    assert r.status_code == 403, f"{rol}: se esperaba 403, llegó {r.status_code}: {r.text[:200]}"
    s = subir(mundo)
    assert s.status_code == 403, f"{rol}: subir el comprobante, se esperaba 403, llegó {s.status_code}"
    assert _pagos_creados(mundo) == 0 and filas_de(mundo, "comprobante_de_pago") == 0


def test_n06_fuera_del_alcance(mundo: Mundo) -> None:
    mundo.como("admin_de_otro_edificio")
    _no_encontrado(informar(mundo, cuerpo(mundo, str(uuid4()), {"1A": "43350.00"})))
    mundo.como("ana")
    _no_encontrado(subir(mundo, complejo=mundo.otro))


# --- N07: las tablas no se editan ----------------------------------------------------------------


@pytest.mark.parametrize("tabla", TABLAS)
def test_n07_la_app_no_edita_ni_borra(mundo: Mundo, tabla: str) -> None:
    informar_ok(mundo, {"1A": "43350.00"})
    for sentencia in (f"UPDATE {tabla} SET administracion_id = administracion_id", f"DELETE FROM {tabla}"):
        with mundo.base.conectar_app() as conexion:
            with pytest.raises(psycopg.Error) as error, conexion.transaction():
                fijar_tenant(conexion, mundo.admin)
                conexion.execute(sentencia)  # type: ignore[arg-type]
        assert isinstance(error.value, psycopg.errors.InsufficientPrivilege), (
            f"{sentencia}: se esperaba falta de permiso, llegó {type(error.value).__name__}: {error.value}"
        )
