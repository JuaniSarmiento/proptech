"""Tests estáticos sobre `infra/ci/humo.sh` (D14, D19, L-006).

Escenario de `integracion-continua`: Humo en el CI (destrucción con
`-p proptech`). Tarea 6.1.
"""

import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
HUMO = RAIZ / "infra" / "ci" / "humo.sh"

#: Cualquier línea que invoque `docker compose` (no un comentario ni un
#: `echo` descriptivo: eso se cubre renombrando esas líneas, ver más abajo).
_PATRON_DOCKER_COMPOSE = re.compile(r"docker compose\b")


def _lineas_no_comentario(texto: str) -> list[str]:
    return [linea for linea in texto.splitlines() if not linea.strip().startswith("#")]


def test_humo_existe() -> None:
    assert HUMO.exists(), "falta infra/ci/humo.sh"


def test_toda_invocacion_de_docker_compose_lleva_p_proptech() -> None:
    """L-006: lo destructivo (sobre todo `down -v`) apunta siempre al
    proyecto `proptech`, sin depender de que `name: proptech` siga en
    `compose.yaml`."""
    texto = HUMO.read_text()
    for linea in _lineas_no_comentario(texto):
        if _PATRON_DOCKER_COMPOSE.search(linea):
            assert "-p proptech" in linea, (
                f"invocación de 'docker compose' sin '-p proptech': {linea.strip()!r}"
            )


#: Mismo patrón que `_PATRON_UUID_CANONICO` de
#: `proptech_core.compartido.seguimiento` (L-008: sólo ASCII, `fullmatch`).
_PATRON_UUID_CANONICO = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
    flags=re.ASCII,
)


def test_el_valor_cliente_del_paso_7_es_un_uuid_canonico() -> None:
    """B4-bis (auditor, vuelta 2, L-017): la entrada de un chequeo es la del
    escenario, no una que otra capa ya rechaza. El escenario
    `trazabilidad-y-logs` > "Cliente que manda su propio número" dice "igual
    a un UUID que eligió"; un valor que NO es un UUID canónico lo descarta
    `validar_request_id` (`seguimiento.py`) sola, sin que Caddy tenga que
    pisar nada: el paso 7 pasaría igual aunque Caddy no pisara el
    encabezado."""
    texto = HUMO.read_text()
    coincidencia = re.search(r'valor_cliente="([^"]*)"', texto)
    assert coincidencia is not None, "no se encontró la asignación de valor_cliente en el paso 7"
    valor_cliente = coincidencia.group(1)
    assert _PATRON_UUID_CANONICO.fullmatch(valor_cliente), (
        f"valor_cliente no es un UUID canónico: {valor_cliente!r}"
    )


def test_el_humo_cuenta_salud_degradada_y_f7c_en_api_y_worker() -> None:
    """B5 (auditor, vuelta 2, L-016): `respaldos` es un script de bash, nunca
    usa `FormateadorJSON` (D7) y por lo tanto NUNCA puede emitir
    `traceback_crudo_descartado` ni `mensaje_no_texto`: contar esos eventos
    sólo en sus logs es un cero garantizado, no una observación del caso real
    que F7c esperaba ver (los únicos que lo emiten son `api` y `worker`). El
    mismo argumento vale para `salud_degradada` (5.1): el único servicio que
    lo loguea es `api`. El conteo de los tres tiene que mirar, como mínimo,
    `api` y `worker`."""
    texto = HUMO.read_text()
    for patron in ("traceback_crudo_descartado", "mensaje_no_texto", "salud_degradada"):
        llamada = re.search(rf'cantidad_\w+=\$\(contar_evento "{patron}"([^)]*)\)', texto)
        assert llamada is not None, (
            f"no se encontró un conteo de '{patron}' con la forma "
            f"'cantidad_x=$(contar_evento \"{patron}\" <servicios>)'"
        )
        servicios = llamada.group(1)
        assert "api" in servicios, f"'{patron}': el conteo no mira los logs de api: {servicios!r}"
        assert "worker" in servicios, (
            f"'{patron}': el conteo no mira los logs de worker: {servicios!r}"
        )


def test_todo_script_de_infra_es_ejecutable() -> None:
    """D-5/D-6 (deuda del 2a, tarea 2.3): todo `infra/**/*.sh` tiene que
    estar en `100755` según el índice de git, no según el filesystem (que
    un checkout puede normalizar distinto): `git update-index --chmod=+x`
    es lo que de verdad hace falta, no sólo `chmod` local."""
    resultado = subprocess.run(
        ["git", "ls-files", "-s", "infra"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    scripts_sin_modo_ejecutable = [
        linea
        for linea in resultado.stdout.splitlines()
        if linea.rsplit("\t", 1)[-1].endswith(".sh") and not linea.startswith("100755")
    ]
    assert not scripts_sin_modo_ejecutable, (
        f"scripts de infra/ sin modo 100755 en el índice de git: {scripts_sin_modo_ejecutable}"
    )


def test_limpiar_despausa_antes_del_down_v() -> None:
    """D6, tarea 5.2: `limpiar` tiene que despausar `db` y `redis` ANTES
    de `compose down -v` (si no, una pausa que la propia falla deja
    puesta se pierde de vista: `down` la baja igual, pero haber estado
    pausada hasta entonces es un estado que nadie pidió). Se verifica el
    ORDEN textual dentro de la función `limpiar`, no sólo que las tres
    líneas existan en algún lado del archivo."""
    texto = HUMO.read_text()
    inicio = texto.index("limpiar() {")
    fin = texto.index("\n}\n", inicio)
    cuerpo_limpiar = texto[inicio:fin]

    posicion_unpause_db = cuerpo_limpiar.index("compose unpause db")
    posicion_unpause_redis = cuerpo_limpiar.index("compose unpause redis")
    # La invocación real, no el `echo "--- limpieza: compose down -v
    # ---"` decorativo de más arriba (que también contiene la cadena
    # "compose down -v" y matchearía primero).
    posicion_down_v = cuerpo_limpiar.index("compose down -v --remove-orphans")

    assert posicion_unpause_db < posicion_down_v, (
        "'compose unpause db' tiene que ir ANTES de 'compose down -v' en limpiar()"
    )
    assert posicion_unpause_redis < posicion_down_v, (
        "'compose unpause redis' tiene que ir ANTES de 'compose down -v' en limpiar()"
    )
