"""H-005 · C19: `carga_de_saldo_inicial` y `origen_de_saldo_inicial` (design D5, D10) son de sólo
agregar, sus CHECK frenan las filas mal formadas y un origen no se cuelga de otra cuenta.

Las filas se insertan a mano como la aplicación: este archivo prueba las tablas, no el caso de
uso."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import errors
from sqlalchemy import text

from proptech_core.cuenta_corriente.aplicacion import emisiones
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

from .._cuenta_corriente import Mundo, sembrar, sesion_app
from .._edificios import BaseDeEdificio, fijar_tenant
from ..test_umbral_migracion import arranque
from ._h005 import MIGRACION, SEP, TABLAS_NUEVAS, d, dia

pytestmark = pytest.mark.integracion

FIRMA = "v1:" + "a" * 64


@dataclass(frozen=True)
class Libro:
    mundo: Mundo
    cuenta_0: UUID
    cuenta_1: UUID
    obligacion_0: UUID
    obligacion_1: UUID


@pytest.fixture
def libro(base_del_edificio: BaseDeEdificio) -> Libro:
    mundo = sembrar(base_del_edificio)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emisiones.registrar_emision(
            s,
            mundo.identidad,
            emision_id=uuid4(),
            complejo_id=mundo.complejo,
            periodo=SEP,
            obligaciones=[
                ObligacionAEmitir(mundo.unidades[n], dia(9, 10), d("1000.00"), d("0.00"), d("0.00"))
                for n in (0, 1)
            ],
            request_id=uuid4(),
        )
        c0, c1 = (r.cuentas[mundo.unidades[n]] for n in (0, 1))
        o0, o1 = (
            UUID(
                str(
                    s.execute(
                        text("SELECT id FROM obligacion WHERE cuenta_id = :c"), {"c": c}
                    ).scalar_one()
                )
            )
            for c in (c0, c1)
        )
        s.commit()
    return Libro(mundo, c0, c1, o0, o1)


@pytest.fixture
def app(base_del_edificio: BaseDeEdificio, libro: Libro) -> Iterator[psycopg.Connection]:
    with base_del_edificio.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, libro.mundo.admin)
        try:
            yield c
        finally:
            c.rollback()


def exigir_tablas(c: psycopg.Connection) -> None:
    for tabla in TABLAS_NUEVAS:
        fila = c.execute("SELECT to_regclass(%s)", (tabla,)).fetchone()
        assert fila is not None and fila[0] is not None, f"falta la tabla {tabla} (0035)"


def carga(c: psycopg.Connection, libro: Libro, **cambios: Any) -> UUID:
    datos: dict[str, Any] = {
        "origen": "importador",
        "archivo": "saldos-octubre.xlsx",
        "motivo": None,
        "firma": FIRMA,
    }
    datos.update(cambios)
    i = uuid4()
    c.execute(
        "INSERT INTO carga_de_saldo_inicial (id, administracion_id, complejo_id, operacion_id, "
        "fecha_de_migracion, origen, archivo, motivo, firma_del_pedido, registrado_por, "
        "request_id, registrado_en) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())",
        (
            i,
            libro.mundo.admin,
            libro.mundo.complejo,
            uuid4(),
            MIGRACION,
            datos["origen"],
            datos["archivo"],
            datos["motivo"],
            datos["firma"],
            libro.mundo.persona,
            uuid4(),
        ),
    )
    return i


def origen(
    c: psycopg.Connection,
    libro: Libro,
    carga_id: UUID,
    *,
    fila: int | None = 7,
    cuenta: UUID | None = None,
    obligacion: UUID | None = None,
    movimiento: UUID | None = None,
    sentido: str | None = None,
) -> UUID:
    i = uuid4()
    c.execute(
        "INSERT INTO origen_de_saldo_inicial (id, administracion_id, complejo_id, carga_id, "
        "cuenta_id, fila, obligacion_id, movimiento_id, sentido_del_movimiento) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            i,
            libro.mundo.admin,
            libro.mundo.complejo,
            carga_id,
            cuenta or libro.cuenta_0,
            fila,
            obligacion,
            movimiento,
            sentido,
        ),
    )
    return i


def test_c19_las_tablas_son_de_solo_agregar(app: psycopg.Connection) -> None:
    exigir_tablas(app)
    from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

    for tabla in TABLAS_NUEVAS:
        assert tabla in TABLAS_DE_SOLO_AGREGAR, f"{tabla} no está en TABLAS_DE_SOLO_AGREGAR"


def test_c19_una_carga_y_su_origen_bien_formados_entran(
    libro: Libro, app: psycopg.Connection
) -> None:
    """Control de los CHECK: una carga manual (en un savepoint que se deshace, porque hay una sola
    carga por edificio, D5), una del importador y un origen ligado a una obligación de su misma
    cuenta entran."""
    exigir_tablas(app)

    class _Deshacer(Exception):
        pass

    with pytest.raises(_Deshacer), app.transaction():
        carga(app, libro, origen="manual", archivo=None, motivo="Cuaderno")
        raise _Deshacer
    k = carga(app, libro)
    origen(app, libro, k, obligacion=libro.obligacion_0)


@pytest.mark.parametrize("tabla", TABLAS_NUEVAS)
def test_c19_el_origen_no_se_edita(
    base_del_edificio: BaseDeEdificio, libro: Libro, app: psycopg.Connection, tabla: str
) -> None:
    """Escenario: El origen no se edita"""
    exigir_tablas(app)
    k = carga(app, libro)
    o = origen(app, libro, k, obligacion=libro.obligacion_0)
    app.commit()
    fijar_tenant(app, libro.mundo.admin)
    fila_id = k if tabla == "carga_de_saldo_inicial" else o
    for sentencia in (
        f"UPDATE {tabla} SET administracion_id = administracion_id WHERE id = %s",  # noqa: S608
        f"DELETE FROM {tabla} WHERE id = %s",  # noqa: S608
    ):
        with pytest.raises(errors.InsufficientPrivilege) as e, app.transaction():
            app.execute(sentencia, (fila_id,))
        assert e.value.sqlstate == "42501"
    with arranque(base_del_edificio) as c:
        for sentencia, args in (
            (f"UPDATE {tabla} SET administracion_id = administracion_id WHERE id = %s", (fila_id,)),  # noqa: S608
            (f"DELETE FROM {tabla} WHERE id = %s", (fila_id,)),  # noqa: S608
            (f"TRUNCATE {tabla} CASCADE", ()),
        ):
            with pytest.raises(errors.RaiseException) as e2, c.transaction():
                c.execute(sentencia, args)
            assert e2.value.sqlstate == "P0001"
        fila = c.execute(f"SELECT count(*) FROM {tabla} WHERE id = %s", (fila_id,)).fetchone()  # noqa: S608
        assert fila == (1,), "la fila cambió"


INVALIDOS_DE_CARGA: dict[str, dict[str, Any]] = {
    "importador_sin_archivo": {"origen": "importador", "archivo": None},
    "manual_sin_motivo": {"origen": "manual", "archivo": None, "motivo": None},
    "origen_fuera_del_vocabulario": {"origen": "planilla"},
    "firma_mal_formada": {"firma": "v1:" + "a" * 63},
    "firma_sin_version": {"firma": "a" * 64},
}


@pytest.mark.parametrize("caso", sorted(INVALIDOS_DE_CARGA))
def test_c19_el_check_frena_una_carga_mal_formada(
    libro: Libro, app: psycopg.Connection, caso: str
) -> None:
    exigir_tablas(app)
    with pytest.raises(errors.CheckViolation), app.transaction():
        carga(app, libro, **INVALIDOS_DE_CARGA[caso])


def test_c19_el_check_frena_una_fila_menor_que_uno(libro: Libro, app: psycopg.Connection) -> None:
    exigir_tablas(app)
    k = carga(app, libro)
    with pytest.raises(errors.CheckViolation), app.transaction():
        origen(app, libro, k, fila=0, obligacion=libro.obligacion_0)


def test_c19_el_check_exige_una_sola_referencia(libro: Libro, app: psycopg.Connection) -> None:
    exigir_tablas(app)
    k = carga(app, libro)
    with pytest.raises(errors.CheckViolation), app.transaction():
        origen(app, libro, k, obligacion=libro.obligacion_0, movimiento=uuid4(), sentido="debito")
    with pytest.raises(errors.CheckViolation), app.transaction():
        origen(app, libro, k)


def test_c19_un_origen_no_se_cuelga_de_otra_cuenta(libro: Libro, app: psycopg.Connection) -> None:
    exigir_tablas(app)
    k = carga(app, libro)
    with pytest.raises(errors.ForeignKeyViolation), app.transaction():
        origen(app, libro, k, cuenta=libro.cuenta_0, obligacion=libro.obligacion_1)
