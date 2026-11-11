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
| H-003 | C-24 `respaldos-2` (PR #6) | El PR de Emiliano verificado e integrado a `main` | Media / HIGH | Terminada |
| H-004 | C-07c 4c, parte 1 | Al emitir, la deuda vencida genera su interés simple al centavo, con corte y tramos | Alta / CRITICAL | Terminada |
| H-005 | C-07c 4c, parte 2 | Un edificio carga una sola vez la deuda que trae y genera interés desde la migración | Alta / CRITICAL | Terminada |
| H-006 | C-07c 4c, parte 3 | Cada cuenta y cada edificio dicen si están al día, con deuda de intereses o morosos críticos | Media / CRITICAL | Terminada |
| H-007 | C-08 5, parte 1 | Un edificio carga su padrón desde la plantilla de Excel, todo o nada, con un informe por fila | Alta / CRITICAL | Pendiente |
| H-008 | C-08 5, parte 2 | Los saldos previos quedan en un borrador comparado unidad por unidad, con las diferencias aceptadas | Alta / CRITICAL | Pendiente |
| H-009 | C-08 5, parte 3 | Confirmar carga el saldo inicial en el libro, cierra la migración y el importador | Alta / CRITICAL | Pendiente |
| H-010 | C-08 5, parte 4 | Un saldo inicial cargado de menos se corrige con un ajuste con motivo | Media / CRITICAL | Pendiente |

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
- Criterios (los verifica `aceptacion/H-003/aceptar.py`, salvo C04 y C07):
  - H-003.C01: la fusión con `main` no tiene conflictos (hoy chocan `CHANGES.md`, `09` y `15`); ninguna
    D ni L se repite; sus decisiones pasan de D-144 a D-146 a **D-148 a D-150** y sus lecciones de
    L-068 y L-069 a **L-078 y L-079**; ninguna línea que agrega el PR nombra los números viejos.
  - H-003.C02: CI del evento `pull_request` en verde sobre la cabeza final, con al menos 6 checks
    (`ensayo-roles` incluido). Hoy no corre porque el PR está en conflicto (`CONFLICTING`): GitHub no
    arma el commit de fusión y el `pull_request` no dispara. Por eso Emiliano lo corrió a mano.
  - H-003.C03: sobre la fusión, los 5 archivos de tests del change dan **108 esperados y 108 pasados**,
    sin skips, fallas ni errores.
  - H-003.C04: HIGH, así que un rompedor de otra familia de modelo (sin revisor aparte), sin
    bloqueantes. Corregido el 11/11/2026, antes de aprobar su aceptación.
  - H-003.C05: change archivado de verdad con sus specs sincronizadas y todas las tareas marcadas;
    `CHANGES.md` y la ficha del 1e al día; `CLAUDE.md` igual a `AGENTS.md`. Hoy la rama dice "archivado
    31/10/2026", pero el change sigue en `openspec/changes/respaldos-2/`: nunca se corrió el archivo.
  - H-003.C06: la propuesta archivada lleva la firma de Juani. **Firmada por Juani el 11/11/2026**
    (`93cba69` en la rama del PR), después del apply: ratifica lo construido sujeto a esta aceptación y
    al rompedor.
  - H-003.C07: demo con la conmutación real contra Docker, en un proyecto de compose propio (backup,
    restauración, conmutación, `GET /api/salud` 200 y vuelta a la base original), y el apagado con
    SIGTERM a mitad de un volcado.
- Dificultad y riesgo: media / HIGH. Toca la restauración y la conmutación de la base. No escribe en
  `cuenta_corriente` ni en `pagos`, pero un error ahí apunta la aplicación a la base equivocada.
- Constructor: `rein-constructor` con Sonnet, elegido por Juani el 11/11/2026. Rompedor: Codex (otra familia).
- Demo: el ensayo de conmutación real y el apagado con SIGTERM a mitad de un volcado.
- Aceptación aprobada por Juani el 11/11/2026: **`16d8719b1da5837694179d96c857284e49545818`**. Comando:
  `git show 16d8719:aceptacion/H-003/aceptar.py > <fuera-del-repo>/aceptar.py && python3
  <fuera-del-repo>/aceptar.py`, desde la raíz del repo. Casos esperados: C01, C02, C03 (108/108), C05 y
  C06 en PASA; C04 (rompedor) y C07 (demo), con evidencia manual. Vista fallar por aserción sobre una fusión de
  prueba: C01 (D-144 a D-146 y L-068, L-069 repetidas; 10 líneas con los números viejos), C05 (sin
  archivar), C06 (sin propuesta archivada) y C03 esperando 107 (108 ejecutados). Pasan sobre la fusión
  de prueba: los 108 tests (1m07s, 0 skips). C02 hoy falla: 0 checks.
- Construcción 1 (11/11/2026, `rein-constructor` Sonnet), pusheada a `change/respaldos-2`
  (`93cba69..401576f`): `237d85e` merge, `714d9d4` renumeración, `f8623cd` archivo con openspec 1.13.0 (8
  requisitos sincronizados), `401576f` KB del cierre. Sin atribución a IA ni cambios de código después
  del merge (verificado por el orquestador).
- Rompedor 1 (C04, Codex, sobre `401576f`): **con bloqueantes**. Informe en el scratchpad de la sesión;
  reproductores en `h003-tmp/` (`ataques.py`, `senales.py`, `test_ataques_reales.py`), corridos de nuevo
  por el orquestador con la misma salida. Bloqueantes: (B1) `conmutar.sh` acepta una base con políticas
  de RLS distintas (`consulta_rls` no compara roles ni permisivo/restrictivo: una fila antes bloqueada
  queda visible); (B2) F4 sigue abierto si el reloj del host retrocede de verdad (también el mtime): de
  7 copias nuevas sobreviven 2; (B3, heredado de `6efbcea`) la limpieza de `proptech-*.dump.parcial` no
  valida el patrón completo y borra archivos ajenos. Deuda: colisión de timestamp que pisa una copia
  validada (heredada), la base activa leída del contenedor `db` después de conmutar, D-149 publica la
  bandera antes del log (503 con 0 líneas), SIGTERM durante `pg_restore --list` agota el plazo, F8 con
  rutas con comillas y errores de `rm` crudos, `arrancar.sh` con rutas entre comillas en `.env`.
- Decisión de Juani (11/11/2026): los tres bloqueantes se arreglan en esta historia, con TDD desde los
  reproductores, y otra pasada del rompedor sobre ellos; las seis deudas van a la ficha 1e, sin dueño.
  Avisarle a Emiliano que se toca su rama. Vuelve a En proceso (nunca llegó a Lista).
- Construcción 2 (vuelta 2, Sonnet, `401576f..169d189`): B3 cerrado; B1 con la definición completa de
  cada política; B2 con mtime monótono. Rompedor 2 (Codex): **con bloqueantes**: B1 incompleto (un rol
  con coma en el nombre da el mismo resumen que dos roles) y regresión de B2 (un mtime futuro destruye
  el piso por días de D-148; si `touch` falla vuelve el 2/7). B3 pasó.
- Decisión de Juani (11/11/2026) para B2: **opción A**, si el reloj retrocedió el ciclo no borra nada y
  deja un log `reloj_atrasado` (D-151). Descartadas: contador persistido (reescribe la spec) y dejarlo
  como deuda. La aceptación con 115 tests queda sin aprobar hasta la vuelta 3, porque el número cambia.
- Construcción 3 (vuelta 3 de 3, Sonnet, `169d189..fc70425`): B1 con roles escapados con `quote_ident`;
  B2 opción A (D-151), con el mtime monótono revertido. Rompedor 3: **con bloqueantes**: B1 sigue
  abierto por el nombre de la política (`"p|*|false|PUBLIC|false|;q"` oculta una restrictiva: 0 filas en
  origen, 1 en destino, conmutación aceptada); deuda en B2: si el dump nuevo es el único con mtime
  futuro, la retención borra y no avisa (no se demostró pérdida de copias). Tope D-092 alcanzado.
- Decisión de Juani (11/11/2026): **cuarta vuelta acotada**: comparar las políticas en JSON y contar el
  archivo actual en la detección de D-151.
- Construcción 4 (Sonnet, `fc70425..00d7578`): B1 con un JSON de PostgreSQL (`jsonb_agg`) por tabla y
  política; B2 con el archivo actual en la detección. Rompedor 4 (pasada corta): **sin bloqueantes**;
  el nombre fabricado se rechaza (rc 1), una base equivalente con otros OID se acepta, el dump nuevo con
  mtime futuro conserva 4/4 y avisa una vez. **C04 cumplido.**
- **Aceptación vigente, aprobada por Juani el 11/11/2026: `8108f2fe3f3592da8b296715cc33cc0c9d2caa0c`**
  (reemplaza a `16d8719`): C03 pasa a 6 archivos y **121 tests** (13 nuevos de los arreglos, 6 en
  `test_conmutar_politicas_reales.py`). Comando: `git show 8108f2f:aceptacion/H-003/aceptar.py >
  <fuera-del-repo>/aceptar.py && python3 <fuera-del-repo>/aceptar.py`.
- Demo (C07), corrida por el orquestador el 11/11/2026 sobre un clon de `00d7578`, proyecto
  `proptech-demo` con el override de red: API en `proptech` con salud 200; backup del arranque; restaurado
  en `proptech_demo_restaurada` (código 0); conmutar a `proptech_no_existe` rechazado ("verificación 1
  (existencia)…", código 1, la API sigue en `proptech`); conmutar a la restaurada (código 0, la API en
  `proptech_demo_restaurada`, salud 200, `.env.anterior` con el valor previo); vuelta manual con
  `.env.anterior` (API en `proptech`, salud 200); SIGTERM: `stop` en 0,3 s, 0 parciales, evento `apagado`,
  **pero el volcado ya había terminado** (base chica): el SIGTERM a mitad del volcado lo cubren los tests y
  el reproductor del rompedor (`SENAL SIGTERM fase dump rc 0 parciales 0`). Stack desarmado con `down -v`.
- C02: el job `web` del PR cayó tres veces por la red del runner de GitHub (`Temporary failure resolving
  'azure.archive.ubuntu.com'` al instalar Chromium, sin correr tests; el PR no toca `web/`); también cayó
  así en `main` (`a8f5ed1`). **Decisión de Juani (11/11/2026): aceptar esa falla como externa.**
  **Aceptación vigente: `4c1d6438ae4c6e4ac5870a70ead45e7c76d526f8`** (reemplaza a `8108f2f`): C02 perdona
  sólo `web`, sólo si el paso fallido es "Instalar Chromium" y su log tiene `Temporary failure resolving`.
  Probado: True con el job real caído por DNS (130623673376) y False con un `backend` caído en "Tipos"
  (130568564628).
- Evidencia final (11/11/2026, orquestador, aceptación sacada de `4c1d643` a un archivo fuera del repo):
  cabeza `00d7578` sobre `origin/main` `a8f5ed1`. C01 PASA, C02 PASA (5 checks en verde; `web` caído por
  la red del runner, perdonado por la excepción), C03 PASA (121/121, 0 skips), C05 PASA, C06 PASA. Salida 0.
- Aprobación de Juani: **Terminada**, sí explícito el 11/11/2026. Integrada a `main` con el merge del PR #6.
- Evidencia y demo: pendientes.

## Changes por partir en historias

- Ninguno: el 4c quedó partido en H-004, H-005 y H-006 (11/11/2026).

## Interés, saldo inicial y moroso (4c, C-07c)

Partido el 11/11/2026 en tres historias, en orden y cada una sobre la anterior: H-004 (interés por mora,
grupos 1 a 5 de `tasks.md`), H-005 (saldo inicial, grupo 6) y H-006 (situación de cobranza, grupo 7). El
grupo 8 (cierre) se reparte entre las tres. Sin rompedor (D-152): todo lo que tiene que fallar va en la
aceptación. **Nada se construye sin la firma CRITICAL de E1 a E19** en `proposal.md` (D-094, D-111).
Desde D-154 las tres historias van en la rama `change/intereses-por-mora` (PR #20) y el CI de GitHub
corre una sola vez, al cerrar el change; el PR se mergea con H-006 Terminada y el CI en verde.

**CI de cierre del change (11/11/2026)**: PR #20 sobre `275336c`, los seis jobs en verde (backend con la
suite completa: 2.793 unitarios e infra y 2.528 de integración, 1 xfailed previo). Queda: las demos de
H-005 y H-006 con Juani, archivar el change y mergear a `main`.

**Delegación de Juani (11/11/2026)**: deja al orquestador a cargo de terminar el change entero: construir
H-005, **escribir y aprobar por adelantado los criterios de H-006** (sobre la spec
`situacion-de-cobranza` y las elecciones firmadas), construirla, correr el CI con la suite completa en
verde y dejar el PR #20 listo para mergear. Pasar cada historia a Terminada y mergear a `main` quedan
para Juani, después de las demos.

### H-004 · Interés por mora al emitir

- Change: C-07c 4c `intereses-saldo-inicial-y-moroso`. Reglas: R03, R07, R08, R17; decisiones D-109.5,
  D-113, D-143; elecciones E1 a E5, E10, E15, E17 y E19 de `design.md`, con su recomendación.
- Resultado para Juani: al registrar la emisión de un período, cada obligación vencida e impaga de las
  cuentas de unidad del edificio recibe su débito de interés simple al centavo, con su corte y su detalle
  por tramo; nunca interés sobre interés ni dos veces el mismo día.
- Alcance: deuda heredada (RB-6, RF-01, RF-02), migración `0034` sólo con `tramo_de_interes`, foto con
  corte y tramos, cálculo puro (`dominio/intereses.py`) e interés dentro de `registrar_emision`, su replay
  y su anulación. **Cambio contra `design.md` D10**: las dos tablas del saldo inicial pasan a una `0035`
  en H-005.
- Exclusiones: saldo inicial (H-005), situación de cobranza (H-006), cuentas de persona (4d), rutas de API
  y pantallas.
- Dificultad y riesgo: alta / CRITICAL.
- Base de los ejemplos, salvo que diga otra cosa: ordinaria de septiembre de $100.000 vencida el
  10/09/2026, 3% mensual proporcional, gracia 0.

Criterios que tienen que pasar:

- **H-004.C01 · Interés al emitir**: la emisión de octubre registra $2.000,00 con corte 30/09/2026 que
  referencia la emisión; una unidad sin obligación nueva también recibe su interés; `EmisionRegistrada`
  informa el interés y un saldo anterior de $102.000,00; emitir el 15/10 cobra sólo hasta el 30/09.
- **H-004.C02 · Simple y sólo sobre el capital**: noviembre da $3.100,00 (no sobre $102.000) con tramo
  desde el 01/10; pago parcial de $40.000 el 20/09 da $1.600,00 en tramos 11/09-20/09 y 21/09-30/09; pago
  total el 20/09 da $1.000,00 en un solo tramo 11/09-20/09; febrero de 2028 cuenta 19 días, $1.900,00.
- **H-004.C03 · Gracia de 5 días**: pagada el 15/09, sin interés; el 16/09, $600,00; vencida el 28/09 e
  impaga, octubre sin interés y noviembre $3.300,00.
- **H-004.C04 · Mes entero**: un día de atraso $3.000,00 (tramo 30/09); el mes siguiente $3.000,00 (tramo
  01/10-31/10); con gracia $6.000,00 en dos tramos; pago a mitad de mes $3.000,00 y $1.800,00; pago total
  $3.000,00 con tramo 11/09-30/09; de proporcional a mes entero $2.000,00 y $3.000,00; de mes entero a
  proporcional $3.000,00 y $3.100,00.
- **H-004.C05 · Configuración vigente al corte**: 3% y desde el 01/10 6% dan $2.000,00 y $6.200,00, y el
  primero no cambia; cada tramo guarda la versión de configuración del corte.
- **H-004.C06 · Redondeo único medio hacia arriba**: $62,50 da $0,13; dos tramos de $0,064 y $0,063 dan
  $0,13.
- **H-004.C07 · Re-emisión y huecos**: anular y volver a emitir no registra otro interés; noviembre
  recupera 51 días, $5.100,00 (o $10.200,00 con el 6%); un hueco que deja un contra-asiento se cobra en dos
  tramos, $5.000,00; los días con tasa 0 se cobran después, $5.100,00.
- **H-004.C08 · Replay**: repetir la emisión devuelve los mismos intereses sin escribir nada; saldo
  anterior $102.000,00 sin cambios, $72.000,00 después de un pago y $100.000,00 después de anular.
- **H-004.C09 · Una sola lectura y candados**: la última foto pide todas las cuentas alcanzadas, incluida
  la que sólo recibió interés; anular bloquea U1 y U2 en una sola llamada ordenada; una emisión
  concurrente con un pago de otra unidad termina sin interbloqueo.
- **H-004.C19 · Un día**: vencida el 29/09, $100,00.
- **H-004.C20 · Base con los tres componentes**: ordinaria $70.000, fondo $10.000 y extraordinaria
  $20.000 dan $2.000,00.
- **H-004.C21 · Tasa con decimales**: 2,5% da $1.666,67.
- **H-004.C22 · Pago imputado a interés y capital**: $30.000 el 05/10 ($2.000 al interés, $28.000 al
  capital); noviembre da 5 días sobre $100.000 más 26 sobre $72.000, $2.372,00.

Criterios que tienen que fallar o no registrar nada:

- **H-004.C10**: con tasa 0, o con un importe que redondea a $0,00, no hay débito.
- **H-004.C11**: sin configuración vigente al corte, o con sólo una versión futura, `Conflicto("configuracion")`
  y el libro sin cambios.
- **H-004.C12**: un edificio de otra administración da no encontrado, nunca conflicto de configuración.
- **H-004.C13**: las obligaciones de una emisión anulada no generan interés; un corte ya ocupado no recibe
  otro interés.
- **H-004.C14**: `tramo_de_interes` rechaza `UPDATE`/`DELETE` de la app (`42501`) y `TRUNCATE` del
  arranque (`P0001`); otra administración no ve tramos; un tramo ligado al movimiento de otra cuenta lo
  frena la FK; días incoherentes o mes entero mal formado (30/09-31/10, 01/10-30/10) los frena el CHECK.
- **H-004.C15**: `redondear_al_centavo` con un valor enorme da `MontoInvalido`, no `InvalidOperation`.
- **H-004.C16**: la anulación espera una corrección en curso, crédito o contra-asiento, y ninguna
  corrección queda escrita sobre una emisión ya anulada.
- **H-004.C23**: vencida el 30/09, el día del corte: sin interés en octubre.
- **H-004.C24**: vencida el 05/10, después del corte: sin interés en octubre.
- **H-004.C25**: pagada entera con fecha valor igual al vencimiento: nunca genera interés.
- **H-004.C26**: emitir el edificio A no toca ninguna cuenta del edificio B de la misma administración.
- **H-004.C27**: las cuentas de persona no reciben interés.

Cierre:

- **H-004.C17**: CI verde sobre el SHA final; `0034` sube y baja dentro del ciclo real de devolución de
  propiedad; ningún test atado a `0033`; los `test_cc_*` del 4b con el mismo conteo y sin fallas nuevas.
- **H-004.C18**: KB al día para el interés: R03 y R17 en `05`, `tramo_de_interes` en `04`, `08`, `11` y la
  ficha del 4c.
- **H-004.C28 · Cobertura**: cada escenario de `intereses-por-mora`, `libro-de-movimientos` y
  `reparto-de-montos` tiene su test en la aceptación; esperados contra ejecutados, un faltante o un skip
  es falla.

- Demo: correr la aceptación desde su SHA y, sobre una base real, emitir octubre y noviembre con
  septiembre impago y mostrar movimientos y tramos.
- Firma CRITICAL: Juani, 11/11/2026, E1 a E19 con la recomendación de `design.md` (`7dc5399`).
- Aceptación aprobada: **Juani la aprobó por adelantado el 11/11/2026**, antes de verla escrita ("sé
  que la aceptación está bien"), y dejó al orquestador a cargo de congelarla después de su revisión
  técnica (rojos por aserción, importes verificados) y de correr las tandas hasta Lista. Los importes de
  C19 a C22 verificados con `Fraction` (cierran todos). **SHA congelado: `d2da37ef509cfb88ef62d5e12b5d4b3ec18d270e`**; 67 tests (60 rojos por aserción y 7 de regresión sobre `7dc5399`, 0 errores, 0 skips), más C17, C18 y C28 en `aceptar.py`. Comando: `python3 aceptacion/H-004/aceptar.py`.
- Constructor: Sonnet (`rein-constructor`), elegido por Juani el 11/11/2026, en seis tandas secuenciales
  con brief y relevo propios (`.git/informes-intereses-saldo-inicial-y-moroso/brief-H-004-t1..t6.md` y
  `relevo-H-004-t1..t6.md`), rama `change/intereses-por-mora`, PR #20.
- Construcción (cada tanda verificada por el orquestador antes de lanzar la siguiente):
  - t1 (1.1 a 1.3): RB-6 arreglado; tests de RF-01 y RF-02 contra-asiento con mutantes rojos.
    Aceptación sobre `53cf5c0`: C15 PASA. Un id de test del 4b parametrizado rompía C17; arreglado en t3.
  - t2 (2.1, 2.2): `0034_tramo_de_interes` con protección y mutantes. **Decisión del orquestador**:
    semilla con configuración opcional (`con_configuracion=True`), porque por defecto rompía C11.
    Cuatro mutantes de protección los frena el chequeo de arranque antes que el test: dos defensas reales.
  - t3 (3.1, 3.2): partes de imputación que cuentan; la foto trae `corte` y `tramos`.
    `interes_desde` desde la migración queda para H-005.
  - t4 (4.1 a 4.3) y t5 (4.4, 4.5): cálculo puro en `dominio/intereses.py`, 88 tests unitarios,
    mutantes, regla E1 y propiedades con `hypothesis` contra un oráculo propio (400 ejemplos).
    Los escenarios de saldo inicial del cálculo quedan para H-005.
  - t6 (5.1 a 5.5): el interés dentro de `registrar_emision`, replay y anulación sobre las cuentas
    alcanzadas. Regresión `test_cc_`/`test_libro`: 429 pasados (405 de base + 24 nuevos), ningún id
    cambiado. Mes entero con días no contiguos: la emisión rechaza con `Conflicto("interes")` sin
    escribir. Mutantes débiles declarados: M12 (bloquear en dos pedidos) depende del orden de los uuid;
    "el replay recalcula y escribe" sin mutante posible con E1.
- Demo preparada: el guion corre en un clon de la rama y muestra el libro y los tramos (septiembre
  impago, octubre $2.000,00, pago de $30.000 el 05/10, noviembre $2.372,00 en dos tramos, saldo
  anterior $74.372,00). Probada el 11/11/2026.
- Evidencia final (11/11/2026): `python3 aceptacion/H-004/aceptar.py --codigo f2f56d5` desde la
  aceptación `d2da37e`: **67 esperados, 67 ejecutados, 67 pasados**, 0 fallas, 0 errores, 0 skips;
  C01 a C16, C19 a C27, C18 y C28 PASA; C17 PASA en el ciclo de la `0034`, sin tests atados a la `0033` y
  con los tests del 4b enteros, y **queda pendiente sólo el CI del PR #20**, que no corrió por la caída de
  GitHub Actions ("major outage" en githubstatus.com, corridas en cola desde las 17:19). Dos vueltas
  previas del CI cayeron por L-064 (el ensayo de roles y tres tests que bajan migraciones no devolvían
  `tramo_de_interes`); arregladas en `7a7e972` y `a74f342`, con un barrido de 53 archivos (1.313 en verde).
- Demo (11/11/2026, en vivo sobre `f2f56d5` y PostgreSQL real): octubre $2.000,00 (20 días), pago de
  $30.000 el 05/10, noviembre $2.372,00 en dos tramos (5 días sobre $100.000 y 26 sobre $72.000), saldo
  anterior $74.372,00.
- CI del PR #20 sobre `92ac3bc` (el código final de H-004), cuando volvió GitHub Actions: los seis jobs en
  verde (backend 10m51s con la suite completa, ensayo-roles, humo, secretos, shellcheck, web). C17 cerrado.
- Aprobación de Juani: **Terminada**, sí explícito el 11/11/2026 ("sí, perfecto entonces"). El PR #20 se
  mergea recién con el CI en verde.

### H-005 · Saldo inicial

- Change: C-07c 4c. Reglas: R09, R03, R04, R05, R08; decisiones D-080, D-082, D-083, D-153; elecciones
  E9, E11, E13, E16, E18 con la recomendación firmada; `design.md` D5; spec `saldo-inicial`.
- Resultado para Juani: un edificio que llega con deuda previa la carga una sola vez, queda en el libro
  con su origen (archivo y fila), y el interés de R03 corre desde la fecha de migración.
- Alcance: migración `0035` (`carga_de_saldo_inicial`, `origen_de_saldo_inicial`),
  `registrar_saldo_inicial` (lo llama el 5) y el `interes_desde` desde la migración que quedó de H-004
  (foto y escenarios del cálculo). Exclusiones: el Excel, el borrador y la comparación (5); autorizar y
  auditar (D9, del llamador).
- Dificultad y riesgo: alta / CRITICAL. Rama `change/intereses-por-mora` (D-154: sin CI por historia).
- Base de los ejemplos: migración 15/10/2026, 3% proporcional, gracia 0.
- Criterios acordados con Juani el 11/11/2026:
  - Tienen que pasar: **C01** dos períodos de U1 (agosto $80.000, septiembre $85.000) dan dos
    obligaciones y $165.000; **C02** dos conceptos de septiembre de U5 dan una obligación ($85.000 +
    $20.000) y un interés importado de $3.000,00; **C03** total único de $50.000: una obligación, período
    01/10, vence 15/10; **C04** interés importado tal cual con corte 15/10 y fuera de la base (agosto con
    $4.000; total único con $2.000 debe $52.000; fila de sólo interés junto a otra con capital entra);
    **C05** proporcional después de migrar: noviembre cobra 16 días, $1.280,00 y $1.360,00, nada antes
    de la migración; **C06** mes entero: $2.400,00 y $2.550,00 (tramo 16/10-31/10), igual con interés
    importado, y diciembre $2.400,00 (01/11-30/11); **C07** total único con gracia 5: pagado el 19/10
    sin interés, impago 16 días $800,00; **C08** crédito inicial: U3 $3.000 a favor, U4 $10.000 − $3.000
    debe $7.000, crédito $15.000 contra $10.000 deja $5.000 a favor; **C09** origen: fila 7 de
    `saldos-octubre.xlsx` ligada a agosto de U1, la obligación de U5 a las filas 12 y 13 y su interés
    sólo a la 12, carga manual con motivo; **C10** replay: el mismo pedido devuelve lo mismo sin
    escribir, también confirmada, en otro orden o con `85000` por `85000.00`; **C11** devuelve cuenta,
    capital, interés importado y crédito por unidad y del edificio; **C12** migración el 31/10:
    noviembre sin días, diciembre 01/11-30/11.
  - Tienen que fallar sin escribir nada: **C13** estado (sin saldos previos o confirmada sin carga →
    `estado_migracion`; segunda carga → conflicto y una sola; dos simultáneas → una entra); **C14**
    fechas (vencimiento posterior a la migración, período que no es día 1 o posterior al mes de
    migración, migración futura, mismo período con vencimientos distintos → `vencimiento`); **C15**
    montos (período con sólo interés → `interes_acumulado`; importe negativo o crédito 0 → `importe`);
    **C16** forma (unidad repetida o sin filas → `unidades`; mezcla de detalle y total o fila repetida
    → `fila`; manual sin motivo → `motivo`; importador sin archivo → `archivo`); **C17** el mismo
    `operacion_id` con otro importe o con iguales sumas en otras filas → `operacion_id`; **C18** tenant
    (unidad de otro edificio u otra administración → no encontrado; B no ve cargas ni orígenes de A; sin
    transacción → error); **C19** tablas nuevas (`42501`, `P0001`, CHECK de origen, firma, fila y una
    sola referencia, FK a la obligación de otra cuenta).
  - Cierre: **C20** la `0035` sube y baja en el ciclo de devolución, las dos tablas en el ensayo de
    roles y en todos los tests que bajan migraciones; la aceptación de H-004 y los tests del 4b siguen
    verdes; **C21** KB (R09 en `05`, tablas en `04` y `08`, glosario, ficha 4c); **C22** cada escenario de
    la spec `saldo-inicial` con su test en verde. Sin criterio de CI (D-154).
- Demo: cargar `saldos-octubre.xlsx` (inventado), emitir noviembre y mostrar libro, orígenes e interés
  desde la migración.
- Construcción (Sonnet, tres tandas verificadas una por una): t1 `0035_saldo_inicial` con protección,
  mutantes, ensayo de roles y barrido local de migraciones (1.315 en verde); agregó `ck_origen_sentido`
  (sin sentido la FK a `movimiento` no se evalúa), aceptado. t2 `registrar_saldo_inicial` con la firma
  del pedido (49 tests, 17 mutantes; los rechazos dentro de un SAVEPOINT). t3 el interés desde la
  migración: la foto trae `interes_desde` con un `LEFT JOIN` a la carga; 3.2, 4.2, 4.3 y 6.3 cerradas.
- **Correcciones de la aceptación hechas por el orquestador** (sin tocar ningún criterio): C19 metía dos
  cargas en un edificio (recongelada en `2fcf6ba`); la regresión de C20 perdona sólo el test de H-004
  que fija la cabeza en `0034` con ese mensaje exacto (quedó atado a su momento, `d083832`); R09 tenía
  "carga de saldo inicial" partido en dos líneas.
- Evidencia (11/11/2026): `python3 aceptacion/H-005/aceptar.py --codigo d083832` desde `2fcf6ba`:
  **60/60**, 0 fallas, 0 errores, 0 skips; C01 a C22 PASA, con C20 corriendo H-004 67/67, los tests del
  4b y el barrido de migraciones. La aceptación de H-006 (su C19) volvió a correr H-005 60/60 sobre
  `4cb5e36`.
- Demo probada (11/11/2026, PostgreSQL real): carga de U1 (agosto $80.000 con $4.000 de interés y
  septiembre $85.000), U2 (total único $50.000 con $2.000), U3 (crédito $3.000) y U4 ($300); orígenes
  fila por fila; replay en otro orden sin escribir; segunda carga rechazada; noviembre cobra $1.280,00 y
  $1.360,00 desde el 16/10.
- Aprobación de Juani: **Terminada**, sí explícito el 11/11/2026 ("sisi"), después de la demo en vivo
  sobre `0caafe1`.
- Constructor: Sonnet en tandas (migración; carga; interés desde la migración). Tests: sólo los de los
  archivos tocados, más el barrido local de migraciones (la historia agrega tablas).
- Aceptación: **congelada en `0b4c5cb69628cd69c7a6ee49ac27f3fb439c1234`** (aprobación por delegación de Juani, después de la revisión técnica): 60 tests, 60 rojos por aserción sobre `aee113a`, 0 errores, 0 skips; C20 (ciclo de la `0035`, ensayo de roles, H-004 67/67 desde `d2da37e`, tests del 4b, barrido de migraciones), C21 y C22 en `aceptar.py`. Contrato para el constructor en `aceptacion/H-005/CONTRATO.md`. **Recongelada en `2fcf6ba91c518abcaccdd5ac5aef3c09bdecaea9`** (11/11/2026, por el orquestador): el test `test_c19_una_carga_y_su_origen_bien_formados_entran` metía dos cargas en el mismo edificio, contra la carga única de D5 y C13; lo encontró la tanda 1. Ahora la carga manual entra en un savepoint que se deshace. Ningún otro test cambió. Importes verificados con `Fraction`. Comando: `python3 aceptacion/H-005/aceptar.py --codigo HEAD` (unos 20 min con la regresión; `--sin-regresion` para una corrida rápida).

### H-006 · Situación de cobranza

- Change: C-07c 4c. Reglas: R20, R30, R05, R08; decisiones D-058, D-074, D-081, D-109.3, D-109.4,
  D-143; elecciones E6, E7, E8, E14 con la recomendación firmada; `design.md` D6; spec
  `situacion-de-cobranza`.
- Resultado para Juani: para una cuenta de unidad o para un edificio entero y a una fecha, el sistema
  dice cuánto hay vencido, cuántas liquidaciones vencidas con capital, si está bajo el umbral de saldos
  chicos, si es sólo deuda de intereses y si es moroso crítico, derivado del libro y nunca guardado.
- Alcance: `dominio/cobranza.py` (`clasificar`, puro) y `aplicacion/cobranza.py`
  (`situacion_de_cuenta`, `situacion_del_edificio`). Exclusiones: rutas, pantallas, avisos (10a), gestión
  judicial (10b), cuentas de persona (4d), historia de la deuda a una fecha pasada (E14).
- Dificultad y riesgo: media / CRITICAL. Sin migraciones.
- **Criterios escritos y aprobados por el orquestador por delegación de Juani (11/11/2026)**, sujetos a su
  demo. Base de los ejemplos: umbral $500, gracia 0, salvo que diga otra cosa.
  - Tienen que pasar: **C01** vencida desde que corre el interés: gracia 5 y vencimiento 10/09, al 15/09
    no está vencida y al 16/09 sí; **C02** total vencido con el interés en su período: agosto ($80.000 +
    $4.000 de interés) y septiembre ($85.000) dan $169.000 y dos liquidaciones, no tres; **C03** umbral:
    $300 en dos períodos queda bajo el umbral y no es moroso; $300 + $250 no queda bajo y es moroso;
    exactamente $500 es moroso (E6, `>=`); el umbral no frena el interés: la emisión de octubre registra
    $6,00 sobre $300 de septiembre (20 días al 3%); **C04** moroso crítico: una sola vencida no; dos con
    capital sí; un pago parcial de agosto no lo cambia; $500 + $20 sí (D-143); un período con sólo
    interés no cuenta (E7: agosto con sólo $4.000 de interés y septiembre con capital es una liquidación,
    no moroso); contra-asentar el pago de agosto vuelve a marcar; **C05** deuda de intereses: sólo $4.000
    de interés vencido es deuda de intereses, no moroso, total $4.000; **C06** saldo inicial: U1 migrada
    con dos períodos es morosa; U2 con total único tiene una liquidación y no es morosa; **C07** la fecha
    clasifica y no reconstruye (E14): con pagos del 20/10 y fecha 30/09, total vencido $0; **C08** por
    edificio: una entrada por cada cuenta de unidad con todos los campos; **C09** la etiqueta única
    respeta la precedencia de D6 (sin deuda vencida → bajo el umbral → deuda de intereses → moroso
    crítico → con deuda vencida), con un caso por etiqueta; **C10** la configuración es la vigente a la
    fecha: con umbral $500 hasta el 30/09 y $1.000 desde el 01/10, $700 vencidos en dos períodos son
    moroso al 30/09 y bajo el umbral al 31/10; **C11** es una lectura: no escribe nada ni toma candados.
  - Tienen que fallar o no contar: **C12** una obligación de una emisión anulada no cuenta; **C13** una
    obligación con fecha igual a vencimiento + gracia no está vencida, y una que vence después de la
    fecha tampoco; **C14** edificio o cuenta de otra administración → no encontrado; **C15** sin versión
    de configuración vigente a la fecha, o sólo una futura → `Conflicto("configuracion")`; **C16** las
    cuentas de persona no aparecen en el listado del edificio.
  - Cierre: **C17** KB: R20 con `>=` (se corrige "supera", E6) y dónde vive, R30 dónde vive, glosario
    (situación de cobranza, fecha de clasificación, deuda de intereses), ficha 4c con H-006; **C18** cada
    escenario de la spec `situacion-de-cobranza` con su test en verde; **C19** las aceptaciones de H-004
    y H-005 siguen en verde. Sin criterio de CI: el CI con la suite completa cierra el change (D-154).
- Demo: un edificio con cinco unidades (al día, saldo chico, deuda de intereses, una vencida, moroso
  crítico) y su listado.
- Construcción (Sonnet, una tanda): `dominio/cobranza.py` (`clasificar`) y `aplicacion/cobranza.py`
  (`situacion_de_cuenta`, `situacion_del_edificio`), sin escrituras ni candados; mutantes en rojo (umbral
  `<=`, período con sólo interés, crédito restado, gracia ignorada, umbral fijo, filtro por fecha valor,
  tenant en la sentencia). Agregó que una cuenta de persona da `NoEncontrado` en `situacion_de_cuenta`,
  con test (fuera del contrato, aceptado). Un mutante equivalente declarado (la exclusión de anuladas ya
  la hace `calcular_estado`).
- Evidencia (11/11/2026): `python3 aceptacion/H-006/aceptar.py --codigo 4cb5e36` desde `3f6629b`:
  **33/33**, C01 a C19 PASA, con C19 corriendo H-004 67/67 y H-005 60/60.
- Demo probada: el listado del edificio migrado da U1 moroso crítico ($171.640, dos liquidaciones), U2
  con deuda vencida ($52.800, una), U3 sin deuda vencida y U4 bajo el umbral ($304,80).
- Aprobación de Juani: **Terminada**, sí explícito el 11/11/2026 ("sisi"), después de la demo en vivo
  sobre `0caafe1`, junto con H-005.
- Aceptación: **congelada en `3f6629bbdbc69ca81f31b1716a28a9d1c1fc1401`** (aprobación por delegación de Juani, después de la revisión técnica): 33 tests, 33 rojos por aserción sobre `3378b43`, 0 errores, 0 skips; C17 (KB), C18 (20 escenarios) y C19 (H-004 y H-005 desde sus SHA) en `aceptar.py`. Contrato en `aceptacion/H-006/CONTRATO.md`. Importes verificados con `Fraction`.

## Importación desde Excel (5, C-08)

Propuesta, diseño, specs y tareas en `openspec/changes/importacion-desde-excel/`. **Firma CRITICAL por
adelantado de Juani** (`04ebf1e`, 11/11/2026, opción 1): aprueba las elecciones E1 a E15 de `design.md`
en la recomendación del orquestador; lo que no le cierre en la demo vuelve a En proceso. **Los criterios de
H-007 a H-010 los escribió el orquestador por delegación de Juani, bajo esa firma.** Rama
`change/importacion-desde-excel`; sin rompedor (D-152); el CI de GitHub con la suite completa corre una vez
al cerrar el change (D-154); las historias que agregan tablas protegidas corren el barrido local de
migraciones (L-083).

**Base de los ejemplos** (datos inventados): edificio "Torre Ficticia" con 3 pisos y 1 subsuelo (pisos
`SS1`, `PB`, `1`, `2`, `3`), migración el 15/10/2026, hoy 11/11/2026, 3% proporcional, gracia 0, umbral
$500. Plantilla `padron-torre-ficticia.xlsx` con 12 unidades (`1A`…`3D`, `C1`, `C2`) cuyos coeficientes
suman 1. Los criterios de interfaz se prueban en navegador real con Playwright (e2e de `web/`).

### H-007 · Plantilla y padrón

- Change: C-08 5. Reglas: R09, R01, D-068, D-077, D-100, D-128; elecciones E1 a E9, E14, E15.
  Spec `importacion-de-padron`; tareas 1.1 a 1.6.
- Resultado para Juani: el administrador sube la plantilla y, si está bien, el edificio queda con su
  padrón y sus propietarios; si tiene un solo error, no se carga nada y ve todos los errores, con hoja,
  fila, columna y motivo.
- Alcance: módulo `importacion`, lector de la plantilla, validación del padrón, migración `0036`, caso de
  uso de importar (padrón), ruta y pantalla de importar. Exclusiones: saldos (H-008), confirmar (H-009),
  ajuste (H-010), grupos parciales, inquilinos, invitar.
- Dificultad y riesgo: alta / CRITICAL.
- Tienen que pasar:
  - **C01** archivo válido de 12 unidades: el edificio queda con 12 unidades con su tipo, piso,
    coeficiente y superficie, todas en el grupo general, y una auditoría de alta por unidad.
  - **C02** columnas en cualquier orden (por ejemplo `Email, Piso, Unidad, Superficie m2, Tipo,
    Coeficiente, Propietario`) se leen igual; columnas extra se ignoran.
  - **C03** propietarios: 10 filas con propietario y email crean 10 personas y 10 asignaciones de vecino
    propietario, **sin ninguna invitación encolada**; un propietario sin email se crea sin email; el
    mismo email en dos filas es una sola persona propietaria de las dos unidades; un email que ya existe
    en la administración reusa esa persona.
  - **C04** números: `0,083333` y `0.083333` como texto, y una celda numérica `0.083333`, dan el mismo
    coeficiente; `8.3e-05` en una celda numérica es `0.000083`; `45,5` y `45.50` de superficie dan `45.50`;
    una fórmula con valor en caché se lee por su valor.
  - **C05** coeficientes que suman `0.9999` (dentro de la tolerancia) cargan con la advertencia de la suma;
    `1.0001` también; exactamente `1` sin advertencia.
  - **C06** el edificio ya con unidades acepta un archivo sin hoja `Unidades` o con la hoja vacía (para
    los saldos de H-008) sin tocar el padrón.
  - **C07** la respuesta informa unidades creadas, propietarios creados y reusados, y advertencias.
  - **C08** interfaz (Playwright): subir el archivo válido muestra el resumen; subir uno con errores
    muestra la tabla de errores (hoja, fila, columna, motivo) y no cambia el padrón; el botón descarga la
    plantilla.
- Tienen que fallar sin escribir nada (0 unidades, 0 personas, 0 importaciones, ninguna auditoría):
  - **C09** archivo: un `.csv`, un PDF renombrado a `.xlsx`, un `.xlsx` corrupto, un archivo de 3 MiB,
    una hoja con 2.001 filas de datos, sin la hoja `Unidades` en un edificio sin unidades, una hoja con
    otro nombre (`unidades`, `Unidades `), un encabezado faltante o mal escrito (`Coeficiente ` o
    `Coef.`), con un error que nombra hoja y columna.
  - **C10** filas: `Unidad` vacía, de 41 caracteres o con un carácter de control; `Unidad` repetida en el
    archivo (el error nombra la otra fila); `Tipo` vacío o fuera del vocabulario (`Depto`, `Departamento`);
    `Piso` vacío, fuera del vocabulario (`4`, `SS2`), con variantes (`1°`, `Entrepiso`, `planta alta`) o
    con espacios (` PB`); `Coeficiente` 0, negativo, mayor que 1, con 7 decimales o ambiguo (`1.234`);
    `Superficie m2` 0, negativa o con 3 decimales; email inválido; una fórmula sin valor en caché.
  - **C11** todos los errores juntos: un archivo con 3 errores en 3 filas distintas devuelve los 3, cada
    uno con hoja, fila del Excel (el encabezado es la fila 1), columna y motivo.
  - **C12** coeficientes que suman `0.9998` o `1.0002` (fuera de la tolerancia) rechazan el archivo
    nombrando la suma y la tolerancia.
  - **C13** padrón: el edificio sin pisos configurados rechaza nombrando `piso`; el edificio con unidades
    rechaza una fila en `Unidades`; una `Unidad` que ya existe en el edificio es error de fila.
  - **C14** reimportación: el mismo archivo (misma huella) subido de nuevo al mismo edificio da conflicto
    en `archivo` nombrando la importación anterior, y el padrón no cambia.
  - **C15** estado: con la migración en `confirmada` o `sin_saldos_previos` da conflicto en
    `estado_migracion`.
  - **C16** permisos y tenant: contador, auxiliar, consejo, vecino propietario e inquilino reciben 403;
    un administrador por edificio de **otro** edificio recibe 403; la administración B sobre un edificio
    de A recibe 404; sin sesión, 401.
  - **C17** concurrencia: dos subidas simultáneas del padrón al mismo edificio vacío: una crea las 12
    unidades y la otra da conflicto; nunca quedan 24.
- Cierre:
  - **C18** la migración `0036` sube y baja dentro del ciclo de devolución; `importacion` con RLS forzada
    (otra administración no ve filas); las acciones nuevas en el vocabulario de auditoría y en la matriz;
    los tests de fronteras, rutas cubiertas y vocabulario en verde; las aceptaciones de H-004 a H-006
    siguen en verde.
  - **C19** KB: R09 y R01 en `05`, `importacion` en `04` y `08`, las acciones en `03`, HU-A2 en `06`,
    Flujo 2 en `07`, glosario (plantilla), ficha 5.
  - **C20** cada escenario de la spec `importacion-de-padron` tiene su test en verde.
- Demo: subir `padron-torre-ficticia.xlsx` en el navegador, ver el resumen; subir una copia con tres
  errores y ver la tabla; subir el mismo archivo otra vez y ver el rechazo.

### H-008 · Borrador de saldos y comparación

- Change: C-08 5. Reglas: R09, D-068, E11/E16/E18 del 4c; elecciones E7, E13, E14. Spec
  `borrador-de-saldos`; tareas 2.1 a 2.5.
- Resultado para Juani: los saldos previos del Excel quedan en un borrador que no toca el libro, comparado
  unidad por unidad con el control del administrador; con diferencias, se aceptan con registro.
- Alcance: validación de `Saldos` y `Control`, migración `0037`, borrador, comparación, aceptación, rutas
  y pantalla de comparación. Exclusiones: confirmar (H-009).
- Dificultad y riesgo: alta / CRITICAL.
- Tienen que pasar:
  - **C01** `1A` con agosto ($80.000 ordinaria, vence 10/08, $4.000 de interés) y septiembre ($85.000,
    vence 10/09) queda en el borrador con sus dos filas y su número de fila del Excel.
  - **C02** `1B` con septiembre ordinaria $85.000 y extraordinaria $20.000 (mismo vencimiento) queda como
    dos filas del mismo período.
  - **C03** `2A` sin período (total único) $50.000 con $2.000 de interés; `2B` con −$3.000 (crédito).
  - **C04** el libro no cambia: ninguna cuenta, obligación ni movimiento nuevo en el edificio.
  - **C05** comparación: por unidad, borrador (capital + interés − crédito), control y diferencia; totales
    del borrador y del control; cantidad de unidades con diferencia. `1A` con borrador $169.000 y control
    $169.000 no tiene diferencia.
  - **C06** dos errores de signo opuesto: `1A` $10.000 de más y `2A` $10.000 de menos; los totales
    coinciden y la comparación muestra las dos diferencias.
  - **C07** unidad con control y sin saldo, y unidad con saldo y sin control, aparecen con su diferencia.
  - **C08** con "mes entero" vigente a la migración, cada unidad con deuda avisa que el primer interés
    cubre octubre de 2026; con "proporcional" no hay aviso.
  - **C09** aceptar diferencias: el administrador principal acepta; queda la lista exacta (unidad,
    borrador, control, diferencia), quién y cuándo, y una auditoría.
  - **C10** un borrador nuevo (otro archivo con el padrón ya creado) descarta el anterior y la aceptación
    anterior deja de valer.
  - **C11** números de importes: `85.000,00`, `85000,00`, `85000.00` y la celda numérica `85000` dan lo
    mismo.
  - **C12** interfaz (Playwright): la comparación muestra las diferencias aunque el total coincida, el
    aviso de mes entero y el botón "Aceptar diferencias" con su confirmación.
- Tienen que fallar sin escribir nada:
  - **C13** filas de `Saldos`: unidad inexistente; período posterior al mes de la migración; período que
    no es un mes (`2026-13`); vencimiento posterior a la migración; vencimiento vacío con período; dos
    vencimientos en el mismo período de una unidad; concepto fuera del vocabulario; importe con 3
    decimales o ambiguo (`1.234`); interés acumulado negativo; período con capital 0 y sólo interés (E11);
    una unidad que mezcla filas con y sin período; crédito con período o concepto.
  - **C14** hojas: `Saldos` sin `Control`; `Control` con una unidad inexistente o repetida; encabezados
    faltantes en `Saldos` o `Control`.
  - **C15** aceptar: un administrador por edificio, contador, consejo o vecino reciben 403; sin
    diferencias no hay nada que aceptar (conflicto); otra administración 404; con la migración cerrada,
    conflicto en `estado_migracion`.
- Cierre:
  - **C16** la migración `0037` sube y baja en el ciclo de devolución; `aceptacion_de_diferencias` de sólo
    agregar (`42501` para la app, `P0001` para el arranque, otra administración no la ve); las tablas en
    el ensayo de roles y en los tests que bajan migraciones (barrido local en verde); H-004 a H-007 siguen
    en verde.
  - **C17** KB: R09 (borrador, control, aceptación), las tablas en `04` y `08`, glosario (borrador de
    saldos, control), ficha 5.
  - **C18** cada escenario de la spec `borrador-de-saldos` tiene su test en verde.
- Demo: subir saldos con una diferencia de signo opuesto, ver la comparación y aceptar.

### H-009 · Confirmar

- Change: C-08 5. Reglas: R09, D-068, D-082; elecciones E6, E8, E10, E12, E15. Spec
  `confirmacion-de-saldos`; tareas 3.1 a 3.3.
- Resultado para Juani: con el borrador comparado, el administrador principal confirma: el libro recibe el
  saldo inicial, el edificio queda en "Saldos iniciales confirmados" y el importador se cierra.
- Alcance: migración `0038`, caso de uso `confirmar`, el estado `confirmada` en `complejos`, web (texto,
  paso 7, botón). Exclusiones: ajuste (H-010).
- Dificultad y riesgo: alta / CRITICAL.
- Tienen que pasar:
  - **C01** confirmar un borrador sin diferencias: el libro tiene las obligaciones, intereses importados
    y créditos del borrador (por ejemplo, `1A` agosto $80.000 con interés $4.000 y septiembre $85.000; `2A`
    $50.000 total único con $2.000; `2B` $3.000 a favor), el edificio en `confirmada`, la importación en
    `confirmada` y una auditoría.
  - **C02** la suma importada coincide con el archivo: los totales que devuelve la carga son exactamente
    los del borrador (capital, interés importado, crédito).
  - **C03** confirmar con diferencias aceptadas funciona; la carga es la del borrador, no la del control.
  - **C04** cada obligación y crédito queda ligado a su fila del Excel y al nombre del archivo (origen del
    4c).
  - **C05** después de confirmar, la emisión de noviembre cobra interés desde el 16/10 ($1.280 sobre los
    $80.000 de agosto de `1A`).
  - **C06** interfaz (Playwright): el resumen dice "Saldos iniciales confirmados" y no ofrece importar; con
    la migración pendiente, el paso 7 ofrece "Importar desde Excel" y "Confirmar sin saldos previos".
- Tienen que fallar sin escribir nada:
  - **C07** diferencias sin aceptar → conflicto en `diferencias`; sin borrador vigente (o una importación
    sin hoja `Saldos`, E10) → conflicto.
  - **C08** repetir la confirmación → conflicto en `estado_migracion` y una sola carga en el libro.
  - **C09** con la migración ya cerrada (`confirmada` o `sin_saldos_previos`), confirmar, aceptar o subir
    → conflicto en `estado_migracion`.
  - **C10** permisos y tenant: administrador por edificio, contador, consejo y vecinos 403; otra
    administración 404.
  - **C11** concurrencia contra PostgreSQL real: dos confirmaciones simultáneas → una termina, la otra
    conflicto, una sola carga; confirmar y "sin saldos previos" simultáneos → uno gana y el edificio queda
    en un solo estado coherente.
  - **C12** si la carga del 4c rechaza (por ejemplo, una fecha de migración posterior a hoy), el edificio
    sigue `pendiente`, la importación sigue en `borrador` y no hay auditoría de confirmar.
- Cierre:
  - **C13** la `0038` sube y baja; vocabulario y matriz en verde; H-004 a H-008 siguen en verde.
  - **C14** KB: R09 (confirmar y cerrar), `03`, `07`, ficha 5, `CHANGES.md` cuando cierre el change.
  - **C15** cada escenario de la spec `confirmacion-de-saldos` tiene su test en verde.
- Demo: confirmar en el navegador y ver el libro de `1A` y el resumen.

### H-010 · Ajuste de saldo inicial

- Change: C-08 5. Reglas: R08, R09, R03, R04; D-155; elección E11 (refina D-155: obligación nueva, no
  movimiento). Spec `ajuste-de-saldo-inicial`; tareas 4.1 a 4.3.
- Resultado para Juani: un saldo inicial cargado de menos se corrige sumando deuda nueva con su motivo,
  sin tocar nada de lo cargado.
- Alcance: migración `0039`, caso de uso `ajustar_saldo_inicial`, ruta y pantalla. Exclusiones: saldo de
  más (correcciones del 4b).
- Dificultad y riesgo: media / CRITICAL.
- Tienen que pasar:
  - **C01** el 05/11/2026 el administrador principal ajusta `1A` en $5.000 de ordinaria con el motivo
    "Faltó la expensa extraordinaria de julio": obligación nueva de $5.000, período 01/10/2026, vence
    05/11/2026, su registro con motivo, autor y fecha, y una auditoría; lo anterior de `1A` no cambia.
  - **C02** una unidad migrada sin saldo (sin cuenta) recibe el ajuste: se crea su cuenta.
  - **C03** una unidad con $3.000 a favor ajustada en $2.000 queda con $1.000 a favor (R04).
  - **C04** el interés del ajuste corre desde el 06/11: al 3% proporcional, la emisión de diciembre
    (corte 30/11) cobra 25 días, $125,00; nunca días anteriores al ajuste.
  - **C05** con "mes entero" el ajuste cobra noviembre entero ($150,00 sobre $5.000).
  - **C06** el ajuste cuenta en la situación de cobranza como una liquidación cuando vence.
  - **C07** replay: el mismo `operacion_id` con los mismos datos devuelve el mismo ajuste sin escribir.
  - **C08** interfaz (Playwright): desde la unidad de un edificio confirmado, ajustar con motivo muestra la
    deuda nueva; con la migración pendiente la acción no aparece.
- Tienen que fallar sin escribir nada:
  - **C09** edificio `pendiente` o `sin_saldos_previos` → conflicto en `estado_migracion`.
  - **C10** motivo vacío, en blanco o de 501 caracteres → `motivo`; importe 0, negativo o con 3 decimales
    → `importe`; componente `interes` o desconocido → `componente`.
  - **C11** el mismo `operacion_id` con otro importe → conflicto en `operacion_id`.
  - **C12** permisos y tenant: administrador por edificio, contador, consejo y vecinos 403; unidad de otro
    edificio o de otra administración 404.
  - **C13** `ajuste_de_saldo_inicial`: `UPDATE`/`DELETE` como app `42501`, `TRUNCATE` como arranque
    `P0001`, otra administración no la ve, una FK frena el ajuste ligado a la obligación de otra cuenta, el
    CHECK frena un motivo en blanco.
- Cierre:
  - **C14** la `0039` sube y baja en el ciclo de devolución, la tabla en el ensayo de roles y en los tests
    que bajan migraciones (barrido local); H-004 a H-009 siguen en verde.
  - **C15** KB: R09 (ajuste), `04`, `08`, `03`, glosario (ajuste de saldo inicial), decisión nueva que
    registra E11 sobre D-155, ficha 5.
  - **C16** cada escenario de la spec `ajuste-de-saldo-inicial` tiene su test en verde.
- Demo: ajustar `1A` en el navegador y emitir diciembre para ver el interés de $125,00.

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
- Evidencia: aceptación del SHA aprobado, suite completa (CI o Juani), pendientes:
- Demo y aprobación de Juani (fecha, o motivo del rechazo o la postergación):
