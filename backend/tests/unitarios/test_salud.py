"""Tests unitarios del endpoint GET /api/salud, sin base ni cola reales
(dependency_overrides). La cola se agrega en la tarea 4.6 (D4): escenarios de
`entorno-de-ejecucion` Todo funciona; La base no responde; La cola no
responde; La base y la cola no responden. Lecciones: L-007, L-009.
"""

import threading
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient


def _cliente_con_verificadores(
    verificador_base: Callable[[], bool], verificador_cola: Callable[[], bool]
) -> TestClient:
    from proptech_api.app import crear_app
    from proptech_api.salud import obtener_verificador_de_base, obtener_verificador_de_cola

    app = crear_app()
    app.dependency_overrides[obtener_verificador_de_base] = lambda: verificador_base
    app.dependency_overrides[obtener_verificador_de_cola] = lambda: verificador_cola
    return TestClient(app)


def test_todo_funciona_responde_200_con_base_y_cola_ok() -> None:
    cliente = _cliente_con_verificadores(lambda: True, lambda: True)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "base": "ok", "cola": "ok"}


def test_base_caida_responde_503_con_cola_ok() -> None:
    cliente = _cliente_con_verificadores(lambda: False, lambda: True)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    assert respuesta.json() == {"estado": "degradado", "base": "sin_conexion", "cola": "ok"}


def test_cola_caida_responde_503_con_base_ok() -> None:
    cliente = _cliente_con_verificadores(lambda: True, lambda: False)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    assert respuesta.json() == {"estado": "degradado", "base": "ok", "cola": "sin_conexion"}


def test_base_y_cola_caidas_responde_503() -> None:
    cliente = _cliente_con_verificadores(lambda: False, lambda: False)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    assert respuesta.json() == {
        "estado": "degradado",
        "base": "sin_conexion",
        "cola": "sin_conexion",
    }


def test_excepcion_del_verificador_de_base_no_filtra_la_cadena_de_conexion() -> None:
    def verificador_que_explota() -> bool:
        raise RuntimeError("no se pudo conectar a postgresql://usuario:secreto@host/db")

    cliente = _cliente_con_verificadores(verificador_que_explota, lambda: True)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    cuerpo_texto = respuesta.text
    assert "secreto" not in cuerpo_texto
    assert "postgresql://" not in cuerpo_texto
    assert respuesta.json() == {"estado": "degradado", "base": "sin_conexion", "cola": "ok"}


def test_excepcion_del_verificador_de_cola_no_filtra_host_ni_usuario_ni_excepcion() -> None:
    marcador = "marcador-excepcion-cola-7b1e2a"

    def verificador_que_explota() -> bool:
        raise RuntimeError(f"no se pudo conectar a redis://usuario:{marcador}@host:6379")

    cliente = _cliente_con_verificadores(lambda: True, verificador_que_explota)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    cuerpo_texto = respuesta.text
    assert marcador not in cuerpo_texto
    assert "redis://" not in cuerpo_texto
    assert respuesta.json() == {"estado": "degradado", "base": "ok", "cola": "sin_conexion"}


def test_sin_prefijo_responde_404() -> None:
    cliente = _cliente_con_verificadores(lambda: True, lambda: True)
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
    from proptech_api.salud import _verificador_con_engine
    from proptech_core.compartido.base_de_datos import crear_engine
    from proptech_core.compartido.configuracion import Configuracion

    monkeypatch.setenv("POSTGRES_HOST", "10.255.255.1")  # IP privada sin ruta: no responde
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "x")
    monkeypatch.setenv("POSTGRES_PASSWORD", "x")
    monkeypatch.setenv("POSTGRES_DB", "x")

    configuracion = Configuracion()
    engine = crear_engine(configuracion)
    try:
        verificar = _verificador_con_engine(engine)

        resultado: list[bool] = []
        hilo = threading.Thread(target=lambda: resultado.append(verificar()), daemon=True)
        hilo.start()
        hilo.join(timeout=5)

        assert not hilo.is_alive(), (
            "el verificador sigue colgado después de 5s: falta el plazo propio de 2s (D18)"
        )
        assert resultado == [False]
    finally:
        engine.dispose()


def test_verificador_de_cola_real_con_excepcion_devuelve_false_y_loguea_sin_el_mensaje(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D4: cualquier excepción del cliente de Redis es `sin_conexion`, nunca el
    texto del error (L-007)."""
    from proptech_api.salud import _verificador_con_cliente_redis
    from proptech_core.compartido.logs import configurar_logs

    configurar_logs("api")
    marcador = "marcador-verificador-cola-4f9c3d"

    class _ClienteQueExplota:
        def ping(self) -> bool:
            raise RuntimeError(f"no se pudo conectar: {marcador}")

    verificar = _verificador_con_cliente_redis(_ClienteQueExplota())  # type: ignore[arg-type]
    assert verificar() is False

    salida = capsys.readouterr()
    assert marcador not in salida.out
    assert marcador not in salida.err
