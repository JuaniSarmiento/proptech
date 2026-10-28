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

- [ ] 1.1 Rebasar sobre `main` y fijar el baseline antes de tocar nada: `alembic heads` con una sola
  cabeza (`0027` o la que haya mergeado el 3d o el 6), y en verde
  `bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_deuda_acceso_2b.py tests/integracion/test_personal_api.py tests/integracion/test_invitar_personal_api.py tests/integracion/test_ejemplo_casos_de_uso.py tests/integracion/test_auditoria_tabla.py tests/unitarios/test_fronteras_de_modulos.py tests/unitarios/acceso`
  y `bash infra/ci/test-web.sh`. Pegar conteos y SHA. Listar con `rg` los tests que hoy afirman 401
  para "token válido sin vínculo", "vinculada sin asignación" y "quitar la única asignación"
  (incluido `test_personal_api.py:144-170`): son los rojos de la tarea 2.

## 2. API: el 403 `sin_acceso`

- [ ] 2.1 `GET /api/sesion` en `tests/integracion/test_sesion_api.py`, por HTTP con tokens firmados de
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
- [ ] 2.2 La precedencia en una ruta de dominio (`GET /api/complejos`), en
  `tests/integracion/test_identidad_clerk_api.py`. **Rojo**: sin persona → 403, línea
  `ingreso_sin_vinculo` sin email ni sub en claro y ninguna fila de auditoría; persona sin asignación y
  sin otra administración → 403 y **exactamente una** fila `ingreso_fallido`; sin persona con
  `X-Proptech-Administracion` de B → 403; vinculada en A sin asignaciones con selector de B → 403, cero
  filas `ingreso_fallido` y ninguna fila de B leída; sin acceso con `no-es-uuid` → 403, nunca 401 ni
  422; dos vínculos sin asignaciones (A y B) y sin selector → 403 y **cero** filas `ingreso_fallido`
  (BE-8); `test_personal_api.py:144-170` renombrado a "…da 403 sin acceso en su próximo pedido" y
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
- [ ] 2.3 Anti-enumeración en `tests/integracion/test_deuda_acceso_2b.py` (o un archivo nuevo de la
  misma carpeta). **Rojo** (cae en el 403 que hoy es 401): A tiene una persona sin vincular con
  `x@ejemplo.invalid` y una invitación enviada a ese email; un token válido sin vínculo con ese email y
  otro con un email distinto reciben **403** con respuestas idénticas (código, cuerpo, cabeceras salvo
  `X-Request-ID`), sin el nombre ni el id de A. **Guarda**: la comparación entre los dos emails ya da
  igual hoy (los dos 401); ninguna sentencia del camino lee `persona` o `invitacion` por `email`
  (instrumentador de los tests de cero SQL). Escenario "El 403 no depende del email". **Mutante**: un
  `SELECT … WHERE email = :email` en `resolver` que cambia el cuerpo si encuentra una fila → rojo; es
  el mutante, no el rojo, quien prueba la garantía.
- [ ] 2.4 `codigo` en todo 403 (AR-6), en `tests/integracion/test_rutas_protegidas.py` y
  `tests/unitarios/test_errores.py` (o el archivo de errores que exista). **Rojo**: un barrido que, por
  cada ruta que puede dar 403, la pide con la identidad que lo dispara y afirma `detail.codigo` en la
  lista cerrada; el 403 de permiso trae `codigo: "sin_permiso"` junto a `detalle` y
  `permiso_faltante`; `GET /api/complejos` de `complejos.py:265` deja de responder `detail` como texto.
  **Guarda**: `detalle` y `permiso_faltante` siguen presentes. Escenarios "Ningún 403 sin código", "El
  403 de permiso lleva su código". **Verde**: la lista cerrada declarada una vez, `Error403` en
  `errores.py`, los tres `HTTPException(403, …)` de `complejos.py` y `personal.py`. **Mutante**: un
  `HTTPException(403, detail={"detalle": "sin_permiso"})` nuevo en una ruta → rojo en el barrido.

## 3. Web: cliente, `regreso`, ciclo, selector y pantalla nueva

- [ ] 3.1 `web/src/lib/api/cliente.test.ts`. **Rojo**: 403 con `codigo: "sin_acceso"` →
  `redirect("/sin-acceso")` sin `regreso`; 403 con `codigo: "sin_permiso"` y `permiso_faltante` →
  `sin_permiso` con ese permiso; con `alNoAutenticar: "devolver"`, un 401 **y** una sesión de Clerk
  nula dan `{ estado: "sin_sesion" }` sin `redirect` (QA-2). **Guardas**: 403 sin cuerpo y 403 con un
  `codigo` desconocido → `sin_permiso` "desconocido" (el primero pasa hoy); sin la opción, 401 y
  sesión nula redirigen como hoy. Actualizar `lib/test/cinco-respuestas.test.ts` para que documente el
  estado nuevo. Escenario "Un 403 sin código en la web". **Verde** en `cliente.ts` (D1, D2).
  **Mutantes**: (a) todo 403 se trata como `sin_acceso` → rojo; (b) se lee `permiso_faltante` en vez de
  `codigo` para decidir → rojo en el desconocido; (c) `"devolver"` ignorado para el 401 → rojo; (d)
  `"devolver"` ignorado para la sesión nula → rojo.
- [ ] 3.2 `web/src/lib/sesion.test.ts`. **Rojo**: los escenarios de "El regreso nunca apunta a una
  pantalla de acceso" y "El regreso tiene un tope de 512 caracteres": anidado; ingreso;
  `/ingresar/`, `/./elegir-administracion`, `/edificios/../ingresar` y `/%69ngresar`; 512 se conserva
  y 513 da `/edificios`; `/edificios/` + 100 `ñ` da `/edificios`; idempotencia sobre una lista con las
  entradas de hoy, no ASCII, con `{` y de 511 a 513 caracteres. **Guarda**: `/invitacion/abc` se
  conserva (pasa hoy). **Verde** en `regresoSeguro` (D3). **Mutantes**: (a) sacar
  `/elegir-administracion` de la lista → rojo; (b) comparar el texto crudo en vez del `pathname`
  normalizado y decodificado → rojo en los disfrazados; (c) tope sólo sobre la entrada → rojo en la
  `ñ` y en la idempotencia; (d) `>=` en vez de `>` → rojo en 512.
- [ ] 3.3 Test de componente del ciclo (QA-1), `web/src/app/ingresar/ciclo.test.tsx` (nombre
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
- [ ] 3.4 Crear `web/src/app/elegir-administracion/page.test.tsx` y `Pantalla.test.tsx` (hoy no existe
  ninguno). **Rojo**: con `/api/sesion` en 401 la página muestra "No pudimos validar tu sesión" con
  "Cerrar sesión" (`/ingresar?cerrar=1`) y no llama a `redirect` a `/ingresar`; **con la sesión de
  Clerk nula**, lo mismo (QA-2); con 403 `sin_acceso` redirige a `/sin-acceso`; con lista vacía
  (defensivo) redirige a `/sin-acceso` y la pantalla no tiene más rama vacía; `elegirAdministracionAction`
  con `"devolver"` ante un 401 devuelve el estado sin redirigir. **Guardas**: con una y con dos
  administraciones, como hoy. Escenarios "La API rechaza un token que Clerk da por bueno", "El selector
  sin sesión utilizable", "Cero administraciones". **Verde** (D2, D4). **Mutantes**: (a) volver a
  `pedirApi` sin `"devolver"` en la página → rojo; (b) lo mismo en la acción → rojo.
- [ ] 3.5 `web/src/app/sin-acceso/Pantalla.test.tsx`, `page.test.tsx` y `web/src/app/layout.test.tsx`.
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
- [ ] 3.6 Teclado en el test de componente de `/sin-acceso` y del selector con error. **Rojo**: Tab
  llega a "Cerrar sesión" y a "Volver a intentar" en ese orden y Enter las activa. El **foco visible**
  no se prueba en jsdom (no dibuja `:focus-visible`): va a la tarea 3.7 (QA-8). Escenario "Recorrer la
  pantalla con teclado". **Mutante**: `tabIndex={-1}` en "Volver a intentar" → rojo.
- [ ] 3.7 `web/e2e/api-falsa.ts`: sumar `user_sin_persona` (403 `sin_acceso` en `/api/sesion` y en
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

- [ ] 5.1 **Rojo** en `tests/integracion/test_ejemplo_casos_de_uso.py` y su parte unitaria de `_main`:
  "Id con otra forma" (antes de conectarse, con la técnica de
  `test_la_guarda_corre_antes_de_conectar_a_la_base`, y afirmando que **ni stdout ni stderr** repiten
  el valor); "Instancia de producción", "Emisor que sólo contiene el dominio de desarrollo" y "Sin
  emisor" (antes de conectarse, sin repetir emisor ni id); "Vincular al cargar por primera vez";
  "Vincular un ejemplo ya cargado" (conteos iguales); "Vincular dos veces el mismo id"; "Ya vinculado a
  otra cuenta" (vínculo intacto); "El id ya es de otra persona del ejemplo" (código distinto de 0,
  mensaje propio, **sin traceback ni id**, nada escrito, BE-3); "Dos cargas a la vez con ids
  distintos" (dos hilos con una barrera, uno con 0 y otro con error, el vínculo es el del 0, BE-4); "La
  función de vinculación con otra persona"; y **"Entrar con la cuenta vinculada"** (después de vincular,
  `GET /api/sesion` con un token firmado para ese `sub` da 200 con el ejemplo solo; hoy da 401, QA-8).
  **Guardas**: "La opción no saltea la guarda" (pasa hoy con la opción vacía) y "La carga sin la opción
  no cambia". Anotar en el informe la fuente de "las instancias de desarrollo de Clerk usan
  `*.clerk.accounts.dev`" (documentación de Clerk, con fecha), sin pegar ningún emisor real.
  **Mutantes**: (a) `re.match` en vez de `fullmatch` → rojo en el salto de línea; (b) validar con
  `type=` de `argparse` → rojo en "sin repetir el valor" sobre stderr (BE-7); (c) validar después de
  crear el engine → rojo; (d) `"clerk.accounts.dev" in emisor` en vez de `hostname.endswith` → rojo en
  el emisor que sólo lo contiene; (e) pisar si es distinto → rojo; (f) leer y después escribir sin
  `UPDATE` condicional → rojo en "Dos cargas a la vez"; (g) sacar el chequeo previo de unicidad → rojo
  en "sin traceback ni id"; (h) la función acepta cualquier persona → rojo; (i) vincular fuera de la
  transacción de la carga → rojo en el escenario de otra cuenta sobre base vacía.
- [ ] 5.2 **Verde**: `--clerk-usuario` en `_main` (texto plano, sin `type=`), las dos trabas en el
  orden de D5, `cargar(..., clerk_usuario=...)`, y el módulo nuevo de `acceso.aplicacion` con los ids
  fijos del ejemplo (que `ejemplo.py` pasa a importar) y la función de vinculación: chequeo previo de
  unicidad y `UPDATE` condicional con `rowcount` (D5, D7).
- [ ] 5.3 La lista permitida de la vinculación en `tests/unitarios/test_fronteras_de_modulos.py`
  (BE-5, AR-4). **Rojo**: el test nuevo falla mientras el módulo de 5.2 no exista con ese nombre, y
  después afirma que `complejos/aplicacion/ejemplo.py` es el único importador. Escenarios "El código de
  hoy pasa", "La API importa la vinculación de desarrollo", "Otro módulo de acceso la importa".
  **Mutantes** (sobre `copia_core`): un `from … import` en `proptech_api/sesion.py` → rojo nombrando
  el archivo; un `import` en `acceso/aplicacion/invitaciones.py` → rojo.
- [ ] 5.4 Escribir en `README.md` (§"Cómo levantarlo") "Entrar con el edificio de ejemplo", paso a
  paso, con `user_XXXXXXXX` como marcador, la condición de usar el Clerk de desarrollo, y sin ningún id,
  email ni emisor real (L-040). **Verificación**: una persona distinta de quien lo escribió (Emiliano o
  Gianfranco) lo sigue tal cual sobre una base limpia con su propia cuenta y llega a "Mis edificios"; el
  informe dice quién, cuándo, con qué SHA, y dónde quedó el id usado (el panel de Clerk), nunca su
  valor. Escenario "Otra persona repite el recorrido". Salda L-039 y la deuda del PR #1.

## 6. `ejemplo.py` sin SQL de `acceso` (sólo si E7 se aprueba)

- [ ] 6.1 Baseline: correr los 10 tests de `test_ejemplo_casos_de_uso.py` y los mutantes M5 a M8 de
  QA-2 (PR #1) y anotar cuáles sobreviven hoy. **Rojo**: sacar de `_EXCEPCIONES_SQL`
  (`tests/unitarios/test_fronteras_de_modulos.py:506-511`) las tres de `ejemplo.py` y sumar el
  escenario "El ejemplo vuelve a escribir una tabla de acceso"; el test falla nombrando `ejemplo.py` y
  `administracion`, `persona`, `asignacion_rol`.
- [ ] 6.2 **Verde**: extraer a `acceso.aplicacion` la creación de administración, persona `super_admin`
  y asignación con ids opcionales, usada por `alta_inicial.crear` y por `ejemplo.cargar` (L-009, D7).
  En verde: fronteras, los 10 del ejemplo (incluido "Dos cargas a la vez"), los de alta inicial
  ("Primera administración", "Datos inválidos"), y M5 a M8 no sobreviven más que en 6.1. Escenario "El
  código de hoy pasa con sus excepciones".

## 7. Los cuatro ítems de acceso (B-3, 2.3, 2.4, 2.5/P66)

- [ ] 7.1 Migración `00NN` (número provisorio; el que mergea segundo renumera): suma `ver_personal` a
  `accion_de_auditoria` (mismo patrón que `0027_editar_edificio.py`). **Rojo**:
  `test_auditoria_tabla.py::test_accion_de_auditoria_coincide_con_accion` y
  `test_vocabulario_configuracion.py` con `Accion.VER_PERSONAL` ya declarada (vacía en la matriz) fallan
  nombrando `ver_personal`. **Verde**: la migración. **Bajada** probada sobre una copia con datos: quita
  la fila y falla sin modificar nada si alguna fila de `auditoria` la usara; subida y bajada con
  `alembic heads` de una sola cabeza. DBA convocado (E11, D13).
- [ ] 7.2 La matriz en `tests/unitarios/acceso/test_permisos.py`. **Rojo**: `_MATRIZ_A_MANO` suma
  `ver_personal` con `_SA` y `_AP`; "El administrador principal ve el personal pero no invita";
  `puede(..., VER_PERSONAL, None)` es verdadero para super admin y administrador principal y falso para
  las otras siete columnas. **Guardas**: "La matriz completa" en las 153 celdas de hoy; sin complejo,
  ninguna otra acción salvo las tres de toda la administración. **Verde**: `_MATRIZ` y el conjunto de
  acciones sin complejo de `puede` (D13). **Mutantes**: (a) `ver_personal` con `_AE` → rojo; (b)
  `ver_personal` fuera del conjunto sin complejo → rojo.
- [ ] 7.3 `GET /api/personal` jerárquico en `tests/integracion/test_personal_api.py`. **Rojo**: con A
  que tiene super admin, otro administrador principal, contador por edificio, auxiliar y vecino, un
  administrador principal recibe 200 sólo con el contador y el auxiliar, y el **cuerpo crudo** no
  contiene el id, el nombre ni el email del super admin, del otro principal ni del vecino; un
  administrador por edificio recibe 403 con `codigo: "sin_permiso"` y `permiso_faltante: "ver_personal"`.
  **Guardas**: el super admin recibe la lista de hoy; el administrador principal recibe 403 con
  `invitar_usuarios_y_asignar_edificios` al invitar, revocar y quitar, sin escribir. Escenarios "El
  administrador principal lista el personal", "El administrador principal no gestiona", "Un
  administrador por edificio pide el personal". **Verde**: `GET` exige `ver_personal`;
  `listar_personal` filtra con las asignaciones de quien pide, en la API (D13). **Mutantes**: (a)
  filtrar por asignación en vez de por persona (mostrar sólo las asignaciones de abajo) → rojo en el
  email del super admin con una asignación extra de consejo; (b) incluir al otro principal → rojo; (c)
  el `GET` sigue exigiendo `invitar_…` → rojo.
- [ ] 7.4 `acciones_permitidas` en `tests/unitarios/acceso/test_permisos.py`. **Rojo**: test de
  propiedad que, para las nueve columnas, cada acción de `Accion` y un edificio propio y otro ajeno (y
  sin complejo para las tres de toda la administración), compara `acciones_permitidas` contra `puede`;
  casos de forma "El super admin" y "Un contador por edificio". Escenario "Las acciones coinciden con
  los 403". **Verde**: la función pura en `acceso/dominio/permisos.py`, calculada con `_MATRIZ` (D11,
  L-009). **Mutantes**: (a) una copia a mano de la matriz dentro de la función, con una celda distinta →
  rojo; (b) las asignaciones por unidad ignoradas → rojo en el vecino.
- [ ] 7.5 `GET /api/sesion` ampliada en `tests/integracion/test_sesion_api.py`. **Rojo**: cada
  administración trae `acciones` con `administracion`, `todos_los_edificios` y `por_edificio`, por HTTP
  con un token firmado, para super admin, administrador por edificio y contador por edificio.
  **Guarda**: el 403 `sin_acceso` sigue siendo exactamente `{"detail": {"codigo": "sin_acceso"}}`
  (compararlo byte a byte contra el de 2.1). Escenarios "El super admin", "Un contador por edificio",
  "El 403 sin acceso no cambia". **Verde** en `consultar` (D11). **Mutante**: `acciones` agregadas
  también al 403 → rojo en la guarda.
- [ ] 7.6 La web oculta lo que no se puede: `componentes/SesionDePantalla.tsx` (acciones y `permite`),
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
  `todos_los_edificios` → rojo en el administrador por edificio; (c) "Personal" atado a `invitar_…` en
  vez de `ver_personal` → rojo en el administrador principal.
- [ ] 7.7 2.4 en `tests/integracion/test_invitar_personal_api.py`. **Rojo**: invitar
  `x@ejemplo.invalid` como "Ana", revocar, reinvitar como "Ana María" con otro perfil → `/api/personal`
  muestra una sola persona "Ana María" con las dos asignaciones; lo mismo con la persona ya vinculada y
  por el alta de vecinos. **Guardas**: reinvitar con un perfil repetido → 409 `campo=rol` y el nombre
  sigue siendo el anterior; "Reinvitar revoca la anterior" sin cambios. Escenarios "Reinvitar el mismo
  email con otro nombre", "El nombre no cambia si la invitación se rechaza". **Verde**: `ON CONFLICT …
  DO UPDATE SET nombre` dentro del `begin_nested()` de `_alta` (D12). **Mutante**: actualizar el nombre
  en una sentencia aparte, fuera del savepoint → rojo en la guarda del 409.
- [ ] 7.8 B-3 en `web/src/app/invitacion/[sobre]/page.test.tsx` y `Pantalla.test.tsx`. **Rojo**: con
  sesión y claim de email, la pantalla dice "Estás ingresado como <email>" y ofrece "Usar otra cuenta"
  (el enlace con `cerrar=1`, `regreso` a la invitación y el mismo `__clerk_ticket`); si la acción
  devuelve error con sesión, el mensaje dice que el enlace no sirve con esa cuenta y repite "Usar otra
  cuenta"; sin claim de email, el texto no nombra ninguno (ni vacío ni "undefined"); un parámetro de
  query con un email no aparece en la pantalla. **Guardas**: sin sesión, la pantalla es la de hoy;
  `test_aceptar_invitacion_api.py` "Otro email" sigue dando el 404 `{"detail":"no encontrado"}` sin
  cambios. Escenarios "Abrir la invitación con la sesión de otra cuenta", "Usar otra cuenta", "Token sin
  email", "Aceptar con la cuenta equivocada", "El email no sale de la URL". **Verde**: `page.tsx` lee
  el claim de `auth().sessionClaims` y lo pasa a `PantallaInvitacion` (D10). Anotar en el informe si el
  claim de email viaja en el token de sesión del Clerk de desarrollo (SUPUESTO de D10), comprobándolo
  sin pegar ningún email real. **Mutantes**: (a) leer el email de `searchParams` → rojo; (b) mostrar el
  texto de error de hoy con sesión → rojo.

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
  invitación de A abierta con la cuenta de B; (f) el menú y los controles con un contador, un
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
