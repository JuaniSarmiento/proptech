# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| Monolito modular, hexagonal por módulo | `backend/src/proptech_core`, un módulo por dominio (`complejos`, `acceso`, `gastos`, `liquidacion`, `cuenta_corriente`, `pagos`, `avisos`, `politicas`, `compartido`), cada uno con `dominio/`, `aplicacion/`, `puertos.py`, `adaptadores/` | Un equipo chico no necesita el costo de desplegar y depurar microservicios; las dependencias apuntan hacia adentro y los módulos sólo se hablan por su capa `aplicacion` (D-021, D-040) |
| Puerto y adaptador (hexagonal) para reglas propias de cada edificio | `politicas/puertos.py` (`MotorDePoliticas`) con un único adaptador real, GoRules ZEN | Si ZEN deja de convenir, se cambia el adaptador y nada más (D-064, D-066) |
| Multi-tenant con Row-Level Security | Toda tabla de una administración, con `administracion_id` y una política RLS forzada | La administración (el tenant) sale de la identidad autenticada, nunca de un parámetro del cliente; RLS es el segundo candado (R10, D-076) |
| Libro de sólo agregar (append-only ledger) | `cuenta_corriente`: ningún movimiento se edita ni se borra | Permite reconstruir cualquier reclamo de un vecino y es la base del aislamiento y la auditoría (R08, D-016) |
| Cola de trabajos con worker aparte | Redis + ARQ para PDFs, emails y lectura de facturas con IA, con reintentos espaciados e idempotencia | Generar PDFs, mandar emails y llamar a la IA mientras el usuario espera no escala ni con un edificio chico (D-038) |
| Verificaciones de salud en paralelo con un plazo total compartido | `GET /api/salud`: la base y la cola se verifican cada una en su propio hilo, con su propia copia de contexto, contra un único `PLAZO_TOTAL_SALUD_S = 1,5 s` | Con las dos verificaciones en serie, una dependencia congelada deja la respuesta por encima de los 2 s con los que `/salud-web` corta (D20, D-095) |

## Estructura de directorios

```
proptech/
├── knowledge-base/           # esta base (Active Stack v1, D-093)
├── openspec/                 # cambios del ciclo OPSX
├── config/
│   ├── parametros.yaml       # valores con que arranca cada edificio nuevo (D-042)
│   ├── semilla/              # edificio-ejemplo.yaml (D-053)
│   └── contratos/            # request-id.json (contrato de `request_id`, L-008)
├── web/                      # Next.js (App Router), áreas (admin) (consejo) (vecino)
├── backend/
│   └── src/
│       ├── proptech_core/    # dominio compartido por módulo
│       │   ├── complejos/
│       │   ├── acceso/
│       │   ├── gastos/
│       │   ├── liquidacion/
│       │   ├── cuenta_corriente/
│       │   ├── pagos/
│       │   ├── avisos/
│       │   ├── politicas/    # el motor de reglas, 13_motor_de_reglas.md
│       │   └── compartido/   # Dinero, sesión de base, tenancy, auditoría
│       ├── proptech_api/     # routers FastAPI
│       └── proptech_worker/  # tareas (ARQ)
└── infra/                    # Docker Compose, Caddyfile, backups
```

Detalle completo de la decisión en `09_decisiones_y_supuestos.md` (D-040).

## Fronteras entre módulos

Dirección de dependencia fijada al cerrar el cambio 2a (ficha 2a de `12_fichas_de_changes.md`):
**`complejos` (y los módulos que colgarán de un edificio: 7, 8, 10b) → `acceso` → `compartido`**.
`acceso` no importa `complejos`, y `compartido` no importa `acceso`: la sesión de base y el tenant son
genéricos (`compartido`), la autorización y la auditoría son del dominio (`acceso`), y los módulos de
negocio que necesitan alcance por edificio dependen de `acceso`, nunca al revés. Cruzar esta dirección
(por ejemplo, que `acceso` importe algo de `complejos` para resolver un nombre de edificio) es la
regresión que el guardián de fronteras del cambio 3 en adelante tiene que impedir.

## Seguridad

- **Autenticación**: login del personal y enlace mágico o alternativa para el vecino; el método
  concreto se decide en el *design* del cambio 2b `login` (D-039, D-043, D-097). El servidor de
  Next guarda el token de sesión; el navegador nunca lo ve (D-036). **Hoy (hasta el 2b)**: la identidad
  se inyecta directamente en los tests (`identidad_actual` da 401 en producción, D7); no hay login real.
- **Cuatro roles de PostgreSQL, uno por responsabilidad** (cambio 2a, D-082, E5): el **rol de arranque**
  (`POSTGRES_USER`/`POSTGRES_PASSWORD`, el superusuario de la imagen oficial; crea y repara los otros
  tres roles con `roles.py antes`/`despues`, y es el único dueño de `auditoria`); `proptech_migrador`
  (`POSTGRES_MIGRADOR_USER`/`POSTGRES_MIGRADOR_PASSWORD`, dueño de las tablas de dominio, corre Alembic;
  sin `BYPASSRLS`, E1: sembrar datos exige fijar el tenant a propósito, igual que la app);
  `proptech_app` (`POSTGRES_APP_USER`/`POSTGRES_APP_PASSWORD`, la usan la API y el worker; sin
  superusuario ni `BYPASSRLS`); `proptech_respaldo` (`POSTGRES_RESPALDO_USER`/
  `POSTGRES_RESPALDO_PASSWORD`, sin superusuario, con `BYPASSRLS` y `pg_read_all_data`, sólo para
  `pg_dump`). Ningún servicio permanente tiene la contraseña del superusuario (R8).
- **Autorización**: tres capas: administración (tenant, deducida del login), alcance por edificio
  según el rol, permiso por acción (D-037, matriz de D-096). Fuera de alcance responde 404; sin permiso,
  403 con el permiso faltante. Row-Level Security de PostgreSQL es el segundo candado del aislamiento
  entre administraciones (R10, D-076), con `SET LOCAL` por transacción y `current_setting(...,
  missing_ok=true)` + `nullif` para que una conexión sin tenant fijado falle cerrada, nunca abierta.
- **Auditoría de acciones sensibles** (D-016, D9, cambio 2a): tabla `auditoria`, de sólo agregar (dos
  triggers bloquean `UPDATE`, `DELETE` y `TRUNCATE` para cualquier rol, incluido su dueño), dueña el rol
  de arranque; vocabulario cerrado en `accion_de_auditoria` (sumar una acción exige una migración). Ver
  `04_modelo_de_datos.md` para el detalle de columnas.
- **Redes** (D10, cambio 2a: `interna` se parte en dos; `infra/compose.yaml`): `datos` (`internal:
  true`) es la única red que alcanza `db` y `redis`; la **web nunca está en ella** — sólo la API y el
  worker. `aplicacion` (`internal: true`) conecta la API, la web y Caddy, con la IP fija de Caddy para
  que `FORWARDED_ALLOW_IPS` la reconozca. `salida_worker`, sin `internal`, da salida a Internet sólo al
  worker (proveedores de email e IA de cambios posteriores), y ningún otro servicio la integra. `borde`
  es la única red publicada (Caddy).
- **Validación de input**: todo monto es `Decimal` construido desde texto, nunca desde `float`
  (R07, D-046); el núcleo arma los datos con tipos fijos antes de llamar al motor de reglas y rechaza
  cualquier dato faltante o mal tipado (R33). Todo texto externo se valida con coincidencia completa y
  sólo ASCII (lección L-008 de `15_lecciones.md`).
- **Secrets management**: nunca secretos ni datos personales reales en el repositorio, que es público
  (`infra/.env.example` sin valores reales); contraseñas como `SecretStr`; el mensaje de error de una
  librería de terceros nunca repite la entrada ni un secreto (lección L-007).
- **Descargas**: ningún archivo (PDF de expensas, comprobantes, facturas) tiene una dirección pública;
  cada descarga usa un link firmado que vence entre un minuto y una hora, y responde "no encontrado"
  si está vencido, modificado o pedido por quien no tiene acceso a esa unidad (D-070).

## Variables de entorno

Verificado contra `infra/.env.example`, `infra/compose.yaml` y
`backend/src/proptech_core/compartido/configuracion.py` al 14/10/2026 (cambios 1a a 1d archivados).
Nunca un valor real: el repositorio es público (`.env` está en `.gitignore`; `infra/.env.example`
sólo trae placeholders; la carpeta de respaldos también está en `.gitignore`).

### Existentes (cambios 1a a 1d, archivados)

| Variable | La usan | Obligatoria/opcional | Default | Propósito |
|---|---|---|---|---|
| `POSTGRES_HOST` | `db` (implícito), API, worker, migraciones (`ConfiguracionBaseDeDatos`) | Obligatoria para `Configuracion`/`ConfiguracionBaseDeDatos` | Compose la fija en `db` para API, worker y migraciones; `.env.example` trae `db` para uso fuera de Compose | Host de PostgreSQL |
| `POSTGRES_PORT` | API, worker, migraciones | Opcional (default `5432` en `Configuracion`; Compose la fija en `"5432"`) | 5432 | Puerto de PostgreSQL |
| `POSTGRES_USER` | `db`, API, worker, migraciones | Obligatoria (`:?falta POSTGRES_USER` en Compose) | sin default | Usuario de conexión, compartido por los cuatro servicios |
| `POSTGRES_PASSWORD` | `db`, API, worker, migraciones | Obligatoria | sin default | Contraseña de PostgreSQL (`SecretStr`; nunca se loguea, L-007) |
| `POSTGRES_DB` | `db`, API, worker, migraciones | Obligatoria | sin default | Nombre de la base |
| `REDIS_HOST` | API, worker | Obligatoria | Compose la fija en `redis` | Host de Redis |
| `REDIS_PORT` | API, worker | Opcional (default `6379`) | 6379 | Puerto de Redis |
| `REDIS_PASSWORD` | `redis`, API, worker | Obligatoria (`:?falta REDIS_PASSWORD`) | sin default | Contraseña de Redis (`SecretStr`; `redis-server` arranca con `--requirepass`) |
| `PROPTECH_PARAMETROS` | API, worker | Obligatoria (el archivo tiene que existir y ser legible) | Compose la fija en `/app/config/parametros.yaml` | Ruta al archivo de parámetros del sistema (D-042) |
| `FORWARDED_ALLOW_IPS` | API (uvicorn, `--proxy-headers`) | Fijada por Compose, no por `.env` | `172.28.0.254` (la IP fija de `caddy` en la red `interna`, D17 del design del 1c) | Única IP de la que la API acepta encabezados `X-Forwarded-*` |
| `PROPTECH_SITIO` | `caddy` | Obligatoria (`:?falta PROPTECH_SITIO`) | sin default | Dominio o URL que sirve Caddy (`http://localhost` en local; el dominio real en producción, con HTTPS automático) |
| `PROPTECH_URL_API_INTERNA` | `web` | Fijada por Compose | `http://api:8000` | URL interna con la que el servidor de Next llama a la API; nunca la ve el navegador (D-036) |
| `DB_POOL_PRE_PING` | API, worker | Opcional | `true` | Verifica la conexión del pool antes de usarla (D18 del design del 1c, M14 de la auditoría de Alberto del 13/10) |
| `DB_POOL_SIZE` | API, worker | Opcional (1 a 50) | 5 | Tamaño del pool del engine de SQLAlchemy |
| `DB_POOL_RECYCLE_S` | API, worker | Opcional (60 a 86400) | 1800 | Segundos antes de reciclar una conexión del pool |
| `DB_POOL_TIMEOUT_S` | API, worker | Opcional (1 a 60) | 5 | Segundos de espera por una conexión libre del pool |
| `DB_CONNECT_TIMEOUT_S` | API, worker | Opcional (1 a 30) | 2 | Segundos de espera al establecer la conexión a PostgreSQL |
| `PROPTECH_DIR_RESPALDOS` | `respaldos` | Obligatoria (`:?falta PROPTECH_DIR_RESPALDOS`) | `./datos-respaldos` en `.env.example` (relativo a `infra/`) | Carpeta del host (bind mount, no volumen con nombre) donde se guardan los `.dump`; sobrevive a `docker compose down -v` |
| `PROPTECH_UID` | `respaldos` | Obligatoria (`:?falta PROPTECH_UID`) | sin default | UID del usuario del host con el que corre el servicio, para que los backups no queden como root ni como un UID que el host no conoce |
| `PROPTECH_GID` | `respaldos` | Obligatoria (`:?falta PROPTECH_GID`) | sin default | GID del usuario del host, gemelo de `PROPTECH_UID` |
| `RESPALDO_INTERVALO_SEGUNDOS` | `respaldos` | Opcional (60 a 604800) | 86400 (diario) | Cada cuánto corre un backup, además del de arranque |
| `RESPALDO_CONSERVAR` | `respaldos` | Opcional (1 a 365) | 14 | Cuántos backups se retienen antes de borrar los más viejos |
| `RESPALDO_LIMITE_SEGUNDOS` | `respaldos` | Opcional (5 a 86400, menor que el intervalo) | 1800 | Corta el volcado (`pg_dump`) si tarda más que este límite (L-001: una base pausada no cuelga el servicio para siempre) |

### Nuevas del cambio 2a `aislamiento-por-administracion` (cuatro roles de PostgreSQL, D-082, E1, E5)

| Variable | La usan | Obligatoria/opcional | Default | Propósito |
|---|---|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `roles.py antes`/`despues` (rol de arranque) | Obligatoria | sin default | El superusuario de la imagen oficial; crea y repara los otros tres roles; único dueño de `auditoria`; ningún servicio permanente la recibe (R8) |
| `POSTGRES_MIGRADOR_USER` / `POSTGRES_MIGRADOR_PASSWORD` | Alembic (migraciones) | Obligatoria | sin default | `proptech_migrador`, dueño de las tablas de dominio; sin `BYPASSRLS` (E1): sembrar datos exige fijar el tenant a propósito |
| `POSTGRES_APP_USER` / `POSTGRES_APP_PASSWORD` | API, worker | Obligatoria | sin default | `proptech_app`, sin superusuario ni `BYPASSRLS`; sujeta a RLS igual que cualquier cliente |
| `POSTGRES_RESPALDO_USER` / `POSTGRES_RESPALDO_PASSWORD` | `respaldos`, `restaurar.sh` | Obligatoria | sin default | `proptech_respaldo`, sin superusuario, con `BYPASSRLS` y `pg_read_all_data`; sólo para `pg_dump` |

Deuda conocida de esta tabla (D-098, "Deuda del cierre del 2a"): V3-14, `POSTGRES_APP_USER` acepta un
nombre de rol que la migración no conoce (dueño 2c); V3-15, al README le faltan estas contraseñas
distintas por rol (dueño 2c, junto con esta misma tabla).

Todas las que llegan como texto desde el entorno (enteros incluidos) se validan con coincidencia
completa y sólo dígitos ASCII, sin ceros a la izquierda (Bash interpreta `060` como octal) y sin
signo (L-002, L-008): un valor con espacios, tabulaciones, saltos de línea o separador de miles se
rechaza en vez de convertirse en silencio a un número distinto. Nunca se imprime el valor de una
variable con problema ni la salida de `pg_dump`/`pg_restore` en el log (L-007).

### Servicio de respaldos (cambio 1d `respaldos-y-restauracion`, HIGH: D-087, D-094, D-095)

Construido y archivado el 14/10/2026. El servicio `respaldos` corre `pg_dump --format=custom` desde
la misma imagen de PostgreSQL que `db` (`postgres:18.6-trixie`), al arrancar y después cada
`RESPALDO_INTERVALO_SEGUNDOS`, sólo en la red `interna` (sin puertos publicados). El volcado sale del
contenedor por un bind mount a `PROPTECH_DIR_RESPALDOS` (no un volumen con nombre, para que
`docker compose down -v` no se lleve los backups junto con la base), con nombre
`proptech-<fecha y hora UTC>.dump`, permisos 600 y dueño el usuario del host (`PROPTECH_UID`/
`PROPTECH_GID`). Retiene los últimos `RESPALDO_CONSERVAR` backups correctos (14 por defecto), sin
borrar nunca el archivo del ciclo en curso aunque el reloj del host atrase. `infra/respaldos/restaurar.sh`
carga un backup en una base aparte (`proptech_restauracion` por defecto), con el destino validado por
la expresión cerrada `^proptech_[a-z0-9_]{1,50}$` y distinto de la base en uso; el humo del CI lo
ejecuta en cada corrida y compara la revisión de Alembic de la base restaurada contra la de la base en
uso. El servicio figura como no saludable si su último backup correcto es más viejo que 1,5
intervalos, si todavía no generó ninguno, si su marca no es un número válido o si esa marca está en
el futuro.
