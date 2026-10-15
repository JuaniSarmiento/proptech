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

## Seguridad

- **Autenticación**: login del personal y enlace mágico o alternativa para el vecino; el método
  concreto se decide en el *design* del cambio 2 `acceso-y-aislamiento` (D-039, D-043). El servidor de
  Next guarda el token de sesión; el navegador nunca lo ve (D-036).
- **Autorización**: tres capas: administración (tenant, deducida del login), alcance por edificio
  según el rol, permiso por acción (D-037, P23 pendiente). Fuera de alcance responde 404; sin permiso,
  403 con el permiso faltante. Row-Level Security de PostgreSQL es el segundo candado del aislamiento
  entre administraciones (R10, D-076).
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
