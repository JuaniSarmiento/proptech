"""4c, tarea 2.1 (H-004): `tramo_de_interes` (design D4, D10) lleva el patrón del libro.

Una defensa por test: cada aserción nombra la tabla y mata el mutante que apaga esa defensa y deja
las demás (matriz de `openspec/changes/intereses-saldo-inicial-y-moroso/tasks.md`, 2.1). Las filas
de interés se insertan a mano, como en `test_libro_esquema`: este archivo prueba la tabla, no el
cálculo.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from psycopg import errors, sql

from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

from ._edificios import BaseDeEdificio, fijar_tenant
from ._libro import Libro, insertar, sembrar_libro
from .test_libro_esquema import libro as _fixture_libro  # noqa: F401
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion

TABLA = "tramo_de_interes"
PROPORCIONAL, MES_ENTERO = "proporcional_por_dia", "mes_entero"


def _fila(libro: Libro, **cambios: Any) -> dict[str, Any]:
    fila: dict[str, Any] = {
        "id": uuid4(),
        "administracion_id": libro.admin,
        "complejo_id": libro.edificios.complejo_a,
        "cuenta_id": libro.cuenta,
        "movimiento_id": libro.interes,
        "sentido_del_movimiento": "debito",
        "desde": date(2026, 10, 11),
        "hasta": date(2026, 10, 26),
        "dias": 16,
        "base": "100000.00",
        "tasa_mensual": "3.00",
        "forma_de_calculo": PROPORCIONAL,
        "dias_de_gracia": 0,
        "configuracion_id": uuid4(),
        "registrado_en": datetime(2026, 10, 27, tzinfo=UTC),
    }
    return {**fila, **cambios}


def _agregar(libro: Libro, **cambios: Any) -> dict[str, Any]:
    fila = _fila(libro, **cambios)
    insertar(libro.conexion, TABLA, fila)
    return fila


def test_tramo_esta_declarado_con_sus_tres_triggers() -> None:
    assert TABLA in TABLAS_DE_SOLO_AGREGAR, f"{TABLA} no está en TABLAS_DE_SOLO_AGREGAR"
    declarada = TABLAS_DE_SOLO_AGREGAR[TABLA]
    assert declarada.mensaje == f"{TABLA} no admite"
    assert declarada.triggers == frozenset(
        {
            f"trg_{TABLA}_sin_update_delete",
            f"trg_{TABLA}_sin_truncate",
            f"trg_{TABLA}_sin_update_delete_por_sentencia",
        }
    )


@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE", "TRUNCATE"])
def test_la_app_no_tiene_permiso_de_edicion(libro: Libro, operacion: str) -> None:
    """Sin el REVOKE de `roles despues` el trigger rechaza con P0001 en vez de 42501: la
    aserción mira el SQLSTATE."""
    _agregar(libro)
    consultas = {
        "UPDATE": "UPDATE tramo_de_interes SET dias = dias",
        "DELETE": "DELETE FROM tramo_de_interes",
        "TRUNCATE": "TRUNCATE tramo_de_interes",
    }
    with pytest.raises(psycopg.Error) as e, libro.conexion.transaction():
        libro.conexion.execute(consultas[operacion])
    assert e.value.sqlstate == "42501", f"{TABLA} {operacion}: {e.value.sqlstate}"


def test_otra_administracion_no_ve_el_detalle(libro: Libro) -> None:
    """Sin `ENABLE` ni política, la app de B vería el tramo de A: ninguna otra defensa filtra
    la lectura."""
    c = libro.conexion
    assert c.execute(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
    ).fetchone() == (False, False)
    fila = _agregar(libro)
    assert c.execute(
        sql.SQL("SELECT count(*) FROM {} WHERE id = %s").format(sql.Identifier(TABLA)),
        (fila["id"],),
    ).fetchone() == (1,)
    fijar_tenant(c, libro.edificios.administracion_b)
    assert c.execute(
        sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(TABLA))
    ).fetchone() == (0,), f"otra administración ve filas de {TABLA}"


def test_un_tramo_no_se_cuelga_de_otra_cuenta(libro: Libro) -> None:
    """Sin `cuenta_id` en la FK a `movimiento`, ningún CHECK mira la cuenta del movimiento."""
    with pytest.raises(errors.ForeignKeyViolation), libro.conexion.transaction():
        _agregar(libro, cuenta_id=libro.cuenta_personal)


def test_un_tramo_no_se_cuelga_de_un_movimiento_ajeno_en_otro_edificio(libro: Libro) -> None:
    """La FK al `complejo` y la FK compuesta a `movimiento` fijan el edificio."""
    with pytest.raises(errors.ForeignKeyViolation), libro.conexion.transaction():
        _agregar(libro, complejo_id=libro.edificios.otro_complejo_a)


CHECKS: dict[str, tuple[str, dict[str, Any], Any]] = {
    "dias_incoherentes": ("ck_tramo_dias", {"dias": 15}, None),
    "hasta_antes_de_desde": (
        "ck_tramo_orden",
        {"desde": date(2026, 10, 26), "hasta": date(2026, 10, 11), "dias": -14},
        None,
    ),
    "base_cero": ("ck_tramo_base", {"base": "0.00"}, None),
    "base_negativa": ("ck_tramo_base", {"base": "-1.00"}, None),
    "forma_fuera_del_vocabulario": ("ck_tramo_forma", {"forma_de_calculo": "anual"}, None),
    "sentido_credito": ("ck_tramo_sentido", {"sentido_del_movimiento": "credito"}, "pago"),
    # PR-14: cada condición del mes entero tiene su negativo discriminante, con `dias` coherente.
    "mes_entero_de_dos_meses": (
        "ck_tramo_mes_entero",
        {
            "forma_de_calculo": MES_ENTERO,
            "desde": date(2026, 9, 30),
            "hasta": date(2026, 10, 31),
            "dias": 32,
        },
        None,
    ),
    "mes_entero_sin_fin_de_mes": (
        "ck_tramo_mes_entero",
        {
            "forma_de_calculo": MES_ENTERO,
            "desde": date(2026, 10, 1),
            "hasta": date(2026, 10, 30),
            "dias": 30,
        },
        None,
    ),
}


@pytest.mark.parametrize("caso", sorted(CHECKS))
def test_el_check_frena_un_tramo_mal_formado(libro: Libro, caso: str) -> None:
    nombre, cambios, movimiento = CHECKS[caso]
    if movimiento == "pago":
        cambios = {**cambios, "movimiento_id": libro.pago}
    with pytest.raises(errors.CheckViolation) as e, libro.conexion.transaction():
        _agregar(libro, **cambios)
    assert e.value.sqlstate == "23514"
    assert e.value.diag.constraint_name == nombre, f"{caso}: rechazó {e.value.diag.constraint_name}"


@pytest.mark.parametrize(
    "desde,hasta,dias",
    [(date(2026, 10, 1), date(2026, 10, 31), 31), (date(2026, 11, 16), date(2026, 11, 30), 15)],
)
def test_un_mes_entero_bien_formado_entra(
    libro: Libro, desde: date, hasta: date, dias: int
) -> None:
    """Control de los CHECK de mes entero: el mes completo y la fracción hasta fin de mes."""
    _agregar(libro, forma_de_calculo=MES_ENTERO, desde=desde, hasta=hasta, dias=dias)


@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE"])
def test_trigger_por_fila_sin_el_de_sentencia(
    base_del_edificio: BaseDeEdificio, operacion: str
) -> None:
    """Sin el trigger por fila, el de sentencia tapa el UPDATE: se lo apaga para ver sólo el
    de fila (el arranque tiene el privilegio; sólo el trigger lo frena)."""
    with arranque(base_del_edificio) as c, c.transaction(force_rollback=True):
        c.execute("SET LOCAL ROLE proptech_app")
        datos = sembrar_libro(c)
        insertar(c, TABLA, _fila(datos))
        c.execute("RESET ROLE")
        c.execute(
            sql.SQL("ALTER TABLE {} DISABLE TRIGGER {}").format(
                sql.Identifier(TABLA),
                sql.Identifier(f"trg_{TABLA}_sin_update_delete_por_sentencia"),
            )
        )
        sentencia = (
            "UPDATE tramo_de_interes SET dias = dias"
            if operacion == "UPDATE"
            else "DELETE FROM tramo_de_interes"
        )
        with pytest.raises(errors.RaiseException) as e, c.transaction():
            c.execute(sentencia)
        assert e.value.sqlstate == "P0001"
        assert e.value.diag.message_primary == f"{TABLA} no admite {operacion}"


@pytest.mark.parametrize("sentencia", ["TRUNCATE", "DELETE WHERE false", "UPDATE WHERE false"])
def test_trigger_por_sentencia_sin_filas(base_del_edificio: BaseDeEdificio, sentencia: str) -> None:
    """Sin filas, el trigger por fila no se dispara: sólo el de sentencia (o el de TRUNCATE)
    frena al dueño."""
    consultas = {
        "TRUNCATE": "TRUNCATE tramo_de_interes",
        "DELETE WHERE false": "DELETE FROM tramo_de_interes WHERE false",
        "UPDATE WHERE false": "UPDATE tramo_de_interes SET dias = dias WHERE false",
    }
    with arranque(base_del_edificio) as c:
        with pytest.raises(errors.RaiseException) as e, c.transaction():
            c.execute(consultas[sentencia])
        assert e.value.sqlstate == "P0001"
        assert e.value.diag.message_primary is not None
        assert e.value.diag.message_primary.startswith(f"{TABLA} no admite")


def test_el_dueno_es_el_arranque_y_la_app_no_es_dueña(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    with arranque(base) as c:
        assert c.execute(
            "SELECT tableowner FROM pg_tables WHERE schemaname='public' AND tablename=%s", (TABLA,)
        ).fetchone() == (base.contenedor.username,)
        assert c.execute(
            "SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE oid=to_regprocedure(%s)",
            (f"fn_{TABLA}_bloqueada()",),
        ).fetchone() == (base.contenedor.username,)


def test_sembrar_con_configuracion_suma_una_version_por_edificio(
    base_del_edificio: BaseDeEdificio,
) -> None:
    """Tarea 2.2: la semilla opcional deja los tres edificios con su versión; la de por defecto,
    ninguna (la aceptación de H-004 la crea con `configurar`)."""
    from ._cuenta_corriente import sembrar

    sin = sembrar(base_del_edificio)
    con = sembrar(base_del_edificio, con_configuracion=True)
    with base_del_edificio.conectar_app() as c:
        c.autocommit = False
        for mundo, esperadas in ((sin, 0), (con, 1)):
            for admin, edificios in (
                (mundo.admin, (mundo.complejo, mundo.otro_complejo)),
                (mundo.admin_b, (mundo.complejo_b,)),
            ):
                fijar_tenant(c, admin)
                for edificio in edificios:
                    assert c.execute(
                        "SELECT count(*), min(tasa_mensual), min(umbral_saldo_chico), "
                        "min(dias_de_gracia), min(forma_de_calculo), min(vigente_desde) "
                        "FROM configuracion_versionada WHERE complejo_id = %s",
                        (edificio,),
                    ).fetchone() == (
                        (esperadas, None, None, None, None, None)
                        if not esperadas
                        else (
                            1,
                            Decimal("0.00"),
                            Decimal("500.00"),
                            0,
                            PROPORCIONAL,
                            date(2026, 1, 1),
                        )
                    )
                c.rollback()
