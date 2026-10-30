"""Contrato público de los 403 del 2d."""

import pytest
from pydantic import ValidationError

from proptech_api.errores import Error403


@pytest.mark.parametrize(
    "detail",
    [
        {"codigo": "sin_acceso"},
        {
            "codigo": "sin_permiso",
            "detalle": "sin_permiso",
            "permiso_faltante": "configurar_padron",
        },
    ],
)
def test_error403_conserva_el_contrato(detail: dict[str, str]) -> None:
    try:
        resultado = Error403.model_validate({"detail": detail}).model_dump(exclude_none=True)
    except ValidationError:
        resultado = None
    assert resultado == {"detail": detail}


@pytest.mark.parametrize("codigo", ["desconocido", ""])
def test_error403_no_acepta_codigos_fuera_de_lista(codigo: str) -> None:
    with pytest.raises(ValidationError):
        Error403.model_validate({"detail": {"codigo": codigo}})
