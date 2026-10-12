## Purpose

Define cómo se reconstruye la historia de un pedido: el formato de los logs, qué campos pueden
aparecer y cuáles nunca, y cómo el número de seguimiento (`request_id`) viaja de la web a la API, a
la base y al worker.

## ADDED Requirements

### Requirement: Logs en JSON con una lista cerrada de campos

La API y el worker SHALL escribir sus logs en la salida estándar, una línea JSON por evento, con los
campos `ts` (UTC, ISO 8601 con milisegundos), `nivel`, `servicio`, `logger`, `evento` y, cuando
exista, `request_id`. Cualquier otro campo MUST pertenecer a una lista cerrada definida en el diseño;
un campo fuera de la lista MUST descartarse y contarse en `campos_descartados`. Una línea de log
MUST NOT romperse en varias líneas aunque un valor contenga saltos de línea.

#### Scenario: Línea de un pedido atendido

- **WHEN** la API atiende `GET /api/salud`
- **THEN** escribe una línea JSON con `evento` "pedido_atendido", método, ruta, código de estado,
  duración en milisegundos y el `request_id` del pedido

#### Scenario: Campo no permitido

- **WHEN** el código intenta loguear un campo `email`
- **THEN** la línea no contiene ese campo y `campos_descartados` vale 1

### Requirement: Lo que nunca se loguea

Los logs MUST NOT contener cuerpos de pedidos o respuestas, query strings, encabezados (salvo el
`request_id`), cookies, tokens, contraseñas, cadenas de conexión, el texto de los mensajes de
excepción ni los argumentos interpolados de un mensaje. Ante un error inesperado, el log MUST
registrar el tipo de error y la ubicación en el código, y la respuesta MUST ser 500 con sólo un
código de error y el `request_id`.

#### Scenario: Query string con un dato personal

- **WHEN** llega `GET /api/salud?email=vecino@ejemplo.invalid`
- **THEN** ninguna línea de log contiene `vecino@ejemplo.invalid` ni el texto `email=`

#### Scenario: Mensaje con argumentos

- **WHEN** el código loguea un mensaje con un argumento interpolado que contiene un dato personal
- **THEN** la línea contiene la plantilla del mensaje y no el dato

#### Scenario: Error inesperado

- **WHEN** un endpoint lanza una excepción cuyo mensaje contiene un dato personal
- **THEN** la respuesta es 500 con `{"error": "interno", "request_id": "<id>"}`, el log registra el
  tipo de error con nivel de error y ni la respuesta ni el log contienen el mensaje de la excepción

### Requirement: Número de seguimiento validado

Un `request_id` válido SHALL ser un UUID en su forma canónica de 36 caracteres. Todo componente que
recibe uno MUST validarlo; si falta o es inválido, MUST generar uno nuevo en lugar de propagarlo. Se
normaliza a minúsculas.

#### Scenario: Pedido sin número de seguimiento

- **WHEN** la API recibe un pedido sin `X-Request-ID`
- **THEN** genera un UUID, lo usa en sus logs y lo devuelve en el encabezado `X-Request-ID` de la
  respuesta

#### Scenario: Número de seguimiento malicioso

- **WHEN** la API recibe `X-Request-ID` con un valor que no es UUID (texto largo, saltos de línea,
  `<script>`, comillas o una inyección SQL)
- **THEN** lo descarta, genera uno nuevo, lo devuelve en la respuesta y ninguna línea de log contiene
  el valor recibido

### Requirement: El número de seguimiento viaja por cada salto

El proxy SHALL asignar a todo pedido que llega de Internet un `request_id` nuevo, pisando el que el
cliente haya mandado, y devolverlo en la respuesta. La web MUST reenviarlo a la API en sus llamadas
del lado del servidor. La API MUST anotarlo en la sesión de PostgreSQL de cada transacción de modo que
aparezca en los logs de la base y no quede pegado a la conexión para el pedido siguiente. Al encolar
un trabajo, la API MUST pasarlo con el trabajo, y el worker MUST usarlo en sus logs y en su sesión de
PostgreSQL.

#### Scenario: Cliente que manda su propio número

- **WHEN** un cliente hace `GET /api/salud` a través del proxy con `X-Request-ID` igual a un UUID que
  eligió
- **THEN** la respuesta trae un `X-Request-ID` distinto, generado por el proxy, y es el que aparece en
  el log de la API

#### Scenario: De la web a la API

- **WHEN** se hace `GET /salud-web` a través del proxy
- **THEN** la respuesta trae un `X-Request-ID` y el log de la API registra la llamada de la web con
  ese mismo valor

#### Scenario: En la sesión de la base

- **WHEN** dentro de un pedido con `request_id` R se abre una transacción y se consulta el nombre de
  aplicación de la sesión
- **THEN** el nombre de aplicación contiene R; y en la transacción siguiente de la misma conexión,
  fuera de ese pedido, ya no lo contiene

#### Scenario: Hasta el worker

- **WHEN** un pedido con `request_id` R encola la tarea de prueba y el worker la ejecuta
- **THEN** las líneas de log del worker para ese trabajo llevan R y la base registra la clave con R

### Requirement: Ruta técnica de la web que llama a la API

La web SHALL exponer `GET /salud-web`, sin interfaz, que responde JSON con el estado de la web y el
estado informado por la API, consultándola con un límite de 2 segundos. Si la API no responde o
responde con error, MUST contestar igual, con la API marcada como sin conexión, sin colgarse y sin
detalles internos.

#### Scenario: API caída o colgada

- **WHEN** la API está detenida o no responde y se hace `GET /salud-web`
- **THEN** la respuesta llega en menos de 3 segundos con la API marcada como sin conexión
