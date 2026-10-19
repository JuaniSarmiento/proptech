"""3.2: miembros y Generales protegidos por restricciones reales (L-018)."""

from uuid import UUID, uuid4

import psycopg
import pytest

from ._edificios import (
    BaseDeEdificio,
    Edificios,
    fijar_tenant,
    insertar_grupo,
    insertar_miembro,
    insertar_unidad,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def grupo(app_edificio: psycopg.Connection, edificios: Edificios) -> UUID:
    return insertar_grupo(app_edificio, edificios.administracion_a, edificios.complejo_a)


@pytest.mark.parametrize("origen", ["otro_edificio", "otra_administracion"])
def test_miembro_con_unidad_existente_ajena_falla_por_fk(
    app_edificio: psycopg.Connection, edificios: Edificios, grupo: UUID, origen: str
) -> None:
    unidad = edificios.otra_unidad_a if origen == "otro_edificio" else edificios.unidad_b
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        insertar_miembro(
            app_edificio, edificios.administracion_a, edificios.complejo_a, grupo, unidad
        )


def test_miembro_con_grupo_existente_de_otro_edificio_falla_por_fk(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    otro_grupo = insertar_grupo(app_edificio, edificios.administracion_a, edificios.otro_complejo_a)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        insertar_miembro(
            app_edificio,
            edificios.administracion_a,
            edificios.complejo_a,
            otro_grupo,
            edificios.unidad_a,
        )


def test_unidad_repetida_en_un_grupo_falla_por_unique(
    app_edificio: psycopg.Connection, edificios: Edificios, grupo: UUID
) -> None:
    insertar_miembro(
        app_edificio, edificios.administracion_a, edificios.complejo_a, grupo, edificios.unidad_a
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        insertar_miembro(
            app_edificio,
            edificios.administracion_a,
            edificios.complejo_a,
            grupo,
            edificios.unidad_a,
        )


def test_unidad_puede_pertenecer_a_dos_grupos_del_mismo_edificio(
    app_edificio: psycopg.Connection, edificios: Edificios, grupo: UUID
) -> None:
    segundo = insertar_grupo(
        app_edificio, edificios.administracion_a, edificios.complejo_a, "cocheras"
    )
    for gid in (grupo, segundo):
        insertar_miembro(
            app_edificio, edificios.administracion_a, edificios.complejo_a, gid, edificios.unidad_a
        )
    assert app_edificio.execute(
        "SELECT grupo_id, unidad_id FROM grupo_unidad ORDER BY grupo_id"
    ).fetchall() == sorted([(grupo, edificios.unidad_a), (segundo, edificios.unidad_a)])


def test_segundo_generales_en_el_mismo_edificio_falla_por_unique(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    insertar_grupo(
        app_edificio,
        edificios.administracion_a,
        edificios.complejo_a,
        "generales",
        es_generales=True,
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        insertar_grupo(
            app_edificio,
            edificios.administracion_a,
            edificios.complejo_a,
            "otro",
            es_generales=True,
        )


@pytest.mark.parametrize("metodo", ["superficie", "partes_iguales"])
def test_generales_solo_admite_metodo_coeficiente(
    app_edificio: psycopg.Connection, edificios: Edificios, metodo: str
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        insertar_grupo(
            app_edificio,
            edificios.administracion_a,
            edificios.complejo_a,
            "generales",
            metodo=metodo,
            es_generales=True,
        )


def test_metodo_desconocido_falla_por_check(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        insertar_grupo(
            app_edificio, edificios.administracion_a, edificios.complejo_a, metodo="inventado"
        )


def test_clave_repetida_en_el_mismo_edificio_falla_por_unique(
    app_edificio: psycopg.Connection, edificios: Edificios, grupo: UUID
) -> None:
    with pytest.raises(psycopg.errors.UniqueViolation):
        insertar_grupo(app_edificio, edificios.administracion_a, edificios.complejo_a)


def test_cada_edificio_admite_su_generales_con_la_misma_clave(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    for cid in (edificios.complejo_a, edificios.otro_complejo_a):
        insertar_grupo(
            app_edificio, edificios.administracion_a, cid, "generales", es_generales=True
        )
    assert app_edificio.execute(
        "SELECT complejo_id, clave FROM grupo_de_reparto ORDER BY complejo_id"
    ).fetchall() == sorted(
        [(edificios.complejo_a, "generales"), (edificios.otro_complejo_a, "generales")]
    )


@pytest.mark.parametrize("tabla", ["grupo_de_reparto", "grupo_unidad"])
@pytest.mark.parametrize("tenant", [None, "b"])
def test_sin_tenant_o_con_otro_tenant_no_se_ven_los_grupos_ni_miembros(
    app_edificio: psycopg.Connection,
    edificios: Edificios,
    grupo: UUID,
    tabla: str,
    tenant: str | None,
) -> None:
    insertar_miembro(
        app_edificio, edificios.administracion_a, edificios.complejo_a, grupo, edificios.unidad_a
    )
    app_edificio.execute(
        "SELECT set_config('app.administracion_id', %s, true)",
        (str(edificios.administracion_b) if tenant else "",),
    )
    assert (
        app_edificio.execute(
            psycopg.sql.SQL("SELECT * FROM {}").format(psycopg.sql.Identifier(tabla))
        ).fetchall()
        == []
    )


@pytest.mark.parametrize("tabla", ["grupo_de_reparto", "grupo_unidad"])
def test_rls_rechaza_escritura_con_administracion_ajena(
    app_edificio: psycopg.Connection, edificios: Edificios, grupo: UUID, tabla: str
) -> None:
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        if tabla == "grupo_de_reparto":
            insertar_grupo(app_edificio, edificios.administracion_b, edificios.complejo_b)
        else:
            insertar_miembro(
                app_edificio,
                edificios.administracion_b,
                edificios.complejo_b,
                grupo,
                edificios.unidad_b,
            )


def test_downgrade_a_0005_borra_grupos_y_upgrade_los_recrea(
    base_del_edificio: BaseDeEdificio,
) -> None:
    admin, complejo = uuid4(), uuid4()
    with base_del_edificio.conectar_app() as app, app.transaction():
        fijar_tenant(app, admin)
        app.execute("INSERT INTO administracion VALUES (%s, 'Prueba')", (admin,))
        app.execute(
            "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
            "VALUES (%s, %s, 'Ciclo', 'Mendoza')",
            (complejo, admin),
        )
        unidad = insertar_unidad(app, admin, complejo)
        grupo = insertar_grupo(app, admin, complejo)
        insertar_miembro(app, admin, complejo, grupo, unidad)
    base_del_edificio.migrar("downgrade", "0005")
    try:
        with base_del_edificio.conectar_app() as app:
            for tabla in ("grupo_de_reparto", "grupo_unidad"):
                with pytest.raises(psycopg.errors.UndefinedTable):
                    app.execute(
                        psycopg.sql.SQL("SELECT * FROM {}").format(psycopg.sql.Identifier(tabla))
                    )
        base_del_edificio.migrar("upgrade", "head")
        with base_del_edificio.conectar_app() as app, app.transaction():
            fijar_tenant(app, admin)
            assert app.execute(
                "SELECT identificador FROM unidad WHERE id = %s", (unidad,)
            ).fetchone() == ("1A",)
            grupo = insertar_grupo(app, admin, complejo)
            insertar_miembro(app, admin, complejo, grupo, unidad)
            assert app.execute("SELECT grupo_id, unidad_id FROM grupo_unidad").fetchall() == [
                (grupo, unidad)
            ]
    finally:
        base_del_edificio.migrar("upgrade", "head")
