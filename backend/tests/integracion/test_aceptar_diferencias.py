"""Tarea 2.4 de `importacion-desde-excel`: aceptar las diferencias del borrador (design D6, E6, E8).
Contra PostgreSQL real, llamando al caso de uso con la sesión como `proptech_app`.

Orden de chequeo (D7 del 2a): alcance (404) -> permiso (403) -> estado de la migración, borrador
vigente, aceptación previa y diferencias (409). Datos inventados."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.complejos.aplicacion.errores import Conflicto, NoEncontrado
from proptech_core.importacion.aplicacion.aceptar import AceptacionRegistrada, aceptar_diferencias
from proptech_core.importacion.aplicacion.comparar import comparar_borrador
from proptech_core.importacion.aplicacion.errores import SinPermiso

from ._edificios import BaseDeEdificio
from ._importacion import RELOJ, Mundo, con_tenant, sembrar
from ._saldos_importados import (
    archivo,
    con_diferencias,
    conteos_del_borrador,
    control_base,
    subir,
)

pytestmark = pytest.mark.integracion

ACCION = "aceptar_diferencias_de_saldos"
DOS_DIFERENCIAS = {
    ("1A", "169000.00", "159000.00", "10000.00"),
    ("2A", "52000.00", "62000.00", "-10000.00"),
}


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


@pytest.fixture
def sesion(mundo: Mundo, sesion_edificio: Session) -> Session:
    con_tenant(sesion_edificio, mundo.admin)
    return sesion_edificio


def _aceptar(
    sesion: Session,
    mundo: Mundo,
    importacion_id: UUID,
    identidad: Identidad | None = None,
    complejo: UUID | None = None,
) -> AceptacionRegistrada:
    return aceptar_diferencias(
        sesion,
        identidad or mundo.principal,
        complejo_id=complejo or mundo.torre,
        importacion_id=importacion_id,
        reloj=RELOJ,
        request_id=uuid4(),
    )


def _diferencias(lista: Any) -> set[tuple[str, str, str, str]]:
    return {(d.unidad, d.borrador, d.control, d.diferencia) for d in lista}


def _rechaza(sesion: Session, error: type[Exception], llamada: Any) -> Exception:
    antes = conteos_del_borrador(sesion)
    with pytest.raises(error) as capturado:
        llamada()
    assert conteos_del_borrador(sesion) == antes, "un rechazo no escribe nada"
    return capturado.value


def _auditorias(sesion: Session) -> int:
    return int(
        sesion.execute(
            text("SELECT count(*) FROM auditoria WHERE accion = :a"), {"a": ACCION}
        ).scalar_one()
    )


# --- Aceptar ----------------------------------------------------------------------------------


def test_aceptar_registra_quien_cuando_y_la_lista_exacta(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    registrada = _aceptar(sesion, mundo, importacion)
    assert _diferencias(registrada.diferencias) == DOS_DIFERENCIAS
    assert registrada.aceptada_por == mundo.principal.persona_id
    assert registrada.aceptada_en == RELOJ()
    fila = sesion.execute(
        text(
            "SELECT importacion_id, complejo_id, aceptada_por, aceptada_en, diferencias "
            "FROM aceptacion_de_diferencias WHERE id = :i"
        ),
        {"i": registrada.aceptacion_id},
    ).one()
    assert (fila[0], fila[1], fila[2], fila[3]) == (
        importacion,
        mundo.torre,
        mundo.principal.persona_id,
        RELOJ(),
    )
    guardadas = {(d["unidad"], d["borrador"], d["control"], d["diferencia"]) for d in fila[4]}
    assert guardadas == DOS_DIFERENCIAS, "lo guardado es la lista exacta de diferencias"


def test_aceptar_audita_una_vez_con_la_aceptacion_como_entidad(
    mundo: Mundo, sesion: Session
) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    registrada = _aceptar(sesion, mundo, importacion)
    filas = sesion.execute(
        text("SELECT entidad, entidad_id, persona_id, detalle FROM auditoria WHERE accion = :a"),
        {"a": ACCION},
    ).all()
    assert len(filas) == 1
    entidad, entidad_id, persona, detalle = filas[0]
    assert (entidad, entidad_id, persona) == (
        "aceptacion_de_diferencias",
        registrada.aceptacion_id,
        mundo.principal.persona_id,
    )
    assert detalle == {
        "complejo_id": str(mundo.torre),
        "importacion_id": str(importacion),
        "unidades_con_diferencia": 2,
    }, "la auditoría guarda cantidades, nunca nombres ni montos"


def test_despues_de_aceptar_la_comparacion_muestra_la_aceptacion(
    mundo: Mundo, sesion: Session
) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    registrada = _aceptar(sesion, mundo, importacion)
    c = comparar_borrador(sesion, mundo.super_admin, complejo_id=mundo.torre)
    assert c.aceptacion is not None
    assert c.aceptacion.aceptacion_id == registrada.aceptacion_id
    assert _diferencias(c.aceptacion.diferencias) == DOS_DIFERENCIAS
    assert c.aceptacion.aceptada_por == mundo.principal.persona_id
    assert c.requiere_aceptacion is False


def test_las_diferencias_se_guardan_ordenadas_y_con_el_signo(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    registrada = _aceptar(sesion, mundo, importacion)
    assert [d.unidad for d in registrada.diferencias] == ["1A", "2A"]
    assert [d.diferencia for d in registrada.diferencias] == ["10000.00", "-10000.00"]


def test_solo_se_guardan_las_unidades_con_diferencia(mundo: Mundo, sesion: Session) -> None:
    control = control_base()
    control[1][1] = "100000.00"  # 1B con $5.000 de diferencia; el resto coincide
    importacion = subir(
        sesion, mundo.super_admin, mundo.torre, archivo(control=control)
    ).importacion_id
    registrada = _aceptar(sesion, mundo, importacion)
    assert _diferencias(registrada.diferencias) == {("1B", "105000.00", "100000.00", "5000.00")}


@pytest.mark.parametrize("quien", ["super_admin", "principal"])
def test_los_que_pueden_aceptar(mundo: Mundo, sesion: Session, quien: str) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    assert _aceptar(sesion, mundo, importacion, getattr(mundo, quien)).aceptacion_id


# --- Los 409 ----------------------------------------------------------------------------------


def test_aceptar_dos_veces(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    _aceptar(sesion, mundo, importacion)
    error = _rechaza(sesion, Conflicto, lambda: _aceptar(sesion, mundo, importacion))
    assert isinstance(error, Conflicto) and error.campo == "aceptacion"
    assert _auditorias(sesion) == 1


def test_un_borrador_sin_diferencias_no_se_acepta(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    error = _rechaza(sesion, Conflicto, lambda: _aceptar(sesion, mundo, importacion))
    assert isinstance(error, Conflicto) and error.campo == "diferencias"


def test_una_importacion_que_no_es_el_borrador_vigente(mundo: Mundo, sesion: Session) -> None:
    primero = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    control = control_base()
    control[0][1] = "159000.00"
    control[1][1] = "100000.00"  # otro contenido
    subir(
        sesion,
        mundo.super_admin,
        mundo.torre,
        archivo(control=control, con_unidades=False),
        nombre="otro.xlsx",
    )
    error = _rechaza(sesion, Conflicto, lambda: _aceptar(sesion, mundo, primero))
    assert isinstance(error, Conflicto) and error.campo == "importacion_id"


def test_una_importacion_inexistente_o_de_otro_edificio_no_es_el_borrador_vigente(
    mundo: Mundo, sesion: Session
) -> None:
    subir(sesion, mundo.super_admin, mundo.torre, con_diferencias())
    ajena = subir(
        sesion,
        mundo.super_admin,
        mundo.con_padron,
        archivo([["9Z", None, None, None, "10.00", None]], [["9Z", "5.00"]], con_unidades=False),
    ).importacion_id
    for importacion in (uuid4(), ajena):
        error = _rechaza(sesion, Conflicto, lambda i=importacion: _aceptar(sesion, mundo, i))
        assert isinstance(error, Conflicto) and error.campo == "importacion_id"


@pytest.mark.parametrize("estado", ["confirmada", "sin_saldos_previos"])
def test_con_la_migracion_cerrada(mundo: Mundo, sesion: Session, estado: str) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    sesion.execute(
        text("UPDATE complejo SET estado_migracion = :e WHERE id = :c"),
        {"e": estado, "c": mundo.torre},
    )
    error = _rechaza(sesion, Conflicto, lambda: _aceptar(sesion, mundo, importacion))
    assert isinstance(error, Conflicto) and error.campo == "estado_migracion"


def test_un_borrador_nuevo_deja_sin_valor_la_aceptacion_anterior(
    mundo: Mundo, sesion: Session
) -> None:
    primero = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    _aceptar(sesion, mundo, primero)
    control = control_base()
    control[0][1] = "159000.00"
    control[2][1] = "62000.00"
    control[1][1] = "104000.00"
    segundo = subir(
        sesion,
        mundo.super_admin,
        mundo.torre,
        archivo(control=control, con_unidades=False),
        nombre="otro.xlsx",
    ).importacion_id
    c = comparar_borrador(sesion, mundo.super_admin, complejo_id=mundo.torre)
    assert c.importacion_id == segundo
    assert c.aceptacion is None, "la aceptación del borrador anterior no vale para el nuevo"
    assert c.requiere_aceptacion is True
    error = _rechaza(sesion, Conflicto, lambda: _aceptar(sesion, mundo, primero))
    assert isinstance(error, Conflicto) and error.campo == "importacion_id"
    assert _aceptar(sesion, mundo, segundo).aceptacion_id, "el nuevo se acepta por sí mismo"


# --- Permiso y alcance ------------------------------------------------------------------------


@pytest.mark.parametrize("quien", ["de_la_torre", "contador", "auxiliar"])
def test_sin_el_permiso_de_aceptar(mundo: Mundo, sesion: Session, quien: str) -> None:
    """El administrador por edificio no acepta (E6), tampoco contador ni auxiliar."""
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    error = _rechaza(
        sesion, SinPermiso, lambda: _aceptar(sesion, mundo, importacion, getattr(mundo, quien))
    )
    assert isinstance(error, SinPermiso) and error.permiso_faltante == ACCION


def test_un_administrador_de_otro_edificio_no_lo_ve(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    _rechaza(sesion, NoEncontrado, lambda: _aceptar(sesion, mundo, importacion, mundo.de_otro))


@pytest.mark.parametrize("quien", ["inexistente", "de_otra_administracion"])
def test_un_edificio_inexistente_o_de_otra_administracion_no_existe(
    mundo: Mundo, sesion: Session, quien: str
) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    complejo = uuid4() if quien == "inexistente" else mundo.complejo_b
    _rechaza(sesion, NoEncontrado, lambda: _aceptar(sesion, mundo, importacion, complejo=complejo))


def test_el_alcance_gana_al_permiso_y_el_permiso_al_estado(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    sesion.execute(
        text("UPDATE complejo SET estado_migracion = 'confirmada' WHERE id = :c"),
        {"c": mundo.torre},
    )
    _rechaza(sesion, NoEncontrado, lambda: _aceptar(sesion, mundo, importacion, mundo.de_otro))
    _rechaza(sesion, SinPermiso, lambda: _aceptar(sesion, mundo, importacion, mundo.de_la_torre))


# --- El candado del complejo (E8) ---------------------------------------------------------------


def test_aceptar_toma_el_candado_del_complejo(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    sesion.commit()  # la subida ya soltó su propio candado: lo que se mira es el de aceptar
    con_tenant(sesion, mundo.admin)
    _aceptar(sesion, mundo, importacion)
    with mundo.conectar() as otra:
        with pytest.raises(psycopg.errors.LockNotAvailable):
            otra.execute("SELECT id FROM complejo WHERE id = %s FOR UPDATE NOWAIT", (mundo.torre,))
        otra.rollback()


def test_dos_aceptaciones_simultaneas_una_gana(
    mundo: Mundo, base_del_edificio: BaseDeEdificio, sesion: Session
) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    sesion.commit()

    def conectar() -> psycopg.Connection:
        conexion = base_del_edificio.conectar_app()
        conexion.autocommit = False
        return conexion

    barrera = threading.Barrier(2)
    resultados: list[Any] = [None, None]

    def correr(i: int) -> None:
        motor = create_engine("postgresql+psycopg://", creator=conectar, poolclass=NullPool)
        try:
            with Session(motor) as s:
                con_tenant(s, mundo.admin)
                barrera.wait()
                try:
                    resultados[i] = _aceptar(s, mundo, importacion)
                    s.commit()
                except Exception as error:
                    s.rollback()
                    resultados[i] = error
        finally:
            motor.dispose()

    hilos = [threading.Thread(target=correr, args=(i,)) for i in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
    ganadoras = [r for r in resultados if isinstance(r, AceptacionRegistrada)]
    perdedoras = [r for r in resultados if isinstance(r, Conflicto)]
    assert (len(ganadoras), len(perdedoras)) == (1, 1), resultados
    assert perdedoras[0].campo == "aceptacion"
    with mundo.conectar() as c:
        assert c.execute(
            "SELECT count(*) FROM aceptacion_de_diferencias WHERE importacion_id = %s",
            (importacion,),
        ).fetchone() == (1,)
        assert c.execute(
            "SELECT count(*) FROM auditoria WHERE accion = %s AND entidad_id = %s",
            (ACCION, ganadoras[0].aceptacion_id),
        ).fetchone() == (1,)
        c.rollback()


def test_la_hora_de_la_aceptacion_es_la_del_reloj_con_zona(mundo: Mundo, sesion: Session) -> None:
    importacion = subir(sesion, mundo.super_admin, mundo.torre, con_diferencias()).importacion_id
    registrada = _aceptar(sesion, mundo, importacion)
    assert registrada.aceptada_en.utcoffset() is not None
    assert registrada.aceptada_en == datetime(2026, 11, 12, 15, tzinfo=UTC)
