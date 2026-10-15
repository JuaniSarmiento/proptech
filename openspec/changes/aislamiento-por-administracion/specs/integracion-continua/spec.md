## ADDED Requirements

### Requirement: CI en los pull requests, con límite de tiempo y búsqueda de secretos fijada

El workflow del CI SHALL correr también en cada pull request, cada trabajo MUST tener un límite de
tiempo, y la imagen de la búsqueda de secretos MUST estar fijada por digest, no sólo por tag.

#### Scenario: Workflow revisado

- **WHEN** se lee el workflow del CI
- **THEN** se dispara con `push` y con `pull_request`, cada trabajo tiene `timeout-minutes` y la imagen
  de gitleaks lleva `@sha256:`

### Requirement: El humo verifica el candado y dice qué paso falló

La prueba de humo SHALL verificar en el stack levantado que la API y el worker conectan como un rol sin
superusuario ni `BYPASSRLS`, que las respuestas del proxy traen las cabeceras de seguridad, y que un
backup restaurado trae las dos administraciones sembradas. Cada paso que falla MUST nombrar el paso, y
donde el paso dice "aparece uno solo" MUST verificar que aparece exactamente uno.

#### Scenario: Rol de la app en el stack vivo

- **WHEN** el humo consulta el rol con el que conectan la API y el worker
- **THEN** es `proptech_app`, sin superusuario ni `BYPASSRLS`

#### Scenario: Un paso que falla

- **WHEN** falla cualquier paso del humo
- **THEN** la salida nombra el número y la descripción de ese paso

#### Scenario: Uno solo

- **WHEN** un paso espera exactamente una línea o un archivo y aparecen dos
- **THEN** el paso falla

### Requirement: El humo congela las dos dependencias a la vez

La prueba de humo SHALL congelar la base y Redis al mismo tiempo y verificar que `/api/salud` responde
503 dentro de su plazo total, con una línea `salud_degradada` por dependencia, y que `/salud-web`
informa la API como degradada y no como sin conexión. Las dos dependencias MUST quedar despausadas
aunque el paso falle.

#### Scenario: Base y Redis congelados

- **WHEN** el humo pausa `db` y `redis` a la vez y pide `/api/salud` y `/salud-web`
- **THEN** `/api/salud` responde 503 en menos de 2 segundos, hay exactamente dos líneas
  `salud_degradada` con el `request_id` del pedido, y `/salud-web` no informa `sin_conexion`
