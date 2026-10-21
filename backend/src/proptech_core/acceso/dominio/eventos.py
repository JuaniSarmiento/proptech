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
