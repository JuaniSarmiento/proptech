"""3.3: ida/vuelta real y retroceso bloqueado sin tocar auditoría (L-013/022/023)."""

import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

from ._catalogo_login import catalogo, comparar
from ._edificios import BaseDeEdificio, fijar_tenant
from ._login_db import preparar_personas
from .test_migracion_invitaciones import insertar

pytestmark = pytest.mark.integracion


def test_catalogo_completo_en_cada_revision_y_segundo_upgrade(
    base_del_edificio: BaseDeEdificio,
) -> None:
    base = base_del_edificio
    cabeza = catalogo(base)
    assert cabeza["invitacion"] is not None
    assert cabeza["invitacion.columna.vence"][1] is True  # attnotnull, no sólo tipo.
    base.migrar("downgrade", "0018")
    anterior = catalogo(base)
    assert anterior["invitacion"] is None
    assert "persona.columna.clerk_usuario_id" not in anterior
    base.migrar("upgrade", "0019")
    intermedia = catalogo(base)
    assert intermedia["invitacion"] is None
    assert "persona.columna.clerk_usuario_id" in intermedia
    base.migrar("upgrade", "0020")
    comparar(cabeza, catalogo(base))
    base.migrar("downgrade", "0019")
    comparar(intermedia, catalogo(base))
    base.migrar("downgrade", "0018")
    comparar(anterior, catalogo(base))
    base.migrar("upgrade", "head")
    comparar(cabeza, catalogo(base))


def test_downgrade_con_evento_nuevo_falla_sin_tocar_nada(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    datos = preparar_personas(base)
    with base.conectar_app() as c, c.transaction():
        fijar_tenant(c, datos.administraciones[0])
        invitacion, _ = insertar(c, datos.administraciones[0], datos.personas[0])
        auditoria = c.execute(
            "INSERT INTO auditoria "
            "(administracion_id,persona_id,accion,entidad,entidad_id,request_id) "
            "VALUES (%s,%s,'ingreso_exitoso','persona',%s,%s) RETURNING id",
            (datos.administraciones[0], datos.personas[0], datos.personas[0], uuid4()),
        ).fetchone()
        assert auditoria is not None
    antes = catalogo(base)
    resultado = subprocess.run(
        ["uv", "run", "alembic", "downgrade", "0019"],
        cwd=Path(__file__).resolve().parents[2],
        env=base.entorno,
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode != 0
    assert "fk_auditoria_accion" in resultado.stderr
    comparar(antes, catalogo(base))
    with base.conectar_app() as c, c.transaction():
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0020",)
        fijar_tenant(c, datos.administraciones[0])
        assert c.execute("SELECT id FROM invitacion").fetchall() == [(invitacion,)]
        assert c.execute("SELECT id,accion FROM auditoria").fetchall() == [
            (auditoria[0], "ingreso_exitoso")
        ]
