"""Tarea 4.3 de `importacion-desde-excel`: la ruta del ajuste de saldo inicial por HTTP, con
identidad inyectada y RLS real (D7, D8, D11, E6, E11). El edificio se confirma por las rutas reales
de H-007 y H-009 (`1A` y `1B`, sin diferencias) y se ajusta por la ruta nueva. Datos inventados.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from ._api_edificios import ApiEdificio
from ._importacion import libro
from ._saldos_importados import CONTROL, SALDOS

pytestmark = pytest.mark.integracion

_SALDOS = [["1A", None, None, None, "60000.00", None], ["1B", None, None, None, "40000.00", None]]
_CONTROL = [["1A", "60000.00"], ["1B", "40000.00"]]
MOTIVO = "Faltó la expensa extraordinaria de julio"


def _confirmar(api: ApiEdificio) -> None:
    subida = api.cliente.post(
        f"/api/complejos/{api.edificio}/importaciones",
        data={"fecha_de_migracion": "2026-10-15"},
        files={
            "archivo": (
                "saldos.xlsx",
                libro({"Saldos": [SALDOS, *_SALDOS], "Control": [CONTROL, *_CONTROL]}),
                "application/octet-stream",
            )
        },
    )
    assert subida.status_code == 201, subida.text
    hecha = api.cliente.post(
        f"/api/complejos/{api.edificio}/importaciones/confirmacion",
        json={"importacion_id": subida.json()["importacion_id"]},
    )
    assert hecha.status_code == 201, hecha.text


def _cuerpo(**cambios: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "operacion_id": str(uuid4()),
        "importe": "5000.00",
        "componente": "ordinaria",
        "motivo": MOTIVO,
    }
    base.update(cambios)
    return base


def _ajustar(
    api: ApiEdificio,
    cuerpo: dict[str, Any] | None = None,
    edificio: UUID | None = None,
    unidad: UUID | None = None,
):
    return api.cliente.post(
        f"/api/complejos/{edificio or api.edificio}/unidades/{unidad or api.unidad}"
        "/ajustes-de-saldo-inicial",
        json=_cuerpo() if cuerpo is None else cuerpo,
    )


def _escrito(api: ApiEdificio) -> list[Any]:
    return [
        api.filas(f"SELECT count(*) FROM {t}")  # noqa: S608
        for t in ("ajuste_de_saldo_inicial", "obligacion", "auditoria")
    ]


def test_ajustar_da_201_con_el_ajuste_y_deja_una_fila_y_una_auditoria(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    _confirmar(api)
    cuerpo = _cuerpo()
    respuesta = _ajustar(api, cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    r = respuesta.json()
    assert set(r) == {
        "ajuste_id", "operacion_id", "obligacion_id", "cuenta_id", "unidad_id", "importe",
        "componente", "periodo", "vencimiento", "motivo", "registrado_por", "registrado_en",
    }  # fmt: skip
    assert (r["operacion_id"], r["unidad_id"], r["importe"], r["componente"], r["motivo"]) == (
        cuerpo["operacion_id"], str(api.unidad), "5000.00", "ordinaria", MOTIVO,
    )  # fmt: skip
    assert r["periodo"] == "2026-10-01"
    assert r["registrado_por"] == str(api.personas["super_admin"])
    assert datetime.fromisoformat(r["registrado_en"]).tzinfo is not None
    assert api.filas(
        "SELECT id, obligacion_id FROM ajuste_de_saldo_inicial WHERE operacion_id = %s",
        (UUID(cuerpo["operacion_id"]),),
    ) == [(UUID(r["ajuste_id"]), UUID(r["obligacion_id"]))]
    assert api.filas("SELECT count(*) FROM auditoria WHERE accion = 'ajustar_saldo_inicial'") == [
        (1,)
    ]


def test_el_replay_devuelve_el_mismo_cuerpo_sin_escribir(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    _confirmar(api)
    cuerpo = _cuerpo()
    primera = _ajustar(api, cuerpo)
    antes = _escrito(api)
    segunda = _ajustar(api, cuerpo)
    assert segunda.status_code in (200, 201), segunda.text
    assert segunda.json() == primera.json()
    assert _escrito(api) == antes


def test_la_misma_operacion_con_otros_datos_es_409_operacion(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    _confirmar(api)
    cuerpo = _cuerpo()
    assert _ajustar(api, cuerpo).status_code == 201
    antes = _escrito(api)
    otra = _ajustar(api, {**cuerpo, "importe": "5000.01"})
    assert otra.status_code == 409
    assert otra.json() == {"detail": "conflicto", "campo": "operacion_id"}
    assert _escrito(api) == antes


def test_con_la_migracion_sin_confirmar_es_409_estado(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    antes = _escrito(api)
    respuesta = _ajustar(api)
    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json() == {"detail": "conflicto", "campo": "estado_migracion"}
    assert _escrito(api) == antes


def test_fuera_de_alcance_o_unidad_ajena_es_404_antes_que_403(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    _confirmar(api)
    api.como("editar")
    antes = _escrito(api)
    for edificio, unidad in (
        (api.otro, api.unidad),
        (api.ajeno, api.unidad_ajena),
        (uuid4(), api.unidad),
        (api.edificio, uuid4()),
        (api.edificio, api.unidad_ajena),
    ):
        respuesta = _ajustar(api, edificio=edificio, unidad=unidad)
        assert respuesta.status_code == 404, (edificio, unidad, respuesta.text)
        assert respuesta.json() == {"detail": "no encontrado"}
    assert _escrito(api) == antes


@pytest.mark.parametrize("rol", ["editar", "ver", "consejo", "contador", "vecino"])
def test_sin_el_permiso_de_ajustar_es_403_y_no_escribe(api_edificio: ApiEdificio, rol: str) -> None:
    api = api_edificio
    _confirmar(api)
    api.como(rol)
    antes = _escrito(api)
    respuesta = _ajustar(api)
    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["detail"]["permiso_faltante"] == "ajustar_saldo_inicial"
    assert _escrito(api) == antes


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"motivo": ""}, "motivo"),
        ({"motivo": "   "}, "motivo"),
        ({"motivo": "x" * 501}, "motivo"),
        ({"importe": "0.00"}, "importe"),
        ({"importe": "-5.00"}, "importe"),
        ({"importe": "1.234"}, "importe"),
        ({"importe": "1000000000000.00"}, "importe"),
        ({"importe": "abc"}, "importe"),
        ({"importe": 5000}, "importe"),
        ({"componente": "interes"}, "componente"),
        ({"componente": "otra"}, "componente"),
        ({"operacion_id": "no-es-uuid"}, "operacion_id"),
        ({"extra": "no"}, "extra"),
    ],
)
def test_un_cuerpo_invalido_es_422_con_el_campo_y_no_escribe(
    api_edificio: ApiEdificio, cambios: dict[str, Any], campo: str
) -> None:
    api = api_edificio
    _confirmar(api)
    antes = _escrito(api)
    respuesta = _ajustar(api, _cuerpo(**cambios))
    assert respuesta.status_code == 422, respuesta.text
    assert ["body", campo] in [e["loc"][:2] for e in respuesta.json()["detail"]]
    assert _escrito(api) == antes


def test_un_motivo_de_500_caracteres_entra(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    _confirmar(api)
    assert _ajustar(api, _cuerpo(motivo="x" * 500)).status_code == 201
