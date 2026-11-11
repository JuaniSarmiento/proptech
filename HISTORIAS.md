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
| H-001 | C-27 `ejemplo-robusto` (PR #7) | El PR de Giuliano verificado e integrado a `main` | Baja / LOW | Terminada |
| H-002 | C-23 `humo-y-ci` (PR #5) | El PR de Gianfranco verificado e integrado a `main` | Media / MEDIUM | Terminada |
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
  - ~~H-001.C04~~: **sacado por Juani el 11/11/2026.** Motivo: un LOW no lleva revisión aparte según la
    tabla de riesgo; el PR ya pasó por constructor, tres rompedores y auditor en su ciclo OPSX; y lo que
    nos toca (integración, tests completos, suite) ya lo cubren C01, C03 y C02. La primera corrida de
    Codex se trabó esperando stdin y la segunda se cortó antes de producir nada: no hay informe.
  - H-001.C06: el comando del ejemplo devuelve los códigos de salida de D-145 e identifica el
    edificio por nombre.
- Dificultad y riesgo: baja / LOW (sin migraciones, permisos ni plata). El PR no tiene descripción.
- Constructor: `rein-constructor` (Claude), elegido por Juani el 11/11/2026.
- Demo: correr el comando del ejemplo dos veces y con un edificio inexistente, y mirar los códigos de salida.
- Aceptación aprobada por Juani el 11/11/2026: **`25275f0db275c8a0ce051e1be3a1ab69a8d2a7bd`** (reemplaza
  a `58651ed`, que incluía C04; mismo código de verificación, sólo cambió la línea de C04). Archivo
  `aceptacion/H-001/aceptar.py`. Comando: `git show 25275f0:aceptacion/H-001/aceptar.py >
  <fuera-del-repo>/aceptar.py && python3 <fuera-del-repo>/aceptar.py`, desde la raíz del repo. Casos
  esperados: C01, C02, C03 (258/258) y C05 en PASA; C06, con evidencia manual.
  Vista fallar por aserción: C01 contra el PR de hoy (conflicto en `09`), C03 esperando 257 (258
  ejecutados) y C05 contra `main` (sin el archivo del change). Sobre la fusión resuelta a mano en un
  worktree descartable: C01, C03 (258/258) y C05 pasan.
- Construcción: `rein-constructor` (Claude), merge `a0ef218` pusheado a `change/ejemplo-robusto` el
  11/11/2026; D-145 antes de D-146, el diff del PR contra `main` sigue siendo de 34 archivos.
- Evidencia (11/11/2026, orquestador, aceptación sacada de `25275f0` a un archivo fuera del repo):
  cabeza `a0ef218` sobre `origin/main` `4decbff`. C01 PASA (146 decisiones, ninguna repetida), C02 PASA
  (5 checks del run 43023822732 en verde: backend 22m40s, humo, web, secretos, shellcheck), C03 PASA
  (258 esperados, 258 ejecutados, 258 pasados, 0 fallas, 0 errores, 0 skips), C05 PASA. Salida 0.
- Demo (C06), corrida por el orquestador el 11/11/2026 a pedido de Juani, sobre el código de `a0ef218`
  en el proyecto de compose `proptech-demo` (sólo `db` y `migraciones`, hasta la `0033`, y la imagen
  de `api` con `run --no-deps`). Override de red para la demo: la subred fija de `aplicacion`
  (`172.28.0.0/24`) choca con la red que quedó de `proptech-3c`, así que se movió a `172.32.0.0/24`
  sólo ahí. Resultados: (1) primera carga, "ejemplo cargado", código 0; (2) segunda carga, "el ejemplo
  ya estaba", 0; (3) sin `PROPTECH_ENTORNO=desarrollo`, "este comando es sólo para desarrollo… no se
  escribió nada", 1; (4) `--semilla ""`, "--semilla no puede estar vacío; no se escribió nada", 2;
  (5) con la base apagada, "la base no está disponible…", 5. Stack desarmado con `down -v`.
- Aprobación de Juani: **Terminada**, sí explícito el 11/11/2026 después de la demo. Integrada a `main`
  con el merge del PR #7.

### H-002 · Integrar el PR #5, `humo-y-ci` (C-23, Gianfranco)

- Change: C-23 / 2e `humo-y-ci`, MEDIUM, sin firma previa. Trae su D-144, que hay que renumerar.
- Resultado para Juani: el humo y el ensayo de roles aislados en un proyecto de compose propio, cada
  falla nombrando paso, línea y comando, el backend del CI en paralelo y Dependabot, todo en `main`.
- Alcance: la rama `change/humo-y-ci` (21 commits, 46 archivos: `infra/ci/`, tests de infra, unitarios y
  de integración, `ci.yml`, `dependabot.yml`, `Caddyfile` y la causa de `arranque_fallido` en
  `proptech_api/app.py`).
- Criterios (los verifica `aceptacion/H-002/aceptar.py`, salvo C08):
  - H-002.C01: la fusión con `main` no tiene conflictos; ninguna D ni L se repite; la decisión del 2e
    pasa de D-144 a **D-147** y sus tres lecciones de L-068 a L-070 a **L-073 a L-075** (en `main`,
    L-068 a L-070 son del 3f); ninguna línea que agrega el PR nombra D-144 ni L-068 a L-070.
  - H-002.C02: CI del evento `pull_request` en verde sobre la cabeza final.
  - H-002.C03: sobre la fusión, los 19 archivos de tests que prueban el change dan **167 esperados y
    167 pasados**, sin skips, fallas ni errores. Quedan afuera `test_rutas_protegidas.py` (591),
    `test_salud_cola_real.py` y `test_zz_rompedor_api_application_name.py`: el PR sólo les tocó la
    preparación, y los corre la suite completa del CI (C02). Ajustado por Juani el 11/11/2026 (eran 762).
  - H-002.C04: MEDIUM, sin rompedor (tabla de `14_forma_de_trabajo.md`): lo cubren la aceptación y
    el CI. Corregido el 11/11/2026, antes de aprobar su aceptación: decía "un revisor y un rompedor",
    arrastrado de D-125.
  - H-002.C05: change archivado con sus specs sincronizadas (cada requisito del delta está en
    `openspec/specs/`), `CHANGES.md` y la ficha del 2e al día, `CLAUDE.md` igual a `AGENTS.md`.
  - H-002.C06: ninguna tarea del change sin marcar; la 10.4 (push, PR y run leído) se cierra con la
    evidencia del run sobre la cabeza final.
  - H-002.C07: `humo.sh` y `ensayo-roles.sh` terminan con 1 **sin llamar a docker** sin
    `PROPTECH_COMPOSE_PROYECTO`, con `proptech` y con un puerto que miran ocupado; con otro nombre y los
    puertos libres pasan la guarda y llegan a docker. Se prueba con un `docker` falso en el `PATH`.
  - H-002.C08: demo.
- Deuda menor encontrada al escribir la aceptación: `ensayo-roles.sh` escribe su evidencia en `.git/` y
  falla en un worktree, donde `.git` es un archivo. No bloquea; va a la deuda del cierre del 2e.
- Dificultad y riesgo: media / MEDIUM. **Cambia el comportamiento**: el humo sin la variable, o con
  `proptech`, deja de correr. Hay que avisarle al equipo.
- Demo: correr el humo sin variable, con `proptech` y con `proptech-humo`, y forzar una falla para ver
  paso, línea y comando.
- Aceptación aprobada por Juani el 11/11/2026: **`ff7836bd015b4e5c300c5c05887ee1ccc026216a`**. Comando:
  `git show ff7836b:aceptacion/H-002/aceptar.py > <fuera-del-repo>/aceptar.py && python3
  <fuera-del-repo>/aceptar.py`, desde la raíz del repo. Casos esperados: C01, C02, C03 (167/167), C05,
  C06 y C07 en PASA; C08, demo.
- Constructor: `rein-constructor` con Sonnet, elegido por Juani el 11/11/2026.
- Historia de la aceptación: Vista fallar por aserción: C01 sobre una
  fusión de prueba (D-144 y L-068 a L-070 repetidas, 31 líneas con los números viejos), C03 esperando
  761 sobre los 22 archivos originales (762 ejecutados), C05 y C06 (change sin archivar), C07 contra
  `main` (los seis rechazos llaman a docker). Pasan sobre la fusión de prueba: los 762 tests de los 22
  archivos (1m56s; los 167 de los 19 que quedan están dentro) y C07 (8 casos). Los 19 archivos
  recolectan 167 en la cabeza del PR. C02 pasa hoy (6 checks sobre `f2be967`).
- Construcción (11/11/2026, `rein-constructor` Sonnet), pusheada a `change/humo-y-ci` (`f2be967..31ef580`):
  `17486b2` merge de `origin/main`, `c0e8ca8` renumeración (27 líneas), `f6add07` tarea 10.4 (run
  41154566331 sobre `f2be967`), `c809b0d` archivo con openspec 1.13.0 (13 requisitos sincronizados),
  `31ef580` KB del cierre. Sin atribución a IA (verificado por el orquestador).
- Evidencia (11/11/2026, orquestador, aceptación sacada de `ff7836b` a un archivo fuera del repo): cabeza
  `31ef580` sobre `origin/main` `6efbcea`. C01 PASA (D-147, L-073 a L-075, nada repetido), C02 PASA (6
  checks en verde: backend 8m50s, ensayo-roles 1m7s, humo, web, secretos, shellcheck), C03 PASA
  (167/167, 0 skips), C05 PASA, C06 PASA (32 tareas), C07 PASA (8 casos). Salida 0. El backend del CI
  bajó de 22m40s (run del PR #7) a 8m50s con la corrida en paralelo.
- Demo (C08), corrida por el orquestador el 11/11/2026 sobre un clon de `31ef580`, con un `docker` falso
  que devuelve 1: (1) sin la variable, "falta PROPTECH_COMPOSE_PROYECTO… Corrélo así: …", código 1;
  (2) con `proptech`, "el proyecto 'proptech' es el del stack de uso real y este script haría 'down -v'
  sobre él…", código 1; (3) con `proptech-humo` y el primer paso fallando, "paso 0 (compose up --build
  -d --wait) falló en la línea 52: docker compose -p \"$PROPTECH_COMPOSE_PROYECTO\" … (llamado desde la
  línea 109)", vuelca `ps -a` y `logs` y hace `down -v` sólo sobre `proptech-humo`; código 1. El camino
  feliz completo lo cubre el CI (humo 3m41s y ensayo-roles 1m7s en verde, C02).
- Aprobación de Juani: **Terminada**, sí explícito el 11/11/2026 después de la demo. Integrada a `main`
  con el merge del PR #5.

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
  - H-003.C04: HIGH, así que un rompedor de otra familia de modelo (sin revisor aparte). Corregido el
    11/11/2026, antes de aprobar su aceptación.
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
