# Contrato que asume la aceptación de H-037

La IA completa el borrador de H-036. Caja negra por la API real y por la tarea del worker, con la identidad inyectada y un
lector de IA falso. Fuente: `HISTORIAS.md` (H-037), D-169, R12 y R23. Si el constructor necesita cambiar algo de esto,
frena y lo pide. Ninguna prueba llama a OpenRouter. Los nombres y códigos de abajo los fija esta aceptación.

## Cómo se dispara

1. `POST /api/complejos/{id}/facturas` (H-036) **después del commit** encola con `request.app.state.cola.encolar(...)` la
   tarea `leer_factura_con_ia` con `clave` (texto no vacío, distinta por gasto, determinista), `request_id` y los datos
   `administracion_id` y `gasto_id` (ambos texto). Se encola también cuando la factura quedó `sin_qr`. **Si la cola
   falla, el 201 sale igual** y el gasto queda `borrador`; el 201 no espera a la IA y su cuerpo **no cambia** (las claves
   de H-036 siguen idénticas: su aceptación congelada fija el conjunto exacto).
2. `proptech_worker.tareas.leer_factura_con_ia(ctx, *, request_id, clave, administracion_id, gasto_id, **datos)`, con el
   patrón de `generar_pdf_de_expensa` (`con_seguimiento_de_tarea`, `con_administracion_de_tarea`, `reintentable`,
   `ejecutar_con_corte`). Devuelve `True` si trabajó y `False` si la `clave` ya estaba hecha. Lee del `ctx`
   `fabrica_de_sesiones` y `lector_de_facturas` (el puerto, o `None`/ausente si no hay IA configurada).
3. El worker arma `ctx["lector_de_facturas"]` al arrancar con el adaptador de OpenRouter (`PROPTECH_OPENROUTER_API_KEY` y
   `PROPTECH_OPENROUTER_MODELO` del 8); sin ellas, `None`. (El 8 llama al lector dentro del pedido de la API, no en el
   worker: acá hay un puerto nuevo, el del 8 sólo devuelve la propuesta de un comprobante y no el uso.)

## El puerto

`proptech_core.gastos.puertos.LectorDeFacturaConIa`, un `Protocol` con el atributo `modelo: str` y

```python
def leer(self, contenido: bytes, tipo: str, *, categorias: Sequence[Mapping[str, str]],
         grupos: Sequence[Mapping[str, str]]) -> LecturaDeIa: ...
```

`tipo` es `"image/jpeg"`, `"image/png"` o `"application/pdf"`; `contenido`, el archivo guardado tal cual. `categorias` y
`grupos` son **sólo las activas del edificio del gasto**, cada una `{"id", "nombre"}` y nada más: nunca el nombre ni el
CUIT del edificio, ni datos de personas. `LecturaDeIa` (duck typing) tiene `propuesta`, `modelo: str`,
`tokens_entrada: int`, `tokens_salida: int` y `costo: str` (dólares, decimal en texto). Puede lanzar cualquier excepción;
una excepción puede traer, opcional, `tokens_entrada`, `tokens_salida` y `costo` (lo gastado antes de fallar; ausentes
valen 0).

## La propuesta y cómo se valida

La propuesta es un objeto con **las cinco claves** `concepto`, `periodo`, `categoria_id`, `grupo_id`, `importe` (los
valores pueden ser `null`); claves de más se ignoran. Una propuesta que no es un objeto o a la que le falta alguna clave
es **fuera de contrato**: `sin_ia`, motivo `fuera_de_contrato`, no se aplica nada. Si cumple el contrato, cada campo se
valida solo y el que no sirve queda `null` y se anota en `detalle.descartados`:

| campo | se aplica si | si no, motivo |
|---|---|---|
| `concepto` | texto de 1 a 200 caracteres tras recortar, sin caracteres de control | `invalido` |
| `periodo` | texto `AAAA-MM` de un mes real; se guarda el primer día (`AAAA-MM-01`) | `invalido` |
| `categoria_id` | el id de una categoría **activa de ese edificio** | `fuera_del_vocabulario` (texto que no es uno de los ofrecidos, de otro edificio o inactiva; cualquier otro tipo, `invalido`) |
| `grupo_id` | ídem con los grupos | ídem |
| `importe` | sólo si el gasto no trae importe (`sin_qr`): texto `^[0-9]+\.[0-9]{2}$` mayor que cero | `invalido`; si el QR ya lo trajo, se ignora sin anotar |

La IA **nunca** escribe `estado`, `tipo`, `proveedor_id`, los cuatro datos de la factura, `fecha_de_factura`,
`documento_receptor`, `periodo_de_imputacion` ni `complejo_id`. No pisa un campo que ya tiene valor (lo que cargó la
persona); no toca `periodo_de_imputacion` (se fija al aprobar, D8). El texto del concepto es sólo texto: lo decide la
persona al revisar. Los valores vienen de un modelo y no son confiables.

## Estados y `GET /api/gastos/{gasto_id}/lectura`

El `estado` del gasto es el del 6 (`borrador`, `sin_ia`, `en_revision`, `aprobado`; ya existen). Tras la tarea:

| caso | `estado` | `motivo` |
|---|---|---|
| lectura buena | `borrador` | `null` |
| lector ausente o `None` (sin llamada) | `sin_ia` | `ia_no_configurada` |
| el lector lanza | `sin_ia` | `ia_fallo` |
| propuesta fuera de contrato | `sin_ia` | `fuera_de_contrato` |
| lectura buena con importe atípico (R23) | `en_revision` | `importe_atipico` |

En `sin_ia` no se aplica nada de la IA (los datos del QR quedan intactos). En `en_revision` la propuesta **sí** se aplica y
la persona la revisa; la persona puede aprobar un gasto `en_revision` o `sin_ia` completo (`POST /gastos/{id}/aprobar`).

`GET /api/gastos/{gasto_id}/lectura` devuelve exactamente `{"estado", "datos_de", "motivo", "detalle"}`:

- `datos_de`: `{"importe", "concepto", "periodo", "categoria_id", "grupo_id"}`, cada uno `"qr"`, `"ia"` o `null` (vacío o
  cargado a mano). Con un QR legible, `importe` es `"qr"` desde la subida; el resto, `null` hasta la lectura. Un campo
  descartado queda `null`. `importe` es `"ia"` sólo en un `sin_qr` cuyo importe puso la IA.
- `motivo`: el de la tabla, o `null`.
- `detalle`: `null` antes de la lectura; objeto después: `descartados` (`{campo: motivo}`, `{}` si no hay) y, en
  `importe_atipico`, `promedio` (texto con dos decimales), `muestras` (entero) e `importe` (texto con dos decimales).
- Regla de acceso: la de `GET /gastos/{id}` (`ver_configuracion_del_edificio`); **404** si el gasto no existe o no alcanza.

## Idempotencia (N03)

La tarea se identifica por `clave` (E3 del 2a: `trabajos_hechos` con la administración adelante). Misma `clave`: `False`,
sin llamar. Además, un gasto que ya tiene una llamada `ok` no se lee de nuevo aunque la `clave` sea otra; uno `aprobado`
o sin factura (cargado a mano) no se toca ni se llama a la IA. Una `clave` repetida después de una falla tampoco vuelve a
llamar ni a cobrar. La llamada, la fila de costo y el cambio del gasto se confirman juntos.

## La tabla de costo `llamada_de_ia` (C04)

Nueva, de sólo agregar (triggers de `UPDATE`, `DELETE` y `TRUNCATE`, D-115), RLS forzada por administración. Migración
`0055`. (El 8 no tiene tabla de costo: no se la reusa, no existe.) Columnas: `id`, `administracion_id`, `complejo_id`,
`gasto_id` (FK compuesta al gasto), `clave` (texto), `modelo` (texto), `tokens_entrada` y `tokens_salida` (enteros >= 0),
`costo_usd` `NUMERIC(12,6)` >= 0 (en la API siempre sale como texto), `resultado` (`ok` o `fallida`) y `creada_en`
(`timestamptz` con `now()`). Una fila por llamada al lector, buena o no; sin lector no hay llamada y no hay fila. Una
respuesta fuera de contrato es `fallida` con el uso de la respuesta; una excepción es `fallida` con el uso de la
excepción (0 si no lo trae) y el `modelo` del lector. `proptech_app` inserta y lee; no actualiza ni borra.

## R23 (C05)

R23 vigente en `05` (D-109), sin tocarla. Al cerrar la lectura buena, con el `proveedor_id` del gasto, su importe final (el
del QR o el de la IA) y su `periodo` (el que dejó la IA, primer día del mes): el promedio (media aritmética) de los gastos
**`aprobado`** de ese proveedor **en ese edificio** cuyo `periodo` cae en los **6 períodos anteriores** al del gasto
leído (para 2026-10: 2026-04 a 2026-09; el mismo mes, uno posterior o uno de hace 7 períodos no cuentan). Con **al menos
un** gasto en la ventana se compara; el importe es atípico si es **estrictamente** mayor que el doble o estrictamente
menor que la mitad del promedio (2000.00 contra 1000.00 no; 2000.01 sí; 500.00 no; 499.99 sí). Sin gastos en la ventana,
sin proveedor (una factura `sin_qr`) o sin período (la IA no lo dio), no se marca. No cuentan los borradores, `sin_ia` ni
`en_revision`, otros proveedores, el mismo CUIT en otro edificio ni el propio gasto. `detalle.muestras` es la cantidad de
gastos de la ventana. El umbral es fijo; "configurable por edificio" es deuda y no se prueba.

## Lo que no hace H-037

No tiene pantalla (6c), no llama a OpenRouter de verdad en la aceptación, no aprueba, no emite ni toca el libro
(`movimiento`, `obligacion`, `imputacion`, `emision` en cero) y no resuelve el proveedor de una factura `sin_qr`.

## Detalles que la construcción tiene que decidir y reportar

- La instrucción fija y el esquema estricto del adaptador de OpenRouter para facturas (con las mismas garantías del 8:
  ZDR, sin herramientas, salida estructurada, clave nunca en un log) y de dónde saca `costo` y los tokens.
- Los eventos de auditoría de la tarea (la aceptación no los compara) y el cota de tiempo de la tarea.
- Si las pruebas de H-036 piden la cola real sin Redis: el POST no puede fallar por eso.
