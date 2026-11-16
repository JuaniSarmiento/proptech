"""H-013 · C12 (parte de migración): la `0041` sube y baja dentro del ciclo de devolución, en su propio
módulo: la base de migraciones es por módulo y otro test que la deje en la `0041` lo volvería inútil (L-086).
"""

from __future__ import annotations

import re
from pathlib import Path

from .._edificios import BaseDeEdificio


# --- C12: el ciclo de la 0041 (L-082: su migración, no "la última") ---------------------------------

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


def test_c12_la_0041_sube_y_baja_en_el_ciclo_de_devolucion(
    base_para_migraciones: BaseDeEdificio, tmp_path: Path
) -> None:
    assert list(_VERSIONES.glob("0041_*.py")), "falta la migración 0041 (tablas de la liquidación)"
    base = base_para_migraciones
    base.roles("antes")
    base.migrar("upgrade", "0040")
    base.roles("despues")
    antes = _dump(base, tmp_path / "0040-antes.sql")
    base.roles("antes")
    base.migrar("upgrade", "0041")
    base.roles("despues")
    assert _version(base) == "0041", "la 0041 no quedó aplicada"
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0040")
    base.roles("despues")
    assert _dump(base, tmp_path / "0040-despues.sql") == antes, "bajar la 0041 no deja el esquema de la 0040"
    base.roles("antes")
    base.migrar("upgrade", "0041")
    base.roles("despues")
    assert _version(base) == "0041"
