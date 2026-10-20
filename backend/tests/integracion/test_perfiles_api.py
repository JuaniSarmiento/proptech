"""La matriz firmada, aplicada por las rutas reales como proptech_app (D3/D4)."""

from typing import Any
from uuid import UUID, uuid4

import pytest

from ._api_edificios import ApiEdificio
from .test_configuracion_api import version

pytestmark = pytest.mark.integracion
_CONFIRMAR = "/estado-de-migracion/sin-saldos-previos"


def _asignacion(
    api: ApiEdificio,
    nombre: str,
    rol: str,
    edificio: UUID | None,
    unidad: UUID | None = None,
    vinculo: str | None = None,
) -> UUID:
    persona = api.personas.setdefault(nombre, uuid4())
    with api.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute("SELECT set_config('app.administracion_id', %s, true)", (str(api.admin),))
        conexion.execute(
            "INSERT INTO persona (id, administracion_id, nombre) "
            "VALUES (%s, %s, 'Perfil ficticio') ON CONFLICT (id) DO NOTHING",
            (persona, api.admin),
        )
        conexion.execute(
            "INSERT INTO asignacion_rol "
            "(administracion_id, persona_id, rol, complejo_id, unidad_id, vinculo) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (api.admin, persona, rol, edificio, unidad, vinculo),
        )
    return persona


@pytest.fixture
def perfiles(api_edificio: ApiEdificio) -> ApiEdificio:
    api = api_edificio
    _asignacion(api, "administrador_principal", "administrador", None)
    _asignacion(api, "contador_principal", "contador", None)
    _asignacion(api, "contador_edificio", "contador", api.edificio)
    _asignacion(api, "inquilino", "vecino", api.edificio, api.unidad, "inquilino")
    _asignacion(api, "copropietario", "vecino", api.edificio, api.unidad, "propietario")
    return api


def _auditoria(
    api: ApiEdificio, respuesta: Any, persona: UUID, accion: str, edificio: UUID
) -> None:
    assert api.filas(
        "SELECT persona_id, accion, entidad_id FROM auditoria WHERE request_id = %s",
        (respuesta.headers["X-Request-ID"],),
    ) == [(persona, accion, edificio)]


def test_administrador_edificio_crea_version_con_autor_y_auditoria_y_no_confirma(
    perfiles: ApiEdificio,
) -> None:
    api = perfiles
    api.como("editar")
    anteriores = api.cliente.get(api.ruta("/configuracion/versiones")).json()
    nueva = api.cliente.post(api.ruta("/configuracion/versiones"), json=version())
    assert nueva.status_code == 201, nueva.text
    versiones = api.cliente.get(api.ruta("/configuracion/versiones")).json()
    assert versiones[:-1] == anteriores
    assert versiones[-1]["autor_id"] == str(api.personas["editar"])
    assert versiones[-1]["tasa_mensual"] == "4.00"
    _auditoria(api, nueva, api.personas["editar"], "crear_version_de_configuracion", api.edificio)
    antes = api.filas("SELECT estado_migracion FROM complejo WHERE id = %s", (api.edificio,))
    auditoria = api.filas("SELECT count(*) FROM auditoria")
    rechazo = api.cliente.post(api.ruta(_CONFIRMAR))
    assert rechazo.status_code == 403
    assert rechazo.json()["detail"]["permiso_faltante"] == "confirmar_sin_saldos_previos"
    assert (
        api.filas("SELECT estado_migracion FROM complejo WHERE id = %s", (api.edificio,)) == antes
    )
    assert api.filas("SELECT count(*) FROM auditoria") == auditoria


def test_administrador_principal_confirma_sin_asignacion_y_no_crea_edificio(
    perfiles: ApiEdificio,
) -> None:
    api = perfiles
    api.como("administrador_principal")
    assert api.filas(
        "SELECT complejo_id FROM asignacion_rol WHERE persona_id = %s",
        (api.personas["administrador_principal"],),
    ) == [(None,)]
    ruta = f"/api/complejos/{api.otro}{_CONFIRMAR}"
    confirmada = api.cliente.post(ruta)
    assert confirmada.status_code == 200, confirmada.text
    assert confirmada.json() == {"id": str(api.otro), "estado_migracion": "sin_saldos_previos"}
    _auditoria(
        api,
        confirmada,
        api.personas["administrador_principal"],
        "confirmar_sin_saldos_previos",
        api.otro,
    )
    antes = api.filas("SELECT count(*) FROM auditoria")
    assert api.cliente.post(ruta).status_code == 409
    assert api.filas("SELECT count(*) FROM auditoria") == antes
    edificios = api.filas("SELECT id FROM complejo ORDER BY id")
    rechazo = api.cliente.post(
        "/api/complejos", json={"nombre": "Impedido", "localidad": "Mendoza"}
    )
    assert rechazo.status_code == 403
    assert rechazo.json()["detail"]["permiso_faltante"] == "crear_edificio"
    assert api.filas("SELECT id FROM complejo ORDER BY id") == edificios
    assert api.filas("SELECT count(*) FROM auditoria") == antes


@pytest.mark.parametrize("rol", ["contador_principal", "contador_edificio", "ver", "consejo"])
def test_perfiles_lectores_ven_padron_y_no_escriben(perfiles: ApiEdificio, rol: str) -> None:
    api = perfiles
    api.como(rol)
    padron = api.cliente.get(api.ruta("/unidades"))
    assert padron.status_code == 200
    assert {u["id"] for u in padron.json()["unidades"]} == {
        str(fila[0])
        for fila in api.filas("SELECT id FROM unidad WHERE complejo_id = %s", (api.edificio,))
    }
    assert padron.json()["informe"]["suma"] == "1.000000"
    antes = api.filas("SELECT id, piso FROM unidad ORDER BY id")
    cantidades = api.filas(
        "SELECT (SELECT count(*) FROM categoria_de_gasto), "
        "(SELECT count(*) FROM configuracion_versionada), (SELECT count(*) FROM auditoria)"
    )
    for metodo, ruta, cuerpo, permiso in (
        ("PATCH", f"/api/unidades/{api.unidad}", {"piso": "9"}, "configurar_padron"),
        (
            "POST",
            api.ruta("/categorias"),
            {"clave": "nueva", "nombre": "Nueva"},
            "configurar_padron",
        ),
        ("POST", api.ruta("/configuracion/versiones"), version(), "crear_version_de_configuracion"),
    ):
        respuesta = api.cliente.request(metodo, ruta, json=cuerpo)
        assert respuesta.status_code == 403, (rol, ruta, respuesta.text)
        assert respuesta.json()["detail"]["permiso_faltante"] == permiso
    assert api.filas("SELECT id, piso FROM unidad ORDER BY id") == antes
    assert (
        api.filas(
            "SELECT (SELECT count(*) FROM categoria_de_gasto), "
            "(SELECT count(*) FROM configuracion_versionada), (SELECT count(*) FROM auditoria)"
        )
        == cantidades
    )


def test_contador_principal_lista_tres_y_lee_cualquier_padron(perfiles: ApiEdificio) -> None:
    api = perfiles
    api.como("titular")
    alta = api.cliente.post("/api/complejos", json={"nombre": "Tercero", "localidad": "Mendoza"})
    assert alta.status_code == 201
    tercero = alta.json()["id"]
    api.como("contador_principal")
    lista = api.cliente.get("/api/complejos")
    assert lista.status_code == 200
    assert {e["id"] for e in lista.json()} == {str(api.edificio), str(api.otro), tercero}
    for edificio in (api.edificio, api.otro, tercero):
        assert api.cliente.get(f"/api/complejos/{edificio}/unidades").status_code == 200
    assert api.cliente.get(f"/api/unidades/{api.unidad_ajena}").status_code == 404


@pytest.mark.parametrize("rol", ["vecino", "inquilino", "copropietario"])
def test_vecinos_ven_su_unidad_y_no_la_ajena_ni_configuracion(
    perfiles: ApiEdificio, rol: str
) -> None:
    api = perfiles
    api.como(rol)
    propia = api.cliente.get(f"/api/unidades/{api.unidad}")
    assert propia.status_code == 200
    assert propia.json()["id"] == str(api.unidad)
    assert propia.json()["coeficiente"] == "0.500000"
    ajena = api.filas(
        "SELECT id FROM unidad WHERE complejo_id = %s AND id <> %s", (api.edificio, api.unidad)
    )[0][0]
    assert api.cliente.get(f"/api/unidades/{ajena}").status_code == 404
    for sufijo in ("/unidades", "/grupos", "/categorias", "/resumen", "/configuracion"):
        respuesta = api.cliente.get(api.ruta(sufijo))
        assert respuesta.status_code == 403, (rol, sufijo)
        assert respuesta.json()["detail"]["permiso_faltante"] == "ver_configuracion_del_edificio"
        assert api.cliente.get(f"/api/complejos/{api.otro}{sufijo}").status_code == 404


def test_administrador_en_a_auxiliar_en_b_no_extiende_permiso_ni_alcanza_c(
    perfiles: ApiEdificio,
) -> None:
    api = perfiles
    api.como("titular")
    alta = api.cliente.post("/api/complejos", json={"nombre": "C", "localidad": "Mendoza"})
    assert alta.status_code == 201
    c = alta.json()["id"]
    _asignacion(api, "mixto", "administrador", api.edificio)
    _asignacion(api, "mixto", "auxiliar", api.otro)
    api.como("mixto")
    lista = api.cliente.get("/api/complejos")
    assert lista.status_code == 200
    assert {e["id"] for e in lista.json()} == {str(api.edificio), str(api.otro)}
    assert api.cliente.get(api.ruta("/unidades")).status_code == 200
    assert api.cliente.get(f"/api/complejos/{api.otro}/unidades").status_code == 200
    assert api.cliente.post(api.ruta("/configuracion/versiones"), json=version()).status_code == 201
    assert (
        api.cliente.post(
            f"/api/complejos/{api.otro}/configuracion/versiones", json=version()
        ).status_code
        == 403
    )
    assert api.cliente.get(f"/api/complejos/{c}/unidades").status_code == 404
    assert (
        api.cliente.post(f"/api/complejos/{c}/configuracion/versiones", json=version()).status_code
        == 404
    )
