"""Tests unitarios del endpoint GET /api/salud, sin base real (dependency_overrides)."""

import threading

import pytest
from fastapi.testclient import TestClient


def _cliente_con_verificador(verificador: object) -> TestClient:
    from proptech_api.app import crear_app
    from proptech_api.salud import obtener_verificador_de_base

    app = crear_app()
    app.dependency_overrides[obtener_verificador_de_base] = lambda: verificador
    return TestClient(app)


def test_base_ok_responde_200() -> None:
    cliente = _cliente_con_verificador(lambda: True)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "base": "ok"}


def test_base_caida_responde_503() -> None:
    cliente = _cliente_con_verificador(lambda: False)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    assert respuesta.json() == {"estado": "degradado", "base": "sin_conexion"}


def test_excepcion_del_verificador_no_filtra_la_cadena_de_conexion() -> None:
    def verificador_que_explota() -> bool:
        raise RuntimeError("no se pudo conectar a postgresql://usuario:secreto@host/db")

    cliente = _cliente_con_verificador(verificador_que_explota)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    cuerpo_texto = respuesta.text
    assert "secreto" not in cuerpo_texto
    assert "postgresql://" not in cuerpo_texto
    assert respuesta.json() == {"estado": "degradado", "base": "sin_conexion"}


def test_sin_prefijo_responde_404() -> None:
    cliente = _cliente_con_verificador(lambda: True)
    respuesta = cliente.get("/salud")
    assert respuesta.status_code == 404


def test_verificador_real_no_cuelga_contra_host_que_no_responde(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D11: timeout de conexión de 2s. Contra una IP que no responde (no rechaza ni
    acepta: nadie contesta), el verificador real tiene que devolver False en pocos
    segundos, no colgarse con el timeout por defecto del sistema operativo.

    Corre en un hilo aparte con `join(timeout=...)` para que el propio test quede
    acotado aunque el código bajo prueba no tenga el timeout aplicado todavía.
    """
    from proptech_api.salud import _verificador_real

    monkeypatch.setenv("POSTGRES_HOST", "10.255.255.1")  # IP privada sin ruta: no responde
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "x")
    monkeypatch.setenv("POSTGRES_PASSWORD", "x")
    monkeypatch.setenv("POSTGRES_DB", "x")

    resultado: list[bool] = []
    hilo = threading.Thread(target=lambda: resultado.append(_verificador_real()), daemon=True)
    hilo.start()
    hilo.join(timeout=5)

    assert not hilo.is_alive(), (
        "el verificador sigue colgado después de 5s: falta el connect_timeout de 2s (D11)"
    )
    assert resultado == [False]
