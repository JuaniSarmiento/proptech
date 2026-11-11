"""H-007 · C18 (parte de migración): la `0036` sube y baja dentro del ciclo real de devolución de
propiedad, y bajar deja el esquema de la `0035` exactamente como estaba.

L-082: el test prueba **su** migración (`upgrade 0036`, la versión `0036`), nunca "la última": una
historia posterior que agregue la `0037` no lo vuelve rojo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion

_VERSIONES = Path(__file__).resolve().parents[3] / "migraciones" / "versions"


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


def test_c18_la_0036_sube_y_baja_en_el_ciclo_de_devolucion(
    base_para_migraciones: BaseDeEdificio, tmp_path: Path
) -> None:
    assert list(_VERSIONES.glob("0036_*.py")), "falta la migración 0036 (importacion)"
    base = base_para_migraciones
    base.roles("antes")
    base.migrar("upgrade", "0035")
    base.roles("despues")
    antes = _dump(base, tmp_path / "0035-antes.sql")
    base.roles("antes")
    base.migrar("upgrade", "0036")
    base.roles("despues")
    assert _version(base) == "0036", "la 0036 no quedó aplicada"
    assert "CREATE TABLE public.importacion" in _dump(base, tmp_path / "0036.sql")
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0035")
    base.roles("despues")
    despues = _dump(base, tmp_path / "0035-despues.sql")
    assert "CREATE TABLE public.importacion " not in despues
    assert despues == antes, "bajar la 0036 no deja el esquema de la 0035"
    base.roles("antes")
    base.migrar("upgrade", "0036")
    base.roles("despues")
    assert _version(base) == "0036"
