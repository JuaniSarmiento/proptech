"""Casos de uso de `gastos` con dobles de persistencia (reproducciones del
rompedor del 6, intento 2, absorbidas acá). No certifican PostgreSQL: la
contraparte con base real vive en `tests/integracion/test_*` de cada recurso."""

from contextlib import nullcontext
from datetime import date
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from proptech_api import gastos as api
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Asignacion, Rol
from proptech_core.compartido.dinero import Dinero
from proptech_core.gastos.aplicacion import cargos_particulares, gastos, notas_de_credito
from proptech_core.gastos.aplicacion.errores import EntradaInvalida, error_de_validacion
from proptech_core.gastos.dominio.gasto import CAMPOS_DE_FACTURA, DatosGasto


def fila_gasto(estado: str = "borrador") -> dict[str, Any]:
    return dict(
        id=uuid4(),
        complejo_id=uuid4(),
        concepto="Prueba ficticia",
        categoria_id=uuid4(),
        grupo_id=uuid4(),
        proveedor_id=None,
        periodo=date(2026, 9, 1),
        periodo_de_imputacion=date(2026, 10, 1),
        tipo="ordinario",
        importe="100.00",
        estado=estado,
        cuit_emisor="30712345678",
        punto_de_venta="1",
        tipo_de_comprobante="A",
        numero_de_comprobante="123",
        documento_receptor=None,
    )


def sesion_gasto(monkeypatch: pytest.MonkeyPatch, fila: dict[str, Any]) -> MagicMock:
    sesion = MagicMock()
    sesion.in_transaction.return_value = False
    sesion.begin.return_value = nullcontext()
    resultado = MagicMock()
    resultado.mappings.return_value.first.return_value = fila
    resultado.scalar_one.return_value = "60.00"
    sesion.execute.return_value = resultado
    monkeypatch.setattr(gastos, "_validar_pertenencia", lambda *_: None)
    monkeypatch.setattr(gastos, "registrar", lambda *_, **__: None)
    return sesion


@pytest.mark.parametrize("estado", ["borrador", "sin_ia", "en_revision"])
def test_no_se_quita_factura_con_notas(monkeypatch: pytest.MonkeyPatch, estado: str) -> None:
    fila = fila_gasto(estado)
    sesion = sesion_gasto(monkeypatch, fila)
    rechazo = None
    try:
        gastos.editar_gasto(
            sesion,
            Identidad(uuid4(), uuid4()),
            gasto_id=fila["id"],
            cambios=dict.fromkeys(CAMPOS_DE_FACTURA),
            request_id=uuid4(),
        )
    except EntradaInvalida as error:
        rechazo = error
    escrituras = [c for c in sesion.execute.call_args_list if str(c.args[0]).startswith("UPDATE")]
    assert rechazo is not None, f"Se permite quitar la factura con notas: {escrituras}"
    assert not escrituras


@pytest.mark.parametrize("importe,rechaza", [("60.00", False), ("59.99", True)])
@pytest.mark.parametrize("estado", ["borrador", "sin_ia", "en_revision"])
def test_tope_al_editar(
    monkeypatch: pytest.MonkeyPatch, importe: str, rechaza: bool, estado: str
) -> None:
    fila = fila_gasto(estado)
    sesion = sesion_gasto(monkeypatch, fila)
    rechazo = None
    try:
        gastos.editar_gasto(
            sesion,
            Identidad(uuid4(), uuid4()),
            gasto_id=fila["id"],
            cambios={"importe": Dinero(importe)},
            request_id=uuid4(),
        )
    except EntradaInvalida as error:
        rechazo = error
    assert (rechazo is not None) == rechaza
    if rechazo is not None:
        assert rechazo.campo == "importe"


def test_patch_y_reaprobar_conservan_imputacion(monkeypatch: pytest.MonkeyPatch) -> None:
    fila = fila_gasto("aprobado")
    sesion = sesion_gasto(monkeypatch, fila)
    identidad = Identidad(uuid4(), uuid4())
    gastos.editar_gasto(sesion, identidad, gasto_id=fila["id"], cambios={}, request_id=uuid4())
    gastos.aprobar_gasto(sesion, identidad, gasto_id=fila["id"], request_id=uuid4())
    assert not [c for c in sesion.execute.call_args_list if str(c.args[0]).startswith("UPDATE")]


@pytest.mark.parametrize("rol", list(Rol))
@pytest.mark.parametrize("recurso", ["gasto", "nota_de_credito", "cargo_particular"])
def test_detalle_respeta_matriz(monkeypatch: pytest.MonkeyPatch, rol: Rol, recurso: str) -> None:
    fila = fila_gasto()
    complejo = fila["complejo_id"]
    asignacion = (
        Asignacion(rol, complejo, uuid4(), "propietario")
        if rol == Rol.VECINO
        else Asignacion(rol, None if rol == Rol.SUPER_ADMIN else complejo)
    )
    monkeypatch.setattr(api, "cargar_asignaciones", lambda *_: [asignacion])
    modulo, cargar = {
        "gasto": (gastos, "cargar_gasto"),
        "nota_de_credito": (notas_de_credito, "cargar_nota_de_credito"),
        "cargo_particular": (cargos_particulares, "cargar_cargo"),
    }[recurso]
    monkeypatch.setattr(modulo, cargar, lambda *_: fila)
    handler = getattr(api, "ver_" + recurso)
    if rol == Rol.VECINO:
        with pytest.raises(HTTPException) as exc:
            handler(uuid4(), Identidad(uuid4(), uuid4()), MagicMock())
        assert exc.value.status_code == 403
        assert isinstance(exc.value.detail, dict)
        assert exc.value.detail["codigo"] == "sin_permiso"
    else:
        assert handler(uuid4(), Identidad(uuid4(), uuid4()), MagicMock()) == fila


@pytest.mark.parametrize(
    "cambios",
    [
        {"concepto": "PRIVADO\x00"},
        {"tipo": "PRIVADO"},
        {"cuit_emisor": "PRIVADO", "punto_de_venta": None},
    ],
)
def test_error_no_repite_entrada(cambios: dict[str, Any]) -> None:
    fila = fila_gasto()
    datos = {
        k: v
        for k, v in fila.items()
        if k not in {"id", "complejo_id", "estado", "periodo_de_imputacion"}
    }
    datos.update(cambios)
    with pytest.raises(ValidationError) as exc:
        DatosGasto.model_validate(datos)
    error = error_de_validacion(exc.value)
    assert "PRIVADO" not in error.motivo
    assert error.motivo


@pytest.mark.parametrize("recurso", ["gasto", "nota_de_credito", "cargo_particular"])
def test_detalle_fuera_de_alcance_da_404(monkeypatch: pytest.MonkeyPatch, recurso: str) -> None:
    fila = fila_gasto()
    monkeypatch.setattr(api, "cargar_asignaciones", lambda *_: [Asignacion(Rol.CONTADOR, uuid4())])
    modulo, cargar = {
        "gasto": (gastos, "cargar_gasto"),
        "nota_de_credito": (notas_de_credito, "cargar_nota_de_credito"),
        "cargo_particular": (cargos_particulares, "cargar_cargo"),
    }[recurso]
    monkeypatch.setattr(modulo, cargar, lambda *_: fila)
    with pytest.raises(HTTPException) as exc:
        getattr(api, "ver_" + recurso)(uuid4(), Identidad(uuid4(), uuid4()), MagicMock())
    assert exc.value.status_code == 404


def test_nota_sin_factura_rechazada_antes_de_insertar(monkeypatch: pytest.MonkeyPatch) -> None:
    fila = fila_gasto()
    fila.update(dict.fromkeys(CAMPOS_DE_FACTURA))
    sesion = sesion_gasto(monkeypatch, fila)
    with pytest.raises(EntradaInvalida) as exc:
        notas_de_credito.crear_nota_de_credito(
            sesion,
            Identidad(uuid4(), uuid4()),
            gasto_id=fila["id"],
            request_id=uuid4(),
            datos={
                "importe": Dinero("10.00"),
                "periodo": date(2026, 10, 1),
                "cuit_emisor": "20123456786",
                "punto_de_venta": "1",
                "tipo_de_comprobante": "NC",
                "numero_de_comprobante": "1",
            },
        )
    assert exc.value.campo == "gasto_id"
    assert not [c for c in sesion.execute.call_args_list if str(c.args[0]).startswith("INSERT")]


def test_quitar_la_factura_sin_notas_se_permite(monkeypatch: pytest.MonkeyPatch) -> None:
    """Borde de F2-1: sin notas acreditadas, la factura se puede quitar."""
    fila = fila_gasto("borrador")
    sesion = sesion_gasto(monkeypatch, fila)
    sesion.execute.return_value.scalar_one.return_value = "0.00"
    gastos.editar_gasto(
        sesion,
        Identidad(uuid4(), uuid4()),
        gasto_id=fila["id"],
        cambios=dict.fromkeys(CAMPOS_DE_FACTURA),
        request_id=uuid4(),
    )
    assert [c for c in sesion.execute.call_args_list if str(c.args[0]).startswith("UPDATE")]
