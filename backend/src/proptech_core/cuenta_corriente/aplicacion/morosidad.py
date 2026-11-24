"""La lectura de la morosidad de un edificio (10a, H-027, R20, R30, D-167).

Es una lectura: sin candados ni escrituras. Se apoya en la situación de cobranza del 4c (mismas
etiquetas, mismo total vencido) y suma lo que pide HU-A8: el desglose de capital e intereses, la
antigüedad y los nombres de los propietarios. El interés es el registrado en el libro: no se estima
el corrido desde el último corte (D-167).
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.propietarios import nombres_de_propietarios
from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.complejos.aplicacion.unidades import identificadores_de_unidades
from proptech_core.cuenta_corriente.aplicacion.cobranza import fotos_y_situaciones_del_edificio
from proptech_core.cuenta_corriente.dominio.cobranza import (
    MOROSO_CRITICO,
    SIN_DEUDA_VENCIDA,
)


@dataclass(frozen=True)
class FilaDeMorosidad:
    unidad_id: UUID
    unidad: str
    propietarios: tuple[str, ...]
    etiqueta: str
    total_vencido: Dinero
    capital: Dinero
    intereses: Dinero
    liquidaciones_vencidas: int
    vencida_desde: date
    dias: int


@dataclass(frozen=True)
class Morosidad:
    fecha: date
    intereses_al: date | None
    unidades: tuple[FilaDeMorosidad, ...]

    @property
    def morosos_criticos(self) -> int:
        return sum(1 for f in self.unidades if f.etiqueta == MOROSO_CRITICO)

    @property
    def total_vencido(self) -> Dinero:
        return sumar(f.total_vencido for f in self.unidades)


def morosidad_del_edificio(sesion: Session, *, complejo_id: UUID, fecha: date) -> Morosidad:
    """Una fila por cuenta de unidad con deuda vencida a `fecha`: los morosos críticos primero y,
    dentro de cada grupo, de mayor a menor deuda; el empate, por identificador de unidad."""
    fotos = fotos_y_situaciones_del_edificio(sesion, complejo_id=complejo_id, fecha=fecha)
    identificadores = identificadores_de_unidades(sesion, complejo_id)
    propietarios = nombres_de_propietarios(sesion, complejo_id)
    filas: list[FilaDeMorosidad] = []
    for foto, s in fotos:
        if s.etiqueta == SIN_DEUDA_VENCIDA or s.vencida_desde is None or foto.unidad_id is None:
            continue
        filas.append(
            FilaDeMorosidad(
                unidad_id=foto.unidad_id,
                unidad=identificadores[foto.unidad_id],
                propietarios=tuple(propietarios.get(foto.unidad_id, [])),
                etiqueta=s.etiqueta,
                total_vencido=s.total_vencido,
                capital=s.capital_vencido,
                intereses=s.interes_vencido,
                liquidaciones_vencidas=s.liquidaciones_vencidas,
                vencida_desde=s.vencida_desde,
                dias=(fecha - s.vencida_desde).days,
            )
        )
    filas.sort(key=lambda f: (f.etiqueta != MOROSO_CRITICO, -f.total_vencido.decimal, f.unidad))
    cortes = [
        m.corte
        for foto, _ in fotos
        for m in foto.movimientos.values()
        if m.tipo == "interes"
        and m.corte is not None
        and m.id in foto.estado.movimientos_que_cuentan
    ]
    return Morosidad(fecha, max(cortes, default=None), tuple(filas))
