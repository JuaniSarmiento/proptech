"""Ayudas de la aceptación de H-009 (confirmar saldos, change 5).

Caja negra: todo pasa por la API real (`POST /api/complejos/{id}/importaciones` de H-007, `GET
.../importaciones/comparacion` y `POST .../importaciones/aceptacion-de-diferencias` de H-008, y
`POST .../importaciones/confirmacion` de H-009) con la identidad inyectada, y se mira el resultado
con lecturas SQL como `proptech_app` con el tenant fijado. La emisión de noviembre (C05) usa el
caso de uso real `registrar_emision` del libro.

Los archivos Excel se generan acá con `openpyxl` (datos inventados). Lo que todavía no existe en el
código (la ruta de confirmar, la acción nueva) se pide con un `assert` y un mensaje, nunca con un
error de setup.

Base de los ejemplos (la de H-008): "Edificio Ficticio de Saldos", 3 pisos y 1 subsuelo, con el
padrón ya cargado (`1A`, `1B`, `2A`, `2B`, `3C`, `4D`, `5E`), migración el 15/10/2026. Hoja
`Saldos`:

- `1A`: fila 2, agosto ordinaria $80.000, vence 10/08, $4.000 de interés; fila 3, septiembre
  ordinaria $85.000, vence 10/09.
- `1B`: fila 4, septiembre ordinaria $85.000; fila 5, septiembre extraordinaria $20.000 (vencen
  10/09).
- `2A`: fila 6, total único $50.000 con $2.000 de interés.
- `2B`: fila 7, crédito de $3.000.
- `4D`: fila 8, crédito de $3.000.

Totales del borrador: capital $320.000 (165.000 + 105.000 + 50.000), interés importado $6.000,
crédito $6.000. El control coincide unidad por unidad (sin diferencias).
"""

from __future__ import annotations

import io
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook

from .._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIGRACION = "2026-10-15"
ARCHIVO = "saldos-octubre.xlsx"
ENC_SALDOS = ["Unidad", "Período", "Vencimiento", "Concepto", "Importe", "Interés acumulado"]
ENC_CONTROL = ["Unidad", "Saldo según el administrador"]
UNIDADES = ("1A", "1B", "2A", "2B", "3C", "4D", "5E")
AVISO = "El primer interés del sistema cubre octubre de 2026"
ACCION_ACEPTAR = "aceptar_diferencias_de_saldos"
ACCION = "confirmar_saldos_iniciales"
PROPORCIONAL, MES_ENTERO = "proporcional_por_dia", "mes_entero"


# --- La plantilla ---------------------------------------------------------------------------------


def saldos_base() -> list[list[Any]]:
    """Las filas de `Saldos` de la base (sin encabezado). Fila del Excel = índice + 2."""
    return [
        ["1A", "2026-08", date(2026, 8, 10), "Ordinaria", "80000.00", "4000.00"],
        ["1A", "2026-09", date(2026, 9, 10), "Ordinaria", "85000.00", None],
        ["1B", "2026-09", date(2026, 9, 10), "Ordinaria", "85000.00", None],
        ["1B", "2026-09", date(2026, 9, 10), "Extraordinaria", "20000.00", None],
        ["2A", None, None, None, "50000.00", "2000.00"],
        ["2B", None, None, None, "-3000.00", None],
        ["4D", None, None, None, "-3000.00", None],
    ]


def control_base() -> list[list[Any]]:
    """Las filas de `Control` de la base (sin encabezado), sin diferencias."""
    return [
        ["1A", "169000.00"],
        ["1B", "105000.00"],
        ["2A", "52000.00"],
        ["2B", "-3000.00"],
        ["4D", "-3000.00"],
    ]


def libro(hojas: dict[str, list[list[Any]]]) -> bytes:
    """Un `.xlsx` con las hojas en ese orden; cada hoja es una lista de filas (la primera, el
    encabezado)."""
    wb = Workbook()
    for hoja_inicial in list(wb.worksheets):
        wb.remove(hoja_inicial)
    for nombre, filas in hojas.items():
        hoja = wb.create_sheet(nombre)
        for fila in filas:
            hoja.append(list(fila))
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


def archivo(
    saldos: list[list[Any]] | None = None,
    control: list[list[Any]] | None = None,
    *,
    enc_saldos: list[str] | None = None,
    enc_control: list[str] | None = None,
    sin_control: bool = False,
    extra: dict[str, list[list[Any]]] | None = None,
) -> bytes:
    """Un archivo de saldos para el edificio con padrón: sin hoja `Unidades` (E7 del 5)."""
    hojas: dict[str, list[list[Any]]] = {
        "Saldos": [list(enc_saldos or ENC_SALDOS), *(saldos_base() if saldos is None else saldos)]
    }
    if not sin_control:
        hojas["Control"] = [
            list(enc_control or ENC_CONTROL),
            *(control_base() if control is None else control),
        ]
    hojas.update(extra or {})
    return libro(hojas)


# --- El mundo -------------------------------------------------------------------------------------


@dataclass
class Mundo:
    app: FastAPI
    cliente: TestClient
    base: BaseDeEdificio
    admin: UUID
    admin_b: UUID
    edificio: UUID
    """Edificio Ficticio de Saldos: padrón cargado (siete unidades), migración pendiente."""
    otro: UUID
    """Otro edificio de la misma administración (el del administrador de otro edificio)."""
    edificio_b: UUID
    """Edificio de la administración B."""
    unidades: dict[str, UUID] = field(default_factory=dict)
    personas: dict[str, UUID] = field(default_factory=dict)
    persona_b: UUID = field(default_factory=uuid4)

    def como(self, rol: str) -> None:
        from proptech_api.acceso import identidad_actual
        from proptech_core.acceso.dominio.identidad import Identidad

        if rol == "administracion_b":
            identidad = Identidad(self.admin_b, self.persona_b)
        else:
            identidad = Identidad(self.admin, self.personas[rol])
        self.app.dependency_overrides[identidad_actual] = lambda: identidad

    def sin_sesion(self) -> None:
        from proptech_api.acceso import identidad_actual

        self.app.dependency_overrides.pop(identidad_actual, None)

    def filas(
        self, consulta: str, parametros: tuple[Any, ...] = (), admin: UUID | None = None
    ) -> list[Any]:
        with self.base.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin or self.admin)
            return list(conexion.execute(consulta, parametros).fetchall())

    def uno(
        self, consulta: str, parametros: tuple[Any, ...] = (), admin: UUID | None = None
    ) -> Any:
        return self.filas(consulta, parametros, admin)[0][0]

    def ejecutar(self, consulta: str, parametros: tuple[Any, ...] = ()) -> None:
        with self.base.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, self.admin)
            conexion.execute(consulta, parametros)


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch) -> Iterator[Mundo]:
    from proptech_api.app import crear_app

    from ...conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION

    for clave, valor in base_del_edificio.entorno.items():
        if clave in {"POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB"}:
            monkeypatch.setenv(clave, valor)
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER_DE_SESION)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD_DE_SESION)
    app = crear_app()
    admin, admin_b = uuid4(), uuid4()
    roles = (
        "super_admin",
        "admin_principal",
        "admin_del_edificio",
        "admin_de_otro_edificio",
        "contador",
        "auxiliar",
        "consejo",
        "vecino_propietario",
        "vecino_inquilino",
    )
    personas = {rol: uuid4() for rol in roles}
    persona_b = uuid4()
    edificio, otro, edificio_b = uuid4(), uuid4(), uuid4()
    with TestClient(app) as cliente:
        with base_del_edificio.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin)
            conexion.execute(
                "INSERT INTO administracion (id, nombre) VALUES (%s, 'Administración Ficticia')",
                (admin,),
            )
            for persona in personas.values():
                conexion.execute(
                    "INSERT INTO persona (id, administracion_id, nombre) "
                    "VALUES (%s, %s, 'Persona del equipo ficticia')",
                    (persona, admin),
                )
            for complejo, nombre in (
                (edificio, "Edificio Ficticio de Saldos"),
                (otro, "Otro Edificio Ficticio"),
            ):
                conexion.execute(
                    "INSERT INTO complejo (id, administracion_id, nombre, localidad, pisos, "
                    "subsuelos) VALUES (%s, %s, %s, 'Mendoza', 3, 1)",
                    (complejo, admin, nombre),
                )
            ids = {}
            for n, identificador in enumerate(UNIDADES):
                coeficiente = "0.142858" if n == len(UNIDADES) - 1 else "0.142857"
                ids[identificador] = insertar_unidad(
                    conexion, admin, edificio, identificador, coeficiente=coeficiente
                )
            insertar_unidad(conexion, admin, otro, "9A", coeficiente="1.000000")
            asignaciones = {
                "super_admin": ("super_admin", None, None, None),
                "admin_principal": ("administrador", None, None, None),
                "admin_del_edificio": ("administrador", edificio, None, None),
                "admin_de_otro_edificio": ("administrador", otro, None, None),
                "contador": ("contador", None, None, None),
                "auxiliar": ("auxiliar", edificio, None, None),
                "consejo": ("consejo", edificio, None, None),
                "vecino_propietario": ("vecino", edificio, ids["1A"], "propietario"),
                "vecino_inquilino": ("vecino", edificio, ids["1B"], "inquilino"),
            }
            for rol, (nombre_rol, complejo, unidad, vinculo) in asignaciones.items():
                conexion.execute(
                    "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id, "
                    "unidad_id, vinculo) VALUES (%s, %s, %s, %s, %s, %s)",
                    (admin, personas[rol], nombre_rol, complejo, unidad, vinculo),
                )
        with base_del_edificio.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin_b)
            conexion.execute(
                "INSERT INTO administracion (id, nombre) "
                "VALUES (%s, 'Otra administración ficticia')",
                (admin_b,),
            )
            conexion.execute(
                "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'Persona B')",
                (persona_b, admin_b),
            )
            conexion.execute(
                "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
                "VALUES (%s, %s, 'super_admin')",
                (admin_b, persona_b),
            )
            conexion.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad, pisos, subsuelos) "
                "VALUES (%s, %s, 'Edificio B ficticio', 'Mendoza', 3, 1)",
                (edificio_b, admin_b),
            )
            insertar_unidad(conexion, admin_b, edificio_b, "1A", coeficiente="1.000000")
        m = Mundo(
            app=app,
            cliente=cliente,
            base=base_del_edificio,
            admin=admin,
            admin_b=admin_b,
            edificio=edificio,
            otro=otro,
            edificio_b=edificio_b,
            unidades=ids,
            personas=personas,
            persona_b=persona_b,
        )
        m.como("super_admin")
        try:
            yield m
        finally:
            app.dependency_overrides.clear()


def configurar(m: Mundo, forma: str, *, desde: date = date(2026, 1, 1)) -> None:
    """Una versión de configuración del edificio vigente a la fecha de migración."""
    m.ejecutar(
        "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, "
        "vigente_desde, tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, "
        "porcentaje_fondo, dia_de_vencimiento, modalidad_de_vencimiento) "
        "VALUES (%s, %s, %s, %s, '3.00', '500.00', 0, %s, '0.00', 10, 'unico')",
        (m.admin, m.edificio, m.personas["super_admin"], desde, forma),
    )


# --- La API ---------------------------------------------------------------------------------------


def importar(
    m: Mundo,
    contenido: bytes,
    *,
    complejo: UUID | None = None,
    nombre: str = ARCHIVO,
    fecha: str = MIGRACION,
) -> Any:
    return m.cliente.post(
        f"/api/complejos/{complejo or m.edificio}/importaciones",
        files={"archivo": (nombre, contenido, XLSX)},
        data={"fecha_de_migracion": fecha},
    )


def aceptada(respuesta: Any) -> dict[str, Any]:
    assert respuesta.status_code == 201, (
        f"se esperaba 201 (importación aceptada), llegó {respuesta.status_code}: "
        f"{respuesta.text[:400]}"
    )
    cuerpo = respuesta.json()
    assert "importacion_id" in cuerpo and "filas_de_saldo" in cuerpo, (
        f"la respuesta no trae importacion_id y filas_de_saldo: {cuerpo}"
    )
    return dict(cuerpo)


def subir(m: Mundo, contenido: bytes | None = None) -> dict[str, Any]:
    return aceptada(importar(m, archivo() if contenido is None else contenido))


@dataclass(frozen=True)
class Error:
    hoja: str | None
    fila: int | None
    columna: str | None
    motivo: str


def errores(respuesta: Any) -> list[Error]:
    """El informe del 422 (contrato de H-007):
    `{"detail": [{"hoja", "fila", "columna", "motivo"}]}`."""
    assert respuesta.status_code == 422, (
        f"se esperaba 422 (archivo rechazado), llegó {respuesta.status_code}: "
        f"{respuesta.text[:400]}"
    )
    detalle = respuesta.json().get("detail")
    assert isinstance(detalle, list) and detalle, (
        f"el 422 no trae una lista de errores: {respuesta.text[:400]}"
    )
    lista = []
    for item in detalle:
        assert isinstance(item, dict) and {"hoja", "fila", "columna", "motivo"} <= set(item), (
            f"cada error lleva hoja, fila, columna y motivo: {item}"
        )
        lista.append(Error(item["hoja"], item["fila"], item["columna"], str(item["motivo"])))
    return lista


def ubicaciones(lista: list[Error]) -> set[tuple[str | None, int | None, str | None]]:
    return {(e.hoja, e.fila, e.columna) for e in lista}


def conflicto(respuesta: Any, campo: str) -> dict[str, Any]:
    assert respuesta.status_code == 409, (
        f"se esperaba 409 en `{campo}`, llegó {respuesta.status_code}: {respuesta.text[:400]}"
    )
    cuerpo = respuesta.json()
    assert cuerpo.get("campo") == campo, f"se esperaba conflicto en `{campo}`: {cuerpo}"
    return dict(cuerpo)


def comparacion(m: Mundo, complejo: UUID | None = None) -> dict[str, Any]:
    respuesta = m.cliente.get(f"/api/complejos/{complejo or m.edificio}/importaciones/comparacion")
    assert respuesta.status_code == 200, (
        f"se esperaba 200 de la comparación, llegó {respuesta.status_code}: {respuesta.text[:400]}"
    )
    cuerpo = respuesta.json()
    for clave in (
        "importacion_id",
        "unidades",
        "total_borrador",
        "total_control",
        "unidades_con_diferencia",
        "requiere_aceptacion",
        "aceptacion",
    ):
        assert clave in cuerpo, f"la comparación no trae `{clave}`: {cuerpo}"
    for u in cuerpo["unidades"]:
        assert {"unidad", "unidad_id", "borrador", "control", "diferencia", "aviso"} <= set(u), (
            f"cada unidad de la comparación lleva unidad, unidad_id, borrador, control, "
            f"diferencia y aviso: {u}"
        )
    return dict(cuerpo)


def por_unidad(c: dict[str, Any]) -> dict[str, tuple[str, str, str]]:
    """Unidad → (borrador, control, diferencia), como texto."""
    return {u["unidad"]: (u["borrador"], u["control"], u["diferencia"]) for u in c["unidades"]}


def avisos(c: dict[str, Any]) -> dict[str, str | None]:
    return {u["unidad"]: u["aviso"] for u in c["unidades"]}


def aceptar(m: Mundo, importacion_id: str, complejo: UUID | None = None) -> Any:
    return m.cliente.post(
        f"/api/complejos/{complejo or m.edificio}/importaciones/aceptacion-de-diferencias",
        json={"importacion_id": importacion_id},
    )


def aceptacion_creada(respuesta: Any) -> dict[str, Any]:
    assert respuesta.status_code == 201, (
        f"se esperaba 201 (diferencias aceptadas), llegó {respuesta.status_code}: "
        f"{respuesta.text[:400]}"
    )
    cuerpo = respuesta.json()
    for clave in ("aceptacion_id", "diferencias", "aceptada_por", "aceptada_en"):
        assert clave in cuerpo, f"la aceptación no trae `{clave}`: {cuerpo}"
    return dict(cuerpo)


def diferencias(lista: list[dict[str, Any]]) -> set[tuple[str, str, str, str]]:
    return {(d["unidad"], d["borrador"], d["control"], d["diferencia"]) for d in lista}


# --- Lo que quedó en la base ----------------------------------------------------------------------

TABLAS_0037 = ("fila_de_saldo_importada", "control_de_saldo", "aceptacion_de_diferencias")
TABLAS_DEL_LIBRO = ("carga_de_saldo_inicial", "origen_de_saldo_inicial")


def existe(m: Mundo, tabla: str) -> bool:
    return bool(m.uno("SELECT to_regclass(%s) IS NOT NULL", (tabla,)))


def exigir_tablas(m: Mundo) -> None:
    for tabla in TABLAS_0037:
        assert existe(m, tabla), f"falta la tabla {tabla} (0037)"


def conteos(m: Mundo) -> dict[str, Any]:
    """Todo lo que importar, aceptar o confirmar podría escribir en la administración A, más el
    estado de migración del edificio y los estados de sus importaciones."""
    c = {
        "unidad": m.uno("SELECT count(*) FROM unidad"),
        "auditoria": m.uno("SELECT count(*) FROM auditoria"),
        "cuenta": m.uno("SELECT count(*) FROM cuenta"),
        "obligacion": m.uno("SELECT count(*) FROM obligacion"),
        "movimiento": m.uno("SELECT count(*) FROM movimiento"),
    }
    for tabla in ("importacion", *TABLAS_0037, *TABLAS_DEL_LIBRO):
        c[tabla] = m.uno(f"SELECT count(*) FROM {tabla}") if existe(m, tabla) else 0  # noqa: S608
    c["estado_migracion"] = m.uno(
        "SELECT estado_migracion FROM complejo WHERE id = %s", (m.edificio,)
    )
    c["estados_de_importacion"] = (
        sorted(str(f[0]) for f in m.filas("SELECT estado FROM importacion"))
        if existe(m, "importacion")
        else []
    )
    return c


def libro_del_edificio(m: Mundo) -> tuple[int, int, int]:
    """Cuentas, obligaciones y movimientos del edificio de saldos."""
    return (
        m.uno("SELECT count(*) FROM cuenta WHERE complejo_id = %s", (m.edificio,)),
        m.uno("SELECT count(*) FROM obligacion WHERE complejo_id = %s", (m.edificio,)),
        m.uno("SELECT count(*) FROM movimiento WHERE complejo_id = %s", (m.edificio,)),
    )


def filas_del_borrador(m: Mundo, importacion_id: str) -> list[tuple[Any, ...]]:
    """(unidad, fila, tipo, período, vencimiento, concepto, importe, interés) de cada fila del
    borrador."""
    assert existe(m, "fila_de_saldo_importada"), "falta la tabla fila_de_saldo_importada (0037)"
    return sorted(
        m.filas(
            "SELECT u.identificador, f.fila, f.tipo, f.periodo, f.vencimiento, f.concepto, "
            "f.importe::text, f.interes_acumulado::text FROM fila_de_saldo_importada f "
            "JOIN unidad u ON u.id = f.unidad_id WHERE f.importacion_id = %s",
            (importacion_id,),
        )
    )


def estado_de(m: Mundo, importacion_id: str) -> str:
    return str(m.uno("SELECT estado FROM importacion WHERE id = %s", (importacion_id,)))


def auditorias(m: Mundo, accion: str) -> int:
    return int(m.uno("SELECT count(*) FROM auditoria WHERE accion = %s", (accion,)))


def en_paralelo(*funciones: Any) -> list[Any]:
    """Corre las funciones a la vez (con una barrera) y devuelve sus resultados o excepciones."""
    barrera = threading.Barrier(len(funciones))
    resultados: list[Any] = [None] * len(funciones)

    def correr(i: int, f: Any) -> None:
        barrera.wait()
        try:
            resultados[i] = f()
        except BaseException as error:
            resultados[i] = error

    hilos = [
        threading.Thread(target=correr, args=(i, f), daemon=True) for i, f in enumerate(funciones)
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=120)
    return resultados


# --- H-009 · confirmar ----------------------------------------------------------------------------


def saldos_de_la_spec() -> tuple[list[list[Any]], list[list[Any]]]:
    """El archivo del escenario "La suma importada coincide con el archivo" de la spec: capital
    $215.300, interés $6.000 y crédito $3.000."""
    saldos = [
        ["1A", "2026-08", date(2026, 8, 10), "Ordinaria", "80000.00", "4000.00"],
        ["1A", "2026-09", date(2026, 9, 10), "Ordinaria", "85000.00", None],
        ["2A", None, None, None, "50000.00", "2000.00"],
        ["2B", None, None, None, "-3000.00", None],
        ["4D", "2026-09", date(2026, 9, 10), "Ordinaria", "300.00", None],
    ]
    control = [["1A", "169000.00"], ["2A", "52000.00"], ["2B", "-3000.00"], ["4D", "300.00"]]
    return saldos, control


def confirmar(m: Mundo, importacion_id: str, complejo: UUID | None = None) -> Any:
    return m.cliente.post(
        f"/api/complejos/{complejo or m.edificio}/importaciones/confirmacion",
        json={"importacion_id": importacion_id},
    )


def confirmacion_creada(respuesta: Any) -> dict[str, Any]:
    assert respuesta.status_code == 201, (
        f"se esperaba 201 (saldos confirmados), llegó {respuesta.status_code}: "
        f"{respuesta.text[:400]}"
    )
    cuerpo = respuesta.json()
    for clave in (
        "importacion_id",
        "carga_id",
        "estado_migracion",
        "totales",
        "confirmada_por",
        "confirmada_en",
    ):
        assert clave in cuerpo, f"la confirmación no trae `{clave}`: {cuerpo}"
    for clave in ("capital", "interes_importado", "credito"):
        assert clave in cuerpo["totales"], f"los totales no traen `{clave}`: {cuerpo['totales']}"
    return dict(cuerpo)


def sin_saldos_previos(m: Mundo, complejo: UUID | None = None) -> Any:
    return m.cliente.post(
        f"/api/complejos/{complejo or m.edificio}/estado-de-migracion/sin-saldos-previos"
    )


def estado_del_edificio(m: Mundo, complejo: UUID | None = None) -> str:
    return str(
        m.uno("SELECT estado_migracion FROM complejo WHERE id = %s", (complejo or m.edificio,))
    )


def cargas(m: Mundo, complejo: UUID | None = None) -> list[Any]:
    """(id, operacion_id, origen, archivo, fecha_de_migracion) de cada carga de saldo inicial."""
    return m.filas(
        "SELECT id, operacion_id, origen, archivo, fecha_de_migracion FROM carga_de_saldo_inicial "
        "WHERE complejo_id = %s",
        (complejo or m.edificio,),
    )


def obligaciones_de(m: Mundo, unidad: str) -> dict[date, tuple[str, str, str, date]]:
    """Período → (ordinaria, fondo, extraordinaria, vencimiento) de las obligaciones de la
    unidad."""
    filas = m.filas(
        "SELECT o.periodo, o.ordinaria::text, o.fondo_de_reserva::text, o.extraordinaria::text, "
        "o.vencimiento FROM obligacion o JOIN cuenta c ON c.id = o.cuenta_id "
        "WHERE c.unidad_id = %s",
        (m.unidades[unidad],),
    )
    return {f[0]: (f[1], f[2], f[3], f[4]) for f in filas}


def movimientos_de(m: Mundo, unidad: str) -> list[tuple[str, str, str, date | None]]:
    """(tipo, sentido, importe, corte) de los movimientos de la cuenta de la unidad."""
    return sorted(
        m.filas(
            "SELECT mv.tipo, mv.sentido, mv.importe::text, mv.corte FROM movimiento mv "
            "JOIN cuenta c ON c.id = mv.cuenta_id WHERE c.unidad_id = %s",
            (m.unidades[unidad],),
        ),
        key=lambda f: (f[0], f[1], f[2]),
    )


def origenes(m: Mundo) -> set[tuple[str, int, str, date | None]]:
    """(unidad, fila del Excel, qué formó, período) de cada fila de origen de la carga del edificio:
    "obligacion", o el tipo del movimiento ("interes", "saldo_inicial")."""
    filas = m.filas(
        "SELECT u.identificador, o.fila, "
        "CASE WHEN o.obligacion_id IS NOT NULL THEN 'obligacion' ELSE mv.tipo END, "
        "COALESCE(ob.periodo, obm.periodo) "
        "FROM origen_de_saldo_inicial o JOIN cuenta c ON c.id = o.cuenta_id "
        "JOIN unidad u ON u.id = c.unidad_id "
        "LEFT JOIN obligacion ob ON ob.id = o.obligacion_id "
        "LEFT JOIN movimiento mv ON mv.id = o.movimiento_id "
        "LEFT JOIN obligacion obm ON obm.id = mv.obligacion_id "
        "WHERE o.complejo_id = %s",
        (m.edificio,),
    )
    return {(f[0], int(f[1]), str(f[2]), f[3]) for f in filas}
