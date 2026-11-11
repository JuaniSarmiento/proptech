"""5.1 a 5.3 del 4c · el interés dentro de `registrar_emision`, contra PostgreSQL real.

Cubre D0, D1, E1, E2, E4, E10, E15, E17 y E19.

Cada paso del libro confirma su transacción (`paso`): dos emisiones en una sola transacción dan
`BloqueoFueraDeOrden` (E2 del 4b), y no se "arregla" en producción. La configuración de cada prueba
la crea `configurar` (el mundo se siembra sin ella). Base común: ordinaria de septiembre de
$100.000 vencida el 10/09/2026, 3% mensual proporcional por día, gracia 0.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import correcciones, creditos, emisiones, lecturas
from proptech_core.cuenta_corriente.aplicacion.correcciones import PedidoDeCorreccion
from proptech_core.cuenta_corriente.aplicacion.emisiones import EmisionRegistrada, ObligacionAEmitir
from proptech_core.cuenta_corriente.aplicacion.errores import Conflicto, NoEncontrado
from proptech_core.cuenta_corriente.dominio.errores import EntradaInvalida

from ._cuenta_corriente import Mundo, contar_escrituras, sembrar, sesion_app
from ._edificios import BaseDeEdificio, fijar_tenant

pytestmark = pytest.mark.integracion

SEP, OCT, NOV, DIC = (date(2026, m, 1) for m in (9, 10, 11, 12))
PROPORCIONAL, MES_ENTERO = "proporcional_por_dia", "mes_entero"
RELLENO = 11  # la unidad que lleva la obligación de un período cuando la medida no debe tenerla


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def d(t: str) -> Dinero:
    return Dinero(t)


def dia(m: int, dd: int) -> date:
    return date(2026, m, dd)


def configurar(
    base: BaseDeEdificio,
    mundo: Mundo,
    *,
    desde: date = date(2026, 1, 1),
    tasa: str = "3.00",
    gracia: int = 0,
    forma: str = PROPORCIONAL,
    complejo: UUID | None = None,
) -> UUID:
    with base.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, mundo.admin)
        fila = c.execute(
            "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, "
            "vigente_desde, tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, "
            "porcentaje_fondo, dia_de_vencimiento, modalidad_de_vencimiento) "
            "VALUES (%s, %s, %s, %s, %s, '500.00', %s, %s, '0.00', 10, 'unico') RETURNING id",
            (mundo.admin, complejo or mundo.complejo, mundo.persona, desde, tasa, gracia, forma),
        ).fetchone()
        assert fila is not None
        c.commit()
        return UUID(str(fila[0]))


def obl(mundo: Mundo, unidad: int, vence: date, ordinaria: str = "100000.00") -> ObligacionAEmitir:
    return ObligacionAEmitir(mundo.unidades[unidad], vence, d(ordinaria), d("0.00"), d("0.00"))


def relleno(mundo: Mundo, periodo: date) -> list[ObligacionAEmitir]:
    return [obl(mundo, RELLENO, periodo.replace(day=10), "1.00")]


def paso(s: Session) -> None:
    s.commit()
    s.begin()


def emitir(
    s: Session,
    mundo: Mundo,
    periodo: date,
    obls: list[ObligacionAEmitir],
    *,
    emision_id: UUID | None = None,
    reloj: Callable[[], datetime] | None = None,
    confirmar: bool = True,
) -> EmisionRegistrada:
    extra: dict[str, Any] = {} if reloj is None else {"reloj": reloj}
    r = emisiones.registrar_emision(
        s,
        mundo.identidad,
        emision_id=emision_id or uuid4(),
        complejo_id=mundo.complejo,
        periodo=periodo,
        obligaciones=obls,
        request_id=uuid4(),
        **extra,
    )
    if confirmar:
        paso(s)
    return r


def septiembre(s: Session, mundo: Mundo, *unidades: int) -> tuple[UUID, UUID]:
    """Septiembre de las unidades (por defecto la 0); devuelve cuenta y obligación de la primera."""
    r = emitir(s, mundo, SEP, [obl(mundo, u, dia(9, 10)) for u in (unidades or (0,))])
    cuenta = r.cuentas[mundo.unidades[(unidades or (0,))[0]]]
    return cuenta, obligacion_de(s, cuenta, r.emision_id)


def obligacion_de(s: Session, cuenta: UUID, emision_id: UUID) -> UUID:
    return UUID(
        str(
            s.execute(
                text("SELECT id FROM obligacion WHERE cuenta_id = :c AND emision_id = :e"),
                {"c": cuenta, "e": emision_id},
            ).scalar_one()
        )
    )


def cuenta_de(s: Session, mundo: Mundo, unidad: int) -> UUID:
    return UUID(
        str(
            s.execute(
                text("SELECT id FROM cuenta WHERE unidad_id = :u"), {"u": mundo.unidades[unidad]}
            ).scalar_one()
        )
    )


@dataclass(frozen=True)
class Interes:
    id: UUID
    cuenta_id: UUID
    obligacion_id: UUID
    corte: date
    importe: Dinero
    emision_id: UUID | None


def intereses(
    s: Session, *, obligacion: UUID | None = None, cuenta: UUID | None = None
) -> list[Interes]:
    filas = s.execute(
        text(
            "SELECT id, cuenta_id, obligacion_id, corte, importe::text AS importe, emision_id "
            "FROM movimiento WHERE tipo = 'interes' AND sentido = 'debito' "
            "AND (CAST(:o AS uuid) IS NULL OR obligacion_id = :o) "
            "AND (CAST(:c AS uuid) IS NULL OR cuenta_id = :c) ORDER BY corte, registrado_en"
        ),
        {"o": obligacion, "c": cuenta},
    ).all()
    return [
        Interes(
            UUID(str(f.id)),
            UUID(str(f.cuenta_id)),
            UUID(str(f.obligacion_id)),
            f.corte,
            d(f.importe),
            None if f.emision_id is None else UUID(str(f.emision_id)),
        )
        for f in filas
    ]


def interes_unico(s: Session, obligacion: UUID, corte: date) -> Interes:
    hay = [i for i in intereses(s, obligacion=obligacion) if i.corte == corte]
    assert len(hay) == 1, f"se espera un interés con corte {corte}, hay {len(hay)}"
    return hay[0]


def tramos(s: Session, movimiento: UUID) -> list[tuple[date, date, int, str, str, str, int, UUID]]:
    filas = s.execute(
        text(
            "SELECT desde, hasta, dias, base::text AS base, tasa_mensual::text AS tasa, "
            "forma_de_calculo, dias_de_gracia, configuracion_id FROM tramo_de_interes "
            "WHERE movimiento_id = :m ORDER BY desde"
        ),
        {"m": movimiento},
    ).all()
    return [
        (
            f.desde,
            f.hasta,
            int(f.dias),
            f.base,
            f.tasa,
            f.forma_de_calculo,
            int(f.dias_de_gracia),
            UUID(str(f.configuracion_id)),
        )
        for f in filas
    ]


def informados(r: EmisionRegistrada) -> dict[UUID, list[tuple[UUID, date, Dinero]]]:
    assert hasattr(r, "intereses"), "EmisionRegistrada no informa `intereses` (design D1)"
    return {
        cuenta: sorted(((i.obligacion_id, i.corte, i.importe) for i in lista), key=str)
        for cuenta, lista in r.intereses.items()
    }


def conteos(s: Session) -> dict[str, int]:
    return {
        t: int(s.execute(text(f"SELECT count(*) FROM {t}")).scalar_one())  # noqa: S608 - fijas
        for t in ("emision", "obligacion", "movimiento", "imputacion", "tramo_de_interes")
    }


def anular(s: Session, mundo: Mundo, emision_id: UUID) -> None:
    emisiones.anular_emision(
        s, mundo.identidad, emision_id=emision_id, motivo="Emisión mal cargada", request_id=uuid4()
    )
    paso(s)


def pagar(s: Session, mundo: Mundo, cuenta: UUID, importe: str, valor: date) -> UUID:
    m = creditos.registrar_credito(
        s,
        mundo.identidad,
        cuenta_id=cuenta,
        tipo="pago",
        importe=d(importe),
        fecha_valor=valor,
        operacion_id=uuid4(),
        destino=None,
        request_id=uuid4(),
    )
    paso(s)
    return m


def contra_asentar(s: Session, mundo: Mundo, movimiento: UUID) -> UUID:
    m = correcciones.corregir(
        s,
        mundo.identidad,
        complejo_id=mundo.complejo,
        pedido=PedidoDeCorreccion(
            "contra_asiento", uuid4(), "Interés mal calculado", movimiento_id=movimiento
        ),
        request_id=uuid4(),
    )
    paso(s)
    return m


# --- 5.1 · Registro del interés al emitir ---------------------------------------------------


def test_cc_interes_de_septiembre_en_la_emision_de_octubre(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Corte 30/09 (E2), referencia a la emisión y tramos guardados con la versión que rigió."""
    version = configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        r = emitir(s, mundo, OCT, relleno(mundo, OCT))
        i = interes_unico(s, o, dia(9, 30))
        assert (i.importe, i.cuenta_id, i.emision_id) == (d("2000.00"), cuenta, r.emision_id)
        assert tramos(s, i.id) == [
            (dia(9, 11), dia(9, 30), 20, "100000.00", "3.00", PROPORCIONAL, 0, version)
        ]
        assert informados(r) == {cuenta: [(o, dia(9, 30), d("2000.00"))]}


def test_cc_unidad_sin_obligacion_en_la_emision_nueva_recibe_su_interes(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """E10: la cuenta que no emite este mes también recibe el interés y queda alcanzada."""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        septiembre(s, mundo, 0, 1)
        u2 = cuenta_de(s, mundo, 1)
        r = emitir(s, mundo, OCT, [obl(mundo, 0, dia(10, 10), "1.00")])
        assert [i.importe for i in intereses(s, cuenta=u2)] == [d("2000.00")]
        assert u2 not in r.cuentas.values() and u2 in r.saldo_anterior
        assert [c for c, lista in informados(r).items() if lista and c == u2] == [u2]


def test_cc_emision_anulada_no_genera_interes_sobre_sus_obligaciones(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        primera = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10))])
        o0 = obligacion_de(s, primera.cuentas[mundo.unidades[0]], primera.emision_id)
        anular(s, mundo, primera.emision_id)
        segunda = emitir(s, mundo, SEP, [obl(mundo, 1, dia(9, 10))])
        o1 = obligacion_de(s, segunda.cuentas[mundo.unidades[1]], segunda.emision_id)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        assert interes_unico(s, o1, dia(9, 30)).importe == d("2000.00"), "control: la vigente sí"
        assert intereses(s, obligacion=o0) == [], "la obligación de una emisión anulada cobró"


def test_cc_saldo_anterior_con_interes(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        r = emitir(s, mundo, OCT, [obl(mundo, 0, dia(10, 10), "50000.00")])
        assert r.saldo_anterior[cuenta] == d("102000.00")
        assert informados(r)[cuenta] == [(o, dia(9, 30), d("2000.00"))]


def test_cc_emitir_a_mitad_de_mes_no_adelanta_interes(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """El corte sale del período emitido, no del reloj: el 15/10 sigue cortando el 30/09."""
    configurar(base_del_edificio, mundo)
    quince = datetime(2026, 10, 15, 12, tzinfo=UTC)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT), reloj=lambda: quince)
        assert [(i.corte, i.importe) for i in intereses(s, obligacion=o)] == [
            (dia(9, 30), d("2000.00"))
        ]


def test_cc_redondeo_unico_sobre_dos_tramos_contra_la_base(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """$64,00 vencida el 28/09 y un pago de $1,00 el 29/09: 0,128 + ... redondea una sola vez."""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 28), "64.00")])
        cuenta = r.cuentas[mundo.unidades[0]]
        o = obligacion_de(s, cuenta, r.emision_id)
        pagar(s, mundo, cuenta, "1.00", dia(9, 29))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        i = interes_unico(s, o, dia(9, 30))
        assert i.importe == d("0.13"), "redondear cada tramo y sumar da $0,12"
        assert [(t[0], t[1], t[3]) for t in tramos(s, i.id)] == [
            (dia(9, 29), dia(9, 29), "64.00"),
            (dia(9, 30), dia(9, 30), "63.00"),
        ]


# --- 5.2 · Configuración al corte (PR-01) ----------------------------------------------------


def _rechazo_por_configuracion(s: Session, mundo: Mundo) -> None:
    emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10))])
    antes = conteos(s)
    with pytest.raises(Conflicto) as e:
        emitir(s, mundo, OCT, relleno(mundo, OCT))
    assert e.value.campo == "configuracion"
    assert conteos(s) == antes, "el libro cambió"


def test_cc_sin_configuracion_vigente_rechaza_sin_escribir(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _rechazo_por_configuracion(s, mundo)


def test_cc_solo_una_version_futura_rechaza_sin_escribir(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo, desde=dia(10, 1))
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _rechazo_por_configuracion(s, mundo)


def test_cc_cambio_de_tasa_entre_periodos(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    v1 = configurar(base_del_edificio, mundo, tasa="3.00")
    v2 = configurar(base_del_edificio, mundo, desde=dia(10, 1), tasa="6.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        sep, octubre = interes_unico(s, o, dia(9, 30)), interes_unico(s, o, dia(10, 31))
        assert (sep.importe, octubre.importe) == (d("2000.00"), d("6200.00"))
        assert {(t[4], t[7]) for t in tramos(s, sep.id)} == {("3.00", v1)}
        assert {(t[4], t[7]) for t in tramos(s, octubre.id)} == {("6.00", v2)}


def test_cc_edificio_de_otra_administracion_no_se_encuentra(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        septiembre(s, mundo)
        s.commit()
        antes = conteos(s)
    with sesion_app(base_del_edificio, mundo.admin_b) as b:
        with pytest.raises(NoEncontrado):
            emisiones.registrar_emision(
                b,
                mundo.identidad_b,
                emision_id=uuid4(),
                complejo_id=mundo.complejo,
                periodo=OCT,
                obligaciones=[obl(mundo, 0, dia(10, 10))],
                request_id=uuid4(),
            )
    with sesion_app(base_del_edificio, mundo.admin) as s:
        assert conteos(s) == antes


def test_cc_forma_que_no_cierra_rechaza_la_emision_sin_escribir(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mes entero con días de un mes no contiguos: el dominio lanza `EntradaInvalida` y la emisión
    lo traduce a `Conflicto("interes")` sin dejar nada escrito (decisión de la tanda 6)."""
    configurar(base_del_edificio, mundo)

    def no_cierra(*args: Any, **kw: Any) -> Any:
        raise EntradaInvalida("dias", "días a cobrar no contiguos dentro de un mes")

    with sesion_app(base_del_edificio, mundo.admin) as s:
        septiembre(s, mundo)
        antes = conteos(s)
        monkeypatch.setattr(emisiones, "calcular_intereses", no_cierra, raising=False)
        with pytest.raises(Conflicto) as e:
            emitir(s, mundo, OCT, relleno(mundo, OCT))
        assert e.value.campo == "interes"
        assert conteos(s) == antes, "el libro cambió"


# --- 5.3 · Re-emisión, replay (E15) ------------------------------------------------------------


def _anular_y_reemitir_octubre(s: Session, mundo: Mundo, o: UUID) -> UUID:
    obls = [obl(mundo, 0, dia(10, 10), "50000.00")]
    primera = emitir(s, mundo, OCT, obls)
    anulado = interes_unico(s, o, dia(9, 30))
    assert anulado.importe == d("2000.00") and anulado.emision_id == primera.emision_id
    anular(s, mundo, primera.emision_id)
    emitir(s, mundo, OCT, obls)
    return anulado.id


def test_cc_anular_y_volver_a_emitir_no_cobra_dos_veces(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        anulado = _anular_y_reemitir_octubre(s, mundo, o)
        del_corte = [i.id for i in intereses(s, obligacion=o) if i.corte == dia(9, 30)]
        assert del_corte == [anulado], "el corte ocupado recibió otro interés"
        assert anulado not in lecturas.foto(s, cuenta).estado.movimientos_que_cuentan
        assert lecturas.estado_de_cuenta(s, cuenta_id=cuenta).deuda == d("150000.00")


def test_cc_el_corte_siguiente_recupera_el_tramo_con_su_tasa(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo, tasa="3.00")
    v2 = configurar(base_del_edificio, mundo, desde=dia(10, 1), tasa="6.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        _anular_y_reemitir_octubre(s, mundo, o)
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        i = interes_unico(s, o, dia(10, 31))
        assert i.importe == d("10200.00"), "51 días al 6%, no $2.000,00 + $6.200,00"
        ts = tramos(s, i.id)
        assert [(t[0], t[1]) for t in ts] == [(dia(9, 11), dia(10, 31))]
        assert {(t[4], t[7]) for t in ts} == {("6.00", v2)}


def test_cc_un_hueco_anterior_se_recupera_aunque_haya_un_interes_posterior(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """E17 con el contra-asiento hecho por el caso de uso real de correcciones del 4b."""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        octubre = interes_unico(s, o, dia(9, 30))
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        noviembre = interes_unico(s, o, dia(10, 31))
        assert (octubre.importe, noviembre.importe) == (d("2000.00"), d("3100.00"))
        contra_asentar(s, mundo, octubre.id)
        emitir(s, mundo, DIC, relleno(mundo, DIC))
        diciembre = interes_unico(s, o, dia(11, 30))
        assert diciembre.importe == d("5000.00")
        assert [(t[0], t[1]) for t in tramos(s, diciembre.id)] == [
            (dia(9, 11), dia(9, 30)),
            (dia(11, 1), dia(11, 30)),
        ]
        cuentan = lecturas.foto(s, cuenta).estado.movimientos_que_cuentan
        assert noviembre.id in cuentan and octubre.id not in cuentan


def test_cc_los_dias_de_un_corte_con_tasa_cero_se_cobran_despues(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """E19 con dos versiones reales de configuración."""
    configurar(base_del_edificio, mundo, tasa="0.00")
    configurar(base_del_edificio, mundo, desde=dia(10, 1), tasa="3.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        i = interes_unico(s, o, dia(10, 31))
        assert i.importe == d("5100.00")
        assert [(t[0], t[1]) for t in tramos(s, i.id)] == [(dia(9, 11), dia(10, 31))]
        assert [x for x in intereses(s, obligacion=o) if x.corte == dia(9, 30)] == []


def test_cc_replay_inmediato_con_interes_no_escribe(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        obls, eid = [obl(mundo, 0, dia(10, 10), "50000.00")], uuid4()
        emitir(s, mundo, OCT, obls, emision_id=eid)
        antes = conteos(s)
        escrituras = contar_escrituras(s)
        replay = emitir(s, mundo, OCT, obls, emision_id=eid)
        assert informados(replay)[cuenta] == [(o, dia(9, 30), d("2000.00"))]
        assert replay.saldo_anterior[cuenta] == d("102000.00")
        assert escrituras == [] and conteos(s) == antes, "el replay escribió"


def test_cc_replay_despues_de_un_pago_recalcula_el_saldo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        obls, eid = [obl(mundo, 0, dia(10, 10), "50000.00")], uuid4()
        emitir(s, mundo, OCT, obls, emision_id=eid)
        pagar(s, mundo, cuenta, "30000.00", dia(10, 5))
        replay = emitir(s, mundo, OCT, obls, emision_id=eid)
        assert informados(replay)[cuenta] == [(o, dia(9, 30), d("2000.00"))]
        assert replay.saldo_anterior[cuenta] == d("72000.00")


def test_cc_replay_despues_de_anular_devuelve_el_interes_que_ya_no_cuenta(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        obls, eid = [obl(mundo, 0, dia(10, 10), "50000.00")], uuid4()
        emitir(s, mundo, OCT, obls, emision_id=eid)
        anular(s, mundo, eid)
        replay = emitir(s, mundo, OCT, obls, emision_id=eid)
        assert informados(replay)[cuenta] == [(o, dia(9, 30), d("2000.00"))]
        assert replay.saldo_anterior[cuenta] == d("100000.00")


def test_cc_emision_concurrente_con_un_pago_de_otra_unidad(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """La emisión bloquea todas las cuentas de unidad del edificio en un solo pedido: el pago de
    otra unidad espera, termina sin interbloqueo y ve el interés recién registrado."""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        septiembre(s, mundo, 0, 1)
        u2 = cuenta_de(s, mundo, 1)
        s.commit()
    resultado: dict[str, Any] = {}

    def pagar_u2() -> None:
        try:
            with sesion_app(base_del_edificio, mundo.admin) as otra:
                resultado["id"] = pagar(otra, mundo, u2, "500.00", dia(10, 5))
                otra.commit()
        except BaseException as error:
            resultado["error"] = error

    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, OCT, [obl(mundo, 0, dia(10, 10), "1.00")], confirmar=False)
        hilo = threading.Thread(target=pagar_u2, daemon=True)
        hilo.start()
        hilo.join(2.0)
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
                {"m": resultado["id"]},
            ).scalars()
        )
    assert "interes" in componentes, "el pago no vio el interés de la emisión"
