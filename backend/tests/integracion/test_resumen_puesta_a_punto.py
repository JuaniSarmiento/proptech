"""Resumen con la puesta a punto del edificio (D5, tarea 2.1).

`edificios-y-unidades` > Edificio recién creado; > Coeficientes en advertencia;
> Coeficientes fuera de tolerancia; > Grupo parcial vacío; > Edificio listo
para liquidar. "El vecino pide el resumen" ya está cubierto, sin cambios, por
`test_vecino_recibe_403_en_resumen_propio_y_404_en_otro` (API, mismo permiso).
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.complejos.aplicacion import escritura, grupos, lectura, unidades

from .test_crear_edificio import reloj
from .test_unidades_casos_de_uso import DATOS, crear

pytestmark = pytest.mark.integracion

_HOY = reloj().date()  # 2026-11-01, Mendoza (UTC-3) no cruza medianoche acá.


def alta_unidad(sesion: Session, identidad: Identidad, edificio: UUID, **cambios: str) -> UUID:
    return unidades.crear_unidad(
        sesion, identidad, complejo_id=edificio, datos={**DATOS, **cambios}, request_id=uuid4()
    )


def test_edificio_recien_creado(sesion_edificio: Session, identidad_edificio: Identidad) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    resumen = lectura.resumen_edificio(sesion_edificio, edificio, _HOY)
    assert resumen["nombre"] == "Ficticio"
    assert resumen["localidad"] == "Mendoza"
    assert resumen["cantidad_unidades"] == 0
    assert resumen["estado_migracion"] == "pendiente"
    assert resumen["pasos"] == {
        "ubicacion": "hecho",
        "unidades": "falta",
        "coeficientes": "falta",
        "grupos": "hecho",
        "categorias": "hecho",
        "intereses_y_vencimiento": "hecho",
        "saldos_previos": "falta",
    }
    assert resumen["listo_para_liquidar"] is False


def test_coeficientes_en_advertencia(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    alta_unidad(sesion_edificio, identidad_edificio, edificio, coeficiente="0.999900")
    resumen = lectura.resumen_edificio(sesion_edificio, edificio, _HOY)
    assert resumen["pasos"]["coeficientes"] == "hecho"
    assert resumen["informe"] == {
        "suma": "0.999900",
        "diferencia": "-0.000100",
        "estado": "advertencia",
    }


def test_coeficientes_fuera_de_tolerancia(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    alta_unidad(sesion_edificio, identidad_edificio, edificio, coeficiente="0.999800")
    resumen = lectura.resumen_edificio(sesion_edificio, edificio, _HOY)
    assert resumen["pasos"]["coeficientes"] == "falta"
    assert resumen["listo_para_liquidar"] is False


def test_grupo_parcial_vacio(sesion_edificio: Session, identidad_edificio: Identidad) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    grupos.crear_grupo(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        datos={"clave": "ascensor", "nombre": "Ascensor", "metodo": "coeficiente"},
        miembros=[],
        request_id=uuid4(),
    )
    resumen = lectura.resumen_edificio(sesion_edificio, edificio, _HOY)
    assert resumen["pasos"]["grupos"] == "falta"


def test_grupo_propios_fuera_de_tolerancia(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    unidad = alta_unidad(sesion_edificio, identidad_edificio, edificio)
    grupos.crear_grupo(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        datos={"clave": "ascensor", "nombre": "Ascensor", "metodo": "coeficiente"},
        miembros=[{"unidad_id": unidad, "coeficiente": "0.500000"}],
        modo="propios",
        request_id=uuid4(),
    )
    resumen = lectura.resumen_edificio(sesion_edificio, edificio, _HOY)
    assert resumen["pasos"]["grupos"] == "falta"


def test_todas_las_categorias_desactivadas(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    sesion_edificio.execute(
        text("UPDATE categoria_de_gasto SET activa=false WHERE complejo_id=:id"), {"id": edificio}
    )
    resumen = lectura.resumen_edificio(sesion_edificio, edificio, _HOY)
    assert resumen["pasos"]["categorias"] == "falta"


def test_edificio_listo_para_liquidar(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    edificio = crear(sesion_edificio, identidad_edificio)
    alta_unidad(sesion_edificio, identidad_edificio, edificio, coeficiente="1.000000")
    escritura.confirmar_sin_saldos_previos(
        sesion_edificio, identidad_edificio, complejo_id=edificio, request_id=uuid4()
    )
    resumen = lectura.resumen_edificio(sesion_edificio, edificio, _HOY)
    assert resumen["pasos"] == {
        "ubicacion": "hecho",
        "unidades": "hecho",
        "coeficientes": "hecho",
        "grupos": "hecho",
        "categorias": "hecho",
        "intereses_y_vencimiento": "hecho",
        "saldos_previos": "hecho",
    }
    assert resumen["listo_para_liquidar"] is True


def test_sin_edificio_da_no_encontrado(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    from proptech_core.complejos.aplicacion.errores import NoEncontrado

    with pytest.raises(NoEncontrado):
        lectura.resumen_edificio(sesion_edificio, UUID(int=0), _HOY)


def test_edificio_migrado_sin_ubicacion(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """Escenario "Edificio migrado sin ubicación" (D3, tarea 3.8)."""
    edificio = crear(sesion_edificio, identidad_edificio)
    sesion_edificio.execute(
        text(
            "UPDATE complejo SET provincia_id=NULL, departamento_id=NULL, "
            "localidad_id=NULL, localidad=NULL WHERE id=:id"
        ),
        {"id": edificio},
    )
    resumen = lectura.resumen_edificio(sesion_edificio, edificio, _HOY)
    assert resumen["pasos"]["ubicacion"] == "falta"
    assert resumen["listo_para_liquidar"] is False


def test_edificio_migrado_sin_pisos_completados(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """Escenario "ubicación completa, pisos/subsuelos completos" (D3,
    tarea 3.8): ubicación completa pero `pisos`/`subsuelos` sin completar."""
    edificio = crear(sesion_edificio, identidad_edificio)
    sesion_edificio.execute(
        text("UPDATE complejo SET pisos=NULL, subsuelos=NULL WHERE id=:id"), {"id": edificio}
    )
    resumen = lectura.resumen_edificio(sesion_edificio, edificio, _HOY)
    assert resumen["pasos"]["ubicacion"] == "falta"


def test_unidad_migrada_con_el_piso_sin_completar(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """Escenario "Unidad migrada con el piso sin completar": ubicación
    completa pero una unidad con el piso sin completar."""
    edificio = crear(sesion_edificio, identidad_edificio)
    unidad_id = alta_unidad(sesion_edificio, identidad_edificio, edificio)
    sesion_edificio.execute(text("UPDATE unidad SET piso=NULL WHERE id=:id"), {"id": unidad_id})
    resumen = lectura.resumen_edificio(sesion_edificio, edificio, _HOY)
    assert resumen["pasos"]["ubicacion"] == "falta"
    assert resumen["unidades_sin_piso_completo"] == 1
    assert resumen["listo_para_liquidar"] is False


def test_explain_de_unidades_sin_piso_completo(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """Evidencia de la tarea 3.8: mismo prefijo de índice que 3.5."""
    edificio = crear(sesion_edificio, identidad_edificio)
    filas = sesion_edificio.execute(
        text("EXPLAIN SELECT count(*) FROM unidad WHERE complejo_id=:id AND piso IS NULL"),
        {"id": edificio},
    ).all()
    plan = "\n".join(f[0] for f in filas)
    assert "uq_unidad_identificador" in plan, plan
