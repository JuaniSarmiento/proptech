# Rompedor · verify · intento 1 · pulido-2 (3d)

- **Rol**: rompedor (subagente nativo de Claude, role-breaker). Intento 1.
- **Revisión revisada**: `b1ec660` (rama local `revision-3d`), diff `e29e36d...b1ec660` (27 archivos, 12 commits).
- **Worktree**: copia aislada; sin commit, sin push, sin tocar producción. Cada mutante se aplicó y se revirtió desde una copia (`git status` final: sólo `tasks.md` del orquestador y los dos archivos de tests nuevos del rompedor).
- **Fecha**: 30/10/2026, 12:06 a 12:12 (-03:00).

## Fuentes leídas

- Plan: `openspec/changes/pulido-2/proposal.md`, `design.md`, `tasks.md`, `specs/edificios-y-unidades/spec.md`, `specs/pantallas-del-edificio/spec.md`.
- Lecciones: `knowledge-base/15_lecciones.md`, secciones L-026, L-027, L-035, L-049, L-050, L-051, L-052 (las pedidas en el brief). No leí el resto del archivo.
- Código del diff: `web/e2e/api-falsa.ts` (contrato, auth, ramas nuevas), `web/e2e/api-falsa.patch-georef.test.ts`, `web/src/lib/pisos.ts` y su test, `web/src/app/page.tsx` y su test, `web/src/proxy.ts` y `proxy.test.ts`, `ayuda.ts` y su test, los cuatro `Pantalla.axe-estados.test.tsx`, `configuracion/Pantalla.dia-fuera-de-rango.test.tsx`, `unidades/Pantalla.rompedor.test.tsx`, el cambio de `unidades/Pantalla.test.tsx`, `e2e/comprobaciones.spec.ts`, `e2e/csp.spec.ts`, `backend/tests/integracion/test_clave_explicita_invalida.py`, `test_rompedor_clave_patch_grupo.py`, el cambio de `test_configuracion_api.py`.
- Consumidores fuera del diff: `backend/src/proptech_api/complejos.py` (modelos `CuerpoDeEdicion`, `CuerpoEdicionEdificio`, `CuerpoEdicionGrupo`, rutas), `cuerpos.py` (`CuerpoDeAlta` strict/forbid, `manejador_422`), `georef.py`, `config/georef/*.json`, `backend/src/proptech_core/complejos/aplicacion/lectura.py` (cálculo de `pasos`), `backend/tests/integracion/test_resumen_puesta_a_punto.py`, `web/src/lib/sesion.ts`, `web/src/app/ingresar/[[...]]/page.tsx` y `Pantalla.tsx`, `web/src/app/edificios/page.tsx`, `unidades/Pantalla.tsx` y `page.tsx`, `web/src/lib/api/{edificios,grupos,georef}.ts`, `web/src/componentes/Formulario.tsx`, `BarraDeProgreso.tsx`, `e2e/barrido-completo.spec.ts`, `infra/ci/humo.sh` (chequeo de `GET /`), `.github/workflows/ci.yml`, `infra/ci/test-backend.sh`, `test-web.sh`.

## Contaminación

- Leí el resumen de la 10.1 y la marca de la 10.2 en `tasks.md` (el número 72/454 del constructor y la nota de que la 10.2 fue rompe-y-audita en un agente). No me apoyé en ninguna de sus conclusiones; no hay informes de la 10.2 en la rama. No leí informes de otros roles.
- El veredicto del CI lo reutilicé (no repetí la suite completa), verificado por mí: ver EVIDENCIA E0.

## Entorno y lo que no se ejecutó

- `web/node_modules` y `backend/.venv` symlinkeados desde el clon principal (el de `.venv` lo borré al terminar).
- PostgreSQL del compose **no** estaba levantado: no corrí tests de integración del backend. Para el contrato real usé una sonda con los **modelos reales** de la API (FastAPI `TestClient`, sin base), y para la integración reutilicé el job `backend` del CI.
- Playwright **no** corrido (L-050: el juez es el job `web` del CI).
- Sin navegador real: no miré la raíz `/` ni los estados de axe con Clerk (8.2 y 9.2 siguen sin mirada humana).

## EVIDENCIA

### E0 · CI reutilizado (verificado, no heredado)

```
$ gh run view 40790724706 --json headSha,conclusion,jobs
{"conclusion":"success","headSha":"b1ec6607c3836d59299126a8886910895994e729",
 "jobs":[shellcheck success, secretos success, humo success, web success, backend success]}
$ gh run view 40790724706 --log | rg ...
web      Test Files 84 passed (84) / Tests 585 passed (585)     (vitest; el canario rojo después es intencional)
web      175 passed (4.5m)                                       (Playwright)
backend  tests/integracion/test_clave_explicita_invalida.py ................ (16)
backend  tests/integracion/test_rompedor_clave_patch_grupo.py ......        (6)
backend  4279 passed, 1 xfailed, 19 warnings in 1040.40s
```

Nota para el auditor: el CI cuenta **84 archivos / 585 tests** de vitest sobre `b1ec660`; la 10.1 dice 72 / 454. No investigué la diferencia (probablemente el entorno Windows del constructor); no es un fallo del código.

### E1 · Tests enfocados corridos por mí (verde)

```
$ (web) npx vitest run e2e/api-falsa.patch-georef.test.ts src/lib/pisos.test.ts src/app/page.test.tsx \
   src/proxy.test.ts src/app/edificios/[id]/ayuda.test.ts .../categorias/Pantalla.axe-estados.test.tsx \
   .../configuracion/Pantalla.axe-estados.test.tsx .../configuracion/Pantalla.dia-fuera-de-rango.test.tsx \
   .../grupos/Pantalla.axe-estados.test.tsx .../saldos-previos/Pantalla.axe-estados.test.tsx \
   .../unidades/Pantalla.rompedor.test.tsx .../unidades/Pantalla.test.tsx
2026-10-30T12:06:08-03:00 · b1ec660
 Test Files  12 passed (12)
      Tests  77 passed (77)
```

### E2 · Sonda del contrato real (modelos reales de `proptech_api.complejos`, `manejador_422` real, sin base)

Script: app FastAPI mínima con `PATCH /api/grupos/{grupo_id: UUID}` (`CuerpoEdicionGrupo`) y `PATCH /api/complejos/{complejo_id: UUID}` (`CuerpoEdicionEdificio`), `TestClient`, `PYTHONPATH=src`. 2026-10-30T12:06:51-03:00, `b1ec660`.

```
grupo sin cuerpo      -> 422 [{"type":"missing","loc":["body"]}]
grupo {}              -> 200
grupo activo "no"     -> 422 bool_type (body.activo)
grupo activo null     -> 422 value_error (body.activo)
grupo metodo "raro"   -> 422 literal_error (body.metodo)
grupo clave mala      -> 422 value_error (body.clave)
grupo id no uuid      -> 422 uuid_parsing (path.grupo_id)
edificio pisos 0      -> 422 greater_than_equal (body.pisos)
edificio subsuelos 6  -> 422 less_than_equal (body.subsuelos)
edificio nombre ""    -> 422 string_too_short (body.nombre)
edificio sin cuerpo   -> 422 [{"type":"missing","loc":["body"]}]
edificio text/plain   -> 422 model_attributes_type (body)
edificio pisos 6.0    -> 422 int_type (body.pisos)
```

### E3 · Mutantes (aplicados con un reemplazo de texto, cada uno revertido desde copia)

| id | archivo | mutación | tests corridos | resultado |
|---|---|---|---|---|
| M1 | `proxy.ts` | el filtro deja `'unsafe-eval'` | `proxy.test.ts` (5) | **muerto** (`expected 'script-src 'self' 'unsafe-eval' …' not to contain 'unsafe-eval'`) |
| M2 | `proxy.ts` | sin filtro | `proxy.test.ts` | **muerto** |
| M3 | `proxy.ts` | filtra sólo `content-security-policy` | `proxy.test.ts` | **muerto** |
| A1 | `api-falsa.ts` | `if (metodo === "PATCH" && resto === "")` pasa a `if (false)` | `api-falsa.patch-georef.test.ts` + `api-falsa.test.ts` (53) | **SOBREVIVE** (53 passed) · ver F5 |
| A2 | `api-falsa.ts` | grupos sin `_erroresDeContrato` | ídem | muerto (2 fallan) |
| A3 | `api-falsa.ts` | departamentos sin filtrar por provincia | ídem | muerto (2) |
| A4 | `api-falsa.ts` | `pisos` texto | ídem | muerto (2) |
| A5 | `api-falsa.ts` | `subsuelos` texto | ídem | muerto (1) |
| A6 | `api-falsa.ts` | `metodo` de grupo booleano | ídem | muerto (1) |
| A7 | `api-falsa.ts` | `clave` de grupo obligatoria | ídem | muerto (4) |
| X1 | `componentes/Formulario.tsx` | campo con error apunta `aria-describedby` a un id inexistente y `role=presentation` | los 3 `axe-estados` con formulario (9) | muerto (los 3 "panel con un error de campo" fallan) |
| P1 | `lib/pisos.ts` | subsuelos ascendentes | `pisos.test.ts` + 2 de unidades (32) | muerto (2) |
| G1 | `app/page.tsx` | siempre a `/ingresar` | `page.test.tsx` (3) | muerto (1) |
| G2 | `app/page.tsx` | con sesión a `/elegir-administracion` | `page.test.tsx` | muerto (1) |

Primera corrida de mutantes: 2026-10-30T12:08:31-03:00; A1: 12:08:50; X1: 12:10:29.

### E4 · CSP real que emite el middleware (sonda temporal, ya borrada)

Con y sin sesión, `GET /` por `proxy()`: `script-src 'self' … 'strict-dynamic' 'nonce-…' https://clerk.proptech-prueba.invalid https://challenges.cloudflare.com`, igual en `content-security-policy` y `x-middleware-request-content-security-policy`; `x-nonce` presente; status 200 sin `location` (el middleware no redirige `/`, lo hace la página). Los mutantes M1/M2 muestran que Clerk sí emite `'unsafe-inline'` y `'unsafe-eval'` antes del filtro, así que el test vigila algo real.

### E5 · Tests que dejo fallando (sin commit)

`web/e2e/api-falsa.rompedor-3d.test.ts` y `web/src/app/edificios/[id]/ayuda.rompedor-3d.test.tsx`.

```
$ (web) npx vitest run e2e/api-falsa.rompedor-3d.test.ts
2026-10-30T12:09:50-03:00 · b1ec660
   × /api/complejos/f760ca3b-… sin cuerpo da 422       AssertionError: expected 200 to be 422
   × /api/grupos/1c9d6f7e-… sin cuerpo da 422          AssertionError: expected 200 to be 422
   × PATCH /api/grupos/no-es-uuid da 422               AssertionError: expected 200 to be 422
   × cada departamento y localidad simulados tienen el nombre real de su id
       + "50028: Godoy Cruz != Guaymallén"
       + "50028010: Godoy Cruz != Colonia Segovia"
       + "06028: Adolfo Alsina != Almirante Brown"
       + "06028010: Carhué != Almirante Brown"
      Tests  4 failed (4)

$ (web) npx vitest run "src/app/edificios/[id]/ayuda.rompedor-3d.test.tsx"
2026-10-30T12:11:31-03:00 · b1ec660
   × RB3D-4: el arranque que cuenta la ayuda coincide con la barra de un edificio recién creado
AssertionError: expected '0 de 7 pasos' to be '4 de 7 pasos'
      Tests  1 failed (1)
```

## Lente 1 · Correctitud

**Hecho**: bordes de cada punto. Pisos: 0/0, 4/0, 4/1, 4/2 cubiertos por los tests; leí el loop nuevo para negativos (devuelve `["PB", …]`, igual que antes) y máximos (60/5, sin problema). API falsa: cuerpo vacío, `{}`, `null`, tipos mal, campo extra, id que no es UUID, métodos no declarados, sin sesión, Georef con padre inexistente y POST, comparado contra la sonda E2. CSP: mutantes M1 a M3 y la política real E4. Día: leí el test de pantalla (29, 31 y segundo vencimiento 31) y el parametrizado del backend (30, 31, segundo 0, 29, 31), que corre en el CI (E0). Clave inválida: leí los dos archivos de integración (corren verdes en el CI).

**Resultado**:

- **F1 (reproducida, BAJA) · `PATCH` sin cuerpo: la falsa da 200, la real 422.** `parseado = cuerpo === "" ? {} : …` (heredado de los POST, donde no importaba porque faltaban campos obligatorios) hace que las dos rutas nuevas, con todos los campos opcionales, acepten un `PATCH` sin cuerpo. La real responde `422 missing loc ["body"]` (E2). Test: RB3D-1 (E5).
- **F2 (reproducida, BAJA) · `PATCH /api/grupos/{id}` con un id que no es UUID: la falsa da 200, la real 422 `uuid_parsing`** (E2). La web filtra con `esIdValido` antes de pedir, así que hoy no lo alcanza la pantalla, pero la falsa sigue sin rechazar lo que la real rechaza. Test: RB3D-2 (E5).
- **Divergencia declarada, no la cuento como falla**: la falsa sólo valida **tipos** (por diseño: "tipos y opcionales", comentario de `_tipoPydantic`), así que acepta `pisos: 0`, `subsuelos: 6`, `nombre: ""`, `metodo: "raro"` y `clave: "Mala Clave"`, que la real rechaza con 422 (E2). Choca con la frase del design ("una API falsa que rechaza lo que la real rechazaría", Goals), pero es el mismo criterio que ya tienen los POST. Decisión del orquestador/auditor, no del rompedor.
- Pisos, raíz, CSP, axe, día y clave: limpio en lo que probé (E1, E3).

## Lente 2 · Cableado

**Hecho**: busqué todos los usos de `vocabularioDePisos` (`rg`: sólo `unidades/Pantalla.tsx:389`, con la opción vacía explícita antes, L-052; nada depende del orden viejo fuera del test corregido). Comparé la falsa con los routers reales (`complejos.py:342` `modificar_edificio`, `:506` `modificar_grupo`, `georef.py`), con `config/georef/` y con lo que manda la web (`lib/api/edificios.ts`, `grupos.ts`, `georef.ts`). Seguí la raíz `/`: `page.tsx` → `sesionActual()` → `/edificios` o `/ingresar`; `/ingresar` sin `regreso` usa `/edificios`; `regreso=/` no está entre las pantallas de acceso de `regresoSeguro`, así que `/ingresar` → `/elegir-administracion?regreso=/` → `/` → `/edificios`: un salto de más, sin loop. Ningún enlace de la web apunta a `/` (`rg` sin resultados). `humo.sh` sigue haciendo `curl -fsS http://localhost/` y ahora recibe la redirección (Caddy pone las cabeceras igual; el job `humo` está verde, E0). El estado "error de la API" de las siete pantallas lo mide con axe el barrido de Playwright (`barrido-completo.spec.ts`, escenario `error_500`), que corre en el CI.

**Resultado**:

- **F3 (reproducida, BAJA) · Georef simulado con nombres que no son los reales.** Los ids existen en `config/georef/`, pero 4 de 8 nombres no: `50028` es Guaymallén (la falsa dice Godoy Cruz), `50028010` es Colonia Segovia, `06028` y `06028010` son Almirante Brown (la falsa dice Adolfo Alsina y Carhué). Un e2e futuro que busque "Godoy Cruz" pasaría contra la falsa y fallaría contra la real. Test: RB3D-3 (E5).
- **Sin consumidor de navegador**: las rutas nuevas de la falsa (`PATCH` de edificio y de grupo, Georef) no las usa ningún spec de Playwright (`rg "georef|PATCH|/grupos/" e2e/*.spec.ts` vacío); sólo las ejercita su test unitario. Está declarado (2.5 sin hacer), pero el objetivo del ítem 1 del proposal ("con sus e2e de Playwright") sigue abierto.
- **No cubierto por la falsa (fuera del alcance escrito)**: `PATCH /api/unidades/{id}` y `PATCH /api/categorias/{id}`, que la web usa (`lib/api/unidades.ts:53`, `categorias.ts:43`), siguen sin declararse. Lo anoto para el PR #4.
- Raíz `/`: sin loop en lo que razoné; no la miré en un navegador real ni con Clerk.

## Lente 3 · Verdad de tests, comentarios y specs

**Hecho**: mutantes de E3 sobre cada test nuevo; contraste de la ayuda y la spec con el cálculo real de `pasos`; comentarios con referencias de línea contra el código; lectura de las aserciones de los tests de backend.

**Resultado**:

- **F4 (reproducida, MEDIA) · La ayuda del resumen, y la spec que la exige, dicen algo falso.** `ayuda.ts` dice "Un edificio recién creado arranca en 0 de 7 pasos … la barra avanza a 2 de 7", y el escenario "Ejemplo de la ayuda" de `specs/pantallas-del-edificio/spec.md` exige esos números. Pero la API real marca 4 pasos hechos en un edificio recién creado (`lectura.py:250-264`: `ubicacion` se completa en el alta, `grupos` es "hecho" sin grupos parciales, más categorías e intereses; lo fija `test_resumen_puesta_a_punto.py::test_edificio_recien_creado`, verde en el CI). La barra muestra "4 de 7" y, después de unidades y coeficientes, "6 de 7". El 3d cambió el 6 por el 7 sin chequear el arranque. Test: RB3D-4 (E5). **Ruteo**: como la spec exige el texto falso, el arreglo va primero al planner (corregir el escenario) y después al constructor.
- **F5 (mutante sobreviviente, BAJA) · El test del `PATCH` de edificio no distingue la respuesta de escritura del fixture de lectura.** Con la rama `PATCH` anulada (A1), el pedido cae en `enviar()` y devuelve el fixture `edificio.json`, cuyo `id` es justo `f760ca3b-…`, así que `toMatchObject({ id: EDIFICIO })` sigue verde: 53/53. Es el mismo modo de falla que L-027 (200 con el fixture de lectura a un `PATCH`). Un `toEqual({ id })`, o un id distinto del fixture, lo mata.
- **F6 (documental, BAJA, reproducida con `rg`, sin test) · Referencias de línea viejas en `api-falsa.ts`.** Los comentarios nuevos citan `editar_edificio (complejos.py:330)` y `editar_grupo (complejos.py:494)` (líneas 321, 364 y 832); en `b1ec660` y en `e29e36d` las rutas son `modificar_edificio` en `:342-343` y `modificar_grupo` en `:506-507`.
- **Aserciones débiles (JUICIO, sin falla demostrada)**:
  - `test_clave_explicita_invalida.py` y `test_rompedor_clave_patch_grupo.py`: `assert clave not in respuesta.text` no vigila nada con `"abc\n"`, porque el JSON escapa el salto de línea (`json.dumps` da `abc\\n`, y `"abc\n" in texto` es `False` aunque el valor vuelva). El de `PATCH` tampoco verifica que el 422 nombre `clave` (`loc`), que es lo que pide el ítem 5.
  - `ayuda.test.ts` fija "7" a mano en vez de derivarlo de los pasos de la pantalla (`_PASOS` no se exporta), y el regex `\bde 6\b` no atrapa "seis". Es el mismo problema que el 3d vino a corregir (L-051).
  - `comprobaciones.spec.ts`: los títulos siguen diciendo "la portada real" y ahora miden `/ingresar`; la raíz `/` se quedó sin ningún test de navegador (9.2 lo declara).
  - `configuracion/Pantalla.dia-fuera-de-rango.test.tsx`: no hay cambio de producción en `configuracion/` en el diff, así que estos tests nacieron verdes (el comportamiento ya existía). No es un defecto del código, pero no hay un RED de esa tarea y `tasks.md` no guarda RED/GREEN de ninguna. Lo dejo para el auditor.
- Con el resto limpio: los tests de CSP, pisos, raíz, axe por estado y el contrato de tipos de la falsa matan sus mutantes (E3).

## SUPOSICIÓN (sin reproducir)

- **S1 · CSP frente a otro formato de Clerk**: el filtro separa por `"; "` y compara con minúsculas exactas. Las palabras clave de CSP no distinguen mayúsculas; si Clerk emitiera `'UNSAFE-INLINE'`, `;` sin espacio o `script-src-elem`, el filtro no las sacaría. Clerk 7.9.19 no lo hace hoy (E4). Para confirmarlo hace falta otra versión de Clerk o un test con una política armada a mano.
- **S2 · Pisos no enteros**: con el loop nuevo, `vocabularioDePisos(4, 1.5)` daría `SS1.5` (antes daba `SS1`). La API real sólo devuelve enteros (`strict`, `ge/le`), así que hoy no se alcanza. No lo ejecuté.
- **S3 · Sesión de Clerk sin token** (`userId` presente y `getToken()` nulo): `/` manda a `/ingresar`, que con una sesión activa puede redirigir a `/elegir-administracion` y volver. Es el camino del 2d, no de este diff; hace falta Clerk real para confirmarlo.
- **S4 · Piso fuera del vocabulario** (una unidad con `SS3` después de bajar a 2 subsuelos): el `<select>` cae en "Sin completar" y guardar borraría el piso. Viene del 3c, el reordenamiento no lo cambia. No lo ejecuté.

## Conteo propio

- Tests corridos en verde: 77 (12 archivos, E1) + 2 de la sonda de CSP (borrada).
- Corridas de mutantes: 14 mutantes (E3); 13 muertos, 1 sobrevive (A1).
- Tests nuevos del rompedor: 5, todos fallan sobre `b1ec660` (E5).
- Sonda del contrato real: 13 pedidos contra los modelos reales (E2).
- Sin correr: suite completa (reutilicé E0), integración del backend local, Playwright y navegador real.

## JUICIO

Autor: rompedor (Claude, intento 1). Comparé el diff contra el plan, contra la API real (modelos y cálculo de pasos) y contra `config/georef/`. Confianza: alta en F1 a F6 (reproducidas con comando o mutante); media en las aserciones débiles; baja en S1 a S4. El núcleo del cambio (pisos, raíz, CSP, axe, día y clave) funciona y sus tests vigilan. Lo que falla es la fidelidad de la API falsa nueva (F1, F2, F3, F5) y la verdad de la ayuda y su spec (F4). Este informe no reemplaza al auditor.

## Fallas reproducidas

1. **F4** (MEDIA): la ayuda y la spec dicen "0 de 7 / 2 de 7"; la API real da 4 de 7 al crear el edificio. Test `ayuda.rompedor-3d.test.tsx`. Va al planner (spec) y después al constructor.
2. **F1** (BAJA): `PATCH` sin cuerpo: 200 en la falsa, 422 en la real. RB3D-1.
3. **F2** (BAJA): `PATCH /api/grupos/{no-uuid}`: 200 en la falsa, 422 en la real. RB3D-2.
4. **F3** (BAJA): 4 nombres de Georef simulados no coinciden con `config/georef/`. RB3D-3.
5. **F5** (BAJA): sobrevive el mutante A1 (sin la rama `PATCH` de edificio, el test sigue verde).
6. **F6** (BAJA, documental): referencias `complejos.py:330/494` viejas en `api-falsa.ts`.
