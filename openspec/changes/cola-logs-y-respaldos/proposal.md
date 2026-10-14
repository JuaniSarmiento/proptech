## Why

Es la segunda mitad del `arranque-del-sistema` original, partido porque no entraba en una vuelta del
constructor, y a su vez partido en dos por la auditoría de Alberto del 13/10 (D-087): este cambio (1c)
deja la cola, los logs y el número de seguimiento; los respaldos, la restauración, el humo ampliado y
el README pasan a `respaldos-y-restauracion` (1d). El nombre del cambio conserva "respaldos" porque el
CLI de OpenSpec no renombra cambios; su alcance es el de esta propuesta.

`arranque-del-sistema` dejó los parámetros, el monto y la semilla; faltan las piezas transversales de
operación que todos los cambios siguientes dan por existentes: una cola con worker para lo lento
(PDFs, emails, IA), un número de seguimiento por pedido para reconstruir cualquier reclamo y logs que
no filtren datos. Si cada cambio de M1 las inventa a su manera, el 7 (liquidación) y el 13 (emails)
se construyen sobre convenciones distintas. Completa la ficha `1c` de `conocimiento/roadmap.md` y
habilita al cambio 1d.

Decisiones que cubre: **D-038** (Redis y worker ARQ con reintentos espaciados e idempotencia),
**D-047 punto 4** en su parte de logs estructurados con número de seguimiento (los backups automáticos
de ese punto van en el 1d) y **D-087** (la partición y las lecciones L-007 a L-009) y **D-052** (la regla de partir un cambio grande). No toca ninguna
regla de negocio (R..) ni historia (HU-..): es infraestructura.

## Gobernanza

**Nivel MEDIUM.** Lógica de infraestructura con checkpoints: no toca cobros, cuenta corriente,
autenticación ni datos de usuario, no borra datos ni escribe fuera de los volúmenes de Docker. La
única tabla nueva (`trabajos_hechos`) es técnica y se crea vacía. Sigue el ciclo completo
(constructor, rompedor y auditor, `forma-de-trabajo.md`) sin aprobación previa de Juani; el
orquestador le muestra las decisiones no obvias que aparezcan al construir.

**Tamaño: 35 tareas** (`tasks.md`; la 1.1 ya está hecha). D-088 registró 29 como excepción; la tercera
auditoría del socio (13/10) sumó seis tareas y varios casos a tareas existentes (ver `design.md`,
Risks). La cifra nueva necesita su decisión en `conocimiento/decisiones.md`.

## What Changes

- **Redis** (`redis:8.10.2-trixie`) en la red `interna`, con contraseña, persistencia en disco y sin
  puertos publicados.
- **Worker ARQ** como servicio aparte que usa la misma imagen que la API con otro comando. Tiene una
  tarea de prueba, reintentos espaciados sólo para errores pasajeros, tope de intentos e
  idempotencia en dos capas (clave del trabajo en la cola y clave única en la base, en la misma
  transacción que el efecto). Los trabajos viajan serializados en JSON, nunca con `pickle`, y `encolar`
  rechaza `float`, `Decimal` y todo tipo fuera de la lista blanca con un error que nombra el campo.
  No arranca con configuración o parámetros inválidos, con los mismos tests de arranque que ya tiene
  la API. Tiene una red de salida a Internet propia, sin la base ni Redis, para los cambios 13 y 14.
- **Migración `0002`** con la tabla técnica `trabajos_hechos` (clave de idempotencia). Es la primera
  tabla del sistema y no es de dominio.
- **Logs estructurados en JSON**, una línea por evento, con una lista cerrada de campos, sin cuerpos,
  sin query strings, sin mensajes de excepción, sin los argumentos de los mensajes, sin los argumentos
  ni el resultado de los trabajos y sin el texto de los errores de Redis, ARQ o psycopg. Alembic deja
  de apagar los loggers existentes y los logs de error de Caddy pierden la URI y los encabezados.
- **Número de seguimiento (`request_id`)**: Caddy lo genera siempre y pisa el que venga de Internet;
  la web lo reenvía a la API; la API lo valida (coincidencia completa, sólo ASCII, con una tabla de
  casos compartida con la web), lo pone en cada línea de log, lo devuelve en la respuesta y lo anota en
  la conexión a PostgreSQL (`application_name`); el worker lo adopta del trabajo encolado.
- **Ruta técnica de la web** `GET /salud-web` (sin interfaz) que consulta la salud de la API
  reenviando el `request_id`, con un contrato de respuesta cerrado.
- **Endpoint de salud ampliado**: informa también si la cola responde. **BREAKING** para quien lea el
  cuerpo exacto: se agrega el campo `cola`. Usa un único engine por proceso, creado en el lifespan, con
  los parámetros del pool desde la configuración y acotado aunque la conexión ya esté abierta.
- **Configuración**: las contraseñas de la base y de Redis pasan a `SecretStr`; la URL con contraseña
  se arma sólo al crear la conexión.
- **`Dinero` copiable y serializable**: `copy`, `deepcopy`, `model_copy(deep=True)` y `pickle` dejan
  de fallar; la reconstrucción pasa por la validación.
- **Uvicorn** con `--no-access-log` y `--proxy-headers`, confiando sólo en la dirección de Caddy.
- **PyYAML** sube a `>=6.0.3,<7` (no hay wheel de 6.0.2 para Python 3.14 en Windows).
- **Rotación de logs** de todos los contenedores.
- **CI**: los tests de integración corren también contra Redis real y el chequeo de imagen real cubre
  Redis. El humo existente sigue corriendo y, como levanta con `--wait`, espera a Redis y al worker
  saludables; su ampliación es del 1d.

## Capabilities

### New Capabilities

- `cola-de-trabajos`: cómo se encola un trabajo, cómo lo ejecuta el worker, qué se reintenta y cuánto
  se espera, cuándo se abandona, por qué un trabajo repetido no duplica su efecto y qué valida el
  worker al arrancar.
- `trazabilidad-y-logs`: formato del log, campos permitidos, qué nunca se loguea, cómo se valida y
  viaja el `request_id` por cada salto y el contrato de `/salud-web`.

### Modified Capabilities

- `entorno-de-ejecucion`: el arranque incluye Redis y el worker; el endpoint de salud informa la cola;
  Redis y el worker también sin root y sin puertos; la configuración de Redis llega también al worker;
  rotación de logs; la red de salida del worker; la API detrás del proxy; el engine único con su pool;
  las contraseñas como secreto.
- `integracion-continua`: los tests de integración corren también contra Redis real y el chequeo de
  imagen real cubre Redis; PyYAML en una versión con wheels para Python 3.14.
- `representacion-de-montos`: un monto se puede copiar y serializar sin perder la validación.

## Lecciones que aplican

Se leyó `conocimiento/lecciones.md` entero (L-001 a L-009). Cómo las cubre cada tarea, en detalle, en
`design.md` ("Cómo aplica cada lección"); en resumen:

| Lección | Tareas |
|---|---|
| L-001 · dependencia apagada, que no responde y lenta | 3.6 (base pausada con una conexión abierta en el pool), 4.5 (Redis en los tres estados), 4.7 (salud con Redis detenido y pausado), 5.8 (base pausada durante un trabajo), 6.3 (API que no contesta) |
| L-002 · configuración rota de muchas formas | 3.5 (contraseñas como secreto), 3.6 (parámetros del pool), 5.9 (arranque del worker: faltante, vacía, en blanco, tipo y rango) |
| L-003 · contar los tests | 1.1 (línea de base), 1.2 (línea de base sobre un clon con historial) y 7.1 (comparación) |
| L-004 · otro camino, no el mismo | design.md: los caminos del `request_id` que cubren los tests, para que el rompedor ataque por otro |
| L-005 · verde es todo el workflow | convención de `tasks.md` y 7.1 |
| L-006 · lo destructivo apunta a `proptech` | 3.6, 4.5 y 5.8: los tests que detienen o pausan usan contenedores propios del test, nunca el de sesión ni el de Compose |
| L-007 · el error de una librería también es una salida | 2.2, 3.3, 3.5, 3.6, 4.4, 4.5, 4.6, 5.3, 5.6, 5.7, 5.9, 6.3, 6.4 |
| L-008 · `fullmatch` y sólo ASCII | 3.1 y 6.1 (validación del `request_id` con su tabla de casos), 4.3 (`Dinero` reconstruido desde su texto), 5.4 (`fallar_veces` entero estricto) |
| L-009 · el arreglo de un módulo se prueba en su gemelo | 3.1 y 6.1 (una tabla para Python y TypeScript), 4.6 (los dos verificadores de salud), 5.9 (los cuatro tests de arranque de la API, replicados en el worker), 3.6 (el pool de la API y el del worker con los mismos parámetros) |

## Fuera del cambio

- **Respaldos, restauración, humo ampliado y README**: cambio 1d `respaldos-y-restauracion` (D-087).
  Los escenarios de punta a punta a través del proxy (`request_id` elegido por el cliente, de la web a
  la API, hasta el worker con un reintento, Redis pausado) se verifican acá por partes (tests de
  configuración, de la ruta y de integración) y de punta a punta en el humo del 1d.
- **Parámetros, `Dinero`, semilla y configuración de Redis en la API**: hechos en `arranque-del-sistema`.
- **Usuarios, login, roles, tenant y Row-Level Security**: cambio 2. `trabajos_hechos` nace sin
  `administracion_id`; el cambio 2 decide si lo lleva, según su plan de RLS (D-087).
- **Tareas reales del worker** (PDF, email, IA): cambios 7, 13 y 14. La red de salida del worker se
  declara acá (tercera auditoría, M18); lo que viaja por ella es de esos cambios.
- **Pantallas**: la única pieza nueva de la web es una ruta técnica que devuelve JSON.
- **Rate limiting en Redis**: cambio 2 (login).
- **Lo de código de la auditoría** que no es de este alcance (D-087: cabeceras de seguridad, volúmenes
  de Caddy, CI en pull requests, tipos Porcentaje y Superficie, convención de nombres de la base). De
  esa lista, `Dinero` copiable y el engine único del endpoint de salud entran a este cambio por pedido
  de la tercera auditoría del socio (13/10).

## Knowledge Base Impact

- `conocimiento/decisiones.md`: **APPEND**. Una decisión con las elecciones de este cambio (versiones
  de Redis, ARQ y redis-py; JSON en vez de `pickle`; formato del log y lista cerrada de campos;
  `request_id` como UUID pisado por Caddy y validado con una tabla de casos compartida).
- `conocimiento/roadmap.md`: **REWRITE** de la ficha 1c (marcarla ✅) y de la ficha 2 para que decida
  si `trabajos_hechos` lleva `administracion_id` y cómo fija el tenant el worker sobre el `request_id`
  ya existente.
- `conocimiento/glosario.md`: **APPEND** de "número de seguimiento (`request_id`)", "clave de
  idempotencia" y "trabajo / tarea del worker", si no están.
- `conocimiento/lecciones.md`: lo propone el auditor al cerrar; este cambio no lo escribe.
- `conocimiento/reglas-de-negocio.md` y `conocimiento/mvp.md`: none. No cambia ninguna regla ni
  historia.

## Impact

- **Código**: `backend/src/proptech_core/compartido/` (logs, seguimiento, cola, idempotencia),
  `backend/src/proptech_api/` (middleware de seguimiento, salud, manejo de errores),
  `backend/src/proptech_worker/` (ajustes, tarea y comando de prueba),
  `backend/migraciones/versions/0002_*`, `web/src/lib/seguimiento.ts`, `web/src/app/salud-web/route.ts`.
- **Datos de test compartidos**: `config/contratos/request-id.json` (tabla de casos del `request_id`,
  la leen pytest y Vitest).
- **Infra**: `infra/compose.yaml` (servicios `redis` y `worker`; red `salida_worker`; subred de
  `interna` y dirección fija de `caddy`; rotación de logs; `log_line_prefix` de PostgreSQL;
  `PROPTECH_URL_API_INTERNA` en `web`), `backend/Dockerfile` (`--no-access-log`, `--proxy-headers`),
  `infra/Caddyfile` (`X-Request-ID` y filtro de los logs de error).
- **Dependencias nuevas**: `arq==0.28.0`, `redis[hiredis]` 5.3.x (ARQ exige `<6`). PyYAML sube a
  `>=6.0.3,<7`. Sin dependencias nuevas en la web.
- **Configuración nueva**: `PROPTECH_URL_API_INTERNA` y `FORWARDED_ALLOW_IPS` (fijas en Compose, no son
  secreto); `DB_POOL_PRE_PING`, `DB_POOL_SIZE`, `DB_POOL_RECYCLE_S`, `DB_POOL_TIMEOUT_S` y
  `DB_CONNECT_TIMEOUT_S`, opcionales con default. Ninguna variable obligatoria nueva en `.env`.
- **Otros archivos**: `backend/migraciones/env.py` (`disable_existing_loggers=False`),
  `backend/src/proptech_core/compartido/dinero.py` (`__reduce__`, `__copy__`, `__deepcopy__`),
  `backend/src/proptech_core/compartido/configuracion.py` (`SecretStr`, parámetros del pool).
- **Contrato**: `GET /api/salud` agrega el campo `cola`; toda respuesta de la API lleva `X-Request-ID`;
  `GET /salud-web` nuevo.
