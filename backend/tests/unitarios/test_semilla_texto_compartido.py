"""Frente 2, familia de `texto.py` (L-009, el gemelo): la semilla valida
los mismos identificadores que la API pero sin `recortado_sin_control`.
No usa Docker."""

import json
from pathlib import Path

import pytest

from proptech_core.compartido.parametros import leer_parametros
from proptech_core.compartido.semilla import SemillaInvalida, leer_semilla

RAIZ = Path(__file__).resolve().parents[3]
EJEMPLO = (RAIZ / "config" / "semilla" / "edificio-ejemplo.yaml").read_text()


@pytest.mark.parametrize(
    ("viejo", "nuevo"),
    [
        ('identificador: "1B",', 'identificador: "1A ",'),
        ('identificador: "1B",', 'identificador: "1A\\u0000",'),
    ],
    ids=["1A_con_espacio_duplica_1A", "nul_en_identificador"],
)
def test_semilla_aplica_la_misma_regla_de_texto_que_la_api(
    tmp_path: Path, viejo: str, nuevo: str
) -> None:
    """R3A-6: para la API "1A " y "1A" son la MISMA unidad (409); para la
    semilla son dos unidades distintas y válidas. R3A-1: la API rechaza
    U+0000; la semilla lo acepta y la falla queda para la carga en la base
    (7.2, que pasó al 3b)."""
    assert EJEMPLO.count(viejo) == 1
    contenido = EJEMPLO.replace(viejo, nuevo).replace('"1B", "2A"', '"2A"')
    ruta = tmp_path / "semilla.yaml"
    ruta.write_text(contenido)
    parametros = leer_parametros(str(RAIZ / "config" / "parametros.yaml"))
    with pytest.raises(SemillaInvalida):
        leer_semilla(str(ruta), parametros)


@pytest.mark.parametrize("caracter", ["\u200b", "\u034f", "\ue000", "\u2028"])
def test_semilla_rechaza_unicode_inseguro(tmp_path: Path, caracter: str) -> None:
    ruta = tmp_path / "semilla.yaml"
    # Sin referencias colgantes: el rechazo sólo puede venir de la regla de texto.
    contenido = EJEMPLO.replace(
        'identificador: "1B",', "identificador: " + json.dumps("1B" + caracter) + ","
    ).replace('"1B", "2A"', '"2A"')
    assert contenido != EJEMPLO
    ruta.write_text(contenido)
    parametros = leer_parametros(str(RAIZ / "config" / "parametros.yaml"))
    with pytest.raises(SemillaInvalida):
        leer_semilla(str(ruta), parametros)


def test_semilla_recorta_identificadores_y_referencias_de_grupos(tmp_path: Path) -> None:
    ruta = tmp_path / "semilla.yaml"
    ruta.write_text(EJEMPLO.replace('"1A"', '" 1A "'))
    parametros = leer_parametros(str(RAIZ / "config" / "parametros.yaml"))
    semilla = leer_semilla(str(ruta), parametros)
    assert any(u.identificador == "1A" for u in semilla.unidades)
    assert all(u.identificador == u.identificador.strip() for u in semilla.unidades)
    ascensor = semilla.grupos["ascensor"]
    assert not isinstance(ascensor, str)
    assert any(m.identificador == "1A" for m in ascensor.unidades)
