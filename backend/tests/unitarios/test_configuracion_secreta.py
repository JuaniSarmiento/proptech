"""Tests de `Configuracion` con contraseñas marcadas (D18). Cambio 1c, tarea 3.5.

Escenarios de `entorno-de-ejecucion`: Contraseñas fuera de la representación
de la configuración; API sin cadena de conexión (regresión). Lecciones:
L-002, L-007.
"""

import json
from pathlib import Path

import pytest
from pydantic import SecretStr

from proptech_core.compartido.configuracion import Configuracion

RAIZ_SRC = Path(__file__).resolve().parents[2] / "src"

SECRETO_POSTGRES = "secreto-postgres-f93a2b"
SECRETO_REDIS = "secreto-redis-c71e4d"


def _configuracion_con_secretos(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Configuracion:
    ruta = tmp_path / "parametros.yaml"
    ruta.write_text("version: 1\n")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_APP_USER", "proptech_app")
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", SECRETO_POSTGRES)
    monkeypatch.setenv("POSTGRES_DB", "proptech")
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_PASSWORD", SECRETO_REDIS)
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(ruta))
    return Configuracion()


def test_las_dos_contrasenas_son_secretstr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    configuracion = _configuracion_con_secretos(monkeypatch, tmp_path)
    assert isinstance(configuracion.postgres_password, SecretStr)
    assert isinstance(configuracion.redis_password, SecretStr)


def test_repr_no_contiene_ninguna_contrasena(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configuracion = _configuracion_con_secretos(monkeypatch, tmp_path)
    texto = repr(configuracion)
    assert SECRETO_POSTGRES not in texto
    assert SECRETO_REDIS not in texto


def test_str_no_contiene_ninguna_contrasena(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configuracion = _configuracion_con_secretos(monkeypatch, tmp_path)
    texto = str(configuracion)
    assert SECRETO_POSTGRES not in texto
    assert SECRETO_REDIS not in texto


def test_vars_no_contiene_ninguna_contrasena(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configuracion = _configuracion_con_secretos(monkeypatch, tmp_path)
    valores = vars(configuracion)
    texto = str(valores)
    assert SECRETO_POSTGRES not in texto
    assert SECRETO_REDIS not in texto


def test_json_dumps_de_vars_no_contiene_ninguna_contrasena(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configuracion = _configuracion_con_secretos(monkeypatch, tmp_path)
    texto = json.dumps(vars(configuracion), default=str)
    assert SECRETO_POSTGRES not in texto
    assert SECRETO_REDIS not in texto


def test_url_sqlalchemy_sigue_devolviendo_la_contrasena_real(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`url_sqlalchemy()` es el único método con permiso de leer el valor
    real (D18): el engine lo necesita para conectarse."""
    from sqlalchemy.engine import make_url

    configuracion = _configuracion_con_secretos(monkeypatch, tmp_path)
    url = make_url(configuracion.url_sqlalchemy())
    assert url.password == SECRETO_POSTGRES


def test_get_secret_value_solo_aparece_en_configuracion_o_conexion_redis() -> None:
    """D18: el valor real de un secreto se lee sólo en el borde. Recorre el
    código fuente y exige que `get_secret_value` no aparezca en ningún otro
    archivo (p.ej. en `salud.py` o en un router).

    `sobres.py` (D6, cambio 2b) y `clerk_http.py` (D7, cambio 2b tarea 5.4)
    son también borde: cifran/descifran el sobre de la invitación y
    autentican contra Clerk respectivamente, y ninguno de los dos existía
    cuando se escribió esta lista (deuda pre-existente, nunca actualizada
    en 5.2)."""
    archivos_permitidos = {"configuracion.py", "conexion_redis.py", "sobres.py", "clerk_http.py"}
    ofensores = []
    for archivo in RAIZ_SRC.rglob("*.py"):
        if archivo.name in archivos_permitidos:
            continue
        if "get_secret_value" in archivo.read_text(encoding="utf-8"):
            ofensores.append(str(archivo.relative_to(RAIZ_SRC)))
    assert not ofensores, f"get_secret_value fuera de lugar en: {ofensores}"


def test_las_contrasenas_vacias_o_en_blanco_se_siguen_rechazando(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_APP_USER", "proptech_app")
    monkeypatch.setenv("POSTGRES_DB", "proptech")
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6379")

    monkeypatch.setenv("POSTGRES_APP_PASSWORD", "")
    monkeypatch.setenv("REDIS_PASSWORD", "clave")
    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()
    assert "POSTGRES_APP_PASSWORD" in str(exc_info.value)

    monkeypatch.setenv("POSTGRES_APP_PASSWORD", "clave")
    monkeypatch.setenv("REDIS_PASSWORD", "   ")
    with pytest.raises(ConfiguracionInvalida) as exc_info:
        Configuracion()
    assert "REDIS_PASSWORD" in str(exc_info.value)
