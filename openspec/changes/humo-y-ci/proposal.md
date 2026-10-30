## Why

El humo y el CI dicen más de lo que distinguen: el humo compara la cantidad de políticas de RLS y no su
contenido, 22 caminos fallan sin nombrar línea ni comando, la lista de servicios del chequeo de
capacidades está escrita a mano, y `humo.sh` fija `-p proptech` e ignora `PROPTECH_COMPOSE_PROYECTO`
(L-047), con el riesgo de pisar un stack real. El ensayo de roles (`ensayo-roles.sh`) no corre en el CI
y su cabeza de migración se desfasó dos veces (L-043). Es deuda de los cierres del 1d, 2c y 4a que
tenía como dueño el 15 o "quien toque el archivo"; D-138 la adelantó a este change (C-23, 2e) porque
el CI es lo que sostiene a los seis changes en paralelo que vienen.

## What Changes

Agrupado por familia (L-021: se arregla la familia, no el ejemplo). El ID de cada ítem es el de su
ficha de origen.

- **El humo dice lo que mide**
  - C2V2-3: comparar el contenido de las políticas de RLS de la base restaurada (`pg_policies`:
    tabla, nombre, comando, roles, `qual`, `with_check`), no su cantidad.
  - C2-5 y C2V2-8: los 22 `exit 1` y los `if !` del humo nombran paso, línea y comando; `compose()`
    informa la línea del llamado.
  - C2V2-7: la lista de servicios del chequeo de capacidades se deriva de `compose config --services`;
    un servicio nuevo sin capacidad declarada da rojo.
  - C2-7: el conteo de `.dump` deja de ser una carrera (espera acotada a que aparezca el volcado).
  - N-a: el verificador de cabeceras rechaza duplicados y valores con texto de más.
  - N9: nota y chequeo para el PID 1 de `db`, que sólo se vio rojo con `init: true`.
  - L-047: `humo.sh` toma el proyecto de `PROPTECH_COMPOSE_PROYECTO`, lo exporta y se niega a correr
    antes de tocar nada si falta la variable, si vale `proptech` (siempre, D15) o si los
    puertos 80 o 443 están ocupados. Corrige un error real: `humo.sh:741` llamaba a `restaurar.sh` sin
    exportar la variable, y `restaurar.sh:46` usa `proptech` por defecto, así que un humo en un
    proyecto propio habría restaurado contra el proyecto `proptech` (la base del stack real, si estaba
    levantado).
- **Caddy**
  - C2V2-6: un test fija el `respond 421` del sitio de respaldo (ocho métodos).
  - C2V2-1 (sólo lo que se puede fijar sin dominio): se declara por escrito, con un test del
    `Caddyfile`, qué devuelve hoy el 443 con un `Host` ajeno y la 308 de http a https; el arreglo con
    el dominio real y HSTS queda en el 15.
  - N2: `reverse_proxy` con timeouts, para que una `api` pausada no deje a Caddy colgado 100 s.
- **Arranque de la API**
  - C2-8: `arranque_fallido` con causa nombrada también ante una base inalcanzable y ante un
    `parametros.yaml` mal formado.
- **Tests del log**
  - C2V2-2 y N-b: el test del log captura todos los niveles de todos los loggers y compara contra los
    campos del registro, no contra un `str()` que puede contener "123" por azar.
- **CI**
  - L-043: `ensayo-roles.sh` corre en el CI, con la cabeza de migración derivada de `alembic heads`
    y no escrita a mano.
  - L-044: caché de Chromium en el job `web`.
  - Dependabot: `.github/dependabot.yml` para `github-actions`, `docker`, `uv` y `npm`/pnpm.
  - Paralelizar el backend: separar unitarios de integración y `pytest-xdist` con una base por worker,
    midiendo antes y después (pedido de Juani, 30/10/2026).
  - DA-12 (D-139): revisar `.gitleaksignore` cuando se rebase el PR #4.

**No entra** (queda en el 15): imágenes en un registro por digest y HSTS con el dominio real.
**No entra** (deuda nueva, anotada en la ficha 2e): correr el humo **en paralelo** con un stack real.
Caddy publica `80:80` y `443:443` fijos y la red `aplicacion` fija su subred y la IP de Caddy
(`infra/compose.yaml:22`, `:191`, `:368-375`), así que hoy el aislamiento por proyecto protege los
volúmenes pero no los puertos; este change lo vuelve un rechazo claro en vez de un fallo a mitad de
camino.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `integracion-continua`: el ensayo de roles en el CI con cabeza derivada, Dependabot, caché de
  Chromium, backend en paralelo, el humo con proyecto parametrizable, lista de servicios derivada,
  carrera del `.dump` y comparación del contenido de las políticas; el paso del humo que nombra línea y
  comando (se retira la excepción de C2-5/C2V2-8).
- `entorno-de-ejecucion`: declaración del 443 y de la 308 sin dominio, `421` del sitio de respaldo,
  timeouts del proxy, y la causa nombrada ante base inalcanzable o `parametros.yaml` mal formado.

## Verificación

Esta tabla es contrato con la tarea de cierre (L-043, L-047): lo que no se puede probar en el clon
Linux de WSL queda declarado como tal, nunca como probado.

| Ítem | Dónde se verifica |
|---|---|
| C2V2-3, C2-5/C2V2-8, C2V2-7, C2-7, N-a, N9 (`humo.sh`) | WSL: `pytest backend/tests/infra`, `shellcheck` y `humo.sh` con Docker, con proyecto aislado |
| L-047: proyecto, restauración y los tres rechazos (variable, `proptech` activo, puertos) | WSL: cada rechazo provocado a propósito (stack `proptech` descartable, puerto 80 ocupado); el job `humo` del CI **no** se ve local |
| C2V2-6, C2V2-1, N2 (Caddyfile) | WSL: `humo.sh` contra el stack vivo; el test estático corre en cualquier lado |
| C2-8 (`arranque_fallido`) | WSL: integración con Docker (una base inalcanzable y un YAML roto reales) |
| C2V2-2, N-b (tests del log) | WSL: pytest, con el defecto puesto para ver el rojo (L-013) |
| `ensayo-roles.sh` con cabeza derivada | WSL: el ensayo corrido entero en proyecto aislado; el job del CI **no** se puede verificar local |
| xdist con una base por worker | WSL: tiempos antes y después de la misma suite; el tiempo en el runner de GitHub **no** |
| Dependabot (`dependabot.yml`) | **No local**: sólo el esquema y el test estático; que abra PRs se ve en GitHub |
| Caché de Chromium | **No local**: `actions/cache` sólo se ve en un run de GitHub (L-037, L-042: se lee el run sobre el SHA) |
| `ensayo-roles` y backend paralelo dentro del CI | **No local**: se ven en el run de un PR, con el límite de tiempo de cada job |
| `.gitleaksignore` (DA-12) | **No local**: depende de cuándo se rebase el PR #4 |

## Impact

- `infra/ci/humo.sh`, `infra/ci/pasos.sh`, `infra/ci/ensayo-roles.sh`, `infra/ci/test-backend.sh`,
  `infra/Caddyfile`, `.github/workflows/ci.yml`, `.github/dependabot.yml` (nuevo), `.gitleaksignore`.
- `backend/src/proptech_api/app.py` (única línea de código de producción: la causa del arranque
  fallido) y `backend/tests/` (infra, unitarios, `conftest.py` para xdist), `backend/pyproject.toml`
  (`pytest-xdist` con `uv.lock`).
- Sin migraciones, sin datos, sin autenticación, sin plata. Gobernanza: MEDIUM, sin firma previa
  (D-094, D-111). Lo construye Gianfranco.
- Knowledge Base Impact: `CHANGES.md` (C-23 `[x]`), `knowledge-base/12_fichas_de_changes.md` (ficha 2e y
  filas de "Deuda del cierre del 2c" que se cierran), una decisión nueva en
  `09_decisiones_y_supuestos.md` y las lecciones que enseñe en `15_lecciones.md`.
