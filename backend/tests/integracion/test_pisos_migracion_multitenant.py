"""3.4: migración `0024` — el mapeo de `unidad.piso` (texto libre → el
vocabulario nuevo) bajo el candado de D9, probado sobre una copia con
**más de una administración** real (no una base vacía de un solo
tenant), y la bajada que rellena `''` (nunca un valor inventado)."""

from uuid import uuid4

import psycopg
import pytest

from ._edificios import BaseDeEdificio, Edificios, fijar_tenant

pytestmark = pytest.mark.integracion

#: Mapeo exacto que el Migration Plan describe (D3): coincidencia textual,
#: sin recortar espacios, sin distinguir mayúsculas de minúsculas aposta.
_CASOS = {
    "PB": "PB",
    "SS": "SS1",
    "": None,
    "4": "4",
    "Entrepiso": None,
    "1°": None,
    " 2 ": None,
    "pb": None,
    "SS2": None,  # sin más contexto que "SS2": no es un valor conocido del mapeo.
    "61": None,  # fuera del rango 1-60: no matchea el patrón de mapeo.
}


def test_mapeo_de_piso_en_mas_de_una_administracion(
    base_del_edificio: BaseDeEdificio,
) -> None:
    admin_x, admin_y = uuid4(), uuid4()
    complejo_x, complejo_y = uuid4(), uuid4()
    unidades_x: dict[str, object] = {}
    unidades_y: dict[str, object] = {}
    try:
        base_del_edificio.devolver_tablas_protegidas()
        base_del_edificio.migrar("downgrade", "0023")

        with base_del_edificio.conectar_app() as app, app.transaction():
            for admin, complejo, unidades, nombre in (
                (admin_x, complejo_x, unidades_x, "Edificio X"),
                (admin_y, complejo_y, unidades_y, "Edificio Y"),
            ):
                fijar_tenant(app, admin)
                app.execute(
                    "INSERT INTO administracion (id, nombre) VALUES (%s, %s)",
                    (admin, f"Administración de {nombre}"),
                )
                app.execute(
                    "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                    "VALUES (%s, %s, %s, 'Mendoza')",
                    (complejo, admin, nombre),
                )
                for valor_viejo in _CASOS:
                    unidad_id = uuid4()
                    identificador = f"U-{valor_viejo!r}"
                    app.execute(
                        "INSERT INTO unidad (id, administracion_id, complejo_id, "
                        "identificador, tipo, piso, coeficiente, superficie_m2) "
                        "VALUES (%s, %s, %s, %s, 'departamento', %s, '1', '1')",
                        (unidad_id, admin, complejo, identificador, valor_viejo),
                    )
                    unidades[valor_viejo] = unidad_id

        base_del_edificio.migrar("upgrade", "head")

        with base_del_edificio.conectar_app() as app, app.transaction():
            for admin, unidades in ((admin_x, unidades_x), (admin_y, unidades_y)):
                fijar_tenant(app, admin)
                for valor_viejo, esperado in _CASOS.items():
                    fila = app.execute(
                        "SELECT piso FROM unidad WHERE id = %s", (unidades[valor_viejo],)
                    ).fetchone()
                    assert fila == (esperado,), (
                        f"admin {admin}, piso viejo {valor_viejo!r}: "
                        f"esperaba {esperado!r}, fue {fila}"
                    )

        # --- Bajada: rellena '' en las dos administraciones, nunca 'PB'. ---
        base_del_edificio.devolver_tablas_protegidas()
        base_del_edificio.migrar("downgrade", "0023")
        with base_del_edificio.conectar_app() as app, app.transaction():
            for admin, unidades in ((admin_x, unidades_x), (admin_y, unidades_y)):
                fijar_tenant(app, admin)
                for valor_viejo, esperado in _CASOS.items():
                    fila = app.execute(
                        "SELECT piso FROM unidad WHERE id = %s", (unidades[valor_viejo],)
                    ).fetchone()
                    if esperado is None:
                        assert fila == ("",), (admin, valor_viejo, fila)
                    else:
                        assert fila == (esperado,), (admin, valor_viejo, fila)
    finally:
        base_del_edificio.migrar("upgrade", "head")


def test_check_de_forma_del_piso_rechaza_por_sql(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    """El `CHECK ck_unidad_piso` de `0024` frena por SQL, no sólo por la
    API. Escenario "El piso no se sale del vocabulario por SQL"."""
    with pytest.raises(psycopg.errors.CheckViolation):
        app_edificio.execute(
            "UPDATE unidad SET piso = 'Entrepiso' WHERE id = %s", (edificios.unidad_a,)
        )


def test_piso_nulo_se_acepta_por_sql(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    """Una unidad migrada sin completar (D3): `piso IS NULL` es válido."""
    fila = app_edificio.execute(
        "UPDATE unidad SET piso = NULL WHERE id = %s RETURNING piso", (edificios.unidad_a,)
    ).fetchone()
    assert fila == (None,)
