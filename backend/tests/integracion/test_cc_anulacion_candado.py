"""RF-01, RF-02, RF-04 · La anulación toma los candados de las cuentas de su emisión (D2, D4, E12).

Una anulación que se confirma en medio de otra escritura de la misma cuenta no puede quedar a
mitad de una foto (E12) ni por debajo de un chequeo "bajo candado" (E6, R08). La anulación corre
en otro hilo y otra conexión: con el candado espera a que la escritura termine; sin él, se
confirma en el medio y el test lo ve en su aserción.
"""

import threading
from collections.abc import Callable
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import correcciones, emisiones
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

from ._cuenta_corriente import Mundo, sembrar, sesion_app
from ._edificios import BaseDeEdificio
from .test_cc_correcciones import credito_corr, emitir

pytestmark = pytest.mark.integracion

#: Lo que se le da a la anulación para confirmarse si nadie la frena (sin candado tarda ms).
_ESPERA = 2.0


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


class _AnulacionEnOtroHilo:
    """Anula en otro hilo y espera `_ESPERA`: si terminó, se confirmó en el medio."""

    def __init__(self, base: BaseDeEdificio, mundo: Mundo, emision_id: UUID) -> None:
        self.error: BaseException | None = None
        self._hilo = threading.Thread(target=self._correr, args=(base, mundo, emision_id))
        self._hilo.daemon = True

    def _correr(self, base: BaseDeEdificio, mundo: Mundo, emision_id: UUID) -> None:
        try:
            with sesion_app(base, mundo.admin) as otra:
                emisiones.anular_emision(
                    otra,
                    mundo.identidad,
                    emision_id=emision_id,
                    motivo="Anulación en carrera",
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
                    "SELECT count(*) FROM evento_de_emision WHERE emision_id = :e "
                    "AND tipo = 'anulada'"
                ),
                {"e": emision_id},
            ).scalar_one()
        )


def _tras_la_primera_llamada(
    real: Callable[..., Any], al_volver: Callable[[], None], hecho: list[bool]
) -> Callable[..., Any]:
    def envuelta(*args: Any, **kw: Any) -> Any:
        resultado = real(*args, **kw)
        if not hecho:
            hecho.append(True)
            al_volver()
        return resultado

    return envuelta


def _setiembre_y_octubre(mundo: Mundo) -> tuple[list[ObligacionAEmitir], list[ObligacionAEmitir]]:
    sep = [
        ObligacionAEmitir(u, date(2026, 9, 10), Dinero("100.00"), Dinero("0.00"), Dinero("0.00"))
        for u in mundo.unidades[:2]
    ]
    oct_ = [
        ObligacionAEmitir(u, date(2026, 10, 10), Dinero("1.00"), Dinero("0.00"), Dinero("0.00"))
        for u in mundo.unidades[:2]
    ]
    return sep, oct_


def _registrar(
    s: Any, mundo: Mundo, emision_id: UUID, periodo: date, obligaciones: list[ObligacionAEmitir]
) -> emisiones.EmisionRegistrada:
    return emisiones.registrar_emision(
        s,
        mundo.identidad,
        emision_id=emision_id,
        complejo_id=mundo.complejo,
        periodo=periodo,
        obligaciones=obligaciones,
        request_id=uuid4(),
    )


def test_rf01_la_emision_nueva_publica_una_sola_foto(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-01, E12: la anulación de setiembre no se mete entre las lecturas del saldo de octubre."""
    sep, oct_ = _setiembre_y_octubre(mundo)
    sep_id, oct_id = uuid4(), uuid4()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _registrar(s, mundo, sep_id, date(2026, 9, 1), sep)
        s.commit()
    anulacion = _AnulacionEnOtroHilo(base_del_edificio, mundo, sep_id)
    hecho: list[bool] = []
    for nombre in ("foto", "fotos"):
        if not hasattr(emisiones, nombre):  # la foto por cuenta ya no existe en emisiones
            continue
        monkeypatch.setattr(
            emisiones,
            nombre,
            _tras_la_primera_llamada(getattr(emisiones, nombre), anulacion.lanzar, hecho),
        )
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = _registrar(s, mundo, oct_id, date(2026, 10, 1), oct_)
        s.commit()
    anulacion.terminar()
    assert hecho
    a, b = sorted(r.cuentas.values())
    assert r.saldo_anterior in (
        {a: Dinero("100.00"), b: Dinero("100.00")},
        {a: Dinero("0.00"), b: Dinero("0.00")},
    ), r.saldo_anterior


def test_rf04_el_replay_de_emision_publica_una_sola_foto(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-04, CX-02: el mismo intercalado en el replay."""
    sep, oct_ = _setiembre_y_octubre(mundo)
    sep_id, oct_id = uuid4(), uuid4()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _registrar(s, mundo, sep_id, date(2026, 9, 1), sep)
        primera = _registrar(s, mundo, oct_id, date(2026, 10, 1), oct_)
        s.commit()
    a, b = sorted(primera.cuentas.values())
    anulacion = _AnulacionEnOtroHilo(base_del_edificio, mundo, sep_id)
    hecho: list[bool] = []
    for nombre in ("foto", "fotos"):
        if not hasattr(emisiones, nombre):  # la foto por cuenta ya no existe en emisiones
            continue
        monkeypatch.setattr(
            emisiones,
            nombre,
            _tras_la_primera_llamada(getattr(emisiones, nombre), anulacion.lanzar, hecho),
        )
    with sesion_app(base_del_edificio, mundo.admin) as s:
        replay = _registrar(s, mundo, oct_id, date(2026, 10, 1), oct_)
        s.commit()
    anulacion.terminar()
    assert hecho
    assert replay.saldo_anterior in (
        {a: Dinero("100.00"), b: Dinero("100.00")},
        {a: Dinero("0.00"), b: Dinero("0.00")},
    ), replay.saldo_anterior


def test_rf02_la_anulacion_no_se_confirma_bajo_una_correccion_en_curso(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-02, E6, R08: el chequeo `_anulada` corre bajo el candado; la anulación lo respeta.

    Con el candado, la anulación espera a que la corrección se confirme (orden serial válido:
    corrección y después anulación). Sin él, la anulación se confirma después del chequeo y antes
    de la escritura: la corrección queda escrita sobre una emisión que ya estaba anulada.
    """
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emision, _, obl = emitir(s, mundo, 4, "100.00")
        s.commit()
    anulacion = _AnulacionEnOtroHilo(base_del_edificio, mundo, emision)
    hecho: list[bool] = []
    monkeypatch.setattr(
        correcciones,
        "_anulada",
        _tras_la_primera_llamada(correcciones._anulada, anulacion.lanzar, hecho),
    )
    with sesion_app(base_del_edificio, mundo.admin) as s:
        credito_corr(s, mundo, obl, "30.00")
        anuladas_al_escribir = _anuladas(base_del_edificio, mundo, emision)
        s.commit()
    anulacion.terminar()
    assert hecho
    assert anuladas_al_escribir == 0, "la anulación se confirmó debajo de la corrección"
    assert _anuladas(base_del_edificio, mundo, emision) == 1
