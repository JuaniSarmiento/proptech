"""D7 (tarea 4.4): autogeneración de clave en sus dos llamadores (grupos y
categorías, L-009): sin clave se deriva del nombre; una clave explícita
sigue aceptándose (parámetros, importador); renombrar no cambia la clave."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.complejos.aplicacion import categorias, grupos
from proptech_core.complejos.aplicacion.errores import EntradaInvalida

from .test_unidades_casos_de_uso import crear

pytestmark = pytest.mark.integracion


def test_grupo_sin_clave_se_deriva_del_nombre(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """Escenario "Clave derivada del nombre" aplicado al llamador real."""
    edificio = crear(sesion_edificio, identidad_edificio)
    grupo_id = grupos.crear_grupo(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        datos={"nombre": "Pileta y SUM", "metodo": "coeficiente"},
        miembros=[],
        request_id=uuid4(),
    )
    fila = next(g for g in grupos.listar_grupos(sesion_edificio, edificio) if g["id"] == grupo_id)
    assert fila["clave"] == "pileta_y_sum"


def test_grupo_con_clave_explicita_se_respeta(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """La API sigue aceptando una clave explícita (parámetros, importador)."""
    edificio = crear(sesion_edificio, identidad_edificio)
    grupo_id = grupos.crear_grupo(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        datos={"clave": "pileta", "nombre": "Pileta", "metodo": "coeficiente"},
        miembros=[],
        request_id=uuid4(),
    )
    fila = next(g for g in grupos.listar_grupos(sesion_edificio, edificio) if g["id"] == grupo_id)
    assert fila["clave"] == "pileta"


def test_grupo_clave_derivada_repetida_se_desempata(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    grupos.crear_grupo(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        datos={"clave": "pileta", "nombre": "Pileta", "metodo": "coeficiente"},
        miembros=[],
        request_id=uuid4(),
    )
    grupo_id = grupos.crear_grupo(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        datos={"nombre": "Pileta", "metodo": "coeficiente"},
        miembros=[],
        request_id=uuid4(),
    )
    fila = next(g for g in grupos.listar_grupos(sesion_edificio, edificio) if g["id"] == grupo_id)
    assert fila["clave"] == "pileta_2"


def test_grupo_sin_clave_derivable_da_422(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """Escenario "Nombre del que no sale ninguna clave"."""
    edificio = crear(sesion_edificio, identidad_edificio)
    with pytest.raises(EntradaInvalida) as exc_info:
        grupos.crear_grupo(
            sesion_edificio,
            identidad_edificio,
            complejo_id=edificio,
            datos={"nombre": "— —", "metodo": "coeficiente"},
            miembros=[],
            request_id=uuid4(),
        )
    assert exc_info.value.campo == "nombre"


def test_renombrar_grupo_no_cambia_la_clave(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """Escenario "Renombrar no cambia la clave"."""
    edificio = crear(sesion_edificio, identidad_edificio)
    grupo_id = grupos.crear_grupo(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        datos={"nombre": "Pileta", "metodo": "coeficiente"},
        miembros=[],
        request_id=uuid4(),
    )
    grupos.editar_grupo(
        sesion_edificio,
        identidad_edificio,
        grupo_id=grupo_id,
        cambios={"nombre": "Pileta y solárium"},
        request_id=uuid4(),
    )
    fila = next(g for g in grupos.listar_grupos(sesion_edificio, edificio) if g["id"] == grupo_id)
    assert fila["clave"] == "pileta"
    assert fila["nombre"] == "Pileta y solárium"


def test_categoria_sin_clave_se_deriva_del_nombre(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """Escenario "Agregar una categoría"."""
    edificio = crear(sesion_edificio, identidad_edificio)
    categoria_id = categorias.crear_categoria(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        datos={"nombre": "Seguridad nocturna"},
    )
    fila = next(
        c
        for c in categorias.listar_categorias(sesion_edificio, edificio)
        if c["id"] == categoria_id
    )
    assert fila["clave"] == "seguridad_nocturna"


def test_renombrar_categoria_no_cambia_la_clave(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """Escenario "Renombrar una categoría" (nombre propio, distinto de las
    nueve que trae la semilla de `parametros.yaml`, para no chocar con
    "Limpieza")."""
    edificio = crear(sesion_edificio, identidad_edificio)
    categoria_id = categorias.crear_categoria(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        datos={"nombre": "Jardinería"},
    )
    categorias.editar_categoria(
        sesion_edificio,
        identidad_edificio,
        categoria_id=categoria_id,
        cambios={"nombre": "Jardinería y riego"},
        request_id=uuid4(),
    )
    fila = next(
        c
        for c in categorias.listar_categorias(sesion_edificio, edificio)
        if c["id"] == categoria_id
    )
    assert fila["clave"] == "jardineria"
    assert fila["nombre"] == "Jardinería y riego"
