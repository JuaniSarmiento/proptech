# verify · intento 2 · ROMPEDOR · gastos-y-cargos (6, MEDIUM)

- Autor: **Codex rompedor**, ejecutor efectivo **subagente nativo Codex**, familia OpenAI/GPT, modelo concreto no verificado. El brief solicitaba `codex:codex-rescue`; este informe no acredita una ejecución de ese plugin. El orquestador despachó explícitamente al ejecutor nativo y ordenó registrar la sustitución. No ejecuté un Codex anidado.
- Fecha: 30/10/2026. HEAD verificado: `63582e4f127a7fe241c64366c6da6968046f6ffe`, rama de trabajo indicada `revision-6`. Código `58f2d76`. Árbol inicial limpio.
- Recibido: brief completo del usuario (F1-F4, S1-S5, tres lentes, consumidores, revisión, evidencia y rutas); instrucciones acotadas del orquestador. Revisión quieta de `6ec260e..f1f165d`, sin arreglos de producción, commits ni push. No actualicé tasks por el límite explícito de escritura: este encabezado y el dispatch de la sesión documentan intento, ejecutor, revisión y próximo paso.
- **Resultado: CON FALLA REPRODUCIDA en aplicación (3 rojos por aserción). Integración pendiente. No habilita cierre ni reemplaza auditoría.**

## EVIDENCIA

### E0 · Estado, alcance y procedencia

`openspec list --json`, `openspec status --change gastos-y-cargos --json` y `openspec instructions apply --change gastos-y-cargos --json`: change presente, artefactos done, 63/63 tareas, all_done. Esto describe tareas, no aprobación de verificación.

Leí instrucciones locales y las lecciones numeradas `knowledge-base/15_lecciones.md` (la salida extensa se truncó parcialmente; no afirmo lectura íntegra de las líneas no visibles). Aplicadas L-003/004/005/007/008/019/021/051 y las advertencias de aislamiento y conteo. `obsidian.md` ausente en este worktree, Engram no disponible. No alteré notas externas. No hice build. Docker se da por no disponible según el brief; no ejecuté integración/RLS ni reclamé probarlos con dobles.

`git diff 58f2d76..63582e4 --stat`: sólo KB12, tasks, apply-2 y LEEME. La evidencia histórica aportada de `58f2d76` (4665 passed, 1 xfailed; ruff/formato/mypy, head 0033) sigue siendo reutilizable para el código sin cambios; es evidencia ajena, no una corrida independiente mía ni prueba de ausencia del defecto nuevo.

### E1 · Comandos y conteo propio

Comandos desde el worktree, prefijo `UV_CACHE_DIR=/tmp/uv-rompedor-6 uv run --no-sync --directory backend`. Ventana de ejecución: 30/10/2026, antes de la marca UTC observada `2026-10-30T18:48:01Z`; los checks de colección/formato posteriores ocurrieron en la misma sesión. No capturé cada hora individual.

| Comando (tras el prefijo) | Resultado observado |
|---|---|
| `pytest tests/unitarios/test_rompedor_gastos_intento_2.py tests/unitarios/test_cuit.py tests/unitarios/test_lector_de_planilla_excel.py tests/unitarios/test_errores.py tests/unitarios/test_dinero.py tests/unitarios/acceso/test_permisos.py tests/unitarios/test_fronteras_de_modulos.py -q -p no:cacheprovider --tb=short` | **3 failed, 1238 passed**, 4.32 s, archivo nuevo entonces con 31 casos |
| `pytest tests/unitarios/test_rompedor_gastos_intento_2.py -q -p no:cacheprovider --tb=short` (archivo final, cuatro casos adicionales) | **3 failed, 32 passed**, 0.54 s |
| `ruff check tests/unitarios/test_rompedor_gastos_intento_2.py tests/integracion/test_rompedor_gastos_intento_2.py` | All checks passed! |
| `ruff format --check tests/unitarios/test_rompedor_gastos_intento_2.py tests/integracion/test_rompedor_gastos_intento_2.py` | 2 files already formatted |
| `mypy tests/unitarios/test_rompedor_gastos_intento_2.py tests/integracion/test_rompedor_gastos_intento_2.py --cache-dir /tmp/mypy-rompedor-6-v2` | Success: no issues found in 2 source files |
| `pytest tests/integracion/test_rompedor_gastos_intento_2.py --collect-only -q -p no:cacheprovider` | **2 tests collected**, no ejecución de sus cuerpos |

Conteo independiente sin sumar repetidos: **1210 casos existentes verdes, 32 casos nuevos verdes, 3 casos nuevos rojos**, más dos de integración sólo recolectados. No es la suite completa. La primera revisión de mis tests tuvo cuatro errores mypy, corregidos sólo en tests antes de la corrida final limpia. Una prueba preliminar de lectura de nota fallaba con un doble que predeterminaba sus columnas: la descarté, ese rojo no cuenta como defecto demostrado; se reemplazó por integración pendiente.

### F2-1 · ALTA · Se puede quitar la factura después de tener notas de crédito

Fuentes: `gastos/aplicacion/gastos.py::editar_gasto`, `dominio/gasto.py::factura_completa_o_ninguna`, `notas_de_credito.py::crear_nota_de_credito`, spec notas, requisito «Toda nota de crédito está asociada a una factura».

El alta de nota ahora rechaza correctamente los campos de factura ausentes. Sin embargo, editar el gasto permite poner **los cuatro campos en null juntos**. El validador admite «ninguna factura» y la consulta del acumulado de notas sólo ocurre si cambia el importe. Una nota existente deja entonces de estar asociada a un gasto con factura. La FK de 0032 sólo referencia id/edificio/administración, no esos campos; no observé un guardia persistente de esa condición en la migración leída.

Reproducción: `test_no_se_quita_factura_con_notas[borrador|sin_ia|en_revision]`, comando E1. El doble ofrece factura de 100.00 y acumulado de notas 60.00 cuando se consulta; el caso real nunca pregunta por ese acumulado al borrar la factura. Se simulan sesión/transacción, pertenencia y auditoría, no el caso de uso ni el validador. Se observa el UPDATE emitido, no el commit en PostgreSQL.

Salida relevante de los tres casos:

```text
AssertionError: Se permite quitar la factura con notas: [call(<TextClause>, {
  ... 'importe': '100.00', 'cuit_emisor': None, 'punto_de_venta': None,
  'tipo_de_comprobante': None, 'numero_de_comprobante': None, ...})]
assert None is not None
3 failed, 32 passed in 0.54s
```

Test HTTP/PostgreSQL listo y marcado: `backend/tests/integracion/test_rompedor_gastos_intento_2.py::test_no_quitar_factura_con_nota_existente`. Crea factura y nota real, exige PATCH 422 y conservación de la clave. **Pendiente de ejecutar**. Reproducción confirmada en aplicación; consecuencias persistidas aún no verificadas en este entorno. No reparé producción.

### E2 · Lente correctitud

- **F1 original**: 18 casos propios de detalle, seis roles reales por tres recursos; vecino propietario recibe 403 `codigo=sin_permiso`, super admin/administrador/contador/auxiliar/consejo conservan lectura. Tres casos fuera de alcance reciben 404. No reproduje otro bypass.
- **F2 original**: PATCH vacío y reaprobar un aprobado tardío no emiten UPDATE. Inspeccioné el retorno idempotente antes del recálculo y el guardia de campos bloqueados. No existen rutas de anulación ni edición de notas en este router. Los cargos operan su propia tabla, sin UPDATE de gasto ni `periodo_de_imputacion`.
- **F3 original**: inspeccioné validadores de gasto/proveedor/nota/cargo, texto compartido y Dinero. Los mensajes presentes no interpolan el valor recibido; el mensaje de factura enumera nombres de campo, y Dinero puede nombrar el tipo, no su contenido. Tres ataques propios (control en texto, literal inválido, factura incompleta con marcador PRIVADO) conservan rechazo sin repetir el marcador. No afirmo inmunidad de futuros validadores: `str(ctx["error"])` confía en su autor. Los errores de tipo/literal siguen genéricos por diseño.
- **S1**: alta sin factura rechazada antes de insertar en caso propio verde; la otra vía de edición del gasto es F2-1. No hay PATCH de nota ni operación de anular nota en la superficie actual.
- **S2**: seis bordes propios verdes, tres estados editables × importe igual a acreditado / centavo menos. El aprobado rechaza edición por el guardia existente. No hay notas anuladas ni estado de nota en 0032: ese borde no es alcanzable con las operaciones actuales. Carrera editar/crear nota no ejecutada; ambas toman FOR UPDATE del gasto por inspección.

### E3 · Lente cableado y consumidores

Relevé los nueve GET del router. Proveedores, listados de gastos/cargos, aprobados y obligatorios pasan por `_edificio_autorizado(...VER_CONFIGURACION_DEL_EDIFICIO)`; los tres detalles pasan por `_lectura_autorizada`. No hay GET de proveedor por id, exportaciones ni endpoint de descarga Excel en este módulo. El Excel es POST de importación y exige permiso de escritura antes de leer el archivo. Listados con parámetros extra no introducen otra ruta ni saltan el guardia. No declaré probado el transporte HTTP de estas observaciones estáticas.

Inspeccioné diff de tests del constructor: son adiciones, sin eliminación de expectativas existentes en este diff. El borde de edición de concepto de aprobado espera 422, coherente con el guardia anterior que bloquea también concepto; no es evidencia del RED de PATCH vacío. La matriz real ejecutada por los tests propios confirma continuidad de contador/consejo/administrador. Tests de fronteras y permisos existentes pasaron en E1.

El consumidor futuro principal es 7; F2-1 altera la integridad documental de su gasto de origen. No agregué escritura al libro, ni cambié permisos o decisiones del portal. **Decisión de producto pendiente de lectura por el humano:** el vecino tampoco lee por id su propio cargo, igual que el listado. El constructor lo declaró; este informe lo conserva visible y no lo resuelve.

### E4 · Lente verdad de contratos

F4 original: `tasks.md:274` y KB12:947 apuntan ahora a **D-140**, correcto. Menciones legítimas D-131 del 2d y las históricas de renumeración no son defecto.

La spec de notas exige gasto con factura y respalda F2-1. Además conserva el escenario que al consultar la nota devuelve **ambos períodos separados**. `cargar_nota_de_credito` selecciona sólo el período de nota; su test existente consulta el gasto en una segunda llamada. Esto sigue siendo S4, pendiente de resolución y ejecución real, no se transforma en una falla runtime por un doble propio.

S3 original sigue visible: design promete validar tamaño/filas y una consulta al padrón, mientras la lectura del archivo es completa y el adaptador no fija límites propios. El comentario de Excel afirma leer fórmulas como texto crudo, pero usa `data_only=True`. No ejercité fórmula con caché ni carga grande; no presento esas sospechas como explotación demostrada. Los tests existentes de Excel verdes no sustituyen esos ataques pendientes.

## JUICIO

Autor: **Codex rompedor**. Comparación: correcciones reales frente a F1-F4, S1/S2 y contratos del change. Confianza **alta en el UPDATE observado de F2-1 y los rechazos/lecturas unitarios**, media en la consecuencia persistida hasta ejecutar PostgreSQL; verificación dinámica de RLS/carreras no disponible.

**El intento 2 no queda limpio.** F1/F2/F3/F4 originales tienen correcciones coherentes en la superficie examinada; S1 queda incompleta por la edición posterior del gasto. Devolver F2-1 al constructor con TDD y ejecutar reproducción de integración. Luego repetir rompedor sobre el diff de corrección. No es un veredicto de auditor ni autorización de construcción en otra frontera. No se infiere cierre de los 63 checks de tasks.

## SUPOSICIÓN

1. Persistencia real de F2-1: pendiente HTTP/PostgreSQL, test marcado entregado. No hay resultado inventado de RLS ni de constraints.
2. **S4**: lectura de nota sin período de factura frente a spec explícita, pendiente test `test_nota_devuelve_periodo_de_su_factura`; sólo recolectado. Definir si cambiar contrato o devolver ambos compete al responsable, no al rompedor.
3. **S3**: límites de Excel, fórmulas con caché y cantidad de consultas del padrón siguen sin ataque dinámico propio.
4. **S5**: RLS, carrera notas/edición, upgrade/downgrade y ensayo de roles no ejecutados por entorno. No se repitió CI remoto ni suite completa.
5. El registro histórico tasks atribuye intento 1 al plugin, mientras su original dice nativo. No reescribí esa historia ni la tomé como prueba de proveedor; este intento declara su ejecutor real.

## Fuentes leídas

- Instrucciones heredadas, CLAUDE/AGENTS por búsquedas locales; obsidian ausente; lecciones KB15 con truncamiento declarado. Skill local `.claude/skills/openspec-verify-change/SKILL.md` consultada como guía, con prioridad del contrato ROMPEDOR y sin adoptar su cierre automático.
- Salidas CLI list/status/instructions; proposal; tasks a través de instructions; design y spec notas en las secciones de factura, períodos, importación y autorización; intento 1 completo e índice LEEME.
- Router gastos; casos de uso gastos/notas/errores; cargos por búsquedas de operaciones; dominio gasto/proveedor/nota/cargo, texto y Dinero compartidos; identidad/permisos y auditoría; migración 0032; adaptador Excel.
- Diff `6ec260e..f1f165d`, en particular sus cinco archivos de tests de integración y cambios de producción; comparación `58f2d76..63582e4`; referencias acotadas de KB12 y tasks.
- Tests ejecutados E1 y helpers reales de notas para tests de integración pendientes.
- `apply-2-constructor.md` completo leído **después** de análisis propio y primeras reproducciones.

## Contaminación

El brief ya trae las afirmaciones del constructor y el intento 1 fue entrada explícita. Además `openspec instructions apply` imprime el texto de tasks, incluyendo C2.1-C2.7, antes de mi análisis: **contaminación por esas afirmaciones declarada**. No leí `apply-2-constructor.md` hasta obtener mis primeros rojos y revisar código; su lectura posterior contrastó alcance/S3/S4 y decisión del vecino. No reclamo independencia sólo por el nombre: constructor declara Claude, este ejecutor es Codex nativo, sin verificación adicional de modelo. No busqué conclusiones de otros revisores para fabricar acuerdo.

## FALLAS REPRODUCIDAS

**F2-1: quitar los cuatro campos de factura a gasto con notas**, en tres estados editables, **tres fallas por aserción a nivel de aplicación**. Tests en `backend/tests/unitarios/test_rompedor_gastos_intento_2.py`. Integración de esa falla y S4 entregadas como pendientes en `backend/tests/integracion/test_rompedor_gastos_intento_2.py`.

Próxima acción: constructor sobre F2-1 y orquestador ejecutando los dos tests de integración; resolver disposición explícita de S3/S4 antes de auditoría. Producción intacta.
