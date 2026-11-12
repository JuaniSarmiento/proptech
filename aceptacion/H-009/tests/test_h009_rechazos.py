"""H-009 · C07 a C12: lo que confirmar tiene que rechazar sin escribir nada (ni en el libro, ni
en el estado del edificio, ni en la importación, ni en la auditoría).

Orden de chequeo de la API (D7 del 2a): primero el alcance (404), después el permiso (403).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from ._h009 import (
    ACCION,
    Mundo,
    aceptacion_creada,
    aceptar,
    archivo,
    auditorias,
    cargas,
    confirmacion_creada,
    confirmar,
    conflicto,
    conteos,
    control_base,
    en_paralelo,
    estado_de,
    estado_del_edificio,
    importar,
    libro,
    subir,
)

pytestmark = pytest.mark.integracion


def _con_diferencias(m: Mundo) -> dict[str, Any]:
    control = control_base()
    control[0][1] = "159000.00"
    return subir(m, archivo(control=control))


# --- C07 · Diferencias sin aceptar y sin borrador vigente -----------------------------------------


def test_c07_diferencias_sin_aceptar(mundo: Mundo) -> None:
    """Escenario: Diferencias sin aceptar"""
    cuerpo = _con_diferencias(mundo)
    antes = conteos(mundo)
    conflicto(confirmar(mundo, cuerpo["importacion_id"]), "diferencias")
    assert conteos(mundo) == antes, "confirmar con diferencias sin aceptar no escribe nada"
    assert estado_del_edificio(mundo) == "pendiente"
    assert estado_de(mundo, cuerpo["importacion_id"]) == "borrador"


def test_c07_la_importacion_no_es_el_borrador_vigente(mundo: Mundo) -> None:
    primero = subir(mundo)
    control = control_base()
    control[1][1] = "104000.00"  # otro contenido: descarta el primero
    subir(mundo, archivo(control=control))
    antes = conteos(mundo)
    conflicto(confirmar(mundo, primero["importacion_id"]), "importacion_id")
    assert conteos(mundo) == antes, "confirmar el borrador descartado no escribe nada"


def test_c07_una_importacion_que_no_existe(mundo: Mundo) -> None:
    subir(mundo)
    antes = conteos(mundo)
    conflicto(confirmar(mundo, str(uuid4())), "importacion_id")
    assert conteos(mundo) == antes


def test_c07_una_importacion_sin_hoja_de_saldos(mundo: Mundo) -> None:
    """E10: sin hoja `Saldos` no hay borrador que confirmar; el edificio se cierra con "sin saldos
    previos"."""
    respuesta = importar(mundo, libro({"Notas": [["Texto"], ["sin saldos"]]}))
    assert respuesta.status_code == 201, (
        f"un archivo sin padrón ni saldos se acepta en un edificio con padrón (H-007): "
        f"{respuesta.status_code} {respuesta.text[:300]}"
    )
    antes = conteos(mundo)
    conflicto(confirmar(mundo, respuesta.json()["importacion_id"]), "saldos")
    assert conteos(mundo) == antes
    assert estado_del_edificio(mundo) == "pendiente"


# --- C08 · Repetir la confirmación ----------------------------------------------------------------


def test_c08_repetir_la_confirmacion(mundo: Mundo) -> None:
    """Escenario: Repetir la confirmación"""
    cuerpo = subir(mundo)
    confirmacion_creada(confirmar(mundo, cuerpo["importacion_id"]))
    antes = conteos(mundo)
    conflicto(confirmar(mundo, cuerpo["importacion_id"]), "estado_migracion")
    assert conteos(mundo) == antes, "la segunda confirmación no escribe nada"
    assert len(cargas(mundo)) == 1, "existe una sola carga"
    assert auditorias(mundo, ACCION) == 1


# --- C09 · Con la migración cerrada, el importador no acepta nada ---------------------------------


def test_c09_subir_despues_de_confirmar(mundo: Mundo) -> None:
    """Escenario: Subir después de confirmar"""
    cuerpo = subir(mundo)
    confirmacion_creada(confirmar(mundo, cuerpo["importacion_id"]))
    control = control_base()
    control[1][1] = "104000.00"
    antes = conteos(mundo)
    conflicto(importar(mundo, archivo(control=control)), "estado_migracion")
    assert conteos(mundo) == antes


def test_c09_aceptar_despues_de_confirmar(mundo: Mundo) -> None:
    cuerpo = _con_diferencias(mundo)
    aceptacion_creada(aceptar(mundo, cuerpo["importacion_id"]))
    confirmacion_creada(confirmar(mundo, cuerpo["importacion_id"]))
    antes = conteos(mundo)
    conflicto(aceptar(mundo, cuerpo["importacion_id"]), "estado_migracion")
    assert conteos(mundo) == antes


@pytest.mark.parametrize("cerrada", ["confirmada", "sin_saldos_previos"])
def test_c09_confirmar_con_la_migracion_cerrada(mundo: Mundo, cerrada: str) -> None:
    cuerpo = subir(mundo)
    mundo.ejecutar(
        "UPDATE complejo SET estado_migracion = %s WHERE id = %s", (cerrada, mundo.edificio)
    )
    antes = conteos(mundo)
    conflicto(confirmar(mundo, cuerpo["importacion_id"]), "estado_migracion")
    assert conteos(mundo) == antes
    assert estado_de(mundo, cuerpo["importacion_id"]) == "borrador"


def test_c09_subir_con_la_migracion_sin_saldos_previos(mundo: Mundo) -> None:
    mundo.ejecutar(
        "UPDATE complejo SET estado_migracion = 'sin_saldos_previos' WHERE id = %s",
        (mundo.edificio,),
    )
    antes = conteos(mundo)
    conflicto(importar(mundo, archivo()), "estado_migracion")
    assert conteos(mundo) == antes


# --- C10 · Permisos y tenant ----------------------------------------------------------------------


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
def test_c10_sin_permiso_403(mundo: Mundo, rol: str) -> None:
    """Escenario: Administrador del edificio"""
    cuerpo = subir(mundo)
    mundo.como(rol)
    antes = conteos(mundo)
    respuesta = confirmar(mundo, cuerpo["importacion_id"])
    assert respuesta.status_code == 403, f"{rol}: se esperaba 403, llegó {respuesta.status_code}"
    assert ACCION in respuesta.text, f"el 403 nombra el permiso que falta: {respuesta.text[:300]}"
    assert conteos(mundo) == antes


def test_c10_administrador_de_otro_edificio_no_lo_ve(mundo: Mundo) -> None:
    cuerpo = subir(mundo)
    mundo.como("admin_de_otro_edificio")
    antes = conteos(mundo)
    respuesta = confirmar(mundo, cuerpo["importacion_id"])
    assert respuesta.status_code == 404, f"se esperaba 404 (D7), llegó {respuesta.status_code}"
    assert respuesta.json() == {"detail": "no encontrado"}, respuesta.text[:200]
    assert conteos(mundo) == antes


def test_c10_otra_administracion(mundo: Mundo) -> None:
    """Escenario: Otra administración"""
    cuerpo = subir(mundo)
    mundo.como("administracion_b")
    antes = conteos(mundo)
    respuesta = confirmar(mundo, cuerpo["importacion_id"])
    assert respuesta.status_code == 404, f"se esperaba 404, llegó {respuesta.status_code}"
    assert respuesta.json() == {"detail": "no encontrado"}, respuesta.text[:200]
    assert conteos(mundo) == antes
    respuesta_b = confirmar(mundo, cuerpo["importacion_id"], complejo=mundo.edificio_b)
    assert respuesta_b.status_code != 201, "B no confirma la importación de A desde su edificio"
    assert conteos(mundo) == antes


def test_c10_sin_sesion_401(mundo: Mundo) -> None:
    cuerpo = subir(mundo)
    mundo.sin_sesion()
    respuesta = confirmar(mundo, cuerpo["importacion_id"])
    assert respuesta.status_code == 401, f"se esperaba 401, llegó {respuesta.status_code}"


# --- C11 · Concurrencia contra PostgreSQL real ----------------------------------------------------


def test_c11_dos_confirmaciones_simultaneas(mundo: Mundo) -> None:
    cuerpo = subir(mundo)
    resultados = en_paralelo(
        lambda: confirmar(mundo, cuerpo["importacion_id"]),
        lambda: confirmar(mundo, cuerpo["importacion_id"]),
    )
    for r in resultados:
        assert not isinstance(r, BaseException), f"una confirmación explotó: {r!r}"
    codigos = sorted(r.status_code for r in resultados)
    assert codigos == [201, 409], f"una confirma y la otra da conflicto: {codigos}"
    perdedora = next(r for r in resultados if r.status_code == 409)
    assert perdedora.json().get("campo") == "estado_migracion", perdedora.text[:200]
    assert len(cargas(mundo)) == 1, "una sola carga en el libro"
    assert auditorias(mundo, ACCION) == 1
    assert estado_del_edificio(mundo) == "confirmada"


def test_c11_confirmar_contra_sin_saldos_previos(mundo: Mundo) -> None:
    """Escenario: Confirmar contra sin saldos previos"""
    from ._h009 import sin_saldos_previos

    cuerpo = subir(mundo)
    resultados = en_paralelo(
        lambda: confirmar(mundo, cuerpo["importacion_id"]),
        lambda: sin_saldos_previos(mundo),
    )
    for r in resultados:
        assert not isinstance(r, BaseException), f"una de las dos explotó: {r!r}"
    confirmo, sin_saldos = resultados
    ganadores = [r for r in resultados if 200 <= r.status_code < 300]
    perdedores = [r for r in resultados if r.status_code == 409]
    assert len(ganadores) == 1 and len(perdedores) == 1, (
        f"una gana y la otra da conflicto: {confirmo.status_code} / {sin_saldos.status_code}"
    )
    assert perdedores[0].json().get("campo") == "estado_migracion", perdedores[0].text[:200]
    if confirmo.status_code == 201:
        assert estado_del_edificio(mundo) == "confirmada"
        assert len(cargas(mundo)) == 1
        assert estado_de(mundo, cuerpo["importacion_id"]) == "confirmada"
    else:
        assert estado_del_edificio(mundo) == "sin_saldos_previos"
        assert cargas(mundo) == [], "con sin saldos previos no hay carga en el libro"
        assert estado_de(mundo, cuerpo["importacion_id"]) == "borrador"
        assert auditorias(mundo, ACCION) == 0


# --- C12 · Si la carga del 4c rechaza, no queda nada escrito --------------------------------------


def test_c12_si_la_carga_del_4c_rechaza_no_queda_nada(mundo: Mundo) -> None:
    """La carga del 4c vuelve a validar la fecha de migración (E15): una fecha posterior a hoy se
    rechaza y el edificio, la importación y la auditoría quedan como estaban."""
    cuerpo = subir(mundo)
    mundo.ejecutar(
        "UPDATE importacion SET fecha_de_migracion = current_date + 1 WHERE id = %s",
        (cuerpo["importacion_id"],),
    )
    antes = conteos(mundo)
    respuesta = confirmar(mundo, cuerpo["importacion_id"])
    assert respuesta.status_code == 422, (
        f"se esperaba 422 (la carga del 4c rechaza la fecha), llegó {respuesta.status_code}: "
        f"{respuesta.text[:300]}"
    )
    assert "fecha_de_migracion" in respuesta.text, respuesta.text[:300]
    assert conteos(mundo) == antes, "un rechazo de la carga no deja nada escrito"
    assert estado_del_edificio(mundo) == "pendiente"
    assert estado_de(mundo, cuerpo["importacion_id"]) == "borrador"
    assert auditorias(mundo, ACCION) == 0
    assert cargas(mundo) == []
