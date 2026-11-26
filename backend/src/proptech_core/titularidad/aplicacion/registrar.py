"""Registrar el cambio de titular de una unidad (H-030, R32, D-168).

Orden de chequeo (D7 del 2a): alcance (404) -> permiso (403) -> la unidad es de este edificio (404)
-> la entrada (422). Todo en una transacción: los vendedores pierden su asignación `vecino` /
`propietario` de la unidad, los compradores la ganan (la persona se reutiliza por email, sin
renombrarla y sin invitación), queda la fila de sólo agregar y la auditoría; si algo falla no queda
nada. Con las opciones por defecto no escribe en el libro. Con `deuda_previa` a nombre del vendedor
(H-031) traslada, en la misma transacción, lo impago de los períodos anteriores al mes del cambio a
la cuenta de persona del vendedor deudor. Avisa, sin bloquear, si la cuenta de la unidad debe
(después del traslado). No commitea: lo hace el llamador.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.aplicacion.propietarios import (
    asegurar_persona,
    asignar_propietario,
    quitar_propietarios,
    vecinos_de_unidad_bloqueados,
)
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.dinero import Dinero
from proptech_core.complejos.aplicacion.errores import EntradaInvalida, transaccion
from proptech_core.cuenta_corriente.aplicacion.lecturas import cuenta_de_unidad, estado_de_cuenta
from proptech_core.cuenta_corriente.aplicacion.traslado_de_deuda import trasladar_deuda
from proptech_core.titularidad.aplicacion.autorizacion import unidad_autorizada
from proptech_core.titularidad.aplicacion.lectura import CambioDeTitular, CompradorDelCambio
from proptech_core.titularidad.dominio.cambio import (
    CambioInvalido,
    validar_compradores,
    validar_pedido,
    validar_vendedor_deudor,
)

_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class CompradorPedido:
    nombre: str
    email: str | None


def _fecha(texto: str) -> date:
    """`AAAA-MM-DD`. Se lee a mano (no como `date` del cuerpo) para que el 422 llegue después del
    404 y del 403, en el orden de D7."""
    try:
        if not _FECHA.fullmatch(texto):
            raise ValueError
        return date.fromisoformat(texto)
    except ValueError:
        raise EntradaInvalida("fecha", "fecha inválida") from None


@accion_sensible(Accion.REGISTRAR_CAMBIO_DE_TITULAR)
def registrar_cambio_de_titular(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    unidad_id: UUID,
    fecha: str,
    vendedores: Sequence[UUID],
    compradores: Sequence[CompradorPedido],
    expensa_del_mes: str,
    deuda_previa: str,
    vendedor_deudor: UUID | None = None,
    hoy: date,
    request_id: UUID,
) -> CambioDeTitular:
    with transaccion(sesion, {}):
        unidad_autorizada(sesion, identidad, complejo_id, unidad_id)
        el_dia = _fecha(fecha)
        vecinos = vecinos_de_unidad_bloqueados(sesion, unidad_id=unidad_id)
        try:
            validar_pedido(
                fecha=el_dia,
                hoy=hoy,
                vendedores=vendedores,
                cantidad_de_compradores=len(compradores),
                propietarios={p for p, vinculo in vecinos.items() if vinculo == "propietario"},
            )
            resueltos = [
                asegurar_persona(sesion, identidad, nombre=c.nombre, email=c.email)
                for c in compradores
            ]
            validar_compradores(
                vendedores=vendedores,
                compradores=[r.persona_id for r in resueltos],
                con_vinculo_en_la_unidad=set(vecinos),
            )
            deudor = validar_vendedor_deudor(
                deuda_previa=deuda_previa, vendedor_deudor=vendedor_deudor, vendedores=vendedores
            )
        except CambioInvalido as error:
            raise EntradaInvalida(error.campo) from None
        quitar_propietarios(sesion, personas=vendedores, unidad_id=unidad_id)
        for r in resueltos:
            asignar_propietario(
                sesion,
                identidad,
                persona_id=r.persona_id,
                complejo_id=complejo_id,
                unidad_id=unidad_id,
            )
        cambio_id = uuid4()
        registrado_en = sesion.execute(
            text(
                "INSERT INTO cambio_de_titular (id, administracion_id, complejo_id, unidad_id, "
                "fecha, expensa_del_mes, deuda_previa, vendedor_deudor_id, registrado_por) "
                "VALUES (:id, :administracion, :complejo, :unidad, :fecha, :expensa, :deuda, "
                ":deudor, :persona) RETURNING registrado_en"
            ),
            {
                "id": cambio_id,
                "administracion": identidad.administracion_id,
                "complejo": complejo_id,
                "unidad": unidad_id,
                "fecha": el_dia,
                "expensa": expensa_del_mes,
                "deuda": deuda_previa,
                "deudor": deudor,
                "persona": identidad.persona_id,
            },
        ).scalar_one()
        partes = [(v, "vendedor", n, None, None) for n, v in enumerate(vendedores)] + [
            (r.persona_id, "comprador", n, c.nombre, c.email)
            for n, (r, c) in enumerate(zip(resueltos, compradores, strict=True))
        ]
        for persona, rol, orden, nombre, email in partes:
            sesion.execute(
                text(
                    "INSERT INTO parte_de_cambio_de_titular (administracion_id, complejo_id, "
                    "cambio_id, persona_id, rol, orden, nombre, email) VALUES (:administracion, "
                    ":complejo, :cambio, :persona, :rol, :orden, :nombre, :email)"
                ),
                {
                    "administracion": identidad.administracion_id,
                    "complejo": complejo_id,
                    "cambio": cambio_id,
                    "persona": persona,
                    "rol": rol,
                    "orden": orden,
                    "nombre": nombre,
                    "email": email,
                },
            )
        registrar(
            sesion,
            identidad,
            Accion.REGISTRAR_CAMBIO_DE_TITULAR,
            entidad="cambio_de_titular",
            entidad_id=cambio_id,
            request_id=request_id,
            detalle={
                "unidad_id": str(unidad_id),
                "fecha": el_dia.isoformat(),
                "expensa_del_mes": expensa_del_mes,
                "deuda_previa": deuda_previa,
            },
        )
        traslado = (
            None
            if deudor is None
            else trasladar_deuda(
                sesion,
                identidad,
                cambio_id=cambio_id,
                unidad_id=unidad_id,
                persona_id=deudor,
                fecha=el_dia,
                request_id=request_id,
            )
        )
        aviso = _deuda_de_la_unidad(sesion, unidad_id)
    return CambioDeTitular(
        id=cambio_id,
        unidad_id=unidad_id,
        fecha=el_dia,
        vendedores=tuple(vendedores),
        compradores=tuple(
            CompradorDelCambio(r.persona_id, c.nombre, c.email)
            for r, c in zip(resueltos, compradores, strict=True)
        ),
        expensa_del_mes=expensa_del_mes,
        deuda_previa=deuda_previa,
        registrado_por=identidad.persona_id,
        registrado_en=registrado_en,
        aviso=aviso,
        trasladado=None if traslado is None else traslado.trasladado,
        cuenta_del_vendedor=None if traslado is None else traslado.cuenta_destino,
    )


def _deuda_de_la_unidad(sesion: Session, unidad_id: UUID) -> Dinero | None:
    """Lo que debe la cuenta de la unidad (capital más interés registrado, imputado), o `None` si no
    tiene cuenta o no debe. Sólo lee: con las opciones por defecto el libro no cambia."""
    cuenta = cuenta_de_unidad(sesion, unidad_id=unidad_id)
    if cuenta is None:
        return None
    deuda = estado_de_cuenta(sesion, cuenta_id=cuenta).deuda
    return deuda if deuda > Dinero("0.00") else None
