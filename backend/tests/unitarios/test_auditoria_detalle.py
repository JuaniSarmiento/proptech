"""Validación del detalle de auditoría (D9, cambio 2a, tarea 6.2): pura,
sin base de datos. `_detalle_validado` es la parte de `registrar()` que
rechaza un detalle con una clave no permitida ANTES de tocar la sesión — acá
se prueba aislada, sin necesitar Postgres para esto.

Escenario de `auditoria-de-acciones`: Clave no permitida en el detalle.
Lecciones: L-007 (el valor rechazado nunca aparece en el mensaje).
"""

from uuid import uuid4

import pytest

from proptech_core.acceso.aplicacion.auditoria import DetalleInvalido, _detalle_validado
from proptech_core.acceso.dominio.permisos import Accion


def test_detalle_valido_para_invitar_usuarios_pasa() -> None:
    complejo_id = uuid4()
    validado = _detalle_validado(
        Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS, {"complejo_id": str(complejo_id)}
    )
    assert validado == {"complejo_id": str(complejo_id)}


def test_clave_no_permitida_se_rechaza_y_el_valor_no_aparece_en_el_error() -> None:
    marcador = "VALOR-SECRETO-QUE-NUNCA-TIENE-QUE-APARECER"
    with pytest.raises(DetalleInvalido) as excinfo:
        _detalle_validado(
            Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS,
            {"complejo_id": str(uuid4()), "clave_no_permitida": marcador},
        )
    assert marcador not in str(excinfo.value)
    assert "clave_no_permitida" in str(excinfo.value)


def test_una_accion_sin_modelo_registrado_acepta_detalle_vacio() -> None:
    # Accion.INFORMAR_PAGO no tiene un modelo propio en el registro: sólo
    # admite detalle vacío (el modelo base no declara ningún campo).
    assert _detalle_validado(Accion.INFORMAR_PAGO, {}) == {}


def test_una_accion_sin_modelo_registrado_rechaza_cualquier_clave() -> None:
    with pytest.raises(DetalleInvalido):
        _detalle_validado(Accion.INFORMAR_PAGO, {"algo": "x"})


def test_falta_un_campo_requerido_del_modelo_se_rechaza() -> None:
    with pytest.raises(DetalleInvalido):
        _detalle_validado(Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS, {})
