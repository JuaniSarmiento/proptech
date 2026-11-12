"""Tarea 1.5 de `importacion-desde-excel`: el caso de uso `importar` (H-007, padrón) contra
PostgreSQL real. Sin la ruta (es de la tanda 3): se llama el caso de uso con la sesión como
`proptech_app`, con el tenant fijado, igual que la API.

Lo que se prueba: permiso y alcance (D7), candado del complejo (E8), estado de migración, una sola
lectura del padrón (D1), huella (E7), unidades y propietarios sin invitar (E3), auditoría, y que
cualquier rechazo no deja nada escrito. Datos inventados.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.complejos.aplicacion.errores import Conflicto, EntradaInvalida, NoEncontrado
from proptech_core.importacion.adaptadores.excel import LectorDePlantillaExcel
from proptech_core.importacion.aplicacion.errores import ArchivoYaImportado, SinPermiso
from proptech_core.importacion.aplicacion.importar import ResultadoDeImportacion, importar
from proptech_core.importacion.dominio.padron import PadronInvalido
from proptech_core.importacion.dominio.plantilla import ArchivoInvalido

from ._edificios import BaseDeEdificio, fijar_tenant
from ._importacion import (
    MIGRACION,
    RELOJ,
    Mundo,
    con_tenant,
    conteos,
    filas_validas,
    libro,
    padron,
    sembrar,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


@pytest.fixture
def sesion(mundo: Mundo, sesion_edificio: Session) -> Session:
    con_tenant(sesion_edificio, mundo.admin)
    return sesion_edificio


def _importar(
    sesion: Session,
    identidad: Identidad,
    complejo: UUID,
    contenido: bytes,
    *,
    fecha: date = MIGRACION,
    nombre: str | None = "padron-torre-ficticia.xlsx",
) -> ResultadoDeImportacion:
    return importar(
        sesion,
        identidad,
        complejo_id=complejo,
        contenido=contenido,
        nombre_del_archivo=nombre,
        fecha_de_migracion=fecha,
        lector=LectorDePlantillaExcel(),
        reloj=RELOJ,
        request_id=uuid4(),
    )


def _uno(sesion: Session, consulta: str, **parametros: Any) -> Any:
    return sesion.execute(text(consulta), parametros).scalar_one()


# --- El camino feliz --------------------------------------------------------------------------


def test_doce_unidades_con_propietarios_sin_invitar(mundo: Mundo, sesion: Session) -> None:
    antes = conteos(sesion)
    resultado = _importar(sesion, mundo.super_admin, mundo.torre, padron())
    despues = conteos(sesion)
    assert resultado.unidades_creadas == 12
    assert resultado.propietarios_creados == 10
    assert resultado.propietarios_reusados == 0
    assert resultado.filas_de_saldo == 0
    assert resultado.advertencias == ()
    assert despues["unidad"] - antes["unidad"] == 12
    assert despues["persona"] - antes["persona"] == 10
    assert despues["asignacion_vecino"] - antes["asignacion_vecino"] == 10
    assert despues["invitacion"] == antes["invitacion"], "importar no invita (E3)"
    assert despues["importacion"] - antes["importacion"] == 1
    fila = sesion.execute(
        text(
            "SELECT p.nombre, p.email, a.vinculo FROM asignacion_rol a "
            "JOIN unidad u ON u.id = a.unidad_id JOIN persona p ON p.id = a.persona_id "
            "WHERE u.complejo_id = :c AND u.identificador = '2B'"
        ),
        {"c": mundo.torre},
    ).one()
    assert tuple(fila) == ("Persona Ficticia 3", "propietario3@ficticio.test", "propietario")


def test_la_importacion_queda_con_su_huella_y_su_fecha(mundo: Mundo, sesion: Session) -> None:
    contenido = padron()
    resultado = _importar(sesion, mundo.super_admin, mundo.torre, contenido)
    fila = sesion.execute(
        text(
            "SELECT complejo_id, huella, fecha_de_migracion, estado, archivo, creada_por "
            "FROM importacion WHERE id = :id"
        ),
        {"id": resultado.importacion_id},
    ).one()
    assert tuple(fila) == (
        mundo.torre,
        hashlib.sha256(contenido).hexdigest(),
        MIGRACION,
        "borrador",
        "padron-torre-ficticia.xlsx",
        mundo.super_admin.persona_id,
    )


def test_audita_una_vez_por_unidad_y_una_la_importacion(mundo: Mundo, sesion: Session) -> None:
    resultado = _importar(sesion, mundo.super_admin, mundo.torre, padron())
    assert _uno(sesion, "SELECT count(*) FROM auditoria WHERE accion = 'crear_unidad'") == 12
    filas = sesion.execute(
        text(
            "SELECT entidad, entidad_id, persona_id, detalle FROM auditoria "
            "WHERE accion = 'importar_padron_y_saldos'"
        )
    ).all()
    assert len(filas) == 1
    entidad, entidad_id, persona_id, detalle = filas[0]
    assert (entidad, entidad_id, persona_id) == (
        "importacion",
        resultado.importacion_id,
        mundo.super_admin.persona_id,
    )
    assert detalle == {
        "complejo_id": str(mundo.torre),
        "unidades": 12,
        "propietarios_creados": 10,
        "propietarios_reusados": 0,
    }


def test_las_unidades_quedan_como_el_archivo(mundo: Mundo, sesion: Session) -> None:
    _importar(sesion, mundo.super_admin, mundo.torre, padron())
    filas = sesion.execute(
        text(
            "SELECT identificador, tipo, piso, coeficiente::text, superficie_m2::text "
            "FROM unidad WHERE complejo_id = :c ORDER BY identificador"
        ),
        {"c": mundo.torre},
    ).all()
    esperadas = sorted(
        (f["Unidad"], f["Tipo"], f["Piso"], f["Coeficiente"], f["Superficie m2"])
        for f in filas_validas()
    )
    assert [tuple(f) for f in filas] == esperadas


# --- Propietarios ----------------------------------------------------------------------------


def test_un_email_ya_existente_reusa_la_persona(mundo: Mundo, sesion: Session) -> None:
    sesion.execute(
        text(
            "INSERT INTO persona (administracion_id, nombre, email) "
            "VALUES (:a, 'Persona Ficticia Existente', 'existente@ficticio.test')"
        ),
        {"a": mundo.admin},
    )
    filas = filas_validas()
    filas[0]["Email"] = "existente@ficticio.test"
    antes = conteos(sesion)
    resultado = _importar(sesion, mundo.super_admin, mundo.torre, padron(filas))
    assert (resultado.propietarios_creados, resultado.propietarios_reusados) == (9, 1)
    assert conteos(sesion)["persona"] - antes["persona"] == 9
    nombre = _uno(sesion, "SELECT nombre FROM persona WHERE email = 'existente@ficticio.test'")
    assert nombre == "Persona Ficticia Existente", "no se renombra a quien ya existía"


def test_el_mismo_email_en_dos_filas_es_una_persona_y_no_cuenta_como_reusada(
    mundo: Mundo, sesion: Session
) -> None:
    filas = filas_validas()
    filas[1]["Email"], filas[1]["Propietario"] = filas[0]["Email"], filas[0]["Propietario"]
    antes = conteos(sesion)
    resultado = _importar(sesion, mundo.super_admin, mundo.torre, padron(filas))
    assert (resultado.propietarios_creados, resultado.propietarios_reusados) == (9, 0)
    assert conteos(sesion)["persona"] - antes["persona"] == 9
    assert conteos(sesion)["asignacion_vecino"] - antes["asignacion_vecino"] == 10


def test_el_mismo_email_con_otro_nombre_conserva_el_primero_y_advierte(
    mundo: Mundo, sesion: Session
) -> None:
    filas = filas_validas()
    filas[1]["Email"], filas[1]["Propietario"] = filas[0]["Email"], "P. Ficticia 1"
    resultado = _importar(sesion, mundo.super_admin, mundo.torre, padron(filas))
    assert (
        _uno(
            sesion,
            "SELECT nombre FROM persona WHERE email = :e",
            e=filas[0]["Email"],
        )
        == "Persona Ficticia 1"
    )
    assert [(a.hoja, a.fila, a.columna) for a in resultado.advertencias] == [
        ("Unidades", 3, "Propietario")
    ]


def test_un_propietario_sin_email_es_una_persona_sin_email(mundo: Mundo, sesion: Session) -> None:
    filas = filas_validas()
    filas[0]["Email"] = None
    _importar(sesion, mundo.super_admin, mundo.torre, padron(filas))
    fila = sesion.execute(
        text(
            "SELECT p.nombre, p.email FROM asignacion_rol a JOIN unidad u ON u.id = a.unidad_id "
            "JOIN persona p ON p.id = a.persona_id WHERE u.identificador = '1A' "
            "AND u.complejo_id = :c"
        ),
        {"c": mundo.torre},
    ).one()
    assert tuple(fila) == ("Persona Ficticia 1", None)


def test_la_suma_dentro_de_la_tolerancia_carga_con_advertencia(
    mundo: Mundo, sesion: Session
) -> None:
    filas = filas_validas()
    filas[11]["Coeficiente"] = "0.083237"  # suma 0,9999
    resultado = _importar(sesion, mundo.super_admin, mundo.torre, padron(filas))
    assert resultado.unidades_creadas == 12
    assert len(resultado.advertencias) == 1
    assert "0,9999" in resultado.advertencias[0].motivo


# --- Rechazos: nada se escribe ----------------------------------------------------------------


def _no_escribe(sesion: Session, error: type[Exception], llamada: Any) -> Exception:
    antes = conteos(sesion)
    with pytest.raises(error) as capturado:
        llamada()
    assert conteos(sesion) == antes, "un rechazo no escribe nada"
    return capturado.value


def test_una_fila_mala_no_carga_nada_y_el_informe_trae_todos_los_errores(
    mundo: Mundo, sesion: Session
) -> None:
    filas = filas_validas()
    filas[7]["Piso"] = "Entrepiso"  # fila 9
    filas[1]["Tipo"] = None  # fila 3
    error = _no_escribe(
        sesion,
        PadronInvalido,
        lambda: _importar(sesion, mundo.super_admin, mundo.torre, padron(filas)),
    )
    assert isinstance(error, PadronInvalido)
    assert [(e.fila, e.columna) for e in error.errores] == [(3, "Tipo"), (9, "Piso")]


def test_un_archivo_que_no_es_excel_no_carga_nada(mundo: Mundo, sesion: Session) -> None:
    _no_escribe(
        sesion,
        ArchivoInvalido,
        lambda: _importar(
            sesion,
            mundo.super_admin,
            mundo.torre,
            b"Unidad,Tipo\n1A,departamento\n",
            nombre="a.csv",
        ),
    )


def test_el_edificio_sin_pisos_se_rechaza_nombrando_el_piso(mundo: Mundo, sesion: Session) -> None:
    error = _no_escribe(
        sesion,
        PadronInvalido,
        lambda: _importar(sesion, mundo.super_admin, mundo.sin_pisos, padron()),
    )
    assert isinstance(error, PadronInvalido)
    assert any(e.columna == "Piso" and e.fila is None for e in error.errores)


@pytest.mark.parametrize("dias", [1, 30])
def test_la_fecha_de_migracion_futura_se_rechaza(mundo: Mundo, sesion: Session, dias: int) -> None:
    hoy = RELOJ().date()
    error = _no_escribe(
        sesion,
        EntradaInvalida,
        lambda: _importar(
            sesion, mundo.super_admin, mundo.torre, padron(), fecha=hoy + timedelta(days=dias)
        ),
    )
    assert isinstance(error, EntradaInvalida)
    assert error.campo == "fecha_de_migracion"


def test_la_fecha_de_migracion_de_hoy_se_acepta(mundo: Mundo, sesion: Session) -> None:
    resultado = _importar(sesion, mundo.super_admin, mundo.torre, padron(), fecha=RELOJ().date())
    assert resultado.unidades_creadas == 12


# --- Estado de migración y huella -------------------------------------------------------------


@pytest.mark.parametrize("estado", ["confirmada", "sin_saldos_previos"])
def test_con_la_migracion_cerrada_no_se_importa(mundo: Mundo, sesion: Session, estado: str) -> None:
    sesion.execute(
        text("UPDATE complejo SET estado_migracion = :e WHERE id = :c"),
        {"e": estado, "c": mundo.torre},
    )
    error = _no_escribe(
        sesion,
        Conflicto,
        lambda: _importar(sesion, mundo.super_admin, mundo.torre, padron()),
    )
    assert isinstance(error, Conflicto)
    assert error.campo == "estado_migracion"


def test_el_mismo_archivo_dos_veces_es_conflicto_y_nombra_la_anterior(
    mundo: Mundo, sesion: Session
) -> None:
    contenido = padron()
    primera = _importar(sesion, mundo.super_admin, mundo.torre, contenido)
    error = _no_escribe(
        sesion,
        ArchivoYaImportado,
        lambda: _importar(
            sesion, mundo.super_admin, mundo.torre, contenido, nombre="otro-nombre.xlsx"
        ),
    )
    assert isinstance(error, ArchivoYaImportado)
    assert (error.campo, error.importacion_id) == ("archivo", primera.importacion_id)


def test_el_mismo_archivo_en_otro_edificio_no_es_conflicto(mundo: Mundo, sesion: Session) -> None:
    contenido = padron()
    _importar(sesion, mundo.super_admin, mundo.torre, contenido)
    resultado = _importar(sesion, mundo.super_admin, mundo.otro, contenido)
    assert resultado.unidades_creadas == 12


def test_un_archivo_descartado_se_puede_volver_a_subir(mundo: Mundo, sesion: Session) -> None:
    contenido = padron()
    primera = _importar(sesion, mundo.super_admin, mundo.torre, contenido)
    sesion.execute(
        text("UPDATE importacion SET estado = 'descartada' WHERE id = :id"),
        {"id": primera.importacion_id},
    )
    # El padrón ya existe: el mismo archivo trae filas en `Unidades` y se rechaza por E7, no por la
    # huella (el conflicto de archivo no corresponde a una importación descartada).
    with pytest.raises(PadronInvalido):
        _importar(sesion, mundo.super_admin, mundo.torre, contenido)


# --- Padrón existente (E7) --------------------------------------------------------------------


@pytest.mark.parametrize("forma", ["sin_hoja", "hoja_vacia"])
def test_un_edificio_con_padron_acepta_un_archivo_sin_filas_de_unidades(
    mundo: Mundo, sesion: Session, forma: str
) -> None:
    contenido = libro({"Notas": [["Texto"], ["x"]]}) if forma == "sin_hoja" else padron([])
    antes = conteos(sesion)
    resultado = _importar(sesion, mundo.super_admin, mundo.con_padron, contenido)
    despues = conteos(sesion)
    assert resultado.unidades_creadas == 0
    assert despues["unidad"] == antes["unidad"]
    assert despues["importacion"] - antes["importacion"] == 1


def test_un_edificio_con_padron_rechaza_filas_de_unidades(mundo: Mundo, sesion: Session) -> None:
    error = _no_escribe(
        sesion,
        PadronInvalido,
        lambda: _importar(sesion, mundo.super_admin, mundo.con_padron, padron()),
    )
    assert isinstance(error, PadronInvalido)
    assert {e.fila for e in error.errores} == set(range(2, 14))


def test_otro_archivo_reemplaza_el_borrador_anterior(mundo: Mundo, sesion: Session) -> None:
    primera = _importar(sesion, mundo.super_admin, mundo.con_padron, libro({"Notas": [["a"]]}))
    segunda = _importar(sesion, mundo.super_admin, mundo.con_padron, libro({"Notas": [["b"]]}))
    estados = dict(
        sesion.execute(
            text("SELECT id, estado FROM importacion WHERE complejo_id = :c"),
            {"c": mundo.con_padron},
        ).all()
    )
    assert estados == {primera.importacion_id: "descartada", segunda.importacion_id: "borrador"}


# --- Permiso y alcance (D7) -------------------------------------------------------------------


@pytest.mark.parametrize("quien", ["super_admin", "principal", "de_la_torre"])
def test_pueden_importar(mundo: Mundo, sesion: Session, quien: str) -> None:
    resultado = _importar(sesion, getattr(mundo, quien), mundo.torre, padron())
    assert resultado.unidades_creadas == 12


@pytest.mark.parametrize("quien", ["contador", "auxiliar"])
def test_sin_el_permiso_da_sin_permiso_y_no_escribe(
    mundo: Mundo, sesion: Session, quien: str
) -> None:
    error = _no_escribe(
        sesion,
        SinPermiso,
        lambda: _importar(sesion, getattr(mundo, quien), mundo.torre, padron()),
    )
    assert isinstance(error, SinPermiso)
    assert error.permiso_faltante == "importar_padron_y_saldos"


def test_el_administrador_de_otro_edificio_no_encuentra_este(mundo: Mundo, sesion: Session) -> None:
    _no_escribe(
        sesion,
        NoEncontrado,
        lambda: _importar(sesion, mundo.de_otro, mundo.torre, padron()),
    )


def test_un_edificio_inexistente_o_de_otra_administracion_no_existe(
    mundo: Mundo, sesion: Session
) -> None:
    for complejo in (uuid4(), mundo.complejo_b):
        _no_escribe(
            sesion,
            NoEncontrado,
            lambda c=complejo: _importar(sesion, mundo.super_admin, c, padron()),  # type: ignore[misc]
        )


def test_el_permiso_se_chequea_antes_que_el_archivo(mundo: Mundo, sesion: Session) -> None:
    """Un archivo roto de alguien sin permiso es 403, no 422 (D7)."""
    _no_escribe(
        sesion,
        SinPermiso,
        lambda: _importar(sesion, mundo.contador, mundo.torre, b"no es un excel"),
    )


# --- El candado del complejo (E8) y una sola lectura del padrón (D1) --------------------------


def test_importar_toma_el_candado_del_complejo(mundo: Mundo, sesion: Session) -> None:
    _importar(sesion, mundo.super_admin, mundo.torre, padron())
    with mundo.conectar() as otra:
        with pytest.raises(psycopg.errors.LockNotAvailable):
            otra.execute("SELECT id FROM complejo WHERE id = %s FOR UPDATE NOWAIT", (mundo.torre,))
        otra.rollback()


@contextmanager
def _sentencias(sesion: Session) -> Iterator[list[str]]:
    vistas: list[str] = []

    def registrar(_c: Any, _cur: Any, sentencia: str, *_: Any) -> None:
        vistas.append(sentencia)

    motor = sesion.get_bind()
    event.listen(motor, "before_cursor_execute", registrar)
    try:
        yield vistas
    finally:
        event.remove(motor, "before_cursor_execute", registrar)


def test_el_padron_se_lee_una_sola_vez(mundo: Mundo, sesion: Session) -> None:
    with _sentencias(sesion) as vistas:
        _importar(sesion, mundo.super_admin, mundo.torre, padron())
    lecturas = [s for s in vistas if "FROM unidad" in s and s.lstrip().upper().startswith("SELECT")]
    assert len(lecturas) == 1, f"el padrón se leyó {len(lecturas)} veces: {lecturas}"


def test_dos_importaciones_simultaneas_del_mismo_archivo_una_gana(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    """E8: el candado serializa las subidas; la segunda ve la importación de la primera y da
    conflicto de archivo, nunca 24 unidades."""
    import threading

    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    def conectar() -> psycopg.Connection:
        conexion = base_del_edificio.conectar_app()
        conexion.autocommit = False
        return conexion

    contenido = padron()
    barrera = threading.Barrier(2)
    resultados: list[Any] = [None, None]

    def correr(i: int) -> None:
        motor = create_engine("postgresql+psycopg://", creator=conectar, poolclass=NullPool)
        try:
            with Session(motor) as s:
                con_tenant(s, mundo.admin)
                barrera.wait()
                try:
                    resultados[i] = _importar(s, mundo.super_admin, mundo.torre, contenido)
                    s.commit()
                except Exception as error:
                    s.rollback()
                    resultados[i] = error
        finally:
            motor.dispose()

    hilos = [threading.Thread(target=correr, args=(i,)) for i in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
    ganadoras = [r for r in resultados if isinstance(r, ResultadoDeImportacion)]
    perdedoras = [r for r in resultados if isinstance(r, ArchivoYaImportado)]
    assert (len(ganadoras), len(perdedoras)) == (1, 1), resultados
    with mundo.conectar() as c:
        assert c.execute(
            "SELECT count(*) FROM unidad WHERE complejo_id = %s", (mundo.torre,)
        ).fetchone() == (12,)
        c.rollback()


def test_el_aislamiento_por_administracion_de_la_tabla(mundo: Mundo, sesion: Session) -> None:
    resultado = _importar(sesion, mundo.super_admin, mundo.torre, padron())
    sesion.commit()
    with mundo.conectar(mundo.admin_b) as c:
        fijar_tenant(c, mundo.admin_b)
        assert c.execute(
            "SELECT count(*) FROM importacion WHERE id = %s", (resultado.importacion_id,)
        ).fetchone() == (0,)
        c.rollback()
