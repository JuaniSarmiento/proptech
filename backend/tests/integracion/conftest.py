"""Valores de entorno por defecto para los tests de integración.

`Configuracion()` (D11) exige también las variables de Redis y
`PROPTECH_PARAMETROS`, aunque el test sólo le interese PostgreSQL (p.ej. Alembic
o el verificador de salud). Un test puede pisar cualquiera con su propio
`monkeypatch.setenv`/`delenv` para probar el caso contrario.
"""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from proptech_core.acceso.dominio.identidad import Identidad

import psycopg
import pytest
from psycopg import sql
from testcontainers.community.postgres import PostgresContainer

from ..conftest import MIGRADOR_PASSWORD_DE_SESION, MIGRADOR_USER_DE_SESION
from ._edificios import BaseDeEdificio, Edificios, fijar_tenant, insertar_unidad

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
