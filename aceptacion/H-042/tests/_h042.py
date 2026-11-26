"""Ayudas de la aceptación de H-042 (condonación y gestión judicial, change 10b, R29, R31, R20, D-171, D-172).

Caja negra por la API real (`aceptacion/H-042/CONTRATO.md`) con la identidad inyectada. El libro se arma con
`registrar_emision` y `registrar_credito` (como H-041). Lo que todavía no existe (las rutas, los módulos nuevos, la tabla)
se pide con un `assert` y un mensaje, nunca con un error de setup.

Base (inventada): "Torre Ficticia", `1A` 0,30, `1B` 0,30, `2A` 0,25 y `2B` 0,15; 3% mensual proporcional, gracia 0,
vencimiento el día 10, umbral de saldo chico 500,00. Septiembre, octubre y noviembre emitidos (`MENSUAL`: 1A 10.000,
1B 40.000, 2A 5.000, 2B 8.000). "Ana Prueba" es propietaria de `1A` y `2B`. Hoy es el 18/11/2026.

  1A  no paga nada: intereses registrados 510,00 sobre septiembre y 210,00 sobre octubre; capital vencido 20.000,00 al
      05/11 y 30.000,00 al 18/11 (dos o tres liquidaciones vencidas: moroso crítico).
  1B  paga a término (`b_tarde=False`) o tarde (`b_tarde=True`, el capital de septiembre el 25/09 y el de octubre más
      los intereses de septiembre el 25/10): sólo deuda de intereses al 05/11.
"""

from __future__ import annotations

import importlib
import io
import re
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

CLAVE_DE_ENLACES = "clave-de-prueba-de-enlaces-firmados-0123456789"
HOY = date(2026, 11, 18)
SEP, OCT, NOV = date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)
CORTE = date(2026, 11, 5)
UNIDADES = {"1A": "0.300000", "1B": "0.300000", "2A": "0.250000", "2B": "0.150000"}
MENSUAL = {"1A": "10000.00", "1B": "40000.00", "2A": "5000.00", "2B": "8000.00"}
NO_ENCONTRADO = {"detail": "no encontrado"}
MONTO = re.compile(r"^-?[0-9]+\.[0-9]{2}$")
MOTIVO = "El vecino acreditó un error de facturación"
CLAVES_DE_LA_CONDONACION = {"id", "unidad_id", "obligacion_id", "periodo", "importe", "motivo", "fecha_valor"}
CLAVES_PARA_EL_VECINO = {"id", "periodo", "importe", "motivo", "fecha_valor"}
CLAVES_PARA_EL_EDIFICIO = {"id", "unidad_id", "unidad", "obligacion_id", "periodo", "importe", "motivo", "fecha_valor"}
CLAVES_DE_LA_MARCA = {"id", "unidad_id", "en_gestion_judicial", "motivo", "fecha"}
CLAVES_DE_FILA = {"unidad_id", "unidad", "propietarios", "etiqueta", "total_vencido", "capital", "intereses",
                  "liquidaciones_vencidas", "vencida_desde", "dias"}
ROLES = ("super_admin", "admin_principal", "admin_del_edificio", "admin_de_otro_edificio", "contador", "auxiliar",
         "consejo")


def importar(modulo: str, nombre: str) -> Any:
    """Lo que todavía no existe se pide con un `assert` (falla por aserción, no por error de setup)."""
    try:
        importado = importlib.import_module(modulo)
    except ImportError:
        importado = None
    assert importado is not None and hasattr(importado, nombre), f"falta `{modulo}.{nombre}` (lo crea el 10b)"
    return getattr(importado, nombre)


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
    unidad_otro: UUID = field(default_factory=uuid4)
    unidad_b: UUID = field(default_factory=uuid4)
    personas: dict[str, UUID] = field(default_factory=dict)
    persona_b: UUID = field(default_factory=uuid4)
    pagos: dict[str, str] = field(default_factory=dict)

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

    def ejecutar(self, consulta: str, parametros: tuple[Any, ...] = ()) -> None:
        with self.base.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, self.admin)
            conexion.execute(consulta, parametros)


def _vecino(conexion: psycopg.Connection, admin: UUID, edificio: UUID, nombre: str,
            unidades: list[tuple[UUID, str]]) -> UUID:
    persona = uuid4()
    conexion.execute("INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, %s)",
                     (persona, admin, nombre))
    for unidad, vinculo in unidades:
        conexion.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id, unidad_id, vinculo) "
            "VALUES (%s, %s, 'vecino', %s, %s, %s)", (admin, persona, edificio, unidad, vinculo))
    return persona


def _fijar_hoy(app: FastAPI) -> None:
    """La fecha de las lecturas de plata es una dependencia (L-090): la de pagos, morosidad, libre deuda, vecino, condonaciones y gestión judicial."""
    for modulo in ("proptech_api.pagos", "proptech_api.morosidad", "proptech_api.libre_deuda", "proptech_api.vecino",
                   "proptech_api.condonaciones", "proptech_api.gestion_judicial"):
        try:
            importado = __import__(modulo, fromlist=["hoy"])
        except ImportError:
            continue  # todavía no existe: la ruta da 404 y cada test falla por aserción
        app.dependency_overrides[importado.hoy] = lambda: HOY


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch) -> Iterator[Mundo]:
    from proptech_api.app import crear_app

    from ...conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION

    for clave, valor in base_del_edificio.entorno.items():
        if clave in {"POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB"}:
            monkeypatch.setenv(clave, valor)
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER_DE_SESION)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD_DE_SESION)
    monkeypatch.setenv("PROPTECH_CLAVE_DE_ENLACES", CLAVE_DE_ENLACES)
    monkeypatch.delenv("PROPTECH_OPENROUTER_API_KEY", raising=False)
    app = crear_app()
    admin, admin_b = uuid4(), uuid4()
    personas = {rol: uuid4() for rol in ROLES}
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
            unidad_otro = insertar_unidad(conexion, admin, otro, "9A", coeficiente="1.000000")
            asignaciones = {
                "super_admin": ("super_admin", None),
                "admin_principal": ("administrador", None),
                "admin_del_edificio": ("administrador", edificio),
                "admin_de_otro_edificio": ("administrador", otro),
                "contador": ("contador", None),
                "auxiliar": ("auxiliar", edificio),
                "consejo": ("consejo", edificio),
            }
            for rol, (nombre_rol, alcance) in asignaciones.items():
                conexion.execute(
                    "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id) "
                    "VALUES (%s, %s, %s, %s)", (admin, personas[rol], nombre_rol, alcance))
            personas["ana"] = _vecino(conexion, admin, edificio, "Ana Prueba",
                                      [(ids["1A"], "propietario"), (ids["2B"], "propietario")])
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
            unidad_b = insertar_unidad(conexion, admin_b, edificio_b, "1A", coeficiente="1.000000")
        m = Mundo(app=app, cliente=cliente, base=base_del_edificio, admin=admin, admin_b=admin_b,
                  edificio=edificio, otro=otro, edificio_b=edificio_b, unidades=ids, unidad_otro=unidad_otro,
                  unidad_b=unidad_b, personas=personas, persona_b=persona_b)
        _fijar_hoy(app)
        m.como("super_admin")
        try:
            yield m
        finally:
            app.dependency_overrides.clear()




# --- El libro ------------------------------------------------------------------------------------------


def cuenta_de(m: Mundo, unidad: str) -> UUID:
    return UUID(str(m.uno("SELECT id FROM cuenta WHERE unidad_id = %s", (m.unidades[unidad],))))


def emitir(m: Mundo, periodo: date) -> UUID:
    """Una emisión del libro con la ordinaria de `MENSUAL`, vencimiento el día 10. Devuelve el id de la emisión."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import emisiones
    from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

    emision_id = uuid4()
    with sesion_app(m.base, m.admin) as s:
        emisiones.registrar_emision(
            s, m.identidad(), emision_id=emision_id, complejo_id=m.edificio, periodo=periodo,
            obligaciones=[ObligacionAEmitir(m.unidades[u], periodo.replace(day=10), Dinero(MENSUAL[u]),
                                            Dinero("0.00"), Dinero("0.00")) for u in UNIDADES],
            request_id=uuid4())
        s.commit()
    return emision_id


def pagar(m: Mundo, unidad: str, importe: str, fecha: date) -> None:
    """Un crédito `pago` directo del libro, imputado con R04 (sin pasar por los pagos informados)."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import creditos

    with sesion_app(m.base, m.admin) as s:
        creditos.registrar_credito(
            s, m.identidad(), cuenta_id=cuenta_de(m, unidad), tipo="pago", importe=Dinero(importe),
            fecha_valor=fecha, operacion_id=uuid4(), destino=None, request_id=uuid4())
        s.commit()


def armar_la_deuda(m: Mundo, *, b_tarde: bool = False) -> None:
    """Septiembre, octubre y noviembre emitidos. `1B` paga a término o, con `b_tarde`, el 25/09 y el 25/10."""
    emitir(m, SEP)
    pagar(m, "1B", MENSUAL["1B"], date(2026, 9, 25) if b_tarde else date(2026, 9, 5))
    emitir(m, OCT)
    if b_tarde:
        pagar(m, "1B", "40600.00", date(2026, 10, 25))
    else:
        pagar(m, "1B", MENSUAL["1B"], date(2026, 10, 5))
    emitir(m, NOV)


def obligacion_de(m: Mundo, unidad: str, periodo: date) -> UUID:
    return UUID(str(m.uno("SELECT id FROM obligacion WHERE cuenta_id = %s AND periodo = %s",
                          (cuenta_de(m, unidad), periodo))))


def intereses_pendientes(m: Mundo, unidad: str) -> dict[date, Decimal]:
    """Lo que el libro todavía debe de interés de cada obligación (por período): intereses registrados menos lo
    imputado al componente interés (pagos y condonaciones). Leído de las tablas, no del código del módulo."""
    filas = m.filas(
        "SELECT o.periodo, (SELECT coalesce(sum(x.importe), 0) FROM movimiento x WHERE x.obligacion_id = o.id "
        "AND x.tipo = 'interes') - (SELECT coalesce(sum(i.importe), 0) FROM imputacion i WHERE i.obligacion_id = o.id "
        "AND i.componente = 'interes') FROM obligacion o WHERE o.cuenta_id = %s ORDER BY o.periodo",
        (cuenta_de(m, unidad),))
    return {f[0]: Decimal(f[1]) for f in filas}


def saldo_de(m: Mundo, unidad: str) -> Decimal:
    """Lo que debe la cuenta: obligaciones más intereses registrados menos todo lo imputado (de pagos y de créditos)."""
    cuenta = cuenta_de(m, unidad)
    obligaciones = m.uno("SELECT coalesce(sum(ordinaria + fondo_de_reserva + extraordinaria), 0) FROM obligacion "
                         "WHERE cuenta_id = %s", (cuenta,))
    intereses = m.uno("SELECT coalesce(sum(importe), 0) FROM movimiento WHERE cuenta_id = %s AND tipo = 'interes'",
                      (cuenta,))
    imputado = m.uno("SELECT coalesce(sum(importe), 0) FROM imputacion WHERE cuenta_id = %s", (cuenta,))
    return Decimal(obligaciones) + Decimal(intereses) - Decimal(imputado)


def superusuario(m: Mundo, consulta: str, parametros: tuple[Any, ...] = ()) -> list[Any]:
    """Una consulta con el superusuario (sin RLS, L-092)."""
    c = m.base.contenedor
    with psycopg.connect(host=c.get_container_host_ip(), port=c.get_exposed_port(5432), dbname=m.base.nombre,
                         user=c.username, password=c.password, autocommit=True) as conexion:
        return list(conexion.execute(consulta, parametros).fetchall())  # type: ignore[arg-type]


def del_libro(m: Mundo) -> dict[str, tuple[int, str]]:
    """Filas y contenido del libro de esta administración, con el superusuario (sin RLS, L-092)."""
    resultado = {}
    for tabla in ("movimiento", "imputacion", "obligacion", "cuenta"):
        fila = superusuario(
            m, f"SELECT count(*), coalesce(md5(string_agg(t::text, '|' ORDER BY t::text)), '') "  # noqa: S608
               f"FROM public.{tabla} t WHERE t.administracion_id = %s", (m.admin,))[0]
        resultado[tabla] = (int(fila[0]), str(fila[1]))
    return resultado


def condonaciones_del_libro(m: Mundo) -> list[Any]:
    """(id, unidad_id, obligacion_id, componente, importe, fecha_valor, motivo, registrado_por) de los créditos
    `condonacion` de la administración, con el superusuario."""
    return superusuario(
        m, "SELECT x.id, c.unidad_id, x.obligacion_id, x.componente, x.importe::text, x.fecha_valor, x.motivo, "
           "x.registrado_por FROM movimiento x JOIN cuenta c ON c.id = x.cuenta_id WHERE x.tipo = 'condonacion' "
           "AND x.administracion_id = %s ORDER BY x.registrado_en, x.id", (m.admin,))


def auditorias(m: Mundo, accion: str) -> list[Any]:
    """(entidad, entidad_id, persona_id, detalle) de la administración de este mundo (L-092)."""
    return superusuario(m, "SELECT entidad, entidad_id, persona_id, detalle FROM auditoria WHERE accion = %s "
                           "AND administracion_id = %s ORDER BY creado_en", (accion, m.admin))


def interes_corrido_del_libro(m: Mundo, unidad: str, corte: date) -> Decimal:
    """El interés de R03 que el libro todavía no registró hasta `corte` (el cálculo de dominio de la emisión)."""
    from proptech_core.cuenta_corriente.aplicacion import emisiones, lecturas

    cuenta = cuenta_de(m, unidad)
    with sesion_app(m.base, m.admin) as s:
        foto = lecturas.foto(s, cuenta)
        _, calculados = emisiones.calcular_intereses_del_corte(s, m.edificio, corte, {cuenta: foto})
        return sum((i.importe.decimal for i in calculados.get(cuenta, [])), Decimal("0.00"))


# --- La condonación (CONTRATO.md) ----------------------------------------------------------------------


def ruta_condonar(m: Mundo, unidad: str | UUID, complejo: UUID | None = None) -> str:
    uid = unidad if isinstance(unidad, UUID) else m.unidades[unidad]
    return f"/api/complejos/{complejo or m.edificio}/unidades/{uid}/condonaciones"


def cuerpo_de_condonacion(obligacion: UUID | str, importe: Any = "100.00", motivo: Any = MOTIVO) -> dict[str, Any]:
    return {"obligacion_id": str(obligacion), "importe": importe, "motivo": motivo}


def condonar(m: Mundo, unidad: str | UUID, cuerpo: dict[str, Any], complejo: UUID | None = None) -> Any:
    return m.cliente.post(ruta_condonar(m, unidad, complejo), json=cuerpo)


def condonar_ok(m: Mundo, unidad: str, periodo: date, importe: str, motivo: str = MOTIVO) -> dict[str, Any]:
    r = condonar(m, unidad, cuerpo_de_condonacion(obligacion_de(m, unidad, periodo), importe, motivo))
    assert r.status_code == 201, f"condonar: se esperaba 201, llegó {r.status_code}: {r.text[:300]}"
    c = r.json()
    assert isinstance(c, dict) and set(c) == CLAVES_DE_LA_CONDONACION, f"las claves de la condonación: {c!r}"
    return dict(c)


def condonaciones_del_vecino(m: Mundo, unidad: str | UUID) -> Any:
    uid = unidad if isinstance(unidad, UUID) else m.unidades[unidad]
    return m.cliente.get(f"/api/mis-unidades/{uid}/condonaciones")


def condonaciones_del_edificio(m: Mundo, complejo: UUID | None = None) -> Any:
    return m.cliente.get(f"/api/complejos/{complejo or m.edificio}/condonaciones")


# --- La gestión judicial (CONTRATO.md) -----------------------------------------------------------------


def ruta_marca(m: Mundo, unidad: str | UUID, complejo: UUID | None = None) -> str:
    uid = unidad if isinstance(unidad, UUID) else m.unidades[unidad]
    return f"/api/complejos/{complejo or m.edificio}/unidades/{uid}/gestion-judicial"


def marcar(m: Mundo, unidad: str | UUID, cuerpo: Any = None, complejo: UUID | None = None) -> Any:
    return m.cliente.post(ruta_marca(m, unidad, complejo), json={"motivo": "Pasó al estudio jurídico"}
                          if cuerpo is None else cuerpo)


def desmarcar(m: Mundo, unidad: str | UUID, cuerpo: Any = None, complejo: UUID | None = None) -> Any:
    return m.cliente.request("DELETE", ruta_marca(m, unidad, complejo),
                             json={"motivo": "Regularizó la deuda"} if cuerpo is None else cuerpo)


def marcar_ok(m: Mundo, unidad: str, motivo: str = "Pasó al estudio jurídico") -> dict[str, Any]:
    r = marcar(m, unidad, {"motivo": motivo})
    assert r.status_code == 201, f"marcar: se esperaba 201, llegó {r.status_code}: {r.text[:300]}"
    c = r.json()
    assert isinstance(c, dict) and set(c) == CLAVES_DE_LA_MARCA, f"las claves de la marca: {c!r}"
    return dict(c)


def desmarcar_ok(m: Mundo, unidad: str, motivo: str = "Regularizó la deuda") -> dict[str, Any]:
    r = desmarcar(m, unidad, {"motivo": motivo})
    assert r.status_code == 200, f"desmarcar: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    c = r.json()
    assert isinstance(c, dict) and set(c) == CLAVES_DE_LA_MARCA, f"las claves de la marca: {c!r}"
    return dict(c)


def marcas_del_historial(m: Mundo) -> list[Any]:
    """(id, unidad_id, accion, motivo, fecha, registrado_por) de `gestion_judicial_de_unidad`, en el orden en que se
    agregaron; pide con un `assert` que la tabla exista."""
    existe = superusuario(m, "SELECT to_regclass('public.gestion_judicial_de_unidad') IS NOT NULL")[0][0]
    assert existe, "falta la tabla `gestion_judicial_de_unidad` (la crea la migración del 10b)"
    return superusuario(
        m, "SELECT id, unidad_id, accion, motivo, fecha, registrado_por FROM gestion_judicial_de_unidad "
           "WHERE administracion_id = %s ORDER BY registrado_en, id", (m.admin,))


def unidades_marcadas(m: Mundo, complejo: UUID | None = None) -> set[UUID]:
    """La consulta de aplicación que usa el 13, con una sesión de la app."""
    consulta = importar("proptech_core.cuenta_corriente.aplicacion.gestion_judicial", "unidades_en_gestion_judicial")
    with sesion_app(m.base, m.admin) as s:
        resultado = consulta(s, complejo_id=complejo or m.edificio)
        assert isinstance(resultado, frozenset), f"tiene que devolver un frozenset de UUID: {resultado!r}"
        return set(resultado)


# --- Lo que dicen R20 y la morosidad -------------------------------------------------------------------


def situacion(m: Mundo, unidad: str, fecha: date) -> Any:
    from proptech_core.cuenta_corriente.aplicacion.cobranza import situacion_de_cuenta

    with sesion_app(m.base, m.admin) as s:
        return situacion_de_cuenta(s, cuenta_id=cuenta_de(m, unidad), fecha=fecha)


def situaciones_del_edificio(m: Mundo, fecha: date) -> dict[str, Any]:
    from proptech_core.cuenta_corriente.aplicacion.cobranza import situacion_del_edificio

    nombre = {v: k for k, v in m.unidades.items()}
    with sesion_app(m.base, m.admin) as s:
        return {nombre[x.unidad_id]: x.situacion for x in situacion_del_edificio(s, complejo_id=m.edificio, fecha=fecha)
                if x.unidad_id in nombre}


def morosidad(m: Mundo) -> dict[str, Any]:
    r = m.cliente.get(f"/api/complejos/{m.edificio}/morosidad")
    assert r.status_code == 200, f"la morosidad: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    return dict(r.json())


def fila_de(cuerpo: dict[str, Any], unidad: str) -> dict[str, Any]:
    filas = [f for f in cuerpo["unidades"] if f["unidad"] == unidad]
    assert len(filas) == 1, f"la morosidad tiene que traer una fila de la {unidad}: {cuerpo['unidades']!r}"
    return dict(filas[0])


# --- El certificado de H-041 ---------------------------------------------------------------------------


def emitir_certificado(m: Mundo, unidad: str, corte: date) -> dict[str, Any]:
    r = m.cliente.post(f"/api/complejos/{m.edificio}/unidades/{m.unidades[unidad]}/libre-deuda",
                       json={"fecha_de_corte": corte.isoformat()})
    assert r.status_code == 201, f"emitir el libre deuda: se esperaba 201, llegó {r.status_code}: {r.text[:300]}"
    return dict(r.json())


def texto_del_pdf(m: Mundo, certificado: dict[str, Any]) -> str:
    from pypdf import PdfReader

    r = m.cliente.get(certificado["enlace"]["url"])
    assert r.status_code == 200 and r.content.startswith(b"%PDF"), f"el PDF: {r.status_code} {r.content[:20]!r}"
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)


def sin_espacios(texto: str) -> str:
    return "".join(texto.split())


# --- Los errores ---------------------------------------------------------------------------------------


def no_encontrado(r: Any, donde: str) -> None:
    assert r.status_code == 404, f"{donde}: se esperaba 404, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == NO_ENCONTRADO, f"{donde}: el 404 tiene que ser {NO_ENCONTRADO}, llegó {r.json()}"


def sin_permiso(r: Any, donde: str, permiso: str) -> None:
    assert r.status_code == 403, f"{donde}: se esperaba 403, llegó {r.status_code}: {r.text[:300]}"
    detalle = r.json().get("detail")
    assert isinstance(detalle, dict) and detalle.get("permiso_faltante") == permiso, (
        f"{donde}: el 403 tiene que decir `{permiso}`: {r.json()}")


def sin_cambios(m: Mundo, antes: dict[str, tuple[int, str]], auditadas: int, accion: str, donde: str) -> None:
    assert del_libro(m) == antes, f"{donde}: el libro cambió"
    assert len(auditorias(m, accion)) == auditadas, f"{donde}: quedó una auditoría de `{accion}`"
