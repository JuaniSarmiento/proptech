## Purpose

Define cómo se generan solos los backups de PostgreSQL, dónde quedan fuera de los contenedores,
cuántos se conservan y cómo se prueba que se pueden restaurar, porque un backup que nunca se
restauró no es un backup.

## ADDED Requirements

### Requirement: Backup automático al arrancar y cada día

El sistema SHALL generar un backup completo de la base al arrancar el servicio de respaldos y después
cada `RESPALDO_INTERVALO_SEGUNDOS` (por defecto 86400, un día), sin intervención manual. El servicio
MUST conectarse a la base sólo por la red interna, sin salida a Internet y sin publicar puertos.

#### Scenario: El backup se genera solo

- **WHEN** se levanta el stack desde cero
- **THEN** en menos de 2 minutos aparece un archivo de backup en la carpeta de respaldos del host sin
  que nadie ejecute ningún comando

### Requirement: El backup queda fuera de los contenedores y de los volúmenes de Docker

Los backups SHALL escribirse en una carpeta del host indicada por `PROPTECH_DIR_RESPALDOS`, con nombre
`proptech-<fecha y hora UTC>.dump`, permisos de lectura sólo para su dueño y como dueño el usuario del
host indicado por `PROPTECH_UID`/`PROPTECH_GID`. Un backup MUST aparecer completo o no aparecer: nunca
queda un archivo final a medio escribir. La carpeta MUST sobrevivir a `docker compose down -v`.

#### Scenario: Sobrevive al borrado de volúmenes

- **WHEN** se genera un backup y después se ejecuta `docker compose down -v`
- **THEN** el archivo sigue en la carpeta del host

#### Scenario: Falla el volcado

- **WHEN** la base no está disponible al momento del backup
- **THEN** no queda ningún archivo `.dump` nuevo, el log registra la falla con nivel de error y el
  servicio reintenta en el próximo ciclo sin terminar

#### Scenario: Carpeta sin permiso de escritura

- **WHEN** la carpeta de respaldos no se puede escribir
- **THEN** el log registra la falla nombrando la carpeta y no queda ningún archivo parcial

### Requirement: Un volcado que no termina se corta

Cada volcado SHALL estar acotado por `RESPALDO_LIMITE_SEGUNDOS` (por defecto 1800). Si la base no
responde o el volcado tarda más que ese límite, el servicio MUST cortarlo, borrar el archivo parcial,
registrar la falla con nivel de error y esperar al próximo ciclo sin terminar.

#### Scenario: Base que no responde durante el volcado

- **WHEN** el volcado no termina dentro de `RESPALDO_LIMITE_SEGUNDOS`
- **THEN** se corta dentro de esa cota más un margen de 5 segundos, no queda ningún `.dump` nuevo ni
  `.parcial` y el log registra la falla con nivel de error

#### Scenario: Base lenta dentro del límite

- **WHEN** el volcado tarda menos que `RESPALDO_LIMITE_SEGUNDOS`
- **THEN** el backup se completa normalmente

### Requirement: Los errores de las herramientas no llegan al log

El log del servicio de respaldos SHALL contener sólo eventos propios con valores fijos (nombre del
archivo, duración, carpeta, variable con problema). La salida y los mensajes de error de `pg_dump`,
`pg_restore` y del sistema MUST NOT copiarse al log, y la contraseña de la base MUST NOT aparecer en
ninguna línea.

#### Scenario: Error de pg_dump con datos en su mensaje

- **WHEN** `pg_dump` falla escribiendo en su salida de error un marcador (como el nombre de una tabla
  o un valor de la base)
- **THEN** el marcador no aparece en ninguna línea del log del servicio, que registra la falla con su
  propio evento

### Requirement: Retención de backups

El servicio SHALL conservar los últimos `RESPALDO_CONSERVAR` backups correctos (por defecto 14) y
borrar los más viejos sólo después de generar uno nuevo correcto. MUST NOT borrar archivos que no
sigan el patrón de nombre de los backups, y MUST NOT borrar nunca el archivo generado en el ciclo en
curso, aunque el reloj del host atrase y su nombre ordene como el más viejo.

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

### Requirement: Configuración del servicio de respaldos validada

El servicio SHALL validar al arrancar su configuración y MUST terminar con un error que nombre la
variable si `RESPALDO_INTERVALO_SEGUNDOS`, `RESPALDO_CONSERVAR` o `RESPALDO_LIMITE_SEGUNDOS` faltan,
están vacíos o en blanco, no son enteros escritos sólo con dígitos ASCII (sin espacios, tabulaciones
ni saltos de línea alrededor, sin signo y sin ceros a la izquierda) o están fuera de rango (intervalo entre 60 y 604800 segundos; conservar
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

#### Scenario: Límite inválido

- **WHEN** `RESPALDO_LIMITE_SEGUNDOS` vale `4`, `86401`, `abc`, o es mayor o igual que el intervalo
- **THEN** el servicio termina con un error que nombra `RESPALDO_LIMITE_SEGUNDOS`

#### Scenario: Compose sin la carpeta de respaldos

- **WHEN** se ejecuta `docker compose config` sin `PROPTECH_DIR_RESPALDOS`
- **THEN** Compose falla y el mensaje nombra `PROPTECH_DIR_RESPALDOS`

### Requirement: Restauración probada

El repositorio SHALL incluir un procedimiento de restauración que carga un backup en una base aparte,
nunca sobre la base en uso por defecto, y el CI MUST ejecutarlo sobre un backup generado por el
servicio en cada corrida del humo. Toda operación que borra una base MUST apuntar al proyecto de
Compose `proptech` y a una base que pasó la validación del destino. El procedimiento MUST funcionar
desde cualquier carpeta de trabajo (encuentra por su cuenta la configuración de Compose y su archivo
de entorno) y MUST pasar el usuario de la base (`POSTGRES_USER` del contenedor) a cada herramienta que
borra, crea o restaura la base.

#### Scenario: Restaurar desde cualquier carpeta

- **WHEN** se ejecuta el procedimiento de restauración desde la raíz del repositorio o desde una
  carpeta ajena al repositorio
- **THEN** cada invocación de Compose corre sobre la configuración y el archivo de entorno de `infra/`

#### Scenario: Usuario de la base en cada herramienta

- **WHEN** el procedimiento borra, crea y restaura la base destino
- **THEN** `dropdb`, `createdb` y `pg_restore` reciben `-U` con el usuario de la base que informa el
  contenedor

#### Scenario: Restaurar el último backup

- **WHEN** se restaura el último backup en una base nueva de restauración
- **THEN** la base restaurada tiene la misma revisión de migraciones que la original y la tabla
  `trabajos_hechos`, y la base en uso no se modificó

#### Scenario: Falla de una herramienta durante la restauración

- **WHEN** un paso de la restauración falla y la herramienta escribe un marcador en su salida de error
- **THEN** el procedimiento termina con código distinto de 0 y un mensaje propio que nombra el paso
  que falló, sin repetir el marcador

### Requirement: Destino de la restauración validado

El procedimiento de restauración SHALL aceptar como base destino sólo un nombre que cumpla por
completo la expresión `^proptech_[a-z0-9_]{1,50}$`, evaluada sobre el texto entero, con caracteres
ASCII y sin depender de la configuración regional, y distinto de la base en uso (`POSTGRES_DB`). Ante
cualquier otro valor MUST terminar con código distinto de 0 antes de ejecutar cualquier comando contra
la base.

#### Scenario: Destino vacío

- **WHEN** el destino es el texto vacío
- **THEN** se rechaza sin tocar la base

#### Scenario: Destino que es sólo el prefijo

- **WHEN** el destino es `proptech_`
- **THEN** se rechaza sin tocar la base

#### Scenario: Destino con espacios

- **WHEN** el destino tiene un espacio, una tabulación o un salto de línea, en el medio o al final
- **THEN** se rechaza sin tocar la base

#### Scenario: Destino con punto y coma

- **WHEN** el destino es `proptech_x;DROP DATABASE proptech`
- **THEN** se rechaza sin tocar la base

#### Scenario: Destino con mayúsculas

- **WHEN** el destino es `proptech_Restauracion`
- **THEN** se rechaza sin tocar la base

#### Scenario: Destino de más de 63 caracteres

- **WHEN** el destino tiene 64 caracteres y empieza con `proptech_`
- **THEN** se rechaza sin tocar la base

#### Scenario: Destino igual a la base en uso

- **WHEN** el destino coincide con `POSTGRES_DB`, incluso cuando la base en uso también cumple la
  expresión (por ejemplo, `proptech_principal`)
- **THEN** se rechaza sin tocar la base

#### Scenario: Destino con dígitos de otro alfabeto

- **WHEN** el destino es `proptech_restauracion` seguido de un dígito de otro alfabeto
- **THEN** se rechaza sin tocar la base

### Requirement: Salud del servicio de respaldos

El servicio de respaldos SHALL figurar como no saludable si su último backup correcto es más viejo
que una vez y media el intervalo configurado, si todavía no generó ninguno pasado el arranque, o si la
marca del último backup no es un número válido.

#### Scenario: Backup atrasado

- **WHEN** el último backup correcto tiene más de 1,5 intervalos de antigüedad
- **THEN** el chequeo de salud del servicio falla

#### Scenario: Marca del último backup corrupta

- **WHEN** la marca del último backup contiene texto que no es un número entero
- **THEN** el chequeo de salud del servicio falla
