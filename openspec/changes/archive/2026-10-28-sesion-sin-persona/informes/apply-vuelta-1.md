# Apply 2d · vuelta 1

## EVIDENCIA

Constructor `/root/apply_v1`. Generado 2026-10-28T11:50:52.283830-03:00. `git rev-parse HEAD`: `0fa013c7643c2cd0edda7793b0b3dc40b5a84dfe`. Rama `apply/sesion-sin-persona-v1`; base firmada `7a49eff`.

Preparación,28/10/2026:  `git rebase main`11:04:23 → rama actualizada con main local; `cd backend && uv run alembic heads`11:05 → `0027 (head)`. Baseline: comando backend completo de1.1,11:04:23–11:06:34 →743passed/131.11s; `bash infra/ci/test-web.sh`,11:07:04–11:07:47 →65archivos/432passed/43.11s.

### Tabla TDD

|Tarea|Test/contrato|Rojo ejecutado|Verde ejecutado|Mutante|
|---|---|---|---|---|
|1.1|baseline|no corresponde|743backend+432web, SHA7a49eff|no corresponde|
|2.1|sesión 403 y cabeceras;401sin SQL|11:08,status401/200!=403|486passed86.00s,11:16:58|a–d muertos|
|2.2|precedencia, auditoría sólo elegida, accesoB|11:08,status401!=403|incluido486passed|a–e muertos|
|2.3|sin consulta por email ni cuerpo distinto|11:08,401!=403;11:46literal agrega motivo|2passed6.41s11:47:32 restaurado|ORemail y SELECTliteral/cuerpo distinto muertos, sin desactivarRLS|
|2.4|barridos403/permiso y Error403|11:08,codigo ausente|incluido486passed|campo omitido y rama403nueva muertos|
|3.1|cliente por codigo,401 y sesión nula|11:17,resultado/redirect incorrecto|488passed51.55s11:26:37|a–d muertos|
|3.2|regreso normalizado,512/513,ñ,idempotencia|11:17,aserciones de regreso|incluido488passed|a–d muertos|
|3.3|ciclo de 50vueltas|11:17,regreso anidado/rebote|incluido488passed|D3 sola:1 falló / 1 pasó;D2 sola:otro1 falló / 1 pasó|
|3.4|selector página/acción sin rebote|11:17,markup/redirect|incluido488passed|página/acción sin devolver, muertos|
|3.5|email cliente,sin API,layout,axe|11:17,markup/página vacíos;guardas aparte|incluido488passed|props/API/layout/email / carga / axe muertos|
|3.6|Tab y Enter|rojo específico:tabIndex=-1 en segunda acción|incluido488passed;foco real e2e|muerto en activeElement|
|3.7|fake,navegación,320/1280,axe,outline|11:20fake401!=403;11:21e2eURL/ingresar!=/sin-acceso|7passed3.5s11:27:20,build+types|D2revertida en e2e:1failed11:25;restaurada7/7|
|5.1|validación,vínculo,carreras,rollback,HTTPsesión|11:30,27failed/62passed38.73s;mensajeCLI1failed|332passed48.98s11:44:10|a,b,c,d,d2,e,f,g,g2,h,i+normalización+otra integridad muertos|
|5.2|alcance fijo y misma transacción|mismos rojos5.1,sin ImportError|mismo332passed|overwrite y fuera de transacción, muertos|
|5.3|lista permitida imports|11:28:27,is_fileFalse/1failed|incluido332passed|API / from y acceso / import,checkerreal exit1 nombraofensor|
|5.4|README|texto,no test trivial|escrito;recorrido humano PENDIENTE|no se inventó persona/fecha/SHA|

Total 47 mutantes acreditados: 13API, 19web, 15 ejemplo. Cada diff, comando, hora, salida y file:line está en `informes/evidencia-api-v1.md`, `evidencia-web-v1.md`, `evidencia-ejemplo-v1.md`; evidencia de tareas en tasks.md. Copias sin commit y restauración en finally; scripts/backups ignorados en `.atl/2d-v1`, ningún mutante en producción.

### Comandos y resultados


```text
COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py tests/unitarios/test_fronteras_de_modulos.py tests/unitarios/test_configuracion.py tests/unitarios/test_configuracion_clerk.py tests/unitarios/test_configuracion_pool.py tests/unitarios/test_configuracion_secreta.py tests/unitarios/test_logs_configuracion.py tests/unitarios/test_semilla_configuracion.py
TIME: 2026-10-28T11:43:20.677977-03:00
EXIT: 0
TIME: 2026-10-28T11:44:10.999584-03:00
======================= 332 passed, 1 warning in 48.98s ========================
```

```text
COMMAND: bash infra/ci/test-web.sh
TIME: 2026-10-28T11:25:45.287955-03:00
EXIT: 0
TIME: 2026-10-28T11:26:37.267240-03:00
Test Files  71 passed (71)
Tests  488 passed (488)
```

```text
COMMAND: bash infra/ci/test-web-navegador.sh sesion.spec.ts
TIME: 2026-10-28T11:27:10.875011-03:00
EXIT: 0
TIME: 2026-10-28T11:27:20.694204-03:00
7 passed (3.5s)
```

```text
COMMAND: bash infra/ci/test-backend.sh tests/integracion/test_deuda_acceso_2b.py::test_el_403_no_depende_del_email_ni_lee_por_email
TIME: 2026-10-28T11:47:24.880796-03:00
SHA: 0fa013c7643c2cd0edda7793b0b3dc40b5a84dfe
EXIT: 0
TIME: 2026-10-28T11:47:32.565965-03:00
========================= 2 passed, 1 warning in 6.41s =========================
```

```text
PENDIENTE: cierre posterior al commit de entrega; ver informe externo final.
```

```text
PENDIENTE: cierre posterior al commit de entrega; ver informe externo final.
```

```text
PENDIENTE: cierre posterior al commit de entrega; ver informe externo final.
```

```text
PENDIENTE: cierre posterior al commit de entrega; ver informe externo final.
```

```text
PENDIENTE: cierre posterior al commit de entrega; ver informe externo final.
```

```text
PENDIENTE: cierre posterior al commit de entrega; ver informe externo final.
```

```text
PENDIENTE: cierre posterior al commit de entrega; ver informe externo final.
```

```text
PENDIENTE: cierre posterior al commit de entrega; ver informe externo final.
```

```text
PENDIENTE: cierre posterior al commit de entrega; ver informe externo final.
```

### Commits

```text
12c1843 chore(acceso): fijar baseline de la primera vuelta del 2d
487fae1 fix(acceso): distinguir una sesión válida sin acceso
0fa013c fix(web): cortar el ciclo de ingreso sin acceso
```

El informe interno conserva este retorno completo previo al commit5; el anexo de cierre posterior al commit, con su SHA real, se completa en el informe externo solicitado `../informe-2d-v1.md`. No se agrega un commit documental extra. No se hizo push.

Fuente oficial consultada sin login el28/10/2026:  [Clerk, How Clerk works](https://clerk.com/docs/guides/how-clerk-works/overview), sección The frontend API, documenta FAPI de desarrollo `https://<slug>.clerk.accounts.dev`; complemento [Convex](https://clerk.com/docs/guides/development/integrations/databases/convex). Ningún emisor real fue leído o publicado.

## JUICIO

Constructor contra proposal E1–E11 firmadas por Juani el 28/10/2026, design D1–D5 y specs. Confianza alta en el alcance automatizado. Grupos1,2,3 y5 construidos, con 5.4 pendiente de recorrido por Emiliano/Gianfranco. No se tocaron grupos4,6,7; las tres excepciones SQL históricas de ejemplo quedan para6.8.1 y 8.2 sin marcar. No hay aprobación de verify/auditor/archive/CI remoto.

Resoluciones propias L-030, sin nuevas reglas de negocio:

- D5 exige igual mensaje en chequeo previo y UNIQUE; mutanteg se discrimina por SELECT previo, garantía ya firmada. Ambos mantienen mensaje fijo sin ids ni parámetros.
- `/` final del emisor, rotulado guarda, era un rojo real del validador general. Sólo CLI valida URL completa y pasa override opcional `Configuracion(clerk_emisor=normalizado)`. Sin override sigue `_LectorDeApp()` idéntico y el validadorAPI/worker no cambia. Helpers de rutas en ejemplo reciben ese objeto para no releer rawemisor. No se muta os.environ.239 guardas de configuración pasaron antes/después.
- Páginas servidor/ciclo: renderToStaticMarkup en node; teclado cliente en jsdom; foco/ancho/axe reales en Chromium. Intentos con server-only / configuración incompleta se descartaron como errores del arnés. Guardas nacidas verdes (axe/ceroAPI/layout/foco/error noUNIQUE) se acreditaron con mutantes. Primer intento literal2.3 sin selector no encontraba filas bajoRLS; se descartó y se acreditó con selectorA, sin desactivarRLS.

Fuentes: brief;AGENTS;proposal/design/tasks/seis specs;knowledge-base/15_lecciones.md;skillapply y skills TDD,postgres-rls,SQLAlchemy,impeccable con PRODUCT/DESIGN. Consumidores considerados: APIguarda/sesión, Nextcliente/layout/selector/ingreso, CLI, scriptsCI y fakee2e. No se escribió firma humana ni se editaron KB/AGENTS/CLAUDE.

Despacho: un constructor con alcance explícito, secuencial, una suite pesada a la vez. Backend,QA,DBA,arquitecto,frontend,analista,DevOps no convocados como revisores: fase apply; ver dispatch-v1.md. No se infiere aprobación. Constructor declarado Codex/OpenAI, modelo heredado compartido con orquestador; no independencia de familia. Identidad exacta no expuesta por harness. Brief mediado por orquestador; retorno completo preservado.

Pendientes:5.4 requiere otra persona con su cuenta y base limpia. El brief prohíbe login a proveedores: no se verificó ese recorrido.grupos 4, 6 y 7 para vuelta 2;8.1 y 8.2 tras vuelta 2. No humo,compose real,CI remoto ni push. PostgreSQL y tokens RSA locales no validan Clerk real.

### Drift de KB (sin reparación)

Constructor contra fecha autora git y día de carpetas archivadas; confianza media: bytes no equivalen a revisión vigente.

|Documento|Fecha autora|Archivados en días posteriores|
|---|---|---|
|01_vision_y_objetivos.md|2026-10-20T16:45:56-03:00|2026-10-22-login-y-usuarios, 2026-10-24-acceso-de-desarrollo, 2026-10-26-cimientos-del-libro, 2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion|
|02_descripcion_general.md|2026-10-26T15:21:27-03:00|2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion|
|03_actores_y_roles.md|2026-10-27T13:16:20-03:00|2026-10-28-pulido-de-la-configuracion|
|04_modelo_de_datos.md|2026-10-28T09:35:44-03:00|ninguno por fecha; no prueba vigencia|
|05_reglas_de_negocio.md|2026-10-27T15:23:10-03:00|2026-10-28-pulido-de-la-configuracion|
|06_funcionalidades.md|2026-10-27T15:23:10-03:00|2026-10-28-pulido-de-la-configuracion|
|07_flujos_principales.md|2026-10-26T15:21:27-03:00|2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion|
|08_arquitectura_propuesta.md|2026-10-28T09:35:44-03:00|ninguno por fecha; no prueba vigencia|
|09_decisiones_y_supuestos.md|2026-10-28T09:37:45-03:00|ninguno por fecha; no prueba vigencia|
|10_preguntas_abiertas.md|2026-10-28T09:36:32-03:00|ninguno por fecha; no prueba vigencia|
|11_glosario.md|2026-10-27T15:23:10-03:00|2026-10-28-pulido-de-la-configuracion|
|12_fichas_de_changes.md|2026-10-28T09:37:45-03:00|ninguno por fecha; no prueba vigencia|
|13_motor_de_reglas.md|2026-10-20T16:45:56-03:00|2026-10-22-login-y-usuarios, 2026-10-24-acceso-de-desarrollo, 2026-10-26-cimientos-del-libro, 2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion|
|14_forma_de_trabajo.md|2026-10-27T13:16:20-03:00|2026-10-28-pulido-de-la-configuracion|
|15_lecciones.md|2026-10-28T09:35:44-03:00|ninguno por fecha; no prueba vigencia|
|16_proyecto_final.md|2026-10-14T17:46:18-03:00|2026-10-15-aislamiento-por-administracion, 2026-10-16-endurecimiento-de-infraestructura, 2026-10-19-configuracion-del-edificio, 2026-10-20-pantallas-del-edificio, 2026-10-20-roles-de-la-empresa, 2026-10-22-login-y-usuarios, 2026-10-24-acceso-de-desarrollo, 2026-10-26-cimientos-del-libro, 2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion|
|README.md|2026-10-15T09:57:44-03:00|2026-10-16-endurecimiento-de-infraestructura, 2026-10-19-configuracion-del-edificio, 2026-10-20-pantallas-del-edificio, 2026-10-20-roles-de-la-empresa, 2026-10-22-login-y-usuarios, 2026-10-24-acceso-de-desarrollo, 2026-10-26-cimientos-del-libro, 2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion|

## SUPUESTO

No verificado con proveedor real: email del navegador, signout, dos pestañas, invitaciones y recorrido por segunda persona.5.4 y 8.2 pendientes. El patrón de dominio corresponde a documentación consultada, no a una prueba contra instancias reales. Fechas de archivo tomadas de nombres; no se ejerció archive. Versión exacta del modelo no expuesta. main comparado localmente; no fetch/push. Cierre sólo de esta vuelta; no suite backend completa ni CI remoto.
