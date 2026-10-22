"""Los nombres y comentarios describen los perfiles vigentes (L-022)."""

import re
import subprocess
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[4]
_ANTERIORES = ("titu" + "lar", "cola" + "borador")
_PATRON = re.compile("|".join((*_ANTERIORES, r"Ni" r"vel\.", r"\bni" r"vel\b")), re.I)
_HISTORIA = {
    "backend/tests/integracion/test_migracion_roles_de_la_empresa.py",
    "infra/ci/ensayo-roles.sh",
}
_LOGS = {
    "backend/src/proptech_core/compartido/logs.py",
    "backend/src/proptech_core/compartido/reintentos.py",
    "backend/tests/unitarios/test_logs.py",
    "backend/tests/unitarios/test_logs_configuracion.py",
    "backend/tests/unitarios/test_middleware_error_inesperado.py",
    "backend/tests/integracion/test_worker_caminos_de_falla.py",
    "backend/tests/integracion/test_worker_logs_de_arq.py",
    "backend/tests/infra/test_respaldos.py",
    "infra/respaldos/respaldar.sh",
}


def _justificada(ruta: str, linea: str) -> bool:
    if ruta in _HISTORIA:
        return True  # Conversión y vuelta atrás sobre 0016, deliberadamente.
    texto = linea.strip()
    if any(palabra in texto.lower() for palabra in _ANTERIORES):
        return (
            ruta == "backend/tests/unitarios/acceso/test_permisos.py"
            and any(texto.startswith(f'("{rol}",') for rol in _ANTERIORES)
        ) or (
            ruta == "backend/tests/integracion/test_asignacion_validacion.py"
            and texto.startswith('for rol in ("super_admin", "vecino",')
        )  # Datos que deben rechazarse, nunca perfiles vigentes.
    if ruta in _LOGS:
        return True
    if ruta == "backend/tests/integracion/test_asignacion_validacion.py":
        return '"ni' + 'vel"' in texto  # Campo que debe dar 422.
    return any(
        expresion in texto
        for expresion in (
            "ni" + "vel de anidamiento",
            "ni" + "vel del modelo",
            "al ni" + "vel",
            "un ni" + "vel más adentro",
        )
    )


def _versionados(carpeta: str) -> list[Path]:
    """Archivos bajo `carpeta` que git tiene versionados, vistos desde la
    raíz del repo: lo ignorado (respaldos reales, `.env`) nunca aparece acá,
    a diferencia de un `rglob` sobre el filesystem."""
    salida = subprocess.run(
        ["git", "ls-files", carpeta],
        cwd=str(_RAIZ),
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [_RAIZ / linea for linea in salida.splitlines() if linea]


def test_fuentes_nombres_y_comentarios_usan_perfiles_vigentes() -> None:
    archivos = [_RAIZ / "backend/migraciones/ayudas_rls.py"]
    for carpeta in ("backend/src", "backend/tests", "infra"):
        archivos.extend(
            archivo
            for archivo in _versionados(carpeta)
            if archivo.is_file()
            and archivo.suffix != ".pyc"
            and not any(parte.startswith(".") for parte in archivo.relative_to(_RAIZ).parts)
        )
    assert _RAIZ / "backend/src/proptech_core/acceso/dominio/permisos.py" in archivos
    inesperadas = [
        f"{ruta}:{numero}:{linea.strip()}"
        for archivo in sorted(archivos)
        for ruta in [archivo.relative_to(_RAIZ).as_posix()]
        for numero, linea in enumerate(archivo.read_text().splitlines(), 1)
        if _PATRON.search(linea) and not _justificada(ruta, linea)
    ]
    assert inesperadas == []
