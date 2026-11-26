"""H-030 (4d): la `0050_cambio_de_titular` crea las dos tablas de sólo agregar con su vocabulario
cerrado y sus FK compuestas, suma la acción de auditoría, sube también sobre una base ya desplegada
(L-089) y no baja con filas. Va en su propio módulo (su propia base). Prueba **su** migración
(L-082).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import psycopg
import pytest

from ._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad

pytestmark = pytest.mark.integracion

ACCION = "registrar_cambio_de_titular"
TABLAS = ("cambio_de_titular", "parte_de_cambio_de_titular")


def _version(base: BaseDeEdificio) -> tuple[object, ...]:
    with base.conectar_migrador() as c:
        return tuple(c.execute("SELECT version_num FROM alembic_version").fetchone() or ())


def _existe(base: BaseDeEdificio, tabla: str) -> bool:
    with base.conectar_migrador() as c:
        fila = c.execute("SELECT to_regclass(%s) IS NOT NULL", (tabla,)).fetchone()
        return bool(fila and fila[0])


def _accion(base: BaseDeEdificio) -> list[tuple[object, ...]]:
    with base.conectar_migrador() as c:
        return c.execute(
            "SELECT nombre FROM accion_de_auditoria WHERE nombre = %s", (ACCION,)
        ).fetchall()


def test_la_0050_crea_las_tablas_y_la_accion(base_del_edificio: BaseDeEdificio) -> None:
    for tabla in TABLAS:
        assert _existe(base_del_edificio, tabla), f"la 0050 no creó {tabla}"
    assert _accion(base_del_edificio) == [(ACCION,)]


def test_baja_vacia_sube_y_vuelve_a_subir_sobre_una_base_ya_desplegada(
    base_del_edificio: BaseDeEdificio,
) -> None:
    base = base_del_edificio
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0049")
    assert _version(base) == ("0049",)
    assert not any(_existe(base, t) for t in TABLAS), "bajar la 0050 no sacó las tablas"
    assert _accion(base) == [], "bajar la 0050 no sacó la acción"
    with base.conectar_migrador() as c:
        for tabla in TABLAS:
            assert c.execute(
                "SELECT to_regprocedure(%s)", (f"fn_{tabla}_bloqueada()",)
            ).fetchone() == (None,), "la función del trigger quedó"
    # L-089: sube sin `roles antes`, con los roles ya devueltos como en una base desplegada.
    base.roles("despues")
    base.migrar("upgrade", "0050")
    base.roles("despues")
    assert _version(base) == ("0050",)
    assert all(_existe(base, t) for t in TABLAS) and _accion(base) == [(ACCION,)]


def _mundo(c: psycopg.Connection) -> tuple[UUID, UUID, UUID, UUID, UUID, UUID]:
    """(administración, edificio, otro edificio, unidad, unidad del otro edificio, persona)."""
    admin, edificio, otro, persona = uuid4(), uuid4(), uuid4(), uuid4()
    fijar_tenant(c, admin)
    c.execute(
        "INSERT INTO administracion (id, nombre) VALUES (%s, 'Administración Ficticia')", (admin,)
    )
    c.execute(
        "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'Pía')",
        (persona, admin),
    )
    for complejo, nombre in ((edificio, "Torre"), (otro, "Otra")):
        c.execute(
            "INSERT INTO complejo (id, administracion_id, nombre, localidad, pisos, subsuelos) "
            "VALUES (%s, %s, %s, 'Mendoza', 3, 1)",
            (complejo, admin, nombre),
        )
    unidad = insertar_unidad(c, admin, edificio, "1A", coeficiente="1.000000")
    ajena = insertar_unidad(c, admin, otro, "9A", coeficiente="1.000000")
    return admin, edificio, otro, unidad, ajena, persona


def _cambio(
    c: psycopg.Connection,
    m: tuple[UUID, ...],
    *,
    unidad: UUID | None = None,
    expensa: str = "entera",
    deuda: str = "en_la_unidad",
) -> UUID:
    admin, edificio, _, u, _, persona = m
    cambio = uuid4()
    c.execute(
        "INSERT INTO cambio_de_titular (id, administracion_id, complejo_id, unidad_id, fecha, "
        "expensa_del_mes, deuda_previa, registrado_por) "
        "VALUES (%s, %s, %s, %s, '2026-11-10', %s, %s, %s)",
        (cambio, admin, edificio, unidad or u, expensa, deuda, persona),
    )
    return cambio


def _parte(
    c: psycopg.Connection,
    m: tuple[UUID, ...],
    cambio: UUID,
    rol: str,
    orden: int = 0,
    nombre: str | None = None,
    email: str | None = None,
) -> None:
    admin, edificio, _, _, _, persona = m
    c.execute(
        "INSERT INTO parte_de_cambio_de_titular (administracion_id, complejo_id, cambio_id, "
        "persona_id, "
        "rol, orden, nombre, email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (admin, edificio, cambio, persona, rol, orden, nombre, email),
    )


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("expensa", "mitad"), ("expensa", "ENTERA"), ("deuda", "se_pierde"), ("deuda", "")],
)
def test_el_vocabulario_de_las_opciones_es_cerrado(
    base_del_edificio: BaseDeEdificio, campo: str, valor: str
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        m = _mundo(c)
        with pytest.raises(psycopg.errors.CheckViolation), c.transaction():
            _cambio(c, m, expensa=valor) if campo == "expensa" else _cambio(c, m, deuda=valor)
        _cambio(
            c, m, expensa="prorrateo", deuda="a_nombre_del_vendedor"
        )  # los dos valores de H-031/H-032


def test_la_base_frena_el_cruce_de_edificio_y_las_partes_mal_formadas(
    base_del_edificio: BaseDeEdificio,
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        m = _mundo(c)
        with pytest.raises(psycopg.errors.ForeignKeyViolation), c.transaction():
            _cambio(c, m, unidad=m[4])  # una unidad de otro edificio
        cambio = _cambio(c, m)
        with pytest.raises(psycopg.errors.CheckViolation), c.transaction():
            _parte(c, m, cambio, "vendedor", nombre="Pía")  # el vendedor no lleva nombre
        with pytest.raises(psycopg.errors.CheckViolation), c.transaction():
            _parte(c, m, cambio, "comprador")  # el comprador sí
        with pytest.raises(psycopg.errors.CheckViolation), c.transaction():
            _parte(c, m, cambio, "tutor", nombre="Pía")
        _parte(c, m, cambio, "comprador", nombre="Pía", email="pia@ejemplo.invalid")
        with pytest.raises(psycopg.errors.UniqueViolation), c.transaction():
            _parte(c, m, cambio, "vendedor")  # la misma persona de los dos lados


def test_no_baja_con_cambios(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    with base.conectar_app() as c, c.transaction():
        m = _mundo(c)
        _cambio(c, m)
    base.devolver_tablas_protegidas()
    with pytest.raises(AssertionError, match="hay cambios de titular"):
        base.migrar("downgrade", "0049")
    # La bajada es una sola transacción: al rechazarla la 0050, las posteriores vuelven a la cabeza.
    assert _version(base) == ("0052",), "la bajada rechazada movió la versión"
    base.roles("despues")
    with base.conectar_migrador() as c:
        assert c.execute(
            "SELECT relforcerowsecurity FROM pg_class WHERE relname = 'cambio_de_titular'"
        ).fetchone() == (True,), "el downgrade rechazado dejó la RLS sin forzar"
