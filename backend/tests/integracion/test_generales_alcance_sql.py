"""Frentes 2 y 4: lo que la base deja hacer a `proptech_app` por SQL sobre
lo que protegió la vuelta de correcciones (0011) y sobre la vida de una
unidad."""

from uuid import UUID

import psycopg
import pytest

from ._edificios import (
    BaseDeEdificio,
    Edificios,
    insertar_grupo,
    insertar_miembro,
)

pytestmark = pytest.mark.integracion


def _generales(conexion: psycopg.Connection, edificios: Edificios) -> UUID:
    return insertar_grupo(
        conexion,
        edificios.administracion_a,
        edificios.complejo_a,
        "generales",
        es_generales=True,
    )


def test_generales_no_admite_miembros_explicitos_por_sql(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    """Spec `grupos-de-reparto`: el ALCANCE de Generales MUST NOT poder
    cambiarse (0011 dice protegerlo "ni por SQL"). El trigger de 0011 sólo
    está en `grupo_de_reparto`; `grupo_unidad` no tiene nada que impida
    colgarle a Generales una lista explícita de miembros, que es justo lo
    que define el alcance de cualquier otro grupo."""
    generales = _generales(app_edificio, edificios)
    with pytest.raises(psycopg.Error):
        insertar_miembro(
            app_edificio,
            edificios.administracion_a,
            edificios.complejo_a,
            generales,
            edificios.unidad_a,
        )


def test_trigger_de_0011_sobrevive_downgrade_y_upgrade(base_del_edificio: BaseDeEdificio) -> None:
    """Fila 3 del auditor: el verde de R3A-3 decía incluir el ciclo
    downgrade/upgrade de 0011 sin correrlo. Acá: bajar a 0010, volver a head
    y comprobar que el trigger sigue frenando el DELETE de Generales."""
    base_del_edificio.migrar("downgrade", "0010")
    base_del_edificio.migrar("upgrade", "head")
    base_del_edificio.roles("despues")
    with base_del_edificio.conectar_app() as conexion:
        conexion.autocommit = False
        try:
            admin = UUID("00000000-0000-4000-8000-0000000000a1")
            conexion.execute("SELECT set_config('app.administracion_id', %s, true)", (str(admin),))
            conexion.execute("INSERT INTO administracion (id, nombre) VALUES (%s, 'x')", (admin,))
            complejo = UUID("00000000-0000-4000-8000-0000000000c1")
            conexion.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "VALUES (%s, %s, 'E', 'Mendoza')",
                (complejo, admin),
            )
            generales = insertar_grupo(conexion, admin, complejo, "generales", es_generales=True)
            with pytest.raises(psycopg.Error):
                conexion.execute("DELETE FROM grupo_de_reparto WHERE id = %s", (generales,))
        finally:
            conexion.rollback()


def test_generales_no_admite_mudarse_de_edificio_por_sql(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    """RF-D-1 (revisión final, 19/10/2026). El trigger de 0011
    (`fn_grupo_generales_protegido`) sólo mira `es_generales`, `metodo` y
    `modo_de_coeficientes`: un `UPDATE grupo_de_reparto SET complejo_id =
    <otro edificio de la misma administración>` sobre Generales pasaba sin
    error. El edificio original queda sin Generales (equivale al DELETE que
    el trigger prohíbe) y la spec (`grupos-de-reparto/spec.md`) exige que el
    alcance de Generales MUST NOT cambiar. La FK compuesta no alcanza: sólo
    impide otra ADMINISTRACIÓN, nunca otro edificio de la misma."""
    generales = _generales(app_edificio, edificios)
    with pytest.raises(psycopg.Error, match="Generales"):
        app_edificio.execute(
            "UPDATE grupo_de_reparto SET complejo_id = %s WHERE id = %s",
            (edificios.otro_complejo_a, generales),
        )


def test_proptech_app_no_tiene_truncate_ni_puede_apagar_el_trigger(
    app_edificio: psycopg.Connection,
) -> None:
    """TRUNCATE no dispara triggers BEFORE DELETE; ALTER TABLE ... DISABLE
    TRIGGER y `session_replication_role` los apagan. Ninguno tiene que estar
    al alcance de `proptech_app`."""
    fila = app_edificio.execute(
        "SELECT has_table_privilege('proptech_app', 'grupo_de_reparto', 'TRUNCATE'), "
        "has_table_privilege('proptech_app', 'grupo_de_reparto', 'TRIGGER'), "
        "pg_has_role('proptech_app', (SELECT tableowner FROM pg_tables "
        "WHERE tablename = 'grupo_de_reparto'), 'MEMBER')"
    ).fetchone()
    assert fila == (False, False, False), fila
    with pytest.raises(psycopg.Error):
        app_edificio.execute("SET session_replication_role = replica")


@pytest.mark.parametrize("operacion", ["insertar", "actualizar", "promover"])
def test_familia_de_miembros_explicitos_de_generales_se_rechaza(
    app_edificio: psycopg.Connection, edificios: Edificios, operacion: str
) -> None:
    # "promover" parte SIN Generales: no puede pasar por su UNIQUE parcial.
    normal = insertar_grupo(
        app_edificio, edificios.administracion_a, edificios.complejo_a, "parcial"
    )
    insertar_miembro(
        app_edificio, edificios.administracion_a, edificios.complejo_a, normal, edificios.unidad_a
    )
    generales = None if operacion == "promover" else _generales(app_edificio, edificios)
    with pytest.raises(psycopg.errors.RaiseException, match="Generales"):
        if operacion == "insertar":
            assert generales is not None
            insertar_miembro(
                app_edificio,
                edificios.administracion_a,
                edificios.complejo_a,
                generales,
                edificios.unidad_a,
            )
        elif operacion == "actualizar":
            app_edificio.execute(
                "UPDATE grupo_unidad SET grupo_id = %s WHERE grupo_id = %s", (generales, normal)
            )
        else:
            app_edificio.execute(
                "UPDATE grupo_de_reparto SET es_generales = true WHERE id = %s", (normal,)
            )


def test_migracion_detecta_miembros_viejos_de_generales_y_revierte_el_candado(
    base_del_edificio: BaseDeEdificio,
) -> None:
    from uuid import uuid4

    base = base_del_edificio
    base.migrar("downgrade", "0011")
    admin, edificio = uuid4(), uuid4()
    with base.conectar_app() as conexion, conexion.transaction():
        conexion.execute("SELECT set_config('app.administracion_id', %s, true)", (str(admin),))
        conexion.execute("INSERT INTO administracion (id, nombre) VALUES (%s, 'Legada')", (admin,))
        conexion.execute(
            "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
            "VALUES (%s, %s, 'Legado', 'Mendoza')",
            (edificio, admin),
        )
        fila = conexion.execute(
            "INSERT INTO unidad (administracion_id, complejo_id, identificador, "
            "tipo, piso, coeficiente, superficie_m2) VALUES (%s, %s, '1A', "
            "'departamento', '1', '1', '1') RETURNING id",
            (admin, edificio),
        ).fetchone()
        assert fila is not None
        unidad = fila[0]
        grupo = insertar_grupo(conexion, admin, edificio, "generales", es_generales=True)
        insertar_miembro(conexion, admin, edificio, grupo, unidad)
    try:
        with pytest.raises(AssertionError, match="Generales tiene miembros explícitos"):
            base.migrar("upgrade", "head")
        with base.conectar_app() as conexion:
            assert conexion.execute(
                "SELECT bool_and(relrowsecurity AND relforcerowsecurity) FROM "
                "pg_class WHERE relname IN ('grupo_unidad', 'grupo_de_reparto')"
            ).fetchone() == (True,)
    finally:
        with base.conectar_app() as conexion, conexion.transaction():
            conexion.execute("SELECT set_config('app.administracion_id', %s, true)", (str(admin),))
            conexion.execute("DELETE FROM grupo_unidad WHERE grupo_id = %s", (grupo,))
        base.migrar("upgrade", "head")
        base.roles("despues")
