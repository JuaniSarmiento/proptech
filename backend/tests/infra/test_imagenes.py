"""Toda imagen usada (Compose y Dockerfiles) tiene versión de parche fijada, nunca `latest`."""

import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[3]
COMPOSE = RAIZ / "infra" / "compose.yaml"

# Exige explícitamente los tres números (mayor.menor.parche). Excepción documentada:
# PostgreSQL versiona con sólo dos números (`18.6`, no `18.6.0`); ver EXCEPCIONES_DOS_NUMEROS.
PATRON_VERSION_DE_PARCHE = re.compile(r":[0-9]+\.[0-9]+\.[0-9]+[\w.-]*$")
PATRON_VERSION_DOS_NUMEROS = re.compile(r":[0-9]+\.[0-9]+[\w.-]*$")
EXCEPCIONES_DOS_NUMEROS = {"postgres"}
PATRON_COPY_FROM = re.compile(r"--from=(\S+)")


def _imagenes_de_compose() -> dict[str, str]:
    """Imágenes de servicios que se bajan de un registro (sin `build:`).

    Los servicios con `build:` usan un tag local (p.ej. `proptech-backend:local`)
    como nombre del resultado, no una referencia versionada; su imagen *base*
    ya se valida vía el Dockerfile, en `test_imagenes_de_dockerfiles_...`.
    """
    datos = yaml.safe_load(COMPOSE.read_text())
    servicios = datos.get("services", {})
    return {
        nombre: servicio["image"]
        for nombre, servicio in servicios.items()
        if "image" in servicio and "build" not in servicio
    }


def _repo_base(imagen: str) -> str:
    """Nombre del repositorio sin tag ni host/organización (p.ej. `postgres` de
    `docker.io/library/postgres:18.6-trixie`)."""
    repo, _, _tag = imagen.rpartition(":")
    return repo.rsplit("/", 1)[-1]


def _version_de_parche_valida(imagen: str) -> bool:
    """Exige mayor.menor.parche, salvo la excepción documentada (PostgreSQL, dos números)."""
    if _repo_base(imagen) in EXCEPCIONES_DOS_NUMEROS:
        return bool(PATRON_VERSION_DOS_NUMEROS.search(imagen))
    return bool(PATRON_VERSION_DE_PARCHE.search(imagen))


def _imagenes_from_de_dockerfiles(raiz: Path = RAIZ) -> list[str]:
    """Imágenes de los `FROM` y de los `COPY --from=` que apuntan a un registro
    externo (no a una etapa local definida con `AS` en el mismo Dockerfile)."""
    imagenes = []
    for dockerfile in raiz.glob("*/Dockerfile"):
        lineas = dockerfile.read_text().splitlines()
        etapas_locales = set()
        for linea in lineas:
            linea = linea.strip()
            if linea.upper().startswith("FROM "):
                partes = linea.split()
                imagenes.append(partes[1])
                if " AS " in linea.upper():
                    etapas_locales.add(partes[-1])
        for linea in lineas:
            linea = linea.strip()
            if not linea.upper().startswith("COPY "):
                continue
            coincidencia = PATRON_COPY_FROM.search(linea)
            if coincidencia is None:
                continue
            origen = coincidencia.group(1)
            es_referencia_a_registro = "/" in origen or ":" in origen or "." in origen
            if origen not in etapas_locales and es_referencia_a_registro:
                imagenes.append(origen)
    return imagenes


def test_imagenes_de_compose_tienen_version_de_parche_sin_latest() -> None:
    imagenes = _imagenes_de_compose()
    assert imagenes, "no se encontraron servicios con imagen en compose.yaml"
    for nombre, imagen in imagenes.items():
        assert ":" in imagen, f"{nombre} ({imagen}) no tiene etiqueta"
        assert not imagen.endswith(":latest"), f"{nombre} ({imagen}) usa latest"
        assert _version_de_parche_valida(imagen), f"{nombre} ({imagen}) no tiene versión de parche"


def test_imagenes_de_dockerfiles_tienen_version_de_parche_sin_latest() -> None:
    # Este cambio crea los Dockerfiles más adelante (tareas 5 y 6); el chequeo
    # vale igual si todavía no hay ninguno (lista vacía) y sigue aplicando sin
    # reescribirse cuando aparezcan.
    imagenes = _imagenes_from_de_dockerfiles()
    for imagen in imagenes:
        if imagen.lower().startswith("scratch"):
            continue
        assert ":" in imagen, f"{imagen} no tiene etiqueta"
        assert not imagen.endswith(":latest"), f"{imagen} usa latest"
        assert _version_de_parche_valida(imagen), f"{imagen} no tiene versión de parche"


def test_conftest_no_tiene_una_imagen_de_postgres_escrita_a_mano() -> None:
    """D12: el fixture deriva la imagen de compose.yaml; no hay una constante
    de imagen escrita a mano en tests/conftest.py (el test tautológico que
    comparaba la constante con sí misma nunca podía fallar, D-051)."""
    conftest = (Path(__file__).resolve().parents[1] / "conftest.py").read_text()
    assert re.search(r':\s*["\'][0-9]+\.[0-9]', conftest) is None, (
        "conftest.py parece tener una versión de imagen escrita a mano"
    )
    assert "_leer_imagen_de_compose" in conftest


def test_patron_version_de_parche_rechaza_tags_de_dos_numeros_sin_excepcion() -> None:
    """Regresión del auditor: python:3.14-slim y caddy:2.11-alpine no declaran parche
    (tercer número) y el patrón anterior los aceptaba por error."""
    assert not _version_de_parche_valida("python:3.14-slim"), (
        "python:3.14-slim no tiene versión de parche y no debería aceptarse"
    )
    assert not _version_de_parche_valida("caddy:2.11-alpine"), (
        "caddy:2.11-alpine no tiene versión de parche y no debería aceptarse"
    )


def test_patron_version_de_parche_acepta_la_excepcion_de_postgres() -> None:
    """postgres versiona con dos números (`18.6`, no `18.6.0`); es la única excepción."""
    assert _version_de_parche_valida("postgres:18.6-trixie")
    assert not _version_de_parche_valida("postgres:18-trixie")


def test_copy_from_de_imagen_externa_sin_parche_se_detecta(tmp_path: Path) -> None:
    """Un `COPY --from=` que referencia una imagen de registro (no una etapa local)
    debe entrar en la lista a validar, igual que las imágenes de los `FROM`."""
    carpeta_servicio = tmp_path / "servicio"
    carpeta_servicio.mkdir()
    (carpeta_servicio / "Dockerfile").write_text(
        "FROM scratch AS base\n"
        "COPY --from=registro.example.com/herramienta:1.2 /bin/x /bin/x\n"
        "COPY --from=base /app /app\n"
    )

    imagenes = _imagenes_from_de_dockerfiles(raiz=tmp_path)

    assert "registro.example.com/herramienta:1.2" in imagenes, (
        "la imagen externa referenciada en COPY --from= no se detectó"
    )
    assert "base" not in imagenes, "una etapa local (AS base) no es una imagen a validar"
