"""Tarea 2.5 de `importacion-desde-excel`: las dos rutas de la comparación y de aceptar diferencias
por HTTP, con identidad inyectada y RLS real (D7, D11, E6, E8). Se sube el borrador por la ruta
real de H-007 (`Saldos` y `Control` sobre el padrón de "Edificio API": `1A` y `1B`) y se lee y se
acepta por las rutas nuevas. Datos inventados.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from ._api_edificios import ApiEdificio
from ._importacion import libro
from ._saldos_importados import CONTROL, SALDOS

pytestmark = pytest.mark.integracion

#: `1A` debe 10.000 más que su control y `1B` 10.000 menos: los totales coinciden (E13 no aplica:
#: el edificio de prueba no tiene una versión de configuración en `mes_entero` a esa fecha).
_SALDOS = [
    ["1A", None, None, None, "60000.00", None],
    ["1B", None, None, None, "40000.00", None],
]
_CONTROL = [["1A", "50000.00"], ["1B", "50000.00"]]
_CONTROL_SIN_DIFERENCIAS = [["1A", "60000.00"], ["1B", "40000.00"]]


def _archivo(control: list[list[str]]) -> bytes:
    return libro({"Saldos": [SALDOS, *_SALDOS], "Control": [CONTROL, *control]})


def _subir(api: ApiEdificio, control: list[list[str]] = _CONTROL, edificio: UUID | None = None):
    return api.cliente.post(
        f"/api/complejos/{edificio or api.edificio}/importaciones",
        data={"fecha_de_migracion": "2026-10-15"},
        files={"archivo": ("saldos.xlsx", _archivo(control), "application/octet-stream")},
    )


def _comparacion(api: ApiEdificio, edificio: UUID | None = None):
    return api.cliente.get(f"/api/complejos/{edificio or api.edificio}/importaciones/comparacion")


def _aceptar(api: ApiEdificio, importacion_id: Any, edificio: UUID | None = None):
    return api.cliente.post(
        f"/api/complejos/{edificio or api.edificio}/importaciones/aceptacion-de-diferencias",
        json={"importacion_id": str(importacion_id)},
    )


def _con_borrador(api: ApiEdificio, control: list[list[str]] = _CONTROL) -> str:
    subida = _subir(api, control)
    assert subida.status_code == 201, subida.text
    return str(subida.json()["importacion_id"])


# --- GET /comparacion --------------------------------------------------------------------------


def test_la_comparacion_da_las_unidades_los_totales_y_lo_que_falta_aceptar(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    importacion = _con_borrador(api)
    respuesta = _comparacion(api)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    unidades = {u["unidad"]: u for u in cuerpo["unidades"]}
    assert {u: (v["borrador"], v["control"], v["diferencia"]) for u, v in unidades.items()} == {
        "1A": ("60000.00", "50000.00", "10000.00"),
        "1B": ("40000.00", "50000.00", "-10000.00"),
    }
    assert all(UUID(v["unidad_id"]) and v["aviso"] is None for v in unidades.values())
    assert cuerpo["importacion_id"] == importacion
    assert (cuerpo["total_borrador"], cuerpo["total_control"]) == ("100000.00", "100000.00")
    assert cuerpo["unidades_con_diferencia"] == 2
    assert cuerpo["requiere_aceptacion"] is True
    assert cuerpo["aceptacion"] is None


def test_la_comparacion_sin_borrador_es_404(api_edificio: ApiEdificio) -> None:
    respuesta = _comparacion(api_edificio)
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "no encontrado"}


def test_la_comparacion_de_otro_edificio_o_de_otra_administracion_es_404(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    _con_borrador(api)
    api.como("editar")
    for edificio in (api.otro, api.ajeno, uuid4()):
        respuesta = _comparacion(api, edificio)
        assert respuesta.status_code == 404, edificio
        assert respuesta.json() == {"detail": "no encontrado"}


@pytest.mark.parametrize("rol", ["ver", "consejo", "contador", "vecino"])
def test_sin_permiso_de_importar_no_se_ve_la_comparacion(
    api_edificio: ApiEdificio, rol: str
) -> None:
    api = api_edificio
    _con_borrador(api)
    api.como(rol)
    respuesta = _comparacion(api)
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["permiso_faltante"] == "importar_padron_y_saldos"


def test_el_administrador_del_edificio_ve_la_comparacion(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    _con_borrador(api)
    api.como("editar")
    assert _comparacion(api).status_code == 200


# --- POST /aceptacion-de-diferencias -----------------------------------------------------------


def test_aceptar_da_201_con_la_lista_y_deja_una_fila_y_una_auditoria(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    importacion = _con_borrador(api)
    antes = api.filas(
        "SELECT count(*) FROM auditoria WHERE accion = 'aceptar_diferencias_de_saldos'"
    )
    respuesta = _aceptar(api, importacion)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"aceptacion_id", "diferencias", "aceptada_por", "aceptada_en"}
    assert sorted(
        (d["unidad"], d["borrador"], d["control"], d["diferencia"]) for d in cuerpo["diferencias"]
    ) == [
        ("1A", "60000.00", "50000.00", "10000.00"),
        ("1B", "40000.00", "50000.00", "-10000.00"),
    ]
    assert cuerpo["aceptada_por"] == str(api.personas["super_admin"])
    cuando = datetime.fromisoformat(cuerpo["aceptada_en"])
    assert cuando.tzinfo is not None
    assert api.filas("SELECT id, importacion_id, aceptada_por FROM aceptacion_de_diferencias") == [
        (UUID(cuerpo["aceptacion_id"]), UUID(importacion), api.personas["super_admin"])
    ]
    despues = api.filas(
        "SELECT count(*) FROM auditoria WHERE accion = 'aceptar_diferencias_de_saldos'"
    )
    assert despues[0][0] - antes[0][0] == 1


def test_despues_de_aceptar_la_comparacion_muestra_la_aceptacion_y_ya_no_pide_aceptar(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    importacion = _con_borrador(api)
    asentada = _aceptar(api, importacion)
    assert asentada.status_code == 201, asentada.text
    aceptada = asentada.json()
    leida = _comparacion(api)
    assert leida.status_code == 200, leida.text
    cuerpo = leida.json()
    assert cuerpo["requiere_aceptacion"] is False
    assert cuerpo["aceptacion"] == aceptada


def test_aceptar_sin_el_permiso_de_aceptar_es_403_y_no_escribe(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    importacion = _con_borrador(api)
    api.como("editar")  # administrador sólo de este edificio: importa, no acepta (E6)
    respuesta = _aceptar(api, importacion)
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["permiso_faltante"] == "aceptar_diferencias_de_saldos"
    assert api.filas("SELECT count(*) FROM aceptacion_de_diferencias") == [(0,)]


def test_aceptar_en_otro_edificio_o_administracion_es_404_antes_que_403(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    importacion = _con_borrador(api)
    api.como("editar")
    for edificio in (api.otro, api.ajeno, uuid4()):
        respuesta = _aceptar(api, importacion, edificio)
        assert respuesta.status_code == 404, edificio
        assert respuesta.json() == {"detail": "no encontrado"}


def test_aceptar_dos_veces_es_409_aceptacion(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    importacion = _con_borrador(api)
    assert _aceptar(api, importacion).status_code == 201
    segunda = _aceptar(api, importacion)
    assert segunda.status_code == 409
    assert segunda.json() == {"detail": "conflicto", "campo": "aceptacion"}
    assert api.filas("SELECT count(*) FROM aceptacion_de_diferencias") == [(1,)]


def test_aceptar_un_borrador_sin_diferencias_es_409_diferencias(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    importacion = _con_borrador(api, _CONTROL_SIN_DIFERENCIAS)
    respuesta = _aceptar(api, importacion)
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": "conflicto", "campo": "diferencias"}
    assert api.filas("SELECT count(*) FROM aceptacion_de_diferencias") == [(0,)]


def test_aceptar_una_importacion_que_no_es_el_borrador_vigente_es_409_importacion_id(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    _con_borrador(api)
    respuesta = _aceptar(api, uuid4())
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": "conflicto", "campo": "importacion_id"}


@pytest.mark.parametrize("cuerpo", [{}, {"importacion_id": "no-es-un-uuid"}, {"importacion_id": 7}])
def test_aceptar_con_un_cuerpo_invalido_es_422_sin_devolver_el_valor(
    api_edificio: ApiEdificio, cuerpo: dict[str, Any]
) -> None:
    api = api_edificio
    respuesta = api.cliente.post(
        f"/api/complejos/{api.edificio}/importaciones/aceptacion-de-diferencias", json=cuerpo
    )
    assert respuesta.status_code == 422
    assert "no-es-un-uuid" not in respuesta.text
    assert all("input" not in e for e in respuesta.json()["detail"])


def test_aceptar_con_un_campo_de_mas_es_422_nombrandolo(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    importacion = _con_borrador(api)
    respuesta = api.cliente.post(
        f"/api/complejos/{api.edificio}/importaciones/aceptacion-de-diferencias",
        json={
            "importacion_id": importacion,
            "aceptada_por": str(uuid4()),
            "fecha": str(date.today()),
        },
    )
    assert respuesta.status_code == 422
    assert ["body", "aceptada_por"] in [e["loc"] for e in respuesta.json()["detail"]]
    assert api.filas("SELECT count(*) FROM aceptacion_de_diferencias") == [(0,)]
