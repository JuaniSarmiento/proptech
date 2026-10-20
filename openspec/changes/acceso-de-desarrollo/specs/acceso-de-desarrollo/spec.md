## Purpose

Permite entrar a las pantallas del administrador contra la API real sin login, sólo en una máquina de
desarrollo, sin código que saltee la identidad en el paquete instalado ni en la imagen de producción
(D11 y E2 del 3a). Se construye sólo con la firma HIGH de un socio (D-094).

## ADDED Requirements

### Requirement: El acceso de desarrollo no viaja a producción

El punto de entrada de desarrollo SHALL vivir fuera del paquete instalado del backend y MUST NOT estar
en la imagen de producción. La app de producción MUST seguir respondiendo 401 a todo pedido de dominio
sin identidad. Ningún archivo bajo `backend/src/` MUST cambiar para este acceso.

#### Scenario: La imagen de producción

- **WHEN** se construye la imagen del backend y se lista su contenido
- **THEN** no hay ningún archivo del punto de entrada de desarrollo

#### Scenario: Producción sin identidad

- **WHEN** se pide una ruta de dominio a la app de producción sin identidad
- **THEN** la respuesta es 401, igual que antes de este cambio

### Requirement: Sólo lo levanta un archivo de Compose aparte

El acceso de desarrollo SHALL levantarse sólo sumando a mano un archivo de Compose propio, que MUST NOT
llamarse `compose.override.yaml` (Compose lo carga solo) y que MUST publicar la API sólo en
`127.0.0.1`. `compose.yaml` MUST NOT referenciarlo, ningún archivo del repositorio MUST poner
`COMPOSE_FILE` con ese archivo, y el humo MUST nombrar `compose.yaml` de forma explícita.

#### Scenario: Un archivo que activa el override

- **WHEN** un archivo del repositorio pone `COMPOSE_FILE` con el archivo de desarrollo
- **THEN** la suite falla nombrando el archivo

#### Scenario: El humo sin archivo explícito

- **WHEN** el humo llama a `docker compose` sin `-f compose.yaml`
- **THEN** la suite falla

### Requirement: Identidad fija en la administración de ejemplo

El punto de entrada SHALL usar siempre la identidad del titular de la administración de ejemplo y
MUST negarse a arrancar si esa administración no existe en la base, o si la base tiene alguna otra
administración. Con esa identidad, la RLS MUST impedir leer o escribir cualquier otra administración.

#### Scenario: Base sin el ejemplo

- **WHEN** se arranca el punto de entrada sobre una base sin la administración de ejemplo
- **THEN** no arranca y dice que falta cargar el ejemplo

#### Scenario: Base con otra administración

- **WHEN** se arranca el punto de entrada sobre una base que tiene la administración de ejemplo y otra
- **THEN** no arranca y no lee nada de la otra administración

#### Scenario: Las pantallas contra la API real

- **WHEN** con el acceso levantado se abre "Mis edificios" en el navegador
- **THEN** se ve el edificio de ejemplo y sólo ése
