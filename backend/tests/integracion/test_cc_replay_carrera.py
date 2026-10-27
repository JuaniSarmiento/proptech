"""El replay bajo carrera (CX-01, E4) y la foto del replay de emisión (CX-02, E12).

Reproducciones del rompedor Codex (`.git/informes-libro-de-movimientos/13-...`), con barreras: dos
llamadas idénticas que vieron ausente el `operacion_id` tienen que devolver el mismo id sin escribir
de más; el replay de una emisión devuelve el saldo anterior de UNA foto, no de dos.
"""

import threading
from collections.abc import Callable
from datetime import UTC, date, datetime
from time import monotonic
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import correcciones, creditos, cuentas, emisiones
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir
from proptech_core.cuenta_corriente.aplicacion.lecturas import fotos
from proptech_core.cuenta_corriente.dominio.imputacion import Componente, Destino

from ._cuenta_corriente import Mundo, en_hilo, sembrar, sesion_app
from ._edificios import BaseDeEdificio
from .test_cc_correcciones import contra, credito_corr, emitir, interes

pytestmark = pytest.mark.integracion
AHORA = datetime(2026, 10, 26, 15, tzinfo=UTC)


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def pagar(
    s: Session,
    mundo: Mundo,
    cuenta: UUID,
    op: UUID,
    tipo: str = "pago",
    destino: Destino | None = None,
    importe: str = "100.00",
) -> UUID:
    return creditos.registrar_credito(
        s,
        mundo.identidad,
        cuenta_id=cuenta,
        tipo=tipo,
        importe=Dinero(importe),
        fecha_valor=date(2026, 10, 20),
        operacion_id=op,
        destino=destino,
        request_id=uuid4(),
        reloj=lambda: AHORA,
    )


def _carrera(
    base: BaseDeEdificio,
    mundo: Mundo,
    modulo: Any,
    monkeypatch: pytest.MonkeyPatch,
    llamada: Callable[[Session], UUID],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Las dos llamadas pasan su primer replay (ausente) y recién ahí siguen, juntas."""
    original = modulo._replay
    barrera = threading.Barrier(2)
    local = threading.local()

    def replay(*a: Any, **kw: Any) -> Any:
        r = original(*a, **kw)
        if not getattr(local, "paso", False):
            local.paso = True
            assert r is None
            barrera.wait(10)
        return r

    monkeypatch.setattr(modulo, "_replay", replay)

    def ejecutar() -> tuple[UUID, dict[str, int]]:
        with sesion_app(base, mundo.admin) as s:
            r = llamada(s)
            filas = _filas_del_libro(s)
            s.commit()
            return r, filas

    h1, r1 = en_hilo(ejecutar)
    h2, r2 = en_hilo(ejecutar)
    h1.join(30)
    h2.join(30)
    assert not h1.is_alive() and not h2.is_alive()
    for resultado in (r1, r2):
        if "valor" in resultado:
            resultado["valor"], resultado["filas"] = resultado["valor"]
    return r1, r2


def _filas_del_libro(s: Session) -> dict[str, int]:
    """Las filas visibles del tenant, para comparar ganador y replay sin depender del ID solo."""
    fila = (
        s.execute(
            text(
                "SELECT (SELECT count(*) FROM cuenta) AS cuenta, "
                "(SELECT count(*) FROM candado_de_cuenta) AS candado, "
                "(SELECT count(*) FROM emision) AS emision, "
                "(SELECT count(*) FROM evento_de_emision) AS evento, "
                "(SELECT count(*) FROM obligacion) AS obligacion, "
                "(SELECT count(*) FROM movimiento) AS movimiento, "
                "(SELECT count(*) FROM imputacion) AS imputacion"
            )
        )
        .mappings()
        .one()
    )
    return {str(nombre): int(cantidad) for nombre, cantidad in fila.items()}


def _imputaciones(s: Session, cuenta: UUID) -> int:
    return int(
        s.execute(
            text("SELECT count(*) FROM imputacion WHERE cuenta_id = :c"), {"c": cuenta}
        ).scalar_one()
    )


@pytest.mark.parametrize("tipo", ["bonificacion", "condonacion", "ajuste_de_interes"])
def test_replay_concurrente_de_un_credito_de_destino_fijo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch, tipo: str
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, obl = emitir(s, mundo, 0, "100.00")
        comp = Componente.ORDINARIA
        if tipo != "bonificacion":
            interes(s, mundo, cuenta, obl, "100.00", date(2026, 10, 15))
            comp = Componente.INTERES
        s.commit()
    op = uuid4()
    r1, r2 = _carrera(
        base_del_edificio,
        mundo,
        creditos,
        monkeypatch,
        lambda s: pagar(s, mundo, cuenta, op, tipo, Destino(obl, comp)),
    )
    assert "error" not in r1 and "error" not in r2, (r1, r2)
    assert r1["valor"] == r2["valor"]
    assert r1["filas"] == r2["filas"]


def test_replay_concurrente_de_un_pago(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, _ = emitir(s, mundo, 0, "100.00")
        s.commit()
    op = uuid4()
    r1, r2 = _carrera(
        base_del_edificio, mundo, creditos, monkeypatch, lambda s: pagar(s, mundo, cuenta, op)
    )
    assert "error" not in r1 and "error" not in r2, (r1, r2)
    assert r1["valor"] == r2["valor"]
    assert r1["filas"] == r2["filas"]
    with sesion_app(base_del_edificio, mundo.admin) as s:
        assert _imputaciones(s, cuenta) == 1


@pytest.mark.parametrize("blanco", ["pago", "interes", "credito_correccion"])
def test_replay_concurrente_de_un_contra_asiento(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch, blanco: str
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, obl = emitir(s, mundo, 0, "100.00")
        if blanco == "pago":
            mov = pagar(s, mundo, cuenta, uuid4())
        elif blanco == "interes":
            mov = interes(s, mundo, cuenta, obl, "100.00", date(2026, 10, 15))
        else:
            mov = credito_corr(s, mundo, obl, "100.00")
        s.commit()
    op = uuid4()
    r1, r2 = _carrera(
        base_del_edificio, mundo, correcciones, monkeypatch, lambda s: contra(s, mundo, mov, op=op)
    )
    assert "error" not in r1 and "error" not in r2, (r1, r2)
    assert r1["valor"] == r2["valor"]
    assert r1["filas"] == r2["filas"]


@pytest.mark.parametrize("forma", ["pago", "credito_correccion"])
def test_el_replay_que_perdio_la_carrera_no_reimputa(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch, forma: str
) -> None:
    """Crédito de $100 a septiembre; al anularlo, su replay no lo pasa a octubre."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        sep, cuenta, obligacion = emitir(s, mundo, 0, "100.00", date(2026, 9, 1))
        emitir(s, mundo, 0, "100.00", date(2026, 10, 1))
        s.commit()
    op = uuid4()
    modulo = creditos if forma == "pago" else correcciones
    original = modulo._replay
    ganador: list[UUID] = []
    filas_del_ganador: list[dict[str, int]] = []
    intercalada: list[bool] = []

    def registrar(s: Session) -> UUID:
        if forma == "pago":
            return pagar(s, mundo, cuenta, op)
        return credito_corr(s, mundo, obligacion, "100.00", op=op)

    def pausa(*a: Any, **kw: Any) -> Any:
        r = original(*a, **kw)
        if not intercalada:  # la marca va antes: la otra sesión también pasa por acá
            intercalada.append(True)
            assert r is None
            with sesion_app(base_del_edificio, mundo.admin) as otra:
                ganador.append(registrar(otra))
                emisiones.anular_emision(
                    otra, mundo.identidad, emision_id=sep, motivo="QA", request_id=uuid4()
                )
                filas_del_ganador.append(_filas_del_libro(otra))
                otra.commit()
        return r

    monkeypatch.setattr(modulo, "_replay", pausa)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        resultado: UUID | Exception
        try:
            resultado = registrar(s)
        except Exception as error:
            resultado = error
        assert resultado == ganador[0], resultado
        assert _filas_del_libro(s) == filas_del_ganador[0]
        assert _imputaciones(s, cuenta) == 1


def test_replay_de_emision_que_otra_registro_mientras_tanto(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    op = uuid4()
    obs = [
        ObligacionAEmitir(
            mundo.unidades[0], date(2026, 10, 10), Dinero("100.00"), Dinero("0.00"), Dinero("0.00")
        )
    ]

    def registrar(s: Session) -> emisiones.EmisionRegistrada:
        return emisiones.registrar_emision(
            s,
            mundo.identidad,
            emision_id=op,
            complejo_id=mundo.complejo,
            periodo=date(2026, 10, 1),
            obligaciones=obs,
            request_id=uuid4(),
        )

    original = emisiones._replay
    ganador: list[emisiones.EmisionRegistrada] = []
    filas_del_ganador: list[dict[str, int]] = []
    intercalada: list[bool] = []

    def pausa(*a: Any, **kw: Any) -> Any:
        r = original(*a, **kw)
        if not intercalada:  # la marca va antes: la otra sesión también pasa por acá
            intercalada.append(True)
            assert r is None
            with sesion_app(base_del_edificio, mundo.admin) as otra:
                ganador.append(registrar(otra))
                filas_del_ganador.append(_filas_del_libro(otra))
                otra.commit()
        return r

    monkeypatch.setattr(emisiones, "_replay", pausa)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        resultado: emisiones.EmisionRegistrada | Exception
        try:
            resultado = registrar(s)
        except Exception as error:
            resultado = error
        assert isinstance(resultado, emisiones.EmisionRegistrada), resultado
        assert _filas_del_libro(s) == filas_del_ganador[0]
    assert resultado.emision_id == ganador[0].emision_id
    assert resultado.intento == ganador[0].intento


def test_el_replay_de_emision_devuelve_una_sola_foto(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Saldo anterior A=$0/B=$100 antes y A=$100/B=$0 después de una transacción atómica: el replay
    devuelve una de las dos fotos (suma $100), nunca la mezcla A=$0/B=$0."""
    sep = [
        ObligacionAEmitir(u, date(2026, 9, 10), Dinero("100.00"), Dinero("0.00"), Dinero("0.00"))
        for u in mundo.unidades[:2]
    ]
    em_oct = uuid4()
    oct_ = [
        ObligacionAEmitir(u, date(2026, 10, 10), Dinero("1.00"), Dinero("0.00"), Dinero("0.00"))
        for u in mundo.unidades[:2]
    ]

    def registrar(s: Session, emision_id: UUID, periodo: date, obs: list[ObligacionAEmitir]) -> Any:
        return emisiones.registrar_emision(
            s,
            mundo.identidad,
            emision_id=emision_id,
            complejo_id=mundo.complejo,
            periodo=periodo,
            obligaciones=obs,
            request_id=uuid4(),
        )

    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = registrar(s, uuid4(), date(2026, 9, 1), sep)
        a, b = sorted(r.cuentas.values())
        pago = pagar(s, mundo, a, uuid4())
        r_oct = registrar(s, em_oct, date(2026, 10, 1), oct_)
        assert r_oct.saldo_anterior == {a: Dinero("0.00"), b: Dinero("100.00")}
        s.commit()

    # Después de la primera lectura, el escritor debe esperar al replay que tomó ambos candados.
    # Sin candados puede confirmar antes de la siguiente lectura: se observa ese resultado también,
    # para que el mutante falle en una aserción y no esperando una barrera que nunca podrá cruzar.
    intercalada: list[bool] = []
    iniciada = threading.Event()
    terminada = threading.Event()
    pid_escritor: list[int] = []
    espera_observada: list[bool] = []
    hilos: list[tuple[threading.Thread, dict[str, Any]]] = []

    def escribir() -> None:
        try:
            with sesion_app(base_del_edificio, mundo.admin) as otra:
                pid_escritor.append(int(otra.execute(text("SELECT pg_backend_pid()")).scalar_one()))
                iniciada.set()
                cuentas.bloquear_cuentas(otra, [a, b])
                contra(otra, mundo, pago)
                pagar(otra, mundo, b, uuid4())
                otra.commit()
        finally:
            terminada.set()

    def despues_de_leer(real: Callable[..., Any]) -> Callable[..., Any]:
        def envuelta(*args: Any, **kw: Any) -> Any:
            resultado = real(*args, **kw)
            if not intercalada:
                intercalada.append(True)
                lectora = args[0]
                pid_lectora = int(lectora.execute(text("SELECT pg_backend_pid()")).scalar_one())
                hilos.append(en_hilo(escribir))
                assert iniciada.wait(10)
                limite = monotonic() + 10
                bloqueada = False
                # conectar_app usa autocommit: cada consulta ve el estado actual de los locks.
                with base_del_edificio.conectar_app() as observadora:
                    while not terminada.is_set() and monotonic() < limite:
                        fila = observadora.execute(
                            "SELECT pg_blocking_pids(%s)", (pid_escritor[0],)
                        ).fetchone()
                        assert fila is not None
                        if pid_lectora in fila[0]:
                            bloqueada = True
                            break
                assert bloqueada or terminada.is_set(), "El escritor no esperó ni terminó"
                espera_observada.append(bloqueada)
            return resultado

        return envuelta

    for nombre in ("foto", "fotos"):
        if hasattr(emisiones, nombre):
            monkeypatch.setattr(emisiones, nombre, despues_de_leer(getattr(emisiones, nombre)))
    try:
        with sesion_app(base_del_edificio, mundo.admin) as s:
            replay = registrar(s, em_oct, date(2026, 10, 1), oct_)
            s.commit()  # libera ambos candados antes de esperar la confirmación del escritor
    finally:
        for hilo, _ in hilos:
            hilo.join(30)
    assert intercalada
    assert len(hilos) == 1
    hilo, resultado_escritor = hilos[0]
    assert not hilo.is_alive()
    assert "error" not in resultado_escritor, resultado_escritor
    with sesion_app(base_del_edificio, mundo.admin) as s:
        despues = {c: f.estado.deuda_sin_emision(em_oct) for c, f in fotos(s, [a, b]).items()}
    assert despues == {a: Dinero("100.00"), b: Dinero("0.00")}
    assert replay.saldo_anterior in (
        {a: Dinero("0.00"), b: Dinero("100.00")},
        {a: Dinero("100.00"), b: Dinero("0.00")},
    ), replay.saldo_anterior
    assert espera_observada == [True], "El replay leyó sin bloquear todas sus cuentas"
