"""Bloque 4 de `gastos-y-cargos`: notas de crédito (R22, D-061, D-082)."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest

from ._api_edificios import ApiEdificio
from ._edificios import Edificios, fijar_tenant

pytestmark = pytest.mark.integracion

_CUIT_A = "20123456786"


def _crear_categoria_y_grupo(
    api_edificio: ApiEdificio, complejo: str | None = None
) -> tuple[str, str]:
    nombre = f"Prueba nota {uuid4().hex[:8]}"
    ruta = f"/api/complejos/{complejo}" if complejo else api_edificio.ruta("")
    api_edificio.como("super_admin")
    categoria = api_edificio.cliente.post(f"{ruta}/categorias", json={"nombre": nombre})
    assert categoria.status_code == 201, categoria.text
    grupo = api_edificio.cliente.post(
        f"{ruta}/grupos", json={"nombre": nombre, "metodo": "coeficiente", "unidades": []}
    )
    assert grupo.status_code == 201, grupo.text
    return categoria.json()["id"], grupo.json()["id"]


def _crear_factura(
    api_edificio: ApiEdificio, categoria: str, grupo: str, importe: str = "100000.00"
) -> str:
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": "Factura de prueba",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": "2026-10-01",
            "importe": importe,
            "cuit_emisor": _CUIT_A,
            "punto_de_venta": "0001",
            "tipo_de_comprobante": "FA",
            "numero_de_comprobante": uuid4().hex[:8],
        },
    )
    assert alta.status_code == 201, alta.text
    return str(alta.json()["id"])


def _nota(gasto_id: str, importe: str, **extra: object) -> dict[str, object]:
    base: dict[str, object] = {
        "gasto_id": gasto_id,
        "importe": importe,
        "periodo": "2026-10-01",
        "cuit_emisor": _CUIT_A,
        "punto_de_venta": "0001",
        "tipo_de_comprobante": "NC",
        "numero_de_comprobante": uuid4().hex[:8],
    }
    base.update(extra)
    return base


# --- 4.1: asociación obligatoria ---


def test_nota_sin_factura_da_422(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo)
    datos = _nota(factura, "10.00")
    del datos["gasto_id"]
    respuesta = api_edificio.cliente.post("/api/notas-de-credito", json=datos)
    assert respuesta.status_code == 422, respuesta.text


def test_factura_de_otro_edificio_da_404(api_edificio: ApiEdificio) -> None:
    #: Factura inexistente (equivalente, para este endpoint, a "de otro
    #: edificio": `_autorizar_gasto` da la misma 404 en los dos casos, D7 —
    #: nunca revela cuál de las dos pasó, L-017).
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        "/api/notas-de-credito", json=_nota(str(uuid4()), "10.00")
    )
    assert respuesta.status_code == 404, respuesta.text


def test_mismo_numero_que_su_factura_otro_tipo_no_es_duplicada(
    api_edificio: ApiEdificio,
) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    numero = uuid4().hex[:8]
    api_edificio.como("editar")
    factura = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": "Factura",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": "2026-10-01",
            "importe": "100000.00",
            "cuit_emisor": _CUIT_A,
            "punto_de_venta": "0001",
            "tipo_de_comprobante": "FA",
            "numero_de_comprobante": numero,
        },
    ).json()["id"]
    respuesta = api_edificio.cliente.post(
        "/api/notas-de-credito",
        json=_nota(factura, "10.00", numero_de_comprobante=numero, tipo_de_comprobante="NC"),
    )
    assert respuesta.status_code == 201, respuesta.text


def test_dos_notas_con_la_misma_clave_la_segunda_da_409(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo)
    datos = _nota(factura, "10.00")
    r1 = api_edificio.cliente.post("/api/notas-de-credito", json=datos)
    assert r1.status_code == 201, r1.text
    r2 = api_edificio.cliente.post("/api/notas-de-credito", json=datos)
    assert r2.status_code == 409, r2.text


# --- 4.3: el tope ---


def test_nota_menor_que_su_factura_pasa(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo, importe="100000.00")
    respuesta = api_edificio.cliente.post("/api/notas-de-credito", json=_nota(factura, "15000.00"))
    assert respuesta.status_code == 201, respuesta.text


def test_nota_igual_al_monto_deja_neto_en_cero(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo, importe="100000.00")
    respuesta = api_edificio.cliente.post("/api/notas-de-credito", json=_nota(factura, "100000.00"))
    assert respuesta.status_code == 201, respuesta.text
    api_edificio.cliente.post(f"/api/gastos/{factura}/aprobar")
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert lectura["grupos"][grupo]["total"] == "0.00"


def test_nota_mayor_por_un_centavo_da_422_y_no_registra_nada(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo, importe="100000.00")
    respuesta = api_edificio.cliente.post("/api/notas-de-credito", json=_nota(factura, "100000.01"))
    assert respuesta.status_code == 422, respuesta.text
    assert (
        api_edificio.filas("SELECT id FROM nota_de_credito WHERE gasto_id = %s", (factura,)) == []
    )


def test_dos_notas_que_juntas_superan_la_factura_rechazan_la_segunda(
    api_edificio: ApiEdificio,
) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo, importe="100000.00")
    r1 = api_edificio.cliente.post("/api/notas-de-credito", json=_nota(factura, "60000.00"))
    assert r1.status_code == 201, r1.text
    r2 = api_edificio.cliente.post("/api/notas-de-credito", json=_nota(factura, "50000.00"))
    assert r2.status_code == 422, r2.text
    assert "40000.00" in r2.text


def test_carrera_entre_dos_notas_simultaneas(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo, importe="100000.00")
    datos_a = _nota(factura, "60000.00")
    datos_b = _nota(factura, "60000.00")

    def _postear(datos: dict[str, object]) -> int:
        return int(api_edificio.cliente.post("/api/notas-de-credito", json=datos).status_code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(_postear, [datos_a, datos_b]))
    assert sorted(resultados) == [201, 422]
    total = api_edificio.filas(
        "SELECT COALESCE(SUM(importe), 0) FROM nota_de_credito WHERE gasto_id = %s", (factura,)
    )[0][0]
    assert total <= 100000


# --- 4.5: mutantes obligatorios sobre 4.3 y 4.4 ---


def test_mutante_sin_for_update_rompe_la_carrera(api_edificio: ApiEdificio) -> None:
    """Dos hilos reales contra el `TestClient` no garantizan pisarse en la
    ventana exacta (L-016: un rojo que depende del scheduler del SO no es
    reproducible). Esta prueba orquesta la interleaving a mano, con dos
    conexiones separadas y sin `FOR UPDATE` (copiando `_nota_sin_for_update`
    paso a paso, L-013): A lee, B lee (sin ver el commit de A todavía), A
    inserta y confirma, B inserta igual — nunca se volvió a consultar el
    acreditado antes del segundo `INSERT`, que es exactamente lo que el
    `FOR UPDATE` real evita bloqueando la lectura de B hasta que A termine."""
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo, importe="100000.00")

    con_a = api_edificio.base.conectar_app()
    con_b = api_edificio.base.conectar_app()
    try:
        for con in (con_a, con_b):
            con.autocommit = False
            con.execute(
                "SELECT set_config('app.administracion_id', %s, true)",
                (str(api_edificio.admin),),
            )
        fila_importe_a = con_a.execute(
            "SELECT importe FROM gasto WHERE id = %s", (factura,)
        ).fetchone()
        fila_importe_b = con_b.execute(
            "SELECT importe FROM gasto WHERE id = %s", (factura,)
        ).fetchone()
        fila_acreditado_a = con_a.execute(
            "SELECT COALESCE(SUM(importe), 0) FROM nota_de_credito WHERE gasto_id = %s",
            (factura,),
        ).fetchone()
        fila_acreditado_b = con_b.execute(
            "SELECT COALESCE(SUM(importe), 0) FROM nota_de_credito WHERE gasto_id = %s",
            (factura,),
        ).fetchone()
        assert fila_importe_a is not None
        assert fila_importe_b is not None
        assert fila_acreditado_a is not None
        assert fila_acreditado_b is not None
        importe_a = fila_importe_a[0]
        importe_b = fila_importe_b[0]
        acreditado_a = fila_acreditado_a[0]
        acreditado_b = fila_acreditado_b[0]
        assert importe_a - acreditado_a >= 60000  # A decide que 60.000 entra
        assert importe_b - acreditado_b >= 60000  # B, sin ver a A, decide lo mismo
        con_a.execute(
            "INSERT INTO nota_de_credito (administracion_id, complejo_id, gasto_id, importe, "
            "periodo, cuit_emisor, punto_de_venta, tipo_de_comprobante, numero_de_comprobante) "
            "VALUES (%s, %s, %s, '60000.00', '2026-10-01', %s, '0001', 'NC', %s)",
            (api_edificio.admin, api_edificio.edificio, factura, _CUIT_A, uuid4().hex[:8]),
        )
        con_a.commit()
        con_b.execute(
            "INSERT INTO nota_de_credito (administracion_id, complejo_id, gasto_id, importe, "
            "periodo, cuit_emisor, punto_de_venta, tipo_de_comprobante, numero_de_comprobante) "
            "VALUES (%s, %s, %s, '60000.00', '2026-10-01', %s, '0001', 'NC', %s)",
            (api_edificio.admin, api_edificio.edificio, factura, _CUIT_A, uuid4().hex[:8]),
        )
        con_b.commit()
    finally:
        con_a.close()
        con_b.close()
    total = api_edificio.filas(
        "SELECT COALESCE(SUM(importe), 0) FROM nota_de_credito WHERE gasto_id = %s", (factura,)
    )[0][0]
    assert total == 120000, (
        "sin FOR UPDATE, las dos conexiones deciden con el mismo acreditado viejo: "
        "120.000 > la factura de 100.000 — exactamente lo que D5 impide con el lock real"
    )


def test_mutante_sin_tope_rompe_en_el_422(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proptech_core.gastos.aplicacion import notas_de_credito as modulo_tope

    def _sin_tope(sesion, identidad, *, gasto_id, datos, request_id):  # type: ignore[no-untyped-def]
        from sqlalchemy import text

        from proptech_core.acceso.aplicacion.auditoria import registrar
        from proptech_core.acceso.dominio.eventos import EventoDelGasto
        from proptech_core.gastos.aplicacion.errores import transaccion
        from proptech_core.gastos.dominio.nota_de_credito import DatosNotaDeCredito

        entrada = DatosNotaDeCredito.model_validate(datos)
        with transaccion(sesion, {"uq_nota_factura": "factura"}):
            factura = (
                sesion.execute(
                    text("SELECT complejo_id FROM gasto WHERE id=:id FOR UPDATE"),
                    {"id": gasto_id},
                )
                .mappings()
                .first()
            )
            #: MUTANTE: no se compara contra el tope — se inserta igual.
            nota_id = sesion.execute(
                text(
                    "INSERT INTO nota_de_credito (administracion_id, complejo_id, gasto_id, "
                    "importe, periodo, cuit_emisor, punto_de_venta, tipo_de_comprobante, "
                    "numero_de_comprobante) VALUES (:admin, :complejo, :gasto_id, :importe, "
                    ":periodo, :cuit_emisor, :punto_de_venta, :tipo_de_comprobante, "
                    ":numero_de_comprobante) RETURNING id"
                ),
                {
                    "admin": identidad.administracion_id,
                    "complejo": factura["complejo_id"],
                    "gasto_id": gasto_id,
                    "importe": entrada.importe.a_texto(),
                    "periodo": entrada.periodo,
                    "cuit_emisor": entrada.cuit_emisor,
                    "punto_de_venta": entrada.punto_de_venta,
                    "tipo_de_comprobante": entrada.tipo_de_comprobante,
                    "numero_de_comprobante": entrada.numero_de_comprobante,
                },
            ).scalar_one()
            registrar(
                sesion,
                identidad,
                EventoDelGasto.CARGAR_NOTA_DE_CREDITO,
                entidad="nota_de_credito",
                entidad_id=nota_id,
                request_id=request_id,
                detalle={"complejo_id": str(factura["complejo_id"]), "gasto_id": str(gasto_id)},
            )
        return nota_id

    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo, importe="100000.00")
    monkeypatch.setattr(modulo_tope, "crear_nota_de_credito", _sin_tope)
    respuesta = api_edificio.cliente.post("/api/notas-de-credito", json=_nota(factura, "100000.01"))
    #: Rompe exactamente en el código de estado que 4.3 afirma (422), no antes.
    assert respuesta.status_code == 201, (
        "el mutante sin tope tiene que dejar pasar un monto que debería rechazarse con 422"
    )


# --- 4.6: efecto en el reparto ---


def test_nota_baja_el_total_de_su_grupo_y_no_toca_otros(api_edificio: ApiEdificio) -> None:
    categoria_a, grupo_a = _crear_categoria_y_grupo(api_edificio)
    categoria_b, grupo_b = _crear_categoria_y_grupo(api_edificio)
    factura_a = _crear_factura(api_edificio, categoria_a, grupo_a, importe="100000.00")
    _crear_factura(api_edificio, categoria_b, grupo_b, importe="50000.00")
    api_edificio.cliente.post(f"/api/gastos/{factura_a}/aprobar")
    for g in api_edificio.filas("SELECT id FROM gasto WHERE grupo_id = %s", (grupo_b,)):
        api_edificio.cliente.post(f"/api/gastos/{g[0]}/aprobar")
    api_edificio.cliente.post("/api/notas-de-credito", json=_nota(factura_a, "15000.00"))
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert lectura["grupos"][grupo_a]["total"] == "85000.00"
    assert lectura["grupos"][grupo_b]["total"] == "50000.00"


def test_nota_no_figura_como_gasto(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo)
    nota_id = api_edificio.cliente.post(
        "/api/notas-de-credito", json=_nota(factura, "15000.00")
    ).json()["id"]
    gastos_del_edificio = api_edificio.cliente.get(api_edificio.ruta("/gastos")).json()
    assert nota_id not in [g["id"] for g in gastos_del_edificio]


def test_nota_sobre_gasto_no_aprobado_no_cambia_el_neto_hasta_aprobar(
    api_edificio: ApiEdificio,
) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo, importe="100000.00")
    respuesta = api_edificio.cliente.post("/api/notas-de-credito", json=_nota(factura, "15000.00"))
    assert respuesta.status_code == 201, respuesta.text
    lectura_antes = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert lectura_antes["grupos"] == {}
    api_edificio.cliente.post(f"/api/gastos/{factura}/aprobar")
    lectura_despues = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert lectura_despues["grupos"][grupo]["total"] == "85000.00"


# --- 4.7: nunca reabre un período ya emitido ---


def test_nota_sobre_factura_de_periodo_anterior_se_descuenta_en_el_periodo_en_que_se_carga(
    api_edificio: ApiEdificio,
) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    factura = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": "Factura de un período anterior",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": "2026-09-01",
            "importe": "100000.00",
            "cuit_emisor": _CUIT_A,
            "punto_de_venta": "0001",
            "tipo_de_comprobante": "FA",
            "numero_de_comprobante": uuid4().hex[:8],
        },
    ).json()["id"]
    api_edificio.cliente.post(f"/api/gastos/{factura}/aprobar")
    nota = api_edificio.cliente.post(
        "/api/notas-de-credito", json=_nota(factura, "15000.00", periodo="2026-10-01")
    )
    assert nota.status_code == 201, nota.text
    lectura_setiembre = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-09-01/gastos-aprobados")
    ).json()
    assert lectura_setiembre["grupos"][grupo]["total"] == "100000.00"
    lectura_octubre = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert lectura_octubre["grupos"][grupo]["total"] == "-15000.00"


def test_nota_queda_con_su_propio_periodo_separado_del_de_la_factura(
    api_edificio: ApiEdificio,
) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    api_edificio.como("editar")
    factura = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": "Factura anterior",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": "2026-09-01",
            "importe": "100000.00",
            "cuit_emisor": _CUIT_A,
            "punto_de_venta": "0001",
            "tipo_de_comprobante": "FA",
            "numero_de_comprobante": uuid4().hex[:8],
        },
    ).json()["id"]
    nota_id = api_edificio.cliente.post(
        "/api/notas-de-credito", json=_nota(factura, "15000.00", periodo="2026-10-01")
    ).json()["id"]
    nota = api_edificio.cliente.get(f"/api/notas-de-credito/{nota_id}").json()
    gasto = api_edificio.cliente.get(f"/api/gastos/{factura}").json()
    assert nota["periodo"] != gasto["periodo"]
    assert nota["periodo"] == "2026-10-01"
    assert gasto["periodo"] == "2026-09-01"


def test_no_escribe_en_el_libro(
    api_edificio: ApiEdificio, app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo)
    api_edificio.cliente.post("/api/notas-de-credito", json=_nota(factura, "15000.00"))
    fijar_tenant(app_edificio, api_edificio.admin)
    for tabla in ("movimiento", "obligacion", "imputacion"):
        assert app_edificio.execute(f"SELECT count(*) FROM {tabla}").fetchone() == (0,)  # noqa: S608


# --- 4.8: auditoría ---


def test_alta_de_nota_auditada_sin_monto(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo)
    nota_id = api_edificio.cliente.post(
        "/api/notas-de-credito", json=_nota(factura, "15000.00")
    ).json()["id"]
    filas = api_edificio.filas(
        "SELECT accion, detalle::text FROM auditoria WHERE entidad_id = %s", (nota_id,)
    )
    assert len(filas) == 1
    accion, detalle = filas[0]
    assert accion == "cargar_nota_de_credito"
    assert "15000" not in detalle
    assert factura in detalle


def test_contador_sin_permiso_da_403(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo)
    api_edificio.como("contador")
    respuesta = api_edificio.cliente.post("/api/notas-de-credito", json=_nota(factura, "15000.00"))
    assert respuesta.status_code == 403, respuesta.text
    # D-131 (2d): todo 403 lleva `codigo`; sumado al integrar `main`.
    assert respuesta.json()["detail"].get("codigo") == "sin_permiso", respuesta.text
