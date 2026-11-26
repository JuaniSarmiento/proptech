"""El prorrateo por días de la expensa del mes del cambio (R32, D-168.5). Reglas puras.

El vendedor responde por los días del mes anteriores a la fecha del cambio (el día del cambio es del
comprador). Por cada componente de la obligación del mes (ordinaria, fondo de reserva y
extraordinaria, nunca el interés) su parte es `componente * días del vendedor / días del mes`
redondeada medio hacia arriba al centavo; la unidad conserva el resto, así la suma es exacta.
Todo en enteros de centavos: ningún `float` ni redondeo intermedio.
"""

import calendar
from datetime import date

from proptech_core.compartido.dinero import Dinero

_CERO = Dinero("0.00")


def dias_del_vendedor(fecha: date) -> int:
    """Los días del mes anteriores a `fecha`: vendió el 11, son 10; el día 1 son 0."""
    return fecha.day - 1


def dias_del_mes(fecha: date) -> int:
    return calendar.monthrange(fecha.year, fecha.month)[1]


def _centavos(monto: Dinero) -> int:
    return int(monto.decimal * 100)


def _desde_centavos(centavos: int) -> Dinero:
    return Dinero(f"{centavos // 100}.{centavos % 100:02d}")


def parte_por_dias(componente: Dinero, dias: int, del_mes: int) -> Dinero:
    """`componente * dias / del_mes` al centavo, medio hacia arriba (componente no negativo)."""
    if not 0 <= dias <= del_mes or del_mes < 1 or componente < _CERO:
        raise ValueError("días fuera del mes o componente negativo")
    return _desde_centavos((2 * _centavos(componente) * dias + del_mes) // (2 * del_mes))


def parte_a_trasladar(emitido: Dinero, impago: Dinero, dias: int, del_mes: int) -> Dinero:
    """Lo que se traslada de un componente: su parte por días menos lo que la unidad ya pagó de él
    (un pago se entiende imputado primero a los días del vendedor), `max(parte - pagado, 0)`."""
    pagado = emitido - impago
    if pagado < _CERO:  # un ajuste de más sobre el componente: nada pagado a cuenta de la parte
        pagado = _CERO
    resto = parte_por_dias(emitido, dias, del_mes) - pagado
    return resto if resto > _CERO else _CERO
