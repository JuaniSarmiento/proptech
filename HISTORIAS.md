# Historias

Backlog del ciclo de Juani con Rein (D-146). Cómo se usa: `knowledge-base/14_forma_de_trabajo.md`;
método: `.rein/METODO.md`. El estado y el próximo paso viven en `obsidian.md`; las reglas y decisiones,
en `knowledge-base/` (acá se enlazan, no se copian).

Estados: Pendiente · En proceso · Lista · Terminada. Sólo Juani pasa una historia a Terminada.

Identificadores: historias `H-001`, `H-002`…; criterios `H-001.C01`. La aceptación de cada historia
vive en `aceptacion/<H-xxx>/`. En el tablero de Jarvis, que exige el formato `HU-…`, van como
`HU-H001`, `HU-H002`…

| HU | Change | Resultado esperado | Dificultad / riesgo | Estado |
|---|---|---|---|---|
| H-001 | C-27 `ejemplo-robusto` (PR #7) | El PR de Giuliano verificado e integrado a `main` | Baja / LOW | En proceso |
| H-002 | C-23 `humo-y-ci` (PR #5) | El PR de Gianfranco verificado e integrado a `main` | Media / MEDIUM | Pendiente |
| H-003 | C-24 `respaldos-2` (PR #6) | El PR de Emiliano verificado e integrado a `main` | Media / HIGH | Pendiente |

Orden: H-001 → H-002 → H-003. El #7 es el más chico y ya viene archivado; el #5 cambia el CI y el humo,
así que conviene que el #6 se rebase después sobre ese CI y corra con él.

## Revisión e integración de PRs del equipo

Relevamiento del 11/11/2026 sobre `main` en `4decbff`. Los tres PRs chocan con `main` sólo en
`knowledge-base/09_decisiones_y_supuestos.md`, porque todos agregan decisiones al final, y algunos números
se repiten: el #5 trae D-144 (en `main` es la del 6c) y el #6 trae D-144, D-145 y D-146 (las tres ya
usadas). Cada D que se renumera arrastra sus referencias dentro del diff (fichas, `CHANGES.md`, specs).

Criterios comunes a H-001, H-002 y H-003 (cada historia los lleva con su prefijo):

- **C01 · Rama integrable**: la rama del PR, al día con `main`, se fusiona sin conflictos; ninguna D se
  repite en `09_decisiones_y_supuestos.md` y toda referencia a una D renumerada apunta al número nuevo.
- **C02 · CI del PR en verde**: todos los checks del evento `pull_request` en verde sobre el SHA final del
  PR (un `workflow_dispatch` no cuenta).
- **C03 · Escenarios cubiertos**: cada escenario de las specs del change tiene al menos un test que corre
  y pasa; se comparan esperados contra ejecutados, y un faltante o un skip no es éxito.
- **C04 · Revisión independiente** según el riesgo (D-125), sin hallazgos bloqueantes abiertos.
- **C05 · Base de conocimiento cerrada**: change archivado en OpenSpec con sus specs sincronizadas,
  `CHANGES.md` marcado, el estado de `CLAUDE.md`/`AGENTS.md` al día e idénticos, y la deuda del cierre
  en su ficha de `12_fichas_de_changes.md`.

### H-001 · Integrar el PR #7, `ejemplo-robusto` (C-27, Giuliano)

- Change: C-27 / 3f `ejemplo-robusto`, D-145. Ya archivado en la rama
  (`openspec/changes/archive/2026-11-04-ejemplo-robusto/`).
- Resultado para Juani: el comando del ejemplo robusto en `main`, con la KB al día.
- Alcance: la rama `change/ejemplo-robusto` (6 commits, 34 archivos, sobre todo informes y KB; código en
  `compartido/` y tests de integración). Exclusiones: nada fuera del PR.
- Criterios: H-001.C01 a C05. Específicos:
  - H-001.C01: D-145 queda antes de D-146, sin cambiar de número.
  - H-001.C03: sobre la fusión con `main`, los tres archivos de tests del change
    (`test_ejemplo_casos_de_uso.py`, `test_arranque_tablas_protegidas.py` y
    `test_puntos_de_entrada_prohibidos.py`) dan **258 esperados y 258 pasados**, sin skips, fallas ni
    errores. La suite completa la corre el CI (C02).
  - H-001.C04: LOW, así que una sola pasada que rompe y audita. Entrega la matriz de los 34 escenarios
    de `datos-semilla` contra el test que cubre cada uno; un escenario sin test es un hallazgo.
  - H-001.C06: el comando del ejemplo devuelve los códigos de salida de D-145 e identifica el
    edificio por nombre.
- Dificultad y riesgo: baja / LOW (sin migraciones, permisos ni plata). El PR no tiene descripción.
- Constructor: a definir con Juani (Giuliano en su rama o `rein-constructor`).
- Demo: correr el comando del ejemplo dos veces y con un edificio inexistente, y mirar los códigos de salida.
- Aceptación aprobada por Juani el 11/11/2026: `58651ed95f53c68f077a258a4462323d27d5dbb7`, archivo
  `aceptacion/H-001/aceptar.py`. Comando: `git show 58651ed:aceptacion/H-001/aceptar.py >
  <fuera-del-repo>/aceptar.py && python3 <fuera-del-repo>/aceptar.py`, desde la raíz del repo. Casos
  esperados: C01, C02, C03 (258/258) y C05 en PASA; C04 y C06, con evidencia manual.
  Vista fallar por aserción: C01 contra el PR de hoy (conflicto en `09`), C03 esperando 257 (258
  ejecutados) y C05 contra `main` (sin el archivo del change). Sobre la fusión resuelta a mano en un
  worktree descartable: C01, C03 (258/258) y C05 pasan.
- Evidencia y demo: pendientes.

### H-002 · Integrar el PR #5, `humo-y-ci` (C-23, Gianfranco)

- Change: C-23 / 2e `humo-y-ci`, MEDIUM, sin firma previa. Trae su D-144, que hay que renumerar.
- Resultado para Juani: el humo y el ensayo de roles aislados en un proyecto de compose propio, cada
  falla nombrando paso, línea y comando, el backend del CI en paralelo y Dependabot, todo en `main`.
- Alcance: la rama `change/humo-y-ci` (21 commits, 46 archivos: `infra/ci/`, tests de infra, unitarios y
  de integración, `ci.yml`, `dependabot.yml`, `Caddyfile` y la causa de `arranque_fallido` en
  `proptech_api/app.py`).
- Criterios: H-002.C01 a C05. Específicos:
  - H-002.C01: su D-144 pasa a la próxima D libre al momento del merge.
  - H-002.C03: 40 escenarios (9 de `entorno-de-ejecucion` y 31 de `integracion-continua`).
  - H-002.C04: MEDIUM, así que un revisor y un rompedor.
  - H-002.C06: la tarea 10.4, la única abierta de 32, queda cerrada con el run completo leído sobre el
    SHA final.
  - H-002.C07: `humo.sh` y `ensayo-roles.sh` terminan con exit 1, antes de tocar `docker compose`,
    sin `PROPTECH_COMPOSE_PROYECTO`, con el valor `proptech` y con el 80 o el 443 ocupados. Con otro
    nombre, corren.
- Dificultad y riesgo: media / MEDIUM. **Cambia el comportamiento**: el humo sin la variable, o con
  `proptech`, deja de correr. Hay que avisarle al equipo.
- Constructor: a definir con Juani.
- Demo: correr el humo sin variable, con `proptech` y con `proptech-humo`, y forzar una falla para ver
  paso, línea y comando.
- Aceptación aprobada, evidencia y demo: pendientes.

### H-003 · Integrar el PR #6, `respaldos-2` (C-24, Emiliano)

- Change: C-24 / 1e `respaldos-2`, HIGH, firmado por Emiliano el 31/10/2026. Trae D-144, D-145 y D-146,
  que hay que renumerar.
- Resultado para Juani: retención por días con reloj atrasado, apagado ordenado, sin la carrera del 503,
  logs en JSON, la carpeta de respaldos creada sola y la conmutación a una base restaurada
  (`infra/respaldos/conmutar.sh`), todo en `main`.
- Alcance: la rama `change/respaldos-2` (22 commits, 24 archivos: `infra/respaldos/`, `infra/`, tests de
  infra y KB).
- Criterios: H-003.C01 a C05. Específicos:
  - H-003.C01: se rebasa después de H-002, y sus tres D pasan a las próximas libres.
  - H-003.C02: hoy el PR no muestra checks. El CI corrió por `workflow_dispatch` (el último, en verde el
    31/10), pero no como check del PR, y tiene que correr así.
  - H-003.C03: 46 escenarios (11 de `entorno-de-ejecucion` y 35 de `respaldos-de-la-base`).
  - H-003.C04: HIGH, así que un rompedor de otra familia de modelo y un revisor.
  - H-003.C06: la firma queda válida según D-094 y D-111. Emiliano firmó su propio change; Juani
    decide si vale o firma él o Alberto.
  - H-003.C07: el ensayo de conmutación de punta a punta corre contra Docker real en un proyecto de
    compose propio (backup, restauración, conmutación, `GET /api/salud` 200 y vuelta a la base
    original).
- Dificultad y riesgo: media / HIGH. Toca la restauración y la conmutación de la base. No escribe en
  `cuenta_corriente` ni en `pagos`, pero un error ahí apunta la aplicación a la base equivocada.
- Constructor: a definir con Juani.
- Demo: el ensayo de conmutación real y el apagado con SIGTERM a mitad de un volcado.
- Aceptación aprobada, evidencia y demo: pendientes.

## Changes por partir en historias

- **4c `intereses-saldo-inicial-y-moroso`** (CRITICAL): propuesta y diseño en
  `openspec/changes/intereses-saldo-inicial-y-moroso/`, sin commitear y sin la firma de D-094. Falta
  acordar con Juani cómo se parte en historias.

## Plantilla de historia

### H-xxx · título

- Change: (de `CHANGES.md`) y reglas o decisiones que cubre (`R03`, `D-143`…)
- Resultado para la persona:
- Alcance y exclusiones:
- Criterios de aceptación (`H-xxx.C01`…, con ejemplos):
- Dificultad y riesgo (LOW, MEDIUM, HIGH o CRITICAL):
- Constructor (modelo elegido por Juani; cualquier cambio, con su OK y el motivo):
- Brief y archivos relevantes:
- Aceptación aprobada: SHA, comando y casos esperados:
- Rompedor (CRITICAL y HIGH): informe y fallas devueltas:
- Evidencia: aceptación del SHA aprobado, suite completa (CI o Juani), pendientes:
- Demo y aprobación de Juani (fecha, o motivo del rechazo o la postergación):
