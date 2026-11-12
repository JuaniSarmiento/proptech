"""H-010 · C13: `ajuste_de_saldo_inicial` (design D8, D10, E11) es de sólo agregar, aislada por
administración, ligada a la obligación de su misma cuenta, con el motivo controlado por CHECK; y la
acción `ajustar_saldo_inicial` está en el vocabulario y en la matriz (E6).

Las filas se insertan a mano como la aplicación: este archivo prueba la tabla, no el caso de uso.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import errors

from .._edificios import fijar_tenant
from ..test_umbral_migracion import arranque
from ._h010 import ACCION, MOTIVO, TABLA, Mundo

pytestmark = pytest.mark.integracion


@dataclass(frozen=True)
class Libro:
    mundo: Mundo
    cuenta_a: UUID
    cuenta_b: UUID
    obligacion_a: UUID
    obligacion_b: UUID


@pytest.fixture
def libro(mundo: Mundo) -> Libro:
    """Dos cuentas (`1A` y `1B`) con una obligación cada una, emitidas con el caso de uso real."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import emisiones
    from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

    from .._cuenta_corriente import sesion_app

    with sesion_app(mundo.base, mundo.admin) as s:
        emisiones.registrar_emision(
            s,
            mundo.identidad(),
            emision_id=uuid4(),
            complejo_id=mundo.edificio,
            periodo=date(2026, 9, 1),
            obligaciones=[
                ObligacionAEmitir(
                    mundo.unidades[u],
                    date(2026, 9, 10),
                    Dinero("1000.00"),
                    Dinero("0.00"),
                    Dinero("0.00"),
                )
                for u in ("1A", "1B")
            ],
            request_id=uuid4(),
        )
        s.commit()
    ids = {}
    for u in ("1A", "1B"):
        cuenta, obligacion = mundo.filas(
            "SELECT c.id, o.id FROM cuenta c JOIN obligacion o ON o.cuenta_id = c.id "
            "WHERE c.unidad_id = %s",
            (mundo.unidades[u],),
        )[0]
        ids[u] = (UUID(str(cuenta)), UUID(str(obligacion)))
    return Libro(mundo, ids["1A"][0], ids["1B"][0], ids["1A"][1], ids["1B"][1])


@pytest.fixture
def app(libro: Libro) -> Iterator[psycopg.Connection]:
    with libro.mundo.base.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, libro.mundo.admin)
        try:
            yield c
        finally:
            c.rollback()


def exigir(c: psycopg.Connection) -> None:
    fila = c.execute("SELECT to_regclass(%s)", (TABLA,)).fetchone()
    assert fila is not None and fila[0] is not None, f"falta la tabla {TABLA} (0039)"


def insertar(
    c: psycopg.Connection,
    libro: Libro,
    *,
    cuenta: UUID | None = None,
    obligacion: UUID | None = None,
    motivo: str = MOTIVO,
    operacion: UUID | None = None,
) -> UUID:
    i = uuid4()
    c.execute(
        f"INSERT INTO {TABLA} (id, administracion_id, complejo_id, cuenta_id, obligacion_id, "  # noqa: S608
        "operacion_id, motivo, registrado_por, request_id, registrado_en) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())",
        (
            i,
            libro.mundo.admin,
            libro.mundo.edificio,
            cuenta or libro.cuenta_a,
            obligacion or libro.obligacion_a,
            operacion or uuid4(),
            motivo,
            libro.mundo.personas["admin_principal"],
            uuid4(),
        ),
    )
    return i


def test_c13_la_tabla_esta_en_la_lista_de_solo_agregar() -> None:
    from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

    assert TABLA in TABLAS_DE_SOLO_AGREGAR, f"{TABLA} falta en TABLAS_DE_SOLO_AGREGAR (D10, L-083)"


def test_c13_el_registro_del_ajuste_no_se_edita(libro: Libro, app: psycopg.Connection) -> None:
    """Escenario: El registro del ajuste no se edita"""
    exigir(app)
    fila_id = insertar(app, libro)
    app.commit()
    fijar_tenant(app, libro.mundo.admin)
    for sentencia in (
        f"UPDATE {TABLA} SET motivo = motivo WHERE id = %s",  # noqa: S608
        f"DELETE FROM {TABLA} WHERE id = %s",  # noqa: S608
    ):
        with pytest.raises(errors.InsufficientPrivilege) as e, app.transaction():
            app.execute(sentencia, (fila_id,))
        assert e.value.sqlstate == "42501"
    with arranque(libro.mundo.base) as c:
        for sentencia, args in (
            (f"UPDATE {TABLA} SET motivo = motivo WHERE id = %s", (fila_id,)),  # noqa: S608
            (f"DELETE FROM {TABLA} WHERE id = %s", (fila_id,)),  # noqa: S608
            (f"TRUNCATE {TABLA} CASCADE", ()),
        ):
            with pytest.raises(errors.RaiseException) as e2, c.transaction():
                c.execute(sentencia, args)
            assert e2.value.sqlstate == "P0001"
        fila = c.execute(f"SELECT count(*) FROM {TABLA} WHERE id = %s", (fila_id,)).fetchone()  # noqa: S608
        assert fila == (1,), "la fila cambió"


def test_c13_otra_administracion_no_ve_el_ajuste(libro: Libro, app: psycopg.Connection) -> None:
    exigir(app)
    insertar(app, libro)
    app.commit()
    m = libro.mundo
    assert m.uno(f"SELECT count(*) FROM {TABLA}") == 1  # noqa: S608
    assert m.uno(f"SELECT count(*) FROM {TABLA}", admin=m.admin_b) == 0, (  # noqa: S608
        "la administración B no ve los ajustes de A"
    )


def test_c13_un_ajuste_no_se_cuelga_de_otra_cuenta(libro: Libro, app: psycopg.Connection) -> None:
    exigir(app)
    with pytest.raises(errors.ForeignKeyViolation), app.transaction():
        insertar(app, libro, cuenta=libro.cuenta_a, obligacion=libro.obligacion_b)
    insertar(app, libro, cuenta=libro.cuenta_b, obligacion=libro.obligacion_b)  # control


@pytest.mark.parametrize("motivo", ["", "   ", "x" * 501], ids=["vacio", "en_blanco", "501"])
def test_c13_el_check_frena_un_motivo_invalido(
    libro: Libro, app: psycopg.Connection, motivo: str
) -> None:
    exigir(app)
    with pytest.raises(errors.CheckViolation), app.transaction():
        insertar(app, libro, motivo=motivo)


def test_c13_una_operacion_es_unica_por_administracion(
    libro: Libro, app: psycopg.Connection
) -> None:
    exigir(app)
    operacion = uuid4()
    insertar(app, libro, operacion=operacion)
    with pytest.raises(errors.UniqueViolation), app.transaction():
        insertar(
            app, libro, cuenta=libro.cuenta_b, obligacion=libro.obligacion_b, operacion=operacion
        )


def test_c13_la_accion_esta_en_el_vocabulario_y_en_la_matriz(mundo: Mundo) -> None:
    nombres = {f[0] for f in mundo.filas("SELECT nombre FROM accion_de_auditoria")}
    assert ACCION in nombres, f"falta {ACCION} en accion_de_auditoria (0039)"
    from proptech_core.acceso.dominio import permisos

    assert ACCION in {a.value for a in permisos.Accion}, "falta la acción en `Accion`"
    accion = permisos.Accion(ACCION)
    edificio = uuid4()

    def puede(rol: str, complejo: object, unidad: object = None, vinculo: object = None) -> bool:
        asignacion = permisos.Asignacion(rol, complejo, unidad, vinculo)  # type: ignore[arg-type]
        return permisos.puede([asignacion], accion, edificio)

    assert puede("super_admin", None)
    assert puede("administrador", None)
    assert not puede("administrador", edificio), "el administrador por edificio no ajusta (E6)"
    assert not puede("contador", None)
    assert not puede("auxiliar", edificio)
    assert not puede("consejo", edificio)
    assert not puede("vecino", edificio, uuid4(), "propietario")
    assert not puede("vecino", edificio, uuid4(), "inquilino")
