"""D2: vínculo, lectura sin tenant y pool real (L-013/016/018/020)."""

from collections.abc import Iterator
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import QueuePool

from proptech_core.compartido.base_de_datos import (
    crear_fabrica_de_sesiones,
    registrar_reset_del_tenant_al_devolver,
    registrar_tenant_por_administracion,
)

from ._edificios import BaseDeEdificio, fijar_tenant
from ._login_db import DatosDeLogin, preparar_personas

pytestmark = pytest.mark.integracion


@pytest.fixture
def datos(base_del_edificio: BaseDeEdificio) -> DatosDeLogin:
    return preparar_personas(base_del_edificio)


@pytest.fixture
def engine_login(base_del_edificio: BaseDeEdificio) -> Iterator[Engine]:
    def conectar() -> psycopg.Connection:
        conexion = base_del_edificio.conectar_app()
        conexion.autocommit = False
        return conexion

    engine = create_engine(
        "postgresql+psycopg://", creator=conectar, pool_size=1, max_overflow=0, pool_timeout=1
    )
    registrar_reset_del_tenant_al_devolver(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def test_columna_en_head_y_unico_por_administracion(
    base_del_edificio: BaseDeEdificio, datos: DatosDeLogin
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, datos.administraciones[0])
        assert c.execute("SELECT current_user").fetchone() == ("proptech_app",)
        assert c.execute("SELECT clerk_usuario_id FROM persona").fetchall() == [(datos.sub,)]
        with pytest.raises(psycopg.errors.UniqueViolation), c.transaction():
            c.execute(
                "INSERT INTO persona (administracion_id,nombre,clerk_usuario_id) "
                "VALUES (%s,'Duplicada',%s)",
                (datos.administraciones[0], datos.sub),
            )
        c.execute(
            "INSERT INTO persona (administracion_id,nombre) VALUES (%s,'Sin vínculo'),(%s,'Otra')",
            (datos.administraciones[0], datos.administraciones[0]),
        )
        fijar_tenant(c, datos.administraciones[1])
        assert c.execute(
            "SELECT id FROM persona WHERE clerk_usuario_id=%s", (datos.sub,)
        ).fetchall() == [(datos.personas[1],)]


@pytest.mark.parametrize("sub", ["otra", "user_", "user_ñ", "user_x\n", "user_" + "a" * 65])
def test_check_de_forma_rechaza_escrituras(
    base_del_edificio: BaseDeEdificio, datos: DatosDeLogin, sub: str
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, datos.administraciones[0])
        with pytest.raises(psycopg.errors.CheckViolation), c.transaction():
            c.execute(
                "INSERT INTO persona (administracion_id,nombre,clerk_usuario_id) "
                "VALUES (%s,'Forma inválida',%s)",
                (datos.administraciones[0], sub),
            )


def test_sesion_por_identidad_solo_lee_sus_personas(
    engine_login: Engine, datos: DatosDeLogin
) -> None:
    from proptech_core.compartido.base_de_datos import abrir_sesion_por_identidad

    fabrica = crear_fabrica_de_sesiones(engine_login)
    registrar_tenant_por_administracion(fabrica)
    with abrir_sesion_por_identidad(fabrica, datos.sub) as sesion:
        for _ in range(2):
            assert set(sesion.execute(text("SELECT id,administracion_id FROM persona"))) == set(
                zip(datos.personas, datos.administraciones, strict=True)
            )
            # Son tablas con filas reales en ambas administraciones.
            for consulta in (
                "SELECT id FROM asignacion_rol",
                "SELECT id FROM complejo",
                "SELECT id FROM unidad",
            ):
                assert sesion.execute(text(consulta)).all() == []
            sesion.commit()


def test_por_identidad_no_escribe(base_del_edificio: BaseDeEdificio, datos: DatosDeLogin) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        c.execute("SELECT set_config('app.identidad_clerk',%s,true)", (datos.sub,))
        assert len(c.execute("SELECT * FROM persona").fetchall()) == 2
        assert (
            c.execute("UPDATE persona SET nombre='Cambio prohibido' RETURNING id").fetchall() == []
        )
        assert c.execute("DELETE FROM persona RETURNING id").fetchall() == []
        with pytest.raises(psycopg.errors.InsufficientPrivilege), c.transaction():
            c.execute(
                "INSERT INTO persona (administracion_id,nombre,clerk_usuario_id) "
                "VALUES (%s,'Prohibida',%s)",
                (datos.administraciones[0], "user_Nueva"),
            )


@pytest.mark.parametrize("identidad", [None, ""])
def test_identidad_ausente_o_vacia_no_lee(
    base_del_edificio: BaseDeEdificio, datos: DatosDeLogin, identidad: str | None
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        if identidad is not None:
            c.execute("SELECT set_config('app.identidad_clerk',%s,true)", (identidad,))
        assert c.execute("SELECT * FROM persona").fetchall() == []


def test_identidad_de_b_con_tenant_a_no_aporta_b(
    base_del_edificio: BaseDeEdificio, datos: DatosDeLogin
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, datos.administraciones[0])
        c.execute("SELECT set_config('app.identidad_clerk',%s,true)", (datos.sub_ajeno,))
        assert c.execute("SELECT id,administracion_id FROM persona").fetchall() == [
            (datos.personas[0], datos.administraciones[0])
        ]


@pytest.mark.parametrize("operacion", ["commit", "rollback"])
def test_pool_limpia_las_tres_variables(engine_login: Engine, operacion: str) -> None:
    with engine_login.connect() as c:
        pid = c.execute(text("SELECT pg_backend_pid()")).scalar_one()
        for variable, valor in (
            ("app.administracion_id", str(uuid4())),
            ("app.identidad_clerk", "user_Pool"),
            ("app.invitacion_token", "ab" * 32),
        ):
            c.execute(
                text("SELECT set_config(:variable,:valor,false)"),
                {"variable": variable, "valor": valor},
            )
        c.commit()  # SET sin LOCAL sobrevive al rollback siguiente.
        c.execute(text("SELECT 1"))
        getattr(c, operacion)()
    with engine_login.connect() as c:
        assert c.execute(text("SELECT pg_backend_pid()")).scalar_one() == pid
        for variable in ("app.administracion_id", "app.identidad_clerk", "app.invitacion_token"):
            assert c.execute(
                text("SELECT current_setting(:variable,true)"), {"variable": variable}
            ).scalar_one() in (None, "")


def test_pool_roto_descarta_y_recupera_una_sola_conexion(
    base_del_edificio: BaseDeEdificio, engine_login: Engine
) -> None:
    with engine_login.connect() as c:
        pid = c.execute(text("SELECT pg_backend_pid()")).scalar_one()
        for variable in ("app.administracion_id", "app.identidad_clerk", "app.invitacion_token"):
            c.execute(text("SELECT set_config(:variable,'residuo',false)"), {"variable": variable})
        c.commit()
        contenedor = base_del_edificio.contenedor
        with psycopg.connect(
            host=contenedor.get_container_host_ip(),
            port=contenedor.get_exposed_port(5432),
            dbname=base_del_edificio.nombre,
            user=contenedor.username,
            password=contenedor.password,
        ) as arranque:
            assert arranque.execute("SELECT pg_terminate_backend(%s)", (pid,)).fetchone() == (True,)
        with pytest.raises(OperationalError):
            c.execute(text("SELECT 1"))
    for _ in range(2):
        with engine_login.connect() as c:
            assert c.execute(text("SELECT pg_backend_pid()")).scalar_one() != pid
            for variable in (
                "app.administracion_id",
                "app.identidad_clerk",
                "app.invitacion_token",
            ):
                assert c.execute(
                    text("SELECT current_setting(:variable,true)"), {"variable": variable}
                ).scalar_one() in (None, "")
    assert isinstance(engine_login.pool, QueuePool)
    assert engine_login.pool.checkedout() == 0


def test_explain_identidad_usa_unico_con_clerk_primero(
    base_del_edificio: BaseDeEdificio, datos: DatosDeLogin
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        for admin in datos.administraciones:
            fijar_tenant(c, admin)
            c.execute(
                "INSERT INTO persona (administracion_id,nombre,clerk_usuario_id) "
                "SELECT %s,'Ficticia','user_' || %s || n::text "
                "FROM generate_series(1,2000) AS s(n)",
                (admin, uuid4().hex),
            )
    with base_del_edificio.conectar_migrador() as c:
        c.execute("ANALYZE persona")
    with base_del_edificio.conectar_app() as c, c.transaction():
        assert c.execute(
            "SELECT current_user,relrowsecurity,relforcerowsecurity FROM pg_class "
            "WHERE oid='persona'::regclass"
        ).fetchone() == ("proptech_app", True, True)
        c.execute("SELECT set_config('app.identidad_clerk',%s,true)", (datos.sub,))
        plan = "\n".join(
            f[0]
            for f in c.execute(
                "EXPLAIN (COSTS OFF) SELECT id,administracion_id FROM persona "
                "WHERE clerk_usuario_id=%s",
                (datos.sub,),
            )
        )
        print("EXPLAIN identidad como proptech_app (RLS ENABLE/FORCE):\n" + plan)
        assert "uq_persona_clerk_administracion" in plan
        assert "Index" in plan
        indice = c.execute(
            "SELECT pg_get_indexdef(indexrelid) FROM pg_index "
            "WHERE indexrelid='uq_persona_clerk_administracion'::regclass"
        ).fetchone()
        assert indice is not None
        assert indice[0].endswith("(clerk_usuario_id, administracion_id)")
