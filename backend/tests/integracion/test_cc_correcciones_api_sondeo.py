"""RF: la ruta de correcciones bajo sondeo, replay y carrera por la API."""

import threading
import time
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from ._api_edificios import ApiEdificio
from .test_cc_auditoria_api import cuerpo, libro_api  # noqa: F401

pytestmark = pytest.mark.integracion
L = tuple[ApiEdificio, dict[str, UUID]]


def _conteos(api: ApiEdificio) -> list[Any]:
    return api.filas(
        "SELECT (SELECT count(*) FROM movimiento), (SELECT count(*) FROM imputacion), "
        "(SELECT count(*) FROM auditoria WHERE accion='corregir_movimiento')"
    )


def test_rf_ae_con_operacion_usada_recibe_403_no_409(libro_api: L) -> None:  # noqa: F811
    api, ids = libro_api
    datos = cuerpo(ids)
    assert api.cliente.post(api.ruta("/correcciones"), json=datos).status_code == 201
    api.como("editar")
    for variante in (datos, {**datos, "motivo": "otro"}):
        r = api.cliente.post(api.ruta("/correcciones"), json=variante)
        assert r.status_code == 403, r.text
    # Mismo AE en un edificio que no alcanza: 404, nunca 409/201.
    r = api.cliente.post(f"/api/complejos/{api.otro}/correcciones", json=datos)
    assert (r.status_code, r.json()) == (404, {"detail": "no encontrado"})
    r = api.cliente.post(f"/api/complejos/{uuid4()}/correcciones", json=datos)
    assert (r.status_code, r.json()) == (404, {"detail": "no encontrado"})


def test_rf_replay_en_otro_edificio_misma_administracion(libro_api: L) -> None:  # noqa: F811
    api, ids = libro_api
    datos = cuerpo(ids)
    primera = api.cliente.post(api.ruta("/correcciones"), json=datos)
    assert primera.status_code == 201
    antes = _conteos(api)
    r = api.cliente.post(f"/api/complejos/{api.otro}/correcciones", json=datos)
    assert (r.status_code, r.json()) == (409, {"detail": "conflicto", "campo": "operacion_id"})
    assert str(primera.json()["movimiento_id"]) not in r.text
    assert _conteos(api) == antes


@pytest.mark.parametrize("forma", ["contra_asiento", "credito"])
def test_rf_replay_tras_anular_y_tras_contra_asentar(libro_api: L, forma: str) -> None:  # noqa: F811
    api, ids = libro_api
    datos = cuerpo(ids, forma)
    primera = api.cliente.post(api.ruta("/correcciones"), json=datos)
    assert primera.status_code == 201
    corr = primera.json()["movimiento_id"]
    # Deshacer la corrección con otra corrección (contra-asiento del crédito, o del contra-asiento
    # sólo si es crédito: el débito de corrección no se contra-asienta).
    if forma == "credito":
        deshacer = {
            "forma": "contra_asiento",
            "operacion_id": str(uuid4()),
            "motivo": "deshacer",
            "movimiento_id": corr,
        }
        assert api.cliente.post(api.ruta("/correcciones"), json=deshacer).status_code == 201
    antes = _conteos(api)
    variantes = [
        datos,
        {**datos, "operacion_id": datos["operacion_id"].upper()},
        {**datos, "operacion_id": datos["operacion_id"].replace("-", "")},
        {**datos, "operacion_id": "urn:uuid:" + datos["operacion_id"]},
        {**datos, "motivo": "  " + datos["motivo"] + "   "},
    ]
    for v in variantes:
        r = api.cliente.post(api.ruta("/correcciones"), json=v)
        assert (r.status_code, r.json()) == (201, {"movimiento_id": corr}), (v, r.text)
    assert _conteos(api) == antes


def test_rf_importe_formas_raras(libro_api: L) -> None:  # noqa: F811
    api, ids = libro_api
    for importe, esperado in (
        (10, 422),
        ("1e1", 422),
        ("10", None),
        (" 10.00", 422),
        ("+10.00", 422),
        ("9999999999999.99", 422),
        (True, 422),
        (None, 422),
        ("NaN", 422),
        ("Infinity", 422),
        ("\uff11\uff10.\uff10\uff10", 422),  # dígitos de ancho completo
    ):
        datos = {**cuerpo(ids, "credito"), "importe": importe}
        r = api.cliente.post(api.ruta("/correcciones"), json=datos)
        if esperado is None:
            assert r.status_code in (201, 422), (importe, r.status_code, r.text)
        else:
            assert r.status_code == esperado, (importe, r.status_code, r.text)
        assert r.status_code != 500


def test_rf_motivo_raro_no_es_500(libro_api: L) -> None:  # noqa: F811
    api, ids = libro_api
    for motivo in ("a\u0000b", "\ud800x", "x‮y", "​", "x" * 100000, 5, None, ["x"]):
        import json

        r = api.cliente.post(
            api.ruta("/correcciones"),
            content=json.dumps({**cuerpo(ids), "motivo": motivo}),
            headers={"content-type": "application/json"},
        )
        assert r.status_code == 422, (repr(motivo)[:20], r.status_code, r.text[:300])


def _esperar_bloqueados(api: ApiEdificio, n: int) -> None:
    fin = time.monotonic() + 20
    while time.monotonic() < fin:
        with api.base.conectar_app() as c:
            fila_bloqueados = c.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type='Lock' "
                "AND datname=current_database()"
            ).fetchone()
        if fila_bloqueados is not None and fila_bloqueados[0] >= n:
            return
        time.sleep(0.05)
    raise AssertionError(f"no se bloquearon {n}")


@pytest.mark.parametrize("forma", ["contra_asiento", "credito"])
@pytest.mark.parametrize("iguales", [True, False])
def test_rf_carrera_por_api(libro_api: L, forma: str, iguales: bool) -> None:  # noqa: F811
    api, ids = libro_api
    datos = cuerpo(ids, forma)
    otro = dict(datos) if iguales else {**datos, "motivo": "Otro motivo de carrera"}
    cuenta = api.filas("SELECT cuenta_id FROM movimiento WHERE id=%s", (ids["pago_propio"],))[0][0]
    antes = _conteos(api)
    resultados: dict[int, Any] = {}

    def postear(i: int, cuerpo_: dict[str, Any]) -> None:
        cliente = TestClient(api.app, raise_server_exceptions=False)
        try:
            r = cliente.post(api.ruta("/correcciones"), json=cuerpo_)
            resultados[i] = (r.status_code, r.json())
        finally:
            cliente.close()

    with api.base.conectar_app() as c, c.transaction():
        c.execute("SELECT set_config('app.administracion_id', %s, true)", (str(api.admin),))
        c.execute("SELECT 1 FROM candado_de_cuenta WHERE cuenta_id=%s FOR UPDATE", (cuenta,))
        hilos = [
            threading.Thread(target=postear, args=(0, datos)),
            threading.Thread(target=postear, args=(1, otro)),
        ]
        for h in hilos:
            h.start()
        _esperar_bloqueados(api, 2)
    for h in hilos:
        h.join(30)
    codigos = sorted(r[0] for r in resultados.values())
    despues = _conteos(api)
    if iguales:
        assert codigos == [201, 201], resultados
        assert resultados[0] == resultados[1]
    else:
        assert codigos == [201, 409], resultados
        conflicto = next(r for r in resultados.values() if r[0] == 409)
        assert conflicto[1] == {"detail": "conflicto", "campo": "operacion_id"}
    # Una sola corrección y una sola auditoría.
    assert despues[0][0] - antes[0][0] == 1
    assert despues[0][2] - antes[0][2] == 1
    # El perdedor no dejó imputaciones propias: replay serial da el mismo conteo.
    ganador = datos if resultados[0][0] == 201 else otro
    r = api.cliente.post(api.ruta("/correcciones"), json=ganador)
    assert r.status_code == 201
    assert _conteos(api) == despues


@pytest.mark.parametrize("importe", ["10.01", "9.99", "1000.00"])
def test_rf_replay_credito_con_otro_importe_es_409(libro_api: L, importe: str) -> None:  # noqa: F811
    api, ids = libro_api
    datos = cuerpo(ids, "credito")
    assert api.cliente.post(api.ruta("/correcciones"), json=datos).status_code == 201
    antes = _conteos(api)
    r = api.cliente.post(api.ruta("/correcciones"), json={**datos, "importe": importe})
    assert (r.status_code, r.json()) == (409, {"detail": "conflicto", "campo": "operacion_id"})
    assert _conteos(api) == antes
    # Mismo valor con otra escritura: es el mismo pedido.
    r = api.cliente.post(api.ruta("/correcciones"), json={**datos, "importe": "10"})
    assert r.status_code == 201, r.text
