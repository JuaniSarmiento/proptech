"""Fixtures compartidos para los tests que corren los scripts de Bash de
`infra/respaldos/` reales, con herramientas falsas (`pg_dump`, `pg_restore`,
`docker`, `id`, `date`) puestas primero en el PATH (L-004: el humo usa las
herramientas reales; estos tests, nunca)."""

import os
import stat
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def carpeta_bin_falso(tmp_path: Path) -> Path:
    carpeta = tmp_path / "bin_falso"
    carpeta.mkdir()
    return carpeta


@pytest.fixture
def entorno_con_bin_falso(carpeta_bin_falso: Path) -> dict[str, str]:
    entorno = dict(os.environ)
    entorno["PATH"] = f"{carpeta_bin_falso}{os.pathsep}{entorno.get('PATH', '')}"
    return entorno


@pytest.fixture
def escribir_herramienta_falsa(carpeta_bin_falso: Path) -> Callable[[str, str], Path]:
    """Devuelve una función que escribe un ejecutable de Bash con el nombre y
    el cuerpo dados en la carpeta que encabeza el PATH de estos tests."""

    def _escribir(nombre: str, cuerpo: str) -> Path:
        ruta = carpeta_bin_falso / nombre
        ruta.write_text(f"#!/usr/bin/env bash\n{cuerpo}\n")
        modo_actual = ruta.stat().st_mode
        ruta.chmod(modo_actual | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return ruta

    return _escribir
