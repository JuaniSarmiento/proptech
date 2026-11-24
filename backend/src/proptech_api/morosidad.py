"""La morosidad de un edificio (10a, R20, R30, D-167): la lectura (H-027) y su Excel (H-028).

`GET /api/complejos/{id}/morosidad` y `.../morosidad/excel` son lecturas, con el orden
de D7 de `liquidaciones.py`: el edificio que no existe o no alcanza da 404; sin `ver_morosidad`
(la lista) o `exportar_morosidad` (el Excel) en él, 403. Leer o exportar no se audita.
"""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.liquidaciones import edificio_autorizado
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.complejos.aplicacion.escritura import hoy_en_mendoza
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.cuenta_corriente.adaptadores.excel_de_morosidad import (
    TIPO_DE_CONTENIDO,
    armar_libro,
    nombre_del_archivo,
)
from proptech_core.cuenta_corriente.aplicacion.morosidad import morosidad_del_edificio

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)


def hoy() -> date:
    """La fecha de hoy en Mendoza. Es una dependencia para que la aceptación la fije (L-090)."""
    return hoy_en_mendoza(lambda: datetime.now(UTC))


@router.get("/complejos/{complejo_id}/morosidad")
def morosidad_del_edificio_en_api(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
    fecha_de_hoy: date = Depends(hoy),
) -> dict[str, Any]:
    edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_MOROSIDAD)
    m = morosidad_del_edificio(sesion, complejo_id=complejo_id, fecha=fecha_de_hoy)
    return {
        "fecha": m.fecha.isoformat(),
        "intereses_al": None if m.intereses_al is None else m.intereses_al.isoformat(),
        "resumen": {
            "unidades_con_deuda": len(m.unidades),
            "morosos_criticos": m.morosos_criticos,
            "total_vencido": m.total_vencido.a_texto(),
        },
        "unidades": [
            {
                "unidad_id": str(f.unidad_id),
                "unidad": f.unidad,
                "propietarios": list(f.propietarios),
                "etiqueta": f.etiqueta,
                "total_vencido": f.total_vencido.a_texto(),
                "capital": f.capital.a_texto(),
                "intereses": f.intereses.a_texto(),
                "liquidaciones_vencidas": f.liquidaciones_vencidas,
                "vencida_desde": f.vencida_desde.isoformat(),
                "dias": f.dias,
            }
            for f in m.unidades
        ],
    }


@router.get("/complejos/{complejo_id}/morosidad/excel")
def morosidad_en_excel(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
    fecha_de_hoy: date = Depends(hoy),
) -> Response:
    edificio_autorizado(sesion, identidad, complejo_id, Accion.EXPORTAR_MOROSIDAD)
    edificio = cargar_complejo(sesion, complejo_id)
    if edificio is None:  # `edificio_autorizado` ya lo dio por 404: no se llega
        raise HTTPException(status_code=404, detail="no encontrado")
    m = morosidad_del_edificio(sesion, complejo_id=complejo_id, fecha=fecha_de_hoy)
    archivo = nombre_del_archivo(edificio.nombre, m.fecha)
    return Response(
        content=armar_libro(edificio.nombre, m),
        media_type=TIPO_DE_CONTENIDO,
        headers={"Content-Disposition": f'attachment; filename="{archivo}"'},
    )
