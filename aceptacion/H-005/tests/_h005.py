"""Ayudas de la aceptación de H-005 (saldo inicial, R09). Caja negra: el caso de uso
`registrar_saldo_inicial` (design D5, contrato en `aceptacion/H-005/CONTRATO.md`), los casos de
uso del libro que ya existen (`registrar_emision`, `registrar_credito`) y lecturas SQL del libro y
de las dos tablas nuevas.

Lo que todavía no existe (el módulo `saldo_inicial`, las tablas `carga_de_saldo_inicial` y
`origen_de_saldo_inicial`) se pide con un `assert` y un mensaje, nunca con un error de setup.

Base de los ejemplos: migración el 15/10/2026, 3% mensual proporcional, gracia 0; "hoy" es el
11/11/2026 (reloj inyectado).
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import ModuleType
from typing import Any
from uuid import UUID, uuid4

import psycopg
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import creditos, emisiones
from proptech_core.cuenta_corriente.aplicacion.emisiones import EmisionRegistrada, ObligacionAEmitir

from .._cuenta_corriente import Mundo
from .._edificios import BaseDeEdificio, fijar_tenant

AGO, SEP, OCT, NOV, DIC = (date(2026, m, 1) for m in (8, 9, 10, 11, 12))
PROPORCIONAL, MES_ENTERO = "proporcional_por_dia", "mes_entero"
MIGRACION = date(2026, 10, 15)
HOY = date(2026, 11, 11)
ARCHIVO = "saldos-octubre.xlsx"
#: La unidad de relleno: lleva las obligaciones de las emisiones posteriores a la migración.
RELLENO = 11
MODULO = "proptech_core.cuenta_corriente.aplicacion.saldo_inicial"
TABLAS_NUEVAS = ("carga_de_saldo_inicial", "origen_de_saldo_inicial")


def d(t: str) -> Dinero:
    return Dinero(t)


def dia(m: int, dd: int, a: int = 2026) -> date:
    return date(a, m, dd)


def reloj_del(dia_: date) -> Callable[[], datetime]:
    return lambda: datetime(dia_.year, dia_.month, dia_.day, 15, tzinfo=UTC)


# --- El caso de uso (todavía no existe en main) ---------------------------------------------


def modulo() -> ModuleType:
    try:
        return importlib.import_module(MODULO)
    except ImportError as e:
        raise AssertionError(
            f"falta `{MODULO}` con `registrar_saldo_inicial` (design D5): {e}"
        ) from None


def _clase(nombre: str) -> Any:
    m = modulo()
    clase = getattr(m, nombre, None)
    assert clase is not None, f"`{MODULO}` no define `{nombre}` (CONTRATO.md)"
    return clase


def importador(archivo: str = ARCHIVO) -> Any:
    return _clase("OrigenDeCarga")(tipo="importador", archivo=archivo)


def manual(motivo: str) -> Any:
    return _clase("OrigenDeCarga")(tipo="manual", motivo=motivo)


def deuda(
    fila: int | None,
    periodo: date,
    vencimiento: date,
    importe: str,
    *,
    componente: str = "ordinaria",
    interes: str = "0.00",
) -> Any:
    return _clase("FilaDeDeuda")(
        fila=fila,
        periodo=periodo,
        vencimiento=vencimiento,
        componente=componente,
        importe=d(importe),
        interes_acumulado=d(interes),
    )


def total(fila: int | None, importe: str, *, interes: str = "0.00") -> Any:
    return _clase("FilaDeTotal")(fila=fila, importe=d(importe), interes_acumulado=d(interes))


def credito(fila: int | None, importe: str) -> Any:
    return _clase("FilaDeCredito")(fila=fila, importe=d(importe))


def unidad(unidad_id: UUID, *filas: Any, modo: str = "detalle") -> Any:
    return _clase("UnidadDeSaldoInicial")(unidad_id=unidad_id, modo=modo, filas=tuple(filas))


def cargar(
    s: Session,
    mundo: Mundo,
    unidades: Sequence[Any],
    *,
    operacion_id: UUID | None = None,
    fecha: date = MIGRACION,
    origen: Any = None,
    complejo: UUID | None = None,
    identidad: Identidad | None = None,
    hoy: date = HOY,
    confirmar: bool = True,
) -> Any:
    registrar = getattr(modulo(), "registrar_saldo_inicial", None)
    assert registrar is not None, f"`{MODULO}` no define `registrar_saldo_inicial`"
    r = registrar(
        s,
        identidad or mundo.identidad,
        complejo_id=complejo or mundo.complejo,
        operacion_id=operacion_id or uuid4(),
        fecha_de_migracion=fecha,
        origen=origen if origen is not None else importador(),
        unidades=list(unidades),
        request_id=uuid4(),
        reloj=reloj_del(hoy),
    )
    if confirmar:
        confirmar_paso(s)
    return r


def campo(error: BaseException) -> str | None:
    return getattr(error, "campo", None)


# --- Configuración, estado de migración y libro ------------------------------------------


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


def poner_estado(base: BaseDeEdificio, mundo: Mundo, estado: str) -> None:
    """El estado de migración del edificio (`complejo.estado_migracion`, 0005)."""
    with base.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, mundo.admin)
        c.execute(
            "UPDATE complejo SET estado_migracion = %s WHERE id = %s", (estado, mundo.complejo)
        )
        c.commit()


def confirmar_paso(s: Session) -> None:
    """Cada paso del libro en su propia transacción, como en producción."""
    s.commit()
    s.begin()


def emitir(s: Session, mundo: Mundo, periodo: date) -> EmisionRegistrada:
    """Una emisión posterior a la migración, con la obligación de la unidad de relleno."""
    r = emisiones.registrar_emision(
        s,
        mundo.identidad,
        emision_id=uuid4(),
        complejo_id=mundo.complejo,
        periodo=periodo,
        obligaciones=[
            ObligacionAEmitir(
                mundo.unidades[RELLENO], periodo.replace(day=10), d("1.00"), d("0.00"), d("0.00")
            )
        ],
        request_id=uuid4(),
    )
    confirmar_paso(s)
    return r


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


def cuenta_de(s: Session, unidad_id: UUID) -> UUID:
    fila = s.execute(text("SELECT id FROM cuenta WHERE unidad_id = :u"), {"u": unidad_id}).first()
    assert fila is not None, "la unidad no tiene cuenta"
    return UUID(str(fila.id))


@dataclass(frozen=True)
class ObligacionMigrada:
    id: UUID
    periodo: date
    vencimiento: date
    ordinaria: Dinero
    fondo_de_reserva: Dinero
    extraordinaria: Dinero
    emision_id: UUID | None

    @property
    def capital(self) -> Dinero:
        return self.ordinaria + self.fondo_de_reserva + self.extraordinaria


def obligaciones(s: Session, cuenta: UUID) -> list[ObligacionMigrada]:
    filas = s.execute(
        text(
            "SELECT id, periodo, vencimiento, ordinaria::text AS o, fondo_de_reserva::text AS f, "
            "extraordinaria::text AS e, emision_id FROM obligacion WHERE cuenta_id = :c "
            "ORDER BY periodo"
        ),
        {"c": cuenta},
    ).all()
    return [
        ObligacionMigrada(
            UUID(str(f.id)),
            f.periodo,
            f.vencimiento,
            d(f.o),
            d(f.f),
            d(f.e),
            None if f.emision_id is None else UUID(str(f.emision_id)),
        )
        for f in filas
    ]


def obligacion_del(s: Session, cuenta: UUID, periodo: date) -> ObligacionMigrada:
    del_periodo = [o for o in obligaciones(s, cuenta) if o.periodo == periodo]
    assert len(del_periodo) == 1, (
        f"se espera una obligación de {periodo} en la cuenta, hay {len(del_periodo)}"
    )
    return del_periodo[0]


@dataclass(frozen=True)
class Interes:
    id: UUID
    obligacion_id: UUID
    corte: date
    importe: Dinero
    emision_id: UUID | None


def intereses(s: Session, *, obligacion: UUID) -> list[Interes]:
    filas = s.execute(
        text(
            "SELECT id, obligacion_id, corte, importe::text AS importe, emision_id FROM movimiento "
            "WHERE tipo = 'interes' AND sentido = 'debito' AND obligacion_id = :o "
            "ORDER BY corte, registrado_en"
        ),
        {"o": obligacion},
    ).all()
    return [
        Interes(
            UUID(str(f.id)),
            UUID(str(f.obligacion_id)),
            f.corte,
            d(f.importe),
            None if f.emision_id is None else UUID(str(f.emision_id)),
        )
        for f in filas
    ]


def importado(s: Session, obligacion: UUID) -> Interes:
    """El interés traído en la carga: tipo `interes`, sin emisión, con corte en la migración."""
    sin_emision = [i for i in intereses(s, obligacion=obligacion) if i.emision_id is None]
    assert len(sin_emision) == 1, (
        f"se espera un interés importado sobre la obligación, hay {len(sin_emision)}"
    )
    return sin_emision[0]


def calculado(s: Session, obligacion: UUID, corte: date) -> Interes:
    del_corte = [
        i
        for i in intereses(s, obligacion=obligacion)
        if i.corte == corte and i.emision_id is not None
    ]
    assert len(del_corte) == 1, (
        f"se espera un interés con corte {corte} sobre la obligación, hay {len(del_corte)}"
    )
    return del_corte[0]


def sin_calculado(s: Session, obligacion: UUID, corte: date | None = None) -> None:
    hay = [
        i
        for i in intereses(s, obligacion=obligacion)
        if i.emision_id is not None and (corte is None or i.corte == corte)
    ]
    assert hay == [], (
        f"no se espera interés de una emisión, hay {[(i.corte, i.importe) for i in hay]}"
    )


@dataclass(frozen=True)
class Tramo:
    desde: date
    hasta: date
    dias: int
    base: Dinero


def tramos(s: Session, movimiento: UUID) -> list[Tramo]:
    filas = s.execute(
        text(
            "SELECT desde, hasta, dias, base::text AS base FROM tramo_de_interes "
            "WHERE movimiento_id = :m ORDER BY desde"
        ),
        {"m": movimiento},
    ).all()
    return [Tramo(f.desde, f.hasta, int(f.dias), d(f.base)) for f in filas]


def fechas(ts: Sequence[Tramo]) -> list[tuple[date, date]]:
    return [(t.desde, t.hasta) for t in ts]


def movimientos_saldo_inicial(s: Session, cuenta: UUID) -> list[tuple[Dinero, date]]:
    filas = s.execute(
        text(
            "SELECT importe::text AS importe, fecha_valor FROM movimiento "
            "WHERE cuenta_id = :c AND tipo = 'saldo_inicial' ORDER BY registrado_en"
        ),
        {"c": cuenta},
    ).all()
    return [(d(f.importe), f.fecha_valor) for f in filas]


def hay_tablas(s: Session) -> None:
    for tabla in TABLAS_NUEVAS:
        assert s.execute(text("SELECT to_regclass(:t)"), {"t": tabla}).scalar_one() is not None, (
            f"falta la tabla {tabla} (migración 0035)"
        )


def conteos(s: Session) -> dict[str, int]:
    tablas = ["cuenta", "obligacion", "movimiento", "imputacion"]
    for tabla in ("tramo_de_interes", *TABLAS_NUEVAS):
        if s.execute(text("SELECT to_regclass(:t)"), {"t": tabla}).scalar_one() is not None:
            tablas.append(tabla)
    return {
        t: int(s.execute(text(f"SELECT count(*) FROM {t}")).scalar_one())  # noqa: S608 - fijas
        for t in tablas
    }


@dataclass(frozen=True)
class Origen:
    fila: int | None
    obligacion_id: UUID | None
    movimiento_id: UUID | None


def origenes(s: Session, cuenta: UUID) -> list[Origen]:
    hay_tablas(s)
    filas = s.execute(
        text(
            "SELECT fila, obligacion_id, movimiento_id FROM origen_de_saldo_inicial "
            "WHERE cuenta_id = :c ORDER BY fila NULLS FIRST, obligacion_id, movimiento_id"
        ),
        {"c": cuenta},
    ).all()
    return [
        Origen(
            None if f.fila is None else int(f.fila),
            None if f.obligacion_id is None else UUID(str(f.obligacion_id)),
            None if f.movimiento_id is None else UUID(str(f.movimiento_id)),
        )
        for f in filas
    ]


def filas_de(
    origen: list[Origen], *, obligacion: UUID | None = None, movimiento: UUID | None = None
) -> set[int | None]:
    return {
        o.fila
        for o in origen
        if (obligacion is not None and o.obligacion_id == obligacion)
        or (movimiento is not None and o.movimiento_id == movimiento)
    }


def cargas(s: Session) -> list[Any]:
    hay_tablas(s)
    return list(
        s.execute(
            text(
                "SELECT id, complejo_id, operacion_id, fecha_de_migracion, origen, archivo, "
                "motivo, firma_del_pedido FROM carga_de_saldo_inicial ORDER BY registrado_en"
            )
        ).all()
    )


def leer(item: Any, *nombres: str) -> Any:
    for n in nombres:
        if isinstance(item, dict) and n in item:
            return item[n]
        if hasattr(item, n):
            return getattr(item, n)
    raise AssertionError(f"el resultado no trae {nombres}: {item!r}")


def totales(t: Any) -> tuple[Dinero, Dinero, Dinero]:
    """(capital, interés importado, crédito) de un `TotalesDeSaldoInicial`."""
    return (leer(t, "capital"), leer(t, "interes_importado"), leer(t, "credito"))


def conexion_app(base: BaseDeEdificio, admin: UUID) -> psycopg.Connection:
    c = base.conectar_app()
    c.autocommit = False
    fijar_tenant(c, admin)
    return c
