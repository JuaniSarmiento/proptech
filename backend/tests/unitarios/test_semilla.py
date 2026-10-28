"""5.1: leer_semilla (D10) — la semilla del edificio de ejemplo."""

import copy
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[3]
PARAMETROS_PATH = RAIZ / "config" / "parametros.yaml"


@pytest.fixture
def parametros() -> Any:
    from proptech_core.compartido.parametros import leer_parametros

    return leer_parametros(str(PARAMETROS_PATH))


@pytest.fixture
def georef() -> Any:
    from proptech_core.compartido.georef import leer_georef

    return leer_georef(str(RAIZ / "config" / "georef"))


#: 6.5: ids reales de Georef (Mendoza/Capital/"Mendoza", mismos que
#: `tests/integracion/_georef_real.py`), 4 pisos y 1 subsuelo.
BASE: dict[str, Any] = {
    "version": 1,
    "edificio": {
        "nombre": "Edificio Ejemplo",
        "provincia_id": "50",
        "departamento_id": "50007",
        "localidad_id": "50007010",
        "pisos": 4,
        "subsuelos": 1,
        "estado_migracion": "sin_saldos_previos",
    },
    "unidades": [
        {
            "identificador": "L-PB",
            "tipo": "local",
            "piso": "PB",
            "coeficiente": "0.400000",
            "superficie_m2": "45.00",
        },
        {
            "identificador": "1A",
            "tipo": "departamento",
            "piso": "1",
            "coeficiente": "0.300000",
            "superficie_m2": "60.00",
        },
        {
            "identificador": "C1",
            "tipo": "cochera",
            "piso": "SS1",
            "coeficiente": "0.300000",
            "superficie_m2": "12.50",
        },
    ],
    "grupos": {
        "generales": "todas",
        "cocheras": ["C1"],
    },
}


def _dump(datos: dict[str, Any]) -> bytes:
    return yaml.safe_dump(datos, allow_unicode=True).encode()


def _valido() -> dict[str, Any]:
    return copy.deepcopy(BASE)


def test_semilla_del_repo_es_valida_y_suma_exactamente_uno(parametros: Any, georef: Any) -> None:
    from proptech_core.compartido.semilla import leer_semilla

    ruta = RAIZ / "config" / "semilla" / "edificio-ejemplo.yaml"
    semilla = leer_semilla(str(ruta), parametros, georef)

    total = sum((u.coeficiente for u in semilla.unidades), start=Decimal(0))
    assert total == Decimal("1")


def test_base_de_test_es_valida(parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import leer_semilla

    ruta = tmp_path / "semilla.yaml"
    ruta.write_bytes(_dump(_valido()))
    semilla = leer_semilla(str(ruta), parametros, georef)
    assert len(semilla.unidades) == 3


def _escribir_y_leer(datos: dict[str, Any], parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import leer_semilla

    ruta = tmp_path / "semilla.yaml"
    ruta.write_bytes(_dump(datos))
    leer_semilla(str(ruta), parametros, georef)


def test_tipo_desconocido_falla(parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["tipo"] = "quincho"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "unidades[0].tipo" in str(exc_info.value)


def test_grupo_desconocido_falla(parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["grupos"]["no_existe"] = ["C1"]
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "grupos" in str(exc_info.value)
    assert "no_existe" in str(exc_info.value)


def test_identificador_repetido_falla(parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][1]["identificador"] = datos["unidades"][0]["identificador"]
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "unidades" in str(exc_info.value)


def test_miembro_de_grupo_inexistente_falla(parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["grupos"]["cocheras"] = ["NO-EXISTE"]
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "cocheras" in str(exc_info.value)
    assert "NO-EXISTE" in str(exc_info.value)


def test_coeficiente_de_suma_distinta_de_uno_falla(
    parametros: Any, georef: Any, tmp_path: Path
) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["coeficiente"] = "0.999999"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "unidades" in str(exc_info.value)


def test_coeficiente_con_siete_decimales_falla(
    parametros: Any, georef: Any, tmp_path: Path
) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["coeficiente"] = "0.4000001"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "unidades[0].coeficiente" in str(exc_info.value)


def test_coeficiente_como_numero_yaml_falla(parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["coeficiente"] = 0.4
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "unidades[0].coeficiente" in str(exc_info.value)


def test_coeficiente_con_digitos_no_ascii_falla(
    parametros: Any, georef: Any, tmp_path: Path
) -> None:
    """Mismo problema que el rompedor encontró en `Dinero` y en
    `_PATRON_PORCENTAJE` (cambio 1b vuelta 2): `_PATRON_COEFICIENTE` usaba
    `\\d` sin `re.ASCII`, que matchea cualquier dígito Unicode de categoría
    Nd. Un coeficiente escrito con dígitos arábigo-índicos (equivalente a
    "0.400000") no debe aceptarse."""
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["coeficiente"] = "٠.٤٠٠٠٠٠"  # noqa: RUF001 - "0.400000"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "unidades[0].coeficiente" in str(exc_info.value)


def test_superficie_no_positiva_falla(parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["superficie_m2"] = "0.00"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "unidades[0].superficie_m2" in str(exc_info.value)


def test_generales_distinto_de_todas_falla(parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["grupos"]["generales"] = ["C1"]
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "generales" in str(exc_info.value)


def test_clave_duplicada_en_el_yaml_falla(parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida, leer_semilla

    ruta = tmp_path / "semilla.yaml"
    ruta.write_text("version: 1\nversion: 1\nedificio: {nombre: x, localidad: y}\n")
    with pytest.raises(SemillaInvalida):
        leer_semilla(str(ruta), parametros, georef)


def test_campo_desconocido_falla(parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["campo_extra"] = 1
    with pytest.raises(SemillaInvalida):
        _escribir_y_leer(datos, parametros, georef, tmp_path)


def test_semilla_no_tiene_campos_de_persona_ni_contacto() -> None:
    """La semilla es ficticia: sin personas, sin contacto, sin calle (D10)."""
    import re

    texto = (RAIZ / "config" / "semilla" / "edificio-ejemplo.yaml").read_text()
    # 6.5: los ids de Georef (`provincia_id`/`departamento_id`/
    # `localidad_id`) son cadenas numéricas largas por diseño, pero sólo
    # aparecen como VALORES del YAML (nunca escritos de nuevo en un
    # comentario, ver la nota de arriba del archivo) — no son un teléfono.
    assert re.search(r"[\w.+-]+@[\w-]+\.\w+", texto) is None, "parece un email"
    sin_valores_de_id = re.sub(r"\w+_id:\s*\"\d+\"", "", texto)
    assert re.search(r"\b\d{2,4}[-\s]?\d{6,8}\b", sin_valores_de_id) is None, "parece un teléfono"
    for prohibida in ("nombre_completo", "dni", "telefono", "email", "contacto", "propietario"):
        assert prohibida not in texto.lower()


# --- 2.3 (3a): deuda del 1b con dueño 3 (D13) ---


def test_version_distinta_de_uno_falla(parametros: Any, georef: Any, tmp_path: Path) -> None:
    """D13: `Semilla.version` pasa a ser `Literal[1]` (hoy acepta cualquier
    `int`, por ejemplo `2`), escenario `datos-semilla` - Version distinta
    de 1."""
    from proptech_core.compartido.semilla import SemillaInvalida, leer_semilla

    datos = _valido()
    datos["version"] = 2
    ruta = tmp_path / "semilla.yaml"
    ruta.write_bytes(_dump(datos))

    with pytest.raises(SemillaInvalida) as exc_info:
        leer_semilla(str(ruta), parametros, georef)
    assert "version" in str(exc_info.value)


# --- 6.5: ubicación y pisos de la semilla (datos-semilla) ---


def test_ubicacion_del_ejemplo_tiene_los_tres_ids_de_georef(parametros: Any, georef: Any) -> None:
    """Escenario "Ubicación del ejemplo": el edificio trae los tres ids de
    ubicación, coherentes entre sí contra el archivo de Georef, y ya no una
    localidad de texto libre."""
    from proptech_core.compartido.semilla import leer_semilla

    ruta = RAIZ / "config" / "semilla" / "edificio-ejemplo.yaml"
    semilla = leer_semilla(str(ruta), parametros, georef)

    assert georef.existe_el_trio(
        semilla.edificio.provincia_id,
        semilla.edificio.departamento_id,
        semilla.edificio.localidad_id,
    )


def test_pisos_del_ejemplo_y_vocabulario_de_cada_unidad(parametros: Any, georef: Any) -> None:
    """Escenario "Pisos del ejemplo": el edificio declara 4 pisos y al menos
    1 subsuelo, y cada unidad tiene un piso de ese vocabulario: `PB` el
    local, `1` a `4` los departamentos y el subsuelo numerado las tres
    cocheras y la baulera."""
    from proptech_core.compartido.pisos import vocabulario_de_pisos
    from proptech_core.compartido.semilla import leer_semilla

    ruta = RAIZ / "config" / "semilla" / "edificio-ejemplo.yaml"
    semilla = leer_semilla(str(ruta), parametros, georef)

    assert semilla.edificio.pisos == 4
    assert semilla.edificio.subsuelos >= 1
    vocabulario = vocabulario_de_pisos(
        pisos=semilla.edificio.pisos, subsuelos=semilla.edificio.subsuelos
    )
    for unidad in semilla.unidades:
        assert unidad.piso in vocabulario, f"{unidad.identificador}: piso {unidad.piso!r}"

    local = next(u for u in semilla.unidades if u.identificador == "L-PB")
    assert local.piso == "PB"
    for cochera_o_baulera in ("C1", "C2", "C3", "B1"):
        unidad = next(u for u in semilla.unidades if u.identificador == cochera_o_baulera)
        assert unidad.piso.startswith("SS"), f"{cochera_o_baulera}: piso {unidad.piso!r}"
        assert unidad.piso != "SS", "el subsuelo tiene que estar numerado (6.5)"


def test_semilla_con_un_piso_fuera_del_vocabulario_falla(
    parametros: Any, georef: Any, tmp_path: Path
) -> None:
    """Escenario "Semilla con un piso fuera del vocabulario": la semilla
    declara una unidad en el piso "5" en un edificio de 4 pisos y 1
    subsuelo; el lector falla nombrando el campo piso y la unidad."""
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][1]["piso"] = "5"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    mensaje = str(exc_info.value)
    assert "unidades[1].piso" in mensaje
    assert "1A" in mensaje


def test_semilla_con_un_subsuelo_sin_numero_falla(
    parametros: Any, georef: Any, tmp_path: Path
) -> None:
    """Mismo escenario con `"SS"` sin número: ya no está en el vocabulario
    de un edificio de 4 pisos y 1 subsuelo (`SS1`)."""
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][2]["piso"] = "SS"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    mensaje = str(exc_info.value)
    assert "unidades[2].piso" in mensaje
    assert "C1" in mensaje


def test_semilla_con_una_ubicacion_incoherente_falla(
    parametros: Any, georef: Any, tmp_path: Path
) -> None:
    """Escenario "Semilla con una ubicación incoherente": la semilla
    declara una localidad que no pertenece al departamento declarado; el
    lector falla nombrando el campo de la localidad."""
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    # "50021" es Godoy Cruz (otro departamento de Mendoza); la localidad
    # "50007010" sigue siendo de Capital, así que el trío ya no encadena.
    datos["edificio"]["departamento_id"] = "50021"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "edificio.localidad_id" in str(exc_info.value)
