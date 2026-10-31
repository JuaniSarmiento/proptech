"""`.github/dependabot.yml` (cambio 2e `humo-y-ci`, D13).

Escenario de `integracion-continua`: El archivo es válido. Que Dependabot abra su primer PR no se
puede ver en local: queda como verificación [GH] en `tasks.md` 9.5.
"""

from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[3]
ARCHIVO = RAIZ / ".github" / "dependabot.yml"

#: (ecosistema, directorio). `docker-compose` es un ecosistema aparte de `docker`: `docker` sólo
#: lee Dockerfile, así que las imágenes de `infra/compose.yaml` (Postgres, Redis, Caddy) necesitan
#: el suyo.
ESPERADO = {
    ("github-actions", "/"),
    ("docker", "/backend"),
    ("docker", "/web"),
    ("docker-compose", "/infra"),
    ("uv", "/backend"),
    ("npm", "/web"),
}


def _entradas() -> list[dict[str, Any]]:
    datos = yaml.safe_load(ARCHIVO.read_text(encoding="utf-8"))
    assert datos["version"] == 2
    return list(datos["updates"])


def test_declara_cada_ecosistema_en_su_directorio() -> None:
    assert {(e["package-ecosystem"], e["directory"]) for e in _entradas()} == ESPERADO


def test_cada_directorio_existe() -> None:
    for entrada in _entradas():
        assert (RAIZ / entrada["directory"].lstrip("/")).is_dir(), entrada["directory"]


def test_semanal_y_con_limite_de_pr_abiertos() -> None:
    for entrada in _entradas():
        assert entrada["schedule"]["interval"] == "weekly", entrada
        assert 1 <= entrada["open-pull-requests-limit"] <= 5, entrada


def test_las_actualizaciones_de_acciones_conservan_el_sha_en_un_grupo() -> None:
    """Dependabot mantiene el SHA de 40 caracteres cuando la acción ya está fijada así; el límite
    lo sigue exigiendo `test_ci_workflow.py`."""
    acciones = next(e for e in _entradas() if e["package-ecosystem"] == "github-actions")
    assert acciones["directory"] == "/"
