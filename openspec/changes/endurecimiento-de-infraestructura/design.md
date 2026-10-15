## Context

Ver `proposal.md` (Why). Este cambio arranca con el 2a archivado: la red `interna` ya está partida en
`datos` y `aplicacion` (la web no alcanza la base), `migraciones` corre el paso de roles y `respaldos`
usa `proptech_respaldo`. Estado de lo que toca este cambio (commit `b77babf`, sin cambios del 2a en
estas piezas):

- **`infra/Caddyfile`**: quita `Server` y pisa `X-Request-ID`; no fija ninguna cabecera de seguridad ni
  quita `Via` ni `X-Powered-By`. Caddy no tiene volúmenes: sus certificados se pierden al recrearlo.
- **`web/next.config.ts`**: Next manda `X-Powered-By: Next.js` por defecto.
- **`infra/compose.yaml`**: ningún servicio tiene `security_opt` ni `cap_drop`. `redis` baja a uid 999
  con `gosu`; `respaldos` corre con `PROPTECH_UID`; `api`, `worker` y `web` con el `USER` de su imagen.
- **`infra/ci/humo.sh`**: el chequeo de PID 1 lee `/proc/1/status` por servicio, pero el rojo se vio
  sólo en `redis` (1d); los pasos 11 y 13 fallan sin decir cuál; "aparece uno solo" no se verifica.
- **`.github/workflows/ci.yml`**: `on: push`, sin `timeout-minutes`, gitleaks
  `zricethezav/gitleaks:v8.30.1` por tag.

## Deuda que recibe este cambio

| Ítem (origen) | Por qué es del 2c y no del 2a |
|---|---|
| Cabeceras de seguridad en Caddy (13/10); `Via`, `X-Powered-By`, HEAD (D-051) | Endurecen el proxy; no cambian quién ve qué dato |
| Volúmenes de Caddy (13/10) | Operación del proxy |
| CI con `pull_request`, límites de tiempo, gitleaks por digest (13/10) | Pipeline |
| Endurecimiento de contenedores (13/10) y PID 1 no root servicio por servicio (1d) | Reducen el daño de un proceso comprometido; el candado de datos vive en la base |
| F7 resto y la doble congelada (1d) | Calidad del humo y de la salud |
| Tabla de variables del README (13/10) | Documentación |
| El orden de la 8.1 (1d) | La 6.1 de este cambio dice el orden y por qué (D7) |

## Goals / Non-Goals

**Goals:** cerrar la deuda de infraestructura con dueño "2" que no hace al candado, con tests que
fallen si vuelve.

**Non-Goals:** credenciales, roles, redes (2a); CSP (2b); HSTS y secretos de Compose (15).

## Decisions

### D1 · Cabeceras en Caddy

Un bloque `header` en el sitio con `X-Content-Type-Options nosniff`, `Referrer-Policy no-referrer`,
`X-Frame-Options DENY`, `Permissions-Policy "camera=(), microphone=(), geolocation=()"` y `-Server`,
`-Via`, `-X-Powered-By`; cada `reverse_proxy` con `header_down -Via` y `header_down -X-Powered-By`, para
que lo que viene de atrás no se cuele. `web/next.config.ts` con `poweredByHeader: false` (defensa en
profundidad: si alguien expone la web sin Caddy, tampoco lo manda). **Descartado**: HSTS ahora; en el CI
el sitio es HTTP y una HSTS mal puesta en un dominio real es difícil de deshacer, va con el 15.

### D2 · Volúmenes de Caddy

`datos_caddy:/data` y `config_caddy:/config`.

### D3 · Privilegios y capacidades

Todos los servicios con `security_opt: [no-new-privileges:true]` y `cap_drop: [ALL]`. Vuelven a agregar
sólo: `db` y `redis`, las que su entrypoint necesita para bajar de usuario (candidatas: `CHOWN`,
`SETUID`, `SETGID`, `DAC_OVERRIDE`, `FOWNER`); `caddy`, `NET_BIND_SERVICE`. **La lista final la fija el
constructor viendo fallar el arranque sin cada una**, y la deja en un comentario de `compose.yaml` y en
su informe; una capacidad que no se vio hacer falta no entra. **Descartado**: `read_only: true` en este
cambio; cada imagen escribe en lugares distintos (`/tmp`, cachés de Next) y exige un `tmpfs` por
servicio, que se evalúa con el despliegue.

### D4 · PID 1 no root servicio por servicio

El chequeo existente del humo (`/proc/1/status`) se aplica a `api`, `worker`, `web`, `migraciones` (que
termina: se lee con `docker compose run` sobre la misma configuración) y `respaldos`. El rojo se ve en
**cada uno** con una copia de Compose que lo pone como `user: "0:0"` (L-013, L-016): ver el rojo en uno
solo no dice nada de los demás, que es exactamente la deuda del 1d.

### D5 · CI

`on: [push, pull_request]`, `timeout-minutes` en cada trabajo (10 los rápidos, 30 el humo) y gitleaks
como `zricethezav/gitleaks:v8.30.1@sha256:<digest>`, con el digest tomado de la imagen que hoy corre el
CI y anotado con el comando que lo obtuvo.

### D6 · Humo

- Una función `paso N "descripción"` que deja el paso en curso y un `trap ERR`/chequeo explícito que
  imprime número y descripción al fallar; cada paso con su `if ! ...; then` (L-014).
- `exactamente_uno` para cada "aparece uno solo" (cuenta líneas o archivos y exige 1).
- Doble congelada: `docker compose -p proptech pause db redis`, los dos pedidos y un `trap` que despausa
  siempre, también si el paso falla.
- Cabeceras de punta a punta con `curl -sI` y `curl -s -D -` por el proxy.

### D7 · La corrida de cierre, en orden

`test-backend.sh`, `test-web.sh` y `humo.sh` en ese orden y de a uno: comparten contenedores del
proyecto `proptech` y en paralelo se pisan.

### D8 · README

Una tabla con cada variable de `infra/.env.example`: qué servicio la usa, si es obligatoria, su default
y qué es. Un test lee las dos y falla si una variable del `.env.example` no está en la tabla.

## Risks / Trade-offs

- [Una actualización de imagen necesita otra capacidad] → el humo falla al levantar; se suma con su
  justificación.
- [Las cabeceras de Caddy rompen algo de la web] → `X-Frame-Options DENY` sólo impide embeber; la web
  no se embebe en ningún lado hoy.
- [El digest de gitleaks queda viejo] → Dependabot, en el cambio 15.

## Migration Plan

`docker compose up --build`. Los volúmenes nuevos de Caddy nacen vacíos (hoy no hay certificados que
conservar). Rollback: volver los archivos; no hay datos ni esquema en juego.
