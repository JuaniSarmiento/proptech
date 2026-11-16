"""H-014 · C10 (parte de migración): la `0042` sube y baja dentro del ciclo de devolución (L-082)."""

from __future__ import annotations

import re
from pathlib import Path

from .._edificios import BaseDeEdificio


# --- C10: el ciclo de la 0042 (L-082: su migración, no "la última") ---------------------------------

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


def test_c10_la_0042_sube_y_baja_en_el_ciclo_de_devolucion(
    base_para_migraciones: BaseDeEdificio, tmp_path: Path
) -> None:
    assert list(_VERSIONES.glob("0042_*.py")), "falta la migración 0042 (evento distribuida y cargo cobrado de menos)"
    base = base_para_migraciones
    base.roles("antes")
    base.migrar("upgrade", "0041")
    base.roles("despues")
    antes = _dump(base, tmp_path / "0041-antes.sql")
    base.roles("antes")
    base.migrar("upgrade", "0042")
    base.roles("despues")
    assert _version(base) == "0042", "la 0042 no quedó aplicada"
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0041")
    base.roles("despues")
    assert _dump(base, tmp_path / "0041-despues.sql") == antes, "bajar la 0042 no deja el esquema de la 0041"
    base.roles("antes")
    base.migrar("upgrade", "0042")
    base.roles("despues")
    assert _version(base) == "0042"
