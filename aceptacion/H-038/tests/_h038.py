"""Ayudas de la aceptación de H-038 (lo que debo y lo que pagué, change 11 `portal-del-vecino`, D-170).

Caja negra por la API real (`aceptacion/H-038/CONTRATO.md`) con la identidad inyectada. La base de los ejemplos sale
de H-015 (la emisión de noviembre por el camino real, con sus PDFs) y de H-022 (informar y confirmar pagos). Lo que
todavía no existe (las rutas, `proptech_api.vecino`) se pide con un `assert` y un mensaje, nunca con un error de setup.

Base (inventada): "Torre Ficticia" con `1A`, `1B`, `2A` y `2B` y "Otro Edificio Ficticio" con `9A`. "Ana Prueba" es
propietaria de `1A`, `2B` y `9A` (dos edificios); "Carla Prueba", propietaria de `1B`; "Beto Prueba", inquilino de
`1B`; "Dora Prueba", propietaria de `2A`. Noviembre de 2026 emitido (vencimiento 10/11): `1A` 43.350,00, `1B`
48.350,00 (33.350,00 sin la extraordinaria de 15.000,00), `2A` 62.375,00 y `2B` 37.425,00. Hoy es el 18/11/2026.
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

CLAVE_DE_ENLACES = "clave-de-prueba-de-enlaces-firmados-0123456789"
HOY = date(2026, 11, 18)
UNIDADES = {"1A": "0.300000", "1B": "0.300000", "2A": "0.250000", "2B": "0.150000"}
SEP, OCT, NOV, DIC = (date(2026, m, 1) for m in (9, 10, 11, 12))
PROPORCIONAL = "proporcional_por_dia"
#: Lo emitido en noviembre por unidad: ordinaria (con cargos), fondo, extraordinaria (H-011).
EMITIDO = {
    "1A": ("27000.00", "1350.00", "15000.00"),
    "1B": ("32000.00", "1350.00", "15000.00"),
    "2A": ("47500.00", "2375.00", "12500.00"),
    "2B": ("28500.00", "1425.00", "7500.00"),
}
CLAVES_DE_UNIDAD = {
    "unidad_id", "identificador", "vinculo", "complejo_id", "edificio", "total_a_pagar", "vencimiento",
    "deuda_anterior", "intereses", "credito_aplicable", "credito_retenido",
}
CLAVES_DEL_CONJUNTO = {"total_a_pagar", "intereses", "credito_aplicable", "credito_retenido"}
CLAVES_DE_PAGO = {"pago_id", "fecha_de_transferencia", "importe", "banco", "numero_de_operacion"}
CLAVES_DE_DOCUMENTO = {"documento_id", "liquidacion_id", "complejo_id", "periodo", "variante", "url", "vence_en"}
CLAVES_DE_CARGO = {"id", "complejo_id", "unidad_id", "concepto", "importe", "periodo", "motivo", "estado"}
NO_ENCONTRADO = {"detail": "no encontrado"}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + bytes(64)


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
    generales: UUID = field(default_factory=uuid4)
    ascensor: UUID = field(default_factory=uuid4)
    generales_otro: UUID = field(default_factory=uuid4)
    categorias: dict[str, UUID] = field(default_factory=dict)
    categoria_otro: UUID = field(default_factory=uuid4)
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

    def filas(self, consulta: str, parametros: tuple[Any, ...] = ()) -> list[Any]:
        with self.base.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, self.admin)
            return list(conexion.execute(consulta, parametros).fetchall())

    def uno(self, consulta: str, parametros: tuple[Any, ...] = ()) -> Any:
        return self.filas(consulta, parametros)[0][0]

    def ejecutar(self, consulta: str, parametros: tuple[Any, ...] = ()) -> Any:
        with self.base.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, self.admin)
            cursor = conexion.execute(consulta, parametros)
            return cursor.fetchone() if cursor.description else None


def _grupo(
    conexion: psycopg.Connection, admin: UUID, complejo: UUID, clave: str, nombre: str, *,
    es_generales: bool = False,
) -> UUID:
    fila = conexion.execute(
        "INSERT INTO grupo_de_reparto (administracion_id, complejo_id, clave, nombre, metodo, es_generales) "
        "VALUES (%s, %s, %s, %s, 'coeficiente', %s) RETURNING id",
        (admin, complejo, clave, nombre, es_generales),
    ).fetchone()
    assert fila is not None
    return UUID(str(fila[0]))


def _categoria(
    conexion: psycopg.Connection, admin: UUID, complejo: UUID, clave: str, nombre: str, orden: int
) -> UUID:
    fila = conexion.execute(
        "INSERT INTO categoria_de_gasto (administracion_id, complejo_id, clave, nombre, orden) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (admin, complejo, clave, nombre, orden),
    ).fetchone()
    assert fila is not None
    return UUID(str(fila[0]))


def _vecino(
    conexion: psycopg.Connection, admin: UUID, nombre: str, unidades: list[tuple[UUID, UUID, str]]
) -> UUID:
    """`unidades`: (edificio, unidad, vínculo)."""
    persona = uuid4()
    conexion.execute("INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, %s)",
                     (persona, admin, nombre))
    for edificio, unidad, vinculo in unidades:
        conexion.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id, unidad_id, vinculo) "
            "VALUES (%s, %s, 'vecino', %s, %s, %s)",
            (admin, persona, edificio, unidad, vinculo),
        )
    return persona


def _fijar_hoy(app: FastAPI) -> None:
    """La fecha de las lecturas de plata es una dependencia (L-090): la de pagos, la de morosidad y la del portal."""
    for modulo in ("proptech_api.pagos", "proptech_api.morosidad", "proptech_api.vecino"):
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
    roles = ("super_admin", "admin_principal", "admin_del_edificio", "admin_de_otro_edificio", "contador",
             "auxiliar", "consejo")
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
            generales = _grupo(conexion, admin, edificio, "generales", "Generales", es_generales=True)
            ascensor = _grupo(conexion, admin, edificio, "ascensor", "Ascensor")
            for u in ("2A", "2B"):
                conexion.execute(
                    "INSERT INTO grupo_unidad (administracion_id, complejo_id, grupo_id, unidad_id, "
                    "modo_de_coeficientes, coeficiente) VALUES (%s, %s, %s, %s, 'renormalizado', NULL)",
                    (admin, edificio, ascensor, ids[u]))
            generales_otro = _grupo(conexion, admin, otro, "generales", "Generales", es_generales=True)
            categorias = {
                nombre: _categoria(conexion, admin, edificio, nombre.lower(), nombre, n)
                for n, nombre in enumerate(("Limpieza", "Ascensor", "Pintura", "Seguridad"))
            }
            categoria_otro = _categoria(conexion, admin, otro, "limpieza", "Limpieza", 0)
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
            personas["ana"] = _vecino(conexion, admin, "Ana Prueba", [
                (edificio, ids["1A"], "propietario"), (edificio, ids["2B"], "propietario"),
                (otro, unidad_otro, "propietario")])
            personas["carla"] = _vecino(conexion, admin, "Carla Prueba", [(edificio, ids["1B"], "propietario")])
            personas["beto"] = _vecino(conexion, admin, "Beto Prueba", [(edificio, ids["1B"], "inquilino")])
            personas["dora"] = _vecino(conexion, admin, "Dora Prueba", [(edificio, ids["2A"], "propietario")])
            conexion.execute("UPDATE complejo SET estado_migracion = 'sin_saldos_previos' WHERE id IN (%s, %s)",
                             (edificio, otro))
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
                  unidad_b=unidad_b, generales=generales, ascensor=ascensor, generales_otro=generales_otro,
                  categorias=categorias, categoria_otro=categoria_otro, personas=personas, persona_b=persona_b)
        _fijar_hoy(app)
        m.como("super_admin")
        try:
            yield m
        finally:
            app.dependency_overrides.clear()


# --- Datos de partida (los de H-015) -------------------------------------------------------------------


def configurar(m: Mundo) -> None:
    m.ejecutar(
        "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, vigente_desde, "
        "tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, porcentaje_fondo, "
        "dia_de_vencimiento, modalidad_de_vencimiento) VALUES (%s, %s, %s, '2026-01-01', '3.00', '500.00', 0, %s, "
        "'5.00', 10, 'unico')", (m.admin, m.edificio, m.personas["super_admin"], PROPORCIONAL))


def gasto(
    m: Mundo, importe: str, *, categoria: str = "Limpieza", grupo: UUID | None = None, tipo: str = "ordinario",
    estado: str = "aprobado", periodo: date = NOV, concepto: str = "Gasto ficticio",
) -> UUID:
    fila = m.ejecutar(
        "INSERT INTO gasto (administracion_id, complejo_id, categoria_id, grupo_id, concepto, periodo, "
        "periodo_de_imputacion, tipo, importe, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "RETURNING id",
        (m.admin, m.edificio, m.categorias[categoria], grupo or m.generales, concepto, periodo, periodo, tipo,
         importe, estado))
    return UUID(str(fila[0]))


def cargo(
    m: Mundo, unidad: str, importe: str, *, concepto: str = "Multa", estado: str = "aprobado",
    periodo: date = NOV, complejo: UUID | None = None, unidad_id: UUID | None = None,
) -> UUID:
    """Un cargo particular por SQL; devuelve su id."""
    fila = m.ejecutar(
        "INSERT INTO cargo_particular (administracion_id, complejo_id, unidad_id, concepto, importe, periodo, "
        "motivo, estado) VALUES (%s, %s, %s, %s, %s, %s, 'Motivo ficticio', %s) RETURNING id",
        (m.admin, complejo or m.edificio, unidad_id or m.unidades[unidad], concepto, importe, periodo, estado))
    return UUID(str(fila[0]))


def cargar_base(m: Mundo) -> None:
    """La base de H-011: Limpieza 100.000 (con una nota de 10.000), Ascensor 40.000 para `2A` y `2B`, Pintura
    extraordinaria 50.000 y un cargo particular de 5.000 a `1B`. Más lo que no entra (borrador, otro período)."""
    configurar(m)
    limpieza = gasto(m, "100000.00", concepto="Limpieza de noviembre")
    gasto(m, "40000.00", categoria="Ascensor", grupo=m.ascensor, concepto="Abono del ascensor")
    gasto(m, "50000.00", categoria="Pintura", tipo="extraordinario", concepto="Pintura del hall")
    m.ejecutar(
        "INSERT INTO nota_de_credito (administracion_id, complejo_id, gasto_id, importe, periodo, cuit_emisor, "
        "punto_de_venta, tipo_de_comprobante, numero_de_comprobante) "
        "VALUES (%s, %s, %s, '10000.00', %s, '20111111112', '0001', 'NC', %s)",
        (m.admin, m.edificio, limpieza, NOV, uuid4().hex[:8]))
    cargo(m, "1B", "5000.00", concepto="Multa")
    gasto(m, "999.00", estado="borrador")
    gasto(m, "12345.00", periodo=OCT)
    cargo(m, "2A", "3000.00", concepto="Cargo borrador", estado="borrador")


# --- El libro y la emisión -----------------------------------------------------------------------------


def emitir_libro(m: Mundo, periodo: date, obligaciones: dict[str, tuple[str, str, str]]) -> Any:
    """Una emisión del libro (unidad → ordinaria, fondo, extraordinaria), vencimiento el día 10."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import emisiones
    from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

    with sesion_app(m.base, m.admin) as s:
        r = emisiones.registrar_emision(
            s, m.identidad(), emision_id=uuid4(), complejo_id=m.edificio, periodo=periodo,
            obligaciones=[ObligacionAEmitir(m.unidades[u], periodo.replace(day=10), Dinero(o), Dinero(f), Dinero(e))
                          for u, (o, f, e) in obligaciones.items()],
            request_id=uuid4())
        s.commit()
    return r


def anular_libro(m: Mundo, emision_id: UUID) -> None:
    from proptech_core.cuenta_corriente.aplicacion import emisiones

    with sesion_app(m.base, m.admin) as s:
        emisiones.anular_emision(s, m.identidad(), emision_id=emision_id, motivo="Anulación ficticia",
                                 request_id=uuid4())
        s.commit()


def cuenta_de(m: Mundo, unidad: str) -> UUID | None:
    filas = m.filas("SELECT id FROM cuenta WHERE unidad_id = %s", (m.unidades.get(unidad) or m.unidad_otro,))
    return UUID(str(filas[0][0])) if filas else None


def pagar(m: Mundo, unidad: str, importe: str, fecha: date) -> None:
    """Un crédito `pago` directo del libro (sin pasar por los pagos informados)."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import creditos

    cuenta = cuenta_de(m, unidad)
    assert cuenta is not None, f"{unidad} no tiene cuenta"
    with sesion_app(m.base, m.admin) as s:
        creditos.registrar_credito(
            s, m.identidad(), cuenta_id=cuenta, tipo="pago", importe=Dinero(importe), fecha_valor=fecha,
            operacion_id=uuid4(), destino=None, request_id=uuid4())
        s.commit()


def bonificar(m: Mundo, unidad: str, periodo: date, importe: str) -> None:
    """Una bonificación del libro atada a la ordinaria de esa obligación (su destino queda fijo, E12 del 4b)."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import creditos
    from proptech_core.cuenta_corriente.dominio.imputacion import Componente, Destino

    cuenta = cuenta_de(m, unidad)
    assert cuenta is not None, f"{unidad} no tiene cuenta"
    obligacion = m.uno("SELECT id FROM obligacion WHERE cuenta_id = %s AND periodo = %s", (cuenta, periodo))
    with sesion_app(m.base, m.admin) as s:
        creditos.registrar_credito(
            s, m.identidad(), cuenta_id=cuenta, tipo="bonificacion", importe=Dinero(importe), fecha_valor=HOY,
            operacion_id=uuid4(), destino=Destino(UUID(str(obligacion)), Componente.ORDINARIA),
            request_id=uuid4())
        s.commit()


def base_noviembre(m: Mundo) -> str:
    """La liquidación de noviembre emitida por el camino real. Devuelve su `liquidacion_id`."""
    m.como("super_admin")
    cargar_base(m)
    return str(emitir_lo_revisado(m)["liquidacion_id"])


def base_con_mora(m: Mundo) -> dict[str, Any]:
    """Octubre emitido por el libro (10.000,00 por unidad; `1B` y `2B` pagan en término, `1A` y `2A` no) y noviembre
    por el camino real. Devuelve la emisión de noviembre (con `liquidacion_id` y `emision_id`)."""
    m.como("super_admin")
    cargar_base(m)
    emitir_libro(m, OCT, {u: ("10000.00", "0.00", "0.00") for u in UNIDADES})
    for u in ("1B", "2B"):
        pagar(m, u, "10000.00", date(2026, 10, 5))
    return emitir_lo_revisado(m)


def emitir_lo_revisado(m: Mundo, periodo: date = NOV) -> dict[str, Any]:
    r = m.cliente.get(f"/api/complejos/{m.edificio}/periodos/{periodo.isoformat()}/preliquidacion")
    assert r.status_code == 200, f"la preliquidación: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    cuerpo = {"emision_id": str(uuid4()), "huella": r.json()["huella"], "alertas_aceptadas": []}
    e = m.cliente.post(f"/api/complejos/{m.edificio}/periodos/{periodo.isoformat()}/emision", json=cuerpo)
    assert e.status_code in (200, 201), f"emitir: se esperaba 201, llegó {e.status_code}: {e.text[:400]}"
    return dict(e.json())


def anular_liquidacion(m: Mundo, liquidacion_id: str) -> None:
    r = m.cliente.post(f"/api/complejos/{m.edificio}/liquidaciones/{liquidacion_id}/anulacion",
                       json={"motivo": "Se cargó mal una factura"})
    assert r.status_code == 200, f"anular: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"


def generar_los_pdfs(m: Mundo, liquidacion_id: str) -> None:
    """Los documentos de la liquidación pasan a `generado` como lo hace el worker."""
    import importlib

    aplicacion = importlib.import_module("proptech_core.liquidacion.aplicacion.documentos")
    r = m.cliente.get(f"/api/complejos/{m.edificio}/liquidaciones/{liquidacion_id}/documentos")
    assert r.status_code == 200, f"documentos: {r.status_code} {r.text[:300]}"
    for d in r.json():
        with sesion_app(m.base, m.admin) as s:
            aplicacion.generar_documento(s, documento_id=UUID(d["documento_id"]))
            s.commit()


def texto_del_pdf(contenido: bytes) -> str:
    import io

    from pypdf import PdfReader

    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(contenido)).pages)


# --- Lo que el libro dice (el oráculo) -----------------------------------------------------------------


def del_libro(m: Mundo, unidad: str, *, sin_extraordinaria: bool = False) -> dict[str, Any]:
    """Los números de una unidad según `estado_de_cuenta` y `situacion_de_cuenta` a hoy: lo que ve el administrador.
    `sin_extraordinaria` es la mirada del inquilino (D-170.2): la deuda sin el componente extraordinaria."""
    from proptech_core.cuenta_corriente.aplicacion import cobranza, lecturas
    from proptech_core.cuenta_corriente.dominio.imputacion import Componente

    cuenta = cuenta_de(m, unidad)
    if cuenta is None:
        return {"total_a_pagar": "0.00", "vencimiento": None, "intereses": "0.00", "credito_aplicable": "0.00",
                "credito_retenido": "0.00"}
    with sesion_app(m.base, m.admin) as s:
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        c = cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=HOY)
    pendientes = {k: v for k, v in e.residual.items()
                  if v.decimal > 0 and not (sin_extraordinaria and k[1] is Componente.EXTRAORDINARIA)}
    total = sum((v.decimal for v in pendientes.values()), Decimal("0.00"))
    vencimientos = [o.vencimiento for o in e.obligaciones
                    if o.id in e.obligaciones_que_cuentan and any(k[0] == o.id for k in pendientes)]
    return {
        "total_a_pagar": f"{total:.2f}",
        "vencimiento": min(vencimientos).isoformat() if vencimientos else None,
        "intereses": c.interes_vencido.a_texto(),
        "credito_aplicable": e.credito_a_favor_aplicable.a_texto(),
        "credito_retenido": e.credito_a_favor_retenido.a_texto(),
    }


def deuda_anterior(m: Mundo, emision_id: str, unidad: str) -> str:
    """El saldo anterior (D12) de la unidad respecto de esa emisión, del libro."""
    from proptech_core.cuenta_corriente.aplicacion import lecturas

    cuenta = cuenta_de(m, unidad)
    assert cuenta is not None
    with sesion_app(m.base, m.admin) as s:
        return lecturas.saldo_anterior(s, emision_id=UUID(emision_id), cuenta_id=cuenta).a_texto()


def conteo_de_todo(m: Mundo) -> dict[str, tuple[int, str]]:
    """Filas y contenido de cada tabla del esquema `public`, con el superusuario (sin RLS)."""
    c = m.base.contenedor
    with psycopg.connect(host=c.get_container_host_ip(), port=c.get_exposed_port(5432), dbname=m.base.nombre,
                         user=c.username, password=c.password, autocommit=True) as conexion:
        tablas = [f[0] for f in conexion.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename").fetchall()]
        resultado = {}
        for tabla in tablas:
            fila = conexion.execute(
                f"SELECT count(*), coalesce(md5(string_agg(t::text, '|' ORDER BY t::text)), '') "  # noqa: S608
                f'FROM public."{tabla}" t').fetchone()
            assert fila is not None
            resultado[tabla] = (int(fila[0]), str(fila[1]))
        return resultado


# --- Los pagos informados (los de H-022) ---------------------------------------------------------------


def ruta_pagos(m: Mundo, sufijo: str = "") -> str:
    return f"/api/complejos/{m.edificio}/pagos{sufijo}"


def informar_ok(
    m: Mundo, partes: dict[str, str], *, numero: str, fecha: str = "2026-11-05", banco: str = "Banco Nación",
) -> str:
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


def confirmar_como_administrador(m: Mundo, pago_id: str, *, volver_a: str) -> None:
    m.como("admin_principal")
    r = m.cliente.post(ruta_pagos(m, f"/{pago_id}/confirmacion"), json={})
    assert r.status_code == 200, f"confirmar: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    assert r.json().get("estado") == "confirmado", r.json()
    m.como(volver_a)


def rechazar_como_administrador(m: Mundo, pago_id: str, *, volver_a: str) -> None:
    m.como("admin_principal")
    r = m.cliente.post(ruta_pagos(m, f"/{pago_id}/rechazo"), json={"motivo": "El monto no coincide"})
    assert r.status_code == 200, f"rechazar: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    m.como(volver_a)


def revertir_como_administrador(m: Mundo, pago_id: str, *, volver_a: str) -> None:
    m.como("admin_principal")
    r = m.cliente.post(ruta_pagos(m, f"/{pago_id}/reversion"), json={"motivo": "Cheque rechazado, sin fondos"})
    assert r.status_code == 200, f"revertir: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    m.como(volver_a)


def pago_confirmado(m: Mundo, quien: str, partes: dict[str, str], *, numero: str, **kwargs: Any) -> str:
    """`quien` informa y el administrador confirma; la sesión vuelve a `quien`."""
    m.como(quien)
    pago = informar_ok(m, partes, numero=numero, **kwargs)
    confirmar_como_administrador(m, pago, volver_a=quien)
    return pago


# --- Las rutas del portal (CONTRATO.md) ----------------------------------------------------------------


def mis_unidades(m: Mundo) -> dict[str, Any]:
    r = m.cliente.get("/api/mis-unidades")
    assert r.status_code == 200, f"mis-unidades: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    cuerpo = r.json()
    assert isinstance(cuerpo, dict), f"mis-unidades tiene que ser un objeto: {cuerpo!r}"
    assert set(cuerpo) == {"fecha", "conjunto", "unidades"}, f"las claves de mis-unidades: {sorted(cuerpo)}"
    assert set(cuerpo["conjunto"]) == CLAVES_DEL_CONJUNTO, cuerpo["conjunto"]
    assert isinstance(cuerpo["unidades"], list), cuerpo["unidades"]
    for u in cuerpo["unidades"]:
        assert set(u) == CLAVES_DE_UNIDAD, f"las claves de una unidad: {sorted(u)}"
    return dict(cuerpo)


def por_unidad(m: Mundo) -> dict[str, dict[str, Any]]:
    """Identificador → su fila de `mis-unidades` (el identificador es único en estos ejemplos)."""
    unidades = mis_unidades(m)["unidades"]
    resultado = {u["identificador"]: u for u in unidades}
    assert len(resultado) == len(unidades), f"un identificador repetido: {unidades}"
    return resultado


def id_de(m: Mundo, unidad: str) -> UUID:
    return m.unidades.get(unidad) or m.unidad_otro


def ruta_unidad(m: Mundo, unidad: str | UUID, sufijo: str) -> str:
    uid = unidad if isinstance(unidad, UUID) else id_de(m, unidad)
    return f"/api/mis-unidades/{uid}{sufijo}"


def pagos_de(m: Mundo, unidad: str) -> list[dict[str, Any]]:
    r = m.cliente.get(ruta_unidad(m, unidad, "/pagos"))
    assert r.status_code == 200, f"pagos de {unidad}: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    lista = r.json()
    assert isinstance(lista, list), f"los pagos tienen que ser una lista: {lista!r}"
    for p in lista:
        assert set(p) == CLAVES_DE_PAGO, f"las claves de un pago: {sorted(p)}"
    return list(lista)


def documentos_de(m: Mundo, unidad: str) -> list[dict[str, Any]]:
    r = m.cliente.get(ruta_unidad(m, unidad, "/documentos"))
    assert r.status_code == 200, f"documentos de {unidad}: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    lista = r.json()
    assert isinstance(lista, list), f"los documentos tienen que ser una lista: {lista!r}"
    for d in lista:
        assert set(d) == CLAVES_DE_DOCUMENTO, f"las claves de un documento: {sorted(d)}"
    return list(lista)


def cargo_de(m: Mundo, unidad: str | UUID, cargo_id: UUID) -> Any:
    return m.cliente.get(ruta_unidad(m, unidad, f"/cargos-particulares/{cargo_id}"))


def no_encontrado(r: Any, donde: str) -> None:
    assert r.status_code == 404, f"{donde}: se esperaba 404, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == NO_ENCONTRADO, f"{donde}: el 404 tiene que ser {NO_ENCONTRADO}, llegó {r.json()}"


def morosidad_del_administrador(m: Mundo) -> dict[str, dict[str, Any]]:
    """Lo que ve el administrador en su ruta de morosidad (10a): identificador → fila."""
    from proptech_api.acceso import identidad_actual

    quien = m.app.dependency_overrides  # la sesión actual se restaura abajo
    anterior = quien.get(identidad_actual)
    m.como("admin_principal")
    try:
        r = m.cliente.get(f"/api/complejos/{m.edificio}/morosidad")
    finally:
        if anterior is not None:
            quien[identidad_actual] = anterior
    assert r.status_code == 200, f"morosidad: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    return {f["unidad"]: f for f in r.json()["unidades"]}
