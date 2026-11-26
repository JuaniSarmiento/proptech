"""Ayudas de la aceptación de H-039 (entender mi expensa, change 11 `portal-del-vecino`, D-170).

Caja negra por la API real (`aceptacion/H-039/CONTRATO.md`) con la identidad inyectada. El mundo es el de H-038 (la
emisión por el camino real del 7 y los vínculos de D-106). Lo que todavía no existe (las rutas nuevas de
`proptech_api.vecino`) se pide con un `assert` y un mensaje, nunca con un error de setup.

Base (inventada): "Torre Ficticia" con `1A`, `1B`, `2A` y `2B` y "Otro Edificio Ficticio" con `9A`. "Ana Prueba" es
propietaria de `1A`, `2B` y `9A`; "Carla Prueba", propietaria de `1B`; "Beto Prueba", inquilino de `1B`; "Dora Prueba",
propietaria de `2A`. Hoy es el 18/11/2026.

Dos meses emitidos por el camino real (`base_dos_meses`): octubre (Limpieza 80.000,00 y Pintura extraordinaria
20.000,00, todo a Generales, fondo 5%) y noviembre (Limpieza 100.000,00, Ascensor 40.000,00 para `2A` y `2B`, Pintura
extraordinaria 50.000,00 y una multa de 5.000,00 a `1B`), con octubre pagado en término (sin intereses en noviembre).
`1A`: 31.200,00 en octubre y 46.500,00 en noviembre (ordinaria 30.000,00, fondo 1.500,00, extraordinaria 15.000,00).
`1B`: 31.200,00 y 51.500,00 (con la multa); sin la extraordinaria, 25.200,00 y 36.500,00.
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

CLAVE_DE_ENLACES = "clave-de-prueba-de-enlaces-firmados-0123456789"
HOY = date(2026, 11, 18)
UNIDADES = {"1A": "0.300000", "1B": "0.300000", "2A": "0.250000", "2B": "0.150000"}
SEP, OCT, NOV, DIC = (date(2026, m, 1) for m in (9, 10, 11, 12))
PROPORCIONAL = "proporcional_por_dia"
NO_ENCONTRADO = {"detail": "no encontrado"}
CLAVES_DE_LA_LISTA = {"liquidacion_id", "periodo", "vencimiento", "total"}
CLAVES_DEL_DETALLE = {
    "liquidacion_id", "complejo_id", "unidad_id", "identificador", "vinculo", "periodo", "vencimiento", "bloques",
    "grupos", "ordinaria", "cargos_particulares", "fondo_de_reserva", "extraordinaria", "intereses", "total",
    "comparacion",
}
#: El inquilino no recibe ni la clave `extraordinaria` (D-170.2).
CLAVES_DEL_DETALLE_DEL_INQUILINO = CLAVES_DEL_DETALLE - {"extraordinaria"}
CLAVES_DE_CATEGORIA = {"categoria_id", "nombre", "importe", "porcentaje"}
CLAVES_DE_GRUPO = {"grupo_id", "nombre", "ordinaria", "extraordinaria"}
CLAVES_DE_GRUPO_DEL_INQUILINO = CLAVES_DE_GRUPO - {"extraordinaria"}
CLAVES_DE_LA_COMPARACION = {"liquidacion_id", "periodo", "total_anterior", "diferencia_total", "categorias"}
CLAVES_DE_CATEGORIA_COMPARADA = {"categoria_id", "nombre", "bloque", "importe", "importe_anterior", "diferencia"}
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


def emitir_lo_revisado(m: Mundo, periodo: date = NOV, edificio: UUID | None = None) -> dict[str, Any]:
    edificio = edificio or m.edificio
    r = m.cliente.get(f"/api/complejos/{edificio}/periodos/{periodo.isoformat()}/preliquidacion")
    assert r.status_code == 200, f"la preliquidación: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    cuerpo = {"emision_id": str(uuid4()), "huella": r.json()["huella"], "alertas_aceptadas": []}
    e = m.cliente.post(f"/api/complejos/{edificio}/periodos/{periodo.isoformat()}/emision", json=cuerpo)
    assert e.status_code in (200, 201), f"emitir: se esperaba 201, llegó {e.status_code}: {e.text[:400]}"
    return dict(e.json())


def anular_liquidacion(m: Mundo, liquidacion_id: str) -> None:
    r = m.cliente.post(f"/api/complejos/{m.edificio}/liquidaciones/{liquidacion_id}/anulacion",
                       json={"motivo": "Se cargó mal una factura"})
    assert r.status_code == 200, f"anular: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"



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



def id_de(m: Mundo, unidad: str) -> UUID:
    return m.unidades.get(unidad) or m.unidad_otro


def ruta_unidad(m: Mundo, unidad: str | UUID, sufijo: str) -> str:
    uid = unidad if isinstance(unidad, UUID) else id_de(m, unidad)
    return f"/api/mis-unidades/{uid}{sufijo}"

def no_encontrado(r: Any, donde: str) -> None:
    assert r.status_code == 404, f"{donde}: se esperaba 404, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == NO_ENCONTRADO, f"{donde}: el 404 tiene que ser {NO_ENCONTRADO}, llegó {r.json()}"



# --- Dos meses emitidos por el camino real -------------------------------------------------------------


@dataclass
class Meses:
    octubre: dict[str, Any]
    noviembre: dict[str, Any]

    @property
    def liq_oct(self) -> str:
        return str(self.octubre["liquidacion_id"])

    @property
    def liq_nov(self) -> str:
        return str(self.noviembre["liquidacion_id"])


def _pagar_lo_emitido(m: Mundo, emitida: dict[str, Any], fecha: date) -> None:
    for o in emitida["obligaciones"]:
        total = sum((int(o[k].replace(".", "")) for k in ("ordinaria", "fondo_de_reserva", "extraordinaria")))
        pagar(m, o["identificador"], f"{total // 100}.{total % 100:02d}", fecha)


def sembrar_octubre(m: Mundo) -> dict[str, Any]:
    """Octubre emitido por el camino real y pagado en término (sin intereses para noviembre)."""
    m.como("super_admin")
    configurar(m)
    gasto(m, "80000.00", periodo=OCT, concepto="Limpieza de octubre")
    gasto(m, "20000.00", categoria="Pintura", tipo="extraordinario", periodo=OCT, concepto="Pintura de octubre")
    emitida = emitir_lo_revisado(m, OCT)
    _pagar_lo_emitido(m, emitida, date(2026, 10, 5))
    return emitida


def sembrar_noviembre(m: Mundo) -> None:
    m.como("super_admin")
    gasto(m, "100000.00", concepto="Limpieza de noviembre")
    gasto(m, "40000.00", categoria="Ascensor", grupo=m.ascensor, concepto="Abono del ascensor")
    gasto(m, "50000.00", categoria="Pintura", tipo="extraordinario", concepto="Pintura del hall")
    cargo(m, "1B", "5000.00", concepto="Multa")


def base_dos_meses(m: Mundo) -> Meses:
    octubre = sembrar_octubre(m)
    sembrar_noviembre(m)
    return Meses(octubre=octubre, noviembre=emitir_lo_revisado(m, NOV))


def base_solo_octubre(m: Mundo) -> Meses:
    octubre = sembrar_octubre(m)
    return Meses(octubre=octubre, noviembre={})


def emitir_otro_edificio(m: Mundo) -> str:
    """Una liquidación de octubre del otro edificio de la misma administración. Devuelve su `liquidacion_id`."""
    m.como("super_admin")
    m.ejecutar(
        "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, vigente_desde, "
        "tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, porcentaje_fondo, "
        "dia_de_vencimiento, modalidad_de_vencimiento) VALUES (%s, %s, %s, '2026-01-01', '3.00', '500.00', 0, %s, "
        "'5.00', 10, 'unico')", (m.admin, m.otro, m.personas["super_admin"], PROPORCIONAL))
    m.ejecutar(
        "INSERT INTO gasto (administracion_id, complejo_id, categoria_id, grupo_id, concepto, periodo, "
        "periodo_de_imputacion, tipo, importe, estado) VALUES (%s, %s, %s, %s, 'Limpieza del otro', %s, %s, "
        "'ordinario', '9000.00', 'aprobado')",
        (m.admin, m.otro, m.categoria_otro, m.generales_otro, OCT, OCT))
    return str(emitir_lo_revisado(m, OCT, m.otro)["liquidacion_id"])


# --- Las rutas del portal (CONTRATO.md) ----------------------------------------------------------------


def lista_de(m: Mundo, unidad: str | UUID) -> Any:
    return m.cliente.get(ruta_unidad(m, unidad, "/liquidaciones"))


def lista_ok(m: Mundo, unidad: str) -> list[dict[str, Any]]:
    r = lista_de(m, unidad)
    assert r.status_code == 200, f"liquidaciones de {unidad}: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    lista = r.json()
    assert isinstance(lista, list), f"la lista tiene que ser una lista: {lista!r}"
    for fila in lista:
        assert set(fila) == CLAVES_DE_LA_LISTA, f"las claves de una fila de la lista: {sorted(fila)}"
    return list(lista)


def detalle_de(m: Mundo, unidad: str | UUID, liquidacion_id: str) -> Any:
    return m.cliente.get(ruta_unidad(m, unidad, f"/liquidaciones/{liquidacion_id}"))


def detalle_ok(m: Mundo, unidad: str, liquidacion_id: str, *, inquilino: bool = False) -> dict[str, Any]:
    r = detalle_de(m, unidad, liquidacion_id)
    assert r.status_code == 200, f"detalle de {unidad}: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    cuerpo = r.json()
    assert isinstance(cuerpo, dict), f"el detalle tiene que ser un objeto: {cuerpo!r}"
    claves = CLAVES_DEL_DETALLE_DEL_INQUILINO if inquilino else CLAVES_DEL_DETALLE
    assert set(cuerpo) == claves, f"las claves del detalle: sobran {sorted(set(cuerpo) - claves)}, faltan {sorted(claves - set(cuerpo))}"
    return dict(cuerpo)


def como_admin(m: Mundo, accion: Callable[[], Any]) -> Any:
    """Corre `accion` como el administrador principal y devuelve la sesión a quien estaba."""
    from proptech_api.acceso import identidad_actual

    anterior = m.app.dependency_overrides.get(identidad_actual)
    m.como("admin_principal")
    try:
        return accion()
    finally:
        if anterior is not None:
            m.app.dependency_overrides[identidad_actual] = anterior


def del_administrador(m: Mundo, liquidacion_id: str) -> dict[str, Any]:
    """Lo que ve el administrador del 7 en `GET /api/complejos/{id}/liquidaciones/{liquidacion_id}`."""
    r = como_admin(m, lambda: m.cliente.get(f"/api/complejos/{m.edificio}/liquidaciones/{liquidacion_id}"))
    assert r.status_code == 200, f"el administrador lee la liquidación: {r.status_code}: {r.text[:300]}"
    return dict(r.json())


def linea_del_administrador(m: Mundo, liquidacion_id: str, identificador: str) -> dict[str, Any]:
    lineas = [u for u in del_administrador(m, liquidacion_id)["unidades"] if u["identificador"] == identificador]
    assert len(lineas) == 1, f"la línea de {identificador}: {lineas}"
    return dict(lineas[0])


def distribuciones(m: Mundo, emision_id: str) -> list[Any]:
    """Los eventos `distribuida` de la emisión, de la base."""
    return m.filas("SELECT origen, registrado_en, persona_id FROM evento_de_emision "
                   "WHERE emision_id = %s AND tipo = 'distribuida'", (UUID(emision_id),))


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
