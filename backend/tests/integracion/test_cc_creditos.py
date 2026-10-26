"""3.4 · `registrar_credito` contra PostgreSQL real (D5, D6, E16, QA-3, QA-9, QA-10)."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import creditos, emisiones, lecturas
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
)
from proptech_core.cuenta_corriente.dominio.imputacion import Componente, Destino

from ._cuenta_corriente import Mundo, contar_escrituras, sembrar, sesion_app
from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def d(t: str) -> Dinero:
    return Dinero(t)


def emitir(
    s: Session, mundo: Mundo, periodo: date, unidad: int, ordinaria: str, extra: str = "0.00"
) -> UUID:
    r = emisiones.registrar_emision(
        s,
        mundo.identidad,
        emision_id=uuid4(),
        complejo_id=mundo.complejo,
        periodo=periodo,
        obligaciones=[
            ObligacionAEmitir(
                mundo.unidades[unidad], periodo.replace(day=10), d(ordinaria), d("0.00"), d(extra)
            )
        ],
        request_id=uuid4(),
    )
    return r.cuentas[mundo.unidades[unidad]]


def pagar(s: Session, mundo: Mundo, cuenta: UUID, importe: str, **extra: object) -> UUID:
    datos: dict[str, object] = {
        "cuenta_id": cuenta,
        "tipo": "pago",
        "importe": d(importe),
        "fecha_valor": date(2026, 10, 20),
        "operacion_id": uuid4(),
        "destino": None,
        "request_id": uuid4(),
    }
    datos.update(extra)
    return creditos.registrar_credito(s, mundo.identidad, **datos)  # type: ignore[arg-type]


def imputaciones(s: Session, movimiento: UUID) -> list[tuple[str, str]]:
    return [
        (f.componente, f.importe)
        for f in s.execute(
            text(
                "SELECT componente, importe::text AS importe FROM imputacion "
                "WHERE movimiento_id = :m ORDER BY orden"
            ),
            {"m": movimiento},
        )
    ]


def test_ejemplo_de_r04_contra_la_base(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = emitir(s, mundo, date(2026, 8, 1), 0, "80000.00")
        emitir(s, mundo, date(2026, 9, 1), 0, "85000.00")
        pago = pagar(s, mundo, cuenta, "100000.00")
        assert imputaciones(s, pago) == [("ordinaria", "80000.00"), ("ordinaria", "20000.00")]
        assert lecturas.estado_de_cuenta(s, cuenta_id=cuenta).deuda == d("65000.00")


def test_pago_mayor_que_la_deuda(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = emitir(s, mundo, date(2026, 10, 1), 1, "50000.00")
        pagar(s, mundo, cuenta, "60000.00")
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (e.deuda, e.credito_a_favor) == (d("0.00"), d("10000.00"))


def test_dos_creditos_seguidos(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = emitir(s, mundo, date(2026, 10, 1), 2, "10000.00")
        pagar(s, mundo, cuenta, "8000.00")
        pagar(s, mundo, cuenta, "8000.00")
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (e.deuda, e.credito_a_favor) == (d("0.00"), d("6000.00"))


def test_el_mismo_credito_dos_veces(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = emitir(s, mundo, date(2026, 10, 1), 3, "10000.00")
        op = uuid4()
        primero = pagar(s, mundo, cuenta, "4000.00", operacion_id=op)
        n = s.execute(text("SELECT count(*) FROM imputacion")).scalar_one()
        assert pagar(s, mundo, cuenta, "4000.00", operacion_id=op, request_id=uuid4()) == primero
        assert s.execute(text("SELECT count(*) FROM imputacion")).scalar_one() == n


@pytest.mark.parametrize("cambio", ["importe", "cuenta_id", "tipo", "fecha_valor"])
def test_reusar_la_operacion_con_otros_datos(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, cambio: str
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = emitir(s, mundo, date(2026, 10, 1), 4, "10000.00")
        op = uuid4()
        pagar(s, mundo, cuenta, "4000.00", operacion_id=op)
        otros: dict[str, object] = {
            "importe": {},
            "cuenta_id": {"cuenta_id": uuid4()},
            "tipo": {"tipo": "baja_de_deuda"},
            "fecha_valor": {"fecha_valor": date(2026, 10, 21)},
        }[cambio]  # type: ignore[assignment]
        with pytest.raises(Conflicto) as e:
            importe = "4001.00" if cambio == "importe" else "4000.00"
            pagar(s, mundo, cuenta, importe, operacion_id=op, **otros)
        assert e.value.campo == "operacion_id"


@pytest.mark.parametrize("tipo", ["correccion", "saldo_inicial", "inventado"])
def test_tipos_no_admitidos(base_del_edificio: BaseDeEdificio, mundo: Mundo, tipo: str) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = emitir(s, mundo, date(2026, 10, 1), 6, "10.00")
        with pytest.raises(EntradaInvalida) as e:
            pagar(s, mundo, cuenta, "1.00", tipo=tipo)
        assert e.value.campo == "tipo"


@pytest.mark.parametrize("importe", ["0.00", "-1.00"])
def test_importe_no_positivo(base_del_edificio: BaseDeEdificio, mundo: Mundo, importe: str) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = emitir(s, mundo, date(2026, 10, 1), 7, "10.00")
        with pytest.raises(EntradaInvalida) as e:
            pagar(s, mundo, cuenta, importe)
        assert e.value.campo == "importe"


def test_destino_fijo_sin_destino_y_sin_capacidad(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """E16: condonación sin interés: 422 `destino`, nada registrado; diciembre sigue en $40.000."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = emitir(s, mundo, date(2026, 11, 1), 8, "80000.00")
        obligacion = s.execute(
            text("SELECT id FROM obligacion WHERE cuenta_id = :c"), {"c": cuenta}
        ).scalar_one()
        with pytest.raises(EntradaInvalida) as e:
            pagar(s, mundo, cuenta, "4000.00", tipo="condonacion")
        assert e.value.campo == "destino"
        escrituras = contar_escrituras(s)
        with pytest.raises(EntradaInvalida) as e:
            pagar(
                s,
                mundo,
                cuenta,
                "4000.00",
                tipo="condonacion",
                destino=Destino(obligacion, Componente.INTERES),
            )
        assert e.value.campo == "destino"
        assert [x for x in escrituras if "movimiento" in x] == []
        emitir(s, mundo, date(2026, 12, 1), 8, "40000.00")
        e2 = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (e2.deuda, e2.credito_a_favor) == (d("120000.00"), d("0.00"))


@pytest.mark.parametrize("cual", ["inexistente", "ajena"])
def test_cuenta_inexistente_o_ajena(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, cual: str
) -> None:
    with sesion_app(base_del_edificio, mundo.admin_b) as s:
        ajena = emisiones.registrar_emision(
            s,
            mundo.identidad_b,
            emision_id=uuid4(),
            complejo_id=mundo.complejo_b,
            periodo=date(2026, 10, 1),
            obligaciones=[
                ObligacionAEmitir(
                    mundo.unidad_b, date(2026, 10, 10), d("1.00"), d("0.00"), d("0.00")
                )
            ],
            request_id=uuid4(),
        ).cuentas[mundo.unidad_b]
        s.commit()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        escrituras = contar_escrituras(s)
        with pytest.raises(NoEncontrado):
            pagar(s, mundo, uuid4() if cual == "inexistente" else ajena, "1.00")
        assert [x for x in escrituras if "movimiento" in x or "imputacion" in x] == []


def test_replay_no_vuelve_a_imputar_aunque_se_anule_entre_medio(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emisiones.registrar_emision(
            s,
            mundo.identidad,
            emision_id=uuid4(),
            complejo_id=mundo.complejo,
            periodo=date(2026, 10, 1),
            obligaciones=[
                ObligacionAEmitir(
                    mundo.unidades[9], date(2026, 10, 10), d("100.00"), d("0.00"), d("0.00")
                )
            ],
            request_id=uuid4(),
        )
        cuenta = r.cuentas[mundo.unidades[9]]
        op = uuid4()
        pagar(s, mundo, cuenta, "100.00", operacion_id=op)
        emisiones.anular_emision(
            s, mundo.identidad, emision_id=r.emision_id, motivo="Error", request_id=uuid4()
        )
        n = s.execute(text("SELECT count(*) FROM imputacion")).scalar_one()
        assert n >= 1
        pagar(s, mundo, cuenta, "100.00", operacion_id=op)
        assert s.execute(text("SELECT count(*) FROM imputacion")).scalar_one() == n
