"""QA-5 (`ejemplo-robusto`, D8): parte de la guarda del escenario "El repositorio no tiene
un punto de entrada propio" del spec `acceso-de-desarrollo`. Mira sólo los dos que nombra
`proposal.md`, `backend/desarrollo` e `infra/compose.desarrollo.yaml`, porque reemplazarían al
login y su sola existencia ya es rojo. No ve variantes con otro nombre o en otra carpeta, ni
una variable que active un punto de entrada.

La raíz es un parámetro para poder probar la guarda contra una copia con el archivo
prohibido (L-016), y sólo se mira la existencia, sin recorrer carpetas reales (L-033).
"""

from pathlib import Path

import pytest

_RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[3]
_PROHIBIDOS = ("backend/desarrollo", "infra/compose.desarrollo.yaml")


def _puntos_de_entrada_prohibidos(raiz: Path) -> list[str]:
    return [relativa for relativa in _PROHIBIDOS if (raiz / relativa).exists()]


def test_el_repositorio_no_tiene_puntos_de_entrada_prohibidos() -> None:
    # Sin estas dos, una ruta equivocada dejaría a la guarda pasando en vacío (L-016).
    assert (_RAIZ_DEL_REPOSITORIO / "infra" / "compose.yaml").is_file()
    assert (_RAIZ_DEL_REPOSITORIO / "backend" / "pyproject.toml").is_file()

    assert _puntos_de_entrada_prohibidos(_RAIZ_DEL_REPOSITORIO) == []


@pytest.mark.parametrize("prohibido", ["backend/desarrollo", "infra/compose.desarrollo.yaml"])
def test_la_guarda_ve_cada_punto_de_entrada(tmp_path: Path, prohibido: str) -> None:
    ruta = tmp_path / prohibido
    ruta.parent.mkdir(parents=True)
    if ruta.suffix:
        ruta.write_text("services: {}\n", encoding="utf-8")
    else:
        ruta.mkdir()

    assert _puntos_de_entrada_prohibidos(tmp_path) == [prohibido]
