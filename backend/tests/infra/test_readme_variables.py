"""D8, tarea 7.1: una sola tabla de variables de entorno, en el README de
la raíz; `knowledge-base/08_arquitectura_propuesta.md` la reemplaza por un
enlace (dos tablas son una que deriva).

Test en los dos sentidos contra la unión de `infra/.env.example` y lo que
`infra/compose.yaml` trae: falla si una variable falta en la tabla del
README, o si la tabla nombra una que ya no existe en ninguno de los dos.

L-018: se compara contra el efecto real de `compose.yaml` (lo que Compose
termina fijando dentro de cada contenedor), no contra una lista escrita a
mano que puede quedar vieja.
"""

import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[3]
ENV_EXAMPLE = RAIZ / "infra" / ".env.example"
COMPOSE = RAIZ / "infra" / "compose.yaml"
README = RAIZ / "README.md"
ARQUITECTURA = RAIZ / "knowledge-base" / "08_arquitectura_propuesta.md"

_PATRON_ASIGNACION_ENV = re.compile(r"^([A-Z][A-Z0-9_]*)=", flags=re.MULTILINE)
_PATRON_SUSTITUCION = re.compile(r"\$\{([A-Z][A-Z0-9_]*)")


def _variables_de_env_example() -> set[str]:
    return set(_PATRON_ASIGNACION_ENV.findall(ENV_EXAMPLE.read_text()))


def _variables_de_compose() -> set[str]:
    """Para cada `CLAVE: valor` de un `environment:` de `compose.yaml`: si
    el valor contiene `${NOMBRE...}`, la variable real es NOMBRE (puede
    coincidir con CLAVE —caso común, D1 a D3— o ser otra —`respaldos` re-
    expone `POSTGRES_RESPALDO_USER` como `PGUSER`, convención de libpq—;
    en ese caso lo que hay que documentar es NOMBRE, no el alias). Si el
    valor es literal (sin `${}`), la variable es la propia CLAVE (caso de
    `FORWARDED_ALLOW_IPS`, `REDIS_HOST`, `PGHOST`, etc.)."""
    datos = yaml.safe_load(COMPOSE.read_text())
    variables: set[str] = set()
    for servicio in datos["services"].values():
        entorno = servicio.get("environment") or {}
        items = entorno.items() if isinstance(entorno, dict) else []
        for clave, valor in items:
            coincidencias = _PATRON_SUSTITUCION.findall(str(valor))
            if coincidencias:
                variables.update(coincidencias)
            else:
                variables.add(clave)
    return variables


def _variables_de_la_tabla_del_readme() -> set[str]:
    """Las filas de toda tabla markdown bajo '## Variables de entorno':
    la primera columna, que puede nombrar más de una variable separada por
    ` / ` (pares usuario/contraseña, D1 a D3)."""
    texto = README.read_text()
    inicio = texto.index("## Variables de entorno")
    resto = texto[inicio:]
    siguiente_titulo = re.search(r"\n## ", resto[1:])
    seccion = resto[: siguiente_titulo.start() + 1] if siguiente_titulo else resto

    variables: set[str] = set()
    for linea in seccion.splitlines():
        if not linea.startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip("|").split("|")]
        if not celdas or celdas[0] in ("Variable", "---") or set(celdas[0]) <= {"-", " "}:
            continue
        primera_celda = celdas[0]
        for nombre in re.findall(r"`([A-Z][A-Z0-9_]*)`", primera_celda):
            variables.add(nombre)
    return variables


def test_env_example_y_compose_tienen_al_menos_una_variable() -> None:
    assert _variables_de_env_example()
    assert _variables_de_compose()


def test_toda_variable_de_env_example_y_compose_esta_en_la_tabla_del_readme() -> None:
    esperadas = _variables_de_env_example() | _variables_de_compose()
    en_tabla = _variables_de_la_tabla_del_readme()
    faltantes = esperadas - en_tabla
    assert not faltantes, f"variables sin fila en la tabla del README: {sorted(faltantes)}"


def test_la_tabla_del_readme_no_nombra_una_variable_inexistente() -> None:
    esperadas = _variables_de_env_example() | _variables_de_compose()
    en_tabla = _variables_de_la_tabla_del_readme()
    sobrantes = en_tabla - esperadas
    assert not sobrantes, (
        f"la tabla del README nombra variables que no están en .env.example "
        f"ni en compose.yaml: {sorted(sobrantes)}"
    )


def test_08_ya_no_tiene_su_propia_tabla_y_enlaza_al_readme() -> None:
    """D8: dos tablas son una que deriva. `08` sólo puede tener un enlace."""
    texto = ARQUITECTURA.read_text()
    inicio = texto.index("## Variables de entorno")
    resto = texto[inicio:]
    siguiente_titulo = re.search(r"\n## ", resto[1:])
    seccion = resto[: siguiente_titulo.start() + 1] if siguiente_titulo else resto
    assert "README.md" in seccion, "08 ya no enlaza al README para la tabla de variables"
    filas_de_tabla = [
        linea
        for linea in seccion.splitlines()
        if linea.startswith("|") and not set(linea.strip("|").strip()) <= {"-", " ", "|"}
    ]
    assert not filas_de_tabla, (
        f"08 todavía tiene filas de una tabla propia de variables: {filas_de_tabla}"
    )


def test_readme_no_dice_que_el_1d_esta_propuesto() -> None:
    """V3-15: 1d (`respaldos-y-restauracion`) está archivado desde el
    14/10/2026 (`CHANGES.md`); el README decía 'Propuesto: **1d** ...'
    (con `**` de markdown, por eso la búsqueda no es un string exacto)."""
    texto = README.read_text()
    assert not re.search(r"[Pp]ropuesto[^.]{0,40}1d\b", texto), (
        "el README todavía describe al 1d como propuesto"
    )
    assert re.search(r"\b1d\b", texto) and "archivad" in texto.lower()


def test_readme_dice_que_el_worker_tiene_salida_a_internet() -> None:
    """V3-15: `salida_worker` (compose.yaml) le da al worker una red sin
    `internal`; decir que TODOS los servicios de atrás de Caddy están en
    'redes internas sin salida' es falso para el worker."""
    texto = README.read_text()
    assert "salida_worker" in texto


def test_readme_pide_las_cuatro_contrasenas_distintas() -> None:
    """V3-15: R8 (vuelta 2 del 2a) rechaza el arranque si dos de las
    cuatro POSTGRES_*_PASSWORD coinciden; `.env.example` ya lo dice, el
    README todavía no."""
    texto = README.read_text()
    assert "distint" in texto.lower()


def _celdas_de(tabla_texto: str, variable: str) -> list[str]:
    for linea in tabla_texto.splitlines():
        if linea.startswith("|") and f"`{variable}`" in linea.split("|")[1]:
            return [c.strip() for c in linea.strip("|").split("|")]
    return []


def test_la_fila_de_postgres_user_ya_no_dice_que_la_comparten_los_cuatro_servicios() -> None:
    """Hallazgo de la revisión de DevOps: desde el 2a, POSTGRES_USER (rol
    de arranque) sólo lo reciben `db` y `migraciones`; API y worker usan
    POSTGRES_APP_USER. La fila vieja decía 'compartido por los cuatro
    servicios', que ya es falso."""
    texto = README.read_text()
    inicio = texto.index("## Variables de entorno")
    seccion = texto[inicio:]
    celdas = _celdas_de(seccion, "POSTGRES_USER")
    assert celdas, "no se encontró una fila para POSTGRES_USER"
    assert "cuatro servicios" not in " ".join(celdas)
