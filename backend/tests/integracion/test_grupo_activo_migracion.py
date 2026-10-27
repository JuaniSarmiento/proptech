"""D7 (tarea 4.3): migración `0025` (la parte de `grupo_de_reparto.activo`,
compartida con la del vocabulario de `editar_edificio`, tarea 3.7) — nace
`NOT NULL DEFAULT true` sin backfill, probada sobre una copia con **más de
una administración** real."""

from uuid import uuid4

import pytest

from ._edificios import BaseDeEdificio, fijar_tenant

pytestmark = pytest.mark.integracion


def test_activo_nace_true_sin_backfill_en_mas_de_una_administracion(
    base_del_edificio: BaseDeEdificio,
) -> None:
    admin_x, admin_y = uuid4(), uuid4()
    complejo_x, complejo_y = uuid4(), uuid4()
    try:
        base_del_edificio.devolver_tablas_protegidas()
        base_del_edificio.migrar("downgrade", "0024")

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
                    "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                    "VALUES (%s, %s, %s, 'Mendoza')",
                    (complejo, admin, nombre),
                )
                app.execute(
                    "INSERT INTO grupo_de_reparto (administracion_id, complejo_id, clave, "
                    "nombre, metodo, es_generales) VALUES (%s, %s, 'generales', "
                    "'Generales', 'coeficiente', true)",
                    (admin, complejo),
                )
                app.execute(
                    "INSERT INTO grupo_de_reparto (administracion_id, complejo_id, clave, "
                    "nombre, metodo) VALUES (%s, %s, 'parcial', 'Parcial', 'coeficiente')",
                    (admin, complejo),
                )

        base_del_edificio.devolver_tablas_protegidas()
        base_del_edificio.migrar("upgrade", "0025")
        base_del_edificio.roles("despues")

        with base_del_edificio.conectar_app() as app, app.transaction():
            for admin, complejo in ((admin_x, complejo_x), (admin_y, complejo_y)):
                fijar_tenant(app, admin)
                filas = app.execute(
                    "SELECT clave, activo FROM grupo_de_reparto WHERE complejo_id=%s "
                    "ORDER BY clave",
                    (complejo,),
                ).fetchall()
                assert filas == [("generales", True), ("parcial", True)]

        base_del_edificio.devolver_tablas_protegidas()
        base_del_edificio.migrar("downgrade", "0024")
        with base_del_edificio.conectar_app() as app, app.transaction():
            fijar_tenant(app, admin_x)
            with pytest.raises(Exception, match="activo"):
                app.execute("SELECT activo FROM grupo_de_reparto LIMIT 1")

        base_del_edificio.migrar("upgrade", "0025")
        base_del_edificio.roles("despues")
        with base_del_edificio.conectar_app() as app, app.transaction():
            fijar_tenant(app, admin_x)
            filas = app.execute(
                "SELECT clave, activo FROM grupo_de_reparto WHERE complejo_id=%s ORDER BY clave",
                (complejo_x,),
            ).fetchall()
            assert filas == [("generales", True), ("parcial", True)]
    finally:
        base_del_edificio.migrar("upgrade", "head")
        base_del_edificio.roles("despues")
