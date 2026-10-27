"""E8: sólo SA y AP, entre los nueve perfiles y alcances de D-106."""

from typing import cast
from uuid import uuid4

import pytest

from proptech_core.acceso.dominio.permisos import Accion, Asignacion, Rol, puede


@pytest.mark.parametrize(
    "rol,principal,vinculo,esperado",
    [
        (Rol.SUPER_ADMIN, True, None, True),
        (Rol.ADMINISTRADOR, True, None, True),
        (Rol.ADMINISTRADOR, False, None, False),
        (Rol.CONTADOR, True, None, False),
        (Rol.CONTADOR, False, None, False),
        (Rol.AUXILIAR, False, None, False),
        (Rol.CONSEJO, False, None, False),
        (Rol.VECINO, False, "propietario", False),
        (Rol.VECINO, False, "inquilino", False),
    ],
)
def test_fila_de_correccion(rol: Rol, principal: bool, vinculo: str | None, esperado: bool) -> None:
    edificio = uuid4()
    asignacion = Asignacion(
        rol, None if principal else edificio, uuid4() if vinculo else None, vinculo
    )
    assert puede([asignacion], cast(Accion, "corregir_movimiento"), edificio) is esperado


@pytest.mark.parametrize("extra", ["motivo", "importe"])
def test_detalle_correccion_rechaza_datos_del_libro(extra: str) -> None:
    from proptech_core.acceso.aplicacion.auditoria import DetalleInvalido, _detalle_validado

    detalle = {
        "complejo_id": str(uuid4()),
        "forma": "credito",
        "corrige": str(uuid4()),
        extra: "PRIVADO",
    }
    with pytest.raises(DetalleInvalido) as error:
        _detalle_validado(Accion.CORREGIR_MOVIMIENTO, detalle)
    assert "PRIVADO" not in str(error.value)
    assert extra in str(error.value)
