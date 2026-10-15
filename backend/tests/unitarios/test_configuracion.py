"""Tests unitarios de las cuatro configuraciones por rol (D3) y de la URL de conexión.

Cada rol lee sólo su propio par de credenciales (usuario/contraseña); host, puerto y
base de datos son comunes a los cuatro. `ConfiguracionDelMigrador`, `ConfiguracionDeRespaldo`
y `Configuracion` (el rol de la app) validan además que el nombre de usuario cumpla
`^proptech_[a-z_]{1,40}$` (D1, L-008): son los tres roles nuevos que este cambio crea con esa
convención. `ConfiguracionDeArranque` lee `POSTGRES_USER`, el superusuario de la imagen oficial
de PostgreSQL, que no sigue esa convención (hoy vale "proptech" en `.env.example`) y por eso no
se le exige el patrón.
"""

import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy.engine import URL, make_url

from proptech_core.compartido.configuracion import (
    Configuracion,
    ConfiguracionBaseDeDatos,
    ConfiguracionDeArranque,
    ConfiguracionDelMigrador,
    ConfiguracionDeRespaldo,
    ConfiguracionInvalida,
)

# --- Tabla de roles: para correr la misma batería de casos sobre los cuatro ---


@dataclass(frozen=True)
class _Rol:
    nombre: str
    clase: Callable[[], object]
    var_usuario: str
    var_password: str
    usuario_ok: str
    exige_patron: bool


ROLES = [
    _Rol(
        "arranque",
        ConfiguracionDeArranque,
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "proptech",
        False,
    ),
    _Rol(
        "migrador",
        ConfiguracionDelMigrador,
        "POSTGRES_MIGRADOR_USER",
        "POSTGRES_MIGRADOR_PASSWORD",
        "proptech_migrador",
        True,
    ),
    _Rol(
        "respaldo",
        ConfiguracionDeRespaldo,
        "POSTGRES_RESPALDO_USER",
        "POSTGRES_RESPALDO_PASSWORD",
        "proptech_respaldo",
        True,
    ),
    _Rol("app", Configuracion, "POSTGRES_APP_USER", "POSTGRES_APP_PASSWORD", "proptech_app", True),
]

_PARAMETROS_DEL_REPO = Path(__file__).resolve().parents[3] / "config" / "parametros.yaml"


def _set_comun(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "proptech")


def _set_ampliadas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sólo las necesita `Configuracion` (API y worker, D11); las otras tres no."""
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_PASSWORD", "redis-pass")
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(_PARAMETROS_DEL_REPO))


def _set_rol_ok(monkeypatch: pytest.MonkeyPatch, rol: _Rol) -> None:
    _set_comun(monkeypatch)
    monkeypatch.setenv(rol.var_usuario, rol.usuario_ok)
    monkeypatch.setenv(rol.var_password, "clave-de-prueba")
    if rol.nombre == "app":
        _set_ampliadas(monkeypatch)


def _instanciar(rol: _Rol) -> object:
    return rol.clase()


# --- Cada rol lee SÓLO su propio par: los otros tres pares no bastan ---


@pytest.mark.parametrize("rol", ROLES, ids=lambda r: r.nombre)
def test_cada_rol_no_arranca_con_el_par_de_otro_rol(
    monkeypatch: pytest.MonkeyPatch, rol: _Rol
) -> None:
    _set_comun(monkeypatch)
    if rol.nombre != "app":
        _set_ampliadas(monkeypatch)  # para no fallar por Redis si el rol es "app" sin querer
    # Pone las credenciales de TODOS los otros roles, nunca las del propio.
    for otro in ROLES:
        if otro.nombre == rol.nombre:
            continue
        monkeypatch.setenv(otro.var_usuario, otro.usuario_ok)
        monkeypatch.setenv(otro.var_password, "clave-de-otro-rol")
    # El propio par, ausente (nunca alcanza con el de otro rol): lo sacamos
    # explícito, sin confiar en que el conftest no lo haya puesto por default.
    monkeypatch.delenv(rol.var_usuario, raising=False)
    monkeypatch.delenv(rol.var_password, raising=False)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        _instanciar(rol)

    mensaje = str(exc_info.value)
    assert rol.var_usuario in mensaje
    assert rol.var_password in mensaje


def test_configuracion_app_no_arranca_con_solo_postgres_user_y_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caso explícito de 2.1: el histórico POSTGRES_USER/POSTGRES_PASSWORD (el par del
    rol de arranque) ya no alcanza para `Configuracion` (D3): exige POSTGRES_APP_USER/_PASSWORD."""
    _set_comun(monkeypatch)
    _set_ampliadas(monkeypatch)
    monkeypatch.setenv("POSTGRES_USER", "proptech")
    monkeypatch.setenv("POSTGRES_PASSWORD", "cualquier-cosa")
    monkeypatch.delenv("POSTGRES_APP_USER", raising=False)
    monkeypatch.delenv("POSTGRES_APP_PASSWORD", raising=False)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    mensaje = str(exc_info.value)
    assert "POSTGRES_APP_USER" in mensaje
    assert "POSTGRES_APP_PASSWORD" in mensaje


# --- Por cada rol: faltante, vacía, en blanco, con espacios alrededor ---


@pytest.mark.parametrize("rol", ROLES, ids=lambda r: r.nombre)
@pytest.mark.parametrize("campo", ["usuario", "password"])
def test_variable_faltante_se_nombra(
    monkeypatch: pytest.MonkeyPatch, rol: _Rol, campo: str
) -> None:
    _set_rol_ok(monkeypatch, rol)
    variable = rol.var_usuario if campo == "usuario" else rol.var_password
    monkeypatch.delenv(variable, raising=False)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        _instanciar(rol)

    assert variable in str(exc_info.value)


@pytest.mark.parametrize("rol", ROLES, ids=lambda r: r.nombre)
@pytest.mark.parametrize("campo", ["usuario", "password"])
def test_variable_vacia_se_nombra(monkeypatch: pytest.MonkeyPatch, rol: _Rol, campo: str) -> None:
    _set_rol_ok(monkeypatch, rol)
    variable = rol.var_usuario if campo == "usuario" else rol.var_password
    monkeypatch.setenv(variable, "")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        _instanciar(rol)

    assert variable in str(exc_info.value)


@pytest.mark.parametrize("rol", ROLES, ids=lambda r: r.nombre)
@pytest.mark.parametrize("campo", ["usuario", "password"])
def test_variable_en_blanco_se_nombra(
    monkeypatch: pytest.MonkeyPatch, rol: _Rol, campo: str
) -> None:
    _set_rol_ok(monkeypatch, rol)
    variable = rol.var_usuario if campo == "usuario" else rol.var_password
    monkeypatch.setenv(variable, "   ")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        _instanciar(rol)

    assert variable in str(exc_info.value)


@pytest.mark.parametrize("rol", ROLES, ids=lambda r: r.nombre)
@pytest.mark.parametrize("campo", ["usuario", "password"])
def test_variable_con_espacios_alrededor_se_nombra(
    monkeypatch: pytest.MonkeyPatch, rol: _Rol, campo: str
) -> None:
    """Un valor con contenido real pero con espacios de sobra alrededor tampoco es válido:
    un ` proptech_app ` pegado por accidente en `.env` no es el rol `proptech_app`."""
    _set_rol_ok(monkeypatch, rol)
    variable = rol.var_usuario if campo == "usuario" else rol.var_password
    valor_real = rol.usuario_ok if campo == "usuario" else "clave-de-prueba"
    monkeypatch.setenv(variable, f"  {valor_real}  ")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        _instanciar(rol)

    assert variable in str(exc_info.value)


# --- Patrón de nombre de rol: sólo migrador, respaldo y app (D1) ---


ROLES_CON_PATRON = [r for r in ROLES if r.exige_patron]


@pytest.mark.parametrize("rol", ROLES_CON_PATRON, ids=lambda r: r.nombre)
@pytest.mark.parametrize(
    "nombre_invalido",
    [
        "otra_cosa",
        "Proptech_App",  # mayúsculas: el patrón es todo minúsculas
        "proptech-app",  # guion, no guion bajo
        "proptech_",  # sin nada después del guion bajo
        "proptech_app1",  # con un dígito ASCII: tampoco está en [a-z_]
        "proptech_app٥",  # con un dígito NO ascii (L-008)  # noqa: RUF001
    ],
)
def test_nombre_de_usuario_fuera_del_patron_se_nombra(
    monkeypatch: pytest.MonkeyPatch, rol: _Rol, nombre_invalido: str
) -> None:
    _set_rol_ok(monkeypatch, rol)
    monkeypatch.setenv(rol.var_usuario, nombre_invalido)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        _instanciar(rol)

    assert rol.var_usuario in str(exc_info.value)


@pytest.mark.parametrize("rol", ROLES_CON_PATRON, ids=lambda r: r.nombre)
def test_nombre_de_usuario_dentro_del_patron_se_acepta(
    monkeypatch: pytest.MonkeyPatch, rol: _Rol
) -> None:
    _set_rol_ok(monkeypatch, rol)

    configuracion = _instanciar(rol)

    assert configuracion.postgres_user == rol.usuario_ok  # type: ignore[attr-defined]


def test_arranque_acepta_un_nombre_que_no_sigue_el_patron_proptech(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El rol de arranque es el superusuario de la imagen oficial: su nombre lo elige
    quien despliega (hoy "proptech" en `.env.example`), no esta convención."""
    _set_comun(monkeypatch)
    monkeypatch.setenv("POSTGRES_USER", "proptech")
    monkeypatch.setenv("POSTGRES_PASSWORD", "clave")

    configuracion = ConfiguracionDeArranque()

    assert configuracion.postgres_user == "proptech"


# --- Ningún valor (ni de otra variable) aparece en el mensaje ni en el traceback ---


@pytest.mark.parametrize("rol", ROLES, ids=lambda r: r.nombre)
def test_password_no_aparece_en_el_mensaje_de_otra_falla(
    monkeypatch: pytest.MonkeyPatch, rol: _Rol
) -> None:
    _set_rol_ok(monkeypatch, rol)
    secreto = "s3cr3t-" + rol.nombre
    monkeypatch.setenv(rol.var_password, secreto)
    monkeypatch.setenv("POSTGRES_HOST", "")  # dispara el error por otra variable

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        _instanciar(rol)

    mensaje = str(exc_info.value)
    assert secreto not in mensaje
    assert "POSTGRES_HOST" in mensaje


def test_traceback_no_filtra_el_password_via_el_cause_suprimido(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_rol_ok(monkeypatch, ROLES[0])
    secreto = "s3cr3t-trace-leak-check"
    monkeypatch.setenv("POSTGRES_PASSWORD", secreto)
    monkeypatch.setenv("POSTGRES_HOST", "")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        ConfiguracionDeArranque()

    err = exc_info.value
    texto_completo = "".join(traceback.format_exception(type(err), err, err.__traceback__))
    assert secreto not in texto_completo


# --- Puerto: entero ASCII estricto, igual para los cuatro (comparten el lector común) ---


@pytest.mark.parametrize("rol", ROLES, ids=lambda r: r.nombre)
def test_puerto_no_numerico_se_nombra(monkeypatch: pytest.MonkeyPatch, rol: _Rol) -> None:
    _set_rol_ok(monkeypatch, rol)
    monkeypatch.setenv("POSTGRES_PORT", "abc")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        _instanciar(rol)

    assert "POSTGRES_PORT" in str(exc_info.value)


@pytest.mark.parametrize("rol", ROLES, ids=lambda r: r.nombre)
@pytest.mark.parametrize(
    "valor_laxo",
    ["5432\n", " 5432", "5_432", "+5432", "5432.0"],
    ids=["salto_de_linea", "espacio", "guion_bajo", "signo_mas", "punto_flotante"],
)
def test_puerto_laxo_se_rechaza(
    monkeypatch: pytest.MonkeyPatch, rol: _Rol, valor_laxo: str
) -> None:
    _set_rol_ok(monkeypatch, rol)
    monkeypatch.setenv("POSTGRES_PORT", valor_laxo)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        _instanciar(rol)

    assert "POSTGRES_PORT" in str(exc_info.value)


def test_puerto_con_ceros_a_la_izquierda_se_acepta(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_rol_ok(monkeypatch, ROLES[0])
    monkeypatch.setenv("POSTGRES_PORT", "05432")

    configuracion = ConfiguracionDeArranque()

    assert configuracion.postgres_port == 5432


# --- La URL es un objeto `sqlalchemy.engine.URL`, no un string (M12) ---


@pytest.mark.parametrize("rol", ROLES, ids=lambda r: r.nombre)
def test_url_sqlalchemy_devuelve_un_objeto_url(monkeypatch: pytest.MonkeyPatch, rol: _Rol) -> None:
    _set_rol_ok(monkeypatch, rol)

    configuracion = _instanciar(rol)
    url = configuracion.url_sqlalchemy()  # type: ignore[attr-defined]

    assert isinstance(url, URL)
    assert url.host == "db"
    assert url.username == rol.usuario_ok
    assert url.database == "proptech"


@pytest.mark.parametrize("rol", ROLES, ids=lambda r: r.nombre)
def test_url_str_y_repr_no_traen_el_password(monkeypatch: pytest.MonkeyPatch, rol: _Rol) -> None:
    _set_rol_ok(monkeypatch, rol)
    secreto = "clave-de-prueba"

    configuracion = _instanciar(rol)
    url = configuracion.url_sqlalchemy()  # type: ignore[attr-defined]

    assert secreto not in str(url)
    assert secreto not in repr(url)


def test_url_escapa_password_con_caracteres_especiales(monkeypatch: pytest.MonkeyPatch) -> None:
    password_especial = "p@ss:w/rd"
    _set_comun(monkeypatch)
    monkeypatch.setenv("POSTGRES_USER", "proptech")
    monkeypatch.setenv("POSTGRES_PASSWORD", password_especial)

    configuracion = ConfiguracionDeArranque()
    url = configuracion.url_sqlalchemy()

    assert url.password == password_especial
    assert url.host == "db"
    assert url.port == 5432
    assert url.username == "proptech"
    assert url.database == "proptech"

    # `make_url` tiene que aceptar el objeto directamente (pasa de largo, no re-parsea
    # un string): sigue dando los mismos valores reales.
    url_reparseada = make_url(url)
    assert url_reparseada.password == password_especial


# --- `Configuracion` (D11: también lee Redis y los parámetros) ---


def test_configuracion_expone_valores_de_redis_y_parametros(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ruta = tmp_path / "parametros.yaml"
    ruta.write_text("version: 1\n")
    _set_comun(monkeypatch)
    monkeypatch.setenv("POSTGRES_APP_USER", "proptech_app")
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", "clave")
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_PASSWORD", "clave-redis")
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(ruta))

    configuracion = Configuracion()

    assert configuracion.redis_host == "redis"
    assert configuracion.redis_port == 6380
    assert configuracion.redis_password.get_secret_value() == "clave-redis"
    assert configuracion.proptech_parametros == str(ruta)


def test_proptech_parametros_archivo_inexistente_se_nombra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_rol_ok(monkeypatch, ROLES[-1])  # "app"
    monkeypatch.setenv("PROPTECH_PARAMETROS", "/no/existe/parametros.yaml")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()

    assert "PROPTECH_PARAMETROS" in str(exc_info.value)


# --- 6.1 (D11, cambio 1b): Alembic sólo necesita PostgreSQL, ahora como el migrador ---


def test_configuracion_del_migrador_no_necesita_redis_ni_parametros(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`migraciones/env.py` corre Alembic como `proptech_migrador` (D2): no se acopla
    a Redis ni al archivo de parámetros del sistema, igual que antes con el rol de arranque."""
    _set_comun(monkeypatch)
    monkeypatch.setenv("POSTGRES_MIGRADOR_USER", "proptech_migrador")
    monkeypatch.setenv("POSTGRES_MIGRADOR_PASSWORD", "clave")
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"):
        monkeypatch.delenv(variable, raising=False)

    configuracion = ConfiguracionDelMigrador()

    assert configuracion.postgres_user == "proptech_migrador"


def test_configuracion_base_de_datos_es_alias_del_migrador(monkeypatch: pytest.MonkeyPatch) -> None:
    """`ConfiguracionBaseDeDatos` (el nombre que usaba `env.py` hasta este cambio) sigue
    existiendo como alias de `ConfiguracionDelMigrador`: nadie más que Alembic lo usa."""
    assert ConfiguracionBaseDeDatos is ConfiguracionDelMigrador
