"""Los enlaces firmados de la expensa (7, H-015, D-070, E13): HMAC-SHA256, vencimiento corto."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from proptech_core.liquidacion.aplicacion.enlaces import (
    EnlaceAlterado,
    EnlaceVencido,
    firmar_enlace,
    verificar_enlace,
)

CLAVE = "clave-de-prueba-de-enlaces-firmados-0123456789"
AHORA = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


def _token(**cambios: object) -> tuple[str, dict[str, object]]:
    datos: dict[str, object] = {
        "administracion_id": uuid4(),
        "documento_id": uuid4(),
        "variante": "completa",
        "vence_en": AHORA + timedelta(minutes=15),
        "clave": CLAVE,
    }
    datos.update(cambios)
    return firmar_enlace(**datos), datos  # type: ignore[arg-type]


def test_un_enlace_firmado_se_verifica_y_devuelve_lo_firmado() -> None:
    token, datos = _token()
    enlace = verificar_enlace(token, clave=CLAVE, ahora=AHORA)
    assert enlace.administracion_id == datos["administracion_id"]
    assert enlace.documento_id == datos["documento_id"]
    assert enlace.variante == "completa"
    assert enlace.vence_en == datos["vence_en"]


def test_el_token_no_lleva_datos_personales_ni_el_nombre_de_la_clave() -> None:
    token, _ = _token()
    assert CLAVE not in token and "@" not in token


def test_un_enlace_vencido_se_distingue_de_uno_alterado() -> None:
    token, _ = _token(vence_en=AHORA - timedelta(minutes=1))
    with pytest.raises(EnlaceVencido):
        verificar_enlace(token, clave=CLAVE, ahora=AHORA)


def test_vence_justo_en_el_instante_de_vencimiento() -> None:
    token, datos = _token()
    with pytest.raises(EnlaceVencido):
        verificar_enlace(token, clave=CLAVE, ahora=datos["vence_en"])  # type: ignore[arg-type]


@pytest.mark.parametrize("posicion", [0, 10, -1, -2])
def test_cualquier_caracter_cambiado_lo_altera(posicion: int) -> None:
    token, _ = _token()
    caracteres = list(token)
    caracteres[posicion] = "A" if caracteres[posicion] != "A" else "B"
    with pytest.raises(EnlaceAlterado):
        verificar_enlace("".join(caracteres), clave=CLAVE, ahora=AHORA)


def test_la_firma_en_mayusculas_no_es_la_misma_firma() -> None:
    token, _ = _token()
    cuerpo, firma = token.rsplit(".", 1)
    with pytest.raises(EnlaceAlterado):
        verificar_enlace(f"{cuerpo}.{firma.upper()}", clave=CLAVE, ahora=AHORA)


def test_otra_clave_no_verifica() -> None:
    token, _ = _token()
    with pytest.raises(EnlaceAlterado):
        verificar_enlace(token, clave="otra-clave-de-prueba-de-enlaces-0123456789", ahora=AHORA)


@pytest.mark.parametrize(
    "token", ["", ".", "a.b", "sin-punto", "a.b.c", "\xff", pytest.param("x" * 5000, id="largo")]
)
def test_un_token_mal_formado_es_alterado(token: str) -> None:
    with pytest.raises(EnlaceAlterado):
        verificar_enlace(token, clave=CLAVE, ahora=AHORA)


def test_una_clave_corta_se_rechaza_al_firmar() -> None:
    with pytest.raises(ValueError, match="clave"):
        firmar_enlace(
            administracion_id=uuid4(),
            documento_id=uuid4(),
            variante="completa",
            vence_en=AHORA,
            clave="corta",
        )


def test_el_vencimiento_sin_zona_horaria_se_rechaza() -> None:
    with pytest.raises(ValueError, match="vence_en"):
        firmar_enlace(
            administracion_id=uuid4(),
            documento_id=uuid4(),
            variante="completa",
            vence_en=datetime(2026, 11, 15, 12, 0),
            clave=CLAVE,
        )
