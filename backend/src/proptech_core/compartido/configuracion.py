"""Configuración del sistema: una sola fuente de verdad, por variables de entorno (H45).

D3 (cambio 2a): cada rol de PostgreSQL lee sólo su propio par de credenciales.
Host, puerto y base de datos son comunes a los cuatro (`_LectorPostgresComun`); el
usuario y la contraseña vienen de una variable distinta por rol:

- `ConfiguracionDeArranque`: `POSTGRES_USER`/`POSTGRES_PASSWORD` (el superusuario de la
  imagen oficial de PostgreSQL; su nombre no sigue la convención `proptech_*` porque lo
  elige quien despliega, D1).
- `ConfiguracionDelMigrador`: `POSTGRES_MIGRADOR_USER`/`POSTGRES_MIGRADOR_PASSWORD`
  (corre Alembic; `ConfiguracionBaseDeDatos` es un alias, es el nombre que ya usaba
  `migraciones/env.py`).
- `ConfiguracionDeRespaldo`: `POSTGRES_RESPALDO_USER`/`POSTGRES_RESPALDO_PASSWORD` (sólo
  para validar en tests: `respaldos` es un script de Bash que usa las variables
  estándar de libpq, no esta clase).
- `Configuracion`: `POSTGRES_APP_USER`/`POSTGRES_APP_PASSWORD` (la usan la API y el
  worker), además de Redis y el archivo de parámetros del sistema (D11).

Los tres roles nuevos (migrador, respaldo, app) validan que el nombre de usuario
cumpla `^proptech_[a-z_]{1,40}$` (D1, L-008); el rol de arranque no, porque no es
un nombre que este proyecto elija.
"""

import re
from pathlib import Path

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class ConfiguracionInvalida(Exception):
    """Falta o es inválida alguna variable de entorno de configuración."""


#: Sólo dígitos ASCII (L-008): pydantic en modo laxo convierte `'5\n'`,
#: `' 5'`, `'\t5'` (espacio en blanco alrededor) y `'5.0'` (parte decimal
#: exacta) a `5` sin avisar, y `'5_0'` a `50` (el separador de miles de
#: `int()`), un valor totalmente distinto del que parece. `REDIS_PORT` y los
#: `DB_POOL_*` (D18, M14) son los enteros que vienen de una variable de
#: entorno de texto; `fullmatch` + `re.ASCII` corta las cinco formas antes
#: de que pydantic las convierta.
_PATRON_ENTERO_ASCII = re.compile(r"[0-9]+", flags=re.ASCII)

#: Nombre de rol de PostgreSQL de este proyecto (D1): minúsculas y guion bajo
#: únicamente, con el prefijo `proptech_` y al menos un carácter después. `[a-z_]`
#: no admite dígitos de ningún tipo (ni ASCII ni de otro script, L-008): un nombre
#: con un dígito queda rechazado por el patrón mismo, sin necesidad de un chequeo
#: aparte.
_PATRON_NOMBRE_DE_ROL = re.compile(r"proptech_[a-z_]{1,40}", flags=re.ASCII)


def _entero_ascii_estricto(valor: object) -> object:
    if isinstance(valor, str) and not _PATRON_ENTERO_ASCII.fullmatch(valor):
        raise ValueError("no es un entero válido (sólo dígitos ASCII, sin signo ni separadores)")
    return valor


def _recortado_sin_cambios(valor: str) -> str:
    """Ni vacío ni sólo espacios, y sin espacios de sobra alrededor del valor real:
    `" proptech_app "` no es el rol `proptech_app`, es un error de tipeo en `.env`."""
    if not valor.strip():
        raise ValueError("no puede estar vacío ni ser sólo espacios")
    if valor != valor.strip():
        raise ValueError("no puede tener espacios al principio o al final")
    return valor


def _nombre_de_rol_valido(valor: str) -> str:
    valor = _recortado_sin_cambios(valor)
    if not _PATRON_NOMBRE_DE_ROL.fullmatch(valor):
        raise ValueError("no cumple el patrón de nombre de rol (^proptech_[a-z_]{1,40}$)")
    return valor


def _mensaje_configuracion_invalida(error: ValidationError) -> str:
    """Arma el mensaje de `ConfiguracionInvalida` nombrando cada variable con
    problemas, sin incluir nunca el valor recibido (ni acá ni en `error`
    mismo, que no se imprime en ningún lado). `loc[0]` es el nombre de la
    variable de entorno tal como se validó (el alias, si el campo tiene uno
    por rol: D3), nunca el nombre interno del campo de Python."""
    faltantes = sorted({str(e["loc"][0]).upper() for e in error.errors() if e["type"] == "missing"})
    invalidas = sorted(
        {str(e["loc"][0]).upper() for e in error.errors() if e["type"] != "missing" and e["loc"]}
    )
    partes = []
    if faltantes:
        partes.append(f"falta configurar: {', '.join(faltantes)}")
    if invalidas:
        partes.append(f"valor inválido en: {', '.join(invalidas)}")
    return "; ".join(partes) if partes else "variables de entorno inválidas"


class _LectorPostgresComun(BaseSettings):
    """Host, puerto y base: comunes a los cuatro roles de PostgreSQL (D3)."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    postgres_host: str
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str

    @field_validator("postgres_port", mode="before")
    @classmethod
    def _puerto_entero_ascii_estricto(cls, valor: object) -> object:
        return _entero_ascii_estricto(valor)

    @field_validator("postgres_host", "postgres_db")
    @classmethod
    def _host_y_db_recortados(cls, valor: str) -> str:
        return _recortado_sin_cambios(valor)


class _LectorDeArranque(_LectorPostgresComun):
    postgres_user: str
    postgres_password: SecretStr

    @field_validator("postgres_user")
    @classmethod
    def _usuario_recortado(cls, valor: str) -> str:
        return _recortado_sin_cambios(valor)

    @field_validator("postgres_password")
    @classmethod
    def _password_recortada(cls, valor: SecretStr) -> SecretStr:
        _recortado_sin_cambios(valor.get_secret_value())
        return valor


class _LectorDelMigrador(_LectorPostgresComun):
    postgres_user: str = Field(validation_alias="POSTGRES_MIGRADOR_USER")
    postgres_password: SecretStr = Field(validation_alias="POSTGRES_MIGRADOR_PASSWORD")

    @field_validator("postgres_user")
    @classmethod
    def _usuario_valido(cls, valor: str) -> str:
        return _nombre_de_rol_valido(valor)

    @field_validator("postgres_password")
    @classmethod
    def _password_recortada(cls, valor: SecretStr) -> SecretStr:
        _recortado_sin_cambios(valor.get_secret_value())
        return valor


class _LectorDeRespaldo(_LectorPostgresComun):
    postgres_user: str = Field(validation_alias="POSTGRES_RESPALDO_USER")
    postgres_password: SecretStr = Field(validation_alias="POSTGRES_RESPALDO_PASSWORD")

    @field_validator("postgres_user")
    @classmethod
    def _usuario_valido(cls, valor: str) -> str:
        return _nombre_de_rol_valido(valor)

    @field_validator("postgres_password")
    @classmethod
    def _password_recortada(cls, valor: SecretStr) -> SecretStr:
        _recortado_sin_cambios(valor.get_secret_value())
        return valor


class _LectorDeApp(_LectorPostgresComun):
    """Credenciales de la app (D3) más Redis y el archivo de parámetros (D11):
    las usan la API y el worker, que sí hablan con Redis y leen los parámetros."""

    postgres_user: str = Field(validation_alias="POSTGRES_APP_USER")
    postgres_password: SecretStr = Field(validation_alias="POSTGRES_APP_PASSWORD")

    redis_host: str
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_password: SecretStr
    proptech_parametros: str

    # Parámetros del pool del engine (D18, M14): opcionales con default, así
    # no se suma ninguna variable obligatoria a `.env`.
    db_pool_pre_ping: bool = True
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_pool_recycle_s: int = Field(default=1800, ge=60, le=86400)
    db_pool_timeout_s: int = Field(default=5, ge=1, le=60)
    db_connect_timeout_s: int = Field(default=2, ge=1, le=30)

    @field_validator("postgres_user")
    @classmethod
    def _usuario_valido(cls, valor: str) -> str:
        return _nombre_de_rol_valido(valor)

    @field_validator("postgres_password")
    @classmethod
    def _password_recortada(cls, valor: SecretStr) -> SecretStr:
        _recortado_sin_cambios(valor.get_secret_value())
        return valor

    @field_validator(
        "redis_port",
        "db_pool_size",
        "db_pool_recycle_s",
        "db_pool_timeout_s",
        "db_connect_timeout_s",
        mode="before",
    )
    @classmethod
    def _enteros_ascii_estrictos(cls, valor: object) -> object:
        return _entero_ascii_estricto(valor)

    @field_validator("redis_host", "proptech_parametros")
    @classmethod
    def _recortados(cls, valor: str) -> str:
        return _recortado_sin_cambios(valor)

    @field_validator("redis_password")
    @classmethod
    def _redis_password_recortada(cls, valor: SecretStr) -> SecretStr:
        _recortado_sin_cambios(valor.get_secret_value())
        return valor

    @field_validator("proptech_parametros")
    @classmethod
    def _archivo_de_parametros_existe(cls, valor: str) -> str:
        if not Path(valor).is_file():
            raise ValueError("el archivo no existe o no se puede leer")
        return valor


class _ConfiguracionPostgresBase:
    """Comportamiento común a las cuatro configuraciones públicas: cargar su
    lector privado, envolver el error de pydantic en `ConfiguracionInvalida`
    y armar la URL de conexión como objeto (D3, M12)."""

    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str

    def _cargar(self, lector_cls: type[_LectorPostgresComun]) -> None:
        try:
            base = lector_cls()
        except ValidationError as error:
            raise ConfiguracionInvalida(
                f"Configuración inválida — {_mensaje_configuracion_invalida(error)}"
            ) from None
        self.postgres_host = base.postgres_host
        self.postgres_port = base.postgres_port
        self.postgres_user = base.postgres_user  # type: ignore[attr-defined]
        self.postgres_password = base.postgres_password  # type: ignore[attr-defined]
        self.postgres_db = base.postgres_db

    def url_sqlalchemy(self) -> URL:
        """La URL de conexión como objeto `sqlalchemy.engine.URL` (M12): `create_engine`
        y `engine_from_config` la aceptan tal cual, y su `str()`/`repr()` ocultan la
        contraseña por default (a diferencia del `str` que devolvía antes esta función,
        que la traía en texto plano). Sólo este método y `conexion_redis.py` tienen
        permiso de leer el valor real de un secreto (D18).
        """
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


class ConfiguracionDeArranque(_ConfiguracionPostgresBase):
    """`POSTGRES_USER`/`POSTGRES_PASSWORD`: el superusuario de la imagen oficial.
    Lo usa `proptech_core.compartido.roles` (el paso `antes`/`despues`, D2) y
    `restaurar.sh` desde el host. Ningún servicio permanente lo tiene."""

    def __init__(self) -> None:
        self._cargar(_LectorDeArranque)


class ConfiguracionDelMigrador(_ConfiguracionPostgresBase):
    """`POSTGRES_MIGRADOR_USER`/`POSTGRES_MIGRADOR_PASSWORD`: corre Alembic
    (`migraciones/env.py`), dueño de las tablas de dominio (D1, D2)."""

    def __init__(self) -> None:
        self._cargar(_LectorDelMigrador)


#: Alias: es el nombre que usaba `migraciones/env.py` antes de este cambio, cuando
#: Alembic corría con el rol de arranque. Nadie más que Alembic debería usarlo.
ConfiguracionBaseDeDatos = ConfiguracionDelMigrador


class ConfiguracionDeRespaldo(_ConfiguracionPostgresBase):
    """`POSTGRES_RESPALDO_USER`/`POSTGRES_RESPALDO_PASSWORD`: sólo para validar la
    forma de estas variables en los tests. `respaldos` es un script de Bash que usa
    las variables estándar de libpq (`PGUSER`/`PGPASSWORD`), no esta clase."""

    def __init__(self) -> None:
        self._cargar(_LectorDeRespaldo)


class _LectorDeAppSoloPostgres(_LectorPostgresComun):
    """Igual que `_LectorDeApp`, pero sin Redis ni el archivo de parámetros
    (D1, D2): la usa `roles.py`, que corre en el contenedor `migraciones`
    antes y después de Alembic, donde esas variables no existen."""

    postgres_user: str = Field(validation_alias="POSTGRES_APP_USER")
    postgres_password: SecretStr = Field(validation_alias="POSTGRES_APP_PASSWORD")

    @field_validator("postgres_user")
    @classmethod
    def _usuario_valido(cls, valor: str) -> str:
        return _nombre_de_rol_valido(valor)

    @field_validator("postgres_password")
    @classmethod
    def _password_recortada(cls, valor: SecretStr) -> SecretStr:
        _recortado_sin_cambios(valor.get_secret_value())
        return valor


class ConfiguracionDeAppSoloPostgres(_ConfiguracionPostgresBase):
    """`POSTGRES_APP_USER`/`POSTGRES_APP_PASSWORD`, sin Redis ni el archivo de
    parámetros (D1, D2): la usa `roles.py` para crear y reparar el rol de la
    app sin acoplarse a variables que el contenedor `migraciones` no tiene."""

    def __init__(self) -> None:
        self._cargar(_LectorDeAppSoloPostgres)


class Configuracion(_ConfiguracionPostgresBase):
    """`POSTGRES_APP_USER`/`POSTGRES_APP_PASSWORD` más Redis y los parámetros del
    sistema (D11): la usan la API y el worker."""

    redis_host: str
    redis_port: int
    redis_password: SecretStr
    proptech_parametros: str
    db_pool_pre_ping: bool
    db_pool_size: int
    db_pool_recycle_s: int
    db_pool_timeout_s: int
    db_connect_timeout_s: int

    def __init__(self) -> None:
        try:
            base = _LectorDeApp()
        except ValidationError as error:
            raise ConfiguracionInvalida(
                f"Configuración inválida — {_mensaje_configuracion_invalida(error)}"
            ) from None
        self.postgres_host = base.postgres_host
        self.postgres_port = base.postgres_port
        self.postgres_user = base.postgres_user
        self.postgres_password = base.postgres_password
        self.postgres_db = base.postgres_db
        self.redis_host = base.redis_host
        self.redis_port = base.redis_port
        self.redis_password = base.redis_password
        self.proptech_parametros = base.proptech_parametros
        self.db_pool_pre_ping = base.db_pool_pre_ping
        self.db_pool_size = base.db_pool_size
        self.db_pool_recycle_s = base.db_pool_recycle_s
        self.db_pool_timeout_s = base.db_pool_timeout_s
        self.db_connect_timeout_s = base.db_connect_timeout_s
