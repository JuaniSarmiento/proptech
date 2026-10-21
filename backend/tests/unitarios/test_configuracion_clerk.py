"""D1 y configuración: sólo entorno, validación común de API/worker (L-002/009)."""

import base64
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from pydantic import SecretStr

from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

EMISOR = "https://instancia-ficticia.clerk.accounts.dev"
ORIGEN = "https://proptech.example.test"
RAIZ = Path(__file__).resolve().parents[3]
VARIABLES = (
    "CLERK_JWT_KEY",
    "CLERK_PARTES_AUTORIZADAS",
    "CLERK_EMISOR",
    "CLERK_SECRET_KEY",
    "INVITACIONES_CLAVE_CIFRADO",
    "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
    "PROPTECH_URL_PUBLICA",
)


@pytest.fixture(autouse=True)
def limpiar_clerk(monkeypatch: pytest.MonkeyPatch) -> None:
    for nombre in VARIABLES:
        monkeypatch.delenv(nombre, raising=False)


@pytest.fixture(scope="module")
def pem() -> dict[str, str]:
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    corta = rsa.generate_private_key(public_exponent=65537, key_size=1024)  # noqa: S505 (ataque)
    curva = ec.generate_private_key(ec.SECP256R1())
    return {
        "publica": privada.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode(),
        "privada": privada.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
        "corta": corta.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode(),
        "ec": curva.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode(),
    }


def habilitar(monkeypatch: pytest.MonkeyPatch, pem: dict[str, str]) -> None:
    monkeypatch.setenv("CLERK_JWT_KEY", pem["publica"])
    monkeypatch.setenv("CLERK_PARTES_AUTORIZADAS", ORIGEN + ",http://localhost:3100")
    monkeypatch.setenv("CLERK_EMISOR", EMISOR)


def test_sin_clave_login_apagado() -> None:
    config = Configuracion()
    assert config.clerk_jwt_key is None
    assert config.clerk_partes_autorizadas == ()
    assert config.clerk_emisor is None


def test_configurada_desde_entorno(monkeypatch: pytest.MonkeyPatch, pem: dict[str, str]) -> None:
    habilitar(monkeypatch, pem)
    config = Configuracion()
    assert config.clerk_jwt_key == pem["publica"]
    assert config.clerk_partes_autorizadas == (ORIGEN, "http://localhost:3100")
    assert config.clerk_emisor == EMISOR


@pytest.mark.parametrize(
    "forma", ["vacia", "espacios", "texto", "recortada", "privada", "ec", "corta"]
)
def test_pem_roto_no_expone_valor(
    monkeypatch: pytest.MonkeyPatch, pem: dict[str, str], forma: str
) -> None:
    habilitar(monkeypatch, pem)
    valores = {
        **pem,
        "vacia": "",
        "espacios": "   ",
        "texto": "pem-marcado-invalido",
        "recortada": pem["publica"][:-40],
    }
    monkeypatch.setenv("CLERK_JWT_KEY", valores[forma])
    with pytest.raises(ConfiguracionInvalida) as error:
        Configuracion()
    assert "CLERK_JWT_KEY" in str(error.value)
    if valores[forma].strip():
        assert valores[forma] not in str(error.value)
    assert "BEGIN" not in str(error.value)


@pytest.mark.parametrize(
    "valor",
    [
        "",
        " ",
        "https://*.example.test",
        "https://example .test",
        "ftp://example.test",
        "https://example.test/ruta",
        "https://example.test?x=y",
        "https://example.test#fragmento",
        "https://usuario:clave@example.test",
        "http://example.test",
        ORIGEN + ",",
        "," + ORIGEN,
        "https://example.test:abc",
        "https://example.test\n",
    ],
)
def test_partes_rotas(monkeypatch: pytest.MonkeyPatch, pem: dict[str, str], valor: str) -> None:
    habilitar(monkeypatch, pem)
    monkeypatch.setenv("CLERK_PARTES_AUTORIZADAS", valor)
    with pytest.raises(ConfiguracionInvalida, match="CLERK_PARTES_AUTORIZADAS"):
        Configuracion()


@pytest.mark.parametrize("variable", ["CLERK_EMISOR", "CLERK_PARTES_AUTORIZADAS"])
def test_obligatorias_con_clave(
    monkeypatch: pytest.MonkeyPatch, pem: dict[str, str], variable: str
) -> None:
    habilitar(monkeypatch, pem)
    monkeypatch.delenv(variable)
    with pytest.raises(ConfiguracionInvalida, match=variable):
        Configuracion()


@pytest.mark.parametrize(
    "valor",
    [
        "",
        " ",
        "https://*.clerk.accounts.dev",
        "https://otra .clerk.accounts.dev",
        EMISOR + "/ruta",
        EMISOR + "?consulta=si",
        "instancia-sin-esquema",
        "ftp://instancia.test",
    ],
)
def test_emisor_roto(monkeypatch: pytest.MonkeyPatch, pem: dict[str, str], valor: str) -> None:
    habilitar(monkeypatch, pem)
    monkeypatch.setenv("CLERK_EMISOR", valor)
    with pytest.raises(ConfiguracionInvalida, match="CLERK_EMISOR"):
        Configuracion()


def test_secretos_ocultos(monkeypatch: pytest.MonkeyPatch) -> None:
    cifrado = base64.b64encode(bytes(range(32))).decode()
    secreto_clerk = "clave-ficticia-del-worker"
    monkeypatch.setenv("CLERK_SECRET_KEY", secreto_clerk)
    monkeypatch.setenv("INVITACIONES_CLAVE_CIFRADO", cifrado)
    config = Configuracion()
    assert isinstance(config.clerk_secret_key, SecretStr)
    assert isinstance(config.invitaciones_clave_cifrado, SecretStr)
    assert config.clave_para_invitar() == SecretStr(cifrado)
    for representacion in (
        repr(config),
        str(vars(config)),
        repr(config.clerk_secret_key),
        repr(config.invitaciones_clave_cifrado),
    ):
        assert secreto_clerk not in representacion
        assert cifrado not in representacion


@pytest.mark.parametrize(
    "valor",
    [
        "",
        "   ",
        "no-base64!",
        "A" * 43,
        "w7E=",
        "eA==",
        base64.b64encode(b"x" * 31).decode(),
        base64.b64encode(b"x" * 33).decode(),
    ],
)
def test_clave_de_cifrado_rota(monkeypatch: pytest.MonkeyPatch, valor: str) -> None:
    monkeypatch.setenv("INVITACIONES_CLAVE_CIFRADO", valor)
    with pytest.raises(ConfiguracionInvalida) as error:
        Configuracion()
    assert "INVITACIONES_CLAVE_CIFRADO" in str(error.value)
    if valor.strip():
        assert valor not in str(error.value)


def test_invitar_exige_clave_propia_sin_exigirla_al_worker() -> None:
    config = Configuracion()
    assert config.invitaciones_clave_cifrado is None
    with pytest.raises(ConfiguracionInvalida, match="INVITACIONES_CLAVE_CIFRADO"):
        config.clave_para_invitar()


@pytest.mark.parametrize(
    "arranque",
    ["from proptech_api.app import crear_app; crear_app()", "import proptech_worker.ajustes"],
)
@pytest.mark.parametrize(
    "variable",
    ["CLERK_JWT_KEY", "CLERK_EMISOR", "CLERK_PARTES_AUTORIZADAS", "INVITACIONES_CLAVE_CIFRADO"],
)
def test_api_y_worker_rechazan_la_misma_configuracion_rota(
    monkeypatch: pytest.MonkeyPatch, pem: dict[str, str], arranque: str, variable: str
) -> None:
    habilitar(monkeypatch, pem)
    marcador = "valor-roto-marcado"
    monkeypatch.setenv(variable, marcador)
    resultado = subprocess.run(
        [sys.executable, "-c", arranque],
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert resultado.returncode != 0
    assert variable in resultado.stderr
    assert marcador not in resultado.stdout + resultado.stderr


def test_configuracion_no_lee_archivos_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic_settings.sources import DotEnvSettingsSource

    from proptech_core.compartido.configuracion import _LectorDeApp

    assert _LectorDeApp.model_config.get("env_file") is None

    def prohibido(*args: object, **kwargs: object) -> dict[str, object]:
        pytest.fail("la configuración no debe leer archivos .env")

    monkeypatch.setattr(DotEnvSettingsSource, "_read_env_file", prohibido)
    assert Configuracion().clerk_jwt_key is None


def test_nombres_sin_valores_y_cifrado_fuera_de_worker_y_web() -> None:
    ejemplo = (RAIZ / "infra/.env.example").read_text()
    for variable in VARIABLES:
        assert f"{variable}=\n" in ejemplo
    compose = yaml.safe_load((RAIZ / "infra/compose.yaml").read_text())
    for servicio in ("worker", "web"):
        assert "INVITACIONES_CLAVE_CIFRADO" not in compose["services"][servicio].get(
            "environment", {}
        )
