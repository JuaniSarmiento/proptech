"""Ayudas de la aceptación de H-041 (el certificado de libre deuda, change 10b, R21, D-171, D-172).

Caja negra por la API real (`aceptacion/H-041/CONTRATO.md`) con la identidad inyectada. El libro se arma con
`registrar_emision` y `registrar_credito` (como H-027) y los pagos informados por la API de pagos (como H-038). Lo que
todavía no existe (la ruta, `proptech_api.libre_deuda`, la tabla) se pide con un `assert` y un mensaje, nunca con un
error de setup.

Base (inventada): "Torre Ficticia", `1A` 0,30, `1B` 0,30, `2A` 0,25 y `2B` 0,15; 3% mensual proporcional, gracia 0,
vencimiento el día 10. Septiembre, octubre y noviembre emitidos (`MENSUAL`: 1A 10.000, 1B 40.000, 2A 5.000, 2B 8.000).
"Ana Prueba" es propietaria de `1A` y `2B`. Hoy es el 18/11/2026.

  1A  no paga nada: capital vencido al 05/11 de 20.000,00 más sus intereses registrados.
  1B  paga septiembre y octubre antes de vencer: al 05/11 no debe nada (noviembre vence el 10).
  2B  P1 8.000,00 transferidos el 20/10 y confirmados el 18/11 (cuentan el 20/10); P2 3.000,00 transferidos el 02/11
      e informados sin confirmar; P3 1.000,00 transferidos el 12/11 y confirmados el 18/11.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
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
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + bytes(64)
NO_ENCONTRADO = {"detail": "no encontrado"}
MONTO = re.compile(r"^-?[0-9]+\.[0-9]{2}$")
HUELLA = re.compile(r"^[0-9a-f]{64}$")
CLAVES_DEL_CERTIFICADO = {
    "id", "unidad_id", "fecha_de_corte", "emitido_en", "saldo", "capital", "intereses", "interes_corrido",
    "libre_de_deuda", "en_revision", "vencen_despues", "huella", "en_gestion_judicial", "enlace",
}
CLAVES_DE_UN_PAGO_EN_REVISION = {"pago_id", "importe", "fecha_de_transferencia", "banco", "numero_de_operacion"}
CLAVES_DE_UNA_CUOTA = {"periodo", "vencimiento", "importe"}
CLAVES_DEL_ENLACE = {"url", "vence_en"}
ROLES = ("super_admin", "admin_principal", "admin_del_edificio", "admin_de_otro_edificio", "contador", "auxiliar",
         "consejo")


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
    """La fecha de las lecturas de plata es una dependencia (L-090): la de pagos, la de morosidad y la del libre deuda."""
    for modulo in ("proptech_api.pagos", "proptech_api.morosidad", "proptech_api.libre_deuda"):
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


# --- Los pagos informados (los de H-022) ---------------------------------------------------------------


def ruta_pagos(m: Mundo, sufijo: str = "") -> str:
    return f"/api/complejos/{m.edificio}/pagos{sufijo}"


def informar_ok(m: Mundo, partes: dict[str, str], *, numero: str, fecha: str, banco: str = "Banco Nación") -> str:
    """Informa un pago como la persona que está en sesión; devuelve su `pago_id`."""
    r = m.cliente.post(ruta_pagos(m, "/lectura"), files={"archivo": ("comprobante.png", PNG, "image/png")})
    assert r.status_code == 201, f"subir el comprobante: se esperaba 201, llegó {r.status_code}: {r.text[:300]}"
    total = sum((Decimal(v) for v in partes.values()), Decimal("0.00"))
    cuerpo = {
        "comprobante_id": str(r.json()["comprobante_id"]), "banco": banco, "numero_de_operacion": numero,
        "fecha_de_transferencia": fecha, "monto": f"{total:.2f}", "cbu_origen": None,
        "partes": [{"unidad_id": str(m.unidades[u]), "importe": i} for u, i in partes.items()],
    }
    r = m.cliente.post(ruta_pagos(m), json=cuerpo)
    assert r.status_code == 201, f"informar: se esperaba 201, llegó {r.status_code}: {r.text[:300]}"
    assert r.json().get("estado") == "informado", r.json()
    return str(r.json()["pago_id"])


def resolver_como_administrador(m: Mundo, pago_id: str, sufijo: str, cuerpo: dict[str, Any], *, volver_a: str) -> None:
    m.como("admin_principal")
    r = m.cliente.post(ruta_pagos(m, f"/{pago_id}/{sufijo}"), json=cuerpo)
    assert r.status_code == 200, f"{sufijo}: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    m.como(volver_a)


def confirmar(m: Mundo, pago_id: str) -> None:
    resolver_como_administrador(m, pago_id, "confirmacion", {}, volver_a="super_admin")


def rechazar(m: Mundo, pago_id: str) -> None:
    resolver_como_administrador(m, pago_id, "rechazo", {"motivo": "El monto no coincide"}, volver_a="super_admin")


def informar_como_ana(m: Mundo, importe: str, *, numero: str, fecha: str) -> str:
    m.como("ana")
    try:
        return informar_ok(m, {"2B": importe}, numero=numero, fecha=fecha)
    finally:
        m.como("super_admin")


def armar_la_deuda(m: Mundo) -> None:
    """Septiembre, octubre y noviembre emitidos; los pagos de `1B` y de `2B` en el orden que dice el módulo."""
    emitir(m, SEP)
    pagar(m, "1B", MENSUAL["1B"], date(2026, 9, 5))
    emitir(m, OCT)
    pagar(m, "1B", MENSUAL["1B"], date(2026, 10, 5))
    p1 = informar_como_ana(m, "8000.00", numero="OP-0001", fecha="2026-10-20")
    confirmar(m, p1)
    emitir(m, NOV)
    m.pagos["P1"] = p1
    m.pagos["P2"] = informar_como_ana(m, "3000.00", numero="OP-0002", fecha="2026-11-02")
    m.pagos["P3"] = informar_como_ana(m, "1000.00", numero="OP-0003", fecha="2026-11-12")
    confirmar(m, m.pagos["P3"])


# --- La API (CONTRATO.md) ------------------------------------------------------------------------------


def ruta(m: Mundo, unidad: str | UUID, complejo: UUID | None = None) -> str:
    uid = unidad if isinstance(unidad, UUID) else m.unidades[unidad]
    return f"/api/complejos/{complejo or m.edificio}/unidades/{uid}/libre-deuda"


def pedir(m: Mundo, unidad: str | UUID, corte: date | str, complejo: UUID | None = None) -> Any:
    valor = corte.isoformat() if isinstance(corte, date) else corte
    return m.cliente.post(ruta(m, unidad, complejo), json={"fecha_de_corte": valor})


def verificar_forma(c: Any) -> dict[str, Any]:
    assert isinstance(c, dict), f"el certificado tiene que ser un objeto: {c!r}"
    assert set(c) == CLAVES_DEL_CERTIFICADO, f"las claves del certificado: {sorted(c)}"
    UUID(c["id"])
    assert HUELLA.match(c["huella"]), c["huella"]
    for clave in ("saldo", "capital", "intereses", "interes_corrido"):
        assert isinstance(c[clave], str) and MONTO.match(c[clave]), f"{clave} es texto con dos decimales: {c[clave]!r}"
    assert Decimal(c["saldo"]) == Decimal(c["capital"]) + Decimal(c["intereses"]), c
    assert c["libre_de_deuda"] is (Decimal(c["saldo"]) == 0), c
    assert isinstance(c["en_revision"], list) and isinstance(c["vencen_despues"], list), c
    for p in c["en_revision"]:
        assert set(p) == CLAVES_DE_UN_PAGO_EN_REVISION, f"las claves de un pago en revisión: {sorted(p)}"
    for q in c["vencen_despues"]:
        assert set(q) == CLAVES_DE_UNA_CUOTA, f"las claves de una cuota: {sorted(q)}"
    assert set(c["enlace"]) == CLAVES_DEL_ENLACE, c["enlace"]
    return dict(c)


def emitir_certificado(m: Mundo, unidad: str, corte: date) -> dict[str, Any]:
    r = pedir(m, unidad, corte)
    assert r.status_code == 201, f"emitir el libre deuda: se esperaba 201, llegó {r.status_code}: {r.text[:300]}"
    return verificar_forma(r.json())


def listar(m: Mundo, unidad: str) -> list[dict[str, Any]]:
    r = m.cliente.get(ruta(m, unidad))
    assert r.status_code == 200, f"listar los certificados: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    lista = r.json()
    assert isinstance(lista, list), f"la lista de certificados tiene que ser una lista: {lista!r}"
    return [verificar_forma(c) for c in lista]


def bajar_el_pdf(m: Mundo, certificado: dict[str, Any]) -> bytes:
    r = m.cliente.get(certificado["enlace"]["url"])
    assert r.status_code == 200, f"bajar el PDF: se esperaba 200, llegó {r.status_code}: {r.text[:200]}"
    assert r.headers["content-type"].startswith("application/pdf"), r.headers["content-type"]
    assert r.content.startswith(b"%PDF"), r.content[:20]
    return bytes(r.content)


def texto_del_pdf(contenido: bytes) -> str:
    import io

    from pypdf import PdfReader

    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(contenido)).pages)


def ars(monto: str) -> str:
    """`20407.23` como lo imprime el PDF: `20.407,23`."""
    entero, decimales = monto.split(".")
    con_puntos = f"{int(entero):,}".replace(",", ".")
    return f"{con_puntos},{decimales}"


def sin_espacios(texto: str) -> str:
    return "".join(texto.split())


def firmar_enlace(m: Mundo, certificado_id: str, *, vence_en: datetime, tipo: str = "libre_deuda") -> str:
    """Un token como el que firma el servidor para un certificado (CONTRATO.md: tipo `libre_deuda`, datos `a` e `i`)."""
    from proptech_core.compartido.enlaces import firmar

    token = firmar(tipo, {"a": str(m.admin), "i": certificado_id}, vence_en=vence_en, clave=CLAVE_DE_ENLACES)
    return f"/api/libre-deuda/descarga?token={token}"


def en_cinco_minutos() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=5)


def no_encontrado(r: Any, donde: str) -> None:
    assert r.status_code == 404, f"{donde}: se esperaba 404, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == NO_ENCONTRADO, f"{donde}: el 404 tiene que ser {NO_ENCONTRADO}, llegó {r.json()}"


def sin_permiso(r: Any, donde: str) -> None:
    assert r.status_code == 403, f"{donde}: se esperaba 403, llegó {r.status_code}: {r.text[:300]}"
    detalle = r.json().get("detail")
    assert isinstance(detalle, dict) and detalle.get("permiso_faltante") == "emitir_libre_deuda", (
        f"{donde}: el 403 tiene que decir `emitir_libre_deuda`: {r.json()}")


# --- Lo que el libro dice (el oráculo) -----------------------------------------------------------------


def superusuario(m: Mundo, consulta: str, parametros: tuple[Any, ...] = ()) -> list[Any]:
    """Una consulta con el superusuario (sin RLS, L-092)."""
    c = m.base.contenedor
    with psycopg.connect(host=c.get_container_host_ip(), port=c.get_exposed_port(5432), dbname=m.base.nombre,
                         user=c.username, password=c.password, autocommit=True) as conexion:
        return list(conexion.execute(consulta, parametros).fetchall())  # type: ignore[arg-type]


def del_libro_a(m: Mundo, unidad: str, corte: date) -> dict[str, Decimal]:
    """Lo que el libro sabía de la unidad a la fecha de corte, leído de las tablas (no del código del módulo):
    capital de las obligaciones con vencimiento hasta el corte, intereses registrados con fecha valor hasta el
    corte y pagos con fecha valor hasta el corte. `saldo = capital + intereses - pagos` (sirve mientras ningún
    pago exceda lo debido, como en estos ejemplos)."""
    cuenta = cuenta_de(m, unidad)
    capital = m.uno("SELECT coalesce(sum(ordinaria + fondo_de_reserva + extraordinaria), 0)::text FROM obligacion "
                    "WHERE cuenta_id = %s AND vencimiento <= %s", (cuenta, corte))
    intereses = m.uno("SELECT coalesce(sum(importe), 0)::text FROM movimiento WHERE cuenta_id = %s "
                      "AND tipo = 'interes' AND fecha_valor <= %s", (cuenta, corte))
    pagos = m.uno("SELECT coalesce(sum(importe), 0)::text FROM movimiento WHERE cuenta_id = %s "
                  "AND tipo = 'pago' AND sentido = 'credito' AND fecha_valor <= %s", (cuenta, corte))
    return {"capital": Decimal(capital), "intereses": Decimal(intereses), "pagos": Decimal(pagos),
            "saldo": Decimal(capital) + Decimal(intereses) - Decimal(pagos)}


def texto_de(valor: Decimal) -> str:
    return f"{valor:.2f}"


def del_libro(m: Mundo) -> dict[str, tuple[int, str]]:
    """Filas y contenido del libro (`movimiento`, `imputacion`, `obligacion`, `cuenta`, `pago_informado`) de esta
    administración, con el superusuario (sin RLS, L-092)."""
    resultado = {}
    for tabla in ("movimiento", "imputacion", "obligacion", "cuenta"):
        fila = superusuario(
            m, f"SELECT count(*), coalesce(md5(string_agg(t::text, '|' ORDER BY t::text)), '') "  # noqa: S608
               f"FROM public.{tabla} t WHERE t.administracion_id = %s", (m.admin,))[0]
        resultado[tabla] = (int(fila[0]), str(fila[1]))
    return resultado


def filas_de_certificados(m: Mundo) -> int:
    """Las filas de `certificado_de_libre_deuda` de la administración; pide con un `assert` que la tabla exista."""
    existe = superusuario(m, "SELECT to_regclass('public.certificado_de_libre_deuda') IS NOT NULL")[0][0]
    assert existe, "falta la tabla `certificado_de_libre_deuda` (la crea la migración del 10b)"
    return int(superusuario(m, "SELECT count(*) FROM certificado_de_libre_deuda WHERE administracion_id = %s",
                            (m.admin,))[0][0])


def auditorias(m: Mundo, accion: str = "emitir_libre_deuda") -> list[Any]:
    """(entidad, entidad_id, persona_id, detalle) de la administración de este mundo (L-092)."""
    return superusuario(m, "SELECT entidad, entidad_id, persona_id, detalle FROM auditoria WHERE accion = %s "
                           "AND administracion_id = %s", (accion, m.admin))


def cargo_sin_liquidar(m: Mundo, unidad: str, importe: str) -> None:
    """Un cargo particular aprobado de noviembre que todavía no se liquidó (no está en el libro)."""
    m.ejecutar(
        "INSERT INTO cargo_particular (administracion_id, complejo_id, unidad_id, concepto, importe, periodo, "
        "motivo, estado) VALUES (%s, %s, %s, 'Multa sin liquidar', %s, %s, 'Motivo ficticio', 'aprobado')",
        (m.admin, m.edificio, m.unidades[unidad], importe, NOV))


def interes_corrido_del_libro(m: Mundo, unidad: str, corte: date) -> Decimal:
    """El interés de R03 que el libro todavía no registró hasta `corte`, por el cálculo de dominio que usa la emisión
    (`calcular_intereses_del_corte`, 4c): la suma de lo que cobraría un corte en esa fecha. No escribe."""
    from proptech_core.cuenta_corriente.aplicacion import emisiones, lecturas

    cuenta = cuenta_de(m, unidad)
    with sesion_app(m.base, m.admin) as s:
        foto = lecturas.foto(s, cuenta)
        _, calculados = emisiones.calcular_intereses_del_corte(s, m.edificio, corte, {cuenta: foto})
        return sum((i.importe.decimal for i in calculados.get(cuenta, [])), Decimal("0.00"))
