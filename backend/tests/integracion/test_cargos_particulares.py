"""Bloque 5 de `gastos-y-cargos`: cargos particulares (R14, D-025)."""

from uuid import uuid4

import psycopg
import pytest

from ._api_edificios import ApiEdificio
from ._edificios import Edificios, insertar_unidad

pytestmark = pytest.mark.integracion


def _datos(unidad_id: str, **extra: object) -> dict[str, object]:
    base: dict[str, object] = {
        "unidad_id": unidad_id,
        "concepto": "Uso del quincho",
        "importe": "5000.00",
        "periodo": "2026-10-01",
        "motivo": "Reserva del 12/10",
    }
    base.update(extra)
    return base


# --- 5.1: pertenece a una sola unidad ---


def test_alta_valida_queda_en_borrador(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"), json=_datos(str(api_edificio.unidad))
    )
    assert respuesta.status_code == 201, respuesta.text
    cargo_id = respuesta.json()["id"]
    cargo = api_edificio.cliente.get(f"/api/cargos-particulares/{cargo_id}").json()
    assert cargo["estado"] == "borrador"
    assert cargo["unidad_id"] == str(api_edificio.unidad)
    assert cargo["importe"] == "5000.00"


def test_unidad_de_otro_edificio_da_404_y_sql_directo_rechazado(
    api_edificio: ApiEdificio, app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"), json=_datos(str(api_edificio.unidad_ajena))
    )
    assert respuesta.status_code == 404, respuesta.text
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with app_edificio.transaction():
            app_edificio.execute(
                "INSERT INTO cargo_particular (id, administracion_id, complejo_id, unidad_id, "
                "concepto, importe, periodo, motivo) "
                "VALUES (%s, %s, %s, %s, 'x', '10.00', '2026-10-01', 'x')",
                (
                    uuid4(),
                    edificios.administracion_a,
                    edificios.complejo_a,
                    uuid4(),
                ),
            )


def test_importe_con_tres_decimales_da_422(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"),
        json=_datos(str(api_edificio.unidad), importe="5000.001"),
    )
    assert respuesta.status_code == 422, respuesta.text


def test_no_acepta_grupo_de_reparto(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"),
        json=_datos(str(api_edificio.unidad), grupo_id=str(uuid4())),
    )
    assert respuesta.status_code == 422, respuesta.text


# --- 5.3: aislamiento del cargo ---


def test_cargo_solo_afecta_a_su_unidad(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"), json=_datos(str(api_edificio.unidad))
    )
    cargo_id = alta.json()["id"]
    api_edificio.cliente.post(f"/api/cargos-particulares/{cargo_id}/aprobar")
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/cargos-aprobados")
    ).json()
    assert str(api_edificio.unidad) in lectura["unidades"]
    assert lectura["unidades"][str(api_edificio.unidad)]["total"] == "5000.00"
    assert str(api_edificio.otra_unidad) not in lectura["unidades"]


def test_cargo_no_cambia_el_total_de_ningun_grupo(api_edificio: ApiEdificio) -> None:
    api_edificio.como("super_admin")
    categoria = api_edificio.cliente.post(
        api_edificio.ruta("/categorias"), json={"nombre": f"Cat {uuid4().hex[:8]}"}
    ).json()["id"]
    grupo = api_edificio.cliente.post(
        api_edificio.ruta("/grupos"),
        json={"nombre": f"Grupo {uuid4().hex[:8]}", "metodo": "coeficiente", "unidades": []},
    ).json()["id"]
    gasto = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": "Gasto de referencia",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": "2026-10-01",
            "importe": "1000.00",
        },
    ).json()["id"]
    api_edificio.cliente.post(f"/api/gastos/{gasto}/aprobar")
    lectura_sin_cargo = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    cargo = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"), json=_datos(str(api_edificio.unidad))
    ).json()["id"]
    api_edificio.cliente.post(f"/api/cargos-particulares/{cargo}/aprobar")
    lectura_con_cargo = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert (
        lectura_sin_cargo["grupos"][grupo]["total"] == lectura_con_cargo["grupos"][grupo]["total"]
    )
    assert lectura_con_cargo["total"] == lectura_sin_cargo["total"]


def test_cargo_llega_en_su_propia_lista_separado_de_los_gastos(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    cargo = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"), json=_datos(str(api_edificio.unidad))
    ).json()["id"]
    api_edificio.cliente.post(f"/api/cargos-particulares/{cargo}/aprobar")
    gastos_del_periodo = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert gastos_del_periodo["grupos"] == {}
    cargos_del_periodo = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/cargos-aprobados")
    ).json()
    assert str(api_edificio.unidad) in cargos_del_periodo["unidades"]


# --- 5.4: mutante obligatorio ---


def test_mutante_que_suma_cargos_al_total_del_grupo_rompe_la_comparacion(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Copia de `gastos_aprobados_del_periodo` que además suma los cargos
    particulares de las unidades del grupo al total — nunca el archivo
    real (L-013); se aplica con `monkeypatch` sobre el módulo."""
    from sqlalchemy import text

    from proptech_core.compartido.dinero import Dinero
    from proptech_core.gastos.aplicacion import gastos as modulo_gastos

    api_edificio.como("super_admin")
    categoria = api_edificio.cliente.post(
        api_edificio.ruta("/categorias"), json={"nombre": f"Cat {uuid4().hex[:8]}"}
    ).json()["id"]
    grupo = api_edificio.cliente.post(
        api_edificio.ruta("/grupos"),
        json={
            "nombre": f"Grupo {uuid4().hex[:8]}",
            "metodo": "coeficiente",
            "unidades": [{"unidad_id": str(api_edificio.unidad)}],
        },
    ).json()["id"]
    gasto = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": "Gasto",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": "2026-10-01",
            "importe": "1000.00",
        },
    ).json()["id"]
    api_edificio.cliente.post(f"/api/gastos/{gasto}/aprobar")
    lectura_real = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    total_sin_mutar = lectura_real["grupos"][grupo]["total"]
    assert total_sin_mutar == "1000.00"

    cargo = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"), json=_datos(str(api_edificio.unidad))
    ).json()["id"]
    api_edificio.cliente.post(f"/api/cargos-particulares/{cargo}/aprobar")

    original = modulo_gastos.gastos_aprobados_del_periodo

    def _mutada(sesion, complejo_id, periodo):  # type: ignore[no-untyped-def]
        #: Real + MUTANTE: además suma los cargos particulares aprobados de
        #: ese período al total (del grupo y al general) — lo que R14/D2
        #: prohíbe.
        resultado = dict(original(sesion, complejo_id, periodo))
        extra = sesion.execute(
            text(
                "SELECT COALESCE(SUM(importe), 0)::text FROM cargo_particular "
                "WHERE complejo_id=:complejo AND periodo=:periodo AND estado='aprobado'"
            ),
            {"complejo": complejo_id, "periodo": periodo},
        ).scalar_one()
        resultado["total"] = (Dinero(resultado["total"]) + Dinero(extra)).a_texto()
        resultado["grupos"] = {
            g: {**datos, "total": (Dinero(datos["total"]) + Dinero(extra)).a_texto()}
            for g, datos in resultado["grupos"].items()
        }
        return resultado

    monkeypatch.setattr(modulo_gastos, "gastos_aprobados_del_periodo", _mutada)
    lectura_mutada = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    assert lectura_mutada["grupos"][grupo]["total"] != total_sin_mutar, (
        "el mutante tiene que romper la comparación: el cargo particular ya no da lo mismo"
    )
    assert lectura_mutada["grupos"][grupo]["total"] == "6000.00"


# --- 5.5: aprobación ---


def test_cargo_en_borrador_no_entra(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"), json=_datos(str(api_edificio.unidad))
    )
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/cargos-aprobados")
    ).json()
    assert lectura["unidades"] == {}


def test_aprobar_dos_veces_no_duplica_ni_la_auditoria(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    cargo = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"), json=_datos(str(api_edificio.unidad))
    ).json()["id"]
    api_edificio.cliente.post(f"/api/cargos-particulares/{cargo}/aprobar")
    api_edificio.cliente.post(f"/api/cargos-particulares/{cargo}/aprobar")
    filas = api_edificio.filas(
        "SELECT accion FROM auditoria WHERE entidad_id = %s "
        "AND accion = 'aprobar_cargo_particular'",
        (cargo,),
    )
    assert len(filas) == 1
    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/cargos-aprobados")
    ).json()
    assert len(lectura["unidades"][str(api_edificio.unidad)]["cargos"]) == 1


def test_editar_importe_de_aprobado_se_rechaza(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    cargo = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"), json=_datos(str(api_edificio.unidad))
    ).json()["id"]
    api_edificio.cliente.post(f"/api/cargos-particulares/{cargo}/aprobar")
    respuesta = api_edificio.cliente.patch(
        f"/api/cargos-particulares/{cargo}", json={"importe": "1.00"}
    )
    assert respuesta.status_code == 422, respuesta.text
    assert (
        api_edificio.cliente.get(f"/api/cargos-particulares/{cargo}").json()["importe"] == "5000.00"
    )


def test_aprobar_sin_permiso_da_403(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    cargo = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"), json=_datos(str(api_edificio.unidad))
    ).json()["id"]
    api_edificio.como("contador")
    respuesta = api_edificio.cliente.post(f"/api/cargos-particulares/{cargo}/aprobar")
    assert respuesta.status_code == 403, respuesta.text
    # D-131 (2d): todo 403 lleva `codigo`; sumado al integrar `main`.
    assert respuesta.json()["detail"].get("codigo") == "sin_permiso", respuesta.text


# --- 5.6/5.7: importación desde Excel ---


def test_importacion_valida_tres_filas_crea_tres_cargos(api_edificio: ApiEdificio) -> None:
    from proptech_core.gastos.aplicacion import cargos_particulares
    from proptech_core.gastos.puertos import FilaCargoImportada

    from ..conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION  # noqa: F401

    identificadores = []
    with api_edificio.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_edificio.admin),)
        )
        for _ in range(3):
            ident = f"U-{uuid4().hex[:6]}"
            insertar_unidad(conexion, api_edificio.admin, api_edificio.edificio, ident)
            identificadores.append(ident)

    class _LectorFalso:
        def leer(self, contenido: bytes) -> list[FilaCargoImportada]:
            return [
                FilaCargoImportada(i + 2, ident, "Expensa extra", "1000.00")
                for i, ident in enumerate(identificadores)
            ]

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import NullPool

    from proptech_core.acceso.dominio.identidad import Identidad

    def conectar():  # type: ignore[no-untyped-def]
        con = api_edificio.base.conectar_app()
        con.autocommit = False
        return con

    engine = create_engine("postgresql+psycopg://", creator=conectar, poolclass=NullPool)
    try:
        with Session(engine) as sesion:
            from sqlalchemy import text

            sesion.execute(
                text("SELECT set_config('app.administracion_id', :id, true)"),
                {"id": str(api_edificio.admin)},
            )
            cantidad = cargos_particulares.importar_cargos_particulares(
                sesion,
                Identidad(api_edificio.admin, api_edificio.personas["super_admin"]),
                complejo_id=api_edificio.edificio,
                lector=_LectorFalso(),
                contenido=b"",
                periodo=__import__("datetime").date(2026, 10, 1),
                request_id=uuid4(),
            )
            sesion.commit()
    finally:
        engine.dispose()
    assert cantidad == 3


def test_fila_con_unidad_inexistente_aborta_todo_y_nombra_la_fila(
    api_edificio: ApiEdificio,
) -> None:
    from proptech_core.gastos.aplicacion import cargos_particulares
    from proptech_core.gastos.aplicacion.errores import ImportacionInvalida
    from proptech_core.gastos.puertos import FilaCargoImportada

    class _LectorFalso:
        def leer(self, contenido: bytes) -> list[FilaCargoImportada]:
            #: "1A" es el identificador real de `api_edificio.unidad` (ver
            #: la siembra de `api_edificio` en conftest.py) — el lector lee
            #: identificadores de unidad, nunca UUIDs.
            return [
                FilaCargoImportada(2, "1A", "Válida", "1000.00"),
                FilaCargoImportada(3, "NO-EXISTE", "Inválida", "500.00"),
            ]

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import NullPool

    from proptech_core.acceso.dominio.identidad import Identidad

    def conectar():  # type: ignore[no-untyped-def]
        con = api_edificio.base.conectar_app()
        con.autocommit = False
        return con

    engine = create_engine("postgresql+psycopg://", creator=conectar, poolclass=NullPool)
    try:
        with Session(engine) as sesion:
            sesion.execute(
                text("SELECT set_config('app.administracion_id', :id, true)"),
                {"id": str(api_edificio.admin)},
            )
            with pytest.raises(ImportacionInvalida) as error:
                cargos_particulares.importar_cargos_particulares(
                    sesion,
                    Identidad(api_edificio.admin, api_edificio.personas["super_admin"]),
                    complejo_id=api_edificio.edificio,
                    lector=_LectorFalso(),
                    contenido=b"",
                    periodo=__import__("datetime").date(2026, 10, 1),
                    request_id=uuid4(),
                )
            assert error.value.errores[0]["fila"] == 3
            sesion.rollback()
    finally:
        engine.dispose()
    assert api_edificio.filas("SELECT id FROM cargo_particular WHERE concepto = 'Válida'") == []


def _importar_por_sesion(api_edificio: ApiEdificio, filas: list) -> int:  # type: ignore[type-arg]
    """Mismo arnés que los tests 5.6/5.7: el caso de uso corre contra una
    sesión real, con un doble del puerto (D6: no conoce Excel)."""
    import datetime

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import NullPool

    from proptech_core.acceso.dominio.identidad import Identidad
    from proptech_core.gastos.aplicacion import cargos_particulares

    class _LectorFalso:
        def leer(self, contenido: bytes) -> list:  # type: ignore[type-arg]
            return filas

    def conectar():  # type: ignore[no-untyped-def]
        con = api_edificio.base.conectar_app()
        con.autocommit = False
        return con

    engine = create_engine("postgresql+psycopg://", creator=conectar, poolclass=NullPool)
    try:
        with Session(engine) as sesion:
            sesion.execute(
                text("SELECT set_config('app.administracion_id', :id, true)"),
                {"id": str(api_edificio.admin)},
            )
            cantidad = cargos_particulares.importar_cargos_particulares(
                sesion,
                Identidad(api_edificio.admin, api_edificio.personas["super_admin"]),
                complejo_id=api_edificio.edificio,
                lector=_LectorFalso(),
                contenido=b"",
                periodo=datetime.date(2026, 10, 1),
                request_id=uuid4(),
            )
            sesion.commit()
    finally:
        engine.dispose()
    return cantidad


def test_dos_filas_con_problemas_distintos_se_informan_las_dos(
    api_edificio: ApiEdificio,
) -> None:
    from proptech_core.gastos.aplicacion.errores import ImportacionInvalida
    from proptech_core.gastos.puertos import FilaCargoImportada

    filas = [
        FilaCargoImportada(2, "1A", "Válida", "1000.00"),
        FilaCargoImportada(3, None, "Sin unidad", "500.00"),
        FilaCargoImportada(4, "1B", "Importe raro", "10.001"),
        FilaCargoImportada(5, "1A", "Otra válida", "200.00"),
        FilaCargoImportada(6, "NO-EXISTE", "Unidad ajena", "300.00"),
    ]
    with pytest.raises(ImportacionInvalida) as error:
        _importar_por_sesion(api_edificio, filas)
    numeros = sorted(int(e["fila"]) for e in error.value.errores)  # type: ignore[call-overload]
    assert numeros == [3, 4, 6]


def test_importe_invalido_en_la_planilla_rechaza_entera(api_edificio: ApiEdificio) -> None:
    from proptech_core.gastos.aplicacion.errores import ImportacionInvalida
    from proptech_core.gastos.puertos import FilaCargoImportada

    for importe_malo in ("10.001", "0.00", "-5.00"):
        filas = [FilaCargoImportada(2, "1A", "Prueba", importe_malo)]
        with pytest.raises(ImportacionInvalida) as error:
            _importar_por_sesion(api_edificio, filas)
        assert error.value.errores[0]["fila"] == 2


def test_importados_quedan_en_borrador(api_edificio: ApiEdificio) -> None:
    from proptech_core.gastos.puertos import FilaCargoImportada

    cantidad = _importar_por_sesion(
        api_edificio, [FilaCargoImportada(2, "1A", "Importado", "100.00")]
    )
    assert cantidad == 1
    filas = api_edificio.filas("SELECT estado FROM cargo_particular WHERE concepto = 'Importado'")
    assert filas == [("borrador",)]


# --- 5.8: auditoría de la importación ---


def test_importacion_deja_una_sola_fila_de_auditoria_sin_importes(
    api_edificio: ApiEdificio,
) -> None:
    from proptech_core.gastos.puertos import FilaCargoImportada

    filas = [FilaCargoImportada(n, "1A", f"Cargo {n}", "100.00") for n in range(2, 32)]  # 30 filas
    _importar_por_sesion(api_edificio, filas)
    auditoria = api_edificio.filas(
        "SELECT detalle::text FROM auditoria WHERE accion = 'importar_cargos_particulares'"
    )
    assert len(auditoria) == 1
    assert "100.00" not in auditoria[0][0]
    assert '"cantidad": 30' in auditoria[0][0] or '"cantidad":30' in auditoria[0][0]


def test_importacion_rechazada_no_deja_fila_ni_cargos(api_edificio: ApiEdificio) -> None:
    from proptech_core.gastos.aplicacion.errores import ImportacionInvalida
    from proptech_core.gastos.puertos import FilaCargoImportada

    filas = [
        FilaCargoImportada(2, "1A", "Válida", "100.00"),
        FilaCargoImportada(3, "NO-EXISTE", "Inválida", "100.00"),
    ]
    with pytest.raises(ImportacionInvalida):
        _importar_por_sesion(api_edificio, filas)
    assert api_edificio.filas("SELECT id FROM cargo_particular WHERE concepto = 'Válida'") == []
    assert (
        api_edificio.filas("SELECT id FROM auditoria WHERE accion = 'importar_cargos_particulares'")
        == []
    )


# --- 5.9: no es un cargo negativo ---


def test_importe_negativo_rechazado(api_edificio: ApiEdificio) -> None:
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"),
        json=_datos(str(api_edificio.unidad), importe="-100.00"),
    )
    assert respuesta.status_code == 422, respuesta.text


def test_no_existe_ruta_de_credito_en_gastos(api_edificio: ApiEdificio) -> None:
    #: Estructural (L-016 no aplica: no hay forma de "observar otro
    #: resultado" en una ausencia, se verifica leyendo el router entero):
    #: ninguna ruta de `gastos.py`/`notas_de_credito`/`cargos_particulares`
    #: acredita plata a una unidad; la única ruta de crédito es la
    #: corrección del libro (4b).
    from proptech_core.gastos.aplicacion import cargos_particulares

    nombres = {nombre for nombre in dir(cargos_particulares) if not nombre.startswith("_")}
    assert not any("credit" in n.lower() or "acredit" in n.lower() for n in nombres)


# --- Intento 2 (rompedor F1): el detalle de un cargo exige el mismo permiso
# de lectura que su listado, no sólo alcanzar el edificio. ---


def _cargo_cargado(api_edificio: ApiEdificio) -> str:
    api_edificio.como("editar")
    alta = api_edificio.cliente.post(
        api_edificio.ruta("/cargos-particulares"), json=_datos(str(api_edificio.unidad))
    )
    assert alta.status_code == 201, alta.text
    return str(alta.json()["id"])


def test_vecino_del_edificio_no_lee_el_detalle_de_un_cargo(api_edificio: ApiEdificio) -> None:
    cargo_id = _cargo_cargado(api_edificio)
    api_edificio.como("vecino")
    listado = api_edificio.cliente.get(api_edificio.ruta("/cargos-particulares"))
    respuesta = api_edificio.cliente.get(f"/api/cargos-particulares/{cargo_id}")
    assert listado.status_code == 403, listado.text
    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["detail"].get("codigo") == "sin_permiso", respuesta.text
    assert respuesta.json()["detail"]["permiso_faltante"] == "ver_configuracion_del_edificio"
    api_edificio.como("super_admin")


@pytest.mark.parametrize("perfil", ["editar", "ver", "consejo", "contador"])
def test_quien_lista_cargos_tambien_lee_su_detalle(api_edificio: ApiEdificio, perfil: str) -> None:
    cargo_id = _cargo_cargado(api_edificio)
    api_edificio.como(perfil)
    respuesta = api_edificio.cliente.get(f"/api/cargos-particulares/{cargo_id}")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["id"] == cargo_id
    api_edificio.como("super_admin")
