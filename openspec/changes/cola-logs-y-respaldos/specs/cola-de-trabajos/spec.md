## Purpose

Define cómo el sistema deja trabajo lento o dependiente de terceros para que lo haga un worker aparte:
cómo se encola, qué se reintenta y con qué espera, cuándo se abandona y por qué un trabajo que llega
dos veces no duplica su efecto.

## ADDED Requirements

### Requirement: Worker separado que comparte el dominio

El sistema SHALL ejecutar los trabajos encolados en un proceso worker separado de la API, construido
desde la misma imagen y el mismo código de dominio, conectado a la cola y a la base sólo por la red
interna. Su salida a Internet (que necesitan los proveedores de email e IA de cambios posteriores) MUST
ser una red propia en la que no está ningún otro servicio. El worker MUST correr sin privilegios de
root y MUST NOT publicar puertos.

#### Scenario: Worker saludable en el stack

- **WHEN** el stack está levantado
- **THEN** el servicio worker está saludable, su proceso no corre como root y no tiene puertos
  publicados hacia el host

### Requirement: Tarea de prueba

El worker SHALL tener registrada una tarea de prueba que recibe una clave de idempotencia, un número de
seguimiento y una cantidad de fallas pasajeras a simular (entre 0 y 10), y que al completarse deja
registrada su clave en la base. Ninguna ruta pública MUST permitir encolarla.

#### Scenario: Tarea de prueba exitosa

- **WHEN** se encola la tarea de prueba con una clave nueva y cero fallas simuladas
- **THEN** el worker la ejecuta en un intento y la base registra esa clave una sola vez, con su número
  de seguimiento

#### Scenario: Cantidad de fallas fuera de rango

- **WHEN** se intenta encolar la tarea de prueba con -1 u 11 fallas simuladas, o con un valor que no es
  un entero (texto, booleano o número con decimales)
- **THEN** el encolado se rechaza con un error que nombra el campo y no se encola nada

#### Scenario: Sin ruta pública para la tarea de prueba

- **WHEN** se recorren las rutas registradas en la API
- **THEN** ninguna permite encolar la tarea de prueba; sólo se encola desde código o desde el comando
  dentro del contenedor

### Requirement: Reintentos espaciados sólo para errores pasajeros

Un trabajo que falla por un error pasajero (dependencia caída, que no responde o lenta más allá de su
límite) SHALL reintentarse con una espera que se duplica en cada intento, partiendo de 2 segundos,
hasta un máximo de 5 intentos en total. Un trabajo que falla por cualquier otro error MUST NOT
reintentarse. Al agotar los intentos, el trabajo MUST quedar registrado en el log como agotado, con
nivel de error, sin efecto parcial en la base.

#### Scenario: Falla pasajera y después éxito

- **WHEN** la tarea de prueba se encola con 2 fallas simuladas
- **THEN** el worker la ejecuta 3 veces, el log registra dos reintentos con esperas de 2 y 4 segundos
  (o su escala configurada en los tests) y la base registra la clave una sola vez

#### Scenario: Intentos agotados

- **WHEN** la tarea de prueba se encola con más fallas simuladas que intentos disponibles
- **THEN** el worker la ejecuta 5 veces, el último evento del log es "agotado" con nivel de error y la
  base no registra la clave

#### Scenario: Error que no es pasajero

- **WHEN** una tarea falla con un error que no es pasajero
- **THEN** el worker la ejecuta una sola vez y el log registra la falla con el tipo de error, sin
  reintento

#### Scenario: Base caída durante el trabajo

- **WHEN** la base no está disponible mientras el worker ejecuta la tarea de prueba y vuelve antes de
  agotar los intentos
- **THEN** el trabajo se reintenta como pasajero y termina registrando la clave una sola vez

### Requirement: Idempotencia de los trabajos

Ejecutar dos veces un trabajo con la misma clave de idempotencia SHALL tener el mismo efecto que
ejecutarlo una vez. La clave MUST registrarse en la base con una restricción de unicidad dentro de la
misma transacción que el efecto del trabajo, de modo que si el efecto falla tampoco queda la clave.
Encolar un trabajo con una clave que ya está en la cola MUST NOT crear un segundo trabajo.

#### Scenario: Mismo trabajo encolado dos veces

- **WHEN** se encola dos veces la tarea de prueba con la misma clave antes de que el worker la tome
- **THEN** el segundo encolado informa que ya estaba encolado y el worker la ejecuta una sola vez

#### Scenario: Trabajo ejecutado dos veces

- **WHEN** la misma tarea con la misma clave se ejecuta dos veces (por ejemplo, el worker se cayó
  después de confirmar en la base y antes de marcarla terminada en la cola)
- **THEN** la base registra la clave una sola vez y la segunda ejecución termina sin error informando
  que ya estaba hecha

#### Scenario: Dos ejecuciones simultáneas

- **WHEN** dos ejecuciones de la misma tarea con la misma clave corren al mismo tiempo
- **THEN** sólo una aplica el efecto y la otra termina informando que ya estaba hecha

#### Scenario: El efecto falla después de reservar la clave

- **WHEN** el efecto del trabajo falla dentro de la transacción después de registrar la clave
- **THEN** la clave no queda registrada y un reintento puede completar el trabajo

### Requirement: Los trabajos viajan como datos, no como código

El contenido de un trabajo en la cola SHALL serializarse como JSON. El worker MUST NOT deserializar
trabajos con un formato capaz de ejecutar código (como `pickle`). Los montos MUST viajar como texto:
`encolar` MUST aceptar sólo texto, enteros, booleanos, nulos, listas y mapas con claves de texto, y
MUST rechazar antes de tocar Redis cualquier otro valor (en particular `float` y `Decimal`, sueltos o
anidados) con un error propio que nombre el campo sin mostrar su valor.

#### Scenario: Monto como número al encolar

- **WHEN** se encola un trabajo con un argumento `float` o `Decimal`, suelto o dentro de una lista o un
  mapa
- **THEN** el encolado se rechaza con un error propio que nombra el campo (por ejemplo `montos[1]`), no
  contiene el valor y no se encola nada

#### Scenario: Trabajo encolado inspeccionado en Redis

- **WHEN** se encola la tarea de prueba y se lee el trabajo crudo guardado en Redis
- **THEN** es JSON válido y contiene los argumentos con sus nombres

#### Scenario: Trabajo con formato ajeno

- **WHEN** aparece en la cola un trabajo serializado con `pickle`
- **THEN** el worker no lo ejecuta y registra el rechazo en el log sin su contenido

### Requirement: Redis protegido y persistente

El servicio de Redis SHALL exigir contraseña (tomada del archivo de entorno, obligatoria), persistir
los trabajos en disco con `appendonly` sobre un volumen con nombre y no descartar trabajos por falta
de memoria. MUST NOT publicar ningún puerto hacia el host.

#### Scenario: Declaración del servicio Redis

- **WHEN** se lee la configuración de Compose
- **THEN** el servicio `redis` arranca con `--requirepass` desde `REDIS_PASSWORD` obligatoria,
  `--appendonly yes` y `--maxmemory-policy noeviction`, monta un volumen con nombre en `/data` y no
  declara `ports`

### Requirement: Cola que no responde

Encolar un trabajo SHALL fallar con un error propio de "cola no disponible" en a lo sumo 3 segundos
cuando Redis está caído, no responde o responde más lento que el límite. El mensaje de ese error MUST
ser propio y MUST NOT repetir el texto del error del cliente de Redis ni de ARQ. La API MUST arrancar y
responder aunque Redis no esté disponible.

#### Scenario: Redis caído

- **WHEN** Redis está detenido y se encola un trabajo
- **THEN** el encolado falla con "cola no disponible" en menos de 3 segundos

#### Scenario: Redis congelado

- **WHEN** el proceso de Redis está pausado (el socket existe pero nadie responde) y se encola un trabajo
- **THEN** el encolado falla con "cola no disponible" en menos de 3 segundos, sin colgarse

#### Scenario: Redis lento

- **WHEN** Redis tarda en responder menos que el límite
- **THEN** el encolado se completa; y cuando tarda más que el límite, falla con "cola no disponible"
  dentro de la cota

#### Scenario: La API arranca sin Redis

- **WHEN** la API arranca con Redis inalcanzable
- **THEN** arranca, no intenta conectarse a Redis al importar la aplicación y `GET /api/salud` responde

### Requirement: El worker no arranca con configuración o parámetros inválidos

El worker SHALL validar al arrancar la misma configuración que la API (variables de la base, de Redis
y `PROPTECH_PARAMETROS`) y leer el archivo de parámetros con el lector validado, y MUST terminar con
un error que nombre cada variable o campo con problema, sin mostrar ninguna contraseña. Cada caso de
arranque que la API ya prueba MUST tener su test equivalente en el worker.

#### Scenario: Worker sin una variable obligatoria

- **WHEN** el worker arranca sin `POSTGRES_PASSWORD`
- **THEN** el proceso termina con un error que nombra la variable

#### Scenario: Worker con variables de Redis rotas

- **WHEN** el worker arranca con `REDIS_PASSWORD` vacía o con `REDIS_PORT=abc`
- **THEN** el proceso termina con un error que nombra la variable y no contiene ninguna contraseña

#### Scenario: Worker con parámetros inválidos

- **WHEN** el worker arranca con un archivo de parámetros que tiene la tasa negativa, o con
  `PROPTECH_PARAMETROS` faltante o vacía
- **THEN** el proceso termina con un error que nombra `intereses.tasa_mensual` o `PROPTECH_PARAMETROS`,
  según el caso
