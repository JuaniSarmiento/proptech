"""Una liquidación emitida mínima, para los tests de base de los documentos de expensa (H-015)."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir, registrar_emision

from ._cuenta_corriente import Mundo, sesion_app
from ._edificios import BaseDeEdificio, fijar_tenant

PERIODO = date(2026, 11, 1)


@dataclass(frozen=True)
class Liquidada:
    liquidacion_id: UUID
    unidad_id: UUID


def liquidar(base: BaseDeEdificio, mundo: Mundo, *, de_b: bool = False) -> Liquidada:
    """La emisión del libro más su `liquidacion` y su línea, de la administración A o de la B."""
    admin = mundo.admin_b if de_b else mundo.admin
    complejo = mundo.complejo_b if de_b else mundo.complejo
    persona = mundo.persona_b if de_b else mundo.persona
    unidad = mundo.unidad_b if de_b else mundo.unidades[0]
    emision, liquidacion = uuid4(), uuid4()
    identidad = mundo.identidad_b if de_b else mundo.identidad
    with sesion_app(base, admin) as s:
        registrar_emision(
            s,
            identidad,
            emision_id=emision,
            complejo_id=complejo,
            periodo=PERIODO,
            obligaciones=[
                ObligacionAEmitir(
                    unidad, date(2026, 11, 10), Dinero("100.00"), Dinero("5.00"), Dinero("0.00")
                )
            ],
            request_id=uuid4(),
        )
        s.commit()
    with base.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, admin)
        c.execute(
            "INSERT INTO liquidacion (id, administracion_id, complejo_id, emision_id, periodo, "
            "huella, version_de_configuracion_id, porcentaje_fondo, vencimiento, total_gastos, "
            "total_notas_de_credito, total_fondo_de_reserva, total_prorrateado, "
            "total_cargos_particulares, total_intereses, total, emitida_por, request_id, "
            "emitida_en) VALUES (%s, %s, %s, %s, %s, 'h', %s, '5.00', '2026-11-10', '100.00', "
            "'0.00', '5.00', '105.00', '0.00', '0.00', '105.00', %s, %s, now())",
            (liquidacion, admin, complejo, emision, PERIODO, uuid4(), persona, uuid4()),
        )
        c.execute(
            "INSERT INTO linea_de_liquidacion (administracion_id, complejo_id, liquidacion_id, "
            "orden, unidad_id, identificador, ordinaria, fondo_de_reserva, extraordinaria, "
            "intereses, total, sin_obligacion, saldo_anterior, cargos_particulares, por_grupo) "
            "VALUES (%s, %s, %s, 0, %s, 'U000', '100.00', '5.00', '0.00', '0.00', '105.00', "
            "false, '0.00', '[]', '[]')",
            (admin, complejo, liquidacion, unidad),
        )
        c.commit()
    return Liquidada(liquidacion, unidad)


def documento(
    base: BaseDeEdificio, mundo: Mundo, liquidada: Liquidada, variante: str = "completa",
    *, de_b: bool = False,
) -> UUID:  # fmt: skip
    admin = mundo.admin_b if de_b else mundo.admin
    complejo = mundo.complejo_b if de_b else mundo.complejo
    with base.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, admin)
        fila = c.execute(
            "INSERT INTO documento_de_expensa (administracion_id, complejo_id, liquidacion_id, "
            "unidad_id, variante) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (admin, complejo, liquidada.liquidacion_id, liquidada.unidad_id, variante),
        ).fetchone()
        c.commit()
    assert fila is not None
    return UUID(str(fila[0]))
