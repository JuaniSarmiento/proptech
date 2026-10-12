"""4.1: el cargador YAML propio rechaza claves duplicadas y arma errores claros (D6)."""

from pathlib import Path

import pytest


def test_clave_duplicada_en_la_raiz_falla_nombrandola(tmp_path: Path) -> None:
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml

    ruta = tmp_path / "dup.yaml"
    ruta.write_text("a: 1\na: 2\n")

    with pytest.raises(ErrorDeCarga) as exc_info:
        cargar_yaml(ruta.read_bytes())

    assert "a" in str(exc_info.value)


def test_clave_duplicada_anidada_falla_nombrandola(tmp_path: Path) -> None:
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml

    ruta = tmp_path / "dup_anidada.yaml"
    ruta.write_text("raiz:\n  x: 1\n  x: 2\n")

    with pytest.raises(ErrorDeCarga) as exc_info:
        cargar_yaml(ruta.read_bytes())

    assert "x" in str(exc_info.value)


def test_yaml_mal_formado_falla_con_linea(tmp_path: Path) -> None:
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml

    ruta = tmp_path / "roto.yaml"
    ruta.write_text("a: [1, 2\n")  # corchete sin cerrar

    with pytest.raises(ErrorDeCarga) as exc_info:
        cargar_yaml(ruta.read_bytes())

    mensaje = str(exc_info.value).lower()
    assert "mal formado" in mensaje
    assert any(c.isdigit() for c in mensaje)


def test_archivo_vacio_falla_con_mal_formado() -> None:
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml

    with pytest.raises(ErrorDeCarga) as exc_info:
        cargar_yaml(b"")

    assert "mal formado" in str(exc_info.value).lower()


def test_raiz_que_no_es_mapa_falla() -> None:
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml

    with pytest.raises(ErrorDeCarga):
        cargar_yaml(b"- 1\n- 2\n")

    with pytest.raises(ErrorDeCarga):
        cargar_yaml(b"solo un texto\n")


def test_archivo_inexistente_falla(tmp_path: Path) -> None:
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, leer_archivo

    ruta = tmp_path / "no-existe.yaml"

    with pytest.raises(ErrorDeCarga) as exc_info:
        leer_archivo(str(ruta))

    assert "no se puede leer" in str(exc_info.value).lower()


def test_archivo_sin_permiso_de_lectura_falla(tmp_path: Path) -> None:
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, leer_archivo

    ruta = tmp_path / "sin-permiso.yaml"
    ruta.write_text("version: 1\n")
    ruta.chmod(0o000)
    try:
        with pytest.raises(ErrorDeCarga) as exc_info:
            leer_archivo(str(ruta))
        assert "no se puede leer" in str(exc_info.value).lower()
    finally:
        ruta.chmod(0o644)


def test_mapa_valido_sin_duplicados_carga_bien() -> None:
    from proptech_core.compartido.cargador_yaml import cargar_yaml

    datos = cargar_yaml(b"a: 1\nb:\n  c: 2\n")
    assert datos == {"a": 1, "b": {"c": 2}}
