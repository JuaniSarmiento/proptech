"""R04 a la fecha de la transferencia (D-166, change 8), sin base.

Un pago confirmado tarde se imputa como si se hubiera confirmado el día de la transferencia: primero
lo que ya se debía ese día (fase 1), después lo que se debe hoy (fase 2). Quién existía ese día lo
decide el llamador al armar `deudas_a_la_fecha`; acá sólo se aplica R04 dos veces.
"""

from collections.abc import Iterable

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.imputacion import Deuda, Imputacion, imputar

_CERO = Dinero("0.00")


def imputar_pago_a_la_fecha(
    deudas_a_la_fecha: Iterable[Deuda], deudas_reales: Iterable[Deuda], importe: Dinero
) -> tuple[list[Imputacion], Dinero]:
    """Devuelve las imputaciones (fase 1 y después fase 2, un solo renglón por destino) y el
    sobrante, que queda como crédito a favor (R05).

    `deudas_a_la_fecha`: lo pendiente calculado como si no existieran las emisiones posteriores a
    la fecha. `deudas_reales`: lo pendiente hoy. La fase 2 trabaja sobre lo real menos lo imputado
    en la fase 1, sin bajar de cero."""
    primeras, resto = imputar(deudas_a_la_fecha, importe)
    imputado: dict[tuple[object, object], Dinero] = {}
    for i in primeras:
        imputado[(i.obligacion_id, i.componente)] = i.importe
    pendientes = []
    for d in deudas_reales:
        quedan = d.residual - imputado.get((d.obligacion_id, d.componente), _CERO)
        if quedan > _CERO:
            pendientes.append(
                Deuda(d.obligacion_id, d.componente, d.periodo, d.vencimiento, quedan)
            )
    segundas: list[Imputacion] = []
    if resto > _CERO:
        segundas, resto = imputar(pendientes, resto)
    juntas: dict[tuple[object, object], Imputacion] = {}
    for i in [*primeras, *segundas]:
        clave = (i.obligacion_id, i.componente)
        previa = juntas.get(clave)
        juntas[clave] = (
            i
            if previa is None
            else Imputacion(i.obligacion_id, i.componente, previa.importe + i.importe)
        )
    return list(juntas.values()), resto
