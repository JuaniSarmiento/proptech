# apply · intento 1 · constructor de integración · `gastos-y-cargos` (6, MEDIUM)

- **Autor**: role-constructor, subagente nativo de Claude (Claude Code), despachado por el orquestador.
- **Fecha**: 30/10/2026.
- **Revisión de partida**: `revision-6` en `2f81682` (= `origin/change/gastos-y-cargos`, base `5c6d84c`) + `origin/main` en `60b3dd5`.
- **Revisión entregada (código y specs)**: `838a0b3`. Encima, un commit sólo de documentación (`tasks.md`, este informe y `LEEME.md`).
- **Commits del intento** (primer padre): `c4c4a25` merge, `1384c3e` renumeración, `05c3914` 403 con `codigo`, `6a48a5a` expectativa del test de personal, `838a0b3` spec de fronteras, más el de documentación.
- **Lecciones leídas**: `knowledge-base/15_lecciones.md` de `origin/main` (encabezado y L-054 a L-062 completas; títulos de L-001 a L-053). Aplicadas en particular: L-055 (suite entera sobre el SHA final), L-056 (ENOTDIR en worktree), L-061 (RED guardado antes del commit), L-062 (gitleaks).

## EVIDENCIA

### E1. Merge y conflictos (14:12:46)

`git merge --no-commit --no-ff origin/main` → conflictos en los seis archivos previstos, ninguno más:

| Archivo | Resolución |
|---|---|
| `backend/tests/integracion/test_libro_rollback.py` | Lado del 6 (cabeza de Alembic), después llevado a `"0033"` en `1384c3e` |
| `infra/ci/ensayo-roles.sh` | Lado del 6, después `verificar_revision 0033` (dos veces) y mensaje `ciclo 0033/0016/0033` |
| `backend/tests/unitarios/test_fronteras_de_modulos.py` | Los dos bloques: tests de `gastos` (6) + `test_el_ejemplo_vuelve_a_escribir_una_tabla_de_acceso` y los de `vinculacion_de_desarrollo` (2d) |
| `knowledge-base/09_decisiones_y_supuestos.md` | `main` primero (D-131 a D-139), después las dos del 6 renumeradas **D-140** (pantallas sin change hermano) y **D-141** (P36 y P37) |
| `knowledge-base/12_fichas_de_changes.md` | Fila RB-5 del 6 (cerrada por `2e2e925`); filas RB-6 y RB-7 de `main` (corrección de D-138) |
| `knowledge-base/15_lecciones.md` | `main` primero (L-055 a L-062), después las dos del 6 como **L-063** (mypy sobre todo `src/`) y **L-064** (suite completa y tests estructurales) |

Merge commiteado como `c4c4a25`. La modificación previa del orquestador en `tasks.md` se conservó y entró en `1384c3e`.

### E2. Renumeración de migraciones (`1384c3e`, 14:15:13)

`git mv` y `revision`/`down_revision`/docstring: `0028_gastos_y_proveedores`→`0029`, `0029_vocabulario_del_gasto`→`0030`, `0030_cuit_del_complejo`→`0031`, `0031_notas_de_credito_y_cargos`→`0032`, `0032_categoria_obligatoria_mensual`→`0033`; `0029` revisa `0028` (= `0028_ver_personal`, id real `"0028"`).

```
$ uv run alembic heads
0033 (head)
$ uv run alembic history | head
0032 -> 0033 (head), La marca de gasto mensual obligatorio ...
0031 -> 0032, Notas de crédito ...
0030 -> 0031, El documento (CUIT) propio del edificio ...
0029 -> 0030, Vocabulario del gasto ...
```

`0028_ver_personal` y `0030_vocabulario_del_gasto` insertan nombres distintos en `accion_de_auditoria` y cada `downgrade` borra sólo los suyos: el orden nuevo no los cruza.

Referencias actualizadas: `test_libro_rollback.py` (3 aserciones), `ensayo-roles.sh` (3 líneas), comentario de `test_gastos.py`, KB `04` (seis menciones) y `12` (ficha 6), `proposal.md` (numeración), `design.md` (nota de integración al pie del Migration Plan, sin reescribir el plan revisado).

### E3. Decisiones y lecciones del 6 (`1384c3e`)

Reemplazos línea por línea, con aserción de que cada línea cambiaba, sólo en las líneas del 6: `CHANGES.md` (C-09, 2), `proposal.md` (2), `tasks.md` (10), KB `04` (3), `06` (2), `10` (3), `11` (2), `12` (4), `0033_categoria_obligatoria_mensual.py`, `complejos/aplicacion/lectura.py`, `gastos/aplicacion/gastos.py`, `test_obligatorios_faltantes.py`, `test_periodo_de_imputacion.py`, `test_gastos.py` (`D-132-bis` → `D-141-bis`). Siguen como D-131/D-132 del 2d: `AGENTS.md`/`CLAUDE.md`, `CHANGES.md` (C-21), KB `03`, `07`, `08`, `10:267`, `11:237-245`, `12` (ficha 2d). Comprobado con `rg -n 'D-13[12]'` sobre el árbol del 6 después del cambio: los únicos restos están en la sección del orquestador de `tasks.md`, que describe la renumeración.

### E4. Falla de integración 1: el 403 del 6 sin `codigo` (`05c3914`)

- RED 14:17:17, `pytest tests/integracion/test_libro_rollback.py ... test_rutas_protegidas.py ...` → `1 failed, 603 passed`: `test_barrido_403_con_alcance_y_sin_permiso` (test del 2d) con `KeyError: 'cargo_id'` (setup: el mundo del barrido no tenía los ids de las rutas del 6). Se sumaron `proveedor_id`, `gasto_id`, `nota_id`, `cargo_id` y `periodo`.
- RED 14:19:05 por aserción, el mismo test:
  ```
  AssertionError: ('/api/complejos/{complejo_id}/cargos-particulares', {'detail': {'detalle': 'sin_permiso', 'permiso_faltante': 'ver_configuracion_del_edificio'}})
  assert None in ('sin_acceso', 'sin_permiso')
  ```
  D-131 (2d) exige `detail.codigo` en todo 403; los cuatro 403 de `proptech_api/gastos.py` (`_edificio_autorizado`, `_autorizar_proveedor`, `_autorizar_gasto`, `_autorizar_cargo`) no lo tenían.
- GREEN 14:20:26 con `"codigo": "sin_permiso"` en los cuatro: `683 passed` (`test_rutas_protegidas`, `test_gastos`, `test_proveedores`, `test_cargos_particulares`, `test_notas_de_credito`).
- El barrido sólo alcanza `_edificio_autorizado`; para los otros tres se sumó `assert respuesta.json()["detail"].get("codigo") == "sin_permiso"` en los tests de 403 del 6 que ya existían (gasto, nota, cargo, escritura de proveedor) y un test nuevo, `test_editar_proveedor_sin_permiso_da_403_con_codigo`.
- Mutantes (borrar la línea `codigo` de un sitio por vez, con `../../mutante.py`, respaldo en `../../gastos.py.bak`):

  | Sitio | Hora | Resultado |
  |---|---|---|
  | `_edificio_autorizado` | 14:23:46 | `AssertionError: {"detail":{"detalle":"sin_permiso","permiso_faltante":"cargar_gastos_y_preparar_liquidacion"}}`, 1 failed |
  | `_autorizar_proveedor` | 14:23:54 | ídem, 1 failed |
  | `_autorizar_gasto` | 14:24:02 | ídem en `test_gastos` y `test_notas_de_credito`, 2 failed |
  | `_autorizar_cargo` | 14:24:14 | ídem, 1 failed |

  Cada mutante revertido; `cmp gastos.py.bak src/proptech_api/gastos.py` → igual; GREEN 14:24:22 `5 passed`. Ningún mutante entregado.

### E5. Falla de integración 2: spec de fronteras (`838a0b3`, 14:25:47)

`openspec validate gastos-y-cargos` (openspec 1.14.3 instalado):

```
✗ [ERROR] fronteras-de-modulos/spec.md: MODIFIED "El SQL de cada módulo sólo nombra sus tablas" omits scenario(s) the current spec still has: "El ejemplo vuelve a escribir una tabla de acceso".
```

El MODIFIED del 6 también listaba las excepciones de `ejemplo.py` que el 2d sacó (D-133). Se sumaron al bloque la frase de `main` sobre `ejemplo.py` y su escenario, y el escenario "El código de hoy pasa" quedó con las excepciones vigentes. Después: `Change 'gastos-y-cargos' is valid` (sólo warnings de largo de requisitos). Los otros MODIFIED del 6 (`auditoria-de-acciones`) no los tocó `main` (`git diff --stat 5c6d84c origin/main -- openspec/specs` no incluye esa capacidad).

### E6. Primera suite completa (sobre `05c3914`, en el worktree, 14:25:17 a 14:43:15)

`alembic heads` → `0033 (head)`; ruff check y format sin hallazgos; `mypy` → `Success: no issues found in 364 source files`; `bash ../infra/ci/test-backend.sh -q -p no:cacheprovider` → `2 failed, 4639 passed, 1 xfailed`:

1. `test_personal_api.py::test_el_administrador_principal_lista_el_personal` (2d): `Extra items in the left set: '4db0da02-…'`. Ese id es el `contador` que el 6 sumó a la fixture `api_edificio` (`conftest.py`), que está por debajo del principal y que el listado muestra bien (D13). Reproducido aislado 14:43:24. Se ajustó la expectativa del test; GREEN 14:44:50, `40 passed` (`test_personal_api.py`, `test_invitar_personal_api.py`). Commit `6a48a5a`.
2. `test_migracion_roles_de_la_empresa.py::test_error_tras_convertir_revierte_filas_esquema_y_force`: `[Errno 20] Not a directory: '…/wt-6/.git/informes-roles-bloque-a-v2'`. Es el ENOTDIR de L-056: en un clon normal de `6a48a5a`, 14:45:34 → `16 passed`.

### E7. Suite de entrega (sobre `838a0b3`, clon normal, 14:46:34 a 15:04:47)

Desde `backend/`:

```
uv run alembic heads                  → 0033 (head)
uv run ruff check .                   → All checks passed!
uv run ruff format --check .          → 401 files already formatted
uv run mypy                           → Success: no issues found in 364 source files
bash ../infra/ci/test-backend.sh -q -p no:cacheprovider
                                      → 4641 passed, 1 xfailed, 19 warnings in 1060.47s
```

Antes (14:15 a 14:17, sobre el árbol de `1384c3e` sin commitear): `tests/unitarios tests/infra` → `2454 passed`.

### E8. Web, CLAUDE/AGENTS

- `git diff --stat 5c6d84c 2f81682` no incluye ningún archivo de `web/`; `git diff origin/main 05c3914 -- web | wc -l` → `0`. El 6 no choca con el 3d (`web/e2e/api-falsa.ts` sale tal cual de `main`).
- `diff CLAUDE.md AGENTS.md` → vacío. Los dos son los de `main` (3d archivado, el 6 "en revisión, sin mergear", PR #4).

## JUICIO

Autor: role-constructor. Comparación: merge contra los dos padres, la cadena de Alembic y el contrato de `main`. Confianza: alta en la cadena de migraciones y en los dos arreglos, que tienen rojo por aserción y suite completa en verde; media en el ensayo de roles, que no corrí.

1. La integración pide tres arreglos que no son conflictos de texto: los tres vienen de reglas de `main` que el 6 no conocía al construirse (contrato 403 de D-131, fixture compartida, spec de fronteras del 2d). Los arreglé con el cambio mínimo porque son integración, no bugs del 6 en su propio alcance. **Para el rompedor**: el arreglo del 403 cambia código de producción del 6 (`proptech_api/gastos.py`). Conviene revisar si queda otro 403 del 6 sin `codigo` por un camino que no sea esos cuatro helpers. Busqué con `rg 'status_code=403|403' src/proptech_api/gastos.py src/proptech_api/app.py` y no encontré otro.
2. En `tasks.md` dejé tal como estaba la numeración vieja de migraciones dentro de la evidencia del apply (RED, `down`, notas de secuencia), porque reescribirla falsearía qué se corrió y cuándo. El mapa nuevo quedó en la tarea I.2. Las decisiones y lecciones sí van con el número nuevo en todo el archivo, como pedía el brief.
3. El texto de L-064 dice "Corregidos a `\"0032\"`": eso es lo que pasó el 29/10, así que lo dejo como historia de un archivo de sólo agregar.
4. `D-132-bis` (ahora `D-141-bis`) en `test_gastos.py` no existe como entrada en `09`. Es la decisión del CUIT del 28/10 que está en la tarea 3.10. Es una observación, no la toqué más allá del número.

## SUPOSICIÓN

- `infra/ci/ensayo-roles.sh` **no se ejecutó** porque necesita el stack de Compose (L-043). Su cabeza escrita a mano pasó a `0033` y coincide con `alembic heads`. `test_ensayo_login.py`, que compara el script con `ScriptDirectory.get_current_head()`, pasó en la suite completa.
- `shellcheck` **no se ejecutó** porque no está instalado en esta máquina. El cambio al script es sólo de números.
- No corrí lint, tipos ni tests de la web porque el árbol `web/` es idéntico al de `main`. Su CI en `main` (`d534ac2`, D-139) no lo verifiqué yo.
- El openspec instalado es 1.14.3 y el proyecto fija 1.13.0. El error de E5 es semántico (un escenario de `main` que se perdía), así que lo doy por válido igual, pero no lo verifiqué con 1.13.0.
- La suite de entrega corrió sobre `838a0b3`. El commit posterior sólo toca `openspec/changes/gastos-y-cargos/{tasks.md,informes/*}`, que ningún test lee: `rg -l openspec backend/tests` → ninguno.
- No hice push ni miré el CI remoto.

## Fuentes leídas

- `knowledge-base/15_lecciones.md` (`origin/main` y el lado del 6).
- Los diffs de conflicto de los seis archivos; `git diff --stat 5c6d84c 2f81682` y `5c6d84c origin/main`.
- `backend/migraciones/versions/0028_ver_personal.py`, `0029`–`0033` del 6.
- `backend/src/proptech_api/gastos.py` (los helpers de autorización), `src/proptech_api/errores.py` (contrato 403).
- `backend/tests/integracion/test_rutas_protegidas.py`, `test_personal_api.py`, `conftest.py` (diff del 6), los tests de 403 del 6, `tests/infra/test_ensayo_login.py` (por `rg`).
- `openspec/specs/fronteras-de-modulos/spec.md` y el delta del 6; `proposal.md`, `design.md` y `tasks.md` del change.
- `infra/ci/test-backend.sh`, `.github/workflows/*.yml` (por `rg`: ruff, ruff format, mypy, test-backend).
- `.gitleaksignore` (main) y `.gitleaks.toml` (el 6), que conviven.

## Contaminación

Ninguna. No había otros informes de este change. No leí informes de rompedor ni de auditor de otros changes, salvo las citas de L-059 a L-062 dentro de `15_lecciones.md`.

## Hallazgos para el orquestador

- **H1 (arreglado, integración)**: los 403 del 6 no llevaban `codigo` (D-131). Commit `05c3914`, con un mutante por sitio.
- **H2 (arreglado, integración)**: `test_personal_api` del 2d no contaba al `contador` que el 6 sumó a la fixture. Commit `6a48a5a`.
- **H3 (arreglado, integración)**: el MODIFIED de fronteras del 6 habría borrado al archivar el escenario del ejemplo del 2d. Commit `838a0b3`.
- **H4 (entorno)**: el ENOTDIR de worktree (L-056) en `test_migracion_roles_de_la_empresa.py`. No es del código. Se juzga en un clon normal.
- No encontré bugs del 6 en su propio alcance.
