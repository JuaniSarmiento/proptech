"""Emitir el certificado de libre deuda de una unidad a una fecha de corte (H-041, R21, D-171).

Orden de chequeo (D7 del 2a): alcance (404) -> permiso (403) -> la unidad es de este edificio (404)
-> la entrada (422: la fecha de corte es una fecha ISO y no es posterior a hoy). Todo en una
transacción: la foto de lo que el libro sabía a la fecha de corte, el PDF (WeasyPrint, guardado
tal como sale y nunca regenerado), la fila de sólo agregar y la auditoría; si algo falla no queda
nada. No escribe en el libro. No commitea: lo hace el llamador.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.complejos.aplicacion.errores import EntradaInvalida, transaccion
from proptech_core.cuenta_corriente.aplicacion.deuda_a_la_fecha import (
    deuda_de_la_unidad_a_la_fecha,
)
from proptech_core.libre_deuda.aplicacion.autorizacion import unidad_autorizada
from proptech_core.libre_deuda.aplicacion.certificado import Certificado
from proptech_core.libre_deuda.dominio.certificado import (
    contenido_del_certificado,
    html_del_certificado,
    huella_del_certificado,
)
from proptech_core.pagos.aplicacion.en_revision import pagos_en_revision_de_la_unidad

_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)

Renderizador = Callable[[str], bytes]


def _renderizador_por_defecto() -> Renderizador:
    from proptech_core.libre_deuda.adaptadores.pdf import renderizar_con_weasyprint

    return renderizar_con_weasyprint


def _fecha_de_corte(valor: Any, *, hoy: date) -> date:
    """Una fecha ISO `AAAA-MM-DD`, no posterior a hoy. Se lee a mano (no como `date` del cuerpo)
    para que el 422 llegue después del 404 y del 403, en el orden de D7."""
    try:
        if not isinstance(valor, str) or not _FECHA.fullmatch(valor):
            raise ValueError
        corte = date.fromisoformat(valor)
    except ValueError:
        raise EntradaInvalida("fecha_de_corte", "fecha inválida") from None
    if corte > hoy:
        raise EntradaInvalida("fecha_de_corte", "no puede ser posterior a hoy")
    return corte


@accion_sensible(Accion.EMITIR_LIBRE_DEUDA)
def emitir_libre_deuda(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    unidad_id: UUID,
    fecha_de_corte: Any,
    hoy: date,
    request_id: UUID,
    renderizar: Renderizador | None = None,
    reloj: Callable[[], datetime] | None = None,
) -> Certificado:
    with transaccion(sesion, {}):
        autorizada = unidad_autorizada(sesion, identidad, complejo_id, unidad_id)
        corte = _fecha_de_corte(fecha_de_corte, hoy=hoy)
        deuda = deuda_de_la_unidad_a_la_fecha(
            sesion, complejo_id=complejo_id, unidad_id=unidad_id, corte=corte
        )
        en_revision = [
            {
                "pago_id": str(p.pago_id),
                "importe": p.importe.a_texto(),
                "fecha_de_transferencia": p.fecha_de_transferencia.isoformat(),
                "banco": p.banco,
                "numero_de_operacion": p.numero_de_operacion,
            }
            for p in pagos_en_revision_de_la_unidad(sesion, unidad_id=unidad_id, corte=corte)
        ]
        vencen_despues = [
            {
                "periodo": c.periodo.isoformat(),
                "vencimiento": c.vencimiento.isoformat(),
                "importe": c.importe.a_texto(),
            }
            for c in deuda.cuotas_posteriores
        ]
        contenido = contenido_del_certificado(
            unidad_id=str(unidad_id),
            fecha_de_corte=corte,
            capital=deuda.capital.a_texto(),
            intereses=deuda.intereses.a_texto(),
            interes_corrido=deuda.interes_corrido.a_texto(),
            en_revision=en_revision,
            vencen_despues=vencen_despues,
        )
        huella = huella_del_certificado(contenido)
        certificado_id = uuid4()
        emitido_en = (reloj or (lambda: datetime.now(UTC)))()
        pdf = (renderizar or _renderizador_por_defecto())(
            html_del_certificado(
                contenido,
                certificado_id=str(certificado_id),
                nombre_del_edificio=autorizada.nombre_del_edificio,
                identificador_de_la_unidad=autorizada.unidad.identificador,
            )
        )
        sesion.execute(
            text(
                "INSERT INTO certificado_de_libre_deuda (id, administracion_id, complejo_id, "
                "unidad_id, fecha_de_corte, saldo, capital, intereses, interes_corrido, "
                "en_revision, vencen_despues, huella, pdf, emitido_por, emitido_en) "
                "VALUES (:id, :administracion, :complejo, :unidad, :corte, :saldo, :capital, "
                ":intereses, :corrido, CAST(:en_revision AS jsonb), "
                "CAST(:vencen_despues AS jsonb), :huella, :pdf, :persona, :emitido_en)"
            ),
            {
                "id": certificado_id,
                "administracion": identidad.administracion_id,
                "complejo": complejo_id,
                "unidad": unidad_id,
                "corte": corte,
                "saldo": contenido["saldo"],
                "capital": contenido["capital"],
                "intereses": contenido["intereses"],
                "corrido": contenido["interes_corrido"],
                "en_revision": _json(en_revision),
                "vencen_despues": _json(vencen_despues),
                "huella": huella,
                "pdf": pdf,
                "persona": identidad.persona_id,
                "emitido_en": emitido_en,
            },
        )
        registrar(
            sesion,
            identidad,
            Accion.EMITIR_LIBRE_DEUDA,
            entidad="certificado_de_libre_deuda",
            entidad_id=certificado_id,
            request_id=request_id,
            detalle={"unidad_id": str(unidad_id), "fecha_de_corte": corte.isoformat()},
        )
    return Certificado(
        id=certificado_id,
        unidad_id=unidad_id,
        fecha_de_corte=corte,
        emitido_en=emitido_en,
        saldo=contenido["saldo"],
        capital=contenido["capital"],
        intereses=contenido["intereses"],
        interes_corrido=contenido["interes_corrido"],
        en_revision=tuple(en_revision),
        vencen_despues=tuple(vencen_despues),
        en_gestion_judicial=False,
        huella=huella,
    )


def _json(valor: list[dict[str, str]]) -> str:
    return json.dumps(valor, sort_keys=True)
