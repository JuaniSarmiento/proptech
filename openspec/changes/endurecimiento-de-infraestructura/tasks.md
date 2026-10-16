Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el paso
rojo es obligatorio y se anota en el informe con el comando y su salida. Si un test nuevo pasa antes de
escribir el código, no prueba nada: se corrige hasta verlo fallar por la razón correcta (L-019). Los
chequeos verifican el efecto en el stack vivo o en el proceso, no sólo la forma del archivo (L-018).
"Verde" quiere decir lint, formato, tipos y tests del lado tocado (L-005), más `shellcheck` sobre todo
script de Bash tocado. Para ver fallar una verificación contra configuración mutada a propósito, se
muta una copia o se saca antes una copia del original y se compara con un diff real (L-013). Cada tarea
nombra los escenarios de la spec que cubre y las lecciones que aplica. Ninguna tarea supera medio día.

Precondiciones: el 2a (`aislamiento-por-administracion`) archivado. Gobernanza MEDIUM: sin aprobación
previa de un socio; las decisiones no obvias (la lista de capacidades, los digests, el mecanismo de
`handle_errors`) van en el informe. **Regla de freno** (`proposal.md`): las tareas 6.1 y 6.2 tocan el
arranque del candado; si aparece algo que afecte el aislamiento, se frena y se consulta a Juani. P1 de
`proposal.md` quedó respondida (a) el 16/10/2026: la 6.0 (V3-5) va antes de la 6.1.

## 1. Línea de base

- [x] 1.1 Correr la suite completa antes de tocar nada (`bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh`, `bash infra/ci/humo.sh`, en ese orden y de a uno, D7) y anotar la cantidad de tests de cada lado, con la hora y el commit (`git rev-parse HEAD`); si algo falla, frenar e informarlo como falla previa. Anotar además la duración por trabajo de las últimas corridas del CI (`gh run view <id> --json jobs`), que es lo que respalda los `timeout-minutes` de 4.3. Escenarios: ninguno (medición de partida). Lecciones: L-003.

## 2. El humo nombra su falla

- [x] 2.1 Pasos con nombre (D6): `infra/ci/pasos.sh` con `paso N "descripción"` y un único `trap ... ERR` con `set -E` que imprime número, descripción, `$LINENO` y `$BASH_COMMAND`; `humo.sh` lo usa en sus 21 pasos y así cubre los 35 `[ ]` y los 11 `grep -q` sueltos; los `if !` que ya existen se quedan (L-014). Test de efecto sin Docker en `tests/infra/test_pasos_humo.py`: un script mínimo que usa `pasos.sh` y fuerza a fallar un `[ ]`, un `grep -q` y un `if !` tiene que imprimir número, descripción, línea y comando en los tres casos; verlo fallar contra el `humo.sh` de hoy (que no los nombra). Escenarios: `integracion-continua` › Un paso que falla. Lecciones: L-014, L-016, L-018.
- [x] 2.2 La falla queda en el log (D6, F-1): si `estado != 0`, `limpiar` vuelca `docker compose -p proptech ps -a` y `docker compose -p proptech logs --no-color --tail=200` antes del `down -v`. **Rojo**: con una copia de Compose que le saca a `redis` una capacidad que su entrypoint necesita (o `CHOWN` una vez que 3.2 existe), hoy el log del humo no contiene el error de `redis`; después, sí. Va antes de 3.2 para que las fallas de capacidades se vean. Escenarios: `integracion-continua` › La falla queda en el log. Lecciones: L-013, L-016.
- [x] 2.3 `humo.sh` ejecutable (D6, deuda D-5 del 2a): `git update-index --chmod=+x infra/ci/humo.sh` y un test en `tests/infra/test_humo.py` que exige `100755` en todo `infra/**/*.sh` según `git ls-files -s`. **Rojo**: hoy `humo.sh` es `100644`. Escenarios: `integracion-continua` › El script del humo es ejecutable. Lecciones: L-016.

## 3. Proxy y contenedores

- [x] 3.1 Cabeceras y volúmenes, parte estática (D1, D2) en `tests/infra/test_caddyfile_seguridad.py` y `tests/infra/test_compose.py`: el `Caddyfile` fija las cuatro cabeceras y quita `Server`, `Via` y `X-Powered-By`, también con `header_down` en cada `reverse_proxy` y en las respuestas de error que genera Caddy (`handle_errors` o el mecanismo que se elija viendo el rojo de 5.3); `web/next.config.ts` tiene `poweredByHeader: false`; Caddy monta `datos_caddy:/data` y `config_caddy:/config`. El rojo de punta a punta de 5.3 se captura **antes** de implementar esta tarea. Escenarios: `entorno-de-ejecucion` › Respuesta de la web y de la API, › Error del proxy, › Caddy recreado conserva sus datos (las partes estáticas). Lecciones: L-004.
- [x] 3.2 Privilegios y capacidades (D3) en `tests/infra/test_compose.py`: todos los servicios con `no-new-privileges` y `cap_drop: [ALL]`; `cap_add` sólo en `db`, `redis` y `caddy` (éste, sólo `NET_BIND_SERVICE`), igual a la lista fijada. Para fijarla, levantar el stack sin cada capacidad candidata (sobre una copia de Compose, L-013) **dos veces**: sobre volúmenes nuevos y con un segundo `up` sobre volúmenes existentes; anotar cuál hizo falta, en cuál de las dos situaciones y el error que dio (que 2.2 deja en el log). La que no hizo falta en ninguna no entra. La lista queda en un comentario de `compose.yaml`. Escenarios: `entorno-de-ejecucion` › Privilegios y capacidades en el stack vivo (la parte estática). Lecciones: L-013.
- [x] 3.3 PID 1 no root en siete servicios (D4): el humo lee `/proc/1/status` en `api`, `web`, `worker`, `migraciones` (con `docker compose run --no-deps`), `respaldos`, `redis` y `db`; `api` y `web` dejan `exec id -u`. El rojo se ve **en cada uno de los siete** con una copia de Compose que lo hace correr como root (`user: "0:0"`; en `db` y `redis`, además, con el entrypoint salteado, porque si no `gosu` baja de usuario igual y el chequeo no puede fallar), y se anota la salida de los siete rojos. `caddy` queda fuera y declarado root (D3). Escenarios: `entorno-de-ejecucion` › Usuario del proceso; › Un servicio configurado como root. Lecciones: L-013, L-016.
- [x] 3.4 Privilegios en el stack vivo (D3): el humo lee `/proc/1/status` de cada servicio y exige `NoNewPrivs: 1` y `CapBnd` igual a la lista justificada de ese servicio (vacía salvo `db`, `redis` y `caddy`). **Rojo**: con una copia de Compose sin `cap_drop` en un servicio, y otra sin `security_opt` en otro, el chequeo falla nombrando el servicio. Escenarios: `entorno-de-ejecucion` › Privilegios y capacidades en el stack vivo. Lecciones: L-013, L-016, L-018.

## 4. CI

- [x] 4.1 Flake de `unitarios/test_worker_tenant.py` (deuda V3-8 del 2a), **antes de 4.3**: reproducirlo con un bucle de shell de 100 corridas del archivo y anotar cuántas fallan y con qué (`"123"` en los metadatos); arreglar la causa. **Rojo**: el conteo previo, con comando y salida. **Verde**: 0 de 100 (con la tasa de 9% vista, 0 de 100 por azar tiene probabilidad menor a 1 en 10.000). Sin dependencias nuevas. Escenarios: ninguno (deuda de un test). Lecciones: L-003, L-007, L-019.
- [x] 4.2 Un cuelgue que se nombra (deuda V3-9 del 2a), junto con 4.3: las sesiones de `tests/integracion/test_tenant_por_transaccion.py:185-260` pasan a `with` o `try/finally` (hoy `sesion_1.close()` en 193, 210, 227 y 256, sobre un pool de 1), y `faulthandler_timeout` en la configuración de pytest (`pyproject.toml`; viene con pytest, sin dependencia nueva). **Rojo**: con una copia sin `registrar_reset_del_tenant_al_devolver`, hoy el archivo se cuelga; después falla en rojo nombrando el test en menos de un minuto. Escenarios: `integracion-continua` › Un test que se cuelga. Lecciones: L-013, L-019, L-020.
- [x] 4.3 CI (D5) en `tests/infra/test_ci_workflow.py`: el workflow se dispara con `push` a `main`, `workflow_dispatch` y `pull_request` (actualizar `test_disparadores_incluyen_push_a_main_y_workflow_dispatch`, línea 58, para que exija los tres); `timeout-minutes` en cada trabajo (`backend` 20, `humo` 15, el resto 5, con la medición de 1.1 citada en el informe); gitleaks **y** `shellcheck` con `@sha256:`, con el digest tomado del registro o del log de pull del CI (no de la copia local) y anotado junto al comando que lo obtuvo. Verlo fallar, implementar, verlo pasar. Escenarios: `integracion-continua` › Workflow revisado; › Push con todo correcto. Lecciones: L-005.

## 5. Humo

- [x] 5.1 Un respaldo por arranque (D6): contar los `.dump` antes y después de cada `up` y del `--una-vez`, y exigir exactamente uno nuevo en cada uno; renombrar el título del paso 11 ("aparece uno solo" ya es falso: con dos `up` hay dos `.dump`). **Rojo**: sobre una copia de `respaldar.sh` que hace dos ciclos por arranque, el paso falla. Escenarios: `integracion-continua` › Un respaldo por arranque. Lecciones: L-013, L-016.
- [x] 5.2 Doble congelada (D6): `pause db redis` a la vez; `/api/salud` 503 en menos de 2,5 s, exactamente dos `salud_degradada` con el `request_id`, `/salud-web` sin `sin_conexion`. Test en `tests/infra/test_humo.py` que exige que `limpiar` despause antes del `down -v`, visto en rojo con una copia que invierte el orden. Si "exactamente dos" flakea, se nombra como F6 (dueño 15) y no como regresión. Escenarios: `integracion-continua` › Base y Redis congelados; › Despausar antes de bajar. Lecciones: L-001, L-013, L-014.
- [x] 5.3 El proxy en el stack vivo (D1, D2, D6): GET y HEAD a `/` y `/api/salud`, GET a una ruta inexistente de la API y `GET /api/salud` con `api` detenida, por el proxy; las cabeceras de seguridad presentes, `Server`, `Via` y `X-Powered-By` ausentes, cada HEAD con las mismas cabeceras que su GET, el 502 sin `Server`. Además, `instance.uuid` de Caddy igual antes y después de `up -d --force-recreate caddy`. **Rojo**, antes de 3.1: hoy faltan las cabeceras, el 502 trae `Server: Caddy` y sin volumen el `instance.uuid` cambia. Escenarios: `integracion-continua` › Cabeceras en el stack vivo; `entorno-de-ejecucion` › Respuesta de la web y de la API; › Respuesta de error de la API; › Error del proxy; › Caddy recreado conserva sus datos. Lecciones: L-004, L-016.
- [x] 5.4 RLS habilitada en la base restaurada (deuda V3-15 del 2a, parte del humo): `relrowsecurity = t` además de `relforcerowsecurity` (`humo.sh:466-468`). **Rojo**: con una copia del dump restaurada con `DISABLE ROW LEVEL SECURITY` sobre `complejo`, hoy el paso pasa; después falla. Escenarios: `integracion-continua` › Restauración con RLS deshabilitada. Lecciones: L-013, L-018.

## 6. Arranque (deuda del 2a; regla de freno)

- [x] 6.0 El cableado real del arranque (deuda V3-5 del 2a, traída del 2b por la respuesta (a) a P1).
  Un test que arranca la API y el worker con su `lifespan` y su `on_startup` reales, sin `patch`, y
  exige que el reset del tenant al devolver una conexión (R7) esté registrado en el engine y que
  `verificar_rol_de_aplicacion_seguro` (R8) haya corrido. **Rojo**: con cada una de esas dos llamadas
  borrada a mano del arranque, el test falla nombrándola; hoy, borrarlas deja la suite en verde
  (informe de la vuelta 3, V3-5). Lecciones: L-016, L-019.
- [x] 6.1 La causa de un arranque rechazado (D10, deuda V2-5 del 2a). **Precondición: la 6.0 en verde.** Cuando `Configuracion()` o `verificar_rol_de_aplicacion_seguro` cortan el arranque, el log de `api` y el de `worker` (L-009) tienen una línea JSON con un evento propio de arranque fallido y la causa, sin valores secretos (L-007, con un marcador que pruebe que la contraseña no se repite). **Rojo**: con una copia de Compose donde `api` conecta con el rol de arranque, hoy `docker compose -p proptech logs api` no contiene la causa; después, sí, y el contenedor sigue sin arrancar. Escenarios: `entorno-de-ejecucion` › Arranque rechazado con causa nombrada. Lecciones: L-007, L-009, L-013, L-016.
- [x] 6.2 Nombre de rol desconocido (D11, deuda V3-14 del 2a): `roles antes` rechaza un `POSTGRES_APP_USER` distinto de `_ROL_DE_LA_APP` (`ayudas_rls.py:19`), nombrando la variable y sin mostrar valores. **Rojo**: con `POSTGRES_APP_USER=otra_app`, hoy `antes` pasa y falla más tarde con otro mensaje; después, `antes` sale con 1 y la causa. La restricción va a la fila de la tabla de 7.1. Escenarios: ninguno nuevo (la verificación es el rojo de esta tarea). Lecciones: L-002, L-007, L-016.

## 7. Documentación

- [x] 7.1 Una sola tabla de variables (D8): la tabla completa vive en el `README.md` de la raíz y `knowledge-base/08_arquitectura_propuesta.md` la reemplaza por un enlace (corrigiendo antes la fila de `POSTGRES_USER`, que hoy dice "compartido por los cuatro servicios"). Test en `tests/infra/test_readme_variables.py` en los dos sentidos contra la unión de `infra/.env.example` y los `${VAR}` de `compose.yaml`: falla si una variable falta en la tabla o si la tabla nombra una que no existe; verlo fallar antes (hoy faltan, entre otras, `FORWARDED_ALLOW_IPS` y `DB_POOL_*`). En el mismo pase, lo de V3-15 en el README: el worker sí tiene salida (`salida_worker`), el 1d no está "Propuesto" (`README.md:13-17`) y las cuatro contraseñas tienen que ser distintas. Escenarios: ninguno (documentación). Lecciones: L-005, L-016.

## 8. Rollback

- [x] 8.1 Rollback ejercitado (D9, F-2): con `git worktree` de `d0502fa` (sin tocar el árbol de trabajo), levantar con `-p proptech` y cargar datos (las dos administraciones del humo o la semilla); anotar `/api/salud` y conteos. Subir a la versión del 2c sobre esos mismos volúmenes: `/api/salud` 200 por el proxy y conteos iguales. Volver a `d0502fa` sobre los mismos volúmenes: `/api/salud` 200 y conteos iguales. Anotar comandos y salida, y reescribir el Migration Plan de `design.md` con los comandos exactos y el resultado. Bajar todo con `down -v` y `git worktree remove` al terminar. Escenarios: ninguno (procedimiento de operación). Lecciones: L-006, L-016.

## 9. Cierre

- [x] 9.1 **Después de la última vuelta de correcciones** (L-010): `bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh` y `bash infra/ci/humo.sh` **en ese orden y de a uno** (D7); anotar la cantidad de tests contra la línea de base de 1.1, con hora y commit. Después, el **clon limpio** (D7): `git clone` del commit final a un directorio temporal, los comandos del README tal cual (`cp`, `mkdir`, `up --build`), `/api/salud` 200 por el proxy y `down -v`; anotar comandos y salida. Repetir todo si el código cambia después. Escenarios: todos. Lecciones: L-003, L-005, L-010.

## Vuelta 2 — bloqueantes de la auditoría (rompedor + auditor, vuelta 1)

Veredicto del auditor: vuelve al constructor con 5 bloqueantes (C2-1, C2-2, C2-3, C2-4, C2-6).
Quedan como deuda con dueño 15, sin tocar: C2-5, C2-7, C2-8 y las notas. Pedido del auditor: arreglar
la familia, no el ejemplo (L-018, L-021). Cada rojo se pega acá antes del código.

- [x] C2-1 El valor de cada cabecera, no sólo su presencia (L-019). `Referrer-Policy` sirve
  `strict-origin-when-cross-origin`; la spec y D1 piden `no-referrer` (confirmado por Juani). Ningún
  test miraba valores: `X-Frame-Options: ALLOWALL` pasaba (M12 del rompedor).

  **Rojo (hoy, antes del código):**
  ```
  $ uv run pytest tests/infra/test_caddyfile_seguridad.py::test_el_caddyfile_fija_las_cuatro_cabeceras_de_seguridad_con_su_valor -q
  AssertionError: Referrer-Policy tiene el valor 'strict-origin-when-cross-origin', se esperaba 'no-referrer'
  1 failed in 0.05s
  ```
  Rojo repetido con un valor débil en las otras tres (copias, restauradas después de cada una):
  `X-Content-Type-Options: sniff`, `X-Frame-Options: ALLOWALL`, `Permissions-Policy` sin negar `camera`
  — las tres fallan nombrando la cabecera y el valor. **Verde**: `Referrer-Policy no-referrer` en el
  Caddyfile (sitio y `handle_errors`); `verificar_cabeceras` del humo exige valor, no sólo presencia.

- [x] C2-2 Toda respuesta que el proxy emite fuera del bloque del sitio (por IP, con `Host` ajeno, sin
  `Host`) sale con `Server: Caddy` y sin ninguna cabecera — la spec dice "toda respuesta servida por
  el proxy". Un sitio de respaldo cubre los tres casos; lo que Caddy arma antes de cualquier ruta (N1:
  400, 431, 505, `OPTIONS *`) queda enumerado en la spec como excepción, con su prueba.

  **Rojo (stack vivo, antes del código)**: `Host: evil.example`, por IP (`127.0.0.1`) y HTTP/1.0 sin
  `Host`, los tres `200 OK` con `Server: Caddy` y sin ninguna de las cuatro cabeceras. **Verde**: sitio
  de respaldo `:80 { header {...} respond 421 }` en el Caddyfile; los tres casos ahora `421` con las
  cuatro cabeceras y sin `Server`; el sitio real y el 502 siguen iguales (verificado). Nuevo paso 6c en
  el humo.

- [x] C2-3 El chequeo vivo de capacidades (3.4) no puede dar rojo en `redis` ni en `db`: lee el PID 1,
  y `redis` (`setpriv`) y `db` (`gosu`) bajan privilegios por su cuenta — el PID 1 no refleja lo que
  puso Compose. El chequeo pasa a leer un proceso nuevo (`compose exec`), que sí depende de Compose;
  se extiende a los ocho servicios (suma `migraciones`, con `compose run --no-deps` como la 3.3).
  Corregir también el comentario de `humo.sh` y de `test_compose.py` que dicen que `redis` baja con
  `gosu` o que su `CapBnd` de PID 1 es su lista.

  **Rojo (stack vivo, antes del código)**: con una copia de Compose sin `security_opt`/`cap_drop`/
  `cap_add` de `redis`, `/proc/1/status` sigue dando `CapBnd: 0` (el chequeo viejo pasaría igual);
  `/proc/self/status` de un `exec` nuevo da `0xa80425fb` (el default de Docker, no `0x1c0`). **Verde**:
  el chequeo lee `/proc/self/status` de un proceso nuevo en los ocho servicios; `redis` pasa a
  esperar `0x1c0` (su propio `cap_add`, no vacío). Comentarios de `humo.sh`, `design.md` y `spec.md`
  corregidos (redis usa `setpriv`, no `gosu`; el mecanismo de lectura cambia, no el de 3.3/PID1-uid).

- [x] C2-4 `relrowsecurity` se mira en 2 de las 6 tablas con políticas (sólo `administracion` y
  `complejo`); la spec pide "en las tablas con políticas". La lista de tablas sale de la BASE EN USO
  (o de las migraciones), nunca de la restaurada — si saliera de ahí, una tabla que perdió sus
  políticas en el dump dejaría de contarse como "con políticas" y pasaría igual.

  **Rojo (restauración real, antes del código)**: con `unidad` (ni `administracion` ni `complejo`) con
  `DISABLE ROW LEVEL SECURITY` en la restaurada, el chequeo viejo (2 tablas) pasa igual; con las
  políticas de `unidad` borradas en la restaurada (`relrowsecurity`/`relforcerowsecurity` siguen en
  `t`), el chequeo de sólo esas dos banderas también pasa igual. **Verde**: la lista de tablas sale de
  `select distinct tablename from pg_policies` contra la BASE EN USO (6 tablas); para cada una,
  `relrowsecurity`, `relforcerowsecurity` y el conteo de políticas, comparado contra la base en uso.
  Bug propio atrapado en el camino: un `while read` que corría varios `compose exec` adentro cortaba
  después de la primera tabla (competían por el mismo stdin); arreglado con `< /dev/null` en cada uno.

- [x] C2-6 El arreglo del flake V3-8 (tarea 4.1) comparaba sólo contra el campo `tarea`; una fuga por
  cualquier otro campo (`valor_recibido`, o el nuevo `causa`) pasa (M10 y M10b del rompedor). Hay que
  comparar contra TODO lo que de verdad sale al log (la línea que arma `FormateadorJSON`, o
  `__dict__` menos los atributos estándar de `LogRecord`), y repetir el lazo del flake 150+ veces para
  mostrar que no se reabre V3-8. El comentario de `logs.py` sobre `causa` tiene que decir qué impide
  hoy que OTRO logger lo use con un valor — y si nada lo impide, decirlo así.

  **Rojo (antes del código)**: con `extra={"tarea": ..., "valor_recibido": str(administracion_id)}`
  (M10) y con `extra={"tarea": ..., "causa": str(administracion_id)}` (M10b), el test viejo (sólo
  miraba `tarea`) sobrevivía a las dos. **Verde**: se compara contra todos los campos extra del
  registro (`__dict__` menos `_ATRIBUTOS_ESTANDAR` de `logs.py`, el mismo criterio que usa
  `FormateadorJSON`); las dos mutaciones ahora fallan, nombrando el campo. Flake V3-8: 0 fallas en 150
  corridas después del arreglo. Comentario de `causa` en `logs.py` reescrito: dice que nada en el
  código impide que otro logger la use con un valor, y que es un aviso, no una barrera.

Fuera de esta vuelta (deuda con dueño 15, no se tocan): C2-5 (línea/comando real del trap en
`compose()` y en los 17 `if !`), C2-7 (el conteo de `.dump` es una carrera en el segundo `up`), C2-8
(`arranque_fallido` sólo cubre `ConfiguracionInvalida`/`RolDeAplicacionInseguro`, no un `POSTGRES_HOST`
o una contraseña inválidos), y las notas N1 a N13.
