"""Ayudas de los tests de las tareas 2.3 y 2.4 de `importacion-desde-excel`: archivos con las tres
hojas (`Unidades`, `Saldos`, `Control`) para el edificio sin padrón, o sólo `Saldos` y `Control`
para el que ya lo tiene, y lo que importar, comparar y aceptar podrían escribir.

Base de los ejemplos (la de H-008): `1A` tiene dos períodos con $4.000 de interés ($169.000),
`1B` dos conceptos del mismo período ($105.000), `2A` un total único con $2.000 de interés
($52.000), `2B` y `C1` un crédito de $3.000 cada una. Todo con datos inventados.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.importacion.adaptadores.excel import LectorDePlantillaExcel
from proptech_core.importacion.aplicacion.importar import ResultadoDeImportacion, importar
from proptech_core.importacion.dominio.plantilla import ENCABEZADOS_POR_HOJA

from ._importacion import (
    ENCABEZADOS,
    MIGRACION,
    RELOJ,
    Mundo,
    filas_validas,
    libro,
)

SALDOS = list(ENCABEZADOS_POR_HOJA["Saldos"])
CONTROL = list(ENCABEZADOS_POR_HOJA["Control"])
AVISO = "El primer interés del sistema cubre octubre de 2026"


def saldos_base() -> list[list[Any]]:
    """Filas de `Saldos` (sin encabezado); la fila del Excel es el índice + 2."""
    return [
        ["1A", "2026-08", date(2026, 8, 10), "Ordinaria", "80000.00", "4000.00"],
        ["1A", "2026-09", date(2026, 9, 10), "Ordinaria", "85000.00", None],
        ["1B", "2026-09", date(2026, 9, 10), "Ordinaria", "85000.00", None],
        ["1B", "2026-09", date(2026, 9, 10), "Extraordinaria", "20000.00", None],
        ["2A", None, None, None, "50000.00", "2000.00"],
        ["2B", None, None, None, "-3000.00", None],
        ["C1", None, None, None, "-3000.00", None],
    ]


def control_base() -> list[list[Any]]:
    return [
        ["1A", "169000.00"],
        ["1B", "105000.00"],
        ["2A", "52000.00"],
        ["2B", "-3000.00"],
        ["C1", "-3000.00"],
    ]


def archivo(
    saldos: list[list[Any]] | None = None,
    control: list[list[Any]] | None = None,
    *,
    con_unidades: bool = True,
    sin_control: bool = False,
    unidades: list[dict[str, Any]] | None = None,
) -> bytes:
    """Un archivo con `Unidades` (las 12 del padrón de prueba) si `con_unidades`, y `Saldos` y
    `Control`."""
    hojas: dict[str, list[list[Any]]] = {}
    if con_unidades:
        filas = filas_validas() if unidades is None else unidades
        hojas["Unidades"] = [ENCABEZADOS, *[[f.get(c) for c in ENCABEZADOS] for f in filas]]
    hojas["Saldos"] = [SALDOS, *(saldos_base() if saldos is None else saldos)]
    if not sin_control:
        hojas["Control"] = [CONTROL, *(control_base() if control is None else control)]
    return libro(hojas)


def con_diferencias() -> bytes:
    """`1A` con $10.000 más que su control y `2A` con $10.000 menos: los totales coinciden."""
    control = control_base()
    control[0][1] = "159000.00"
    control[2][1] = "62000.00"
    return archivo(control=control)


def subir(
    sesion: Session,
    identidad: Identidad,
    complejo: UUID,
    contenido: bytes,
    *,
    fecha: date = MIGRACION,
    nombre: str = "saldos-octubre.xlsx",
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


def unidad_de_la_torre(sesion: Session, mundo: Mundo, identificador: str) -> UUID:
    return UUID(
        str(
            sesion.execute(
                text("SELECT id FROM unidad WHERE complejo_id = :c AND identificador = :i"),
                {"c": mundo.torre, "i": identificador},
            ).scalar_one()
        )
    )


def configurar(sesion: Session, mundo: Mundo, complejo: UUID, forma: str, desde: date) -> None:
    """Una versión de configuración del edificio con esa forma de cálculo."""
    sesion.execute(
        text(
            "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, "
            "vigente_desde, tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, "
            "porcentaje_fondo, dia_de_vencimiento, modalidad_de_vencimiento) "
            "VALUES (:a, :c, :p, :d, '3.00', '500.00', 0, :f, '0.00', 10, 'unico')"
        ),
        {
            "a": mundo.admin,
            "c": complejo,
            "p": mundo.super_admin.persona_id,
            "d": desde,
            "f": forma,
        },
    )


def conteos_del_borrador(sesion: Session) -> dict[str, int]:
    """Todo lo que importar o aceptar podrían escribir, de la administración de la sesión."""
    tablas = (
        "unidad",
        "importacion",
        "fila_de_saldo_importada",
        "control_de_saldo",
        "aceptacion_de_diferencias",
        "auditoria",
        "cuenta",
        "obligacion",
        "movimiento",
    )
    resultado = {}
    for tabla in tablas:
        hay = sesion.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": tabla}).scalar_one()
        resultado[tabla] = (
            int(sesion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one())  # noqa: S608
            if hay
            else 0
        )
    return resultado


def filas_del_borrador(sesion: Session, importacion_id: UUID) -> list[tuple[Any, ...]]:
    """(unidad, fila, tipo, período, vencimiento, concepto, importe, interés) de cada fila."""
    return sorted(
        tuple(f)
        for f in sesion.execute(
            text(
                "SELECT u.identificador, f.fila, f.tipo, f.periodo, f.vencimiento, f.concepto, "
                "f.importe::text, f.interes_acumulado::text FROM fila_de_saldo_importada f "
                "JOIN unidad u ON u.id = f.unidad_id WHERE f.importacion_id = :i"
            ),
            {"i": importacion_id},
        )
    )


def controles_del_borrador(sesion: Session, importacion_id: UUID) -> list[tuple[Any, ...]]:
    return sorted(
        tuple(f)
        for f in sesion.execute(
            text(
                "SELECT u.identificador, c.fila, c.saldo::text FROM control_de_saldo c "
                "JOIN unidad u ON u.id = c.unidad_id WHERE c.importacion_id = :i"
            ),
            {"i": importacion_id},
        )
    )


def estado_de(sesion: Session, importacion_id: UUID) -> str:
    return str(
        sesion.execute(
            text("SELECT estado FROM importacion WHERE id = :i"), {"i": importacion_id}
        ).scalar_one()
    )
