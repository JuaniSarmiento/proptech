"""3.3: coherencia del modo por FK y CHECK, con INSERT/UPDATE reales."""

from decimal import Decimal
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


def _grupo(
    app: psycopg.Connection,
    edificios: Edificios,
    modo: str,
    *,
    metodo: str = "coeficiente",
    es_generales: bool = False,
) -> UUID:
    fila = app.execute(
        "INSERT INTO grupo_de_reparto (administracion_id, complejo_id, clave, nombre, metodo, "
        "es_generales, modo_de_coeficientes) VALUES (%s, %s, 'ascensor', 'Ascensor', %s, %s, %s) "
        "RETURNING id",
        (edificios.administracion_a, edificios.complejo_a, metodo, es_generales, modo),
    ).fetchone()
    assert fila is not None
    return UUID(str(fila[0]))


@pytest.mark.parametrize("modo,coeficiente", [("renormalizado", "0.5"), ("propios", None)])
def test_miembro_incoherente_con_su_modo_falla_por_check(
    app_edificio: psycopg.Connection,
    edificios: Edificios,
    modo: str,
    coeficiente: str | None,
) -> None:
    grupo = _grupo(app_edificio, edificios, modo)
    with pytest.raises(psycopg.errors.CheckViolation):
        insertar_miembro(
            app_edificio,
            edificios.administracion_a,
            edificios.complejo_a,
            grupo,
            edificios.unidad_a,
            modo=modo,
            coeficiente=coeficiente,
        )


@pytest.mark.parametrize(
    "modo_grupo,modo_miembro,coeficiente",
    [("renormalizado", "propios", "0.5"), ("propios", "renormalizado", None)],
)
def test_modo_de_miembro_distinto_del_padre_falla_por_fk(
    app_edificio: psycopg.Connection,
    edificios: Edificios,
    modo_grupo: str,
    modo_miembro: str,
    coeficiente: str | None,
) -> None:
    grupo = _grupo(app_edificio, edificios, modo_grupo)
    # La forma del miembro es válida: sólo la FK puede detectar la diferencia.
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        insertar_miembro(
            app_edificio,
            edificios.administracion_a,
            edificios.complejo_a,
            grupo,
            edificios.unidad_a,
            modo=modo_miembro,
            coeficiente=coeficiente,
        )


@pytest.mark.parametrize("metodo", ["superficie", "partes_iguales"])
def test_propios_con_otro_metodo_falla_por_check(
    app_edificio: psycopg.Connection, edificios: Edificios, metodo: str
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        _grupo(app_edificio, edificios, "propios", metodo=metodo)


def test_generales_con_modo_propios_falla_por_check(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        _grupo(app_edificio, edificios, "propios", es_generales=True)


def test_modo_desconocido_falla_por_check(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        _grupo(app_edificio, edificios, "inventado")


@pytest.mark.parametrize("coeficiente", ["0", "-0.1", "1.000001"])
def test_coeficiente_propio_fuera_de_rango_falla_por_check(
    app_edificio: psycopg.Connection, edificios: Edificios, coeficiente: str
) -> None:
    grupo = _grupo(app_edificio, edificios, "propios")
    with pytest.raises(psycopg.errors.CheckViolation):
        insertar_miembro(
            app_edificio,
            edificios.administracion_a,
            edificios.complejo_a,
            grupo,
            edificios.unidad_a,
            modo="propios",
            coeficiente=coeficiente,
        )


@pytest.mark.parametrize("coeficiente", ["0.000001", "1.000000"])
def test_coeficiente_propio_valido_se_guarda_como_decimal(
    app_edificio: psycopg.Connection, edificios: Edificios, coeficiente: str
) -> None:
    grupo = _grupo(app_edificio, edificios, "propios")
    insertar_miembro(
        app_edificio,
        edificios.administracion_a,
        edificios.complejo_a,
        grupo,
        edificios.unidad_a,
        modo="propios",
        coeficiente=coeficiente,
    )
    assert app_edificio.execute(
        "SELECT modo_de_coeficientes, coeficiente FROM grupo_unidad WHERE grupo_id = %s", (grupo,)
    ).fetchall() == [("propios", Decimal(coeficiente))]


def test_grupo_por_defecto_renormalizado_admite_miembro_sin_coeficiente(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    grupo = insertar_grupo(app_edificio, edificios.administracion_a, edificios.complejo_a)
    insertar_miembro(
        app_edificio, edificios.administracion_a, edificios.complejo_a, grupo, edificios.unidad_a
    )
    assert app_edificio.execute(
        "SELECT g.modo_de_coeficientes, m.modo_de_coeficientes, m.coeficiente "
        "FROM grupo_de_reparto g JOIN grupo_unidad m ON m.grupo_id = g.id WHERE g.id = %s",
        (grupo,),
    ).fetchone() == ("renormalizado", "renormalizado", None)


def test_modo_del_miembro_es_obligatorio_sin_default_temporal(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    grupo = insertar_grupo(app_edificio, edificios.administracion_a, edificios.complejo_a)
    with pytest.raises(psycopg.errors.NotNullViolation) as error:
        app_edificio.execute(
            "INSERT INTO grupo_unidad (administracion_id, complejo_id, grupo_id, unidad_id) "
            "VALUES (%s, %s, %s, %s)",
            (edificios.administracion_a, edificios.complejo_a, grupo, edificios.unidad_a),
        )
    assert error.value.diag.column_name == "modo_de_coeficientes"


@pytest.mark.parametrize(
    "modo_inicial,modo_final,coeficiente",
    [("renormalizado", "propios", None), ("propios", "renormalizado", "1.000000")],
)
def test_cambiar_modo_con_miembros_falla_por_check_del_cascade_y_no_cambia_filas(
    app_edificio: psycopg.Connection,
    edificios: Edificios,
    modo_inicial: str,
    modo_final: str,
    coeficiente: str | None,
) -> None:
    grupo = _grupo(app_edificio, edificios, modo_inicial)
    insertar_miembro(
        app_edificio,
        edificios.administracion_a,
        edificios.complejo_a,
        grupo,
        edificios.unidad_a,
        modo=modo_inicial,
        coeficiente=coeficiente,
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        with app_edificio.transaction():
            app_edificio.execute(
                "UPDATE grupo_de_reparto SET modo_de_coeficientes = %s WHERE id = %s",
                (modo_final, grupo),
            )
    assert app_edificio.execute(
        "SELECT g.modo_de_coeficientes, m.modo_de_coeficientes, m.coeficiente, m.unidad_id "
        "FROM grupo_de_reparto g JOIN grupo_unidad m ON m.grupo_id = g.id WHERE g.id = %s",
        (grupo,),
    ).fetchall() == [
        (
            modo_inicial,
            modo_inicial,
            Decimal(coeficiente) if coeficiente else None,
            edificios.unidad_a,
        )
    ]


def test_cambiar_modo_reemplazando_miembros_en_una_transaccion_es_valido(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    grupo = _grupo(app_edificio, edificios, "renormalizado")
    insertar_miembro(
        app_edificio, edificios.administracion_a, edificios.complejo_a, grupo, edificios.unidad_a
    )
    with app_edificio.transaction():
        app_edificio.execute("DELETE FROM grupo_unidad WHERE grupo_id = %s", (grupo,))
        app_edificio.execute(
            "UPDATE grupo_de_reparto SET modo_de_coeficientes = 'propios' WHERE id = %s", (grupo,)
        )
        insertar_miembro(
            app_edificio,
            edificios.administracion_a,
            edificios.complejo_a,
            grupo,
            edificios.unidad_a,
            modo="propios",
            coeficiente="1.000000",
        )
    assert app_edificio.execute(
        "SELECT g.modo_de_coeficientes, m.modo_de_coeficientes, m.coeficiente "
        "FROM grupo_de_reparto g JOIN grupo_unidad m ON m.grupo_id = g.id WHERE g.id = %s",
        (grupo,),
    ).fetchall() == [("propios", "propios", Decimal("1.000000"))]


def test_downgrade_a_0006_y_upgrade_rellena_modo_de_grupos_y_miembros_existentes(
    base_del_edificio: BaseDeEdificio,
) -> None:
    base_del_edificio.devolver_tablas_protegidas()
    base_del_edificio.migrar("downgrade", "0006")
    admin, complejo = uuid4(), uuid4()
    try:
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
            app.execute(
                "INSERT INTO grupo_unidad (administracion_id, complejo_id, grupo_id, unidad_id) "
                "VALUES (%s, %s, %s, %s)",
                (admin, complejo, grupo, unidad),
            )
        base_del_edificio.migrar("upgrade", "head")
        with base_del_edificio.conectar_app() as app, app.transaction():
            fijar_tenant(app, admin)
            assert app.execute(
                "SELECT g.modo_de_coeficientes, m.modo_de_coeficientes, m.coeficiente, m.unidad_id "
                "FROM grupo_de_reparto g JOIN grupo_unidad m ON m.grupo_id = g.id WHERE g.id = %s",
                (grupo,),
            ).fetchone() == ("renormalizado", "renormalizado", None, unidad)
        base_del_edificio.devolver_tablas_protegidas()
        base_del_edificio.migrar("downgrade", "0006")
        with base_del_edificio.conectar_app() as app, app.transaction():
            fijar_tenant(app, admin)
            assert app.execute("SELECT grupo_id, unidad_id FROM grupo_unidad").fetchall() == [
                (grupo, unidad)
            ]
            for tabla in ("grupo_de_reparto", "grupo_unidad"):
                with pytest.raises(psycopg.errors.UndefinedColumn):
                    with app.transaction():
                        app.execute(
                            psycopg.sql.SQL("SELECT modo_de_coeficientes FROM {}").format(
                                psycopg.sql.Identifier(tabla)
                            )
                        )
    finally:
        base_del_edificio.migrar("upgrade", "head")
