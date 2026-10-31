"""D8 (respaldos-2, reemplaza el escenario con `FAKE_PG_DUMP_FALLA` de
`tests/infra/test_respaldos.py:905-940`, L-019): el escenario "Volcado con
el rol equivocado" se prueba con `pg_dump` REAL de la imagen
(`postgres:18.6-trixie`, la misma que usa el servicio `respaldos`) contra la
base REAL del test, con las credenciales de `proptech_app`. Corre
`respaldar.sh` dentro de un contenedor efímero de esa imagen (`docker run
--rm`), conectando al contenedor de `testcontainers` por
`host.docker.internal` (el puerto ya está expuesto al host). Nunca una
herramienta falsa: un `FAKE_PG_DUMP_FALLA` no distingue un rol realmente
rechazado de un compose mal escrito (L-019)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ..conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION
from ._edificios import BaseDeEdificio

RAIZ = Path(__file__).resolve().parents[3]
SCRIPT = RAIZ / "infra" / "respaldos" / "respaldar.sh"
IMAGEN = "postgres:18.6-trixie"

pytestmark = pytest.mark.skipif(
    subprocess.run(["docker", "info"], capture_output=True, check=False).returncode != 0,
    reason="Docker no está disponible en este entorno",
)


def _correr_respaldar_real(
    tmp_path: Path,
    base: BaseDeEdificio,
    *,
    usuario: str,
    password: str,
    args: list[str],
    carpeta: Path | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    if carpeta is None:
        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
    puerto = base.contenedor.get_exposed_port(5432)

    resultado = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--user",
            "1000:1000",
            "--add-host=host.docker.internal:host-gateway",
            "-e",
            f"PGHOST=host.docker.internal",
            "-e",
            f"PGPORT={puerto}",
            "-e",
            f"PGUSER={usuario}",
            "-e",
            f"PGPASSWORD={password}",
            "-e",
            f"PGDATABASE={base.nombre}",
            "-e",
            "RESPALDO_INTERVALO_SEGUNDOS=3600",
            "-e",
            "RESPALDO_CONSERVAR=14",
            "-e",
            "RESPALDO_CONSERVAR_DIAS=14",
            "-e",
            "RESPALDO_LIMITE_SEGUNDOS=30",
            "-e",
            "RESPALDO_CARPETA=/respaldos",
            "-v",
            f"{SCRIPT}:/usr/local/bin/respaldar.sh:ro",
            "-v",
            f"{carpeta}:/respaldos",
            "--entrypoint",
            "/usr/local/bin/respaldar.sh",
            IMAGEN,
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return resultado, carpeta


def _lineas_json(texto: str) -> list[dict[str, object]]:
    return [json.loads(l) for l in texto.splitlines() if l.strip()]


class TestVolcadoConElRolEquivocado:
    def test_rol_de_app_hace_fallar_el_volcado_sin_dejar_archivos(
        self,
        tmp_path: Path,
        base_del_edificio: BaseDeEdificio,
    ) -> None:
        resultado, carpeta = _correr_respaldar_real(
            tmp_path,
            base_del_edificio,
            usuario=APP_USER_DE_SESION,
            password=APP_PASSWORD_DE_SESION,
            args=["--una-vez"],
        )

        assert resultado.returncode != 0, (
            f"el volcado con {APP_USER_DE_SESION} debía fallar: "
            f"stdout={resultado.stdout!r} stderr={resultado.stderr!r}"
        )
        assert list(carpeta.glob("*.dump")) == [], "no debía quedar ningún .dump"
        assert list(carpeta.glob("*.parcial")) == [], "no debía quedar ningún .parcial"

        lineas = _lineas_json(resultado.stdout + resultado.stderr)
        fallidas = [l for l in lineas if l.get("evento") == "respaldo_fallido"]
        assert fallidas, f"se esperaba respaldo_fallido en el log: {lineas}"
        # L-007: el campo `etapa` (nuestro propio nombre de paso, "pg_dump")
        # es distinto de la SALIDA real de la herramienta ("FATAL: permiso
        # denegado...", el nombre de la tabla que rechazó, etc.) — eso es lo
        # que no tiene que aparecer.
        texto_del_log = json.dumps(fallidas)
        assert "FATAL" not in texto_del_log
        assert "permission denied" not in texto_del_log
        assert "pg_dump: error" not in texto_del_log

        # El chequeo de salud también tiene que quedar en rojo (misma
        # carpeta: sin ningún backup bueno todavía).
        salud, _ = _correr_respaldar_real(
            tmp_path,
            base_del_edificio,
            usuario=APP_USER_DE_SESION,
            password=APP_PASSWORD_DE_SESION,
            args=["--salud"],
            carpeta=carpeta,
        )
        assert salud.returncode != 0, "el chequeo de salud debía fallar sin ningún backup bueno"

    def test_el_rol_correcto_si_puede_volcar(
        self,
        tmp_path: Path,
        base_del_edificio: BaseDeEdificio,
    ) -> None:
        """Triangulación: con las credenciales CORRECTAS (`proptech_respaldo`,
        gemelo del rol de app) el mismo camino sí produce un backup válido —
        así el test de arriba no pasa "porque pg_dump siempre falla", pasa
        porque el ROL es el que decide."""
        from ..conftest import RESPALDO_PASSWORD_DE_SESION, RESPALDO_USER_DE_SESION

        resultado, carpeta = _correr_respaldar_real(
            tmp_path,
            base_del_edificio,
            usuario=RESPALDO_USER_DE_SESION,
            password=RESPALDO_PASSWORD_DE_SESION,
            args=["--una-vez"],
        )

        assert resultado.returncode == 0, (
            f"con el rol correcto el volcado debía andar: "
            f"stdout={resultado.stdout!r} stderr={resultado.stderr!r}"
        )
        dumps = list(carpeta.glob("*.dump"))
        assert len(dumps) == 1, dumps
