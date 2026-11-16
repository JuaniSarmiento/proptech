"""7, H-014: el cargo cobrado de menos (E11) y el evento `distribuida` (E9) en el libro, contra
PostgreSQL real. La aceptación lo prueba por la API; acá, lo que ella no recorre: el replay por
`operacion_id`, el origen ajeno, un rechazo que no escribe y la distribución sobre una anulada."""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import emisiones
from proptech_core.cuenta_corriente.aplicacion.cargos_de_menos import (
    CargoRegistrado,
    registrar_cargo_cobrado_de_menos,
)
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
)

from ._cuenta_corriente import Mundo, sembrar, sesion_app
from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion

MOTIVO = "Faltó cobrar la reparación del portón"


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def _reloj(dia: date) -> object:
    return lambda: datetime(dia.year, dia.month, dia.day, 15, tzinfo=UTC)


def _emitir(s: Session, mundo: Mundo, unidad: int) -> tuple[UUID, UUID]:
    """Una emisión de octubre para la unidad; devuelve la emisión y su obligación."""
    periodo = date(2026, 10, 1)
    r = emisiones.registrar_emision(
        s,
        mundo.identidad,
        emision_id=uuid4(),
        complejo_id=mundo.complejo,
        periodo=periodo,
        obligaciones=[
            ObligacionAEmitir(
                mundo.unidades[unidad],
                date(2026, 10, 10),
                Dinero("1000.00"),
                Dinero("0.00"),
                Dinero("0.00"),
            )
        ],
        request_id=uuid4(),
    )
    obligacion = s.execute(
        text("SELECT id FROM obligacion WHERE emision_id = :e AND cuenta_id = :c"),
        {"e": r.emision_id, "c": r.cuentas[mundo.unidades[unidad]]},
    ).scalar_one()
    return r.emision_id, UUID(str(obligacion))


def _cargo(
    s: Session,
    mundo: Mundo,
    origen: UUID,
    *,
    unidad: int = 0,
    importe: str = "1500.00",
    componente: str = "ordinaria",
    motivo: str = MOTIVO,
    operacion_id: UUID | None = None,
    dia: date = date(2026, 11, 20),
) -> CargoRegistrado:
    return registrar_cargo_cobrado_de_menos(
        s,
        mundo.identidad,
        complejo_id=mundo.complejo,
        unidad_id=mundo.unidades[unidad],
        obligacion_origen_id=origen,
        operacion_id=operacion_id or uuid4(),
        importe=Dinero(importe),
        componente=componente,
        motivo=motivo,
        request_id=uuid4(),
        reloj=_reloj(dia),  # type: ignore[arg-type]
    )


def _filas(s: Session) -> tuple[int, int]:
    obligaciones = s.execute(text("SELECT count(*) FROM obligacion")).scalar_one()
    cargos = s.execute(text("SELECT count(*) FROM cargo_cobrado_de_menos")).scalar_one()
    return int(obligaciones), int(cargos)


def test_el_cargo_es_una_obligacion_nueva_del_periodo_de_origen(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, origen = _emitir(s, mundo, 0)
        r = _cargo(s, mundo, origen, componente="fondo_de_reserva")
        s.commit()
        fila = s.execute(
            text(
                "SELECT periodo, vencimiento, emision_id, ordinaria::text, "
                "fondo_de_reserva::text, extraordinaria::text FROM obligacion WHERE id = :o"
            ),
            {"o": r.obligacion_id},
        ).one()
        assert tuple(fila) == (
            date(2026, 10, 1),
            date(2026, 11, 20),
            None,
            "0.00",
            "1500.00",
            "0.00",
        )
        vinculo = s.execute(
            text(
                "SELECT obligacion_origen_id, obligacion_id, motivo FROM cargo_cobrado_de_menos "
                "WHERE id = :c"
            ),
            {"c": r.cargo_id},
        ).one()
        assert tuple(vinculo) == (origen, r.obligacion_id, MOTIVO)
        assert (r.repetido, r.componente, r.vencimiento) == (
            False,
            "fondo_de_reserva",
            date(2026, 11, 20),
        )


def test_el_vencimiento_es_el_dia_de_mendoza(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    """Las 02:00 UTC del 21/11 son las 23:00 del 20/11 en Mendoza (UTC-3)."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, origen = _emitir(s, mundo, 0)
        r = registrar_cargo_cobrado_de_menos(
            s,
            mundo.identidad,
            complejo_id=mundo.complejo,
            unidad_id=mundo.unidades[0],
            obligacion_origen_id=origen,
            operacion_id=uuid4(),
            importe=Dinero("10.00"),
            componente="ordinaria",
            motivo=MOTIVO,
            request_id=uuid4(),
            reloj=lambda: datetime(2026, 11, 21, 2, tzinfo=UTC),
        )
        assert r.vencimiento == date(2026, 11, 20)


def test_el_mismo_operacion_id_con_los_mismos_datos_es_un_replay(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, origen = _emitir(s, mundo, 0)
        operacion = uuid4()
        primero = _cargo(s, mundo, origen, operacion_id=operacion)
        s.commit()
        antes = _filas(s)
        otra_vez = _cargo(s, mundo, origen, operacion_id=operacion, dia=date(2026, 11, 25))
        assert otra_vez.repetido is True
        assert (otra_vez.cargo_id, otra_vez.obligacion_id) == (
            primero.cargo_id,
            primero.obligacion_id,
        )
        assert otra_vez.vencimiento == date(2026, 11, 20), "lo ya registrado, no el día del replay"
        assert _filas(s) == antes


@pytest.mark.parametrize(
    "cambio", [{"importe": "1600.00"}, {"componente": "extraordinaria"}, {"motivo": "Otro motivo"}]
)
def test_el_mismo_operacion_id_con_otros_datos_es_un_conflicto(
    mundo: Mundo, base_del_edificio: BaseDeEdificio, cambio: dict[str, Any]
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, origen = _emitir(s, mundo, 0)
        operacion = uuid4()
        _cargo(s, mundo, origen, operacion_id=operacion)
        s.commit()
        antes = _filas(s)
        with pytest.raises(Conflicto) as error:
            _cargo(s, mundo, origen, operacion_id=operacion, **cambio)
        assert error.value.campo == "operacion_id"
        assert _filas(s) == antes


def test_un_origen_de_otra_unidad_o_inexistente_es_404_y_no_escribe(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, origen_de_la_primera = _emitir(s, mundo, 0)
        s.commit()
        antes = _filas(s)
        with pytest.raises(NoEncontrado):
            _cargo(s, mundo, origen_de_la_primera, unidad=1)
        with pytest.raises(NoEncontrado):
            _cargo(s, mundo, uuid4())
        assert _filas(s) == antes


@pytest.mark.parametrize(
    "cambio",
    [{"importe": "0.00"}, {"importe": "-5.00"}, {"componente": "interes"}, {"motivo": "  "}],
)
def test_un_pedido_invalido_es_422_y_no_escribe(
    mundo: Mundo, base_del_edificio: BaseDeEdificio, cambio: dict[str, Any]
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, origen = _emitir(s, mundo, 0)
        s.commit()
        antes = _filas(s)
        with pytest.raises(EntradaInvalida):
            _cargo(s, mundo, origen, **cambio)
        assert _filas(s) == antes


def test_distribuir_es_idempotente_y_gana_el_primero(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emision, _ = _emitir(s, mundo, 0)
        r = [
            emisiones.distribuir_emision(
                s, emision_id=emision, origen=origen, persona_id=None, request_id=uuid4()
            )
            for origen in ("portal", "email")
        ]
        s.commit()
        assert r == [True, False]
        filas = s.execute(
            text("SELECT tipo, origen, motivo FROM evento_de_emision WHERE emision_id = :e"),
            {"e": emision},
        ).all()
        assert [tuple(f) for f in filas] == [("distribuida", "portal", None)]


def test_no_se_distribuye_una_anulada_ni_un_origen_raro(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emision, _ = _emitir(s, mundo, 0)
        with pytest.raises(EntradaInvalida):
            emisiones.distribuir_emision(
                s, emision_id=emision, origen="telepatia", persona_id=None, request_id=uuid4()
            )
        with pytest.raises(EntradaInvalida):
            emisiones.distribuir_emision(
                s, emision_id=emision, origen="manual", persona_id=None, request_id=uuid4()
            )
        emisiones.anular_emision(
            s, mundo.identidad, emision_id=emision, motivo="x", request_id=uuid4()
        )
        with pytest.raises(Conflicto):
            emisiones.distribuir_emision(
                s, emision_id=emision, origen="portal", persona_id=None, request_id=uuid4()
            )
        with pytest.raises(NoEncontrado):
            emisiones.distribuir_emision(
                s, emision_id=uuid4(), origen="portal", persona_id=None, request_id=uuid4()
            )
