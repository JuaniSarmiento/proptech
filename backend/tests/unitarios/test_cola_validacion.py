"""Tests unitarios de la validación de `encolar` antes de tocar Redis (D2,
D3 capa 1, D4). Vuelta 3, F8b.

`_validar_clave` sólo rechazaba la clave vacía; ni en blanco (espacios o
saltos de línea: ARQ no la trata como "sin id" pero tampoco identifica nada),
ni más larga que el `CHECK` de `trabajos_hechos` (200 caracteres, migración
0002: una clave más larga encola bien y recién falla mucho después, al
confirmar el efecto), ni no-texto. Tampoco había validación de un dato
llamado `function`, que choca con el parámetro posicional de
`ArqRedis.enqueue_job` y hoy llega como `TypeError` crudo en vez de un error
propio que nombre el campo (D13, L-007).

No usan Redis real: toda esta validación corre en `AdaptadorColaArq.encolar`
antes de crear el pool, así que un host inalcanzable nunca se toca.
"""

from typing import Any

import pytest
from arq.connections import RedisSettings

from proptech_core.compartido.cola import AdaptadorColaArq, ArgumentoNoPermitido

pytestmark = pytest.mark.anyio

#: Nunca se llega a conectar: la validación tiene que fallar antes.
_AJUSTES_SIN_USAR = RedisSettings(host="redis-no-se-usa.invalid", port=1)


async def _encolar(**datos: Any) -> None:
    cola = AdaptadorColaArq(_AJUSTES_SIN_USAR)
    base: dict[str, Any] = {
        "clave": "clave-valida",
        "request_id": "3f2c1a00-0001-4001-8001-000000000001",
    }
    base.update(datos)
    await cola.encolar("tarea_de_prueba", **base)


async def test_clave_vacia_se_rechaza_nombrando_el_campo() -> None:
    with pytest.raises(ArgumentoNoPermitido) as exc_info:
        await _encolar(clave="")
    assert "clave" in str(exc_info.value)


@pytest.mark.parametrize("clave_en_blanco", [" ", "\t", "\n", "   \t\n  "])
async def test_clave_en_blanco_se_rechaza(clave_en_blanco: str) -> None:
    with pytest.raises(ArgumentoNoPermitido) as exc_info:
        await _encolar(clave=clave_en_blanco)
    assert "clave" in str(exc_info.value)


async def test_clave_de_201_caracteres_se_rechaza() -> None:
    """Gemelo del `CHECK (length(clave) BETWEEN 1 AND 200)` de
    `trabajos_hechos` (migración 0002): 200 caracteres está permitido, 201 no."""
    with pytest.raises(ArgumentoNoPermitido) as exc_info:
        await _encolar(clave="c" * 201)
    assert "clave" in str(exc_info.value)


async def test_clave_de_200_caracteres_no_se_rechaza_por_el_largo() -> None:
    """Triangula el test anterior: 200 es el límite, no 201 menos uno por
    error de cálculo. Falla en la conexión (nunca se levanta, el host no
    existe) y no en la validación, así que el error NO es `ArgumentoNoPermitido`."""
    with pytest.raises(Exception) as exc_info:
        await _encolar(clave="c" * 200)
    assert not isinstance(exc_info.value, ArgumentoNoPermitido)


async def test_clave_no_textual_se_rechaza_nombrando_el_campo() -> None:
    with pytest.raises(ArgumentoNoPermitido) as exc_info:
        await _encolar(clave=123)
    assert "clave" in str(exc_info.value)


async def test_dato_llamado_function_se_rechaza_con_error_propio() -> None:
    """Choca con el parámetro posicional de `ArqRedis.enqueue_job`
    (`function`, el nombre de la tarea): hoy llega como `TypeError` crudo de
    "got multiple values for argument". El mensaje tiene que nombrar el
    campo, no ser ese `TypeError`."""
    with pytest.raises(ArgumentoNoPermitido) as exc_info:
        await _encolar(function="otra-tarea")
    assert "function" in str(exc_info.value)
