"""Aceptación de H-030: registrar el cambio de titular (change 4d `cambio-de-titular`, CRITICAL; R32, D-168).

Cada test lleva su criterio en el nombre (C01…, N01…). Sin la ruta, un 404 contra el 201 esperado es una falla por
aserción; lo que depende de la tabla `cambio_de_titular` pide antes que exista (`filas_del_cambio`).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import psycopg
import pytest

from .._edificios import fijar_tenant
from ._h030 import (
    CLAVES_DEL_CAMBIO,
    EMAIL_DE_ANA,
    EMAIL_DE_DORA,
    FECHA,
    MENSUAL,
    SEP,
    Mundo,
    armar_la_base,
    asignaciones,
    auditorias,
    del_libro,
    deuda_del_libro,
    duenos,
    emitir,
    filas_del_cambio,
    listar,
    no_encontrado,
    no_procesable,
    pagar,
    personas_con_nombre,
    registrar,
    registrar_ok,
    ruta,
    sembrar_deuda,
    sin_permiso,
)

MONTO = re.compile(r"^[0-9]+\.[0-9]{2}$")


def _uuid(texto: object) -> UUID:
    return UUID(str(texto))


# --- C01: el registro ----------------------------------------------------------------------------------


def test_c01_registra_el_cambio_y_responde_con_el_registro(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    cambio = registrar_ok(mundo, "1A", [ana], [{"nombre": "Nora Compradora", "email": "nora@ejemplo.invalid"}])
    assert set(cambio) == CLAVES_DEL_CAMBIO, f"claves de la respuesta: {sorted(cambio)}"
    assert _uuid(cambio["id"]) and cambio["unidad_id"] == str(mundo.unidades["1A"]), cambio
    assert cambio["fecha"] == FECHA, cambio
    assert cambio["vendedores"] == [str(ana)], cambio
    assert len(cambio["compradores"]) == 1, cambio
    comprador = cambio["compradores"][0]
    assert comprador["nombre"] == "Nora Compradora" and comprador["email"] == "nora@ejemplo.invalid", comprador
    assert _uuid(comprador["persona_id"]), f"el comprador trae el id de su persona: {comprador}"
    assert cambio["expensa_del_mes"] == "entera" and cambio["deuda_previa"] == "en_la_unidad", cambio
    assert cambio["registrado_por"] == str(mundo.personas["admin_principal"]), cambio
    assert re.match(r"^\d{4}-\d{2}-\d{2}T", cambio["registrado_en"]), f"registrado_en es un instante: {cambio}"
    assert cambio["aviso"] is None, f"`1A` no tiene deuda: {cambio}"


def test_c01_acepta_las_dos_opciones_en_su_valor_por_defecto_dichas_a_mano(mundo: Mundo) -> None:
    cambio = registrar_ok(mundo, "1A", [mundo.personas["ana"]], expensa_del_mes="entera",
                          deuda_previa="en_la_unidad")
    assert cambio["expensa_del_mes"] == "entera" and cambio["deuda_previa"] == "en_la_unidad", cambio


def test_c01_varios_vendedores_y_varios_compradores(mundo: Mundo) -> None:
    dora, edu = mundo.personas["dora"], mundo.personas["edu"]
    cambio = registrar_ok(mundo, "2A", [dora, edu], [
        {"nombre": "Nora Compradora", "email": "nora@ejemplo.invalid"},
        {"nombre": "Omar Comprador", "email": None},
    ])
    assert sorted(cambio["vendedores"]) == sorted([str(dora), str(edu)]), cambio
    assert [c["nombre"] for c in cambio["compradores"]] == ["Nora Compradora", "Omar Comprador"], cambio
    assert all(_uuid(c["persona_id"]) for c in cambio["compradores"]), cambio


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal", "admin_del_edificio"])
def test_c01_registran_el_super_admin_y_el_administrador_con_alcance(mundo: Mundo, rol: str) -> None:
    mundo.como(rol)
    cambio = registrar_ok(mundo, "1A", [mundo.personas["ana"]])
    assert cambio["registrado_por"] == str(mundo.personas[rol]), cambio


# --- C02: las asignaciones -----------------------------------------------------------------------------


def test_c02_los_vendedores_dejan_de_ser_propietarios_y_los_compradores_pasan_a_serlo(mundo: Mundo) -> None:
    cambio = registrar_ok(mundo, "1A", [mundo.personas["ana"]],
                          [{"nombre": "Nora Compradora", "email": "nora@ejemplo.invalid"}])
    comprador = _uuid(cambio["compradores"][0]["persona_id"])
    assert duenos(mundo, "1A") == {comprador}, "el comprador es el único propietario de `1A`"
    assert mundo.personas["ana"] not in duenos(mundo, "1A")
    fila = mundo.filas("SELECT nombre, email FROM persona WHERE id = %s", (comprador,))
    assert fila == [("Nora Compradora", "nora@ejemplo.invalid")], fila


def test_c02_no_toca_a_los_inquilinos_ni_las_otras_unidades_ni_borra_personas(mundo: Mundo) -> None:
    antes_2b = duenos(mundo, "2B")
    registrar_ok(mundo, "1B", [mundo.personas["carla"]], [{"nombre": "Nora Compradora", "email": None}])
    assert mundo.personas["carla"] not in duenos(mundo, "1B")
    assert duenos(mundo, "1B", "inquilino") == {mundo.personas["beto"]}, "el inquilino de `1B` sigue"
    assert duenos(mundo, "2B") == antes_2b == {mundo.personas["ana"]}, "las otras unidades no cambian"
    assert mundo.filas("SELECT count(*) FROM persona WHERE id = %s", (mundo.personas["carla"],))[0][0] == 1, (
        "el vendedor sigue existiendo como persona")


def test_c02_el_comprador_que_ya_existe_por_email_se_reutiliza(mundo: Mundo) -> None:
    # Alguien con el email de Ana compra `1B`: es la persona que ya existe.
    cambio = registrar_ok(mundo, "1B", [mundo.personas["carla"]], [{"nombre": "Ana Otra Vez", "email": EMAIL_DE_ANA}])
    assert cambio["compradores"][0]["persona_id"] == str(mundo.personas["ana"]), cambio
    assert mundo.filas("SELECT count(*) FROM persona WHERE email = %s", (EMAIL_DE_ANA,))[0][0] == 1
    assert mundo.filas("SELECT nombre FROM persona WHERE id = %s", (mundo.personas["ana"],)) == [("Ana Prueba",)], (
        "no se renombra a quien ya existía")
    assert duenos(mundo, "1B") == {mundo.personas["ana"]}
    assert duenos(mundo, "1A") == {mundo.personas["ana"]}, "Ana sigue siendo propietaria de `1A`"
    assert len(personas_con_nombre(mundo, "Ana Otra Vez")) == 0


def test_c02_un_vendedor_que_tiene_otra_unidad_la_conserva(mundo: Mundo) -> None:
    registrar_ok(mundo, "1A", [mundo.personas["ana"]])
    assert duenos(mundo, "2B") == {mundo.personas["ana"]}, "Ana vendió `1A` y sigue en `2B`"


def test_c02_con_dos_propietarios_vende_sólo_el_elegido(mundo: Mundo) -> None:
    registrar_ok(mundo, "2A", [mundo.personas["dora"]], [{"nombre": "Omar Comprador", "email": None}])
    propietarios = duenos(mundo, "2A")
    assert mundo.personas["dora"] not in propietarios and mundo.personas["edu"] in propietarios, propietarios
    assert len(propietarios) == 2, "Edu y el comprador"


# --- C03: la fila y la auditoría -----------------------------------------------------------------------


def test_c03_queda_una_fila_de_sólo_agregar_con_la_unidad_la_fecha_y_las_dos_elecciones(mundo: Mundo) -> None:
    cambio = registrar_ok(mundo, "1A", [mundo.personas["ana"]])
    assert filas_del_cambio(mundo) == 1
    from ._h030 import superusuario

    fila = superusuario(mundo, "SELECT id, unidad_id, fecha, expensa_del_mes, deuda_previa FROM cambio_de_titular "
                               "WHERE administracion_id = %s", (mundo.admin,))
    assert [(str(f[0]), str(f[1]), str(f[2]), f[3], f[4]) for f in fila] == [
        (cambio["id"], str(mundo.unidades["1A"]), FECHA, "entera", "en_la_unidad")], fila


def test_c03_queda_la_auditoria_registrar_cambio_de_titular(mundo: Mundo) -> None:
    existe = mundo.filas("SELECT count(*) FROM accion_de_auditoria WHERE nombre = 'registrar_cambio_de_titular'")
    assert existe[0][0] == 1, "la migración suma `registrar_cambio_de_titular` al vocabulario de auditoría"
    cambio = registrar_ok(mundo, "1A", [mundo.personas["ana"]])
    filas = auditorias(mundo)
    assert len(filas) == 1, filas
    entidad, entidad_id, persona_id, detalle = filas[0]
    assert (entidad, str(entidad_id), str(persona_id)) == ("cambio_de_titular", cambio["id"],
                                                            str(mundo.personas["admin_principal"])), filas
    assert detalle == {"unidad_id": str(mundo.unidades["1A"]), "fecha": FECHA, "expensa_del_mes": "entera",
                       "deuda_previa": "en_la_unidad"}, detalle


# --- C04: el aviso -------------------------------------------------------------------------------------


def test_c04_con_deuda_trae_el_aviso_con_el_monto_como_texto_y_registra_igual(mundo: Mundo) -> None:
    deuda = sembrar_deuda(mundo, "1A")
    cambio = registrar_ok(mundo, "1A", [mundo.personas["ana"]])
    assert cambio["aviso"] == {"deuda": deuda}, f"el aviso trae lo adeudado ({deuda}): {cambio['aviso']}"
    assert isinstance(cambio["aviso"]["deuda"], str) and MONTO.match(cambio["aviso"]["deuda"]), cambio["aviso"]
    assert filas_del_cambio(mundo) == 1, "el aviso no bloquea: el cambio queda registrado"
    assert duenos(mundo, "1A") != {mundo.personas["ana"]}


def test_c04_sin_deuda_el_aviso_es_nulo(mundo: Mundo) -> None:
    emitir(mundo, SEP, ("2B",))
    pagar(mundo, "2B", MENSUAL["2B"], date(2026, 9, 5))
    assert Decimal(deuda_del_libro(mundo, "2B")) == 0, "precondición: `2B` está al día"
    assert registrar_ok(mundo, "2B", [mundo.personas["ana"]])["aviso"] is None
    assert registrar_ok(mundo, "1B", [mundo.personas["carla"]])["aviso"] is None, "`1B` ni siquiera tiene cuenta"


def test_c04_el_aviso_es_el_de_la_unidad_vendida_y_no_el_de_las_demas(mundo: Mundo) -> None:
    armar_la_base(mundo)
    deuda_1b = deuda_del_libro(mundo, "1B")
    assert Decimal(deuda_1b) > 0
    cambio = registrar_ok(mundo, "1B", [mundo.personas["carla"]])
    assert cambio["aviso"] == {"deuda": deuda_1b}, cambio["aviso"]


# --- C05: el libro no cambia ---------------------------------------------------------------------------


def test_c05_con_las_opciones_por_defecto_el_libro_queda_idéntico(mundo: Mundo) -> None:
    armar_la_base(mundo)
    antes = del_libro(mundo)
    deuda = deuda_del_libro(mundo, "1A")
    registrar_ok(mundo, "1A", [mundo.personas["ana"]])
    assert del_libro(mundo) == antes, "el cambio no escribe en movimiento, imputacion, obligacion, cuenta ni emision"
    assert deuda_del_libro(mundo, "1A") == deuda, "el estado de cuenta de la unidad es el mismo"


# --- C06: la lista -------------------------------------------------------------------------------------


def test_c06_lista_los_cambios_de_la_unidad_el_más_nuevo_primero(mundo: Mundo) -> None:
    primero = registrar_ok(mundo, "1A", [mundo.personas["ana"]], [{"nombre": "Nora Compradora", "email": None}],
                           fecha="2026-10-01")
    nora = _uuid(primero["compradores"][0]["persona_id"])
    segundo = registrar_ok(mundo, "1A", [nora], [{"nombre": "Omar Comprador", "email": None}], fecha=FECHA)
    registrar_ok(mundo, "1B", [mundo.personas["carla"]])
    r = listar(mundo, "1A")
    assert r.status_code == 200, f"se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    cuerpo = r.json()
    assert [c["id"] for c in cuerpo] == [segundo["id"], primero["id"]], f"el más nuevo primero y sólo `1A`: {cuerpo}"
    sin_aviso = CLAVES_DEL_CAMBIO - {"aviso"}
    assert sin_aviso <= set(cuerpo[0]), sorted(cuerpo[0])
    assert {k: v for k, v in cuerpo[1].items() if k in sin_aviso} == {k: v for k, v in primero.items()
                                                                    if k in sin_aviso}, "el mismo registro del POST"


def test_c06_una_unidad_sin_cambios_da_la_lista_vacía(mundo: Mundo) -> None:
    r = listar(mundo, "2B")
    assert r.status_code == 200, f"se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == [], r.json()


# --- N01: permisos y alcance ---------------------------------------------------------------------------


@pytest.mark.parametrize("rol", ["contador", "contador_del_edificio", "auxiliar", "consejo", "ana", "carla"])
def test_n01_sin_el_permiso_da_403_y_no_cambia_nada(mundo: Mundo, rol: str) -> None:
    antes = asignaciones(mundo)
    mundo.como(rol)
    sin_permiso(registrar(mundo, "1A", [mundo.personas["ana"]]))
    assert asignaciones(mundo) == antes
    assert filas_del_cambio(mundo) == 0 and auditorias(mundo) == []


@pytest.mark.parametrize("rol", ["admin_de_otro_edificio", "consejo_de_otro_edificio", "administracion_b"])
def test_n01_fuera_del_alcance_da_404(mundo: Mundo, rol: str) -> None:
    mundo.como(rol)
    no_encontrado(registrar(mundo, "1A", [mundo.personas["ana"]]))
    no_encontrado(listar(mundo, "1A"))


def test_n01_un_edificio_de_otra_administración_o_una_unidad_que_no_es_del_edificio_dan_404(mundo: Mundo) -> None:
    mundo.como("super_admin")
    cuerpo = {"fecha": FECHA, "vendedores": [str(mundo.personas["ana"])],
              "compradores": [{"nombre": "Nora Compradora", "email": None}]}
    no_encontrado(mundo.cliente.post(ruta(mundo, complejo=mundo.edificio_b), json=cuerpo))
    no_encontrado(mundo.cliente.post(ruta(mundo, unidad_id=uuid4()), json=cuerpo))
    no_encontrado(mundo.cliente.post(ruta(mundo, complejo=mundo.otro), json=cuerpo))  # `1A` no es de `otro`


# --- N02: los 422 --------------------------------------------------------------------------------------


def test_n02_un_vendedor_que_no_es_propietario_actual_da_422(mundo: Mundo) -> None:
    no_procesable(registrar(mundo, "1A", [mundo.personas["carla"]]))  # propietaria de otra unidad
    no_procesable(registrar(mundo, "1B", [mundo.personas["beto"]]))  # el inquilino no vende
    no_procesable(registrar(mundo, "1A", [uuid4()]))  # una persona que no existe


def test_n02_sin_vendedores_o_sin_compradores_da_422(mundo: Mundo) -> None:
    no_procesable(registrar(mundo, "1A", []))
    no_procesable(registrar(mundo, "1A", [mundo.personas["ana"]], []))


def test_n02_la_misma_persona_de_los_dos_lados_da_422(mundo: Mundo) -> None:
    # El comprador trae el email de la vendedora: es ella.
    no_procesable(registrar(mundo, "1A", [mundo.personas["ana"]], [{"nombre": "Ana Prueba", "email": EMAIL_DE_ANA}]))
    no_procesable(registrar(mundo, "2A", [mundo.personas["dora"], mundo.personas["edu"]], [
        {"nombre": "Omar Comprador", "email": None}, {"nombre": "Dora Prueba", "email": EMAIL_DE_DORA}]))


def test_n02_una_fecha_futura_da_422(mundo: Mundo) -> None:
    mañana = (date.today() + timedelta(days=1)).isoformat()
    no_procesable(registrar(mundo, "1A", [mundo.personas["ana"]], fecha=mañana))
    no_procesable(registrar(mundo, "1A", [mundo.personas["ana"]], fecha="2099-01-01"))


def test_n02_el_mismo_vendedor_dos_veces_da_422(mundo: Mundo) -> None:
    no_procesable(registrar(mundo, "1A", [mundo.personas["ana"], mundo.personas["ana"]]))


# --- N03: un pedido que falla no deja nada -------------------------------------------------------------


def _foto(m: Mundo) -> tuple[object, ...]:
    return (asignaciones(m), m.filas("SELECT count(*) FROM persona")[0][0], filas_del_cambio(m), auditorias(m),
            del_libro(m))


def test_n03_falla_a_mitad_por_un_comprador_que_es_el_vendedor(mundo: Mundo) -> None:
    antes = _foto(mundo)
    no_procesable(registrar(mundo, "1A", [mundo.personas["ana"]], [
        {"nombre": "Nuevo Comprador", "email": "nuevo.comprador@ejemplo.invalid"},
        {"nombre": "Ana Prueba", "email": EMAIL_DE_ANA},
    ]))
    assert _foto(mundo) == antes, "ni persona nueva, ni fila, ni asignaciones, ni auditoría"
    assert personas_con_nombre(mundo, "Nuevo Comprador") == []


def test_n03_falla_a_mitad_por_un_segundo_vendedor_que_no_es_propietario(mundo: Mundo) -> None:
    sembrar_deuda(mundo, "2A")
    antes = _foto(mundo)
    no_procesable(registrar(mundo, "2A", [mundo.personas["dora"], mundo.personas["ana"]],
                            [{"nombre": "Nuevo Comprador", "email": None}]))
    assert _foto(mundo) == antes
    assert duenos(mundo, "2A") == {mundo.personas["dora"], mundo.personas["edu"]}, "Dora sigue siendo propietaria"


def test_n03_falla_por_fecha_futura_con_todo_lo_demás_válido(mundo: Mundo) -> None:
    antes = _foto(mundo)
    no_procesable(registrar(mundo, "1A", [mundo.personas["ana"]], fecha="2099-01-01"))
    assert _foto(mundo) == antes


# --- N04: sólo agregar y RLS ---------------------------------------------------------------------------


@pytest.mark.parametrize("sentencia", ["UPDATE cambio_de_titular SET fecha = fecha",
                                       "DELETE FROM cambio_de_titular"])
def test_n04_la_app_no_edita_ni_borra(mundo: Mundo, sentencia: str) -> None:
    registrar_ok(mundo, "1A", [mundo.personas["ana"]])
    assert filas_del_cambio(mundo) == 1
    with mundo.base.conectar_app() as conexion:
        with pytest.raises(psycopg.Error) as error, conexion.transaction():
            fijar_tenant(conexion, mundo.admin)
            conexion.execute(sentencia)  # type: ignore[arg-type]
    assert isinstance(error.value, psycopg.errors.InsufficientPrivilege), (
        f"{sentencia}: se esperaba falta de permiso, llegó {type(error.value).__name__}: {error.value}")


def test_n04_otra_administración_no_ve_la_tabla_y_la_rls_está_forzada(mundo: Mundo) -> None:
    registrar_ok(mundo, "1A", [mundo.personas["ana"]])
    assert filas_del_cambio(mundo) == 1
    from ._h030 import superusuario

    flags = superusuario(mundo, "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                                "WHERE oid = 'public.cambio_de_titular'::regclass")
    assert flags == [(True, True)], f"RLS habilitada y forzada: {flags}"
    with mundo.base.conectar_app() as conexion, conexion.transaction():
        fijar_tenant(conexion, mundo.admin_b)
        assert conexion.execute("SELECT count(*) FROM cambio_de_titular").fetchone() == (0,), (
            "la administración B no ve los cambios de A")
    with mundo.base.conectar_app() as conexion, conexion.transaction():
        fijar_tenant(conexion, mundo.admin)
        assert conexion.execute("SELECT count(*) FROM cambio_de_titular").fetchone() == (1,)
