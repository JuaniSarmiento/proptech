"""RF-D-2 (revisión final, 19/10/2026): un texto que queda vacío DESPUÉS
del recorte de 0013 (`fn_recortar_texto_3a`, R3A-6) se guardaba igual como
`''`. La API ya lo rechaza con 422 (`recortado_sin_control` levanta
`ValueError` si el recorte queda vacío, en `nombre`/`identificador`/
`localidad` de toda la familia) — pero nada en la BASE lo impedía: un
`INSERT`/`UPDATE` por SQL (como `proptech_app`) con `''`, o un valor que el
trigger de 0013 recorta hasta `''` (sólo espacios), pasaba sin error.

Antes de agregar el `CHECK`: ningún seed ni dato legítimo usa `''` en estas
columnas (`rg` en `backend/`, `config/`, `infra/`) — el único `''` que
aparece es el de `test_semilla_comando.py`, que ya prueba que el LECTOR de
semillas lo rechaza."""

import psycopg
import pytest

from ._edificios import Edificios, insertar_unidad

pytestmark = pytest.mark.integracion


def test_unidad_identificador_vacio_se_rechaza_en_la_base(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        insertar_unidad(app_edificio, edificios.administracion_a, edificios.complejo_a, "")


def test_grupo_nombre_vacio_se_rechaza_en_la_base(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        app_edificio.execute(
            "INSERT INTO grupo_de_reparto (administracion_id, complejo_id, clave, nombre, "
            "metodo) VALUES (%s, %s, 'vacio', '', 'coeficiente')",
            (edificios.administracion_a, edificios.complejo_a),
        )


def test_categoria_nombre_vacio_se_rechaza_en_la_base(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        app_edificio.execute(
            "INSERT INTO categoria_de_gasto (administracion_id, complejo_id, clave, nombre, "
            "orden) VALUES (%s, %s, 'vacia', '', 1)",
            (edificios.administracion_a, edificios.complejo_a),
        )


def test_complejo_nombre_vacio_se_rechaza_en_la_base(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        app_edificio.execute(
            "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
            "VALUES (gen_random_uuid(), %s, '', 'Mendoza')",
            (edificios.administracion_a,),
        )


def test_complejo_localidad_vacia_se_rechaza_en_la_base(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        app_edificio.execute(
            "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
            "VALUES (gen_random_uuid(), %s, 'Un edificio', '')",
            (edificios.administracion_a,),
        )


def test_un_valor_que_recorta_a_vacio_tambien_se_rechaza(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    """El trigger de 0013 (`fn_recortar_campos_3a`) recorta ANTES de
    guardar: un identificador de sólo espacios llega al CHECK ya vacío, no
    con los espacios que el cliente mandó."""
    with pytest.raises(psycopg.errors.CheckViolation):
        insertar_unidad(app_edificio, edificios.administracion_a, edificios.complejo_a, "   ")
