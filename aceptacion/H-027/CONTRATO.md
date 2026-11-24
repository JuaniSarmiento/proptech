# Contrato que asume la aceptación de H-027

Caja negra por la API real, con la identidad inyectada como en H-018 a H-026. Si el constructor necesita
cambiar algo de esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-027), `openspec/changes/morosidad/design.md` (E1 a E7), R20, R30, D-106, D-143 y los
acuerdos del 24/11/2026 (D-167).

## El día de hoy

`proptech_api.morosidad.hoy` es una dependencia de FastAPI sin parámetros que devuelve la fecha de hoy en
Mendoza (`date`). La ruta la usa como fecha de clasificación; la aceptación la reemplaza por el 18/11/2026 con
`app.dependency_overrides` (L-090).

## Quién puede

Acción nueva `ver_morosidad` en `Accion` y en `_MATRIZ`: super admin, administrador principal y por
edificio, contador principal y por edificio, auxiliar y consejo. Es también vocabulario de auditoría: una
migración la suma a `accion_de_auditoria` (sube y baja como `0028`). Leer no se audita.

Orden de chequeo (D7): el edificio fuera del alcance de la persona, o de otra administración, da **404**
`{"detail": "no encontrado"}`; sin `ver_morosidad` en ese edificio, **403** con `detail` `{"codigo":
"sin_permiso", "detalle": "sin_permiso", "permiso_faltante": "ver_morosidad"}`.

## `GET /api/complejos/{id}/morosidad`

Sin parámetros. **200**:

```json
{
  "fecha": "2026-11-18",
  "intereses_al": "2026-10-31",
  "resumen": {"unidades_con_deuda": 3, "morosos_criticos": 1, "total_vencido": "71234.56"},
  "unidades": [
    {"unidad_id": "<uuid>", "unidad": "1A", "propietarios": ["Ana Prueba"], "etiqueta": "moroso_critico",
     "total_vencido": "30812.34", "capital": "30000.00", "intereses": "812.34", "liquidaciones_vencidas": 3,
     "vencida_desde": "2026-09-10", "dias": 69}
  ]
}
```

- Cada fila trae **exactamente** esas diez claves. Montos como texto con dos decimales (`^-?[0-9]+\.[0-9]{2}$`).
- **Qué filas**: una por cuenta de unidad del edificio con `total_vencido` mayor que cero a `fecha`, según
  `situacion_del_edificio` (R20, R30): mismas etiquetas (`moroso_critico`, `con_deuda_vencida`,
  `deuda_de_intereses`, `bajo_umbral`) y mismo total vencido. Las de `sin_deuda_vencida` no aparecen.
- **`capital` e `intereses`**: el residual de capital (todo componente que no es interés) y de interés de las
  obligaciones vencidas que cuentan; `total_vencido = capital + intereses`. El interés es el registrado en el
  libro (no se estima el corrido desde el último corte).
- **`vencida_desde`**: el vencimiento de la obligación vencida más vieja con residual mayor que cero en
  cualquier componente; `dias` = `fecha` − `vencida_desde`, en días.
- **`propietarios`**: los nombres de las personas con asignación de vecino `propietario` en esa unidad,
  ordenados alfabéticamente; vacía si no hay. Nunca inquilinos, emails, teléfonos ni documentos.
- **`unidad`**: el identificador de la unidad.
- **Orden**: primero las `moroso_critico`; dentro de cada grupo, `total_vencido` descendente y, ante empate, el
  identificador ascendente.
- **`resumen`**: `unidades_con_deuda` = cantidad de filas; `morosos_criticos` = filas `moroso_critico`;
  `total_vencido` = suma de las filas.
- **`intereses_al`**: el `corte` más reciente de un movimiento de interés que cuenta en las cuentas de unidad del
  edificio; `null` si no hay ninguno.
- No escribe nada: `movimiento`, `imputacion`, `obligacion` y `auditoria` quedan iguales.

## Los datos de la aceptación

Los de H-018 a H-022 (Torre Ficticia, `1A` a `2B`, 3% mensual proporcional, gracia 0, umbral $500), con las
emisiones de septiembre, octubre y noviembre de 2026 (vencimiento el 10 de cada mes) cargadas con
`registrar_emision` y los pagos con `registrar_credito` del libro. "Ana Prueba" es propietaria de `1A` y `2B`
(con email); "Carla Prueba", propietaria de `1B`; "Beto Prueba", inquilino de `1B`; `2A` no tiene
propietarios.
