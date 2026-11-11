"""Tarea 1.3 de `importacion-desde-excel`: la validación pura del padrón (design D2, D3, E1 a E5,
E7, E14). Sin Excel y sin base: se arma la `PlantillaLeida` a mano. Datos inventados."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import pytest

from proptech_core.compartido.pisos import vocabulario_de_pisos
from proptech_core.importacion.dominio.numeros import NumeroInvalido, leer_decimal
from proptech_core.importacion.dominio.padron import (
    ContextoDelEdificio,
    PadronInvalido,
    PadronValidado,
    validar_padron,
)
from proptech_core.importacion.dominio.plantilla import (
    ENCABEZADOS_POR_HOJA,
    ErrorDeImportacion,
    FilaLeida,
    HojaLeida,
    PlantillaLeida,
)

UNIDADES = ENCABEZADOS_POR_HOJA["Unidades"]
EDIFICIO = ContextoDelEdificio(
    vocabulario_de_pisos=vocabulario_de_pisos(pisos=3, subsuelos=1), tiene_unidades=False
)
CON_PADRON = ContextoDelEdificio(
    vocabulario_de_pisos=vocabulario_de_pisos(pisos=3, subsuelos=1), tiene_unidades=True
)
SIN_PISOS = ContextoDelEdificio(vocabulario_de_pisos=None, tiene_unidades=False)


def _valida(n: int) -> dict[str, str | None]:
    """La fila `n` (1 a 12) de un padrón válido: los coeficientes suman exactamente 1."""
    coeficiente = "0.083337" if n == 12 else "0.083333"
    return {
        "Unidad": f"U{n}",
        "Tipo": "departamento",
        "Piso": ("PB", "SS1", "1", "2", "3")[n % 5],
        "Coeficiente": coeficiente,
        "Superficie m2": "45.50",
        "Propietario": f"Persona Ficticia {n}",
        "Email": f"propietario{n}@ficticio.test",
    }


def _filas(**cambios: Mapping[int, Any]) -> list[dict[str, str | None]]:
    """Las 12 filas válidas; `cambios` es `{"Columna": {fila_del_excel: valor}}`, filas 2 a 13."""
    filas = [_valida(n) for n in range(1, 13)]
    for columna, por_fila in cambios.items():
        for n, valor in por_fila.items():
            filas[n - 2][columna.replace("_", " ")] = valor
    return filas


def _plantilla(
    filas: list[dict[str, str | None]],
    *,
    encabezados: tuple[str, ...] = UNIDADES,
    numericas: Mapping[int, frozenset[str]] | None = None,
    sin_cache: Mapping[int, frozenset[str]] | None = None,
    hoja: bool = True,
) -> PlantillaLeida:
    if not hoja:
        return PlantillaLeida(hojas={})
    leidas = tuple(
        FilaLeida(
            numero=i + 2,
            valores={c: v for c, v in fila.items() if c in encabezados},
            formulas_sin_cache=(sin_cache or {}).get(i + 2, frozenset()),
            numericas=(numericas or {}).get(i + 2, frozenset()),
        )
        for i, fila in enumerate(filas)
    )
    return PlantillaLeida(hojas={"Unidades": HojaLeida("Unidades", encabezados, leidas)})


def _rechazo(
    plantilla: PlantillaLeida, contexto: ContextoDelEdificio = EDIFICIO
) -> list[ErrorDeImportacion]:
    with pytest.raises(PadronInvalido) as error:
        validar_padron(plantilla, contexto)
    return list(error.value.errores)


def _donde(errores: list[ErrorDeImportacion]) -> list[tuple[str | None, int | None, str | None]]:
    return [(e.hoja, e.fila, e.columna) for e in errores]


def _aceptado(
    plantilla: PlantillaLeida, contexto: ContextoDelEdificio = EDIFICIO
) -> PadronValidado:
    padron = validar_padron(plantilla, contexto)
    hoja = plantilla.hojas.get("Unidades")
    esperadas = 0 if contexto.tiene_unidades or hoja is None else len(hoja.filas)
    assert len(padron.unidades) == esperadas, "el padrón válido no devolvió todas sus unidades"
    return padron


# --- Un padrón válido -------------------------------------------------------------------------


def test_un_padron_valido_devuelve_sus_unidades_ya_tipadas() -> None:
    padron = _aceptado(_plantilla(_filas()))
    assert padron.advertencias == ()
    assert [u.identificador for u in padron.unidades] == [f"U{n}" for n in range(1, 13)]
    primera, *_, ultima = padron.unidades
    assert (primera.fila, primera.tipo, primera.piso) == (2, "departamento", "1")
    assert primera.coeficiente.decimal == Decimal("0.083333")
    assert primera.superficie_m2.decimal == Decimal("45.50")
    assert (primera.propietario, primera.email) == (
        "Persona Ficticia 1",
        "propietario1@ficticio.test",
    )
    assert ultima.coeficiente.decimal == Decimal("0.083337")
    assert ultima.fila == 13


def test_los_pisos_del_vocabulario_se_aceptan_exactos() -> None:
    pisos = {2: "SS1", 3: "PB", 4: "1", 5: "2", 6: "3"}
    padron = _aceptado(_plantilla(_filas(Piso=pisos)))
    assert [u.piso for u in padron.unidades[:5]] == ["SS1", "PB", "1", "2", "3"]


# --- Todo o nada, con todos los errores juntos ------------------------------------------------


def test_un_solo_error_nombra_hoja_fila_columna_y_motivo() -> None:
    """Escenario: Un solo error no carga nada"""
    [error] = _rechazo(_plantilla(_filas(Piso={9: "Entrepiso"})))
    assert (error.hoja, error.fila, error.columna) == ("Unidades", 9, "Piso")
    assert error.motivo


def test_varios_errores_juntos_en_el_orden_del_archivo() -> None:
    """Escenario: Varios errores juntos"""
    errores = _rechazo(_plantilla(_filas(Tipo={3: None}, Superficie_m2={7: "0"})))
    assert _donde(errores) == [("Unidades", 3, "Tipo"), ("Unidades", 7, "Superficie m2")]


def test_varias_columnas_de_una_misma_fila_dan_un_error_cada_una() -> None:
    errores = _rechazo(_plantilla(_filas(Tipo={4: "Depto"}, Piso={4: "9"}, Email={4: "mal"})))
    assert _donde(errores) == [
        ("Unidades", 4, "Tipo"),
        ("Unidades", 4, "Piso"),
        ("Unidades", 4, "Email"),
    ]


def test_los_errores_de_cada_fila_no_se_pisan_entre_si() -> None:
    errores = _rechazo(_plantilla(_filas(Piso={2: "9", 13: "9"}, Tipo={7: "x"})))
    assert _donde(errores) == [
        ("Unidades", 2, "Piso"),
        ("Unidades", 7, "Tipo"),
        ("Unidades", 13, "Piso"),
    ]


# --- Unidad -----------------------------------------------------------------------------------


def test_unidad_repetida_nombra_la_otra_fila() -> None:
    """Escenario: Unidad repetida"""
    errores = _rechazo(_plantilla(_filas(Unidad={12: "U3"})))
    assert _donde(errores) == [("Unidades", 12, "Unidad")]
    assert "fila 4" in errores[0].motivo


def test_una_unidad_repetida_se_detecta_aun_con_espacios_en_el_borde() -> None:
    """El alta manual recorta el identificador (R3A-6): `" U3 "` es la unidad `U3`."""
    errores = _rechazo(_plantilla(_filas(Unidad={12: " U3 "})))
    assert _donde(errores) == [("Unidades", 12, "Unidad")]


def test_el_identificador_se_recorta_como_en_el_alta_manual() -> None:
    padron = _aceptado(_plantilla(_filas(Unidad={2: "  U1  "})))
    assert padron.unidades[0].identificador == "U1"


@pytest.mark.parametrize(
    "valor",
    [None, "", "   ", "X" * 41, "1\tC", "1\x00C"],
    ids=["none", "vacia", "blancos", "41", "tab", "nul"],
)
def test_unidad_invalida(valor: str | None) -> None:
    errores = _rechazo(_plantilla(_filas(Unidad={4: valor})))
    assert _donde(errores) == [("Unidades", 4, "Unidad")]
    assert valor is None or valor not in errores[0].motivo or not valor.strip()


def test_una_unidad_de_40_caracteres_se_acepta() -> None:
    padron = _aceptado(_plantilla(_filas(Unidad={4: "X" * 40})))
    assert padron.unidades[2].identificador == "X" * 40


# --- Tipo y piso ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tipo", [None, "Departamento", "Depto", "DEPARTAMENTO", " cochera", "garage"]
)
def test_tipo_exacto_en_minuscula(tipo: str | None) -> None:
    assert _donde(_rechazo(_plantilla(_filas(Tipo={6: tipo})))) == [("Unidades", 6, "Tipo")]


@pytest.mark.parametrize("tipo", ["departamento", "cochera", "baulera", "local"])
def test_los_cuatro_tipos_se_aceptan(tipo: str) -> None:
    assert _aceptado(_plantilla(_filas(Tipo={6: tipo}))).unidades[4].tipo == tipo


@pytest.mark.parametrize(
    "piso",
    [None, "", "4", "SS2", "1°", "Entrepiso", "planta alta", " PB", "PB ", "pb", "01", "1\n"],
)
def test_piso_fuera_del_vocabulario_o_con_espacios_no_se_recorta(piso: str | None) -> None:
    """Escenario: Piso fuera del vocabulario / Celda vacía obligatoria"""
    assert _donde(_rechazo(_plantilla(_filas(Piso={6: piso})))) == [("Unidades", 6, "Piso")]


def test_edificio_sin_pisos_configurados_se_rechaza_nombrando_piso() -> None:
    """Escenario: Edificio sin pisos configurados"""
    [error] = _rechazo(_plantilla(_filas()), SIN_PISOS)
    assert (error.hoja, error.fila, error.columna) == ("Unidades", None, "Piso")
    assert "piso" in error.motivo.lower()


def test_sin_pisos_configurados_los_demas_errores_se_informan_igual() -> None:
    errores = _rechazo(_plantilla(_filas(Tipo={4: None})), SIN_PISOS)
    assert _donde(errores) == [("Unidades", None, "Piso"), ("Unidades", 4, "Tipo")]


def test_sin_pisos_configurados_el_piso_vacio_sigue_siendo_error_de_fila() -> None:
    errores = _rechazo(_plantilla(_filas(Piso={4: None})), SIN_PISOS)
    assert ("Unidades", 4, "Piso") in _donde(errores)


# --- Números (E14) ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "decimales", "esperado"),
    [
        ("0,083333", 6, "0.083333"),
        ("0.083333", 6, "0.083333"),
        ("1.234,56", 2, "1234.56"),
        ("1234,56", 2, "1234.56"),
        ("1234.56", 2, "1234.56"),
        ("45.50", 2, "45.50"),
        ("45", 2, "45"),
        ("1,234", 6, "1.234"),
        ("-45,5", 2, "-45.5"),
        (" 45,5 ", 2, "45.5"),
        ("1.234.567,5", 2, "1234567.5"),
    ],
)
def test_numero_valido_desde_texto(texto: str, decimales: int, esperado: str) -> None:
    resultado = leer_decimal(texto, decimales=decimales)
    assert resultado == Decimal(esperado)
    assert str(resultado) == esperado


@pytest.mark.parametrize(
    ("texto", "decimales"),
    [
        ("1.234", 6),
        ("45.555", 2),
        ("0.0833333", 6),
        ("45,555", 2),
        ("1.234.567", 2),
        ("1.23,4.5", 2),
        ("1,2,3", 2),
        ("abc", 2),
        ("", 2),
        ("   ", 2),
        ("1e-5", 6),
        ("1_000", 2),
        ("4 5", 2),
        ("٤٥", 2),
        ("1,", 2),
        (",5", 2),
        ("NaN", 2),
        ("Infinity", 2),
    ],
)
def test_numero_invalido_desde_texto_nunca_se_redondea(texto: str, decimales: int) -> None:
    with pytest.raises(NumeroInvalido) as error:
        leer_decimal(texto, decimales=decimales)
    assert str(error.value)


@pytest.mark.parametrize(("texto", "esperado"), [("0.125", "0.125"), ("1.234", "1.234")])
def test_una_celda_numerica_no_es_ambigua(texto: str, esperado: str) -> None:
    assert leer_decimal(texto, decimales=6, numerico=True) == Decimal(esperado)


def test_una_celda_numerica_con_mas_decimales_tambien_se_rechaza() -> None:
    with pytest.raises(NumeroInvalido):
        leer_decimal("0.0833333", decimales=6, numerico=True)


@pytest.mark.parametrize("coma", [True, False], ids=["coma", "punto"])
def test_coeficientes_desde_texto_con_coma_o_con_punto(coma: bool) -> None:
    """Escenario: Coma decimal"""
    filas = _filas()
    for fila in filas:
        coeficiente = fila["Coeficiente"]
        assert coeficiente is not None
        fila["Coeficiente"] = coeficiente.replace(".", ",") if coma else coeficiente
    padron = _aceptado(_plantilla(filas))
    assert [u.coeficiente.decimal for u in padron.unidades] == [
        *[Decimal("0.083333")] * 11,
        Decimal("0.083337"),
    ]


def test_un_solo_coeficiente_de_uno_es_valido() -> None:
    padron = _aceptado(_plantilla([{**_valida(1), "Coeficiente": "1"}]))
    assert padron.unidades[0].coeficiente.decimal == Decimal("1")


@pytest.mark.parametrize(
    "valor",
    [None, "", "0", "0,000000", "-0.083333", "1.5", "2", "1.234", "0.0833333", "abc", "1e-5"],
)
def test_coeficiente_invalido(valor: str | None) -> None:
    """Escenario: Siete decimales (y el resto de los coeficientes mal escritos)"""
    errores = _rechazo(_plantilla(_filas(Coeficiente={6: valor})))
    assert _donde(errores) == [("Unidades", 6, "Coeficiente")]


def test_siete_decimales_no_se_redondean_a_seis() -> None:
    """Mutante: redondear `0.0833333` a `0.083333` y aceptarlo."""
    errores = _rechazo(_plantilla(_filas(Coeficiente={6: "0.0833333"})))
    assert _donde(errores) == [("Unidades", 6, "Coeficiente")]
    assert "6" in errores[0].motivo


def test_una_celda_numerica_de_tres_decimales_se_acepta_pero_el_texto_igual_es_ambiguo() -> None:
    suma_ok = {n: "0.000001" for n in range(3, 14)}
    numerica = _plantilla(
        _filas(Coeficiente={2: "0.125", **suma_ok}), numericas={2: frozenset({"Coeficiente"})}
    )
    with pytest.raises(PadronInvalido) as suma:
        validar_padron(numerica, EDIFICIO)
    assert _donde(list(suma.value.errores)) == [("Unidades", None, "Coeficiente")]
    en_texto = _rechazo(_plantilla(_filas(Coeficiente={2: "0.125", **suma_ok})))
    assert ("Unidades", 2, "Coeficiente") in _donde(en_texto)


@pytest.mark.parametrize("valor", ["45.50", "45,5", "1.234,56", "45", "0,01", "99999999,99"])
def test_superficie_valida(valor: str) -> None:
    padron = _aceptado(_plantilla(_filas(Superficie_m2={2: valor})))
    esperado = Decimal(valor.replace(".", "").replace(",", ".") if "," in valor else valor)
    assert padron.unidades[0].superficie_m2.decimal == esperado


@pytest.mark.parametrize(
    "valor", [None, "", "0", "0,00", "-45.50", "45.555", "45,555", "abc", "100000000", "1.234"]
)
def test_superficie_invalida(valor: str | None) -> None:
    errores = _rechazo(_plantilla(_filas(Superficie_m2={6: valor})))
    assert _donde(errores) == [("Unidades", 6, "Superficie m2")]


def test_una_formula_sin_valor_en_cache_es_error_de_esa_celda() -> None:
    """Escenario: Fórmula sin valor en caché"""
    filas = _filas(Superficie_m2={6: None})
    errores = _rechazo(_plantilla(filas, sin_cache={6: frozenset({"Superficie m2"})}))
    assert _donde(errores) == [("Unidades", 6, "Superficie m2")]
    assert "fórmula" in errores[0].motivo.lower()


def test_una_formula_sin_cache_en_otra_columna_obligatoria() -> None:
    filas = _filas(Coeficiente={6: None})
    errores = _rechazo(_plantilla(filas, sin_cache={6: frozenset({"Coeficiente"})}))
    assert _donde(errores) == [("Unidades", 6, "Coeficiente")]
    assert "fórmula" in errores[0].motivo.lower()


# --- Suma de coeficientes (E4, R01) -----------------------------------------------------------


def _con_ultimo(coeficiente: str) -> list[dict[str, str | None]]:
    return _filas(Coeficiente={13: coeficiente})


def test_suma_exacta_no_advierte() -> None:
    assert _aceptado(_plantilla(_filas())).advertencias == ()


@pytest.mark.parametrize(("ultimo", "suma"), [("0.083237", "0,9999"), ("0.083437", "1,0001")])
def test_suma_dentro_de_la_tolerancia_distinta_de_uno_advierte(ultimo: str, suma: str) -> None:
    """Escenario: Suma 0,9999 (el borde de la tolerancia entra)"""
    padron = _aceptado(_plantilla(_con_ultimo(ultimo)))
    assert len(padron.unidades) == 12
    [aviso] = padron.advertencias
    assert (aviso.hoja, aviso.fila, aviso.columna) == ("Unidades", None, "Coeficiente")
    assert f"suman {suma}" in aviso.motivo


@pytest.mark.parametrize(
    ("ultimo", "suma"), [("0.083137", "0,9998"), ("0.083537", "1,0002"), ("0.000001", "0,9166")]
)
def test_suma_fuera_de_la_tolerancia_rechaza_con_un_error_de_la_hoja(
    ultimo: str, suma: str
) -> None:
    """Escenario: Suma 0,9998"""
    [error] = _rechazo(_plantilla(_con_ultimo(ultimo)))
    assert (error.hoja, error.fila, error.columna) == ("Unidades", None, "Coeficiente")
    assert f"suman {suma}" in error.motivo
    assert "0,0001" in error.motivo


def test_con_errores_de_fila_no_se_informa_la_suma() -> None:
    """Con una fila mal la suma no es confiable: sólo el error de la fila."""
    errores = _rechazo(_plantilla(_filas(Coeficiente={6: "0.0833333"})))
    assert _donde(errores) == [("Unidades", 6, "Coeficiente")]


def test_la_suma_cuenta_el_coeficiente_de_una_celda_numerica_exacto() -> None:
    filas = _filas(Coeficiente={13: "0.083337"})
    numericas = {n: frozenset({"Coeficiente"}) for n in range(2, 14)}
    assert _aceptado(_plantilla(filas, numericas=numericas)).advertencias == ()


# --- Propietario y email ----------------------------------------------------------------------


def test_propietario_y_email_son_opcionales() -> None:
    filas = _filas(Propietario={2: None, 3: None}, Email={2: None, 3: None})
    padron = _aceptado(_plantilla(filas))
    assert [(u.propietario, u.email) for u in padron.unidades[:2]] == [(None, None), (None, None)]


def test_propietario_sin_email() -> None:
    """Escenario: Propietario sin email"""
    padron = _aceptado(_plantilla(_filas(Email={2: None})))
    assert (padron.unidades[0].propietario, padron.unidades[0].email) == (
        "Persona Ficticia 1",
        None,
    )


@pytest.mark.parametrize(
    "email", ["no-es-un-email", "sin-arroba.test", "a@b", "a b@c.test", "@c.test"]
)
def test_email_invalido(email: str) -> None:
    """Escenario: Email inválido"""
    assert _donde(_rechazo(_plantilla(_filas(Email={6: email})))) == [("Unidades", 6, "Email")]


def test_el_email_se_normaliza_como_en_el_alta_de_personas() -> None:
    padron = _aceptado(_plantilla(_filas(Email={2: " Uno@Ficticio.Test "})))
    assert padron.unidades[0].email == "uno@ficticio.test"


def test_el_nombre_del_propietario_se_recorta() -> None:
    padron = _aceptado(_plantilla(_filas(Propietario={2: "  Persona Ficticia Uno  "})))
    assert padron.unidades[0].propietario == "Persona Ficticia Uno"


def test_un_email_sin_propietario_es_error_de_la_columna_propietario() -> None:
    errores = _rechazo(_plantilla(_filas(Propietario={6: None})))
    assert _donde(errores) == [("Unidades", 6, "Propietario")]
    assert "email" in errores[0].motivo.lower()


def test_un_propietario_con_caracteres_de_control_es_error() -> None:
    errores = _rechazo(_plantilla(_filas(Propietario={6: "Persona\x00Ficticia"})))
    assert _donde(errores) == [("Unidades", 6, "Propietario")]


def test_el_mismo_email_en_dos_filas_no_es_un_error() -> None:
    filas = _filas(Email={3: "propietario1@ficticio.test"}, Propietario={3: "Persona Ficticia 1"})
    padron = _aceptado(_plantilla(filas))
    assert padron.unidades[0].email == padron.unidades[1].email


# --- La hoja y los encabezados (E7) -----------------------------------------------------------


def test_edificio_sin_unidades_sin_hoja_unidades_se_rechaza_nombrandola() -> None:
    [error] = _rechazo(_plantilla([], hoja=False))
    assert (error.hoja, error.fila, error.columna) == ("Unidades", None, None)
    assert "Unidades" in error.motivo


def test_edificio_sin_unidades_con_la_hoja_vacia_se_rechaza() -> None:
    [error] = _rechazo(_plantilla([]))
    assert (error.hoja, error.fila) == ("Unidades", None)
    assert "filas" in error.motivo


def test_falta_un_encabezado() -> None:
    """Escenario: Falta un encabezado: sólo el error de archivo, sin leer filas."""
    sin_coeficiente = tuple(c for c in UNIDADES if c != "Coeficiente")
    errores = _rechazo(_plantilla(_filas(Piso={4: "9"}), encabezados=sin_coeficiente))
    assert _donde(errores) == [("Unidades", None, "Coeficiente")]
    assert "Coeficiente" in errores[0].motivo


def test_faltan_dos_encabezados_y_se_informan_los_dos() -> None:
    sin_dos = tuple(c for c in UNIDADES if c not in ("Coeficiente", "Email"))
    errores = _rechazo(_plantilla(_filas(), encabezados=sin_dos))
    assert _donde(errores) == [("Unidades", None, "Coeficiente"), ("Unidades", None, "Email")]


def test_el_orden_de_los_encabezados_no_importa() -> None:
    padron = _aceptado(_plantilla(_filas(), encabezados=tuple(reversed(UNIDADES))))
    assert len(padron.unidades) == 12


@pytest.mark.parametrize("forma", ["sin_hoja", "hoja_vacia", "hoja_sin_encabezados"])
def test_edificio_con_unidades_acepta_un_archivo_sin_padron(forma: str) -> None:
    """Escenario: Padrón sobre unidades existentes (el caso permitido)"""
    plantilla = {
        "sin_hoja": _plantilla([], hoja=False),
        "hoja_vacia": _plantilla([]),
        "hoja_sin_encabezados": _plantilla([], encabezados=()),
    }[forma]
    padron = _aceptado(plantilla, CON_PADRON)
    assert padron.unidades == ()
    assert padron.advertencias == ()


def test_edificio_con_unidades_rechaza_cada_fila_de_la_hoja_unidades() -> None:
    """Escenario: Padrón sobre unidades existentes"""
    errores = _rechazo(_plantilla(_filas()[:3]), CON_PADRON)
    assert _donde(errores) == [("Unidades", 2, None), ("Unidades", 3, None), ("Unidades", 4, None)]
    assert "ya tiene unidades" in errores[0].motivo


def test_edificio_con_unidades_no_valida_nada_mas_de_la_hoja() -> None:
    """Sólo importa que hay filas: no se suma el ruido de piso, tipo o coeficiente."""
    errores = _rechazo(_plantilla(_filas(Piso={2: "9"})[:1]), CON_PADRON)
    assert _donde(errores) == [("Unidades", 2, None)]
