"""H-005 · C13 a C18: lo que la carga rechaza sin escribir nada (spec `saldo-inicial`, design D5).

Cada rechazo se mide en la misma transacción: el caso de uso valida antes de escribir o deshace lo
suyo en un SAVEPOINT, así el llamador (el 5) puede seguir usando su transacción."""

from __future__ import annotations

import functools
import threading
from typing import Any
from uuid import UUID, uuid4

import pytest

from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
    RegistroFueraDeTransaccion,
)

from .._cuenta_corriente import Mundo, en_hilo, sembrar, sesion_app
from .._edificios import BaseDeEdificio
from ._h005 import (
    AGO,
    SEP,
    campo,
    cargar,
    cargas,
    conexion_app,
    conteos,
    credito,
    deuda,
    dia,
    importador,
    manual,
    modulo,
    poner_estado,
    total,
    unidad,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def u(mundo: Mundo, n: int) -> UUID:
    return mundo.unidades[n]


def septiembre(mundo: Mundo, n: int = 1, fila: int = 8) -> Any:
    return unidad(u(mundo, n), deuda(fila, SEP, dia(9, 10), "85000.00"))


def rechaza(
    base: BaseDeEdificio,
    mundo: Mundo,
    error: type[BaseException],
    nombre_del_campo: str | None,
    unidades: list[Any] | None = None,
    **kw: Any,
) -> None:
    """El pedido se rechaza con `error` (y su `campo`, si se nombra) y el libro no cambia."""
    with sesion_app(base, mundo.admin) as s:
        modulo()
        antes = conteos(s)
        pedido = unidades if unidades is not None else [septiembre(mundo)]
        with pytest.raises(error) as e:
            cargar(s, mundo, pedido, confirmar=False, **kw)
        if nombre_del_campo is not None:
            assert campo(e.value) == nombre_del_campo, (
                f"se rechazó nombrando {campo(e.value)!r}, no {nombre_del_campo!r}"
            )
        assert conteos(s) == antes, "el rechazo escribió en el libro"


# --- C13 · Estado de migración y una sola carga ----------------------------------------------


def test_c13_edificio_sin_saldos_previos(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Edificio sin saldos previos"""
    poner_estado(base_del_edificio, mundo, "sin_saldos_previos")
    rechaza(base_del_edificio, mundo, Conflicto, "estado_migracion")


def test_c13_importador_cerrado_sin_carga_previa(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Importador cerrado sin carga previa"""
    poner_estado(base_del_edificio, mundo, "confirmada")
    rechaza(base_del_edificio, mundo, Conflicto, "estado_migracion")


def test_c13_segunda_carga_con_otra_operacion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Segunda carga con otra operación"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [septiembre(mundo, 1)])
        s.commit()
    rechaza(base_del_edificio, mundo, Conflicto, None, [septiembre(mundo, 2, fila=9)])
    with sesion_app(base_del_edificio, mundo.admin) as s:
        assert len(cargas(s)) == 1


def test_c13_dos_cargas_simultaneas(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Dos cargas simultáneas"""
    modulo()
    largada = threading.Barrier(2, timeout=30)

    def una_carga(n: int) -> Any:
        with sesion_app(base_del_edificio, mundo.admin) as s:
            pedido = [septiembre(mundo, n, fila=n)]
            largada.wait()
            r = cargar(s, mundo, pedido, confirmar=False)
            s.commit()
            return r

    hilos = [en_hilo(functools.partial(una_carga, n)) for n in (1, 2)]
    for hilo, _ in hilos:
        hilo.join(60)
        assert not hilo.is_alive(), "una carga quedó colgada"
    resultados = [r for _, r in hilos]
    entraron = [r for r in resultados if "valor" in r]
    errores = [r["error"] for r in resultados if "error" in r]
    assert len(entraron) == 1, (
        f"se esperaba una sola carga registrada, hay {len(entraron)}: {errores}"
    )
    assert len(errores) == 1 and isinstance(errores[0], Conflicto), (
        f"la otra tenía que dar Conflicto, dio {errores!r}"
    )
    with sesion_app(base_del_edificio, mundo.admin) as s:
        assert len(cargas(s)) == 1


# --- C14 · Fechas ---------------------------------------------------------------------------


def test_c14_vencimiento_futuro(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Vencimiento futuro"""
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "vencimiento",
        [unidad(u(mundo, 1), deuda(7, dia(10, 1), dia(10, 20), "85000.00"))],
    )


def test_c14_periodo_que_no_empieza_el_dia_1(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "periodo",
        [unidad(u(mundo, 1), deuda(7, dia(9, 5), dia(9, 10), "85000.00"))],
    )


def test_c14_periodo_posterior_al_mes_de_migracion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "periodo",
        [unidad(u(mundo, 1), deuda(7, dia(11, 1), dia(10, 10), "85000.00"))],
    )


def test_c14_migracion_en_el_futuro(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "fecha_de_migracion",
        fecha=dia(11, 12),
        hoy=dia(11, 11),
    )


def test_c14_mismo_periodo_con_vencimientos_distintos(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Mismo período con vencimientos distintos"""
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "vencimiento",
        [
            unidad(
                u(mundo, 5),
                deuda(12, SEP, dia(9, 10), "85000.00", interes="3000.00"),
                deuda(13, SEP, dia(9, 15), "20000.00", componente="extraordinaria"),
            )
        ],
    )


# --- C15 · Montos ---------------------------------------------------------------------------


def test_c15_periodo_con_solo_interes(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Período con sólo interés"""
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "interes_acumulado",
        [unidad(u(mundo, 1), deuda(7, dia(7, 1), dia(7, 10), "0.00", interes="500.00"))],
    )


def test_c15_importe_negativo(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "importe",
        [unidad(u(mundo, 1), deuda(7, SEP, dia(9, 10), "-100.00"))],
    )


def test_c15_credito_en_cero(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "importe",
        [unidad(u(mundo, 3), credito(30, "0.00"))],
    )


# --- C16 · Forma del pedido -------------------------------------------------------------------


def test_c16_unidad_repetida(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Unidad repetida"""
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "unidades",
        [
            unidad(u(mundo, 1), deuda(7, AGO, dia(8, 10), "80000.00")),
            unidad(u(mundo, 1), deuda(8, SEP, dia(9, 10), "85000.00")),
        ],
    )


def test_c16_unidad_sin_filas(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "unidades",
        [septiembre(mundo, 1), unidad(u(mundo, 2))],
    )


def test_c16_unidad_que_mezcla_detalle_y_total(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "fila",
        [unidad(u(mundo, 1), deuda(7, SEP, dia(9, 10), "85000.00"), total(8, "1000.00"))],
    )


def test_c16_fila_repetida(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Fila repetida"""
    rechaza(
        base_del_edificio,
        mundo,
        EntradaInvalida,
        "fila",
        [
            unidad(u(mundo, 1), deuda(7, AGO, dia(8, 10), "80000.00")),
            unidad(u(mundo, 2), deuda(7, SEP, dia(9, 10), "85000.00")),
        ],
    )


def test_c16_carga_manual_sin_motivo(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Carga manual sin motivo"""
    rechaza(base_del_edificio, mundo, EntradaInvalida, "motivo", origen=manual("   "))


def test_c16_importador_sin_archivo(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    rechaza(base_del_edificio, mundo, EntradaInvalida, "archivo", origen=importador(""))


# --- C17 · El mismo operacion_id con otro pedido ---------------------------------------------


def _dos_filas_de_u5(mundo: Mundo, a: str, b: str) -> list[Any]:
    return [
        unidad(
            u(mundo, 5),
            deuda(12, SEP, dia(9, 10), a, interes="3000.00"),
            deuda(13, SEP, dia(9, 10), b),
        )
    ]


def test_c17_misma_operacion_con_otros_datos(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Misma operación con otros datos"""
    op = uuid4()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, _dos_filas_de_u5(mundo, "85000.00", "20000.00"), operacion_id=op)
        s.commit()
    rechaza(
        base_del_edificio,
        mundo,
        Conflicto,
        "operacion_id",
        _dos_filas_de_u5(mundo, "85000.00", "20001.00"),
        operacion_id=op,
    )


def test_c17_misma_operacion_con_iguales_sumas_y_otras_filas(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Misma operación con iguales sumas y otras filas"""
    op = uuid4()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, _dos_filas_de_u5(mundo, "85000.00", "20000.00"), operacion_id=op)
        s.commit()
    rechaza(
        base_del_edificio,
        mundo,
        Conflicto,
        "operacion_id",
        _dos_filas_de_u5(mundo, "84000.00", "21000.00"),
        operacion_id=op,
    )


# --- C18 · Tenant y transacción ---------------------------------------------------------------


def test_c18_unidad_de_otro_edificio(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Unidad de otro edificio"""
    rechaza(
        base_del_edificio,
        mundo,
        NoEncontrado,
        None,
        [unidad(mundo.unidad_otro_complejo, deuda(7, SEP, dia(9, 10), "85000.00"))],
    )


def test_c18_edificio_de_otra_administracion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    rechaza(
        base_del_edificio,
        mundo,
        NoEncontrado,
        None,
        [unidad(mundo.unidad_b, deuda(7, SEP, dia(9, 10), "85000.00"))],
        complejo=mundo.complejo_b,
    )


def test_c18_otra_administracion_no_ve_la_carga(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Otra administración no ve la carga"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [septiembre(mundo, 1)])
        s.commit()
    with conexion_app(base_del_edificio, mundo.admin) as c:
        propias = [
            c.execute(f"SELECT count(*) FROM {t}").fetchone()  # noqa: S608 - fijas
            for t in ("carga_de_saldo_inicial", "origen_de_saldo_inicial")
        ]
        assert all(p is not None and p[0] >= 1 for p in propias), "control: A ve lo suyo"
        c.rollback()
    with conexion_app(base_del_edificio, mundo.admin_b) as c:
        for tabla in ("carga_de_saldo_inicial", "origen_de_saldo_inicial"):
            fila = c.execute(f"SELECT count(*) FROM {tabla}").fetchone()  # noqa: S608 - fijas
            assert fila == (0,), f"la administración B ve filas de A en {tabla}"
        c.rollback()


def test_c18_sin_transaccion_abierta(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin, comenzar=False) as s:
        modulo()
        assert not s.in_transaction()
        with pytest.raises(RegistroFueraDeTransaccion):
            cargar(s, mundo, [septiembre(mundo)], confirmar=False)
