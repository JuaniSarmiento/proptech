"""D9: eventos separados y diferencias normalizadas del padrón."""

from typing import Any

import pytest

from ._api_edificios import ApiEdificio
from .test_auditoria_unidades_padron import alta

pytestmark = pytest.mark.integracion


def grupo(api: ApiEdificio, miembros: list[dict[str, str]], modo: str = "propios") -> str:
    r = api.cliente.post(
        api.ruta("/grupos"),
        json={
            "clave": "auditado",
            "nombre": "Privado",
            "metodo": "coeficiente",
            "modo_de_coeficientes": modo,
            "unidades": miembros,
        },
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def eventos(api: ApiEdificio, evento: str, entidad: str) -> list[Any]:
    return api.filas(
        "SELECT detalle,persona_id,request_id FROM auditoria WHERE accion=%s AND entidad_id=%s",
        (evento, entidad),
    )


def test_grupo_coeficientes_y_no_op(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    a, b, c = [alta(api, identificador=f"Nueva {i}") for i in range(3)]
    g = grupo(api, [{"unidad_id": a, "coeficiente": "0.4"}, {"unidad_id": b, "coeficiente": "0.6"}])
    creados = eventos(api, "crear_grupo", g)
    assert len(creados) == 1
    assert creados[0][0]["coeficientes"] == sorted(
        [
            {"unidad_id": a, "anterior": None, "nuevo": "0.400000"},
            {"unidad_id": b, "anterior": None, "nuevo": "0.600000"},
        ],
        key=str,
    )
    cuerpo: dict[str, Any] = {
        "modo_de_coeficientes": "propios",
        "unidades": [
            {"unidad_id": b, "coeficiente": "0.600000"},
            {"unidad_id": a, "coeficiente": "0.400000"},
        ],
    }
    assert api.cliente.put(f"/api/grupos/{g}/unidades", json=cuerpo).status_code == 200
    assert eventos(api, "fijar_unidades", g) == []
    cuerpo["unidades"] = [
        {"unidad_id": a, "coeficiente": "0.3"},
        {"unidad_id": c, "coeficiente": "0.7"},
    ]
    assert api.cliente.put(f"/api/grupos/{g}/unidades", json=cuerpo).status_code == 200
    registros = eventos(api, "fijar_unidades", g)
    assert len(registros) == 1
    assert registros[0][0] == {
        "complejo_id": str(api.edificio),
        "campos": ["unidades"],
        "coeficientes": sorted(
            [
                {"unidad_id": a, "anterior": "0.400000", "nuevo": "0.300000"},
                {"unidad_id": b, "anterior": "0.600000", "nuevo": None},
                {"unidad_id": c, "anterior": None, "nuevo": "0.700000"},
            ],
            key=str,
        ),
    }
    assert registros[0][1] == api.personas["super_admin"]


def test_siete_eventos_y_solo_nombres(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    uid = alta(api)
    assert api.cliente.patch(f"/api/unidades/{uid}", json={"piso": "Privado"}).status_code == 200
    g = grupo(api, [], modo="renormalizado")
    assert api.cliente.patch(f"/api/grupos/{g}", json={"nombre": "Otro privado"}).status_code == 200
    assert (
        api.cliente.put(
            f"/api/grupos/{g}/unidades",
            json={"modo_de_coeficientes": "renormalizado", "unidades": [{"unidad_id": uid}]},
        ).status_code
        == 200
    )
    cats = api.cliente.get(api.ruta("/categorias")).json()
    cid = cats[0]["id"]
    assert (
        api.cliente.patch(
            f"/api/categorias/{cid}", json={"nombre": "Nombre privado", "activa": False}
        ).status_code
        == 200
    )
    orden = [c["id"] for c in reversed(cats)]
    assert api.cliente.put(api.ruta("/categorias/orden"), json={"orden": orden}).status_code == 200
    esperado = {
        "crear_unidad",
        "editar_unidad",
        "crear_grupo",
        "editar_grupo",
        "fijar_unidades",
        "editar_categoria",
        "reordenar_categorias",
    }
    filas = api.filas(
        "SELECT accion, detalle FROM auditoria WHERE accion = ANY(%s)", (list(esperado),)
    )
    assert len(filas) == 7
    assert {f[0] for f in filas} == esperado
    for evento, entidad in [
        ("editar_grupo", g),
        ("editar_categoria", cid),
        ("reordenar_categorias", str(api.edificio)),
    ]:
        registro = eventos(api, evento, entidad)
        assert len(registro) == 1
        assert set(registro[0][0]) == {"complejo_id", "campos"}
        assert "privado" not in str(registro[0][0])
    # Repetir exactamente las entradas no agrega eventos.
    assert api.cliente.patch(f"/api/grupos/{g}", json={"nombre": "Otro privado"}).status_code == 200
    assert (
        api.cliente.patch(
            f"/api/categorias/{cid}", json={"nombre": "Nombre privado", "activa": False}
        ).status_code
        == 200
    )
    assert api.cliente.put(api.ruta("/categorias/orden"), json={"orden": orden}).status_code == 200
    assert (
        len(api.filas("SELECT accion FROM auditoria WHERE accion = ANY(%s)", (list(esperado),)))
        == 7
    )
