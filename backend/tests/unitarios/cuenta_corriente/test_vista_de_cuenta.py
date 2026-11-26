"""El detalle de una cuenta de persona (4d, H-033): por período y componente, y los movimientos
en el orden del libro. Puro, sin base."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.estado import (
    ImputacionRegistrada,
    Movimiento,
    Obligacion,
    calcular_estado,
)
from proptech_core.cuenta_corriente.dominio.imputacion import Componente
from proptech_core.cuenta_corriente.dominio.vista_de_cuenta import (
    movimientos_en_orden,
    periodos_de,
)

CERO = Dinero("0.00")
SEP, OCT = date(2026, 9, 1), date(2026, 10, 1)


def _contenedora(periodo: date) -> Obligacion:
    return Obligacion(uuid4(), None, periodo, periodo.replace(day=10), CERO, CERO, CERO)


def _debito(
    obligacion: Obligacion, componente: Componente, importe: str, minuto: int = 0
) -> Movimiento:
    return Movimiento(
        uuid4(),
        "traslado",
        "debito",
        Dinero(importe),
        obligacion.vencimiento,
        datetime(2026, 11, 10, 12, minuto, tzinfo=UTC),
        obligacion.id,
        componente,
    )


def _cobro(importe: str, minuto: int) -> Movimiento:
    return Movimiento(
        uuid4(),
        "pago",
        "credito",
        Dinero(importe),
        date(2026, 12, 5),
        datetime(2026, 12, 5, 12, minuto, tzinfo=UTC),
    )


def test_junta_por_periodo_y_componente_aunque_haya_dos_contenedoras_del_mismo_periodo() -> None:
    a, b, c = _contenedora(SEP), _contenedora(SEP), _contenedora(OCT)
    movimientos = [
        _debito(a, Componente.ORDINARIA, "100.00"),
        _debito(b, Componente.ORDINARIA, "50.00"),
        _debito(b, Componente.INTERES, "7.00"),
        _debito(c, Componente.EXTRAORDINARIA, "30.00"),
    ]
    estado = calcular_estado([a, b, c], movimientos, [], [])
    periodos = periodos_de(estado)
    assert [p.periodo for p in periodos] == [SEP, OCT]
    assert list(periodos[0].componentes) == [Componente.INTERES, Componente.ORDINARIA]
    ordinaria = periodos[0].componentes[Componente.ORDINARIA]
    assert (ordinaria.debe, ordinaria.cobrado, ordinaria.pendiente) == (
        Dinero("150.00"),
        CERO,
        Dinero("150.00"),
    )
    assert list(periodos[1].componentes) == [Componente.EXTRAORDINARIA]


def test_lo_cobrado_baja_lo_pendiente_y_los_componentes_sin_traslado_no_aparecen() -> None:
    a = _contenedora(SEP)
    debito = _debito(a, Componente.ORDINARIA, "100.00")
    cobro = _cobro("40.00", 1)
    imputacion = ImputacionRegistrada(cobro.id, a.id, Componente.ORDINARIA, Dinero("40.00"), 1)
    estado = calcular_estado([a], [debito, cobro], [imputacion], [])
    (periodo,) = periodos_de(estado)
    assert list(periodo.componentes) == [Componente.ORDINARIA]
    t = periodo.componentes[Componente.ORDINARIA]
    assert (t.debe, t.cobrado, t.pendiente) == (Dinero("100.00"), Dinero("40.00"), Dinero("60.00"))


def test_un_componente_cobrado_entero_sigue_en_el_detalle_con_pendiente_cero() -> None:
    a = _contenedora(SEP)
    debito = _debito(a, Componente.ORDINARIA, "100.00")
    cobro = _cobro("100.00", 1)
    imputacion = ImputacionRegistrada(cobro.id, a.id, Componente.ORDINARIA, Dinero("100.00"), 1)
    (periodo,) = periodos_de(calcular_estado([a], [debito, cobro], [imputacion], []))
    assert periodo.componentes[Componente.ORDINARIA].pendiente == CERO


def test_los_movimientos_van_por_registro_y_desempatan_por_id() -> None:
    a = _contenedora(SEP)
    tarde = _cobro("10.00", 5)
    temprano = _debito(a, Componente.ORDINARIA, "100.00", 1)
    iguales = sorted(
        (_debito(a, Componente.INTERES, "1.00", 3), _debito(a, Componente.INTERES, "2.00", 3)),
        key=lambda m: str(m.id),
    )
    orden = movimientos_en_orden([tarde, iguales[1], temprano, iguales[0]])
    assert [m.id for m in orden] == [temprano.id, iguales[0].id, iguales[1].id, tarde.id]
    assert isinstance(orden[0].id, UUID)
