"""Tests de `infra/respaldos/respaldar.sh` (D9).

Corren el script real con `pg_dump`, `pg_restore`, `id` y `date` falsos en el
PATH (L-004) y una carpeta temporal como `RESPALDO_CARPETA` (la ruta interna
que en Compose es el punto de montaje `/respaldos`; estos tests la pisan para
no depender de Docker). Todo entero externo se prueba con la batería completa
de L-008 (`fullmatch`, sólo ASCII) y ninguna salida de herramienta externa
debe llegar al log (L-007): por eso `PGPASSWORD` se fija a un marcador que
ningún test debería encontrar en la salida combinada del proceso.
"""

import json
import os
import re
import signal
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

PATRON_NOMBRE_BACKUP = re.compile(r"^proptech-[0-9]{8}T[0-9]{6}Z\.dump$")

FAKE_PG_DUMP_OK = """
archivo=""
for arg in "$@"; do
  case "$arg" in
    --file=*) archivo="${arg#--file=}" ;;
  esac
done
echo "contenido-dump-de-prueba" > "$archivo"
exit 0
"""

FAKE_PG_RESTORE_OK = """
exit 0
"""


def _lineas_json(texto: str) -> list[dict[str, object]]:
    lineas = [linea for linea in texto.splitlines() if linea.strip()]
    return [json.loads(linea) for linea in lineas]


RAIZ = Path(__file__).resolve().parents[3]
SCRIPT = RAIZ / "infra" / "respaldos" / "respaldar.sh"

MARCADOR_CONTRASENA = "marcador-pgpassword-no-real-9f3c21"

ENV_BASE_VALIDO = {
    "RESPALDO_INTERVALO_SEGUNDOS": "3600",
    "RESPALDO_CONSERVAR": "14",
    "RESPALDO_LIMITE_SEGUNDOS": "1800",
}


def _correr(
    tmp_path: Path,
    entorno_con_bin_falso: dict[str, str],
    *,
    carpeta: Path | None = None,
    crear_carpeta: bool = True,
    overrides: dict[str, str | None] | None = None,
    args: list[str] | None = None,
    timeout: float = 15,
) -> subprocess.CompletedProcess[str]:
    entorno = dict(entorno_con_bin_falso)
    entorno.update(ENV_BASE_VALIDO)
    entorno["PGPASSWORD"] = MARCADOR_CONTRASENA

    carpeta_respaldos = carpeta if carpeta is not None else (tmp_path / "respaldos")
    if crear_carpeta:
        carpeta_respaldos.mkdir(parents=True, exist_ok=True)
    entorno["RESPALDO_CARPETA"] = str(carpeta_respaldos)

    for clave, valor in (overrides or {}).items():
        if valor is None:
            entorno.pop(clave, None)
        else:
            entorno[clave] = valor

    return subprocess.run(
        ["bash", str(SCRIPT), *(args or ["--una-vez"])],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _salida_combinada(resultado: subprocess.CompletedProcess[str]) -> str:
    return resultado.stdout + resultado.stderr


VALORES_INTERVALO_INVALIDO: list[str | None] = [
    None,  # faltante
    "",
    " ",
    "\t",
    "abc",
    "0",
    "59",
    "604801",
    "060",
    "+60",
    " 60",
    "60 ",
    "\t60",
    "60\t",
    "\n60",
    "60\n",
    "٦٠",  # dígitos árabe-índicos (60 en ese alfabeto)
]


def test_script_existe() -> None:
    assert SCRIPT.exists(), "falta infra/respaldos/respaldar.sh"


class TestIntervaloInvalido:
    def test_cada_valor_invalido_rechaza_nombrando_la_variable(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
    ) -> None:
        for valor in VALORES_INTERVALO_INVALIDO:
            resultado = _correr(
                tmp_path,
                entorno_con_bin_falso,
                overrides={"RESPALDO_INTERVALO_SEGUNDOS": valor},
            )
            assert resultado.returncode != 0, f"valor {valor!r} debería rechazarse"
            assert "RESPALDO_INTERVALO_SEGUNDOS" in resultado.stderr, (
                f"valor {valor!r}: stderr={resultado.stderr!r}"
            )
            assert MARCADOR_CONTRASENA not in _salida_combinada(resultado)


VALORES_CONSERVAR_INVALIDO: list[str | None] = [
    "0",
    "366",
    "abc",
    "",
    "١٤",  # dígitos árabe-índicos (14)
]


class TestRetencionInvalida:
    def test_cada_valor_invalido_rechaza_nombrando_la_variable(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
    ) -> None:
        for valor in VALORES_CONSERVAR_INVALIDO:
            resultado = _correr(
                tmp_path,
                entorno_con_bin_falso,
                overrides={"RESPALDO_CONSERVAR": valor},
            )
            assert resultado.returncode != 0, f"valor {valor!r} debería rechazarse"
            assert "RESPALDO_CONSERVAR" in resultado.stderr
            assert MARCADOR_CONTRASENA not in _salida_combinada(resultado)


class TestLimiteInvalido:
    @pytest.mark.parametrize("valor", ["4", "86401", "abc"])
    def test_valor_fuera_de_rango_o_no_entero(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        valor: str,
    ) -> None:
        resultado = _correr(
            tmp_path,
            entorno_con_bin_falso,
            overrides={"RESPALDO_LIMITE_SEGUNDOS": valor},
        )
        assert resultado.returncode != 0
        assert "RESPALDO_LIMITE_SEGUNDOS" in resultado.stderr
        assert MARCADOR_CONTRASENA not in _salida_combinada(resultado)

    def test_limite_igual_al_intervalo_se_rechaza(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
    ) -> None:
        resultado = _correr(
            tmp_path,
            entorno_con_bin_falso,
            overrides={
                "RESPALDO_INTERVALO_SEGUNDOS": "3600",
                "RESPALDO_LIMITE_SEGUNDOS": "3600",
            },
        )
        assert resultado.returncode != 0
        assert "RESPALDO_LIMITE_SEGUNDOS" in resultado.stderr


class TestCarpeta:
    def test_carpeta_inexistente(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
    ) -> None:
        resultado = _correr(
            tmp_path,
            entorno_con_bin_falso,
            carpeta=tmp_path / "no-existe",
            crear_carpeta=False,
        )
        assert resultado.returncode != 0
        assert "no-existe" in resultado.stderr
        assert MARCADOR_CONTRASENA not in _salida_combinada(resultado)

    def test_carpeta_sin_permiso_de_escritura(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
    ) -> None:
        carpeta = tmp_path / "sin-permiso"
        carpeta.mkdir()
        carpeta.chmod(0o500)
        try:
            resultado = _correr(
                tmp_path,
                entorno_con_bin_falso,
                carpeta=carpeta,
                crear_carpeta=False,
            )
            assert resultado.returncode != 0
            assert "sin-permiso" in resultado.stderr
            assert MARCADOR_CONTRASENA not in _salida_combinada(resultado)
            assert list(carpeta.iterdir()) == []
        finally:
            carpeta.chmod(0o700)


class TestCorreComoRoot:
    def test_termina_antes_de_invocar_pg_dump_o_escribir(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("id", "echo 0\n")
        marcador_invocado = tmp_path / "pg_dump_invocado"
        escribir_herramienta_falsa(
            "pg_dump",
            f'touch "{marcador_invocado}"\nexit 0\n',
        )

        resultado = _correr(tmp_path, entorno_con_bin_falso)

        assert resultado.returncode != 0
        assert "PROPTECH_UID" in resultado.stderr
        assert not marcador_invocado.exists(), "no debía invocar pg_dump"
        carpeta = tmp_path / "respaldos"
        assert list(carpeta.iterdir()) == [], "no debía escribir nada en la carpeta"


class TestCicloExitoso:
    def test_genera_backup_con_nombre_y_permisos_correctos(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_OK)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)

        resultado = _correr(tmp_path, entorno_con_bin_falso)

        assert resultado.returncode == 0, resultado.stderr
        carpeta = tmp_path / "respaldos"
        archivos = list(carpeta.iterdir())
        parciales = [a for a in archivos if a.name.endswith(".parcial")]
        dumps = [a for a in archivos if a.name.endswith(".dump")]

        assert parciales == [], f"no debía quedar ningún .parcial: {parciales}"
        assert len(dumps) == 1, f"se esperaba un solo .dump: {dumps}"
        assert PATRON_NOMBRE_BACKUP.match(dumps[0].name), dumps[0].name

        permisos = stat.S_IMODE(dumps[0].stat().st_mode)
        assert permisos == 0o600, oct(permisos)

        marca = carpeta / ".ultimo-ok"
        assert marca.exists()
        assert marca.read_text().strip().isdigit()

        lineas = _lineas_json(resultado.stdout)
        assert lineas, "se esperaba al menos una línea de log JSON"
        for linea in lineas:
            assert set(linea) >= {"ts", "nivel", "servicio", "evento"}
            assert linea["servicio"] == "respaldos"

    def test_parcial_huerfano_se_borra_al_arrancar(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_OK)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        huerfano = carpeta / "proptech-20200101T000000Z.dump.parcial"
        huerfano.write_text("restos de un ciclo anterior")

        resultado = _correr(tmp_path, entorno_con_bin_falso, carpeta=carpeta)

        assert resultado.returncode == 0, resultado.stderr
        assert not huerfano.exists(), "el .parcial huérfano debía borrarse al arrancar"


FAKE_PG_DUMP_FALLA = """
exit 1
"""

FAKE_PG_RESTORE_FALLA = """
exit 1
"""

MARCADOR_ERROR_PG_DUMP = "detalle-de-la-tabla-secreta-xyz"

FAKE_PG_DUMP_FALLA_CON_MARCADOR = f"""
echo "{MARCADOR_ERROR_PG_DUMP}" >&2
exit 1
"""

FAKE_PG_DUMP_LENTO = """
archivo=""
for arg in "$@"; do
  case "$arg" in
    --file=*) archivo="${arg#--file=}" ;;
  esac
done
sleep 1
echo "contenido-lento" > "$archivo"
exit 0
"""

FAKE_PG_DUMP_SE_CUELGA = """
echo $$ > "$ARCHIVO_PID_CUELGA"
trap '' TERM
sleep 60
"""


class TestFallasDelCiclo:
    def test_falla_el_volcado_no_deja_archivos_y_loguea_error(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_FALLA)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)

        resultado = _correr(tmp_path, entorno_con_bin_falso)

        carpeta = tmp_path / "respaldos"
        assert list(carpeta.glob("*.dump")) == []
        assert list(carpeta.glob("*.parcial")) == []
        lineas = _lineas_json(resultado.stdout)
        fallidas = [linea for linea in lineas if linea["evento"] == "respaldo_fallido"]
        assert fallidas, f"se esperaba respaldo_fallido en: {lineas}"
        assert fallidas[0]["nivel"] == "error"

    def test_falla_pg_restore_list_no_deja_archivos_y_loguea_error(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_OK)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_FALLA)

        resultado = _correr(tmp_path, entorno_con_bin_falso)

        carpeta = tmp_path / "respaldos"
        assert list(carpeta.glob("*.dump")) == []
        assert list(carpeta.glob("*.parcial")) == []
        lineas = _lineas_json(resultado.stdout)
        fallidas = [linea for linea in lineas if linea["evento"] == "respaldo_fallido"]
        assert fallidas
        assert fallidas[0]["nivel"] == "error"

    def test_marcador_del_error_de_pg_dump_no_llega_al_log(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_FALLA_CON_MARCADOR)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)

        resultado = _correr(tmp_path, entorno_con_bin_falso)

        assert MARCADOR_ERROR_PG_DUMP not in _salida_combinada(resultado)

    def test_base_que_no_responde_se_corta_y_el_proceso_muere(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_SE_CUELGA)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)

        archivo_pid = tmp_path / "pid-cuelga"

        import time

        inicio = time.monotonic()
        resultado = _correr(
            tmp_path,
            entorno_con_bin_falso,
            overrides={
                "RESPALDO_LIMITE_SEGUNDOS": "5",
                "ARCHIVO_PID_CUELGA": str(archivo_pid),
            },
            timeout=20,
        )
        duracion = time.monotonic() - inicio

        assert duracion < 11, f"tardó {duracion}s en cortar"
        carpeta = tmp_path / "respaldos"
        assert list(carpeta.glob("*.dump")) == []
        assert list(carpeta.glob("*.parcial")) == []

        assert archivo_pid.exists(), "el pg_dump falso no llegó a escribir su PID"
        pid = int(archivo_pid.read_text().strip())
        import os as _os
        import signal as _signal

        with pytest.raises(ProcessLookupError):
            _os.kill(pid, _signal.SIG_DFL)  # sólo para comprobar que ya no existe

        lineas = _lineas_json(resultado.stdout)
        fallidas = [linea for linea in lineas if linea["evento"] == "respaldo_fallido"]
        assert fallidas

    def test_base_lenta_dentro_del_limite_completa(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_LENTO)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)

        resultado = _correr(
            tmp_path,
            entorno_con_bin_falso,
            overrides={"RESPALDO_LIMITE_SEGUNDOS": "10"},
            timeout=20,
        )

        assert resultado.returncode == 0, resultado.stderr
        carpeta = tmp_path / "respaldos"
        assert len(list(carpeta.glob("*.dump"))) == 1

    def test_modo_continuo_sigue_vivo_despues_de_una_falla(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_FALLA)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)

        entorno = dict(entorno_con_bin_falso)
        entorno.update(ENV_BASE_VALIDO)
        entorno["PGPASSWORD"] = MARCADOR_CONTRASENA
        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        entorno["RESPALDO_CARPETA"] = str(carpeta)

        proceso = subprocess.Popen(
            ["bash", str(SCRIPT)],
            env=entorno,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            import time

            time.sleep(2)
            assert proceso.poll() is None, "el proceso debía seguir vivo tras la falla"
        finally:
            proceso.terminate()
            try:
                proceso.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait(timeout=5)


FAKE_MV_FALLA = """
exit 1
"""

FAKE_DATE_FALLA_AL_ESCRIBIR_LA_MARCA = """
case "$*" in
  *'+%s') exit 1 ;;
  *) /usr/bin/date "$@" ;;
esac
"""

FAKE_RM_FALLA = """
exit 1
"""

ENTORNO_CONTINUO = {"RESPALDO_INTERVALO_SEGUNDOS": "60", "RESPALDO_LIMITE_SEGUNDOS": "5"}


def _correr_continuo(
    tmp_path: Path,
    entorno_con_bin_falso: dict[str, str],
    *,
    carpeta: Path,
    overrides: dict[str, str] | None = None,
) -> subprocess.Popen[str]:
    """Modo continuo real (sin `--una-vez`): el mismo binario que corre en
    producción, con `ciclo_backup || true` (B2, L-014)."""
    entorno = dict(entorno_con_bin_falso)
    entorno.update(ENV_BASE_VALIDO)
    entorno.update(ENTORNO_CONTINUO)
    entorno["PGPASSWORD"] = MARCADOR_CONTRASENA
    entorno["RESPALDO_CARPETA"] = str(carpeta)
    entorno.update(overrides or {})

    return subprocess.Popen(
        ["bash", str(SCRIPT)],
        env=entorno,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,  # grupo propio: ver _matar.
    )


def _matar(proceso: subprocess.Popen[str]) -> str:
    """Mata TODO el grupo de procesos, no sólo el bash de PID 1 (F5: bash
    ignora SIGTERM como PID 1, así que un `terminate()` a secas no lo corta,
    y `communicate()` además necesita que el `sleep` del modo continuo,
    hijo del bash, también suelte el extremo de escritura del pipe de
    stdout para devolver EOF; de otro modo `communicate()` cuelga esperando
    un EOF que nunca llega)."""
    os.killpg(proceso.pid, signal.SIGKILL)
    return proceso.communicate(timeout=5)[0]


class TestModoContinuoNoDeclaraExitoSiFallaUnPasoPosterior:
    """B2 (auditor, vuelta 2, F2/L-014): en bash, una función llamada como
    operando izquierdo de `||` (así corre `ciclo_backup` en modo continuo,
    el modo real de producción) corre con `set -e` DESACTIVADO en todo su
    cuerpo. Los pasos con `if !` explícito (`pg_dump`, `pg_restore --list`)
    ya se manejaban bien; `mv`, la escritura de `.ultimo-ok` y la retención
    confiaban en `set -e` y no. Si cualquiera de los tres falla DESPUÉS de
    `pg_restore --list`, el ciclo no puede loguear `respaldo_generado` (la
    spec: "no saludable si todavía no generó ninguno")."""

    def test_falla_el_mv_no_declara_exito(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_OK)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)
        escribir_herramienta_falsa("mv", FAKE_MV_FALLA)

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        proceso = _correr_continuo(tmp_path, entorno_con_bin_falso, carpeta=carpeta)
        try:
            import time

            time.sleep(2)
        finally:
            salida = _matar(proceso)

        assert "respaldo_generado" not in salida, salida
        lineas = _lineas_json(salida)
        fallidas = [linea for linea in lineas if linea.get("evento") == "respaldo_fallido"]
        assert fallidas, salida
        assert list(carpeta.glob("*.dump")) == []
        salud = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert salud.returncode != 0, "salud OK sin ningún backup en la carpeta"

    def test_falla_la_escritura_de_ultimo_ok_no_declara_exito(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_OK)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)
        escribir_herramienta_falsa("date", FAKE_DATE_FALLA_AL_ESCRIBIR_LA_MARCA)

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        proceso = _correr_continuo(tmp_path, entorno_con_bin_falso, carpeta=carpeta)
        try:
            import time

            time.sleep(2)
        finally:
            salida = _matar(proceso)

        assert "respaldo_generado" not in salida, salida
        lineas = _lineas_json(salida)
        fallidas = [linea for linea in lineas if linea.get("evento") == "respaldo_fallido"]
        assert fallidas, salida
        salud = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert salud.returncode != 0, "salud OK sin una marca válida"

    def test_falla_la_retencion_no_declara_exito(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_OK)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)
        escribir_herramienta_falsa("rm", FAKE_RM_FALLA)

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        # Con RESPALDO_CONSERVAR=1 y un backup viejo ya en la carpeta, el
        # ciclo que genera uno nuevo tiene que borrar el viejo: ahí es donde
        # el `rm` falso falla.
        _crear_backups(carpeta, ["proptech-20200101T000000Z.dump"])
        proceso = _correr_continuo(
            tmp_path,
            entorno_con_bin_falso,
            carpeta=carpeta,
            overrides={"RESPALDO_CONSERVAR": "1"},
        )
        try:
            import time

            time.sleep(2)
        finally:
            salida = _matar(proceso)

        assert "respaldo_generado" not in salida, salida
        lineas = _lineas_json(salida)
        fallidas = [linea for linea in lineas if linea.get("evento") == "respaldo_fallido"]
        assert fallidas, salida


def _crear_backups(carpeta: Path, nombres: list[str]) -> None:
    for nombre in nombres:
        (carpeta / nombre).write_text("contenido-de-prueba-retencion")


def _archivos_dump(carpeta: Path) -> list[str]:
    """Sólo los nombres que cumplen el patrón COMPLETO de un backup (L-008):
    un glob `*.dump` a secas también toma `proptech-copia-a-mano.dump`, que
    el escenario "Se supera la retención" exige dejar intacto."""
    return sorted(p.name for p in carpeta.glob("*.dump") if PATRON_NOMBRE_BACKUP.match(p.name))


FAKE_DATE_RELOJ_ATRASADO = """
case "$*" in
  *'+%Y%m%dT%H%M%SZ') echo "20261001T000000Z" ;;
  *'+%Y-%m-%dT%H:%M:%SZ') echo "2026-10-01T00:00:00Z" ;;
  *'+%s') echo "1759276800" ;;
  *) /usr/bin/date "$@" ;;
esac
"""


class TestRetencion:
    def test_se_supera_la_retencion_borra_el_mas_viejo(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_OK)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        nombres_viejos = [f"proptech-202610{(dia):02d}T000000Z.dump" for dia in range(1, 15)]
        _crear_backups(carpeta, nombres_viejos)
        archivo_ajeno = carpeta / "archivo-ajeno.txt"
        archivo_ajeno.write_text("no es un backup")
        copia_a_mano = carpeta / "proptech-copia-a-mano.dump"
        copia_a_mano.write_text("copia manual, no sigue el patrón")
        backup_bak = carpeta / "proptech-20261013T000000Z.dump.bak"
        backup_bak.write_text("un .bak no es un .dump")

        resultado = _correr(
            tmp_path,
            entorno_con_bin_falso,
            carpeta=carpeta,
            overrides={"RESPALDO_CONSERVAR": "14"},
        )

        assert resultado.returncode == 0, resultado.stderr
        dumps = _archivos_dump(carpeta)
        assert len(dumps) == 14, dumps
        assert "proptech-20261001T000000Z.dump" not in dumps, "el más viejo debía borrarse"
        assert archivo_ajeno.exists()
        assert copia_a_mano.exists()
        assert backup_bak.exists()

    def test_un_backup_fallido_no_borra_nada(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_FALLA)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        nombres_viejos = [f"proptech-202610{(dia):02d}T000000Z.dump" for dia in range(1, 15)]
        _crear_backups(carpeta, nombres_viejos)

        _correr(
            tmp_path,
            entorno_con_bin_falso,
            carpeta=carpeta,
            overrides={"RESPALDO_CONSERVAR": "14"},
        )

        assert _archivos_dump(carpeta) == sorted(nombres_viejos)

    def test_conservar_uno_deja_solo_el_nuevo(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_OK)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        nombres_viejos = [f"proptech-202610{(dia):02d}T000000Z.dump" for dia in range(1, 15)]
        _crear_backups(carpeta, nombres_viejos)

        resultado = _correr(
            tmp_path,
            entorno_con_bin_falso,
            carpeta=carpeta,
            overrides={"RESPALDO_CONSERVAR": "1"},
        )

        assert resultado.returncode == 0, resultado.stderr
        dumps = _archivos_dump(carpeta)
        assert len(dumps) == 1, dumps
        for nombre_viejo in nombres_viejos:
            assert nombre_viejo not in dumps

    def test_reloj_atrasado_no_borra_el_backup_nuevo(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_OK)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)
        escribir_herramienta_falsa("date", FAKE_DATE_RELOJ_ATRASADO)

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        nombres_recientes = [f"proptech-20261020T{hora:02d}0000Z.dump" for hora in range(14)]
        _crear_backups(carpeta, nombres_recientes)

        resultado = _correr(
            tmp_path,
            entorno_con_bin_falso,
            carpeta=carpeta,
            overrides={"RESPALDO_CONSERVAR": "14"},
        )

        assert resultado.returncode == 0, resultado.stderr
        dumps = _archivos_dump(carpeta)
        assert "proptech-20261001T000000Z.dump" in dumps, (
            "el backup nuevo (que ordena como el más viejo) no debía borrarse"
        )
        assert len(dumps) == 14, dumps
        assert "proptech-20261020T000000Z.dump" not in dumps, (
            "debía borrarse el más viejo de los anteriores"
        )


def _correr_salud(
    tmp_path: Path,
    entorno_con_bin_falso: dict[str, str],
    carpeta: Path,
    *,
    overrides: dict[str, str | None] | None = None,
) -> subprocess.CompletedProcess[str]:
    return _correr(
        tmp_path,
        entorno_con_bin_falso,
        carpeta=carpeta,
        crear_carpeta=False,
        overrides=overrides,
        args=["--salud"],
    )


class TestSalud:
    def test_falla_sin_ultimo_ok(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
    ) -> None:
        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        resultado = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert resultado.returncode != 0

    def test_falla_con_backup_atrasado(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
    ) -> None:
        import time

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        # RESPALDO_INTERVALO_SEGUNDOS=3600 (del entorno base) -> atrasado si
        # tiene más de 1,5 intervalos: 5401s alcanza.
        epoch_atrasado = int(time.time()) - 5401
        (carpeta / ".ultimo-ok").write_text(str(epoch_atrasado))
        resultado = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert resultado.returncode != 0

    def test_pasa_con_backup_reciente(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
    ) -> None:
        import time

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        (carpeta / ".ultimo-ok").write_text(str(int(time.time())))
        resultado = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert resultado.returncode == 0, resultado.stderr

    @pytest.mark.parametrize(
        "contenido",
        [
            "abc",
            "",
            "\n123",
            "١٢٣",  # dígitos árabe-índicos
        ],
    )
    def test_falla_con_marca_corrupta(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        contenido: str,
    ) -> None:
        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        (carpeta / ".ultimo-ok").write_text(contenido, encoding="utf-8")
        resultado = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert resultado.returncode != 0

    @pytest.mark.parametrize(
        "segundos_en_el_futuro",
        [
            365 * 86400,  # un año adelantado (reloj del host mal puesto)
            999999999999 - int(__import__("time").time()),  # el máximo de 12 dígitos
        ],
    )
    def test_falla_con_marca_en_el_futuro(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        segundos_en_el_futuro: int,
    ) -> None:
        """B3 (auditor, vuelta 2, F3): sólo se rechazaba `antiguedad > limite`;
        una antigüedad NEGATIVA (la marca está en el futuro) pasaba como
        salud OK, hasta que el reloj real la alcanzara. Pasa aunque el reloj
        del host haya estado adelantado cuando se escribió la marca (o la
        marca sea basura numérica dentro del rango de 12 dígitos que
        `verificar_salud` ya acepta como "número válido")."""
        import time

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        (carpeta / ".ultimo-ok").write_text(str(int(time.time()) + segundos_en_el_futuro))
        resultado = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert resultado.returncode != 0, "marca con fecha futura aceptada como salud"


class TestSaludTrasUnFalloConUltimoOkBueno:
    """R10 (vuelta 2, opción A): el rol equivocado hace fallar el volcado
    (ya probado arriba, `test_falla_pg_dump_no_deja_archivos_y_loguea_error`),
    pero antes `--salud` seguía dando 0 hasta 1,5 intervalos después del
    último backup bueno — el escenario "Volcado con el rol equivocado"
    pide que el servicio quede no saludable, y antes no quedaba si ya había
    un backup previo (el caso real; el humo parte sin ninguno, L-016)."""

    def test_salud_falla_si_un_ciclo_falla_despues_de_un_ultimo_ok_bueno(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        import time

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        (carpeta / ".ultimo-ok").write_text(str(int(time.time())))

        salud_antes = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert salud_antes.returncode == 0, salud_antes.stderr

        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_FALLA)
        resultado_ciclo = _correr(
            tmp_path,
            entorno_con_bin_falso,
            carpeta=carpeta,
            crear_carpeta=False,
            args=["--una-vez"],
        )
        assert resultado_ciclo.returncode == 1

        salud_despues = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert salud_despues.returncode != 0, "salud OK después de un ciclo fallido"

    def test_un_exito_posterior_limpia_la_marca_de_fallo(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
        escribir_herramienta_falsa: Callable[[str, str], Path],
    ) -> None:
        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()

        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_FALLA)
        resultado_fallido = _correr(
            tmp_path,
            entorno_con_bin_falso,
            carpeta=carpeta,
            crear_carpeta=False,
            args=["--una-vez"],
        )
        assert resultado_fallido.returncode == 1
        assert (carpeta / ".ultimo-fallo").exists()

        escribir_herramienta_falsa("pg_dump", FAKE_PG_DUMP_OK)
        escribir_herramienta_falsa("pg_restore", FAKE_PG_RESTORE_OK)
        resultado_ok = _correr(
            tmp_path,
            entorno_con_bin_falso,
            carpeta=carpeta,
            crear_carpeta=False,
            args=["--una-vez"],
        )
        assert resultado_ok.returncode == 0, resultado_ok.stderr

        salud = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert salud.returncode == 0, salud.stderr


class TestSaludConUltimoFalloVacioODisco:
    """V2-4 (vuelta 3): el disco lleno deja `.ultimo-fallo` CREADO pero
    VACÍO (`date +%s > .ultimo-fallo` crea el archivo antes de que la
    escritura falle) — un contenido vacío no pasa el `fullmatch` de
    `verificar_salud` y la marca se ignoraba en silencio, igual que antes
    de R10. La corrección compara por mtime (`-nt`) cuando el contenido no
    se puede leer como número, nunca depende de poder ESCRIBIR con el
    disco lleno (eso ya pasó: sólo hace falta poder leer lo que ya existe)."""

    def test_salud_falla_con_un_ultimo_fallo_vacio_mas_nuevo_que_el_ultimo_ok(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
    ) -> None:
        import os
        import time

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        marca_ok = carpeta / ".ultimo-ok"
        marca_fallo = carpeta / ".ultimo-fallo"
        marca_ok.write_text(str(int(time.time())))
        marca_fallo.write_text("")  # vacío: el caso real del disco lleno.

        ahora = time.time()
        os.utime(marca_ok, (ahora - 100, ahora - 100))
        os.utime(marca_fallo, (ahora, ahora))  # estrictamente más nueva.

        resultado = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert resultado.returncode != 0, "salud OK con un .ultimo-fallo vacío más nuevo"

    def test_salud_pasa_si_el_ultimo_fallo_vacio_es_mas_viejo_que_el_ultimo_ok(
        self,
        tmp_path: Path,
        entorno_con_bin_falso: dict[str, str],
    ) -> None:
        """El caso sano: un fallo vacío VIEJO (de antes del último éxito)
        no tiene que tapar un backup bueno más reciente."""
        import os
        import time

        carpeta = tmp_path / "respaldos"
        carpeta.mkdir()
        marca_ok = carpeta / ".ultimo-ok"
        marca_fallo = carpeta / ".ultimo-fallo"
        marca_fallo.write_text("")
        marca_ok.write_text(str(int(time.time())))

        ahora = time.time()
        os.utime(marca_fallo, (ahora - 100, ahora - 100))
        os.utime(marca_ok, (ahora, ahora))  # estrictamente más nueva que el fallo.

        resultado = _correr_salud(tmp_path, entorno_con_bin_falso, carpeta)
        assert resultado.returncode == 0, resultado.stderr
