"""Las reglas puras del cambio de titular (H-030, R32, D-168): quién vende y a quién. Sin base."""

from datetime import date
from uuid import UUID, uuid4

import pytest

from proptech_core.titularidad.dominio.cambio import (
    CambioInvalido,
    validar_compradores,
    validar_pedido,
)

HOY = date(2026, 11, 18)
ANA, BETO, CARLA, DORA = (uuid4() for _ in range(4))


def _pedido(**cambios: object) -> None:
    base: dict[str, object] = {
        "fecha": date(2026, 11, 10),
        "hoy": HOY,
        "vendedores": [ANA],
        "cantidad_de_compradores": 1,
        "propietarios": {ANA, BETO},
    }
    validar_pedido(**{**base, **cambios})  # type: ignore[arg-type]


def _campo_del_pedido(**cambios: object) -> str:
    with pytest.raises(CambioInvalido) as error:
        _pedido(**cambios)
    return error.value.campo


def test_un_pedido_valido_no_levanta_nada() -> None:
    _pedido()
    _pedido(fecha=HOY)


def test_la_fecha_futura_es_invalida() -> None:
    assert _campo_del_pedido(fecha=date(2026, 11, 19)) == "fecha"


def test_sin_vendedores_es_invalido() -> None:
    assert _campo_del_pedido(vendedores=[]) == "vendedores"


def test_sin_compradores_es_invalido() -> None:
    assert _campo_del_pedido(cantidad_de_compradores=0) == "compradores"


def test_un_vendedor_repetido_es_invalido() -> None:
    assert _campo_del_pedido(vendedores=[ANA, ANA]) == "vendedores"


@pytest.mark.parametrize("vendedor", [CARLA, DORA])
def test_quien_no_es_propietario_actual_no_vende(vendedor: UUID) -> None:
    assert _campo_del_pedido(vendedores=[vendedor]) == "vendedores"
    assert _campo_del_pedido(vendedores=[ANA, vendedor]) == "vendedores"


def _campo_de_compradores(**cambios: object) -> str:
    base: dict[str, object] = {
        "vendedores": [ANA],
        "compradores": [CARLA],
        "con_vinculo_en_la_unidad": {ANA, BETO},
    }
    with pytest.raises(CambioInvalido) as error:
        validar_compradores(**{**base, **cambios})  # type: ignore[arg-type]
    return error.value.campo


def test_compradores_validos() -> None:
    validar_compradores(
        vendedores=[ANA], compradores=[CARLA, DORA], con_vinculo_en_la_unidad={ANA, BETO}
    )


def test_vender_a_uno_mismo_es_invalido() -> None:
    assert _campo_de_compradores(compradores=[ANA]) == "compradores"
    assert _campo_de_compradores(compradores=[CARLA, ANA]) == "compradores"


def test_un_comprador_repetido_es_invalido() -> None:
    assert _campo_de_compradores(compradores=[CARLA, CARLA]) == "compradores"


def test_quien_ya_tiene_otro_vinculo_con_la_unidad_no_compra() -> None:
    # Beto es el otro copropietario o el inquilino: la base admite una asignación por unidad.
    assert _campo_de_compradores(compradores=[BETO]) == "compradores"
