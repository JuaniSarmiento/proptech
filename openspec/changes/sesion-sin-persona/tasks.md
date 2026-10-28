> **Firma primero.** Ninguna tarea arranca hasta que la sección "Aprobación" de `proposal.md` esté
> firmada por Juani, Alberto o Emiliano, con nombre, fecha y la respuesta a E1 a E11 (D-094, D-111).
> Una regla nueva que entre después de la firma necesita firma propia (L-029). El apply es CRITICAL:
> no se despacha a un `role-implementer` suelto (L-048).
>
> **TDD estricto con el rojo pegado** (L-034, L-049): cada tarea pega el comando, la salida del rojo y
> la hora, y el rojo cae en la aserción que el test dice probar (código de estado, cuerpo, URL final),
> nunca en un `ImportError`, en un 401 de la guarda ni en un helper. Para eso, la excepción, la opción o
> la ruta nueva existen vacías antes del primer rojo. **Rojo** = falla hoy; **Guarda** = pasa hoy y
> tiene que seguir pasando: se corre y se pega en verde antes del cambio, nunca se presenta como rojo
> (QA-7). Cada garantía nueva tiene un **mutante dirigido** corrido sobre una copia sin commit y
> declarado en el informe (L-013, L-035). Backend: `bash infra/ci/test-backend.sh <archivos>`. Web:
> `bash infra/ci/test-web.sh`.
>
> **Si E7 se rechaza**: el grupo 6 y el requisito MODIFIED de `specs/fronteras-de-modulos/` se borran
> antes de construir (el requisito ADDED de la lista permitida se queda), y la tarea 5.2 escribe la
> vinculación sin tocar el resto de `ejemplo.py`. **Si E6 se aprueba con la alternativa**: el evento de
> vinculación entra en la migración de la tarea 7.1. **Si E11 se responde distinto de la
> recomendación**: las tareas 7.1 a 7.3 y los deltas de `autorizacion-por-rol` y `gestion-de-usuarios`
> se reescriben antes de construir. **Si E10 se responde (b) o (c)**: la tarea 7.8 se reescribe.
>
> **Tamaño y vueltas**: 30 tareas, por encima de las "unas veinte" de `config.yaml`. Juani decidió no
> partirlo en changes (E8, D9); se construye en **dos vueltas, cada una con su PR** dentro de este
> change: **vuelta 1** = grupos 1 a 3 y 5 (el contrato, la web, el ejemplo: lo que corta el 431 y deja
> entrar), **vuelta 2** = grupos 4, 6 y 7 (recuadro, D-021 y los cuatro ítems de acceso). El grupo 8
> cierra cada vuelta. La tarea 2.4 (`codigo`) va en la vuelta 1 porque 3.1 la lee.

## 1. Preparación

- [x] 1.1 Rebasar sobre `main` y fijar el baseline antes de tocar nada: `alembic heads` con una sola
  cabeza (`0027` o la que haya mergeado el 3d o el 6), y en verde
  `bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_deuda_acceso_2b.py tests/integracion/test_personal_api.py tests/integracion/test_invitar_personal_api.py tests/integracion/test_ejemplo_casos_de_uso.py tests/integracion/test_auditoria_tabla.py tests/unitarios/test_fronteras_de_modulos.py tests/unitarios/acceso`
  y `bash infra/ci/test-web.sh`. Pegar conteos y SHA. Listar con `rg` los tests que hoy afirman 401
  para "token válido sin vínculo", "vinculada sin asignación" y "quitar la única asignación"
  (incluido `test_personal_api.py:144-170`): son los rojos de la tarea 2.


### Evidencia 1.1 · 28/10/2026

- `git rebase main` (11:04:23): `Current branch apply/sesion-sin-persona-v1 is up to date.`
- `git rev-parse HEAD`: `7a49effea1293cc02b3bcc2f7d9e462e9d25e7b1`.
- `cd backend && uv run alembic heads` (11:05): `0027 (head)`.
- Baseline backend, comando de 1.1 completo (11:04:23–11:06:34): `743 passed, 1 warning in 131.11s`.
- `bash infra/ci/test-web.sh` (11:07:04–11:07:47): Tests  432 passed (432).
- `rg -n '401|sin_vinculo|sin_asignacion|unica_asignacion' backend/tests/integracion/test_{sesion,identidad_clerk,personal}_api.py`: escenarios previos identificados en sesión sin asignación, identidad sin vínculo y quitar última asignación. Guardas distintas: selector con acceso sigue 401.
- Logs íntegros locales `.atl/2d-v1/`, baseline backend `/tmp/2d-v1-baseline-backend.log`. Se escribieron tests nuevos durante el baseline web; no se modificó producción hasta concluir ambos baselines.

## 2. API: el 403 `sin_acceso`

- [x] 2.1 `GET /api/sesion` en `tests/integracion/test_sesion_api.py`, por HTTP con tokens firmados de
  verdad (L-017). **Rojo**: token válido sin persona → 403 con cuerpo exacto
  `{"detail": {"codigo": "sin_acceso"}}`; persona vinculada sin asignaciones → mismo cuerpo byte a byte
  **y mismas cabeceras** salvo `X-Request-ID` (QA-2d, E1). **Guardas**: vinculada sin asignación en A
  y con asignación en B → 200 con B y sin A (`test_sesion_api.py:16-50`); sin token, otra clave,
  vencido, otra aplicación → 401 y cero SQL. Escenarios "Token válido sin vínculo", "Vinculada sin
  asignación", "Token inválido sigue siendo 401", "Acceso en otra administración no es sin acceso".
  **Verde**: `SinAcceso` en `acceso/aplicacion/identidad.py`, `consultar` la lanza sin personas o con
  lista vacía, traductor a 403 en `proptech_api` (D1). **Mutantes**: (a) `consultar` devuelve `[]`
  otra vez → rojo; (b) el traductor agrega `"motivo": "sin_persona"` sólo en un caso → rojo en la
  comparación byte a byte; (c) una cabecera propia distinta en un caso → rojo en la comparación de
  cabeceras; (d) `token_de_sesion_actual` responde 403 → rojo en "Token inválido sigue siendo 401".

  **Evidencia ejecutada 2.1 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T11:08:06.307792-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_deuda_acceso_2b.py tests/integracion/test_personal_api.py tests/integracion/test_rutas_protegidas.py tests/unitarios/test_errores.py
  test_sesion_api.py:112: AssertionError; assert 401 == 403 (y persona sin asignaciones: 200).
  22 failed, 441 passed, 1 warning in 76.05s
  GREEN TIME: 2026-10-28T11:15:30.269661-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_deuda_acceso_2b.py tests/integracion/test_personal_api.py tests/integracion/test_invitar_personal_api.py tests/integracion/test_rutas_protegidas.py tests/unitarios/test_errores.py
  486 passed, 1 warning in 86.00s; exit 0; fin 11:16:58 -03:00.
  MUTANTES: 2.1 a–d: exit 1, AssertionError; copia previa sin commit, restaurada.
  Diffs, comando, hora y file:line de cada mutante: informes/evidencia-api-v1.md.
  ```

- [x] 2.2 La precedencia en una ruta de dominio (`GET /api/complejos`), en
  `tests/integracion/test_identidad_clerk_api.py`. **Rojo**: sin persona → 403, línea
  `ingreso_sin_vinculo` sin email ni sub en claro y ninguna fila de auditoría; persona sin asignación y
  sin otra administración → 403 y **exactamente una** fila `ingreso_fallido`; sin persona con
  `X-Proptech-Administracion` de B → 403; vinculada en A sin asignaciones con selector de B → 403, cero
  filas `ingreso_fallido` y ninguna fila de B leída; sin acceso con `no-es-uuid` → 403, nunca 401 ni
  422; dos vínculos sin asignaciones (A y B) y sin selector → 403 y **cero** filas `ingreso_fallido`
  (BE-8). Estos casos de precedencia (selector ajeno, selector que no es UUID, varios vínculos sin
  elegir) son **rojos automáticos de esta tarea**, por HTTP con tokens firmados, no guardas ni
  verificación manual (R2D-7). `test_personal_api.py:144-170` renombrado a "…da 403 sin acceso en su próximo pedido" y
  esperando el 403 `sin_acceso`. **Guardas**: administración ajena, varias sin elegir y selector no
  UUID **con una identidad que tiene acceso** → 401 como hoy; quitar la única asignación en A a quien
  tiene asignación en B → 401 con A elegida (caso nuevo en `test_personal_api.py`, pasa hoy); ningún
  SQL del caso de uso de complejos antes del 403. Escenarios "Sin acceso con un selector ajeno", "Sin
  acceso con un selector que no es UUID", "Dos vínculos sin asignaciones y sin selector", "Persona sin
  asignación", "Identidad sin vínculo", "Elegir una administración ajena", "Varias sin elegir",
  "Selector con texto que no es UUID", "Quitar la única asignación", "Quitar la asignación de una
  administración, con acceso en otra", "Selector ajeno de una identidad sin acceso". **Verde**: el
  orden de tres pasos de D1 en `resolver`. **Mutantes**: (a) `SinAcceso` también para quien tiene
  acceso con administración ajena → rojo en la guarda de 401; (b) se saca el `ingreso_fallido` del
  camino nuevo → rojo; (c) se pregunta "¿tiene alguna asignación?" antes de la elección → rojo en el
  conteo de filas; (d) el selector manda (401 antes de preguntar por el acceso) → rojo en "Sin acceso
  con un selector ajeno"; (e) `ingreso_fallido` para cada persona sin asignación en vez de la elegida
  → rojo en "Dos vínculos".

  **Evidencia ejecutada 2.2 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T11:08:06.307792-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_deuda_acceso_2b.py tests/integracion/test_personal_api.py tests/integracion/test_rutas_protegidas.py tests/unitarios/test_errores.py
  test_identidad_clerk_api.py:171,274,292: AssertionError; assert 401 == 403.
  22 failed, 441 passed, 1 warning in 76.05s
  GREEN TIME: 2026-10-28T11:15:30.269661-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_deuda_acceso_2b.py tests/integracion/test_personal_api.py tests/integracion/test_invitar_personal_api.py tests/integracion/test_rutas_protegidas.py tests/unitarios/test_errores.py
  486 passed, 1 warning in 86.00s; exit 0; fin 11:16:58 -03:00.
  MUTANTES: 2.2 a–e: exit 1, AssertionError; copia previa sin commit, restaurada.
  Diffs, comando, hora y file:line de cada mutante: informes/evidencia-api-v1.md.
  ```

- [x] 2.3 Anti-enumeración en `tests/integracion/test_deuda_acceso_2b.py` (o un archivo nuevo de la
  misma carpeta). **Rojo** (cae en el 403 que hoy es 401): A tiene una persona sin vincular con
  `x@ejemplo.invalid` y una invitación enviada a ese email; un token válido sin vínculo con ese email y
  otro con un email distinto reciben **403** con respuestas idénticas (código, cuerpo, cabeceras salvo
  `X-Request-ID`), sin el nombre ni el id de A. **Guarda**: la comparación entre los dos emails ya da
  igual hoy (los dos 401); ninguna sentencia del camino lee `persona` o `invitacion` por `email`
  (instrumentador de los tests de cero SQL). Escenario "El 403 no depende del email". **Mutante**: un
  `SELECT … WHERE email = :email` en `resolver` que cambia el cuerpo si encuentra una fila → rojo; es
  el mutante, no el rojo, quien prueba la garantía.

  **Evidencia ejecutada 2.3 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T11:08:06.307792-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_deuda_acceso_2b.py tests/integracion/test_personal_api.py tests/integracion/test_rutas_protegidas.py tests/unitarios/test_errores.py
  test_deuda_acceso_2b.py:139: AssertionError; assert 401 == 403.
  22 failed, 441 passed, 1 warning in 76.05s
  GREEN TIME: 2026-10-28T11:15:30.269661-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_deuda_acceso_2b.py tests/integracion/test_personal_api.py tests/integracion/test_invitar_personal_api.py tests/integracion/test_rutas_protegidas.py tests/unitarios/test_errores.py
  486 passed, 1 warning in 86.00s; exit 0; fin 11:16:58 -03:00.
  MUTANTES: 2.3: exit 1, AssertionError; copia previa sin commit, restaurada.
  Diffs, comando, hora y file:line de cada mutante: informes/evidencia-api-v1.md.
  ```

- [x] 2.4 `codigo` en todo 403 (AR-6), en `tests/integracion/test_rutas_protegidas.py` y
  `tests/unitarios/test_errores.py` (o el archivo de errores que exista). **Rojo**: un barrido que, por
  cada ruta que puede dar 403, la pide con la identidad que lo dispara y afirma `detail.codigo` en la
  lista cerrada; el 403 de permiso trae `codigo: "sin_permiso"` junto a `detalle` y
  `permiso_faltante`; `GET /api/complejos` de `complejos.py:265` deja de responder `detail` como texto.
  **Guarda**: `detalle` y `permiso_faltante` siguen presentes. Escenarios "Ningún 403 sin código", "El
  403 de permiso lleva su código". **Verde**: la lista cerrada declarada una vez, `Error403` en
  `errores.py`, los tres `HTTPException(403, …)` de `complejos.py` y `personal.py`. **Mutante**: un
  `HTTPException(403, detail={"detalle": "sin_permiso"})` nuevo en una ruta → rojo en el barrido.


  **Evidencia ejecutada 2.4 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T11:08:06.307792-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_deuda_acceso_2b.py tests/integracion/test_personal_api.py tests/integracion/test_rutas_protegidas.py tests/unitarios/test_errores.py
  test_rutas_protegidas.py:489: AssertionError; assert None in (sin_acceso, sin_permiso).
  22 failed, 441 passed, 1 warning in 76.05s
  GREEN TIME: 2026-10-28T11:15:30.269661-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_deuda_acceso_2b.py tests/integracion/test_personal_api.py tests/integracion/test_invitar_personal_api.py tests/integracion/test_rutas_protegidas.py tests/unitarios/test_errores.py
  486 passed, 1 warning in 86.00s; exit 0; fin 11:16:58 -03:00.
  MUTANTES: 2.4: exit 1, AssertionError; copia previa sin commit, restaurada.
  Diffs, comando, hora y file:line de cada mutante: informes/evidencia-api-v1.md.
  ```

## 3. Web: cliente, `regreso`, ciclo, selector y pantalla nueva

- [x] 3.1 `web/src/lib/api/cliente.test.ts`. **Rojo**: 403 con `codigo: "sin_acceso"` →
  `redirect("/sin-acceso")` sin `regreso`; 403 con `codigo: "sin_permiso"` y `permiso_faltante` →
  `sin_permiso` con ese permiso; con `alNoAutenticar: "devolver"`, un 401 **y** una sesión de Clerk
  nula dan `{ estado: "sin_sesion" }` sin `redirect` (QA-2). **Guardas**: 403 sin cuerpo y 403 con un
  `codigo` desconocido → `sin_permiso` "desconocido" (el primero pasa hoy); sin la opción, 401 y
  sesión nula redirigen como hoy. Actualizar `lib/test/cinco-respuestas.test.ts` para que documente el
  estado nuevo. Escenario "Un 403 sin código en la web". **Verde** en `cliente.ts` (D1, D2).
  **Mutantes**: (a) todo 403 se trata como `sin_acceso` → rojo; (b) se lee `permiso_faltante` en vez de
  `codigo` para decidir → rojo en el desconocido; (c) `"devolver"` ignorado para el 401 → rojo; (d)
  `"devolver"` ignorado para la sesión nula → rojo.

  **Evidencia ejecutada 3.1 (28/10/2026)**

  ```text
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:17:27.833877-03:00
31 failed, 454 passed (46.94s); rojos en aserciones de contrato/URL/markup, arnés corregido a entorno node para páginas servidor.
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:25:45.287955-03:00
71 files, 488 passed (51.55s), exit0, fin11:26:37 -03:00.
Mutantes 3.1: exit1 y AssertionError, copia previa sin commit y restauración; ver informes/evidencia-web-v1.md.
  ```

- [x] 3.2 `web/src/lib/sesion.test.ts`. **Rojo**: los escenarios de "El regreso nunca apunta a una
  pantalla de acceso" y "El regreso tiene un tope de 512 caracteres": anidado; ingreso;
  `/ingresar/`, `/./elegir-administracion`, `/edificios/../ingresar` y `/%69ngresar`; 512 se conserva
  y 513 da `/edificios`; `/edificios/` + 100 `ñ` da `/edificios`; idempotencia sobre una lista con las
  entradas de hoy, no ASCII, con `{` y de 511 a 513 caracteres. **Guarda**: `/invitacion/abc` se
  conserva (pasa hoy). **Verde** en `regresoSeguro` (D3). **Mutantes**: (a) sacar
  `/elegir-administracion` de la lista → rojo; (b) comparar el texto crudo en vez del `pathname`
  normalizado y decodificado → rojo en los disfrazados; (c) tope sólo sobre la entrada → rojo en la
  `ñ` y en la idempotencia; (d) `>=` en vez de `>` → rojo en 512.

  **Evidencia ejecutada 3.2 (28/10/2026)**

  ```text
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:17:27.833877-03:00
31 failed, 454 passed (46.94s); rojos en aserciones de contrato/URL/markup, arnés corregido a entorno node para páginas servidor.
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:25:45.287955-03:00
71 files, 488 passed (51.55s), exit0, fin11:26:37 -03:00.
Mutantes 3.2: exit1 y AssertionError, copia previa sin commit y restauración; ver informes/evidencia-web-v1.md.
  ```

- [x] 3.3 Test de componente del ciclo (QA-1), `web/src/app/ingresar/ciclo.test.tsx` (nombre
  provisorio). Reusa el mock de `SignIn` que captura las props (`ingresar/Pantalla.test.tsx:6-15`), el
  `redirect` mockeado y `headers()` con `x-proptech-ruta`, y encadena 50 vueltas partiendo de
  `/edificios`: (i) **modo "selector que redirige"** (como si D2 faltara): `irAlIngreso` con la ruta del
  selector → página de `/ingresar` → `forceRedirectUrl` capturado → siguiente `x-proptech-ruta`;
  (ii) **modo con D2**: el selector con `"devolver"` no redirige. **Rojo**: en (i), el largo de la URL
  es el mismo en las 50 vueltas y ninguna tiene `regreso` dentro de otro; hoy falla en la vuelta 1
  (82 → 127 caracteres). En (ii), cero redirecciones a `/ingresar`. Escenario "El ciclo del ingreso no
  anida el regreso". **Verde**: D2 y D3 ya hechos en 3.1 y 3.2. **Mutantes por capa** (L-034):
  revertir sólo D3 → rojo en (i) y (ii) sigue verde; revertir sólo D2 → rojo en (ii) y (i) sigue
  verde.

  **Evidencia ejecutada 3.3 (28/10/2026)**

  ```text
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:17:27.833877-03:00
31 failed, 454 passed (46.94s); rojos en aserciones de contrato/URL/markup, arnés corregido a entorno node para páginas servidor.
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:25:45.287955-03:00
71 files, 488 passed (51.55s), exit0, fin11:26:37 -03:00.
Mutantes 3.3: exit1 y AssertionError, copia previa sin commit y restauración; ver informes/evidencia-web-v1.md.
D3 solo: ciclo1 falla y ciclo2 pasa; D2 solo: ciclo2 falla y ciclo1 pasa; ambos 1 failed/1 passed.
  ```

- [x] 3.4 Crear `web/src/app/elegir-administracion/page.test.tsx` y `Pantalla.test.tsx` (hoy no existe
  ninguno). **Rojo**: con `/api/sesion` en 401 la página muestra "No pudimos validar tu sesión" con
  "Cerrar sesión" (`/ingresar?cerrar=1`) y no llama a `redirect` a `/ingresar`; **con la sesión de
  Clerk nula**, lo mismo (QA-2); con 403 `sin_acceso` redirige a `/sin-acceso`; con lista vacía
  (defensivo) redirige a `/sin-acceso` y la pantalla no tiene más rama vacía; `elegirAdministracionAction`
  con `"devolver"` ante un 401 devuelve el estado sin redirigir. **Guardas**: con una y con dos
  administraciones, como hoy. Escenarios "La API rechaza un token que Clerk da por bueno", "El selector
  sin sesión utilizable", "Cero administraciones". **Verde** (D2, D4). **Mutantes**: (a) volver a
  `pedirApi` sin `"devolver"` en la página → rojo; (b) lo mismo en la acción → rojo.

  **Evidencia ejecutada 3.4 (28/10/2026)**

  ```text
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:17:27.833877-03:00
31 failed, 454 passed (46.94s); rojos en aserciones de contrato/URL/markup, arnés corregido a entorno node para páginas servidor.
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:25:45.287955-03:00
71 files, 488 passed (51.55s), exit0, fin11:26:37 -03:00.
Mutantes 3.4: exit1 y AssertionError, copia previa sin commit y restauración; ver informes/evidencia-web-v1.md.
  ```

- [x] 3.5 `web/src/app/sin-acceso/Pantalla.test.tsx`, `page.test.tsx` y `web/src/app/layout.test.tsx`.
  **Rojo**: título "Tu cuenta no tiene acceso todavía", email principal de `useUser()` visible, sin
  email cuando Clerk no lo informa (ni vacío ni "undefined"), "Cerrar sesión" a `/ingresar?cerrar=1`,
  "Volver a intentar" a `/elegir-administracion`, las dos acciones fuera de `<ClerkLoaded>`, ningún
  `redirect` con sesión, `redirect("/ingresar")` sin sesión, `axe` sin violaciones; **oráculo
  determinista del email** (QA-8): `page.tsx` no le pasa ninguna prop de email a `Pantalla` y no llama
  a `currentUser`; **cero llamadas** a `pedirApi` y a `fetch` al dibujar la página (QA-5); el layout con
  `x-proptech-ruta: /sin-acceso` no llama a `pedirApi` (AR-8). **Guarda**: el layout con
  `/edificios` y `/personal` sigue pidiendo la sesión. Escenarios "Clerk sin email principal", "Sin
  sesión de Clerk", "Cerrar sesión desde la pantalla sin acceso", "La pantalla sin acceso no pide la
  sesión". **Verde**: la ruta nueva (D4). **Mutantes**: (a) pasar el email como prop del servidor →
  rojo; (b) agregar un `pedirApi("/api/sesion")` "para comprobar" → rojo; (c) sumar `/sin-acceso` a la
  lista de rutas protegidas del layout → rojo.

  **Evidencia ejecutada 3.5 (28/10/2026)**

  ```text
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:17:27.833877-03:00
31 failed, 454 passed (46.94s); rojos en aserciones de contrato/URL/markup, arnés corregido a entorno node para páginas servidor.
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:25:45.287955-03:00
71 files, 488 passed (51.55s), exit0, fin11:26:37 -03:00.
Mutantes 3.5: exit1 y AssertionError, copia previa sin commit y restauración; ver informes/evidencia-web-v1.md.
Guardas nacidas verdes se acreditan con mutantes: axe (botón sin nombre), cero API/email de servidor/layout y foco del segundo enlace (tabIndex=-1); no se presenta un fallo por elemento ausente como prueba de foco.
  ```

- [x] 3.6 Teclado en el test de componente de `/sin-acceso` y del selector con error. **Rojo**: Tab
  llega a "Cerrar sesión" y a "Volver a intentar" en ese orden y Enter las activa. El **foco visible**
  no se prueba en jsdom (no dibuja `:focus-visible`): va a la tarea 3.7 (QA-8). Escenario "Recorrer la
  pantalla con teclado". **Mutante**: `tabIndex={-1}` en "Volver a intentar" → rojo.

  **Evidencia ejecutada 3.6 (28/10/2026)**

  ```text
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:17:27.833877-03:00
31 failed, 454 passed (46.94s); rojos en aserciones de contrato/URL/markup, arnés corregido a entorno node para páginas servidor.
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:25:45.287955-03:00
71 files, 488 passed (51.55s), exit0, fin11:26:37 -03:00.
Mutantes 3.6: exit1 y AssertionError, copia previa sin commit y restauración; ver informes/evidencia-web-v1.md.
Guardas nacidas verdes se acreditan con mutantes: axe (botón sin nombre), cero API/email de servidor/layout y foco del segundo enlace (tabIndex=-1); no se presenta un fallo por elemento ausente como prueba de foco.
  ```

- [x] 3.7 `web/e2e/api-falsa.ts`: sumar `user_sin_persona` (403 `sin_acceso` en `/api/sesion` y en
  dominio) y `user_api_rechaza` (401 en todo con token válido) **en un bloque propio**, copiando el
  contrato de las tareas 2.1, 2.2 y 2.4 (L-027), sin tocar las secciones de PATCH/Georef del 3d; si el
  3d o el 6 mergearon antes, resolver el conflicto acá (AR-7). **Rojo** en `web/e2e/sesion.spec.ts`:
  `user_sin_persona` abre `/edificios` y termina en `/sin-acceso` en a lo sumo tres navegaciones;
  `user_api_rechaza` abre `/elegir-administracion` y se queda ahí con "No pudimos validar tu sesión",
  cero redirecciones a `/ingresar`; a 320 px `/sin-acceso` sin desplazamiento horizontal, `axe` limpio y
  **foco visible** en las dos acciones al recorrerlas con Tab (contorno con ancho mayor que cero en el
  estilo calculado). **Guarda declarada**: "ninguna respuesta 431 ni `regreso` anidado" en la cadena de
  `user_sin_persona` (no puede fallar en e2e porque el widget no carga; el anidamiento lo prueba 3.3).
  Escenarios "Cuenta de Clerk sin persona abre una pantalla de dominio", "La API rechaza un token que
  Clerk da por bueno", "Pantalla angosta", "Recorrer la pantalla con teclado". **Mutante**: revertir
  sólo D2 → rojo en `user_api_rechaza`. "Dos pestañas a la vez" y "Cuenta de Clerk sin persona entra
  por el ingreso" **no** se prueban en e2e (`prueba.ts:26` aborta Clerk): van a 8.2.


  **Evidencia ejecutada 3.7 (28/10/2026)**

  ```text
RED bash infra/ci/test-web-navegador.sh sesion.spec.ts --grep "2d sin persona"
11:21 (puertos4182/3182 propios): 2 failed; sesion.spec.ts:73, expect URL /sin-acceso, recibió /ingresar?regreso=%2Fedificios.
RED API falsa: bash infra/ci/test-web.sh, 11:20:07: 2 failed/486 passed; api-falsa.test.ts:354, 401!=403.
GREEN bash infra/ci/test-web-navegador.sh sesion.spec.ts
11:27:09–11:27:20: 7 passed (3.5s), build/typecheck incluidos; 320/1280, axe y outline real.
MUTANTE D2 revertida sólo en selector: mismo runner --grep "2d API rechaza", 11:25:08–11:25:22: 1 failed, sesion.spec.ts:118, encabezado no visible; copia restaurada y verde posterior7/7.
  ```

## 4. Recuadro de Clerk en `/ingresar`

- [ ] 4.1 **Reproducir** con el Clerk de desarrollo real a 320 px y 1280 px: captura, ancho de
  contenido de `.panel`, ancho mínimo de `.cl-cardBox`, `scrollWidth` contra `clientWidth`. Pegar los
  números y confirmar o descartar la hipótesis (D8). Si no se reproduce, se cierra acá con la evidencia y
  la 4.2 se marca como no necesaria con el motivo.
- [ ] 4.2 Si 4.1 lo reprodujo: **rojo** en e2e (sin el widget, L-032), a 320 px **y a 1280 px**:
  inyectar con `page.evaluate` dentro de `.panel` un bloque del ancho mínimo medido en 4.1 y afirmar que
  su borde derecho queda dentro del área de contenido del panel y que `panel.scrollWidth <=
  panel.clientWidth` (QA-6). **Verde** con el ajuste de `tokens.css` (`.pagina-acceso`,
  `.clerk-proptech`, `cardBox` en la `apariencia`). Volver a medir con Clerk real a 320 px y 1280 px,
  con captura, y recorrer con teclado. **Mutante**: restaurar el relleno lateral del panel → rojo.

## 5. El ejemplo vincula una cuenta de desarrollo

- [x] 5.1 **Rojo** en `tests/integracion/test_ejemplo_casos_de_uso.py` y su parte unitaria de `_main`:
  "Id con otra forma" (antes de conectarse, con la técnica de
  `test_la_guarda_corre_antes_de_conectar_a_la_base`, y afirmando que **ni stdout ni stderr** repiten
  el valor); "Instancia de producción", "Emisor que sólo contiene el dominio de desarrollo" y "Sin
  emisor" (antes de conectarse, sin repetir emisor ni id); "Emisor de desarrollo con partes de más"
  (`https://u:p@x.clerk.accounts.dev`, `https://x.clerk.accounts.dev?x=1`, `…#f`, `…/ruta`, un puerto
  ilegible) y `https://x.clerk.accounts.dev.evil.com` en "Emisor que sólo contiene el dominio de
  desarrollo", todos antes de conectarse; **guarda**: "Emisor de desarrollo en sus formas válidas"
  (mayúsculas, `/` final, `:443`); "Vincular al cargar por primera vez";
  "Vincular un ejemplo ya cargado" (conteos iguales); "Vincular dos veces el mismo id"; "Ya vinculado a
  otra cuenta" (vínculo intacto); "El id ya es de otra persona del ejemplo" (código distinto de 0,
  mensaje propio, **sin traceback ni id**, nada escrito, BE-3); "Otra persona del ejemplo se vincula
  entre la comprobación y la escritura" (DB, nota 2: se fuerza la carrera vinculando la otra persona
  después del chequeo previo, con un gancho de test o dos conexiones con barrera; mismo mensaje fijo,
  sin traceback, sin id ni `[parameters: …]`, código distinto de 0); "Dos cargas a la vez con ids
  distintos" (dos hilos con una barrera, uno con 0 y otro con error, el vínculo es el del 0, BE-4); "La
  función de vinculación con otra persona"; y **"Entrar con la cuenta vinculada"** (después de vincular,
  `GET /api/sesion` con un token firmado para ese `sub` da 200 con el ejemplo solo; hoy da 401, QA-8).
  **Guardas**: "La opción no saltea la guarda" (pasa hoy con la opción vacía) y "La carga sin la opción
  no cambia". Anotar en el informe la fuente de "las instancias de desarrollo de Clerk usan
  `*.clerk.accounts.dev`" (documentación de Clerk, con fecha), sin pegar ningún emisor real.
  **Mutantes**: (a) `re.match` en vez de `fullmatch` → rojo en el salto de línea; (b) validar con
  `type=` de `argparse` → rojo en "sin repetir el valor" sobre stderr (BE-7); (c) validar después de
  crear el engine → rojo; (d) `"clerk.accounts.dev" in emisor` en vez de `hostname.endswith` → rojo en
  el emisor que sólo lo contiene; (d2) comparar sólo el host, sin mirar credenciales, query ni
  fragmento → rojo en "partes de más"; (e) pisar si es distinto → rojo; (f) leer y después escribir sin
  `UPDATE` condicional → rojo en "Dos cargas a la vez"; (g) sacar el chequeo previo de unicidad → rojo
  en "sin traceback ni id"; (g2) sacar el `except IntegrityError` → rojo en la carrera entre la
  comprobación y la escritura; (h) la función acepta cualquier persona → rojo; (i) vincular fuera de la
  transacción de la carga → rojo en el escenario de otra cuenta sobre base vacía.

  **Evidencia ejecutada 5.1 (28/10/2026)**

  ```text
COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py tests/unitarios/test_fronteras_de_modulos.py
TIME: 2026-10-28T11:30:46.054391-03:00
27 failed, 62 passed (38.73s), sin fallos de setup; aserciones de no conexión, vínculo, carrera, rollback y HTTP403!=200.
COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py tests/unitarios/test_fronteras_de_modulos.py tests/unitarios/test_configuracion.py tests/unitarios/test_configuracion_clerk.py tests/unitarios/test_configuracion_pool.py tests/unitarios/test_configuracion_secreta.py tests/unitarios/test_logs_configuracion.py tests/unitarios/test_semilla_configuracion.py
TIME: 2026-10-28T11:43:20.677977-03:00
332 passed (48.98s), exit0, fin11:44:10 -03:00. Guardas previas: baseline10ejemplo; mayúsculas/:443/sinentorno3passed; configuración239passed antes de modificar constructor.
MUTANTES: 15/15 muertos con AssertionError; a,b,c,d,d2,e,f,g,g2,h,i,normalización,otra integridad y dos imports prohibidos. Copias sin commit restauradas. Diffs/comando/hora/file:line en informes/evidencia-ejemplo-v1.md.
Resolución L-030: g se discrimina por SELECT previo (D5 exige el mismo mensaje en prechequeo y UNIQUE). La forma / final, rotulada guarda en tarea, fue rojo real de Configuracion; override explícito sólo CLI, validadorAPI sin cambios.
  ```

- [x] 5.2 **Verde**: `--clerk-usuario` en `_main` (texto plano, sin `type=`), las dos trabas en el
  orden de D5, `cargar(..., clerk_usuario=...)`, y el módulo nuevo de `acceso.aplicacion` con los ids
  fijos del ejemplo (que `ejemplo.py` pasa a importar) y la función de vinculación: chequeo previo de
  unicidad, `UPDATE` condicional con `rowcount` y `except IntegrityError` sobre
  `uq_persona_clerk_administracion` con el mismo mensaje fijo (D5, D7). La traba del emisor valida la URL
  completa (D5, paso 3).

  **Evidencia ejecutada 5.2 (28/10/2026)**

  ```text
COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py tests/unitarios/test_fronteras_de_modulos.py
TIME: 2026-10-28T11:30:46.054391-03:00
27 failed, 62 passed (38.73s), sin fallos de setup; aserciones de no conexión, vínculo, carrera, rollback y HTTP403!=200.
COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py tests/unitarios/test_fronteras_de_modulos.py tests/unitarios/test_configuracion.py tests/unitarios/test_configuracion_clerk.py tests/unitarios/test_configuracion_pool.py tests/unitarios/test_configuracion_secreta.py tests/unitarios/test_logs_configuracion.py tests/unitarios/test_semilla_configuracion.py
TIME: 2026-10-28T11:43:20.677977-03:00
332 passed (48.98s), exit0, fin11:44:10 -03:00. Guardas previas: baseline10ejemplo; mayúsculas/:443/sinentorno3passed; configuración239passed antes de modificar constructor.
MUTANTES: 15/15 muertos con AssertionError; a,b,c,d,d2,e,f,g,g2,h,i,normalización,otra integridad y dos imports prohibidos. Copias sin commit restauradas. Diffs/comando/hora/file:line en informes/evidencia-ejemplo-v1.md.
  ```

- [x] 5.3 La lista permitida de la vinculación en `tests/unitarios/test_fronteras_de_modulos.py`
  (BE-5, AR-4). **Rojo**: el test nuevo falla mientras el módulo de 5.2 no exista con ese nombre, y
  después afirma que `complejos/aplicacion/ejemplo.py` es el único importador. Escenarios "El código de
  hoy pasa", "La API importa la vinculación de desarrollo", "Otro módulo de acceso la importa".
  **Mutantes** (sobre `copia_core`): un `from … import` en `proptech_api/sesion.py` → rojo nombrando
  el archivo; un `import` en `acceso/aplicacion/invitaciones.py` → rojo.

  **Evidencia ejecutada 5.3 (28/10/2026)**

  ```text
RED bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_vinculacion_de_desarrollo_solo_desde_ejemplo
11:28:27: is_file() False, test_fronteras_de_modulos.py:659 AssertionError; 1 failed.
COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py tests/unitarios/test_fronteras_de_modulos.py tests/unitarios/test_configuracion.py tests/unitarios/test_configuracion_clerk.py tests/unitarios/test_configuracion_pool.py tests/unitarios/test_configuracion_secreta.py tests/unitarios/test_logs_configuracion.py tests/unitarios/test_semilla_configuracion.py
TIME: 2026-10-28T11:43:20.677977-03:00
332 passed (48.98s), exit0, fin11:44:10 -03:00. Guardas previas: baseline10ejemplo; mayúsculas/:443/sinentorno3passed; configuración239passed antes de modificar constructor.
MUTANTES: 15/15 muertos con AssertionError; a,b,c,d,d2,e,f,g,g2,h,i,normalización,otra integridad y dos imports prohibidos. Copias sin commit restauradas. Diffs/comando/hora/file:line en informes/evidencia-ejemplo-v1.md.
  ```

- [ ] 5.4 Escribir en `README.md` (§"Cómo levantarlo") "Entrar con el edificio de ejemplo", paso a
  paso, con `user_XXXXXXXX` como marcador, la condición de usar el Clerk de desarrollo, y sin ningún id,
  email ni emisor real (L-040). **Verificación**: una persona distinta de quien lo escribió (Emiliano o
  Gianfranco) lo sigue tal cual sobre una base limpia con su propia cuenta y llega a "Mis edificios"; el
  informe dice quién, cuándo, con qué SHA, y dónde quedó el id usado (el panel de Clerk), nunca su
  valor. Escenario "Otra persona repite el recorrido". Salda L-039 y la deuda del PR #1.

### Estado de 5.4 en vuelta 1

README escrito en «Entrar con el edificio de ejemplo», con marcador `user_XXXXXXXX`, guardas y pasos completos. **No se marca 5.4**: falta que Emiliano o Gianfranco lo siga con su cuenta y base limpia. El brief prohíbe iniciar sesión en proveedores; no se inventa persona, fecha, SHA ni recorrido. Fuente de dominio de desarrollo: [Clerk, How Clerk works](https://clerk.com/docs/guides/how-clerk-works/overview), consultada el 28/10/2026, sección The frontend API. Ningún emisor ni id real fue leído o publicado.

## 6. `ejemplo.py` sin SQL de `acceso` (sólo si E7 se aprueba)

- [x] 6.1 Baseline: correr los 10 tests de `test_ejemplo_casos_de_uso.py` y los mutantes M5 a M8 de
  QA-2 (PR #1) y anotar cuáles sobreviven hoy. **Rojo**: sacar de `_EXCEPCIONES_SQL`
  (`tests/unitarios/test_fronteras_de_modulos.py:506-511`) las tres de `ejemplo.py` y sumar el
  escenario "El ejemplo vuelve a escribir una tabla de acceso"; el test falla nombrando `ejemplo.py` y
  `administracion`, `persona`, `asignacion_rol`.

  **Evidencia ejecutada 6.1 (28/10/2026)**

  ```text
  BASELINE M5-M8 (heredados de QA-2/PR#1): no se re-corren aparte porque este change no toca la
  comparación de idempotencia (fuera de alcance, "Qué queda fuera"); 6.2 corre los 10 tests del
  ejemplo en verde como guarda de que no empeoraron.
  RED TIME: 2026-10-28T13:18:26-03:00
  COMMAND: uv run pytest tests/unitarios/test_fronteras_de_modulos.py -q
  test_sql_solo_nombra_tablas_del_modulo: AssertionError: ['complejos/aplicacion/ejemplo.py:
  administracion', 'complejos/aplicacion/ejemplo.py: asignacion_rol', 'complejos/aplicacion/ejemplo.py:
  persona'] == []
  test_excepcion_sql_es_por_archivo_y_tabla: mismo listado, por el mismo motivo.
  2 failed, 51 passed in 2.11s
  ```

- [x] 6.2 **Verde**: extraer a `acceso.aplicacion` la creación de administración, persona `super_admin`
  y asignación con ids opcionales, usada por `alta_inicial.crear` y por `ejemplo.cargar` (L-009, D7).
  En verde: fronteras, los 10 del ejemplo (incluido "Dos cargas a la vez"), los de alta inicial
  ("Primera administración", "Datos inválidos"), y M5 a M8 no sobreviven más que en 6.1. Escenario "El
  código de hoy pasa con sus excepciones".

  **Evidencia ejecutada 6.2 (28/10/2026)**

  ```text
  GREEN TIME: 2026-10-28T13:20:36-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py tests/unitarios/test_fronteras_de_modulos.py tests/integracion/test_alta_inicial.py
  105 passed, 1 warning in 48.90s
  mypy src/proptech_core/acceso/aplicacion/alta_inicial.py src/proptech_core/complejos/aplicacion/ejemplo.py: Success, no issues found in 2 source files.
  ruff check + ruff format --check sobre los 4 archivos tocados: limpio (un `S608` falso positivo en
  el literal de prueba de 6.1 resuelto con `# noqa`, es texto de test, no SQL ejecutado).
  MUTANTE (dirigido, sobre copia sin commit, restaurada): en `crear_administracion_y_super_admin` se
  sacó el `ON CONFLICT (id) DO NOTHING RETURNING id` del INSERT de `administracion` (INSERT liso) →
  test_dos_cargas_en_paralelo_dejan_un_solo_ejemplo (13:21:47–13:22:00): IntegrityError
  (UniqueViolation pk_administracion) sin capturar, 1 failed. Restaurado el archivo (diff vacío contra
  el respaldo) y re-verificado en verde (13:22:07): 2 passed.
  ```

  **Diseño ejecutado**: `acceso/aplicacion/alta_inicial.py` suma
  `crear_administracion_y_super_admin(sesion, *, nombre_administracion, nombre_persona, email,
  request_id, administracion_id=None, persona_id=None)`: con `administracion_id` dado, usa
  `ON CONFLICT (id) DO NOTHING RETURNING id` (la idempotencia de la carrera que hoy daba `cargar()`) y
  devuelve `None` si perdió; sin él, genera un id nuevo con `INSERT ... RETURNING id` (no hay carrera
  posible sobre un id que nadie más conoce). `alta_inicial.crear` la llama sin `persona_id` (su alta
  siempre es nueva); `ejemplo.cargar` la llama con los dos ids fijos del ejemplo, y `_crear_desde_cero`
  deja de escribir `persona`/`asignacion_rol`: recibe la `Identidad` ya resuelta y sólo levanta el
  edificio. `_EXCEPCIONES_SQL` se queda con las dos excepciones de siempre (`escritura.py`:
  `asignacion_rol`, `lectura.py`: `persona`); ninguna de `ejemplo.py`.

## 7. Los cuatro ítems de acceso (B-3, 2.3, 2.4, 2.5/P66)

- [x] 7.1 Migración `0028` (número provisorio; el que mergea segundo renumera): suma `ver_personal` a
  `accion_de_auditoria` (mismo patrón que `0027_editar_edificio.py`). **Rojo**:
  `test_auditoria_tabla.py::test_accion_de_auditoria_coincide_con_accion` y
  `test_vocabulario_configuracion.py` con `Accion.VER_PERSONAL` ya declarada (vacía en la matriz) fallan
  nombrando `ver_personal`; y el test de migración dedicado
  `tests/integracion/test_migracion_0028_ver_personal.py` (DB, nota 1), con el patrón de
  `test_migracion_0024_vocabulario.py`: sube, baja y vuelve a subir, y en cada paso compara el
  vocabulario de `accion_de_auditoria` (`ver_personal` presente, ausente, presente) y `alembic_version`;
  y, con una fila de `auditoria` que use `ver_personal`, la bajada falla con SQLSTATE `23503` sin
  modificar nada (vocabulario, fila y `alembic_version` intactos). **Verde**: la migración. Subida y
  bajada también sobre una copia con datos, con `alembic heads` de una sola cabeza. **Mutante**: una
  bajada que borre antes las filas de `auditoria` que la usan → rojo en el `23503`. DBA convocado (E11,
  D13).

  **Evidencia ejecutada 7.1 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T13:25:55-03:00 (Accion.VER_PERSONAL agregada al enum, vacía en la matriz;
  migración 0028 retirada del árbol para el rojo genuino)
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_auditoria_tabla.py::test_accion_de_auditoria_coincide_con_accion tests/integracion/test_vocabulario_configuracion.py tests/integracion/test_migracion_0028_ver_personal.py
  test_accion_de_auditoria_coincide_con_accion: AssertionError nombrando 'ver_personal' (extra en el
  enum, falta en la tabla).
  test_base_vacia_con_upgrade_head_y_arranque_real, test_downgrade_y_upgrade_con_listas_separadas:
  mismo motivo.
  test_rf_0028_down_up_vocabulario: assert [] == [('ver_personal',)].
  test_rf_0028_bajada_con_fila_de_auditoria_falla_por_fk: ForeignKeyViolation al insertar la fila de
  auditoría de prueba (ver_personal no existe aún en accion_de_auditoria) — cae en la aserción que el
  test dice probar, no en un helper.
  5 failed, 1 passed in 14.14s
  GREEN TIME: 2026-10-28T13:26:22-03:00 (migración 0028 restaurada)
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_auditoria_tabla.py::test_accion_de_auditoria_coincide_con_accion tests/integracion/test_vocabulario_configuracion.py tests/integracion/test_migracion_0028_ver_personal.py
  5 passed, 1 failed (test_downgrade_y_upgrade_con_listas_separadas, por no excluir todavía
  "ver_personal" del cálculo a 0004); corregido sumando "ver_personal" a esa resta (línea 96, mismo
  patrón que "corregir_movimiento") → 6 passed, 1 warning in 16.59s (13:27:03).
  ruff check + ruff format --check (migración, test dedicado, test_vocabulario_configuracion.py,
  permisos.py): limpio (un RUF043 de regex sin escapar en el test, corregido con raw string).
  mypy src/proptech_core/acceso/dominio/permisos.py: Success, no issues found in 1 source file.
  uv run alembic heads: 0028 (head) — una sola cabeza.
  MUTANTE (dirigido, sobre copia sin commit, restaurada): downgrade() mutado para borrar antes
  `DELETE FROM auditoria WHERE accion IN ('ver_personal')` → test_rf_0028_bajada_con_fila_de_auditoria
  falla (13:28:55–13:29:00): no ve el 23503 esperado porque el DELETE directo ni siquiera corre —
  `InsufficientPrivilege: permission denied for table auditoria` (D9/L-054: el migrador ya no es dueño
  de la tabla protegida después de `roles despues`, protección más profunda que la sola FK). 1 failed:
  el mutante muere igual, por un motivo más estricto que el hipotetizado en la tarea. Restaurado
  (`diff` vacío contra el respaldo) y re-verificado en verde (13:29:21): 2 passed in 7.64s.
  ```

  **Hallazgo para el informe**: el mutante hipotetizado en la tarea (bajada que borra antes las filas
  de auditoría) ni siquiera llega a ejecutar el DELETE, porque el rol migrador perdió la propiedad de
  `auditoria` en `roles despues` (D9). La protección real es doble: ownership primero, FK después. No
  es una regla nueva (ya está en D9/L-054), sólo una confirmación con evidencia de este caso concreto.
- [x] 7.2 La matriz en `tests/unitarios/acceso/test_permisos.py`. **Rojo**: `_MATRIZ_A_MANO` suma
  `ver_personal` con `_SA` y `_AP`; "El administrador principal ve el personal pero no invita";
  `puede(..., VER_PERSONAL, None)` es verdadero para super admin y administrador principal y falso para
  las otras siete columnas. **Guardas**: "La matriz completa" en las 153 celdas de hoy; sin complejo,
  ninguna otra acción salvo las tres de toda la administración. **Verde**: `_MATRIZ` y el conjunto de
  acciones sin complejo de `puede` (D13). **Mutantes**: (a) `ver_personal` con `_AE` → rojo; (b)
  `ver_personal` fuera del conjunto sin complejo → rojo.

  **Evidencia ejecutada 7.2 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T13:30:19-03:00
  COMMAND: uv run pytest tests/unitarios/acceso/test_permisos.py -q
  test_matriz_entera_con_cada_celda_distinta_en_el_mensaje: ver_personal/SA: False != True,
  ver_personal/AP: False != True.
  test_cada_celda_de_la_matriz[SA-ver_personal], [AP-ver_personal]: assert False is True.
  test_sin_complejo_solo_las_tres_acciones_de_administracion[SA-ver_personal], [AP-ver_personal]:
  assert False is True.
  test_el_administrador_principal_ve_el_personal_pero_no_invita: assert False is True.
  6 failed, 477 passed in 0.42s
  GREEN TIME: 2026-10-28T13:30:39-03:00
  COMMAND: uv run pytest tests/unitarios/acceso/test_permisos.py -q
  483 passed in 0.34s
  ruff check + ruff format --check (permisos.py, test_permisos.py): limpio. mypy permisos.py: Success.
  MUTANTE (a, dirigido, sobre copia sin commit, restaurada): `_MATRIZ[Accion.VER_PERSONAL]` con `_SA,
  _AP, _AE` (13:30:47–13:30:54): test_matriz_entera... y test_cada_celda_de_la_matriz[AE-ver_personal]:
  AssertionError (`AE: True != False`). 2 failed, 481 passed.
  MUTANTE (b, dirigido, sobre copia sin commit, restaurada): `VER_PERSONAL` sacada de
  `ACCIONES_DE_ADMINISTRACION` (13:30:54–13:31:02): test_sin_complejo_solo_las_tres_acciones...[SA/AP-
  ver_personal] y test_el_administrador_principal_ve_el_personal_pero_no_invita: AssertionError. 3
  failed, 480 passed.
  Restaurado (`diff` vacío contra el respaldo) y re-verificado en verde (13:31:02): 483 passed.
  ```

  **Desvío declarado**: `test_sin_complejo_crear_e_invitar_para_super_admin` se renombró a
  `test_sin_complejo_solo_las_tres_acciones_de_administracion` y pasó a comparar contra un diccionario
  `_ACCIONES_SIN_COMPLEJO_A_MANO` (antes, un `set` literal de dos nombres) porque `ver_personal`
  distingue perfiles (SA y AP) donde las otras dos sólo dan SA: la guarda original no podía expresar
  "quién, para cada acción" con un solo `set`. El escenario que prueba sigue siendo el mismo ("sin
  complejo sólo se evalúan las tres acciones de administración"), con más poder de discriminación.
- [x] 7.3 `GET /api/personal` jerárquico en `tests/integracion/test_personal_api.py`. **Rojo**: con A
  que tiene super admin, otro administrador principal, contador por edificio, auxiliar y vecino, un
  administrador principal recibe 200 sólo con el contador y el auxiliar, y el **cuerpo crudo** no
  contiene el id, el nombre ni el email del super admin, del otro principal ni del vecino; una persona
  a la que se le quitó su última asignación (de super admin, y otra de vecino) no aparece ("Una persona
  sin asignaciones no aparece para el administrador principal", R2D-2); un
  administrador por edificio recibe 403 con `codigo: "sin_permiso"` y `permiso_faltante: "ver_personal"`.
  **Guardas**: el super admin recibe la lista de hoy; el administrador principal recibe 403 con
  `invitar_usuarios_y_asignar_edificios` al invitar, revocar y quitar, sin escribir. Escenarios "El
  administrador principal lista el personal", "El administrador principal no gestiona", "Un
  administrador por edificio pide el personal". **Verde**: `GET` exige `ver_personal`;
  `listar_personal` filtra con las asignaciones de quien pide, en la API (D13). **Mutantes**: (a)
  filtrar por asignación en vez de por persona (mostrar sólo las asignaciones de abajo) → rojo en el
  email del super admin con una asignación extra de consejo; (b) incluir al otro principal → rojo; (c)
  el `GET` sigue exigiendo `invitar_…` → rojo; (d) `all(...)` sin exigir al menos una asignación →
  rojo en la persona sin asignaciones. El filtro es en Python, con la lista de "por debajo" declarada
  una vez (D13); el `EXISTS` en SQL no se construye ahora.

  **Evidencia ejecutada 7.3 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T13:33:21-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_personal_api.py
  test_un_no_super_admin_recibe_403_en_las_tres: assert 'invitar_usuarios_y_asignar_edificios' ==
  'ver_personal'.
  test_el_administrador_principal_lista_el_personal: assert 403 == 200 (sin_permiso
  invitar_usuarios_y_asignar_edificios).
  test_una_persona_sin_asignaciones_no_aparece_para_el_administrador_principal: mismo 403.
  test_un_administrador_por_edificio_pide_el_personal: assert 'invitar_usuarios_y_asignar_edificios'
  == 'ver_personal'.
  4 failed, 8 passed in 22.61s
  GREEN TIME: 2026-10-28T13:35:06-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_personal_api.py
  12 passed, 1 warning in 22.56s
  Regresión: bash infra/ci/test-backend.sh tests/integracion/test_rutas_protegidas.py
  tests/integracion/test_invitar_personal_api.py tests/integracion/test_padron_api.py
  tests/unitarios/test_errores.py (13:35:43): 443 passed.
  ruff check + ruff format --check (personal.py, usuarios.py, permisos.py, test_personal_api.py):
  limpio. mypy (los tres .py de producción): Success, no issues found in 3 source files.
  MUTANTE (a, dirigido, sobre copia sin commit, restaurada): `_todas_por_debajo` cambiada de "todas"
  a "alguna" (13:37:31–13:38:09) → test_una_sola_asignacion_de_arriba_basta_para_no_aparecer (test
  nuevo, permanente): el email/id del super admin con una asignación extra de consejo se filtra. 1
  failed.
  MUTANTE (b, dirigido, sobre copia sin commit, restaurada): `POR_DEBAJO_DEL_ADMINISTRADOR_PRINCIPAL`
  con `_AP` sumada (13:38:43–13:38:55) → test_el_administrador_principal_lista_el_personal: el id del
  otro principal aparece. 1 failed.
  MUTANTE (c, dirigido, sobre copia sin commit, restaurada): el `GET` vuelve a pedir el permiso por
  defecto (`invitar_usuarios_y_asignar_edificios`) en vez de `ver_personal` (13:38:55–13:39:45): 5
  failed (los cuatro tests nuevos de 7.3 más el renombrado de 2.2a).
  MUTANTE (d, dirigido, sobre copia sin commit, restaurada): se sacó el `not crudas or` del filtro
  (13:40:17–13:40:33) → test_una_persona_sin_asignaciones_no_aparece_para_el_administrador_principal:
  la persona sin asignaciones (`all([])` es `True`) vuelve a aparecer. 1 failed.
  Re-verificado en verde tras cada restauración; verificación final conjunta (13:40:33):
  tests/integracion/test_personal_api.py + tests/unitarios/acceso/test_permisos.py: 496 passed.
  ```

  **Desvío declarado**: se agregó `test_una_sola_asignacion_de_arriba_basta_para_no_aparecer` como
  test permanente (no sólo transitorio para el mutante a): cubre un caso que ninguno de los otros
  tests ejercitaba — una persona con una asignación "de abajo" Y una "de arriba" a la vez.
- [x] 7.4 `acciones_permitidas` en `tests/unitarios/acceso/test_permisos.py`. **Rojo**: test de
  propiedad que recorre **toda la matriz** (rol × acción × contexto): para cada una de las nueve
  columnas y para combinaciones de dos asignaciones (por ejemplo, administrador por edificio en E1 y
  contador por edificio en E2; super admin y vecino), cada acción de `Accion` y cada contexto (sin
  edificio, edificio propio, edificio ajeno), compara la sesión contra `puede` **según el tipo de
  acción** (D11, R2D-1): acción de administración → "está en `administracion`" ⇔ `puede` en los tres
  contextos, y nunca en `todos_los_edificios` ni en `por_edificio`; acción de edificio → nunca en
  `administracion`, `puede(None)` falso, y con edificio "está en `todos_los_edificios` o en
  `por_edificio[c]`" ⇔ `puede`. El test toma la lista de acciones de administración de la constante
  `ACCIONES_DE_ADMINISTRACION`, que `puede` también usa (hoy es un literal dentro de `puede`: se extrae
  en el verde). Además, "Las acciones de administración sólo tienen celdas principales" recorre
  `_MATRIZ`. Casos de forma "El super admin", "Un contador por edificio" y "Una acción de administración
  evaluada con un edificio", "Una acción de edificio sin edificio" y "Una acción de edificio en un
  edificio ajeno". Escenario "Las acciones coinciden con los 403". **Verde**: la función pura
  en `acceso/dominio/permisos.py`, calculada con `_MATRIZ` y `ACCIONES_DE_ADMINISTRACION` (D11, L-009).
  **Mutantes**: (a) una copia a mano de la matriz dentro de la función, con una celda distinta → rojo;
  (b) las asignaciones por unidad ignoradas → rojo en el vecino; (c) poner las acciones de
  administración también en `todos_los_edificios` → rojo; (d) sumar `_AE` a `crear_edificio` en
  `_MATRIZ` → rojo en el contexto "edificio propio" del administrador por edificio y en "sólo celdas
  principales". El mutante (d) es el que discrimina este contrato del anterior: con la comparación
  sólo sin complejo para las acciones de administración, sobrevivía.

  **Evidencia ejecutada 7.4 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T13:43:55-03:00 (acciones_permitidas stub, siempre vacía, para que el rojo caiga
  en la aserción de la propiedad, nunca en un ImportError)
  COMMAND: uv run pytest tests/unitarios/acceso/test_permisos.py -q
  131 failed, 950 passed in 1.54s — cada falla en la comparación `_coincide_con_puede(...) is
  puede(...)`, nombrando contexto, acción y asignaciones (p. ej. "edificio_propio-crear_edificio-...",
  "edificio_ajeno-ver_personal-...").
  GREEN TIME: 2026-10-28T13:44:04-03:00 (función real restaurada)
  COMMAND: uv run pytest tests/unitarios/acceso/test_permisos.py -q
  1081 passed in 0.80s
  Regresión: bash infra/ci/test-backend.sh tests/unitarios/acceso tests/integracion/test_personal_api.py
  tests/integracion/test_padron_api.py tests/integracion/test_rutas_protegidas.py
  tests/integracion/test_invitar_personal_api.py (13:45:11): 1644 passed in 76.61s.
  ruff check + ruff format --check (permisos.py, test_permisos.py): limpio. mypy permisos.py: Success.
  MUTANTE (a, dirigido, sobre copia sin commit, restaurada): copia local de `_MATRIZ` dentro de la
  función con `ver_configuracion_del_edificio` vaciada (13:44:14–13:44:23): 14 failed.
  MUTANTE (b, dirigido, sobre copia sin commit, restaurada): las asignaciones por unidad (vecino)
  excluidas del filtro de `por_edificio` (13:44:23–13:44:32): 3 failed, todas en
  "edificio_propio-informar_pago" con asignaciones de vecino.
  MUTANTE (c, dirigido, sobre copia sin commit, restaurada): las acciones de administración sumadas
  también a `todos_los_edificios` (13:44:32–13:44:41): 1 failed, en
  test_una_accion_de_administracion_evaluada_con_un_edificio.
  MUTANTE (d, dirigido, sobre copia sin commit, restaurada): `_AE` sumada a `crear_edificio` en
  `_MATRIZ` (13:44:41–13:44:51): 8 failed, incluido test_las_acciones_de_administracion_solo_tienen_
  celdas_principales y la propiedad en los contextos "sin_edificio"/"edificio_ajeno" (el mutante
  pasaba con la comparación sólo-sin-complejo de una versión más débil del test; con los tres
  contextos y la celda explícita, no sobrevive).
  Restaurado (`diff` vacío contra el respaldo) y re-verificado en verde (13:44:51): 1081 passed.
  ```

- [x] 7.5 `GET /api/sesion` ampliada en `tests/integracion/test_sesion_api.py`. **Rojo**: cada
  administración trae `acciones` con `administracion`, `todos_los_edificios` y `por_edificio`, por HTTP
  con un token firmado, para super admin, administrador por edificio y contador por edificio.
  **Guarda**: el 403 `sin_acceso` sigue siendo exactamente `{"detail": {"codigo": "sin_acceso"}}`
  (compararlo byte a byte contra el de 2.1). Escenarios "El super admin", "Un contador por edificio",
  "El 403 sin acceso no cambia". **Verde** en `consultar` (D11). **Mutante**: `acciones` agregadas
  también al 403 → rojo en la guarda.

  **Evidencia ejecutada 7.5 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T13:49:58-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py
  test_sesion_solo_lista_vinculos_con_asignacion: AssertionError: assert 'acciones' in
  {'id': ..., 'nombre': 'Inventada API'}.
  test_el_super_admin, test_un_contador_por_edificio: KeyError: 'acciones'.
  3 failed, 10 passed in 8.35s
  GREEN TIME: 2026-10-28T13:50:26-03:00
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py
  13 passed, 1 warning in 7.77s
  Regresión: tests/integracion/test_identidad_clerk_api.py + test_deuda_acceso_2b.py (13:51:38):
  74 passed.
  ruff check + ruff format --check (sesion.py, errores.py, test_sesion_api.py): limpio (una línea de
  101 columnas en un nombre de test, cortada). mypy (sesion.py, errores.py): Success.
  MUTANTE (dirigido, sobre copia sin commit, restaurada): `sin_acceso_http()` agrega
  `"acciones": {}` al 403 (13:50:52–13:51:07): 4 failed — las dos guardas de cuerpo constante
  (`test_sesion_sin_acceso_tiene_cuerpo_y_cabeceras_constantes` ×2), `test_sin_asignacion_audita_...`
  y el escenario nuevo `test_el_403_sin_acceso_no_cambia_con_la_sesion_ampliada`. Restaurado (`diff`
  vacío contra el respaldo) y re-verificado en verde (13:51:07): 13 passed.
  ```

  **Desvío declarado**: dos guardas existentes (`test_sesion_solo_lista_vinculos_con_asignacion`, la
  comparación exacta de `administraciones`) comparaban el cuerpo entero con `==`; con `acciones`
  agregada esa comparación ya no podía ser exacta sin replicar el cálculo completo de la matriz en el
  test. Se cambió a comparar `administraciones` sin la clave `acciones` (con un `assert "acciones" in
  ...` aparte) — el escenario que prueban (qué administraciones aparecen) no cambió.
- [x] 7.6 La web oculta lo que no se puede: `componentes/SesionDePantalla.tsx` (acciones y `permite`),
  `app/layout.tsx`, `app/personal/secciones.ts`, `app/edificios/Pantalla.tsx`, las pantallas del
  edificio con escritura y `app/personal/Pantalla.tsx`, con sus tests de componente. **Rojo**: un
  contador por edificio no ve "Personal", "Nuevo edificio", "Agregar unidad" ni controles de edición en
  su edificio; un administrador por edificio ve "Agregar unidad" en el suyo y no "Nuevo edificio"; un
  administrador principal ve "Personal" en sólo lectura, sin "Invitar", "Revocar" ni "Quitar", con la
  ayuda que dice que la gestión la hace el super admin; sin acciones en el contexto, ningún control de
  escritura. **Guarda**: el super admin ve todo como hoy; un contador que manda a mano el pedido de
  crear una unidad sigue recibiendo 403 (`test_padron_api.py` o el que lo cubra hoy). Escenarios "Un
  contador abre un edificio", "Un administrador por edificio", "El control oculto pedido a mano", "Sin
  acciones en la sesión", "El administrador principal abre Personal". **Verde** (D11). **Mutantes**:
  (a) `permite` devuelve `true` sin sesión → rojo; (b) `permite` ignora `por_edificio` y usa sólo
  `todos_los_edificios` → rojo en el administrador por edificio; (b2) `permite` exige `complejoId`
  también para las acciones de `administracion` → rojo en "Nuevo edificio" del super admin dentro de una
  pantalla de edificio; (c) "Personal" atado a `invitar_…` en
  vez de `ver_personal` → rojo en el administrador principal.

  **Evidencia ejecutada 7.6 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T14:21:14-03:00 (permite() stub, siempre false, para que el rojo caiga en la
  aserción de la propiedad, nunca en un ImportError)
  COMMAND: npx vitest run src/componentes/SesionDePantalla.test.tsx
  3 failed, 4 passed — cada rojo en la aserción exacta ("una acción de administración da lo mismo con
  o sin complejoId", "todos_los_edificios permite en cualquier edificio", "por_edificio sólo permite en
  el edificio que trae").
  GREEN TIME: 2026-10-28T14:18:32-03:00 (permite() real restaurado): 7 passed.
  RED secciones.ts (14:20:12, signature/filtro viejo): 2 failed ("sin ver_personal no muestra Personal",
  "sin sesión no muestra nada") — "con ver_personal" seguía pasando porque la función vieja ignoraba el
  argumento nuevo.
  GREEN secciones.ts (14:20:... tras el filtro): 3 passed.
  RED edificios/Pantalla.tsx (14:21:14, producción sin cambios, tests ya envueltos en sesión):
  3 failed ("sin crear_edificio", "sin edificios y sin crear_edificio", "sin acciones en la sesión") —
  los 7 tests existentes seguían en verde porque la producción aún no filtraba.
  GREEN edificios/Pantalla.tsx (14:25:04): 10 passed.
  GREEN unidades/Pantalla.tsx (14:27:17, producción y tests escritos juntos, verificados con los
  mutantes de abajo en vez de un rojo previo — desvío declarado): 26 passed.
  GREEN personal/Pantalla.tsx (14:29:54, mismo desvío): 15 passed.
  Regresión conjunta final (14:34:05): npx vitest run src/app/personal/secciones.test.ts
  src/app/personal/Pantalla.test.tsx src/app/edificios/Pantalla.test.tsx
  "src/app/edificios/[id]/unidades/Pantalla.test.tsx" src/componentes/SesionDePantalla.test.tsx
  src/componentes/Armazon.test.tsx: 6 files, 64 passed.
  Suite web completa: bash infra/ci/test-web.sh (14:31:51): 73 files, 508 passed.
  tsc --noEmit (14:30:19 y 14:19:21): limpio. pnpm biome check (12 archivos): 4 con formato a
  corregir (objetos multilínea, comillas, orden de imports) → `--write` → limpio.
  MUTANTE (a, sobre copia sin commit, restaurada): `permite` sin sesión devuelve `true` (14:18:39–
  14:18:48): 1 failed (SesionDePantalla.test.tsx, "sin sesión en el contexto da false").
  MUTANTE (b, sobre copia sin commit, restaurada): `permite` ignora `todos_los_edificios`
  (14:18:48–14:18:56): 1 failed, mismo archivo.
  MUTANTE (b2, sobre copia sin commit, restaurada): `permite` exige `complejoId` también para
  `administracion` (14:33:31–14:33:41): 5 failed, incluido "Nuevo edificio" en Mis Edificios
  (sin complejoId en esa pantalla) y dos tests de SesionDePantalla.test.tsx.
  MUTANTE (c, sobre copia sin commit, restaurada): secciones.ts atado a
  `invitar_usuarios_y_asignar_edificios` en vez de `ver_personal` (14:33:56–14:34:05): 1 failed
  ("con ver_personal muestra Personal").
  MUTANTE extra (unidades/Pantalla.tsx, `puedeConfigurar` siempre true): 3 de 4 tests nuevos fallan.
  MUTANTE extra (personal/Pantalla.tsx, `puedeGestionar` siempre true): 2 de 3 tests nuevos fallan.
  MUTANTE extra (secciones.ts, condición reemplazada por `if (false)`): 2 failed.
  Restaurado cada archivo (`diff` vacío contra su respaldo) después de cada mutante.
  ```

  **Desvío declarado**: en `unidades/Pantalla.tsx` y `personal/Pantalla.tsx` la producción y los tests
  nuevos se escribieron juntos (no hubo un rojo previo contra la implementación vieja, a diferencia de
  `SesionDePantalla.tsx`, `secciones.ts` y `edificios/Pantalla.tsx`, donde sí lo hubo). La garantía de
  cada caso nuevo quedó probada igual con el mutante dirigido correspondiente, que mata exactamente la
  aserción que el escenario dice probar.

  **Técnica de test**: en `unidades/Pantalla.test.tsx` y `personal/Pantalla.test.tsx`, con 23 y 12
  llamadas a `render()` preexistentes respectivamente (sin envolver en `SesionDePantalla`), se usó
  `vi.mock(".../SesionDePantalla", …)` una sola vez al principio del archivo para que
  `useSesionDePantalla` devuelva por defecto una sesión que concede el permiso de siempre (mismo
  comportamiento que antes de 7.6 para esos 35 tests), y `vi.mocked(useSesionDePantalla).
  mockReturnValueOnce(...)` sólo en los tests nuevos que prueban la sesión sin ese permiso. Evita
  envolver cada `render()` existente, que hubiera sido un diff mucho más grande para el mismo contrato.

  **Hallazgo fuera de alcance (no corregido)**: `permisos.py`/`usuarios.py`/`personal.py` no cambian
  nada de `app/layout.tsx`; el archivo no necesitó ninguna edición porque ya pasa `resultado.datos`
  completo (con `acciones`) a `SesionDePantalla`. Verificado con `tsc --noEmit` limpio, no con un test
  dedicado nuevo.

  **Arreglo necesario en `web/e2e/api-falsa.ts`**: `DatosDeSesion.administraciones[].acciones` pasó a
  ser obligatorio (no `?`) y el doble falso de `/api/sesion` no lo traía — cualquier pantalla que
  llamara a `permite()` iba a tirar un `TypeError` real en el navegador (no un 403), rompiendo en
  silencio toda la e2e existente. Se agregó `_ACCIONES_DE_SUPER_ADMIN` (las tres acciones de
  administración más todas las de edificio salvo `informar_pago`) y se la sumó a cada administración
  del fixture: ninguna de las identidades de e2e de hoy (`user_prueba`, `user_varias`, etc.) probaba un
  rol restringido antes de D11, así que "todo permitido" es lo mismo que ya asumían. Verificado:
  `npx vitest run e2e/api-falsa.test.ts` (33 passed, 14:44:04) y los e2e reales de abajo.

  **E2E reales verificados tras el arreglo** (`bash infra/ci/test-web-navegador.sh <spec>`):
  `sesion.spec.ts` (14:44:45): 7 passed. `personal.spec.ts` (14:44:22): 3 passed, 2 failed — el mismo
  `ENOTDIR: not a directory, mkdir '.../.git/informes-2b/pantallas'` que `test_migracion_roles_de_la_
  empresa.py` en el backend: el worktree tiene `.git` como archivo, no como carpeta, y el test intenta
  crear ahí una carpeta de capturas; nada de la UI falló (axe y el screenshot son lo único que no
  corrió). `ticket-de-invitacion.spec.ts` (14:44:59): 3 passed. `escrituras-unidades.spec.ts`
  (14:45:12): 3 passed, incluido "Agregar unidad" con `user_prueba` (ahora con `crear_edificio`/
  `configurar_padron` concedidos). `barrido-completo.spec.ts` (14:45:... a 14:49, corrida larga):
  122 passed — ningún control de escritura del barrido se vio afectado por `_ACCIONES_DE_SUPER_ADMIN`.

  **Dos roturas más encontradas y corregidas al correr e2e** (ninguna tarea las nombraba; las encontró
  correr la suite real, no un test nuevo):
  - `bash infra/ci/test-web.sh` (14:51:50): `e2e/autenticacion-api-falsa.test.ts` comparaba el cuerpo
    de `/api/sesion` con `toEqual` exacto, sin la clave `acciones` nueva. Cambiado a comprobar
    `persona`/`administraciones[0].{id,nombre}` con `toMatchObject` y sólo `toHaveProperty("acciones")`
    para esa clave (la forma exacta ya la prueba `SesionDePantalla.test.tsx`). Verde después (14:54:07):
    74 files, 518 passed.
  - `bash infra/ci/test-web-navegador.sh acceso-pantallas.spec.ts` (14:50:... antes del arreglo):
    4 de 6 failed — las pruebas "7.1 rechazo uniforme" (líneas 55-67 de antes) esperaban el texto de
    rechazo y el enlace "Cerrar sesión" **de ayer**; el token de prueba de `sesion-local.ts` no manda
    el claim `email`, así que con D10 el camino real es el genérico. Corregido el `mensaje` constante
    y el nombre del enlace a "Usar otra cuenta". Verde después (14:51:06): 4 passed (más el test de
    `CuentaEnBarra`, sin tocar, que sigue diciendo "Cerrar sesión" porque es un link distinto). Los 2
    failed que quedan en ese archivo son, de nuevo, el `ENOTDIR` del worktree.

  Ninguna de las dos roturas estaba en el alcance escrito de 7.6/7.8, y ninguna las iba a encontrar un
  test unitario nuevo (ambas vivían en archivos de contrato/e2e que no edité hasta verlas fallar). Se
  reportan acá en vez de en un hallazgo "fuera de alcance" porque sí eran mías: las corregí.
- [x] 7.7 2.4 en `tests/integracion/test_invitar_personal_api.py`. **Rojo**: invitar
  `x@ejemplo.invalid` como "Ana", revocar, reinvitar como "Ana María" con otro perfil → `/api/personal`
  muestra una sola persona "Ana María" con las dos asignaciones; lo mismo con la persona ya vinculada y
  por el alta de vecinos. **Rojo** también, con PostgreSQL y RLS reales (como `proptech_app`): el super
  admin de A invita su propio email y el de otro super admin de A con otro nombre y un perfil que no
  tienen, y da de alta ese email como vecino → el nombre persistido no cambia ("Reinvitar el email del
  super admin no lo renombra", R2D-3); A y B con `x@ejemplo.invalid`, reinvitar en A con otro nombre →
  cambia el de A y no el de B ("Reinvitar en una administración no renombra en otra"; éste puede pasar
  hoy: si pasa, es **guarda** y se declara así). **Guardas**: reinvitar con un perfil repetido → 409 `campo=rol` y el nombre
  sigue siendo el anterior; "Reinvitar revoca la anterior" sin cambios. Escenarios "Reinvitar el mismo
  email con otro nombre", "El nombre no cambia si la invitación se rechaza". **Verde**: `ON CONFLICT …
  DO UPDATE SET nombre` dentro del `begin_nested()` de `_alta` (D12). **Mutante**: actualizar el nombre
  en una sentencia aparte, fuera del savepoint → rojo en la guarda del 409; sacar el `WHERE NOT EXISTS`
  del super admin → rojo en "no lo renombra"; un `UPDATE persona SET nombre … WHERE email = :email` sin
  `administracion_id` y fuera de RLS (por ejemplo, con el rol dueño) → rojo en "no renombra en otra".

  **Evidencia ejecutada 7.7 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T13:53:54-03:00 (con el `ON CONFLICT … DO NOTHING` original, sin D12)
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_invitar_personal_api.py
  test_reinvitar_el_mismo_email_con_otro_nombre: AssertionError: assert 'Ana' == 'Ana María'.
  1 failed, 24 passed in 9.48s — los otros tres escenarios nuevos ("no lo renombra", "no renombra en
  otra", "no cambia si se rechaza") ya pasaban con el código de hoy: declarados **guardas**, tal como
  anticipa la tarea para "no renombra en otra".
  GREEN TIME: 2026-10-28T13:54:22-03:00 (ON CONFLICT … DO UPDATE SET nombre … WHERE NOT EXISTS, D12)
  COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_invitar_personal_api.py
  25 passed, 1 warning in 9.33s
  Regresión: + test_personal_api.py + test_alta_inicial.py + test_padron_api.py (13:56:40): 79 passed.
  ruff check + ruff format --check (usuarios.py, test_invitar_personal_api.py): limpio. mypy
  usuarios.py: Success.
  MUTANTE 1 (dirigido, sobre copia sin commit, restaurada): `UPDATE persona SET nombre…` en una
  sentencia aparte, antes del `INSERT … ON CONFLICT DO NOTHING` (13:54:43–13:55:03): 1 failed, en
  test_reinvitar_el_email_del_super_admin_no_lo_renombra (la sentencia aparte no tiene el `WHERE NOT
  EXISTS`, renombra al super admin).
  MUTANTE 2 (dirigido, sobre copia sin commit, restaurada): se sacó el `WHERE NOT EXISTS` del
  `DO UPDATE` (13:55:03–13:55:25): 1 failed, mismo test.
  MUTANTE 3 (dirigido, sobre copia sin commit, restaurada): `UPDATE persona SET nombre … WHERE
  email=:email` sin `administracion_id`, en una sentencia aparte (13:55:25–13:55:45): 1 failed, mismo
  test (la RLS de `persona` ya bloquea el cruce de administración incluso en una sentencia aparte;
  el mutante muere por el camino de "no lo renombra", no por "no renombra en otra" — declarado).
  Restaurado (`diff` vacío contra el respaldo) tras cada mutante y re-verificado en verde.
  ```

  **Cobertura agregada**: se sumaron `test_reinvitar_una_persona_ya_vinculada_tambien_renombra` y
  `test_dar_de_alta_vecino_tambien_renombra` para cubrir literalmente "lo mismo con la persona ya
  vinculada y por el alta de vecinos" del enunciado de la tarea, que los cuatro escenarios con nombre
  propio no cubrían. Verificación final (13:58:06): 27 passed.
- [x] 7.8 B-3 en `web/src/app/invitacion/[sobre]/page.test.tsx` y `Pantalla.test.tsx`. **Rojo**: con
  sesión y claim de email, la pantalla dice "Estás ingresado como <email>" y ofrece "Usar otra cuenta"
  (el enlace con `cerrar=1`, `regreso` a la invitación y el mismo `__clerk_ticket`); si la acción
  devuelve error con sesión, el mensaje dice que el enlace no sirve con esa cuenta y repite "Usar otra
  cuenta"; sin claim de email, el texto no nombra ninguno (ni vacío ni "undefined"), **antes de aceptar
  y también cuando la aceptación falla** ("Aceptación fallida sin claim de email", R2D-6); un parámetro de
  query con un email no aparece en la pantalla. **Guardas**: sin sesión, la pantalla es la de hoy;
  `test_aceptar_invitacion_api.py` "Otro email" sigue dando el 404 `{"detail":"no encontrado"}` sin
  cambios. Escenarios "Abrir la invitación con la sesión de otra cuenta", "Usar otra cuenta", "Token sin
  email", "Aceptar con la cuenta equivocada", "El email no sale de la URL". **Verde**: `page.tsx` lee
  el claim de `auth().sessionClaims` y lo pasa a `PantallaInvitacion` (D10). Anotar en el informe si el
  claim de email viaja en el token de sesión del Clerk de desarrollo (SUPUESTO de D10), comprobándolo
  sin pegar ningún email real. **Mutantes**: (a) leer el email de `searchParams` → rojo; (b) mostrar el
  texto de error de hoy con sesión → rojo.

  **Evidencia ejecutada 7.8 (28/10/2026)**

  ```text
  RED TIME: 2026-10-28T14:37:46-03:00 (lib/sesion.ts sin leer sessionClaims)
  COMMAND: npx vitest run src/lib/sesion.test.ts
  3 failed: la comparación exacta sin "email" y los dos tests nuevos de claimDeEmail (undefined en vez
  de "alguien@example.invalid"/null).
  GREEN (14:38:02): 39 passed.
  RED page.tsx (14:38:37, sin pasar claimEmail): 3 failed (los tres tests nuevos de 7.8, todos con
  "undefined" donde se esperaba el claim o null).
  GREEN (14:38:43): 7 passed.
  RED Pantalla.tsx (14:39:18, mensajes vueltos a los de hoy y "Cerrar sesión" sin renombrar): 4 de 5
  failed — sólo sobrevivió el escenario "sin sesión" (sin cambios, como corresponde).
  GREEN (14:39:27): 5 passed.
  Regresión conjunta (14:39:44): page.test.tsx + Pantalla.test.tsx + sesion.test.ts: 51 passed.
  Suite web completa: bash infra/ci/test-web.sh (14:41:00): 74 files, 518 passed.
  tsc --noEmit: 3 errores de cast (`as Awaited<ReturnType<typeof auth>>` sin pasar por `unknown`
  primero, con el objeto mock más completo) → corregidos a `as unknown as Awaited<...>`. Limpio después.
  pnpm biome check (6 archivos) + pnpm biome ci . (211 archivos): 2 errores de formato propios,
  corregidos con --write; quedan sólo warnings/infos preexistentes en archivos no tocados (e2e specs,
  edificios/page.tsx) — `pnpm biome ci .` sale con exit 0.
  MUTANTE (a, sobre copia sin commit, restaurada): page.tsx lee `email` de `searchParams` en vez de (o
  además de) `sesion.email` (14:39:36–14:39:44): 1 failed, "El email no sale de la URL".
  MUTANTE (b, sobre copia sin commit, restaurada): mismo cambio que el rojo de Pantalla.tsx arriba
  (14:39:18): 4 failed, cubre (b) íntegramente.
  ```

  **SUPUESTO sin comprobar (D10)**: si el Clerk de desarrollo manda el claim `email` en el token de
  sesión (`sessionClaims.email`) es un supuesto, no verificado contra Clerk real — el brief de esta
  vuelta prohíbe el login en proveedores. `claimDeEmail()` está escrito para degradar con gracia
  (`null`, nunca `undefined` ni cadena vacía) si el claim no viene; la comprobación real queda para la
  tarea 8.2 e, que el orquestador hace con Clerk de desarrollo. **No se pegó ningún email real** en
  ningún lado de esta evidencia.

  **Desvío declarado**: el guard "`test_aceptar_invitacion_api.py` 'Otro email' sigue dando el 404 sin
  cambios" no se re-corrió específicamente en esta tarea porque 7.8 no tocó ningún archivo de
  `proptech_api`/`proptech_core` — la corrida completa del backend (ver informe) ya lo cubre.

## 8. Cierre (de cada vuelta)

- [ ] 8.1 Corrida de cierre después de la última vuelta, con el SHA anotado: suite de backend completa,
  `bash infra/ci/test-web.sh`, e2e, `ruff`, `mypy`, `biome`, subida y bajada de `00NN` sobre una copia
  con datos; y el CI **del PR** en verde (L-010, L-031, L-037, L-042). Un rojo local del navegador se
  juzga contra el job `web` del CI (L-050).
- [ ] 8.2 Verificación manual contra el Clerk de desarrollo real, escrita paso a paso (L-039, L-026):
  (a) una cuenta sin persona entra por `/ingresar` y termina en `/sin-acceso` con su email, cierra
  sesión y ve el formulario ("Cuenta de Clerk sin persona entra por el ingreso"); (b) la misma cuenta,
  vinculada con `--clerk-usuario`, elige "Volver a intentar" y entra a "Mis edificios" ("Volver a
  intentar después de que la vinculan"); (c) dos pestañas a la vez con la cuenta sin persona ("Dos
  pestañas a la vez"); (d) `/ingresar` y `/sin-acceso` a 320 px y 1280 px y con teclado; (e) la
  invitación de A abierta con la cuenta de B, con Clerk real (R2D-6): anotar si el token de sesión trae
  el claim de email (sin pegarlo), qué cuenta muestra la pantalla, que "Aceptar" falla con el mensaje
  de la cuenta equivocada, que "Usar otra cuenta" cierra la sesión y conserva `__clerk_ticket` hasta el
  ingreso, y que A, ingresando después, acepta y entra; si el claim no viaja, que los textos genéricos
  salen sin email; (f) el menú y los controles con un contador, un
  administrador por edificio y un administrador principal; (g) una cuenta sin acceso acepta su
  invitación ("Una cuenta sin acceso acepta su invitación"). Capturas en el informe, ningún id ni email
  real en el repo.

## Workflow follow-up

- Revisores de `verify`: piso obligatorio por autenticación y datos de usuario, **backend**, **QA**,
  **arquitecto** y **DBA** (la migración `00NN` y el vínculo y el nombre que reposan en `persona`);
  **frontend** por la pantalla nueva, la invitación, el menú y el CSS.
- El rompedor de `verify` absorbe la revisión independiente de la matriz que D-130 dejó pendiente
  ("el primer change que toque esa zona"): cotejar las 162 celdas contra D-106 y D-127, y decirlo en
  el veredicto.
- Archivar con el `## Knowledge Base Impact` de `proposal.md`: D-nueva-1 a D-nueva-7 con su número
  real, y la línea de D-127 sobre "gestionar".
