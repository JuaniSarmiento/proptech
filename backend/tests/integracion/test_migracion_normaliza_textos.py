"""R3B-8: normalización de datos legados y de futuras escrituras SQL."""

from uuid import UUID, uuid4

import pytest

from ._api_edificios import ApiEdificio
from ._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad

pytestmark = pytest.mark.integracion
UNIDAD = {"tipo": "departamento", "piso": "1", "coeficiente": "0.100000", "superficie_m2": "60.00"}


def test_dato_cargado_sin_normalizar_no_convive_con_su_version_recortada(
    api_edificio: ApiEdificio,
) -> None:
    """R3A-6 recorta en la API pero no hubo migración de datos ni cambio en
    el UNIQUE (`uq_unidad_identificador` sigue siendo sobre el texto
    crudo). Una fila guardada antes del arreglo (o por otro camino que no
    recorta: la semilla valida "1A " sin recortar) convive con la versión
    recortada que ahora manda la API: dos unidades que se ven iguales."""
    api = api_edificio
    api.como("super_admin")
    with api.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute("SELECT set_config('app.administracion_id', %s, true)", (str(api.admin),))
        conexion.execute(
            "INSERT INTO unidad (administracion_id, complejo_id, identificador, tipo, piso, "
            "coeficiente, superficie_m2) VALUES (%s, %s, '5C ', 'departamento', '1', "
            "'0.010000', '60.00')",
            (api.admin, api.edificio),
        )
    respuesta = api.cliente.post(api.ruta("/unidades"), json={**UNIDAD, "identificador": "5C"})
    assert respuesta.status_code == 409, (respuesta.status_code, respuesta.text)


def _legados(base: BaseDeEdificio) -> list[tuple[UUID, UUID]]:
    resultado = []
    with base.conectar_app() as conexion, conexion.transaction():
        for _ in range(2):
            admin, edificio = uuid4(), uuid4()
            fijar_tenant(conexion, admin)
            conexion.execute(
                "INSERT INTO administracion (id, nombre) VALUES (%s, 'Legada')", (admin,)
            )
            conexion.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, "
                "localidad) VALUES (%s, %s, ' Legado ', %s)",
                (edificio, admin, "\u00a0Mendoza\u00a0"),
            )
            insertar_unidad(conexion, admin, edificio, " 5C\u3000")
            conexion.execute(
                "INSERT INTO categoria_de_gasto (administracion_id, "
                "complejo_id, clave, nombre, orden) VALUES (%s, %s, 'limpieza', "
                "' Limpieza ', 0)",
                (admin, edificio),
            )
            conexion.execute(
                "INSERT INTO grupo_de_reparto (administracion_id, complejo_id, "
                "clave, nombre, metodo) VALUES (%s, %s, 'ascensor', ' Ascensor "
                "', 'coeficiente')",
                (admin, edificio),
            )
            resultado.append((admin, edificio))
    return resultado


def test_migracion_normaliza_todas_las_administraciones_y_campos(
    base_del_edificio: BaseDeEdificio,
) -> None:
    base = base_del_edificio
    base.migrar("downgrade", "0012")
    datos = _legados(base)
    base.migrar("upgrade", "head")
    with base.conectar_app() as conexion, conexion.transaction():
        for admin, edificio in datos:
            fijar_tenant(conexion, admin)
            assert conexion.execute(
                "SELECT nombre, localidad FROM complejo WHERE id = %s", (edificio,)
            ).fetchone() == ("Legado", "Mendoza")
            assert conexion.execute(
                "SELECT identificador FROM unidad WHERE complejo_id = %s", (edificio,)
            ).fetchall() == [("5C",)]
            assert conexion.execute(
                "SELECT nombre FROM categoria_de_gasto WHERE complejo_id = %s", (edificio,)
            ).fetchall() == [("Limpieza",)]
            assert conexion.execute(
                "SELECT nombre FROM grupo_de_reparto WHERE complejo_id = %s", (edificio,)
            ).fetchall() == [("Ascensor",)]
            # La lectura como app sigue aislada después de migrar todos los tenants.
            assert conexion.execute(
                "SELECT count(*) FROM complejo WHERE administracion_id <> %s", (admin,)
            ).fetchone() == (0,)


@pytest.mark.parametrize("tabla", ["unidad", "categoria_de_gasto"])
def test_migracion_con_choque_falla_claro_y_no_toca_datos_ni_rls(
    base_del_edificio: BaseDeEdificio, tabla: str
) -> None:
    base = base_del_edificio
    base.migrar("downgrade", "0012")
    datos = _legados(base)
    admin, edificio = datos[1]  # El choque está en el segundo tenant, nunca sólo en el primero.
    with base.conectar_app() as conexion, conexion.transaction():
        fijar_tenant(conexion, admin)
        if tabla == "unidad":
            duplicado = insertar_unidad(conexion, admin, edificio, "5C")
        else:
            fila = conexion.execute(
                "INSERT INTO categoria_de_gasto (administracion_id, "
                "complejo_id, clave, nombre, orden) VALUES (%s, %s, "
                "'duplicada', 'limpieza', 1) RETURNING id",
                (admin, edificio),
            ).fetchone()
            assert fila is not None
            duplicado = fila[0]
    try:
        with pytest.raises(AssertionError, match="normalización.*colisión.*" + tabla):
            base.migrar("upgrade", "head")
        with base.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin)
            assert conexion.execute(
                "SELECT nombre FROM complejo WHERE id = %s", (edificio,)
            ).fetchone() == (" Legado ",)
            assert conexion.execute("SELECT version_num FROM alembic_version").fetchone() == (
                "0012",
            )
            assert conexion.execute(
                "SELECT bool_and(relrowsecurity AND relforcerowsecurity) FROM "
                "pg_class WHERE relname IN ('unidad', 'complejo', "
                "'categoria_de_gasto', 'grupo_de_reparto')"
            ).fetchone() == (True,)
    finally:
        with base.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin)
            from psycopg import sql

            conexion.execute(
                sql.SQL("DELETE FROM {} WHERE id = %s").format(sql.Identifier(tabla)), (duplicado,)
            )
        base.migrar("upgrade", "head")


def test_recorte_sql_coincide_con_strip_unicode(base_del_edificio: BaseDeEdificio) -> None:
    with base_del_edificio.conectar_app() as conexion:
        # Incluye espacios no ASCII; no hay una segunda lista de espacios en el test.
        espacios = "".join(chr(c) for c in range(0x110000) if chr(c).isspace())
        assert conexion.execute(
            "SELECT public.fn_recortar_texto_3a(%s)", (espacios + "1 A" + espacios,)
        ).fetchone() == ("1 A",)
