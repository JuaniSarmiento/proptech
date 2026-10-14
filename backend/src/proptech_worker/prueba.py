"""Comando para encolar la tarea de prueba desde la línea de comandos (D3).
Cambio 1c, tarea 5.11.

`python -m proptech_worker.prueba encolar --fallar-veces N`: sólo se corre
desde código o dentro del contenedor (lo usa el humo del cambio 1d); ninguna
ruta pública de la API permite encolar la tarea de prueba (tarea 5.4).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from proptech_core.compartido.cola import AdaptadorColaArq, ColaNoDisponible
from proptech_worker.tareas import ArgumentoDeTareaInvalido, encolar_tarea_de_prueba


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
