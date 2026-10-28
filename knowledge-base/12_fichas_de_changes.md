# Fichas detalladas de los changes

Extra de Active Stack v1 (D-093): el detalle completo de cada cambio del roadmap, sin el estado (que
vive sólo en `CHANGES.md`, la fuente única para saber qué está hecho). Cada ficha es **la entrada del
`/opsx:propose`** de ese cambio: el proponente parte de acá y de los archivos que la ficha cita. **Se
reescribe** cuando cambia el plan; el porqué va a `09_decisiones_y_supuestos.md` (D-045, D-047,
D-049).

El ciclo de cada cambio está en `14_forma_de_trabajo.md`: proponer, construir, romper, auditar y
archivar con commit y push. Un cambio arranca cuando el anterior está archivado.

**Regla transversal para todo cambio con pantallas** (D-102): cada pantalla nueva o modificada lleva su
ayuda "?" con las tres partes (para qué sirve, qué hago acá, qué pasa después), según HU-T1 y la
Always-Help Rule de `DESIGN.md`. Forma parte del "Terminado cuando" de cada ficha aunque la ficha no
lo repita.

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
vea sólo lo suyo, aunque el código tenga un error. P18 conserva D-096; la matriz de P23 se
reemplazó por D-106 en el 2.2a y el método de login por D-107 en el 2b.

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

### 2.2a · `roles-de-la-empresa` · archivado 20/10/2026 · CRITICAL

- **Objetivo**: construir los perfiles y alcances reales de la empresa antes de conectar el login.
- **Reglas y decisiones**: R10, D-076, D-106; Clerk se registra aparte en D-107 y se construye en 2b.
- **Entró**: matriz perfil × alcance, `vinculo` propietario/inquilino en la relación persona-unidad,
  migraciones 0017 y 0018, personal único por persona y alcance y consejo único por persona y
  edificio. El super admin y todo administrador del edificio emiten y configuran; las correcciones
  reservadas y "sin saldos previos" requieren super admin o administrador principal. RLS conserva
  el tenant y la aplicación el alcance por edificio. Asignaciones por edificio sólo por super admin,
  sin `nivel`, con 409 al repetir, 422 por campos ajenos y auditoría de la persona destinataria.
- **No entró**: login ni gestión de usuarios (2b); lecturas de ordinarias para el inquilino y lecturas
  contables (6, 7, 10a, 11, 12); carga del ejemplo y acceso de desarrollo.
- **Firmado por Juani (20/10/2026)**: E1 a E8 en la propuesta; RR-1 a RR-4 con firma propia en
  `610eb4a`. No se extiende esa firma a reglas posteriores por inferencia del brief.
- **Deuda del 2a resuelta**: R5, contrato de error de asignación, tarea 4.2; cuerpo por edificio con
  extras prohibidos y rechazo 422 de `unidad_id` y `vinculo`, también con ids válidos ajenos.
- **Depende de**: 2a y 3a/3b, cuya configuración y textos adapta. **Habilita**: 2b.
- **Cierre**: 17 tareas `[x]`; 7.2 documentada en `4c24333`. Corridas sobre `835a002`: backend 2076
  passed y 1 xfailed (+319 respecto de 1.1), web 301 (+3), navegador 144 y humo OK. Ensayo del respaldo
  restaurado ampliado a 0018/0016/0018, con 10 asignaciones y origen intacto.
- **Auditoría**: una vuelta de Claude sobre la construcción de Codex; el ALTO de firma y las filas
  2 a 4 se atendieron en el cierre. Los límites de revisión y el supuesto RD-2 quedan abajo en
  "Deuda del cierre del 2.2a". Artefactos en
  `openspec/changes/archive/2026-10-20-roles-de-la-empresa/`.

### 2b · `login-y-usuarios` · archivado 22/10/2026 · CRITICAL

- **Objetivo**: que el personal y los vecinos entren con Clerk, y que el super admin gestione las
  invitaciones, perfiles y alcances de su administración.
- **Historias**: HU-V1 (la parte de entrar; "ver mis unidades" queda para el 11), HU-SA1 (nueva,
  `06_funcionalidades.md`). **Decisiones**: D-036 (corregida en parte), D-039, D-096 (cuenta por
  administración, acotada a "por administración" en D-108), D-099, D-106, D-107 (reemplaza el método
  de D-097) y **D-108** (las elecciones E1 a E17 y las tres decisiones de cierre).
- **Entró**:
  - Clerk **sólo para autenticar**, con usuario y contraseña también para vecinos, link mágico y
    Google (E17). La autorización sigue en nuestra base: tenant, perfiles, alcance y RLS. La identidad
    se vincula por `persona.clerk_usuario_id` (migración `0019`), único **por administración**, nunca
    sólo por email.
  - La API verifica el token de Clerk **sin red** (PyJWT 2.15.1 + clave PEM del entorno); sesión del
    lado del servidor de Next (D-036, D4, con `CLERK_SECRET_KEY` también en Next, E16); selector de
    administración después de autenticarse (`/elegir-administracion`, D-099); CSP estricta con nonce
    (6.2, cierra la deuda del 2c); Caddy deja de publicar `/api/*` salvo `/api/salud` (cierra RF-B-4
    del 3a, **BREAKING** sin efecto real).
  - **Gestión de usuarios (RA-6)**: el super admin invita al personal con perfil y alcance (migración
    `0020`, tabla `invitacion`) y da de alta vecinos desde el padrón, con unidad y vínculo
    propietario/inquilino. Varios propietarios por unidad y vínculos distintos de una persona. El
    worker crea y envía la invitación con reintentos e idempotencia; se acepta con un token propio de
    un solo uso **y** el email verificado de Clerk igual al de la persona (minúsculas sólo ASCII,
    R2B-3).
  - Auditoría de ingresos (`ingreso_exitoso`, `ingreso_fallido`) y de la gestión sensible, ocho eventos
    nuevos en `accion_de_auditoria` (D13). Barra superior con el usuario real (cierra deuda del 3b).
  - Pantallas (shape firmado por Juani, `openspec/exploraciones/`): `/ingresar`, `/registrarse`,
    `/elegir-administracion`, `/invitacion/[sobre]`, `/privacidad` (aviso, **borrador**), `/personal`;
    alta de vecinos integrada al padrón del edificio.
- **No entró**: puerto de email completo con reintentos y plantillas (13), portal del vecino (11),
  vista del consejo (12), carga del edificio de ejemplo (`acceso-de-desarrollo`, reducido por E12, sin
  firma propia todavía), verificación del costo real de Clerk (15).
- **Tarea sin construir, a propósito**: **7.2, el aviso de privacidad, queda `[ ]` y en borrador**
  (decisión de cierre 3, D-108): faltan responsable, contacto y conservación; completarlos es deuda
  obligatoria antes de producción. Es la única de las 37 tareas sin marcar.
- **Deuda heredada, resuelta en este cierre** (L-012): del 2a, R9, V2-7, D-1 y D-6 (tarea 4.3); D-2
  queda verificada como restricción, no removida (sigue aplicando al próximo cambio que referencie
  `auditoria`). Del 2c, CSP (tarea 6.2). Del 3a, RF-B-4. Del 3b, el usuario real en la barra superior.
- **Deuda heredada, NO confirmada como resuelta**: del 2.2a, la revisión independiente de los ataques
  de base RR-1 a RR-4 y el cotejo de las 144 celdas del test de permisos contra D-106 (filas 2 y 5 de
  "Deuda del cierre del 2.2a"). El propose de este cambio lo proponía como blanco explícito del
  rompedor; no se encontró en `tasks.md` ni en los informes del rompedor/auditor del 2b evidencia de
  que se haya ejecutado como acción separada. Quedan abiertas, sin dueño nuevo.
- **Deuda nueva de este cierre** (deuda del cierre del 2b, ver tabla más abajo): SU-01 (invitación a un
  email con cuenta previa en Clerk, no verificada), la 8.2 acortada (deuda declarada: link por email,
  bloqueo por intentos, segunda administración, email secundario, reinvitar, revocar contra Clerk
  real en vuelo), y los 7 hallazgos de la verificación real del 21-22/10/2026.
- **Depende de**: 2a y 2.2a. **Habilita**: uso real de las pantallas, 11 y 15.
- **Firmado por Juani**: E1 a E15 el 21/10/2026 (`2212c9e`); E16 y E17 el 21/10/2026, misma tabla; las
  tres decisiones de cierre (R2B-3, 8.2 acortada, aviso de privacidad como borrador) el 21/10/2026.
- **Cierre (22/10/2026)**: 36 de 37 tareas `[x]` (7.2 en borrador, sin marcar). Una vuelta de rompedor
  y auditor (4 hallazgos, `.git/informes-2b/rompedor/informe.md`, corregidos el mismo día) más
  correcciones post-rompedor (RB2b-post-1 a 4). Verificación real con Juani al teclado contra Clerk de
  desarrollo (8.2, acortada por decisión de cierre 2): registro desde el mail, Google con el email
  invitado y el rechazo con otro Gmail, revocar una invitación y confirmarlo en el panel de Clerk.
  Hallazgo propio de la 8.2: el `__clerk_ticket` se perdía entre páginas (L-032, arreglado el mismo
  día, `90131a6`). Corrida de cierre sobre `7607863`: backend 2675 passed + 1 xfailed (+599 sobre
  1.1), web 385 (+84), web-navegador 172 (+28); humo verde sobre `1ea0d8b` (22/10/2026, 09:38-09:41).
  Dos tests de infraestructura frágiles (asumían `infra/datos-respaldos/` vacía) se corrigieron sin
  tocar `backend/src` (`7607863`).
- **Artefactos**: `openspec/changes/archive/2026-10-22-login-y-usuarios/`.

### 2c · `endurecimiento-de-infraestructura` · MEDIUM

- **Estado**: cerrado el 16/10/2026 sin vuelta 3 (D-101), con dos vueltas de constructor, rompedor y
  auditor; la deuda queda en "Deuda del cierre del 2c" más abajo, casi toda con dueño 15.
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

### 3 · `configuracion-del-edificio` · partido en 3a y 3b (propuesto, E1 del 3a)

El propose del 16/10/2026 (`openspec/changes/configuracion-del-edificio/`, revisado por el arquitecto
el mismo día, con D-100 aplicada) cuenta 24 tareas de backend y unas 15 de pantallas, y propone
partirlo (elección E1, la firma el socio que apruebe): el **3a** es el modelo, las reglas, la API y la
semilla, y es lo único que necesita el 4; el **3b** son los `shape` de las pantallas con Juani y las
pantallas. Si E1 se rechaza, las dos fichas vuelven a
ser una. Objetivo común: que el administrador cree un edificio y lo configure como dice su reglamento.

### 3a · `configuracion-del-edificio` · HIGH

- **Estado**: archivado el 19/10/2026 (D-103, D-104). Constructor Codex (GPT-6.1-Sol en `xhigh`, por
  bloques A a E, detalle en `14_forma_de_trabajo.md`); rompedor y auditor en dos vueltas (vuelta 1: 6
  hallazgos, R3A-1 a R3A-6; vuelta 2: 12 hallazgos, R3B-1 a R3B-12) y, sobre el HEAD final (`334daf5`),
  revisores de rol de backend y DBA que encontraron además RF-B-1 a RF-B-4 y RF-D-1 a RF-D-4 (ésta dio
  la migración `0015`, D-103). El auditor dio **OK**; la deuda queda en "Deuda del cierre del 3a" más
  abajo, con dueño por ítem (mayormente 3b, 2b, 15 y el 7).
- **Objetivo**: que el modelo del edificio quede completo para el 4, con la base frenando cualquier
  cruce de edificio o de administración, y la configuración que cambia plata versionada y de sólo
  agregar.
- **Historias**: HU-A1 (los datos; las pantallas son del 3b). **Reglas**: R01 (la definición de
  grupos con los dos modos de coeficientes de D-100 y el informe de la suma), R02 (sólo el campo de
  estado, desactivado; la regla se construye con barrios, D-089), R03 (su configuración, con el día fijo
  de vencimiento del 1 al 28), R26 (sólo como configuración: vencimiento único o doble con recargo en
  porcentaje, D-100), R09 (el estado de migración), R15 (porcentaje), R16 (categorías).
- **Propuestas** que **no entran** (ninguna se validó): R35, R36, R39.
- **Decisiones**: D-010, D-013, D-029, D-030, D-031, D-041, D-042, D-080, D-082, D-083, D-087, D-089,
  D-094, D-096, D-098, D-100.
- **Gobernanza HIGH** (D-087, D-094): guarda la configuración versionada de intereses, que cambia montos,
  y suma permisos a la matriz de D-096. Se propone y se espera la aprobación de uno de los dos socios,
  con las elecciones E1 a E10, antes de construir.
- **Entra**: edificio (localidad, estado de migración) y unidad (identificador, tipo de D-029, piso,
  coeficiente, superficie, estado desactivado) completos; grupos de reparto con FK compuesta que
  comparte `complejo_id`, "Generales" obligatorio; categorías de gasto (crear, renombrar, ordenar,
  desactivar, nunca borrar); configuración de intereses, vencimiento (día fijo del 1 al 28, único o
  doble con recargo en porcentaje, E9) y fondo de reserva como **menús cerrados** tomados de
  `parametros.yaml` al crear (o del reglamento, en el mismo alta), versionada con vigencia, autor y
  fecha, de sólo agregar también en los permisos que sobreviven a cada `up` (D-010, D-080, E4); grupos
  parciales renormalizados o con coeficientes propios (D-100); el informe de R01 con la tolerancia de
  ±0,0001, con la función pura en `compartido` (bloquea el 7, no la carga, E5); permisos de
  configuración y de lectura, con el vecino viendo sólo lo suyo (E3), y auditoría de crear edificio,
  crear versión y confirmar "sin saldos previos" (E7); API con contrato de error (401, 422 del cuerpo,
  404, 403, 409, 422 sin el valor); **cargar en la base el edificio de ejemplo** con un comando
  idempotente, en una administración de ejemplo propia (E6, E10; se recomienda mover esa tarea al 3b);
  el **estado de migración** (pendiente, confirmada o sin saldos previos, R09, D-083) en la base y en
  la semilla, con el ejemplo "sin saldos previos"; **alinear el validador de la semilla con R01** y con
  los modos de D-100. 24 tareas en `openspec/changes/configuracion-del-edificio/` (23 si la carga del
  ejemplo pasa al 3b; excepción a D-088 como el 1c).
- **No entra**: los `shape`, las pantallas y el acceso de desarrollo (3b); carga masiva desde Excel
  (5); cálculos (4, 7), incluido el recargo del segundo vencimiento; correr el vencimiento al emitir
  (7); que una liquidación emitida no cambie al cambiar la tasa (se prueba en el 7); el motor de reglas
  (6b, D-087); bajas de edificios, unidades o grupos.
- **Deuda con dueño este cambio** (L-012, D-098): **R6**, que bloquea antes de la primera ruta nueva (el
  sweep de rutas protegidas no ve `include_router(prefix=...)` ni `add_api_route`); **R11** (el id lo
  genera siempre el servidor, E8: un alta con `id` da 422, verificado por un barrido); y la fila del 1b
  de "Deuda técnica de las auditorías del 13/10" (el tope del YAML ya estaba hecho; la parte de
  infraestructura choca con `main` en `app.py`, no en Compose).
- **Depende de**: 2a (para construirse; el 2b, para que una persona lo use). **Habilita**: 4, 5, 6, 3b.
- **Bloqueado por**: nada. P19, P24 y P33 se resolvieron en D-100 (16/10/2026, pendiente de contrastar
  con el reglamento del piloto) y las 24 tareas quedan libres desde la aprobación. P16 sólo bloquearía
  R39, que no entra. P47 no bloquea el código pero sí la integración (`app.py` y `roles.py`). Cuatro
  preguntas nuevas de la revisión (PR1 a PR4 en el design) no bloquean.
- **Decidido en el design**: la configuración vigente para una fecha es la versión de mayor vigencia que
  no la supera; cada liquidación del 7 referencia la versión que usó (qué fecha usa es P34, del 4 y el
  7). Desde el 3a, el rollback con edificios cargados es restaurar un respaldo; el `downgrade` vale
  sólo para una base sin auditoría nueva.
- **Que intente romper el rompedor**: coeficientes de un grupo que no suman 1 (bordes 0,9999 y 1,0001,
  0,9998); una unidad repetida; cambiar la tasa y que se pierda la versión anterior; versiones
  superpuestas o simultáneas para la misma fecha; editar una versión después de un segundo `up`;
  vencimientos incoherentes; editar la configuración de otro edificio; un vecino que lee el padrón;
  una unidad de otro edificio o de otra administración en un grupo, por la API y por SQL; el edificio
  de ejemplo cargado dos veces, en paralelo o después de editarlo; montos y proporciones como `float`;
  un alta con `id` del cliente; una ruta nueva que el sweep no ve; un import de `complejos` en
  `compartido`. La lista completa está en la propuesta.
- **Terminado cuando**: se cumplen los criterios de datos de HU-A1; un edificio nuevo arranca con los
  valores de `parametros.yaml`; cambiar el archivo no altera edificios existentes; la base rechaza como
  `proptech_app` toda escritura cruzada y toda edición de una versión, también después de un segundo
  `up`; el vecino no lee la configuración; las migraciones bajan y suben sobre una copia sin auditoría
  nueva y, con auditoría nueva, el `downgrade` falla y se restaura el respaldo; la corrida de cierre en
  orden y un clon limpio en verde.

### 3b · `pantallas-del-edificio` · archivado 20/10/2026 · OK

- **Objetivo**: que el administrador configure su edificio desde el navegador.
- **Precondición del propose**: el `shape` de cada una de las siete pantallas con Juani (una sesión
  de `impeccable shape` por pantalla, con un brief en `openspec/exploraciones/` y el OK de Juani con
  fecha). Era la tarea 8.1 de la primera versión del propose del 3a; pasó acá para no atar el cierre del 3a a siete sesiones de diseño
  (revisión del arquitecto del 16/10).
- **Entró y se construyó**: las siete pantallas de la superficie del administrador (mis edificios,
  resumen del edificio, padrón de unidades, grupos de reparto, categorías de gasto, intereses y
  vencimiento, confirmar "sin saldos previos"); los tokens de `DESIGN.md`; una enmienda del shape
  (19/10/2026, D-105) a todo el ancho, con menú lateral agrupado con íconos, barra superior y ayuda "?"
  acoplada que empuja el contenido, con Mercado Pago como referencia.
- **Reglas de diseño**: números tabulares y formato argentino en coeficientes, tasas y porcentajes; el
  estado de R01 y el de migración nunca sólo con color; una acción principal por pantalla; la web no
  calcula (la suma y su estado vienen de la API).
- **Terminado cuando**: cada pantalla se opera entera con teclado y foco visible; cada error está
  asociado a su campo por programa; los estados de carga, vacío y error se alcanzan a pedido; a 320 px
  no hay scroll horizontal; WCAG 2.2 AA sin violaciones de axe en cada estado.
  Cada pantalla tiene su ayuda "?" con las tres partes escritas (D-102, HU-T1, The Always-Help
  Rule de `DESIGN.md`, pedido de Alberto del 17/10/2026).
- **Quedó afuera, movido al change `acceso-de-desarrollo` (20/10/2026)**: el acceso de desarrollo sin
  login de E2 (punto de entrada fuera del paquete instalado y un Compose aparte) y la carga del
  edificio de ejemplo en la base (la 7.2 del 3a): las dos esperaban la firma HIGH de Juani (D-094) y
  además la carga del ejemplo quedó bloqueada por un `GRANT INSERT ON auditoria` CRITICAL que tampoco
  decide un agente solo. Ninguna de las dos la necesitaban las siete pantallas: se probaron con la API
  simulada, una API falsa y fixtures generados por la API real (D3, D4 del design del 3b).
- **Cerrado por**: constructor Claude Sonnet (bloques de TDD estricto), una vuelta de rompedor y
  auditor Claude Opus, con un pulido y un rediseño de UI entre medio (L-026). **OK**; la deuda queda en
  "Deuda del cierre del 3b" más abajo.
- **Depende de**: 3a y los `shape`. **Habilita**: `acceso-de-desarrollo` y el uso real del 3 junto con
  el 2b.

### 3b-bis · `acceso-de-desarrollo` · HIGH, archivado OK (24/10/2026, D-110)

- **Objetivo**: cargar el edificio de ejemplo para recorrer las siete pantallas contra la API real,
  entrando por el login de verdad. **Reducido por E12** (firmada por Juani en el 2b, 21/10/2026): con
  Clerk construido, el acceso sin login sobra y es una puerta más que podría llegar a producción.
- **Descartado por D11 del design del 2b**: el punto de entrada sin login (`backend/desarrollo/`,
  `compose.desarrollo.yaml`) y sus guardas, **y el `GRANT INSERT ON auditoria TO proptech_migrador`**
  que este change tenía pendiente de firma. No se construyen ni se piden: la carga corre como
  `proptech_app`, que ya tiene `SELECT, INSERT` sobre `auditoria` (el mismo permiso del que depende
  D10, `alta inicial`), así que el `GRANT` al migrador no hace falta.
- **Gobernanza**: queda **HIGH** (toca cómo se carga identidad y datos en el log de auditoría, aunque
  con el mismo mecanismo que ya usa D10). Ya no hay una segunda decisión CRITICAL: al no pedirse el
  `GRANT`, no queda nada que toque permisos sobre `auditoria` por fuera de lo que D10 ya firmó con E11.
- **Lo único que construye**: la carga del edificio de ejemplo (7.2 del 3a, D9/E6/E10) reescrita sobre
  el camino de **D10 · Alta inicial** del 2b (el comando corre con las credenciales de `proptech_app`,
  nunca `proptech_migrador`, fija el tenant de la administración de ejemplo y crea su fila
  `super_admin` en la misma transacción) y el recorrido de las siete pantallas del 3b contra la API
  real con ese ejemplo cargado.
- **L-029**: la firma de E12 en el proposal del 2b aprueba la *decisión de forma*, no estos artefactos
  reescritos; este change sigue necesitando su propia firma en su sección "Aprobación".
- **Cierre**: firmado por Emiliano Caceres el 24/10/2026 (D-110); la firma la ratifica D-111 (Juani,
  25/10/2026), que suma a Emiliano como firmante HIGH/CRITICAL junto a Juani y Alberto. Construido y verificado: `ejemplo.py` corre como
  `proptech_app`, probado contra PostgreSQL real; recorrido a mano de las siete pantallas del 3b contra
  la API real con el ejemplo cargado, entrando con Clerk de desarrollo, en 1280 px, 320 px y con
  teclado. **OK**; deuda y hallazgos (fallas de portabilidad Windows en la suite de pytest, `humo.sh`
  sin forma de aislarse de un stack real, el CVE de Next.js 16.4.0 ya resuelto con la actualización a
  16.4.3) quedan en D-110.
- **Revisión del PR #1 (25/10/2026)**: backend, DBA, QA, arquitecto y auditor (informes en
  `.git/informes-pr1/`, fuera de git). Corregido en el mismo PR: D-094 vuelve a su texto y la firma de
  Emiliano se ratifica en D-111; el comando sólo corre con `PROPTECH_ENTORNO=desarrollo` (guarda de
  entorno, D-112, para que el módulo que viaja en la imagen de producción
  no cree un `super_admin` ahí); hay tests que corren el comando real (rol `proptech_app`, códigos de
  salida, "ya estaba", rechazo del migrador) y el mutante M9 ya no sobrevive; 04, 08, 10 y el README
  dicen lo que hay. El resto queda en "Deuda del cierre de `acceso-de-desarrollo`" más abajo.
- **Depende de**: 3a, 3b, 2.2a y 2b (D10, D11, E11, E12). **Habilita**: recorrido con datos de ejemplo,
  nunca datos personales reales.

### 3c · `pulido-de-la-configuracion` · HIGH · firmado y construido (27/10/2026, D-128)

- **Objetivo**: que un administrador configure su edificio sin tropezar: cada error en el campo que
  corresponde y diciendo qué se espera, la ubicación elegida de listas oficiales y el piso de cada
  unidad elegido de los pisos que tiene el edificio.
- **Origen**: el QA manual del 23/10/2026 (antes en `CLAUDE.md`/`AGENTS.md`, migrado a esta ficha y a
  `10_preguntas_abiertas.md` al cerrar) y dos pedidos de Juani del 26/10/2026 (ubicación con listas
  encadenadas y cantidad de pisos). Exploración completa, con cada ítem ubicado en el código:
  `openspec/exploraciones/2026-10-26-pulido-de-la-configuracion.md`.
- **Historias**: HU-A1 (configurar el edificio); HU-A2 por el borde de la columna "piso" del Excel
  (el importador en sí no se construye acá, cambio 5).
- **Construido**: los errores de intereses y vencimiento (B-1: el conflicto de "Rige desde" deja de
  caer en el mensaje genérico; B-2: reproducido primero con un test en rojo antes de tocar código, D6);
  ayudas y mensajes de identificador, coeficiente y clave de grupos y categorías (G-1 a G-3);
  confirmación de "Quitar" en Personal con el diálogo de `PanelLateral` (G-4, D10); la nota interna de
  `/privacidad` reemplazada por un texto para el usuario (G-5, los datos legales siguen pendientes de
  Juani, D-108); un grupo se desactiva en vez de borrarse y la clave de grupos y categorías se
  autogenera desde el nombre (G-6, E6); la **ubicación** del edificio (provincia, departamento y
  localidad encadenados desde el archivo de Georef en el repo, CC BY 4.0, D1); `PATCH /complejos/{id}`
  para **editar el edificio**, que no existía (D5); la **cantidad de pisos y subsuelos** del edificio y
  `unidad.piso` acotado a ese vocabulario (D3); la migración de los edificios y unidades ya cargados,
  sin inventar ningún valor (E3, E5); el edificio de ejemplo con ubicación real de Georef y pisos (6.5).
  Tres migraciones nuevas: `0025` (ubicación), `0026` (pisos/subsuelos y `unidad.piso`), `0027` (grupo
  desactivable y el evento de auditoría `editar_edificio`).
- **Quedó fuera** (P68, D-128), para un change de acceso propio y futuro, CRITICAL: la invitación
  abierta con la sesión de otra cuenta (B-3), el menú que se adapta al rol (2.3), reinvitar el mismo
  email (2.4), `/personal` jerárquica (2.5/P66, aprobada en principio por D-127) y, sumado en el
  recorrido 7.1 del 27/10/2026, el **loop infinito en `/elegir-administracion?regreso=...`**
  (`web/src/app/ingresar/Pantalla.tsx`/`web/src/lib/sesion.ts`: el header `x-proptech-ruta` repite la
  ruta actual en cada paso y, si esa ruta ya es `/elegir-administracion?regreso=...`, el `regreso` se
  anida y se re-codifica en cada vuelta sin límite). Los cinco comparten el mismo motivo: tocar
  `acceso` subiría el change entero a CRITICAL. También quedaron fuera, sin change propio: los datos
  legales del aviso de privacidad (a cargo de Juani, D-108); aceptar coeficientes en porcentaje; calles
  normalizadas contra Georef; selector de país; cualquier escritura en `configuracion_versionada` o en
  plata (4b a 4d); el piso en el importador de Excel (5); borrar las cuentas de Mailinator (P67, acción
  operativa de Emiliano, sin código).
- **Gobernanza**: HIGH (D-094, D-111). Firmado por **Emiliano Caceres el 26/10/2026** (E1 a E6 y E8 a
  E10 completas; E7 no era una elección de este change).
- **Resuelto**: P61 a P65 (ubicación y pisos), P67 (Mailinator), P68 (alcance) y P69 (grupos),
  escritas como **D-128** al cerrar. P66 cerrada por D-127 (change de acceso futuro).
- **Choques con el 4a**: el 4a ya estaba mergeado en `main` (migraciones `0021`/`0022`) antes de la
  primera tarea de este change; las migraciones del 3c nacen desde `0025` y la rama se rebasó sobre
  `main` antes de empezar, sin conflicto real en `unidades.py` más allá de lo previsto en el design.
- **Choques con el 4b** (integración del 27/10/2026, rama `integrar/3c-sobre-4b`): el 4b llegó a `main`
  con `0023_libro_de_movimientos` y `0024_correccion_auditada` mientras el 3c estaba abierto; sus tres
  migraciones nacieron como `0023` a `0025` y se renumeraron a `0025` a `0027`, encadenadas detrás de
  `0024`. Sus decisiones D-120 y D-121 pasaron a D-127 y D-128, y sus lecciones L-047 a L-049 a L-051
  a L-053, porque el 4b ya había usado esos números.
- **Construido con TDD estricto**, por bloques, con mutantes dirigidos en cada garantía nueva
  (coherencia del trío de ubicación, piso dentro del vocabulario, "Generales" no se desactiva); detalle
  bloque por bloque en `tasks.md` del change.
- **Cierre (7.2)**: suite completa de backend y de web corridas después de la última vuelta (comando,
  resultado y hora pegados en `tasks.md`, tarea 7.2); subida y bajada de las tres migraciones ejercitada
  por los tests de integración dedicados (`test_ubicacion_db.py`, `test_ubicacion_migracion_multitenant.py`,
  `test_pisos_db.py`, `test_pisos_migracion_multitenant.py`, `test_grupo_activo_migracion.py`,
  `test_eventos_padron_migracion.py`, `test_rls_edificio.py`), con `testcontainers` levantando su
  PostgreSQL propio por módulo — no se usó una "copia con datos" aparte porque esos tests ya ejercitan
  el flujo con una base sembrada; **esta rama no tiene PR abierto, así que no corrió CI**: no hay SHA
  que anotar (L-010, L-031, L-037, L-042).
- **Deuda del cierre**: la tarea **7.1** (recorrido manual de cada pantalla tocada a 1280 px y 320 px,
  con teclado y capturas, más cómo la cuenta de Clerk usada quedó vinculada a su persona) queda **sin
  marcar, a cargo del humano** — nunca de un agente (L-039, salda también la deuda del PR #1 del
  3b-bis). `complejo.localidad` sigue sin borrarse (D2): queda anotada para el primer change que toque
  el módulo después de este. El tope de 5 subsuelos y 60 pisos (D3) es un `CHECK` de una línea si un
  edificio real no entra. Si el `<select>` de 135 departamentos resulta incómodo en el recorrido de
  7.1, el combobox accesible queda como deuda, no como alcance.
  **Hallazgo del recorrido 7.1 (27/10/2026) que sigue abierto** (los otros tres, ya arreglados en la
  misma sesión, quedaron como lección en `15_lecciones.md`, L-053; el loop de `/elegir-administracion`
  encontrado el mismo día no es deuda de 3c — queda arriba, junto a B-3/2.3/2.4, porque toca `acceso`):
  en "Puesta a punto", el paso de ubicación sigue rotulado "Completar la ubicación" aunque ya esté
  marcado "Hecho" — **decisión pendiente** del usuario (cambiar el label a "Editar la ubicación" cuando
  está hecho, o sacar el botón).
- **Revisores**: QA siempre; DBA por las tres migraciones; frontend por las pantallas tocadas; backend
  por los endpoints nuevos (`PATCH /complejos/{id}`, las tres rutas de lectura de Georef).
- **Depende de**: 3a, 3b y 2b (archivados). Construido en paralelo al 4a. **Habilita**: la columna
  "piso" del importador (5) y un alta de edificio presentable para el piloto (15).

### 4 · `motor-de-cuenta-corriente` · crítico · explore propio · partido en 4a, 4b, 4c y 4d

> **Partido** (exploración del 4, `openspec/exploraciones/2026-10-22-motor-de-cuenta-corriente.md`
> §8, D-117): **4a** `cimientos-del-libro` (HIGH, **archivado el 26/10/2026**, D-119; su ficha va
> abajo), **4b** `libro-de-movimientos` (CRITICAL, **archivado el 27/10/2026**, D-121 a D-126; su
> ficha va abajo), **4c** `intereses-saldo-inicial-y-moroso` y **4d** `cambio-de-titular` (los dos
> CRITICAL que faltan; el 4d puede ir después del 7 y no bloquea M1). Dependencias en `CHANGES.md`
> [C-07a] a [C-07d]: el 6 puede arrancar tras el 4a si no escribe en el libro, el 5 necesita el 4c y el
> 7 el 4b y el 4c. Esta ficha queda como entrada común; el detalle por sub-change lo escribe cada
> propose.

- **Objetivo**: el corazón de la plata: que cada peso de deuda viva en un solo lugar y nunca se pierda un centavo.
- **Historias**: HU-A9 (correcciones). **Reglas**: R03, R04, R05 (con los créditos que no son pagos,
  D-086), R06, R07, R08, R09 (el caso de uso
  de saldo inicial), R13 (orden de imputación por tipo).
- **Decisiones**: D-010, D-011, D-012, D-015, D-016, D-024, D-046, D-068, D-073, D-074, D-080, D-081,
  D-082, D-086.
- **Vigente desde D-109**: R30 (umbral de saldos chicos). El 4a ya guarda el umbral por versión de
  configuración; su efecto sobre el moroso crítico (R20) lo construye el 4c.
- **Propuestas** (entran si se validan): R35 (intereses desde el día hábil), R36 (tasa propia de la
  extraordinaria), R39 (sin intereses ni moroso crítico para unidades del consorcio). Hoy no tienen
  ninguna marca en el modelo (ni en `unidad` ni en `configuracion_versionada`): el change que las
  valide agrega la columna que necesite.
- **Entra**: libro de movimientos de sólo agregar, sin campo saldo; obligaciones, pagos e
  imputaciones; intereses simples calculados al registrarse; reparto por **mayor resto** como función
  pública (hecho en el 4a: `compartido/reparto.py`, la usan el 4b, el 6 y el 7); correcciones con
  contra-asiento; dos fechas por
  pago (registro y valor); caso de uso de saldo inicial (con detalle por período o total único);
  bloqueo para pagos simultáneos de la misma unidad; el efecto del umbral de saldos chicos (R30,
  vigente; el número ya vive en `configuracion_versionada` desde el 4a, ProTecc D3); **la función pura de moroso crítico** (R20, D-074), como consulta sobre
  el libro que usan los cambios 8, 10a y 10b; el saldo excluye todo movimiento generado por una
  emisión anulada, incluidos los ajustes de interés que la compensaban (D-073, D-079, D-084, D-085).
  **Contrato mínimo de emisión** (D-086): este cambio define la entidad emisión con lo justo para el
  libro (identificador, período, edificio y estado), y cada movimiento referencia la emisión que lo
  generó; el cambio 7 la completa con la preliquidación, los controles y la distribución. La anulación en sí se construye en el cambio 7: acá se prueba con
  una emisión marcada como anulada en el test.
- **No entra**: la pantalla para confirmar pagos (8); la importación del Excel (5); la emisión (7).
- **Depende de**: 2a, 3a (el menú de intereses versionado) y, para el 4b en adelante, el 4a.
  **Habilita**: 5, 6 (desde el 4a, si no escribe en el libro), 7.
- **Bloqueado por**: P10, P11 y P42 ya no bloquean (D-109 punto 6). Cada sub-change tiene las suyas en
  `10_preguntas_abiertas.md`: el 4b, P-8 (repositorio sin puerto) y P-6 (pantalla de corrección); el
  4c, P-4 y P-5; el 4d, P-1 y P-2. Para Alberto, A-1 a A-4 (A-1 puede cambiar el desempate del 4a sin
  tocar datos).
- **Deuda técnica del 1b** (D-053): **cerrada en el 4a**. Se borró el `except TypeError` muerto de
  `leer_parametros` (y el par del lector de la semilla) con tests que muestran que otra capa ya corta
  esos caminos, y quedó escrito y probado con mutantes que `Dinero.desde_decimal` **acepta** ceros de
  más cuando el valor no cambia (`Decimal("1.0000")` da `1.00`) y rechaza lo que cambiaría, mientras
  que el texto (`Dinero("1.0000")`) los rechaza (D-114.6, que corrige la nota de D-053).
- **El modelo de tablas del libro y el candado por cuenta ya no son "a decidir": se construyeron en el
  4b** (D-121, migración `0023`). **Decidir en el design del 4c**: el **ajuste de saldo inicial bajo
  R09**, con motivo y origen (de dónde sale la fila: el importador, el 5, o una corrección manual); el
  4b deja la columna `obligacion.operacion_id` para una obligación sin emisión, pero el caso de uso en
  sí (cómo se carga, qué lo audita) es del 4c.
- **Lo que el 4c recibe hecho del 4b**: las ocho tablas del libro, el candado por cuenta, el orden de
  imputación (R04/R15) y el estado de cuenta (`estado_de_cuenta`, E12); el 4c sólo agrega el detalle
  de interés (días, tasa, base) y el caso de uso de saldo inicial, ninguno de los dos reabre `0023`
  (E10: columnas y referencias futuras ya anticipadas, cambiar CHECK/únicos exige préstamo D-115.3).
- **Lo que el 4d recibe hecho del 4b**: la `cuenta` ya nace polimórfica (de unidad o de persona, única
  por administración y edificio, P52) y el vocabulario `tipo_de_movimiento` ya tiene `traslado` (ambos
  sentidos) y `enlazado_a` sembrados (E14); el 4d usa ese traslado para mover el historial de deuda de
  la cuenta de la unidad a la cuenta de la persona vendedora, sin ALTER.
- **Lo que el 4b recibía hecho del 4a** (histórico): sus seis tablas se declaraban en
  `compartido/tablas_protegidas.py` y nacían con trigger por fila de `UPDATE` y `DELETE`, `BEFORE
  TRUNCATE` y el trigger `BEFORE UPDATE OR DELETE ... FOR EACH STATEMENT` (D-114.4), los tres con la
  misma función; `roles despues` las transfiere y verifica sin cambiar su lógica. Ese trigger por
  sentencia **bloquea `INSERT ... ON CONFLICT DO UPDATE`** aunque no haya conflicto: la idempotencia
  del libro va con `ON CONFLICT DO NOTHING` y leyendo la fila existente.
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
- **Precondiciones de la auditoría de cimientos (22/10/2026)**: el grupo B de preguntas de negocio
  (P10, P11, P21, P31 y P34) quedó respondido por D-109 (22/10/2026). Quedan sin bloquear el propose
  ni la construcción: las dos sub-preguntas abiertas para Alberto (a qué unidad va el centavo
  sobrante, P10; si su Excel corta el interés en la misma fecha, P34) y P42 (la sesión con un contador
  o administrador de Mendoza) — las tres se resuelven antes del piloto (15). Por D-109 (P11), el 4
  suma una **cuenta de persona**, además de la cuenta de unidad, para la opción "deuda a nombre del
  vendedor" en un cambio de titular. **Resueltas en el 4a**: dueño de las tablas de sólo agregar
  (D-115), redondeo y precisión del reparto con invariantes (D-113, D-118), reglas nuevas del test de
  fronteras (D-116) y auditoría del coeficiente (D-114.2, D-114.3). **Siguen para los sub-changes
  siguientes**: dueño de `emision`, idempotencia de punta a punta, commit-y-encolar con reproceso,
  errores de campo y `pesos()`, contrato de error uniforme, patrón puertos/adaptadores del libro, el
  contrato de la API falsa para los formularios nuevos y el canario que no repita la suite entera.
  Detalle completo, con criterio de terminado por ítem, en
  `openspec/exploraciones/2026-10-22-cimientos-antes-del-4.md`.

#### 4a · `cimientos-del-libro` · HIGH · archivado 26/10/2026 (D-119)

- **Qué dejó**: cinco reglas de fronteras sobre `cuenta_corriente/` vacío (D-116); las tablas de sólo
  agregar del rol de arranque, verificadas por el efecto y con chequeo de arranque (D-115);
  `compartido/reparto.py` (mayor resto en centavos enteros, desempate por orden natural, total negativo
  simétrico) y `redondear_al_centavo`, con propiedades en `hypothesis` (D-113, D-118); suma, resta y
  negación de `Dinero`; el umbral de R30 en `configuracion_versionada` (`0021`, D-114.1) y en
  `parametros.yaml`; siete eventos del padrón auditados con el coeficiente anterior y el nuevo
  (`0022`, D-114.2, D-114.3); la deuda D-053 cerrada (D-114.6). Sin pantallas.
- **Firma**: Juani, 26/10/2026, E1 a E8. **Archivo**:
  `openspec/changes/archive/2026-10-26-cimientos-del-libro/`. **Merge**: `583f2f7`.
- **Rollback**: con punto de no retorno en el primer evento del padrón registrado (D-114.5); el
  procedimiento está en el "Migration Plan" del design archivado.

##### 4a · deuda del cierre

La "Deuda aceptada" del design archivado más la deuda nueva de la auditoría final
(`14-auditor-final.md`). Los códigos son los de los informes en `.git/informes-cimientos-del-libro/`.
Dueño por el primer cambio que necesita que esté resuelta (L-012); donde no lo firmó nadie, la fila lo
dice.

| Deuda | Por qué no bloquea | Cambio |
|---|---|---|
| RB-4: el mutante que saca `WHERE t.schemaname='public'` de `verificar_tablas_de_solo_agregar` sobrevive; el test de la tabla homónima pasa por el orden del catálogo, no por el filtro | **Cerrada en el 4b** (tasks.md 1.3): tabla homónima creada antes **y** después que la de `public`, mutante rojo en los dos órdenes | — |
| RB-5: el mutante que no registra `modo_de_coeficientes` en `campos` de `fijar_unidades` sobrevive; tampoco se registra qué unidades entran o salen de un grupo `renormalizado` | Los coeficientes sí se registran; falta el nombre del campo y la pertenencia en un caso | El próximo cambio que toque `grupos.py` (3c o 6). Dueño propuesto, no confirmado por Juani |
| RB-6: `redondear_al_centavo` con \|valor\| ≥ ~1e30 levanta `decimal.InvalidOperation`, no `MontoInvalido` como dice D7 del design | **Sin consumidor todavía**: el 4b agregó `test_deuda_4a.py`/`test_deuda_4a_umbral.py` (tasks.md 5.1, commit `4164aa2`), pero el auditor final del 4b nota que **ningún revisor independiente los abrió**, sólo los mutantes del propio constructor (`16-auditor-final.md`, Chequeo 3/5) | 4c, primer consumidor real (interés). Tests existen; falta su revisión independiente |
| RB-7 (anterior al 4a): `Dinero(texto)` construido bajo un contexto decimal de baja precisión levanta `InvalidOperation`; la aritmética sí está aislada, el constructor no | Igual que RB-6: cubierta por `test_deuda_4a.py` del 4b, sin revisión independiente confirmada | 4b, cerrada con la misma salvedad que RB-6 |
| RB-11: la 4.1 no tiene el rojo de la aceptación con `0022` vacía; lo reemplazan dos mutantes | El mutante de vocabulario hace un trabajo equivalente (auditoría del apply) | — (se registra, no se reabre) |
| El ensayo de roles (`infra/ci/ensayo-roles.sh`) no corre en CI: `test_ensayo_login.py` fija el número de revisión y el orden del paso 1 del rollback en el texto del script, no que funcione. Sólo se prueba corriéndolo a mano (L-043) | **Corrido en el cierre del 4b** (`PROPTECH_COMPOSE_PROYECTO=proptech-cierre-4b bash infra/ci/ensayo-roles.sh` → `ENSAYO ROLES OK`, proyecto aislado, tasks.md línea 547) | Sigue sin entrar al CI; dueño: quien lo agregue al workflow |
| El mensaje del ensayo `ciclo 0018/0016/0018` ya no es verdad (14-auditor-final) | Es texto de salida; el ensayo hace lo correcto | Quien toque `ensayo-roles.sh`. Dueño propuesto, no confirmado por Juani |
| `PROPTECH_COMPOSE_PROYECTO` exportada en la shell se filtra a `restaurar.sh`, que deja de apuntar a `proptech` (14-auditor-final) | **Reaparece en el 4b** como L-047 (`knowledge-base/15_lecciones.md`): `humo.sh` fija `-p proptech` e ignora la variable; el cierre del 4b lo esquivó con un envoltorio externo, el script sigue sin parametrización nativa | Quien toque `infra/ci/humo.sh` o `restaurar.sh`. Dueño propuesto, no confirmado por Juani |
| Cachear Chromium en el job `web` del CI: hoy se instala en cada corrida (hasta 10 minutos) y el límite del job pasó a 25 (L-044) | Con 25 minutos pasa; la última corrida tardó 7 | Quien toque `.github/workflows/ci.yml`. Dueño propuesto, no confirmado por Juani |
| Revisión del propose, deuda aceptada del design: AR-5 (mover `ejemplo.py` a una raíz de composición), AR-7 (las reglas de fronteras miran sólo imports directos), AR-9 (dirección de los eventos); DB-2 (comparar el esquema de `0020` con `pg_dump -s` o `information_schema`, no con `pg_attribute` crudo); AN-7 y AN-9 | Escritas en el design (D4, D9) y en las specs | AR-5: quien toque `ejemplo.py`; el resto, sin dueño. Propuesto, no confirmado por Juani |
| QA sin tarea propia: QA-6 y QA-7 sin test dedicado más allá de 2.1, 2.2 y 2.4; QA-9 (SQLSTATE del `UPDATE` del umbral y borde "0.00" del `CHECK`); QA-12 (modelo de detalle permisivo); QA-14 (migración de prueba que hace algo antes del `ALTER`); QA-15 (función con otro dueño) | **QA-15 cerrada en el 4b** (tasks.md 1.3: función de bloqueo con otro dueño y función con el texto de otra tabla, rojas en `despues()`). **QA-6, QA-7, QA-9, QA-12, QA-14**: cubiertas por `test_deuda_4a.py`/`test_deuda_4a_umbral.py` del 4b (5.1, `4164aa2`), con la misma salvedad que RB-6/RB-7: sin revisor independiente que las haya abierto | 4b, cerrado salvo la revisión independiente pendiente |

**Nota sobre la salvedad "sin revisión independiente" (RB-6, RB-7, QA-6, QA-7, QA-9, QA-12, QA-14)**: el
auditor final del 4b revisó contra el diff completo (`git diff 84badd1..8d25bd6 --stat`, 77 archivos) y
listó estos tests entre lo que "nadie miró salvo con los mutantes del constructor". Los tests existen y
corren verdes; lo que falta es que alguien distinto de quien los escribió los haya leído. No se marcan
"cerrados sin más" para no repetir el patrón que esta misma tabla señala en L-012.

#### 4b · `libro-de-movimientos` · CRITICAL · archivado 27/10/2026 (D-121 a D-126)

- **Qué dejó**: el libro de movimientos construido: ocho tablas (`cuenta`, `candado_de_cuenta`,
  `emision`, `evento_de_emision`, `obligacion`, `movimiento`, `imputacion`, `tipo_de_movimiento`,
  migración `0023`), con RLS, claves naturales y candado por cuenta (E1-E4); orden de imputación con
  el fondo de reserva provisorio (E5); corrección por contra-asiento o crédito, con su tope por
  crédito (E6, E7, enmienda RB4B-01/D-122); permiso y auditoría de `corregir_movimiento` (E8,
  migración `0024`); contrato de error de la ruta `POST
  /api/complejos/{complejo_id}/correcciones` (E9); columnas anticipadas para el 4c/7/8 (E10); regla de
  fronteras del SQL por módulo (E11); lecturas con foto consistente y crédito aplicable/retenido
  separado (E12, E16); deuda del 4a cerrada o reasignada (E13, ver tabla arriba); vocabulario
  ampliable de tipos de movimiento (E14); `GRANT REFERENCES` al migrador sobre el libro (E15). Detalle
  completo de las 16 elecciones en `knowledge-base/09_decisiones_y_supuestos.md` D-121.
- **Firma**: Juani, 26/10/2026, E1 a E16 (D-121); enmienda E7 · tope por crédito, 26/10/2026 (D-122);
  deuda D8 sobre crédito de corrección y emisión anulada, 27/10/2026 (D-123, bloquea el 7).
- **Archivo**: `openspec/changes/archive/2026-10-27-libro-de-movimientos/`. **Merge**: `409274f`
  (CI run `40533627016`).
- **Rollback**: sólo con el libro vacío o sin ninguna corrección auditada (E13); una vez que hay una
  fila en cualquier tabla del libro, bajar `0023` es hacia adelante, igual que `0022` para el 4a
  (D-114.5). Procedimiento en el "Migration Plan" del design archivado.
- **No construyó** (quedó explícitamente fuera, para los cambios que siguen): la pantalla de
  corrección, `pesos()` y la API falsa (8, D-120); intereses, saldo inicial y moroso crítico (4c);
  cambio de titular y cuenta de persona en uso (4d); la acción de anular en sí, con su ventana y
  motivo en pantalla (7, D-124); confirmar/revertir/reimputar pagos (8); condonación, bonificación y
  baja de deuda como acciones (10b, 8); outbox y encolado (7, 15); el préstamo de propiedad para un
  `ALTER` sobre una tabla protegida (el primer cambio que lo necesite).

##### 4b · deuda del cierre

Lista completa del auditor final (`.git/informes-libro-de-movimientos/16-auditor-final.md`, "Lo que
queda como deuda"), con dueño propuesto por cambio. Dueño por el primer cambio que necesita que esté
resuelta (L-012); donde no lo firmó nadie, la fila lo dice.

| Deuda | Qué falta | Cambio |
|---|---|---|
| Mutante de RF-01 (replay de emisión, "un `foto` por cuenta" en `registrar_emision`) sin matar: el único mutante corrido (`03-mutante-anular-sin-bloquear.log`) da `..F`, RF-01 y RF-04 quedan en verde | Escribir y correr el mutante que vuelve a publicar más de una foto por cuenta | Quien toque `registrar_emision` o audite el 4b después. Dueño propuesto, no confirmado por Juani |
| Test de RF-02 en la forma contra-asiento: sólo se probó en la forma crédito (`test_cc_anulacion_candado.py`) | Agregar el caso contra-asiento al mismo test | Quien toque anulación/corrección. Dueño propuesto, no confirmado por Juani |
| El registro de RF (los tres commits 447b8e5, 8496f00, 8d25bd6) no quedó en `tasks.md`, y ninguno de los tres lo revisó un rompedor o revisor distinto del constructor | Completar el registro o, si no se completa, que quien lo use sepa que esos tres commits están sin revisar | Orquestador, al cerrar un ciclo con RF. Sin dueño de cambio: es higiene de proceso |
| Ficha del 7: `anular_emision` tiene que tomar los candados de las cuentas de su emisión antes de escribir (igual que las demás escrituras del libro, E2) | Construir esa toma de candado en el 7 | **7**, ya anotado arriba en su ficha y en D-124 |
| D8 (crédito de corrección sobre una emisión anulada): Juani la anotó como deuda que bloquea el 7 en vez de resolverla ahora (opción c) | Decidir retenido (como E16) o a favor (como un pago) antes de construir `anular_emision` | **7**, D-123; no se construye la anulación sin decidir esto |
| RB4B-01, CX-01 y CX-02 (bloqueantes del rompedor de fases 1-3) arreglados en HEAD pero revisados sólo por el auditor, nunca por un rompedor independiente de ese arreglo puntual | Una pasada de rompedor sobre los tres arreglos, antes de confiar en ellos para el 7 | Quien abra el 7; revisar antes de depender de `imputado_por_credito` y el candado de `registrar_emision` |
| El auditor final no revisó código: "yo no reviso código, así que ese hueco sigue abierto" sobre el cierre de RF | Una revisión de código real (no documental) de 447b8e5, 8496f00 y 8d25bd6 | Quien abra el 7, como parte de leer qué recibe hecho |

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
- **Depende de**: 3 y el 4c (saldo inicial; el 4c ya trae el 4a y el 4b). **Habilita**: 7 y el test de M1.
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
- **Lecturas y vínculos (D-106)**: contador (principal o por edificio) y consejo leen los gastos y
  comprobantes de su alcance, sin escribir. Preparar la separación de ordinarias y extraordinarias
  para que el inquilino vea sólo ordinarias; el propietario ve ambas. El 2.2a sólo creó el vínculo.
- **Historias**: HU-A3 (carga manual, incluido el sueldo del encargado), HU-A3b. **Reglas**: R01
  (reparto de cada gasto en su grupo, usando el mayor resto del 4a, `compartido/reparto.py`), R12 (la clave de factura
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
- **Depende de**: 3 y el 4a (el reparto por mayor resto); si escribe en el libro, también el 4b (S-04, sin verificar contra R14 y R25). **Habilita**: 7, 14.
- **Bloqueado por**: P15, P17, P25, P36 y P37.
- **Que intente romper el rompedor**: un gasto sin categoría que se aprueba; un cargo particular que
  termina repartido entre todos; un gasto de otro edificio; un importe con tres decimales; aprobar
  dos veces el mismo gasto; borrar una categoría con gastos (sólo se desactiva, R16); una nota de
  crédito que supera el monto de su factura; una nota de crédito sin factura asociada.
- **Terminado cuando**: se cumplen los criterios de HU-A3 (manual) y HU-A3b; un gasto en borrador,
  sin IA o en revisión no aparece en ningún cálculo; sólo el aprobado entra.

### 7 · `liquidacion-y-emision` · crítico · explore propio

- **Objetivo**: convertir los gastos del mes en la expensa de cada unidad, revisable antes de emitir.
- **Permisos y lecturas (D-106)**: emite y distribuye el super admin y todo administrador del edificio;
  anular o aceptar alertas bloqueantes requiere super admin o administrador principal. Contador y
  consejo leen dentro de su alcance, sin escribir (P39 sigue abierta). El propietario ve ambas
  expensas; el inquilino sólo ordinarias, también en su PDF y links de descarga. Probar que el filtro
  no dependa del navegador ni exponga extraordinarias por descarga directa.
- **Historias**: HU-A4, HU-A5. **Reglas**: R01, R03, R06, R07, R13, R15, R16, R17, R19, R24, R34.
- **Propuestas** (entran si se validan, como código simple; el motor llega en el 6b, D-089): R14
  (cargo recurrente), R35 (vencimiento corrido en el PDF), R37 (los dos importes en el PDF), R38 (bloque de ingresos en la expensa), R40 (períodos en
  orden).
- **Decisiones**: D-024, D-031, D-041, D-047 (puntos 5, 7 y 8), D-055, D-066, D-067, D-069, D-070,
  D-073, D-074, D-075, D-078, D-079, D-080, D-081, D-082, D-084, D-085, D-100.
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
    validar, factura duplicada, gastos en revisión (bloqueante), gastos sin IA (advertencia),
    **coeficientes fuera de tolerancia** (bloqueante duro: lee el informe de R01 del 3a para
    "Generales" y cada grupo con coeficientes propios; es lo que hace cumplir R01, porque la carga del
    padrón no se bloquea, E5 del 3a) y, sobre las consultas que expone el cambio 6, gasto mensual
    obligatorio faltante e ingresos mayores que los gastos. Los controles de pagos, extracto y
    contactos los suman los cambios 8, 9 y 13.
  - **Vencimiento de la liquidación** (D-100, P33): toma el día fijo y la modalidad (único o doble, con
    el recargo en porcentaje) de la configuración vigente del 3a, y permite **correr el vencimiento al
    emitir** una liquidación puntual (un feriado, un ajuste), dejando registrado quién, cuándo, de qué
    día a qué día y el motivo. Correrlo no cambia la configuración del edificio.
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
- **Bloqueado también por la deuda firmada D8 del 4b** (27/10/2026, `knowledge-base/09_decisiones_y_supuestos.md` D-123): qué pasa con un crédito de corrección cuya obligación queda en una emisión anulada (retenido como E16 o a favor). Ver la sección "Deuda firmada D8" del proposal archivado del 4b. Además: `anular_emision` toma los candados de las cuentas de su emisión (D-124); si el 7 anula y re-emite en la misma transacción, respeta el orden de E2.
- **Construye también** (deuda explícita que el 4b dejó para este cambio, "Qué queda fuera" de su proposal):
  - **Cargo cobrado de menos**: un cargo complementario con motivo y vínculo al origen (la obligación o
    el movimiento que cobró de menos), por la misma ruta de corrección del 4b (R08), no un ajuste
    silencioso.
  - **Snapshot de `saldo_anterior`**: el 4b expone sólo el estado actual (E12); este cambio tiene que
    guardar la foto de lo pendiente **después de imputar** al emitir, para que la expensa muestre el
    saldo anterior que regía en ese momento y no el que haya cambiado después.
  - **Autoridad de "anulada"**: el libro (`evento_de_emision`) y la auditoría de emitir/anular son del
    llamador — este cambio es quien emite y quien anula, y por eso es quien audita esas dos acciones
    (E8 del 4b: el libro mismo sólo audita la corrección).
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
- **Que intente romper el rompedor**: emitir con un padrón que suma 0,9998 o aceptar esa alerta;
  correr el vencimiento sin dejar registro; emitir dos veces el mismo período; una preliquidación que
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
- **Deuda de la auditoría de cimientos del 22/10/2026 (DBA-2)**: `grupos.py:90` escanea
  `grupo_unidad` completo para armar la liquidación mensual (Seq Scan sobre 125k filas sintéticas);
  falta un índice con prefijo `(administracion_id, complejo_id)` antes de que este cambio corra con
  datos reales. Detalle en `openspec/exploraciones/2026-10-22-cimientos-antes-del-4.md`.

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
- **Construye también** (deuda explícita que el 4b dejó para este cambio):
  - **Reversión de una bonificación retenida (R37, E16 del 4b)**: cuando se anula la emisión de una
    obligación que ya tenía una bonificación imputada, ese crédito queda **retenido** en vez de
    liberarse; este cambio construye la acción que lo revierte (lo libera como crédito a favor o lo
    reimputa, según se valide R37).
  - **Vocabulario y enlace entre cuentas** (`enlazado_a`, E14 del 4b): el tipo `reversion_de_pago` y el
    enlace entre cuentas de la misma administración ya están sembrados en `tipo_de_movimiento`; este
    cambio es el primer consumidor real al revertir un pago hacia otra cuenta.
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
- **Ciclo**: completo, con aprobación de Juani, Alberto o Emiliano antes de codear (D-077, D-094, D-111). Si R29 sigue sin saber quién
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
- **Vínculos y lecturas (D-106)**: cada propietario ve la cuenta completa de su unidad y cualquiera
  informa un pago; el inquilino sólo ve ordinarias, incluidos los PDFs y comprobantes descargables.
  Una persona puede tener vínculos distintos por unidad. Las lecturas del contador y del consejo
  respetan su alcance y no habilitan escritura ni el acceso al portal de otra persona.
- **Historias**: HU-V1 (pantallas), HU-V2, HU-V3, HU-V5. **Reglas**: R16 (presentación).
- **Entra**: todas las unidades de la persona juntas; deuda y vencimiento según su vínculo; ordinarias
  y extraordinarias para propietarios y sólo ordinarias para inquilinos, por categoría y comparadas
  con el mes anterior; PDFs del vínculo con links firmados y con vencimiento (D-070); app instalable.
  **Crédito a favor separado en dos cifras** (E12/E16 del 4b, que ya devuelve la lectura separada):
  **aplicable** (libre, se descuenta de la próxima expensa) y **retenido** (atado a un destino que
  todavía no se liberó, por ejemplo una bonificación de una emisión anulada); el vecino con $2.000
  retenidos y $0 aplicables sigue viendo su deuda de $40.000 completa, no descontada. Pasa por la
  skill impeccable.
- **Depende de**: 10a y 2b (el vecino tiene que poder entrar). **Habilita**: 12.
- **Distribución** (D-074): la primera vez que un vecino abre una liquidación, el portal llama al
  puerto de distribución del cambio 7.
- **Que intente romper el rompedor**: ver la unidad de otro vecino; números distintos a los del
  administrador; un iPhone sin instalar la app; pantalla de 320 px; abrir un link de descarga
  vencido, modificado o de otra unidad.
- **Terminado cuando**: se cumplen HU-V1, V2, V3 y V5.

### 12 · `vista-del-consejo` · HIGH (D-087)

- **Objetivo**: transparencia para el consejo de propietarios.
- **Lecturas (D-106)**: consejo y contador leen gastos, liquidaciones y comprobantes de su alcance;
  el consejo sólo su edificio, el contador principal toda su administración y el contador por
  edificio sólo los asignados. Ninguno escribe. El consejo tiene una asignación por persona y
  edificio (RR-3). El filtro de inquilino a ordinarias sigue en la vista por unidad del 11; no se
  concede lectura contable de todo el edificio por ser inquilino.
- **Historias**: HU-C1.
- **Entra**: morosidad, gastos, liquidaciones y comprobantes en sólo lectura, con los alcances del
  consejo y del contador definidos en D-106.
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
- **Deuda del 2c con dueño este cambio** (D-101): ver "Deuda del cierre del 2c" más abajo. Lo grueso:
  el proxy con `https://` y la 308, el humo que compara políticas de RLS por conteo, el log a todo nivel,
  la lista de servicios escrita a mano y los `exit 1` del humo sin línea.
- **Depende de**: todos los anteriores y los datos del piloto (P1).
- **Bloqueado por**: P1 (el edificio piloto) y P12.
- **Deuda de la auditoría de cimientos del 22/10/2026 (OPS-3, OPS-4, OPS-5, OPS-6, OPS-7, OPS-8)**:
  ningún modo de falla tiene métrica ni alerta (respaldo fallido, tarea agotada); deploy a producción
  sin documentar y sin rollback de imagen ensayado en producción real; `stderr` de `pg_dump`
  descartado; el `mkdir` del README falla en silencio si se saltea; `-p proptech` con `down -v` en
  scripts de operación puede borrar volúmenes del stack manual; imágenes de ejecución sólo por tag,
  no por digest. Detalle en `openspec/exploraciones/2026-10-22-cimientos-antes-del-4.md`.
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
| Cabeceras de seguridad en Caddy, volúmenes de Caddy, CI con `pull_request`, límites de tiempo y gitleaks fijado por digest, endurecimiento de contenedores, tabla de variables del README | 2c (no hacen al candado, D-097) — **cerrada en el 2c (las cinco cosas, tareas 3.1 a 4.3 y 7.1)** |
| CSP en Next | 2b — **cerrada en el 2b (tarea 6.2)**: CSP estricta con nonce, resuelto E16 |
| Dependabot | 15, propuesto (no lo necesita ni el candado ni el login; va con las imágenes por digest; lo confirma E4 de la aprobación del 2a) |
| `naming_convention` en la base de SQLAlchemy, tipos `Porcentaje` y `Superficie`, versión de la semilla como `Literal[1]`, pydantic declarado como dependencia directa, app con `--factory`, tope de lectura del YAML, test de chmod salteado en Windows, `.gitignore` ampliado, healthcheck de la web contra 127.0.0.1 | 3a (tareas 2.3 y 2.4; el tope del YAML ya estaba hecho) |
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
| F7, resto: "aparece uno solo" no se verifica; los `[ ]` de los pasos 11 y 13 del humo fallan sin decir cuál | No esconde fallas | 2c (confianza media) — **cerrada en el 2c (5.1 y pasos nombrados; los `exit 1` sueltos quedan en C2-5)** |
| El humo nunca congela las dos dependencias de salud a la vez | Lo cubren los unitarios de 5.1 | 2c — **cerrada en el 2c (5.2)** |
| PID 1 no root: el rojo se mostró sólo para `redis`, no para `worker` ni `respaldos` | El assert es idéntico en los tres y lo que se probó es la lectura de `/proc/1/status` | 2c (endurecimiento de contenedores) — **cerrada en el 2c (3.3, rojo en los siete)** |
| La 8.1 (la corrida equivalente al CI) corrió en paralelo y no "en este orden", como pide la tarea (vueltas 2 y 3) | Todos los resultados dieron verde y el repo real se recorrió de nuevo al final | 2a y 2c (cada corrida de cierre dice el orden y por qué) — **cerrada en el 2c (9.1, en orden y de a uno)** |

### Deuda del cierre del 2a (auditoría vuelta 3, D-098)

La que dejó el rompedor al cerrar el 2a, aceptada por Juani como "OK con deuda anotada". Las filas
V3-1, V3-2 y V3-4 (M8 y M5) de la tabla original de la vuelta 3 se cerraron en la vuelta 4 (opción B,
D-098) y no entran acá; V3-4 (M2) sigue abierta. Dueño asignado por el primer cambio que de verdad
necesita que esté resuelta (L-012), no por el que suena más obvio.

| Deuda | Por qué no bloquea | Cambio |
|---|---|---|
| R5: contrato de error del endpoint de asignación | Cerrada en el 2.2a, tarea 4.2: cuerpo por edificio sin vecino, `nivel`, `vinculo` ni `unidad_id`, con 422 por extras incluso con ids válidos ajenos; no escribe ni filtra | 2.2a, cerrada el 20/10/2026 |
| R6: el sweep de rutas protegidas no ve `include_router(prefix=...)` | Hoy no hay fuga (`app.py` sin prefix) | 3a (C-06a), bloqueante antes de su primera ruta nueva (tarea 2.1) |
| R9: la igualdad de tiempo entre 403 y 404 | Necesita una identidad autenticada de la misma administración, que no existe hasta el login | 2b (C-05b) — **cerrada en el 2b (tarea 4.3)**: 200 pedidos por clase, diferencia 0.368ms bajo el umbral de 5ms |
| R11: "el id lo genera siempre el servidor" en las altas | Hoy verificado sin agujero: no hay ninguna alta de complejo ni unidad todavía | 3a (C-06a), tarea 2.2 |
| V2-3: `roles antes` no revoca membresías de `proptech_app`, y la verificación de arranque no las mira | No rompe la letra (D2 promete reparar atributos, no membresías); exige un superusuario que otorgue la membresía a mano y que la app además ejecute `SET ROLE` o DDL | 15 (piloto), antes de operar la base con el superusuario |
| V2-5: la API no nombra en el log por qué no arrancó | La garantía (no arrancar) se cumple y la falla no queda escondida; sólo falta la causa nombrada | 2c (C-05c), junto con el humo con pasos nombrados — **cerrada en el 2c (6.1)** |
| V2-7: el registro de `@accion_sensible` se pisa con la misma `Accion`; el sweep invoca una tabla paralela; el test de `test_auditoria_transaccion.py:416` no puede dar rojo | Hoy hay un solo caso, así que no hay agujero | 2b (C-05b) — **cerrada en el 2b (tarea 4.3)**: el test se reescribió y se vio rojo con un segundo caso |
| V3-4 (M2): la rama `invalidate` de `_checkin` no tiene test | Sin camino real hoy: hace falta un corte de base con tráfico real | 15 (piloto), antes de tener cortes de base con tráfico real |
| V3-5: ningún test pasa por el cableado real de R7 y R8 en el arranque | El arranque real activa las dos protecciones hoy; lo que falta es un test que lo exija, para que una refactorización no las pierda con todo en verde | 2c (C-05c), tarea 6.0. Pasó del 2b al 2c por la respuesta (a) de Juani a P1 del 2c, 16/10/2026 — **cerrada en el 2c (6.0)** |
| V3-6: sin inodos, `--salud` da 0 (no se puede ni crear la marca) | Mucho más raro que el disco lleno; queda declarado acá en vez de con un test | 15 (piloto), revisar con el monitoreo del servidor real |
| V3-7: `despues()` espera sin límite un lock de `auditoria` (sin `lock_timeout`) | Hace falta tráfico real y un redeploy en caliente; hoy no hay ninguno de los dos | 15 (piloto), antes del primer redeploy con usuarios |
| V3-8: flake de `unitarios/test_worker_tenant.py` (9% de las corridas, `"123"` en los metadatos del log) | No esconde una fuga hoy, aunque entrena a ignorar justo el test de L-007 | 2c (C-05c), antes de activar el CI en pull requests — **cerrada en el 2c (4.1)** |
| V3-9: el test de R7 se cuelga en vez de dar rojo (sesiones sin `finally`) | Hoy R7 está cerrado; el riesgo es si vuelve a romperse y el CI se cuelga en vez de mostrar el rojo | 2c (C-05c), junto con el límite de tiempo del CI — **cerrada en el 2c (4.2)** |
| V3-14: `POSTGRES_APP_USER` acepta un nombre que la migración no conoce | Falla ruidoso, sin agujero de seguridad | 2c (C-05c), con la tabla de variables del README — **cerrada en el 2c (6.2)** |
| V3-15: README desactualizado (el worker sí tiene salida, el 1d no está "Propuesto", faltan las contraseñas distintas) y el humo no mira `relrowsecurity` | Dos frases falsas y un requisito no escrito, no una fuga | 2c (C-05c), con la tabla de variables del README y el humo con pasos nombrados — **cerrada en el 2c (7.1 y 5.4)** |
| Chequeo 5: 25 archivos de test de RLS, permisos y rutas que nadie abrió ni mutó | El comportamiento de aislamiento sí se probó de caja negra con scripts propios; lo que no se sabe es si esos tests pueden dar rojo | 15 (piloto), una pasada de mutación antes de cargar datos reales |
| Chequeo 5: ninguna verificación de arranque mira las políticas de las tablas de negocio (`complejo`, `unidad` y las otras), sólo las de `auditoria` | El diseño (D2) sólo promete esa verificación para la auditoría; para el resto no hay promesa rota, pero Juani decidió prometerlo | 15 (piloto) — decisión de Juani, no deuda sin dueño (D-098) |
| D-1: de las 7 comparaciones de `_verificar_politica_de_auditoria`, 5 no tienen test que las exija (nombre, PERMISSIVE, comando, roles, WITH CHECK) | Hoy el código anda (caja negra); son mutantes vivos, no una falla observada | 2b (C-05b), junto con V3-5 — **cerrada en el 2b (tarea 4.3)**: un test por cada comparación, visto rojo con copia mutada |
| D-2: la primera FK legítima hacia `auditoria` frena todo arranque (exit 1 en `despues`, con `SQLSTATE 0A000` y no el texto "FK") | Es lo diseñado (ruidoso en vez de ciego), pero nadie lo documentó como restricción del esquema | 2b (C-05b) — **verificada, no cerrada, en el 2b**: queda escrita en el design como restricción (ninguna FK hacia `auditoria`) y se confirmó que 0019/0020 no agregan ninguna; la primera tabla que sí la necesite vuelve a frenar el arranque, a propósito |
| D-4: `vuelta-3/arbol/backend/.venv` de la copia del rompedor es un symlink al `.venv` real del repo; un `uv run`/`uv sync` desde ahí redirige la instalación editable | Hoy no hay daño (el `.pth` volvió a apuntar al repo); es el entorno de trabajo efímero del rompedor, no el repo | orquestador — borrar el symlink o el `arbol/` entero antes de reusar `vuelta-3/mutar.py`, no es un cambio del roadmap |
| D-5: `infra/ci/humo.sh` está en git como `100644` (sin `+x`); el CI lo corre con `bash` y no falla | Corrido a mano como `./humo.sh` da "Permiso denegado"; no afecta al CI | 2c (C-05c), con el humo con pasos nombrados — **cerrada en el 2c (commit de `humo.sh` con +x)** |
| D-6: el test de M5 detecta "sin sonda de TRUNCATE" sólo porque la palabra `"TRUNCATE"` en mayúsculas no aparece en el aviso de catálogo | El caso de la FK lo sigue cubriendo | 2b (C-05b), con D-1 — **cerrada en el 2b (tarea 4.3)**: sonda que no depende de la palabra en mayúsculas |
| Aviso para el 2b: la primera FK legítima hacia `auditoria` va a frenar cada arranque (V3-2, mismo mecanismo que D-2); contemplarlo antes de agregar cualquier referencia nueva a `auditoria` | Es el comportamiento diseñado, no una falla nueva | Vigente: 0019/0020 no agregaron FK hacia `auditoria`; sigue aplicando al primer cambio que sí lo haga |

D-3 (la evidencia de `tasks.md` 13.3 mostraba otro mutante que el M5 original) no entra en esta tabla:
el rompedor sugirió corregirla "en la misma pasada que V3-10", y se corrigió en ese mismo commit
(`3bbd2a6`).

### Deuda del cierre del 2c (auditoría vuelta 2, D-101)

Cerrado sin vuelta 3 por decisión de Juani. El auditor la leyó como una sola familia: el chequeo
compara un resumen y no el conjunto. Quien la tome, que arregle la familia y no el ejemplo (L-021).

| Deuda | Por qué no bloquea | Cambio |
|---|---|---|
| C2V2-1: con `PROPTECH_SITIO=https://...`, un `Host` ajeno por el 443 sale `200` con `Server: Caddy` y sin las cuatro cabeceras; la 308 de http a https tampoco las lleva | Hoy el stack corre en HTTP y el 443 no escucha; la spec quedó acotada a HTTP y lo dice | 15 (piloto), con el dominio real y HSTS |
| C2V2-2: el test del log (`test_worker_tenant.py`) captura sólo ERROR de un logger; una fuga en WARNING o en otro logger llega al JSON de producción | Anterior al 2c (`741caf2`); hoy ningún WARNING ni INFO emite el valor | 15 (piloto), antes de cargar datos reales |
| C2V2-3: el humo compara la CANTIDAD de políticas de RLS de la base restaurada, no su contenido; `USING (true)` o un renombre pasan | La RLS de la base en uso está intacta; el comentario de `humo.sh` ya declara el límite | 15 (piloto), junto con la prueba de restauración |
| C2V2-6: nada fija qué devuelve el sitio de respaldo (hoy `421` vacío en ocho métodos) | La configuración de hoy es correcta | 15 (piloto), junto con C2V2-1 |
| C2V2-7: la lista de servicios del chequeo de capacidades está escrita a mano; un noveno servicio no lo ve nadie | Hoy hay ocho y los ocho dan rojo | 15 (piloto) |
| C2-5 y C2V2-8: 22 `exit 1` e `if !` del humo sin línea ni comando; `compose()` informa su propia línea | El paso se ve por su encabezado; la spec nombra la excepción | 15 (piloto) |
| C2-7: el conteo de `.dump` en el segundo `up` es una carrera (el comentario de `humo.sh:84-88` es falso) | Hoy no se ve: el volcado tarda menos de 1 s | 15 (piloto) |
| C2-8: `arranque_fallido` no cubre una base inalcanzable ni un `parametros.yaml` mal formado (confirmado con comando en la vuelta 2) | El contenedor igual no arranca; falta la causa nombrada | 15 (piloto), antes del despliegue |
| N2: con la `api` pausada, Caddy no responde en 100 s | Sin tráfico real no muerde | 15 (piloto) |
| N9: el chequeo de PID 1 de `db` se vio rojo sólo con `init: true` | El chequeo funciona; la prueba original no lo mostraba por su cuenta | 15 (piloto), nota |
| N-a: el verificador de cabeceras acepta duplicados y valores sin límite de palabra | No explotable hoy: el `Caddyfile` es correcto | 15 (piloto), con C2V2-1 |
| N-b: el test del log da rojo falso con un campo que contenga "123" | 0 de 200 hoy | 15 (piloto), con C2V2-2 |
| N-c: el tenant por transacción (D4 del 2a) no tiene ningún test que pueda dar rojo; con el tenant por sesión pasan los 900 — **CERRADA** (`7555b59`): `test_set_config_de_administracion_id_no_sobrevive_al_commit_sin_pasar_por_checkin` en `backend/tests/integracion/test_tenant_por_transaccion.py`. Dos sesiones ligadas a la MISMA `Connection` (sin pasar por `checkin`, que tapaba el mutante vía R7); rojo confirmado con `set_config(..., true→false)` (assert en `test_tenant_por_transaccion.py:354`, 2026-10-22 12:48:51) y con quitar el reset del `checkin` (rojo cae en el test preexistente `test_un_set_de_sesion_sin_local_no_contagia_gracias_al_reset_de_checkin`, `test_tenant_por_transaccion.py:306`, 2026-10-22 12:49:21); verde final `10 passed` (2026-10-22 12:49:40) | R7 tapa la fuga, no hay exposición | 3 (C-06), antes de su primera tabla nueva con RLS. Dueño propuesto por el orquestador; lo confirma Juani |

### Deuda del cierre del 2.2a

Cierre del 20/10/2026, `4c24333`. Fuente: `.git/informes-roles/auditor/informe.md`, contrastado con
las correcciones y la evidencia final de `tasks.md` del archivado. La fila 1 (ALTO) quedó resuelta con
la firma aparte de Juani en `610eb4a`; el ensayo pendiente de la fila 2 se amplió a 0018, la línea
de base de la fila 3 se corrigió y la fila 4 atribuyó a Codex sus dos criterios de verificación. Esas
correcciones están cerradas; la revisión independiente y el informe faltante siguen en la tabla.
Quedan estos límites; ninguna fila implica aceptación o dueño confirmado por Juani:

| Deuda o supuesto | Límite al cierre | Cambio |
|---|---|---|
| Auditor fila 2: falta lectura independiente de las correcciones RR | Se probó 0018 sobre el respaldo restaurado, pero eso no reemplaza la revisión independiente de 0018, `escritura.py`, `auditoria.py`, `Estados.tsx` y las seis páginas tocadas por RR | 2b, antes de conectar identidades. Dueño propuesto, no confirmado por Juani |
| Auditor fila 5: el rompedor no repitió los ataques de base ni cotejó las 144 celdas del test de permisos | El auditor cotejó la matriz del código con D3, pero leer los tests del constructor no equivale a un segundo ataque independiente | 2b, antes de usar la matriz con login. Dueño propuesto, no confirmado por Juani |
| RD-2: se supone que no hay producción ni datos reales y que nunca se desplegó | No se verificó externamente; el ensayo usa el respaldo restaurado del humo con dos administraciones inventadas, no un respaldo de producción. Si el supuesto es falso, esa evidencia no alcanza | 15, antes de migrar datos reales; validar antes si aparecen. Dueño propuesto, no confirmado por Juani |
| Auditor fila 3: falta el informe original de Sonnet 6.1/7.1 | Hay comandos en `tasks.md` y logs locales; la comparación se corrigió, pero el resumen del orquestador no reemplaza un informe original para futuras revisiones | Próximo cierre con varios constructores, aplicar el formato de `14_forma_de_trabajo.md`. Dueño propuesto, no confirmado por Juani |

### Deuda del cierre del 3a

La que dejó el cierre del 3a: constructor Codex por bloques, rompedor y auditor en dos vueltas, más los
revisores de rol de backend y DBA sobre el HEAD final (detalle en la ficha del 3a y en
`14_forma_de_trabajo.md`). Dueño asignado por el primer cambio que de verdad necesita que esté resuelta
(L-012), no por el que suena más obvio; donde ese dueño lo propuso el orquestador sin que Juani lo haya
firmado todavía, queda dicho en la fila.

| Deuda | Por qué no bloquea | Cambio |
|---|---|---|
| No hay procedimiento con herramienta para pasar la aplicación a servir desde una base restaurada: `restaurar.sh` reconstruye siempre en una base aparte (D9 del 1d), nunca sobre la activa; 8.1 se cerró con esa limitación anotada en vez de resuelta | La restauración en una base aparte sí se probó entera, con conteos y filas idénticos y `/api/salud` en 200; falta sólo el paso de conmutar la aplicación, no la restauración en sí | 15 (piloto). Dueño propuesto, no confirmado por Juani |
| `complejo.localidad` puede quedar `''` en los edificios que vienen del 2a (el backfill de `0005` usa `server_default=""`); el `CHECK` de texto no vacío de `0016` la excluye a propósito, por ese mismo motivo (RF-D-2, hallado en la propia migración) | La API ya rechaza `''` en `localidad` con 422 (`CuerpoEdificio.localidad`); el agujero es sólo por SQL directo y sólo sobre edificios que ya existían antes del 3a | 3b (editar la localidad desde el padrón y agregar ahí el `CHECK`) |
| RF-B-4: un anónimo puede deducir qué rutas y métodos existen por el 405 con `Allow` y por el 404, fuera del contrato de error de D6 | Ninguna de las dos respuestas revela un dato de negocio, sólo la forma de la API | 2b — **cerrada en el 2b**: Caddy deja de publicar `/api/*` salvo `/api/salud`; un anónimo ya no llega a sondear métodos ni rutas de la API (design D3) |
| Auditoría vuelta 2, fila 6: los diez archivos de test nuevos de la vuelta 2 de correcciones sólo tienen mutantes de su propio autor (Codex); nadie de otra familia los leyó contra los escenarios que dicen cubrir | El rompedor sí los corrió y pasan; falta la lectura independiente, no que fallen | El rompedor del 3b. Dueño propuesto, no confirmado por Juani |
| La versión de configuración con fecha pasada se acepta por SQL, aunque la aplicación la rechaza | Decisión tomada y declarada, no un agujero sin dueño: D-103 deja la excepción a propósito porque la migración de historia de edificios reales la va a necesitar | 7 (migración de historia de edificios reales) |

### Deuda del cierre del 3b

La que dejó el cierre del 3b (20/10/2026): constructor Claude Sonnet por bloques, una vuelta de
rompedor y auditor Claude Opus, con un pulido y un rediseño de UI entre medio (L-026). Dueño asignado
por el primer cambio que de verdad necesita que esté resuelta, no por el que suena más obvio; donde
ese dueño lo propuso el orquestador sin que Juani lo haya firmado todavía, queda dicho en la fila.

| Deuda | Por qué no bloquea | Cambio |
|---|---|---|
| La barra superior muestra "Administración" en vez de un usuario real | La API todavía no expone quién inició sesión (D-105d); mostrar un nombre inventado sería peor que no mostrar ninguno | 2b — **cerrada en el 2b (tarea 7.1)**: muestra nombre, administración, "Salir" y "Cambiar de administración" |
| El encabezado de la tabla de 200 unidades no queda fijo (`sticky`) al bajar la página | La tabla sigue siendo legible, con scroll propio y operable con teclado; es una comodidad, no un defecto de acceso | polish futuro. Dueño propuesto, no confirmado por Juani |
| La versión de configuración con fecha pasada se acepta por SQL, aunque la aplicación la rechaza | No es deuda nueva de este cambio: ya está decidida y declarada en D-103, y ya figura arriba en "Deuda del cierre del 3a" con dueño el cambio 7; no se repite acá | — (ver "Deuda del cierre del 3a") |

### Deuda del cierre del 2b (D-108, 22/10/2026)

Cierre con una vuelta de rompedor y auditor más correcciones post-rompedor, y verificación real
acortada con Juani al teclado (decisión de cierre 2). 7.2 (aviso de privacidad) quedó en borrador, sin
marcar. Dueño asignado por el primer cambio que de verdad necesita que esté resuelta (L-012); donde
ese dueño lo propuso el orquestador sin que Juani lo haya firmado todavía, queda dicho en la fila.

| Deuda | Por qué no bloquea | Cambio |
|---|---|---|
| SU-01: invitar a un email que ya tiene usuario en Clerk, sin verificar contra Clerk real | La 8.2 acortada no llegó a probar este caso; lo que se vio fue el camino de un email nuevo | Antes de que un vecino o personal con cuenta previa necesite una invitación nueva, o antes del 15 (ver `09_decisiones_y_supuestos.md` SU-01) |
| 8.2 acortada (decisión de cierre 2): sin verificar ingreso con link por email, bloqueo por intentos fallidos, selector con una segunda administración, email secundario y cambio del principal, reinvitar con una invitación `enviada`, revocar en vuelo contra Clerk real | Decisión de Juani, no un agujero sin dueño; lo cubierto alcanza para registrarse, entrar, Google y revocar | 15 (piloto), antes de operar con usuarios reales. Dueño propuesto, no confirmado por Juani |
| El rechazo de un Gmail no invitado termina en la página alojada de Clerk, en inglés y fuera de la app | No hay fuga de datos; sólo la experiencia es pobre | polish futuro. Dueño propuesto, no confirmado por Juani |
| Levantar el stack sin `mkdir -p infra/datos-respaldos` del README deja la carpeta como root y el contenedor de respaldos reinicia en bucle | El README ya lo pide; es un error de quien levanta el stack, no del código | DevOps (documentar o automatizar el `mkdir`). Dueño propuesto, no confirmado por Juani |
| Con una sola administración, tras aceptar la invitación se muestra el selector igual (el shape dice "entra directo") | Entra, sólo con un paso de más | 7.1, revisión de UI. Dueño propuesto, no confirmado por Juani |
| Pantalla de personal: el botón "Quitar" cae en la columna de Invitación (desalineado) y se ofrece sobre el único super admin (la API lo rechaza, R2B-2) | La API frena la acción peligrosa; es un defecto visual y de affordance | 7.3, revisión de UI. Dueño propuesto, no confirmado por Juani |
| El menú lateral sólo muestra "Personal": no hay entrada a "Mis edificios" | Se llega por URL directa; falta el acceso desde el menú | 7.1/7.3, revisión de UI. Dueño propuesto, no confirmado por Juani |
| Los logs del worker y de httpx salen sin interpolar (`"HTTP Request: %s %s ..."`) | En producción un error de Clerk no dice a qué URL ni qué respondió; no es una fuga, es falta de información | 15 (piloto), antes de depender de esos logs para diagnosticar. Dueño propuesto, no confirmado por Juani |
| Deuda heredada del 2.2a (filas 2 y 5 de "Deuda del cierre del 2.2a"): revisión independiente de RR-1 a RR-4 y cotejo de las 144 celdas, propuesta como blanco del rompedor del 2b | No se encontró evidencia en `tasks.md` ni en los informes del rompedor/auditor de que se haya ejecutado como acción separada; queda igual que antes del 2b | 2b original lo proponía; sin confirmación, pasa intacta al próximo cambio que toque identidades |
| El aviso de privacidad (`/privacidad`) es un borrador: faltan identidad legal, domicilio y contacto del responsable, y la conservación | Decidido así por Juani (decisión de cierre 3); publicar sin esos datos sería afirmar un cumplimiento legal no verificado | Antes de producción, obligatorio. Dueño: Juani (aprueba el texto final, tarea 7.2) |

### Deuda del cierre de `acceso-de-desarrollo` (3b-bis, D-110; revisión del PR #1, 25/10/2026)

La que dejó la revisión del PR #1 (backend, DBA, QA, arquitecto y auditor; `05-auditor.md`, "Deuda
aceptable"), más lo que Juani decidió el 25/10/2026. Los códigos (BE-, DB-, QA-, AR-) son los de esos
informes. Dueño asignado por el primer cambio que de verdad necesita que esté resuelta (L-012); donde
ese dueño lo propuso el orquestador sin que Juani lo haya firmado todavía, queda dicho en la fila.

| Deuda | Por qué no bloquea | Cambio |
|---|---|---|
| **Cómo se vinculó una cuenta de Clerk a la persona `super_admin` del ejemplo (`…e1`) no está escrito** (BE-1, DB-6, AR-7, QA-4). `ejemplo.py` la crea sin `clerk_usuario_id` ni invitación, y el único camino del código que lo completa es aceptar una invitación (`invitaciones.py:119`); por eso el recorrido de la tarea 1.1 no lo puede repetir otra persona, y tampoco trae capturas | Decisión de Juani (25/10/2026): el vínculo **no se rediseña** (nada de invitaciones para el ejemplo) y queda como deuda registrada. Si el paso fue un `UPDATE` a mano, se aparta de "nunca un punto de entrada que reemplace la identidad" del spec, y eso se ve recién cuando esté escrito | Dueño: **Emiliano**, que tiene que dejar escrito el paso exacto (comando o pantalla, con qué rol y contra qué base) para que otra persona pueda repetir la 1.1 |
| D-110 afirma que las siete pantallas se verificaron "a 1280 px, a 320 px y con teclado", pero ningún revisor de frontend lo miró y no hay capturas ni pasos que se puedan repetir (auditoría final del PR #1) | El cambio no toca la web (`git diff 116a97d..294cda6 -- web` sólo cambia la versión de Next.js); las pantallas son las del 3b, que ya pasaron su propio recorrido | Dueño: **Emiliano**, junto con el paso de vinculación a Clerk de la fila de arriba: capturas a 1280 y 320 px y el recorrido con teclado |
| Dos cuentas de Mailinator quedaron nombradas en `CLAUDE.md`/`AGENTS.md`, en un repo público; las bandejas de Mailinator son públicas (BE-7) | Son cuentas del Clerk **de desarrollo**, no de producción; nadie verificó si siguen activas | **Decidido (P67, 26/10/2026)**: se borran del Clerk de desarrollo. Las direcciones ya no figuran en ningún documento vigente (esta fila incluida) desde el 26/10/2026, pero siguen en el historial de git; borrar las cuentas en Clerk vuelve ese resto inerte sin necesidad de reescribir la historia |
| Contrato de errores del comando: los errores de configuración, de rol y de base salen como traceback crudo, y todo sale con el mismo código 1, incluida la guarda de entorno (BE-3, QA-3) | Es un comando de desarrollo, nunca expuesto a un usuario; el mensaje útil está en la última línea | polish futuro. Dueño propuesto, no confirmado por Juani |
| El comando exige `REDIS_HOST` y `REDIS_PASSWORD` aunque no usa Redis (QA-3) | Con valores cualesquiera corre; sólo es fricción | polish futuro. Dueño propuesto, no confirmado por Juani |
| La comparación de idempotencia sólo se prueba en una de sus ramas: los mutantes M5 a M8 (modo de los grupos, `estado_migracion`, tipo y piso de la unidad, conjunto de grupos) sobreviven; con cualquiera de ellos un ejemplo cambiado se informa como "ya estaba" (QA-2) | Afecta sólo a datos de ejemplo en desarrollo; M3 (la comparación entera) sí muere por la aserción | El próximo cambio que toque `ejemplo.py`. Dueño propuesto, no confirmado por Juani |
| El test de "dos cargas a la vez" no fuerza la concurrencia (pasa igual si los hilos corren uno después del otro) y la rama de reintento con `RuntimeError` no la alcanza ningún test (QA-7, DB-3) | En READ COMMITTED el `INSERT … ON CONFLICT` del perdedor espera al ganador, así que el caso real termina en "ya estaba" | El próximo cambio que toque `ejemplo.py`. Dueño propuesto, no confirmado por Juani |
| `SELECT id FROM complejo … LIMIT 1` sin `ORDER BY`, y la comparación no mira la `persona` del ejemplo (DB-4) | La administración de ejemplo tiene un solo complejo; nada la crea con dos | El próximo cambio que toque `ejemplo.py`. Dueño propuesto, no confirmado por Juani |
| El ejemplo no se puede borrar: `auditoria` y "Generales" lo impiden por diseño (DB-5) | Es la protección correcta; para rehacer el ejemplo se recrea la base de desarrollo | — (se registra para que nadie lo intente borrar por SQL) |
| `ejemplo.py` escribe con SQL directo en tablas de `acceso` (`persona`, `asignacion_rol`), contra D-021, con el precedente de `escritura.py:59`; y el texto de "Risks" del design no coincide con el código (no verifica que exista un `super_admin` y compara contra la semilla) (AR-6, BE-4, DB-7) | El test de fronteras sólo mira imports, no SQL; la RLS sigue aislando | Un caso de uso en `acceso/aplicacion` que `ejemplo.py` llame, en el próximo cambio que toque `acceso`. Dueño propuesto, no confirmado por Juani |
| La cuarentena de dependencias de pnpm (`minimumReleaseAgeExclude`) se salteó para `next@16.4.3` y 9 paquetes `@next/*`, sin el id del CVE ni una decisión que lo registre (BE-6, AR-8) | La subida resuelve un `next build` bloqueado; sacar las entradas cuando 16.4.3 cumpla la antigüedad es barato | Quien toque `web/` primero. Dueño propuesto, no confirmado por Juani |
| Falta un test de guarda de que no existen `backend/desarrollo/` ni `infra/compose.desarrollo.yaml` (QA-5) | Hoy no existen (inspección de QA); el spec lo prohíbe | polish futuro. Dueño propuesto, no confirmado por Juani |

## Pendientes de arranque

- [ ] Pedirle a Alberto los datos del edificio piloto: padrón con coeficientes, facturas y recibo del
  encargado de un mes, y la liquidación de ese mes (P1).
- [x] Contarle a Alberto que los montos van en Decimal, como en su documento (D-046).
- [x] Repositorio limpio y OpenSpec listo.
