"""3.6: sólo agregar, rangos, autor y concurrencia en PostgreSQL real."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import sql

from ._edificios import BaseDeEdificio, Edificios, fijar_tenant

pytestmark = pytest.mark.integracion


def insertar_version(
    app: psycopg.Connection, admin: UUID, complejo: UUID, autor: UUID, **cambios: Any
) -> UUID:
    valores = {
        "administracion_id": admin,
        "complejo_id": complejo,
        "autor_id": autor,
        "vigente_desde": date(2026, 11, 1),
        "tasa_mensual": "3.00",
        "umbral_saldo_chico": "500.00",
        "dias_de_gracia": 0,
        "forma_de_calculo": "proporcional_por_dia",
        "porcentaje_fondo": "0.00",
        "dia_de_vencimiento": 10,
        "modalidad_de_vencimiento": "unico",
        **cambios,
    }
    fila = app.execute(
        sql.SQL("INSERT INTO configuracion_versionada ({}) VALUES ({}) RETURNING id").format(
            sql.SQL(", ").join(map(sql.Identifier, valores)),
            sql.SQL(", ").join(sql.Placeholder() for _ in valores),
        ),
        tuple(valores.values()),
    ).fetchone()
    assert fila is not None
    return UUID(str(fila[0]))


def insertar_autor(app: psycopg.Connection, admin: UUID) -> UUID:
    autor = uuid4()
    app.execute(
        "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'Persona ficticia')",
        (autor, admin),
    )
    return autor


@pytest.fixture
def autor(app_edificio: psycopg.Connection, edificios: Edificios) -> UUID:
    return insertar_autor(app_edificio, edificios.administracion_a)


@pytest.mark.parametrize("rol", ["app", "migrador"])
@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE", "TRUNCATE"])
def test_escritura_real_se_rechaza_y_la_fila_queda_igual_tras_dos_up(
    base_del_edificio: BaseDeEdificio,
    app_edificio: psycopg.Connection,
    edificios: Edificios,
    autor: UUID,
    rol: str,
    operacion: str,
) -> None:
    vid = insertar_version(app_edificio, edificios.administracion_a, edificios.complejo_a, autor)
    # Otro usuario necesita ver la fila: confirmar la preparación antes del ataque.
    app_edificio.commit()
    conectar = (
        base_del_edificio.conectar_app if rol == "app" else base_del_edificio.conectar_migrador
    )
    with conectar() as conexion, conexion.transaction():
        fijar_tenant(conexion, edificios.administracion_a)
        fila = conexion.execute(
            "SELECT * FROM configuracion_versionada WHERE id = %s", (vid,)
        ).fetchone()
        assert fila is not None
        sentencia = {
            "UPDATE": "UPDATE configuracion_versionada SET tasa_mensual = '4.00' WHERE id = %s",
            "DELETE": "DELETE FROM configuracion_versionada WHERE id = %s",
            "TRUNCATE": "TRUNCATE configuracion_versionada",
        }[operacion]
        error = (
            psycopg.errors.InsufficientPrivilege if rol == "app" else psycopg.errors.RaiseException
        )
        mensaje = "permission denied" if rol == "app" else "configuracion_versionada no admite"
        with pytest.raises(error, match=mensaje), conexion.transaction():
            conexion.execute(sentencia, (vid,) if operacion != "TRUNCATE" else None)
        assert (
            conexion.execute(
                "SELECT * FROM configuracion_versionada WHERE id = %s", (vid,)
            ).fetchone()
            == fila
        )


@pytest.mark.parametrize(
    "cambios",
    [
        {"dia_de_vencimiento": 0},
        {"dia_de_vencimiento": 29},
        {"modalidad_de_vencimiento": "doble", "dia_segundo_vencimiento": 20},
        {"modalidad_de_vencimiento": "doble", "recargo_segundo_vencimiento": "5.00"},
        {"recargo_segundo_vencimiento": "5.00"},
        {"dia_segundo_vencimiento": 20},
        {
            "modalidad_de_vencimiento": "doble",
            "dia_segundo_vencimiento": 10,
            "recargo_segundo_vencimiento": "5.00",
        },
        {
            "modalidad_de_vencimiento": "doble",
            "dia_segundo_vencimiento": 29,
            "recargo_segundo_vencimiento": "5.00",
        },
        {
            "modalidad_de_vencimiento": "doble",
            "dia_segundo_vencimiento": 20,
            "recargo_segundo_vencimiento": "0.00",
        },
        {
            "modalidad_de_vencimiento": "doble",
            "dia_segundo_vencimiento": 20,
            "recargo_segundo_vencimiento": "20.01",
        },
        {"modalidad_de_vencimiento": "desconocida"},
        {"tasa_mensual": "-0.01"},
        {"tasa_mensual": "10.01"},
        {"tasa_mensual": "NaN"},
        {"dias_de_gracia": -1},
        {"dias_de_gracia": 32},
        {"forma_de_calculo": "capitalizado"},
        {"porcentaje_fondo": "-0.01"},
        {"porcentaje_fondo": "100.01"},
    ],
)
def test_rangos_y_coherencia_por_sql(
    app_edificio: psycopg.Connection, edificios: Edificios, autor: UUID, cambios: dict[str, Any]
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        insertar_version(
            app_edificio, edificios.administracion_a, edificios.complejo_a, autor, **cambios
        )


@pytest.mark.parametrize("recargo", ["0.01", "20.00"])
def test_doble_valido_guarda_decimales_autor_y_fecha(
    app_edificio: psycopg.Connection, edificios: Edificios, autor: UUID, recargo: str
) -> None:
    vid = insertar_version(
        app_edificio,
        edificios.administracion_a,
        edificios.complejo_a,
        autor,
        modalidad_de_vencimiento="doble",
        dia_segundo_vencimiento=28,
        recargo_segundo_vencimiento=recargo,
        tasa_mensual="10.00",
        porcentaje_fondo="100.00",
        dias_de_gracia=31,
        forma_de_calculo="mes_entero",
    )
    fila = app_edificio.execute(
        "SELECT autor_id, recargo_segundo_vencimiento, tasa_mensual, porcentaje_fondo, "
        "creada_en IS NOT NULL FROM configuracion_versionada WHERE id = %s",
        (vid,),
    ).fetchone()
    assert fila == (autor, Decimal(recargo), Decimal("10.00"), Decimal("100.00"), True)


def test_autor_existente_de_otra_administracion_falla_por_fk(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    fijar_tenant(app_edificio, edificios.administracion_b)
    ajeno = insertar_autor(app_edificio, edificios.administracion_b)
    fijar_tenant(app_edificio, edificios.administracion_a)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        insertar_version(app_edificio, edificios.administracion_a, edificios.complejo_a, ajeno)


def test_dos_inserciones_concurrentes_dejan_exactamente_una_version(
    base_del_edificio: BaseDeEdificio,
    app_edificio: psycopg.Connection,
    edificios: Edificios,
    autor: UUID,
) -> None:
    app_edificio.commit()
    barrera = Barrier(2)

    def competir() -> str:
        with base_del_edificio.conectar_app() as app:
            try:
                with app.transaction():
                    app.execute("SET LOCAL lock_timeout = '5s'")
                    fijar_tenant(app, edificios.administracion_a)
                    barrera.wait(timeout=5)
                    insertar_version(app, edificios.administracion_a, edificios.complejo_a, autor)
                return "guardada"
            except psycopg.errors.UniqueViolation:
                return "repetida"

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(ejecutor.map(lambda _: competir(), range(2)))
    assert sorted(resultados) == ["guardada", "repetida"]
    fijar_tenant(app_edificio, edificios.administracion_a)
    assert app_edificio.execute("SELECT count(*) FROM configuracion_versionada").fetchone() == (1,)


def test_downgrade_upgrade_de_la_configuracion(base_del_edificio: BaseDeEdificio) -> None:
    base_del_edificio.migrar("downgrade", "0008")
    try:
        with base_del_edificio.conectar_app() as app:
            assert app.execute("SELECT to_regclass('configuracion_versionada')").fetchone() == (
                None,
            )
    finally:
        base_del_edificio.migrar("upgrade", "head")
    with base_del_edificio.conectar_app() as app:
        assert app.execute("SELECT count(*) FROM configuracion_versionada").fetchone() == (0,)
