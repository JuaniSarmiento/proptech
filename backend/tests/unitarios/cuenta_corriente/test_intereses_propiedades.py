"""4.5 · Propiedades del interés por mora con hypothesis (R03, E1, E17, E19, PR-13, PR-15).

El oráculo calcula con `fractions.Fraction`, día por día, y agrupa por mes calendario con su propio
código: no importa nada de `intereses.py` salvo la función que se prueba y sus tipos (QA-4 del 4a).
Las pruebas encadenan cortes como la emisión: calculan, registran lo que el dominio devuelve,
contra-asientan intereses cualesquiera (no sólo el último) y vuelven a calcular. El modelo del
oráculo lleva su propia cuenta de lo cubierto, a partir de lo que él mismo esperaba cobrar.
"""

from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from fractions import Fraction
from math import floor
from uuid import uuid4

from hypothesis import assume, example, given, settings
from hypothesis import strategies as st

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.cuenta_corriente.dominio.errores import EntradaInvalida
from proptech_core.cuenta_corriente.dominio.estado import (
    ImputacionRegistrada,
    Movimiento,
    Obligacion,
    calcular_estado,
)
from proptech_core.cuenta_corriente.dominio.imputacion import Componente
from proptech_core.cuenta_corriente.dominio.intereses import (
    ConfiguracionDeInteres,
    FormaDeCalculo,
    InteresCalculado,
    calcular_intereses,
)

HOY = datetime(2026, 11, 11, tzinfo=UTC)
PROP: FormaDeCalculo = "proporcional_por_dia"
MES: FormaDeCalculo = "mes_entero"

#: Ejemplos por propiedad: lo bastante altos para que los mutantes de control fallen siempre.
EJEMPLOS = 400
PROPIEDAD = settings(max_examples=EJEMPLOS)


# ---------------------------------------------------------------------------------------------
# El escenario: una obligación, sus pagos y débitos de capital, y una secuencia de pasos
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Emitir:
    corte: date
    tasa: int  # centésimas de punto porcentual: 300 es 3,00%
    forma: FormaDeCalculo


@dataclass(frozen=True)
class Anular:
    cual: int  # índice, módulo la cantidad de intereses que cuentan


@dataclass(frozen=True)
class Escenario:
    capital: int  # centavos
    vencimiento: date
    gracia: int
    pagos: tuple[tuple[date, int], ...]  # (fecha valor, centavos); su suma no pasa el capital
    debitos: tuple[tuple[date, int], ...]
    pasos: tuple[Emitir | Anular, ...]


def fin_de_mes(anio: int, mes: int) -> date:
    anio += (mes - 1) // 12
    mes = (mes - 1) % 12 + 1
    siguiente = date(anio + (mes == 12), mes % 12 + 1, 1)
    return siguiente - timedelta(days=1)


def texto(centavos: int) -> str:
    return f"{centavos // 100}.{centavos % 100:02d}"


@st.composite
def escenarios(draw: st.DrawFn) -> Escenario:
    capital = draw(st.one_of(st.integers(1, 30_000), st.integers(1, 100_000_000)))
    vencimiento = date(2026, 9, 1) + timedelta(days=draw(st.integers(0, 60)))
    gracia = draw(st.sampled_from([0, 0, 0, 3, 5, 10]))
    pagos: list[tuple[date, int]] = []
    restante = capital
    for _ in range(draw(st.integers(0, 3))):
        if restante == 0:
            break
        importe = restante if draw(st.booleans()) else draw(st.integers(1, restante))
        restante -= importe
        pagos.append((vencimiento + timedelta(days=draw(st.integers(-3, 120))), importe))
    debitos = [
        (vencimiento + timedelta(days=draw(st.integers(0, 120))), draw(st.integers(1, capital)))
        for _ in range(draw(st.integers(0, 2)))
    ]
    mes = vencimiento.month + draw(st.integers(0, 1))
    pasos: list[Emitir | Anular] = []
    for n in range(draw(st.integers(1, 7))):
        if n and draw(st.integers(0, 3)) == 0:
            pasos.append(Anular(draw(st.integers(0, 5))))
            continue
        mes += draw(st.integers(0, 2)) if n else 0
        tasa = draw(st.one_of(st.sampled_from([0, 100, 300, 600]), st.integers(0, 1500)))
        pasos.append(
            Emitir(fin_de_mes(vencimiento.year, mes), tasa, draw(st.sampled_from([PROP, MES])))
        )
    return Escenario(capital, vencimiento, gracia, tuple(pagos), tuple(debitos), tuple(pasos))


# ---------------------------------------------------------------------------------------------
# Producción: la cuenta que encadena cortes con `calcular_intereses`
# ---------------------------------------------------------------------------------------------


class Cuenta:
    def __init__(self, e: Escenario) -> None:
        self.e = e
        self.obligacion = Obligacion(
            uuid4(),
            None,
            e.vencimiento.replace(day=1),
            e.vencimiento,
            Dinero(texto(e.capital)),
            Dinero("0.00"),
            Dinero("0.00"),
        )
        self.movimientos: list[Movimiento] = []
        self.imputaciones: list[ImputacionRegistrada] = []
        for orden, (fecha, centavos) in enumerate(e.pagos, start=1):
            pago = Movimiento(uuid4(), "pago", "credito", Dinero(texto(centavos)), fecha, HOY)
            self.movimientos.append(pago)
            self.imputaciones.append(
                ImputacionRegistrada(
                    pago.id,
                    self.obligacion.id,
                    Componente.ORDINARIA,
                    Dinero(texto(centavos)),
                    orden,
                )
            )
        for fecha, centavos in e.debitos:
            self.movimientos.append(
                Movimiento(
                    uuid4(),
                    "ajuste",
                    "debito",
                    Dinero(texto(centavos)),
                    fecha,
                    HOY,
                    self.obligacion.id,
                    Componente.ORDINARIA,
                )
            )
        #: Los intereses registrados, en orden, y si cuentan (lo lleva la prueba, no el dominio).
        self.intereses: list[Movimiento] = []
        self.cuentan: list[bool] = []

    def emitir(
        self, corte: date, tasa: int, forma: FormaDeCalculo
    ) -> tuple[InteresCalculado, ...] | None:
        """El resultado del dominio, registrado en el libro; `None` si el dominio lanzó."""
        estado = calcular_estado([self.obligacion], self.movimientos, self.imputaciones, [])
        configuracion = ConfiguracionDeInteres(
            Porcentaje(f"{tasa // 100}.{tasa % 100:02d}"), self.e.gracia, forma
        )
        try:
            resultado = calcular_intereses(estado, self.movimientos, corte, configuracion)
        except EntradaInvalida:
            return None
        for interes in resultado:
            movimiento = Movimiento(
                uuid4(),
                "interes",
                "debito",
                interes.importe,
                interes.corte,
                HOY,
                self.obligacion.id,
                Componente.INTERES,
                corte=interes.corte,
                tramos=tuple((t.desde, t.hasta) for t in interes.tramos),
            )
            self.movimientos.append(movimiento)
            self.intereses.append(movimiento)
            self.cuentan.append(True)
        return resultado

    def anular(self, indice: int) -> int | None:
        """Contra-asienta el `indice`-ésimo (módulo) interés que cuenta; devuelve su posición."""
        vigentes = [n for n, cuenta in enumerate(self.cuentan) if cuenta]
        if not vigentes:
            return None
        posicion = vigentes[indice % len(vigentes)]
        interes = self.intereses[posicion]
        self.movimientos.append(
            Movimiento(
                uuid4(),
                "contra_asiento",
                "credito",
                interes.importe,
                interes.fecha_valor,
                HOY,
                self.obligacion.id,
                Componente.INTERES,
                corrige_a=interes.id,
            )
        )
        self.cuentan[posicion] = False
        return posicion


# ---------------------------------------------------------------------------------------------
# El oráculo: Fraction, día por día, con su propia agrupación por mes calendario
# ---------------------------------------------------------------------------------------------


class Invalido:
    """El oráculo también rechaza: mes entero con días a cobrar que no son un solo bloque."""


INVALIDO = Invalido()


@dataclass(frozen=True)
class Esperado:
    centavos: int
    dias: frozenset[date]
    tramos: tuple[tuple[date, date, Fraction], ...]  # (primer día, último día, base)


def medio_hacia_arriba(importe: Fraction) -> int:
    """Centavos del importe, redondeando el medio centavo hacia arriba (importes no negativos)."""
    return floor(importe * 100 + Fraction(1, 2))


def base_del_dia(e: Escenario, dia: date) -> Fraction:
    """Capital impago del día: lo pagado o sumado baja o sube la base desde el día siguiente."""
    total = Fraction(e.capital, 100)
    for fecha, centavos in e.debitos:
        if fecha < dia:
            total += Fraction(centavos, 100)
    for fecha, centavos in e.pagos:
        efectiva = e.vencimiento if fecha <= e.vencimiento + timedelta(days=e.gracia) else fecha
        if efectiva < dia:
            total -= Fraction(centavos, 100)
    return max(total, Fraction(0))


def esperado(
    e: Escenario,
    corte: date,
    tasa: int,
    forma: FormaDeCalculo,
    cubiertos: frozenset[date],
    cortes_ocupados: frozenset[date],
) -> Esperado | Invalido | None:
    if corte in cortes_ocupados or (corte - e.vencimiento).days <= e.gracia:
        return None
    inicio = e.vencimiento + timedelta(days=1)
    a_cobrar = [
        inicio + timedelta(days=n)
        for n in range((corte - inicio).days + 1)
        if inicio + timedelta(days=n) not in cubiertos
    ]
    tasa_mensual = Fraction(tasa, 100)
    total = Fraction(0)
    dias: set[date] = set()
    tramos: list[tuple[date, date, Fraction]] = []
    if forma == PROP:
        for dia in a_cobrar:
            base = base_del_dia(e, dia)
            if base > 0:
                total += base * tasa_mensual / 100 / 30
                dias.add(dia)
                tramos.append((dia, dia, base))
    else:
        por_mes: dict[tuple[int, int], list[date]] = {}
        for dia in a_cobrar:
            por_mes.setdefault((dia.year, dia.month), []).append(dia)
        for del_mes in por_mes.values():
            primero, ultimo = del_mes[0], del_mes[-1]
            if (ultimo - primero).days + 1 != len(del_mes):
                return INVALIDO
            if ultimo != fin_de_mes(ultimo.year, ultimo.month):
                return INVALIDO
            base = base_del_dia(e, primero)
            if base > 0:
                total += base * tasa_mensual / 100
                dias.update(del_mes)
                tramos.append((primero, ultimo, base))
    centavos = medio_hacia_arriba(total)
    if centavos == 0:
        return None
    return Esperado(centavos, frozenset(dias), tuple(tramos))


def centavos_de(dinero: Dinero) -> int:
    entero, _, fraccion = dinero.a_texto().partition(".")
    return int(entero) * 100 + int(fraccion)


def dias_del_tramo(desde: date, hasta: date) -> list[date]:
    return [desde + timedelta(days=n) for n in range((hasta - desde).days + 1)]


# ---------------------------------------------------------------------------------------------
# La ejecución paso a paso, con lo que esperaba el oráculo
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PasoEjecutado:
    emitir: Emitir
    resultado: tuple[InteresCalculado, ...] | None
    esperado: Esperado | Invalido | None
    cubiertos_oraculo: frozenset[date]
    #: Un elemento por día de cada tramo de los intereses que cuentan (con repetidos si se solapan).
    cubiertos_produccion: tuple[date, ...]
    #: Meses de los tramos que cuentan y que se calcularon con mes entero.
    meses_de_mes_entero: tuple[tuple[int, int], ...]


def ejecutar(e: Escenario) -> Iterator[PasoEjecutado]:
    cuenta = Cuenta(e)
    registros: list[tuple[date, bool, frozenset[date]]] = []  # del oráculo: corte, cuenta, días
    formas: list[FormaDeCalculo] = []
    for paso in e.pasos:
        if isinstance(paso, Anular):
            posicion = cuenta.anular(paso.cual)
            if posicion is not None and posicion < len(registros):
                corte, _, dias = registros[posicion]
                registros[posicion] = (corte, False, dias)
            continue
        cubiertos = frozenset(d for _, cuenta_, dias in registros if cuenta_ for d in dias)
        ocupados = frozenset(corte for corte, _, _ in registros)
        previsto = esperado(e, paso.corte, paso.tasa, paso.forma, cubiertos, ocupados)
        resultado = cuenta.emitir(paso.corte, paso.tasa, paso.forma)
        if isinstance(previsto, Esperado):
            registros.append((paso.corte, True, previsto.dias))
            formas.append(paso.forma)
        if resultado:
            # Lo registrado por producción va en la misma posición que lo del oráculo mientras
            # coinciden; si no coinciden, la propiedad que mira el paso ya falló.
            while len(formas) < len(cuenta.intereses):
                formas.append(paso.forma)
        yield PasoEjecutado(
            paso,
            resultado,
            previsto,
            frozenset(d for _, cuenta_, dias in registros if cuenta_ for d in dias),
            tuple(
                dia
                for n, interes in enumerate(cuenta.intereses)
                if cuenta.cuentan[n]
                for desde, hasta in interes.tramos
                for dia in dias_del_tramo(desde, hasta)
            ),
            tuple(
                (desde.year, desde.month)
                for n, interes in enumerate(cuenta.intereses)
                if cuenta.cuentan[n] and formas[n] == MES
                for desde, _ in interes.tramos
            ),
        )


# Los dos casos fijos de la tarea: el discriminante entre las dos formas con un pago total.
PAGO_TOTAL_PROPORCIONAL = Escenario(
    10_000_000,
    date(2026, 9, 10),
    0,
    ((date(2026, 9, 20), 10_000_000),),
    (),
    (Emitir(date(2026, 9, 30), 300, PROP),),
)
PAGO_TOTAL_MES_ENTERO = replace(
    PAGO_TOTAL_PROPORCIONAL, pasos=(Emitir(date(2026, 9, 30), 300, MES),)
)


# ---------------------------------------------------------------------------------------------
# Propiedades
# ---------------------------------------------------------------------------------------------


def suma_exacta_de_los_tramos(
    interes: InteresCalculado, forma: FormaDeCalculo, tasa: int
) -> Fraction:
    mensual = Fraction(tasa, 100)
    total = Fraction(0)
    for tramo in interes.tramos:
        base = Fraction(tramo.base.a_texto())
        total += base * mensual / 100 * (Fraction(tramo.dias, 30) if forma == PROP else 1)
    return total


@PROPIEDAD
@example(e=PAGO_TOTAL_PROPORCIONAL)
@example(e=PAGO_TOTAL_MES_ENTERO)
@given(e=escenarios())
def test_el_importe_es_el_redondeo_medio_hacia_arriba_de_la_suma_exacta_de_los_tramos(
    e: Escenario,
) -> None:
    for paso in ejecutar(e):
        if isinstance(paso.esperado, Invalido):
            assert paso.resultado is None
            continue
        assert paso.resultado is not None, "el dominio lanzó donde el oráculo calcula"
        if paso.esperado is None:
            assert paso.resultado == ()
            continue
        assert len(paso.resultado) == 1, "el oráculo espera un interés y el dominio no devuelve uno"
        interes = paso.resultado[0]
        suma = suma_exacta_de_los_tramos(interes, paso.emitir.forma, paso.emitir.tasa)
        assert centavos_de(interes.importe) == medio_hacia_arriba(suma)
        assert centavos_de(interes.importe) == paso.esperado.centavos


@PROPIEDAD
@given(e=escenarios())
def test_el_interes_nunca_es_negativo(e: Escenario) -> None:
    for paso in ejecutar(e):
        for interes in paso.resultado or ():
            assert centavos_de(interes.importe) > 0
            assert interes.tramos
            for tramo in interes.tramos:
                assert tramo.dias > 0
                assert Fraction(tramo.base.a_texto()) > 0


@PROPIEDAD
@given(e=escenarios())
def test_con_tasa_cero_no_hay_importe(e: Escenario) -> None:
    for paso in ejecutar(e):
        if paso.emitir.tasa == 0:
            assert not paso.resultado


@PROPIEDAD
@given(e=escenarios())
def test_con_base_cero_no_hay_importe(e: Escenario) -> None:
    # Todo el capital pagado el día del vencimiento: ningún día tiene base positiva.
    pagado = replace(e, pagos=((e.vencimiento, e.capital),), debitos=())
    for paso in ejecutar(pagado):
        assert not paso.resultado


@PROPIEDAD
@given(e=escenarios(), data=st.data())
def test_agregar_un_pago_nunca_sube_el_interes(e: Escenario, data: st.DataObject) -> None:
    restante = e.capital - sum(c for _, c in e.pagos)
    assume(restante > 0)
    corte = fin_de_mes(e.vencimiento.year, e.vencimiento.month + data.draw(st.integers(0, 4)))
    forma = data.draw(st.sampled_from([PROP, MES]))
    tasa = data.draw(st.integers(1, 1500))
    nuevo = (
        e.vencimiento + timedelta(days=data.draw(st.integers(-3, 120))),
        data.draw(st.integers(1, restante)),
    )

    def importe(escenario: Escenario) -> int:
        resultado = Cuenta(escenario).emitir(corte, tasa, forma)
        assert resultado is not None
        return sum(centavos_de(i.importe) for i in resultado)

    sin_historia = replace(e, pasos=())
    assert importe(replace(sin_historia, pagos=(*e.pagos, nuevo))) <= importe(sin_historia)


@PROPIEDAD
@given(e=escenarios())
def test_ningun_dia_queda_cubierto_dos_veces_por_intereses_que_cuentan(e: Escenario) -> None:
    for paso in ejecutar(e):
        assert len(paso.cubiertos_produccion) == len(set(paso.cubiertos_produccion))


@PROPIEDAD
@example(e=PAGO_TOTAL_PROPORCIONAL)
@example(e=PAGO_TOTAL_MES_ENTERO)
@given(e=escenarios())
def test_lo_cubierto_es_exactamente_lo_que_el_oraculo_asigna_a_un_tramo_con_base(
    e: Escenario,
) -> None:
    inicio = e.vencimiento + timedelta(days=1)
    for paso in ejecutar(e):
        if not isinstance(paso.esperado, Esperado):
            continue
        assert paso.resultado, "el oráculo espera que este corte registre"
        assert set(paso.cubiertos_produccion) == set(paso.cubiertos_oraculo)
        assert all(inicio <= dia <= paso.emitir.corte for dia in paso.cubiertos_oraculo)
        # Los tramos de este corte, día por día y con su base, contra lo que asigna el oráculo.
        interes = paso.resultado[0]
        dias_de_produccion: set[date] = set()
        for tramo in interes.tramos:
            for dia in dias_del_tramo(tramo.desde, tramo.hasta):
                dias_de_produccion.add(dia)
                if paso.emitir.forma == PROP:
                    assert Fraction(tramo.base.a_texto()) == base_del_dia(e, dia)
            assert tramo.dias == (tramo.hasta - tramo.desde).days + 1
            if paso.emitir.forma == MES:
                assert Fraction(tramo.base.a_texto()) == base_del_dia(e, tramo.desde)
        assert dias_de_produccion == paso.esperado.dias


@PROPIEDAD
@example(e=PAGO_TOTAL_MES_ENTERO)
@given(e=escenarios())
def test_en_mes_entero_cada_tramo_es_de_un_mes_y_hay_uno_por_mes(e: Escenario) -> None:
    for paso in ejecutar(e):
        if paso.emitir.forma == MES:
            for interes in paso.resultado or ():
                for tramo in interes.tramos:
                    assert (tramo.desde.year, tramo.desde.month) == (
                        tramo.hasta.year,
                        tramo.hasta.month,
                    )
                    assert tramo.hasta == fin_de_mes(tramo.hasta.year, tramo.hasta.month)
        assert len(paso.meses_de_mes_entero) == len(set(paso.meses_de_mes_entero))


@PROPIEDAD
@given(e=escenarios(), data=st.data())
def test_partir_un_tramo_proporcional_en_dos_cortes_suma_lo_mismo_salvo_el_redondeo(
    e: Escenario, data: st.DataObject
) -> None:
    primero = fin_de_mes(e.vencimiento.year, e.vencimiento.month + data.draw(st.integers(0, 2)))
    segundo = fin_de_mes(primero.year, primero.month + data.draw(st.integers(1, 2)))
    tasa = data.draw(st.integers(1, 1500))
    sin_historia = replace(e, pasos=())

    junto = Cuenta(sin_historia).emitir(segundo, tasa, PROP)
    partida = Cuenta(sin_historia)
    antes = partida.emitir(primero, tasa, PROP)
    despues = partida.emitir(segundo, tasa, PROP)
    assert junto is not None and antes is not None and despues is not None
    total_junto = sum(centavos_de(i.importe) for i in junto)
    total_partido = sum(centavos_de(i.importe) for i in (*antes, *despues))
    assert abs(total_junto - total_partido) <= 1
