# Revisión del plan · propose · intento 1

- Rol: plan-reviewer.
- Ejecutor declarado: Codex vía plugin, ejecución directa de esta sesión, sin anidar `codex exec`. Modelo exacto no expuesto por la sesión.
- Revisión revisada: `main`, `533a44027d16819fd774c404372b5e5dbd39917d`, más los artefactos sin commitear de `intereses-saldo-inicial-y-moroso`.
- Fecha: 30/10/2026, Argentina, UTC-03.
- Alcance: revisión documental y estática de viabilidad. Única escritura autorizada: este informe. Sin tests, build, migraciones ejecutadas ni commit. No se editaron artefactos, índices de informes, memoria ni Obsidian.

## Fuentes leídas

Rutas de artefactos relativas a `openspec/changes/intereses-saldo-inicial-y-moroso/`:

- `proposal.md:1-155`, `design.md:1-279`, `tasks.md:1-228`.
- `specs/intereses-por-mora/spec.md:1-207`, `specs/saldo-inicial/spec.md:1-174`, `specs/situacion-de-cobranza/spec.md:1-151`, `specs/libro-de-movimientos/spec.md:1-41`, `specs/reparto-de-montos/spec.md:1-26`.
- `informes/propose-1-planner.md:1-119`, al final de la investigación independiente, ver Contaminación.

Fuentes del repositorio:

- `CLAUDE.md`, instrucciones completas; instrucciones AGENTS aportadas en el encargo. No hay tabla de ejecutores propia que desplace la elección explícita del humano para esta revisión.
- `obsidian.md:1-65`, symlink a la nota existente. No se actualizó por la restricción de una sola escritura.
- `knowledge-base/05_reglas_de_negocio.md:173-217,340-409,792-825`, centrado en R03, R09, R30 y R20.
- `knowledge-base/09_decisiones_y_supuestos.md:2020-2046,2551-2598,2926-2953`: D-113, D-130 y D-143.
- `knowledge-base/12_fichas_de_changes.md:677-740,790-800,848-856`.
- `CHANGES.md:574-618`.
- `openspec/exploraciones/2026-10-22-motor-de-cuenta-corriente.md:200-233,399-445`.
- `knowledge-base/15_lecciones.md`: títulos L-001 a L-067; texto de L-012/L-013 (127-152), L-016 a L-020 (177-251), L-031 (416-425), L-034 a L-036 (461-520), L-048/L-049 (697-732), L-054/L-055 (826-871), L-061 (959-968), L-064 (1001-1035).
- `backend/src/proptech_core/cuenta_corriente/aplicacion/emisiones.py:1-285`, `lecturas.py:1-188`, `cuentas.py:1-155`, `correcciones.py:100-285`, `dominio/estado.py:1-223`.
- `backend/src/proptech_core/compartido/reparto.py:1-45`, `tablas_protegidas.py:1-42` y búsqueda de sus entradas; `roles.py:895-945` y búsqueda de transferencia de propiedad, dependencias y verificación.
- `backend/src/proptech_core/complejos/aplicacion/lectura.py:200-245`.
- `backend/migraciones/versions/0023_libro_de_movimientos.py:1-260`, `0033_categoria_obligatoria_mensual.py:1-25`, `backend/migraciones/ayudas_rls.py:1-50`. Revisiones y predecesoras de todas las migraciones, extraídas por AST, sin ejecutarlas.
- `backend/tests/integracion/test_cc_anulacion_candado.py:1-210`, `test_cc_correcciones.py:1-90,110-145`, `_cuenta_corriente.py:1-145`, `test_cc_replay_carrera.py:225-325`, `test_cc_auditoria_api.py:25-85`, `test_cc_concurrencia.py:20-62`, `test_cc_emisiones.py:20-60`, `test_cc_lecturas.py:20-44`, `test_libro_rollback.py:35-90`.
- Búsqueda de llamadas a `registrar_emision`, revisión `0033`, índices y restricciones en `backend/src`, `backend/tests` y la migración `0023`; listado de archivos de cuenta corriente y migraciones mediante `rg --files`.

## EVIDENCIA

Todos los resultados corresponden a la revisión indicada en el encabezado. Las primeras llamadas no capturaron reloj: se declara esa falta y no se inventa su hora. La evidencia extensa de lecturas está en la transcripción de herramientas de la sesión; este informe conserva rangos, comandos y resultados relevantes, sin crear otro archivo.

| Comando o lectura ejecutada | Hora local del 30/10/2026 | Salida relevante |
|---|---|---|
| `pwd`; `git status --short`; `git rev-parse HEAD`; `openspec list --json` | No capturada, antes de 18:12:29 | Repo esperado; sólo `?? openspec/changes/intereses-saldo-inicial-y-moroso/`; HEAD `533a44027d16819fd774c404372b5e5dbd39917d`; 0/23 tareas, `in-progress` |
| `openspec status --change intereses-saldo-inicial-y-moroso --json` | No capturada, antes de 18:12:29 | Cuatro artefactos `done`, `isPlanningComplete: true`. Esto informa estado de artefactos, no aprobación humana ni implementación terminada |
| `openspec instructions apply --change intereses-saldo-inicial-y-moroso --json` | No capturada, antes de 18:12:29 | `state: ready`, 23 pendientes; reglas de TDD y firma CRITICAL. No se ejecutó apply |
| `python - <<'PY' ...` para lectura inicial | No capturada | `/bin/bash: python: command not found`, salida 127. Se repitieron las lecturas con `python3`; no se interpreta este fallo como validación |
| `python3` con `Path.read_text().splitlines()` y numeración, en las rutas y rangos de Fuentes leídas | Lecturas anteriores a 18:12:29; lotes adicionales 18:12:29, 18:12:56 y 18:13:11 | Contratos, algoritmo y código contrastados; resultados concretos en PR-01 a PR-09. Las salidas truncadas se completaron con lecturas focalizadas, especialmente interés 139-207, ficha 677-691 y D-143 |
| `rg --files backend/src/proptech_core/cuenta_corriente backend/migraciones/versions` | No capturada, antes de 18:12:29 | Existen los archivos actuales citados; los módulos nuevos del 4c y `0034` todavía son plan |
| `rg -n 'registrar_emision\(|uq_mov_interes|ck_obligacion_importes|aislar_por_administracion|0033' backend/src backend/tests backend/migraciones/versions/0023*` | No capturada, antes de 18:12:29 | Único en `0023:205-206`; llamadas sólo en tests; tres expectativas `0033` en `test_libro_rollback.py:60,86,129` |
| `date -Iseconds`; `openspec validate intereses-saldo-inicial-y-moroso --strict` | 18:12:29-03:00 | `Change 'intereses-saldo-inicial-y-moroso' is valid`, salida 0 |
| `rg -n '^##|^###' knowledge-base/15_lecciones.md` | 18:12:29-03:00 | Títulos L-001 a L-067, incluidos libro, plata, mutantes, candados y evidencia |
| `rg -n 'def contra|def sembrar|configuracion|TABLAS_DE_SOLO_AGREGAR|FORCE ROW|OWNER TO'` sobre `_cuenta_corriente.py`, `test_cc_correcciones.py`, `roles.py`, `tablas_protegidas.py` | 18:12:29-03:00 | Helper `contra` existe en línea 114; `sembrar` en 42; transferencia y revocaciones en `roles.py:898-938` |
| `python3`: enumeración de archivos `.py` que contienen `registrar_emision(` fuera de su definición | 18:12:56-03:00 | Ocho consumidores directos de tests, listados en la sección Consumidores. No apareció consumidor de producción |
| `python3`: recálculo con `Decimal`, fechas y `ROUND_HALF_UP`, sin importar producción | 18:12:56-03:00 | 20 días: 2000.00; 31: 3100.00; 6: 600.00; 33: 3300.00; 19: 1900.00; 51: 5100.00, todos sobre 100000 al 3%; 80000 × 16: 1280.00; 85000 × 16: 1360.00; 50000 × 16: 800.00; 62.50 × 2: 0.13 |
| `date -Iseconds`; lectura final de `informes/propose-1-planner.md` con `python3` | 18:13:11-03:00 | Informe leído después de comparar fuentes, índice, contratos y escenarios. No reemplaza evidencia propia |
| `git branch --show-current`; `git diff --name-only`; `rg -c '^- \[ \]' .../tasks.md` | 18:13:27-03:00 | `main`; diff de archivos rastreados vacío; 23 tareas |
| `python3`: `ast.parse` de cada migración y extracción literal de `revision`/`down_revision` | 18:13:27-03:00 | Cadena única `0001` a `0033`, `0033` depende de `0032`; `0034` es un número viable. No se consultó una base desplegada |
| `python3`: oráculo decimal de dos tramos de 1 día, bases 64 y 63 al 3%/30 | 18:13:27-03:00 | Exactos `0.064`, `0.063`; redondeo único `0.13`, por tramo `0.12` |

Los montos publicados son aritméticamente coherentes bajo E2/E3. Pago parcial: 10 × 100 + 10 × 60 = $1.600. Cambio al 6%: 31 × 200 = $6.200. Total de cobranza: 80.000 + 4.000 + 85.000 = $169.000; deuda y crédito: 10.000 - 3.000 = $7.000. Esto es recálculo del plan, no ejecución del comportamiento futuro.

## Hallazgos

### PR-01 · La ausencia de configuración devuelve `None`, no `NoEncontrado`

- Fuente: `tasks.md:150-153`, `design.md:72-74`; `backend/src/proptech_core/complejos/aplicacion/lectura.py:213-227`.
- Observación: la tarea dice traducir `NoEncontrado` al faltar versión. La función real devuelve `None` si existe el edificio pero no hay versión vigente. Sólo lanza `NoEncontrado` si no existe el edificio. Seguir literalmente la tarea puede dejar pasar el caso o producir un error de acceso a `None`, en lugar del conflicto exigido.
- Por qué importa: son dos resultados distintos, con semántica de campo y de tenant diferente. El diseño no debe convertir un edificio ajeno en un conflicto de configuración.
- Disposición: **CORREGIR**. Especificar `None → Conflicto("configuracion")`, conservar no encontrado para edificio invisible, y probar ambos caminos, incluyendo versión únicamente futura y libro sin escrituras.

### PR-02 · Anular no bloquea las cuentas que sólo recibieron interés en la emisión

- Fuente: `design.md:69-75,235`; interés, escenario `specs/intereses-por-mora/spec.md:25-28`; `backend/src/proptech_core/cuenta_corriente/aplicacion/emisiones.py:257-265`; `correcciones.py:167-189`.
- Observación: E10 permite que octubre registre interés para U2 aunque sólo cree obligación de octubre para U1. `anular_emision` descubre sus cuentas exclusivamente desde `obligacion WHERE emision_id=:id`, por lo que bloquea U1 y no U2. Un contra-asiento del interés de U2 toma U2 y comprueba la emisión bajo ese candado, pero la anulación puede confirmarse sin esperarlo. El plan modifica el alcance de emitir sin modificar el de anular.
- Secuencia de análisis: registrar interés de septiembre de U2 en octubre; corrección de ese interés pasa `_anulada`; otra conexión anula octubre tomando sólo U1; la corrección escribe después sobre el interés ya excluido. Es una intercalación deducida del código y del alcance futuro, no un fallo runtime reproducido.
- Por qué importa: invalida la garantía de anulación/corrección bajo el mismo candado y deja efectos de la emisión fuera de su conjunto protegido. Los tests RF-02 propuestos sólo usan obligaciones de la propia emisión.
- Disposición: **BLOQUEANTE** para construir ese diseño. Incluir unión de cuentas de obligaciones y movimientos generados por la emisión, con un único pedido ordenado, y escenarios de anulación frente a corrección/lectura de U2 sin obligación nueva. Revisar también el replay cuando deba leer los intereses de estas cuentas. No alcanza con remitirlo al 7: el contrato nuevo nace en el 4c.

### PR-03 · “Mes entero” omite el primer tramo de una obligación migrada

- Fuente: `design.md:88-101`; `specs/saldo-inicial/spec.md:72-83`; `tasks.md:121-124,180-182`.
- Observación: el inicio natural migrado pasa al día posterior a la migración, pero los bloques de mes entero siguen anclados al vencimiento original y sólo se cobran si su inicio cae en el tramo. Con vencimiento 10/08, migración 15/10 y corte 31/10, los inicios son 11/08, 10/09, 10/10 y 09/11. Ninguno cae entre 16/10 y 31/10: el algoritmo registra cero aunque hay capital migrado impago después de la migración. Ese intervalo no se recupera como primer bloque en el corte siguiente.
- Por qué importa: la promesa de R09 de generar interés desde la migración no queda definida para una de las dos modalidades admitidas. Las tareas sólo triangulan el saldo migrado proporcional.
- Disposición: **BLOQUEANTE**. Completar E3/E9 con la convención para bloques migrados, conservar la prohibición de cobrar antes de la migración y agregar escenario con/sin interés importado. La elección de anclaje le corresponde al humano; no la decido acá.

### PR-04 · La consulta “a una fecha” usa residuales actuales sin definir el corte histórico

- Fuente: `design.md:176-182`; `specs/situacion-de-cobranza/spec.md:129-141`; `lecturas.py:44-64,145-150`; `estado.py:144-194`.
- Observación: la foto actual incluye todos los movimientos e imputaciones y todos los eventos de anulación, sin filtro de fecha. `calcular_estado` tampoco recibe fecha. El diseño nuevo pasa `fecha` a la clasificación y a la configuración, pero no define cómo reconstruir lo impago a esa fecha. Dos obligaciones impagas el 30/09 y pagadas el 20/10 aparecerían canceladas si se consulta el 30/09 después del pago usando esa foto.
- Por qué importa: “situación a fecha” puede significar historia efectiva o clasificación del saldo actual con una fecha de vencimiento elegida. Son contratos observables distintos para los consumidores 8/10a/10b.
- Disposición: **CORREGIR** antes de firma. Definir el significado, incluyendo fechas valor, registro, imputaciones y anulación posterior. Si promete historia, diseñar y probar esa reconstrucción. Si sólo promete saldo actual, acotar explícitamente la API y los escenarios para no ofrecer historia que no calcula.

### PR-05 · El replay promete un saldo anterior estable que el libro no conserva

- Fuente: `specs/intereses-por-mora/spec.md:191-207`; `design.md:21-24`; `emisiones.py:112-121`; `estado.py:91-97`.
- Observación: la spec exige “el mismo saldo anterior”. El replay actual vuelve a calcularlo desde el estado actual; su comentario declara que el libro no lo persiste y que lo guardará el 7. Ejemplo: octubre devuelve $102.000 de septiembre con interés; después se registra un crédito que cancela septiembre; repetir octubre vuelve a leer y ya no devuelve $102.000. La tarea 5.3 sólo pide replay sin escrituras y no introduce persistencia ni define el replay después de otros movimientos.
- Por qué importa: se introduce una garantía incompatible con el mecanismo elegido y con el contrato previo. Leer los débitos originales permite devolver los mismos intereses registrados, pero no recupera automáticamente la foto original del saldo.
- Disposición: **BLOQUEANTE** para prometer identidad del resultado. Separar intereses registrados estables de saldo recalculado, o diseñar almacenamiento de la foto dentro del alcance firmado. Agregar replay después de pago y después de anulación, con expectativas explícitas; no inferirlas del replay inmediato.

### PR-06 · Los mutantes de aislamiento no discriminan las defensas que dicen probar

- Fuente: `tasks.md:67-73,205-207`; `backend/migraciones/ayudas_rls.py:41-48`; `lecturas.py:38-41`; `roles.py:898-918`; lecciones L-034 y L-036.
- Observación: quitar sólo `FORCE ROW LEVEL SECURITY` no hace que `proptech_app`, que no es dueño tras `roles despues`, vea filas ajenas: `ENABLE` y la política siguen filtrando. Análogamente, omitir sólo el filtro de tenant del SQL de cobranza no vence la RLS correcta. Las tareas prometen rojo de aislamiento por esas mutaciones sin especificar una preparación que elimine la defensa que las tapa.
- Por qué importa: el plan CRITICAL exige mutantes que fallen en la aserción específica, no en setup ni en otra garantía. El diseño de propiedad y sólo agregar es viable con el registro y `roles despues`, pero estos dos controles no prueban lo declarado.
- Disposición: **CORREGIR**. Para FORCE, probar como dueño sin BYPASSRLS con filas de ambos tenants y aislamiento definido, o complementar con catálogo y sonda adecuada. Para SQL/RLS, separar cada defensa y declarar qué se desactiva en el ensayo controlado, con restauración, sin alterar login. Extender la matriz de mutantes a cada aserción de seguridad nueva, no declarar que un solo mutante cubre tres tablas y todas las FK.

### PR-07 · El contrato para Excel no define la agrupación de conceptos del mismo período

- Fuente: R09 en `knowledge-base/05_reglas_de_negocio.md:342-344,356-370`; `design.md:142-156,161-163`; `specs/saldo-inicial/spec.md:32-42,101-110`; `0023_libro_de_movimientos.py:199-200`.
- Observación: R09 describe hoja con unidad, concepto y período. El contrato nuevo ofrece renglones ya desglosados y dice que cada uno genera obligación. Dos filas legítimas de la misma unidad y período, una ordinaria y otra extraordinaria, comparten `(administracion_id, operacion_id, cuenta_id, periodo)` y chocan con el único existente si se pasan literalmente. Si el 5 debe agruparlas, el campo singular `fila` no alcanza para expresar el origen múltiple en el contrato tal como está escrito, aunque la tabla de origen podría admitir varias referencias.
- Por qué importa: el primer consumidor necesita saber si recibe filas de Excel o períodos normalizados y cómo preserva todos los orígenes. No es necesario implementar Excel en el 4c, sí entregar un contrato utilizable.
- Disposición: **CORREGIR**. Definir responsable de agrupar, claves de duplicado, manejo de varios vencimientos y referencias múltiples de origen. Agregar ejemplo con dos conceptos del mismo período y dos filas de archivo. Mantener explícita la limitación E11 hasta la decisión humana.

### PR-08 · El escenario de redondeo no mata el mutante de redondear por tramo

- Fuente: `specs/intereses-por-mora/spec.md:144-160`; `tasks.md:109-115,129-134`.
- Observación: $62,50 durante dos días sin cambio de base genera un único tramo de $0,125. Redondear cada tramo y sumar da también $0,13, por lo que ese escenario no mata el mutante nombrado. El pago parcial de $100.000/$60.000 produce tramos de importes enteros y tampoco discrimina. La propiedad generativa puede encontrar otro caso, pero no se especifica uno que garantice este rojo.
- Por qué importa: el ejemplo prueba redondeo medio hacia arriba, pero no el momento del redondeo que pretende cubrir la tarea CRITICAL.
- Disposición: **CORREGIR**. Agregar un ejemplo de al menos dos tramos con diferencia demostrable: un día sobre $64 y otro sobre $63 al 3%/30 dan $0,064 + $0,063 = $0,127, redondeado $0,13; por tramo da $0,12. Nombrar la imputación y fechas que generan esas bases. Exigir rojo de ese test con el mutante, además de las propiedades.

### PR-09 · E6 vuelve a consultar una decisión cerrada y hay referencias de tareas desactualizadas

- Fuente: `proposal.md:67-74,122-123`; `design.md:231,241-244,259-260`; `tasks.md:61-84,150-162`; D-143 en `knowledge-base/09_decisiones_y_supuestos.md:2938-2952`.
- Observación: E6 presenta `>=` como una elección abierta frente a `>`, pero D-143 ya decidió “$500 o más” y el encargo prohíbe reabrirlo. Sólo corresponde corregir el texto rezagado de R20. Además, design remite a 2.3, que no existe, para el cambio de contrato, y a 2.2 para estructurales, que están en 2.1; proposal menciona 8.2, inexistente, al citar cierre.
- Por qué importa: la firma no debe aparentar una decisión nueva ni dejar al constructor persiguiendo tareas equivocadas.
- Disposición: **MENOR**. Presentar E6 como ratificación de cumplimiento de D-143, sin alternativa vigente, y corregir referencias a 2.1, 2.2, 5.4 y 8.1 según corresponda.

## Comprobaciones de cobertura y viabilidad

### Tests mínimos de reglas

| Regla y mínimo | Escenario/tarea del plan | Evaluación |
|---|---|---|
| R03: pago parcial, gracia y pago después de gracia | Pago parcial, Pago dentro/un día después, 4.1/4.2 | Cubiertos en plan |
| R03: tasa entre períodos y no capitalización | Cambio de tasa, Nunca interés sobre interés, 4.1/5.2 | Cubiertos; corregir el contrato de ausencia de versión, PR-01 |
| R03: mes entero con un día y corte de período | Un día/segundo bloque, Emitir a mitad de mes, 4.3/5.1 | Cubiertos para obligación emitida; falta composición con migración, PR-03 |
| R09: interés traído tal cual y desde migración | Interés importado, Primer interés después de migrar, 6.2/6.3 | Cubiertos en proporcional; PR-03 y E11 limitan alcance |
| R09: detalle y total único | Dos períodos viejos, Total único, 6.2 | Cubiertos para períodos distintos; falta contrato de filas por concepto, PR-07 |
| R09: saldo negativo como crédito | Unidad con saldo a favor, Deuda y crédito, 6.2 | Contrato usa importe positivo en canal crédito y rechaza importes negativos. Es viable si el 5 normaliza el signo del Excel; debe documentarse esa responsabilidad |
| R09: suma contra archivo, diferencias opuestas por unidad, borrador sin movimientos, aceptación registrada | Fuera de alcance en proposal 55-56; retorna totales en D5 | Son obligaciones del 5, sin escenario/tarea de ejecución en este 4c. No se declara cobertura completa de R09. El contrato debe preservar datos por unidad/origen para que el 5 las pruebe |
| R09: importador cerrado rechaza segunda importación | Edificio sin saldos previos, Segunda carga, replay posterior a confirmar, 6.4 | Falta caso explícito de operación nueva en estado `confirmada` sin carga previa. Agregar como triangulación de 6.4; replay permitido no equivale a nueva importación |
| R30: bajo umbral no reclama ni cuenta; igual/encima normal | Saldo chico, Dos saldos chicos, Justo en umbral, El umbral no frena interés, 7.1/7.2 | Clasificación cubierta; aviso real queda para 10a. No reabrir `>=` |
| R20: una/dos vencidas, parcial y reversión | Escenarios homónimos, Deshacer un pago vuelve a marcar, 7.1/7.2 | Cubiertos mediante contra-asiento existente; R18 real corresponde al 8 |
| R20: migrada con dos períodos o total único | Migrada con dos períodos/total único, 7.2 | Cubiertos bajo E7/E8, sujeto al significado de fecha de PR-04 |

### RF-01 y RF-02

La aserción nueva de RF-01 sí tiene capacidad estática de matar el mutante de `emisiones.py:224`: con dos cuentas, la última sentencia del mutante solicita una, mientras la propuesta exige el conjunto exacto de dos. Debe instrumentarse sobre SQL ejecutado y parámetros reales, considerando la compilación de `:ids`; no comparar literalmente una plantilla sin confirmar su representación. En replay, la lectura hoy está en **117**, mientras **116** bloquea cuentas. Corregir la localización del mutante en las tareas. No se ejecutó mutante ni se afirma rojo observado. La carrera vieja sigue sin discriminar una foto de varias por los candados, tal como documenta la ficha 853.

RF-02 tiene helper `contra(...)` real en `test_cc_correcciones.py:114-133`; la parametrización propuesta es viable. Debe crear el crédito original antes de instalar la pausa de `_anulada`, para que la carrera observe el contra-asiento asignado y no su preparación. PR-02 exige además cubrir el alcance nuevo de intereses.

### Consumidores de `registrar_emision`

La búsqueda propia encontró ocho archivos con llamadas directas, todos de integración:

- `test_cc_lecturas.py:35,96`.
- `test_cc_emisiones.py:50,291`.
- `test_cc_creditos.py:38,189,214,324`.
- `test_cc_correcciones.py:42,463`.
- `test_cc_replay_carrera.py:250,305`.
- `test_cc_concurrencia.py:50`.
- `test_cc_anulacion_candado.py:110`.
- `test_cc_auditoria_api.py:59`.

El plan no enumera estos consumidores uno por uno, aunque 5.4 los selecciona por nombre. `sembrar` alcanza a las fixtures `Mundo` revisadas; `test_cc_auditoria_api` usa `ApiEdificio`, no esa semilla. Su emisión actual tiene vencimiento de octubre y corte septiembre, así que no está demostrado que necesite versión bajo el contrato condicional propuesto. No afirmo ocho archivos rotos ni una falla de esa fixture. Agregar este inventario a 5.4 y discriminar quién requiere adaptación al activar deuda anterior. Ningún consumidor de producción apareció en la búsqueda de llamadas; 5 y 7 son futuros. Los conteos de 74/21/7 del planner no son conteos de tests y no se certifican acá.

### Migración, propiedad y alcance

`0034` es viable después de `0033`. D10 propone RLS forzada mediante un helper que efectivamente ejecuta ENABLE y FORCE. Registrar las tres tablas en `TABLAS_DE_SOLO_AGREGAR` activa transferencia de dueño al arranque, transferencia de funciones y revocación de UPDATE/DELETE/TRUNCATE de la app en el mecanismo actual. Es coherente con la restricción D-115 descrita por el proyecto y con no alterar `0023`; no se consultó una migración nueva que aún no existe. La bajada exige el ciclo real de devolución de propiedad y tablas vacías, no sólo `alembic downgrade -1` aislado.

D4 sólo dice FK por administración a movimiento y obligación; completar en el diseño las columnas para mantener también cuenta/edificio y coherencia del movimiento de interés referenciado. Las claves compuestas existentes de `0023:128-134,174-179` ofrecen soporte. Las FK de tenant no prueban por sí solas que dos referencias del mismo tenant sean de la misma cuenta. Incluir esos cruces en los CHECK/FK y mutantes de la tarea 2.1. Es una precisión pendiente del esquema, no un defecto demostrado de una migración ejecutada.

Las 23 tareas tienen justificación de tamaño y grupos secuenciales razonables. No recomiendo partir el cambio sólo por superar una cifra orientativa. El freno es la coherencia de contratos y escenarios anteriores.

## Elecciones para el humano

No completo ni juzgo como ausente la firma. Estas evaluaciones revisan el planteo, no deciden por quien firma.

| Punto | Coherencia de la opción propuesta y calidad de la pregunta |
|---|---|
| E1 | **Choque confirmado estáticamente**: `uq_mov_interes` incluye administración, obligación y corte, sin `emision_id` ni estado. Anular agrega evento; no borra el movimiento. Repetir interés de la obligación vieja al mismo corte violaría el único. El diferimiento evita ese choque y está expuesto como cambio de comportamiento, no como decisión ya tomada. La pregunta es pertinente. “La plata no se pierde” exige precisar que habrá un corte posterior y cuál tasa rige entonces: con E4 puede cambiar el importe frente a cobrar al corte original. No prometer equivalencia monetaria incondicional. PR-02 y PR-05 siguen abiertos aunque se firme E1 |
| E2 | Coherente con “al emitir la liquidación siguiente” de R03 y el ejemplo de D-143. La pregunta es clara y los montos cierran; el corte no es una prueba del Excel de Alberto |
| E3 | /30 y bloques de 30 días son elecciones explícitas, no hechos fijados en D-113. Se pueden someter al humano sin convertir P57-P60 en bloqueantes. Falta formular el caso migrado de PR-03 y su interacción con gracia y cambio de forma |
| E6 | El valor propuesto es correcto por R30/D-143. La pregunta no debe volver a ofrecer `>` como alternativa abierta, ver PR-09 |
| E7 | Separar sólo intereses es coherente con la categoría de deuda de intereses que el plan atribuye a D-109.4. Que un período sólo con interés deje de contar cuando hay otro con capital es una elección adicional frente al texto amplio de R20. Está bien preguntar por ese caso mixto y conservar el resultado explícito; no presentarlo como deducción inevitable de D-143 |
| E11 | El rechazo es técnicamente coherente con `ck_obligacion_importes:82-83`, que exige capital positivo. No es una garantía de que el Excel real nunca tenga esa fila. La pregunta debe hacer visible que excluye una entrada plausible de migración y pedir aceptación de esa limitación para el contrato del 5, sin sumar intereses a otro período de oficio |
| PA-1 | La pregunta identifica un límite real: las correcciones existentes ofrecen crédito o contra-asiento, no débito libre; una obligación de saldo inicial no es un movimiento que se pueda contra-asentar para subir su capital. Es válido separarla del código del 4c si queda como decisión pendiente antes del camino afectado del 5. No afirmar cumplimiento completo de la corrección posconfirmación de R09 ni habilitar el 5 ignorando ese límite |

## JUICIO

Autor: Codex, plan-reviewer. Comparé los artefactos reales y sus escenarios con las secciones de KB indicadas, la cadena estática de migraciones y los consumidores actuales del libro. Confianza alta en PR-01, PR-02, PR-03, PR-05, PR-06, PR-08 y PR-09 como observaciones de contrato/código o aritmética; media-alta en PR-04 y PR-07, donde una aclaración explícita de semántica puede resolver parte del hallazgo sin ampliar implementación.

El plan es revisable y OpenSpec lo acepta estructuralmente, pero tiene contratos incompatibles con piezas existentes y combinaciones financieras sin respuesta. La firma humana debe recibir un plan corregido, no resolver además las contradicciones técnicas por omisión. D-143 se conserva; no se reabren P53/P54 ni se exige resolver P57-P60.

## SUPOSICIÓN

- No se corrió suite, test aislado, mutante, Docker, PostgreSQL ni migración. Las intercalaciones y resultados futuros se analizaron; no son fallos runtime reproducidos.
- No se verificaron rendimiento, EXPLAIN, tiempos de espera ni los “milisegundos” de design 247. Ese tiempo es una expectativa del planner, sin medición aquí.
- `0033` se confirmó como cabeza de archivos, no como revisión de una base levantada.
- No se consultaron leyes ni fuentes externas: se revisó el cumplimiento del contrato suministrado de interés simple, sin emitir asesoramiento jurídico.
- No se inspeccionó un Excel real ni se probó que el formato futuro tenga un concepto o varios por período. PR-07 exige definir la transformación que el contrato necesita, no presume datos de un edificio real.
- No se recuperó Engram ni se leyeron informes hermanos/regresión para formar acuerdo. La autoridad usada fue el repo y este encargo. No se actualizó memoria por la restricción de única escritura.
- No se hizo auditoría exhaustiva de todos los tests ni de la KB completa. Los rangos anteriores delimitan lo leído. No se compararon fechas de autor de cada documento con todo el archivo histórico; eso no sustenta este veredicto ni habilita reescritura de la KB.
- El entorno de sesión tiene permisos de escritura más amplios que un único archivo; no afirmo que exista un sandbox técnico por ruta única. Se respetó el límite operativo del encargo escribiendo sólo este informe.

## Contaminación

Leí `informes/propose-1-planner.md:1-119` a las **18:13:11-03:00**, después de la investigación independiente de artefactos, fuentes y código y del recálculo de montos. Es posible contaminación al redactar la evaluación final de E1/E6/E11/PA-1 y del alcance de las fixtures. Sus conclusiones no se usan como EVIDENCIA propia: el índice, las devoluciones de configuración, el candado de anulación, el estado y los importes se verificaron directamente. No leí originales de otros revisores ni informes de regresión; sus citas dentro de KB y de la sección de lecciones sí forman parte de las fuentes declaradas.

## Veredicto

**VUELVE AL PLANNER**.

Lo justifican PR-02, PR-03 y PR-05, **BLOQUEANTES**, y las correcciones PR-01, PR-04, PR-06, PR-07 y PR-08 antes de llevar el plan a firma. PR-09 es MENOR y conviene resolverlo en la misma revisión. No se señala como hallazgo la firma humana pendiente.

### Control del archivo entregado

EVIDENCIA, 2026-10-30T18:16:35-03:00: `python3` leyó este informe, verificó las secciones obligatorias, nueve hallazgos y ausencia de em dashes; `git status --short` devolvió `?? openspec/changes/intereses-saldo-inicial-y-moroso/`; `git diff --name-only` salió vacío. Se corrigió únicamente una etiqueta de la tabla de elecciones dentro de este mismo informe. Resultado: contrato de formato válido, sin cambios rastreados. No es una prueba de comportamiento del 4c.
