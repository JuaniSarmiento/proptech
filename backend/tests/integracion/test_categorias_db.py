"""3.4: categorías por edificio, con orden diferible y RLS real."""

from uuid import UUID

import psycopg
import pytest

from ._edificios import BaseDeEdificio, Edificios, fijar_tenant

pytestmark = pytest.mark.integracion


def insertar_categoria(
    conexion: psycopg.Connection,
    admin: UUID,
    complejo: UUID,
    clave: str = "limpieza",
    nombre: str = "Limpieza",
    orden: int = 1,
) -> UUID:
    fila = conexion.execute(
        "INSERT INTO categoria_de_gasto (administracion_id, complejo_id, clave, nombre, orden) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (admin, complejo, clave, nombre, orden),
    ).fetchone()
    assert fila is not None
    return UUID(str(fila[0]))


@pytest.mark.parametrize("repetir", ["nombre", "clave", "orden"])
def test_repeticion_en_el_mismo_edificio_falla(
    app_edificio: psycopg.Connection, edificios: Edificios, repetir: str
) -> None:
    insertar_categoria(app_edificio, edificios.administracion_a, edificios.complejo_a)
    with pytest.raises(psycopg.errors.UniqueViolation):
        with app_edificio.transaction():
            insertar_categoria(
                app_edificio,
                edificios.administracion_a,
                edificios.complejo_a,
                "limpieza" if repetir == "clave" else "otra",
                "limpieza" if repetir == "nombre" else "Otra",
                1 if repetir == "orden" else 2,
            )
            app_edificio.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_mismo_nombre_clave_y_orden_en_otro_edificio(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    ids = [
        insertar_categoria(app_edificio, edificios.administracion_a, complejo)
        for complejo in (edificios.complejo_a, edificios.otro_complejo_a)
    ]
    assert app_edificio.execute(
        "SELECT id, activa FROM categoria_de_gasto ORDER BY id"
    ).fetchall() == [(cid, True) for cid in sorted(ids)]


def test_intercambiar_orden_en_una_transaccion(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    primero = insertar_categoria(app_edificio, edificios.administracion_a, edificios.complejo_a)
    segundo = insertar_categoria(
        app_edificio, edificios.administracion_a, edificios.complejo_a, "varios", "Varios", 2
    )
    app_edificio.execute("UPDATE categoria_de_gasto SET orden = 2 WHERE id = %s", (primero,))
    app_edificio.execute("UPDATE categoria_de_gasto SET orden = 1 WHERE id = %s", (segundo,))
    app_edificio.execute("SET CONSTRAINTS ALL IMMEDIATE")
    assert app_edificio.execute("SELECT id FROM categoria_de_gasto ORDER BY orden").fetchall() == [
        (segundo,),
        (primero,),
    ]


def test_categoria_existente_de_otra_administracion_no_se_ve(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    fijar_tenant(app_edificio, edificios.administracion_b)
    cid = insertar_categoria(app_edificio, edificios.administracion_b, edificios.complejo_b)
    assert app_edificio.execute("SELECT id FROM categoria_de_gasto").fetchall() == [(cid,)]
    fijar_tenant(app_edificio, edificios.administracion_a)
    assert app_edificio.execute("SELECT id FROM categoria_de_gasto").fetchall() == []


def test_downgrade_upgrade_de_categorias(base_del_edificio: BaseDeEdificio) -> None:
    base_del_edificio.migrar("downgrade", "0007")
    try:
        with base_del_edificio.conectar_app() as app:
            assert app.execute("SELECT to_regclass('categoria_de_gasto')").fetchone() == (None,)
    finally:
        base_del_edificio.migrar("upgrade", "head")
    with base_del_edificio.conectar_app() as app:
        assert app.execute("SELECT count(*) FROM categoria_de_gasto").fetchone() == (0,)
