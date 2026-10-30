"""Ataques del tercer intento con dobles, sin PostgreSQL."""

from itertools import combinations
from uuid import uuid4

import pytest
from pydantic import ValidationError

from proptech_api.gastos import CuerpoEdicionGasto
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.gastos.aplicacion import gastos
from proptech_core.gastos.aplicacion.errores import EntradaInvalida
from proptech_core.gastos.dominio.gasto import CAMPOS_DE_FACTURA

from .test_gastos_aplicacion import fila_gasto, sesion_gasto


@pytest.mark.parametrize(
    "campos", [c for n in (1, 2, 3) for c in combinations(CAMPOS_DE_FACTURA, n)]
)
def test_quita_parcial(monkeypatch: pytest.MonkeyPatch, campos: tuple[str, ...]) -> None:
    fila = fila_gasto()
    sesion = sesion_gasto(monkeypatch, fila)
    with pytest.raises(EntradaInvalida):
        gastos.editar_gasto(
            sesion,
            Identidad(uuid4(), uuid4()),
            gasto_id=fila["id"],
            cambios=dict.fromkeys(campos),
            request_id=uuid4(),
        )
    assert not [c for c in sesion.execute.call_args_list if str(c.args[0]).startswith("UPDATE")]


@pytest.mark.parametrize("estado", ["borrador", "sin_ia", "en_revision", "aprobado"])
@pytest.mark.parametrize("importe", ["59.99", "60.00", "150.00"])
def test_quita_y_cambia_importe(monkeypatch: pytest.MonkeyPatch, estado: str, importe: str) -> None:
    fila = fila_gasto(estado)
    sesion = sesion_gasto(monkeypatch, fila)
    with pytest.raises(EntradaInvalida) as exc:
        gastos.editar_gasto(
            sesion,
            Identidad(uuid4(), uuid4()),
            gasto_id=fila["id"],
            cambios={**dict.fromkeys(CAMPOS_DE_FACTURA), "importe": Dinero(importe)},
            request_id=uuid4(),
        )
    assert exc.value.campo == ("estado" if estado == "aprobado" else "factura")
    assert not [c for c in sesion.execute.call_args_list if str(c.args[0]).startswith("UPDATE")]


@pytest.mark.parametrize("acreditado", ["0.00", "60.00"])
def test_edicion_legitima(monkeypatch: pytest.MonkeyPatch, acreditado: str) -> None:
    fila = fila_gasto()
    sesion = sesion_gasto(monkeypatch, fila)
    sesion.execute.return_value.scalar_one.return_value = acreditado
    gastos.editar_gasto(
        sesion,
        Identidad(uuid4(), uuid4()),
        gasto_id=fila["id"],
        cambios={"concepto": "Otro concepto ficticio"},
        request_id=uuid4(),
    )
    escrituras = [c for c in sesion.execute.call_args_list if str(c.args[0]).startswith("UPDATE")]
    assert len(escrituras) == 1
    assert escrituras[0].args[1]["concepto"] == "Otro concepto ficticio"
    assert all(escrituras[0].args[1][campo] == fila[campo] for campo in CAMPOS_DE_FACTURA)


@pytest.mark.parametrize("campo", CAMPOS_DE_FACTURA)
def test_http_null(campo: str) -> None:
    with pytest.raises(ValidationError) as exc:
        CuerpoEdicionGasto.model_validate({campo: None})
    assert "el campo no admite null" in str(exc.value)
