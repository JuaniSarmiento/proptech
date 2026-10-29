"""Proveedores del edificio (R12, D-019; cambio 6 `gastos-y-cargos`, bloque 2).

Mismo orden de D7 que `complejos.py`: cargar el recurso → 404 si no existe
o no alcanza → 403 si no puede. La lectura usa `Accion.VER_CONFIGURACION_
DEL_EDIFICIO` (mismo gate que categorías/grupos/unidades, D-096: ya
alcanza al contador, al auxiliar y al consejo); la escritura usa
`Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION` (proposal.md · What Changes).
Ninguna acción nueva se agrega a la matriz de D-106.
"""

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.complejos import CuerpoDeEdicion
from proptech_api.cuerpos import CuerpoDeAlta
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, alcanza, puede
from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.gastos.adaptadores.excel import LectorDePlanillaExcel, PlanillaInvalida
from proptech_core.gastos.aplicacion import (
    cargos_particulares,
    gastos,
    notas_de_credito,
    proveedores,
)
from proptech_core.gastos.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    ImportacionInvalida,
    NoEncontrado,
)

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)


def _no_encontrado() -> HTTPException:
    return HTTPException(status_code=404, detail="no encontrado")


async def manejar_error_de_gastos(_request: Request, error: Exception) -> JSONResponse:
    if isinstance(error, NoEncontrado):
        return JSONResponse(status_code=404, content={"detail": "no encontrado"})
    if isinstance(error, Conflicto):
        return JSONResponse(status_code=409, content={"detail": "conflicto", "campo": error.campo})
    if isinstance(error, EntradaInvalida):
        item: dict[str, object] = {
            "loc": ["body", *error.campo.split(".")],
            "msg": error.motivo,
            "type": error.tipo,
        }
        if error.identificadores is not None:
            item["identificadores"] = error.identificadores
        return JSONResponse(status_code=422, content={"detail": [item]})
    if isinstance(error, ImportacionInvalida):
        #: D6: TODAS las filas con problema, nunca sólo la primera.
        return JSONResponse(status_code=422, content={"detail": error.errores})
    if isinstance(error, PlanillaInvalida):
        return JSONResponse(status_code=422, content={"detail": [{"msg": "planilla inválida"}]})
    raise TypeError("error de gastos inesperado")


def _edificio_autorizado(
    sesion: Session, identidad: Identidad, complejo_id: UUID, accion: Accion
) -> None:
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if edificio is None or not alcanza(asignaciones, complejo_id):
        raise _no_encontrado()
    if not puede(asignaciones, accion, complejo_id):
        raise HTTPException(
            status_code=403, detail={"detalle": "sin_permiso", "permiso_faltante": accion.value}
        )


def _autorizar_proveedor(
    sesion: Session, identidad: Identidad, proveedor_id: UUID
) -> dict[str, Any]:
    proveedor = proveedores.cargar_proveedor(sesion, proveedor_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if proveedor is None or not alcanza(asignaciones, proveedor["complejo_id"]):
        raise _no_encontrado()
    if not puede(
        asignaciones, Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION, proveedor["complejo_id"]
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "detalle": "sin_permiso",
                "permiso_faltante": Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION.value,
            },
        )
    return proveedor


class CuerpoProveedor(CuerpoDeAlta):
    razon_social: Annotated[str, Field(min_length=1, max_length=200)]
    cuit: str


class CuerpoEdicionProveedor(CuerpoDeEdicion):
    razon_social: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    activo: bool | None = None


@router.get("/complejos/{complejo_id}/proveedores")
def proveedores_del_edificio(
    complejo_id: UUID,
    solo_activos: bool = False,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return proveedores.listar_proveedores(sesion, complejo_id, solo_activos=solo_activos)


@router.post("/complejos/{complejo_id}/proveedores", status_code=201)
def alta_proveedor(
    complejo_id: UUID,
    cuerpo: CuerpoProveedor,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_autorizado(
        sesion, identidad, complejo_id, Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION
    )
    id_ = proveedores.crear_proveedor(
        sesion,
        identidad,
        complejo_id=complejo_id,
        datos=cuerpo.model_dump(),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"id": str(id_)}


@router.patch("/proveedores/{proveedor_id}")
def modificar_proveedor(
    proveedor_id: UUID,
    cuerpo: CuerpoEdicionProveedor,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _autorizar_proveedor(sesion, identidad, proveedor_id)
    proveedores.editar_proveedor(
        sesion,
        identidad,
        proveedor_id=proveedor_id,
        cambios=cuerpo.model_dump(exclude_unset=True),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"id": str(proveedor_id)}


# --- Bloque 3: gastos (R12, R13, R16, D-075) ---


def _autorizar_gasto(sesion: Session, identidad: Identidad, gasto_id: UUID) -> dict[str, Any]:
    gasto = gastos.cargar_gasto(sesion, gasto_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if gasto is None or not alcanza(asignaciones, gasto["complejo_id"]):
        raise _no_encontrado()
    if not puede(asignaciones, Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION, gasto["complejo_id"]):
        raise HTTPException(
            status_code=403,
            detail={
                "detalle": "sin_permiso",
                "permiso_faltante": Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION.value,
            },
        )
    return gasto


#: `strict=True` (heredado de `CuerpoDeAlta`) exige instancias de `UUID`/
#: `date` en modo "python"; un cuerpo JSON sólo puede mandar su única
#: representación posible (texto), así que estos dos campos vuelven a
#: `strict=False` puntual, igual que `_UUIDDeCuerpo` en `complejos.py`.
_UUIDDeCuerpo = Annotated[UUID, Field(strict=False)]
_FechaDeCuerpo = Annotated[date, Field(strict=False)]


class CuerpoGasto(CuerpoDeAlta):
    concepto: Annotated[str, Field(min_length=1, max_length=200)]
    categoria_id: _UUIDDeCuerpo
    grupo_id: _UUIDDeCuerpo
    proveedor_id: _UUIDDeCuerpo | None = None
    periodo: _FechaDeCuerpo
    tipo: str = "ordinario"
    importe: Dinero
    cuit_emisor: str | None = None
    punto_de_venta: str | None = None
    tipo_de_comprobante: str | None = None
    numero_de_comprobante: str | None = None
    documento_receptor: str | None = None


class CuerpoEdicionGasto(CuerpoDeEdicion):
    concepto: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    categoria_id: _UUIDDeCuerpo | None = None
    grupo_id: _UUIDDeCuerpo | None = None
    proveedor_id: _UUIDDeCuerpo | None = None
    periodo: _FechaDeCuerpo | None = None
    tipo: str | None = None
    importe: Dinero | None = None
    cuit_emisor: str | None = None
    punto_de_venta: str | None = None
    tipo_de_comprobante: str | None = None
    numero_de_comprobante: str | None = None
    documento_receptor: str | None = None


@router.get("/complejos/{complejo_id}/gastos")
def gastos_del_edificio(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return gastos.listar_gastos(sesion, complejo_id)


@router.post("/complejos/{complejo_id}/gastos", status_code=201)
def alta_gasto(
    complejo_id: UUID,
    cuerpo: CuerpoGasto,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_autorizado(
        sesion, identidad, complejo_id, Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION
    )
    id_, aviso = gastos.crear_gasto(
        sesion,
        identidad,
        complejo_id=complejo_id,
        datos=cuerpo.model_dump(),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    if aviso is not None:
        return {"id": str(id_), "aviso": aviso}
    return {"id": str(id_)}


@router.get("/gastos/{gasto_id}")
def ver_gasto(
    gasto_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    gasto = gastos.cargar_gasto(sesion, gasto_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if gasto is None or not alcanza(asignaciones, gasto["complejo_id"]):
        raise _no_encontrado()
    return gasto


@router.patch("/gastos/{gasto_id}")
def modificar_gasto(
    gasto_id: UUID,
    cuerpo: CuerpoEdicionGasto,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _autorizar_gasto(sesion, identidad, gasto_id)
    gastos.editar_gasto(
        sesion,
        identidad,
        gasto_id=gasto_id,
        cambios=cuerpo.model_dump(exclude_unset=True),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"id": str(gasto_id)}


@router.post("/gastos/{gasto_id}/aprobar")
def aprobar_gasto(
    gasto_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _autorizar_gasto(sesion, identidad, gasto_id)
    gastos.aprobar_gasto(
        sesion, identidad, gasto_id=gasto_id, request_id=UUID(request_id_actual.get() or "")
    )
    sesion.commit()
    return {"id": str(gasto_id)}


@router.get("/complejos/{complejo_id}/periodos/{periodo}/gastos-aprobados")
def gastos_aprobados_del_periodo(
    complejo_id: UUID,
    periodo: date,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return gastos.gastos_aprobados_del_periodo(sesion, complejo_id, periodo)


@router.get("/complejos/{complejo_id}/periodos/{periodo}/obligatorios-faltantes")
def obligatorios_faltantes_del_periodo(
    complejo_id: UUID,
    periodo: date,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return gastos.obligatorios_faltantes(sesion, complejo_id, periodo)


# --- Bloque 4: notas de crédito (R22, D-061, D-082) ---


class CuerpoNotaDeCredito(CuerpoDeAlta):
    #: Requerido, sin default (escenario "Nota de crédito sin factura"): se
    #: omite -> 422 de pydantic, nombrando el campo, antes de llegar a D7.
    gasto_id: _UUIDDeCuerpo
    importe: Dinero
    periodo: _FechaDeCuerpo
    cuit_emisor: str
    punto_de_venta: str
    tipo_de_comprobante: str
    numero_de_comprobante: str


@router.post("/notas-de-credito", status_code=201)
def alta_nota_de_credito(
    cuerpo: CuerpoNotaDeCredito,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    #: Mismo orden de D7 que el resto del router: cargar el recurso (la
    #: factura) → 404 si no existe o no alcanza → 403 si no puede.
    _autorizar_gasto(sesion, identidad, cuerpo.gasto_id)
    id_ = notas_de_credito.crear_nota_de_credito(
        sesion,
        identidad,
        gasto_id=cuerpo.gasto_id,
        datos=cuerpo.model_dump(exclude={"gasto_id"}),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"id": str(id_)}


@router.get("/notas-de-credito/{nota_id}")
def ver_nota_de_credito(
    nota_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    nota = notas_de_credito.cargar_nota_de_credito(sesion, nota_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if nota is None or not alcanza(asignaciones, nota["complejo_id"]):
        raise _no_encontrado()
    return nota


# --- Bloque 5: cargos particulares (R14, D-025) ---


def _autorizar_cargo(sesion: Session, identidad: Identidad, cargo_id: UUID) -> dict[str, Any]:
    cargo = cargos_particulares.cargar_cargo(sesion, cargo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if cargo is None or not alcanza(asignaciones, cargo["complejo_id"]):
        raise _no_encontrado()
    if not puede(asignaciones, Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION, cargo["complejo_id"]):
        raise HTTPException(
            status_code=403,
            detail={
                "detalle": "sin_permiso",
                "permiso_faltante": Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION.value,
            },
        )
    return cargo


class CuerpoCargoParticular(CuerpoDeAlta):
    unidad_id: _UUIDDeCuerpo
    concepto: Annotated[str, Field(min_length=1, max_length=200)]
    importe: Dinero
    periodo: _FechaDeCuerpo
    motivo: Annotated[str, Field(min_length=1, max_length=500)]


class CuerpoEdicionCargoParticular(CuerpoDeEdicion):
    unidad_id: _UUIDDeCuerpo | None = None
    concepto: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    importe: Dinero | None = None
    periodo: _FechaDeCuerpo | None = None
    motivo: Annotated[str, Field(min_length=1, max_length=500)] | None = None


@router.get("/complejos/{complejo_id}/cargos-particulares")
def cargos_del_edificio(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return cargos_particulares.listar_cargos(sesion, complejo_id)


@router.post("/complejos/{complejo_id}/cargos-particulares", status_code=201)
def alta_cargo_particular(
    complejo_id: UUID,
    cuerpo: CuerpoCargoParticular,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_autorizado(
        sesion, identidad, complejo_id, Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION
    )
    id_ = cargos_particulares.crear_cargo_particular(
        sesion,
        identidad,
        complejo_id=complejo_id,
        datos=cuerpo.model_dump(),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"id": str(id_)}


@router.get("/cargos-particulares/{cargo_id}")
def ver_cargo_particular(
    cargo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    cargo = cargos_particulares.cargar_cargo(sesion, cargo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if cargo is None or not alcanza(asignaciones, cargo["complejo_id"]):
        raise _no_encontrado()
    return cargo


@router.patch("/cargos-particulares/{cargo_id}")
def modificar_cargo_particular(
    cargo_id: UUID,
    cuerpo: CuerpoEdicionCargoParticular,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _autorizar_cargo(sesion, identidad, cargo_id)
    cargos_particulares.editar_cargo_particular(
        sesion,
        identidad,
        cargo_id=cargo_id,
        cambios=cuerpo.model_dump(exclude_unset=True),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"id": str(cargo_id)}


@router.post("/cargos-particulares/{cargo_id}/aprobar")
def aprobar_cargo_particular(
    cargo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _autorizar_cargo(sesion, identidad, cargo_id)
    cargos_particulares.aprobar_cargo_particular(
        sesion, identidad, cargo_id=cargo_id, request_id=UUID(request_id_actual.get() or "")
    )
    sesion.commit()
    return {"id": str(cargo_id)}


@router.get("/complejos/{complejo_id}/periodos/{periodo}/cargos-aprobados")
def cargos_aprobados_del_periodo(
    complejo_id: UUID,
    periodo: date,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return cargos_particulares.cargos_aprobados_del_periodo(sesion, complejo_id, periodo)


@router.post("/complejos/{complejo_id}/cargos-particulares/importar")
async def importar_cargos_particulares(
    complejo_id: UUID,
    periodo: date,
    archivo: UploadFile = File(...),
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, int]:
    _edificio_autorizado(
        sesion, identidad, complejo_id, Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION
    )
    contenido = await archivo.read()
    cantidad = cargos_particulares.importar_cargos_particulares(
        sesion,
        identidad,
        complejo_id=complejo_id,
        lector=LectorDePlanillaExcel(),
        contenido=contenido,
        periodo=periodo,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"creados": cantidad}
