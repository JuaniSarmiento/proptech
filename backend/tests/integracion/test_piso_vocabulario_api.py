"""D3 (tarea 3.3): el piso de una unidad se valida contra el vocabulario DEL
EDIFICIO (`PB`, `SS1..SS<subsuelos>`, `1..<pisos>`), no sólo contra la forma
que el `CHECK` de la base puede expresar. El edificio del fixture
`api_edificio` tiene 4 pisos y 1 subsuelo (`conftest.py`)."""

from sqlalchemy import text

from ._api_edificios import ApiEdificio

UNIDAD = {
    "identificador": "9Z",
    "tipo": "departamento",
    "piso": "3",
    "coeficiente": "0.100000",
    "superficie_m2": "60.50",
}


def test_piso_que_el_edificio_no_tiene_da_422_sin_el_valor(api_edificio: ApiEdificio) -> None:
    """Escenario "Piso que el edificio no tiene": el edificio tiene 4 pisos y
    1 subsuelo; "5", "SS2" y "0" no están en su vocabulario."""
    api_edificio.como("editar")
    for piso in ("5", "SS2", "0"):
        respuesta = api_edificio.cliente.post(
            api_edificio.ruta("/unidades"), json={**UNIDAD, "piso": piso}
        )
        assert respuesta.status_code == 422
        cuerpo = respuesta.json()
        assert cuerpo["detail"][0]["loc"] == ["body", "piso"]
        assert piso not in str(cuerpo)


def test_piso_como_texto_libre_da_422(api_edificio: ApiEdificio) -> None:
    """Escenario "Piso como texto libre"."""
    api_edificio.como("editar")
    for piso in ("Entrepiso", "pb", " 1", "1°", "SS", "١"):
        respuesta = api_edificio.cliente.post(
            api_edificio.ruta("/unidades"), json={**UNIDAD, "piso": piso}
        )
        assert respuesta.status_code == 422
        assert respuesta.json()["detail"][0]["loc"] == ["body", "piso"]


def test_unidad_nueva_sin_piso_da_422(api_edificio: ApiEdificio) -> None:
    """Escenario "Unidad nueva sin piso": falta o viene en `null`."""
    api_edificio.como("editar")
    sin_piso = {k: v for k, v in UNIDAD.items() if k != "piso"}
    respuesta = api_edificio.cliente.post(api_edificio.ruta("/unidades"), json=sin_piso)
    assert respuesta.status_code == 422

    con_null = {**UNIDAD, "piso": None}
    respuesta = api_edificio.cliente.post(api_edificio.ruta("/unidades"), json=con_null)
    assert respuesta.status_code == 422


def test_piso_dentro_del_vocabulario_se_acepta(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    for piso in ("PB", "SS1", "1", "4"):
        respuesta = api_edificio.cliente.post(
            api_edificio.ruta("/unidades"), json={**UNIDAD, "identificador": f"libre-{piso}", "piso": piso}
        )
        assert respuesta.status_code == 201, respuesta.json()
        assert respuesta.json()["piso"] == piso


def test_editar_piso_fuera_del_vocabulario_da_422(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    unidad_id = api_edificio.unidad
    respuesta = api_edificio.cliente.patch(
        f"/api/unidades/{unidad_id}", json={"piso": "Entrepiso"}
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"] == ["body", "piso"]


def test_el_piso_no_se_sale_del_vocabulario_por_sql(api_edificio: ApiEdificio) -> None:
    """Escenario "El piso no se sale del vocabulario por SQL": conectado
    como `proptech_app`, insertar o actualizar por SQL con un piso fuera de
    forma lo rechaza el `CHECK` de `0024`, sin pasar por la aplicación."""
    with api_edificio.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_edificio.admin),)
        )
        try:
            conexion.execute(
                "UPDATE unidad SET piso = 'Entrepiso' WHERE id = %s", (str(api_edificio.unidad),)
            )
        except Exception as error:  # noqa: BLE001
            assert "ck_unidad" in str(error).lower() or "check" in str(error).lower()
        else:
            raise AssertionError("la base aceptó un piso fuera del vocabulario por SQL")
