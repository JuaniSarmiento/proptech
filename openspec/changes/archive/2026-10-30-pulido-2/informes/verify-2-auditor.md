# Auditor · verify · intento 2 · pulido-2 (3d)

- **Rol**: auditor (subagente nativo de Claude, role-auditor). Intento 2 de 3 en esta compuerta (el 1 dio BLOQUEANTES, `verify-1-auditor.md`, que queda intacto).
- **Revisión auditada**: `ee47c3f` (rama `revision-3d`, también head del PR #3). Sobre `decf692` sólo agrega `informes/LEEME.md`, `informes/verify-1-auditor.md` (`dbb05b7`) y la sección "Decisiones de Juani sobre los bloqueantes del auditor" en `tasks.md` (`ee47c3f`). Ningún archivo de código cambió.
- **Fecha**: 30/10/2026, 12:45 a 12:58 (-03:00).
- **Familia**: todo Claude, igual que en el intento 1.

## Fuentes usadas

- `git diff decf692..ee47c3f` completo (LEEME.md y sección nueva de tasks.md, leídos enteros).
- `verify-1-auditor.md` (mío, intento 1).
- CI: runs 41082416501 (`dbb05b7`) y 41084509723 (`ee47c3f`), logs de los jobs `secretos`, `backend` y `web` por la API de GitHub.
- `.github/workflows/ci.yml` (job `secretos`), ancestría de `a6bb954`.
- Memoria: la misma del intento 1; Engram no usado.

## Contaminación

El orquestador me resumió el falso positivo y su reproducción local. No me apoyé en eso: lo verifiqué con el log del CI, la ancestría del commit y gitleaks propio (B3 a B5). Las decisiones de Juani las conozco sólo por cómo las transcribió el orquestador en `tasks.md` (ver SUPOSICIÓN).

## EVIDENCIA

### B1 · Sólo docs desde la revisión auditada

```
$ git diff --stat decf692..ee47c3f
 openspec/changes/pulido-2/informes/LEEME.md        |  23
 openspec/changes/pulido-2/informes/verify-1-auditor.md | 192
 openspec/changes/pulido-2/tasks.md                 |  13
$ git diff --name-only dbb05b7 ee47c3f -> openspec/changes/pulido-2/tasks.md
```
El conteo propio del intento 1 (vitest 85 / 597, tsc y biome sobre `decf692`) sigue vigente para el código.

### B2 · Disposición de cada bloqueante del intento 1

| Bloqueante | Dónde queda | Estado |
|---|---|---|
| BJ-1 informes faltantes | `LEEME.md` declara cada faltante con commit; `tasks.md`: deuda justificada con evidencia sustituta | cerrado |
| BJ-2 raíz `/` | `tasks.md`: confirmado, sin cambio de código | cerrado |
| BJ-3 aviso a Emiliano | `tasks.md`: ratificado; se le avisa al rebasar el PR #4 | cerrado |
| BJ-4 Playwright 2.5 | `tasks.md`: deuda de C-26 `pulido-web-3` | cerrado como DEUDA |
| BJ-5 navegador real 8.2 (y DA-6) | `tasks.md`: deuda de C-26 | cerrado como DEUDA |
| BJ-6 orden de pisos | `tasks.md`: queda el orden de altura; decisión nueva en `09` y ficha reescrita al archivar | cerrado; pendiente de cierre documental |
| BM-1 CI sobre el SHA final | ver B3 a B6 | cerrado salvo `secretos` |

`LEEME.md` cumple lo pedido (autor, ejecutor, familia, revisión y faltantes). Lo marca como índice que no reemplaza los originales.

### B3 · CI sobre `dbb05b7` (mismo código que `ee47c3f`)

```
$ gh run view 41082416501   (12:55:28 -03:00)
completed  humo=success  secretos=failure  backend=success  shellcheck=success  web=success
backend log: "4279 passed, 1 xfailed, 19 warnings in 1011.98s" (el "1 failed" posterior es infra/ci/canario.sh, roto a propósito)
web log:     vitest "Test Files 85 passed (85)", Playwright "175 passed (4.0m)" (el "1 failed" posterior es src/canario-roto.test.ts, a propósito)
```
Los 85 archivos de vitest del CI coinciden con mi corrida del intento 1. Playwright, que antes no estaba vigente para `api-falsa.ts`, ahora está verde sobre ese código.

### B4 · El hallazgo de `secretos`

```
job secretos, run 41082416501:
Secret:  complejo=api_edificio.otro   RuleID: generic-api-key
File:    backend/tests/integracion/test_gastos.py   Line: 120
Commit:  a6bb95442afacd2af1774445eb5b3f78bd173104   Author: cachii   Date: 2026-10-29T05:48:23Z
551 commits scanned. leaks found: 1
ci.yml: checkout con fetch-depth: 0 y `gitleaks git --config /repo/.gitleaks.toml -v .`
```
El "secreto" es una expresión de test (`complejo=api_edificio.otro`): falso positivo.

### B5 · De quién es el commit

```
$ git branch -a --contains a6bb954           -> remotes/origin/change/gastos-y-cargos   (PR #4)
$ git merge-base --is-ancestor a6bb954 ee47c3f -> 1 (no es ancestro del 3d)
$ git merge-base --is-ancestor a6bb954 2e9ec84 -> 1 (no está en main)
$ git merge-base --is-ancestor a6bb954 2f81682 -> 0 (está en el head del PR #4)
$ gitleaks git --config .gitleaks.toml --log-opts="e29e36d..ee47c3f" .   12:52:03 -> no leaks found
$ gitleaks git --config .gitleaks.toml --log-opts="--all" .                -> leaks found: 1
```
El 3d no introduce el hallazgo. Lo ve porque `fetch-depth: 0` trae todas las ramas del repo y gitleaks las recorre a todas.

### B6 · CI sobre `ee47c3f`

```
$ gh run view 41084509723  (12:55:28)
in_progress  secretos=failure  shellcheck=success  humo=success  backend, web en curso
$ gh api …/branches/main/protection -> 404 "Branch not protected"
```
Mientras exista la rama del PR #4 con `a6bb954`, cualquier run de cualquier rama va a dar `secretos` rojo, también `main` después del merge.

## JUICIO

Autor: auditor (Claude, intento 2). Confianza alta.

- **Los bloqueantes del intento 1 quedan cerrados** (B2). Ninguno requería código. Las decisiones quedaron escritas y con fecha en `tasks.md`, y en MEDIUM no hace falta firma (D-094, D-111).
- **El falso positivo no bloquea al 3d: es DEUDA del PR #4.** El commit no está en la historia del 3d ni en `main`. Sobre el rango propio del 3d gitleaks no encuentra nada (B5), y arreglarlo desde el 3d (tocando `.gitleaks.toml`) sería ampliar el alcance con un cambio de seguridad del CI que nadie pidió. Pero **no lo cuento como verde**: un job fallado no es éxito. Mergear con `secretos` en rojo es una decisión de publicación de Juani. Además, `main` va a quedar con ese job rojo en todos los runs hasta que se arregle, para todos los PRs, así que conviene arreglarlo antes de o junto con el merge.
- **Cómo se arregla (para el dueño)**: como el commit ya está en la historia de la rama, un `# gitleaks:allow` en un commit nuevo no alcanza. Las opciones son una entrada en `.gitleaksignore` con el fingerprint del hallazgo (`a6bb954…:backend/tests/integracion/test_gastos.py:generic-api-key:120`), una allowlist acotada en `.gitleaks.toml`, o reescribir ese commit en la rama del PR #4. Cualquiera de las tres tiene que verificarse con `gitleaks git --log-opts="--all"` sin hallazgos y sin dejar pasar otros.
- **CI vigente para el código**: backend, web (vitest y Playwright), humo y shellcheck en verde sobre `dbb05b7`, con el mismo código que `ee47c3f` (B1, B3). El run de `ee47c3f` sigue en curso; por la regla de publicación, antes de mergear hay que leerlo terminado.

## SUPOSICIÓN

- No vi el chat donde Juani respondió. Tomo como su decisión lo que el orquestador transcribió en `tasks.md` ("si" para BJ-2, "vamos con tus recomendados" para el resto). Si la transcripción no es fiel, este veredicto cae.
- No esperé al run 41084509723 terminado. Lo doy por equivalente al de `dbb05b7` porque el código es idéntico (B1), pero queda como condición de merge.
- No miré `.gitleaksignore` ni el contenido de `.gitleaks.toml`; las tres formas de arreglo son de la documentación de gitleaks 8.x, no las probé.

## Veredicto

**APROBADO** (intento 2), para el contenido del 3d en `ee47c3f`. No hay fallas reproducidas abiertas, los bloqueantes del intento 1 tienen disposición escrita y el CI del código está verde salvo un hallazgo ajeno.

### Condiciones de merge (no son bloqueantes del auditor; las cumple el orquestador o las decide Juani)

1. **Run 41084509723 sobre `ee47c3f` terminado**, con backend, web, humo y shellcheck en `success`. Si cualquiera de esos cuatro falla, el veredicto se reabre.
2. **`secretos` rojo por `a6bb954` (PR #4)**: un job fallado no es verde. Hay dos salidas, y elige Juani: (a) arreglar primero el falso positivo (Emiliano en el PR #4, o un change mínimo propio sobre `main`) y mergear con los cinco jobs verdes; (b) mergear el 3d con `secretos` en rojo, dejando escrito en `tasks.md` que el hallazgo es ajeno (B4, B5). Recomiendo (a), porque con (b) `main` queda rojo para todos.
3. **Cierre documental al archivar (10.3, 10.4)**: decisión nueva en `09` por el orden de pisos, ficha 3d reescrita sobre `2e9ec84` o posterior, `CHANGES.md` con C-22 en `[x]`, deuda llevada a la ficha de C-26 y C-28, y lecciones numeradas en `15`. Al archivar, el texto de 9.1 y 9.2 ("pendiente de confirmar con Juani") se actualiza a la confirmación del 30/10.

APROBADO no autoriza push, merge ni ampliar el alcance.

## DEUDA

Queda la del intento 1, con estos cambios:

| id | qué | dueño |
|---|---|---|
| DA-1 | La ayuda no se sincroniza con `lectura.py` | C-26 `pulido-web-3` |
| DA-2 | Los PATCH de la API falsa validan sólo tipos, no rangos | el primer change con e2e sobre esas rutas, hoy C-26 (hereda la 2.5) |
| DA-3 | `PATCH /unidades/{id}` y `/categorias/{id}` no están declarados en la API falsa | el primer change con e2e de esas pantallas |
| DA-4 | La API falsa no rechaza un POST a `/complejos/{no-uuid}/…` | igual que DA-2 |
| DA-5 | La aserción de clave es vacía con `"abc\n"`; el test del PATCH no comprueba `loc` | C-28 `revisiones-independientes` |
| DA-6 | La raíz `/` no tiene test de navegador; los títulos de `comprobaciones.spec.ts` | C-26 (decisión BJ-5) |
| DA-7 | — | **cerrada** con BJ-1 (`LEEME.md`) |
| DA-8 | Sospechas S1 a S4 sin reproducir | S1 a C-29 o al 15; S4 a C-26 |
| DA-9 | Tarea 2.5: e2e de Playwright de ubicación y grupo | C-26 (decisión BJ-4) |
| DA-10 | Tarea 8.2: navegador real a 1280 y 320 px | C-26 (decisión BJ-5) |
| DA-11 | Informes originales faltantes y rojo no comprobable del trabajo de Gianfranco | aceptada (BJ-1); sin dueño de código |
| DA-12 | `secretos` rojo en todo el repo por el falso positivo `generic-api-key` de `a6bb954` (`test_gastos.py:120`) | PR #4 (Emiliano), o C-23 `humo-y-ci` si Juani prefiere arreglarlo sobre `main` |

## LECCIONES

Las tres candidatas del intento 1, más esta:

- **Con `fetch-depth: 0`, gitleaks recorre todas las ramas: el falso positivo de un PR pone en rojo el job `secretos` de todos los demás.** El 3d dio rojo por un commit del PR #4 que no está en su historia (B4, B5). Regla: ante un rojo de `secretos`, primero se comprueba la ancestría del commit (`git merge-base --is-ancestor`) y se corre gitleaks sobre el rango propio. El arreglo lo hace el dueño del commit, y un `gitleaks:allow` agregado después no cura la historia.
