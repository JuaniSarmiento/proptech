"""4.2/4.3: esquema de config/parametros.yaml y leer_parametros (D6)."""

import copy
from typing import Any

import pytest
import yaml

BASE: dict[str, Any] = {
    "version": 1,
    "intereses": {
        "tasa_mensual": "3.00",
        "dias_de_gracia": 0,
        "forma_de_calculo": "proporcional_por_dia",
    },
    "fondo_de_reserva": {"porcentaje": "0.00"},
    "vencimiento": {
        "dia": 10,
        "modalidad": "unico",
        "rango_recargo": {"minimo": "0.01", "maximo": "20.00"},
    },
    "categorias_de_gasto": [
        {"clave": "encargado", "nombre": "Encargado y cargas sociales"},
        {"clave": "seguridad", "nombre": "Seguridad"},
    ],
    "grupos_de_reparto": [
        {
            "clave": "generales",
            "nombre": "Generales",
            "metodo": "coeficiente",
            "alcance": "todas_las_unidades",
        },
        {
            "clave": "ascensor",
            "nombre": "Ascensor",
            "metodo": "coeficiente",
            "alcance": "a_elegir",
        },
    ],
    "tipos_de_unidad": [
        {"clave": "departamento", "nombre": "Departamento"},
    ],
    "estados_de_unidad": {
        "habilitados": False,
        "estados": [
            {"clave": "habitado", "nombre": "Habitado", "factor": "100.00", "cargo_fijo": "0.00"},
            {
                "clave": "desocupado",
                "nombre": "Desocupado",
                "factor": "100.00",
                "cargo_fijo": "0.00",
            },
        ],
    },
}


def _dump(datos: dict[str, Any]) -> bytes:
    return yaml.safe_dump(datos, allow_unicode=True).encode()


def _valido() -> dict[str, Any]:
    return copy.deepcopy(BASE)


def test_referencia_valida_pasa() -> None:
    from proptech_core.compartido.parametros import Parametros

    Parametros(**_valido())


@pytest.mark.parametrize("tasa", ["-1.00", "10.01", "3.005"])
def test_tasa_fuera_de_rango_o_mal_formada_falla(tasa: str) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["intereses"]["tasa_mensual"] = tasa
    with pytest.raises(ValidationError):
        Parametros(**datos)


def test_fondo_de_reserva_negativo_tambien_nombra_el_rango_permitido() -> None:
    """`_validador_porcentaje` es compartido por `tasa_mensual` y por
    `fondo_de_reserva.porcentaje` (rompedor, cambio 1b vuelta 2): el mensaje
    de formato nombra el rango permitido para los dos, no sólo para la tasa."""
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["fondo_de_reserva"]["porcentaje"] = "-1.00"
    with pytest.raises(ValidationError) as exc_info:
        Parametros(**datos)
    mensaje = str(exc_info.value)
    assert "0" in mensaje and "100" in mensaje


@pytest.mark.parametrize("tasa", ["0.00", "10.00"])
def test_tasa_en_el_borde_pasa(tasa: str) -> None:
    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["intereses"]["tasa_mensual"] = tasa
    Parametros(**datos)


@pytest.mark.parametrize("dias", [32, -1, "diez", True])
def test_dias_de_gracia_invalidos_fallan(dias: object) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["intereses"]["dias_de_gracia"] = dias
    with pytest.raises(ValidationError):
        Parametros(**datos)


@pytest.mark.parametrize("dias", [0, 31])
def test_dias_de_gracia_en_el_borde_pasan(dias: int) -> None:
    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["intereses"]["dias_de_gracia"] = dias
    Parametros(**datos)


@pytest.mark.parametrize("campo,valor", [("tasa_mensual", 3.5), ("tasa_mensual", 3)])
def test_tasa_como_numero_yaml_falla_pidiendo_texto(campo: str, valor: object) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["intereses"][campo] = valor
    with pytest.raises(ValidationError):
        Parametros(**datos)


@pytest.mark.parametrize("valor", [3.5, 3])
def test_fondo_como_numero_yaml_falla_pidiendo_texto(valor: object) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["fondo_de_reserva"]["porcentaje"] = valor
    with pytest.raises(ValidationError):
        Parametros(**datos)


@pytest.mark.parametrize("campo", ["tasa_mensual", "fondo_de_reserva.porcentaje"])
def test_porcentaje_con_digitos_no_ascii_falla(campo: str) -> None:
    """Mismo problema que el rompedor encontró en `Dinero` (cambio 1b vuelta
    2): `_PATRON_PORCENTAJE` usaba `\\d` sin `re.ASCII`. Un texto compuesto
    por dígitos arábigo-índicos (equivalente a "3.00") no debe aceptarse ni
    para la tasa ni para el fondo de reserva, que comparten el validador."""
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    valor_no_ascii = "٣.٠٠"  # noqa: RUF001 - equivalente a "3.00"
    if campo == "tasa_mensual":
        datos["intereses"]["tasa_mensual"] = valor_no_ascii
    else:
        datos["fondo_de_reserva"]["porcentaje"] = valor_no_ascii
    with pytest.raises(ValidationError):
        Parametros(**datos)


def test_forma_de_calculo_desconocida_falla() -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["intereses"]["forma_de_calculo"] = "otra_cosa"
    with pytest.raises(ValidationError):
        Parametros(**datos)


def test_nombre_en_blanco_falla() -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["categorias_de_gasto"][0]["nombre"] = "   "
    with pytest.raises(ValidationError):
        Parametros(**datos)


def test_campo_desconocido_falla() -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["campo_que_no_existe"] = 1
    with pytest.raises(ValidationError):
        Parametros(**datos)


def test_campo_faltante_falla() -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    del datos["fondo_de_reserva"]
    with pytest.raises(ValidationError):
        Parametros(**datos)


def test_claves_de_categoria_repetidas_falla() -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["categorias_de_gasto"][1]["clave"] = datos["categorias_de_gasto"][0]["clave"]
    with pytest.raises(ValidationError):
        Parametros(**datos)


def test_estado_repetido_falla() -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["estados_de_unidad"]["estados"][1]["clave"] = datos["estados_de_unidad"]["estados"][0][
        "clave"
    ]
    with pytest.raises(ValidationError):
        Parametros(**datos)


def test_falta_generales_falla() -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["grupos_de_reparto"] = [datos["grupos_de_reparto"][1]]
    with pytest.raises(ValidationError):
        Parametros(**datos)


# --- 6.3: rangos de los estados de unidad (D6) ---


@pytest.mark.parametrize("factor", ["-0.01", "100.01"])
def test_estado_factor_fuera_de_rango_falla(factor: str) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["estados_de_unidad"]["estados"][0]["factor"] = factor
    with pytest.raises(ValidationError):
        Parametros(**datos)


@pytest.mark.parametrize("factor", ["0.00", "100.00"])
def test_estado_factor_en_el_borde_pasa(factor: str) -> None:
    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["estados_de_unidad"]["estados"][0]["factor"] = factor
    Parametros(**datos)


def test_estado_cargo_fijo_negativo_falla() -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["estados_de_unidad"]["estados"][0]["cargo_fijo"] = "-1.00"
    with pytest.raises(ValidationError):
        Parametros(**datos)


def test_estado_cargo_fijo_cero_pasa() -> None:
    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["estados_de_unidad"]["estados"][0]["cargo_fijo"] = "0.00"
    Parametros(**datos)


def test_lista_de_estados_vacia_falla() -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["estados_de_unidad"]["estados"] = []
    with pytest.raises(ValidationError):
        Parametros(**datos)


def test_fondo_de_reserva_en_el_borde_superior_pasa() -> None:
    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["fondo_de_reserva"]["porcentaje"] = "100.00"
    Parametros(**datos)


def test_generales_con_alcance_a_elegir_falla() -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["grupos_de_reparto"][0]["alcance"] = "a_elegir"
    with pytest.raises(ValidationError):
        Parametros(**datos)


# --- 4.3: leer_parametros junta TODOS los errores en un solo ParametrosInvalidos ---


def test_leer_parametros_junta_tres_problemas_a_la_vez(tmp_path: Any) -> None:
    from proptech_core.compartido.parametros import ParametrosInvalidos, leer_parametros

    datos = _valido()
    datos["intereses"]["tasa_mensual"] = "-1.00"
    datos["categorias_de_gasto"][0]["nombre"] = "   "
    datos["intereses"]["dias_de_gracia"] = 99
    ruta = tmp_path / "parametros.yaml"
    ruta.write_bytes(_dump(datos))

    with pytest.raises(ParametrosInvalidos) as exc_info:
        leer_parametros(str(ruta))

    mensaje = str(exc_info.value)
    assert "intereses.tasa_mensual" in mensaje
    assert "categorias_de_gasto[0].nombre" in mensaje
    assert "intereses.dias_de_gracia" in mensaje


def test_leer_parametros_archivo_inexistente() -> None:
    from proptech_core.compartido.parametros import ParametrosInvalidos, leer_parametros

    with pytest.raises(ParametrosInvalidos):
        leer_parametros("/no/existe/parametros.yaml")


# --- 6.4: MontoInvalido no filtra contenido del archivo (D5) ---


def test_leer_parametros_cargo_fijo_mal_escrito_no_filtra_el_valor(tmp_path: Any) -> None:
    from proptech_core.compartido.parametros import ParametrosInvalidos, leer_parametros

    datos = _valido()
    datos["estados_de_unidad"]["estados"][0]["cargo_fijo"] = "1,5"
    ruta = tmp_path / "parametros.yaml"
    ruta.write_bytes(_dump(datos))

    with pytest.raises(ParametrosInvalidos) as exc_info:
        leer_parametros(str(ruta))

    mensaje = str(exc_info.value)
    assert "1,5" not in mensaje
    assert "cargo_fijo" in mensaje


def test_leer_parametros_archivo_valido(tmp_path: Any) -> None:
    from proptech_core.compartido.parametros import Parametros, leer_parametros

    ruta = tmp_path / "parametros.yaml"
    ruta.write_bytes(_dump(_valido()))

    parametros = leer_parametros(str(ruta))
    assert isinstance(parametros, Parametros)
    assert parametros.intereses.dias_de_gracia == 0


# --- 2.3 (3a): deuda del 1b con dueño 3 (D13, nota N9 c de design.md) ---


def test_tipo_de_unidad_fuera_de_los_cuatro_de_d029_falla() -> None:
    """D-029 fija los cuatro tipos (departamento, cochera, baulera, local);
    hoy `tipos_de_unidad` acepta cualquier clave que matchee `_PATRON_CLAVE`."""
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["tipos_de_unidad"] = [{"clave": "quincho", "nombre": "Quincho"}]
    with pytest.raises(ValidationError):
        Parametros(**datos)


@pytest.mark.parametrize("clave", ["departamento", "cochera", "baulera", "local"])
def test_cada_tipo_de_unidad_de_d029_pasa(clave: str) -> None:
    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["tipos_de_unidad"] = [{"clave": clave, "nombre": clave.capitalize()}]
    Parametros(**datos)


# 3.6: vencimiento y rango del recargo, como texto y con límites cerrados.
def test_vencimiento_y_rango_validos() -> None:
    from decimal import Decimal

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["vencimiento"] = {
        "dia": 10,
        "modalidad": "unico",
        "rango_recargo": {"minimo": "0.01", "maximo": "20.00"},
    }
    vencimiento = Parametros(**datos).vencimiento
    assert vencimiento.dia == 10
    assert vencimiento.modalidad == "unico"
    assert vencimiento.rango_recargo.minimo == Decimal("0.01")
    assert vencimiento.rango_recargo.maximo == Decimal("20.00")


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("dia", 0),
        ("dia", 29),
        ("dia", "10"),
        ("dia", True),
        ("modalidad", "libre"),
        ("rango_recargo", {"minimo": "0.00", "maximo": "20.00"}),
        ("rango_recargo", {"minimo": "0.01", "maximo": "20.01"}),
        ("rango_recargo", {"minimo": "5.00", "maximo": "4.00"}),
        ("rango_recargo", {"minimo": 0.01, "maximo": "20.00"}),
    ],
)
def test_vencimiento_invalido_no_se_acepta(campo: str, valor: object) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["vencimiento"] = {
        "dia": 10,
        "modalidad": "unico",
        "rango_recargo": {"minimo": "0.01", "maximo": "20.00"},
        campo: valor,
    }
    with pytest.raises(ValidationError) as error:
        Parametros(**datos)
    assert any(e["loc"][:2] == ("vencimiento", campo) for e in error.value.errors())


@pytest.mark.parametrize(
    "cambios",
    [
        {"modalidad": "doble"},
        {
            "modalidad": "doble",
            "dia_segundo_vencimiento": 10,
            "recargo_segundo_vencimiento": "5.00",
        },
        {"recargo_segundo_vencimiento": "5.00"},
    ],
)
def test_defaults_de_vencimiento_incoherentes(cambios: dict[str, Any]) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["vencimiento"] = {
        "dia": 10,
        "modalidad": "unico",
        "rango_recargo": {"minimo": "0.01", "maximo": "20.00"},
        **cambios,
    }
    with pytest.raises(ValidationError) as error:
        Parametros(**datos)
    assert "vencimiento incoherente" in str(error.value)


def test_defaults_de_vencimiento_doble_completos() -> None:
    from proptech_core.compartido.parametros import Parametros

    datos = _valido()
    datos["vencimiento"] = {
        "dia": 10,
        "modalidad": "doble",
        "dia_segundo_vencimiento": 20,
        "recargo_segundo_vencimiento": "5.00",
        "rango_recargo": {"minimo": "0.01", "maximo": "20.00"},
    }
    assert Parametros(**datos).vencimiento.dia_segundo_vencimiento == 20
