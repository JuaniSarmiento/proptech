"""H-032 (4d): la `0052_prorrateo_de_cambio` crea las dos tablas de sólo agregar (el prorrateo es
único por unidad y período), baja vacía y sube sobre una base ya desplegada: sus claves foráneas
referencian `cambio_de_titular` y por eso declara `PRESTA_PROPIEDAD` (`roles antes`, D-115.3). Va en
su propio módulo (su propia base). Prueba **su** migración (L-082).
"""

from __future__ import annotations

import pytest

from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion

TABLAS = ("prorrateo_de_cambio", "prorrateo_aplicado")


def _version(base: BaseDeEdificio) -> tuple[object, ...]:
    with base.conectar_migrador() as c:
        return tuple(c.execute("SELECT version_num FROM alembic_version").fetchone() or ())


def _existe(base: BaseDeEdificio, tabla: str) -> bool:
    with base.conectar_migrador() as c:
        fila = c.execute("SELECT to_regclass(%s) IS NOT NULL", (tabla,)).fetchone()
        return bool(fila and fila[0])


def test_la_0052_crea_las_tablas_con_la_unicidad_por_unidad_y_periodo(
    base_del_edificio: BaseDeEdificio,
) -> None:
    assert all(_existe(base_del_edificio, t) for t in TABLAS)
    with base_del_edificio.conectar_migrador() as c:
        unicas = {
            fila[0]
            for fila in c.execute(
                "SELECT conname FROM pg_constraint WHERE contype = 'u' "
                "AND conrelid = 'prorrateo_de_cambio'::regclass"
            ).fetchall()
        }
        forzadas = c.execute(
            "SELECT relname FROM pg_class WHERE relname = ANY(%s) AND relforcerowsecurity",
            (list(TABLAS),),
        ).fetchall()
    assert "uq_prorrateo_unidad_periodo" in unicas
    assert {f[0] for f in forzadas} == set(TABLAS), "RLS forzada en las dos"


def test_baja_vacia_sube_y_vuelve_a_subir_sobre_una_base_ya_desplegada(
    base_del_edificio: BaseDeEdificio,
) -> None:
    base = base_del_edificio
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0051")
    assert _version(base) == ("0051",)
    assert not any(_existe(base, t) for t in TABLAS), "bajar la 0052 no sacó las tablas"
    with base.conectar_migrador() as c:
        for tabla in TABLAS:
            assert c.execute(
                "SELECT to_regprocedure(%s)", (f"fn_{tabla}_bloqueada()",)
            ).fetchone() == (None,), "la función del trigger quedó"
    # Como en una base desplegada: `roles antes` presta `cambio_de_titular` para las FK.
    base.roles("antes")
    base.migrar("upgrade", "0052")
    base.roles("despues")
    assert _version(base) == ("0052",)
    assert all(_existe(base, t) for t in TABLAS)
