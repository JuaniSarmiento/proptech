"""H-031 · `trasladar_deuda` contra PostgreSQL real (4d, R32, D-168.2): lo impago de los períodos
anteriores al mes del cambio pasa de la cuenta de la unidad a la cuenta de persona del vendedor, con
`traslado` enlazados, en la transacción del llamador."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import (
    creditos,
    cuentas,
    emisiones,
    lecturas,
    traslado_de_deuda,
)
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir
from proptech_core.cuenta_corriente.aplicacion.traslado_de_deuda import trasladar_deuda

from ._cuenta_corriente import Mundo, sembrar, sesion_app
from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion

SEP, OCT, NOV = date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    """Con una tasa del 3 % mensual: lo impago de septiembre y octubre trae interés registrado."""
    mundo = sembrar(base_del_edificio)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        s.execute(
            text(
                "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, "
                "vigente_desde, tasa_mensual, umbral_saldo_chico, dias_de_gracia, "
                "forma_de_calculo, porcentaje_fondo, dia_de_vencimiento, "
                "modalidad_de_vencimiento) VALUES (:adm, :c, :autor, '2026-01-01', '3.00', "
                "'500.00', 0, 'proporcional_por_dia', '0.00', 10, 'unico')"
            ),
            {"adm": mundo.admin, "c": mundo.complejo, "autor": mundo.persona},
        )
        s.commit()
    return mundo


def _emitir(
    s: Session, mundo: Mundo, unidades: tuple[int, ...], periodo: date, ordinaria: str
) -> None:
    emisiones.registrar_emision(
        s,
        mundo.identidad,
        emision_id=uuid4(),
        complejo_id=mundo.complejo,
        periodo=periodo,
        obligaciones=[
            ObligacionAEmitir(
                mundo.unidades[u],
                periodo.replace(day=10),
                Dinero(ordinaria),
                Dinero("1.00"),
                Dinero("0.00"),
            )
            for u in unidades
        ],
        request_id=uuid4(),
    )


def _con_deuda(base: BaseDeEdificio, mundo: Mundo, unidades: tuple[int, ...] = (0,)) -> UUID:
    """Septiembre, octubre y noviembre emitidos y sin pagar, con el interés registrado. Devuelve la
    cuenta de la primera unidad."""
    with sesion_app(base, mundo.admin) as s:
        for periodo in (SEP, OCT, NOV):
            _emitir(s, mundo, unidades, periodo, "10000.00")
        s.commit()
    return _cuenta(base, mundo, unidades[0])


def _cuenta(base: BaseDeEdificio, mundo: Mundo, unidad: int) -> UUID:
    with sesion_app(base, mundo.admin) as s:
        return UUID(
            str(
                s.execute(
                    text("SELECT id FROM cuenta WHERE unidad_id = :u"),
                    {"u": mundo.unidades[unidad]},
                ).scalar_one()
            )
        )


def _trasladar(
    base: BaseDeEdificio, mundo: Mundo, unidad: int = 0, fecha: date = date(2026, 11, 10)
) -> traslado_de_deuda.TrasladoDeDeuda:
    with sesion_app(base, mundo.admin) as s:
        resultado = trasladar_deuda(
            s,
            mundo.identidad,
            cambio_id=uuid4(),
            unidad_id=mundo.unidades[unidad],
            persona_id=mundo.persona,
            fecha=fecha,
            request_id=uuid4(),
        )
        s.commit()
    return resultado


def _estado(base: BaseDeEdificio, mundo: Mundo, cuenta: UUID) -> object:
    with sesion_app(base, mundo.admin) as s:
        return lecturas.estado_de_cuenta(s, cuenta_id=cuenta)


def _residual_anterior(base: BaseDeEdificio, mundo: Mundo, cuenta: UUID, corte: date) -> Decimal:
    e = _estado(base, mundo, cuenta)
    por_id = {o.id: o for o in e.obligaciones}  # type: ignore[attr-defined]
    return sum(
        (
            Decimal(r.a_texto())
            for (o, _), r in e.residual.items()  # type: ignore[attr-defined]
            if por_id[o].periodo < corte
        ),
        Decimal("0.00"),
    )


def _deuda(base: BaseDeEdificio, mundo: Mundo, cuenta: UUID) -> Decimal:
    return Decimal(_estado(base, mundo, cuenta).deuda.a_texto())  # type: ignore[attr-defined]


def _traslados(base: BaseDeEdificio, mundo: Mundo) -> list[dict[str, object]]:
    with sesion_app(base, mundo.admin) as s:
        filas = s.execute(
            text(
                "SELECT id, cuenta_id, sentido, importe::text AS importe, obligacion_id, "
                "componente, enlazado_a, operacion_id FROM movimiento WHERE tipo = 'traslado' "
                "ORDER BY registrado_en, id"
            )
        ).mappings()
        return [dict(f) for f in filas]


def test_lo_impago_anterior_al_mes_pasa_entero_a_la_cuenta_de_la_persona(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    unidad = _con_deuda(base_del_edificio, mundo)
    antes = _deuda(base_del_edificio, mundo, unidad)
    previo = _residual_anterior(base_del_edificio, mundo, unidad, NOV)
    assert previo > Decimal("20000.00"), "precondición: capital e interés de septiembre y octubre"
    resultado = _trasladar(base_del_edificio, mundo)
    assert resultado.cuenta_destino is not None
    assert resultado.trasladado.a_texto() == format(previo, ".2f"), resultado
    assert _residual_anterior(base_del_edificio, mundo, unidad, NOV) == 0
    assert _deuda(base_del_edificio, mundo, resultado.cuenta_destino) == previo
    despues = _deuda(base_del_edificio, mundo, unidad)
    assert despues == antes - previo, "lo de noviembre queda en la unidad"
    assert despues + previo == antes, "la suma de las dos cuentas no cambia"


def test_cada_componente_tiene_su_credito_en_la_unidad_y_su_debito_enlazado(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    unidad = _con_deuda(base_del_edificio, mundo)
    resultado = _trasladar(base_del_edificio, mundo)
    filas = _traslados(base_del_edificio, mundo)
    creditos_ = [f for f in filas if f["sentido"] == "credito"]
    debitos = [f for f in filas if f["sentido"] == "debito"]
    assert creditos_ and len(creditos_) == len(debitos)
    assert {f["cuenta_id"] for f in creditos_} == {unidad}
    assert {f["cuenta_id"] for f in debitos} == {resultado.cuenta_destino}
    assert {f["componente"] for f in creditos_} >= {"ordinaria", "fondo_de_reserva", "interes"}
    for c in creditos_:
        pares = [d for d in debitos if d["enlazado_a"] == c["id"]]
        assert len(pares) == 1, f"un solo débito enlazado por crédito: {c}"
        assert pares[0]["importe"] == c["importe"] and pares[0]["componente"] == c["componente"]
    assert all(f["operacion_id"] is not None for f in filas)
    assert len({f["operacion_id"] for f in filas}) == len(filas), "uno distinto por movimiento"


def test_la_cuenta_de_persona_se_reutiliza(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    _con_deuda(base_del_edificio, mundo, (0, 1))
    uno = _trasladar(base_del_edificio, mundo, 0)
    antes = _deuda(base_del_edificio, mundo, uno.cuenta_destino)  # type: ignore[arg-type]
    dos = _trasladar(base_del_edificio, mundo, 1)
    assert dos.cuenta_destino == uno.cuenta_destino
    assert _deuda(base_del_edificio, mundo, uno.cuenta_destino) == antes + Decimal(  # type: ignore[arg-type]
        dos.trasladado.a_texto()
    )
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cantidad = s.execute(
            text("SELECT count(*) FROM cuenta WHERE persona_id = :p"), {"p": mundo.persona}
        ).scalar_one()
    assert cantidad == 1


def test_sin_nada_que_trasladar_no_escribe_ni_crea_la_cuenta(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:  # sólo noviembre: nada anterior
        _emitir(s, mundo, (2,), NOV, "10000.00")
        s.commit()
    resultado = _trasladar(base_del_edificio, mundo, 2)
    assert resultado.trasladado.a_texto() == "0.00" and resultado.cuenta_destino is None
    assert _traslados(base_del_edificio, mundo) == []
    with sesion_app(base_del_edificio, mundo.admin) as s:
        assert (
            s.execute(
                text("SELECT count(*) FROM cuenta WHERE persona_id = :p"), {"p": mundo.persona}
            ).scalar_one()
            == 0
        )
    # y una unidad sin cuenta tampoco falla
    assert _trasladar(base_del_edificio, mundo, 3).cuenta_destino is None


def test_lo_ya_trasladado_no_se_traslada_de_nuevo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    _con_deuda(base_del_edificio, mundo)
    primero = _trasladar(base_del_edificio, mundo)
    movimientos = len(_traslados(base_del_edificio, mundo))
    segundo = _trasladar(base_del_edificio, mundo, fecha=date(2026, 11, 20))
    assert primero.trasladado.a_texto() != "0.00"
    assert segundo.trasladado.a_texto() == "0.00" and segundo.cuenta_destino is None
    assert len(_traslados(base_del_edificio, mundo)) == movimientos


def test_toma_el_candado_de_las_dos_cuentas_en_una_llamada(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    unidad = _con_deuda(base_del_edificio, mundo)
    llamadas: list[list[UUID]] = []
    original = cuentas.bloquear_cuentas

    def espia(sesion: Session, ids: list[UUID]) -> None:
        llamadas.append(list(ids))
        original(sesion, ids)

    monkeypatch.setattr(f"{traslado_de_deuda.__name__}.bloquear_cuentas", espia)
    resultado = _trasladar(base_del_edificio, mundo)
    assert llamadas == [[unidad, resultado.cuenta_destino]] or llamadas == [
        [resultado.cuenta_destino, unidad]
    ], llamadas


def test_una_falla_a_mitad_de_camino_no_deja_nada(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    unidad = _con_deuda(base_del_edificio, mundo)
    antes = _deuda(base_del_edificio, mundo, unidad)
    llamadas = {"n": 0}
    original = creditos.insertar_imputaciones

    def falla_en_la_tercera(*args: object, **kwargs: object) -> None:
        llamadas["n"] += 1
        if llamadas["n"] == 3:
            raise RuntimeError("falla inyectada")
        original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(f"{traslado_de_deuda.__name__}.insertar_imputaciones", falla_en_la_tercera)
    with sesion_app(base_del_edificio, mundo.admin) as s, pytest.raises(RuntimeError):
        trasladar_deuda(
            s,
            mundo.identidad,
            cambio_id=uuid4(),
            unidad_id=mundo.unidades[0],
            persona_id=mundo.persona,
            fecha=date(2026, 11, 10),
            request_id=uuid4(),
        )
    assert llamadas["n"] == 3, "la falla llegó a la tercera imputación"
    assert _traslados(base_del_edificio, mundo) == []
    assert _deuda(base_del_edificio, mundo, unidad) == antes
    with sesion_app(base_del_edificio, mundo.admin) as s:
        assert (
            s.execute(
                text("SELECT count(*) FROM cuenta WHERE persona_id = :p"), {"p": mundo.persona}
            ).scalar_one()
            == 0
        )


def test_un_pago_posterior_no_toca_lo_trasladado(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    unidad = _con_deuda(base_del_edificio, mundo)
    resultado = _trasladar(base_del_edificio, mundo)
    trasladada = _deuda(base_del_edificio, mundo, resultado.cuenta_destino)  # type: ignore[arg-type]
    with sesion_app(base_del_edificio, mundo.admin) as s:
        creditos.registrar_credito(
            s,
            mundo.identidad,
            cuenta_id=unidad,
            tipo="pago",
            importe=Dinero("999999.00"),
            fecha_valor=date(2026, 11, 25),
            operacion_id=uuid4(),
            destino=None,
            request_id=uuid4(),
        )
        s.commit()
    assert _deuda(base_del_edificio, mundo, resultado.cuenta_destino) == trasladada  # type: ignore[arg-type]
    assert _deuda(base_del_edificio, mundo, unidad) == 0
