"""Datos inventados y SQL de prueba del esquema del libro, sin aplicación futura."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg import sql

from ._edificios import Edificios, fijar_tenant, insertar_unidad

LIBRO = ("cuenta", "emision", "evento_de_emision", "obligacion", "movimiento", "imputacion")


def insertar(c: psycopg.Connection, tabla: str, fila: dict[str, Any]) -> None:
    c.execute(
        sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(tabla),
            sql.SQL(", ").join(map(sql.Identifier, fila)),
            sql.SQL(", ").join(sql.Placeholder() for _ in fila),
        ),
        tuple(fila.values()),
    )


@dataclass
class Libro:
    conexion: psycopg.Connection
    edificios: Edificios
    persona: UUID = field(default_factory=uuid4)
    persona_libre: UUID = field(default_factory=uuid4)
    cuenta: UUID = field(default_factory=uuid4)
    cuenta_personal: UUID = field(default_factory=uuid4)
    cuenta_otro_edificio: UUID = field(default_factory=uuid4)
    cuenta_ajena: UUID = field(default_factory=uuid4)
    emision: UUID = field(default_factory=uuid4)
    obligacion: UUID = field(default_factory=uuid4)
    pago: UUID = field(default_factory=uuid4)
    pago_personal: UUID = field(default_factory=uuid4)
    interes: UUID = field(default_factory=uuid4)

    @property
    def admin(self) -> UUID:
        return self.edificios.administracion_a

    def fila(self, tabla: str, **cambios: Any) -> dict[str, Any]:
        base = {
            "id": uuid4(),
            "administracion_id": self.admin,
            "complejo_id": self.edificios.complejo_a,
        }
        registro = datetime(2026, 10, 26, tzinfo=UTC)
        datos: dict[str, dict[str, Any]] = {
            "cuenta": {"unidad_id": None, "persona_id": self.persona_libre, "creada_en": registro},
            "emision": {
                "periodo": date(2026, 10, 1),
                "intento": 1,
                "registrada_por": self.persona,
                "request_id": uuid4(),
                "registrada_en": registro,
            },
            "evento_de_emision": {
                "emision_id": self.emision,
                "tipo": "anulada",
                "motivo": "Prueba",
                "persona_id": self.persona,
                "request_id": uuid4(),
                "registrado_en": registro,
            },
            "obligacion": {
                "cuenta_id": self.cuenta,
                "emision_id": None,
                "operacion_id": uuid4(),
                "periodo": date(2026, 10, 1),
                "vencimiento": date(2026, 10, 10),
                "ordinaria": "100.00",
                "fondo_de_reserva": "2.00",
                "extraordinaria": "10.00",
                "registrada_en": registro,
            },
            "movimiento": {
                "cuenta_id": self.cuenta,
                "tipo": "pago",
                "sentido": "credito",
                "importe": "50.00",
                "fecha_valor": date(2026, 10, 26),
                "registrado_por": self.persona,
                "request_id": uuid4(),
                "registrado_en": registro,
                "operacion_id": uuid4(),
                "emision_id": None,
                "obligacion_id": None,
                "componente": None,
                "corte": None,
                "corrige_a": None,
                "tipo_corregido": None,
                "enlazado_a": None,
                "motivo": None,
            },
            "imputacion": {
                "cuenta_id": self.cuenta,
                "movimiento_id": self.pago,
                "sentido_del_movimiento": "credito",
                "obligacion_id": self.obligacion,
                "componente": "ordinaria",
                "importe": "10.00",
                "corrida_id": uuid4(),
                "registrada_en": registro,
            },
        }
        return {**base, **datos[tabla], **cambios}

    def agregar(self, tabla: str, **cambios: Any) -> dict[str, Any]:
        fila = self.fila(tabla, **cambios)
        insertar(self.conexion, tabla, fila)
        return fila

    def sembrar(self) -> None:
        c, e = self.conexion, self.edificios
        insertar(
            c,
            "persona",
            {"id": self.persona, "administracion_id": self.admin, "nombre": "Ficticia libro"},
        )
        self.agregar("cuenta", id=self.cuenta, unidad_id=e.unidad_a, persona_id=None)
        insertar(
            c,
            "persona",
            {"id": self.persona_libre, "administracion_id": self.admin, "nombre": "Sin cuenta"},
        )
        self.agregar("cuenta", id=self.cuenta_personal, persona_id=self.persona)
        self.agregar(
            "cuenta",
            id=self.cuenta_otro_edificio,
            complejo_id=e.otro_complejo_a,
            unidad_id=e.otra_unidad_a,
            persona_id=None,
        )
        fijar_tenant(c, e.administracion_b)
        self.agregar(
            "cuenta",
            id=self.cuenta_ajena,
            administracion_id=e.administracion_b,
            complejo_id=e.complejo_b,
            unidad_id=e.unidad_b,
            persona_id=None,
        )
        fijar_tenant(c, self.admin)
        self.agregar("emision", id=self.emision)
        self.agregar("obligacion", id=self.obligacion, emision_id=self.emision, operacion_id=None)
        self.agregar("movimiento", id=self.pago)
        self.agregar("movimiento", id=self.pago_personal, cuenta_id=self.cuenta_personal)
        self.agregar(
            "movimiento",
            id=self.interes,
            tipo="interes",
            sentido="debito",
            operacion_id=None,
            obligacion_id=self.obligacion,
            componente="interes",
            corte=date(2026, 10, 26),
        )


def sembrar_libro(c: psycopg.Connection) -> Libro:
    """Dataset independiente de los fixtures, para transacciones de rollback/propiedad."""
    aa, ab, ca, oa, cb = (uuid4() for _ in range(5))
    unidades = []
    for admin, complejos in ((aa, (ca, oa)), (ab, (cb,))):
        fijar_tenant(c, admin)
        insertar(c, "administracion", {"id": admin, "nombre": "Administración inventada"})
        for complejo in complejos:
            insertar(
                c,
                "complejo",
                {
                    "id": complejo,
                    "administracion_id": admin,
                    "nombre": "Edificio inventado",
                    "localidad": "Mendoza",
                },
            )
            unidades.append(insertar_unidad(c, admin, complejo))
    fijar_tenant(c, aa)
    datos = Libro(c, Edificios(aa, ab, ca, oa, cb, *unidades))
    datos.sembrar()
    return datos
