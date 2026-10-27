"""RF: la auditoría falla DE VERDAD (FK al vocabulario), no por monkeypatch."""

from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from ._api_edificios import ApiEdificio
from .test_cc_auditoria_api import cuerpo, libro_api  # noqa: F401

pytestmark = pytest.mark.integracion


@pytest.mark.parametrize("forma", ["credito", "contra_asiento"])
def test_rf_auditoria_real_falla_y_nada_queda(
    libro_api: tuple[ApiEdificio, dict[str, UUID]],  # noqa: F811
    capfd: pytest.CaptureFixture[str],
    forma: str,
) -> None:
    api, ids = libro_api
    antes = api.filas(
        "SELECT (SELECT count(*) FROM movimiento), (SELECT count(*) FROM imputacion), "
        "(SELECT count(*) FROM auditoria)"
    )
    with api.base.conectar_migrador() as c:
        c.execute("DELETE FROM accion_de_auditoria WHERE nombre='corregir_movimiento'")
    try:
        cliente = TestClient(api.app, raise_server_exceptions=False)
        datos: dict[str, Any] = cuerpo(ids, forma)
        datos["motivo"] = "MOTIVO_SECRETO"
        r = cliente.post(api.ruta("/correcciones"), json=datos)
        cliente.close()
    finally:
        with api.base.conectar_migrador() as c:
            c.execute("INSERT INTO accion_de_auditoria (nombre) VALUES ('corregir_movimiento')")
    assert r.status_code == 500, r.text
    assert set(r.json()) == {"error", "request_id"}
    assert "MOTIVO_SECRETO" not in r.text and "corregir_movimiento" not in r.text
    salida = capfd.readouterr()
    assert "MOTIVO_SECRETO" not in salida.out + salida.err
    assert "Key (" not in salida.out + salida.err
    # Otra conexión: nada de la corrección quedó.
    assert (
        api.filas(
            "SELECT (SELECT count(*) FROM movimiento), (SELECT count(*) FROM imputacion), "
            "(SELECT count(*) FROM auditoria)"
        )
        == antes
    )
    if forma != "contra_asiento":  # el último parámetro: después nadie borra el vocabulario
        return
    # Y la misma operación, ya con vocabulario, se crea limpia (no quedó nada a medias).
    r2 = api.cliente.post(api.ruta("/correcciones"), json=datos)
    assert r2.status_code == 201, r2.text
    assert api.filas("SELECT count(*) FROM auditoria WHERE accion='corregir_movimiento'") == [(1,)]
