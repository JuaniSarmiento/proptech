"""Vigencias, reloj de Mendoza y cierre de migración (5.5)."""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from psycopg.errors import UniqueViolation
from sqlalchemy import event, text
from sqlalchemy.engine import ExceptionContext
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.parametros import leer_parametros
from proptech_core.complejos.aplicacion import escritura, lectura
from proptech_core.complejos.aplicacion.errores import Conflicto, EntradaInvalida
from proptech_core.complejos.dominio.configuracion import ConfiguracionEdificio

from .test_crear_edificio import (
    DEPARTAMENTO_ID,
    GEOREF,
    LOCALIDAD_ID,
    PARAMETROS,
    PROVINCIA_ID,
    reloj,
)
from .test_unidades_casos_de_uso import crear

pytestmark = pytest.mark.integracion


def configuracion(**cambios: Any) -> ConfiguracionEdificio:
    base = ConfiguracionEdificio.desde_parametros(leer_parametros(str(PARAMETROS)))
    return ConfiguracionEdificio.model_validate({**base.model_dump(mode="json"), **cambios})


def version(
    sesion: Session, identidad: Identidad, edificio: UUID, fecha: date, **cambios: Any
) -> UUID:
    return escritura.crear_version_de_configuracion(
        sesion,
        identidad,
        complejo_id=edificio,
        configuracion=configuracion(**cambios),
        vigente_desde=fecha,
        reloj=reloj,
        parametros=leer_parametros(str(PARAMETROS)),
        request_id=uuid4(),
    )


def test_cambiar_tasa_y_doble_vencimiento_conserva_anterior(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    anterior = lectura.listar_versiones(sesion_edificio, edificio)[0]
    nueva = version(
        sesion_edificio,
        identidad_edificio,
        edificio,
        date(2026, 11, 2),
        tasa_mensual="4.00",
        modalidad_de_vencimiento="doble",
        dia_segundo_vencimiento=20,
        recargo_segundo_vencimiento="5.00",
    )
    versiones = lectura.listar_versiones(sesion_edificio, edificio)
    assert len(versiones) == 2
    assert versiones[0] == anterior
    assert anterior["modalidad_de_vencimiento"] == "unico"
    assert anterior["recargo_segundo_vencimiento"] is None
    assert versiones[1]["id"] == nueva
    assert versiones[1]["tasa_mensual"] == "4.00"
    assert versiones[1]["modalidad_de_vencimiento"] == "doble"
    assert versiones[1]["dia_segundo_vencimiento"] == 20
    assert versiones[1]["recargo_segundo_vencimiento"] == "5.00"
    assert versiones[1]["autor_id"] == identidad_edificio.persona_id
    assert isinstance(versiones[1]["creada_en"], datetime)
    assert versiones[1]["creada_en"].tzinfo is not None
    assert sesion_edificio.execute(
        text(
            "SELECT detalle, persona_id, entidad_id FROM auditoria "
            "WHERE accion='crear_version_de_configuracion'"
        )
    ).one() == (
        {"complejo_id": str(edificio), "vigente_desde": "2026-11-02"},
        identidad_edificio.persona_id,
        edificio,
    )


def test_ayer_es_invalido_y_no_deja_nada(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    antes = lectura.listar_versiones(sesion_edificio, edificio)
    with pytest.raises(EntradaInvalida) as error:
        version(sesion_edificio, identidad_edificio, edificio, date(2026, 10, 31))
    assert error.value.campo == "vigente_desde"
    assert lectura.listar_versiones(sesion_edificio, edificio) == antes
    assert (
        sesion_edificio.execute(
            text("SELECT count(*) FROM auditoria WHERE accion='crear_version_de_configuracion'")
        ).scalar_one()
        == 0
    )


@pytest.mark.parametrize(
    ("instante", "hoy"),
    [
        (datetime(2026, 11, 2, 2, 30, tzinfo=UTC), date(2026, 11, 1)),  # 23:30 Mendoza
        (datetime(2026, 11, 2, 3, 30, tzinfo=UTC), date(2026, 11, 2)),  # 00:30 Mendoza
    ],
)
def test_hoy_es_mendoza_alrededor_de_medianoche(
    sesion_edificio: Session, identidad_edificio: Identidad, instante: datetime, hoy: date
) -> None:
    parametros = leer_parametros(str(PARAMETROS))
    edificio = escritura.crear_edificio(
        sesion_edificio,
        identidad_edificio,
        nombre="Reloj",
        provincia_id=PROVINCIA_ID,
        departamento_id=DEPARTAMENTO_ID,
        localidad_id=LOCALIDAD_ID,
        georef=GEOREF,
        parametros=parametros,
        reloj=lambda: datetime(2026, 10, 30, 12, tzinfo=UTC),
        request_id=uuid4(),
    )
    nueva = escritura.crear_version_de_configuracion(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        configuracion=configuracion(),
        vigente_desde=hoy,
        reloj=lambda: instante,
        parametros=parametros,
        request_id=uuid4(),
    )
    assert lectura.listar_versiones(sesion_edificio, edificio)[-1]["id"] == nueva
    assert lectura.listar_versiones(sesion_edificio, edificio)[-1]["vigente_desde"] == hoy
    with pytest.raises(EntradaInvalida):
        escritura.crear_version_de_configuracion(
            sesion_edificio,
            identidad_edificio,
            complejo_id=edificio,
            configuracion=configuracion(),
            vigente_desde=hoy - timedelta(days=1),
            reloj=lambda: instante,
            parametros=parametros,
            request_id=uuid4(),
        )


def test_fecha_repetida_traduce_unique_real_sin_auditoria(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    antes = lectura.listar_versiones(sesion_edificio, edificio)
    observados: list[BaseException] = []

    def observar(contexto: ExceptionContext) -> None:
        observados.append(contexto.original_exception)

    engine = sesion_edificio.get_bind()
    event.listen(engine, "handle_error", observar)
    try:
        with pytest.raises(Conflicto) as error:
            version(
                sesion_edificio,
                identidad_edificio,
                edificio,
                date(2026, 11, 1),
                tasa_mensual="4.00",
            )
    finally:
        event.remove(engine, "handle_error", observar)
    assert error.value.campo == "vigente_desde"
    assert len(observados) == 1 and isinstance(observados[0], UniqueViolation)
    assert lectura.listar_versiones(sesion_edificio, edificio) == antes
    assert (
        sesion_edificio.execute(
            text("SELECT count(*) FROM auditoria WHERE accion='crear_version_de_configuracion'")
        ).scalar_one()
        == 0
    )


def test_vigente_para_fecha_y_antes_de_la_primera(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    # `configuracion_vigente` no trae `autor_nombre` (D5, tarea 2.2: sólo
    # el historial lo necesita); se lo descarta para comparar el resto.
    anterior = {
        k: v
        for k, v in lectura.listar_versiones(sesion_edificio, edificio)[0].items()
        if k != "autor_nombre"
    }
    nueva = version(
        sesion_edificio, identidad_edificio, edificio, date(2026, 12, 1), tasa_mensual="4.00"
    )
    assert lectura.configuracion_vigente(sesion_edificio, edificio, date(2026, 11, 15)) == anterior
    vigente = lectura.configuracion_vigente(sesion_edificio, edificio, date(2026, 12, 1))
    assert vigente is not None
    assert vigente["id"] == nueva
    assert lectura.configuracion_vigente(sesion_edificio, edificio, date(2026, 10, 31)) is None


def test_confirmar_solo_desde_pendiente_con_auditoria(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    request = uuid4()
    escritura.confirmar_sin_saldos_previos(
        sesion_edificio, identidad_edificio, complejo_id=edificio, request_id=request
    )
    assert (
        sesion_edificio.execute(
            text("SELECT estado_migracion FROM complejo WHERE id=:id"), {"id": edificio}
        ).scalar_one()
        == "sin_saldos_previos"
    )
    with pytest.raises(Conflicto) as error:
        escritura.confirmar_sin_saldos_previos(
            sesion_edificio, identidad_edificio, complejo_id=edificio, request_id=uuid4()
        )
    assert error.value.campo == "estado_migracion"
    assert sesion_edificio.execute(
        text(
            "SELECT entidad_id, detalle, persona_id, request_id FROM auditoria "
            "WHERE accion='confirmar_sin_saldos_previos'"
        )
    ).all() == [(edificio, {"complejo_id": str(edificio)}, identidad_edificio.persona_id, request)]
    otro = crear(sesion_edificio, identidad_edificio)
    sesion_edificio.execute(
        text("UPDATE complejo SET estado_migracion='confirmada' WHERE id=:id"), {"id": otro}
    )
    with pytest.raises(Conflicto):
        escritura.confirmar_sin_saldos_previos(
            sesion_edificio, identidad_edificio, complejo_id=otro, request_id=uuid4()
        )
