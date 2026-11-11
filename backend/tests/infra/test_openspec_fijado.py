"""OpenSpec queda en la versión que fija el README (2e, D10 del 6).

El instalador de Active Stack deja la última versión de OpenSpec y un `openspec update` regenera
`.claude/skills/openspec-*` con ella (en el 6 se instaló la 1.14.3 en vez de la 1.13.0). El
repositorio no puede mirar la máquina de nadie, pero sí que lo que se commitea siga generado por la
versión fijada: si alguien regenera las skills con otra, este test da rojo.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


def _version_fijada(raiz: Path) -> str:
    """La versión que el README manda instalar con `npm install -g @fission-ai/openspec@X`."""
    encontrada = re.search(
        r"@fission-ai/openspec@(\d+\.\d+\.\d+)", (raiz / "README.md").read_text()
    )
    assert encontrada, "el README no fija la versión de OpenSpec con @fission-ai/openspec@X.Y.Z"
    return encontrada.group(1)


def _discrepancias(raiz: Path) -> list[str]:
    fijada = _version_fijada(raiz)
    skills = sorted((raiz / ".claude" / "skills").glob("openspec-*/SKILL.md"))
    assert skills, "no hay skills openspec-* generadas"
    malas = []
    for skill in skills:
        generada = re.search(r'generatedBy:\s*"([^"]+)"', skill.read_text())
        if generada is None or generada.group(1) != fijada:
            malas.append(
                f"{skill.relative_to(raiz)}: {generada.group(1) if generada else 'sin generatedBy'}"
            )
    return malas


def test_las_skills_de_openspec_estan_generadas_con_la_version_fijada() -> None:
    assert _discrepancias(RAIZ) == [], "regeneradas con otra versión de OpenSpec que la del README"


def test_una_skill_regenerada_con_otra_version_da_rojo(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("npm install -g @fission-ai/openspec@1.13.0\n")
    for nombre, version in (("openspec-propose", "1.13.0"), ("openspec-apply-change", "1.14.3")):
        carpeta = tmp_path / ".claude" / "skills" / nombre
        carpeta.mkdir(parents=True)
        (carpeta / "SKILL.md").write_text(f'metadata:\n  generatedBy: "{version}"\n')
    assert _discrepancias(tmp_path) == [
        f"{Path('.claude/skills/openspec-apply-change/SKILL.md')}: 1.14.3"
    ]
