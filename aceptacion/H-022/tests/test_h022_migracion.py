"""H-022 · C07: la migración que siembra `interes_por_reversion` sube y baja (L-089). En su propio módulo, con su
propia base (L-086)."""

from __future__ import annotations

import re
from pathlib import Path

from .._edificios import BaseDeEdificio

# --- C07: la migración del tipo nuevo ------------------------------------------------------------------

_VERSIONES = Path(__file__).resolve().parents[3] / "migraciones" / "versions"


def _migracion_del_tipo() -> tuple[str, str]:
    for archivo in sorted(_VERSIONES.glob("00*.py")):
        texto = archivo.read_text()
        # La que lo siembra en el vocabulario, no la que sólo lo nombra (la 0044 lo admite como papel).
        if re.search(r"INSERT INTO\s+(?:public\.)?tipo_de_movimiento[^;]*interes_por_reversion", texto, flags=re.S):
            revision = re.search(r'^revision\s*(?::[^=]+)?=\s*"([^"]+)"', texto, flags=re.M)
            anterior = re.search(r'^down_revision\s*(?::[^=]+)?=\s*"([^"]+)"', texto, flags=re.M)
            assert revision and anterior, f"{archivo.name} no tiene revision y down_revision legibles"
            return revision.group(1), anterior.group(1)
    raise AssertionError("ninguna migración siembra `interes_por_reversion`")


def _dump(base: BaseDeEdificio, destino: Path) -> str:
    codigo, salida = base.contenedor.exec(["pg_dump", "-U", base.contenedor.username, "-d", base.nombre,
                                           "--table=tipo_de_movimiento", "--data-only", "--inserts"])
    assert codigo == 0
    texto = "\n".join(sorted(l for l in salida.decode().splitlines() if l.startswith("INSERT")))
    destino.write_text(texto)
    return texto


def test_c07_la_migracion_del_tipo_sube_y_baja(base_para_migraciones: BaseDeEdificio, tmp_path: Path) -> None:
    revision, anterior = _migracion_del_tipo()
    base = base_para_migraciones
    base.roles("antes")
    base.migrar("upgrade", anterior)
    base.roles("despues")
    antes = _dump(base, tmp_path / "antes.sql")
    assert "interes_por_reversion" not in antes
    base.roles("antes")
    base.migrar("upgrade", revision)
    base.roles("despues")
    assert "'interes_por_reversion', 'debito'" in _dump(base, tmp_path / "con.sql"), "el tipo nuevo es un débito"
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", anterior)
    base.roles("despues")
    assert _dump(base, tmp_path / "despues.sql") == antes, "bajar la migración no deja el vocabulario de antes"
