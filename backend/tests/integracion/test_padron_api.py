"""Unidades y grupos por HTTP, con identidad inyectada y RLS real."""

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event

from proptech_api.acceso import identidad_actual

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion

UNIDAD = {
    "identificador": "3A",
    "tipo": "departamento",
    "piso": "3",
    "coeficiente": "0.100000",
    "superficie_m2": "60.50",
}
GRUPO = {"clave": "ascensor", "nombre": "Ascensor", "metodo": "coeficiente", "unidades": []}


def test_alta_edicion_y_lista_de_unidades_con_informe_y_textos(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("editar")
    alta = api.cliente.post(api.ruta("/unidades"), json=UNIDAD)
    assert alta.status_code == 201
    id_ = UUID(alta.json()["id"])
    assert {k: alta.json()[k] for k in UNIDAD} == UNIDAD
    edicion = api.cliente.patch(f"/api/unidades/{id_}", json={"coeficiente": "0.2", "piso": "4"})
    assert edicion.status_code == 200
    assert edicion.json()["coeficiente"] == "0.200000"
    assert edicion.json()["piso"] == "4"
    assert edicion.json()["superficie_m2"] == "60.50"
    padron = api.cliente.get(api.ruta("/unidades"))
    assert padron.status_code == 200
    assert len(padron.json()["unidades"]) == 3
    assert padron.json()["informe"] == {
        "suma": "1.200000",
        "diferencia": "0.200000",
        "estado": "fuera_de_tolerancia",
    }
    repetida = api.cliente.post(api.ruta("/unidades"), json=UNIDAD)
    assert repetida.status_code == 409
    assert repetida.json() == {"detail": "conflicto", "campo": "identificador"}


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("coeficiente", 0.123456),
        ("superficie_m2", 65.43),
        ("coeficiente", "0"),
        ("coeficiente", "-0.1"),
        ("coeficiente", "1.000001"),
        ("coeficiente", "0.1234567"),
        ("coeficiente", "0.1\n"),
        ("coeficiente", "\u0660.\u0661"),
        ("coeficiente", " 0.1"),
        ("coeficiente", "0.1\t"),
        ("superficie_m2", "0"),
        ("superficie_m2", "60.5\n"),
        ("tipo", "quincho"),
        ("administracion_id", "MARCADOR_ADMIN"),
        ("complejo_id", "MARCADOR_EDIFICIO"),
    ],
)
def test_cuerpo_invalido_precede_404_y_403_sin_devolver_valor(
    api_edificio: ApiEdificio, campo: str, valor: Any
) -> None:
    api = api_edificio
    api.como("ver")
    if campo == "administracion_id":
        valor = str(api.admin_ajena)
    elif campo == "complejo_id":
        valor = str(api.ajeno)
    antes = api.filas("SELECT id, coeficiente, superficie_m2 FROM unidad ORDER BY id")
    for id_ in (api.edificio, api.otro, api.ajeno, uuid4()):
        respuesta = api.cliente.post(
            f"/api/complejos/{id_}/unidades", json={**UNIDAD, campo: valor}
        )
        assert respuesta.status_code == 422
        assert campo in [e["loc"][-1] for e in respuesta.json()["detail"]]
        assert all("input" not in e and "ctx" not in e for e in respuesta.json()["detail"])
        assert str(valor) not in respuesta.text
    assert api.filas("SELECT id, coeficiente, superficie_m2 FROM unidad ORDER BY id") == antes


@pytest.mark.parametrize("campo", ["administracion_id", "complejo_id", "id"])
def test_patch_no_mueve_la_unidad_ni_acepta_ids(api_edificio: ApiEdificio, campo: str) -> None:
    api = api_edificio
    respuesta = api.cliente.patch(f"/api/unidades/{api.unidad}", json={campo: str(api.ajeno)})
    assert respuesta.status_code == 422
    assert str(api.ajeno) not in respuesta.text
    assert ["body", campo] in [e["loc"] for e in respuesta.json()["detail"]]
    assert api.filas("SELECT complejo_id FROM unidad WHERE id=%s", (api.unidad,)) == [
        (api.edificio,)
    ]


@pytest.mark.parametrize("rol", ["consejo", "ver"])
def test_consejo_y_auxiliar_leen_padron_y_no_escriben(api_edificio: ApiEdificio, rol: str) -> None:
    api = api_edificio
    api.como(rol)
    for sufijo in ("/unidades", "/grupos"):
        assert api.cliente.get(api.ruta(sufijo)).status_code == 200
    for metodo, ruta, cuerpo in (
        ("POST", api.ruta("/unidades"), UNIDAD),
        ("PATCH", f"/api/unidades/{api.unidad}", {"piso": "9"}),
        ("POST", api.ruta("/grupos"), GRUPO),
    ):
        respuesta = api.cliente.request(metodo, ruta, json=cuerpo)
        assert respuesta.status_code == 403
        assert respuesta.json()["detail"]["permiso_faltante"] == "configurar_padron"
    assert api.filas("SELECT piso FROM unidad WHERE id=%s", (api.unidad,)) == [("1",)]


def test_vecino_lee_solo_su_unidad_completa_no_padron_ni_grupos(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("vecino")
    propia = api.cliente.get(f"/api/unidades/{api.unidad}")
    assert propia.status_code == 200
    assert propia.json() == {
        "id": str(api.unidad),
        "administracion_id": str(api.admin),
        "complejo_id": str(api.edificio),
        "identificador": "1A",
        "tipo": "departamento",
        "piso": "1",
        "coeficiente": "0.500000",
        "superficie_m2": "60.00",
    }
    for sufijo in ("/unidades", "/grupos"):
        rechazo = api.cliente.get(api.ruta(sufijo))
        assert rechazo.status_code == 403
        assert rechazo.json()["detail"]["permiso_faltante"] == "ver_configuracion_del_edificio"
        assert api.cliente.get(f"/api/complejos/{api.otro}{sufijo}").status_code == 404


def test_grupo_alta_edicion_y_reemplazo_atomico_de_modo_y_miembros(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    api.como("editar")
    alta = api.cliente.post(
        api.ruta("/grupos"), json={**GRUPO, "unidades": [{"unidad_id": str(api.unidad)}]}
    )
    assert alta.status_code == 201
    id_ = UUID(alta.json()["id"])
    grupos = api.cliente.get(api.ruta("/grupos"))
    assert grupos.status_code == 200
    generales, ascensor = grupos.json()
    assert generales["es_generales"] is True
    assert len(generales["unidades"]) == 2
    assert ascensor["modo_de_coeficientes"] == "renormalizado"
    assert ascensor["informe"] is None
    assert ascensor["unidades"] == [{"unidad_id": str(api.unidad), "coeficiente": None}]
    assert (
        api.cliente.patch(f"/api/grupos/{id_}", json={"nombre": "Ascensor nuevo"}).status_code
        == 200
    )
    nuevos = {
        "modo_de_coeficientes": "propios",
        "unidades": [{"unidad_id": str(api.unidad), "coeficiente": "0.9999"}],
    }
    assert api.cliente.put(f"/api/grupos/{id_}/unidades", json=nuevos).status_code == 200
    grupo = api.cliente.get(api.ruta("/grupos")).json()[1]
    assert grupo["nombre"] == "Ascensor nuevo"
    assert grupo["modo_de_coeficientes"] == "propios"
    assert grupo["unidades"] == [{"unidad_id": str(api.unidad), "coeficiente": "0.999900"}]
    assert grupo["informe"] == {
        "suma": "0.999900",
        "diferencia": "-0.000100",
        "estado": "advertencia",
    }
    conflicto = api.cliente.post(api.ruta("/grupos"), json=GRUPO)
    assert conflicto.status_code == 409
    assert conflicto.json() == {"detail": "conflicto", "campo": "clave"}


def test_miembros_ajenos_o_de_otro_edificio_dan_el_mismo_422_y_no_escriben(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    respuestas = []
    for unidad in (api.otra_unidad, api.unidad_ajena):
        respuesta = api.cliente.post(
            api.ruta("/grupos"), json={**GRUPO, "unidades": [{"unidad_id": str(unidad)}]}
        )
        assert respuesta.status_code == 422
        assert str(unidad) not in respuesta.text
        assert ["body", "unidades"] in [e["loc"] for e in respuesta.json()["detail"]]
        respuestas.append(respuesta.json())
    assert respuestas[0] == respuestas[1]
    assert api.filas(
        "SELECT clave FROM grupo_de_reparto WHERE complejo_id=%s", (api.edificio,)
    ) == [("generales",)]


@pytest.mark.parametrize("propios,coeficiente", [(True, None), (False, "0.5")])
def test_modo_y_coeficientes_incoherentes_dan_422(
    api_edificio: ApiEdificio, propios: bool, coeficiente: str | None
) -> None:
    api = api_edificio
    respuesta = api.cliente.post(
        api.ruta("/grupos"),
        json={
            **GRUPO,
            "modo_de_coeficientes": "propios" if propios else "renormalizado",
            "unidades": [{"unidad_id": str(api.unidad), "coeficiente": coeficiente}],
        },
    )
    assert respuesta.status_code == 422
    assert ["body", "unidades"] in [e["loc"] for e in respuesta.json()["detail"]]


def test_generales_no_se_edita_y_los_duplicados_dan_409(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    general = api.filas("SELECT id FROM grupo_de_reparto WHERE complejo_id=%s", (api.edificio,))[0][
        0
    ]
    respuesta = api.cliente.patch(f"/api/grupos/{general}", json={"metodo": "partes_iguales"})
    assert respuesta.status_code == 422
    assert (
        api.cliente.put(
            f"/api/grupos/{general}/unidades",
            json={"modo_de_coeficientes": "renormalizado", "unidades": []},
        ).status_code
        == 422
    )
    duplicado = api.cliente.post(
        api.ruta("/grupos"), json={**GRUPO, "unidades": [{"unidad_id": str(api.unidad)}] * 2}
    )
    assert duplicado.status_code == 409
    assert duplicado.json() == {"detail": "conflicto", "campo": "unidades"}


@pytest.mark.parametrize(
    "metodo,recurso,cuerpo",
    [
        ("GET", "complejos/{edificio}/unidades", None),
        ("GET", "complejos/{edificio}/grupos", None),
        ("POST", "complejos/{edificio}/unidades", UNIDAD),
        ("POST", "complejos/{edificio}/grupos", GRUPO),
        ("PATCH", "unidades/{unidad}", {"piso": "2"}),
        ("PATCH", "grupos/{grupo}", {"nombre": "Nuevo"}),
        (
            "PUT",
            "grupos/{grupo}/unidades",
            {"modo_de_coeficientes": "renormalizado", "unidades": []},
        ),
    ],
)
def test_recursos_fuera_de_alcance_inexistentes_y_ajenos_dan_404_identico(
    api_edificio: ApiEdificio, metodo: str, recurso: str, cuerpo: Any
) -> None:
    api = api_edificio
    grupo_otro = api.filas("SELECT id FROM grupo_de_reparto WHERE complejo_id=%s", (api.otro,))[0][
        0
    ]
    api.como("ver")
    for edificio, unidad, grupo in (
        (api.otro, api.otra_unidad, grupo_otro),
        (api.ajeno, api.unidad_ajena, api.grupo_ajeno),
        (uuid4(), uuid4(), uuid4()),
    ):
        ruta = "/api/" + recurso.format(edificio=edificio, unidad=unidad, grupo=grupo)
        respuesta = api.cliente.request(metodo, ruta, json=cuerpo)
        assert respuesta.status_code == 404
        assert respuesta.json() == {"detail": "no encontrado"}


def test_todas_las_rutas_nuevas_sin_identidad_dan_401_sin_sql(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.app.dependency_overrides.pop(identidad_actual)
    grupo = api.filas("SELECT id FROM grupo_de_reparto WHERE complejo_id=%s", (api.edificio,))[0][0]
    sentencias = []

    def registrar(*args: object) -> None:
        sentencias.append(args)

    event.listen(api.app.state.engine, "before_cursor_execute", registrar)
    try:
        for metodo, ruta, cuerpo in (
            ("GET", api.ruta("/unidades"), None),
            ("GET", api.ruta("/grupos"), None),
            ("POST", api.ruta("/unidades"), UNIDAD),
            ("POST", api.ruta("/grupos"), GRUPO),
            ("PATCH", f"/api/unidades/{api.unidad}", {"piso": "2"}),
            ("PATCH", f"/api/grupos/{grupo}", {"nombre": "Nuevo"}),
            (
                "PUT",
                f"/api/grupos/{grupo}/unidades",
                {"modo_de_coeficientes": "renormalizado", "unidades": []},
            ),
        ):
            respuesta = api.cliente.request(metodo, ruta, json=cuerpo)
            assert respuesta.status_code == 401, ruta
    finally:
        event.remove(api.app.state.engine, "before_cursor_execute", registrar)
    assert sentencias == []


def test_vecino_no_edita_unidad_ajena_del_mismo_edificio(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    unidad_del_otro_vecino = api.filas(
        "SELECT id FROM unidad WHERE complejo_id=%s AND id<>%s", (api.edificio, api.unidad)
    )[0][0]
    api.como("vecino")
    respuesta = api.cliente.patch(f"/api/unidades/{unidad_del_otro_vecino}", json={"piso": "9"})
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "no encontrado"}
