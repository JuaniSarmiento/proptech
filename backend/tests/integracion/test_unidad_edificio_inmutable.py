"""R3B-5: la pertenencia de una unidad es inmutable también por SQL real."""

from uuid import uuid4

import psycopg
import pytest

from ._edificios import BaseDeEdificio, Edificios, fijar_tenant, insertar_unidad

pytestmark = pytest.mark.integracion
MENSAJE = "La unidad no admite cambiar complejo_id ni administracion_id"


def test_una_unidad_no_se_muda_a_otro_edificio_de_la_misma_administracion_por_sql(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    # Ambos edificios tienen "1A": cambiar el identificador evita que el UNIQUE
    # dé un falso verde. La unidad no tiene miembros ni roles que frenen el UPDATE.
    with app_edificio.transaction():
        with pytest.raises(psycopg.errors.CheckViolation, match=MENSAJE):
            with app_edificio.transaction():
                app_edificio.execute(
                    "UPDATE unidad SET complejo_id = %s, identificador = 'mudada' WHERE id = %s",
                    (edificios.otro_complejo_a, edificios.unidad_a),
                )
        assert app_edificio.execute(
            "SELECT administracion_id, complejo_id, identificador FROM unidad WHERE id = %s",
            (edificios.unidad_a,),
        ).fetchone() == (edificios.administracion_a, edificios.complejo_a, "1A")


@pytest.mark.parametrize("cambiar_edificio", [False, True], ids=["solo_admin", "admin_y_edificio"])
def test_no_cambia_administracion_aunque_se_cambie_tambien_el_edificio(
    app_edificio: psycopg.Connection, edificios: Edificios, cambiar_edificio: bool
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation, match=MENSAJE):
        app_edificio.execute(
            "UPDATE unidad SET administracion_id = %s, complejo_id = %s, "
            "identificador = 'mudada' WHERE id = %s",
            (
                edificios.administracion_b,
                edificios.complejo_b if cambiar_edificio else edificios.complejo_a,
                edificios.unidad_a,
            ),
        )


@pytest.mark.parametrize(
    "sentencia",
    [
        "UPDATE unidad SET identificador = '2A', piso = '2' WHERE id = %s "
        "RETURNING administracion_id, complejo_id, identificador, piso",
        "UPDATE unidad SET complejo_id = complejo_id, administracion_id = administracion_id, "
        "identificador = '2A', piso = '2' WHERE id = %s "
        "RETURNING administracion_id, complejo_id, identificador, piso",
    ],
    ids=["editar", "mismas_claves"],
)
def test_edicion_legitima_y_reasignacion_de_las_mismas_claves_son_validas(
    app_edificio: psycopg.Connection, edificios: Edificios, sentencia: str
) -> None:
    assert app_edificio.execute(sentencia, (edificios.unidad_a,)).fetchone() == (
        edificios.administracion_a,
        edificios.complejo_a,
        "2A",
        "2",
    )


def test_downgrade_quita_la_barrera_y_upgrade_la_reinstala_sin_perder_datos(
    base_del_edificio: BaseDeEdificio,
) -> None:
    base = base_del_edificio
    admin, origen, destino = uuid4(), uuid4(), uuid4()
    with base.conectar_app() as app, app.transaction():
        fijar_tenant(app, admin)
        app.execute("INSERT INTO administracion VALUES (%s, 'Prueba R3B-5')", (admin,))
        for edificio in (origen, destino):
            app.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "VALUES (%s, %s, 'Edificio inventado', 'Mendoza')",
                (edificio, admin),
            )
        unidad = insertar_unidad(app, admin, origen)
        with pytest.raises(psycopg.errors.CheckViolation, match=MENSAJE):
            with app.transaction():
                app.execute("UPDATE unidad SET complejo_id = %s WHERE id = %s", (destino, unidad))
    try:
        base.migrar("downgrade", "0013")
        with base.conectar_app() as app, app.transaction():
            fijar_tenant(app, admin)
            assert app.execute(
                "SELECT to_regprocedure('public.fn_unidad_edificio_inmutable()')"
            ).fetchone() == (None,)
            assert app.execute(
                "UPDATE unidad SET complejo_id = %s WHERE id = %s RETURNING complejo_id",
                (destino, unidad),
            ).fetchone() == (destino,)
        base.migrar("upgrade", "head")
        with base.conectar_app() as app, app.transaction():
            fijar_tenant(app, admin)
            with pytest.raises(psycopg.errors.CheckViolation, match=MENSAJE):
                with app.transaction():
                    app.execute(
                        "UPDATE unidad SET complejo_id = %s WHERE id = %s", (origen, unidad)
                    )
            assert app.execute(
                "SELECT administracion_id, complejo_id, identificador FROM unidad WHERE id = %s",
                (unidad,),
            ).fetchone() == (admin, destino, "1A")
            assert app.execute("SELECT version_num FROM alembic_version").fetchone() == ("0017",)
    finally:
        base.migrar("upgrade", "head")
