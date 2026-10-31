## Context

Estado verificado contra `main` `60b3dd5` (30/10/2026). Motivación y alcance: ver `proposal.md`.

- `infra/ci/humo.sh` (867 líneas) tiene 25 `exit 1` o `if !`; `pasos.sh` sólo cubre con `trap ERR` lo
  que falla fuera de una condición (L-014). `compose()` fija `-p proptech` (`humo.sh:40`).
- La comparación de RLS restaurada mira `count(*)` de `pg_policies` (`humo.sh:~775-815`).
- `verificar_privilegios` se llama ocho veces a mano (`humo.sh:341-348`).
- `ensayo-roles.sh` ya parametriza el proyecto (`PROPTECH_COMPOSE_PROYECTO`) pero tiene `0028`
  escrito en `verificar_revision` (`:233,:245`); `test_ensayo_login.py` compara ese texto contra
  `ScriptDirectory.get_current_head()`, o sea que el test hoy obliga a editar el script con cada
  migración. El CI no lo corre.
- Los tests de integración usan `PostgresContainer` y un Redis, ambos con `scope="session"`
  (`backend/tests/conftest.py`). Los roles se crean a nivel clúster (`roles_reales`), así que dos
  workers no pueden compartir un contenedor sin pisarse. No hay `pytest-xdist`.
- El job `backend` del CI tarda ~17,5 min en serie (4279 tests, 30 min de límite); `web` instala Chromium
  en cada corrida; no hay `dependabot.yml`.
- `app.py:60-73`: `Configuracion()` está atrapado, pero `leer_parametros(...)` no, y el
  `except` del lifespan sólo cubre `RolDeAplicacionInseguro` y `TablasDeSoloAgregarDesprotegidas`: una
  base inalcanzable sale como `OperationalError` sin evento propio.

## Goals / Non-Goals

**Goals:**
- Cada ítem de la proposal con un test o chequeo que da rojo con el defecto puesto (L-013: mutar con
  copia previa y diff real), o una declaración escrita cuando no se puede fijar (C2V2-1).
- Que correr el humo o el ensayo en una máquina con un stack real no pueda destruirlo.

**Non-Goals:**
- Reescribir `humo.sh` entero ni partirlo en archivos. Se tocan los puntos de la deuda.
- Cambiar qué verifica el humo más allá de la deuda listada.
- Imágenes por digest y HSTS (15). Nada de producción salvo la causa del `arranque_fallido`.

## Decisions

**D1. Proyecto aislado: la variable manda y el humo se niega antes de tocar nada.** `compose()` usa
`-p "$PROYECTO_COMPOSE"` con `PROPTECH_COMPOSE_PROYECTO`, igual que `ensayo-roles.sh`, y el script la
`export`a. Una función `verificar_que_se_puede_correr` corre antes de cualquier `up`/`down` y rechaza
con mensaje propio: (a) variable ausente; (b) valor `proptech` con `docker compose -p proptech ps -q`
no vacío; (c) puerto 80 o 443 ocupado (comprobación con `ss -ltn` o, si no está, con `/dev/tcp`). El
job `humo` del CI exporta un nombre propio. *Hallazgo al aplicar (30/10/2026):* `infra/compose.yaml`
publica Caddy con `80:80` y `443:443` fijos (`:368-370`) y la red `aplicacion` tiene una IP fija
(`172.28.0.254`, D17), así que el humo **no puede correr en paralelo** con un stack real aunque tenga
otro nombre de proyecto: el aislamiento protege los volúmenes y el `down -v` del stack real, no los
puertos. Hacerlos configurables queda fuera de este change (ver Open Questions). *Error real que
esto corrige:* `humo.sh:741` llamaba a `restaurar.sh` sin exportar la variable, y `restaurar.sh:46`
usa `proptech` por defecto, así que un humo en un proyecto propio habría restaurado contra el proyecto
`proptech` (la base del stack real, si estaba levantado) en vez de contra la propia. *Alternativa
descartada:* generar un nombre aleatorio por defecto; oculta con qué proyecto se corre y el ensayo ya
fijó la convención de que lo elige quien corre. *Orden:* es la primera tarea de código, porque todo lo
demás se verifica corriendo el humo.

**D2. Pasos con línea y comando sin reescribir 22 `exit 1`.** Los `exit 1` explícitos pasan a
`fallar_paso "mensaje"`, que llama a `reportar_fallo_paso` con `${BASH_LINENO[0]}` y el comando que se
pasa como segundo argumento; los `if !` mantienen su `ERROR:` y suman la llamada al formateador.
`compose()` informa `BASH_LINENO[0]` (el llamador) con `trap ... ERR` propio dentro de la función
(`set -E` ya lo propaga). Un test estático recorre `humo.sh` y falla ante un `exit 1` que no sea el de
`fallar_paso` o el de `limpiar`. *Alternativa descartada:* `trap DEBUG`; ruidoso y rompe `shellcheck`.

**D3. Servicios derivados, capacidades declaradas.** La lista sale de `compose config --services`; las
capacidades esperadas quedan en un arreglo asociativo en el humo (`CAPBND_ESPERADO[servicio]`), y un
servicio sin entrada da rojo. `migraciones` conserva su lectura especial. El test estático cruza el
arreglo con `compose.yaml`. N9: hoy ningún servicio de `compose.yaml` declara `init: true`; el chequeo de PID 1 de `db` sólo se
vio rojo al AGREGARLO (`docker-init` corre como root). Queda un test estático que prohíbe `init: true`
y una nota en el humo; la mutación (agregarlo a una copia) se ve en WSL.

**D3b. Funciones del humo en `infra/ci/humo-lib.sh`.** El verificador de cabeceras, la espera del
volcado y el chequeo de servicios declarados se mueven a un archivo que `humo.sh` fuentea y que los
tests fuentean sin Docker (con un `contar_dumps` y un arreglo `CAPBND_ESPERADO` propios). Sin ese
corte, `humo.sh` es un script lineal que no se puede probar por partes.

**D4. Carrera del `.dump`.** `contar_dumps` se reemplaza por `esperar_dumps N` con reintentos cada 0,5 s
hasta 15 s, fallando con el conteo real. Se corrige el comentario falso de `humo.sh:85-89`.

**D5. Comparar políticas por contenido.** Una consulta que devuelve, por tabla, las filas
`schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check` de `pg_policies`
ordenadas, en la base en uso y en la restaurada, y se comparan con `diff`. Las expresiones se comparan
tal como las devuelve Postgres de las dos bases (mismo motor, mismo texto), sin parsear SQL. Los
`FORCE` y `ENABLE` siguen igual. El mensaje nombra la tabla y la política que difiere.

**D6. Verificador de cabeceras estricto.** Por cada cabecera de seguridad exige exactamente una línea
(`grep -ic` igual a 1) y valor igual al esperado (comparación de cadena completa, ya existente) más
`Permissions-Policy` con las tres directivas `=()`. Se corre el verificador sobre fixtures de texto en
un test de bash, sin Docker.

**D7. Caddy.**
- C2V2-6: un test estático del `Caddyfile` fija `respond 421` en el bloque `:80` y el humo hace los
  ocho métodos contra un `Host` ajeno.
- C2V2-1: no se arregla (necesita dominio). Un test estático fija que el `Caddyfile` no tiene bloque
  `:443` ni `Strict-Transport-Security`, con el mensaje "si esto cambió, actualizá la declaración del
  spec y del 15". La declaración vive en el spec delta.
- N2: `reverse_proxy` con `transport http { dial_timeout 5s; response_header_timeout 30s }` en `api` y
  `web`. Los valores salen de lo que tarda la API más lenta hoy (`/api/salud`, plazo total menor a
  2,5 s, 1c) con holgura; se confirman al medir. El humo ya sabe pausar servicios, así que el
  escenario se prueba con `docker compose pause api`, y el paso mide que la respuesta llega antes de
  35 s. *Alternativa descartada:* un timeout global; tocaría a `web`, que sí puede tardar en el primer
  render.

**D8. `arranque_fallido` completo (única línea de código de producción).** En `app.py`, el
`leer_parametros(...)` entra en un `try/except` que registra `arranque_fallido` con la causa y vuelve
a levantar; en el lifespan, `verificar_rol_de_aplicacion_seguro` y `verificar_tablas_de_solo_agregar`
quedan envueltos también con `OperationalError`, y la causa dice "la base no es alcanzable" sin
`str(error)` (que en SQLAlchemy puede traer el DSN). Se prueba con un `Configuracion` real apuntando
a un puerto cerrado (integración, con Docker no hace falta: basta un puerto sin escuchar) y con un YAML
roto en `tmp_path`. *Riesgo vigilado:* L-007, que la causa nunca lleve credenciales.

**D9. Tests del log.** Un helper compartido `capturar_todo(caplog)` pone el logger raíz en `DEBUG` y
recorre todos los registros; la comparación del valor rechazado se hace contra
`registro.getMessage()` y cada campo extra por igualdad de valor, no por `representacion in str(...)`,
así un campo que contenga "123" no da rojo falso (N-b). Para ver el rojo (C2V2-2), el rompedor agrega un
`WARNING` temporal con el valor y se comprueba que el test lo ve.

**D10. Ensayo de roles en el CI con cabeza derivada.** El script obtiene la cabeza con
`compose run --rm --no-deps migraciones alembic heads` (formato `NNNN (head)`) y la guarda en
`CABEZA`; `verificar_revision "$CABEZA"`. El texto final imprime `$CABEZA`. `test_ensayo_login.py`
cambia de "el texto trae la cabeza real" a "el texto no trae ningún literal de revisión en
`verificar_revision` y usa `alembic heads`"; el `0016` del downgrade es una revisión fija a propósito
(la de origen del ensayo) y queda con un nombre (`REVISION_DE_ORIGEN`). Nuevo job `ensayo-roles` en
`ci.yml`, `timeout-minutes` por medición (L-044), `PROPTECH_COMPOSE_PROYECTO=proptech-ensayo`.
*Alternativa descartada:* sumarlo al job `humo`; si uno falla el otro queda sin verse, y los dos
hacen `down -v`.

**D11. Backend en paralelo.** `pytest-xdist` en el grupo de desarrollo. Cada worker de xdist es un
proceso con sus propios fixtures `scope="session"`, así que `postgres_contenedor` y el Redis ya son
**un contenedor por worker** sin tocar los fixtures; lo que hay que revisar es lo que dependa de un
nombre o un puerto fijo (`conftest.py`, tests de Redis caído/congelado, `test_compose.py`) y los tests
que levantan Docker Compose por su cuenta. `test-backend.sh` acepta `-n`; el CI usa un número fijo
(medido, ver tarea 9.3), nunca `auto`, porque el runner tiene 4 vCPU y cada worker agrega dos
contenedores. Los tests que no toleren paralelo se marcan `@pytest.mark.serial` con motivo y se corren
en una segunda pasada `-p no:xdist`. *Alternativa descartada:* una sola base con una base por worker
(`CREATE DATABASE`): los roles son del clúster y varios tests los manipulan (`roles_reales`).
*Separar unitarios de integración* en dos pasos del job aprovecha que los unitarios no necesitan
Docker y dan el rojo rápido.

**D12. Caché de Chromium.** `actions/cache` (fijado por SHA, L-037) sobre `~/.cache/ms-playwright` con
clave `playwright-${{ runner.os }}-${{ hashFiles('web/pnpm-lock.yaml') }}`; el paso
`playwright install --with-deps chromium` sigue corriendo siempre (instala las dependencias del
sistema, que no se cachean, y sólo descarga el navegador si falta), así que sin caché el job pasa
igual.

**D13. Dependabot.** `github-actions` en `/`, `docker` en `/backend` y `/web` (sus Dockerfile) y `docker-compose` en `/infra`
(las imágenes de `compose.yaml`: Postgres, Redis y Caddy; `docker` sólo lee Dockerfile, así que se corrigió al implementar), `uv` en `/backend`, `npm` en `/web`. Semanal, límite de 5 PR por
ecosistema, agrupados donde se pueda. Un test estático lee el YAML y verifica que cada directorio existe.
Que Dependabot abra los PR no es verificable en local.

**D15. `proptech` se rechaza siempre y el ensayo comparte los rechazos (cambia lo aprobado).** El
rechazo (b) del humo miraba `docker ps -q` y sólo actuaba con contenedores *corriendo*. El rompedor
(R1, 30/10/2026) mostró el hueco: con el stack real *detenido* (un `compose stop`, un reinicio) sus
volúmenes siguen vivos y el `down -v` del `trap limpiar` se los lleva. Decisión de Gianfranco: el valor
`proptech` se rechaza siempre, sin mirar Docker, y cualquier otro nombre sigue permitido. El mismo
riesgo vale para `ensayo-roles.sh` (R2: ahora corre en el CI, pero a mano conservaba `:-proptech`), así
que los tres rechazos (a, b, c) pasan a `exigir_proyecto_de_compose_propio` en `humo-lib.sh`, que
llaman el humo y el ensayo. *Alternativa descartada:* seguir con `docker ps -a` y `docker volume ls`
filtrados por etiqueta: es más fino pero depende de que Docker conteste y de etiquetas que cambian entre
versiones de Compose; rechazar el nombre no depende de nada. *Nota (auditor N5):* tras el arreglo B1 el ensayo ya no levanta Caddy, así que el rechazo (c) por
puertos no le hace falta; se conserva porque la función es una sola y es más conservador (un ensayo que
no publica puertos igual se niega junto a otro stack), y no cuesta nada en el CI. *Costo:* quien hoy corre el humo en el
proyecto `proptech` tiene que pasar otro nombre (el mensaje le dice cuál).

**D14. Tiempos y verificación.** Antes de cambiar nada se anotan los tiempos del baseline en WSL; al
cierre se repiten sobre el mismo commit. El CI real se lee sobre el SHA del PR (L-037, L-042), con el
límite de cada job puesto después de leer los tiempos por paso (L-044), y `test_ci_workflow.py` se
actualiza con cada límite.

## Risks / Trade-offs

- [xdist sube la memoria: 4 workers × (Postgres + Redis) en un runner de 16 GB] → medir pico; bajar a 2
  workers si hace falta; el criterio es el tiempo total y que los mismos tests pasen.
- [Tests de integración con estado compartido que sólo se rompen en paralelo] → primera pasada
  paralela en WSL antes de tocar el CI; `serial` con motivo escrito para los que no toleren.
- [El humo se niega ante `proptech` y alguien lo usa sin saberlo] → el mensaje dice cómo correrlo
  (`PROPTECH_COMPOSE_PROYECTO=proptech-humo bash infra/ci/humo.sh`); README lo documenta en la sección "Cómo correr la prueba
  de humo" (`test_ci_workflow.py::test_el_readme_explica_el_rechazo_del_humo` la fija).
- [El ensayo en el CI duplica el tiempo del `down -v` y del build] → job aparte y en paralelo con
  `humo`; el costo es minutos de runner, no de camino crítico.
- [Timeouts de Caddy demasiado cortos cortan una carga legítima de `web`] → `response_header_timeout`
  mide hasta la primera cabecera, no la descarga completa; se verifica con `/` y con el humo.
- [Comparar `qual` por texto falla si Postgres cambia el formato entre versiones] → las dos bases
  son la misma imagen; se fija la versión y el diff nombra la política.
- [`arranque_fallido` con `OperationalError` filtra el DSN] → no se loguea `str(error)`; test que busca la
  contraseña en el log (L-007).
- [Lo que no se puede probar local: Dependabot, caché, límites de tiempo del runner] → declarado en la
  proposal; se lee el run de GitHub sobre el SHA del PR antes de decir "listo".

## Migration Plan

Sin migraciones ni despliegue: sólo scripts, CI y una línea de la API. Rollback: `git revert` de los
commits del change; el único comportamiento visible para quien corre el humo es el rechazo ante un
stack `proptech` real. Se pushea sólo con el OK explícito de Gianfranco.

## Open Questions

Resueltas con una suposición, para confirmar al revisar la propuesta (ninguna cambia las specs ni las
tareas más que lo anotado):

1. **DA-12 (`.gitleaksignore`)**: depende de que se rebase el PR #4 (Emiliano), y no es verificable
   hoy. Se deja como tarea final *condicional*; si el PR #4 no se rebasó al cerrar, queda como deuda
   anotada y no bloquea el cierre.
2. **C2-8 en el worker**: la ficha nombra `proptech_api/app.py`; el spec dice "la API o el worker".
   Se hace sólo la API (la ficha) y se anota el worker como deuda si su arranque tiene el mismo
   hueco.
3. **Valores de los timeouts de Caddy (5 s y 30 s) y cantidad de workers**: se fijan al medir, no
   antes.
4. **Humo en paralelo con un stack real (deuda, fuera del change):** haría falta que los puertos de
   Caddy dejen de ser fijos (`infra/compose.yaml:368-370`, `"80:80"` y `"443:443"`, p. ej. con
   `${PROPTECH_PUERTO_HTTP:-80}`) y que la red `aplicacion` no fije su subred ni la IP de Caddy
   (`infra/compose.yaml:22` la subred `172.28.0.0/24`, `:374-375` el `ipv4_address: 172.28.0.254` de
   Caddy y `:191` el `FORWARDED_ALLOW_IPS` de la API, que depende de esa IP, D17), y que las 20 referencias a
   `localhost` de `humo.sh` usen ese puerto. Es cambiar la superficie de despliegue, no sólo el CI.
