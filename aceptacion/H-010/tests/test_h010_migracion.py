"""H-010 · C14 (parte de migración): la `0039` sube y baja dentro del ciclo real de devolución de
propiedad, crea `ajuste_de_saldo_inicial` y agrega `ajustar_saldo_inicial` al vocabulario, y bajar
deja el esquema y el vocabulario de la `0038` exactamente como estaban.

L-082: el test prueba **su** migración (`upgrade 0039`, la versión `0039`), nunca "la última".
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion

_VERSIONES = Path(__file__).resolve().parents[3] / "migraciones" / "versions"
ACCION = "ajustar_saldo_inicial"
TABLA = "ajuste_de_saldo_inicial"


def _dump(base: BaseDeEdificio, destino: Path) -> str:
    comando = ["pg_dump", "--schema-only", "-U", base.contenedor.username, "-d", base.nombre]
    codigo, salida = base.contenedor.exec(comando)
    assert codigo == 0
    texto = salida.decode()
    texto = re.sub(r"^\\(?:un)?restrict .*\n", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"^-- Dumped (?:from|by) .*\n", "", texto, flags=re.MULTILINE)
    destino.write_text(texto)
    return texto


def _version(base: BaseDeEdificio) -> str:
    with base.conectar_app() as c:
        fila = c.execute("SELECT version_num FROM alembic_version").fetchone()
        assert fila is not None
        return str(fila[0])


def _vocabulario(base: BaseDeEdificio) -> set[str]:
    with base.conectar_app() as c:
        return {str(f[0]) for f in c.execute("SELECT nombre FROM accion_de_auditoria").fetchall()}


def _existe(base: BaseDeEdificio) -> bool:
    with base.conectar_app() as c:
        fila = c.execute("SELECT to_regclass(%s) IS NOT NULL", (TABLA,)).fetchone()
        return bool(fila and fila[0])


def test_c14_la_0039_sube_y_baja_en_el_ciclo_de_devolucion(
    base_para_migraciones: BaseDeEdificio, tmp_path: Path
) -> None:
    assert list(_VERSIONES.glob("0039_*.py")), "falta la migración 0039 (ajuste de saldo inicial)"
    base = base_para_migraciones
    base.roles("antes")
    base.migrar("upgrade", "0038")
    base.roles("despues")
    antes = _dump(base, tmp_path / "0038-antes.sql")
    vocabulario_antes = _vocabulario(base)
    assert ACCION not in vocabulario_antes and not _existe(base)
    base.roles("antes")
    base.migrar("upgrade", "0039")
    base.roles("despues")
    assert _version(base) == "0039", "la 0039 no quedó aplicada"
    assert _existe(base), f"la 0039 crea {TABLA}"
    assert _vocabulario(base) == vocabulario_antes | {ACCION}, (
        "la 0039 agrega ajustar_saldo_inicial y nada más al vocabulario"
    )
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0038")
    base.roles("despues")
    despues = _dump(base, tmp_path / "0038-despues.sql")
    assert despues == antes, "bajar la 0039 no deja el esquema de la 0038"
    assert _vocabulario(base) == vocabulario_antes, "bajar la 0039 saca la acción del vocabulario"
    base.roles("antes")
    base.migrar("upgrade", "0039")
    base.roles("despues")
    assert _version(base) == "0039"
