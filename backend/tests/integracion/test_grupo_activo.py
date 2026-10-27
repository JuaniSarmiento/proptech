"""D7 (tarea 4.5, y la mitad API de 4.2): desactivar/reactivar un grupo
parcial; "Generales" lo rechaza; sin ruta de borrado; un grupo desactivado
no reclama unidades en la puesta a punto."""

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


def _grupo_parcial(api: ApiEdificio) -> str:
    r = api.cliente.post(
        api.ruta("/grupos"),
        json={"nombre": "Pileta", "metodo": "coeficiente"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def test_desactivar_un_grupo_parcial(api_edificio: ApiEdificio) -> None:
    """Escenario "Desactivar un grupo parcial"."""
    api = api_edificio
    api.como("super_admin")
    grupo_id = _grupo_parcial(api)
    r = api.cliente.patch(f"/api/grupos/{grupo_id}", json={"activo": False})
    assert r.status_code == 200, r.text
    disponibles = api.cliente.get(api.ruta("/grupos?solo_activos=true")).json()
    assert grupo_id not in [g["id"] for g in disponibles]
    todos = api.cliente.get(api.ruta("/grupos")).json()
    grupo = next(g for g in todos if g["id"] == grupo_id)
    assert grupo["activo"] is False


def test_reactivar(api_edificio: ApiEdificio) -> None:
    """Escenario "Reactivar"."""
    api = api_edificio
    api.como("super_admin")
    grupo_id = _grupo_parcial(api)
    api.cliente.patch(f"/api/grupos/{grupo_id}", json={"activo": False})
    r = api.cliente.patch(f"/api/grupos/{grupo_id}", json={"activo": True})
    assert r.status_code == 200, r.text
    disponibles = api.cliente.get(api.ruta("/grupos?solo_activos=true")).json()
    assert grupo_id in [g["id"] for g in disponibles]


def test_borrar_no_tiene_ruta(api_edificio: ApiEdificio) -> None:
    """Escenario "Borrar": no existe ruta que lo permita."""
    api = api_edificio
    api.como("super_admin")
    grupo_id = _grupo_parcial(api)
    r = api.cliente.delete(f"/api/grupos/{grupo_id}")
    assert r.status_code == 405
    assert api.cliente.get(api.ruta("/grupos")).json()


def test_desactivar_generales_da_422(api_edificio: ApiEdificio) -> None:
    """Escenario "Desactivar Generales" (D7, tarea 4.2, mitad API)."""
    api = api_edificio
    api.como("super_admin")
    generales = next(g for g in api.cliente.get(api.ruta("/grupos")).json() if g["es_generales"])
    r = api.cliente.patch(f"/api/grupos/{generales['id']}", json={"activo": False})
    assert r.status_code == 422
    assert (
        next(g for g in api.cliente.get(api.ruta("/grupos")).json() if g["es_generales"])["activo"]
        is True
    )


def test_grupo_desactivado_sin_unidades_no_bloquea_la_puesta_a_punto(
    api_edificio: ApiEdificio,
) -> None:
    """Escenario "Un grupo desactivado no reclama unidades"."""
    api = api_edificio
    api.como("super_admin")
    grupo_id = _grupo_parcial(api)
    resumen_antes = api.cliente.get(api.ruta("/resumen")).json()
    assert resumen_antes["pasos"]["grupos"] == "falta"
    api.cliente.patch(f"/api/grupos/{grupo_id}", json={"activo": False})
    resumen_despues = api.cliente.get(api.ruta("/resumen")).json()
    assert resumen_despues["pasos"]["grupos"] == "hecho"


def _plan(api: ApiEdificio, consulta: str, parametros: tuple[object, ...]) -> str:
    filas = api.filas("EXPLAIN " + consulta, parametros)
    plan = "\n".join(f[0] for f in filas)
    print(plan)
    return plan


def test_explain_de_los_grupos_activos_entra_por_indice(api_edificio: ApiEdificio) -> None:
    """DB-1 (revisión del PR #2): las dos consultas de la tarea 4.5 que
    filtran por `activo` — la de la puesta a punto (`lectura.py`) y la de
    `listar_grupos(solo_activos=True)` (`grupos.py`) — entran por un índice
    único con prefijo `(administracion_id, complejo_id)` (hoy el planner
    elige `uq_grupo_modo`; `uq_grupo_clave` y `uq_grupo_complejo_id` de
    `0006` tienen el mismo prefijo), con la igualdad de RLS como condición
    del índice, y nunca recorren `grupo_de_reparto` entero. Mismo patrón que
    `test_explain_de_la_consulta_de_unidades_fuera_de_rango`."""
    api = api_edificio
    api.como("super_admin")
    _grupo_parcial(api)
    edificio = str(api.edificio)
    consultas: list[tuple[str, tuple[object, ...]]] = [
        (
            "SELECT id, modo_de_coeficientes FROM grupo_de_reparto "
            "WHERE complejo_id=%s AND NOT es_generales AND activo",
            (edificio,),
        ),
        (
            "SELECT * FROM grupo_de_reparto WHERE complejo_id=%s "
            "AND (NOT %s OR activo) ORDER BY es_generales DESC, clave",
            (edificio, True),
        ),
    ]
    for consulta, parametros in consultas:
        plan = _plan(api, consulta, parametros)
        assert "Seq Scan on grupo_de_reparto" not in plan, plan
        assert "Index Scan using uq_grupo_" in plan, plan
        condicion = next(linea for linea in plan.splitlines() if "Index Cond" in linea)
        assert "administracion_id" in condicion and "complejo_id" in condicion, plan
