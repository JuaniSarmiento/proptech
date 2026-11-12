"""Ayudas de los tests de la tarea 1.5 de `importacion-desde-excel`: un mundo sembrado y
**confirmado** (la sesión del caso de uso es otra conexión), archivos `.xlsx` inventados y los
conteos de lo que importar podría escribir. Todo con datos ficticios."""

from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from openpyxl import Workbook
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad

from ._edificios import BaseDeEdificio, fijar_tenant

ENCABEZADOS = ["Unidad", "Tipo", "Piso", "Coeficiente", "Superficie m2", "Propietario", "Email"]
MIGRACION = date(2026, 10, 15)
RELOJ: Callable[[], datetime] = lambda: datetime(2026, 11, 12, 15, tzinfo=UTC)  # noqa: E731


def filas_validas() -> list[dict[str, Any]]:
    """Las 12 unidades de la Torre Ficticia (3 pisos y 1 subsuelo); los coeficientes suman 1."""
    datos = [
        ("1A", "departamento", "1"),
        ("1B", "departamento", "1"),
        ("2B", "departamento", "2"),
        ("1C", "departamento", "1"),
        ("2A", "departamento", "2"),
        ("2C", "departamento", "2"),
        ("3A", "departamento", "3"),
        ("3B", "departamento", "3"),
        ("3C", "departamento", "3"),
        ("L1", "local", "PB"),
        ("C1", "cochera", "SS1"),
        ("C2", "baulera", "SS1"),
    ]
    return [
        {
            "Unidad": unidad,
            "Tipo": tipo,
            "Piso": piso,
            "Coeficiente": "0.083337" if n == 11 else "0.083333",
            "Superficie m2": f"{50 + n}.25",
            "Propietario": f"Persona Ficticia {n + 1}" if n < 10 else None,
            "Email": f"propietario{n + 1}@ficticio.test" if n < 10 else None,
        }
        for n, (unidad, tipo, piso) in enumerate(datos)
    ]


def libro(hojas: dict[str, list[list[Any]]]) -> bytes:
    wb = Workbook()
    for inicial in list(wb.worksheets):
        wb.remove(inicial)
    for nombre, filas in hojas.items():
        hoja = wb.create_sheet(nombre)
        for fila in filas:
            hoja.append(list(fila))
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


def padron(filas: list[dict[str, Any]] | None = None) -> bytes:
    filas = filas_validas() if filas is None else filas
    return libro({"Unidades": [ENCABEZADOS, *[[f.get(c) for c in ENCABEZADOS] for f in filas]]})


@dataclass
class Mundo:
    """Una administración A con cinco edificios y cinco personas, todo ya confirmado en la base."""

    base: BaseDeEdificio
    admin: UUID
    torre: UUID  # 3 pisos, 1 subsuelo, sin unidades
    sin_pisos: UUID
    con_padron: UUID  # ya tiene la unidad `9Z`
    otro: UUID  # un edificio más de A
    super_admin: Identidad
    principal: Identidad  # administrador principal
    de_la_torre: Identidad  # administrador sólo de la torre
    de_otro: Identidad  # administrador sólo de `otro`
    contador: Identidad  # contador principal
    auxiliar: Identidad  # auxiliar de la torre
    admin_b: UUID
    complejo_b: UUID

    def conectar(self, administracion: UUID | None = None) -> Any:
        conexion = self.base.conectar_app()
        conexion.autocommit = False
        fijar_tenant(conexion, administracion or self.admin)
        return conexion


def sembrar(base: BaseDeEdificio) -> Mundo:
    admin, admin_b = uuid4(), uuid4()
    with base.conectar_app() as c:
        c.autocommit = False
        for a in (admin, admin_b):
            fijar_tenant(c, a)
            c.execute("INSERT INTO administracion (id, nombre) VALUES (%s, 'Ficticia')", (a,))
        fijar_tenant(c, admin)

        def complejo(pisos: int | None, subsuelos: int | None, nombre: str) -> UUID:
            id_ = uuid4()
            c.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad, pisos, subsuelos) "
                "VALUES (%s, %s, %s, 'Mendoza', %s, %s)",
                (id_, admin, nombre, pisos, subsuelos),
            )
            return id_

        torre = complejo(3, 1, "Torre Ficticia")
        sin_pisos = complejo(None, None, "Sin pisos")
        con_padron = complejo(3, 1, "Con padrón")
        otro = complejo(3, 1, "Otro")
        c.execute(
            "INSERT INTO unidad (administracion_id, complejo_id, identificador, tipo, piso, "
            "coeficiente, superficie_m2) VALUES (%s, %s, '9Z', 'departamento', '1', '1.000000', "
            "'60.00')",
            (admin, con_padron),
        )

        def persona(nombre: str, rol: str, complejo_id: UUID | None) -> Identidad:
            id_ = uuid4()
            c.execute(
                "INSERT INTO persona (id, administracion_id, nombre, email) "
                "VALUES (%s, %s, %s, %s)",
                (id_, admin, nombre, f"{id_.hex[:8]}@ficticio.test"),
            )
            c.execute(
                "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id) "
                "VALUES (%s, %s, %s, %s)",
                (admin, id_, rol, complejo_id),
            )
            return Identidad(admin, id_)

        super_admin = persona("Super", "super_admin", None)
        principal = persona("Principal", "administrador", None)
        de_la_torre = persona("De la torre", "administrador", torre)
        de_otro = persona("De otro", "administrador", otro)
        contador = persona("Contador", "contador", None)
        auxiliar = persona("Auxiliar", "auxiliar", torre)
        fijar_tenant(c, admin_b)
        complejo_b = uuid4()
        c.execute(
            "INSERT INTO complejo (id, administracion_id, nombre, localidad, pisos, subsuelos) "
            "VALUES (%s, %s, 'De B', 'Mendoza', 3, 1)",
            (complejo_b, admin_b),
        )
        c.commit()
    return Mundo(
        base, admin, torre, sin_pisos, con_padron, otro, super_admin, principal, de_la_torre,
        de_otro, contador, auxiliar, admin_b, complejo_b,
    )  # fmt: skip


def con_tenant(sesion: Session, administracion: UUID) -> None:
    sesion.execute(
        text("SELECT set_config('app.administracion_id', :id, true)"), {"id": str(administracion)}
    )


def conteos(sesion: Session) -> dict[str, int]:
    """Todo lo que importar podría escribir (la sesión ya tiene su tenant)."""
    consultas = {
        "unidad": "SELECT count(*) FROM unidad",
        "persona": "SELECT count(*) FROM persona",
        "asignacion_vecino": "SELECT count(*) FROM asignacion_rol WHERE rol = 'vecino'",
        "auditoria": "SELECT count(*) FROM auditoria",
        "invitacion": "SELECT count(*) FROM invitacion",
    }
    resultado = {k: int(sesion.execute(text(q)).scalar_one()) for k, q in consultas.items()}
    # Antes de la 0036 la tabla no existe: el conteo es 0 y los tests fallan por aserción.
    hay = sesion.execute(text("SELECT to_regclass('importacion') IS NOT NULL")).scalar_one()
    resultado["importacion"] = (
        int(sesion.execute(text("SELECT count(*) FROM importacion")).scalar_one()) if hay else 0
    )
    return resultado
