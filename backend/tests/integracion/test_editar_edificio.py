"""D3 (tareas 3.5, 3.6, 3.7): `PATCH /complejos/{id}` edita nombre,
ubicación, calle y número, pisos y subsuelos, auditado como
`editar_edificio`. El edificio del fixture `api_edificio` tiene 4 pisos y 1
subsuelo (`conftest.py`), sin unidades en ningún piso salvo las creadas en
cada test."""

from ._api_edificios import ApiEdificio


def test_corregir_la_localidad(api_edificio: ApiEdificio) -> None:
    """Escenario "Corregir la localidad": cambia sólo la localidad, a otra
    del mismo departamento (Capital, `50007`: de la localidad "Mendoza",
    `50007010`, a su "1ra Sección", `5000701001`, confirmada en
    `config/georef/localidades.json`)."""
    api_edificio.como("super_admin")
    anterior = api_edificio.cliente.get(api_edificio.ruta()).json()
    assert anterior["localidad"] == "Mendoza"
    respuesta = api_edificio.cliente.patch(
        api_edificio.ruta(), json={"localidad_id": "5000701001"}
    )
    assert respuesta.status_code == 200, respuesta.text
    edificio = api_edificio.cliente.get(api_edificio.ruta()).json()
    assert edificio["nombre"] == anterior["nombre"]
    assert edificio["localidad"] == "1ra Sección"
    assert edificio["provincia_id"] == anterior["provincia_id"]
    assert edificio["departamento_id"] == anterior["departamento_id"]
    filas = api_edificio.filas(
        "SELECT accion FROM auditoria WHERE entidad_id=%s AND accion='editar_edificio'",
        (str(api_edificio.edificio),),
    )
    assert len(filas) == 1


def test_completar_ubicacion_de_edificio_viejo(api_edificio: ApiEdificio) -> None:
    """Escenario "Completar la ubicación de un edificio viejo"."""
    api_edificio.como("super_admin")
    with api_edificio.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_edificio.admin),)
        )
        conexion.execute(
            "UPDATE complejo SET provincia_id=NULL, departamento_id=NULL, "
            "localidad_id=NULL, localidad=NULL WHERE id=%s",
            (str(api_edificio.edificio),),
        )
    respuesta = api_edificio.cliente.patch(
        api_edificio.ruta(),
        json={
            "provincia_id": "50",
            "departamento_id": "50007",
            "localidad_id": "50007010",
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    edificio = api_edificio.cliente.get(api_edificio.ruta()).json()
    assert edificio["localidad"] == "Mendoza"
    assert edificio["provincia_id"] == "50"


def test_anular_nombre_o_pisos_da_422_sin_cambios(api_edificio: ApiEdificio) -> None:
    """Escenario "Anular un campo obligatorio"."""
    api_edificio.como("super_admin")
    for cuerpo in ({"nombre": None}, {"pisos": None}):
        respuesta = api_edificio.cliente.patch(api_edificio.ruta(), json=cuerpo)
        assert respuesta.status_code == 422


def test_editar_fuera_del_alcance_da_404(api_edificio: ApiEdificio) -> None:
    """Escenario "Editar un edificio fuera del alcance": una identidad con
    alcance a `edificio` (no a `otro`) edita `otro`."""
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.patch(
        f"/api/complejos/{api_edificio.otro}", json={"nombre": "Otro nombre"}
    )
    assert respuesta.status_code == 404


def test_editar_sin_permiso_da_403(api_edificio: ApiEdificio) -> None:
    """Escenario "Editar sin permiso de configurar el padrón": un contador
    (rol "ver") no tiene `CONFIGURAR_PADRON`."""
    api_edificio.como("ver")
    respuesta = api_edificio.cliente.patch(api_edificio.ruta(), json={"nombre": "Otro nombre"})
    assert respuesta.status_code == 403


def test_cambiar_administracion_por_la_edicion_da_422(api_edificio: ApiEdificio) -> None:
    """Escenario "Cambiar la administración por la edición"."""
    api_edificio.como("super_admin")
    for cuerpo in (
        {"administracion_id": str(api_edificio.admin_ajena)},
        {"estado_migracion": "sin_saldos_previos"},
    ):
        respuesta = api_edificio.cliente.patch(api_edificio.ruta(), json=cuerpo)
        assert respuesta.status_code == 422


def test_bajar_pisos_con_unidades_arriba_da_422_con_identificadores(
    api_edificio: ApiEdificio,
) -> None:
    """Escenario "Bajar pisos con unidades arriba": el edificio tiene 4
    pisos; se crea una unidad en el piso 4 y se intenta bajar a 3."""
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/unidades"),
        json={
            "identificador": "4A-bajar",
            "tipo": "departamento",
            "piso": "4",
            "coeficiente": "0.100000",
            "superficie_m2": "60.00",
        },
    )
    assert alta.status_code == 201, alta.text
    api_edificio.como("super_admin")
    respuesta = api_edificio.cliente.patch(api_edificio.ruta(), json={"pisos": 3})
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"] == ["body", "pisos"]
    assert "4A-bajar" in str(respuesta.json())
    assert (
        api_edificio.cliente.get(api_edificio.ruta()).json()["pisos"] == 4
    )


def test_bajar_subsuelos_con_cocheras_abajo_da_422_con_identificadores(
    api_edificio: ApiEdificio,
) -> None:
    """Escenario "Bajar subsuelos con cocheras abajo": el edificio tiene 1
    subsuelo; se crea una cochera en "SS1" y se intenta bajar a 0."""
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/unidades"),
        json={
            "identificador": "SS1-bajar",
            "tipo": "cochera",
            "piso": "SS1",
            "coeficiente": "0.010000",
            "superficie_m2": "12.00",
        },
    )
    assert alta.status_code == 201, alta.text
    api_edificio.como("super_admin")
    respuesta = api_edificio.cliente.patch(api_edificio.ruta(), json={"subsuelos": 0})
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"] == ["body", "subsuelos"]
    assert "SS1-bajar" in str(respuesta.json())


def test_bajar_pisos_sin_unidades_arriba_es_exitosa(api_edificio: ApiEdificio) -> None:
    """Escenario "Bajar pisos sin unidades arriba": edificio de 4 pisos sin
    ninguna unidad en el piso 4 se edita a 3 pisos."""
    api_edificio.como("super_admin")
    respuesta = api_edificio.cliente.patch(api_edificio.ruta(), json={"pisos": 3})
    assert respuesta.status_code == 200, respuesta.text
    assert api_edificio.cliente.get(api_edificio.ruta()).json()["pisos"] == 3


def test_editar_la_ubicacion_audita_solo_los_campos(api_edificio: ApiEdificio) -> None:
    """Escenario "Editar la ubicación": localidad y calle cambian; queda
    `editar_edificio` con el edificio y los nombres de los dos campos, sin
    los valores."""
    api_edificio.como("super_admin")
    respuesta = api_edificio.cliente.patch(
        api_edificio.ruta(),
        json={"localidad_id": "5000701002", "calle_y_numero": "Alsina 123"},
    )
    assert respuesta.status_code == 200, respuesta.text
    filas = api_edificio.filas(
        "SELECT detalle FROM auditoria WHERE entidad_id=%s AND accion='editar_edificio'",
        (str(api_edificio.edificio),),
    )
    assert len(filas) == 1
    detalle = filas[0][0]
    assert detalle["complejo_id"] == str(api_edificio.edificio)
    assert sorted(detalle["campos"]) == ["calle_y_numero", "localidad_id"]
    assert "Alsina" not in str(detalle)


def test_edicion_que_falla_no_deja_auditoria(api_edificio: ApiEdificio) -> None:
    """Escenario "La edición falla": trío incoherente."""
    api_edificio.como("super_admin")
    respuesta = api_edificio.cliente.patch(
        api_edificio.ruta(),
        json={"provincia_id": "50", "departamento_id": "50021", "localidad_id": "50007010"},
    )
    assert respuesta.status_code == 422
    filas = api_edificio.filas(
        "SELECT accion FROM auditoria WHERE entidad_id=%s AND accion='editar_edificio'",
        (str(api_edificio.edificio),),
    )
    assert filas == []


def test_edicion_sin_cambios_no_deja_auditoria(api_edificio: ApiEdificio) -> None:
    """Escenario "Edición sin cambios"."""
    api_edificio.como("super_admin")
    actual = api_edificio.cliente.get(api_edificio.ruta()).json()
    respuesta = api_edificio.cliente.patch(
        api_edificio.ruta(), json={"nombre": actual["nombre"]}
    )
    assert respuesta.status_code == 200
    filas = api_edificio.filas(
        "SELECT accion FROM auditoria WHERE entidad_id=%s AND accion='editar_edificio'",
        (str(api_edificio.edificio),),
    )
    assert filas == []


def test_explain_de_la_consulta_de_unidades_fuera_de_rango(api_edificio: ApiEdificio) -> None:
    """Evidencia de la tarea 3.5: el `EXPLAIN` de la consulta que busca
    unidades fuera de rango entra por `uq_unidad_identificador`."""
    filas = api_edificio.filas(
        "EXPLAIN SELECT identificador, piso FROM unidad "
        "WHERE complejo_id=%s AND piso IS NOT NULL",
        (str(api_edificio.edificio),),
    )
    plan = "\n".join(f[0] for f in filas)
    assert "uq_unidad_identificador" in plan, plan
