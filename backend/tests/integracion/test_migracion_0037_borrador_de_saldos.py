"""Tarea 2.2 de `importacion-desde-excel`: la migración `0037_borrador_de_saldos` (design D5, D6,
D10).

L-082: el test prueba **su** migración (`0037` sobre la `0036`), nunca "la última". La bajada y la
subida, que no admiten filas, están en `test_migracion_0037_baja_y_sube.py` (su propia base).
`fila_de_saldo_importada` y `control_de_saldo` las cambia la app (RLS forzada, FK compuestas);
`aceptacion_de_diferencias` es de sólo agregar (patrón del libro, `0035`): tres triggers, el
arranque de dueño y la app sin `UPDATE`/`DELETE`. Una defensa por test, para que un mutante que
apague una sola caiga en la aserción que la nombra (matriz de la `0034`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import errors

from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

from ._edificios import BaseDeEdificio
from ._importacion import Mundo, sembrar
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion

_VERSIONES = Path(__file__).resolve().parents[2] / "migraciones" / "versions"
FILA, CONTROL, ACEPTACION = (
    "fila_de_saldo_importada",
    "control_de_saldo",
    "aceptacion_de_diferencias",
)
TABLAS = (FILA, CONTROL, ACEPTACION)
ACCION = "aceptar_diferencias_de_saldos"
_DIFERENCIAS = '[{"unidad": "1A", "borrador": "10.00", "control": "0.00", "diferencia": "10.00"}]'


@dataclass
class Datos:
    mundo: Mundo
    importacion: UUID
    unidad: UUID
    unidad_de_otro: UUID
    importacion_de_otro: UUID
    persona_de_b: UUID

    @property
    def admin(self) -> UUID:
        return self.mundo.admin

    @property
    def edificio(self) -> UUID:
        return self.mundo.torre

    @property
    def persona(self) -> UUID:
        return self.mundo.super_admin.persona_id


def _filas(base: BaseDeEdificio, consulta: str, *parametros: object) -> list[tuple[Any, ...]]:
    with base.conectar_app() as c:
        return [tuple(f) for f in c.execute(consulta, parametros).fetchall()]


def _tablas_existen(base: BaseDeEdificio) -> None:
    for tabla in TABLAS:
        assert _filas(base, "SELECT to_regclass(%s) IS NOT NULL", f"public.{tabla}") == [(True,)], (
            f"falta la tabla {tabla} (0037)"
        )


def _datos(base: BaseDeEdificio) -> Datos:
    """Un edificio con una unidad y su importación en borrador, y otro con lo mismo."""
    m = sembrar(base)
    with m.conectar() as c:
        ids = {}
        for nombre, edificio in (("torre", m.torre), ("otro", m.otro)):
            unidad = c.execute(
                "INSERT INTO unidad (administracion_id, complejo_id, identificador, tipo, piso, "
                "coeficiente, superficie_m2) VALUES (%s, %s, '1A', 'departamento', '1', "
                "'1.000000', '60.00') RETURNING id",
                (m.admin, edificio),
            ).fetchone()
            importacion = c.execute(
                "INSERT INTO importacion (administracion_id, complejo_id, archivo, huella, "
                "fecha_de_migracion, creada_por) VALUES (%s, %s, 'a.xlsx', %s, %s, %s) "
                "RETURNING id",
                (
                    m.admin,
                    edificio,
                    ("a" if nombre == "torre" else "b") * 64,
                    date(2026, 10, 15),
                    m.super_admin.persona_id,
                ),
            ).fetchone()
            assert unidad is not None and importacion is not None
            ids[nombre] = (unidad[0], importacion[0])
    persona_b = uuid4()
    with m.conectar(m.admin_b) as c:
        c.execute(
            "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'Persona B')",
            (persona_b, m.admin_b),
        )
    return Datos(m, ids["torre"][1], ids["torre"][0], ids["otro"][0], ids["otro"][1], persona_b)


def _fila(d: Datos, **cambios: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "administracion_id": d.admin,
        "complejo_id": d.edificio,
        "importacion_id": d.importacion,
        "unidad_id": d.unidad,
        "fila": 2,
        "tipo": "detalle",
        "periodo": date(2026, 9, 1),
        "vencimiento": date(2026, 9, 10),
        "concepto": "ordinaria",
        "importe": "85000.00",
        "interes_acumulado": "0.00",
    }
    return {**base, **cambios}


def _control(d: Datos, **cambios: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "administracion_id": d.admin,
        "complejo_id": d.edificio,
        "importacion_id": d.importacion,
        "unidad_id": d.unidad,
        "fila": 2,
        "saldo": "85000.00",
    }
    return {**base, **cambios}


def _aceptacion(d: Datos, **cambios: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "administracion_id": d.admin,
        "complejo_id": d.edificio,
        "importacion_id": d.importacion,
        "aceptada_por": d.persona,
        "aceptada_en": datetime(2026, 11, 12, 15, tzinfo=UTC),
        "diferencias": _DIFERENCIAS,
    }
    return {**base, **cambios}


def _insertar(c: psycopg.Connection, tabla: str, fila: dict[str, Any]) -> None:
    columnas = ", ".join(fila)
    marcas = ", ".join("%s" for _ in fila)
    c.execute(
        f"INSERT INTO {tabla} ({columnas}) VALUES ({marcas})",  # noqa: S608
        tuple(fila.values()),
    )


@pytest.fixture
def datos(base_del_edificio: BaseDeEdificio) -> Datos:
    return _datos(base_del_edificio)


# --- La migración y su esquema ---------------------------------------------------------------


def test_la_migracion_es_la_0037_sobre_la_0036() -> None:
    archivos = list(_VERSIONES.glob("0037_*.py"))
    assert len(archivos) == 1, "falta la migración 0037 (borrador de saldos)"
    texto = archivos[0].read_text()
    assert 'revision: str = "0037"' in texto
    assert 'down_revision: str | None = "0036"' in texto


COLUMNAS = {
    FILA: [
        ("administracion_id", "uuid", "NO"),
        ("complejo_id", "uuid", "NO"),
        ("concepto", "text", "YES"),
        ("fila", "integer", "NO"),
        ("id", "uuid", "NO"),
        ("importacion_id", "uuid", "NO"),
        ("importe", "numeric", "NO"),
        ("interes_acumulado", "numeric", "NO"),
        ("periodo", "date", "YES"),
        ("tipo", "text", "NO"),
        ("unidad_id", "uuid", "NO"),
        ("vencimiento", "date", "YES"),
    ],
    CONTROL: [
        ("administracion_id", "uuid", "NO"),
        ("complejo_id", "uuid", "NO"),
        ("fila", "integer", "NO"),
        ("id", "uuid", "NO"),
        ("importacion_id", "uuid", "NO"),
        ("saldo", "numeric", "NO"),
        ("unidad_id", "uuid", "NO"),
    ],
    ACEPTACION: [
        ("aceptada_en", "timestamp with time zone", "NO"),
        ("aceptada_por", "uuid", "NO"),
        ("administracion_id", "uuid", "NO"),
        ("complejo_id", "uuid", "NO"),
        ("diferencias", "jsonb", "NO"),
        ("id", "uuid", "NO"),
        ("importacion_id", "uuid", "NO"),
    ],
}


@pytest.mark.parametrize("tabla", TABLAS)
def test_columnas(base_del_edificio: BaseDeEdificio, tabla: str) -> None:
    _tablas_existen(base_del_edificio)
    columnas = _filas(
        base_del_edificio,
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s ORDER BY column_name",
        tabla,
    )
    assert columnas == COLUMNAS[tabla]


@pytest.mark.parametrize("tabla", [FILA, CONTROL])
def test_los_importes_son_numeric_14_2(base_del_edificio: BaseDeEdificio, tabla: str) -> None:
    _tablas_existen(base_del_edificio)
    columnas = {FILA: ("importe", "interes_acumulado"), CONTROL: ("saldo",)}[tabla]
    for columna in columnas:
        assert _filas(
            base_del_edificio,
            "SELECT numeric_precision, numeric_scale FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = %s",
            tabla,
            columna,
        ) == [(14, 2)], f"{tabla}.{columna} es NUMERIC(14,2)"


@pytest.mark.parametrize("tabla", TABLAS)
def test_rls_forzada_con_su_politica(base_del_edificio: BaseDeEdificio, tabla: str) -> None:
    _tablas_existen(base_del_edificio)
    assert _filas(
        base_del_edificio,
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = %s",
        tabla,
    ) == [(True, True)], f"{tabla}: RLS activada y forzada"
    assert _filas(
        base_del_edificio, "SELECT policyname FROM pg_policies WHERE tablename = %s", tabla
    ) == [(f"{tabla}_por_administracion",)]


@pytest.mark.parametrize("tabla", TABLAS)
def test_otra_administracion_no_ve_las_filas(datos: Datos, tabla: str) -> None:
    """Sin la política, la app de B vería las filas de A: ninguna otra defensa filtra la lectura."""
    _tablas_existen(datos.mundo.base)
    escribir = {FILA: _fila, CONTROL: _control, ACEPTACION: _aceptacion}[tabla]
    with datos.mundo.conectar() as c:
        _insertar(c, tabla, escribir(datos))
    with datos.mundo.conectar() as c:
        assert c.execute(f"SELECT count(*) FROM {tabla}").fetchone() == (1,)  # noqa: S608
    with datos.mundo.conectar(datos.mundo.admin_b) as c:
        assert c.execute(f"SELECT count(*) FROM {tabla}").fetchone() == (0,), (  # noqa: S608
            f"otra administración ve filas de {tabla}"
        )


def test_permisos_de_la_app(base_del_edificio: BaseDeEdificio) -> None:
    _tablas_existen(base_del_edificio)
    consulta = (
        "SELECT privilege_type FROM information_schema.role_table_grants "
        "WHERE table_name = %s AND grantee = 'proptech_app' ORDER BY 1"
    )
    for tabla in (FILA, CONTROL):
        assert _filas(base_del_edificio, consulta, tabla) == [
            ("DELETE",),
            ("INSERT",),
            ("SELECT",),
            ("UPDATE",),
        ], f"{tabla}: la app cambia el borrador"
    assert _filas(base_del_edificio, consulta, ACEPTACION) == [("INSERT",), ("SELECT",)]


@pytest.mark.parametrize("tabla", TABLAS)
def test_las_claves_foraneas_son_compuestas_con_la_administracion(
    base_del_edificio: BaseDeEdificio, tabla: str
) -> None:
    _tablas_existen(base_del_edificio)
    filas = _filas(
        base_del_edificio,
        "SELECT confrelid::regclass::text, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid = %s::regclass AND contype = 'f' ORDER BY 1",
        tabla,
    )
    esperadas = {
        FILA: ["complejo", "importacion", "unidad"],
        CONTROL: ["complejo", "importacion", "unidad"],
        ACEPTACION: ["complejo", "importacion", "persona"],
    }[tabla]
    assert [f[0] for f in filas] == esperadas
    assert all("administracion_id" in f[1] for f in filas)


def test_la_accion_esta_en_el_vocabulario_de_auditoria(base_del_edificio: BaseDeEdificio) -> None:
    assert _filas(
        base_del_edificio, "SELECT nombre FROM accion_de_auditoria WHERE nombre = %s", ACCION
    ) == [(ACCION,)]


# --- Sólo la aceptación es de sólo agregar ----------------------------------------------------


def test_solo_la_aceptacion_esta_declarada_de_solo_agregar() -> None:
    assert ACEPTACION in TABLAS_DE_SOLO_AGREGAR, f"{ACEPTACION} no está en TABLAS_DE_SOLO_AGREGAR"
    declarada = TABLAS_DE_SOLO_AGREGAR[ACEPTACION]
    assert declarada.mensaje == f"{ACEPTACION} no admite"
    assert declarada.triggers == frozenset(
        {
            f"trg_{ACEPTACION}_sin_update_delete",
            f"trg_{ACEPTACION}_sin_truncate",
            f"trg_{ACEPTACION}_sin_update_delete_por_sentencia",
        }
    )
    assert FILA not in TABLAS_DE_SOLO_AGREGAR and CONTROL not in TABLAS_DE_SOLO_AGREGAR


@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE", "TRUNCATE"])
def test_la_app_no_tiene_permiso_de_edicion_de_la_aceptacion(datos: Datos, operacion: str) -> None:
    """Sin el REVOKE de `roles despues` el trigger rechazaría con P0001 en vez de 42501."""
    _tablas_existen(datos.mundo.base)
    consultas = {
        "UPDATE": f"UPDATE {ACEPTACION} SET administracion_id = administracion_id",  # noqa: S608
        "DELETE": f"DELETE FROM {ACEPTACION}",  # noqa: S608
        "TRUNCATE": f"TRUNCATE {ACEPTACION} CASCADE",
    }
    with datos.mundo.conectar() as c:
        _insertar(c, ACEPTACION, _aceptacion(datos))
    with datos.mundo.conectar() as c, pytest.raises(psycopg.Error) as e:
        c.execute(consultas[operacion])
    assert e.value.sqlstate == "42501", f"{operacion}: {e.value.sqlstate}"


def test_el_dueno_de_la_aceptacion_es_el_arranque(base_del_edificio: BaseDeEdificio) -> None:
    _tablas_existen(base_del_edificio)
    with arranque(base_del_edificio) as c:
        assert c.execute(
            "SELECT tableowner FROM pg_tables WHERE schemaname='public' AND tablename=%s",
            (ACEPTACION,),
        ).fetchone() == (base_del_edificio.contenedor.username,)
        assert c.execute(
            "SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE oid=to_regprocedure(%s)",
            (f"fn_{ACEPTACION}_bloqueada()",),
        ).fetchone() == (base_del_edificio.contenedor.username,)
        for tabla in (FILA, CONTROL):
            assert c.execute(
                "SELECT tableowner FROM pg_tables WHERE schemaname='public' AND tablename=%s",
                (tabla,),
            ).fetchone() != (base_del_edificio.contenedor.username,), f"{tabla} es del migrador"


@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE"])
def test_trigger_por_fila_sin_el_de_sentencia(datos: Datos, operacion: str) -> None:
    """Se apaga el de sentencia para ver sólo el de fila: el arranque tiene el privilegio, sólo el
    trigger lo frena."""
    _tablas_existen(datos.mundo.base)
    with datos.mundo.conectar() as c:
        _insertar(c, ACEPTACION, _aceptacion(datos))
    with arranque(datos.mundo.base) as c:
        c.execute(
            f"ALTER TABLE {ACEPTACION} DISABLE TRIGGER "
            f"trg_{ACEPTACION}_sin_update_delete_por_sentencia"
        )
        try:
            sentencia = (
                f"UPDATE {ACEPTACION} SET administracion_id = administracion_id"  # noqa: S608
                if operacion == "UPDATE"
                else f"DELETE FROM {ACEPTACION}"  # noqa: S608
            )
            with pytest.raises(errors.RaiseException) as e, c.transaction():
                c.execute(sentencia)
            assert e.value.sqlstate == "P0001"
            assert e.value.diag.message_primary == f"{ACEPTACION} no admite {operacion}"
        finally:
            c.execute(
                f"ALTER TABLE {ACEPTACION} ENABLE TRIGGER "
                f"trg_{ACEPTACION}_sin_update_delete_por_sentencia"
            )


@pytest.mark.parametrize("sentencia", ["TRUNCATE", "DELETE WHERE false", "UPDATE WHERE false"])
def test_trigger_por_sentencia_sin_filas(base_del_edificio: BaseDeEdificio, sentencia: str) -> None:
    """Sin filas el trigger por fila no se dispara: sólo el de sentencia frena al dueño."""
    _tablas_existen(base_del_edificio)
    consultas = {
        "TRUNCATE": f"TRUNCATE {ACEPTACION} CASCADE",
        "DELETE WHERE false": f"DELETE FROM {ACEPTACION} WHERE false",  # noqa: S608
        "UPDATE WHERE false": (
            f"UPDATE {ACEPTACION} SET administracion_id = administracion_id WHERE false"  # noqa: S608
        ),
    }
    with arranque(base_del_edificio) as c:
        with pytest.raises(errors.RaiseException) as e, c.transaction():
            c.execute(consultas[sentencia])
        assert e.value.sqlstate == "P0001"
        assert (e.value.diag.message_primary or "").startswith(f"{ACEPTACION} no admite")


# --- Las claves foráneas fijan edificio y administración --------------------------------------


@pytest.mark.parametrize(
    ("tabla", "escribir"), [(FILA, _fila), (CONTROL, _control), (ACEPTACION, _aceptacion)]
)
def test_la_importacion_de_otro_edificio_se_rechaza(
    datos: Datos, tabla: str, escribir: Any
) -> None:
    """La FK compuesta a `importacion` incluye el edificio: la importación de `otro` no sirve."""
    _tablas_existen(datos.mundo.base)
    with datos.mundo.conectar() as c, pytest.raises(errors.ForeignKeyViolation):
        _insertar(c, tabla, escribir(datos, importacion_id=datos.importacion_de_otro))


@pytest.mark.parametrize("tabla", [FILA, CONTROL])
def test_la_unidad_de_otro_edificio_se_rechaza(datos: Datos, tabla: str) -> None:
    _tablas_existen(datos.mundo.base)
    escribir = {FILA: _fila, CONTROL: _control}[tabla]
    with datos.mundo.conectar() as c, pytest.raises(errors.ForeignKeyViolation):
        _insertar(c, tabla, escribir(datos, unidad_id=datos.unidad_de_otro))


@pytest.mark.parametrize(
    ("tabla", "escribir"), [(FILA, _fila), (CONTROL, _control), (ACEPTACION, _aceptacion)]
)
def test_el_edificio_de_otra_administracion_se_rechaza(
    datos: Datos, tabla: str, escribir: Any
) -> None:
    _tablas_existen(datos.mundo.base)
    with datos.mundo.conectar() as c, pytest.raises(errors.ForeignKeyViolation):
        _insertar(c, tabla, escribir(datos, complejo_id=datos.mundo.complejo_b))


def test_la_aceptacion_no_la_firma_una_persona_de_otra_administracion(datos: Datos) -> None:
    _tablas_existen(datos.mundo.base)
    with datos.mundo.conectar() as c, pytest.raises(errors.ForeignKeyViolation):
        _insertar(c, ACEPTACION, _aceptacion(datos, aceptada_por=datos.persona_de_b))


# --- Los CHECK y los únicos -------------------------------------------------------------------

CHECKS_DE_FILA: dict[str, dict[str, Any]] = {
    "tipo_fuera_del_vocabulario": {"tipo": "otro"},
    "concepto_fuera_del_vocabulario": {"concepto": "expensa"},
    "importe_negativo": {"importe": "-1.00"},
    "interes_negativo": {"interes_acumulado": "-1.00"},
    "fila_menor_que_2": {"fila": 1},
    "periodo_que_no_es_dia_1": {"periodo": date(2026, 9, 15)},
    "detalle_sin_periodo": {"periodo": None},
    "detalle_sin_vencimiento": {"vencimiento": None},
    "detalle_sin_concepto": {"concepto": None},
    "total_con_periodo": {"tipo": "total", "vencimiento": None, "concepto": None},
    "total_con_vencimiento": {"tipo": "total", "periodo": None, "concepto": None},
    "total_con_concepto": {"tipo": "total", "periodo": None, "vencimiento": None},
    "credito_con_periodo": {"tipo": "credito", "vencimiento": None, "concepto": None},
    "credito_con_interes": {
        "tipo": "credito",
        "periodo": None,
        "vencimiento": None,
        "concepto": None,
        "interes_acumulado": "5.00",
    },
}


@pytest.mark.parametrize("caso", sorted(CHECKS_DE_FILA))
def test_el_check_frena_una_fila_mal_formada(datos: Datos, caso: str) -> None:
    _tablas_existen(datos.mundo.base)
    with datos.mundo.conectar() as c, pytest.raises(errors.CheckViolation):
        _insertar(c, FILA, _fila(datos, **CHECKS_DE_FILA[caso]))


@pytest.mark.parametrize(
    "cambios",
    [
        {},
        {"tipo": "total", "periodo": None, "vencimiento": None, "concepto": None},
        {"tipo": "credito", "periodo": None, "vencimiento": None, "concepto": None},
        {"concepto": "fondo_de_reserva"},
        {"concepto": "extraordinaria", "interes_acumulado": "4000.00"},
    ],
    ids=["detalle", "total", "credito", "fondo", "extraordinaria"],
)
def test_las_filas_bien_formadas_entran(datos: Datos, cambios: dict[str, Any]) -> None:
    """Control de los CHECK de la fila: las tres formas del contrato entran."""
    _tablas_existen(datos.mundo.base)
    with datos.mundo.conectar() as c:
        _insertar(c, FILA, _fila(datos, **cambios))


def test_una_fila_del_excel_no_se_repite_en_la_importacion(datos: Datos) -> None:
    _tablas_existen(datos.mundo.base)
    with datos.mundo.conectar() as c:
        _insertar(c, FILA, _fila(datos))
    with datos.mundo.conectar() as c, pytest.raises(errors.UniqueViolation):
        _insertar(c, FILA, _fila(datos))


def test_el_control_no_repite_fila_ni_unidad(datos: Datos) -> None:
    _tablas_existen(datos.mundo.base)
    with datos.mundo.conectar() as c:
        _insertar(c, CONTROL, _control(datos))
    with datos.mundo.conectar() as c, pytest.raises(errors.UniqueViolation):
        _insertar(c, CONTROL, _control(datos, unidad_id=uuid4()))  # misma fila, otra unidad
    with datos.mundo.conectar() as c, pytest.raises(errors.UniqueViolation):
        _insertar(c, CONTROL, _control(datos, fila=3))  # misma unidad, otra fila


def test_el_control_con_saldo_negativo_y_la_fila_menor_que_2(datos: Datos) -> None:
    _tablas_existen(datos.mundo.base)
    with datos.mundo.conectar() as c:
        _insertar(c, CONTROL, _control(datos, saldo="-3000.00"))
    with datos.mundo.conectar() as c, pytest.raises(errors.CheckViolation):
        _insertar(c, CONTROL, _control(datos, fila=1))


def test_hay_una_sola_aceptacion_por_importacion(datos: Datos) -> None:
    _tablas_existen(datos.mundo.base)
    with datos.mundo.conectar() as c:
        _insertar(c, ACEPTACION, _aceptacion(datos))
    with datos.mundo.conectar() as c, pytest.raises(errors.UniqueViolation):
        _insertar(c, ACEPTACION, _aceptacion(datos))


@pytest.mark.parametrize("diferencias", ["[]", "{}", '"texto"'])
def test_la_aceptacion_guarda_una_lista_no_vacia_de_diferencias(
    datos: Datos, diferencias: str
) -> None:
    _tablas_existen(datos.mundo.base)
    with datos.mundo.conectar() as c, pytest.raises(errors.CheckViolation):
        _insertar(c, ACEPTACION, _aceptacion(datos, diferencias=diferencias))
