"""3.1: restricciones reales, tenant de la app y ciclo con filas del 2a."""

from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest

from ._edificios import BaseDeEdificio, Edificios, fijar_tenant, insertar_unidad

pytestmark = pytest.mark.integracion


def test_identificador_repetido_falla_en_el_mismo_edificio(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(psycopg.errors.UniqueViolation):
        insertar_unidad(app_edificio, edificios.administracion_a, edificios.complejo_a)


def test_identificador_igual_en_otro_edificio_pasa(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    assert app_edificio.execute(
        "SELECT complejo_id, identificador FROM unidad ORDER BY complejo_id"
    ).fetchall() == sorted([(edificios.complejo_a, "1A"), (edificios.otro_complejo_a, "1A")])


@pytest.mark.parametrize("coeficiente", ["0", "-0.1", "1.000001"])
def test_coeficiente_invalido_falla_por_check(
    app_edificio: psycopg.Connection, edificios: Edificios, coeficiente: str
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        insertar_unidad(
            app_edificio,
            edificios.administracion_a,
            edificios.complejo_a,
            "2A",
            coeficiente=coeficiente,
        )


@pytest.mark.parametrize("coeficiente", ["0.000001", "1.000000"])
def test_extremos_del_coeficiente_se_guardan_como_decimal(
    app_edificio: psycopg.Connection, edificios: Edificios, coeficiente: str
) -> None:
    unidad = insertar_unidad(
        app_edificio,
        edificios.administracion_a,
        edificios.complejo_a,
        "2A",
        coeficiente=coeficiente,
    )
    assert app_edificio.execute(
        "SELECT coeficiente, superficie_m2, estado FROM unidad WHERE id = %s", (unidad,)
    ).fetchone() == (Decimal(coeficiente), Decimal("60.00"), None)


@pytest.mark.parametrize("asignacion", ["tipo = 'quincho'", "superficie_m2 = 0"])
def test_tipo_y_superficie_invalidos_fallan_por_check(
    app_edificio: psycopg.Connection, edificios: Edificios, asignacion: str
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        app_edificio.execute(
            f"UPDATE unidad SET {asignacion} WHERE id = %s",  # noqa: S608 (literales del test)
            (edificios.unidad_a,),
        )


@pytest.mark.parametrize("tipo", ["departamento", "cochera", "baulera", "local"])
def test_los_cuatro_tipos_de_d029_se_aceptan(
    app_edificio: psycopg.Connection, edificios: Edificios, tipo: str
) -> None:
    assert app_edificio.execute(
        "UPDATE unidad SET tipo = %s WHERE id = %s RETURNING tipo", (tipo, edificios.unidad_a)
    ).fetchone() == (tipo,)


def test_mover_unidad_a_edificio_existente_de_otra_administracion_falla_por_inmutabilidad(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(
        psycopg.errors.CheckViolation,
        match="La unidad no admite cambiar complejo_id ni administracion_id",
    ):
        app_edificio.execute(
            "UPDATE unidad SET complejo_id = %s WHERE id = %s",
            (edificios.complejo_b, edificios.unidad_a),
        )


def test_estado_migracion_arranca_pendiente_y_rechaza_un_estado_desconocido(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    assert app_edificio.execute(
        "SELECT localidad, estado_migracion FROM complejo WHERE id = %s", (edificios.complejo_a,)
    ).fetchone() == ("Mendoza", "pendiente")
    with pytest.raises(psycopg.errors.CheckViolation):
        app_edificio.execute(
            "UPDATE complejo SET estado_migracion = 'inventado' WHERE id = %s",
            (edificios.complejo_a,),
        )


@pytest.mark.parametrize("estado", ["pendiente", "confirmada", "sin_saldos_previos"])
def test_estados_de_migracion_validos(
    app_edificio: psycopg.Connection, edificios: Edificios, estado: str
) -> None:
    assert app_edificio.execute(
        "UPDATE complejo SET estado_migracion = %s WHERE id = %s RETURNING estado_migracion",
        (estado, edificios.complejo_a),
    ).fetchone() == (estado,)


@pytest.mark.parametrize("campo", ["tipo", "piso", "coeficiente", "superficie_m2"])
def test_datos_obligatorios_no_conservan_defaults_temporales(
    app_edificio: psycopg.Connection, edificios: Edificios, campo: str
) -> None:
    valores = {
        "administracion_id": edificios.administracion_a,
        "complejo_id": edificios.complejo_a,
        "identificador": "2A",
        "tipo": "departamento",
        "piso": "1",
        "coeficiente": "0.1",
        "superficie_m2": "60.00",
    }
    del valores[campo]
    with pytest.raises(psycopg.errors.NotNullViolation) as error:
        app_edificio.execute(
            psycopg.sql.SQL("INSERT INTO unidad ({}) VALUES ({})").format(
                psycopg.sql.SQL(", ").join(map(psycopg.sql.Identifier, valores)),
                psycopg.sql.SQL(", ").join(psycopg.sql.Placeholder() for _ in valores),
            ),
            list(valores.values()),
        )
    assert error.value.diag.column_name == campo


def test_localidad_es_obligatoria_sin_default_temporal(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(psycopg.errors.NotNullViolation) as error:
        app_edificio.execute(
            "INSERT INTO complejo (administracion_id, nombre) VALUES (%s, 'Sin localidad')",
            (edificios.administracion_a,),
        )
    assert error.value.diag.column_name == "localidad"


def test_downgrade_a_0004_y_upgrade_conservan_la_unidad_del_2a(
    base_del_edificio: BaseDeEdificio,
) -> None:
    base_del_edificio.migrar("downgrade", "0004")
    admin, complejo, unidad = uuid4(), uuid4(), uuid4()
    try:
        with base_del_edificio.conectar_app() as app, app.transaction():
            fijar_tenant(app, admin)
            app.execute("INSERT INTO administracion VALUES (%s, 'Prueba')", (admin,))
            app.execute("INSERT INTO complejo VALUES (%s, %s, 'Edificio 2a')", (complejo, admin))
            app.execute(
                "INSERT INTO unidad (id, administracion_id, complejo_id, nombre) "
                "VALUES (%s, %s, %s, 'Anterior')",
                (unidad, admin, complejo),
            )
        base_del_edificio.migrar("upgrade", "head")
        with base_del_edificio.conectar_app() as app, app.transaction():
            fijar_tenant(app, admin)
            assert app.execute(
                "SELECT identificador, tipo, piso, coeficiente, superficie_m2, estado "
                "FROM unidad WHERE id = %s",
                (unidad,),
            ).fetchone() == ("Anterior", "departamento", "", Decimal("1"), Decimal("1"), None)
        base_del_edificio.migrar("downgrade", "0004")
        with base_del_edificio.conectar_app() as app, app.transaction():
            fijar_tenant(app, admin)
            assert app.execute("SELECT nombre FROM unidad WHERE id = %s", (unidad,)).fetchone() == (
                "Anterior",
            )
    finally:
        base_del_edificio.migrar("upgrade", "head")
