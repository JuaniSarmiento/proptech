"""Ayudas de la aceptación de H-010 (ajuste de saldo inicial, change 5, D-155, E11).

Caja negra: el ajuste entra por la API real (`POST /api/complejos/{id}/unidades/{unidad}/
ajustes-de-saldo-inicial`) con la identidad inyectada, y por el caso de uso
`proptech_core.importacion.aplicacion.ajuste.ajustar_saldo_inicial` cuando el escenario necesita
fijar el día del ajuste con el `reloj` (05/11/2026). El saldo inicial de la base se carga con el
caso de uso real del 4c (`registrar_saldo_inicial`), el edificio se pasa a `confirmada` por SQL
como la app, y el interés se mira emitiendo con `registrar_emision`.

Lo que todavía no existe (el caso de uso, la ruta, la tabla `ajuste_de_saldo_inicial`, la acción
`ajustar_saldo_inicial`) se pide con un `assert` y un mensaje, nunca con un error de setup.

Base de los ejemplos: "Edificio Ficticio de Saldos" (7 unidades: `1A`, `1B`, `2A`, `2B`, `3C`,
`4D`, `5E`), migración el 15/10/2026 desde `saldos-octubre.xlsx` (inventado):

- `1A`: agosto, ordinaria $80.000, vence 10/08/2026 (debía $85.000: faltan $5.000).
- `4D`: crédito de $3.000.
- `5E`: sin saldo (no tiene cuenta).

Después el edificio queda `confirmada`.
"""

from __future__ import annotations

import importlib
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from types import ModuleType
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .._cuenta_corriente import sesion_app
from .._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad

UNIDADES = ("1A", "1B", "2A", "2B", "3C", "4D", "5E")
MIGRACION = date(2026, 10, 15)
DIA_DEL_AJUSTE = date(2026, 11, 5)
MOTIVO = "Faltó la expensa extraordinaria de julio"
ACCION = "ajustar_saldo_inicial"
TABLA = "ajuste_de_saldo_inicial"
MODULO = "proptech_core.importacion.aplicacion.ajuste"
PROPORCIONAL, MES_ENTERO = "proporcional_por_dia", "mes_entero"
AGO, OCT, NOV, DIC = (date(2026, m, 1) for m in (8, 10, 11, 12))


def reloj_del(dia: date) -> Callable[[], datetime]:
    return lambda: datetime(dia.year, dia.month, dia.day, 15, tzinfo=UTC)


def hoy_posibles() -> set[date]:
    """El día del ajuste por la API es el del reloj real: se acepta el de UTC o el de Mendoza (un
    test que corre cerca de la medianoche no se vuelve rojo por la zona)."""
    ahora = datetime.now(UTC)
    return {ahora.date(), ahora.astimezone(ZoneInfo("America/Argentina/Mendoza")).date()}


# --- El mundo -------------------------------------------------------------------------------------


@dataclass
class Mundo:
    app: FastAPI
    cliente: TestClient
    base: BaseDeEdificio
    admin: UUID
    admin_b: UUID
    edificio: UUID
    """Edificio Ficticio de Saldos: siete unidades, migración pendiente hasta `confirmar_base`."""
    otro: UUID
    """Otro edificio de la misma administración, con la unidad `9A`."""
    edificio_b: UUID
    """Edificio de la administración B, con su unidad `1A`."""
    unidades: dict[str, UUID] = field(default_factory=dict)
    unidad_otro: UUID = field(default_factory=uuid4)
    unidad_b: UUID = field(default_factory=uuid4)
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
            unidad_otro = insertar_unidad(conexion, admin, otro, "9A", coeficiente="1.000000")
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
            for rol, (nombre_rol, alcance, de_unidad, vinculo) in asignaciones.items():
                conexion.execute(
                    "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id, "
                    "unidad_id, vinculo) VALUES (%s, %s, %s, %s, %s, %s)",
                    (admin, personas[rol], nombre_rol, alcance, de_unidad, vinculo),
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
            unidad_b = insertar_unidad(conexion, admin_b, edificio_b, "1A", coeficiente="1.000000")
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
            unidad_otro=unidad_otro,
            unidad_b=unidad_b,
            personas=personas,
            persona_b=persona_b,
        )
        m.como("super_admin")
        try:
            yield m
        finally:
            app.dependency_overrides.clear()


def configurar(m: Mundo, forma: str, *, desde: date = date(2026, 1, 1), gracia: int = 0) -> None:
    """Una versión de configuración del edificio: 3% mensual, umbral $500."""
    m.ejecutar(
        "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, "
        "vigente_desde, tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, "
        "porcentaje_fondo, dia_de_vencimiento, modalidad_de_vencimiento) "
        "VALUES (%s, %s, %s, %s, '3.00', '500.00', %s, %s, '0.00', 10, 'unico')",
        (m.admin, m.edificio, m.personas["super_admin"], desde, gracia, forma),
    )


def cargar_base(m: Mundo, *, confirmar: bool = True) -> None:
    """La carga de saldo inicial de la base con el caso de uso real del 4c, y el edificio
    `confirmada` (como lo deja H-009)."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import saldo_inicial as si

    with sesion_app(m.base, m.admin) as s:
        si.registrar_saldo_inicial(
            s,
            m.identidad(),
            complejo_id=m.edificio,
            operacion_id=uuid4(),
            fecha_de_migracion=MIGRACION,
            origen=si.OrigenDeCarga(tipo="importador", archivo="saldos-octubre.xlsx"),
            unidades=[
                si.UnidadDeSaldoInicial(
                    unidad_id=m.unidades["1A"],
                    modo="detalle",
                    filas=(
                        si.FilaDeDeuda(
                            fila=2,
                            periodo=AGO,
                            vencimiento=date(2026, 8, 10),
                            componente="ordinaria",
                            importe=Dinero("80000.00"),
                            interes_acumulado=Dinero("0.00"),
                        ),
                    ),
                ),
                si.UnidadDeSaldoInicial(
                    unidad_id=m.unidades["4D"],
                    modo="detalle",
                    filas=(si.FilaDeCredito(fila=3, importe=Dinero("3000.00")),),
                ),
            ],
            request_id=uuid4(),
            reloj=reloj_del(date(2026, 11, 1)),
        )
        s.commit()
    if confirmar:
        poner_estado(m, "confirmada")


def poner_estado(m: Mundo, estado: str, complejo: UUID | None = None) -> None:
    m.ejecutar(
        "UPDATE complejo SET estado_migracion = %s WHERE id = %s", (estado, complejo or m.edificio)
    )


# --- El ajuste ------------------------------------------------------------------------------------


def modulo() -> ModuleType:
    try:
        return importlib.import_module(MODULO)
    except ImportError as error:
        raise AssertionError(f"falta `{MODULO}` (caso de uso del ajuste, H-010): {error}") from None


def ajustar(
    m: Mundo,
    unidad: str,
    importe: str = "5000.00",
    *,
    componente: str = "ordinaria",
    motivo: str = MOTIVO,
    dia: date = DIA_DEL_AJUSTE,
    operacion_id: UUID | None = None,
    rol: str = "admin_principal",
) -> Any:
    """El ajuste por el caso de uso, con el día fijado por el reloj."""
    from proptech_core.compartido.dinero import Dinero

    funcion = getattr(modulo(), "ajustar_saldo_inicial", None)
    assert funcion is not None, f"`{MODULO}` no define `ajustar_saldo_inicial`"
    with sesion_app(m.base, m.admin) as s:
        r = funcion(
            s,
            m.identidad(rol),
            complejo_id=m.edificio,
            unidad_id=m.unidades[unidad],
            operacion_id=operacion_id or uuid4(),
            importe=Dinero(importe),
            componente=componente,
            motivo=motivo,
            request_id=uuid4(),
            reloj=reloj_del(dia),
        )
        s.commit()
    return r


def ruta(m: Mundo, unidad: UUID, complejo: UUID | None = None) -> str:
    return f"/api/complejos/{complejo or m.edificio}/unidades/{unidad}/ajustes-de-saldo-inicial"


def ajustar_api(
    m: Mundo,
    unidad: str | UUID,
    importe: Any = "5000.00",
    *,
    componente: Any = "ordinaria",
    motivo: Any = MOTIVO,
    operacion_id: UUID | None = None,
    complejo: UUID | None = None,
) -> Any:
    unidad_id = m.unidades[unidad] if isinstance(unidad, str) else unidad
    return m.cliente.post(
        ruta(m, unidad_id, complejo),
        json={
            "operacion_id": str(operacion_id or uuid4()),
            "importe": importe,
            "componente": componente,
            "motivo": motivo,
        },
    )


CLAVES_DEL_AJUSTE = (
    "ajuste_id",
    "operacion_id",
    "obligacion_id",
    "cuenta_id",
    "unidad_id",
    "importe",
    "componente",
    "periodo",
    "vencimiento",
    "motivo",
    "registrado_por",
    "registrado_en",
)


def ajuste_creado(respuesta: Any, *, codigos: tuple[int, ...] = (201,)) -> dict[str, Any]:
    assert respuesta.status_code in codigos, (
        f"se esperaba {codigos} (ajuste registrado), llegó {respuesta.status_code}: "
        f"{respuesta.text[:400]}"
    )
    cuerpo = respuesta.json()
    for clave in CLAVES_DEL_AJUSTE:
        assert clave in cuerpo, f"el ajuste no trae `{clave}`: {cuerpo}"
    return dict(cuerpo)


def leer(r: Any, nombre: str) -> Any:
    valor = r.get(nombre) if isinstance(r, dict) else getattr(r, nombre, None)
    assert valor is not None, f"el resultado del ajuste no trae `{nombre}`: {r!r}"
    return valor


def conflicto(respuesta: Any, campo: str) -> None:
    assert respuesta.status_code == 409, (
        f"se esperaba 409 en `{campo}`, llegó {respuesta.status_code}: {respuesta.text[:400]}"
    )
    cuerpo = respuesta.json()
    assert cuerpo.get("campo") == campo, f"se esperaba conflicto en `{campo}`: {cuerpo}"


def invalido(respuesta: Any, campo: str) -> None:
    """422 que nombra el campo: `{"detail": [{"loc": ["body", <campo>, ...], ...}]}` (el formato de
    validación de la API y del libro)."""
    assert respuesta.status_code == 422, (
        f"se esperaba 422 en `{campo}`, llegó {respuesta.status_code}: {respuesta.text[:400]}"
    )
    detalle = respuesta.json().get("detail")
    assert isinstance(detalle, list) and detalle, f"el 422 no trae la lista: {respuesta.text[:300]}"
    campos = {str(parte) for item in detalle for parte in (item.get("loc") or [])}
    assert campo in campos, f"el 422 no nombra `{campo}`: {detalle}"


# --- Lo que quedó en la base ----------------------------------------------------------------------


def existe(m: Mundo, tabla: str = TABLA) -> bool:
    return bool(m.uno("SELECT to_regclass(%s) IS NOT NULL", (tabla,)))


def exigir_tabla(m: Mundo) -> None:
    assert existe(m), f"falta la tabla {TABLA} (0039)"


def conteos(m: Mundo) -> dict[str, Any]:
    """Todo lo que ajustar podría escribir en la administración A."""
    c: dict[str, Any] = {
        "cuenta": m.uno("SELECT count(*) FROM cuenta"),
        "obligacion": m.uno("SELECT count(*) FROM obligacion"),
        "movimiento": m.uno("SELECT count(*) FROM movimiento"),
        "imputacion": m.uno("SELECT count(*) FROM imputacion"),
        "auditoria": m.uno("SELECT count(*) FROM auditoria"),
    }
    c[TABLA] = m.uno(f"SELECT count(*) FROM {TABLA}") if existe(m) else 0  # noqa: S608
    c["estado"] = m.uno("SELECT estado_migracion FROM complejo WHERE id = %s", (m.edificio,))
    return c


def cuenta_de(m: Mundo, unidad: str) -> UUID | None:
    filas = m.filas("SELECT id FROM cuenta WHERE unidad_id = %s", (m.unidades[unidad],))
    return UUID(str(filas[0][0])) if filas else None


def obligaciones_de(m: Mundo, unidad: str) -> dict[UUID, tuple[date, date, str, str, str, Any]]:
    """Id → (período, vencimiento, ordinaria, fondo, extraordinaria, emision_id)."""
    filas = m.filas(
        "SELECT o.id, o.periodo, o.vencimiento, o.ordinaria::text, o.fondo_de_reserva::text, "
        "o.extraordinaria::text, o.emision_id FROM obligacion o "
        "JOIN cuenta c ON c.id = o.cuenta_id WHERE c.unidad_id = %s",
        (m.unidades[unidad],),
    )
    return {UUID(str(f[0])): (f[1], f[2], f[3], f[4], f[5], f[6]) for f in filas}


def movimientos_de(m: Mundo, unidad: str) -> list[tuple[str, str, str]]:
    return sorted(
        m.filas(
            "SELECT mv.tipo, mv.sentido, mv.importe::text FROM movimiento mv "
            "JOIN cuenta c ON c.id = mv.cuenta_id WHERE c.unidad_id = %s",
            (m.unidades[unidad],),
        )
    )


def ajustes(m: Mundo) -> list[tuple[Any, ...]]:
    """(id, cuenta_id, obligacion_id, operacion_id, motivo, registrado_por) de cada ajuste."""
    exigir_tabla(m)
    return m.filas(
        f"SELECT id, cuenta_id, obligacion_id, operacion_id, motivo, registrado_por FROM {TABLA}"  # noqa: S608
    )


def auditorias(m: Mundo, accion: str = ACCION) -> int:
    return int(m.uno("SELECT count(*) FROM auditoria WHERE accion = %s", (accion,)))


def estado_de_cuenta(m: Mundo, unidad: str) -> Any:
    from proptech_core.cuenta_corriente.aplicacion import lecturas

    cuenta = cuenta_de(m, unidad)
    assert cuenta is not None, f"{unidad} no tiene cuenta"
    with sesion_app(m.base, m.admin) as s:
        return lecturas.estado_de_cuenta(s, cuenta_id=cuenta)


def emitir(m: Mundo, periodo: date) -> None:
    """Una emisión con la obligación de relleno de `3C` (vence el 10 del período)."""
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.cuenta_corriente.aplicacion import emisiones
    from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

    with sesion_app(m.base, m.admin) as s:
        emisiones.registrar_emision(
            s,
            m.identidad(),
            emision_id=uuid4(),
            complejo_id=m.edificio,
            periodo=periodo,
            obligaciones=[
                ObligacionAEmitir(
                    m.unidades["3C"],
                    periodo.replace(day=10),
                    Dinero("1.00"),
                    Dinero("0.00"),
                    Dinero("0.00"),
                )
            ],
            request_id=uuid4(),
        )
        s.commit()


def intereses_de(m: Mundo, obligacion: UUID) -> list[tuple[date, str, list[tuple[date, date]]]]:
    """(corte, importe, tramos) de cada interés de la obligación."""
    filas = m.filas(
        "SELECT id, corte, importe::text FROM movimiento WHERE obligacion_id = %s "
        "AND tipo = 'interes' AND sentido = 'debito' ORDER BY corte",
        (obligacion,),
    )
    resultado = []
    for mov, corte, importe in filas:
        tramos = m.filas(
            "SELECT desde, hasta FROM tramo_de_interes WHERE movimiento_id = %s ORDER BY desde",
            (mov,),
        )
        resultado.append((corte, importe, [(t[0], t[1]) for t in tramos]))
    return resultado


def situacion(m: Mundo, unidad: str, fecha: date) -> Any:
    from proptech_core.cuenta_corriente.aplicacion import cobranza

    cuenta = cuenta_de(m, unidad)
    assert cuenta is not None, f"{unidad} no tiene cuenta"
    with sesion_app(m.base, m.admin) as s:
        return cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=fecha)


def en_paralelo(*funciones: Any) -> list[Any]:
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
