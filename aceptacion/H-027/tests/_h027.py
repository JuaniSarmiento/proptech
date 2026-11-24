"""Ayudas de la aceptación de H-027 (la lectura de la morosidad, change 10a `morosidad`, D-167). Copia del mundo
de H-022 (Torre Ficticia), sin pagos informados: las emisiones y los pagos se cargan con el libro.

Caja negra por la API real (`aceptacion/H-027/CONTRATO.md`) con la identidad inyectada. Lo que todavía no existe
(la ruta, `proptech_api.morosidad`) se pide con un `assert` y un mensaje, nunca con un error de setup.

Base de los ejemplos (inventada, HISTORIAS.md "Morosidad"): "Torre Ficticia", `1A` 0,30, `1B` 0,30, `2A` 0,25 y
`2B` 0,15; 3% mensual proporcional, gracia 0, umbral $500. "Ana Prueba" es propietaria de `1A` y `2B` (con
email), "Carla Prueba" propietaria de `1B`, "Beto Prueba" inquilino de `1B`; `2A` sin propietarios. Hoy es el
18/11/2026.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .._cuenta_corriente import sesion_app
from .._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad

HOY = date(2026, 11, 18)
SEP, OCT, NOV = date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)
UNIDADES = {"1A": "0.300000", "1B": "0.300000", "2A": "0.250000", "2B": "0.150000"}
#: Ordinaria mensual de cada unidad en la base de los ejemplos.
MENSUAL = {"1A": "10000.00", "1B": "40000.00", "2A": "5000.00", "2B": "8000.00"}
EMAIL_DE_ANA = "ana.prueba@ejemplo.invalid"
CLAVES_DE_FILA = {"unidad_id", "unidad", "propietarios", "etiqueta", "total_vencido", "capital", "intereses",
                  "liquidaciones_vencidas", "vencida_desde", "dias"}


@dataclass
class Mundo:
    app: FastAPI
    cliente: TestClient
    base: BaseDeEdificio
    admin: UUID
    admin_b: UUID
    edificio: UUID
    otro: UUID
    edificio_b: UUID
    unidades: dict[str, UUID] = field(default_factory=dict)
    personas: dict[str, UUID] = field(default_factory=dict)
    persona_b: UUID = field(default_factory=uuid4)
    emisiones: dict[date, UUID] = field(default_factory=dict)

    def identidad(self, rol: str = "super_admin") -> Any:
        from proptech_core.acceso.dominio.identidad import Identidad

        return Identidad(self.admin, self.personas[rol])

    def como(self, rol: str) -> None:
        from proptech_api.acceso import identidad_actual
        from proptech_core.acceso.dominio.identidad import Identidad

        if rol == "administracion_b":
            identidad = Identidad(self.admin_b, self.persona_b)
        else:
            identidad = Identidad(self.admin, self.personas[rol])
        self.app.dependency_overrides[identidad_actual] = lambda: identidad

    def filas(self, consulta: str, parametros: tuple[Any, ...] = ()) -> list[Any]:
        with self.base.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, self.admin)
            return list(conexion.execute(consulta, parametros).fetchall())

    def uno(self, consulta: str, parametros: tuple[Any, ...] = ()) -> Any:
        return self.filas(consulta, parametros)[0][0]


def _vecino(conexion: psycopg.Connection, admin: UUID, edificio: UUID, nombre: str,
            unidades: list[tuple[UUID, str]], email: str | None = None) -> UUID:
    persona = uuid4()
    conexion.execute("INSERT INTO persona (id, administracion_id, nombre, email) VALUES (%s, %s, %s, %s)",
                     (persona, admin, nombre, email))
    for unidad, vinculo in unidades:
        conexion.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id, unidad_id, vinculo) "
            "VALUES (%s, %s, 'vecino', %s, %s, %s)",
            (admin, persona, edificio, unidad, vinculo),
        )
    return persona


def _fijar_hoy(app: FastAPI) -> None:
    try:
        from proptech_api.morosidad import hoy
    except ImportError:
        return  # todavía no existe: la ruta da 404 y cada test falla por aserción
    app.dependency_overrides[hoy] = lambda: HOY


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch) -> Iterator[Mundo]:
    from proptech_api.app import crear_app

    from ...conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION

    for clave, valor in base_del_edificio.entorno.items():
        if clave in {"POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB"}:
            monkeypatch.setenv(clave, valor)
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER_DE_SESION)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD_DE_SESION)
    monkeypatch.setenv("PROPTECH_CLAVE_DE_ENLACES", "clave-de-prueba-de-enlaces-firmados-0123456789")
    monkeypatch.delenv("PROPTECH_OPENROUTER_API_KEY", raising=False)
    app = crear_app()
    admin, admin_b = uuid4(), uuid4()
    roles = ("super_admin", "admin_principal", "admin_del_edificio", "admin_de_otro_edificio",
             "contador", "contador_del_edificio", "auxiliar", "consejo", "consejo_de_otro_edificio")
    personas = {rol: uuid4() for rol in roles}
    persona_b = uuid4()
    edificio, otro, edificio_b = uuid4(), uuid4(), uuid4()
    with TestClient(app) as cliente:
        with base_del_edificio.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin)
            conexion.execute("INSERT INTO administracion (id, nombre) VALUES (%s, 'Administración Ficticia')",
                             (admin,))
            for persona in personas.values():
                conexion.execute("INSERT INTO persona (id, administracion_id, nombre) "
                                 "VALUES (%s, %s, 'Persona del equipo ficticia')", (persona, admin))
            for complejo, nombre in ((edificio, "Torre Ficticia"), (otro, "Otro Edificio Ficticio")):
                conexion.execute(
                    "INSERT INTO complejo (id, administracion_id, nombre, localidad, pisos, subsuelos) "
                    "VALUES (%s, %s, %s, 'Mendoza', 3, 1)", (complejo, admin, nombre))
            ids = {u: insertar_unidad(conexion, admin, edificio, u, coeficiente=c) for u, c in UNIDADES.items()}
            insertar_unidad(conexion, admin, otro, "9A", coeficiente="1.000000")
            asignaciones = {
                "super_admin": ("super_admin", None),
                "admin_principal": ("administrador", None),
                "admin_del_edificio": ("administrador", edificio),
                "admin_de_otro_edificio": ("administrador", otro),
                "contador": ("contador", None),
                "contador_del_edificio": ("contador", edificio),
                "auxiliar": ("auxiliar", edificio),
                "consejo": ("consejo", edificio),
                "consejo_de_otro_edificio": ("consejo", otro),
            }
            for rol, (nombre_rol, alcance) in asignaciones.items():
                conexion.execute(
                    "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id) "
                    "VALUES (%s, %s, %s, %s)", (admin, personas[rol], nombre_rol, alcance))
            personas["ana"] = _vecino(conexion, admin, edificio, "Ana Prueba",
                                      [(ids["1A"], "propietario"), (ids["2B"], "propietario")], EMAIL_DE_ANA)
            personas["carla"] = _vecino(conexion, admin, edificio, "Carla Prueba", [(ids["1B"], "propietario")])
            personas["beto"] = _vecino(conexion, admin, edificio, "Beto Prueba", [(ids["1B"], "inquilino")])
            conexion.execute("UPDATE complejo SET estado_migracion = 'sin_saldos_previos' WHERE id IN (%s, %s)",
                             (edificio, otro))
            for complejo in (edificio, otro):
                conexion.execute(
                    "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, vigente_desde, "
                    "tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, porcentaje_fondo, "
                    "dia_de_vencimiento, modalidad_de_vencimiento) VALUES (%s, %s, %s, '2026-01-01', '3.00', "
                    "'500.00', 0, 'proporcional_por_dia', '5.00', 10, 'unico')",
                    (admin, complejo, personas["super_admin"]))
        with base_del_edificio.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin_b)
            conexion.execute("INSERT INTO administracion (id, nombre) VALUES (%s, 'Otra administración ficticia')",
                             (admin_b,))
            conexion.execute("INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'Persona B')",
                             (persona_b, admin_b))
            conexion.execute("INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
                             "VALUES (%s, %s, 'super_admin')", (admin_b, persona_b))
            conexion.execute("INSERT INTO complejo (id, administracion_id, nombre, localidad, pisos, subsuelos) "
                             "VALUES (%s, %s, 'Edificio B ficticio', 'Mendoza', 3, 1)", (edificio_b, admin_b))
            insertar_unidad(conexion, admin_b, edificio_b, "1A", coeficiente="1.000000")
        m = Mundo(app=app, cliente=cliente, base=base_del_edificio, admin=admin, admin_b=admin_b,
                  edificio=edificio, otro=otro, edificio_b=edificio_b, unidades=ids, personas=personas,
                  persona_b=persona_b)
        _fijar_hoy(app)
        m.como("admin_principal")
        try:
            yield m
        finally:
            app.dependency_overrides.clear()


# --- El libro ------------------------------------------------------------------------------------------


def emitir(m: Mundo, periodo: date, unidades: tuple[str, ...] = tuple(UNIDADES)) -> UUID:
    """Una emisión del libro con la ordinaria de `MENSUAL`, vencimiento el día 10 del período."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import emisiones
    from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

    emision_id = uuid4()
    with sesion_app(m.base, m.admin) as s:
        emisiones.registrar_emision(
            s, m.identidad(), emision_id=emision_id, complejo_id=m.edificio, periodo=periodo,
            obligaciones=[ObligacionAEmitir(m.unidades[u], periodo.replace(day=10), Dinero(MENSUAL[u]),
                                            Dinero("0.00"), Dinero("0.00")) for u in unidades],
            request_id=uuid4(),
        )
        s.commit()
    m.emisiones[periodo] = emision_id
    return emision_id


def pagar(m: Mundo, unidad: str, importe: str, fecha: date) -> None:
    """Un crédito `pago` del libro, imputado con R04."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import creditos

    with sesion_app(m.base, m.admin) as s:
        creditos.registrar_credito(
            s, m.identidad(), cuenta_id=cuenta_de(m, unidad), tipo="pago", importe=Dinero(importe),
            fecha_valor=fecha, operacion_id=uuid4(), destino=None, request_id=uuid4())
        s.commit()


def anular(m: Mundo, emision_id: UUID) -> None:
    from proptech_core.cuenta_corriente.aplicacion import emisiones

    with sesion_app(m.base, m.admin) as s:
        emisiones.anular_emision(s, m.identidad(), emision_id=emision_id, motivo="Anulación ficticia",
                                 request_id=uuid4())
        s.commit()


def armar_la_base(m: Mundo) -> None:
    """Septiembre, octubre y noviembre emitidos. `1A` no paga nada (moroso crítico); `1B` y `2B` pagan
    septiembre y octubre antes del vencimiento y deben noviembre (con deuda vencida); `2A` paga todo menos $300
    de noviembre (bajo el umbral)."""
    emitir(m, SEP)
    for u in ("1B", "2A", "2B"):
        pagar(m, u, MENSUAL[u], date(2026, 9, 5))
    emitir(m, OCT)
    for u in ("1B", "2A", "2B"):
        pagar(m, u, MENSUAL[u], date(2026, 10, 5))
    emitir(m, NOV)
    pagar(m, "2A", "4700.00", date(2026, 11, 5))


def cuenta_de(m: Mundo, unidad: str) -> UUID:
    return UUID(str(m.uno("SELECT id FROM cuenta WHERE unidad_id = %s", (m.unidades[unidad],))))


def intereses_registrados(m: Mundo, unidad: str) -> Decimal:
    """La suma de los movimientos `interes` de la cuenta (sin pagos ni ajustes en `1A`, es su residual)."""
    return Decimal(str(m.uno(
        "SELECT coalesce(sum(importe), 0)::numeric(14,2)::text FROM movimiento WHERE cuenta_id = %s "
        "AND tipo = 'interes'", (cuenta_de(m, unidad),))))


def situacion_del_libro(m: Mundo) -> dict[str, tuple[str, str]]:
    """Unidad → (etiqueta, total vencido) según `situacion_del_edificio` del 4c, a hoy."""
    from proptech_core.cuenta_corriente.aplicacion import cobranza

    por_id = {v: k for k, v in m.unidades.items()}
    with sesion_app(m.base, m.admin) as s:
        return {por_id[x.unidad_id]: (x.situacion.etiqueta, x.situacion.total_vencido.a_texto())
                for x in cobranza.situacion_del_edificio(s, complejo_id=m.edificio, fecha=HOY)}


def del_libro(m: Mundo) -> dict[str, tuple[int, str]]:
    """Filas y contenido de `movimiento`, `imputacion`, `obligacion` y `auditoria` de esta administración, con el
    superusuario (sin RLS, L-092)."""
    c = m.base.contenedor
    with psycopg.connect(host=c.get_container_host_ip(), port=c.get_exposed_port(5432), dbname=m.base.nombre,
                         user=c.username, password=c.password, autocommit=True) as conexion:
        resultado = {}
        for tabla in ("movimiento", "imputacion", "obligacion", "auditoria"):
            fila = conexion.execute(
                f"SELECT count(*), coalesce(md5(string_agg(t::text, '|' ORDER BY t::text)), '') "  # noqa: S608
                f"FROM public.{tabla} t WHERE t.administracion_id = %s", (m.admin,)
            ).fetchone()
            assert fila is not None
            resultado[tabla] = (int(fila[0]), str(fila[1]))
        return resultado


# --- La API --------------------------------------------------------------------------------------------


def ruta(m: Mundo, complejo: UUID | None = None) -> str:
    return f"/api/complejos/{complejo or m.edificio}/morosidad"


def pedir(m: Mundo, complejo: UUID | None = None) -> Any:
    return m.cliente.get(ruta(m, complejo))


def morosidad(m: Mundo) -> dict[str, Any]:
    r = pedir(m)
    assert r.status_code == 200, f"la morosidad: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    cuerpo = r.json()
    for clave in ("fecha", "intereses_al", "resumen", "unidades"):
        assert clave in cuerpo, f"la morosidad no trae `{clave}`: {cuerpo}"
    return dict(cuerpo)


def filas(m: Mundo) -> dict[str, dict[str, Any]]:
    """Identificador de la unidad → su fila."""
    return {f["unidad"]: f for f in morosidad(m)["unidades"]}


def sin_permiso(r: Any, accion: str = "ver_morosidad") -> None:
    assert r.status_code == 403, f"se esperaba 403, llegó {r.status_code}: {r.text[:300]}"
    detalle = r.json().get("detail")
    assert isinstance(detalle, dict) and detalle.get("permiso_faltante") == accion, r.json()


def no_encontrado(r: Any) -> None:
    assert r.status_code == 404, f"se esperaba 404, llegó {r.status_code}: {r.text[:300]}"
