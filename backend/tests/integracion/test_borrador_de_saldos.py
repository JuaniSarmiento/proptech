"""Tarea 2.3 de `importacion-desde-excel` (parte del borrador): la subida con `Saldos` y `Control`
guarda un borrador que no toca el libro, y un borrador nuevo descarta al anterior (design D5, E7).
Contra PostgreSQL real, llamando al caso de uso `importar` con la sesión como `proptech_app` (la
ruta ya existe y el aceptado de H-008 la recorre). Datos inventados."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.importacion.aplicacion.errores import ArchivoYaImportado
from proptech_core.importacion.dominio.padron import PadronInvalido

from ._edificios import BaseDeEdificio
from ._importacion import Mundo, con_tenant, filas_validas, padron, sembrar
from ._saldos_importados import (
    archivo,
    conteos_del_borrador,
    control_base,
    controles_del_borrador,
    estado_de,
    filas_del_borrador,
    saldos_base,
    subir,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


@pytest.fixture
def sesion(mundo: Mundo, sesion_edificio: Session) -> Session:
    con_tenant(sesion_edificio, mundo.admin)
    return sesion_edificio


def _detalle(
    unidad: str, fila: int, mes: int, concepto: str, importe: str, interes: str
) -> tuple[Any, ...]:
    """Una fila de detalle del 2026: período el día 1 del `mes`, vencimiento el día 10."""
    vence = date(2026, mes, 10)
    return (unidad, fila, "detalle", date(2026, mes, 1), vence, concepto, importe, interes)


def _rechazo(sesion: Session, mundo: Mundo, contenido: bytes, complejo: Any = None) -> Any:
    antes = conteos_del_borrador(sesion)
    with pytest.raises(PadronInvalido) as capturado:
        subir(sesion, mundo.super_admin, complejo or mundo.torre, contenido)
    assert conteos_del_borrador(sesion) == antes, "un rechazo no escribe nada"
    return capturado.value


# --- El borrador de una subida con el padrón --------------------------------------------------


def test_la_subida_guarda_las_filas_de_saldo_y_el_control(mundo: Mundo, sesion: Session) -> None:
    resultado = subir(sesion, mundo.super_admin, mundo.torre, archivo())
    assert resultado.unidades_creadas == 12
    assert resultado.filas_de_saldo == 7
    assert filas_del_borrador(sesion, resultado.importacion_id) == [
        _detalle("1A", 2, 8, "ordinaria", "80000.00", "4000.00"),
        _detalle("1A", 3, 9, "ordinaria", "85000.00", "0.00"),
        _detalle("1B", 4, 9, "ordinaria", "85000.00", "0.00"),
        _detalle("1B", 5, 9, "extraordinaria", "20000.00", "0.00"),
        ("2A", 6, "total", None, None, None, "50000.00", "2000.00"),
        ("2B", 7, "credito", None, None, None, "3000.00", "0.00"),
        ("C1", 8, "credito", None, None, None, "3000.00", "0.00"),
    ]
    assert controles_del_borrador(sesion, resultado.importacion_id) == [
        ("1A", 2, "169000.00"),
        ("1B", 3, "105000.00"),
        ("2A", 4, "52000.00"),
        ("2B", 5, "-3000.00"),
        ("C1", 6, "-3000.00"),
    ]
    assert estado_de(sesion, resultado.importacion_id) == "borrador"


def test_el_borrador_no_toca_el_libro(mundo: Mundo, sesion: Session) -> None:
    antes = conteos_del_borrador(sesion)
    assert (antes["cuenta"], antes["obligacion"], antes["movimiento"]) == (0, 0, 0)
    subir(sesion, mundo.super_admin, mundo.torre, archivo())
    despues = conteos_del_borrador(sesion)
    assert (despues["cuenta"], despues["obligacion"], despues["movimiento"]) == (0, 0, 0), (
        "el borrador creó cuentas, obligaciones o movimientos"
    )
    assert sesion.execute(text("SELECT count(*) FROM carga_de_saldo_inicial")).scalar_one() == 0


def test_la_auditoria_de_importar_sigue_siendo_una_sola(mundo: Mundo, sesion: Session) -> None:
    subir(sesion, mundo.super_admin, mundo.torre, archivo())
    assert (
        sesion.execute(
            text("SELECT count(*) FROM auditoria WHERE accion = 'importar_padron_y_saldos'")
        ).scalar_one()
        == 1
    )


def test_un_archivo_sin_saldos_no_deja_borrador(mundo: Mundo, sesion: Session) -> None:
    resultado = subir(sesion, mundo.super_admin, mundo.torre, padron())
    assert resultado.filas_de_saldo == 0
    antes = conteos_del_borrador(sesion)
    assert (antes["fila_de_saldo_importada"], antes["control_de_saldo"]) == (0, 0)


def test_las_hojas_de_la_plantilla_descargada_sin_filas_no_son_un_borrador(
    mundo: Mundo, sesion: Session
) -> None:
    resultado = subir(sesion, mundo.super_admin, mundo.torre, archivo(saldos=[], control=[]))
    assert resultado.filas_de_saldo == 0
    assert conteos_del_borrador(sesion)["control_de_saldo"] == 0
    assert estado_de(sesion, resultado.importacion_id) == "borrador"


# --- Sobre el padrón que ya existe (E7) ---------------------------------------------------------


def _sobre_el_padron_existente(unidad: str = "9Z") -> bytes:
    return archivo(
        saldos=[[unidad, None, None, None, "1000.00", None]],
        control=[[unidad, "1000.00"]],
        con_unidades=False,
    )


def test_con_el_padron_ya_creado_se_importan_solo_saldos_y_control(
    mundo: Mundo, sesion: Session
) -> None:
    antes = conteos_del_borrador(sesion)
    resultado = subir(sesion, mundo.super_admin, mundo.con_padron, _sobre_el_padron_existente())
    assert resultado.unidades_creadas == 0 and resultado.filas_de_saldo == 1
    assert conteos_del_borrador(sesion)["unidad"] == antes["unidad"], "el padrón no cambia"
    assert filas_del_borrador(sesion, resultado.importacion_id) == [
        ("9Z", 2, "total", None, None, None, "1000.00", "0.00")
    ]


def test_un_borrador_nuevo_descarta_al_anterior(mundo: Mundo, sesion: Session) -> None:
    primero = subir(sesion, mundo.super_admin, mundo.con_padron, _sobre_el_padron_existente())
    segundo = subir(
        sesion,
        mundo.super_admin,
        mundo.con_padron,
        archivo(
            saldos=[["9Z", None, None, None, "2000.00", None]],
            control=[["9Z", "2000.00"]],
            con_unidades=False,
        ),
        nombre="saldos-corregidos.xlsx",
    )
    assert estado_de(sesion, primero.importacion_id) == "descartada"
    assert estado_de(sesion, segundo.importacion_id) == "borrador"
    assert (
        sesion.execute(
            text("SELECT count(*) FROM importacion WHERE complejo_id = :c AND estado = 'borrador'"),
            {"c": mundo.con_padron},
        ).scalar_one()
        == 1
    )
    assert [f[6] for f in filas_del_borrador(sesion, segundo.importacion_id)] == ["2000.00"]


def test_el_mismo_archivo_de_saldos_dos_veces_es_conflicto(mundo: Mundo, sesion: Session) -> None:
    primero = subir(sesion, mundo.super_admin, mundo.con_padron, _sobre_el_padron_existente())
    antes = conteos_del_borrador(sesion)
    with pytest.raises(ArchivoYaImportado) as capturado:
        subir(sesion, mundo.super_admin, mundo.con_padron, _sobre_el_padron_existente())
    assert capturado.value.importacion_id == primero.importacion_id
    assert conteos_del_borrador(sesion) == antes


# --- Un rechazo no escribe nada ---------------------------------------------------------------


def test_una_fila_de_saldos_mala_rechaza_todo_incluido_el_padron(
    mundo: Mundo, sesion: Session
) -> None:
    saldos = saldos_base()
    saldos[0][0] = "9Z"  # fila 2: unidad que no existe (en la torre; `_rechazo` mira que no se cree
    # ni una unidad del padrón ni nada de lo demás)
    error = _rechazo(sesion, mundo, archivo(saldos))
    assert [(e.hoja, e.fila, e.columna) for e in error.errores] == [("Saldos", 2, "Unidad")]


def test_los_errores_del_padron_y_de_saldos_van_juntos(mundo: Mundo, sesion: Session) -> None:
    unidades = filas_validas()
    unidades[1]["Tipo"] = None  # fila 3 de Unidades
    saldos = saldos_base()
    saldos[1][3] = "Expensa"  # fila 3 de Saldos
    control = [*control_base(), ["9Z", "10.00"]]  # fila 7 de Control
    error = _rechazo(sesion, mundo, archivo(saldos, control, unidades=unidades))
    assert [(e.hoja, e.fila, e.columna) for e in error.errores] == [
        ("Unidades", 3, "Tipo"),
        ("Saldos", 3, "Concepto"),
        ("Control", 7, "Unidad"),
    ]


def test_las_unidades_del_padron_con_error_igual_sirven_para_ubicar_los_saldos(
    mundo: Mundo, sesion: Session
) -> None:
    """Un error de la fila de `Unidades` no vuelve "inexistentes" a las unidades de `Saldos`."""
    unidades = filas_validas()
    unidades[0]["Superficie m2"] = "0"  # fila 2: 1A mal cargada
    error = _rechazo(sesion, mundo, archivo(unidades=unidades))
    assert [(e.hoja, e.fila, e.columna) for e in error.errores] == [
        ("Unidades", 2, "Superficie m2")
    ]


def test_saldos_sin_la_hoja_control_es_error_de_archivo(mundo: Mundo, sesion: Session) -> None:
    error = _rechazo(sesion, mundo, archivo(sin_control=True))
    assert [(e.hoja, e.fila) for e in error.errores] == [("Control", None)]


def test_la_fecha_de_migracion_decide_que_vencimientos_valen(mundo: Mundo, sesion: Session) -> None:
    """Con la migración el 05/09/2026, los vencimientos del 10/09 son posteriores."""
    antes = conteos_del_borrador(sesion)
    with pytest.raises(PadronInvalido) as capturado:
        subir(sesion, mundo.super_admin, mundo.torre, archivo(), fecha=date(2026, 9, 5))
    assert {(e.hoja, e.fila, e.columna) for e in capturado.value.errores} == {
        ("Saldos", 3, "Vencimiento"),
        ("Saldos", 4, "Vencimiento"),
        ("Saldos", 5, "Vencimiento"),
    }
    assert conteos_del_borrador(sesion) == antes
