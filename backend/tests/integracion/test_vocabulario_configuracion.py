"""3.7/D14: vocabulario desde base vacía y lifespan real, sin FK a auditoría."""

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from proptech_core.acceso.dominio.eventos import EventoDelPadron
from proptech_core.acceso.dominio.permisos import Accion

from ..conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION
from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion

_NUEVAS = {
    "crear_edificio",
    "crear_version_de_configuracion",
    "confirmar_sin_saldos_previos",
    "configurar_padron",
    "ver_configuracion_del_edificio",
}


_EVENTOS_DEL_2B = {
    "ingreso_exitoso",
    "ingreso_fallido",
    "alta_inicial",
    "invitar_personal",
    "dar_de_alta_vecino",
    "aceptar_invitacion",
    "revocar_invitacion",
    "quitar_asignacion",
}


def test_base_vacia_con_upgrade_head_y_arranque_real(
    base_del_edificio: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # La fixture crea una base propia desde cero y corre dos up completos.
    assert _NUEVAS <= {a.value for a in Accion}
    with base_del_edificio.conectar_app() as app:
        assert {f[0] for f in app.execute("SELECT nombre FROM accion_de_auditoria").fetchall()} == (
            {a.value for a in Accion} | _EVENTOS_DEL_2B | {e.value for e in EventoDelPadron}
        )
        assert (
            app.execute(
                "SELECT conname FROM pg_constraint WHERE contype = 'f' "
                "AND confrelid = 'auditoria'::regclass"
            ).fetchall()
            == []
        )
    for variable, valor in {
        "POSTGRES_HOST": base_del_edificio.contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(base_del_edificio.contenedor.get_exposed_port(5432)),
        "POSTGRES_DB": base_del_edificio.nombre,
        "POSTGRES_APP_USER": APP_USER_DE_SESION,
        "POSTGRES_APP_PASSWORD": APP_PASSWORD_DE_SESION,
    }.items():
        monkeypatch.setenv(variable, valor)
    from proptech_api.app import crear_app

    app_real = crear_app()
    with TestClient(app_real):
        with app_real.state.engine.connect() as conexion:
            assert conexion.execute(text("SELECT current_user")).scalar_one() == "proptech_app"


def test_migraciones_de_vocabulario_no_importan_accion() -> None:
    versiones = Path(__file__).resolve().parents[2] / "migraciones" / "versions"
    for nombre in (
        "0004_auditoria.py",
        "0010_acciones_de_configuracion.py",
        "0020_invitaciones.py",
        "0022_eventos_del_padron.py",
    ):
        arbol = ast.parse((versiones / nombre).read_text())
        assert not any(
            isinstance(nodo, (ast.Import, ast.ImportFrom))
            and any("Accion" in alias.name or "permisos" in alias.name for alias in nodo.names)
            for nodo in ast.walk(arbol)
        ), f"{nombre} importa el vocabulario vivo"


def test_downgrade_y_upgrade_con_listas_separadas(base_del_edificio: BaseDeEdificio) -> None:
    assert _NUEVAS <= {a.value for a in Accion}
    base_del_edificio.migrar("downgrade", "0004")
    try:
        with base_del_edificio.conectar_app() as app:
            assert {
                f[0] for f in app.execute("SELECT nombre FROM accion_de_auditoria").fetchall()
            } == {a.value for a in Accion} - _NUEVAS
    finally:
        base_del_edificio.migrar("upgrade", "head")
    with base_del_edificio.conectar_app() as app:
        assert {f[0] for f in app.execute("SELECT nombre FROM accion_de_auditoria").fetchall()} == (
            {a.value for a in Accion} | _EVENTOS_DEL_2B | {e.value for e in EventoDelPadron}
        )
