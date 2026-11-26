"""Ayudas de la aceptación de H-031 (deuda previa a nombre del vendedor, change 4d `cambio-de-titular`, R32, D-168).
Mundo de H-027 (Torre Ficticia) con dos propietarios en `2A`. Caja negra por la API real
(`aceptacion/H-031/CONTRATO.md`) con la identidad inyectada. Lo que todavía no existe (la ruta, la tabla
`cambio_de_titular`) se pide con un `assert` y un mensaje, nunca con un error de setup.

Base: "Torre Ficticia", `1A` 0,30, `1B` 0,30, `2A` 0,25 y `2B` 0,15. "Ana Prueba" (con email) es propietaria de
`1A` y `2B`; "Carla Prueba" propietaria de `1B` y "Beto Prueba" su inquilino; "Dora Prueba" (con email) y "Edu
Prueba" (sin email) copropietarios de `2A`.
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

#: Hoy está fijo (como en H-027): la fecha de un cambio se prueba contra él, no contra el reloj.
HOY = date(2026, 12, 15)
SEP, OCT, NOV, DIC = (date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1))
UNIDADES = {"1A": "0.300000", "1B": "0.300000", "2A": "0.250000", "2B": "0.150000"}
#: Ordinaria mensual de cada unidad en la base de los ejemplos.
MENSUAL = {"1A": "10000.00", "1B": "40000.00", "2A": "5000.00", "2B": "8000.00"}
EMAIL_DE_ANA = "ana.prueba@ejemplo.invalid"
EMAIL_DE_DORA = "dora.prueba@ejemplo.invalid"
FECHA = "2026-11-10"
CLAVES_DEL_CAMBIO = {"id", "unidad_id", "fecha", "vendedores", "compradores", "expensa_del_mes", "deuda_previa",
                     "registrado_por", "registrado_en", "aviso"}
#: Con `deuda_previa: "a_nombre_del_vendedor"` la respuesta suma estas dos.
CLAVES_DEL_TRASLADO = CLAVES_DEL_CAMBIO | {"trasladado", "cuenta_del_vendedor"}
A_NOMBRE = "a_nombre_del_vendedor"


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
    from proptech_api.morosidad import hoy

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
            personas["dora"] = _vecino(conexion, admin, edificio, "Dora Prueba", [(ids["2A"], "propietario")],
                                       EMAIL_DE_DORA)
            personas["edu"] = _vecino(conexion, admin, edificio, "Edu Prueba", [(ids["2A"], "propietario")])
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
        m.como("admin_principal")
        _fijar_hoy(app)
        try:
            yield m
        finally:
            app.dependency_overrides.clear()


# --- El libro ------------------------------------------------------------------------------------------


def emitir(m: Mundo, periodo: date, unidades: tuple[str, ...] = tuple(UNIDADES),
           importes: dict[str, str] | None = None) -> UUID:
    """Una emisión del libro con la ordinaria de `MENSUAL` (o la de `importes`), vencimiento el día 10."""
    mensual = {**MENSUAL, **(importes or {})}
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import emisiones
    from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

    emision_id = uuid4()
    with sesion_app(m.base, m.admin) as s:
        emisiones.registrar_emision(
            s, m.identidad(), emision_id=emision_id, complejo_id=m.edificio, periodo=periodo,
            obligaciones=[ObligacionAEmitir(m.unidades[u], periodo.replace(day=10), Dinero(mensual[u]),
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


def del_libro(m: Mundo, tablas: tuple[str, ...] = ("movimiento", "imputacion", "obligacion", "cuenta",
                                                    "emision")) -> dict[str, tuple[int, str]]:
    """Filas y contenido de las tablas del libro de esta administración, con el superusuario (sin RLS, L-092)."""
    c = m.base.contenedor
    with psycopg.connect(host=c.get_container_host_ip(), port=c.get_exposed_port(5432), dbname=m.base.nombre,
                         user=c.username, password=c.password, autocommit=True) as conexion:
        resultado = {}
        for tabla in tablas:
            fila = conexion.execute(
                f"SELECT count(*), coalesce(md5(string_agg(t::text, '|' ORDER BY t::text)), '') "  # noqa: S608
                f"FROM public.{tabla} t WHERE t.administracion_id = %s", (m.admin,)
            ).fetchone()
            assert fila is not None
            resultado[tabla] = (int(fila[0]), str(fila[1]))
        return resultado


def superusuario(m: Mundo, consulta: str, parametros: tuple[Any, ...] = ()) -> list[Any]:
    """Una consulta con el superusuario (sin RLS, L-092)."""
    c = m.base.contenedor
    with psycopg.connect(host=c.get_container_host_ip(), port=c.get_exposed_port(5432), dbname=m.base.nombre,
                         user=c.username, password=c.password, autocommit=True) as conexion:
        return list(conexion.execute(consulta, parametros).fetchall())  # type: ignore[arg-type]


def deuda_del_libro(m: Mundo, unidad: str) -> str:
    """La deuda de la cuenta de la unidad según `estado_de_cuenta` del libro, como texto."""
    from proptech_core.cuenta_corriente.aplicacion import lecturas

    with sesion_app(m.base, m.admin) as s:
        return str(lecturas.estado_de_cuenta(s, cuenta_id=cuenta_de(m, unidad)).deuda.a_texto())


def sembrar_deuda(m: Mundo, unidad: str = "1A") -> str:
    """`unidad` con deuda: septiembre y octubre emitidos y sin pagar (con el interés de septiembre registrado).
    Devuelve la deuda del libro."""
    emitir(m, SEP, (unidad,))
    emitir(m, OCT, (unidad,))
    deuda = deuda_del_libro(m, unidad)
    assert Decimal(deuda) > Decimal(MENSUAL[unidad]), f"precondición: `{unidad}` debe más que un mes: {deuda}"
    return deuda


# --- Las personas --------------------------------------------------------------------------------------


def duenos(m: Mundo, unidad: str, vinculo: str = "propietario") -> set[UUID]:
    """Las personas con asignación `vecino` de ese vínculo sobre la unidad."""
    return {UUID(str(f[0])) for f in m.filas(
        "SELECT persona_id FROM asignacion_rol WHERE rol = 'vecino' AND vinculo = %s AND unidad_id = %s",
        (vinculo, m.unidades[unidad]))}


def asignaciones(m: Mundo) -> list[tuple[str, ...]]:
    """Todas las asignaciones de la administración, ordenadas (para comparar antes y después)."""
    return sorted(tuple(str(x) for x in f) for f in m.filas(
        "SELECT persona_id, rol, complejo_id, unidad_id, vinculo FROM asignacion_rol"))


def personas_con_nombre(m: Mundo, nombre: str) -> list[Any]:
    return m.filas("SELECT id, email FROM persona WHERE nombre = %s", (nombre,))


def auditorias(m: Mundo, accion: str = "registrar_cambio_de_titular") -> list[Any]:
    """(entidad, entidad_id, persona_id, detalle) de la administración de este mundo (L-092)."""
    return superusuario(m, "SELECT entidad, entidad_id, persona_id, detalle FROM auditoria WHERE accion = %s "
                           "AND administracion_id = %s", (accion, m.admin))


def filas_del_cambio(m: Mundo) -> int:
    """Las filas de `cambio_de_titular` de la administración; pide con un `assert` que la tabla exista."""
    existe = superusuario(m, "SELECT to_regclass('public.cambio_de_titular') IS NOT NULL")[0][0]
    assert existe, "falta la tabla `cambio_de_titular` (la crea la migración del 4d)"
    return int(superusuario(m, "SELECT count(*) FROM cambio_de_titular WHERE administracion_id = %s",
                            (m.admin,))[0][0])


# --- La API --------------------------------------------------------------------------------------------


def ruta(m: Mundo, unidad: str = "1A", complejo: UUID | None = None, unidad_id: UUID | None = None) -> str:
    return (f"/api/complejos/{complejo or m.edificio}/unidades/{unidad_id or m.unidades[unidad]}"
            "/cambios-de-titular")


def cuerpo(vendedores: list[UUID], compradores: list[dict[str, Any]] | None = None, fecha: str = FECHA,
           **opciones: Any) -> dict[str, Any]:
    nuevos = compradores if compradores is not None else [{"nombre": "Nora Compradora", "email": None}]
    return {"fecha": fecha, "vendedores": [str(v) for v in vendedores], "compradores": nuevos, **opciones}


def registrar(m: Mundo, unidad: str, vendedores: list[UUID], compradores: list[dict[str, Any]] | None = None,
              fecha: str = FECHA, **opciones: Any) -> Any:
    return m.cliente.post(ruta(m, unidad), json=cuerpo(vendedores, compradores, fecha, **opciones))


def registrar_ok(m: Mundo, unidad: str, vendedores: list[UUID], compradores: list[dict[str, Any]] | None = None,
                 fecha: str = FECHA, **opciones: Any) -> dict[str, Any]:
    r = registrar(m, unidad, vendedores, compradores, fecha, **opciones)
    assert r.status_code == 201, f"se esperaba 201, llegó {r.status_code}: {r.text[:300]}"
    return dict(r.json())


def listar(m: Mundo, unidad: str = "1A") -> Any:
    return m.cliente.get(ruta(m, unidad))


def sin_permiso(r: Any, accion: str = "registrar_cambio_de_titular") -> None:
    assert r.status_code == 403, f"se esperaba 403, llegó {r.status_code}: {r.text[:300]}"
    detalle = r.json().get("detail")
    assert isinstance(detalle, dict) and detalle.get("permiso_faltante") == accion, r.json()


def no_encontrado(r: Any) -> None:
    assert r.status_code == 404, f"se esperaba 404, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == {"detail": "no encontrado"}, r.json()


def no_procesable(r: Any) -> None:
    assert r.status_code == 422, f"se esperaba 422, llegó {r.status_code}: {r.text[:300]}"


# --- H-031: el traslado entre cuentas ------------------------------------------------------------------


def dinero(texto: Any) -> Decimal:
    return Decimal(str(texto))


def estado(m: Mundo, cuenta_id: UUID) -> Any:
    """El `EstadoDeCuenta` del libro de esa cuenta (de unidad o de persona)."""
    from proptech_core.cuenta_corriente.aplicacion import lecturas

    with sesion_app(m.base, m.admin) as s:
        return lecturas.estado_de_cuenta(s, cuenta_id=cuenta_id)


def desglose(m: Mundo, unidad: str, corte: date = NOV) -> dict[str, Decimal]:
    """Lo impago de la unidad según el libro, partido en lo anterior al período `corte` y lo de `corte` en
    adelante; `previo_interes` es el interés registrado de lo anterior."""
    e = estado(m, cuenta_de(m, unidad))
    previo = posterior = previo_interes = Decimal("0.00")
    for (obligacion, componente), residual in e.residual.items():
        monto = dinero(residual.a_texto())
        if next(o for o in e.obligaciones if o.id == obligacion).periodo < corte:
            previo += monto
            if getattr(componente, "value", componente) == "interes":
                previo_interes += monto
        else:
            posterior += monto
    return {"previo": previo, "posterior": posterior, "previo_interes": previo_interes,
            "deuda": dinero(e.deuda.a_texto())}


def residuales_anteriores(m: Mundo, unidad: str, corte: date = NOV) -> dict[tuple[str, str], Decimal]:
    """(período, componente) -> impago, sólo de los períodos anteriores a `corte` con algo impago."""
    e = estado(m, cuenta_de(m, unidad))
    salida: dict[tuple[str, str], Decimal] = {}
    for (obligacion, componente), residual in e.residual.items():
        periodo = next(o for o in e.obligaciones if o.id == obligacion).periodo
        if periodo < corte and dinero(residual.a_texto()) != 0:
            salida[(periodo.isoformat(), str(getattr(componente, "value", componente)))] = dinero(
                residual.a_texto())
    return salida


def deuda_de_cuenta(m: Mundo, cuenta_id: UUID) -> Decimal:
    return dinero(estado(m, cuenta_id).deuda.a_texto())


def cuentas_de_persona(m: Mundo, persona: UUID) -> list[UUID]:
    return [UUID(str(f[0])) for f in superusuario(
        m, "SELECT id FROM cuenta WHERE persona_id = %s AND administracion_id = %s", (persona, m.admin))]


def movimientos(m: Mundo, cuenta_id: UUID, tipo: str | None = None) -> list[dict[str, Any]]:
    """Los movimientos de la cuenta (de un tipo, si se pide), con el superusuario (sin RLS, L-092)."""
    filas = superusuario(
        m, "SELECT id, tipo, sentido, importe, obligacion_id, componente, enlazado_a, operacion_id "
           "FROM movimiento WHERE cuenta_id = %s AND administracion_id = %s AND (%s::text IS NULL OR tipo = %s) "
           "ORDER BY registrado_en, id", (cuenta_id, m.admin, tipo, tipo))
    return [dict(zip(("id", "tipo", "sentido", "importe", "obligacion_id", "componente", "enlazado_a",
                      "operacion_id"), f, strict=True)) for f in filas]


def periodos_de_obligaciones(m: Mundo, cuenta_id: UUID) -> dict[UUID, date]:
    return {UUID(str(f[0])): f[1] for f in superusuario(
        m, "SELECT id, periodo FROM obligacion WHERE cuenta_id = %s", (cuenta_id,))}


def traslados(m: Mundo) -> list[Any]:
    """Todos los movimientos `traslado` de la administración (id, cuenta, sentido, importe, obligación, enlace)."""
    return superusuario(
        m, "SELECT id, cuenta_id, sentido, importe, obligacion_id, enlazado_a, operacion_id FROM movimiento "
           "WHERE tipo = 'traslado' AND administracion_id = %s ORDER BY registrado_en, id", (m.admin,))


def sembrar(m: Mundo, unidades: tuple[str, ...] = ("1A",), parcial: bool = True,
            hasta: date = NOV) -> dict[str, Decimal]:
    """Septiembre, octubre y noviembre (hasta `hasta`) emitidos y sin pagar en `unidades`, todas con la ordinaria
    de 10.000 (para compararlas). En `1A`, un pago parcial de 3.000 el 20/10, antes de noviembre. Devuelve el
    desglose de `1A` (o de la primera). La precondición de cada test: hay interés registrado anterior a noviembre."""
    importes = {u: "10000.00" for u in unidades}
    emitir(m, SEP, unidades, importes)
    emitir(m, OCT, unidades, importes)
    if parcial:
        pagar(m, unidades[0], "3000.00", date(2026, 10, 20))
    if hasta >= NOV:
        emitir(m, NOV, unidades, importes)
    d = desglose(m, unidades[0])
    assert d["previo_interes"] > 0, f"precondición: interés registrado anterior a noviembre: {d}"
    assert d["previo"] > d["previo_interes"] and d["posterior"] > 0, f"precondición: {d}"
    return d


def trasladar(m: Mundo, unidad: str, vendedores: list[UUID], deudor: UUID | None = None,
              compradores: list[dict[str, Any]] | None = None, fecha: str = FECHA) -> dict[str, Any]:
    """Registra el cambio con la deuda previa a nombre del vendedor (201 esperado)."""
    opciones: dict[str, Any] = {"deuda_previa": A_NOMBRE}
    if deudor is not None:
        opciones["vendedor_deudor"] = str(deudor)
    return registrar_ok(m, unidad, vendedores, compradores, fecha, **opciones)


def cuenta_del_vendedor(cambio: dict[str, Any]) -> UUID:
    assert "cuenta_del_vendedor" in cambio and cambio["cuenta_del_vendedor"], f"sin cuenta del vendedor: {cambio}"
    return UUID(str(cambio["cuenta_del_vendedor"]))


def todo(m: Mundo) -> dict[str, Any]:
    """Lo que un pedido que falla no debe tocar: el libro entero, las asignaciones, las personas, los cambios
    y las auditorías."""
    return {"libro": del_libro(m), "asignaciones": asignaciones(m),
            "personas": m.filas("SELECT count(*) FROM persona")[0][0], "cambios": filas_del_cambio(m),
            "auditorias": len(auditorias(m))}
