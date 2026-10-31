"""Tests de `infra/respaldos/conmutar.sh` (D6): conmuta la aplicación
(`POSTGRES_DB` en `infra/.env`) a una base ya restaurada, con tres
verificaciones previas (existe, revisión de Alembic, RLS/políticas) antes de
tocar nada. Corren el script real con un `docker` falso en el PATH que
registra cada invocación (L-004, L-006), igual que `test_restaurar.py`.
"""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
SCRIPT = RAIZ / "infra" / "respaldos" / "conmutar.sh"
INFRA_DIR = RAIZ / "infra"

USUARIO_DE_PRUEBA = "usuario_de_prueba_no_real"
CABEZA_DE_PRUEBA = "0032"


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
    destino: str | None = "proptech_restaurada",
    cwd: Path | None = None,
    overrides: dict[str, str] | None = None,
    timeout: float = 15,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    entorno = dict(entorno_con_bin_falso)
    registro = tmp_path / "registro-docker.txt"
    entorno["REGISTRO_DOCKER"] = str(registro)
    # SIEMPRE una carpeta de prueba, NUNCA el infra/ real del checkout: si
    # el script llega a reescribir `.env`, tiene que ser el de ACÁ (hallazgo
    # real, ver tasks.md 8.3 — dos corridas sin esto dejaron el
    # `infra/.env` real del repo con `POSTGRES_DB=proptech_restaurada`).
    carpeta_infra_de_prueba = tmp_path / "infra-de-prueba"
    carpeta_infra_de_prueba.mkdir(exist_ok=True)
    env_de_prueba = carpeta_infra_de_prueba / ".env"
    if not env_de_prueba.exists():
        env_de_prueba.write_text(
            "POSTGRES_DB=proptech_principal\nPOSTGRES_USER=usuario_de_prueba_no_real\n"
            "OTRA_VARIABLE=no_se_toca\n"
        )
    entorno["CONMUTAR_INFRA_DIR"] = str(carpeta_infra_de_prueba)
    for clave, valor in (overrides or {}).items():
        entorno[clave] = valor

    args = [destino] if destino is not None else []
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
    assert SCRIPT.exists(), "falta infra/respaldos/conmutar.sh"


FAKE_DOCKER_REGISTRA = """
echo "$(pwd)|$*" >> "$REGISTRO_DOCKER"
case "$*" in
  *"printenv POSTGRES_DB"*) echo "proptech_principal" ;;
  *"printenv POSTGRES_USER"*) echo "usuario_de_prueba_no_real" ;;
esac
exit 0
"""

DESTINOS_INVALIDOS = [
    "",
    "proptech_",
    "proptech_con espacio",
    "proptech_con\ttab",
    "proptech_con_salto\n",
    "proptech_x;DROP DATABASE proptech",
    "proptech_Restauracion",
    "proptech_" + ("a" * 55),
    "sin_el_prefijo",
    "proptech_restaurada" + "٣",
]


class TestValidacionDelDestino:
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
            f"destino {destino!r}: no debía invocar docker: {_invocaciones(registro)}"
        )

    def test_destino_igual_a_la_base_en_uso_rechaza_tras_un_solo_printenv(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_REGISTRA)

        resultado, registro = _correr(
            tmp_path, entorno_con_bin_falso, destino="proptech_principal"
        )

        assert resultado.returncode != 0
        invocaciones = _invocaciones(registro)
        assert len(invocaciones) == 1, f"se esperaba una sola invocación: {invocaciones}"
        assert "printenv POSTGRES_DB" in invocaciones[0][1]


def _fake_docker_con_verificaciones(
    *,
    existe: bool = True,
    revision: str | None = CABEZA_DE_PRUEBA,
    politicas_destino: str = "t1|t|p1|cmd|q|wc",
    politicas_base: str = "t1|t|p1|cmd|q|wc",
) -> str:
    revision_linea = f'echo "{revision}"' if revision is not None else "true"
    existencia = "exit 0" if existe else "exit 1"
    return f"""
echo "$(pwd)|$*" >> "$REGISTRO_DOCKER"
case "$*" in
  *"printenv POSTGRES_DB"*) echo "proptech_principal"; exit 0 ;;
  *"printenv POSTGRES_USER"*) echo "{USUARIO_DE_PRUEBA}"; exit 0 ;;
  *"alembic heads"*) echo "{CABEZA_DE_PRUEBA} (head)"; exit 0 ;;
  *"SELECT version_num"*) {revision_linea}; exit 0 ;;
  *proptech_restaurada*"SELECT 1"*) {existencia} ;;
  *"SELECT 1"*) exit 0 ;;
  *proptech_restaurada*"pg_class"*) echo "{politicas_destino}"; exit 0 ;;
  *"pg_class"*) echo "{politicas_base}"; exit 0 ;;
  *) exit 0 ;;
esac
"""


class TestLasTresVerificaciones:
    def test_destino_inexistente_rechaza_antes_de_tocar_la_aplicacion(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", _fake_docker_con_verificaciones(existe=False))

        resultado, registro = _correr(tmp_path, entorno_con_bin_falso)

        assert resultado.returncode != 0
        invocaciones = [c for _, c in _invocaciones(registro)]
        assert not any("alembic" in c for c in invocaciones), (
            "no debía llegar a la verificación de migraciones: " f"{invocaciones}"
        )

    def test_revision_de_migraciones_equivocada_rechaza(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa(
            "docker", _fake_docker_con_verificaciones(revision="0001")
        )

        resultado, registro = _correr(tmp_path, entorno_con_bin_falso)

        assert resultado.returncode != 0
        assert "migraciones" in resultado.stderr.lower()
        invocaciones = [c for _, c in _invocaciones(registro)]
        assert not any("pg_class" in c for c in invocaciones), (
            "no debía llegar a la verificación de RLS: " f"{invocaciones}"
        )

    def test_sin_revision_en_la_base_destino_rechaza(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa(
            "docker", _fake_docker_con_verificaciones(revision=None)
        )

        resultado, registro = _correr(tmp_path, entorno_con_bin_falso)

        assert resultado.returncode != 0

    def test_politicas_distintas_entre_destino_y_base_en_uso_rechaza(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa(
            "docker",
            _fake_docker_con_verificaciones(
                politicas_base="t1|t|p1|cmd|q|wc",
                politicas_destino="t1|f|p1|cmd|q|wc",  # forcerowsecurity distinta
            ),
        )

        resultado, registro = _correr(tmp_path, entorno_con_bin_falso)

        assert resultado.returncode != 0
        assert "seguridad" in resultado.stderr.lower() or "rls" in resultado.stderr.lower()

    def test_las_tres_verificaciones_pasando_no_rechaza_por_si_solas(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        """No verifica la conmutación en sí (eso es 8.3/8.4): sólo que pasar
        las tres verificaciones no termina en un error DE LAS TRES."""
        escribir_herramienta_falsa("docker", _fake_docker_con_verificaciones())

        resultado, registro = _correr(tmp_path, entorno_con_bin_falso)

        invocaciones = [c for _, c in _invocaciones(registro)]
        assert any("alembic heads" in c for c in invocaciones)
        assert any("SELECT version_num" in c for c in invocaciones)
        assert any("pg_class" in c for c in invocaciones)


FAKE_DOCKER_CONMUTACION_EXITOSA = f"""
echo "$(pwd)|$*" >> "$REGISTRO_DOCKER"
case "$*" in
  *"printenv POSTGRES_DB"*) echo "proptech_principal"; exit 0 ;;
  *"printenv POSTGRES_USER"*) echo "{USUARIO_DE_PRUEBA}"; exit 0 ;;
  *"alembic heads"*) echo "{CABEZA_DE_PRUEBA} (head)"; exit 0 ;;
  *"SELECT version_num"*) echo "{CABEZA_DE_PRUEBA}"; exit 0 ;;
  *"SELECT 1"*) exit 0 ;;
  *"pg_class"*) echo "t1|t|p1|cmd|q|wc"; exit 0 ;;
  *"compose up"*) exit 0 ;;
  *"exec -T api python"*) exit 0 ;;
  *) exit 0 ;;
esac
"""

MARCADOR_ERROR_HERRAMIENTA = "detalle-secreto-de-la-herramienta-xyz"

FAKE_DOCKER_FALLA_AL_LEVANTAR = f"""
echo "$(pwd)|$*" >> "$REGISTRO_DOCKER"
case "$*" in
  *"printenv POSTGRES_DB"*) echo "proptech_principal"; exit 0 ;;
  *"printenv POSTGRES_USER"*) echo "{USUARIO_DE_PRUEBA}"; exit 0 ;;
  *"alembic heads"*) echo "{CABEZA_DE_PRUEBA} (head)"; exit 0 ;;
  *"SELECT version_num"*) echo "{CABEZA_DE_PRUEBA}"; exit 0 ;;
  *"SELECT 1"*) exit 0 ;;
  *"pg_class"*) echo "t1|t|p1|cmd|q|wc"; exit 0 ;;
  *compose*up*) echo "{MARCADOR_ERROR_HERRAMIENTA}" >&2; exit 1 ;;
  *) exit 0 ;;
esac
"""


class TestLaConmutacionEnSi:
    def test_env_queda_con_el_destino_y_las_demas_lineas_intactas(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_CONMUTACION_EXITOSA)

        resultado, registro = _correr(tmp_path, entorno_con_bin_falso)

        assert resultado.returncode == 0, resultado.stderr
        env_de_prueba = tmp_path / "infra-de-prueba" / ".env"
        contenido = env_de_prueba.read_text()
        assert "POSTGRES_DB=proptech_restaurada" in contenido
        assert "POSTGRES_USER=usuario_de_prueba_no_real" in contenido
        assert "OTRA_VARIABLE=no_se_toca" in contenido

    def test_env_anterior_guarda_el_valor_previo(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_CONMUTACION_EXITOSA)

        resultado, registro = _correr(tmp_path, entorno_con_bin_falso)

        assert resultado.returncode == 0, resultado.stderr
        anterior = tmp_path / "infra-de-prueba" / ".env.anterior"
        assert anterior.exists(), "faltó el resguardo .env.anterior"
        assert "POSTGRES_DB=proptech_principal" in anterior.read_text()

    def test_falla_al_levantar_no_repite_el_marcador_de_la_herramienta(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", FAKE_DOCKER_FALLA_AL_LEVANTAR)

        resultado, registro = _correr(tmp_path, entorno_con_bin_falso)

        assert resultado.returncode != 0
        assert MARCADOR_ERROR_HERRAMIENTA not in resultado.stderr
        assert "compose" in resultado.stderr.lower() or "levantar" in resultado.stderr.lower()
        # El .env YA quedó con el destino nuevo (la escritura es anterior al
        # intento de levantar) y el anterior sigue disponible para volver.
        anterior = tmp_path / "infra-de-prueba" / ".env.anterior"
        assert anterior.exists()


class TestProyectoComposeAislado:
    def test_usa_la_variable_del_proyecto(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("docker", _fake_docker_con_verificaciones(existe=False))

        resultado, registro = _correr(
            tmp_path,
            entorno_con_bin_falso,
            overrides={"PROPTECH_COMPOSE_PROYECTO": "proptech-ensayo-x"},
        )

        invocaciones = [c for _, c in _invocaciones(registro)]
        assert invocaciones
        assert all(c.startswith("compose -p proptech-ensayo-x ") for c in invocaciones), (
            invocaciones
        )
