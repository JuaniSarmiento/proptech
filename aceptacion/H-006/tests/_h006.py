"""Ayudas de la aceptación de H-006 (situación de cobranza: R20, R30, D-109.4, D-143). Caja
negra: `situacion_de_cuenta` y `situacion_del_edificio` (design D6, contrato en
`aceptacion/H-006/CONTRATO.md`) y, para armar los datos, los casos de uso del libro que ya
existen (`registrar_emision`, `anular_emision`, `registrar_credito`, `correcciones.corregir`) y
`registrar_saldo_inicial` (H-005).

Lo que todavía no existe (el módulo `cobranza`) se pide con un `assert` y un mensaje, nunca con un
error de setup.

Base de los ejemplos: umbral $500, gracia 0 y tasa 0 (así las emisiones no generan interés que no
pida el caso); los casos de interés usan su propia tasa.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from types import ModuleType
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import correcciones, creditos, emisiones
from proptech_core.cuenta_corriente.aplicacion.correcciones import PedidoDeCorreccion
from proptech_core.cuenta_corriente.aplicacion.emisiones import EmisionRegistrada, ObligacionAEmitir

from .._cuenta_corriente import Mundo
from .._edificios import BaseDeEdificio, fijar_tenant

AGO, SEP, OCT, NOV = (date(2026, m, 1) for m in (8, 9, 10, 11))
PROPORCIONAL = "proporcional_por_dia"
COBRANZA = "proptech_core.cuenta_corriente.aplicacion.cobranza"
SALDO_INICIAL = "proptech_core.cuenta_corriente.aplicacion.saldo_inicial"
MIGRACION = date(2026, 10, 15)
HOY = date(2026, 11, 11)
ETIQUETAS = (
    "sin_deuda_vencida",
    "bajo_umbral",
    "deuda_de_intereses",
    "moroso_critico",
    "con_deuda_vencida",
)


def d(t: str) -> Dinero:
    return Dinero(t)


def dia(m: int, dd: int, a: int = 2026) -> date:
    return date(a, m, dd)


def reloj_del(dia_: date) -> Callable[[], datetime]:
    return lambda: datetime(dia_.year, dia_.month, dia_.day, 15, tzinfo=UTC)


# --- La situación de cobranza (todavía no existe en la rama) ---------------------------------


def _cobranza() -> ModuleType:
    try:
        return importlib.import_module(COBRANZA)
    except ImportError as e:
        raise AssertionError(f"falta `{COBRANZA}` (design D6): {e}") from None


def _funcion(nombre: str) -> Any:
    f = getattr(_cobranza(), nombre, None)
    assert f is not None, f"`{COBRANZA}` no define `{nombre}` (CONTRATO.md)"
    return f


def de_cuenta(s: Session, cuenta: UUID, fecha: date) -> Any:
    return _funcion("situacion_de_cuenta")(s, cuenta_id=cuenta, fecha=fecha)


def del_edificio(s: Session, complejo: UUID, fecha: date) -> list[Any]:
    return list(_funcion("situacion_del_edificio")(s, complejo_id=complejo, fecha=fecha))


def leer(item: Any, nombre: str) -> Any:
    """Un campo de una situación; en el listado del edificio puede venir anidado en `situacion`."""
    for fuente in (item, getattr(item, "situacion", None)):
        if fuente is None:
            continue
        if isinstance(fuente, dict) and nombre in fuente:
            return fuente[nombre]
        if hasattr(fuente, nombre):
            return getattr(fuente, nombre)
    raise AssertionError(f"la situación no trae `{nombre}` (CONTRATO.md): {item!r}")


def total_vencido(x: Any) -> Dinero:
    valor: Dinero = leer(x, "total_vencido")
    return valor


def liquidaciones(x: Any) -> int:
    return int(leer(x, "liquidaciones_vencidas"))


def bajo_umbral(x: Any) -> bool:
    return bool(leer(x, "bajo_umbral"))


def deuda_de_intereses(x: Any) -> bool:
    return bool(leer(x, "deuda_de_intereses"))


def moroso(x: Any) -> bool:
    return bool(leer(x, "moroso_critico"))


def etiqueta(x: Any) -> str:
    return str(leer(x, "etiqueta"))


def situacion(x: Any) -> tuple[Dinero, int, bool, bool, bool, str]:
    """(total vencido, liquidaciones, bajo el umbral, deuda de intereses, moroso, etiqueta)."""
    return (
        total_vencido(x),
        liquidaciones(x),
        bajo_umbral(x),
        deuda_de_intereses(x),
        moroso(x),
        etiqueta(x),
    )


# --- Configuración y libro ------------------------------------------------------------------


def configurar(
    base: BaseDeEdificio,
    mundo: Mundo,
    *,
    desde: date = date(2026, 1, 1),
    tasa: str = "0.00",
    gracia: int = 0,
    umbral: str = "500.00",
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
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '0.00', 10, 'unico') RETURNING id",
            (
                mundo.admin,
                complejo or mundo.complejo,
                mundo.persona,
                desde,
                tasa,
                umbral,
                gracia,
                PROPORCIONAL,
            ),
        ).fetchone()
        assert fila is not None
        c.commit()
        return UUID(str(fila[0]))


def confirmar_paso(s: Session) -> None:
    """Cada paso del libro en su propia transacción, como en producción (E2 del 4b)."""
    s.commit()
    s.begin()


def obl(mundo: Mundo, unidad: int, vencimiento: date, importe: str) -> ObligacionAEmitir:
    return ObligacionAEmitir(mundo.unidades[unidad], vencimiento, d(importe), d("0.00"), d("0.00"))


def emitir(
    s: Session,
    mundo: Mundo,
    periodo: date,
    obligaciones: list[ObligacionAEmitir],
    *,
    complejo: UUID | None = None,
) -> EmisionRegistrada:
    r = emisiones.registrar_emision(
        s,
        mundo.identidad,
        emision_id=uuid4(),
        complejo_id=complejo or mundo.complejo,
        periodo=periodo,
        obligaciones=obligaciones,
        request_id=uuid4(),
    )
    confirmar_paso(s)
    return r


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


def contra_asentar(s: Session, mundo: Mundo, movimiento: UUID) -> UUID:
    m = correcciones.corregir(
        s,
        mundo.identidad,
        complejo_id=mundo.complejo,
        pedido=PedidoDeCorreccion(
            "contra_asiento", uuid4(), "Pago mal cargado", movimiento_id=movimiento
        ),
        request_id=uuid4(),
    )
    confirmar_paso(s)
    return m


def cuenta_de(s: Session, unidad_id: UUID) -> UUID:
    fila = s.execute(text("SELECT id FROM cuenta WHERE unidad_id = :u"), {"u": unidad_id}).first()
    assert fila is not None, "la unidad no tiene cuenta"
    return UUID(str(fila.id))


def cuentas_de_unidad(s: Session, complejo: UUID) -> set[UUID]:
    filas = s.execute(
        text("SELECT id FROM cuenta WHERE complejo_id = :c AND unidad_id IS NOT NULL"),
        {"c": complejo},
    ).all()
    return {UUID(str(f.id)) for f in filas}


def intereses_de_la_cuenta(s: Session, cuenta: UUID) -> list[Dinero]:
    filas = s.execute(
        text(
            "SELECT importe::text AS importe FROM movimiento WHERE cuenta_id = :c "
            "AND tipo = 'interes' AND sentido = 'debito' ORDER BY corte, registrado_en"
        ),
        {"c": cuenta},
    ).all()
    return [d(f.importe) for f in filas]


def sentencias(s: Session) -> list[str]:
    """Cada sentencia que la sesión manda a PostgreSQL desde ahora."""
    vistas: list[str] = []

    @event.listens_for(s.get_bind(), "before_cursor_execute")
    def _ver(conn: Any, cursor: Any, sentencia: str, *args: Any) -> None:
        vistas.append(sentencia)

    return vistas


# --- Escenarios armados con el libro real ----------------------------------------------------


def solo_interes(s: Session, mundo: Mundo, unidad: int, capital: str) -> UUID:
    """Agosto de `capital` vencido el 10/08 y pagado entero el 25/08: la emisión de septiembre
    (corte 31/08) le registra el interés de los 15 días impagos (al 10%, $4.000 sobre $80.000 o
    $400 sobre $8.000), que queda como única deuda vencida del período. Exige configuración al
    10%."""
    r = emitir(s, mundo, AGO, [obl(mundo, unidad, dia(8, 10), capital)])
    cuenta = r.cuentas[mundo.unidades[unidad]]
    pagar(s, mundo, cuenta, capital, dia(8, 25))
    return cuenta


# --- Saldo inicial (H-005), sólo para armar datos migrados -----------------------------------


def _saldo_inicial() -> ModuleType:
    try:
        return importlib.import_module(SALDO_INICIAL)
    except ImportError as e:
        raise AssertionError(f"falta `{SALDO_INICIAL}` (H-005): {e}") from None


def _clase(nombre: str) -> Any:
    clase = getattr(_saldo_inicial(), nombre, None)
    assert clase is not None, f"`{SALDO_INICIAL}` no define `{nombre}` (H-005)"
    return clase


def deuda(
    fila: int, periodo: date, vencimiento: date, importe: str, *, interes: str = "0.00"
) -> Any:
    return _clase("FilaDeDeuda")(
        fila=fila,
        periodo=periodo,
        vencimiento=vencimiento,
        componente="ordinaria",
        importe=d(importe),
        interes_acumulado=d(interes),
    )


def total(fila: int, importe: str) -> Any:
    return _clase("FilaDeTotal")(fila=fila, importe=d(importe), interes_acumulado=d("0.00"))


def unidad(unidad_id: UUID, *filas: Any, modo: str = "detalle") -> Any:
    return _clase("UnidadDeSaldoInicial")(unidad_id=unidad_id, modo=modo, filas=tuple(filas))


def cargar(s: Session, mundo: Mundo, unidades: Sequence[Any]) -> None:
    registrar = getattr(_saldo_inicial(), "registrar_saldo_inicial", None)
    assert registrar is not None, f"`{SALDO_INICIAL}` no define `registrar_saldo_inicial`"
    registrar(
        s,
        mundo.identidad,
        complejo_id=mundo.complejo,
        operacion_id=uuid4(),
        fecha_de_migracion=MIGRACION,
        origen=_clase("OrigenDeCarga")(tipo="importador", archivo="saldos-octubre.xlsx"),
        unidades=list(unidades),
        request_id=uuid4(),
        reloj=reloj_del(HOY),
    )
    confirmar_paso(s)
