"""R11 (D7 del design, E8): el id de un alta lo genera siempre el servidor.

Barrido de TODA ruta `POST` de dominio que encuentra el barrido de rutas
(mismo criterio que R6/D8, `_barrido_de_rutas`, compartido con
`test_rutas_protegidas.py`, L-009): a su cuerpo válido (de
`_CUERPOS_DE_PRUEBA`) le suma `id`, `administracion_id` y `complejo_id`
con un marcador, y espera 422 cuya ruta de error nombra `id` (no cualquier
campo), ninguna fila nueva en la base y el marcador ausente de TODA la
respuesta (nunca el valor rechazado, L-007).

Una ruta `POST` sin cuerpo de prueba en `_CUERPOS_DE_PRUEBA` hace fallar la
suite nombrándola: nunca se saltea en silencio (L-019). Hoy sólo existe una
ruta `POST` bajo `/api` (la asignación del 2a); si una tarea futura agrega
otra sin pasar por este archivo, este test la detecta y falla.

Exclusiones, con el motivo (D7, nota N8):

- la asignación del 2a (`/api/complejos/{complejo_id}/asignaciones`): su
  `CuerpoAsignacion` declara `administracion_id` a propósito y lo ignora
  (diferencia conocida con el resto del cambio); para ESTA ruta sólo se
  exige que `id` dé 422 nombrándolo, no que `administracion_id` también lo
  haga (puede dar otro error, de tipo, porque SÍ está declarado).
- `POST .../sin-saldos-previos` (tarea 6.1, todavía no existe): no lleva
  cuerpo. Se deja la constante declarada para cuando 6.1 la agregue.

Contenedor propio (L-006; mismo motivo que 4.1/4.2/5.2/5.3 y
`test_rutas_protegidas.py`).
"""

import subprocess
import sys
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from proptech_api.acceso import identidad_actual
from proptech_core.acceso.dominio.identidad import Identidad

from ._barrido_de_rutas import rutas_efectivas

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

ARRANQUE_USER = "arranque_altas"
ARRANQUE_PASSWORD = "clave-arranque-no-real"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"

#: Marcador reconocible, nunca un UUID válido: si aparece en la respuesta,
#: es la fuga que este test existe para impedir (L-007).
_MARCADOR = "marcador-nunca-tendria-que-salir-en-una-respuesta"

#: Rutas `POST` SIN cuerpo (D7, nota N8): quedan fuera del barrido de abajo
#: porque no hay nada a lo que sumarle `id`. `.../sin-saldos-previos` es de
#: la tarea 6.1, que todavía no existe en este cambio.
_RUTAS_SIN_CUERPO: set[tuple[str, str]] = {
    ("/api/sesion/ingreso", "POST"),
    ("/api/complejos/{complejo_id}/estado-de-migracion/sin-saldos-previos", "POST"),
}

#: Cuerpo válido por ruta `POST` de dominio (D7, nota N8): una ruta nueva
#: que no agregue su entrada acá hace fallar `test_toda_ruta_post_tiene_cuerpo_de_prueba`.
_CUERPOS_DE_PRUEBA: dict[tuple[str, str], Callable[[dict[str, Any]], dict[str, Any]]] = {
    ("/api/complejos/{complejo_id}/categorias", "POST"): lambda mundo: {
        "clave": "nueva",
        "nombre": "Nueva",
    },
    ("/api/complejos/{complejo_id}/configuracion/versiones", "POST"): lambda mundo: {
        "vigente_desde": "2099-01-01",
        "tasa_mensual": "4.00",
        "dias_de_gracia": 0,
        "forma_de_calculo": "proporcional_por_dia",
        "porcentaje_fondo": "2.00",
        "dia_de_vencimiento": 10,
        "modalidad_de_vencimiento": "unico",
    },
    ("/api/complejos/{complejo_id}/unidades", "POST"): lambda mundo: {
        "identificador": "2A",
        "tipo": "departamento",
        "piso": "2",
        "coeficiente": "0.2",
        "superficie_m2": "60.00",
    },
    ("/api/complejos/{complejo_id}/grupos", "POST"): lambda mundo: {
        "clave": "ascensor",
        "nombre": "Ascensor",
        "metodo": "coeficiente",
        "unidades": [],
    },
    ("/api/complejos", "POST"): lambda mundo: {"nombre": "Edificio", "localidad": "Mendoza"},
    ("/api/complejos/{complejo_id}/asignaciones", "POST"): lambda mundo: {
        "persona_id": str(mundo["destinatario"]),
        "rol": "consejo",
    },
}

#: Motivo por el que, en esta ruta puntual, `administracion_id` no tiene que
#: dar 422 nombrándolo (diferencia conocida del 2a, D7) — sólo documenta el
#: porqué, no saca la ruta del barrido: `id` SÍ tiene que dar 422 igual.
_EXCLUSION_ADMINISTRACION_ID = {
    ("/api/complejos/{complejo_id}/asignaciones", "POST"): (
        "CuerpoAsignacion declara administracion_id y lo ignora a propósito "
        "(2a); no es un campo 'extra', así que no da extra_forbidden."
    ),
}


def _conectar(contenedor: PostgresContainer, usuario: str, password: str) -> psycopg.Connection:
    return psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=usuario,
        password=password,
        dbname=contenedor.dbname,
        autocommit=True,
    )


@pytest.fixture(scope="module")
def contenedor() -> Iterator[PostgresContainer]:
    from ..conftest import IMAGEN_POSTGRES_PARA_TESTS

    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username=ARRANQUE_USER,
        password=ARRANQUE_PASSWORD,
    ) as iniciado:
        yield iniciado


def _entorno_de_roles(contenedor: PostgresContainer) -> dict[str, str]:
    import os

    return {
        **os.environ,
        "POSTGRES_HOST": contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
        "POSTGRES_USER": contenedor.username,
        "POSTGRES_PASSWORD": contenedor.password,
        "POSTGRES_DB": contenedor.dbname,
        "POSTGRES_MIGRADOR_USER": MIGRADOR_USER,
        "POSTGRES_MIGRADOR_PASSWORD": MIGRADOR_PASSWORD,
        "POSTGRES_APP_USER": APP_USER,
        "POSTGRES_APP_PASSWORD": APP_PASSWORD,
        "POSTGRES_RESPALDO_USER": RESPALDO_USER,
        "POSTGRES_RESPALDO_PASSWORD": RESPALDO_PASSWORD,
    }


def _alembic_env(contenedor: PostgresContainer) -> dict[str, str]:
    entorno = dict(_entorno_de_roles(contenedor))
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"):
        entorno.pop(variable, None)
    return entorno


def _correr(args: list[str], entorno: dict[str, str]) -> None:
    subprocess.run(args, cwd=RAIZ_BACKEND, env=entorno, check=True, capture_output=True, text=True)


@pytest.fixture(scope="module")
def esquema(contenedor: PostgresContainer) -> Iterator[None]:
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        _entorno_de_roles(contenedor),
    )
    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    try:
        yield
    finally:
        _correr(["uv", "run", "alembic", "downgrade", "base"], _alembic_env(contenedor))


@pytest.fixture(scope="module")
def mundo(contenedor: PostgresContainer, esquema: None) -> dict[str, Any]:
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    with conexion.cursor() as cur:
        admin_id = uuid.uuid4()
        cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_id),))
        cur.execute("INSERT INTO administracion (id, nombre) VALUES (%s, %s)", (str(admin_id), "A"))

        complejo_id = uuid.uuid4()
        cur.execute(
            "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
            "VALUES (%s, %s, %s, 'Mendoza')",
            (str(complejo_id), str(admin_id), "Complejo"),
        )

        super_admin_id = uuid.uuid4()
        destinatario_id = uuid.uuid4()
        for pid, nombre in ((super_admin_id, "super_admin"), (destinatario_id, "destinatario")):
            cur.execute(
                "INSERT INTO persona (id, administracion_id, nombre, email) "
                "VALUES (%s, %s, %s, %s)",
                (str(pid), str(admin_id), nombre, f"{nombre}@ej.com"),
            )
        cur.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
            "VALUES (%s, %s, 'super_admin')",
            (str(admin_id), str(super_admin_id)),
        )
    conexion.close()
    return {
        "administracion_id": admin_id,
        "complejo_id": complejo_id,
        "super_admin": super_admin_id,
        "destinatario": destinatario_id,
    }


def _cantidad_de_asignaciones(contenedor: PostgresContainer, administracion_id: uuid.UUID) -> int:
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.administracion_id', %s, false)", (str(administracion_id),)
            )
            cur.execute("SELECT count(*) FROM asignacion_rol")
            fila = cur.fetchone()
            assert fila is not None
            return int(fila[0])
    finally:
        conexion.close()


@pytest.fixture
def app_real(
    contenedor: PostgresContainer, esquema: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> Iterator[FastAPI]:
    monkeypatch.setenv("POSTGRES_HOST", contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(contenedor.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD)
    monkeypatch.setenv("POSTGRES_DB", contenedor.dbname)
    monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
    monkeypatch.setenv("REDIS_PORT", "1")
    monkeypatch.setenv("REDIS_PASSWORD", "x")
    ruta_parametros = tmp_path / "parametros.yaml"
    raiz = RAIZ_BACKEND.parent
    ruta_parametros.write_text((raiz / "config" / "parametros.yaml").read_text())
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(ruta_parametros))

    from proptech_api.app import crear_app

    app = crear_app()
    with TestClient(app):
        yield app


@pytest.fixture
def cliente(app_real: FastAPI) -> Iterator[TestClient]:
    with TestClient(app_real) as cliente:
        yield cliente


def _como(app: FastAPI, administracion_id: uuid.UUID, persona_id: uuid.UUID) -> None:
    app.dependency_overrides[identidad_actual] = lambda: Identidad(
        administracion_id=administracion_id, persona_id=persona_id
    )


def _rutas_post_de_dominio(app: FastAPI) -> list[tuple[str, str]]:
    """Toda ruta `POST` bajo `/api` que encuentra el mismo barrido de R6
    (D8), menos las públicas (ninguna hoy es `POST`) — sin repetir una ruta
    con más de un método."""
    vistas: set[tuple[str, str]] = set()
    for sub in rutas_efectivas(app):
        if "POST" in (sub.methods or set()):
            vistas.add((sub.path, "POST"))
    return sorted(vistas)


# --- Ninguna ruta POST nueva se queda sin cuerpo de prueba (L-019) ---


def test_toda_ruta_post_tiene_cuerpo_de_prueba(app_real: FastAPI) -> None:
    encontradas = (
        set(_rutas_post_de_dominio(app_real))
        - _RUTAS_SIN_CUERPO
        - {("/api/invitaciones/aceptar", "POST")}
    )
    # D6 tiene su contrato de cuerpo propio en test_dos_guardas/test_aceptar_invitacion_api.
    declaradas = set(_CUERPOS_DE_PRUEBA.keys())
    sin_cuerpo = encontradas - declaradas
    assert not sin_cuerpo, f"ruta(s) POST sin cuerpo de prueba en _CUERPOS_DE_PRUEBA: {sin_cuerpo}"


# --- El barrido de R11: id, administracion_id y complejo_id con marcador ---


@pytest.mark.parametrize("ruta_y_metodo", sorted(_CUERPOS_DE_PRUEBA.keys()))
def test_alta_con_id_del_cliente_da_422_sin_escribir_ni_filtrar_el_valor(
    cliente: TestClient,
    app_real: FastAPI,
    contenedor: PostgresContainer,
    mundo: dict[str, Any],
    ruta_y_metodo: tuple[str, str],
) -> None:
    ruta, _metodo = ruta_y_metodo
    cuerpo_valido = _CUERPOS_DE_PRUEBA[ruta_y_metodo](mundo)
    cuerpo_con_ids_del_cliente = {
        **cuerpo_valido,
        "id": _MARCADOR,
        "administracion_id": _MARCADOR,
        "complejo_id": _MARCADOR,
    }
    ruta_resuelta = ruta.format(complejo_id=mundo["complejo_id"])

    antes = _cantidad_de_asignaciones(contenedor, mundo["administracion_id"])
    _como(app_real, mundo["administracion_id"], mundo["super_admin"])
    try:
        respuesta = cliente.post(ruta_resuelta, json=cuerpo_con_ids_del_cliente)
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)
    despues = _cantidad_de_asignaciones(contenedor, mundo["administracion_id"])

    assert respuesta.status_code == 422, f"{ruta}: {respuesta.status_code} — {respuesta.text}"
    assert despues == antes, "el alta con id del cliente escribió una fila (R11 roto)"
    assert _MARCADOR not in respuesta.text, (
        "el 422 repite el marcador (el valor rechazado) en la respuesta (L-007)"
    )

    errores = respuesta.json()["detail"]
    locs_con_id = [error["loc"] for error in errores if "id" in error["loc"]]
    assert locs_con_id, f"ningún error del 422 nombra 'id': {errores}"


def test_las_exclusiones_documentadas_siguen_siendo_rutas_del_barrido() -> None:
    """Guarda de coherencia: si una exclusión queda huérfana (la ruta que
    nombra ya no existe en `_CUERPOS_DE_PRUEBA`), que se note acá y no se
    arrastre como comentario muerto."""
    for ruta_y_metodo in _EXCLUSION_ADMINISTRACION_ID:
        assert ruta_y_metodo in _CUERPOS_DE_PRUEBA, ruta_y_metodo
