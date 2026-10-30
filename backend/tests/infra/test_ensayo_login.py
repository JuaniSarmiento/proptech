"""El ensayo debe verificar la cabeza real tras los dos upgrades restaurados."""

import re
from pathlib import Path

from alembic.script import ScriptDirectory

RAIZ = Path(__file__).resolve().parents[3]


def test_ensayo_deriva_la_cabeza_de_alembic_y_la_verifica_dos_veces() -> None:
    """L-043 (2e): la cabeza no se escribe a mano; la dice `alembic heads` del stack del ensayo.
    Una migración nueva ya no deja el script viejo."""
    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    assert re.search(r"^CABEZA=.*alembic heads", script, flags=re.MULTILINE)
    revisiones = re.findall(
        r"migrar_restaurada upgrade head[^\n]*\nverificar_revision (\S+)", script
    )
    assert revisiones == ['"$CABEZA"', '"$CABEZA"']


def test_ensayo_no_escribe_ninguna_revision_de_alembic_a_mano() -> None:
    """Sólo `REVISION_DE_ORIGEN` (el piso del ciclo de bajada) puede nombrar una revisión."""
    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    literales = [
        linea
        for linea in script.splitlines()
        if re.search(r"(?<![\w-])[0-9]{4}(?![\w-])", linea)
        and not linea.lstrip().startswith("#")
        and not linea.startswith("REVISION_DE_ORIGEN=")
    ]
    assert literales == []
    assert len(re.findall(r"^REVISION_DE_ORIGEN=\"?[0-9]{4}\"?$", script, flags=re.MULTILINE)) == 1
    assert "downgrade 0016" not in script


def test_ensayo_usa_un_proyecto_compose_parametrizable() -> None:
    # El ensayo hace `down -v`: corre sólo en un proyecto aislado y sin la variable se niega
    # (2e, L-047; `test_rechazos_de_scripts_destructivos.py`). Nunca hay un default `proptech`.
    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    assert 'PROYECTO_COMPOSE="$PROPTECH_COMPOSE_PROYECTO"' in script
    assert ":-proptech" not in script
    assert 'compose() { docker compose -p "$PROYECTO_COMPOSE" "$@"; }' in script
    assert "-p proptech " not in script


def test_ensayo_devuelve_la_tabla_protegida_antes_de_migrar() -> None:
    # RB-1 (4a): tras `despues` o tras restaurar con --no-owner, configuracion_versionada
    # no es del migrador y cruzar 0021 falla con `must be owner`. Es el paso 1 del
    # rollback del Migration Plan; no prueba el ensayo entero, que sólo se prueba corriéndolo.
    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    assert "ALTER TABLE configuracion_versionada OWNER TO" in script
    assert "ALTER FUNCTION fn_configuracion_versionada_bloqueada() OWNER TO" in script
    origen = script.index('devolver_al_migrador "$BASE_ORIGEN"')
    assert origen < script.index("migraciones alembic downgrade")
    restaurada = script.index("devolver_al_migrador proptech_restauracion")
    assert script.index("roles antes") < restaurada
    assert restaurada < script.index("migrar_restaurada upgrade head")


def test_ensayo_devuelve_todas_las_tablas_de_la_lista() -> None:
    from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    faltantes = [
        tabla for tabla in TABLAS_DE_SOLO_AGREGAR if f"ALTER TABLE {tabla} OWNER TO" not in script
    ]
    assert faltantes == [], f"sin devolución de propiedad: {faltantes}"


def test_ensayo_comprueba_libro_vacio_antes_de_devolverlo() -> None:
    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    assert "SELECT EXISTS (SELECT 1 FROM public.%I)" in script
    assert script.index("el libro tiene filas") < script.index("ALTER TABLE cuenta OWNER TO")


def test_ensayo_no_miente_sobre_la_revision_del_ciclo() -> None:
    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    assert "ciclo $CABEZA/$REVISION_DE_ORIGEN/$CABEZA" in script


def test_el_piso_del_ciclo_existe_en_alembic() -> None:
    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    piso = re.search(r'^REVISION_DE_ORIGEN="?([0-9]{4})"?$', script, flags=re.MULTILINE)
    assert piso is not None
    assert ScriptDirectory(str(RAIZ / "backend/migraciones")).get_revision(piso.group(1))


def test_ensayo_compara_la_forma_del_esquema_tras_bajar() -> None:
    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    antes = script.index('esquema "$CARPETA_ENSAYO/esquema_antes.sql"')
    bajada = script.index("migrar_restaurada downgrade")
    despues = script.index('esquema "$CARPETA_ENSAYO/esquema_downgrade.sql"')
    assert antes < bajada < despues < script.index("diff -u")
