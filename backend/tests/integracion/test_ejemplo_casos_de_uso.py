"""Tarea 1.0 de `acceso-de-desarrollo`: la carga del edificio de ejemplo,
reescrita sobre D1 del design (corre como `proptech_app`, nunca
`proptech_migrador`), llamando a los mismos casos de uso que la API.

Escenarios de `datos-semilla` (Primera carga / Segunda carga igual / Cambiar
los parámetros no hace fallar / Dos cargas a la vez / El ejemplo cambió en la
base / Otras administraciones no se tocan) y de `acceso-de-desarrollo` (La
carga corre como `proptech_app`, vigilado por los tests del comando real al
final del archivo), más la propiedad de diseño "sin tenant no escribe nada"
(D1: `cargar()` depende de que la `fabrica` tenga registrado
`registrar_tenant_por_administracion`) y la guarda de entorno del comando.
"Ningún permiso nuevo sobre `auditoria`" no se mira acá: lo cubre
`test_auditoria_tabla.py`.

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
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
import sqlalchemy.exc
from psycopg import sql
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import (
    abrir_sesion,
    crear_engine,
    registrar_tenant_por_administracion,
)
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.georef import Georef, leer_georef
from proptech_core.compartido.parametros import Parametros, leer_parametros
from proptech_core.compartido.semilla import Semilla, leer_semilla
from proptech_core.complejos.aplicacion import ejemplo

from ..conftest import (
    APP_PASSWORD_DE_SESION,
    APP_USER_DE_SESION,
    MIGRADOR_PASSWORD_DE_SESION,
    MIGRADOR_USER_DE_SESION,
)
from ._api_edificios import ApiEdificio
from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion

_RAIZ = Path(__file__).resolve().parents[3]
_PARAMETROS = _RAIZ / "config" / "parametros.yaml"
_SEMILLA = _RAIZ / "config" / "semilla" / "edificio-ejemplo.yaml"
_GEOREF = _RAIZ / "config" / "georef"


def _parametros() -> Parametros:
    return leer_parametros(str(_PARAMETROS))


def _semilla() -> Semilla:
    return leer_semilla(str(_SEMILLA), _parametros(), _georef())


def _georef() -> Georef:
    return leer_georef(str(_GEOREF))


def _contar(fabrica: sessionmaker[Session], tabla: str, admin_id: UUID) -> int:
    # `api_edificio.filas()` fija el tenant al admin PROPIO de ese fixture
    # (D4): para contar filas de la administración de ejemplo (otro tenant)
    # hay que abrir una sesión con SU id, no reusar esa conexión.
    with abrir_sesion(fabrica, admin_id) as sesion:
        return int(
            sesion.execute(
                text(f"SELECT count(*) FROM {tabla} WHERE administracion_id = :id"),  # noqa: S608
                {"id": admin_id},
            ).scalar_one()
        )


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


def _fabrica_app(base: BaseDeEdificio) -> tuple[Engine, sessionmaker[Session]]:
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
        fabrica,
        parametros=_parametros(),
        semilla=_semilla(),
        georef=_georef(),
        request_id=uuid4(),
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
        fabrica,
        parametros=_parametros(),
        semilla=_semilla(),
        georef=_georef(),
        request_id=uuid4(),
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
            semilla=leer_semilla(str(_SEMILLA), parametros_nuevos, _georef()),
            georef=_georef(),
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
        ejemplo.cargar(
            fabrica,
            parametros=_parametros(),
            semilla=_semilla(),
            georef=_georef(),
            request_id=uuid4(),
        )

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
    resultados: list[ejemplo.ResultadoCarga | Exception | None] = [None, None]

    def _correr(indice: int) -> None:
        engine, fabrica = _fabrica_app(base_fresca)
        try:
            resultados[indice] = ejemplo.cargar(
                fabrica,
                parametros=parametros,
                semilla=semilla,
                georef=_georef(),
                request_id=uuid4(),
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

    cargas = [r for r in resultados if isinstance(r, ejemplo.ResultadoCarga)]
    assert len(cargas) == 2
    assert {r.hizo_algo for r in cargas} == {True, False}
    admin_id = cargas[0].administracion_id
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
                georef=_georef(),
                request_id=uuid4(),
            )
        fabrica_con_tenant = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        registrar_tenant_por_administracion(fabrica_con_tenant)
        with abrir_sesion(fabrica_con_tenant, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion:
            assert sesion.execute(text("SELECT count(*) FROM administracion")).scalar_one() == 0
    finally:
        engine.dispose()


# --- El comando real (`python -m proptech_core.complejos.aplicacion.ejemplo cargar`) ---
#
# Los tests de arriba llaman a `cargar()` con una fábrica que arma el propio
# test: no pueden dar rojo por nada que cambie en `_main` (QA-1, mutante M9 del
# PR #1). Estos corren el comando como lo corre una persona, contra una base
# propia, y miran el código de salida, el mensaje y lo que quedó escrito.

_BACKEND = Path(__file__).resolve().parents[2]


def _entorno_del_comando(
    base: BaseDeEdificio, *, usuario: str, clave: str, entorno: str | None
) -> dict[str, str]:
    """Sólo las credenciales de la app (nunca las del migrador como tales):
    si `_main` leyera otro par de variables, la carga no tendría con qué
    conectarse. `PROPTECH_ENTORNO` se quita siempre del entorno heredado y
    se pone sólo si el test lo pide (D-112, Juani 25/10/2026)."""
    variables = {
        clave_entorno: valor
        for clave_entorno, valor in os.environ.items()
        if not clave_entorno.startswith(("POSTGRES_", "PROPTECH_ENTORNO"))
    }
    variables.update(
        {
            "POSTGRES_HOST": base.contenedor.get_container_host_ip(),
            "POSTGRES_PORT": str(base.contenedor.get_exposed_port(5432)),
            "POSTGRES_DB": base.nombre,
            "POSTGRES_APP_USER": usuario,
            "POSTGRES_APP_PASSWORD": clave,
        }
    )
    if entorno is not None:
        variables["PROPTECH_ENTORNO"] = entorno
    return variables


def _correr_comando(variables: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "proptech_core.complejos.aplicacion.ejemplo", "cargar"],
        cwd=_BACKEND,
        env=variables,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _filas_escritas(base: BaseDeEdificio) -> dict[str, int]:
    """Con el superusuario del contenedor (sin RLS): cuenta TODO lo que hay,
    de cualquier administración, en las tablas que la carga escribiría."""
    with psycopg.connect(
        host=base.contenedor.get_container_host_ip(),
        port=base.contenedor.get_exposed_port(5432),
        user=base.contenedor.username,
        password=base.contenedor.password,
        dbname=base.nombre,
        autocommit=True,
    ) as conexion:
        conteos: dict[str, int] = {}
        for tabla in ("administracion", "persona", "complejo", "auditoria"):
            fila = conexion.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(tabla))
            ).fetchone()
            assert fila is not None
            conteos[tabla] = int(fila[0])
        return conteos


_SIN_ESCRITURAS = {"administracion": 0, "persona": 0, "complejo": 0, "auditoria": 0}


@pytest.mark.parametrize("entorno", [None, "produccion", "Desarrollo", " desarrollo "])
def test_el_comando_no_corre_fuera_de_desarrollo(
    base_fresca: BaseDeEdificio, entorno: str | None
) -> None:
    """Guarda de entorno (D-112): sin `PROPTECH_ENTORNO=desarrollo` el comando
    sale con error, dice por qué y no escribe nada en la base. La comparación es
    exacta: ni mayúsculas ni espacios alrededor cuentan como "desarrollo"."""
    assert _filas_escritas(base_fresca) == _SIN_ESCRITURAS

    resultado = _correr_comando(
        _entorno_del_comando(
            base_fresca,
            usuario=APP_USER_DE_SESION,
            clave=APP_PASSWORD_DE_SESION,
            entorno=entorno,
        )
    )

    assert resultado.returncode != 0, resultado.stdout
    assert "PROPTECH_ENTORNO=desarrollo" in resultado.stderr
    assert _filas_escritas(base_fresca) == _SIN_ESCRITURAS


def test_la_guarda_corre_antes_de_conectar_a_la_base() -> None:
    """Sin `PROPTECH_ENTORNO` y con una base inalcanzable, el comando sale por
    la guarda, sin intentar conectarse: si la guarda corriera después de
    conectar (por ejemplo, después de `verificar_rol_de_aplicacion_seguro`),
    lo que saldría es el error de conexión, no su mensaje (D-112)."""
    variables = {
        clave_entorno: valor
        for clave_entorno, valor in os.environ.items()
        if not clave_entorno.startswith(("POSTGRES_", "PROPTECH_ENTORNO"))
    }
    variables.update(
        {
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PORT": "1",
            "POSTGRES_DB": "proptech_inalcanzable",
            "POSTGRES_APP_USER": APP_USER_DE_SESION,
            "POSTGRES_APP_PASSWORD": APP_PASSWORD_DE_SESION,
        }
    )

    resultado = _correr_comando(variables)

    assert resultado.returncode == 1, resultado.stdout
    assert "PROPTECH_ENTORNO=desarrollo" in resultado.stderr, resultado.stderr[-2000:]
    assert "Traceback" not in resultado.stderr


def test_el_comando_real_carga_como_proptech_app_y_la_segunda_vez_dice_ya_estaba(
    base_fresca: BaseDeEdificio,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`_main` tal como lo llama `python -m` (QA-1, BE-5, DB-9): la conexión
    que arma el propio comando es `proptech_app`, la primera carga sale con 0
    y "ejemplo cargado", y la segunda con 0 y "ya estaba" sin escribir nada."""
    for variable, valor in _entorno_del_comando(
        base_fresca,
        usuario=APP_USER_DE_SESION,
        clave=APP_PASSWORD_DE_SESION,
        entorno="desarrollo",
    ).items():
        monkeypatch.setenv(variable, valor)

    usuarios: list[str] = []

    def _espia(configuracion: Configuracion) -> Engine:
        engine = crear_engine(configuracion)
        with engine.connect() as conexion:
            usuarios.append(str(conexion.execute(text("SELECT current_user")).scalar_one()))
        return engine

    monkeypatch.setattr(ejemplo, "crear_engine", _espia)

    assert ejemplo._main(["cargar"]) == 0
    primera = capsys.readouterr()
    assert "ejemplo cargado" in primera.out, primera.err
    assert usuarios == ["proptech_app"]
    escritas = _filas_escritas(base_fresca)
    assert escritas["administracion"] == 1
    assert escritas["complejo"] == 1

    assert ejemplo._main(["cargar"]) == 0
    segunda = capsys.readouterr()
    assert "ya estaba" in segunda.out, segunda.err
    assert usuarios == ["proptech_app", "proptech_app"]
    assert _filas_escritas(base_fresca) == escritas


def test_el_comando_real_se_niega_a_correr_como_el_migrador(base_fresca: BaseDeEdificio) -> None:
    """Con las credenciales del migrador puestas como las de la app, el
    comando sale con 1 por `RolDeAplicacionInseguro` (el control de `_main`,
    no un permiso que falte más adelante) y no escribe nada."""
    resultado = _correr_comando(
        _entorno_del_comando(
            base_fresca,
            usuario=MIGRADOR_USER_DE_SESION,
            clave=MIGRADOR_PASSWORD_DE_SESION,
            entorno="desarrollo",
        )
    )

    assert resultado.returncode == 1, resultado.stdout
    assert "RolDeAplicacionInseguro" in resultado.stderr, resultado.stderr[-2000:]
    assert _filas_escritas(base_fresca) == _SIN_ESCRITURAS
