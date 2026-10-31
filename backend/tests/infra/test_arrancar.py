"""Tests de `infra/arrancar.sh` (D7, F-mkdir): el camino de arranque
documentado deja la carpeta de respaldos del host creada y escribible por
`PROPTECH_UID`/`PROPTECH_GID` sin que quien levanta el stack tenga que
crearla antes a mano. Corre el script real con un `docker` falso en el
PATH (L-004), nunca Docker de verdad acá (eso es 6.2/integración real)."""

import os
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
SCRIPT = RAIZ / "infra" / "arrancar.sh"
README = RAIZ / "README.md"


def _correr(
    tmp_path: Path,
    entorno_con_bin_falso: dict[str, str],
    *,
    carpeta: Path,
    args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    entorno = dict(entorno_con_bin_falso)
    entorno["PROPTECH_DIR_RESPALDOS"] = str(carpeta)
    entorno["PROPTECH_UID"] = str(os.getuid()) if hasattr(os, "getuid") else "1000"
    entorno["PROPTECH_GID"] = str(os.getgid()) if hasattr(os, "getgid") else "1000"
    return subprocess.run(
        ["bash", str(SCRIPT), *(args or ["config"])],
        env=entorno,
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


FAKE_DOCKER_REGISTRA = """
echo "$@" >> "$REGISTRO_DOCKER"
exit 0
"""


def test_script_existe() -> None:
    assert SCRIPT.exists(), "falta infra/arrancar.sh"


class TestPrimerArranqueSinCarpeta:
    def test_crea_la_carpeta_con_el_dueno_del_host(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_REGISTRA)
        registro = tmp_path / "registro-docker.txt"
        carpeta = tmp_path / "datos-respaldos"
        assert not carpeta.exists()

        entorno = dict(entorno_con_bin_falso)
        entorno["REGISTRO_DOCKER"] = str(registro)
        resultado = _correr(tmp_path, entorno, carpeta=carpeta)

        assert resultado.returncode == 0, resultado.stderr
        assert carpeta.is_dir(), "la carpeta debía quedar creada"
        assert registro.exists(), "no se llegó a invocar docker compose"

    def test_delega_en_docker_compose_up_con_los_argumentos(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_REGISTRA)
        registro = tmp_path / "registro-docker.txt"
        carpeta = tmp_path / "datos-respaldos"

        entorno = dict(entorno_con_bin_falso)
        entorno["REGISTRO_DOCKER"] = str(registro)
        resultado = _correr(tmp_path, entorno, carpeta=carpeta, args=["up", "--build"])

        assert resultado.returncode == 0, resultado.stderr
        invocacion = registro.read_text().strip()
        assert invocacion == "compose up --build", invocacion


class TestCarpetaYaCreada:
    def test_no_cambia_el_contenido_ni_falla(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_REGISTRA)
        registro = tmp_path / "registro-docker.txt"
        carpeta = tmp_path / "datos-respaldos"
        carpeta.mkdir()
        backup_viejo = carpeta / "proptech-20261001T000000Z.dump"
        backup_viejo.write_text("contenido de prueba")

        entorno = dict(entorno_con_bin_falso)
        entorno["REGISTRO_DOCKER"] = str(registro)
        resultado = _correr(tmp_path, entorno, carpeta=carpeta)

        assert resultado.returncode == 0, resultado.stderr
        assert backup_viejo.exists()
        assert backup_viejo.read_text() == "contenido de prueba"


class TestElReadmeYaNoPideElPasoManual:
    def test_sin_mkdir_de_datos_respaldos(self) -> None:
        texto = README.read_text(encoding="utf-8")
        assert "mkdir -p infra/datos-respaldos" not in texto, (
            "el README todavía pide crear la carpeta a mano"
        )

    def test_la_variable_sigue_documentada(self) -> None:
        texto = README.read_text(encoding="utf-8")
        assert "PROPTECH_DIR_RESPALDOS" in texto
