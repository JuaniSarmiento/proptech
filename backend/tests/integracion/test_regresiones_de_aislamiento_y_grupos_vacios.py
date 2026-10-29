"""Intentos SIN hallazgo, guardados como test para que el comando que los
respalda sea reproducible (pedido del auditor sobre la vuelta 1). Todos
pasan hoy: si alguno se pone rojo, es una regresión."""

from uuid import uuid4

import pytest

from proptech_api.acceso import identidad_actual
from proptech_core.acceso.dominio.identidad import Identidad

from ._api_edificios import ApiEdificio
from .test_rutas_protegidas import _RUTAS_CUBIERTAS, _RUTAS_SIN_ALCANCE

pytestmark = pytest.mark.integracion

_CUERPOS = {
    "/api/complejos/{complejo_id}/correcciones": {
        "forma": "contra_asiento",
        "operacion_id": str(uuid4()),
        "movimiento_id": str(uuid4()),
        "motivo": "Prueba ficticia de aislamiento",
    },
    "/api/complejos/{complejo_id}/unidades": {
        "identificador": "Z9",
        "tipo": "departamento",
        "piso": "1",
        "coeficiente": "0.100000",
        "superficie_m2": "60.00",
    },
    "/api/unidades/{unidad_id}": {"piso": "9"},
    "/api/complejos/{complejo_id}": {"nombre": "X"},
    "/api/complejos/{complejo_id}/grupos": {"clave": "x", "nombre": "X", "metodo": "coeficiente"},
    "/api/grupos/{grupo_id}": {"nombre": "X"},
    "/api/grupos/{grupo_id}/unidades": {"modo_de_coeficientes": "renormalizado", "unidades": []},
    "/api/complejos/{complejo_id}/categorias": {"clave": "x", "nombre": "X"},
    "/api/categorias/{categoria_id}": {"nombre": "X"},
    "/api/complejos/{complejo_id}/categorias/orden": {"orden": []},
    "/api/complejos/{complejo_id}/configuracion/versiones": {
        "vigente_desde": "2099-01-01",
        "tasa_mensual": "4.00",
        "dias_de_gracia": 0,
        "forma_de_calculo": "proporcional_por_dia",
        "porcentaje_fondo": "2.00",
        "dia_de_vencimiento": 10,
        "modalidad_de_vencimiento": "unico",
    },
    # Cambio 6 `gastos-y-cargos`: 404 de aislamiento llega ANTES de tocar
    # ningún recurso (D7), así que estos cuerpos sólo necesitan ser válidos
    # para pydantic, nunca referenciar filas reales.
    "/api/complejos/{complejo_id}/proveedores": {"razon_social": "X", "cuit": "20123456786"},
    "/api/proveedores/{proveedor_id}": {},
    "/api/complejos/{complejo_id}/gastos": {
        "concepto": "X",
        "categoria_id": str(uuid4()),
        "grupo_id": str(uuid4()),
        "periodo": "2026-10-01",
        "importe": "100.00",
    },
    "/api/gastos/{gasto_id}": {},
    "/api/notas-de-credito": {
        "gasto_id": str(uuid4()),
        "importe": "100.00",
        "periodo": "2026-10-01",
        "cuit_emisor": "20123456786",
        "punto_de_venta": "0001",
        "tipo_de_comprobante": "nota_de_credito_a",
        "numero_de_comprobante": "1",
    },
    "/api/complejos/{complejo_id}/cargos-particulares": {
        "unidad_id": str(uuid4()),
        "concepto": "X",
        "importe": "100.00",
        "periodo": "2026-10-01",
        "motivo": "x",
    },
    "/api/cargos-particulares/{cargo_id}": {},
}


#: Rutas de la segunda guarda del 2b (`token_de_sesion_actual`, D3 y RB2b-2): no
#: reciben una identidad con persona, así que el override de `identidad_actual`
#: no aplica y no tienen un recurso de A que alcanzar. Su aislamiento lo prueban
#: (RB2b-post-4) `test_aceptar_invitacion_api.py::
#: test_identidad_con_persona_en_b_y_otro_email_no_acepta_el_sobre_de_a` y
#: `test_sesion_api.py::test_identidad_vinculada_solo_a_b_no_muestra_nada_de_a`.
_RUTAS_CON_TOKEN_SIN_PERSONA = frozenset({"/api/sesion", "/api/invitaciones/aceptar"})


def test_super_admin_de_otra_administracion_no_alcanza_nada_de_a(api_edificio: ApiEdificio) -> None:
    """Frente 1, tercer caso: identidad válida de B (super_admin, con su fila en
    `asignacion_rol`) contra cada ruta con ids de A. Nunca 2xx; y la lista
    de edificios de B no trae los de A."""
    api = api_edificio
    persona_b = uuid4()
    with api.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api.admin_ajena),)
        )
        conexion.execute(
            "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'B')",
            (persona_b, api.admin_ajena),
        )
        conexion.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
            "VALUES (%s, %s, 'super_admin')",
            (api.admin_ajena, persona_b),
        )
    grupo_a = api.filas(
        "SELECT id FROM grupo_de_reparto WHERE complejo_id = %s AND NOT es_generales "
        "UNION ALL SELECT id FROM grupo_de_reparto WHERE complejo_id = %s LIMIT 1",
        (api.edificio, api.edificio),
    )[0][0]
    categoria_a = api.filas(
        "SELECT id FROM categoria_de_gasto WHERE complejo_id = %s LIMIT 1", (api.edificio,)
    )[0][0]
    antes = api.filas("SELECT count(*) FROM unidad")[0][0]
    api.app.dependency_overrides[identidad_actual] = lambda: Identidad(api.admin_ajena, persona_b)
    fallas = []
    for ruta, metodo in sorted(_RUTAS_CUBIERTAS):
        if ruta == "/api/complejos":
            continue
        if (ruta, metodo) in _RUTAS_SIN_ALCANCE:
            # D1: datos del país, no del edificio — cualquier identidad
            # autenticada los lee igual, sin que importe la administración.
            continue
        if ruta in _RUTAS_CON_TOKEN_SIN_PERSONA:
            continue
        if (ruta, metodo) in {("/api/personal", "GET"), ("/api/sesion/ingreso", "POST")}:
            # Alcance propio de la sesión (B), sin ids de A en la ruta: el personal se
            # comprueba abajo (que no traiga a nadie de A); el ingreso registra el de B.
            continue
        resuelta = ruta.format(
            complejo_id=api.edificio,
            unidad_id=api.unidad,
            grupo_id=grupo_a,
            categoria_id=categoria_a,
            invitacion_id=uuid4(),
            asignacion_id=uuid4(),
            provincia_id="50",
            departamento_id="50007",
            # Cambio 6 `gastos-y-cargos`: mismo patrón, no hacen falta filas reales.
            proveedor_id=uuid4(),
            gasto_id=uuid4(),
            nota_id=uuid4(),
            cargo_id=uuid4(),
            periodo="2026-10-01",
        )
        cuerpo = _CUERPOS.get(ruta, {"persona_id": str(persona_b), "rol": "consejo"})
        if ruta == "/api/personal/invitaciones":
            # Invitar a alguien con alcance en un edificio de A: tiene que dar 404.
            cuerpo = {
                "nombre": "Ajena",
                "email": "ajena@ejemplo.test",
                "rol": "administrador",
                "alcance": "edificio",
                "complejo_id": str(api.edificio),
            }
        if ruta == "/api/complejos/{complejo_id}/cargos-particulares/importar":
            # Cambio 6: multipart + query, no JSON — mismo motivo que
            # `test_cargos_particulares.py` (D6, el puerto nunca es JSON).
            respuesta = api.cliente.post(
                resuelta,
                params={"periodo": "2026-10-01"},
                files={"archivo": ("x.xlsx", b"x", "application/octet-stream")},
            )
        else:
            respuesta = api.cliente.request(
                metodo, resuelta, json=None if metodo == "GET" or "sin-saldos" in ruta else cuerpo
            )
        if respuesta.status_code != 404:
            fallas.append((metodo, ruta, respuesta.status_code, respuesta.text[:120]))
    lista = api.cliente.get("/api/complejos")
    assert lista.status_code == 200
    assert {str(api.edificio), str(api.otro)}.isdisjoint({e["id"] for e in lista.json()})
    personal = api.cliente.get("/api/personal")
    assert personal.status_code == 200
    personas_de_a = {
        str(f[0])
        for f in api.filas("SELECT id FROM persona WHERE administracion_id = %s", (api.admin,))
    }
    assert personas_de_a, "el escenario tiene que tener personas en A"
    assert personas_de_a.isdisjoint({p["persona_id"] for p in personal.json()})
    assert api.filas("SELECT count(*) FROM unidad")[0][0] == antes
    assert not fallas, fallas


def test_grupo_propios_sin_miembros_no_rompe_la_lista(api_edificio: ApiEdificio) -> None:
    """a64172f: el arreglo del IN vacío. Grupo `propios` vacío, y después
    vaciar uno con miembros; la lista de grupos sigue respondiendo 200."""
    api = api_edificio
    api.como("super_admin")
    alta = api.cliente.post(
        api.ruta("/grupos"),
        json={
            "clave": "vacio",
            "nombre": "Vacío",
            "metodo": "coeficiente",
            "modo_de_coeficientes": "propios",
            "unidades": [],
        },
    )
    assert alta.status_code == 201, alta.text
    con_uno = api.cliente.post(
        api.ruta("/grupos"),
        json={
            "clave": "uno",
            "nombre": "Uno",
            "metodo": "coeficiente",
            "unidades": [{"unidad_id": str(api.unidad)}],
        },
    )
    assert con_uno.status_code == 201, con_uno.text
    vaciar = api.cliente.put(
        f"/api/grupos/{con_uno.json()['id']}/unidades",
        json={"modo_de_coeficientes": "renormalizado", "unidades": []},
    )
    assert vaciar.status_code == 200, vaciar.text
    lista = api.cliente.get(api.ruta("/grupos"))
    assert lista.status_code == 200, lista.text
    vacio = next(g for g in lista.json() if g["clave"] == "vacio")
    assert vacio["unidades"] == []
