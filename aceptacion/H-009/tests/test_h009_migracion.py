"""H-009 · C13 (parte de migración): la `0038` sube y baja dentro del ciclo real de devolución de
propiedad, agrega `confirmar_saldos_iniciales` al vocabulario de auditoría, y bajar deja el
esquema y el vocabulario de la `0037` exactamente como estaban.

L-082: el test prueba **su** migración (`upgrade 0038`, la versión `0038`), nunca "la última": una
historia posterior que agregue la `0039` no lo vuelve rojo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion

_VERSIONES = Path(__file__).resolve().parents[3] / "migraciones" / "versions"
ACCION = "confirmar_saldos_iniciales"


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


def test_c13_la_0038_sube_y_baja_en_el_ciclo_de_devolucion(
    base_para_migraciones: BaseDeEdificio, tmp_path: Path
) -> None:
    assert list(_VERSIONES.glob("0038_*.py")), "falta la migración 0038 (confirmar saldos)"
    base = base_para_migraciones
    base.roles("antes")
    base.migrar("upgrade", "0037")
    base.roles("despues")
    antes = _dump(base, tmp_path / "0037-antes.sql")
    vocabulario_antes = _vocabulario(base)
    assert ACCION not in vocabulario_antes
    base.roles("antes")
    base.migrar("upgrade", "0038")
    base.roles("despues")
    assert _version(base) == "0038", "la 0038 no quedó aplicada"
    assert _vocabulario(base) == vocabulario_antes | {ACCION}, (
        "la 0038 agrega confirmar_saldos_iniciales y nada más al vocabulario"
    )
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0037")
    base.roles("despues")
    despues = _dump(base, tmp_path / "0037-despues.sql")
    assert despues == antes, "bajar la 0038 no deja el esquema de la 0037"
    assert _vocabulario(base) == vocabulario_antes, "bajar la 0038 saca la acción del vocabulario"
    base.roles("antes")
    base.migrar("upgrade", "0038")
    base.roles("despues")
    assert _version(base) == "0038"
