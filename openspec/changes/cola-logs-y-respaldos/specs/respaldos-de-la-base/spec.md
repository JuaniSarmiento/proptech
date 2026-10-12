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

### Requirement: Retención de backups

El servicio SHALL conservar los últimos `RESPALDO_CONSERVAR` backups correctos (por defecto 14) y
borrar los más viejos sólo después de generar uno nuevo correcto. MUST NOT borrar archivos que no
sigan el patrón de nombre de los backups.

#### Scenario: Se supera la retención

- **WHEN** hay 14 backups y se genera uno nuevo correcto
- **THEN** quedan 14, se borró el más viejo y un archivo ajeno en la carpeta sigue ahí

#### Scenario: Un backup fallido no borra nada

- **WHEN** hay 14 backups y el siguiente falla
- **THEN** siguen los 14

### Requirement: Configuración del servicio de respaldos validada

El servicio SHALL validar al arrancar su configuración y MUST terminar con un error que nombre la
variable si `RESPALDO_INTERVALO_SEGUNDOS` o `RESPALDO_CONSERVAR` faltan, están vacíos, no son enteros
o están fuera de rango (intervalo entre 60 y 604800 segundos; conservar entre 1 y 365), sin mostrar
valores de contraseñas. Compose MUST negarse a arrancar si falta `PROPTECH_DIR_RESPALDOS`.

#### Scenario: Intervalo inválido

- **WHEN** `RESPALDO_INTERVALO_SEGUNDOS` vale `abc`, `0` o está vacío
- **THEN** el servicio termina con un error que nombra `RESPALDO_INTERVALO_SEGUNDOS`

### Requirement: Restauración probada

El repositorio SHALL incluir un procedimiento de restauración que carga un backup en una base aparte,
nunca sobre la base en uso por defecto, y el CI MUST ejecutarlo sobre un backup generado por el
servicio en cada corrida del humo.

#### Scenario: Restaurar el último backup

- **WHEN** se restaura el último backup en una base nueva de restauración
- **THEN** la base restaurada tiene la misma revisión de migraciones que la original y la tabla
  `trabajos_hechos`, y la base en uso no se modificó

### Requirement: Salud del servicio de respaldos

El servicio de respaldos SHALL figurar como no saludable si su último backup correcto es más viejo
que una vez y media el intervalo configurado, o si todavía no generó ninguno pasado el arranque.

#### Scenario: Backup atrasado

- **WHEN** el último backup correcto tiene más de 1,5 intervalos de antigüedad
- **THEN** el chequeo de salud del servicio falla
