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
