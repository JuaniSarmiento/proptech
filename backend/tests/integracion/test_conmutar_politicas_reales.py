"""H-003 B1: `conmutar.sh` compara las políticas de Row-Level Security de la
base destino con las de la base en uso contra PostgreSQL REAL (testcontainers).
Una consulta que ignore los roles o el modo permisivo/restrictivo acepta un
destino cuya seguridad deja ver filas que antes estaban bloqueadas. Sólo el
`docker compose exec ... psql` se sustituye por un `docker` falso que reenvía
el SQL a la base real (nunca se toca el Docker real ni un stack levantado)."""

# ruff: noqa: S106  (contraseña del contenedor efímero de este test, nunca real)
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

RAIZ = Path(__file__).resolve().parents[3]
SCRIPT = RAIZ / "infra" / "respaldos" / "conmutar.sh"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32"
    or subprocess.run(["docker", "info"], capture_output=True, check=False).returncode != 0,
    reason="requiere Docker y semántica POSIX",
)

DOCKER_FALSO = """#!/usr/bin/env python3
import os, sys
import psycopg
a = sys.argv
s = " ".join(a)
if "psql" in a:
    with psycopg.connect(
        host=os.environ["PG_HOST"], port=os.environ["PG_PORT"], user="prueba",
        password="prueba", dbname=a[a.index("-d") + 1], autocommit=True,
    ) as conn:
        for fila in conn.execute(a[a.index("-tAc") + 1]).fetchall():
            print("|".join("t" if x is True else "f" if x is False else str(x) for x in fila))
elif "printenv POSTGRES_DB" in s:
    print("proptech_original")
elif "printenv POSTGRES_USER" in s:
    print("prueba")
elif "alembic heads" in s:
    print("0036 (head)")
"""

PREPARAR = (
    "CREATE TABLE alembic_version(version_num text); INSERT INTO alembic_version VALUES ('0036');"
    "CREATE TABLE datos(id int, edificio int); INSERT INTO datos VALUES (1, 1);"
    "GRANT SELECT ON datos TO app, otro;"
    "ALTER TABLE datos ENABLE ROW LEVEL SECURITY; ALTER TABLE datos FORCE ROW LEVEL SECURITY;"
)


@pytest.fixture(scope="module")
def pg() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        "postgres:18.6-trixie", username="prueba", password="prueba", dbname="prueba"
    ) as contenedor:
        with psycopg.connect(
            host=contenedor.get_container_host_ip(),
            port=contenedor.get_exposed_port(5432),
            user="prueba",
            password="prueba",
            dbname="prueba",
            autocommit=True,
        ) as admin:
            admin.execute('CREATE ROLE app; CREATE ROLE otro; CREATE ROLE "app,otro"')
        yield contenedor


def _base(pg: PostgresContainer, nombre: str, politicas: str) -> None:
    with psycopg.connect(
        host=pg.get_container_host_ip(),
        port=pg.get_exposed_port(5432),
        user="prueba",
        password="prueba",
        dbname="prueba",
        autocommit=True,
    ) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {nombre}")
        admin.execute(f"CREATE DATABASE {nombre}")
    with psycopg.connect(
        host=pg.get_container_host_ip(),
        port=pg.get_exposed_port(5432),
        user="prueba",
        password="prueba",
        dbname=nombre,
        autocommit=True,
    ) as conn:
        conn.execute(PREPARAR + politicas)


def _conmutar(pg: PostgresContainer, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    for nombre, cuerpo in (("docker", DOCKER_FALSO), ("sleep", "#!/bin/sh\nexit 0\n")):
        ruta = bin_ / nombre
        ruta.write_text(cuerpo)
        ruta.chmod(0o755)
    infra = tmp_path / "infra"
    infra.mkdir(exist_ok=True)
    (infra / ".env").write_text("POSTGRES_DB=proptech_original\n")
    entorno = dict(
        os.environ,
        PATH=f"{bin_}:{os.environ['PATH']}",
        CONMUTAR_INFRA_DIR=str(infra),
        PROPTECH_COMPOSE_PROYECTO="proptech-prueba",
        PG_HOST=pg.get_container_host_ip(),
        PG_PORT=str(pg.get_exposed_port(5432)),
    )
    return subprocess.run(
        ["bash", str(SCRIPT), "proptech_destino"],
        env=entorno,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )


POLITICA_BASE = (
    "CREATE POLICY permitir ON datos TO app USING (true);"
    "CREATE POLICY aislar ON datos AS RESTRICTIVE TO app USING (false);"
)


class TestConmutarComparaLaDefinicionCompleta:
    def test_politicas_identicas_se_aceptan(self, pg: PostgresContainer, tmp_path: Path) -> None:
        _base(pg, "proptech_original", POLITICA_BASE)
        _base(pg, "proptech_destino", POLITICA_BASE)
        resultado = _conmutar(pg, tmp_path)
        assert resultado.returncode == 0, resultado.stderr

    def test_politica_restrictiva_vuelta_permisiva_se_rechaza(
        self, pg: PostgresContainer, tmp_path: Path
    ) -> None:
        _base(pg, "proptech_original", POLITICA_BASE)
        _base(
            pg,
            "proptech_destino",
            "CREATE POLICY permitir ON datos TO app USING (true);"
            "CREATE POLICY aislar ON datos AS PERMISSIVE TO app USING (false);",
        )
        resultado = _conmutar(pg, tmp_path)
        assert resultado.returncode != 0, resultado.stdout
        assert "seguridad de filas" in resultado.stderr

    def test_politica_con_otros_roles_se_rechaza(
        self, pg: PostgresContainer, tmp_path: Path
    ) -> None:
        _base(pg, "proptech_original", POLITICA_BASE)
        _base(
            pg,
            "proptech_destino",
            "CREATE POLICY permitir ON datos TO otro USING (true);"
            "CREATE POLICY aislar ON datos AS RESTRICTIVE TO app USING (false);",
        )
        resultado = _conmutar(pg, tmp_path)
        assert resultado.returncode != 0, resultado.stdout
        assert "seguridad de filas" in resultado.stderr

    def test_politica_con_otra_expresion_se_rechaza(
        self, pg: PostgresContainer, tmp_path: Path
    ) -> None:
        _base(pg, "proptech_original", POLITICA_BASE)
        _base(
            pg,
            "proptech_destino",
            "CREATE POLICY permitir ON datos TO app USING (edificio = 1);"
            "CREATE POLICY aislar ON datos AS RESTRICTIVE TO app USING (false);",
        )
        resultado = _conmutar(pg, tmp_path)
        assert resultado.returncode != 0, resultado.stdout
        assert "seguridad de filas" in resultado.stderr

    def test_rol_con_coma_no_se_confunde_con_dos_roles(
        self, pg: PostgresContainer, tmp_path: Path
    ) -> None:
        # Un rol llamado "app,otro" y los roles `app` y `otro` no pueden dar el
        # mismo resumen: en el destino `app` pasaría a ver filas (H-003, B1).
        _base(pg, "proptech_original", 'CREATE POLICY p ON datos TO "app,otro" USING (true);')
        _base(pg, "proptech_destino", "CREATE POLICY p ON datos TO app, otro USING (true);")
        resultado = _conmutar(pg, tmp_path)
        assert resultado.returncode != 0, resultado.stdout
        assert "seguridad de filas" in resultado.stderr

    def test_nombre_de_politica_fabricado_no_oculta_una_restrictiva_faltante(
        self, pg: PostgresContainer, tmp_path: Path
    ) -> None:
        # H-003 vuelta 4, B1: un nombre con los separadores del resumen no puede
        # hacer pasar una base con una restrictiva menos por la original.
        _base(
            pg,
            "proptech_original",
            "CREATE POLICY p ON datos AS RESTRICTIVE USING (false);"
            "CREATE POLICY q ON datos USING (true);",
        )
        _base(
            pg,
            "proptech_destino",
            'CREATE POLICY "p|*|false|PUBLIC|false|;q" ON datos USING (true);',
        )
        resultado = _conmutar(pg, tmp_path)
        assert resultado.returncode != 0, resultado.stdout
        assert "seguridad de filas" in resultado.stderr
