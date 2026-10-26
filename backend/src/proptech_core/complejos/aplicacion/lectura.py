"""Lectura mínima de `complejo`/`unidad` (D7, cambio 2a).

Nace acá, con lo mínimo que el candado necesita para cargar el recurso
dentro de la sesión ya filtrada por RLS (D5): `None` si no existe o es de
otra administración (RLS ya lo filtró). El resto del dominio de complejos
(crearlos, editarlos, D6) es del cambio 3; este módulo nunca importa
`acceso` (D-021, frontera verificada en `test_fronteras_de_modulos.py`).
"""

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.coeficientes import Coeficiente, informar_coeficientes
from proptech_core.complejos.aplicacion.errores import NoEncontrado


@dataclass(frozen=True)
class ComplejoLeido:
    id: UUID
    administracion_id: UUID
    nombre: str
    localidad: str
    estado_migracion: str


@dataclass(frozen=True)
class UnidadLeida:
    id: UUID
    administracion_id: UUID
    complejo_id: UUID
    identificador: str
    tipo: str
    piso: str
    coeficiente: str
    superficie_m2: str


def cargar_complejo(sesion: Session, complejo_id: UUID) -> ComplejoLeido | None:
    fila = sesion.execute(
        text(
            "SELECT id, administracion_id, nombre, localidad, estado_migracion "
            "FROM complejo WHERE id = :id"
        ),
        {"id": str(complejo_id)},
    ).first()
    if fila is None:
        return None
    return ComplejoLeido(
        id=fila.id,
        administracion_id=fila.administracion_id,
        nombre=fila.nombre,
        localidad=fila.localidad,
        estado_migracion=fila.estado_migracion,
    )


def listar_complejos(sesion: Session) -> list[ComplejoLeido]:
    return [
        ComplejoLeido(**dict(fila))
        for fila in sesion.execute(
            text(
                "SELECT id, administracion_id, nombre, localidad, estado_migracion "
                "FROM complejo ORDER BY nombre, id"
            )
        ).mappings()
    ]


def cargar_unidad(sesion: Session, unidad_id: UUID) -> UnidadLeida | None:
    fila = sesion.execute(
        text(
            "SELECT id, administracion_id, complejo_id, identificador, tipo, piso, "
            "coeficiente::text, superficie_m2::text FROM unidad WHERE id = :id"
        ),
        {"id": str(unidad_id)},
    ).first()
    if fila is None:
        return None
    return UnidadLeida(
        id=fila.id,
        administracion_id=fila.administracion_id,
        complejo_id=fila.complejo_id,
        identificador=fila.identificador,
        tipo=fila.tipo,
        piso=fila.piso,
        coeficiente=fila.coeficiente,
        superficie_m2=fila.superficie_m2,
    )


def cargar_grupo(sesion: Session, grupo_id: UUID) -> dict[str, Any] | None:
    fila = (
        sesion.execute(
            text("SELECT id, complejo_id FROM grupo_de_reparto WHERE id=:id"), {"id": grupo_id}
        )
        .mappings()
        .first()
    )
    return None if fila is None else dict(fila)


def cargar_categoria(sesion: Session, categoria_id: UUID) -> dict[str, Any] | None:
    fila = (
        sesion.execute(
            text("SELECT id, complejo_id FROM categoria_de_gasto WHERE id=:id"),
            {"id": categoria_id},
        )
        .mappings()
        .first()
    )
    return None if fila is None else dict(fila)


_COLUMNAS_CONFIGURACION = (
    "SELECT id, complejo_id, vigente_desde, tasa_mensual::text, dias_de_gracia, "
    "forma_de_calculo, porcentaje_fondo::text, dia_de_vencimiento, modalidad_de_vencimiento, "
    "dia_segundo_vencimiento, recargo_segundo_vencimiento::text, "
    "umbral_saldo_chico::text, autor_id, creada_en "
    "FROM configuracion_versionada WHERE complejo_id=:id "
)


def listar_versiones(sesion: Session, complejo_id: UUID) -> list[dict[str, Any]]:
    """`autor_nombre` (D5, tarea 2.2): `JOIN persona` por la FK compuesta
    que ya existe (`fk_configuracion_autor`), dentro de la misma sesión con
    tenant — nunca sólo `autor_id = p.id`, para no depender del filtro de
    RLS para aislar la fila correcta de `persona`."""
    if cargar_complejo(sesion, complejo_id) is None:
        raise NoEncontrado()
    return [
        dict(f)
        for f in sesion.execute(
            text(
                "SELECT cv.id, cv.complejo_id, cv.vigente_desde, cv.tasa_mensual::text, "
                "cv.dias_de_gracia, cv.forma_de_calculo, cv.porcentaje_fondo::text, "
                "cv.dia_de_vencimiento, cv.modalidad_de_vencimiento, "
                "cv.dia_segundo_vencimiento, cv.recargo_segundo_vencimiento::text, "
                "cv.umbral_saldo_chico::text, cv.autor_id, cv.creada_en, p.nombre AS autor_nombre "
                "FROM configuracion_versionada cv "
                "JOIN persona p ON p.id = cv.autor_id "
                "AND p.administracion_id = cv.administracion_id "
                "WHERE cv.complejo_id=:id ORDER BY cv.vigente_desde"
            ),
            {"id": complejo_id},
        ).mappings()
    ]


def configuracion_vigente(sesion: Session, complejo_id: UUID, fecha: date) -> dict[str, Any] | None:
    if cargar_complejo(sesion, complejo_id) is None:
        raise NoEncontrado()
    fila = (
        sesion.execute(
            text(
                _COLUMNAS_CONFIGURACION
                + "AND vigente_desde<=:fecha ORDER BY vigente_desde DESC LIMIT 1"
            ),
            {"id": complejo_id, "fecha": fecha},
        )
        .mappings()
        .first()
    )
    return None if fila is None else dict(fila)


def resumen_edificio(sesion: Session, complejo_id: UUID, hoy: date) -> dict[str, Any]:
    """D5 (tarea 2.1): la puesta a punto del edificio. Nunca llama a
    `unidades`/`grupos`/`categorias` (evitaría el ciclo: esos módulos ya
    importan de acá) — consulta directo, como el resto de este archivo.

    Los seis pasos (criterio de `edificios-y-unidades` > "Resumen y puesta a
    punto del edificio"): `unidades`, `coeficientes`, `grupos`, `categorias`,
    `intereses_y_vencimiento` y `saldos_previos`.
    """
    complejo = cargar_complejo(sesion, complejo_id)
    if complejo is None:
        raise NoEncontrado()

    coeficientes_unidades = (
        sesion.execute(
            text("SELECT coeficiente::text FROM unidad WHERE complejo_id=:id"), {"id": complejo_id}
        )
        .scalars()
        .all()
    )
    cantidad_unidades = len(coeficientes_unidades)
    informe = informar_coeficientes(Coeficiente(c) for c in coeficientes_unidades)

    grupos_parciales = (
        sesion.execute(
            text(
                "SELECT id, modo_de_coeficientes FROM grupo_de_reparto "
                "WHERE complejo_id=:id AND NOT es_generales"
            ),
            {"id": complejo_id},
        )
        .mappings()
        .all()
    )
    paso_grupos = "hecho"
    for grupo in grupos_parciales:
        miembros = (
            sesion.execute(
                text("SELECT coeficiente::text FROM grupo_unidad WHERE grupo_id=:id"),
                {"id": grupo["id"]},
            )
            .scalars()
            .all()
        )
        if not miembros:
            paso_grupos = "falta"
            break
        if grupo["modo_de_coeficientes"] == "propios":
            informe_grupo = informar_coeficientes(Coeficiente(c) for c in miembros)
            if informe_grupo["estado"] == "fuera_de_tolerancia":
                paso_grupos = "falta"
                break

    categorias_activas = sesion.execute(
        text("SELECT count(*) FROM categoria_de_gasto WHERE complejo_id=:id AND activa"),
        {"id": complejo_id},
    ).scalar_one()

    pasos = {
        "unidades": "hecho" if cantidad_unidades > 0 else "falta",
        "coeficientes": (
            "hecho"
            if cantidad_unidades > 0 and informe["estado"] in ("ok", "advertencia")
            else "falta"
        ),
        "grupos": paso_grupos,
        "categorias": "hecho" if categorias_activas > 0 else "falta",
        "intereses_y_vencimiento": (
            "hecho" if configuracion_vigente(sesion, complejo_id, hoy) is not None else "falta"
        ),
        "saldos_previos": "hecho" if complejo.estado_migracion != "pendiente" else "falta",
    }

    return {
        "nombre": complejo.nombre,
        "localidad": complejo.localidad,
        "cantidad_unidades": cantidad_unidades,
        "estado_migracion": complejo.estado_migracion,
        "informe": informe,
        "pasos": pasos,
        "listo_para_liquidar": all(paso == "hecho" for paso in pasos.values()),
    }
