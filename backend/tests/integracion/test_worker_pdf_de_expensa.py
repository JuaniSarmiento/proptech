"""La tarea `generar_pdf_de_expensa` y el barrido de pendientes del worker (7, H-015, E12).

Contra PostgreSQL real y WeasyPrint real, sin Redis: el `ctx` se arma a mano (la fábrica con el
tenant por transacción, como la del worker) y la cola es un doble que anota lo que se le encola.
"""

import asyncio
import hashlib
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from proptech_core.compartido.base_de_datos import (
    crear_fabrica_de_sesiones,
    registrar_tenant_por_administracion,
)
from proptech_core.compartido.reintentos import PoliticaReintentos
from proptech_worker import tareas
from proptech_worker.tareas import (
    ArgumentoDeTareaInvalido,
    barrido_de_documentos_pendientes,
    generar_pdf_de_expensa,
)

from ._cuenta_corriente import Mundo, sembrar
from ._documentos import Liquidada, documento, liquidar
from ._edificios import BaseDeEdificio, fijar_tenant

pytestmark = pytest.mark.integracion


class ColaQueAnota:
    def __init__(self) -> None:
        self.llamadas: list[tuple[str, dict[str, Any]]] = []

    async def encolar(self, tarea: str, **datos: Any) -> None:
        self.llamadas.append((tarea, datos))


@pytest.fixture(scope="module")
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio, unidades=2, con_configuracion=True)


@pytest.fixture(scope="module")
def liquidada(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> Liquidada:
    return liquidar(base_del_edificio, mundo)


@pytest.fixture(scope="module")
def liquidada_b(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> Liquidada:
    return liquidar(base_del_edificio, mundo, de_b=True)


@pytest.fixture
def fabrica(base_del_edificio: BaseDeEdificio) -> Iterator[sessionmaker[Session]]:
    def conectar() -> psycopg.Connection:
        conexion = base_del_edificio.conectar_app()
        conexion.autocommit = False  # el tenant es local a la transacción (set_config ..., true)
        return conexion

    engine = create_engine("postgresql+psycopg://", creator=conectar, poolclass=NullPool)
    fabrica = crear_fabrica_de_sesiones(engine)
    registrar_tenant_por_administracion(fabrica)
    yield fabrica
    engine.dispose()


def _ctx(fabrica: sessionmaker[Session], cola: ColaQueAnota | None = None) -> dict[str, Any]:
    return {
        "fabrica_de_sesiones": fabrica,
        "politica": PoliticaReintentos(espera_base=0.01, intentos_maximos=3),
        "job_try": 1,
        "cola": cola or ColaQueAnota(),
    }


def _generar(fabrica: sessionmaker[Session], admin: UUID, doc: UUID, clave: str) -> Any:
    return asyncio.run(
        generar_pdf_de_expensa(
            _ctx(fabrica),
            request_id=str(uuid4()),
            clave=clave,
            administracion_id=str(admin),
            documento_id=str(doc),
        )
    )


def _archivado(base: BaseDeEdificio, admin: UUID, doc: UUID) -> list[tuple[str, str, bytes]]:
    with base.conectar_app() as c, c.transaction():
        fijar_tenant(c, admin)
        filas = c.execute(
            "SELECT d.estado, p.sha256, p.contenido FROM documento_de_expensa d "
            "LEFT JOIN pdf_de_expensa p ON p.documento_id = d.id WHERE d.id = %s",
            (doc,),
        ).fetchall()
    return [(str(e), s, bytes(b)) for e, s, b in filas if s is not None]


def test_la_tarea_genera_y_archiva_el_pdf_una_sola_vez(
    base_del_edificio: BaseDeEdificio,
    mundo: Mundo,
    liquidada: Liquidada,
    fabrica: sessionmaker[Session],
) -> None:
    doc = documento(base_del_edificio, mundo, liquidada, "completa")
    assert _generar(fabrica, mundo.admin, doc, f"pdf:{doc}:e") is True
    [(estado, sha, contenido)] = _archivado(base_del_edificio, mundo.admin, doc)
    assert estado == "generado" and contenido.startswith(b"%PDF")
    assert sha == hashlib.sha256(contenido).hexdigest()
    # La misma clave ya estaba hecha; y otra clave (un reencolado) no reescribe nada.
    assert _generar(fabrica, mundo.admin, doc, f"pdf:{doc}:e") is False
    assert _generar(fabrica, mundo.admin, doc, f"pdf:{doc}:r1") is True
    assert _archivado(base_del_edificio, mundo.admin, doc) == [(estado, sha, contenido)]


def test_la_tarea_pasa_por_el_corte_de_la_base(monkeypatch: pytest.MonkeyPatch) -> None:
    visto: dict[str, Any] = {}

    def espiado(fabrica: Any, **kwargs: Any) -> bool:
        visto.update(kwargs)
        return True

    monkeypatch.setattr(tareas, "ejecutar_con_corte", espiado)
    mundo_id, doc = uuid4(), uuid4()
    asyncio.run(
        generar_pdf_de_expensa(
            _ctx(None),  # type: ignore[arg-type]
            request_id=str(uuid4()),
            clave="c",
            administracion_id=str(mundo_id),
            documento_id=str(doc),
        )
    )
    assert visto["administracion_id"] == mundo_id
    assert visto["cota_s"] == tareas.COTA_GENERAR_PDF_S < 60
    assert visto["tarea"] == "generar_pdf_de_expensa"
    assert visto["clave"] == f"{mundo_id}:c", "la clave lleva la administración (E3 del 2a)"


@pytest.mark.parametrize("documento_id", ["no-es-un-uuid", 5, None])
def test_un_documento_mal_formado_no_toca_la_base(
    fabrica: sessionmaker[Session], documento_id: Any
) -> None:
    with pytest.raises(ArgumentoDeTareaInvalido, match="documento_id"):
        asyncio.run(
            generar_pdf_de_expensa(
                _ctx(fabrica),
                request_id=str(uuid4()),
                clave="c",
                administracion_id=str(uuid4()),
                documento_id=documento_id,
            )
        )


def test_el_barrido_reencola_lo_pendiente_de_todas_las_administraciones(
    base_del_edificio: BaseDeEdificio,
    mundo: Mundo,
    liquidada: Liquidada,
    liquidada_b: Liquidada,
    fabrica: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sin_generar = documento(base_del_edificio, mundo, liquidada, "sin_extraordinaria")
    de_b = documento(base_del_edificio, mundo, liquidada_b, "completa", de_b=True)
    cola = ColaQueAnota()
    # Recién creados: el encolado de la emisión está en camino, el barrido todavía no los toca.
    assert asyncio.run(barrido_de_documentos_pendientes(_ctx(fabrica, cola))) == 0
    monkeypatch.setattr(tareas, "ANTIGUEDAD_DEL_BARRIDO_S", 0)
    encolados = asyncio.run(barrido_de_documentos_pendientes(_ctx(fabrica, cola)))
    por_documento = {d["documento_id"]: d for _, d in cola.llamadas}
    assert encolados == len(cola.llamadas) >= 2
    assert {t for t, _ in cola.llamadas} == {"generar_pdf_de_expensa"}
    assert por_documento[str(sin_generar)]["administracion_id"] == str(mundo.admin)
    assert por_documento[str(de_b)]["administracion_id"] == str(mundo.admin_b)
    assert all(d["clave"].startswith(f"pdf:{d['documento_id']}:b") for d in por_documento.values())
    # Lo generado no se reencola.
    asyncio.run(
        generar_pdf_de_expensa(
            _ctx(fabrica),
            request_id=str(uuid4()),
            clave="g",
            administracion_id=str(mundo.admin),
            documento_id=str(sin_generar),
        )
    )
    cola.llamadas.clear()
    asyncio.run(barrido_de_documentos_pendientes(_ctx(fabrica, cola)))
    assert str(sin_generar) not in {d["documento_id"] for _, d in cola.llamadas}
