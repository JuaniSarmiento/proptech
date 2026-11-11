"""Saldo inicial (R09, design D5 del 4c): pedido, validación, firma y agrupación. Puro."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.compartido.texto import recortado_sin_control
from proptech_core.cuenta_corriente.dominio.errores import EntradaInvalida

_CERO = Dinero("0.00")
_COMPONENTES = ("ordinaria", "fondo_de_reserva", "extraordinaria")
_MODOS = ("detalle", "total")
_LARGO_DE_ARCHIVO = 255
_LARGO_DE_MOTIVO = 500


@dataclass(frozen=True)
class OrigenDeCarga:
    tipo: str
    archivo: str | None = None
    motivo: str | None = None


@dataclass(frozen=True)
class FilaDeDeuda:
    fila: int | None
    periodo: date
    vencimiento: date
    componente: str
    importe: Dinero
    interes_acumulado: Dinero


@dataclass(frozen=True)
class FilaDeTotal:
    fila: int | None
    importe: Dinero
    interes_acumulado: Dinero


@dataclass(frozen=True)
class FilaDeCredito:
    fila: int | None
    importe: Dinero


@dataclass(frozen=True)
class UnidadDeSaldoInicial:
    unidad_id: UUID
    modo: str
    filas: tuple[FilaDeDeuda | FilaDeTotal | FilaDeCredito, ...]


@dataclass(frozen=True)
class TotalesDeSaldoInicial:
    capital: Dinero
    interes_importado: Dinero
    credito: Dinero


@dataclass(frozen=True)
class PedidoNormalizado:
    """El pedido ya validado: origen recortado, unidades por `unidad_id` y filas en orden canónico.
    Es lo que se firma y lo que se agrupa; el orden en que el 5 manda unidades o filas no cuenta."""

    complejo_id: UUID
    fecha_de_migracion: date
    origen: OrigenDeCarga
    unidades: tuple[UnidadDeSaldoInicial, ...]


@dataclass(frozen=True)
class DeudaAMigrar:
    """Una obligación de saldo inicial: las filas de un período (o el total único) agrupadas."""

    periodo: date
    vencimiento: date
    ordinaria: Dinero
    fondo_de_reserva: Dinero
    extraordinaria: Dinero
    interes_importado: Dinero
    filas_de_capital: tuple[int | None, ...]
    filas_de_interes: tuple[int | None, ...]


@dataclass(frozen=True)
class SaldoDeUnidad:
    unidad_id: UUID
    deudas: tuple[DeudaAMigrar, ...]
    credito: Dinero
    filas_de_credito: tuple[int | None, ...]

    @property
    def totales(self) -> TotalesDeSaldoInicial:
        return TotalesDeSaldoInicial(
            capital=sumar(d.ordinaria + d.fondo_de_reserva + d.extraordinaria for d in self.deudas),
            interes_importado=sumar(d.interes_importado for d in self.deudas),
            credito=self.credito,
        )


def sumar_totales(totales: list[TotalesDeSaldoInicial]) -> TotalesDeSaldoInicial:
    return TotalesDeSaldoInicial(
        capital=sumar(t.capital for t in totales),
        interes_importado=sumar(t.interes_importado for t in totales),
        credito=sumar(t.credito for t in totales),
    )


def _origen_normalizado(origen: OrigenDeCarga) -> OrigenDeCarga:
    if origen.tipo == "importador":
        return OrigenDeCarga(
            "importador", archivo=_texto(origen.archivo, "archivo", _LARGO_DE_ARCHIVO)
        )
    if origen.tipo == "manual":
        return OrigenDeCarga("manual", motivo=_texto(origen.motivo, "motivo", _LARGO_DE_MOTIVO))
    raise EntradaInvalida("origen")


def _texto(valor: str | None, campo: str, largo: int) -> str:
    if valor is None:
        raise EntradaInvalida(campo)
    try:
        limpio = recortado_sin_control(valor)
    except ValueError:
        raise EntradaInvalida(campo) from None
    if len(limpio) > largo:
        raise EntradaInvalida(campo)
    return limpio


def _validar_numero_de_fila(fila: int | None, origen: OrigenDeCarga, vistas: set[int]) -> None:
    if fila is None:
        if origen.tipo == "importador":
            raise EntradaInvalida("fila")
        return
    if type(fila) is not int or fila < 1 or fila in vistas:
        raise EntradaInvalida("fila")
    vistas.add(fila)


def _validar_fila(
    fila: FilaDeDeuda | FilaDeTotal | FilaDeCredito,
    modo: str,
    migracion: date,
    origen: OrigenDeCarga,
    vistas: set[int],
) -> None:
    if isinstance(fila, FilaDeDeuda):
        if modo != "detalle":
            raise EntradaInvalida("fila")
    elif isinstance(fila, FilaDeTotal):
        if modo != "total":
            raise EntradaInvalida("fila")
    elif not isinstance(fila, FilaDeCredito):
        raise EntradaInvalida("fila")
    _validar_numero_de_fila(fila.fila, origen, vistas)
    if isinstance(fila, FilaDeCredito):
        if not fila.importe > _CERO:
            raise EntradaInvalida("importe")
        return
    if isinstance(fila, FilaDeDeuda):
        if fila.periodo.day != 1 or fila.periodo > migracion.replace(day=1):
            raise EntradaInvalida("periodo")
        if fila.vencimiento > migracion:
            raise EntradaInvalida("vencimiento")
        if fila.componente not in _COMPONENTES:
            raise EntradaInvalida("componente")
    if fila.importe < _CERO:
        raise EntradaInvalida("importe")
    if fila.interes_acumulado < _CERO:
        raise EntradaInvalida("interes_acumulado")


def _validar_capital_por_periodo(unidad: UnidadDeSaldoInicial) -> None:
    """E11, E16: el capital se mide por período (o por el total único), no por fila."""
    por_periodo: dict[date, list[FilaDeDeuda]] = {}
    for fila in unidad.filas:
        if isinstance(fila, FilaDeDeuda):
            por_periodo.setdefault(fila.periodo, []).append(fila)
    for filas in por_periodo.values():
        if len({f.vencimiento for f in filas}) > 1:
            raise EntradaInvalida("vencimiento")
        if not sumar(f.importe for f in filas) > _CERO:
            raise EntradaInvalida("interes_acumulado")
    totales = [f for f in unidad.filas if isinstance(f, FilaDeTotal)]
    if totales and not sumar(f.importe for f in totales) > _CERO:
        raise EntradaInvalida("interes_acumulado")


def _campos(fila: FilaDeDeuda | FilaDeTotal | FilaDeCredito) -> list[Any]:
    """Lo que identifica una fila: número, tipo, período, vencimiento, componente, importe e interés
    acumulado (importes como texto con dos decimales, fechas ISO)."""
    if isinstance(fila, FilaDeDeuda):
        return [
            fila.fila,
            "deuda",
            fila.periodo.isoformat(),
            fila.vencimiento.isoformat(),
            fila.componente,
            fila.importe.a_texto(),
            fila.interes_acumulado.a_texto(),
        ]
    if isinstance(fila, FilaDeTotal):
        return [
            fila.fila,
            "total",
            "",
            "",
            "",
            fila.importe.a_texto(),
            fila.interes_acumulado.a_texto(),
        ]
    return [fila.fila, "credito", "", "", "", fila.importe.a_texto(), ""]


def _clave(fila: FilaDeDeuda | FilaDeTotal | FilaDeCredito) -> tuple[Any, ...]:
    """El orden canónico: la tupla completa, con la fila nula primero."""
    numero, *resto = _campos(fila)
    return (numero is not None, numero or 0, *resto)


def normalizar_pedido(
    *,
    complejo_id: UUID,
    fecha_de_migracion: date,
    origen: OrigenDeCarga,
    unidades: tuple[UnidadDeSaldoInicial, ...],
    hoy: date,
) -> PedidoNormalizado:
    """Valida el pedido entero antes de que nadie escriba (design D5, spec "La carga rechaza...") y
    lo deja en su forma canónica. Cada rechazo nombra su campo y nunca el valor recibido (D10)."""
    normal = _origen_normalizado(origen)
    if fecha_de_migracion > hoy:
        raise EntradaInvalida("fecha_de_migracion")
    if not unidades or len({u.unidad_id for u in unidades}) != len(unidades):
        raise EntradaInvalida("unidades")
    if any(not u.filas for u in unidades):
        raise EntradaInvalida("unidades")
    vistas: set[int] = set()
    for u in unidades:
        if u.modo not in _MODOS:
            raise EntradaInvalida("modo")
        for fila in u.filas:
            _validar_fila(fila, u.modo, fecha_de_migracion, normal, vistas)
        _validar_capital_por_periodo(u)
    ordenadas = tuple(
        UnidadDeSaldoInicial(u.unidad_id, u.modo, tuple(sorted(u.filas, key=_clave)))
        for u in sorted(unidades, key=lambda x: str(x.unidad_id))
    )
    return PedidoNormalizado(complejo_id, fecha_de_migracion, normal, ordenadas)


def firmar_pedido(pedido: PedidoNormalizado) -> str:
    """`"v1:"` + SHA-256 del pedido normalizado como JSON canónico (design D5, PR-11, E16).

    Queda fuera `operacion_id`, `request_id`, la identidad y el reloj. Cualquier dato de una fila
    cambia la firma aunque las sumas por período coincidan; el orden de unidades y filas, no."""
    cuerpo = {
        "complejo_id": str(pedido.complejo_id),
        "fecha_de_migracion": pedido.fecha_de_migracion.isoformat(),
        "origen": {
            "tipo": pedido.origen.tipo,
            "archivo": pedido.origen.archivo,
            "motivo": pedido.origen.motivo,
        },
        "unidades": [
            {
                "unidad_id": str(u.unidad_id),
                "modo": u.modo,
                "filas": [_campos(f) for f in u.filas],
            }
            for u in pedido.unidades
        ],
    }
    canonico = json.dumps(cuerpo, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "v1:" + hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def agrupar_unidad(unidad: UnidadDeSaldoInicial, fecha_de_migracion: date) -> SaldoDeUnidad:
    """E16: en detalle, una obligación por período con la suma de cada componente y del interés;
    en total único, una sola con todo en ordinaria, el primer día del mes de la migración y vencida
    en la migración. Varias filas de crédito suman un crédito."""
    deudas: list[DeudaAMigrar] = []
    creditos = [f for f in unidad.filas if isinstance(f, FilaDeCredito)]
    if unidad.modo == "total":
        totales = [f for f in unidad.filas if isinstance(f, FilaDeTotal)]
        if totales:
            deudas.append(
                DeudaAMigrar(
                    periodo=fecha_de_migracion.replace(day=1),
                    vencimiento=fecha_de_migracion,
                    ordinaria=sumar(f.importe for f in totales),
                    fondo_de_reserva=_CERO,
                    extraordinaria=_CERO,
                    interes_importado=sumar(f.interes_acumulado for f in totales),
                    filas_de_capital=tuple(f.fila for f in totales if f.importe > _CERO),
                    filas_de_interes=tuple(f.fila for f in totales if f.interes_acumulado > _CERO),
                )
            )
    else:
        por_periodo: dict[date, list[FilaDeDeuda]] = {}
        for fila in unidad.filas:
            if isinstance(fila, FilaDeDeuda):
                por_periodo.setdefault(fila.periodo, []).append(fila)
        for periodo in sorted(por_periodo):
            filas = por_periodo[periodo]

            def de(componente: str, filas: list[FilaDeDeuda] = filas) -> Dinero:
                return sumar(f.importe for f in filas if f.componente == componente)

            deudas.append(
                DeudaAMigrar(
                    periodo=periodo,
                    vencimiento=filas[0].vencimiento,
                    ordinaria=de("ordinaria"),
                    fondo_de_reserva=de("fondo_de_reserva"),
                    extraordinaria=de("extraordinaria"),
                    interes_importado=sumar(f.interes_acumulado for f in filas),
                    filas_de_capital=tuple(f.fila for f in filas if f.importe > _CERO),
                    filas_de_interes=tuple(f.fila for f in filas if f.interes_acumulado > _CERO),
                )
            )
    return SaldoDeUnidad(
        unidad.unidad_id,
        tuple(deudas),
        sumar(f.importe for f in creditos),
        tuple(f.fila for f in creditos),
    )
