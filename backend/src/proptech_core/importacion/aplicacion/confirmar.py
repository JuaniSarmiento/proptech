"""Confirmar el borrador de saldos (design D7, E6, E8, E10, E15): el libro recibe el saldo inicial
(4c), el edificio pasa a `confirmada` y el importador se cierra.

Orden de chequeo (D7 del 2a): alcance (404) -> permiso (403) -> candado del complejo (`FOR UPDATE`,
E8) -> estado de la migración, borrador vigente, saldos (E10) y diferencias aceptadas (409) -> carga
del 4c, que vuelve a validar la fecha de migración (422, E15). Todo en **una** transacción: si algo
falla después de empezar a escribir, el SAVEPOINT deshace todo y el edificio sigue `pendiente`. Se
audita una vez, con ids y sin montos.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.dinero import Dinero
from proptech_core.complejos.aplicacion.errores import Conflicto, NoEncontrado, transaccion
from proptech_core.complejos.aplicacion.escritura import confirmar_saldos_iniciales_del_edificio
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.cuenta_corriente.aplicacion.saldo_inicial import (
    FilaDeCredito,
    FilaDeDeuda,
    FilaDeTotal,
    OrigenDeCarga,
    TotalesDeSaldoInicial,
    UnidadDeSaldoInicial,
    registrar_saldo_inicial,
)
from proptech_core.importacion.aplicacion.borrador import (
    borrador_vigente,
    comparar_importacion,
    leer_aceptacion,
)
from proptech_core.importacion.aplicacion.edificio import edificio_autorizado

__all__ = ["ConfirmacionRegistrada", "confirmar"]


@dataclass(frozen=True)
class ConfirmacionRegistrada:
    importacion_id: UUID
    #: La fila de `carga_de_saldo_inicial` que dejó el 4c.
    carga_id: UUID
    estado_migracion: str
    #: Los totales del edificio que devuelve `registrar_saldo_inicial`.
    totales: TotalesDeSaldoInicial
    confirmada_por: UUID
    confirmada_en: datetime


_FilaDelLibro = FilaDeDeuda | FilaDeTotal | FilaDeCredito


def _filas_del_borrador(sesion: Session, importacion_id: UUID) -> dict[UUID, list[_FilaDelLibro]]:
    """Las filas de `Saldos` de la importación, traducidas a los tipos del 4c y agrupadas por unidad
    (concepto a componente; el crédito se guarda positivo y viaja como `FilaDeCredito`)."""
    por_unidad: dict[UUID, list[_FilaDelLibro]] = {}
    consulta = text(
        "SELECT unidad_id, fila, tipo, periodo, vencimiento, concepto, importe::text, "
        "interes_acumulado::text FROM fila_de_saldo_importada WHERE importacion_id = :importacion "
        "ORDER BY fila"
    )
    for unidad, fila, tipo, periodo, vencimiento, concepto, importe, interes in sesion.execute(
        consulta, {"importacion": importacion_id}
    ):
        monto, acumulado = Dinero(str(importe)), Dinero(str(interes))
        traducida: _FilaDelLibro
        if tipo == "detalle":
            traducida = FilaDeDeuda(
                fila=int(fila),
                periodo=periodo,
                vencimiento=vencimiento,
                componente=str(concepto),
                importe=monto,
                interes_acumulado=acumulado,
            )
        elif tipo == "total":
            traducida = FilaDeTotal(fila=int(fila), importe=monto, interes_acumulado=acumulado)
        else:
            traducida = FilaDeCredito(fila=int(fila), importe=monto)
        por_unidad.setdefault(UUID(str(unidad)), []).append(traducida)
    return por_unidad


def _unidades_del_libro(
    por_unidad: dict[UUID, list[_FilaDelLibro]],
) -> list[UnidadDeSaldoInicial]:
    """Una unidad es de "total" si trae una fila de total único y de "detalle" si no (una unidad
    sólo con crédito vale en las dos modalidades)."""
    return [
        UnidadDeSaldoInicial(
            unidad_id=unidad,
            modo="total" if any(isinstance(f, FilaDeTotal) for f in filas) else "detalle",
            filas=tuple(filas),
        )
        for unidad, filas in por_unidad.items()
    ]


@accion_sensible(Accion.CONFIRMAR_SALDOS_INICIALES)
def confirmar(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    importacion_id: UUID,
    reloj: Callable[[], datetime],
    request_id: UUID,
) -> ConfirmacionRegistrada:
    with transaccion(sesion, {}):
        edificio_autorizado(sesion, identidad, complejo_id, Accion.CONFIRMAR_SALDOS_INICIALES)
        # E8: el candado va antes de leer el estado, y el estado se lee ya con él puesto.
        edificio = cargar_complejo(sesion, complejo_id, bloquear=True)
        if edificio is None:
            raise NoEncontrado()
        if edificio.estado_migracion != "pendiente":
            raise Conflicto("estado_migracion")
        vigente = borrador_vigente(sesion, complejo_id)
        if vigente is None or vigente.importacion_id != importacion_id:
            raise Conflicto("importacion_id")
        por_unidad = _filas_del_borrador(sesion, importacion_id)
        if not por_unidad:  # E10: sin hoja `Saldos` el edificio se cierra con "sin saldos previos"
            raise Conflicto("saldos")
        comparacion = comparar_importacion(sesion, complejo_id, importacion_id)
        if (
            comparacion.unidades_con_diferencia > 0
            and leer_aceptacion(sesion, importacion_id) is None
        ):
            raise Conflicto("diferencias")
        confirmada_en = reloj()
        fecha: date = vigente.fecha_de_migracion
        registrado = registrar_saldo_inicial(
            sesion,
            identidad,
            complejo_id=complejo_id,
            operacion_id=importacion_id,
            fecha_de_migracion=fecha,
            origen=OrigenDeCarga(tipo="importador", archivo=vigente.archivo),
            unidades=_unidades_del_libro(por_unidad),
            request_id=request_id,
            reloj=lambda: confirmada_en,
        )
        confirmar_saldos_iniciales_del_edificio(sesion, complejo_id=complejo_id)
        sesion.execute(
            text("UPDATE importacion SET estado = 'confirmada' WHERE id = :id"),
            {"id": importacion_id},
        )
        registrar(
            sesion,
            identidad,
            Accion.CONFIRMAR_SALDOS_INICIALES,
            entidad="importacion",
            entidad_id=importacion_id,
            request_id=request_id,
            detalle={
                "complejo_id": str(complejo_id),
                "importacion_id": str(importacion_id),
                "carga_id": str(registrado.carga_id),
            },
        )
    return ConfirmacionRegistrada(
        importacion_id=importacion_id,
        carga_id=registrado.carga_id,
        estado_migracion="confirmada",
        totales=registrado.total,
        confirmada_por=identidad.persona_id,
        confirmada_en=confirmada_en,
    )
