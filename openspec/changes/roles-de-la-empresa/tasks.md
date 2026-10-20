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


- [ ] 2.3 El alcance (D3) en `backend/tests/unitarios/acceso/test_permisos.py`: `alcanza` por perfil y alcance (principal, todo complejo y unidad de la administración; por edificio, su complejo y sus unidades y ningún otro; por unidad, su unidad y su complejo, nunca otra unidad del mismo complejo), dos propietarios distintos de la misma unidad y un inquilino de otra. RED: con `alcanza` viejo, un contador principal no alcanza nada. Escenarios: `autorizacion-por-rol` › Colaborador en un edificio no asignado; › Vecino en la unidad de otro vecino; › Consejo en otro edificio; › Contador principal; › Dos asignaciones de la misma persona (la parte del dominio). Lecciones: L-019.

  JUICIO: pendiente; depende del modelo de asignación de 2.1. No hay RED/GREEN ni
  implementación; `alcanza` original sigue intacto.


## 3. La base

- [ ] 3.1 Migración `0017_roles_de_la_empresa`, `upgrade` (D5), en `backend/tests/integracion/test_migracion_roles_de_la_empresa.py` con contenedor propio: sembrar en 0016, en dos administraciones, una fila de cada forma vieja (titular, colaborador "editar", colaborador "ver", consejo, vecino); `upgrade`; leer como `proptech_app` con el tenant de cada una y exigir el perfil nuevo de cada fila y ninguna con `titular`, `colaborador` ni `nivel`; `relrowsecurity` y `relforcerowsecurity` siguen prendidos y con el tenant de A no aparece ninguna fila de B; los tres objetos nuevos existen después del `upgrade`: el índice único `uq_asignacion_rol_persona_unidad` (D2), el índice único `uq_asignacion_rol_persona_alcance` (RA-5) y el índice `ix_asignacion_rol_persona` (RD-1, el que sirve a `cargar_asignaciones`). Tres rojos, cada uno sobre una copia de la migración (L-013): sin el `NO FORCE`, las filas quedan con el vocabulario viejo y la migración termina sin error (el silencio que esta tarea existe para ver); sin el `FORCE` final, el test de aislamiento falla; con un `RAISE` agregado después de convertir, la tabla queda como en 0016 y con `FORCE`. Además, dos filas de vecino de la misma persona y unidad hacen fallar el `upgrade` sin cambiar nada y con un mensaje sin ids. Escenarios: `autorizacion-por-rol` › Conversión en dos administraciones; › La tabla sigue aislada; › Una relación repetida frena la conversión. Lecciones: L-013, L-016, L-018, L-020.

  EVIDENCIA (20/10/2026): experimento aislado sobre la imagen PostgreSQL del Compose,
  con Testcontainers propio, dueño proptech_migrador sin superusuario ni BYPASSRLS,
  dos administraciones y verificación de filas como proptech_app con cada tenant.
  **No es la migración 0017 ni sus tests de aceptación**; comprueba la contradicción
  de la reproducción exigida antes de implementar una migración distinta de D5.

  ```text
  $ cd backend && date +%T && uv run pytest ../.git/informes-roles-bloque-a/test_validacion_check.py -q -s
  11:51:54
  NO FORCE=False; filas convertidas=0
  NO FORCE=True; filas convertidas=2
  E psycopg.errors.CheckViolation: check constraint "ck_asignacion_rol_rol_valido"
    of relation "asignacion_rol" is violated by some row
  FAILED test_la_secuencia_exigida_termina_sin_error[sin_NO_FORCE]
  1 failed, 1 passed in 4.36s
  ```

  JUICIO: pendiente. D5 exige recrear y validar los CHECK del vocabulario nuevo.
  Sin NO FORCE, el UPDATE no ve filas, pero el CHECK nuevo sí valida las filas
  existentes y rechaza titular. Por eso no se puede obtener a la vez la migración
  de D5 y el mutante exigido por esta tarea que "termina sin error" con filas viejas.
  No se omitió ni se dejó NOT VALID ningún CHECK para fabricar ese silencio.
  El control con NO FORCE pasa; ambos caminos verifican FORCE restaurado y las
  filas esperadas, incluyendo el rollback del camino que falla. El contenedor
  del experimento fue eliminado por Testcontainers. Código y salida completos:
  `.git/informes-roles-bloque-a/test_validacion_check.py` y `3.1-conflicto-check.log`.
  No se implementó 0017 ni se marca esta tarea terminada.
  SUPUESTO: ninguno para el resultado del experimento.

- [ ] 3.2 La forma de cada asignación en la base (D1, D2), en el mismo archivo, como `proptech_app` en `head`: una fila válida de cada perfil y alcance entra (nueve formas); cada forma inválida falla por el `CHECK` y no deja nada (auxiliar, consejo o vecino sin complejo; super admin con complejo; vecino sin vínculo; administrador con vínculo; rol `titular`, `colaborador` y uno inventado); la misma persona propietaria e inquilina de una unidad falla por el índice único; la misma persona con dos asignaciones de rol de personal (cualquier combinación de super admin, administrador, contador o auxiliar) en el mismo alcance falla por `uq_asignacion_rol_persona_alcance` (RA-5), y esto vale también con `complejo_id` nulo en las dos (alcance principal, antes exento con un `UNIQUE` sin `NULLS NOT DISTINCT`); la misma persona con un rol de personal y, además, una fila de consejo o de vecino en el mismo edificio entra sin problema (RA-5: son asignaciones de otro tipo); dos propietarios distintos y un inquilino distinto de la misma unidad entran. Actualizar los casos de `test_rls_acceso_minimo.py` que prueban en `head` el `CHECK` de 0003 (colaborador sin nivel), sin borrar ninguno sin reemplazo. RED: con la base de 0016 los inserts del vocabulario nuevo fallan. Escenarios: `autorizacion-por-rol` › Alcance principal regalado; › Super admin atado a un edificio; › Vecino sin vínculo o personal con vínculo; › Perfil desconocido; › Propietaria e inquilina de la misma unidad; › Dos roles de personal en el mismo alcance; › Dos propietarios de la misma unidad (la parte de la base). Lecciones: L-016, L-018.

  JUICIO: pendiente; depende de 0017 (3.1 detenida). No hay RED/GREEN, cambios en
  los CHECK ni cambios a los tests de `test_rls_acceso_minimo.py`.

- [ ] 3.3 El `downgrade` (D5, E7, RD-3, RD-4), en el mismo archivo: con sólo filas con forma vieja, `downgrade 0016` corre en el orden de D5 (`LOCK`, `NO FORCE`, chequeo previo de conteos, conversión, `FORCE`) y devuelve cada una a su rol y nivel exactos en las dos administraciones; el catálogo de `asignacion_rol` (columnas **excluyendo `ordinal_position`**, que cambia con el orden de creación y no es señal real de drift; `CHECK`; que ya no estén la constraint `uq_asignacion_rol_persona_unidad` ni los índices `uq_asignacion_rol_persona_alcance` y `ix_asignacion_rol_persona`; políticas; `FORCE`) queda idéntico al de antes del `upgrade`, comparado entero; después `upgrade` vuelve a pasar. Con un contador, con un administrador principal y con un vecino inquilino, por separado, el `downgrade` falla, el mensaje dice cuántas filas de cada tipo y no trae ningún id ni nombre, y ni las filas ni el esquema cambian. RED: una copia del `downgrade` que convierte el inquilino en vecino en vez de fallar pasa el caso que debía fallar, y el test lo muestra; otra copia que hace el chequeo previo de conteos antes del `LOCK`/`NO FORCE` (en vez de después, RD-3) se marca y se corrige. Escenarios: `autorizacion-por-rol` › Volver atrás sin datos nuevos; › Volver atrás con un contador o un inquilino. Lecciones: L-013, L-016, L-022.

  JUICIO: pendiente; depende de 0017 (3.1 detenida). No hay RED/GREEN ni downgrade.
  Conflicto adicional de D5 para aclarar antes de implementarlo: D2 y el upgrade
  crean `uq_asignacion_rol_persona_unidad` como índice único parcial; el downgrade
  lo llama constraint. Se debe precisar ese paso, sin cambiarlo por interpretación.

- [ ] 3.4 Todo `INSERT` a `asignacion_rol` del repositorio (L-023): `rg` sobre el repositorio entero (`backend/`, `infra/`, `web/`, `openspec/changes/acceso-de-desarrollo/`) y, aparte, sobre `.git/informes-3b/`; pasar al vocabulario nuevo los ayudantes de `tests/integracion/conftest.py` y cada test que siembra asignaciones, con el mapeo de D5 (titular → super admin, colaborador "editar" → administrador, "ver" → auxiliar, vecino → vecino propietario). La carga del ejemplo sin commitear no se toca: se anota en el informe qué línea cambiaría. La identidad de desarrollo (fuera de este cambio, en el change `acceso-de-desarrollo`, en curso y sin firmar) necesita SUMAR una fila de rol `super_admin` a la persona de ejemplo con el vocabulario nuevo, no reemplazar lo que ya tenga (RA-1, revisión del arquitecto): se anota en el informe, y `acceso-de-desarrollo` hereda esta tarea pendiente — es ese change el que tiene que retomarla (ver `design.md`, Open Questions, "El orden con `acceso-de-desarrollo`"). Verificación: la lista del `rg` antes y después en el informe, y la suite completa del backend en verde con la misma cantidad de tests de la 1.1 más los nuevos. Escenarios: ninguno nuevo (sostiene los existentes). Lecciones: L-003, L-023.

  EVIDENCIA (20/10/2026): barrido del repo entero, incluyendo infra/, web/,
  openspec/changes/acceso-de-desarrollo/ y, aparte, .git/informes-3b/ con su 2.3-wip/.
  Se usó rg con --hidden --no-ignore y patrón multilínea que admite SQL repartido
  entre literales; se excluyeron .env, .env.*, especificacion/, .git/ en el barrido
  general y carpetas de dependencias/cachés. Ningún .env fue leído ni mostrado.
  Comando (las exclusiones anteriores se pasan como -g):

  ```text
  rg -n -i -U --hidden --no-ignore --file .git/informes-roles-bloque-a/patron-insert.txt .
  rg -n -i -U --hidden --no-ignore --file .git/informes-roles-bloque-a/patron-insert.txt .git/informes-3b/
  ```

  Lista completa de ubicaciones ANTES (18); la segunda corrida DESPUÉS es idéntica,
  sin modificaciones de INSERT. SQL completo local en `3.4-repo-{antes,despues}.log`
  dentro de `.git/informes-roles-bloque-a/`:

  ```text
backend/src/proptech_core/complejos/aplicacion/escritura.py:54
backend/tests/integracion/conftest.py:246
backend/tests/integracion/test_alcance_api.py:152
backend/tests/integracion/test_alcance_api.py:158
backend/tests/integracion/test_alcance_api.py:163
backend/tests/integracion/test_alcance_api.py:168
backend/tests/integracion/test_alcance_api.py:174
backend/tests/integracion/test_altas_sin_id_del_cliente.py:210
backend/tests/integracion/test_asignar_edificio_api.py:148
backend/tests/integracion/test_asignar_edificio_api.py:153
backend/tests/integracion/test_asignar_edificio_api.py:159
backend/tests/integracion/test_asignar_edificio_api.py:164
backend/tests/integracion/test_identidad_api.py:152
backend/tests/integracion/test_regresiones_de_aislamiento_y_grupos_vacios.py:59
backend/tests/integracion/test_rls_acceso_minimo.py:311
backend/tests/integracion/test_rls_acceso_minimo.py:350
backend/tests/integracion/test_rls_acceso_minimo.py:361
openspec/changes/archive/2026-10-19-configuracion-del-edificio/tasks.md:2672
  ```

  Cero INSERT en infra/, web/, acceso-de-desarrollo/ y .git/informes-3b/ (ambas
  corridas); los archivos ignorados también se revisaron con --no-ignore.
  En `.git/informes-3b/2.3-wip/ejemplo.py:211`, entre el INSERT de persona (203-210)
  y crear_edificio (212), acceso-de-desarrollo debe SUMAR la fila super_admin de
  esa persona, con complejo/unidad/vínculo nulos, conservando otras asignaciones
  (RA-1). Material WIP intacto. Ese change hereda la tarea pendiente, como dice D5.
  La ocurrencia archivada de 3a es evidencia histórica: no se debe reescribir.
  JUICIO: pendiente; inventario realizado, sin conversión de fixtures ni código.
  La suite completa verde solicitada depende también de 4.1 (SELECT nivel) y
  4.2 (INSERT con nivel y cuerpo colaborador/consejo): cambiar sólo la siembra no
  podría dar ese verde sobre 0017. No se adelantan esas tareas sin resolver el
  límite del bloque. No hay RED/GREEN de implementación ni se marca [x].
  SUPUESTO: ninguno para el barrido; el alta de ejemplo sigue pendiente.


- [ ] 3.5 Ensayo de la migración sobre la copia más fiel disponible (RD-2, revisión del DBA): **supuesto declarado** — no hay producción ni datos reales de este sistema, nunca se desplegó (Migration Plan, "Despliegue: no hay"). Levantar el stack de humo (`infra/ci/humo.sh`) con sus dos administraciones sembradas; volcar con `compose exec -T respaldos /usr/local/bin/respaldar.sh --una-vez`; restaurar ese dump en una base aparte con `bash infra/respaldos/restaurar.sh <archivo_dump> proptech_restauracion` (el mismo camino que usa `humo.sh`); sobre esa base restaurada correr `alembic upgrade` a 0017, `alembic downgrade` a 0016 y `alembic upgrade` otra vez, comparando conteos por `administracion_id` y por `rol` antes del primer `upgrade`, después del `downgrade` y después del segundo `upgrade`. Verificación: los tres conteos (antes, tras el `downgrade`, tras el segundo `upgrade`) en el informe, idénticos entre el primero y el tercero. Escenarios: `autorizacion-por-rol` › Conversión en dos administraciones (repetida sobre la copia restaurada, no sobre datos sembrados a mano). Lecciones: L-013, L-016.

  JUICIO: pendiente; el ensayo depende del upgrade y downgrade de 3.1/3.3, detenidos.
  No se presenta el humo de 1.1 como ensayo de 0017, ni una tabla vacía como prueba
  de conversión. No hay conteos de este ensayo ni RED/GREEN de la migración.
  SUPUESTO declarado por el diseño (RD-2), sin verificar externamente: no hay
  producción ni datos reales y el sistema nunca se desplegó.



  EVIDENCIA de cierre del intento (no valida tareas pendientes de implementación):

  ```text
  $ date +%T && bash infra/ci/test-backend.sh
  11:55:24
=========== 1757 passed, 1 xfailed, 16 warnings in 427.25s (0:07:07) ===========
  $ date +%T && bash infra/ci/humo.sh
  12:03:03
  HUMO OK
 Network proptech_datos  Removed
 Network proptech_aplicacion  Removed
 Network proptech_borde  Removed
 Network proptech_salida_worker  Removed
  ```

  Ambos terminaron con estado 0, en ese orden y de a uno. El humo ejecutó su
  limpieza con `-p proptech`, sin invocaciones manuales de Docker. Logs locales:
  `.git/informes-roles-bloque-a/cierre-{backend,humo}.log`.
  `git diff --exit-code bf066ce -- backend infra web` terminó con estado 0:
  sólo se documentó el intento; no quedaron cambios de aplicación, tests o infra.
  Sólo 1.1 está completada; 2.1 a 3.5 quedan pendientes con los motivos anteriores.

## 4. Aplicación y API

- [ ] 4.1 `cargar_asignaciones` lee `vinculo` y arma el perfil (D2), en `backend/tests/integracion/test_alcance_api.py` como `proptech_app`: una persona con una fila de cada perfil recibe las asignaciones con el perfil y el alcance correctos, y una fila de B nunca aparece con el tenant de A. RED: hoy la consulta pide `nivel`, que ya no existe (`UndefinedColumn`). Verificación (RD-1, revisión del DBA): pegar en el informe el `EXPLAIN` de la consulta de `cargar_asignaciones` (`acceso/aplicacion/autorizacion.py:31`) corriendo como `proptech_app` con el `administracion_id` (tenant) fijado, mostrando que usa `ix_asignacion_rol_persona`. Escenarios: `autorizacion-por-rol` › Propietaria de una unidad e inquilina de otra. Lecciones: L-016, L-017.
- [ ] 4.2 El endpoint de asignación (D7, RA-2) en `backend/tests/integracion/test_asignar_edificio_api.py` y `test_asignacion_validacion.py`: el super admin asigna a una persona de su administración como administrador, contador, auxiliar y consejo (201, la fila tiene ese perfil y la persona pasa a ver el complejo, y la fila de auditoría de esa acción tiene en `detalle` el `complejo_id`, el `rol` asignado y el alcance); un administrador por edificio en su complejo recibe 403 con `invitar_usuarios_y_asignar_edificios`, y en otro complejo 404; un administrador principal, 403; el super admin de A con una persona de B (UUID existente), 404 y nada escrito; un cuerpo con `nivel`, `vinculo` o `unidad_id`, o con `rol` `super_admin`, `vecino`, `titular` o `colaborador`, da 422 nombrando el campo y nada escrito. Verificar si R5 del 2a queda cubierta y decirlo en el informe. RED: con el cuerpo viejo, `rol: "administrador"` da 422 y `nivel` es obligatorio; aparte, el `detalle` de auditoría todavía no tiene `rol` ni alcance (RA-2). Escenarios: `autorizacion-por-rol` › Colaborador asigna un edificio; › Sin permiso y fuera de alcance; › Titular asigna un edificio; › Asignar a una persona de otra administración; › Cuerpo de la asignación con el vocabulario viejo o fuera de lo asignable. Lecciones: L-012, L-017.
- [ ] 4.3 Las rutas existentes con la matriz nueva, en `backend/tests/integracion/test_alcance_api.py` y un archivo nuevo `test_perfiles_api.py`, como `proptech_app` con la identidad inyectada: un administrador por edificio crea una versión de configuración en su edificio (201, autor y auditoría) y recibe 403 al confirmar "sin saldos previos"; un administrador principal confirma en un edificio que nadie le asignó (200 y auditoría); un administrador principal recibe 403 al crear un edificio; un contador principal lista todos los edificios, lee el padrón de cualquiera (200) y recibe 403 al editar una unidad, crear una categoría y crear una versión; un auxiliar recibe 403 al crear una categoría; el consejo lee el padrón (200) y no edita una unidad (403); el vecino propietario y el inquilino ven su unidad (200), reciben 404 en la de otro vecino del mismo complejo y 403 en la configuración de su complejo; una persona administrador por edificio en A y auxiliar en B recibe 404 en C. RED: con la matriz vieja el administrador por edificio recibe 403 al crear la versión. Escenarios: `autorizacion-por-rol` › Titular; › Contador principal; › Dos asignaciones de la misma persona; › Un colaborador crea un edificio; › Un colaborador "ver" crea una categoría; › El contador no escribe; › El consejo edita una unidad de su edificio; › El consejo lee el padrón; › El vecino pide la configuración de su edificio; › El vecino pide la configuración de otro edificio; › El vecino ve su unidad; › Dos propietarios de la misma unidad; `configuracion-versionada` › Cambiar la tasa; › Un administrador del edificio cambia la tasa; › Un colaborador cambia la tasa; `edificios-y-unidades` › Confirmar sin saldos previos; › Un administrador principal confirma; › Confirmar dos veces; › Un colaborador confirma; › Lista de un colaborador; › Lista de un contador principal; › Unidad de otra administración. Lecciones: L-016, L-017.

- [ ] 4.4 Consistencia del vocabulario de roles asignables (RA-4, revisión del arquitecto), en un test nuevo (por ejemplo `backend/tests/unitarios/acceso/test_vocabulario_asignable.py`): el conjunto de valores del `Literal` de `CuerpoAsignacion.rol` (`proptech_api/complejos.py`), el conjunto de valores permitidos por `ck_asignacion_rol_rol_valido` (leído de la migración `0017`, no copiado a mano) y el subconjunto asignable por esta ruta del enum `Rol` de `acceso/dominio/permisos.py` tienen que ser el mismo conjunto; el test falla si alguno de los tres cambia sin que los otros dos lo acompañen. RED: se escribe el test contra el estado de hoy (el `Literal` todavía dice `colaborador | consejo`) y se lo ve fallar por la razón correcta antes de actualizar el cuerpo del endpoint en 4.2/D7. Escenarios: ninguno nuevo (sostiene la consistencia entre D7 y D1). Lecciones: L-019, L-022.

## 5. La web

- [ ] 5.1 Los textos de 403 (D8) en `web/src/componentes/Estados.test.tsx` y el test de `web/src/app/edificios/acciones.ts`: el estado "sin permiso" y el error de crear un edificio dicen "Esto lo puede hacer el super admin de la empresa." y ningún texto de `web/src` (fuera de nombres de tokens CSS) contiene "titular" ni "colaborador" (un test que recorre los archivos con la lista completa de las dos palabras). RED: hoy los dos tests encuentran "titular". Verificación: `bash infra/ci/test-web.sh` en verde. Escenarios: `pantallas-del-edificio` › Sin permiso; › Crear un edificio sin permiso. Lecciones: L-019, L-022.

## 6. El vocabulario que queda

- [ ] 6.1 Barrido del vocabulario viejo (lente de verdad de los comentarios): `rg -n -i "titular|colaborador|Nivel\.|\bnivel\b"` sobre `backend/src`, `backend/migraciones/ayudas_rls.py`, `backend/tests` y `infra/`, con la lista completa en el informe; cada aparición en código o comentario se corrige o se justifica (la migración `0003` y la `0017` lo nombran a propósito, y el log de `reintentos`/`logs` usa "nivel" en otro sentido); el comentario del guardián (`_EXCEPCIONES_COMPLEJO_ID_NULO`) pasa a nombrar el alcance principal. Verificación: la segunda corrida del `rg` en el informe, sólo con las apariciones justificadas. Escenarios: ninguno (sostiene la verdad de los comentarios). Lecciones: L-022.

## 7. Cierre

- [ ] 7.1 El barrido de rutas protegidas (`test_rutas_protegidas.py`) y el guardián del catálogo (`test_catalogo_rls.py`) siguen en verde sin cambiar su lista de rutas ni sus excepciones (este cambio no suma rutas ni tablas), y el test de fronteras de módulos sigue en verde. Verificación: los tres archivos corridos con su salida. Escenarios: `autorizacion-por-rol` › Las rutas de hoy siguen cubiertas (existente). Lecciones: L-016.
- [ ] 7.2 Corrida de cierre después de la última vuelta (L-010): `bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh` y `bash infra/ci/humo.sh`, en ese orden y de a uno (comparten contenedores con nombres del proyecto), con la cantidad de tests de cada lado comparada con la 1.1, la hora y el SHA (`git rev-parse HEAD`). Verificación: los tres comandos con su salida en el informe. Escenarios: todos los del cambio, por última vez juntos. Lecciones: L-003, L-005, L-010.
