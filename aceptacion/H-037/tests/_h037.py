"""Ayudas de la aceptación de H-037 (la IA completa la factura; change 14 `lectura-de-facturas`, L, R12, R23, D-169).

Caja negra por la API real y la tarea del worker con la identidad inyectada (`aceptacion/H-037/CONTRATO.md`). Parte de
las ayudas de H-036 (el mundo, las facturas con QR) y suma el lector de IA falso, la cola que anota y la siembra de
gastos aprobados. Los archivos de factura se arman acá, con datos inventados. Los archivos de factura se
generan acá, con datos inventados: el QR lo codifica `_qr.py` (el entorno no trae `qrcode` ni `segno`), la imagen se
arma con Pillow y el PDF con WeasyPrint. Lo que todavía no existe (la ruta `facturas`) se pide con un `assert` y un
mensaje, nunca con un error de setup (L-106).

Mundo: "Torre Ficticia" con `cuit` 20000000001 (el receptor del ejemplo oficial) y dos unidades, "Otro Edificio
Ficticio" sin CUIT, y una segunda administración con su edificio.
"""

from __future__ import annotations

import base64
import importlib.util
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from weasyprint import HTML

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from proptech_core.compartido.base_de_datos import crear_fabrica_de_sesiones, registrar_tenant_por_administracion

from .._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad
from ._qr import imagen_del_qr, png_del_qr

CLAVE_DE_ENLACES = "clave-de-prueba-de-enlaces-firmados-0123456789"
CUIT_DEL_EDIFICIO = "20000000001"
#: Del ejemplo oficial de la especificación v1 de ARCA (cuit del emisor y documento del receptor, ambos válidos).
CUIT_DEL_EJEMPLO = "30000000007"

#: El ejemplo oficial de la especificación v1 (QRespecificaciones.pdf de ARCA), campo por campo.
EJEMPLO_OFICIAL: dict[str, Any] = {
    "ver": 1, "fecha": "2020-10-13", "cuit": 30000000007, "ptoVta": 10, "tipoCmp": 1, "nroCmp": 94,
    "importe": 12100, "moneda": "DOL", "ctz": 65, "tipoDocRec": 80, "nroDocRec": 20000000001,
    "tipoCodAut": "E", "codAut": 70417054367476,
}

#: Cuántas claves tiene el gasto que devuelve la ruta (las del 6, más las de H-036).
CLAVES_DEL_GASTO_DEL_6 = {"id", "complejo_id", "proveedor_id", "categoria_id", "grupo_id", "concepto", "periodo",
                          "periodo_de_imputacion", "tipo", "importe", "estado", "cuit_emisor", "punto_de_venta",
                          "tipo_de_comprobante", "numero_de_comprobante", "documento_receptor"}
CLAVES_NUEVAS_DEL_GASTO = {"fecha_de_factura", "origen", "motivo_sin_qr"}
CLAVES_DE_LA_RESPUESTA = CLAVES_DEL_GASTO_DEL_6 | CLAVES_NUEVAS_DEL_GASTO | {"aviso", "factura"}
#: Los campos que sólo puede traer el QR (o la carga a mano, H-037): sin QR legible, todos vacíos.
CAMPOS_DEL_QR = ("proveedor_id", "cuit_emisor", "punto_de_venta", "tipo_de_comprobante", "numero_de_comprobante",
                 "importe", "fecha_de_factura", "documento_receptor")
CAMPOS_SIN_CARGAR = ("concepto", "categoria_id", "grupo_id", "periodo", "periodo_de_imputacion")
ACCION_DE_CARGAR = "cargar_gastos_y_preparar_liquidacion"
LIBRO = ("movimiento", "obligacion", "imputacion", "emision")


def cuit_valido_desde(prefijo: int) -> str:
    """El primer CUIT de 11 dígitos con verificador válido (módulo 11) cuyos diez primeros dígitos son >= prefijo."""
    pesos = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    while True:
        digitos = [int(c) for c in str(prefijo)]
        verificador = 11 - sum(d * p for d, p in zip(digitos, pesos, strict=True)) % 11
        verificador = 0 if verificador == 11 else verificador
        if verificador != 10:
            return f"{prefijo}{verificador}"
        prefijo += 1


CUIT_DEL_PROVEEDOR = cuit_valido_desde(3071111111)
OTRO_CUIT = cuit_valido_desde(3069999999)
CUIT_DEL_RECEPTOR_AJENO = cuit_valido_desde(2711111111)


def datos_qr(**cambios: Any) -> dict[str, Any]:
    """Una factura C emitida a Torre Ficticia por $1.500,50, con el QR v1 completo."""
    base: dict[str, Any] = {
        "ver": 1, "fecha": "2026-10-14", "cuit": int(CUIT_DEL_PROVEEDOR), "ptoVta": 3, "tipoCmp": 11, "nroCmp": 1001,
        "importe": 1500.5, "moneda": "PES", "ctz": 1, "tipoDocRec": 80, "nroDocRec": int(CUIT_DEL_EDIFICIO),
        "tipoCodAut": "E", "codAut": 70417054367476,
    }
    base.update(cambios)
    return {k: v for k, v in base.items() if v is not None}


def texto_del_qr(datos: dict[str, Any] | str, dominio: str = "www.arca.gob.ar") -> str:
    """`https://<dominio>/fe/qr/?p=<base64 del JSON>`; si `datos` es texto, es el JSON ya armado (puede ser basura)."""
    crudo = datos if isinstance(datos, str) else json.dumps(datos, separators=(",", ":"))
    return f"https://{dominio}/fe/qr/?p={base64.b64encode(crudo.encode()).decode()}"


# --- Los archivos de factura -----------------------------------------------------------------------------


def verificar_con_zxing(texto: str, imagen: Image.Image) -> None:
    """Donde `zxingcpp` esté instalado (lo agrega la construcción, D-169), el fixture tiene que leerse idéntico."""
    if importlib.util.find_spec("zxingcpp") is None:
        return
    import zxingcpp

    leidos = [r.text for r in zxingcpp.read_barcodes(imagen)]
    assert leidos == [texto], f"el fixture de la aceptación no se lee: {leidos!r}"


def _hoja(texto: str | None) -> Image.Image:
    hoja = Image.new("RGB", (900, 1150), "white")
    dibujo = ImageDraw.Draw(hoja)
    dibujo.rectangle((40, 40, 860, 140), outline="black", width=3)
    dibujo.text((60, 70), "FACTURA C  -  PROVEEDOR FICTICIO S.A.", fill="black")
    for n in range(8):
        dibujo.line((60, 220 + n * 40, 840, 220 + n * 40), fill="gray", width=2)
        dibujo.text((60, 200 + n * 40), f"Servicio de prueba, renglon {n + 1}", fill="black")
    if texto is not None:
        qr = imagen_del_qr(texto, escala=4).convert("RGB")
        hoja.paste(qr, (60, 700))
    return hoja


def _guardar(hoja: Image.Image, formato: str, **opciones: Any) -> bytes:
    salida = BytesIO()
    hoja.save(salida, format=formato, **opciones)
    return salida.getvalue()


def png_con_qr(texto: str) -> bytes:
    hoja = _hoja(texto)
    verificar_con_zxing(texto, hoja)
    return _guardar(hoja, "PNG")


def jpeg_con_qr(texto: str) -> bytes:
    contenido = _guardar(_hoja(texto), "JPEG", quality=92)
    verificar_con_zxing(texto, Image.open(BytesIO(contenido)))
    return contenido


def png_sin_qr() -> bytes:
    return _guardar(_hoja(None), "PNG")


def _pdf(paginas: list[str | None]) -> bytes:
    cuerpo = ""
    for numero, texto in enumerate(paginas, start=1):
        imagen = ""
        if texto is not None:
            uri = base64.b64encode(png_del_qr(texto)).decode()
            imagen = f'<img src="data:image/png;base64,{uri}" style="width:5cm;height:5cm">'
        corte = "page-break-after: always" if numero < len(paginas) else ""
        cuerpo += (f'<div style="{corte}"><h1>Factura C, pagina {numero}</h1><p>Proveedor Ficticio S.A.</p>'
                   f"{imagen}</div>")
    return HTML(string=f"<html><body>{cuerpo}</body></html>").write_pdf()


def pdf_con_qr(texto: str) -> bytes:
    return _pdf([texto])


def pdf_sin_qr() -> bytes:
    return _pdf([None])


def pdf_con_qr_en_la_segunda_pagina(texto: str) -> bytes:
    return _pdf([None, texto])


def png_con_cabecera_enorme() -> bytes:
    """Un PNG de pocos bytes que declara 30000 x 30000 píxeles (una bomba de descompresión)."""
    import struct
    import zlib

    def trozo(tipo: bytes, datos: bytes) -> bytes:
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))

    cabecera = struct.pack(">IIBBBBB", 30000, 30000, 8, 0, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", cabecera) + trozo(b"IDAT", zlib.compress(b"\x00" * 64))
            + trozo(b"IEND", b""))


# --- El mundo --------------------------------------------------------------------------------------------


class ColaQueAnota:
    """La cola de ARQ de la API, reemplazada por un doble que anota lo que se le encola (sin Redis)."""

    def __init__(self) -> None:
        self.llamadas: list[tuple[str, dict[str, Any]]] = []
        self.falla = False

    async def encolar(self, tarea: str, **datos: Any) -> None:
        if self.falla:
            raise ConnectionError("la cola está caída")
        self.llamadas.append((tarea, datos))


def _conectar(base: BaseDeEdificio) -> Any:
    def conectar() -> Any:
        conexion = base.conectar_app()
        conexion.autocommit = False  # el tenant es local a la transacción (set_config ..., true)
        return conexion

    return conectar


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
    personas: dict[str, UUID] = field(default_factory=dict)
    persona_b: UUID = field(default_factory=uuid4)
    contador_de_nros: int = 2000
    cola: Any = None
    fabrica: Any = None

    def como(self, rol: str) -> None:
        from proptech_api.acceso import identidad_actual
        from proptech_core.acceso.dominio.identidad import Identidad

        identidad = (Identidad(self.admin_b, self.persona_b) if rol == "administracion_b"
                     else Identidad(self.admin, self.personas[rol]))
        self.app.dependency_overrides[identidad_actual] = lambda: identidad

    def filas(self, consulta: str, parametros: tuple[Any, ...] = ()) -> list[Any]:
        with self.base.conectar_app() as conexion, conexion.transaction():
            fijar_tenant(conexion, self.admin)
            return list(conexion.execute(consulta, parametros).fetchall())

    def uno(self, consulta: str, parametros: tuple[Any, ...] = ()) -> Any:
        return self.filas(consulta, parametros)[0][0]

    def numero_nuevo(self) -> int:
        self.contador_de_nros += 1
        return self.contador_de_nros


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
    cola = ColaQueAnota()
    app.state.cola = cola
    admin, admin_b = uuid4(), uuid4()
    roles = {"super_admin": ("super_admin", None), "admin_principal": ("administrador", None),
             "admin_del_edificio": ("administrador", "edificio"), "admin_de_otro_edificio": ("administrador", "otro"),
             "contador": ("contador", None), "contador_del_edificio": ("contador", "edificio"),
             "auxiliar": ("auxiliar", "edificio"), "consejo": ("consejo", "edificio"),
             "consejo_de_otro_edificio": ("consejo", "otro")}
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
            for complejo, nombre, cuit in ((edificio, "Torre Ficticia", CUIT_DEL_EDIFICIO),
                                           (otro, "Otro Edificio Ficticio", None)):
                conexion.execute(
                    "INSERT INTO complejo (id, administracion_id, nombre, localidad, pisos, subsuelos, cuit) "
                    "VALUES (%s, %s, %s, 'Mendoza', 3, 1, %s)", (complejo, admin, nombre, cuit))
            insertar_unidad(conexion, admin, edificio, "1A", coeficiente="0.600000")
            insertar_unidad(conexion, admin, edificio, "1B", coeficiente="0.400000")
            insertar_unidad(conexion, admin, otro, "9A", coeficiente="1.000000")
            alcances = {"edificio": edificio, "otro": otro, None: None}
            for rol, (nombre_rol, alcance) in roles.items():
                conexion.execute(
                    "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id) "
                    "VALUES (%s, %s, %s, %s)", (admin, personas[rol], nombre_rol, alcances[alcance]))
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
        m = Mundo(app=app, cliente=cliente, base=base_del_edificio, admin=admin, admin_b=admin_b, edificio=edificio,
                  otro=otro, edificio_b=edificio_b, personas=personas, persona_b=persona_b, cola=cola)
        m.como("admin_principal")
        engine = create_engine("postgresql+psycopg://", creator=_conectar(base_del_edificio), poolclass=NullPool)
        m.fabrica = crear_fabrica_de_sesiones(engine)
        registrar_tenant_por_administracion(m.fabrica)
        try:
            yield m
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


# --- Lo que se pide y lo que se mira ----------------------------------------------------------------------


def subir(m: Mundo, contenido: bytes, *, nombre: str = "factura.png", tipo: str = "image/png",
          complejo: UUID | str | None = None, campo: str = "archivo") -> Any:
    return m.cliente.post(f"/api/complejos/{complejo or m.edificio}/facturas",
                          files={campo: (nombre, contenido, tipo)})


def creada(m: Mundo, contenido: bytes, **opciones: Any) -> dict[str, Any]:
    """Sube la factura y exige el 201; devuelve el gasto."""
    r = subir(m, contenido, **opciones)
    assert r.status_code == 201, f"POST .../facturas: se esperaba 201, llegó {r.status_code}: {r.text[:300]}"
    cuerpo = r.json()
    assert isinstance(cuerpo, dict), f"el cuerpo del 201 tiene que ser un objeto: {cuerpo!r}"
    return cuerpo


def subir_qr(m: Mundo, datos: dict[str, Any] | str, *, dominio: str = "www.arca.gob.ar", **opciones: Any) -> dict[str, Any]:
    """Una factura PNG con ese QR, subida y aceptada (201)."""
    return creada(m, png_con_qr(texto_del_qr(datos, dominio)), **opciones)


def sin_qr_ok(gasto: dict[str, Any], motivo: str) -> None:
    """El gasto de una factura sin datos del QR: `sin_qr`, con su motivo, y nada leído."""
    assert gasto["origen"] == "sin_qr", f"origen: se esperaba sin_qr, llegó {gasto['origen']!r}"
    assert gasto["motivo_sin_qr"] == motivo, f"motivo_sin_qr: se esperaba {motivo!r}, llegó {gasto['motivo_sin_qr']!r}"
    assert gasto["estado"] == "borrador", f"estado: se esperaba borrador, llegó {gasto['estado']!r}"
    llenos = {c: gasto[c] for c in (*CAMPOS_DEL_QR, *CAMPOS_SIN_CARGAR) if gasto[c] is not None}
    assert not llenos, f"sin QR legible no puede haber datos del QR ni inventados: {llenos}"
    assert gasto["aviso"] is None, f"sin datos no hay aviso de receptor: {gasto['aviso']!r}"


def cantidad(m: Mundo, tabla: str) -> int:
    return int(m.uno(f"SELECT count(*) FROM {tabla}"))  # noqa: S608 - nombres fijos de la aceptación


def en_el_libro(m: Mundo) -> int:
    return sum(cantidad(m, tabla) for tabla in LIBRO)


def categoria_y_grupo(m: Mundo, complejo: UUID | None = None) -> tuple[str, str]:
    """Una categoría y un grupo de reparto nuevos del edificio, por la API del 3a (como el test del 6)."""
    ruta = f"/api/complejos/{complejo or m.edificio}"
    nombre = f"Prueba factura {uuid4().hex[:8]}"
    m.como("super_admin")
    c = m.cliente.post(f"{ruta}/categorias", json={"nombre": nombre})
    assert c.status_code == 201, f"sembrar categoría: {c.status_code} {c.text[:200]}"
    g = m.cliente.post(f"{ruta}/grupos", json={"nombre": nombre, "metodo": "coeficiente", "unidades": []})
    assert g.status_code == 201, f"sembrar grupo: {g.status_code} {g.text[:200]}"
    m.como("admin_principal")
    return str(c.json()["id"]), str(g.json()["id"])


def gasto_del_6(m: Mundo, *, nro: int, cuit: str = CUIT_DEL_PROVEEDOR, pto: str = "3", tipo: str = "11",
                receptor: str | None = None, importe: str = "1000.00", complejo: UUID | None = None) -> Any:
    """El alta manual de `POST /gastos` del 6 (devuelve la respuesta, no la exige)."""
    categoria, grupo = categoria_y_grupo(m, complejo)
    cuerpo: dict[str, Any] = {
        "concepto": "Servicio de prueba", "categoria_id": categoria, "grupo_id": grupo, "periodo": "2026-10-01",
        "importe": importe, "cuit_emisor": cuit, "punto_de_venta": pto, "tipo_de_comprobante": tipo,
        "numero_de_comprobante": str(nro)}
    if receptor is not None:
        cuerpo["documento_receptor"] = receptor
    return m.cliente.post(f"/api/complejos/{complejo or m.edificio}/gastos", json=cuerpo)


def firmar_de_factura(m: Mundo, gasto_id: str, *, vence_en: datetime | None = None, administracion: UUID | None = None,
                      tipo: str = "factura") -> str:
    """Un token firmado como el servidor lo firma (`compartido.enlaces`, tipo `factura`, datos `a` y `g`)."""
    from proptech_core.compartido.enlaces import firmar

    return firmar(tipo, {"a": str(administracion or m.admin), "g": gasto_id},
                  vence_en=vence_en or datetime.now(UTC) + timedelta(minutes=5), clave=CLAVE_DE_ENLACES)


def url_de_la_factura(gasto: dict[str, Any]) -> str:
    factura = gasto["factura"]
    assert isinstance(factura, dict) and set(factura) == {"url", "vence_en"}, f"`factura` tiene que ser {{url, vence_en}}: {factura!r}"
    return str(factura["url"])


# === H-037: la lectura con IA ===================================================================================

TAREA = "leer_factura_con_ia"
MODELO_DE_PRUEBA = "proveedor/modelo-de-prueba"
CAMPOS_DEL_BORRADOR = ("importe", "concepto", "periodo", "categoria_id", "grupo_id")
#: Lo que trae el QR y la IA no puede tocar nunca (N01).
CAMPOS_INTOCABLES = ("proveedor_id", "cuit_emisor", "punto_de_venta", "tipo_de_comprobante",
                     "numero_de_comprobante", "fecha_de_factura", "documento_receptor", "importe", "tipo",
                     "origen", "motivo_sin_qr", "periodo_de_imputacion", "complejo_id")


@dataclass
class UsoFalso:
    """Lo que el puerto devuelve de una llamada (duck typing de `LecturaDeIa`, CONTRATO.md)."""

    propuesta: Any
    modelo: str = MODELO_DE_PRUEBA
    tokens_entrada: int = 1200
    tokens_salida: int = 80
    costo: str = "0.001234"


class ErrorDeIaFalso(Exception):
    """Una llamada que falló después de gastar (los atributos de uso son opcionales en el contrato)."""

    def __init__(self, mensaje: str = "la IA falló", *, tokens_entrada: int | None = None,
                 tokens_salida: int | None = None, costo: str | None = None) -> None:
        super().__init__(mensaje)
        if tokens_entrada is not None:
            self.tokens_entrada = tokens_entrada
        if tokens_salida is not None:
            self.tokens_salida = tokens_salida
        if costo is not None:
            self.costo = costo


class LectorDeIaFalso:
    """El puerto `LectorDeFacturaConIa` de `proptech_core.gastos.puertos`, con respuesta a medida."""

    modelo = MODELO_DE_PRUEBA

    def __init__(self, propuesta: Any = None, *, falla: Exception | None = None, uso: UsoFalso | None = None) -> None:
        self.propuesta = propuesta
        self.falla = falla
        self.uso = uso
        self.llamadas: list[dict[str, Any]] = []

    def leer(self, contenido: bytes, tipo: str, *, categorias: Any, grupos: Any) -> Any:
        self.llamadas.append({"contenido": contenido, "tipo": tipo, "categorias": [dict(c) for c in categorias],
                              "grupos": [dict(g) for g in grupos]})
        if self.falla is not None:
            raise self.falla
        return self.uso or UsoFalso(self.propuesta)


def propuesta_buena(categoria: str, grupo: str, **cambios: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"concepto": "Mantenimiento de ascensores, octubre", "periodo": "2026-10",
                            "categoria_id": categoria, "grupo_id": grupo, "importe": "1500.50"}
    base.update(cambios)
    return base


def tarea_del_worker() -> Any:
    from proptech_worker import tareas

    tarea = getattr(tareas, TAREA, None)
    assert tarea is not None, f"falta la tarea `proptech_worker.tareas.{TAREA}` (CONTRATO.md)"
    return tarea


def _ctx(m: Mundo, lector: Any, intento: int = 1) -> dict[str, Any]:
    from proptech_core.compartido.reintentos import PoliticaReintentos

    return {"fabrica_de_sesiones": m.fabrica, "politica": PoliticaReintentos(espera_base=0.01, intentos_maximos=3),
            "job_try": intento, "cola": m.cola, "lector_de_facturas": lector}


def correr_la_tarea(m: Mundo, gasto_id: str, lector: Any, *, clave: str | None = None,
                    administracion: UUID | None = None) -> Any:
    """La tarea del worker con su `ctx` armado a mano (como los tests del PDF de la expensa del 7)."""
    import asyncio

    tarea = tarea_del_worker()
    return asyncio.run(tarea(_ctx(m, lector), request_id=str(uuid4()), clave=clave or f"leer-factura:{gasto_id}",
                             administracion_id=str(administracion or m.admin), gasto_id=gasto_id))


def encolado(m: Mundo, gasto_id: str) -> list[dict[str, Any]]:
    return [datos for tarea, datos in m.cola.llamadas if tarea == TAREA and datos.get("gasto_id") == gasto_id]


def gasto(m: Mundo, gasto_id: str) -> dict[str, Any]:
    r = m.cliente.get(f"/api/gastos/{gasto_id}")
    assert r.status_code == 200, f"GET /gastos/{gasto_id}: {r.status_code} {r.text[:200]}"
    return r.json()


def lectura(m: Mundo, gasto_id: str) -> dict[str, Any]:
    """`GET /api/gastos/{id}/lectura` (CONTRATO.md): `datos_de`, `motivo` y `detalle`."""
    r = m.cliente.get(f"/api/gastos/{gasto_id}/lectura")
    assert r.status_code == 200, f"GET /gastos/{gasto_id}/lectura: se esperaba 200, llegó {r.status_code}: {r.text[:200]}"
    cuerpo = r.json()
    assert set(cuerpo) == {"estado", "datos_de", "motivo", "detalle"}, f"claves de la lectura: {sorted(cuerpo)}"
    assert set(cuerpo["datos_de"]) == set(CAMPOS_DEL_BORRADOR), f"datos_de: {sorted(cuerpo['datos_de'])}"
    return cuerpo


def leida(m: Mundo, datos: dict[str, Any] | str, lector: Any, *, dominio: str = "www.arca.gob.ar") -> str:
    """Sube la factura con ese QR, corre la tarea con ese lector y devuelve el id del gasto."""
    subido = subir_qr(m, datos, dominio=dominio)
    correr_la_tarea(m, str(subido["id"]), lector)
    return str(subido["id"])


def leida_sin_qr(m: Mundo, lector: Any) -> str:
    subido = creada(m, png_sin_qr())
    correr_la_tarea(m, str(subido["id"]), lector)
    return str(subido["id"])


def llamadas(m: Mundo, gasto_id: str | None = None) -> list[dict[str, Any]]:
    """Las filas de `llamada_de_ia`, de la más vieja a la más nueva."""
    existe = m.uno("SELECT to_regclass('llamada_de_ia') IS NOT NULL")
    assert existe, "falta la tabla `llamada_de_ia` (migración de H-037, CONTRATO.md)"
    filtro, parametros = ("WHERE gasto_id = %s", (gasto_id,)) if gasto_id else ("", ())
    filas = m.filas("SELECT gasto_id::text, complejo_id::text, modelo, tokens_entrada, tokens_salida, costo_usd, "
                    f"resultado FROM llamada_de_ia {filtro} ORDER BY creada_en, id", parametros)  # noqa: S608
    return [{"gasto_id": f[0], "complejo_id": f[1], "modelo": f[2], "tokens_entrada": f[3], "tokens_salida": f[4],
             "costo_usd": f[5], "resultado": f[6]} for f in filas]


def datos_intocables(g: dict[str, Any]) -> dict[str, Any]:
    return {c: g[c] for c in CAMPOS_INTOCABLES}


def proveedor_con_aprobados(m: Mundo, importes: list[str], *, cuit: str = CUIT_DEL_PROVEEDOR,
                            complejo: UUID | None = None, periodo: str = "2026-08-01") -> str:
    """El proveedor del edificio (por la API del 6) con un gasto aprobado por cada importe; devuelve su id."""
    edificio = complejo or m.edificio
    r = m.cliente.post(f"/api/complejos/{edificio}/proveedores", json={"razon_social": "Proveedor Ficticio S.A.",
                                                                       "cuit": cuit})
    assert r.status_code == 201, f"sembrar proveedor: {r.status_code} {r.text[:200]}"
    proveedor = str(r.json()["id"])
    for importe in importes:
        aprobado_del_6(m, proveedor, importe, cuit=cuit, complejo=edificio, periodo=periodo)
    return proveedor


def aprobado_del_6(m: Mundo, proveedor: str, importe: str, *, cuit: str = CUIT_DEL_PROVEEDOR, aprobar: bool = True,
                   complejo: UUID | None = None, periodo: str = "2026-08-01") -> str:
    edificio = complejo or m.edificio
    categoria, grupo = categoria_y_grupo(m, edificio)
    r = m.cliente.post(f"/api/complejos/{edificio}/gastos", json={
        "concepto": "Servicio anterior", "categoria_id": categoria, "grupo_id": grupo, "periodo": periodo,
        "importe": importe, "proveedor_id": proveedor, "cuit_emisor": cuit, "punto_de_venta": "9",
        "tipo_de_comprobante": "11", "numero_de_comprobante": str(m.numero_nuevo())})
    assert r.status_code == 201, f"sembrar gasto: {r.status_code} {r.text[:200]}"
    gasto_id = str(r.json()["id"])
    if aprobar:
        a = m.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
        assert a.status_code == 200, f"sembrar aprobación: {a.status_code} {a.text[:200]}"
    return gasto_id


def desactivar(m: Mundo, ruta: str, id_: str) -> None:
    m.como("super_admin")
    r = m.cliente.patch(f"/api/{ruta}/{id_}", json={"activa" if ruta == "categorias" else "activo": False})
    assert r.status_code == 200, f"desactivar {ruta}: {r.status_code} {r.text[:200]}"
    m.como("admin_principal")
