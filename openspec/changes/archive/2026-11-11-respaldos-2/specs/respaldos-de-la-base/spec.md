## ADDED Requirements

### Requirement: Apagado ordenado del servicio de respaldos

El servicio de respaldos SHALL atender las señales `SIGTERM` y `SIGINT` y terminar por su cuenta con
código 0 sin esperar a que lo mate el orquestador. Al recibir una de esas señales MUST cortar la
espera del próximo ciclo, borrar el archivo `.parcial` del volcado en curso si hay uno, registrar un
evento propio de apagado y salir; MUST NOT dejar ningún `.dump` final a medio escribir ni ninguna
marca de último backup correcto por un ciclo que no terminó. Un volcado ya completado antes de la
señal MUST quedar en la carpeta.

#### Scenario: Apagado mientras no hay volcado en curso

- **WHEN** el servicio está esperando el próximo ciclo y recibe `SIGTERM`
- **THEN** termina con código 0 en menos de 2 segundos, sin que nadie tenga que mandarle `SIGKILL`, y
  el log registra el evento de apagado como JSON

#### Scenario: Apagado durante un volcado

- **WHEN** hay un volcado en curso con su archivo `.parcial` escrito y el servicio recibe `SIGTERM`
- **THEN** termina con código 0, no queda ningún archivo `.parcial` ni `.dump` nuevo en la carpeta, y
  la marca del último backup correcto no se actualizó

#### Scenario: Apagado del stack completo

- **WHEN** se ejecuta la detención del stack de Compose
- **THEN** el contenedor de respaldos sale por su cuenta, sin consumir el plazo de gracia completo ni
  recibir `SIGKILL`

### Requirement: La carpeta de respaldos no depende de un paso manual

El arranque del stack SHALL dejar la carpeta de respaldos del host creada y escribible por el usuario
indicado por `PROPTECH_UID`/`PROPTECH_GID`, sin que quien levanta el stack tenga que crearla antes a
mano. Si la carpeta no existe, el arranque MUST crearla con ese dueño; MUST NOT quedar como propiedad
de root, y el servicio de respaldos MUST NOT entrar en un ciclo de reinicios por no poder escribir en
ella. Si la carpeta existe pero no se puede escribir, el servicio MUST terminar con un error que la
nombre, como ya hace hoy, en vez de crear otra.

#### Scenario: Primer arranque sin la carpeta creada

- **WHEN** se levanta el stack desde cero sin haber creado antes la carpeta de respaldos
- **THEN** la carpeta queda creada con el usuario del host como dueño, aparece un backup en menos de 2
  minutos y el servicio de respaldos no reinició ninguna vez

#### Scenario: Carpeta ya creada por quien levanta el stack

- **WHEN** la carpeta ya existe con backups adentro y se levanta el stack
- **THEN** los backups anteriores siguen ahí, el dueño de la carpeta no cambia y el servicio arranca
  normalmente

#### Scenario: La documentación ya no pide el paso manual

- **WHEN** se lee el procedimiento de arranque del repositorio
- **THEN** no incluye ningún paso de creación manual de la carpeta de respaldos, y la variable que la
  nombra sigue documentada en la tabla de variables

### Requirement: Conmutar la aplicación a una base restaurada

El repositorio SHALL incluir un procedimiento que apunte la aplicación a una base previamente
restaurada, de modo que un backup restaurado sirva para volver a operar y no sólo para inspeccionar.
El procedimiento MUST verificar, antes de conmutar y contra la base destino misma, las tres
condiciones siguientes: (1) la base existe y acepta conexión; (2) su revisión de migraciones coincide
exactamente con la cabeza del repositorio; (3) las tablas de negocio conservan Row-Level Security
forzada y sus políticas. Si alguna de las tres falla, MUST terminar con código distinto de 0 nombrando
cuál falló y MUST NOT conmutar nada. MUST NOT borrar, vaciar ni modificar la base que deja de usarse,
y MUST NOT restaurar sobre la base en uso. MUST aceptar como destino sólo un nombre que cumpla por
completo la misma expresión que valida el destino de la restauración, y MUST correr sobre el proyecto
de Compose que indica la variable del proyecto, igual que la restauración. Ningún mensaje propio MUST
repetir la salida de las herramientas de la base.

#### Scenario: Conmutación a una base restaurada correcta

- **WHEN** se restaura un backup en una base aparte y se conmuta la aplicación a esa base
- **THEN** la aplicación responde contra la base restaurada, `GET /api/salud` da 200, los datos
  consultados son los del backup y la base anterior sigue existiendo intacta

#### Scenario: Destino con la revisión de migraciones equivocada

- **WHEN** la base destino tiene una revisión de migraciones distinta de la cabeza del repositorio
- **THEN** el procedimiento termina con código distinto de 0, el mensaje nombra la verificación de
  migraciones y la aplicación sigue apuntando a la base anterior

#### Scenario: Destino sin Row-Level Security forzada

- **WHEN** la base destino tiene una tabla de negocio sin RLS forzada o sin sus políticas
- **THEN** el procedimiento termina con código distinto de 0, el mensaje nombra la verificación de
  Row-Level Security y la aplicación sigue apuntando a la base anterior

#### Scenario: Destino inexistente o inalcanzable

- **WHEN** la base destino no existe o no acepta conexión
- **THEN** el procedimiento termina con código distinto de 0 antes de tocar la aplicación

#### Scenario: Destino que es la base en uso

- **WHEN** el destino de la conmutación coincide con la base que la aplicación ya está usando
- **THEN** el procedimiento termina con código distinto de 0 sin ejecutar ningún comando contra la
  base

#### Scenario: Destino que no cumple el patrón de nombre

- **WHEN** el destino tiene un espacio, un punto y coma, mayúsculas, un salto de línea, dígitos de
  otro alfabeto, es el texto vacío o es sólo el prefijo
- **THEN** se rechaza sin ejecutar ningún comando contra la base

#### Scenario: Falla de una herramienta durante la conmutación

- **WHEN** un paso de la conmutación falla y la herramienta escribe un marcador en su salida de error
- **THEN** el procedimiento termina con código distinto de 0 y un mensaje propio que nombra el paso que
  falló, sin repetir el marcador

## MODIFIED Requirements

### Requirement: Retención de backups

El servicio SHALL conservar los últimos `RESPALDO_CONSERVAR` backups correctos (por defecto 14) y
borrar los más viejos sólo después de generar uno nuevo correcto. La antigüedad de un backup SHALL
determinarse por su fecha de modificación en el sistema de archivos, no por el orden alfabético de su
nombre, de modo que un reloj del host atrasado o adelantado no pueda cambiar cuáles se conservan.
Además de la cantidad, el servicio MUST conservar, dentro de los últimos `RESPALDO_CONSERVAR_DIAS`
días (por defecto 14), el backup correcto más nuevo de cada día: con muchos reinicios del stack la
cuenta por cantidad sola puede cubrir unas pocas horas, y ese piso garantiza una ventana real de
recuperación. MUST NOT borrar archivos que no sigan el patrón de nombre de los backups, y MUST NOT
borrar nunca el archivo generado en el ciclo en curso.

#### Scenario: Se supera la retención

- **WHEN** hay 14 backups y se genera uno nuevo correcto
- **THEN** quedan 14, se borró el más viejo y un archivo ajeno en la carpeta sigue ahí

#### Scenario: Un backup fallido no borra nada

- **WHEN** hay 14 backups y el siguiente falla
- **THEN** siguen los 14

#### Scenario: Reloj atrasado

- **WHEN** hay 14 backups y se genera uno nuevo correcto con el reloj del host atrasado, de modo que su
  nombre lleva una fecha anterior a la de todos los demás
- **THEN** el backup nuevo sigue en la carpeta, quedan 14 y se borró el más viejo de los anteriores

#### Scenario: Siete ciclos con el reloj atrasado

- **WHEN** el reloj del host atrasa y se generan siete backups correctos seguidos, todos con nombres
  anteriores a los que ya estaban
- **THEN** los siete siguen en la carpeta y la cantidad conservada es la configurada, no uno solo

#### Scenario: Reloj adelantado

- **WHEN** el reloj del host adelanta y se genera un backup correcto cuyo nombre ordena como el más
  nuevo, y después el reloj vuelve a la hora real y se generan más backups correctos
- **THEN** la retención borra los de modificación más vieja, no conserva indefinidamente el del reloj
  adelantado

#### Scenario: Muchos reinicios dentro del mismo día

- **WHEN** el stack se reinicia muchas veces en un solo día, generando más de `RESPALDO_CONSERVAR`
  backups correctos en esas horas, y había backups correctos de días anteriores dentro de la ventana
  de `RESPALDO_CONSERVAR_DIAS`
- **THEN** el backup más nuevo de cada uno de esos días anteriores sigue en la carpeta

#### Scenario: Backups más viejos que la ventana por días

- **WHEN** hay backups correctos más viejos que `RESPALDO_CONSERVAR_DIAS` días y la cantidad
  configurada ya está cubierta por backups más nuevos
- **THEN** esos backups viejos se borran: el piso por antigüedad no conserva para siempre

### Requirement: Los errores de las herramientas no llegan al log

El log del servicio de respaldos SHALL contener sólo eventos propios con valores fijos (nombre del
archivo, duración, carpeta, variable con problema). **Todas** sus líneas MUST ser JSON con el mismo
esquema (momento, nivel, servicio y evento, más pares propios), incluidas las que informan una
configuración inválida, una carpeta que no se puede escribir o el rechazo por correr como root: MUST
NOT quedar ninguna línea de texto plano en ninguna salida del servicio. La salida y los mensajes de
error de `pg_dump`, `pg_restore` y del sistema MUST NOT copiarse al log, y la contraseña de la base
MUST NOT aparecer en ninguna línea.

#### Scenario: Error de pg_dump con datos en su mensaje

- **WHEN** `pg_dump` falla escribiendo en su salida de error un marcador (como el nombre de una tabla
  o un valor de la base)
- **THEN** el marcador no aparece en ninguna línea del log del servicio, que registra la falla con su
  propio evento

#### Scenario: Configuración inválida

- **WHEN** el servicio termina porque una variable de configuración falta, está vacía, no es un entero
  válido o está fuera de rango
- **THEN** la línea que lo informa es JSON con el mismo esquema que el resto del log, con nivel de
  error y un evento propio, y nombra la variable con problema sin mostrar ningún valor de contraseña

#### Scenario: Carpeta sin permiso de escritura, en JSON

- **WHEN** el servicio termina porque la carpeta de respaldos no existe o no se puede escribir
- **THEN** la línea que lo informa es JSON con el mismo esquema y nombra la carpeta

#### Scenario: Rechazo por correr como root, en JSON

- **WHEN** el servicio termina porque arrancó con uid 0
- **THEN** la línea que lo informa es JSON con el mismo esquema y nombra la variable del usuario del
  host

#### Scenario: Todas las líneas del servicio son JSON

- **WHEN** se recorren todas las líneas que el servicio escribió en su salida estándar y en su salida
  de error en cualquiera de sus modos (continuo, una sola vez, chequeo de salud, configuración
  inválida)
- **THEN** cada línea no vacía se parsea como JSON y trae el momento, el nivel, el servicio y el
  evento

### Requirement: Configuración del servicio de respaldos validada

El servicio SHALL validar al arrancar su configuración y MUST terminar con un error que nombre la
variable si `RESPALDO_INTERVALO_SEGUNDOS`, `RESPALDO_CONSERVAR`, `RESPALDO_CONSERVAR_DIAS` o
`RESPALDO_LIMITE_SEGUNDOS` faltan, están vacíos o en blanco, no son enteros escritos sólo con dígitos
ASCII (sin espacios, tabulaciones ni saltos de línea alrededor, sin signo y sin ceros a la izquierda)
o están fuera de rango (intervalo entre 60 y 604800 segundos; conservar entre 1 y 365; conservar días
entre 1 y 365; límite entre 5 y 86400 y menor que el intervalo), sin mostrar valores de contraseñas.
Compose MUST negarse a arrancar si falta `PROPTECH_DIR_RESPALDOS`, `PROPTECH_UID` o `PROPTECH_GID`. El
script de respaldo MUST negarse a correr con uid 0, antes de cualquier otra verificación.

#### Scenario: Corre como root

- **WHEN** el script de respaldo arranca con uid 0 (por ejemplo, con `PROPTECH_UID=0`)
- **THEN** termina con código distinto de 0 y un error que nombra `PROPTECH_UID`, sin ejecutar
  `pg_dump` ni escribir en la carpeta

#### Scenario: Intervalo inválido

- **WHEN** `RESPALDO_INTERVALO_SEGUNDOS` vale `abc`, `0`, `59`, `604801`, `060` o `+60`, está vacío o
  en blanco, tiene un espacio, una tabulación o un salto de línea alrededor, o usa dígitos de otro
  alfabeto
- **THEN** el servicio termina con un error que nombra `RESPALDO_INTERVALO_SEGUNDOS`

#### Scenario: Retención inválida

- **WHEN** `RESPALDO_CONSERVAR` vale `0`, `366`, `abc`, está vacío o usa dígitos de otro alfabeto
- **THEN** el servicio termina con un error que nombra `RESPALDO_CONSERVAR`

#### Scenario: Ventana por días inválida

- **WHEN** `RESPALDO_CONSERVAR_DIAS` vale `0`, `366`, `abc`, `060`, `+1`, está vacío, en blanco, tiene
  un espacio, una tabulación o un salto de línea alrededor, o usa dígitos de otro alfabeto
- **THEN** el servicio termina con un error que nombra `RESPALDO_CONSERVAR_DIAS`

#### Scenario: Límite inválido

- **WHEN** `RESPALDO_LIMITE_SEGUNDOS` vale `4`, `86401`, `abc`, o es mayor o igual que el intervalo
- **THEN** el servicio termina con un error que nombra `RESPALDO_LIMITE_SEGUNDOS`

#### Scenario: Compose sin la carpeta de respaldos

- **WHEN** se ejecuta `docker compose config` sin `PROPTECH_DIR_RESPALDOS`
- **THEN** Compose falla y el mensaje nombra `PROPTECH_DIR_RESPALDOS`

### Requirement: El backup trae todas las administraciones sin ser superusuario

El servicio de respaldos SHALL volcar la base con `proptech_respaldo`, un rol sin superusuario al que
Row-Level Security no le filtra filas y que puede leer todas las tablas, de modo que el backup tenga los
datos de todas las administraciones. MUST NOT usar las credenciales del rol de arranque, de
`proptech_app` ni de `proptech_migrador`, y ningún volcado MUST usar `--enable-row-security`, que con
un rol filtrado produce un backup vacío sin error. Que un rol insuficiente haga fallar el volcado
SHALL verificarse ejecutando `pg_dump` real contra la base real con ese rol, no con una herramienta
falsa ni sólo inspeccionando la configuración.

#### Scenario: Backup con dos administraciones

- **WHEN** la base tiene complejos de dos administraciones, se genera un backup y se restaura en una
  base aparte
- **THEN** la base restaurada tiene los complejos de las dos, en la misma cantidad que la original, y
  conserva la RLS forzada y las políticas de cada tabla

#### Scenario: Volcado con el rol equivocado

- **WHEN** el servicio de respaldos se configura con las credenciales de `proptech_app` y corre un
  ciclo contra la base real, con el `pg_dump` real de la imagen
- **THEN** el volcado falla con código distinto de 0, no queda ningún `.dump` ni `.parcial` nuevo, el
  log registra la falla con su propio evento en JSON sin la salida de `pg_dump`, y el chequeo de salud
  del servicio falla

#### Scenario: Un rol insuficiente no produce un backup aparentemente válido

- **WHEN** se intenta volcar la base con un rol al que Row-Level Security sí le filtra filas
- **THEN** no queda ningún archivo de backup que `pg_restore --list` acepte como completo: el fallo es
  ruidoso, nunca un backup vacío sin error

#### Scenario: Credenciales y opciones del servicio

- **WHEN** se inspecciona la configuración del servicio de respaldos y sus scripts
- **THEN** su usuario es `proptech_respaldo`, no tiene la contraseña del rol de arranque y ningún
  script usa `--enable-row-security`
