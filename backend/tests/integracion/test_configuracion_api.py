"""Categorías y configuración versionada: contrato D6 por HTTP real."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event

from proptech_api.acceso import identidad_actual

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion

CONFIGURACION: dict[str, Any] = {
    "tasa_mensual": "4.00",
    "dias_de_gracia": 0,
    "forma_de_calculo": "proporcional_por_dia",
    "porcentaje_fondo": "2.00",
    "dia_de_vencimiento": 10,
    "modalidad_de_vencimiento": "unico",
}


def version(**cambios: Any) -> dict[str, Any]:
    hoy = datetime.now(UTC).astimezone(ZoneInfo("America/Argentina/Mendoza")).date()
    return {**CONFIGURACION, "vigente_desde": str(hoy + timedelta(days=1)), **cambios}


def test_categorias_alta_edicion_desactivacion_reactivacion_orden_y_conflictos(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    api.como("editar")
    alta = api.cliente.post(
        api.ruta("/categorias"),
        json={"clave": "seguridad_nocturna", "nombre": "Seguridad nocturna"},
    )
    assert alta.status_code == 201
    id_ = alta.json()["id"]
    repetida = api.cliente.post(
        api.ruta("/categorias"), json={"clave": "otra", "nombre": "SEGURIDAD NOCTURNA"}
    )
    assert repetida.status_code == 409
    assert repetida.json() == {"detail": "conflicto", "campo": "nombre"}
    clave_repetida = api.cliente.post(
        api.ruta("/categorias"), json={"clave": "seguridad_nocturna", "nombre": "Otra"}
    )
    assert clave_repetida.status_code == 409
    assert clave_repetida.json()["campo"] == "clave"
    assert (
        api.cliente.patch(
            f"/api/categorias/{id_}", json={"nombre": "Vigilancia", "activa": False}
        ).status_code
        == 200
    )
    todas = api.cliente.get(api.ruta("/categorias"))
    assert todas.status_code == 200
    categoria = next(c for c in todas.json() if c["id"] == id_)
    assert categoria["nombre"] == "Vigilancia"
    assert categoria["activa"] is False
    activas = api.cliente.get(api.ruta("/categorias?solo_activas=true"))
    assert activas.status_code == 200
    assert id_ not in [c["id"] for c in activas.json()]
    assert api.cliente.patch(f"/api/categorias/{id_}", json={"activa": True}).status_code == 200
    ids = [c["id"] for c in todas.json()][::-1]
    assert api.cliente.put(api.ruta("/categorias/orden"), json={"orden": ids}).status_code == 200
    assert [c["id"] for c in api.cliente.get(api.ruta("/categorias")).json()] == ids
    for orden_invalido in (ids[:-1], [*ids, ids[0]], [*ids[:-1], str(uuid4())]):
        rechazo = api.cliente.put(api.ruta("/categorias/orden"), json={"orden": orden_invalido})
        assert rechazo.status_code == 422
        assert [c["id"] for c in api.cliente.get(api.ruta("/categorias")).json()] == ids
    assert api.filas(
        "SELECT count(*) FROM categoria_de_gasto WHERE complejo_id=%s", (api.otro,)
    ) == [(9,)]


@pytest.mark.parametrize("rol", ["editar", "ver", "consejo", "vecino"])
def test_permisos_de_categorias_y_versiones_con_cuerpos_validos(
    api_edificio: ApiEdificio, rol: str
) -> None:
    api = api_edificio
    api.como(rol)
    for sufijo in ("/categorias", "/configuracion", "/configuracion/versiones"):
        respuesta = api.cliente.get(api.ruta(sufijo))
        assert respuesta.status_code == (403 if rol == "vecino" else 200)
        if rol == "vecino":
            assert (
                respuesta.json()["detail"]["permiso_faltante"] == "ver_configuracion_del_edificio"
            )
    categoria = api.cliente.post(
        api.ruta("/categorias"),
        json={"clave": "seguridad_nocturna", "nombre": "Seguridad nocturna"},
    )
    assert categoria.status_code == (201 if rol == "editar" else 403)
    if rol != "editar":
        assert categoria.json()["detail"]["permiso_faltante"] == "configurar_padron"
    configuracion = api.cliente.post(api.ruta("/configuracion/versiones"), json=version())
    assert configuracion.status_code == (201 if rol == "editar" else 403)
    if rol != "editar":
        assert (
            configuracion.json()["detail"]["permiso_faltante"] == "crear_version_de_configuracion"
        )
    assert api.filas(
        "SELECT count(*) FROM configuracion_versionada WHERE complejo_id=%s", (api.edificio,)
    ) == [(2 if rol == "editar" else 1,)]


def test_versiones_vigente_por_fecha_y_unique_violation_traducida_a_409(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    iniciales = api.cliente.get(api.ruta("/configuracion/versiones"))
    assert iniciales.status_code == 200
    assert len(iniciales.json()) == 1
    inicial = iniciales.json()[0]
    cuerpo = version(
        modalidad_de_vencimiento="doble",
        dia_segundo_vencimiento=20,
        recargo_segundo_vencimiento="5.00",
    )
    alta = api.cliente.post(api.ruta("/configuracion/versiones"), json=cuerpo)
    assert alta.status_code == 201
    choque = api.cliente.post(api.ruta("/configuracion/versiones"), json=cuerpo)
    assert choque.status_code == 409
    assert choque.json() == {"detail": "conflicto", "campo": "vigente_desde"}
    versiones = api.cliente.get(api.ruta("/configuracion/versiones")).json()
    assert len(versiones) == 2
    assert versiones[0] == inicial
    nueva = versiones[1]
    assert nueva["autor_id"] == str(api.personas["super_admin"])
    assert nueva["autor_nombre"] == "Persona ficticia"
    assert nueva["creada_en"]
    assert nueva["tasa_mensual"] == "4.00"
    assert nueva["recargo_segundo_vencimiento"] == "5.00"
    assert nueva["dia_segundo_vencimiento"] == 20
    # `/configuracion` no trae `autor_nombre` (D5, tarea 2.2: sólo el
    # historial lo necesita); se lo descarta para comparar el resto.
    for fecha, esperada in (
        ("2000-01-01", None),
        (inicial["vigente_desde"], {k: v for k, v in inicial.items() if k != "autor_nombre"}),
        (cuerpo["vigente_desde"], {k: v for k, v in nueva.items() if k != "autor_nombre"}),
    ):
        vigente = api.cliente.get(api.ruta("/configuracion"), params={"fecha": fecha})
        assert vigente.status_code == 200
        assert vigente.json() == esperada
    assert api.filas(
        "SELECT accion FROM auditoria WHERE entidad_id=%s ORDER BY id", (api.edificio,)
    ) == [("crear_edificio",), ("crear_version_de_configuracion",)]


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("tasa_mensual", 3.5),
        ("tasa_mensual", "NaN"),
        ("tasa_mensual", "Infinity"),
        ("tasa_mensual", "10.01"),
        ("tasa_mensual", "-1.00"),
        ("porcentaje_fondo", "100.01"),
        ("recargo_segundo_vencimiento", 5.37),
        ("recargo_segundo_vencimiento", "NaN"),
        ("recargo_segundo_vencimiento", "20.01"),
        ("dia_de_vencimiento", 29),
        # pulido-2 (3d): el tope 28 vale para toda la familia de días, no sólo el 29.
        ("dia_de_vencimiento", 30),
        ("dia_de_vencimiento", 31),
        ("dia_segundo_vencimiento", 0),
        ("dia_segundo_vencimiento", 29),
        ("dia_segundo_vencimiento", 31),
        ("dia_de_vencimiento", 0),
        ("dia_de_vencimiento", "10"),
        ("dias_de_gracia", True),
        ("capitalizacion", "MARCADOR_CAPITALIZACION"),
        ("formula", "MARCADOR_FORMULA"),
    ],
)
def test_configuracion_invalida_da_422_antes_del_alcance_y_permiso_sin_valor(
    api_edificio: ApiEdificio, campo: str, valor: Any
) -> None:
    api = api_edificio
    api.como("ver")
    cuerpo = {
        **version(
            modalidad_de_vencimiento="doble",
            dia_segundo_vencimiento=20,
            recargo_segundo_vencimiento="5.00",
        ),
        campo: valor,
    }
    for edificio in (api.edificio, api.otro, api.ajeno, uuid4()):
        respuesta = api.cliente.post(
            f"/api/complejos/{edificio}/configuracion/versiones", json=cuerpo
        )
        assert respuesta.status_code == 422
        assert campo in [e["loc"][-1] for e in respuesta.json()["detail"]]
        assert all("input" not in e and "ctx" not in e for e in respuesta.json()["detail"])
        if type(valor) is not int and valor != "10":
            assert str(valor) not in respuesta.text


def test_vigencia_pasada_y_doble_incoherente_no_escriben(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    for cuerpo, campo in (
        (version(vigente_desde="2000-01-01"), "vigente_desde"),
        (version(modalidad_de_vencimiento="doble"), "dia_segundo_vencimiento"),
        (
            version(
                modalidad_de_vencimiento="doble",
                dia_segundo_vencimiento=10,
                recargo_segundo_vencimiento="5.00",
            ),
            "dia_segundo_vencimiento",
        ),
    ):
        respuesta = api.cliente.post(api.ruta("/configuracion/versiones"), json=cuerpo)
        assert respuesta.status_code == 422
        assert campo in [e["loc"][-1] for e in respuesta.json()["detail"]]
    assert api.filas(
        "SELECT count(*) FROM configuracion_versionada WHERE complejo_id=%s", (api.edificio,)
    ) == [(1,)]


def test_no_hay_borrado_de_categoria_ni_edicion_o_borrado_de_version(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    categorias = api.cliente.get(api.ruta("/categorias"))
    assert categorias.status_code == 200
    categoria = categorias.json()[0]["id"]
    versiones = api.cliente.get(api.ruta("/configuracion/versiones"))
    assert versiones.status_code == 200
    version_id = versiones.json()[0]["id"]
    assert api.cliente.delete(f"/api/categorias/{categoria}").status_code == 405
    assert api.cliente.delete(api.ruta(f"/configuracion/versiones/{version_id}")).status_code == 404
    assert (
        api.cliente.patch(
            api.ruta(f"/configuracion/versiones/{version_id}"), json={"tasa_mensual": "1.00"}
        ).status_code
        == 404
    )
    assert api.cliente.get(api.ruta("/categorias")).json() == categorias.json()
    assert api.cliente.get(api.ruta("/configuracion/versiones")).json() == versiones.json()


@pytest.mark.parametrize(
    "metodo,sufijo,cuerpo",
    [
        ("GET", "/categorias", None),
        ("POST", "/categorias", {"clave": "nueva", "nombre": "Nueva"}),
        ("PUT", "/categorias/orden", {"orden": []}),
        ("GET", "/configuracion", None),
        ("GET", "/configuracion/versiones", None),
        ("POST", "/configuracion/versiones", version()),
    ],
)
def test_404_identico_con_cuerpo_valido_y_401_sin_sql(
    api_edificio: ApiEdificio, metodo: str, sufijo: str, cuerpo: Any
) -> None:
    api = api_edificio
    api.como("ver")
    for edificio in (api.otro, api.ajeno, uuid4()):
        respuesta = api.cliente.request(metodo, f"/api/complejos/{edificio}{sufijo}", json=cuerpo)
        assert respuesta.status_code == 404
        assert respuesta.json() == {"detail": "no encontrado"}
    api.app.dependency_overrides.pop(identidad_actual)
    sentencias = []

    def registrar(*args: object) -> None:
        sentencias.append(args)

    event.listen(api.app.state.engine, "before_cursor_execute", registrar)
    try:
        respuesta = api.cliente.request(metodo, api.ruta(sufijo), json=cuerpo)
    finally:
        event.remove(api.app.state.engine, "before_cursor_execute", registrar)
    assert respuesta.status_code == 401
    assert sentencias == []


def test_patch_categoria_con_alcance_permiso_y_401_sin_sql(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    propia = api.filas(
        "SELECT id FROM categoria_de_gasto WHERE complejo_id=%s ORDER BY orden", (api.edificio,)
    )[0][0]
    otra = api.filas(
        "SELECT id FROM categoria_de_gasto WHERE complejo_id=%s ORDER BY orden", (api.otro,)
    )[0][0]
    for rol in ("ver", "consejo", "vecino"):
        api.como(rol)
        rechazo = api.cliente.patch(f"/api/categorias/{propia}", json={"activa": False})
        assert rechazo.status_code == 403
        assert rechazo.json()["detail"]["permiso_faltante"] == "configurar_padron"
    for id_ in (otra, api.categoria_ajena, uuid4()):
        rechazo = api.cliente.patch(f"/api/categorias/{id_}", json={"activa": False})
        assert rechazo.status_code == 404
        assert rechazo.json() == {"detail": "no encontrado"}
    api.app.dependency_overrides.pop(identidad_actual)
    sentencias = []

    def registrar(*args: object) -> None:
        sentencias.append(args)

    event.listen(api.app.state.engine, "before_cursor_execute", registrar)
    try:
        respuesta = api.cliente.patch(f"/api/categorias/{propia}", json={"activa": False})
    finally:
        event.remove(api.app.state.engine, "before_cursor_execute", registrar)
    assert respuesta.status_code == 401
    assert sentencias == []
