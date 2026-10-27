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

from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import AfterValidator, Field, field_validator
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.cuerpos import CuerpoDeAlta
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones, existe_persona
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, alcanza, puede
from proptech_core.compartido.coeficientes import Coeficiente
from proptech_core.compartido.parametros import CategoriaDeGasto
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.compartido.superficie import Superficie
from proptech_core.compartido.texto import recortado_sin_control, sin_caracteres_de_control
from proptech_core.complejos.aplicacion import categorias, grupos, unidades
from proptech_core.complejos.aplicacion.errores import Conflicto, EntradaInvalida, NoEncontrado
from proptech_core.complejos.aplicacion.escritura import (
    asignar_complejo_a_persona,
    confirmar_sin_saldos_previos,
    crear_edificio,
    crear_version_de_configuracion,
    editar_edificio,
    hoy_en_mendoza,
)
from proptech_core.complejos.aplicacion.lectura import (
    ComplejoLeido,
    cargar_categoria,
    cargar_complejo,
    cargar_grupo,
    cargar_unidad,
    configuracion_vigente,
    listar_complejos,
    listar_versiones,
)
from proptech_core.complejos.aplicacion.lectura import (
    resumen_edificio as leer_resumen_edificio,
)
from proptech_core.complejos.dominio.configuracion import ConfiguracionEdificio

#: `strict=True` de `CuerpoDeAlta` exige una instancia de `UUID` en modo
#: "python" (D7, R11); un `UUID` de cuerpo tiene que volver a aceptar su
#: única representación posible en JSON (texto) con `strict=False` puntual
#: — el resto del cuerpo (acá, `rol`) sigue estricto.
_UUIDDeCuerpo = Annotated[UUID, Field(strict=False)]

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)


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
    #: R3A-1/R3A-6: nunca un carácter de control, recortados en el borde.
    nombre: Annotated[
        str, Field(min_length=1, max_length=200), AfterValidator(recortado_sin_control)
    ]
    #: D2 (tarea 2.6): el trío es obligatorio en toda alta nueva; `localidad`
    #: deja de ser una entrada — se escribe derivada del nombre de Georef.
    provincia_id: str
    departamento_id: str
    localidad_id: str
    #: H-8/D2: sin `CHECK` de largo en la base (igual que `localidad` hoy);
    #: el máximo de 200 y el recorte de control viven sólo acá.
    calle_y_numero: (
        Annotated[str, Field(max_length=200), AfterValidator(recortado_sin_control)] | None
    ) = None
    #: D3 (tarea 3.2): un edificio nuevo trae las dos cantidades siempre;
    #: `strict=True` (heredado de `CuerpoDeAlta`) ya rechaza `"4"` por texto.
    pisos: Annotated[int, Field(ge=1, le=60)]
    subsuelos: Annotated[int, Field(ge=0, le=5)]
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


class CuerpoEdicionEdificio(CuerpoDeEdicion):
    """D3 (tarea 3.6): sin `administracion_id` ni `estado_migracion` — ni
    siquiera declarados, `extra="forbid"` (heredado) los rechaza con 422
    (escenario "Cambiar la administración por la edición")."""

    nombre: (
        Annotated[str, Field(min_length=1, max_length=200), AfterValidator(recortado_sin_control)]
        | None
    ) = None
    provincia_id: str | None = None
    departamento_id: str | None = None
    localidad_id: str | None = None
    calle_y_numero: (
        Annotated[str, Field(max_length=200), AfterValidator(recortado_sin_control)] | None
    ) = None
    pisos: Annotated[int, Field(ge=1, le=60)] | None = None
    subsuelos: Annotated[int, Field(ge=0, le=5)] | None = None


class CuerpoEdicionUnidad(CuerpoDeEdicion):
    #: R3A-1/R3A-6: misma familia que `unidades.DatosUnidad`.
    identificador: (
        Annotated[str, Field(min_length=1, max_length=40), AfterValidator(recortado_sin_control)]
        | None
    ) = None
    tipo: str | None = None
    piso: Annotated[str, AfterValidator(sin_caracteres_de_control)] | None = None
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
    #: R3A-1/R3A-6: misma familia que `grupos.DatosGrupo`.
    nombre: (
        Annotated[str, Field(min_length=1, max_length=80), AfterValidator(recortado_sin_control)]
        | None
    ) = None
    metodo: Literal["coeficiente", "superficie", "partes_iguales"] | None = None
    #: D7 (tarea 4.5): desactivar/reactivar un grupo parcial; "Generales"
    #: lo rechaza antes de llegar acá (`editar_grupo` corta en
    #: `es_generales`, nunca llega a mirar este campo).
    activo: bool | None = None

    @field_validator("clave")
    @classmethod
    def clave_valida(cls, valor: str | None) -> str | None:
        return None if valor is None else grupos.DatosGrupo.clave_valida(valor)


class CuerpoCategoria(CategoriaDeGasto, CuerpoDeAlta):
    #: R3A-1/R3A-6, revisión final (19/10/2026, arreglo 1): mismo tope que
    #: `CuerpoEdicionCategoria` — el `nombre` heredado de `CategoriaDeGasto`
    #: (`_Nombre`) mide los 80 caracteres DESPUÉS de recortar espacios;
    #: `CuerpoEdicionCategoria` los mide ANTES (`Field(max_length=80)`), como
    #: el resto de la familia (`grupos.DatosGrupo`, `CuerpoEdicionGrupo`). Sin
    #: este override, un nombre de 81 caracteres crudos que recorta a 79 se
    #: podía crear y no se podía volver a mandar igual al editar.
    nombre: Annotated[
        str, Field(min_length=1, max_length=80), AfterValidator(recortado_sin_control)
    ]
    #: D7 (tarea 4.4): sin clave, se deriva de `nombre` en `crear_categoria`
    #: (que vuelve a validar la forma con `CategoriaDeGasto`, nunca confía
    #: en que una clave explícita ya pasó por acá sin control). Angosta el
    #: tipo heredado (`str` → `str | None`): válido en runtime (Pydantic
    #: valida el campo declarado acá, no el de la base), mypy no lo sabe.
    clave: str | None = None  # type: ignore[assignment]


class CuerpoEdicionCategoria(CuerpoDeEdicion):
    #: R3A-1/R3A-6: misma familia que `CategoriaDeGasto` (parametros.py).
    nombre: (
        Annotated[str, Field(min_length=1, max_length=80), AfterValidator(recortado_sin_control)]
        | None
    ) = None
    activa: bool | None = None


class CuerpoOrdenCategorias(CuerpoDeAlta):
    orden: list[_UUIDDeCuerpo]


class CuerpoVersion(ConfiguracionEdificio, CuerpoDeAlta):
    vigente_desde: Annotated[date, Field(strict=False)]


@router.get("/complejos")
def mis_edificios(
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, str | None]]:
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
        provincia_id=cuerpo.provincia_id,
        departamento_id=cuerpo.departamento_id,
        localidad_id=cuerpo.localidad_id,
        calle_y_numero=cuerpo.calle_y_numero,
        pisos=cuerpo.pisos,
        subsuelos=cuerpo.subsuelos,
        georef=request.app.state.georef,
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
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return leer_resumen_edificio(sesion, complejo_id, hoy_en_mendoza(lambda: datetime.now(UTC)))


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


@router.patch("/complejos/{complejo_id}")
def modificar_edificio(
    complejo_id: UUID,
    cuerpo: CuerpoEdicionEdificio,
    request: Request,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.CONFIGURAR_PADRON)
    editar_edificio(
        sesion,
        identidad,
        complejo_id=complejo_id,
        cambios=cuerpo.model_dump(exclude_unset=True),
        georef=request.app.state.georef,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"id": str(complejo_id)}


@router.get("/complejos/{complejo_id}")
def ver_complejo(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
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
        "provincia_id": complejo.provincia_id,
        "departamento_id": complejo.departamento_id,
        "localidad_id": complejo.localidad_id,
        "calle_y_numero": complejo.calle_y_numero,
        "pisos": complejo.pisos,
        "subsuelos": complejo.subsuelos,
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
        sesion,
        identidad,
        complejo_id=complejo_id,
        datos=cuerpo.model_dump(),
        request_id=UUID(request_id_actual.get() or ""),
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
        sesion,
        identidad,
        unidad_id=unidad_id,
        cambios=cuerpo.model_dump(exclude_unset=True),
        request_id=UUID(request_id_actual.get() or ""),
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
    solo_activos: bool = False,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return grupos.listar_grupos(sesion, complejo_id, solo_activos=solo_activos)


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
        request_id=UUID(request_id_actual.get() or ""),
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
    grupos.editar_grupo(
        sesion,
        identidad,
        grupo_id=grupo_id,
        cambios=cuerpo.model_dump(exclude_unset=True),
        request_id=UUID(request_id_actual.get() or ""),
    )
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
        identidad,
        grupo_id=grupo_id,
        modo=cuerpo.modo_de_coeficientes,
        miembros=[m.model_dump() for m in cuerpo.unidades],
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"id": str(grupo_id)}


@router.get("/complejos/{complejo_id}/categorias")
def categorias_del_edificio(
    complejo_id: UUID,
    solo_activas: bool = False,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return categorias.listar_categorias(sesion, complejo_id, solo_activas=solo_activas)


@router.post("/complejos/{complejo_id}/categorias", status_code=201)
def alta_categoria(
    complejo_id: UUID,
    cuerpo: CuerpoCategoria,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.CONFIGURAR_PADRON)
    id_ = categorias.crear_categoria(
        sesion, identidad, complejo_id=complejo_id, datos=cuerpo.model_dump()
    )
    sesion.commit()
    return {"id": str(id_)}


@router.patch("/categorias/{categoria_id}")
def modificar_categoria(
    categoria_id: UUID,
    cuerpo: CuerpoEdicionCategoria,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    categoria = cargar_categoria(sesion, categoria_id)
    if categoria is None:
        raise _no_encontrado()
    _edificio_autorizado(sesion, identidad, categoria["complejo_id"], Accion.CONFIGURAR_PADRON)
    categorias.editar_categoria(
        sesion,
        identidad,
        categoria_id=categoria_id,
        cambios=cuerpo.model_dump(exclude_unset=True),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"id": str(categoria_id)}


@router.put("/complejos/{complejo_id}/categorias/orden")
def ordenar_categorias(
    complejo_id: UUID,
    cuerpo: CuerpoOrdenCategorias,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.CONFIGURAR_PADRON)
    categorias.reordenar_categorias(
        sesion,
        identidad,
        complejo_id=complejo_id,
        orden=cuerpo.orden,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"id": str(complejo_id)}


@router.get("/complejos/{complejo_id}/configuracion")
def vigente_del_edificio(
    complejo_id: UUID,
    fecha: date | None = None,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any] | None:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return configuracion_vigente(
        sesion, complejo_id, fecha or hoy_en_mendoza(lambda: datetime.now(UTC))
    )


@router.get("/complejos/{complejo_id}/configuracion/versiones")
def versiones_del_edificio(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_CONFIGURACION_DEL_EDIFICIO)
    return listar_versiones(sesion, complejo_id)


@router.post("/complejos/{complejo_id}/configuracion/versiones", status_code=201)
def alta_version(
    complejo_id: UUID,
    cuerpo: CuerpoVersion,
    request: Request,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.CREAR_VERSION_DE_CONFIGURACION)
    id_ = crear_version_de_configuracion(
        sesion,
        identidad,
        complejo_id=complejo_id,
        configuracion=ConfiguracionEdificio.model_validate(
            cuerpo.model_dump(exclude={"vigente_desde"})
        ),
        vigente_desde=cuerpo.vigente_desde,
        parametros=request.app.state.parametros,
        reloj=lambda: datetime.now(UTC),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"id": str(id_)}


class CuerpoAsignacion(CuerpoDeAlta):
    persona_id: _UUIDDeCuerpo
    # D7: sólo perfiles por edificio; los campos extra se rechazan en el borde.
    rol: Literal["administrador", "contador", "auxiliar", "consejo"]
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
        request_id=request_id,
    )
    sesion.commit()
    return {"id": str(nueva_id)}
