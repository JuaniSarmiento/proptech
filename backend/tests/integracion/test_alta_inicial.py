"""5.1: bootstrap transaccional como proptech_app, sin Clerk."""

import asyncio
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from ._api_edificios import ApiEdificio
from ._usuarios import preparar

pytestmark = pytest.mark.integracion


def test_primera_administracion_y_permiso_existente(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proptech_core.acceso.aplicacion.alta_inicial import crear
    from proptech_core.compartido.base_de_datos import abrir_sesion

    cola = preparar(api_edificio, monkeypatch)
    request_id = uuid4()
    admin = asyncio.run(
        crear(
            api_edificio.app.state.fabrica_de_sesiones,
            configuracion=api_edificio.app.state.configuracion,
            parametros=api_edificio.app.state.parametros,
            cola=cola,
            administracion="Administración inventada",
            nombre="Persona inventada",
            email="NUEVA@example.invalid",
            request_id=request_id,
        )
    )
    with abrir_sesion(api_edificio.app.state.fabrica_de_sesiones, admin) as sesion:
        assert sesion.execute(text("SELECT current_user")).scalar_one() == "proptech_app"
        assert sesion.execute(text("SELECT nombre FROM administracion")).scalars().all() == [
            "Administración inventada"
        ]
        persona = sesion.execute(text("SELECT id,email FROM persona")).one()
        assert persona.email == "nueva@example.invalid"
        assert sesion.execute(text("SELECT persona_id,rol FROM asignacion_rol")).all() == [
            (persona.id, "super_admin")
        ]
        invitacion = sesion.execute(
            text("SELECT persona_id,estado,token_resumen FROM invitacion")
        ).one()
        assert invitacion.persona_id == persona.id and invitacion.estado == "pendiente"
        assert len(invitacion.token_resumen) == 32
        assert sesion.execute(
            text("SELECT persona_id,accion,request_id,detalle FROM auditoria")
        ).all() == [(persona.id, "alta_inicial", request_id, {})]
    assert len(cola.trabajos) == 1
    assert cola.trabajos[0]["administracion_id"] == str(admin)
    assert "sobre" in cola.trabajos[0] and "@" not in str(cola.trabajos)
    assert api_edificio.filas("SELECT nombre FROM administracion") == [("Inventada API",)]
    # Repetir sobre EL MISMO tenant: el comando normalmente genera un UUID nuevo.
    monkeypatch.setattr("proptech_core.acceso.aplicacion.alta_inicial.uuid4", lambda: admin)
    with pytest.raises(ValueError, match="administracion"):
        asyncio.run(
            crear(
                api_edificio.app.state.fabrica_de_sesiones,
                configuracion=api_edificio.app.state.configuracion,
                parametros=api_edificio.app.state.parametros,
                cola=cola,
                administracion="Administración inventada",
                nombre="Persona inventada",
                email="NUEVA@example.invalid",
                request_id=uuid4(),
            )
        )
    assert len(cola.trabajos) == 1


@pytest.mark.parametrize(
    ("campo", "valor"), [("email", "MARCADOR"), ("nombre", " "), ("administracion", "")]
)
def test_datos_invalidos_no_escriben(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch, campo: str, valor: str
) -> None:
    from proptech_core.acceso.aplicacion.alta_inicial import crear

    cola = preparar(api_edificio, monkeypatch)
    datos: dict[str, Any] = {
        "administracion": "Inventada",
        "nombre": "Ficticia",
        "email": "nueva@example.invalid",
    }
    datos[campo] = valor
    with pytest.raises(ValueError) as error:
        asyncio.run(
            crear(
                api_edificio.app.state.fabrica_de_sesiones,
                configuracion=api_edificio.app.state.configuracion,
                parametros=api_edificio.app.state.parametros,
                cola=cola,
                request_id=uuid4(),
                **datos,
            )
        )
    assert campo in str(error.value) and "MARCADOR" not in str(error.value)
    assert cola.trabajos == []
    assert api_edificio.filas("SELECT count(*) FROM persona WHERE email IS NOT NULL") == [(0,)]


def test_comando_y_rollback_del_alta(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from uuid import UUID

    from proptech_core.acceso.aplicacion import alta_inicial
    from proptech_core.compartido.base_de_datos import abrir_sesion

    cola = preparar(api_edificio, monkeypatch)
    monkeypatch.setattr(alta_inicial, "AdaptadorColaArq", lambda ajustes: cola)
    monkeypatch.setattr(
        "sys.argv",
        [
            "alta_inicial",
            "--administracion",
            "Inventada CLI",
            "--nombre",
            "Ficticia CLI",
            "--email",
            "cli@example.invalid",
        ],
    )
    alta_inicial.main()
    admin = UUID(capsys.readouterr().out.strip())
    assert cola.trabajos[-1]["administracion_id"] == str(admin)
    nuevo = uuid4()
    monkeypatch.setattr(alta_inicial, "uuid4", lambda: nuevo)

    def fallar(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("fallo simulado antes de auditar")

    monkeypatch.setattr(
        "sys.argv",
        [
            "alta_inicial",
            "--administracion",
            "Inventada rollback",
            "--nombre",
            "Ficticia rollback",
            "--email",
            "rollback@example.invalid",
        ],
    )
    monkeypatch.setattr(alta_inicial, "registrar", fallar)
    with pytest.raises(RuntimeError, match="fallo simulado"):
        alta_inicial.main()
    with abrir_sesion(api_edificio.app.state.fabrica_de_sesiones, nuevo) as sesion:
        for consulta in (
            "SELECT count(*) FROM administracion",
            "SELECT count(*) FROM persona",
            "SELECT count(*) FROM asignacion_rol",
            "SELECT count(*) FROM invitacion",
            "SELECT count(*) FROM auditoria",
        ):
            assert sesion.execute(text(consulta)).scalar_one() == 0
    assert len(cola.trabajos) == 1
