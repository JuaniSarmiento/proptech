#!/usr/bin/env bash
# RD-2 y 2b/3.3: respaldo del humo restaurado aparte, ida/vuelta hasta la cabeza de Alembic.
# Supuesto del design: no hay producción ni datos reales. Todo lo sembrado es ficticio.
set -euo pipefail

RAIZ_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ_REPO/infra"
mkdir -p "$RAIZ_REPO/.git/informes-login-bloque-a"
CARPETA_ENSAYO="$(mktemp -d "$RAIZ_REPO/.git/informes-login-bloque-a/3.3-XXXXXX")"
mkdir "$CARPETA_ENSAYO/respaldos"
export PROPTECH_DIR_RESPALDOS="$CARPETA_ENSAYO/respaldos"
PROPTECH_UID="$(id -u)"
PROPTECH_GID="$(id -g)"
export PROPTECH_UID PROPTECH_GID

# El ensayo hace `down -v`: corrido a mano junto a un stack levantado, se le da
# un proyecto propio (PROPTECH_COMPOSE_PROYECTO=proptech-ensayo ...). Se exporta
# para que restaurar.sh restaure en el MISMO proyecto, nunca en otro.
# L-043 (2e): la revisión desde la que nace el origen y a la que vuelve el ciclo de bajada. Es el
# único número de migración escrito a mano; la cabeza se pregunta a Alembic (CABEZA, más abajo).
REVISION_DE_ORIGEN="0016"

PROYECTO_COMPOSE="${PROPTECH_COMPOSE_PROYECTO:-proptech}"
export PROPTECH_COMPOSE_PROYECTO="$PROYECTO_COMPOSE"
compose() { docker compose -p "$PROYECTO_COMPOSE" "$@"; }
limpiar() {
  local estado=$?
  trap - EXIT
  if ! compose down -v --remove-orphans; then
    estado=1
  fi
  echo "Informe del ensayo: $CARPETA_ENSAYO"
  exit "$estado"
}
trap limpiar EXIT

# La base de origen es la del stack efímero de este script. Nunca una base ajena.
compose up --build -d --wait
USUARIO_DB="$(compose exec -T db printenv POSTGRES_USER)"
BASE_ORIGEN="$(compose exec -T db printenv POSTGRES_DB)"
MIGRADOR="$(compose run --rm --no-deps -T migraciones printenv POSTGRES_MIGRADOR_USER)"
# La cabeza la dice `alembic heads` (formato `NNNN (head)`); una migración nueva no deja este script viejo.
CABEZA="$(compose run --rm --no-deps -T migraciones alembic heads | awk '$2 == "(head)" { print $1 }')"
if [ -z "$CABEZA" ] || [ "$(wc -w <<<"$CABEZA")" -ne 1 ]; then
  echo "ERROR: alembic heads no devolvió una cabeza única: '$CABEZA'" >&2
  exit 1
fi
# Paso 1 del rollback del Migration Plan (design, D-114.5), como rol de arranque:
# tras `roles despues` la tabla protegida y su función no son del migrador, y
# cruzar la migración de la tabla protegida en cualquier sentido falla con `must be owner` (RB-1 del 4a).
devolver_al_migrador() {
  compose exec -T db psql -U "$USUARIO_DB" -d "$1" -v ON_ERROR_STOP=1 \
    -v migrador="$MIGRADOR" <<'SQL'
-- Paso 1 del rollback: el arranque ve todas las filas, sin filtrado por RLS.
DO $$ DECLARE tabla text; tiene_filas boolean; BEGIN
    FOREACH tabla IN ARRAY ARRAY['cuenta','emision','evento_de_emision','obligacion','movimiento','imputacion'] LOOP
        IF to_regclass(format('public.%I',tabla)) IS NOT NULL THEN
            EXECUTE format('SELECT EXISTS (SELECT 1 FROM public.%I)',tabla) INTO tiene_filas;
            IF tiene_filas THEN RAISE EXCEPTION 'el libro tiene filas en %',tabla; END IF;
        END IF;
    END LOOP;
END $$;
SELECT to_regclass('public.cuenta') IS NOT NULL AS existe \gset
\if :existe
ALTER TABLE cuenta OWNER TO :"migrador";
ALTER FUNCTION fn_cuenta_bloqueada() OWNER TO :"migrador";
\endif
SELECT to_regclass('public.emision') IS NOT NULL AS existe \gset
\if :existe
ALTER TABLE emision OWNER TO :"migrador";
ALTER FUNCTION fn_emision_bloqueada() OWNER TO :"migrador";
\endif
SELECT to_regclass('public.evento_de_emision') IS NOT NULL AS existe \gset
\if :existe
ALTER TABLE evento_de_emision OWNER TO :"migrador";
ALTER FUNCTION fn_evento_de_emision_bloqueada() OWNER TO :"migrador";
\endif
SELECT to_regclass('public.obligacion') IS NOT NULL AS existe \gset
\if :existe
ALTER TABLE obligacion OWNER TO :"migrador";
ALTER FUNCTION fn_obligacion_bloqueada() OWNER TO :"migrador";
\endif
SELECT to_regclass('public.movimiento') IS NOT NULL AS existe \gset
\if :existe
ALTER TABLE movimiento OWNER TO :"migrador";
ALTER FUNCTION fn_movimiento_bloqueada() OWNER TO :"migrador";
\endif
SELECT to_regclass('public.imputacion') IS NOT NULL AS existe \gset
\if :existe
ALTER TABLE imputacion OWNER TO :"migrador";
ALTER FUNCTION fn_imputacion_bloqueada() OWNER TO :"migrador";
\endif
SELECT to_regclass('public.configuracion_versionada') IS NOT NULL AS existe \gset
\if :existe
ALTER TABLE configuracion_versionada OWNER TO :"migrador";
ALTER FUNCTION fn_configuracion_versionada_bloqueada() OWNER TO :"migrador";
\endif
SELECT to_regclass('public.auditoria') IS NOT NULL AS existe \gset
\if :existe
ALTER TABLE auditoria OWNER TO :"migrador";
ALTER FUNCTION fn_auditoria_bloqueada() OWNER TO :"migrador";
\endif
SQL
}
devolver_al_migrador "$BASE_ORIGEN"
compose run --rm --no-deps migraciones alembic downgrade "$REVISION_DE_ORIGEN"

# Las dos administraciones y sus dos complejos, como en humo.sh; cinco formas
# legadas por administración para que el respaldo permita observar la conversión.
compose exec -T db psql -U "$USUARIO_DB" -d "$BASE_ORIGEN" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO administracion (id,nombre) VALUES
 ('10000000-0000-0000-0000-000000000001','Administración A del humo'),
 ('10000000-0000-0000-0000-000000000002','Administración B del humo');
INSERT INTO complejo (administracion_id,nombre,localidad)
 SELECT a.id, 'Complejo ' || e.numero::text, 'Mendoza'
 FROM administracion a CROSS JOIN generate_series(1,2) AS e(numero);
INSERT INTO unidad (administracion_id,complejo_id,identificador,tipo,piso,coeficiente,superficie_m2)
 SELECT administracion_id,id,'1A','departamento','1','0.500000','60.00' FROM complejo;
INSERT INTO persona (administracion_id,nombre)
 SELECT a.id, 'Perfil ficticio ' || p.numero::text
 FROM administracion a CROSS JOIN generate_series(1,5) AS p(numero);
-- INSERT legado intencional: origen en la revisión de origen, antes del pg_dump (L-023).
INSERT INTO asignacion_rol (administracion_id,persona_id,rol,complejo_id,unidad_id,nivel)
 SELECT p.administracion_id,p.id,
        CASE p.nombre WHEN 'Perfil ficticio 1' THEN 'titular'
                      WHEN 'Perfil ficticio 2' THEN 'colaborador'
                      WHEN 'Perfil ficticio 3' THEN 'colaborador'
                      WHEN 'Perfil ficticio 4' THEN 'consejo' ELSE 'vecino' END,
        CASE WHEN p.nombre = 'Perfil ficticio 1' THEN NULL ELSE c.id END,
        CASE WHEN p.nombre = 'Perfil ficticio 5' THEN u.id ELSE NULL END,
        CASE p.nombre WHEN 'Perfil ficticio 2' THEN 'editar'
                      WHEN 'Perfil ficticio 3' THEN 'ver' ELSE NULL END
 FROM persona p JOIN complejo c ON c.administracion_id=p.administracion_id AND c.nombre='Complejo 1'
 JOIN unidad u ON u.complejo_id=c.id;
SQL

conteos() {
  local base="$1" archivo="$2"
  # El rol de arranque sólo abre la conexión: los datos se leen como app con
  # SET LOCAL y un tenant por vez, y se exige RLS habilitada y forzada.
  compose exec -T db psql -U "$USUARIO_DB" -d "$base" -qAt -v ON_ERROR_STOP=1 > "$archivo" <<'SQL'
BEGIN;
SET LOCAL ROLE proptech_app;
DO $$ BEGIN
 IF current_user <> 'proptech_app' OR EXISTS (
   SELECT 1 FROM pg_roles WHERE rolname=current_user AND (rolsuper OR rolbypassrls)
 ) THEN RAISE EXCEPTION 'el lector debe ser proptech_app sin privilegios'; END IF;
 IF NOT (SELECT relrowsecurity AND relforcerowsecurity FROM pg_class
         WHERE oid='asignacion_rol'::regclass)
 THEN RAISE EXCEPTION 'RLS debe seguir habilitada y forzada'; END IF;
END $$;
SELECT set_config('app.administracion_id','10000000-0000-0000-0000-000000000001',true) AS tenant \gset
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM asignacion_rol
            WHERE administracion_id <> '10000000-0000-0000-0000-000000000001')
 THEN RAISE EXCEPTION 'se filtró otra administración'; END IF;
END $$;
SELECT 'A',rol,count(*) FROM asignacion_rol GROUP BY rol ORDER BY rol;
SELECT 'A','tabla:persona',count(*) FROM persona
 UNION ALL SELECT 'A','tabla:complejo',count(*) FROM complejo
 UNION ALL SELECT 'A','tabla:unidad',count(*) FROM unidad
 UNION ALL SELECT 'A','tabla:asignacion_rol',count(*) FROM asignacion_rol;
SELECT set_config('app.administracion_id','10000000-0000-0000-0000-000000000002',true) AS tenant \gset
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM asignacion_rol
            WHERE administracion_id <> '10000000-0000-0000-0000-000000000002')
 THEN RAISE EXCEPTION 'se filtró otra administración'; END IF;
END $$;
SELECT 'B',rol,count(*) FROM asignacion_rol GROUP BY rol ORDER BY rol;
SELECT 'B','tabla:persona',count(*) FROM persona
 UNION ALL SELECT 'B','tabla:complejo',count(*) FROM complejo
 UNION ALL SELECT 'B','tabla:unidad',count(*) FROM unidad
 UNION ALL SELECT 'B','tabla:asignacion_rol',count(*) FROM asignacion_rol;
COMMIT;
SQL
}
verificar_conteos() {
  local modo="$1" archivo="$2"
  python3 - "$modo" "$archivo" <<'PY'
from pathlib import Path
import sys
modo, archivo = sys.argv[1:]
# Oráculo literal independiente del código de la migración de roles; cuenta no vacía por cada tenant.
esperados = ({"titular": 1, "colaborador": 2, "consejo": 1, "vecino": 1}
             if modo == "legado" else
             {"super_admin": 1, "administrador": 1, "auxiliar": 1, "consejo": 1, "vecino": 1})
esperados.update({"tabla:persona": 5, "tabla:complejo": 2, "tabla:unidad": 2,
                  "tabla:asignacion_rol": 5})
filas = Path(archivo).read_text().splitlines()
obtenido = sorted(filas)
esperado = sorted(f"{tenant}|{rol}|{n}" for tenant in ("A", "B") for rol,n in esperados.items())
if obtenido != esperado:
    raise SystemExit(f"ERROR: conteos {modo} no coinciden con D5: {obtenido}")
print(f"CONTEOS {Path(archivo).stem}: " + ", ".join(filas))
PY
}
migrar_restaurada() {
  compose run --rm --no-deps -e POSTGRES_DB=proptech_restauracion migraciones alembic "$@"
}
# DB-8: la forma del esquema, no sólo los conteos. Sin los tokens aleatorios de PG18.
esquema() {
  echo "ESQUEMA: pg_dump --schema-only -U $USUARIO_DB -d proptech_restauracion -> $1"
  compose exec -T db pg_dump --schema-only -U "$USUARIO_DB" -d proptech_restauracion \
    | grep -Ev '^\\(un)?restrict |^-- Dumped (from|by) ' >"$1"
}
verificar_revision() {
  local esperada="$1" obtenida
  obtenida="$(compose exec -T db psql -U "$USUARIO_DB" -d proptech_restauracion \
    -qAt -v ON_ERROR_STOP=1 -c 'SELECT version_num FROM alembic_version')"
  if [ "$obtenida" != "$esperada" ]; then
    echo "ERROR: revisión restaurada esperada=$esperada obtenida=$obtenida" >&2
    return 1
  fi
  echo "REVISION RESTAURADA: $obtenida"
}

conteos "$BASE_ORIGEN" "$CARPETA_ENSAYO/origen.txt"
verificar_conteos legado "$CARPETA_ENSAYO/origen.txt"
compose exec -T respaldos /usr/local/bin/respaldar.sh --una-vez
ARCHIVO_DUMP="$(python3 - "$PROPTECH_DIR_RESPALDOS" <<'PY'
from pathlib import Path
import sys
archivos = sorted(Path(sys.argv[1]).glob('proptech-*.dump'))
if not archivos:
    raise SystemExit('no hay respaldo para restaurar')
print(archivos[-1])
PY
)"
bash respaldos/restaurar.sh "$ARCHIVO_DUMP" proptech_restauracion
# restaurar.sh usa --no-owner: se aplica el mismo paso de roles del despliegue
# para devolver al migrador la propiedad de las tablas de la base restaurada.
compose run --rm --no-deps -e POSTGRES_DB=proptech_restauracion migraciones \
  python -m proptech_core.compartido.roles antes
# `antes` ya no reasigna las tablas protegidas (D0): la restaurada, que quedó
# del rol de arranque por --no-owner, se devuelve igual que el origen.
devolver_al_migrador proptech_restauracion
conteos proptech_restauracion "$CARPETA_ENSAYO/antes.txt"
verificar_conteos legado "$CARPETA_ENSAYO/antes.txt"
cmp "$CARPETA_ENSAYO/origen.txt" "$CARPETA_ENSAYO/antes.txt"
esquema "$CARPETA_ENSAYO/esquema_antes.sql"

migrar_restaurada upgrade head
verificar_revision "$CABEZA"
conteos proptech_restauracion "$CARPETA_ENSAYO/primer_upgrade.txt"
verificar_conteos nuevo "$CARPETA_ENSAYO/primer_upgrade.txt"
migrar_restaurada downgrade "$REVISION_DE_ORIGEN"
verificar_revision "$REVISION_DE_ORIGEN"
conteos proptech_restauracion "$CARPETA_ENSAYO/downgrade.txt"
verificar_conteos legado "$CARPETA_ENSAYO/downgrade.txt"
cmp "$CARPETA_ENSAYO/antes.txt" "$CARPETA_ENSAYO/downgrade.txt"
esquema "$CARPETA_ENSAYO/esquema_downgrade.sql"
diff -u "$CARPETA_ENSAYO/esquema_antes.sql" "$CARPETA_ENSAYO/esquema_downgrade.sql"
echo "ESQUEMA RESTAURADO: diff vacío entre esquema_antes.sql y esquema_downgrade.sql"
migrar_restaurada upgrade head # segundo upgrade
verificar_revision "$CABEZA"
conteos proptech_restauracion "$CARPETA_ENSAYO/segundo_upgrade.txt"
verificar_conteos nuevo "$CARPETA_ENSAYO/segundo_upgrade.txt"
cmp "$CARPETA_ENSAYO/primer_upgrade.txt" "$CARPETA_ENSAYO/segundo_upgrade.txt"
compose run --rm --no-deps -e POSTGRES_DB=proptech_restauracion migraciones \
  python -m proptech_core.compartido.roles despues
conteos "$BASE_ORIGEN" "$CARPETA_ENSAYO/origen_despues.txt"
cmp "$CARPETA_ENSAYO/origen.txt" "$CARPETA_ENSAYO/origen_despues.txt"
echo "ENSAYO ROLES OK: respaldo restaurado, 10 asignaciones, ciclo $CABEZA/$REVISION_DE_ORIGEN/$CABEZA y origen intacto"
