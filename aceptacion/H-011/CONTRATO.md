# Contrato que asume la aceptación de H-011

La aceptación de H-011 (`aceptacion/H-011/tests/` y `aceptacion/H-011/e2e/`) es de caja negra: entra por la
API real y por el navegador; los datos de partida se cargan por SQL con el rol de la app (como los dejaría
el 6) y las emisiones previas con `registrar_emision` y `anular_emision` del libro. Si el constructor
necesita cambiar algo de esta lista, frena y lo pide: cambiarlo obliga a congelar otra aceptación.

Fuente: `HISTORIAS.md` (H-011), `openspec/changes/liquidacion-y-emision/design.md` (E1 a E16 en su
recomendación), la spec `preliquidacion` y D-157.

## La ruta

### `GET /api/complejos/{complejo_id}/periodos/{periodo}/preliquidacion`

- `periodo`: fecha ISO con día 1 (`2026-11-01`). Otro día, un mes imposible o un texto → **422** (nunca
  500).
- Orden de chequeo: edificio inexistente o fuera de alcance → **404** `{"detail": "no encontrado"}`
  (también el administrador de otro edificio y otra administración); sin el permiso
  `cargar_gastos_y_preparar_liquidacion` → **403** con el cuerpo de siempre (`"permiso_faltante":
  "cargar_gastos_y_preparar_liquidacion"`); sin sesión → **401**; período inválido → 422; orden de
  períodos → 409.
- **409** `{"detail": "conflicto", "campo": "periodo", "motivo": "<motivo>"}` con `motivo`:
  - `periodo_emitido`: el período tiene una emisión sin anular.
  - `periodo_anterior_sin_emitir`: hay al menos una emisión sin anular en el edificio y el mes anterior al
    período no tiene una emisión sin anular.
  - El primer período del edificio (ninguna emisión sin anular) siempre se puede preliquidar.
  - "Emitido" se lee del libro (`emision` sin evento `anulada`), no de tablas nuevas.
- **200** con este cuerpo (los montos, texto con dos decimales; nunca números):

```json
{
  "complejo_id": "<uuid>",
  "periodo": "2026-11-01",
  "vencimiento": "2026-11-10",
  "porcentaje_fondo": "5.00",
  "huella": "<64 hexadecimales en minúscula>",
  "totales": {
    "gastos": "190000.00",
    "notas_de_credito": "10000.00",
    "fondo_de_reserva": "6500.00",
    "prorrateado": "186500.00",
    "cargos_particulares": "5000.00",
    "intereses": "0.00",
    "total": "191500.00"
  },
  "bloques": {
    "ordinario": {
      "subtotal": "130000.00",
      "categorias": [{"categoria_id": "<uuid>", "nombre": "Limpieza", "importe": "90000.00", "porcentaje": "69.23"}]
    },
    "extraordinario": {"subtotal": "50000.00", "categorias": [...]}
  },
  "grupos": [
    {"grupo_id": "<uuid>", "nombre": "Generales", "metodo": "coeficiente",
     "ordinario": "90000.00", "extraordinario": "50000.00"}
  ],
  "unidades": [
    {
      "unidad_id": "<uuid>",
      "identificador": "1A",
      "ordinaria": "27000.00",
      "fondo_de_reserva": "1350.00",
      "extraordinaria": "15000.00",
      "cargos_particulares": [{"concepto": "Multa", "importe": "5000.00"}],
      "intereses": "0.00",
      "total": "43350.00",
      "sin_obligacion": false,
      "por_grupo": [{"grupo_id": "<uuid>", "ordinaria": "27000.00", "extraordinaria": "15000.00"}]
    }
  ],
  "controles": []
}
```

- `unidades`: **todas** las unidades del edificio, en orden natural del identificador (R07, D-118).
- `ordinaria` de la unidad es la **ordinaria prorrateada** (sin cargos ni intereses ni fondo).
- `total` = `ordinaria` + `fondo_de_reserva` + `extraordinaria` + la suma de `cargos_particulares` +
  `intereses`. `sin_obligacion` es `true` si `ordinaria` + `fondo_de_reserva` + `extraordinaria` + cargos
  da $0,00 (el interés no genera obligación).
- `por_grupo`: un elemento por cada grupo con gastos del período en el que participa la unidad; los
  grupos sin gastos no aparecen. "Generales" incluye a todas las unidades (no tiene filas en
  `grupo_unidad`, 0012).
- `totales.gastos` es la suma bruta de los gastos que entran; `notas_de_credito`, la suma de las notas
  que se restan; `prorrateado` = `gastos` − `notas_de_credito` + `fondo_de_reserva`; `total` =
  `prorrateado` + `cargos_particulares` + `intereses`, y es igual a la suma de los `total` de las unidades.
- `bloques.*.categorias`: importe neto de notas de crédito por categoría, con el **nombre actual** de la
  categoría y `porcentaje` sobre el subtotal del bloque (texto con dos decimales, medio hacia arriba).
  Los subtotales por categoría suman el subtotal del bloque.
- **Fondo**: el total del fondo es el porcentaje sobre la suma de las ordinarias prorrateadas, redondeado
  medio hacia arriba al centavo, y se reparte entre las unidades en proporción a su ordinaria prorrateada
  con `repartir` (mayor resto). Con 0% es $0,00 en todas.
- **Configuración**: el fondo y el vencimiento salen de la versión vigente el primer día del período; el
  vencimiento es el `dia_de_vencimiento` de ese mes. El interés usa la vigente a su corte (4c).
- **Interés** (`intereses` de la unidad): la suma de lo que `calcular_intereses` daría para todas las
  obligaciones de la cuenta de la unidad con el corte del período (el último día del mes anterior), igual
  al que registraría `registrar_emision` en ese momento. Una unidad sin cuenta, $0,00.
- `huella`: cambia si cambia cualquier importe, unidad, grupo, categoría, el porcentaje, el vencimiento o
  la versión de configuración; no cambia entre dos pedidos sin cambios.
- `controles`: en H-011 puede venir vacío (los llena H-012), pero la clave está.
- No escribe: ninguna fila nueva, modificada ni borrada en ninguna tabla (tampoco `auditoria`).

## Base de datos

- Migración `0040`: el índice de DBA-2 sobre `grupo_unidad (administracion_id, complejo_id, grupo_id)`
  (E16). No crea tablas en H-011. La aceptación pregunta por un índice de `grupo_unidad` cuyas primeras
  columnas sean `administracion_id, complejo_id`.

## La pantalla

- `/edificios/{id}/liquidaciones/{AAAA-MM}` (por ejemplo `/edificios/<id>/liquidaciones/2026-11`), con el
  título (`heading`) "Preliquidación de noviembre de 2026".
- Una tabla (`role=table`) con una fila por unidad (su identificador en la primera celda) y las columnas
  "Ordinaria", "Fondo de reserva", "Extraordinaria", "Cargos particulares", "Intereses" y "Total"; los
  importes con punto de miles y coma decimal (`43.350,00`). Con fondo 0% la columna "Fondo de reserva" no
  está.
- Una fila o un pie con el total de la liquidación (`191.500,00`).
- Los bloques "Ordinaria" y "Extraordinaria" con sus categorías, importe y porcentaje.
- Sin errores de axe; usable a 320 px sin scroll horizontal de la página (la tabla puede tener scroll
  propio) y con teclado.

### API falsa (`web/e2e/api-falsa.ts`)

Tiene que conocer estos edificios (todos con sesión de super admin):

| Edificio | `GET .../periodos/2026-11-01/preliquidacion` |
|---|---|
| `00000000-0000-0000-0000-000000001101` | 200 con la base de los ejemplos (los importes de C01) |
| `00000000-0000-0000-0000-000000001102` | 200 con la base y fondo 0% (`porcentaje_fondo: "0.00"`, fondo $0,00 en cada unidad) |
| `00000000-0000-0000-0000-000000001103` | 409 `periodo_anterior_sin_emitir` |

Con el 409, la pantalla muestra un mensaje que dice que falta emitir el período anterior.
