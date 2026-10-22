# Búsqueda de escritores para 0019/0020 (3.3, L-023)

Constructor, 2026-10-21 10:39:36. Búsqueda con `rg --hidden -n -i -U`,
respetando `.gitignore` y excluyendo `.git`, `.env*`, entornos, dependencias y artefactos locales.
Incluye SQL directo y las migraciones con `bulk_insert` del vocabulario. No se abre ningún `.env`.

Patrón: `INSERT\s+INTO\s+(?:public\.)?"?(?:persona|accion_de_auditoria)\b|(?:bulk_insert|sa\.table\("accion_de_auditoria")`.

25 archivos, 47 líneas coincidentes.

- `backend/migraciones/versions/0004_auditoria.py`: 60, 61.
- `backend/migraciones/versions/0010_acciones_de_configuracion.py`: 27, 28, 36.
- `backend/migraciones/versions/0020_invitaciones.py`: 76, 77, 85.
- `backend/tests/integracion/_login_db.py`: 33, 50.
- `backend/tests/integracion/conftest.py`: 165, 208.
- `backend/tests/integracion/test_alcance_api.py`: 131, 264.
- `backend/tests/integracion/test_altas_sin_id_del_cliente.py`: 205.
- `backend/tests/integracion/test_asignar_edificio_api.py`: 143, 187, 404.
- `backend/tests/integracion/test_auditoria_tabla.py`: 352.
- `backend/tests/integracion/test_auditoria_transaccion.py`: 193.
- `backend/tests/integracion/test_autor_en_historial.py`: 27.
- `backend/tests/integracion/test_catalogo_rls.py`: 183.
- `backend/tests/integracion/test_categorias_casos_de_uso.py`: 123.
- `backend/tests/integracion/test_configuracion_versionada_db.py`: 49.
- `backend/tests/integracion/test_grupos_casos_de_uso.py`: 114.
- `backend/tests/integracion/test_identidad_api.py`: 145.
- `backend/tests/integracion/test_migracion_roles_de_la_empresa.py`: 108, 284.
- `backend/tests/integracion/test_migracion_vinculo_con_clerk.py`: 55, 60, 77, 115, 207.
- `backend/tests/integracion/test_perfiles_api.py`: 27, 230.
- `backend/tests/integracion/test_regresiones_de_aislamiento_y_grupos_vacios.py`: 55.
- `backend/tests/integracion/test_rls_acceso_minimo.py`: 147, 391, 396, 411, 416.
- `backend/tests/integracion/test_rutas_protegidas.py`: 199, 204.
- `infra/ci/ensayo-roles.sh`: 45.
- `openspec/changes/archive/2026-10-19-configuracion-del-edificio/design.md`: 27, 458.
- `openspec/changes/archive/2026-10-19-configuracion-del-edificio/tasks.md`: 2671.

Revisión: `persona.clerk_usuario_id` es nullable y las escrituras previas pueden omitirla;
las nuevas la envían con la forma de D1. `accion_de_auditoria` conserva su única columna,
por lo que las inserciones previas siguen válidas. 0020 agrega sólo los ocho eventos firmados.
Chequeo explícito adicional: `rg -n -i 'persona|accion_de_auditoria|insert' infra/ci/humo.sh
openspec/changes/acceso-de-desarrollo/`. El humo no inserta en estas dos tablas: sólo inserta
`administracion` (línea 112) y `complejo` (115); menciona `persona` en un comentario (750).
Por eso no figura entre los escritores y no requiere cambios.
`openspec/changes/acceso-de-desarrollo/`: sin INSERT coincidentes.

Coincidencias completas:

```text
./openspec/changes/archive/2026-10-19-configuracion-del-edificio/design.md:27:  y `bulk_insert(... for accion in Accion)`. Cualquier miembro nuevo de `Accion` aparece en 0004 en
./openspec/changes/archive/2026-10-19-configuracion-del-edificio/design.md:458:`0004` hace `bulk_insert(... for accion in Accion)` con el enum **vivo**: en una base vacía, un
./backend/tests/integracion/test_asignar_edificio_api.py:143:                "INSERT INTO persona (id, administracion_id, nombre, email) "
./backend/tests/integracion/test_asignar_edificio_api.py:187:            "INSERT INTO persona (id, administracion_id, nombre, email) VALUES (%s, %s, %s, %s)",
./backend/tests/integracion/test_asignar_edificio_api.py:404:            "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'Principal')",
./openspec/changes/archive/2026-10-19-configuracion-del-edificio/tasks.md:2671:  INSERT INTO persona (id, administracion_id, nombre) SELECT ('30000000-0000-0000-0000-00000000000'||i)::uuid, ('10000000-0000-0000-0000-00000000000'||i)::uuid, 'Persona ficticia '||i FROM generate_series(1,2) i;
./backend/tests/integracion/test_grupos_casos_de_uso.py:114:            "INSERT INTO persona (id,administracion_id,nombre) "
./backend/tests/integracion/test_auditoria_transaccion.py:193:                    "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, %s)",
./backend/tests/integracion/test_alcance_api.py:131:        text("INSERT INTO persona (id, administracion_id, nombre) VALUES (:id, :admin, 'B')"),
./backend/tests/integracion/test_alcance_api.py:264:                "INSERT INTO persona (id, administracion_id, nombre, email) "
./backend/tests/integracion/test_configuracion_versionada_db.py:49:        "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'Persona ficticia')",
./backend/tests/integracion/_login_db.py:33:                "INSERT INTO persona (id,administracion_id,nombre,clerk_usuario_id) "
./backend/tests/integracion/_login_db.py:50:            "INSERT INTO persona (id,administracion_id,nombre,clerk_usuario_id) "
./backend/tests/integracion/test_identidad_api.py:145:                "INSERT INTO persona (id, administracion_id, nombre, email) "
./backend/tests/integracion/conftest.py:165:            "INSERT INTO persona (id, administracion_id, nombre) "
./backend/tests/integracion/conftest.py:208:                        "INSERT INTO persona (id, administracion_id, nombre) "
./backend/tests/integracion/test_regresiones_de_aislamiento_y_grupos_vacios.py:55:            "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'B')",
./backend/tests/integracion/test_autor_en_historial.py:27:        text("INSERT INTO persona (id, administracion_id, nombre) VALUES (:id, :admin, :nombre)"),
./backend/tests/integracion/test_auditoria_tabla.py:352:        "INSERT INTO accion_de_auditoria (nombre) VALUES ('accion_inventada_por_la_app')",
./backend/tests/integracion/test_perfiles_api.py:27:            "INSERT INTO persona (id, administracion_id, nombre) "
./backend/tests/integracion/test_perfiles_api.py:230:            "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'Rompedor')",
./backend/tests/integracion/test_altas_sin_id_del_cliente.py:205:                "INSERT INTO persona (id, administracion_id, nombre, email) "
./backend/tests/integracion/test_migracion_vinculo_con_clerk.py:55:                "INSERT INTO persona (administracion_id,nombre,clerk_usuario_id) "
./backend/tests/integracion/test_migracion_vinculo_con_clerk.py:60:            "INSERT INTO persona (administracion_id,nombre) VALUES (%s,'Sin vínculo'),(%s,'Otra')",
./backend/tests/integracion/test_migracion_vinculo_con_clerk.py:77:                "INSERT INTO persona (administracion_id,nombre,clerk_usuario_id) "
./backend/tests/integracion/test_migracion_vinculo_con_clerk.py:115:                "INSERT INTO persona (administracion_id,nombre,clerk_usuario_id) "
./backend/tests/integracion/test_migracion_vinculo_con_clerk.py:207:                "INSERT INTO persona (administracion_id,nombre,clerk_usuario_id) "
./backend/migraciones/versions/0020_invitaciones.py:76:    op.bulk_insert(
./backend/migraciones/versions/0020_invitaciones.py:77:        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
./backend/migraciones/versions/0020_invitaciones.py:85:    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
./backend/tests/integracion/test_migracion_roles_de_la_empresa.py:108:                    "INSERT INTO persona (id,administracion_id,nombre) "
./backend/tests/integracion/test_migracion_roles_de_la_empresa.py:284:        "INSERT INTO persona (id,administracion_id,nombre) VALUES (%s,%s,'Perfil ficticio')",
./backend/tests/integracion/test_rutas_protegidas.py:199:            "INSERT INTO persona (id, administracion_id, nombre, email) VALUES (%s, %s, %s, %s)",
./backend/tests/integracion/test_rutas_protegidas.py:204:            "INSERT INTO persona (id, administracion_id, nombre, email) VALUES (%s, %s, %s, %s)",
./backend/tests/integracion/test_categorias_casos_de_uso.py:123:                "INSERT INTO persona (id,administracion_id,nombre) "
./backend/tests/integracion/test_rls_acceso_minimo.py:147:                "INSERT INTO persona (id, administracion_id, nombre, email) "
./backend/tests/integracion/test_rls_acceso_minimo.py:391:                "INSERT INTO persona (administracion_id, nombre, email) VALUES (%s, %s, %s)",
./backend/tests/integracion/test_rls_acceso_minimo.py:396:                    "INSERT INTO persona (administracion_id, nombre, email) VALUES (%s, %s, %s)",
./backend/tests/integracion/test_rls_acceso_minimo.py:411:                "INSERT INTO persona (administracion_id, nombre, email) VALUES (%s, %s, %s)",
./backend/tests/integracion/test_rls_acceso_minimo.py:416:                "INSERT INTO persona (administracion_id, nombre, email) VALUES (%s, %s, %s)",
./backend/migraciones/versions/0004_auditoria.py:60:    op.bulk_insert(
./backend/migraciones/versions/0004_auditoria.py:61:        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
./backend/migraciones/versions/0010_acciones_de_configuracion.py:27:    op.bulk_insert(
./backend/migraciones/versions/0010_acciones_de_configuracion.py:28:        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
./backend/migraciones/versions/0010_acciones_de_configuracion.py:36:    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
./infra/ci/ensayo-roles.sh:45:INSERT INTO persona (administracion_id,nombre)
./backend/tests/integracion/test_catalogo_rls.py:183:                "INSERT INTO persona (id, administracion_id, nombre) "
```
