"""Rollback vacío, conservación de datos y dump completo del esquema 0022 (1.1/1.4)."""

import re
from pathlib import Path

import pytest
from psycopg import sql

from ._edificios import BaseDeEdificio, devolver_tabla_al_migrador
from ._libro import LIBRO, sembrar_libro
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion


POSTERIORES_AL_LIBRO = (
    "tramo_de_interes",
    "carga_de_saldo_inicial",
    "origen_de_saldo_inicial",
    "aceptacion_de_diferencias",
    "ajuste_de_saldo_inicial",
    "liquidacion",
    "categoria_de_liquidacion",
    "grupo_de_liquidacion",
    "composicion_de_grupo",
    "linea_de_liquidacion",
    "alerta_aceptada",
    "cargo_cobrado_de_menos",
    "pdf_de_expensa",
    "comprobante_de_pago",
    "pago_informado",
    "parte_de_pago",
    "evento_de_pago",
    "movimiento_de_pago",
    "cbu_de_unidad",
    "cambio_de_titular",
    "parte_de_cambio_de_titular",
)


def devolver_tramos(base: BaseDeEdificio) -> None:
    """La `0035` y la `0034` bajan antes que la `0024`: sus tablas vuelven al migrador como las
    del libro. La `0042` además altera `evento_de_emision` al bajar, la `0046` y la `0047` alteran
    `movimiento` y la `0051` también `obligacion` (D-115.3)."""
    with arranque(base) as c:
        c.execute("ALTER TABLE evento_de_emision OWNER TO proptech_migrador")
        c.execute("ALTER TABLE movimiento OWNER TO proptech_migrador")
        c.execute("ALTER TABLE obligacion OWNER TO proptech_migrador")
        for tabla in POSTERIORES_AL_LIBRO:
            devolver_tabla_al_migrador(c, tabla, "proptech_migrador")


def devolver_libro(base: BaseDeEdificio) -> None:
    with arranque(base) as c:
        for tabla in (*LIBRO, *POSTERIORES_AL_LIBRO):
            devolver_tabla_al_migrador(c, tabla, "proptech_migrador")


def dump(base: BaseDeEdificio, destino: Path) -> str:
    comando = ["pg_dump", "--schema-only", "-U", base.contenedor.username, "-d", base.nombre]
    codigo, salida = base.contenedor.exec(comando)
    assert codigo == 0
    texto = salida.decode()
    # PG18 usa tokens aleatorios de psql. No se filtra DDL ni ACL.
    texto = re.sub(r"^\\(?:un)?restrict .*\n", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"^-- Dumped (?:from|by) .*\n", "", texto, flags=re.MULTILINE)
    destino.write_text(texto)
    print(f"DUMP: {' '.join(comando)} -> {destino}")
    return texto


def test_ciclo_0022_0024_0022_conserva_esquema(
    base_para_migraciones: BaseDeEdificio, tmp_path: Path
) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "0022")
    base.roles("despues")
    antes = dump(base, tmp_path / "0022-antes.sql")
    base.roles("antes")
    base.migrar("upgrade", "head")
    base.roles("despues")
    devolver_libro(base)
    base.migrar("downgrade", "0022")
    despues = dump(base, tmp_path / "0022-despues.sql")
    assert despues == antes
    base.roles("antes")
    base.migrar("upgrade", "head")
    base.roles("despues")
    with base.conectar_app() as c:
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0051",)
        for tabla in LIBRO:
            assert c.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(tabla))
            ).fetchone() == (0,)


def test_downgrade_con_fila_conserva_el_libro(base_para_migraciones: BaseDeEdificio) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "head")
    base.roles("despues")
    with base.conectar_app() as c, c.transaction():
        datos = sembrar_libro(c)
        cuenta = datos.cuenta
    devolver_libro(base)
    rechazo = None
    try:
        base.migrar("downgrade", "0022")
    except AssertionError as e:
        rechazo = str(e)
    with arranque(base) as c:
        tabla = c.execute("SELECT to_regclass('public.cuenta') IS NOT NULL").fetchone()
        assert tabla == (True,), (
            "el downgrade borró el libro con filas, invisible al dueño por FORCE sin tenant"
        )
        assert c.execute("SELECT count(*) FROM cuenta WHERE id=%s", (cuenta,)).fetchone() == (1,)
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0051",)
    assert rechazo is not None and "tiene filas" in rechazo
    base.roles("despues")


def test_0024_con_correccion_auditada_no_baja(base_del_edificio: BaseDeEdificio) -> None:
    from uuid import uuid4

    from proptech_core.acceso.dominio.identidad import Identidad
    from proptech_core.cuenta_corriente.aplicacion.correcciones import PedidoDeCorreccion, corregir

    from ._cuenta_corriente import sesion_app

    base = base_del_edificio
    with base.conectar_app() as c, c.transaction():
        datos = sembrar_libro(c)
    with sesion_app(base, datos.admin) as s:
        movimiento = corregir(
            s,
            Identidad(datos.admin, datos.persona),
            complejo_id=datos.edificios.complejo_a,
            pedido=PedidoDeCorreccion(
                "contra_asiento",
                uuid4(),
                "Prueba del punto de no retorno",
                movimiento_id=datos.pago,
            ),
            request_id=uuid4(),
        )
        s.commit()
    devolver_tramos(base)
    rechazo = None
    try:
        base.migrar("downgrade", "0023")
    except AssertionError as error:
        rechazo = str(error)
    base.roles("despues")
    assert rechazo is not None and "ForeignKeyViolation" in rechazo, rechazo
    # SQLSTATE del mismo DELETE de 0024, sin aceptar otro fallo del CLI como prueba.
    import psycopg

    with base.conectar_migrador() as c:
        with pytest.raises(psycopg.errors.ForeignKeyViolation) as error_fk:
            c.execute("DELETE FROM accion_de_auditoria WHERE nombre='corregir_movimiento'")
        assert error_fk.value.sqlstate == "23503"
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0051",)
    with sesion_app(base, datos.admin) as s:
        from sqlalchemy import text

        assert (
            s.execute(
                text(
                    "SELECT count(*) FROM auditoria WHERE accion='corregir_movimiento' "
                    "AND entidad_id=:m"
                ),
                {"m": movimiento},
            ).scalar_one()
            == 1
        )
        assert (
            s.execute(
                text("SELECT count(*) FROM movimiento WHERE id=:m"), {"m": movimiento}
            ).scalar_one()
            == 1
        )
