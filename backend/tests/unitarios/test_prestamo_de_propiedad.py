"""D-115.3: una migración que hace `ALTER` sobre una tabla protegida lo declara en
`PRESTA_PROPIEDAD`, y `roles antes` presta sólo esas tablas y sólo mientras la migración está
pendiente. Acá, la parte pura: qué tablas hay que prestar según las migraciones y la versión de la
base. Sin base de datos."""

from pathlib import Path

import pytest

from proptech_core.compartido.roles import tablas_a_prestar


def _migracion(
    carpeta: Path, nombre: str, revision: str, anterior: str | None, presta: str
) -> None:
    (carpeta / nombre).write_text(
        f'revision: str = "{revision}"\ndown_revision: str | None = {anterior!r}\n{presta}\n',
        encoding="utf-8",
    )


@pytest.fixture
def versiones(tmp_path: Path) -> Path:
    _migracion(tmp_path, "0001_a.py", "0001", None, "")
    _migracion(
        tmp_path,
        "0002_b.py",
        "0002",
        "0001",
        'PRESTA_PROPIEDAD: tuple[str, ...] = ("evento_de_emision",)',
    )
    _migracion(tmp_path, "0003_c.py", "0003", "0002", "")
    _migracion(
        tmp_path, "0004_d.py", "0004", "0003", 'PRESTA_PROPIEDAD = ("auditoria", "movimiento")'
    )
    return tmp_path


def test_presta_lo_de_las_migraciones_pendientes(versiones: Path) -> None:
    assert tablas_a_prestar(versiones, "0001") == {"evento_de_emision", "auditoria", "movimiento"}


def test_no_presta_lo_de_una_migracion_ya_aplicada(versiones: Path) -> None:
    assert tablas_a_prestar(versiones, "0002") == {"auditoria", "movimiento"}


def test_en_la_cabeza_no_presta_nada(versiones: Path) -> None:
    assert tablas_a_prestar(versiones, "0004") == set()


def test_una_base_sin_version_las_considera_todas_pendientes(versiones: Path) -> None:
    assert tablas_a_prestar(versiones, None) == {"evento_de_emision", "auditoria", "movimiento"}


def test_sin_carpeta_de_migraciones_no_presta_nada(tmp_path: Path) -> None:
    assert tablas_a_prestar(tmp_path / "no_existe", "0001") == set()


def test_una_tabla_que_no_es_protegida_es_un_error(tmp_path: Path) -> None:
    _migracion(tmp_path, "0001_a.py", "0001", None, "")
    _migracion(tmp_path, "0002_b.py", "0002", "0001", 'PRESTA_PROPIEDAD = ("cuenta_comun",)')
    with pytest.raises(ValueError, match="cuenta_comun"):
        tablas_a_prestar(tmp_path, "0001")
