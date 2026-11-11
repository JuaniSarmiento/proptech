"""H-005, tarea 2.1 (parte de saldo inicial): `carga_de_saldo_inicial` y `origen_de_saldo_inicial`
(design D5, D10) llevan el patrón del libro.

Una defensa por test, parametrizado por tabla donde la defensa es común: cada aserción nombra la
tabla y mata el mutante que apaga esa defensa y deja las demás (matriz de
`openspec/changes/intereses-saldo-inicial-y-moroso/tasks.md`, 2.1). Las filas se insertan a mano,
como en `test_intereses_esquema`: este archivo prueba las tablas, no el caso de uso.
"""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import errors, sql

from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

from ._edificios import BaseDeEdificio, fijar_tenant
from ._libro import Libro, insertar, sembrar_libro
from .test_libro_esquema import libro as _fixture_libro  # noqa: F401
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion

CARGA, ORIGEN = "carga_de_saldo_inicial", "origen_de_saldo_inicial"
TABLAS = (CARGA, ORIGEN)
FIRMA = "v1:" + "a" * 64


def _carga(libro: Libro, **cambios: Any) -> dict[str, Any]:
    fila: dict[str, Any] = {
        "id": uuid4(),
        "administracion_id": libro.admin,
        "complejo_id": libro.edificios.complejo_a,
        "operacion_id": uuid4(),
        "fecha_de_migracion": date(2026, 10, 31),
        "origen": "importador",
        "archivo": "saldos-octubre.xlsx",
        "motivo": None,
        "firma_del_pedido": FIRMA,
        "registrado_por": libro.persona,
        "request_id": uuid4(),
        "registrado_en": datetime(2026, 11, 1, tzinfo=UTC),
    }
    return {**fila, **cambios}


def _origen(libro: Libro, carga_id: UUID, **cambios: Any) -> dict[str, Any]:
    fila: dict[str, Any] = {
        "id": uuid4(),
        "administracion_id": libro.admin,
        "complejo_id": libro.edificios.complejo_a,
        "carga_id": carga_id,
        "cuenta_id": libro.cuenta,
        "fila": 7,
        "obligacion_id": libro.obligacion,
        "movimiento_id": None,
        "sentido_del_movimiento": None,
    }
    return {**fila, **cambios}


def _agregar_carga(libro: Libro, **cambios: Any) -> dict[str, Any]:
    fila = _carga(libro, **cambios)
    insertar(libro.conexion, CARGA, fila)
    return fila


def _agregar_origen(libro: Libro, carga_id: UUID, **cambios: Any) -> dict[str, Any]:
    fila = _origen(libro, carga_id, **cambios)
    insertar(libro.conexion, ORIGEN, fila)
    return fila


def _una_de_cada(libro: Libro) -> tuple[dict[str, Any], dict[str, Any]]:
    carga = _agregar_carga(libro)
    return carga, _agregar_origen(libro, carga["id"])


@pytest.mark.parametrize("tabla", TABLAS)
def test_la_tabla_esta_declarada_con_sus_tres_triggers(tabla: str) -> None:
    assert tabla in TABLAS_DE_SOLO_AGREGAR, f"{tabla} no está en TABLAS_DE_SOLO_AGREGAR"
    declarada = TABLAS_DE_SOLO_AGREGAR[tabla]
    assert declarada.mensaje == f"{tabla} no admite"
    assert declarada.triggers == frozenset(
        {
            f"trg_{tabla}_sin_update_delete",
            f"trg_{tabla}_sin_truncate",
            f"trg_{tabla}_sin_update_delete_por_sentencia",
        }
    )


@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE", "TRUNCATE"])
@pytest.mark.parametrize("tabla", TABLAS)
def test_la_app_no_tiene_permiso_de_edicion(libro: Libro, tabla: str, operacion: str) -> None:
    """Sin el REVOKE de `roles despues` el trigger rechaza con P0001 en vez de 42501: la
    aserción mira el SQLSTATE."""
    _una_de_cada(libro)
    consultas = {
        "UPDATE": f"UPDATE {tabla} SET administracion_id = administracion_id",  # noqa: S608
        "DELETE": f"DELETE FROM {tabla}",  # noqa: S608
        "TRUNCATE": f"TRUNCATE {tabla} CASCADE",
    }
    with pytest.raises(psycopg.Error) as e, libro.conexion.transaction():
        libro.conexion.execute(consultas[operacion])
    assert e.value.sqlstate == "42501", f"{tabla} {operacion}: {e.value.sqlstate}"


@pytest.mark.parametrize("tabla", TABLAS)
def test_otra_administracion_no_ve_las_filas(libro: Libro, tabla: str) -> None:
    """Sin `ENABLE` ni política, la app de B vería las filas de A: ninguna otra defensa filtra
    la lectura."""
    c = libro.conexion
    assert c.execute(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
    ).fetchone() == (False, False)
    carga, origen = _una_de_cada(libro)
    fila_id = carga["id"] if tabla == CARGA else origen["id"]
    assert c.execute(
        sql.SQL("SELECT count(*) FROM {} WHERE id = %s").format(sql.Identifier(tabla)),
        (fila_id,),
    ).fetchone() == (1,)
    fijar_tenant(c, libro.edificios.administracion_b)
    assert c.execute(
        sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(tabla))
    ).fetchone() == (0,), f"otra administración ve filas de {tabla}"


def test_un_origen_no_se_cuelga_de_la_obligacion_de_otra_cuenta(libro: Libro) -> None:
    """Sin `cuenta_id` en la FK a `obligacion`, ningún CHECK mira la cuenta de la obligación."""
    carga = _agregar_carga(libro)
    with pytest.raises(errors.ForeignKeyViolation) as e, libro.conexion.transaction():
        _agregar_origen(libro, carga["id"], cuenta_id=libro.cuenta_personal)
    assert e.value.diag.constraint_name == "fk_origen_obligacion"


def test_un_origen_no_se_cuelga_del_movimiento_de_otra_cuenta(libro: Libro) -> None:
    """Ídem para `movimiento`: el crédito o el interés es de la misma cuenta que el origen."""
    carga = _agregar_carga(libro)
    with pytest.raises(errors.ForeignKeyViolation) as e, libro.conexion.transaction():
        _agregar_origen(
            libro,
            carga["id"],
            cuenta_id=libro.cuenta_personal,
            obligacion_id=None,
            movimiento_id=libro.interes,
            sentido_del_movimiento="debito",
        )
    assert e.value.diag.constraint_name == "fk_origen_movimiento"


def test_un_origen_con_movimiento_de_su_cuenta_entra(libro: Libro) -> None:
    """Control de la FK a `movimiento`: el interés importado de la misma cuenta se liga."""
    carga = _agregar_carga(libro)
    _agregar_origen(
        libro,
        carga["id"],
        obligacion_id=None,
        movimiento_id=libro.interes,
        sentido_del_movimiento="debito",
    )


def test_un_origen_no_ignora_su_movimiento_sin_sentido(libro: Libro) -> None:
    """Con el sentido nulo la FK compuesta no se evalúa (MATCH SIMPLE): el CHECK lo impide."""
    carga = _agregar_carga(libro)
    with pytest.raises(errors.CheckViolation) as e, libro.conexion.transaction():
        _agregar_origen(
            libro,
            carga["id"],
            cuenta_id=libro.cuenta_personal,
            obligacion_id=None,
            movimiento_id=libro.interes,
            sentido_del_movimiento=None,
        )
    assert e.value.diag.constraint_name == "ck_origen_sentido"


def test_un_origen_no_se_cuelga_de_una_carga_de_otro_edificio(libro: Libro) -> None:
    """La FK compuesta a la carga fija el edificio del origen."""
    carga = _agregar_carga(libro)
    with pytest.raises(errors.ForeignKeyViolation) as e, libro.conexion.transaction():
        _agregar_origen(libro, carga["id"], complejo_id=libro.edificios.otro_complejo_a)
    assert e.value.diag.constraint_name == "fk_origen_carga"


@pytest.mark.parametrize("tabla", TABLAS)
def test_la_fila_no_se_cuelga_de_un_edificio_de_otra_administracion(
    libro: Libro, tabla: str
) -> None:
    """La FK a `complejo` fija que el edificio es de la administración."""
    carga = _agregar_carga(libro)
    with pytest.raises(errors.ForeignKeyViolation) as e, libro.conexion.transaction():
        if tabla == CARGA:
            _agregar_carga(libro, complejo_id=libro.edificios.complejo_b)
        else:
            _agregar_origen(libro, carga["id"], complejo_id=libro.edificios.complejo_b)
    assert e.value.diag.constraint_name == (
        "fk_carga_complejo" if tabla == CARGA else "fk_origen_complejo"
    )


def test_una_carga_no_se_registra_por_una_persona_de_otra_administracion(libro: Libro) -> None:
    with pytest.raises(errors.ForeignKeyViolation) as e, libro.conexion.transaction():
        _agregar_carga(libro, registrado_por=uuid4())
    assert e.value.diag.constraint_name == "fk_carga_persona"


def test_hay_una_sola_carga_por_edificio(libro: Libro) -> None:
    _agregar_carga(libro)
    with pytest.raises(errors.UniqueViolation) as e, libro.conexion.transaction():
        _agregar_carga(libro)
    assert e.value.diag.constraint_name == "uq_carga_complejo"


def test_una_operacion_no_se_repite_entre_cargas(libro: Libro) -> None:
    """El único por operación va aparte del de edificio: con otro edificio el `operacion_id`
    repetido sigue frenado."""
    primera = _agregar_carga(libro)
    with pytest.raises(errors.UniqueViolation) as e, libro.conexion.transaction():
        _agregar_carga(
            libro, complejo_id=libro.edificios.otro_complejo_a, operacion_id=primera["operacion_id"]
        )
    assert e.value.diag.constraint_name == "uq_carga_operacion"


CHECKS_DE_CARGA: dict[str, tuple[str, dict[str, Any]]] = {
    "importador_sin_archivo": ("ck_carga_origen", {"origen": "importador", "archivo": None}),
    "manual_sin_motivo": (
        "ck_carga_origen",
        {"origen": "manual", "archivo": None, "motivo": None},
    ),
    "origen_fuera_del_vocabulario": ("ck_carga_origen", {"origen": "planilla"}),
    "firma_con_63_hexadecimales": ("ck_carga_firma", {"firma_del_pedido": "v1:" + "a" * 63}),
    "firma_sin_version": ("ck_carga_firma", {"firma_del_pedido": "a" * 64}),
    "firma_con_mayusculas": ("ck_carga_firma", {"firma_del_pedido": "v1:" + "A" * 64}),
}


@pytest.mark.parametrize("caso", sorted(CHECKS_DE_CARGA))
def test_el_check_frena_una_carga_mal_formada(libro: Libro, caso: str) -> None:
    nombre, cambios = CHECKS_DE_CARGA[caso]
    with pytest.raises(errors.CheckViolation) as e, libro.conexion.transaction():
        _agregar_carga(libro, **cambios)
    assert e.value.sqlstate == "23514"
    assert e.value.diag.constraint_name == nombre, f"{caso}: rechazó {e.value.diag.constraint_name}"


def test_una_carga_manual_con_motivo_entra(libro: Libro) -> None:
    """Control de los CHECK de la carga: la manual lleva motivo y no archivo."""
    _agregar_carga(libro, origen="manual", archivo=None, motivo="Cuaderno de la administración")


CHECKS_DE_ORIGEN: dict[str, tuple[str, dict[str, Any]]] = {
    "fila_cero": ("ck_origen_fila", {"fila": 0}),
    "fila_negativa": ("ck_origen_fila", {"fila": -3}),
    "dos_referencias": (
        "ck_origen_referencia",
        {"movimiento_id": "INTERES", "sentido_del_movimiento": "debito"},
    ),
    "ninguna_referencia": ("ck_origen_referencia", {"obligacion_id": None}),
}


@pytest.mark.parametrize("caso", sorted(CHECKS_DE_ORIGEN))
def test_el_check_frena_un_origen_mal_formado(libro: Libro, caso: str) -> None:
    nombre, cambios = CHECKS_DE_ORIGEN[caso]
    cambios = {k: (libro.interes if v == "INTERES" else v) for k, v in cambios.items()}
    carga = _agregar_carga(libro)
    with pytest.raises(errors.CheckViolation) as e, libro.conexion.transaction():
        _agregar_origen(libro, carga["id"], **cambios)
    assert e.value.sqlstate == "23514"
    assert e.value.diag.constraint_name == nombre, f"{caso}: rechazó {e.value.diag.constraint_name}"


def test_una_fila_nula_entra_en_una_carga_manual(libro: Libro) -> None:
    """Control de `fila >= 1`: nula sólo en una carga manual (lo verifica la aplicación)."""
    carga = _agregar_carga(libro, origen="manual", archivo=None, motivo="Cuaderno")
    _agregar_origen(libro, carga["id"], fila=None)


@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE"])
@pytest.mark.parametrize("tabla", TABLAS)
def test_trigger_por_fila_sin_el_de_sentencia(
    base_del_edificio: BaseDeEdificio, tabla: str, operacion: str
) -> None:
    """Sin el trigger por fila, el de sentencia tapa el UPDATE: se lo apaga para ver sólo el
    de fila (el arranque tiene el privilegio; sólo el trigger lo frena)."""
    with arranque(base_del_edificio) as c, c.transaction(force_rollback=True):
        c.execute("SET LOCAL ROLE proptech_app")
        datos = sembrar_libro(c)
        carga = _carga(datos)
        insertar(c, CARGA, carga)
        insertar(c, ORIGEN, _origen(datos, carga["id"]))
        c.execute("RESET ROLE")
        c.execute(
            sql.SQL("ALTER TABLE {} DISABLE TRIGGER {}").format(
                sql.Identifier(tabla),
                sql.Identifier(f"trg_{tabla}_sin_update_delete_por_sentencia"),
            )
        )
        sentencia = (
            f"UPDATE {tabla} SET administracion_id = administracion_id"  # noqa: S608
            if operacion == "UPDATE"
            else f"DELETE FROM {tabla}"  # noqa: S608
        )
        with pytest.raises(errors.RaiseException) as e, c.transaction():
            c.execute(sentencia)
        assert e.value.sqlstate == "P0001"
        assert e.value.diag.message_primary == f"{tabla} no admite {operacion}"


@pytest.mark.parametrize("sentencia", ["TRUNCATE", "DELETE WHERE false", "UPDATE WHERE false"])
@pytest.mark.parametrize("tabla", TABLAS)
def test_trigger_por_sentencia_sin_filas(
    base_del_edificio: BaseDeEdificio, tabla: str, sentencia: str
) -> None:
    """Sin filas, el trigger por fila no se dispara: sólo el de sentencia (o el de TRUNCATE)
    frena al dueño."""
    consultas = {
        "TRUNCATE": f"TRUNCATE {tabla} CASCADE",
        "DELETE WHERE false": f"DELETE FROM {tabla} WHERE false",  # noqa: S608
        "UPDATE WHERE false": (
            f"UPDATE {tabla} SET administracion_id = administracion_id WHERE false"  # noqa: S608
        ),
    }
    with arranque(base_del_edificio) as c:
        with pytest.raises(errors.RaiseException) as e, c.transaction():
            c.execute(consultas[sentencia])
        assert e.value.sqlstate == "P0001"
        assert e.value.diag.message_primary is not None
        assert e.value.diag.message_primary.startswith(f"{tabla} no admite")


@pytest.mark.parametrize("tabla", TABLAS)
def test_el_dueno_es_el_arranque_y_la_app_no_es_dueña(
    base_del_edificio: BaseDeEdificio, tabla: str
) -> None:
    base = base_del_edificio
    with arranque(base) as c:
        assert c.execute(
            "SELECT tableowner FROM pg_tables WHERE schemaname='public' AND tablename=%s", (tabla,)
        ).fetchone() == (base.contenedor.username,)
        assert c.execute(
            "SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE oid=to_regprocedure(%s)",
            (f"fn_{tabla}_bloqueada()",),
        ).fetchone() == (base.contenedor.username,)
