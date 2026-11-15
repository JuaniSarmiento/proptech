"""H-011 · permisos (C11), sin efectos (N01) y el índice de DBA-2 (C13)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from ._h011 import (
    OCT,
    Mundo,
    cargar_base,
    conteo_de_todo,
    emitir_libro,
    gasto,
    pedir,
    preliquidacion,
)

PERMISO = "cargar_gastos_y_preparar_liquidacion"


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal", "admin_del_edificio"])
def test_c11_pueden_preliquidar(mundo: Mundo, rol: str) -> None:
    cargar_base(mundo)
    mundo.como(rol)
    r = pedir(mundo)
    assert r.status_code == 200, f"{rol}: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    assert r.json()["totales"]["total"] == "191500.00"


@pytest.mark.parametrize("rol", ["contador", "consejo", "auxiliar"])
def test_c11_no_pueden_preliquidar(mundo: Mundo, rol: str) -> None:
    cargar_base(mundo)
    mundo.como(rol)
    r = pedir(mundo)
    assert r.status_code == 403, f"{rol}: se esperaba 403, llegó {r.status_code}: {r.text[:300]}"
    detalle = r.json().get("detail")
    assert isinstance(detalle, dict) and detalle.get("permiso_faltante") == PERMISO, (
        f"{rol}: el 403 tiene que nombrar `{PERMISO}`: {r.json()}"
    )


@pytest.mark.parametrize("quien", ["admin_de_otro_edificio", "administracion_b"])
def test_c11_fuera_de_alcance_es_404(mundo: Mundo, quien: str) -> None:
    cargar_base(mundo)
    mundo.como(quien)
    r = pedir(mundo)
    assert r.status_code == 404, f"{quien}: se esperaba 404, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == {"detail": "no encontrado"}


def test_c11_edificio_inexistente_es_404(mundo: Mundo) -> None:
    r = pedir(mundo, complejo=uuid4())
    assert r.status_code == 404, f"se esperaba 404, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == {"detail": "no encontrado"}, f"el 404 del contrato, no el de una ruta inexistente: {r.json()}"


def test_c11_sin_sesion_es_401(mundo: Mundo) -> None:
    cargar_base(mundo)
    mundo.sin_sesion()
    r = pedir(mundo)
    assert r.status_code == 401, f"se esperaba 401, llegó {r.status_code}: {r.text[:300]}"


def test_n01_no_escribe_nada(mundo: Mundo) -> None:
    """Escenario: Nada escrito"""
    cargar_base(mundo)
    emitir_libro(mundo, OCT, {"1A": ("100000.00", "0.00", "0.00")}, OCT.replace(day=10))
    antes = conteo_de_todo(mundo)
    assert preliquidacion(mundo)["huella"]
    despues = conteo_de_todo(mundo)
    cambiadas = sorted(t for t in antes if antes[t] != despues.get(t))
    nuevas = sorted(set(despues) - set(antes))
    assert not cambiadas and not nuevas, (
        f"la preliquidación escribió en: {cambiadas or nuevas}"
    )


def test_n01_no_escribe_aunque_falle(mundo: Mundo) -> None:
    cargar_base(mundo)
    emitir_libro(mundo, OCT, {"1A": ("100.00", "0.00", "0.00")})
    gasto(mundo, "100.00", periodo=OCT)
    antes = conteo_de_todo(mundo)
    assert pedir(mundo, OCT).status_code == 409
    assert conteo_de_todo(mundo) == antes, "un rechazo de la preliquidación escribió algo"


def test_c13_indice_de_grupo_unidad_por_edificio(mundo: Mundo) -> None:
    definiciones = [f[0] for f in mundo.filas(
        "SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'grupo_unidad'"
    )]
    assert any(
        "(administracion_id, complejo_id" in d.replace('"', "") for d in definiciones
    ), f"falta el índice de DBA-2 sobre grupo_unidad (administracion_id, complejo_id, ...): {definiciones}"
