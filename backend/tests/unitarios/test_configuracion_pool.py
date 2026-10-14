"""Tests de los parámetros del pool del engine en `Configuracion` (D18, L-002).
Cambio 1c, tarea 3.6 (parte 1 de 3).

Opcionales con default: faltante usa el default; vacía, en blanco, con tipo
equivocado y fuera de rango terminan nombrando la variable.
"""

import pytest

VARIABLES_DEFAULT = {
    "DB_POOL_PRE_PING": True,
    "DB_POOL_SIZE": 5,
    "DB_POOL_RECYCLE_S": 1800,
    "DB_POOL_TIMEOUT_S": 5,
    "DB_CONNECT_TIMEOUT_S": 2,
}

CAMPOS_DE = {
    "DB_POOL_PRE_PING": "db_pool_pre_ping",
    "DB_POOL_SIZE": "db_pool_size",
    "DB_POOL_RECYCLE_S": "db_pool_recycle_s",
    "DB_POOL_TIMEOUT_S": "db_pool_timeout_s",
    "DB_CONNECT_TIMEOUT_S": "db_connect_timeout_s",
}


def test_sin_ninguna_variable_usa_los_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_core.compartido.configuracion import Configuracion

    for variable in VARIABLES_DEFAULT:
        monkeypatch.delenv(variable, raising=False)

    configuracion = Configuracion()

    for variable, esperado in VARIABLES_DEFAULT.items():
        campo = CAMPOS_DE[variable]
        assert getattr(configuracion, campo) == esperado, campo


@pytest.mark.parametrize("variable", list(VARIABLES_DEFAULT))
def test_variable_vacia_se_nombra(monkeypatch: pytest.MonkeyPatch, variable: str) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv(variable, "")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert variable in str(exc_info.value)


@pytest.mark.parametrize("variable", list(VARIABLES_DEFAULT))
def test_variable_en_blanco_se_nombra(monkeypatch: pytest.MonkeyPatch, variable: str) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv(variable, "   ")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert variable in str(exc_info.value)


@pytest.mark.parametrize("variable", list(VARIABLES_DEFAULT))
def test_variable_con_tipo_equivocado_se_nombra(
    monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv(variable, "no-es-ni-numero-ni-booleano")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert variable in str(exc_info.value)


@pytest.mark.parametrize(
    ("variable", "valor_fuera_de_rango"),
    [
        ("DB_POOL_SIZE", "0"),
        ("DB_POOL_SIZE", "51"),
        ("DB_POOL_RECYCLE_S", "59"),
        ("DB_POOL_RECYCLE_S", "86401"),
        ("DB_POOL_TIMEOUT_S", "0"),
        ("DB_POOL_TIMEOUT_S", "61"),
        ("DB_CONNECT_TIMEOUT_S", "0"),
        ("DB_CONNECT_TIMEOUT_S", "31"),
    ],
)
def test_variable_fuera_de_rango_se_nombra(
    monkeypatch: pytest.MonkeyPatch, variable: str, valor_fuera_de_rango: str
) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv(variable, valor_fuera_de_rango)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert variable in str(exc_info.value)


def test_db_pool_pre_ping_acepta_false(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_core.compartido.configuracion import Configuracion

    monkeypatch.setenv("DB_POOL_PRE_PING", "false")

    configuracion = Configuracion()

    assert configuracion.db_pool_pre_ping is False


#: Ataque del rompedor (vuelta 2, F10; L-008): formas que pydantic en modo
#: laxo convierte a entero SIN avisar (y, en el caso de `5_0`, a un valor
#: totalmente distinto del que parece) en vez de rechazar.
_VARIABLES_ENTERAS = [
    "DB_POOL_SIZE",
    "DB_POOL_RECYCLE_S",
    "DB_POOL_TIMEOUT_S",
    "DB_CONNECT_TIMEOUT_S",
]


@pytest.mark.parametrize("variable", _VARIABLES_ENTERAS)
@pytest.mark.parametrize(
    "valor_laxo",
    ["5\n", " 5", "\t5", "5.0", "5_0"],
    ids=["salto_de_linea", "espacio", "tabulacion", "punto_flotante", "guion_bajo"],
)
def test_variable_entera_laxa_se_rechaza(
    monkeypatch: pytest.MonkeyPatch, variable: str, valor_laxo: str
) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv(variable, valor_laxo)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert variable in str(exc_info.value)
