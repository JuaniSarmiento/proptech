"""Comando para encolar la tarea de prueba desde la línea de comandos (D3).
Cambio 1c, tarea 5.11.

`python -m proptech_worker.prueba encolar --fallar-veces N`: sólo se corre
desde código o dentro del contenedor (lo usa el humo del cambio 1d); ninguna
ruta pública de la API permite encolar la tarea de prueba (tarea 5.4).

`tarea_de_prueba_con_administracion` (D4, D8, cambio 2a, tarea 7.1) es la
tarea de prueba del tenant del worker: cuenta los complejos visibles con el
`administracion_id` que recibe, validado por `con_administracion_de_tarea`
antes de llegar acá. Tampoco tiene ruta pública: sólo la usan los tests de
la 7.1, que la invocan directo con un `ctx` armado a mano.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from typing import Any

from sqlalchemy import text

from proptech_core.compartido.base_de_datos import abrir_sesion
from proptech_core.compartido.cola import AdaptadorColaArq, ColaNoDisponible
from proptech_core.compartido.reintentos import reintentable
from proptech_core.compartido.seguimiento import con_seguimiento_de_tarea
from proptech_core.compartido.tenant_de_tarea import con_administracion_de_tarea
from proptech_worker.tareas import ArgumentoDeTareaInvalido, encolar_tarea_de_prueba

#: Nombre tal como queda registrado en ARQ si algún día se la registra en un
#: `AjustesDelWorker` (hoy no: es sólo de test, D4, D8, tarea 7.1).
NOMBRE_TAREA_DE_PRUEBA_CON_ADMINISTRACION = "tarea_de_prueba_con_administracion"


def _contar_complejos(fabrica: Any, *, administracion_id: uuid.UUID) -> int:
    """Corre en un hilo (`asyncio.to_thread`, D4, L-015): el tenant viaja en
    `session.info`, no en una `ContextVar`, así que no depende de qué hilo
    abre o usa la sesión."""
    sesion = abrir_sesion(fabrica, administracion_id)
    try:
        return int(sesion.execute(text("SELECT count(*) FROM complejo")).scalar_one())
    finally:
        sesion.close()


@con_seguimiento_de_tarea
@con_administracion_de_tarea
@reintentable
async def tarea_de_prueba_con_administracion(
    ctx: dict[str, Any],
    *,
    request_id: str,
    administracion_id: uuid.UUID,
    clave: str | None = None,
    **datos: Any,
) -> int:
    """Cuenta los complejos de `administracion_id` (D8). `con_administracion_
    de_tarea` ya validó y convirtió el argumento a `UUID`, y le agregó el
    `administracion_id` adelante de `clave` si vino una (E3: `trabajos_hechos`
    tiene una sola clave global)."""
    del datos
    fabrica = ctx["fabrica_de_sesiones"]
    return await asyncio.to_thread(_contar_complejos, fabrica, administracion_id=administracion_id)


async def _encolar(fallar_veces: int) -> int:
    from proptech_worker.ajustes import AjustesDelWorker

    clave = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    cola = AdaptadorColaArq(AjustesDelWorker.redis_settings)
    try:
        await encolar_tarea_de_prueba(
            cola, clave=clave, request_id=request_id, fallar_veces=fallar_veces
        )
    except ArgumentoDeTareaInvalido as error:
        print(str(error), file=sys.stderr)
        return 1
    except ColaNoDisponible as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"clave={clave}")
    print(f"request_id={request_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m proptech_worker.prueba")
    subparsers = parser.add_subparsers(dest="comando", required=True)
    encolar_parser = subparsers.add_parser("encolar")
    encolar_parser.add_argument("--fallar-veces", dest="fallar_veces", type=int, required=True)

    args = parser.parse_args(argv)
    if args.comando == "encolar":
        return asyncio.run(_encolar(args.fallar_veces))
    parser.error(f"comando desconocido: {args.comando}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
