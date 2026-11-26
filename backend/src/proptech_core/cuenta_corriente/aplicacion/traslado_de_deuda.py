"""Trasladar deuda de la cuenta de una unidad a la cuenta de persona de un vendedor (4d, H-031, R32,
D-168.2).

Se arma con las piezas de la reimputación (`reversion_de_pago`): lo que se mueve entre dos cuentas
es un par de movimientos enlazados, con los candados de las dos tomados juntos y en orden, en la
transacción del llamador. Por cada obligación de la unidad con período anterior al mes de `fecha`
y por cada componente que tenga algo impago (capital o interés registrado):

1. en la unidad, un crédito `traslado` sobre esa obligación y ese componente, por lo impago, con su
   imputación directa (no pasa por R04: tiene destino y se imputa entero, así un pago posterior no
   se lo come ni queda a favor);
2. en la cuenta de persona, una obligación "contenedora" del mismo período y vencimiento, sin
   capital (`0051`), y un débito `traslado` del mismo importe sobre ella, enlazado al crédito
   (`enlazado_a`).

La deuda trasladada **no genera interés** (D-168.2a): el crédito se fecha al vencimiento de la
obligación, que es desde cuando el libro deja de contar la base de interés, y la emisión sólo
calcula sobre cuentas de unidad. Viaja con el capital y el interés ya registrados. La cuenta de
persona queda fuera de la morosidad y de la situación de cobranza, que son por unidad (D-167).

Dos cambios sobre la misma unidad no repiten: lo ya trasladado quedó imputado y no es residual.
"""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid4, uuid5

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.creditos import (
    Reloj,
    ahora_utc,
    imputar_pendientes,
    insertar_imputaciones,
)
from proptech_core.cuenta_corriente.aplicacion.cuentas import (
    bloquear_cuentas,
    exigir_identidad,
    tenant,
)
from proptech_core.cuenta_corriente.aplicacion.errores import exigir_transaccion, traducir
from proptech_core.cuenta_corriente.aplicacion.lecturas import (
    FotoDeCuenta,
    cuenta_de_unidad,
    foto,
)
from proptech_core.cuenta_corriente.aplicacion.reversion_de_pago import _insertar
from proptech_core.cuenta_corriente.dominio.estado import Obligacion
from proptech_core.cuenta_corriente.dominio.imputacion import Componente, Imputacion

_CERO = Dinero("0.00")
#: Fijo: de él sale el `operacion_id` de cada movimiento y obligación del traslado.
_ESPACIO_DE_TRASLADOS = UUID("5c1d8e3a-7b94-4f26-9a0e-3d6b2c8f1e45")
_MOTIVO = "Traslado de la deuda previa al vendedor por cambio de titular"


@dataclass(frozen=True)
class TrasladoDeDeuda:
    trasladado: Dinero
    #: La cuenta de persona que recibió la deuda; `None` si no había nada que trasladar.
    cuenta_destino: UUID | None


@dataclass(frozen=True)
class _Parte:
    obligacion: Obligacion
    componente: Componente
    importe: Dinero


def _partes(actual: FotoDeCuenta, limite: date) -> list[_Parte]:
    """Lo impago por obligación y componente de los períodos anteriores a `limite`, del período más
    viejo al más nuevo y, dentro de uno, en el orden de R04."""
    por_id = {o.id: o for o in actual.estado.obligaciones}
    orden = list(Componente)
    partes = [
        _Parte(por_id[obligacion], componente, residual)
        for (obligacion, componente), residual in actual.estado.residual.items()
        if residual > _CERO and por_id[obligacion].periodo < limite
    ]
    partes.sort(
        key=lambda p: (p.obligacion.periodo, orden.index(p.componente), str(p.obligacion.id))
    )
    return partes


def _cuenta_de_persona(sesion: Session, complejo_id: UUID, persona_id: UUID) -> UUID | None:
    existente = sesion.execute(
        text("SELECT id FROM cuenta WHERE complejo_id = :c AND persona_id = :p"),
        {"c": complejo_id, "p": persona_id},
    ).scalar_one_or_none()
    return None if existente is None else UUID(str(existente))


def _crear_cuenta_de_persona(
    sesion: Session, complejo_id: UUID, persona_id: UUID, instante: datetime
) -> UUID:
    """Única por administración, edificio y persona (`uq_cuenta_persona`): si otra transacción la
    creó mientras tanto, la de esa. La persona de otra administración la rechaza la FK compuesta."""
    with traducir(sesion, {}):
        sesion.execute(
            text(
                "INSERT INTO cuenta (id, administracion_id, complejo_id, persona_id, creada_en) "
                "VALUES (:id, :adm, :c, :p, :en) ON CONFLICT (administracion_id, complejo_id, "
                "persona_id) WHERE persona_id IS NOT NULL DO NOTHING"
            ),
            {
                "id": uuid4(),
                "adm": tenant(sesion),
                "c": complejo_id,
                "p": persona_id,
                "en": instante,
            },
        )
    cuenta = _cuenta_de_persona(sesion, complejo_id, persona_id)
    if cuenta is None:
        raise RuntimeError("la cuenta de persona no se pudo leer")
    return cuenta


def _contenedora(
    sesion: Session,
    destino: FotoDeCuenta,
    obligacion: Obligacion,
    cambio_id: UUID,
    instante: datetime,
) -> UUID:
    """La obligación de la cuenta del vendedor que contiene lo trasladado de una obligación de la
    unidad: mismo período y vencimiento, sin capital; su deuda son los débitos `traslado`."""
    identificador = uuid4()
    sesion.execute(
        text(
            "INSERT INTO obligacion (id, administracion_id, complejo_id, cuenta_id, operacion_id, "
            "periodo, vencimiento, ordinaria, fondo_de_reserva, extraordinaria, registrada_en) "
            "VALUES (:id, :adm, :c, :cuenta, :op, :p, :v, '0.00', '0.00', '0.00', :en)"
        ),
        {
            "id": identificador,
            "adm": tenant(sesion),
            "c": destino.complejo_id,
            "cuenta": destino.cuenta_id,
            "op": uuid5(_ESPACIO_DE_TRASLADOS, f"{cambio_id}|{obligacion.id}|obligacion"),
            "p": obligacion.periodo,
            "v": obligacion.vencimiento,
            "en": instante,
        },
    )
    return identificador


def trasladar_deuda(
    sesion: Session,
    identidad: Identidad,
    *,
    cambio_id: UUID,
    unidad_id: UUID,
    persona_id: UUID,
    fecha: date,
    request_id: UUID,
    reloj: Reloj = ahora_utc,
) -> TrasladoDeDeuda:
    """Traslada lo impago de los períodos anteriores al mes de `fecha` de la cuenta de `unidad_id` a
    la de `persona_id` (la crea si falta). Sin cuenta de unidad o sin nada impago anterior no
    escribe nada ni crea la cuenta de persona. No commitea: lo hace el llamador."""
    exigir_transaccion(sesion)
    exigir_identidad(sesion, identidad)
    limite = fecha.replace(day=1)
    cuenta_unidad = cuenta_de_unidad(sesion, unidad_id=unidad_id)
    if cuenta_unidad is None or not _partes(foto(sesion, cuenta_unidad), limite):
        return TrasladoDeDeuda(_CERO, None)
    instante = reloj()
    complejo_id = foto(sesion, cuenta_unidad).complejo_id
    cuenta_persona = _cuenta_de_persona(
        sesion, complejo_id, persona_id
    ) or _crear_cuenta_de_persona(sesion, complejo_id, persona_id, instante)
    bloquear_cuentas(sesion, [cuenta_unidad, cuenta_persona])  # las dos, juntas y en orden
    imputar_pendientes(sesion, cuenta_unidad, uuid4(), instante)  # R04 primero: lo a favor paga
    origen = foto(sesion, cuenta_unidad)
    partes = _partes(origen, limite)  # con el candado tomado: lo que decide la escritura
    if not partes:
        return TrasladoDeDeuda(_CERO, None)
    destino = foto(sesion, cuenta_persona)
    contenedoras: dict[UUID, UUID] = {}
    total = _CERO
    corrida = uuid4()
    for parte in partes:
        obligacion = parte.obligacion
        clave = f"{cambio_id}|{obligacion.id}|{parte.componente.value}"
        credito = _insertar(
            sesion,
            identidad,
            origen,
            tipo="traslado",
            sentido="credito",
            importe=parte.importe,
            fecha_valor=obligacion.vencimiento,
            operacion_id=uuid5(_ESPACIO_DE_TRASLADOS, f"{clave}|credito"),
            motivo=_MOTIVO,
            request_id=request_id,
            instante=instante,
            obligacion_id=obligacion.id,
            componente=parte.componente.value,
        )
        insertar_imputaciones(
            sesion,
            origen,
            credito,
            [Imputacion(obligacion.id, parte.componente, parte.importe)],
            corrida,
            instante,
        )
        if obligacion.id not in contenedoras:
            contenedoras[obligacion.id] = _contenedora(
                sesion, destino, obligacion, cambio_id, instante
            )
        _insertar(
            sesion,
            identidad,
            destino,
            tipo="traslado",
            sentido="debito",
            importe=parte.importe,
            fecha_valor=fecha,
            operacion_id=uuid5(_ESPACIO_DE_TRASLADOS, f"{clave}|debito"),
            motivo=_MOTIVO,
            request_id=request_id,
            instante=instante,
            obligacion_id=contenedoras[obligacion.id],
            componente=parte.componente.value,
            enlazado_a=credito,
        )
        total = total + parte.importe
    return TrasladoDeDeuda(total, cuenta_persona)

