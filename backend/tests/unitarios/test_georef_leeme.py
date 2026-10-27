"""1.2: `config/georef/LEEME.md` declara procedencia (escenario "Procedencia
declarada" de `ubicacion-del-edificio`): fuente, fecha de descarga, licencia
CC BY 4.0 y el comando exacto que regenera el dato."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3] / "config" / "georef"


def test_leeme_declara_fuente_fecha_licencia_y_comando() -> None:
    texto = (RAIZ / "LEEME.md").read_text(encoding="utf-8")
    assert "Georef" in texto
    assert "26/10/2026" in texto
    assert "CC BY 4.0" in texto
    assert "curl" in texto


def test_los_tres_archivos_de_datos_existen() -> None:
    for nombre in ("provincias.json", "departamentos.json", "localidades.json"):
        assert (RAIZ / nombre).exists()
