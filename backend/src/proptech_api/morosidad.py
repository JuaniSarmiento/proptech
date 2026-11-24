"""La morosidad de un edificio (10a, H-027, R20, R30, D-167): `GET /api/complejos/{id}/morosidad`.

Es una lectura. Mismo orden de D7 que `liquidaciones.py`: el edificio que no existe o no alcanza da
404; sin `ver_morosidad` en él, 403. Leer no se audita.
"""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.liquidaciones import _edificio_autorizado
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.complejos.aplicacion.escritura import hoy_en_mendoza
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
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_MOROSIDAD)
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
