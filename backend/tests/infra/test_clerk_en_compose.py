"""D4/6.3: distribución completa de variables y arranque sin claves reales."""

import json
import os
import subprocess
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[3]
CLAVE_PUBLICABLE = "pk_test_cHJvcHRlY2gtcHJ1ZWJhLmNsZXJrLmFjY291bnRzLmRldiQ="
VARIABLES = {
    "CLERK_JWT_KEY",
    "CLERK_PARTES_AUTORIZADAS",
    "CLERK_EMISOR",
    "CLERK_SECRET_KEY",
    "INVITACIONES_CLAVE_CIFRADO",
    "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
    "PROPTECH_URL_PUBLICA",
}


def test_cada_variable_solo_en_los_servicios_firmados() -> None:
    servicios = yaml.safe_load((RAIZ / "infra/compose.yaml").read_text())["services"]
    ubicaciones = {
        variable: {
            nombre
            for nombre, servicio in servicios.items()
            if variable in servicio.get("environment", {})
        }
        for variable in VARIABLES - {"NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"}
    }
    assert ubicaciones == {
        "CLERK_JWT_KEY": {"api", "web"},
        "CLERK_PARTES_AUTORIZADAS": {"api", "web"},
        "CLERK_EMISOR": {"api"},
        "CLERK_SECRET_KEY": {"worker", "web"},
        "INVITACIONES_CLAVE_CIFRADO": {"api"},
        "PROPTECH_URL_PUBLICA": {"worker", "web"},
    }
    argumentos = {
        nombre: servicio["build"]["args"]
        for nombre, servicio in servicios.items()
        if isinstance(servicio.get("build"), dict) and servicio["build"].get("args")
    }
    assert argumentos == {
        "web": {"NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY": "${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:-}"}
    }
    assert "ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" in (RAIZ / "web/Dockerfile").read_text()


def test_compose_resuelve_el_ejemplo_con_opcionales_sin_valor_y_clave_publicable_de_prueba() -> (
    None
):
    # Entorno cerrado: no hereda credenciales y --env-file evita leer infra/.env.
    entorno = {
        "PATH": os.environ["PATH"],
        "PROPTECH_DIR_RESPALDOS": str(RAIZ / "infra/datos-respaldos"),
        "PROPTECH_UID": "1000",
        "PROPTECH_GID": "1000",
        "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY": CLAVE_PUBLICABLE,
    }
    resultado = subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            "proptech",
            "--env-file",
            ".env.example",
            "config",
            "--format",
            "json",
        ],
        cwd=RAIZ / "infra",
        env=entorno,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    servicios = json.loads(resultado.stdout)["services"]
    presentes = {
        nombre: {
            clave: valor
            for clave, valor in servicio.get("environment", {}).items()
            if clave in VARIABLES
        }
        for nombre, servicio in servicios.items()
    }
    assert presentes == {
        nombre: dict.fromkeys(claves)
        for nombre, claves in {
            "api": {
                "CLERK_JWT_KEY",
                "CLERK_PARTES_AUTORIZADAS",
                "CLERK_EMISOR",
                "INVITACIONES_CLAVE_CIFRADO",
            },
            "worker": {"CLERK_SECRET_KEY", "PROPTECH_URL_PUBLICA"},
            "web": {
                "CLERK_JWT_KEY",
                "CLERK_PARTES_AUTORIZADAS",
                "CLERK_SECRET_KEY",
                "PROPTECH_URL_PUBLICA",
            },
            "db": set(),
            "redis": set(),
            "migraciones": set(),
            "respaldos": set(),
            "caddy": set(),
        }.items()
    }, "Compose conserva null para las variables que omitirá en el contenedor; nunca cadenas vacías"
    assert (
        servicios["web"]["build"]["args"]["NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"]
        == entorno["NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"]
    )


def test_compose_transmite_los_valores_configurados_sin_defaults_de_clerk() -> None:
    entorno = {"PATH": os.environ["PATH"]} | {
        variable: f"valor-inventado-para-config-{variable}" for variable in VARIABLES
    }
    resultado = subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            "proptech",
            "--env-file",
            ".env.example",
            "config",
            "--format",
            "json",
        ],
        cwd=RAIZ / "infra",
        env=entorno,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    servicios = json.loads(resultado.stdout)["services"]
    recibidas = {
        nombre: {
            clave: valor
            for clave, valor in servicio.get("environment", {}).items()
            if clave in VARIABLES
        }
        for nombre, servicio in servicios.items()
    }
    assert recibidas == {
        nombre: {clave: entorno[clave] for clave in claves}
        for nombre, claves in {
            "api": {
                "CLERK_JWT_KEY",
                "CLERK_PARTES_AUTORIZADAS",
                "CLERK_EMISOR",
                "INVITACIONES_CLAVE_CIFRADO",
            },
            "worker": {"CLERK_SECRET_KEY", "PROPTECH_URL_PUBLICA"},
            "web": {
                "CLERK_JWT_KEY",
                "CLERK_PARTES_AUTORIZADAS",
                "CLERK_SECRET_KEY",
                "PROPTECH_URL_PUBLICA",
            },
            "db": set(),
            "redis": set(),
            "migraciones": set(),
            "respaldos": set(),
            "caddy": set(),
        }.items()
    }
