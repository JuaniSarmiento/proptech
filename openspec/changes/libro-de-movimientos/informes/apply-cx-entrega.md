# Construcción: CX-01 y CX-02 (27/10/2026)

## JUICIO (constructor, confianza alta)

Alcance recibido: corregir exclusivamente CX-01/E4 y CX-02/E12 sobre `401bcd5`, en
`change/libro-de-movimientos`. Comparado con el informe completo
`.git/informes-libro-de-movimientos/13-rompedor-codex-fases-1-3.md`, D3/D4/D5/D12,
las elecciones firmadas E1 a E16 y la enmienda E7. No se modificaron esas elecciones, el
design, los permisos, las migraciones ni el cálculo puro de exclusiones y topes.

- Créditos y ambas formas de corrección vuelven a resolver replay inmediatamente después de
  adquirir el candado y antes de validar estado o imputar pendientes. Conservan la consulta
  optimista inicial y la comparación de los datos del pedido.
- Emisión vuelve a resolver replay después de leer intentos, antes de rechazar por período
  activo. El replay bloquea todas sus cuentas en una sola llamada ordenada y toma una sola
  foto SQL con `fotos`, también consistente ante anulación concurrente, que no toma candados.
- Se revisó el archivo de diez tests recibido sin commit. CX-02 requería corregir un
  intercalado sincrónico que se trabaría con el bloqueo correcto. Ahora usa hilo, eventos y
  `pg_blocking_pids`, sin sleeps; verifica las fotos exactas y libera el lector antes del join.
  Se agregaron conteos de siete tablas y una variante del crédito de corrección: once casos.

## EVIDENCIA (constructor)

Todos los horarios siguientes son del 27/10/2026, zona -03. Los comandos de pruebas usan
`UV_NO_ENV_FILE=1`. Las primeras corridas corresponden a la base `401bcd5` y, desde GREEN,
al árbol de construcción todavía sin commit, no a un SHA de entrega inventado.

```text
BASELINE: bash infra/ci/test-backend.sh tests/integracion/test_cc_cuentas.py
  tests/integracion/test_cc_creditos.py tests/integracion/test_cc_correcciones.py
  tests/integracion/test_cc_emisiones.py tests/integracion/test_cc_concurrencia.py
  tests/integracion/test_cc_lecturas.py -q -p no:cacheprovider --tb=short
08:35:17–08:36:01 -> 92 passed in 43.15s

FOCAL: bash infra/ci/test-backend.sh tests/integracion/test_cc_replay_carrera.py
  -q -p no:cacheprovider --tb=short
RED   08:38:04–08:38:13 -> 10 failed, 1 passed in 7.41s
GREEN 08:38:41–08:38:50 -> 11 passed in 7.52s

MUTANTE replay: mismo comando FOCAL
08:39:33–08:39:46 -> 9 failed, 2 passed in 11.23s
E AssertionError: rechazo de replay idéntico / imputacion: 2 != 1
Restauración y FOCAL: 08:39:54–08:40:07 -> 11 passed in 10.63s

MUTANTE foto: bash infra/ci/test-backend.sh
  tests/integracion/test_cc_replay_carrera.py::test_el_replay_de_emision_devuelve_una_sola_foto
  -q -p no:cacheprovider --tb=short
08:40:14–08:40:24 -> 1 failed in 9.44s
E AssertionError: El replay leyó sin bloquear todas sus cuentas
E assert [False] == [True]
Restauración y FOCAL: 08:40:29–08:40:42 -> 11 passed in 11.18s

uv run --directory backend --no-env-file ruff check .
08:40:53 -> All checks passed!
uv run --directory backend --no-env-file ruff format --check .
08:41:00 -> 326 files already formatted
uv run --directory backend --no-env-file mypy
08:41:01 -> Success: no issues found in 299 source files
```

Las salidas completas con comando, SHA, horas y líneas `E` están en
`.git/4b-fase1-logs/codex-cx/`. Los mutantes guardan primero `backup-*.py`, escriben
`mutante-replay.patch` y `mutante-foto.patch` y restauran bytes exactos en `finally`.
Una primera invocación del segundo mutante se detuvo en la comprobación del runner por
coincidir también la indentación de otro bloqueo; no llegó a mutar ni ejecutar pytest.
Se corrigió el runner y se produjo la evidencia válida anterior. Formato detectó un archivo
por reformatear; se aplicó formato exclusivamente al test nuevo antes del verde de formato.

El mutante de foto conserva `fotos` en una sentencia, por lo que su fallo demuestra la
espera bajo candado elegida, no una foto mezclada en esa variante. El RED contra `401bcd5`
sí demuestra la mezcla imposible `{A: 0, B: 0}`. No se confunden ambas afirmaciones.

### Corrida sobre el commit de entrega

Se ejecuta después de este commit, sin nuevas ediciones de código. La evidencia de cierre,
incluido `git rev-parse HEAD`, comando, hora, resultado y limpieza, se conserva localmente en:

- `.git/4b-fase1-logs/codex-cx/09-cierre-backend.log`:
  `bash infra/ci/test-backend.sh -q -p no:cacheprovider`, suite completa.
- `.git/4b-fase1-logs/codex-cx/10-cierre-ruff-check.log`,
  `10-cierre-ruff-format.log`, `10-cierre-mypy.log`.
- `.git/4b-fase1-logs/codex-cx/11-estado-final.log`.
- `.git/informes-libro-de-movimientos/14-constructor-codex-cx.md`: retorno final completo.

Esta sección identifica dónde consultar resultados posteriores, no afirma que ya se hubieran
ejecutado al escribirla. No completa la tarea 6.1 del change: no hay web, humo, ensayo de
roles, CI remoto, push ni archive en este encargo de corrección.

## EVIDENCIA (despacho)

`openspec list --json` y `openspec status --change libro-de-movimientos --json` encontraron el
change activo, artefactos completos; `openspec instructions apply` informó 14/19 tareas.
La captura inicial de comandos, horas y estado está en
`.git/4b-fase1-logs/codex-cx/inicial.txt` (incluye `active-stack roles --json`).

Se lanzó un único auxiliar de construcción, `cx_tests`, con alcance explícito:
`backend/tests/integracion/test_cc_replay_carrera.py` y los helpers importados de
`_cuenta_corriente.py` y `test_cc_correcciones.py`. Primero inspeccionó sin editar ni ejecutar;
después, sobre sus hallazgos, corrigió sólo ese test, también sin ejecutar suites. El constructor
principal adaptó dos rechazos para que el rojo se observe en aserciones y ordenó las aserciones
de CX-02 antes de correr RED. No hubo dos suites en paralelo ni otros agentes de construcción.
El retorno íntegro del auxiliar está en `apply-cx-auxiliar-tests.md`.

## JUICIO (constructor, confianza alta; límites de revisión)

No se convocaron revisores de verify: éste es un encargo de construcción. No hay dictamen
independiente ni APROBADO del auditor sobre estas correcciones. QA del comando devuelve
`always`, pero no se presenta al auxiliar constructor como revisor QA independiente.
La salida del selector para DBA fue `no-schema`, backend `no-endpoint`, frontend `no-ui-tree`,
DevOps `no-deploy`; arquitecto y analista, `not-decided-by-diff`. No se usan esas salidas
para acreditar una revisión del libro financiero. Backend, DBA, arquitecto y QA quedan para
verify del diff quieto; frontend y DevOps no revisaron por no cambiar UI ni despliegue.
Analista no se convocó porque no se está explorando, proponiendo ni archivando. Rompedor,
senior y auditor no se convocaron: no se solicitó otro ciclo de verify ni cierre del change.

Fuentes leídas: AGENTS.md, proposal, design, tasks, delta specs relevantes, informe 13 completo,
log rojo heredado, `knowledge-base/15_lecciones.md`, módulos de aplicación y sus tests/fixtures,
runner de backend, pyproject y workflow de CI. Consumidores buscados en core/API/worker/infra:
actualmente sólo existen las definiciones del libro; los consumidores reales 4c/7/8 siguen pendientes.
Skills aplicadas: openspec-apply-change, test-driven-development, postgres-rls y pautas SQLAlchemy.
El contexto de Engram incluía trabajo anterior y el informe 13; el usuario dictó los dos hallazgos
y mutantes. No se atribuye independencia entre esta construcción y el rompedor Codex anterior.

## SUPUESTOS y límites

- Constructor y auxiliar son de la familia Codex/OpenAI disponible. La variante exacta no se
  acredita mediante un registro externo de modelo; no se afirma diversidad de proveedores.
- El selector de roles y las fechas de Git no prueban por sí solos conformidad ni vigencia de
  la KB. Se informaron documentos anteriores al archive de 4a y no se reescribió la KB.
- Los locks se mantienen hasta terminar la transacción del llamador. El replay no agrega
  movimientos, obligaciones, eventos ni imputaciones; el protocolo técnico de candados sigue
  usando `INSERT ... ON CONFLICT DO NOTHING` y `SELECT ... FOR UPDATE` de E2.
- Sin stress exhaustivo ni model checking; once regresiones focales y suites ejecutadas no
  demuestran todos los intercalados posibles. No se acreditan los flujos futuros del 7/8.
- Los logs en `.git` son locales y no se publican ni viajan con el commit.
