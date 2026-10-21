"""Servidor HTTP falso de Clerk (D7, cambio 2b tarea 5.4, L-027): valida
método, `Authorization`, `Content-Type` y la forma del cuerpo como lo haría
la API real, en vez de aceptar cualquier escritura (L-027). Lo comparten el
unitario del adaptador y el de integración del worker.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

#: `(metodo, ruta, cabeceras, cuerpo) -> (estado, cuerpo_de_respuesta)`.
Manejador = Callable[[str, str, dict[str, str], dict[str, Any] | None], tuple[int, dict[str, Any]]]

CLAVE_DE_PRUEBA = "clave-de-prueba-no-real"


class ServidorClerkFalso:
    """Servidor real en `127.0.0.1` (puerto al azar): cada pedido que pasa
    las validaciones de contrato se delega a `manejador`. `pedidos` guarda
    cada uno tal como llegó, para que el test compruebe lo que el adaptador
    mandó de verdad (cabeceras y cuerpo), nunca lo que el adaptador CREE
    haber mandado."""

    def __init__(self, manejador: Manejador, *, clave_esperada: str = CLAVE_DE_PRUEBA) -> None:
        self.pedidos: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        externo = self

        class _Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: Any) -> None:  # silencioso en los tests
                pass

            def _cuerpo(self) -> bytes:
                largo = int(self.headers.get("Content-Length", 0) or 0)
                return self.rfile.read(largo) if largo else b""

            def _responder(self) -> None:
                crudo = self._cuerpo()
                cuerpo = json.loads(crudo) if crudo else None
                cabeceras = dict(self.headers)
                with externo._lock:
                    externo.pedidos.append(
                        {
                            "metodo": self.command,
                            "ruta": self.path,
                            "cabeceras": cabeceras,
                            "cuerpo": cuerpo,
                        }
                    )
                if cabeceras.get("Authorization") != f"Bearer {clave_esperada}":
                    self._enviar(401, {"errors": [{"message": "no autorizado"}]})
                    return
                if crudo and cabeceras.get("Content-Type") != "application/json":
                    self._enviar(415, {"errors": [{"message": "content-type"}]})
                    return
                estado, cuerpo_respuesta = manejador(self.command, self.path, cabeceras, cuerpo)
                self._enviar(estado, cuerpo_respuesta)

            def _enviar(self, estado: int, cuerpo: dict[str, Any]) -> None:
                datos = json.dumps(cuerpo).encode()
                try:
                    self.send_response(estado)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(datos)))
                    self.end_headers()
                    self.wfile.write(datos)
                except BrokenPipeError, ConnectionResetError:
                    # El cliente de prueba ya cerró la conexión por su
                    # propio plazo (L-001, "no responde"): nada que
                    # devolver, nadie lo está esperando.
                    pass

            def do_POST(self) -> None:
                self._responder()

        self._servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._hilo = threading.Thread(target=self._servidor.serve_forever, daemon=True)

    def __enter__(self) -> ServidorClerkFalso:
        self._hilo.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._servidor.shutdown()
        self._servidor.server_close()

    @property
    def base_url(self) -> str:
        host = str(self._servidor.server_address[0])
        puerto = self._servidor.server_address[1]
        return f"http://{host}:{puerto}"
