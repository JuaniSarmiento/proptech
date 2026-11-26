"""Registrar el cambio de titular de una unidad (H-030, R32, D-168).

Orden de chequeo (D7 del 2a): alcance (404) -> permiso (403) -> la unidad es de este edificio (404)
-> la entrada (422). Todo en una transacción: los vendedores pierden su asignación `vecino` /
`propietario` de la unidad, los compradores la ganan (la persona se reutiliza por email, sin
renombrarla y sin invitación), queda la fila de sólo agregar y la auditoría; si algo falla no queda
nada. Con las opciones por defecto no escribe en el libro. Con `deuda_previa` a nombre del vendedor
(H-031) traslada, en la misma transacción, lo impago de los períodos anteriores al mes del cambio a
la cuenta de persona del vendedor deudor. Avisa, sin bloquear, si la cuenta de la unidad debe
(después del traslado). Con `expensa_del_mes = "prorrateo"` (H-032) guarda el prorrateo de los días
del vendedor y, si el período del mes ya está emitido, lo traslada en la misma transacción; si no,
queda pendiente y lo aplica la emisión de ese período. No commitea: lo hace el llamador.
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
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.cuenta_corriente.aplicacion.lecturas import cuenta_de_unidad, estado_de_cuenta
from proptech_core.cuenta_corriente.aplicacion.traslado_de_deuda import trasladar_deuda
from proptech_core.titularidad.aplicacion.autorizacion import unidad_autorizada
from proptech_core.titularidad.aplicacion.lectura import (
    CambioDeTitular,
    CompradorDelCambio,
    Prorrateo,
)
from proptech_core.titularidad.aplicacion.prorrateo import pedir_prorrateo, prorrateo_ya_pedido
from proptech_core.titularidad.dominio.cambio import (
    CambioInvalido,
    validar_compradores,
    validar_pedido,
    validar_vendedor_deudor,
)
from proptech_core.titularidad.dominio.prorrateo import dias_del_mes, dias_del_vendedor

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
        con_prorrateo = expensa_del_mes == "prorrateo"
        a_nombre = deuda_previa == "a_nombre_del_vendedor"
        if con_prorrateo or a_nombre:
            # Todo lo que traslada toma el candado del período (el de la emisión, E5) antes que
            # los de las cuentas: un prorrateo no se pierde entre un registro y una emisión.
            cargar_complejo(sesion, complejo_id, bloquear=True)
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
                deuda_previa=deuda_previa,
                vendedor_deudor=vendedor_deudor,
                vendedores=vendedores,
                con_prorrateo=con_prorrateo,
            )
            if con_prorrateo and prorrateo_ya_pedido(sesion, unidad_id=unidad_id, fecha=el_dia):
                raise CambioInvalido("expensa_del_mes")
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
            if deudor is None or not a_nombre
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
        prorrateo = None
        if con_prorrateo and deudor is not None:
            parte = pedir_prorrateo(
                sesion,
                identidad,
                complejo_id=complejo_id,
                cambio_id=cambio_id,
                unidad_id=unidad_id,
                fecha=el_dia,
                deudor_id=deudor,
                request_id=request_id,
            )
            prorrateo = Prorrateo(
                el_dia.replace(day=1), dias_del_vendedor(el_dia), dias_del_mes(el_dia), parte
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
        prorrateo=prorrateo,
    )


def _deuda_de_la_unidad(sesion: Session, unidad_id: UUID) -> Dinero | None:
    """Lo que debe la cuenta de la unidad (capital más interés registrado, imputado), o `None` si no
    tiene cuenta o no debe. Sólo lee: con las opciones por defecto el libro no cambia."""
    cuenta = cuenta_de_unidad(sesion, unidad_id=unidad_id)
    if cuenta is None:
        return None
    deuda = estado_de_cuenta(sesion, cuenta_id=cuenta).deuda
    return deuda if deuda > Dinero("0.00") else None
