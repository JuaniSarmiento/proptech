## Why

El 3c cerró con deuda chica de 3b/3c que la regresión del 27/10/2026 encontró y que no era bloqueante
para mergear (D-130). Lo que más pesa: la API falsa de e2e no conoce los `PATCH` ni Georef que agregó el
3c, así que editar el edificio, desactivar un grupo y elegir la ubicación no tienen ningún e2e de
Playwright; y hay un test que certifica un bug (el orden de los pisos). Se hace ahora, antes del 6 de
Emiliano, para que él use una API falsa completa sin choques.

Cubre: **HU-A1** (configurar el edificio) y el borde de **HU-T1** (ayuda "?" por pantalla).
**Reglas**: **R01** (sin cambios; sólo la ayuda que la explica). **Decisiones**: **D-130** (reparto de
la deuda; origen de este change), **D-102** (toda pantalla lleva su ayuda), **D-105** (forma de las
pantallas), **D-094** y **D-111** (quién firma: acá no hace falta, es MEDIUM), **D-040** (fronteras de
módulos).

## What Changes

- **API falsa de e2e** (`web/e2e/api-falsa.ts`): declara `PATCH` para edificio (`/complejos/{id}`) y
  grupos (`/grupos/{id}`) en `_CONTRATO_DE_ESCRITURA`, y simula las rutas de Georef; hoy un `PATCH` real
  cae en "método no declarado" (405 hardcodeado, línea ~831). Con sus e2e de Playwright: editar
  ubicación/edificio, desactivar un grupo y el selector encadenado. **Este archivo se coordina con
  Emiliano antes de tocarlo** (ver Gobernanza).
- **Ayuda del resumen** (`web/src/app/edificios/[id]/ayuda.ts`): "0 de 6 pasos … 2 de 6" pasa a 7
  pasos, que es el flujo real desde el 3c, con los números que da la API real: un edificio recién
  creado arranca en "4 de 7" y, tras unidades y coeficientes, queda en "6 de 7" (corregido el
  30/10/2026 por el hallazgo F4 del rompedor, `informes/verify-1-breaker.md`; antes decía "0 de 7 …
  2 de 7", que era falso).
- **Orden de los pisos** (`web/src/lib/pisos.ts`, `vocabularioDePisos`): la lista de la unidad pasa a
  `SS<N>`…`SS1`, `PB`, `1`…`<pisos>` (orden de altura, `SS1` pegado a `PB`). El test del escenario
  "Elegir el piso de la lista del edificio" (`unidades/Pantalla.test.tsx:511-531`) hoy fija el orden
  viejo como esperado: se corrige y se le suma un caso con 2 subsuelos (pisos=4, subsuelos=2 →
  `["SS2","SS1","PB","1","2","3","4"]`), porque con un solo subsuelo no se distingue el orden.
- **Raíz `/`**: deja de ser el placeholder `<p>PropTech</p>` del change 1a.
- **`axe` en más de un estado** en las cuatro pantallas que hoy lo corren una sola vez, siempre en
  estado feliz (`categorias`, `grupos`, `configuracion`, `saldos-previos`).
- **Clave explícita inválida** (`backend/src/proptech_core/compartido/parametros.py:97-99`): un test de
  punta a punta vía API. Sólo test, sin código de producción.
- **CSP/nonce** (`web/src/proxy.ts`): un test que verifique el resultado del post-proceso de la
  política (se quitan `'unsafe-inline'`/`'unsafe-eval'` de `script-src`); `proxy.test.ts` hoy sólo
  cubre el token (E16).
- **Día de vencimiento fuera de rango (29 a 31)**: que lo frene la aplicación nombrando el campo, no
  sólo la validación nativa del `<input type="number">`. Ver "Preguntas que el propose deja abiertas".

## Discrepancias entre la ficha de 3d y el repo (anotadas para Juani en el PR)

1. **Orden de los pisos.** La ficha dice que `SS1` va "arriba de `PB`", pero su "Terminado cuando" lista
   `PB`, `1`…`N`, `SS1`…`SSN`, que es el orden que el código **ya tiene**. Decisión de Gianfranco
   (28/10/2026): `SS<N>`…`SS1`, `PB`, `1`…`N`, por orden de altura, con `SS1` pegado a `PB`. El
   "Terminado cuando" de la ficha lista el orden viejo y se corrige al archivar.
2. **CSP/nonce.** La ficha dice "sin ningún test que verifique el resultado". Ya existe
   `web/e2e/csp.spec.ts` (Next real, nonce distinto por pedido). Lo que falta es un test unitario del
   post-proceso de `proxy.ts`; el alcance se achica a eso.
3. **Día 31.** El backend ya acota `dia_de_vencimiento` a 1..28 (`dominio/configuracion.py:24`), hay un
   test de API para 29 (`test_configuracion_api.py:166`) y la acción de la web ya marca el campo ante
   ese 422 (`acciones.conflicto.test.ts:56`). Lo que parece faltar es una prueba de que la pantalla lo
   muestra aunque el navegador no frene antes. El alcance real se confirma en la primera tarea.
4. **3d no es sólo web.** La ficha dice "web", pero incluye un test de backend (clave inválida).
5. **`.git/informes-regresion/03-edificio.md`**, que `CHANGES.md` pide leer, es local de Juani y no está
   en el clon de Gianfranco. Este propose se escribió sin él, desde la ficha y el código.

## Capabilities

### New Capabilities
<!-- Ninguna: todo es corrección de comportamiento o de cobertura de capacidades existentes. -->

### Modified Capabilities
- `edificios-y-unidades`: el vocabulario de pisos que arma la lista de la unidad tiene un orden
  definido (`SS<N>`…`SS1`, `PB`, `1`…`<pisos>`); hoy la spec lista los valores pero no el orden.
- `pantallas-del-edificio`: la ayuda del resumen describe los 7 pasos reales; la raíz `/` deja de ser un
  placeholder; el escenario "axe en cada estado" se exige en las siete pantallas y no sólo en las dos que
  hoy lo cumplen; el día de vencimiento fuera de rango se rechaza y se nombra en el campo.

## Qué queda fuera

| qué | dónde va | por qué |
|---|---|---|
| Cualquier cambio en `backend/` de producción, incluido el orden de pisos | Ninguno | Decisión de Gianfranco: el orden es sólo de la lista de la web; `pisos.py` (vocabulario válido) no cambia. Los tests de backend de este change no tocan código de producción |
| Todo `acceso` (B-3, 2.3, 2.4, 2.5, el loop de `/elegir-administracion`) | `2d` | CRITICAL, autenticación |
| `configuracion_versionada`, cuenta corriente, montos | 4b a 4d | Plata |
| Georef sin `timeout`/`AbortController` en `pedirApi` | 15 | Deuda preexistente al 3c, dueño ya asignado en D-130 |
| Encabezado `sticky` de la tabla de unidades | 15 | Dueño ya asignado en D-130 |
| Mutantes de RF-01/RF-02 (4c), RB-5 (6), RE11 | 4c, 6 | D-130 |
| `/privacidad` (datos legales) | Bloqueante del 15 | D-130 |
| Lo que la raíz `/` debe ser en el producto final (portal, landing) | Futuro | Acá sólo deja de ser un placeholder; ver preguntas abiertas |

## Gobernanza

**MEDIUM** (ficha de 3d, D-130): no toca autenticación, pagos ni datos de usuario. No requiere firma
de Juani, Alberto ni Emiliano (D-094 y D-111 son sólo para CRITICAL y HIGH). Ciclo (`14_forma_de_trabajo.md`,
"Escalado por riesgo"): constructor y después una sola pasada que rompe y audita, con informes en
EVIDENCIA / JUICIO / SUPUESTOS; Juani revisa el PR.

**Coordinación obligatoria**: `web/e2e/api-falsa.ts` se toca sólo después de avisar a Emiliano (que
construye el 6 en paralelo y la va a usar). Los cambios a ese archivo se suben primero y por separado.

## Preguntas que el propose deja abiertas (a resolver antes o durante apply)

1. **Qué es la raíz `/`.** La ficha sólo dice que "deja de ser el placeholder". Propuesta mínima: un
   redirect a `/edificios` para quien tiene sesión y a `/ingresar` para quien no. Confirmar con Juani.
2. **Día 29 a 31.** Confirmar con la primera tarea si ya hay cobertura de pantalla; si la hay, el ítem
   se reduce a un test y se anota.
3. **`.git/informes-regresion/03-edificio.md`**: pedirle a Juani, por si agrega ítems.

## Knowledge Base Impact

| archivo | acción | por qué |
|---|---|---|
| `knowledge-base/12_fichas_de_changes.md` | REWRITE | La ficha 3d pasa a archivada; se corrige su "Terminado cuando" (orden de pisos) y se anota qué ítems estaban ya cubiertos (CSP e2e, día 29) |
| `CHANGES.md` | REWRITE | C-22 pasa a `[x]` al archivar |
| `knowledge-base/09_decisiones_y_supuestos.md` | APPEND | Una decisión nueva con el orden de pisos y su razón, y la corrección de la ficha. Número a asignar al archivar |
| `knowledge-base/15_lecciones.md` | APPEND | Sólo si el rompedor o el auditor dejan una lección; la lección candidata es "un test que fija el comportamiento actual como esperado" (hay uno acá) |
| `knowledge-base/04_modelo_de_datos.md`, `05_reglas_de_negocio.md`, `03_actores_y_roles.md` | none | No cambia modelo, reglas ni roles |

## Lecciones aplicadas (`15_lecciones.md`)

| lección | cómo la cubre |
|---|---|
| **L-027** · una API falsa que acepta cualquier escritura esconde errores de contrato | Los `PATCH` nuevos de `api-falsa.ts` declaran el esquema de campos de `_CONTRATO_DE_ESCRITURA` (tipos y opcionales), no responden 200 a todo; cada ruta con un test en `api-falsa.test.ts` que rechaza un cuerpo mal formado |
| **L-035** · un test que existe no es un test que vigila | Cada test nuevo se ve fallar antes del código (TDD) y se verifica con una mutación a mano (sacar el orden, quitar el filtro de `'unsafe-inline'`) |
| **L-026** · todos los tests en verde no dice nada sobre cómo se ve la pantalla | La raíz `/` y los estados nuevos de axe se miran en un navegador real, no sólo en jsdom |
| **L-050** · el navegador local puede dar rojo por el entorno de Clerk | El juez de los e2e es el job `web` del CI; no se declara verde un e2e sólo por correrlo en Windows |
| **L-052** · un `<select>` no controlado necesita opción vacía | El cambio de orden de `vocabularioDePisos` conserva la opción vacía inicial (`""`) que ya exige el test |
| **L-049** · un rojo contra stubs puede caer en un helper | El rojo de cada test se lee en su aserción, no sólo "falla" |
| **L-042** · sin CI en una rama sin PR | El cierre no dice "listo" hasta leer el CI del PR |
| **L-051** · arreglar el campo que encontró el QA no deja regla para el siguiente | Los tests de axe y de día fuera de rango se escriben sobre la clase (todos los estados / todos los campos acotados de esa pantalla), no sólo el caso puntual |

(Las lecciones que cada tarea cubre van nombradas en `tasks.md`.)
