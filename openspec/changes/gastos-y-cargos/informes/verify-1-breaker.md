# verify · intento 1 · ROMPEDOR · gastos-y-cargos (6)

- Autor: **Codex como rompedor**. Ejecutor efectivo: **subagente nativo Codex**, familia OpenAI/GPT; modelo concreto no verificado. Sustitución explícita del plugin Codex no disponible. No se atribuye ejecución al plugin.
- Revisión: `40af1a1d4ad8d94d63a6be638fba8ec468e3b0ca`; último código/specs `838a0b3`. Intento 1, sin reparación. Fecha: 30/10/2026.
- Recibido: brief del usuario con objetivo, worktree, diff `2f81682..838a0b3`, plan revisado, decisiones, límites, tres lentes, evidencia anterior y destinos. Recibí además instrucciones del orquestador para registrar sustituciones y no modificar producción ni tasks. El brief y esta revisión son la trazabilidad de dispatch disponible; no inventé un registro anterior en tasks.md.
- Escritura permitida por alcance: este informe, LEEME y archivo nuevo de reproducción. El permiso de workspace no impone esa lista por archivo: el alcance se comprobó con git al terminar.
- **Resultado del rompedor: CON FALLAS REPRODUCIDAS. No habilita cierre ni reemplaza auditoría.** Cuatro hallazgos, siete casos rojos por aserción. Integración real pendiente por falta de acceso a Docker.

## EVIDENCIA

### E0 · Entorno y estado

Comandos ejecutados durante esta revisión el 30/10/2026, antes del cierre UTC indicado al pie. Donde no capturé la hora individual, no invento precisión: la evidencia se identifica por esta ventana y revisión.

- `git rev-parse HEAD`: `40af1a1d4ad8d94d63a6be638fba8ec468e3b0ca`. `git status --short` inicial: vacío.
- `openspec list --json`: sólo `gastos-y-cargos`, 56/56 tareas, estado CLI `complete`. `openspec status --change gastos-y-cargos --json`: artefactos done. `openspec instructions apply --change gastos-y-cargos --json`: all_done. Ese estado de tareas no es aprobación de revisión.
- Leí `CLAUDE.md`, las instrucciones heredadas y las lecciones numeradas de `knowledge-base/15_lecciones.md` antes de las reproducciones. En particular L-003, L-004, L-005, L-008, L-019, L-034, L-035, L-043, L-046, L-055, L-056 y L-063/L-064. `obsidian.md` no existe en este worktree, tampoco como symlink. Engram no estuvo disponible como herramienta de este ejecutor.
- Intento de ejecución externa: `codex exec --ephemeral -s workspace-write -c approval_policy='"never"' -C <worktree> ...`: exit 1, `failed to initialize in-process app-server client: Read-only file system (os error 30)`. No inició una revisión CLI. Continué como subagente nativo, sin bypass ni escalación.
- `docker info --format '{{.ServerVersion}}'`: exit 1, `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock`. No corrieron integración, RLS, carreras ni upgrade/downgrade reales. No cloné para simular una corrida que igualmente requería Docker. El falso ENOTDIR conocido no fue interpretado como regresión.
- `uv run --no-sync ...` inicial no pudo escribir su cache de usuario; `UV_CACHE_DIR=/tmp/uv-rompedor-6` permitió usar el entorno existente, sin instalar dependencias.
- Un primer intento con TestClient y otra selección que incluía `test_dinero_pydantic.py` quedaron sin terminar y se interrumpieron. No se cuentan ni como verde ni como falla del producto. Las reproducciones entregadas llaman handlers y casos de uso directamente: **no son un recorrido HTTP completo ni una prueba de PostgreSQL**.

### E1 · Conteo propio y comandos

Todos los comandos de Python siguientes desde `backend/`, con prefijo `UV_CACHE_DIR=/tmp/uv-rompedor-6 uv run --no-sync`. Código de producción siempre en `40af1a1`.

| Comando | Resultado observado |
|---|---|
| `pytest tests/unitarios/test_fronteras_de_modulos.py -q -p no:cacheprovider` | **66 passed** en 2.84 s |
| `pytest tests/unitarios/test_cuit.py tests/unitarios/test_lector_de_planilla_excel.py tests/unitarios/test_errores.py tests/unitarios/test_dinero.py -q -p no:cacheprovider` | **63 passed** en 0.28 s |
| `pytest tests/unitarios/test_rompedor_gastos_intento_1.py -q -p no:cacheprovider --tb=short` | **7 failed**, todos por aserción; tres variantes de F1, F2, F3 y dos variantes documentales F4 |
| `alembic heads` | `0033 (head)` |
| `ruff check tests/unitarios/test_rompedor_gastos_intento_1.py` | limpio en la revisión entregada |
| `ruff format --check tests/unitarios/test_rompedor_gastos_intento_1.py` | `1 file already formatted` |
| `mypy tests/unitarios/test_rompedor_gastos_intento_1.py --cache-dir /tmp/mypy-rompedor-6` | `Success: no issues found in 1 source file` |

Conteo propio: **129 casos existentes verdes + 7 reproducciones rojas**. No es el conteo de la suite completa. No repetí la suite completa aportada por el constructor (4641/1 xfailed); es evidencia ajena sobre `838a0b3`, no una observación mía. Los archivos nuevos se revisaron con lint/formato/tipos; los rojos se conservan deliberadamente para el constructor.

### F1 · ALTA, frontera de autorización: los detalles por id omiten el permiso de lectura

Fuentes: `proptech_api/gastos.py`, handlers `ver_gasto`, `ver_nota_de_credito`, `ver_cargo_particular`; `acceso/dominio/permisos.py`, `alcanza` y matriz; KB `03_actores_y_roles.md`, perfil × alcance y restricción de inquilino a ordinarias; spec gastos, requisito de alcance/permisos. Los listados usan `VER_CONFIGURACION_DEL_EDIFICIO`; estos tres detalles sólo usan `alcanza(asignaciones, complejo_id)`. Para el vecino del edificio, `alcanza` sin unidad devuelve verdadero; no filtra tipo, estado ni unidad del cargo.

Reproducción: los tres casos `test_reproduccion_vecino_sin_permiso_no_lee_detalle[...]`, comando E1. La asignación real es vecino inquilino de otra unidad del mismo edificio. La política real confirma que no tiene permiso de lectura de configuración. El helper de listado rechaza 403 con código válido; cada handler de detalle devuelve el dict sin excepción.

Salida relevante:

```text
[gastos] AssertionError: El handler devuelve datos sin permiso: {... 'tipo': 'extraordinario', 'estado': 'borrador'}
[notas-de-credito] AssertionError: El handler devuelve datos sin permiso: {... 'importe': '100.00' ...}
[cargos-particulares] AssertionError: El handler devuelve datos sin permiso: {... 'unidad_id': <otra unidad> ...}
assert None in (403, 404)
```

Los dobles sólo entregan filas y asignaciones que la persistencia podría devolver dentro de un mismo tenant. No reemplazan `alcanza`, `puede` ni el código de los handlers. La falla demostrada es la autorización del handler, no una fuga entre administraciones ni una autenticación saltada. Conocer un UUID no debe conceder permiso. La ruta está registrada en `app.py` por `app.include_router(gastos.router)` y no hay gate extra en el APIRouter; `RutaConIdentidad` agrega identidad, no ese permiso.

JUICIO: bloqueante. Reparar esta frontera exige evaluar su clasificación y aprobación según las reglas de seguridad del proyecto; **no declaré que se hubiera escrito en el libro ni reclassifiqué silenciosamente el change**. No implementé la reparación.

### F2 · ALTA, imputación: PATCH vacío de un aprobado tardío intenta moverlo al período original

Fuente: `gastos/aplicacion/gastos.py::editar_gasto`, construcción de `nuevos`, comparación y UPDATE; D-141; design D8. El guardia de aprobado sólo rechaza si `cambios` contiene campos bloqueados. Con `{}` lo pasa. Después asigna siempre `periodo_de_imputacion = entrada.periodo`, incluso si ya se fijó a otro mes al aprobar.

Reproducción `test_reproduccion_patch_vacio_no_desimputa_gasto_aprobado`: fila aprobada con origen 2026-09-01 e imputación 2026-10-01; `cambios={}`. La función real emite un UPDATE que lleva imputación a septiembre. El test de no-op falla:

```text
AssertionError: [datetime.date(2026, 9, 1)]
assert not [call(<TextClause>, {... 'periodo_de_imputacion': date(2026,9,1) ...})]
```

Usa Session de grabación, lecturas de categoría/grupo simuladas y auditoría simulada. Está demostrado el UPDATE incorrecto emitido por el caso de uso; **no ejecuté ni confirmé ese UPDATE en PostgreSQL**. Falta ampliar a integración con gasto aprobado mediante el puerto de períodos emitidos, PATCH real y consulta posterior. La consecuencia sobre una liquidación real es juicio, porque el adaptador de emisión pertenece al 7. Un PATCH vacío de ese estado ya debe conservarlo hoy. El caso tampoco queda cubierto por el test existente de aprobar dos veces, que recorre otra función.

### F3 · MEDIA, contrato del error: se pierde el formato esperado del CUIT

Fuentes: proveedores spec, alta con CUIT inválido; L-051; `dominio/proveedor.py`, `FORMATO_CUIT`; `aplicacion/errores.py::error_de_validacion`; `proptech_api/gastos.py::manejar_error_de_gastos`.

Reproducción `test_reproduccion_cuit_invalido_conserva_formato_en_error`: crear proveedor con razón social ficticia y CUIT inválido. El validador produce el formato, pero `error_de_validacion` lo descarta y crea `EntradaInvalida('cuit', 'valor inválido')`. El handler usa ese `motivo` como msg del 422.

```text
AssertionError: assert 'once dígitos (0-9 ASCII), sin espacios ni guiones, con dígito verificador válido' in 'valor inválido'
```

Se rechaza la entrada, no se guardó un CUIT inválido. La falla es el texto contractual del error, comprobado sin base porque la validación precede a la transacción. Otros errores de dominio que pasan por la misma conversión pueden perder su explicación; no afirmo haber reproducido cada uno.

### F4 · BAJA, integración documental: quedaron dos referencias del 6 al D-131 del 2d

Fuentes: `tasks.md:274` y `knowledge-base/12_fichas_de_changes.md:947`. Las deudas de las pantallas de HU-A3/HU-A3b siguen diciendo D-131, cuando su decisión es D-140. D-131 ahora es el discriminador 403 del 2d. Esto contradice el criterio explícito del brief de no dejar referencias del 6 con numeración vieja.

Reproducción documental, dos casos `test_reproduccion_deuda_de_pantallas_apunta_a_decision_del_6[...]`:

```text
AssertionError: [... las pantallas de gastos (sin nombre, D-131) ...]
AssertionError: [... Las pantallas de HU-A3/HU-A3b, todavía sin change ni nombre (D-131) ...]
```

No son las menciones históricas de renumeración ni los comentarios que aplican legítimamente D-131 del 2d a los 403. La búsqueda de numeración las distinguió. Este test es validación de contrato documental, no un test runtime. No reescribí ninguna decisión vieja ni la KB.

### E2 · Lente correctitud: trabajo y resultado

- Leí modelos de dominio, los cuatro casos de uso, lectura de aprobados/obligatorios, router y adaptador Excel. Contrasté los requisitos de gastos/notas/cargos/proveedores y tareas.
- CUIT y Dinero tienen rechazos puros ejercitados por los 63 tests de E1, con formato ASCII/completo, rango y precisión. El error visible pierde el formato, F3.
- La pertenencia de categoría/grupo/proveedor se comprueba en la aplicación; el grupo desactivado se rechaza. La selección de proveedores activos existe. No atribuyo a SQL un rechazo de proveedor desactivado que no ejecuté.
- Notas: inspeccioné bloqueo `FOR UPDATE` de gasto antes de sumar acreditado y comparación con tope restante. No ejecuté carrera ni tope contra base; quedan sin verificación independiente en este entorno. Ver sospechas abajo.
- Aprobación y períodos: filtro `estado='aprobado'` presente en lectura y obligatorios, consulta por `periodo_de_imputacion`; PATCH vacío demostró F2. Listar obligatorios usa la marca de categoría y estado aprobado, y sin categorías retorna vacío.
- Cruces de edificio/admin: comprobé el orden alcance/permiso y claves compuestas por inspección. F1 es dentro del mismo edificio/tenant. RLS real y mutantes de cruces no ejecutados.

### E3 · Lente cableado: trabajo y resultado

- Router incluido en la app; excepciones de gastos e importación registradas. Revisados los cuatro 403 propios: todos llevan `codigo: sin_permiso`. Dependencias comunes `identidad_actual` usan `sin_acceso_http` y sesión depende de identidad. No apareció otro 403 propio sin código. F1 expone un camino donde falta rechazo, que un sweep del formato de los 403 no detecta.
- AST de revisiones y `alembic heads`: cadena única `0028 -> 0029 -> 0030 -> 0031 -> 0032 -> 0033`. En `0028` permanece `ver_personal`; vocabulario de `0030` no repite ese evento. `ensayo-roles.sh` apunta dos veces a 0033 y `test_libro_rollback.py` tiene sus tres aserciones en 0033.
- Leí upgrade/downgrade de las cinco migraciones y ayuda RLS: FORCE + USING/WITH CHECK con administración y GRANT explícito a app; FKs compuestas atan gasto/proveedor/cargo/nota al edificio. Downs de tablas quitan FORCE para verificar filas antes de DROP y tienen guardias; 0030 borra sólo su vocabulario; 0031/0033 quitan sus columnas. **Lectura estática no prueba que el rollback con roles reales funcione**. Upgrade/downgrade y ensayo real pendientes, no “limpios”.
- Los 66 tests de fronteras incluyen copias con imports/SQL ilegales de gastos y regresión de ejemplo del 2d. Pasaron. Inspección del SQL del módulo: tablas propias y lecturas permitidas por aplicación, sin INSERT/UPDATE/DELETE en `movimiento`, `obligacion` ni `imputacion`. No encontré activación de la regla de escalada por escrituras del libro. No lo infiero de buscar la subcadena `imputacion`, que aparece legítimamente en el nombre de columna `periodo_de_imputacion`.
- Fixture contador: asignación `contador` con `edificios[0]`, misma administración de las personas, no principal; teardown filtra por administración. Principal lo puede ver según D13, y el ajuste de expectativa es coherente con esa fila. `listar_personal` usa RLS para tenant y la matriz jerárquica para filtrar. No hay evidencia propia de fuga a otro tenant y tampoco prueba real independiente de su ausencia, por Docker. No atribuyo al cambio de expectativa una fuga que no reproduje.

### E4 · Lente verdad de contratos y numeración: trabajo y resultado

- `git diff 2f81682..838a0b3` inspeccionado en la superficie afectada; F4 contradice la afirmación del constructor de que sólo restaban menciones históricas en tasks.
- Comparación byte a byte con `git show 60b3dd5:<archivo>`: `09_decisiones_y_supuestos.md` y `15_lecciones.md` actuales **preservan como prefijo completo los archivos de main**. No se pisaron D-131..D-139 ni L-055..L-062. Las entradas nuevas son D-140/D-141 y L-063/L-064. Se mantiene el número histórico 0032 dentro de L-064, sin reescribir historia.
- La spec MODIFIED de fronteras conserva regla y escenario del ejemplo del 2d, sin volver a exceptuar ejemplo.py. Su mutante existente está dentro de los 66 verdes.
- `openspec --version`: 1.14.3, distinto del fijado 1.13.0. `openspec validate gastos-y-cargos`: válido con warnings de longitud, no probé validación 1.13.0 ni instalé otra versión.
- Fechas git consultadas: ficha KB12 `1384c3e`, 30/10/2026 14:25:09 -03; lecciones `c4c4a25`, 30/10/2026 14:13:29 -03. El drift concreto detectado es F4. No regeneré el mapa de documentación.

## JUICIO

Autor: Codex como rompedor. Comparación: implementación entregada frente al plan, specs, matriz vigente y criterios del brief de integración. Confianza **alta** en los siete rojos observados en las capas indicadas; **media** en las consecuencias de persistencia de F2 y de F1 en despliegue, porque no hubo PostgreSQL/HTTP completo; **sin verificación dinámica independiente** de RLS, carreras y rollback.

El intento devuelve hallazgos al constructor: F1 y F2 bloquean dar este cambio por limpio; F3 incumple contrato explícito y F4 incumple la renumeración pedida. El merge arregla los cuatro códigos de 403 y preserva las fronteras del 2d, pero eso no demuestra que todo acceso que requiere rechazo lo emita. No reparé producción y no emití aprobación de auditor.

## SUPOSICIÓN

1. **Notas contra gasto sin factura**: `crear_nota_de_credito` carga sólo complejo e importe del gasto, sin verificar que tenga las cuatro columnas de factura. La spec exige gasto con factura. Falta reproducción con PostgreSQL y petición real; lo dejo como sospecha, no como quinta falla demostrada.
2. **Reducir en borrador el importe de una factura con notas existentes**: `editar_gasto` no consulta el acumulado acreditado, mientras el tope se comprueba sólo al crear la nota. Podría dejar suma de notas mayor que el gasto. Falta reproducción transaccional real; no se cuenta como falla demostrada.
3. **Excel y contrato de recursos**: design promete límites de bytes/filas y comentarios dicen no usar fórmulas. `archivo.read()` lee completo y el adaptador usa `data_only=True`, sin límite explícito propio ni inspección de fórmulas; tampoco verifica encabezado. No ejercité una planilla grande ni una fórmula con caché, ni deduje un ataque demostrado de esa lectura. Falta fijar límite contractual y probar entrada adversarial acotada. La afirmación de una sola consulta al padrón también difiere del bucle de búsquedas por fila; no medí rendimiento.
4. **Período de factura en lectura de nota**: la spec pide ambos períodos al consultar la nota; el SELECT de nota devuelve su período y gasto_id, y el test existente obtiene el período original por otra llamada. Falta resolver si la lectura compuesta satisface el contrato o debe devolver ambos; no lo cuento como falla demostrada.
5. **Pendientes de entorno**: real PostgreSQL para RLS y alcance, carrera de notas, migraciones desde/hacia 0028 y `ensayo-roles.sh` en Compose aislado. No los reemplaza el verde ajeno de la suite completa. No se pidió ni se hizo push/CI remoto.

## Fuentes leídas

- Instrucciones heredadas y CLAUDE.md; KB `03_actores_y_roles.md`, `09_decisiones_y_supuestos.md`, `12_fichas_de_changes.md`, `15_lecciones.md`; búsquedas acotadas en KB04/06/10/11 y CHANGES.md. Obsidian ausente.
- Proposal, design, tasks y specs de gastos, proveedores, notas, cargos y fronteras del change; las instrucciones del CLI contienen las rutas canónicas del resto.
- `backend/src/proptech_api/{gastos,acceso,errores,app}.py`; `proptech_core/gastos/{dominio,aplicacion,adaptadores}`; matriz de permisos/identidad, auditoría, consultas relevantes de usuarios; migraciones 0028..0033 y ayudas_rls.
- Tests de fronteras, CUIT, Excel, Dinero/errores; selección leída de tests de notas, períodos, proveedores, cargos, rutas, personal, conftest compartido y rollback; ensayo-roles.sh por sus referencias a revisión.
- Diff de integración; commit 6a48a5a; comparación con main `60b3dd5` de decisiones/lecciones.
- Informe original del constructor y LEEME en la etapa final, con contaminación declarada abajo.

## Contaminación por otros informes

Leí el brief con los puntos sugeridos por el constructor desde el inicio. Un `rg` de numeración sobre el directorio del change incluyó accidentalmente fragmentos de `apply-1-constructor.md` antes de terminar mi análisis. Esto incumple el aislamiento temporal estricto pedido: **no declaro contaminación cero**. F1/F2/F3 ya habían surgido de mis lecturas de código; F4 salió de búsquedas propias, y no copié un veredicto ajeno. Después de obtener las reproducciones leí completo `apply-1-constructor.md` para contrastar afirmaciones y límites. No leí informes de auditor/rompedor de otros cambios; sí sus citas dentro de las lecciones. No se reclama independencia sólo por el nombre del agente; ejecutor constructor declarado Claude frente a este ejecutor Codex nativo.

## FALLAS REPRODUCIDAS

1. **F1**: tres handlers devuelven detalles a vecino sin el gate de lectura, incluida unidad ajena/tipo extraordinario (3 rojos unitarios, no HTTP/DB).
2. **F2**: editar con `{}` un aprobado tardío emite UPDATE que vuelve su imputación al período de origen (1 rojo con Session de grabación).
3. **F3**: CUIT inválido pierde el formato esperado en la conversión del error (1 rojo de validación real).
4. **F4**: deuda de pantallas aún referencia D-131 del 2d en tasks y KB12 (2 rojos documentales).

No hay reparación de producción, mutante entregado, commit ni push. El siguiente rol es constructor para correcciones, luego nuevo rompedor sobre su revisión; auditor todavía pendiente.

Cierre del informe UTC: 2026-10-30T18:15:36.065899+00:00

Validación final de entrega: 2026-10-30T18:15:56.054851+00:00. `git diff --check`: exit 0; `git status --short`: sólo LEEME modificado, informe nuevo y test nuevo. Ruff check/format finales limpios. Última corrida de siete reproducciones terminada (mtime del log, UTC): 2026-10-30T18:13:34.555326+00:00, `7 failed in 0.55s`, exit 1, por aserciones esperadas. Salida completa temporal: `/tmp/rompedor-6-reproducciones-final.log`; evidencia relevante preservada arriba. La hora de las dos corridas verdes anteriores no se capturó individualmente, limitación declarada, y no se repitieron sobre el mismo código.
