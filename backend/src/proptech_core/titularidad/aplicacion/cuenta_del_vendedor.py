"""La cuenta de persona del vendedor (4d, H-033, R32, D-168.2c): ver la de cada vendedor del
edificio y registrar su cobro.

Los tres casos de uso autorizan solos, en el orden de D7: el edificio que no existe o no alcanza da
404; sin `ver_morosidad` (las dos lecturas) o `confirmar_pago_informado` (el cobro) en él, 403; una
cuenta que no es de persona de ese edificio (de unidad, de otro edificio o administración, que no
existe o con un id que no es uuid), 404; el cuerpo, 422. El cobro es un `pago` del libro con R04 a
la fecha de la transferencia (`cuenta_corriente.aplicacion.pagos`), en una sola transacción con su
auditoría; no toca cuentas de unidad ni la bandeja de pagos informados.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.aplicacion.propietarios import nombres_de_personas
from proptech_core.acceso.dominio.eventos import EventoDelPago
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, alcanza, puede
from proptech_core.compartido.dinero import Dinero
from proptech_core.complejos.aplicacion.errores import EntradaInvalida, NoEncontrado, transaccion
from proptech_core.complejos.aplicacion.lectura import cargar_complejo, identificadores_de_unidades
from proptech_core.cuenta_corriente.aplicacion.cuentas import bloquear_cuentas
from proptech_core.cuenta_corriente.aplicacion.cuentas_de_persona import (
    CuentaDePersona,
    MovimientoDeCuenta,
    PeriodoDeCuenta,
    cuenta_de_persona,
    cuentas_de_persona,
)
from proptech_core.cuenta_corriente.aplicacion.pagos import registrar_pago
from proptech_core.titularidad.aplicacion.errores import SinPermiso
from proptech_core.titularidad.dominio.cobro import CobroInvalido, validar_cobro


@dataclass(frozen=True)
class CuentaDelVendedor:
    cuenta_id: UUID
    persona_id: UUID
    nombre: str
    deuda: Dinero
    #: Las unidades de los cambios que le trasladaron deuda: (id, identificador), por identificador.
    unidades: tuple[tuple[UUID, str], ...]


@dataclass(frozen=True)
class DetalleDeLaCuenta:
    cuenta: CuentaDelVendedor
    periodos: tuple[PeriodoDeCuenta, ...]
    movimientos: tuple[MovimientoDeCuenta, ...]


def _edificio_autorizado(
    sesion: Session, identidad: Identidad, complejo_id: UUID, accion: Accion
) -> None:
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if (
        edificio is None
        or edificio.administracion_id != identidad.administracion_id
        or not alcanza(asignaciones, complejo_id)
    ):
        raise NoEncontrado()
    if not puede(asignaciones, accion, complejo_id):
        raise SinPermiso(accion.value)


def _uuid(texto: str) -> UUID:
    try:
        return UUID(texto)
    except ValueError:
        raise NoEncontrado() from None


def _unidades_de_origen(
    sesion: Session, complejo_id: UUID, personas: list[UUID]
) -> dict[UUID, list[tuple[UUID, str]]]:
    """Por vendedor, las unidades de los cambios en que quedó como deudor, sin repetir."""
    if not personas:
        return {}
    filas = sesion.execute(
        text(
            "SELECT DISTINCT vendedor_deudor_id AS persona, unidad_id FROM cambio_de_titular "
            "WHERE complejo_id = :c AND vendedor_deudor_id = ANY(CAST(:personas AS uuid[]))"
        ),
        {"c": complejo_id, "personas": [str(p) for p in personas]},
    ).all()
    identificadores = identificadores_de_unidades(sesion, [UUID(str(f.unidad_id)) for f in filas])
    salida: dict[UUID, list[tuple[UUID, str]]] = {}
    for f in filas:
        unidad = UUID(str(f.unidad_id))
        if unidad in identificadores:
            salida.setdefault(UUID(str(f.persona)), []).append((unidad, identificadores[unidad]))
    return {p: sorted(u, key=lambda par: par[1]) for p, u in salida.items()}


def _armar(
    sesion: Session, complejo_id: UUID, cuentas: list[CuentaDePersona]
) -> list[CuentaDelVendedor]:
    personas = [c.persona_id for c in cuentas]
    nombres = nombres_de_personas(sesion, personas)
    unidades = _unidades_de_origen(sesion, complejo_id, personas)
    return [
        CuentaDelVendedor(
            c.cuenta_id,
            c.persona_id,
            nombres.get(c.persona_id, ""),
            c.deuda,
            tuple(unidades.get(c.persona_id, [])),
        )
        for c in cuentas
    ]


def listar_cuentas_de_vendedores(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID
) -> list[CuentaDelVendedor]:
    """Una por cuenta de persona del edificio, también las que quedaron en cero; la de más deuda
    primero."""
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_MOROSIDAD)
    cuentas = _armar(sesion, complejo_id, cuentas_de_persona(sesion, complejo_id=complejo_id))
    return sorted(cuentas, key=lambda c: (-c.deuda.decimal, c.nombre, str(c.cuenta_id)))


def _detalle(sesion: Session, complejo_id: UUID, cuenta: CuentaDePersona) -> DetalleDeLaCuenta:
    return DetalleDeLaCuenta(
        _armar(sesion, complejo_id, [cuenta])[0],
        tuple(cuenta.periodos()),
        tuple(cuenta.movimientos()),
    )


def cuenta_de_vendedor(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID, cuenta_id: str
) -> DetalleDeLaCuenta:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_MOROSIDAD)
    cuenta = cuenta_de_persona(sesion, complejo_id=complejo_id, cuenta_id=_uuid(cuenta_id))
    if cuenta is None:
        raise NoEncontrado()
    return _detalle(sesion, complejo_id, cuenta)


@accion_sensible(EventoDelPago.REGISTRAR_COBRO_DE_VENDEDOR)
def registrar_cobro_de_vendedor(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    cuenta_id: str,
    importe: Any,
    fecha: Any,
    hoy: date,
    request_id: UUID,
) -> DetalleDeLaCuenta:
    """Un cobro de la cuenta de persona: lo que se debe se imputa con R04 a la fecha de la
    transferencia. Un importe mayor que la deuda, o sobre una cuenta en cero, da 422 sin cambiar
    nada. Dos pedidos iguales son dos cobros (sin idempotencia, D3 del contrato). No commitea."""
    with transaccion(sesion, {}):
        _edificio_autorizado(sesion, identidad, complejo_id, Accion.CONFIRMAR_PAGO_INFORMADO)
        id_de_cuenta = _uuid(cuenta_id)
        if cuenta_de_persona(sesion, complejo_id=complejo_id, cuenta_id=id_de_cuenta) is None:
            raise NoEncontrado()
        bloquear_cuentas(
            sesion, [id_de_cuenta]
        )  # la deuda que decide el tope se lee con el candado
        deuda = cuenta_de_persona(sesion, complejo_id=complejo_id, cuenta_id=id_de_cuenta)
        if deuda is None:
            raise NoEncontrado()
        try:
            monto, el_dia = validar_cobro(importe=importe, fecha=fecha, hoy=hoy, deuda=deuda.deuda)
        except CobroInvalido as error:
            raise EntradaInvalida(error.campo) from None
        registrar_pago(
            sesion,
            identidad,
            cuenta_id=id_de_cuenta,
            importe=monto,
            fecha_valor=el_dia,
            operacion_id=uuid4(),
            request_id=request_id,
        )
        registrar(
            sesion,
            identidad,
            EventoDelPago.REGISTRAR_COBRO_DE_VENDEDOR,
            entidad="cuenta",
            entidad_id=id_de_cuenta,
            request_id=request_id,
            detalle={"cuenta_id": id_de_cuenta, "importe": monto.a_texto(), "fecha": el_dia},
        )
        actual = cuenta_de_persona(sesion, complejo_id=complejo_id, cuenta_id=id_de_cuenta)
        if actual is None:
            raise NoEncontrado()
        return _detalle(sesion, complejo_id, actual)
