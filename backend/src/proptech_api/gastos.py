"""Proveedores del edificio (R12, D-019; cambio 6 `gastos-y-cargos`, bloque 2).

Mismo orden de D7 que `complejos.py`: cargar el recurso → 404 si no existe
o no alcanza → 403 si no puede. La lectura usa `Accion.VER_CONFIGURACION_
DEL_EDIFICIO` (mismo gate que categorías/grupos/unidades, D-096: ya
alcanza al contador, al auxiliar y al consejo); la escritura usa
`Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION` (proposal.md · What Changes).
Ninguna acción nueva se agrega a la matriz de D-106.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

import anyio.from_thread
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import Field
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.complejos import CuerpoDeEdicion
from proptech_api.cuerpos import CuerpoDeAlta
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, Asignacion, alcanza, puede
from proptech_core.compartido.base_de_datos import abrir_sesion
from proptech_core.compartido.configuracion import ConfiguracionInvalida
from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.enlaces import EnlaceVencido
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.gastos.adaptadores.excel import LectorDePlanillaExcel, PlanillaInvalida
from proptech_core.gastos.adaptadores.qr import LectorDeQrConZxing
from proptech_core.gastos.aplicacion import (
    cargos_particulares,
    enlaces,
    facturas,
    gastos,
    lectura_de_factura,
    notas_de_credito,
    proveedores,
)
from proptech_core.gastos.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    ImportacionInvalida,
    NoEncontrado,
)
from proptech_core.gastos.dominio.archivo_de_factura import TAMANO_MAXIMO, TIPOS_MIME
from proptech_core.gastos.puertos import LectorDeQr
from proptech_core.liquidacion.aplicacion.periodos import es_periodo_emitido

_logger = logging.getLogger("proptech_api.gastos")

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)
#: La descarga de la factura (H-036): pública por diseño. El token firmado ES la autorización
#: (D-070), así que no pasa por identidad ni por tenant: el tenant sale del token verificado.
router_de_descarga = APIRouter(prefix="/api")
#: Cuánto dura un enlace de descarga de la factura (D-070).
VIGENCIA_DEL_ENLACE = timedelta(minutes=15)


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


def _lectura_autorizada(asignaciones: list[Asignacion], complejo_id: UUID) -> None:
    """Detalle por id: el mismo permiso de lectura que el listado del recurso
    (`ver_configuracion_del_edificio`), no sólo alcanzar el edificio. Orden
    de D7: 404 si no alcanza, 403 si no puede."""
    if not alcanza(asignaciones, complejo_id):
        raise _no_encontrado()
    if not puede(asignaciones, Accion.VER_CONFIGURACION_DEL_EDIFICIO, complejo_id):
        raise HTTPException(
            status_code=403,
            detail={
                "codigo": "sin_permiso",
                "detalle": "sin_permiso",
                "permiso_faltante": Accion.VER_CONFIGURACION_DEL_EDIFICIO.value,
            },
        )


def _edificio_autorizado(
    sesion: Session, identidad: Identidad, complejo_id: UUID, accion: Accion
) -> None:
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if edificio is None or not alcanza(asignaciones, complejo_id):
        raise _no_encontrado()
    if not puede(asignaciones, accion, complejo_id):
        raise HTTPException(
            status_code=403,
            detail={
                "codigo": "sin_permiso",
                "detalle": "sin_permiso",
                "permiso_faltante": accion.value,
            },
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
                "codigo": "sin_permiso",
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
                "codigo": "sin_permiso",
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


# --- H-036: la factura con QR de ARCA (R12, D-169) ---


def lector_de_qr() -> LectorDeQr:
    """El lector del QR de las facturas. Es una dependencia para que la aceptación ponga uno
    falso."""
    return LectorDeQrConZxing()


def _clave_de_enlaces(request: Request) -> str:
    try:
        return str(request.app.state.configuracion.clave_de_enlaces())
    except ConfiguracionInvalida:
        raise HTTPException(status_code=503, detail="enlaces_no_configurados") from None


def _enlace_de_la_factura(
    request: Request, administracion_id: UUID, gasto_id: UUID
) -> dict[str, str]:
    vence_en = (datetime.now(UTC) + VIGENCIA_DEL_ENLACE).replace(microsecond=0)
    token = enlaces.firmar_enlace_de_la_factura(
        administracion_id=administracion_id,
        gasto_id=gasto_id,
        vence_en=vence_en,
        clave=_clave_de_enlaces(request),
    )
    return {"url": f"/api/facturas/descarga?token={token}", "vence_en": vence_en.isoformat()}


def _encolar_la_lectura(request: Request, identidad: Identidad, gasto_id: UUID) -> None:
    """H-037, después del commit: si la cola falla, el gasto ya está confirmado y el 201 sale igual;
    queda en `borrador` y la persona lo completa (o se reprocesa)."""
    try:
        anyio.from_thread.run(
            lambda: lectura_de_factura.encolar_lectura(
                request.app.state.cola,
                administracion_id=identidad.administracion_id,
                gasto_id=gasto_id,
                request_id=UUID(request_id_actual.get() or ""),
            )
        )
    except Exception as error:  # nada de la cola puede tumbar una subida ya confirmada
        _logger.warning("lectura_sin_encolar", extra={"tipo_error": type(error).__name__})


@router.post("/complejos/{complejo_id}/facturas", status_code=201)
def subir_factura(
    complejo_id: UUID,
    request: Request,
    archivo: Annotated[UploadFile, File()],
    el_lector: LectorDeQr = Depends(lector_de_qr),
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    """Sube una factura (JPEG, PNG o PDF de hasta 10 MB, por sus primeros bytes) y deja el gasto en
    borrador con lo que trae su QR de ARCA, o `sin_qr` con su motivo. 404 si el edificio no alcanza,
    403 sin `cargar_gastos_y_preparar_liquidacion`, 422 si el archivo no sirve, 409 si la factura ya
    está cargada. Se lee un byte de más del tope para saber que se pasó sin cargar un archivo
    enorme."""
    _edificio_autorizado(
        sesion, identidad, complejo_id, Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION
    )
    _clave_de_enlaces(request)
    contenido = archivo.file.read(TAMANO_MAXIMO + 1)
    gasto, aviso = facturas.subir_factura(
        sesion,
        identidad,
        complejo_id=complejo_id,
        contenido=contenido,
        lector=el_lector,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    _encolar_la_lectura(request, identidad, gasto["id"])
    return {
        **gasto,
        "aviso": aviso,
        "factura": _enlace_de_la_factura(request, identidad.administracion_id, gasto["id"]),
    }


@router.post("/gastos/{gasto_id}/factura/enlace", status_code=201)
def enlace_de_la_factura(
    gasto_id: UUID,
    request: Request,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    """Un enlace firmado nuevo que vence a los 15 minutos. Lo pide quien puede leer el gasto (la
    regla de `GET /gastos/{id}`); 404 también si el gasto no tiene factura (se cargó a mano)."""
    gasto = gastos.cargar_gasto(sesion, gasto_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if gasto is None:
        raise _no_encontrado()
    _lectura_autorizada(asignaciones, gasto["complejo_id"])
    if facturas.factura_del_gasto(sesion, gasto_id=gasto_id) is None:
        raise _no_encontrado()
    return _enlace_de_la_factura(request, identidad.administracion_id, gasto_id)


@router_de_descarga.get("/facturas/descarga")
def descargar_la_factura(request: Request, token: Annotated[str, Query()]) -> Response:
    """Sin sesión: el token firmado es la autorización. 200 con los bytes subidos y su tipo; 410
    vencido; 403 alterado, de otro tipo, de un gasto que no existe o de otra administración. Nunca
    se
    abre una sesión de base antes de verificar la firma, y el tenant sale del token verificado."""
    try:
        enlace = enlaces.verificar_enlace_de_la_factura(
            token, clave=_clave_de_enlaces(request), ahora=datetime.now(UTC)
        )
    except EnlaceVencido:
        raise HTTPException(status_code=410, detail="enlace_vencido") from None
    except enlaces.EnlaceAlterado:
        raise HTTPException(status_code=403, detail="enlace_invalido") from None
    sesion = abrir_sesion(request.app.state.fabrica_de_sesiones, enlace.administracion_id)
    try:
        archivada = facturas.factura_del_gasto(sesion, gasto_id=enlace.gasto_id)
        sesion.rollback()
    finally:
        sesion.close()
    if archivada is None:
        raise HTTPException(status_code=403, detail="enlace_invalido")
    contenido, tipo = archivada
    return Response(
        content=contenido,
        media_type=TIPOS_MIME[tipo],
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/gastos/{gasto_id}/lectura")
def lectura_del_gasto(
    gasto_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    """H-037: de dónde sale cada dato del borrador (`qr`, `ia` o `null`), el estado de la lectura
    con su motivo y su detalle. La regla de acceso es la de `GET /gastos/{id}`: 404 si no existe
    o no alcanza."""
    lectura = lectura_de_factura.lectura_del_gasto(sesion, gasto_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if lectura is None:
        raise _no_encontrado()
    _lectura_autorizada(asignaciones, lectura.pop("complejo_id"))
    return lectura


@router.get("/gastos/{gasto_id}")
def ver_gasto(
    gasto_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    gasto = gastos.cargar_gasto(sesion, gasto_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if gasto is None:
        raise _no_encontrado()
    _lectura_autorizada(asignaciones, gasto["complejo_id"])
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
        sesion,
        identidad,
        gasto_id=gasto_id,
        request_id=UUID(request_id_actual.get() or ""),
        # P36, D-141: el período emitido lo dice el libro; `gastos` no importa `liquidacion`.
        es_periodo_emitido=es_periodo_emitido,
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
    if nota is None:
        raise _no_encontrado()
    _lectura_autorizada(asignaciones, nota["complejo_id"])
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
                "codigo": "sin_permiso",
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
    if cargo is None:
        raise _no_encontrado()
    _lectura_autorizada(asignaciones, cargo["complejo_id"])
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
