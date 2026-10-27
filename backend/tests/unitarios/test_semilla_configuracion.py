"""R01 compartida, estado de migración y modos de grupo de la semilla (7.1)."""

from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from proptech_core.compartido import coeficientes
from proptech_core.compartido.parametros import Parametros, leer_parametros
from proptech_core.compartido.semilla import Semilla, SemillaInvalida, leer_semilla

from .test_semilla import PARAMETROS_PATH, RAIZ, _dump, _valido


@pytest.fixture
def parametros() -> Parametros:
    return leer_parametros(str(PARAMETROS_PATH))


@pytest.fixture
def georef() -> Any:
    from proptech_core.compartido.georef import leer_georef

    return leer_georef(str(RAIZ / "config" / "georef"))


def leer(datos: dict[str, Any], parametros: Parametros, georef: Any, tmp_path: Path) -> Semilla:
    ruta = tmp_path / "semilla.yaml"
    ruta.write_bytes(_dump(datos))
    return leer_semilla(str(ruta), parametros, georef)


def propios(coeficiente: str = "1.000000") -> dict[str, Any]:
    return {"modo": "propios", "unidades": [{"identificador": "C1", "coeficiente": coeficiente}]}


def test_ejemplo_declara_estado_y_grupos_parciales_renormalizados(
    parametros: Parametros, georef: Any
) -> None:
    semilla = leer_semilla(str(RAIZ / "config/semilla/edificio-ejemplo.yaml"), parametros, georef)
    assert semilla.edificio.estado_migracion == "sin_saldos_previos"
    assert len(semilla.unidades) == 13
    assert semilla.grupos["generales"] == "todas"
    ascensor, cocheras = semilla.grupos["ascensor"], semilla.grupos["cocheras"]
    assert not isinstance(ascensor, str)
    assert not isinstance(cocheras, str)
    assert ascensor.modo == cocheras.modo == "renormalizado"
    assert len(ascensor.unidades) == 8


@pytest.mark.parametrize(
    "coeficiente,diferencia", [("0.399900", "-0.000100"), ("0.400100", "0.000100")]
)
def test_r01_acepta_ambos_bordes_con_advertencia_y_sin_redondear(
    parametros: Parametros, georef: Any, tmp_path: Path, coeficiente: str, diferencia: str
) -> None:
    datos = _valido()
    datos["unidades"][0]["coeficiente"] = coeficiente
    with pytest.warns(UserWarning, match=diferencia):
        semilla = leer(datos, parametros, georef, tmp_path)
    assert semilla.unidades[0].coeficiente == Decimal(coeficiente)


@pytest.mark.parametrize(
    "coeficiente,diferencia", [("0.399800", "-0.000200"), ("0.400200", "0.000200")]
)
def test_r01_rechaza_afuera_de_tolerancia_nombrando_diferencia(
    parametros: Parametros, georef: Any, tmp_path: Path, coeficiente: str, diferencia: str
) -> None:
    datos = _valido()
    datos["unidades"][0]["coeficiente"] = coeficiente
    with pytest.raises(SemillaInvalida) as error:
        leer(datos, parametros, georef, tmp_path)
    assert "unidades" in str(error.value)
    assert diferencia in str(error.value)


def test_propios_usa_su_suma_y_acepta_tolerancia(
    parametros: Parametros, georef: Any, tmp_path: Path
) -> None:
    datos = _valido()
    datos["grupos"]["cocheras"] = propios("0.999800")
    with pytest.raises(SemillaInvalida) as error:
        leer(datos, parametros, georef, tmp_path)
    assert "grupos.cocheras" in str(error.value)
    assert "-0.000200" in str(error.value)
    datos["grupos"]["cocheras"] = propios()
    semilla = leer(datos, parametros, georef, tmp_path)
    cocheras = semilla.grupos["cocheras"]
    assert not isinstance(cocheras, str)
    assert cocheras.unidades[0].coeficiente == Decimal("1")
    datos["grupos"]["cocheras"] = propios("0.999900")
    with pytest.warns(UserWarning, match=r"grupos.cocheras.*-0.000100"):
        leer(datos, parametros, georef, tmp_path)


def test_semilla_llama_la_funcion_compartida_para_generales_y_propios(
    parametros: Parametros, georef: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = coeficientes.informar_coeficientes
    llamadas: list[list[coeficientes.Coeficiente]] = []

    def observar(valores: Iterable[coeficientes.Coeficiente]) -> coeficientes.InformeCoeficientes:
        valores = list(valores)
        llamadas.append(valores)
        return original(valores)

    monkeypatch.setattr(coeficientes, "informar_coeficientes", observar)
    semilla = leer(_valido(), parametros, georef, tmp_path)
    cocheras = semilla.grupos["cocheras"]
    assert not isinstance(cocheras, str)
    assert cocheras.modo == "renormalizado"
    assert len(llamadas) == 1
    assert [c.a_texto() for c in llamadas[0]] == ["0.400000", "0.300000", "0.300000"]
    llamadas.clear()
    datos = _valido()
    datos["grupos"]["cocheras"] = propios()
    leer(datos, parametros, georef, tmp_path)
    assert len(llamadas) == 2
    assert [c.a_texto() for c in llamadas[1]] == ["1.000000"]


@pytest.mark.parametrize("estado", ["pendiente", "confirmada", "sin_saldos_previos"])
def test_estado_de_migracion_valido(
    parametros: Parametros, georef: Any, tmp_path: Path, estado: str
) -> None:
    datos = _valido()
    datos["edificio"]["estado_migracion"] = estado
    assert leer(datos, parametros, georef, tmp_path).edificio.estado_migracion == estado


def test_estado_desconocido_nombra_el_campo_y_estados_permitidos(
    parametros: Parametros, georef: Any, tmp_path: Path
) -> None:
    datos = _valido()
    datos["edificio"]["estado_migracion"] = "MARCADOR_ESTADO"
    with pytest.raises(SemillaInvalida) as error:
        leer(datos, parametros, georef, tmp_path)
    assert "edificio.estado_migracion" in str(error.value)
    assert "pendiente" in str(error.value)
    assert "confirmada" in str(error.value)
    assert "MARCADOR_ESTADO" not in str(error.value)


@pytest.mark.parametrize(
    "grupo,campo",
    [
        ({"modo": "inexistente", "unidades": ["C1"]}, "modo"),
        ({"modo": "propios", "unidades": ["C1"]}, "coeficiente"),
        ({"unidades": [{"identificador": "C1", "coeficiente": "1.000000"}]}, "coeficiente"),
        (
            {"modo": "propios", "unidades": [{"identificador": "C1", "coeficiente": 1}]},
            "coeficiente",
        ),
        (
            {"modo": "propios", "unidades": [{"identificador": "C1", "coeficiente": "1.000001"}]},
            "coeficiente",
        ),
        (
            {"modo": "propios", "unidades": [{"identificador": "C1", "coeficiente": "1.0\n"}]},
            "coeficiente",
        ),
        (
            {"modo": "propios", "unidades": [{"identificador": "C1", "coeficiente": "\u0661.0"}]},
            "coeficiente",
        ),
        (
            {
                "modo": "propios",
                "unidades": [{"identificador": "C1", "coeficiente": "1.0", "extra": "MARCADOR"}],
            },
            "extra",
        ),
    ],
)
def test_modo_coherencia_y_formato_del_miembro_se_validan(
    parametros: Parametros, georef: Any, tmp_path: Path, grupo: Any, campo: str
) -> None:
    datos = _valido()
    datos["grupos"]["cocheras"] = grupo
    with pytest.raises(SemillaInvalida) as error:
        leer(datos, parametros, georef, tmp_path)
    assert "grupos.cocheras" in str(error.value)
    assert campo in str(error.value)
    assert "MARCADOR" not in str(error.value)


def test_propios_no_se_admite_en_un_grupo_por_superficie(
    parametros: Parametros, georef: Any, tmp_path: Path
) -> None:
    parametros = parametros.model_copy(
        update={
            "grupos_de_reparto": [
                g.model_copy(update={"metodo": "superficie"}) if g.clave == "cocheras" else g
                for g in parametros.grupos_de_reparto
            ]
        }
    )
    datos = _valido()
    datos["grupos"]["cocheras"] = propios()
    with pytest.raises(SemillaInvalida) as error:
        leer(datos, parametros, georef, tmp_path)
    assert "grupos.cocheras.modo" in str(error.value)


def test_generales_es_obligatorio_y_no_tiene_modo_propios(
    parametros: Parametros, georef: Any, tmp_path: Path
) -> None:
    datos = _valido()
    datos["grupos"].pop("generales")
    with pytest.raises(SemillaInvalida, match=r"grupos.generales"):
        leer(datos, parametros, georef, tmp_path)
    datos["grupos"]["generales"] = propios()
    with pytest.raises(SemillaInvalida, match=r"grupos.generales"):
        leer(datos, parametros, georef, tmp_path)
