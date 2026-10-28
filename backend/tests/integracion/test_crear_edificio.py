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
from proptech_core.compartido.georef import leer_georef
from proptech_core.compartido.parametros import CategoriaDeGasto, leer_parametros
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.complejos.aplicacion import escritura
from proptech_core.complejos.aplicacion.errores import Conflicto, EntradaInvalida

pytestmark = pytest.mark.integracion
PARAMETROS = Path(__file__).resolve().parents[3] / "config/parametros.yaml"
GEOREF = leer_georef(str(Path(__file__).resolve().parents[3] / "config/georef"))
#: Mendoza / Capital / "Mendoza" — ids reales, confirmados contra
#: `config/georef/` el 26/10/2026 (ver `_georef_real.py`).
PROVINCIA_ID = "50"
DEPARTAMENTO_ID = "50007"
LOCALIDAD_ID = "50007010"
#: D3 (tarea 3.2): un alta nueva siempre trae las dos cantidades.
PISOS = 4
SUBSUELOS = 1


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
        provincia_id=PROVINCIA_ID,
        departamento_id=DEPARTAMENTO_ID,
        localidad_id=LOCALIDAD_ID,
        georef=GEOREF,
        pisos=PISOS,
        subsuelos=SUBSUELOS,
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
            provincia_id=PROVINCIA_ID,
            departamento_id=DEPARTAMENTO_ID,
            localidad_id=LOCALIDAD_ID,
            georef=GEOREF,
            pisos=PISOS,
            subsuelos=SUBSUELOS,
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
        provincia_id=PROVINCIA_ID,
        departamento_id=DEPARTAMENTO_ID,
        localidad_id=LOCALIDAD_ID,
        georef=GEOREF,
        pisos=PISOS,
        subsuelos=SUBSUELOS,
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
        provincia_id=PROVINCIA_ID,
        departamento_id=DEPARTAMENTO_ID,
        localidad_id=LOCALIDAD_ID,
        georef=GEOREF,
        pisos=PISOS,
        subsuelos=SUBSUELOS,
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
            provincia_id=PROVINCIA_ID,
            departamento_id=DEPARTAMENTO_ID,
            localidad_id=LOCALIDAD_ID,
            georef=GEOREF,
            pisos=PISOS,
            subsuelos=SUBSUELOS,
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


@pytest.mark.parametrize(
    ("provincia_id", "departamento_id", "localidad_id", "campo_esperado"),
    [
        # Localidad de otro departamento (Godoy Cruz) con provincia y
        # departamento coherentes (Mendoza / Capital).
        (PROVINCIA_ID, DEPARTAMENTO_ID, "5002101001", "localidad_id"),
        # Departamento de otra provincia (San Juan) con la provincia Mendoza.
        (PROVINCIA_ID, "70126", "70126010", "departamento_id"),
        # Id de provincia que no existe.
        ("99", DEPARTAMENTO_ID, LOCALIDAD_ID, "provincia_id"),
    ],
)
def test_trio_incoherente_rechaza_sin_crear_nada(
    sesion_edificio: Session,
    identidad_edificio: Identidad,
    provincia_id: str,
    departamento_id: str,
    localidad_id: str,
    campo_esperado: str,
) -> None:
    """D2 (tarea 2.6): la aplicación es la autoridad sobre la coherencia del
    trío, nunca la base ni el cliente. Escenarios "Localidad de otro
    departamento", "Departamento de otra provincia" e "Id que no existe"."""
    with pytest.raises(EntradaInvalida) as exc_info:
        escritura.crear_edificio(
            sesion_edificio,
            identidad_edificio,
            nombre="Incoherente",
            provincia_id=provincia_id,
            departamento_id=departamento_id,
            localidad_id=localidad_id,
            georef=GEOREF,
            pisos=PISOS,
            subsuelos=SUBSUELOS,
            parametros=leer_parametros(str(PARAMETROS)),
            reloj=reloj,
            request_id=uuid4(),
        )
    assert exc_info.value.campo == campo_esperado
    assert sesion_edificio.execute(text("SELECT count(*) FROM complejo")).scalar_one() == 0


def test_localidad_se_escribe_derivada_del_nombre_de_georef(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """D2: la ubicación y `localidad` quedan guardadas con los tres ids y el
    nombre real de Georef — nunca un valor que el cliente pudiera mandar
    (la API ya no acepta `localidad` como entrada, tarea 2.6). Escenario
    "Trío coherente"."""
    edificio = escritura.crear_edificio(
        sesion_edificio,
        identidad_edificio,
        nombre="Con ubicación",
        provincia_id=PROVINCIA_ID,
        departamento_id="50021",
        localidad_id="5002101001",
        georef=GEOREF,
        pisos=PISOS,
        subsuelos=SUBSUELOS,
        calle_y_numero="Alsina 123",
        parametros=leer_parametros(str(PARAMETROS)),
        reloj=reloj,
        request_id=uuid4(),
    )
    assert sesion_edificio.execute(
        text(
            "SELECT provincia_id, departamento_id, localidad_id, calle_y_numero, localidad "
            "FROM complejo WHERE id=:id"
        ),
        {"id": edificio},
    ).one() == (PROVINCIA_ID, "50021", "5002101001", "Alsina 123", "Ciudad de Godoy Cruz")


def test_alta_sin_calle_queda_vacia(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """Escenario "Alta sin calle": el alta es exitosa y la calle queda nula."""
    edificio = escritura.crear_edificio(
        sesion_edificio,
        identidad_edificio,
        nombre="Sin calle",
        provincia_id=PROVINCIA_ID,
        departamento_id=DEPARTAMENTO_ID,
        localidad_id=LOCALIDAD_ID,
        georef=GEOREF,
        pisos=PISOS,
        subsuelos=SUBSUELOS,
        parametros=leer_parametros(str(PARAMETROS)),
        reloj=reloj,
        request_id=uuid4(),
    )
    assert (
        sesion_edificio.execute(
            text("SELECT calle_y_numero FROM complejo WHERE id=:id"), {"id": edificio}
        ).scalar_one()
        is None
    )


@pytest.mark.parametrize(
    ("pisos", "subsuelos", "campo_esperado"),
    [
        (61, SUBSUELOS, "pisos"),
        (0, SUBSUELOS, "pisos"),
        (-1, SUBSUELOS, "pisos"),
        (PISOS, -1, "subsuelos"),
        (PISOS, 6, "subsuelos"),
    ],
)
def test_pisos_o_subsuelos_fuera_de_rango_rechaza_sin_crear_nada(
    sesion_edificio: Session,
    identidad_edificio: Identidad,
    pisos: int,
    subsuelos: int,
    campo_esperado: str,
) -> None:
    """Escenario "Cantidades fuera de rango" de `edificios-y-unidades`."""
    with pytest.raises(EntradaInvalida) as exc_info:
        escritura.crear_edificio(
            sesion_edificio,
            identidad_edificio,
            nombre="Fuera de rango",
            provincia_id=PROVINCIA_ID,
            departamento_id=DEPARTAMENTO_ID,
            localidad_id=LOCALIDAD_ID,
            georef=GEOREF,
            pisos=pisos,
            subsuelos=subsuelos,
            parametros=leer_parametros(str(PARAMETROS)),
            reloj=reloj,
            request_id=uuid4(),
        )
    assert exc_info.value.campo == campo_esperado
    assert sesion_edificio.execute(text("SELECT count(*) FROM complejo")).scalar_one() == 0


def test_pisos_y_subsuelos_se_guardan_completos(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    """Escenario "Edificio nuevo sin pisos completados" (contraparte: acá se
    confirma que, cuando SÍ se mandan, quedan completos — nunca `NULL` para
    un alta nueva)."""
    edificio = escritura.crear_edificio(
        sesion_edificio,
        identidad_edificio,
        nombre="Con pisos",
        provincia_id=PROVINCIA_ID,
        departamento_id=DEPARTAMENTO_ID,
        localidad_id=LOCALIDAD_ID,
        georef=GEOREF,
        pisos=12,
        subsuelos=2,
        parametros=leer_parametros(str(PARAMETROS)),
        reloj=reloj,
        request_id=uuid4(),
    )
    assert sesion_edificio.execute(
        text("SELECT pisos, subsuelos FROM complejo WHERE id=:id"), {"id": edificio}
    ).one() == (12, 2)
