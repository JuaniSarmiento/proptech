"""RF: 0028 sube, baja y vuelve a subir el vocabulario `ver_personal`
(2d, grupo 7, tarea 7.1, D13/E11); la bajada con una fila de `auditoria`
que lo use falla por FK (23503) sin tocar nada (D9). Mismo patrón que
`test_migracion_0024_vocabulario.py`.
"""

import uuid

import pytest

from ._edificios import BaseDeEdificio
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion


def _vocabulario(base: BaseDeEdificio) -> list[tuple[str]]:
    with base.conectar_migrador() as c:
        return c.execute(
            "SELECT nombre FROM accion_de_auditoria WHERE nombre='ver_personal'"
        ).fetchall()


def _version(base: BaseDeEdificio) -> tuple[str] | None:
    with base.conectar_migrador() as c:
        fila = c.execute("SELECT version_num FROM alembic_version").fetchone()
        return None if fila is None else (str(fila[0]),)


def test_rf_0028_down_up_vocabulario(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    assert _vocabulario(base) == [("ver_personal",)]
    base.migrar("downgrade", "0027")
    assert _version(base) == ("0027",)
    assert _vocabulario(base) == []
    base.migrar("upgrade", "0028")
    assert _version(base) == ("0028",)
    assert _vocabulario(base) == [("ver_personal",)]
    base.roles("despues")


def test_rf_0028_bajada_con_fila_de_auditoria_falla_por_fk(
    base_del_edificio: BaseDeEdificio,
) -> None:
    base = base_del_edificio
    anterior_vocabulario = _vocabulario(base)
    anterior_version = _version(base)
    with arranque(base) as c:
        c.execute(
            "INSERT INTO auditoria (administracion_id,persona_id,accion,entidad,"
            "entidad_id,request_id) VALUES (%s,%s,%s,'persona',%s,%s)",
            (uuid.uuid4(), uuid.uuid4(), "ver_personal", uuid.uuid4(), uuid.uuid4()),
        )
        fila_antes = c.execute(
            "SELECT count(*) FROM auditoria WHERE accion='ver_personal'"
        ).fetchone()
    assert fila_antes == (1,)
    with pytest.raises(AssertionError, match=r"23503|ForeignKeyViolation"):
        base.migrar("downgrade", "0027")
    assert _vocabulario(base) == anterior_vocabulario
    assert _version(base) == anterior_version
    with arranque(base) as c:
        assert c.execute(
            "SELECT count(*) FROM auditoria WHERE accion='ver_personal'"
        ).fetchone() == (1,)
