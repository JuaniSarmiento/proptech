"""RF: 0024 baja y sube sin auditoría, y su vocabulario se va y vuelve."""

import pytest

from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion


def _vocabulario(base: BaseDeEdificio) -> list[tuple[str]]:
    with base.conectar_migrador() as c:
        return c.execute(
            "SELECT nombre FROM accion_de_auditoria WHERE nombre='corregir_movimiento'"
        ).fetchall()


def _version(base: BaseDeEdificio) -> tuple[str] | None:
    with base.conectar_migrador() as c:
        fila = c.execute("SELECT version_num FROM alembic_version").fetchone()
        return None if fila is None else (str(fila[0]),)


def test_rf_0024_down_up_vocabulario(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    assert _vocabulario(base) == [("corregir_movimiento",)]
    base.migrar("downgrade", "0023")
    assert _version(base) == ("0023",)
    assert _vocabulario(base) == []
    base.migrar("upgrade", "0024")
    assert _version(base) == ("0024",)
    assert _vocabulario(base) == [("corregir_movimiento",)]
    base.roles("despues")
