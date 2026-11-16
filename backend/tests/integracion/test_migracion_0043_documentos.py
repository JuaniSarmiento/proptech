"""El ciclo de la `0043` (7, H-015): sube, baja con las tablas vacías, vuelve a subir y no baja con
documentos. L-082: prueba **su** migración, nunca "la última"; L-086: en su propio módulo, porque la
base de migraciones es por módulo."""

import pytest

from ._cuenta_corriente import sembrar
from ._documentos import documento, liquidar
from ._edificios import BaseDeEdificio
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion

_TABLAS = ("documento_de_expensa", "pdf_de_expensa")


def _existen(base: BaseDeEdificio) -> dict[str, bool]:
    with arranque(base) as c:
        return {
            t: c.execute("SELECT to_regclass(%s)", (f"public.{t}",)).fetchone() != (None,)
            for t in _TABLAS
        }


def _subir(base: BaseDeEdificio) -> None:
    base.roles("antes")
    base.migrar("upgrade", "0043")
    base.roles("despues")


def _bajar(base: BaseDeEdificio) -> None:
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0042")


def test_la_0043_sube_sobre_una_base_ya_desplegada(base_para_migraciones: BaseDeEdificio) -> None:
    """El camino real: la base está en la 0042 con `roles despues` hecho (`liquidacion` es del rol
    de arranque) y la 0043 la referencia: el migrador necesita `REFERENCES` sobre ella."""
    base = base_para_migraciones
    base.roles("antes")
    base.migrar("upgrade", "0042")
    base.roles("despues")
    assert _existen(base) == {"documento_de_expensa": False, "pdf_de_expensa": False}
    _subir(base)
    assert _existen(base) == {"documento_de_expensa": True, "pdf_de_expensa": True}


def test_el_ciclo_de_la_0043(base_para_migraciones: BaseDeEdificio) -> None:
    base = base_para_migraciones
    _subir(base)
    assert _existen(base) == {"documento_de_expensa": True, "pdf_de_expensa": True}
    with arranque(base) as c:
        dueno = c.execute(
            "SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid = 'pdf_de_expensa'::regclass"
        ).fetchone()
    assert dueno == (base.contenedor.username,), "el PDF archivado es del rol de arranque (D-115)"
    _bajar(base)
    assert _existen(base) == {"documento_de_expensa": False, "pdf_de_expensa": False}
    _subir(base)
    assert _existen(base) == {"documento_de_expensa": True, "pdf_de_expensa": True}


def test_con_documentos_la_0043_no_baja(base_para_migraciones: BaseDeEdificio) -> None:
    base = base_para_migraciones
    base.roles("antes")
    base.migrar("upgrade", "head")
    base.roles("despues")
    mundo = sembrar(base, unidades=1, con_configuracion=True)
    documento(base, mundo, liquidar(base, mundo))
    base.devolver_tablas_protegidas()
    with pytest.raises(AssertionError) as error:
        base.migrar("downgrade", "0042")
    assert "la migración no puede bajarse" in str(error.value)
    assert _existen(base) == {"documento_de_expensa": True, "pdf_de_expensa": True}
