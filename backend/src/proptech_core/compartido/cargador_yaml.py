"""Cargador YAML propio (D6): rechaza claves duplicadas (PyYAML se queda con la
última en silencio) y arma errores con la línea de sintaxis. Lo reutiliza el
lector de parámetros y el de la semilla."""

from __future__ import annotations

from typing import Any

import yaml


class ErrorDeCarga(Exception):
    """El archivo no se pudo leer o el YAML está mal formado."""


# Límite de tamaño del archivo (D6/D10, documentado en design.md): un archivo
# de parámetros o de semilla no tiene por qué superar esto; es una segunda
# barrera, independiente del límite de anidamiento de abajo, contra un
# archivo deliberadamente enorme.
_TAMANIO_MAXIMO_BYTES = 1 * 1024 * 1024  # 1 MiB


class _LoaderSinDuplicados(yaml.SafeLoader):
    """SafeLoader que rechaza claves repetidas en cualquier mapa, a cualquier
    nivel de anidamiento."""


def _construir_mapeo_sin_duplicados(
    loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapeo: dict[Any, Any] = {}
    for clave_nodo, valor_nodo in node.value:
        clave = loader.construct_object(clave_nodo, deep=True)  # type: ignore[no-untyped-call]
        if not isinstance(clave, str):
            # L-009 (constructor, cambio 1b vuelta 4): una clave que no es
            # texto (un entero, un booleano, `null`...) escapaba de maneras
            # distintas según el lector: en `leer_parametros` como un
            # `TypeError` crudo reenviado ("keywords must be strings"), y en
            # `leer_semilla` sin atajar en absoluto (ni siquiera lo envolvía).
            # Se cierra una sola vez, acá, para los dos lectores y para
            # cualquier nivel de anidamiento (este constructor arma todos los
            # mapas, no sólo el de la raíz). El mensaje nombra el tipo y la
            # posición, nunca el valor de la clave ni el de su valor asociado
            # (D13: los mensajes pueden nombrar claves, nunca valores).
            raise ErrorDeCarga(
                "las claves del YAML deben ser texto, no "
                f"{type(clave).__name__} (línea {clave_nodo.start_mark.line + 1}, "
                f"columna {clave_nodo.start_mark.column + 1})"
            )
        if clave in mapeo:
            raise ErrorDeCarga(
                f"clave duplicada: {clave!r} (línea {clave_nodo.start_mark.line + 1})"
            )
        mapeo[clave] = loader.construct_object(  # type: ignore[no-untyped-call]
            valor_nodo, deep=deep
        )
    return mapeo


_LoaderSinDuplicados.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construir_mapeo_sin_duplicados,
)


def cargar_yaml(contenido: bytes) -> dict[Any, Any]:
    """Parsea bytes YAML. Nunca devuelve algo que no sea un mapa."""
    if len(contenido) > _TAMANIO_MAXIMO_BYTES:
        raise ErrorDeCarga(
            f"YAML mal formado: supera el tamaño máximo permitido ({_TAMANIO_MAXIMO_BYTES} bytes)"
        )
    try:
        # _LoaderSinDuplicados hereda de yaml.SafeLoader (no construye objetos
        # arbitrarios): sólo agrega el chequeo de claves duplicadas.
        datos = yaml.load(contenido, Loader=_LoaderSinDuplicados)  # noqa: S506
    except ErrorDeCarga:
        raise
    except RecursionError:
        # Un YAML chico pero muy anidado (listas/mapas dentro de listas/mapas)
        # agota la pila de recursión del parser antes de terminar: sin esto,
        # escapa sin capturar hasta quien llame al lector (rompedor, cambio
        # 1b vuelta 2). No se incluye el contenido ni la traza, igual que el
        # resto de los errores de este módulo.
        raise ErrorDeCarga("YAML mal formado: demasiados niveles de anidamiento") from None
    except MemoryError:
        # Misma familia que RecursionError: otra forma de agotar un recurso
        # del proceso al parsear, que tampoco debe escapar sin control.
        raise ErrorDeCarga("YAML mal formado: agotó la memoria al parsearse") from None
    except yaml.YAMLError as error:
        # Nunca se reenvía `str(error)`: PyYAML lo arma con un snippet de la
        # línea que rompió el parseo (el texto exacto, con un `^` marcando la
        # columna), y ese texto puede ser el contenido de un archivo
        # malformado a propósito (p.ej. un valor secreto mal cerrado). El
        # mensaje nombra sólo la posición y una descripción genérica, nunca
        # el texto de PyYAML (constructor, cambio 1b vuelta 3; L-002).
        marca = getattr(error, "problem_mark", None)
        if marca is not None:
            raise ErrorDeCarga(
                f"YAML mal formado (línea {marca.line + 1}, columna {marca.column + 1})"
            ) from None
        raise ErrorDeCarga("YAML mal formado") from None

    if datos is None:
        raise ErrorDeCarga("YAML mal formado: el archivo está vacío")
    if not isinstance(datos, dict):
        raise ErrorDeCarga(f"la raíz del YAML debe ser un mapa, no {type(datos).__name__}")
    return datos


def leer_archivo(ruta: str) -> bytes:
    try:
        with open(ruta, "rb") as archivo:
            return archivo.read()
    except OSError:
        raise ErrorDeCarga(f"no se puede leer el archivo: {ruta}") from None
