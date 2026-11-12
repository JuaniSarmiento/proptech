"""H-010 · C09 a C12: lo que el ajuste tiene que rechazar sin escribir nada (ni obligación, ni
cuenta, ni ajuste, ni auditoría).

Orden de chequeo de la API (D7 del 2a): primero el alcance (404), después el permiso (403).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from ._h010 import (
    ACCION,
    MOTIVO,
    Mundo,
    ajustar_api,
    ajuste_creado,
    cargar_base,
    conflicto,
    conteos,
    invalido,
    poner_estado,
)

pytestmark = pytest.mark.integracion


# --- C09 · La migración no está confirmada --------------------------------------------------------


def test_c09_edificio_pendiente(mundo: Mundo) -> None:
    """Escenario: Edificio pendiente"""
    cargar_base(mundo, confirmar=False)
    antes = conteos(mundo)
    conflicto(ajustar_api(mundo, "1A"), "estado_migracion")
    assert conteos(mundo) == antes


def test_c09_edificio_sin_saldos_previos(mundo: Mundo) -> None:
    poner_estado(mundo, "sin_saldos_previos")
    antes = conteos(mundo)
    conflicto(ajustar_api(mundo, "1A"), "estado_migracion")
    assert conteos(mundo) == antes


def test_c09_edificio_pendiente_sin_carga(mundo: Mundo) -> None:
    antes = conteos(mundo)
    conflicto(ajustar_api(mundo, "5E"), "estado_migracion")
    assert conteos(mundo) == antes


# --- C10 · Motivo, importe y componente -----------------------------------------------------------


@pytest.mark.parametrize(
    "motivo",
    ["", "   ", "x" * 501],
    ids=["vacio", "en_blanco", "501_caracteres"],
)
def test_c10_sin_motivo(mundo: Mundo, motivo: str) -> None:
    """Escenario: Sin motivo"""
    cargar_base(mundo)
    antes = conteos(mundo)
    invalido(ajustar_api(mundo, "1A", motivo=motivo), "motivo")
    assert conteos(mundo) == antes


def test_c10_un_motivo_de_500_caracteres_entra(mundo: Mundo) -> None:
    """Control del borde: 500 caracteres es el máximo y entra."""
    cargar_base(mundo)
    ajuste_creado(ajustar_api(mundo, "1A", motivo="x" * 500))


@pytest.mark.parametrize(
    "importe",
    ["0.00", "-1.00", "1.234", "1000000000000.00"],
    ids=["cero", "negativo", "tres_decimales", "fuera_de_numeric_14_2"],
)
def test_c10_importe_invalido(mundo: Mundo, importe: str) -> None:
    cargar_base(mundo)
    antes = conteos(mundo)
    invalido(ajustar_api(mundo, "1A", importe), "importe")
    assert conteos(mundo) == antes


@pytest.mark.parametrize("componente", ["interes", "otro", ""])
def test_c10_componente_invalido(mundo: Mundo, componente: str) -> None:
    cargar_base(mundo)
    antes = conteos(mundo)
    invalido(ajustar_api(mundo, "1A", componente=componente), "componente")
    assert conteos(mundo) == antes


# --- C11 · La misma operación con otros datos -----------------------------------------------------


@pytest.mark.parametrize(
    "cambio",
    [
        {"importe": "4000.00"},
        {"motivo": "Otro motivo"},
        {"componente": "extraordinaria"},
        {"unidad": "1B"},
    ],
    ids=["otro_importe", "otro_motivo", "otro_componente", "otra_unidad"],
)
def test_c11_la_misma_operacion_con_otros_datos(mundo: Mundo, cambio: dict[str, str]) -> None:
    cargar_base(mundo)
    operacion = uuid4()
    ajuste_creado(ajustar_api(mundo, "1A", operacion_id=operacion))
    antes = conteos(mundo)
    respuesta = ajustar_api(
        mundo,
        cambio.get("unidad", "1A"),
        cambio.get("importe", "5000.00"),
        componente=cambio.get("componente", "ordinaria"),
        motivo=cambio.get("motivo", MOTIVO),
        operacion_id=operacion,
    )
    conflicto(respuesta, "operacion_id")
    assert conteos(mundo) == antes


# --- C12 · Permisos y tenant ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "rol",
    [
        "admin_del_edificio",
        "contador",
        "auxiliar",
        "consejo",
        "vecino_propietario",
        "vecino_inquilino",
    ],
)
def test_c12_administrador_del_edificio(mundo: Mundo, rol: str) -> None:
    """Escenario: Administrador del edificio"""
    cargar_base(mundo)
    mundo.como(rol)
    antes = conteos(mundo)
    respuesta = ajustar_api(mundo, "1A")
    assert respuesta.status_code == 403, f"{rol}: se esperaba 403, llegó {respuesta.status_code}"
    assert ACCION in respuesta.text, f"el 403 nombra el permiso que falta: {respuesta.text[:300]}"
    assert conteos(mundo) == antes


def test_c12_administrador_de_otro_edificio_no_lo_ve(mundo: Mundo) -> None:
    cargar_base(mundo)
    mundo.como("admin_de_otro_edificio")
    antes = conteos(mundo)
    respuesta = ajustar_api(mundo, "1A")
    assert respuesta.status_code == 404, f"se esperaba 404 (D7), llegó {respuesta.status_code}"
    assert respuesta.json() == {"detail": "no encontrado"}, respuesta.text[:200]
    assert conteos(mundo) == antes


def test_c12_unidad_de_otro_edificio(mundo: Mundo) -> None:
    cargar_base(mundo)
    antes = conteos(mundo)
    respuesta = ajustar_api(mundo, mundo.unidad_otro)
    assert respuesta.status_code == 404, f"se esperaba 404, llegó {respuesta.status_code}"
    assert respuesta.json() == {"detail": "no encontrado"}, respuesta.text[:200]
    assert conteos(mundo) == antes


def test_c12_unidad_inexistente(mundo: Mundo) -> None:
    cargar_base(mundo)
    antes = conteos(mundo)
    respuesta = ajustar_api(mundo, uuid4())
    assert respuesta.status_code == 404, f"se esperaba 404, llegó {respuesta.status_code}"
    assert respuesta.json() == {"detail": "no encontrado"}, (
        f"el 404 es el de la unidad, no el de una ruta inexistente: {respuesta.text[:200]}"
    )
    assert conteos(mundo) == antes


def test_c12_otra_administracion(mundo: Mundo) -> None:
    cargar_base(mundo)
    mundo.como("administracion_b")
    antes = conteos(mundo)
    respuesta = ajustar_api(mundo, "1A")
    assert respuesta.status_code == 404, f"se esperaba 404, llegó {respuesta.status_code}"
    assert respuesta.json() == {"detail": "no encontrado"}, respuesta.text[:200]
    respuesta_b = ajustar_api(mundo, "1A", complejo=mundo.edificio_b)
    assert respuesta_b.status_code == 404, (
        f"B no ajusta una unidad de A desde su edificio: {respuesta_b.status_code}"
    )
    assert conteos(mundo) == antes


def test_c12_sin_sesion_401(mundo: Mundo) -> None:
    cargar_base(mundo)
    mundo.sin_sesion()
    respuesta = ajustar_api(mundo, "1A")
    assert respuesta.status_code == 401, f"se esperaba 401, llegó {respuesta.status_code}"
