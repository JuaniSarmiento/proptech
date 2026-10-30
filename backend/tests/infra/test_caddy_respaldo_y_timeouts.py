"""Caddy: el sitio de respaldo, el 443 sin dominio y los timeouts (cambio 2e `humo-y-ci`).

Escenarios de `entorno-de-ejecucion`: El sitio de respaldo del proxy responde 421 y lo dice un test;
Qué cubre y qué no el proxy con un sitio https está declarado; El proxy no cuelga si un servicio de
atrás no responde. C2V2-6, C2V2-1 y N2 de la ficha 2e.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
CADDYFILE = RAIZ / "infra" / "Caddyfile"
HUMO = RAIZ / "infra" / "ci" / "humo.sh"

METODOS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE")

#: Plazo máximo de espera de una respuesta de atrás (segundos): lo que el spec llama "plazo
#: configurado". El humo mide que el corte llega antes de este valor más un margen de 5 s.
PLAZO_MAXIMO_RESPUESTA = 30


def _sin_comentarios(texto: str) -> str:
    return "\n".join(linea for linea in texto.splitlines() if not linea.strip().startswith("#"))


def _bloque_del_sitio_de_respaldo() -> str:
    texto = _sin_comentarios(CADDYFILE.read_text(encoding="utf-8"))
    inicio = texto.index(":80 {")
    return texto[inicio : texto.index("\n}", inicio)]


def test_el_sitio_de_respaldo_responde_421_y_nada_mas() -> None:
    """C2V2-6: nada lo fijaba. Un cambio a otro código, o un `reverse_proxy` ahí, da rojo."""
    bloque = _bloque_del_sitio_de_respaldo()
    respuestas = [
        linea.strip() for linea in bloque.splitlines() if linea.strip().startswith("respond")
    ]
    assert respuestas == ["respond 421"]
    assert "reverse_proxy" not in bloque


def test_el_humo_prueba_los_ocho_metodos_contra_el_respaldo() -> None:
    texto = HUMO.read_text(encoding="utf-8")
    bucle = re.search(r"for metodo in ([A-Z ]+); do", texto)
    assert bucle is not None, "el humo no recorre los métodos HTTP contra el sitio de respaldo"
    assert tuple(bucle.group(1).split()) == METODOS
    assert "421" in texto[bucle.start() :][:600]


def test_el_caddyfile_no_declara_el_443_ni_hsts() -> None:
    """C2V2-1: sin dominio no se puede fijar el comportamiento del 443 ni de la redirección
    308. Esta es la declaración del estado actual (spec `entorno-de-ejecucion`, "Qué cubre y qué
    no el proxy con un sitio https está declarado"): si cambia, hay que actualizar la declaración
    y la ficha del cambio 15, que es el que pone el dominio real y HSTS."""
    texto = _sin_comentarios(CADDYFILE.read_text(encoding="utf-8"))
    assert not re.search(r"^\s*:?443\b", texto, flags=re.MULTILINE), (
        "el Caddyfile ahora declara un sitio para el 443: actualizá la declaración del spec "
        "`entorno-de-ejecucion` y la ficha del cambio 15"
    )
    assert "strict-transport-security" not in texto.lower(), (
        "el Caddyfile ahora pone HSTS: actualizá la declaración del spec `entorno-de-ejecucion` "
        "y la ficha del cambio 15"
    )


def _segundos(valor: str) -> float:
    numero, unidad = re.fullmatch(r"([0-9.]+)(ms|s|m)", valor).groups()  # type: ignore[union-attr]
    return float(numero) * {"ms": 0.001, "s": 1, "m": 60}[unidad]


def _bloque_de_reverse_proxy(destino: str) -> str:
    texto = _sin_comentarios(CADDYFILE.read_text(encoding="utf-8"))
    inicio = texto.index(f"reverse_proxy {destino}")
    fin_de_linea = texto.index("\n", inicio)
    if not texto[inicio:fin_de_linea].rstrip().endswith("{"):
        return texto[inicio:fin_de_linea]
    profundidad = 0
    for posicion in range(inicio, len(texto)):
        if texto[posicion] == "{":
            profundidad += 1
        elif texto[posicion] == "}":
            profundidad -= 1
            if profundidad == 0:
                return texto[inicio : posicion + 1]
    raise AssertionError(f"reverse_proxy {destino}: llave sin cerrar")


def test_cada_reverse_proxy_tiene_timeouts() -> None:
    """N2: sin timeout, con la `api` pausada Caddy no respondía en 100 s."""
    for destino in ("api:8000", "web:3000"):
        bloque = _bloque_de_reverse_proxy(destino)
        conexion = re.search(r"dial_timeout\s+(\S+)", bloque)
        respuesta = re.search(r"response_header_timeout\s+(\S+)", bloque)
        assert conexion, f"reverse_proxy {destino} sin dial_timeout"
        assert respuesta, f"reverse_proxy {destino} sin response_header_timeout"
        assert _segundos(conexion.group(1)) <= 10
        assert _segundos(respuesta.group(1)) <= PLAZO_MAXIMO_RESPUESTA


def test_el_humo_pausa_api_y_web_y_mide_el_corte() -> None:
    texto = HUMO.read_text(encoding="utf-8")
    assert 'compose pause "$servicio"' in texto
    assert 'compose unpause "$servicio"' in texto
    assert "cortar_en_plazo api /api/salud" in texto
    assert "cortar_en_plazo web /" in texto
    assert '"502"' in texto and '"504"' in texto


def test_limpiar_despausa_api_y_web_antes_del_down_v() -> None:
    texto = HUMO.read_text(encoding="utf-8")
    inicio = texto.index("limpiar() {")
    cuerpo = texto[inicio : texto.index("\n}\n", inicio)]
    posicion_down = cuerpo.index("compose down -v --remove-orphans")
    for servicio in ("api", "web"):
        assert cuerpo.index(f"compose unpause {servicio}") < posicion_down
