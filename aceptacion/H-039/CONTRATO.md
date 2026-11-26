# Contrato que asume la aceptación de H-039

Entender mi expensa: la liquidación emitida explicada para el vecino, comparada con la anterior, y la distribución al
abrirla (change 11 `portal-del-vecino`). Caja negra por la API real, con la identidad inyectada. Fuente:
`HISTORIAS.md` (H-039), D-170, D-074, D-106 y R16. Sigue vigente el contrato de H-038 (quién es "mi unidad", el 404
`{"detail": "no encontrado"}`, la fecha de `hoy`). Si el constructor necesita cambiar algo de esto, frena y lo pide. Las
claves de cada objeto son **exactamente** las listadas (los tests comparan el conjunto).

Las dos rutas viven en `proptech_api.vecino`, bajo `/api/mis-unidades/{unidad_id}`. Toda ruta por unidad da `404`
con cuerpo exacto `{"detail": "no encontrado"}` si la unidad no es de la persona (ajena, de otro edificio o
administración, inexistente, o pedida por personal sin asignación `vecino`). Además: una liquidación que no es de
**ese edificio**, que no existe, que está **anulada** o que no fue emitida da el mismo 404, aunque la unidad sea propia.
Sólo cuentan las liquidaciones emitidas y no anuladas (estado `emitida` o `distribuida`).

## `GET /api/mis-unidades/{unidad_id}/liquidaciones`

`200` con la lista de las liquidaciones emitidas y no anuladas del edificio de esa unidad, **la más nueva primero**
(por período y, dentro de uno, por cuándo se emitió). No distribuye nada y no escribe nada. Cada elemento, exactamente:

| clave | qué es |
|---|---|
| `liquidacion_id` | el id de la liquidación |
| `periodo` | `AAAA-MM-01` |
| `vencimiento` | el vencimiento de la liquidación, `AAAA-MM-DD` |
| `total` | el total de **esa unidad** en esa liquidación (la línea emitida), según su vínculo: el propietario con la extraordinaria, el inquilino sin ella (D-170.2) |

Los montos son texto Decimal con dos decimales, nunca número. Una persona sin liquidaciones emitidas recibe `[]`.

## `GET /api/mis-unidades/{unidad_id}/liquidaciones/{liquidacion_id}`

`200` con un objeto. Lee lo **guardado al emitir** (nunca recalcula: R16, E2 del 7). Claves exactas:

| clave | qué es |
|---|---|
| `liquidacion_id`, `complejo_id`, `unidad_id`, `identificador`, `periodo`, `vencimiento` | identificación (texto) |
| `vinculo` | `propietario` o `inquilino`, el de la persona sobre esa unidad |
| `bloques` | `{"ordinario": B, "extraordinario": B}` con `B = {"subtotal", "categorias": [{"categoria_id", "nombre", "importe", "porcentaje"}]}`: **igual, valor por valor, a `bloques` de `GET /api/complejos/{id}/liquidaciones/{liquidacion_id}` del 7** (son los gastos del edificio por categoría, netos de notas de crédito, con el nombre al emitir). El inquilino **no tiene la clave `extraordinario`** |
| `grupos` | los grupos de reparto con gastos en que participa la unidad, en el orden de `grupos` del 7: `{"grupo_id", "nombre", "ordinaria", "extraordinaria"}`, con las partes de `por_grupo` de **su** línea del 7. El inquilino recibe `{"grupo_id", "nombre", "ordinaria"}` (sin `extraordinaria`) |
| `ordinaria` | la ordinaria prorrateada de la unidad, sin cargos |
| `cargos_particulares` | `[{"concepto", "importe"}]` de **esa** unidad en esa liquidación (`[]` si no tiene) |
| `fondo_de_reserva` | su parte del fondo |
| `extraordinaria` | su parte de la extraordinaria. **Sólo el propietario**: el inquilino no recibe la clave |
| `intereses` | los intereses cobrados en esa emisión a esa unidad |
| `total` | `ordinaria` + `cargos_particulares` + `fondo_de_reserva` + `extraordinaria` + `intereses` (el inquilino, sin `extraordinaria`) |
| `comparacion` | `null` o el objeto de abajo; la clave siempre está |

**Cierra al centavo con lo emitido para la unidad**: `ordinaria` + suma de `cargos_particulares` es la `ordinaria` de
la obligación que el libro recibió para esa unidad (la respuesta de `POST .../emision` del 7, `obligaciones[]`);
`fondo_de_reserva` y `extraordinaria`, lo mismo; y `total` es el `total` de su línea en `unidades[]` del 7 (para el
propietario). Los montos de la unidad nunca son los de otra: el detalle **no trae** las claves `unidades`,
`composicion`, `alertas_aceptadas`, `emitida_por`, `huella` ni `saldo_anterior`, ni el id, el identificador o el
nombre de otra unidad o persona, ni los cargos de otra unidad.

### `comparacion`

La liquidación emitida **inmediatamente anterior del mismo edificio** (D-170.3): la más reciente, de período anterior,
que no está anulada (si el mes anterior se anuló y se volvió a emitir, es la nueva). Sin anterior, `null`. Si hay:

```json
{
  "liquidacion_id": "<la anterior>", "periodo": "2026-10-01",
  "total_anterior": "31200.00", "diferencia_total": "15300.00",
  "categorias": [{"categoria_id", "nombre", "bloque": "ordinario"|"extraordinario",
                  "importe": "100000.00", "importe_anterior": "80000.00", "diferencia": "20000.00"}]
}
```

`total_anterior` es el `total` de la línea de **esa unidad** en la anterior (según el vínculo) y `diferencia_total` =
`total` actual − `total_anterior`. `categorias` es la unión de las de las dos liquidaciones, con el importe del
edificio de cada una (`"0.00"` si no estaba) y `diferencia` = `importe` − `importe_anterior`; orden: bloque (ordinario
primero) y, dentro, el de la liquidación actual y luego las que sólo estaban en la anterior. Para el inquilino
(D-170.2): sólo categorías del bloque ordinario y su `total_anterior` sin la extraordinaria. Nunca algo extraordinario.

## La distribución al abrir (D-074, D-170.4)

La **primera lectura del detalle** de una liquidación emitida y no distribuida por cualquier vecino llama al puerto del
7, `proptech_core.liquidacion.aplicacion.distribucion.registrar_distribucion(..., origen="portal", ...)`, en la misma
transacción de la lectura. Cómo se observa, sin ruta nueva:

- `GET /api/complejos/{id}/liquidaciones/{liquidacion_id}` del 7 (como administrador): pasa de `"estado": "emitida"` a
  `"distribuida"`, con `"distribucion": {"origen": "portal", "en": ...}`.
- En la base, una sola fila `distribuida` en `evento_de_emision` para esa `emision_id`, con `origen = 'portal'`.
- `POST .../liquidaciones/{id}/anulacion` da después `409` con `motivo: "ya_distribuida"` (R08, D-016).

Reglas: sólo el detalle distribuye; la **lista no** y un 404 tampoco. Las lecturas siguientes (de la misma persona o de
otro vecino, de otra unidad) no repiten el efecto: el primero gana (mismo evento, mismo instante, mismo origen) y no
escriben nada. Una liquidación ya distribuida a mano conserva su origen `manual`. El detalle sólo toca
`evento_de_emision` (y, si el constructor lo decide, `auditoria`): ninguna otra tabla, nada del libro. Dos lecturas
simultáneas de la misma liquidación sin distribuir dan `200` las dos y **un solo** evento `distribuida`.

## Lo que no hace

No hay rutas de escritura nuevas ni cambios en las del 7 (`GET .../liquidaciones` y `.../liquidaciones/{id}` del
administrador, `POST .../distribucion` y `.../anulacion` siguen igual). Las pantallas y la app instalable son de H-040.
