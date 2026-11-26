"""Leer los pagos informados (E2, E4): el estado sale de los eventos, nunca de una columna.

El personal con `confirmar_pago_informado` ve todos los del edificio; un vecino, los que tienen
alguna parte en una de sus unidades, y de ellos sólo las partes de sus unidades. Un pago que no se
puede ver es lo mismo que uno que no existe: nada lo distingue (404).
"""

from collections import defaultdict
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.complejos.aplicacion.lectura import identificadores_de_unidades
from proptech_core.cuenta_corriente.aplicacion.ubicacion_de_pago import unidades_vigentes
from proptech_core.cuenta_corriente.aplicacion.vision_del_vecino import (
    importe_imputado_sin_extraordinaria,
)
from proptech_core.pagos.dominio.estado import estado_del_pago

_CON_MOTIVO = frozenset({"rechazado", "revertido"})


def _filas_de_pagos(
    sesion: Session, complejo_id: UUID, unidades: frozenset[UUID] | None, pago_id: UUID | None
) -> list[Any]:
    return list(
        sesion.execute(
            text(
                "SELECT p.id, p.comprobante_id, p.banco, p.numero_de_operacion, "
                "p.fecha_de_transferencia, p.monto::text AS monto, p.informado_por, "
                "p.informado_en FROM pago_informado p WHERE p.complejo_id = :c "
                "AND (CAST(:pago AS uuid) IS NULL OR p.id = CAST(:pago AS uuid)) "
                "AND (CAST(:propias AS uuid[]) IS NULL OR EXISTS (SELECT 1 FROM parte_de_pago x "
                "WHERE x.pago_id = p.id AND x.unidad_id = ANY(CAST(:propias AS uuid[])))) "
                "ORDER BY p.informado_en DESC, p.id"
            ),
            {
                "c": complejo_id,
                "pago": None if pago_id is None else str(pago_id),
                "propias": None if unidades is None else [str(u) for u in unidades],
            },
        ).all()
    )


def _eventos(sesion: Session, pagos: Sequence[UUID]) -> dict[UUID, list[tuple[str, str | None]]]:
    eventos: dict[UUID, list[tuple[str, str | None]]] = defaultdict(list)
    filas = sesion.execute(
        text(
            "SELECT pago_id, tipo, motivo FROM evento_de_pago "
            "WHERE pago_id = ANY(CAST(:ids AS uuid[])) ORDER BY registrado_en, id"
        ),
        {"ids": [str(p) for p in pagos]},
    )
    for fila in filas:
        eventos[UUID(str(fila.pago_id))].append((str(fila.tipo), fila.motivo))
    return eventos


def _vigentes_por_pago(sesion: Session, pagos: Sequence[UUID]) -> dict[tuple[UUID, UUID], UUID]:
    """`{(pago, unidad de la parte): unidad donde está hoy su plata}`, según el libro (H-026).
    Una parte que nunca se reimputó queda en su propia unidad."""
    filas = sesion.execute(
        text(
            "SELECT pago_id, movimiento_id FROM movimiento_de_pago "
            "WHERE pago_id = ANY(CAST(:ids AS uuid[])) AND papel IN ('pago', 'reimputacion')"
        ),
        {"ids": [str(p) for p in pagos]},
    ).all()
    por_pago: dict[UUID, list[UUID]] = defaultdict(list)
    for fila in filas:
        por_pago[UUID(str(fila.pago_id))].append(UUID(str(fila.movimiento_id)))
    return {
        (pago, origen): vigente
        for pago, movimientos in por_pago.items()
        for origen, vigente in unidades_vigentes(sesion, movimientos).items()
    }


def _partes(
    sesion: Session, pagos: Sequence[UUID], unidades: frozenset[UUID] | None
) -> dict[UUID, list[dict[str, str]]]:
    filas = sesion.execute(
        text(
            "SELECT pago_id, unidad_id, importe::text AS importe FROM parte_de_pago "
            "WHERE pago_id = ANY(CAST(:ids AS uuid[])) ORDER BY id"
        ),
        {"ids": [str(p) for p in pagos]},
    ).all()
    visibles = [f for f in filas if unidades is None or UUID(str(f.unidad_id)) in unidades]
    vigentes = _vigentes_por_pago(sesion, pagos)
    nombres = identificadores_de_unidades(
        sesion,
        [
            *(UUID(str(f.unidad_id)) for f in visibles),
            *(
                vigente
                for fila in visibles
                if (vigente := vigentes.get((UUID(str(fila.pago_id)), UUID(str(fila.unidad_id)))))
            ),
        ],
    )
    partes: dict[UUID, list[dict[str, str]]] = defaultdict(list)
    for fila in visibles:
        unidad = UUID(str(fila.unidad_id))
        pago = UUID(str(fila.pago_id))
        vigente = vigentes.get((pago, unidad), unidad)
        partes[pago].append(
            {
                "unidad_id": str(unidad),
                "identificador": nombres[unidad],
                "importe": fila.importe,
                "unidad_vigente_id": str(vigente),
                "identificador_vigente": nombres[vigente],
            }
        )
    for lista in partes.values():
        lista.sort(key=lambda parte: parte["identificador"])
    return partes


def _pagos(
    sesion: Session, complejo_id: UUID, unidades: frozenset[UUID] | None, pago_id: UUID | None
) -> list[dict[str, Any]]:
    filas = _filas_de_pagos(sesion, complejo_id, unidades, pago_id)
    ids = [UUID(str(f.id)) for f in filas]
    if not ids:
        return []
    eventos = _eventos(sesion, ids)
    partes = _partes(sesion, ids, unidades)
    resultado = []
    for fila in filas:
        pago = UUID(str(fila.id))
        historia = eventos.get(pago, [])
        estado = estado_del_pago([tipo for tipo, _ in historia])
        resultado.append(
            {
                "pago_id": str(pago),
                "estado": estado,
                "motivo": historia[-1][1] if estado in _CON_MOTIVO else None,
                "banco": fila.banco,
                "numero_de_operacion": fila.numero_de_operacion,
                "fecha_de_transferencia": fila.fecha_de_transferencia.isoformat(),
                "monto": fila.monto,
                "comprobante_id": str(fila.comprobante_id),
                "informado_por": str(fila.informado_por),
                "informado_en": fila.informado_en.isoformat(),
                "partes": partes.get(pago, []),
            }
        )
    return resultado


def listar_pagos(
    sesion: Session, *, complejo_id: UUID, unidades: frozenset[UUID] | None
) -> list[dict[str, Any]]:
    """`unidades`: las del vecino; `None` para el personal, que ve el edificio entero."""
    return _pagos(sesion, complejo_id, unidades, None)


def leer_pago(
    sesion: Session, *, complejo_id: UUID, pago_id: UUID, unidades: frozenset[UUID] | None
) -> dict[str, Any] | None:
    """`None` si no existe, es de otro edificio o administración (RLS) o de una unidad ajena."""
    encontrados = _pagos(sesion, complejo_id, unidades, pago_id)
    return encontrados[0] if encontrados else None


def comprobante_del_pago(sesion: Session, *, pago_id: UUID) -> tuple[bytes, str] | None:
    """Los bytes y el tipo del comprobante de un pago, o `None` si no existe en la administración
    de la sesión (RLS). Quién puede pedirlo lo decide quien llama."""
    fila = sesion.execute(
        text(
            "SELECT c.contenido, c.tipo FROM pago_informado p "
            "JOIN comprobante_de_pago c ON c.id = p.comprobante_id WHERE p.id = :pago"
        ),
        {"pago": pago_id},
    ).first()
    return None if fila is None else (bytes(fila.contenido), str(fila.tipo))


def pagos_sin_confirmar(sesion: Session, *, complejo_id: UUID) -> tuple[int, Dinero]:
    """Cuántos pagos del edificio siguen `informado` (sin ningún evento: ni confirmados ni
    rechazados) y su total (R34, H-024)."""
    montos = sesion.execute(
        text(
            "SELECT p.monto::text AS monto FROM pago_informado p WHERE p.complejo_id = :c "
            "AND NOT EXISTS (SELECT 1 FROM evento_de_pago e WHERE e.pago_id = p.id)"
        ),
        {"c": complejo_id},
    ).all()
    return len(montos), sumar(Dinero(str(m.monto)) for m in montos)


def pagos_confirmados_de_unidad(
    sesion: Session, *, unidad_id: UUID, sin_extraordinaria: bool
) -> list[dict[str, str]]:
    """Los pagos confirmados con una parte en la unidad, del más nuevo al más viejo por fecha de
    transferencia (H-038, N03: nunca los informados, rechazados o revertidos; el estado sale de los
    eventos). `importe` es la parte de la unidad. Con `sin_extraordinaria` (el inquilino, D-170.2)
    es sólo lo imputado a interés, ordinaria y fondo, y un pago que fue entero a la extraordinaria
    no figura."""
    filas = sesion.execute(
        text(
            "SELECT p.id, p.banco, p.numero_de_operacion, p.fecha_de_transferencia, "
            "x.importe::text AS importe FROM parte_de_pago x JOIN pago_informado p "
            "ON p.id = x.pago_id WHERE x.unidad_id = :u "
            "ORDER BY p.fecha_de_transferencia DESC, p.informado_en DESC, p.id"
        ),
        {"u": unidad_id},
    ).all()
    if not filas:
        return []
    ids = [UUID(str(f.id)) for f in filas]
    eventos = _eventos(sesion, ids)
    movimientos: dict[UUID, set[UUID]] = defaultdict(set)
    if sin_extraordinaria:
        for fila in sesion.execute(
            text(
                "SELECT pago_id, movimiento_id FROM movimiento_de_pago "
                "WHERE pago_id = ANY(CAST(:ids AS uuid[])) AND papel = 'pago'"
            ),
            {"ids": [str(i) for i in ids]},
        ):
            movimientos[UUID(str(fila.pago_id))].add(UUID(str(fila.movimiento_id)))
    resultado = []
    for fila in filas:
        pago = UUID(str(fila.id))
        if estado_del_pago([tipo for tipo, _ in eventos.get(pago, [])]) != "confirmado":
            continue
        importe = fila.importe
        if sin_extraordinaria:
            imputado = importe_imputado_sin_extraordinaria(
                sesion, unidad_id=unidad_id, movimiento_ids=frozenset(movimientos[pago])
            )
            if imputado <= Dinero("0.00"):
                continue
            importe = imputado.a_texto()
        resultado.append(
            {
                "pago_id": str(pago),
                "fecha_de_transferencia": fila.fecha_de_transferencia.isoformat(),
                "importe": importe,
                "banco": fila.banco,
                "numero_de_operacion": fila.numero_de_operacion,
            }
        )
    return resultado
