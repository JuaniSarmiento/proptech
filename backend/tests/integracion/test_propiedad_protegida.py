"""D1: deploy desde 3a, atomicidad y rollback explícito del umbral."""

import shutil
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from psycopg import sql

from ._edificios import BaseDeEdificio
from .test_umbral_migracion import arranque, insertar

pytestmark = pytest.mark.integracion


def devolver_configuracion(base: BaseDeEdificio) -> None:
    with arranque(base) as c:
        c.execute(
            sql.SQL("ALTER TABLE configuracion_versionada OWNER TO {}").format(
                sql.Identifier(base.entorno["POSTGRES_MIGRADOR_USER"])
            )
        )
        c.execute(
            sql.SQL("ALTER FUNCTION fn_configuracion_versionada_bloqueada() OWNER TO {}").format(
                sql.Identifier(base.entorno["POSTGRES_MIGRADOR_USER"])
            )
        )


def test_deploy_3a_y_rollback(base_para_migraciones: BaseDeEdificio) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "0020")
    devolver_configuracion(base)
    base.roles("antes")
    base.migrar("upgrade", "head")
    with arranque(base) as c:
        admin, complejo, persona = uuid4(), uuid4(), uuid4()
        c.execute("INSERT INTO administracion (id,nombre) VALUES (%s,'Ficticia')", (admin,))
        c.execute(
            ("INSERT INTO persona (id,administracion_id,nombre) VALUES (%s,%s,'Ficticia')"),
            (persona, admin),
        )
        c.execute(
            "INSERT INTO complejo (id,administracion_id,nombre,localidad) VALUES "
            "(%s,%s,'Ficticio','Mendoza')",
            (complejo, admin),
        )
        insertar(c, admin, complejo, persona, date(2026, 11, 1), "300.00")
    base.roles("despues")
    base.roles("antes")
    with arranque(base) as c:
        assert c.execute(
            "SELECT tableowner FROM pg_tables WHERE schemaname='public' AND "
            "tablename='configuracion_versionada'"
        ).fetchone() == (base.contenedor.username,)
        assert c.execute(
            "SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE "
            "oid='fn_configuracion_versionada_bloqueada()'::regprocedure"
        ).fetchone() == (base.contenedor.username,)
    with pytest.raises(AssertionError, match="must be owner"):
        base.migrar("downgrade", "0020")
    devolver_configuracion(base)
    base.migrar("downgrade", "0020")
    base.migrar("upgrade", "head")
    with arranque(base) as c:
        assert c.execute("SELECT umbral_saldo_chico FROM configuracion_versionada").fetchall() == [
            (Decimal("500.00"),)
        ]
    base.roles("despues")


def test_migracion_futura_revierte_todo(
    base_para_migraciones: BaseDeEdificio, tmp_path: Path
) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "head")
    base.roles("despues")
    raiz = Path(__file__).resolve().parents[2]
    copia = tmp_path / "migraciones"
    shutil.copytree(raiz / "migraciones", copia)
    (copia / "versions" / "0026_sonda.py").write_text("""from alembic import op
revision = '0026'
down_revision = '0025'
def upgrade():
    op.execute('CREATE TABLE sonda_atomica (id int)')
    op.execute('ALTER TABLE configuracion_versionada ADD COLUMN no_debe_quedar int')
def downgrade():
    pass
""")
    ini = tmp_path / "alembic.ini"
    ini.write_text(
        (raiz / "alembic.ini")
        .read_text()
        .replace("script_location = migraciones", f"script_location = {copia}")
    )
    r = subprocess.run(
        ["uv", "run", "alembic", "-c", str(ini), "upgrade", "head"],
        cwd=raiz,
        env=base.entorno,
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0 and "must be owner" in r.stderr
    with arranque(base) as c:
        assert c.execute("SELECT to_regclass('public.sonda_atomica')").fetchone() == (None,)
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0025",)
