"""D1: restricciones reales, con app y tenant después del deploy completo."""

from datetime import date
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from psycopg import errors, sql

from ._edificios import Edificios, fijar_tenant
from ._libro import LIBRO, Libro, insertar

pytestmark = pytest.mark.integracion


@pytest.fixture(name="libro")
def libro(app_edificio: psycopg.Connection, edificios: Edificios) -> Libro:
    datos = Libro(app_edificio, edificios)
    datos.sembrar()
    return datos


# Nombre de la garantía, columna/valor, SQLSTATE preciso. Cada fila prueba INSERT real.
CASOS_CHECK = [
    ("cuenta", "ck_cuenta_duenio", {"unidad_id": None, "persona_id": None}),
    ("cuenta", "ck_cuenta_duenio", {"unidad_id": "$unidad", "persona_id": "$libre"}),
    ("emision", "ck_emision_periodo", {"periodo": date(2026, 10, 15)}),
    ("emision", "ck_emision_intento", {"intento": 0}),
    ("evento_de_emision", "ck_evento_tipo", {"tipo": "otra"}),
    ("evento_de_emision", "ck_evento_motivo", {"motivo": "   "}),
    ("evento_de_emision", "ck_evento_motivo", {"motivo": "x" * 501}),
    ("obligacion", "ck_obligacion_origen", {"operacion_id": None}),
    ("obligacion", "ck_obligacion_origen", {"emision_id": "$emision"}),
    ("obligacion", "ck_obligacion_periodo", {"periodo": date(2026, 10, 15)}),
    ("obligacion", "ck_obligacion_importes", {"ordinaria": "-1.00"}),
    ("obligacion", "ck_obligacion_importes", {"fondo_de_reserva": "-1.00"}),
    ("obligacion", "ck_obligacion_importes", {"extraordinaria": "-1.00"}),
    (
        "obligacion",
        "ck_obligacion_importes",
        {"ordinaria": "0", "fondo_de_reserva": "0", "extraordinaria": "0"},
    ),
    ("movimiento", "ck_mov_importe", {"importe": "0"}),
    ("movimiento", "ck_mov_importe", {"importe": "-1"}),
    ("movimiento", "ck_mov_componente", {"componente": "otro"}),
    (
        "movimiento",
        "ck_mov_interes",
        {
            "tipo": "interes",
            "sentido": "debito",
            "obligacion_id": "$obligacion",
            "componente": "ordinaria",
            "corte": date(2026, 11, 1),
        },
    ),
    (
        "movimiento",
        "ck_mov_interes",
        {
            "tipo": "interes",
            "sentido": "debito",
            "obligacion_id": "$obligacion",
            "componente": "interes",
        },
    ),
    ("movimiento", "ck_mov_destino_interes", {"tipo": "condonacion"}),
    (
        "movimiento",
        "ck_mov_destino_interes",
        {"tipo": "ajuste_de_interes", "obligacion_id": "$obligacion", "componente": "ordinaria"},
    ),
    ("movimiento", "ck_mov_bonificacion", {"tipo": "bonificacion"}),
    (
        "movimiento",
        "ck_mov_bonificacion",
        {"tipo": "bonificacion", "obligacion_id": "$obligacion", "componente": "interes"},
    ),
    ("movimiento", "ck_mov_debito_destino", {"tipo": "reversion_de_pago", "sentido": "debito"}),
    ("movimiento", "ck_mov_operacion", {"operacion_id": None}),
    (
        "movimiento",
        "ck_mov_motivo",
        {"tipo": "correccion", "obligacion_id": "$obligacion", "motivo": " "},
    ),
    (
        "movimiento",
        "ck_mov_motivo",
        {"tipo": "correccion", "obligacion_id": "$obligacion", "motivo": None},
    ),
    (
        "movimiento",
        "ck_mov_motivo",
        {"tipo": "correccion", "obligacion_id": "$obligacion", "motivo": "x" * 501},
    ),
    (
        "movimiento",
        "ck_mov_correccion_debito",
        {
            "tipo": "correccion",
            "sentido": "debito",
            "obligacion_id": "$obligacion",
            "componente": "ordinaria",
            "motivo": "Error",
        },
    ),
    ("movimiento", "ck_mov_correccion_credito", {"tipo": "correccion", "motivo": "Error"}),
    ("movimiento", "ck_mov_corrige_tipo", {"corrige_a": "$pago", "tipo_corregido": "pago"}),
    (
        "movimiento",
        "ck_mov_corrige_par",
        {
            "tipo": "correccion",
            "corrige_a": "$interes",
            "tipo_corregido": None,
            "importe": "999",
            "motivo": "Error",
        },
    ),
    (
        "movimiento",
        "ck_mov_corrige_par",
        {
            "tipo": "correccion",
            "obligacion_id": "$obligacion",
            "tipo_corregido": "pago",
            "motivo": "Error",
        },
    ),
    ("imputacion", "ck_imputacion_importe", {"importe": "0"}),
    ("imputacion", "ck_imputacion_importe", {"importe": "-1"}),
    ("imputacion", "ck_imputacion_componente", {"componente": "otro"}),
    (
        "imputacion",
        "ck_imputacion_sentido",
        {"movimiento_id": "$interes", "sentido_del_movimiento": "debito"},
    ),
]


def resolver(libro: Libro, datos: dict[str, Any]) -> dict[str, Any]:
    ids = {
        "$unidad": libro.edificios.unidad_a,
        "$libre": libro.persona_libre,
        "$emision": libro.emision,
        "$obligacion": libro.obligacion,
        "$pago": libro.pago,
        "$interes": libro.interes,
        "$cuenta_ajena": libro.cuenta_ajena,
        "$cuenta_otra": libro.cuenta_personal,
        "$otro_edificio": libro.edificios.otro_complejo_a,
    }
    return {k: ids[v] if isinstance(v, str) and v in ids else v for k, v in datos.items()}


@pytest.mark.parametrize(
    "tabla,restriccion,cambios",
    CASOS_CHECK,
    ids=[f"{t}-{r}-{i}" for i, (t, r, _) in enumerate(CASOS_CHECK)],
)
def test_check(libro: Libro, tabla: str, restriccion: str, cambios: dict[str, Any]) -> None:
    with pytest.raises(errors.CheckViolation) as e, libro.conexion.transaction():
        libro.agregar(tabla, **resolver(libro, cambios))
    assert e.value.sqlstate == "23514"
    assert e.value.diag.constraint_name == restriccion


CASOS_FK = [
    ("cuenta", "fk_cuenta_admin", {"administracion_id": "$inexistente"}),
    ("cuenta", "fk_cuenta_complejo", {"complejo_id": "$inexistente"}),
    ("cuenta", "fk_cuenta_unidad", {"unidad_id": "$inexistente", "persona_id": None}),
    ("cuenta", "fk_cuenta_persona", {"persona_id": "$inexistente"}),
    ("emision", "fk_emision_complejo", {"complejo_id": "$inexistente"}),
    ("emision", "fk_emision_persona", {"registrada_por": "$inexistente", "intento": 2}),
    ("evento_de_emision", "fk_evento_emision", {"emision_id": "$inexistente"}),
    ("evento_de_emision", "fk_evento_persona", {"persona_id": "$inexistente"}),
    ("obligacion", "fk_obligacion_cuenta", {"cuenta_id": "$cuenta_ajena"}),
    (
        "obligacion",
        "fk_obligacion_emision",
        {
            "emision_id": "$emision",
            "operacion_id": None,
            "periodo": date(2026, 11, 1),
            "cuenta_id": "$cuenta_otra",
        },
    ),
    ("movimiento", "fk_mov_tipo_sentido", {"tipo": "no_declarado"}),
    (
        "movimiento",
        "fk_mov_tipo_sentido",
        {
            "tipo": "pago",
            "sentido": "debito",
            "obligacion_id": "$obligacion",
            "componente": "ordinaria",
        },
    ),
    ("movimiento", "fk_mov_cuenta", {"cuenta_id": "$inexistente"}),
    ("movimiento", "fk_mov_cuenta", {"complejo_id": "$otro_edificio"}),
    (
        "movimiento",
        "fk_mov_obligacion",
        {"cuenta_id": "$cuenta_otra", "obligacion_id": "$obligacion"},
    ),
    ("movimiento", "fk_mov_emision", {"emision_id": "$inexistente"}),
    ("movimiento", "fk_mov_persona", {"registrado_por": "$inexistente"}),
    (
        "movimiento",
        "fk_mov_corrige",
        {
            "tipo": "correccion",
            "sentido": "debito",
            "corrige_a": "$pago",
            "tipo_corregido": "pago",
            "importe": "999",
            "motivo": "Error",
        },
    ),
    (
        "movimiento",
        "fk_mov_corrige",
        {
            "tipo": "correccion",
            "sentido": "debito",
            "corrige_a": "$pago",
            "tipo_corregido": "pago",
            "cuenta_id": "$cuenta_otra",
            "motivo": "Error",
        },
    ),
    ("movimiento", "fk_mov_enlazado", {"enlazado_a": "$inexistente"}),
    ("imputacion", "fk_imputacion_movimiento", {"movimiento_id": "$interes"}),
    ("imputacion", "fk_imputacion_obligacion", {"obligacion_id": "$inexistente"}),
]


@pytest.mark.parametrize(
    "tabla,restriccion,cambios",
    CASOS_FK,
    ids=[f"{t}-{r}-{i}" for i, (t, r, _) in enumerate(CASOS_FK)],
)
def test_fk(libro: Libro, tabla: str, restriccion: str, cambios: dict[str, Any]) -> None:
    cambios = {k: uuid4() if v == "$inexistente" else v for k, v in cambios.items()}
    # El tenant de una cuenta sin administración existente pasa RLS, para llegar a la FK.
    if tabla == "cuenta" and "administracion_id" in cambios:
        fijar_tenant(libro.conexion, cambios["administracion_id"])
    with pytest.raises(errors.ForeignKeyViolation) as e, libro.conexion.transaction():
        libro.agregar(tabla, **resolver(libro, cambios))
    assert e.value.sqlstate == "23503"
    assert e.value.diag.constraint_name == restriccion


@pytest.mark.parametrize(
    "tabla,columna",
    [
        ("evento_de_emision", "motivo"),
        ("imputacion", "sentido_del_movimiento"),
        ("obligacion", "vencimiento"),
        ("movimiento", "registrado_por"),
        ("movimiento", "request_id"),
    ],
)
def test_not_null(libro: Libro, tabla: str, columna: str) -> None:
    with pytest.raises(errors.NotNullViolation) as e, libro.conexion.transaction():
        libro.agregar(tabla, **{columna: None})
    assert e.value.sqlstate == "23502"
    assert e.value.diag.column_name == columna


@pytest.mark.parametrize(
    "tabla,columna",
    [
        ("cuenta", "unidad_id"),
        ("emision", "intento"),
        ("evento_de_emision", "tipo"),
        ("obligacion", "emision_id"),
        ("obligacion", "operacion_id"),
        ("movimiento", "operacion_id"),
        ("movimiento", "corrige_a"),
        ("movimiento", "corte"),
    ],
)
def test_unicos(libro: Libro, tabla: str, columna: str) -> None:
    cambios: dict[str, Any] = {}
    if tabla == "cuenta":
        cambios = {"unidad_id": libro.edificios.unidad_a, "persona_id": None}
    elif tabla == "emision":
        pass
    elif tabla == "evento_de_emision":
        libro.agregar(tabla)
    elif tabla == "obligacion":
        if columna == "emision_id":
            cambios = {"emision_id": libro.emision, "operacion_id": None}
        else:
            cambios = {"operacion_id": uuid4()}
            libro.agregar(tabla, **cambios)
    elif columna == "operacion_id":
        cambios = {"operacion_id": uuid4()}
        libro.agregar(tabla, **cambios)
    elif columna == "corrige_a":
        cambios = {
            "tipo": "correccion",
            "sentido": "debito",
            "corrige_a": libro.pago,
            "tipo_corregido": "pago",
            "motivo": "Error",
        }
        libro.agregar(tabla, **cambios)
    else:
        cambios = {
            "tipo": "interes",
            "sentido": "debito",
            "obligacion_id": libro.obligacion,
            "componente": "interes",
            "corte": date(2026, 10, 26),
            "operacion_id": None,
        }
    with pytest.raises(errors.UniqueViolation) as e, libro.conexion.transaction():
        libro.agregar(tabla, **cambios)
    assert e.value.sqlstate == "23505"


@pytest.mark.parametrize(
    "tipo,sentido",
    [
        ("interes", "debito"),
        ("pago", "credito"),
        ("correccion", "debito"),
        ("correccion", "credito"),
        ("condonacion", "credito"),
        ("ajuste_de_interes", "credito"),
        ("bonificacion", "credito"),
        ("baja_de_deuda", "credito"),
        ("saldo_inicial", "credito"),
        ("reversion_de_pago", "debito"),
        ("reimputacion", "debito"),
        ("reimputacion", "credito"),
        ("traslado", "debito"),
        ("traslado", "credito"),
    ],
)
def test_tipos_anticipados(libro: Libro, tipo: str, sentido: str) -> None:
    campos: dict[str, Any] = {
        "tipo": tipo,
        "sentido": sentido,
        "fecha_valor": date(2026, 12, 31),
        "obligacion_id": libro.obligacion,
        "componente": "interes"
        if tipo in {"interes", "condonacion", "ajuste_de_interes"}
        else "ordinaria",
    }
    if tipo == "interes":
        campos["corte"] = date(2026, 11, 1)
    if tipo == "correccion":
        campos["motivo"] = "Prueba"
        if sentido == "debito":
            campos.update(corrige_a=libro.pago, tipo_corregido="pago")
    if tipo == "ajuste_de_interes":
        campos["enlazado_a"] = libro.interes
    f = None
    try:
        with libro.conexion.transaction():
            f = libro.agregar("movimiento", **campos)
    except errors.CheckViolation:
        pass
    assert f is not None, f"el esquema rechaza un {tipo}/{sentido} anticipado válido"
    assert libro.conexion.execute(
        "SELECT tipo,sentido FROM movimiento WHERE id=%s", (f["id"],)
    ).fetchone() == (tipo, sentido)


def test_corregir_credito_de_correccion_una_vez(libro: Libro) -> None:
    c = libro.agregar(
        "movimiento", tipo="correccion", obligacion_id=libro.obligacion, motivo="Error"
    )
    campos = {
        "tipo": "correccion",
        "sentido": "debito",
        "corrige_a": c["id"],
        "tipo_corregido": "correccion",
        "motivo": "Deshacer",
    }
    libro.agregar("movimiento", **campos)
    with pytest.raises(errors.UniqueViolation) as e, libro.conexion.transaction():
        libro.agregar("movimiento", **campos)
    assert e.value.diag.constraint_name == "uq_mov_corrige_a"


def test_secuencia_decide_empate_de_registro(libro: Libro) -> None:
    a = libro.agregar("imputacion")
    b = libro.agregar("imputacion", corrida_id=a["corrida_id"])
    filas = libro.conexion.execute(
        "SELECT id,orden,registrada_en FROM imputacion ORDER BY orden"
    ).fetchall()
    assert [f[0] for f in filas] == [a["id"], b["id"]]
    assert filas[0][1] < filas[1][1] and filas[0][2] == filas[1][2]


def test_sin_saldos(libro: Libro) -> None:
    columnas = libro.conexion.execute(
        (
            "SELECT table_name,column_name FROM information_schema.columns WHE"
            "RE table_schema='public' AND table_name=ANY(%s)"
        ),
        (list(LIBRO),),
    ).fetchall()
    assert len({t for t, _ in columnas}) == 6
    assert not [(t, c) for t, c in columnas if any(p in c for p in ("saldo", "residual", "pagad"))]


@pytest.mark.parametrize("tabla", LIBRO)
def test_rls(libro: Libro, tabla: str) -> None:
    if tabla == "evento_de_emision":
        libro.agregar(tabla)
    if tabla == "imputacion":
        libro.agregar(tabla)
    fijar_tenant(libro.conexion, libro.edificios.administracion_b)
    filas = libro.conexion.execute(
        sql.SQL("SELECT administracion_id FROM {}").format(sql.Identifier(tabla))
    ).fetchall()
    assert all(f[0] == libro.edificios.administracion_b for f in filas)
    if tabla != "cuenta":
        assert filas == []


def test_cuenta_personal_unica_por_edificio(libro: Libro) -> None:
    with pytest.raises(errors.UniqueViolation) as e, libro.conexion.transaction():
        libro.agregar("cuenta", persona_id=libro.persona)
    assert e.value.diag.constraint_name == "uq_cuenta_persona"
    otro = libro.agregar(
        "cuenta", complejo_id=libro.edificios.otro_complejo_a, persona_id=libro.persona
    )
    assert libro.conexion.execute(
        "SELECT complejo_id FROM cuenta WHERE id=%s", (otro["id"],)
    ).fetchone() == (libro.edificios.otro_complejo_a,)


def test_candado_fk_no_cruza_administracion(libro: Libro) -> None:
    with pytest.raises(errors.ForeignKeyViolation) as e, libro.conexion.transaction():
        insertar(
            libro.conexion,
            "candado_de_cuenta",
            {"cuenta_id": libro.cuenta_ajena, "administracion_id": libro.admin},
        )
    assert e.value.diag.constraint_name == "fk_candado_cuenta"


def test_enlace_entre_cuentas_y_rechazo_de_otro_tenant(libro: Libro) -> None:
    a = libro.agregar("movimiento", cuenta_id=libro.cuenta_personal)
    b = libro.agregar("movimiento", tipo="reimputacion", enlazado_a=a["id"])
    assert libro.conexion.execute(
        "SELECT enlazado_a FROM movimiento WHERE id=%s", (b["id"],)
    ).fetchone() == (a["id"],)
    fijar_tenant(libro.conexion, libro.edificios.administracion_b)
    ajeno = uuid4()
    insertar(
        libro.conexion,
        "persona",
        {"id": ajeno, "administracion_id": libro.edificios.administracion_b, "nombre": "Ficticio"},
    )
    pago = libro.agregar(
        "movimiento",
        administracion_id=libro.edificios.administracion_b,
        complejo_id=libro.edificios.complejo_b,
        cuenta_id=libro.cuenta_ajena,
        registrado_por=ajeno,
    )
    fijar_tenant(libro.conexion, libro.admin)
    with pytest.raises(errors.ForeignKeyViolation) as e, libro.conexion.transaction():
        libro.agregar("movimiento", enlazado_a=pago["id"])
    assert e.value.diag.constraint_name == "fk_mov_enlazado"


def test_vocabulario_ampliable_sin_alter(base_del_edificio: Any) -> None:
    with base_del_edificio.conectar_migrador() as c, c.transaction(force_rollback=True):
        c.execute("INSERT INTO tipo_de_movimiento VALUES ('futuro','credito')")
        assert c.execute(
            "SELECT sentido FROM tipo_de_movimiento WHERE tipo='futuro'"
        ).fetchone() == ("credito",)
        with pytest.raises(errors.CheckViolation) as e, c.transaction():
            c.execute("INSERT INTO tipo_de_movimiento VALUES ('','credito')")
        assert e.value.diag.constraint_name == "ck_tipo_no_vacio"
        with pytest.raises(errors.CheckViolation) as e, c.transaction():
            c.execute("INSERT INTO tipo_de_movimiento VALUES ('futuro','otro')")
        assert e.value.diag.constraint_name == "ck_tipo_sentido"


def test_imputacion_obligacion_de_otra_cuenta(libro: Libro) -> None:
    with pytest.raises(errors.ForeignKeyViolation) as e, libro.conexion.transaction():
        libro.agregar(
            "imputacion", cuenta_id=libro.cuenta_personal, movimiento_id=libro.pago_personal
        )
    assert e.value.diag.constraint_name == "fk_imputacion_obligacion"


def test_movimiento_inexistente_no_pasa_con_sentido_nulo(libro: Libro) -> None:
    with pytest.raises(errors.NotNullViolation) as e, libro.conexion.transaction():
        libro.agregar("imputacion", movimiento_id=uuid4(), sentido_del_movimiento=None)
    assert e.value.sqlstate == "23502"
    assert e.value.diag.column_name == "sentido_del_movimiento"
