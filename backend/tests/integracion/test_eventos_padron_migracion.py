"""Vocabulario persistido y el punto de no retorno de 0022."""

from uuid import uuid4

import psycopg
import pytest

from proptech_core.acceso.dominio.eventos import EventoDelPadron

from ._edificios import BaseDeEdificio
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion


def test_vocabulario_y_bajada(base_para_migraciones: BaseDeEdificio) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "0021")
    with arranque(base) as c:
        anterior = c.execute("SELECT nombre FROM accion_de_auditoria ORDER BY nombre").fetchall()
        base.migrar("upgrade", "0022")
        #: `editar_edificio` (D3, tarea 3.7) llega recién en `0025` — acá sólo
        #: se prueba el vocabulario que `0022` sembró, no el de `EventoDelPadron`
        #: entero (que ya incluye eventos de migraciones posteriores).
        vocabulario = {f[0] for f in c.execute("SELECT nombre FROM accion_de_auditoria")}
        assert {e.value for e in EventoDelPadron if e is not EventoDelPadron.EDITAR_EDIFICIO} <= (
            vocabulario
        )
        base.migrar("upgrade", "0025")
        vocabulario = {f[0] for f in c.execute("SELECT nombre FROM accion_de_auditoria")}
        assert {e.value for e in EventoDelPadron} <= vocabulario

        def insertar(evento: str) -> None:
            c.execute(
                "INSERT INTO auditoria (administracion_id,persona_id,accion,entidad,"
                "entidad_id,request_id) VALUES (%s,%s,%s,'unidad',%s,%s)",
                (uuid4(), uuid4(), evento, uuid4(), uuid4()),
            )

        for evento in EventoDelPadron:
            with c.transaction(force_rollback=True):
                insertar(evento.value)
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            insertar("evento_inventado")
        base.migrar("downgrade", "0021")
        assert (
            c.execute("SELECT nombre FROM accion_de_auditoria ORDER BY nombre").fetchall()
            == anterior
        )
        base.migrar("upgrade", "0022")
        insertar("editar_unidad")
        with pytest.raises(psycopg.errors.ForeignKeyViolation) as error:
            c.execute("DELETE FROM accion_de_auditoria WHERE nombre='editar_unidad'")
        assert error.value.sqlstate == "23503"
        with pytest.raises(AssertionError, match="ForeignKeyViolation"):
            base.migrar("downgrade", "0021")
