"""El portal del vecino, lecturas (change 11, H-038, D-170): lo que debo y lo que pagué.

Las unidades de la persona son sus asignaciones `vecino` (D-106): la identidad sale del login y
ningún parámetro del cliente decide quién es. Ser personal no da unidades. Toda ruta por unidad
da 404 `no encontrado` si la unidad no es de la persona, sea ajena, de otro edificio, de otra
administración o inexistente. Ninguna ruta escribe (N04). El inquilino no ve lo extraordinario
(D-170.2): la deuda, los pagos y el PDF son los suyos.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Rol
from proptech_core.compartido.configuracion import ConfiguracionInvalida
from proptech_core.compartido.dinero import sumar
from proptech_core.compartido.reparto import clave_de_orden_natural
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.complejos.aplicacion.escritura import hoy_en_mendoza
from proptech_core.complejos.aplicacion.lectura import (
    cargar_complejo,
    identificadores_de_unidades,
)
from proptech_core.cuenta_corriente.aplicacion.vision_del_vecino import cifras_de_unidad
from proptech_core.gastos.aplicacion import cargos_particulares
from proptech_core.liquidacion.aplicacion import documentos, enlaces, expensa_del_vecino
from proptech_core.liquidacion.aplicacion.errores import NoEncontrado
from proptech_core.liquidacion.aplicacion.lectura import ultima_emision_vigente
from proptech_core.pagos.aplicacion.lectura import pagos_confirmados_de_unidad

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)
#: Cuánto dura un enlace de descarga (D-070), el mismo del 7.
VIGENCIA_DEL_ENLACE = timedelta(minutes=15)
PROPIETARIO = "propietario"
INQUILINO = "inquilino"


def hoy() -> date:
    """La fecha de hoy en Mendoza. Es una dependencia para que la aceptación la fije (L-090)."""
    return hoy_en_mendoza(lambda: datetime.now(UTC))


def _no_encontrado() -> HTTPException:
    return HTTPException(status_code=404, detail="no encontrado")


def _unidades_de_la_persona(sesion: Session, identidad: Identidad) -> dict[UUID, tuple[UUID, str]]:
    """`{unidad: (edificio, vínculo)}` de las asignaciones `vecino` de la persona. Si tuviera las
    dos sobre una misma unidad, vale la de propietario."""
    unidades: dict[UUID, tuple[UUID, str]] = {}
    for a in cargar_asignaciones(sesion, identidad.persona_id):
        if a.rol is not Rol.VECINO or a.unidad_id is None or a.complejo_id is None:
            continue
        if a.vinculo == PROPIETARIO or a.unidad_id not in unidades:
            unidades[a.unidad_id] = (a.complejo_id, str(a.vinculo))
    return unidades


def _mi_unidad(sesion: Session, identidad: Identidad, unidad_id: UUID) -> tuple[UUID, str]:
    propia = _unidades_de_la_persona(sesion, identidad).get(unidad_id)
    if propia is None:
        raise _no_encontrado()
    return propia


@router.get("/mis-unidades")
def mis_unidades(
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
    fecha_de_hoy: date = Depends(hoy),
) -> dict[str, Any]:
    propias = _unidades_de_la_persona(sesion, identidad)
    nombres = identificadores_de_unidades(sesion, list(propias))
    edificios = {c: cargar_complejo(sesion, c) for c in {c for c, _ in propias.values()}}
    emisiones = {c: ultima_emision_vigente(sesion, complejo_id=c) for c in edificios}
    filas = []
    for unidad_id, (complejo_id, vinculo) in propias.items():
        edificio = edificios[complejo_id]
        if edificio is None or unidad_id not in nombres:  # lo impide la FK: no se llega
            continue
        cifras = cifras_de_unidad(
            sesion,
            unidad_id=unidad_id,
            fecha=fecha_de_hoy,
            emision_id=emisiones[complejo_id],
            sin_extraordinaria=vinculo == INQUILINO,
        )
        filas.append((edificio.nombre, nombres[unidad_id], unidad_id, complejo_id, vinculo, cifras))
    filas.sort(key=lambda f: (f[0], clave_de_orden_natural(f[1], f[2])))
    return {
        "fecha": fecha_de_hoy.isoformat(),
        "conjunto": {
            campo: sumar(getattr(f[5], campo) for f in filas).a_texto()
            for campo in ("total_a_pagar", "intereses", "credito_aplicable", "credito_retenido")
        },
        "unidades": [
            {
                "unidad_id": str(unidad_id),
                "identificador": identificador,
                "vinculo": vinculo,
                "complejo_id": str(complejo_id),
                "edificio": nombre,
                "total_a_pagar": c.total_a_pagar.a_texto(),
                "vencimiento": None if c.vencimiento is None else c.vencimiento.isoformat(),
                "deuda_anterior": c.deuda_anterior.a_texto(),
                "intereses": c.intereses.a_texto(),
                "credito_aplicable": c.credito_aplicable.a_texto(),
                "credito_retenido": c.credito_retenido.a_texto(),
            }
            for nombre, identificador, unidad_id, complejo_id, vinculo, c in filas
        ],
    }


@router.get("/mis-unidades/{unidad_id}/pagos")
def pagos_de_mi_unidad(
    unidad_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, str]]:
    _, vinculo = _mi_unidad(sesion, identidad, unidad_id)
    return pagos_confirmados_de_unidad(
        sesion, unidad_id=unidad_id, sin_extraordinaria=vinculo == INQUILINO
    )


@router.get("/mis-unidades/{unidad_id}/documentos")
def documentos_de_mi_unidad(
    unidad_id: UUID,
    request: Request,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    """Los PDFs de la variante del vínculo (D-106), con el enlace firmado del 7 al listar."""
    _, vinculo = _mi_unidad(sesion, identidad, unidad_id)
    try:
        clave = request.app.state.configuracion.clave_de_enlaces()
    except ConfiguracionInvalida:
        raise HTTPException(status_code=503, detail="enlaces_no_configurados") from None
    variante = "sin_extraordinaria" if vinculo == INQUILINO else "completa"
    vence_en = (datetime.now(UTC) + VIGENCIA_DEL_ENLACE).replace(microsecond=0)
    resultado = []
    for d in documentos.documentos_de_unidad(sesion, unidad_id=unidad_id, variante=variante):
        token = enlaces.firmar_enlace(
            administracion_id=identidad.administracion_id,
            documento_id=UUID(d["documento_id"]),
            variante=d["variante"],
            vence_en=vence_en,
            clave=clave,
        )
        resultado.append(
            {
                **d,
                "url": f"/api/documentos/descarga?token={token}",
                "vence_en": vence_en.isoformat(),
            }
        )
    return resultado


@router.get("/mis-unidades/{unidad_id}/cargos-particulares/{cargo_id}")
def cargo_de_mi_unidad(
    unidad_id: UUID,
    cargo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    """Cierra D3 del 6: el cargo particular aprobado de la unidad, de sólo lectura. Un cargo de
    otra unidad (aunque sea otra mía) o en borrador no existe para el vecino."""
    _mi_unidad(sesion, identidad, unidad_id)
    cargo = cargos_particulares.cargar_cargo(sesion, cargo_id)
    if cargo is None or cargo["unidad_id"] != unidad_id or cargo["estado"] != "aprobado":
        raise _no_encontrado()
    return cargo


@router.get("/mis-unidades/{unidad_id}/liquidaciones")
def liquidaciones_de_mi_unidad(
    unidad_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, str]]:
    """Las expensas emitidas y no anuladas del edificio, con el total de mi unidad. No distribuye
    ni escribe nada."""
    complejo_id, vinculo = _mi_unidad(sesion, identidad, unidad_id)
    return expensa_del_vecino.listar_de_la_unidad(
        sesion, complejo_id=complejo_id, unidad_id=unidad_id, vinculo=vinculo
    )


@router.get("/mis-unidades/{unidad_id}/liquidaciones/{liquidacion_id}")
def liquidacion_de_mi_unidad(
    unidad_id: UUID,
    liquidacion_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    """La expensa explicada (R16), comparada con la anterior. La primera lectura de una emitida la
    distribuye con origen `portal` (D-074); es lo único que escribe, y es idempotente."""
    complejo_id, vinculo = _mi_unidad(sesion, identidad, unidad_id)
    try:
        detalle = expensa_del_vecino.detalle_de_la_unidad(
            sesion,
            complejo_id=complejo_id,
            unidad_id=unidad_id,
            liquidacion_id=liquidacion_id,
            vinculo=vinculo,
            identidad_persona_id=identidad.persona_id,
            request_id=UUID(request_id_actual.get() or ""),
        )
    except NoEncontrado:
        sesion.rollback()
        raise _no_encontrado() from None
    sesion.commit()
    return detalle
