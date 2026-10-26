"""0021: filas leídas como arranque, nunca conjuntos vacíos por RLS."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion


def arranque(base: BaseDeEdificio) -> psycopg.Connection:
    c = base.contenedor
    return psycopg.connect(
        host=c.get_container_host_ip(),
        port=c.get_exposed_port(5432),
        user=c.username,
        password=c.password,
        dbname=base.nombre,
        autocommit=True,
    )


def esquema(c: psycopg.Connection) -> list[tuple[object, ...]]:
    return c.execute(
        "SELECT column_name, data_type, is_nullable, column_default, "
        "numeric_precision, numeric_scale FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='configuracion_versionada' "
        "ORDER BY column_name"
    ).fetchall()


def insertar(
    c: psycopg.Connection,
    admin: object,
    complejo: object,
    persona: object,
    fecha: date,
    umbral: str | None = None,
) -> None:
    columnas = (
        "administracion_id,complejo_id,autor_id,vigente_desde,tasa_mensual,"
        "dias_de_gracia,forma_de_calculo,porcentaje_fondo,dia_de_vencimiento,"
        "modalidad_de_vencimiento"
    )
    valores = [
        admin,
        complejo,
        persona,
        fecha,
        "3.00",
        0,
        "proporcional_por_dia",
        "0.00",
        10,
        "unico",
    ]
    if umbral is not None:
        columnas += ",umbral_saldo_chico"
        valores.append(umbral)
    c.execute(
        sql.SQL("INSERT INTO configuracion_versionada ({}) VALUES ({})").format(
            sql.SQL(columnas), sql.SQL(",").join(sql.Placeholder() for _ in valores)
        ),
        valores,
    )


def test_0021_preserva_filas_y_restauracion(base_para_migraciones: BaseDeEdificio) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "0020")
    with arranque(base) as c:
        antes = esquema(c)
        base.migrar("upgrade", "0021")
        assert c.execute("SELECT count(*) FROM configuracion_versionada").fetchone() == (0,)
        for sentencia in (
            "UPDATE configuracion_versionada SET tasa_mensual=tasa_mensual WHERE false",
            "DELETE FROM configuracion_versionada WHERE false",
        ):
            with pytest.raises(
                psycopg.errors.RaiseException, match="configuracion_versionada no admite"
            ):
                c.execute(sentencia)
        base.migrar("downgrade", "0020")
        admin, complejo, persona = uuid4(), uuid4(), uuid4()
        c.execute("INSERT INTO administracion (id,nombre) VALUES (%s,'Inventada')", (admin,))
        c.execute(
            "INSERT INTO complejo (id,administracion_id,nombre,localidad) "
            "VALUES (%s,%s,'Inventado','Mendoza')",
            (complejo, admin),
        )
        c.execute(
            "INSERT INTO persona (id,administracion_id,nombre) VALUES (%s,%s,'Inventada')",
            (persona, admin),
        )
        for dia in (1, 2):
            insertar(c, admin, complejo, persona, date(2026, 11, dia))
        filas = c.execute(
            "SELECT to_jsonb(v) FROM configuracion_versionada v ORDER BY id"
        ).fetchall()
        assert len(filas) == 2
        base.migrar("upgrade", "0021")
        assert any(col[0] == "umbral_saldo_chico" for col in esquema(c))
        despues = c.execute(
            "SELECT to_jsonb(v) - 'umbral_saldo_chico', umbral_saldo_chico "
            "FROM configuracion_versionada v ORDER BY id"
        ).fetchall()
        assert [f[0] for f in despues] == [f[0] for f in filas]
        assert [f[1] for f in despues] == [Decimal("500.00")] * 2
        assert next(col for col in esquema(c) if col[0] == "umbral_saldo_chico")[2:] == (
            "NO",
            None,
            14,
            2,
        )
        with pytest.raises(psycopg.errors.NotNullViolation):
            insertar(c, admin, complejo, persona, date(2026, 11, 3))
        with pytest.raises(psycopg.errors.CheckViolation):
            insertar(c, admin, complejo, persona, date(2026, 11, 3), "-0.01")
        insertar(c, admin, complejo, persona, date(2026, 11, 3), "0.00")
        insertar(c, admin, complejo, persona, date(2026, 11, 4), "300.00")
        for sentencia in [
            "UPDATE configuracion_versionada SET tasa_mensual=tasa_mensual WHERE false",
            "DELETE FROM configuracion_versionada WHERE false",
            "INSERT INTO configuracion_versionada DEFAULT VALUES "
            "ON CONFLICT DO UPDATE SET tasa_mensual=3",
        ]:
            # ON CONFLICT necesita un destino válido para llegar al trigger.
            sentencia = sentencia.replace("ON CONFLICT DO", "ON CONFLICT (id) DO")
            with pytest.raises(
                psycopg.errors.RaiseException, match="configuracion_versionada no admite"
            ):
                c.execute(sentencia)
        with base.conectar_app() as app:
            with pytest.raises(psycopg.errors.InsufficientPrivilege) as error:
                app.execute("UPDATE configuracion_versionada SET umbral_saldo_chico=0 WHERE false")
            assert error.value.sqlstate == "42501"
        base.migrar("downgrade", "0020")
        assert esquema(c) == antes
        base.migrar("upgrade", "0021")
        assert (
            c.execute("SELECT umbral_saldo_chico FROM configuracion_versionada").fetchall()
            == [(Decimal("500.00"),)] * 4
        )
