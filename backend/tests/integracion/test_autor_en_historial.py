"""`autor_nombre` en el historial de configuración (D5, tarea 2.2).

`configuracion-versionada` > Historial con dos autores; > Edificio recién
creado.
"""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.complejos.aplicacion import lectura

from .test_unidades_casos_de_uso import crear
from .test_versiones_casos_de_uso import version

pytestmark = pytest.mark.integracion


def otra_persona(sesion: Session, identidad: Identidad, nombre: str) -> Identidad:
    """Otra persona de la MISMA administración que `identidad`."""
    persona_id = uuid4()
    sesion.execute(
        text("INSERT INTO persona (id, administracion_id, nombre) VALUES (:id, :admin, :nombre)"),
        {"id": persona_id, "admin": identidad.administracion_id, "nombre": nombre},
    )
    return Identidad(identidad.administracion_id, persona_id)


def test_historial_con_dos_autores(sesion_edificio: Session, identidad_edificio: Identidad) -> None:
    nombre_autor_a = sesion_edificio.execute(
        text("SELECT nombre FROM persona WHERE id=:id"), {"id": identidad_edificio.persona_id}
    ).scalar_one()
    autor_b = otra_persona(sesion_edificio, identidad_edificio, "Autor B")
    edificio = crear(sesion_edificio, identidad_edificio)
    version(sesion_edificio, autor_b, edificio, date(2026, 11, 2), tasa_mensual="4.00")

    versiones = lectura.listar_versiones(sesion_edificio, edificio)
    assert len(versiones) == 2
    assert versiones[0]["autor_id"] == identidad_edificio.persona_id
    assert versiones[0]["autor_nombre"] == nombre_autor_a
    assert versiones[1]["autor_id"] == autor_b.persona_id
    assert versiones[1]["autor_nombre"] == "Autor B"


def test_edificio_recien_creado_trae_el_nombre_del_autor(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    nombre_autor = sesion_edificio.execute(
        text("SELECT nombre FROM persona WHERE id=:id"), {"id": identidad_edificio.persona_id}
    ).scalar_one()
    edificio = crear(sesion_edificio, identidad_edificio)
    versiones = lectura.listar_versiones(sesion_edificio, edificio)
    assert len(versiones) == 1
    assert versiones[0]["autor_nombre"] == nombre_autor
