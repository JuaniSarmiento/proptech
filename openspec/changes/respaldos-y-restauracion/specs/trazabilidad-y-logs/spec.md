## MODIFIED Requirements

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
