# Revisor del plan · propose · intento 2 · pulido-2 (3d)

- **Rol**: plan-reviewer (subagente nativo de Claude, despachado por el orquestador). No edita plan ni código.
- **Fecha**: 30/10/2026, 12:15 a 12:25 (-03:00).
- **Revisión**: HEAD `b1ec660` más el diff sin commit de `openspec/changes/pulido-2/{proposal.md,specs/,tasks.md}` (corrección del plan por F1 a F6). La sección "Estado de la revisión independiente" de tasks.md queda fuera (es del orquestador).
- **Veredicto**: **CORREGIR** (1 defecto que bloquea, 2 menores).

## Fuentes leídas

- `git diff` del plan (proposal, spec `pantallas-del-edificio`, tasks).
- `informes/verify-1-breaker.md`: sólo la lista de hallazgos F1 a F6, la tabla de mutantes (A1) y "Fallas reproducidas".
- `backend/src/proptech_core/complejos/aplicacion/lectura.py:205-264` (cálculo de pasos).
- `backend/tests/integracion/test_resumen_puesta_a_punto.py:32-48` y `:118-136`.
- `backend/tests/integracion/test_contrato_web.py:1-160` (guarda de fixtures).
- `backend/src/proptech_api/complejos.py:178` (`piso` opcional en el alta de unidad).
- `web/src/app/edificios/[id]/ayuda.ts`, `ayuda.test.ts`, `ayuda.rompedor-3d.test.tsx`, `Pantalla.test.tsx:146-158`.
- `web/src/lib/api/fixtures/resumen.json`, `web/e2e/api-falsa.ts` (por `rg`), `web/e2e/api-falsa.patch-georef.test.ts:20-113`, `web/e2e/api-falsa.rompedor-3d.test.ts`.

## Contaminación

Leí el informe del rompedor (es el origen de la corrección). Mis chequeos de F4 los rehice contra `lectura.py` y los tests del backend, no contra su conclusión. No leí otros informes.

## EVIDENCIA

### E1 · Estado rojo de los tests de partida (corrido por mí)

- Comando: `cd web && npx vitest run "src/app/edificios/[id]/ayuda" e2e/api-falsa.rompedor-3d.test.ts e2e/api-falsa.patch-georef.test.ts`
- Timestamp: 2026-10-30T12:16:49-03:00, revisión `b1ec660` + archivos sin commit del rompedor.
- Resultado: 4 archivos, 28 tests, **5 fallan, 23 pasan**. Los 5 fallan por aserción, no por setup: RB3D-1 (x2, `PATCH` sin cuerpo), RB3D-2, RB3D-3 (`50028010: Godoy Cruz != Colonia Segovia`, `06028: Adolfo Alsina != Almirante Brown`, ...) y RB3D-4 (`expected '0 de 7 pasos' to be '4 de 7 pasos'`).
- Alcance: confirma que 4.3, 11.1, 11.2 y 11.3 tienen un rojo por aserción disponible. No corrí el mutante A1 (11.4): lo tomo del informe del rompedor (SUPOSICIÓN S2).

### E2 · Verdad del escenario "Ejemplo de la ayuda" contra el backend (lectura de código, sin base)

- Recién creado: `test_edificio_recien_creado` fija `ubicacion`, `grupos`, `categorias`, `intereses_y_vencimiento` en "hecho" y `unidades`, `coeficientes`, `saldos_previos` en "falta": **4 de 7**. Verdadero.
- Después de unidades y coeficientes: `test_edificio_listo_para_liquidar` (una unidad con coeficiente 1) da los 6 primeros en "hecho" antes de confirmar saldos; `lectura.py:250-264` lo explica. **6 de 7** verdadero, con una condición: `ubicacion` exige `unidades_sin_piso_completo == 0` (`lectura.py:240-252`) y `piso` es opcional en la API (`complejos.py:178`). Si se cargan unidades sin piso, la barra queda en 5 de 7.

### E3 · Qué ata hoy la web al cálculo real

- `test_contrato_web.py:79-89` sólo compara **forma** (claves y tipos) de `resumen.json` contra la API real, no valores; y su escenario tiene 3 unidades (no es un edificio recién creado).
- `ayuda.rompedor-3d.test.tsx` usa un `Resumen` escrito a mano que copia los `pasos` de `test_edificio_recien_creado`.
- Conclusión observada: ningún test de vitest ve `lectura.py`. Si el cálculo cambia, la copia a mano de la web no cambia y el test de la ayuda sigue verde.

### E4 · Tests vigentes que la corrección toca

- `ayuda.test.ts:14-16` (tarea 4.1, marcada `[x]`) afirma `"0 de 7 pasos"` y `"2 de 7"`: con el arreglo de 4.3 se pone rojo.
- `api-falsa.patch-georef.test.ts:59-62` afirma que un `PATCH` con `{}` da 200 ("todos los campos son opcionales"). RB3D-1 manda cuerpo `""`, no `{}`.
- RB3D-3 ya lee `config/georef/` (`readFileSync(join(dir, ...))`): la cláusula condicional de 11.3 está cumplida de entrada.

## Defectos

### PR2-1 (BLOQUEA) · El AND del escenario "Ejemplo de la ayuda" promete algo que ningún test de la web puede cumplir

- **Fuente**: `specs/pantallas-del-edificio/spec.md`, escenario "Ejemplo de la ayuda", segundo AND ("...de modo que si el cálculo cambia el test de la ayuda se pone rojo"); tarea 4.3 ("ata los números a los pasos que el backend vigente marca hechos").
- **Observación**: E3. El test de vitest sólo puede atar el texto a un `Resumen` copiado a mano; la guarda de contrato compara forma, no valores. El "como mínimo" no salva la frase final, que sigue exigiendo que un cambio de `lectura.py` ponga rojo el test de la ayuda.
- **Impacto**: criterio de aceptación no verificable; el auditor no puede darlo por cumplido y el constructor no tiene cómo satisfacerlo sin salir del alcance.
- **Criterio incumplido**: criterios de aceptación testeables; no prometer comportamiento que el test no vigila.
- **Corrección verificable** (decide el planificador, no la elijo yo):
  - (a) Aflojar el AND: el test de la web arma el `Resumen` con los `pasos` de `test_edificio_recien_creado` copiados con su referencia (archivo y nombre del test) y compara el "arranca en N de 7" con lo que la barra muestra para ese `Resumen` (lo que ya hace RB3D-4), más "6 de 7" con los pasos de `test_edificio_listo_para_liquidar` antes de saldos. La sincronía automática con el backend queda como DEUDA nombrada (dueño sugerido: C-23 `humo-y-ci` o quien toque `test_contrato_web.py`).
  - (b) Mantener el AND y agregar una guarda del lado del backend (sólo tests, sin producción): por ejemplo, un fixture `resumen_recien_creado.json` generado desde la API real por `test_contrato_web.py` y comparado **por valor** en `pasos`, que el test de la web importe. Es tocar tests del backend: hay que decir quién lo coordina y que sigue siendo MEDIUM.
  - Verificación de cualquiera: el texto del escenario no afirma más de lo que el test elegido vigila; con (b), cambiar a mano un `pasos` del fixture o del cálculo pone rojo un test.

### PR2-2 (menor) · La 4.3 no nombra el test vigente que va a romper

- **Fuente**: tasks.md 4.3 ("La 4.2 queda superada por esta"); E4 (`ayuda.test.ts:14-16`).
- **Impacto**: la 4.1 marcada `[x]` vigila el texto falso; si no se reescribe queda un test contradictorio o se borra sin rastro.
- **Corrección verificable**: la 4.3 dice explícitamente que `ayuda.test.ts` cambia sus aserciones a "4 de 7"/"6 de 7" (y conserva el "ningún de 6"), y que 4.1 y 4.2 quedan superadas (no desmarcadas en silencio). Verificación: `rg -n "0 de 7|2 de 7" web/src` sin resultados en la revisión entregada.

### PR2-3 (menor) · 11.1 no protege el caso `{}` → 200

- **Fuente**: tasks.md 11.1 ("los `POST` existentes siguen igual"); E4 (`api-falsa.patch-georef.test.ts:59-62`).
- **Impacto**: un arreglo que rechace todo cuerpo vacío o `{}` rompería la paridad con la real (todos los campos opcionales). El test existente lo atraparía, pero la tarea no lo nombra como criterio.
- **Corrección verificable**: agregar a la verificación de 11.1 "un `PATCH` con `{}` sigue dando 200 en ambas rutas" (`api-falsa.patch-georef.test.ts` verde).

## Revisión de 11.1 a 11.5 sin defecto

- 11.1, 11.2, 11.3: rojo por aserción disponible (E1), cambios sólo en `web/e2e/api-falsa.ts`, sin backend de producción. Dentro de MEDIUM.
- 11.4: verificación por mutante A1 a mano y revertido, sin entregarlo; un `toEqual({ id })` o un id distinto al del fixture es un test de comportamiento (distingue escritura de lectura), no tautológico. Factible.
- 11.5: documental, verificación por `rg`, declara correctamente que no lleva RED/GREEN.
- Ninguna toca `backend/src/`. Proposal y spec coherentes entre sí en "4 de 7 / 6 de 7".

## JUICIO

Autor: plan-reviewer (Claude). Comparé el escenario y las tareas nuevas contra el cálculo de `lectura.py`, los tests del backend que lo fijan, la guarda de contrato de fixtures y los tests de la web. Los números nuevos son verdaderos (confianza alta). El AND que exige que el test de la ayuda caiga si cambia el cálculo no es alcanzable desde vitest sin una pieza nueva (confianza alta, E3). Elegir entre aflojarlo o agregar la guarda del backend es decisión de alcance del planificador. El resto de la corrección es factible y queda en MEDIUM.

## SUPOSICIÓN

- S1: no corrí los tests del backend (`test_resumen_puesta_a_punto.py`); tomo de su código que están verdes (el rompedor cita CI verde en `b1ec660`, run 40790724706, que no verifiqué).
- S2: no apliqué el mutante A1; tomo del informe del rompedor que sobrevive.
- S3: asumo que `DATOS` de `test_unidades_casos_de_uso.py` trae `piso` (no lo abrí); si no, el "6 de 7" del test listo se apoyaría en otro camino. El ejemplo de la ayuda podría mencionar el piso para ser exacto; no lo marco como defecto.

## No ejecutado

Suite completa de la web y del backend; mutante A1; `openspec validate` (lo corrió el orquestador a las 12:15: valid).

## Vuelta 2 (30/10/2026, después de las 12:18)

- **Alcance**: sólo PR2-1, PR2-2 y PR2-3, sobre el diff sin commit actual de `specs/pantallas-del-edificio/spec.md` y `tasks.md` (HEAD `b1ec660`). `openspec validate pulido-2` lo corrió el orquestador (valid, 12:18); no lo volví a correr.
- **Fuente**: `git diff -- openspec/changes/pulido-2/specs openspec/changes/pulido-2/tasks.md`.

### EVIDENCIA

- PR2-1: el AND ahora dice "el test de la ayuda exige sólo el texto, y la sincronía automática con ese cálculo queda como deuda"; el THEN aclara "unidades (con su piso)". tasks.md agrega "Decisiones y deuda de la revisión del plan (intento 2)" con la opción (a) y la DEUDA con destino C-26 `pulido-web-3`. La 4.3 ya no promete atar el texto al cálculo. **Resuelto.**
- PR2-2: la 4.3 nombra `ayuda.test.ts:14-16` y exige reescribirlo a "4 de 7"/"6 de 7"; la verificación excluye "0 de 7"/"2 de 7"/"de 6". **Resuelto.**
- PR2-3: la 11.1 dice que `{}` sigue dando 200 y que se conserva `api-falsa.patch-georef.test.ts:59-62`. **Resuelto.**

### JUICIO

Autor: plan-reviewer (Claude). Los tres criterios ahora son verificables y no prometen más de lo que vigila el test. Confianza alta. Observación sin defecto: la opción (a) la eligió el orquestador y la DEUDA cae en C-26 (Matías); conviene que Juani o el dueño de C-26 se enteren al cerrar, pero en MEDIUM no requiere firma.

### SUPOSICIÓN

No reabrí 11.2 a 11.5 ni el resto del plan (fuera del encargo de esta vuelta). Siguen vigentes S1 a S3 de la vuelta 1.

### Veredicto vuelta 2

**APTO PARA CONSTRUIR** (las tareas 4.3 y 11.1 a 11.5).
