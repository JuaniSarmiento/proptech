"""Lo que `liquidacion` pide a la infraestructura: la cola de trabajos (D4 del 1c), vista desde
quien encola. `AdaptadorColaArq` (en `compartido`) la cumple por duck typing."""

from typing import Any, Protocol

from proptech_core.compartido.cola import ResultadoEncolado


class ColaDeDocumentos(Protocol):
    async def encolar(
        self,
        tarea: str,
        *,
        clave: str,
        request_id: str,
        expira_en_s: int | None = None,
        **datos: Any,
    ) -> ResultadoEncolado: ...
