"""Cada Dockerfile del repo corre como usuario no root y su .dockerignore excluye .env*."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


def _dockerfiles() -> list[Path]:
    return sorted(RAIZ.glob("*/Dockerfile"))


def _ultima_etapa_usuario(dockerfile: Path) -> str | None:
    usuario_actual: str | None = None
    for linea in dockerfile.read_text().splitlines():
        texto = linea.strip()
        if texto.upper().startswith("FROM "):
            usuario_actual = None  # cada etapa nueva arranca sin USER declarado
        elif texto.upper().startswith("USER "):
            usuario_actual = texto.split(None, 1)[1].strip()
    return usuario_actual


def test_dockerfiles_existen() -> None:
    assert _dockerfiles(), "no se encontró ningún Dockerfile en el repo"


def test_ultima_etapa_declara_usuario_no_root() -> None:
    for dockerfile in _dockerfiles():
        usuario = _ultima_etapa_usuario(dockerfile)
        assert usuario is not None, f"{dockerfile} no declara USER en su última etapa"
        assert usuario not in ("root", "0"), f"{dockerfile} corre como root ({usuario})"


def test_dockerignore_excluye_env_y_env_estrella() -> None:
    for dockerfile in _dockerfiles():
        dockerignore = dockerfile.parent / ".dockerignore"
        assert dockerignore.exists(), f"falta {dockerignore}"
        contenido = dockerignore.read_text().splitlines()
        contenido_limpio = [linea.strip() for linea in contenido]
        assert ".env" in contenido_limpio, f"{dockerignore} no excluye .env"
        assert ".env.*" in contenido_limpio, f"{dockerignore} no excluye .env.*"
