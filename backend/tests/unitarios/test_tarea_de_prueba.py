"""Tests unitarios de la tarea de prueba y su modelo de argumentos (D3).
Cambio 1c, tarea 5.4.

Escenarios de `cola-de-trabajos`: Cantidad de fallas fuera de rango; Sin ruta
pública para la tarea de prueba. Lecciones: L-008 (coincidencia completa:
acá, el tipo exacto del valor, sin coerción).
"""

import uuid
from pathlib import Path
from typing import Any

import pytest

from proptech_core.compartido.cola import ResultadoEncolado
from proptech_worker.tareas import ArgumentoDeTareaInvalido, encolar_tarea_de_prueba

pytestmark = pytest.mark.anyio

RAIZ_SRC = Path(__file__).resolve().parents[2] / "src" / "proptech_api"


class _ColaFalsa:
    def __init__(self) -> None:
        self.llamadas: list[dict[str, Any]] = []

    async def encolar(
        self, tarea: str, *, clave: str, request_id: str, **datos: Any
    ) -> ResultadoEncolado:
        self.llamadas.append({"tarea": tarea, "clave": clave, "request_id": request_id, **datos})
        return ResultadoEncolado.ENCOLADO


@pytest.mark.parametrize("fallar_veces", [-1, 11, "3", True, 2.5])
async def test_fallar_veces_invalido_se_rechaza_sin_encolar_nada(fallar_veces: object) -> None:
    cola = _ColaFalsa()
    with pytest.raises(ArgumentoDeTareaInvalido) as exc_info:
        await encolar_tarea_de_prueba(
            cola,
            clave=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            fallar_veces=fallar_veces,
        )
    assert "fallar_veces" in str(exc_info.value)
    assert cola.llamadas == []


@pytest.mark.parametrize("fallar_veces", [0, 10])
async def test_fallar_veces_en_el_rango_se_acepta(fallar_veces: int) -> None:
    cola = _ColaFalsa()
    clave = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    resultado = await encolar_tarea_de_prueba(
        cola,
        clave=clave,
        request_id=request_id,
        fallar_veces=fallar_veces,
    )
    assert resultado is ResultadoEncolado.ENCOLADO
    assert cola.llamadas == [
        {
            "tarea": "tarea_de_prueba",
            "clave": clave,
            "request_id": request_id,
            "fallar_veces": fallar_veces,
        }
    ]


def test_ninguna_ruta_de_la_api_menciona_la_tarea_de_prueba() -> None:
    """Ninguna ruta pública de `crear_app()` permite encolar la tarea de
    prueba (D3): sólo se encola desde código o desde el comando dentro del
    contenedor (tarea 5.11)."""
    ofensores = [
        str(archivo.relative_to(RAIZ_SRC))
        for archivo in RAIZ_SRC.rglob("*.py")
        if "tarea_de_prueba" in archivo.read_text(encoding="utf-8")
    ]
    assert not ofensores, f"la API menciona la tarea de prueba en: {ofensores}"
