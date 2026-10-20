"""Alcance por edificio con 404 (D6, D7, cambio 2a, tarea 5.2), contra
PostgreSQL real, con `crear_app()` de verdad.

Contenedor propio (L-006; mismo motivo que 4.1/4.2, ver el comentario largo
en `test_tenant_por_transaccion.py`).

Escenarios de `autorizacion-por-rol`: Administrador en un edificio no
asignado; Vecino en la unidad de otro vecino; Consejo en otro edificio;
Super admin. Lecciones: L-017 (el id de otra administración es un UUID válido y
existente, nunca un texto que FastAPI ya rechaza con 422).
"""

import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from proptech_api.acceso import identidad_actual
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Alcance, Perfil

pytestmark = pytest.mark.integracion


def test_lector_arma_cada_perfil_y_su_alcance(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    sesion = sesion_edificio
    admin, persona = identidad_edificio.administracion_id, identidad_edificio.persona_id
    esperadas = set()
    complejo_vecino = uuid.uuid4()
    for rol, vinculo in (
        ("super_admin", None),
        ("administrador", None),
        ("contador", None),
        ("auxiliar", None),
        ("consejo", None),
        ("vecino", "propietario"),
        ("vecino", "inquilino"),
    ):
        complejo = None if rol == "super_admin" else uuid.uuid4()
        if vinculo:
            complejo = complejo_vecino
        unidad = uuid.uuid4() if vinculo else None
        if complejo and vinculo != "inquilino":
            sesion.execute(
                text(
                    "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                    "VALUES (:id, :admin, 'Inventado', 'Mendoza')"
                ),
                {"id": complejo, "admin": admin},
            )
        if unidad:
            sesion.execute(
                text(
                    "INSERT INTO unidad (id, administracion_id, complejo_id, identificador, "
                    "tipo, piso, coeficiente, superficie_m2) "
                    "VALUES (:id, :admin, :complejo, :nombre, 'departamento', '1', '1', '60')"
                ),
                {"id": unidad, "admin": admin, "complejo": complejo, "nombre": vinculo},
            )
        sesion.execute(
            text(
                "INSERT INTO asignacion_rol "
                "(administracion_id, persona_id, rol, complejo_id, unidad_id, vinculo) "
                "VALUES (:admin, :persona, :rol, :complejo, :unidad, :vinculo)"
            ),
            {
                "admin": admin,
                "persona": persona,
                "rol": rol,
                "complejo": complejo,
                "unidad": unidad,
                "vinculo": vinculo,
            },
        )
        esperadas.add(
            (
                Perfil(f"vecino_{vinculo}" if vinculo else rol),
                Alcance.UNIDAD if unidad else Alcance.EDIFICIO if complejo else Alcance.PRINCIPAL,
                complejo,
                unidad,
                vinculo,
            )
        )

    assert {
        (a.perfil, a.alcance, a.complejo_id, a.unidad_id, a.vinculo)
        for a in cargar_asignaciones(sesion, persona)
    } == esperadas

    # EXPLAIN de la sentencia real del lector, sin forzar el planificador.
    consultas: list[tuple[str, Any]] = []
    conexion = sesion.connection()

    def capturar(
        _conexion: Any, _cursor: Any, sentencia: str, parametros: Any, _contexto: Any, _muchas: bool
    ) -> None:
        consultas.append((sentencia, parametros))

    event.listen(conexion, "before_cursor_execute", capturar)
    try:
        cargar_asignaciones(sesion, persona)
    finally:
        event.remove(conexion, "before_cursor_execute", capturar)
    sentencia, parametros = consultas[0]
    plan = "\n".join(conexion.exec_driver_sql("EXPLAIN " + sentencia, parametros).scalars())
    print(f"proptech_app; SET LOCAL app.administracion_id = '{admin}';\n{sentencia}\n{plan}")
    assert "ix_asignacion_rol_persona" in plan

    # B tiene una fila real; A no la ve ni consultando su persona existente.
    admin_b, persona_b = uuid.uuid4(), uuid.uuid4()
    sesion.execute(
        text("SELECT set_config('app.administracion_id', :id, true)"), {"id": str(admin_b)}
    )
    sesion.execute(
        text("INSERT INTO administracion (id, nombre) VALUES (:id, 'B inventada')"), {"id": admin_b}
    )
    sesion.execute(
        text("INSERT INTO persona (id, administracion_id, nombre) VALUES (:id, :admin, 'B')"),
        {"id": persona_b, "admin": admin_b},
    )
    sesion.execute(
        text(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
            "VALUES (:admin, :persona, 'super_admin')"
        ),
        {"admin": admin_b, "persona": persona_b},
    )
    assert len(cargar_asignaciones(sesion, persona_b)) == 1
    assert cargar_asignaciones(sesion, persona) == []
    sesion.execute(
        text("SELECT set_config('app.administracion_id', :id, true)"), {"id": str(admin)}
    )
    assert cargar_asignaciones(sesion, persona_b) == []
    assert len(cargar_asignaciones(sesion, persona)) == 7


RAIZ_BACKEND = Path(__file__).resolve().parents[2]

ARRANQUE_USER = "arranque_alcance"
ARRANQUE_PASSWORD = "clave-arranque-no-real"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"


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
    """Una administración con dos complejos, dos unidades (en el primer
    complejo) y una persona por rol, más una segunda administración con su
    propio complejo (para el id "de otra administración, pero existente")."""
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    datos: dict[str, Any] = {}
    with conexion.cursor() as cur:
        admin_id = uuid.uuid4()
        cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_id),))
        cur.execute("INSERT INTO administracion (id, nombre) VALUES (%s, %s)", (str(admin_id), "A"))

        complejo_1 = uuid.uuid4()
        complejo_2 = uuid.uuid4()
        for cid, nombre in ((complejo_1, "Complejo 1"), (complejo_2, "Complejo 2")):
            cur.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "VALUES (%s, %s, %s, 'Mendoza')",
                (str(cid), str(admin_id), nombre),
            )

        unidad_1 = uuid.uuid4()
        unidad_2 = uuid.uuid4()
        for uid, nombre in ((unidad_1, "1A"), (unidad_2, "1B")):
            cur.execute(
                "INSERT INTO unidad (id, administracion_id, complejo_id, identificador, "
                "tipo, piso, coeficiente, superficie_m2) "
                "VALUES (%s, %s, %s, %s, 'departamento', '1', '0.1', '60.00')",
                (str(uid), str(admin_id), str(complejo_1), nombre),
            )

        personas: dict[str, uuid.UUID] = {}
        for nombre_rol in ("super_admin", "administrador", "consejo", "vecino1", "vecino2"):
            pid = uuid.uuid4()
            cur.execute(
                "INSERT INTO persona (id, administracion_id, nombre, email) "
                "VALUES (%s, %s, %s, %s)",
                (str(pid), str(admin_id), nombre_rol, f"{nombre_rol}@ej.com"),
            )
            personas[nombre_rol] = pid

        cur.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
            "VALUES (%s, %s, 'super_admin')",
            (str(admin_id), str(personas["super_admin"])),
        )
        # El administrador sólo está asignado al complejo 1, nunca al 2.
        cur.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id) "
            "VALUES (%s, %s, 'administrador', %s)",
            (str(admin_id), str(personas["administrador"]), str(complejo_1)),
        )
        cur.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id) "
            "VALUES (%s, %s, 'consejo', %s)",
            (str(admin_id), str(personas["consejo"]), str(complejo_1)),
        )
        cur.execute(
            "INSERT INTO asignacion_rol "
            "(administracion_id, persona_id, rol, complejo_id, unidad_id, vinculo) "
            "VALUES (%s, %s, 'vecino', %s, %s, 'propietario')",
            (str(admin_id), str(personas["vecino1"]), str(complejo_1), str(unidad_1)),
        )
        cur.execute(
            "INSERT INTO asignacion_rol "
            "(administracion_id, persona_id, rol, complejo_id, unidad_id, vinculo) "
            "VALUES (%s, %s, 'vecino', %s, %s, 'propietario')",
            (str(admin_id), str(personas["vecino2"]), str(complejo_1), str(unidad_2)),
        )

        # Otra administración, con su propio complejo (id real, existente,
        # pero inalcanzable desde la primera: L-017).
        admin_b = uuid.uuid4()
        cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_b),))
        cur.execute("INSERT INTO administracion (id, nombre) VALUES (%s, %s)", (str(admin_b), "B"))
        complejo_de_b = uuid.uuid4()
        cur.execute(
            "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
            "VALUES (%s, %s, %s, 'Mendoza')",
            (str(complejo_de_b), str(admin_b), "Complejo de B"),
        )

        datos = {
            "administracion_id": admin_id,
            "complejo_1": complejo_1,
            "complejo_2": complejo_2,
            "unidad_1": unidad_1,
            "unidad_2": unidad_2,
            "personas": personas,
            "complejo_de_b": complejo_de_b,
        }
    conexion.close()
    return datos


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


# --- Administrador en un edificio no asignado: 404 ---


def test_administrador_en_complejo_no_asignado_da_404(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any]
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"]["administrador"])
    try:
        # Su complejo asignado: 200.
        ok = cliente.get(f"/api/complejos/{mundo['complejo_1']}")
        assert ok.status_code == 200
        # El otro complejo de la misma administración, no asignado: 404.
        no = cliente.get(f"/api/complejos/{mundo['complejo_2']}")
        assert no.status_code == 404
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


# --- Vecino en la unidad de otro vecino (mismo complejo): 404 ---


def test_vecino_en_la_unidad_de_otro_vecino_da_404(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any]
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"]["vecino1"])
    try:
        propia = cliente.get(f"/api/unidades/{mundo['unidad_1']}")
        assert propia.status_code == 200
        assert propia.json() == {
            "id": str(mundo["unidad_1"]),
            "administracion_id": str(mundo["administracion_id"]),
            "complejo_id": str(mundo["complejo_1"]),
            "identificador": "1A",
            "tipo": "departamento",
            "piso": "1",
            "coeficiente": "0.100000",
            "superficie_m2": "60.00",
        }
        de_otro = cliente.get(f"/api/unidades/{mundo['unidad_2']}")
        assert de_otro.status_code == 404
        # El complejo (sin pedir una unidad en particular) sí lo alcanza.
        complejo = cliente.get(f"/api/complejos/{mundo['complejo_1']}")
        assert complejo.status_code == 200
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


# --- Consejo en otro edificio: 404 ---


def test_consejo_en_otro_complejo_da_404(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any]
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"]["consejo"])
    try:
        suyo = cliente.get(f"/api/complejos/{mundo['complejo_1']}")
        assert suyo.status_code == 200
        otro = cliente.get(f"/api/complejos/{mundo['complejo_2']}")
        assert otro.status_code == 404
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


# --- El super_admin recibe 200 en todos los de su administración ---


def test_super_admin_200_en_todos_los_complejos_y_unidades_de_su_administracion(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any]
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"]["super_admin"])
    try:
        for ruta in (
            f"/api/complejos/{mundo['complejo_1']}",
            f"/api/complejos/{mundo['complejo_2']}",
            f"/api/unidades/{mundo['unidad_1']}",
            f"/api/unidades/{mundo['unidad_2']}",
        ):
            respuesta = cliente.get(ruta)
            assert respuesta.status_code == 200, ruta
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


# --- Un id existente de otra administración y uno inexistente: misma respuesta ---


def test_complejo_de_otra_administracion_y_uno_inexistente_dan_la_misma_respuesta(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any]
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"]["super_admin"])
    try:
        de_otra_administracion = cliente.get(f"/api/complejos/{mundo['complejo_de_b']}")
        inexistente = cliente.get(f"/api/complejos/{uuid.uuid4()}")

        assert de_otra_administracion.status_code == inexistente.status_code == 404
        assert de_otra_administracion.json() == inexistente.json()

        def _sin_request_id(respuesta: Any) -> dict[str, str]:
            return {k: v for k, v in respuesta.headers.items() if k.lower() != "x-request-id"}

        assert _sin_request_id(de_otra_administracion) == _sin_request_id(inexistente)
        assert "X-Request-ID" in de_otra_administracion.headers
        assert "X-Request-ID" in inexistente.headers
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)
