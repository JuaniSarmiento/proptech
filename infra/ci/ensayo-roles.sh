#!/usr/bin/env bash
# RD-2: respaldo real del stack de humo, restaurado aparte y migrado ida/vuelta.
# Supuesto del design: no hay producción ni datos reales. Todo lo sembrado es ficticio.
set -euo pipefail

RAIZ_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ_REPO/infra"
mkdir -p "$RAIZ_REPO/.git/informes-roles-bloque-a-v2"
CARPETA_ENSAYO="$(mktemp -d "$RAIZ_REPO/.git/informes-roles-bloque-a-v2/3.5-XXXXXX")"
mkdir "$CARPETA_ENSAYO/respaldos"
export PROPTECH_DIR_RESPALDOS="$CARPETA_ENSAYO/respaldos"
PROPTECH_UID="$(id -u)"
PROPTECH_GID="$(id -g)"
export PROPTECH_UID PROPTECH_GID

compose() { docker compose -p proptech "$@"; }
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
compose run --rm --no-deps migraciones alembic downgrade 0016

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
-- INSERT legado intencional: origen en 0016, antes del pg_dump (L-023).
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
SELECT set_config('app.administracion_id','10000000-0000-0000-0000-000000000002',true) AS tenant \gset
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM asignacion_rol
            WHERE administracion_id <> '10000000-0000-0000-0000-000000000002')
 THEN RAISE EXCEPTION 'se filtró otra administración'; END IF;
END $$;
SELECT 'B',rol,count(*) FROM asignacion_rol GROUP BY rol ORDER BY rol;
COMMIT;
SQL
}
verificar_conteos() {
  local modo="$1" archivo="$2"
  python3 - "$modo" "$archivo" <<'PY'
from pathlib import Path
import sys
modo, archivo = sys.argv[1:]
# Oráculo literal independiente del código de 0017; cuenta no vacía por cada tenant.
esperados = ({"titular": 1, "colaborador": 2, "consejo": 1, "vecino": 1}
             if modo == "legado" else
             {"super_admin": 1, "administrador": 1, "auxiliar": 1, "consejo": 1, "vecino": 1})
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
conteos proptech_restauracion "$CARPETA_ENSAYO/antes.txt"
verificar_conteos legado "$CARPETA_ENSAYO/antes.txt"
cmp "$CARPETA_ENSAYO/origen.txt" "$CARPETA_ENSAYO/antes.txt"

migrar_restaurada upgrade 0017
conteos proptech_restauracion "$CARPETA_ENSAYO/primer_upgrade.txt"
verificar_conteos nuevo "$CARPETA_ENSAYO/primer_upgrade.txt"
migrar_restaurada downgrade 0016
conteos proptech_restauracion "$CARPETA_ENSAYO/downgrade.txt"
verificar_conteos legado "$CARPETA_ENSAYO/downgrade.txt"
cmp "$CARPETA_ENSAYO/antes.txt" "$CARPETA_ENSAYO/downgrade.txt"
migrar_restaurada upgrade 0017 # segundo upgrade
conteos proptech_restauracion "$CARPETA_ENSAYO/segundo_upgrade.txt"
verificar_conteos nuevo "$CARPETA_ENSAYO/segundo_upgrade.txt"
cmp "$CARPETA_ENSAYO/primer_upgrade.txt" "$CARPETA_ENSAYO/segundo_upgrade.txt"
compose run --rm --no-deps -e POSTGRES_DB=proptech_restauracion migraciones \
  python -m proptech_core.compartido.roles despues
conteos "$BASE_ORIGEN" "$CARPETA_ENSAYO/origen_despues.txt"
cmp "$CARPETA_ENSAYO/origen.txt" "$CARPETA_ENSAYO/origen_despues.txt"
echo "ENSAYO ROLES OK: respaldo restaurado, 10 asignaciones, ciclo 0017/0016/0017 y origen intacto"
