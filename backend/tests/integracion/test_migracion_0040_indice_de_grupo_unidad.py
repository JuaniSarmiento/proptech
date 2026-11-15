"""H-011 (change 7): la `0040_indice_de_grupo_unidad` crea el índice de DBA-2 sobre
`grupo_unidad (administracion_id, complejo_id, grupo_id)` y baja sin dejarlo.

L-082: prueba **su** migración (`downgrade 0039` / `upgrade 0040`), nunca "la última".
"""

from __future__ import annotations

import pytest

from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion

INDICE = "ix_grupo_unidad_edificio"


def _columnas(base: BaseDeEdificio) -> list[str] | None:
    with base.conectar_migrador() as c:
        fila = c.execute(
            "SELECT array_agg(a.attname::text ORDER BY k.ord) FROM pg_index i "
            "JOIN pg_class ic ON ic.oid = i.indexrelid "
            "CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord) "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.attnum "
            "WHERE ic.relname = %s",
            (INDICE,),
        ).fetchone()
        return None if fila is None else fila[0]


def test_la_0040_crea_el_indice_por_edificio(base_del_edificio: BaseDeEdificio) -> None:
    assert _columnas(base_del_edificio) == ["administracion_id", "complejo_id", "grupo_id"]


def test_baja_sin_el_indice_y_sube_de_nuevo(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0039")
    assert _columnas(base) is None, "bajar la 0040 no sacó el índice"
    base.roles("antes")
    base.migrar("upgrade", "0040")
    base.roles("despues")
    assert _columnas(base) == ["administracion_id", "complejo_id", "grupo_id"]
