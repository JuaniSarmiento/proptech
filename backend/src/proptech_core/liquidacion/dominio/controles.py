"""Controles antes de emitir (R34, E6, D-157): el nivel, el orden y el detalle de cada uno.

Puro: recibe lo que ya leyeron los módulos dueños y devuelve la lista; no escribe ni lee nada."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from proptech_core.compartido.dinero import Dinero


@dataclass(frozen=True)
class InformeDeGrupo:
    grupo_id: str
    nombre: str
    suma: str
    diferencia: str
    estado: str


@dataclass(frozen=True)
class BloqueDeGrupo:
    grupo_id: str
    nombre: str
    bloque: str
    importe: Dinero


@dataclass(frozen=True)
class ContextoDeControles:
    estado_migracion: str = "confirmada"
    informes: Sequence[InformeDeGrupo] = ()
    modalidad_de_vencimiento: str = "unico"
    gastos_en_revision: Sequence[str] = ()
    gastos_sin_ia: Sequence[str] = ()
    categorias_faltantes: Sequence[tuple[str, str]] = ()


_CERO = Dinero("0.00")
_ESTADOS_CERRADOS = ("confirmada", "sin_saldos_previos")


def _cantidad(n: int, singular: str, plural: str) -> str:
    return f"Hay {n} {singular if n == 1 else plural}"


def controles_de(
    contexto: ContextoDeControles, bloques: Sequence[BloqueDeGrupo]
) -> list[dict[str, Any]]:
    """Los controles activos, en el orden fijo de E6: duros, bloqueantes y advertencias. Sólo el
    7 construye estos siete: factura duplicada la garantiza `uq_gasto_factura` (R34, D-157)."""
    controles: list[dict[str, Any]] = []

    def agregar(codigo: str, nivel: str, mensaje: str, detalle: dict[str, Any]) -> None:
        controles.append({"codigo": codigo, "nivel": nivel, "mensaje": mensaje, "detalle": detalle})

    if contexto.estado_migracion not in _ESTADOS_CERRADOS:
        agregar(
            "saldos_iniciales_sin_validar",
            "duro",
            "Faltan validar los saldos iniciales del edificio",
            {"estado_migracion": contexto.estado_migracion},
        )
    fuera = [i for i in contexto.informes if i.estado == "fuera_de_tolerancia"]
    if fuera:
        agregar(
            "coeficientes_fuera_de_tolerancia",
            "duro",
            "Los coeficientes de "
            + ", ".join(i.nombre for i in fuera)
            + " no suman 1 dentro de la tolerancia",
            {
                "grupos": [
                    {
                        "grupo_id": i.grupo_id,
                        "nombre": i.nombre,
                        "suma": i.suma,
                        "diferencia": i.diferencia,
                    }
                    for i in fuera
                ]
            },
        )
    negativos = [b for b in bloques if b.importe < _CERO]
    if negativos:
        agregar(
            "bloque_negativo",
            "duro",
            "Un bloque de gastos da negativo en "
            + ", ".join(f"{b.nombre} ({b.bloque})" for b in negativos),
            {
                "bloques": [
                    {
                        "grupo_id": b.grupo_id,
                        "nombre": b.nombre,
                        "bloque": b.bloque,
                        "importe": b.importe.a_texto(),
                    }
                    for b in negativos
                ]
            },
        )
    if contexto.modalidad_de_vencimiento == "doble":
        agregar(
            "doble_vencimiento_sin_regla",
            "duro",
            "El edificio tiene doble vencimiento y todavía no hay regla para calcularlo",
            {"modalidad": "doble"},
        )
    if contexto.gastos_en_revision:
        n = len(contexto.gastos_en_revision)
        agregar(
            "gastos_en_revision",
            "bloqueante",
            _cantidad(n, "factura leída con alertas", "facturas leídas con alertas"),
            {"cantidad": n, "gastos": list(contexto.gastos_en_revision)},
        )
    if contexto.gastos_sin_ia:
        n = len(contexto.gastos_sin_ia)
        agregar(
            "gastos_sin_ia",
            "advertencia",
            _cantidad(n, "factura sin cargar", "facturas sin cargar"),
            {"cantidad": n, "gastos": list(contexto.gastos_sin_ia)},
        )
    if contexto.categorias_faltantes:
        agregar(
            "gasto_mensual_obligatorio_faltante",
            "advertencia",
            "Falta el gasto mensual obligatorio de "
            + ", ".join(nombre for _, nombre in contexto.categorias_faltantes),
            {
                "categorias": [
                    {"categoria_id": i, "nombre": nombre}
                    for i, nombre in contexto.categorias_faltantes
                ]
            },
        )
    return controles
