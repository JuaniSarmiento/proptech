"""3.6 · Concurrencia contra PostgreSQL real (D2, D4, RC-03, QA-5, QA-6, DB-4, L-011, L-020)."""

import threading
from collections.abc import Iterator
from datetime import date
from functools import partial
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import creditos, cuentas, emisiones, lecturas
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir
from proptech_core.cuenta_corriente.aplicacion.errores import (
    AislamientoNoAdmitido,
    CandadoIncompleto,
    Conflicto,
)
from proptech_core.cuenta_corriente.dominio import imputacion as dominio_imputacion

from ._cuenta_corriente import Mundo, en_hilo, sembrar, sesion_app
from ._edificios import BaseDeEdificio
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def d(t: str) -> Dinero:
    return Dinero(t)


def obligacion(mundo: Mundo, unidad: int, importe: str) -> ObligacionAEmitir:
    return ObligacionAEmitir(
        mundo.unidades[unidad], date(2026, 10, 10), d(importe), d("0.00"), d("0.00")
    )


def emitir_confirmado(
    base: BaseDeEdificio, mundo: Mundo, periodo: date, obls: list[ObligacionAEmitir]
) -> emisiones.EmisionRegistrada:
    with sesion_app(base, mundo.admin) as s:
        r = emisiones.registrar_emision(
            s,
            mundo.identidad,
            emision_id=uuid4(),
            complejo_id=mundo.complejo,
            periodo=periodo,
            obligaciones=obls,
            request_id=uuid4(),
        )
        s.commit()
        return r


def pagar(base: BaseDeEdificio, mundo: Mundo, cuenta: UUID, importe: str, **opciones: Any) -> UUID:
    with sesion_app(base, mundo.admin, **opciones) as s:
        m = creditos.registrar_credito(
            s,
            mundo.identidad,
            cuenta_id=cuenta,
            tipo="pago",
            importe=d(importe),
            fecha_valor=date(2026, 10, 20),
            operacion_id=uuid4(),
            destino=None,
            request_id=uuid4(),
        )
        s.commit()
        return m


def estado(base: BaseDeEdificio, mundo: Mundo, cuenta: UUID) -> Any:
    with sesion_app(base, mundo.admin) as s:
        return lecturas.estado_de_cuenta(s, cuenta_id=cuenta)


def suma_imputada(base: BaseDeEdificio, mundo: Mundo, cuenta: UUID) -> Dinero:
    with sesion_app(base, mundo.admin) as s:
        return Dinero(
            s.execute(
                text("SELECT coalesce(sum(importe), 0)::text FROM imputacion WHERE cuenta_id = :c"),
                {"c": cuenta},
            ).scalar_one()
        )


@pytest.fixture
def barrera_antes_de_imputar(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[threading.Event]]:
    """La barrera va ENTRE leer el estado e imputar (QA-5). Con el candado real la segunda nunca
    llega mientras la primera no confirme: se espera con plazo y sin exigir que llegue (L-020)."""
    llegaron = [threading.Event(), threading.Event()]
    nombres: dict[int, int] = {}
    original = dominio_imputacion.imputar

    def con_barrera(*args: Any, **kwargs: Any) -> Any:
        yo = nombres.setdefault(threading.get_ident(), len(nombres) % 2)
        llegaron[yo].set()
        llegaron[1 - yo].wait(2)
        return original(*args, **kwargs)

    monkeypatch.setattr(creditos, "imputar", con_barrera)
    yield llegaron


def test_dos_pagos_simultaneos(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, barrera_antes_de_imputar: list[threading.Event]
) -> None:
    r = emitir_confirmado(
        base_del_edificio, mundo, date(2026, 10, 1), [obligacion(mundo, 0, "100000.00")]
    )
    cuenta = r.cuentas[mundo.unidades[0]]
    h1, r1 = en_hilo(lambda: pagar(base_del_edificio, mundo, cuenta, "60000.00"))
    h2, r2 = en_hilo(lambda: pagar(base_del_edificio, mundo, cuenta, "60000.00"))
    h1.join(40)
    h2.join(40)
    assert "error" not in r1 and "error" not in r2, (r1.get("error"), r2.get("error"))
    assert suma_imputada(base_del_edificio, mundo, cuenta) == d("100000.00")
    e = estado(base_del_edificio, mundo, cuenta)
    assert (e.deuda, e.credito_a_favor) == (d("0.00"), d("20000.00"))


def test_dos_emisiones_simultaneas_del_mismo_periodo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La barrera va después de calcular el intento (paso 2): las dos llegan al INSERT."""
    llegaron = [threading.Event(), threading.Event()]
    nombres: dict[int, int] = {}
    real_execute = Session.execute

    def ejecutar(self: Session, sentencia: Any, *a: Any, **k: Any) -> Any:
        if "INSERT INTO emision" in str(sentencia):
            yo = nombres.setdefault(threading.get_ident(), len(nombres) % 2)
            llegaron[yo].set()
            llegaron[1 - yo].wait(2)
        return real_execute(self, sentencia, *a, **k)

    monkeypatch.setattr(Session, "execute", ejecutar)
    obls = [obligacion(mundo, 1, "100.00")]
    h1, r1 = en_hilo(lambda: emitir_confirmado(base_del_edificio, mundo, date(2026, 10, 1), obls))
    h2, r2 = en_hilo(lambda: emitir_confirmado(base_del_edificio, mundo, date(2026, 10, 1), obls))
    h1.join(40)
    h2.join(40)
    resultados = sorted(["ok" if "valor" in r else type(r["error"]).__name__ for r in (r1, r2)])
    assert resultados == ["Conflicto", "ok"], (r1, r2)
    error = r1.get("error") or r2.get("error")
    assert isinstance(error, Conflicto) and error.campo == "periodo"
    with sesion_app(base_del_edificio, mundo.admin) as s:
        assert (
            s.execute(
                text("SELECT count(*) FROM emision WHERE complejo_id = :c AND periodo = :p"),
                {"c": mundo.complejo, "p": date(2026, 10, 1)},
            ).scalar_one()
            == 1
        )


def test_una_emision_y_un_pago_a_la_vez(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    previa = emitir_confirmado(
        base_del_edificio, mundo, date(2026, 9, 1), [obligacion(mundo, 0, "0.01")]
    )
    cuenta = previa.cuentas[mundo.unidades[0]]
    pagar(base_del_edificio, mundo, cuenta, "0.01")  # deuda inicial cero
    obls = [obligacion(mundo, n, "40000.00") for n in range(10)]
    for orden in ("emision_primero", "pago_primero"):
        periodo = date(2026, 10, 1) if orden == "emision_primero" else date(2026, 11, 1)
        h1, r1 = en_hilo(partial(emitir_confirmado, base_del_edificio, mundo, periodo, obls))
        h2, r2 = en_hilo(lambda: pagar(base_del_edificio, mundo, cuenta, "40000.00"))
        h1.join(40)
        h2.join(40)
        assert "error" not in r1 and "error" not in r2, (orden, r1.get("error"), r2.get("error"))
        e = estado(base_del_edificio, mundo, cuenta)
        assert (e.deuda, e.credito_a_favor) == (d("0.00"), d("0.00")), orden


#: El mutante de RC-03 pone esto en True: cada emisión crea sus cuentas en el orden de su entrada.
CREAR_EN_ORDEN_DE_ENTRADA = False


def test_emisiones_con_unidades_nuevas_cruzadas(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RC-03: períodos DISTINTOS del mismo edificio, así el único de emisión no tapa el defecto."""
    a, b = sorted(mundo.unidades[10:12])
    llegaron = [threading.Event(), threading.Event()]
    nombres: dict[int, int] = {}
    original = cuentas.crear_cuentas_de_unidades

    def crear(sesion: Session, *, complejo_id: UUID, unidad_ids: list[UUID]) -> dict[UUID, UUID]:
        if not CREAR_EN_ORDEN_DE_ENTRADA:
            return original(sesion, complejo_id=complejo_id, unidad_ids=unidad_ids)
        resultado: dict[UUID, UUID] = {}
        for u in unidad_ids:  # de a una, en el orden del pedido, con barrera tras la primera
            resultado.update(original(sesion, complejo_id=complejo_id, unidad_ids=[u]))
            yo = nombres.setdefault(threading.get_ident(), len(nombres) % 2)
            llegaron[yo].set()
            llegaron[1 - yo].wait(2)
        return resultado

    monkeypatch.setattr(emisiones, "crear_cuentas_de_unidades", crear)
    ua, ub = mundo.unidades.index(a), mundo.unidades.index(b)
    oct_ = [obligacion(mundo, ua, "1.00"), obligacion(mundo, ub, "1.00")]
    nov = [obligacion(mundo, ub, "1.00"), obligacion(mundo, ua, "1.00")]
    h1, r1 = en_hilo(lambda: emitir_confirmado(base_del_edificio, mundo, date(2026, 10, 1), oct_))
    h2, r2 = en_hilo(lambda: emitir_confirmado(base_del_edificio, mundo, date(2026, 11, 1), nov))
    h1.join(40)
    h2.join(40)
    assert (r1.get("error"), r2.get("error")) == (None, None)


def test_cuentas_distintas_no_se_esperan(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    r = emitir_confirmado(
        base_del_edificio,
        mundo,
        date(2026, 10, 1),
        [obligacion(mundo, 2, "10.00"), obligacion(mundo, 3, "10.00")],
    )
    c1, c2 = r.cuentas[mundo.unidades[2]], r.cuentas[mundo.unidades[3]]
    retenida = threading.Event()
    soltar = threading.Event()

    def demorada() -> None:
        with sesion_app(base_del_edificio, mundo.admin) as s:
            cuentas.bloquear_cuentas(s, [c1])
            retenida.set()
            soltar.wait(20)
            s.commit()

    h, _ = en_hilo(demorada)
    assert retenida.wait(10)
    try:
        pagar(base_del_edificio, mundo, c2, "10.00")  # confirma sin esperar a la otra
    finally:
        soltar.set()
        h.join(20)


def test_candado_borrado_entre_insertar_y_bloquear(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """QA-6: el arranque borra el candado después del INSERT y antes del FOR UPDATE."""
    r = emitir_confirmado(
        base_del_edificio, mundo, date(2026, 10, 1), [obligacion(mundo, 4, "10.00")]
    )
    cuenta = r.cuentas[mundo.unidades[4]]
    with sesion_app(base_del_edificio, mundo.admin) as s:

        @event.listens_for(s.get_bind(), "before_cursor_execute")
        def _borrar(conn: Any, cursor: Any, sentencia: str, *args: Any) -> None:
            if "FOR UPDATE" in sentencia and "candado_de_cuenta" in sentencia:
                with arranque(base_del_edificio) as c:
                    c.execute("DELETE FROM candado_de_cuenta WHERE cuenta_id = %s", (cuenta,))

        with pytest.raises(CandadoIncompleto):
            creditos.registrar_credito(
                s,
                mundo.identidad,
                cuenta_id=cuenta,
                tipo="pago",
                importe=d("10.00"),
                fecha_valor=date(2026, 10, 20),
                operacion_id=uuid4(),
                destino=None,
                request_id=uuid4(),
            )
        assert (
            s.execute(
                text("SELECT count(*) FROM movimiento WHERE cuenta_id = :c"), {"c": cuenta}
            ).scalar_one()
            == 0
        )


def test_repeatable_read_no_usa_una_foto_vieja(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """DB-4: con la foto vieja se imputaría $120.000 sobre $100.000; el chequeo lo rechaza."""
    r = emitir_confirmado(
        base_del_edificio, mundo, date(2026, 10, 1), [obligacion(mundo, 5, "100000.00")]
    )
    cuenta = r.cuentas[mundo.unidades[5]]
    with sesion_app(base_del_edificio, mundo.admin, aislamiento="REPEATABLE READ") as vieja:
        lecturas.estado_de_cuenta(vieja, cuenta_id=cuenta)  # toma la foto
        pagar(base_del_edificio, mundo, cuenta, "60000.00")
        with pytest.raises(AislamientoNoAdmitido):
            creditos.registrar_credito(
                vieja,
                mundo.identidad,
                cuenta_id=cuenta,
                tipo="pago",
                importe=d("60000.00"),
                fecha_valor=date(2026, 10, 20),
                operacion_id=uuid4(),
                destino=None,
                request_id=uuid4(),
            )
    assert suma_imputada(base_del_edificio, mundo, cuenta) == d("60000.00")
