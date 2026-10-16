## Why

Las auditorías de Alberto del 13/10 y el cierre del 1d dejaron deuda de infraestructura con dueño "2"
que no cambia quién ve qué dato: cabeceras del proxy, volúmenes de Caddy, el CI que sólo corre en
`push`, contenedores con más privilegios de los que necesitan, PID 1 no root probado en un solo
servicio, un humo que no dice qué paso falló y que nunca congela las dos dependencias a la vez, y una
tabla de variables del README que no existe. Al partir el cambio 2 (**D-097**, a partir de la revisión
del arquitecto del 15/10/2026), esa deuda sale del 2a (el candado) a este cambio, el **2c**, para que la
aprobación CRITICAL del candado no cargue con trabajo de otro perfil de riesgo.

Cubre: **D-051** (las notas de seguridad del 1a: `Via`, `X-Powered-By`, HEAD), **D-087** y **D-089**
(la deuda de las auditorías del 13/10), **D-095** (la deuda del cierre del 1d: F7 resto, la doble
congelada, PID 1 no root, el orden de la 8.1), **D-097** (la partición) y **D-098** (la deuda del cierre
del 2a con dueño 2c: V2-5, V3-8, V3-9, V3-14, V3-15 y D-5). No toca reglas de negocio (R..) ni historias
(HU-..): es infraestructura.

## Gobernanza

**Nivel MEDIUM.** No toca datos de ninguna administración, ni el esquema de la base, ni crea
credenciales o roles. Sí toca, por dos deudas del 2a, código de arranque del candado: V2-5 (`app.py` y
`base_de_datos.py`, para que la causa de un arranque rechazado quede en el log) y V3-14 (`roles.py`,
para rechazar antes un nombre de rol que las migraciones no conocen). Sigue siendo MEDIUM porque las
dos sólo **rechazan antes y nombran la causa**: no cambian quién ve qué dato ni qué rol se usa.

Se construye con checkpoints y sin aprobación previa de un socio (D-094: MEDIUM no la necesita). Las
decisiones no obvias del design se muestran a Juani en el informe del constructor.

**Regla de freno, en voz alta**: si una tarea toca el arranque del candado (`app.py` o `roles.py`, por
V2-5 y V3-14) y aparece algo que afecte el aislamiento (quién ve qué dato, qué rol conecta, qué
protección de R7 o R8 se activa), **se frena y se consulta a Juani** antes de seguir; si hace falta,
pasa a un cambio CRITICAL. Lo mismo para cualquier otra tarea donde aparezca algo que cambie quién ve
qué dato.

Revisado por DevOps el 16/10/2026 contra `d0502fa`; cambios aprobados por Juani.

## Preguntas para Juani

- **P1 · V2-5 toca `lifespan` y V3-5 lo pide antes.** `verificar_rol_de_aplicacion_seguro` corre
  dentro de `lifespan` (`app.py`). La deuda V3-5 del 2a (dueño 2b, D-098) dice que hace falta un test del
  cableado real de R7 y R8 en el arranque "antes de tocar `lifespan` u `on_startup`". Hacer V2-5 acá
  adelanta ese toque al 2c. Opciones: (a) traer V3-5 al 2c, antes de la tarea 6.1; (b) hacer V2-5 sin
  tocar `lifespan` (la línea del log sale de donde se levanta el error, en `base_de_datos.py` y en la
  construcción de `Configuracion`), y V3-5 sigue en el 2b; (c) pasar V2-5 al 2b, junto con V3-5.
  **Respuesta de Juani (16/10/2026): (a).** V3-5 pasa del 2b al 2c como tarea 6.0, y la 6.1 arranca
  recién con la 6.0 en verde.

## What Changes

- **Cabeceras de seguridad en Caddy** (`nosniff`, `Referrer-Policy`, `X-Frame-Options`,
  `Permissions-Policy`), sin `Server`, `Via` ni `X-Powered-By` (también lo que viene de la web y la API,
  y los 502 que genera el propio Caddy), y HEAD con las mismas cabeceras que GET.
- **Volúmenes de Caddy** para `/data` y `/config`, verificados con `instance.uuid` tras recrearlo.
- **Contenedores endurecidos**: `no-new-privileges` en todos los servicios, `cap_drop: [ALL]` con sólo
  las capacidades que cada uno necesita (probadas sobre volúmenes nuevos y existentes), verificado en el
  proceso vivo; PID 1 no root verificado en siete servicios (`api`, `web`, `worker`, `migraciones`,
  `respaldos`, `redis`, `db`), con el rojo visto en cada uno; `caddy` root declarado.
- **CI**: también en `pull_request`, sin perder `push` a `main` ni `workflow_dispatch`; `timeout-minutes`
  medidos en cada trabajo; gitleaks y `shellcheck` fijados por digest; antes, el flake de
  `test_worker_tenant.py` (V3-8) y el cuelgue del test de R7 (V3-9).
- **Humo**: cada paso dice su número, descripción, línea y comando al fallar; vuelca estado y logs antes
  de bajar el stack; un respaldo exacto por arranque; la base y Redis congelados a la vez; las cabeceras
  de punta a punta, con el 502; `relrowsecurity` en la base restaurada; `humo.sh` ejecutable.
- **Arranque** (deuda del 2a): la causa de un arranque rechazado en el log (V2-5) y el rechazo temprano
  de un nombre de rol que las migraciones no conocen (V3-14).
- **Una sola tabla de variables**, en el README, con un test en los dos sentidos; `08` la enlaza.
- **Rollback ejercitado** sobre volúmenes con datos y **clon limpio** con los comandos del README.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `entorno-de-ejecucion`: cabeceras del proxy (con el 502 de Caddy), volúmenes de Caddy, contenedores
  endurecidos verificados en el proceso vivo, PID 1 no root en siete servicios (MODIFIED de
  "Contenedores sin privilegios de root") y la causa de un arranque rechazado en el log.
- `integracion-continua`: CI en pull requests con límite de tiempo y gitleaks y `shellcheck` por
  digest (MODIFIED de "Verificaciones en cada push"); pasos del humo con nombre y logs al fallar, un
  respaldo por arranque, la doble congelada, las cabeceras de punta a punta y `relrowsecurity`.

## Que intente romper el rompedor

- Una respuesta que se escapa sin cabeceras: un error 502 de Caddy, una redirección de Next, un 404 de
  la API, un HEAD.
- `Via` o `X-Powered-By` que vuelven desde atrás del proxy.
- Un servicio que arranca como root porque una imagen cambió su `USER`, y el chequeo que no lo ve
  (L-016).
- Una capacidad de más que nadie justificó, o una de menos que sólo rompe al reiniciar sobre un volumen
  existente; un `cap_drop` que está en el YAML y no en el proceso.
- Un `user: "0:0"` en `db` o `redis` que el chequeo de PID 1 no ve porque `gosu` baja igual.
- Un trabajo del CI que cuelga sin límite, un pull request que no corre el CI, un tag de gitleaks
  re-publicado con otro contenido.
- Un paso del humo que falla sin decir cuál, un arranque de `respaldos` que deja dos `.dump`, la doble
  congelada que deja `db` o `redis` pausados si el paso falla (L-014), y una falla cuyo log se pierde
  con el `down -v`.
- Una variable de `.env.example` o de `compose.yaml` que no está en la tabla, o una fila que nombra una
  variable que ya no existe.
- Un arranque rechazado cuyo log no dice por qué, o que lo dice mostrando una contraseña.
- Un rollback que no vuelve: volúmenes creados por el 2c que `d0502fa` no puede abrir.

## Lecciones que aplican

| Lección | Tareas |
|---|---|
| L-001 · dependencia que no responde | 5.2 (base y Redis congelados a la vez) |
| L-002 · la configuración se rompe de muchas formas | 6.2 |
| L-003 · contar los tests | 1.1, 4.1 y 9.1 |
| L-004 · otro camino | 3.1 (tests estáticos del `Caddyfile`) contra 5.3 (las cabeceras de punta a punta por el proxy) |
| L-005 · verde es todo el workflow | 4.3, 7.1 y 9.1 |
| L-006 · un comando destructivo apunta a un nombre único | 8.1 |
| L-007 · el mensaje de error también es una salida | 4.1, 6.1 y 6.2 |
| L-009 · el gemelo | 6.1 (`api` y `worker`) |
| L-010 · la corrida de cierre va al final | 9.1 |
| L-013 · mutar sin commit exige copia | 2.2, 3.2, 3.3, 3.4, 4.2, 5.1, 5.2, 5.4 y 6.1 |
| L-014 · `set -e` dentro de `||` | 2.1 (el `trap ERR` no salta en condiciones: los `if !` se quedan) y 5.2 |
| L-016 · una observación tiene que poder dar otro resultado | 3.3 (rojo en cada uno de los siete, salteando `gosu` en `db` y `redis`), 3.4, 5.1, 5.3 |
| L-018 · verificar el efecto, no la forma | 2.1 (test de efecto de los helpers), 3.4 (capacidades en el proceso vivo), 5.4 (`relrowsecurity`) |
| L-019 · un test que no puede dar rojo | se saca "HEAD sin cuerpo" (no puede fallar); 4.1 y 4.2 |
| L-020 · arreglar un bloqueante puede crear otro | 4.2 (el arreglo de las sesiones de R7) |

## Fuera del cambio

- **Todo lo que hace al candado** (2a): roles, RLS, credenciales por rol, la web fuera de la red de la
  base.
- **CSP en Next** (2b): una CSP sin pantallas no prueba nada.
- **HSTS** y el dominio real: con el despliegue (cambio 15).
- **Dependabot**: cambio 15 (E4 del 2a).
- **Secretos de Compose** (la contraseña del rol de arranque en el entorno del contenedor terminado de
  `migraciones`): con el despliegue (cambio 15).
- **`REDIS_PASSWORD` en la línea de comando** de `redis-server` (`--requirepass`), visible en
  `docker inspect` y en `/proc/1/cmdline`, y **todas las contraseñas de los servicios en el `Config.Env`
  de `docker inspect`**: con el despliegue (cambio 15; origen: revisión del 2c, 16/10/2026).
- **`read_only`, imágenes base por digest y monitoreo fuera del CI**: con el despliegue (cambio 15).

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 16/10/2026): `01_vision_y_objetivos.md`,
`02_descripcion_general.md`, `03_actores_y_roles.md`, `04_modelo_de_datos.md`,
`05_reglas_de_negocio.md`, `06_funcionalidades.md`, `07_flujos_principales.md`,
`08_arquitectura_propuesta.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`,
`11_glosario.md`, `12_fichas_de_changes.md`, `13_motor_de_reglas.md`, `14_forma_de_trabajo.md`,
`15_lecciones.md`, `16_proyecto_final.md`, `README.md`.

- `12_fichas_de_changes.md`: **REWRITE** de la ficha 2c (cierre: estado, tareas hechas) y de las filas
  de deuda que resuelve: las del 13/10 con dueño 2c, las del 1d (F7 resto, doble congelada, PID 1, orden
  de la 8.1) y las del 2a (V2-5, V3-8, V3-9, V3-14, V3-15, D-5). La ficha 2c y la del 15 ya se tocaron
  en esta propuesta (cuenta de tareas, "Terminado cuando", la deuda nueva del 15).
- `08_arquitectura_propuesta.md`: **REWRITE** de la sección de seguridad (cabeceras, contenedores,
  capacidades por servicio, `caddy` root declarado) y de la tabla de variables, que se reemplaza por un
  enlace a la del README (antes se corrige la fila de `POSTGRES_USER`, que hoy miente).
- `09_decisiones_y_supuestos.md`: **APPEND** de una decisión con las elecciones de código del 2c
  (capacidades por servicio y en qué situación hizo falta cada una, digests de gitleaks y `shellcheck`,
  el mecanismo para los errores de Caddy, una sola tabla de variables) y, si Juani la toma, la
  respuesta a P1.
- `15_lecciones.md`: **APPEND** de lo que proponga el auditor al cerrar.
- `01` a `07`, `10`, `11`, `13`, `14`, `16` y `README.md` de la base: none. No cambia ninguna regla,
  historia, flujo, pregunta ni término.
- Fuera de `knowledge-base/`: `CHANGES.md` (**REWRITE** del estado de C-05c al archivar; el alcance ya
  se actualizó en esta propuesta) y el `README.md` de la raíz (la tabla única de variables y las frases
  de V3-15).

## Impact

- **Infra**: `infra/compose.yaml`, `infra/Caddyfile`, `infra/ci/humo.sh` (y su modo `100755`),
  `infra/ci/pasos.sh` (nuevo), `.github/workflows/ci.yml`, `web/next.config.ts`, `README.md`.
- **Backend** (sólo por la deuda del 2a, bajo la regla de freno): `backend/src/proptech_api/app.py`,
  `backend/src/proptech_core/compartido/base_de_datos.py`, `backend/src/proptech_core/compartido/roles.py`,
  el arranque del worker (gemelo, L-009), `backend/migraciones/` (lectura de `_ROL_DE_LA_APP`) y
  `backend/pyproject.toml` (`faulthandler_timeout`).
- **Tests**: `backend/tests/infra/` (`test_compose.py`, `test_caddyfile_seguridad.py`,
  `test_ci_workflow.py`, `test_humo.py`, `test_pasos_humo.py`, `test_readme_variables.py`),
  `backend/tests/unitarios/test_worker_tenant.py` (V3-8), `backend/tests/integracion/test_tenant_por_transaccion.py`
  (V3-9) y los de configuración y roles que cubran V2-5 y V3-14.
- **Knowledge base**: `knowledge-base/08_arquitectura_propuesta.md` (la tabla pasa a enlace).
- **Dependencias nuevas**: ninguna. **Contrato de la API**: ninguno.
- **Depende de**: 2a (los dos tocan `compose.yaml` y `humo.sh`; en secuencia no se pisan).
