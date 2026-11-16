# Contrato que asume la aceptación de H-013

Caja negra: emitir y leer lo emitido entran por la API real; los datos de partida por SQL con el rol de la
app y las emisiones previas con el libro, como en H-011 (`aceptacion/H-011/CONTRATO.md`, que sigue
vigente, igual que el de H-012). Si el constructor necesita cambiar algo de esta lista, frena y lo pide.

Fuente: `HISTORIAS.md` (H-013), `design.md` (E2, E3, E5, E7, E8, E15) y la spec `emision-de-liquidacion`.

## Emitir

### `POST /api/complejos/{complejo_id}/periodos/{periodo}/emision`

Cuerpo:

```json
{
  "emision_id": "<uuid que elige el cliente>",
  "huella": "<la de la preliquidación revisada>",
  "alertas_aceptadas": ["gastos_en_revision"],
  "vencimiento": {"fecha": "2026-11-12", "motivo": "Feriado del 10/11"}
}
```

`alertas_aceptadas` es obligatoria (puede ser `[]`); `vencimiento` es opcional (`null` o ausente: el de
la configuración).

Orden de chequeo, y nada se escribe en ninguno de los rechazos:

1. Edificio inexistente o fuera de alcance → **404** `{"detail": "no encontrado"}`. Sin el permiso
   `emitir_y_distribuir_liquidacion` → **403** con `permiso_faltante`. Sin sesión → **401**.
2. Período o cuerpo inválido → **422** (FastAPI o `{"detail": [...]}` que nombre el campo):
   `vencimiento.motivo` faltante, en blanco o de más de 500 caracteres; `vencimiento.fecha` anterior al
   primer día del período.
3. **Replay**: el mismo `emision_id` con el mismo cuerpo devuelve la misma respuesta (200 o 201) sin
   escribir nada nuevo.
4. Orden de períodos (como la preliquidación): **409** `{"detail": "conflicto", "campo": "periodo",
   "motivo": "periodo_emitido" | "periodo_anterior_sin_emitir"}`.
5. La preliquidación recalculada **bajo el candado** (E5) tiene otra huella → **409** `{"detail":
   "conflicto", "campo": "huella", "motivo": "preliquidacion_cambio"}`.
6. Algún control **duro** activo, venga o no en `alertas_aceptadas` → **422** `{"detail":
   "control_duro", "controles": ["<codigo>", ...]}`.
7. `alertas_aceptadas` distinta del conjunto exacto de **bloqueantes** activos (falta uno, sobra uno, o
   trae una advertencia) → **409** `{"detail": "conflicto", "campo": "alertas_aceptadas", "motivo":
   "alertas_distintas"}`.
8. Aceptar al menos un bloqueante sin el permiso `aceptar_alertas_bloqueantes` → **403** con
   `"permiso_faltante": "aceptar_alertas_bloqueantes"`.

**201** con:

```json
{
  "liquidacion_id": "<uuid>",
  "emision_id": "<el del pedido>",
  "periodo": "2026-11-01",
  "vencimiento": "2026-11-10",
  "huella": "<la emitida>",
  "obligaciones": [
    {"unidad_id": "<uuid>", "identificador": "1B", "ordinaria": "32000.00",
     "fondo_de_reserva": "1350.00", "extraordinaria": "15000.00", "vencimiento": "2026-11-10"}
  ]
}
```

- Una obligación del libro por unidad con `sin_obligacion: false` en la preliquidación, ninguna para las
  otras. En el libro, `ordinaria` = ordinaria prorrateada + cargos particulares (E15).
- Todo en una transacción: liquidación, líneas, composición, alertas aceptadas, foto del saldo anterior,
  `registrar_emision` del libro y la auditoría. Toma el candado de E5 (la fila de `complejo` antes que las
  cuentas).
- Auditoría: una fila con `accion = 'emitir_y_distribuir_liquidacion'` por emisión; si se aceptó algún
  bloqueante, además una fila con `accion = 'aceptar_alertas_bloqueantes'`.
- **Aprobar un gasto** (`aprobar_gasto`, su ruta del 6) toma el mismo candado y usa el adaptador real de
  `es_periodo_emitido`: un gasto de un período ya emitido pasa al primer período sin emitir (P36).

## Leer lo emitido

### `GET /api/complejos/{complejo_id}/liquidaciones/{liquidacion_id}`

Permiso nuevo `ver_liquidaciones` (super admin, administrador principal y de edificio, contador; el
consejo con la regla de P39 que construye H-014; auxiliar y vecinos no). 404 si no existe o es de otro
edificio. **200**: lo **guardado** al emitir, nunca recalculado:

```json
{
  "liquidacion_id": "<uuid>", "emision_id": "<uuid>", "periodo": "2026-11-01", "estado": "emitida",
  "huella": "...", "version_de_configuracion_id": "<uuid>", "porcentaje_fondo": "5.00",
  "vencimiento": "2026-11-12", "vencimiento_original": "2026-11-10",
  "motivo_del_vencimiento": "Feriado del 10/11",
  "emitida_por": "<persona_id>", "emitida_en": "<instante ISO>",
  "totales": {...como la preliquidación...},
  "bloques": {...como la preliquidación, con el nombre de la categoría al emitir...},
  "grupos": [{"grupo_id", "nombre", "metodo", "ordinario", "extraordinario",
              "composicion": [{"unidad_id": "<uuid>", "coeficiente": "0.625000"}]}],
  "unidades": [{...como la preliquidación..., "saldo_anterior": "102100.00"}],
  "alertas_aceptadas": [{"codigo": "gastos_en_revision", "aceptada_por": "<persona_id>",
                         "aceptada_en": "<instante ISO>"}]
}
```

- `vencimiento_original` y `motivo_del_vencimiento` son `null` si no se corrió.
- `composicion`: por cada grupo con gastos del período, las unidades y el **coeficiente efectivo usado**
  con seis decimales (Generales: el de cada unidad dividido por la suma; un grupo renormalizado: el
  general sobre la suma de los del grupo; por superficie o en partes iguales: la fracción usada).
- `saldo_anterior` de cada unidad: la foto `EmisionRegistrada.saldo_anterior` de su cuenta, tomada bajo
  el candado al emitir; `"0.00"` si la unidad no tiene cuenta. Es lo que devolvía
  `cuenta_corriente.aplicacion.lecturas.saldo_anterior(emision_id, cuenta)` en ese instante.
- Renombrar una categoría, cambiar el fondo o cobrarle a una unidad después no cambia nada de esta
  respuesta.

## Base de datos

Una sola migración nueva, la `0041`, con las tablas de E2 y el permiso `ver_liquidaciones`, todas de sólo agregar y protegidas (L-064, L-083:
ensayo de roles, `_DUENO_DE_TABLA`, tablas protegidas, barrido de migraciones). La aceptación no fija sus
nombres: lee todo por la API. Sí exige que la migración nueva tenga su ciclo (sube, baja y vuelve a subir).
El permiso nuevo `ver_liquidaciones` entra en el vocabulario de acciones con su migración.

## La pantalla

En `/edificios/{id}/liquidaciones/{AAAA-MM}` (H-011), un botón "Emitir liquidación":

- Abre una confirmación (`role=dialog` o `alertdialog`) que dice "no se deshace" o equivalente con el
  período y el total.
- Si hay bloqueantes, cada uno aparece con una casilla "Acepto <mensaje>" y "Confirmar" queda
  deshabilitado hasta marcarlas todas. Los duros no tienen casilla; con un duro activo, el botón "Emitir
  liquidación" está deshabilitado.
- La confirmación muestra el total de la liquidación con punto de miles (`191.500,00`).
- Ofrece una casilla "Correr el vencimiento" que, marcada, muestra los campos "Nuevo vencimiento" (fecha
  ISO en un `input type=date`) y "Motivo"; se mandan como `vencimiento: {fecha, motivo}`.
- Al confirmar, manda `POST .../emision` con un `emision_id` nuevo, la huella mostrada y las alertas
  marcadas; al volver 201 muestra una región "Liquidación emitida" con el período y el total.

### API falsa

| Edificio | Preliquidación de 2026-11-01 | `POST .../emision` |
|---|---|---|
| `00000000-0000-0000-0000-000000001101` | (H-011) sin controles | 201 con la base |
| `00000000-0000-0000-0000-000000001201` | (H-012) un duro, un bloqueante y una advertencia | (no se llama) |
| `00000000-0000-0000-0000-000000001301` | la base con sólo `gastos_en_revision` (bloqueante, "Hay 1 factura leída con alertas") y `gastos_sin_ia` (advertencia) | 201 |

La API falsa guarda la última escritura en `/api/__debug/ultima-escritura` como en los e2e anteriores.
