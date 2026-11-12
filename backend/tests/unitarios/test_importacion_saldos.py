"""Tarea 2.1 de `importacion-desde-excel`: la validación pura de las hojas `Saldos` y `Control`
(design D1, D2, D3, E14; contrato del saldo inicial, E11 y E16 del 4c). Sin Excel y sin base: se arma
la `PlantillaLeida` a mano, con los valores como los entrega el lector (fechas ISO, números en
notación fija). Datos inventados."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.importacion.dominio.plantilla import (
    ENCABEZADOS_POR_HOJA,
    ErrorDeImportacion,
    FilaLeida,
    HojaLeida,
    PlantillaLeida,
)
from proptech_core.importacion.dominio.saldos import (
    BorradorValidado,
    FilaDeControl,
    FilaDeSaldo,
    validar_saldos,
)

SALDOS = ENCABEZADOS_POR_HOJA["Saldos"]
CONTROL = ENCABEZADOS_POR_HOJA["Control"]
UNIDADES = frozenset({"1A", "1B", "2A", "2B", "3C", "4D", "5E"})
MIGRACION = date(2026, 10, 15)

Fila = dict[str, str | None]


def _s(
    unidad: str,
    periodo: str | None,
    vencimiento: str | None,
    concepto: str | None,
    importe: str | None,
    interes: str | None = None,
) -> Fila:
    return dict(
        zip(SALDOS, (unidad, periodo, vencimiento, concepto, importe, interes), strict=True)
    )


def _saldos_base() -> list[Fila]:
    """Las filas 2 a 8 de la base de la historia (H-008)."""
    return [
        _s("1A", "2026-08", "2026-08-10", "Ordinaria", "80000.00", "4000.00"),
        _s("1A", "2026-09", "2026-09-10", "Ordinaria", "85000.00"),
        _s("1B", "2026-09", "2026-09-10", "Ordinaria", "85000.00"),
        _s("1B", "2026-09", "2026-09-10", "Extraordinaria", "20000.00"),
        _s("2A", None, None, None, "50000.00", "2000.00"),
        _s("2B", None, None, None, "-3000.00"),
        _s("4D", None, None, None, "-3000.00"),
    ]


def _control_base() -> list[Fila]:
    return [
        {"Unidad": "1A", "Saldo según el administrador": "169000.00"},
        {"Unidad": "1B", "Saldo según el administrador": "105000.00"},
        {"Unidad": "2A", "Saldo según el administrador": "52000.00"},
        {"Unidad": "2B", "Saldo según el administrador": "-3000.00"},
        {"Unidad": "4D", "Saldo según el administrador": "-3000.00"},
    ]


def _hoja(
    nombre: str,
    filas: list[Fila],
    encabezados: tuple[str, ...],
    numericas: Mapping[int, frozenset[str]] | None = None,
    sin_cache: Mapping[int, frozenset[str]] | None = None,
) -> HojaLeida:
    leidas = tuple(
        FilaLeida(
            numero=i + 2,
            valores={c: v for c, v in fila.items() if c in encabezados},
            formulas_sin_cache=(sin_cache or {}).get(i + 2, frozenset()),
            numericas=(numericas or {}).get(i + 2, frozenset()),
        )
        for i, fila in enumerate(filas)
    )
    return HojaLeida(nombre, encabezados, leidas)


def _plantilla(
    saldos: list[Fila] | None = None,
    control: list[Fila] | None = None,
    *,
    sin_saldos: bool = False,
    sin_control: bool = False,
    enc_saldos: tuple[str, ...] = SALDOS,
    enc_control: tuple[str, ...] = CONTROL,
    numericas_saldos: Mapping[int, frozenset[str]] | None = None,
    sin_cache_saldos: Mapping[int, frozenset[str]] | None = None,
    numericas_control: Mapping[int, frozenset[str]] | None = None,
) -> PlantillaLeida:
    hojas: dict[str, HojaLeida] = {}
    if not sin_saldos:
        hojas["Saldos"] = _hoja(
            "Saldos",
            _saldos_base() if saldos is None else saldos,
            enc_saldos,
            numericas_saldos,
            sin_cache_saldos,
        )
    if not sin_control:
        hojas["Control"] = _hoja(
            "Control",
            _control_base() if control is None else control,
            enc_control,
            numericas_control,
        )
    return PlantillaLeida(hojas=hojas)


def _con(filas: list[Fila], fila: int, **cambios: str | None) -> list[Fila]:
    """Copia de `filas` con la `fila` del Excel (2 en adelante) cambiada: `Interés_acumulado`
    escribe la columna con espacio."""
    nuevas = [dict(f) for f in filas]
    for columna, valor in cambios.items():
        nuevas[fila - 2][columna.replace("_", " ")] = valor
    return nuevas


def _valida(plantilla: PlantillaLeida, fecha_de_migracion: date = MIGRACION) -> BorradorValidado:
    borrador, errores = validar_saldos(
        plantilla, unidades=UNIDADES, fecha_de_migracion=fecha_de_migracion
    )
    assert errores == (), f"se esperaba un archivo válido y llegaron errores: {errores}"
    assert borrador is not None, "un archivo válido con saldos devolvió un borrador vacío"
    return borrador


def _errores(
    plantilla: PlantillaLeida, fecha_de_migracion: date = MIGRACION
) -> list[ErrorDeImportacion]:
    borrador, errores = validar_saldos(
        plantilla, unidades=UNIDADES, fecha_de_migracion=fecha_de_migracion
    )
    assert borrador is None, "un archivo con errores no devuelve borrador (todo o nada)"
    assert errores, "se esperaban errores y el archivo se aceptó"
    return list(errores)


def _donde(errores: list[ErrorDeImportacion]) -> set[tuple[str | None, int | None, str | None]]:
    return {(e.hoja, e.fila, e.columna) for e in errores}


# --- Un archivo válido ------------------------------------------------------------------------


def test_un_archivo_valido_devuelve_sus_filas_ya_tipadas() -> None:
    borrador = _valida(_plantilla())
    assert borrador.filas[0] == FilaDeSaldo(
        fila=2,
        unidad="1A",
        tipo="detalle",
        periodo=date(2026, 8, 1),
        vencimiento=date(2026, 8, 10),
        concepto="ordinaria",
        importe=Dinero("80000.00"),
        interes_acumulado=Dinero("4000.00"),
    )
    assert borrador.filas[3] == FilaDeSaldo(
        5,
        "1B",
        "detalle",
        date(2026, 9, 1),
        date(2026, 9, 10),
        "extraordinaria",
        Dinero("20000.00"),
        Dinero("0.00"),
    )
    assert borrador.filas[4] == FilaDeSaldo(
        6, "2A", "total", None, None, None, Dinero("50000.00"), Dinero("2000.00")
    )
    assert borrador.filas[5] == FilaDeSaldo(
        7, "2B", "credito", None, None, None, Dinero("3000.00"), Dinero("0.00")
    ), "el crédito se guarda positivo con tipo credito"
    assert [f.fila for f in borrador.filas] == [2, 3, 4, 5, 6, 7, 8]
    assert borrador.controles == (
        FilaDeControl(2, "1A", Dinero("169000.00")),
        FilaDeControl(3, "1B", Dinero("105000.00")),
        FilaDeControl(4, "2A", Dinero("52000.00")),
        FilaDeControl(5, "2B", Dinero("-3000.00")),
        FilaDeControl(6, "4D", Dinero("-3000.00")),
    )


@pytest.mark.parametrize("concepto", ["Ordinaria", "Fondo de reserva", "Extraordinaria"])
def test_los_tres_conceptos_se_traducen_a_su_vocabulario(concepto: str) -> None:
    saldos = _con(_saldos_base(), 2, Concepto=concepto)
    esperado = {
        "Ordinaria": "ordinaria",
        "Fondo de reserva": "fondo_de_reserva",
        "Extraordinaria": "extraordinaria",
    }[concepto]
    assert _valida(_plantilla(saldos)).filas[0].concepto == esperado


@pytest.mark.parametrize("periodo", ["2026-08", "2026-08-01"], ids=["AAAA-MM", "fecha con dia 1"])
def test_el_periodo_acepta_aaaa_mm_o_una_fecha_con_dia_1(periodo: str) -> None:
    saldos = _con(_saldos_base(), 2, Período=periodo)
    assert _valida(_plantilla(saldos)).filas[0].periodo == date(2026, 8, 1)


def test_el_mes_de_la_migracion_y_su_fecha_se_aceptan() -> None:
    saldos = _con(_saldos_base(), 3, Período="2026-10", Vencimiento="2026-10-15")
    fila = _valida(_plantilla(saldos)).filas[1]
    assert (fila.periodo, fila.vencimiento) == (date(2026, 10, 1), date(2026, 10, 15))


def test_el_vencimiento_acepta_dia_mes_anio_con_barras() -> None:
    saldos = _con(_saldos_base(), 2, Vencimiento="10/08/2026")
    assert _valida(_plantilla(saldos)).filas[0].vencimiento == date(2026, 8, 10)


def test_un_total_unico_puede_repetirse_y_un_credito_puede_repetirse() -> None:
    saldos = [
        _s("2A", None, None, None, "50000.00"),
        _s("2A", None, None, None, "1000.00", "10.00"),
        _s("2B", None, None, None, "-3000.00"),
        _s("2B", None, None, None, "-500.00"),
    ]
    assert len(_valida(_plantilla(saldos, [])).filas) == 4


def test_el_credito_no_cuenta_en_la_mezcla_de_modos() -> None:
    saldos = [
        _s("1A", None, None, None, "-500.00"),
        _s("1A", "2026-09", "2026-09-10", "Ordinaria", "85000.00"),
        _s("1A", None, None, None, "-100.00"),
    ]
    assert len(_valida(_plantilla(saldos, [])).filas) == 3


def test_una_celda_vacia_de_interes_vale_cero_y_un_cero_tambien() -> None:
    saldos = _con(_saldos_base(), 3, Interés_acumulado="0.00")
    filas = _valida(_plantilla(saldos)).filas
    assert filas[1].interes_acumulado == Dinero("0.00") == filas[2].interes_acumulado


# --- Los números (E14) ------------------------------------------------------------------------


@pytest.mark.parametrize("importe", ["85.000,00", "85000,00", "85000.00", "85000"])
def test_importes_con_coma_con_punto_o_enteros(importe: str) -> None:
    saldos = _con(_saldos_base(), 3, Importe=importe)
    assert _valida(_plantilla(saldos)).filas[1].importe == Dinero("85000.00")


def test_una_celda_numerica_no_es_ambigua() -> None:
    saldos = _con(_saldos_base(), 3, Importe="85.125")
    plantilla = _plantilla(saldos, numericas_saldos={3: frozenset({"Importe"})})
    # 85.125 numérico tiene tres decimales: sigue siendo error, pero por decimales, no por ambiguo
    errores = _errores(plantilla)
    assert ("Saldos", 3, "Importe") in _donde(errores)
    assert "ambiguo" not in [e for e in errores if e.fila == 3][0].motivo


@pytest.mark.parametrize(
    ("importe", "esperado"),
    [("85000.123", "decimales"), ("1.234", "ambiguo"), ("abc", "no es un número")],
)
def test_importe_con_tres_decimales_ambiguo_o_no_numerico(importe: str, esperado: str) -> None:
    saldos = _con(_saldos_base(), 3, Importe=importe)
    errores = _errores(_plantilla(saldos))
    assert _donde(errores) == {("Saldos", 3, "Importe")}
    assert esperado in errores[0].motivo
    assert importe not in errores[0].motivo, "el motivo no repite lo que escribió la persona"


def test_importe_o_control_que_no_entran_en_numeric_14_2() -> None:
    saldos = _con(_saldos_base(), 3, Importe="1000000000000.00")
    control = [{"Unidad": "1A", "Saldo según el administrador": "-1000000000000,00"}]
    donde = _donde(_errores(_plantilla(saldos, control)))
    assert {("Saldos", 3, "Importe"), ("Control", 2, "Saldo según el administrador")} <= donde


def test_importe_vacio_es_error() -> None:
    saldos = _con(_saldos_base(), 3, Importe=None)
    assert ("Saldos", 3, "Importe") in _donde(_errores(_plantilla(saldos)))


def test_interes_con_tres_decimales_o_negativo() -> None:
    saldos = _con(_saldos_base(), 2, Interés_acumulado="-1.00")
    saldos = _con(saldos, 3, Interés_acumulado="1,001")
    assert _donde(_errores(_plantilla(saldos))) == {
        ("Saldos", 2, "Interés acumulado"),
        ("Saldos", 3, "Interés acumulado"),
    }


def test_una_formula_sin_valor_guardado_es_error_de_la_celda() -> None:
    saldos = _con(_saldos_base(), 3, Importe=None)
    plantilla = _plantilla(saldos, sin_cache_saldos={3: frozenset({"Importe"})})
    errores = _errores(plantilla)
    assert _donde(errores) == {("Saldos", 3, "Importe")}
    assert "fórmula" in errores[0].motivo


# --- Errores de fila de Saldos (contrato de H-008) --------------------------------------------

CASOS: dict[str, tuple[dict[int, dict[str, str | None]], tuple[str, int, str]]] = {
    "unidad_inexistente": ({2: {"Unidad": "9Z"}}, ("Saldos", 2, "Unidad")),
    "unidad_vacia": ({2: {"Unidad": None}}, ("Saldos", 2, "Unidad")),
    "periodo_posterior_al_mes_de_migracion": (
        {3: {"Período": "2026-11"}},
        ("Saldos", 3, "Período"),
    ),
    "periodo_que_no_es_un_mes": ({3: {"Período": "2026-13"}}, ("Saldos", 3, "Período")),
    "periodo_con_dia_distinto_de_1": ({3: {"Período": "2026-09-15"}}, ("Saldos", 3, "Período")),
    "periodo_texto": ({3: {"Período": "septiembre"}}, ("Saldos", 3, "Período")),
    "vencimiento_posterior_a_la_migracion": (
        {3: {"Vencimiento": "2026-10-16"}},
        ("Saldos", 3, "Vencimiento"),
    ),
    "vencimiento_vacio_con_periodo": ({3: {"Vencimiento": None}}, ("Saldos", 3, "Vencimiento")),
    "vencimiento_que_no_es_una_fecha": (
        {3: {"Vencimiento": "2026-02-30"}},
        ("Saldos", 3, "Vencimiento"),
    ),
    "concepto_fuera_del_vocabulario": ({3: {"Concepto": "Expensa"}}, ("Saldos", 3, "Concepto")),
    "concepto_en_minuscula": ({3: {"Concepto": "ordinaria"}}, ("Saldos", 3, "Concepto")),
    "concepto_vacio_con_periodo": ({3: {"Concepto": None}}, ("Saldos", 3, "Concepto")),
    "total_con_concepto": ({6: {"Concepto": "Ordinaria"}}, ("Saldos", 6, "Concepto")),
    "total_con_vencimiento": ({6: {"Vencimiento": "2026-09-10"}}, ("Saldos", 6, "Vencimiento")),
    "credito_con_periodo": ({7: {"Período": "2026-09"}}, ("Saldos", 7, "Período")),
    "credito_con_concepto": ({8: {"Concepto": "Ordinaria"}}, ("Saldos", 8, "Concepto")),
    "credito_con_vencimiento": ({7: {"Vencimiento": "2026-09-10"}}, ("Saldos", 7, "Vencimiento")),
    "credito_con_interes": (
        {7: {"Interés acumulado": "10.00"}},
        ("Saldos", 7, "Interés acumulado"),
    ),
}


@pytest.mark.parametrize("caso", sorted(CASOS))
def test_fila_de_saldos_invalida_nombra_hoja_fila_y_columna(caso: str) -> None:
    cambios, esperado = CASOS[caso]
    saldos = _saldos_base()
    for fila, columnas in cambios.items():
        saldos = _con(saldos, fila, **{c.replace(" ", "_"): v for c, v in columnas.items()})
    errores = _errores(_plantilla(saldos))
    assert esperado in _donde(errores), f"{caso}: {_donde(errores)}"
    assert all(e.hoja == "Saldos" for e in errores)
    assert all(e.motivo for e in errores)


def test_dos_vencimientos_en_el_mismo_periodo_error_en_la_segunda_fila() -> None:
    saldos = _con(_saldos_base(), 5, Vencimiento="2026-09-15")
    assert _donde(_errores(_plantilla(saldos))) == {("Saldos", 5, "Vencimiento")}


def test_dos_vencimientos_se_miden_por_unidad_y_por_periodo() -> None:
    saldos = [
        _s("1A", "2026-09", "2026-09-10", "Ordinaria", "1000.00"),
        _s("1B", "2026-09", "2026-09-15", "Ordinaria", "1000.00"),  # otra unidad: otro vencimiento
        _s("1A", "2026-08", "2026-08-12", "Ordinaria", "1000.00"),  # otro período
    ]
    _valida(_plantilla(saldos, []))


def test_periodo_con_capital_cero_y_solo_interes() -> None:
    saldos = [
        *_saldos_base(),
        _s("1A", "2026-07", "2026-07-10", "Ordinaria", "0.00", "500.00"),
    ]
    assert _donde(_errores(_plantilla(saldos))) == {("Saldos", 9, "Interés acumulado")}


def test_periodo_con_capital_cero_se_suma_por_periodo_no_por_fila() -> None:
    saldos = [
        _s("1A", "2026-07", "2026-07-10", "Ordinaria", "0.00", "500.00"),
        _s("1A", "2026-07", "2026-07-10", "Extraordinaria", "10.00"),
    ]
    _valida(_plantilla(saldos, []))


def test_total_unico_con_capital_cero_y_solo_interes() -> None:
    saldos = [_s("2A", None, None, None, "0.00", "300.00")]
    assert _donde(_errores(_plantilla(saldos, []))) == {("Saldos", 2, "Interés acumulado")}


def test_periodo_que_suma_cero_sin_interes_tampoco_se_acepta() -> None:
    """El 4c rechaza capital 0 por período (con o sin interés): se avisa acá, no al confirmar."""
    saldos = [_s("1A", "2026-07", "2026-07-10", "Ordinaria", "0.00")]
    assert _donde(_errores(_plantilla(saldos, []))) == {("Saldos", 2, "Importe")}


def test_unidad_que_mezcla_detalle_y_total() -> None:
    saldos = [*_saldos_base(), _s("1A", None, None, None, "1000.00")]
    assert _donde(_errores(_plantilla(saldos))) == {("Saldos", 9, "Período")}


def test_la_mezcla_se_marca_en_la_primera_fila_que_difiere_de_la_primera_de_la_unidad() -> None:
    saldos = [
        _s("1A", None, None, None, "1000.00"),  # fila 2: total
        _s("1A", "2026-09", "2026-09-10", "Ordinaria", "85000.00"),  # fila 3: detalle (difiere)
        _s("1A", None, None, None, "10.00"),  # fila 4: total otra vez, como la primera
    ]
    assert _donde(_errores(_plantilla(saldos, []))) == {("Saldos", 3, "Período")}


def test_un_error_de_importe_no_arrastra_errores_de_capital_cero() -> None:
    saldos = [_s("1A", "2026-07", "2026-07-10", "Ordinaria", "1.234", "500.00")]
    assert _donde(_errores(_plantilla(saldos, []))) == {("Saldos", 2, "Importe")}


def test_todos_los_errores_juntos_y_en_orden() -> None:
    saldos = _con(_saldos_base(), 2, Unidad="9Z")
    saldos = _con(saldos, 3, Concepto="Expensa")
    saldos = _con(saldos, 6, Importe="1.234")
    control = [*_control_base(), {"Unidad": "9Z", "Saldo según el administrador": "100.00"}]
    errores = _errores(_plantilla(saldos, control))
    assert [(e.hoja, e.fila, e.columna) for e in errores] == [
        ("Saldos", 2, "Unidad"),
        ("Saldos", 3, "Concepto"),
        ("Saldos", 6, "Importe"),
        ("Control", 7, "Unidad"),
    ]


def test_el_motivo_no_repite_el_valor_de_la_celda() -> None:
    saldos = _con(_saldos_base(), 2, Unidad="9Z-secreta")
    errores = _errores(_plantilla(saldos))
    assert "9Z-secreta" not in errores[0].motivo


# --- Control ----------------------------------------------------------------------------------


def test_control_con_unidad_inexistente_o_vacia() -> None:
    control = [
        *_control_base(),
        {"Unidad": "9Z", "Saldo según el administrador": "100.00"},
        {"Unidad": None, "Saldo según el administrador": "100.00"},
    ]
    assert _donde(_errores(_plantilla(None, control))) == {
        ("Control", 7, "Unidad"),
        ("Control", 8, "Unidad"),
    }


def test_control_con_unidad_repetida_nombra_la_otra_fila() -> None:
    control = [*_control_base(), {"Unidad": "1A", "Saldo según el administrador": "169000.00"}]
    errores = _errores(_plantilla(None, control))
    assert [(e.hoja, e.fila, e.columna) for e in errores] == [("Control", 7, "Unidad")]
    assert "repetida, ya está en la fila 2" in errores[0].motivo


def test_control_con_saldo_vacio_o_ambiguo() -> None:
    control = _control_base()
    control[0]["Saldo según el administrador"] = None
    control[1]["Saldo según el administrador"] = "1.234"
    assert _donde(_errores(_plantilla(None, control))) == {
        ("Control", 2, "Saldo según el administrador"),
        ("Control", 3, "Saldo según el administrador"),
    }


def test_control_acepta_coma_y_celda_numerica_y_negativos() -> None:
    control = [
        {"Unidad": "1A", "Saldo según el administrador": "85.000,00"},
        {"Unidad": "1B", "Saldo según el administrador": "-1,50"},
        {"Unidad": "2A", "Saldo según el administrador": "85000"},
    ]
    plantilla = _plantilla(
        None, control, numericas_control={4: frozenset({"Saldo según el administrador"})}
    )
    saldos = [c.saldo for c in _valida(plantilla).controles]
    assert saldos == [Dinero("85000.00"), Dinero("-1.50"), Dinero("85000.00")]


def test_una_unidad_con_saldo_y_sin_control_o_al_reves_es_valida() -> None:
    saldos = [*_saldos_base(), _s("5E", None, None, None, "1000.00")]
    control = [*_control_base(), {"Unidad": "3C", "Saldo según el administrador": "5000.00"}]
    borrador = _valida(_plantilla(saldos, control))
    assert {c.unidad for c in borrador.controles} >= {"3C"}


# --- Las hojas --------------------------------------------------------------------------------


def test_sin_saldos_ni_control_no_hay_borrador_ni_error() -> None:
    assert validar_saldos(
        PlantillaLeida(hojas={}), unidades=UNIDADES, fecha_de_migracion=MIGRACION
    ) == (None, ())


def test_las_hojas_de_la_plantilla_descargada_sin_filas_no_son_un_borrador() -> None:
    plantilla = _plantilla([], [])
    assert validar_saldos(plantilla, unidades=UNIDADES, fecha_de_migracion=MIGRACION) == (None, ())


def test_saldos_sin_la_hoja_control_es_error_de_archivo_que_la_nombra() -> None:
    errores = _errores(_plantilla(sin_control=True))
    assert [(e.hoja, e.fila) for e in errores] == [("Control", None)]
    assert "Control" in errores[0].motivo


def test_control_con_filas_y_sin_la_hoja_saldos_es_error_de_archivo() -> None:
    errores = _errores(_plantilla(sin_saldos=True))
    assert [(e.hoja, e.fila) for e in errores] == [("Saldos", None)]


@pytest.mark.parametrize("falta", SALDOS)
def test_encabezado_faltante_en_saldos(falta: str) -> None:
    encabezados = tuple(c for c in SALDOS if c != falta)
    errores = _errores(_plantilla(enc_saldos=encabezados))
    assert (("Saldos", None, falta)) in _donde(errores)
    assert falta in [e for e in errores if e.columna == falta][0].motivo


@pytest.mark.parametrize("falta", CONTROL)
def test_encabezado_faltante_en_control(falta: str) -> None:
    encabezados = tuple(c for c in CONTROL if c != falta)
    errores = _errores(_plantilla(enc_control=encabezados))
    assert (("Control", None, falta)) in _donde(errores)


def test_un_error_de_archivo_corta_antes_de_las_filas() -> None:
    saldos = _con(_saldos_base(), 2, Unidad="9Z")
    errores = _errores(_plantilla(saldos, enc_control=tuple(c for c in CONTROL if c != "Unidad")))
    assert all(e.fila is None for e in errores), "con un error de archivo no se leen filas"
