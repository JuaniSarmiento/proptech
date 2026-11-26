"""La IA completa el borrador de una factura (R12, R23, H-037, D-169).

La tarea del worker `leer_factura_con_ia` llama a `leer_la_factura` dentro de `ejecutar_con_corte`:
la llamada al lector, la fila de costo (`llamada_de_ia`) y el cambio del gasto se confirman juntos.
La IA sólo propone: nunca aprueba, nunca toca lo que trajo el QR ni lo que cargó una persona, nunca
escribe en el libro. Cada campo se valida solo contra lo que existe y está activo en el edificio
(`dominio.lectura_de_factura`); el texto de la factura es un dato, no una orden.

Estados que deja (`gasto.estado`, con su motivo en `gasto.lectura_ia`): `borrador` (lectura buena),
`en_revision` (lectura buena con importe atípico, R23), `sin_ia` (`ia_no_configurada`, `ia_fallo`,
`fuera_de_contrato`). En `sin_ia` no se aplica nada. Un gasto aprobado, sin factura (cargado a mano)
o que ya tuvo una llamada `ok` no se lee de nuevo.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.complejos.aplicacion.lectura import (
    listar_categorias_activas,
    listar_grupos_activos,
)
from proptech_core.gastos.dominio.archivo_de_factura import TIPOS_MIME
from proptech_core.gastos.dominio.lectura_de_factura import (
    CAMPOS_DE_LA_PROPUESTA,
    VENTANA_EN_PERIODOS,
    FueraDeContrato,
    evaluar_importe,
    validar_propuesta,
)
from proptech_core.gastos.puertos import ColaDeLecturas, LectorDeFacturaConIa

_logger = logging.getLogger("proptech_core.gastos.lectura_de_factura")

TAREA = "leer_factura_con_ia"
#: Un pedido sin leer vence a la hora, como el del PDF de la expensa.
_EXPIRA_EN_S = 3600
_MICRO_DOLAR = Decimal("0.000001")
#: `NUMERIC(12,6)`: hasta seis dígitos enteros.
_COSTO_MAXIMO = Decimal("1000000")
_TOPE_DE_TOKENS = 2**31 - 1

MOTIVO_SIN_CONFIGURAR = "ia_no_configurada"
MOTIVO_FALLO = "ia_fallo"
MOTIVO_FUERA_DE_CONTRATO = "fuera_de_contrato"
MOTIVO_ATIPICO = "importe_atipico"


async def encolar_lectura(
    cola: ColaDeLecturas, *, administracion_id: UUID, gasto_id: UUID, request_id: UUID
) -> None:
    """Encola `leer_factura_con_ia` para un gasto. Si la cola falla, el error sube: quien llama (la
    subida de la factura, después del commit) decide que el 201 sale igual."""
    await cola.encolar(
        TAREA,
        clave=f"lectura:{gasto_id}:e",
        request_id=str(request_id),
        expira_en_s=_EXPIRA_EN_S,
        administracion_id=str(administracion_id),
        gasto_id=str(gasto_id),
    )


# --- el uso de una llamada (nada de lo que devuelve el lector es confiable) ---


def _entero(valor: Any) -> int:
    if isinstance(valor, int) and not isinstance(valor, bool) and 0 <= valor <= _TOPE_DE_TOKENS:
        return valor
    return 0


def _costo(valor: Any) -> Decimal:
    if isinstance(valor, bool) or not isinstance(valor, str | int | float | Decimal):
        return Decimal(0)
    try:
        costo = Decimal(str(valor))
        if not costo.is_finite() or costo < 0 or costo >= _COSTO_MAXIMO:
            return Decimal(0)
        return costo.quantize(_MICRO_DOLAR, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return Decimal(0)


def _uso(origen: Any) -> tuple[int, int, Decimal]:
    return (
        _entero(getattr(origen, "tokens_entrada", 0)),
        _entero(getattr(origen, "tokens_salida", 0)),
        _costo(getattr(origen, "costo", 0)),
    )


def _modelo(origen: Any, lector: LectorDeFacturaConIa) -> str:
    modelo = getattr(origen, "modelo", None)
    if not isinstance(modelo, str) or not modelo.strip():
        modelo = getattr(lector, "modelo", None)
    if not isinstance(modelo, str) or not modelo.strip():
        return "desconocido"
    return modelo.strip()[:200]


# --- lectura de la base ---


def _vocabulario_activo(sesion: Session, complejo_id: UUID) -> tuple[list[dict[str, str]], ...]:
    """Las categorías y los grupos activos del edificio, como se le ofrecen a la IA."""
    return tuple(
        [{"id": str(o["id"]), "nombre": str(o["nombre"])} for o in opciones]
        for opciones in (
            listar_categorias_activas(sesion, complejo_id),
            listar_grupos_activos(sesion, complejo_id),
        )
    )


_LEER_GASTO = (
    "SELECT complejo_id, estado, proveedor_id, concepto, periodo, categoria_id, grupo_id, "
    "importe FROM gasto WHERE id=:id"
)


def _gasto_a_leer(sesion: Session, gasto_id: UUID, *, bloquear: bool) -> Any:
    consulta = text(_LEER_GASTO + " FOR UPDATE") if bloquear else text(_LEER_GASTO)
    return sesion.execute(consulta, {"id": gasto_id}).first()


def _ya_leido(sesion: Session, gasto_id: UUID) -> bool:
    return (
        sesion.execute(
            text("SELECT 1 FROM llamada_de_ia WHERE gasto_id=:g AND resultado='ok' LIMIT 1"),
            {"g": gasto_id},
        ).first()
        is not None
    )


def _meses_antes(periodo: date, meses: int) -> date:
    indice = periodo.year * 12 + periodo.month - 1 - meses
    return date(indice // 12, indice % 12 + 1, 1)


def _historial_del_proveedor(
    sesion: Session, *, complejo_id: UUID, proveedor_id: UUID, gasto_id: UUID, periodo: date
) -> list[Dinero]:
    """R23: los aprobados de ese proveedor y edificio en los 6 períodos anteriores al del gasto."""
    filas = sesion.execute(
        text(
            "SELECT importe::text FROM gasto WHERE complejo_id=:c AND proveedor_id=:p "
            "AND estado='aprobado' AND id<>:g AND periodo>=:desde AND periodo<:hasta"
        ),
        {
            "c": complejo_id,
            "p": proveedor_id,
            "g": gasto_id,
            "desde": _meses_antes(periodo, VENTANA_EN_PERIODOS),
            "hasta": periodo,
        },
    ).all()
    return [Dinero(str(f[0])) for f in filas]


# --- escritura ---


def _registrar_llamada(
    sesion: Session,
    *,
    administracion_id: UUID,
    complejo_id: UUID,
    gasto_id: UUID,
    clave: str,
    modelo: str,
    uso: tuple[int, int, Decimal],
    resultado: str,
) -> None:
    sesion.execute(
        text(
            "INSERT INTO llamada_de_ia (administracion_id, complejo_id, gasto_id, clave, modelo, "
            "tokens_entrada, tokens_salida, costo_usd, resultado) VALUES (:a, :c, :g, :k, :m, "
            ":ti, :ts, :costo, :r)"
        ),
        {
            "a": administracion_id,
            "c": complejo_id,
            "g": gasto_id,
            "k": clave,
            "m": modelo,
            "ti": uso[0],
            "ts": uso[1],
            "costo": uso[2],
            "r": resultado,
        },
    )


def _dejar_sin_ia(sesion: Session, gasto_id: UUID, motivo: str) -> None:
    lectura = {"motivo": motivo, "detalle": {"descartados": {}}, "campos": []}
    sesion.execute(
        text("UPDATE gasto SET estado='sin_ia', lectura_ia=CAST(:l AS jsonb) WHERE id=:id"),
        {"id": gasto_id, "l": _json(lectura)},
    )


def _json(valor: Any) -> str:
    return json.dumps(valor, separators=(",", ":"))


def leer_la_factura(
    sesion: Session,
    *,
    administracion_id: UUID,
    gasto_id: UUID,
    clave: str,
    lector: LectorDeFacturaConIa | None,
) -> None:
    """Lee la factura de un gasto con el lector de IA y deja el resultado. No confirma: lo hace
    `ejecutar_una_vez`. No hace nada si el gasto no existe en la administración de la sesión, está
    aprobado, no tiene factura o ya tuvo una lectura buena."""
    gasto = _gasto_a_leer(sesion, gasto_id, bloquear=False)
    if gasto is None or gasto.estado == "aprobado":
        return
    factura = sesion.execute(
        text("SELECT contenido, tipo FROM factura_de_gasto WHERE gasto_id=:g"), {"g": gasto_id}
    ).first()
    if factura is None or _ya_leido(sesion, gasto_id):
        return
    if lector is None:
        _dejar_sin_ia(sesion, gasto_id, MOTIVO_SIN_CONFIGURAR)
        return
    categorias, grupos = _vocabulario_activo(sesion, gasto.complejo_id)
    resultado: Any = None
    error: Exception | None = None
    try:
        # Sin el candado del gasto: la llamada es lenta y no frena a quien lo aprueba.
        resultado = lector.leer(
            bytes(factura.contenido),
            TIPOS_MIME[str(factura.tipo)],
            categorias=categorias,
            grupos=grupos,
        )
    except Exception as falla:  # lo que falle del lado de la IA no tumba la tarea
        error = falla
        _logger.warning("lectura_de_ia_fallida", extra={"tipo_error": type(falla).__name__})
    if error is not None or not hasattr(resultado, "propuesta"):
        uso = _uso(error if error is not None else None)
        _registrar_llamada(
            sesion,
            administracion_id=administracion_id,
            complejo_id=gasto.complejo_id,
            gasto_id=gasto_id,
            clave=clave,
            modelo=_modelo(None, lector),
            uso=uso,
            resultado="fallida",
        )
        _cerrar_sin_ia(
            sesion, gasto_id, MOTIVO_FALLO if error is not None else MOTIVO_FUERA_DE_CONTRATO
        )
        return
    _aplicar(
        sesion,
        administracion_id=administracion_id,
        gasto_id=gasto_id,
        clave=clave,
        lector=lector,
        resultado=resultado,
        categorias=categorias,
        grupos=grupos,
    )


def _cerrar_sin_ia(sesion: Session, gasto_id: UUID, motivo: str) -> None:
    """Con el candado y sólo si el gasto sigue sin aprobar (pudo aprobarse durante la llamada)."""
    actual = _gasto_a_leer(sesion, gasto_id, bloquear=True)
    if actual is not None and actual.estado != "aprobado":
        _dejar_sin_ia(sesion, gasto_id, motivo)


def _aplicar(
    sesion: Session,
    *,
    administracion_id: UUID,
    gasto_id: UUID,
    clave: str,
    lector: LectorDeFacturaConIa,
    resultado: Any,
    categorias: Sequence[dict[str, str]],
    grupos: Sequence[dict[str, str]],
) -> None:
    actual = _gasto_a_leer(sesion, gasto_id, bloquear=True)
    if actual is None:
        return
    pedidos = {
        "concepto": actual.concepto is None,
        "periodo": actual.periodo is None,
        "categoria_id": actual.categoria_id is None,
        "grupo_id": actual.grupo_id is None,
        "importe": actual.importe is None,
    }
    try:
        validada = validar_propuesta(
            resultado.propuesta,
            categorias={UUID(c["id"]) for c in categorias},
            grupos={UUID(g["id"]) for g in grupos},
            completar={campo for campo in CAMPOS_DE_LA_PROPUESTA if pedidos[campo]},
        )
    except FueraDeContrato:
        validada = None
    _registrar_llamada(
        sesion,
        administracion_id=administracion_id,
        complejo_id=actual.complejo_id,
        gasto_id=gasto_id,
        clave=clave,
        modelo=_modelo(resultado, lector),
        uso=_uso(resultado),
        resultado="ok" if validada is not None else "fallida",
    )
    if actual.estado == "aprobado" or _ya_leido_por_otra(sesion, gasto_id, clave):
        return  # alguien lo aprobó, o otra lectura ya lo completó, mientras llamábamos
    if validada is None:
        _dejar_sin_ia(sesion, gasto_id, MOTIVO_FUERA_DE_CONTRATO)
        return
    aplicados = {
        campo: getattr(validada, campo)
        for campo in CAMPOS_DE_LA_PROPUESTA
        if getattr(validada, campo) is not None
    }
    importe_final: Dinero | None = aplicados.get("importe")
    if importe_final is None and actual.importe is not None:
        importe_final = Dinero(str(actual.importe))
    periodo_final: date | None = aplicados.get("periodo", actual.periodo)
    estado, motivo = "borrador", None
    detalle: dict[str, Any] = {"descartados": validada.descartados}
    if actual.proveedor_id is not None and importe_final is not None and periodo_final is not None:
        atipico = evaluar_importe(
            importe_final,
            _historial_del_proveedor(
                sesion,
                complejo_id=actual.complejo_id,
                proveedor_id=actual.proveedor_id,
                gasto_id=gasto_id,
                periodo=periodo_final,
            ),
        )
        if atipico is not None:
            estado, motivo = "en_revision", MOTIVO_ATIPICO
            detalle |= {
                "promedio": atipico.promedio.a_texto(),
                "muestras": atipico.muestras,
                "importe": importe_final.a_texto(),
            }
    lectura = {"motivo": motivo, "detalle": detalle, "campos": sorted(aplicados)}
    sesion.execute(
        text(
            "UPDATE gasto SET concepto=COALESCE(concepto, :concepto), "
            "periodo=COALESCE(periodo, :periodo), "
            "categoria_id=COALESCE(categoria_id, :categoria), "
            "grupo_id=COALESCE(grupo_id, :grupo), "
            "importe=COALESCE(importe, CAST(:importe AS numeric)), "
            "estado=:estado, lectura_ia=CAST(:lectura AS jsonb) WHERE id=:id"
        ),
        {
            "id": gasto_id,
            "concepto": aplicados.get("concepto"),
            "periodo": aplicados.get("periodo"),
            "categoria": aplicados.get("categoria_id"),
            "grupo": aplicados.get("grupo_id"),
            "importe": None if "importe" not in aplicados else aplicados["importe"].a_texto(),
            "estado": estado,
            "lectura": _json(lectura),
        },
    )


def _ya_leido_por_otra(sesion: Session, gasto_id: UUID, clave: str) -> bool:
    return (
        sesion.execute(
            text(
                "SELECT 1 FROM llamada_de_ia WHERE gasto_id=:g AND resultado='ok' AND clave<>:k "
                "LIMIT 1"
            ),
            {"g": gasto_id, "k": clave},
        ).first()
        is not None
    )


# --- la lectura de un gasto (GET /gastos/{id}/lectura) ---


def lectura_del_gasto(sesion: Session, gasto_id: UUID) -> dict[str, Any] | None:
    """`{estado, datos_de, motivo, detalle}` o `None` si el gasto no existe en la administración.
    `datos_de` dice de dónde sale cada dato: `qr`, `ia` o `None` (vacío o cargado a mano)."""
    fila = sesion.execute(
        text(
            "SELECT complejo_id, estado, origen, importe IS NOT NULL AS con_importe, lectura_ia "
            "FROM gasto WHERE id=:id"
        ),
        {"id": gasto_id},
    ).first()
    if fila is None:
        return None
    lectura = fila.lectura_ia or {}
    campos = set(lectura.get("campos", []))
    datos_de: dict[str, str | None] = {
        campo: "ia" if campo in campos else None for campo in CAMPOS_DE_LA_PROPUESTA
    }
    if "importe" not in campos and fila.origen == "qr" and fila.con_importe:
        datos_de["importe"] = "qr"
    return {
        "estado": fila.estado,
        "datos_de": {
            c: datos_de[c] for c in ("importe", "concepto", "periodo", "categoria_id", "grupo_id")
        },
        "motivo": lectura.get("motivo"),
        "detalle": lectura.get("detalle"),
        "complejo_id": fila.complejo_id,
    }
