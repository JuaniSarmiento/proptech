"""2.1: el lector de `config/georef/` (D1) — archivo ausente, vacío, truncado,
de otro tipo, con id repetido, con un padre que no existe, y el caso verde
(Mendoza con id oficial `50`, 24 jurisdicciones). Ningún error repite el
contenido del archivo (L-002, L-007, L-008)."""

import json
from pathlib import Path
from typing import Any

import pytest

from proptech_core.compartido.georef import GeorefInvalido, leer_georef

_SECRETO = "no-debería-aparecer-en-ningún-mensaje-de-error"


def _escribir(directorio: Path, **archivos: Any) -> None:
    for nombre, contenido in archivos.items():
        ruta = directorio / nombre
        if isinstance(contenido, bytes):
            ruta.write_bytes(contenido)
        else:
            ruta.write_text(json.dumps(contenido), encoding="utf-8")


def _archivos_validos() -> dict[str, Any]:
    return {
        "provincias.json": [
            {"id": "50", "nombre": "Mendoza"},
            {"id": "06", "nombre": "Buenos Aires"},
        ],
        "departamentos.json": [{"id": "50007", "nombre": "Capital", "provincia_id": "50"}],
        "localidades.json": [{"id": "50007010", "nombre": "Mendoza", "departamento_id": "50007"}],
    }


def test_archivo_ausente_falla_al_arrancar_nombrando_el_archivo(tmp_path: Path) -> None:
    _escribir(
        tmp_path, **{k: v for k, v in _archivos_validos().items() if k != "departamentos.json"}
    )
    with pytest.raises(GeorefInvalido) as excinfo:
        leer_georef(str(tmp_path))
    assert "departamentos.json" in str(excinfo.value)
    assert _SECRETO not in str(excinfo.value)


def test_archivo_vacio_falla_nombrando_el_archivo(tmp_path: Path) -> None:
    datos = _archivos_validos()
    _escribir(tmp_path, **{**datos, "provincias.json": b""})
    with pytest.raises(GeorefInvalido) as excinfo:
        leer_georef(str(tmp_path))
    assert "provincias.json" in str(excinfo.value)


def test_archivo_truncado_falla_sin_repetir_el_contenido(tmp_path: Path) -> None:
    contenido_malo = b'[{"id": "50", "nombre": "' + _SECRETO.encode("utf-8")
    datos = _archivos_validos()
    _escribir(tmp_path, **{**datos, "provincias.json": contenido_malo})
    with pytest.raises(GeorefInvalido) as excinfo:
        leer_georef(str(tmp_path))
    assert "provincias.json" in str(excinfo.value)
    assert _SECRETO not in str(excinfo.value)


def test_archivo_de_otro_tipo_falla(tmp_path: Path) -> None:
    datos = _archivos_validos()
    _escribir(tmp_path, **{**datos, "provincias.json": {"no": "es una lista"}})
    with pytest.raises(GeorefInvalido) as excinfo:
        leer_georef(str(tmp_path))
    assert "provincias.json" in str(excinfo.value)


def test_id_repetido_falla(tmp_path: Path) -> None:
    datos = _archivos_validos()
    datos["provincias.json"] = [
        {"id": "50", "nombre": "Mendoza"},
        {"id": "50", "nombre": "Otra"},
    ]
    _escribir(tmp_path, **datos)
    with pytest.raises(GeorefInvalido) as excinfo:
        leer_georef(str(tmp_path))
    assert "provincias.json" in str(excinfo.value)


def test_padre_inexistente_falla(tmp_path: Path) -> None:
    datos = _archivos_validos()
    datos["departamentos.json"] = [{"id": "50007", "nombre": "Capital", "provincia_id": "99"}]
    _escribir(tmp_path, **datos)
    with pytest.raises(GeorefInvalido) as excinfo:
        leer_georef(str(tmp_path))
    assert "departamentos.json" in str(excinfo.value)


def test_mendoza_existe_con_su_id_oficial_y_hay_24_jurisdicciones() -> None:
    raiz = Path(__file__).resolve().parents[3] / "config" / "georef"
    georef = leer_georef(str(raiz))
    provincias = georef.listar_provincias()
    assert len(provincias) == 24
    mendoza = next(p for p in provincias if p.id == "50")
    assert mendoza.nombre == "Mendoza"


def test_departamentos_de_una_provincia_inexistente_devuelve_none(tmp_path: Path) -> None:
    _escribir(tmp_path, **_archivos_validos())
    georef = leer_georef(str(tmp_path))
    assert georef.departamentos_de("99") is None


def test_localidades_de_un_departamento_inexistente_devuelve_none(tmp_path: Path) -> None:
    _escribir(tmp_path, **_archivos_validos())
    georef = leer_georef(str(tmp_path))
    assert georef.localidades_de("99999") is None


def test_existe_el_trio_coherente(tmp_path: Path) -> None:
    _escribir(tmp_path, **_archivos_validos())
    georef = leer_georef(str(tmp_path))
    assert georef.existe_el_trio("50", "50007", "50007010") is True


def test_existe_el_trio_incoherente_es_falso(tmp_path: Path) -> None:
    datos = _archivos_validos()
    datos["departamentos.json"].append(
        {"id": "06840", "nombre": "La Matanza", "provincia_id": "06"}
    )
    datos["localidades.json"].append(
        {"id": "0684001001", "nombre": "La Matanza", "departamento_id": "06840"}
    )
    _escribir(tmp_path, **datos)
    georef = leer_georef(str(tmp_path))
    # La localidad existe, pero bajo otro departamento que el pedido.
    assert georef.existe_el_trio("50", "50007", "0684001001") is False
