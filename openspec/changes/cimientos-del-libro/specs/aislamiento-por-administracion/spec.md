# Spec Delta

## MODIFIED Requirements

### Requirement: Roles de la base separados por trabajo

El sistema SHALL usar cuatro roles de PostgreSQL distintos: el rol de arranque del contenedor
(superusuario), sólo para crear y reparar los otros y como dueño de la auditoría y de toda tabla de
sólo agregar; `proptech_migrador`, dueño de las demás tablas de dominio, para las migraciones;
`proptech_app`, para la API y el worker; y `proptech_respaldo`, sólo para volcar la base. Ninguno de
los tres roles del proyecto MUST ser superusuario ni tener `CREATEROLE` o `CREATEDB`;
`proptech_migrador` y `proptech_app` MUST NOT tener `BYPASSRLS`; `proptech_app` MUST NOT ser dueño de
ninguna tabla; `proptech_migrador` MUST NOT ser dueño de ninguna tabla de sólo agregar.
`proptech_migrador` MUST poder crear tablas en el esquema de la aplicación, y `proptech_app` MUST tener
permisos sobre las tablas que ya existían antes de este cambio. La creación de los roles MUST ser
idempotente y funcionar también sobre un volumen de datos que ya existía.

#### Scenario: Los atributos de cada rol

- **WHEN** se levanta el stack y se consulta el catálogo de roles
- **THEN** `proptech_migrador`, `proptech_app` y `proptech_respaldo` existen, ninguno es superusuario,
  sólo `proptech_respaldo` tiene `BYPASSRLS`, y `proptech_app` no es dueño de ninguna tabla

#### Scenario: Arranque repetido

- **WHEN** el paso que crea los roles corre dos veces seguidas sobre la misma base
- **THEN** la segunda corrida termina sin error y los roles quedan con los mismos atributos

#### Scenario: Volumen anterior a este cambio

- **WHEN** se levanta el stack sobre un volumen con las tablas de los cambios 1a a 1d, creadas por el
  rol de arranque
- **THEN** las migraciones terminan con éxito como `proptech_migrador`, esas tablas pasan a ser suyas y
  `proptech_app` puede leer y escribir `trabajos_hechos`

#### Scenario: El migrador no es dueño de una tabla de sólo agregar

- **WHEN** después del paso de roles, de las migraciones y de un segundo `antes`, `proptech_migrador`
  intenta `NO FORCE ROW LEVEL SECURITY` sobre `auditoria` o sobre `configuracion_versionada`
- **THEN** la base lo rechaza por no ser el dueño, en las dos tablas

## ADDED Requirements

### Requirement: Las tablas de sólo agregar pasan al rol de arranque después de migrar

El paso de roles posterior a las migraciones SHALL dejar cada tabla del conjunto de sólo agregar, y las
funciones de sus triggers, con dueño el rol de arranque, y el paso anterior MUST NOT devolvérselas al
migrador. Una tabla que se sume al conjunto MUST quedar cubierta sin cambiar el paso de roles.

#### Scenario: Volumen del 3a, donde el migrador era dueño

- **WHEN** se levanta el stack sobre un volumen donde `configuracion_versionada` es de
  `proptech_migrador`
- **THEN** las migraciones pendientes corren como migrador, y al terminar el paso posterior la tabla y
  su función de bloqueo son del rol de arranque

#### Scenario: Una migración futura sobre una tabla protegida

- **WHEN** con `configuracion_versionada` ya del rol de arranque, una migración nueva corrida como
  `proptech_migrador` intenta un `ALTER TABLE` sobre ella
- **THEN** la migración falla con el error de no ser el dueño y no queda aplicada a medias

#### Scenario: Bajar la migración que agrega el umbral

- **WHEN** se intenta bajar la migración `0021` como `proptech_migrador` después del paso posterior
- **THEN** falla por no ser el dueño, y con la tabla devuelta al migrador por el rol de arranque baja y
  vuelve a subir sin perder versiones

### Requirement: La protección de cada tabla de sólo agregar se verifica por el efecto

Al terminar, el paso de roles SHALL confirmar en cada tabla del conjunto: RLS habilitada y forzada,
triggers de bloqueo presentes y habilitados, sus funciones del rol de arranque, y que un `UPDATE` y un
`DELETE` reales fallen con el error del trigger. `TRUNCATE` MUST probarse ejecutado, o por catálogo sólo
si una FK entrante lo impide. Si algo falta, MUST fallar nombrándolo, sin confirmar nada.

#### Scenario: Trigger deshabilitado

- **WHEN** antes del paso posterior alguien deshabilitó el trigger de `UPDATE` de
  `configuracion_versionada`
- **THEN** el paso falla nombrando la tabla y el trigger, y no confirma ningún cambio de dueño

#### Scenario: Función de bloqueo reemplazada por una que no hace nada

- **WHEN** la función del trigger de `configuracion_versionada` fue reemplazada por una que devuelve la
  fila sin error
- **THEN** el paso falla diciendo que la tabla admite `UPDATE`

#### Scenario: Otro error frena el intento

- **WHEN** el intento de `DELETE` falla por un motivo distinto del error del trigger
- **THEN** el paso falla diciendo que no pudo confirmar el bloqueo, en lugar de darlo por bueno

### Requirement: Los procesos no arrancan si una tabla de sólo agregar tiene otro dueño

La API y el worker SHALL verificar al arrancar, antes de aceptar pedidos o tareas, que cada tabla del
conjunto de sólo agregar existe y es de un rol superusuario; si no, MUST NOT arrancar y MUST nombrar
cada tabla con problema, sin mostrar ningún valor de configuración.

#### Scenario: Una tabla quedó del migrador

- **WHEN** `configuracion_versionada` es de `proptech_migrador` y arranca la API
- **THEN** la API no arranca y el log nombra `configuracion_versionada` y el motivo

#### Scenario: Todo en orden

- **WHEN** todas las tablas del conjunto son del rol de arranque
- **THEN** la API y el worker arrancan como antes
