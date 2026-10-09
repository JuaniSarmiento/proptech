"""Configuración del sistema: una sola fuente de verdad, por variables de entorno (H45)."""

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class ConfiguracionInvalida(Exception):
    """Falta o es inválida alguna variable de entorno de configuración."""


class _ConfiguracionBase(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    postgres_host: str
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_user: str
    postgres_password: str
    postgres_db: str

    @field_validator("postgres_host", "postgres_user", "postgres_password", "postgres_db")
    @classmethod
    def _no_vacio_ni_blanco(cls, valor: str) -> str:
        """Una variable presente pero vacía/con sólo espacios no es un valor válido."""
        if not valor.strip():
            raise ValueError("no puede estar vacío ni ser sólo espacios")
        return valor


class Configuracion:
    """Variables de conexión a PostgreSQL.

    Entran sólo por variables de entorno, nunca con valores por defecto para
    el password: si falta, se nombra la variable de entorno (no el campo
    interno) y nunca se imprime ningún valor.
    """

    def __init__(self) -> None:
        try:
            base = _ConfiguracionBase()
        except ValidationError as error:
            # Cualquier error (falta, vacía, mal tipada, puerto fuera de rango) nombra
            # la variable de entorno responsable; nunca se incluye el valor recibido
            # (ni acá ni en `error` mismo, que no se imprime en ningún lado).
            faltantes = sorted(
                {str(e["loc"][0]).upper() for e in error.errors() if e["type"] == "missing"}
            )
            invalidas = sorted(
                {
                    str(e["loc"][0]).upper()
                    for e in error.errors()
                    if e["type"] != "missing" and e["loc"]
                }
            )
            partes = []
            if faltantes:
                partes.append(f"falta configurar: {', '.join(faltantes)}")
            if invalidas:
                partes.append(f"valor inválido en: {', '.join(invalidas)}")
            detalle = "; ".join(partes) if partes else "variables de entorno inválidas"
            raise ConfiguracionInvalida(f"Configuración inválida — {detalle}") from None
        self.postgres_host = base.postgres_host
        self.postgres_port = base.postgres_port
        self.postgres_user = base.postgres_user
        self.postgres_password = base.postgres_password
        self.postgres_db = base.postgres_db

    def url_sqlalchemy(self) -> str:
        """Arma la URL de conexión escapando caracteres especiales del password."""
        url = URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )
        return url.render_as_string(hide_password=False)
