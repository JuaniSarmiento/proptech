"""Tests de `infra/respaldos/restaurar.sh` (D9).

Corren el script real con un `docker` falso en el PATH que registra cada
invocación (argumentos y carpeta de trabajo) en un archivo, para verificar
sin Docker real ni Compose que el destino se valida ANTES de tocar la base
(L-004, L-006), que `restaurar.sh` encuentra `infra/` desde cualquier carpeta
y que usa siempre el proyecto `proptech` (L-006).
"""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
SCRIPT = RAIZ / "infra" / "respaldos" / "restaurar.sh"

FAKE_DOCKER_REGISTRA = """
echo "$(pwd)|$*" >> "$REGISTRO_DOCKER"
case "$*" in
  *"printenv POSTGRES_DB"*) echo "proptech_principal" ;;
  *"printenv POSTGRES_USER"*) echo "proptech" ;;
esac
exit 0
"""


def _invocaciones(registro: Path) -> list[tuple[str, str]]:
    if not registro.exists():
        return []
    salida = []
    for linea in registro.read_text().splitlines():
        if not linea.strip():
            continue
        cwd, _, resto = linea.partition("|")
        salida.append((cwd, resto))
    return salida


def _correr(
    tmp_path: Path,
    entorno_con_bin_falso: dict[str, str],
    *,
    destino: str | None = "",
    archivo_backup: Path | None = None,
    cwd: Path | None = None,
    overrides: dict[str, str] | None = None,
    timeout: float = 15,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    entorno = dict(entorno_con_bin_falso)
    registro = tmp_path / "registro-docker.txt"
    entorno["REGISTRO_DOCKER"] = str(registro)
    for clave, valor in (overrides or {}).items():
        entorno[clave] = valor

    if archivo_backup is None:
        archivo_backup = tmp_path / "proptech-20261014T000000Z.dump"
        archivo_backup.write_text("contenido-de-prueba")

    args = [str(archivo_backup)]
    if destino is not None:
        args.append(destino)

    resultado = subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=entorno,
        cwd=str(cwd) if cwd is not None else str(tmp_path),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return resultado, registro


def test_script_existe() -> None:
    assert SCRIPT.exists(), "falta infra/respaldos/restaurar.sh"


DESTINOS_INVALIDOS = [
    "",
    "proptech_",
    "proptech_con espacio",
    "proptech_con\ttab",
    "proptech_con_salto\n",
    "proptech_x;DROP DATABASE proptech",
    "proptech_Restauracion",
    "proptech_" + ("a" * 55),  # 64 caracteres en total, empieza con proptech_
    "sin_el_prefijo",
    "proptech_restauracion" + "٣",  # dígito árabe-índico al final
]


class TestDestinoInvalido:
    @pytest.mark.parametrize("destino", DESTINOS_INVALIDOS)
    def test_rechaza_sin_invocar_docker(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
        destino: str,
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_REGISTRA)

        resultado, registro = _correr(tmp_path, entorno_con_bin_falso, destino=destino)

        assert resultado.returncode != 0, f"destino {destino!r} debía rechazarse"
        assert _invocaciones(registro) == [], (
            f"destino {destino!r}: no debía invocar docker, invocó {_invocaciones(registro)}"
        )

    def test_archivo_inexistente_se_rechaza_sin_invocar_docker(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_REGISTRA)
        no_existe = tmp_path / "no-existe.dump"

        resultado, registro = _correr(
            tmp_path,
            entorno_con_bin_falso,
            archivo_backup=no_existe,
            destino="proptech_restauracion",
        )

        assert resultado.returncode != 0
        assert _invocaciones(registro) == []

    def test_destino_igual_a_la_base_en_uso_rechaza_tras_un_solo_printenv(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_REGISTRA)

        resultado, registro = _correr(
            tmp_path,
            entorno_con_bin_falso,
            destino="proptech_principal",
        )

        assert resultado.returncode != 0
        invocaciones = _invocaciones(registro)
        assert len(invocaciones) == 1, f"se esperaba una sola invocación: {invocaciones}"
        assert "printenv POSTGRES_DB" in invocaciones[0][1]
        assert "dropdb" not in invocaciones[0][1]
        assert "createdb" not in invocaciones[0][1]
        assert "pg_restore" not in invocaciones[0][1]


INFRA_DIR = RAIZ / "infra"
USUARIO_DE_PRUEBA = "usuario_de_prueba_no_real"
MARCADOR_ERROR_CREATEDB = "detalle-de-createdb-secreto"

FAKE_DOCKER_EXITOSO = f"""
echo "$(pwd)|$*" >> "$REGISTRO_DOCKER"
case "$*" in
  *"printenv POSTGRES_DB"*) echo "proptech_principal" ;;
  *"printenv POSTGRES_USER"*) echo "{USUARIO_DE_PRUEBA}" ;;
esac
exit 0
"""

FAKE_DOCKER_FALLA_CREATEDB = f"""
echo "$(pwd)|$*" >> "$REGISTRO_DOCKER"
case "$*" in
  *"printenv POSTGRES_DB"*) echo "proptech_principal"; exit 0 ;;
  *"printenv POSTGRES_USER"*) echo "{USUARIO_DE_PRUEBA}"; exit 0 ;;
  *"createdb"*) echo "{MARCADOR_ERROR_CREATEDB}" >&2; exit 1 ;;
  *) exit 0 ;;
esac
"""


class TestInvocacionConDestinoValido:
    def test_sin_destino_usa_proptech_restauracion(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_EXITOSO)

        resultado, registro = _correr(tmp_path, entorno_con_bin_falso, destino=None)

        assert resultado.returncode == 0, resultado.stderr
        invocaciones = _invocaciones(registro)
        invocaciones_destino = [cmd for _, cmd in invocaciones if "proptech_restauracion" in cmd]
        assert invocaciones_destino, f"ningún comando usó proptech_restauracion: {invocaciones}"

    @pytest.mark.parametrize("cwd_relativo", ["raiz_del_repo", "tmp"])
    def test_toda_invocacion_corre_con_infra_como_carpeta_de_trabajo(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
        cwd_relativo: str,
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_EXITOSO)

        carpeta_desde_donde_se_llama = RAIZ if cwd_relativo == "raiz_del_repo" else tmp_path

        resultado, registro = _correr(
            tmp_path,
            entorno_con_bin_falso,
            destino="proptech_restauracion",
            cwd=carpeta_desde_donde_se_llama,
        )

        assert resultado.returncode == 0, resultado.stderr
        invocaciones = _invocaciones(registro)
        assert invocaciones, "no se registró ninguna invocación de docker"
        for cwd_invocacion, _ in invocaciones:
            assert cwd_invocacion == str(INFRA_DIR), (
                f"invocación corrió en {cwd_invocacion!r}, se esperaba {INFRA_DIR}"
            )

    def test_pasa_usuario_de_la_base_a_dropdb_createdb_y_pg_restore(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_EXITOSO)

        resultado, registro = _correr(
            tmp_path, entorno_con_bin_falso, destino="proptech_restauracion"
        )

        assert resultado.returncode == 0, resultado.stderr
        invocaciones = [cmd for _, cmd in _invocaciones(registro)]

        def _tiene_herramienta(nombre: str) -> str:
            coincidencias = [cmd for cmd in invocaciones if nombre in cmd]
            assert coincidencias, f"no se invocó {nombre}: {invocaciones}"
            return coincidencias[0]

        for herramienta in ("dropdb", "createdb", "pg_restore"):
            comando = _tiene_herramienta(herramienta)
            assert f"-U {USUARIO_DE_PRUEBA}" in comando, (
                f"{herramienta} no recibió -U {USUARIO_DE_PRUEBA}: {comando!r}"
            )

    def test_invoca_exec_dropdb_createdb_pg_restore_sin_sh_c(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_EXITOSO)

        resultado, registro = _correr(
            tmp_path, entorno_con_bin_falso, destino="proptech_restauracion"
        )

        assert resultado.returncode == 0, resultado.stderr
        invocaciones = [cmd for _, cmd in _invocaciones(registro)]

        comando_dropdb = next(c for c in invocaciones if "dropdb" in c)
        comando_createdb = next(c for c in invocaciones if "createdb" in c and "dropdb" not in c)
        comando_pg_restore = next(c for c in invocaciones if "pg_restore" in c)

        assert "compose -p proptech exec -T db" in comando_dropdb
        assert "--if-exists" in comando_dropdb
        assert "proptech_restauracion" in comando_dropdb

        assert "compose -p proptech exec -T db" in comando_createdb
        assert "proptech_restauracion" in comando_createdb

        assert "compose -p proptech exec -T db" in comando_pg_restore
        assert "--no-owner" in comando_pg_restore

        for comando in (comando_dropdb, comando_createdb, comando_pg_restore):
            assert "sh -c" not in comando, f"no debía pasar por sh -c: {comando!r}"

    def test_proyecto_compose_aislado_por_variable(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        # Vuelta 2 del 4a: el ensayo aislado restaura en SU proyecto, nunca en `proptech`.
        escribir_herramienta_falsa("docker", FAKE_DOCKER_EXITOSO)

        resultado, registro = _correr(
            tmp_path,
            entorno_con_bin_falso,
            destino="proptech_restauracion",
            overrides={"PROPTECH_COMPOSE_PROYECTO": "proptech-ensayo-x"},
        )

        assert resultado.returncode == 0, resultado.stderr
        invocaciones = [cmd for _, cmd in _invocaciones(registro)]
        assert invocaciones
        assert all(c.startswith("compose -p proptech-ensayo-x ") for c in invocaciones), (
            invocaciones
        )

    def test_falla_de_createdb_nombra_el_paso_y_no_sigue_a_pg_restore(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_FALLA_CREATEDB)

        resultado, registro = _correr(
            tmp_path, entorno_con_bin_falso, destino="proptech_restauracion"
        )

        assert resultado.returncode != 0
        assert "createdb" in resultado.stderr
        assert resultado.stderr.count(MARCADOR_ERROR_CREATEDB) == 0
        invocaciones = [cmd for _, cmd in _invocaciones(registro)]
        assert not any("pg_restore" in cmd for cmd in invocaciones), (
            f"no debía invocar pg_restore tras la falla de createdb: {invocaciones}"
        )
