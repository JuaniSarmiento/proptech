"""La matriz de D-096 y el alcance por edificio (D7, D-096, cambio 2a).

`puede` y `alcanza` son funciones puras: las asignaciones siempre salen de
la base (filtradas por RLS), nunca del pedido. `puede` decide el permiso
por acción (403); `alcanza` decide el alcance por edificio (404). El orden
de chequeo en cada endpoint es siempre: cargar el recurso → si no existe o
no alcanza, 404 → si no puede, 403 (D7).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Rol(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMINISTRADOR = "administrador"
    CONTADOR = "contador"
    AUXILIAR = "auxiliar"
    CONSEJO = "consejo"
    VECINO = "vecino"


class Perfil(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMINISTRADOR = "administrador"
    CONTADOR = "contador"
    AUXILIAR = "auxiliar"
    CONSEJO = "consejo"
    VECINO_PROPIETARIO = "vecino_propietario"
    VECINO_INQUILINO = "vecino_inquilino"


class Alcance(StrEnum):
    PRINCIPAL = "principal"
    EDIFICIO = "edificio"
    UNIDAD = "unidad"


class Accion(StrEnum):
    """D-096: el vocabulario de permisos. También es, sin cambiar de nombre,
    el vocabulario de la auditoría (D9, tarea 6.x): un mismo `Accion.X` es a
    la vez el permiso que `puede` consulta y la acción que queda registrada.
    """

    CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION = "cargar_gastos_y_preparar_liquidacion"
    EMITIR_Y_DISTRIBUIR_LIQUIDACION = "emitir_y_distribuir_liquidacion"
    ANULAR_LIQUIDACION = "anular_liquidacion"
    CONFIRMAR_PAGO_INFORMADO = "confirmar_pago_informado"
    REVERTIR_O_REIMPUTAR_PAGO = "revertir_o_reimputar_pago"
    CONDONAR_INTERESES = "condonar_intereses"
    DAR_DE_BAJA_DEUDA = "dar_de_baja_deuda"
    ACEPTAR_ALERTAS_NO_BLOQUEANTES = "aceptar_alertas_no_bloqueantes"
    ACEPTAR_ALERTAS_BLOQUEANTES = "aceptar_alertas_bloqueantes"
    INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS = "invitar_usuarios_y_asignar_edificios"
    #: "Ver su cuenta e informar pagos" de D-096: la única fila de la matriz
    #: que es del vecino, no del titular/colaborador/consejo.
    INFORMAR_PAGO = "informar_pago"
    CREAR_EDIFICIO = "crear_edificio"
    CREAR_VERSION_DE_CONFIGURACION = "crear_version_de_configuracion"
    CONFIRMAR_SIN_SALDOS_PREVIOS = "confirmar_sin_saldos_previos"
    CONFIGURAR_PADRON = "configurar_padron"
    VER_CONFIGURACION_DEL_EDIFICIO = "ver_configuracion_del_edificio"


@dataclass(frozen=True)
class Asignacion:
    """Una fila de `asignacion_rol`, tal como la devuelve la base (ya
    filtrada por RLS): nunca se construye a partir de un dato del pedido."""

    rol: Rol
    complejo_id: UUID | None
    unidad_id: UUID | None = None
    vinculo: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rol", Rol(self.rol))
        if self.rol is Rol.VECINO:
            valido = (
                self.complejo_id is not None
                and self.unidad_id is not None
                and self.vinculo in ("propietario", "inquilino")
            )
        else:
            valido = self.unidad_id is None and self.vinculo is None
            if self.rol is Rol.SUPER_ADMIN:
                valido = valido and self.complejo_id is None
            elif self.rol in (Rol.AUXILIAR, Rol.CONSEJO):
                valido = valido and self.complejo_id is not None
        if not valido:
            raise ValueError("forma de asignación inválida para el rol")

    @property
    def perfil(self) -> Perfil:
        if self.rol is Rol.VECINO:
            return (
                Perfil.VECINO_PROPIETARIO
                if self.vinculo == "propietario"
                else Perfil.VECINO_INQUILINO
            )
        return Perfil(self.rol.value)

    @property
    def alcance(self) -> Alcance:
        if self.complejo_id is None:
            return Alcance.PRINCIPAL
        return Alcance.UNIDAD if self.unidad_id is not None else Alcance.EDIFICIO


# D3: cada celda es (perfil, alcance). Una acción ausente se niega.
_SA = (Perfil.SUPER_ADMIN, Alcance.PRINCIPAL)
_AP = (Perfil.ADMINISTRADOR, Alcance.PRINCIPAL)
_AE = (Perfil.ADMINISTRADOR, Alcance.EDIFICIO)
_CP = (Perfil.CONTADOR, Alcance.PRINCIPAL)
_CE = (Perfil.CONTADOR, Alcance.EDIFICIO)
_AX = (Perfil.AUXILIAR, Alcance.EDIFICIO)
_CO = (Perfil.CONSEJO, Alcance.EDIFICIO)
_VP = (Perfil.VECINO_PROPIETARIO, Alcance.UNIDAD)
_VI = (Perfil.VECINO_INQUILINO, Alcance.UNIDAD)
_MATRIZ: dict[Accion, frozenset[tuple[Perfil, Alcance]]] = {
    Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION: frozenset({_SA, _AP, _AE}),
    Accion.EMITIR_Y_DISTRIBUIR_LIQUIDACION: frozenset({_SA, _AP, _AE}),
    Accion.ANULAR_LIQUIDACION: frozenset({_SA, _AP}),
    Accion.CONFIRMAR_PAGO_INFORMADO: frozenset({_SA, _AP, _AE}),
    Accion.REVERTIR_O_REIMPUTAR_PAGO: frozenset({_SA, _AP}),
    Accion.CONDONAR_INTERESES: frozenset({_SA, _AP}),
    Accion.DAR_DE_BAJA_DEUDA: frozenset({_SA, _AP}),
    Accion.ACEPTAR_ALERTAS_NO_BLOQUEANTES: frozenset({_SA, _AP, _AE}),
    Accion.ACEPTAR_ALERTAS_BLOQUEANTES: frozenset({_SA, _AP}),
    Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS: frozenset({_SA}),
    Accion.INFORMAR_PAGO: frozenset({_VP, _VI}),
    Accion.CREAR_EDIFICIO: frozenset({_SA}),
    Accion.CREAR_VERSION_DE_CONFIGURACION: frozenset({_SA, _AP, _AE}),
    Accion.CONFIRMAR_SIN_SALDOS_PREVIOS: frozenset({_SA, _AP}),
    Accion.CONFIGURAR_PADRON: frozenset({_SA, _AP, _AE}),
    Accion.VER_CONFIGURACION_DEL_EDIFICIO: frozenset({_SA, _AP, _AE, _CP, _CE, _AX, _CO}),
}


def puede(asignaciones: Sequence[Asignacion], accion: Accion, complejo_id: UUID | None) -> bool:
    """D-096. El titular no tiene una asignación por complejo (D6: su fila
    tiene `complejo_id = NULL`, cubre toda la administración); las demás
    sólo cuentan si su `complejo_id` coincide con el que se está pidiendo.
    Sin complejo sólo se evalúa crear un edificio (D5 del 3a)."""
    if complejo_id is None and accion is not Accion.CREAR_EDIFICIO:
        return False
    permitidos = _MATRIZ.get(accion, frozenset())
    for asignacion in asignaciones:
        if asignacion.alcance is not Alcance.PRINCIPAL and asignacion.complejo_id != complejo_id:
            continue
        clave = (asignacion.perfil, asignacion.alcance)
        if clave in permitidos:
            return True
    return False


def alcanza(
    asignaciones: Sequence[Asignacion], complejo_id: UUID, unidad_id: UUID | None = None
) -> bool:
    """D-096: titular, todo; colaborador, sólo los complejos asignados;
    consejo, el suyo; vecino, sus unidades y su complejo (el complejo de una
    unidad propia, aunque no se pida ninguna unidad en particular)."""
    for asignacion in asignaciones:
        if asignacion.rol is Rol.SUPER_ADMIN:
            return True
        if asignacion.rol in (Rol.ADMINISTRADOR, Rol.AUXILIAR, Rol.CONSEJO):
            if asignacion.complejo_id == complejo_id:
                return True
        elif asignacion.rol is Rol.VECINO and asignacion.complejo_id == complejo_id:
            if unidad_id is None or asignacion.unidad_id == unidad_id:
                return True
    return False
