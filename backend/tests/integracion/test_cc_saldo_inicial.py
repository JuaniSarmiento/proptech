"""6.1, 6.2 y 6.4 · `registrar_saldo_inicial` contra PostgreSQL real (design D5, R09, E11, E16).

Apoyo del constructor para H-005 (la aceptación que decide es `aceptacion/H-005/`): acá se miden los
mutantes de cada tarea, por su aserción.
"""

import functools
import threading
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import lecturas
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
)
from proptech_core.cuenta_corriente.aplicacion.saldo_inicial import (
    FilaDeCredito,
    FilaDeDeuda,
    FilaDeTotal,
    OrigenDeCarga,
    SaldoInicialRegistrado,
    UnidadDeSaldoInicial,
    registrar_saldo_inicial,
)

from ._cuenta_corriente import Mundo, contar_escrituras, en_hilo, sembrar, sesion_app
from ._edificios import BaseDeEdificio, fijar_tenant

pytestmark = pytest.mark.integracion

AGO, SEP, OCT = date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)
MIGRACION = date(2026, 10, 15)
HOY = date(2026, 11, 11)
ARCHIVO = "saldos-octubre.xlsx"


def d(t: str) -> Dinero:
    return Dinero(t)


def reloj(dia: date = HOY) -> Callable[[], datetime]:
    return lambda: datetime(dia.year, dia.month, dia.day, 15, tzinfo=UTC)


def deuda(
    fila: int | None,
    periodo: date,
    vence: date,
    importe: str,
    *,
    componente: str = "ordinaria",
    interes: str = "0.00",
) -> FilaDeDeuda:
    return FilaDeDeuda(fila, periodo, vence, componente, d(importe), d(interes))


def u(mundo: Mundo, n: int, *filas: Any, modo: str = "detalle") -> UnidadDeSaldoInicial:
    return UnidadDeSaldoInicial(mundo.unidades[n], modo, tuple(filas))


def importador(archivo: str = ARCHIVO) -> OrigenDeCarga:
    return OrigenDeCarga(tipo="importador", archivo=archivo)


def cargar(
    s: Session,
    mundo: Mundo,
    unidades: list[UnidadDeSaldoInicial],
    *,
    operacion_id: UUID | None = None,
    fecha: date = MIGRACION,
    origen: OrigenDeCarga | None = None,
    complejo: UUID | None = None,
    hoy: date = HOY,
) -> SaldoInicialRegistrado:
    return registrar_saldo_inicial(
        s,
        mundo.identidad,
        complejo_id=complejo or mundo.complejo,
        operacion_id=operacion_id or uuid4(),
        fecha_de_migracion=fecha,
        origen=origen or importador(),
        unidades=unidades,
        request_id=uuid4(),
        reloj=reloj(hoy),
    )


def septiembre(mundo: Mundo, n: int = 1, fila: int = 8) -> UnidadDeSaldoInicial:
    return u(mundo, n, deuda(fila, SEP, date(2026, 9, 10), "85000.00"))


def dos_conceptos(mundo: Mundo, a: str = "85000.00", b: str = "20000.00") -> UnidadDeSaldoInicial:
    return u(
        mundo,
        5,
        deuda(12, SEP, date(2026, 9, 10), a, interes="3000.00"),
        deuda(13, SEP, date(2026, 9, 10), b, componente="extraordinaria"),
    )


def conteos(s: Session) -> dict[str, int]:
    tablas = (
        "cuenta",
        "obligacion",
        "movimiento",
        "imputacion",
        "carga_de_saldo_inicial",
        "origen_de_saldo_inicial",
    )
    return {
        t: int(s.execute(text(f"SELECT count(*) FROM {t}")).scalar_one())  # noqa: S608 - fijas
        for t in tablas
    }


def cuenta_de(s: Session, unidad: UUID) -> UUID:
    fila = s.execute(text("SELECT id FROM cuenta WHERE unidad_id = :u"), {"u": unidad}).first()
    assert fila is not None, "la unidad no tiene cuenta"
    return UUID(str(fila.id))


def poner_estado(base: BaseDeEdificio, mundo: Mundo, estado: str) -> None:
    with base.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, mundo.admin)
        c.execute(
            "UPDATE complejo SET estado_migracion = %s WHERE id = %s", (estado, mundo.complejo)
        )
        c.commit()


def obligaciones(s: Session, cuenta: UUID) -> list[Any]:
    return list(
        s.execute(
            text(
                "SELECT id, periodo, vencimiento, ordinaria::text AS ord, "
                "fondo_de_reserva::text AS fon, extraordinaria::text AS ext, emision_id, "
                "operacion_id FROM obligacion WHERE cuenta_id = :c ORDER BY periodo"
            ),
            {"c": cuenta},
        ).all()
    )


def intereses(s: Session, obligacion: UUID) -> list[Any]:
    return list(
        s.execute(
            text(
                "SELECT id, importe::text AS importe, corte, emision_id, componente, operacion_id "
                "FROM movimiento WHERE tipo = 'interes' AND obligacion_id = :o"
            ),
            {"o": obligacion},
        ).all()
    )


def origenes(s: Session, cuenta: UUID) -> list[Any]:
    return list(
        s.execute(
            text(
                "SELECT fila, obligacion_id, movimiento_id, sentido_del_movimiento "
                "FROM origen_de_saldo_inicial WHERE cuenta_id = :c"
            ),
            {"c": cuenta},
        ).all()
    )


def filas_de(
    origen: list[Any], *, obligacion: UUID | None = None, movimiento: UUID | None = None
) -> set[Any]:
    return {
        o.fila
        for o in origen
        if (obligacion is not None and o.obligacion_id == obligacion)
        or (movimiento is not None and o.movimiento_id == movimiento)
    }


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


# --- 6.1 · Validaciones (E11, E16) -------------------------------------------------------------


def _casos_invalidos(m: Mundo) -> list[tuple[str, str, dict[str, Any]]]:
    sep = date(2026, 9, 10)
    return [
        (
            "vencimiento_un_dia_despues_de_la_migracion",
            "vencimiento",
            {"unidades": [u(m, 1, deuda(7, OCT, date(2026, 10, 16), "100.00"))]},
        ),
        (
            "vencimiento_futuro",
            "vencimiento",
            {"unidades": [u(m, 1, deuda(7, OCT, date(2026, 10, 20), "85000.00"))]},
        ),
        (
            "mismo_periodo_con_vencimientos_distintos",
            "vencimiento",
            {
                "unidades": [
                    u(
                        m,
                        5,
                        deuda(12, SEP, sep, "85000.00", interes="3000.00"),
                        deuda(13, SEP, date(2026, 9, 15), "20000.00", componente="extraordinaria"),
                    )
                ]
            },
        ),
        (
            "periodo_que_no_es_dia_1",
            "periodo",
            {"unidades": [u(m, 1, deuda(7, date(2026, 9, 5), sep, "85000.00"))]},
        ),
        (
            "periodo_posterior_al_mes_de_migracion",
            "periodo",
            {"unidades": [u(m, 1, deuda(7, date(2026, 11, 1), date(2026, 10, 10), "100.00"))]},
        ),
        ("migracion_futura", "fecha_de_migracion", {"fecha": date(2026, 11, 12)}),
        (
            "periodo_con_solo_interes",
            "interes_acumulado",
            {
                "unidades": [
                    u(m, 1, deuda(7, date(2026, 7, 1), date(2026, 7, 10), "0.00", interes="500.00"))
                ]
            },
        ),
        (
            "total_sin_capital",
            "interes_acumulado",
            {"unidades": [u(m, 1, FilaDeTotal(7, d("0.00"), d("500.00")), modo="total")]},
        ),
        (
            "importe_de_deuda_negativo",
            "importe",
            {"unidades": [u(m, 1, deuda(7, SEP, sep, "-100.00"))]},
        ),
        ("credito_en_cero", "importe", {"unidades": [u(m, 3, FilaDeCredito(30, d("0.00")))]}),
        ("credito_negativo", "importe", {"unidades": [u(m, 3, FilaDeCredito(30, d("-5.00")))]}),
        (
            "unidad_repetida",
            "unidades",
            {
                "unidades": [
                    u(m, 1, deuda(7, AGO, date(2026, 8, 10), "80000.00")),
                    u(m, 1, deuda(8, SEP, sep, "85000.00")),
                ]
            },
        ),
        ("unidad_sin_filas", "unidades", {"unidades": [septiembre(m, 1), u(m, 2)]}),
        ("sin_unidades", "unidades", {"unidades": []}),
        (
            "total_en_una_unidad_de_detalle",
            "fila",
            {
                "unidades": [
                    u(m, 1, deuda(7, SEP, sep, "85000.00"), FilaDeTotal(8, d("1.00"), d("0.00")))
                ]
            },
        ),
        (
            "deuda_en_una_unidad_de_total",
            "fila",
            {"unidades": [u(m, 1, deuda(7, SEP, sep, "85000.00"), modo="total")]},
        ),
        (
            "fila_repetida_entre_unidades",
            "fila",
            {
                "unidades": [
                    u(m, 1, deuda(7, AGO, date(2026, 8, 10), "80000.00")),
                    u(m, 2, deuda(7, SEP, sep, "85000.00")),
                ]
            },
        ),
        (
            "fila_repetida_dentro_de_la_unidad",
            "fila",
            {
                "unidades": [
                    u(m, 1, deuda(7, AGO, date(2026, 8, 10), "1.00"), FilaDeCredito(7, d("1.00")))
                ]
            },
        ),
        ("manual_sin_motivo", "motivo", {"origen": OrigenDeCarga("manual", motivo="   ")}),
        ("importador_sin_archivo", "archivo", {"origen": OrigenDeCarga("importador", archivo="")}),
        (
            "importador_sin_numero_de_fila",
            "fila",
            {"unidades": [u(m, 1, deuda(None, SEP, sep, "85000.00"))]},
        ),
    ]


def test_cada_rechazo_nombra_su_campo_y_no_escribe_nada(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """6.1: cada caso falla por su aserción de campo; ningún INSERT, en la misma transacción."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        escrituras = contar_escrituras(s)
        antes = conteos(s)
        for nombre, campo, kw in _casos_invalidos(mundo):
            pedido = {"unidades": [septiembre(mundo)], **kw}
            with pytest.raises(EntradaInvalida) as e:
                cargar(s, mundo, **pedido)
            assert e.value.campo == campo, f"{nombre}: nombró {e.value.campo!r}, no {campo!r}"
            assert escrituras == [], f"{nombre}: escribió {escrituras}"
            assert conteos(s) == antes, nombre


def test_el_vencimiento_en_el_dia_de_la_migracion_entra(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Borde del mutante "aceptar vencimiento igual a la migración + 1 día": el día exacto entra."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [u(mundo, 1, deuda(7, OCT, MIGRACION, "100.00"))])
        (o,) = obligaciones(s, cuenta_de(s, mundo.unidades[1]))
        assert o.vencimiento == MIGRACION


def test_el_vencimiento_se_compara_en_cada_fila_no_solo_en_la_primera(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Mutante "tomar el vencimiento de la primera fila cuando difieren": la segunda fila de otro
    período vence después de la migración y tiene que rechazarse."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        with pytest.raises(EntradaInvalida) as e:
            cargar(
                s,
                mundo,
                [
                    u(
                        mundo,
                        1,
                        deuda(7, AGO, date(2026, 8, 10), "80000.00"),
                        deuda(8, OCT, date(2026, 10, 20), "85000.00"),
                    )
                ],
            )
        assert e.value.campo == "vencimiento"


def test_fila_de_solo_interes_junto_a_otra_con_capital_entra(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Mutante "validar el capital por fila en vez de por período": la fila 14 (capital 0) entra."""
    sep = date(2026, 9, 10)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [
                u(
                    mundo,
                    6,
                    deuda(14, SEP, sep, "0.00", interes="500.00"),
                    deuda(15, SEP, sep, "10000.00"),
                )
            ],
        )
        (o,) = obligaciones(s, cuenta_de(s, mundo.unidades[6]))
        assert (o.ord, o.fon, o.ext) == ("10000.00", "0.00", "0.00")
        (i,) = intereses(s, o.id)
        assert (i.importe, i.corte) == ("500.00", MIGRACION)


def test_la_transaccion_sigue_usable_despues_de_un_rechazo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        with pytest.raises(EntradaInvalida):
            cargar(s, mundo, [u(mundo, 1, deuda(7, SEP, date(2026, 9, 10), "-1.00"))])
        cargar(s, mundo, [septiembre(mundo)])
        assert conteos(s)["carga_de_saldo_inicial"] == 1


# --- 6.2 · Registro -----------------------------------------------------------------------------


def test_dos_conceptos_del_mismo_periodo_son_una_obligacion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Mutante "una obligación por fila": quedan dos, o choca con `uq_obligacion_operacion`."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [dos_conceptos(mundo)])
        cuenta = cuenta_de(s, mundo.unidades[5])
        (o,) = obligaciones(s, cuenta)
        assert (o.periodo, o.ord, o.ext, o.fon, o.emision_id) == (
            SEP,
            "85000.00",
            "20000.00",
            "0.00",
            None,
        )
        assert o.operacion_id is not None


def test_el_interes_importado_es_un_debito_de_interes_con_corte_en_la_migracion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Mutante "el interés entra en otro componente": entraría en la base de R03."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [dos_conceptos(mundo)])
        cuenta = cuenta_de(s, mundo.unidades[5])
        (o,) = obligaciones(s, cuenta)
        (i,) = intereses(s, o.id)
        assert (i.importe, i.corte, i.componente, i.emision_id, i.operacion_id) == (
            "3000.00",
            MIGRACION,
            "interes",
            None,
            None,
        )
        assert (
            s.execute(
                text("SELECT count(*) FROM tramo_de_interes WHERE movimiento_id = :m"), {"m": i.id}
            ).scalar_one()
            == 0
        ), "el interés importado no se recalcula: no lleva tramos"
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert e.deuda == d("108000.00")


def test_el_interes_importado_suma_las_filas_del_periodo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    sep = date(2026, 9, 10)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [
                u(
                    mundo,
                    5,
                    deuda(12, SEP, sep, "85000.00", interes="3000.00"),
                    deuda(13, SEP, sep, "20000.00", interes="1250.50"),
                )
            ],
        )
        (o,) = obligaciones(s, cuenta_de(s, mundo.unidades[5]))
        (i,) = intereses(s, o.id)
        assert i.importe == "4250.50"


def test_total_unico_vence_en_la_migracion_con_todo_en_ordinaria(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = cargar(
            s,
            mundo,
            [
                u(
                    mundo,
                    2,
                    FilaDeTotal(20, d("30000.00"), d("1500.00")),
                    FilaDeTotal(21, d("20000.00"), d("500.00")),
                    modo="total",
                )
            ],
        )
        cuenta = cuenta_de(s, mundo.unidades[2])
        (o,) = obligaciones(s, cuenta)
        assert (o.periodo, o.vencimiento, o.ord, o.fon, o.ext) == (
            OCT,
            MIGRACION,
            "50000.00",
            "0.00",
            "0.00",
        )
        (i,) = intereses(s, o.id)
        assert i.importe == "2000.00"
        assert filas_de(origenes(s, cuenta), obligacion=o.id) == {20, 21}
        assert filas_de(origenes(s, cuenta), movimiento=i.id) == {20, 21}
        assert r.total.capital == d("50000.00")


def test_el_credito_se_imputa_a_la_deuda_con_r04(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Mutante "el crédito no se imputa": la unidad seguiría debiendo $10.000."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [
                u(
                    mundo,
                    4,
                    deuda(40, SEP, date(2026, 9, 10), "10000.00"),
                    FilaDeCredito(41, d("1000.00")),
                    FilaDeCredito(42, d("2000.00")),
                )
            ],
        )
        cuenta = cuenta_de(s, mundo.unidades[4])
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (e.deuda, e.credito_a_favor) == (d("7000.00"), d("0.00"))
        (m,) = s.execute(
            text(
                "SELECT importe::text AS importe, fecha_valor, operacion_id FROM movimiento "
                "WHERE cuenta_id = :c AND tipo = 'saldo_inicial'"
            ),
            {"c": cuenta},
        ).all()
        assert (m.importe, m.fecha_valor) == ("3000.00", MIGRACION)


def test_unidad_con_saldo_a_favor_y_cuenta_sin_deuda(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [u(mundo, 3, FilaDeCredito(30, d("3000.00")))])
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta_de(s, mundo.unidades[3]))
        assert (e.deuda, e.credito_a_favor_aplicable) == (d("0.00"), d("3000.00"))


def test_el_origen_liga_cada_fila_a_lo_que_formo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Mutantes "el origen se liga a otra fila" y "el interés se liga a todas las filas del período"."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [dos_conceptos(mundo)])
        cuenta = cuenta_de(s, mundo.unidades[5])
        (o,) = obligaciones(s, cuenta)
        (i,) = intereses(s, o.id)
        orig = origenes(s, cuenta)
        assert filas_de(orig, obligacion=o.id) == {12, 13}
        assert filas_de(orig, movimiento=i.id) == {12}
        assert {x.sentido_del_movimiento for x in orig if x.movimiento_id is not None} == {"debito"}


def test_una_fila_de_solo_interes_se_liga_al_interes_y_no_a_la_obligacion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    sep = date(2026, 9, 10)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [
                u(
                    mundo,
                    6,
                    deuda(14, SEP, sep, "0.00", interes="500.00"),
                    deuda(15, SEP, sep, "10000.00"),
                )
            ],
        )
        cuenta = cuenta_de(s, mundo.unidades[6])
        (o,) = obligaciones(s, cuenta)
        (i,) = intereses(s, o.id)
        orig = origenes(s, cuenta)
        assert filas_de(orig, obligacion=o.id) == {15}
        assert filas_de(orig, movimiento=i.id) == {14}


def test_el_origen_del_credito_y_la_carga_manual(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    motivo = "  Saldos del cuaderno del administrador anterior "
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [
                u(
                    mundo,
                    4,
                    deuda(None, SEP, date(2026, 9, 10), "10000.00"),
                    FilaDeCredito(None, d("3000.00")),
                )
            ],
            origen=OrigenDeCarga("manual", motivo=motivo, archivo="ignorado.xlsx"),
        )
        carga = s.execute(
            text("SELECT origen, archivo, motivo, firma_del_pedido FROM carga_de_saldo_inicial")
        ).one()
        assert (carga.origen, carga.archivo, carga.motivo) == (
            "manual",
            None,
            "Saldos del cuaderno del administrador anterior",
        )
        assert carga.firma_del_pedido.startswith("v1:")
        orig = origenes(s, cuenta_de(s, mundo.unidades[4]))
        assert len(orig) == 2 and {x.fila for x in orig} == {None}


def test_devuelve_cuentas_y_totales(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    op = uuid4()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = cargar(
            s,
            mundo,
            [
                dos_conceptos(mundo),
                u(
                    mundo,
                    4,
                    deuda(40, SEP, date(2026, 9, 10), "10000.00"),
                    FilaDeCredito(41, d("3000.00")),
                ),
            ],
            operacion_id=op,
        )
        assert r.operacion_id == op
        assert r.cuentas == {
            mundo.unidades[5]: cuenta_de(s, mundo.unidades[5]),
            mundo.unidades[4]: cuenta_de(s, mundo.unidades[4]),
        }
        assert {
            k: (v.capital, v.interes_importado, v.credito) for k, v in r.por_unidad.items()
        } == {
            mundo.unidades[5]: (d("105000.00"), d("3000.00"), d("0.00")),
            mundo.unidades[4]: (d("10000.00"), d("0.00"), d("3000.00")),
        }
        assert (r.total.capital, r.total.interes_importado, r.total.credito) == (
            d("115000.00"),
            d("3000.00"),
            d("3000.00"),
        )
        carga = s.execute(text("SELECT id FROM carga_de_saldo_inicial")).scalar_one()
        assert r.carga_id == carga


# --- 6.4 · Estado de migración, carga única, replay y tenant ------------------------------------


@pytest.mark.parametrize("estado", ["sin_saldos_previos", "confirmada"])
def test_solo_se_carga_con_la_migracion_pendiente(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, estado: str
) -> None:
    """Mutante "sin el chequeo de `pendiente`": el edificio cerrado registraría."""
    poner_estado(base_del_edificio, mundo, estado)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        antes = conteos(s)
        with pytest.raises(Conflicto) as e:
            cargar(s, mundo, [septiembre(mundo)])
        assert e.value.campo == "estado_migracion"
        assert conteos(s) == antes


def test_segunda_carga_con_otra_operacion(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Mutante "sin el único por edificio": quedarían dos cargas."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [septiembre(mundo, 1)])
        s.commit()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        antes = conteos(s)
        with pytest.raises(Conflicto):
            cargar(s, mundo, [septiembre(mundo, 2, fila=9)])
        assert conteos(s) == antes
        assert antes["carga_de_saldo_inicial"] == 1


def test_dos_cargas_simultaneas_una_registra_y_la_otra_es_conflicto(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    largada = threading.Barrier(2, timeout=30)

    def una_carga(n: int) -> SaldoInicialRegistrado:
        with sesion_app(base_del_edificio, mundo.admin) as s:
            pedido = [septiembre(mundo, n, fila=n)]
            largada.wait()
            r = cargar(s, mundo, pedido)
            s.commit()
            return r

    hilos = [en_hilo(functools.partial(una_carga, n)) for n in (1, 2)]
    for hilo, _ in hilos:
        hilo.join(60)
        assert not hilo.is_alive(), "una carga quedó colgada"
    entraron = [r for _, r in hilos if "valor" in r]
    errores = [r["error"] for _, r in hilos if "error" in r]
    assert len(entraron) == 1, f"se esperaba una sola carga, hay {len(entraron)}: {errores}"
    assert len(errores) == 1 and isinstance(errores[0], Conflicto), repr(errores)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        assert conteos(s)["carga_de_saldo_inicial"] == 1


def _foto(r: SaldoInicialRegistrado) -> tuple[Any, ...]:
    return (
        r.operacion_id,
        r.cuentas,
        {k: (v.capital, v.interes_importado, v.credito) for k, v in r.por_unidad.items()},
        (r.total.capital, r.total.interes_importado, r.total.credito),
    )


def test_replay_despues_de_confirmar_devuelve_lo_registrado(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Mutante "replay después del chequeo de estado": con la migración `confirmada` da conflicto."""
    op = uuid4()
    pedido = [dos_conceptos(mundo), septiembre(mundo, 1)]
    with sesion_app(base_del_edificio, mundo.admin) as s:
        primera = cargar(s, mundo, pedido, operacion_id=op)
        s.commit()
    poner_estado(base_del_edificio, mundo, "confirmada")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        antes = conteos(s)
        segunda = cargar(s, mundo, pedido, operacion_id=op)
        assert conteos(s) == antes, "el replay escribió"
        assert _foto(segunda) == _foto(primera)
        assert segunda.carga_id == primera.carga_id


def test_mismo_pedido_en_otro_orden_y_con_importes_sin_decimales_es_replay(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Mutante "la firma sin ordenar unidades y filas": el otro orden daría conflicto."""
    op = uuid4()
    sep = date(2026, 9, 10)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        primera = cargar(s, mundo, [dos_conceptos(mundo), septiembre(mundo, 1)], operacion_id=op)
        antes = conteos(s)
        al_reves = [
            septiembre(mundo, 1),
            u(
                mundo,
                5,
                deuda(13, SEP, sep, "20000", componente="extraordinaria"),
                deuda(12, SEP, sep, "85000", interes="3000"),
            ),
        ]
        segunda = cargar(s, mundo, al_reves, operacion_id=op)
        assert conteos(s) == antes
        assert _foto(segunda) == _foto(primera)


def test_misma_operacion_con_otros_datos_es_conflicto_en_operacion_id(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    op = uuid4()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [dos_conceptos(mundo)], operacion_id=op)
        s.commit()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        antes = conteos(s)
        with pytest.raises(Conflicto) as e:
            cargar(s, mundo, [dos_conceptos(mundo, b="20001.00")], operacion_id=op)
        assert e.value.campo == "operacion_id"
        assert conteos(s) == antes


def test_misma_operacion_con_iguales_sumas_y_otras_filas_es_conflicto(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Mutante "la firma sobre las sumas por período y componente": daría replay."""
    op = uuid4()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [dos_conceptos(mundo, "85000.00", "20000.00")], operacion_id=op)
        s.commit()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        antes = conteos(s)
        with pytest.raises(Conflicto) as e:
            cargar(s, mundo, [dos_conceptos(mundo, "84000.00", "21000.00")], operacion_id=op)
        assert e.value.campo == "operacion_id"
        assert conteos(s) == antes


def test_unidad_de_otro_edificio_no_se_encuentra_y_no_deja_nada(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        antes = conteos(s)
        pedido = [
            septiembre(mundo, 1),
            UnidadDeSaldoInicial(
                mundo.unidad_otro_complejo, "detalle", (deuda(9, SEP, date(2026, 9, 10), "1.00"),)
            ),
        ]
        with pytest.raises(NoEncontrado):
            cargar(s, mundo, pedido)
        assert conteos(s) == antes, "lo escrito antes de fallar vuelve con el SAVEPOINT"
        cargar(s, mundo, [septiembre(mundo, 1)])  # la transacción sigue usable


def test_edificio_de_otra_administracion_no_se_encuentra(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        antes = conteos(s)
        pedido = [
            UnidadDeSaldoInicial(
                mundo.unidad_b, "detalle", (deuda(7, SEP, date(2026, 9, 10), "1.00"),)
            )
        ]
        with pytest.raises(NoEncontrado):
            cargar(s, mundo, pedido, complejo=mundo.complejo_b)
        assert conteos(s) == antes


def test_otra_administracion_no_ve_la_carga(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [septiembre(mundo, 1)])
        s.commit()
    with sesion_app(base_del_edificio, mundo.admin_b) as s:
        assert conteos(s)["carga_de_saldo_inicial"] == 0
        assert conteos(s)["origen_de_saldo_inicial"] == 0


def test_la_identidad_de_otra_administracion_no_carga(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    from proptech_core.cuenta_corriente.aplicacion.errores import IdentidadDeOtraAdministracion

    with (
        sesion_app(base_del_edificio, mundo.admin) as s,
        pytest.raises(IdentidadDeOtraAdministracion),
    ):
        registrar_saldo_inicial(
            s,
            mundo.identidad_b,
            complejo_id=mundo.complejo,
            operacion_id=uuid4(),
            fecha_de_migracion=MIGRACION,
            origen=importador(),
            unidades=[septiembre(mundo)],
            request_id=uuid4(),
            reloj=reloj(),
        )


def test_sin_transaccion_abierta(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    from proptech_core.cuenta_corriente.aplicacion.errores import RegistroFueraDeTransaccion

    with sesion_app(base_del_edificio, mundo.admin, comenzar=False) as s:
        with pytest.raises(RegistroFueraDeTransaccion):
            cargar(s, mundo, [septiembre(mundo)])
