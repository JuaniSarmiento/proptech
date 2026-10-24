"""Tarea 1.0 de `acceso-de-desarrollo`: la carga del edificio de ejemplo,
reescrita sobre D1 del design (corre como `proptech_app`, nunca
`proptech_migrador`), llamando a los mismos casos de uso que la API.

Escenarios de `datos-semilla` (Primera carga / Segunda carga igual / Cambiar
los parámetros no hace fallar / Dos cargas a la vez / El ejemplo cambió en la
base / Otras administraciones no se tocan) y de `acceso-de-desarrollo` (La
carga corre como `proptech_app` / Ningún permiso nuevo sobre `auditoria`),
más la propiedad de diseño "sin tenant no escribe nada" (D1: `cargar()`
depende de que la `fabrica` tenga registrado `registrar_tenant_por_administracion`).

Nota de diseño de los tests: "Generales" MUST NOT poder borrarse, ni por SQL
(R3A-3, migración 0011) y `auditoria` MUST NOT admitir DELETE para ningún rol
(D9, migración 0004) -- las dos cosas que la propia carga del ejemplo deja
escritas. Por eso el ciclo de vida completo (primera carga -> segunda carga
igual -> cambiar parámetros -> unidad editada) vive en UN solo test, sobre la
base compartida del módulo (D2a, conftest.py): no hay forma de "deshacer" el
ejemplo entre tests sin violar esas dos protecciones. "Dos cargas a la vez" y
"sin tenant" sí necesitan ver la administración de ejemplo todavía sin
cargar, así que usan `base_fresca`, una base propia y nueva por test.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
import sqlalchemy.exc
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import abrir_sesion, registrar_tenant_por_administracion
from proptech_core.compartido.parametros import leer_parametros
from proptech_core.compartido.semilla import leer_semilla
from proptech_core.complejos.aplicacion import ejemplo

from ..conftest import MIGRADOR_PASSWORD_DE_SESION, MIGRADOR_USER_DE_SESION
from ._api_edificios import ApiEdificio
from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion

_RAIZ = Path(__file__).resolve().parents[3]
_PARAMETROS = _RAIZ / "config" / "parametros.yaml"
_SEMILLA = _RAIZ / "config" / "semilla" / "edificio-ejemplo.yaml"


def _parametros():
    return leer_parametros(str(_PARAMETROS))


def _semilla():
    return leer_semilla(str(_SEMILLA), _parametros())


def _contar(fabrica, tabla: str, admin_id) -> int:
    # `api_edificio.filas()` fija el tenant al admin PROPIO de ese fixture
    # (D4): para contar filas de la administración de ejemplo (otro tenant)
    # hay que abrir una sesión con SU id, no reusar esa conexión.
    with abrir_sesion(fabrica, admin_id) as sesion:
        return sesion.execute(
            text(f"SELECT count(*) FROM {tabla} WHERE administracion_id = :id"),  # noqa: S608
            {"id": admin_id},
        ).scalar_one()


@pytest.fixture
def base_fresca(
    postgres_contenedor: PostgresContainer, roles_reales: None
) -> Iterator[BaseDeEdificio]:
    """Una base propia por test (a diferencia de `base_del_edificio` del
    conftest, por módulo): "dos cargas a la vez" y "sin tenant" necesitan ver
    la administración de ejemplo todavía sin cargar, y acá no hay forma de
    "vaciar" una base que ya la tiene (nota del docstring del módulo)."""
    nombre = f"proptech_ejemplo_{uuid4().hex}"
    with psycopg.connect(
        host=postgres_contenedor.get_container_host_ip(),
        port=postgres_contenedor.get_exposed_port(5432),
        user=postgres_contenedor.username,
        password=postgres_contenedor.password,
        dbname=postgres_contenedor.dbname,
        autocommit=True,
    ) as arranque:
        arranque.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(nombre), sql.Identifier(MIGRADOR_USER_DE_SESION)
            )
        )
        base = BaseDeEdificio(
            postgres_contenedor,
            nombre,
            {
                **os.environ,
                "POSTGRES_HOST": postgres_contenedor.get_container_host_ip(),
                "POSTGRES_PORT": str(postgres_contenedor.get_exposed_port(5432)),
                "POSTGRES_DB": nombre,
                "POSTGRES_MIGRADOR_USER": MIGRADOR_USER_DE_SESION,
                "POSTGRES_MIGRADOR_PASSWORD": MIGRADOR_PASSWORD_DE_SESION,
            },
        )
        try:
            base.roles("antes")
            base.migrar("upgrade", "head")
            base.roles("despues")
            yield base
        finally:
            arranque.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(nombre)))


def _fabrica_app(base: BaseDeEdificio) -> tuple:
    def _conectar() -> object:
        conexion = base.conectar_app()
        conexion.autocommit = False
        return conexion

    engine = create_engine("postgresql+psycopg://", creator=_conectar, poolclass=NullPool)
    fabrica = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    registrar_tenant_por_administracion(fabrica)
    return engine, fabrica


def test_ciclo_completo_de_carga_del_ejemplo(api_edificio: ApiEdificio) -> None:
    """Primera carga / segunda carga igual / cambiar parámetros no hace
    fallar / otras administraciones no se tocan / el ejemplo cambió en la
    base -- en ese orden, sobre la misma base compartida del módulo (ver el
    docstring del archivo: no hay forma de deshacer entre tests)."""
    fabrica = api_edificio.app.state.fabrica_de_sesiones

    # --- "Otras administraciones no se tocan": estado de ANTES de cargar ---
    antes_admin = api_edificio.filas("SELECT nombre, id FROM administracion")
    antes_complejos = api_edificio.filas(
        "SELECT nombre, estado_migracion FROM complejo ORDER BY nombre"
    )
    antes_unidades = api_edificio.filas(
        "SELECT identificador, coeficiente::text FROM unidad ORDER BY identificador"
    )

    # --- Primera carga ---
    primera = ejemplo.cargar(
        fabrica, parametros=_parametros(), semilla=_semilla(), request_id=uuid4()
    )
    assert primera.hizo_algo is True
    assert primera.administracion_id == ejemplo.ADMINISTRACION_EJEMPLO_ID
    assert _contar(fabrica, "persona", primera.administracion_id) == 1
    assert _contar(fabrica, "unidad", primera.administracion_id) == 13

    with abrir_sesion(fabrica, primera.administracion_id) as sesion:
        assert sesion.execute(text("SELECT rol FROM asignacion_rol")).scalar_one() == "super_admin"
        assert (
            sesion.execute(
                text("SELECT estado_migracion FROM complejo WHERE id=:id"),
                {"id": primera.complejo_id},
            ).scalar_one()
            == "sin_saldos_previos"
        )
        acciones = sesion.execute(text("SELECT accion FROM auditoria")).scalars().all()
        assert "alta_inicial" in acciones
        assert "crear_edificio" in acciones
        assert "confirmar_sin_saldos_previos" in acciones
        grupos = (
            sesion.execute(
                text("SELECT clave FROM grupo_de_reparto WHERE complejo_id=:id ORDER BY clave"),
                {"id": primera.complejo_id},
            )
            .scalars()
            .all()
        )
        assert grupos == ["ascensor", "cocheras", "generales"]
        assert sesion.execute(text("SELECT current_user")).scalar_one() == "proptech_app"

    # --- Otras administraciones no se tocan (después de la primera carga) ---
    assert api_edificio.filas("SELECT nombre, id FROM administracion") == antes_admin
    assert (
        api_edificio.filas("SELECT nombre, estado_migracion FROM complejo ORDER BY nombre")
        == antes_complejos
    )
    assert (
        api_edificio.filas(
            "SELECT identificador, coeficiente::text FROM unidad ORDER BY identificador"
        )
        == antes_unidades
    )

    # --- Segunda carga igual: no cambia nada ---
    conteos_antes = {
        tabla: _contar(fabrica, tabla, primera.administracion_id)
        for tabla in ("persona", "unidad", "grupo_de_reparto", "asignacion_rol")
    }
    segunda = ejemplo.cargar(
        fabrica, parametros=_parametros(), semilla=_semilla(), request_id=uuid4()
    )
    assert segunda.hizo_algo is False
    assert segunda.administracion_id == primera.administracion_id
    assert segunda.complejo_id == primera.complejo_id
    for tabla, cantidad in conteos_antes.items():
        assert _contar(fabrica, tabla, primera.administracion_id) == cantidad

    # --- Cambiar los parámetros no hace fallar la carga ---
    import tempfile

    texto = _PARAMETROS.read_text(encoding="utf-8")
    assert 'tasa_mensual: "3.00"' in texto
    with tempfile.TemporaryDirectory() as directorio:
        alterado = Path(directorio) / "parametros.yaml"
        alterado.write_text(
            texto.replace('tasa_mensual: "3.00"', 'tasa_mensual: "7.00"'), encoding="utf-8"
        )
        parametros_nuevos = leer_parametros(str(alterado))
        tercera = ejemplo.cargar(
            fabrica,
            parametros=parametros_nuevos,
            semilla=leer_semilla(str(_SEMILLA), parametros_nuevos),
            request_id=uuid4(),
        )
    assert tercera.hizo_algo is False
    assert tercera.complejo_id == primera.complejo_id
    with abrir_sesion(fabrica, primera.administracion_id) as sesion:
        tasa = sesion.execute(
            text("SELECT tasa_mensual::text FROM configuracion_versionada WHERE complejo_id=:id"),
            {"id": primera.complejo_id},
        ).scalar_one()
        assert tasa == "3.00"

    # --- El ejemplo cambió en la base: falla sin escribir, dice qué difiere ---
    with abrir_sesion(fabrica, primera.administracion_id) as sesion:
        sesion.execute(
            text(
                "UPDATE unidad SET coeficiente='0.999999' "
                "WHERE complejo_id=:id AND identificador='1A'"
            ),
            {"id": primera.complejo_id},
        )
        sesion.commit()

    with pytest.raises(ejemplo.EjemploDistinto, match=r"unidades\[1A\]"):
        ejemplo.cargar(fabrica, parametros=_parametros(), semilla=_semilla(), request_id=uuid4())

    with abrir_sesion(fabrica, primera.administracion_id) as sesion:
        coeficiente = sesion.execute(
            text(
                "SELECT coeficiente::text FROM unidad WHERE complejo_id=:id AND identificador='1A'"
            ),
            {"id": primera.complejo_id},
        ).scalar_one()
        # Nada más se escribió: la comparación avisa, no corrige.
        assert coeficiente == "0.999999"
        assert sesion.execute(text("SELECT count(*) FROM unidad")).scalar_one() == 13


def test_dos_cargas_en_paralelo_dejan_un_solo_ejemplo(base_fresca: BaseDeEdificio) -> None:
    parametros = _parametros()
    semilla = _semilla()
    resultados: list[object] = [None, None]

    def _correr(indice: int) -> None:
        engine, fabrica = _fabrica_app(base_fresca)
        try:
            resultados[indice] = ejemplo.cargar(
                fabrica, parametros=parametros, semilla=semilla, request_id=uuid4()
            )
        except Exception as error:
            resultados[indice] = error
        finally:
            engine.dispose()

    hilos = [threading.Thread(target=_correr, args=(i,)) for i in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    for resultado in resultados:
        if isinstance(resultado, Exception):
            raise resultado

    assert {r.hizo_algo for r in resultados} == {True, False}  # type: ignore[union-attr]
    admin_id = resultados[0].administracion_id  # type: ignore[union-attr]
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        with abrir_sesion(fabrica, admin_id) as sesion:
            assert (
                sesion.execute(
                    text("SELECT count(*) FROM administracion WHERE id=:id"), {"id": admin_id}
                ).scalar_one()
                == 1
            )
        assert _contar(fabrica, "complejo", admin_id) == 1
        assert _contar(fabrica, "unidad", admin_id) == 13
    finally:
        engine.dispose()


def test_sin_tenant_registrado_no_escribe_nada(base_fresca: BaseDeEdificio) -> None:
    """Si la `fabrica` nunca registra el tenant (un futuro refactor que se
    olvida de `registrar_tenant_por_administracion`), la política de RLS
    rechaza la escritura con el tenant fijo de este módulo y no queda nada a
    medias (D1 de `acceso-de-desarrollo`): es la garantía de que no existe
    ningún camino de escritura que dependa de "confiar" en el tenant."""

    def _conectar() -> object:
        conexion = base_fresca.conectar_app()
        conexion.autocommit = False
        return conexion

    engine = create_engine("postgresql+psycopg://", creator=_conectar, poolclass=NullPool)
    try:
        fabrica_sin_tenant = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        # A propósito: NO se llama a registrar_tenant_por_administracion(fabrica_sin_tenant).
        with pytest.raises(sqlalchemy.exc.DBAPIError):
            ejemplo.cargar(
                fabrica_sin_tenant,
                parametros=_parametros(),
                semilla=_semilla(),
                request_id=uuid4(),
            )
        fabrica_con_tenant = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        registrar_tenant_por_administracion(fabrica_con_tenant)
        with abrir_sesion(fabrica_con_tenant, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion:
            assert sesion.execute(text("SELECT count(*) FROM administracion")).scalar_one() == 0
    finally:
        engine.dispose()
