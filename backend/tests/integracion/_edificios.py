"""Ayudas del modelo 3a: bases de test aisladas y escrituras como app real."""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg import sql
from testcontainers.community.postgres import PostgresContainer

from ..conftest import (
    APP_PASSWORD_DE_SESION,
    APP_USER_DE_SESION,
    MIGRADOR_PASSWORD_DE_SESION,
    MIGRADOR_USER_DE_SESION,
    RESPALDO_PASSWORD_DE_SESION,
    RESPALDO_USER_DE_SESION,
)


@dataclass(frozen=True)
class BaseDeEdificio:
    contenedor: PostgresContainer
    nombre: str
    entorno: dict[str, str]

    def roles(self, paso: str) -> None:
        entorno = {
            **self.entorno,
            "POSTGRES_USER": self.contenedor.username,
            "POSTGRES_PASSWORD": self.contenedor.password,
            "POSTGRES_APP_USER": APP_USER_DE_SESION,
            "POSTGRES_APP_PASSWORD": APP_PASSWORD_DE_SESION,
            "POSTGRES_RESPALDO_USER": RESPALDO_USER_DE_SESION,
            "POSTGRES_RESPALDO_PASSWORD": RESPALDO_PASSWORD_DE_SESION,
        }
        resultado = subprocess.run(
            [sys.executable, "-m", "proptech_core.compartido.roles", paso],
            cwd=Path(__file__).resolve().parents[2],
            env=entorno,
            capture_output=True,
            text=True,
        )
        assert resultado.returncode == 0, resultado.stdout + resultado.stderr

    def conectar_migrador(self) -> psycopg.Connection:
        return psycopg.connect(
            host=self.contenedor.get_container_host_ip(),
            port=self.contenedor.get_exposed_port(5432),
            dbname=self.nombre,
            user=MIGRADOR_USER_DE_SESION,
            password=MIGRADOR_PASSWORD_DE_SESION,
            autocommit=True,
        )

    def migrar(self, accion: str, revision: str) -> None:
        resultado = subprocess.run(
            ["uv", "run", "alembic", accion, revision],
            cwd=Path(__file__).resolve().parents[2],
            env=self.entorno,
            capture_output=True,
            text=True,
        )
        assert resultado.returncode == 0, resultado.stdout + resultado.stderr

    def devolver_tablas_protegidas(self) -> None:
        """Sólo tests: procedimiento firmado de rollback, rol de arranque explícito."""
        devolver_tablas_protegidas(
            self.contenedor, self.nombre, self.entorno["POSTGRES_MIGRADOR_USER"]
        )

    def conectar_app(self) -> psycopg.Connection:
        return psycopg.connect(
            host=self.contenedor.get_container_host_ip(),
            port=self.contenedor.get_exposed_port(5432),
            dbname=self.nombre,
            user=APP_USER_DE_SESION,
            password=APP_PASSWORD_DE_SESION,
            autocommit=True,
        )


@dataclass(frozen=True)
class Edificios:
    administracion_a: UUID
    administracion_b: UUID
    complejo_a: UUID
    otro_complejo_a: UUID
    complejo_b: UUID
    unidad_a: UUID
    otra_unidad_a: UUID
    unidad_b: UUID


def fijar_tenant(conexion: psycopg.Connection, administracion_id: UUID) -> None:
    conexion.execute(
        "SELECT set_config('app.administracion_id', %s, true)", (str(administracion_id),)
    )


def insertar_unidad(
    conexion: psycopg.Connection,
    administracion_id: UUID,
    complejo_id: UUID,
    identificador: str = "1A",
    *,
    coeficiente: str = "0.100000",
) -> UUID:
    fila = conexion.execute(
        "INSERT INTO unidad (administracion_id, complejo_id, identificador, tipo, piso, "
        "coeficiente, superficie_m2) VALUES (%s, %s, %s, 'departamento', '1', %s, '60.00') "
        "RETURNING id",
        (administracion_id, complejo_id, identificador, coeficiente),
    ).fetchone()
    assert fila is not None
    return UUID(str(fila[0]))


def insertar_grupo(
    conexion: psycopg.Connection,
    administracion_id: UUID,
    complejo_id: UUID,
    clave: str = "ascensor",
    *,
    metodo: str = "coeficiente",
    es_generales: bool = False,
) -> UUID:
    fila = conexion.execute(
        "INSERT INTO grupo_de_reparto (administracion_id, complejo_id, clave, nombre, metodo, "
        "es_generales) VALUES (%s, %s, %s, 'Grupo de prueba', %s, %s) RETURNING id",
        (administracion_id, complejo_id, clave, metodo, es_generales),
    ).fetchone()
    assert fila is not None
    return UUID(str(fila[0]))


def insertar_miembro(
    conexion: psycopg.Connection,
    administracion_id: UUID,
    complejo_id: UUID,
    grupo_id: UUID,
    unidad_id: UUID,
    *,
    modo: str = "renormalizado",
    coeficiente: str | None = None,
) -> None:
    conexion.execute(
        "INSERT INTO grupo_unidad (administracion_id, complejo_id, grupo_id, unidad_id, "
        "modo_de_coeficientes, coeficiente) VALUES (%s, %s, %s, %s, %s, %s)",
        (administracion_id, complejo_id, grupo_id, unidad_id, modo, coeficiente),
    )


def devolver_tablas_protegidas(contenedor: PostgresContainer, base: str, migrador: str) -> None:
    """Sólo tests: procedimiento firmado de rollback, rol de arranque explícito.

    Después de `roles despues` las tablas de sólo agregar son del rol de
    arranque y el migrador ya no puede bajarlas: esto se las devuelve antes
    de un `alembic downgrade`, igual que el Migration Plan (D-114.5).
    """
    from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

    with psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=contenedor.username,
        password=contenedor.password,
        dbname=base,
        autocommit=True,
    ) as conexion:
        for tabla in TABLAS_DE_SOLO_AGREGAR:
            fila = conexion.execute("SELECT to_regclass(%s)", (f"public.{tabla}",)).fetchone()
            if fila is None or fila[0] is None:
                continue
            conexion.execute(
                sql.SQL("ALTER TABLE {} OWNER TO {}").format(
                    sql.Identifier("public", tabla), sql.Identifier(migrador)
                )
            )
            funciones = conexion.execute(
                "SELECT DISTINCT p.proname FROM pg_trigger t "
                "JOIN pg_proc p ON p.oid=t.tgfoid "
                "WHERE t.tgrelid=to_regclass(%s) AND NOT t.tgisinternal",
                (f"public.{tabla}",),
            ).fetchall()
            for funcion in funciones:
                conexion.execute(
                    sql.SQL("ALTER FUNCTION {}() OWNER TO {}").format(
                        sql.Identifier("public", funcion[0]), sql.Identifier(migrador)
                    )
                )
