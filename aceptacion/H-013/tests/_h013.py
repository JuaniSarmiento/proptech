"""Ayudas de la aceptación de H-013 (emitir lo revisado, change 7, D-157).

Copia de las ayudas de H-011, más las de emitir y leer lo emitido (al final).

Caja negra: la preliquidación entra por la API real
(`GET /api/complejos/{id}/periodos/{AAAA-MM-01}/preliquidacion`) con la identidad inyectada. Los datos
de partida se cargan por SQL con el rol de la app, como los dejaría el 6; las emisiones previas, con
`registrar_emision` y `anular_emision` del libro (4b, 4c). Lo que todavía no existe (la ruta) se pide con
un `assert` y un mensaje, nunca con un error de setup.

Base de los ejemplos (inventada, HISTORIAS.md H-011): "Torre Ficticia", unidades `1A` 0,30, `1B` 0,30,
`2A` 0,25 y `2B` 0,15; grupos Generales y Ascensor (`2A`, `2B`, renormalizado); fondo 5%, vencimiento día
10, 3% mensual proporcional, gracia 0; noviembre de 2026.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
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

UNIDADES = {"1A": "0.300000", "1B": "0.300000", "2A": "0.250000", "2B": "0.150000"}
SEP, OCT, NOV, DIC = (date(2026, m, 1) for m in (9, 10, 11, 12))
PROPORCIONAL, MES_ENTERO = "proporcional_por_dia", "mes_entero"
CLAVES_DE_UNIDAD = (
    "unidad_id",
    "identificador",
    "ordinaria",
    "fondo_de_reserva",
    "extraordinaria",
    "cargos_particulares",
    "intereses",
    "total",
    "sin_obligacion",
    "por_grupo",
)
CLAVES_DE_TOTALES = (
    "gastos",
    "notas_de_credito",
    "fondo_de_reserva",
    "prorrateado",
    "cargos_particulares",
    "intereses",
    "total",
)


@dataclass
class Mundo:
    app: FastAPI
    cliente: TestClient
    base: BaseDeEdificio
    admin: UUID
    admin_b: UUID
    edificio: UUID
    """Torre Ficticia: cuatro unidades, Generales y Ascensor, sin configuración hasta `configurar`."""
    otro: UUID
    """Otro edificio de la misma administración, con la unidad `9A` y su Generales."""
    edificio_b: UUID
    """Edificio de la administración B."""
    unidades: dict[str, UUID] = field(default_factory=dict)
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

    def sin_sesion(self) -> None:
        from proptech_api.acceso import identidad_actual

        self.app.dependency_overrides.pop(identidad_actual, None)

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
    metodo: str = "coeficiente", es_generales: bool = False,
) -> UUID:
    fila = conexion.execute(
        "INSERT INTO grupo_de_reparto (administracion_id, complejo_id, clave, nombre, metodo, "
        "es_generales) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (admin, complejo, clave, nombre, metodo, es_generales),
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
            for complejo, nombre in ((edificio, "Torre Ficticia"), (otro, "Otro Edificio Ficticio")):
                conexion.execute(
                    "INSERT INTO complejo (id, administracion_id, nombre, localidad, pisos, "
                    "subsuelos) VALUES (%s, %s, %s, 'Mendoza', 3, 1)",
                    (complejo, admin, nombre),
                )
            ids = {
                u: insertar_unidad(conexion, admin, edificio, u, coeficiente=c)
                for u, c in UNIDADES.items()
            }
            insertar_unidad(conexion, admin, otro, "9A", coeficiente="1.000000")
            generales = _grupo(conexion, admin, edificio, "generales", "Generales", es_generales=True)
            ascensor = _grupo(conexion, admin, edificio, "ascensor", "Ascensor")
            for u in ("2A", "2B"):
                conexion.execute(
                    "INSERT INTO grupo_unidad (administracion_id, complejo_id, grupo_id, unidad_id, "
                    "modo_de_coeficientes, coeficiente) VALUES (%s, %s, %s, %s, 'renormalizado', NULL)",
                    (admin, edificio, ascensor, ids[u]),
                )
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
                    "VALUES (%s, %s, %s, %s)",
                    (admin, personas[rol], nombre_rol, alcance),
                )
            conexion.execute(
                "UPDATE complejo SET estado_migracion = 'sin_saldos_previos' WHERE id IN (%s, %s)",
                (edificio, otro),
            )
        with base_del_edificio.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, admin_b)
            conexion.execute(
                "INSERT INTO administracion (id, nombre) VALUES (%s, 'Otra administración ficticia')",
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
            generales=generales,
            ascensor=ascensor,
            generales_otro=generales_otro,
            categorias=categorias,
            categoria_otro=categoria_otro,
            personas=personas,
            persona_b=persona_b,
        )
        m.como("super_admin")
        try:
            yield m
        finally:
            app.dependency_overrides.clear()


# --- Datos de partida ------------------------------------------------------------------------------


def configurar(
    m: Mundo, *, fondo: str = "5.00", desde: date = date(2026, 1, 1), forma: str = PROPORCIONAL,
    gracia: int = 0, dia: int = 10, complejo: UUID | None = None,
) -> None:
    m.ejecutar(
        "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, "
        "vigente_desde, tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, "
        "porcentaje_fondo, dia_de_vencimiento, modalidad_de_vencimiento) "
        "VALUES (%s, %s, %s, %s, '3.00', '500.00', %s, %s, %s, %s, 'unico')",
        (m.admin, complejo or m.edificio, m.personas["super_admin"], desde, gracia, forma, fondo, dia),
    )


def gasto(
    m: Mundo, importe: str, *, categoria: str = "Limpieza", grupo: UUID | None = None,
    tipo: str = "ordinario", estado: str = "aprobado", periodo: date = NOV,
    imputacion: date | None = None, complejo: UUID | None = None, concepto: str = "Gasto ficticio",
) -> UUID:
    en_otro = complejo == m.otro
    fila = m.ejecutar(
        "INSERT INTO gasto (administracion_id, complejo_id, categoria_id, grupo_id, concepto, "
        "periodo, periodo_de_imputacion, tipo, importe, estado) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            m.admin,
            complejo or m.edificio,
            m.categoria_otro if en_otro else m.categorias[categoria],
            m.generales_otro if en_otro else (grupo or m.generales),
            concepto,
            periodo,
            imputacion or periodo,
            tipo,
            importe,
            estado,
        ),
    )
    return UUID(str(fila[0]))


def nota_de_credito(m: Mundo, gasto_id: UUID, importe: str, *, periodo: date = NOV) -> None:
    m.ejecutar(
        "INSERT INTO nota_de_credito (administracion_id, complejo_id, gasto_id, importe, periodo, "
        "cuit_emisor, punto_de_venta, tipo_de_comprobante, numero_de_comprobante) "
        "VALUES (%s, %s, %s, %s, %s, '20111111112', '0001', 'NC', %s)",
        (m.admin, m.edificio, gasto_id, importe, periodo, uuid4().hex[:8]),
    )


def cargo(
    m: Mundo, unidad: str, importe: str, *, concepto: str = "Multa", estado: str = "aprobado",
    periodo: date = NOV,
) -> None:
    m.ejecutar(
        "INSERT INTO cargo_particular (administracion_id, complejo_id, unidad_id, concepto, "
        "importe, periodo, motivo, estado) VALUES (%s, %s, %s, %s, %s, %s, 'Motivo ficticio', %s)",
        (m.admin, m.edificio, m.unidades[unidad], concepto, importe, periodo, estado),
    )


def cargar_base(m: Mundo, *, con_lo_que_no_entra: bool = True) -> dict[str, UUID]:
    """La base de los ejemplos de HISTORIAS.md (H-011)."""
    configurar(m)
    limpieza = gasto(m, "100000.00", categoria="Limpieza", concepto="Limpieza de noviembre")
    gasto(m, "40000.00", categoria="Ascensor", grupo=m.ascensor, concepto="Abono del ascensor")
    gasto(m, "50000.00", categoria="Pintura", tipo="extraordinario", concepto="Pintura del hall")
    nota_de_credito(m, limpieza, "10000.00")
    cargo(m, "1B", "5000.00")
    ids = {"limpieza": limpieza}
    if con_lo_que_no_entra:
        ids["borrador"] = gasto(m, "999.00", estado="borrador")
        gasto(m, "777.00", estado="sin_ia")
        # Sin el gasto `en_revision` de H-011: desde H-012 es un bloqueante y emitir la base lo pediría.
        gasto(m, "12345.00", periodo=OCT)
        gasto(m, "54321.00", complejo=m.otro)
        cargo(m, "2A", "3000.00", estado="borrador")
    return ids


# --- La preliquidación -----------------------------------------------------------------------------


def ruta(m: Mundo, periodo: date | str = NOV, complejo: UUID | None = None) -> str:
    texto = periodo.isoformat() if isinstance(periodo, date) else periodo
    return f"/api/complejos/{complejo or m.edificio}/periodos/{texto}/preliquidacion"


def pedir(m: Mundo, periodo: date | str = NOV, complejo: UUID | None = None) -> Any:
    return m.cliente.get(ruta(m, periodo, complejo))


def preliquidacion(m: Mundo, periodo: date | str = NOV) -> dict[str, Any]:
    r = pedir(m, periodo)
    assert r.status_code == 200, (
        f"se esperaba 200 de la preliquidación, llegó {r.status_code}: {r.text[:400]}"
    )
    cuerpo = r.json()
    for clave in ("periodo", "vencimiento", "porcentaje_fondo", "huella", "totales", "bloques",
                  "grupos", "unidades", "controles"):
        assert clave in cuerpo, f"la preliquidación no trae `{clave}`: {list(cuerpo)}"
    for clave in CLAVES_DE_TOTALES:
        assert clave in cuerpo["totales"], f"los totales no traen `{clave}`: {cuerpo['totales']}"
    for u in cuerpo["unidades"]:
        for clave in CLAVES_DE_UNIDAD:
            assert clave in u, f"la unidad {u.get('identificador')} no trae `{clave}`: {u}"
    return dict(cuerpo)


def unidad(cuerpo: dict[str, Any], identificador: str) -> dict[str, Any]:
    encontradas = [u for u in cuerpo["unidades"] if u["identificador"] == identificador]
    assert len(encontradas) == 1, f"se esperaba una unidad {identificador}: {cuerpo['unidades']}"
    return dict(encontradas[0])


def por_grupo(u: dict[str, Any], grupo: UUID) -> dict[str, Any] | None:
    lista = [g for g in u["por_grupo"] if g["grupo_id"] == str(grupo)]
    assert len(lista) <= 1, f"el grupo {grupo} aparece dos veces en {u['identificador']}"
    return lista[0] if lista else None


def plata(texto: Any) -> Decimal:
    assert isinstance(texto, str), f"un monto tiene que llegar como texto, llegó {texto!r}"
    valor = Decimal(texto)
    assert valor == valor.quantize(Decimal("0.01")) and "." in texto and len(texto.split(".")[1]) == 2, (
        f"un monto tiene que tener dos decimales: {texto!r}"
    )
    return valor


def total_de_cargos(u: dict[str, Any]) -> Decimal:
    return sum((plata(c["importe"]) for c in u["cargos_particulares"]), Decimal("0.00"))


def sumas_cierran(cuerpo: dict[str, Any]) -> None:
    """N04: cada total es la suma de sus partes, al centavo."""
    t = {k: plata(v) for k, v in cuerpo["totales"].items()}
    us = cuerpo["unidades"]
    assert sum((plata(u["ordinaria"]) + plata(u["extraordinaria"]) for u in us), Decimal(0)) == (
        t["gastos"] - t["notas_de_credito"]
    ), "la ordinaria y la extraordinaria de las unidades no suman los gastos menos las notas"
    assert sum((plata(u["fondo_de_reserva"]) for u in us), Decimal(0)) == t["fondo_de_reserva"]
    assert t["prorrateado"] == t["gastos"] - t["notas_de_credito"] + t["fondo_de_reserva"]
    assert sum((total_de_cargos(u) for u in us), Decimal(0)) == t["cargos_particulares"]
    assert sum((plata(u["intereses"]) for u in us), Decimal(0)) == t["intereses"]
    assert t["total"] == t["prorrateado"] + t["cargos_particulares"] + t["intereses"]
    for u in us:
        esperado = (plata(u["ordinaria"]) + plata(u["fondo_de_reserva"]) + plata(u["extraordinaria"])
                    + total_de_cargos(u) + plata(u["intereses"]))
        assert plata(u["total"]) == esperado, f"el total de {u['identificador']} no es la suma"
    assert sum((plata(u["total"]) for u in us), Decimal(0)) == t["total"]


# --- El libro (emisiones previas) ------------------------------------------------------------------


def emitir_libro(
    m: Mundo, periodo: date, obligaciones: dict[str, tuple[str, str, str]],
    vencimiento: date | None = None,
) -> Any:
    """Una emisión del libro con las obligaciones dadas (unidad → ordinaria, fondo, extraordinaria)."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import emisiones
    from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

    with sesion_app(m.base, m.admin) as s:
        r = emisiones.registrar_emision(
            s,
            m.identidad(),
            emision_id=uuid4(),
            complejo_id=m.edificio,
            periodo=periodo,
            obligaciones=[
                ObligacionAEmitir(
                    m.unidades[u],
                    vencimiento or periodo.replace(day=10),
                    Dinero(o),
                    Dinero(f),
                    Dinero(e),
                )
                for u, (o, f, e) in obligaciones.items()
            ],
            request_id=uuid4(),
        )
        s.commit()
    return r


def emitir_lo_preliquidado(m: Mundo, cuerpo: dict[str, Any]) -> Any:
    """La emisión del libro con lo que dice la preliquidación (la ordinaria lleva los cargos, E15)."""
    obligaciones = {
        u["identificador"]: (
            str(plata(u["ordinaria"]) + total_de_cargos(u)),
            u["fondo_de_reserva"],
            u["extraordinaria"],
        )
        for u in cuerpo["unidades"]
        if not u["sin_obligacion"]
    }
    return emitir_libro(m, date.fromisoformat(cuerpo["periodo"]), obligaciones,
                        date.fromisoformat(cuerpo["vencimiento"]))


def anular_libro(m: Mundo, emision_id: UUID) -> None:
    from proptech_core.cuenta_corriente.aplicacion import emisiones

    with sesion_app(m.base, m.admin) as s:
        emisiones.anular_emision(
            s, m.identidad(), emision_id=emision_id, motivo="Anulación ficticia", request_id=uuid4()
        )
        s.commit()


def intereses_emitidos_por_unidad(m: Mundo, registrada: Any) -> dict[str, Decimal]:
    """Interés de la emisión por identificador de unidad, leído del resultado del libro."""
    por_cuenta = {c: sum((i.importe.decimal for i in lista), Decimal("0.00"))
                  for c, lista in registrada.intereses.items()}
    cuentas = {UUID(str(c)): u for c, u in m.filas(
        "SELECT c.id, un.identificador FROM cuenta c JOIN unidad un ON un.id = c.unidad_id "
        "WHERE un.complejo_id = %s", (m.edificio,))}
    resultado = {u: Decimal("0.00") for u in UNIDADES}
    for cuenta, importe in por_cuenta.items():
        resultado[cuentas[cuenta]] += importe
    return resultado


# --- Sin efectos -----------------------------------------------------------------------------------


def conteo_de_todo(m: Mundo) -> dict[str, tuple[int, str]]:
    """Filas y contenido de cada tabla del esquema `public`, con el superusuario (sin RLS)."""
    c = m.base.contenedor
    with psycopg.connect(
        host=c.get_container_host_ip(), port=c.get_exposed_port(5432), dbname=m.base.nombre,
        user=c.username, password=c.password, autocommit=True,
    ) as conexion:
        tablas = [f[0] for f in conexion.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        ).fetchall()]
        resultado = {}
        for tabla in tablas:
            fila = conexion.execute(
                f'SELECT count(*), coalesce(md5(string_agg(t::text, \'|\' ORDER BY t::text)), \'\') '  # noqa: S608
                f'FROM public."{tabla}" t'
            ).fetchone()
            assert fila is not None
            resultado[tabla] = (int(fila[0]), str(fila[1]))
        return resultado


# --- Emitir y leer lo emitido (H-013) --------------------------------------------------------------

MOTIVO_VENCIMIENTO = "Feriado del 10/11"


def ruta_emision(m: Mundo, periodo: date | str = NOV, complejo: UUID | None = None) -> str:
    texto = periodo.isoformat() if isinstance(periodo, date) else periodo
    return f"/api/complejos/{complejo or m.edificio}/periodos/{texto}/emision"


def cuerpo_de_emision(
    huella: str, *, aceptadas: list[str] | None = None, vencimiento: dict[str, Any] | None = None,
    emision_id: UUID | None = None,
) -> dict[str, Any]:
    cuerpo: dict[str, Any] = {
        "emision_id": str(emision_id or uuid4()),
        "huella": huella,
        "alertas_aceptadas": aceptadas or [],
    }
    if vencimiento is not None:
        cuerpo["vencimiento"] = vencimiento
    return cuerpo


def emitir(m: Mundo, cuerpo: dict[str, Any], periodo: date | str = NOV) -> Any:
    return m.cliente.post(ruta_emision(m, periodo), json=cuerpo)


def emitida(r: Any) -> dict[str, Any]:
    assert r.status_code in (200, 201), (
        f"se esperaba 201 (emitida), llegó {r.status_code}: {r.text[:400]}"
    )
    cuerpo = r.json()
    for clave in ("liquidacion_id", "emision_id", "periodo", "vencimiento", "huella", "obligaciones"):
        assert clave in cuerpo, f"la emisión no trae `{clave}`: {list(cuerpo)}"
    return dict(cuerpo)


def emitir_lo_revisado(
    m: Mundo, periodo: date = NOV, *, aceptadas: list[str] | None = None,
    vencimiento: dict[str, Any] | None = None,
) -> dict[str, Any]:
    huella = preliquidacion(m, periodo)["huella"]
    return emitida(emitir(m, cuerpo_de_emision(huella, aceptadas=aceptadas, vencimiento=vencimiento),
                          periodo))


def leer_liquidacion(m: Mundo, liquidacion_id: str) -> dict[str, Any]:
    r = m.cliente.get(f"/api/complejos/{m.edificio}/liquidaciones/{liquidacion_id}")
    assert r.status_code == 200, f"se esperaba 200 al leer la liquidación, llegó {r.status_code}: {r.text[:400]}"
    return dict(r.json())


def obligacion_de(cuerpo: dict[str, Any], identificador: str) -> dict[str, Any] | None:
    lista = [o for o in cuerpo["obligaciones"] if o["identificador"] == identificador]
    assert len(lista) <= 1, f"{identificador} tiene dos obligaciones en la emisión"
    return lista[0] if lista else None


def obligaciones_del_libro(m: Mundo, periodo: date = NOV) -> dict[str, tuple[str, str, str, date]]:
    """Identificador → (ordinaria, fondo, extraordinaria, vencimiento) de las obligaciones con emisión."""
    filas = m.filas(
        "SELECT u.identificador, o.ordinaria::text, o.fondo_de_reserva::text, o.extraordinaria::text, "
        "o.vencimiento FROM obligacion o JOIN cuenta c ON c.id = o.cuenta_id "
        "JOIN unidad u ON u.id = c.unidad_id WHERE o.complejo_id = %s AND o.periodo = %s "
        "AND o.emision_id IS NOT NULL",
        (m.edificio, periodo),
    )
    resultado: dict[str, tuple[str, str, str, date]] = {}
    for f in filas:
        assert f[0] not in resultado, f"{f[0]} tiene dos obligaciones del libro en {periodo}"
        resultado[f[0]] = (f[1], f[2], f[3], f[4])
    return resultado


def auditorias(m: Mundo, accion: str) -> int:
    return int(m.uno("SELECT count(*) FROM auditoria WHERE accion = %s", (accion,)))


def cuenta_de(m: Mundo, unidad: str) -> UUID:
    filas = m.filas("SELECT id FROM cuenta WHERE unidad_id = %s", (m.unidades[unidad],))
    assert filas, f"{unidad} no tiene cuenta"
    return UUID(str(filas[0][0]))


def saldo_anterior_del_libro(m: Mundo, emision_id: str, unidad: str) -> str:
    from proptech_core.cuenta_corriente.aplicacion import lecturas

    with sesion_app(m.base, m.admin) as s:
        return lecturas.saldo_anterior(s, emision_id=UUID(emision_id), cuenta_id=cuenta_de(m, unidad)).a_texto()


def credito_de_correccion(m: Mundo, unidad: str, obligacion_periodo: date, importe: str) -> None:
    """Un crédito de corrección del 4b sobre la obligación de la unidad en ese período."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import correcciones

    obligacion = m.uno(
        "SELECT o.id FROM obligacion o JOIN cuenta c ON c.id = o.cuenta_id "
        "WHERE c.unidad_id = %s AND o.periodo = %s",
        (m.unidades[unidad], obligacion_periodo),
    )
    with sesion_app(m.base, m.admin) as s:
        correcciones.corregir(
            s,
            m.identidad(),
            complejo_id=m.edificio,
            pedido=correcciones.PedidoDeCorreccion(
                forma="credito", operacion_id=uuid4(), motivo="Corrección ficticia",
                obligacion_id=UUID(str(obligacion)), importe=Dinero(importe),
            ),
            request_id=uuid4(),
        )
        s.commit()


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
