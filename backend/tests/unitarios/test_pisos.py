"""3.1: el vocabulario de pisos como función pura (D3) — `PB` siempre,
`SS1..SS<subsuelos>`, `1..<pisos>`, con 0 subsuelos y 0 pisos, y los
límites 5 y 60; coincidencia completa y sólo ASCII (L-008)."""

import pytest

from proptech_core.compartido.pisos import vocabulario_de_pisos


def test_pb_siempre_presente() -> None:
    assert "PB" in vocabulario_de_pisos(pisos=0, subsuelos=0)
    assert "PB" in vocabulario_de_pisos(pisos=4, subsuelos=1)


def test_subsuelos_desde_ss1() -> None:
    assert vocabulario_de_pisos(pisos=0, subsuelos=3) == {"PB", "SS1", "SS2", "SS3"}


def test_pisos_desde_1() -> None:
    assert vocabulario_de_pisos(pisos=4, subsuelos=0) == {"PB", "1", "2", "3", "4"}


def test_cero_pisos_y_cero_subsuelos_es_solo_pb() -> None:
    assert vocabulario_de_pisos(pisos=0, subsuelos=0) == {"PB"}


def test_limite_maximo_5_subsuelos_y_60_pisos() -> None:
    vocab = vocabulario_de_pisos(pisos=60, subsuelos=5)
    assert "SS5" in vocab
    assert "SS6" not in vocab
    assert "60" in vocab
    assert "61" not in vocab


@pytest.mark.parametrize("pisos", [-1, 61])
def test_pisos_fuera_de_rango_rechazado(pisos: int) -> None:
    with pytest.raises(ValueError):
        vocabulario_de_pisos(pisos=pisos, subsuelos=0)


@pytest.mark.parametrize("subsuelos", [-1, 6])
def test_subsuelos_fuera_de_rango_rechazado(subsuelos: int) -> None:
    with pytest.raises(ValueError):
        vocabulario_de_pisos(pisos=0, subsuelos=subsuelos)


def test_piso_no_ascii_no_coincide_con_el_patron() -> None:
    from proptech_core.compartido.pisos import PATRON_PISO

    assert PATRON_PISO.fullmatch("１") is None  # noqa: RUF001 - dígito de ancho completo, no ASCII


def test_coincidencia_completa_no_substring() -> None:
    from proptech_core.compartido.pisos import PATRON_PISO

    assert PATRON_PISO.fullmatch("1\n") is None
    assert PATRON_PISO.fullmatch(" 1") is None
    assert PATRON_PISO.fullmatch("SS") is None
    assert PATRON_PISO.fullmatch("pb") is None
