"""El cambio de titular de una unidad (4d, H-030, R32, D-168): registrarlo y listar los de ella; y
la cuenta del vendedor (H-033): ver las del edificio, el detalle de una y registrar su cobro.

Los dos casos de uso autorizan solos, en el orden de D7: el edificio que no existe o no alcanza, o
la unidad que no es de él, da 404; sin `registrar_cambio_de_titular` (que también cubre leer), 403;
la entrada que no sirve, 422. `NoEncontrado` y `EntradaInvalida` los traduce el manejador de
`complejos`.
Las dos opciones de R32 se aceptan: la deuda previa a nombre del vendedor (H-031) y el prorrateo por
días de la expensa del mes (H-032), que agrega `prorrateo` a la respuesta y al listado.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import AfterValidator, Field
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.cuerpos import CuerpoDeAlta
from proptech_api.morosidad import hoy
from proptech_core.acceso.aplicacion.datos_de_usuario import email_valido, nombre_valido
from proptech_core.acceso.aplicacion.lectura_de_personas import (
    nombres_de_personas,
    propietarios_de_unidad,
)
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.titularidad.aplicacion.cuenta_del_vendedor import (
    CuentaDelVendedor,
    DetalleDeLaCuenta,
    cuenta_de_vendedor,
    listar_cuentas_de_vendedores,
    registrar_cobro_de_vendedor,
)
from proptech_core.titularidad.aplicacion.autorizacion import unidad_autorizada
from proptech_core.titularidad.aplicacion.errores import SinPermiso
from proptech_core.titularidad.aplicacion.lectura import CambioDeTitular, listar_cambios
from proptech_core.titularidad.aplicacion.registrar import (
    CompradorPedido,
    registrar_cambio_de_titular,
)

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)


async def manejar_sin_permiso(_request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, SinPermiso):
        raise TypeError(f"manejar_sin_permiso recibió un error inesperado: {type(error)!r}")
    return JSONResponse(
        status_code=403,
        content={
            "detail": {
                "codigo": "sin_permiso",
                "detalle": "sin_permiso",
                "permiso_faltante": error.permiso_faltante,
            }
        },
    )


def _nombre(valor: str) -> str:
    recortado = nombre_valido(valor)
    if not 1 <= len(recortado) <= 80:
        raise ValueError("el nombre debe tener de 1 a 80 caracteres")
    return recortado


class CuerpoComprador(CuerpoDeAlta):
    nombre: Annotated[str, AfterValidator(_nombre)]
    email: Annotated[str, AfterValidator(email_valido)] | None = None


class CuerpoCambioDeTitular(CuerpoDeAlta):
    #: Texto `AAAA-MM-DD`: el caso de uso lo lee, para que su 422 llegue después del 404 y del 403.
    fecha: str
    vendedores: list[Annotated[UUID, Field(strict=False)]]
    compradores: list[CuerpoComprador]
    expensa_del_mes: Literal["entera", "prorrateo"] = "entera"
    deuda_previa: Literal["en_la_unidad", "a_nombre_del_vendedor"] = "en_la_unidad"
    #: Con la deuda a nombre del vendedor: cuál de los vendedores (puede omitirse con uno solo).
    vendedor_deudor: Annotated[UUID, Field(strict=False)] | None = None


def _como_json(cambio: CambioDeTitular, *, con_aviso: bool) -> dict[str, Any]:
    respuesta: dict[str, Any] = {
        "id": str(cambio.id),
        "unidad_id": str(cambio.unidad_id),
        "fecha": cambio.fecha.isoformat(),
        "vendedores": [str(v) for v in cambio.vendedores],
        "compradores": [
            {"nombre": c.nombre, "email": c.email, "persona_id": str(c.persona_id)}
            for c in cambio.compradores
        ],
        "expensa_del_mes": cambio.expensa_del_mes,
        "deuda_previa": cambio.deuda_previa,
        "registrado_por": str(cambio.registrado_por),
        "registrado_en": cambio.registrado_en.isoformat(),
    }
    if con_aviso:
        respuesta["aviso"] = None if cambio.aviso is None else {"deuda": cambio.aviso.a_texto()}
    if cambio.trasladado is not None:
        respuesta["trasladado"] = cambio.trasladado.a_texto()
        respuesta["cuenta_del_vendedor"] = (
            None if cambio.cuenta_del_vendedor is None else str(cambio.cuenta_del_vendedor)
        )
    if cambio.prorrateo is not None:
        parte = cambio.prorrateo.parte_del_vendedor
        respuesta["prorrateo"] = {
            "estado": cambio.prorrateo.estado,
            "periodo": cambio.prorrateo.periodo.isoformat(),
            "dias_del_vendedor": cambio.prorrateo.dias_del_vendedor,
            "dias_del_mes": cambio.prorrateo.dias_del_mes,
            "parte_del_vendedor": None if parte is None else parte.a_texto(),
        }
    return respuesta


def _con_nombres_de_vendedores(
    sesion: Session,
    identidad: Identidad,
    cambios: list[CambioDeTitular],
    respuestas: list[dict[str, Any]],
) -> None:
    """`?con_nombres=true` (H-035): suma `vendedores_detalle` en el orden de `vendedores`."""
    nombres = nombres_de_personas(
        sesion, identidad, persona_ids=[v for c in cambios for v in c.vendedores]
    )
    for cambio, respuesta in zip(cambios, respuestas, strict=True):
        respuesta["vendedores_detalle"] = [
            {"persona_id": str(v), "nombre": nombres.get(v, "")} for v in cambio.vendedores
        ]


@router.get("/complejos/{complejo_id}/unidades/{unidad_id}/propietarios")
def propietarios(
    complejo_id: UUID,
    unidad_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    """Los propietarios actuales de la unidad (id y nombre, por nombre), para elegir al vendedor.
    Mismo permiso que el cambio de titular; es una lectura: no se audita."""
    unidad_autorizada(sesion, identidad, complejo_id, unidad_id)
    return {
        "propietarios": [
            {"persona_id": str(p.persona_id), "nombre": p.nombre}
            for p in propietarios_de_unidad(sesion, identidad, unidad_id=unidad_id)
        ]
    }


@router.post("/complejos/{complejo_id}/unidades/{unidad_id}/cambios-de-titular", status_code=201)
def registrar(
    complejo_id: UUID,
    unidad_id: UUID,
    cuerpo: CuerpoCambioDeTitular,
    con_nombres: bool = False,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
    fecha_de_hoy: date = Depends(hoy),
) -> dict[str, Any]:
    """Los vendedores dejan de ser propietarios de la unidad y los compradores lo pasan a ser; si la
    unidad debe, `aviso` trae el monto (nunca bloquea)."""
    cambio = registrar_cambio_de_titular(
        sesion,
        identidad,
        complejo_id=complejo_id,
        unidad_id=unidad_id,
        fecha=cuerpo.fecha,
        vendedores=cuerpo.vendedores,
        compradores=[CompradorPedido(c.nombre, c.email) for c in cuerpo.compradores],
        expensa_del_mes=cuerpo.expensa_del_mes,
        deuda_previa=cuerpo.deuda_previa,
        vendedor_deudor=cuerpo.vendedor_deudor,
        hoy=fecha_de_hoy,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    respuesta = _como_json(cambio, con_aviso=True)
    if con_nombres:
        _con_nombres_de_vendedores(sesion, identidad, [cambio], [respuesta])
    return respuesta


@router.get("/complejos/{complejo_id}/unidades/{unidad_id}/cambios-de-titular")
def listar(
    complejo_id: UUID,
    unidad_id: UUID,
    con_nombres: bool = False,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    cambios = listar_cambios(sesion, identidad, complejo_id=complejo_id, unidad_id=unidad_id)
    respuestas = [_como_json(c, con_aviso=False) for c in cambios]
    if con_nombres:
        _con_nombres_de_vendedores(sesion, identidad, cambios, respuestas)
    return respuestas


class CuerpoCobro(CuerpoDeAlta):
    #: Sin tipo: el caso de uso los lee, para que su 422 llegue después del 404 y del 403 (D7).
    importe: Any
    fecha: Any


def _cuenta_como_json(cuenta: CuentaDelVendedor) -> dict[str, Any]:
    return {
        "cuenta_id": str(cuenta.cuenta_id),
        "persona": {"id": str(cuenta.persona_id), "nombre": cuenta.nombre},
        "deuda": cuenta.deuda.a_texto(),
        "unidades": [{"id": str(u), "identificador": i} for u, i in cuenta.unidades],
    }


def _detalle_como_json(detalle: DetalleDeLaCuenta) -> dict[str, Any]:
    return {
        **_cuenta_como_json(detalle.cuenta),
        "periodos": [
            {
                "periodo": p.periodo.isoformat(),
                "componentes": {
                    c.value: {
                        "debe": t.debe.a_texto(),
                        "cobrado": t.cobrado.a_texto(),
                        "pendiente": t.pendiente.a_texto(),
                    }
                    for c, t in p.componentes.items()
                },
            }
            for p in detalle.periodos
        ],
        "movimientos": [
            {
                "id": str(m.id),
                "tipo": m.tipo,
                "sentido": m.sentido,
                "importe": m.importe.a_texto(),
                "fecha": m.fecha.isoformat(),
            }
            for m in detalle.movimientos
        ],
    }


@router.get("/complejos/{complejo_id}/cuentas-de-vendedores")
def cuentas_de_vendedores(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    """Las cuentas de persona del edificio (la deuda que el cambio de titular les trasladó), la de
    más deuda primero. Es una lectura: no se audita."""
    cuentas = listar_cuentas_de_vendedores(sesion, identidad, complejo_id=complejo_id)
    return {"cuentas": [_cuenta_como_json(c) for c in cuentas]}


@router.get("/complejos/{complejo_id}/cuentas-de-vendedores/{cuenta_id}")
def cuenta_del_vendedor(
    complejo_id: UUID,
    cuenta_id: str,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    detalle = cuenta_de_vendedor(sesion, identidad, complejo_id=complejo_id, cuenta_id=cuenta_id)
    return _detalle_como_json(detalle)


@router.post("/complejos/{complejo_id}/cuentas-de-vendedores/{cuenta_id}/cobros", status_code=201)
def cobrar_al_vendedor(
    complejo_id: UUID,
    cuenta_id: str,
    cuerpo: CuerpoCobro,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
    fecha_de_hoy: date = Depends(hoy),
) -> dict[str, Any]:
    """Registra el cobro (el importe en texto y la fecha de la transferencia) y responde con el
    detalle de la cuenta ya actualizado."""
    detalle = registrar_cobro_de_vendedor(
        sesion,
        identidad,
        complejo_id=complejo_id,
        cuenta_id=cuenta_id,
        importe=cuerpo.importe,
        fecha=cuerpo.fecha,
        hoy=fecha_de_hoy,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return _detalle_como_json(detalle)
