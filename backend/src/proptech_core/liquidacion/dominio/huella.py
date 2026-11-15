"""Huella de una preliquidación (E3): SHA-256 de su forma canónica."""

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def huella_de(cuerpo: Mapping[str, Any], version_de_configuracion: str) -> str:
    """Todo el cuerpo salvo `huella`, con las claves ordenadas, más el id de la versión de
    configuración. Los montos ya son texto: la forma canónica no depende de ningún número."""
    sin_huella = {k: v for k, v in cuerpo.items() if k != "huella"}
    canonico = json.dumps(
        {"cuerpo": sin_huella, "version_de_configuracion": version_de_configuracion},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()
