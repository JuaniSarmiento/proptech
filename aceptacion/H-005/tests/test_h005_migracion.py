"""H-005 · C20 (parte de esquema): la `0035` sube y baja dentro del ciclo real de devolución de
propiedad, y bajar deja el esquema de la `0034` exactamente como estaba."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion


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


def test_c20_la_0035_sube_y_baja_en_el_ciclo_de_devolucion(
    base_para_migraciones: BaseDeEdificio, tmp_path: Path
) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "0034")
    base.roles("despues")
    antes = _dump(base, tmp_path / "0034-antes.sql")
    base.roles("antes")
    base.migrar("upgrade", "head")
    base.roles("despues")
    assert _version(base) == "0035", "la cabeza no es la 0035"
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0034")
    base.roles("despues")
    despues = _dump(base, tmp_path / "0034-despues.sql")
    assert "carga_de_saldo_inicial" not in despues and "origen_de_saldo_inicial" not in despues
    assert despues == antes, "bajar la 0035 no deja el esquema de la 0034"
    base.roles("antes")
    base.migrar("upgrade", "head")
    base.roles("despues")
    assert _version(base) == "0035"
