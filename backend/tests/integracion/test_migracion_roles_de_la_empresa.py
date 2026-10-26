"""D5: conversión transaccional de todos los tenants, como roles reales."""

import importlib.util
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import Base

from ..conftest import IMAGEN_POSTGRES_PARA_TESTS, MIGRADOR_USER_DE_SESION
from ._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad

pytestmark = pytest.mark.integracion
_MIGRACION = (
    Path(__file__).resolve().parents[2] / "migraciones/versions/0017_roles_de_la_empresa.py"
)


@pytest.fixture(scope="module")
def postgres_roles() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username="proptech_test",
        password="proptech_test",  # noqa: S106 (sólo este contenedor de test)
    ) as contenedor:
        yield contenedor


@pytest.fixture
def base_roles(postgres_roles: PostgresContainer) -> Iterator[BaseDeEdificio]:
    c = postgres_roles
    nombre = "proptech_roles_" + uuid4().hex
    with psycopg.connect(
        host=c.get_container_host_ip(),
        port=c.get_exposed_port(5432),
        user=c.username,
        password=c.password,
        dbname=c.dbname,
        autocommit=True,
    ) as arranque:
        # roles antes necesita la base default para crear el dueño primero.
        entorno = {
            **os.environ,
            "POSTGRES_HOST": c.get_container_host_ip(),
            "POSTGRES_PORT": str(c.get_exposed_port(5432)),
            "POSTGRES_DB": c.dbname,
            "POSTGRES_MIGRADOR_USER": MIGRADOR_USER_DE_SESION,
            "POSTGRES_MIGRADOR_PASSWORD": "clave-migrador-de-sesion-no-real",
        }
        inicial = BaseDeEdificio(c, c.dbname, entorno)
        inicial.roles("antes")
        arranque.execute(
            psycopg.sql.SQL("CREATE DATABASE {} OWNER {}").format(
                psycopg.sql.Identifier(nombre), psycopg.sql.Identifier(MIGRADOR_USER_DE_SESION)
            )
        )
        base = BaseDeEdificio(c, nombre, {**entorno, "POSTGRES_DB": nombre})
        try:
            base.roles("antes")
            # Sin `roles despues` en 0016: desde el 4a ese paso verifica la
            # protección de la cabeza (el trigger por sentencia de 0021) y en
            # una revisión intermedia falla cerrado, a propósito. El deploy
            # sólo lo corre después de `upgrade head`; ninguna migración de
            # 0017 a la cabeza toca `auditoria`, sólo `accion_de_auditoria`.
            base.migrar("upgrade", "0016")
            yield base
        finally:
            arranque.execute(
                psycopg.sql.SQL("DROP DATABASE {}").format(psycopg.sql.Identifier(nombre))
            )


# admin, complejo, unidad, personas de las cinco formas viejas.
Legado = tuple[UUID, UUID, UUID, list[UUID]]


def _sembrar(base: BaseDeEdificio) -> list[Legado]:
    datos = []
    with base.conectar_app() as c, c.transaction():
        assert c.execute(
            "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        ).fetchone() == ("proptech_app", False, False)
        for _ in range(2):
            admin, complejo = uuid4(), uuid4()
            personas = [uuid4() for _ in range(5)]
            fijar_tenant(c, admin)
            c.execute("INSERT INTO administracion (id,nombre) VALUES (%s,'Ficticia')", (admin,))
            c.execute(
                "INSERT INTO complejo (id,administracion_id,nombre,localidad) "
                "VALUES (%s,%s,'Ficticio','Mendoza')",
                (complejo, admin),
            )
            unidad = insertar_unidad(c, admin, complejo)
            for persona, rol, nivel in zip(
                personas,
                ("titular", "colaborador", "colaborador", "consejo", "vecino"),
                (None, "editar", "ver", None, None),
                strict=True,
            ):
                c.execute(
                    "INSERT INTO persona (id,administracion_id,nombre) "
                    "VALUES (%s,%s,'Persona inventada')",
                    (persona, admin),
                )
                c.execute(
                    "INSERT INTO asignacion_rol "
                    "(administracion_id,persona_id,rol,complejo_id,unidad_id,nivel) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        admin,
                        persona,
                        rol,
                        None if rol == "titular" else complejo,
                        unidad if rol == "vecino" else None,
                        nivel,
                    ),
                )
            datos.append((admin, complejo, unidad, personas))
    return datos


def _catalogo(base: BaseDeEdificio) -> dict[str, list[tuple[object, ...]]]:
    consultas = {
        "columnas": "SELECT column_name,to_jsonb(c) - 'ordinal_position' - 'dtd_identifier' "
        "FROM information_schema.columns AS c "
        "WHERE table_schema='public' AND table_name='asignacion_rol' ORDER BY column_name",
        "constraints": "SELECT conname,contype,pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid='asignacion_rol'::regclass ORDER BY conname",
        "indices": "SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' "
        "AND tablename='asignacion_rol' ORDER BY indexname",
        "politicas": "SELECT policyname,permissive,roles,cmd,qual,with_check FROM pg_policies "
        "WHERE schemaname='public' AND tablename='asignacion_rol' ORDER BY policyname",
        "rls": "SELECT relrowsecurity,relforcerowsecurity FROM pg_class "
        "WHERE oid='asignacion_rol'::regclass",
    }
    with base.conectar_app() as c:
        return {nombre: c.execute(sql).fetchall() for nombre, sql in consultas.items()}


def _filas(
    base: BaseDeEdificio, datos: list[Legado], columna: str
) -> list[list[tuple[object, ...]]]:
    assert columna in ("nivel", "vinculo")
    with base.conectar_app() as c, c.transaction():
        resultado = []
        for admin, _, _, _ in datos:
            fijar_tenant(c, admin)
            resultado.append(
                c.execute(
                    psycopg.sql.SQL(
                        "SELECT persona_id,rol,complejo_id,unidad_id,{} FROM asignacion_rol "
                        "ORDER BY persona_id"
                    ).format(psycopg.sql.Identifier(columna))
                ).fetchall()
            )
            assert c.execute(
                "SELECT count(*) FROM asignacion_rol WHERE administracion_id <> %s", (admin,)
            ).fetchone() == (0,)
        return resultado


def _comprobar_conversion(base: BaseDeEdificio, datos: list[Legado]) -> None:
    filas = _filas(base, datos, "vinculo")
    for lote, (_, complejo, unidad, personas) in zip(filas, datos, strict=True):
        esperado = [
            (
                persona,
                rol,
                None if rol == "super_admin" else complejo,
                unidad if rol == "vecino" else None,
                "propietario" if rol == "vecino" else None,
            )
            for persona, rol in zip(
                personas,
                ("super_admin", "administrador", "auxiliar", "consejo", "vecino"),
                strict=True,
            )
        ]
        assert lote == sorted(esperado)
    # El dueño también debe volver a quedar filtrado por FORCE, sin tenant.
    with base.conectar_migrador() as c:
        assert c.execute("SELECT count(*) FROM asignacion_rol").fetchone() == (0,)

    catalogo = _catalogo(base)
    assert catalogo["rls"] == [(True, True)]
    assert "nivel" not in {fila[0] for fila in catalogo["columnas"]}
    assert {fila[0] for fila in catalogo["indices"]} == {
        "pk_asignacion_rol",
        "uq_asignacion_rol_persona_unidad",
        "uq_asignacion_rol_persona_alcance",
        "ix_asignacion_rol_persona",
    }


def test_upgrade_convierte_dos_administraciones_y_conserva_aislamiento(
    base_roles: BaseDeEdificio,
) -> None:
    datos = _sembrar(base_roles)
    base_roles.migrar("upgrade", "0017")
    _comprobar_conversion(base_roles, datos)


def _copia_que_falla_despues_de_convertir(base: BaseDeEdificio) -> None:
    original = _MIGRACION.read_text()
    # Copia previa real, aislada del archivo que usa Alembic (L-013).
    carpeta = _MIGRACION.parents[3] / ".git/informes-roles-bloque-a-v2"
    carpeta.mkdir(exist_ok=True)
    (carpeta / "0017-original.py").write_text(original)
    mutante = original.replace(
        '    op.drop_column("asignacion_rol", "nivel")',
        "    op.execute(\"DO $$ BEGIN RAISE EXCEPTION 'fallo tras convertir'; END $$\")\n"
        '    op.drop_column("asignacion_rol", "nivel")',
    )
    assert mutante != original
    (carpeta / "0017-raise.py").write_text(mutante)
    spec = importlib.util.spec_from_file_location(
        "migracion_roles_mutada", carpeta / "0017-raise.py"
    )
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    def conectar() -> psycopg.Connection:
        c = base.conectar_migrador()
        c.autocommit = False
        return c

    motor = create_engine("postgresql+psycopg://", creator=conectar, poolclass=NullPool)
    try:
        with (
            motor.begin() as conexion,
            Operations.context(
                MigrationContext.configure(conexion, opts={"target_metadata": Base.metadata})
            ),
        ):
            modulo.upgrade()
    finally:
        motor.dispose()


def test_error_tras_convertir_revierte_filas_esquema_y_force(base_roles: BaseDeEdificio) -> None:
    datos = _sembrar(base_roles)
    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
    with pytest.raises(Exception, match="fallo tras convertir"):
        _copia_que_falla_despues_de_convertir(base_roles)
    assert _catalogo(base_roles) == catalogo
    assert _filas(base_roles, datos, "nivel") == filas
    with base_roles.conectar_app() as c:
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0016",)


def test_vecino_repetido_aborta_sin_cambiar_nada_ni_publicar_ids(
    base_roles: BaseDeEdificio,
) -> None:
    datos = _sembrar(base_roles)
    admin, complejo, unidad, personas = datos[1]
    with base_roles.conectar_app() as c, c.transaction():
        fijar_tenant(c, admin)
        c.execute(
            "INSERT INTO asignacion_rol (administracion_id,persona_id,rol,complejo_id,unidad_id) "
            "VALUES (%s,%s,'vecino',%s,%s)",
            (admin, personas[4], complejo, unidad),
        )
    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
    with pytest.raises(AssertionError, match="relaciones repetidas: 1") as error:
        base_roles.migrar("upgrade", "0017")
    assert all(str(id_) not in str(error.value) for lote in datos for id_ in lote[:3])
    assert all(str(p) not in str(error.value) for lote in datos for p in lote[3])
    assert "Persona inventada" not in str(error.value)
    assert _catalogo(base_roles) == catalogo
    assert _filas(base_roles, datos, "nivel") == filas


def _persona(c: psycopg.Connection, admin: UUID) -> UUID:
    persona = uuid4()
    c.execute(
        "INSERT INTO persona (id,administracion_id,nombre) VALUES (%s,%s,'Perfil ficticio')",
        (persona, admin),
    )
    return persona


def _asignar(
    c: psycopg.Connection,
    admin: UUID,
    persona: UUID,
    rol: str,
    complejo: UUID | None,
    unidad: UUID | None = None,
    vinculo: str | None = None,
) -> None:
    c.execute(
        "INSERT INTO asignacion_rol "
        "(administracion_id,persona_id,rol,complejo_id,unidad_id,vinculo) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (admin, persona, rol, complejo, unidad, vinculo),
    )


def _asignar_devolviendo_id(
    c: psycopg.Connection,
    admin: UUID,
    persona: UUID,
    rol: str,
    complejo: UUID | None,
    unidad: UUID | None = None,
    vinculo: str | None = None,
) -> UUID:
    fila = c.execute(
        "INSERT INTO asignacion_rol "
        "(administracion_id,persona_id,rol,complejo_id,unidad_id,vinculo) "
        "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (admin, persona, rol, complejo, unidad, vinculo),
    ).fetchone()
    assert fila is not None
    return UUID(str(fila[0]))


def test_las_nueve_formas_validas_entran_como_app(base_roles: BaseDeEdificio) -> None:
    datos = _sembrar(base_roles)
    base_roles.migrar("upgrade", "head")
    with base_roles.conectar_app() as c, c.transaction():
        for admin, complejo, unidad, _ in datos:
            fijar_tenant(c, admin)
            formas = [
                ("super_admin", None, None, None),
                ("administrador", None, None, None),
                ("administrador", complejo, None, None),
                ("contador", None, None, None),
                ("contador", complejo, None, None),
                ("auxiliar", complejo, None, None),
                ("consejo", complejo, None, None),
                ("vecino", complejo, unidad, "propietario"),
                ("vecino", complejo, unidad, "inquilino"),
            ]
            for rol, edificio, u, vinculo in formas:
                persona = _persona(c, admin)
                _asignar(c, admin, persona, rol, edificio, u, vinculo)
                assert c.execute(
                    "SELECT rol,complejo_id,unidad_id,vinculo FROM asignacion_rol "
                    "WHERE persona_id=%s",
                    (persona,),
                ).fetchall() == [(rol, edificio, u, vinculo)]


def test_cada_forma_invalida_falla_por_check_y_no_deja_filas(base_roles: BaseDeEdificio) -> None:
    datos = _sembrar(base_roles)
    base_roles.migrar("upgrade", "head")
    with base_roles.conectar_app() as c, c.transaction():
        for admin, complejo, unidad, _ in datos:
            fijar_tenant(c, admin)
            formas = [
                ("super_admin", complejo, None, None),
                ("super_admin", None, unidad, None),
                ("super_admin", None, None, "propietario"),
                ("administrador", complejo, unidad, None),
                ("administrador", None, None, "propietario"),
                ("contador", complejo, unidad, None),
                ("contador", None, None, "inquilino"),
                ("auxiliar", None, None, None),
                ("auxiliar", complejo, unidad, None),
                ("auxiliar", complejo, None, "propietario"),
                ("consejo", None, None, None),
                ("consejo", complejo, unidad, None),
                ("consejo", complejo, None, "inquilino"),
                ("vecino", None, unidad, "propietario"),
                ("vecino", complejo, None, "propietario"),
                ("vecino", complejo, unidad, None),
                ("vecino", complejo, unidad, "inventado"),
                ("titular", None, None, None),
                ("colaborador", complejo, None, None),
                ("inventado", complejo, None, None),
            ]
            for rol, edificio, u, vinculo in formas:
                persona = _persona(c, admin)
                with pytest.raises(psycopg.errors.CheckViolation), c.transaction():
                    _asignar(c, admin, persona, rol, edificio, u, vinculo)
                assert c.execute(
                    "SELECT count(*) FROM asignacion_rol WHERE persona_id=%s", (persona,)
                ).fetchone() == (0,)


def test_unicidad_de_vecino_y_de_todas_las_combinaciones_de_personal(
    base_roles: BaseDeEdificio,
) -> None:
    datos = _sembrar(base_roles)
    base_roles.migrar("upgrade", "head")
    with base_roles.conectar_app() as c, c.transaction():
        for admin, complejo, unidad, _ in datos:
            fijar_tenant(c, admin)
            persona = _persona(c, admin)
            _asignar(c, admin, persona, "vecino", complejo, unidad, "propietario")
            with (
                pytest.raises(
                    psycopg.errors.UniqueViolation, match="uq_asignacion_rol_persona_unidad"
                ),
                c.transaction(),
            ):
                _asignar(c, admin, persona, "vecino", complejo, unidad, "inquilino")
            assert c.execute(
                "SELECT vinculo FROM asignacion_rol WHERE persona_id=%s", (persona,)
            ).fetchall() == [("propietario",)]
            for edificio, roles in [
                (None, ("super_admin", "administrador", "contador")),
                (complejo, ("administrador", "contador", "auxiliar")),
            ]:
                for primero in roles:
                    for segundo in roles:
                        persona = _persona(c, admin)
                        _asignar(c, admin, persona, primero, edificio)
                        with (
                            pytest.raises(
                                psycopg.errors.UniqueViolation,
                                match="uq_asignacion_rol_persona_alcance",
                            ),
                            c.transaction(),
                        ):
                            _asignar(c, admin, persona, segundo, edificio)
                        assert c.execute(
                            "SELECT rol FROM asignacion_rol WHERE persona_id=%s", (persona,)
                        ).fetchall() == [(primero,)]


def test_consejo_repetido_en_el_mismo_edificio_falla_por_indice_unico(
    base_roles: BaseDeEdificio,
) -> None:
    """Corrección RR-3 (rompedor, BAJA): `uq_asignacion_rol_persona_alcance`
    (0017) excluye a propósito el rol `consejo` de su `WHERE` (RA-5, convive
    con un rol de personal), así que sin 0018 nada impedía dos filas de
    consejo de la misma persona en el mismo edificio. L-018: se prueba
    insertando como `proptech_app`, no leyendo el catálogo de índices."""
    datos = _sembrar(base_roles)
    base_roles.migrar("upgrade", "head")
    assert _catalogo(base_roles)["rls"] == [(True, True)]
    _filas(base_roles, datos, "vinculo")  # Lee ambos tenants y niega sus cruces.
    with base_roles.conectar_migrador() as c:
        assert c.execute("SELECT count(*) FROM asignacion_rol").fetchone() == (0,)
    with base_roles.conectar_app() as c, c.transaction():
        for admin, complejo, _, _ in datos:
            fijar_tenant(c, admin)
            persona = _persona(c, admin)
            _asignar(c, admin, persona, "consejo", complejo)
            with (
                pytest.raises(
                    psycopg.errors.UniqueViolation,
                    match="uq_asignacion_rol_consejo_persona_complejo",
                ),
                c.transaction(),
            ):
                _asignar(c, admin, persona, "consejo", complejo)
            assert c.execute(
                "SELECT count(*) FROM asignacion_rol WHERE persona_id=%s AND rol='consejo'",
                (persona,),
            ).fetchone() == (1,)
            # RA-5: consejo sigue conviviendo con un rol de personal en el
            # mismo edificio; el índice nuevo no toca esa combinación.
            _asignar(c, admin, persona, "administrador", complejo)
            assert c.execute(
                "SELECT rol FROM asignacion_rol WHERE persona_id=%s ORDER BY rol", (persona,)
            ).fetchall() == [("administrador",), ("consejo",)]


def test_consejo_previamente_repetido_aborta_sin_datos_personales_ni_cambios(
    base_roles: BaseDeEdificio,
) -> None:
    datos = _sembrar(base_roles)
    base_roles.migrar("upgrade", "0017")
    admin, complejo, _, personas = datos[1]  # El conflicto está en el segundo tenant.
    with base_roles.conectar_app() as c, c.transaction():
        fijar_tenant(c, admin)
        _asignar(c, admin, personas[3], "consejo", complejo)
    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "vinculo")
    with pytest.raises(AssertionError, match="consejos repetidos: 1") as error:
        base_roles.migrar("upgrade", "head")
    assert all(str(id_) not in str(error.value) for lote in datos for id_ in lote[:3])
    assert all(str(p) not in str(error.value) for lote in datos for p in lote[3])
    assert "Persona inventada" not in str(error.value)
    assert _catalogo(base_roles) == catalogo
    assert _filas(base_roles, datos, "vinculo") == filas
    with base_roles.conectar_app() as c:
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0017",)


def test_downgrade_de_0018_quita_el_indice_y_permite_el_duplicado(
    base_roles: BaseDeEdificio,
) -> None:
    """El `downgrade` de 0018 es sólo el índice (no transforma filas, a
    diferencia de 0017): comprobar que vuelve a permitir lo que el upgrade
    prohíbe, y que un nuevo upgrade lo vuelve a prohibir."""
    datos = _sembrar(base_roles)
    base_roles.migrar("upgrade", "head")
    catalogo_con_indice = _catalogo(base_roles)
    assert "uq_asignacion_rol_consejo_persona_complejo" in {
        fila[0] for fila in catalogo_con_indice["indices"]
    }
    base_roles.migrar("downgrade", "0017")
    assert "uq_asignacion_rol_consejo_persona_complejo" not in {
        fila[0] for fila in _catalogo(base_roles)["indices"]
    }
    admin, complejo, _, _ = datos[0]
    with base_roles.conectar_app() as c, c.transaction():
        fijar_tenant(c, admin)
        persona = _persona(c, admin)
        _asignar(c, admin, persona, "consejo", complejo)
        duplicado = _asignar_devolviendo_id(c, admin, persona, "consejo", complejo)
        assert c.execute(
            "SELECT count(*) FROM asignacion_rol WHERE persona_id=%s", (persona,)
        ).fetchone() == (2,)
        # Sacar el duplicado antes de volver a subir: 0018 no limpia datos
        # (a diferencia de 0017), así que el upgrade falla si ya hay dos.
        c.execute("DELETE FROM asignacion_rol WHERE id=%s", (duplicado,))
    base_roles.migrar("upgrade", "0018")
    with base_roles.conectar_app() as c, c.transaction():
        fijar_tenant(c, admin)
        with pytest.raises(psycopg.errors.UniqueViolation), c.transaction():
            _asignar(c, admin, persona, "consejo", complejo)
        assert c.execute(
            "SELECT count(*) FROM asignacion_rol WHERE persona_id=%s", (persona,)
        ).fetchone() == (1,)


def test_personal_coexiste_con_consejo_y_vecino_y_la_unidad_admite_tres_personas(
    base_roles: BaseDeEdificio,
) -> None:
    datos = _sembrar(base_roles)
    base_roles.migrar("upgrade", "head")
    with base_roles.conectar_app() as c, c.transaction():
        for admin, complejo, unidad, _ in datos:
            fijar_tenant(c, admin)
            for rol in ("administrador", "contador", "auxiliar"):
                persona = _persona(c, admin)
                _asignar(c, admin, persona, rol, complejo)
                _asignar(c, admin, persona, "consejo", complejo)
                _asignar(c, admin, persona, "vecino", complejo, unidad, "propietario")
                assert c.execute(
                    "SELECT rol FROM asignacion_rol WHERE persona_id=%s ORDER BY rol", (persona,)
                ).fetchall() == sorted([(rol,), ("consejo",), ("vecino",)])
            personas = [_persona(c, admin) for _ in range(3)]
            for persona, vinculo in zip(
                personas, ("propietario", "propietario", "inquilino"), strict=True
            ):
                _asignar(c, admin, persona, "vecino", complejo, unidad, vinculo)
            assert c.execute(
                "SELECT vinculo FROM asignacion_rol WHERE persona_id=ANY(%s) ORDER BY vinculo",
                (personas,),
            ).fetchall() == [("inquilino",), ("propietario",), ("propietario",)]


def test_downgrade_restaura_filas_y_catalogo_entero_y_permite_otro_upgrade(
    base_roles: BaseDeEdificio,
) -> None:
    datos = _sembrar(base_roles)
    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
    base_roles.migrar("upgrade", "0017")
    base_roles.migrar("downgrade", "0016")
    assert _filas(base_roles, datos, "nivel") == filas
    assert _catalogo(base_roles) == catalogo
    base_roles.migrar("upgrade", "0017")
    _comprobar_conversion(base_roles, datos)


@pytest.mark.parametrize(
    "tipo,cantidad,mensaje",
    [
        ("contador", 2, "contador=2, administrador_principal=0, inquilino=0"),
        ("administrador", 3, "contador=0, administrador_principal=3, inquilino=0"),
        ("inquilino", 4, "contador=0, administrador_principal=0, inquilino=4"),
    ],
)
def test_downgrade_rechaza_cada_tipo_nuevo_sin_cambiar_nada(
    base_roles: BaseDeEdificio,
    tipo: str,
    cantidad: int,
    mensaje: str,
) -> None:
    datos = _sembrar(base_roles)
    base_roles.migrar("upgrade", "0017")
    admin, complejo, unidad, _ = datos[1]
    personas = []
    with base_roles.conectar_app() as c, c.transaction():
        fijar_tenant(c, admin)
        for _ in range(cantidad):
            persona = _persona(c, admin)
            personas.append(persona)
            if tipo == "inquilino":
                _asignar(c, admin, persona, "vecino", complejo, unidad, "inquilino")
            else:
                _asignar(c, admin, persona, tipo, None)
    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "vinculo")
    with pytest.raises(AssertionError, match=mensaje) as error:
        base_roles.migrar("downgrade", "0016")
    assert all(str(id_) not in str(error.value) for lote in datos for id_ in lote[:3])
    assert all(str(p) not in str(error.value) for p in personas)
    assert "Perfil ficticio" not in str(error.value)
    assert _catalogo(base_roles) == catalogo
    assert _filas(base_roles, datos, "vinculo") == filas
    with base_roles.conectar_app() as c:
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0017",)


def test_downgrade_emite_lock_no_force_y_despues_chequea_conteos(
    base_roles: BaseDeEdificio,
) -> None:
    resultado = subprocess.run(
        ["uv", "run", "alembic", "downgrade", "0017:0016", "--sql"],
        cwd=_MIGRACION.parents[2],
        env=base_roles.entorno,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    salida = resultado.stdout
    assert (
        salida.index("LOCK TABLE asignacion_rol IN ACCESS EXCLUSIVE MODE")
        < salida.index("ALTER TABLE asignacion_rol NO FORCE ROW LEVEL SECURITY")
        < salida.index("contador=")
        < salida.index("UPDATE asignacion_rol")
        < salida.index("ALTER TABLE asignacion_rol FORCE ROW LEVEL SECURITY")
    )
    assert (
        salida.index("DROP INDEX uq_asignacion_rol_persona_unidad")
        < salida.index("DROP INDEX uq_asignacion_rol_persona_alcance")
        < salida.index("DROP INDEX ix_asignacion_rol_persona")
        < salida.index("DROP COLUMN vinculo")
    )


def test_personal_legado_repetido_aborta_con_conteo_sin_ids(base_roles: BaseDeEdificio) -> None:
    datos = _sembrar(base_roles)
    admin, complejo, _, personas = datos[1]
    for persona, rol, edificio, nivel in [
        (personas[0], "titular", None, None),
        (personas[1], "colaborador", complejo, "ver"),
    ]:
        with base_roles.conectar_app() as c, c.transaction():
            fijar_tenant(c, admin)
            fila = c.execute(
                "INSERT INTO asignacion_rol "
                "(administracion_id,persona_id,rol,complejo_id,nivel) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (admin, persona, rol, edificio, nivel),
            ).fetchone()
            assert fila is not None
            duplicado = fila[0]
        catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
        with pytest.raises(AssertionError, match="personal repetido: 1") as error:
            base_roles.migrar("upgrade", "0017")
        assert str(persona) not in str(error.value)
        assert str(admin) not in str(error.value)
        assert _catalogo(base_roles) == catalogo
        assert _filas(base_roles, datos, "nivel") == filas
        with base_roles.conectar_app() as c, c.transaction():
            fijar_tenant(c, admin)
            c.execute("DELETE FROM asignacion_rol WHERE id=%s", (duplicado,))
