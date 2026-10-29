"""Bloque 6 de `gastos-y-cargos`: la marca de gasto mensual obligatorio
(D7, P37 resuelta en D-132) y su consulta de faltantes."""

from uuid import uuid4

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


def _marcar_obligatoria(api_edificio: ApiEdificio, categoria_id: str) -> None:
    """D7: no se construyó edición por API (igual que `complejo.cuit` en
    3.10) — se fija por SQL directo, como el resto de los campos de
    `categoria_de_gasto` que todavía no tienen su propio PATCH."""
    with api_edificio.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_edificio.admin),)
        )
        conexion.execute(
            "UPDATE categoria_de_gasto SET obligatorio_mensual = true WHERE id = %s",
            (categoria_id,),
        )


def _categoria(api_edificio: ApiEdificio, nombre: str | None = None) -> str:
    api_edificio.como("super_admin")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/categorias"), json={"nombre": nombre or f"Cat {uuid4().hex[:8]}"}
    )
    return str(respuesta.json()["id"])


def _grupo(api_edificio: ApiEdificio) -> str:
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/grupos"),
        json={"nombre": f"Grupo {uuid4().hex[:8]}", "metodo": "coeficiente", "unidades": []},
    )
    return str(respuesta.json()["id"])


def test_falta_un_obligatorio_sin_gasto_aprobado(api_edificio: ApiEdificio) -> None:
    categoria = _categoria(api_edificio, "Sueldo del encargado")
    _marcar_obligatoria(api_edificio, categoria)
    api_edificio.como("super_admin")
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/obligatorios-faltantes")
    ).json()
    assert [f["id"] for f in lectura["faltantes"]] == [categoria]
    assert lectura["faltantes"][0]["nombre"] == "Sueldo del encargado"


def test_obligatorio_cubierto_no_figura(api_edificio: ApiEdificio) -> None:
    categoria = _categoria(api_edificio, "Sueldo del encargado")
    _marcar_obligatoria(api_edificio, categoria)
    grupo = _grupo(api_edificio)
    api_edificio.como("editar")
    gasto = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": "Sueldo de octubre",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": "2026-10-01",
            "importe": "500000.00",
        },
    ).json()["id"]
    api_edificio.cliente.post(f"/api/gastos/{gasto}/aprobar")
    api_edificio.como("super_admin")
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/obligatorios-faltantes")
    ).json()
    assert lectura["faltantes"] == []


def test_gasto_en_borrador_no_cubre_el_obligatorio(api_edificio: ApiEdificio) -> None:
    categoria = _categoria(api_edificio, "Sueldo del encargado")
    _marcar_obligatoria(api_edificio, categoria)
    grupo = _grupo(api_edificio)
    api_edificio.como("editar")
    api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": "Sueldo de octubre",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": "2026-10-01",
            "importe": "500000.00",
        },
    )
    api_edificio.como("super_admin")
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/obligatorios-faltantes")
    ).json()
    assert [f["id"] for f in lectura["faltantes"]] == [categoria]


def test_edificio_sin_obligatorios_devuelve_lista_vacia(api_edificio: ApiEdificio) -> None:
    _categoria(api_edificio)  # categoría normal, nunca marcada
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/obligatorios-faltantes")
    ).json()
    assert lectura["faltantes"] == []


def test_la_consulta_no_bloquea_ninguna_operacion(api_edificio: ApiEdificio) -> None:
    #: Estructural (L-016): es una lectura (`GET`), sin ningún efecto en la
    #: carga/aprobación de gastos — se verifica llamándola y confirmando que
    #: el alta y la aprobación de un gasto en ese mismo período siguen
    #: funcionando igual, antes y después de consultarla.
    categoria = _categoria(api_edificio, "Sueldo del encargado")
    _marcar_obligatoria(api_edificio, categoria)
    grupo = _grupo(api_edificio)
    api_edificio.como("super_admin")
    api_edificio.cliente.get(api_edificio.ruta("/periodos/2026-10-01/obligatorios-faltantes"))
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": "Sueldo de octubre",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": "2026-10-01",
            "importe": "500000.00",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    aprobacion = api_edificio.cliente.post(f"/api/gastos/{respuesta.json()['id']}/aprobar")
    assert aprobacion.status_code == 200, aprobacion.text
