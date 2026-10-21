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
from proptech_core.acceso.dominio.permisos import (
    Accion,
    Alcance,
    Asignacion,
    Perfil,
    Rol,
    alcanza,
    puede,
)

COMPLEJO = uuid.uuid4()
OTRO_COMPLEJO = uuid.uuid4()
UNIDAD = uuid.uuid4()
OTRA_UNIDAD = uuid.uuid4()

# D3 copiada A MANO: SA, AP, AE, CP, CE, AX, CO, VP, VI.
_MATRIZ_A_MANO: dict[str, tuple[bool, ...]] = {
    "cargar_gastos_y_preparar_liquidacion": (
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
    ),
    "emitir_y_distribuir_liquidacion": (True, True, True, False, False, False, False, False, False),
    "anular_liquidacion": (True, True, False, False, False, False, False, False, False),
    "confirmar_pago_informado": (True, True, True, False, False, False, False, False, False),
    "revertir_o_reimputar_pago": (True, True, False, False, False, False, False, False, False),
    "condonar_intereses": (True, True, False, False, False, False, False, False, False),
    "dar_de_baja_deuda": (True, True, False, False, False, False, False, False, False),
    "aceptar_alertas_no_bloqueantes": (True, True, True, False, False, False, False, False, False),
    "aceptar_alertas_bloqueantes": (True, True, False, False, False, False, False, False, False),
    "invitar_usuarios_y_asignar_edificios": (
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    ),
    "informar_pago": (False, False, False, False, False, False, False, True, True),
    "crear_edificio": (True, False, False, False, False, False, False, False, False),
    "crear_version_de_configuracion": (True, True, True, False, False, False, False, False, False),
    "confirmar_sin_saldos_previos": (True, True, False, False, False, False, False, False, False),
    "configurar_padron": (True, True, True, False, False, False, False, False, False),
    "ver_configuracion_del_edificio": (True, True, True, True, True, True, True, False, False),
}
_PERFILES = [
    Asignacion(Rol.SUPER_ADMIN, None),
    Asignacion(Rol.ADMINISTRADOR, None),
    Asignacion(Rol.ADMINISTRADOR, COMPLEJO),
    Asignacion(Rol.CONTADOR, None),
    Asignacion(Rol.CONTADOR, COMPLEJO),
    Asignacion(Rol.AUXILIAR, COMPLEJO),
    Asignacion(Rol.CONSEJO, COMPLEJO),
    Asignacion(Rol.VECINO, COMPLEJO, UNIDAD, "propietario"),
    Asignacion(Rol.VECINO, COMPLEJO, UNIDAD, "inquilino"),
]
_COLUMNAS = ["SA", "AP", "AE", "CP", "CE", "AX", "CO", "VP", "VI"]


def test_matriz_entera_con_cada_celda_distinta_en_el_mensaje() -> None:
    diferencias = []
    for nombre, fila in _MATRIZ_A_MANO.items():
        for columna, asignacion, esperado in zip(_COLUMNAS, _PERFILES, fila, strict=True):
            obtenido = puede([asignacion], Accion(nombre), COMPLEJO)
            if obtenido != esperado:
                diferencias.append(f"{nombre}/{columna}: {obtenido} != {esperado}")
    assert not diferencias, "\n".join(diferencias)


@pytest.mark.parametrize("asignacion", [a for a in _PERFILES if a.complejo_id is not None])
@pytest.mark.parametrize("accion", list(Accion))
def test_fuera_del_complejo_nadie_puede(asignacion: Asignacion, accion: Accion) -> None:
    assert puede([asignacion], accion, OTRO_COMPLEJO) is False


def test_dos_asignaciones_no_prestan_el_permiso_al_otro_edificio() -> None:
    asignaciones = [
        Asignacion(Rol.ADMINISTRADOR, COMPLEJO),
        Asignacion(Rol.AUXILIAR, OTRO_COMPLEJO),
    ]
    assert puede(asignaciones, Accion.CONFIGURAR_PADRON, COMPLEJO) is True
    assert puede(asignaciones, Accion.CONFIGURAR_PADRON, OTRO_COMPLEJO) is False


def test_ra3_principal_no_evalua_anular_sin_complejo() -> None:
    assert puede([Asignacion(Rol.ADMINISTRADOR, None)], Accion.ANULAR_LIQUIDACION, None) is False


def _asignacion_de(rol: Rol) -> Asignacion:
    return next(a for a in _PERFILES if a.rol is rol)


@pytest.mark.parametrize("nombre", _MATRIZ_A_MANO)
@pytest.mark.parametrize("perfil", range(9), ids=_COLUMNAS)
def test_cada_celda_de_la_matriz(nombre: str, perfil: int) -> None:
    assert puede([_PERFILES[perfil]], Accion(nombre), COMPLEJO) is _MATRIZ_A_MANO[nombre][perfil]


@pytest.mark.parametrize("nombre", _MATRIZ_A_MANO)
@pytest.mark.parametrize("perfil", range(9), ids=_COLUMNAS)
def test_sin_complejo_crear_e_invitar_para_super_admin(nombre: str, perfil: int) -> None:
    esperado = nombre in {"crear_edificio", "invitar_usuarios_y_asignar_edificios"} and perfil == 0
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

    for rol in (Rol.SUPER_ADMIN, Rol.ADMINISTRADOR, Rol.AUXILIAR, Rol.CONSEJO, Rol.VECINO):
        asignacion = _asignacion_de(rol)
        assert puede([asignacion], accion_quitada, COMPLEJO) is False, rol.value


# --- alcanza: super_admin todo; administrador/consejo su complejo; vecino su unidad ---


def test_alcanza_super_admin_cualquier_complejo_y_unidad() -> None:
    asignacion = Asignacion(rol=Rol.SUPER_ADMIN, complejo_id=None)
    assert alcanza([asignacion], COMPLEJO) is True
    assert alcanza([asignacion], OTRO_COMPLEJO) is True
    assert alcanza([asignacion], COMPLEJO, UNIDAD) is True
    assert alcanza([asignacion], OTRO_COMPLEJO, OTRA_UNIDAD) is True


def test_alcanza_administrador_solo_el_complejo_asignado() -> None:
    asignacion = Asignacion(rol=Rol.ADMINISTRADOR, complejo_id=COMPLEJO)
    assert alcanza([asignacion], COMPLEJO) is True
    assert alcanza([asignacion], OTRO_COMPLEJO) is False


def test_alcanza_consejo_solo_su_complejo() -> None:
    asignacion = Asignacion(rol=Rol.CONSEJO, complejo_id=COMPLEJO)
    assert alcanza([asignacion], COMPLEJO) is True
    assert alcanza([asignacion], OTRO_COMPLEJO) is False


def test_alcanza_vecino_su_complejo_y_su_unidad_no_otra() -> None:
    asignacion = Asignacion(
        rol=Rol.VECINO, complejo_id=COMPLEJO, unidad_id=UNIDAD, vinculo="propietario"
    )
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


# D1/D2: literal independiente de la implementación.
@pytest.mark.parametrize(
    "rol,complejo,unidad,vinculo,perfil,alcance",
    [
        ("super_admin", None, None, None, Perfil.SUPER_ADMIN, Alcance.PRINCIPAL),
        ("administrador", None, None, None, Perfil.ADMINISTRADOR, Alcance.PRINCIPAL),
        ("administrador", COMPLEJO, None, None, Perfil.ADMINISTRADOR, Alcance.EDIFICIO),
        ("contador", None, None, None, Perfil.CONTADOR, Alcance.PRINCIPAL),
        ("contador", COMPLEJO, None, None, Perfil.CONTADOR, Alcance.EDIFICIO),
        ("auxiliar", COMPLEJO, None, None, Perfil.AUXILIAR, Alcance.EDIFICIO),
        ("consejo", COMPLEJO, None, None, Perfil.CONSEJO, Alcance.EDIFICIO),
        ("vecino", COMPLEJO, UNIDAD, "propietario", Perfil.VECINO_PROPIETARIO, Alcance.UNIDAD),
        ("vecino", COMPLEJO, UNIDAD, "inquilino", Perfil.VECINO_INQUILINO, Alcance.UNIDAD),
    ],
)
def test_perfil_y_alcance_de_cada_forma(
    rol: str,
    complejo: uuid.UUID | None,
    unidad: uuid.UUID | None,
    vinculo: str | None,
    perfil: Perfil,
    alcance: Alcance,
) -> None:
    asignacion = Asignacion(Rol(rol), complejo, unidad, vinculo)
    assert asignacion.perfil is perfil
    assert asignacion.alcance is alcance


@pytest.mark.parametrize(
    "rol,complejo,unidad,vinculo",
    [
        ("super_admin", COMPLEJO, None, None),
        ("super_admin", None, UNIDAD, None),
        ("super_admin", None, None, "propietario"),
        ("administrador", COMPLEJO, UNIDAD, None),
        ("administrador", None, UNIDAD, None),
        ("administrador", COMPLEJO, None, "propietario"),
        ("contador", COMPLEJO, UNIDAD, None),
        ("contador", None, None, "inquilino"),
        ("auxiliar", None, None, None),
        ("auxiliar", COMPLEJO, UNIDAD, None),
        ("auxiliar", COMPLEJO, None, "propietario"),
        ("consejo", None, None, None),
        ("consejo", COMPLEJO, UNIDAD, None),
        ("consejo", COMPLEJO, None, "inquilino"),
        ("vecino", None, UNIDAD, "propietario"),
        ("vecino", COMPLEJO, None, "propietario"),
        ("vecino", COMPLEJO, UNIDAD, None),
        ("vecino", COMPLEJO, UNIDAD, "inventado"),
        ("titular", None, None, None),
        ("colaborador", COMPLEJO, None, None),
        ("inventado", COMPLEJO, None, None),
    ],
)
def test_rechaza_formas_invalidas_al_construir(
    rol: str,
    complejo: uuid.UUID | None,
    unidad: uuid.UUID | None,
    vinculo: str | None,
) -> None:
    with pytest.raises(ValueError):
        Asignacion(rol, complejo, unidad, vinculo)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "indice,esperados",
    [
        (0, (True, True, True, True)),
        (1, (True, True, True, True)),
        (2, (True, True, True, False)),
        (3, (True, True, True, True)),
        (4, (True, True, True, False)),
        (5, (True, True, True, False)),
        (6, (True, True, True, False)),
        (7, (True, True, False, False)),
        (8, (True, True, False, False)),
    ],
    ids=_COLUMNAS,
)
def test_alcance_de_los_nueve_perfiles(indice: int, esperados: tuple[bool, ...]) -> None:
    asignaciones = [_PERFILES[indice]]
    obtenido = (
        alcanza(asignaciones, COMPLEJO),
        alcanza(asignaciones, COMPLEJO, UNIDAD),
        alcanza(asignaciones, COMPLEJO, OTRA_UNIDAD),
        alcanza(asignaciones, OTRO_COMPLEJO, UNIDAD),
    )
    assert obtenido == esperados


def test_alcance_de_dos_propietarios_e_inquilino_de_otra_unidad() -> None:
    propietaria = [Asignacion(Rol.VECINO, COMPLEJO, UNIDAD, "propietario")]
    propietario = [Asignacion(Rol.VECINO, COMPLEJO, UNIDAD, "propietario")]
    inquilino = [Asignacion(Rol.VECINO, COMPLEJO, OTRA_UNIDAD, "inquilino")]
    for persona in (propietaria, propietario):
        assert alcanza(persona, COMPLEJO, UNIDAD) is True
        assert alcanza(persona, COMPLEJO, OTRA_UNIDAD) is False
    assert alcanza(inquilino, COMPLEJO, OTRA_UNIDAD) is True
    assert alcanza(inquilino, COMPLEJO, UNIDAD) is False
    assert alcanza(propietaria + inquilino, COMPLEJO, UNIDAD) is True
    assert alcanza(propietaria + inquilino, COMPLEJO, OTRA_UNIDAD) is True
    assert alcanza(propietaria + inquilino, OTRO_COMPLEJO) is False
