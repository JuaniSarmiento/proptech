"""Ayudas de la aceptación de H-007 (plantilla y padrón, change 5). Caja negra: todo pasa por la API
real (`POST /api/complejos/{id}/importaciones`, `GET .../importaciones/plantilla`) con la identidad
inyectada, y se mira el resultado con lecturas SQL como `proptech_app` con el tenant fijado.

Los archivos Excel se generan acá con `openpyxl` (datos inventados). Lo que todavía no existe en el
código (la ruta, la tabla `importacion`) se pide con un `assert` y un mensaje, nunca con un error de
setup.

Base de los ejemplos (HISTORIAS.md, "Importación desde Excel"): "Torre Ficticia" con 3 pisos y 1
subsuelo (pisos `SS1`, `PB`, `1`, `2`, `3`), migración el 15/10/2026, 12 unidades cuyos coeficientes
suman 1.
"""

from __future__ import annotations

import io
import re
import threading
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import text

from .._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIGRACION = "2026-10-15"
ARCHIVO = "padron-torre-ficticia.xlsx"
ENCABEZADOS = ["Unidad", "Tipo", "Piso", "Coeficiente", "Superficie m2", "Propietario", "Email"]
#: Ruta del parámetros del repo (la misma que usa la fixture `api_edificio`).
_PARAMETROS = Path(__file__).resolve().parents[4] / "config" / "parametros.yaml"


# --- La plantilla ---------------------------------------------------------------------------------


def filas_validas() -> list[dict[str, Any]]:
    """Las 12 unidades de la Torre Ficticia, en el orden de la plantilla.

    Fila del Excel = índice + 2
    (el encabezado es la fila 1). La fila 4 es `2B` (escenario "Unidad repetida")."""
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
    filas = []
    for n, (unidad, tipo, piso) in enumerate(datos):
        con_propietario = n < 10
        filas.append(
            {
                "Unidad": unidad,
                "Tipo": tipo,
                "Piso": piso,
                # 11 x 0,083333 + 0,083337 = 1 exacto.
                "Coeficiente": "0.083337" if n == 11 else "0.083333",
                "Superficie m2": f"{50 + n}.25",
                "Propietario": f"Persona Ficticia {n + 1}" if con_propietario else None,
                "Email": f"propietario{n + 1}@ficticio.test" if con_propietario else None,
            }
        )
    return filas


def fila_del_excel(unidad: str, filas: list[dict[str, Any]] | None = None) -> int:
    filas = filas or filas_validas()
    return next(n + 2 for n, f in enumerate(filas) if f["Unidad"] == unidad)


def libro(hojas: dict[str, list[list[Any]]]) -> bytes:
    """Un `.xlsx` con las hojas en ese orden; cada hoja es una lista de filas.

    La primera fila de cada hoja es el encabezado."""
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


def hoja_unidades(
    filas: list[dict[str, Any]] | None = None, encabezados: list[str] | None = None
) -> list[list[Any]]:
    filas = filas_validas() if filas is None else filas
    encabezados = encabezados or ENCABEZADOS
    return [list(encabezados), *[[f.get(c) for c in encabezados] for f in filas]]


def padron(
    filas: list[dict[str, Any]] | None = None,
    *,
    encabezados: list[str] | None = None,
    nombre_de_hoja: str = "Unidades",
    extra: dict[str, list[list[Any]]] | None = None,
) -> bytes:
    return libro({nombre_de_hoja: hoja_unidades(filas, encabezados), **(extra or {})})


def con_formula(
    contenido: bytes, celda: str, formula: str, cache: str | None, hoja: int = 1
) -> bytes:
    """Reemplaza la celda `celda` de la hoja `hoja` por una fórmula, con o sin valor en caché.
    `openpyxl` nunca guarda el valor en caché: el XML se edita a mano."""
    entrada = zipfile.ZipFile(io.BytesIO(contenido))
    ruta = f"xl/worksheets/sheet{hoja}.xml"
    xml = entrada.read(ruta).decode()
    nueva = (
        f'<c r="{celda}"><f>{formula}</f>'
        + (f"<v>{cache}</v>" if cache is not None else "")
        + "</c>"
    )
    xml, cambios = re.subn(rf'<c r="{celda}"[^>]*?(?:/>|>.*?</c>)', nueva, xml, count=1, flags=re.S)
    assert cambios == 1, f"no encontré la celda {celda} para poner la fórmula"
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as nuevo:
        for item in entrada.infolist():
            nuevo.writestr(item, xml if item.filename == ruta else entrada.read(item.filename))
    return salida.getvalue()


# --- El mundo -------------------------------------------------------------------------------------


@dataclass
class Mundo:
    app: FastAPI
    cliente: TestClient
    base: BaseDeEdificio
    admin: UUID
    admin_b: UUID
    torre: UUID
    """Torre Ficticia: 3 pisos y 1 subsuelo, sin unidades, migración pendiente."""
    con_padron: UUID
    """Edificio de 3 pisos y 1 subsuelo con dos unidades (`1A`, `1B`), migración pendiente."""
    sin_pisos: UUID
    """Edificio sin pisos ni subsuelos configurados."""
    edificio_b: UUID
    """Edificio de la administración B."""
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


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch) -> Iterator[Mundo]:
    from proptech_api.app import crear_app
    from proptech_core.acceso.dominio.identidad import Identidad
    from proptech_core.compartido.base_de_datos import abrir_sesion
    from proptech_core.compartido.georef import leer_georef
    from proptech_core.compartido.parametros import leer_parametros
    from proptech_core.complejos.aplicacion.escritura import crear_edificio

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
    with TestClient(app) as cliente:
        with abrir_sesion(app.state.fabrica_de_sesiones, admin) as sesion:
            sesion.execute(
                text(
                    "INSERT INTO administracion (id, nombre) "
                    "VALUES (:id, 'Administración Ficticia')"
                ),
                {"id": admin},
            )
            for persona in personas.values():
                sesion.execute(
                    text(
                        "INSERT INTO persona (id, administracion_id, nombre) "
                        "VALUES (:id, :admin, 'Persona del equipo ficticia')"
                    ),
                    {"id": persona, "admin": admin},
                )
            identidad = Identidad(admin, personas["super_admin"])
            parametros = leer_parametros(str(_PARAMETROS))
            georef = leer_georef(str(_PARAMETROS.parent / "georef"))
            torre, con_padron = (
                crear_edificio(
                    sesion,
                    identidad,
                    nombre=nombre,
                    provincia_id="50",
                    departamento_id="50007",
                    localidad_id="50007010",
                    georef=georef,
                    pisos=3,
                    subsuelos=1,
                    parametros=parametros,
                    reloj=lambda: datetime.now(UTC),
                    request_id=uuid4(),
                )
                for nombre in ("Torre Ficticia", "Edificio Ficticio con padrón")
            )
            sin_pisos = uuid4()
            sesion.execute(
                text(
                    "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                    "VALUES (:id, :admin, 'Edificio Ficticio sin pisos', 'Mendoza')"
                ),
                {"id": sin_pisos, "admin": admin},
            )
            sesion.commit()
        with base_del_edificio.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin)
            u1 = insertar_unidad(conexion, admin, con_padron, "1A", coeficiente="0.500000")
            u2 = insertar_unidad(conexion, admin, con_padron, "1B", coeficiente="0.500000")
            asignaciones = {
                "super_admin": ("super_admin", None, None, None),
                "admin_principal": ("administrador", None, None, None),
                "admin_del_edificio": ("administrador", con_padron, None, None),
                "admin_de_otro_edificio": ("administrador", torre, None, None),
                "contador": ("contador", None, None, None),
                "auxiliar": ("auxiliar", con_padron, None, None),
                "consejo": ("consejo", con_padron, None, None),
                "vecino_propietario": ("vecino", con_padron, u1, "propietario"),
                "vecino_inquilino": ("vecino", con_padron, u2, "inquilino"),
            }
            for rol, (nombre_rol, complejo, unidad, vinculo) in asignaciones.items():
                conexion.execute(
                    "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id, "
                    "unidad_id, vinculo) VALUES (%s, %s, %s, %s, %s, %s)",
                    (admin, personas[rol], nombre_rol, complejo, unidad, vinculo),
                )
        with base_del_edificio.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin_b)
            edificio_b = uuid4()
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
        m = Mundo(
            app=app,
            cliente=cliente,
            base=base_del_edificio,
            admin=admin,
            admin_b=admin_b,
            torre=torre,
            con_padron=con_padron,
            sin_pisos=sin_pisos,
            edificio_b=edificio_b,
            personas=personas,
            persona_b=persona_b,
        )
        m.como("super_admin")
        try:
            yield m
        finally:
            app.dependency_overrides.clear()


# --- La API ---------------------------------------------------------------------------------------


def importar(
    m: Mundo,
    complejo: UUID,
    contenido: bytes,
    *,
    nombre: str = ARCHIVO,
    fecha: str | None = MIGRACION,
    tipo: str = XLSX,
    cliente: TestClient | None = None,
) -> Any:
    datos = {} if fecha is None else {"fecha_de_migracion": fecha}
    return (cliente or m.cliente).post(
        f"/api/complejos/{complejo}/importaciones",
        files={"archivo": (nombre, contenido, tipo)},
        data=datos,
    )


def aceptada(respuesta: Any) -> dict[str, Any]:
    assert respuesta.status_code == 201, (
        f"se esperaba 201 (importación aceptada), llegó {respuesta.status_code}: "
        f"{respuesta.text[:400]}"
    )
    cuerpo = respuesta.json()
    for clave in (
        "importacion_id",
        "unidades_creadas",
        "propietarios_creados",
        "propietarios_reusados",
        "filas_de_saldo",
        "advertencias",
    ):
        assert clave in cuerpo, f"la respuesta no trae `{clave}`: {cuerpo}"
    return dict(cuerpo)


@dataclass(frozen=True)
class Error:
    hoja: str | None
    fila: int | None
    columna: str | None
    motivo: str


def errores(respuesta: Any) -> list[Error]:
    """El informe del 422: `{"detail": [{"hoja", "fila", "columna", "motivo"}]}`."""
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


def de_fila(lista: list[Error]) -> list[tuple[str | None, int, str | None]]:
    return sorted((e.hoja, e.fila, e.columna) for e in lista if e.fila is not None)


def conflicto(respuesta: Any, campo: str) -> dict[str, Any]:
    assert respuesta.status_code == 409, (
        f"se esperaba 409 en `{campo}`, llegó {respuesta.status_code}: {respuesta.text[:400]}"
    )
    cuerpo = respuesta.json()
    assert cuerpo.get("campo") == campo, f"se esperaba conflicto en `{campo}`: {cuerpo}"
    return dict(cuerpo)


# --- Lo que quedó en la base ----------------------------------------------------------------------


def hay_importacion(m: Mundo) -> bool:
    return bool(m.uno("SELECT to_regclass('importacion') IS NOT NULL"))


def conteos(m: Mundo) -> dict[str, int]:
    """Todo lo que importar podría escribir en la administración A."""
    c = {
        "unidad": m.uno("SELECT count(*) FROM unidad"),
        "persona": m.uno("SELECT count(*) FROM persona"),
        "asignacion_vecino": m.uno("SELECT count(*) FROM asignacion_rol WHERE rol = 'vecino'"),
        "auditoria": m.uno("SELECT count(*) FROM auditoria"),
        "invitacion": m.uno("SELECT count(*) FROM invitacion"),
    }
    c["importacion"] = m.uno("SELECT count(*) FROM importacion") if hay_importacion(m) else 0
    return c


def unidades(m: Mundo, complejo: UUID) -> dict[str, dict[str, str]]:
    filas = m.filas(
        "SELECT identificador, tipo, piso, coeficiente::text, superficie_m2::text FROM unidad "
        "WHERE complejo_id = %s",
        (complejo,),
    )
    return {
        f[0]: {"tipo": f[1], "piso": f[2], "coeficiente": f[3], "superficie": f[4]} for f in filas
    }


def propietarios(m: Mundo, complejo: UUID) -> dict[str, tuple[str, str | None]]:
    """Unidad → (nombre, email) de su propietario."""
    filas = m.filas(
        "SELECT u.identificador, p.nombre, p.email FROM asignacion_rol a "
        "JOIN unidad u ON u.id = a.unidad_id JOIN persona p ON p.id = a.persona_id "
        "WHERE a.rol = 'vecino' AND a.vinculo = 'propietario' AND u.complejo_id = %s",
        (complejo,),
    )
    return {f[0]: (f[1], f[2]) for f in filas}


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
