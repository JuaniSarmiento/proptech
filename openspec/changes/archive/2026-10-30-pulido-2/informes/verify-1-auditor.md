# Auditor · verify · intento 1 · pulido-2 (3d)

- **Rol**: auditor (subagente nativo de Claude, role-auditor). Intento 1.
- **Revisión auditada**: `decf692` (rama `revision-3d`), diff `e29e36d...decf692` (33 archivos, 18 commits). PR #3 en GitHub sigue en `b1ec660` (`gh pr view 3`: `headRefOid b1ec660…`, OPEN).
- **Fecha**: 30/10/2026, 12:32 a 12:40 (-03:00). Sin editar código ni informes ajenos; sólo este archivo.
- **Familia**: planner, plan-reviewer, constructor, rompedor y auditor son todos Claude (subagentes nativos). Contexto compartido: los informes en disco. No hay independencia de proveedor; la independencia es de rol y de corrida.

## Fuentes usadas

- Plan: `proposal.md`, `design.md`, `specs/edificios-y-unidades/spec.md`, `specs/pantallas-del-edificio/spec.md`, `tasks.md` (completo, con el historial del orquestador).
- Informes originales: `informes/verify-1-breaker.md`, `informes/propose-2-plan-reviewer.md` (vueltas 1 y 2), `informes/apply-1-constructor.md` (intentos 1 y 2), `informes/verify-2-breaker.md`, `informes/verify-3-breaker.md`. Leídos completos.
- Lecciones: `knowledge-base/15_lecciones.md` en `2e9ec84` (58 lecciones; leí los encabezados de todas y en detalle L-026, L-027, L-035, L-042, L-050, L-051, L-052, L-055).
- KB: ficha 3d de `knowledge-base/12_fichas_de_changes.md` (en `2e9ec84`, líneas 605-645) y "Escalado por riesgo" de `14_forma_de_trabajo.md`.
- Código: el diff completo por nombre; leídos `backend/tests/integracion/test_clave_explicita_invalida.py`, `test_rompedor_clave_patch_grupo.py` (aserciones), y búsquedas sobre `web/e2e/*.spec.ts`.
- Memoria: lista de `openspec/changes/archive/` (antecedentes: `2026-10-19-configuracion-del-edificio`, `2026-10-20-pantallas-del-edificio`, `2026-10-28-pulido-de-la-configuracion`). **Engram no usado** (no disponible en este subagente). No usé `obsidian.md`.

## Contaminación

Leí todos los informes de los otros roles (es mi tarea). Las conclusiones que siguen sobre alcance, frescura, conteo, merge y cableado salen de comandos propios (EVIDENCIA A1 a A8). Lo que tomo de otros sin reproducir lo marco como heredado.

## EVIDENCIA

### A1 · Alcance: nada de producción del backend ni fuera de la web

```
$ git diff --stat e29e36d...decf692 -- backend/src config infra .github      -> (vacío)
$ git diff --name-only e29e36d...decf692 | rg -v '^(web/e2e|web/src|backend/tests|openspec/changes/pulido-2)/'  -> (vacío)
$ (producción web, sin tests ni e2e) -> web/src/app/edificios/[id]/ayuda.ts, web/src/app/page.tsx, web/src/lib/pisos.ts
```
Las tres piezas de producción están en el plan (4.x, 9.x, 3.x). No hay reescritura de algo existente fuera de lo pedido ni código crítico tocado.

### A2 · Frescura: qué cambió después del CI verde (`b1ec660`)

```
$ git diff --name-only b1ec660 decf692 | rg -v '^openspec/'
web/e2e/api-falsa.patch-georef.test.ts
web/e2e/api-falsa.ts
web/src/app/edificios/[id]/ayuda.coherencia.test.tsx
web/src/app/edificios/[id]/ayuda.test.ts
web/src/app/edificios/[id]/ayuda.ts
```
Backend y humo: sus archivos no cambiaron desde `b1ec660`; el run 40790724706 sigue cubriéndolos. Playwright (job `web`) **no**: `api-falsa.ts` es el servidor de todos los e2e y cambió.

### A3 · CI reutilizado, verificado por mí

```
$ gh run view 40790724706 --json headSha,conclusion,jobs
headSha b1ec6607…, conclusion success; jobs shellcheck, secretos, humo, web, backend: success
```
Sobre `decf692` no hay ningún run (la rama no está empujada al PR).

### A4 · Conteo independiente sobre `decf692`

```
$ (web) npx vitest run        2026-10-30T12:32:59-03:00 · decf692
 Test Files  85 passed (85)
      Tests  597 passed (597)
$ (web) npx tsc --noEmit      2026-10-30T12:34:08-03:00 -> exit 0
$ (web) npx biome ci .        -> Checked 222 files. No fixes applied. 7 warnings, 6 infos. exit 0
```
Coincide con el constructor (85 / 597). El CI sobre `b1ec660` contó 84 / 585: la diferencia (+1 archivo `ayuda.coherencia.test.tsx`, +12 tests) cuadra con 4.3, 11.1 a 11.6. La cifra 72 / 454 de la 10.1 de Gianfranco no coincide con ninguna revisión observada y no tiene salida guardada.

### A5 · Merge contra `main` real

```
$ git diff --name-only e29e36d 2e9ec84  -> AGENTS.md, CHANGES.md, CLAUDE.md, knowledge-base/{09,12,14}
$ git merge-tree --write-tree 2e9ec84 decf692 -> merge limpio
```
`2e9ec84` no toca archivos del 3d. Sí toca `12_fichas_de_changes.md`, que la 10.4 va a editar al archivar: hay que hacerlo sobre `2e9ec84` o posterior.

### A6 · Choque con el PR #4 (motivo de la 1.2)

```
$ gh api repos/JuaniSarmiento/proptech/pulls/4 --jq .changed_files  -> 71 (head 2f81682)
$ git merge-base e29e36d 2f81682 -> 5c6d84c
$ git diff --name-only e29e36d...2f81682 | rg "e2e|api-falsa"   -> (vacío)
```
En su head actual, el PR #4 **no toca** `web/e2e/api-falsa.ts` ni ningún archivo de `web/e2e`. La afirmación "el PR #4 también toca `api-falsa.ts`" no la pude confirmar. Los conflictos de `merge-tree 2f81682 decf692` son todos de archivos que no son del 3d (`test_libro_rollback.py`, `test_fronteras_de_modulos.py`, `ensayo-roles.sh`, KB 09 y 15): vienen de que el PR #4 parte de `5c6d84c`, no del 3d.

### A7 · Cableado de las rutas nuevas de la API falsa

```
$ rg -n "PATCH|georef|/grupos/" web/e2e/*.spec.ts -> (vacío)
$ rg -n "de 7" web/e2e  -> pulido.spec.ts:151 /de 7 pasos/ (regex, no depende de 0/4/6)
```
Ningún spec de Playwright usa el `PATCH` de edificio, el de grupo ni Georef. Los cambios de `api-falsa.ts` posteriores a `b1ec660` (422 a `PATCH` sin cuerpo o con id no UUID, nombres de Georef) no los alcanza ningún e2e existente: riesgo bajo de que el job `web` cambie, pero no está medido. Y la tarea 2.5 (los specs que motivan el change) **no existe** en el diff: no es "Playwright lo juzga el CI", es que el spec no se escribió.

### A8 · TDD del trabajo original de Gianfranco

```
$ git log --format='%h %ad' e29e36d..b1ec660  -> 302fef4 a 4db2227, todos 2026-10-28 13:32:33/34 (reescritos en bloque)
$ git show --stat b98cad1  -> pisos.test.ts, Pantalla.test.tsx, Pantalla.rompedor.test.tsx y pisos.ts en el mismo commit
$ tasks.md 3.x, 4.1, 4.2, 5.x, 6.1, 7.1, 8.1, 9.x -> sin comando, hora ni salida de RED/GREEN
```
No hay forma de comprobar que el RED de esas tareas fue anterior a la producción. Lo que sí hay es evidencia sustituta independiente: los 14 mutantes del rompedor intento 1 (E3, 13 muertos; el que sobrevivía, A1, quedó muerto en el intento 2 como B7). Esa evidencia prueba que las aserciones vigilan, no el orden RED antes de GREEN.

### A9 · Aserción vacía en el test de clave inválida

```
$ python3 -c 'import json; print("abc\n" in json.dumps({"x":"abc\n"}))'  -> False
test_clave_explicita_invalida.py:23 "abc\n" ; :58 assert clave not in respuesta.text
test_rompedor_clave_patch_grupo.py:10 parametriza "abc\n" y no comprueba loc
```
Confirma el JUICIO del rompedor: para `"abc\n"` el `not in` pasa aunque el valor vuelva (el JSON lo escapa). Para las otras claves la aserción vigila. No lo corrí contra la API real (sin Docker); es lectura más la prueba de escape.

## Contraste por punto

| Punto | Plan | Estado en `decf692` | Fuente |
|---|---|---|---|
| Orden de pisos (3.x) | SS<n>..SS1, PB, 1..N | hecho; mutante P1 muerto | breaker-1 E3, A4 |
| Ayuda 4 de 7 / 6 de 7 (4.3) | spec corregida, opción (a) | hecho; B8/B9 muertos | apply-1, breaker-2 |
| Día fuera de rango (5.x) | pantalla y backend | hecho; tests nacieron verdes porque el comportamiento ya existía (sin cambio de producción) | breaker-1 lente 3 |
| Clave inválida (6.1) | integración | hecho; verde en CI `b1ec660`; aserción débil para `"abc\n"` (A9) | A3, A9 |
| CSP (7.1) | unitario del filtro | hecho; M1 a M3 muertos | breaker-1 E3 |
| axe por estado (8.1) | 4 pantallas, vacío y error | hecho en jsdom; X1 muerto; 8.2 sin navegador | breaker-1 E3 |
| Raíz `/` (9.x) | redirect, **no arranca sin Juani** (design, Decisión 3 y Riesgos) | construido sin la confirmación | tasks 9.x |
| API falsa (2.1 a 2.4, 11.x) | PATCH, Georef, 422 como la real | hecho; F1 a F7 cerradas | breaker-2, breaker-3 |
| e2e de Playwright (2.5) | specs de editar ubicación y desactivar grupo | **no escritos** | A7 |
| Aviso a Emiliano (1.2) | **sin respuesta, el grupo 2 no arranca** | grupo 2 hecho sin respuesta | tasks 1.2, A6 |

## Informes requeridos (MEDIUM, cinco roles)

| Informe | Estado |
|---|---|
| Planificador del plan original (Gianfranco, 28/10) | **falta** |
| Planificador de la corrección por F4 (30/10) | **falta** (la corrección está en el diff del plan y la revisó el plan-reviewer, pero no hay informe del planner) |
| Revisor del plan original (`propose-1-…`) | **falta**: `propose-2` revisa sólo la corrección por F1 a F6 |
| Constructor original (Gianfranco, tareas 1 a 10.1) | **falta**: ni informe ni RED/GREEN en `tasks.md` (A8) |
| Rompe-y-audita de la 10.2 | **falta** en la rama (lo dice el propio orquestador) |
| `apply-1-constructor.md`, `propose-2-plan-reviewer.md`, `verify-1/2/3-breaker.md` | presentes, vigentes para lo que cubren |
| `LEEME.md` (índice con autor, ejecutor, familia, revisión y faltantes) | **falta** |

## JUICIO

Autor: auditor (Claude, intento 1). Comparé plan, diff, tests e informes contra mis propias corridas (A1 a A9). Confianza alta en lo técnico: el código entregado hace lo que el plan pide en los puntos construidos, no toca producción del backend, los tests vigilan (mutantes independientes del rompedor, más mi conteo 85 / 597 verde con typecheck y lint) y no hay ninguna falla reproducida abierta. No encontré defecto de código que bloquee.

Lo que impide APROBADO no es código: es evidencia y decisiones que faltan.

1. **Informes faltantes** (tabla de arriba). El contrato no deja aprobar con originales faltantes. El orden RED antes de producción del trabajo original no se puede recuperar (A8); lo que se puede es declararlo y que Juani lo acepte por escrito como deuda justificada, con la evidencia sustituta de los mutantes. Un resumen del orquestador no reemplaza los originales faltantes.
2. **Tareas abiertas sin disposición**: 1.2, 2.5, 8.2, 9.1/9.2 (confirmación de la raíz), 10.3, 10.4. Dos son desvíos del plan propio, no sólo pendientes: la raíz `/` se construyó aunque el design decía que no arrancaba sin Juani, y el grupo 2 se hizo aunque la 1.2 decía que sin la respuesta de Emiliano no arrancaba. Hoy el riesgo de choque con el PR #4 no se materializa (A6), pero el desvío necesita que alguien con autoridad lo ratifique.
3. **La ficha 3d contra el orden de pisos**: la ficha se contradice sola ("SS1 arriba de PB" en Entra, `PB, 1..N, SS1..SSN` en Terminado cuando). El orden de Gianfranco es razonable y cumple la primera frase, pero el proyecto dice que ante una contradicción con la KB se para y se pregunta a Juani. Lo que hay que hacer: Juani elige el orden y lo deja escrito en `tasks.md`; al archivar (10.4) se agrega una decisión nueva en `09_decisiones_y_supuestos.md` y se reescribe el "Terminado cuando" de la ficha sobre `2e9ec84` o posterior. No se edita la decisión vieja.
4. **CI sobre el SHA final**: con los cambios de A2, el job `web` (Playwright) de `b1ec660` ya no es vigente. No alcanza con lo que corrimos local. Esto es una condición de merge, no una falla: el merge espera los cinco jobs verdes sobre el SHA empujado.

Sobre 2.5: el "Terminado cuando" de la ficha **sí** se cumple sin los specs de Playwright (pide que la falsa responda los PATCH y simule Georef). La tarea 2.5 la agregó el propio plan, y el porqué del change es justamente que esos flujos no tienen e2e. Que quede como deuda es defendible, pero lo decide Juani, no el orquestador ni yo.

## SUPOSICIÓN

- No corrí Playwright, pytest de integración ni nada contra la API real o Clerk (sin Docker ni Clerk en este subagente). Lo que digo del backend se apoya en el CI de `b1ec660`, verificado por `gh` (A3), y en que sus archivos no cambiaron (A2).
- Las sondas contra los modelos reales de la API (breaker-1 E2, breaker-2 E4) son heredadas: no las repetí. Los mutantes del rompedor y del constructor tampoco los repetí; conté los tests y verifiqué alcance, frescura y merge.
- A6 mira el head actual del PR #4 (`2f81682`); si Emiliano empuja cambios a `web/e2e`, el choque puede aparecer.
- S1 a S4 del rompedor intento 1 (CSP con otro formato de Clerk, pisos no enteros, sesión sin token, piso fuera del vocabulario) siguen como sospechas sin reproducir; no las promuevo.
- No miré la raíz `/` ni las pantallas en un navegador real (8.2, 9.2).

## Veredicto

**BLOQUEANTES**. Ninguno es una falla de código; todos se cierran con decisiones escritas, el índice de informes y el CI. Intento 1 de 3 en esta compuerta.

### Bloquea el merge (técnico)

- **BM-1 · CI verde sobre el SHA final.** Empujar `revision-3d` al PR #3 y leer los cinco jobs (shellcheck, secretos, humo, web, backend) del run sobre ese SHA exacto. El de `b1ec660` no cubre `api-falsa.ts` ni `ayuda.ts` (A2). Responsable: orquestador. Ningún job pendiente, saltado ni cancelado cuenta como verde (L-042).

### Necesita una decisión de Juani (impide APROBADO; cada respuesta, escrita y con fecha en `tasks.md`)

- **BJ-1 · Informes faltantes y TDD no comprobable del trabajo original.** Faltan el planificador (original y corrección), el revisor del plan original, el constructor original con su RED/GREEN y la 10.2 (tabla de informes). El orquestador arma `informes/LEEME.md` declarando cada faltante, autor y revisión. Juani elige: aceptarlo como deuda justificada (con los mutantes del rompedor como evidencia sustituta, A8) o pedir una revisión del plan completo antes de cerrar. Responsable de la evidencia: orquestador; de la decisión: Juani.
- **BJ-2 · La raíz `/` (9.1, 9.2).** Confirmar el redirect (`/edificios` con sesión, `/ingresar` sin sesión) o pedir otra cosa. Se construyó antes de la confirmación, contra lo que decía el design. Si cambia, vuelve al planificador y al constructor por TDD, y después rompedor y auditor sobre lo nuevo.
- **BJ-3 · Coordinación con Emiliano (1.2).** Ratificar que el grupo 2 se haya hecho sin su respuesta o pedir el aviso antes de mergear. Dato a favor: el PR #4 actual no toca `web/e2e` (A6).
- **BJ-4 · e2e de Playwright (2.5).** Construirlo ahora (vuelve al constructor por TDD, y después rompedor y auditor) o pasarlo a deuda con dueño. Mi recomendación: deuda para C-26 `pulido-web-3` o C-23 `humo-y-ci`, porque la ficha queda cumplida sin él.
- **BJ-5 · Navegador real (8.2).** Hacer el recorrido a 1280 y 320 px o aceptarlo como deuda con dueño. axe en jsdom no mide contraste ni ancho (L-026).
- **BJ-6 · Orden de pisos contra la ficha.** Juani elige el orden (el de Gianfranco u otro). Al archivar va como decisión nueva en `09` y se reescribe el "Terminado cuando" de la ficha 3d sobre `2e9ec84` o posterior.

Cerrados BM-1 y BJ-1 a BJ-6 sin cambios de código, alcanza con que el auditor relea `tasks.md`, `LEEME.md` y el CI del SHA nuevo para emitir el veredicto. Si alguna decisión cambia código (BJ-2, BJ-4), lo afectado pasa otra vez por constructor, rompedor y auditor.

## DEUDA

| id | qué | evidencia | dueño propuesto |
|---|---|---|---|
| DA-1 | La ayuda del resumen no se sincroniza con el cálculo de `lectura.py`; si cambia, el texto queda viejo sin test rojo | PR2-1, `tasks.md` (decisión del orquestador 30/10) | C-26 `pulido-web-3` (ya asignado) |
| DA-2 | La API falsa valida sólo tipos en los PATCH nuevos: acepta `pisos: 0`, `subsuelos: 6`, `nombre: ""`, `metodo: "raro"`, clave mal formada, que la real rechaza con 422. Contradice el objetivo del design ("rechaza lo que la real rechazaría"), con el mismo criterio que ya tenían los POST | breaker-1 E2, lente 1 | el primer change que escriba un e2e sobre esas rutas (2.5 o quien la herede) |
| DA-3 | `PATCH /api/unidades/{id}` y `PATCH /api/categorias/{id}` siguen sin declararse en la API falsa | breaker-1 lente 2 | el primer change con e2e de esas pantallas |
| DA-4 | Un POST a `/api/complejos/{no-uuid}/…` no lo rechaza la falsa (mutante C3 sobrevive); hueco previo al 3d | breaker-3 JUICIO | igual que DA-2 |
| DA-5 | `assert clave not in respuesta.text` es vacía para `"abc\n"`, y el test de PATCH de grupo no comprueba que el 422 nombre `clave` | A9, breaker-1 lente 3 | C-28 `revisiones-independientes` |
| DA-6 | `comprobaciones.spec.ts` dice "la portada real" y ahora mide `/ingresar`; la raíz `/` no tiene ningún test de navegador | breaker-1 lente 3, tasks 9.2 | quien cierre BJ-5 |
| DA-7 | Las cifras de la 10.1 (72 / 454 y "41 fallas de Windows") no tienen salida guardada ni coinciden con ninguna revisión observada | A4 | se cierra con BJ-1 (declarado en `LEEME.md`) |
| DA-8 | Sospechas sin reproducir S1 a S4 del rompedor intento 1 | breaker-1 SUPOSICIÓN | S1 a C-29 `base-y-rls` o al 15 (CSP); S4 a C-26 |

Más las que salgan de BJ-1, BJ-4 y BJ-5 si Juani elige deuda.

## LECCIONES (candidatas, número a asignar al archivar en `15_lecciones.md`)

- **Un número copiado a un texto de ayuda se valida contra el cálculo que lo produce, no contra el texto viejo.** El 3d cambió "de 6" por "de 7" y dejó "arranca en 0" sin mirar `lectura.py`, y la spec lo exigía (F4). Regla: si una ayuda cita un valor que calcula el sistema, el test lo deriva del render o del cálculo, y si no puede, la spec lo declara como deuda.
- **Una tarea con "no arranca sin X" necesita que alguien la frene, no sólo que lo diga.** La raíz `/` y el grupo 2 se construyeron sin la confirmación que el propio plan exigía. Regla: una tarea bloqueada por una persona queda sin casilla en `tasks.md` hasta que la respuesta esté escrita, y el constructor la saltea.
- **Un commit que junta test y producción no prueba el RED.** Las tareas originales del 3d llegaron reescritas en bloque, con el test y el código en el mismo commit y sin salida de RED guardada (A8). Regla: el RED se guarda con comando, hora y salida en `tasks.md` antes del commit de producción, porque después no se puede reconstruir.
