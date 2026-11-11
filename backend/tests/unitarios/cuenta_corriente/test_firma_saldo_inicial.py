"""6.4 · La firma del pedido normalizado (design D5, PR-11, E16): pura, sin base.

El replay compara por esta firma, no por lo que quedó en el libro: agrupar pierde el aporte de cada
fila. Cada test afirma una propiedad de la firma; los mutantes de la tarea los vigilan por nombre.
"""

import re
from dataclasses import replace
from datetime import date
from typing import Any
from uuid import UUID

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.saldo_inicial import (
    FilaDeCredito,
    FilaDeDeuda,
    FilaDeTotal,
    OrigenDeCarga,
    UnidadDeSaldoInicial,
    firmar_pedido,
    normalizar_pedido,
)

HOY = date(2026, 11, 11)
MIGRACION = date(2026, 10, 15)
EDIFICIO = UUID("00000000-0000-0000-0000-0000000000e1")
U1 = UUID("00000000-0000-0000-0000-000000000001")
U5 = UUID("00000000-0000-0000-0000-000000000005")
SEP = date(2026, 9, 1)
AGO = date(2026, 8, 1)


def d(t: str) -> Dinero:
    return Dinero(t)


def deuda(
    fila: int | None, importe: str, *, interes: str = "0.00", componente: str = "ordinaria"
) -> FilaDeDeuda:
    return FilaDeDeuda(fila, SEP, date(2026, 9, 10), componente, d(importe), d(interes))


def u5(
    a: str = "85000.00", b: str = "20000.00", interes12: str = "3000.00"
) -> UnidadDeSaldoInicial:
    return UnidadDeSaldoInicial(
        U5, "detalle", (deuda(12, a, interes=interes12), deuda(13, b, componente="extraordinaria"))
    )


def u1() -> UnidadDeSaldoInicial:
    return UnidadDeSaldoInicial(
        U1,
        "detalle",
        (
            FilaDeDeuda(7, AGO, date(2026, 8, 10), "ordinaria", d("80000.00"), d("0.00")),
            deuda(8, "85000.00"),
        ),
    )


def firma(
    unidades: list[UnidadDeSaldoInicial] | None = None,
    *,
    origen: OrigenDeCarga | None = None,
    complejo: UUID = EDIFICIO,
    fecha: date = MIGRACION,
) -> str:
    pedido = normalizar_pedido(
        complejo_id=complejo,
        fecha_de_migracion=fecha,
        origen=origen or OrigenDeCarga("importador", archivo="saldos-octubre.xlsx"),
        unidades=tuple(unidades if unidades is not None else [u1(), u5()]),
        hoy=HOY,
    )
    return firmar_pedido(pedido)


def test_la_firma_tiene_el_formato_que_exige_la_base() -> None:
    assert re.fullmatch(r"v1:[0-9a-f]{64}", firma())


def test_es_determinista() -> None:
    assert firma() == firma()


def test_mismo_pedido_en_otro_orden_da_la_misma_firma() -> None:
    """Escenario: Mismo pedido en otro orden (unidades y filas)."""
    al_reves = [
        replace(u5(), filas=tuple(reversed(u5().filas))),
        replace(u1(), filas=tuple(reversed(u1().filas))),
    ]
    assert firma(al_reves) == firma([u1(), u5()])


def test_el_importe_escrito_sin_decimales_da_la_misma_firma() -> None:
    assert firma([u5(a="85000", b="20000", interes12="3000")]) == firma([u5()])


def test_iguales_sumas_con_otras_filas_dan_otra_firma() -> None:
    """Escenario: iguales sumas y otras filas ($85.000/$20.000 frente a $84.000/$21.000)."""
    assert firma([u5(a="84000.00", b="21000.00")]) != firma([u5()])


def test_mover_interes_de_una_fila_a_otra_da_otra_firma() -> None:
    """La firma lleva el interés acumulado de cada fila: la suma por período no cambia."""
    original = UnidadDeSaldoInicial(
        U5, "detalle", (deuda(12, "85000.00", interes="3000.00"), deuda(13, "20000.00"))
    )
    movido = UnidadDeSaldoInicial(
        U5,
        "detalle",
        (deuda(12, "85000.00", interes="2000.00"), deuda(13, "20000.00", interes="1000.00")),
    )
    assert firma([movido]) != firma([original])


def _con_cambio(nombre: str) -> tuple[Any, ...]:
    base = u5()
    primera, segunda = base.filas
    assert isinstance(primera, FilaDeDeuda) and isinstance(segunda, FilaDeDeuda)
    cambios: dict[str, tuple[list[UnidadDeSaldoInicial], dict[str, Any]]] = {
        "numero_de_fila": ([replace(base, filas=(replace(primera, fila=14), segunda))], {}),
        "periodo": ([replace(base, filas=(replace(primera, periodo=AGO), segunda))], {}),
        "vencimiento": (
            [
                replace(
                    base,
                    filas=(
                        replace(primera, vencimiento=date(2026, 9, 9)),
                        replace(segunda, vencimiento=date(2026, 9, 9)),
                    ),
                )
            ],
            {},
        ),
        "componente": (
            [replace(base, filas=(replace(primera, componente="fondo_de_reserva"), segunda))],
            {},
        ),
        "importe": ([replace(base, filas=(replace(primera, importe=d("85000.01")), segunda))], {}),
        "interes": (
            [replace(base, filas=(replace(primera, interes_acumulado=d("3000.01")), segunda))],
            {},
        ),
        "fila_de_mas": ([replace(base, filas=(*base.filas, FilaDeCredito(14, d("1.00"))))], {}),
        "otra_unidad": ([replace(base, unidad_id=U1)], {}),
        "archivo": ([base], {"origen": OrigenDeCarga("importador", archivo="otro.xlsx")}),
        "origen_manual": (
            [base],
            {"origen": OrigenDeCarga("manual", motivo="saldos-octubre.xlsx")},
        ),
        "edificio": ([base], {"complejo": UUID(int=99)}),
        "fecha": ([base], {"fecha": date(2026, 10, 14)}),
    }
    return cambios[nombre]


@pytest.mark.parametrize(
    "nombre",
    [
        "numero_de_fila",
        "periodo",
        "vencimiento",
        "componente",
        "importe",
        "interes",
        "fila_de_mas",
        "otra_unidad",
        "archivo",
        "origen_manual",
        "edificio",
        "fecha",
    ],
)
def test_cualquier_dato_distinto_cambia_la_firma(nombre: str) -> None:
    unidades, kw = _con_cambio(nombre)
    assert firma(unidades, **kw) != firma([u5()])


def test_el_modo_cambia_la_firma() -> None:
    en_total = UnidadDeSaldoInicial(U5, "total", (FilaDeTotal(12, d("85000.00"), d("0.00")),))
    en_detalle = UnidadDeSaldoInicial(U5, "detalle", (deuda(12, "85000.00"),))
    assert firma([en_total]) != firma([en_detalle])


def test_el_credito_cuenta_en_la_firma() -> None:
    sin = UnidadDeSaldoInicial(U1, "detalle", (deuda(8, "85000.00"),))
    con = UnidadDeSaldoInicial(U1, "detalle", (deuda(8, "85000.00"), FilaDeCredito(9, d("100.00"))))
    assert firma([con]) != firma([sin])


def test_el_archivo_se_normaliza_antes_de_firmar() -> None:
    """El origen entra ya normalizado: espacios de más no hacen otra firma."""
    assert firma(
        [u5()], origen=OrigenDeCarga("importador", archivo="  saldos-octubre.xlsx ")
    ) == firma([u5()])
