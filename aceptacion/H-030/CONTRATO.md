# Contrato que asume la aceptación de H-030

Caja negra por la API real, con la identidad inyectada como en H-027. Si el constructor necesita cambiar algo de
esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-030), D-168 y R32.

## Quién puede

Acción nueva `registrar_cambio_de_titular` en `Accion` y en `_MATRIZ`: super admin y administrador (principal y por
edificio). Contador, auxiliar, consejo y vecinos no. Vocabulario de auditoría con su migración (sube y baja).
Orden de chequeo (D7): edificio fuera del alcance, otra administración o unidad que no es del edificio, **404**
`{"detail": "no encontrado"}`; sin permiso, **403** con `permiso_faltante` `registrar_cambio_de_titular`; después, 422.
`GET` de la lista: la aceptación sólo fija el 404 fuera de alcance (el permiso de lectura queda a decidir).

## `POST /api/complejos/{complejo_id}/unidades/{unidad_id}/cambios-de-titular`

Cuerpo: `{"fecha": "AAAA-MM-DD", "vendedores": [persona_id, ...], "compradores": [{"nombre": str, "email": str|null}, ...]}`,
más `expensa_del_mes` (por defecto `"entera"`) y `deuda_previa` (por defecto `"en_la_unidad"`). En H-030 sólo se
aceptan esos valores (los otros los habilitan H-031 y H-032). La aceptación manda los defaults, ausentes o dichos.

**201** con: `id, unidad_id, fecha, vendedores` (ids de persona), `compradores` (`nombre`, `email`, `persona_id`, en el
orden pedido), `expensa_del_mes`, `deuda_previa`, `registrado_por` (persona de la identidad), `registrado_en`
(instante ISO) y `aviso`: `null` o `{"deuda": "1234.56"}` (texto con dos decimales, nunca número).

`aviso.deuda` es la `deuda` de `estado_de_cuenta` de la cuenta de la unidad (capital más interés registrado,
imputado); sin cuenta o sin deuda, `null`. Nunca bloquea.

**422** si: un vendedor no es propietario actual de la unidad (inquilino, de otra unidad o inexistente), un vendedor
repetido, `vendedores` o `compradores` vacíos, la misma persona de los dos lados (el comprador resuelve, por email, a
un vendedor) o la fecha es posterior a hoy. Todo en una transacción: un pedido que falla no deja persona nueva,
fila, asignaciones cambiadas ni auditoría.

## Efecto

- Los vendedores pierden su asignación `vecino` / `propietario` de la unidad (sus otras unidades y su persona quedan).
- Los compradores la ganan, sin invitación: persona reutilizada si ya existe en la administración con ese email
  (`asegurar_persona`, sin renombrar), nueva si no (sin email, siempre nueva).
- Los inquilinos y las otras unidades no se tocan. Con los defaults el libro no cambia (`movimiento`,
  `imputacion`, `obligacion`, `cuenta` y `emision` idénticos).

## Tabla `cambio_de_titular`

De sólo agregar (`UPDATE` y `DELETE` de `proptech_app` fallan por falta de permiso, como las del libro) y con RLS
habilitada y forzada. Columnas que la aceptación lee: `administracion_id`, `id`, `unidad_id`, `fecha`,
`expensa_del_mes`, `deuda_previa`; el resto (`complejo_id`, vendedores, compradores, `registrado_por`,
`registrado_en`) las decide el constructor.

## Auditoría

Evento `registrar_cambio_de_titular` (una fila por cambio): `entidad` = `cambio_de_titular`, `entidad_id` = el id del
cambio, `persona_id` = quien lo registró y `detalle` exactamente
`{"unidad_id", "fecha", "expensa_del_mes", "deuda_previa"}` (sin nombres ni emails de las personas).

## `GET .../cambios-de-titular`

**200** con la lista de los cambios de esa unidad (no de otras), el más nuevo primero; `[]` si no hay. Cada elemento
trae las claves del POST (`aviso` puede faltar o ser `null`: es de la respuesta del registro).
