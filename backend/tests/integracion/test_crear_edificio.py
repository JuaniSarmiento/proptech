"""Alta atómica con parámetros recibidos, como proptech_app (5.1)."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.parametros import CategoriaDeGasto, leer_parametros
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.complejos.aplicacion import escritura
from proptech_core.complejos.aplicacion.errores import Conflicto

pytestmark = pytest.mark.integracion
PARAMETROS = Path(__file__).resolve().parents[3] / "config/parametros.yaml"


def reloj() -> datetime:
    return datetime(2026, 11, 1, 15, tzinfo=UTC)


def test_alta_copia_todos_los_valores(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    parametros = leer_parametros(str(PARAMETROS))
    request = uuid4()
    edificio = escritura.crear_edificio(
        sesion_edificio,
        identidad_edificio,
        nombre="Edificio ficticio",
        localidad="Mendoza",
        parametros=parametros,
        reloj=reloj,
        request_id=request,
    )
    assert sesion_edificio.execute(
        text(
            "SELECT administracion_id, nombre, localidad, "
            "estado_migracion FROM complejo WHERE id=:id"
        ),
        {"id": edificio},
    ).one() == (identidad_edificio.administracion_id, "Edificio ficticio", "Mendoza", "pendiente")
    fila = (
        sesion_edificio.execute(
            text("SELECT * FROM configuracion_versionada WHERE complejo_id=:id"), {"id": edificio}
        )
        .mappings()
        .one()
    )
    assert (
        str(fila["tasa_mensual"]),
        fila["dias_de_gracia"],
        fila["forma_de_calculo"],
        str(fila["porcentaje_fondo"]),
        fila["dia_de_vencimiento"],
        fila["modalidad_de_vencimiento"],
        fila["dia_segundo_vencimiento"],
        fila["recargo_segundo_vencimiento"],
        fila["autor_id"],
        fila["vigente_desde"],
    ) == (
        "3.00",
        0,
        "proporcional_por_dia",
        "0.00",
        parametros.vencimiento.dia,
        "unico",
        None,
        None,
        identidad_edificio.persona_id,
        reloj().date(),
    )
    categorias = sesion_edificio.execute(
        text(
            "SELECT clave, nombre, activa FROM categoria_de_gasto "
            "WHERE complejo_id=:id ORDER BY orden"
        ),
        {"id": edificio},
    ).all()
    assert categorias == [(c.clave, c.nombre, True) for c in parametros.categorias_de_gasto]
    assert len(categorias) == 9
    assert sesion_edificio.execute(
        text(
            "SELECT clave, nombre, metodo, es_generales, modo_de_coeficientes "
            "FROM grupo_de_reparto WHERE complejo_id=:id"
        ),
        {"id": edificio},
    ).all() == [("generales", "Generales", "coeficiente", True, "renormalizado")]
    assert sesion_edificio.execute(
        text("SELECT accion, entidad_id, persona_id, request_id, detalle FROM auditoria")
    ).one() == (
        "crear_edificio",
        edificio,
        identidad_edificio.persona_id,
        request,
        {"complejo_id": str(edificio)},
    )


def test_categorias_con_nombre_repetido_sin_mayusculas_da_conflicto_no_500(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """R3A-2 (L-018), segunda capa: `leer_parametros` ya rechaza esto al
    arrancar, pero si a `crear_edificio` igual le llega un `Parametros` con
    nombres de categoría repetidos sin distinguir mayúsculas (construido a
    mano, sin pasar por el lector), la `UniqueViolation` de
    `uq_categoria_nombre` no tiene que escapar cruda (500): tiene que
    traducirse al mismo `Conflicto` que ya usa `categorias.crear_categoria`."""
    parametros = leer_parametros(str(PARAMETROS))
    parametros = parametros.model_copy(
        update={
            "categorias_de_gasto": [
                *parametros.categorias_de_gasto,
                CategoriaDeGasto(clave="limpieza_bis", nombre="LIMPIEZA"),
            ]
        }
    )
    with pytest.raises(Conflicto) as exc_info:
        escritura.crear_edificio(
            sesion_edificio,
            identidad_edificio,
            nombre="Edificio",
            localidad="Mendoza",
            parametros=parametros,
            reloj=reloj,
            request_id=uuid4(),
        )
    assert exc_info.value.campo == "categorias_de_gasto"
    for tabla in ("complejo", "configuracion_versionada", "categoria_de_gasto", "auditoria"):
        consulta = f"SELECT count(*) FROM {tabla}"  # noqa: S608 - tablas literales del test
        assert sesion_edificio.execute(text(consulta)).scalar_one() == 0


def test_configuracion_inicial_y_parametros_nuevos_no_alteran_el_primero(
    sesion_edificio: Session,
    identidad_edificio: Identidad,
) -> None:
    from proptech_core.complejos.dominio.configuracion import ConfiguracionEdificio

    parametros = leer_parametros(str(PARAMETROS))
    inicial = ConfiguracionEdificio.desde_parametros(parametros).model_copy(
        update={
            "tasa_mensual": Porcentaje("5.00"),
            "porcentaje_fondo": Porcentaje("2.00"),
        }
    )
    primero = escritura.crear_edificio(
        sesion_edificio,
        identidad_edificio,
        nombre="Primero",
        localidad="Mendoza",
        parametros=parametros,
        configuracion_inicial=inicial,
        reloj=reloj,
        request_id=uuid4(),
    )
    otros = parametros.model_copy(
        update={
            "intereses": parametros.intereses.model_copy(update={"tasa_mensual": Decimal("4.00")})
        }
    )
    segundo = escritura.crear_edificio(
        sesion_edificio,
        identidad_edificio,
        nombre="Segundo",
        localidad="Mendoza",
        parametros=otros,
        reloj=reloj,
        request_id=uuid4(),
    )
    assert sesion_edificio.execute(
        text(
            "SELECT complejo_id, tasa_mensual::text, porcentaje_fondo::text "
            "FROM configuracion_versionada ORDER BY tasa_mensual DESC"
        )
    ).all() == [(primero, "5.00", "2.00"), (segundo, "4.00", "0.00")]


def test_falla_despues_de_auditar_revierte_todo(
    sesion_edificio: Session, identidad_edificio: Identidad, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = registrar

    def falla(*args: object, **kwargs: object) -> None:
        original(*args, **kwargs)  # type: ignore[arg-type]
        assert sesion_edificio.execute(text("SELECT count(*) FROM auditoria")).scalar_one() == 1
        raise RuntimeError("falla forzada")

    monkeypatch.setattr(escritura, "registrar", falla)
    with pytest.raises(RuntimeError, match="falla forzada"):
        escritura.crear_edificio(
            sesion_edificio,
            identidad_edificio,
            nombre="Fallido",
            localidad="Mendoza",
            parametros=leer_parametros(str(PARAMETROS)),
            reloj=reloj,
            request_id=uuid4(),
        )
    for tabla in (
        "complejo",
        "configuracion_versionada",
        "grupo_de_reparto",
        "categoria_de_gasto",
        "auditoria",
    ):
        consulta = f"SELECT count(*) FROM {tabla}"  # noqa: S608 - tablas literales del test
        assert sesion_edificio.execute(text(consulta)).scalar_one() == 0
