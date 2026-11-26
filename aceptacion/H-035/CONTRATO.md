# Contrato que asume la aceptación de H-035

Caja negra por la API real, con la identidad inyectada como en H-030 a H-033. Si el constructor necesita cambiar algo
de esto, frena y lo pide. Fuente: `HISTORIAS.md` (H-035), D-168 y R32.

## Quién puede

El permiso existente `registrar_cambio_de_titular` (matriz real: super admin, administrador principal y
administrador del edificio; contador, auxiliar, consejo y vecinos no). Sin acción nueva ni migración. Orden de chequeo
(D7): edificio fuera del alcance, de otra administración o inexistente, o unidad que no es del edificio o inexistente,
**404** `{"detail": "no encontrado"}`; sin permiso, **403** con `permiso_faltante` `registrar_cambio_de_titular`.
El 404 gana al 403 (un consejo de otro edificio recibe 404).

## `GET /api/complejos/{complejo_id}/unidades/{unidad_id}/propietarios`

**200** `{"propietarios": [{"persona_id": "...", "nombre": "..."}]}`: los propietarios actuales de la unidad
(asignación `vecino` con vínculo `propietario`), **ordenados por nombre**. Sin inquilinos ni propietarios de otras
unidades. Claves exactas: la respuesta, `propietarios`; cada elemento, `persona_id` y `nombre` (ni email, ni teléfono,
ni documento, ni asignaciones). Es una lectura: no escribe ni audita.

## Los nombres del historial (decisión del orquestador, compatible con H-030 a H-033)

Hoy `vendedores` es una lista de ids de persona y las aceptaciones de H-030 a H-032 fijan el conjunto exacto de
claves del `201` y del historial (`CLAVES_DEL_CAMBIO`, `CLAVES_DEL_TRASLADO`): sumar una clave siempre, o cambiar
`vendedores` a objetos, rompería su regresión. Por eso los nombres son **opcionales**:

- `POST .../cambios-de-titular?con_nombres=true` y `GET .../cambios-de-titular?con_nombres=true` suman a cada cambio
  `vendedores_detalle`: `[{"persona_id", "nombre"}]`, en el orden de `vendedores` y con claves exactas (sin email).
  `vendedores` sigue siendo la lista de ids. Los `compradores` ya traen `nombre` (y `email`, `persona_id`) y no cambian.
- **Sin el parámetro** las respuestas son exactamente las de hoy (sin `vendedores_detalle`).
- El nombre sale aunque la persona ya no sea propietaria de la unidad (el vendedor de un cambio viejo).
- Mismo permiso y mismo orden de chequeos que la ruta sin el parámetro.
