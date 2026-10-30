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
    EDITAR_EDIFICIO = "editar_edificio"


class EventoDelGasto(StrEnum):
    """D9 ampliado por `gastos-y-cargos`: proveedores, gastos, notas de
    crédito y cargos particulares. El detalle MUST NOT llevar ningún
    importe ni el CUIT de un proveedor (auditoria-de-acciones, "Ningún
    importe en el detalle de un evento del gasto")."""

    CREAR_PROVEEDOR = "crear_proveedor"
    EDITAR_PROVEEDOR = "editar_proveedor"
    CREAR_GASTO = "crear_gasto"
    EDITAR_GASTO = "editar_gasto"
    APROBAR_GASTO = "aprobar_gasto"
    CARGAR_NOTA_DE_CREDITO = "cargar_nota_de_credito"
    CREAR_CARGO_PARTICULAR = "crear_cargo_particular"
    EDITAR_CARGO_PARTICULAR = "editar_cargo_particular"
    APROBAR_CARGO_PARTICULAR = "aprobar_cargo_particular"
    IMPORTAR_CARGOS_PARTICULARES = "importar_cargos_particulares"
