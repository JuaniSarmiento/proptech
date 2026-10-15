## ADDED Requirements

### Requirement: CI en los pull requests, con límite de tiempo y búsqueda de secretos fijada

El workflow del CI SHALL correr también en cada pull request, cada trabajo MUST tener un límite de
tiempo, y la imagen de la búsqueda de secretos MUST estar fijada por digest, no sólo por tag.

#### Scenario: Workflow revisado

- **WHEN** se lee el workflow del CI
- **THEN** se dispara con `push` y con `pull_request`, cada trabajo tiene `timeout-minutes` y la imagen
  de gitleaks lleva `@sha256:`

### Requirement: Cada paso del humo dice cuál es y cuenta exacto

Cada paso de la prueba de humo que falla SHALL nombrar su número y su descripción, y donde un paso
espera una sola aparición MUST verificar que aparece exactamente una.

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

### Requirement: Las cabeceras de seguridad se verifican de punta a punta

La prueba de humo SHALL pedir por el proxy la web y la API con GET y con HEAD y verificar las cabeceras
de seguridad y la ausencia de `Server`, `Via` y `X-Powered-By`.

#### Scenario: Cabeceras en el stack vivo

- **WHEN** el humo pide `/` y `/api/salud` por el proxy con GET y con HEAD
- **THEN** las cuatro respuestas cumplen el requisito de cabeceras del entorno de ejecución
