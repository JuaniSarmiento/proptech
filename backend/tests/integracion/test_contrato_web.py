"""Guarda del contrato D4 (tarea 3.4): las fixtures de `web/src/lib/api/
fixtures/*.json` se generan desde la API real, nunca a mano (D11 del 3a
descartó "datos falsos en la web" por esto mismo). Compara FORMA (claves y
tipos, nunca ids ni fechas): si la API renombra o agrega un campo, este
test falla antes que la web lo note en producción.

Con `PROPTECH_ACTUALIZAR_FIXTURES=1` reescribe los ocho archivos en vez de
compararlos — sólo para un cambio deliberado del contrato.
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion

_FIXTURES = Path(__file__).resolve().parents[3] / "web" / "src" / "lib" / "api" / "fixtures"
_ACTUALIZAR = os.environ.get("PROPTECH_ACTUALIZAR_FIXTURES") == "1"

#: Las ocho rutas de lectura que usa la web (D1), como sufijo de `api.ruta()`.
#: `None` es `/api/complejos` (sin id), el único caso sin sufijo del edificio.
_RUTAS: dict[str, str | None] = {
    "lista": None,
    "edificio": "",
    "resumen": "/resumen",
    "unidades": "/unidades",
    "grupos": "/grupos",
    "categorias": "/categorias",
    "vigente": "/configuracion",
    "versiones": "/configuracion/versiones",
}


def _tipo(valor: Any) -> str:
    if valor is None:
        return "null"
    if isinstance(valor, bool):
        return "bool"
    if isinstance(valor, int | float):
        return "number"
    if isinstance(valor, str):
        return "string"
    if isinstance(valor, list):
        return "array"
    if isinstance(valor, dict):
        return "object"
    raise TypeError(f"tipo no soportado en la forma del contrato: {type(valor).__name__}")


def _diferencias_de_forma(actual: Any, fixture: Any, camino: str = "<raíz>") -> list[str]:
    """Claves y tipos, recursivo; en un array, la forma de su primer
    elemento (son listas homogéneas en toda ruta de este contrato)."""
    tipo_actual, tipo_fixture = _tipo(actual), _tipo(fixture)
    if tipo_actual != tipo_fixture:
        return [f"{camino}: la API da {tipo_actual}, el fixture esperaba {tipo_fixture}"]
    if tipo_fixture == "object":
        problemas = []
        claves_actual, claves_fixture = set(actual), set(fixture)
        for clave in sorted(claves_fixture - claves_actual):
            problemas.append(f"{camino}.{clave}: está en el fixture y ya no en la respuesta real")
        for clave in sorted(claves_actual - claves_fixture):
            problemas.append(f"{camino}.{clave}: la API lo suma y el fixture todavía no lo tiene")
        for clave in sorted(claves_actual & claves_fixture):
            problemas.extend(
                _diferencias_de_forma(actual[clave], fixture[clave], f"{camino}.{clave}")
            )
        return problemas
    if tipo_fixture == "array" and actual and fixture:
        return _diferencias_de_forma(actual[0], fixture[0], f"{camino}[0]")
    return []


def _verificar_o_actualizar(nombre: str, respuesta: Any) -> None:
    ruta = _FIXTURES / f"{nombre}.json"
    if _ACTUALIZAR:
        ruta.write_text(
            json.dumps(respuesta, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return
    fixture = json.loads(ruta.read_text(encoding="utf-8"))
    problemas = _diferencias_de_forma(respuesta, fixture)
    assert problemas == [], "\n".join(problemas)


@pytest.fixture
def api_con_datos(api_edificio: ApiEdificio) -> ApiEdificio:
    """Algo más que el mínimo de `api_edificio`, para que los fixtures
    cubran lo que la web lee de verdad: un grupo parcial (con su informe,
    D5) y una segunda versión de configuración (con `autor_nombre`, D5
    tarea 2.2)."""
    api = api_edificio
    tercera_unidad = api.cliente.post(
        api.ruta("/unidades"),
        json={
            "identificador": "1C",
            "tipo": "departamento",
            "piso": "1",
            "coeficiente": "0.100000",
            "superficie_m2": "55.00",
        },
    )
    assert tercera_unidad.status_code == 201
    grupo = api.cliente.post(
        api.ruta("/grupos"),
        json={
            "clave": "ascensor",
            "nombre": "Ascensor",
            "metodo": "coeficiente",
            "unidades": [
                {"unidad_id": str(api.unidad)},
                {"unidad_id": tercera_unidad.json()["id"]},
            ],
        },
    )
    assert grupo.status_code == 201
    version = api.cliente.post(
        api.ruta("/configuracion/versiones"),
        json={
            "tasa_mensual": "4.00",
            "dias_de_gracia": 5,
            "forma_de_calculo": "proporcional_por_dia",
            "porcentaje_fondo": "2.00",
            "dia_de_vencimiento": 10,
            "modalidad_de_vencimiento": "unico",
            "vigente_desde": (date.today() + timedelta(days=1)).isoformat(),
        },
    )
    assert version.status_code == 201
    return api


@pytest.mark.parametrize("nombre", sorted(_RUTAS))
def test_forma_de_cada_ruta_que_usa_la_web(api_con_datos: ApiEdificio, nombre: str) -> None:
    api = api_con_datos
    sufijo = _RUTAS[nombre]
    ruta = "/api/complejos" if sufijo is None else api.ruta(sufijo)
    respuesta = api.cliente.get(ruta)
    assert respuesta.status_code == 200
    _verificar_o_actualizar(nombre, respuesta.json())
