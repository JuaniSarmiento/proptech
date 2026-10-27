"""2.3: coherencia del trío de ubicación contra el archivo REAL de Georef
(no fixtures sintéticos): localidad de otro departamento, departamento de
otra provincia, id inexistente, trío incompleto (acá, incoherente por
construcción — el "incompleto" real lo valida Pydantic en la API, tarea
2.6) y el trío coherente. `campo_incoherente` nombra el primer campo que no
encadena, nunca el valor (L-007)."""

from pathlib import Path

from proptech_core.compartido.georef import Georef, leer_georef

RAIZ = Path(__file__).resolve().parents[3] / "config" / "georef"

# Ids reales, confirmados contra config/georef/ el 26/10/2026:
# Mendoza = 50, Capital (Mendoza) = 50007, "Mendoza" (localidad de Capital) = 50007010.
# Godoy Cruz (depto de Mendoza) = 50021, "Ciudad de Godoy Cruz" = 5002101001.
# San Juan = 70, "25 de Mayo" (depto de San Juan) = 70126, "El Encón" = 70126010.
_MENDOZA = "50"
_CAPITAL = "50007"
_LOCALIDAD_CAPITAL = "50007010"
_GODOY_CRUZ = "50021"
_LOCALIDAD_GODOY_CRUZ = "5002101001"
_SAN_JUAN_DEPTO = "70126"
_LOCALIDAD_SAN_JUAN = "70126010"


def _georef() -> Georef:
    return leer_georef(str(RAIZ))


def test_trio_coherente() -> None:
    georef = _georef()
    assert georef.campo_incoherente(_MENDOZA, _CAPITAL, _LOCALIDAD_CAPITAL) is None


def test_localidad_de_otro_departamento() -> None:
    georef = _georef()
    # Provincia y departamento coherentes (Mendoza/Capital), pero la
    # localidad es de Godoy Cruz, otro departamento de la misma provincia.
    assert georef.campo_incoherente(_MENDOZA, _CAPITAL, _LOCALIDAD_GODOY_CRUZ) == "localidad_id"


def test_departamento_de_otra_provincia() -> None:
    georef = _georef()
    # El departamento y la localidad son coherentes entre sí (San Juan),
    # pero se manda con la provincia Mendoza.
    assert (
        georef.campo_incoherente(_MENDOZA, _SAN_JUAN_DEPTO, _LOCALIDAD_SAN_JUAN)
        == "departamento_id"
    )


def test_id_de_provincia_que_no_existe() -> None:
    georef = _georef()
    assert georef.campo_incoherente("99", _CAPITAL, _LOCALIDAD_CAPITAL) == "provincia_id"


def test_id_de_departamento_que_no_existe() -> None:
    georef = _georef()
    assert georef.campo_incoherente(_MENDOZA, "99999", _LOCALIDAD_CAPITAL) == "departamento_id"


def test_id_de_localidad_que_no_existe() -> None:
    georef = _georef()
    assert georef.campo_incoherente(_MENDOZA, _CAPITAL, "9999999999") == "localidad_id"


def test_ningun_mensaje_repite_el_id_recibido() -> None:
    georef = _georef()
    campo = georef.campo_incoherente(_MENDOZA, _CAPITAL, _LOCALIDAD_GODOY_CRUZ)
    assert campo == "localidad_id"
    assert _LOCALIDAD_GODOY_CRUZ not in str(campo)
