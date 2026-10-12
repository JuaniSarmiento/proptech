"""Tests unitarios de Configuracion y de la URL de conexión a PostgreSQL."""

import traceback
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

VARIABLES_STRING = ["POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
TODAS_LAS_VARIABLES = [*VARIABLES_STRING, "POSTGRES_PORT"]

VARIABLES_STRING_AMPLIADAS = ["REDIS_HOST", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"]

BASE_OK: dict[str, str] = {
    "POSTGRES_HOST": "db",
    "POSTGRES_PORT": "5432",
    "POSTGRES_USER": "proptech",
    "POSTGRES_PASSWORD": "pass",
    "POSTGRES_DB": "proptech",
}


def _set_base(
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, str] | None = None,
    deletes: list[str] | None = None,
) -> None:
    """Variables de entorno válidas de base, para las pruebas de la ronda 3 del Rompedor
    que siguen. Se definen acá (no en el fixture autouse de `conftest.py`) porque estos
    tests pisan variables puntuales a propósito."""
    for clave, valor in BASE_OK.items():
        monkeypatch.setenv(clave, valor)
    for clave, valor in (overrides or {}).items():
        monkeypatch.setenv(clave, valor)
    for clave in deletes or []:
        monkeypatch.delenv(clave, raising=False)


def test_sin_password_falla_nombrando_la_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_core.compartido.configuracion import Configuracion

    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "proptech")
    monkeypatch.setenv("POSTGRES_DB", "proptech")

    with pytest.raises(Exception) as exc_info:
        Configuracion()

    mensaje = str(exc_info.value)
    assert "POSTGRES_PASSWORD" in mensaje


@pytest.mark.parametrize("variable", VARIABLES_STRING)
def test_cada_variable_faltante_se_nombra(monkeypatch: pytest.MonkeyPatch, variable: str) -> None:
    """Las 4 variables sin default, si faltan, aparecen nombradas en el error (D11).

    `POSTGRES_PORT` tiene default (5432) a propósito: que falte no es un error,
    así que no entra en este caso (si falta, Configuracion() arranca con 5432)."""
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.delenv(variable, raising=False)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert variable in str(exc_info.value)


@pytest.mark.parametrize("variable", TODAS_LAS_VARIABLES)
def test_cada_variable_vacia_se_nombra(monkeypatch: pytest.MonkeyPatch, variable: str) -> None:
    """Presente pero vacía (`""`) no es "falta" para pydantic: igual se nombra y se rechaza."""
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv(variable, "")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert variable in str(exc_info.value)


@pytest.mark.parametrize("variable", VARIABLES_STRING)
def test_cada_variable_string_en_blanco_se_nombra(
    monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    """Sólo espacios tampoco es un valor válido, aunque la variable esté "presente"."""
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv(variable, "   ")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert variable in str(exc_info.value)


def test_puerto_no_numerico_se_nombra(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv("POSTGRES_PORT", "abc")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert "POSTGRES_PORT" in str(exc_info.value)


@pytest.mark.parametrize("puerto", ["0", "70000"])
def test_puerto_fuera_de_rango_se_nombra(monkeypatch: pytest.MonkeyPatch, puerto: str) -> None:
    """El puerto válido de TCP es 1-65535; 0 y 70000 quedan afuera."""
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv("POSTGRES_PORT", puerto)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert "POSTGRES_PORT" in str(exc_info.value)


def test_ningun_valor_aparece_en_el_mensaje_de_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un password con pinta de secreto real no debe aparecer en el error, ni cuando
    el que falla es OTRA variable: el mensaje nombra variables, nunca valores."""
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    secreto = "s3cr3t@:/"
    monkeypatch.setenv("POSTGRES_PASSWORD", secreto)
    monkeypatch.setenv("POSTGRES_HOST", "")  # dispara el error; el password es válido

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    mensaje = str(exc_info.value)
    assert secreto not in mensaje
    assert "POSTGRES_HOST" in mensaje


def test_url_escapa_password_con_caracteres_especiales(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_core.compartido.configuracion import Configuracion

    password_especial = "p@ss:w/rd"
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "proptech")
    monkeypatch.setenv("POSTGRES_PASSWORD", password_especial)
    monkeypatch.setenv("POSTGRES_DB", "proptech")

    configuracion = Configuracion()
    url_texto = configuracion.url_sqlalchemy()

    url = make_url(url_texto)
    assert url.password == password_especial
    assert url.host == "db"
    assert url.port == 5432
    assert url.username == "proptech"
    assert url.database == "proptech"


# --- Regresión de la ronda 3 del Rompedor (ex `tests/rompedor/test_configuracion_ronda3.py`) ---


def test_multiples_variables_rotas_a_la_vez_se_nombran_todas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Varias variables inválidas al mismo tiempo: se nombran TODAS, no sólo la primera."""
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    _set_base(
        monkeypatch,
        overrides={"POSTGRES_HOST": "   ", "POSTGRES_PORT": "999999"},
        deletes=["POSTGRES_USER"],
    )

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    mensaje = str(exc_info.value)
    assert "POSTGRES_HOST" in mensaje
    assert "POSTGRES_PORT" in mensaje
    assert "POSTGRES_USER" in mensaje


def test_puerto_con_espacios_alrededor_se_acepta_recortado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from proptech_core.compartido.configuracion import Configuracion

    _set_base(monkeypatch, overrides={"POSTGRES_PORT": " 5432 "})

    configuracion = Configuracion()

    assert configuracion.postgres_port == 5432


def test_puerto_con_signo_mas_se_acepta(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_core.compartido.configuracion import Configuracion

    _set_base(monkeypatch, overrides={"POSTGRES_PORT": "+5432"})

    configuracion = Configuracion()

    assert configuracion.postgres_port == 5432


def test_puerto_con_ceros_a_la_izquierda_se_acepta(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_core.compartido.configuracion import Configuracion

    _set_base(monkeypatch, overrides={"POSTGRES_PORT": "05432"})

    configuracion = Configuracion()

    assert configuracion.postgres_port == 5432


def test_puerto_como_string_de_float_exacto_se_acepta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regresión: pydantic acepta "5432.0" para un campo int porque el float es exacto."""
    from proptech_core.compartido.configuracion import Configuracion

    _set_base(monkeypatch, overrides={"POSTGRES_PORT": "5432.0"})

    configuracion = Configuracion()

    assert configuracion.postgres_port == 5432


def test_puerto_vacio_se_rechaza_y_no_usa_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """POSTGRES_PORT="" está PRESENTE pero vacío: se rechaza, no cae al default 5432."""
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    _set_base(monkeypatch, overrides={"POSTGRES_PORT": ""})

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert "POSTGRES_PORT" in str(exc_info.value)


def test_password_con_newline_y_unicode_no_filtra_valor(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    secreto = "s3cr3t\ncon-ñ-y-emoji-🔥-y-barra/dos:puntos"
    _set_base(monkeypatch, overrides={"POSTGRES_PASSWORD": secreto, "POSTGRES_HOST": ""})

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    mensaje = str(exc_info.value)
    assert secreto not in mensaje
    assert "s3cr3t" not in mensaje


def test_password_muy_largo_no_aparece_en_mensaje_de_otra_falla(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    secreto = "x" * 5000
    _set_base(monkeypatch, overrides={"POSTGRES_PASSWORD": secreto, "POSTGRES_USER": " "})

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    mensaje = str(exc_info.value)
    assert secreto not in mensaje
    assert "POSTGRES_USER" in mensaje


def test_valor_de_una_variable_contiene_nombre_de_otra(monkeypatch: pytest.MonkeyPatch) -> None:
    """POSTGRES_HOST vacío, pero POSTGRES_PASSWORD tiene el string 'POSTGRES_HOST' adentro:
    no debería confundir el parseo de variables nombradas en el error."""
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    _set_base(
        monkeypatch,
        overrides={
            "POSTGRES_HOST": "",
            "POSTGRES_PASSWORD": "valor-que-dice-POSTGRES_HOST-adentro",
        },
    )

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    mensaje = str(exc_info.value)
    assert "POSTGRES_HOST" in mensaje
    assert "valor-que-dice" not in mensaje


def test_traceback_no_filtra_el_password_via_el_cause_suprimido(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La ValidationError original (con el valor crudo en error['input']) se suprime con
    `from None`. Si algo renderizara el traceback completo con __cause__/__context__,
    el valor podría filtrarse igual. Verificamos que __cause__ y __context__ no lo porten."""
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    secreto = "s3cr3t-trace-leak-check"
    _set_base(monkeypatch, overrides={"POSTGRES_PASSWORD": secreto, "POSTGRES_HOST": ""})

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    err = exc_info.value
    texto_completo = "".join(traceback.format_exception(type(err), err, err.__traceback__))
    assert secreto not in texto_completo, "el valor se filtró por el traceback completo"


# --- D11: Redis y PROPTECH_PARAMETROS (cambio 1b) ---


@pytest.mark.parametrize("variable", VARIABLES_STRING_AMPLIADAS)
def test_cada_variable_ampliada_faltante_se_nombra(
    monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.delenv(variable, raising=False)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert variable in str(exc_info.value)


@pytest.mark.parametrize("variable", [*VARIABLES_STRING_AMPLIADAS, "REDIS_PORT"])
def test_cada_variable_ampliada_vacia_se_nombra(
    monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv(variable, "")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert variable in str(exc_info.value)


@pytest.mark.parametrize("variable", VARIABLES_STRING_AMPLIADAS)
def test_cada_variable_ampliada_en_blanco_se_nombra(
    monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv(variable, "   ")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert variable in str(exc_info.value)


def test_redis_port_no_numerico_se_nombra(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv("REDIS_PORT", "abc")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert "REDIS_PORT" in str(exc_info.value)


@pytest.mark.parametrize("puerto", ["0", "70000"])
def test_redis_port_fuera_de_rango_se_nombra(monkeypatch: pytest.MonkeyPatch, puerto: str) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv("REDIS_PORT", puerto)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert "REDIS_PORT" in str(exc_info.value)


def test_proptech_parametros_archivo_inexistente_se_nombra(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv("PROPTECH_PARAMETROS", "/no/existe/parametros.yaml")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert "PROPTECH_PARAMETROS" in str(exc_info.value)


def test_redis_password_no_aparece_en_el_mensaje_de_otra_falla(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secreto = "redis-s3cr3t"
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv("REDIS_PASSWORD", secreto)
    monkeypatch.setenv("POSTGRES_HOST", "")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    mensaje = str(exc_info.value)
    assert secreto not in mensaje
    assert "POSTGRES_HOST" in mensaje


def test_configuracion_expone_valores_de_redis_y_parametros(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from proptech_core.compartido.configuracion import Configuracion

    ruta = tmp_path / "parametros.yaml"
    ruta.write_text("version: 1\n")
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_PASSWORD", "clave")
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(ruta))

    configuracion = Configuracion()

    assert configuracion.redis_host == "redis"
    assert configuracion.redis_port == 6380
    assert configuracion.redis_password == "clave"
    assert configuracion.proptech_parametros == str(ruta)


# --- 6.1: Alembic sólo necesita PostgreSQL (D11) ---


def test_configuracion_base_de_datos_no_necesita_redis_ni_parametros(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Alembic (`migraciones/env.py`) sólo habla con PostgreSQL: su configuración
    no se puede acoplar a Redis ni al archivo de parámetros del sistema."""
    from proptech_core.compartido.configuracion import ConfiguracionBaseDeDatos

    _set_base(
        monkeypatch,
        deletes=["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"],
    )

    configuracion = ConfiguracionBaseDeDatos()

    assert configuracion.postgres_host == "db"
    assert configuracion.postgres_port == 5432
    assert configuracion.postgres_user == "proptech"
    assert configuracion.postgres_password == "pass"
    assert configuracion.postgres_db == "proptech"


def test_configuracion_base_de_datos_sigue_exigiendo_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from proptech_core.compartido.configuracion import (
        ConfiguracionBaseDeDatos,
        ConfiguracionInvalida,
    )

    _set_base(
        monkeypatch,
        deletes=[
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_PASSWORD",
            "PROPTECH_PARAMETROS",
            "POSTGRES_PASSWORD",
        ],
    )

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        ConfiguracionBaseDeDatos()

    assert "POSTGRES_PASSWORD" in str(exc_info.value)


def test_configuracion_base_de_datos_url_sqlalchemy(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_core.compartido.configuracion import ConfiguracionBaseDeDatos

    _set_base(
        monkeypatch,
        deletes=["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"],
    )

    configuracion = ConfiguracionBaseDeDatos()
    url = make_url(configuracion.url_sqlalchemy())

    assert url.host == "db"
    assert url.username == "proptech"


def test_configuracion_completa_es_tambien_configuracion_base_de_datos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`Configuracion` (la que usa la API) es una especialización de
    `ConfiguracionBaseDeDatos` (la que usa Alembic), no un tipo aparte."""
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionBaseDeDatos

    configuracion = Configuracion()

    assert isinstance(configuracion, ConfiguracionBaseDeDatos)
