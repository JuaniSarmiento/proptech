"""Rollback vacío, conservación de datos y dump completo del esquema 0022 (1.1/1.4)."""

import re
from pathlib import Path

import pytest
from psycopg import sql

from ._edificios import BaseDeEdificio
from ._libro import LIBRO, sembrar_libro
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion


def devolver_libro(base: BaseDeEdificio) -> None:
    with arranque(base) as c:
        for tabla in LIBRO:
            c.execute(
                sql.SQL("ALTER TABLE {} OWNER TO proptech_migrador").format(sql.Identifier(tabla))
            )
            c.execute(
                sql.SQL("ALTER FUNCTION {}() OWNER TO proptech_migrador").format(
                    sql.Identifier(f"fn_{tabla}_bloqueada")
                )
            )


def dump(base: BaseDeEdificio, destino: Path) -> str:
    comando = ["pg_dump", "--schema-only", "-U", base.contenedor.username, "-d", base.nombre]
    codigo, salida = base.contenedor.exec(comando)
    assert codigo == 0
    texto = salida.decode()
    # PG18 usa tokens aleatorios de psql. No se filtra DDL ni ACL.
    texto = re.sub(r"^\\(?:un)?restrict .*\n", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"^-- Dumped (?:from|by) .*\n", "", texto, flags=re.MULTILINE)
    destino.write_text(texto)
    print(f"DUMP: {' '.join(comando)} -> {destino}")
    return texto


def test_ciclo_0022_0023_0022_conserva_esquema(
    base_para_migraciones: BaseDeEdificio, tmp_path: Path
) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "0022")
    base.roles("despues")
    antes = dump(base, tmp_path / "0022-antes.sql")
    base.roles("antes")
    base.migrar("upgrade", "head")
    base.roles("despues")
    devolver_libro(base)
    base.migrar("downgrade", "0022")
    despues = dump(base, tmp_path / "0022-despues.sql")
    assert despues == antes
    base.roles("antes")
    base.migrar("upgrade", "head")
    base.roles("despues")
    with base.conectar_app() as c:
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0023",)
        for tabla in LIBRO:
            assert c.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(tabla))
            ).fetchone() == (0,)


def test_downgrade_con_fila_conserva_el_libro(base_para_migraciones: BaseDeEdificio) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "head")
    base.roles("despues")
    with base.conectar_app() as c, c.transaction():
        datos = sembrar_libro(c)
        cuenta = datos.cuenta
    devolver_libro(base)
    rechazo = None
    try:
        base.migrar("downgrade", "0022")
    except AssertionError as e:
        rechazo = str(e)
    with arranque(base) as c:
        tabla = c.execute("SELECT to_regclass('public.cuenta') IS NOT NULL").fetchone()
        assert tabla == (True,), (
            "el downgrade borró el libro con filas, invisible al dueño por FORCE sin tenant"
        )
        assert c.execute("SELECT count(*) FROM cuenta WHERE id=%s", (cuenta,)).fetchone() == (1,)
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0023",)
    assert rechazo is not None and "tiene filas" in rechazo
    base.roles("despues")
