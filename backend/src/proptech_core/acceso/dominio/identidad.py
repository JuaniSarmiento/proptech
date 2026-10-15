"""La identidad autenticada (D7, cambio 2a).

Sólo dos ids: a qué administración pertenece (el tenant, D4) y quién es la
persona. Las asignaciones de rol de esa persona (D-096) salen siempre de la
base, nunca de este objeto ni del pedido (tarea 5.1 en adelante): acá no hay
ningún campo de rol, a propósito.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Identidad:
    administracion_id: UUID
    persona_id: UUID
