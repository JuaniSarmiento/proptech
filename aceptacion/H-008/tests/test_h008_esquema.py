"""H-008 · C16 (esquema, protección y vocabulario): las tablas de la `0037` con RLS forzada,
`aceptacion_de_diferencias` de sólo agregar, y la acción nueva en el vocabulario y en la matriz
(E6)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from psycopg import errors

from .._edificios import fijar_tenant
from ..test_umbral_migracion import arranque
from ._h008 import (
    ACCION,
    TABLAS_0037,
    Mundo,
    aceptacion_creada,
    aceptar,
    archivo,
    control_base,
    exigir_tablas,
    subir,
)

pytestmark = pytest.mark.integracion


def _aceptacion(m: Mundo) -> tuple[str, str]:
    control = control_base()
    control[0][1] = "159000.00"
    cuerpo = subir(m, archivo(control=control))
    acepto = aceptacion_creada(aceptar(m, cuerpo["importacion_id"]))
    return cuerpo["importacion_id"], acepto["aceptacion_id"]


@pytest.mark.parametrize("tabla", TABLAS_0037)
def test_c16_tablas_con_rls_forzada(mundo: Mundo, tabla: str) -> None:
    exigir_tablas(mundo)
    fila = mundo.filas(
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = %s", (tabla,)
    )
    assert fila == [(True, True)], f"{tabla} necesita RLS activada y forzada: {fila}"


def test_c16_otra_administracion_no_ve_el_borrador_ni_la_aceptacion(mundo: Mundo) -> None:
    importacion_id, _ = _aceptacion(mundo)
    for tabla in TABLAS_0037:
        propias = mundo.uno(
            f"SELECT count(*) FROM {tabla} WHERE importacion_id = %s",  # noqa: S608
            (importacion_id,),
        )
        ajenas = mundo.uno(
            f"SELECT count(*) FROM {tabla} WHERE importacion_id = %s",  # noqa: S608
            (importacion_id,),
            admin=mundo.admin_b,
        )
        assert propias > 0, f"{tabla} no tiene filas de la importación de A"
        assert ajenas == 0, f"la administración B ve filas de {tabla} de A"


def test_c16_la_aceptacion_es_de_solo_agregar(mundo: Mundo) -> None:
    _, aceptacion_id = _aceptacion(mundo)
    with mundo.base.conectar_app() as app:
        for sentencia in (
            "UPDATE aceptacion_de_diferencias SET administracion_id = administracion_id "
            "WHERE id = %s",
            "DELETE FROM aceptacion_de_diferencias WHERE id = %s",
        ):
            with pytest.raises(errors.InsufficientPrivilege) as e, app.transaction():
                fijar_tenant(app, mundo.admin)
                app.execute(sentencia, (aceptacion_id,))
            assert e.value.sqlstate == "42501", f"la app no puede {sentencia.split()[0]}"
    with arranque(mundo.base) as c:
        for sentencia, args in (
            (
                "UPDATE aceptacion_de_diferencias SET administracion_id = administracion_id "
                "WHERE id = %s",
                (aceptacion_id,),
            ),
            ("DELETE FROM aceptacion_de_diferencias WHERE id = %s", (aceptacion_id,)),
            ("TRUNCATE aceptacion_de_diferencias CASCADE", ()),
        ):
            with pytest.raises(errors.RaiseException) as e2, c.transaction():
                c.execute(sentencia, args)
            assert e2.value.sqlstate == "P0001", f"el arranque tampoco: {sentencia.split()[0]}"
        fila = c.execute(
            "SELECT count(*) FROM aceptacion_de_diferencias WHERE id = %s", (aceptacion_id,)
        ).fetchone()
        assert fila == (1,), "la aceptación cambió"


def test_c16_la_aceptacion_esta_en_la_lista_de_solo_agregar(mundo: Mundo) -> None:
    from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

    nombres = {getattr(t, "nombre", t) for t in TABLAS_DE_SOLO_AGREGAR}
    assert "aceptacion_de_diferencias" in nombres, (
        "aceptacion_de_diferencias tiene que estar en TABLAS_DE_SOLO_AGREGAR (L-054, L-083)"
    )


def test_c16_la_accion_esta_en_el_vocabulario_y_en_la_matriz(mundo: Mundo) -> None:
    nombres = {f[0] for f in mundo.filas("SELECT nombre FROM accion_de_auditoria")}
    assert ACCION in nombres, "falta aceptar_diferencias_de_saldos en accion_de_auditoria"
    from proptech_core.acceso.dominio import permisos

    assert ACCION in {a.value for a in permisos.Accion}, "falta la acción en `Accion`"
    accion = permisos.Accion(ACCION)
    edificio = uuid4()

    def puede(rol: str, complejo: object, unidad: object = None, vinculo: object = None) -> bool:
        asignacion = permisos.Asignacion(rol, complejo, unidad, vinculo)  # type: ignore[arg-type]
        return permisos.puede([asignacion], accion, edificio)

    assert puede("super_admin", None)
    assert puede("administrador", None)
    assert not puede("administrador", edificio), "el administrador por edificio no acepta (E6)"
    assert not puede("contador", None)
    assert not puede("auxiliar", edificio)
    assert not puede("consejo", edificio)
    assert not puede("vecino", edificio, uuid4(), "propietario")
    assert not puede("vecino", edificio, uuid4(), "inquilino")
