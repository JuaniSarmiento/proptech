"""H-018 · C08: la `0044` sube y baja en el ciclo de devolución (L-082, L-086) y deja las tablas de pagos con RLS
forzada (L-064). En su propio módulo, con su propia base (L-086)."""

from __future__ import annotations

import re
from pathlib import Path

from .._edificios import BaseDeEdificio

_VERSIONES = Path(__file__).resolve().parents[3] / "migraciones" / "versions"
TABLAS = ("comprobante_de_pago", "pago_informado", "parte_de_pago", "evento_de_pago", "movimiento_de_pago",
          "cbu_de_unidad")


def _dump(base: BaseDeEdificio, destino: Path) -> str:
    codigo, salida = base.contenedor.exec(["pg_dump", "--schema-only", "-U", base.contenedor.username,
                                           "-d", base.nombre])
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


def _rls(base: BaseDeEdificio) -> dict[str, tuple[bool, bool]]:
    with base.conectar_migrador() as c:
        filas = c.execute(
            "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
            "WHERE relname = ANY(%s) AND relkind = 'r'", (list(TABLAS),)
        ).fetchall()
    return {str(f[0]): (bool(f[1]), bool(f[2])) for f in filas}


def test_c08_la_0044_sube_y_baja_en_el_ciclo_de_devolucion(
    base_para_migraciones: BaseDeEdificio, tmp_path: Path
) -> None:
    assert list(_VERSIONES.glob("0044_*.py")), "falta la migración 0044 (las tablas de pagos)"
    base = base_para_migraciones
    base.roles("antes")
    base.migrar("upgrade", "0043")
    base.roles("despues")
    antes = _dump(base, tmp_path / "0043-antes.sql")
    base.roles("antes")
    base.migrar("upgrade", "0044")
    base.roles("despues")
    assert _version(base) == "0044", "la 0044 no quedó aplicada"
    assert _rls(base) == {t: (True, True) for t in TABLAS}, f"RLS habilitada y forzada en las seis: {_rls(base)}"
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0043")
    base.roles("despues")
    assert _dump(base, tmp_path / "0043-despues.sql") == antes, "bajar la 0044 no deja el esquema de la 0043"
    base.roles("antes")
    base.migrar("upgrade", "0044")
    base.roles("despues")
    assert _version(base) == "0044"
