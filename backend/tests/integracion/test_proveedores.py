"""Bloque 2 de `gastos-y-cargos`: proveedores por edificio (R12, D-019)."""

from uuid import uuid4

import psycopg
import pytest
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad

from ._api_edificios import ApiEdificio
from ._edificios import Edificios, fijar_tenant

pytestmark = pytest.mark.integracion

_CUIT_A = "20123456786"
_CUIT_B = "20329642993"


# --- 2.3: alta contra PostgreSQL real ---


def test_alta_valida_queda_activa_y_se_lista(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Ascensores SA", "cuit": _CUIT_A}
    )
    assert respuesta.status_code == 201, respuesta.text
    proveedor_id = respuesta.json()["id"]
    listado = api_edificio.cliente.get(api_edificio.ruta("/proveedores")).json()
    fila = next(p for p in listado if p["id"] == proveedor_id)
    assert fila["razon_social"] == "Ascensores SA"
    assert fila["cuit"] == _CUIT_A
    assert fila["activo"] is True


def test_cuit_repetido_en_el_mismo_edificio_da_409(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Uno", "cuit": _CUIT_A}
    )
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Otro", "cuit": _CUIT_A}
    )
    assert respuesta.status_code == 409, respuesta.text


def test_mismo_cuit_en_dos_edificios_no_choca(api_edificio: ApiEdificio) -> None:
    #: "editar" (administrador) sólo alcanza `api_edificio.edificio`; para
    #: escribir en `otro` (misma administración) se necesita el alcance
    #: principal de super_admin — el 404 de abajo es por alcance, no por R12.
    api_edificio.como("super_admin")
    r1 = api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Uno", "cuit": _CUIT_A}
    )
    assert r1.status_code == 201, r1.text
    ruta_otro = f"/api/complejos/{api_edificio.otro}/proveedores"
    r2 = api_edificio.cliente.post(
        ruta_otro, json={"razon_social": "Otro edificio", "cuit": _CUIT_A}
    )
    assert r2.status_code == 201, r2.text


@pytest.mark.parametrize(
    "cuit,motivo",
    [
        ("20123456780", "dígito verificador equivocado"),
        ("2012345678", "diez dígitos"),
        ("20123456786 ", "espacio al final"),
    ],
)
def test_cuit_invalido_da_422_sin_repetir_el_valor(
    api_edificio: ApiEdificio, cuit: str, motivo: str
) -> None:
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Alguien", "cuit": cuit}
    )
    assert respuesta.status_code == 422, (motivo, respuesta.text)
    assert cuit not in respuesta.text


def test_proveedor_de_otro_edificio_por_sql_directo_rechazado(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with app_edificio.transaction():
            app_edificio.execute(
                "INSERT INTO proveedor (id, administracion_id, complejo_id, razon_social, cuit) "
                "VALUES (%s, %s, %s, 'Ajeno', %s)",
                (uuid4(), edificios.administracion_a, edificios.complejo_b, _CUIT_A),
            )


# --- 2.5: desactivación y reactivación, nunca borrado ---


def test_no_existe_ruta_de_borrado(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Uno", "cuit": _CUIT_A}
    )
    proveedor_id = alta.json()["id"]
    respuesta = api_edificio.cliente.delete(f"/api/proveedores/{proveedor_id}")
    assert respuesta.status_code == 405, respuesta.text


def test_desactivar_oculta_de_disponibles_y_reactivar_lo_devuelve(
    api_edificio: ApiEdificio,
) -> None:
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Uno", "cuit": _CUIT_A}
    )
    proveedor_id = alta.json()["id"]
    desactivar = api_edificio.cliente.patch(
        f"/api/proveedores/{proveedor_id}", json={"activo": False}
    )
    assert desactivar.status_code == 200, desactivar.text
    disponibles = api_edificio.cliente.get(
        api_edificio.ruta("/proveedores"), params={"solo_activos": "true"}
    ).json()
    assert proveedor_id not in [p["id"] for p in disponibles]
    todos = api_edificio.cliente.get(api_edificio.ruta("/proveedores")).json()
    fila = next(p for p in todos if p["id"] == proveedor_id)
    assert fila["activo"] is False
    assert fila["razon_social"] == "Uno"
    assert fila["cuit"] == _CUIT_A
    reactivar = api_edificio.cliente.patch(
        f"/api/proveedores/{proveedor_id}", json={"activo": True}
    )
    assert reactivar.status_code == 200, reactivar.text
    disponibles = api_edificio.cliente.get(
        api_edificio.ruta("/proveedores"), params={"solo_activos": "true"}
    ).json()
    assert proveedor_id in [p["id"] for p in disponibles]


def test_proveedor_desactivado_conserva_sus_gastos_aprobados_en_el_calculo(
    api_edificio: ApiEdificio,
) -> None:
    """2.5, escenario pendiente del bloque 3 (verify del cierre, hallazgo 1,
    29/10/2026): un gasto ya aprobado contra un proveedor que después se
    desactiva sigue sumando en `gastos-aprobados` — desactivar es sobre el
    proveedor, nunca sobre lo que ya se aprobó."""
    api_edificio.como("super_admin")
    nombre = f"Prueba desactivado {uuid4().hex[:8]}"
    categoria_resp = api_edificio.cliente.post(
        api_edificio.ruta("/categorias"), json={"nombre": nombre}
    )
    grupo_resp = api_edificio.cliente.post(
        api_edificio.ruta("/grupos"),
        json={"nombre": nombre, "metodo": "coeficiente", "unidades": []},
    )
    categoria, grupo = categoria_resp.json()["id"], grupo_resp.json()["id"]

    api_edificio.como("editar")
    proveedor_id = api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Uno", "cuit": _CUIT_A}
    ).json()["id"]
    gasto_id = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": "Service del ascensor",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "proveedor_id": proveedor_id,
            "periodo": "2026-10-01",
            "importe": "1000.00",
        },
    ).json()["id"]
    aprobar = api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    assert aprobar.status_code == 200, aprobar.text

    desactivar = api_edificio.cliente.patch(
        f"/api/proveedores/{proveedor_id}", json={"activo": False}
    )
    assert desactivar.status_code == 200, desactivar.text

    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert lectura["grupos"][grupo]["total"] == "1000.00"


# --- 2.6: alcance, permisos y aislamiento ---


def test_proveedor_de_edificio_fuera_de_alcance_da_404(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    ruta_ajena = f"/api/complejos/{api_edificio.ajeno}/proveedores"
    respuesta = api_edificio.cliente.get(ruta_ajena)
    assert respuesta.status_code == 404, respuesta.text


def test_lectura_del_contador(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Uno", "cuit": _CUIT_A}
    )
    api_edificio.como("contador")
    respuesta = api_edificio.cliente.get(api_edificio.ruta("/proveedores"))
    assert respuesta.status_code == 200, respuesta.text
    assert len(respuesta.json()) == 1


def test_escritura_del_contador_da_403(api_edificio: ApiEdificio) -> None:
    api_edificio.como("contador")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Uno", "cuit": _CUIT_A}
    )
    assert respuesta.status_code == 403, respuesta.text


def test_aislamiento_entre_administraciones_por_rls(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    fijar_tenant(app_edificio, edificios.administracion_b)
    app_edificio.execute(
        "INSERT INTO proveedor (id, administracion_id, complejo_id, razon_social, cuit) "
        "VALUES (%s, %s, %s, 'De B', %s)",
        (uuid4(), edificios.administracion_b, edificios.complejo_b, _CUIT_A),
    )
    fijar_tenant(app_edificio, edificios.administracion_a)
    assert app_edificio.execute("SELECT id FROM proveedor").fetchall() == []


# --- 2.7: auditoría de proveedor ---


def test_alta_auditada_sin_cuit(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Uno", "cuit": _CUIT_A}
    )
    proveedor_id = alta.json()["id"]
    filas = api_edificio.filas(
        "SELECT accion, detalle::text FROM auditoria WHERE entidad_id = %s", (proveedor_id,)
    )
    assert len(filas) == 1
    accion, detalle = filas[0]
    assert accion == "crear_proveedor"
    assert _CUIT_A not in detalle


def test_edicion_sin_cambios_no_deja_fila(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/proveedores"), json={"razon_social": "Uno", "cuit": _CUIT_A}
    )
    proveedor_id = alta.json()["id"]
    api_edificio.cliente.patch(f"/api/proveedores/{proveedor_id}", json={"razon_social": "Uno"})
    filas = api_edificio.filas(
        "SELECT accion FROM auditoria WHERE entidad_id = %s AND accion = 'editar_proveedor'",
        (proveedor_id,),
    )
    assert filas == []


def test_auditoria_falla_y_el_proveedor_no_queda(
    sesion_edificio: Session, identidad_edificio: Identidad, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import text

    from proptech_core.gastos.aplicacion import proveedores

    admin = identidad_edificio.administracion_id
    complejo_id = uuid4()
    sesion_edificio.execute(
        text(
            "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
            "VALUES (:id, :admin, 'Edificio', 'Mendoza')"
        ),
        {"id": complejo_id, "admin": admin},
    )
    sesion_edificio.flush()

    def _registrar_roto(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("falla forzada de auditoría")

    monkeypatch.setattr(proveedores, "registrar", _registrar_roto)
    with pytest.raises(RuntimeError):
        proveedores.crear_proveedor(
            sesion_edificio,
            identidad_edificio,
            complejo_id=complejo_id,
            datos={"razon_social": "Uno", "cuit": _CUIT_A},
            request_id=uuid4(),
        )
    assert proveedores.listar_proveedores(sesion_edificio, complejo_id) == []
