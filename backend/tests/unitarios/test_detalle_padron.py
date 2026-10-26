from uuid import uuid4

import pytest

from proptech_core.acceso.aplicacion.auditoria import DetalleInvalido, _detalle_validado
from proptech_core.acceso.dominio.eventos import EventoDelPadron


@pytest.mark.parametrize(
    "evento,campos",
    [
        ("crear_unidad", ["coeficiente"]),
        ("editar_unidad", ["piso", "coeficiente"]),
        ("crear_grupo", ["clave", "unidades"]),
        ("editar_grupo", ["nombre"]),
        ("fijar_unidades", ["unidades"]),
        ("editar_categoria", ["activa"]),
        ("reordenar_categorias", ["orden"]),
    ],
)
def test_detalle_valido_por_evento(evento: str, campos: list[str]) -> None:
    detalle = {"complejo_id": str(uuid4()), "campos": campos}
    assert _detalle_validado(EventoDelPadron(evento), detalle) == detalle


@pytest.mark.parametrize(
    "evento,extra",
    [
        (EventoDelPadron.EDITAR_GRUPO, {"campos": ["coeficiente"]}),
        (EventoDelPadron.EDITAR_UNIDAD, {"piso_anterior": "VALOR_PRIVADO"}),
    ],
)
def test_rechazo_antes_de_escribir(evento: EventoDelPadron, extra: dict[str, object]) -> None:
    detalle = {"complejo_id": str(uuid4()), "campos": ["piso"], **extra}
    with pytest.raises(DetalleInvalido) as error:
        _detalle_validado(evento, detalle)
    assert "VALOR_PRIVADO" not in str(error.value)
