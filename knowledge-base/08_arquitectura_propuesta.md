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
├── web/                      # Next.js (App Router); src/app/edificios/ = pantallas del administrador
│                             # (3b); (consejo) y (vecino), sin pantallas todavía
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

## La web (`pantallas-del-edificio`, 3b)

- **Lectura en el servidor, escritura con server actions** (D1 del design del 3b): cada página de
  `web/src/app/edificios/` es un componente de servidor que pide sus datos con el cliente de abajo y
  se los pasa a un componente de cliente; las altas y ediciones son **server actions** que llaman a la
  misma API y devuelven un resultado tipado que el formulario muestra con `useActionState`. La web
  llama a la API **desde el servidor de Next** (`PROPTECH_URL_API_INTERNA`), nunca desde el navegador,
  igual en desarrollo que en producción (D11 del 3a); el acceso sin login de ese mismo D11 (E2) quedó
  escrito pero sin construir, en el change `acceso-de-desarrollo`, a la espera de la firma HIGH de
  Juani (D-094).
- **Un cliente y un mapa de errores** (D2): `web/src/lib/api/` traduce cada respuesta de la API a una
  unión discriminada (`ok`, `sin_sesion`, `sin_permiso`, `no_existe`, `conflicto`, `invalido`,
  `fallo`); ningún texto que viene de la API llega tal cual a la pantalla (L-007), y los valores de
  plata se validan como texto decimal, nunca como `float`.
- **Fixtures del contrato, generados por la API real** (D4): `backend/tests/integracion/
  test_contrato_web.py` arma un edificio y compara la forma de cada respuesta de lectura que usa la
  web contra `web/src/lib/api/fixtures/*.json`; esos mismos fixtures alimentan los tests de la web y
  la API falsa de Playwright (`web/e2e/api-falsa.ts`, D7, sólo Chromium). Si la API renombra un campo,
  falla primero el test del backend.
- La web **no calcula**: la suma de coeficientes, su estado según R01, los seis pasos de puesta a
  punto y "listo para liquidar" vienen de `GET /api/complejos/{id}/resumen` (D5 del design del 3b,
  requisito nuevo de `edificios-y-unidades`); el historial de configuración trae el nombre del autor
  de cada versión con un `JOIN` a `persona` (mismo requisito nuevo de `configuracion-versionada`).

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
- **Proxy** (cambio 2c, D1 y D2): Caddy agrega a toda respuesta `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` y una `Permissions-Policy` restrictiva, y
  quita `Server`, `Via` y `X-Powered-By`, también en sus propios errores (el 502 con la API caída). Un
  sitio de respaldo en `:80` responde `421` a todo pedido por IP o con un `Host` ajeno, con las mismas
  cabeceras. **Límite**: sólo en HTTP; el 443 con `https://` y la redirección 308 son deuda del 15
  (C2V2-1, D-101). Sin HSTS hasta el dominio real (cambio 15).
- **Contenedores** (cambio 2c, D3 y D4): todo servicio con `no-new-privileges` y `cap_drop: [ALL]`;
  `cap_add` sólo donde un arranque real lo pidió: `db` (`CHOWN`, `DAC_OVERRIDE`, `SETUID`, `SETGID`, para
  que su entrypoint baje a `postgres`), `redis` (`SETUID`, `SETGID`) y `caddy` (`NET_BIND_SERVICE`). El
  PID 1 corre sin root en siete servicios; `caddy` queda root, declarado. El humo lee `/proc/self/status`
  de cada servicio vivo y exige `NoNewPrivs: 1` y su `CapBnd` exacto. **Límite**: la lista de servicios
  está escrita a mano (un noveno servicio no lo ve nadie, C2V2-7, deuda del 15).
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

Tabla única (D8, tarea 2c del cambio `endurecimiento-de-infraestructura`): la lista completa, con
quién la usa, si es obligatoria, su default y su propósito, vive en
[`README.md#variables-de-entorno`](../README.md#variables-de-entorno). Antes esta sección tenía su
propia tabla (duplicada con la del README, y con una fila que ya mentía: `POSTGRES_USER` decía
"compartido por los cuatro servicios", falso desde el 2a); dos tablas son una que deriva, así que acá
queda sólo el enlace.

`POSTGRES_APP_USER` tiene que ser el nombre del rol que conoce la migración (`proptech_app`): con
otro nombre, `roles antes` corta el arranque nombrando la variable (V3-14, cerrada en el 2c, tarea 6.2).

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
