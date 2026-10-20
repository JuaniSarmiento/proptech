Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el paso
rojo es obligatorio y se anota en el informe con el comando, su salida y la hora. Si un test nuevo pasa
antes de escribir el código, no prueba nada: se corrige el test hasta verlo fallar por la razón
correcta y se informa (L-019). "Verde" quiere decir lint, formato, tipos y tests del lado tocado (L-005).
Los tests de base corren contra PostgreSQL real **conectados como `proptech_app`**, con filas en **dos
administraciones** y leyendo con el tenant de cada una, nunca como el rol de arranque, que ve todo y
haría pasar una migración que no migró (L-016). Los ids "de otro edificio" y "de otra administración"
son UUID válidos de filas que existen (L-017). Ningún mensaje de error de la migración nombra a una
persona ni trae un id. Para ver fallar una verificación contra código mutado a propósito, se muta una
copia o se saca antes una copia del original y se compara con un diff real (L-013). Cada tarea nombra
los escenarios de la spec que cubre (`capacidad` › escenario) y las lecciones que aplica. Ninguna tarea
supera medio día. Al tocar `tests/conftest.py`, `tests/integracion/conftest.py` o un router real, se
corre la suite completa, no sólo el archivo propio (lección del 2a, 4.1).

Precondiciones: la sección "Aprobación" de `proposal.md` completada por uno de los dos socios, Juani o
Alberto, con su nombre, la fecha, el alcance aprobado y la respuesta a E1 a E8 (gobernanza CRITICAL,
D-094). Si una elección se rechaza, se corrigen `design.md` y las specs antes de empezar. Sin eso, no se
empieza. Ningún agente completa esa sección.

Resoluciones de esta vuelta, **resuelto por el orquestador, 20/10/2026**:
- 2.1 incluye el constructor y la adaptación mínima de sus llamadores y tests.
  4.1/4.2 conservan sus tests y comportamiento nuevos; antes de 0017 se lee
  sólo el esquema actual, sin anticipar la lectura de `vinculo`.
- 3.1: el mutante sin `NO FORCE` que falla con `CheckViolation` es rojo válido;
  la conversión exacta por rol sigue siendo la exigencia.
- D5: el índice parcial se borra con `DROP INDEX`; frase corregida en design.
- 3.4: sumar `super_admin` en el ejemplo corresponde a `acceso-de-desarrollo`;
  ese material no se toca.

## 1. Línea de base

- [x] 1.1 Correr `bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh` y `bash infra/ci/humo.sh`, en ese orden y de a uno, y anotar la cantidad de tests de cada lado, la hora y el commit (`git rev-parse HEAD`); si algo falla, frenar e informarlo como falla previa. Verificación: los tres comandos con su salida en el informe. Escenarios: ninguno (medición de partida). Lecciones: L-003, L-010.

  EVIDENCIA (20/10/2026, HEAD `bf066ce3065ab5bed3b4b8c39cb827e0d29d1c60`):
  RED: no aplica; esta tarea mide la línea de base y no cambia comportamiento.
  Los tres comandos corrieron en orden, de a uno, sin cambios de implementación:

  ```text
  $ date +%T && git rev-parse HEAD && bash infra/ci/test-backend.sh
  11:37:27
  bf066ce3065ab5bed3b4b8c39cb827e0d29d1c60
  =========== 1757 passed, 1 xfailed, 16 warnings in 544.73s (0:09:04) ===========
  $ date +%T && bash infra/ci/test-web.sh
  11:46:41
   Test Files  45 passed (45)
        Tests  298 passed (298)
  $ date +%T && bash infra/ci/humo.sh
  11:47:30
  HUMO OK
  Network proptech_borde  Removed
  ```

  JUICIO: línea de base verde (1758 tests backend recolectados, ninguno omitido;
  el `xfail(strict=True)` F2c de `test_zz_rompedor_v3_agotada_con_efecto.py` es deuda
  preexistente del cambio 7: el hilo puede confirmar después de agotar los reintentos).
  Humo terminó con estado 0; siembra, backup, restauración y limpieza del proyecto
  `proptech` por el script original. Logs completos locales en
  `.git/informes-roles-bloque-a/1.1-{backend,web,humo}.log`.
  SUPUESTO: ninguno para esta medición.


## 2. El dominio

- [x] 2.1 Perfil y alcance (D1, D2) en `backend/tests/unitarios/acceso/test_permisos.py`: una tabla escrita a mano que, para cada forma de fila de base (`rol`, `complejo_id`, `unidad_id`, `vinculo`), espera el perfil de los siete y el alcance (principal, por edificio, por unidad); las formas inválidas (super admin con complejo, auxiliar o consejo sin complejo, vecino sin vínculo, vínculo en una fila de personal, un rol `titular` o `colaborador`) levantan al construir la asignación en vez de dar un perfil. RED: el módulo todavía no tiene `Perfil` ni `Alcance` (`ImportError`). Implementar en `acceso/dominio/permisos.py` sin tocar `Accion`. Escenarios: `autorizacion-por-rol` › Alcance principal regalado; › Vecino sin vínculo o personal con vínculo (la mitad del dominio). Lecciones: L-019.

EVIDENCIA (20/10/2026, segunda vuelta):
  ```text
  $ cd backend && date +%T && uv run pytest tests/unitarios/acceso/test_permisos.py -q
  12:08:15
  E ImportError: cannot import name 'Alcance'
  1 error in 0.11s
  $ cd backend && date +%T && uv run pytest tests/unitarios/acceso/test_permisos.py -q
  12:08:41
  197 passed in 0.17s
  $ cd backend && date +%T && uv run pytest tests/unitarios/acceso tests/integracion/test_alcance_api.py tests/integracion/test_asignar_edificio_api.py tests/integracion/test_identidad_api.py -q
  12:08:54
  218 passed, 1 warning in 13.24s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 225 files already formatted / Success: no issues found in 205 source files
  ```
  JUICIO: nueve formas válidas y 21 inválidas; sin `nivel` en Asignacion.
  Resuelto por el orquestador, 20/10/2026: se adaptaron en el mismo commit
  los tests existentes y cargar_asignaciones. Este último traduce el vocabulario
  de 0016 leyendo `nivel`; aún no consulta `vinculo` (reservado a 4.1).
  La matriz conserva sus permisos anteriores para cambiarla con el rojo de 2.2.
  SUPUESTO: ninguno. Logs locales en `.git/informes-roles-bloque-a-v2/`.


- [x] 2.2 La matriz (D3) en `backend/tests/unitarios/acceso/test_permisos.py`: la tabla de D3 copiada a mano como literal del test (16 acciones por 9 columnas, 144 celdas), comparada **entera** contra `puede` en un complejo del alcance, y el mensaje del fallo nombra cada celda distinta; además, toda acción para una asignación por edificio en otro complejo da "no"; `crear_edificio` con `complejo_id=None` sólo para el super admin; una `Accion` sin fila se niega para todos; una persona con dos asignaciones (administrador por edificio en A, auxiliar en B) puede escribir en A y no en B; un administrador principal, para el permiso `anular_liquidacion`, con `complejo_id=None`, da "no" (RA-3: se conserva la guarda de `permisos.py:109`, que sin complejo sólo evalúa `crear_edificio`). RED: con la matriz vieja la comparación falla nombrando las celdas; mutar una celda en una copia de `permisos.py` y verla fallar (L-013). Escenarios: `autorizacion-por-rol` › La matriz completa; › Una asignación por edificio en otro complejo; › El administrador por edificio emite pero no anula; › El administrador principal corrige en cualquier edificio. Lecciones: L-013, L-019, L-022.

EVIDENCIA (20/10/2026):
  ```text
  $ cd backend && date +%T && uv run pytest tests/unitarios/acceso/test_permisos.py -q
  12:09:52
  19 failed, 405 passed in 0.43s
  $ date +%T && cd backend && uv run pytest tests/unitarios/acceso/test_permisos.py::test_matriz_entera_con_cada_celda_distinta_en_el_mensaje -q
  12:10:31
  E AssertionError: anular_liquidacion/AE: True != False
  1 failed in 0.05s
  ```
  Mutante sobre copia previa local (L-013), diff real; restaurada y comparada byte a byte:
  ```diff
  -    Accion.ANULAR_LIQUIDACION: frozenset({_SA, _AP}),
  +    Accion.ANULAR_LIQUIDACION: frozenset({_SA, _AP, _AE}),
  ```
  ```text
  $ cd backend && date +%T && uv run pytest tests/unitarios/acceso tests/integracion/test_alcance_api.py tests/integracion/test_asignar_edificio_api.py -q
  12:10:33
  437 passed, 1 warning in 10.74s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 225 files already formatted / Success: no issues found in 205 source files
  ```
  JUICIO: matriz literal de 144 celdas, comparación entera con diferencias por
  celda; pruebas sin fila, fuera de alcance, dos asignaciones y RA-3 verdes.
  SUPUESTO: ninguno. Logs y copia previa locales en `.git/informes-roles-bloque-a-v2/`.


- [x] 2.3 El alcance (D3) en `backend/tests/unitarios/acceso/test_permisos.py`: `alcanza` por perfil y alcance (principal, todo complejo y unidad de la administración; por edificio, su complejo y sus unidades y ningún otro; por unidad, su unidad y su complejo, nunca otra unidad del mismo complejo), dos propietarios distintos de la misma unidad y un inquilino de otra. RED: con `alcanza` viejo, un contador principal no alcanza nada. Escenarios: `autorizacion-por-rol` › Colaborador en un edificio no asignado; › Vecino en la unidad de otro vecino; › Consejo en otro edificio; › Contador principal; › Dos asignaciones de la misma persona (la parte del dominio). Lecciones: L-019.

EVIDENCIA (20/10/2026):
  ```text
  $ cd backend && date +%T && uv run pytest tests/unitarios/acceso/test_permisos.py -q
  12:11:18
  FAILED test_alcance_de_los_nueve_perfiles[CP]
  3 failed, 431 passed in 0.42s
  $ cd backend && date +%T && uv run pytest tests/unitarios/acceso -q
  12:11:26
  436 passed, 1 warning in 0.57s
  ```
  JUICIO: los nueve perfiles cubren complejo, unidad propia, otra unidad y otro
  edificio; incluye dos propietarios y un inquilino, y la unión de asignaciones.
  Los casos que nacieron verdes se atacaron con el mutante de unidad (copia
  previa local y diff real, restaurado byte a byte):
  ```diff
  -        if unidad_id is None or asignacion.unidad_id == unidad_id:
  +        if asignacion.complejo_id == complejo_id:
  ```
  ```text
  $ cd backend && date +%T && uv run pytest tests/unitarios/acceso/test_permisos.py -q -k alcance_de
  12:11:44
  FAILED test_alcance_de_dos_propietarios_e_inquilino_de_otra_unidad
  3 failed, 16 passed, 415 deselected in 0.08s
  $ cd backend && date +%T && uv run pytest tests/unitarios/acceso -q
  12:11:45
  436 passed, 1 warning in 0.53s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 225 files already formatted / Success: no issues found in 205 source files
  ```
  SUPUESTO: ninguno.


## 3. La base

- [x] 3.1 Migración `0017_roles_de_la_empresa`, `upgrade` (D5), en `backend/tests/integracion/test_migracion_roles_de_la_empresa.py` con contenedor propio: sembrar en 0016, en dos administraciones, una fila de cada forma vieja (titular, colaborador "editar", colaborador "ver", consejo, vecino); `upgrade`; leer como `proptech_app` con el tenant de cada una y exigir el perfil nuevo de cada fila y ninguna con `titular`, `colaborador` ni `nivel`; `relrowsecurity` y `relforcerowsecurity` siguen prendidos y con el tenant de A no aparece ninguna fila de B; los tres objetos nuevos existen después del `upgrade`: el índice único `uq_asignacion_rol_persona_unidad` (D2), el índice único `uq_asignacion_rol_persona_alcance` (RA-5) y el índice `ix_asignacion_rol_persona` (RD-1, el que sirve a `cargar_asignaciones`). Tres rojos, cada uno sobre una copia de la migración (L-013): sin el `NO FORCE`, la migración falla con `CheckViolation` al validar el vocabulario nuevo y el test de conversión queda rojo (resuelto por el orquestador, 20/10/2026); sin el `FORCE` final, el test de aislamiento falla; con un `RAISE` agregado después de convertir, la tabla queda como en 0016 y con `FORCE`. Además, dos filas de vecino de la misma persona y unidad hacen fallar el `upgrade` sin cambiar nada y con un mensaje sin ids. Escenarios: `autorizacion-por-rol` › Conversión en dos administraciones; › La tabla sigue aislada; › Una relación repetida frena la conversión. Lecciones: L-013, L-016, L-018, L-020.

EVIDENCIA (20/10/2026):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py -q
  12:13:34
  FAILED: Can't locate revision identified by '0017'
  3 failed in 10.80s
  ```
  Tres mutantes contra copia previa local, con diff real y restauración byte a byte:
  ```diff
  -    op.execute("ALTER TABLE asignacion_rol NO FORCE ROW LEVEL SECURITY")
  +    # Mutante: NO FORCE omitido
  -    op.execute("ALTER TABLE asignacion_rol FORCE ROW LEVEL SECURITY")
  +    # Mutante: FORCE final omitido
  +    op.execute("DO $$ BEGIN RAISE EXCEPTION 'fallo tras convertir'; END $$")
       op.drop_column("asignacion_rol", "nivel")
  ```
  El comando se repitió para cada copia (logs `3.1-{sin-no-force,sin-force,raise}.log`):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py::test_upgrade_convierte_dos_administraciones_y_conserva_aislamiento -q
  12:15:25
  E sqlalchemy.exc.IntegrityError: (psycopg.errors.CheckViolation)
  1 failed in 4.82s
  12:15:47
  E assert (10,) == (0,)
  1 failed in 5.98s
  12:16:00
  E sqlalchemy.exc.ProgrammingError: (psycopg.errors.RaiseException) fallo tras convertir
  1 failed in 6.45s
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py tests/unitarios/acceso -q
  12:16:17
  439 passed, 1 warning in 11.38s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 227 files already formatted / Success: no issues found in 206 source files
  ```
  JUICIO: conversión exacta de diez filas, dos tenants; app sin privilegios,
  aislamiento y tres índices. Duplicado en B aborta con contador sin ids;
  el test con RAISE compara filas, catálogo, FORCE y revisión 0016 tras rollback.
  Resuelto por el orquestador, 20/10/2026: CheckViolation sin NO FORCE es
  rojo válido. El texto original de la tarea queda aclarado por esta resolución.
  El downgrade sigue pendiente de su tarea 3.3; los fixtures actuales se adaptan
  en 3.4 antes de la suite completa. SUPUESTO: ninguno.


- [x] 3.2 La forma de cada asignación en la base (D1, D2), en el mismo archivo, como `proptech_app` en `head`: una fila válida de cada perfil y alcance entra (nueve formas); cada forma inválida falla por el `CHECK` y no deja nada (auxiliar, consejo o vecino sin complejo; super admin con complejo; vecino sin vínculo; administrador con vínculo; rol `titular`, `colaborador` y uno inventado); la misma persona propietaria e inquilina de una unidad falla por el índice único; la misma persona con dos asignaciones de rol de personal (cualquier combinación de super admin, administrador, contador o auxiliar) en el mismo alcance falla por `uq_asignacion_rol_persona_alcance` (RA-5), y esto vale también con `complejo_id` nulo en las dos (alcance principal, antes exento con un `UNIQUE` sin `NULLS NOT DISTINCT`); la misma persona con un rol de personal y, además, una fila de consejo o de vecino en el mismo edificio entra sin problema (RA-5: son asignaciones de otro tipo); dos propietarios distintos y un inquilino distinto de la misma unidad entran. Actualizar los casos de `test_rls_acceso_minimo.py` que prueban en `head` el `CHECK` de 0003 (colaborador sin nivel), sin borrar ninguno sin reemplazo. RED: con la base de 0016 los inserts del vocabulario nuevo fallan. Escenarios: `autorizacion-por-rol` › Alcance principal regalado; › Super admin atado a un edificio; › Vecino sin vínculo o personal con vínculo; › Perfil desconocido; › Propietaria e inquilina de la misma unidad; › Dos roles de personal en el mismo alcance; › Dos propietarios de la misma unidad (la parte de la base). Lecciones: L-016, L-018.

EVIDENCIA (20/10/2026): los cuatro tests nuevos nacieron verdes a las
  12:18:19 (7 passed in 22.19s); los CHECK/índices ya se crearon por D5 en 3.1.
  Se verificaron sus rojos sobre copias previas locales, restauradas byte a byte:
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py -q -k 'formas or invalida or unicidad or personal'
  12:18:56  (copia del test contra 0016)
  E psycopg.errors.UndefinedColumn: column "vinculo" does not exist
  4 failed, 3 deselected in 13.91s
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py::test_cada_forma_invalida_falla_por_check_y_no_deja_filas -q
  12:19:19  (CHECK de forma abierto)
  E Failed: DID NOT RAISE CheckViolation
  1 failed in 6.23s
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py::test_unicidad_de_vecino_y_de_todas_las_combinaciones_de_personal -q
  12:19:47  (sin índices únicos)
  E Failed: DID NOT RAISE UniqueViolation
  1 failed in 5.87s
  12:20:01  (NULLS DISTINCT)
  E Failed: DID NOT RAISE UniqueViolation
  1 failed in 4.79s
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py::test_personal_coexiste_con_consejo_y_vecino_y_la_unidad_admite_tres_personas -q
  12:20:17  (índice de personal extendido a consejo/vecino)
  E psycopg.errors.UniqueViolation: uq_asignacion_rol_persona_alcance
  1 failed in 5.98s
  ```
  Diffs reales completos en los logs locales `3.2-*.log`; extractos de las copias:
  ```diff
  -    base_roles.migrar("upgrade", "head")
  +    base_roles.migrar("upgrade", "0016")
  -        "(rol = 'super_admin' AND complejo_id IS NULL AND unidad_id IS NULL "
  +        "TRUE OR (rol = 'super_admin' AND complejo_id IS NULL AND unidad_id IS NULL "
  -        "CREATE UNIQUE INDEX uq_asignacion_rol_persona_unidad ON asignacion_rol "
  +        "CREATE INDEX uq_asignacion_rol_persona_unidad ON asignacion_rol "
  -        "(administracion_id, persona_id, complejo_id) NULLS NOT DISTINCT "
  +        "(administracion_id, persona_id, complejo_id) NULLS DISTINCT "
  -        "WHERE rol IN ('super_admin', 'administrador', 'contador', 'auxiliar')"
  +        "WHERE rol IN ('super_admin', 'administrador', 'contador', 'auxiliar', 'consejo', 'vecino')"
  ```
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py -q
  12:20:27
  7 passed in 18.78s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 227 files already formatted / Success: no issues found in 206 source files
  ```
  JUICIO: nueve formas válidas y veinte inválidas, en ambos tenants como app;
  todas las combinaciones de personal por alcance, NULL incluido, y coexistencia.
  Vecino sin unidad y colaborador sin nivel del test viejo se reemplazan por
  vecino sin unidad y auxiliar sin complejo; la FK usa vecino propietario válido.
  Resuelto por el orquestador, 20/10/2026: la suite de test_rls_acceso_minimo
  ejecuta downgrade base al cerrar. Su verde se completa después del downgrade
  de 3.3, ahora verificada. Se corrigió la transacción del caso legado para
  que SET LOCAL sobreviva al INSERT. SUPUESTO: ninguno.
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_rls_acceso_minimo.py -q -k asignacion_incompleta
  12:24:24  (mismo mutante del CHECK de forma, restaurado)
  E Failed: DID NOT RAISE CheckViolation
  2 failed, 17 deselected in 4.17s
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py tests/integracion/test_rls_acceso_minimo.py -q
  12:24:41
  31 passed in 45.69s
  ```


- [x] 3.3 El `downgrade` (D5, E7, RD-3, RD-4), en el mismo archivo: con sólo filas con forma vieja, `downgrade 0016` corre en el orden de D5 (`LOCK`, `NO FORCE`, chequeo previo de conteos, conversión, `FORCE`) y devuelve cada una a su rol y nivel exactos en las dos administraciones; el catálogo de `asignacion_rol` (columnas **excluyendo `ordinal_position`**, que cambia con el orden de creación y no es señal real de drift; `CHECK`; que ya no estén los índices `uq_asignacion_rol_persona_unidad`, `uq_asignacion_rol_persona_alcance` e `ix_asignacion_rol_persona`; políticas; `FORCE`) queda idéntico al de antes del `upgrade`, comparado entero; después `upgrade` vuelve a pasar. Con un contador, con un administrador principal y con un vecino inquilino, por separado, el `downgrade` falla, el mensaje dice cuántas filas de cada tipo y no trae ningún id ni nombre, y ni las filas ni el esquema cambian. RED: una copia del `downgrade` que convierte el inquilino en vecino en vez de fallar pasa el caso que debía fallar, y el test lo muestra; otra copia que hace el chequeo previo de conteos antes del `LOCK`/`NO FORCE` (en vez de después, RD-3) se marca y se corrige. Escenarios: `autorizacion-por-rol` › Volver atrás sin datos nuevos; › Volver atrás con un contador o un inquilino. Lecciones: L-013, L-016, L-022.

EVIDENCIA (20/10/2026):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py -q -k downgrade
  12:21:37
  E NotImplementedError: El downgrade se construye en la tarea 3.3
  5 failed, 7 deselected in 16.29s
  ```
  Mutantes con copias previas locales, diff real y restauración byte a byte:
  ```diff
  -                   count(*) FILTER (WHERE rol = 'vecino' AND vinculo = 'inquilino')
  +                   count(*) FILTER (WHERE false)
  ```
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py -q -k 'downgrade_rechaza and inquilino'
  12:23:16
  E Failed: DID NOT RAISE AssertionError
  1 failed, 2 passed, 9 deselected in 12.29s
  ```
  Segunda copia: las dos instrucciones LOCK y NO FORCE se movieron de antes
  del DO a después (diff completo en `3.3-preflight-antes-lock.log`):
  ```diff
  -    op.execute("LOCK TABLE asignacion_rol IN ACCESS EXCLUSIVE MODE")
  -    op.execute("ALTER TABLE asignacion_rol NO FORCE ROW LEVEL SECURITY")
       op.execute(""" ... chequeo previo ... """)
  +    op.execute("LOCK TABLE asignacion_rol IN ACCESS EXCLUSIVE MODE")
  +    op.execute("ALTER TABLE asignacion_rol NO FORCE ROW LEVEL SECURITY")
  ```
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py::test_downgrade_emite_lock_no_force_y_despues_chequea_conteos -q
  12:23:31
  E assert 746 < 546
  1 failed in 4.75s
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py tests/integracion/test_rls_acceso_minimo.py -q
  12:24:41
  31 passed in 45.69s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 227 files already formatted / Success: no issues found in 206 source files
  ```
  JUICIO: ciclo exacto en dos tenants; sin índices nuevos tras downgrade;
  políticas, CHECK, FK, PK y propiedades de columnas comparados completos.
  Cada tipo nuevo bloquea con sus conteos (2, 3 y 4), sin ids ni nombres;
  filas, esquema, FORCE y versión quedan intactos tras cada rechazo.
  resuelto por el orquestador, 20/10/2026: DROP INDEX para el índice parcial;
  también se excluye dtd_identifier (7 → 9 al recrear nivel, rojo a 12:22:51,
  `3.3-catalogo-detalle.log`), porque identifica la posición del atributo igual
  que ordinal_position. No es drift estructural; design aclarado.
  SUPUESTO: ninguno.


- [x] 3.4 Todo `INSERT` a `asignacion_rol` del repositorio (L-023): `rg` sobre el repositorio entero (`backend/`, `infra/`, `web/`, `openspec/changes/acceso-de-desarrollo/`) y, aparte, sobre `.git/informes-3b/`; pasar al vocabulario nuevo los ayudantes de `tests/integracion/conftest.py` y cada test que siembra asignaciones, con el mapeo de D5 (titular → super admin, colaborador "editar" → administrador, "ver" → auxiliar, vecino → vecino propietario). La carga del ejemplo sin commitear no se toca: se anota en el informe qué línea cambiaría. La identidad de desarrollo (fuera de este cambio, en el change `acceso-de-desarrollo`, en curso y sin firmar) necesita SUMAR una fila de rol `super_admin` a la persona de ejemplo con el vocabulario nuevo, no reemplazar lo que ya tenga (RA-1, revisión del arquitecto): se anota en el informe, y `acceso-de-desarrollo` hereda esta tarea pendiente — es ese change el que tiene que retomarla (ver `design.md`, Open Questions, "El orden con `acceso-de-desarrollo`"). Verificación: la lista del `rg` antes y después en el informe, y la suite completa del backend en verde con la misma cantidad de tests de la 1.1 más los nuevos. Escenarios: ninguno nuevo (sostiene los existentes). Lecciones: L-003, L-023.

EVIDENCIA (20/10/2026): barrido completo con rg multilínea, también ignorados;
  exclusiones: .env, .env.*, especificacion/, .git/ (salvo el barrido separado),
  node_modules/, .venv/, .next/ y cachés. No se leyeron archivos .env.
  ```text
  rg -n -i -U --hidden --no-ignore --file .git/informes-roles-bloque-a-v2/patron-insert.txt [exclusiones -g anteriores] .
  rg -n -i -U --hidden --no-ignore -g '!.env' -g '!.env.*' --file .git/informes-roles-bloque-a-v2/patron-insert.txt .git/informes-3b/
  ```
  Ubicaciones completas ANTES → DESPUÉS (20 → 21 INSERT); SQL completo en los
  logs locales `3.4-repo-{antes,despues}.log`. Números de línea por archivo:

  | Archivo | Antes | Después |
  |---|---|---|
  | backend/src/proptech_core/complejos/aplicacion/escritura.py | 54 | 54 |
  | backend/tests/integracion/conftest.py | 246 | 246 |
  | backend/tests/integracion/test_alcance_api.py | 152,158,163,168,174 | 152,158,163,168,174 |
  | backend/tests/integracion/test_altas_sin_id_del_cliente.py | 210 | 210 |
  | backend/tests/integracion/test_asignar_edificio_api.py | 148,153,159,164 | 148,153,159,164 |
  | backend/tests/integracion/test_identidad_api.py | 152 | 152 |
  | backend/tests/integracion/test_migracion_roles_de_la_empresa.py | 113,267,300 | 113,267,300,528 |
  | backend/tests/integracion/test_regresiones_de_aislamiento_y_grupos_vacios.py | 59 | 59 |
  | backend/tests/integracion/test_rls_acceso_minimo.py | 311,352 | 311,352 |
  | openspec/changes/archive/2026-10-19-configuracion-del-edificio/tasks.md | 2672 | 2672 |

  Cero INSERT en infra/, web/, acceso-de-desarrollo/ y .git/informes-3b/, incluido
  2.3-wip/. La evidencia archivada y los tres INSERT legados del test de migración
  se conservan a propósito (0016); el ayudante de perfiles escribe ya en head.
  En .git/informes-3b/2.3-wip/ejemplo.py:211, acceso-de-desarrollo debe SUMAR
  super_admin, con complejo/unidad/vínculo nulos, después del alta de persona;
  no reemplazar sus otras asignaciones (RA-1). Ese change hereda la tarea.
  Archivo intacto: SHA256 53356420b6c5b161966af358908228b1a0ab72aaa787992188d8007a1ead3005.
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_configuracion_api.py -q -x
  12:26:24
  E psycopg.errors.UndefinedColumn: column "nivel" of relation "asignacion_rol" does not exist
  1 warning, 1 error in 8.99s
  $ cd backend && date +%T && uv run pytest tests/integracion/test_migracion_roles_de_la_empresa.py::test_personal_legado_repetido_aborta_con_conteo_sin_ids -q
  12:32:39
  E AssertionError: Regex pattern did not match (UniqueViolation con ids, sin el conteo exigido)
  1 failed in 4.88s
  12:33:08  (mismo comando, con chequeo previo)
  1 passed in 5.99s
  $ cd backend && date +%T && uv run pytest
  12:27:35
  2 failed, 2034 passed, 1 xfailed, 16 warnings in 547.24s (0:09:07)
  ```
  resuelto por el orquestador, 20/10/2026: la adaptación mínima tras 0017 quita
  nivel del lector/INSERT. Leer vinculo real y el cuerpo/auditoría nuevos siguen
  en 4.1/4.2. Se ajustan sólo expectativas existentes de configuración según D3,
  el destinatario positivo para que no choque con RA-5 y head=0017 en el test viejo.
  El preflight de personal evita filtrar ids al crear el índice (hallazgo de
  implementación, sin cambiar RA-5 ni permisos; test primero, design aclarado).
  Verificación de cada corrección de la primera suite, con date +%T:
  ```text
  12:31:04  uv run pytest tests/integracion/test_asignacion_validacion.py -q
  8 passed, 1 warning in 9.72s
  12:35:18  uv run pytest tests/integracion/test_unidad_edificio_inmutable.py -q
  6 passed in 9.51s
  ```
  ```text
  $ cd backend && date +%T && uv run pytest
  12:37:02
  =========== 2037 passed, 1 xfailed, 16 warnings in 496.42s (0:08:16) ===========
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 227 files already formatted / Success: no issues found in 206 source files
  ```
  JUICIO: suite completa verde: 2038 recolectados frente a 1758 de 1.1, +280;
  ningún test quitado ni omitido. El xfail estricto es el mismo previo del cambio 7.
  Barrido adicional tras 3.5, mismo rg: se suma infra/ci/ensayo-roles.sh:49,
  INSERT legado deliberado sobre 0016 para el respaldo de prueba (22 en total).
  Las demás ubicaciones no cambian; web/ e informes-3b/ siguen sin INSERT.
  SUPUESTO: ninguno para el barrido ni las verificaciones.


- [x] 3.5 Ensayo de la migración sobre la copia más fiel disponible (RD-2, revisión del DBA): **supuesto declarado** — no hay producción ni datos reales de este sistema, nunca se desplegó (Migration Plan, "Despliegue: no hay"). Levantar el stack de humo (`infra/ci/humo.sh`) con sus dos administraciones sembradas; volcar con `compose exec -T respaldos /usr/local/bin/respaldar.sh --una-vez`; restaurar ese dump en una base aparte con `bash infra/respaldos/restaurar.sh <archivo_dump> proptech_restauracion` (el mismo camino que usa `humo.sh`); sobre esa base restaurada correr `alembic upgrade` a 0017, `alembic downgrade` a 0016 y `alembic upgrade` otra vez, comparando conteos por `administracion_id` y por `rol` antes del primer `upgrade`, después del `downgrade` y después del segundo `upgrade`. Verificación: los tres conteos (antes, tras el `downgrade`, tras el segundo `upgrade`) en el informe, idénticos entre antes y downgrade con el vocabulario viejo, y entre el primero y el tercero al aplicar el mapeo de D5 (resuelto por el orquestador, 20/10/2026: los textos de rol cambian a propósito). Escenarios: `autorizacion-por-rol` › Conversión en dos administraciones (repetida sobre la copia restaurada, no sobre datos sembrados a mano). Lecciones: L-013, L-016.

SUPUESTO declarado por RD-2 (sin verificar externamente): no hay producción ni
  datos reales; nunca se desplegó. Se ensaya la copia más fiel disponible.
  EVIDENCIA (20/10/2026): test operativo nuevo `infra/ci/ensayo-roles.sh`.
  El primer ensayo nació verde sobre 0017; se verificó su rojo con una copia
  previa real del script, diff completo y restauración byte a byte (L-013):
  ```text
  $ date +%T && bash infra/ci/ensayo-roles.sh
  12:46:32
  ENSAYO ROLES OK: respaldo restaurado, 10 asignaciones, ciclo 0017/0016/0017 y origen intacto
  ```
  ```diff
  -migrar_restaurada upgrade 0017 # segundo upgrade
  +: # mutante: segundo upgrade omitido
  ```
  ```text
  $ date +%T && bash infra/ci/ensayo-roles.sh
  12:47:44  (copia mutada)
  ERROR: conteos nuevo no coinciden con D5: ['A|colaborador|2', 'A|consejo|1', 'A|titular|1', 'A|vecino|1', 'B|colaborador|2', 'B|consejo|1', 'B|titular|1', 'B|vecino|1']
  exit 1; limpieza del proyecto proptech terminada
  $ date +%T && bash infra/ci/ensayo-roles.sh
  12:48:31  (script restaurado)
  ENSAYO ROLES OK: respaldo restaurado, 10 asignaciones, ciclo 0017/0016/0017 y origen intacto
  ```
  Tres conteos completos, leídos como proptech_app con SET LOCAL por tenant:
  A = 10000000-0000-0000-0000-000000000001; B = 10000000-0000-0000-0000-000000000002.

  | Momento | Administración | Conteos por rol |
  |---|---|---|
  | Antes del primer upgrade | A | colaborador=2, consejo=1, titular=1, vecino=1 |
  | Antes del primer upgrade | B | colaborador=2, consejo=1, titular=1, vecino=1 |
  | Tras downgrade | A | colaborador=2, consejo=1, titular=1, vecino=1 |
  | Tras downgrade | B | colaborador=2, consejo=1, titular=1, vecino=1 |
  | Tras segundo upgrade | A | administrador=1, auxiliar=1, consejo=1, super_admin=1, vecino=1 |
  | Tras segundo upgrade | B | administrador=1, auxiliar=1, consejo=1, super_admin=1, vecino=1 |

  resuelto por el orquestador, 20/10/2026: la igualdad entre primer y tercer
  conteo se evalúa con el mapeo de D5; los nombres de rol cambian a propósito.
  Cada colaborador de la siembra tiene un nivel distinto. Antes y downgrade
  son idénticos crudos; primer y segundo upgrade son idénticos crudos. El
  oráculo exige las filas de ambos tenants: nunca acepta una tabla vacía.
  El script levanta el stack completo de humo, lo lleva a 0016 y siembra ahí;
  pide `compose exec -T respaldos /usr/local/bin/respaldar.sh --una-vez`, restaura
  con `bash infra/respaldos/restaurar.sh <dump> proptech_restauracion`, aplica
  roles antes (pg_restore usa --no-owner), migra sólo la restaurada y aplica
  roles despues. Verifica RLS habilitada/forzada y que el origen no cambie.
  Docker sólo dentro del script de CI, siempre `docker compose -p proptech`;
  los tres ensayos terminaron con down -v del mismo proyecto. Dumps/conteos
  conservados en `.git/informes-roles-bloque-a-v2/3.5-fqkwXJ/` (ensayo final).
  Logs: `3.5-{inicial,rojo,verde}.log`. Bash -n y ShellCheck 0.10.0 limpios;
  binario temporal en `.git/informes-roles-bloque-a-v2/herramientas/`, sin
  instalación ni configuración global.
  EVIDENCIA de cierre del bloque, comandos completos, en ese orden y de a uno:
  ```text
  $ date +%T && bash infra/ci/test-backend.sh
  12:49:38
  =========== 2037 passed, 1 xfailed, 16 warnings in 475.50s (0:07:55) ===========
  $ date +%T && bash infra/ci/humo.sh
  12:57:43
  HUMO OK
  ...
   Network proptech_datos  Removed
   Network proptech_borde  Removed
   Network proptech_salida_worker  Removed
   Network proptech_aplicacion  Removed
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 227 files already formatted / Success: no issues found in 206 source files
  ```
  JUICIO: ambos scripts terminaron con estado 0; cierre verde (2038 tests,
  +280 frente a 1.1; mismo xfail previo del cambio 7). Las ocho tareas del bloque
  están completas. Logs completos locales: `cierre-{backend,humo}.log`.


## 4. Aplicación y API

- [x] 4.1 `cargar_asignaciones` lee `vinculo` y arma el perfil (D2), en `backend/tests/integracion/test_alcance_api.py` como `proptech_app`: una persona con una fila de cada perfil recibe las asignaciones con el perfil y el alcance correctos, y una fila de B nunca aparece con el tenant de A. RED: con el lector mínimo adaptado en 2.1/3.4, un vecino inquilino todavía se arma como propietario porque no se lee `vinculo` (resuelto por el orquestador, 20/10/2026). Verificación (RD-1, revisión del DBA): pegar en el informe el `EXPLAIN` de la consulta de `cargar_asignaciones` (`acceso/aplicacion/autorizacion.py:31`) corriendo como `proptech_app` con el `administracion_id` (tenant) fijado, mostrando que usa `ix_asignacion_rol_persona`. Escenarios: `autorizacion-por-rol` › Propietaria de una unidad e inquilina de otra. Lecciones: L-016, L-017.

  EVIDENCIA (20/10/2026):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_alcance_api.py::test_lector_arma_cada_perfil_y_su_alcance -q -s
  13:03:15
  E AssertionError: VECINO_PROPIETARIO / propietario != VECINO_INQUILINO / inquilino
  1 failed, 1 warning in 5.23s
  $ cd backend && date +%T && uv run pytest tests/integracion/test_alcance_api.py -q -s
  13:03:30
  6 passed, 1 warning in 8.70s
  ```
  EXPLAIN capturado de la consulta real del lector (sin forzar planificador):
  ```sql
  proptech_app; SET LOCAL app.administracion_id = '4d8aeb5e-35d7-481a-ac6d-6c055996522c';
  SELECT rol, complejo_id, unidad_id, vinculo FROM asignacion_rol WHERE persona_id = %(persona_id)s
  Index Scan using ix_asignacion_rol_persona on asignacion_rol  (cost=0.16..8.18 rows=1 width=96)
    Index Cond: ((administracion_id = (NULLIF(current_setting('app.administracion_id'::text, true), ''::text))::uuid) AND (persona_id = 'a0a805e3-f463-48f9-b92f-7fd0890c9cbc'::uuid))
  ```
  JUICIO: siete perfiles y sus alcances exactos, propietario e inquilino de
  dos unidades del mismo edificio, fila real de B visible en B y oculta en A.
  La fixture verifica current_user=proptech_app, rolsuper=false, rolbypassrls=false.
  Ruff check / format --check / mypy: limpios (227 archivos / 206 fuentes).
  SUPUESTO: ninguno. Logs completos locales en .git/informes-roles-bloque-b/4.1-*.log.

- [x] 4.2 El endpoint de asignación (D7, RA-2) en `backend/tests/integracion/test_asignar_edificio_api.py` y `test_asignacion_validacion.py`: el super admin asigna a una persona de su administración como administrador, contador, auxiliar y consejo (201, la fila tiene ese perfil y la persona pasa a ver el complejo, y la fila de auditoría de esa acción tiene en `detalle` el `complejo_id`, el `rol` asignado y el alcance); un administrador por edificio en su complejo recibe 403 con `invitar_usuarios_y_asignar_edificios`, y en otro complejo 404; un administrador principal, 403; el super admin de A con una persona de B (UUID existente), 404 y nada escrito; un cuerpo con `nivel`, `vinculo` o `unidad_id`, o con `rol` `super_admin`, `vecino`, `titular` o `colaborador`, da 422 nombrando el campo y nada escrito. Verificar si R5 del 2a queda cubierta y decirlo en el informe. RED: con el cuerpo viejo, `rol: "administrador"` da 422 y `nivel` es obligatorio; aparte, el `detalle` de auditoría todavía no tiene `rol` ni alcance (RA-2). Escenarios: `autorizacion-por-rol` › Colaborador asigna un edificio; › Sin permiso y fuera de alcance; › Titular asigna un edificio; › Asignar a una persona de otra administración; › Cuerpo de la asignación con el vocabulario viejo o fuera de lo asignable. Lecciones: L-012, L-017.

  EVIDENCIA (20/10/2026):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_asignacion_validacion.py tests/integracion/test_asignar_edificio_api.py -q
  13:04:56
  E assert 422 == 201 (administrador/contador/auxiliar); consejo: detalle sin rol ni alcance
  10 failed, 14 passed, 1 warning in 18.12s
  $ cd backend && date +%T && uv run pytest tests/unitarios/test_auditoria_detalle.py -q
  13:06:29
  E DetalleInvalido: ... alcance, rol (el validador también necesitaba el contrato nuevo)
  1 failed, 4 passed in 0.13s
  ```
  El 403 del principal nació verde (matriz del bloque A); copia previa real
  `.git/informes-roles-bloque-b/4.2-permisos-original.py`, mutante sin commit:
  ```diff
  -Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS: frozenset({_SA}),
  +Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS: frozenset({_SA, _AP}),
  ```
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_asignar_edificio_api.py::test_administrador_principal_no_asigna -q
  13:07:13
  E assert 201 == 403
  1 failed, 1 warning in 5.70s
  $ cd backend && date +%T && uv run pytest tests/integracion/test_asignar_edificio_api.py tests/integracion/test_asignacion_validacion.py tests/integracion/test_auditoria_transaccion.py tests/integracion/test_identidad_api.py tests/integracion/test_422_sin_el_valor.py tests/integracion/test_altas_sin_id_del_cliente.py tests/unitarios/test_auditoria_detalle.py -q
  13:06:37
  54 passed, 1 warning in 27.81s
  $ cd backend && date +%T && uv run pytest tests/integracion/test_asignar_edificio_api.py::test_administrador_principal_no_asigna tests/unitarios/test_auditoria_detalle.py -q
  13:07:22 (copia restaurada byte a byte)
  6 passed, 1 warning in 5.92s
  ```
  JUICIO: cuatro roles con fila exacta, acceso antes/después y detalle auditado
  por request_id; denegaciones 403/404 y nueve cuerpos 422 con campo explícito.
  Nada escrito incluye asignaciones Y auditoría, también para la persona real
  de B, consultando como proptech_app. R5 del 2a cubierta: unidad_id válido en
  cuerpo con rol válido da 422 con loc=[body, unidad_id] y no escribe nada;
  el cierre de esa deuda corresponde al archivo del change. Llamadores de
  aplicación adaptados a la eliminación de nivel, sin compatibilidad legada.
  Ruff check / format --check / mypy: limpios (227 archivos / 206 fuentes).
  SUPUESTO: ninguno. Logs locales: .git/informes-roles-bloque-b/4.2-*.log.

- [x] 4.3 Las rutas existentes con la matriz nueva, en `backend/tests/integracion/test_alcance_api.py` y un archivo nuevo `test_perfiles_api.py`, como `proptech_app` con la identidad inyectada: un administrador por edificio crea una versión de configuración en su edificio (201, autor y auditoría) y recibe 403 al confirmar "sin saldos previos"; un administrador principal confirma en un edificio que nadie le asignó (200 y auditoría); un administrador principal recibe 403 al crear un edificio; un contador principal lista todos los edificios, lee el padrón de cualquiera (200) y recibe 403 al editar una unidad, crear una categoría y crear una versión; un auxiliar recibe 403 al crear una categoría; el consejo lee el padrón (200) y no edita una unidad (403); el vecino propietario y el inquilino ven su unidad (200), reciben 404 en la de otro vecino del mismo complejo y 403 en la configuración de su complejo; una persona administrador por edificio en A y auxiliar en B recibe 404 en C. RED: con la matriz vieja el administrador por edificio recibe 403 al crear la versión. Escenarios: `autorizacion-por-rol` › Titular; › Contador principal; › Dos asignaciones de la misma persona; › Un colaborador crea un edificio; › Un colaborador "ver" crea una categoría; › El contador no escribe; › El consejo edita una unidad de su edificio; › El consejo lee el padrón; › El vecino pide la configuración de su edificio; › El vecino pide la configuración de otro edificio; › El vecino ve su unidad; › Dos propietarios de la misma unidad; `configuracion-versionada` › Cambiar la tasa; › Un administrador del edificio cambia la tasa; › Un colaborador cambia la tasa; `edificios-y-unidades` › Confirmar sin saldos previos; › Un administrador principal confirma; › Confirmar dos veces; › Un colaborador confirma; › Lista de un colaborador; › Lista de un contador principal; › Unidad de otra administración. Lecciones: L-016, L-017.

  EVIDENCIA (20/10/2026): las rutas ya usan la matriz del bloque A; no se
  cambia un permiso para fabricar implementación. Los 11 tests nuevos
  nacieron verdes a las 13:09:27 (11 passed, 1 warning in 7.60s).
  Copia previa real: .git/informes-roles-bloque-b/4.3-permisos-original.py.
  Seis mutantes independientes, sin commit, restaurados byte a byte cada vez:
  ```diff
  -Accion.CREAR_VERSION_DE_CONFIGURACION: frozenset({_SA, _AP, _AE}),
  +Accion.CREAR_VERSION_DE_CONFIGURACION: frozenset({_SA}),
  -Accion.CONFIRMAR_SIN_SALDOS_PREVIOS: frozenset({_SA, _AP}),
  +Accion.CONFIRMAR_SIN_SALDOS_PREVIOS: frozenset({_SA, _AE}),
  -Accion.CONFIGURAR_PADRON: frozenset({_SA, _AP, _AE}),
  +Accion.CONFIGURAR_PADRON: frozenset({_SA, _AP, _AE, _CP, _CE, _AX, _CO}),
  -Accion.VER_CONFIGURACION_DEL_EDIFICIO: frozenset({_SA, _AP, _AE, _CP, _CE, _AX, _CO}),
  +Accion.VER_CONFIGURACION_DEL_EDIFICIO: frozenset({_SA, _AP, _AE}),
  -if unidad_id is None or asignacion.unidad_id == unidad_id:
  +if True:  # mutante: cualquier unidad del edificio
  -if asignacion.alcance is not Alcance.PRINCIPAL and asignacion.complejo_id != complejo_id:
  +if False:  # mutante: una asignación habilita todos los edificios
  ```
  Todos los comandos siguientes desde backend, con `date +%T &&` antes:
  ```text
  uv run pytest tests/integracion/test_perfiles_api.py::test_administrador_edificio_crea_version_con_autor_y_auditoria_y_no_confirma -q
  13:09:55 E assert 403 == 201 / 1 failed, 1 warning in 5.57s
  uv run pytest tests/integracion/test_perfiles_api.py::test_administrador_principal_confirma_sin_asignacion_y_no_crea_edificio -q
  13:10:02 E assert 403 == 200 / 1 failed, 1 warning in 5.60s
  uv run pytest tests/integracion/test_perfiles_api.py::test_perfiles_lectores_ven_padron_y_no_escriben -q
  13:10:09 E assert 200 == 403 / 4 failed, 1 warning in 6.00s
  uv run pytest tests/integracion/test_perfiles_api.py::test_perfiles_lectores_ven_padron_y_no_escriben -q
  13:10:16 E assert 403 == 200 / 4 failed, 1 warning in 6.01s
  uv run pytest tests/integracion/test_perfiles_api.py::test_vecinos_ven_su_unidad_y_no_la_ajena_ni_configuracion -q
  13:10:23 E assert 200 == 404 / 3 failed, 1 warning in 5.74s
  uv run pytest tests/integracion/test_perfiles_api.py::test_administrador_en_a_auxiliar_en_b_no_extiende_permiso_ni_alcanza_c -q
  13:10:30 E assert 201 == 403 / 1 failed, 1 warning in 5.62s
  uv run pytest tests/integracion/test_perfiles_api.py tests/integracion/test_alcance_api.py tests/integracion/test_edificios_api.py tests/integracion/test_configuracion_api.py tests/integracion/test_padron_api.py tests/unitarios/acceso/test_permisos.py -q
  13:10:39
  539 passed, 1 warning in 30.16s
  ```
  JUICIO: autor y auditoría al crear versión; principal confirma sin asignación
  por edificio, segundo intento 409, crear edificio 403. Contadores de ambos
  alcances, auxiliar y consejo leen y no escriben; principal lista tres edificios;
  propietario, inquilino y copropietario ven su unidad y no la ajena del mismo
  edificio. Identidad mixta no hereda permisos de A en B ni accede a C.
  Se corren también los escenarios existentes de alcance y aislamiento. Emitir
  y corregir aún no tienen rutas: se sostienen por la matriz unitaria firmada.
  Ruff check / format --check / mypy: limpios (228 archivos / 207 fuentes).
  SUPUESTO: ninguno. Logs locales: .git/informes-roles-bloque-b/4.3-*.log.


- [x] 4.4 Consistencia del vocabulario de roles asignables (RA-4, revisión del arquitecto), en un test nuevo (por ejemplo `backend/tests/unitarios/acceso/test_vocabulario_asignable.py`): el conjunto de valores del `Literal` de `CuerpoAsignacion.rol` (`proptech_api/complejos.py`), el conjunto de valores permitidos por `ck_asignacion_rol_rol_valido` (leído de la migración `0017`, no copiado a mano) y el subconjunto asignable por esta ruta del enum `Rol` de `acceso/dominio/permisos.py` tienen que ser el mismo conjunto; el test falla si alguno de los tres cambia sin que los otros dos lo acompañen. RED: se escribe el test contra el estado de hoy (el `Literal` todavía dice `colaborador | consejo`) y se lo ve fallar por la razón correcta antes de actualizar el cuerpo del endpoint en 4.2/D7. Escenarios: ninguno nuevo (sostiene la consistencia entre D7 y D1). Lecciones: L-019, L-022.

  EVIDENCIA (20/10/2026): el test ejecuta upgrade() de 0017 con `op` simulado
  y obtiene el CHECK por su nombre; no copia su lista. Compara todos los roles
  de base/enum y el subconjunto asignable con el Literal de la API.
  JUICIO sobre el orden: la frase RED "antes de actualizar ... en 4.2" no puede
  cumplirse haciendo 4.2 antes de 4.4. Se respeta el orden explícito de Juani:
  el test nace verde y se demuestra el rojo con el Literal anterior mutado.
  Los tres mutantes son independientes, con copia previa real en
  .git/informes-roles-bloque-b/4.4-{api,check,enum}-original.py, sin commit y
  restauración byte a byte antes del siguiente:
  ```diff
  -rol: Literal["administrador", "contador", "auxiliar", "consejo"]
  +rol: Literal["colaborador", "consejo"]
  -"rol IN ('super_admin', 'administrador', 'contador', 'auxiliar', 'consejo', 'vecino')",
  +"rol IN ('super_admin', 'administrador', 'auxiliar', 'consejo', 'vecino')",
  -AUXILIAR = "auxiliar"
  +AUXILIAR = "auxiliar_mutante"
  ```
  ```text
  $ cd backend && date +%T && uv run pytest tests/unitarios/acceso/test_vocabulario_asignable.py -q
  13:11:56 (inicial): 1 passed in 0.36s
  13:12:10 (api-rojo): 1 failed in 0.41s
  13:12:11 (check-rojo): 1 failed in 0.40s
  13:12:13 (enum-rojo): 1 failed in 0.40s
  $ cd backend && date +%T && uv run pytest tests/unitarios/acceso -q
  13:12:14
  437 passed, 1 warning in 0.71s
  ```
  JUICIO: cambiar sólo el Literal, sólo el CHECK o sólo el enum rompe el test.
  Ruff check / format --check / mypy: limpios (229 archivos / 208 fuentes).
  SUPUESTO: ninguno. Logs locales: .git/informes-roles-bloque-b/4.4-*.log.


## 5. La web

- [x] 5.1 Los textos de 403 (D8) en `web/src/componentes/Estados.test.tsx` y el test de `web/src/app/edificios/acciones.ts`: el estado "sin permiso" y el error de crear un edificio dicen "Esto lo puede hacer el super admin de la empresa." y ningún texto de `web/src` (fuera de nombres de tokens CSS) contiene "titular" ni "colaborador" (un test que recorre los archivos con la lista completa de las dos palabras). RED: hoy los dos tests encuentran "titular". Verificación: `bash infra/ci/test-web.sh` en verde. Escenarios: `pantallas-del-edificio` › Sin permiso; › Crear un edificio sin permiso. Lecciones: L-019, L-022.

  EVIDENCIA (20/10/2026):
  ```text
  $ cd web && date +%T && corepack pnpm@12.10.1 vitest run src/componentes/Estados.test.tsx src/app/edificios/acciones.test.ts src/lib/test/vocabulario.test.ts
  13:13:28
  Estados y acción: se recibió "titular de la administración"; barrido: cuatro apariciones, ambas palabras.
  Test Files 3 failed (3) / Tests 3 failed | 5 passed (8)
  $ cd web && date +%T && corepack pnpm@12.10.1 biome ci && corepack pnpm@12.10.1 tsc --noEmit && corepack pnpm@12.10.1 vitest run
  13:14:33
  Checked 141 files; sin errores, 1 warning previo useOptionalChain en app/edificios/page.tsx:43.
  tsc --noEmit: estado 0, sin salida.
  Test Files 47 passed (47) / Tests 300 passed (300)
  $ date +%T && bash infra/ci/test-web.sh
  13:16:17
  Test Files 47 passed (47) / Tests 300 passed (300)
  ```
  HALLAZGO: primera corrida del script a las 13:15:05: 299 passed, 1 failed
  en configuracion/Pantalla.test.tsx:176, recargo enviado "2,75", input "1,50".
  Ese archivo no se modificó. Reproducción aislada y nueva suite por la falla:
  ```text
  $ cd web && date +%T && corepack pnpm@12.10.1 vitest run 'src/app/edificios/[id]/configuracion/Pantalla.test.tsx'
  13:16:14
  Test Files 1 passed (1) / Tests 8 passed (8)
  ```
  JUICIO: ambos textos exactos de D8 y vocabulario completo en todos los
  archivos de web/src, incluidos tests/comentarios; sólo se excluyen nombres
  de tokens CSS. No había test de la acción de alta: se agregó uno que pasa
  por la acción y el cliente HTTP real, con respuesta fetch 403 controlada.
  Aplicada impeccable/clarify con texto ya aprobado y sin rediseño.
  La falla intermitente del recargo queda visible para el rompedor, no se
  suprime ni se altera su test. Logs completos 5.1-*.log en .git/informes-roles-bloque-b/.
  Ruff check / format --check / mypy: limpios (229 archivos / 208 fuentes).
  SUPUESTO: no se atribuye causa a la intermitencia; no se verificó su origen.


## 6. El vocabulario que queda

- [x] 6.1 Barrido del vocabulario viejo (lente de verdad de los comentarios): `rg -n -i "titular|colaborador|Nivel\.|\bnivel\b"` sobre `backend/src`, `backend/migraciones/ayudas_rls.py`, `backend/tests` y `infra/`, con la lista completa en el informe; cada aparición en código o comentario se corrige o se justifica (la migración `0003` y la `0017` lo nombran a propósito, y el log de `reintentos`/`logs` usa "nivel" en otro sentido); el comentario del guardián (`_EXCEPCIONES_COMPLEJO_ID_NULO`) pasa a nombrar el alcance principal. Verificación: la segunda corrida del `rg` en el informe, sólo con las apariciones justificadas. Escenarios: ninguno (sostiene la verdad de los comentarios). Lecciones: L-022.
  De 174 apariciones a 65, todas justificadas en `evidencia-6.1-vocabulario.md`
  (logs/reintentos con "nivel" de severidad, la migración 0016→0017 histórica
  en `test_migracion_roles_de_la_empresa.py` e `infra/ci/ensayo-roles.sh`, y
  datos que el dominio/API deben rechazar). 27 archivos renombrados
  mecánicamente (fixtures, nombres de test, docstrings); ningún assert ni
  valor de rol cambiado — sólo las claves locales (`"titular"`→`"super_admin"`,
  `"colaborador"`→`"administrador"`). El comentario de
  `_EXCEPCIONES_COMPLEJO_ID_NULO` en `test_catalogo_rls.py` ahora nombra el
  alcance principal. De paso se corrigió un docstring desactualizado en
  `complejos/aplicacion/escritura.py` que decía que `asignar_complejo_a_persona`
  era "el único" `@accion_sensible`: ya no es cierto desde las tareas 2-5 de
  este mismo cambio (hoy hay cuatro). Guardián nuevo:
  `backend/tests/unitarios/acceso/test_vocabulario_vigente.py`, rojo
  confirmado con un mutante (comentario con "titular" en
  `permisos.py`, 13:35:44) y verde tras revertirlo (13:35:48).
  Ruff check / format --check / mypy: limpios.

## Correcciones del rompedor (RR)

Informe: `.git/informes-roles/rompedor/informe.md` (leído entero). Se conserva el
árbol recibido en `.git/informes-roles-rr-constructor/inicial/`; la evidencia de
esta sección corresponde a corridas nuevas, con cada corrección aislada.

- [x] RR-1 (MEDIA): traducir el perfil de personal duplicado a 409 con el cuerpo de D6 del 3a (`detail=conflicto`, `campo=rol`), sin asignación ni auditoría nuevas. Revisar la familia de escrituras y trasladar los siete intentos verdes a `test_perfiles_api.py`. D7; `autorizacion-por-rol` › Titular asigna un edificio / Sin permiso y fuera de alcance. L-017, L-019, L-020, L-022.

  EVIDENCIA (20/10/2026, corridas nuevas):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_asignacion_validacion.py -k segundo_perfil -q -p no:cacheprovider --color=no
  15:14:25
  E assert 500 == 409
  3 failed, 13 deselected, 1 warning in 7.89s
  ```
  Los siete intentos trasladados ya eran verdes: se verificaron con dos guardas
  mutadas en `permisos.py` (copia previa y restauración byte a byte):
  ```diff
  +    if asignaciones:
  +        return True
  ```
  Ese mismo diff de dos líneas se aplicó al inicio de `puede` y de `alcanza`.
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_perfiles_api.py -k 'lectores_no_escriben or administrador_por_edificio_no_toca or principal_no_cruza or propietaria_de_una' -q -p no:cacheprovider --color=no
  15:14:44
  7 failed, 11 deselected, 1 warning in 7.89s
  ```
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_asignacion_validacion.py tests/integracion/test_perfiles_api.py tests/integracion/test_asignar_edificio_api.py tests/integracion/test_auditoria_transaccion.py tests/integracion/test_edificios_api.py tests/integracion/test_configuracion_api.py tests/integracion/test_padron_api.py -q -p no:cacheprovider --color=no
  15:14:59
  139 passed, 1 warning in 40.69s
  $ cd backend && date +%T && uv run ruff check . && uv run ruff format --check . && uv run mypy
  15:15:45
  All checks passed! / 230 files already formatted / Success: no issues found in 209 source files
  ```
  JUICIO: contrato completo de conflicto y rollback verificados; las otras
  escrituras del módulo ya usan `transaccion`. Traslado definitivo de los siete
  intentos, sin carpeta `rompedor_roles` (ya ausente al recibir el árbol).
  SUPUESTO: ninguno. Logs en `.git/informes-roles-rr-constructor/rr1-*.log`.

- [x] RR-2 (MEDIA): exigir en el detalle de la auditoría la persona destinataria y el id exacto de la asignación, además de rol y alcance. D7, RA-2; `autorizacion-por-rol` › Titular asigna un edificio. L-019.

  EVIDENCIA (20/10/2026):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_asignacion_validacion.py -k auditoria -q -p no:cacheprovider --color=no
  15:16:10
  E AssertionError: auditoría sin persona destino (... detalle sin persona_id)
  1 failed, 16 deselected, 1 warning in 5.40s
  ```
  Se reforzó el test trasladado: exige ambos UUID exactos, sin buscar texto ni
  aceptar `entidad_id` como sustituto. El id de asignación también se vio fallar
  con copia previa, diff real y restauración byte a byte:
  ```diff
  -                "asignacion_id": str(fila.id),
  +                "asignacion_id": str(persona_id),
  ```
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_asignacion_validacion.py -k auditoria -q -p no:cacheprovider --color=no
  15:16:52
  E assert detalle.get("asignacion_id") == str(asignacion)
  1 failed, 16 deselected, 1 warning in 5.33s
  ```
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_asignacion_validacion.py tests/integracion/test_asignar_edificio_api.py tests/integracion/test_auditoria_transaccion.py tests/unitarios/test_auditoria_detalle.py -q -p no:cacheprovider --color=no
  15:17:06
  39 passed, 1 warning in 17.66s
  $ cd backend && date +%T && uv run ruff check . && uv run ruff format --check . && uv run mypy
  15:17:21
  All checks passed! / 230 files already formatted / Success: no issues found in 209 source files
  ```
  JUICIO: actor, destinataria y asignación quedan diferenciados; modelo estricto
  y rollback de asignación/auditoría verdes. No se modifican filas históricas.
  SUPUESTO: ninguno. Logs locales `rr2-*.log`.

- [ ] RR-3 (BAJA): impedir consejo duplicado por persona y edificio como `proptech_app`, manteniendo coexistencia con personal, aislamiento y downgrade. D5, RA-5; `autorizacion-por-rol` › La base sostiene la forma de cada asignación. L-016, L-018, L-019, L-020.

- [ ] RR-4 (BAJA): un 403 de `informar_pago` identifica a propietario/inquilino, sin atribuir el permiso al super admin. D8, excepción autorizada por Juani en esta corrección; `pantallas-del-edificio` › Sin permiso. L-019, L-022.

## 7. Cierre

- [x] 7.1 El barrido de rutas protegidas (`test_rutas_protegidas.py`) y el guardián del catálogo (`test_catalogo_rls.py`) siguen en verde sin cambiar su lista de rutas ni sus excepciones (este cambio no suma rutas ni tablas), y el test de fronteras de módulos sigue en verde. Verificación: los tres archivos corridos con su salida. Escenarios: `autorizacion-por-rol` › Las rutas de hoy siguen cubiertas (existente). Lecciones: L-016.
  Sin cambios en `_TABLAS_TECNICAS` ni en `_EXCEPCIONES_COMPLEJO_ID_NULO`
  (sólo su comentario, ver 6.1); `test_rutas_protegidas.py` sin tocar.

  ```
  13:36:08 tests/unitarios/test_fronteras_de_modulos.py -q   → 5 passed in 0.24s
  13:36:12 tests/integracion/test_rutas_protegidas.py -q    → 67 passed in 7.13s
  13:36:24 tests/integracion/test_catalogo_rls.py -q        → 12 passed in 4.41s
  ```

  Corrida de cierre (L-010), de a uno, SHA b2e8672 (commit de 6.1):

  ```
  13:37:28 bash infra/ci/test-backend.sh  → 2061 passed, 1 xfailed, 16 warnings in 476.20s (0:07:56)
  13:45:33 bash infra/ci/test-web.sh      → 47 test files, 300 tests passed in 8.42s
  13:45:45 bash infra/ci/humo.sh          → HUMO OK, compose down -v limpio
  ```
  vs. la 1.1 (2 failed, 2034 passed, 1 xfailed): los dos failed de la 1.1 ya
  no están y se sumaron los tests de las tareas 2-6. No se corrió 7.2 (fuera
  de este alcance); esta corrida es evidencia para 7.1, no el cierre formal.
- [ ] 7.2 Corrida de cierre después de la última vuelta (L-010): `bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh` y `bash infra/ci/humo.sh`, en ese orden y de a uno (comparten contenedores con nombres del proyecto), con la cantidad de tests de cada lado comparada con la 1.1, la hora y el SHA (`git rev-parse HEAD`). Verificación: los tres comandos con su salida en el informe. Escenarios: todos los del cambio, por última vez juntos. Lecciones: L-003, L-005, L-010.
