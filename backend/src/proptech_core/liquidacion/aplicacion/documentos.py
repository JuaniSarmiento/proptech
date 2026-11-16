"""El PDF de la expensa de cada unidad (7, H-015, E12, E13, D-060, D-160).

Al emitir (la transacción de H-013) se crean dos documentos por unidad con obligación, uno por
variante (`completa` y `sin_extraordinaria`, D-106), en `pendiente`. Después del commit se encola
su generación; si Redis no está, la emisión sale igual y un barrido del worker reencola lo
pendiente. `generar_documento` arma el HTML desde lo **guardado** (nunca recalculado), lo convierte
a PDF y lo archiva con su SHA-256: un documento `generado` no se toca más (CCyC art. 2067 inc. i).

Sin permisos ni HTTP: la API decide quién lo pide (`puede_pedir_el_enlace`) y arma los enlaces
firmados (`enlaces.py`).
"""

import hashlib
import logging
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.permisos import (
    Accion,
    Asignacion,
    Rol,
    alcanza,
    puede,
)
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.cuenta_corriente.aplicacion.creditos import ahora_utc
from proptech_core.liquidacion.aplicacion.errores import NoEncontrado, SinPermiso
from proptech_core.liquidacion.aplicacion.lectura import leer_liquidacion, ve_lo_no_distribuido
from proptech_core.liquidacion.dominio.documento import (
    COMPLETA,
    SIN_EXTRAORDINARIA,
    VARIANTES,
    html_de_la_expensa,
)
from proptech_core.liquidacion.dominio.nombre_de_archivo import nombre_del_pdf
from proptech_core.liquidacion.puertos import ColaDeDocumentos

_logger = logging.getLogger("proptech_core.liquidacion.aplicacion.documentos")

#: La tarea del worker (`proptech_worker.tareas`) que genera el PDF de un documento.
TAREA_DE_PDF = "generar_pdf_de_expensa"
#: Si el worker no lo toma en una hora, el trabajo expira y el barrido lo reencola.
_EXPIRA_EN_S = 3600

#: Lo más largo que se guarda del motivo de un fallo (el `CHECK` de la `0043` admite 500).
_LARGO_DEL_MOTIVO = 300

Renderizador = Callable[[str], bytes]


def crear_documentos(
    sesion: Session,
    *,
    administracion_id: UUID,
    complejo_id: UUID,
    liquidacion_id: UUID,
    unidades_con_obligacion: Sequence[UUID],
) -> list[UUID]:
    """Dos documentos `pendiente` por unidad (completa y sin extraordinaria), en la transacción de
    emitir. Devuelve sus ids, por orden de unidad y variante, para encolarlos después del commit."""
    ids: list[UUID] = []
    filas: list[dict[str, Any]] = []
    for unidad in unidades_con_obligacion:
        for variante in (COMPLETA, SIN_EXTRAORDINARIA):
            documento = uuid4()
            ids.append(documento)
            filas.append(
                {
                    "id": documento,
                    "adm": administracion_id,
                    "c": complejo_id,
                    "l": liquidacion_id,
                    "u": unidad,
                    "v": variante,
                }
            )
    if filas:
        sesion.execute(
            text(
                "INSERT INTO documento_de_expensa (id, administracion_id, complejo_id, "
                "liquidacion_id, unidad_id, variante) VALUES (:id, :adm, :c, :l, :u, :v)"
            ),
            filas,
        )
    return ids


def listar_documentos(
    sesion: Session, *, complejo_id: UUID, liquidacion_id: UUID
) -> list[dict[str, Any]]:
    """Por orden natural de unidad y, dentro de cada una, la completa antes que la otra. Nunca los
    bytes: el PDF sólo sale por un enlace firmado."""
    filas = (
        sesion.execute(
            text(
                "SELECT d.id, d.unidad_id, l.identificador, d.variante, d.estado, d.motivo "
                "FROM documento_de_expensa d JOIN linea_de_liquidacion l "
                "ON l.liquidacion_id = d.liquidacion_id AND l.unidad_id = d.unidad_id "
                "WHERE d.liquidacion_id = :l AND d.complejo_id = :c "
                "ORDER BY l.orden, (d.variante <> 'completa'), d.id"
            ),
            {"l": liquidacion_id, "c": complejo_id},
        )
        .mappings()
        .all()
    )
    return [
        {
            "documento_id": str(f["id"]),
            "unidad_id": str(f["unidad_id"]),
            "identificador": f["identificador"],
            "variante": f["variante"],
            "estado": f["estado"],
            "motivo": f["motivo"],
        }
        for f in filas
    ]


def documento_del_edificio(
    sesion: Session, *, complejo_id: UUID, documento_id: UUID
) -> dict[str, Any] | None:
    """`None` si no existe, es de otro edificio o de otra administración (RLS)."""
    fila = (
        sesion.execute(
            text(
                "SELECT id, liquidacion_id, unidad_id, variante, estado FROM documento_de_expensa "
                "WHERE id = :id AND complejo_id = :c"
            ),
            {"id": documento_id, "c": complejo_id},
        )
        .mappings()
        .first()
    )
    return None if fila is None else dict(fila)


def preparar_reproceso(
    sesion: Session, *, complejo_id: UUID, liquidacion_id: UUID, reloj: Callable[[], datetime]
) -> list[UUID]:
    """Los `fallido` vuelven a `pendiente` (un `generado` nunca se toca) y se devuelven todos los
    `pendiente` de la liquidación, listos para encolar."""
    sesion.execute(
        text(
            "UPDATE documento_de_expensa SET estado = 'pendiente', motivo = NULL, "
            "actualizado_en = :ahora WHERE liquidacion_id = :l AND complejo_id = :c "
            "AND estado = 'fallido'"
        ),
        {"ahora": reloj(), "l": liquidacion_id, "c": complejo_id},
    )
    return [
        UUID(str(fila))
        for fila in sesion.execute(
            text(
                "SELECT d.id FROM documento_de_expensa d JOIN linea_de_liquidacion l "
                "ON l.liquidacion_id = d.liquidacion_id AND l.unidad_id = d.unidad_id "
                "WHERE d.liquidacion_id = :l AND d.complejo_id = :c AND d.estado = 'pendiente' "
                "ORDER BY l.orden, (d.variante <> 'completa'), d.id"
            ),
            {"l": liquidacion_id, "c": complejo_id},
        ).scalars()
    ]


def pendientes_del_barrido(
    sesion: Session, *, antiguedad_s: int, limite: int
) -> list[tuple[UUID, UUID]]:
    """`(administracion_id, documento_id)` de los `pendiente` de cualquier administración con más de
    `antiguedad_s` segundos (para no pisar el encolado de la emisión misma). Sólo anda con la
    sesión del barrido (`abrir_sesion_del_barrido_de_documentos`): la política
    `documento_pendiente_del_barrido` de la `0043` es de sólo lectura y sólo de `pendiente`."""
    filas = sesion.execute(
        text(
            "SELECT administracion_id, id FROM documento_de_expensa WHERE estado = 'pendiente' "
            "AND creado_en < now() - make_interval(secs => :antiguedad) "
            "ORDER BY creado_en, id LIMIT :limite"
        ),
        {"antiguedad": antiguedad_s, "limite": limite},
    ).all()
    return [(UUID(str(a)), UUID(str(d))) for a, d in filas]


async def encolar_generacion(
    cola: ColaDeDocumentos,
    *,
    administracion_id: UUID,
    documentos: Sequence[UUID],
    request_id: UUID,
    origen: str,
) -> int:
    """Encola `generar_pdf_de_expensa` por documento y devuelve cuántos. La clave lleva el
    `origen` (`e` la emisión, `r...` un reproceso, `b...` el barrido): un reintento del mismo origen
    se deduplica en ARQ, y uno nuevo no choca con el resultado ya guardado de uno anterior. Si la
    cola falla, el error sube (quien llama decide si la emisión sale igual o es un 503); los que ya
    entraron quedan encolados, y generar dos veces es inofensivo (`generar_documento`)."""
    for documento in documentos:
        await cola.encolar(
            TAREA_DE_PDF,
            clave=f"pdf:{documento}:{origen}",
            request_id=str(request_id),
            expira_en_s=_EXPIRA_EN_S,
            administracion_id=str(administracion_id),
            documento_id=str(documento),
        )
    return len(documentos)


def _renderizador_por_defecto() -> Renderizador:
    from proptech_core.liquidacion.adaptadores.pdf import renderizar_con_weasyprint

    return renderizar_con_weasyprint


def _motivo_del_fallo(error: Exception) -> str:
    texto = " ".join(f"{type(error).__name__}: {error}".split())
    return texto[:_LARGO_DEL_MOTIVO]


def generar_documento(
    sesion: Session,
    *,
    documento_id: UUID,
    renderizar: Renderizador | None = None,
    reloj: Callable[[], datetime] = ahora_utc,
) -> None:
    """Genera y archiva el PDF de un documento. No commitea: lo hace el llamador (el corte del
    worker, `ejecutar_con_corte`).

    Toma la fila con `FOR UPDATE`: dos generaciones del mismo documento (un reencolado, el barrido)
    se serializan y la segunda ve el `generado` de la primera. Sobre un `generado` no hace nada: el
    PDF archivado no se reescribe nunca. Si el armado o `renderizar` fallan, el documento queda
    `fallido` con su motivo y no lanza (el reproceso lo vuelve a intentar)."""
    fila = (
        sesion.execute(
            text(
                "SELECT administracion_id, complejo_id, liquidacion_id, unidad_id, variante, "
                "estado FROM documento_de_expensa WHERE id = :id FOR UPDATE"
            ),
            {"id": documento_id},
        )
        .mappings()
        .first()
    )
    if fila is None:
        raise NoEncontrado
    if fila["estado"] == "generado":
        return
    try:
        liquidacion = leer_liquidacion(
            sesion, complejo_id=fila["complejo_id"], liquidacion_id=fila["liquidacion_id"]
        )
        edificio = cargar_complejo(sesion, fila["complejo_id"])
        if liquidacion is None or edificio is None:
            raise LookupError("la liquidación del documento no está")
        html = html_de_la_expensa(
            liquidacion,
            unidad_id=str(fila["unidad_id"]),
            nombre_del_edificio=edificio.nombre,
            variante=fila["variante"],
        )
        contenido = (renderizar or _renderizador_por_defecto())(html)
        if not contenido:
            raise ValueError("el PDF salió vacío")
    except Exception as error:
        _logger.warning("documento_fallido", extra={"tipo_error": type(error).__name__})
        sesion.execute(
            text(
                "UPDATE documento_de_expensa SET estado = 'fallido', motivo = :motivo, "
                "actualizado_en = :ahora WHERE id = :id"
            ),
            {"motivo": _motivo_del_fallo(error), "ahora": reloj(), "id": documento_id},
        )
        return
    instante = reloj()
    sesion.execute(
        text(
            "INSERT INTO pdf_de_expensa (administracion_id, complejo_id, documento_id, contenido, "
            "sha256, generado_en) VALUES (:adm, :c, :d, :contenido, :sha, :en)"
        ),
        {
            "adm": fila["administracion_id"],
            "c": fila["complejo_id"],
            "d": documento_id,
            "contenido": contenido,
            "sha": hashlib.sha256(contenido).hexdigest(),
            "en": instante,
        },
    )
    sesion.execute(
        text(
            "UPDATE documento_de_expensa SET estado = 'generado', actualizado_en = :ahora "
            "WHERE id = :id"
        ),
        {"ahora": instante, "id": documento_id},
    )


def puede_pedir_el_enlace(
    asignaciones: Sequence[Asignacion],
    *,
    complejo_id: UUID,
    unidad_id: UUID,
    variante_del_documento: str,
    visible_para_el_consejo: bool,
) -> None:
    """Quién descarga qué (D-106). El personal con `ver_liquidaciones` pide las dos variantes (el
    consejo, sólo de lo distribuido, P39: si no, `NoEncontrado`). El vecino, sólo la de su unidad:
    el propietario las dos y el inquilino la `sin_extraordinaria` (la completa, `SinPermiso`); el
    vecino de otra unidad no ve que exista (`NoEncontrado`). Cualquier otro (el auxiliar),
    `SinPermiso`."""
    if not alcanza(asignaciones, complejo_id, unidad_id):
        raise NoEncontrado
    if puede(asignaciones, Accion.VER_LIQUIDACIONES, complejo_id):
        if not ve_lo_no_distribuido(asignaciones, complejo_id) and not visible_para_el_consejo:
            raise NoEncontrado
        return
    propias = [
        a
        for a in asignaciones
        if a.rol is Rol.VECINO and a.complejo_id == complejo_id and a.unidad_id == unidad_id
    ]
    if not propias:
        raise SinPermiso(Accion.VER_LIQUIDACIONES.value)
    if variante_del_documento not in VARIANTES:  # pragma: no cover - lo impide el CHECK
        raise NoEncontrado
    if variante_del_documento == COMPLETA and not any(a.vinculo == "propietario" for a in propias):
        raise SinPermiso(Accion.VER_LIQUIDACIONES.value)


def leer_pdf(sesion: Session, *, documento_id: UUID, variante: str) -> tuple[bytes, str] | None:
    """Los bytes archivados de un documento `generado` de esa variante y el nombre con el que baja
    (H-017: período, unidad y variante), o `None`."""
    fila = sesion.execute(
        text(
            "SELECT p.contenido, l.periodo, i.identificador FROM pdf_de_expensa p "
            "JOIN documento_de_expensa d ON d.id = p.documento_id "
            "JOIN liquidacion l ON l.id = d.liquidacion_id "
            "JOIN linea_de_liquidacion i ON i.liquidacion_id = d.liquidacion_id "
            "AND i.unidad_id = d.unidad_id "
            "WHERE d.id = :id AND d.variante = :v AND d.estado = 'generado'"
        ),
        {"id": documento_id, "v": variante},
    ).first()
    if fila is None:
        return None
    return bytes(fila[0]), nombre_del_pdf(fila[1], fila[2], variante)
