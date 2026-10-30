## 1. Antes de tocar nada

- [x] 1.1 Leer `knowledge-base/15_lecciones.md` completa y anotar en el informe cuáles aplican (L-027, L-035, L-049, L-050, L-051, L-052 como mínimo). Verificación: el informe del constructor las lista.
- [ ] 1.2 **[BLOQUEADA: hay que avisar a Emiliano]** Avisar a Emiliano que se va a tocar `web/e2e/api-falsa.ts` y acordar cómo se suben los cambios (commit aparte y primero). Verificación: respuesta de Emiliano anotada en el informe; sin ella, el grupo 2 no arranca.
- [x] 1.3 Buscar todos los consumidores de `vocabularioDePisos` (`rg "vocabularioDePisos" web/`) y confirmar que ninguno depende del orden viejo. Verificación: lista de usos en el informe.
- [x] 1.4 Dejar el baseline de la rama: `pnpm test` (65 archivos, 432 pruebas), `pnpm typecheck`, y la lista de fallas conocidas de Windows. Verificación: salida pegada en el informe.

## 2. API falsa de e2e (coordinada con Emiliano) — 2.1 a 2.4 hechas sin respuesta de Emiliano; 1.2 sigue pendiente; 2.5 sin hacer

- [x] 2.1 **[hecho sin respuesta de Emiliano; la 1.2 sigue pendiente; el test va en `web/e2e/api-falsa.patch-georef.test.ts`, archivo aparte para no chocar con `api-falsa.test.ts`]** Test rojo: un `PATCH` válido a `/complejos/{id}` responde 200, uno con un campo de tipo equivocado responde 422 y uno con un método no declarado en otra ruta sigue dando 405. Verificación: el test falla por "método no declarado" antes del código (escenario: lista de pisos sin tocar; cubre la deuda D-130 de `api-falsa.ts`).
- [x] 2.2 Declarar `PATCH` de edificio en `_CONTRATO_DE_ESCRITURA` con el esquema de campos de la API real y verificar que 2.1 pasa.
- [x] 2.3 Test rojo y luego `PATCH /grupos/{id}` (desactivar un grupo) en el mismo contrato; verificar que el test pasa y que un cuerpo mal formado da 422.
- [x] 2.4 Test rojo y luego simulación de las rutas de Georef con una respuesta fija chica (provincias, departamentos, localidades encadenados); verificar con un test que cada nivel filtra por el anterior.
- [ ] 2.5 **[NO HECHA: Playwright no se corre local, el juez es el CI]** Spec de Playwright que edita la ubicación del edificio con las listas encadenadas y otro que desactiva un grupo, ambos contra la API falsa. Verificación: se corren con `pnpm exec playwright test` y se anota el resultado local como señal; el juez es el job `web` del CI (L-050).

## 3. Orden de los pisos (escenarios "Edificio con dos subsuelos", "con un subsuelo", "sin subsuelos")

- [x] 3.1 Test rojo en `web/src/lib/pisos.test.ts` (crear si no existe): pisos=4, subsuelos=2 → `["SS2","SS1","PB","1","2","3","4"]`; subsuelos=1 y subsuelos=0 con sus órdenes. Verificación: falla porque hoy devuelve `PB` primero.
- [x] 3.2 Cambiar `vocabularioDePisos` para devolver el orden de altura y actualizar su comentario (decisión de Gianfranco, 28/10/2026). Verificación: 3.1 pasa.
- [x] 3.3 Corregir `unidades/Pantalla.test.tsx:511-531` (hoy espera `["", "PB", "1", ..., "SS1"]`) al orden nuevo, conservando la opción vacía (L-052), y verlo fallar antes de 3.2 (mutar a mano para verlo rojo). Verificación: el test pasa con el código nuevo y falla con el viejo.

## 4. Ayuda del resumen (escenario "Ejemplo de la ayuda")

- [x] 4.1 Test rojo en el test de la pantalla del resumen que afirme que el texto de `AYUDA_RESUMEN` no contiene "de 6" y contiene "de 7". Verificación: falla con el texto actual.
- [x] 4.2 Corregir `ayuda.ts` ("0 de 7 pasos", "2 de 7") y verificar que 4.1 pasa.
- [x] 4.3 Corregir el ejemplo de la ayuda a 4 de 7 / 6 de 7 (hallazgo F4 del rompedor, `informes/verify-1-breaker.md`), con test rojo primero. Archivos: `web/src/app/edificios/[id]/ayuda.ts` (`AYUDA_RESUMEN.ejemplo`) y su test (puede partir de `ayuda.rompedor-3d.test.tsx`, que el rompedor dejó en rojo). El test de la 4.1, `web/src/app/edificios/[id]/ayuda.test.ts:14-16`, hoy afirma "0 de 7 pasos" y "2 de 7": hay que reescribirlo para que exija "4 de 7" y "6 de 7". Verificación: el test afirma "4 de 7" y "6 de 7" y ningún "0 de 7"/"2 de 7"/"de 6" (sólo el texto, opción (a) de PR2-1; los números son los del backend vigente, `lectura.py:250-264`, `test_resumen_puesta_a_punto.py:32-48`, y el "6 de 7" supone unidades con piso); se ve fallar con el texto actual y pasar con el corregido (escenario "Ejemplo de la ayuda", reescrito el 30/10/2026). La 4.2 queda superada por esta.
  - Evidencia (constructor intento 1, `informes/apply-1-constructor.md`). Baseline 12:19:30 (`pnpm exec vitest run` de los 5 archivos enfocados sobre `b1ec660` + diff sin commit): 5 failed (RB3D-1 x2, RB3D-2, RB3D-3, RB3D-4) / 56 passed.
  - RED 12:20:00: `pnpm exec vitest run "src/app/edificios/[id]/ayuda.test.ts" "src/app/edificios/[id]/ayuda.coherencia.test.tsx"` -> 2 failed / 2 passed. `ayuda.test.ts`: `expected 'Un edificio recién creado arranca en …' to contain 'arranca en 4 de 7 pasos'`; RB3D-4: `expected '0 de 7 pasos' to be '4 de 7 pasos'`. Por aserción.
  - GREEN 12:20:09: `pnpm exec vitest run "src/app/edificios/[id]/"` -> 23 archivos, 136 passed. Commit `b5d7cbb`.
  - `ayuda.test.ts` exige "arranca en 4 de 7 pasos", "6 de 7" y ningún `\b[02] de 7\b`; el test de "de 6" se conserva. RB3D-4 reubicado (no duplicado) en `ayuda.coherencia.test.tsx`: compara el arranque con la barra renderizada.

## 5. Día de vencimiento fuera de rango (escenario "Día 31")

- [x] 5.1 Investigar y anotar en el informe qué cobertura ya existe: `test_configuracion_api.py:166` (29), `acciones.conflicto.test.ts:56`, y si el segundo vencimiento tiene tope propio en el backend. Verificación: lista de lo cubierto y lo que falta, con archivo y línea. Si ya está todo cubierto, se anota y se saltan 5.2 y 5.3.
- [x] 5.2 Test rojo (pantalla): con el formulario sin validación nativa, enviar 31 muestra el error sólo en el campo "Día de vencimiento"; ídem para el segundo vencimiento si 5.1 lo confirma.
- [x] 5.3 Hacer pasar 5.2 con el cambio mínimo en la web; si hiciera falta tocar el backend de producción, parar y consultar (el alcance lo excluye).

## 6. Test de punta a punta: clave explícita inválida

- [x] 6.1 Test de integración en `backend/tests/integracion/` (sin tocar producción): `POST` de una categoría y de un grupo con clave que no cumple `^[a-z][a-z0-9_]{0,39}$` responde 422 nombrando el campo `clave` sin repetir el valor. Verificación: pasa contra la API real con Docker; se verifica con una mutación a mano (aflojar el patrón) que se pone rojo (L-035). Si Docker no está disponible, queda anotado como no verificado.

## 7. CSP del proxy

- [x] 7.1 Test rojo en `web/src/proxy.test.ts`: dada una respuesta con `script-src 'self' 'unsafe-inline' 'unsafe-eval' 'nonce-x'`, la política final no contiene `'unsafe-inline'` ni `'unsafe-eval'`, conserva el nonce y se aplica tanto a `content-security-policy` como a `x-middleware-request-content-security-policy`. Verificación: se ve fallar quitando a mano el filtro de `proxy.ts` (L-035) y pasar con el código actual.

## 8. axe en más de un estado (escenario "axe cubre más de un estado…")

- [x] 8.1 Para `categorias`, `grupos`, `configuracion` y `saldos-previos`: escribir primero los tests de axe en estado vacío y con error de campo (reutilizando `sinViolaciones`, parametrizado por estado, L-051) y ver cuáles fallan. Verificación: salida de cada pantalla en el informe; si alguno revela una violación real, se arregla con su test antes del arreglo.
- [ ] 8.2 **[NO VERIFICADA EN NAVEGADOR REAL: requiere Clerk de desarrollo; axe en jsdom no mide contraste ni 320 px]** Mirar las cuatro pantallas en esos estados en un navegador real a 1280 px y 320 px (L-026). Verificación: nota en el informe con lo visto.

## 9. Raíz `/` — hecha, PENDIENTE DE CONFIRMAR CON JUANI (qué muestra la raíz; ver `design.md`)

- [x] 9.1 **[pendiente de confirmar con Juani]** Test rojo: test rojo (con y sin sesión) de la ruta `/` según los escenarios "Con sesión" y "Sin sesión". Si Juani decide otra cosa, se reescribe el escenario antes de seguir.
- [x] 9.2 **[pendiente de confirmar con Juani; NO mirada en navegador real; `web/e2e/comprobaciones.spec.ts` (320 px y reduced-motion) y `web/e2e/csp.spec.ts` (nonce por pedido público) usaban `/` como portada: se apuntaron a `/ingresar`, que no redirige, sin cambiar lo que verifican; NO CORRIDO LOCALMENTE (Playwright), lo decide el CI (L-050)]** Implementar la raíz y verificar 9.1; mirarla en un navegador real (L-026).

## 10. Cierre

- [x] 10.1 **[28/10/2026: web 72 archivos / 454 tests, tsc 0, Biome limpio sobre los archivos cambiados; backend -m "not integracion" 41 fallas, las mismas 41 del baseline de Windows, 0 nuevas; tests de backend agregados 57 verdes. NO re-corridos: integración completa (baseline: 11 por SIGUSR1) ni Playwright (juez: CI, L-050)]** `pnpm test`, `pnpm typecheck` y `pnpm lint` completos; las fallas de formato por CRLF de Windows van listadas aparte, no se arreglan reformateando todo el repo. Pytest `-m "not integracion"` y los de integración con Docker. Verificación: salida pegada, todo lo nuevo en verde y el baseline de Windows igual que el del paso 1.4.
- [x] 10.2 Pasada que rompe y audita (un agente con los dos trabajos, tope de 3 vueltas, D-092): casos borde de cada tarea, regresiones en pantallas vecinas, dependencias de `api-falsa.ts`. Cada hallazgo vuelve como test antes del arreglo. Informe en EVIDENCIA / JUICIO / SUPUESTOS.
- [ ] 10.3 Armar la descripción del PR con: qué cambia, por qué (C-22 / D-130), cómo se probó, lo que el rompedor intentó y su resultado, pendientes, y la corrección de la ficha (orden de pisos, CSP ya con e2e, día 29 ya cubierto). La corrida de cierre va después de la última vuelta (D-092). No se hace commit, push ni PR sin que Gianfranco lo confirme.
- [ ] 10.4 Al archivar: actualizar `12_fichas_de_changes.md`, `CHANGES.md` (C-22 a `[x]`), agregar la decisión a `09_decisiones_y_supuestos.md` y, si corresponde, la lección a `15_lecciones.md`.

## 11. Correcciones del rompedor (intento 1)

Origen: `informes/verify-1-breaker.md` (revisión `b1ec660`). Cada una entra por TDD: test rojo por aserción primero (los RB3D-1 a RB3D-3 del rompedor sirven de punto de partida), después el arreglo mínimo. F4 va en la 4.3.

- [x] 11.1 F1: un `PATCH` sin cuerpo a `/complejos/{id}` o a `/grupos/{id}` en la API falsa (`web/e2e/api-falsa.ts`) responde 422, como la real (`422 missing loc ["body"]`), en lugar de 200. Sólo el cuerpo vacío o que no es JSON pasa a 422: un `PATCH` con `{}` sigue dando 200, porque todos los campos son opcionales también en la real (`api-falsa.patch-georef.test.ts:59-62` se conserva). Verificación: RB3D-1 rojo antes del arreglo y verde después; los `POST` existentes siguen igual (`api-falsa.test.ts`).
  - RED 12:21:17: `pnpm exec vitest run e2e/api-falsa.patch-georef.test.ts` -> 4 failed / 25 passed: los dos "sin cuerpo da 422 missing en body" (`expected 200 to be 422`), F2 (`expected 200 to be 422`) y F3 (lista de 4 nombres distintos). RB3D-1 a RB3D-3 integrados en este archivo; `api-falsa.rompedor-3d.test.ts` borrado (sin commit previo).
  - GREEN 12:21:38: `pnpm exec vitest run e2e/api-falsa.patch-georef.test.ts e2e/api-falsa.test.ts` -> 62 passed (los POST de `api-falsa.test.ts` sin cambios). Commit `ef1d8e9`.
  - Bordes nacidos verdes (no JSON -> 422 json_invalid en las dos rutas; `{}` -> 200 en las dos), probados con mutantes revertidos (12:22:01 a 12:22:17): M-B1 grupos catch -> `parseado = {}` rojo; M-B2 complejos catch -> `cuerpoParseado = {}` rojo (`expected 200 to be 422`; un primer intento de M-B2 cayó por timeout y se descartó por no ser aserción); M-B3/M-B4 rechazar también `{}` rojo en los tests de `{}` (incluido el original de las líneas 59-62).
- [x] 11.2 F2: `PATCH /api/grupos/{id}` con un id que no es UUID responde 422 (`uuid_parsing`) en la API falsa, como la real. Verificación: RB3D-2 rojo antes y verde después.
  - RED 12:21:17 (misma corrida que 11.1): `PATCH /api/grupos/no-es-uuid da 422 uuid_parsing en el path` -> `expected 200 to be 422`.
  - GREEN 12:21:38: 62 passed. El detalle es `[{type:"uuid_parsing", loc:["path","grupo_id"]}]`. Borde: UUID en mayúsculas -> 200 (nació verde; mutante M-B5 quitar la `i` del patrón 12:22:09 -> rojo; revertido). Límite declarado en el comentario: la falsa sólo acepta la forma con guiones.
- [x] 11.3 F3: los nombres de provincias, departamentos y localidades que simula la API falsa coinciden con `config/georef/` para los mismos ids (`50028` Guaymallén, `50028010` Colonia Segovia, `06028`/`06028010` Almirante Brown). Verificación: RB3D-3 rojo antes y verde después; si RB3D-3 no lee `config/georef/`, el constructor agrega una aserción que compare cada nombre simulado con ese archivo para el mismo id.
  - RED 12:21:17: `expected [ …(4) ] to deeply equal []`: `departamento 50028: Godoy Cruz`, `localidad 50028010: Godoy Cruz`, `departamento 06028: Adolfo Alsina`, `localidad 06028010: Carhué`.
  - GREEN 12:21:38: 62 passed. El test lee `config/georef/{provincias,departamentos,localidades}.json` y compara nombre y padre (`provincia_id`, `departamento_id`) de cada fila simulada, también las provincias.
- [x] 11.4 F5 (L-027): el test del `PATCH` de edificio en `web/e2e/api-falsa.patch-georef.test.ts` falla si se quita la rama `PATCH` de `api-falsa.ts` (mutante A1 del rompedor), por ejemplo con `toEqual` exacto o un id distinto del de `edificio.json`. Verificación: aplicar A1 a mano, ver el test rojo por aserción, revertir y verlo verde; el mutante no se entrega.
  - Mutante A1 antes de endurecer (12:22:24): `if (metodo === "PATCH" && resto === "")` -> `if (false)`: 62 passed (sobrevive, confirma F5). Revertido.
  - Cambio del test: `toMatchObject({ id: EDIFICIO })` -> `toEqual({ id: EDIFICIO })`.
  - RED con A1 (12:22:37): `un cambio válido de nombre y ubicación responde 200 con el id` -> `expected { …(10) } to deeply equal { Object (id) }` (recibe el fixture `edificio.json`). Revertido (`diff -q` contra la copia: idéntico).
  - GREEN sin mutante (12:22:37): 62 passed. Commit `ef1d8e9`; el mutante no se entrega.
- [x] 11.5 F6 (documental): corregir en los comentarios de `web/e2e/api-falsa.ts` las referencias a `complejos.py:330`/`:494` y a `editar_edificio`/`editar_grupo` por `modificar_edificio` (`complejos.py:342`) y `modificar_grupo` (`complejos.py:506`). Verificación: `rg -n "complejos.py:" web/e2e/api-falsa.ts` sólo muestra líneas vigentes en la revisión entregada; sin RED/GREEN de código (es sólo comentario).
  - Validación documental (sin RED/GREEN de código), 12:23:00: se corrigieron las nueve citas de `complejos.py:` del archivo (no sólo las dos del plan: las otras siete también eran viejas y el criterio exige que todas sean vigentes). Cada una apunta al decorador `@router` de la función nombrada, comprobado con `awk` sobre `backend/src/proptech_api/complejos.py`: ver_complejo 363, modificar_edificio 342, resumen_edificio 318, vigente_del_edificio 612, alta_unidad 423, alta_grupo 485, alta_categoria 556, modificar_grupo 506 (dos veces), alta_version 635. `rg -n "editar_edificio|editar_grupo" web/e2e/api-falsa.ts` -> sin resultados. Commit `ef1d8e9`.

- [x] 11.6 F7 (`informes/verify-2-breaker.md`; extensión de la 11.2, decisión del orquestador 30/10/2026): `PATCH /api/complejos/{id}` con un id que no es UUID responde 422 `uuid_parsing` (`loc ["path","complejo_id"]`) en la API falsa, como la real. Verificación: RB3D-7 integrado en `api-falsa.patch-georef.test.ts` rojo antes y verde después; archivo del rompedor borrado.
  - RED 12:28:52: `pnpm exec vitest run e2e/api-falsa.patch-georef.test.ts` -> 1 failed / 30 passed: `PATCH /api/complejos/no-es-uuid da 422 uuid_parsing en el path` -> `expected 200 to be 422`.
  - GREEN 12:29:00: con `api-falsa.test.ts`, 64 passed. Reutiliza `_UUID` de la 11.2. Borde nacido verde (id en mayúsculas -> 200) probado con mutante M-B6 (patrón sin `i`) 12:29:10 -> `expected 422 to be 200`; revertido, 31 passed.
  - Suite completa sobre `173089b`: `pnpm test` 12:29:15 -> 85 archivos, 597 passed, exit 0; `pnpm typecheck` 12:30:17 -> exit 0; Biome sobre los dos archivos tocados limpio. Commit `173089b`.

### Decisiones y deuda de la revisión del plan (intento 2)

- PR2-1 (`informes/propose-2-plan-reviewer.md`): se elige la opción (a), la de menor alcance (decisión del orquestador, 30/10/2026). El escenario "Ejemplo de la ayuda" exige sólo el texto "4 de 7 / 6 de 7" y que no diga "de 6"; el "6 de 7" supone unidades con piso.
- DEUDA: la ayuda no se sincroniza automáticamente con el cálculo de pasos de `lectura.py`; si ese cálculo cambia, el texto puede quedar desactualizado sin que ningún test lo detecte. Destino: C-26 `pulido-web-3`.

## Estado de la revisión independiente (orquestador, 30/10/2026)

- Motivo: la 10.2 la hizo un solo agente que rompía y auditaba a la vez; no hay informes en la rama. Juani pidió rompedor, constructor si rompe, y auditor, antes de mergear el PR #3.
- Rol activo: rompedor (role-breaker, subagente nativo de Claude). Intento 1.
- Revisión: `b1ec660` (diff `e29e36d...b1ec660`, 27 archivos). CI verde en `b1ec660` (run 40790724706: backend, humo, secretos, shellcheck, web).
- Informes: `informes/verify-1-breaker.md`.
- Bloqueos abiertos: 1.2 (aviso a Emiliano), 8.2 (navegador real), 9.x (confirmar la raíz con Juani), orden de pisos contra la ficha.
- Próximo paso: rompedor; si reproduce fallas, constructor por TDD; después auditor.
- 30/10/2026 12:20: rompedor intento 1 terminó con F1 a F6 reproducidas (`informes/verify-1-breaker.md`). Plan corregido por el planner (subagente nativo) y revisado en dos vueltas (`informes/propose-2-plan-reviewer.md`: APTO PARA CONSTRUIR). Rol activo: constructor (role-constructor, subagente nativo), intento 1, tareas 4.3 y 11.1 a 11.5 sobre `b1ec660` más el diff sin commit. Próximo: rompedor intento 2 sobre el diff del constructor, después auditor.
- 30/10/2026 12:25: constructor intento 1 terminó 4.3 y 11.1 a 11.5 (`informes/apply-1-constructor.md`). Commits `b5d7cbb` (4.3) y `ef1d8e9` (11.x) sobre `b1ec660`. Corrida completa sobre `ef1d8e9`: `pnpm test` 12:23:26 -> 85 archivos, 595 passed, exit 0; `pnpm typecheck` 12:24:27 -> exit 0; `pnpm lint` (biome ci) 12:24:35 -> exit 0, 7 warnings y 6 infos, ninguno en archivos tocados. No corridos: Playwright (juez: CI, L-050) ni pytest (no se tocó el backend). Rol activo siguiente: rompedor intento 2 sobre `e29e36d...` HEAD de `revision-3d`, después auditor.
- 30/10/2026 12:31: rompedor intento 2 cerró F1 a F6 y reprodujo F7 (`informes/verify-2-breaker.md`). Constructor intento 2: 11.6 en `173089b`. Próximo: rompedor sobre `173089b`, después auditor.
- 30/10/2026: rompedor intento 3 sobre `d15c610`: ninguna falla reproducida (`informes/verify-3-breaker.md`). Rol activo: auditor (role-auditor, subagente nativo), intento 1. Próximo: veredicto; si APROBADO, push de la rama al PR #3 y CI sobre el SHA nuevo.
