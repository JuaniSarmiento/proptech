"""H-007 · C16 (permisos y tenant) y C17 (concurrencia).

Orden de chequeo de la API (D7 del 2a): primero el alcance (404, "no existe" y "no alcanza" dan lo
mismo), después el permiso (403). Por eso un administrador de **otro** edificio recibe 404,
igual que
otra administración: no ve el edificio.
"""

from __future__ import annotations

import pytest

from ._h007 import (
    Mundo,
    aceptada,
    conteos,
    en_paralelo,
    importar,
    libro,
    padron,
    unidades,
)

pytestmark = pytest.mark.integracion


def _sin_padron() -> bytes:
    """Un archivo válido para el edificio con padrón (sin hoja Unidades): sólo decide el permiso."""
    return libro({"Notas": [["Texto"], ["sin padrón"]]})


# --- C16 · Permisos -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rol", ["contador", "auxiliar", "consejo", "vecino_propietario", "vecino_inquilino"]
)
def test_c16_sin_permiso_403(mundo: Mundo, rol: str) -> None:
    """Escenario: Consejo o vecino"""
    mundo.como(rol)
    antes = conteos(mundo)
    respuesta = importar(mundo, mundo.con_padron, _sin_padron())
    assert respuesta.status_code == 403, f"{rol}: se esperaba 403, llegó {respuesta.status_code}"
    assert "importar_padron_y_saldos" in respuesta.text, (
        f"el 403 nombra el permiso que falta: {respuesta.text[:300]}"
    )
    assert conteos(mundo) == antes


def test_c16_administrador_de_otro_edificio_no_lo_ve(mundo: Mundo) -> None:
    mundo.como("admin_de_otro_edificio")
    antes = conteos(mundo)
    respuesta = importar(mundo, mundo.con_padron, _sin_padron())
    assert respuesta.status_code == 404, f"se esperaba 404 (D7), llegó {respuesta.status_code}"
    assert respuesta.json() == {"detail": "no encontrado"}, (
        f"el 404 es el del edificio, no el de una ruta inexistente: {respuesta.text[:200]}"
    )
    assert conteos(mundo) == antes


def test_c16_otra_administracion(mundo: Mundo) -> None:
    """Escenario: Edificio de otra administración"""
    mundo.como("administracion_b")
    antes = conteos(mundo)
    respuesta = importar(mundo, mundo.torre, padron())
    assert respuesta.status_code == 404, f"se esperaba 404, llegó {respuesta.status_code}"
    assert respuesta.json() == {"detail": "no encontrado"}, (
        f"el 404 es el del edificio, no el de una ruta inexistente: {respuesta.text[:200]}"
    )
    assert conteos(mundo) == antes
    assert unidades(mundo, mundo.torre) == {}


def test_c16_sin_sesion_401(mundo: Mundo) -> None:
    mundo.sin_sesion()
    antes = conteos(mundo)
    respuesta = importar(mundo, mundo.torre, padron())
    assert respuesta.status_code == 401, f"se esperaba 401, llegó {respuesta.status_code}"
    assert conteos(mundo) == antes


@pytest.mark.parametrize("rol", ["admin_del_edificio", "admin_principal", "super_admin"])
def test_c16_los_que_pueden_importar(mundo: Mundo, rol: str) -> None:
    """Control de E6: super admin, administrador principal y administrador del edificio importan."""
    mundo.como(rol)
    cuerpo = aceptada(importar(mundo, mundo.con_padron, _sin_padron()))
    assert cuerpo["unidades_creadas"] == 0


# --- C17 · Concurrencia ---------------------------------------------------------------------------


def test_c17_dos_subidas_simultaneas_del_padron(mundo: Mundo) -> None:
    contenido = padron()
    resultados = en_paralelo(
        lambda: importar(mundo, mundo.torre, contenido),
        lambda: importar(mundo, mundo.torre, contenido),
    )
    for r in resultados:
        assert not isinstance(r, BaseException), f"una subida explotó: {r!r}"
    codigos = sorted(r.status_code for r in resultados)
    assert codigos == [201, 409], f"una crea el padrón y la otra da conflicto: {codigos}"
    assert len(unidades(mundo, mundo.torre)) == 12, "nunca quedan 24 unidades"
    assert mundo.uno("SELECT count(*) FROM importacion WHERE complejo_id = %s", (mundo.torre,)) == 1
