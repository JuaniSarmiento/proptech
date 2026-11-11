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

Los casos de comparación (`ejemplo-robusto`, D1) cargan el ejemplo una vez por
módulo en otra base (`ejemplo_cargado`) y llaman a `cargar()` con una copia
alterada de la semilla: la comparación falla antes de escribir, así que ningún
caso ensucia esa base y ninguno depende del orden.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import NoReturn, cast
from uuid import UUID, uuid4

import psycopg
import pytest
import sqlalchemy.exc
from psycopg import sql
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

from proptech_core.acceso.aplicacion.alta_inicial import crear_administracion_y_super_admin
from proptech_core.acceso.aplicacion.vinculacion_de_desarrollo import (
    VinculacionDeDesarrolloNoDisponible,
)
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.base_de_datos import (
    abrir_sesion,
    crear_engine,
    registrar_tenant_por_administracion,
)
from proptech_core.compartido.configuracion import (
    Configuracion,
    ConfiguracionDelEjemplo,
    ConfiguracionInvalida,
)
from proptech_core.compartido.georef import Georef, leer_georef
from proptech_core.compartido.parametros import Parametros, ParametrosInvalidos, leer_parametros
from proptech_core.compartido.semilla import Grupo, Semilla, leer_semilla
from proptech_core.compartido.superficie import Superficie
from proptech_core.complejos.aplicacion import ejemplo
from proptech_core.complejos.aplicacion.errores import EntradaInvalida
from proptech_core.complejos.aplicacion.escritura import crear_edificio
from proptech_core.complejos.aplicacion.grupos import crear_grupo
from proptech_core.complejos.aplicacion.unidades import crear_unidad

from ..conftest import (
    APP_PASSWORD_DE_SESION,
    APP_USER_DE_SESION,
    MIGRADOR_PASSWORD_DE_SESION,
    MIGRADOR_USER_DE_SESION,
)
from ._api_edificios import ApiEdificio
from ._clerk import clerk_falso as clerk_falso
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


@contextmanager
def _base_propia(contenedor: PostgresContainer) -> Iterator[BaseDeEdificio]:
    """Una base nueva y migrada, con sus roles, que se borra al salir."""
    nombre = f"proptech_ejemplo_{uuid4().hex}"
    with psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=contenedor.username,
        password=contenedor.password,
        dbname=contenedor.dbname,
        autocommit=True,
    ) as arranque:
        arranque.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(nombre), sql.Identifier(MIGRADOR_USER_DE_SESION)
            )
        )
        base = BaseDeEdificio(
            contenedor,
            nombre,
            {
                **os.environ,
                "POSTGRES_HOST": contenedor.get_container_host_ip(),
                "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
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


@pytest.fixture
def base_fresca(
    postgres_contenedor: PostgresContainer, roles_reales: None
) -> Iterator[BaseDeEdificio]:
    """Una base propia por test (a diferencia de `base_del_edificio` del
    conftest, por módulo): "dos cargas a la vez" y "sin tenant" necesitan ver
    la administración de ejemplo todavía sin cargar, y acá no hay forma de
    "vaciar" una base que ya la tiene (nota del docstring del módulo)."""
    with _base_propia(postgres_contenedor) as base:
        yield base


def _fabrica_app(base: BaseDeEdificio) -> tuple[Engine, sessionmaker[Session]]:
    def _conectar() -> object:
        conexion = base.conectar_app()
        conexion.autocommit = False
        return conexion

    engine = create_engine("postgresql+psycopg://", creator=_conectar, poolclass=NullPool)
    fabrica = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    registrar_tenant_por_administracion(fabrica)
    return engine, fabrica


@dataclass(frozen=True)
class _EjemploCargado:
    base: BaseDeEdificio
    fabrica: sessionmaker[Session]


@pytest.fixture(scope="module")
def ejemplo_cargado(
    postgres_contenedor: PostgresContainer, roles_reales: None
) -> Iterator[_EjemploCargado]:
    """Una sola carga por módulo, en una base propia que nadie edita (D1 de
    `ejemplo-robusto`): quien la use tiene que alterar la semilla, nunca la base."""
    with _base_propia(postgres_contenedor) as base:
        engine, fabrica = _fabrica_app(base)
        try:
            primera = ejemplo.cargar(
                fabrica,
                parametros=_parametros(),
                semilla=_semilla(),
                georef=_georef(),
                request_id=uuid4(),
            )
            assert primera.hizo_algo is True
            yield _EjemploCargado(base, fabrica)
        finally:
            engine.dispose()


_TABLAS_DEL_EJEMPLO = (
    "persona",
    "asignacion_rol",
    "complejo",
    "unidad",
    "grupo_de_reparto",
    "grupo_unidad",
    "auditoria",
)


def _conteos_del_ejemplo(fabrica: sessionmaker[Session]) -> dict[str, int]:
    return {
        tabla: _contar(fabrica, tabla, ejemplo.ADMINISTRACION_EJEMPLO_ID)
        for tabla in _TABLAS_DEL_EJEMPLO
    }


def _con_edificio(semilla: Semilla, **cambios: object) -> Semilla:
    return semilla.model_copy(update={"edificio": semilla.edificio.model_copy(update=cambios)})


def _con_unidad(semilla: Semilla, identificador: str, **cambios: object) -> Semilla:
    return semilla.model_copy(
        update={
            "unidades": [
                unidad.model_copy(update=cambios)
                if unidad.identificador == identificador
                else unidad
                for unidad in semilla.unidades
            ]
        }
    )


def _grupo(semilla: Semilla, clave: str) -> Grupo:
    grupo = semilla.grupos[clave]
    assert isinstance(grupo, Grupo)
    return grupo


def _con_grupo(semilla: Semilla, clave: str, grupo: Grupo) -> Semilla:
    return semilla.model_copy(update={"grupos": {**semilla.grupos, clave: grupo}})


def _otro_estado_de_migracion(semilla: Semilla) -> Semilla:
    return _con_edificio(semilla, estado_migracion="pendiente")


def _otro_modo_de_grupo(semilla: Semilla) -> Semilla:
    return _con_grupo(
        semilla, "ascensor", _grupo(semilla, "ascensor").model_copy(update={"modo": "propios"})
    )


def _otro_tipo_de_unidad(semilla: Semilla) -> Semilla:
    return _con_unidad(semilla, "1A", tipo="local")


def _otro_piso_de_unidad(semilla: Semilla) -> Semilla:
    return _con_unidad(semilla, "1A", piso="2")


def _otra_superficie_de_unidad(semilla: Semilla) -> Semilla:
    return _con_unidad(semilla, "1A", superficie_m2=Superficie("61.00"))


def _semilla_con_una_unidad_mas(semilla: Semilla) -> Semilla:
    extra = semilla.unidades[0].model_copy(update={"identificador": "9Z"})
    return semilla.model_copy(update={"unidades": [*semilla.unidades, extra]})


def _semilla_con_una_unidad_menos(semilla: Semilla) -> Semilla:
    return semilla.model_copy(
        update={"unidades": [u for u in semilla.unidades if u.identificador != "B1"]}
    )


def _semilla_con_un_grupo_mas(semilla: Semilla) -> Semilla:
    """Al ejemplo le falta un grupo. Con la rama apagada muere en un `KeyError`."""
    return _con_grupo(semilla, "servicios_centrales", _grupo(semilla, "cocheras"))


def _semilla_con_un_grupo_menos(semilla: Semilla) -> Semilla:
    """Al ejemplo le sobra un grupo: el caso que llega a la aserción con la rama apagada."""
    return semilla.model_copy(
        update={"grupos": {c: g for c, g in semilla.grupos.items() if c != "cocheras"}}
    )


def _semilla_con_un_miembro_mas(semilla: Semilla) -> Semilla:
    grupo = _grupo(semilla, "ascensor")
    extra = grupo.unidades[0].model_copy(update={"identificador": "C1"})
    return _con_grupo(
        semilla, "ascensor", grupo.model_copy(update={"unidades": [*grupo.unidades, extra]})
    )


def _semilla_con_un_miembro_menos(semilla: Semilla) -> Semilla:
    grupo = _grupo(semilla, "ascensor")
    return _con_grupo(
        semilla,
        "ascensor",
        grupo.model_copy(
            update={"unidades": [m for m in grupo.unidades if m.identificador != "4B"]}
        ),
    )


def _con_coeficiente_de_miembro(semilla: Semilla, clave: str, coeficiente: Decimal) -> Semilla:
    grupo = _grupo(semilla, clave)
    primero, *resto = grupo.unidades
    return _con_grupo(
        semilla,
        clave,
        grupo.model_copy(
            update={"unidades": [primero.model_copy(update={"coeficiente": coeficiente}), *resto]}
        ),
    )


def _semilla_con_coeficiente_de_miembro(semilla: Semilla) -> Semilla:
    return _con_coeficiente_de_miembro(semilla, "ascensor", Decimal("0.500000"))


def _solo_el_campo_de_la_unidad(campo: str) -> str:
    """D9: el mensaje entero. `match` busca en cualquier lugar, así que sin los anclajes
    también pasaría un mensaje que nombra otro campo o que muestra un valor."""
    return rf"\Aunidades\[1A\]\.{campo}: difiere de la semilla\Z"


def test_la_semilla_sin_alterar_no_difiere(ejemplo_cargado: _EjemploCargado) -> None:
    """Control de los casos de abajo: sin esto, un `EjemploDistinto` podría venir
    de cualquier otra diferencia entre la base compartida y la semilla (L-016)."""
    resultado = ejemplo.cargar(
        ejemplo_cargado.fabrica,
        parametros=_parametros(),
        semilla=_semilla(),
        georef=_georef(),
        request_id=uuid4(),
    )
    assert resultado.hizo_algo is False


@pytest.mark.parametrize(
    "alterar,mensaje",
    [
        pytest.param(
            _otro_estado_de_migracion,
            r"estado_migracion: base='sin_saldos_previos' semilla='pendiente'",
            id="estado_migracion",
        ),
        pytest.param(_otro_modo_de_grupo, r"grupos\.ascensor\.modo", id="modo_del_grupo"),
        pytest.param(
            _otro_tipo_de_unidad, _solo_el_campo_de_la_unidad("tipo"), id="tipo_de_unidad"
        ),
        pytest.param(
            _otro_piso_de_unidad, _solo_el_campo_de_la_unidad("piso"), id="piso_de_unidad"
        ),
        pytest.param(
            _otra_superficie_de_unidad,
            _solo_el_campo_de_la_unidad("superficie_m2"),
            id="superficie_de_unidad",
        ),
        pytest.param(
            _semilla_con_una_unidad_mas,
            r"unidades: faltan \['9Z'\], sobran \[\]",
            id="unidad_de_menos_en_la_base",
        ),
        pytest.param(
            _semilla_con_una_unidad_menos,
            r"unidades: faltan \[\], sobran \['B1'\]",
            id="unidad_de_mas_en_la_base",
        ),
        pytest.param(
            _semilla_con_un_grupo_mas,
            r"grupos: faltan \['servicios_centrales'\], sobran \[\]",
            id="grupo_que_falta",
        ),
        pytest.param(
            _semilla_con_un_grupo_menos,
            r"grupos: faltan \[\], sobran \['cocheras'\]",
            id="grupo_que_sobra",
        ),
        pytest.param(
            _semilla_con_un_miembro_mas,
            r"grupos\.ascensor\.unidades: difiere",
            id="miembro_de_menos_en_la_base",
        ),
        pytest.param(
            _semilla_con_un_miembro_menos,
            r"grupos\.ascensor\.unidades: difiere",
            id="miembro_de_mas_en_la_base",
        ),
        pytest.param(
            _semilla_con_coeficiente_de_miembro,
            r"grupos\.ascensor\.unidades\[1A\]\.coeficiente",
            id="coeficiente_del_miembro",
        ),
    ],
)
def test_cada_dato_comparado_se_detecta_por_separado(
    ejemplo_cargado: _EjemploCargado, alterar: Callable[[Semilla], Semilla], mensaje: str
) -> None:
    antes = _conteos_del_ejemplo(ejemplo_cargado.fabrica)

    with pytest.raises(ejemplo.EjemploDistinto, match=mensaje):
        ejemplo.cargar(
            ejemplo_cargado.fabrica,
            parametros=_parametros(),
            semilla=alterar(_semilla()),
            georef=_georef(),
            request_id=uuid4(),
        )

    assert _conteos_del_ejemplo(ejemplo_cargado.fabrica) == antes


def test_cada_campo_de_la_unidad_que_difiere_suma_su_mensaje(
    ejemplo_cargado: _EjemploCargado,
) -> None:
    """D9: cuatro campos distintos son cuatro mensajes, sin valores. Los casos de arriba
    alteran un solo campo y no distinguen esto de un mensaje que corta en el primero."""
    alterada = _con_unidad(
        _semilla(),
        "1A",
        tipo="local",
        piso="2",
        coeficiente=Decimal("0.999999"),
        superficie_m2=Superficie("61.00"),
    )

    with pytest.raises(ejemplo.EjemploDistinto) as error:
        ejemplo.cargar(
            ejemplo_cargado.fabrica,
            parametros=_parametros(),
            semilla=alterada,
            georef=_georef(),
            request_id=uuid4(),
        )

    assert sorted(str(error.value).split("; ")) == [
        "unidades[1A].coeficiente: difiere de la semilla",
        "unidades[1A].piso: difiere de la semilla",
        "unidades[1A].superficie_m2: difiere de la semilla",
        "unidades[1A].tipo: difiere de la semilla",
    ]


def test_el_coeficiente_propio_de_un_miembro_se_compara_por_valor(
    base_fresca: BaseDeEdificio,
) -> None:
    """La otra mitad de la rama: los dos lados tienen coeficiente y difieren. La
    semilla del repositorio no tiene un grupo en modo `propios`, así que el caso
    carga uno: en la base compartida del módulo este camino no se puede alcanzar."""
    grupo = _grupo(_semilla(), "ascensor")
    miembros = [m.model_copy(update={"coeficiente": Decimal("0.125000")}) for m in grupo.unidades]
    con_propios = _con_grupo(
        _semilla(), "ascensor", grupo.model_copy(update={"modo": "propios", "unidades": miembros})
    )
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        ejemplo.cargar(
            fabrica,
            parametros=_parametros(),
            semilla=con_propios,
            georef=_georef(),
            request_id=uuid4(),
        )
        antes = _conteos_del_ejemplo(fabrica)
        with pytest.raises(
            ejemplo.EjemploDistinto, match=r"grupos\.ascensor\.unidades\[1A\]\.coeficiente"
        ):
            ejemplo.cargar(
                fabrica,
                parametros=_parametros(),
                semilla=_con_coeficiente_de_miembro(con_propios, "ascensor", Decimal("0.500000")),
                georef=_georef(),
                request_id=uuid4(),
            )
        assert _conteos_del_ejemplo(fabrica) == antes
    finally:
        engine.dispose()


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

    with pytest.raises(ejemplo.EjemploDistinto, match=_solo_el_campo_de_la_unidad("coeficiente")):
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
    """D6 de `ejemplo-robusto`: la barrera hace que los dos hilos lleguen al mismo
    `INSERT INTO administracion` a la vez. Sin ella, este test pasaba aunque los
    hilos corrieran uno después del otro. Si se serializan, la barrera se rompe por
    tiempo y el error sale por los resultados."""
    from sqlalchemy import event

    parametros = _parametros()
    semilla = _semilla()
    resultados: list[ejemplo.ResultadoCarga | Exception | None] = [None, None]
    barrera = threading.Barrier(2, timeout=15)
    cruces: list[bool] = []

    def _esperar_al_otro(*args: object) -> None:
        if "INSERT INTO administracion" in str(args[2]):
            barrera.wait()
            cruces.append(True)

    def _correr(indice: int) -> None:
        engine, fabrica = _fabrica_app(base_fresca)
        event.listen(engine, "before_cursor_execute", _esperar_al_otro)
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
        hilo.join(timeout=60)
    assert not any(hilo.is_alive() for hilo in hilos)

    for resultado in resultados:
        if isinstance(resultado, Exception):
            raise resultado

    # L-016: sin este conteo, un `INSERT` con otro texto dejaría la barrera sin
    # usar y el test volvería a pasar sin forzar nada.
    assert len(cruces) == 2
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


def _alta_sin_edificio(fabrica: sessionmaker[Session]) -> None:
    """La administración y su persona, sin el edificio: un estado que la carga no
    deja sola, porque toda la carga va en una transacción (D7 de `ejemplo-robusto`)."""
    with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion, sesion.begin():
        alta = crear_administracion_y_super_admin(
            sesion,
            administracion_id=ejemplo.ADMINISTRACION_EJEMPLO_ID,
            persona_id=ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID,
            nombre_administracion=ejemplo.NOMBRE_ADMINISTRACION_EJEMPLO,
            nombre_persona=ejemplo.NOMBRE_SUPER_ADMIN_EJEMPLO,
            email=ejemplo.EMAIL_SUPER_ADMIN_EJEMPLO,
            request_id=uuid4(),
        )
    assert alta is not None


def test_la_administracion_sin_edificio_agota_la_espera(base_fresca: BaseDeEdificio) -> None:
    """Escenario "La administración de ejemplo quedó sin edificio": el mensaje dice
    lo que se ve, sin culpar a una corrida en paralelo que el contexto descarta."""
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        _alta_sin_edificio(fabrica)
        antes = _conteos_del_ejemplo(fabrica)

        with pytest.raises(ejemplo.EsperaAgotada, match="existe sin edificio"):
            ejemplo.cargar(
                fabrica,
                parametros=_parametros(),
                semilla=_semilla(),
                georef=_georef(),
                request_id=uuid4(),
                intentos=2,
                espera_s=0,
            )

        assert _conteos_del_ejemplo(fabrica) == antes
        assert antes["complejo"] == 0
    finally:
        engine.dispose()


def test_el_edificio_que_aparece_durante_la_espera_se_compara(
    base_fresca: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Escenario "El edificio aparece durante la espera": otra sesión lo confirma en
    medio de la espera, y `cargar` vuelve a mirar con una sesión nueva y compara."""
    engine, fabrica = _fabrica_app(base_fresca)
    esperas: list[float] = []

    def _aparece_el_edificio(segundos: float) -> None:
        esperas.append(segundos)
        identidad = Identidad(
            ejemplo.ADMINISTRACION_EJEMPLO_ID, ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID
        )
        with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as otra, otra.begin():
            ejemplo._crear_desde_cero(
                otra,
                identidad,
                parametros=_parametros(),
                semilla=_semilla(),
                georef=_georef(),
                reloj=ejemplo._reloj_por_defecto,
                request_id=uuid4(),
            )

    monkeypatch.setattr(ejemplo, "time", SimpleNamespace(sleep=_aparece_el_edificio))
    try:
        _alta_sin_edificio(fabrica)
        try:
            resultado = ejemplo.cargar(
                fabrica,
                parametros=_parametros(),
                semilla=_semilla(),
                georef=_georef(),
                request_id=uuid4(),
                intentos=3,
                espera_s=0,
            )
        except ejemplo.EsperaAgotada as error:
            pytest.fail(f"no volvió a mirar después de la espera: {error}")
        assert resultado.hizo_algo is False
        assert esperas == [0]
        assert _contar(fabrica, "complejo", ejemplo.ADMINISTRACION_EJEMPLO_ID) == 1
    finally:
        engine.dispose()


# --- El edificio correcto y el super admin del ejemplo (`ejemplo-robusto`, D2 y D3) ---


def _crear_otro_edificio(fabrica: sessionmaker[Session], nombre: str) -> UUID:
    """Por el mismo caso de uso que `POST /complejos` (L-017): es el segundo edificio
    que un `super_admin` vinculado con `--clerk-usuario` puede crear de verdad."""
    semilla = _semilla()
    identidad = Identidad(ejemplo.ADMINISTRACION_EJEMPLO_ID, ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID)
    with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion, sesion.begin():
        return crear_edificio(
            sesion,
            identidad,
            nombre=nombre,
            provincia_id=semilla.edificio.provincia_id,
            departamento_id=semilla.edificio.departamento_id,
            localidad_id=semilla.edificio.localidad_id,
            georef=_georef(),
            pisos=semilla.edificio.pisos,
            subsuelos=semilla.edificio.subsuelos,
            parametros=_parametros(),
            reloj=ejemplo._reloj_por_defecto,
            request_id=uuid4(),
        )


def _sumar_unidad_y_grupo(fabrica: sessionmaker[Session], complejo_id: UUID) -> None:
    """Un edificio recién creado no tiene unidades y su único grupo es Generales, que la
    comparación excluye: al lado de él, nada vigila que se mire sólo el edificio del
    ejemplo (F8 y F9 de verify 1, L-017). Por los mismos casos de uso que la API."""
    identidad = Identidad(ejemplo.ADMINISTRACION_EJEMPLO_ID, ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID)
    with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion, sesion.begin():
        unidad_id = crear_unidad(
            sesion,
            identidad,
            request_id=uuid4(),
            complejo_id=complejo_id,
            datos={
                "identificador": "9Z",
                "tipo": "departamento",
                "piso": "1",
                "coeficiente": "0.100000",
                "superficie_m2": Superficie("60.00"),
            },
        )
        crear_grupo(
            sesion,
            identidad,
            complejo_id=complejo_id,
            datos={"clave": "solo_del_otro", "nombre": "Sólo del otro", "metodo": "coeficiente"},
            miembros=[{"unidad_id": unidad_id}],
            request_id=uuid4(),
        )


def _primeros_edificios_sin_orden(fabrica: sessionmaker[Session]) -> set[UUID]:
    """Qué fila elegía la consulta `LIMIT 1` sin `ORDER BY` que tenía `cargar()`, con el
    plan que prefiera Postgres y recorriendo la tabla: es la condición del escenario."""
    consulta = text("SELECT id FROM complejo WHERE administracion_id=:admin LIMIT 1")
    parametros = {"admin": ejemplo.ADMINISTRACION_EJEMPLO_ID}
    with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion:
        con_el_plan_preferido = sesion.execute(consulta, parametros).scalar_one()
        for sin_indice in (
            "SET LOCAL enable_indexscan = off",
            "SET LOCAL enable_indexonlyscan = off",
            "SET LOCAL enable_bitmapscan = off",
        ):
            sesion.execute(text(sin_indice))
        recorriendo_la_tabla = sesion.execute(consulta, parametros).scalar_one()
    return {con_el_plan_preferido, recorriendo_la_tabla}


def _fila_de_edificio(fabrica: sessionmaker[Session], complejo_id: UUID) -> tuple[object, ...]:
    with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion:
        fila = sesion.execute(
            text(
                "SELECT nombre, estado_migracion, "
                "(SELECT count(*) FROM unidad WHERE complejo_id = c.id), "
                "(SELECT count(*) FROM grupo_de_reparto WHERE complejo_id = c.id) "
                "FROM complejo c WHERE id=:id"
            ),
            {"id": complejo_id},
        ).one()
        return tuple(fila)


def test_otro_edificio_con_otro_nombre_no_cambia_el_resultado(base_fresca: BaseDeEdificio) -> None:
    """Escenario "Otro edificio en la administración de ejemplo". `LIMIT 1` corría
    sobre `uq_complejo_administracion_id`, así que elegía el `id` más bajo: con un
    edificio creado por el caso de uso, el resultado salía a cara o cruz, y ni un
    `UPDATE` lo movía. Para que este test no dependa de la suerte, una fila con el
    `id` más bajo posible queda primera en ese índice, antes del edificio creado por
    el caso de uso; y el `UPDATE` deja al ejemplo último en la tabla."""
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        carga = _cargar_con_usuario(fabrica)
        id_mas_bajo = UUID("00000000-0000-4000-8000-000000000001")
        with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion, sesion.begin():
            sesion.execute(
                text(
                    "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                    "VALUES (:id, :admin, 'Edificio del id bajo, ficticio', 'Mendoza')"
                ),
                {"id": id_mas_bajo, "admin": ejemplo.ADMINISTRACION_EJEMPLO_ID},
            )
        otro = _crear_otro_edificio(fabrica, "Otro edificio ficticio")
        _sumar_unidad_y_grupo(fabrica, otro)
        # Una unidad y dos grupos, Generales y el propio: sin esto, el caso no vigila nada.
        assert _fila_de_edificio(fabrica, otro)[2:] == (1, 2)
        with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion, sesion.begin():
            sesion.execute(
                text("UPDATE complejo SET nombre = nombre WHERE id=:id"),
                {"id": carga.complejo_id},
            )
        assert _primeros_edificios_sin_orden(fabrica) == {id_mas_bajo}, "no es el orden buscado"
        filas_de_los_otros = [_fila_de_edificio(fabrica, c) for c in (otro, id_mas_bajo)]

        try:
            resultado = _cargar_con_usuario(fabrica)
        except ejemplo.EjemploDistinto as error:
            pytest.fail(f"falso 'el ejemplo cambió': {error}")

        assert resultado.hizo_algo is False
        assert resultado.complejo_id == carga.complejo_id
        assert [_fila_de_edificio(fabrica, c) for c in (otro, id_mas_bajo)] == filas_de_los_otros
    finally:
        engine.dispose()


def test_ningun_edificio_con_el_nombre_de_la_semilla_es_distinto_sin_esperar(
    ejemplo_cargado: _EjemploCargado, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Escenario "El edificio del ejemplo no se puede identificar", ninguno."""
    esperas: list[float] = []
    monkeypatch.setattr(ejemplo, "time", SimpleNamespace(sleep=esperas.append))
    antes = _conteos_del_ejemplo(ejemplo_cargado.fabrica)

    with pytest.raises(ejemplo.EjemploDistinto, match=r"edificio\.nombre"):
        ejemplo.cargar(
            ejemplo_cargado.fabrica,
            parametros=_parametros(),
            semilla=_con_edificio(_semilla(), nombre="Otro nombre ficticio"),
            georef=_georef(),
            request_id=uuid4(),
        )

    assert esperas == []
    assert _conteos_del_ejemplo(ejemplo_cargado.fabrica) == antes


def test_dos_edificios_con_el_nombre_de_la_semilla_es_distinto_sin_esperar(
    base_fresca: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Escenario "El edificio del ejemplo no se puede identificar", más de uno:
    `complejo` no tiene unicidad por nombre."""
    esperas: list[float] = []
    monkeypatch.setattr(ejemplo, "time", SimpleNamespace(sleep=esperas.append))
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        _cargar_con_usuario(fabrica)
        _crear_otro_edificio(fabrica, _semilla().edificio.nombre)
        antes = _conteos_del_ejemplo(fabrica)

        with pytest.raises(ejemplo.EjemploDistinto, match=r"edificio\.nombre"):
            _cargar_con_usuario(fabrica)

        assert esperas == []
        assert _conteos_del_ejemplo(fabrica) == antes
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "sentencia,mensaje",
    [
        pytest.param(
            "UPDATE persona SET nombre='Otro nombre ficticio' WHERE id=:id",
            r"persona\.nombre",
            id="nombre",
        ),
        pytest.param(
            "UPDATE persona SET email='otra@ejemplo.proptech.invalid' WHERE id=:id",
            r"persona\.email",
            id="email",
        ),
        pytest.param(
            "DELETE FROM asignacion_rol WHERE persona_id=:id AND rol='super_admin'",
            r"persona\.asignaciones",
            id="asignacion",
        ),
        pytest.param(
            "UPDATE asignacion_rol SET rol='contador' WHERE persona_id=:id AND rol='super_admin'",
            r"persona\.asignaciones",
            id="asignacion_con_otro_rol",
        ),
    ],
)
def test_el_super_admin_del_ejemplo_cambio(
    base_fresca: BaseDeEdificio, sentencia: str, mensaje: str
) -> None:
    """El escenario de `datos-semilla` sobre la persona del ejemplo que cambió. Acá
    la base sí se edita (D3): la persona no sale de la semilla, así que alterar la
    semilla no la tocaría."""
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        _cargar_con_usuario(fabrica)
        with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion, sesion.begin():
            sesion.execute(text(sentencia), {"id": ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID})
        antes = _conteos_del_ejemplo(fabrica)

        with pytest.raises(ejemplo.EjemploDistinto, match=mensaje):
            _cargar_con_usuario(fabrica)

        assert _conteos_del_ejemplo(fabrica) == antes
    finally:
        engine.dispose()


def test_sin_el_super_admin_el_ejemplo_es_distinto(
    ejemplo_cargado: _EjemploCargado, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Con un doble, porque en la base no se puede llegar a este estado: la primera
    versión de la configuración referencia a la persona (`fk_configuracion_autor`)."""
    monkeypatch.setattr(ejemplo, "listar_personal", lambda _: [])

    with pytest.raises(ejemplo.EjemploDistinto, match=r"persona: "):
        ejemplo.cargar(
            ejemplo_cargado.fabrica,
            parametros=_parametros(),
            semilla=_semilla(),
            georef=_georef(),
            request_id=uuid4(),
        )


@pytest.mark.parametrize(
    "sentencia",
    [
        pytest.param(
            "UPDATE persona SET clerk_usuario_id='user_Dev123' WHERE id=:id",
            id="cuenta_vinculada",
        ),
        pytest.param(
            "INSERT INTO persona(administracion_id, nombre) "
            "SELECT administracion_id, 'Otra ficticia' FROM persona WHERE id=:id",
            id="otra_persona",
        ),
    ],
)
def test_lo_que_no_cuenta_como_ejemplo_cambiado(
    base_fresca: BaseDeEdificio, sentencia: str
) -> None:
    """Escenario "Lo que no cuenta como ejemplo cambiado" (D3): una cuenta vinculada
    u otra persona que aceptó una invitación no son "el ejemplo cambió"."""
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        _cargar_con_usuario(fabrica)
        with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion, sesion.begin():
            sesion.execute(text(sentencia), {"id": ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID})

        assert _cargar_con_usuario(fabrica).hizo_algo is False
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


def _correr_comando(
    variables: dict[str, str],
    *argumentos: str,
    tope_s: float = 120,
    directorio: Path = _BACKEND,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "proptech_core.complejos.aplicacion.ejemplo",
            "cargar",
            *argumentos,
        ],
        cwd=directorio,
        env=variables,
        capture_output=True,
        text=True,
        timeout=tope_s,
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

    def _espia(configuracion: ConfiguracionDelEjemplo) -> Engine:
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


def test_el_comando_real_carga_sin_ninguna_variable_de_redis(base_fresca: BaseDeEdificio) -> None:
    """Escenario "Carga sin variables de Redis": el comando no usa Redis, así que
    no las exige (QA-3, D5 de `ejemplo-robusto`). `conftest.py` las pone para todos
    los tests de integración, por eso se sacan acá."""
    variables = {
        clave_entorno: valor
        for clave_entorno, valor in _entorno_del_comando(
            base_fresca,
            usuario=APP_USER_DE_SESION,
            clave=APP_PASSWORD_DE_SESION,
            entorno="desarrollo",
        ).items()
        if not clave_entorno.startswith("REDIS_")
    }

    resultado = _correr_comando(variables)

    assert resultado.returncode == 0, resultado.stderr[-2000:]
    assert "ejemplo cargado" in resultado.stdout
    escritas = _filas_escritas(base_fresca)
    assert escritas["administracion"] == 1
    assert escritas["complejo"] == 1


#: Ficticia: si aparece en una salida, la salida está filtrando la contraseña.
_CLAVE_SEMBRADA = "clave-sembrada-no-real"
_VALOR_SEMBRADO = "valor-sembrado"


def _entorno_limpio() -> dict[str, str]:
    """Sin ninguna variable de configuración del proyecto, heredada o del `conftest.py`."""
    return {
        clave_entorno: valor
        for clave_entorno, valor in os.environ.items()
        if not clave_entorno.startswith(("POSTGRES_", "PROPTECH_", "REDIS_", "DB_", "CLERK_"))
    }


def _entorno_con_base_cerrada() -> dict[str, str]:
    """Todo correcto y nada escuchando: si el comando llega a conectarse, termina con
    el código 5. Así, un 2 o un 3 prueban que no intentó conectarse."""
    return {
        **_entorno_limpio(),
        "PROPTECH_ENTORNO": "desarrollo",
        "PROPTECH_PARAMETROS": str(_PARAMETROS),
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": "1",
        "POSTGRES_DB": "proptech_ficticia",
        "POSTGRES_APP_USER": APP_USER_DE_SESION,
        "POSTGRES_APP_PASSWORD": _CLAVE_SEMBRADA,
    }


def _afirmar_salida_limpia(salida: str, *valores: str) -> None:
    for prohibido in ("Traceback", "[parameters:", _CLAVE_SEMBRADA, *valores):
        assert prohibido not in salida, salida[-2000:]


def _codigo_de_main(*argumentos: str) -> int:
    """Una excepción que se escapa es la falla que se está probando, no un error del
    test: hace que el rojo caiga en una aserción propia (L-034)."""
    try:
        return ejemplo._main(["cargar", *argumentos])
    except Exception as error:
        pytest.fail(f"_main dejó escapar {type(error).__name__}")


def _configuracion_valida(monkeypatch: pytest.MonkeyPatch) -> None:
    """Todo lo que piden los dos lectores (L-009), con la base en un puerto cerrado."""
    for variable, valor in {
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": "1",
        "POSTGRES_DB": "proptech_ficticia",
        "POSTGRES_APP_USER": APP_USER_DE_SESION,
        "POSTGRES_APP_PASSWORD": _CLAVE_SEMBRADA,
        "PROPTECH_PARAMETROS": str(_PARAMETROS),
        "REDIS_HOST": "127.0.0.1",
        "REDIS_PASSWORD": "redis-sembrada-no-real",
    }.items():
        monkeypatch.setenv(variable, valor)


def _casos_de_variable(variable: str, *valores: str | None) -> list[tuple[str, str | None]]:
    return [(variable, valor) for valor in valores]


@pytest.mark.parametrize(
    "variable,valor",
    [
        # L-002: faltante (None), vacía, en blanco, tipo equivocado y fuera de rango.
        *_casos_de_variable("POSTGRES_HOST", None, "", "   "),
        *_casos_de_variable("POSTGRES_DB", None, "", "   "),
        *_casos_de_variable("POSTGRES_PORT", "", "   ", _VALOR_SEMBRADO, "0", "65536"),
        *_casos_de_variable("POSTGRES_APP_USER", None, "", "   ", _VALOR_SEMBRADO),
        *_casos_de_variable("POSTGRES_APP_PASSWORD", None, "", "   "),
        *_casos_de_variable("PROPTECH_PARAMETROS", None, "", "   ", _VALOR_SEMBRADO),
        *_casos_de_variable("DB_POOL_PRE_PING", "", "   ", _VALOR_SEMBRADO),
        *_casos_de_variable("DB_POOL_SIZE", "", "   ", _VALOR_SEMBRADO, "5_0", " 5", "0", "51"),
        # F5 de verify 1: el entero con espacio o con guion bajo, dentro del rango de cada
        # variable. Fuera de rango, el rango lo rechaza aunque falte el validador (L-017).
        *_casos_de_variable(
            "DB_POOL_RECYCLE_S", "", "   ", _VALOR_SEMBRADO, "59", "86401", " 900", "9_00"
        ),
        *_casos_de_variable(
            "DB_POOL_TIMEOUT_S", "", "   ", _VALOR_SEMBRADO, "0", "61", " 5", "5_0"
        ),
        *_casos_de_variable(
            "DB_CONNECT_TIMEOUT_S", "", "   ", _VALOR_SEMBRADO, "0", "31", " 5", "1_0"
        ),
    ],
)
@pytest.mark.parametrize(
    "lector",
    [
        pytest.param(ConfiguracionDelEjemplo, id="comando"),
        pytest.param(Configuracion, id="api_y_worker"),
    ],
)
def test_la_configuracion_rota_se_nombra_sin_mostrar_el_valor(
    monkeypatch: pytest.MonkeyPatch,
    lector: Callable[[], object],
    variable: str,
    valor: str | None,
) -> None:
    """Escenario "Configuración rota", con los mismos valores en los dos lectores."""
    _configuracion_valida(monkeypatch)
    if valor is None:
        monkeypatch.delenv(variable)
    else:
        monkeypatch.setenv(variable, valor)

    with pytest.raises(ConfiguracionInvalida, match=variable) as error:
        lector()

    assert _CLAVE_SEMBRADA not in str(error.value)
    if valor and valor.strip():
        assert valor not in str(error.value)


def test_la_configuracion_del_ejemplo_lee_lo_que_usa_el_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configuracion_valida(monkeypatch)
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("DB_POOL_PRE_PING", "false")
    monkeypatch.setenv("DB_POOL_SIZE", "7")
    monkeypatch.setenv("DB_POOL_RECYCLE_S", "900")
    monkeypatch.setenv("DB_POOL_TIMEOUT_S", "11")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT_S", "4")

    configuracion = ConfiguracionDelEjemplo()

    assert configuracion.proptech_parametros == str(_PARAMETROS)
    assert configuracion.db_pool_pre_ping is False
    assert configuracion.db_pool_size == 7
    assert configuracion.db_pool_recycle_s == 900
    assert configuracion.db_pool_timeout_s == 11
    assert configuracion.db_connect_timeout_s == 4
    url = configuracion.url_sqlalchemy()
    assert url.username == APP_USER_DE_SESION
    assert url.password == _CLAVE_SEMBRADA
    assert url.database == "proptech_ficticia"


@pytest.mark.parametrize("variable", ["REDIS_HOST", "REDIS_PASSWORD"])
@pytest.mark.parametrize(
    "codigo",
    [
        pytest.param("from proptech_api.app import crear_app; crear_app()", id="api"),
        pytest.param("import proptech_worker.ajustes", id="worker"),
    ],
)
def test_la_api_y_el_worker_siguen_exigiendo_redis(
    monkeypatch: pytest.MonkeyPatch, codigo: str, variable: str
) -> None:
    """Escenario "La API y el worker siguen exigiendo Redis": con el proceso real de
    cada uno, no con `Configuracion()` a secas, por si alguno dejara de leerla."""
    _configuracion_valida(monkeypatch)
    monkeypatch.delenv(variable)

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=_BACKEND,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert resultado.returncode != 0, resultado.stdout
    assert variable in resultado.stderr, resultado.stderr[-2000:]


@pytest.mark.parametrize(
    "variable,valor",
    [
        ("POSTGRES_APP_PASSWORD", None),
        ("POSTGRES_HOST", ""),
        ("POSTGRES_DB", "   "),
        ("POSTGRES_PORT", _VALOR_SEMBRADO),
        ("DB_POOL_SIZE", "51"),
        ("PROPTECH_PARAMETROS", _VALOR_SEMBRADO),
    ],
)
def test_una_variable_rota_termina_con_3_sin_conectarse(variable: str, valor: str | None) -> None:
    """Escenario "Configuración rota", por el proceso real: la base está en un puerto
    cerrado, así que si intentara conectarse terminaría con 5."""
    variables = _entorno_con_base_cerrada()
    if valor is None:
        del variables[variable]
    else:
        variables[variable] = valor

    resultado = _correr_comando(variables)

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    assert variable in resultado.stderr
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr, _VALOR_SEMBRADO)


def test_parametros_invalidos_terminan_con_3(tmp_path: Path) -> None:
    """`leer_parametros` estaba fuera de todo `try` y salía como traceback (D4)."""
    archivo = tmp_path / "parametros.yaml"
    archivo.write_text(f"tasa_mensual: [{_VALOR_SEMBRADO}\n", encoding="utf-8")
    variables = _entorno_con_base_cerrada()
    variables["PROPTECH_PARAMETROS"] = str(archivo)

    resultado = _correr_comando(variables)

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    assert resultado.stderr.strip()
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr, _VALOR_SEMBRADO)


def test_georef_invalido_termina_con_3(tmp_path: Path) -> None:
    """Parámetros válidos sin la carpeta `georef/` al lado."""
    shutil.copyfile(_PARAMETROS, tmp_path / "parametros.yaml")
    variables = _entorno_con_base_cerrada()
    variables["PROPTECH_PARAMETROS"] = str(tmp_path / "parametros.yaml")

    resultado = _correr_comando(variables)

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    assert ".json" in resultado.stderr
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr)


@pytest.mark.parametrize(
    "contenido",
    [
        pytest.param(f"version: [{_VALOR_SEMBRADO}\n", id="yaml_roto"),
        pytest.param(f"version: 1\nedificio: {_VALOR_SEMBRADO}\n", id="forma_invalida"),
    ],
)
def test_semilla_invalida_termina_con_3(tmp_path: Path, contenido: str) -> None:
    archivo = tmp_path / "semilla.yaml"
    archivo.write_text(contenido, encoding="utf-8")

    resultado = _correr_comando(_entorno_con_base_cerrada(), "--semilla", str(archivo))

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    assert resultado.stderr.strip()
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr, _VALOR_SEMBRADO)


def test_la_ruta_de_la_semilla_no_se_repite(tmp_path: Path) -> None:
    """`--semilla` es algo que se tipeó, y puede ser el id de la cuenta. El lector de
    archivos repite la ruta que no pudo leer, así que el comando se la saca (L-007)."""
    ruta = tmp_path / f"user_Sembrado1-{_VALOR_SEMBRADO}.yaml"

    resultado = _correr_comando(_entorno_con_base_cerrada(), "--semilla", str(ruta))

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    assert "no se puede leer" in resultado.stderr
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr, _VALOR_SEMBRADO, "user_Sembrado1")


def test_la_ruta_de_los_parametros_no_se_repite(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """El gemelo del anterior (L-009), con un doble: el lector de variables ya exige que
    el archivo exista, así que sólo se llega acá con un archivo que no se deja leer."""
    _configuracion_valida(monkeypatch)
    monkeypatch.setenv("PROPTECH_ENTORNO", "desarrollo")

    def _lanzar(ruta: str) -> Parametros:
        raise ParametrosInvalidos(f"no se puede leer el archivo: {ruta}")

    monkeypatch.setattr(ejemplo, "leer_parametros", _lanzar)

    assert _codigo_de_main() == 3
    salida = capsys.readouterr()
    assert salida.err.strip() == "no se puede leer el archivo: <parámetros>"
    _afirmar_salida_limpia(salida.out + salida.err, str(_PARAMETROS))


@pytest.mark.parametrize("ruta", ["a", "e", "archivo", "user_Sembrado1", "   "])
def test_una_ruta_corta_no_deforma_el_mensaje_del_archivo_ilegible(
    tmp_path: Path, ruta: str
) -> None:
    """Escenarios "Un archivo que no se puede leer" y "La ruta de la semilla es una palabra
    del mensaje" (F1 de verify 1). Compara el mensaje entero: la ruta no sale, y lo demás
    queda intacto. La carpeta es propia, así que ninguna de estas rutas existe ahí."""
    resultado = _correr_comando(_entorno_con_base_cerrada(), "--semilla", ruta, directorio=tmp_path)

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    assert resultado.stderr.strip() == "no se puede leer el archivo: <semilla>"


def test_una_ruta_corta_no_deforma_el_mensaje_de_la_semilla_invalida(tmp_path: Path) -> None:
    """F1: `s` es una letra de casi cualquier mensaje del lector, y el archivo sí se leyó."""
    (tmp_path / "s").write_text("version: 2\n", encoding="utf-8")

    resultado = _correr_comando(_entorno_con_base_cerrada(), "--semilla", "s", directorio=tmp_path)

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    assert "version:" in resultado.stderr, resultado.stderr[-2000:]
    assert "<semilla>" not in resultado.stderr, resultado.stderr[-2000:]


def test_una_ruta_que_es_un_campo_no_borra_el_campo(tmp_path: Path) -> None:
    """F1: el archivo se llama como el campo que el mensaje tiene que nombrar."""
    texto = _SEMILLA.read_text(encoding="utf-8")
    assert 'identificador: "1B"' in texto
    (tmp_path / "unidades").write_text(
        texto.replace('identificador: "1B"', 'identificador: "1A"'), encoding="utf-8"
    )

    resultado = _correr_comando(
        _entorno_con_base_cerrada(), "--semilla", "unidades", directorio=tmp_path
    )

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    assert "unidades: hay identificadores repetidos" in resultado.stderr, resultado.stderr[-2000:]
    assert "<semilla>" not in resultado.stderr, resultado.stderr[-2000:]


def test_una_ruta_corta_de_los_parametros_no_deforma_el_mensaje(tmp_path: Path) -> None:
    """F1, el gemelo (L-009), por el proceso real: `e` es una letra de "parámetros"."""
    (tmp_path / "e").write_text("version: 99\n", encoding="utf-8")

    resultado = _correr_comando(
        {**_entorno_con_base_cerrada(), "PROPTECH_PARAMETROS": "e"}, directorio=tmp_path
    )

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    assert "parámetros inválidos" in resultado.stderr, resultado.stderr[-2000:]
    assert "<parámetros>" not in resultado.stderr, resultado.stderr[-2000:]


def test_sin_la_semilla_por_defecto_termina_con_3(tmp_path: Path) -> None:
    shutil.copyfile(_PARAMETROS, tmp_path / "parametros.yaml")
    shutil.copytree(_GEOREF, tmp_path / "georef")
    variables = _entorno_con_base_cerrada()
    variables["PROPTECH_PARAMETROS"] = str(tmp_path / "parametros.yaml")

    resultado = _correr_comando(variables)

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    assert resultado.stderr.strip()
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr)


def test_fuera_de_desarrollo_sin_ninguna_otra_variable_termina_con_1() -> None:
    """Escenario "Fuera de desarrollo, sin ninguna otra variable" (RV-1 de D-112): la
    guarda va antes que la configuración, y por eso no sale el código 3."""
    resultado = _correr_comando(_entorno_limpio())

    assert resultado.returncode == 1, resultado.stderr[-2000:]
    assert "PROPTECH_ENTORNO=desarrollo" in resultado.stderr
    assert "Traceback" not in resultado.stderr


@pytest.mark.parametrize(
    "argumentos",
    [
        pytest.param(["--semilla="], id="con_igual"),
        pytest.param(["--semilla", ""], id="separado"),
    ],
)
def test_la_semilla_vacia_termina_con_2_sin_conectarse(argumentos: list[str]) -> None:
    """Escenario "`--semilla` vacío" (O4 de verify 1): un `--semilla "$VARIABLE"` sin definir
    cargaba la semilla por defecto. La base está cerrada, así que conectarse daría 5."""
    resultado = _correr_comando(_entorno_con_base_cerrada(), *argumentos)

    assert resultado.returncode == 2, resultado.stderr[-2000:]
    assert "--semilla" in resultado.stderr, resultado.stderr[-2000:]
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr)


def test_la_semilla_vacia_fuera_de_desarrollo_termina_con_1() -> None:
    """La guarda sigue primero (D4): `--semilla=` no cambia el código de la guarda."""
    resultado = _correr_comando(_entorno_limpio(), "--semilla=")

    assert resultado.returncode == 1, resultado.stderr[-2000:]
    assert "PROPTECH_ENTORNO=desarrollo" in resultado.stderr, resultado.stderr[-2000:]


def test_la_semilla_vacia_va_antes_que_la_configuracion() -> None:
    """F11 de verify 2: el orden de D4 pone `--semilla` vacío (2) antes de leer la
    configuración (3). Sin ninguna variable de PostgreSQL, un comando que leyera primero la
    configuración terminaría con 3 (mutante B4)."""
    resultado = _correr_comando(
        {**_entorno_limpio(), "PROPTECH_ENTORNO": "desarrollo"}, "--semilla="
    )

    assert resultado.returncode == 2, resultado.stderr[-2000:]
    assert "--semilla no puede estar vacío" in resultado.stderr, resultado.stderr[-2000:]
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr)


def test_el_id_con_formato_invalido_termina_con_2_por_el_proceso_real() -> None:
    """Escenario "Id de cuenta con formato inválido": el código sale del proceso."""
    resultado = _correr_comando(
        _entorno_con_base_cerrada(), "--clerk-usuario", f"no_es_un_id_{_VALOR_SEMBRADO}"
    )

    assert resultado.returncode == 2, resultado.stderr[-2000:]
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr, _VALOR_SEMBRADO)


def test_el_emisor_que_no_es_de_desarrollo_termina_con_3_por_el_proceso_real() -> None:
    """Escenario "Instancia de Clerk que no es de desarrollo"."""
    variables = _entorno_con_base_cerrada()
    variables["CLERK_EMISOR"] = f"https://{_VALOR_SEMBRADO}.invalid"

    resultado = _correr_comando(variables, "--clerk-usuario", "user_Sembrado1")

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr, _VALOR_SEMBRADO, "user_Sembrado1")


def test_el_comando_real_se_niega_a_correr_como_el_migrador(base_fresca: BaseDeEdificio) -> None:
    """Escenario "El rol no es seguro". Con las credenciales del migrador puestas
    como las de la app, el comando sale con 4 por `RolDeAplicacionInseguro` (el
    control de `_main`, no un permiso que falte más adelante) y no escribe nada."""
    resultado = _correr_comando(
        _entorno_del_comando(
            base_fresca,
            usuario=MIGRADOR_USER_DE_SESION,
            clave=MIGRADOR_PASSWORD_DE_SESION,
            entorno="desarrollo",
        )
    )

    assert resultado.returncode == 4, resultado.stderr[-2000:]
    assert "no es seguro" in resultado.stderr, resultado.stderr[-2000:]
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr, MIGRADOR_PASSWORD_DE_SESION)
    assert _filas_escritas(base_fresca) == _SIN_ESCRITURAS


@pytest.mark.parametrize(
    "tabla,cambio,motivo",
    [
        pytest.param(
            "configuracion_versionada",
            sql.SQL("OWNER TO {}").format(sql.Identifier(MIGRADOR_USER_DE_SESION)),
            "dueño no superusuario",
            id="configuracion_versionada",
        ),
        pytest.param(
            "imputacion",
            sql.SQL("OWNER TO {}").format(sql.Identifier(MIGRADOR_USER_DE_SESION)),
            "dueño no superusuario",
            id="imputacion",
        ),
        pytest.param(
            "imputacion",
            sql.SQL("RENAME TO imputacion_oculta"),
            "no existe en public",
            id="imputacion_que_no_existe",
        ),
    ],
)
def test_tablas_de_solo_agregar_desprotegidas_terminan_con_4(
    base_fresca: BaseDeEdificio, tabla: str, cambio: sql.Composable, motivo: str
) -> None:
    """Escenario "Hay tablas de sólo agregar desprotegidas": la salida nombra la tabla y
    su motivo, porque es lo que hay que ir a arreglar. La base se borra al terminar el
    test, así que no hace falta deshacer el cambio."""
    with psycopg.connect(
        host=base_fresca.contenedor.get_container_host_ip(),
        port=base_fresca.contenedor.get_exposed_port(5432),
        user=base_fresca.contenedor.username,
        password=base_fresca.contenedor.password,
        dbname=base_fresca.nombre,
        autocommit=True,
    ) as arranque:
        arranque.execute(sql.SQL("ALTER TABLE {} {}").format(sql.Identifier(tabla), cambio))

    resultado = _correr_comando(
        _entorno_del_comando(
            base_fresca,
            usuario=APP_USER_DE_SESION,
            clave=APP_PASSWORD_DE_SESION,
            entorno="desarrollo",
        )
    )

    assert resultado.returncode == 4, resultado.stderr[-2000:]
    assert f"{tabla}: {motivo}" in resultado.stderr, resultado.stderr[-2000:]
    assert resultado.stderr.strip().endswith("no se escribió nada"), resultado.stderr[-2000:]
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr, APP_PASSWORD_DE_SESION)
    assert _filas_escritas(base_fresca) == _SIN_ESCRITURAS


def test_la_base_apagada_termina_con_5_sin_mostrar_la_conexion() -> None:
    """Escenario "La base está apagada": nada escucha en ese puerto."""
    resultado = _correr_comando(_entorno_con_base_cerrada())

    assert resultado.returncode == 5, resultado.stderr[-2000:]
    assert "no está disponible" in resultado.stderr, resultado.stderr[-2000:]
    _afirmar_salida_limpia(
        resultado.stdout + resultado.stderr, "127.0.0.1", "proptech_ficticia", APP_USER_DE_SESION
    )


def test_la_base_que_no_responde_termina_con_5_dentro_del_limite() -> None:
    """Escenario "La base no responde" (L-001). Un socket que acepta la conexión y
    nunca contesta: se comporta igual en cualquier red, y por eso sí mide el límite.
    Con el límite en 8 s, el piso distingue si se usa `DB_CONNECT_TIMEOUT_S` o los 2 s
    por defecto, y el techo incluye el arranque del intérprete."""
    limite_s = 8
    with socket.socket() as mudo:
        mudo.bind(("127.0.0.1", 0))
        mudo.listen(8)
        variables = _entorno_con_base_cerrada()
        variables["POSTGRES_PORT"] = str(mudo.getsockname()[1])
        variables["DB_CONNECT_TIMEOUT_S"] = str(limite_s)

        inicio = time.monotonic()
        try:
            resultado = _correr_comando(variables, tope_s=60)
        except subprocess.TimeoutExpired:
            pytest.fail("el comando siguió esperando después de DB_CONNECT_TIMEOUT_S")
        duracion_s = time.monotonic() - inicio

    assert resultado.returncode == 5, resultado.stderr[-2000:]
    assert limite_s <= duracion_s < limite_s + 30, duracion_s
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr, "127.0.0.1", "proptech_ficticia")


def test_el_host_sin_ruta_termina_con_5_dentro_del_limite() -> None:
    """La otra cara de L-001, con la misma IP que `test_salud.py`. Según la red, puede
    no contestar o rechazar al instante: los dos son código 5, así que acá sólo se
    acota el techo. Quien mide el límite es el test del socket."""
    limite_s = 2
    variables = _entorno_con_base_cerrada()
    variables["POSTGRES_HOST"] = "10.255.255.1"
    variables["POSTGRES_PORT"] = "5432"
    variables["DB_CONNECT_TIMEOUT_S"] = str(limite_s)

    inicio = time.monotonic()
    try:
        resultado = _correr_comando(variables, tope_s=60)
    except subprocess.TimeoutExpired:
        pytest.fail("el comando siguió esperando después de DB_CONNECT_TIMEOUT_S")
    duracion_s = time.monotonic() - inicio

    assert resultado.returncode == 5, resultado.stderr[-2000:]
    assert duracion_s < limite_s + 30, duracion_s
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr, "10.255.255.1")


# 2d: todo valor es ficticio; nunca se leen archivos de entorno.
@pytest.mark.parametrize(
    "usuario,emisor,esperado",
    [
        ("user_Dev123", None, 3),
        ("otra_forma", "https://x.clerk.accounts.dev", 2),
        ("user_", "https://x.clerk.accounts.dev", 2),
        ("user_" + "a" * 65, "https://x.clerk.accounts.dev", 2),
        ("user_ñ", "https://x.clerk.accounts.dev", 2),
        ("user_abc\n", "https://x.clerk.accounts.dev", 2),
        *[
            ("user_Dev123", emisor, 3)
            for emisor in (
                "",
                "https://produccion.invalid",
                "https://x.clerk.accounts.dev.evil.com",
                "https://u:p@x.clerk.accounts.dev",
                "https://x.clerk.accounts.dev?x=1",
                "https://x.clerk.accounts.dev#f",
                "https://x.clerk.accounts.dev/ruta",
                "https://x.clerk.accounts.dev:puerto",
                "https://x.clerk.accounts.dev:8443",
                "http://x.clerk.accounts.dev",
                "https://x.clerk.accounts.dev?",
                "https://x.clerk.accounts.dev#",
            )
        ],
        *[
            ("user_Dev123", emisor, "conectó")
            for emisor in (
                "https://X.CLERK.ACCOUNTS.DEV",
                "https://x.clerk.accounts.dev/",
                "https://x.clerk.accounts.dev:443",
            )
        ],
    ],
)
def test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    usuario: str,
    emisor: str | None,
    esperado: int | str,
) -> None:
    monkeypatch.setenv("PROPTECH_ENTORNO", "desarrollo")
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(_PARAMETROS))
    if emisor is None:
        monkeypatch.delenv("CLERK_EMISOR", raising=False)
    else:
        monkeypatch.setenv("CLERK_EMISOR", emisor)
    for campo, valor in {
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": "1",
        "POSTGRES_DB": "proptech_ficticia",
        "POSTGRES_APP_USER": APP_USER_DE_SESION,
        "POSTGRES_APP_PASSWORD": APP_PASSWORD_DE_SESION,
    }.items():
        monkeypatch.setenv(campo, valor)

    class ConexionIntentada(BaseException):
        """`BaseException`, para que no la tape el código 9 de una excepción no prevista."""

    def conectar(_: ConfiguracionDelEjemplo) -> Engine:
        raise ConexionIntentada

    monkeypatch.setattr(ejemplo, "crear_engine", conectar)
    try:
        resultado: int | str = ejemplo._main(["cargar", "--clerk-usuario", usuario])
    except ConexionIntentada:
        resultado = "conectó"
    assert os.environ.get("CLERK_EMISOR") == emisor
    salida = capsys.readouterr()
    assert usuario not in salida.out + salida.err
    if emisor:
        assert emisor not in salida.out + salida.err
    assert resultado == esperado


def test_opcion_no_salta_guarda(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PROPTECH_ENTORNO", raising=False)

    def conectar(_: ConfiguracionDelEjemplo) -> Engine:
        pytest.fail("la guarda debe correr antes de conectar")

    monkeypatch.setattr(ejemplo, "crear_engine", conectar)
    assert ejemplo._main(["cargar", "--clerk-usuario", "user_Dev123"]) == 1
    assert "user_Dev123" not in str(capsys.readouterr())


@pytest.mark.parametrize(
    "argv",
    [
        # B-2 (rompedor, vuelta 1): typo en el nombre de la opción.
        ["cargar", "--clerk-usuarios", "user_Dev123"],
        # el id como posicional extra.
        ["cargar", "user_Dev123"],
        # abreviatura de `--clerk-usuario`: `allow_abbrev` por defecto la acepta.
        ["cargar", "--clerk", "user_Dev123"],
        # el id en el lugar del subcomando: argparse lo repetía en `invalid choice`.
        ["user_Dev123"],
    ],
)
def test_argumentos_no_reconocidos_no_repiten_el_id(
    capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    """B-2 (rompedor, vuelta 1): con un error de tipeo, argparse imprimía el
    id de Clerk tal cual en `unrecognized arguments`, y con `allow_abbrev`
    (activo por defecto) aceptaba `--clerk` como si fuera `--clerk-usuario`.
    El mensaje ahora es fijo y la abreviatura ya no se reconoce."""
    with pytest.raises(SystemExit) as salida:
        ejemplo._main(argv)
    assert salida.value.code == 2
    capturado = capsys.readouterr()
    assert "user_Dev123" not in capturado.out + capturado.err


def _cargar_con_usuario(
    fabrica: sessionmaker[Session], usuario: str | None = None
) -> ejemplo.ResultadoCarga:
    return ejemplo.cargar(
        fabrica,
        parametros=_parametros(),
        semilla=_semilla(),
        georef=_georef(),
        request_id=uuid4(),
        clerk_usuario=usuario,
    )


def _usuario_ejemplo(fabrica: sessionmaker[Session]) -> str | None:
    with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion:
        return cast(
            str | None,
            sesion.execute(
                text("SELECT clerk_usuario_id FROM persona WHERE id=:id"),
                {"id": ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID},
            ).scalar_one(),
        )


@pytest.mark.parametrize("ya_cargado", [False, True])
def test_vincular_primera_carga_o_existente_e_idempotencia(
    base_fresca: BaseDeEdificio, ya_cargado: bool
) -> None:
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        if ya_cargado:
            _cargar_con_usuario(fabrica)
        _cargar_con_usuario(fabrica, "user_Dev123")
        assert _usuario_ejemplo(fabrica) == "user_Dev123"
        antes = {
            t: _contar(fabrica, t, ejemplo.ADMINISTRACION_EJEMPLO_ID)
            for t in ("persona", "unidad", "asignacion_rol", "auditoria")
        }
        _cargar_con_usuario(fabrica, "user_Dev123")
        assert _usuario_ejemplo(fabrica) == "user_Dev123"
        assert antes == {t: _contar(fabrica, t, ejemplo.ADMINISTRACION_EJEMPLO_ID) for t in antes}
        error = None
        try:
            _cargar_con_usuario(fabrica, "user_Otro456")
        except Exception as e:
            error = e
        assert error is not None and "otra cuenta" in str(error)
        assert _usuario_ejemplo(fabrica) == "user_Dev123"
    finally:
        engine.dispose()


def _entorno_clerk(monkeypatch: pytest.MonkeyPatch, base: BaseDeEdificio) -> None:
    for variable, valor in _entorno_del_comando(
        base, usuario=APP_USER_DE_SESION, clave=APP_PASSWORD_DE_SESION, entorno="desarrollo"
    ).items():
        monkeypatch.setenv(variable, valor)
    monkeypatch.setenv("CLERK_EMISOR", "https://x.clerk.accounts.dev")


def test_el_id_de_otra_persona_es_error_propio_sin_datos(
    base_fresca: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _entorno_clerk(monkeypatch, base_fresca)
    assert ejemplo._main(["cargar"]) == 0
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as sesion, sesion.begin():
            sesion.execute(
                text(
                    "INSERT INTO persona(administracion_id,nombre,clerk_usuario_id) "
                    "VALUES (:admin,'Otra ficticia','user_Dev123')"
                ),
                {"admin": ejemplo.ADMINISTRACION_EJEMPLO_ID},
            )
        antes = _filas_escritas(base_fresca)
        from sqlalchemy import event

        sentencias: list[str] = []

        def espia(configuracion: ConfiguracionDelEjemplo) -> Engine:
            motor = crear_engine(configuracion)
            event.listen(motor, "before_cursor_execute", lambda *args: sentencias.append(args[2]))
            return motor

        monkeypatch.setattr(ejemplo, "crear_engine", espia)
        resultado = ejemplo._main(["cargar", "--clerk-usuario", "user_Dev123"])
        salida = capsys.readouterr()
        assert resultado == 7
        assert any("SELECT id FROM persona WHERE clerk_usuario_id" in sql for sql in sentencias)
        assert not any("UPDATE persona SET clerk_usuario_id" in sql for sql in sentencias)
        assert "esa cuenta ya está vinculada a otra persona del ejemplo" in salida.err
        assert all(
            v not in salida.out + salida.err for v in ("user_Dev123", "Traceback", "[parameters:")
        )
        assert _usuario_ejemplo(fabrica) is None
        assert _filas_escritas(base_fresca) == antes
    finally:
        engine.dispose()


def test_carrera_de_unicidad_se_traduce_sin_parametros(
    base_fresca: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from sqlalchemy import event

    _entorno_clerk(monkeypatch, base_fresca)
    assert ejemplo._main(["cargar"]) == 0
    engine, fabrica = _fabrica_app(base_fresca)
    otra = uuid4()
    with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as s, s.begin():
        s.execute(
            text(
                "INSERT INTO persona(id,administracion_id,nombre) VALUES (:id,:a,'Otra ficticia')"
            ),
            {"id": otra, "a": ejemplo.ADMINISTRACION_EJEMPLO_ID},
        )
    disparo: list[bool] = []

    def carrera(*args: object) -> None:
        if "UPDATE persona SET clerk_usuario_id" in str(args[2]) and not disparo:
            disparo.append(True)
            with base_fresca.conectar_app() as c, c.transaction():
                c.execute(
                    "SELECT set_config('app.administracion_id',%s,true)",
                    (str(ejemplo.ADMINISTRACION_EJEMPLO_ID),),
                )
                c.execute("UPDATE persona SET clerk_usuario_id='user_Dev123' WHERE id=%s", (otra,))

    event.listen(engine, "before_cursor_execute", carrera)
    monkeypatch.setattr(ejemplo, "crear_engine", lambda _: engine)
    try:
        resultado = ejemplo._main(["cargar", "--clerk-usuario", "user_Dev123"])
        salida = capsys.readouterr()
        assert resultado == 7
        assert disparo == [True]
        assert "esa cuenta ya está vinculada a otra persona del ejemplo" in salida.err
        assert all(
            v not in salida.out + salida.err for v in ("user_Dev123", "Traceback", "[parameters:")
        )
        assert _usuario_ejemplo(fabrica) is None
    finally:
        engine.dispose()


def test_dos_vinculaciones_a_la_vez_no_pisan_a_la_ganadora(base_fresca: BaseDeEdificio) -> None:
    from sqlalchemy import event

    engine, fabrica = _fabrica_app(base_fresca)
    _cargar_con_usuario(fabrica)
    barrera = threading.Barrier(2, timeout=15)

    def esperar(*args: object) -> None:
        if "SELECT clerk_usuario_id FROM persona WHERE id" in str(args[2]):
            barrera.wait()

    event.listen(engine, "after_cursor_execute", esperar)
    resultados: list[tuple[str, bool]] = []

    def correr(usuario: str) -> None:
        try:
            _cargar_con_usuario(fabrica, usuario)
            resultados.append((usuario, True))
        except Exception:
            resultados.append((usuario, False))

    hilos = [threading.Thread(target=correr, args=(u,)) for u in ("user_Uno", "user_Dos")]
    try:
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=25)
        event.remove(engine, "after_cursor_execute", esperar)
        assert sorted(ok for _, ok in resultados) == [False, True]
        assert _usuario_ejemplo(fabrica) == next(u for u, ok in resultados if ok)
    finally:
        engine.dispose()


def test_conflicto_al_crear_revierte_toda_la_carga(
    base_fresca: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typing import Any

    original = ejemplo._crear_desde_cero

    def con_vinculo(sesion: Session, identidad: Any, **kwargs: Any) -> UUID:
        complejo = original(sesion, identidad, **kwargs)
        sesion.execute(
            text("UPDATE persona SET clerk_usuario_id='user_Otra' WHERE id=:id"),
            {"id": ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID},
        )
        return complejo

    monkeypatch.setattr(ejemplo, "_crear_desde_cero", con_vinculo)
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        error = None
        try:
            _cargar_con_usuario(fabrica, "user_Dev123")
        except Exception as e:
            error = e
        assert error is not None and "otra cuenta" in str(error)
        assert _filas_escritas(base_fresca) == _SIN_ESCRITURAS
    finally:
        engine.dispose()


def test_entrar_con_la_cuenta_vinculada(
    base_fresca: BaseDeEdificio, clerk_falso: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from fastapi.testclient import TestClient

    from proptech_api.app import crear_app

    from ._clerk import encabezados, sub_de

    assert isinstance(clerk_falso, rsa.RSAPrivateKey)
    _entorno_clerk(monkeypatch, base_fresca)
    usuario = sub_de(clerk_falso)
    assert ejemplo._main(["cargar", "--clerk-usuario", usuario]) == 0
    with TestClient(crear_app()) as cliente:
        r = cliente.get(
            "/api/sesion", headers=encabezados(clerk_falso, iss="https://x.clerk.accounts.dev")
        )
        assert r.status_code == 200
        assert [a["id"] for a in r.json()["administraciones"]] == [
            str(ejemplo.ADMINISTRACION_EJEMPLO_ID)
        ]


@pytest.mark.parametrize("otra_administracion", [False, True])
def test_la_funcion_de_vinculacion_rechaza_otra_persona_sin_escribir(
    base_fresca: BaseDeEdificio, otra_administracion: bool
) -> None:
    from proptech_core.acceso.aplicacion.vinculacion_de_desarrollo import vincular

    engine, fabrica = _fabrica_app(base_fresca)
    try:
        _cargar_con_usuario(fabrica)
        otra = uuid4()
        with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as s, s.begin():
            s.execute(
                text(
                    "INSERT INTO persona(id,administracion_id,nombre) "
                    "VALUES (:id,:a,'Otra ficticia')"
                ),
                {"id": otra, "a": ejemplo.ADMINISTRACION_EJEMPLO_ID},
            )
        error = None
        with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as s, s.begin():
            try:
                vincular(
                    s,
                    uuid4() if otra_administracion else ejemplo.ADMINISTRACION_EJEMPLO_ID,
                    ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID if otra_administracion else otra,
                    "user_Dev123",
                )
            except Exception as e:
                error = e
            assert error is not None
            assert (
                s.execute(
                    text("SELECT clerk_usuario_id FROM persona WHERE id=:id"), {"id": otra}
                ).scalar_one()
                is None
            )
    finally:
        engine.dispose()


def test_vincular_el_mismo_id_otra_vez_no_escribe_la_fila(base_fresca: BaseDeEdificio) -> None:
    """B-1 (rompedor, vuelta 1): la spec de `acceso-de-desarrollo` pide que
    vincular dos veces el mismo id "no hace nada / sin escribir". Contar
    filas no alcanza -- el `UPDATE` condicional coincidía igual cuando el id
    ya era el mismo y Postgres escribía una versión nueva de la fila (el
    rompedor lo midió con `xmin`: 764 antes, 782 después). Esta vez se
    compara `xmin`, que sólo cambia si hubo una escritura real."""
    from proptech_core.acceso.aplicacion.vinculacion_de_desarrollo import vincular

    engine, fabrica = _fabrica_app(base_fresca)
    try:
        _cargar_con_usuario(fabrica, "user_Dev123")
        with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as s:
            xmin_antes = s.execute(
                text("SELECT xmin::text FROM persona WHERE id=:id"),
                {"id": ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID},
            ).scalar_one()

        with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as s, s.begin():
            resultado = vincular(
                s,
                ejemplo.ADMINISTRACION_EJEMPLO_ID,
                ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID,
                "user_Dev123",
            )
        assert resultado == "ya estaba vinculado"

        with abrir_sesion(fabrica, ejemplo.ADMINISTRACION_EJEMPLO_ID) as s:
            xmin_despues = s.execute(
                text("SELECT xmin::text FROM persona WHERE id=:id"),
                {"id": ejemplo.PERSONA_SUPER_ADMIN_EJEMPLO_ID},
            ).scalar_one()
        assert xmin_despues == xmin_antes
    finally:
        engine.dispose()


def test_mensajes_de_vinculacion_no_imprimen_el_id(
    base_fresca: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _entorno_clerk(monkeypatch, base_fresca)
    assert ejemplo._main(["cargar", "--clerk-usuario", "user_Dev123"]) == 0
    primera = capsys.readouterr()
    assert "vinculado" in primera.out
    assert "user_Dev123" not in primera.out + primera.err
    assert ejemplo._main(["cargar", "--clerk-usuario", "user_Dev123"]) == 0
    segunda = capsys.readouterr()
    assert "ya estaba vinculado" in segunda.out
    assert "user_Dev123" not in segunda.out + segunda.err


def test_otro_integrity_error_no_se_disfraza_de_cuenta_ajena(
    base_fresca: BaseDeEdificio,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _entorno_clerk(monkeypatch, base_fresca)
    assert ejemplo._main(["cargar"]) == 0
    with base_fresca.conectar_migrador() as c:
        c.execute(
            "ALTER TABLE persona ADD CONSTRAINT ck_solo_nulo_de_prueba "
            "CHECK (clerk_usuario_id IS NULL)"
        )
    resultado = ejemplo._main(["cargar", "--clerk-usuario", "user_Dev123"])
    salida = capsys.readouterr()
    assert resultado == 8
    assert "no se pudo completar la carga" in salida.err
    assert "otra persona del ejemplo" not in salida.err
    assert all(
        v not in salida.out + salida.err for v in ("user_Dev123", "Traceback", "[parameters:")
    )
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        assert _usuario_ejemplo(fabrica) is None
    finally:
        engine.dispose()


# --- Cada familia de error con su código (`ejemplo-robusto`, BE-3, D4) ---


def _error_del_driver(tipo: type[sqlalchemy.exc.DBAPIError]) -> sqlalchemy.exc.DBAPIError:
    """Con el valor sembrado en la sentencia, en los parámetros y en el error del
    driver: las tres cosas que SQLAlchemy imprime en `str(error)`."""
    return tipo(
        f"INSERT INTO persona VALUES ('{_VALOR_SEMBRADO}')",  # noqa: S608
        {"clave": _VALOR_SEMBRADO},
        Exception(_VALOR_SEMBRADO),
    )


@pytest.mark.parametrize(
    "excepcion,codigo,mensaje",
    [
        pytest.param(
            lambda: ejemplo.EjemploDistinto("unidades[1A]: difiere de la semilla"),
            6,
            "unidades[1A]",
            id="ejemplo_distinto",
        ),
        pytest.param(
            lambda: VinculacionDeDesarrolloNoDisponible("el ejemplo ya está vinculado"),
            7,
            "ya está vinculado",
            id="vinculacion_rechazada",
        ),
        pytest.param(
            lambda: _error_del_driver(sqlalchemy.exc.IntegrityError),
            8,
            "no se pudo completar la carga",
            id="integridad",
        ),
        pytest.param(
            lambda: _error_del_driver(sqlalchemy.exc.DBAPIError),
            8,
            "no se pudo completar la carga",
            id="otro_error_de_la_base",
        ),
        pytest.param(
            lambda: ejemplo.EsperaAgotada("existe sin edificio"),
            8,
            "existe sin edificio",
            id="espera_agotada",
        ),
        pytest.param(
            lambda: _error_del_driver(sqlalchemy.exc.OperationalError),
            5,
            "no está disponible",
            id="base_cortada_durante_la_carga",
        ),
        pytest.param(
            lambda: EntradaInvalida("pisos", _VALOR_SEMBRADO),
            3,
            "no se pueden cargar: pisos;",
            id="rechazo_del_caso_de_uso",
        ),
        pytest.param(
            lambda: RuntimeError(_VALOR_SEMBRADO), 9, "RuntimeError", id="inesperada_runtime"
        ),
        pytest.param(lambda: KeyError(_VALOR_SEMBRADO), 9, "KeyError", id="inesperada_clave"),
    ],
)
def test_cada_familia_de_error_de_la_carga_tiene_su_codigo(
    ejemplo_cargado: _EjemploCargado,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    excepcion: Callable[[], Exception],
    codigo: int,
    mensaje: str,
) -> None:
    """Con un doble que lanza dentro de `cargar`, y la verificación de la base real.
    Cada error lleva sembrado un texto que no tiene que salir."""
    _entorno_clerk(monkeypatch, ejemplo_cargado.base)

    def _lanzar(*_: object, **__: object) -> ejemplo.ResultadoCarga:
        raise excepcion()

    monkeypatch.setattr(ejemplo, "cargar", _lanzar)

    assert _codigo_de_main("--clerk-usuario", "user_Sembrado1") == codigo
    salida = capsys.readouterr()
    assert mensaje in salida.err
    _afirmar_salida_limpia(
        salida.out + salida.err,
        _VALOR_SEMBRADO,
        APP_PASSWORD_DE_SESION,
        "user_Sembrado1",
        "x.clerk.accounts.dev",
    )


def test_un_value_error_no_previsto_en_la_carga_termina_con_9(
    base_fresca: BaseDeEdificio,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """F10 de verify 2: `EntradaInvalida` hereda de `ValueError`, pero sólo ella es la familia
    del 3. Cualquier otro `ValueError` dentro de la carga real es lo no previsto de D4: sale
    con 9, nombra sólo su tipo y no deja nada escrito. Distingue `except EntradaInvalida` de
    un `except ValueError` más ancho (mutante B7)."""
    _entorno_clerk(monkeypatch, base_fresca)

    def _lanzar(*_: object, **__: object) -> NoReturn:
        raise ValueError(_VALOR_SEMBRADO)

    monkeypatch.setattr(ejemplo, "crear_grupo", _lanzar)

    assert _codigo_de_main() == 9
    salida = capsys.readouterr()
    assert salida.err.strip() == "error inesperado: ValueError"
    _afirmar_salida_limpia(salida.out + salida.err, _VALOR_SEMBRADO, APP_PASSWORD_DE_SESION)
    assert _filas_escritas(base_fresca) == _SIN_ESCRITURAS


def test_una_excepcion_no_prevista_al_leer_los_archivos_termina_con_9(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Antes, cualquier excepción de esta parte se imprimía entera y salía con 1."""
    _configuracion_valida(monkeypatch)
    monkeypatch.setenv("PROPTECH_ENTORNO", "desarrollo")

    def _lanzar(_: str) -> Georef:
        raise PermissionError(_VALOR_SEMBRADO)

    monkeypatch.setattr(ejemplo, "leer_georef", _lanzar)

    assert _codigo_de_main() == 9
    salida = capsys.readouterr()
    assert "PermissionError" in salida.err
    _afirmar_salida_limpia(salida.out + salida.err, _VALOR_SEMBRADO)


_IDENTIFICADOR_LARGO = "L" * 41


def _semilla_con_pisos_cero(texto: str) -> str:
    assert "pisos: 4" in texto
    texto = texto.replace("pisos: 4", "pisos: 0")
    for piso in "1234":
        texto = texto.replace(f'piso: "{piso}"', 'piso: "PB"')
    return texto


def _semilla_con_identificador_largo(texto: str) -> str:
    assert 'identificador: "L-PB"' in texto
    return texto.replace('identificador: "L-PB"', f'identificador: "{_IDENTIFICADOR_LARGO}"')


def _semilla_confirmada(texto: str) -> str:
    assert "estado_migracion: sin_saldos_previos" in texto
    return texto.replace("estado_migracion: sin_saldos_previos", "estado_migracion: confirmada")


@pytest.mark.parametrize(
    "alterar,campo",
    [
        pytest.param(_semilla_con_pisos_cero, "pisos", id="pisos_cero"),
        pytest.param(_semilla_con_identificador_largo, "identificador", id="identificador_largo"),
        pytest.param(_semilla_confirmada, "estado_migracion", id="confirmada"),
    ],
)
def test_la_semilla_que_el_caso_de_uso_rechaza_termina_con_3(
    base_fresca: BaseDeEdificio, tmp_path: Path, alterar: Callable[[str], str], campo: str
) -> None:
    """Escenario "El caso de uso rechaza la semilla" (F2 de verify 1, D10): el lector la deja
    pasar y la carga la rechaza. Ya se conectó, y la transacción revierte."""
    archivo = tmp_path / "semilla.yaml"
    archivo.write_text(alterar(_SEMILLA.read_text(encoding="utf-8")), encoding="utf-8")

    resultado = _correr_comando(
        _entorno_del_comando(
            base_fresca,
            usuario=APP_USER_DE_SESION,
            clave=APP_PASSWORD_DE_SESION,
            entorno="desarrollo",
        ),
        "--semilla",
        str(archivo),
    )

    assert resultado.returncode == 3, resultado.stderr[-2000:]
    assert resultado.stderr.strip() == (
        f"la semilla o los parámetros no se pueden cargar: {campo}; no se escribió nada"
    )
    assert _filas_escritas(base_fresca) == _SIN_ESCRITURAS


@pytest.mark.parametrize(
    "donde", ["_leer_argumentos", "crear_engine", "verificar_rol_de_aplicacion_seguro"]
)
def test_ctrl_c_termina_con_130_sin_prometer_que_no_se_escribio(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], donde: str
) -> None:
    """Escenario "Se interrumpe con Ctrl-C" (F3 de verify 1, D10). No puede decir que no se
    escribió nada, porque la interrupción puede llegar después del commit. `donde` cubre
    antes de `_ejecutar`, antes de su `try` y adentro, con el `finally` que cierra el engine."""
    _configuracion_valida(monkeypatch)
    monkeypatch.setenv("PROPTECH_ENTORNO", "desarrollo")

    def _ctrl_c(*_: object, **__: object) -> NoReturn:
        raise KeyboardInterrupt

    monkeypatch.setattr(ejemplo, donde, _ctrl_c)
    try:
        codigo = ejemplo._main(["cargar"])
    except KeyboardInterrupt:
        # Sin esto, un `KeyboardInterrupt` que se escapa corta la corrida entera de pytest.
        pytest.fail("_main dejó escapar KeyboardInterrupt")

    assert codigo == 130
    salida = capsys.readouterr()
    assert "a medias" in salida.err
    assert "no se escribió nada" not in salida.err
    _afirmar_salida_limpia(salida.out + salida.err)


def test_ctrl_c_en_el_proceso_termina_con_130_sin_traceback() -> None:
    """Con `main()`, que es lo que corre `python -m`. Sin capturar, Python imprime el traceback
    y termina con otro código. La interrupción es un doble, no una señal real: en Windows no
    se puede mandar a un proceso aislado."""
    programa = (
        "import sys\n"
        "from proptech_core.complejos.aplicacion import ejemplo\n"
        "def _ctrl_c(*_):\n"
        "    raise KeyboardInterrupt\n"
        "ejemplo.crear_engine = _ctrl_c\n"
        "sys.argv = ['ejemplo', 'cargar']\n"
        "ejemplo.main()\n"
    )

    resultado = subprocess.run(
        [sys.executable, "-c", programa],
        cwd=_BACKEND,
        env=_entorno_con_base_cerrada(),
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert resultado.returncode == 130, resultado.stderr[-2000:]
    assert "a medias" in resultado.stderr, resultado.stderr[-2000:]
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr)


def test_el_comando_real_con_el_ejemplo_distinto_termina_con_6(
    ejemplo_cargado: _EjemploCargado, tmp_path: Path
) -> None:
    """Escenario "El ejemplo es distinto", con la comparación real: la semilla alterada
    va en un archivo, como la pasaría una persona, y la base compartida no se toca."""
    alterada = tmp_path / "semilla.yaml"
    texto = _SEMILLA.read_text(encoding="utf-8")
    assert "estado_migracion: sin_saldos_previos" in texto
    alterada.write_text(
        texto.replace("estado_migracion: sin_saldos_previos", "estado_migracion: pendiente"),
        encoding="utf-8",
    )
    antes = _conteos_del_ejemplo(ejemplo_cargado.fabrica)

    resultado = _correr_comando(
        _entorno_del_comando(
            ejemplo_cargado.base,
            usuario=APP_USER_DE_SESION,
            clave=APP_PASSWORD_DE_SESION,
            entorno="desarrollo",
        ),
        "--semilla",
        str(alterada),
    )

    assert resultado.returncode == 6, resultado.stderr[-2000:]
    assert "estado_migracion" in resultado.stderr
    _afirmar_salida_limpia(resultado.stdout + resultado.stderr, APP_PASSWORD_DE_SESION)
    assert _conteos_del_ejemplo(ejemplo_cargado.fabrica) == antes


def test_el_comando_real_con_la_espera_agotada_termina_con_8(base_fresca: BaseDeEdificio) -> None:
    """Escenario "La carga no se completa", espera agotada: el `RuntimeError` que antes
    salía como traceback. Son los 50 intentos reales, unos 5 segundos."""
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        _alta_sin_edificio(fabrica)
        antes = _conteos_del_ejemplo(fabrica)

        resultado = _correr_comando(
            _entorno_del_comando(
                base_fresca,
                usuario=APP_USER_DE_SESION,
                clave=APP_PASSWORD_DE_SESION,
                entorno="desarrollo",
            )
        )

        assert resultado.returncode == 8, resultado.stderr[-2000:]
        assert "sin edificio" in resultado.stderr
        _afirmar_salida_limpia(resultado.stdout + resultado.stderr, APP_PASSWORD_DE_SESION)
        assert _conteos_del_ejemplo(fabrica) == antes
    finally:
        engine.dispose()


def test_el_comando_espera_de_verdad_antes_de_rendirse(
    base_fresca: BaseDeEdificio,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Escenario "La administración de ejemplo quedó sin edificio", con los valores por
    defecto de `cargar`, que son los del comando (F6 de verify 1): los otros dos tests
    de la espera pasan `intentos` a mano. Cuenta las esperas en lugar de medir el reloj."""
    esperas: list[float] = []
    monkeypatch.setattr(ejemplo, "time", SimpleNamespace(sleep=esperas.append))
    _entorno_clerk(monkeypatch, base_fresca)
    engine, fabrica = _fabrica_app(base_fresca)
    try:
        _alta_sin_edificio(fabrica)

        assert _codigo_de_main() == 8

        assert "sin edificio" in capsys.readouterr().err
        assert esperas == [0.1] * 50
    finally:
        engine.dispose()


def test_el_ejemplo_ya_vinculado_a_otra_cuenta_termina_con_7(
    base_fresca: BaseDeEdificio,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Escenario "Vinculación rechazada", su otra mitad: los dos tests de arriba cubren
    la cuenta ya vinculada a otra persona."""
    _entorno_clerk(monkeypatch, base_fresca)
    assert ejemplo._main(["cargar", "--clerk-usuario", "user_Primero1"]) == 0
    capsys.readouterr()

    assert _codigo_de_main("--clerk-usuario", "user_Segundo2") == 7
    salida = capsys.readouterr()
    assert "otra cuenta" in salida.err
    _afirmar_salida_limpia(salida.out + salida.err, "user_Primero1", "user_Segundo2")
