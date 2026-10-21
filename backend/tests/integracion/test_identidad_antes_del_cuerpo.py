"""Frente 1 (fila 1 del auditor): la guarda de identidad REAL de las rutas
del 3a, sin `dependency_overrides`, y el barrido que dice verlas a todas.

`api_edificio` deja inyectado al super_admin al final del fixture; acá se saca
el override antes de cada pedido para que corra `identidad_actual` de
producción (`proptech_api/acceso.py`)."""

import uuid
from typing import Any

import pytest

from proptech_api.acceso import identidad_actual

from ._api_edificios import ApiEdificio
from .test_rutas_protegidas import _RUTAS_CUBIERTAS

pytestmark = pytest.mark.integracion


def _resolver(api: ApiEdificio, ruta: str) -> str:
    return ruta.format(
        complejo_id=api.edificio,
        unidad_id=api.unidad,
        grupo_id=api.grupo_ajeno,
        categoria_id=api.categoria_ajena,
        # 5.6: no hacen falta filas reales acá tampoco — este archivo nunca
        # llega a tocar la base (prueba justo lo contrario, D7).
        invitacion_id=uuid.uuid4(),
        asignacion_id=uuid.uuid4(),
    )


def _sin_override(api: ApiEdificio) -> None:
    api.app.dependency_overrides.pop(identidad_actual, None)


_CREDENCIALES: list[dict[str, Any]] = [
    {"headers": {"Authorization": "Bearer cualquier-cosa"}},
    {"headers": {"Authorization": "Basic dGl0dWxhcjp0aXR1bGFy"}},
    {"headers": {"Cookie": "session=forjada; proptech_sesion=forjada"}},
    {"headers": {"X-Administracion-Id": "00000000-0000-0000-0000-000000000001"}},
]


@pytest.mark.parametrize("credencial", _CREDENCIALES, ids=lambda c: next(iter(c["headers"])))
def test_credencial_inventada_o_invalida_da_401_en_toda_ruta(
    api_edificio: ApiEdificio, credencial: dict[str, Any]
) -> None:
    _sin_override(api_edificio)
    fallas = []
    for ruta, metodo in sorted(_RUTAS_CUBIERTAS):
        respuesta = api_edificio.cliente.request(
            metodo, _resolver(api_edificio, ruta), json={}, **credencial
        )
        if respuesta.status_code != 401:
            fallas.append((metodo, ruta, respuesta.status_code))
    assert not fallas, fallas


_RUTAS_CON_CUERPO = sorted(
    (ruta, metodo)
    for ruta, metodo in _RUTAS_CUBIERTAS
    if metodo in ("POST", "PATCH", "PUT") and not ruta.endswith("/sin-saldos-previos")
)


@pytest.mark.parametrize("ruta_y_metodo", _RUTAS_CON_CUERPO)
def test_cuerpo_json_malformado_sin_identidad_da_401_no_422(
    api_edificio: ApiEdificio, ruta_y_metodo: tuple[str, str]
) -> None:
    """Spec `autorizacion-por-rol`: "toda ruta de esa lista MUST responder
    401 sin identidad". Con un cuerpo que no es JSON válido, FastAPI corta en
    el parseo del cuerpo ANTES de resolver las dependencias, así que un
    anónimo recibe 422 (y con eso aprende la forma del cuerpo de la ruta)
    en vez de 401. El barrido de R6 sólo manda cuerpos válidos."""
    _sin_override(api_edificio)
    ruta, metodo = ruta_y_metodo
    respuesta = api_edificio.cliente.request(
        metodo,
        _resolver(api_edificio, ruta),
        content=b'{"nombre": ',
        headers={"Content-Type": "application/json"},
    )
    assert respuesta.status_code == 401, (metodo, ruta, respuesta.status_code, respuesta.text)


@pytest.mark.parametrize("contenido", [b'{"nombre":', b"[] trailing", b'{"nombre":"\xff"}'])
@pytest.mark.parametrize("autenticado", [False, True])
def test_error_de_parseo_respeta_identidad_sin_sql(
    api_edificio: ApiEdificio, contenido: bytes, autenticado: bool
) -> None:
    from sqlalchemy import event

    api = api_edificio
    if not autenticado:
        _sin_override(api)
    sentencias = []

    def registrar(*args: Any) -> None:
        sentencias.append(args[2])

    event.listen(api.app.state.engine, "before_cursor_execute", registrar)
    try:
        respuesta = api.cliente.post(
            "/api/complejos", content=contenido, headers={"Content-Type": "application/json"}
        )
    finally:
        event.remove(api.app.state.engine, "before_cursor_execute", registrar)
    esperado = (400 if b"\xff" in contenido else 422) if autenticado else 401
    assert respuesta.status_code == esperado, respuesta.text
    assert sentencias == []
