"""Configuración del sistema: una sola fuente de verdad, por variables de entorno (H45)."""

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


def _entero_ascii_estricto(valor: object) -> object:
    if isinstance(valor, str) and not _PATRON_ENTERO_ASCII.fullmatch(valor):
        raise ValueError("no es un entero válido (sólo dígitos ASCII, sin signo ni separadores)")
    return valor


def _mensaje_configuracion_invalida(error: ValidationError) -> str:
    """Arma el mensaje de `ConfiguracionInvalida` nombrando cada variable con
    problemas, sin incluir nunca el valor recibido (ni acá ni en `error`
    mismo, que no se imprime en ningún lado)."""
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


class _ConfiguracionBaseDeDatosBase(BaseSettings):
    """Sólo las variables de PostgreSQL. Alembic (`migraciones/env.py`) y
    cualquier proceso que sólo hable con la base arrancan con esto, sin
    acoplarse a Redis ni a los parámetros del sistema (D11, tarea 6.1)."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    postgres_host: str
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str

    @field_validator("postgres_port", mode="before")
    @classmethod
    def _postgres_port_entero_ascii_estricto(cls, valor: object) -> object:
        """Gemelo de `_enteros_ascii_estrictos` en `_ConfiguracionBase`
        (L-009, vuelta 3 F10b): `postgres_port` vive en esta clase base (la
        que también usa Alembic) y se le había aplicado el validador de L-008
        sólo a `redis_port` y los `db_pool_*`, nunca a este gemelo."""
        return _entero_ascii_estricto(valor)

    @field_validator("postgres_host", "postgres_user", "postgres_db")
    @classmethod
    def _no_vacio_ni_blanco(cls, valor: str) -> str:
        """Una variable presente pero vacía/con sólo espacios no es un valor válido."""
        if not valor.strip():
            raise ValueError("no puede estar vacío ni ser sólo espacios")
        return valor

    @field_validator("postgres_password")
    @classmethod
    def _password_no_vacio_ni_blanco(cls, valor: SecretStr) -> SecretStr:
        """Igual que `_no_vacio_ni_blanco`, pero sobre el valor secreto: un
        `SecretStr` no tiene `.strip()` directo (D18)."""
        if not valor.get_secret_value().strip():
            raise ValueError("no puede estar vacío ni ser sólo espacios")
        return valor


class _ConfiguracionBase(_ConfiguracionBaseDeDatosBase):
    """Variables de proceso completas: además de PostgreSQL, Redis y la ruta
    del archivo de parámetros del sistema. Las usan la API y el worker."""

    redis_host: str
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_password: SecretStr
    proptech_parametros: str

    # Parámetros del pool del engine (D18, M14): opcionales con default, así
    # no se suma ninguna variable obligatoria a `.env`. Cuando vienen, se
    # validan con las cinco formas de L-002 (faltante usa el default; vacía,
    # en blanco, con tipo equivocado y fuera de rango nombran la variable).
    db_pool_pre_ping: bool = True
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_pool_recycle_s: int = Field(default=1800, ge=60, le=86400)
    db_pool_timeout_s: int = Field(default=5, ge=1, le=60)
    db_connect_timeout_s: int = Field(default=2, ge=1, le=30)

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
    def _no_vacio_ni_blanco_ampliada(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("no puede estar vacío ni ser sólo espacios")
        return valor

    @field_validator("redis_password")
    @classmethod
    def _redis_password_no_vacio_ni_blanco(cls, valor: SecretStr) -> SecretStr:
        if not valor.get_secret_value().strip():
            raise ValueError("no puede estar vacío ni ser sólo espacios")
        return valor

    @field_validator("proptech_parametros")
    @classmethod
    def _archivo_de_parametros_existe(cls, valor: str) -> str:
        if not Path(valor).is_file():
            raise ValueError("el archivo no existe o no se puede leer")
        return valor


class ConfiguracionBaseDeDatos:
    """Variables de conexión a PostgreSQL, y sólo esas (D11).

    Entran sólo por variables de entorno, nunca con valores por defecto para
    el password: si falta, se nombra la variable de entorno (no el campo
    interno) y nunca se imprime ningún valor. La usa Alembic
    (`migraciones/env.py`): un trabajo de migraciones no tiene por qué
    conocer Redis ni el archivo de parámetros del sistema.
    """

    def __init__(self) -> None:
        try:
            base = _ConfiguracionBaseDeDatosBase()
        except ValidationError as error:
            raise ConfiguracionInvalida(
                f"Configuración inválida — {_mensaje_configuracion_invalida(error)}"
            ) from None
        self.postgres_host = base.postgres_host
        self.postgres_port = base.postgres_port
        self.postgres_user = base.postgres_user
        self.postgres_password = base.postgres_password
        self.postgres_db = base.postgres_db

    def url_sqlalchemy(self) -> str:
        """Arma la URL de conexión escapando caracteres especiales del password.

        Único lugar, junto con `conexion_redis.py` (4.4), con permiso de leer
        el valor real de un secreto (D18): el test `test_get_secret_value_...`
        exige que `get_secret_value` no aparezca en ningún otro archivo.
        """
        url = URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )
        return url.render_as_string(hide_password=False)


class Configuracion(ConfiguracionBaseDeDatos):
    """Variables de proceso completas: PostgreSQL, Redis y la ruta del
    archivo de parámetros del sistema. La usan la API y el worker, que sí
    hablan con Redis y leen los parámetros; Alembic usa `ConfiguracionBaseDeDatos`.
    """

    def __init__(self) -> None:
        try:
            base = _ConfiguracionBase()
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
