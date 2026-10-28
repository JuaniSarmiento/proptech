> **Firma primero.** Ninguna tarea arranca hasta que la sección "Aprobación" de `proposal.md` esté
> firmada por Juani, Alberto o Emiliano, con nombre, fecha y la respuesta a E1 a E9 (D-094, D-111).
> Una regla nueva que entre después de la firma necesita firma propia (L-029). El apply es CRITICAL:
> no se despacha a un `role-implementer` suelto (L-048).
>
> **TDD estricto con el rojo pegado** (L-034, L-049): cada tarea pega el comando, la salida del rojo y
> la hora, y el rojo cae en la aserción que el test dice probar (código de estado, cuerpo, URL final),
> nunca en un `ImportError`, en un 401 de la guarda ni en un helper. Para eso, la excepción, la opción o
> la ruta nueva existen vacías antes del primer rojo. Cada garantía nueva tiene un **mutante dirigido**
> corrido sobre una copia sin commit y declarado en el informe (L-013, L-035). Backend:
> `bash infra/ci/test-backend.sh <archivos>`. Web: `bash infra/ci/test-web.sh`.
>
> **Si E7 se rechaza**: el grupo 6 y `specs/fronteras-de-modulos/` se borran antes de construir, y la
> tarea 5.2 escribe la vinculación en una función de `acceso.aplicacion` sin tocar el resto de
> `ejemplo.py`. **Si E6 se aprueba con la alternativa**: se agrega una tarea de migración del
> vocabulario de auditoría (número provisorio `00NN`, el que mergea segundo renumera) antes de la 5.2, y
> se convoca al DBA.
>
> **Tamaño**: 19 tareas, cerca del tope de ~20 de `config.yaml`. Si hay que partirlo, el corte natural
> es **2d-1** = grupos 1 a 3 y 7 (el contrato y la web: lo que corta el 431) y **2d-2** = grupos 4 a 6
> (recuadro de Clerk, vínculo del ejemplo, D-021).

## 1. Preparación

- [ ] 1.1 Rebasar sobre `main` y fijar el baseline antes de tocar nada: `alembic heads` con una sola
  cabeza (`0027` o la que haya mergeado el 3d o el 6), y en verde
  `bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_deuda_acceso_2b.py tests/integracion/test_ejemplo_casos_de_uso.py tests/unitarios/test_fronteras_de_modulos.py tests/unitarios/acceso`
  y `bash infra/ci/test-web.sh`. Pegar conteos y SHA. Listar con `rg` los tests que hoy afirman 401
  para "token válido sin vínculo" y "vinculada sin asignación": son los que la tarea 2 cambia primero.

## 2. API: el 403 `sin_acceso`

- [ ] 2.1 **Rojo** en `tests/integracion/test_sesion_api.py`, por HTTP con tokens firmados de verdad
  (L-017): token válido sin persona → 403 con cuerpo exacto `{"detail": {"codigo": "sin_acceso"}}`;
  persona vinculada sin asignaciones → mismo cuerpo byte a byte; vinculada sin asignación en A y con
  asignación en B → 200 con B y sin A; sin token, otra clave, vencido, otra aplicación → 401 y cero
  SQL. Escenarios "Token válido sin vínculo", "Vinculada sin asignación", "Token inválido sigue siendo
  401", "Acceso en otra administración no es sin acceso", "Cero administraciones" (contrato). **Verde**:
  `SinAcceso` en `acceso/aplicacion/identidad.py`, `consultar` la lanza con lista vacía, traductor a 403
  en `proptech_api` (design D1). **Mutantes**: (a) `consultar` devuelve `[]` otra vez → rojo; (b) el
  traductor agrega `"motivo": "sin_persona"` sólo en un caso → rojo en la comparación byte a byte;
  (c) `token_de_sesion_actual` responde 403 → rojo en "Token inválido sigue siendo 401".
- [ ] 2.2 **Rojo** en `tests/integracion/test_identidad_clerk_api.py` sobre una ruta de dominio
  (`GET /api/complejos`): sin persona → 403 `sin_acceso`, línea `ingreso_sin_vinculo` sin email ni sub
  en claro y ninguna fila de auditoría; persona sin asignación y sin otra administración → 403 y una
  fila `ingreso_fallido`; administración ajena, varias sin elegir y selector no UUID → 401 como hoy, y
  ningún SQL del caso de uso de complejos antes del 403. Escenarios "Persona sin asignación", "Identidad
  sin vínculo", "Elegir una administración ajena", "Varias sin elegir", "Selector con texto que no es
  UUID". **Verde**: `resolver` lanza `SinAcceso` sólo cuando ninguna persona del `sub` tiene
  asignaciones, después de la búsqueda de hoy (design D1, "Orden de las comprobaciones").
  **Mutantes**: (a) `SinAcceso` también para administración ajena → rojo; (b) se saca el
  `ingreso_fallido` del camino nuevo → rojo; (c) se pregunta "¿tiene alguna asignación?" antes del
  selector → rojo en el conteo de filas de auditoría.
- [ ] 2.3 **Rojo** de anti-enumeración en `tests/integracion/test_deuda_acceso_2b.py` (o un archivo
  nuevo de la misma carpeta): A tiene una persona sin vincular con `x@ejemplo.invalid` y una invitación
  enviada a ese email; un token válido sin vínculo con ese email y otro con un email distinto reciben
  respuestas idénticas (código, cuerpo, cabeceras propias), sin el nombre ni el id de A; ninguna
  sentencia del camino lee `persona` o `invitacion` por `email` (contando sentencias con el
  instrumentador que ya usan los tests de cero SQL). Escenario "El 403 no depende del email".
  **Mutante**: un `SELECT … WHERE email = :email` en `resolver` que cambia el cuerpo si encuentra una
  fila → rojo.

## 3. Web: cliente, `regreso`, selector y pantalla nueva

- [ ] 3.1 **Rojo** en `web/src/lib/api/cliente.test.ts`: 403 con `{"detail":{"codigo":"sin_acceso"}}`
  → `redirect("/sin-acceso")` sin `regreso`; 403 con `permiso_faltante` → `sin_permiso` como hoy; 403
  sin cuerpo → `sin_permiso` "desconocido"; con `alNoAutenticar: "devolver"` un 401 da
  `{ estado: "sin_sesion" }` sin `redirect`, y sin la opción redirige como hoy (design D2). Actualizar
  `lib/test/cinco-respuestas.test.ts` para que documente el estado nuevo. **Verde** en `cliente.ts`.
  **Mutantes**: (a) todo 403 se trata como `sin_acceso` → rojo; (b) `"devolver"` ignorado → rojo.
- [ ] 3.2 **Rojo** en `web/src/lib/sesion.test.ts` con los seis escenarios de "El regreso nunca
  apunta a una pantalla de acceso" (anidado, ingreso, disfrazado con `/./`, `/../` y barra final, 513
  caracteres, invitación conservada, idempotencia sobre una lista de entradas que incluye las de hoy).
  **Verde** en `regresoSeguro` (design D3). **Mutantes**: (a) sacar `/elegir-administracion` de la lista
  → rojo; (b) comparar contra el texto crudo en vez del `pathname` normalizado → rojo en "disfrazado";
  (c) sacar el tope → rojo en 513.
- [ ] 3.3 Crear `web/src/app/elegir-administracion/page.test.tsx` y `Pantalla.test.tsx` (hoy no
  existe ninguno). **Rojo**: con `/api/sesion` en 401 la página muestra "No pudimos validar tu sesión"
  con "Cerrar sesión" (`/ingresar?cerrar=1`) y no llama a `redirect` a `/ingresar`; con 403
  `sin_acceso` redirige a `/sin-acceso`; con lista vacía (defensivo) redirige a `/sin-acceso` y la
  pantalla no tiene más rama vacía; con una y con dos administraciones, como hoy. Escenarios "La API
  rechaza un token que Clerk da por bueno", "Cero administraciones". **Verde** (design D2, D4).
  **Mutante**: volver a `pedirApi` sin `"devolver"` en la página → rojo.
- [ ] 3.4 **Rojo** en `web/src/app/sin-acceso/Pantalla.test.tsx` y `page.test.tsx`: título "Tu cuenta
  no tiene acceso todavía", email principal de `useUser()` visible, sin email cuando Clerk no lo
  informa (ni vacío ni "undefined"), "Cerrar sesión" a `/ingresar?cerrar=1`, "Volver a intentar" a
  `/elegir-administracion`, ningún `redirect` con sesión, `redirect("/ingresar")` sin sesión, `axe` sin
  violaciones. Escenarios "Clerk sin email principal", "Sin sesión de Clerk", "Cerrar sesión desde la
  pantalla sin acceso". **Verde**: la ruta nueva (design D4). **Mutante**: renderizar el email desde
  una prop del servidor en vez de `useUser()` → rojo en el test que verifica que el HTML del servidor no
  trae el email.
- [ ] 3.5 Recorrido con teclado de `/sin-acceso` y del selector con error, en el test de componente:
  Tab llega a cada acción con foco visible y Enter las activa. Escenario "Recorrer la pantalla con
  teclado". **Mutante**: `tabIndex={-1}` en "Volver a intentar" → rojo.
- [ ] 3.6 Rebasar sobre la parte del 3d en `web/e2e/api-falsa.ts`. Sumar `user_sin_persona` (403
  `sin_acceso` en `/api/sesion` y en dominio) y `user_api_rechaza` (401 en todo con token válido),
  copiando el contrato de las tareas 2.1 y 2.2 (L-027). **Rojo** en `web/e2e/sesion.spec.ts`:
  `user_sin_persona` abre `/edificios` y termina en `/sin-acceso` en a lo sumo tres navegaciones, sin
  ninguna respuesta 431 y sin `regreso` anidado en ninguna URL de la cadena; `user_api_rechaza` abre
  `/elegir-administracion` y se queda ahí con "No pudimos validar tu sesión", cero redirecciones a
  `/ingresar`; dos pestañas a la vez con `user_sin_persona` terminan las dos en `/sin-acceso`; a 320 px
  `/sin-acceso` sin desplazamiento horizontal y con `axe` limpio. Escenarios "Cuenta de Clerk sin
  persona abre una pantalla de dominio", "Dos pestañas a la vez", "La API rechaza un token que Clerk da
  por bueno", "Pantalla angosta". **Mutante combinado** (L-034, capas por separado): revertir sólo D2 →
  el test de `user_api_rechaza` da rojo y el de `user_sin_persona` sigue verde; revertir D2 y D3 juntas →
  aparece el anidamiento.

## 4. Recuadro de Clerk en `/ingresar`

- [ ] 4.1 **Reproducir** con el Clerk de desarrollo real a 320 px y 1280 px: captura, ancho de
  contenido de `.panel`, ancho de `.cl-cardBox`, `scrollWidth` contra `clientWidth`. Pegar los números
  y confirmar o descartar la hipótesis (design D8). Si no se reproduce, se cierra acá con la evidencia y
  la 4.2 se marca como no necesaria con el motivo.
- [ ] 4.2 Si 4.1 lo reprodujo: **rojo** en e2e sobre el contenedor (sin el widget, L-032): a 320 px
  `/ingresar` sin desplazamiento horizontal y ancho de contenido del panel al menos el mínimo medido en
  4.1. **Verde** con el ajuste de `tokens.css` (`.pagina-acceso`, `.clerk-proptech`, `cardBox` en la
  `apariencia`). Volver a medir con Clerk real a 320 px y 1280 px, con captura, y recorrer con teclado.
  **Mutante**: restaurar el relleno lateral del panel → rojo.

## 5. El ejemplo vincula una cuenta de desarrollo

- [ ] 5.1 **Rojo** en `tests/integracion/test_ejemplo_casos_de_uso.py` (y su parte unitaria de
  `_main`): los escenarios "Id con otra forma" (antes de conectarse: se verifica con la misma técnica
  de `test_la_guarda_corre_antes_de_conectar_a_la_base`), "La opción no saltea la guarda", "Vincular al
  cargar por primera vez", "Vincular un ejemplo ya cargado" (conteos iguales), "Vincular dos veces el
  mismo id", "Ya vinculado a otra cuenta" (vínculo intacto, nada escrito) y ningún mensaje repite el id
  (L-007, L-008). **Mutantes**: (a) `re.match` en vez de `fullmatch` → rojo en el salto de línea; (b)
  pisar si es distinto → rojo; (c) validar después de crear el engine → rojo; (d) vincular fuera de la
  transacción de la carga → rojo en el escenario de otra cuenta sobre base vacía.
- [ ] 5.2 **Verde**: `--clerk-usuario` en `_main` y `cargar(..., clerk_usuario=...)`, con la
  vinculación como función de `acceso.aplicacion` (design D5, D7). Más un test de punta a punta:
  después de vincular, `GET /api/sesion` con un token firmado para ese `sub` da 200 con la
  administración de ejemplo sola. Escenario "Entrar con la cuenta vinculada".
- [ ] 5.3 Escribir en `README.md` (§"Cómo levantarlo") "Entrar con el edificio de ejemplo", paso a
  paso, con `user_XXXXXXXX` como marcador y sin ningún id ni email real (L-040). **Verificación**: una
  persona distinta de quien lo escribió (Emiliano o Gianfranco) lo sigue tal cual sobre una base limpia
  con su propia cuenta y llega a "Mis edificios"; el informe dice quién, cuándo, con qué SHA, y dónde
  quedó el id usado (el panel de Clerk), nunca su valor. Escenario "Otra persona repite el recorrido".
  Salda L-039 y la deuda del PR #1.

## 6. `ejemplo.py` sin SQL de `acceso` (sólo si E7 se aprueba)

- [ ] 6.1 Baseline: correr los 10 tests de `test_ejemplo_casos_de_uso.py` y los mutantes M5 a M8 de
  QA-2 (PR #1) y anotar cuáles sobreviven hoy. **Rojo**: sacar de `_EXCEPCIONES_SQL`
  (`tests/unitarios/test_fronteras_de_modulos.py:506-511`) las tres de `ejemplo.py` y sumar el
  escenario "El ejemplo vuelve a escribir una tabla de acceso"; el test falla nombrando `ejemplo.py` y
  `administracion`, `persona`, `asignacion_rol`.
- [ ] 6.2 **Verde**: extraer a `acceso.aplicacion` la creación de administración, persona `super_admin`
  y asignación con ids opcionales, usada por `alta_inicial.crear` y por `ejemplo.cargar` (L-009,
  design D7). En verde: fronteras, los 10 del ejemplo (incluido "Dos cargas a la vez"), los de alta
  inicial (`gestion-de-usuarios`, "Primera administración", "Datos inválidos"), y M5 a M8 no
  sobreviven más que en 6.1. Escenario "El código de hoy pasa con sus excepciones".

## 7. Cierre

- [ ] 7.1 Corrida de cierre después de la última vuelta, con el SHA anotado: suite de backend completa,
  `bash infra/ci/test-web.sh`, e2e, `ruff`, `mypy`, `biome`; y el CI **del PR** en verde (L-010, L-031,
  L-037, L-042). Un rojo local del navegador se juzga contra el job `web` del CI (L-050).
- [ ] 7.2 Verificación manual contra el Clerk de desarrollo real, escrita paso a paso (L-039, L-026):
  (a) una cuenta sin persona entra por `/ingresar` y termina en `/sin-acceso` con su email, cierra
  sesión y ve el formulario; (b) la misma cuenta, vinculada con `--clerk-usuario`, elige "Volver a
  intentar" y entra a "Mis edificios"; (c) dos pestañas a la vez con la cuenta sin persona; (d)
  `/ingresar` y `/sin-acceso` a 320 px y 1280 px y con teclado. Capturas en el informe, ningún id real
  en el repo. Escenarios "Cuenta de Clerk sin persona entra por el ingreso" y "Volver a intentar
  después de que la vinculan".

## Workflow follow-up

- Revisores de `verify`: piso obligatorio por autenticación, **backend**, **QA** y **arquitecto**;
  **frontend** por la pantalla nueva y el CSS; **DBA** sólo si E6 se aprobó con migración.
- Archivar con el `## Knowledge Base Impact` de `proposal.md`: D-nueva-1 a D-nueva-3 con su número
  real, y la ficha nueva de lo que E8 deje afuera.
