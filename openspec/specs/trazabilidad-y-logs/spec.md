# trazabilidad-y-logs Specification

## Purpose
Define cómo se reconstruye la historia de un pedido: el formato de los logs, qué campos pueden
aparecer y cuáles nunca, y cómo el número de seguimiento (`request_id`) viaja de la web a la API, a
la base y al worker.

## Requirements

### Requirement: Logs en JSON con una lista cerrada de campos

La API y el worker SHALL escribir sus logs en la salida estándar, una línea JSON por evento, con los
campos `ts` (UTC, ISO 8601 con milisegundos), `nivel`, `servicio`, `logger`, `evento` y, cuando
exista, `request_id`. Cualquier otro campo MUST pertenecer a una lista cerrada definida en el diseño;
un campo fuera de la lista MUST descartarse y contarse en `campos_descartados`. Una línea de log
MUST NOT romperse en varias líneas aunque un valor contenga saltos de línea.

**Excepción conocida**: antes del `on_startup` del worker, mientras ARQ todavía tiene su propio
handler (el que `configurar_logs` reemplaza), escribe dos líneas fijas sin este formato: el conteo de
funciones registradas y las estadísticas de la conexión a Redis. Ninguna de las dos lleva datos de un
trabajo ni de un pedido; son del arranque de la biblioteca, antes de que el formato propio exista.

#### Scenario: Línea de un pedido atendido

- **WHEN** la API atiende `GET /api/salud`
- **THEN** escribe una línea JSON con `evento` "pedido_atendido", método, ruta, código de estado,
  duración en milisegundos y el `request_id` del pedido

#### Scenario: Campo no permitido

- **WHEN** el código intenta loguear un campo `email`
- **THEN** la línea no contiene ese campo y `campos_descartados` vale 1

#### Scenario: Las migraciones no apagan los logs

- **WHEN** un proceso que ya configuró sus logs corre las migraciones de Alembic
- **THEN** los loggers creados antes de las migraciones siguen escribiendo sus líneas JSON

### Requirement: Lo que nunca se loguea

Los logs MUST NOT contener cuerpos de pedidos o respuestas, query strings, encabezados (salvo el
`request_id`), cookies, tokens, contraseñas, cadenas de conexión, el texto de los mensajes de
excepción, los argumentos interpolados de un mensaje ni los argumentos o el resultado de un trabajo
del worker. Esto vale también para los errores de las
bibliotecas de terceros (el cliente de Redis, ARQ, psycopg y SQLAlchemy): su texto MUST NOT llegar a
un log, a un mensaje de error propio ni a una respuesta sin un test que pruebe que no repite la
entrada. Ante un error inesperado, el log MUST registrar el tipo de error y la ubicación en el código,
y la respuesta MUST ser 500 con sólo un código de error y el `request_id`. Un mensaje de log que ya
llega como un traceback formateado en texto MUST registrarse con el evento fijo
`traceback_crudo_descartado`, `tipo_error` igual a `desconocido` y `traza` vacía, sin extraer ningún
dato de ese texto. Un mensaje que no es exactamente texto (tampoco una subclase de texto) MUST
registrarse con un evento fijo y nunca con su representación de texto: si es una excepción,
`excepcion_como_mensaje`, con el tipo y la traza tomados del objeto; si es cualquier otro objeto,
`mensaje_no_texto`.

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

#### Scenario: Error de un tercero con datos en su mensaje

- **WHEN** el cliente de Redis, ARQ o psycopg lanzan un error cuyo mensaje contiene un marcador (como
  un host, un parámetro de SQL o el contenido de un trabajo)
- **THEN** el marcador no aparece en ninguna línea de log, ni en el mensaje de "cola no disponible",
  ni en el error de arranque del worker, ni en la respuesta de la API

#### Scenario: Argumentos y resultado de un trabajo

- **WHEN** el worker ejecuta un trabajo encolado con un argumento que contiene un marcador y la tarea
  devuelve un resultado con otro marcador
- **THEN** ninguno de los dos marcadores aparece en ninguna línea de log del worker, incluidas las que
  escribe ARQ

#### Scenario: Traceback crudo con datos en su texto

- **WHEN** se loguea como mensaje un traceback ya formateado en texto que lleva un marcador en el
  nombre de la excepción, en una línea `File "..."` o en el mensaje de la excepción
- **THEN** la línea tiene `evento` igual a `traceback_crudo_descartado`, `tipo_error` igual a
  `desconocido` y `traza` vacía, y el marcador no aparece en ninguna parte de la línea

#### Scenario: Mensaje que no es texto

- **WHEN** se loguea como mensaje un objeto que no es una excepción (o una subclase de texto) cuya
  representación de texto devuelve un marcador
- **THEN** la línea tiene `evento` igual a `mensaje_no_texto` y el marcador no aparece en ninguna parte
  de la línea

### Requirement: Logs de error del proxy sin query string ni encabezados

Los logs del proxy SHALL omitir la URI con su query string y los encabezados del pedido, también en
los registros de error (por ejemplo, cuando la API o la web no responden). El proxy MUST NOT tener log
de acceso.

#### Scenario: Error del proxy con un dato en la query

- **WHEN** llega a través del proxy un pedido con `?email=vecino@ejemplo.invalid` y una cookie marcada,
  y el proxy registra un error porque el servicio de destino no responde
- **THEN** ninguna línea del log del proxy contiene `vecino@ejemplo.invalid`, `email=` ni la cookie

### Requirement: Número de seguimiento validado

Un `request_id` válido SHALL ser un UUID en su forma canónica de 36 caracteres (`8-4-4-4-12`, sólo
dígitos ASCII y letras `a-f` o `A-F`). Todo componente que recibe uno MUST validarlo con coincidencia
completa sobre el texto entero y sólo con caracteres ASCII, antes de cualquier normalización; si falta
o es inválido, MUST generar uno nuevo en lugar de propagarlo. Un valor válido se normaliza a
minúsculas después de validarlo. La API y la web MUST aceptar y rechazar exactamente los mismos
valores, probados con una sola tabla de casos compartida.

#### Scenario: Pedido sin número de seguimiento

- **WHEN** la API recibe un pedido sin `X-Request-ID`
- **THEN** genera un UUID, lo usa en sus logs y lo devuelve en el encabezado `X-Request-ID` de la
  respuesta

#### Scenario: Número de seguimiento malicioso

- **WHEN** la API recibe `X-Request-ID` con un valor que no es UUID (texto largo, saltos de línea,
  `<script>`, comillas o una inyección SQL)
- **THEN** lo descarta, genera uno nuevo, lo devuelve en la respuesta y ninguna línea de log contiene
  el valor recibido

#### Scenario: UUID con espacios, tabulaciones, saltos de línea o dígitos no ASCII

- **WHEN** llega un UUID válido con un espacio o una tabulación alrededor, con un salto de línea al
  principio o al final, o con uno de sus dígitos reemplazado por un dígito de otro alfabeto o una letra
  de ancho completo
- **THEN** se rechaza y se genera uno nuevo; nunca se recorta ni se normaliza para aceptarlo

#### Scenario: UUID en mayúsculas

- **WHEN** llega un UUID canónico escrito en mayúsculas
- **THEN** se acepta y se propaga en minúsculas

#### Scenario: Mismos casos en la web y en la API

- **WHEN** corren los tests de validación del `request_id` de la API y de la web
- **THEN** los dos leen la misma tabla de casos y dan el mismo resultado para cada entrada

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

### Requirement: Contrato de respuesta de /salud-web

`GET /salud-web` SHALL responder siempre con `Content-Type: application/json` y un cuerpo con
exactamente dos campos: `web`, que vale `"ok"`, y `api`, que vale uno de `"ok"`, `"degradado"`,
`"sin_conexion"` o `"sin_configurar"`. El código de estado MUST ser 200 sólo cuando `api` vale `"ok"`,
y 503 en cualquier otro caso. El valor de `api` MUST derivarse sólo del código de estado de la
respuesta de la API (200 es `"ok"`, cualquier otro código es `"degradado"`), sin interpretar su cuerpo;
si la API no contesta dentro de 2 segundos o la conexión falla, es `"sin_conexion"`; si falta la
dirección interna de la API, es `"sin_configurar"`. La respuesta MUST llevar en `X-Request-ID` el mismo
número de seguimiento que se reenvió a la API, y MUST NOT incluir texto de errores, direcciones
internas ni el cuerpo de la respuesta de la API.

#### Scenario: API saludable

- **WHEN** la API responde 200 a la consulta de salud
- **THEN** `/salud-web` responde 200 con exactamente `{"web": "ok", "api": "ok"}`, `Content-Type`
  JSON y en `X-Request-ID` el mismo valor que se reenvió a la API

#### Scenario: API degradada

- **WHEN** la API responde 503
- **THEN** `/salud-web` responde 503 con `{"web": "ok", "api": "degradado"}`

#### Scenario: API con un error inesperado

- **WHEN** la API responde 500 o cualquier código distinto de 200 y 503, con el cuerpo que sea
- **THEN** `/salud-web` responde 503 con `{"web": "ok", "api": "degradado"}` y el cuerpo de la API no
  aparece en la respuesta

#### Scenario: Conexión rechazada

- **WHEN** la conexión con la API se rechaza al instante
- **THEN** `/salud-web` responde 503 con `{"web": "ok", "api": "sin_conexion"}`

#### Scenario: API que no contesta

- **WHEN** la API acepta la conexión y no contesta
- **THEN** `/salud-web` corta a los 2 segundos y responde 503 con `{"web": "ok", "api": "sin_conexion"}`

#### Scenario: Sin dirección de la API

- **WHEN** la web corre sin `PROPTECH_URL_API_INTERNA`
- **THEN** `/salud-web` responde 503 con `{"web": "ok", "api": "sin_configurar"}` sin intentar ninguna
  conexión

#### Scenario: Error con datos en su mensaje

- **WHEN** la consulta a la API falla con un error cuyo mensaje contiene un marcador (como la dirección
  interna)
- **THEN** el marcador no aparece en la respuesta de `/salud-web`
