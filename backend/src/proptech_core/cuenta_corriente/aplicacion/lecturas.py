"""Lecturas del libro (D12): una sola sentencia por foto, después `calcular_estado`.

En READ COMMITTED cada sentencia ve un snapshot propio; leer obligaciones, movimientos e
imputaciones en sentencias separadas podría mezclar una transacción con otra (BE-6). Por eso cada
foto es UNA sentencia con subconsultas, y la del edificio parte de `cuenta` y usa `= ANY(ids)` sobre
las tablas grandes (DB-2), nunca sólo `complejo_id`.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.errores import NoEncontrado
from proptech_core.cuenta_corriente.dominio.estado import (
    EstadoDeCuenta,
    ImputacionRegistrada,
    Movimiento,
    Obligacion,
    calcular_estado,
)
from proptech_core.cuenta_corriente.dominio.imputacion import Componente

_IDS = bindparam("ids", type_=ARRAY(PG_UUID(as_uuid=True)))

#: Una foto por cuenta en UNA sentencia. Los importes viajan como texto: nunca float.
#: Sirve a `ix_obligacion_cuenta_periodo`, `ix_movimiento_cuenta` e `ix_imputacion_cuenta`
#: (administracion_id, cuenta_id), que son el acceso de esta consulta.
_FOTO = """
WITH t AS (SELECT nullif(current_setting('app.administracion_id', true), '')::uuid AS adm),
cuentas AS (
    SELECT c.id, c.complejo_id, c.unidad_id FROM cuenta c, t
    WHERE c.administracion_id = t.adm AND c.id = ANY(:ids)
)
SELECT c.id, c.complejo_id, c.unidad_id,
  (SELECT coalesce(json_agg(json_build_object(
      'id', o.id, 'emision_id', o.emision_id, 'periodo', o.periodo, 'vencimiento', o.vencimiento,
      'ordinaria', o.ordinaria::text, 'fondo_de_reserva', o.fondo_de_reserva::text,
      'extraordinaria', o.extraordinaria::text)), '[]')
   FROM obligacion o, t WHERE o.administracion_id = t.adm AND o.cuenta_id = c.id) AS obligaciones,
  (SELECT coalesce(json_agg(json_build_object(
      'id', m.id, 'tipo', m.tipo, 'sentido', m.sentido, 'importe', m.importe::text,
      'fecha_valor', m.fecha_valor, 'registrado_en', m.registrado_en,
      'obligacion_id', m.obligacion_id, 'componente', m.componente, 'emision_id', m.emision_id,
      'corrige_a', m.corrige_a, 'enlazado_a', m.enlazado_a)), '[]')
   FROM movimiento m, t WHERE m.administracion_id = t.adm AND m.cuenta_id = c.id) AS movimientos,
  (SELECT coalesce(json_agg(json_build_object(
      'movimiento_id', i.movimiento_id, 'obligacion_id', i.obligacion_id,
      'componente', i.componente, 'importe', i.importe::text, 'orden', i.orden)), '[]')
   FROM imputacion i, t WHERE i.administracion_id = t.adm AND i.cuenta_id = c.id) AS imputaciones,
  (SELECT coalesce(json_agg(e.emision_id), '[]') FROM evento_de_emision e, t
   WHERE e.administracion_id = t.adm AND e.tipo = 'anulada' AND e.emision_id IN (
       SELECT o.emision_id FROM obligacion o WHERE o.administracion_id = t.adm
         AND o.cuenta_id = c.id AND o.emision_id IS NOT NULL
       UNION SELECT m.emision_id FROM movimiento m WHERE m.administracion_id = t.adm
         AND m.cuenta_id = c.id AND m.emision_id IS NOT NULL)) AS anuladas
FROM cuentas c ORDER BY c.id
"""


@dataclass(frozen=True)
class FotoDeCuenta:
    cuenta_id: UUID
    complejo_id: UUID
    unidad_id: UUID | None
    estado: EstadoDeCuenta
    movimientos: dict[UUID, Movimiento]


@dataclass(frozen=True)
class DeudaDeCuenta:
    cuenta_id: UUID
    unidad_id: UUID | None
    deuda: Dinero
    credito_a_favor: Dinero
    credito_a_favor_aplicable: Dinero
    credito_a_favor_retenido: Dinero


def _uuid(valor: Any) -> UUID | None:
    return None if valor is None else UUID(str(valor))


def _carga(valor: Any) -> list[dict[str, Any]]:
    return json.loads(valor) if isinstance(valor, str) else list(valor)


def _foto(fila: Any) -> FotoDeCuenta:
    obligaciones = [
        Obligacion(
            UUID(o["id"]),
            _uuid(o["emision_id"]),
            date.fromisoformat(o["periodo"]),
            date.fromisoformat(o["vencimiento"]),
            Dinero(o["ordinaria"]),
            Dinero(o["fondo_de_reserva"]),
            Dinero(o["extraordinaria"]),
        )
        for o in _carga(fila.obligaciones)
    ]
    movimientos = [
        Movimiento(
            UUID(m["id"]),
            m["tipo"],
            m["sentido"],
            Dinero(m["importe"]),
            date.fromisoformat(m["fecha_valor"]),
            datetime.fromisoformat(m["registrado_en"]),
            _uuid(m["obligacion_id"]),
            None if m["componente"] is None else Componente(m["componente"]),
            _uuid(m["emision_id"]),
            _uuid(m["corrige_a"]),
            _uuid(m["enlazado_a"]),
        )
        for m in _carga(fila.movimientos)
    ]
    imputaciones = [
        ImputacionRegistrada(
            UUID(i["movimiento_id"]),
            UUID(i["obligacion_id"]),
            Componente(i["componente"]),
            Dinero(i["importe"]),
            int(i["orden"]),
        )
        for i in _carga(fila.imputaciones)
    ]
    anuladas = {UUID(str(e)) for e in _carga(fila.anuladas)}
    return FotoDeCuenta(
        UUID(str(fila.id)),
        UUID(str(fila.complejo_id)),
        _uuid(fila.unidad_id),
        calcular_estado(obligaciones, movimientos, imputaciones, anuladas),
        {m.id: m for m in movimientos},
    )


def fotos(sesion: Session, cuenta_ids: Sequence[UUID]) -> dict[UUID, FotoDeCuenta]:
    filas = sesion.execute(text(_FOTO).bindparams(_IDS), {"ids": list(cuenta_ids)}).all()
    return {f.cuenta_id: f for f in map(_foto, filas)}


def foto(sesion: Session, cuenta_id: UUID) -> FotoDeCuenta:
    resultado = fotos(sesion, [cuenta_id])
    if cuenta_id not in resultado:
        raise NoEncontrado
    return resultado[cuenta_id]


def estado_de_cuenta(sesion: Session, *, cuenta_id: UUID) -> EstadoDeCuenta:
    return foto(sesion, cuenta_id).estado


def deuda_del_edificio(sesion: Session, *, complejo_id: UUID) -> list[DeudaDeCuenta]:
    """Una sola sentencia: enumera `cuenta` del edificio y lee el resto por `= ANY(ids)`."""
    filas = sesion.execute(
        text(
            _FOTO.replace(
                "WHERE c.administracion_id = t.adm AND c.id = ANY(:ids)",
                "WHERE c.administracion_id = t.adm AND c.complejo_id = :complejo",
            )
        ),
        {"complejo": complejo_id},
    ).all()
    return [
        DeudaDeCuenta(
            f.cuenta_id,
            f.unidad_id,
            f.estado.deuda,
            f.estado.credito_a_favor,
            f.estado.credito_a_favor_aplicable,
            f.estado.credito_a_favor_retenido,
        )
        for f in map(_foto, filas)
    ]


def saldo_anterior(sesion: Session, *, emision_id: UUID, cuenta_id: UUID) -> Dinero:
    """R06 para el 7: deuda residual no negativa sin la emisión pedida; el crédito va aparte."""
    return foto(sesion, cuenta_id).estado.deuda_sin_emision(emision_id)
