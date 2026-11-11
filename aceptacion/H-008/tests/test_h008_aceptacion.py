"""H-008 · C09, C10 (la aceptación anterior deja de valer) y C15: aceptar diferencias con registro,
permisos, tenant, migración cerrada y concurrencia.

Orden de chequeo de la API (D7 del 2a): primero el alcance (404), después el permiso (403).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from ._h008 import (
    ACCION,
    Mundo,
    aceptacion_creada,
    aceptar,
    archivo,
    auditorias,
    comparacion,
    conflicto,
    conteos,
    control_base,
    diferencias,
    en_paralelo,
    exigir_tablas,
    subir,
)

pytestmark = pytest.mark.integracion

DOS_DIFERENCIAS = {
    ("1A", "169000.00", "159000.00", "10000.00"),
    ("2A", "52000.00", "62000.00", "-10000.00"),
}


def _con_diferencias(m: Mundo) -> dict[str, Any]:
    control = control_base()
    control[0][1] = "159000.00"
    control[2][1] = "62000.00"
    return subir(m, archivo(control=control))


def _filas_de_aceptacion(m: Mundo, importacion_id: str) -> list[Any]:
    exigir_tablas(m)
    return m.filas(
        "SELECT aceptada_por, aceptada_en FROM aceptacion_de_diferencias WHERE importacion_id = %s",
        (importacion_id,),
    )


# --- C09 · Aceptar diferencias --------------------------------------------------------------------


def test_c09_aceptar_diferencias_queda_registrado(mundo: Mundo) -> None:
    """Escenario: Aceptar diferencias"""
    cuerpo = _con_diferencias(mundo)
    mundo.como("admin_principal")
    antes = datetime.now().astimezone()
    acepto = aceptacion_creada(aceptar(mundo, cuerpo["importacion_id"]))
    assert diferencias(acepto["diferencias"]) == DOS_DIFERENCIAS, acepto["diferencias"]
    assert acepto["aceptada_por"] == str(mundo.personas["admin_principal"])
    assert datetime.fromisoformat(acepto["aceptada_en"]) >= antes.replace(microsecond=0)
    filas = _filas_de_aceptacion(mundo, cuerpo["importacion_id"])
    assert len(filas) == 1 and filas[0][0] == mundo.personas["admin_principal"], filas
    assert auditorias(mundo, ACCION) == 1, "una auditoría de aceptar_diferencias_de_saldos"
    c = comparacion(mundo)
    assert c["aceptacion"] is not None, "la comparación muestra la aceptación"
    assert diferencias(c["aceptacion"]["diferencias"]) == DOS_DIFERENCIAS
    assert c["aceptacion"]["aceptada_por"] == str(mundo.personas["admin_principal"])
    assert c["requiere_aceptacion"] is False, "con las diferencias aceptadas no requiere aceptación"


def test_c09_aceptar_dos_veces(mundo: Mundo) -> None:
    cuerpo = _con_diferencias(mundo)
    aceptacion_creada(aceptar(mundo, cuerpo["importacion_id"]))
    antes = conteos(mundo)
    conflicto(aceptar(mundo, cuerpo["importacion_id"]), "aceptacion")
    assert conteos(mundo) == antes, "la segunda aceptación no escribe nada"
    assert len(_filas_de_aceptacion(mundo, cuerpo["importacion_id"])) == 1


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal"])
def test_c09_los_que_pueden_aceptar(mundo: Mundo, rol: str) -> None:
    """Control de E6: super admin y administrador principal aceptan."""
    cuerpo = _con_diferencias(mundo)
    mundo.como(rol)
    aceptacion_creada(aceptar(mundo, cuerpo["importacion_id"]))


# --- C10 · Un borrador nuevo deja sin valor la aceptación anterior --------------------------------


def test_c10_la_aceptacion_anterior_no_vale_para_el_borrador_nuevo(mundo: Mundo) -> None:
    """Escenario: Borrador nuevo después de aceptar"""
    primero = _con_diferencias(mundo)
    aceptacion_creada(aceptar(mundo, primero["importacion_id"]))
    control = control_base()
    control[0][1] = "159000.00"
    control[2][1] = "62000.00"
    control[1][1] = "104000.00"  # otro contenido
    segundo = subir(mundo, archivo(control=control))
    c = comparacion(mundo)
    assert c["importacion_id"] == segundo["importacion_id"]
    assert c["aceptacion"] is None, "la aceptación del borrador anterior no vale para el nuevo"
    assert c["requiere_aceptacion"] is True
    antes = conteos(mundo)
    conflicto(aceptar(mundo, primero["importacion_id"]), "importacion_id")
    assert conteos(mundo) == antes, "aceptar el borrador descartado no escribe nada"


# --- C15 · Lo que tiene que fallar al aceptar -----------------------------------------------------


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
def test_c15_sin_permiso_403(mundo: Mundo, rol: str) -> None:
    """Escenario: Administrador del edificio"""
    cuerpo = _con_diferencias(mundo)
    mundo.como(rol)
    antes = conteos(mundo)
    respuesta = aceptar(mundo, cuerpo["importacion_id"])
    assert respuesta.status_code == 403, f"{rol}: se esperaba 403, llegó {respuesta.status_code}"
    assert ACCION in respuesta.text, f"el 403 nombra el permiso que falta: {respuesta.text[:300]}"
    assert conteos(mundo) == antes


def test_c15_administrador_de_otro_edificio_no_lo_ve(mundo: Mundo) -> None:
    cuerpo = _con_diferencias(mundo)
    mundo.como("admin_de_otro_edificio")
    antes = conteos(mundo)
    respuesta = aceptar(mundo, cuerpo["importacion_id"])
    assert respuesta.status_code == 404, f"se esperaba 404 (D7), llegó {respuesta.status_code}"
    assert respuesta.json() == {"detail": "no encontrado"}, respuesta.text[:200]
    assert conteos(mundo) == antes


def test_c15_otra_administracion(mundo: Mundo) -> None:
    cuerpo = _con_diferencias(mundo)
    mundo.como("administracion_b")
    antes = conteos(mundo)
    respuesta = aceptar(mundo, cuerpo["importacion_id"])
    assert respuesta.status_code == 404, f"se esperaba 404, llegó {respuesta.status_code}"
    assert respuesta.json() == {"detail": "no encontrado"}, respuesta.text[:200]
    assert conteos(mundo) == antes
    comparar_b = mundo.cliente.get(f"/api/complejos/{mundo.edificio}/importaciones/comparacion")
    assert comparar_b.status_code == 404, "B tampoco ve la comparación de A"


def test_c15_sin_sesion_401(mundo: Mundo) -> None:
    cuerpo = _con_diferencias(mundo)
    mundo.sin_sesion()
    respuesta = aceptar(mundo, cuerpo["importacion_id"])
    assert respuesta.status_code == 401, f"se esperaba 401, llegó {respuesta.status_code}"


def test_c15_sin_diferencias_no_hay_nada_que_aceptar(mundo: Mundo) -> None:
    cuerpo = subir(mundo)
    antes = conteos(mundo)
    conflicto(aceptar(mundo, cuerpo["importacion_id"]), "diferencias")
    assert conteos(mundo) == antes


def test_c15_con_la_migracion_cerrada(mundo: Mundo) -> None:
    cuerpo = _con_diferencias(mundo)
    mundo.ejecutar(
        "UPDATE complejo SET estado_migracion = 'confirmada' WHERE id = %s", (mundo.edificio,)
    )
    antes = conteos(mundo)
    conflicto(aceptar(mundo, cuerpo["importacion_id"]), "estado_migracion")
    assert conteos(mundo) == antes


def test_c15_dos_aceptaciones_simultaneas(mundo: Mundo) -> None:
    cuerpo = _con_diferencias(mundo)
    resultados = en_paralelo(
        lambda: aceptar(mundo, cuerpo["importacion_id"]),
        lambda: aceptar(mundo, cuerpo["importacion_id"]),
    )
    for r in resultados:
        assert not isinstance(r, BaseException), f"una aceptación explotó: {r!r}"
    codigos = sorted(r.status_code for r in resultados)
    assert codigos == [201, 409], f"una acepta y la otra da conflicto: {codigos}"
    assert len(_filas_de_aceptacion(mundo, cuerpo["importacion_id"])) == 1
    assert auditorias(mundo, ACCION) == 1
