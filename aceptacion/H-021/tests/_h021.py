"""Ayudas de la aceptación de H-021 (el ajuste del interés, change 8, D-166). Copia de las de H-020. Copia de las de H-018, sin la
emisión automática de noviembre: cada test arma sus meses con `emitir`.

Caja negra por la API real (`aceptacion/H-021/CONTRATO.md`, el de H-020 y el de H-018) con la identidad inyectada. Los datos de partida
se cargan por SQL con el rol de la app y la emisión de noviembre con `registrar_emision` del libro. Lo que
todavía no existe (las rutas, `proptech_api.pagos`) se pide con un `assert` y un mensaje, nunca con un error de
setup.

Base de los ejemplos (inventada, HISTORIAS.md "Pagos informados"): "Torre Ficticia", `1A` 0,30, `1B` 0,30,
`2A` 0,25 y `2B` 0,15, con la expensa de noviembre de 2026 emitida (vencimiento 10/11/2026). "Ana Prueba" es
propietaria de `1A` y de `2B`; "Beto Prueba", inquilino de `1B`. Hoy es el 18/11/2026.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .._cuenta_corriente import sesion_app
from .._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad

HOY = date(2026, 11, 18)
NOV = date(2026, 11, 1)
UNIDADES = {"1A": "0.300000", "1B": "0.300000", "2A": "0.250000", "2B": "0.150000"}
#: Lo emitido en noviembre por unidad: ordinaria (con cargos), fondo, extraordinaria (H-011).
EMITIDO = {
    "1A": ("27000.00", "1350.00", "15000.00"),
    "1B": ("32000.00", "1350.00", "15000.00"),
    "2A": ("47500.00", "2375.00", "12500.00"),
    "2B": ("28500.00", "1425.00", "7500.00"),
}
TABLAS = (
    "comprobante_de_pago",
    "pago_informado",
    "parte_de_pago",
    "evento_de_pago",
    "movimiento_de_pago",
    "cbu_de_unidad",
)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + bytes(64)
JPEG = b"\xff\xd8\xff\xe0" + bytes(64)
PDF = b"%PDF-1.4\n%comprobante ficticio\n" + bytes(32)
EXE = b"MZ\x90\x00" + bytes(64)


@dataclass
class Mundo:
    app: FastAPI
    cliente: TestClient
    base: BaseDeEdificio
    admin: UUID
    admin_b: UUID
    edificio: UUID
    otro: UUID
    """Otro edificio de la misma administración, con la unidad `9A`."""
    edificio_b: UUID
    unidades: dict[str, UUID] = field(default_factory=dict)
    unidad_otro: UUID = field(default_factory=uuid4)
    personas: dict[str, UUID] = field(default_factory=dict)
    persona_b: UUID = field(default_factory=uuid4)

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

    def filas(self, consulta: str, parametros: tuple[Any, ...] = (), admin: UUID | None = None) -> list[Any]:
        with self.base.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin or self.admin)
            return list(conexion.execute(consulta, parametros).fetchall())

    def uno(self, consulta: str, parametros: tuple[Any, ...] = ()) -> Any:
        return self.filas(consulta, parametros)[0][0]

    def ejecutar(self, consulta: str, parametros: tuple[Any, ...] = ()) -> Any:
        with self.base.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, self.admin)
            cursor = conexion.execute(consulta, parametros)
            return cursor.fetchone() if cursor.description else None


def _vecino(conexion: psycopg.Connection, admin: UUID, edificio: UUID, nombre: str,
            unidades: list[tuple[UUID, str]]) -> UUID:
    persona = uuid4()
    conexion.execute("INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, %s)",
                     (persona, admin, nombre))
    for unidad, vinculo in unidades:
        conexion.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id, unidad_id, vinculo) "
            "VALUES (%s, %s, 'vecino', %s, %s, %s)",
            (admin, persona, edificio, unidad, vinculo),
        )
    return persona


def _fijar_hoy(app: FastAPI) -> None:
    try:
        from proptech_api.pagos import hoy
    except ImportError:
        return  # todavía no existe: las rutas dan 404 y cada test falla por aserción
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
             "contador", "auxiliar", "consejo")
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
            personas["beto"] = _vecino(conexion, admin, edificio, "Beto Prueba", [(ids["1B"], "inquilino")])
            conexion.execute("UPDATE complejo SET estado_migracion = 'sin_saldos_previos' WHERE id IN (%s, %s)",
                             (edificio, otro))
            conexion.execute(
                "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, vigente_desde, "
                "tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, porcentaje_fondo, "
                "dia_de_vencimiento, modalidad_de_vencimiento) VALUES (%s, %s, %s, '2026-01-01', '3.00', "
                "'500.00', 0, 'proporcional_por_dia', '5.00', 10, 'unico')",
                (admin, edificio, personas["super_admin"]))
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
                  edificio=edificio, otro=otro, edificio_b=edificio_b, unidades=ids, unidad_otro=unidad_otro,
                  personas=personas, persona_b=persona_b)
        _fijar_hoy(app)
        m.como("ana")
        try:
            yield m
        finally:
            app.dependency_overrides.clear()


def _emitir_noviembre(m: Mundo) -> None:
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import emisiones
    from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

    with sesion_app(m.base, m.admin) as s:
        emisiones.registrar_emision(
            s, m.identidad(), emision_id=uuid4(), complejo_id=m.edificio, periodo=NOV,
            obligaciones=[ObligacionAEmitir(m.unidades[u], date(2026, 11, 10), Dinero(o), Dinero(f), Dinero(e))
                          for u, (o, f, e) in EMITIDO.items()],
            request_id=uuid4(),
        )
        s.commit()


# --- La API --------------------------------------------------------------------------------------------


def ruta(m: Mundo, sufijo: str = "", complejo: UUID | None = None) -> str:
    return f"/api/complejos/{complejo or m.edificio}/pagos{sufijo}"


def subir(m: Mundo, contenido: bytes = PNG, nombre: str = "comprobante.png",
          complejo: UUID | None = None) -> Any:
    return m.cliente.post(ruta(m, "/lectura", complejo), files={"archivo": (nombre, contenido, "image/png")})


def comprobante(m: Mundo, contenido: bytes = PNG, complejo: UUID | None = None) -> str:
    r = subir(m, contenido, complejo=complejo)
    assert r.status_code == 201, f"subir el comprobante: se esperaba 201, llegó {r.status_code}: {r.text[:300]}"
    cuerpo = r.json()
    for clave in ("comprobante_id", "lectura", "propuesta"):
        assert clave in cuerpo, f"la lectura no trae `{clave}`: {cuerpo}"
    return str(cuerpo["comprobante_id"])


def cuerpo(
    m: Mundo, comprobante_id: str, partes: dict[str, str], *, banco: str = "Banco Nación",
    numero: str = "12-345.678", fecha: str = "2026-11-05", monto: Any = None, cbu: Any = None,
) -> dict[str, Any]:
    from decimal import Decimal

    total = monto if monto is not None else f"{sum(Decimal(v) for v in partes.values()):.2f}"
    return {
        "comprobante_id": comprobante_id,
        "banco": banco,
        "numero_de_operacion": numero,
        "fecha_de_transferencia": fecha,
        "monto": total,
        "cbu_origen": cbu,
        "partes": [{"unidad_id": str(m.unidades.get(u) or u), "importe": i} for u, i in partes.items()],
    }


def informar(m: Mundo, datos: dict[str, Any], complejo: UUID | None = None) -> Any:
    return m.cliente.post(ruta(m, complejo=complejo), json=datos)


def informado(r: Any) -> str:
    assert r.status_code == 201, f"informar: se esperaba 201, llegó {r.status_code}: {r.text[:300]}"
    datos = r.json()
    assert datos.get("estado") == "informado", f"el pago tiene que quedar informado: {datos}"
    assert datos.get("pago_id"), f"falta `pago_id`: {datos}"
    return str(datos["pago_id"])


def informar_ok(m: Mundo, partes: dict[str, str], **kwargs: Any) -> str:
    return informado(informar(m, cuerpo(m, comprobante(m), partes, **kwargs)))


def campo_422(r: Any) -> str:
    assert r.status_code == 422, f"se esperaba 422, llegó {r.status_code}: {r.text[:300]}"
    detalle = r.json().get("detail")
    assert isinstance(detalle, list) and detalle, f"un 422 trae `detail` como lista: {r.json()}"
    return str(detalle[0]["loc"][-1])


def listar(m: Mundo) -> list[dict[str, Any]]:
    r = m.cliente.get(ruta(m))
    assert r.status_code == 200, f"listar pagos: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    lista = r.json()
    assert isinstance(lista, list), f"la lista de pagos tiene que ser una lista: {lista}"
    for p in lista:
        for clave in ("pago_id", "estado", "motivo", "banco", "numero_de_operacion", "fecha_de_transferencia",
                      "monto", "partes"):
            assert clave in p, f"un pago no trae `{clave}`: {p}"
    return list(lista)


def rechazar_en_la_base(m: Mundo, pago_id: str) -> None:
    """Rechazar es H-020: el rechazo se siembra como lo deja el contrato."""
    m.ejecutar(
        "INSERT INTO evento_de_pago (administracion_id, pago_id, tipo, motivo, registrado_por) "
        "VALUES (%s, %s, 'rechazado', 'Motivo ficticio', %s)",
        (m.admin, pago_id, m.personas["super_admin"]),
    )


# --- El libro y la base --------------------------------------------------------------------------------


def cuenta_de(m: Mundo, unidad: str) -> UUID:
    return UUID(str(m.uno("SELECT id FROM cuenta WHERE unidad_id = %s", (m.unidades[unidad],))))


def situacion(m: Mundo) -> dict[str, tuple[str, str, str, str]]:
    """Unidad → (deuda, a favor, aplicable, etiqueta de cobranza) al 18/11/2026."""
    from proptech_core.cuenta_corriente.aplicacion import cobranza, lecturas

    resultado = {}
    with sesion_app(m.base, m.admin) as s:
        for u in UNIDADES:
            cuenta = cuenta_de(m, u)
            e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
            c = cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=HOY)
            resultado[u] = (e.deuda.a_texto(), e.credito_a_favor.a_texto(), e.credito_a_favor_aplicable.a_texto(),
                            str(getattr(c, "etiqueta", c)))
    return resultado


def del_libro(m: Mundo) -> dict[str, tuple[int, str]]:
    """Filas y contenido de `movimiento`, `imputacion` y `obligacion`, con el superusuario (sin RLS)."""
    c = m.base.contenedor
    with psycopg.connect(host=c.get_container_host_ip(), port=c.get_exposed_port(5432), dbname=m.base.nombre,
                         user=c.username, password=c.password, autocommit=True) as conexion:
        resultado = {}
        for tabla in ("movimiento", "imputacion", "obligacion"):
            fila = conexion.execute(
                f"SELECT count(*), coalesce(md5(string_agg(t::text, '|' ORDER BY t::text)), '') "  # noqa: S608
                f"FROM public.{tabla} t"
            ).fetchone()
            assert fila is not None
            resultado[tabla] = (int(fila[0]), str(fila[1]))
        return resultado


def filas_de(m: Mundo, tabla: str) -> int:
    """Filas de una tabla de pagos **de la administración de este mundo**, con el superusuario (0 si la tabla
    todavía no existe). La base es de alcance módulo y las tablas son de sólo agregar: contar todas las
    administraciones arrastraría las filas de los tests anteriores."""
    c = m.base.contenedor
    with psycopg.connect(host=c.get_container_host_ip(), port=c.get_exposed_port(5432), dbname=m.base.nombre,
                         user=c.username, password=c.password, autocommit=True) as conexion:
        existe = conexion.execute("SELECT to_regclass(%s)", (f"public.{tabla}",)).fetchone()
        if existe is None or existe[0] is None:
            return 0
        fila = conexion.execute(
            f"SELECT count(*) FROM public.{tabla} WHERE administracion_id = %s", (m.admin,)  # noqa: S608
        ).fetchone()
        assert fila is not None
        return int(fila[0])


# --- Emisiones, confirmar y rechazar (H-020) -------------------------------------------------------------

SEP, OCT, DIC = date(2026, 9, 1), date(2026, 10, 1), date(2026, 12, 1)
CBU = "0110599520000001234567"


def emitir(m: Mundo, periodo: date, obligaciones: dict[str, str]) -> UUID:
    """Una emisión del libro: unidad → ordinaria (sin fondo ni extraordinaria), vencimiento el día 10."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import emisiones
    from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

    emision_id = uuid4()
    with sesion_app(m.base, m.admin) as s:
        emisiones.registrar_emision(
            s, m.identidad(), emision_id=emision_id, complejo_id=m.edificio, periodo=periodo,
            obligaciones=[ObligacionAEmitir(m.unidades[u], periodo.replace(day=10), Dinero(o), Dinero("0.00"),
                                            Dinero("0.00")) for u, o in obligaciones.items()],
            request_id=uuid4(),
        )
        s.commit()
    return emision_id


def emitir_noviembre(m: Mundo) -> UUID:
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import emisiones
    from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

    emision_id = uuid4()
    with sesion_app(m.base, m.admin) as s:
        emisiones.registrar_emision(
            s, m.identidad(), emision_id=emision_id, complejo_id=m.edificio, periodo=NOV,
            obligaciones=[ObligacionAEmitir(m.unidades[u], date(2026, 11, 10), Dinero(o), Dinero(f), Dinero(e))
                          for u, (o, f, e) in EMITIDO.items()],
            request_id=uuid4(),
        )
        s.commit()
    return emision_id


def confirmar(m: Mundo, pago_id: str) -> Any:
    return m.cliente.post(ruta(m, f"/{pago_id}/confirmacion"), json={})


def rechazar(m: Mundo, pago_id: str, motivo: Any = "El monto no coincide con el comprobante") -> Any:
    return m.cliente.post(ruta(m, f"/{pago_id}/rechazo"), json={} if motivo is None else {"motivo": motivo})


def ok(r: Any, estado: str, pago_id: str) -> None:
    assert r.status_code == 200, f"se esperaba 200, llegó {r.status_code}: {r.text[:400]}"
    assert r.json() == {"pago_id": pago_id, "estado": estado}, r.json()


def conflicto_de_estado(r: Any) -> None:
    assert r.status_code == 409, f"se esperaba 409, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == {"detail": "conflicto", "campo": "pago", "motivo": "estado"}, r.json()


def informar_y_confirmar(m: Mundo, partes: dict[str, str], **kwargs: Any) -> str:
    m.como("ana" if set(partes) <= {"1A", "2B"} else "beto")
    pago = informar_ok(m, partes, **kwargs)
    m.como("admin_principal")
    ok(confirmar(m, pago), "confirmado", pago)
    return pago


def estado(m: Mundo, unidad: str) -> Any:
    from proptech_core.cuenta_corriente.aplicacion import lecturas

    with sesion_app(m.base, m.admin) as s:
        return lecturas.estado_de_cuenta(s, cuenta_id=cuenta_de(m, unidad))


def residuales_por_periodo(m: Mundo, unidad: str) -> dict[tuple[str, str], str]:
    """(período, componente) → residual que cuenta: comparable entre dos cuentas distintas."""
    e = estado(m, unidad)
    periodos = {o.id: o.periodo.isoformat() for o in e.obligaciones}
    return {(periodos[o], str(c.value)): r.a_texto() for (o, c), r in e.residual.items()}


def pagos_del_libro(m: Mundo, unidad: str) -> list[tuple[str, str, date]]:
    """(tipo, importe, fecha_valor) de los créditos `pago` de la cuenta."""
    return [(str(f[0]), str(f[1]), f[2]) for f in m.filas(
        "SELECT tipo, importe::text, fecha_valor FROM movimiento WHERE cuenta_id = %s AND tipo = 'pago' "
        "ORDER BY registrado_en", (cuenta_de(m, unidad),))]


def intereses_de_la_emision(m: Mundo, unidad: str, emision_id: UUID) -> str:
    return str(m.uno(
        "SELECT coalesce(sum(importe), 0)::numeric(14,2)::text FROM movimiento WHERE cuenta_id = %s "
        "AND tipo = 'interes' AND emision_id = %s", (cuenta_de(m, unidad), emision_id)))


def eventos(m: Mundo, pago_id: str) -> list[tuple[str, Any]]:
    return [(str(f[0]), f[1]) for f in m.filas(
        "SELECT tipo, motivo FROM evento_de_pago WHERE pago_id = %s ORDER BY registrado_en", (pago_id,))]


def auditorias(m: Mundo, accion: str) -> int:
    """Sólo de la administración de este mundo (L-092)."""
    return int(m.uno("SELECT count(*) FROM auditoria WHERE accion = %s AND administracion_id = %s",
                     (accion, m.admin)))


def en_paralelo(*funciones: Callable[[], Any]) -> list[Any]:
    barrera = threading.Barrier(len(funciones))
    resultados: list[Any] = [None] * len(funciones)

    def correr(i: int, f: Callable[[], Any]) -> None:
        barrera.wait()
        try:
            resultados[i] = f()
        except BaseException as error:  # noqa: BLE001
            resultados[i] = error

    hilos = [threading.Thread(target=correr, args=(i, f), daemon=True) for i, f in enumerate(funciones)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=120)
    return resultados


# --- El ajuste (H-021) ---------------------------------------------------------------------------------


def configurar_desde(m: Mundo, desde: date, *, tasa: str = "3.00", forma: str = "proporcional_por_dia") -> None:
    m.ejecutar(
        "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, vigente_desde, "
        "tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, porcentaje_fondo, "
        "dia_de_vencimiento, modalidad_de_vencimiento) VALUES (%s, %s, %s, %s, %s, '500.00', 0, %s, '5.00', 10, "
        "'unico')", (m.admin, m.edificio, m.personas["super_admin"], desde, tasa, forma))


def ajustes(m: Mundo, unidad: str) -> list[tuple[str, Any]]:
    """(importe, enlazado_a) de los `ajuste_de_interes` de la cuenta."""
    return [(str(f[0]), f[1]) for f in m.filas(
        "SELECT importe::text, enlazado_a FROM movimiento WHERE cuenta_id = %s AND tipo = 'ajuste_de_interes' "
        "ORDER BY registrado_en", (cuenta_de(m, unidad),))]


def interes_de(m: Mundo, unidad: str, emision_id: UUID, periodo_de_la_obligacion: date) -> UUID:
    filas = m.filas(
        "SELECT mv.id FROM movimiento mv JOIN obligacion o ON o.id = mv.obligacion_id "
        "WHERE mv.cuenta_id = %s AND mv.tipo = 'interes' AND mv.emision_id = %s AND o.periodo = %s",
        (cuenta_de(m, unidad), emision_id, periodo_de_la_obligacion))
    assert len(filas) == 1, f"{unidad}: se esperaba un interés de la obligación {periodo_de_la_obligacion}: {filas}"
    return UUID(str(filas[0][0]))


def credito_directo(m: Mundo, unidad: str, importe: str, fecha: date) -> None:
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


def ordenes(m: Mundo, movimiento_id: Any) -> list[int]:
    return [int(f[0]) for f in m.filas("SELECT orden FROM imputacion WHERE movimiento_id = %s", (movimiento_id,))]
