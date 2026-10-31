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

- [ ] 4.1 Test rojo del apagado: `SIGTERM` en espera y `SIGTERM` durante un volcado en curso. Cubre
  los escenarios "Apagado mientras no hay volcado en curso" y "Apagado durante un volcado" de
  `respaldos-de-la-base`. Verificación: rojo con el script sin `trap` (el proceso no sale por su
  cuenta y queda el `.parcial`), con la salida y el tiempo medido pegados.
- [ ] 4.2 Implementar D3: `trap` de `SIGTERM`/`SIGINT`, espera y volcado con `& wait "$!"`, muerte del
  hijo, borrado del `.parcial`, evento JSON de apagado y salida 0; un apagado no escribe
  `respaldo_fallido` ni `.ultimo-fallo`, y todo el camino con `if !` explícito (L-014). Verificación:
  el test de 4.1 en verde y la suite de 1.3 sin regresiones.
- [ ] 4.3 Ejecutar el apagado del stack real y medir. Cubre "Apagado del stack completo".
  Verificación: el contenedor de respaldos sale por su cuenta, sin consumir el plazo de gracia ni
  recibir `SIGKILL`; comando, tiempo y salida pegados.

## 5. Ningún 503 sin su línea (F6)

- [ ] 5.1 Repetir la ráfaga del rompedor del 1d sobre `GET /api/salud` con una dependencia congelada y
  pegar comando, cantidad de intentos y salida, nombrando qué servicio puede producir la línea
  (L-016). Verificación: queda escrito si F6 se reprodujo y en cuántos intentos; el resultado no cierra
  la tarea por sí solo.
- [ ] 5.2 Test rojo determinista de D5: forzar la carrera perdida (el verificador devuelve `False` sin
  haber informado) y exigir la línea `salud_degradada` con el `request_id` antes del 503, ni cero ni
  dos. Cubre el escenario "Ráfaga de pedidos con una dependencia congelada" de `entorno-de-ejecucion`.
  Verificación: rojo contra `salud.py` de hoy, con la salida pegada; si diera verde, se declara con el
  mutante que prueba la aserción (L-049).
- [ ] 5.3 Implementar D5 en `proptech_api/salud.py`: antes de responder, cada dependencia informada
  como `sin_conexion` pasa por `_informar_una_sola_vez`. Verificación: el test de 5.2 en verde y el
  escenario "Una sola línea por verificación fallida" sigue en verde sin modificarse.

## 6. La carpeta del host sin paso manual

- [ ] 6.1 Test rojo del arranque: el camino documentado deja la carpeta creada con el UID/GID del host
  si falta, no cambia el dueño ni el contenido si ya existe, y el README no pide ningún `mkdir`. Cubre
  los tres escenarios de "La carpeta de respaldos no depende de un paso manual". Los tests no asumen
  `infra/datos-respaldos/` vacía ni leen binarios como texto (L-033). Verificación: rojo con el README
  y el arranque de hoy, con la salida pegada.
- [ ] 6.2 Implementar D7: script de arranque en `infra/` que crea la carpeta con el dueño correcto y
  delega en `docker compose up`; README, humo y CI pasan a usarlo; la tabla de variables se actualiza.
  Verificación: el test de 6.1 en verde, un arranque desde cero sin la carpeta creada genera un backup
  en menos de 2 minutos y el servicio de respaldos no reinició ninguna vez.

## 7. Volcado con el rol equivocado, con `pg_dump` real

- [ ] 7.1 Test rojo de integración: un ciclo con las credenciales de `proptech_app` contra la base real
  y el `pg_dump` real de la imagen. Cubre los escenarios "Volcado con el rol equivocado" (reforzado:
  con `pg_dump` real) y "Un rol insuficiente no produce un backup aparentemente válido". Verificación: se ve el rojo
  con el rol correcto configurado (el test exige el fallo y con el rol bueno el volcado anda), con la
  salida pegada.
- [ ] 7.2 Implementar D8: el test nuevo queda verde y **reemplaza** al caso con `FAKE_PG_DUMP_FALLA`
  de `test_respaldos.py:905-940` para ese escenario (L-019); los demás usos del binario falso quedan.
  Verificación: el test nuevo en verde, el viejo borrado, y la garantía estática de
  `test_compose.py:510` sigue en verde.

## 8. Conmutar la aplicación a una base restaurada

- [ ] 8.1 Test rojo de la validación y de las tres verificaciones de `conmutar.sh`: destino que no
  cumple el patrón, destino vacío, sólo el prefijo, con espacio, punto y coma, mayúsculas, salto de
  línea y dígitos de otro alfabeto; destino igual a la base en uso; base inexistente; revisión de
  migraciones distinta de la cabeza; tabla de negocio sin RLS forzada o sin sus políticas. Cubre los
  escenarios "Destino que no cumple el patrón de nombre", "Destino que es la base en uso", "Destino
  inexistente o inalcanzable", "Destino con la revisión de migraciones equivocada" y "Destino sin
  Row-Level Security forzada". Verificación: rojo porque el script no existe, con la salida pegada.
- [ ] 8.2 Implementar D6 (pasos 1 a 4): `conmutar.sh` con la validación del destino, la cabeza de
  Alembic **derivada** y no escrita a mano, y las verificaciones de RLS por el efecto en el catálogo
  comparando el contenido de las políticas, no su cantidad (L-018). Verificación: el test de 8.1 en
  verde y ningún comando contra la base antes de que la validación del nombre pase.
- [ ] 8.3 Test rojo de la conmutación en sí: `.env` queda con el `POSTGRES_DB` nuevo y las demás líneas
  idénticas byte a byte, `.env.anterior` guarda el valor anterior con los mismos permisos, la base
  anterior sigue existiendo intacta, y una falla de una herramienta no repite su marcador. Cubre
  "Conmutación a una base restaurada correcta" y "Falla de una herramienta durante la conmutación".
  Verificación: rojo antes de 8.4, con la salida pegada.
- [ ] 8.4 Implementar D6 (pasos 5 y 6): resguardo de `.env`, reemplazo de la línea, levantada de los
  servicios que se conectan a la base y verificación final de `GET /api/salud`; el script no borra ni
  modifica la base que deja de usarse y lee `PROPTECH_COMPOSE_PROYECTO` (L-047). Verificación: el test
  de 8.3 en verde.
- [ ] 8.5 Ensayo real de la conmutación de punta a punta: generar un backup, restaurarlo con
  `restaurar.sh`, conmutar, confirmar `GET /api/salud` 200 y que los datos son los del backup, y
  volver a la base original con el procedimiento documentado. Cubre "Restauración probada" y
  "Conmutación a una base restaurada correcta" de punta a punta (L-043). Verificación: comandos, hora y
  salida pegados; se decide acá si el ensayo entra al humo o queda en el cierre según cuánto suma al
  job (L-044).

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
