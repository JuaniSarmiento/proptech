"""Valores de entorno por defecto para los tests de integración.

`Configuracion()` (D11) exige también las variables de Redis y
`PROPTECH_PARAMETROS`, aunque el test sólo le interese PostgreSQL (p.ej. Alembic
o el verificador de salud). Un test puede pisar cualquiera con su propio
`monkeypatch.setenv`/`delenv` para probar el caso contrario.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from proptech_core.acceso.dominio.identidad import Identidad

    from ._api_edificios import ApiEdificio

import psycopg
import pytest
from psycopg import sql
from testcontainers.community.postgres import PostgresContainer

from ..conftest import MIGRADOR_PASSWORD_DE_SESION, MIGRADOR_USER_DE_SESION
from ._edificios import BaseDeEdificio, Edificios, fijar_tenant, insertar_grupo, insertar_unidad

_PARAMETROS_DEL_REPO = Path(__file__).resolve().parents[3] / "config" / "parametros.yaml"


@pytest.fixture(autouse=True)
def _variables_ampliadas_por_defecto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_PASSWORD", "redis-pass")
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(_PARAMETROS_DEL_REPO))


@pytest.fixture(scope="module")
def base_del_edificio(
    postgres_contenedor: PostgresContainer, roles_reales: None
) -> Iterator[BaseDeEdificio]:
    """Reutiliza el contenedor/roles de sesión, con una base propia por módulo.

    Sólo CREATE/DROP DATABASE usa el arranque. Los escenarios y la siembra
    conectan como proptech_app; Alembic conecta como proptech_migrador.
    El ciclo downgrade/upgrade nunca altera el esquema de otro test.
    """
    nombre = f"proptech_edificio_{uuid4().hex}"
    with psycopg.connect(
        host=postgres_contenedor.get_container_host_ip(),
        port=postgres_contenedor.get_exposed_port(5432),
        user=postgres_contenedor.username,
        password=postgres_contenedor.password,
        dbname=postgres_contenedor.dbname,
        autocommit=True,
    ) as arranque:
        arranque.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(nombre), sql.Identifier(MIGRADOR_USER_DE_SESION)
            )
        )
        base = BaseDeEdificio(
            postgres_contenedor,
            nombre,
            {
                **os.environ,
                "POSTGRES_HOST": postgres_contenedor.get_container_host_ip(),
                "POSTGRES_PORT": str(postgres_contenedor.get_exposed_port(5432)),
                "POSTGRES_DB": nombre,
                "POSTGRES_MIGRADOR_USER": MIGRADOR_USER_DE_SESION,
                "POSTGRES_MIGRADOR_PASSWORD": MIGRADOR_PASSWORD_DE_SESION,
            },
        )
        try:
            for _ in range(2):
                base.roles("antes")
                base.migrar("upgrade", "head")
                base.roles("despues")
            yield base
        finally:
            arranque.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(nombre)))


@pytest.fixture
def app_edificio(base_del_edificio: BaseDeEdificio) -> Iterator[psycopg.Connection]:
    with base_del_edificio.conectar_app() as conexion:
        conexion.autocommit = False
        assert conexion.execute(
            "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        ).fetchone() == ("proptech_app", False, False)
        try:
            yield conexion
        finally:
            conexion.rollback()


@pytest.fixture
def edificios(app_edificio: psycopg.Connection) -> Edificios:
    admin_a, admin_b = uuid4(), uuid4()
    complejo_a, otro_a, complejo_b = uuid4(), uuid4(), uuid4()
    unidades = []
    for admin, complejos in ((admin_a, (complejo_a, otro_a)), (admin_b, (complejo_b,))):
        fijar_tenant(app_edificio, admin)
        app_edificio.execute(
            "INSERT INTO administracion (id, nombre) VALUES (%s, 'Administración ficticia')",
            (admin,),
        )
        for complejo in complejos:
            app_edificio.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "VALUES (%s, %s, 'Edificio de prueba', 'Mendoza')",
                (complejo, admin),
            )
            unidades.append(insertar_unidad(app_edificio, admin, complejo))
    fijar_tenant(app_edificio, admin_a)
    return Edificios(admin_a, admin_b, complejo_a, otro_a, complejo_b, *unidades)


@pytest.fixture
def sesion_edificio(base_del_edificio: BaseDeEdificio) -> Iterator[Session]:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import NullPool

    def conectar() -> psycopg.Connection:
        conexion = base_del_edificio.conectar_app()
        conexion.autocommit = False
        return conexion

    engine = create_engine("postgresql+psycopg://", creator=conectar, poolclass=NullPool)
    try:
        with Session(engine) as sesion:
            assert sesion.execute(
                text(
                    "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles "
                    "WHERE rolname = current_user"
                )
            ).one() == ("proptech_app", False, False)
            yield sesion
            sesion.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def identidad_edificio(sesion_edificio: Session) -> Identidad:
    from sqlalchemy import text

    from proptech_core.acceso.dominio.identidad import Identidad

    admin, persona = uuid4(), uuid4()
    sesion_edificio.execute(
        text("SELECT set_config('app.administracion_id', :id, true)"), {"id": str(admin)}
    )
    sesion_edificio.execute(
        text("INSERT INTO administracion (id, nombre) VALUES (:id, 'Inventada')"), {"id": admin}
    )
    sesion_edificio.execute(
        text(
            "INSERT INTO persona (id, administracion_id, nombre) "
            "VALUES (:id, :admin, 'Persona ficticia')"
        ),
        {"id": persona, "admin": admin},
    )
    return Identidad(admin, persona)


@pytest.fixture
def api_edificio(
    base_del_edificio: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch
) -> Iterator[ApiEdificio]:
    from datetime import UTC, datetime

    from fastapi.testclient import TestClient
    from sqlalchemy import text

    from proptech_api.app import crear_app
    from proptech_core.acceso.dominio.identidad import Identidad
    from proptech_core.compartido.base_de_datos import abrir_sesion
    from proptech_core.compartido.parametros import leer_parametros
    from proptech_core.complejos.aplicacion.escritura import crear_edificio

    from ..conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION
    from ._api_edificios import ApiEdificio

    for clave, valor in base_del_edificio.entorno.items():
        if clave in {"POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB"}:
            monkeypatch.setenv(clave, valor)
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER_DE_SESION)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD_DE_SESION)
    app = crear_app()
    admin, admin_b = uuid4(), uuid4()
    personas = {rol: uuid4() for rol in ("titular", "editar", "ver", "consejo", "vecino")}
    with TestClient(app) as cliente:
        with abrir_sesion(app.state.fabrica_de_sesiones, admin) as sesion:
            sesion.execute(
                text("INSERT INTO administracion (id, nombre) VALUES (:id, 'Inventada API')"),
                {"id": admin},
            )
            for persona in personas.values():
                sesion.execute(
                    text(
                        "INSERT INTO persona (id, administracion_id, nombre) "
                        "VALUES (:id, :admin, 'Persona ficticia')"
                    ),
                    {"id": persona, "admin": admin},
                )
            identidad = Identidad(admin, personas["titular"])
            parametros = leer_parametros(str(_PARAMETROS_DEL_REPO))
            edificios = [
                crear_edificio(
                    sesion,
                    identidad,
                    nombre=nombre,
                    localidad="Mendoza",
                    parametros=parametros,
                    reloj=lambda: datetime.now(UTC),
                    request_id=uuid4(),
                )
                for nombre in ("Edificio API", "Otro edificio API")
            ]
            unidades = [
                sesion.execute(
                    text(
                        "INSERT INTO unidad (administracion_id, complejo_id, identificador, "
                        "tipo, piso, coeficiente, superficie_m2) "
                        "VALUES (:admin, :edificio, :nombre, 'departamento', '1', '0.5', '60') "
                        "RETURNING id"
                    ),
                    {"admin": admin, "edificio": edificio, "nombre": nombre},
                ).scalar_one()
                for edificio, nombre in (
                    (edificios[0], "1A"),
                    (edificios[0], "1B"),
                    (edificios[1], "2A"),
                )
            ]
            for rol, persona in personas.items():
                sesion.execute(
                    text(
                        "INSERT INTO asignacion_rol "
                        "(administracion_id, persona_id, rol, complejo_id, unidad_id, nivel) "
                        "VALUES (:admin, :persona, :rol, :edificio, :unidad, :nivel)"
                    ),
                    {
                        "admin": admin,
                        "persona": persona,
                        "rol": "colaborador" if rol in ("editar", "ver") else rol,
                        "edificio": None if rol == "titular" else edificios[0],
                        "unidad": unidades[0] if rol == "vecino" else None,
                        "nivel": rol if rol in ("editar", "ver") else None,
                    },
                )
            sesion.commit()
        with base_del_edificio.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin_b)
            ajeno = uuid4()
            conexion.execute(
                "INSERT INTO administracion (id, nombre) VALUES (%s, 'Otra inventada API')",
                (admin_b,),
            )
            conexion.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "VALUES (%s, %s, 'Ajeno API', 'Mendoza')",
                (ajeno, admin_b),
            )
            unidad_ajena = insertar_unidad(conexion, admin_b, ajeno)
            grupo_ajeno = insertar_grupo(conexion, admin_b, ajeno)
            categoria_ajena = uuid4()
            conexion.execute(
                "INSERT INTO categoria_de_gasto (id, administracion_id, complejo_id, clave, "
                "nombre, orden) VALUES (%s, %s, %s, 'limpieza', 'Limpieza', 0)",
                (categoria_ajena, admin_b, ajeno),
            )
        api = ApiEdificio(
            app=app,
            cliente=cliente,
            base=base_del_edificio,
            admin=admin,
            admin_ajena=admin_b,
            edificio=edificios[0],
            otro=edificios[1],
            ajeno=ajeno,
            unidad=unidades[0],
            otra_unidad=unidades[2],
            unidad_ajena=unidad_ajena,
            grupo_ajeno=grupo_ajeno,
            categoria_ajena=categoria_ajena,
            personas=personas,
        )
        api.como("titular")
        yield api
