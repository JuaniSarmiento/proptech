"""Ayudas de la aceptación de H-004 (interés por mora al emitir). Caja negra: sólo casos de uso del
libro que ya existen (`registrar_emision`, `anular_emision`, `registrar_credito`, `corregir`,
`lecturas`) y lecturas SQL del libro y de `tramo_de_interes` (columnas de design D4).

Lo que todavía no existe en `main` (la tabla de tramos, el campo `intereses` de
`EmisionRegistrada`) se pide con un `assert` y un mensaje, nunca con un error de setup.

Base de los ejemplos: ordinaria de septiembre de $100.000 vencida el 10/09/2026, 3% mensual
proporcional, gracia 0.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import correcciones, creditos, emisiones
from proptech_core.cuenta_corriente.aplicacion.correcciones import PedidoDeCorreccion
from proptech_core.cuenta_corriente.aplicacion.emisiones import EmisionRegistrada, ObligacionAEmitir

from .._cuenta_corriente import Mundo
from .._edificios import BaseDeEdificio, fijar_tenant

AGO, SEP, OCT, NOV, DIC = (date(2026, m, 1) for m in (8, 9, 10, 11, 12))
PROPORCIONAL, MES_ENTERO = "proporcional_por_dia", "mes_entero"
#: La unidad de relleno: lleva las obligaciones de un período cuando la que se mide no debe tenerla.
RELLENO = 11


def d(t: str) -> Dinero:
    return Dinero(t)


def dia(m: int, dd: int, a: int = 2026) -> date:
    return date(a, m, dd)


def configurar(
    base: BaseDeEdificio,
    mundo: Mundo,
    *,
    desde: date = date(2026, 1, 1),
    tasa: str = "3.00",
    gracia: int = 0,
    forma: str = PROPORCIONAL,
    complejo: UUID | None = None,
) -> UUID:
    """Una versión de configuración del edificio, confirmada (la lee otra conexión)."""
    with base.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, mundo.admin)
        fila = c.execute(
            "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, "
            "vigente_desde, tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, "
            "porcentaje_fondo, dia_de_vencimiento, modalidad_de_vencimiento) "
            "VALUES (%s, %s, %s, %s, %s, '500.00', %s, %s, '0.00', 10, 'unico') RETURNING id",
            (mundo.admin, complejo or mundo.complejo, mundo.persona, desde, tasa, gracia, forma),
        ).fetchone()
        assert fila is not None
        c.commit()
        return UUID(str(fila[0]))


def obl(
    mundo: Mundo,
    unidad: int,
    vencimiento: date,
    ordinaria: str = "100000.00",
    fondo: str = "0.00",
    extra: str = "0.00",
) -> ObligacionAEmitir:
    return ObligacionAEmitir(mundo.unidades[unidad], vencimiento, d(ordinaria), d(fondo), d(extra))


def emitir(
    s: Session,
    mundo: Mundo,
    periodo: date,
    obligaciones: list[ObligacionAEmitir],
    *,
    emision_id: UUID | None = None,
    complejo: UUID | None = None,
    identidad: Identidad | None = None,
    reloj: Callable[[], datetime] | None = None,
    confirmar: bool = True,
) -> EmisionRegistrada:
    extra: dict[str, Any] = {} if reloj is None else {"reloj": reloj}
    r = emisiones.registrar_emision(
        s,
        identidad or mundo.identidad,
        emision_id=emision_id or uuid4(),
        complejo_id=complejo or mundo.complejo,
        periodo=periodo,
        obligaciones=obligaciones,
        request_id=uuid4(),
        **extra,
    )
    if confirmar:
        confirmar_paso(s)
    return r


def relleno(mundo: Mundo, periodo: date) -> list[ObligacionAEmitir]:
    """La obligación de un período para la unidad de relleno ($1,00, vence el 10)."""
    return [obl(mundo, RELLENO, periodo.replace(day=10), "1.00")]


def anular(s: Session, mundo: Mundo, emision_id: UUID) -> None:
    emisiones.anular_emision(
        s, mundo.identidad, emision_id=emision_id, motivo="Emisión mal cargada", request_id=uuid4()
    )
    confirmar_paso(s)


def pagar(s: Session, mundo: Mundo, cuenta: UUID, importe: str, fecha_valor: date) -> UUID:
    m = creditos.registrar_credito(
        s,
        mundo.identidad,
        cuenta_id=cuenta,
        tipo="pago",
        importe=d(importe),
        fecha_valor=fecha_valor,
        operacion_id=uuid4(),
        destino=None,
        request_id=uuid4(),
    )
    confirmar_paso(s)
    return m


def contra_asentar(s: Session, mundo: Mundo, movimiento: UUID, *, confirmar: bool = True) -> UUID:
    m = correcciones.corregir(
        s,
        mundo.identidad,
        complejo_id=mundo.complejo,
        pedido=PedidoDeCorreccion(
            "contra_asiento", uuid4(), "Interés mal calculado", movimiento_id=movimiento
        ),
        request_id=uuid4(),
    )
    if confirmar:
        confirmar_paso(s)
    return m


def confirmar_paso(s: Session) -> None:
    """Cada paso del libro en su propia transacción, como en producción: dos emisiones en una
    sola transacción violan el orden de candados de `bloquear_cuentas` (E2 del 4b)."""
    s.commit()
    s.begin()


def reloj_del(dia_: date) -> Callable[[], datetime]:
    return lambda: datetime(dia_.year, dia_.month, dia_.day, 15, tzinfo=UTC)


def cuenta_de(s: Session, unidad: UUID) -> UUID:
    return UUID(
        str(
            s.execute(
                text("SELECT id FROM cuenta WHERE unidad_id = :u"), {"u": unidad}
            ).scalar_one()
        )
    )


def obligacion_de(s: Session, cuenta: UUID, emision_id: UUID) -> UUID:
    return UUID(
        str(
            s.execute(
                text("SELECT id FROM obligacion WHERE cuenta_id = :c AND emision_id = :e"),
                {"c": cuenta, "e": emision_id},
            ).scalar_one()
        )
    )


@dataclass(frozen=True)
class Interes:
    id: UUID
    cuenta_id: UUID
    obligacion_id: UUID
    corte: date
    importe: Dinero
    emision_id: UUID | None


def intereses(
    s: Session, *, obligacion: UUID | None = None, cuenta: UUID | None = None
) -> list[Interes]:
    """Los débitos de interés del libro (tipo `interes`), por obligación o por cuenta."""
    filas = s.execute(
        text(
            "SELECT id, cuenta_id, obligacion_id, corte, importe::text AS importe, emision_id "
            "FROM movimiento WHERE tipo = 'interes' AND sentido = 'debito' "
            "AND (CAST(:o AS uuid) IS NULL OR obligacion_id = :o) "
            "AND (CAST(:c AS uuid) IS NULL OR cuenta_id = :c) ORDER BY corte, registrado_en"
        ),
        {"o": obligacion, "c": cuenta},
    ).all()
    return [
        Interes(
            UUID(str(f.id)),
            UUID(str(f.cuenta_id)),
            UUID(str(f.obligacion_id)),
            f.corte,
            d(f.importe),
            None if f.emision_id is None else UUID(str(f.emision_id)),
        )
        for f in filas
    ]


def interes_unico(s: Session, obligacion: UUID, corte: date) -> Interes:
    del_corte = [i for i in intereses(s, obligacion=obligacion) if i.corte == corte]
    assert len(del_corte) == 1, (
        f"se espera un interés con corte {corte} sobre la obligación, hay {len(del_corte)}"
    )
    return del_corte[0]


def sin_interes(s: Session, obligacion: UUID, corte: date | None = None) -> None:
    hay = [i for i in intereses(s, obligacion=obligacion) if corte is None or i.corte == corte]
    assert hay == [], f"no se espera interés, hay {[(i.corte, i.importe) for i in hay]}"


def hay_tabla_de_tramos(s: Session) -> None:
    assert s.execute(text("SELECT to_regclass('tramo_de_interes')")).scalar_one() is not None, (
        "falta la tabla tramo_de_interes (migración 0034)"
    )


@dataclass(frozen=True)
class Tramo:
    desde: date
    hasta: date
    dias: int
    base: Dinero
    tasa_mensual: str
    forma_de_calculo: str
    dias_de_gracia: int
    configuracion_id: UUID


def tramos(s: Session, movimiento: UUID) -> list[Tramo]:
    hay_tabla_de_tramos(s)
    filas = s.execute(
        text(
            "SELECT desde, hasta, dias, base::text AS base, tasa_mensual::text AS tasa, "
            "forma_de_calculo, dias_de_gracia, configuracion_id FROM tramo_de_interes "
            "WHERE movimiento_id = :m ORDER BY desde"
        ),
        {"m": movimiento},
    ).all()
    return [
        Tramo(
            f.desde,
            f.hasta,
            int(f.dias),
            d(f.base),
            f.tasa,
            f.forma_de_calculo,
            int(f.dias_de_gracia),
            UUID(str(f.configuracion_id)),
        )
        for f in filas
    ]


def fechas(ts: Iterable[Tramo]) -> list[tuple[date, date]]:
    return [(t.desde, t.hasta) for t in ts]


def conteos(s: Session) -> dict[str, int]:
    tablas = ["emision", "obligacion", "movimiento", "imputacion"]
    if s.execute(text("SELECT to_regclass('tramo_de_interes')")).scalar_one() is not None:
        tablas.append("tramo_de_interes")
    return {
        t: int(s.execute(text(f"SELECT count(*) FROM {t}")).scalar_one())  # noqa: S608 - fijas
        for t in tablas
    }


def intereses_informados(r: EmisionRegistrada) -> dict[UUID, list[tuple[UUID, date, Dinero]]]:
    """El campo `intereses` de `EmisionRegistrada` (design D1: por cuenta, obligación, corte e
    importe), normalizado. Acepta objetos con atributos o diccionarios."""
    campo = getattr(r, "intereses", None)
    assert campo is not None, "EmisionRegistrada no informa `intereses` (design D1)"

    def leer(item: Any, *nombres: str) -> Any:
        for n in nombres:
            if isinstance(item, dict) and n in item:
                return item[n]
            if hasattr(item, n):
                return getattr(item, n)
        raise AssertionError(f"un interés informado no trae {nombres}: {item!r}")

    def dinero(valor: Any) -> Dinero:
        return valor if isinstance(valor, Dinero) else Dinero(str(valor))

    return {
        cuenta: sorted(
            (
                (
                    UUID(str(leer(i, "obligacion_id", "obligacion"))),
                    leer(i, "corte"),
                    dinero(leer(i, "importe")),
                )
                for i in lista
            ),
            key=lambda x: (str(x[0]), x[1]),
        )
        for cuenta, lista in dict(campo).items()
    }
