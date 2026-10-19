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

# D-096 y D5 del 3a, escritos a mano: titular, editar, ver, consejo, vecino.
_MATRIZ_A_MANO: dict[str, tuple[bool, bool, bool, bool, bool]] = {
    "cargar_gastos_y_preparar_liquidacion": (True, True, False, False, False),
    "emitir_y_distribuir_liquidacion": (True, False, False, False, False),
    "anular_liquidacion": (True, False, False, False, False),
    "confirmar_pago_informado": (True, True, False, False, False),
    "revertir_o_reimputar_pago": (True, False, False, False, False),
    "condonar_intereses": (True, False, False, False, False),
    "dar_de_baja_deuda": (True, False, False, False, False),
    "aceptar_alertas_no_bloqueantes": (True, True, False, False, False),
    "aceptar_alertas_bloqueantes": (True, False, False, False, False),
    "invitar_usuarios_y_asignar_edificios": (True, False, False, False, False),
    "informar_pago": (False, False, False, False, True),
    "crear_edificio": (True, False, False, False, False),
    "crear_version_de_configuracion": (True, False, False, False, False),
    "confirmar_sin_saldos_previos": (True, False, False, False, False),
    "configurar_padron": (True, True, False, False, False),
    "ver_configuracion_del_edificio": (True, True, True, True, False),
}
_PERFILES = [
    Asignacion(Rol.TITULAR, None),
    Asignacion(Rol.COLABORADOR, COMPLEJO, nivel=Nivel.EDITAR),
    Asignacion(Rol.COLABORADOR, COMPLEJO, nivel=Nivel.VER),
    Asignacion(Rol.CONSEJO, COMPLEJO),
    Asignacion(Rol.VECINO, COMPLEJO, unidad_id=UNIDAD),
]


def _asignacion_de(rol: Rol) -> Asignacion:
    return next(a for a in _PERFILES if a.rol is rol)


@pytest.mark.parametrize("nombre", _MATRIZ_A_MANO)
@pytest.mark.parametrize("perfil", range(5), ids=["titular", "editar", "ver", "consejo", "vecino"])
def test_cada_celda_de_la_matriz(nombre: str, perfil: int) -> None:
    assert puede([_PERFILES[perfil]], Accion(nombre), COMPLEJO) is _MATRIZ_A_MANO[nombre][perfil]


@pytest.mark.parametrize("nombre", _MATRIZ_A_MANO)
@pytest.mark.parametrize("perfil", range(5), ids=["titular", "editar", "ver", "consejo", "vecino"])
def test_sin_complejo_solo_crear_edificio_para_titular(nombre: str, perfil: int) -> None:
    esperado = nombre == "crear_edificio" and perfil == 0
    assert puede([_PERFILES[perfil]], Accion(nombre), None) is esperado


def test_la_matriz_de_prueba_cubre_exactamente_el_vocabulario() -> None:
    assert {a.value for a in Accion} == set(_MATRIZ_A_MANO)


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
