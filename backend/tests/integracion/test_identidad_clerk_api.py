"""4.1: firma antes de SQL, vínculo por identidad y selector posterior."""

import hashlib
import logging
from typing import Any
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import event

from ._api_edificios import ApiEdificio
from ._clerk import api_clerk as api_clerk
from ._clerk import clerk_falso as clerk_falso
from ._clerk import encabezados, sub_de, token

pytestmark = pytest.mark.integracion


def test_vinculada_con_asignacion_entra(
    api_clerk: ApiEdificio, clerk_falso: rsa.RSAPrivateKey
) -> None:
    respuesta = api_clerk.cliente.get(api_clerk.ruta(), headers=encabezados(clerk_falso))
    assert respuesta.status_code == 200
    assert respuesta.json()["administracion_id"] == str(api_clerk.admin)


@pytest.mark.parametrize(
    "caso",
    [
        "ausente",
        "vacio",
        "doble",
        "roto",
        "firma",
        "none",
        "hs256",
        "azp_ausente",
        "iss_ausente",
        "sub_ausente",
        "sub_ascii",
        "sub_otra_forma",
        "sub_largo",
        "sub_vacio",
        "sub_numero",
        "azp_lista",
        *[
            f"{campo}_{tipo}"
            for campo in ("exp", "nbf", "iat")
            for tipo in ("ausente", "texto", "booleano", "float")
        ],
        "vencido",
        "nbf",
        "iat",
        "iss",
        "azp",
        "sub",
        "pending",
        "tiempo_texto",
        "tiempo_bool",
        "sin_exp",
        "sin_sub",
    ],
)
def test_invalidos_401_identico_cero_sql(
    api_clerk: ApiEdificio,
    clerk_falso: rsa.RSAPrivateKey,
    caso: str,
) -> None:
    cambios: dict[str, dict[str, Any]] = {
        "vencido": {"exp": 1},
        "nbf": {"nbf": 9999999999},
        "iat": {"iat": 9999999999},
        "iss": {"iss": "https://otro.invalid"},
        "azp": {"azp": "https://otro.invalid"},
        "sub": {"sub": "user_ñ"},
        "pending": {"sts": "pending"},
        "tiempo_texto": {"exp": "9999999999"},
        "tiempo_bool": {"nbf": True},
        "sin_exp": {"exp": None},
        "sin_sub": {"sub": None},
        "azp_ausente": {"azp": None},
        "iss_ausente": {"iss": None},
        "sub_ausente": {"sub": None},
        "sub_ascii": {"sub": "user_\uff11\uff12"},
        "sub_otra_forma": {"sub": "otra_forma"},
        "sub_largo": {"sub": "user_" + "x" * 65},
        "sub_vacio": {"sub": "user_"},
        "sub_numero": {"sub": 123},
        "azp_lista": {"azp": ["https://proptech.invalid"]},
        **{
            f"{campo}_{tipo}": {campo: valor}
            for campo in ("exp", "nbf", "iat")
            for tipo, valor in (
                ("ausente", None),
                ("texto", "9999999999"),
                ("booleano", True),
                ("float", 9999999999.0),
            )
        },
    }
    valor = token(clerk_falso, **cambios.get(caso, {}))
    if caso == "firma":
        valor = token(rsa.generate_private_key(public_exponent=65537, key_size=2048))
    if caso == "none":
        import jwt

        valor = jwt.encode({"sub": "user_Prueba"}, key="", algorithm="none")
    if caso == "hs256":
        import jwt
        from cryptography.hazmat.primitives import serialization

        from tests.unitarios.acceso.test_token import token_hs256

        publica = (
            clerk_falso.public_key()
            .public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            .decode()
        )
        claims = jwt.decode(valor, options={"verify_signature": False})
        valor = token_hs256(claims, publica)
    cabeceras = {"Authorization": "Bearer " + valor}
    if caso == "ausente":
        cabeceras = {}
    elif caso == "vacio":
        cabeceras = {"Authorization": "Bearer "}
    elif caso == "doble":
        cabeceras["Authorization"] += " " + valor
    elif caso == "roto":
        cabeceras = {"Authorization": "Bearer no-jwt"}
    cabeceras["X-Proptech-Administracion"] = "no-es-uuid"
    sentencias: list[str] = []

    def contar(*args: Any) -> None:
        sentencias.append(args[2])

    event.listen(api_clerk.app.state.engine, "before_cursor_execute", contar)
    try:
        base = api_clerk.cliente.get(api_clerk.ruta())
        respuesta = api_clerk.cliente.get(api_clerk.ruta(), headers=cabeceras)
    finally:
        event.remove(api_clerk.app.state.engine, "before_cursor_execute", contar)
    assert sentencias == []
    assert respuesta.status_code == base.status_code == 401
    assert respuesta.content == base.content
    assert dict(respuesta.headers) | {"x-request-id": ""} == dict(base.headers) | {
        "x-request-id": ""
    }


def test_sin_vinculo_minimiza_y_loguea_resumen(
    api_clerk: ApiEdificio,
    clerk_falso: rsa.RSAPrivateKey,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sentencias: list[str] = []

    def contar(*args: Any) -> None:
        sentencias.append(args[2])

    event.listen(api_clerk.app.state.engine, "before_cursor_execute", contar)
    try:
        with caplog.at_level(logging.INFO):
            respuesta = api_clerk.cliente.get(
                api_clerk.ruta(), headers=encabezados(clerk_falso, sub="user_SinVinculo")
            )
    finally:
        event.remove(api_clerk.app.state.engine, "before_cursor_execute", contar)
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "Unauthorized"}
    assert not any(
        tabla in s.lower() for s in sentencias for tabla in ("complejo", "unidad", "asignacion_rol")
    )
    registros = [r for r in caplog.records if r.msg == "ingreso_sin_vinculo"]
    assert len(registros) == 1
    assert (
        registros[0].__dict__["sub_resumen"] == hashlib.sha256(b"user_SinVinculo").hexdigest()[:12]
    )
    assert "user_SinVinculo" not in caplog.text


def test_selector_solo_administraciones_vinculadas(
    api_clerk: ApiEdificio,
    clerk_falso: rsa.RSAPrivateKey,
) -> None:
    h = encabezados(clerk_falso)
    leidos: list[dict[str, Any]] = []

    def contar(*args: Any) -> None:
        if "set_config('app.administracion_id'" in args[2]:
            leidos.append(args[3])

    event.listen(api_clerk.app.state.engine, "before_cursor_execute", contar)
    for selector in (str(api_clerk.admin_ajena), "no-es-uuid"):
        respuesta = api_clerk.cliente.get(
            api_clerk.ruta(), headers=h | {"X-Proptech-Administracion": selector}
        )
        assert respuesta.status_code == 401
    event.remove(api_clerk.app.state.engine, "before_cursor_execute", contar)
    assert leidos == []
    with api_clerk.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_clerk.admin_ajena),)
        )
        persona = uuid4()
        conexion.execute(
            "INSERT INTO persona (id, administracion_id, nombre, clerk_usuario_id) "
            "VALUES (%s, %s, 'Otra ficticia', %s)",
            (persona, api_clerk.admin_ajena, sub_de(clerk_falso)),
        )
        conexion.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
            "VALUES (%s, %s, 'super_admin')",
            (api_clerk.admin_ajena, persona),
        )
    assert api_clerk.cliente.get(api_clerk.ruta(), headers=h).status_code == 401
    assert (
        api_clerk.cliente.get(
            api_clerk.ruta(), headers=h | {"X-Proptech-Administracion": str(api_clerk.admin)}
        ).status_code
        == 200
    )

    assert (
        api_clerk.cliente.get(
            f"/api/complejos/{api_clerk.ajeno}",
            headers=h | {"X-Proptech-Administracion": str(api_clerk.admin_ajena)},
        ).status_code
        == 200
    )


def test_login_apagado_no_lee_sql(
    api_clerk: ApiEdificio, clerk_falso: rsa.RSAPrivateKey, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_clerk.app.state.configuracion, "clerk_jwt_key", None)
    sentencias: list[str] = []

    def contar(*args: Any) -> None:
        sentencias.append(args[2])

    event.listen(api_clerk.app.state.engine, "before_cursor_execute", contar)
    try:
        respuesta = api_clerk.cliente.get(api_clerk.ruta(), headers=encabezados(clerk_falso))
    finally:
        event.remove(api_clerk.app.state.engine, "before_cursor_execute", contar)
    assert respuesta.status_code == 401
    assert sentencias == []
