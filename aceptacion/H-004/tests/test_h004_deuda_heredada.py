"""H-004 · C09, C15 y C16: la deuda heredada del 4b (RF-01, RF-02, RB-6) y su extensión a las
cuentas que la emisión sólo toca con interés (design D0, PR-02)."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero, MontoInvalido
from proptech_core.compartido.reparto import redondear_al_centavo
from proptech_core.cuenta_corriente.aplicacion import correcciones, emisiones
from proptech_core.cuenta_corriente.aplicacion.correcciones import PedidoDeCorreccion

from .._cuenta_corriente import Mundo, en_hilo, sembrar, sesion_app
from .._edificios import BaseDeEdificio
from ._h004 import (
    OCT,
    SEP,
    configurar,
    contra_asentar,
    d,
    dia,
    emitir,
    intereses,
    obl,
    obligacion_de,
    pagar,
)

pytestmark = pytest.mark.integracion

#: Lo que se le da a la otra conexión para confirmarse si nadie la frena.
_ESPERA = 2.0


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


# --- C15 · RB-6 ------------------------------------------------------------------------------


@pytest.mark.parametrize("valor", ["1e30", "-1e30", "1e40"])
def test_c15_valor_enorme_rechazado_como_monto_invalido(valor: str) -> None:
    """Escenario: Valor enorme rechazado como monto inválido"""
    try:
        redondear_al_centavo(Decimal(valor))
    except MontoInvalido:
        return
    except Exception as e:
        raise AssertionError(f"sale {type(e).__name__} en vez de MontoInvalido") from e
    raise AssertionError("no rechazó el valor enorme")


def test_c15_el_medio_sube() -> None:
    """Escenario: El medio sube"""
    assert redondear_al_centavo(Decimal("0.125")) == Dinero("0.13")
    assert redondear_al_centavo(Decimal("0.124999")) == Dinero("0.12")
    assert redondear_al_centavo(Decimal("-0.125")) == Dinero("-0.13")


def test_c15_float_rechazado() -> None:
    """Escenario: Float rechazado"""
    with pytest.raises(MontoInvalido):
        redondear_al_centavo(0.125)  # type: ignore[arg-type]


# --- C09 · Una sola lectura y candados -------------------------------------------------------


@contextmanager
def sentencias(s: Session) -> Iterator[list[tuple[str, Any]]]:
    """Cada sentencia que la sesión manda a PostgreSQL, con sus parámetros."""
    vistas: list[tuple[str, Any]] = []
    bind = s.get_bind()

    def ver(conn: Any, cursor: Any, sentencia: str, parametros: Any, *args: Any) -> None:
        vistas.append((sentencia, parametros))

    event.listen(bind, "before_cursor_execute", ver)
    try:
        yield vistas
    finally:
        event.remove(bind, "before_cursor_execute", ver)


def _es_foto(sentencia: str) -> bool:
    # La foto del libro (lecturas._FOTO): una sentencia con las cuatro subconsultas por cuenta.
    return "AS imputaciones" in sentencia and "AS anuladas" in sentencia


def _ids(parametros: Any) -> set[UUID]:
    valor = parametros.get("ids") if isinstance(parametros, dict) else None
    assert valor is not None, f"la foto no pide cuentas por id: {parametros!r}"
    return {UUID(str(v)) for v in valor}


def ultima_foto(vistas: list[tuple[str, Any]]) -> set[UUID]:
    fotos = [i for i, (sentencia, _) in enumerate(vistas) if _es_foto(sentencia)]
    assert fotos, "no hubo ninguna foto del libro"
    escrituras = [
        i
        for i, (sentencia, _) in enumerate(vistas)
        if sentencia.lstrip().upper().startswith("INSERT")
    ]
    ultima = fotos[-1]
    assert not escrituras or ultima > escrituras[-1], (
        "la última foto no es posterior a la última escritura"
    )
    return _ids(vistas[ultima][1])


def test_c09_una_sola_lectura_al_publicar_una_emision_nueva(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Una sola lectura al publicar una emisión nueva"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        obls = [obl(mundo, 0, dia(10, 10), "40000.00"), obl(mundo, 1, dia(10, 10), "30000.00")]
        with sentencias(s) as vistas:
            r = emitir(s, mundo, OCT, obls)
        assert ultima_foto(vistas) == set(r.cuentas.values())


def test_c09_una_sola_lectura_al_repetir_una_emision(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Una sola lectura al repetir una emisión"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        obls, eid = (
            [obl(mundo, 0, dia(10, 10), "40000.00"), obl(mundo, 1, dia(10, 10), "30000.00")],
            uuid4(),
        )
        r = emitir(s, mundo, OCT, obls, emision_id=eid)
        with sentencias(s) as vistas:
            emitir(s, mundo, OCT, obls, emision_id=eid)
        assert ultima_foto(vistas) == set(r.cuentas.values())


def _septiembre_de_dos(s: Session, mundo: Mundo) -> tuple[UUID, UUID]:
    r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10)), obl(mundo, 1, dia(9, 10))])
    return r.cuentas[mundo.unidades[0]], r.cuentas[mundo.unidades[1]]


def test_c09_la_lectura_incluye_la_cuenta_que_solo_recibio_interes(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: La lectura incluye la cuenta que sólo recibió interés"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        u1, u2 = _septiembre_de_dos(s, mundo)
        with sentencias(s) as vistas:
            r = emitir(s, mundo, OCT, [obl(mundo, 0, dia(10, 10), "1.00")])
        assert ultima_foto(vistas) == {u1, u2}
        assert {u1, u2} <= set(r.saldo_anterior), "falta el saldo anterior de U2"
        assert r.saldo_anterior[u2] == d("102000.00")


def test_c09_anular_bloquea_tambien_la_cuenta_que_solo_recibio_interes(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Escenario: Anular bloquea también la cuenta que sólo recibió interés"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        u1, u2 = _septiembre_de_dos(s, mundo)
        r = emitir(s, mundo, OCT, [obl(mundo, 0, dia(10, 10), "1.00")])
        llamadas: list[list[UUID]] = []
        real = emisiones.bloquear_cuentas  # type: ignore[attr-defined]

        def espia(sesion: Session, cuentas: Any) -> None:
            llamadas.append(list(cuentas))
            real(sesion, cuentas)

        monkeypatch.setattr(emisiones, "bloquear_cuentas", espia)
        emisiones.anular_emision(
            s, mundo.identidad, emision_id=r.emision_id, motivo="Mal cargada", request_id=uuid4()
        )
        assert [set(c) for c in llamadas] == [{u1, u2}], f"candados pedidos: {llamadas}"


def test_c09_emision_concurrente_con_un_pago_de_otra_unidad(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """La emisión bloquea todas las cuentas de unidad del edificio en un solo pedido: el pago de
    otra unidad espera, termina sin interbloqueo y ve el interés recién registrado."""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, u2 = _septiembre_de_dos(s, mundo)
        s.commit()
    pago: dict[str, Any] = {}

    def pagar_u2() -> None:
        with sesion_app(base_del_edificio, mundo.admin) as otra:
            pago["id"] = pagar(otra, mundo, u2, "500.00", dia(10, 5))
            otra.commit()

    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, OCT, [obl(mundo, 0, dia(10, 10), "1.00")], confirmar=False)
        hilo, resultado = en_hilo(pagar_u2)
        hilo.join(_ESPERA)
        esperaba = hilo.is_alive()
        s.commit()
    hilo.join(60)
    assert not hilo.is_alive(), "el pago quedó colgado"
    assert "error" not in resultado, f"el pago falló: {resultado.get('error')!r}"
    assert esperaba, "el pago de U2 no esperó a la emisión que le registra interés"
    with sesion_app(base_del_edificio, mundo.admin) as s:
        componentes = set(
            s.execute(
                text("SELECT componente FROM imputacion WHERE movimiento_id = :m"),
                {"m": pago["id"]},
            ).scalars()
        )
        assert "interes" in componentes, "el pago no vio el interés de la emisión"


# --- C16 · La anulación espera una corrección en curso --------------------------------------


class _AnulacionEnOtroHilo:
    """Anula en otro hilo y espera `_ESPERA`: si terminó, se confirmó en el medio."""

    def __init__(self, base: BaseDeEdificio, mundo: Mundo, emision_id: UUID) -> None:
        self.error: BaseException | None = None
        self._hilo = threading.Thread(
            target=self._correr, args=(base, mundo, emision_id), daemon=True
        )

    def _correr(self, base: BaseDeEdificio, mundo: Mundo, emision_id: UUID) -> None:
        try:
            with sesion_app(base, mundo.admin) as otra:
                emisiones.anular_emision(
                    otra,
                    mundo.identidad,
                    emision_id=emision_id,
                    motivo="En carrera",
                    request_id=uuid4(),
                )
                otra.commit()
        except BaseException as e:
            self.error = e

    def lanzar(self) -> None:
        self._hilo.start()
        self._hilo.join(_ESPERA)

    def terminar(self) -> None:
        self._hilo.join(60)
        assert not self._hilo.is_alive(), "la anulación quedó colgada"
        assert self.error is None, repr(self.error)


def _anuladas(base: BaseDeEdificio, mundo: Mundo, emision_id: UUID) -> int:
    with sesion_app(base, mundo.admin) as s:
        return int(
            s.execute(
                text(
                    "SELECT count(*) FROM evento_de_emision "
                    "WHERE emision_id = :e AND tipo = 'anulada'"
                ),
                {"e": emision_id},
            ).scalar_one()
        )


def _pausar_en_anulada(
    monkeypatch: pytest.MonkeyPatch, al_volver: Callable[[], None]
) -> list[bool]:
    hecho: list[bool] = []
    real = correcciones._anulada

    def envuelta(*args: Any, **kw: Any) -> Any:
        resultado = real(*args, **kw)
        if not hecho:
            hecho.append(True)
            al_volver()
        return resultado

    monkeypatch.setattr(correcciones, "_anulada", envuelta)
    return hecho


def _credito_de_correccion(s: Session, mundo: Mundo, obligacion: UUID, importe: str) -> UUID:
    return correcciones.corregir(
        s,
        mundo.identidad,
        complejo_id=mundo.complejo,
        pedido=PedidoDeCorreccion(
            "credito", uuid4(), "Cobrado de más", obligacion_id=obligacion, importe=d(importe)
        ),
        request_id=uuid4(),
    )


def _octubre_de_una(base: BaseDeEdificio, mundo: Mundo) -> tuple[UUID, UUID]:
    with sesion_app(base, mundo.admin) as s:
        r = emitir(s, mundo, OCT, [obl(mundo, 4, dia(10, 10), "100.00")])
        o = obligacion_de(s, r.cuentas[mundo.unidades[4]], r.emision_id)
        s.commit()
    return r.emision_id, o


def test_c16_anulacion_durante_un_credito_de_correccion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Escenario: Anulación durante un crédito de corrección"""
    configurar(base_del_edificio, mundo)
    emision, o = _octubre_de_una(base_del_edificio, mundo)
    anulacion = _AnulacionEnOtroHilo(base_del_edificio, mundo, emision)
    hecho = _pausar_en_anulada(monkeypatch, anulacion.lanzar)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _credito_de_correccion(s, mundo, o, "30.00")
        al_escribir = _anuladas(base_del_edificio, mundo, emision)
        s.commit()
    anulacion.terminar()
    assert hecho
    assert al_escribir == 0, "la anulación se confirmó debajo de la corrección"
    assert _anuladas(base_del_edificio, mundo, emision) == 1


def test_c16_anulacion_durante_un_contra_asiento(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Escenario: Anulación durante un contra-asiento"""
    configurar(base_del_edificio, mundo)
    emision, o = _octubre_de_una(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        credito = _credito_de_correccion(s, mundo, o, "30.00")
        s.commit()
    anulacion = _AnulacionEnOtroHilo(base_del_edificio, mundo, emision)
    hecho = _pausar_en_anulada(monkeypatch, anulacion.lanzar)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        contra_asentar(s, mundo, credito, confirmar=False)
        al_escribir = _anuladas(base_del_edificio, mundo, emision)
        s.commit()
    anulacion.terminar()
    assert hecho
    assert al_escribir == 0, "la anulación se confirmó debajo del contra-asiento"
    assert _anuladas(base_del_edificio, mundo, emision) == 1


def test_c16_anulacion_durante_el_contra_asiento_de_un_interes_sin_obligacion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Escenario: Anulación durante el contra-asiento de un interés de una cuenta sin obligación"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, u2 = _septiembre_de_dos(s, mundo)
        r = emitir(s, mundo, OCT, [obl(mundo, 0, dia(10, 10), "1.00")])
        s.commit()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        de_u2 = [i for i in intereses(s, cuenta=u2) if i.emision_id == r.emision_id]
    assert len(de_u2) == 1, "U2 no recibió el interés de septiembre en la emisión de octubre"
    anulacion = _AnulacionEnOtroHilo(base_del_edificio, mundo, r.emision_id)
    hecho = _pausar_en_anulada(monkeypatch, anulacion.lanzar)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        contra_asentar(s, mundo, de_u2[0].id, confirmar=False)
        al_escribir = _anuladas(base_del_edificio, mundo, r.emision_id)
        s.commit()
    anulacion.terminar()
    assert hecho
    assert al_escribir == 0, "la anulación se confirmó debajo del contra-asiento del interés de U2"
    assert _anuladas(base_del_edificio, mundo, r.emision_id) == 1
