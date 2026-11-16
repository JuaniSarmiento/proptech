"""Declaración única de tablas de sólo agregar (D0 del 4a). Sin infraestructura."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class TablaProtegida:
    mensaje: str
    triggers: frozenset[str]
    verificacion_con_fila: bool = False


def _con_tres_triggers(tabla: str) -> TablaProtegida:
    """El patrón del libro desde `0035`: un trigger por fila, por TRUNCATE y por sentencia."""
    return TablaProtegida(
        f"{tabla} no admite",
        frozenset(
            {
                f"trg_{tabla}_sin_update_delete",
                f"trg_{tabla}_sin_truncate",
                f"trg_{tabla}_sin_update_delete_por_sentencia",
            }
        ),
    )


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
        "tramo_de_interes": TablaProtegida(
            "tramo_de_interes no admite",
            frozenset(
                {
                    "trg_tramo_de_interes_sin_update_delete",
                    "trg_tramo_de_interes_sin_truncate",
                    "trg_tramo_de_interes_sin_update_delete_por_sentencia",
                }
            ),
        ),
        "carga_de_saldo_inicial": TablaProtegida(
            "carga_de_saldo_inicial no admite",
            frozenset(
                {
                    "trg_carga_de_saldo_inicial_sin_update_delete",
                    "trg_carga_de_saldo_inicial_sin_truncate",
                    "trg_carga_de_saldo_inicial_sin_update_delete_por_sentencia",
                }
            ),
        ),
        "origen_de_saldo_inicial": TablaProtegida(
            "origen_de_saldo_inicial no admite",
            frozenset(
                {
                    "trg_origen_de_saldo_inicial_sin_update_delete",
                    "trg_origen_de_saldo_inicial_sin_truncate",
                    "trg_origen_de_saldo_inicial_sin_update_delete_por_sentencia",
                }
            ),
        ),
        "aceptacion_de_diferencias": TablaProtegida(
            "aceptacion_de_diferencias no admite",
            frozenset(
                {
                    "trg_aceptacion_de_diferencias_sin_update_delete",
                    "trg_aceptacion_de_diferencias_sin_truncate",
                    "trg_aceptacion_de_diferencias_sin_update_delete_por_sentencia",
                }
            ),
        ),
        "ajuste_de_saldo_inicial": TablaProtegida(
            "ajuste_de_saldo_inicial no admite",
            frozenset(
                {
                    "trg_ajuste_de_saldo_inicial_sin_update_delete",
                    "trg_ajuste_de_saldo_inicial_sin_truncate",
                    "trg_ajuste_de_saldo_inicial_sin_update_delete_por_sentencia",
                }
            ),
        ),
        # 7, H-013 (`0041`): lo emitido, guardado tal como se usó.
        **{
            tabla: _con_tres_triggers(tabla)
            for tabla in (
                "liquidacion",
                "categoria_de_liquidacion",
                "grupo_de_liquidacion",
                "composicion_de_grupo",
                "linea_de_liquidacion",
                "alerta_aceptada",
            )
        },
        # 7, H-014 (`0042`): el cargo cobrado de menos, con su motivo y su origen.
        "cargo_cobrado_de_menos": _con_tres_triggers("cargo_cobrado_de_menos"),
        # 7, H-015 (`0043`): el PDF archivado de la expensa. Su documento cambia de estado y no es
        # de sólo agregar; los bytes sí, y no se reescriben nunca (CCyC art. 2067 inc. i).
        "pdf_de_expensa": _con_tres_triggers("pdf_de_expensa"),
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
