# Fichas detalladas de los changes

Extra de Active Stack v1 (D-093): el detalle completo de cada cambio del roadmap, sin el estado (que
vive sólo en `CHANGES.md`, la fuente única para saber qué está hecho). Cada ficha es **la entrada del
`/opsx:propose`** de ese cambio: el proponente parte de acá y de los archivos que la ficha cita. **Se
reescribe** cuando cambia el plan; el porqué va a `09_decisiones_y_supuestos.md` (D-045, D-047,
D-049).

El ciclo de cada cambio está en `14_forma_de_trabajo.md`: proponer, construir, romper, auditar y
archivar con commit y push. Un cambio arranca cuando el anterior está archivado.

---

## M1 · Liquida

### 1a · `infraestructura-base`

- **Objetivo**: que el proyecto arranque entero con un comando y que los tests corran solos en cada push.
- **Decisiones**: D-020, D-036, D-038, D-040, D-043, D-046.
- **Entra**: estructura de carpetas de D-040 (`config/`, `web/`, `backend/` con `proptech_core`,
  `proptech_api` y `proptech_worker`, `infra/`); Docker Compose con PostgreSQL, Caddy, la API y la
  web; Alembic con una primera migración vacía; esqueleto de FastAPI con un endpoint de salud;
  esqueleto de Next.js; CI que corre los tests y el linter; `.env.example` sin secretos; sólo Caddy
  con puertos públicos.
- **No entra**: parámetros y datos semilla (1b); Redis, worker y logs (1c); login (2).
- **Habilita**: 1b.
- **Decidir en el design**: versiones fijadas de cada imagen; herramienta de lint y formato de
  Python y TypeScript; cómo corre PostgreSQL real en el CI para los tests de integración.
- **Que intente romper el rompedor**: levantar desde un clon limpio siguiendo sólo el README; que la
  base o algún servicio interno quede expuesto a Internet; que el CI pase con un test roto; secretos
  en el repo o en las imágenes.
- **Terminado cuando**: `docker compose up` levanta todo desde un clon limpio; el endpoint de salud
  responde a través de Caddy; el CI está en verde y falla a propósito con un test roto.

### 1b · `arranque-del-sistema`

- **Objetivo**: las piezas transversales que todos los cambios usan (re-alcanzado por D-052).
- **Decisiones**: D-042, D-046, D-052, D-053.
- **Entró**: configuración con las variables de Redis y el archivo de parámetros conectadas en Compose;
  migraciones que dependen sólo de PostgreSQL; tipo `Dinero` sobre `Decimal`; `config/parametros.yaml`
  con su lector validado; el edificio de ejemplo como archivo validado y su comando de verificación.
- **Pasó a 1c**: Redis y el worker, logs y número de seguimiento, respaldos, `/salud-web`, humo y README.
- **Habilita**: 1c.

### 1c · `cola-logs-y-respaldos`

- **Objetivo**: la cola de trabajos con su worker, los logs estructurados y el número de seguimiento
  de punta a punta, que todos los cambios siguientes dan por existentes (D-052). Partido del 1d por la
  auditoría de Alberto (D-087); el nombre conserva "respaldos" porque el CLI de OpenSpec no renombra
  cambios, pero los respaldos son del 1d.
- **Decisiones**: D-038, D-047 (punto 4, logs con número de seguimiento), D-052, D-087, D-090, D-091.
- **Gobernanza**: MEDIUM. Ciclo completo, sin aprobación previa de los socios.
- **Entró**: logs en JSON con una lista cerrada de campos y sin el texto de los errores de terceros
  (L-007), con las dos excepciones conocidas de ARQ y los eventos fijos `excepcion_como_mensaje` y
  `traceback_crudo_descartado` (D-091); `request_id` validado con coincidencia completa y sólo ASCII,
  con una sola tabla de casos para la API y la web (L-008, L-009), que viaja por Caddy, la web, la
  API, PostgreSQL y el worker; Redis protegido y persistente; worker ARQ con reintentos espaciados,
  idempotencia (tabla `trabajos_hechos`) y los mismos tests de arranque que la API (L-009); `/api/salud`
  con la cola; `/salud-web` con su contrato de respuesta; rotación de logs; `Dinero` copiable y
  serializable; contraseñas como `SecretStr`; un único engine por proceso con su pool. 35 tareas en
  `openspec/changes/archive/2026-10-14-cola-logs-y-respaldos/` (D-090), las 35 hechas.
- **No entró**: respaldos, restauración, el humo ampliado y el README (1d); tareas reales del worker
  (7, 13, 14); el tenant del worker (2).
- **Depende de**: 1b. **Habilita**: 1d.
- **Cierre (14/10/2026)**: el auditor dio **OK con deuda anotada** (D-091); Juani aceptó la tabla. La
  deuda queda en "Deuda técnica de las auditorías del 13/10" más abajo, con dueño por ítem: F2c (base
  congelada con efecto tardío) y F12b (excepciones de terceros envueltas) y `repr(RedisSettings)` al
  cambio 7; F13 (`/salud-web` con dependencia congelada), `salud_degradada` duplicado y F7c (parseo de
  traceback crudo con formas muy particulares) al 1d; M12 a medias (URL de base como `str`) al cambio 2.
  La verificación de punta a punta por el proxy queda para el humo del 1d.

### 1d · `respaldos-y-restauracion` · HIGH (D-087)

- **Objetivo**: que exista siempre un backup reciente de la base fuera de Docker, generado solo, y que
  cada corrida del CI pruebe que se restaura; y que el humo verifique de punta a punta lo del 1c.
- **Decisiones**: D-043, D-047 (punto 4, backups automáticos), D-087. Avanza H46 (restauración
  probada) de M3.
- **Gobernanza HIGH** (D-087, D-094): borra bases (`dropdb` en la restauración), escribe en el disco del host
  (bind mount) y suma un servicio con la contraseña de la base. Juani aprobó por escrito y con fecha en
  `proposal.md` antes de construir (14/10/2026).
- **Entró**: servicio `respaldos` con `pg_dump` al arrancar y cada día, acotado por un límite de tiempo
  (L-001), en una carpeta del host a salvo de `docker compose down -v`, con 14 copias y salud por
  antigüedad; validación de su configuración con dígitos ASCII y sin ceros a la izquierda (L-002,
  L-008); `restaurar.sh` con el destino validado por `^proptech_[a-z0-9_]{1,50}$` y distinto de la base
  en uso, siempre sobre el proyecto `proptech` (L-006), sin repetir la salida de las herramientas
  (L-007); humo ampliado (Redis, worker, `request_id` de punta a punta, Redis pausado, backup,
  restauración y semilla); README. 20 tareas en
  `openspec/changes/archive/2026-10-14-respaldos-y-restauracion/` (D-095, corrige el número de D-090).
- **No entra**: copia fuera del servidor y cifrado (con el despliegue); restaurar sobre la base en
  uso; backups de Redis; alertas externas.
- **Deuda del 1c, resuelta por este cambio** (D-091): **F13**, `/salud-web` informaba `sin_conexion`
  cuando una dependencia estaba congelada en vez de lenta (la API tardaba 2,005 s y la web cortaba a
  2,000 s): resuelto con las dos verificaciones en hilos paralelos y un plazo total de 1,5 s (D20,
  D-095). **`salud_degradada` duplicado**: el log de la base pausada escribía dos líneas por cada
  pedido colgado; resuelto junto con el plazo total (una sola línea por verificación fallida, con el
  `request_id`). **F7c**: el parseo de un traceback crudo podía sacar datos raros a
  `tipo_error`/`traza` con formas muy particulares; resuelto al dejar de parsear el texto (D21: evento
  fijo según `type(msg) is str`).
- **Depende de**: 1c. **Habilita**: 2a.
- **Cierre (14/10/2026)**: tres vueltas entre constructor, rompedor y auditor. El auditor dio **OK con
  deuda anotada** en su vuelta 3 (D-095); Juani aceptó esa tabla. Backend 516 → 606 tests (+1
  xfailed); web sin cambios (16). La deuda aceptada queda en "Deuda del cierre del 1d" más abajo, con
  dueño por ítem (mayormente el cambio 15 y el cambio 2).
- **Que intentó romper el rompedor**: un destino de restauración que borre la base en uso (con espacios,
  punto y coma, mayúsculas, salto de línea, más de 63 caracteres o igual a `POSTGRES_DB`); una
  retención que borre un archivo ajeno de la carpeta; un volcado que se cuelgue con la base pausada;
  una configuración con `060`, espacios o dígitos de otro alfabeto que pase; la contraseña o la salida
  de `pg_dump` en el log; un backup a medio escribir con nombre final; que el backup no sobreviva a
  `docker compose down -v`.
- **Terminado**: Juani aprobó la propuesta el 14/10/2026; las 20 tareas están hechas con su test visto
  en rojo; el humo genera el backup solo, lo restaura en `proptech_restauracion` con la misma revisión
  de Alembic y el archivo sobrevive a `down -v`; la corrida equivalente al CI está en verde; el
  auditor dio el OK con deuda anotada.

### 2 · `acceso-y-aislamiento` · partido en 2a, 2b y 2c (D-097)

El explore propio (`openspec/exploraciones/2026-10-15-acceso-y-aislamiento.md`, 15/10/2026) recomendó
partirlo, Juani lo aprobó el mismo día y la revisión del arquitecto separó además el endurecimiento
(D-097): el **2a** es el candado y se prueba sin login; el **2b** es el login; el **2c** es el
endurecimiento de infraestructura que el candado no necesita. Objetivo común: que cada persona entre y
vea sólo lo suyo, aunque el código tenga un error. P18 y P23 se resolvieron en D-096.

### 2a · `aislamiento-por-administracion` · crítico

- **Objetivo**: que la base misma impida ver o escribir datos de otra administración, y que el alcance
  por edificio y el permiso por acción respondan 404 y 403 según D-037 y D-096, con la identidad
  inyectada en los tests (todavía sin login).
- **Reglas**: R10. **Decisiones**: D-016, D-021, D-037, D-076, D-082, D-087, D-091, D-096, D-097.
- **Entra**: cuatro roles de PostgreSQL (el de arranque, superusuario, sólo para crear y reparar los
  otros y como dueño de la auditoría; `proptech_migrador`, dueño de las tablas de dominio;
  `proptech_app`, sin superusuario ni `BYPASSRLS`, para la API y el worker; `proptech_respaldo`, sin
  superusuario, con `BYPASSRLS` y `pg_read_all_data`, para `pg_dump`), con un par de credenciales por
  rol y ningún servicio permanente con la contraseña del superusuario; tablas mínimas (D-082) con
  `administracion_id NOT NULL`, FK compuestas y RLS forzada con `current_setting(..., true)` y
  `nullif`; la convención de `complejo_id NOT NULL` con FK compuesta para toda tabla de un edificio; el
  tenant en `session.info` y fijado con `set_config(..., true)` en cada transacción; la identidad
  inyectable (401 en producción hasta el 2b); 404 fuera de alcance, indistinguible de "no existe", y
  403 con el permiso faltante; auditoría en `acceso.aplicacion`, del rol de arranque, de sólo agregar y
  en la misma transacción; el tenant del worker como argumento validado; el guardián del catálogo; la
  web fuera de la red de la base; M12.
- **Fronteras**: `complejos` (y 7, 8, 10b) → `acceso` → `compartido`; `acceso` no importa `complejos`
  y `compartido` no importa `acceso`.
- **Elecciones que firma el socio que apruebe**: E1, el migrador sin `BYPASSRLS` (es de confianza
  equivalente al superusuario sobre sus tablas; la razón es obligar a sembrar con el tenant fijado a
  propósito); E2, el alcance por edificio en la aplicación, con su riesgo (un vecino viendo a otro) y
  su costo de revertir; E3, `trabajos_hechos` sin `administracion_id`; E4, Dependabot al cambio 15; E5,
  cuatro roles en vez de los dos de D-087.
- **No entra**: el login (2b); el endurecimiento que no hace al candado (2c); quién lee la auditoría;
  las acciones sensibles de otros módulos; la recuperación real desde un backup en otro servidor
  (cambio 15).
- **Depende de**: 1d. **Habilita**: 2b, 2c, 3.
- **Aprobado**: Juani, 15/10/2026, las cinco elecciones E1 a E5 firmadas en `proposal.md` (gobernanza
  CRITICAL, D-094).
- **Que intentó romper el rompedor**: la lista de la propuesta (fuga por un `SET LOCAL` que no se
  aplicó, `current_setting` sin `missing_ok`, un rol con `BYPASSRLS` o superusuario usado por la app,
  backups incompletos por usar el rol equivocado o `--enable-row-security`, 404 contra 403 filtrando
  existencia, la auditoría salteada, editada o con su trigger desactivado, el worker sin tenant, el
  `GRANT` olvidado, el filtro por edificio de la aplicación), más lo que ya pedía esta ficha: ver un
  edificio de otra administración tipeando la URL o mandando otro `tenant_id`, un `SET` sin `LOCAL` que
  contagie al pedido siguiente, un colaborador en un edificio no asignado.
- **Terminado**: hay tests contra PostgreSQL real, conectados como `proptech_app`, que intentan
  cruzar administraciones y fallan cerrados; cada rol ve exactamente lo de D-037 y cada acción sigue la
  matriz de D-096; la auditoría registra la asignación de edificios y ni la app ni el migrador la
  pueden editar; el humo verifica el rol de la app y un backup completo hecho sin superusuario; 34
  tareas en `openspec/changes/archive/2026-10-15-aislamiento-por-administracion/`, hechas con su rojo
  visto.
- **Cierre (15/10/2026)**: cuatro vueltas entre constructor, rompedor y auditor. El auditor bloqueó en
  la vuelta 1 (R1 a R4, R7, R8, R10) y en la vuelta 2 (V2-1, V2-2, V2-4); el constructor los resolvió
  todos. En la vuelta 3 el auditor encontró tres bloqueantes más (V3-1, V3-2, V3-4) y dio a elegir entre
  cerrar con esos tres anotados como deuda (opción A) o abrirlos una vuelta más (opción B); Juani eligió
  la **opción B** el 15/10/2026, con la regla de cierre "el rompedor verifica sólo los 4 puntos (V3-1,
  V3-2, V3-4 y V3-10); lo que encuentre fuera de eso va a deuda nueva y no bloquea" (D-098). El rompedor
  de la vuelta 4 cerró V3-1, V3-2 y V3-4 (M8 y M5); V3-10 se cerró aparte, en el commit `3bbd2a6`. Corrida
  de cierre: backend 863 passed + 1 xfailed, web 16 passed, humo OK con el segundo `up` incluido. El
  auditor dio **OK con deuda anotada**; la deuda queda en "Deuda del cierre del 2a" más abajo, con dueño
  por ítem (mayormente el 2b y el 15).

### 2b · `login` (nombre provisional) · crítico

- **Objetivo**: que cada persona entre a su administración: el personal con contraseña, el vecino con
  link mágico por mail (D-097).
- **Historias**: HU-V1. **Decisiones**: D-036, D-039, D-043, D-096, D-097.
- **Entra**: login del personal (titular, colaborador, consejo) con contraseña; link mágico del vecino
  (token de un solo uso con vencimiento corto); la sesión del lado del servidor de Next (D-036); límite
  de intentos en el login (por cuenta y, más laxo, por IP, para no bloquear a un edificio detrás del
  mismo wifi); auditoría de `ingreso_exitoso` e `ingreso_fallido` con `acceso.aplicacion` (cada acción
  nueva, con su migración de vocabulario); CSP en Next; la pantalla de login; qué rutas quedan sin
  sesión.
- **No entra**: el puerto de email completo, con reintentos y plantillas (13); las pantallas del portal
  (11) y del consejo (12).
- **Deuda del 2a con dueño este cambio** (L-012, D-098): ver "Deuda del cierre del 2a" más arriba (R5,
  R9, V2-7, V3-5, D-1, D-2 y D-6, más el aviso de que la primera FK legítima hacia `auditoria` frena
  cada arranque).
- **Depende de**: 2a. **Habilita**: el uso por una persona y el despliegue: lo piden 11 y 15 (no el 3,
  que se construye con la identidad inyectada).
- **Bloqueado por**: **P48** (a qué administración entra un email con cuenta en dos).
- **Decidir en el design**: cómo se manda el mail del link mágico antes del cambio 13 (un envío mínimo
  en este cambio o adelantar parte del puerto del 13); si el límite de intentos falla abierto o cerrado
  cuando Redis no responde (el explore sugiere abierto, como ya trata a Redis `/api/salud`); el reset de
  contraseña del personal (asistido por el titular o por mail).
- **Que intente romper el rompedor**: fuerza bruta contra el login; un vecino abriendo pantallas del
  personal; un link mágico reusado, vencido o reenviado; el login entrando a la cuenta equivocada
  cuando el mismo email existe en dos administraciones; el límite de intentos bloqueando a todo un
  edificio por IP compartida; el token de sesión visible en el navegador.
- **Terminado cuando**: el personal y el vecino entran a su administración y a ninguna otra; los
  intentos fallidos se limitan y se auditan.

### 2c · `endurecimiento-de-infraestructura` · MEDIUM

- **Objetivo**: cerrar la deuda de infraestructura con dueño "2" que no cambia quién ve qué dato, y la
  del cierre del 2a con dueño 2c.
- **Decisiones**: D-051, D-087, D-089, D-095, D-097, D-098.
- **Gobernanza**: MEDIUM. Checkpoints, sin aprobación previa de los socios (D-094). Regla de freno: dos
  tareas tocan el arranque del candado (`app.py` por V2-5, `roles.py` por V3-14); si aparece algo que
  afecte el aislamiento, se frena y se consulta a Juani. Revisado por DevOps el 16/10/2026 contra
  `d0502fa`; cambios aprobados por Juani.
- **Entra**: cabeceras de seguridad en Caddy, sin `Server`, `Via` ni `X-Powered-By`, también en los 502
  que genera Caddy, y HEAD con las mismas cabeceras que GET; volúmenes de Caddy (verificados con
  `instance.uuid`); `no-new-privileges` y capacidades mínimas justificadas viendo fallar el arranque
  sobre volúmenes nuevos y existentes, verificadas en el proceso vivo; PID 1 no root en siete servicios,
  con el rojo en cada uno; CI en pull requests sin perder `push` a `main` ni `workflow_dispatch`, con
  `timeout-minutes` medidos y gitleaks y `shellcheck` por digest; humo con pasos nombrados, logs al
  fallar, un respaldo por arranque, la doble congelada y las cabeceras de punta a punta; una sola tabla
  de variables (README, `08` la enlaza); la deuda del 2a (V2-5, V3-8, V3-9, V3-14, V3-15, D-5); rollback
  ejercitado. 20 tareas en `openspec/changes/endurecimiento-de-infraestructura/`.
- **No entra**: HSTS, `read_only` en los contenedores, imágenes base por digest, monitoreo fuera del CI
  y los secretos de Compose, incluidos `REDIS_PASSWORD` en la línea de comando y las contraseñas en
  `docker inspect` (con el despliegue, 15); CSP (2b); Dependabot (15).
- **Deuda del 2a con dueño este cambio** (L-012, D-098): ver "Deuda del cierre del 2a" más abajo (V2-5,
  V3-8, V3-9, V3-14, V3-15 y D-5). V2-5 tiene una pregunta abierta para Juani (P1 de la propuesta: choca
  con V3-5, dueño 2b, que pide un test antes de tocar `lifespan`).
- **Depende de**: 2a (los dos tocan `compose.yaml` y `humo.sh`). **Habilita**: 15.
- **Que intente romper el rompedor**: una respuesta que se escapa sin cabeceras (un 502 de Caddy, una
  redirección, un 404, un HEAD); un servicio que arranca como root y el chequeo que no lo ve (`gosu` en
  `db` y `redis`); una capacidad de más sin justificar, o una de menos que sólo rompe sobre un volumen
  existente; un trabajo del CI sin límite; un paso del humo que falla sin decir cuál o cuyo log se
  pierde; la doble congelada que deja algo pausado; un rollback que no vuelve.
- **Terminado cuando**: las 20 tareas están hechas con su rojo visto; el rollback se ejercitó (subir y
  volver a `d0502fa` sobre volúmenes con datos, salud 200 y conteos iguales en las dos direcciones, con
  comandos y salida); la corrida de cierre está en verde, en orden y de a uno; y un clon limpio del
  commit final levanta con los comandos del README tal cual, con `/api/salud` 200.

### 3 · `configuracion-del-edificio` · HIGH

- **Objetivo**: que el administrador cree un edificio y lo configure como dice su reglamento.
- **Historias**: HU-A1. **Reglas**: R01 (sólo la definición de grupos), R02 (sólo el campo de estado, desactivado; la regla se construye con barrios, D-089), R03 (su
  configuración), R15 (porcentaje), R16 (categorías).
- **Propuestas** (entran si se validan): R35 (calendario de feriados del sistema), R36 (tasa de la
  extraordinaria), R39 (marca de unidad del consorcio).
- **Decisiones**: D-010, D-013, D-029, D-030, D-031, D-041, D-042, D-080, D-087.
- **Gobernanza HIGH** (D-087, D-094): guarda la configuración versionada de intereses, que cambia montos. Se
  propone y se espera la revisión de uno de los dos socios antes de construir.
- **Entra**: edificios, unidades con su tipo (departamento, cochera, baulera, local) y coeficiente;
  grupos de reparto con sus unidades y método; categorías de gasto (crear, renombrar, ordenar,
  desactivar); configuración de intereses y fondo de reserva como **menús cerrados** tomados de
  `parametros.yaml` al crear, con versión (D-010, D-080);
  **cargar en la base el edificio de ejemplo** de `config/semilla/edificio-ejemplo.yaml` (validado en 1b);
  el **estado de migración del edificio** (pendiente, confirmada o sin saldos previos, R09, D-083): la
  semilla y su validador suman ese campo, y el edificio de ejemplo queda "sin saldos previos"; el
  cambio 5 usa ese estado; **alinear el validador de la semilla con R01** (tolerancia de ±0,0001) y con
  la respuesta a P24: hoy los grupos Ascensor y Cocheras de la semilla no suman 1 con un solo
  coeficiente por unidad.
- **No entra**: carga masiva desde Excel (5); cálculos (4, 7); el motor de reglas (6b, D-087).
- **Deuda del 2a con dueño este cambio** (L-012, D-098): ver "Deuda del cierre del 2a" más arriba (R6 y
  R11). **R6 bloquea antes de la primera ruta nueva de este cambio**: el sweep de rutas protegidas no
  ve `include_router(prefix=...)`, y es la forma más probable de agregar rutas acá.
- **Depende de**: 2a (para construirse; el 2b, para que una persona lo use). **Habilita**: 4, 5, 6.
- **Bloqueado por**: P16, P19, P24 y P33.
- **Decidir en el design**: cómo se guarda la configuración vigente en cada liquidación (historia);
  si el edificio piloto usa primer y segundo vencimiento con recargo escalonado (R26, pendiente: P19, ProTecc G4) en vez del vencimiento único de R03.
- **Que intente romper el rompedor**: coeficientes de un grupo que no suman 1; una unidad repetida;
  cambiar la tasa y que se pierda la versión anterior; editar la configuración de otro edificio.
- **Terminado cuando**: se cumplen los criterios de HU-A1; un edificio nuevo arranca con los valores
  de `parametros.yaml`; cambiar el archivo no altera edificios existentes.

### 4 · `motor-de-cuenta-corriente` · crítico · explore propio

- **Objetivo**: el corazón de la plata: que cada peso de deuda viva en un solo lugar y nunca se pierda un centavo.
- **Historias**: HU-A9 (correcciones). **Reglas**: R03, R04, R05 (con los créditos que no son pagos,
  D-086), R06, R07, R08, R09 (el caso de uso
  de saldo inicial), R13 (orden de imputación por tipo).
- **Decisiones**: D-010, D-011, D-012, D-015, D-016, D-024, D-046, D-068, D-073, D-074, D-080, D-081,
  D-082, D-086.
- **Propuestas** (entran si se validan): R30 (umbral de saldos chicos), R35 (intereses desde el día
  hábil), R36 (tasa propia de la extraordinaria), R39 (sin intereses ni moroso crítico para unidades del
  consorcio).
- **Entra**: libro de movimientos de sólo agregar, sin campo saldo; obligaciones, pagos e
  imputaciones; intereses simples calculados al registrarse; reparto por **mayor resto** como función
  pública de `proptech_core` (la usa el cambio 6); correcciones con contra-asiento; dos fechas por
  pago (registro y valor); caso de uso de saldo inicial (con detalle por período o total único);
  bloqueo para pagos simultáneos de la misma unidad; umbral mínimo para saldos chicos de redondeo
  (R30, propuesta: entra si se valida y se fija el umbral, ProTecc D3); **la función pura de moroso crítico** (R20, D-074), como consulta sobre
  el libro que usan los cambios 8, 10a y 10b; el saldo excluye todo movimiento generado por una
  emisión anulada, incluidos los ajustes de interés que la compensaban (D-073, D-079, D-084, D-085).
  **Contrato mínimo de emisión** (D-086): este cambio define la entidad emisión con lo justo para el
  libro (identificador, período, edificio y estado), y cada movimiento referencia la emisión que lo
  generó; el cambio 7 la completa con la preliquidación, los controles y la distribución. La anulación en sí se construye en el cambio 7: acá se prueba con
  una emisión marcada como anulada en el test.
- **No entra**: la pantalla para confirmar pagos (8); la importación del Excel (5); la emisión (7).
- **Depende de**: 2a y 3 (el menú de intereses versionado y las marcas que usan R35, R36 y R39).
  **Habilita**: 5, 6, 7.
- **Bloqueado por**: P10, P11, P21, P31, P34 y P42 (la sesión con un contador o administrador).
- **Deuda técnica del 1b** (D-053): limpiar el `except TypeError` que no se alcanza en
  `leer_parametros` y verificar con un test que `Dinero` rechaza ceros de más (`1.0000`).
- **Decidir en el design** (y en su explore): el modelo de tablas del libro; cómo se bloquea la
  cuenta durante una imputación; el desempate determinista del mayor resto.
- **Que intente romper el rompedor**: dos pagos simultáneos a la misma unidad; un pago parcial
  seguido de otro que completa; un pago mayor a la deuda; un pago con fecha valor anterior a una
  corrección; intereses sobre intereses; un reparto que pierde o gana un centavo; editar o borrar un
  movimiento por SQL directo; una obligación de una liquidación anulada que sigue sumando al saldo; una
  unidad con una sola liquidación vencida que la función de R20 marca como moroso crítico.
- **Terminado cuando**: pasan los tests mínimos de R03 a R08 y R20, los del caso de uso de saldo
  inicial de R09 y los de imputación de R13 (los de R09 sobre el borrador y el importador son del cambio
  5, los de R13 sobre bloques y multas, de los cambios 6 y 7, y el de R20 con un pago revertido, del
  cambio 8). Los tests de R05 con condonación o ajuste de interés y los de R06 con una expensa arman
  esos créditos y esa expensa a mano en el test, igual que la emisión anulada; los cambios 7, 8 y 10b
  los repiten con lo real; hay pruebas de propiedades del
  mayor resto (la suma siempre da exacta); el test de concurrencia contra PostgreSQL real pasa; un
  intento de modificar un movimiento rebota.

### 5 · `importacion-desde-excel` · crítico (D-077)

- **Objetivo**: cargar un edificio real desde su Excel sin tipear nada.
- **Historias**: HU-A2. **Reglas**: R09.
- **Decisiones**: D-015, D-029, D-068, D-082, D-083.
- **Entra**: plantilla de Excel con una hoja opcional de saldos por período (unidad, concepto,
  período, vencimiento, monto, interés acumulado; R09, D-082), y la acción "sin saldos previos" para un edificio
  nuevo; la hoja principal con piso, departamento, tipo, propietario, contacto, coeficiente, saldo
  inicial (sólo capital) e interés devengado (que no genera interés, D-083); validación fila por fila con informe de errores; carga atómica (todo o nada); detección
  de reimportación; saldos en un **borrador** que no toca la cuenta corriente, comparado **unidad por
  unidad** contra el listado del administrador, con aceptación registrada de las diferencias y cierre
  del importador al confirmar (D-068); saldos iniciales usando el caso de uso del cambio 4.
- **No entra**: importar gastos o cargos (6).
- **Depende de**: 3, 4. **Habilita**: 7 y el test de M1.
- **Bloqueado por**: P24 (coeficientes de grupos parciales).
- **Que intente romper el rompedor**: un archivo con columnas cambiadas de lugar, celdas vacías,
  números con coma y con punto, coeficientes que suman 0,9999; el mismo archivo subido dos veces; un
  archivo enorme; un archivo que no es Excel; dos errores de signo opuesto en dos unidades que dan el
  total correcto; importar de nuevo con el importador cerrado.
- **Terminado cuando**: se cumplen los criterios de HU-A2; un archivo con un solo error no carga
  nada y lo informa; la suma importada coincide con la del archivo; cada diferencia por unidad se
  muestra aunque el total coincida.

### 6 · `gastos-y-cargos`

- **Objetivo**: cargar los gastos del mes y los cargos de cada unidad, listos para liquidar.
- **Historias**: HU-A3 (carga manual, incluido el sueldo del encargado), HU-A3b. **Reglas**: R01
  (reparto de cada gasto en su grupo, usando el mayor resto del cambio 4), R12 (la clave de factura
  `cuit + ptoVta + tipoCmp + nroCmp`, que usa el control de duplicados del 7), R13, R14, R16, R22.
- **Propuestas** (entran si se validan): R38 (ingresos del consorcio) y las **consultas** que usan los
  controles de R34 "gasto mensual obligatorio faltante" e "ingresos mayores que los gastos" (el control
  en sí lo arma el cambio 7).
- **Decisiones**: D-013, D-024, D-025, D-026, D-028, D-041, D-061, D-075, D-078, D-082.
- **Entra**: proveedores; gastos con sus **cuatro estados** (borrador, sin IA, en revisión y aprobado,
  D-075), con categoría, grupo y tipo ordinario o extraordinario (acá la carga es manual: los estados
  sin IA y en revisión se usan desde el cambio 14, pero ya existen y se prueban); sueldo del encargado como gasto; cargos particulares sueltos o importados desde
  Excel; aprobación; nota de crédito asociada a la factura que corrige, con su monto topeado al de
  esa factura (R22, ProTecc H1).
- **No entra**: la lectura de facturas por QR e IA (14): acá la carga es manual.
- **Depende de**: 3, 4. **Habilita**: 7, 14.
- **Bloqueado por**: P15, P17, P25, P36 y P37.
- **Que intente romper el rompedor**: un gasto sin categoría que se aprueba; un cargo particular que
  termina repartido entre todos; un gasto de otro edificio; un importe con tres decimales; aprobar
  dos veces el mismo gasto; borrar una categoría con gastos (sólo se desactiva, R16); una nota de
  crédito que supera el monto de su factura; una nota de crédito sin factura asociada.
- **Terminado cuando**: se cumplen los criterios de HU-A3 (manual) y HU-A3b; un gasto en borrador,
  sin IA o en revisión no aparece en ningún cálculo; sólo el aprobado entra.

### 7 · `liquidacion-y-emision` · crítico · explore propio

- **Objetivo**: convertir los gastos del mes en la expensa de cada unidad, revisable antes de emitir.
- **Historias**: HU-A4, HU-A5. **Reglas**: R01, R03, R06, R07, R13, R15, R16, R17, R19, R24, R34.
- **Propuestas** (entran si se validan, como código simple; el motor llega en el 6b, D-089): R14
  (cargo recurrente), R35 (vencimiento corrido en el PDF), R37 (los dos importes en el PDF), R38 (bloque de ingresos en la expensa), R40 (períodos en
  orden).
- **Decisiones**: D-024, D-031, D-041, D-047 (puntos 5, 7 y 8), D-055, D-066, D-067, D-069, D-070,
  D-073, D-074, D-075, D-078, D-079, D-080, D-081, D-082, D-084, D-085.
- **Entra**, en dos bloques de tareas:
  - **Preliquidación (sin efectos)**: reparto de los gastos aprobados, fondo de reserva, cargos
    particulares e intereses, agrupado por ordinaria y extraordinaria y por categoría; no escribe deuda.
  - **Emisión (con efectos)**: congela importes y configuración, genera una obligación por unidad y
    período en una sola transacción y encola el PDF en el worker (el email llega en el cambio 13).
  - **Estados de la liquidación** (R17, D-073, D-074): borrador, emitida, distribuida y anulada (sólo
    desde emitida), guardados como eventos de sólo agregar. **Anular** es un cambio de estado con motivo
    y responsable: no borra movimientos. **Distribuir** es una acción manual del administrador, y un
    **puerto de distribución** registra el evento para que después lo llamen el portal (11) y el email
    (13). Después de distribuida, sólo se corrige con un ajuste (R08).
  - **Controles antes de emitir** (R34, D-069): la lista con bloqueantes y advertencias, la emisión
    con alertas aceptadas y su registro, y los controles sobre los gastos: saldos iniciales sin
    validar, factura duplicada, gastos en revisión (bloqueante), gastos sin IA (advertencia) y, sobre
    las consultas que expone el cambio 6, gasto mensual obligatorio faltante e ingresos mayores que
    los gastos. Los controles de pagos, extracto y contactos los suman los cambios 8, 9 y 13.
  - **Links de descarga firmados y con vencimiento** (D-070): el PDF de la expensa nunca tiene una
    dirección pública; este cambio arma el mecanismo que reusan los demás.
  - **Reglas propias del edificio sin motor** (D-089): si se validan, el importe con descuento de la
    bonificación para el PDF (R37) y el cargo recurrente del reglamento (R14) se construyen como código
    simple; el 6b los migra al motor después.
  - Plantilla del PDF de la expensa (pasa por la skill impeccable), con el código corto de la unidad
    en el concepto sugerido de la transferencia (R19, ProTecc A1/E3).
- **No entra**: el portal donde el vecino la ve (11); los avisos de vencimiento (13).
- **Depende de**: 5, 6. **Habilita**: 6b, 8, 10a, 11, 12, 13, 14 y el test de M1.
- **Bloqueado por**: P26, P27, P28, P38 y P39, y la normativa de la expensa en Mendoza (D-060).
- **Deuda del 1c, con dueño este cambio (D-091, L-011, L-012)**: **F2c es bloqueante antes de
  registrar la primera tarea real del worker** (el encolado del PDF de la expensa, que es la primera
  vez que el worker tiene un efecto real): hoy `asyncio.wait_for` sólo corta la espera, no el hilo que
  corre la operación de base, y si la base queda congelada más que la ventana de reintentos, el hilo
  del primer intento puede confirmar su efecto después de que el trabajo ya se marcó agotado. Se
  resuelve con un corte del lado de la base (`statement_timeout` o equivalente) y una cota propia por
  tarea, no la `COTA_OPERACION_S` genérica del 1c. También quedan a cargo de este cambio, sin ser
  bloqueantes: F12b (el `sys.excepthook` del worker no cubre una excepción de terceros envuelta por
  otra capa) y que `repr(RedisSettings)` no muestre la contraseña (no se demostró que llegue a un log,
  pero tampoco está resuelto).
- **Prerrequisito**: investigar qué exige la normativa de Mendoza para una expensa antes de cerrar
  el PDF (ProTecc H4, Q12 de Alberto, D-060); Alberto cita la Ley 941 de CABA sólo como ejemplo, no aplica acá.
- **Decidir en el design** (y en su explore): la frontera de la transacción; **qué pasa si falla el
  encolado del PDF después de emitir** (como mínimo, estado por emisión y una forma de reprocesar);
  **qué pasa si falla el extracto bancario o el servicio de IA el día de emitir** (R24, principio 6
  de Alberto, ProTecc A4): la liquidación sale igual; los gastos "sin IA" no entran y generan una
  advertencia, y los "en revisión" bloquean salvo aceptación (D-075). Los tests de R24 arman a mano
  gastos en esos estados, sin esperar a los cambios 9 y 14.
- **Que intente romper el rompedor**: emitir dos veces el mismo período; una preliquidación que
  escribe algo; lo prorrateado que no da los gastos menos notas de crédito e ingresos, más el fondo; Redis caído justo
  después de emitir; renombrar una categoría después de emitir; anular una liquidación después de
  que fue distribuida; anular sin motivo; anular y que algún movimiento del libro cambie; distribuir
  dos veces; emitir con un bloqueo activo sin aceptarlo; aceptar una alerta sin que quede
  registro.
- **Ajuste de interés y anulación**: el test de R17 que excluye un ajuste de R11 se arma acá con un
  ajuste cargado a mano en el test, y el cambio 8 lo repite con el ajuste real (D-084, D-085).
- **Terminado cuando**: se cumplen HU-A4 y HU-A5; **con los datos del piloto, reproduce su última
  liquidación al centavo** (test de aceptación de M1; si los datos todavía no están, se corre con el
  edificio de ejemplo y M1 queda pendiente de ese test).

---

## M2 · Cobra

### 8 · `pagos-informados` · crítico

- **Objetivo**: que el vecino informe su pago con el comprobante y el administrador lo confirme en un clic.
- **Historias**: HU-A6, HU-V4. **Reglas**: R05, R11, R18, R19, R34.
- **Propuestas** (entran si se validan): R25 (reimputación), R37 (la bonificación por pronto pago se
  registra al confirmar el pago, D-080, como código simple hasta el 6b), R39 (las unidades del consorcio no reciben bonificación).
- **Decisiones**: D-017, D-018, D-029, D-056, D-057, D-069, D-070, D-074, D-080, D-082, D-083, D-084,
  D-085.
- **Ajuste de interés**: el ajuste de R11 nace acá; el test de R17 que lo excluye al anular su emisión
  se corre acá con el ajuste real.
- **Entra**: subir comprobante; lectura con IA que precarga monto, fecha y número de operación;
  número de operación único por edificio; bandeja de confirmación y rechazo con motivo; imputación
  con la fecha de la transferencia usando el motor del cambio 4; repartir un pago entre varias
  unidades de la misma persona; guardar el CBU de origen de cada pago confirmado cuando se conoce
  (R19, ProTecc A1/E3; la sugerencia por CBU llega con el extracto, cambio 9); estado **revertido** para un pago
  confirmado que el banco devuelve, con su contra-movimiento (R18, ProTecc D4); asistente de
  reimputación entre dos unidades, con los dos movimientos enlazados en una sola transacción (R25,
  propuesta: entra si se valida, ProTecc B2); los comprobantes se descargan con links firmados y con vencimiento
  (D-070); el control "pagos sin confirmar" en la lista antes de emitir, como advertencia (R34).
- **Pantalla**: la del vecino para subir el comprobante y ver su estado (HU-V4) se construye acá, y
  pasa por la skill impeccable; el resto del portal es del cambio 11.
- **No entra**: el cruce con el extracto (9).
- **Depende de**: 7. **Habilita**: 6b, 9, 10a, 13.
- **Bloqueado por**: P12, P27, P29 y P40, y la elección del proveedor de IA (datos de comprobantes con CBU y CUIT).
- **Moroso crítico**: después de revertir o reimputar, los tests usan la función de R20 del cambio 4
  (D-074): la unidad pasa a cumplirla o deja de cumplirla, sin esperar al cambio 10a.
- **Decidir en el design**: el proveedor de IA para leer comprobantes (detrás de un puerto).
- **Que intente romper el rompedor**: el mismo comprobante dos veces o para dos unidades; un
  comprobante de otro edificio; una confirmación tardía que genera intereses; doble clic en confirmar;
  una imagen con texto que intenta darle órdenes a la IA; revertir un pago que no está confirmado;
  reimputar y que falle a mitad de camino (no tiene que dejar un solo movimiento aplicado); abrir el
  comprobante de otra unidad con un link modificado o vencido.
- **Terminado cuando**: se cumplen HU-A6 y HU-V4; la fecha que cuenta para los intereses es la de la
  transferencia.

### 6b · `motor-de-reglas` · explore propio

- **Objetivo**: dejar andando la base del motor de reglas cuando haya reglas validadas que lo necesiten
  (D-087, D-089). Está fuera del camino a M1: ninguna regla vigente pasa por el motor.
- **Reglas**: R33 (datos completos y tipados antes del motor). **Decisiones**: D-064, D-066, D-067,
  D-080, D-085, D-087. Detalle en `13_motor_de_reglas.md`.
- **Entra**: el módulo `politicas`, el puerto de políticas, el adaptador de GoRules ZEN, el validador en
  sus dos momentos, las reglas versionadas por edificio, el editor (jdm-editor) en el frontend con el
  esquema de permisos que defina P22 (propuesta: dos niveles) y "repetir el mes pasado" contra datos de prueba. Migra al motor las reglas que se hayan validado y construido como código simple en el 7 y el 8
  (cargo recurrente R14, bonificación R37), y suma los controles propios del edificio (R34).
- **Prerrequisito del explore**: bajar y revisar el demo BRE, y probar jdm-editor con React 19.3 y
  `antd` 5.21.2 (pendientes de `13_motor_de_reglas.md`).
- **Depende de**: 7 y 8. **Habilita**: la migración al motor de las reglas propias que se hayan
  construido como código simple (R14, R37) y los controles propios del edificio.
- **Bloqueado por**: P22.
- **Que intente romper el rompedor**: un dato mal tipado que hace caer la tabla a la fila por defecto;
  una respuesta vacía; una regla que devuelve plata como número; editar la estructura con permiso de
  sólo valores; leer las reglas de otra administración.
- **Terminado cuando**: los tests mínimos de R33 pasan contra ZEN real como rechazo del validador (y que una
  respuesta inválida frene la emisión, que ya existe desde el 7), y una regla de prueba se
  guarda, se versiona y se evalúa de punta a punta; una regla migrada da los mismos importes que su
  versión en código simple.

### 9 · `extracto-bancario`

- **Objetivo**: que el administrador valide los pagos informados contra el banco.
- **Historias**: HU-A7. **Reglas**: R11, R34.
- **Entra**: subir el extracto en CSV o Excel; un adaptador por banco y formato; marcar coincidencias;
  movimientos sin comprobante como fondos pendientes; un movimiento no confirma dos pagos;
  sugerencias de confianza alta por código de unidad o por CBU histórico (R19); el
  control "extracto incompleto" en la lista antes de emitir, como advertencia (R34, D-069).
- **Depende de**: 8.
- **Bloqueado por**: P9 y P30.
- **Prerrequisito**: responder qué traen los extractos de los bancos que usan los administradores
  de Mendoza (CBU o nombre del originante, concepto completo): es la pregunta P9 (Q2 de Alberto),
  prioridad 0 de su documento, y condiciona si R19 (código de unidad y CBU histórico) funciona como
  está pensado (D-063).
- **Que intente romper el rompedor**: formatos de distintos bancos; el mismo extracto dos veces; dos
  pagos con el mismo importe y fecha.
- **Terminado cuando**: se cumplen los criterios de HU-A7.

### 10a · `morosidad`

- **Objetivo**: ver quién debe, cuánto y desde cuándo.
- **Historias**: HU-A8. **Reglas**: R20 (presentación). **Decisiones**: D-058, D-074, D-077.
- **Entra**: listado por unidad calculado desde las imputaciones; exportación a Excel; presentación
  del **moroso crítico** (dos o más liquidaciones vencidas con saldo impago, sin bloqueo de
  amenities), que ya viene calculado por la función del cambio 4 (R20, ProTecc M1). Es de sólo
  lectura: no escribe en la cuenta corriente.
- **No entra**: la condonación, la gestión judicial y el libre deuda (10b).
- **Depende de**: 8. **Habilita**: 10b, 11.
- **Que intente romper el rompedor**: una deuda pagada en partes que sigue figurando; diferencias
  entre la pantalla y el Excel; una unidad con una sola liquidación vencida marcada como moroso
  crítico; una pantalla que muestra un moroso crítico distinto del que da la función del cambio 4.
- **Terminado cuando**: se cumplen los criterios de HU-A8.

### 10b · `condonacion-judicial-y-libre-deuda` · crítico

- **Objetivo**: las operaciones de morosidad que escriben en la cuenta corriente o tienen peso legal.
- **Historias**: HU-A10 (certificado de libre deuda), HU-A11 (condonación y gestión judicial).
  **Reglas**: R21. **Decisiones**: D-059, D-074, D-077, D-078.
- **Propuestas** (entran si se validan): R29, R31, R41 (va con R31).
- **Entra**: condonación de interés como movimiento con motivo, sin borrar el recargo original (R29,
  falta decidir quién aprueba: P20, ProTecc B5); marca de "gestión judicial" por unidad que frena los
  recordatorios automáticos y la saca del cálculo de moroso crítico (R31, ProTecc G2); **certificado de
  libre deuda** por venta de unidad, con fecha de corte, saldo calculado desde la cuenta corriente y
  pagos en revisión listados aparte (R21, ProTecc G3). La marca de gestión judicial se expone como
  consulta para que la usen el cambio 13 (avisos) y la **exclusión en la función de R20**, que este
  cambio agrega a la función del cambio 4 (D-078).
- **Ciclo**: completo, con aprobación de uno de los dos socios antes de codear (D-077, D-094). Si R29 sigue sin saber quién
  aprueba una condonación, esa parte se separa y el resto avanza.
- **Depende de**: 10a. **Habilita**: 13.
- **Bloqueado por**: P14, P20 y P32.
- **Que intente romper el rompedor**: una condonación que borra el recargo; condonar sin motivo; una
  unidad en gestión judicial que sigue contando como moroso crítico; un
  certificado de libre deuda que incluye una estimación del período en curso; generar el certificado
  dos veces y que cambie el saldo sin que cambie la cuenta corriente.
- **Terminado cuando**: se cumplen los criterios de HU-A10 y los tests mínimos de R21, y HU-A11 con
  los de R29 y R31 si se validaron.

### 11 · `portal-del-vecino`

- **Objetivo**: que el vecino entienda su expensa y pague desde el celular.
- **Historias**: HU-V1 (pantallas), HU-V2, HU-V3, HU-V5. **Reglas**: R16 (presentación).
- **Entra**: todas las unidades de la persona juntas; deuda y vencimiento; expensa por ordinaria,
  extraordinaria y categoría, con la comparación contra el mes anterior; descarga de PDFs con links
  firmados y con vencimiento (D-070); app instalable. Pasa por la skill impeccable.
- **Depende de**: 10a y 2b (el vecino tiene que poder entrar). **Habilita**: 12.
- **Distribución** (D-074): la primera vez que un vecino abre una liquidación, el portal llama al
  puerto de distribución del cambio 7.
- **Que intente romper el rompedor**: ver la unidad de otro vecino; números distintos a los del
  administrador; un iPhone sin instalar la app; pantalla de 320 px; abrir un link de descarga
  vencido, modificado o de otra unidad.
- **Terminado cuando**: se cumplen HU-V1, V2, V3 y V5.

### 12 · `vista-del-consejo` · HIGH (D-087)

- **Objetivo**: transparencia para el consejo de propietarios.
- **Historias**: HU-C1.
- **Entra**: morosidad, gastos y liquidaciones en sólo lectura.
- **Depende de**: 11.
- **Que intente romper el rompedor**: cualquier acción de escritura desde un usuario del consejo.
- **Terminado cuando**: se cumple HU-C1.

### 13 · `avisos-por-email`

- **Objetivo**: avisar antes del vencimiento y en mora, sin molestar de más.
- **Historias**: HU-V6. **Reglas**: R34.
- **Propuestas** (entran si se validan): R27 (aviso corrido al día hábil), R28 (contactos válidos), R30 y
  R39 (ver abajo).
- **Entra**: puerto de email con su adaptador; aviso de vencimiento y de mora; un aviso por evento,
  con clave de idempotencia; no avisar a quien ya pagó; un aviso que cae en sábado, domingo o
  feriado se reprograma al primer día hábil siguiente (R27, propuesta: entra si se valida, ProTecc W3); validar el
  contacto al cargarlo y, si un envío rebota, mostrar al administrador la lista de "unidades sin
  contacto válido" (R28, propuesta: entra si se valida, ProTecc W4); el control "unidades sin contacto válido" en la
  lista antes de emitir, como advertencia (R34, D-069).
- **Depende de**: 8 y 10b (la consulta de gestión judicial, D-078).
- **Bloqueado por**: P41.
- **Propuestas que también se prueban acá, si se validan**: R30 (no avisar mora por saldos debajo del
  umbral) y R39 (las unidades del consorcio no reciben avisos de mora).
- **Gestión judicial**: si R31 se valida y el 10b la construye, una unidad marcada en gestión judicial
  no recibe avisos automáticos de mora; este cambio lo prueba.
- **Distribución** (D-074): cuando sale el primer email de una liquidación, el cambio 13 llama al puerto
  de distribución del cambio 7.
- **Decidir en el design**: el proveedor de email (detrás de un puerto, sin costo o el más barato, D-043).
- **Que intente romper el rompedor**: el worker que se cae a mitad del envío; dos avisos el mismo día;
  aviso de mora a alguien con el pago confirmado; un aviso programado para un sábado que no se mueve;
  un contacto con formato inválido que igual queda en la lista de envío.
- **Terminado cuando**: se cumple HU-V6.

---

## M3 · Piloto

### 14 · `lectura-de-facturas`

- **Objetivo**: que el administrador cargue una factura con una foto.
- **Historias**: HU-A3 (factura con QR e IA). **Reglas**: R12, R16, R34.
- **Decisiones**: D-019, D-069, D-070.
- **Propuestas** (entran si se validan): R23 (control de monto atípico, con su umbral, P21).
- **Entra**: lectura del QR de ARCA (los dos dominios); la IA completa concepto, período, categoría
  y grupo; factura duplicada frenada; aviso si el receptor no es el consorcio; nunca aprobado sin confirmación (borrador, sin IA o en
  revisión, D-075);
  registro del costo de cada llamada a la IA; control de monto atípico contra el historial de ese
  proveedor en el edificio, para marcar para revisión una factura que la IA pudo leer mal (R23,
  propuesta: entra si se valida y se fija el umbral, ProTecc A2); las facturas se descargan con links firmados y con
  vencimiento (D-070); la lectura deja cada gasto en el estado que corresponde (sin IA o en revisión),
  y los controles del cambio 7 lo toman sin cambios.
- **Depende de**: 6 y 7 (controles y links firmados).
- **Bloqueado por**: P12, P21 y la elección del proveedor de IA.
- **Decidir en el design**: el proveedor de IA (puede ser el mismo del cambio 8).
- **Que intente romper el rompedor**: el ejemplo oficial de ARCA; una factura en dólares; una sin QR;
  una con instrucciones escondidas para la IA; la misma factura dos veces; un monto leído diez veces
  más grande o más chico que el historial del proveedor.
- **Terminado cuando**: se cumple HU-A3 en su parte de factura; decodifica el ejemplo oficial.

### 15 · `piloto-en-paralelo`

- **Objetivo**: demostrar que PropTech reemplaza el método actual del edificio piloto.
- **Entra**: carga de los datos reales del piloto; un mes completo en paralelo; comparación al
  centavo; prueba de restauración de un backup; evidencia de aislamiento entre administraciones y alcance por edificio.
- **Deuda del 1d, con dueño este cambio** (L-012): ver "Deuda del cierre del 1d" más abajo (F4, F5,
  F6, F8 y "14 copias no son 14 días").
- **Deuda del 2a con dueño este cambio** (L-012, D-098): ver "Deuda del cierre del 2a" más abajo (V2-3,
  V3-4 (M2), V3-6, V3-7 y el chequeo 5 completo: los 25 archivos de test sin mutar y la verificación de
  arranque de las políticas de las tablas de negocio, prometida como deuda de este cambio por decisión
  de Juani).
- **Deuda nueva, origen "revisión del 2c, 16/10/2026"**: `REDIS_PASSWORD` va en la línea de comando de
  `redis-server` (`--requirepass` en `compose.yaml`), visible en `docker inspect` y en `/proc/1/cmdline`;
  y todas las contraseñas de los servicios quedan en el `Config.Env` de `docker inspect`. Se suma a la
  contraseña del rol de arranque en el entorno de `migraciones`, ya con dueño 15.
- **Depende de**: todos los anteriores y los datos del piloto (P1).
- **Bloqueado por**: P1 (el edificio piloto) y P12.
- **Terminado cuando**: el cierre del mes coincide con el del administrador y un backup se restauró
  con éxito.

---

## Deuda técnica de las auditorías del 13/10

Lo que dejaron las auditorías de código de Alberto, con el cambio que lo resuelve (D-089). Lo del 1c y
el 1d ya está en sus tareas (D-090).

| Deuda | Cambio |
|---|---|
| `Dinero` copiable y serializable (`__reduce__`, `__copy__`, `__deepcopy__`), pyyaml 6.0.3, rechazo de float y Decimal al encolar, logs de ARQ sin argumentos, logs de error de Caddy, Alembic sin apagar loggers, red de egreso del worker, SecretStr, un solo engine y su pool, uvicorn sin log de acceso y con `--proxy-headers`, línea de base sobre un clon con historial | 1c |
| Restauración con `-U` y la ruta del `.env`, retención que no borra el ciclo en curso, rechazo de uid 0, shellcheck en el CI, `-p proptech` en el humo | 1d |
| Roles de PostgreSQL para RLS (migrador y aplicación) | 2a |
| Cabeceras de seguridad en Caddy, volúmenes de Caddy, CI con `pull_request`, límites de tiempo y gitleaks fijado por digest, endurecimiento de contenedores, tabla de variables del README | 2c (no hacen al candado, D-097) |
| CSP en Next | 2b (una CSP sin pantallas no prueba nada; la primera es la de login) |
| Dependabot | 15, propuesto (no lo necesita ni el candado ni el login; va con las imágenes por digest; lo confirma E4 de la aprobación del 2a) |
| `naming_convention` en la base de SQLAlchemy, tipos `Porcentaje` y `Superficie`, versión de la semilla como `Literal[1]`, pydantic declarado como dependencia directa, app con `--factory`, tope de lectura del YAML, test de chmod salteado en Windows, `.gitignore` ampliado, healthcheck de la web contra 127.0.0.1 | 3 |
| Imágenes publicadas en un registro con tag de SHA y despliegue que sólo hace pull, imágenes fijadas por digest | 15 |

### Deuda del cierre del 1c (auditoría del 14/10, D-091)

La que dejó el rompedor en su vuelta final del 1c, aceptada por Juani como "OK con deuda anotada".
Dueño asignado por el primer cambio que de verdad necesita que esté resuelta (L-012), no por el que
suena más obvio.

| Deuda | Por qué no bloquea | Cambio |
|---|---|---|
| F2c: un trabajo agotado por base congelada confirma su efecto cuando la base vuelve (el hilo del primer intento, abandonado por `wait_for`, confirma tarde) | Hoy el efecto es vacío y la idempotencia frena el reencolado | 7 (bloqueante antes de registrar su primera tarea real) |
| F12b: el `sys.excepthook` del worker no ve excepciones de terceros envueltas (cadena, `ExceptionGroup`, `OSError`) | Sin camino real hoy | 7 |
| `repr(RedisSettings)` muestra la contraseña | No se demostró que llegue a un log | 7 |
| F13: `/salud-web` informa `sin_conexion` cuando una dependencia está congelada en vez de lenta | Cumple la letra de la spec y nadie lo consume aún | resuelto en 1d |
| `salud_degradada` duplicado (dos líneas por pedido colgado) | Sólo ensucia los logs | resuelto en 1d |
| F7c: el parseo de un traceback crudo saca datos a `tipo_error`/`traza` con formas muy particulares | Formas muy raras, confianza baja | resuelto en 1d |
| F3b: `_ruta_de` usa un atributo interno de FastAPI 0.143 (`effective_route_context`) | FastAPI fijado `<0.144` y un test lo detecta | quien suba FastAPI |
| M12 a medias: `url_sqlalchemy()` devuelve `str` con la contraseña; Alberto pidió un objeto `URL` renderizado sólo en el borde | Impacto bajo | 2a (reescribe `configuracion.py` para las credenciales por rol) |
| Redis congelado frena el worker mientras dura | Se recupera solo | aceptar, sin dueño |
| `POSTGRES_PORT` y `REDIS_PORT` estrictos (cambia el comportamiento laxo del 1b) | En línea con L-008 | aceptar, sin dueño |

### Deuda del cierre del 1d (auditoría del 14/10, vuelta 3, D-095)

La que aceptó el auditor al cerrar el 1d como "OK con deuda anotada" (B4-bis quedó resuelto en la
vuelta 3 y no entra en esta tabla). Dueño asignado por el primer cambio que de verdad necesita que
esté resuelta (L-012), no por el que suena más obvio.

| Deuda | Por qué no bloquea | Cambio |
|---|---|---|
| F4: con el reloj del host atrasado, la retención por nombre deja 1 backup real de 7 | Cumple la letra del escenario "Reloj atrasado" | 15 |
| F5: `respaldos` ignora SIGTERM (10 s y `KILL`) | La `.parcial` se borra sola al arrancar | 15 |
| F6: un 503 puede salir sin `salud_degradada` (1 de 18) | Ventana de menos de 1 ms | 15 |
| F8: líneas que no son JSON en el log de `respaldos` | No llevan secretos | 15 |
| "14 copias" no son 14 días si hay muchos reinicios | Cumple la spec (retención por cantidad, no por tiempo) | 15 |
| F7, resto: "aparece uno solo" no se verifica; los `[ ]` de los pasos 11 y 13 del humo fallan sin decir cuál | No esconde fallas | 2c (confianza media) |
| El humo nunca congela las dos dependencias de salud a la vez | Lo cubren los unitarios de 5.1 | 2c |
| PID 1 no root: el rojo se mostró sólo para `redis`, no para `worker` ni `respaldos` | El assert es idéntico en los tres y lo que se probó es la lectura de `/proc/1/status` | 2c (endurecimiento de contenedores) |
| La 8.1 (la corrida equivalente al CI) corrió en paralelo y no "en este orden", como pide la tarea (vueltas 2 y 3) | Todos los resultados dieron verde y el repo real se recorrió de nuevo al final | 2a y 2c (cada corrida de cierre dice el orden y por qué) |

### Deuda del cierre del 2a (auditoría vuelta 3, D-098)

La que dejó el rompedor al cerrar el 2a, aceptada por Juani como "OK con deuda anotada". Las filas
V3-1, V3-2 y V3-4 (M8 y M5) de la tabla original de la vuelta 3 se cerraron en la vuelta 4 (opción B,
D-098) y no entran acá; V3-4 (M2) sigue abierta. Dueño asignado por el primer cambio que de verdad
necesita que esté resuelta (L-012), no por el que suena más obvio.

| Deuda | Por qué no bloquea | Cambio |
|---|---|---|
| R5: el contrato de error del endpoint de asignación (`unidad_id` del vecino) | Es contrato de error, no fuga: no escribe nada y el log no filtra; el endpoint es inalcanzable en producción hasta el login (401 siempre) | 2b (C-05b) |
| R6: el sweep de rutas protegidas no ve `include_router(prefix=...)` | Hoy no hay fuga (`app.py` sin prefix) | 3 (C-06), bloqueante antes de su primera ruta nueva |
| R9: la igualdad de tiempo entre 403 y 404 | Necesita una identidad autenticada de la misma administración, que no existe hasta el login | 2b (C-05b) |
| R11: "el id lo genera siempre el servidor" en las altas | Hoy verificado sin agujero: no hay ninguna alta de complejo ni unidad todavía | 3 (C-06) |
| V2-3: `roles antes` no revoca membresías de `proptech_app`, y la verificación de arranque no las mira | No rompe la letra (D2 promete reparar atributos, no membresías); exige un superusuario que otorgue la membresía a mano y que la app además ejecute `SET ROLE` o DDL | 15 (piloto), antes de operar la base con el superusuario |
| V2-5: la API no nombra en el log por qué no arrancó | La garantía (no arrancar) se cumple y la falla no queda escondida; sólo falta la causa nombrada | 2c (C-05c), junto con el humo con pasos nombrados |
| V2-7: el registro de `@accion_sensible` se pisa con la misma `Accion`; el sweep invoca una tabla paralela; el test de `test_auditoria_transaccion.py:416` no puede dar rojo | Hoy hay un solo caso, así que no hay agujero | 2b (C-05b), antes del primer segundo caso con una misma acción |
| V3-4 (M2): la rama `invalidate` de `_checkin` no tiene test | Sin camino real hoy: hace falta un corte de base con tráfico real | 15 (piloto), antes de tener cortes de base con tráfico real |
| V3-5: ningún test pasa por el cableado real de R7 y R8 en el arranque | El arranque real activa las dos protecciones hoy; lo que falta es un test que lo exija, para que una refactorización no las pierda con todo en verde | 2b (C-05b), antes de tocar `lifespan` u `on_startup` |
| V3-6: sin inodos, `--salud` da 0 (no se puede ni crear la marca) | Mucho más raro que el disco lleno; queda declarado acá en vez de con un test | 15 (piloto), revisar con el monitoreo del servidor real |
| V3-7: `despues()` espera sin límite un lock de `auditoria` (sin `lock_timeout`) | Hace falta tráfico real y un redeploy en caliente; hoy no hay ninguno de los dos | 15 (piloto), antes del primer redeploy con usuarios |
| V3-8: flake de `unitarios/test_worker_tenant.py` (9% de las corridas, `"123"` en los metadatos del log) | No esconde una fuga hoy, aunque entrena a ignorar justo el test de L-007 | 2c (C-05c), antes de activar el CI en pull requests |
| V3-9: el test de R7 se cuelga en vez de dar rojo (sesiones sin `finally`) | Hoy R7 está cerrado; el riesgo es si vuelve a romperse y el CI se cuelga en vez de mostrar el rojo | 2c (C-05c), junto con el límite de tiempo del CI |
| V3-14: `POSTGRES_APP_USER` acepta un nombre que la migración no conoce | Falla ruidoso, sin agujero de seguridad | 2c (C-05c), con la tabla de variables del README |
| V3-15: README desactualizado (el worker sí tiene salida, el 1d no está "Propuesto", faltan las contraseñas distintas) y el humo no mira `relrowsecurity` | Dos frases falsas y un requisito no escrito, no una fuga | 2c (C-05c), con la tabla de variables del README y el humo con pasos nombrados |
| Chequeo 5: 25 archivos de test de RLS, permisos y rutas que nadie abrió ni mutó | El comportamiento de aislamiento sí se probó de caja negra con scripts propios; lo que no se sabe es si esos tests pueden dar rojo | 15 (piloto), una pasada de mutación antes de cargar datos reales |
| Chequeo 5: ninguna verificación de arranque mira las políticas de las tablas de negocio (`complejo`, `unidad` y las otras), sólo las de `auditoria` | El diseño (D2) sólo promete esa verificación para la auditoría; para el resto no hay promesa rota, pero Juani decidió prometerlo | 15 (piloto) — decisión de Juani, no deuda sin dueño (D-098) |
| D-1: de las 7 comparaciones de `_verificar_politica_de_auditoria`, 5 no tienen test que las exija (nombre, PERMISSIVE, comando, roles, WITH CHECK) | Hoy el código anda (caja negra); son mutantes vivos, no una falla observada | 2b (C-05b), junto con V3-5 |
| D-2: la primera FK legítima hacia `auditoria` frena todo arranque (exit 1 en `despues`, con `SQLSTATE 0A000` y no el texto "FK") | Es lo diseñado (ruidoso en vez de ciego), pero nadie lo documentó como restricción del esquema | 2b (C-05b), antes de diseñar cualquier tabla que referencie `auditoria` |
| D-4: `vuelta-3/arbol/backend/.venv` de la copia del rompedor es un symlink al `.venv` real del repo; un `uv run`/`uv sync` desde ahí redirige la instalación editable | Hoy no hay daño (el `.pth` volvió a apuntar al repo); es el entorno de trabajo efímero del rompedor, no el repo | orquestador — borrar el symlink o el `arbol/` entero antes de reusar `vuelta-3/mutar.py`, no es un cambio del roadmap |
| D-5: `infra/ci/humo.sh` está en git como `100644` (sin `+x`); el CI lo corre con `bash` y no falla | Corrido a mano como `./humo.sh` da "Permiso denegado"; no afecta al CI | 2c (C-05c), con el humo con pasos nombrados |
| D-6: el test de M5 detecta "sin sonda de TRUNCATE" sólo porque la palabra `"TRUNCATE"` en mayúsculas no aparece en el aviso de catálogo | El caso de la FK lo sigue cubriendo | 2b (C-05b), con D-1 |
| Aviso para el 2b: la primera FK legítima hacia `auditoria` va a frenar cada arranque (V3-2, mismo mecanismo que D-2); contemplarlo antes de agregar cualquier referencia nueva a `auditoria` | Es el comportamiento diseñado, no una falla nueva | 2b (C-05b) |

D-3 (la evidencia de `tasks.md` 13.3 mostraba otro mutante que el M5 original) no entra en esta tabla:
el rompedor sugirió corregirla "en la misma pasada que V3-10", y se corrigió en ese mismo commit
(`3bbd2a6`).

## Pendientes de arranque

- [ ] Pedirle a Alberto los datos del edificio piloto: padrón con coeficientes, facturas y recibo del
  encargado de un mes, y la liquidación de ese mes (P1).
- [x] Contarle a Alberto que los montos van en Decimal, como en su documento (D-046).
- [x] Repositorio limpio y OpenSpec listo.
