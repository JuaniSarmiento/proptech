"""La matriz de D-096 (D7, cambio 2a, tarea 5.1): `puede` y `alcanza`,
funciones puras, sin base de datos.

La tabla de casos de este archivo está copiada a mano de la matriz de
D-096 (`knowledge-base/09_decisiones_y_supuestos.md`), no generada desde
`permisos.py`: si alguien cambia la matriz del código sin querer, este
archivo tiene que notarlo.

Escenarios de `autorizacion-por-rol`: La matriz completa.
"""

import uuid

import pytest

from proptech_core.acceso.dominio import permisos
from proptech_core.acceso.dominio.permisos import Accion, Asignacion, Nivel, Rol, alcanza, puede

COMPLEJO = uuid.uuid4()
OTRO_COMPLEJO = uuid.uuid4()
UNIDAD = uuid.uuid4()
OTRA_UNIDAD = uuid.uuid4()

#: Copiada a mano de la matriz de D-096 (P23): Sí/No/Ve por acción y rol. El
#: colaborador de esta tabla es siempre el de nivel "editar" (D-037); el de
#: "ver" no tiene ninguna fila en Sí, en ninguna acción (se prueba aparte).
#: "Ve" se trata como False para `puede` (es una autorización de LECTURA,
#: un concepto que esta tarea no cubre): sólo "Sí" es True.
_MATRIZ_A_MANO: dict[Accion, dict[Rol, bool]] = {
    Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION: {
        Rol.TITULAR: True,
        Rol.COLABORADOR: True,
        Rol.CONSEJO: False,  # "Ve"
        Rol.VECINO: False,
    },
    Accion.EMITIR_Y_DISTRIBUIR_LIQUIDACION: {
        Rol.TITULAR: True,
        Rol.COLABORADOR: False,
        Rol.CONSEJO: False,
        Rol.VECINO: False,
    },
    Accion.ANULAR_LIQUIDACION: {
        Rol.TITULAR: True,
        Rol.COLABORADOR: False,
        Rol.CONSEJO: False,
        Rol.VECINO: False,
    },
    Accion.CONFIRMAR_PAGO_INFORMADO: {
        Rol.TITULAR: True,
        Rol.COLABORADOR: True,
        Rol.CONSEJO: False,
        Rol.VECINO: False,
    },
    Accion.REVERTIR_O_REIMPUTAR_PAGO: {
        Rol.TITULAR: True,
        Rol.COLABORADOR: False,
        Rol.CONSEJO: False,
        Rol.VECINO: False,
    },
    Accion.CONDONAR_INTERESES: {
        Rol.TITULAR: True,
        Rol.COLABORADOR: False,
        Rol.CONSEJO: False,  # "Ve"
        Rol.VECINO: False,
    },
    Accion.DAR_DE_BAJA_DEUDA: {
        Rol.TITULAR: True,
        Rol.COLABORADOR: False,
        Rol.CONSEJO: False,
        Rol.VECINO: False,
    },
    Accion.ACEPTAR_ALERTAS_NO_BLOQUEANTES: {
        Rol.TITULAR: True,
        Rol.COLABORADOR: True,
        Rol.CONSEJO: False,
        Rol.VECINO: False,
    },
    Accion.ACEPTAR_ALERTAS_BLOQUEANTES: {
        Rol.TITULAR: True,
        Rol.COLABORADOR: False,
        Rol.CONSEJO: False,
        Rol.VECINO: False,
    },
    Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS: {
        Rol.TITULAR: True,
        Rol.COLABORADOR: False,
        Rol.CONSEJO: False,
        Rol.VECINO: False,
    },
    Accion.INFORMAR_PAGO: {
        Rol.TITULAR: False,
        Rol.COLABORADOR: False,
        Rol.CONSEJO: False,
        Rol.VECINO: True,
    },
}


def _asignacion_de(rol: Rol) -> Asignacion:
    if rol is Rol.TITULAR:
        return Asignacion(rol=Rol.TITULAR, complejo_id=None)
    if rol is Rol.COLABORADOR:
        return Asignacion(rol=Rol.COLABORADOR, complejo_id=COMPLEJO, nivel=Nivel.EDITAR)
    if rol is Rol.CONSEJO:
        return Asignacion(rol=Rol.CONSEJO, complejo_id=COMPLEJO)
    return Asignacion(rol=Rol.VECINO, complejo_id=COMPLEJO, unidad_id=UNIDAD)


# --- Cada celda de la matriz, una por una ---


@pytest.mark.parametrize("accion", list(Accion), ids=lambda a: a.value)
@pytest.mark.parametrize("rol", list(Rol), ids=lambda r: r.value)
def test_cada_celda_de_la_matriz(accion: Accion, rol: Rol) -> None:
    esperado = _MATRIZ_A_MANO[accion][rol]
    asignacion = _asignacion_de(rol)

    resultado = puede([asignacion], accion, COMPLEJO)

    assert resultado is esperado, f"{accion.value} x {rol.value}: esperaba {esperado}"


def test_colaborador_de_nivel_ver_no_tiene_ninguna_fila_en_si() -> None:
    """D-096: "un colaborador de sólo 'ver' no hace ninguna de estas
    acciones, cierre o no cierre"."""
    asignacion = Asignacion(rol=Rol.COLABORADOR, complejo_id=COMPLEJO, nivel=Nivel.VER)
    for accion in Accion:
        assert puede([asignacion], accion, COMPLEJO) is False, accion.value


# --- Una Accion sin fila en la matriz se niega para todos ---


def test_una_accion_sin_fila_en_la_matriz_se_niega_para_todos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matriz_sin_una_fila = dict(permisos._MATRIZ)
    accion_quitada = next(iter(matriz_sin_una_fila))
    del matriz_sin_una_fila[accion_quitada]
    monkeypatch.setattr(permisos, "_MATRIZ", matriz_sin_una_fila)

    for rol in Rol:
        asignacion = _asignacion_de(rol)
        assert puede([asignacion], accion_quitada, COMPLEJO) is False, rol.value


# --- alcanza: titular todo; colaborador/consejo su complejo; vecino su unidad ---


def test_alcanza_titular_cualquier_complejo_y_unidad() -> None:
    asignacion = Asignacion(rol=Rol.TITULAR, complejo_id=None)
    assert alcanza([asignacion], COMPLEJO) is True
    assert alcanza([asignacion], OTRO_COMPLEJO) is True
    assert alcanza([asignacion], COMPLEJO, UNIDAD) is True
    assert alcanza([asignacion], OTRO_COMPLEJO, OTRA_UNIDAD) is True


def test_alcanza_colaborador_solo_el_complejo_asignado() -> None:
    asignacion = Asignacion(rol=Rol.COLABORADOR, complejo_id=COMPLEJO, nivel=Nivel.EDITAR)
    assert alcanza([asignacion], COMPLEJO) is True
    assert alcanza([asignacion], OTRO_COMPLEJO) is False


def test_alcanza_consejo_solo_su_complejo() -> None:
    asignacion = Asignacion(rol=Rol.CONSEJO, complejo_id=COMPLEJO)
    assert alcanza([asignacion], COMPLEJO) is True
    assert alcanza([asignacion], OTRO_COMPLEJO) is False


def test_alcanza_vecino_su_complejo_y_su_unidad_no_otra() -> None:
    asignacion = Asignacion(rol=Rol.VECINO, complejo_id=COMPLEJO, unidad_id=UNIDAD)
    # Su complejo, sin pedir una unidad en particular: sí.
    assert alcanza([asignacion], COMPLEJO) is True
    # Su propia unidad: sí.
    assert alcanza([asignacion], COMPLEJO, UNIDAD) is True
    # La unidad de otro vecino, mismo complejo: no.
    assert alcanza([asignacion], COMPLEJO, OTRA_UNIDAD) is False
    # Otro complejo: no.
    assert alcanza([asignacion], OTRO_COMPLEJO) is False
    assert alcanza([asignacion], OTRO_COMPLEJO, UNIDAD) is False


def test_alcanza_sin_ninguna_asignacion_es_falso() -> None:
    assert alcanza([], COMPLEJO) is False
    assert alcanza([], COMPLEJO, UNIDAD) is False
