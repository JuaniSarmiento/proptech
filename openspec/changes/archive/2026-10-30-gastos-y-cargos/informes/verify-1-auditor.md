# verify · intento 1 · AUDITOR · `gastos-y-cargos` (6, MEDIUM)

- **Autor**: role-auditor, subagente nativo de Claude (Claude Code, Opus), despachado por el orquestador.
  Misma familia que los tres constructores (Claude); distinta del rompedor (Codex, OpenAI).
- **Fecha**: 30/10/2026.
- **Revisión auditada**: `51a7ff3` (rama `revision-6`). Código de producción vigente desde `f432055`;
  `f432055..51a7ff3` sólo suma tests del rompedor 3, `tasks.md`, informes y `LEEME.md`.
- **Base de comparación**: `main` `60b3dd5`; rama original de Emiliano `2f81682` (base `5c6d84c`).
- **Lecciones**: leí `knowledge-base/15_lecciones.md` (títulos L-001 a L-064 y texto completo de L-033 a
  L-064). Aplicadas: L-034/L-049 (dónde cae el rojo), L-035, L-041/L-055/L-064 (suite entera), L-043
  (script fuera de CI), L-056 (clon normal), L-060 (tarea bloqueada por una persona), L-061 (RED en el
  mismo commit), L-062 (gitleaks).

## Veredicto: **BLOQUEANTES**

Los dos bloqueantes son de gobierno y los resuelve una decisión escrita de Juani (o de Alberto), no
código. La técnica de la revisión `51a7ff3` está limpia en todo lo que verifiqué yo mismo: suite
completa `4736 passed, 1 xfailed`, una cabeza `0033`, ruff, format y mypy limpios, gitleaks limpio,
ninguna escritura en el libro.

## EVIDENCIA (propia, sobre `51a7ff3`)

Todo en un **clon normal** (L-056): `git clone wt-6 scratchpad/clon-auditor && git checkout 51a7ff3`
→ `51a7ff3f168e32004a7fa35b2a131aabb60cff22`, árbol limpio antes y después.

| # | Comando (desde `backend/` salvo indicación) | Hora | Resultado |
|---|---|---|---|
| A1 | `uv run alembic heads` | 16:19:42 | `0033 (head)` |
| A2 | `uv run ruff check .` | 16:19:42 | `All checks passed!` |
| A3 | `uv run ruff format --check .` | 16:19:42 | `404 files already formatted` |
| A4 | `uv run mypy` | 16:19:42 | `Success: no issues found in 367 source files` |
| A5 | `bash ../infra/ci/test-backend.sh -q -p no:cacheprovider` | 16:19:39 a 16:39:57 | **`4736 passed, 1 xfailed, 19 warnings in 1194.13s`**, exit 0 |
| A6 | `uv run pytest --collect-only -q -p no:cacheprovider` | ~16:25 | `4737 tests collected` |
| A7 | conteo propio de la salida de A5: caracteres `.` y `x` en las 66 líneas de progreso | 16:40 | 4736 `.` + 1 `x` = 4737 = A6. Ningún `F` ni `E` |
| A8 | `git diff --stat 60b3dd5..51a7ff3 -- web/` | 16:20 | vacío: el 6 no toca la web; no corrí la suite web |
| A9 | `diff AGENTS.md CLAUDE.md` (raíz) | 16:20 | vacío |
| A10 | `gitleaks git --config .gitleaks.toml --log-opts="--all" --redact .` (raíz) | 16:21:47 | `573 commits scanned`, `no leaks found` |
| A11 | `openspec validate gastos-y-cargos` (openspec **1.14.3**; el proyecto fija 1.13.0) | 16:21:41 | `Change 'gastos-y-cargos' is valid`, sólo warnings de largo |
| A12 | `bash -n infra/ci/ensayo-roles.sh` | 16:21:41 | sintaxis válida |

Conteo independiente: 4703 passed + 1 xfailed declarados por el constructor 3 sobre `f432055` (dato
ajeno), más los 33 tests que suma `51a7ff3` (`--collect-only` propio: 32 en
`tests/unitarios/test_rompedor_gastos_intento_3.py`, 1 en `tests/integracion/test_rompedor_gastos_intento_3.py`)
dan 4737, igual a A6. El test de integración del rompedor 3 que sólo estaba recolectado
(`test_periodo_factura_editada`) corrió en A5 y pasó.

### Comprobaciones dirigidas

- **El 6 no escribe en el libro** (condición de escalamiento a CRITICAL, proposal · Gobernanza).
  `rg -i '(insert into|update|delete from)\s+(movimiento|obligacion|imputacion|cuenta)'` sobre
  `proptech_core/gastos`, `proptech_api/gastos.py` y las migraciones `0029`-`0033`: sin resultados.
  Las únicas escrituras del módulo son `INSERT`/`UPDATE` sobre `proveedor`, `gasto`, `nota_de_credito`
  y `cargo_particular`. "imputacion" sólo aparece como la columna `periodo_de_imputacion`. **Sigue
  MEDIUM.**
- **Cadena de Alembic**: `0028`(`ver_personal`, 2d) → `0029` → `0030` → `0031` → `0032` → `0033`, leída
  de `revision`/`down_revision`. Una sola cabeza (A1). `test_libro_rollback.py` baja desde la cabeza
  hasta `0022`, así que los `downgrade` de `0033` a `0029` corren dentro de A5.
- **RLS**: las cuatro tablas nuevas llaman a `aislar_por_administracion` (`FORCE ROW LEVEL SECURITY` +
  política + `GRANT`), en `0029` (`proveedor`, `gasto`) y `0032` (`nota_de_credito`, `cargo_particular`).
- **`ensayo-roles.sh`**: `verificar_revision 0033` dos veces y mensaje `ciclo 0033/0016/0033`
  (`git diff 60b3dd5..51a7ff3 -- infra/ci/ensayo-roles.sh`). **No lo ejecuté** (necesita Compose, L-043);
  `test_ensayo_login.py`, que compara el número con la cabeza real, pasó dentro de A5.
- **Numeración sin pisar `main`**: los primeros N bytes de `knowledge-base/09_decisiones_y_supuestos.md`
  y `15_lecciones.md` son idénticos a los de `git show 60b3dd5:<archivo>` (`cmp`: iguales). Últimos
  encabezados: `D-139` en main, `D-140`/`D-141` agregados; `L-062` en main, `L-063`/`L-064` agregados;
  sin encabezados duplicados (`sort | uniq -d` vacío). Ninguna referencia del 6 queda en `D-131`/`D-132`
  (`rg 'D-13[12]'` filtrado por gasto/proveedor/cargo/nota en `CHANGES.md` y KB12: vacío).
- **Autorización de las 19 rutas**: cada `@router` de `proptech_api/gastos.py` pasa por
  `_edificio_autorizado`, `_lectura_autorizada`, `_autorizar_gasto`, `_autorizar_proveedor` o
  `_autorizar_cargo` (mapa con `rg`, líneas 138 a 531). Lectura con `VER_CONFIGURACION_DEL_EDIFICIO`,
  escritura con `CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION`; ninguna acción nueva en la matriz.
- **Exposición del importador de Excel**: `infra/Caddyfile` responde 404 a `/api/*` salvo
  `/api/salud`; la web no tiene consumidor de `cargos-particulares` (`rg` en `web/`: sólo menciones de
  texto en el 3b/2d, ninguna llamada). Hoy la ruta de importación no es alcanzable desde afuera.
- **Sonda propia del Excel** (`scratchpad/sonda_formula.py`, 16:21:18): una planilla con `C2 = =500+500`
  escrita por openpyxl (sin valor en caché) se lee como `importe=None` (se rechaza); la misma celda con
  `<v>1000</v>` en caché, como la deja Excel, se lee como `importe='1000'`. El comentario de
  `gastos/adaptadores/excel.py` ("no se usan nunca celdas con fórmula como entrada: se leen como texto
  crudo") es **falso**: con `data_only=True` se usa el valor en caché. No ejecuta la fórmula (eso sí es
  cierto) y el valor igual pasa por la validación de `Dinero`. Además, `importar_cargos_particulares`
  hace `await archivo.read()` sin tope y el adaptador no limita bytes ni filas, contra la mitigación
  escrita en `design.md` · Risks ("acota el tamaño del archivo y la cantidad de filas").
- **`complejos/aplicacion/errores.py::error_de_validacion`** (3a): devuelve sólo los nombres de campo,
  sin la explicación del validador. Confirmado leyendo el archivo; es anterior al 6 y el 6 no lo tocó.

### Lo que el merge y los arreglos tocaron fuera de `gastos`

`git diff --stat 60b3dd5..51a7ff3`, excluyendo el módulo, su router, sus tests y el change: 49
archivos. Producción fuera de `gastos`, revisada línea por línea:

| Archivo | Cambio | Juicio |
|---|---|---|
| `proptech_api/app.py` | registra el router y los manejadores de error del 6; renombra `tipo` → `tipo_del_libro` | wiring pedido por el proposal (Impact) |
| `acceso/dominio/eventos.py` | `EventoDelGasto` nuevo | aditivo, pedido (auditoria-de-acciones MODIFIED) |
| `acceso/aplicacion/auditoria.py` | modelos de detalle de los 10 eventos; alias `_Accionable`; `miembros` en `_DetalleFijarUnidades` | aditivo; `miembros` es RB-5, asignado al 6 por D-130 |
| `complejos/aplicacion/grupos.py` | `miembros` entran/salen en la auditoría de `fijar_unidades` (`2e2e925`) | RB-5 (D-130); declarado en proposal · "Deuda heredada" |
| `complejos/aplicacion/lectura.py` | `cuit` en `ComplejoLeido`; `cargar_unidad_por_identificador`; `activo` en `cargar_grupo`; `listar_categorias_obligatorias` | puertos de sólo lectura, aditivos; las fronteras de módulo lo exigen |
| migraciones `0029`-`0033` | tablas nuevas; columnas nullable/default en `complejo` y `categoria_de_gasto`; `UNIQUE` aditivo en `categoria_de_gasto` | aditivas, con `down` |
| `infra/ci/ensayo-roles.sh` | cabeza `0028` → `0033` | necesario |
| `.gitleaks.toml` | allowlist acotada a `test_gastos.py` y al texto exacto | convive con `.gitleaksignore` de `main` (`bc7b9ce`); redundante, no dañino |
| `pyproject.toml` / `uv.lock` | `openpyxl`, `python-multipart`, `types-openpyxl`, `fastapi.File` | pedidos por el importador |

Tests de otros changes tocados: `test_personal_api.py` (expectativa por el contador nuevo de la
fixture), `test_libro_rollback.py`, `test_vocabulario_configuracion.py`, `test_auditoria_tabla.py`,
`test_auditoria_transaccion.py`, `test_rutas_protegidas.py`, `test_identidad_antes_del_cuerpo.py`,
`test_regresiones_de_aislamiento_y_grupos_vacios.py`, `test_altas_sin_id_del_cliente.py`, `conftest.py`
y `test_fronteras_de_modulos.py`. En todos el diff **agrega** rutas, ids, eventos o cabeza; no encontré
una aserción existente debilitada (leí las líneas `-` del diff de cada uno). Los textos borrados de la
KB son los REWRITE que declara el proposal (las cuatro entidades "planificadas", P36/P37 abiertas, la
fila RB-5).

**No hay reescritura de algo existente ni código crítico tocado sin pedido.**

## JUICIO

Autor: role-auditor (Claude). Comparación: plan revisado (`proposal.md`, `design.md`, `tasks.md`,
specs) contra el diff `60b3dd5..51a7ff3`, los seis informes originales y mis propias corridas.
Confianza: alta en lo técnico (todo lo de la tabla de EVIDENCIA lo corrí yo); alta en que B1 y B2
existen como hechos documentales; la disposición es humana.

### Bloqueantes

**B1 · Falta el revisor del plan y el RED original no vale como RED.** Responsable: **Juani**
(decisión); si elige revisión retroactiva, planificador y revisor del plan.

- MEDIUM exige cinco roles. El 6 se construyó sin informe de plan-reviewer (no existe en ningún lado
  del change; `LEEME.md` lo declara) y sin informes de rompedor ni auditor de Emiliano.
- El RED de Emiliano en los bloques 2 a 5 se obtuvo **sacando la implementación a un respaldo**, y
  falla por setup, no por aserción: 2.1 `ModuleNotFoundError`, bloque 3 `29 errors` (`ImportError`),
  bloque 4 `17 errors` (`ImportError`), bloque 5 `21 errors` (`ImportError`, "documentación
  retroactiva"), 5.6 `ModuleNotFoundError` (`tasks.md` líneas 52, 109, 145, 155-159, 175, 185). Por el
  contrato del constructor y L-061 eso no es RED. Hay excepciones válidas (1.1, 1.3, 6.1, 7.1 y los
  mutantes 3.7, 4.5, 5.4, 8.2 como tests permanentes).
- Lo que el rompedor y yo aportamos como sustituto: tres rondas de rompedor (Codex) contra el plan,
  con 8 hallazgos reproducidos y cerrados (F1 a F4, S1, S2, F2-1, S4), mutantes de los constructores 2
  y 3 (M1 a M6), los cuatro mutantes permanentes de Emiliano y la suite A5.
- Es el mismo caso que BJ-1 del 3d, que Juani aceptó como deuda justificada **por escrito** (D-139).
  Ese precedente no me autoriza a convertirlo en deuda solo: hace falta la misma decisión escrita para
  el 6. **Recomendación**: aceptarlo como deuda con la evidencia sustituta de arriba. La revisión que
  hicieron los rompedores contra el plan cubrió buena parte de lo que habría visto un revisor del plan
  (S4 y la promesa de límites del Excel salieron de leer la spec y el design contra el código).

**B2 · P36 y P37 las respondió Emiliano, pero el plan pedía a Juani o a Alberto.** Responsable:
**Juani o Alberto** (ratificar o cambiar); si cambian la respuesta, vuelve a planificador y constructor
(tareas 6.1 y 7.1).

- `proposal.md:136`: la tabla de P25, P36 y P37 dice "Propuesta (**a confirmar por Juani o Alberto**)".
  `tasks.md:13-18`: 6.1 y 7.1 estaban "BLOQUEADA a la espera de respuesta escrita de Juani o Alberto";
  las destrabó Emiliano "como dueño del change" (D-141, `Quién: Emiliano Caceres, 28/10/2026`).
- D-111 hace firmante a Emiliano de propuestas HIGH y CRITICAL; no le asigna responder preguntas que
  el propio plan reservaba a Juani o Alberto. P36 define cómo un gasto aprobado tarde entra en la
  liquidación del 7 (CRITICAL), así que el efecto llega a la plata.
- Es el patrón de L-060 y de BJ-2/BJ-3 del 3d, ratificados por Juani en D-139. D-141 no está en `main`
  todavía, así que ratificarla ahora no reescribe nada.
- La implementación sigue exactamente las propuestas del plan (D7/D8 del design), con tests y mutantes
  (`test_periodo_de_imputacion.py`, `test_obligatorios_faltantes.py`). Si Juani ratifica, no hay que
  tocar código.

### Hallazgos resueltos que verifiqué y no reabro

F1 (detalle sin permiso), F2 (PATCH vacío), F3 (texto del 422), F4 (D-131), S1, S2, F2-1 y S4: hay test
de integración o unitario para cada uno dentro de A5, y pasan. Lo de F2-1 (el guardia sólo se prueba
con dobles porque por HTTP es inalcanzable: `CuerpoDeEdicion.no_nulo` rechaza el `null` antes) lo
acepto: la capa HTTP lo frena hoy y el guardia queda para consumidores futuros. Va a DEUDA (D5).

### Frescura e independencia de los informes

| Informe | Revisión que declara | ¿Vigente para `51a7ff3`? |
|---|---|---|
| `apply-1-constructor.md` | entrega `838a0b3` | sí para la integración; su suite (4641) quedó superada por A5 |
| `verify-1-breaker.md` | `40af1a1` (código `838a0b3`) | superado por las correcciones; sus hallazgos cerrados |
| `apply-2-constructor.md` | entrega `58f2d76` | sí; F1-F4/S1/S2 verdes en A5 |
| `verify-2-breaker.md` | `63582e4` (código `58f2d76`) | superado por `f432055`; F2-1/S4 cerrados |
| `apply-3-constructor.md` | entrega `f432055` | sí: es el código vigente |
| `verify-3-breaker.md` | `8e6e13e` (código `f432055`) | sí: `8e6e13e..51a7ff3` sólo suma sus propios tests y documentación |

- Los rompedores no tuvieron Docker: su integración la corrió el orquestador (tasks.md) y ahora A5.
  Ninguna conclusión de RLS o carrera de los rompedores se presentó como propia; está bien declarado.
- Los rompedores declararon contaminación por el brief y por `openspec instructions` (que imprime
  `tasks.md`). Sus hallazgos salieron del código y se reprodujeron por aserción; no veo conclusiones
  copiadas sin reproducir.
- **Independencia limitada**: constructores y auditor somos de la misma familia (Claude). El
  orquestador, también Claude, escribió los briefs y la sección de estado de `tasks.md`, que leí. El
  rompedor (Codex) es la única mirada de otra familia.
- `LEEME.md` registra para el rompedor 1 "plugin no disponible, subagente nativo Codex", y el
  `tasks.md` del orquestador dice "plugin `codex:codex-rescue`". El informe original manda; lo dejo
  anotado (el rompedor 2 ya lo señaló) y no cambia ningún resultado.

## SUPOSICIÓN (lo que no verifiqué)

- `infra/ci/ensayo-roles.sh` sin ejecutar (Compose, L-043); sólo sintaxis (A12) y su test de número.
- `shellcheck` no está instalado: no corrió.
- Web: no corrí lint, tipos ni tests porque `web/` es idéntico a `main` (A8).
- CI remoto: no miré `gh run list` sobre `51a7ff3` ni sobre ninguna revisión de esta revisión
  independiente. El único CI verde citado es de Emiliano sobre `484eb1b` (antes del merge). **Antes de
  mergear el PR #4 hace falta CI verde sobre el SHA final** (L-042).
- `openspec validate` corrió con 1.14.3, no con la 1.13.0 fijada.
- La carrera entre editar el importe y cargar una nota (S2) no tiene test de concurrencia; las dos
  operaciones toman `FOR UPDATE` sobre la misma fila de `gasto` (lo leí, no lo ejecuté).
- No medí el costo del bucle de consultas al padrón por fila de la importación.
- Engram no lo usé.

## DEUDA (cada ítem con su destino sugerido)

| # | Deuda | Evidencia | Destino sugerido |
|---|---|---|---|
| D1 | El importador de Excel no limita bytes ni filas (`archivo.read()` sin tope), contra `design.md` · Risks. Hace una consulta al padrón por fila, contra D6 | sonda y lectura de `excel.py` y del router; ruta hoy inalcanzable desde afuera (Caddy 404, sin consumidor web) | **C-08 `importacion-desde-excel` (5)**, el primero que vuelve a usar el puerto de planillas; a más tardar, el change de pantallas de gastos (D-140) antes de exponer la ruta |
| D2 | Comentario falso en `gastos/adaptadores/excel.py`: una fórmula con valor en caché entra como su valor | sonda de las 16:21:18 | **C-08**, junto con D1 (corregir el texto y decidir si las fórmulas se rechazan) |
| D3 | El vecino no ve por id su propio cargo particular (coherente con el listado). Decisión de producto pendiente | `apply-2-constructor.md`, JUICIO; `verify-2-breaker.md`, E3 | **C-16 `portal-del-vecino` (11)** |
| D4 | `complejos/aplicacion/errores.py` (3a) pierde la explicación del validador en el 422, como F3 | leído; anterior al 6 | **C-26 `pulido-web-3`** (los mensajes de error que ve el formulario) |
| D5 | El guardia de F2-1 sólo se prueba con dobles: por HTTP es inalcanzable | `apply-3-constructor.md`, SUPOSICIÓN | **C-08** o el primer consumidor que llame a `editar_gasto` sin pasar por `CuerpoDeEdicion` (worker, importación) |
| D6 | Sin test de concurrencia entre editar el importe y cargar una nota | `apply-2-constructor.md`, SUPOSICIÓN | **C-28 `revisiones-independientes`** |
| D7 | `ensayo-roles.sh` con cabeza `0033` sin ejecutar; `shellcheck` sin correr localmente | SUPOSICIÓN | **C-23 `humo-y-ci`** (y el CI del PR #4 para `shellcheck`) |
| D8 | `.gitleaks.toml` (allowlist del 6) y `.gitleaksignore` de `main` (DA-12) cubren el mismo falso positivo de `a6bb954`; como se integró por merge, `a6bb954` sigue en la historia y ninguno sobra todavía | A10; `.gitleaksignore`; DA-12 | **C-23 `humo-y-ci`** (ya tenía DA-12) |
| D9 | `test_gastos.py` cita `D-141-bis` (la columna `complejo.cuit`, tarea 3.10), que no existe en `09` | `apply-1-constructor.md`, JUICIO 4 | **el cierre de este change**: decisión nueva D-NNN o quitar la cita |
| D10 | openspec instalado 1.14.3, fijado 1.13.0 | A11 | **C-23 `humo-y-ci`** |
| D11 | Sin CI sobre el SHA final de la revisión independiente | SUPOSICIÓN | **quien mergee el PR #4**, antes del merge (L-042) |
| D12 | El change de pantallas de HU-A3/HU-A3b no tiene nombre ni lugar en el roadmap (D-140) | proposal · Decisión de alcance | **Juani**, al planificar (decisión de coordinación, no del 6) |

Si Juani acepta B1 como deuda, se suma acá como D13 (informes faltantes del plan-reviewer, rompedor y
auditor originales; RED por setup en los bloques 2 a 5), con evidencia sustituta y declarada en
`LEEME.md`, como DA-11 del 3d.

## LECCIONES

- **L-propuesta · Un comentario que describe lo que hace una librería se prueba contra la librería.**
  El adaptador decía que las fórmulas "se leen como texto crudo"; `openpyxl` con `data_only=True`
  devuelve el valor en caché. Ni el constructor ni tres rondas de rompedor lo ejecutaron, y lo
  confirmó una sonda de 20 líneas. Regla: si un comentario o un design promete un comportamiento de
  seguridad de una dependencia (no evalúa, no sigue enlaces, acota tamaño), hay un test que lo
  ejercita con la entrada adversaria mínima, o el comentario dice "no verificado".
- **L-propuesta · "Revisión independiente" de un PR ajeno no repone el revisor del plan.** El 3d y el
  6 llegaron sin plan-reviewer; en los dos lo que la revisión agregó fue rompedor y auditor sobre el
  código ya hecho, y en los dos terminó en una decisión de Juani sobre informes faltantes. Regla: si
  un desarrollador nuevo construye un MEDIUM o superior, el plan-reviewer corre antes del apply, o la
  falta queda declarada en el proposal desde el principio, no al auditar.

## Fuentes leídas

- Memoria: artefactos del change (`proposal.md`, `design.md` por secciones, `tasks.md` completo, specs
  por `rg`), `informes/LEEME.md`, los seis informes originales completos, la lista de
  `openspec/changes/archive/` (16 archivados, del `2026-10-09-infraestructura-base` al
  `2026-10-30-pulido-2`). **Engram no lo usé.**
- `CLAUDE.md` (proyecto y global), `CHANGES.md` (árbol, C-08, C-16, C-23 a C-29),
  `knowledge-base/09_decisiones_y_supuestos.md` (D-111, D-139, D-141), `10_preguntas_abiertas.md`
  (P36/P37 en `main` y en la rama), `15_lecciones.md`.
- Código: `proptech_api/gastos.py` (rutas y guardas), `proptech_api/app.py`,
  `gastos/adaptadores/excel.py`, `gastos/aplicacion/errores.py`, `complejos/aplicacion/errores.py`,
  `complejos/aplicacion/lectura.py` y `grupos.py` (diff), `acceso/aplicacion/auditoria.py` y
  `acceso/dominio/eventos.py` (diff), migraciones `0028`-`0033` (encabezados y DDL por `rg`),
  `infra/Caddyfile` (por `rg`), `infra/ci/test-backend.sh`, `infra/ci/ensayo-roles.sh` (diff),
  `.gitleaks.toml`, `.gitleaksignore`.

## Contaminación

Leí los seis informes y la sección del orquestador en `tasks.md` antes de mis corridas, así que conocía
sus conclusiones. Mis resultados propios son los de la tabla de EVIDENCIA (corridas, conteo, sonda,
lecturas de código y diffs). B1 y B2 salen de leer `tasks.md`, `proposal.md` y D-141/D-139 directo, no
de otro informe. D1/D2 parten de la sospecha S3 de los rompedores, pero la falsedad del comentario la
reproduje yo. D3, D5 y D6 son declaraciones de los constructores que no reproduje: las tomo como deuda
declarada, no como fallas demostradas.

## Próxima acción

El orquestador lleva B1 y B2 a Juani. Si Juani (o Alberto, para B2) ratifica por escrito en `tasks.md`
o en una decisión nueva, sin cambiar código, este informe puede pasar a APROBADO en un intento 2 del
auditor sin repetir la suite, porque `51a7ff3` no habrá cambiado. Si cambia la respuesta a P36 o P37,
vuelve a planificador y constructor, y después rompedor y auditor sobre la revisión nueva. APROBADO no
autoriza push ni merge del PR #4.
