"""D6/D7/D13: invitaciones y vocabulario como proptech_app (L-016/018)."""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg
import pytest

from ._edificios import BaseDeEdificio, fijar_tenant
from ._login_db import DatosDeLogin, preparar_personas

pytestmark = pytest.mark.integracion
EVENTOS = (
    "ingreso_exitoso",
    "ingreso_fallido",
    "alta_inicial",
    "invitar_personal",
    "dar_de_alta_vecino",
    "aceptar_invitacion",
    "revocar_invitacion",
    "quitar_asignacion",
)


def insertar(
    c: psycopg.Connection,
    admin: UUID,
    persona: UUID,
    *,
    creada_por: UUID | None = None,
    estado: str = "pendiente",
    resumen: bytes | None = None,
) -> tuple[UUID, bytes]:
    id_ = uuid4()
    resumen = resumen if resumen is not None else hashlib.sha256(id_.bytes).digest()
    c.execute(
        "INSERT INTO invitacion (id,administracion_id,persona_id,estado,token_resumen,"
        "vence,creada_por) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (
            id_,
            admin,
            persona,
            estado,
            resumen,
            datetime(2000, 1, 1, tzinfo=UTC),
            creada_por if creada_por is not None else persona,
        ),
    )
    return id_, resumen


@dataclass(frozen=True)
class Invitaciones:
    personas: DatosDeLogin
    ids: tuple[UUID, UUID, UUID]
    resumenes: tuple[bytes, bytes, bytes]


@pytest.fixture
def datos(base_del_edificio: BaseDeEdificio) -> Invitaciones:
    personas = preparar_personas(base_del_edificio)
    filas = []
    with base_del_edificio.conectar_app() as c, c.transaction():
        for admin, persona in zip(personas.administraciones, personas.personas, strict=True):
            fijar_tenant(c, admin)
            filas.append(insertar(c, admin, persona))
        filas.append(insertar(c, personas.administraciones[1], personas.persona_ajena))
    return Invitaciones(
        personas, (filas[0][0], filas[1][0], filas[2][0]), (filas[0][1], filas[1][1], filas[2][1])
    )


def test_tabla_y_aislamiento(base_del_edificio: BaseDeEdificio, datos: Invitaciones) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        assert c.execute(
            "SELECT current_user,rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"
        ).fetchone() == ("proptech_app", False, False)
        assert c.execute("SELECT * FROM invitacion").fetchall() == []
        fijar_tenant(c, datos.personas.administraciones[0])
        assert c.execute("SELECT id FROM invitacion").fetchall() == [(datos.ids[0],)]
        assert c.execute(
            "SELECT relrowsecurity,relforcerowsecurity FROM pg_class "
            "WHERE oid='invitacion'::regclass"
        ).fetchone() == (True, True)


@pytest.mark.parametrize("campo", ["persona_id", "creada_por"])
def test_fk_compuesta_no_acepta_persona_de_b(
    base_del_edificio: BaseDeEdificio, datos: Invitaciones, campo: str
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        admin = datos.personas.administraciones[0]
        fijar_tenant(c, admin)
        with pytest.raises(psycopg.errors.ForeignKeyViolation), c.transaction():
            insertar(
                c,
                admin,
                datos.personas.personas[1] if campo == "persona_id" else datos.personas.personas[0],
                creada_por=datos.personas.personas[1] if campo == "creada_por" else None,
                estado="revocada",
            )


@pytest.mark.parametrize(
    ("campo", "valor", "excepcion"),
    [
        ("estado", "inventado", psycopg.errors.CheckViolation),
        ("clerk_invitacion_id", "otro_x", psycopg.errors.CheckViolation),
        ("clerk_invitacion_id", "inv_ñ", psycopg.errors.CheckViolation),
        ("clerk_invitacion_id", "inv_x\n", psycopg.errors.CheckViolation),
        ("clerk_invitacion_id", "inv_", psycopg.errors.CheckViolation),
        ("vence", None, psycopg.errors.NotNullViolation),
    ],
)
def test_restricciones_de_escritura(
    base_del_edificio: BaseDeEdificio,
    datos: Invitaciones,
    campo: str,
    valor: str | None,
    excepcion: type[psycopg.Error],
) -> None:
    from psycopg import sql

    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, datos.personas.administraciones[0])
        with pytest.raises(excepcion), c.transaction():
            c.execute(
                sql.SQL("UPDATE invitacion SET {}=%s WHERE id=%s").format(sql.Identifier(campo)),
                (valor, datos.ids[0]),
            )


@pytest.mark.parametrize("estado", ["pendiente", "enviada", "fallida"])
def test_unica_abierta_incluso_vencida(
    base_del_edificio: BaseDeEdificio, datos: Invitaciones, estado: str
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        admin = datos.personas.administraciones[0]
        fijar_tenant(c, admin)
        c.execute("UPDATE invitacion SET estado=%s WHERE id=%s", (estado, datos.ids[0]))
        with pytest.raises(psycopg.errors.UniqueViolation), c.transaction():
            insertar(c, admin, datos.personas.personas[0])
        c.execute("UPDATE invitacion SET estado='revocada' WHERE id=%s", (datos.ids[0],))
        insertar(c, admin, datos.personas.personas[0], estado="aceptada")
        insertar(c, admin, datos.personas.personas[0])
        c.execute(
            "UPDATE invitacion SET clerk_invitacion_id='inv_Prueba123' WHERE id=%s", (datos.ids[0],)
        )


def test_resumen_unico_global(base_del_edificio: BaseDeEdificio, datos: Invitaciones) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, datos.personas.administraciones[1])
        with pytest.raises(psycopg.errors.UniqueViolation), c.transaction():
            insertar(
                c,
                datos.personas.administraciones[1],
                datos.personas.personas[1],
                estado="revocada",
                resumen=datos.resumenes[0],
            )


def test_lectura_por_hexadecimal_no_escribe_ni_filtra_columnas(
    base_del_edificio: BaseDeEdificio, datos: Invitaciones
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        c.execute("SELECT set_config('app.invitacion_token',%s,true)", (datos.resumenes[1].hex(),))
        # SELECT de columnas completas: la política protege filas, no columnas.
        fila = c.execute("SELECT id,persona_id,token_resumen,creada_por FROM invitacion").fetchall()
        assert fila == [
            (
                datos.ids[1],
                datos.personas.personas[1],
                datos.resumenes[1],
                datos.personas.personas[1],
            )
        ]
        for consulta in (
            "SELECT id FROM persona",
            "SELECT id FROM asignacion_rol",
            "SELECT id FROM complejo",
            "SELECT id FROM unidad",
        ):
            assert c.execute(consulta).fetchall() == []
        assert c.execute("UPDATE invitacion SET estado='aceptada' RETURNING id").fetchall() == []
        assert c.execute("DELETE FROM invitacion RETURNING id").fetchall() == []
        with pytest.raises(psycopg.errors.InsufficientPrivilege), c.transaction():
            insertar(c, datos.personas.administraciones[1], datos.personas.personas[1])


@pytest.mark.parametrize("resumen", [None, ""])
def test_sin_resumen_no_lee(
    base_del_edificio: BaseDeEdificio, datos: Invitaciones, resumen: str | None
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        if resumen is not None:
            c.execute("SELECT set_config('app.invitacion_token',%s,true)", (resumen,))
        assert c.execute("SELECT * FROM invitacion").fetchall() == []


def test_resumen_b_con_tenant_a_no_aporta_b(
    base_del_edificio: BaseDeEdificio, datos: Invitaciones
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, datos.personas.administraciones[0])
        c.execute("SELECT set_config('app.invitacion_token',%s,true)", (datos.resumenes[1].hex(),))
        assert c.execute("SELECT id,administracion_id FROM invitacion").fetchall() == [
            (datos.ids[0], datos.personas.administraciones[0])
        ]


def test_indices_y_explain_por_resumen(
    base_del_edificio: BaseDeEdificio, datos: Invitaciones
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        for admin, persona in zip(
            datos.personas.administraciones, datos.personas.personas, strict=True
        ):
            fijar_tenant(c, admin)
            for _ in range(1000):
                insertar(c, admin, persona, estado="revocada")
    with base_del_edificio.conectar_migrador() as c:
        c.execute("ANALYZE invitacion")
    with base_del_edificio.conectar_app() as c, c.transaction():
        assert c.execute("SELECT current_user").fetchone() == ("proptech_app",)
        c.execute("SELECT set_config('app.invitacion_token',%s,true)", (datos.resumenes[1].hex(),))
        plan = "\n".join(
            f[0]
            for f in c.execute(
                "EXPLAIN (COSTS OFF) SELECT id,administracion_id FROM invitacion "
                "WHERE token_resumen=%s",
                (datos.resumenes[1],),
            )
        )
        print("EXPLAIN resumen como proptech_app (RLS ENABLE/FORCE):\n" + plan)
        assert "uq_invitacion_token_resumen" in plan
        indices: dict[str, str] = dict(
            c.execute("SELECT indexname,indexdef FROM pg_indexes WHERE tablename='invitacion'")
        )
        assert indices["ix_invitacion_persona"].endswith("(administracion_id, persona_id)")
        assert indices["uq_invitacion_abierta"] == (
            "CREATE UNIQUE INDEX uq_invitacion_abierta ON public.invitacion USING btree "
            "(administracion_id, persona_id) WHERE (estado = ANY "
            "(ARRAY['pendiente'::text, 'enviada'::text, 'fallida'::text]))"
        )


def test_vocabulario_y_auditoria_aceptan_ocho_eventos(base_del_edificio: BaseDeEdificio) -> None:
    personas = preparar_personas(base_del_edificio)
    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, personas.administraciones[0])
        for evento in EVENTOS:
            c.execute(
                "INSERT INTO auditoria "
                "(administracion_id,persona_id,accion,entidad,entidad_id,request_id) "
                "VALUES (%s,%s,%s,'persona',%s,%s)",
                (
                    personas.administraciones[0],
                    personas.personas[0],
                    evento,
                    personas.personas[0],
                    uuid4(),
                ),
            )
        assert set(f[0] for f in c.execute("SELECT accion FROM auditoria")) == set(EVENTOS)
        assert set(
            f[0]
            for f in c.execute(
                "SELECT nombre FROM accion_de_auditoria WHERE nombre=ANY(%s)", (list(EVENTOS),)
            )
        ) == set(EVENTOS)
