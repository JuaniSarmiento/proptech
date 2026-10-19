"""Los tres endpoints mínimos del candado (D7, cambio 2a, tareas 4.2 y 5.x):
ver un complejo, ver una unidad, asignar un edificio a una persona.

Compone `complejos.aplicacion` (cargar) y `acceso.aplicacion` + `acceso.
dominio.permisos` (autorizar, D-096): nunca al revés (D-021, frontera
verificada en `test_fronteras_de_modulos.py`). El orden de cada endpoint es
siempre el de D7: cargar el recurso en la sesión con tenant (ya filtrada
por RLS) → si no existe o no alcanza, 404 (`_no_encontrado()`, siempre la
misma respuesta, para no filtrar cuál de los dos pasó, L-017) → si no
puede, 403 con `permiso_faltante` (tarea 5.3).
"""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator
from sqlalchemy.orm import Session

from proptech_api.acceso import identidad_actual, sesion_con_tenant
from proptech_api.cuerpos import CuerpoDeAlta
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones, existe_persona
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, alcanza, puede
from proptech_core.compartido.coeficientes import Coeficiente
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.compartido.superficie import Superficie
from proptech_core.complejos.aplicacion import grupos, unidades
from proptech_core.complejos.aplicacion.errores import Conflicto, EntradaInvalida, NoEncontrado
from proptech_core.complejos.aplicacion.escritura import (
    asignar_complejo_a_persona,
    confirmar_sin_saldos_previos,
    crear_edificio,
)
from proptech_core.complejos.aplicacion.lectura import (
    ComplejoLeido,
    cargar_complejo,
    cargar_grupo,
    cargar_unidad,
    listar_complejos,
)
from proptech_core.complejos.aplicacion.unidades import listar_unidades
from proptech_core.complejos.dominio.configuracion import ConfiguracionEdificio

#: `strict=True` de `CuerpoDeAlta` exige una instancia de `UUID` en modo
#: "python" (D7, R11); un `UUID` de cuerpo tiene que volver a aceptar su
#: única representación posible en JSON (texto) con `strict=False` puntual
#: — el resto del cuerpo (acá, `rol`) sigue estricto.
_UUIDDeCuerpo = Annotated[UUID, Field(strict=False)]

router = APIRouter(prefix="/api")


def _no_encontrado() -> HTTPException:
    """Una sola función para "no existe" y "no alcanza" (L-017): las dos
    tienen que dar exactamente la misma respuesta, nunca una variación que
    delate cuál de las dos pasó."""
    return HTTPException(status_code=404, detail="no encontrado")


async def manejar_error_de_complejos(_request: Request, error: Exception) -> JSONResponse:
    if isinstance(error, NoEncontrado):
        return JSONResponse(status_code=404, content={"detail": "no encontrado"})
    if isinstance(error, Conflicto):
        return JSONResponse(status_code=409, content={"detail": "conflicto", "campo": error.campo})
    if isinstance(error, EntradaInvalida):
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {
                        "loc": ["body", *error.campo.split(".")],
                        "msg": error.motivo,
                        "type": "value_error",
                    }
                ]
            },
        )
    raise TypeError("error de complejos inesperado")


def _autorizar(
    sesion: Session, identidad: Identidad, accion: Accion, complejo_id: UUID | None
) -> None:
    if not puede(cargar_asignaciones(sesion, identidad.persona_id), accion, complejo_id):
        raise HTTPException(
            status_code=403, detail={"detalle": "sin_permiso", "permiso_faltante": accion.value}
        )


def _edificio_autorizado(
    sesion: Session, identidad: Identidad, complejo_id: UUID, accion: Accion
) -> ComplejoLeido:
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if edificio is None or not alcanza(asignaciones, complejo_id):
        raise _no_encontrado()
    _autorizar(sesion, identidad, accion, complejo_id)
    return edificio


class CuerpoEdificio(CuerpoDeAlta):
    nombre: str = Field(min_length=1, max_length=200)
    localidad: str = Field(min_length=1, max_length=200)
    configuracion_inicial: ConfiguracionEdificio | None = None


class CuerpoUnidad(unidades.DatosUnidad, CuerpoDeAlta):
    pass


class CuerpoDeEdicion(CuerpoDeAlta):
    """Un PATCH puede omitir campos, pero no anularlos."""

    @field_validator("*", mode="before", check_fields=False)
    @classmethod
    def no_nulo(cls, valor: Any) -> Any:
        if valor is None:
            raise ValueError("el campo no admite null")
        return valor


class CuerpoEdicionUnidad(CuerpoDeEdicion):
    identificador: str | None = Field(default=None, min_length=1, max_length=40)
    tipo: str | None = None
    piso: str | None = None
    coeficiente: Coeficiente | None = None
    superficie_m2: Superficie | None = None

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, valor: str | None) -> str | None:
        return None if valor is None else unidades.DatosUnidad.tipo_valido(valor)

    @field_validator("superficie_m2")
    @classmethod
    def superficie_positiva(cls, valor: Superficie | None) -> Superficie | None:
        return None if valor is None else unidades.DatosUnidad.superficie_positiva(valor)


class CuerpoMiembro(CuerpoDeAlta):
    unidad_id: _UUIDDeCuerpo
    coeficiente: Coeficiente | None = None


class CuerpoMiembros(CuerpoDeAlta):
    modo_de_coeficientes: Literal["renormalizado", "propios"] = "renormalizado"
    unidades: list[CuerpoMiembro]


class CuerpoGrupo(grupos.DatosGrupo, CuerpoDeAlta):
    modo_de_coeficientes: Literal["renormalizado", "propios"] = "renormalizado"
    unidades: list[CuerpoMiembro] = Field(default_factory=list)


class CuerpoEdicionGrupo(CuerpoDeEdicion):
    clave: str | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    metodo: Literal["coeficiente", "superficie", "partes_iguales"] | None = None

    @field_validator("clave")
    @classmethod
    def clave_valida(cls, valor: str | None) -> str | None:
        return None if valor is None else grupos.DatosGrupo.clave_valida(valor)


@router.get("/complejos")
def mis_edificios(
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, str]]:
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if not asignaciones:
        raise HTTPException(status_code=403, detail="sin_permiso")
    return [
        {"id": str(e.id), "nombre": e.nombre, "localidad": e.localidad}
        for e in listar_complejos(sesion)
        if alcanza(asignaciones, e.id)
    ]


@router.post("/complejos", status_code=201)
def alta_edificio(
    cuerpo: CuerpoEdificio,
    request: Request,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _autorizar(sesion, identidad, Accion.CREAR_EDIFICIO, None)
    if cuerpo.configuracion_inicial is not None:
        try:
            cuerpo.configuracion_inicial.validar_rango_recargo(request.app.state.parametros)
        except ValueError:
            raise EntradaInvalida("configuracion_inicial.recargo_segundo_vencimiento") from None
    id_ = crear_edificio(
        sesion,
        identidad,
        nombre=cuerpo.nombre,
        localidad=cuerpo.localidad,
        parametros=request.app.state.parametros,
        reloj=lambda: datetime.now(UTC),
        request_id=UUID(request_id_actual.get() or ""),
        configuracion_inicial=cuerpo.configuracion_inicial,
    )
    sesion.commit()
    return {"id": str(id_)}


@router.get("/complejos/{complejo_id}/resumen")
def resumen_edificio(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    edificio = _edificio_autorizado(
        sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO
    )
    return {
        "estado_migracion": edificio.estado_migracion,
        "informe": listar_unidades(sesion, complejo_id)["informe"],
    }


@router.post("/complejos/{complejo_id}/estado-de-migracion/sin-saldos-previos")
def confirmar_edificio(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.CONFIRMAR_SIN_SALDOS_PREVIOS)
    confirmar_sin_saldos_previos(
        sesion, identidad, complejo_id=complejo_id, request_id=UUID(request_id_actual.get() or "")
    )
    sesion.commit()
    return {"id": str(complejo_id), "estado_migracion": "sin_saldos_previos"}


@router.get("/complejos/{complejo_id}")
def ver_complejo(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    complejo = cargar_complejo(sesion, complejo_id)
    if complejo is None:
        raise _no_encontrado()
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if not alcanza(asignaciones, complejo_id):
        raise _no_encontrado()
    return {
        "id": str(complejo.id),
        "administracion_id": str(complejo.administracion_id),
        "nombre": complejo.nombre,
        "localidad": complejo.localidad,
    }


@router.get("/unidades/{unidad_id}")
def ver_unidad(
    unidad_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    unidad = cargar_unidad(sesion, unidad_id)
    if unidad is None:
        raise _no_encontrado()
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if not alcanza(asignaciones, unidad.complejo_id, unidad_id):
        raise _no_encontrado()
    return {
        "id": str(unidad.id),
        "administracion_id": str(unidad.administracion_id),
        "complejo_id": str(unidad.complejo_id),
        "identificador": unidad.identificador,
        "tipo": unidad.tipo,
        "piso": unidad.piso,
        "coeficiente": unidad.coeficiente,
        "superficie_m2": unidad.superficie_m2,
    }


@router.get("/complejos/{complejo_id}/unidades")
def padron_del_edificio(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return dict(unidades.listar_unidades(sesion, complejo_id))


@router.post("/complejos/{complejo_id}/unidades", status_code=201)
def alta_unidad(
    complejo_id: UUID,
    cuerpo: CuerpoUnidad,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.CONFIGURAR_PADRON)
    id_ = unidades.crear_unidad(
        sesion, identidad, complejo_id=complejo_id, datos=cuerpo.model_dump()
    )
    respuesta = ver_unidad(id_, identidad, sesion)
    sesion.commit()
    return respuesta


@router.patch("/unidades/{unidad_id}")
def modificar_unidad(
    unidad_id: UUID,
    cuerpo: CuerpoEdicionUnidad,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    unidad = cargar_unidad(sesion, unidad_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if unidad is None or not alcanza(asignaciones, unidad.complejo_id, unidad_id):
        raise _no_encontrado()
    _edificio_autorizado(sesion, identidad, unidad.complejo_id, Accion.CONFIGURAR_PADRON)
    unidades.editar_unidad(
        sesion, unidad_id=unidad_id, cambios=cuerpo.model_dump(exclude_unset=True)
    )
    respuesta = ver_unidad(unidad_id, identidad, sesion)
    sesion.commit()
    return respuesta


def _autorizar_grupo(sesion: Session, identidad: Identidad, grupo_id: UUID) -> None:
    grupo = cargar_grupo(sesion, grupo_id)
    if grupo is None:
        raise _no_encontrado()
    _edificio_autorizado(sesion, identidad, grupo["complejo_id"], Accion.CONFIGURAR_PADRON)


@router.get("/complejos/{complejo_id}/grupos")
def grupos_del_edificio(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return grupos.listar_grupos(sesion, complejo_id)


@router.post("/complejos/{complejo_id}/grupos", status_code=201)
def alta_grupo(
    complejo_id: UUID,
    cuerpo: CuerpoGrupo,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.CONFIGURAR_PADRON)
    id_ = grupos.crear_grupo(
        sesion,
        identidad,
        complejo_id=complejo_id,
        datos=cuerpo.model_dump(include={"clave", "nombre", "metodo"}),
        miembros=[m.model_dump() for m in cuerpo.unidades],
        modo=cuerpo.modo_de_coeficientes,
    )
    sesion.commit()
    return {"id": str(id_)}


@router.patch("/grupos/{grupo_id}")
def modificar_grupo(
    grupo_id: UUID,
    cuerpo: CuerpoEdicionGrupo,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _autorizar_grupo(sesion, identidad, grupo_id)
    grupos.editar_grupo(sesion, grupo_id=grupo_id, cambios=cuerpo.model_dump(exclude_unset=True))
    sesion.commit()
    return {"id": str(grupo_id)}


@router.put("/grupos/{grupo_id}/unidades")
def reemplazar_miembros(
    grupo_id: UUID,
    cuerpo: CuerpoMiembros,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _autorizar_grupo(sesion, identidad, grupo_id)
    grupos.fijar_unidades(
        sesion,
        grupo_id=grupo_id,
        modo=cuerpo.modo_de_coeficientes,
        miembros=[m.model_dump() for m in cuerpo.unidades],
    )
    sesion.commit()
    return {"id": str(grupo_id)}


class CuerpoAsignacion(CuerpoDeAlta):
    persona_id: _UUIDDeCuerpo
    rol: str
    nivel: str | None = None
    # Se acepta para que un cuerpo que lo manda no explote con un campo
    # desconocido (422), pero se ignora a propósito (D7, D4): el tenant de
    # la fila sale siempre de la identidad, nunca de un campo del cuerpo.
    # Diferencia conocida con el resto del cambio (D7): acá NO da 422 por
    # nombrarlo (está declarado, no es "extra"); `id` y `complejo_id`, que
    # nunca se declaran, sí.
    administracion_id: _UUIDDeCuerpo | None = None


#: La acción de D-096 que este endpoint autoriza (D9: el mismo nombre que
#: va a quedar registrado en la auditoría, tarea 6.x).
_ACCION = Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS


@router.post("/complejos/{complejo_id}/asignaciones", status_code=201)
def asignar_complejo(
    complejo_id: UUID,
    cuerpo: CuerpoAsignacion,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    complejo = cargar_complejo(sesion, complejo_id)
    if complejo is None:
        raise _no_encontrado()
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if not alcanza(asignaciones, complejo_id):
        raise _no_encontrado()
    if not puede(asignaciones, _ACCION, complejo_id):
        raise HTTPException(
            status_code=403,
            detail={"detalle": "sin_permiso", "permiso_faltante": _ACCION.value},
        )
    # La persona destino (del cuerpo, no del path): recién después del
    # permiso, para no revelar si existe antes de confirmar que quien pide
    # puede hacer esta acción en este complejo.
    if not existe_persona(sesion, cuerpo.persona_id):
        raise _no_encontrado()

    # El request_id lo fija el middleware (D8): siempre un UUID canónico
    # dentro de un pedido real (`seguimiento.validar_request_id`).
    request_id = UUID(request_id_actual.get() or "")
    nueva_id = asignar_complejo_a_persona(
        sesion,
        identidad,
        complejo_id=complejo_id,
        persona_id=cuerpo.persona_id,
        rol=cuerpo.rol,
        nivel=cuerpo.nivel,
        request_id=request_id,
    )
    sesion.commit()
    return {"id": str(nueva_id)}
