# Contrato que asume la aceptación de H-026

Las pantallas de pagos contra la API falsa y un dato más de la API real. Siguen vigentes los contratos de H-018 a
H-025 (en especial el de H-025: rutas, etiquetas y escenarios `2501`/`2502`). Si el constructor necesita cambiar algo
de esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-026), hallazgos de la demo del 18/11/2026.

## La API real: la unidad vigente de cada parte

`GET /api/complejos/{id}/pagos` y `GET /api/complejos/{id}/pagos/{pago_id}` suman a cada elemento de `partes`:
`unidad_vigente_id` y `identificador_vigente`, la unidad donde está hoy la plata de esa parte: la misma `unidad_id` si
nunca se reimputó, la de destino de la última reimputación si sí (después de revertir, la última donde estuvo). Los
campos que ya existían no cambian.

## El menú del edificio

En `seccionesDelEdificio`, "Resumen", "Unidades", "Grupos", "Categorías" e "Intereses y vencimiento" piden la acción
`ver_configuracion_del_edificio` (como "Liquidaciones" pide `ver_liquidaciones`). Quien la tiene (el personal) los ve
igual que hoy; la vecina (`user_vecina`, sólo `informar_pago`) ve sólo "Mis pagos".

## Los montos en "Informar un pago"

El campo "Monto" y cada "Importe para <identificador>" aceptan el formato argentino: punto de miles opcional y coma
decimal opcional, con hasta dos decimales (`43350`, `43.350`, `43350,5`, `43.350,00`). Antes de mandar, la pantalla
**sólo cambia el formato** a `^[0-9]+\.[0-9]{2}$` (`43350.00`, `43350.50`): saca los puntos de miles, cambia la coma por
punto y completa con ceros a la derecha. **Nunca redondea ni calcula**: lo que no encaja (por ejemplo `43350,123`) se
manda tal cual y se muestra el 422 de la API en su campo.

## Las listas

En "Mis pagos" y en la bandeja, el motivo de un rechazo o una reversión es un elemento propio con el texto exacto
`Motivo: <motivo>`, en su renglón (nunca pegado a la unidad).

En la bandeja, una parte cuya `unidad_vigente_id` es distinta de `unidad_id` muestra el texto `Ahora en
<identificador_vigente>`. "Reimputar" manda `desde_unidad_id` = la `unidad_vigente_id` de la parte (no la original), y
el `select` "Unidad de destino" no ofrece esa unidad vigente.

## El administrador informa por el vecino

La bandeja tiene un link "Informar un pago" a `/edificios/{id}/pagos/informar`: la misma pantalla de H-025 (encabezado
"Informar un pago", las mismas etiquetas), con un "Importe para <identificador>" por cada unidad de
`GET .../pagos/unidades` (para el personal, todas). Con 201 vuelve a `/edificios/{id}/pagos`. La ruta pide
`confirmar_pago_informado` en el edificio (la vecina no la ve en el menú).

## API falsa

El escenario `00000000-0000-0000-0000-000000002501` suma un quinto pago, `...025005` (número "11110005", $10.000,00,
`confirmado`), con una parte de `1A` reimputada a `2A`: `unidad_id` `...025101`, `unidad_vigente_id` `...025103`,
`identificador_vigente` "2A". El resto de las partes de los escenarios trae `unidad_vigente_id` igual a `unidad_id`.

`POST .../pagos` de la API falsa responde **422** con `campo` `monto` (o `partes`, para un importe) cuando el monto o un
importe no cumple `^[0-9]+\.[0-9]{2}$`, antes de mirar si las partes suman.
