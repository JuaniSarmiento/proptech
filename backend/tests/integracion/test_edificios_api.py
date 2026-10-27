"""Contrato D6: 401 → 422 de cuerpo → 404 → 403 → conflicto/semántica."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import event

from proptech_api.acceso import identidad_actual

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion

_CONFIRMAR = "/estado-de-migracion/sin-saldos-previos"


@pytest.mark.parametrize("rol", ["super_admin", "editar", "ver", "consejo", "vecino"])
def test_lista_solo_devuelve_edificios_del_alcance(api_edificio: ApiEdificio, rol: str) -> None:
    api = api_edificio
    api.como(rol)
    respuesta = api.cliente.get("/api/complejos")
    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"id": str(id_), "nombre": nombre, "localidad": "Mendoza"}
        for id_, nombre in (
            [(api.edificio, "Edificio API"), (api.otro, "Otro edificio API")]
            if rol == "super_admin"
            else [(api.edificio, "Edificio API")]
        )
    ]


def test_ver_edificio_y_resumen_con_estado_e_informe(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    vista = api.cliente.get(api.ruta())
    assert vista.status_code == 200
    assert vista.json()["localidad"] == "Mendoza"
    resumen = api.cliente.get(api.ruta("/resumen"))
    assert resumen.status_code == 200
    assert resumen.json() == {
        "nombre": "Edificio API",
        "localidad": "Mendoza",
        "provincia_id": "50",
        "departamento_id": "50007",
        "localidad_id": "50007010",
        "calle_y_numero": None,
        "pisos": 4,
        "subsuelos": 1,
        "cantidad_unidades": 2,
        "unidades_sin_piso_completo": 0,
        "estado_migracion": "pendiente",
        "informe": {"suma": "1.000000", "diferencia": "0.000000", "estado": "ok"},
        "pasos": {
            "ubicacion": "hecho",
            "unidades": "hecho",
            "coeficientes": "hecho",
            "grupos": "hecho",
            "categorias": "hecho",
            "intereses_y_vencimiento": "hecho",
            "saldos_previos": "falta",
        },
        "listo_para_liquidar": False,
    }


def test_alta_copia_parametros_del_arranque_sin_releer_el_archivo(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    api = api_edificio
    monkeypatch.setenv("PROPTECH_PARAMETROS", "/archivo/que/no/existe")
    respuesta = api.cliente.post(
        "/api/complejos",
        json={
            "nombre": "Nuevo",
            "provincia_id": "50",
            "departamento_id": "50021",
            "localidad_id": "5002101001",
            "pisos": 4,
            "subsuelos": 1,
        },
    )
    assert respuesta.status_code == 201
    id_ = UUID(respuesta.json()["id"])
    # D2: `localidad` se escribe derivada del nombre real de Georef para el
    # departamento Godoy Cruz — nunca de un valor del pedido (que ya no
    # existe como campo).
    assert api.filas(
        "SELECT nombre, localidad, estado_migracion FROM complejo WHERE id=%s", (id_,)
    ) == [("Nuevo", "Ciudad de Godoy Cruz", "pendiente")]
    assert api.filas(
        "SELECT tasa_mensual::text FROM configuracion_versionada WHERE complejo_id=%s", (id_,)
    ) == [("3.00",)]
    assert api.filas("SELECT count(*) FROM categoria_de_gasto WHERE complejo_id=%s", (id_,)) == [
        (9,)
    ]
    assert api.filas("SELECT clave FROM grupo_de_reparto WHERE complejo_id=%s", (id_,)) == [
        ("generales",)
    ]
    assert api.filas("SELECT accion FROM auditoria WHERE entidad_id=%s", (id_,)) == [
        ("crear_edificio",)
    ]


def test_alta_con_configuracion_inicial_y_id_propio_rechazado(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    configuracion = {
        "tasa_mensual": "5.00",
        "dias_de_gracia": 0,
        "forma_de_calculo": "proporcional_por_dia",
        "porcentaje_fondo": "2.00",
        "dia_de_vencimiento": 10,
        "modalidad_de_vencimiento": "unico",
    }
    cuerpo = {
        "nombre": "Reglamento",
        "provincia_id": "50",
        "departamento_id": "50007",
        "localidad_id": "50007010",
        "pisos": 4,
        "subsuelos": 1,
        "configuracion_inicial": configuracion,
    }
    antes = api.filas("SELECT id FROM complejo ORDER BY id")
    rechazo = api.cliente.post("/api/complejos", json={**cuerpo, "id": "MARCADOR_PRIVADO"})
    assert rechazo.status_code == 422
    assert "MARCADOR_PRIVADO" not in rechazo.text
    assert ["body", "id"] in [e["loc"] for e in rechazo.json()["detail"]]
    assert api.filas("SELECT id FROM complejo ORDER BY id") == antes
    alta = api.cliente.post("/api/complejos", json=cuerpo)
    assert alta.status_code == 201
    assert api.filas(
        "SELECT tasa_mensual::text, porcentaje_fondo::text, dia_de_vencimiento "
        "FROM configuracion_versionada WHERE complejo_id=%s",
        (alta.json()["id"],),
    ) == [("5.00", "2.00", 10)]


@pytest.mark.parametrize("rol", ["editar", "ver", "consejo", "vecino"])
def test_perfiles_por_edificio_no_crean_ni_confirman_con_permiso_faltante(
    api_edificio: ApiEdificio, rol: str
) -> None:
    api = api_edificio
    api.como(rol)
    antes = api.filas("SELECT id, estado_migracion FROM complejo ORDER BY id")
    for ruta, cuerpo, permiso in (
        (
            "/api/complejos",
            {
                "nombre": "Impedido",
                "provincia_id": "50",
                "departamento_id": "50007",
                "localidad_id": "50007010",
                "pisos": 4,
                "subsuelos": 1,
            },
            "crear_edificio",
        ),
        (api.ruta(_CONFIRMAR), None, "confirmar_sin_saldos_previos"),
    ):
        respuesta = api.cliente.post(ruta, json=cuerpo)
        assert respuesta.status_code == 403
        assert respuesta.json()["detail"]["permiso_faltante"] == permiso
    assert api.filas("SELECT id, estado_migracion FROM complejo ORDER BY id") == antes


def test_confirmar_una_vez_audita_y_dos_veces_da_409_sin_volver_atras(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    primera = api.cliente.post(api.ruta(_CONFIRMAR))
    assert primera.status_code == 200
    assert api.cliente.get(api.ruta("/resumen")).json()["estado_migracion"] == "sin_saldos_previos"
    segunda = api.cliente.post(api.ruta(_CONFIRMAR))
    assert segunda.status_code == 409
    assert segunda.json() == {"detail": "conflicto", "campo": "estado_migracion"}
    for estado in ("pendiente", "confirmada"):
        # D3 (tarea 3.6): `PATCH /complejos/{id}` existe ahora, pero
        # `estado_migracion` no es un campo declarado — `extra="forbid"` lo
        # rechaza con 422 (antes de 3.6 era 405, sin ruta alguna).
        assert api.cliente.patch(api.ruta(), json={"estado_migracion": estado}).status_code == 422
        assert api.cliente.post(api.ruta(f"/estado-de-migracion/{estado}")).status_code == 404
    assert api.filas(
        "SELECT accion FROM auditoria WHERE entidad_id=%s ORDER BY id", (api.edificio,)
    ) == [("crear_edificio",), ("confirmar_sin_saldos_previos",)]


@pytest.mark.parametrize("metodo,sufijo", [("GET", ""), ("GET", "/resumen"), ("POST", _CONFIRMAR)])
def test_404_identico_para_inexistente_fuera_de_alcance_y_ajeno(
    api_edificio: ApiEdificio, metodo: str, sufijo: str
) -> None:
    api = api_edificio
    api.como("editar")
    for id_ in (uuid4(), api.otro, api.ajeno):
        respuesta = api.cliente.request(metodo, f"/api/complejos/{id_}{sufijo}")
        assert respuesta.status_code == 404
        assert respuesta.json() == {"detail": "no encontrado"}


def test_vecino_recibe_403_en_resumen_propio_y_404_en_otro(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("vecino")
    propio = api.cliente.get(api.ruta("/resumen"))
    assert propio.status_code == 403
    assert propio.json()["detail"]["permiso_faltante"] == "ver_configuracion_del_edificio"
    assert api.cliente.get(f"/api/complejos/{api.otro}/resumen").json() == {
        "detail": "no encontrado"
    }


def test_422_del_cuerpo_precede_403_y_no_refleja_valores(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("editar")
    respuesta = api.cliente.post("/api/complejos", json={"nombre": "MARCADOR_PRIVADO"})
    assert respuesta.status_code == 422
    assert "MARCADOR_PRIVADO" not in respuesta.text
    # D2 (tarea 2.6): `localidad` dejó de ser una entrada; el trío de
    # ubicación es obligatorio desde esta misma rama de validación.
    assert ["body", "provincia_id"] in [e["loc"] for e in respuesta.json()["detail"]]


@pytest.mark.parametrize(
    "metodo,ruta,cuerpo",
    [
        ("GET", "/api/complejos", None),
        ("POST", "/api/complejos", {"nombre": "Incompleto"}),
        ("GET", "/api/complejos/{id}/resumen", None),
        ("POST", "/api/complejos/{id}" + _CONFIRMAR, None),
    ],
)
def test_401_sin_sql_incluso_con_cuerpo_invalido(
    api_edificio: ApiEdificio, metodo: str, ruta: str, cuerpo: dict[str, str] | None
) -> None:
    api = api_edificio
    api.app.dependency_overrides.pop(identidad_actual)
    sentencias = []

    def registrar(*args: object) -> None:
        sentencias.append(args)

    event.listen(api.app.state.engine, "before_cursor_execute", registrar)
    try:
        respuesta = api.cliente.request(metodo, ruta.format(id=api.edificio), json=cuerpo)
    finally:
        event.remove(api.app.state.engine, "before_cursor_execute", registrar)
    assert respuesta.status_code == 401
    assert sentencias == []


@pytest.mark.parametrize(
    "calle_y_numero",
    ["A" * 201, "Alsina\u0000123"],
    ids=["demasiado_larga", "caracter_de_control"],
)
def test_calle_invalida_da_422_sin_el_valor(api_edificio: ApiEdificio, calle_y_numero: str) -> None:
    """Escenario "Calle con carácter de control o demasiado larga"."""
    api = api_edificio
    respuesta = api.cliente.post(
        "/api/complejos",
        json={
            "nombre": "Con calle inválida",
            "provincia_id": "50",
            "departamento_id": "50007",
            "localidad_id": "50007010",
            "pisos": 4,
            "subsuelos": 1,
            "calle_y_numero": calle_y_numero,
        },
    )
    assert respuesta.status_code == 422, respuesta.text
    assert calle_y_numero not in respuesta.text
    assert ["body", "calle_y_numero"] in [e["loc"] for e in respuesta.json()["detail"]]


def test_alta_sin_ubicacion_da_422(api_edificio: ApiEdificio) -> None:
    """Escenario "Alta sin ubicación": el edificio no se crea."""
    api = api_edificio
    antes = api.filas("SELECT id FROM complejo ORDER BY id")
    respuesta = api.cliente.post("/api/complejos", json={"nombre": "Sin ubicación"})
    assert respuesta.status_code == 422, respuesta.text
    assert ["body", "provincia_id"] in [e["loc"] for e in respuesta.json()["detail"]]
    assert api.filas("SELECT id FROM complejo ORDER BY id") == antes
