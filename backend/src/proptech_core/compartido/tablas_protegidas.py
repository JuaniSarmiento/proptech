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
        "cuenta": TablaProtegida(
            "cuenta no admite",
            frozenset(
                {
                    "trg_cuenta_sin_update_delete",
                    "trg_cuenta_sin_truncate",
                    "trg_cuenta_sin_update_delete_por_sentencia",
                }
            ),
        ),
        "emision": TablaProtegida(
            "emision no admite",
            frozenset(
                {
                    "trg_emision_sin_update_delete",
                    "trg_emision_sin_truncate",
                    "trg_emision_sin_update_delete_por_sentencia",
                }
            ),
        ),
        "evento_de_emision": TablaProtegida(
            "evento_de_emision no admite",
            frozenset(
                {
                    "trg_evento_de_emision_sin_update_delete",
                    "trg_evento_de_emision_sin_truncate",
                    "trg_evento_de_emision_sin_update_delete_por_sentencia",
                }
            ),
        ),
        "obligacion": TablaProtegida(
            "obligacion no admite",
            frozenset(
                {
                    "trg_obligacion_sin_update_delete",
                    "trg_obligacion_sin_truncate",
                    "trg_obligacion_sin_update_delete_por_sentencia",
                }
            ),
        ),
        "movimiento": TablaProtegida(
            "movimiento no admite",
            frozenset(
                {
                    "trg_movimiento_sin_update_delete",
                    "trg_movimiento_sin_truncate",
                    "trg_movimiento_sin_update_delete_por_sentencia",
                }
            ),
        ),
        "imputacion": TablaProtegida(
            "imputacion no admite",
            frozenset(
                {
                    "trg_imputacion_sin_update_delete",
                    "trg_imputacion_sin_truncate",
                    "trg_imputacion_sin_update_delete_por_sentencia",
                }
            ),
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
