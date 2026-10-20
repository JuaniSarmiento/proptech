"""D5: conversión transaccional de todos los tenants, como roles reales."""

import importlib.util
import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import Base

from ..conftest import IMAGEN_POSTGRES_PARA_TESTS, MIGRADOR_USER_DE_SESION
from ._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad

pytestmark = pytest.mark.integracion
_MIGRACION = (
    Path(__file__).resolve().parents[2] / "migraciones/versions/0017_roles_de_la_empresa.py"
)


@pytest.fixture(scope="module")
def postgres_roles() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username="proptech_test",
        password="proptech_test",  # noqa: S106 (sólo este contenedor de test)
    ) as contenedor:
        yield contenedor


@pytest.fixture
def base_roles(postgres_roles: PostgresContainer) -> Iterator[BaseDeEdificio]:
    c = postgres_roles
    nombre = "proptech_roles_" + uuid4().hex
    with psycopg.connect(
        host=c.get_container_host_ip(),
        port=c.get_exposed_port(5432),
        user=c.username,
        password=c.password,
        dbname=c.dbname,
        autocommit=True,
    ) as arranque:
        # roles antes necesita la base default para crear el dueño primero.
        entorno = {
            **os.environ,
            "POSTGRES_HOST": c.get_container_host_ip(),
            "POSTGRES_PORT": str(c.get_exposed_port(5432)),
            "POSTGRES_DB": c.dbname,
            "POSTGRES_MIGRADOR_USER": MIGRADOR_USER_DE_SESION,
            "POSTGRES_MIGRADOR_PASSWORD": "clave-migrador-de-sesion-no-real",
        }
        inicial = BaseDeEdificio(c, c.dbname, entorno)
        inicial.roles("antes")
        arranque.execute(
            psycopg.sql.SQL("CREATE DATABASE {} OWNER {}").format(
                psycopg.sql.Identifier(nombre), psycopg.sql.Identifier(MIGRADOR_USER_DE_SESION)
            )
        )
        base = BaseDeEdificio(c, nombre, {**entorno, "POSTGRES_DB": nombre})
        try:
            base.roles("antes")
            base.migrar("upgrade", "0016")
            base.roles("despues")
            yield base
        finally:
            arranque.execute(
                psycopg.sql.SQL("DROP DATABASE {}").format(psycopg.sql.Identifier(nombre))
            )


# admin, complejo, unidad, personas de las cinco formas viejas.
Legado = tuple[UUID, UUID, UUID, list[UUID]]


def _sembrar(base: BaseDeEdificio) -> list[Legado]:
    datos = []
    with base.conectar_app() as c, c.transaction():
        assert c.execute(
            "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        ).fetchone() == ("proptech_app", False, False)
        for _ in range(2):
            admin, complejo = uuid4(), uuid4()
            personas = [uuid4() for _ in range(5)]
            fijar_tenant(c, admin)
            c.execute("INSERT INTO administracion (id,nombre) VALUES (%s,'Ficticia')", (admin,))
            c.execute(
                "INSERT INTO complejo (id,administracion_id,nombre,localidad) "
                "VALUES (%s,%s,'Ficticio','Mendoza')",
                (complejo, admin),
            )
            unidad = insertar_unidad(c, admin, complejo)
            for persona, rol, nivel in zip(
                personas,
                ("titular", "colaborador", "colaborador", "consejo", "vecino"),
                (None, "editar", "ver", None, None),
                strict=True,
            ):
                c.execute(
                    "INSERT INTO persona (id,administracion_id,nombre) "
                    "VALUES (%s,%s,'Persona inventada')",
                    (persona, admin),
                )
                c.execute(
                    "INSERT INTO asignacion_rol "
                    "(administracion_id,persona_id,rol,complejo_id,unidad_id,nivel) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        admin,
                        persona,
                        rol,
                        None if rol == "titular" else complejo,
                        unidad if rol == "vecino" else None,
                        nivel,
                    ),
                )
            datos.append((admin, complejo, unidad, personas))
    return datos


def _catalogo(base: BaseDeEdificio) -> dict[str, list[tuple[object, ...]]]:
    consultas = {
        "columnas": "SELECT column_name,data_type,is_nullable,column_default "
        "FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='asignacion_rol' ORDER BY column_name",
        "constraints": "SELECT conname,contype,pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid='asignacion_rol'::regclass ORDER BY conname",
        "indices": "SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' "
        "AND tablename='asignacion_rol' ORDER BY indexname",
        "politicas": "SELECT policyname,permissive,roles,cmd,qual,with_check FROM pg_policies "
        "WHERE schemaname='public' AND tablename='asignacion_rol' ORDER BY policyname",
        "rls": "SELECT relrowsecurity,relforcerowsecurity FROM pg_class "
        "WHERE oid='asignacion_rol'::regclass",
    }
    with base.conectar_app() as c:
        return {nombre: c.execute(sql).fetchall() for nombre, sql in consultas.items()}


def _filas(
    base: BaseDeEdificio, datos: list[Legado], columna: str
) -> list[list[tuple[object, ...]]]:
    assert columna in ("nivel", "vinculo")
    with base.conectar_app() as c, c.transaction():
        resultado = []
        for admin, _, _, _ in datos:
            fijar_tenant(c, admin)
            resultado.append(
                c.execute(
                    psycopg.sql.SQL(
                        "SELECT persona_id,rol,complejo_id,unidad_id,{} FROM asignacion_rol "
                        "ORDER BY persona_id"
                    ).format(psycopg.sql.Identifier(columna))
                ).fetchall()
            )
            assert c.execute(
                "SELECT count(*) FROM asignacion_rol WHERE administracion_id <> %s", (admin,)
            ).fetchone() == (0,)
        return resultado


def _comprobar_conversion(base: BaseDeEdificio, datos: list[Legado]) -> None:
    filas = _filas(base, datos, "vinculo")
    for lote, (_, complejo, unidad, personas) in zip(filas, datos, strict=True):
        esperado = [
            (
                persona,
                rol,
                None if rol == "super_admin" else complejo,
                unidad if rol == "vecino" else None,
                "propietario" if rol == "vecino" else None,
            )
            for persona, rol in zip(
                personas,
                ("super_admin", "administrador", "auxiliar", "consejo", "vecino"),
                strict=True,
            )
        ]
        assert lote == sorted(esperado)
    # El dueño también debe volver a quedar filtrado por FORCE, sin tenant.
    with base.conectar_migrador() as c:
        assert c.execute("SELECT count(*) FROM asignacion_rol").fetchone() == (0,)

    catalogo = _catalogo(base)
    assert catalogo["rls"] == [(True, True)]
    assert "nivel" not in {fila[0] for fila in catalogo["columnas"]}
    assert {fila[0] for fila in catalogo["indices"]} == {
        "pk_asignacion_rol",
        "uq_asignacion_rol_persona_unidad",
        "uq_asignacion_rol_persona_alcance",
        "ix_asignacion_rol_persona",
    }


def test_upgrade_convierte_dos_administraciones_y_conserva_aislamiento(
    base_roles: BaseDeEdificio,
) -> None:
    datos = _sembrar(base_roles)
    base_roles.migrar("upgrade", "0017")
    _comprobar_conversion(base_roles, datos)


def _copia_que_falla_despues_de_convertir(base: BaseDeEdificio) -> None:
    original = _MIGRACION.read_text()
    # Copia previa real, aislada del archivo que usa Alembic (L-013).
    carpeta = _MIGRACION.parents[3] / ".git/informes-roles-bloque-a-v2"
    carpeta.mkdir(exist_ok=True)
    (carpeta / "0017-original.py").write_text(original)
    mutante = original.replace(
        '    op.drop_column("asignacion_rol", "nivel")',
        "    op.execute(\"DO $$ BEGIN RAISE EXCEPTION 'fallo tras convertir'; END $$\")\n"
        '    op.drop_column("asignacion_rol", "nivel")',
    )
    assert mutante != original
    (carpeta / "0017-raise.py").write_text(mutante)
    spec = importlib.util.spec_from_file_location(
        "migracion_roles_mutada", carpeta / "0017-raise.py"
    )
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    def conectar() -> psycopg.Connection:
        c = base.conectar_migrador()
        c.autocommit = False
        return c

    motor = create_engine("postgresql+psycopg://", creator=conectar, poolclass=NullPool)
    try:
        with (
            motor.begin() as conexion,
            Operations.context(
                MigrationContext.configure(conexion, opts={"target_metadata": Base.metadata})
            ),
        ):
            modulo.upgrade()
    finally:
        motor.dispose()


def test_error_tras_convertir_revierte_filas_esquema_y_force(base_roles: BaseDeEdificio) -> None:
    datos = _sembrar(base_roles)
    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
    with pytest.raises(Exception, match="fallo tras convertir"):
        _copia_que_falla_despues_de_convertir(base_roles)
    assert _catalogo(base_roles) == catalogo
    assert _filas(base_roles, datos, "nivel") == filas
    with base_roles.conectar_app() as c:
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0016",)


def test_vecino_repetido_aborta_sin_cambiar_nada_ni_publicar_ids(
    base_roles: BaseDeEdificio,
) -> None:
    datos = _sembrar(base_roles)
    admin, complejo, unidad, personas = datos[1]
    with base_roles.conectar_app() as c, c.transaction():
        fijar_tenant(c, admin)
        c.execute(
            "INSERT INTO asignacion_rol (administracion_id,persona_id,rol,complejo_id,unidad_id) "
            "VALUES (%s,%s,'vecino',%s,%s)",
            (admin, personas[4], complejo, unidad),
        )
    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
    with pytest.raises(AssertionError, match="relaciones repetidas: 1") as error:
        base_roles.migrar("upgrade", "0017")
    assert all(str(id_) not in str(error.value) for lote in datos for id_ in lote[:3])
    assert all(str(p) not in str(error.value) for lote in datos for p in lote[3])
    assert "Persona inventada" not in str(error.value)
    assert _catalogo(base_roles) == catalogo
    assert _filas(base_roles, datos, "nivel") == filas
