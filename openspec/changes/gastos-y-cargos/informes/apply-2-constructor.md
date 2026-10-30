# apply · intento 2 · constructor (correcciones del rompedor) · `gastos-y-cargos` (6, MEDIUM)

- **Autor**: role-constructor, subagente nativo de Claude (Claude Code), despachado por el orquestador.
- **Fecha**: 30/10/2026.
- **Revisión de partida**: `6ec260e`, más el archivo sin commitear del rompedor `backend/tests/unitarios/test_rompedor_gastos_intento_1.py`.
- **Revisión entregada (código)**: `58f2d76`. Encima va un commit sólo de documentación: F4 en `12_fichas_de_changes.md` y `tasks.md`, este informe y `LEEME.md`.
- **Lecciones**: `knowledge-base/15_lecciones.md`, ya leído en el intento 1 (L-001 a L-064). Aplicadas: L-051 (F3), L-055 y L-056 (suite completa en un clon normal), L-061 (RED guardado antes del commit).
- **Alcance**: sólo F1 a F4, S1 y S2 de `verify-1-breaker.md`. S3 y S4 no los toqué.

## EVIDENCIA

### RED

- 15:17:11 `uv run pytest tests/unitarios/test_rompedor_gastos_intento_1.py -q` → `7 failed in 0.52s`. Las 7 fallan por aserción: F1 ×3, F2, F3 y F4 ×2.
- 15:19:16, tests propios de integración (HTTP real, PostgreSQL en Docker), sobre `6ec260e` sin cambios de producción:

  ```
  test_vecino_del_edificio_no_lee_el_detalle_de_un_gasto      assert 200 == 403
  test_vecino_del_edificio_no_lee_el_detalle_de_una_nota      assert 200 == 403
  test_vecino_del_edificio_no_lee_el_detalle_de_un_cargo      assert 200 == 403
  test_el_422_del_gasto_conserva_la_explicacion_del_dominio[importe]  assert 'el importe debe ser mayor que cero' in 'valor inválido'
  test_el_422_del_gasto_conserva_la_explicacion_del_dominio[periodo]  assert 'el período debe ser el primer día de un mes' in 'valor inválido'
  test_cuit_invalido_da_422_con_el_formato_esperado           assert 'once dígitos (0-9 ASCII), ...' in 'valor inválido'
  test_nota_contra_un_gasto_sin_factura_da_422 (S1)           assert 201 == 422
  test_bajar_la_factura_por_debajo_de_sus_notas_da_422 (S2)   assert 200 == 422
  test_editar_un_aprobado_tarde_conserva... (F2, {})          assert '2026-10-01' == '2026-11-01'
  10 failed, 15 passed
  ```

  La variante de F2 con `{"concepto": ...}` falló por otra razón: `422` del guardia de aprobado, que bloquea todos los campos, también `concepto`. La expectativa del test estaba mal, no el código. La reescribí como borde, `test_editar_un_campo_de_un_aprobado_tarde_da_422_y_no_lo_mueve`, que nace verde. 15:20:04: el RED de F2 con `{}` sigue en `assert '2026-10-01' == '2026-11-01'`.

### GREEN (15:21:05)

`ruff check src tests` limpio y `mypy` → `Success: no issues found in 365 source files` (cuenta el archivo del rompedor, todavía presente). El pytest corrió sobre los cinco archivos de integración del 6, más `test_rutas_protegidas`, `test_lectura_gastos_aprobados`, `test_obligatorios_faltantes` y `tests/unitarios`: `2 failed, 2982 passed`. Los 2 rojos eran F4, documental. Después de corregir F4, 15:24:03: el archivo del rompedor dio `7 passed`, y lo borré.

Cambios de producción:

| Hallazgo | Archivo | Cambio |
|---|---|---|
| F1 | `proptech_api/gastos.py` | `_lectura_autorizada(asignaciones, complejo_id)`: 404 si no alcanza; 403 `{"codigo": "sin_permiso", "detalle": "sin_permiso", "permiso_faltante": "ver_configuracion_del_edificio"}` si no puede. La usan `ver_gasto`, `ver_nota_de_credito` y `ver_cargo_particular`. Es el mismo permiso que el listado: sin permiso nuevo ni cambio en la matriz. |
| F2 | `gastos/aplicacion/gastos.py::editar_gasto` | `periodo_de_imputacion` sigue a `periodo` sólo en un estado editable; si no, conserva el de la fila. |
| F3 | `gastos/aplicacion/errores.py::error_de_validacion` | Conserva `str(ctx["error"])` de los errores `value_error`, que son los validadores propios con textos fijos; el resto queda como "valor inválido". Un solo arreglo para los cinco casos de uso que la llaman (proveedores, gastos, notas, cargos). |
| S1 | `gastos/aplicacion/notas_de_credito.py` | Al bloquear la factura lee también los cuatro campos de factura; si falta alguno, 422 en `gasto_id`. |
| S2 | `gastos/aplicacion/gastos.py::editar_gasto` | Si cambia el importe, suma las notas del gasto (con la fila ya bloqueada `FOR UPDATE`); si el importe nuevo queda por debajo, 422 en `importe`. |

### Mutantes (un mutante por aserción clave de F1 y F2, todos revertidos)

| Mutante | Hora | Resultado |
|---|---|---|
| M1: `_lectura_autorizada` saltea el `puede` | 15:24:18 | 3 rojos `assert 200 == 403` (gasto, nota, cargo) |
| M2: pide `cargar_gastos_y_preparar_liquidacion` en vez del permiso de lectura | 15:24:36 | 9 rojos `assert 403 == 200` (`ver`, `consejo`, `contador` × 3 recursos) |
| M3: `periodo_de_imputacion` sigue siempre a `periodo` | 15:24:54 | 1 rojo `assert '2026-10-01' == '2026-11-01'` |

Restauración comprobada con `cmp` contra los respaldos `../../api.bak` y `../../core.bak` → `RESTAURADO`. Ningún mutante entregado.

### F4 (documental, sin RED de código)

`tasks.md:274` y `knowledge-base/12_fichas_de_changes.md:947` pasan de D-131 a D-140. Lo validan las dos reproducciones del rompedor, que dieron verde a las 15:24:03 antes de borrar el archivo. Además, `rg -n 'D-13[12]' | rg -i 'gasto|pantallas de|HU-A3|P36|P37|proveedor|cargo'` sólo devuelve comentarios del 2d sobre el 403, historia de la renumeración e informes.

### Suite completa de entrega (`58f2d76`, clon normal, 15:25:22 a 15:43:41)

```
uv run alembic heads          → 0033 (head)
uv run ruff check .           → All checks passed!
uv run ruff format --check .  → 401 files already formatted
uv run mypy                   → Success: no issues found in 364 source files
bash ../infra/ci/test-backend.sh -q -p no:cacheprovider → 4665 passed, 1 xfailed, 19 warnings in 1064.96s
```

Conteo propio: 4641 (intento 1) + 24 tests nuevos = 4665.

| Archivo | Tests nuevos |
|---|---|
| `test_gastos.py` | 8 (F1: 1 + 4 perfiles + 404; F3: 2) |
| `test_proveedores.py` | 1 (F3) |
| `test_notas_de_credito.py` | 8 (F1: 1 + 4; S1: 1; S2: 2) |
| `test_cargos_particulares.py` | 5 (F1: 1 + 4) |
| `test_periodo_de_imputacion.py` | 2 (F2 y su borde) |

## JUICIO

Autor: role-constructor. Confianza: alta para F1, F2, S1 y S2, que tienen RED por aserción en PostgreSQL real, GREEN, suite completa y, en F1 y F2, mutantes.

- **F1** cerrada sin tocar la matriz ni crear permisos: el detalle usa exactamente la acción del listado. El change sigue MEDIUM según el criterio que fijó el orquestador. Consecuencia que conviene mirar: el vecino tampoco ve por id **su propio** cargo particular. Hoy tampoco puede listarlo, así que el comportamiento queda coherente con el listado. Que el vecino lea sus cargos es una funcionalidad del portal del vecino, fuera de este change.
- **F3**: el arreglo sólo deja pasar textos de `ValueError` propios, que el código del dominio escribe fijos y que no repiten el valor (L-002, L-051). Si algún día un validador incluyera el valor en su mensaje, este arreglo lo filtraría al 422. Eso queda como regla para quien escriba validadores. `complejos/aplicacion/errores.py` tiene la misma forma y la misma pérdida, pero es del 3a, no del 6, y no lo toqué.
- **S1 y S2** se reprodujeron como fallas reales, no eran sólo sospechas. El código de 422 y el campo que nombran (`gasto_id`, `importe`) siguen la forma de los demás 422 del módulo.
- **F4**: mi informe del intento 1 decía que las referencias del 6 estaban todas renumeradas. Era falso para dos líneas, y lo reconozco en C2.6 de `tasks.md`.

## SUPOSICIÓN

- No probé una carrera entre editar el importe (S2) y cargar una nota al mismo tiempo. Me apoyo en que las dos operaciones toman `FOR UPDATE` sobre la misma fila de `gasto`; es lectura de código, sin test de concurrencia.
- No corrí `shellcheck` (no está instalado) ni `ensayo-roles.sh` (necesita Compose). Este intento no tocó ninguno de los dos.
- El contrato OpenAPI de los detalles no declara el 403 nuevo de forma explícita. No hay test que lo exija y no lo cambié.
- No hice push ni miré el CI remoto.

## Fuentes leídas

- `informes/verify-1-breaker.md` completo y `backend/tests/unitarios/test_rompedor_gastos_intento_1.py` (primeras 80 líneas y salida).
- `proptech_api/gastos.py` (helpers de autorización, handlers de detalle, manejador de 422); `gastos/aplicacion/{gastos,notas_de_credito,errores}.py`; `gastos/dominio/{cuit,gasto}.py`; `compartido/dinero.py` (mensajes) y `compartido/texto.py`.
- La matriz de permisos, evaluada con `puede` para vecino propietario e inquilino, consejo, contador y auxiliar.
- Specs del change: `notas-de-credito` y `gastos-del-periodo` (requisito de aprobado).
- Tests y fixture: `conftest.py` (roles de `api_edificio`) y los helpers de los cinco archivos de integración del 6.

## Contaminación

Leí el informe del rompedor (`verify-1-breaker.md`), que es la entrada de esta corrección: los hallazgos y sus ubicaciones vienen de ahí. Antes de corregir verifiqué cada uno con tests propios contra PostgreSQL. Ya conocía mi propio informe del intento 1. No leí otros informes.
