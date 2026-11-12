"""Tarea 3.2 de `importacion-desde-excel`: confirmar el borrador de saldos (design D7, E6, E8, E10,
E15). Contra PostgreSQL real, llamando al caso de uso con la sesión como `proptech_app`.

Orden de chequeo (D7 del 2a): alcance (404) -> permiso (403) -> candado del complejo -> estado de la
migración, borrador vigente, saldos y diferencias (409) -> carga del 4c (422 de la fecha).
Datos inventados."""

from __future__ import annotations

import threading
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from proptech_core.complejos.aplicacion.errores import Conflicto, NoEncontrado
from proptech_core.cuenta_corriente.aplicacion.errores import EntradaInvalida
from proptech_core.importacion.aplicacion.aceptar import aceptar_diferencias
from proptech_core.importacion.aplicacion.confirmar import ConfirmacionRegistrada, confirmar
from proptech_core.importacion.aplicacion.errores import SinPermiso

from ._edificios import BaseDeEdificio
from ._importacion import RELOJ, Mundo, con_tenant, libro, sembrar
from ._saldos_importados import archivo, con_diferencias, estado_de, subir

pytestmark = pytest.mark.integracion

ACCION = "confirmar_saldos_iniciales"


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


@pytest.fixture
def sesion(mundo: Mundo, sesion_edificio: Session) -> Session:
    con_tenant(sesion_edificio, mundo.admin)
    return sesion_edificio


def _confirmar(
    sesion: Session,
    mundo: Mundo,
    importacion_id: UUID,
    quien: object = None,
    complejo: UUID | None = None,
) -> ConfirmacionRegistrada:
    return confirmar(
        sesion,
        quien or mundo.principal,  # type: ignore[arg-type]
        complejo_id=complejo or mundo.torre,
        importacion_id=importacion_id,
        reloj=RELOJ,
        request_id=uuid4(),
    )


def _escrito(sesion: Session) -> dict[str, object]:
    """Todo lo que confirmar podría escribir, más el estado del edificio y de las importaciones."""
    c: dict[str, object] = {}
    for tabla in (
        "auditoria",
        "cuenta",
        "obligacion",
        "movimiento",
        "carga_de_saldo_inicial",
        "origen_de_saldo_inicial",
    ):
        c[tabla] = sesion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()  # noqa: S608
    c["estados"] = sorted(str(f[0]) for f in sesion.execute(text("SELECT estado FROM importacion")))
    c["migraciones"] = sorted(
        str(f[0]) for f in sesion.execute(text("SELECT estado_migracion FROM complejo"))
    )
    return c


def _rechaza(sesion: Session, error: type[Exception], llamada: object) -> Exception:
    antes = _escrito(sesion)
    with pytest.raises(error) as capturado:
        llamada()  # type: ignore[operator]
    assert _escrito(sesion) == antes, "un rechazo no escribe nada"
    return capturado.value


def _auditorias(sesion: Session) -> list[tuple[object, ...]]:
    return [
        tuple(f)
        for f in sesion.execute(
            text(
                "SELECT entidad, entidad_id, persona_id, detalle FROM auditoria WHERE accion = :a"
            ),
            {"a": ACCION},
        )
    ]


# --- Confirmar --------------------------------------------------------------------------------


def test_confirmar_devuelve_la_carga_los_totales_y_quien_y_cuando(
    mundo: Mundo, sesion: Session
) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    r = _confirmar(sesion, mundo, importacion)
    assert r.importacion_id == importacion
    assert r.estado_migracion == "confirmada"
    assert r.confirmada_por == mundo.principal.persona_id
    assert r.confirmada_en == RELOJ()
    assert (
        r.totales.capital.a_texto(),
        r.totales.interes_importado.a_texto(),
        r.totales.credito.a_texto(),
    ) == ("320000.00", "6000.00", "6000.00")
    carga = sesion.execute(
        text(
            "SELECT id, operacion_id, origen, archivo, fecha_de_migracion, registrado_por "
            "FROM carga_de_saldo_inicial WHERE complejo_id = :c"
        ),
        {"c": mundo.torre},
    ).one()
    assert tuple(carga) == (
        r.carga_id,
        importacion,
        "importador",
        "saldos-octubre.xlsx",
        date(2026, 10, 15),
        mundo.principal.persona_id,
    )
    assert estado_de(sesion, importacion) == "confirmada"
    assert (
        sesion.execute(
            text("SELECT estado_migracion FROM complejo WHERE id = :c"), {"c": mundo.torre}
        ).scalar_one()
        == "confirmada"
    )


def test_confirmar_audita_una_vez_con_ids_y_sin_montos(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    r = _confirmar(sesion, mundo, importacion)
    assert _auditorias(sesion) == [
        (
            "importacion",
            importacion,
            mundo.principal.persona_id,
            {
                "complejo_id": str(mundo.torre),
                "importacion_id": str(importacion),
                "carga_id": str(r.carga_id),
            },
        )
    ], "una fila, con ids y nunca montos ni nombres (D9)"


def test_con_diferencias_aceptadas_se_confirma_el_borrador(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    aceptar_diferencias(
        sesion,
        mundo.principal,
        complejo_id=mundo.torre,
        importacion_id=importacion,
        reloj=RELOJ,
        request_id=uuid4(),
    )
    assert _confirmar(sesion, mundo, importacion).totales.capital.a_texto() == "320000.00"


@pytest.mark.parametrize("quien", ["super_admin", "principal"])
def test_los_que_pueden_confirmar(mundo: Mundo, sesion: Session, quien: str) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    assert _confirmar(sesion, mundo, importacion, getattr(mundo, quien)).carga_id


# --- Los 409 y el 422 -------------------------------------------------------------------------


def test_diferencias_sin_aceptar(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    error = _rechaza(sesion, Conflicto, lambda: _confirmar(sesion, mundo, importacion))
    assert isinstance(error, Conflicto) and error.campo == "diferencias"


def test_la_aceptacion_de_otro_borrador_no_vale(mundo: Mundo, sesion: Session) -> None:
    primero = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    aceptar_diferencias(
        sesion,
        mundo.principal,
        complejo_id=mundo.torre,
        importacion_id=primero,
        reloj=RELOJ,
        request_id=uuid4(),
    )
    from ._saldos_importados import control_base

    control = control_base()
    control[0][1] = "159000.00"
    control[1][1] = "100000.00"
    segundo = subir(
        sesion,
        mundo.super_admin,
        mundo.torre,
        archivo(control=control, con_unidades=False),
        nombre="otro.xlsx",
    ).importacion_id
    error = _rechaza(sesion, Conflicto, lambda: _confirmar(sesion, mundo, segundo))
    assert isinstance(error, Conflicto) and error.campo == "diferencias"
    error = _rechaza(sesion, Conflicto, lambda: _confirmar(sesion, mundo, primero))
    assert isinstance(error, Conflicto) and error.campo == "importacion_id"


def test_una_importacion_inexistente(mundo: Mundo, sesion: Session) -> None:
    subir(sesion, mundo.super_admin, mundo.torre, archivo())
    error = _rechaza(sesion, Conflicto, lambda: _confirmar(sesion, mundo, uuid4()))
    assert isinstance(error, Conflicto) and error.campo == "importacion_id"


def test_una_importacion_sin_hoja_de_saldos(mundo: Mundo, sesion: Session) -> None:
    """E10: el edificio con padrón y un archivo sin `Saldos` no tiene nada que confirmar."""
    sin_saldos = libro({"Notas": [["Texto"], ["sin saldos"]]})
    importacion = subir(sesion, mundo.super_admin, mundo.con_padron, sin_saldos).importacion_id
    error = _rechaza(
        sesion,
        Conflicto,
        lambda: _confirmar(sesion, mundo, importacion, complejo=mundo.con_padron),
    )
    assert isinstance(error, Conflicto) and error.campo == "saldos"


@pytest.mark.parametrize("estado", ["confirmada", "sin_saldos_previos"])
def test_con_la_migracion_cerrada(mundo: Mundo, sesion: Session, estado: str) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    sesion.execute(
        text("UPDATE complejo SET estado_migracion = :e WHERE id = :c"),
        {"e": estado, "c": mundo.torre},
    )
    error = _rechaza(sesion, Conflicto, lambda: _confirmar(sesion, mundo, importacion))
    assert isinstance(error, Conflicto) and error.campo == "estado_migracion"


def test_repetir_la_confirmacion(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    _confirmar(sesion, mundo, importacion)
    error = _rechaza(sesion, Conflicto, lambda: _confirmar(sesion, mundo, importacion))
    assert isinstance(error, Conflicto) and error.campo == "estado_migracion"
    assert len(_auditorias(sesion)) == 1


def test_una_fecha_de_migracion_futura_la_rechaza_la_carga_y_no_queda_nada(
    mundo: Mundo, sesion: Session
) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    sesion.execute(
        text("UPDATE importacion SET fecha_de_migracion = :f WHERE id = :i"),
        {"f": date(2026, 11, 13), "i": importacion},  # un día después del "hoy" de RELOJ
    )
    error = _rechaza(sesion, EntradaInvalida, lambda: _confirmar(sesion, mundo, importacion))
    assert isinstance(error, EntradaInvalida) and error.campo == "fecha_de_migracion"
    assert estado_de(sesion, importacion) == "borrador"


# --- Permiso y alcance ------------------------------------------------------------------------


@pytest.mark.parametrize("quien", ["de_la_torre", "contador", "auxiliar"])
def test_sin_el_permiso_de_confirmar(mundo: Mundo, sesion: Session, quien: str) -> None:
    """El administrador por edificio no confirma (E6), tampoco contador ni auxiliar."""
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    error = _rechaza(
        sesion, SinPermiso, lambda: _confirmar(sesion, mundo, importacion, getattr(mundo, quien))
    )
    assert isinstance(error, SinPermiso) and error.permiso_faltante == ACCION


def test_un_administrador_de_otro_edificio_no_lo_ve(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    _rechaza(sesion, NoEncontrado, lambda: _confirmar(sesion, mundo, importacion, mundo.de_otro))


@pytest.mark.parametrize("cual", ["inexistente", "de_otra_administracion"])
def test_un_edificio_inexistente_o_de_otra_administracion_no_existe(
    mundo: Mundo, sesion: Session, cual: str
) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    complejo = uuid4() if cual == "inexistente" else mundo.complejo_b
    _rechaza(
        sesion, NoEncontrado, lambda: _confirmar(sesion, mundo, importacion, complejo=complejo)
    )


def test_el_alcance_gana_al_permiso_y_el_permiso_al_estado(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    sesion.execute(
        text("UPDATE complejo SET estado_migracion = 'confirmada' WHERE id = :c"),
        {"c": mundo.torre},
    )
    _rechaza(sesion, NoEncontrado, lambda: _confirmar(sesion, mundo, importacion, mundo.de_otro))
    _rechaza(sesion, SinPermiso, lambda: _confirmar(sesion, mundo, importacion, mundo.de_la_torre))
    error = _rechaza(sesion, Conflicto, lambda: _confirmar(sesion, mundo, importacion))
    assert isinstance(error, Conflicto) and error.campo == "estado_migracion"


# --- El candado del complejo (E8), con dos conexiones reales -------------------------------------


def _en_otro_hilo(
    mundo: Mundo, base: BaseDeEdificio, importacion: UUID
) -> tuple[threading.Thread, list[Any]]:
    """Confirma en otra conexión y otra transacción; el resultado (o el error) queda en la lista."""
    resultado: list[Any] = []

    def conectar() -> psycopg.Connection:
        conexion = base.conectar_app()
        conexion.autocommit = False
        return conexion

    def correr() -> None:
        motor = create_engine("postgresql+psycopg://", creator=conectar, poolclass=NullPool)
        try:
            with Session(motor) as otra:
                con_tenant(otra, mundo.admin)
                try:
                    resultado.append(_confirmar(otra, mundo, importacion))
                    otra.commit()
                except Exception as error:
                    otra.rollback()
                    resultado.append(error)
        finally:
            motor.dispose()

    return threading.Thread(target=correr), resultado


def _cargas(mundo: Mundo) -> int:
    with mundo.conectar() as c:
        (cantidad,) = c.execute("SELECT count(*) FROM carga_de_saldo_inicial").fetchone()
        c.rollback()
    return int(cantidad)


def test_la_segunda_confirmacion_espera_a_la_primera_y_da_conflicto(
    mundo: Mundo, base_del_edificio: BaseDeEdificio, sesion: Session
) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    sesion.commit()
    con_tenant(sesion, mundo.admin)
    _confirmar(sesion, mundo, importacion)  # la primera, todavía sin confirmar la transacción
    hilo, resultado = _en_otro_hilo(mundo, base_del_edificio, importacion)
    hilo.start()
    hilo.join(timeout=2)
    assert hilo.is_alive(), "la segunda confirmación no esperó el candado del complejo"
    sesion.commit()
    hilo.join(timeout=30)
    assert len(resultado) == 1 and isinstance(resultado[0], Conflicto), resultado
    assert resultado[0].campo == "estado_migracion"
    assert _cargas(mundo) == 1, "una sola carga en el libro"


def test_confirmar_pierde_contra_un_sin_saldos_previos_que_ya_tenia_el_candado(
    mundo: Mundo, base_del_edificio: BaseDeEdificio, sesion: Session
) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    sesion.commit()
    with mundo.conectar() as otra:
        otra.execute("SELECT id FROM complejo WHERE id = %s FOR UPDATE", (mundo.torre,))
        hilo, resultado = _en_otro_hilo(mundo, base_del_edificio, importacion)
        hilo.start()
        hilo.join(timeout=2)
        assert hilo.is_alive(), "confirmar no esperó el candado que ya tenía otra transacción"
        otra.execute(
            "UPDATE complejo SET estado_migracion = 'sin_saldos_previos' WHERE id = %s",
            (mundo.torre,),
        )
        otra.commit()
    hilo.join(timeout=30)
    assert len(resultado) == 1 and isinstance(resultado[0], Conflicto), resultado
    assert resultado[0].campo == "estado_migracion"
    assert _cargas(mundo) == 0, "con sin saldos previos no hay carga en el libro"
    with mundo.conectar() as c:
        assert c.execute(
            "SELECT estado FROM importacion WHERE id = %s", (importacion,)
        ).fetchone() == ("borrador",)
        assert c.execute(
            "SELECT estado_migracion FROM complejo WHERE id = %s", (mundo.torre,)
        ).fetchone() == ("sin_saldos_previos",)
        c.rollback()
