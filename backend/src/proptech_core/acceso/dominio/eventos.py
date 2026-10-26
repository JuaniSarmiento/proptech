"""D13: lo que ocurrió, separado de la matriz de permisos de D-106."""

from enum import StrEnum


class EventoDeAcceso(StrEnum):
    INGRESO_EXITOSO = "ingreso_exitoso"
    INGRESO_FALLIDO = "ingreso_fallido"
    ALTA_INICIAL = "alta_inicial"
    INVITAR_PERSONAL = "invitar_personal"
    DAR_DE_ALTA_VECINO = "dar_de_alta_vecino"
    ACEPTAR_INVITACION = "aceptar_invitacion"
    REVOCAR_INVITACION = "revocar_invitacion"
    QUITAR_ASIGNACION = "quitar_asignacion"


class EventoDelPadron(StrEnum):
    CREAR_UNIDAD = "crear_unidad"
    EDITAR_UNIDAD = "editar_unidad"
    CREAR_GRUPO = "crear_grupo"
    EDITAR_GRUPO = "editar_grupo"
    FIJAR_UNIDADES = "fijar_unidades"
    EDITAR_CATEGORIA = "editar_categoria"
    REORDENAR_CATEGORIAS = "reordenar_categorias"
