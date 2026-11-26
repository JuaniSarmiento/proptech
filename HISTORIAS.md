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
| H-007 | C-08 5, parte 1 | Un edificio carga su padrón desde la plantilla de Excel, todo o nada, con un informe por fila | Alta / CRITICAL | Terminada |
| H-008 | C-08 5, parte 2 | Los saldos previos quedan en un borrador comparado unidad por unidad, con las diferencias aceptadas | Alta / CRITICAL | Terminada |
| H-009 | C-08 5, parte 3 | Confirmar carga el saldo inicial en el libro, cierra la migración y el importador | Alta / CRITICAL | Terminada |
| H-010 | C-08 5, parte 4 | Un saldo inicial cargado de menos se corrige con un ajuste con motivo | Media / CRITICAL | Terminada |
| H-011 | C-10 7, parte 1 | El administrador ve lo que paga cada unidad, sin efectos, igual al centavo a lo que se emite | Alta / CRITICAL | Terminada |
| H-012 | C-10 7, parte 2 | Los controles de R34 en la preliquidación, cada uno con su nivel, sin escribir nada | Media / CRITICAL | Terminada |
| H-013 | C-10 7, parte 3 | Emitir exactamente lo revisado, con las alertas aceptadas y todo lo usado guardado | Alta / CRITICAL | Terminada |
| H-014 | C-10 7, parte 4 | Distribuir, anular con sus límites (P26, D8) y el cargo cobrado de menos | Alta / CRITICAL | Terminada |
| H-016 | C-10 7, parte 5a (D-158) | Una tarea del worker con efecto se corta en la base y nunca confirma después de agotada | Media / HIGH | Terminada |
| H-015 | C-10 7, parte 5 | El PDF de cada unidad con links firmados que vencen | Alta / CRITICAL | Terminada |
| H-017 | C-10 7, parte 6 | Las pantallas de la liquidación se encuentran y se usan sin escribir URLs | Baja / MEDIUM | Terminada |
| H-018 | C-11 8, parte 1 | El vecino informa su pago con el comprobante, sin cambiar la deuda, con número único | Alta / CRITICAL | Terminada |
| H-019 | C-11 8, parte 2 | La IA propone los datos del comprobante y nunca decide ni frena | Media / CRITICAL | Terminada |
| H-020 | C-11 8, parte 3 | Confirmar imputa con la fecha de la transferencia; rechazar no toca el libro | Alta / CRITICAL | Terminada |
| H-021 | C-11 8, parte 4 | Un pago confirmado tarde devuelve exacto el interés que se cobró de más | Alta / CRITICAL | Terminada |
| H-022 | C-11 8, parte 5 | Revertir un pago devuelve la deuda y el interés como si nunca hubiera entrado | Alta / CRITICAL | Terminada |
| H-023 | C-11 8, parte 6 | Reimputar un pago a la unidad correcta en una sola operación | Alta / CRITICAL | Terminada |
| H-024 | C-11 8, parte 7 | El comprobante sólo baja con link firmado y la emisión avisa los pagos sin confirmar | Media / CRITICAL | Terminada |
| H-025 | C-11 8, parte 8 | El vecino informa y sigue sus pagos, y el administrador los maneja desde su bandeja | Media / CRITICAL | Terminada |
| H-026 | C-11 8, parte 9 | Los hallazgos de la demo del 8: menú del vecino, montos naturales, unidad vigente y el administrador informa | Media / MEDIUM | Terminada |
| H-027 | C-14 10a, parte 1 | La lectura de la morosidad por unidad | Media / HIGH | Terminada |
| H-028 | C-14 10a, parte 2 | El Excel de la morosidad | Baja / HIGH | Terminada |
| H-029 | C-14 10a, parte 3 | La pantalla de la morosidad | Baja / HIGH | Terminada |
| H-030 | C-07d 4d, parte 1 | Registrar un cambio de titular con las opciones por defecto, auditado y con aviso de deuda | Media / CRITICAL (L) | Lista |
| H-031 | C-07d 4d, parte 2 | La deuda previa pasa a nombre del vendedor y la unidad queda en cero por ese concepto | Alta / CRITICAL (L) | Lista |
| H-032 | C-07d 4d, parte 3 | La expensa del mes del cambio se prorratea por días entre vendedor y comprador | Alta / CRITICAL (L) | Lista |
| H-033 | C-07d 4d, parte 4 | La cuenta del vendedor: ver su saldo y registrar su cobro | Media / CRITICAL (L) | En proceso |
| H-034 | C-07d 4d, parte 5 | Las pantallas del cambio de titular y de la cuenta del vendedor | Media / HIGH (M) | Pendiente |

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

- Ninguno: el 7 quedó partido en H-011 a H-015 (15/11/2026, D-157).

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

Propuesta, diseño, specs y tareas en `openspec/changes/archive/2026-11-12-importacion-desde-excel/`. **Firma CRITICAL por
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
    un administrador por edificio de **otro** edificio recibe 404 (D7 del 2a: el alcance va antes que el permiso; corregido por el orquestador al escribir la aceptación); la administración B sobre un edificio
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
- Aceptación: **congelada en `d183ff611d87b69f061f8a0947ffd52ea92973d1`** (firma por adelantado de Juani, revisión técnica del orquestador): 87 tests de backend y 4 en navegador (Playwright), 91 rojos por aserción sobre `15f30bd`, 0 errores; cierre, KB y cobertura en `aceptar.py`. Contrato en `aceptacion/H-007/CONTRATO.md`. **Recongelada en `4c3525e1288837f81e87bb07ea04722956f60e59`** (11/11/2026, por el orquestador): el test de navegador del aviso 403 buscaba `getByRole("alert")` sin acotar y chocaba con el anunciador de rutas de Next (`role="alert"`); ahora se acota por su texto. Lo encontró la tanda 3 de H-007. Ningún otro test cambió.
- Construcción (Sonnet, tres tandas verificadas): t1 módulo `importacion`, lector de la plantilla (nunca
  `float`, coma decimal, fórmulas por su valor en caché, D1 y D2 del 6 cerrados) y validación del padrón
  (252 tests, 20 mutantes); t2 `0036_importacion` y el caso de uso `importar` (36 tests de integración, 9
  mutantes, barrido de migraciones 1.330 en verde); t3 la ruta, la plantilla descargable y la pantalla
  "Importar desde Excel". Decisiones del constructor aceptadas: el mismo email con otro nombre en el
  archivo es la misma persona, con advertencia; la ruta de la plantilla exige el permiso de importar.
  Desvío declarado: los tests de la web se escribieron junto al código (los cubren los mutantes y el rojo
  de los e2e). **La skill impeccable no está instalada**: la pantalla siguió los patrones del 3b y el 3c.
- Evidencia (11/11/2026): `python3 aceptacion/H-007/aceptar.py --codigo 12add68 --sin-regresion` desde
  `4c3525e`: **87/87 de backend y 4/4 en navegador**, C01 a C17 y C20 PASA; C18 (regresión H-004 a
  H-006 y barrido, 1.352) PASA en la corrida completa del constructor sobre `1258ca3`; C19 PASA sobre
  `eb2db50`.
- Demo (12/11/2026, API y PostgreSQL reales, clon en `2c70c4d`): archivo con 3 errores, 422 con hoja, fila, columna y motivo y nada escrito; padrón válido, 12 unidades y 10 propietarios sin invitación; el mismo archivo otra vez, 409 en `archivo`. **Terminada por Juani el 12/11/2026** ("sip").

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
- Aceptación: **congelada en `f214893eb656d466043716aff3a085d9e0a482ec`** (firma por adelantado de Juani, revisión técnica del orquestador): 58 tests de backend y 4 en navegador, 62 rojos por aserción sobre `ca57c88`, 0 errores; regresión H-004 a H-007, KB y cobertura en `aceptar.py`. Contrato en `aceptacion/H-008/CONTRATO.md`. Decisión del orquestador: aceptar dos veces da 409 `aceptacion`. **Recongelada en `4c3525e1288837f81e87bb07ea04722956f60e59`** (11/11/2026, por el orquestador): el test de navegador del aviso 403 buscaba `getByRole("alert")` sin acotar y chocaba con el anunciador de rutas de Next (`role="alert"`); ahora se acota por su texto. Lo encontró la tanda 3 de H-007. Ningún otro test cambió.
- Construcción (Sonnet, dos tandas verificadas): t1 validación de `Saldos` y `Control`,
  `0037_borrador_de_saldos`, borrador, comparación y aceptar diferencias con candado (más de 40
  mutantes, barrido 2.843 en verde); t2 rutas y pantalla de comparación, más el mutante "el borrador
  escribe en el libro" (rojo por aserción en sus tres formas) y un test de totales distintos. Arregló un
  test de aislamiento que H-007 había dejado rojo (la ruta multipart). Suposiciones del constructor
  aceptadas por el orquestador: leer la comparación exige el permiso de importar; una importación
  inexistente da 409; el administrador por edificio ve la comparación pero no acepta. La pantalla no pasó
  por impeccable (no instalada).
- Evidencia (11/11/2026): `python3 aceptacion/H-008/aceptar.py --codigo 99eb6be` desde `4c3525e`:
  **58/58 de backend y 4/4 en navegador**, C01 a C18 PASA, con la regresión H-004 a H-007, el barrido de
  migraciones y la KB.
- Demo (12/11/2026, API y PostgreSQL reales, clon en `2c70c4d`): dos diferencias de signo opuesto con totales iguales ($320.000), la comparación las muestra; el contador recibe 403; el administrador principal acepta con su registro y su auditoría; el libro sigue vacío. **Terminada por Juani el 12/11/2026** ("sip").

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
- Aceptación: **congelada en `4c783e7ba04d394a2ea377dbec3abe36fb027148`** (firma por adelantado de Juani, revisión técnica del orquestador): 32 tests de backend y 5 en navegador, 37 rojos por aserción sobre `8c74866`, 0 errores; regresión H-004 a H-008, KB y cobertura en `aceptar.py`. Contrato en `aceptacion/H-009/CONTRATO.md`. **Recongelada en `4c3525e1288837f81e87bb07ea04722956f60e59`** (11/11/2026, por el orquestador): el test de navegador del aviso 403 buscaba `getByRole("alert")` sin acotar y chocaba con el anunciador de rutas de Next (`role="alert"`); ahora se acota por su texto. Lo encontró la tanda 3 de H-007. Ningún otro test cambió.
- Construcción (Sonnet, una tanda verificada): `0038_confirmar_saldos`, el caso de uso `confirmar` en una
  transacción con candado, la ruta y la web (botón "Confirmar saldos", paso 7 "Cargar los saldos previos" con
  los dos caminos). Mutantes: murieron nueve; "sin candado del complejo" sobrevive por dos defensas más
  (cubiertas con dos tests de dos conexiones), anotado como deuda en la ficha 5. Supuestos aceptados por el
  orquestador: el botón se ve deshabilitado con diferencias sin aceptar; `confirmada_en` no se guarda (se
  devuelve el reloj). La pantalla no pasó por impeccable (no instalada).
- Evidencia (12/11/2026): `python3 aceptacion/H-009/aceptar.py --codigo f774ce4` desde `4c3525e`: **32/32 de
  backend y 5/5 en navegador**, C01 a C15 PASA, con la regresión H-004 a H-008, el barrido de migraciones y
  la KB. 0 rojos.

- Demo (12/11/2026, API y PostgreSQL reales en `b1b8959`, y la web en Chrome con la API falsa): confirmar con
  diferencias sin aceptar da 409, el contador 403; aceptadas, confirma, el edificio queda en "Saldos iniciales
  confirmados" y el libro recibe capital, interés y crédito; confirmar o subir otra vez da 409. Pedido de Juani en
  la demo: un botón "Importar desde Excel" en el padrón con la migración pendiente (`2132a0d`, `ac52b03`).
  **Terminada por Juani el 12/11/2026.**

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
- Aceptación: **congelada en `8c67e94a93acb71eee37353f8e248ac0704d4bf4`** (firma por adelantado de Juani, revisión técnica del orquestador): 56 tests de backend y 4 en navegador, 60 rojos por aserción sobre `a8a40f0`, 0 errores; regresión H-004 a H-009, KB (incluida una D posterior a D-155 que registre E11) y cobertura en `aceptar.py`. Contrato en `aceptacion/H-010/CONTRATO.md`. **Recongelada en `4c3525e1288837f81e87bb07ea04722956f60e59`** (11/11/2026, por el orquestador): el test de navegador del aviso 403 buscaba `getByRole("alert")` sin acotar y chocaba con el anunciador de rutas de Next (`role="alert"`); ahora se acota por su texto. Lo encontró la tanda 3 de H-007. Ningún otro test cambió.

## Liquidación y emisión (7, C-10)

Propuesta y diseño en `openspec/changes/archive/2026-11-16-liquidacion-y-emision/`. Acuerdo previo D-157 (Juani, 15/11/2026):
D8 retenido, P26 no, P38 fecha de la transferencia, P39 no, P27 y P28 al 8, R40 adentro, doble vencimiento y
bloque negativo frenan con un control duro. **Firma CRITICAL por adelantado de Juani** (15/11/2026) en
`proposal.md`: aprueba E1 a E16 en la recomendación del orquestador; lo que no le cierre en la demo vuelve a
En proceso (D-094, D-111). Rama `change/liquidacion-y-emision`; sin rompedor (D-152); CI una vez al cerrar (D-154).
Orden: H-011 → H-012 → H-013 → H-014; H-015 espera la normativa de Mendoza (D-060) y F2c (C-25). **Juani levantó el
límite de dos historias en Lista para todo el 7** (15/11/2026: "sin pasar por mí, terminalo"): las
historias se construyen una detrás de otra y las demos se hacen juntas al final. Los
criterios los escribe el orquestador bajo esa firma, historia por historia.

**Cierre del change (15/11/2026)**: regresión completa una sola vez desde la aceptación de H-015 sobre
`c448953`: estructurales, aceptaciones de H-004 a H-014 y H-016 desde sus SHA y barrido de migraciones en
verde. CI del PR #22: la primera corrida (run 43790658588) dio 3 rojos de 3.053 en `backend` (un test de
acciones por perfil viejo, una fecha fija en `test_umbral_api`, el margen del worker de H-016 por encima del
`job_timeout`; L-090), arreglados en `62aab4f`; la segunda (run 43792064854) dio los seis jobs en verde.
Quedan las demos de H-011 a H-016 con Juani, archivar y mergear.

**Base de los ejemplos** (datos inventados): edificio "Torre Ficticia", sin saldos previos confirmado,
configuración vigente desde el 01/10/2026 con fondo de reserva 5%, vencimiento día 10, único, 3% mensual
proporcional, gracia 0. Unidades y coeficientes: `1A` 0,30, `1B` 0,30, `2A` 0,25, `2B` 0,15. Grupos:
"Generales" (las cuatro) y "Ascensor" (`2A` y `2B`, renormalizado: 0,625 y 0,375). Período noviembre de
2026 (`2026-11`). Gastos aprobados con período de imputación `2026-11`: Limpieza ordinario Generales
$100.000,00, Abono del ascensor ordinario Ascensor $40.000,00, Pintura extraordinario Generales
$50.000,00; una nota de crédito de $10.000,00 sobre Limpieza cargada en `2026-11`; un cargo particular
aprobado de $5.000,00 a `1B` ("Multa"). Además, que **no** entran: un gasto en `borrador` ($999,00), uno
`sin_ia` ($777,00), uno `en_revision` ($555,00), un gasto aprobado de `2026-10`, uno aprobado de otro
edificio y un cargo particular en `borrador` de $3.000,00 a `2A`.

### H-011 · Preliquidación sin efectos

- Change: C-10 7, parte 1. Reglas: R01, R03, R07, R13, R14, R15, R16, R22, R40; HU-A4; elecciones E1, E2
  (la preliquidación no se guarda), E3, E4, E15 y E16 de `design.md`.
- Resultado para Juani: el administrador abre la preliquidación de un período y ve, unidad por unidad, lo
  que va a pagar (ordinaria por grupo, fondo, extraordinaria, cargos particulares e interés) y los gastos
  por bloque y categoría; nada de eso escribe en la base, y lo que muestra es lo mismo que después se
  emite.
- Alcance: módulo `liquidacion` (dominio puro del reparto, el fondo y la huella), la lectura de interés
  sin candado en `cuenta_corriente.aplicacion` con la misma función que la emisión, la ruta
  `GET /api/complejos/{id}/periodos/{AAAA-MM-01}/preliquidacion` (el período como fecha, igual que
  las rutas de gastos del 6), el índice de DBA-2 y la pantalla
  `edificios/[id]/liquidaciones/[AAAA-MM]`. Exclusiones: controles (H-012), emitir (H-013), distribuir y
  anular (H-014), PDF (H-015), pantallas de gastos (6c).
- Dificultad y riesgo: alta / CRITICAL.
- Tienen que pasar:
  - **C01** la base: `1A` ordinaria $27.000,00, fondo $1.350,00, extraordinaria $15.000,00, total
    $43.350,00; `1B` $27.000,00, $1.350,00, $15.000,00, cargo "Multa" $5.000,00, total $48.350,00; `2A`
    $47.500,00 ($22.500,00 de Generales y $25.000,00 de Ascensor), $2.375,00, $12.500,00, total
    $62.375,00; `2B` $28.500,00 ($13.500,00 y $15.000,00), $1.425,00, $7.500,00, total $37.425,00.
  - **C02** los totales: gastos $190.000,00 menos notas de crédito $10.000,00 más fondo $6.500,00 da lo
    prorrateado, $186.500,00; más cargos $5.000,00 e intereses $0,00 da el total, $191.500,00, igual a la
    suma de las unidades.
  - **C03** mayor resto: un único gasto ordinario Generales de $333,33 (fondo 0%) da `1A` $100,00, `1B`
    $100,00, `2A` $83,33, `2B` $50,00 (el empate de `1A` y `1B` se resuelve por orden natural).
  - **C04** grupo parcial: el abono del ascensor no toca a `1A` ni a `1B`; un período con sólo ese gasto
    deja a `1A` y `1B` en $0,00 con `sin_obligacion: true` y a las otras dos con `false`.
  - **C05** grupos por superficie y en partes iguales reparten según su método y suman exacto.
  - **C06** fondo: sobre la ordinaria prorrateada, sin cargos ni intereses (la multa de `1B` no sube su
    fondo); con 0% el fondo es $0,00 en cada unidad y la pantalla no muestra la fila.
  - **C07** categorías: dentro de cada bloque, los subtotales por categoría (neto de notas de crédito:
    Limpieza $90.000,00) suman el bloque, cada uno con su porcentaje y el nombre vigente.
  - **C08** interés: con una obligación de septiembre de $100.000,00 de `1A` vencida el 10/09 e impaga, la
    preliquidación de octubre muestra $2.000,00 de interés en `1A`, y en cada caso de esta aceptación el
    interés por unidad es igual, al centavo, al que registra `registrar_emision` del mismo período justo
    después.
  - **C09** la huella: 64 hexadecimales; pedirla dos veces sin cambios da la misma; aprobar un gasto,
    cargar una nota de crédito o cambiar el fondo la cambia.
  - **C10** orden (R40): el primer período del edificio se preliquida; con octubre emitido, noviembre sí y
    diciembre no (409 `periodo_anterior_sin_emitir`); un período ya emitido sin anular da 409
    `periodo_emitido`; con octubre anulado, octubre se vuelve a preliquidar.
  - **C11** permisos: super admin, administrador principal y administrador del edificio, 200; contador,
    consejo y auxiliar, 403; administrador de otro edificio u otra administración, 404; sin sesión, 401.
  - **C12** pantalla en navegador real: la tabla por unidad con los importes de C01 con separador de miles
    (`43.350,00`), los bloques por categoría y los totales; a 320 px y 1280 px, con teclado y sin
    errores de axe.
  - **C13** regresión: las aceptaciones de H-004 a H-010 desde sus SHA, los tests estructurales del repo,
    el barrido de migraciones y el ensayo de roles siguen en verde.
  - **C14** la base de conocimiento: R40 vigente (D-157), R01, R13 y R15 dicen dónde vive el reparto
    (`liquidacion`), `08` nombra el módulo `liquidacion`, el glosario define preliquidación y huella, y la
    ficha 7 registra H-011.
  - **C15** cada escenario de la spec `preliquidacion` tiene un test que corrió y pasó.
- Tienen que fallar (y la aceptación lo prueba):
  - **N01** la preliquidación escribe algo: el conteo de filas de **todas** las tablas del esquema es el
    mismo antes y después de pedirla (también `auditoria`).
  - **N02** entra un gasto que no es aprobado del período y del edificio, o un cargo en borrador (la base
    de los ejemplos).
  - **N03** un período mal escrito (`2026-13-01`, `2026-11-05`, `noviembre`) da 422, no 500.
  - **N04** la suma de las unidades se aparta un centavo del total (cada caso de C01 a C08 lo verifica).
- Constructor: Claude Sonnet (`rein-constructor`), elegido por Juani el 15/11/2026.
- Aceptación aprobada: `dd9e1fb` (por el orquestador bajo la firma por adelantado de Juani del
  15/11/2026). Comando: `python3 aceptacion/H-011/aceptar.py`. Esperados: 41 de backend y 7 en navegador;
  antes de construir, 48 rojos, todos por aserción (ruta inexistente, índice faltante, KB).
  **Vuelta 2** (`72cd09e`, 15/11/2026): dos locators del e2e estaban mal escritos (la región "Ordinaria"
  también tomaba "Extraordinaria" y el `role="alert"` chocaba con el anunciador de rutas de Next); se
  corrigieron con `exact: true` y un filtro por texto, sin cambiar lo que se prueba. El contrato suma dos 409
  que el constructor necesitó (configuración sin definir, grupo sin base de reparto). Lección L-085.
- Construcción (Sonnet, una tanda): `039cb96` dominio puro (reparto, fondo, huella), `662bc9e` ruta, interés
  a cobrar sin candados (`calcular_intereses_del_corte`, extraído de `_registrar_intereses` para que la
  emisión y la preliquidación usen la misma función) y orden de períodos, `934fceb` barridos de rutas y
  test de la `0040`, `b0ab175` pantalla y API falsa, `b8d6bd9` KB. Ruff, mypy entero, lint, typecheck y
  vitest limpios según el constructor. La pantalla no pasó por impeccable (no instalada); `por_grupo`
  viaja en la API pero la pantalla no lo dibuja.
- Evidencia (15/11/2026): `python3 aceptacion/H-011/aceptar.py --sin-regresion` desde `72cd09e` sobre el
  código `9b92893`: **41/41 de backend y 7/7 en navegador**, C01 a C12, N01 a N04, C14 y C15 PASA, 0 rojos.
  C13 queda para el cierre del change (regresión de H-004 a H-010 y barrido de migraciones, por decisión
  de Juani del 15/11: la regresión larga corre una vez al cerrar).
- Demo y aprobación de Juani: 16/11/2026, recorrida por el orquestador desde el usuario con la base, la API,
  el worker y la web reales en Chrome. **Terminada por Juani el 16/11/2026** ("paso las 7 a terminada").

### H-012 · Controles antes de emitir

- Change: C-10 7, parte 2. Reglas: R01, R09, R24, R34, D-075, D-141, D-157; elección E6 de `design.md`.
- Resultado para Juani: la preliquidación lista los problemas antes de emitir, cada uno con su nivel
  (duro, bloqueante o advertencia), qué pasa y dónde; nada se escribe por mostrarlos.
- Alcance: la lista `controles` de la preliquidación (cada uno con `codigo`, `nivel`, `mensaje` y
  `detalle`) y su bloque en la pantalla. Exclusiones: aceptar alertas y frenar la emisión (H-013); los
  controles de pagos, extracto y contactos (8, 9 y 13).
- Dificultad y riesgo: media / CRITICAL.
- Tienen que pasar:
  - **C01** `saldos_iniciales_sin_validar` (duro) con la migración `pendiente`; no aparece con
    `confirmada` ni con `sin_saldos_previos`.
  - **C02** `coeficientes_fuera_de_tolerancia` (duro): Generales que suma 0,9998 lo dispara nombrando el
    grupo, la suma y la diferencia; un grupo con coeficientes propios que suma 0,8 lo dispara nombrando
    ese grupo.
  - **C03** `bloque_negativo` (duro): con $50.000,00 de gastos ordinarios de Generales en noviembre, una nota
    de crédito de noviembre de $60.000,00 sobre una factura de octubre de $80.000,00 deja ese bloque en
    −$10.000,00; el control nombra el grupo y el bloque, y la
    preliquidación responde 200 (no 500).
  - **C04** `doble_vencimiento_sin_regla` (duro) con la configuración en "doble".
  - **C05** `gastos_en_revision` (bloqueante) con la cantidad y los ids; `gastos_sin_ia` (advertencia)
    con el texto "hay N facturas sin cargar" y N correcto. Ninguno de los dos entra en el cálculo.
  - **C06** `gasto_mensual_obligatorio_faltante` (advertencia) nombra la categoría; desaparece cuando se
    aprueba un gasto de esa categoría en el período.
  - **C07** orden fijo (duros, después bloqueantes, después advertencias) y la huella cambia cuando cambia
    el conjunto de controles.
  - **C08** pantalla en navegador real: cada control con su nivel en texto (no sólo color), los duros
    dicen "no se puede aceptar"; sin errores de axe, a 320 px y con teclado.
  - **C09** regresión: H-004 a H-011 desde sus SHA y los estructurales en verde.
  - **C10** la KB: R34 con los controles del 7 y los dos nuevos (bloque negativo, doble vencimiento), y la
    ficha 7 con H-012.
- Tienen que fallar:
  - **N01** un padrón que suma 0,9999 dispara un duro (está dentro de la tolerancia: no aparece).
  - **N02** un gasto en revisión o sin IA de **otro** edificio dispara un control de este.
  - **N03** mostrar los controles escribe algo (el conteo de todas las tablas, con todos los controles
    activos a la vez).
  - **N04** existe un control `factura_duplicada` o `ingresos_mayores_que_los_gastos` (D-157); y una
    segunda factura con la misma clave entra en la base (la rechaza `uq_gasto_factura`).
- Constructor: Claude Sonnet (`rein-constructor`), el mismo que eligió Juani para el 7.
- Aceptación aprobada: `478705f` (por el orquestador bajo la firma por adelantado de Juani). Comando:
  `python3 aceptacion/H-012/aceptar.py --sin-regresion` por historia (la regresión, C09, al cierre).
  Esperados: 18 de backend y 4 en navegador; antes de construir, 21 rojos por aserción y un verde que ya
  existía (`test_n04_la_factura_duplicada_la_rechaza_la_base`, en `NACEN_VERDES`).
- Construcción (Sonnet, una tanda): `4b102ac` los siete controles en el dominio (`liquidacion/dominio/
  controles.py`, puro), `a6248af` las lecturas por la `aplicacion` de cada dueño (`gastos_por_resolver_del_periodo`
  nueva en gastos), `5ab87b6` la región "Controles antes de emitir" y el escenario 1201, `2621c51` KB. La
  pantalla no pasó por impeccable. `gastos_sin_ia` usa el singular con N = 1.
- Evidencia (15/11/2026): `python3 aceptacion/H-012/aceptar.py --codigo 2621c51 --sin-regresion` desde
  `478705f`: **18/18 de backend y 4/4 en navegador**, C01 a C08, N01 a N04, C10 y SPEC PASA, 0 rojos. C09
  (regresión) queda para el cierre del change.
- Demo y aprobación de Juani: 16/11/2026, recorrida por el orquestador desde el usuario con la base, la API,
  el worker y la web reales en Chrome. **Terminada por Juani el 16/11/2026** ("paso las 7 a terminada").

### H-013 · Emitir lo revisado

- Change: C-10 7, parte 3. Reglas: R03, R06, R13, R15, R16, R17, R34, P36, D-069, D-100, D-141, D-157;
  elecciones E2, E3, E5, E7, E8, E15 de `design.md`.
- Resultado para Juani: el administrador emite la preliquidación que revisó: cada unidad queda con su
  obligación en el libro, todo lo usado queda guardado y nada de lo que cambie después lo altera.
- Alcance: `POST /api/complejos/{id}/periodos/{AAAA-MM-01}/emision` con `emision_id`, `huella`,
  `alertas_aceptadas` y, opcional, el vencimiento corrido con su motivo; las tablas de E2 (migración
  nueva); el candado de E5 compartido con aprobar un gasto; el adaptador real de `es_periodo_emitido`; la
  auditoría; el botón "Emitir" con su confirmación en la pantalla. Exclusiones: distribuir y anular
  (H-014), PDF (H-015).
- Dificultad y riesgo: alta / CRITICAL.
- Tienen que pasar:
  - **C01** emitir la base: 201; `1A`, `1B`, `2A` y `2B` con una obligación cada una, vencimiento
    10/11/2026, y `1B` con ordinaria $32.000,00 (prorrateada más la multa), fondo $1.350,00 y
    extraordinaria $15.000,00.
  - **C02** lo emitido es lo preliquidado: obligaciones e intereses iguales, al centavo, a la
    preliquidación con la misma huella (también con la deuda de septiembre de H-011.C08).
  - **C03** queda guardado: la liquidación con su huella, versión de configuración, porcentaje y
    vencimiento; las líneas por unidad con el nombre de la categoría; renombrar la categoría o cambiar el
    fondo después no cambia nada de lo emitido.
  - **C04** la composición de cada grupo con el coeficiente efectivo usado (Ascensor: 0,625 y 0,375).
  - **C05** la foto del saldo anterior: una unidad con deuda de octubre la ve guardada, y cobrarle después
    no cambia la foto.
  - **C06** vencimiento corrido al 12/11/2026 con motivo: las obligaciones vencen ese día; queda la fecha
    original, la nueva, quién, cuándo y el motivo; la configuración del edificio no cambia.
  - **C07** alertas: con `gastos_en_revision` activo, emitir aceptándolo con el administrador principal da
    201 y deja en `alerta_aceptada` el código, quién y cuándo; con una advertencia activa se emite sin
    aceptar nada.
  - **C08** un gasto de noviembre aprobado después de emitir noviembre pasa a diciembre
    (`periodo_de_imputacion`, P36).
  - **C09** idempotencia: repetir el pedido con el mismo `emision_id` y el mismo cuerpo devuelve lo mismo
    sin duplicar nada.
  - **C10** permisos: super admin, principal y administrador del edificio 201; contador, consejo y
    auxiliar 403; otro edificio u otra administración 404; sin sesión 401. Una auditoría por emisión.
  - **C11** pantalla en navegador real: "Emitir" pide confirmación, ofrece aceptar los bloqueantes
    aceptables y no ofrece aceptar un duro; sin errores de axe.
  - **C12** regresión: H-004 a H-012 desde sus SHA, el ensayo de roles con las tablas nuevas, el barrido
    de migraciones y los estructurales.
  - **C13** la KB: R13, R15, R16, R17 y R34 con lo construido, `04` y `08` con las tablas nuevas, HU-A5
    y la ficha 7 con H-013.
- Tienen que fallar:
  - **N01** emitir con una huella vieja (un gasto aprobado en el medio): 409 `preliquidacion_cambio` y
    nada escrito.
  - **N02** emitir con un duro activo, aunque venga en `alertas_aceptadas`: 422 y nada escrito.
  - **N03** aceptar de menos (falta un bloqueante activo) o de más (un código que no está activo): 409 y
    nada escrito.
  - **N04** el administrador del edificio acepta un bloqueante: 403 y nada escrito.
  - **N05** emitir otra vez el mismo período con otro `emision_id`: 409 `periodo_emitido`.
  - **N06** dos emisiones del mismo período en paralelo: una 201, la otra 409, una sola obligación por
    unidad.
  - **N07** aprobar un gasto del período y emitir en paralelo: el gasto nunca queda en un período emitido
    sin estar liquidado (o entra en la liquidación o su período de imputación pasa a diciembre).
  - **N08** vencimiento corrido sin motivo o a una fecha anterior al período: 422.
  - **N09** una unidad con `sin_obligacion` recibe una obligación en $0,00.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `68729fc` (por el orquestador bajo la firma por adelantado de Juani). Contrato en
  `aceptacion/H-013/CONTRATO.md`: la ruta `POST .../periodos/{AAAA-MM-01}/emision`, la lectura
  `GET .../liquidaciones/{id}` con el permiso nuevo `ver_liquidaciones` y la migración `0041`. Comando:
  `python3 aceptacion/H-013/aceptar.py --sin-regresion`. Esperados: 36 de backend y 5 en navegador; antes de
  construir, 41 rojos por aserción.
- **Vuelta 2** (`af84436`, 15/11/2026): la base de ejemplos heredada de H-011 traía un gasto en revisión
  que desde H-012 es un bloqueante (los tests que emiten la base sin aceptar nada no podían pasar junto con
  N03), y el ciclo de la `0041` compartía la base de migraciones de su módulo. Se sacó el gasto de la base y
  el ciclo pasó a `test_h013_migracion.py`; lo que se prueba no cambia. Lección L-086. Los detectó el
  constructor y los pidió corregir sin tocar `aceptacion/`.
- Construcción (Sonnet, una tanda): `f05d22e` dominio puro de emitir, `28a9394` permiso `ver_liquidaciones`,
  `be48ac0` migración `0041` (seis tablas protegidas, D-159), `f218494` emitir y leer, `5fbdc5f` web,
  `0975ca5` KB, `fd17bff` y `95f5379` FKs de las tablas hijas a `complejo`. `aprobar_gasto` toma el candado
  del `complejo` y recibe el `es_periodo_emitido` real desde `proptech_api`. Fuera del contrato: el replay
  responde 200, el mismo `emision_id` con otro cuerpo da 409 `emision_id_repetido`, y si el interés del libro
  difiere del preliquidado vuelve todo con 409 `preliquidacion_cambio`. `emitir_liquidacion` no lleva
  `@accion_sensible` (la aceptación verifica las filas de auditoría). La pantalla no pasó por impeccable.
- Evidencia (15/11/2026): `python3 aceptacion/H-013/aceptar.py --codigo 95f5379 --sin-regresion` desde
  `af84436`: **36/36 de backend y 5/5 en navegador**, C01 a C11, N01 a N09, C13 y SPEC PASA, 0 rojos. C12
  (regresión) queda para el cierre del change.
- Demo y aprobación de Juani: 16/11/2026, recorrida por el orquestador desde el usuario con la base, la API,
  el worker y la web reales en Chrome. **Terminada por Juani el 16/11/2026** ("paso las 7 a terminada").

### H-014 · Distribuir, anular y cargo cobrado de menos

- Change: C-10 7, parte 4. Reglas: R08, R17, P26, P38, P39, D-073, D-074, D-079, D-081, D-123 (D8),
  D-124, D-157; elecciones E9, E10, E11, E14 de `design.md`.
- Resultado para Juani: una liquidación emitida se distribuye y desde ahí no se anula; mientras no esté
  distribuida se puede anular con motivo y la deuda vuelve a como estaba; un cargo cobrado de menos se
  corrige con una deuda nueva con motivo.
- Alcance: el evento `distribuida` (migración), el puerto `registrar_distribucion`, las rutas de
  distribuir, anular y cargo cobrado de menos, la lectura de liquidaciones por rol, D8 en el estado de la
  cuenta y sus pantallas. Exclusiones: distribuir por email (13) o por el portal (11), que sólo llaman al
  puerto.
- Dificultad y riesgo: alta / CRITICAL.
- Tienen que pasar:
  - **C01** distribuir una emitida: queda distribuida con origen `manual`, quién y cuándo, y se audita.
  - **C02** el puerto es idempotente: llamarlo desde `portal` y después desde `email` deja un solo evento,
    con el origen del primero.
  - **C03** anular una emitida con motivo: queda anulada con motivo y responsable; el saldo de cada unidad
    es igual al de antes de emitir; ninguna fila de `movimiento`, `obligacion` ni `imputacion` cambia ni
    se borra.
  - **C04** anular y volver a emitir el período no cobra dos veces ni la expensa ni el interés.
  - **C05** un pago imputado a la emisión anulada vuelve como crédito a favor con su fecha de
    transferencia, y la re-emisión lo imputa sin cobrar interés por los días en que estaba pagado (P38).
  - **C06** D8: un crédito de corrección imputado a una obligación de la emisión anulada queda retenido:
    no figura como crédito a favor ni se imputa en la re-emisión.
  - **C07** cargo cobrado de menos de $1.500,00 sobre la obligación de noviembre de `1A`: obligación nueva
    con su motivo y su vínculo a la de origen, interés desde el día siguiente a su vencimiento, auditado.
  - **C08** permisos: anular, super admin y principal (administrador del edificio 403); distribuir,
    super admin, principal y administrador del edificio; el consejo ve las distribuidas y no ve una
    emitida sin distribuir (P39); el contador ve las dos.
  - **C09** pantalla en navegador real: "Distribuir" y "Anular" con confirmación, el motivo obligatorio y
    el estado de la liquidación en texto; sin errores de axe.
  - **C10** regresión: H-004 a H-013 desde sus SHA, las aceptaciones del 4b y el 4c que tocan el estado de
    la cuenta, el ensayo de roles y el barrido de migraciones.
  - **C11** la KB: R17 con distribuida, P26 y D8; R08 con el cargo cobrado de menos; P26, P38 y P39
    resueltas en `10`; la ficha 7 con H-014.
- Tienen que fallar:
  - **N01** anular una distribuida: 409 y nada escrito.
  - **N02** anular sin motivo o con motivo en blanco: 422.
  - **N03** anular una ya anulada: 409.
  - **N04** anular octubre con noviembre emitido sin anular: 409 (P26).
  - **N05** distribuir una anulada, o distribuir dos veces a mano: 409.
  - **N06** anular y distribuir en paralelo: queda una sola de las dos, nunca las dos.
  - **N07** cargo cobrado de menos con importe 0 o negativo (422), sin motivo (422), o con una obligación
    de origen de otra unidad o de otro edificio (404).
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `280417d`. Contrato en `aceptacion/H-014/CONTRATO.md` (distribuir, anular, el puerto
  `registrar_distribucion`, la lista de liquidaciones por rol, el cargo cobrado de menos y la migración
  `0042`). Comando: `python3 aceptacion/H-014/aceptar.py --sin-regresion`. Esperados: 24 de backend y 4 en
  navegador; antes de construir, 27 rojos por aserción (sobre el código con H-013).
- **Vuelta 2** (`6a7280b`): C04 contaba obligaciones con una ayuda que exige una por unidad, y dos e2e de C09
  leían la última escritura sin esperarla (carrera). Lo que se prueba no cambia. Lecciones L-087 y L-088.
- Construcción (Sonnet, una tanda): `b83ca00` el préstamo de propiedad de D-115.3 (D-161), `ce0bafe` a
  `2ed0a36` la `0042` (`distribuida` con origen, índice único parcial que impide anulada y distribuida a la
  vez, tabla `cargo_cobrado_de_menos`), D8 en una línea del paso 5 de `estado.py`, distribuir, anular, la
  lista y la lectura por rol, el cargo cobrado de menos, los barridos de rutas, la web y la KB. Además el
  orquestador exceptuó el nivel de un control del test de vocabulario (`ea93de2`). `ensayo-roles.sh` queda
  sin correr hasta el CI. La pantalla no pasó por impeccable.
- Evidencia (15/11/2026): `python3 aceptacion/H-014/aceptar.py --codigo 2ed0a36 --sin-regresion` desde
  `6a7280b`: **24/24 de backend y 4/4 en navegador**, C01 a C09, N01 a N07, C11 y SPEC PASA, 0 rojos. C10
  (regresión) queda para el cierre. **Para la demo**: D-161 (préstamo de propiedad) es seguridad de la
  base y lo revisa Juani.
- Demo y aprobación de Juani: 16/11/2026, recorrida por el orquestador desde el usuario con la base, la API,
  el worker y la web reales en Chrome. **Terminada por Juani el 16/11/2026** ("paso las 7 a terminada").

### H-016 · Corte del lado de la base para las tareas del worker (F2c)

- Change: C-10 7 (D-158, F2c del 1c, antes en el C-25). Va antes de H-015.
- Resultado para Juani: una tarea del worker que toca la base (la primera real es el PDF) tiene su propio
  límite de tiempo **en la base**: si la base se traba, la tarea se corta y no confirma nada, ni siquiera
  cuando la base vuelve; un reintento posterior la hace una sola vez.
- Alcance: `proptech_worker/corte.py` con `ejecutar_con_corte` (sesión con `statement_timeout`,
  `lock_timeout` e `idle_in_transaction_session_timeout` locales a la transacción, una cota por tarea y un
  chequeo del plazo antes de confirmar), la tarea de prueba pasando por ahí, sin `COTA_OPERACION_S`.
  Exclusiones: F12b, los logs y F3b (siguen en el C-25).
- Dificultad y riesgo: media / HIGH (el worker va a mover documentos de plata).
- Tienen que pasar:
  - **C01** dentro del efecto, `statement_timeout`, `lock_timeout` e `idle_in_transaction_session_timeout`
    valen la cota de la tarea (500 ms para una cota de 0,5 s), y fuera de la transacción vuelven a su valor.
  - **C02** con la clave tomada por otra transacción sin confirmar, la tarea se corta en menos de 3 s con
    `CorteDeLaBase` (un `ErrorPasajero`) y, liberada la clave, no quedó ninguna fila suya.
  - **C03** un reintento después del corte confirma el efecto una sola vez, y otro más devuelve `False`.
  - **C04** la tarea de prueba usa `ejecutar_con_corte` y `COTA_OPERACION_S` ya no existe.
  - **C05** la KB: la ficha 1f dice que F2c lo cerró H-016 del 7 (D-158) y la ficha 7 registra H-016.
- Tienen que fallar:
  - **N01** un efecto lento (`pg_sleep` del triple de la cota) confirma: tiene que cortarse sin fila.
  - **N02** un efecto que termina en Python después del plazo (sin sentencia lenta) confirma: tiene que
    revertirse sin fila.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `b7b526a`. Comando: `python3 aceptacion/H-016/aceptar.py --sin-navegador`. Esperados: 5
  de backend; antes de construir, 5 rojos por aserción (falta `proptech_worker.corte`) y C05 sin la KB.
- Construcción (Sonnet, una tanda): `62eb6d4` `proptech_worker/corte.py` (`ejecutar_con_corte` con los tres
  timeouts locales por `set_config(..., true)`, el plazo verificado antes de confirmar y `CorteDeLaBase`), la
  tarea de prueba por el corte con `COTA_TAREA_DE_PRUEBA_S`; `test_zz_rompedor_v3_agotada_con_efecto.py` deja
  de ser `xfail` (F2c resuelta); `5644b2f` fichas 1f y 7 y C-25 en `CHANGES.md`.
- Evidencia (15/11/2026): `python3 aceptacion/H-016/aceptar.py --codigo 5644b2f --sin-navegador` desde
  `b7b526a`: **5/5**, C01 a C05, N01 y N02 PASA, 0 rojos.
- Demo y aprobación de Juani: 16/11/2026, recorrida por el orquestador desde el usuario con la base, la API,
  el worker y la web reales en Chrome. **Terminada por Juani el 16/11/2026** ("paso las 7 a terminada").

### H-015 · PDF de la expensa y links firmados

- Change: C-10 7, parte 5. Reglas: R19, D-047 (punto 7), D-060, D-070, D-106; CCyC art. 2067 inc. i
  (archivo de las liquidaciones); elecciones E12 y E13 de `design.md`. **Después de H-016** (F2c, D-158): el worker ya tiene corte del lado de la base.
- Resultado para Juani: cada unidad tiene el PDF de su expensa, generado por el worker aunque Redis falle
  al emitir, guardado sin cambios, y se descarga sólo con un link firmado que vence.
- Alcance: `documento_de_expensa` con su estado, el encolado después del commit, el barrido que reencola,
  la tarea del worker, la plantilla (con impeccable, sobre el modelo de la Ley 941 de CABA sin presentarlo
  como exigencia en Mendoza), el reproceso y los links firmados. Exclusiones: el envío por email (13), el
  portal (11).
- Dificultad y riesgo: alta / CRITICAL.
- Tienen que pasar:
  - **C01** al emitir, un documento por unidad con obligación, en `pendiente`; el worker lo pasa a
    `generado`.
  - **C02** el PDF trae el edificio, la unidad y su código corto (R19), el período, el vencimiento, la
    ordinaria y la extraordinaria por categoría, el fondo, los cargos, el interés, el saldo anterior de la
    foto y el total, iguales a la liquidación.
  - **C03** con Redis caído al emitir, la emisión queda confirmada con los documentos en `pendiente`, y el
    barrido los reencola cuando Redis vuelve.
  - **C04** una generación que falla queda `fallido` con su motivo; reprocesar la deja `generado`.
  - **C05** un link firmado descarga el PDF; vencido, da 410; alterado, 403.
  - **C06** el inquilino recibe la variante sin extraordinaria y el propietario la completa.
  - **C07** un PDF `generado` no cambia: reprocesar o cambiar después la configuración no lo reescribe.
  - **C08** pantalla en navegador real: el estado de cada documento, el reproceso y la descarga.
  - **C09** regresión: H-004 a H-014 y los tests del worker.
  - **C10** la KB: D-060 con lo investigado (decisión nueva), R19 y `08` con los links firmados, y la ficha
    7 con H-015.
- Tienen que fallar:
  - **N01** el PDF tiene una dirección pública o se descarga sin link firmado.
  - **N02** el inquilino obtiene la variante completa cambiando el link o pidiéndola directo.
  - **N03** un documento queda generado dos veces, o con dos versiones distintas, por un reencolado.
  - **N04** un link de otra administración o de otra unidad descarga algo.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `21b1e36`. Contrato en `aceptacion/H-015/CONTRATO.md` (dos variantes por unidad, la
  tarea `generar_pdf_de_expensa` por `ejecutar_con_corte`, el barrido, `generar_documento`, el reproceso, los
  enlaces firmados con `PROPTECH_CLAVE_DE_ENLACES` y la descarga, el código `TF-1B`). D-160 cierra D-060.
  Comando: `python3 aceptacion/H-015/aceptar.py --sin-regresion`. Esperados: 16 de backend y 3 en navegador;
  antes de construir, 19 rojos por aserción (un test que importaba el worker y fallaba por configuración se
  cambió por una lectura del código antes de congelar).
- **Vuelta 2** (`f179066`): un sondeo del e2e leía `.url` sin `?.` y fallaba si todavía no había ninguna
  escritura (mismo patrón que L-087). Lo que se prueba no cambia.
- Construcción (Sonnet, una tanda): `88badfd` WeasyPrint 70.0 y pypdf 7.1.0 (Pango y fuentes en
  `backend/Dockerfile` y en `ci.yml`), `b3b63eb` la `0043` (`documento_de_expensa` con trigger y
  `pdf_de_expensa` de sólo agregar), `0e156d8` dominio, enlaces firmados y `generar_documento`, `5c67005` API,
  tarea `generar_pdf_de_expensa` por `ejecutar_con_corte`, barrido cada 5 minutos, compose y README,
  `737c2b9` web (la descarga pasa por la ruta de Next `/documentos/descarga`, Caddy no publica `/api/*`),
  `b552b50` KB, `9b39986` la API falsa devuelve una escritura vacía en vez de `null`. Decisiones de base en
  D-162 (política del barrido, `REFERENCES` del migrador) y L-089. La pantalla no pasó por impeccable.
- Evidencia (15/11/2026): `python3 aceptacion/H-015/aceptar.py --codigo 9b39986 --sin-regresion` desde
  `f179066`: **16/16 de backend y 3/3 en navegador**, C01 a C08, N01 a N04, C10 y SPEC PASA, 0 rojos. C09
  (regresión) queda para el cierre. **Para la demo**: D-162 es seguridad de la base y lo revisa Juani.
- Deuda que deja (a la ficha 7): `infra/.env.example` sin las líneas de `PROPTECH_CLAVE_DE_ENLACES` (una
  regla de permisos impide editarlo: lo tiene que hacer Juani); el enlace de una liquidación anulada no se
  bloquea y la emisión de un enlace no se audita (al 11, el portal, que es quien los va a pedir).
- Demo y aprobación de Juani: 16/11/2026, recorrida por el orquestador desde el usuario con la base, la API,
  el worker y la web reales en Chrome. **Terminada por Juani el 16/11/2026** ("paso las 7 a terminada").

### H-017 · Pulido de las pantallas de la liquidación

- Change: C-10 7. Origen: los hallazgos de la demo del 16/11/2026 con la base real (Juani eligió hacerlos
  historia antes de archivar). Nivel M: pantallas y una cabecera, sin plata nueva; la base no cambia.
- Resultado para Juani: el administrador llega a la liquidación desde el menú, ve la lista de períodos con su
  estado (también las anuladas) y entra a preparar el próximo; la liquidación emitida muestra lo que paga cada
  unidad; cada PDF baja con un nombre que dice período, unidad y variante; y el cargo cobrado de menos se
  registra desde la pantalla.
- Alcance: el link "Liquidaciones" en el menú del edificio, la página `edificios/[id]/liquidaciones`, la tabla
  por unidad en la emitida (con `obligacion_id` en la lectura de H-013), el `Content-Disposition` de la
  descarga y el diálogo del cargo cobrado de menos. Exclusiones: la skill impeccable (C-26), el portal del
  vecino (11).
- Tienen que pasar:
  - **C01** el menú del edificio tiene "Liquidaciones" y lleva a `edificios/[id]/liquidaciones`, que lista
    cada liquidación con su período en palabras, su estado en texto y su total, con un link al período.
  - **C02** la lista ofrece "Preparar la liquidación de <mes siguiente al último emitido sin anular>" (o del
    mes actual si no hay ninguna), que lleva a la preliquidación de ese período.
  - **C03** la liquidación emitida muestra la tabla de lo que paga cada unidad (lo guardado: ordinaria, fondo,
    extraordinaria, cargos, intereses, saldo anterior y total), y la lectura `GET .../liquidaciones/{id}`
    trae el `obligacion_id` de cada unidad con obligación.
  - **C04** la descarga del PDF trae `Content-Disposition: attachment; filename="expensa-2026-11-1b-completa.pdf"`
    (período, unidad y variante).
  - **C05** en la emitida, cada unidad con obligación tiene "Cargo cobrado de menos" que abre un diálogo con
    importe, concepto y motivo y manda el `POST` de H-014 con su `obligacion_origen_id`.
  - **C06** la lista muestra las anuladas con "Anulada" y sin link a distribuir ni anular.
  - **C07** sin errores de axe y sin scroll horizontal a 320 px en la lista; la ficha 7 registra H-017.
- Tienen que fallar:
  - **N01** el link "Liquidaciones" aparece para quien no tiene `ver_liquidaciones`.
  - **N02** "Cargo cobrado de menos" aparece para quien no tiene `corregir_movimiento`.
  - **N03** el nombre del archivo lleva datos personales (el nombre del propietario) o caracteres fuera de
    `[a-z0-9-.]`.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `22c7364`. Contrato en `aceptacion/H-017/CONTRATO.md`. Comando:
  `python3 aceptacion/H-017/aceptar.py`. Esperados: 5 de backend y 8 en navegador; antes de construir, 13 rojos
  por aserción.
- Construcción (Sonnet): `84c9090` y `1c2a759` (nombre del PDF puro y testeado, `obligacion_id` leído por
  `cuenta_corriente.obligaciones_de_la_emision`, menú por `ver_liquidaciones`, lista, tabla y diálogo del
  cargo, API falsa con acciones por edificio). Sin impeccable.
- Evidencia (16/11/2026): `python3 aceptacion/H-017/aceptar.py --codigo 1c2a759` desde `22c7364`: **5/5 de
  backend y 8/8 en navegador**, C01 a C07, N01 a N03 y KB PASA, 0 rojos.
- Demo y aprobación de Juani: 16/11/2026, recorrida por el orquestador desde el usuario con la base, la API,
  el worker y la web reales en Chrome. **Terminada por Juani el 16/11/2026** ("paso las 7 a terminada").

## Pagos informados (8, C-11)

Propuesta y diseño en `openspec/changes/pagos-informados/` (E1 a E14). Acuerdo previo D-163 y D-164 (Juani,
18/11/2026): P12 frena el despliegue y no la construcción, P40 con el banco, P29 desde el vencimiento
original, R37 con P27 y P28 al 6b, R25 adentro, OpenRouter detrás de un puerto. **Firma CRITICAL por
adelantado de Juani** (18/11/2026) en `proposal.md`: aprueba E1 a E14 en la recomendación del orquestador;
lo que no le cierre en la demo vuelve a En proceso (D-094, D-111). Rama `8-pagos-informados`; sin rompedor
(D-152); CI y regresión una vez al cerrar (D-154). Juani delegó el change entero ("te podes hacer cargo del
change"): como en el 7, las historias se construyen una detrás de otra y las demos se hacen juntas al final.
**Juani levantó el límite de dos historias en Lista para todo el 8** (18/11/2026, con H-018 a H-020 en Lista: "levanta
el limite testeamos todo al final").
Constructor y todo subagente con Claude Sonnet (Juani, 18/11/2026). Orden: H-018 → H-019 → H-020 → H-021 →
H-022 → H-023 → H-024 → H-025.

**Base de los ejemplos** (datos inventados): la "Torre Ficticia" de los ejemplos del 7, con la liquidación de
noviembre de 2026 emitida (vencimiento 10/11/2026; totales `1A` $43.350,00, `1B` $48.350,00, `2A` $62.375,00,
`2B` $37.425,00), 3% mensual proporcional y gracia 0. Personas: "Ana Prueba", propietaria de `1A` y de `2B`;
"Beto Prueba", inquilino de `1B`; un administrador principal. Comprobantes de prueba: imágenes PNG y un PDF
generados en el test, sin datos reales, con banco "Banco Nación" o "Mercado Pago" y números inventados.

### H-018 · Informar un pago

- Change: C-11 8, parte 1. Reglas: R10, R11; D-163 (P40); E1 a E4 de `design.md`.
- Resultado para Juani: un vecino sube el comprobante de su transferencia y lo informa para su unidad (o lo
  reparte entre sus unidades); el pago queda "informado", sin tocar la deuda, y el mismo comprobante no se
  puede informar dos veces.
- Alcance: el módulo `pagos`, la migración de sus tablas (comprobante, pago, partes, eventos, enlace con el
  libro, CBU), `POST .../pagos/lectura` guardando el comprobante con la lectura en `sin_ia` (el adaptador de
  IA es H-019), `POST .../pagos`, la lista del vecino y la del edificio. Exclusiones: confirmar (H-020), la
  IA real (H-019), las pantallas (H-025).
- Dificultad y riesgo: alta / CRITICAL. Nivel L.
- Tienen que pasar:
  - **C01** Ana informa $43.350,00 del 05/11/2026 para `1A` con su comprobante: 201, estado `informado`; la
    deuda de `1A`, su crédito a favor y su `situacion_de_cuenta` son iguales a los de antes.
  - **C02** Ana reparte $80.775,00 en `1A` $43.350,00 y `2B` $37.425,00: el pago tiene dos partes.
  - **C03** el administrador informa por Beto un pago de `1B`: 201, con quién lo informó.
  - **C04** el mismo banco y número, escritos distinto (`Banco Nación` / `banco nacion`, `12-345.678` /
    `12345678`), dan 409 `numero_de_operacion` `repetido`, también para otra unidad; otro banco con el mismo
    número entra.
  - **C05** un pago rechazado libera su número: se puede volver a informar (el rechazo se siembra directo en
    la base, porque rechazar es H-020).
  - **C06** el vecino lista los pagos de sus unidades (Ana ve los de `1A` y `2B`, Beto los de `1B`) con su
    estado; el administrador ve la lista del edificio.
  - **C07** subir un comprobante JPEG, PNG o PDF de hasta 10 MB devuelve `comprobante_id` y `lectura`
    `sin_ia` con la propuesta vacía.
  - **C08** la migración sube sobre una base ya desplegada y baja limpia; las tablas nuevas tienen RLS, están
    protegidas (sólo agregar) y entran en el catálogo, el ensayo de roles y el barrido (L-064, L-089).
  - **C09** la KB: R11 con dónde vive, el modelo de datos y la ficha 8 con H-018.
- Tienen que fallar:
  - **N01** Ana informa para `1B` (no es suya): 404, sin nada creado.
  - **N02** partes que no suman el monto, una unidad repetida, monto cero o negativo, monto con tres
    decimales, fecha futura o de hace más de un año: 422 con su campo, sin nada creado.
  - **N03** un comprobante que no es imagen ni PDF (un ejecutable renombrado `.png`) o de más de 10 MB: 422
    `archivo`, sin nada guardado.
  - **N04** el mismo comprobante usado en dos pagos, o un comprobante de otro edificio u otra
    administración: 422 o 404.
  - **N05** un vecino ve un pago de una unidad ajena o de otra administración, por lista o por id: 404.
  - **N06** alguien sin `informar_pago` ni `confirmar_pago_informado` (el consejo, el contador) informa: 403.
  - **N07** el rol de la aplicación puede hacer `UPDATE` o `DELETE` sobre las tablas nuevas.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `fdd1c4f` (bajo la firma por adelantado del 8). Contrato en `aceptacion/H-018/CONTRATO.md`
  (la dependencia `proptech_api.pagos.hoy`, las dos rutas de escritura y las dos de lectura, el orden de las
  validaciones, la `0044` con seis tablas protegidas y el estado por `evento_de_pago`). Comando:
  `python3 aceptacion/H-018/aceptar.py --sin-regresion`. Esperados: 54 de backend; antes de construir, 54 rojos
  por aserción, 0 por setup.
- **Vuelta 2 de la aceptación** (`221f619`, congelada en `b51aef6`): el constructor frenó por dos defectos de la
  aceptación, no del código: `filas_de` contaba todas las administraciones sobre una base de alcance módulo (32
  falsos rojos) y el runner copiaba una carpeta `e2e` que la historia no tiene. Lo que se prueba no cambia
  (L-092).
- Construcción (Sonnet, una tanda): `df17700` dominio puro (normalización, tipo por los primeros bytes, pedido,
  estado derivado), `b07955b` la `0044` con seis tablas protegidas y el número único por un trigger con candado
  consultivo (D-165), `8da2bab` rutas, `ab8e833` el pedido rechaza campos ajenos (`test_altas_sin_id_del_cliente`),
  `98473de` los ayudantes de rollback con funciones extra de trigger, `c3b9f37` y `f97e1b3` KB (R11, `04`, `08`,
  ficha 8, D-165, L-091). Además del contrato: un vecino ve sólo las partes de sus unidades de un pago
  repartido, y la lista trae `comprobante_id`, `informado_por` e `informado_en`.
- Evidencia (18/11/2026): `python3 aceptacion/H-018/aceptar.py --codigo b51aef6 --sin-regresion` desde `221f619`:
  **54/54**, C01 a C09, N01 a N07, EST y SPEC (9 escenarios) PASA, 0 rojos. El constructor corrió además 70
  unitarios del dominio, `test_pagos_base.py` (6, con la carrera de dos números iguales), el barrido de los 59
  archivos que bajan migraciones y ruff, format y mypy enteros, en verde. La regresión de H-004 a H-017 queda
  para el cierre (D-154).
- Demo y aprobación de Juani: 18/11/2026, dos recorridas del orquestador con la base, la API, el worker y la web
  reales en Chrome (la segunda, con los arreglos de H-026); regresión del cierre H-004 a H-024 y barrido en verde, CI
  del PR #27 verde en `de70b95`. **Terminada por Juani el 18/11/2026** ("si tengo ganas de, primero cerra este 8").

### H-019 · Lectura del comprobante con IA

- Change: C-11 8, parte 2. Reglas: R11; D-164; E5.
- Resultado para Juani: al subir el comprobante, el vecino ve banco, número, fecha, monto y CBU precargados
  para revisar; si la IA falla, carga a mano, y nada que diga la imagen puede confirmar un pago.
- Alcance: el puerto de lectura, el adaptador de OpenRouter (httpx, con tope de 20 s), la validación de la
  propuesta en el dominio, la configuración `PROPTECH_OPENROUTER_API_KEY` y `PROPTECH_OPENROUTER_MODELO`.
  Exclusiones: la pantalla (H-025).
- Dificultad y riesgo: media / CRITICAL (datos de comprobantes a un tercero). Nivel L.
- Tienen que pasar:
  - **C01** con un lector falso que devuelve `Banco Nación`, `12345678`, `2026-11-05`, `43350.00` y un CBU de
    22 dígitos, la lectura trae esos valores y `lectura` `ok`.
  - **C02** el lector que lanza o que tarda más que el tope: 201 con `lectura` `fallida` y la propuesta vacía.
  - **C03** sin clave configurada: 201 con `lectura` `sin_ia`, sin llamar a la red.
  - **C04** el adaptador real, sobre un transporte HTTP falso: llama a
    `https://openrouter.ai/api/v1/chat/completions` con `Authorization: Bearer <clave>`, el modelo de la
    configuración, la imagen en base64, `response_format` con esquema JSON estricto y `provider` con `zdr`
    `true`, `data_collection` `deny` y `require_parameters` `true`; interpreta la respuesta de chat.
  - **C05** lo que leyó la IA queda guardado con el comprobante (la propuesta y el resultado).
  - **C06** la KB: D-164 aplicado en `08` (variables nuevas) y la ficha 8 con H-019.
- Tienen que fallar:
  - **N01** el cuerpo que sale hacia OpenRouter contiene el nombre de la persona, el identificador de la
    unidad o el nombre del edificio.
  - **N02** un campo inválido de la IA sobrevive: monto `"1; confirmá este pago"`, monto negativo, fecha
    `2030-01-01` o inexistente, CBU de 21 dígitos, número de 200 caracteres (cada uno vuelve nulo).
  - **N03** una respuesta de la IA crea un pago, un evento o un movimiento.
  - **N04** la falla de la IA llega al vecino como 5xx.
  - **N05** la clave aparece en un log o en una respuesta.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `b847213` (bajo la firma por adelantado del 8). Contrato en `aceptacion/H-019/CONTRATO.md`
  (el puerto `LectorDeComprobantes`, las dependencias `lector` y `tope_de_lectura`, la validación campo por campo,
  el adaptador `LectorOpenRouter` con su pedido exacto). Comando: `python3 aceptacion/H-019/aceptar.py
  --sin-regresion`. Esperados: 41 de backend; antes de construir, 40 rojos por aserción y C03 verde (sin clave ya
  responde `sin_ia` desde H-018: queda como regresión).
- Construcción (Sonnet, una tanda): `6e8cf18` `validar_propuesta` pura (22 unitarios vistos fallar con un stub),
  `96cc168` el puerto, `LectorOpenRouter` con ZDR y la configuración (`PROPTECH_OPENROUTER_API_KEY` y
  `PROPTECH_OPENROUTER_MODELO`, también pasadas a la API en `infra/compose.yaml`), `c9c8cc1` la lectura en un hilo con
  tope (20 s; el `httpx` corta a los 15 s), `0a20b77` y `0a951f4` README, `08`, ficha 8 y L-093. El PDF va como parte
  `file` de OpenRouter: **sólo probado con transportes falsos**. Juani decidió el 18/11/2026 no probarlo con su clave
  antes de cerrar el 8: la lectura contra el servicio real (imagen y PDF) queda como deuda del cierre del 8. La
  instrucción fija le dice a la IA que ignore órdenes escritas en la imagen (defensa extra; el contrato no depende de
  eso). Sin migración nueva.
- Evidencia (18/11/2026): `python3 aceptacion/H-019/aceptar.py --codigo b18ca89 --sin-regresion` desde `b847213`:
  **41/41**, C01 a C06, N01 a N05, EST y SPEC (5 escenarios) PASA, 0 rojos. El constructor corrió además H-018 sobre
  `0a951f4`: 54/54. Para `infra/.env.example` (lo agrega Juani): las dos variables comentadas como opcionales.
- Demo y aprobación de Juani: 18/11/2026, dos recorridas del orquestador con la base, la API, el worker y la web
  reales en Chrome (la segunda, con los arreglos de H-026); regresión del cierre H-004 a H-024 y barrido en verde, CI
  del PR #27 verde en `de70b95`. **Terminada por Juani el 18/11/2026** ("si tengo ganas de, primero cerra este 8").

### H-020 · Confirmar y rechazar

- Change: C-11 8, parte 3. Reglas: R04, R05, R11, R19, D-016; E6, E13.
- Resultado para Juani: el administrador confirma un pago en un clic y queda imputado con la fecha de la
  transferencia, aunque lo confirme días después; o lo rechaza con un motivo que el vecino ve.
- Alcance: `POST .../pagos/{id}/confirmacion` y `.../rechazo`, el registro en el libro desde
  `cuenta_corriente/aplicacion/pagos.py` con R04 a la fecha de la transferencia, el CBU de la unidad, la
  auditoría. Exclusiones: el ajuste de interés (H-021).
- Dificultad y riesgo: alta / CRITICAL. Nivel L.
- Tienen que pasar:
  - **C01** confirmar el pago de $43.350,00 de `1A`: un crédito `pago` con `fecha_valor` 05/11/2026 que deja
    la deuda de noviembre de `1A` en cero; evento `confirmado`; auditado.
  - **C02** fecha de la transferencia, no de la confirmación: `1A` debe $100.000 vencidos el 10/09, transfiere
    $100.000 el 30/09 y se confirma el 20/10; la emisión siguiente cobra interés sólo del 11/09 al 30/09.
  - **C03** R04 a la fecha de la transferencia: un pago transferido antes de una emisión y confirmado después
    se imputa primero a la deuda que existía el día de la transferencia, y el resto como lo habría imputado
    la emisión; queda igual al centavo que el mismo pago confirmado el día de la transferencia.
  - **C04** un pago mayor que la deuda deja el excedente como crédito a favor aplicable (R05).
  - **C05** el pago repartido entre `1A` y `2B` imputa cada parte en su unidad.
  - **C06** con CBU de origen, queda guardado para la unidad (R19).
  - **C07** rechazar con motivo deja el evento `rechazado`, no escribe en el libro y el vecino ve el motivo.
  - **C08** la KB: R11 y R05 con lo construido, D nueva si sale, la ficha 8 con H-020.
- Tienen que fallar:
  - **N01** dos confirmaciones del mismo pago (seguidas o en carrera): más de un crédito por parte o más de un
    evento; la segunda responde 200 con el mismo resultado.
  - **N02** confirmar un pago rechazado o revertido, o rechazar uno confirmado: algo distinto de 409
    `estado`.
  - **N03** rechazar sin motivo o con uno de 2 caracteres: algo distinto de 422.
  - **N04** el vecino, el consejo o el contador confirman o rechazan: algo distinto de 403.
  - **N05** confirmar un pago de otro edificio u otra administración: algo distinto de 404.
  - **N06** la confirmación falla a mitad (una parte) y queda alguna parte imputada o el evento escrito.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `da62e96` (bajo la firma por adelantado del 8). Contrato en `aceptacion/H-020/CONTRATO.md`
  (las dos rutas, R04 a la fecha de la transferencia por D-166, `cuenta_corriente.aplicacion.pagos.registrar_pago`
  una vez por parte, auditoría `confirmar_pago_informado` y `rechazar_pago_informado`). Comando:
  `python3 aceptacion/H-020/aceptar.py --sin-regresion`. Esperados: 27 de backend; antes de construir, 27 rojos por
  aserción.
- **Vuelta 2 de la aceptación** (`4196b3c`, congelada en `af941d7`): N06 esperaba la excepción inyectada, pero el
  middleware de seguimiento la convierte en 500; el constructor lo vio y frenó. Ahora espera el 500; lo que se prueba
  (nada escrito después de la falla) no cambia. El comentario del test cita L-095 y la lección quedó como L-094.
- Construcción (Sonnet, una tanda): `a7e1d3c` R04 en dos fases puro (`cuenta_corriente/dominio/pago.py`, 7 unitarios),
  `2c27b57` `registrar_pago` con la deuda de ese día (`calcular_estado` con las emisiones posteriores como anuladas),
  `1443c00` la `0045` (`rechazar_pago_informado` en el vocabulario de auditoría), `c282e08` confirmar y rechazar
  (candado por pago y después las cuentas en orden), `c45435e` R11 con D-166, R05, `04`, ficha 8 y L-094.
  `FotoDeCuenta` suma `imputaciones` y `anuladas` con valor por defecto. Riesgo anotado: `registrar_pago` usa
  `_Pedido` y `_replay` privados de `creditos.py`.
- Evidencia (18/11/2026): `python3 aceptacion/H-020/aceptar.py --codigo af941d7 --sin-regresion` desde `4196b3c`:
  **27/27**, C01 a C08, N01 a N06, EST y SPEC (5 escenarios) PASA, 0 rojos. El constructor corrió además H-018 (54/54)
  y H-019 (41/41) sobre `c45435e`.
- Demo y aprobación de Juani: 18/11/2026, dos recorridas del orquestador con la base, la API, el worker y la web
  reales en Chrome (la segunda, con los arreglos de H-026); regresión del cierre H-004 a H-024 y barrido en verde, CI
  del PR #27 verde en `de70b95`. **Terminada por Juani el 18/11/2026** ("si tengo ganas de, primero cerra este 8").

### H-021 · El ajuste del interés cobrado de más

- Change: C-11 8, parte 4. Reglas: R03, R11, R05 (destino fijo); D-082, D-084, D-085; E7.
- Resultado para Juani: si el administrador confirma tarde un pago y en el medio una emisión le cobró
  interés al vecino por días en que ya había pagado, el sistema le devuelve exacto ese interés.
- Alcance: la función pura de la diferencia de interés en `cuenta_corriente/dominio/intereses.py` (sirve
  también a H-022), el ajuste registrado antes del pago al confirmar, enlazado al interés y al pago.
- Dificultad y riesgo: alta / CRITICAL. Nivel L.
- Tienen que pasar:
  - **C01** `1A` debe la expensa de octubre ($100.000, vencida el 10/10) y transfiere $100.000 el 05/11; la
    emisión de noviembre cobra octubre ($2.100) y la de diciembre cobra noviembre entero sobre $100.000 ($3.000);
    se confirma después: un `ajuste_de_interes` de $2.447,50 (con el pago imputado el 05/11, R04 primero al
    interés de octubre, correspondían $552,50), con destino ese interés y `enlazado_a` él.
  - **C02** después del ajuste, la cuenta queda igual al centavo que la de `1B`, que confirmó el mismo pago
    antes de la emisión de diciembre.
  - **C03** con mes entero en vez de proporcional, el ajuste usa la forma, la tasa y la gracia guardadas en
    los tramos de ese interés.
  - **C04** un pago confirmado antes de la emisión siguiente no genera ajuste.
  - **C05** anular la emisión de diciembre deja fuera el ajuste junto con su interés, sin contra-movimiento
    (D-085).
  - **C06** un pago parcial ajusta sólo el interés de la parte pagada.
  - **C07** un ajuste que no entra en su interés (ya pagado por otro crédito) se registra hasta lo que entra y
    el resto vuelve como `ajuste_sin_destino` en la respuesta, auditado.
  - **C08** la función de la diferencia tiene tests puros con `hypothesis`: nunca negativa para un pago que
    entra, cero sin días cubiertos después de la transferencia.
  - **C09** la KB: R11 (el ajuste construido) y la ficha 8 con H-021.
- Tienen que fallar:
  - **N01** el ajuste se calcula con la configuración vigente hoy y no con la de los tramos.
  - **N02** el pago se imputa antes que el ajuste y paga el interés que se está compensando.
  - **N03** se ajusta un interés de una emisión con período hasta la fecha de la transferencia (D-166).
  - **N04** confirmar dos veces registra dos ajustes.
  - **N05** queda una obligación con residual de interés negativo.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `dc5fbfc` (bajo la firma por adelantado del 8). Contrato en `aceptacion/H-021/CONTRATO.md` (el
  ajuste antes del pago, sobre los tramos guardados, la vista de la fase 1 sin los ajustes de emisiones posteriores,
  `ajuste_sin_destino` en la respuesta, `diferencia_de_interes` y `TramoGuardado` puros). Comando:
  `python3 aceptacion/H-021/aceptar.py --sin-regresion`. Esperados: 13 de backend; sobre el código de H-020, 11 rojos por
  aserción y C04 y N05 verdes (no ajustar cuando no corresponde ya se cumple: quedan como regresión).
- Construcción (Sonnet, una tanda): `002c994` `diferencia_de_interes` y `TramoGuardado` puros (7 unitarios vistos
  fallar con un stub en $0,00; reusan `_proporcional` y `_mes_entero`, así redondean como la emisión), `a595723` el
  ajuste antes del pago (`cuenta_corriente/aplicacion/ajuste_de_interes.py`, con el pago simulado en las dos fases;
  `registrar_credito` acepta `enlazado_a`), `066866f` R11, ficha 8 y L-095. Decisiones del constructor: la auditoría no
  lleva el monto del ajuste sin destino (D9: el detalle nunca lleva montos); la `fecha_valor` del ajuste es la del corte
  del interés que compensa. **Riesgo anotado (deuda)**: el ajuste se calcula con la fase 2 de R04 sobre el estado de
  antes del ajuste; si el sobrante de un pago grande cae en capital de obligaciones posteriores, el ajuste puede quedar
  levemente corto. Ningún test lo cubre.
- Evidencia (18/11/2026): `python3 aceptacion/H-021/aceptar.py --codigo 066866f --sin-regresion` desde `dc5fbfc`: **13/13**,
  C01 a C09, N01 a N05, EST y SPEC (3 escenarios) PASA, 0 rojos. El constructor corrió además H-020 (27/27).
- Demo y aprobación de Juani: 18/11/2026, dos recorridas del orquestador con la base, la API, el worker y la web
  reales en Chrome (la segunda, con los arreglos de H-026); regresión del cierre H-004 a H-024 y barrido en verde, CI
  del PR #27 verde en `de70b95`. **Terminada por Juani el 18/11/2026** ("si tengo ganas de, primero cerra este 8").

### H-022 · Revertir un pago

- Change: C-11 8, parte 5. Reglas: R03, R18, R20; D-074, D-083, D-163 (P29); E8, E9, E13.
- Resultado para Juani: un pago que el banco devuelve se marca revertido con un motivo, la unidad vuelve a
  deber todo lo que debía con el interés desde el vencimiento original, y si ahora es moroso crítico, lo
  dice.
- Alcance: `POST .../pagos/{id}/reversion`, el `reversion_de_pago` por parte, la reversión de los ajustes
  enlazados, el tipo nuevo `interes_por_reversion` (migración) y su exclusión si su interés deja de contar.
- Dificultad y riesgo: alta / CRITICAL. Nivel L.
- Tienen que pasar:
  - **C01** revertir el pago confirmado de `1A` con "cheque rechazado": un `reversion_de_pago` con
    `corrige_a` el pago; la deuda de `1A` vuelve a la de antes del pago; el pago se ve `revertido`; auditado.
  - **C02** P29: el pago del 05/11 se confirmó el 05/11, la emisión de diciembre cobró interés con él
    adentro, el 10/12 se revierte: `interes_por_reversion` por la diferencia, y el interés de `1A` queda
    igual al centavo al de una cuenta que nunca recibió ese pago.
  - **C03** revertir un pago con ajuste de interés (H-021) revierte el ajuste con un contra-asiento.
  - **C04** después de revertir, `situacion_de_cuenta` da a `1A` como moroso crítico si tiene dos
    liquidaciones vencidas con capital impago.
  - **C05** un pago repartido revierte todas sus partes.
  - **C06** anular la emisión cuyo interés completó el `interes_por_reversion` lo deja fuera con él.
  - **C07** la migración del tipo nuevo sube sobre una base desplegada y baja limpia; la KB: R18 y la ficha 8.
- Tienen que fallar:
  - **N01** revertir un pago `informado`, `rechazado` o ya `revertido`: algo distinto de 409 `estado`.
  - **N02** revertir sin motivo: algo distinto de 422.
  - **N03** el pago original se borra, cambia o deja de verse.
  - **N04** el `interes_por_reversion` genera interés en un corte siguiente (interés sobre interés, R03).
  - **N05** quien no tiene `revertir_o_reimputar_pago` revierte: algo distinto de 403.
  - **N06** revertir dos veces en carrera deja dos reversiones.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `c5e08e3` (bajo la firma por adelantado del 8). Contrato en `aceptacion/H-022/CONTRATO.md` (la
  reversión del movimiento vigente, el contra-asiento de los ajustes, `interes_por_reversion` con `diferencia_de_interes`
  sin el pago, su exclusión como la del ajuste, auditoría `revertir_pago_informado`, sólo SA y AP). Comando:
  `python3 aceptacion/H-022/aceptar.py --sin-regresion`. Esperados: 20 de backend; sobre el código de H-021, 20 rojos por
  aserción (C07 buscaba la migración por el nombre del tipo y encontraba la `0044`, que lo admite como papel: antes de
  congelar se afinó a la que lo siembra en `tipo_de_movimiento`).
- Construcción (Sonnet, una tanda): `0b32899` la exclusión de `interes_por_reversion` como la del ajuste (2 unitarios
  vistos fallar), `ef5d260` la `0046` (siembra el tipo y `revertir_pago_informado`, deja que `reversion_de_pago` lleve
  `corrige_a` con dos `CHECK` nuevos, con `PRESTA_PROPIEDAD` sobre `movimiento`, L-088), `864f459` revertir con la reversión
  del ajuste y el interés de P29 (`cuenta_corriente/aplicacion/reversion_de_pago.py`), `d0db10a` R18, `04`, ficha 8 y
  L-096, `d688bb7` el libro decide qué movimiento del pago está vigente (frontera: `pagos` no lee `movimiento`),
  `22834f9` estilo. Decisiones del constructor: P29 compara contra el interés **neto** (con sus ajustes y sus intereses
  por reversión, para no cobrar dos veces si dos pagos tardíos tocan el mismo interés: **sin test**, deuda); un interés
  importado sin tramos no se recalcula; una corrección manual no puede deshacer un `reversion_de_pago` (409, con test).
- Evidencia (18/11/2026): `python3 aceptacion/H-022/aceptar.py --codigo 22834f9 --sin-regresion` desde `c5e08e3`: **20/20**, C01
  a C07, N01 a N06, KB, EST y SPEC (4 escenarios) PASA, 0 rojos. El constructor corrió además H-021 (13/13) y H-020
  (27/27).
- Demo y aprobación de Juani: 18/11/2026, dos recorridas del orquestador con la base, la API, el worker y la web
  reales en Chrome (la segunda, con los arreglos de H-026); regresión del cierre H-004 a H-024 y barrido en verde, CI
  del PR #27 verde en `de70b95`. **Terminada por Juani el 18/11/2026** ("si tengo ganas de, primero cerra este 8").

### H-023 · Reimputar un pago a la unidad correcta

- Change: C-11 8, parte 6. Reglas: R25 (vigente por D-163), R20; D-163 (P29); E10, E13.
- Resultado para Juani: un pago confirmado en la unidad equivocada pasa a la correcta en una sola operación:
  la equivocada vuelve a deber como antes y la correcta queda pagada con la fecha de la transferencia.
- Alcance: `POST .../pagos/{id}/reimputacion`, los dos `reimputacion` enlazados, la reversión de ajustes y el
  interés de la reversión en la de origen, el ajuste en la de destino.
- Dificultad y riesgo: alta / CRITICAL. Nivel L.
- Tienen que pasar:
  - **C01** el pago de $43.350,00 confirmado en `1B` se reimputa a `1A`: en `1B` un `reimputacion` débito con
    `corrige_a` el pago y `1B` vuelve a deber lo de antes; en `1A` un `reimputacion` crédito con `fecha_valor`
    la de la transferencia, `enlazado_a` el débito, imputado con R04 a esa fecha; evento `reimputado`;
    auditado.
  - **C02** `situacion_de_cuenta` da bien a las dos unidades después.
  - **C03** con una emisión de por medio, `1B` recibe su `interes_por_reversion` y `1A` su ajuste, al
    centavo.
  - **C04** reimputar de nuevo desde `1A` a `2A` corrige el `reimputacion` crédito de `1A`.
  - **C05** revertir después un pago reimputado revierte el movimiento vigente (el de `1A`).
  - **C06** la KB: R25 vigente y construida, la ficha 8 con H-023.
- Tienen que fallar:
  - **N01** un fallo en el paso de destino (inyectado) deja algún movimiento en cualquiera de las dos cuentas.
  - **N02** reimputar a la misma unidad (422), a una de otro edificio (404), una parte que no está en esa
    unidad (422), un pago no confirmado (409).
  - **N03** reimputar sin motivo: 422.
  - **N04** dos reimputaciones en carrera de la misma parte dejan dos movimientos.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `3c3bb8d` (bajo la firma por adelantado del 8). Contrato en `aceptacion/H-023/CONTRATO.md` (el orden
  de validaciones, la unidad vigente de cada parte, el destino por `registrar_pago` para poder hacerlo fallar, la
  auditoría `reimputar_pago_informado`). Comando: `python3 aceptacion/H-023/aceptar.py --sin-regresion`. Esperados: 16 de
  backend; sobre el código de H-022, 16 rojos por aserción.
- Construcción (Sonnet, una tanda): `208b1b1` reimputar con la `0047` (`corrige_a` en el débito, `enlazado_a` en el crédito,
  `reimputar_pago_informado`, `PRESTA_PROPIEDAD` sobre `movimiento`), el origen como la reversión
  (`_revertir_en_la_cuenta` compartido) y el destino por `registrar_pago` con `tipo`, `enlazado_a` y `motivo`; `624ff56`
  R25 vigente, ficha 8, `04` y L-097; `0c90d68` estilo. **Deuda para la demo**: si una parte se reimputa a una unidad que
  ya tenía otra parte del mismo pago, reimputar después "desde esa unidad" mueve las dos (los ajustes no se distinguen
  por parte); sin test, documentado en R25. El 422 de `desde_unidad_id` se detecta después de escribir el origen y lo
  deshace el rollback (no queda nada).
- Evidencia (18/11/2026): `python3 aceptacion/H-023/aceptar.py --codigo 0c90d68 --sin-regresion` desde `3c3bb8d`: **16/16**, C01
  a C05, N01 a N05, KB, EST y SPEC (2 escenarios) PASA, 0 rojos. El constructor corrió además H-022 (20/20) y H-021
  (13/13).
- Demo y aprobación de Juani: 18/11/2026, dos recorridas del orquestador con la base, la API, el worker y la web
  reales en Chrome (la segunda, con los arreglos de H-026); regresión del cierre H-004 a H-024 y barrido en verde, CI
  del PR #27 verde en `de70b95`. **Terminada por Juani el 18/11/2026** ("si tengo ganas de, primero cerra este 8").

### H-024 · El comprobante con link firmado y el control de pagos sin confirmar

- Change: C-11 8, parte 7. Reglas: R34; D-070; E1 (firma compartida), E11, E12.
- Resultado para Juani: el comprobante de un pago se abre sólo con un link que vence en 15 minutos, y al
  preparar la liquidación se ve cuántos pagos faltan confirmar.
- Alcance: la firma HMAC en `compartido/enlaces.py` con tipo, la fachada de la expensa intacta, el enlace y la
  descarga del comprobante, la ruta de Next para bajarlo, el control `pagos_sin_confirmar`.
- Dificultad y riesgo: media / CRITICAL. Nivel M.
- Tienen que pasar:
  - **C01** el administrador pide el enlace del comprobante y descarga los mismos bytes con su tipo.
  - **C02** Ana pide el enlace de un pago de `1A` y lo descarga; vencido da 410; alterado, 403.
  - **C03** dos pagos informados ($30.000 y $15.000) hacen aparecer `pagos_sin_confirmar`, advertencia, al
    final de la lista, con 2 y `45000.00`; confirmados o rechazados, no aparece; no frena la emisión.
  - **C04** las aceptaciones de H-012 (controles) y H-015 (enlaces de la expensa) siguen en verde.
  - **C05** la KB: R34 y `08` con lo construido, la ficha 8 con H-024.
- Tienen que fallar:
  - **N01** un token de expensa sirve para un comprobante, o al revés: algo distinto de 403.
  - **N02** Beto (inquilino de `1B`) o un vecino de otra administración piden el enlace de un pago de `1A`:
    algo distinto de 404.
  - **N03** el comprobante tiene una dirección pública o se baja sin token.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `1e6e461` (bajo la firma por adelantado del 8). Contrato en `aceptacion/H-024/CONTRATO.md` (el enlace y
  la descarga, la firma compartida con tipo, `firmar_enlace_del_comprobante`, el control con su `detalle`). Comando:
  `python3 aceptacion/H-024/aceptar.py --sin-regresion` (corre siempre H-012 y H-015 del 7, C04). Esperados: 13 de backend;
  sobre el código de H-022, 12 rojos por aserción y `test_c03_sin_pagos_no_aparece` verde (queda como regresión).
- Construcción (Sonnet, una tanda): `673c722` la firma HMAC en `compartido/enlaces.py` con el tipo dentro del cuerpo firmado
  (la expensa queda como capa fina con su contrato de H-015), `5b5772f` el enlace y la descarga del comprobante y el control
  `pagos_sin_confirmar` (`liquidacion` lee `pagos.aplicacion.lectura`), `4fb7b11` R34, `08`, ficha 8 y L-098. Riesgo anotado:
  el control entra en la huella de la preliquidación; confirmar o rechazar un pago entre preliquidar y emitir pide volver a
  revisar (coherente con H-013; lo mira la regresión del cierre). La ruta de Next para bajar el comprobante es de H-025.
- Evidencia (18/11/2026): `python3 aceptacion/H-024/aceptar.py --codigo 4fb7b11 --sin-regresion` desde `1e6e461`: **13/13**, C01
  a C05 (C04: H-012 y H-015 en verde desde sus SHA), N01 a N03, EST y SPEC (2 escenarios) PASA, 0 rojos.
- Demo y aprobación de Juani: 18/11/2026, dos recorridas del orquestador con la base, la API, el worker y la web
  reales en Chrome (la segunda, con los arreglos de H-026); regresión del cierre H-004 a H-024 y barrido en verde, CI
  del PR #27 verde en `de70b95`. **Terminada por Juani el 18/11/2026** ("si tengo ganas de, primero cerra este 8").

### H-025 · Las pantallas de pagos

- Change: C-11 8, parte 8. Reglas: HU-V4, HU-A6; D-131 (menú por rol); E14. Skill **impeccable**.
- Resultado para Juani: el vecino entra, sube su comprobante, revisa lo que leyó la IA, elige la unidad y
  envía, y después ve el estado; el administrador abre "Pagos" del edificio y confirma, rechaza, revierte o
  reimputa desde ahí.
- Alcance: "Mis pagos" e "Informar un pago" del vecino, "Pagos" del edificio, el menú por rol, los escenarios
  de la API falsa. Exclusiones: el resto del portal (11).
- Dificultad y riesgo: media / CRITICAL (pantallas que escriben en el libro). Nivel M.
- Tienen que pasar (en navegador real, contra la API falsa):
  - **C01** el vecino sube el comprobante, ve la propuesta precargada, corrige un campo, elige la unidad y
    envía; la última escritura es el `POST .../pagos` con lo corregido.
  - **C02** con dos unidades, reparte el pago en dos partes; el envío manda las dos.
  - **C03** si la lectura volvió `fallida`, los campos están vacíos con un aviso y se puede enviar a mano.
  - **C04** "Mis pagos" muestra cada pago con su estado en texto y el motivo de un rechazo.
  - **C05** la bandeja del administrador lista los informados; "Confirmar" pide confirmación y manda el
    `POST`; "Rechazar" exige motivo.
  - **C06** en un confirmado, "Revertir" (con motivo) y "Reimputar" (unidad de destino y motivo) mandan sus
    `POST`.
  - **C07** "Ver comprobante" pide el enlace y abre la URL.
  - **C08** a 320 px sin scroll horizontal y sin errores de axe en las tres pantallas; la ficha 8 con H-025.
- Tienen que fallar:
  - **N01** el menú del vecino muestra "Pagos" del edificio o el del administrador no lo muestra.
  - **N02** el vecino ve, para elegir, una unidad que no es suya.
  - **N03** la pantalla calcula o redondea un monto: partes que no suman se mandan igual y el 422 de la API
    (`campo` `partes`) se muestra en el reparto, nunca una suma hecha en el navegador.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `0d5c6d3` (bajo la firma por adelantado del 8). Contrato en `aceptacion/H-025/CONTRATO.md` (la ruta nueva
  `GET .../pagos/unidades`, las tres pantallas, el menú por acción, la ruta de Next del comprobante y los escenarios
  `2501`/`2502` de la API falsa con la identidad `user_vecina`). Comando: `python3 aceptacion/H-025/aceptar.py` (sin
  `--sin-regresion` corre la regresión del cierre: H-004 a H-024 y el barrido). Esperados: 5 de backend y 13 en navegador;
  antes de construir, 18 rojos por aserción. El runner reintenta una vez el build de la web: Next.js 16.4.3 corta el
  primer build de cada carpeta nueva con un aviso de seguridad (la actualización la decide Juani).
- Construcción (Sonnet, una tanda, con la skill impeccable): `3711412` la ruta `GET .../pagos/unidades`, `03731a3` el cliente
  de pagos y la ruta de Next `/comprobantes/descarga`, `3cf6078` "Pagos" y "Mis pagos" en el menú por acción, `487cd1d` la API
  falsa de pagos con `user_vecina`, `2baea95` las tres pantallas, `36462fd` ficha 8, HU-V4, HU-A6, `08` y L-099.
  `next.config.ts` sube el límite de las server actions a 11 MB (la foto de un comprobante pasa de 1 MB). **Para la demo**:
  reimputar desde la pantalla sólo ofrece la primera parte de un pago repartido; la vecina no tiene "Ver comprobante" en
  "Mis pagos" (el contrato no lo pedía); `impeccable detect` no se corrió; nadie vio las pantallas fuera de Playwright.
- **Next.js 16.4.5** (`e8b6145`, decisión delegada por Juani el 18/11/2026: "como quieras"): 16.4.3 tenía GHSA-mfr8-8qww-v76h y
  GHSA-vc7v-qv4w-wrv8 (moderadas, parche desde 16.4.5) y su build cortaba la primera corrida de cada carpeta nueva.
  `pnpm audit --prod` sin vulnerabilidades después.
- **Cierre del change, regresión una sola vez** (18/11/2026): `python3 aceptacion/H-025/aceptar.py --codigo 36462fd` desde
  `0d5c6d3`: las aceptaciones congeladas de H-004 a H-024 en verde; el barrido de migraciones dio 2 de 1653 en rojo, los dos
  de deuda del 8 que sólo ve el barrido (L-100): las rutas POST nuevas sin registrar en `test_altas_sin_id_del_cliente`
  (y, para que su 422 llegue, un campo ajeno en rechazar, revertir y reimputar se rechaza antes de buscar el pago) y el
  conteo de `tipo_de_movimiento` en `test_libro_proteccion` (15 con la `0046`). Arreglados en `12fc23c`, `23c182d` y
  `4f0b631`; re-corridos esos archivos y H-020 (27/27), H-022 (20/20) y H-023 (16/16) sobre `4f0b631`.
- Evidencia (18/11/2026): `python3 aceptacion/H-025/aceptar.py --codigo 4f0b631 --sin-regresion` desde `0d5c6d3`: **5/5 de backend y
  13/13 en navegador** con Next 16.4.5, C01 a C08, N01 a N03 y C10 PASA, 0 rojos.
- Demo y aprobación de Juani: 18/11/2026, dos recorridas del orquestador con la base, la API, el worker y la web
  reales en Chrome (la segunda, con los arreglos de H-026); regresión del cierre H-004 a H-024 y barrido en verde, CI
  del PR #27 verde en `de70b95`. **Terminada por Juani el 18/11/2026** ("si tengo ganas de, primero cerra este 8").

### H-026 · Los hallazgos de la demo del 8

- Change: C-11 8, parte 9. Origen: la demo en vivo del 18/11/2026 con la base, la API, el worker y la web reales (Juani:
  "dale, se arregla como hu nueva"). Nivel M: pantallas y un dato más en la lista de pagos; ningún movimiento nuevo en
  el libro. Constructor y subagentes con Sonnet.
- Resultado para Juani: la vecina ve sólo lo suyo en el menú, escribe el monto como lo escribe cualquiera, la lista se
  lee bien, un pago reimputado dice dónde está ahora, y el administrador puede informar un pago por un vecino.
- Alcance: el menú del edificio por acción (las secciones de configuración piden `ver_configuracion_del_edificio`), el
  formato de los montos en "Informar un pago" (sólo formato, nunca un cálculo), el motivo en su propio renglón, la
  unidad vigente de cada parte en `GET .../pagos` y en la pantalla, y "Informar un pago" desde la bandeja.
  Exclusiones: el resto del portal del vecino (11).
- Tienen que pasar:
  - **C01** la vecina ve en el menú del edificio sólo "Mis pagos" (ni "Resumen", ni "Unidades", ni "Grupos", ni
    "Categorías", ni "Intereses y vencimiento").
  - **C02** en "Informar un pago" el monto y los importes se escriben como en Argentina ("43350", "43.350", "43350,5",
    "43.350,00") y la API recibe `"43350.00"` / `"43350.50"`.
  - **C03** en las listas, la unidad y el motivo van en renglones separados (nunca "Unidad 2BMotivo:").
  - **C04** `GET .../pagos` trae en cada parte la unidad vigente (`unidad_vigente_id`, `identificador_vigente`): la
    misma unidad si no se reimputó, la de destino si sí.
  - **C05** la bandeja muestra "Ahora en <identificador>" en una parte reimputada, y "Reimputar" parte de la unidad
    vigente.
  - **C06** la bandeja tiene "Informar un pago", que lleva a `/edificios/{id}/pagos/informar` con todas las unidades
    del edificio; al enviar, vuelve a la bandeja.
  - **C07** a 320 px sin scroll horizontal y sin errores de axe en las pantallas tocadas; H-025 sigue en verde; la
    ficha 8 registra H-026.
- Tienen que fallar:
  - **N01** el administrador pierde del menú "Resumen", "Unidades", "Grupos", "Categorías" o "Intereses y
    vencimiento".
  - **N02** la pantalla redondea o calcula: "43350,123" se manda tal cual y se muestra el error de la API, nunca
    "43350.12".
  - **N03** una vecina ve "Informar un pago" de la bandeja, o la bandeja.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `ed8276f`. Contrato en `aceptacion/H-026/CONTRATO.md`. Comando: `python3 aceptacion/H-026/aceptar.py
  --sin-regresion`. Esperados: 3 de backend y 12 en navegador; antes de construir, 12 rojos por aserción y N01 a N03 verdes
  (guardas de regresión). Antes de congelar, C03 se cambió a medir posiciones (con `innerText` pasaba sin reproducir el
  defecto de la demo) y C06 a esperar el link antes de hacer clic (fallaba por timeout).
- Construcción (Sonnet, una tanda, sin migraciones): `380d1b6` la unidad vigente de cada parte
  (`cuenta_corriente/aplicacion/ubicacion_de_pago.py`, sigue la cadena de reimputaciones; `pagos` la pide por `aplicacion`),
  `7e4fe30` el menú por `ver_configuracion_del_edificio`, `montoArgentinoParaApi` (sólo formato), el motivo en su renglón,
  "Ahora en X" y reimputar desde la vigente, "Informar un pago" desde la bandeja (`pagos/informar`), `7076882` ficha 8,
  HU-V4, HU-A6 y L-101. **Para la demo**: la vecina ve el identificador de la unidad a la que se reimputó su pago (sólo
  dónde quedó, ningún saldo); `/pagos/informar` no tiene chequeo de permiso del servidor (lo hace la pantalla y la API al
  enviar); `impeccable detect` no se pudo correr (su script no está en el repo).
- Evidencia (18/11/2026): `python3 aceptacion/H-026/aceptar.py --codigo 7076882 --sin-regresion` desde `ed8276f`: **3/3 de
  backend y 12/12 en navegador**, C01 a C07, N01 a N03 y C10 PASA, 0 rojos. El constructor corrió además H-025 (5/5 y 13/13).
- Demo y aprobación de Juani: 18/11/2026, dos recorridas del orquestador con la base, la API, el worker y la web
  reales en Chrome (la segunda, con los arreglos de H-026); regresión del cierre H-004 a H-024 y barrido en verde, CI
  del PR #27 verde en `de70b95`. **Terminada por Juani el 18/11/2026** ("si tengo ganas de, primero cerra este 8").

## Morosidad (10a, C-14)

Riesgo **HIGH** (Juani, 24/11/2026): sólo lectura, sin escribir en el libro, pero muestra plata y datos
personales y exporta. Lleva la firma de la propuesta en `openspec/changes/morosidad/` antes de construir (D-094,
D-111). Historias en nivel L de Rein 1.5. Rama `10a-morosidad`; sin rompedor (D-152); CI y regresión una vez al
cerrar (D-154). Tres historias: H-027 (la lectura y su API), H-028 (el Excel), H-029 (la pantalla).
Juani delegó el change entero (24/11/2026: "podes trabajar solo, te doy el permiso y armarte vos el change
directamente y despues hacemos la demo juntos"): como en el 8, las historias se construyen una detrás de otra y las
demos van juntas al final, también con dos o más en Lista. Constructor y subagentes con Claude Sonnet.

**Cierre (24/11/2026)**: regresión del cierre (H-004 a H-028, barrido de migraciones y estructurales) en verde sobre
`c7ea831` con `python3 aceptacion/H-029/aceptar.py --sin-navegador`. CI del PR #28 en tres vueltas: la primera cayó en
`web/e2e/pulido.spec.ts`, que contaba 6 links del menú (L-103, `39b4177`); la segunda, en un test del 7 que dependía del
orden con xdist (L-104, `8c5b278`); la tercera, **verde 6/6 sobre `8c5b278`**. Deuda en la ficha 10a.

**Acuerdos de Juani del 24/11/2026** (van a una decisión nueva con H-027, K02):
- **Ven** la morosidad super admin, administrador, contador, auxiliar y consejo, cada uno en su alcance (D-106);
  **exportan** el Excel sólo super admin, administrador y contador. Auxiliar y consejo sólo ven.
- **Intereses**: sólo el interés registrado en el libro e impago; no se estima el que corrió desde la última
  emisión. La pantalla dice a qué fecha es.
- **Antigüedad**: la liquidación vencida más vieja con algo impago (capital o interés); se muestran su fecha de
  vencimiento y los días desde el vencimiento (no desde el fin de la gracia). Sin deuda vencida, vacía.
- **Qué unidades aparecen**: sólo las que tienen deuda vencida, con su etiqueta de R20/R30; primero los morosos
  críticos y, dentro de cada grupo, de mayor a menor deuda; arriba, cuántas deben, cuántas son morosos críticos y
  el total vencido del edificio.
- **Datos de la persona**: el identificador de la unidad y el nombre de sus propietarios; sin email, teléfono ni
  DNI.

### H-027 · La lectura de la morosidad

- Change: C-14 10a, parte 1. Reglas: R20, R30; D-058, D-074, D-106, D-143; HU-A8.
- Resultado para Juani: `GET .../complejos/{id}/morosidad` devuelve las unidades que deben, con su deuda vencida,
  capital, intereses y antigüedad, y el resumen del edificio, para quien puede verlo.
- Alcance: completar la lectura del 4c (capital e interés por separado y el vencimiento más viejo impago), el
  permiso de ver la morosidad y la ruta de lectura. Exclusiones: el Excel (H-028), la pantalla (H-029), la gestión
  judicial y su exclusión de R20 (10b).
- Dificultad y riesgo: media / HIGH. Nivel L (plata y datos personales detrás de permisos).
- Tienen que pasar:
  - **C01** cada fila trae unidad, nombres de los propietarios, etiqueta, total vencido, capital, intereses,
    liquidaciones vencidas, fecha del vencimiento más viejo y días; arriba, el resumen del edificio y la fecha de
    los intereses (la de la última emisión).
  - **C02** una deuda pagada en partes baja en la lista; pagada entera, la unidad desaparece.
  - **C03** orden: morosos críticos primero y, dentro de cada grupo, de mayor a menor total vencido.
  - **C04** la etiqueta de cada unidad es la misma que da `situacion_del_edificio` del 4c a la misma fecha.
  - **C05** si de la liquidación más vieja sólo quedó el interés impago, la antigüedad sigue contando desde ella.
  - **C06** super admin, administrador, contador, auxiliar y consejo con alcance sobre el edificio: 200.
  - **C07** la KB queda al día según K01 a K03.
- Tienen que fallar:
  - **N01** el vecino pide la morosidad: 403; personal o consejo sin alcance sobre el edificio, u otra
    administración: 404.
  - **N02** una unidad con una sola liquidación vencida, o con total vencido menor a $500, no sale como moroso
    crítico.
  - **N03** la respuesta no trae email, teléfono ni DNI de nadie.
  - **N04** pedir la morosidad no escribe: movimientos, imputaciones y auditoría quedan iguales.
  - **N05** una unidad al día, o con sólo crédito a favor, no aparece; una obligación de una emisión anulada no
    cuenta.
  - **N06** el interés que corrió después de la última emisión no se suma a los intereses.
- Cierre de la base:
  - **K01** R20 en `knowledge-base/05_reglas_de_negocio.md`: dónde vive el listado y las definiciones de
    antigüedad e intereses.
  - **K02** una decisión nueva en `knowledge-base/09_decisiones_y_supuestos.md` con los acuerdos del 24/11/2026.
  - **K03** el permiso de ver la morosidad en `knowledge-base/03_actores_y_roles.md`.
- Guion de demo: con la Torre Ficticia de los ejemplos del 8, entrar como administrador y como consejo y ver la
  lista con un moroso crítico, una unidad con deuda vencida, una bajo el umbral y una que pagó en partes.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `4a1ae4f` (bajo la firma por adelantado del 10a). Contrato en `aceptacion/H-027/CONTRATO.md`
  (la dependencia `proptech_api.morosidad.hoy`, `ver_morosidad` con su migración, la forma exacta de la
  respuesta, el orden y `intereses_al`). Comando: `python3 aceptacion/H-027/aceptar.py --sin-regresion`. Esperados:
  25 de backend; antes de construir, 21 rojos por aserción, 0 por setup, y 4 guardas de 404 que nacen verdes.
- **Vuelta 2 de la aceptación** (`3265551`, congelada en `4948116`): el constructor frenó en N02 con evidencia: el
  escenario armaba la deuda con pagos parciales sin hacer la cuenta de R04, que imputa primero al período más viejo,
  y daba una sola vencida en `2B` y un moroso crítico real en `1B`. El error era del escenario, no del código. N02
  pasa a armarse sin pagos parciales (`2B` con dos meses de $200 impagos); se vio fallar por aserción contra un
  mutante que pone el moroso crítico antes del umbral (`'moroso_critico' == 'bajo_umbral'`) y pasar contra lo
  construido. Lección L-102.
- Construcción (Sonnet, una tanda): `d4fcb57` capital, interés y `vencida_desde` en `clasificar` (4 tests de apoyo, rojo
  por `AttributeError` del campo inexistente, no por aserción de valor), `38d23d7` `ver_morosidad` y la `0048`, `978b115`
  la lectura (`cuenta_corriente/aplicacion/morosidad.py`, con los propietarios desde `acceso/aplicacion/propietarios.py`
  y los identificadores desde `complejos/aplicacion/unidades.py`) y la ruta, `0f221bb` KB (R20, D-167, `03`, ficha
  10a). Estructurales actualizados: rutas protegidas, permisos, vocabulario, sesión y la cabeza en `test_libro_rollback`.
  Ruff, format y mypy enteros en verde. **Deuda chica**: `proptech_api/morosidad.py` importa `_edificio_autorizado`,
  privada de `liquidaciones.py`.
- Evidencia (24/11/2026): `python3 aceptacion/H-027/aceptar.py --sin-regresion` sobre `4948116` desde `3265551`:
  **25/25**, C01 a C06, N01 a N06 y SPEC (6 escenarios) PASA, 0 rojos; C07 con K01 a K03, la ficha y los estructurales
  en verde, sólo pendiente la regresión del cierre (D-154).
- Demo y aprobación de Juani: 24/11/2026, recorrida del orquestador con PostgreSQL efímero (roles y migraciones
  reales, la deuda cargada con `registrar_emision` y `registrar_credito`), la API y la web compilada en Chrome.
  Administrador: resumen 4 / 1 / $79.020,00, 1A moroso crítico primero ($30.720, 75 días), 2A bajo el umbral al
  final; Excel bajado desde el botón, abierto en LibreOffice, montos numéricos y total $79.020; consejo sin botón y
  403 en la ruta del Excel; 320 px sin scroll horizontal (Playwright: Chrome no baja de 534 px). Hallazgo anotado
  como deuda en la ficha 10a. **Terminada por Juani el 24/11/2026** ("anotalo como deuda y pasa a terminado").
- Estado: **Terminada** (24/11/2026).

### H-028 · El Excel de la morosidad

- Change: C-14 10a, parte 2. Reglas: R20; D-106, D-167; HU-A8 ("cuando la exporto, obtengo un Excel con los mismos
  números"); E6 y E8 de `design.md`.
- Resultado para Juani: el administrador o el contador baja la morosidad del edificio en un `.xlsx` con las mismas
  filas y los mismos montos que la pantalla, como números con formato de pesos que se pueden sumar.
- Alcance: `GET /api/complejos/{id}/morosidad/excel` sobre la lectura de H-027, la acción `exportar_morosidad` con su
  migración. Exclusiones: el botón en la pantalla (H-029), otros formatos (CSV, PDF).
- Dificultad y riesgo: baja / HIGH. Nivel L (datos personales que salen del sistema).
- Tienen que pasar:
  - **C01** responde un `.xlsx` (`content-type` de Excel, adjunto `morosidad-torre-ficticia-2026-11-18.xlsx`) con el
    encabezado (edificio, fecha, intereses al), los títulos y una fila por unidad.
  - **C02** celda por celda: las filas, el orden y cada monto son iguales al centavo a los de la API de H-027.
  - **C03** la fila de totales suma el total vencido, el capital y los intereses, igual al resumen de la API.
  - **C04** exportan super admin, administrador principal y por edificio, contador principal y por edificio.
  - **C05** un edificio sin deuda vencida baja el Excel con los títulos y el total en cero.
  - **C06** la KB queda al día según K01 y K02.
- Tienen que fallar:
  - **N01** auxiliar, consejo y vecino: 403 `exportar_morosidad`; fuera del alcance u otra administración: 404.
  - **N02** ningún monto ni total va como texto ni como fórmula: son números con formato `#,##0.00`.
  - **N03** el Excel no trae el email de nadie.
  - **N04** bajar el Excel no escribe en el libro ni en la auditoría.
- Cierre de la base:
  - **K01** `exportar_morosidad` en `knowledge-base/03_actores_y_roles.md`.
  - **K02** HU-A8 en `knowledge-base/06_funcionalidades.md` con lo construido (la ruta del Excel).
- Guion de demo: como administrador, bajar el Excel de la Torre Ficticia, abrirlo y sumar una columna; como consejo,
  ver que no puede bajarlo.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `6acb3a4` (bajo la firma por adelantado del 10a). Contrato en `aceptacion/H-028/CONTRATO.md`
  (la hoja `Morosidad` celda por celda, el nombre del archivo, `exportar_morosidad` con su migración). Comando:
  `python3 aceptacion/H-028/aceptar.py --sin-regresion`. Esperados: 19 de backend; antes de construir, 16 rojos por
  aserción, 0 por setup, y 3 guardas de 404 que nacen verdes. Antes de congelar, N04 se endureció para exigir el 200
  de quien exporta (sin eso pasaba con la ruta ausente).
- Construcción (Sonnet, una tanda, `11432e9`): `exportar_morosidad` y la `0049`; el libro se arma en
  `cuenta_corriente/adaptadores/excel_de_morosidad.py` desde `morosidad_del_edificio` (la misma lectura de H-027);
  montos como número (`float` del `Decimal` exacto, la celda de Excel es de punto flotante) con formato `"$ "#,##0.00`,
  totales sumados con `Dinero` en Python, sin fórmulas; fechas `dd/mm/yyyy`. Saldó la deuda chica de H-027:
  `_edificio_autorizado` pasa a `edificio_autorizado`, pública. Tests de apoyo del nombre del archivo, con rojo por
  aserción. Ruff, format y mypy enteros en verde. El `.xlsx` se leyó con `openpyxl`, no se abrió en Excel ni en
  LibreOffice (queda para la demo).
- Evidencia (24/11/2026): `python3 aceptacion/H-028/aceptar.py --sin-regresion` sobre `11432e9` desde `6acb3a4`:
  **19/19**, C01 a C05, N01 a N04 y SPEC PASA, 0 rojos; C06 con K01, K02, la ficha y los estructurales en verde, sólo
  pendiente la regresión del cierre. H-027 sigue en 25/25 sobre el mismo commit.
- Demo y aprobación de Juani: 24/11/2026, recorrida del orquestador con PostgreSQL efímero (roles y migraciones
  reales, la deuda cargada con `registrar_emision` y `registrar_credito`), la API y la web compilada en Chrome.
  Administrador: resumen 4 / 1 / $79.020,00, 1A moroso crítico primero ($30.720, 75 días), 2A bajo el umbral al
  final; Excel bajado desde el botón, abierto en LibreOffice, montos numéricos y total $79.020; consejo sin botón y
  403 en la ruta del Excel; 320 px sin scroll horizontal (Playwright: Chrome no baja de 534 px). Hallazgo anotado
  como deuda en la ficha 10a. **Terminada por Juani el 24/11/2026** ("anotalo como deuda y pasa a terminado").
- Estado: **Terminada** (24/11/2026).

### H-029 · La pantalla de la morosidad

- Change: C-14 10a, parte 3. Reglas: R20; D-036, D-106, D-167; HU-A8; L-085, L-099, L-101.
- Resultado para Juani: desde el menú del edificio, "Morosidad" muestra el resumen, la fecha de los intereses y la
  lista de las unidades que deben, y quien puede baja el Excel con un botón.
- Alcance: la sección del menú, la pantalla `/edificios/{id}/morosidad`, la ruta de Next que baja el Excel (el
  navegador nunca ve el token, D-036), la API falsa de e2e. Pasa por la skill impeccable. Exclusiones: filtros,
  búsqueda, el detalle de una unidad.
- Dificultad y riesgo: media / HIGH. Nivel L (datos personales en pantalla, permisos por perfil).
- Tienen que pasar:
  - **C01** el super admin ve "Morosidad" en el menú, en el grupo "Liquidación", y lleva a la pantalla.
  - **C02** la pantalla muestra el resumen (unidades que deben, morosos críticos y total vencido) y "Intereses al
    31/10/2026".
  - **C03** la lista "Unidades con deuda" trae una fila por unidad en el orden de la API, con la unidad, los
    propietarios, la situación en palabras, los montos con punto de miles y coma decimal, las liquidaciones vencidas
    y desde cuándo debe (fecha y días).
  - **C04** "Exportar a Excel" baja `morosidad-torre-ficticia-2026-11-18.xlsx` con lo que devuelve la API.
  - **C05** un edificio sin deuda muestra "No hay unidades con deuda vencida".
  - **C06** a 320 px sin scroll horizontal y sin errores de axe.
  - **C07** la KB queda al día según K01.
- Tienen que fallar:
  - **N01** el consejo ve la lista pero no "Exportar a Excel", y la ruta del Excel le da 403.
  - **N02** la vecina no ve "Morosidad" en el menú, y si entra a la pantalla ve que no tiene permiso.
  - **N03** la pantalla no suma ni redondea: el total del resumen es el de la API aunque no coincida con la suma de
    las filas.
- Cierre de la base:
  - **K01** HU-A8 en `knowledge-base/06_funcionalidades.md` nombra la pantalla `/edificios/{id}/morosidad`.
- Guion de demo: entrar como administrador a la Torre Ficticia, abrir "Morosidad" desde el menú, bajar el Excel; a
  320 px; como consejo, ver la lista sin el botón.
- Constructor: Claude Sonnet (`rein-constructor`).
- Aceptación aprobada: `8f4f5fd` (bajo la firma por adelantado del 10a). Contrato en `aceptacion/H-029/CONTRATO.md` (el
  menú, la pantalla, la ruta de Next del Excel, la API falsa con `user_consejo` y el total del resumen un centavo
  distinto de la suma, a propósito, para N03). Comando: `python3 aceptacion/H-029/aceptar.py --sin-regresion`.
  Esperados: 9 en navegador, sin tests de backend; antes de construir, 9 rojos por aserción, 0 por setup.
- Construcción (Sonnet, `0a01b59` y `06b39bb`): "Morosidad" en `secciones.ts` (grupo "Liquidación", `ver_morosidad`);
  `morosidad/page.tsx` y `Pantalla.tsx` (cliente, el link de exportar por `permite(sesion, "exportar_morosidad", id)`),
  cada dato en su `dl`; `morosidad/excel/route.ts` reenvía el `Content-Disposition` de la API sólo si es un nombre
  seguro (si no, `morosidad.xlsx`); `lib/api/morosidad.ts` valida montos, etiquetas y forma; la API falsa en
  `e2e/escenarios-morosidad.ts` con `user_consejo`. **Fuera del contrato, para la demo**: la API falsa contesta
  `GET liquidaciones` con `[]` en 2701 y 2702 (C01 abre esa pantalla), y `Estados.tsx` suma la rama de `ver_morosidad`
  como la de `informar_pago`. Rojo por aserción visto en `secciones.test.ts` y en el link de exportar; el resto de los
  tests de apoyo se escribió con el código hecho. `biome ci`, `tsc` e `impeccable detect --changed` limpios (impeccable
  avisa que el proyecto no tiene `PRODUCT.md` ni `DESIGN.md`).
- Evidencia (24/11/2026): `python3 aceptacion/H-029/aceptar.py --sin-regresion` sobre `06b39bb` desde `8f4f5fd`: **9/9
  en navegador**, C01 a C06, N01 a N03 y SPEC PASA, 0 rojos; C07 con K01 y la ficha en verde, sólo pendiente la
  regresión del cierre.
- Demo y aprobación de Juani: 24/11/2026, recorrida del orquestador con PostgreSQL efímero (roles y migraciones
  reales, la deuda cargada con `registrar_emision` y `registrar_credito`), la API y la web compilada en Chrome.
  Administrador: resumen 4 / 1 / $79.020,00, 1A moroso crítico primero ($30.720, 75 días), 2A bajo el umbral al
  final; Excel bajado desde el botón, abierto en LibreOffice, montos numéricos y total $79.020; consejo sin botón y
  403 en la ruta del Excel; 320 px sin scroll horizontal (Playwright: Chrome no baja de 534 px). Hallazgo anotado
  como deuda en la ficha 10a. **Terminada por Juani el 24/11/2026** ("anotalo como deuda y pasa a terminado").
- Estado: **Terminada** (24/11/2026).

## Cambio de titular (4d, C-07d)

Firmado por el orquestador por delegación escrita de Juani (25/11/2026, D-168), que decide P51 y P52 y el
diseño. Las historias quedan en **Lista** con su demo hecha; Terminada la marca Juani. Rama
`change/cambio-de-titular`. Orden: H-030 → H-031 → H-032 → H-033 → H-034 (cada una usa el registro de la
anterior). En el tablero de Jarvis van como `HU-H030`…

### H-030 · Registrar el cambio de titular

- Objetivo observable: el administrador registra que una unidad cambió de dueño, con fecha, vendedores y
  compradores; los propietarios de la unidad se reemplazan, queda el registro auditado y, si la unidad
  debe, se avisa sin bloquear. Las dos opciones de R32 quedan en su valor por defecto (expensa del mes
  entera, deuda previa en la unidad); las alternativas son H-031 y H-032.
- Incluye: tabla de sólo agregar `cambio_de_titular`, permiso y evento de auditoría
  `registrar_cambio_de_titular`, `POST` y `GET` de los cambios de una unidad, reemplazo de las
  asignaciones de propietario. No incluye: pantallas (H-034), traslados en el libro (H-031, H-032).
- Nivel: **L** (cobros y cuenta corriente, datos de personas).
- **C01**: `POST /complejos/{c}/unidades/{u}/cambios-de-titular` con `fecha`, `vendedores` (ids de persona
  de los propietarios actuales) y `compradores` (nombre y email opcional) responde 201 con el registro:
  id, fecha, vendedores, compradores, `expensa_del_mes: "entera"`, `deuda_previa: "en_la_unidad"`, quién
  lo registró y cuándo.
- **C02**: después, los vendedores ya no son propietarios de la unidad y los compradores sí; los inquilinos
  siguen igual. Un comprador que ya existe como persona en la administración (mismo email) se reutiliza.
- **C03**: queda una fila en `cambio_de_titular` y una auditoría `registrar_cambio_de_titular` con la
  unidad, la fecha y las dos elecciones.
- **C04**: si la unidad tiene deuda, la respuesta trae `aviso` con el monto adeudado como texto y el
  cambio se registra igual; sin deuda, `aviso` es nulo.
- **C05**: con las opciones por defecto el libro no cambia: el estado de cuenta de la unidad es idéntico
  antes y después.
- **C06**: `GET` de la misma ruta lista los cambios de la unidad, el más nuevo primero.
- **N01**: contador, auxiliar, consejo y vecino reciben 403; una unidad de otra administración o fuera de
  alcance, 404.
- **N02**: 422 si un vendedor no es propietario actual de la unidad, si falta vendedor o comprador, si una
  persona está de los dos lados o si la fecha es futura.
- **N03**: un pedido que falla no deja nada: ni fila, ni asignaciones cambiadas, ni auditoría.
- **N04**: `cambio_de_titular` no acepta `UPDATE` ni `DELETE`, y RLS impide verla desde otra administración.
- **K01**: D-168 entra a la base; R32 pasa a "en construcción" en `05_reglas_de_negocio.md`.
- Demo: con el edificio de ejemplo, registrar la venta de una unidad con deuda por API, ver el aviso, el
  padrón con el comprador y el registro en la lista.
- Aceptación: `aceptacion/H-030/`, 40 casos vistos fallar por aserción (0 errores de setup), congelada en
  `abbc1e2` por el orquestador bajo D-168. El `GET` lo usan los mismos roles que registran.
- Construcción (Sonnet): `b2ef21a`, `2fbd97d`, `8526a80`, `b61bd10`. Módulo nuevo `titularidad`, migración `0050`
  con `cambio_de_titular` y `parte_de_cambio_de_titular` (una fila por persona y lado), la acción
  `registrar_cambio_de_titular` es permiso y evento a la vez (como `ajustar_saldo_inicial`). Un comprador que ya
  tiene otra asignación en la unidad da 422.
- Evidencia (25/11/2026, orquestador): `python3 aceptacion/H-030/aceptar.py --sin-regresion` sobre `b61bd10` desde
  `abbc1e2`: 40 esperados, 40 pasados, 0 fallas, 0 errores, 0 skips; C01 a N04 PASA; K01 sin regresión (se corre al
  cerrar el change, D-154). `git diff abbc1e2 HEAD -- aceptacion/` sólo cambia la línea del SHA.
- Demo (25/11/2026, por API, sin Juani): PostgreSQL efímero con roles y migraciones reales hasta `0050`, uvicorn
  real con la identidad inyectada (no hay modo de desarrollo sin Clerk). Venta de la copropietaria de A: 201 con
  `aviso.deuda` `"20200.00"` (igual a `/morosidad`); padrón con la otra propietaria, la compradora y el inquilino
  intactos; huella del libro idéntica antes y después; B con `aviso` nulo; contador 403; fecha futura y vendedor
  inquilino 422 sin cambiar nada; auditoría por cambio; `UPDATE`/`DELETE` negados a `proptech_app`.
- **Deuda** (para otra historia): sin test de dos cambios simultáneos sobre la misma unidad (`FOR UPDATE`); los
  tests de `0050` no se vieron fallar por aserción antes de la tabla; un vendedor con invitación abierta no la
  pierde (sin revisar); los 422 dicen `"valor inválido"` sin motivo legible (lo necesita H-034); no hay ruta HTTP
  del estado de cuenta de una unidad para el personal.
- Estado: **Lista** (25/11/2026). Terminada la marca Juani.

### H-031 · Deuda previa a nombre del vendedor

- Objetivo: con `deuda_previa: "a_nombre_del_vendedor"`, lo impago de los períodos anteriores al mes del
  cambio (capital e interés registrado) pasa a la cuenta de persona del vendedor elegido, con traslados
  enlazados; la unidad queda en cero por ese concepto y esa deuda no genera interés nuevo (D-168.2).
- Incluye: el traslado en el libro (caso de uso en `cuenta_corriente`, como la reimputación), la cuenta de
  persona creada si no existe, la elección del vendedor deudor. No incluye: el cobro y la lectura de la
  cuenta del vendedor (H-033), pantallas (H-034).
- Nivel: **L**.
- **C01**: el `POST` de H-030 acepta `deuda_previa: "a_nombre_del_vendedor"` y `vendedor_deudor` (id de uno
  de los vendedores; si hay un solo vendedor puede omitirse) y responde 201 con `trasladado` (monto en
  texto) y `cuenta_del_vendedor` (id de la cuenta de persona).
- **C02**: lo impago de las obligaciones de períodos anteriores al mes de la fecha del cambio (cada
  componente de capital y el interés registrado) queda en cero en la cuenta de la unidad y la cuenta de
  persona del vendedor debe exactamente lo mismo, al centavo; la suma de las dos cuentas no cambia.
- **C03**: en el libro quedan movimientos `traslado`: un crédito en la unidad por cada obligación
  trasladada y su contraparte en la cuenta del vendedor, enlazados entre sí (`enlazado_a`), cada uno con
  un `operacion_id` derivado del cambio (el libro lo exige único por movimiento).
- **C04**: la deuda del mes del cambio y de los posteriores queda en la unidad; lo ya pagado no se mueve.
- **C05**: emitir el período siguiente no genera interés sobre la cuenta del vendedor; la unidad sólo
  genera interés sobre lo que le quedó.
- **C06**: si la cuenta de persona del vendedor ya existía en el edificio, se reutiliza.
- **C07**: sin deuda previa, el cambio se registra igual, sin movimientos y con `trasladado` `"0.00"`.
- **N01**: 422 si `vendedor_deudor` no está entre los vendedores, o si falta con más de un vendedor; nada
  cambia.
- **N02**: un pedido que falla no deja ni movimientos, ni cuenta nueva, ni fila, ni auditoría.
- **N03**: la cuenta del vendedor no aparece en la morosidad ni en la situación del edificio (D-168.2b).
- **N04**: un pago confirmado después sobre la unidad no se imputa a la deuda trasladada.
- **N05**: un segundo cambio de la misma unidad no vuelve a trasladar lo que ya se trasladó.
- **K01**: lección en `15_lecciones.md` sobre el traslado entre cuentas, o "nada, porque…".
- Demo: unidad con dos meses vencidos e interés; cambio con deuda a nombre del vendedor; la unidad en cero
  por esos meses, el vendedor debiendo lo mismo; emitir el mes siguiente y ver que el vendedor no suma
  interés.
- Aceptación: `aceptacion/H-031/`, 27 casos vistos fallar por aserción (0 errores), congelada en `d4804ac`
  bajo D-168. Contrato: el `aviso` es lo que le queda a la unidad después del traslado; sin deuda previa,
  `trasladado` `"0.00"` y `cuenta_del_vendedor` nulo. Sólo se vio fallar la primera aserción de cada test.
- **Recongelada** en `8601a7a` (25/11/2026): N03 pedía la situación de cuatro cuentas en un mundo que sólo crea la
  de 1A (`IndexError`, error del orquestador, lo frenó el constructor con evidencia). Única diferencia en
  `aceptacion/` desde `d4804ac`: esa aserción y la línea del SHA.
- Construcción (Sonnet): `97dc6e3`, `329dd5a`, `8e16036`, `25feddd`. `trasladar_deuda` en
  `cuenta_corriente/aplicacion/traslado_de_deuda.py`: un crédito `traslado` por obligación y componente en la
  unidad, con `fecha_valor` en el vencimiento (si no, el interés del mes seguía corriendo), y su débito enlazado
  en una obligación contenedora de la cuenta de persona; migración `0051` (`obligacion.de_traslado`, la única con
  capital cero; `ck_mov_traslado`; `cambio_de_titular.vendedor_deudor_id`). L-105 en `15_lecciones.md`.
- Evidencia (25/11/2026, orquestador): `aceptar.py --sin-regresion` sobre `fd8d603` desde `8601a7a`: 27/27, 0
  fallas, 0 errores, 0 skips; H-030 sigue 40/40.
- Demo (25/11/2026, por API, sin Juani): A debía 27.689,20 (septiembre 7.200 + 279,20 tras un pago de 3.000 que
  cubrió primero 200 de interés, octubre 10.000 + 210, noviembre 10.000). Cambio con deuda a nombre de Ana: 201,
  `trasladado` `"17689.20"`, `aviso` `"10000.00"`; A con septiembre y octubre en cero y noviembre intacto; Ana debe
  17.689,20; 8 traslados (4 y 4) que suman igual; `/morosidad` con A sólo en noviembre y sin Ana; al emitir
  diciembre Ana no suma interés y A suma 200 sólo sobre noviembre (igual que la testigo B en ese mes); 422 con
  deudor ajeno o inquilino sin cambiar nada.
- **Deuda**: carrera de dos cambios que crean la misma cuenta de persona (puede quedar una cuenta sin
  movimientos); de los tests propios del constructor sólo el primero se vio fallar; `vendedor_deudor` con
  `en_la_unidad` da 422 (no estaba en el contrato).
- Estado: **Lista** (25/11/2026). Terminada la marca Juani.

### H-032 · Prorrateo por días de la expensa del mes del cambio

- Objetivo: con `expensa_del_mes: "prorrateo"`, la parte del vendedor de la obligación del mes del cambio
  (días anteriores a la fecha) pasa a su cuenta de persona, al registrar si el período ya se emitió o al
  emitirlo si no (D-168.5).
- Incluye: el cálculo por días, el traslado con el mismo mecanismo de H-031, el prorrateo pendiente que se
  aplica al emitir. No incluye: pantallas (H-034).
- Nivel: **L**.
- Decisiones del orquestador (D-168, al acordar): con varios vendedores, la parte va al `vendedor_deudor`
  (mismo campo y misma regla que H-031); sólo se traslada lo impago de la parte del vendedor (lo que la
  unidad ya pagó de esa obligación no se mueve); anular la emisión de un período con prorrateo aplicado se
  rechaza con 409 hasta que una historia posterior resuelva cómo deshacerlo (deuda anotada).
- **C01**: el `POST` acepta `expensa_del_mes: "prorrateo"` y responde 201 con `prorrateo`: `estado`
  (`"aplicado"` o `"pendiente"`), `periodo`, `dias_del_vendedor`, `dias_del_mes` y `parte_del_vendedor` (texto,
  nula si está pendiente).
- **C02**: si el período del mes del cambio ya está emitido, cada componente de esa obligación (ordinaria,
  fondo de reserva, extraordinaria) se parte: el vendedor responde por `componente × días_del_vendedor ÷
  días_del_mes` redondeado medio hacia arriba al centavo, la unidad por el resto; la suma da exacta y la
  parte del vendedor pasa a su cuenta de persona con traslados enlazados.
- **C03**: los días del vendedor son los anteriores a la fecha del cambio (vendió el 11 de noviembre: 10 de
  30); el día del cambio es del comprador. Con fecha el día 1, la parte es `"0.00"` y no hay movimientos.
  Febrero bisiesto cuenta 29 días.
- **C04**: si el período no está emitido, queda `"pendiente"`; al emitir ese período se aplica en la misma
  transacción de la emisión, y el `GET` lo muestra `"aplicado"` con su parte.
- **C05**: prorrateo y deuda a nombre del vendedor juntos en un mismo cambio dan las dos cosas, sin contar
  nada dos veces.
- **C06**: si la unidad ya pagó parte de la obligación del mes, sólo se traslada lo impago de la parte del
  vendedor.
- **N01**: anular la emisión de un período con prorrateo aplicado da 409 y no cambia nada.
- **N02**: un segundo cambio con prorrateo en la misma unidad y el mismo período da 422.
- **N03**: la parte trasladada no genera interés en la cuenta del vendedor al emitir los períodos
  siguientes.
- **N04**: si el traslado al emitir falla, la emisión entera no ocurre (todo o nada).
- **N05**: el interés registrado en la emisión del mes no se prorratea: sólo ordinaria, fondo de reserva y
  extraordinaria. **Deuda**: los cargos particulares entran sumados a la ordinaria de la obligación, así que
  hoy se prorratean con ella; separarlos toca la emisión y queda para otra historia.
- **K01**: R32 con `prorrateo` en `05`, H-032 en la ficha del 4d y la deuda de N01 anotada.
- Demo: vender el 11 de noviembre con prorrateo antes de emitir; emitir noviembre; ver el traslado de 10/30
  al vendedor al centavo y la suma exacta; intentar anular noviembre y ver el 409.
- Aceptación: `aceptacion/H-032/`, 23 casos vistos fallar por aserción (0 errores), congelada en `e451c6c` bajo
  D-168. Contrato: C06 imputa lo ya pagado primero a los días del vendedor (`max(parte - pagado, 0)` por
  componente); `parte_del_vendedor` es lo trasladado; N03 compara con una testigo con tolerancia de $0,05.
- Construcción (Sonnet): `fb6781c`, `a907887`, `1697465`. Dominio puro `titularidad/dominio/prorrateo.py`;
  `trasladar_parte_del_mes` comparte el traslado de H-031; la emisión crea y bloquea las cuentas de los vendedores
  junto con las del edificio (`tambien_bloquear`: bloquear una cuenta nueva después da `BloqueoFueraDeOrden`) y
  aplica los pendientes en la misma transacción; migración `0052` (`prorrateo_de_cambio` único por unidad y
  período, `prorrateo_aplicado`); anular da 409 sólo si el prorrateo trasladó más de cero.
- Evidencia (25/11/2026, orquestador): sobre `1697465`, H-032 23/23 desde `e451c6c`, H-031 27/27 desde `8601a7a`,
  H-030 40/40 desde `abbc1e2`; 0 fallas, 0 errores, 0 skips; en `aceptacion/` sólo cambió la línea del SHA.
- Demo (25/11/2026, por API, sin Juani; noviembre emitido por `GET preliquidacion` + `POST emision` reales): 1A
  vendida el 11/11 antes de emitir → `pendiente`, 10 de 30; al emitir, `aplicado` con `"15500.11"` (10.000,10 +
  500,01 + 5.000,00 sobre 30.000,31 / 1.500,02 / 15.000,01; la unidad con el resto; 3 y 3 traslados enlazados; la
  vendedora sin interés); 1B vendida el 16/11 con noviembre emitido → `aplicado` al momento, 15 de 30,
  `"23250.17"`; anular noviembre → 409 `prorrateo_aplicado` con el libro idéntico; segundo prorrateo → 422.
- **Deuda** (en la ficha 4d): anular con prorrateo aplicado da 409 hasta que una historia resuelva deshacerlo;
  cargos particulares prorrateados con la ordinaria; lo aplicado al emitir no tiene acción de auditoría propia; un
  período emitido sin obligación para la unidad queda `aplicado` en `"0.00"`; posible cuenta de persona vacía si un
  crédito cubre toda la parte; el 422 del segundo prorrateo no dice el motivo; `ensayo-roles.sh` actualizado sin
  ejecutar (corre en el CI de cierre).
- Estado: **Lista** (25/11/2026). Terminada la marca Juani.

### H-033 · La cuenta del vendedor

- Objetivo: el administrador ve el estado de la cuenta de persona del vendedor y registra su cobro, que se
  imputa con R04 (D-168.2c).
- Incluye: lista y detalle de las cuentas de vendedores del edificio, registrar un cobro. No incluye: pantallas
  (H-034), que el vendedor informe su pago desde el portal (no entra, D-168.2c).
- Nivel: **L**.
- Decisiones del orquestador (D-168, al acordar): ver usa el permiso existente `ver_morosidad`; cobrar, el
  existente `confirmar_pago_informado`; un cobro mayor que la deuda se rechaza (el vendedor no tiene expensas
  futuras donde aplicar un crédito a favor).
- **C01**: `GET /api/complejos/{c}/cuentas-de-vendedores` lista las cuentas de persona del edificio con su
  persona (nombre), deuda (texto) y las unidades de los cambios que la originaron, de mayor a menor deuda.
- **C02**: `GET /api/complejos/{c}/cuentas-de-vendedores/{cuenta_id}` da el estado por período y componente,
  el total y los movimientos (traslados y cobros) en orden.
- **C03**: `POST .../cuentas-de-vendedores/{cuenta_id}/cobros` con `importe` (texto) y `fecha` (de la
  transferencia) responde 201; el cobro se imputa con R04 (interés y lo más viejo primero) y la deuda baja
  exactamente el importe.
- **C04**: un cobro igual a la deuda deja la cuenta en cero; uno mayor da 422 sin cambiar nada.
- **C05**: cada cobro queda auditado (`registrar_cobro_de_vendedor`, con cuenta, importe y fecha).
- **N01**: sin el permiso, 403; una cuenta de otro edificio o administración, o una cuenta de unidad, 404.
- **N02**: importe cero, negativo o con más de dos decimales, o fecha futura: 422 sin cambios.
- **N03**: el cobro no toca ninguna cuenta de unidad, no aparece en la bandeja de pagos informados ni en la
  morosidad, y no genera interés al emitir el período siguiente.
- **K01**: R32 y la ficha 4d con H-033; la acción nueva de auditoría en `03_actores_y_roles.md`.
- Demo: después de H-031, ver la cuenta de la vendedora, cobrarle una parte y después el resto hasta cero.
- Aceptación: `aceptacion/H-033/`, 40 casos vistos fallar por aserción (0 errores), congelada en `c309f01` bajo
  D-168. Contrato: leen quienes tienen `ver_morosidad` (contador, auxiliar y consejo incluidos), cobran super admin
  y administrador; el 201 del cobro devuelve el detalle; dos cobros iguales son dos cobros (sin idempotencia).
- Estado: En proceso.

### H-034 · Pantallas del cambio de titular

- Objetivo: desde el padrón, "Cambiar titular" con las dos opciones, el aviso de deuda, el historial de
  cambios y la cuenta del vendedor con su cobro, con impeccable. Criterios: se escriben antes de
  construir.
- Estado: Pendiente.

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
- Construcción (Sonnet, dos tandas verificadas): t1 `0039_ajuste_de_saldo_inicial` y el caso de uso
  `ajustar_saldo_inicial` como obligación nueva (E11, D-156), con la tabla en `cuenta_corriente` porque su
  replay cruza `obligacion` y `cuenta`; t2 la ruta `POST .../unidades/{uid}/ajustes-de-saldo-inicial` y la
  pantalla "Ajustar saldo inicial" con el link desde el padrón. Orden de chequeo: alcance, permiso, unidad
  (404), estado (409), entrada (422). Mutantes de la ruta sobre la validación del cuerpo sobreviven porque
  el libro repite la regla. La pantalla no pasó por impeccable; el layout a 320/1280 px con teclado sólo
  se probó con los e2e de la aceptación.
- Evidencia (12/11/2026): `python3 aceptacion/H-010/aceptar.py --codigo cf4667f` desde `4c3525e`: **56/56 de
  backend y 4/4 en navegador**, C01 a C16 PASA, con la regresión H-004 a H-009, el ensayo de roles, el
  barrido de migraciones y la KB (D-156). 0 rojos.
- Demo y aprobación de Juani: 12/11/2026, API y PostgreSQL reales y la web en Chrome. El ajuste de $5.000 a `1A`
  queda como deuda nueva (agosto intacto), vence el día del ajuste y cobra $90,00 en diciembre (18 días); el
  administrador por edificio recibe 403. **Terminada por Juani el 12/11/2026, con E11 (D-156) aprobado.**
  Deuda chica vista en la demo: el panel de confirmación muestra el importe sin separador de miles
  ("5000,00"); sin permiso, la pantalla del ajuste muestra el formulario y recién avisa al enviar.
