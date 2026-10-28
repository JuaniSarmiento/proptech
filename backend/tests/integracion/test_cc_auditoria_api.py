"""4.2/4.3: app real, roles del deploy, datos confirmados y lectura por otra conexión."""

from collections.abc import Iterator
from datetime import date
from typing import Any, Literal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import correcciones, creditos, emisiones
from proptech_core.cuenta_corriente.aplicacion.correcciones import PedidoDeCorreccion
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

from ._api_edificios import ApiEdificio
from ._cuenta_corriente import sesion_app

pytestmark = pytest.mark.integracion


@pytest.fixture
def libro_api(api_edificio: ApiEdificio) -> Iterator[tuple[ApiEdificio, dict[str, UUID]]]:
    api = api_edificio
    ids: dict[str, UUID] = {}
    principal = uuid4()
    with api.base.conectar_app() as c, c.transaction():
        c.execute("SELECT set_config('app.administracion_id', %s, true)", (str(api.admin),))
        c.execute(
            "INSERT INTO persona (id, administracion_id, nombre) "
            "VALUES (%s, %s, 'Principal ficticio')",
            (principal, api.admin),
        )
        c.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
            "VALUES (%s, %s, 'administrador')",
            (api.admin, principal),
        )
    api.personas["principal"] = principal
    for etiqueta, adm, edificio, unidad in (
        ("propio", api.admin, api.edificio, api.unidad),
        ("otro", api.admin, api.otro, api.otra_unidad),
        ("ajeno", api.admin_ajena, api.ajeno, api.unidad_ajena),
    ):
        with sesion_app(api.base, adm) as s:
            persona = api.personas["super_admin"] if adm == api.admin else uuid4()
            if adm != api.admin:
                s.execute(
                    text(
                        "INSERT INTO persona (id, administracion_id, nombre) "
                        "VALUES (:p, :a, 'Ajena ficticia')"
                    ),
                    {"p": persona, "a": adm},
                )
            identidad = Identidad(adm, persona)
            emitida = emisiones.registrar_emision(
                s,
                identidad,
                emision_id=uuid4(),
                complejo_id=edificio,
                periodo=date(2026, 10, 1),
                obligaciones=[
                    ObligacionAEmitir(
                        unidad, date(2026, 10, 10), Dinero("100.00"), Dinero("0.00"), Dinero("0.00")
                    )
                ],
                request_id=uuid4(),
            )
            cuenta = emitida.cuentas[unidad]
            obligacion = s.execute(
                text("SELECT id FROM obligacion WHERE cuenta_id=:c"), {"c": cuenta}
            ).scalar_one()
            pago = creditos.registrar_credito(
                s,
                identidad,
                cuenta_id=cuenta,
                tipo="pago",
                importe=Dinero("20.00"),
                fecha_valor=date(2026, 10, 11),
                operacion_id=uuid4(),
                destino=None,
                request_id=uuid4(),
            )
            ids[f"obligacion_{etiqueta}"] = obligacion
            ids[f"pago_{etiqueta}"] = pago
            s.commit()
    api.como("principal")
    yield api, ids


def cuerpo(ids: dict[str, UUID], forma: str = "contra_asiento") -> dict[str, Any]:
    datos: dict[str, Any] = {
        "forma": forma,
        "operacion_id": str(uuid4()),
        "motivo": "Error ficticio",
    }
    if forma == "credito":
        datos.update(obligacion_id=str(ids["obligacion_propio"]), importe="10.00")
    else:
        datos["movimiento_id"] = str(ids["pago_propio"])
    return datos


@pytest.mark.parametrize("forma", ["contra_asiento", "credito"])
def test_correccion_auditada_y_replay(
    libro_api: tuple[ApiEdificio, dict[str, UUID]], forma: Literal["contra_asiento", "credito"]
) -> None:
    api, ids = libro_api
    datos = cuerpo(ids, forma)
    correccion = None
    error = None
    # Sin 0024 el error FK se captura aquí, nunca en el arranque de la fixture.
    with sesion_app(api.base, api.admin) as s:
        try:
            correccion = correcciones.corregir(
                s,
                Identidad(api.admin, api.personas["principal"]),
                complejo_id=api.edificio,
                pedido=PedidoDeCorreccion(
                    forma,
                    UUID(datos["operacion_id"]),
                    datos["motivo"],
                    movimiento_id=ids["pago_propio"] if forma == "contra_asiento" else None,
                    obligacion_id=ids["obligacion_propio"] if forma == "credito" else None,
                    importe=Dinero("10.00") if forma == "credito" else None,
                ),
                request_id=uuid4(),
            )
            s.commit()
        except IntegrityError as fallo:
            error = getattr(fallo.orig, "sqlstate", None)
    filas = api.filas(
        "SELECT entidad_id, detalle FROM auditoria WHERE accion='corregir_movimiento'"
    )
    assert filas == [
        (
            correccion,
            {
                "complejo_id": str(api.edificio),
                "forma": forma,
                "corrige": str(
                    ids["pago_propio"] if forma == "contra_asiento" else ids["obligacion_propio"]
                ),
            },
        )
    ], f"auditoria ausente o distinta, SQLSTATE={error}"
    repetido = api.cliente.post(api.ruta("/correcciones"), json=datos)
    assert repetido.status_code == 201
    assert repetido.json() == {"movimiento_id": str(correccion)}
    assert api.filas("SELECT count(*) FROM auditoria WHERE accion='corregir_movimiento'") == [(1,)]


def test_falla_auditoria_por_api_no_confirma(
    libro_api: tuple[ApiEdificio, dict[str, UUID]], monkeypatch: pytest.MonkeyPatch
) -> None:
    api, ids = libro_api
    antes = api.filas("SELECT (SELECT count(*) FROM movimiento), (SELECT count(*) FROM imputacion)")
    vistas = []

    def fallar(sesion: Any, *args: Any, **kwargs: Any) -> None:
        vistas.append(
            sesion.execute(
                text("SELECT count(*) FROM movimiento WHERE tipo='correccion'")
            ).scalar_one()
        )
        raise RuntimeError("fallo ficticio de auditoria")

    monkeypatch.setattr(correcciones, "registrar", fallar, raising=False)
    cliente = TestClient(api.app, raise_server_exceptions=False)
    try:
        respuesta = cliente.post(api.ruta("/correcciones"), json=cuerpo(ids, "credito"))
    finally:
        cliente.close()
    assert respuesta.status_code == 500
    assert vistas == [1], "La auditoría debe fallar después de insertar la corrección"
    assert (
        api.filas("SELECT (SELECT count(*) FROM movimiento), (SELECT count(*) FROM imputacion)")
        == antes
    )
    assert api.filas("SELECT count(*) FROM movimiento WHERE tipo='correccion'") == [(0,)]


def test_vocabulario_de_correccion(base_del_edificio: Any) -> None:
    with base_del_edificio.conectar_app() as c:
        filas = c.execute(
            "SELECT nombre FROM accion_de_auditoria WHERE nombre='corregir_movimiento'"
        ).fetchall()
    assert filas == [("corregir_movimiento",)]


def test_openapi_contrato_completo(libro_api: tuple[ApiEdificio, dict[str, UUID]]) -> None:
    api, _ = libro_api
    documento = api.app.openapi()
    respuestas = documento["paths"]["/api/complejos/{complejo_id}/correcciones"]["post"][
        "responses"
    ]
    assert set(respuestas) == {"201", "401", "403", "404", "409", "422", "500", "503"}
    campos = {
        "201": {"movimiento_id"},
        "401": {"detail"},
        "403": {"detail"},
        "404": {"detail"},
        "409": {"detail", "campo"},
        "422": {"detail"},
        "500": {"error", "request_id"},
        "503": {"detail"},
    }
    for codigo, nombres in campos.items():
        esquema = respuestas[codigo]["content"]["application/json"]["schema"]
        if "$ref" in esquema:
            esquema = documento["components"]["schemas"][esquema["$ref"].split("/")[-1]]
        assert set(esquema["properties"]) == nombres, codigo
        assert set(esquema["required"]) == nombres, codigo


@pytest.mark.parametrize("rol", ["super_admin", "principal"])
@pytest.mark.parametrize("forma", ["contra_asiento", "credito"])
def test_ruta_crea_y_repite(
    libro_api: tuple[ApiEdificio, dict[str, UUID]], rol: str, forma: str
) -> None:
    api, ids = libro_api
    api.como(rol)
    datos = cuerpo(ids, forma)
    primera = api.cliente.post(api.ruta("/correcciones"), json=datos)
    segunda = api.cliente.post(api.ruta("/correcciones"), json=datos)
    assert primera.status_code == segunda.status_code == 201
    assert primera.json() == segunda.json()
    assert api.filas("SELECT count(*) FROM auditoria WHERE accion='corregir_movimiento'") == [(1,)]


@pytest.mark.parametrize("forma", ["contra_asiento", "credito"])
@pytest.mark.parametrize("origen", ["inexistente", "otro", "ajeno"])
def test_recurso_ajeno_es_igual_a_inexistente(
    libro_api: tuple[ApiEdificio, dict[str, UUID]], forma: str, origen: str
) -> None:
    api, ids = libro_api
    datos = cuerpo(ids, forma)
    campo, prefijo = (
        ("movimiento_id", "pago") if forma == "contra_asiento" else ("obligacion_id", "obligacion")
    )
    datos[campo] = str(uuid4() if origen == "inexistente" else ids[f"{prefijo}_{origen}"])
    respuesta = api.cliente.post(api.ruta("/correcciones"), json=datos)
    assert (respuesta.status_code, respuesta.json()) == (404, {"detail": "no encontrado"})
    assert api.filas("SELECT count(*) FROM movimiento WHERE tipo='correccion'") == [(0,)]


@pytest.mark.parametrize("existe", [False, True])
def test_ae_sin_permiso_no_averigua_recurso(
    libro_api: tuple[ApiEdificio, dict[str, UUID]], existe: bool
) -> None:
    api, ids = libro_api
    api.como("editar")
    datos = cuerpo(ids)
    if not existe:
        datos["movimiento_id"] = str(uuid4())
    respuesta = api.cliente.post(api.ruta("/correcciones"), json=datos)
    assert (respuesta.status_code, respuesta.json()) == (
        403,
        {
            "detail": {
                "codigo": "sin_permiso",
                "detalle": "sin_permiso",
                "permiso_faltante": "corregir_movimiento",
            }
        },
    )


@pytest.mark.parametrize("motivo", ["x", "x" * 500, " " + "x" * 500 + " "])
def test_motivo_normalizado_valido(
    libro_api: tuple[ApiEdificio, dict[str, UUID]], motivo: str
) -> None:
    api, ids = libro_api
    datos = {**cuerpo(ids), "motivo": motivo}
    respuesta = api.cliente.post(api.ruta("/correcciones"), json=datos)
    assert respuesta.status_code == 201
    assert api.filas("SELECT motivo FROM movimiento WHERE tipo='correccion'") == [(motivo.strip(),)]


@pytest.mark.parametrize(
    "cambios,campo",
    [
        ({"extra": "PRIVADO"}, "extra"),
        ({"importe": "10.005"}, "importe"),
        ({"importe": "0.00"}, "importe"),
        ({"importe": "-1.00"}, "importe"),
        ({"importe": 10.0}, "importe"),
        ({"operacion_id": "PRIVADO"}, "operacion_id"),
        ({"motivo": ""}, "motivo"),
        ({"motivo": "   "}, "motivo"),
        ({"motivo": "x" * 501}, "motivo"),
        ({"forma": "debito"}, "forma"),
    ],
)
def test_validacion_del_cuerpo(
    libro_api: tuple[ApiEdificio, dict[str, UUID]], cambios: dict[str, Any], campo: str
) -> None:
    api, ids = libro_api
    respuesta = api.cliente.post(
        api.ruta("/correcciones"), json={**cuerpo(ids, "credito"), **cambios}
    )
    assert respuesta.status_code == 422
    assert any(
        campo in error["loc"] or (campo == "forma" and error["type"] == "union_tag_invalid")
        for error in respuesta.json()["detail"]
    ), respuesta.json()
    assert "PRIVADO" not in respuesta.text and "10.005" not in respuesta.text
    assert all("input" not in error and "ctx" not in error for error in respuesta.json()["detail"])
    assert api.filas("SELECT count(*) FROM movimiento WHERE tipo='correccion'") == [(0,)]


@pytest.mark.parametrize("forma", ["contra_asiento", "credito"])
@pytest.mark.parametrize("cambio", ["motivo", "inexistente", "otro", "ajeno"])
def test_replay_cambiado_gana_a_recurso_inexistente(
    libro_api: tuple[ApiEdificio, dict[str, UUID]], forma: str, cambio: str
) -> None:
    api, ids = libro_api
    datos = cuerpo(ids, forma)
    primera = api.cliente.post(api.ruta("/correcciones"), json=datos)
    assert primera.status_code == 201
    if cambio == "motivo":
        datos["motivo"] = "Otro motivo ficticio"
    else:
        campo, prefijo = (
            ("movimiento_id", "pago")
            if forma == "contra_asiento"
            else ("obligacion_id", "obligacion")
        )
        datos[campo] = str(uuid4() if cambio == "inexistente" else ids[f"{prefijo}_{cambio}"])
    respuesta = api.cliente.post(api.ruta("/correcciones"), json=datos)
    assert (respuesta.status_code, respuesta.json()) == (
        409,
        {"detail": "conflicto", "campo": "operacion_id"},
    )
    assert api.filas("SELECT count(*) FROM auditoria WHERE accion='corregir_movimiento'") == [(1,)]


@pytest.mark.parametrize("json_roto", [False, True])
def test_sin_identidad_no_toca_base(
    libro_api: tuple[ApiEdificio, dict[str, UUID]], json_roto: bool
) -> None:
    from sqlalchemy import event

    from proptech_api.acceso import identidad_actual

    api, ids = libro_api
    api.app.dependency_overrides.pop(identidad_actual)
    consultas = []

    def ver(*args: Any) -> None:
        consultas.append(args[2])

    event.listen(api.app.state.engine, "before_cursor_execute", ver)
    try:
        respuesta = api.cliente.post(
            api.ruta("/correcciones"),
            content="{" if json_roto else None,
            json=None if json_roto else cuerpo(ids),
        )
    finally:
        event.remove(api.app.state.engine, "before_cursor_execute", ver)
    assert respuesta.status_code == 401
    assert consultas == []


def test_orden_cuerpo_edificio_permiso(libro_api: tuple[ApiEdificio, dict[str, UUID]]) -> None:
    api, ids = libro_api
    api.como("editar")
    datos = cuerpo(ids)
    assert (
        api.cliente.post(api.ruta("/correcciones"), json={**datos, "extra": "x"}).status_code == 422
    )
    ruta = f"/api/complejos/{api.otro}/correcciones"
    respuesta = api.cliente.post(ruta, json=datos)
    assert (respuesta.status_code, respuesta.json()) == (404, {"detail": "no encontrado"})


@pytest.mark.parametrize(
    "estado,constraint,codigo,campo",
    [
        ("23505", "uq_mov_operacion", 409, "operacion_id"),
        ("23505", "uq_obligacion_operacion", 409, "operacion_id"),
        ("23505", "uq_mov_corrige_a", 409, "movimiento_id"),
        ("23505", "uq_emision_intento", 409, "periodo"),
        ("23505", "emision_pkey", 409, "emision_id"),
        ("23505", "uq_obligacion_emision", 409, "emision_id"),
        ("23505", "uq_evento_emision_tipo", 409, "emision_id"),
        ("23505", "uq_cuenta_unidad", 409, "unidad_id"),
        ("23505", "uq_cuenta_persona", 409, "persona_id"),
        ("23505", "no_declarado", 500, None),
        ("23503", "fk_ficticia", 404, None),
        ("23514", "ck_ficticio", 500, None),
        ("42501", "privilegio", 500, None),
        ("40P01", "deadlock", 503, None),
        ("40001", "serializacion", 503, None),
        ("55P03", "espera", 503, None),
        ("57014", "cancelacion", 503, None),
    ],
)
def test_sqlstate_real_recupera_transaccion(
    libro_api: tuple[ApiEdificio, dict[str, UUID]],
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    estado: str,
    constraint: str,
    codigo: int,
    campo: str | None,
) -> None:
    from proptech_api import cuenta_corriente as ruta
    from proptech_core.cuenta_corriente.aplicacion.errores import traducir

    api, ids = libro_api
    recuperada = []
    intentos = []

    def fallar(sesion: Any, *args: Any, **kwargs: Any) -> None:
        intentos.append(1)
        try:
            with traducir(sesion, {}):
                sesion.execute(
                    text(
                        f"DO $$ BEGIN RAISE EXCEPTION USING ERRCODE='{estado}', "
                        f"CONSTRAINT='{constraint}', MESSAGE='PRIVADO_SQL', "
                        "DETAIL='PRIVADO_DETAIL'; END $$"
                    )
                )
        except Exception:
            recuperada.append(sesion.execute(text("SELECT 1")).scalar_one())
            raise

    monkeypatch.setattr(ruta, "corregir", fallar)
    respuesta = api.cliente.post(api.ruta("/correcciones"), json=cuerpo(ids))
    assert respuesta.status_code == codigo
    assert recuperada == [1] and intentos == [1]
    if codigo == 409:
        assert respuesta.json() == {"detail": "conflicto", "campo": campo}
    elif codigo == 404:
        assert respuesta.json() == {"detail": "no encontrado"}
    elif codigo == 503:
        assert respuesta.json() == {"detail": "temporalmente no disponible"}
    else:
        assert respuesta.json() == {
            "error": "interno",
            "request_id": respuesta.headers["X-Request-ID"],
        }
    salida = capfd.readouterr()
    assert "PRIVADO_" not in respuesta.text + salida.out + salida.err
