"""2.4: el candado de D9 en la bajada de `0023` (`LOCK` → `NO FORCE` →
`UPDATE complejo SET localidad=''` → `FORCE`) tiene que tocar las filas de
TODAS las administraciones, no sólo las del tenant de turno — si el
`UPDATE` corriera bajo RLS normal (sin el candado), vería cero filas sin
avisar (el mismo defecto documentado como DB-3 en el 4a). Se siembra una
base con más de una administración antes de bajar, para que el candado se
pruebe de verdad."""

from uuid import uuid4

import pytest

from ._edificios import BaseDeEdificio, fijar_tenant

pytestmark = pytest.mark.integracion


def test_downgrade_de_0023_rellena_localidad_en_mas_de_una_administracion(
    base_del_edificio: BaseDeEdificio,
) -> None:
    admin_x, admin_y = uuid4(), uuid4()
    complejo_x, complejo_y = uuid4(), uuid4()
    try:
        with base_del_edificio.conectar_app() as app, app.transaction():
            for admin, complejo, nombre in (
                (admin_x, complejo_x, "Edificio X"),
                (admin_y, complejo_y, "Edificio Y"),
            ):
                fijar_tenant(app, admin)
                app.execute(
                    "INSERT INTO administracion (id, nombre) VALUES (%s, %s)",
                    (admin, f"Administración de {nombre}"),
                )
                app.execute(
                    "INSERT INTO complejo (id, administracion_id, nombre, provincia_id, "
                    "departamento_id, localidad_id) VALUES (%s, %s, %s, '50', '50007', "
                    "'50007010')",
                    (complejo, admin, nombre),
                )
            fijar_tenant(app, admin_x)
            app.execute("UPDATE complejo SET localidad = NULL WHERE id = %s", (complejo_x,))
            fijar_tenant(app, admin_y)
            app.execute("UPDATE complejo SET localidad = NULL WHERE id = %s", (complejo_y,))

        base_del_edificio.devolver_tablas_protegidas()
        base_del_edificio.migrar("downgrade", "0022")

        with base_del_edificio.conectar_app() as app, app.transaction():
            for admin, complejo in ((admin_x, complejo_x), (admin_y, complejo_y)):
                fijar_tenant(app, admin)
                fila = app.execute(
                    "SELECT localidad FROM complejo WHERE id = %s", (complejo,)
                ).fetchone()
                assert fila == ("",), f"complejo de {admin} no quedó con localidad=''"
    finally:
        base_del_edificio.migrar("upgrade", "head")


def test_downgrade_de_0023_elimina_las_columnas_de_ubicacion(
    base_del_edificio: BaseDeEdificio,
) -> None:
    try:
        base_del_edificio.devolver_tablas_protegidas()
        base_del_edificio.migrar("downgrade", "0022")
        with base_del_edificio.conectar_app() as app:
            columnas = {
                fila[0]
                for fila in app.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'complejo'"
                ).fetchall()
            }
        assert "provincia_id" not in columnas
        assert "calle_y_numero" not in columnas
    finally:
        base_del_edificio.migrar("upgrade", "head")
