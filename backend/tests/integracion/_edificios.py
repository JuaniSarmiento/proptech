"""Ayudas del modelo 3a: bases de test aisladas y escrituras como app real."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import psycopg
from testcontainers.community.postgres import PostgresContainer

from ..conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION


@dataclass(frozen=True)
class BaseDeEdificio:
    contenedor: PostgresContainer
    nombre: str
    entorno: dict[str, str]

    def migrar(self, accion: str, revision: str) -> None:
        resultado = subprocess.run(
            ["uv", "run", "alembic", accion, revision],
            cwd=Path(__file__).resolve().parents[2],
            env=self.entorno,
            capture_output=True,
            text=True,
        )
        assert resultado.returncode == 0, resultado.stdout + resultado.stderr

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
) -> None:
    conexion.execute(
        "INSERT INTO grupo_unidad (administracion_id, complejo_id, grupo_id, unidad_id) "
        "VALUES (%s, %s, %s, %s)",
        (administracion_id, complejo_id, grupo_id, unidad_id),
    )
