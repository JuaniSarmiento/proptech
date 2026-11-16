"""El nombre con el que baja el PDF de una expensa (H-017), sin base."""

from datetime import date

import pytest

from proptech_core.liquidacion.dominio.nombre_de_archivo import nombre_del_pdf


def test_periodo_unidad_y_variante() -> None:
    assert nombre_del_pdf(date(2026, 11, 1), "1B", "completa") == "expensa-2026-11-1b-completa.pdf"


def test_la_variante_cambia_el_guion_bajo() -> None:
    assert (
        nombre_del_pdf(date(2026, 1, 1), "2A", "sin_extraordinaria")
        == "expensa-2026-01-2a-sin-extraordinaria.pdf"
    )


@pytest.mark.parametrize(
    ("identificador", "esperado"),
    [
        ("PB-1", "pb-1"),
        ("1 B", "1-b"),
        ("Planta Baja / Ñandú", "planta-baja-nandu"),
        ('1"; filename="x', "1-filename-x"),
        ("../../etc", "etc"),
        ("   ", "unidad"),
        ("", "unidad"),
    ],
)
def test_el_identificador_queda_en_a_z_0_9_y_guion(identificador: str, esperado: str) -> None:
    assert nombre_del_pdf(date(2026, 11, 1), identificador, "completa") == (
        f"expensa-2026-11-{esperado}-completa.pdf"
    )
