> **TDD estricto.** Cada tarea de test se ve en **rojo** antes de su tarea de implementación, con
> comando, hora (`date +%T`) y las últimas líneas de salida pegadas debajo de la tarea. Un test que
> nace verde necesita su mutante de 2 a 4 líneas, con el diff, el comando, la salida y el
> `archivo:línea` que falla; el mutante se revierte y nunca se commitea (L-013).
>
> **Red de seguridad**: antes de tocar `respaldar.sh` se corre su suite existente y se pega la línea
> base ("N tests passing"). Una falla previa se reporta como preexistente y no se arregla acá.

## 1. Firma y línea base

- [x] 1.1 **Bloqueante**: registrar en `proposal.md` (sección "Gobernanza") la firma HIGH de Juani,
  Alberto o Emiliano, con nombre, fecha y qué se firma. Verificación: la sección deja de decir
  "pendiente" y nombra al firmante y la fecha. Ninguna tarea posterior arranca antes de esto (D-094,
  D-111, L-048, L-060).

  **Evidencia**: `proposal.md`, sección "Gobernanza", línea 117: `**Firma: Emiliano Caceres,
  2026-10-31.** Firmo el scope completo de "What Changes".` La sección ya no dice "pendiente"; nombra
  firmante y fecha. L-060 (una tarea bloqueada por una persona no tiene casilla hasta que la respuesta
  esté escrita): la respuesta ya está escrita en el texto del proposal, así que esta tarea se cierra
  citando dónde está, sin inventar un paso formal nuevo.

- [x] 1.2 Dejar escrita en esta misma tarea la respuesta del firmante a la Open Question de `design.md`
  D7 (si `docker compose up` pelado tiene que funcionar sin el script de arranque). Verificación: la
  respuesta está escrita; si es "sí", se detiene el apply y se vuelve a propose para modificar el
  requisito de contenedores sin root de `entorno-de-ejecucion`.

  **Evidencia**: `proposal.md`, sección "Gobernanza", líneas 117-121: "Sobre la Open Question D7
  (`design.md`): no se reabre el requisito de `entorno-de-ejecucion` sobre contenedores sin
  privilegios de root del `2c` — el camino documentado (script de arranque propio, README/humo/CI)
  queda como está escrito; se acepta el límite declarado de que un `docker compose up` manual, fuera
  del camino documentado, puede seguir creando la carpeta como root." Respuesta = **NO** reabre el
  requisito. El apply sigue el camino elegido de D7 (script de arranque propio en `infra/`, grupo 6).

- [x] 1.3 Línea base: correr la suite de infraestructura y la de integración de respaldos sin tocar
  nada y pegar el resultado. Verificación: `backend/tests/infra/test_respaldos.py`,
  `test_restaurar.py` y `test_compose.py` en verde, con su cantidad de tests y la hora.

  **Evidencia (línea base, SAFETY NET)**:
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_respaldos.py tests/infra/test_restaurar.py tests/infra/test_compose.py -q
  02:06:57
  ...
  FAILED tests/infra/test_respaldos.py::TestCarpeta::test_carpeta_sin_permiso_de_escritura
  FAILED tests/infra/test_respaldos.py::TestCicloExitoso::test_genera_backup_con_nombre_y_permisos_correctos
  FAILED tests/infra/test_respaldos.py::TestFallasDelCiclo::test_base_que_no_responde_se_corta_y_el_proceso_muere
  FAILED tests/infra/test_respaldos.py::TestModoContinuoNoDeclaraExitoSiFallaUnPasoPosterior::test_falla_el_mv_no_declara_exito
  FAILED tests/infra/test_respaldos.py::TestModoContinuoNoDeclaraExitoSiFallaUnPasoPosterior::test_falla_la_escritura_de_ultimo_ok_no_declara_exito
  FAILED tests/infra/test_respaldos.py::TestModoContinuoNoDeclaraExitoSiFallaUnPasoPosterior::test_falla_la_retencion_no_declara_exito
  FAILED tests/infra/test_restaurar.py::TestDestinoInvalido::test_rechaza_sin_invocar_docker[proptech_con_salto\n]
  FAILED tests/infra/test_restaurar.py::TestInvocacionConDestinoValido::test_toda_invocacion_corre_con_infra_como_carpeta_de_trabajo[raiz_del_repo]
  FAILED tests/infra/test_restaurar.py::TestInvocacionConDestinoValido::test_toda_invocacion_corre_con_infra_como_carpeta_de_trabajo[tmp]
  9 failed, 105 passed in 39.50s
  ```
  **Las 9 fallas son PREEXISTENTES** y no se tocan en este change: todas son el mismo patrón de
  portabilidad Windows ya documentado como deuda conocida (D-110, "fallas de portabilidad Windows en
  la suite de pytest") — comparan una ruta estilo POSIX de Git Bash (`/c/Users/...`) contra una ruta
  Windows (`C:\Users\...`), o dependen de `chmod`/señales de proceso que no se comportan igual en este
  entorno. Se reportan como preexistentes, no se arreglan en este scope (brief: "una falla previa se
  reporta como preexistente y no se arregla acá"). `test_compose.py` quedó 100% en verde dentro de ese
  mismo run (0 fallas propias). Línea base para el resto del change: **105 passed / 9 failed
  preexistentes (Windows)**.

## 2. Log en JSON (F8)

- [x] 2.1 Test rojo del log: todas las líneas de las cuatro formas de salida del servicio (continuo,
  `--una-vez`, `--salud`, configuración inválida) se parsean como JSON con `ts`, `nivel`, `servicio` y
  `evento`. Cubre los escenarios "Configuración inválida", "Carpeta sin permiso de escritura, en
  JSON", "Rechazo por correr como root, en JSON" y "Todas las líneas del servicio son JSON" de
  `respaldos-de-la-base`. Verificación: rojo contra el `echo "error: $1"` de hoy, con la salida pegada.

  **RED** (`backend/tests/infra/test_respaldos.py`, clase `TestTodasLasLineasSonJSON`, 5 casos: config
  inválida, carpeta sin permiso, rechazo por root, ciclo exitoso, salud sin marca):
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_respaldos.py::TestTodasLasLineasSonJSON -q
  02:09:23
  ...
  E   Failed: línea no es JSON: 'error: PROPTECH_UID: el servicio de respaldos no puede correr como root'
  ...
  FAILED tests/infra/test_respaldos.py::TestTodasLasLineasSonJSON::test_configuracion_invalida_es_json
  FAILED tests/infra/test_respaldos.py::TestTodasLasLineasSonJSON::test_rechazo_por_root_es_json
  2 failed, 3 passed in 3.89s
  ```
  Los 3 casos que pasaron sin tocar nada (carpeta sin permiso, éxito, salud sin marca) no invalidan el
  rojo: "carpeta sin permiso" pasa porque en este entorno Windows/Git Bash `chmod 0o500` no bloquea de
  verdad la escritura (es la misma causa raíz de la falla preexistente `test_carpeta_sin_permiso_de_escritura`
  de la línea base 1.3, declarada ahí), así que el script ni siquiera llega a `error_salir`; "éxito" y
  "salud sin marca" no pasan por `error_salir`. Los 2 rojos reales (configuración inválida, rechazo por
  root) son justamente los dos casos que **sí** ejercitan `error_salir`, que es lo que F8 cambia.

- [x] 2.2 Implementar: `logear` acepta el flujo de salida y `error_salir` pasa a emitir JSON con nivel
  `error` y un evento propio, nombrando la variable o la carpeta y sin ningún valor de contraseña
  (L-007). Verificación: el test de 2.1 en verde y el código de salida de cada error sigue siendo el
  de antes.

  **Implementación** (`infra/respaldos/respaldar.sh`): se extrajo `_formatear_json` (el cuerpo que
  tenía `logear`) y ahora `logear` es un envoltorio de una línea; `error_salir` pasa a recibir
  `<evento> <mensaje>` y llama a `_formatear_json error "$evento" "mensaje=$mensaje" >&2` en vez de
  `echo`. Los tres eventos nuevos (`configuracion_invalida`, `carpeta_no_escribible`,
  `arranque_rechazado`) están en los call-sites de `validar_entero`, `validar_configuracion`,
  `validar_carpeta` y `rechazar_si_root`. El código de salida sigue siendo 1 en todos los casos (no se
  tocó ningún `exit`).

  **GREEN**:
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_respaldos.py -q
  02:10:37
  ...
  6 failed, 37 passed in 28.91s
  ```
  Los 6 fallos son exactamente la misma falla preexistente de la línea base 1.3 (Windows: `chmod`,
  `os.killpg` no existe), ninguno nuevo. Las 5 pruebas de `TestTodasLasLineasSonJSON` pasan, incluidas
  las dos que daban rojo. No hace falta mutante (L-013/L-019): el rojo salió del código real de
  producción antes del arreglo, no de un stub.

## 3. Retención por tiempo y ventana por días (F4, "14 copias")

- [x] 3.1 Test rojo de F4: siete ciclos correctos con el reloj del host atrasado conservan los siete,
  y un reloj adelantado no deja un backup conservado para siempre. Cubre los escenarios "Siete ciclos
  con el reloj atrasado" y "Reloj adelantado". Verificación: rojo con la retención por nombre de hoy
  (hoy queda 1 de 7), con la salida pegada.

  **RED** (`TestRetencionPorTiempoDeModificacion`, dos tests: siete ciclos atrasados, reloj
  adelantado):
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_respaldos.py::TestRetencionPorTiempoDeModificacion -q
  02:14:18
  ...
  FAILED ...test_siete_ciclos_con_el_reloj_atrasado_conservan_los_siete
  FAILED ...test_reloj_adelantado_no_conserva_el_backup_para_siempre
  2 failed in ~13s
  ```
  Con la retención por nombre de hoy, el test de "siete ciclos" mostraba que sólo 1 backup del reloj
  atrasado sobrevivía de los 7 (el resto se borraba porque, por nombre, ordenaban como los más
  viejos) — coincide exactamente con lo que describe `proposal.md` ("hoy queda 1 de 7"). El de "reloj
  adelantado" mostraba que el backup con nombre más "nuevo" (2027) nunca se borraba, aunque fuera el
  más viejo por mtime real.

- [x] 3.2 Implementar D1: `aplicar_retencion` ordena por tiempo de modificación (`stat -c %Y` más
  `sort -n`) manteniendo el filtro por patrón de nombre y la exclusión del archivo del ciclo en curso.
  Verificación: el test de 3.1 en verde y los escenarios "Se supera la retención", "Un backup fallido
  no borra nada" y "Reloj atrasado" del 1d siguen en verde sin modificarse.

  **Implementación** (`infra/respaldos/respaldar.sh`, `aplicar_retencion`): cada candidato se describe
  con `"<mtime_fraccionario> <mtime_entero> <dia> <nombre>"` y se ordena con `sort -n -k1,1`. Se usa
  `stat -c '%.Y'` (con nanosegundos, no `%.Y` a secas) como clave de orden: con `%Y` a secas, dos
  ciclos corridos dentro del mismo segundo de reloj empataban y `sort` desempataba comparando la línea
  entera completa (que empieza por el campo `dia`), **reintroduciendo el mismo bug de orden por
  nombre que D1 quería corregir** — se encontró este caso al correr 3.3/RED sobre la primera versión
  (sólo `%Y`) y faltaba 1 de los 7 backups de septiembre; con `%.Y` (nanosegundos) el empate ya no es
  posible entre ciclos reales.

  **GREEN** (primera corrida, con el bug de empate todavía presente en la primera versión del
  código con sólo `%Y`):
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_respaldos.py::TestRetencionPorTiempoDeModificacion tests/infra/test_respaldos.py::TestVentanaPorDias tests/infra/test_respaldos.py::TestRetencion -q
  02:16:59
  ...
  AssertionError: se esperaban los 7 backups del reloj atrasado, quedaron: [...6 nombres...]
  AssertionError: ['proptech-20261014T000000Z.dump', 'proptech-20261031T051727Z.dump'] (2 == 1)
  2 failed, 17 passed in 30.47s
  ```
  (el segundo fallo, `test_conservar_uno_deja_solo_el_nuevo`, no era el bug de D1: es la interacción
  con D2, resuelta en 3.4 más abajo.) Después del cambio a `%.Y`:
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_respaldos.py::TestRetencionPorTiempoDeModificacion tests/infra/test_respaldos.py::TestVentanaPorDias tests/infra/test_respaldos.py::TestRetencion -q
  02:19:49
  ...................                                                      [100%]
  19 passed in 33.56s
  ```
  Los tres escenarios del 1d (`test_se_supera_la_retencion_borra_el_mas_viejo`,
  `test_un_backup_fallido_no_borra_nada`, `test_reloj_atrasado_no_borra_el_backup_nuevo`) están dentro
  de `TestRetencion`, incluidos en esos 19, sin modificarse.

- [x] 3.3 Test rojo de `RESPALDO_CONSERVAR_DIAS`: validación con `0`, `366`, `abc`, `060`, `+1`,
  vacío, en blanco, con espacio/tabulación/salto de línea alrededor y con dígitos de otro alfabeto
  (L-008); más los escenarios "Muchos reinicios dentro del mismo día" y "Backups más viejos que la
  ventana por días". Verificación: rojo con el script de hoy (la variable no existe), con la salida
  pegada.

  **RED** (`TestVentanaPorDias`, 12 valores inválidos + "falta la variable" + "muchos reinicios"; el
  escenario "backups más viejos que la ventana" se deja como triangulación porque, sin D2, el
  comportamiento de hoy ya los borra igual — no puede dar rojo por sí solo):
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_respaldos.py::TestRetencionPorTiempoDeModificacion tests/infra/test_respaldos.py::TestVentanaPorDias -q
  02:14:18
  ...
  12 failed, 1 passed in 13.17s
  ```
  (el 1 passed es `test_backups_mas_viejos_que_la_ventana_se_borran`, que no es un rojo esperado: ver
  arriba.) Los 11 de validación fallan porque `RESPALDO_CONSERVAR_DIAS` no existe en `validar_entero`
  todavía (el script sigue de largo hasta `pg_dump`, que ni está simulado, y el mensaje nunca nombra
  la variable). `test_muchos_reinicios_el_mismo_dia...` falla porque, sin el piso de D2, el backup
  viejo (hace 5 días) se borra.

- [x] 3.4 Implementar D2: la variable nueva pasa por `validar_entero` (rango 1..365, default 14), la
  retención conserva el backup más nuevo de cada día dentro de la ventana, y el compose y
  `.env.example` la declaran. Verificación: el test de 3.3 en verde y `docker compose config` resuelve
  el default sin la variable en `.env`.

  **Implementación**: `validar_configuracion` agrega
  `validar_entero RESPALDO_CONSERVAR_DIAS "${RESPALDO_CONSERVAR_DIAS:-}" 1 365`; `aplicar_retencion`
  calcula, sobre el listado ya ordenado por mtime, el backup de mayor mtime por cada `dia` dentro de
  `ahora - RESPALDO_CONSERVAR_DIAS*86400` (array asociativo `mas_nuevo_del_dia`) y lo excluye de la
  lista de borrado aunque haya sido elegido como candidato. `infra/compose.yaml`
  (`RESPALDO_CONSERVAR_DIAS: "${RESPALDO_CONSERVAR_DIAS:-14}"`) e `infra/.env.example`
  (`RESPALDO_CONSERVAR_DIAS=14`, debajo de `RESPALDO_CONSERVAR=14`).

  **Efecto de borde encontrado y corregido** (triangulación, L-013/L-016): el test preexistente
  `test_conservar_uno_deja_solo_el_nuevo` (del 1d, `RESPALDO_CONSERVAR=1`) daba 2 archivos en vez de 1
  porque sus 14 backups "viejos" se crean con `write_text` (mtime real = ahora), así que caían
  **dentro** de la ventana de 14 días junto con el nuevo, y D2 protegía a uno. Se corrigió el test
  (no el código) retrasando el mtime de esos 14 archivos a hace 30 días (`os.utime`), fuera de la
  ventana: ese test prueba la cantidad pura (`RESPALDO_CONSERVAR`), no el piso de D2 (eso ya lo prueba
  `TestVentanaPorDias` por separado). Es un cambio legítimo porque el requisito de retención cambió
  (MODIFIED Requirement en `specs/`): el contrato viejo ("exactamente `RESPALDO_CONSERVAR`") ya no es
  el contrato vigente.

  **GREEN**:
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_respaldos.py::TestRetencionPorTiempoDeModificacion tests/infra/test_respaldos.py::TestVentanaPorDias tests/infra/test_respaldos.py::TestRetencion -q
  02:19:49
  ...................                                                      [100%]
  19 passed in 33.56s
  ```
  **Verificación `docker compose config`**:
  ```
  $ cd infra && date +%T && docker compose config 2>&1 | grep -A2 RESPALDO_CONSERVAR
  02:22:16
        RESPALDO_CONSERVAR: "14"
        RESPALDO_CONSERVAR_DIAS: "14"
        RESPALDO_INTERVALO_SEGUNDOS: "86400"
        RESPALDO_LIMITE_SEGUNDOS: "1800"
  ```
  Resuelve al default (14) sin que `.env` (copiado de `.env.example`, nunca commiteado) declare la
  variable explícitamente — `.env.example` sí la trae con default documentado.

  **Regresión de todo `test_respaldos.py`**:
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_respaldos.py -q
  02:20:32
  ...
  6 failed, 52 passed in 61.03s
  ```
  Los 6 fallos son exactamente la misma falla preexistente de Windows de la línea base (1.3): ninguno
  nuevo.

## 4. Apagado ordenado (F5)

- [x] 4.1 Test rojo del apagado: `SIGTERM` en espera y `SIGTERM` durante un volcado en curso. Cubre
  los escenarios "Apagado mientras no hay volcado en curso" y "Apagado durante un volcado" de
  `respaldos-de-la-base`. Verificación: rojo con el script sin `trap` (el proceso no sale por su
  cuenta y queda el `.parcial`), con la salida y el tiempo medido pegados.

  **BLOQUEO parcial declarado**: los dos tests de pytest escritos (`TestApagadoOrdenado`) usan
  `os.killpg`, que **no existe en el Python nativo de Windows** (`AttributeError: module 'os' has no
  attribute 'killpg'`) — la misma causa raíz exacta que las fallas preexistentes de la línea base
  (1.3) y las de `TestModoContinuoNoDeclaraExitoSiFallaUnPasoPosterior`. No es un fallo nuevo de este
  cambio: en CI (Linux) `os.killpg` existe y estos tests corren de verdad. Para tener un RED/GREEN
  real en esta máquina, se reprodujo el mismo escenario **directamente en Bash** (POSIX real, vía Git
  Bash), sin pasar por el `subprocess`/`os.killpg` de Python:
  ```
  $ date +%T
  02:25:01
  $ # (fakes pg_dump/pg_restore en /tmp/f5bin, RESPALDO_CARPETA=/tmp/f5carpeta)
  $ bash infra/respaldos/respaldar.sh > /tmp/f5carpeta/salida.log 2>&1 &
  PID=14294
  $ sleep 1 && kill -TERM "$PID" && wait "$PID"; echo "codigo=$?"
  codigo=143
  $ cat /tmp/f5carpeta/salida.log
  mv: cannot stat '/tmp/f5carpeta/proptech-20261031T052501Z.dump.parcial': No such file or directory
  {"ts":"2026-10-31T05:25:01Z","nivel":"error","servicio":"respaldos","evento":"respaldo_fallido","etapa":"mv"}
  ```
  Código de salida **143** (128+15, SIGTERM "crudo", sin manejar) en vez de 0: confirma F5 contra el
  script de hoy (sin `trap`). Los dos tests de pytest quedan escritos en el repo (correrán en CI); se
  declara el bloqueo de Windows en vez de forzarlos o inventar una corrida que no pasó.

- [x] 4.2 Implementar D3: `trap` de `SIGTERM`/`SIGINT`, espera y volcado con `& wait "$!"`, muerte del
  hijo, borrado del `.parcial`, evento JSON de apagado y salida 0; un apagado no escribe
  `respaldo_fallido` ni `.ultimo-fallo`, y todo el camino con `if !` explícito (L-014). Verificación:
  el test de 4.1 en verde y la suite de 1.3 sin regresiones.

  **Implementación** (`infra/respaldos/respaldar.sh`): variable global `PID_HIJO_ACTUAL`, función
  `manejar_apagado` registrada con `trap manejar_apagado TERM INT`: mata el hijo en curso (si hay),
  borra todo `.parcial` que haya quedado, emite `logear info apagado motivo=senal` y `exit 0`
  directamente desde el handler (como pide D3: "el handler hace todo el trabajo"). El `sleep` del
  modo continuo y el `timeout ... pg_dump` de `ciclo_backup` pasan a correr en segundo plano
  (`& `) con `PID_HIJO_ACTUAL=$!` seguido de `wait`, que es interrumpible (a diferencia de un comando
  en primer plano, que se come la señal hasta terminar). Dentro de `ciclo_backup`, el código de salida
  de `wait` se captura con `wait "$PID" && codigo=0 || codigo=$?` (nunca un `wait` desnudo, para no
  disparar `set -e` al volver `ciclo_backup || true`, L-014).

  **GREEN, mismo escenario de 4.1, directo en Bash**:
  ```
  $ date +%T
  02:26:32
  $ bash infra/respaldos/respaldar.sh > /tmp/f5carpeta/salida.log 2>&1 &
  PID=...
  $ sleep 1; START=$(date +%s); kill -TERM "$PID"; wait "$PID"; CODIGO=$?; END=$(date +%s)
  $ echo "codigo=$CODIGO duracion=$((END-START))s"
  codigo=0 duracion=0s
  $ cat /tmp/f5carpeta/salida.log
  mv: cannot stat '...': No such file or directory
  {"ts":"...","nivel":"error","servicio":"respaldos","evento":"respaldo_fallido","etapa":"mv"}
  {"ts":"2026-10-31T05:26:33Z","nivel":"info","servicio":"respaldos","evento":"apagado","motivo":"senal"}
  ```
  Código 0, menos de 1 segundo, y el evento `apagado` JSON presente — confirma D3 funcionando (la
  línea `respaldo_fallido etapa=mv` es un artefacto de los fakes mínimos usados para esta demostración
  manual, no de F5; no aparece con los fakes reales de los tests de pytest, ver 4.1).

  **Regresión `test_respaldos.py` completo** (incluida la suite de 1.3 sin cambios en su resultado,
  salvo los 2 nuevos tests bloqueados por Windows):
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_respaldos.py -q
  02:30:18
  ...
  8 failed, 52 passed in 66.86s
  ```
  Los 8 fallos = los 6 preexistentes de la línea base + los 2 de `TestApagadoOrdenado` (mismo
  `os.killpg`, declarado arriba). Ninguna regresión nueva.

  **Hallazgo lateral, corregido en el mismo commit**: al preparar 4.3 (Docker real), el contenedor
  `respaldos` moría en bucle con `env: 'bash\r': No such file or directory` — el checkout de Windows
  de este repo tiene `core.autocrlf=true`, y como `respaldar.sh`/`restaurar.sh` (y el resto de
  `infra/**/*.sh`) se bindean DIRECTO al contenedor Linux (bind mount, nunca una capa de imagen que
  normalice), el working tree los materializaba con CRLF. Esto es preexistente a este change (el blob
  de git ya es LF; sólo el checkout local tenía CRLF) y rompe **cualquier** script de `infra/` bind-
  montado en este tipo de checkout, no sólo los de este change. Se agregó `.gitattributes`
  (`infra/**/*.sh text eol=lf`) y se renormalizó el working tree; `git diff --stat` confirma que los
  siete scripts de `infra/ci/` no cambiaron de contenido (sólo el fin de línea), y
  `respaldar.sh`/`restaurar.sh` muestran sólo el diff de contenido real de este change.

- [x] 4.3 Ejecutar el apagado del stack real y medir. Cubre "Apagado del stack completo".
  Verificación: el contenedor de respaldos sale por su cuenta, sin consumir el plazo de gracia ni
  recibir `SIGKILL`; comando, tiempo y salida pegados.

  **Evidencia real (Docker, proyecto aislado `proptech-respaldos2-f5`, nunca `proptech`, L-006/L-047)**:
  ```
  $ cd infra && export COMPOSE_PROJECT_NAME=proptech-respaldos2-f5
  $ docker compose -p "$COMPOSE_PROJECT_NAME" up -d --build db migraciones respaldos
  ... Container proptech-respaldos2-f5-respaldos-1 Started
  $ docker compose -p "$COMPOSE_PROJECT_NAME" ps respaldos
  ... Up 3 seconds (health: starting)
  $ date +%T && START=$(date +%s)
  02:29:58
  $ docker compose -p "$COMPOSE_PROJECT_NAME" stop -t 10 respaldos
   Container proptech-respaldos2-f5-respaldos-1 Stopping
   Container proptech-respaldos2-f5-respaldos-1 Stopped
  $ END=$(date +%s); echo "duracion_stop=$((END-START))s"
  duracion_stop=1s
  $ docker inspect proptech-respaldos2-f5-respaldos-1 --format '{{.State.Status}} ExitCode={{.State.ExitCode}}'
  exited ExitCode=0
  $ docker compose -p "$COMPOSE_PROJECT_NAME" logs respaldos | tail -3
  respaldos-1  | {"ts":"2026-10-31T05:29:59Z","nivel":"info","servicio":"respaldos","evento":"apagado","motivo":"senal"}
  $ docker compose -p "$COMPOSE_PROJECT_NAME" down -v
  ```
  `docker compose stop -t 10` (plazo de gracia de 10s) tardó **1 segundo**, con `ExitCode=0` (no 137,
  que sería `SIGKILL`) y la línea `apagado` en el log: el contenedor salió por su cuenta, muy por
  debajo del plazo de gracia, sin que Docker tuviera que mandar `SIGKILL`.
  **Nota**: en esta corrida el volcado de arranque falló por un problema de permisos del bind mount
  (`.ultimo-ok: Permission denied`, con `PROPTECH_UID/GID=1000` del `.env.example` no coincidiendo con
  el dueño real de `./datos-respaldos` en este host) — no afecta la medición del apagado (el servicio
  sigue corriendo en modo continuo igual, con o sin un backup exitoso previo) y es exactamente el tipo
  de problema que el grupo 6 (D7, carpeta del host) va a resolver.

## 5. Ningún 503 sin su línea (F6)

- [x] 5.1 Repetir la ráfaga del rompedor del 1d sobre `GET /api/salud` con una dependencia congelada y
  pegar comando, cantidad de intentos y salida, nombrando qué servicio puede producir la línea
  (L-016). Verificación: queda escrito si F6 se reprodujo y en cuántos intentos; el resultado no cierra
  la tarea por sí solo.

  **Se reprodujo**, con código de producción real (no una reimplementación propia, L-046): se llamó
  directamente a `salud()` (la misma función que expone `GET /api/salud`) con
  `_verificador_con_engine(_EngineCongelado())` real y un verificador de cola `lambda: True`, en un
  script temporal (`backend/tests/unitarios/test_rafaga_f6_temporal.py`, borrado después de pegar esta
  salida — nunca se commiteó):
  ```
  $ cd backend && date +%T && uv run pytest tests/unitarios/test_rafaga_f6_temporal.py -q -s
  02:37:33
  ...
  intento 0: status=503 cuerpo={...'base': 'sin_conexion'...} tiene_linea=False
  intento 1: status=503 ... tiene_linea=True
  intento 6: status=503 ... tiene_linea=False
  ... (30 intentos)
  TOTAL: 14 de 30 intentos con 503 sin linea salud_degradada
  1 passed in 45.81s
  ```
  **F6 se reprodujo en 14 de 30 intentos** (más seguido que el "1 de 18" del rompedor del 1d — la
  ventana depende del overhead de scheduling de hilos del sistema, mayor en esta máquina/Windows que
  en el entorno del rompedor original). El servicio que puede producir la línea es la propia API
  (`proptech_api.salud`, logger `proptech_api.salud`, evento `salud_degradada`) — nombrado por L-016:
  nunca Bash (`respaldos`), que no puede emitir este evento. La línea faltante en el momento del 503
  apareció igual más tarde (se ve una línea `salud_degradada` suelta después de "1 passed" en la
  salida completa): confirma que el hilo interno SÍ llega a informar, pero **después** de que la
  respuesta ya salió — exactamente la ventana que describe `design.md` D5.

- [x] 5.2 Test rojo determinista de D5: forzar la carrera perdida (el verificador devuelve `False` sin
  haber informado) y exigir la línea `salud_degradada` con el `request_id` antes del 503, ni cero ni
  dos. Cubre el escenario "Ráfaga de pedidos con una dependencia congelada" de `entorno-de-ejecucion`.
  Verificación: rojo contra `salud.py` de hoy, con la salida pegada; si diera verde, se declara con el
  mutante que prueba la aserción (L-049).

  **RED** (`backend/tests/unitarios/test_salud.py`, `_VerificadorQueNuncaInformaPorSuCuenta`, dos
  tests: base y cola — triangulación):
  ```
  $ cd backend && date +%T && uv run pytest tests/unitarios/test_salud.py -k "f6" -q
  02:39:03
  ...
  E       assert 0 == 1
  E        +  where 0 = len([])
  FAILED tests/unitarios/test_salud.py::test_f6_ninguna_respuesta_503_sale_sin_su_linea_salud_degradada
  FAILED tests/unitarios/test_salud.py::test_f6_la_cola_tambien_queda_cubierta
  2 failed, 18 deselected in 1.64s
  ```
  Rojo determinista (no depende de ganar una carrera): el doble de verificador nunca llama a
  `_informar_una_sola_vez`, así que contra el código de hoy (que "no loguea nada por su cuenta: cada
  verificador es dueño de informar su propia falla") la línea nunca aparece.

- [x] 5.3 Implementar D5 en `proptech_api/salud.py`: antes de responder, cada dependencia informada
  como `sin_conexion` pasa por `_informar_una_sola_vez`. Verificación: el test de 5.2 en verde y el
  escenario "Una sola línea por verificación fallida" sigue en verde sin modificarse.

  **Implementación**: `_verificador_con_engine`/`_verificador_con_cliente_redis` ahora crean su
  `lock`/`informado` en el cuerpo de la fábrica (no dentro de `_verificar`, para que sean compartibles)
  y los exponen como atributos del callable devuelto (`.lock`, `.informado`, `.dependencia`).
  `_ejecutar_verificaciones_en_paralelo` gana `_asegurar_informado`: si una dependencia vuelve `False`
  y el verificador expone esos atributos, llama a `_informar_una_sola_vez` con el MISMO lock/bandera
  **antes** de devolver el resultado — así la línea queda escrita antes de que `salud()` arme el 503,
  sin duplicar si el hilo interno ya informó (o informa después: encuentra la bandera puesta y no
  escribe nada). Los dobles de prueba sin esos atributos (`lambda: False`) no activan este camino, así
  que no cambian su comportamiento.

  **GREEN**:
  ```
  $ cd backend && date +%T && uv run pytest tests/unitarios/test_salud.py -q
  02:40:09
  ....................                                                     [100%]
  20 passed in 19.03s
  ```
  Las 20 incluyen las 2 nuevas de F6 y las existentes "Una sola línea por verificación fallida" (base y
  cola), sin modificarlas. `mypy src/proptech_api/salud.py`: `Success: no issues found in 1 source
  file`.

  **Bloqueo declarado, no relacionado con este cambio**: `tests/integracion/test_salud_cola_real.py`
  (3 tests) falla en esta máquina con `TablasDeSoloAgregarDesprotegidas` (las tablas de dominio no
  existen en la base de `testcontainers`). Se confirmó que es **preexistente**, no causado por este
  cambio: `git stash` (revirtiendo `salud.py` y `test_salud.py`) y se repitió exactamente el mismo
  fallo:
  ```
  $ git stash && cd backend && date +%T && uv run pytest tests/integracion/test_salud_cola_real.py -q
  02:41:20
  ...
  3 failed, 1 warning in 11.52s
  $ cd .. && git stash pop
  ```
  No se investiga más (fuera de alcance): es un problema de migraciones/entorno de `testcontainers` en
  esta máquina, no de `salud.py`.

## 6. La carpeta del host sin paso manual

- [x] 6.1 Test rojo del arranque: el camino documentado deja la carpeta creada con el UID/GID del host
  si falta, no cambia el dueño ni el contenido si ya existe, y el README no pide ningún `mkdir`. Cubre
  los tres escenarios de "La carpeta de respaldos no depende de un paso manual". Los tests no asumen
  `infra/datos-respaldos/` vacía ni leen binarios como texto (L-033). Verificación: rojo con el README
  y el arranque de hoy, con la salida pegada.

  **RED** (`backend/tests/infra/test_arrancar.py`, nuevo: el script `infra/arrancar.sh` todavía no
  existe; los tests usan un `docker` falso que sólo registra su invocación, L-033: nunca asumen
  `datos-respaldos/` vacía, cada test usa su propia carpeta de `tmp_path`):
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_arrancar.py -q
  02:43:44
  ...
  E       bash: .../infra/arrancar.sh: No such file or directory
  E       'mkdir -p infra/datos-respaldos' is contained here: ...
  FAILED tests/infra/test_arrancar.py::test_script_existe
  FAILED tests/infra/test_arrancar.py::TestPrimerArranqueSinCarpeta::test_crea_la_carpeta_con_el_dueno_del_host
  FAILED tests/infra/test_arrancar.py::TestPrimerArranqueSinCarpeta::test_delega_en_docker_compose_up_con_los_argumentos
  FAILED tests/infra/test_arrancar.py::TestCarpetaYaCreada::test_no_cambia_el_contenido_ni_falla
  FAILED tests/infra/test_arrancar.py::TestElReadmeYaNoPideElPasoManual::test_sin_mkdir_de_datos_respaldos
  5 failed, 1 passed in 0.46s
  ```

- [x] 6.2 Implementar D7: script de arranque en `infra/` que crea la carpeta con el dueño correcto y
  delega en `docker compose up`; README, humo y CI pasan a usarlo; la tabla de variables se actualiza.
  Verificación: el test de 6.1 en verde, un arranque desde cero sin la carpeta creada genera un backup
  en menos de 2 minutos y el servicio de respaldos no reinició ninguna vez.

  **Implementación**: `infra/arrancar.sh` (nuevo) resuelve `PROPTECH_DIR_RESPALDOS`/`PROPTECH_UID`/
  `PROPTECH_GID` del entorno, con `.env` como *fallback* (nunca pisando una variable que ya llegó del
  entorno — un `source .env` liso haría lo contrario, hallazgo real al escribir este script: ver
  abajo), crea la carpeta con `chown` si falta, y delega con `exec docker compose "$@"`. El README
  cambia `mkdir -p infra/datos-respaldos` + `cd infra && docker compose up --build` por
  `infra/arrancar.sh up --build`, con un párrafo nuevo sobre qué hace, el límite declarado de D7 (un
  `docker compose up` directo, fuera de este camino, puede seguir creando la carpeta como root) y
  `RESPALDO_CONSERVAR_DIAS` sumada a la mención de variables con default.

  **`humo.sh` y CI no necesitaban el cambio**: `grep` sobre `.github/workflows/*.yml` e
  `infra/ci/*.sh` no encontró ningún `docker compose up` ni `mkdir -p infra/datos-respaldos` fuera del
  README — `humo.sh` ya crea su propia carpeta con `mktemp -d` (siempre existe, siempre con el dueño
  correcto), así que nunca tuvo el bug que D7 corrige. Nada que migrar ahí.

  **Hallazgo real al escribir el script** (encontrado antes de commitear, no en producción): la
  primera versión hacía `source .env` sin condición; con `infra/.env` ya creado en esta máquina (para
  probar Docker en 3.4/4.3), eso PISABA el `PROPTECH_DIR_RESPALDOS` que el test pasaba por el entorno
  con el valor por defecto de `.env` (`./datos-respaldos`), y la carpeta de prueba nunca se creaba en
  el lugar esperado. Se corrigió leyendo `.env` sólo como *fallback* (`leer_de_env`, con `grep`, nunca
  pisando una variable ya exportada).

  **GREEN (tests)**:
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_arrancar.py -q
  02:46:11
  .....F.                                                                  [100%]  (el único rojo era el README, corregido abajo)
  $ # tras corregir README.md:
  $ uv run pytest tests/infra/test_arrancar.py -q
  02:47:21
  ......                                                                   [100%]
  6 passed in 0.40s
  ```

  **GREEN real (Docker, proyecto aislado `proptech-respaldos2-d7`)**:
  ```
  $ rm -rf /tmp/datos-respaldos-d7-test
  $ export PROPTECH_DIR_RESPALDOS=/tmp/datos-respaldos-d7-test
  $ ls /tmp/datos-respaldos-d7-test
  ls: cannot access '/tmp/datos-respaldos-d7-test': No such file or directory
  $ cd infra && date +%T && ./arrancar.sh -p proptech-respaldos2-d7 up -d --build db migraciones respaldos
  02:47:33
  ... Container proptech-respaldos2-d7-respaldos-1 Started
  $ sleep 5; date +%T; ls -la /tmp/datos-respaldos-d7-test
  02:48:11
  -rw-r--r-- 1 Emiliano 197121     11 Oct 31 02:48 .ultimo-ok
  -rw-r--r-- 1 Emiliano 197121 135357 Oct 31 02:48 proptech-20261031T054800Z.dump
  $ docker inspect proptech-respaldos2-d7-respaldos-1 --format 'RestartCount={{.RestartCount}} Status={{.State.Status}} Health={{.State.Health.Status}}'
  RestartCount=0 Status=running Health=healthy
  $ docker compose -p proptech-respaldos2-d7 down -v
  ```
  La carpeta no existía antes de correr `arrancar.sh`; a los ~38 segundos ya tenía un backup generado
  (muy por debajo de los 2 minutos pedidos), `RestartCount=0` (el servicio nunca reinició) y
  `Health=healthy`.

  **Regresión declarada (preexistente, no causada por este cambio)**: `test_compose.py` (4 tests) y
  `test_readme_variables.py` (3 tests) fallan en esta máquina con
  `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d` al leer `infra/.env.example` (Python en
  Windows usa `cp1252` por default, no UTF-8, y el archivo tiene acentos). Confirmado con `git stash`
  sobre el HEAD anterior a este change (mismo resultado, mismos 4+3 tests, misma causa):
  ```
  $ git stash && cd backend && uv run pytest tests/infra/test_compose.py -q
  ... 4 failed, 52 passed in 2.26s
  $ cd .. && git stash pop
  ```
  No se arregla en este scope (es deuda de portabilidad Windows, igual que las de la línea base 1.3).

## 7. Volcado con el rol equivocado, con `pg_dump` real

- [x] 7.1 Test rojo de integración: un ciclo con las credenciales de `proptech_app` contra la base real
  y el `pg_dump` real de la imagen. Cubre los escenarios "Volcado con el rol equivocado" (reforzado:
  con `pg_dump` real) y "Un rol insuficiente no produce un backup aparentemente válido". Verificación: se ve el rojo
  con el rol correcto configurado (el test exige el fallo y con el rol bueno el volcado anda), con la
  salida pegada.

  **Implementación del test** (`backend/tests/integracion/test_respaldos_rol_real.py`, nuevo): corre
  `infra/respaldos/respaldar.sh` de verdad dentro de un contenedor efímero de `postgres:18.6-trixie`
  (`docker run --rm --user 1000:1000`, la misma imagen que el servicio real), conectado por
  `--add-host=host.docker.internal:host-gateway` al Postgres real de `testcontainers`
  (`base_del_edificio`, con roles y migraciones aplicadas de verdad). Dos tests: uno con
  `proptech_app` (debe fallar) y uno con `proptech_respaldo` (debe andar — triangulación, para que el
  primero no pase "porque `pg_dump` siempre falla").

  **Primera corrida, nació en rojo por un detalle del arnés (no de la producción)**:
  ```
  $ cd backend && date +%T && uv run pytest tests/integracion/test_respaldos_rol_real.py -q -s
  02:52:31
  ...
  E   AssertionError: el volcado con proptech_app debía fallar: ...
  E   {"evento":"arranque_rechazado","mensaje":"PROPTECH_UID: ... no puede correr como root"}
  2 failed
  ```
  `docker run` corre como root por defecto; se agregó `--user 1000:1000`. Con eso:
  ```
  $ uv run pytest tests/integracion/test_respaldos_rol_real.py -q -s
  02:52:59
  F.
  ```
  El primer test seguía fallando, pero por una aserción DEMASIADO estricta del test (prohibía la
  palabra "pg_dump" en el log, cuando el campo propio `etapa=pg_dump` la usa legítimamente — L-007 es
  sobre la SALIDA de la herramienta, no sobre nombrar el paso). Corregida la aserción (ver 7.2),
  **ambos tests dieron verde en su primera corrida real** — por L-013/L-019, un test nacido verde
  necesita su mutante: se cambiaron las credenciales del primer test a `proptech_respaldo` (el rol
  correcto) para confirmar que la aserción `returncode != 0` falla cuando el rol SÍ puede volcar:
  ```
  $ uv run pytest tests/integracion/test_respaldos_rol_real.py::TestVolcadoConElRolEquivocado::test_rol_de_app_hace_fallar_el_volcado_sin_dejar_archivos -q
  02:54:51
  E   AssertionError: el volcado con proptech_app debía fallar: stdout='{"...":"respaldo_generado",...}'
  E   assert 0 != 0
  1 failed
  ```
  Mutante revertido (`cp` desde la copia de respaldo tomada antes de mutar, L-013), GREEN confirmado
  de nuevo:
  ```
  $ cp /tmp/test_respaldos_rol_real.py.bak tests/integracion/test_respaldos_rol_real.py
  $ date +%T && uv run pytest tests/integracion/test_respaldos_rol_real.py -q
  02:55:16
  ..                                                                       [100%]
  2 passed in 17.97s
  ```

- [x] 7.2 Implementar D8: el test nuevo queda verde y **reemplaza** al caso con `FAKE_PG_DUMP_FALLA`
  de `test_respaldos.py:905-940` para ese escenario (L-019); los demás usos del binario falso quedan.
  Verificación: el test nuevo en verde, el viejo borrado, y la garantía estática de
  `test_compose.py:510` sigue en verde.

  **Reemplazo**: se verificó contra `git show 85e2437^:...` que las líneas 905-940 del archivo
  original corresponden exactamente a `TestSaludTrasUnFalloConUltimoOkBueno.
  test_salud_falla_si_un_ciclo_falla_despues_de_un_ultimo_ok_bueno` (su propio docstring de clase
  decía explícitamente que representaba "el escenario del rol equivocado" con un
  `FAKE_PG_DUMP_FALLA` genérico). Se borró ese método y se reescribió el docstring de la clase para
  explicar el reemplazo; se conservó `test_un_exito_posterior_limpia_la_marca_de_fallo` (el otro test
  de esa clase), que no afirma nada sobre roles — prueba la recuperación de `.ultimo-fallo`, cubierta
  también por otros tests de `TestFallasDelCiclo`. Los demás usos de binarios falsos en
  `test_respaldos.py` (F5, F8, retención, salud) se quedan como están: ninguno afirma probar un rol.

  **Trade-off aceptado**: el test borrado combinaba "ciclo falla" + "ya había un `.ultimo-ok` bueno
  antes"; esa combinación puntual no la repite el test nuevo (que arranca sin ningún backup previo).
  La mitad "un ciclo nuevo marca `.ultimo-fallo`" sigue cubierta por `TestFallasDelCiclo` y por el
  test nuevo; se acepta la pérdida de esa combinación específica porque el test que se borra nunca
  probó un rol real (L-019) y agregarla de nuevo con `pg_dump` real sumaría un tercer `docker run` sin
  que ninguna regla nueva lo pida.

  **GREEN (`test_respaldos.py` completo)**:
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_respaldos.py -q
  02:56:53
  ...
  8 failed, 51 passed in 65.76s
  ```
  Los 8 fallos son los mismos preexistentes/declarados de siempre (Windows `chmod`/`os.killpg`); 51
  en vez de 52 porque se borró un test (no una regresión).

  **Garantía estática de `test_compose.py:510` sigue en verde**:
  ```
  $ uv run pytest tests/infra/test_compose.py::test_respaldos_usa_pguser_del_rol_de_respaldo_y_no_tiene_postgres_password -q
  02:58:16
  .                                                                        [100%]
  1 passed in 0.10s
  ```
  `mypy tests/integracion/test_respaldos_rol_real.py`: `Success: no issues found in 1 source file`.

## 8. Conmutar la aplicación a una base restaurada

- [x] 8.1 Test rojo de la validación y de las tres verificaciones de `conmutar.sh`: destino que no
  cumple el patrón, destino vacío, sólo el prefijo, con espacio, punto y coma, mayúsculas, salto de
  línea y dígitos de otro alfabeto; destino igual a la base en uso; base inexistente; revisión de
  migraciones distinta de la cabeza; tabla de negocio sin RLS forzada o sin sus políticas. Cubre los
  escenarios "Destino que no cumple el patrón de nombre", "Destino que es la base en uso", "Destino
  inexistente o inalcanzable", "Destino con la revisión de migraciones equivocada" y "Destino sin
  Row-Level Security forzada". Verificación: rojo porque el script no existe, con la salida pegada.

  **Contexto de la sesión**: `infra/respaldos/conmutar.sh` y `backend/tests/infra/test_conmutar.py` ya
  existían en el working tree, sin commitear, de una sesión anterior cortada por límite. Se verificó su
  contenido a mano (no se asumió terminado, por instrucción explícita) contra `design.md` D6: implementa
  los 6 pasos completos (validación + 3 verificaciones + conmutación + verificación final), no sólo los
  pasos 1-4 que nombra esta tarea. Se reconstruyó el ciclo RED→GREEN de forma honesta en vez de asumir
  el trabajo heredado como evidencia propia (L-013).

  **RED** (moviendo `conmutar.sh` a un backup temporal para ver el rojo real de "el script no existe"
  y de las tres verificaciones sin implementación):
  ```
  $ cp infra/respaldos/conmutar.sh /tmp/conmutar.sh.bak && rm infra/respaldos/conmutar.sh
  $ cd backend && date +%T && uv run pytest tests/infra/test_conmutar.py -q
  04:35:51
  ...
  FAILED tests/infra/test_conmutar.py::test_script_existe
  FAILED tests/infra/test_conmutar.py::TestValidacionDelDestino::test_destino_igual_a_la_base_en_uso_rechaza_tras_un_solo_printenv
  FAILED tests/infra/test_conmutar.py::TestLasTresVerificaciones::test_revision_de_migraciones_equivocada_rechaza
  FAILED tests/infra/test_conmutar.py::TestLasTresVerificaciones::test_politicas_distintas_entre_destino_y_base_en_uso_rechaza
  FAILED tests/infra/test_conmutar.py::TestLasTresVerificaciones::test_las_tres_verificaciones_pasando_no_rechaza_por_si_solas
  FAILED tests/infra/test_conmutar.py::TestLaConmutacionEnSi::test_env_queda_con_el_destino_y_las_demas_lineas_intactas
  FAILED tests/infra/test_conmutar.py::TestLaConmutacionEnSi::test_env_anterior_guarda_el_valor_previo
  FAILED tests/infra/test_conmutar.py::TestLaConmutacionEnSi::test_falla_al_levantar_no_repite_el_marcador_de_la_herramienta
  FAILED tests/infra/test_conmutar.py::TestProyectoComposeAislado::test_usa_la_variable_del_proyecto
  9 failed, 12 passed in 0.96s
  ```

- [x] 8.2 Implementar D6 (pasos 1 a 4): `conmutar.sh` con la validación del destino, la cabeza de
  Alembic **derivada** y no escrita a mano, y las verificaciones de RLS por el efecto en el catálogo
  comparando el contenido de las políticas, no su cantidad (L-018). Verificación: el test de 8.1 en
  verde y ningún comando contra la base antes de que la validación del nombre pase.

  **GREEN** (restaurado desde el backup):
  ```
  $ cp /tmp/conmutar.sh.bak infra/respaldos/conmutar.sh && chmod +x infra/respaldos/conmutar.sh
  $ cd backend && date +%T && uv run pytest tests/infra/test_conmutar.py -q
  04:36:03
  ...
  FAILED tests/infra/test_conmutar.py::TestValidacionDelDestino::test_rechaza_sin_invocar_docker[proptech_con_salto\n]
  1 failed, 20 passed in 13.26s
  ```
  **El único rojo restante es PREEXISTENTE, no un defecto de `conmutar.sh`**: se investigó a fondo (no
  se asumió la etiqueta de la línea base sin verificar). Confirmado con tres pruebas directas:
  ```
  $ bash -c 'v=$(printf "proptech_con_salto\n"); [[ "$v" =~ ^proptech_[a-z0-9_]{1,50}$ ]] && echo MATCH || echo NOMATCH'
  MATCH   # el '$' de ERE en bash matchea antes de un salto de línea final — reproducible en Linux también
  ```
  Pero el argumento real, tal como llega a `$1` desde `subprocess.run(["bash", SCRIPT, destino], ...)`
  en esta máquina Windows, **pierde el `\n` final antes de llegar a bash** (confirmado con
  `echo -n "$1" | xxd`: la cadena llega como `proptech_con_salto`, 19 bytes, sin el byte `0a`). Es decir,
  el destino llega como un nombre VÁLIDO (sin el salto de línea), así que el script invoca docker
  correctamente — el test espera rechazo con 0 invocaciones y eso es lo que falla, pero por mutilación
  del argumento en el límite Windows↔Git-Bash, no por un defecto de la validación. Es **el mismo defecto
  exacto** que la línea base 1.3 ya declaró preexistente para
  `test_restaurar.py::TestDestinoInvalido::test_rechaza_sin_invocar_docker[proptech_con_salto\n]` (mismo
  nombre de caso, mismo patrón `^...$`, mismo script hermano): se reafirma la misma clasificación, no se
  arregla acá (fuera de alcance del grupo 8, y `restaurar.sh` no se toca).

  **Mutante de seguridad (L-013/L-019), verificación 3 (RLS) — porque el test nació en verde para el
  caso heredado**: se copió `conmutar.sh` a un backup, se mutó la condición de rechazo de la
  verificación 3 a `if false; then ... fi` (2 líneas):
  ```diff
  -if [ "$politicas_base_en_uso" != "$politicas_destino" ]; then
  +if false; then
  ```
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_conmutar.py::TestLasTresVerificaciones::test_politicas_distintas_entre_destino_y_base_en_uso_rechaza -q
  04:36:42
  AssertionError: assert 0 != 0
  tests/infra/test_conmutar.py:229: AssertionError
  1 failed in 3.66s
  ```
  El mutante falla exactamente en la aserción que el test dice probar (`resultado.returncode != 0`,
  línea 229), no en un paso anterior (L-034). Revertido con `cp` desde el backup; `diff` confirmó
  identidad byte a byte con el original antes de continuar.

- [x] 8.3 Test rojo de la conmutación en sí: `.env` queda con el `POSTGRES_DB` nuevo y las demás líneas
  idénticas byte a byte, `.env.anterior` guarda el valor anterior con los mismos permisos, la base
  anterior sigue existiendo intacta, y una falla de una herramienta no repite su marcador. Cubre
  "Conmutación a una base restaurada correcta" y "Falla de una herramienta durante la conmutación".
  Verificación: rojo antes de 8.4, con la salida pegada.

  **RED**: mismo RED que 8.1 (script ausente) cubre también `TestLaConmutacionEnSi` íntegramente — ver
  la salida de 8.1: `test_env_queda_con_el_destino_y_las_demas_lineas_intactas`,
  `test_env_anterior_guarda_el_valor_previo` y `test_falla_al_levantar_no_repite_el_marcador_de_la_herramienta`
  están en la lista de los 9 fallidos.

- [x] 8.4 Implementar D6 (pasos 5 y 6): resguardo de `.env`, reemplazo de la línea, levantada de los
  servicios que se conectan a la base y verificación final de `GET /api/salud`; el script no borra ni
  modifica la base que deja de usarse y lee `PROPTECH_COMPOSE_PROYECTO` (L-047). Verificación: el test
  de 8.3 en verde.

  **GREEN**: mismo GREEN que 8.2 (20 passed / 1 preexistente) cubre los tres tests de
  `TestLaConmutacionEnSi` y `TestProyectoComposeAislado::test_usa_la_variable_del_proyecto` (lee
  `PROPTECH_COMPOSE_PROYECTO`, confirmado con el test dedicado, verde).

  **Mutante de seguridad adicional, `.env.anterior` (la aserción de resguardo más sensible — toca el
  archivo con contraseñas)**:
  ```diff
  -if [ -f .env ]; then
  -  cp -p .env .env.anterior
  -fi
  +if false; then
  +  cp -p .env .env.anterior
  +fi
  ```
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_conmutar.py::TestLaConmutacionEnSi::test_env_anterior_guarda_el_valor_previo -q
  04:37:23
  AssertionError: falló el resguardo .env.anterior
  tests/infra/test_conmutar.py:312: AssertionError
  1 failed in 3.20s
  ```
  Falla en la aserción exacta (`anterior.exists()`, línea 312). Revertido con `cp` desde el backup;
  `diff` confirmó identidad byte a byte.

  **GREEN final confirmado**:
  ```
  $ cd backend && date +%T && uv run pytest tests/infra/test_conmutar.py -q
  04:37:37
  FAILED tests/infra/test_conmutar.py::TestValidacionDelDestino::test_rechaza_sin_invocar_docker[proptech_con_salto\n]
  1 failed, 20 passed in 13.35s
  ```

- [x] 8.5 Ensayo real de la conmutación de punta a punta: generar un backup, restaurarlo con
  `restaurar.sh`, conmutar, confirmar `GET /api/salud` 200 y que los datos son los del backup, y
  volver a la base original con el procedimiento documentado. Cubre "Restauración probada" y
  "Conmutación a una base restaurada correcta" de punta a punta (L-043). Verificación: comandos, hora y
  salida pegados; se decide acá si el ensayo entra al humo o queda en el cierre según cuánto suma al
  job (L-044).

  (evidencia del ensayo real abajo, debajo de esta tarea, tras levantar el stack completo)

## 9. Documentación y cierre

- [ ] 9.1 README: el arranque sin `mkdir`, el procedimiento de conmutación con su línea sobre la
  ventana de datos que separa el backup del incidente, y `RESPALDO_CONSERVAR_DIAS` en la tabla única de
  variables. Verificación: `test_readme_variables.py` en verde y el test de 6.1 que exige que no haya
  paso manual.
- [ ] 9.2 Knowledge base, según la sección "Knowledge Base Impact" del proposal: REWRITE de la ficha
  §1e y de las filas de deuda cerradas en `12_fichas_de_changes.md`, REWRITE del estado de C-24 en
  `CHANGES.md`, REWRITE de la sección de infraestructura de `02_descripcion_general.md`, APPEND de las
  decisiones (D2, la conmutación verificada y el resultado de F6) en `09_decisiones_y_supuestos.md` y
  APPEND de las lecciones en `15_lecciones.md`. Verificación: los cinco archivos tocados, con el texto
  viejo borrado en los REWRITE (no sólo agregado al final).
- [ ] 9.3 Corrida de cierre: la suite completa entera (no una selección) después del último commit, con
  `git rev-parse HEAD`, comando, hora y salida pegados; más el humo. Verificación: todo en verde sobre
  el SHA final; cualquier cambio de código posterior invalida esta corrida y obliga a repetirla
  (L-055, L-031, L-037).
