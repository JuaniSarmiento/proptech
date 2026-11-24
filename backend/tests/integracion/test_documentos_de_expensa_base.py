"""La base de los documentos de expensa (7, H-015, `0043`, E12): el archivo no se reescribe, el
aislamiento por administración y el barrido que lee lo `pendiente` de todas."""

import hashlib
from uuid import UUID

import psycopg
import pytest

from ._cuenta_corriente import Mundo, sembrar
from ._documentos import Liquidada, documento, liquidar
from ._edificios import BaseDeEdificio, fijar_tenant

pytestmark = pytest.mark.integracion

_PDF = b"%PDF-1.7 contenido ficticio"


@pytest.fixture(scope="module")
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio, unidades=2, con_configuracion=True)


@pytest.fixture(scope="module")
def liquidada(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> Liquidada:
    return liquidar(base_del_edificio, mundo)


@pytest.fixture(scope="module")
def liquidada_b(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> Liquidada:
    return liquidar(base_del_edificio, mundo, de_b=True)


@pytest.fixture(scope="module")
def pendiente_de_b(base_del_edificio: BaseDeEdificio, mundo: Mundo, liquidada_b: Liquidada) -> UUID:
    """El documento pendiente de la otra administración. Es fixture y no lo crea un test: con
    xdist los tests de un módulo se reparten entre workers y el barrido no puede depender de que
    otro test haya corrido antes en el suyo (L-104)."""
    return documento(base_del_edificio, mundo, liquidada_b, "completa", de_b=True)


@pytest.fixture(scope="module")
def pendiente_de_a(base_del_edificio: BaseDeEdificio, mundo: Mundo, liquidada: Liquidada) -> UUID:
    """Un pendiente de la primera administración que ningún otro test crea (segunda unidad, sin
    extraordinaria): el barrido no depende del orden (L-104)."""
    otra = Liquidada(liquidada.liquidacion_id, mundo.unidades[1])
    return documento(base_del_edificio, mundo, otra, "sin_extraordinaria")


def _archivar(c: psycopg.Connection, mundo: Mundo, doc: UUID, contenido: bytes = _PDF) -> None:
    c.execute(
        "INSERT INTO pdf_de_expensa (administracion_id, complejo_id, documento_id, contenido, "
        "sha256, generado_en) VALUES (%s, %s, %s, %s, %s, now())",
        (mundo.admin, mundo.complejo, doc, contenido, hashlib.sha256(contenido).hexdigest()),
    )


def _estado(base: BaseDeEdificio, mundo: Mundo, doc: UUID) -> tuple[str, str | None]:
    with base.conectar_app() as c, c.transaction():
        fijar_tenant(c, mundo.admin)
        fila = c.execute(
            "SELECT estado, motivo FROM documento_de_expensa WHERE id = %s", (doc,)
        ).fetchone()
    assert fila is not None
    return str(fila[0]), fila[1]


def test_un_documento_nace_pendiente_y_las_dos_variantes_son_unicas(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, liquidada: Liquidada
) -> None:
    doc = documento(base_del_edificio, mundo, liquidada, "completa")
    assert _estado(base_del_edificio, mundo, doc) == ("pendiente", None)
    with pytest.raises(psycopg.errors.UniqueViolation):
        documento(base_del_edificio, mundo, liquidada, "completa")
    with pytest.raises(psycopg.errors.CheckViolation):
        documento(base_del_edificio, mundo, liquidada, "otra")


def test_pasar_a_generado_exige_el_pdf_archivado(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, liquidada: Liquidada
) -> None:
    doc = documento(base_del_edificio, mundo, liquidada, "sin_extraordinaria")
    with base_del_edificio.conectar_app() as c, pytest.raises(psycopg.errors.RaiseException):
        with c.transaction():
            fijar_tenant(c, mundo.admin)
            c.execute("UPDATE documento_de_expensa SET estado = 'generado' WHERE id = %s", (doc,))
    assert _estado(base_del_edificio, mundo, doc)[0] == "pendiente"


@pytest.fixture(scope="module")
def generado(base_del_edificio: BaseDeEdificio, mundo: Mundo, liquidada: Liquidada) -> UUID:
    """Un documento de la segunda unidad que recorre pendiente, fallido, pendiente y generado."""
    otra = Liquidada(liquidada.liquidacion_id, mundo.unidades[1])
    doc = documento(base_del_edificio, mundo, otra, "completa")
    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, mundo.admin)
        c.execute(
            "UPDATE documento_de_expensa SET estado = 'fallido', motivo = 'sin fuentes' "
            "WHERE id = %s",
            (doc,),
        )
    assert _estado(base_del_edificio, mundo, doc) == ("fallido", "sin fuentes")
    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, mundo.admin)
        c.execute(
            "UPDATE documento_de_expensa SET estado = 'pendiente', motivo = NULL WHERE id = %s",
            (doc,),
        )
        _archivar(c, mundo, doc)
        c.execute("UPDATE documento_de_expensa SET estado = 'generado' WHERE id = %s", (doc,))
    return doc


def test_un_documento_generado_ya_no_se_toca_ni_se_borra_ni_su_pdf(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, generado: UUID
) -> None:
    assert _estado(base_del_edificio, mundo, generado) == ("generado", None)
    for sentencia in (
        "UPDATE documento_de_expensa SET estado = 'pendiente' WHERE id = %s",
        "UPDATE documento_de_expensa SET estado = 'fallido', motivo = 'x' WHERE id = %s",
        "DELETE FROM documento_de_expensa WHERE id = %s",
        "UPDATE pdf_de_expensa SET contenido = '\\x01' WHERE documento_id = %s",
        "DELETE FROM pdf_de_expensa WHERE documento_id = %s",
    ):
        with (
            base_del_edificio.conectar_app() as c,
            pytest.raises((psycopg.errors.RaiseException, psycopg.errors.InsufficientPrivilege)),
        ):
            with c.transaction():
                fijar_tenant(c, mundo.admin)
                c.execute(sentencia, (generado,))
    assert _estado(base_del_edificio, mundo, generado) == ("generado", None)


def test_el_archivo_no_se_agrega_dos_veces_ni_se_trunca(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, generado: UUID
) -> None:
    with base_del_edificio.conectar_app() as c, pytest.raises(psycopg.errors.UniqueViolation):
        with c.transaction():
            fijar_tenant(c, mundo.admin)
            _archivar(c, mundo, generado, b"%PDF otra version")
    with base_del_edificio.conectar_app() as c, pytest.raises(psycopg.errors.Error):
        c.execute("TRUNCATE pdf_de_expensa")


def test_una_administracion_no_ve_los_documentos_de_otra(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, pendiente_de_b: UUID
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, mundo.admin_b)
        assert c.execute("SELECT count(*) FROM documento_de_expensa").fetchone() == (1,)
        assert c.execute("SELECT count(*) FROM pdf_de_expensa").fetchone() == (0,)
    with base_del_edificio.conectar_app() as c, c.transaction():
        assert c.execute("SELECT count(*) FROM documento_de_expensa").fetchone() == (0,)


def test_el_barrido_ve_lo_pendiente_de_todas_y_nada_mas(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, pendiente_de_a: UUID, pendiente_de_b: UUID
) -> None:
    barrido = "SELECT set_config('app.barrido_de_documentos', 'si', true)"
    with base_del_edificio.conectar_app() as c, c.transaction():
        c.execute(barrido)
        filas = c.execute("SELECT administracion_id, estado FROM documento_de_expensa").fetchall()
        assert {f[0] for f in filas} == {mundo.admin, mundo.admin_b}
        assert {f[1] for f in filas} == {"pendiente"}, "sólo lo pendiente, nunca lo generado"
        assert c.execute("SELECT count(*) FROM pdf_de_expensa").fetchone() == (0,), (
            "los bytes no se ven sin tenant"
        )
        assert c.execute("SELECT count(*) FROM liquidacion").fetchone() == (0,)
    with base_del_edificio.conectar_app() as c, c.transaction():
        c.execute("SELECT set_config('app.barrido_de_documentos', 'no', true)")
        assert c.execute("SELECT count(*) FROM documento_de_expensa").fetchone() == (0,)


def test_con_tenant_la_marca_del_barrido_no_abre_otra_administracion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with base_del_edificio.conectar_app() as c, c.transaction():
        c.execute("SELECT set_config('app.barrido_de_documentos', 'si', true)")
        fijar_tenant(c, mundo.admin_b)
        filas = c.execute("SELECT DISTINCT administracion_id FROM documento_de_expensa").fetchall()
        assert filas == [(mundo.admin_b,)]


def test_el_barrido_no_escribe(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with base_del_edificio.conectar_app() as c:
        c.execute("BEGIN")
        c.execute("SELECT set_config('app.barrido_de_documentos', 'si', true)")
        c.execute(
            "UPDATE documento_de_expensa SET estado = 'fallido', motivo = 'x' "
            "WHERE estado = 'pendiente'"
        )
        assert c.execute("SELECT count(*) FROM documento_de_expensa").fetchone() is not None
        c.execute("ROLLBACK")
    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, mundo.admin)
        assert c.execute(
            "SELECT count(*) FROM documento_de_expensa WHERE estado = 'fallido'"
        ).fetchone() == (0,)
