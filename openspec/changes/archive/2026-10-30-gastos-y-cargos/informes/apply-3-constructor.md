# apply · intento 3 · constructor (correcciones del rompedor 2) · `gastos-y-cargos` (6, MEDIUM)

- **Autor**: role-constructor, subagente nativo de Claude (Claude Code), despachado por el orquestador.
- **Fecha**: 30/10/2026.
- **Partida**: `a6029cf`, más los dos archivos sin commitear del rompedor 2.
- **Código entregado**: `f432055`. Encima, un commit sólo de documentación (`tasks.md`, este informe y `LEEME.md`).
- **Lecciones**: `knowledge-base/15_lecciones.md`, ya leído en el intento 1.
- **Alcance**: F2-1 y S4 de `verify-2-breaker.md`. S3 (límites de Excel) no se tocó; queda para el auditor como deuda candidata.

## EVIDENCIA

### Por qué la integración de F2-1 pasaba

`proptech_api/complejos.py::CuerpoDeEdicion.no_nulo` (que hereda `CuerpoEdicionGasto`) rechaza cualquier `null` en un PATCH con "el campo no admite null". El gasto del test del rompedor estaba en `borrador` (estado editable), así que el 422 lo daba la capa HTTP antes de llegar a `editar_gasto`. Por HTTP no hay forma de mandar los campos de factura en `null`, en ningún estado. El test absorbido ahora afirma el estado `borrador` y el motivo del 422.

### RED (15:53:26)

`pytest tests/unitarios/test_gastos_aplicacion.py tests/integracion/test_notas_de_credito.py -k ...` → `4 failed, 33 passed`:

```
test_no_se_quita_factura_con_notas[borrador|sin_ia|en_revision]
  AssertionError: Se permite quitar la factura con notas: [call(<TextClause>, {...})]
  assert None is not None
test_nota_devuelve_periodo_de_su_factura   (PostgreSQL)
  assert None == '2026-10-01'
```

### GREEN (15:53:52)

`ruff check src tests` limpio y `mypy` → `Success: no issues found in 365 source files`. `pytest` sobre `test_gastos_aplicacion`, `test_notas_de_credito`, `test_gastos`, `test_lectura_gastos_aprobados`, `test_regresiones_de_aislamiento_y_grupos_vacios` y `test_altas_sin_id_del_cliente` → `128 passed`. 15:54:39: el test de integración de F2-1 con la aserción del motivo → `1 passed`.

| Hallazgo | Archivo | Cambio |
|---|---|---|
| F2-1 | `gastos/aplicacion/gastos.py::editar_gasto` | Consulta lo acreditado si cambia el importe o si la edición deja vacíos los datos de factura de un gasto que los tenía. Con notas, `EntradaInvalida("factura", "no se puede quitar la factura de un gasto con notas de crédito")`. |
| S4 | `gastos/aplicacion/notas_de_credito.py::cargar_nota_de_credito` | `JOIN gasto` por id y `administracion_id`; suma `periodo_de_la_factura`. Aditivo. |

### Mutantes (revertidos, `cmp` → `RESTAURADO`)

| Mutante | Hora | Resultado |
|---|---|---|
| M4: el rechazo de factura con notas no se dispara nunca | 15:54:57 | 3 rojos `assert None is not None` |
| M5: lo acreditado sólo se consulta si cambia el importe (el código de antes) | 15:54:59 | 3 rojos `assert None is not None` |
| M6: `periodo_de_la_factura` devuelve el período de la nota | 15:55:01 | 1 rojo `assert '2026-11-01' == '2026-10-01'` |

GREEN después de revertir, 15:55:09: `65 passed` (`test_gastos_aplicacion` + `test_notas_de_credito`).

### Chequeos

Desde `backend/`:

- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `402 files already formatted`
- `uv run mypy` → `Success: no issues found in 365 source files`
- `alembic heads` → `0033 (head)`
- Enfocados, 16:14:38: `test_fronteras_de_modulos.py` + `test_gastos_aplicacion.py` → `102 passed`.

**Suite completa: por decisión de Juani (30/10/2026) no se corre en este intento; la corre el auditor final.** La instrucción llegó cuando ya había terminado una corrida lanzada antes, en clon normal sobre `f432055` (15:55:34 a 16:14:27): `4703 passed, 1 xfailed`. La dejo como dato, sin valor de cierre.

## JUICIO

Autor: role-constructor. Confianza: alta.

- **F2-1** no se alcanza por HTTP hoy. Igual es una falla real del caso de uso: si otra capa lo llamara (worker, importación, un cuerpo futuro que acepte `null`), dejaría notas sin factura, que es lo que la spec prohíbe. El guardia ahora vive en el caso de uso, no sólo en la capa HTTP.
- **S4**: elegí `periodo_de_la_factura` porque la spec no nombra el campo. Si el auditor o el cambio 7 prefieren otro nombre, el cambio es de una línea.

## SUPOSICIÓN

- No hay test de integración de F2-1 que llegue al caso de uso con datos de factura en `null`, porque la capa HTTP no lo permite. El guardia está probado con dobles (unitario), sin PostgreSQL.
- No corrí `shellcheck` ni `ensayo-roles.sh`; este intento no los tocó. No hice push.

## Fuentes leídas

- `informes/verify-2-breaker.md` (los hallazgos que resumió el orquestador) y los dos archivos de reproducción del rompedor 2.
- `proptech_api/gastos.py` (`CuerpoEdicionGasto`), `proptech_api/complejos.py` (`CuerpoDeEdicion`), `gastos/aplicacion/{gastos,notas_de_credito}.py`.
- El requisito de la spec de notas de crédito "Una nota de crédito nunca reabre un período ya emitido".

## Contaminación

Partí de las reproducciones del rompedor 2 y del resumen del orquestador, que eran la entrada de esta corrección. Antes de corregir averigüé por mi cuenta por qué pasaba el test de integración. No leí otros informes.
