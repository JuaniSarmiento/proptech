"""`registrar()` en la misma transacción que el efecto (D9, cambio 2a, tarea
6.2), contra PostgreSQL real. Contenedor propio (L-006).

El caso de uso real que se prueba es `complejos.aplicacion.escritura.
asignar_complejo_a_persona`, el único marcado con `@accion_sensible` hoy.

Escenarios de `auditoria-de-acciones`: Acción confirmada; Acción revertida;
Registro que no se puede escribir; Toda acción sensible registrada.
Lecciones: L-007, L-011, L-013.
"""

from __future__ import annotations

import subprocess
import sys
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import pytest
import sqlalchemy.exc
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from proptech_core.acceso.aplicacion import auditoria as auditoria_modulo
from proptech_core.acceso.aplicacion.auditoria import (
    RegistroFueraDeTransaccion,
    casos_sensibles_registrados,
    registrar,
)
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.complejos.aplicacion import escritura
from proptech_core.complejos.aplicacion.escritura import asignar_complejo_a_persona

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

ARRANQUE_USER = "arranque_auditoria_tx"
ARRANQUE_PASSWORD = "clave-arranque-no-real"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"


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


def _devolver_auditoria_al_migrador(contenedor: PostgresContainer) -> None:
    conexion = psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=ARRANQUE_USER,
        password=ARRANQUE_PASSWORD,
        dbname=contenedor.dbname,
        autocommit=True,
    )
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT to_regclass('public.auditoria') IS NOT NULL")
            fila = cur.fetchone()
            if fila is not None and fila[0]:
                cur.execute(f"ALTER TABLE auditoria OWNER TO {MIGRADOR_USER}")
    finally:
        conexion.close()


@pytest.fixture(scope="module")
def esquema(contenedor: PostgresContainer) -> Iterator[None]:
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        _entorno_de_roles(contenedor),
    )
    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "despues"],
        _entorno_de_roles(contenedor),
    )
    try:
        yield
    finally:
        _devolver_auditoria_al_migrador(contenedor)
        _correr(["uv", "run", "alembic", "downgrade", "base"], _alembic_env(contenedor))


def _sesion_app(contenedor: PostgresContainer) -> Session:
    """Sesión de SQLAlchemy real como `proptech_app` (L-016): nunca el
    superusuario, para que la política de D5 también alcance a estos tests."""
    engine = create_engine(
        f"postgresql+psycopg://{APP_USER}:{APP_PASSWORD}@"
        f"{contenedor.get_container_host_ip()}:{contenedor.get_exposed_port(5432)}/"
        f"{contenedor.dbname}"
    )
    return Session(bind=engine)


def _sembrar_administracion_complejo_y_personas(
    contenedor: PostgresContainer,
) -> dict[str, Any]:
    """Como `proptech_migrador`, fijando su propio tenant (E1: sin
    BYPASSRLS)."""
    conexion = psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=MIGRADOR_USER,
        password=MIGRADOR_PASSWORD,
        dbname=contenedor.dbname,
        autocommit=True,
    )
    datos: dict[str, Any] = {}
    try:
        with conexion.cursor() as cur:
            admin_id = uuid.uuid4()
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_id),))
            cur.execute(
                "INSERT INTO administracion (id, nombre) VALUES (%s, %s)",
                (str(admin_id), "Administración de prueba"),
            )
            complejo_id = uuid.uuid4()
            cur.execute(
                "INSERT INTO complejo (id, administracion_id, nombre) VALUES (%s, %s, %s)",
                (str(complejo_id), str(admin_id), "Complejo de prueba"),
            )
            titular_id = uuid.uuid4()
            colaborador_id = uuid.uuid4()
            for persona_id, nombre in ((titular_id, "Titular"), (colaborador_id, "Colaborador")):
                cur.execute(
                    "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, %s)",
                    (str(persona_id), str(admin_id), nombre),
                )
            datos = {
                "administracion_id": admin_id,
                "complejo_id": complejo_id,
                "titular_id": titular_id,
                "colaborador_id": colaborador_id,
            }
    finally:
        conexion.close()
    return datos


def _filas_de(sesion: Session, tabla: str) -> list[Any]:
    return list(sesion.execute(text(f"SELECT * FROM {tabla}")).all())  # noqa: S608


def _con_tenant(sesion: Session, administracion_id: uuid.UUID) -> None:
    sesion.execute(
        text("SELECT set_config('app.administracion_id', :valor, false)"),
        {"valor": str(administracion_id)},
    )


# --- registrar() fuera de una transacción es un error ---


def test_registrar_fuera_de_transaccion_es_un_error(
    contenedor: PostgresContainer, esquema: None
) -> None:
    sesion = _sesion_app(contenedor)
    try:
        assert not sesion.in_transaction()
        identidad = Identidad(administracion_id=uuid.uuid4(), persona_id=uuid.uuid4())
        with pytest.raises(RegistroFueraDeTransaccion):
            registrar(
                sesion,
                identidad,
                Accion.INFORMAR_PAGO,
                entidad="complejo",
                entidad_id=uuid.uuid4(),
                request_id=uuid.uuid4(),
            )
    finally:
        sesion.close()


# --- Acción confirmada ---


def test_asignar_complejo_deja_una_fila_de_asignacion_y_una_de_auditoria(
    contenedor: PostgresContainer, esquema: None
) -> None:
    datos = _sembrar_administracion_complejo_y_personas(contenedor)
    identidad = Identidad(
        administracion_id=datos["administracion_id"], persona_id=datos["titular_id"]
    )
    request_id = uuid.uuid4()

    sesion = _sesion_app(contenedor)
    try:
        _con_tenant(sesion, datos["administracion_id"])
        asignar_complejo_a_persona(
            sesion,
            identidad,
            complejo_id=datos["complejo_id"],
            persona_id=datos["colaborador_id"],
            rol="colaborador",
            nivel="editar",
            request_id=request_id,
        )
        sesion.commit()

        filas_asignacion = _filas_de(sesion, "asignacion_rol")
        assert len(filas_asignacion) == 1

        filas_auditoria = sesion.execute(
            text("SELECT persona_id, accion, entidad, entidad_id, request_id FROM auditoria")
        ).all()
        assert len(filas_auditoria) == 1
        fila = filas_auditoria[0]
        assert fila.persona_id == datos["titular_id"]
        assert fila.accion == Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS.value
        assert fila.entidad == "complejo"
        assert fila.entidad_id == datos["complejo_id"]
        assert fila.request_id == request_id
    finally:
        sesion.rollback()
        sesion.close()


# --- Acción revertida: una falla forzada después de registrar() revierte las dos ---


def test_una_falla_forzada_despues_de_registrar_revierte_la_asignacion_y_la_fila(
    contenedor: PostgresContainer,
    esquema: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    datos = _sembrar_administracion_complejo_y_personas(contenedor)
    identidad = Identidad(
        administracion_id=datos["administracion_id"], persona_id=datos["titular_id"]
    )

    registrar_real = auditoria_modulo.registrar

    def _registrar_y_despues_fallar(*args: Any, **kwargs: Any) -> None:
        registrar_real(*args, **kwargs)  # la fila de auditoría SÍ se escribe...
        raise RuntimeError("falla forzada después de registrar(), a propósito (L-013)")

    monkeypatch.setattr(escritura, "registrar", _registrar_y_despues_fallar)

    sesion = _sesion_app(contenedor)
    try:
        _con_tenant(sesion, datos["administracion_id"])
        with pytest.raises(RuntimeError, match="falla forzada"):
            asignar_complejo_a_persona(
                sesion,
                identidad,
                complejo_id=datos["complejo_id"],
                persona_id=datos["colaborador_id"],
                rol="colaborador",
                nivel="editar",
                request_id=uuid.uuid4(),
            )
        # ... pero la transacción (o el SAVEPOINT) revierte las dos (D9).
        assert _filas_de(sesion, "asignacion_rol") == []
        assert _filas_de(sesion, "auditoria") == []
    finally:
        sesion.rollback()
        sesion.close()


# --- Registro que no se puede escribir: una fila rechazada por la base revierte la asignación ---


def test_una_asignacion_rechazada_por_el_check_no_deja_nada(
    contenedor: PostgresContainer, esquema: None
) -> None:
    """`rol="vecino"` sin `unidad_id` viola el CHECK de forma-por-rol (3.1):
    el `INSERT` de `asignacion_rol` nunca llega a existir, así que
    `registrar()` nunca corre — no hay nada que revertir en `auditoria`
    porque nunca hubo nada que escribir ahí."""
    datos = _sembrar_administracion_complejo_y_personas(contenedor)
    identidad = Identidad(
        administracion_id=datos["administracion_id"], persona_id=datos["titular_id"]
    )

    sesion = _sesion_app(contenedor)
    try:
        _con_tenant(sesion, datos["administracion_id"])
        # Pasa por `sesion.execute()` del ORM, que envuelve el error real de
        # psycopg en `sqlalchemy.exc.IntegrityError` (`.orig` es el de
        # psycopg): se verifica el envoltorio, que es lo que esta sesión
        # realmente levanta.
        with pytest.raises(sqlalchemy.exc.IntegrityError) as excinfo:
            asignar_complejo_a_persona(
                sesion,
                identidad,
                complejo_id=datos["complejo_id"],
                persona_id=datos["colaborador_id"],
                rol="vecino",
                nivel=None,
                request_id=uuid.uuid4(),
            )
        assert isinstance(excinfo.value.orig, psycopg.errors.CheckViolation)
        sesion.rollback()

        sesion2 = _sesion_app(contenedor)
        try:
            _con_tenant(sesion2, datos["administracion_id"])
            assert _filas_de(sesion2, "asignacion_rol") == []
            assert _filas_de(sesion2, "auditoria") == []
        finally:
            sesion2.rollback()
            sesion2.close()
    finally:
        sesion.close()


# --- Toda acción sensible registrada ---


def test_todos_los_casos_marcados_dejan_exactamente_una_fila_de_auditoria(
    contenedor: PostgresContainer, esquema: None
) -> None:
    """Recorre `casos_sensibles_registrados()`. Hoy sólo hay uno
    (`asignar_complejo_a_persona`); se invoca con fixtures mínimas y se
    exige una fila por Accion."""
    datos = _sembrar_administracion_complejo_y_personas(contenedor)
    identidad = Identidad(
        administracion_id=datos["administracion_id"], persona_id=datos["titular_id"]
    )

    _INVOCADORES: dict[Accion, Callable[[Session], UUID]] = {
        Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS: lambda sesion: asignar_complejo_a_persona(
            sesion,
            identidad,
            complejo_id=datos["complejo_id"],
            persona_id=datos["colaborador_id"],
            rol="colaborador",
            nivel="editar",
            request_id=uuid.uuid4(),
        ),
    }

    registrados = casos_sensibles_registrados()
    assert set(registrados) == set(_INVOCADORES), (
        "hay un caso de uso marcado con @accion_sensible sin invocador en este test "
        "(sumar uno antes de marcar un caso de uso nuevo)"
    )

    for accion, invocar in _INVOCADORES.items():
        sesion = _sesion_app(contenedor)
        try:
            _con_tenant(sesion, datos["administracion_id"])
            invocar(sesion)
            sesion.commit()
            filas = sesion.execute(
                text("SELECT 1 FROM auditoria WHERE accion = :accion"), {"accion": accion.value}
            ).all()
            assert len(filas) == 1, (
                f"{accion.value}: se esperaba 1 fila de auditoría, hay {len(filas)}"
            )
        finally:
            sesion.rollback()
            sesion.close()


def test_rojo_un_caso_marcado_que_no_registra_no_pasa_el_sweep(
    contenedor: PostgresContainer, esquema: None
) -> None:
    """L-013: sobre una COPIA del registro (`casos_sensibles_registrados()`
    ya devuelve una, nunca el dict real), se agrega un caso de uso falso que
    jamás llama a `registrar()`, y se repite la misma aserción del sweep
    real para verla fallar."""

    def _caso_falso_que_no_registra(sesion: Session) -> None:
        with sesion.begin_nested() if sesion.in_transaction() else sesion.begin():
            pass  # a propósito: nunca llama a registrar().

    registro_falso = {
        **casos_sensibles_registrados(),
        Accion.ACEPTAR_ALERTAS_NO_BLOQUEANTES: _caso_falso_que_no_registra,
    }
    assert Accion.ACEPTAR_ALERTAS_NO_BLOQUEANTES in registro_falso

    sesion = _sesion_app(contenedor)
    try:
        _caso_falso_que_no_registra(sesion)
        sesion.commit()
        filas = sesion.execute(
            text("SELECT 1 FROM auditoria WHERE accion = :accion"),
            {"accion": Accion.ACEPTAR_ALERTAS_NO_BLOQUEANTES.value},
        ).all()
        with pytest.raises(AssertionError):
            assert len(filas) == 1, "se esperaba 1 fila de auditoría para este caso marcado"
    finally:
        sesion.rollback()
        sesion.close()
