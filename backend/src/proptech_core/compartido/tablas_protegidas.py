"""Declaración única de tablas de sólo agregar (D0 del 4a). Sin infraestructura."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class TablaProtegida:
    mensaje: str
    triggers: frozenset[str]
    verificacion_con_fila: bool = False


TABLAS_DE_SOLO_AGREGAR: Mapping[str, TablaProtegida] = MappingProxyType(
    {
        "auditoria": TablaProtegida(
            "auditoria no admite",
            frozenset({"trg_auditoria_sin_update_delete", "trg_auditoria_sin_truncate"}),
            True,
        ),
        "configuracion_versionada": TablaProtegida(
            "configuracion_versionada no admite",
            frozenset(
                {
                    "trg_configuracion_sin_update_delete",
                    "trg_configuracion_sin_truncate",
                    "trg_configuracion_sin_update_delete_por_sentencia",
                }
            ),
        ),
    }
)
