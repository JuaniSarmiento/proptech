"""5.3: relaciones persona-unidad, reuso y permiso antes del cuerpo."""

from typing import Any

import pytest

from ._api_edificios import ApiEdificio
from ._usuarios import preparar

pytestmark = pytest.mark.integracion


def ruta(api: ApiEdificio, unidad: Any = None) -> str:
    return f"/api/unidades/{unidad or api.unidad}/vecinos"


def datos(email: str = "vecina@example.invalid", vinculo: str = "propietario") -> dict[str, str]:
    return {"nombre": "Vecina ficticia", "email": email, "vinculo": vinculo}


def _conteos(api_edificio: ApiEdificio) -> Any:
    return api_edificio.filas(
        "SELECT (SELECT count(*) FROM persona),(SELECT count(*) FROM asignacion_rol),"
        "(SELECT count(*) FROM invitacion),(SELECT count(*) FROM auditoria)"
    )


def test_dos_propietarios_y_una_persona_en_dos_unidades(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    cola = preparar(api_edificio, monkeypatch)
    api_edificio.como("super_admin")
    r1 = api_edificio.cliente.post(ruta(api_edificio), json=datos())
    assert r1.status_code == 201, r1.text
    r2 = api_edificio.cliente.post(ruta(api_edificio), json=datos("otro@example.invalid"))
    assert r2.status_code == 201, r2.text
    r3 = api_edificio.cliente.post(
        ruta(api_edificio, api_edificio.otra_unidad), json=datos(vinculo="inquilino")
    )
    assert r3.status_code == 201, r3.text
    assert r1.json()["persona_id"] == r3.json()["persona_id"] != r2.json()["persona_id"]
    assert api_edificio.filas("SELECT count(*) FROM persona WHERE email IS NOT NULL") == [(2,)]
    filas = api_edificio.filas(
        "SELECT unidad_id,vinculo FROM asignacion_rol WHERE persona_id=%s ORDER BY vinculo",
        (r1.json()["persona_id"],),
    )
    assert filas == [(api_edificio.otra_unidad, "inquilino"), (api_edificio.unidad, "propietario")]
    assert api_edificio.filas(
        "SELECT count(*) FROM invitacion WHERE persona_id=%s "
        "AND estado IN ('pendiente','enviada','fallida')",
        (r1.json()["persona_id"],),
    ) == [(1,)]
    auditorias = api_edificio.filas(
        "SELECT detalle FROM auditoria WHERE accion='dar_de_alta_vecino' ORDER BY id"
    )
    assert [d[0] for d in auditorias] == [
        {"persona_id": r.json()["persona_id"], "asignacion_id": r.json()["asignacion_id"]}
        for r in (r1, r2, r3)
    ]
    assert all("@" not in str(t) for t in cola.trabajos)


@pytest.mark.parametrize(
    ("caso", "esperado"),
    [("duplicado", 409), ("vecino", 403), ("ajena", 404), ("vinculo", 422), ("extra", 422)],
)
def test_rechazos_no_escriben(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch, caso: str, esperado: int
) -> None:
    cola = preparar(api_edificio, monkeypatch)
    api_edificio.como("super_admin")
    if caso == "duplicado":
        assert api_edificio.cliente.post(ruta(api_edificio), json=datos()).status_code == 201
    if caso == "vecino":
        api_edificio.como("vecino")
    cuerpo: dict[str, Any] = datos(vinculo="inquilino" if caso == "duplicado" else "propietario")
    if caso == "vinculo":
        cuerpo["vinculo"] = "MARCADOR"
    if caso == "extra":
        cuerpo["extra"] = "MARCADOR"
    antes = _conteos(api_edificio)
    trabajos = len(cola.trabajos)
    r = api_edificio.cliente.post(
        ruta(api_edificio, api_edificio.unidad_ajena if caso == "ajena" else None), json=cuerpo
    )
    assert r.status_code == esperado, r.text
    assert "MARCADOR" not in r.text
    assert _conteos(api_edificio) == antes
    assert len(cola.trabajos) == trabajos
    if caso == "vecino":
        assert r.json()["detail"]["permiso_faltante"] == "invitar_usuarios_y_asignar_edificios"
    if caso == "duplicado":
        assert r.json()["campo"] == "vinculo"
