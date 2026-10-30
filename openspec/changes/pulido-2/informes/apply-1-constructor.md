# apply-1 · constructor · pulido-2 (3d)

- Autor: constructor (subagente nativo de Claude, role-constructor), intento 1 de correcciones.
- Revisión de partida: `b1ec660` más el diff sin commit del rompedor y del planner.
- Revisión entregada: `ef1d8e9` (rama `revision-3d`). Commits: `b5d7cbb` (4.3), `ef1d8e9` (11.1 a 11.5) y el commit `docs(openspec)` con plan, informes y tasks.md encima.
- Tareas: 4.3, 11.1, 11.2, 11.3, 11.4, 11.5. Nada más.
- Nivel: MEDIUM (TDD con triangulación de bordes y errores).

## Fuentes leídas

- `openspec/changes/pulido-2/tasks.md` (4.3, 11.x, decisiones PR2-1 y estado).
- `openspec/changes/pulido-2/specs/pantallas-del-edificio/spec.md`, escenario "Ejemplo de la ayuda".
- `openspec/changes/pulido-2/informes/verify-1-breaker.md`: sólo F1 a F6 y la fila del mutante A1.
- `knowledge-base/15_lecciones.md`: L-027, L-049, L-050, L-051, L-052 (encabezado y "Qué pasó"/"Regla").
- Código: `web/e2e/api-falsa.ts`, `web/e2e/api-falsa.patch-georef.test.ts`, `web/e2e/api-falsa.rompedor-3d.test.ts`, `web/src/app/edificios/[id]/ayuda.ts`, `ayuda.test.ts`, `ayuda.rompedor-3d.test.tsx`, decoradores de `backend/src/proptech_api/complejos.py`, `backend/tests/integracion/test_resumen_puesta_a_punto.py:32-48`, entradas de `config/georef/*.json` para los ids simulados.

## Contaminación

Leí el informe del rompedor (F1 a F6) porque es la entrada de las tareas; sus tests RB3D-1 a RB3D-4 fueron mi RED de partida. No leí `propose-2-plan-reviewer.md` más allá de lo citado en tasks.md. Las conclusiones de abajo salen de corridas propias.

## EVIDENCIA

Todos los comandos desde `web/` del worktree. Logs completos de la corrida final en el scratchpad de la sesión (fuera del repo).

- Baseline 12:19:30, `pnpm exec vitest run` de los 5 archivos enfocados: 5 failed (RB3D-1 x2, RB3D-2, RB3D-3, RB3D-4) / 56 passed. Coincide con lo que reportó el rompedor.
- 4.3 RED 12:20:00 (`ayuda.test.ts`, `ayuda.coherencia.test.tsx`): 2 failed por aserción (`to contain 'arranca en 4 de 7 pasos'`; `expected '0 de 7 pasos' to be '4 de 7 pasos'`). GREEN 12:20:09 `vitest run "src/app/edificios/[id]/"`: 136 passed.
- 11.1 a 11.3 RED 12:21:17 (`api-falsa.patch-georef.test.ts`): 4 failed por aserción (`expected 200 to be 422` x3; F3 con los 4 nombres distintos). GREEN 12:21:38 con `api-falsa.test.ts`: 62 passed.
- Mutantes para aserciones nacidas verdes, todos revertidos con `diff -q` idéntico: M-B1 (no JSON en grupos), M-B2 (no JSON en complejos; primer intento cayó por timeout de 5 s, descartado por no ser aserción y rehecho: `expected 200 to be 422`), M-B3/M-B4 (`{}` rechazado: rojo también el test original "un cuerpo vacío es válido"), M-B5 (UUID sensible a mayúsculas).
- 11.4: A1 antes de endurecer, 12:22:24: 62 passed (sobrevive). Con `toEqual({ id })`, A1 12:22:37: rojo `expected { …(10) } to deeply equal { Object (id) }`. Revertido: 62 passed.
- 11.5 (documental), 12:23:00: las nueve citas `complejos.py:N` apuntan al decorador `@router` de la función nombrada (verificado con `awk 'NR==N'`); `editar_edificio`/`editar_grupo` ya no aparecen.
- Corrida completa sobre `ef1d8e9`: `pnpm test` 12:23:26 -> 85 archivos, 595 passed, exit 0. `pnpm typecheck` 12:24:27 -> exit 0. `pnpm lint` (biome ci) 12:24:35 -> exit 0, 7 warnings y 6 infos en `acceso-pantallas.spec.ts`, `api-falsa.test.ts:359`, `personal.spec.ts`, `vecinos-del-padron.spec.ts`, `edificios/page.tsx`, `sesion.test.ts`: ninguno en archivos tocados.

## Cambios

- `web/src/app/edificios/[id]/ayuda.ts`: el ejemplo dice "arranca en 4 de 7 pasos" (ubicación, grupos, categorías e intereses y vencimiento hechos al crear) y "queda en 6 de 7" tras unidades con piso y coeficientes.
- `web/src/app/edificios/[id]/ayuda.test.ts`: exige "arranca en 4 de 7 pasos", "6 de 7" y ningún "0 de 7"/"2 de 7"; se conserva el de "de 6".
- `web/src/app/edificios/[id]/ayuda.coherencia.test.tsx`: RB3D-4 reubicado (antes `ayuda.rompedor-3d.test.tsx`), encabezado actualizado.
- `web/e2e/api-falsa.ts`: PATCH sin cuerpo -> 422 `missing ["body"]` en `/complejos/{id}` (sólo PATCH; POST igual) y `/grupos/{id}`; `/grupos/{id}` con id no UUID -> 422 `uuid_parsing ["path","grupo_id"]`; nombres de Georef reales (Guaymallén, Colonia Segovia, Almirante Brown x2); nueve citas de línea corregidas.
- `web/e2e/api-falsa.patch-georef.test.ts`: describes F1, F2, F3 (RB3D-1 a RB3D-3 integrados, con bordes), `toEqual` exacto en el PATCH de edificio, variable `godoyCruz` -> `guaymallen`.
- `web/e2e/api-falsa.rompedor-3d.test.ts`: borrado (nunca tuvo commit; su contenido quedó integrado).

## JUICIO

Autor: constructor. Comparé cada tarea contra su criterio de verificación en tasks.md y contra la API real donde había fuente local (modelos de ruta, `config/georef/`, test de integración del resumen). Confianza alta en 4.3, 11.1 a 11.4 (RED por aserción, GREEN y mutantes). Alta en 11.5 (comprobado línea por línea). Amplié 11.5 a siete citas más que el plan no nombraba porque su criterio ("sólo líneas vigentes") no se cumplía sin ellas; es sólo comentario.

## SUPOSICIÓN

- La forma exacta del 422 de la real (`missing ["body"]`, `uuid_parsing ["path","grupo_id"]`) la tomo del informe del rompedor (E2) y de cómo funciona FastAPI; no levanté la API real (sin Docker por el brief).
- La real acepta UUID sin guiones o con `urn:uuid:`; la falsa los rechaza. Queda declarado en el comentario; la web siempre manda la forma con guiones (no verificado exhaustivamente).
- Un PATCH con id no UUID y además cuerpo inválido: la real podría juntar los dos errores en una sola lista; la falsa devuelve sólo el del path. No probado contra la real.
- No corrí Playwright (juez: CI, L-050) ni pytest (no se tocó backend).
- Entorno: `node_modules` es symlink al repo principal; pnpm imprime "Error: installing dependencies ... workspace hoist directory is not a real directory" por `verifyDepsBeforeRun` antes de cada script, con lockfile "up to date". No afectó los resultados (vitest, tsc y biome terminaron con exit 0). `sd` no está instalado en la máquina; usé Edit y python para los reemplazos.

## Intento 2

- Entrada: F7 de `informes/verify-2-breaker.md` (sólo esa sección y "Fallas reproducidas"), test RB3D-7 en `web/e2e/api-falsa.rompedor-3d-v2.test.ts` (sin commit). Tarea 11.6 agregada a tasks.md por decisión del orquestador.
- EVIDENCIA: RED 12:28:52 por aserción (`expected 200 to be 422`) con RB3D-7 ya integrado en el describe "F2 y F7" de `api-falsa.patch-georef.test.ts`. GREEN 12:29:00: 64 passed (con `api-falsa.test.ts`). Mutante M-B6 sobre el borde de mayúsculas 12:29:10: rojo por aserción, revertido (`diff -q` idéntico). `pnpm test` 12:29:15 sobre `173089b`: 85 archivos, 597 passed, exit 0. `pnpm typecheck` 12:30:17: exit 0. Biome limpio sobre los dos archivos.
- Cambios: `api-falsa.ts` rechaza `PATCH /api/complejos/{id}` con id no UUID (reutiliza `_UUID`; sólo PATCH de la raíz del edificio, los GET y POST no cambian); test integrado y `api-falsa.rompedor-3d-v2.test.ts` borrado.
- JUICIO (constructor): confianza alta; los ids de `escenarios.ts` son todos UUID, así que el chequeo no cambia ningún escenario existente (la suite completa lo confirma).
- SUPOSICIÓN: las divergencias que el rompedor dejó como JUICIO (UUID sin guiones, id devuelto en mayúsculas, path inválido más cuerpo vacío con 1 error en vez de 2) no se tocaron: fuera de la lista.
- Contaminación: leí la F7 y el JUICIO adyacente del informe del rompedor intento 2; nada más.
