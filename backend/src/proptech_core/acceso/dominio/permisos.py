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
    TITULAR = "titular"
    COLABORADOR = "colaborador"
    CONSEJO = "consejo"
    VECINO = "vecino"


class Nivel(StrEnum):
    VER = "ver"
    EDITAR = "editar"


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
    nivel: Nivel | None = None


#: La matriz de D-096, escrita a mano (no generada desde el código): para
#: cada acción, el conjunto de (rol, nivel) que puede hacerla. El nivel es
#: `None` salvo para `COLABORADOR` (D-037): el nivel "ver" sólo permite
#: leer la configuración del edificio (D5 del 3a). Una
#: `Accion` sin entrada aquí se niega para todos (`.get(..., frozenset())`
#: en `puede`, nunca `[accion]`).
_MATRIZ: dict[Accion, frozenset[tuple[Rol, Nivel | None]]] = {
    Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION: frozenset(
        {(Rol.TITULAR, None), (Rol.COLABORADOR, Nivel.EDITAR)}
    ),
    Accion.EMITIR_Y_DISTRIBUIR_LIQUIDACION: frozenset({(Rol.TITULAR, None)}),
    Accion.ANULAR_LIQUIDACION: frozenset({(Rol.TITULAR, None)}),
    Accion.CONFIRMAR_PAGO_INFORMADO: frozenset(
        {(Rol.TITULAR, None), (Rol.COLABORADOR, Nivel.EDITAR)}
    ),
    Accion.REVERTIR_O_REIMPUTAR_PAGO: frozenset({(Rol.TITULAR, None)}),
    Accion.CONDONAR_INTERESES: frozenset({(Rol.TITULAR, None)}),
    Accion.DAR_DE_BAJA_DEUDA: frozenset({(Rol.TITULAR, None)}),
    Accion.ACEPTAR_ALERTAS_NO_BLOQUEANTES: frozenset(
        {(Rol.TITULAR, None), (Rol.COLABORADOR, Nivel.EDITAR)}
    ),
    Accion.ACEPTAR_ALERTAS_BLOQUEANTES: frozenset({(Rol.TITULAR, None)}),
    Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS: frozenset({(Rol.TITULAR, None)}),
    Accion.INFORMAR_PAGO: frozenset({(Rol.VECINO, None)}),
    Accion.CREAR_EDIFICIO: frozenset({(Rol.TITULAR, None)}),
    Accion.CREAR_VERSION_DE_CONFIGURACION: frozenset({(Rol.TITULAR, None)}),
    Accion.CONFIRMAR_SIN_SALDOS_PREVIOS: frozenset({(Rol.TITULAR, None)}),
    Accion.CONFIGURAR_PADRON: frozenset({(Rol.TITULAR, None), (Rol.COLABORADOR, Nivel.EDITAR)}),
    Accion.VER_CONFIGURACION_DEL_EDIFICIO: frozenset(
        {
            (Rol.TITULAR, None),
            (Rol.COLABORADOR, Nivel.EDITAR),
            (Rol.COLABORADOR, Nivel.VER),
            (Rol.CONSEJO, None),
        }
    ),
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
        clave: tuple[Rol, Nivel | None]
        if asignacion.rol is Rol.TITULAR:
            clave = (asignacion.rol, None)
        elif asignacion.complejo_id == complejo_id:
            clave = (asignacion.rol, asignacion.nivel)
        else:
            continue
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
        if asignacion.rol is Rol.TITULAR:
            return True
        if asignacion.rol in (Rol.COLABORADOR, Rol.CONSEJO):
            if asignacion.complejo_id == complejo_id:
                return True
        elif asignacion.rol is Rol.VECINO and asignacion.complejo_id == complejo_id:
            if unidad_id is None or asignacion.unidad_id == unidad_id:
                return True
    return False
