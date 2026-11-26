"""D6 del design: el caso de uso de importación no sabe que existe Excel.
Un puerto con filas ya tipadas; el adaptador real vive en `adaptadores/`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class FilaCargoImportada:
    """Una fila de la planilla, cruda (sin validar contra el padrón ni
    contra el formato de `Dinero`): eso lo hace el caso de uso, una sola
    vez, para juntar TODOS los errores (D6) en vez de abortar en la
    primera."""

    numero_de_fila: int
    unidad_identificador: str | None
    concepto: str | None
    importe: str | None


class LectorDePlanillaDeCargos(Protocol):
    def leer(self, contenido: bytes) -> list[FilaCargoImportada]: ...


class LectorDeQr(Protocol):
    """H-036 (D-169): los textos de los QR de una factura, imagen (`jpeg`, `png`) o PDF (`pdf`, sólo
    su primera página). Una lista vacía si no hay ninguno o el archivo no se puede abrir: nunca
    levanta."""

    def leer(self, contenido: bytes, tipo: str) -> list[str]: ...


@dataclass(frozen=True)
class LecturaDeIa:
    """Lo que devuelve una llamada al lector de IA: la propuesta (sin validar: viene de un modelo) y
    el uso que costó. `costo` son dólares, decimal en texto."""

    propuesta: Any
    modelo: str
    tokens_entrada: int
    tokens_salida: int
    costo: str


class LectorDeFacturaConIa(Protocol):
    """H-037 (D-169): lee el archivo de una factura y propone concepto, período, categoría, grupo e
    importe. Al proveedor sólo le llegan el archivo y los nombres de las categorías y los grupos
    activos del edificio (`{"id", "nombre"}`): nunca el edificio ni personas. Puede lanzar cualquier
    excepción; una puede traer `tokens_entrada`, `tokens_salida` y `costo` (lo gastado antes de
    fallar)."""

    modelo: str

    def leer(
        self,
        contenido: bytes,
        tipo: str,
        *,
        categorias: Sequence[Mapping[str, str]],
        grupos: Sequence[Mapping[str, str]],
    ) -> LecturaDeIa: ...


class ColaDeLecturas(Protocol):
    async def encolar(
        self,
        tarea: str,
        *,
        clave: str,
        request_id: str,
        expira_en_s: int | None = None,
        **datos: Any,
    ) -> Any: ...
