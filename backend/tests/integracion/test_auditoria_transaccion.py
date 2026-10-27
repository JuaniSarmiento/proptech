"""`registrar()` en la misma transacción que el efecto (D9, cambio 2a, tarea
6.2), contra PostgreSQL real. Contenedor propio (L-006).

Se ejercitan los casos marcados de configuración y padrón, cada uno con su evento.

Escenarios de `auditoria-de-acciones`: Acción confirmada; Acción revertida;
Registro que no se puede escribir; Toda acción sensible registrada.
Lecciones: L-007, L-011, L-013.
"""

from __future__ import annotations

import subprocess
import sys
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
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
from proptech_core.acceso.dominio.eventos import EventoDelPadron
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.georef import leer_georef
from proptech_core.compartido.parametros import leer_parametros
from proptech_core.complejos.aplicacion import categorias, escritura, grupos, unidades
from proptech_core.complejos.aplicacion.escritura import asignar_complejo_a_persona
from proptech_core.complejos.dominio.configuracion import ConfiguracionEdificio

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
_GEOREF = leer_georef(str(RAIZ_BACKEND.parent / "config/georef"))

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
    """D9/D11, y desde R2 (vuelta 2) también la función de sus triggers: el
    `downgrade` de la 0004 corre como migrador y hace `DROP FUNCTION`, y ya
    no es su dueño (gemelo del helper de `test_auditoria_tabla.py`)."""
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
            config = cur.execute("SELECT to_regclass('public.configuracion_versionada')").fetchone()
            if config is not None and config[0] is not None:
                cur.execute(f"ALTER TABLE configuracion_versionada OWNER TO {MIGRADOR_USER}")
                cur.execute(
                    f"ALTER FUNCTION fn_configuracion_versionada_bloqueada() "
                    f"OWNER TO {MIGRADOR_USER}"
                )
            # 4b: las seis tablas del libro también son del arranque tras `despues`.
            from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

            for tabla in TABLAS_DE_SOLO_AGREGAR:
                if tabla in {"auditoria", "configuracion_versionada"}:
                    continue
                existe = cur.execute("SELECT to_regclass(%s)", (f"public.{tabla}",)).fetchone()
                if existe is not None and existe[0] is not None:
                    cur.execute(f"ALTER TABLE {tabla} OWNER TO {MIGRADOR_USER}")
                    cur.execute(f"ALTER FUNCTION fn_{tabla}_bloqueada() OWNER TO {MIGRADOR_USER}")
            cur.execute("SELECT to_regclass('public.auditoria') IS NOT NULL")
            fila = cur.fetchone()
            if fila is not None and fila[0]:
                cur.execute(f"ALTER TABLE auditoria OWNER TO {MIGRADOR_USER}")
                cur.execute(
                    "SELECT DISTINCT p.proname FROM pg_trigger t "
                    "JOIN pg_proc p ON p.oid = t.tgfoid "
                    "WHERE t.tgrelid = 'auditoria'::regclass AND NOT t.tgisinternal"
                )
                for fila_funcion in cur.fetchall():
                    cur.execute(f"ALTER FUNCTION {fila_funcion[0]}() OWNER TO {MIGRADOR_USER}")
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
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "VALUES (%s, %s, %s, 'Mendoza')",
                (str(complejo_id), str(admin_id), "Complejo de prueba"),
            )
            super_admin_id = uuid.uuid4()
            administrador_id = uuid.uuid4()
            for persona_id, nombre in (
                (super_admin_id, "Super admin"),
                (administrador_id, "Administrador"),
            ):
                cur.execute(
                    "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, %s)",
                    (str(persona_id), str(admin_id), nombre),
                )
            datos = {
                "administracion_id": admin_id,
                "complejo_id": complejo_id,
                "super_admin_id": super_admin_id,
                "administrador_id": administrador_id,
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
        administracion_id=datos["administracion_id"], persona_id=datos["super_admin_id"]
    )
    request_id = uuid.uuid4()

    sesion = _sesion_app(contenedor)
    try:
        _con_tenant(sesion, datos["administracion_id"])
        asignar_complejo_a_persona(
            sesion,
            identidad,
            complejo_id=datos["complejo_id"],
            persona_id=datos["administrador_id"],
            rol="administrador",
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
        assert fila.persona_id == datos["super_admin_id"]
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
        administracion_id=datos["administracion_id"], persona_id=datos["super_admin_id"]
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
                persona_id=datos["administrador_id"],
                rol="administrador",
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
        administracion_id=datos["administracion_id"], persona_id=datos["super_admin_id"]
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
                persona_id=datos["administrador_id"],
                rol="vecino",
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
    """Recorre el registro completo: cada caso tiene invocador y deja una fila por evento."""
    datos = _sembrar_administracion_complejo_y_personas(contenedor)
    identidad = Identidad(
        administracion_id=datos["administracion_id"], persona_id=datos["super_admin_id"]
    )

    def invocar_padron(sesion: Session, evento: EventoDelPadron) -> UUID:
        from .test_unidades_casos_de_uso import DATOS

        edificio = escritura.crear_edificio(
            sesion,
            identidad,
            nombre="Padrón ficticio",
            provincia_id="50",
            departamento_id="50007",
            localidad_id="50007010",
            georef=_GEOREF,
            pisos=4,
            subsuelos=1,
            parametros=leer_parametros(str(RAIZ_BACKEND.parent / "config/parametros.yaml")),
            reloj=lambda: datetime(2026, 11, 1, tzinfo=UTC),
            request_id=uuid.uuid4(),
        )
        uid = unidades.crear_unidad(
            sesion, identidad, complejo_id=edificio, datos=DATOS, request_id=uuid.uuid4()
        )
        if evento == EventoDelPadron.CREAR_UNIDAD:
            return uid
        if evento == EventoDelPadron.EDITAR_UNIDAD:
            unidades.editar_unidad(
                sesion, identidad, unidad_id=uid, cambios={"piso": "2"}, request_id=uuid.uuid4()
            )
            return uid
        if evento in (
            EventoDelPadron.CREAR_GRUPO,
            EventoDelPadron.EDITAR_GRUPO,
            EventoDelPadron.FIJAR_UNIDADES,
        ):
            gid = grupos.crear_grupo(
                sesion,
                identidad,
                complejo_id=edificio,
                datos={"clave": "auditado", "nombre": "Ficticio", "metodo": "coeficiente"},
                miembros=[],
                request_id=uuid.uuid4(),
            )
            if evento == EventoDelPadron.EDITAR_GRUPO:
                grupos.editar_grupo(
                    sesion,
                    identidad,
                    grupo_id=gid,
                    cambios={"nombre": "Otro"},
                    request_id=uuid.uuid4(),
                )
            elif evento == EventoDelPadron.FIJAR_UNIDADES:
                grupos.fijar_unidades(
                    sesion,
                    identidad,
                    grupo_id=gid,
                    modo="renormalizado",
                    miembros=[{"unidad_id": uid}],
                    request_id=uuid.uuid4(),
                )
            return gid
        if evento == EventoDelPadron.EDITAR_EDIFICIO:
            escritura.editar_edificio(
                sesion,
                identidad,
                complejo_id=edificio,
                cambios={"nombre": "Padrón ficticio editado"},
                georef=_GEOREF,
                request_id=uuid.uuid4(),
            )
            return edificio
        lista = categorias.listar_categorias(sesion, edificio)
        if evento == EventoDelPadron.EDITAR_CATEGORIA:
            categorias.editar_categoria(
                sesion,
                identidad,
                categoria_id=lista[0]["id"],
                cambios={"activa": False},
                request_id=uuid.uuid4(),
            )
            return UUID(str(lista[0]["id"]))
        categorias.reordenar_categorias(
            sesion,
            identidad,
            complejo_id=edificio,
            orden=[c["id"] for c in reversed(lista)],
            request_id=uuid.uuid4(),
        )
        return edificio

    _INVOCADORES: dict[Accion | EventoDelPadron, Callable[[Session], UUID]] = {
        Accion.CREAR_VERSION_DE_CONFIGURACION: lambda sesion: (
            escritura.crear_version_de_configuracion(
                sesion,
                identidad,
                complejo_id=datos["complejo_id"],
                configuracion=ConfiguracionEdificio.desde_parametros(
                    leer_parametros(str(RAIZ_BACKEND.parent / "config/parametros.yaml"))
                ),
                parametros=leer_parametros(str(RAIZ_BACKEND.parent / "config/parametros.yaml")),
                vigente_desde=date(2026, 11, 1),
                reloj=lambda: datetime(2026, 11, 1, 12, tzinfo=UTC),
                request_id=uuid.uuid4(),
            )
        ),
        Accion.CONFIRMAR_SIN_SALDOS_PREVIOS: lambda sesion: escritura.confirmar_sin_saldos_previos(
            sesion,
            identidad,
            complejo_id=datos["complejo_id"],
            request_id=uuid.uuid4(),
        ),
        Accion.CREAR_EDIFICIO: lambda sesion: escritura.crear_edificio(
            sesion,
            identidad,
            nombre="Ficticio",
            provincia_id="50",
            departamento_id="50007",
            localidad_id="50007010",
            georef=_GEOREF,
            pisos=4,
            subsuelos=1,
            parametros=leer_parametros(str(RAIZ_BACKEND.parent / "config/parametros.yaml")),
            reloj=lambda: datetime(2026, 11, 1, tzinfo=UTC),
            request_id=uuid.uuid4(),
        ),
        Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS: lambda sesion: asignar_complejo_a_persona(
            sesion,
            identidad,
            complejo_id=datos["complejo_id"],
            persona_id=datos["administrador_id"],
            rol="administrador",
            request_id=uuid.uuid4(),
        ),
    }

    def invocador(evento: EventoDelPadron) -> Callable[[Session], UUID]:
        return lambda sesion: invocar_padron(sesion, evento)

    for evento in EventoDelPadron:
        _INVOCADORES[evento] = invocador(evento)

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
            # Las acciones nuevas impiden downgrade por su FK (D14).
            # El barrido verifica en la misma transacción y la revierte.
            sesion.flush()
            filas = sesion.execute(
                text("SELECT 1 FROM auditoria WHERE accion = :accion"), {"accion": accion.value}
            ).all()
            assert len(filas) == 1, (
                f"{accion.value}: se esperaba 1 fila de auditoría, hay {len(filas)}"
            )
        finally:
            sesion.rollback()
            sesion.close()


@pytest.mark.parametrize("evento", [Accion.CREAR_EDIFICIO, "ingreso_exitoso"])
def test_rojo_un_caso_marcado_que_no_registra_no_pasa_el_sweep(
    monkeypatch: pytest.MonkeyPatch, evento: Accion | str
) -> None:
    """V2-7: ejercita el decorador real con dos casos para la misma acción."""
    monkeypatch.setattr(auditoria_modulo, "_CASOS_SENSIBLES", {})

    def primero() -> None:
        pass

    def segundo() -> None:
        pass

    from proptech_core.acceso.dominio.eventos import EventoDeAcceso

    accion = evento if isinstance(evento, Accion) else EventoDeAcceso(evento)
    auditoria_modulo.accion_sensible(accion)(primero)
    with pytest.raises(ValueError) as error:
        auditoria_modulo.accion_sensible(accion)(segundo)
    assert accion.value in str(error.value)
    assert "primero" in str(error.value)
    assert "segundo" in str(error.value)
    assert auditoria_modulo.casos_sensibles_registrados() == {accion: primero}
