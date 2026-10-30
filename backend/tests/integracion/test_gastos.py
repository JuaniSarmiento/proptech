"""Bloque 3 de `gastos-y-cargos`: el gasto y sus cuatro estados (D-075)."""

from uuid import uuid4

import psycopg
import pytest

from ._api_edificios import ApiEdificio
from ._edificios import Edificios, fijar_tenant, insertar_grupo
from .test_categorias_db import insertar_categoria

pytestmark = pytest.mark.integracion

_CUIT_A = "20123456786"


def _fijar_estado(api_edificio: ApiEdificio, gasto_id: str, estado: str) -> None:
    """`ApiEdificio.filas` espera un `SELECT` (hace `fetchall`); un `UPDATE`
    directo de prueba (sólo para forzar `sin_ia`/`en_revision`, D-078: nadie
    los produce todavía en este cambio) necesita su propia conexión."""
    with api_edificio.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_edificio.admin),)
        )
        conexion.execute("UPDATE gasto SET estado = %s WHERE id = %s", (estado, gasto_id))


def _crear_categoria_y_grupo(
    api_edificio: ApiEdificio, complejo: str | None = None
) -> tuple[str, str]:
    #: Nombre único por llamada (L-016): "Ascensor" ya existe entre las
    #: categorías que `crear_edificio` siembra desde `parametros.yaml`, y
    #: repetirlo da 409 por `uq_categoria_nombre`, no por el test.
    nombre = f"Prueba gasto {uuid4().hex[:8]}"
    ruta = f"/api/complejos/{complejo}" if complejo else api_edificio.ruta("")
    api_edificio.como("super_admin")
    categoria_resp = api_edificio.cliente.post(f"{ruta}/categorias", json={"nombre": nombre})
    assert categoria_resp.status_code == 201, categoria_resp.text
    grupo_resp = api_edificio.cliente.post(
        f"{ruta}/grupos", json={"nombre": nombre, "metodo": "coeficiente", "unidades": []}
    )
    assert grupo_resp.status_code == 201, grupo_resp.text
    return str(categoria_resp.json()["id"]), str(grupo_resp.json()["id"])


def _datos_minimos(categoria: str, grupo: str, **extra: object) -> dict[str, object]:
    base: dict[str, object] = {
        "concepto": "Service del ascensor",
        "categoria_id": categoria,
        "grupo_id": grupo,
        "periodo": "2026-10-01",
        "importe": "1000.00",
    }
    base.update(extra)
    return base


# --- 3.2: alta manual ---


def test_alta_minima_queda_en_borrador_con_importe_texto(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    assert respuesta.status_code == 201, respuesta.text
    gasto_id = respuesta.json()["id"]
    gasto = api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()
    assert gasto["estado"] == "borrador"
    assert gasto["importe"] == "1000.00"
    assert gasto["tipo"] == "ordinario"


def test_sin_categoria_da_422_y_no_crea_nada(api_edificio: ApiEdificio) -> None:
    _categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    datos = _datos_minimos("x", grupo)
    del datos["categoria_id"]
    respuesta = api_edificio.cliente.post(api_edificio.ruta("/gastos"), json=datos)
    assert respuesta.status_code == 422, respuesta.text


@pytest.mark.parametrize("importe", ["1000.001", "0.00", "-5.00"])
def test_importe_invalido_da_422(api_edificio: ApiEdificio, importe: str) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo, importe=importe)
    )
    assert respuesta.status_code == 422, respuesta.text


def test_periodo_que_no_es_primero_del_mes_da_422(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json=_datos_minimos(categoria, grupo, periodo="2026-10-15"),
    )
    assert respuesta.status_code == 422, respuesta.text


def test_grupo_desactivado_da_422(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("super_admin")
    api_edificio.cliente.patch(f"/api/grupos/{grupo}", json={"activo": False})
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    assert respuesta.status_code == 422, respuesta.text


def test_categoria_de_otro_edificio_da_422_y_sql_directo_rechazado(
    api_edificio: ApiEdificio, app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    _categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    edificio_ajeno = str(api_edificio.otro)
    categoria_ajena, _grupo_ajeno = _crear_categoria_y_grupo(api_edificio, complejo=edificio_ajeno)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria_ajena, grupo)
    )
    assert respuesta.status_code == 422, respuesta.text
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with app_edificio.transaction():
            app_edificio.execute(
                "INSERT INTO gasto (id, administracion_id, complejo_id, categoria_id, grupo_id, "
                "concepto, periodo, periodo_de_imputacion, importe) "
                "VALUES (%s, %s, %s, %s, %s, 'x', '2026-10-01', '2026-10-01', '10.00')",
                (
                    uuid4(),
                    edificios.administracion_a,
                    edificios.complejo_a,
                    uuid4(),
                    uuid4(),
                ),
            )


def test_tipo_por_defecto_es_ordinario(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    assert respuesta.json
    gasto_id = respuesta.json()["id"]
    assert api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()["tipo"] == "ordinario"


# --- 3.5: el sueldo del encargado ---


def test_sueldo_del_encargado_sin_proveedor_entra_al_aprobar(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    gasto_id = alta.json()["id"]
    assert api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()["proveedor_id"] is None
    api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert lectura["grupos"][grupo]["total"] == "1000.00"


# --- 3.6 / 3.7: los cuatro estados ---


def test_gasto_nace_en_borrador(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    gasto_id = alta.json()["id"]
    assert api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()["estado"] == "borrador"


@pytest.mark.parametrize("estado", ["borrador", "sin_ia", "en_revision"])
def test_estado_no_aprobado_no_entra_en_el_calculo(api_edificio: ApiEdificio, estado: str) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    gasto_id = alta.json()["id"]
    if estado != "borrador":
        _fijar_estado(api_edificio, gasto_id, estado)
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert lectura["grupos"] == {}
    assert lectura["total"] == "0.00"


def test_estado_desconocido_rechazado_por_sql(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    categoria_id = insertar_categoria(
        app_edificio, edificios.administracion_a, edificios.complejo_a
    )
    grupo_id = insertar_grupo(app_edificio, edificios.administracion_a, edificios.complejo_a)
    with pytest.raises(psycopg.errors.CheckViolation):
        with app_edificio.transaction():
            app_edificio.execute(
                "INSERT INTO gasto (id, administracion_id, complejo_id, categoria_id, grupo_id, "
                "concepto, periodo, periodo_de_imputacion, importe, estado) "
                "VALUES (%s, %s, %s, %s, %s, 'x', '2026-10-01', '2026-10-01', '10.00', "
                "'inventado')",
                (
                    uuid4(),
                    edificios.administracion_a,
                    edificios.complejo_a,
                    categoria_id,
                    grupo_id,
                ),
            )


def test_mutante_sin_filtro_de_estado_rompe_en_el_total(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    """3.7 — mutante obligatorio: sacar `estado='aprobado'` del `WHERE` de la
    lectura (copiando la función real y editando sólo esa cláusula, L-013)
    tiene que romper la aserción del TOTAL, no un paso anterior (L-034,
    L-049): con el gasto en `borrador` sin aprobar, el total pasa de "0.00"
    (RED de `test_estado_no_aprobado_no_entra_en_el_calculo`) a "1000.00"."""
    from sqlalchemy import text as sa_text

    from proptech_core.compartido.dinero import Dinero, sumar
    from proptech_core.gastos.aplicacion import gastos as modulo_gastos

    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    assert api_edificio.cliente.get(f"/api/gastos/{alta.json()['id']}").json()["estado"] == (
        "borrador"
    )

    def _lectura_mutada_sin_filtro_de_estado(sesion, complejo_id, periodo):  # type: ignore[no-untyped-def]
        #: Copia literal de `gastos_aprobados_del_periodo`, MENOS
        #: "AND estado='aprobado'" en el WHERE — el resto es idéntico.
        filas = (
            sesion.execute(
                sa_text(
                    "SELECT grupo_id, categoria_id, tipo, importe::text AS importe FROM gasto "
                    "WHERE complejo_id=:complejo AND periodo_de_imputacion=:periodo"
                ),
                {"complejo": complejo_id, "periodo": periodo},
            )
            .mappings()
            .all()
        )
        total = sumar(Dinero(f["importe"]) for f in filas)
        return {"periodo": periodo.isoformat(), "total": total.a_texto(), "grupos": {}}

    monkeypatch.setattr(
        modulo_gastos, "gastos_aprobados_del_periodo", _lectura_mutada_sin_filtro_de_estado
    )
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert lectura["total"] == "1000.00", (
        "el mutante tiene que sumar el borrador igual, rompiendo la aserción del total"
    )


# --- 3.8: aprobación ---


@pytest.mark.parametrize("estado_inicial", ["borrador", "sin_ia", "en_revision"])
def test_aprobacion_desde_los_tres_estados(api_edificio: ApiEdificio, estado_inicial: str) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    gasto_id = alta.json()["id"]
    if estado_inicial != "borrador":
        _fijar_estado(api_edificio, gasto_id, estado_inicial)
    respuesta = api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    assert respuesta.status_code == 200, respuesta.text
    assert api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()["estado"] == "aprobado"


def test_aprobar_dos_veces_no_duplica_ni_la_auditoria(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    gasto_id = alta.json()["id"]
    api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    filas = api_edificio.filas(
        "SELECT accion FROM auditoria WHERE entidad_id = %s AND accion = 'aprobar_gasto'",
        (gasto_id,),
    )
    assert len(filas) == 1
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert lectura["grupos"][grupo]["total"] == "1000.00"


def test_editar_importe_de_aprobado_se_rechaza(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    gasto_id = alta.json()["id"]
    api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    respuesta = api_edificio.cliente.patch(f"/api/gastos/{gasto_id}", json={"importe": "1.00"})
    assert respuesta.status_code == 422, respuesta.text
    assert api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()["importe"] == "1000.00"


def test_aprobar_sin_permiso_da_403(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    gasto_id = alta.json()["id"]
    api_edificio.como("contador")
    respuesta = api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    assert respuesta.status_code == 403, respuesta.text
    # D-131 (2d): todo 403 lleva `codigo`; sumado al integrar `main`.
    assert respuesta.json()["detail"].get("codigo") == "sin_permiso", respuesta.text
    api_edificio.como("super_admin")
    assert api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()["estado"] == "borrador"


# --- 3.9: factura y control de duplicados ---


def test_factura_duplicada_en_el_mismo_edificio_da_409(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    datos = _datos_minimos(
        categoria,
        grupo,
        cuit_emisor=_CUIT_A,
        punto_de_venta="0001",
        tipo_de_comprobante="FA",
        numero_de_comprobante="00000001",
    )
    r1 = api_edificio.cliente.post(api_edificio.ruta("/gastos"), json=datos)
    assert r1.status_code == 201, r1.text
    r2 = api_edificio.cliente.post(api_edificio.ruta("/gastos"), json=datos)
    assert r2.status_code == 409, r2.text


def test_misma_clave_en_otro_edificio_no_choca(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    edificio_otro = str(api_edificio.otro)
    categoria_otro, grupo_otro = _crear_categoria_y_grupo(api_edificio, complejo=edificio_otro)
    datos = _datos_minimos(
        categoria,
        grupo,
        cuit_emisor=_CUIT_A,
        punto_de_venta="0001",
        tipo_de_comprobante="FA",
        numero_de_comprobante="00000001",
    )
    api_edificio.como("super_admin")
    assert api_edificio.cliente.post(api_edificio.ruta("/gastos"), json=datos).status_code == 201
    datos_otro = _datos_minimos(
        categoria_otro,
        grupo_otro,
        cuit_emisor=_CUIT_A,
        punto_de_venta="0001",
        tipo_de_comprobante="FA",
        numero_de_comprobante="00000001",
    )
    respuesta = api_edificio.cliente.post(
        f"/api/complejos/{api_edificio.otro}/gastos", json=datos_otro
    )
    assert respuesta.status_code == 201, respuesta.text


def test_misma_clave_con_tipo_de_comprobante_distinto_no_es_duplicada(
    api_edificio: ApiEdificio,
) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    factura = _datos_minimos(
        categoria,
        grupo,
        cuit_emisor=_CUIT_A,
        punto_de_venta="0001",
        tipo_de_comprobante="FA",
        numero_de_comprobante="00000001",
    )
    nota = {**factura, "tipo_de_comprobante": "NC"}
    assert api_edificio.cliente.post(api_edificio.ruta("/gastos"), json=factura).status_code == 201
    assert api_edificio.cliente.post(api_edificio.ruta("/gastos"), json=nota).status_code == 201


@pytest.mark.parametrize(
    "incompletos",
    [
        {"cuit_emisor": _CUIT_A, "numero_de_comprobante": "1"},
        {"cuit_emisor": _CUIT_A, "punto_de_venta": "0001"},
        {"tipo_de_comprobante": "FA", "numero_de_comprobante": "1"},
    ],
)
def test_datos_de_factura_incompletos_dan_422(
    api_edificio: ApiEdificio, incompletos: dict[str, str]
) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo, **incompletos)
    )
    assert respuesta.status_code == 422, respuesta.text


# --- 3.10: aviso de receptor distinto (D-141-bis, decisión del 28/10/2026:
# `complejo.cuit`, nullable, migración `0031`) ---


def _fijar_cuit_del_complejo(api_edificio: ApiEdificio, cuit: str | None) -> None:
    with api_edificio.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_edificio.admin),)
        )
        conexion.execute(
            "UPDATE complejo SET cuit = %s WHERE id = %s", (cuit, api_edificio.edificio)
        )


def test_sin_cuit_del_edificio_no_hay_aviso(api_edificio: ApiEdificio) -> None:
    #: `complejo.cuit` nace NULL (migración aditiva): sin dato, nada que
    #: comparar — nunca error, nunca aviso.
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json=_datos_minimos(categoria, grupo, documento_receptor="20999999999"),
    )
    assert respuesta.status_code == 201, respuesta.text
    assert "aviso" not in respuesta.json()


def test_receptor_distinto_del_edificio_trae_aviso_y_no_bloquea(
    api_edificio: ApiEdificio,
) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    _fijar_cuit_del_complejo(api_edificio, _CUIT_A)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json=_datos_minimos(categoria, grupo, documento_receptor="20999999999"),
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert "no coincide" in cuerpo["aviso"]
    #: No bloquea: el gasto quedó creado igual.
    assert api_edificio.cliente.get(f"/api/gastos/{cuerpo['id']}").json()["estado"] == "borrador"


def test_receptor_igual_al_edificio_no_trae_aviso(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    _fijar_cuit_del_complejo(api_edificio, _CUIT_A)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json=_datos_minimos(categoria, grupo, documento_receptor=_CUIT_A),
    )
    assert respuesta.status_code == 201, respuesta.text
    assert "aviso" not in respuesta.json()


def test_sin_documento_receptor_informado_no_hay_aviso(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    _fijar_cuit_del_complejo(api_edificio, _CUIT_A)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    assert respuesta.status_code == 201, respuesta.text
    assert "aviso" not in respuesta.json()


# --- 3.11: alcance, permisos y aislamiento ---


def test_gasto_de_otro_edificio_da_404(api_edificio: ApiEdificio) -> None:
    api_edificio.como("super_admin")
    respuesta = api_edificio.cliente.get(f"/api/complejos/{api_edificio.ajeno}/gastos")
    assert respuesta.status_code == 404, respuesta.text


def test_el_consejo_lee_pero_no_escribe(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("consejo")
    lectura = api_edificio.cliente.get(api_edificio.ruta("/gastos"))
    assert lectura.status_code == 200, lectura.text
    carga = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"), json=_datos_minimos(categoria, grupo)
    )
    assert carga.status_code == 403, carga.text


def test_aislamiento_por_administracion_tambien_por_sql(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    fijar_tenant(app_edificio, edificios.administracion_b)
    categoria_id, grupo_id = uuid4(), uuid4()
    app_edificio.execute(
        "INSERT INTO categoria_de_gasto (id, administracion_id, complejo_id, clave, nombre, "
        "orden) VALUES (%s, %s, %s, 'x', 'X', 0)",
        (categoria_id, edificios.administracion_b, edificios.complejo_b),
    )
    app_edificio.execute(
        "INSERT INTO grupo_de_reparto (id, administracion_id, complejo_id, clave, nombre, "
        "metodo) VALUES (%s, %s, %s, 'x', 'X', 'partes_iguales')",
        (grupo_id, edificios.administracion_b, edificios.complejo_b),
    )
    app_edificio.execute(
        "INSERT INTO gasto (administracion_id, complejo_id, categoria_id, grupo_id, concepto, "
        "periodo, periodo_de_imputacion, importe) "
        "VALUES (%s, %s, %s, %s, 'x', '2026-10-01', '2026-10-01', '10.00')",
        (edificios.administracion_b, edificios.complejo_b, categoria_id, grupo_id),
    )
    fijar_tenant(app_edificio, edificios.administracion_a)
    assert app_edificio.execute("SELECT id FROM gasto").fetchall() == []
