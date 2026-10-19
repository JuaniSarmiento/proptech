"""D13 (deuda del 1b con dueño 3, tarea 2.4): `.gitignore` ampliado con los
artefactos de desarrollo que todavía no cubría — editores (`.vscode/`,
`.idea/`), el sistema de archivos de macOS/Windows (`.DS_Store`,
`Thumbs.db`) y los artefactos de empaquetado/cobertura de Python
(`*.egg-info/`, `dist/`, `build/`, `.coverage`, `htmlcov/`). Los cachés de
`mypy`/`pytest`/`ruff` ya se ignoran solos (cada uno escribe su propio
`.gitignore` adentro, verificado con `git check-ignore`); esto no los toca."""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


def _gitignore() -> str:
    return (RAIZ / ".gitignore").read_text()


def test_gitignore_cubre_carpetas_de_editores() -> None:
    contenido = _gitignore()
    assert ".vscode/" in contenido
    assert ".idea/" in contenido


def test_gitignore_cubre_archivos_de_sistema_operativo() -> None:
    contenido = _gitignore()
    assert ".DS_Store" in contenido
    assert "Thumbs.db" in contenido


def test_gitignore_cubre_artefactos_de_empaquetado_y_cobertura_de_python() -> None:
    contenido = _gitignore()
    assert "*.egg-info/" in contenido
    assert ".coverage" in contenido
    assert "htmlcov/" in contenido


# --- D13 (deuda del 1b con dueño 3, tarea 2.4): el test de chmod salteado
# en Windows (`os.chmod(0o000)` no bloquea la lectura ahí; el test fallaría
# por una razón ajena a `cargador_yaml.py`). Es un test estático sobre el
# código fuente del test (no se puede ejercitar el salto real sin una
# máquina Windows, ASUNCIÓN declarada), igual que `test_ci_workflow.py`
# verifica el workflow sin correrlo. ---


def test_el_test_de_chmod_esta_salteado_en_windows() -> None:
    import ast

    ruta = RAIZ / "backend" / "tests" / "unitarios" / "test_cargador_yaml.py"
    arbol = ast.parse(ruta.read_text())
    funcion = next(
        nodo
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.FunctionDef)
        and nodo.name == "test_archivo_sin_permiso_de_lectura_falla"
    )
    fuente_decoradores = "\n".join(ast.unparse(d) for d in funcion.decorator_list)
    assert "skipif" in fuente_decoradores, (
        f"falta un @pytest.mark.skipif en el test de chmod: {fuente_decoradores!r}"
    )
    assert "win32" in fuente_decoradores
