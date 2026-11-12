"""Tarea 4.2 de `importacion-desde-excel` (H-010): `ajustar_saldo_inicial` (design D8, E6, E11).

El ajuste es una obligación **nueva** sin emisión (período el primer día del mes de la migración,
vencimiento el día del ajuste), con su fila en `ajuste_de_saldo_inicial`, su permiso, su auditoría y
su replay por `operacion_id`. Contra PostgreSQL real, con la sesión como `proptech_app`.

Orden de chequeo: alcance (404) -> permiso (403) -> estado de la migración (409) -> entrada (422) ->
replay / escritura. Datos inventados.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.complejos.aplicacion.errores import Conflicto as ConflictoDeEdificio
from proptech_core.complejos.aplicacion.errores import NoEncontrado as NoEncontradoDeEdificio
from proptech_core.cuenta_corriente.aplicacion.errores import Conflicto, EntradaInvalida
from proptech_core.importacion.aplicacion.ajuste import AjusteRegistrado, ajustar_saldo_inicial
from proptech_core.importacion.aplicacion.confirmar import confirmar
from proptech_core.importacion.aplicacion.errores import SinPermiso

from ._edificios import BaseDeEdificio
from ._importacion import RELOJ, Mundo, con_tenant, sembrar
from ._saldos_importados import archivo, subir, unidad_de_la_torre

pytestmark = pytest.mark.integracion

ACCION = "ajustar_saldo_inicial"
MOTIVO = "Faltó la expensa extraordinaria de julio"
DIA = date(2026, 11, 5)


def _reloj(dia: date = DIA) -> object:
    return lambda: datetime(dia.year, dia.month, dia.day, 15, tzinfo=UTC)


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


@pytest.fixture
def sesion(mundo: Mundo, sesion_edificio: Session) -> Session:
    con_tenant(sesion_edificio, mundo.admin)
    return sesion_edificio


@pytest.fixture
def confirmado(mundo: Mundo, sesion: Session) -> Mundo:
    """La torre confirmada con el borrador de siempre (migración el 15/10/2026): `1A` debe, `2B`
    tiene crédito y `3A` no tiene cuenta."""
    importacion = subir(sesion, mundo.super_admin, mundo.torre, archivo()).importacion_id
    confirmar(
        sesion,
        mundo.principal,
        complejo_id=mundo.torre,
        importacion_id=importacion,
        reloj=RELOJ,
        request_id=uuid4(),
    )
    # El ajuste es otra transacción (otra petición): el candado por cuenta exige un orden dentro de
    # una misma transacción, y confirmar ya tomó las cuentas del saldo inicial.
    sesion.commit()
    con_tenant(sesion, mundo.admin)
    return mundo


def _ajustar(
    sesion: Session,
    mundo: Mundo,
    unidad: str = "1A",
    importe: str = "5000.00",
    *,
    quien: Identidad | None = None,
    complejo: UUID | None = None,
    componente: str = "ordinaria",
    motivo: str = MOTIVO,
    operacion_id: UUID | None = None,
    dia: date = DIA,
    unidad_id: UUID | None = None,
) -> AjusteRegistrado:
    return ajustar_saldo_inicial(
        sesion,
        quien or mundo.principal,
        complejo_id=complejo or mundo.torre,
        unidad_id=unidad_id or unidad_de_la_torre(sesion, mundo, unidad),
        operacion_id=operacion_id or uuid4(),
        importe=Dinero(importe),
        componente=componente,
        motivo=motivo,
        request_id=uuid4(),
        reloj=_reloj(dia),  # type: ignore[arg-type]
    )


def _escrito(sesion: Session) -> dict[str, object]:
    """Todo lo que el ajuste podría escribir."""
    c: dict[str, object] = {}
    for tabla in ("auditoria", "cuenta", "obligacion", "movimiento", "imputacion"):
        c[tabla] = sesion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()  # noqa: S608
    c["ajustes"] = sesion.execute(
        text("SELECT count(*) FROM ajuste_de_saldo_inicial")
        if sesion.execute(text("SELECT to_regclass('ajuste_de_saldo_inicial')")).scalar_one()
        else text("SELECT 0")
    ).scalar_one()
    return c


def _rechaza(sesion: Session, error: type[Exception], llamada: object) -> Exception:
    antes = _escrito(sesion)
    with pytest.raises(error) as capturado:
        llamada()  # type: ignore[operator]
    assert _escrito(sesion) == antes, "un rechazo no escribe nada"
    return capturado.value


def _obligaciones(sesion: Session, unidad: UUID) -> list[tuple[object, ...]]:
    return [
        tuple(f)
        for f in sesion.execute(
            text(
                "SELECT o.id, o.periodo, o.vencimiento, o.ordinaria::text, "
                "o.fondo_de_reserva::text, o.extraordinaria::text, o.emision_id, o.operacion_id "
                "FROM obligacion o JOIN cuenta c ON c.id = o.cuenta_id "
                "WHERE c.unidad_id = :u ORDER BY o.registrada_en, o.vencimiento"
            ),
            {"u": unidad},
        )
    ]


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


# --- El ajuste ---------------------------------------------------------------------------------


def test_el_ajuste_es_una_obligacion_nueva_sin_emision(confirmado: Mundo, sesion: Session) -> None:
    unidad = unidad_de_la_torre(sesion, confirmado, "1A")
    antes = _obligaciones(sesion, unidad)
    r = _ajustar(sesion, confirmado)
    despues = _obligaciones(sesion, unidad)
    assert all(o in despues for o in antes), "R08: lo de antes no cambia"
    nuevas = [o for o in despues if o not in antes]
    assert len(nuevas) == 1, nuevas
    obligacion, periodo, vencimiento, ordinaria, fondo, extra, emision, operacion = nuevas[0]
    assert (periodo, vencimiento) == (date(2026, 10, 1), DIA), "mes de la migración, día del ajuste"
    assert (ordinaria, fondo, extra) == ("5000.00", "0.00", "0.00")
    assert emision is None and operacion == r.operacion_id
    assert (r.obligacion_id, r.unidad_id, r.componente, r.motivo) == (
        obligacion,
        unidad,
        "ordinaria",
        MOTIVO,
    )
    assert (r.importe.a_texto(), r.periodo, r.vencimiento) == ("5000.00", periodo, DIA)
    assert (r.registrado_por, r.registrado_en) == (
        confirmado.principal.persona_id,
        _reloj()(),  # type: ignore[operator]
    )


def test_el_ajuste_deja_su_fila_con_el_motivo_recortado(confirmado: Mundo, sesion: Session) -> None:
    r = _ajustar(sesion, confirmado, motivo=f"  {MOTIVO}  ")
    existe = sesion.execute(text("SELECT to_regclass('ajuste_de_saldo_inicial')")).scalar_one()
    assert existe is not None, "falta la tabla ajuste_de_saldo_inicial (0039)"
    fila = sesion.execute(
        text(
            "SELECT id, cuenta_id, obligacion_id, operacion_id, motivo, registrado_por, "
            "administracion_id, complejo_id FROM ajuste_de_saldo_inicial"
        )
    ).one()
    assert tuple(fila) == (
        r.ajuste_id,
        r.cuenta_id,
        r.obligacion_id,
        r.operacion_id,
        MOTIVO,
        confirmado.principal.persona_id,
        confirmado.admin,
        confirmado.torre,
    )
    assert r.motivo == MOTIVO


@pytest.mark.parametrize(
    ("componente", "columnas"),
    [
        ("ordinaria", ("2500.00", "0.00", "0.00")),
        ("fondo_de_reserva", ("0.00", "2500.00", "0.00")),
        ("extraordinaria", ("0.00", "0.00", "2500.00")),
    ],
)
def test_el_importe_va_al_componente_elegido(
    confirmado: Mundo, sesion: Session, componente: str, columnas: tuple[str, str, str]
) -> None:
    unidad = unidad_de_la_torre(sesion, confirmado, "1A")
    antes = _obligaciones(sesion, unidad)
    _ajustar(sesion, confirmado, importe="2500.00", componente=componente)
    nueva = next(o for o in _obligaciones(sesion, unidad) if o not in antes)
    assert nueva[3:6] == columnas


def test_una_unidad_sin_cuenta_la_crea(confirmado: Mundo, sesion: Session) -> None:
    unidad = unidad_de_la_torre(sesion, confirmado, "3A")
    assert _obligaciones(sesion, unidad) == []
    cuentas = sesion.execute(
        text("SELECT count(*) FROM cuenta WHERE unidad_id = :u"), {"u": unidad}
    )
    assert cuentas.scalar_one() == 0
    r = _ajustar(sesion, confirmado, "3A", "2000.00")
    cuenta = sesion.execute(
        text("SELECT id FROM cuenta WHERE unidad_id = :u"), {"u": unidad}
    ).scalar_one()
    assert r.cuenta_id == cuenta
    assert [o[3:6] for o in _obligaciones(sesion, unidad)] == [("2000.00", "0.00", "0.00")]


def test_el_credito_a_favor_se_imputa_al_ajuste(confirmado: Mundo, sesion: Session) -> None:
    """`2B` tiene $3.000 a favor: el ajuste de $2.000 lo consume y quedan $1.000 (R04)."""
    unidad = unidad_de_la_torre(sesion, confirmado, "2B")
    _ajustar(sesion, confirmado, "2B", "2000.00")
    saldo = sesion.execute(
        text(
            "SELECT coalesce(sum(i.importe), 0)::text FROM imputacion i "
            "JOIN cuenta c ON c.id = i.cuenta_id WHERE c.unidad_id = :u"
        ),
        {"u": unidad},
    ).scalar_one()
    assert saldo == "2000.00", "el crédito se imputó entero al ajuste"


def test_no_agrega_movimientos(confirmado: Mundo, sesion: Session) -> None:
    antes = _escrito(sesion)["movimiento"]
    _ajustar(sesion, confirmado)
    assert _escrito(sesion)["movimiento"] == antes, "el ajuste es deuda nueva, no un movimiento"


def test_el_ajuste_se_audita_una_vez_con_ids_y_sin_montos(
    confirmado: Mundo, sesion: Session
) -> None:
    r = _ajustar(sesion, confirmado)
    assert _auditorias(sesion) == [
        (
            "ajuste_de_saldo_inicial",
            r.ajuste_id,
            confirmado.principal.persona_id,
            {
                "complejo_id": str(confirmado.torre),
                "unidad_id": str(r.unidad_id),
                "obligacion_id": str(r.obligacion_id),
                "componente": "ordinaria",
            },
        )
    ], "una fila, con ids y nunca montos ni el motivo (D9)"


@pytest.mark.parametrize("quien", ["super_admin", "principal"])
def test_los_que_pueden_ajustar(confirmado: Mundo, sesion: Session, quien: str) -> None:
    assert _ajustar(sesion, confirmado, quien=getattr(confirmado, quien)).ajuste_id


# --- El vencimiento es el día del ajuste (mutante: retroactivo) --------------------------------


@pytest.mark.parametrize("dia", [date(2026, 11, 5), date(2026, 12, 20)])
def test_el_vencimiento_es_el_dia_del_ajuste_nunca_la_migracion(
    confirmado: Mundo, sesion: Session, dia: date
) -> None:
    r = _ajustar(sesion, confirmado, dia=dia)
    assert r.vencimiento == dia and r.periodo == date(2026, 10, 1)
    guardado = sesion.execute(
        text("SELECT vencimiento FROM obligacion WHERE id = :o"), {"o": r.obligacion_id}
    ).scalar_one()
    assert guardado == dia, "no es la fecha de migración ni una retroactiva (E11)"


# --- Replay ------------------------------------------------------------------------------------


def test_el_replay_devuelve_lo_mismo_sin_escribir(confirmado: Mundo, sesion: Session) -> None:
    operacion = uuid4()
    primero = _ajustar(sesion, confirmado, operacion_id=operacion)
    antes = _escrito(sesion)
    segundo = _ajustar(sesion, confirmado, operacion_id=operacion)
    assert segundo.ajuste_id == primero.ajuste_id
    assert segundo.obligacion_id == primero.obligacion_id
    assert (segundo.importe, segundo.componente, segundo.motivo, segundo.vencimiento) == (
        primero.importe,
        primero.componente,
        primero.motivo,
        primero.vencimiento,
    )
    assert segundo.repetido is True and primero.repetido is False
    assert _escrito(sesion) == antes, "ni obligación, ni ajuste, ni auditoría"
    assert len(_auditorias(sesion)) == 1


def test_el_replay_con_el_motivo_sin_recortar_es_el_mismo_pedido(
    confirmado: Mundo, sesion: Session
) -> None:
    operacion = uuid4()
    primero = _ajustar(sesion, confirmado, operacion_id=operacion)
    assert _ajustar(sesion, confirmado, operacion_id=operacion, motivo=f" {MOTIVO} ").ajuste_id == (
        primero.ajuste_id
    )


@pytest.mark.parametrize(
    "cambio",
    [
        {"importe": "4000.00"},
        {"motivo": "Otro motivo"},
        {"componente": "extraordinaria"},
        {"unidad": "1B"},
    ],
    ids=["otro_importe", "otro_motivo", "otro_componente", "otra_unidad"],
)
def test_la_misma_operacion_con_otros_datos_es_conflicto(
    confirmado: Mundo, sesion: Session, cambio: dict[str, str]
) -> None:
    operacion = uuid4()
    _ajustar(sesion, confirmado, operacion_id=operacion)
    error = _rechaza(
        sesion,
        Conflicto,
        lambda: _ajustar(
            sesion,
            confirmado,
            cambio.get("unidad", "1A"),
            cambio.get("importe", "5000.00"),
            componente=cambio.get("componente", "ordinaria"),
            motivo=cambio.get("motivo", MOTIVO),
            operacion_id=operacion,
        ),
    )
    assert isinstance(error, Conflicto) and error.campo == "operacion_id"


# --- Rechazos: el estado de la migración (mutante: permitir con la migración pendiente) --------


@pytest.mark.parametrize("estado", ["pendiente", "sin_saldos_previos"])
def test_solo_con_la_migracion_confirmada(confirmado: Mundo, sesion: Session, estado: str) -> None:
    unidad = unidad_de_la_torre(sesion, confirmado, "1A")
    sesion.execute(
        text("UPDATE complejo SET estado_migracion = :e WHERE id = :c"),
        {"e": estado, "c": confirmado.torre},
    )
    error = _rechaza(sesion, ConflictoDeEdificio, lambda: _ajustar(sesion, confirmado))
    assert isinstance(error, ConflictoDeEdificio) and error.campo == "estado_migracion"
    assert unidad  # la unidad existe: lo que frena es el estado


def test_un_edificio_pendiente_sin_carga(mundo: Mundo, sesion: Session) -> None:
    """La torre con el padrón importado y sin confirmar (pendiente, sin carga): nada que ajustar."""
    subir(sesion, mundo.super_admin, mundo.torre, archivo())  # el padrón sí está; la carga no
    error = _rechaza(
        sesion,
        ConflictoDeEdificio,
        lambda: ajustar_saldo_inicial(
            sesion,
            mundo.principal,
            complejo_id=mundo.torre,
            unidad_id=unidad_de_la_torre(sesion, mundo, "1A"),
            operacion_id=uuid4(),
            importe=Dinero("1.00"),
            componente="ordinaria",
            motivo=MOTIVO,
            request_id=uuid4(),
            reloj=RELOJ,
        ),
    )
    assert error.campo == "estado_migracion"  # type: ignore[attr-defined]


# --- Rechazos: la entrada (mutante: sin motivo) ------------------------------------------------


@pytest.mark.parametrize(
    "motivo", ["", "   ", "x" * 501, "\n\t"], ids=["vacio", "blanco", "501", "ctl"]
)
def test_el_motivo_es_obligatorio_y_acotado(
    confirmado: Mundo, sesion: Session, motivo: str
) -> None:
    error = _rechaza(sesion, EntradaInvalida, lambda: _ajustar(sesion, confirmado, motivo=motivo))
    assert error.campo == "motivo"  # type: ignore[attr-defined]


def test_un_motivo_de_500_caracteres_entra(confirmado: Mundo, sesion: Session) -> None:
    assert _ajustar(sesion, confirmado, motivo="x" * 500).motivo == "x" * 500


@pytest.mark.parametrize("importe", ["0.00", "-1.00"], ids=["cero", "negativo"])
def test_el_importe_es_mayor_que_cero(confirmado: Mundo, sesion: Session, importe: str) -> None:
    error = _rechaza(sesion, EntradaInvalida, lambda: _ajustar(sesion, confirmado, importe=importe))
    assert error.campo == "importe"  # type: ignore[attr-defined]


@pytest.mark.parametrize("componente", ["interes", "otro", ""])
def test_el_componente_es_uno_de_los_tres(
    confirmado: Mundo, sesion: Session, componente: str
) -> None:
    error = _rechaza(
        sesion, EntradaInvalida, lambda: _ajustar(sesion, confirmado, componente=componente)
    )
    assert error.campo == "componente"  # type: ignore[attr-defined]


# --- Rechazos: alcance y permiso (404 antes que 403) -------------------------------------------


@pytest.mark.parametrize("quien", ["de_la_torre", "contador", "auxiliar"])
def test_sin_el_permiso_es_403(confirmado: Mundo, sesion: Session, quien: str) -> None:
    error = _rechaza(
        sesion,
        SinPermiso,
        lambda: _ajustar(sesion, confirmado, quien=getattr(confirmado, quien)),
    )
    assert error.permiso_faltante == ACCION  # type: ignore[attr-defined]


def test_el_administrador_de_otro_edificio_no_lo_ve(confirmado: Mundo, sesion: Session) -> None:
    _rechaza(
        sesion,
        NoEncontradoDeEdificio,
        lambda: _ajustar(sesion, confirmado, quien=confirmado.de_otro),
    )


def test_una_unidad_de_otro_edificio_no_existe(confirmado: Mundo, sesion: Session) -> None:
    ajena = UUID(
        str(
            sesion.execute(
                text("SELECT id FROM unidad WHERE complejo_id = :c"), {"c": confirmado.con_padron}
            ).scalar_one()
        )
    )
    from proptech_core.cuenta_corriente.aplicacion.errores import NoEncontrado

    _rechaza(sesion, NoEncontrado, lambda: _ajustar(sesion, confirmado, unidad_id=ajena))


def test_una_unidad_inexistente(confirmado: Mundo, sesion: Session) -> None:
    from proptech_core.cuenta_corriente.aplicacion.errores import NoEncontrado

    _rechaza(sesion, NoEncontrado, lambda: _ajustar(sesion, confirmado, unidad_id=uuid4()))


def test_otra_administracion_no_existe(confirmado: Mundo, sesion: Session) -> None:
    con_tenant(sesion, confirmado.admin_b)
    _rechaza(
        sesion,
        NoEncontradoDeEdificio,
        lambda: ajustar_saldo_inicial(
            sesion,
            confirmado.principal,
            complejo_id=confirmado.torre,
            unidad_id=uuid4(),
            operacion_id=uuid4(),
            importe=Dinero("1.00"),
            componente="ordinaria",
            motivo=MOTIVO,
            request_id=uuid4(),
            reloj=RELOJ,
        ),
    )


@pytest.mark.parametrize("estado", ["pendiente", "sin_saldos_previos"])
def test_la_unidad_que_no_es_del_edificio_gana_al_estado_de_la_migracion(
    confirmado: Mundo, sesion: Session, estado: str
) -> None:
    """Orden del contrato: alcance y unidad (404) antes que el estado (409). La unidad es de otro
    edificio, y el edificio no está confirmado: sigue siendo un 404, nunca un 409."""
    from proptech_core.cuenta_corriente.aplicacion.errores import NoEncontrado

    ajena = UUID(
        str(
            sesion.execute(
                text("SELECT id FROM unidad WHERE complejo_id = :c"), {"c": confirmado.con_padron}
            ).scalar_one()
        )
    )
    sesion.execute(
        text("UPDATE complejo SET estado_migracion = :e WHERE id = :c"),
        {"e": estado, "c": confirmado.torre},
    )
    antes = _escrito(sesion)
    try:
        _ajustar(sesion, confirmado, unidad_id=ajena)
        resultado: object = None
    except Exception as error:
        resultado = error
    assert isinstance(resultado, NoEncontrado), f"se esperaba NoEncontrado, llegó {resultado!r}"
    assert _escrito(sesion) == antes
