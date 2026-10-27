"""Georef real, cargado una sola vez, para que los tests de `crear_edificio`
y de la API de edificios no repitan fixtures sintéticos (D2, tarea 2.6).
Ids confirmados contra `config/georef/` el 26/10/2026."""

from pathlib import Path

from proptech_core.compartido.georef import leer_georef

_RAIZ = Path(__file__).resolve().parents[3] / "config" / "georef"
GEOREF = leer_georef(str(_RAIZ))

PROVINCIA_MENDOZA = "50"
DEPARTAMENTO_CAPITAL = "50007"
LOCALIDAD_MENDOZA = "50007010"
DEPARTAMENTO_GODOY_CRUZ = "50021"
LOCALIDAD_GODOY_CRUZ = "5002101001"
