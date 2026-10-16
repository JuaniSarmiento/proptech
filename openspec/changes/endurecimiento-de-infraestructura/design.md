## Context

Ver `proposal.md` (Why). Este cambio arranca con el 2a archivado: la red `interna` ya está partida en
`datos` y `aplicacion` (la web no alcanza la base), `migraciones` corre el paso de roles y `respaldos`
usa `proptech_respaldo`. Estado de lo que toca este cambio, leído contra `d0502fa` (revisión de DevOps
del 16/10/2026). `Caddyfile`, `ci.yml` y `next.config.ts` no cambiaron desde `b77babf`; `humo.sh`
(+157 líneas) y `compose.yaml` (+80) sí cambiaron con el 2a:

- **`infra/Caddyfile`**: quita `Server` y pisa `X-Request-ID`; no fija ninguna cabecera de seguridad ni
  quita `Via` ni `X-Powered-By`. Un 502 que genera el propio Caddy vuelve con `Server: Caddy` aunque
  esté `header -Server` (reproducido con un Caddyfile mínimo de la misma versión, 16/10 09:50). Caddy no
  tiene volúmenes: `/data/caddy/instance.uuid` (que existe también en HTTP) se pierde al recrearlo.
- **`web/next.config.ts`**: Next manda `X-Powered-By: Next.js` por defecto.
- **`infra/compose.yaml`**: 8 servicios (`db`, `migraciones`, `redis`, `respaldos`, `web`, `worker`,
  `api`, `caddy`), cuatro redes (`datos`, `aplicacion` y las de salida, entre ellas `salida_worker`);
  ningún servicio tiene `security_opt` ni `cap_drop`. `db` y `redis` bajan de usuario con `gosu`;
  `respaldos` corre con `PROPTECH_UID`; `api`, `worker` y `web` con el `USER` de su imagen; `caddy` corre
  como root (la imagen no fija `USER`).
- **`infra/ci/humo.sh`**: 21 pasos y dos `up` (el segundo, del 2a, sobre los volúmenes existentes,
  `humo.sh:106-107`). El chequeo de PID 1 lee `/proc/1/status` en `worker`, `redis` y `respaldos`
  (`humo.sh:209-219`); `api` y `web` se chequean con `exec id -u` (`humo.sh:203-207`), y el rojo se vio
  sólo en `redis` (1d). Hay 35 asserts `[ ]` y 11 `grep -q` sueltos que fallan sin decir en qué paso.
  "Aparece uno solo" del paso 11 (`humo.sh:375`) ya es falso: `respaldos` hace un backup por arranque
  (`respaldar.sh:270`), así que con dos `up` hay dos `.dump` antes del paso 11. `limpiar` despausa `db`
  y `redis` antes del `down -v` (`humo.sh:42-44`), pero baja el stack sin volcar los logs: si algo
  falla, en el CI sólo queda la última línea del script. El archivo está en git como `100644`.
- **`.github/workflows/ci.yml`**: `on: push: branches: [main]` y `workflow_dispatch`, sin
  `pull_request` y sin `timeout-minutes`; gitleaks `zricethezav/gitleaks:v8.30.1` y shellcheck
  `koalaman/shellcheck:v0.11.0` por tag. Duración medida del trabajo `backend`: 4 min 26 s, 5 min 18 s,
  5 min 32 s y 9 min 08 s en las últimas cuatro corridas (creciendo); `humo`, de 1 min 00 s a 2 min
  00 s; el resto, menos de 20 s (`gh run view`, 16/10 09:48).

## Deuda que recibe este cambio

| Ítem (origen) | Por qué es del 2c y no del 2a |
|---|---|
| Cabeceras de seguridad en Caddy (13/10); `Via`, `X-Powered-By`, HEAD (D-051) | Endurecen el proxy; no cambian quién ve qué dato |
| Volúmenes de Caddy (13/10) | Operación del proxy |
| CI con `pull_request`, límites de tiempo, gitleaks por digest (13/10) | Pipeline |
| Endurecimiento de contenedores (13/10) y PID 1 no root servicio por servicio (1d) | Reducen el daño de un proceso comprometido; el candado de datos vive en la base |
| F7 resto y la doble congelada (1d) | Calidad del humo y de la salud |
| Tabla de variables del README (13/10) | Documentación |
| El orden de la 8.1 (1d) | La corrida de cierre de este cambio dice el orden y por qué (D7) |
| V2-5: la API no nombra en el log por qué no arrancó (2a, D-098) | "La falla se ve en el log": D10 |
| V3-8: flake de `test_worker_tenant.py` (2a) | Va antes de activar el CI en pull requests (D5) |
| V3-9: el test de R7 se cuelga en vez de dar rojo (2a) | Va junto con el límite de tiempo del CI (D5) |
| V3-14: `POSTGRES_APP_USER` con un nombre que la migración no conoce (2a) | Va con la tabla de variables (D11) |
| V3-15: README desactualizado y el humo sin `relrowsecurity` (2a) | Va con la tabla y el humo (D6, D8) |
| D-5: `humo.sh` en `100644` (2a) | Va con el humo (D6) |

## Goals / Non-Goals

**Goals:** cerrar la deuda de infraestructura con dueño "2" que no hace al candado, y la del 2a con
dueño 2c, con tests que fallen si vuelve; dejar el rollback ejercitado, no descrito.

**Non-Goals:** credenciales, roles y redes nuevos (2a); CSP (2b); HSTS, `read_only`, imágenes base por
digest, monitoreo fuera del CI y los secretos visibles en `docker inspect` (15).

## Decisions

### D1 · Cabeceras en Caddy

Un bloque `header` en el sitio con `X-Content-Type-Options nosniff`, `Referrer-Policy no-referrer`,
`X-Frame-Options DENY`, `Permissions-Policy "camera=(), microphone=(), geolocation=()"` y `-Server`,
`-Via`, `-X-Powered-By`; cada `reverse_proxy` con `header_down -Via` y `header_down -X-Powered-By`, para
que lo que viene de atrás no se cuele. `web/next.config.ts` con `poweredByHeader: false` (defensa en
profundidad: si alguien expone la web sin Caddy, tampoco lo manda).

**Las respuestas que genera Caddy** (502 y 504 cuando `api` o `web` no responden) no pasan por el
bloque `header` de una respuesta normal: hoy vuelven con `Server: Caddy`. Se cubren con `handle_errors`
(o el mecanismo equivalente que el constructor elija **después de ver el rojo** con `api` detenida), y
el escenario "Error del proxy" es el que lo exige. La elección y el porqué van en el informe.

**Descartado**: HSTS ahora; en el CI el sitio es HTTP y una HSTS mal puesta en un dominio real es
difícil de deshacer, va con el 15.

### D2 · Volúmenes de Caddy

`datos_caddy:/data` y `config_caddy:/config`. La verificación es por efecto: `/data/caddy/instance.uuid`
es el mismo antes y después de `docker compose -p proptech up -d --force-recreate caddy`. En el CI el
sitio es HTTP y no hay certificados que perder, así que "conserva los certificados" no podría fallar;
`instance.uuid` sí cambia si falta el volumen.

### D3 · Privilegios y capacidades

Todos los servicios con `security_opt: [no-new-privileges:true]` y `cap_drop: [ALL]`. Vuelven a agregar
sólo: `db` y `redis`, las que su entrypoint necesita para bajar de usuario (candidatas: `CHOWN`,
`SETUID`, `SETGID`, `DAC_OVERRIDE`, `FOWNER`); `caddy`, `NET_BIND_SERVICE`.

**La lista final la fija el constructor viendo fallar el arranque sin cada una, en dos situaciones**:
sobre volúmenes nuevos **y** con un segundo `up` sobre volúmenes existentes. El entrypoint de `db` y
`redis` hace `chown`/`chmod` sobre un directorio que en la segunda corrida ya es de otro usuario: root
sin `DAC_OVERRIDE`, `DAC_READ_SEARCH` o `FOWNER` puede arrancar la primera vez y fallar la segunda. Una
capacidad que no se vio hacer falta en ninguna de las dos no entra. La lista queda en un comentario de
`compose.yaml` y en el informe, con el error que dio cada una.

**`caddy` queda uid 0, declarado**, sin capacidades salvo `NET_BIND_SERVICE`. **Descartado**: `user:` no
root para Caddy; con `no-new-privileges` las capacidades de archivo de su binario no se aplican, y un
proceso no root no podría abrir el puerto 80. Root sin capacidades ni privilegios nuevos es el menor de
los dos males. Si el constructor ve otra cosa al probarlo, se informa antes de cambiarlo.

La verificación es por efecto, no por forma (L-018): además del test sobre el YAML, en el stack vivo
`/proc/1/status` de cada servicio trae `NoNewPrivs: 1` y su `CapBnd` es exactamente la lista
justificada de ese servicio (vacía salvo `db`, `redis` y `caddy`). Un `cap_drop` que el runtime ignore
pasa el test del YAML y no pasa éste.

**Descartado**: `read_only: true` en este cambio; cada imagen escribe en lugares distintos (`/tmp`,
cachés de Next) y exige un `tmpfs` por servicio, que se evalúa con el despliegue (15).

### D4 · PID 1 no root servicio por servicio

Se chequea el usuario del PID 1 por `/proc/1/status` en **siete** servicios: `api`, `web`, `worker`,
`migraciones`, `respaldos`, `redis` y `db` (en `db` y `redis`, el PID 1 después de `gosu`). `api` y `web`
pasan de `exec id -u` a `/proc/1/status`, como el resto: `id -u` dice quién es el `exec`, no quién es el
proceso. `caddy` queda fuera de la lista y declarado root (D3).

`migraciones` termina, así que se lee con `docker compose run --no-deps` sobre la misma configuración:
eso lee el usuario configurado, no el del proceso que corrió. Es aceptable porque la imagen del backend
no cambia de usuario en el entrypoint (`backend/Dockerfile`: `USER proptech`, sin `ENTRYPOINT`); si eso
cambia, este chequeo deja de alcanzar y hay que revisarlo.

El rojo se ve en **cada uno de los siete** con una copia de Compose que lo hace correr como root
(L-013, L-016): ver el rojo en uno solo no dice nada de los demás, que es exactamente la deuda del 1d.
En `db` y `redis`, `user: "0:0"` no alcanza: el entrypoint arranca como root igual y baja con `gosu`,
así que el chequeo seguiría en verde sin probar nada. Ahí la copia saltea el entrypoint (como se hizo
con `redis` en el 1d: `--entrypoint sh -c "redis-server ..."`, sin el `gosu`).

### D5 · CI

- **Disparadores**: se mantienen `push: branches: [main]` y `workflow_dispatch`, y se suma
  `pull_request`. `on: [push, pull_request]` borraría `workflow_dispatch` y el filtro de rama, rompería
  `test_ci_workflow.py:58-65` y contradiría la spec principal ("en cada push a `main` y a pedido
  manual").
- **Límites de tiempo**, con la medición del Context: `backend` 20 min (peor corrida medida 9 min 08 s
  y creciendo; 10 dejaría 52 s de margen), `humo` 15 min (1 a 2 min medidos), el resto 5 min (menos de
  20 s medidos). Si la 1.1 mide algo distinto, se ajusta con esa medición y se anota.
- **Digests**: gitleaks **y** shellcheck como `imagen:tag@sha256:<digest>`. El digest se toma del
  registro o del log de pull del CI, no de la copia local de la imagen (la local de gitleaks también
  tiene el tag `latest`), y se anota con el comando que lo obtuvo.
- **Orden con la deuda del 2a**: V3-8 (el flake) se resuelve **antes** de activar `pull_request`, y V3-9
  (el cuelgue) **junto con** el límite de tiempo: un cuelgue cortado a los 20 min sin nombrar el test
  no es un rojo útil.

### D6 · Humo

- **Un único `trap ... ERR` con `set -E`** que imprime el paso en curso (número y descripción), `$LINENO`
  y `$BASH_COMMAND`. Cubre los 35 `[ ]` y los 11 `grep -q` sueltos sin reescribir cada uno a `if !`.
  Los `if !` que ya existen se quedan: `trap ERR` no salta dentro de una condición ni a la izquierda de
  `||` (L-014).
- **Los helpers** (`paso N "descripción"`, el `trap`, el conteo) viven en `infra/ci/pasos.sh`, aparte de
  `humo.sh`, para probar su efecto sin Docker: un script mínimo que los usa y fuerza un paso a fallar
  tiene que imprimir número, descripción, línea y comando.
- **Un respaldo por arranque**: en vez de "aparece uno solo", se cuentan los `.dump` antes y después de
  cada `up` y del `--una-vez`, y cada uno deja exactamente un `.dump` nuevo. El título del paso 11 se
  renombra para decir eso.
- **Doble congelada**: `docker compose -p proptech pause db redis` y los dos pedidos. `limpiar` ya
  despausa antes del `down -v` (`humo.sh:42-44`); lo que falta es un test que exija ese orden, para que
  no se pierda. La cota de `/api/salud` es **2,5 s**: el plazo total de la salud es 1,5 s
  (`PLAZO_TOTAL_SALUD_S`, `salud.py:34`), y si alguien lo cambiara a la suma de los dos plazos (3 s) el
  paso tiene que dar rojo; 2,5 s lo detecta y deja 1 s de margen en un runner compartido (2 s dejaba
  0,5 s). "Exactamente dos `salud_degradada`" puede flakear por F6 (1d, dueño 15: un 503 sin
  `salud_degradada`, 1 de 18): si pasa, se nombra como F6 y no como regresión.
- **Cabeceras de punta a punta** con `curl -sI` y `curl -s -D -` por el proxy, más el 502 con `api`
  detenida. No se verifica "HEAD sin cuerpo": curl no lee cuerpo con `-I` y Caddy descarta el cuerpo de
  HEAD solo, así que ese chequeo no puede fallar (L-019).
- **La falla queda en el log**: si `estado != 0`, `limpiar` vuelca `docker compose -p proptech ps -a` y
  `docker compose -p proptech logs --no-color --tail=200` **antes** del `down -v`. Con `cap_drop: [ALL]`
  la falla esperable es un `chown: Operation not permitted` en el log de `db` o `redis`, que hoy nadie
  vería.
- **`relrowsecurity`**: en la base restaurada, el humo exige `relrowsecurity = t` además de
  `relforcerowsecurity` (`humo.sh:466-468`; el gemelo de V2-2, L-018).
- **Ejecutable**: `humo.sh` pasa a `100755`, y un test exige ese modo en todo `infra/**/*.sh` según
  `git ls-files -s`.

### D7 · La corrida de cierre, en orden

`test-backend.sh`, `test-web.sh` y `humo.sh` en ese orden y de a uno: comparten contenedores del
proyecto `proptech` y en paralelo se pisan. Después, un **clon limpio**: `git clone` del commit final a
un directorio temporal y los comandos del README tal cual (`cp`, `mkdir`, `up --build`), `/api/salud`
200 por el proxy y `down -v`. El humo del CI se parece pero no es eso: usa sus propios comandos y su
propia carpeta de respaldos (`humo.sh:19-25`).

### D8 · Una sola tabla de variables

La tabla vive en el `README.md` de la raíz (la deuda del 13/10 la pide ahí) y
`knowledge-base/08_arquitectura_propuesta.md` la reemplaza por un enlace: dos tablas son una que
deriva, y la de `08` ya miente (`POSTGRES_USER`: "compartido por los cuatro servicios"; hoy sólo lo
reciben `db` y `migraciones`). Cada fila: qué servicio la usa, si es obligatoria, su default, qué es y
sus restricciones. Un test en los dos sentidos contra la unión de `infra/.env.example` y los `${VAR}`
de `compose.yaml` (que trae variables que no están en `.env.example`, como `FORWARDED_ALLOW_IPS` y
`DB_POOL_*`): falla si una variable falta en la tabla **o** si la tabla nombra una que ya no existe.
Con la tabla se corrige lo de V3-15 en el README: el worker sí tiene salida (`salida_worker`), el 1d
no está "Propuesto" y las cuatro contraseñas tienen que ser distintas.

### D9 · Rollback ejercitado

El rollback se prueba, no se describe. Sobre un stack con datos (las dos administraciones del humo o
la semilla) levantado desde `d0502fa` con `git worktree`, sin tocar el árbol de trabajo:

```bash
git worktree add /tmp/proptech-base d0502fa
# levantar desde /tmp/proptech-base/infra con -p proptech y cargar los datos; anotar conteos
# subir: levantar desde el árbol del 2c, mismo -p proptech, mismos volúmenes (sin down -v)
docker compose -p proptech up -d --build --wait
# /api/salud 200 por el proxy y conteos iguales
# volver: levantar de nuevo desde /tmp/proptech-base/infra, mismos volúmenes
docker compose -p proptech up -d --build --wait
# /api/salud 200 por el proxy y conteos iguales
git worktree remove /tmp/proptech-base
```

Cubre lo que el humo no cubre: un volumen creado **sin** `cap_drop` abierto **con** `cap_drop`, que es
el camino real de la máquina de Juani y del 15. Los comandos exactos que se usaron y su salida van al
Migration Plan al terminar la tarea.

### D10 · La causa de un arranque rechazado queda en el log (V2-5)

Cuando `Configuracion()` (`app.py:35`) o `verificar_rol_de_aplicacion_seguro` (`base_de_datos.py:198`)
cortan el arranque, el log de `api` (y su gemelo `worker`, L-009) tiene una línea JSON con un evento
propio (por ejemplo `arranque_fallido`) y la causa (`es superusuario`, la variable que falta), sin
ningún valor secreto (L-007). El contenedor sigue sin arrancar: se agrega la causa, no se cambia la
decisión. **Abierto** (ver `proposal.md`, Preguntas para Juani): `verificar_rol_de_aplicacion_seguro`
corre dentro de `lifespan`, y la deuda V3-5 (dueño 2b) pide un test del cableado de R7 y R8 "antes de
tocar `lifespan` u `on_startup`".

### D11 · El nombre del rol de la app es el que conocen las migraciones (V3-14)

`ayudas_rls.py:19` fija `_ROL_DE_LA_APP = "proptech_app"` mientras `POSTGRES_APP_USER` acepta cualquier
nombre válido. `roles antes` rechaza un `POSTGRES_APP_USER` distinto del que conocen las migraciones,
nombrando la variable y sin mostrar valores; la tabla de variables dice la restricción. Toca
`roles.py`, código de arranque del candado: aplica la regla de freno de `proposal.md`.

## Risks / Trade-offs

- [Una actualización de imagen necesita otra capacidad] → el humo falla al levantar y, con D6, el log
  dice cuál; se suma con su justificación.
- [Una capacidad que sólo falta al reiniciar sobre un volumen existente] → D3 prueba las dos
  situaciones, y D9 abre volúmenes viejos con la configuración nueva.
- [Un 502 o 504 de Caddy sin cabeceras] → D1 y el escenario "Error del proxy".
- [Las cabeceras de Caddy rompen algo de la web] → `X-Frame-Options DENY` sólo impide embeber; la web
  no se embebe en ningún lado hoy.
- [El digest de gitleaks o de shellcheck queda viejo] → Dependabot, en el cambio 15.
- [El "exactamente dos `salud_degradada`" flakea] → puede ser F6 (dueño 15); se nombra así.
- [Tocar el arranque del candado (V2-5, V3-14)] → regla de freno de `proposal.md`.

## Migration Plan

`docker compose up --build` sobre los volúmenes existentes. Los volúmenes nuevos de Caddy nacen vacíos
(hoy no hay certificados que conservar, el sitio de prueba es `http://localhost`). Sin cambios de
Alembic en este cambio (2c es infra pura): la versión de la base no se mueve en ningún sentido del
rollback.

**Ejercitado el 16/10/2026** (tarea 8.1), sobre un stack con datos reales, con `git worktree` de
`d0502fa` (sin tocar el árbol de trabajo):

```bash
git worktree add /tmp/proptech-base d0502fa
```

1. **Arriba, desde `d0502fa`** (`/tmp/proptech-base/infra`, con `infra/.env` copiado de `.env.example`):
   ```bash
   docker compose -p proptech up -d --build --wait
   ```
   Siete servicios `Healthy`. Se sembraron dos administraciones con dos complejos cada una (mismo
   patrón que el paso 0 del humo, con otro UUID para no pisarlas) directo por `psql` como el rol de
   arranque:
   ```
   $ curl -s http://localhost/api/salud
   {"estado":"ok","base":"ok","cola":"ok"}
   $ psql ... -tAc "select count(*) from administracion"   -> 2
   $ psql ... -tAc "select count(*) from complejo"          -> 4
   $ psql ... -tAc "select version_num from alembic_version" -> 0004
   ```

2. **Subir a la versión del 2c, mismos volúmenes** (desde el árbol de trabajo real, `infra/.env`
   copiado del mismo que usó el paso 1 — mismas credenciales, mismo volumen de Postgres):
   ```bash
   docker compose -p proptech up -d --build --wait
   ```
   Siete servicios `Healthy` de nuevo (ahora con `cap_drop`, `no-new-privileges`, las cabeceras de
   Caddy y los dos volúmenes nuevos de Caddy, creados vacíos sobre la marcha):
   ```
   $ curl -s http://localhost/api/salud
   {"estado":"ok","base":"ok","cola":"ok"}
   $ psql ... -tAc "select count(*) from administracion"   -> 2   (igual)
   $ psql ... -tAc "select count(*) from complejo"          -> 4   (igual)
   $ psql ... -tAc "select version_num from alembic_version" -> 0004 (igual)
   ```

3. **Volver a `d0502fa`, mismos volúmenes** (desde `/tmp/proptech-base/infra` otra vez):
   ```bash
   docker compose -p proptech up -d --build --wait
   ```
   Siete servicios `Healthy`:
   ```
   $ curl -s http://localhost/api/salud
   {"estado":"ok","base":"ok","cola":"ok"}
   $ psql ... -tAc "select count(*) from administracion"   -> 2   (igual)
   $ psql ... -tAc "select count(*) from complejo"          -> 4   (igual)
   $ psql ... -tAc "select version_num from alembic_version" -> 0004 (igual)
   ```

4. **Abajo y limpieza:**
   ```bash
   docker compose -p proptech down -v --remove-orphans
   git worktree remove /tmp/proptech-base
   ```

**Resultado: el rollback ida y vuelta no perdió datos ni rompió `/api/salud` por el proxy, en ningún
sentido.** El volumen de Postgres, creado por `d0502fa` **sin** `cap_drop`, se abrió sin problema con
el `db` del 2c (**con** `cap_drop` y `DAC_OVERRIDE` sólo para el segundo arranque, tarea 3.2) — es
exactamente el camino real de la máquina de Juani y del despliegue (cambio 15): un volumen que ya
existe desde antes de este cambio, no uno creado de cero con la imagen ya endurecida.
