## MODIFIED Requirements

### Requirement: Tests de integración contra PostgreSQL real

Los tests de integración SHALL correr contra un PostgreSQL real y un Redis real de la misma versión
que usa Compose, y MUST NOT reemplazarlos por otro motor ni por dobles en memoria. El mismo mecanismo
MUST funcionar en la máquina del desarrollador y en el CI. La verificación de que las versiones
coinciden MUST mirar la imagen del contenedor que efectivamente corrió en los tests, no una constante
derivada del propio archivo de Compose.

#### Scenario: Migraciones en el CI

- **WHEN** corre la suite de integración en el CI
- **THEN** las migraciones se aplican y se revierten contra un PostgreSQL real levantado para la
  corrida

#### Scenario: Worker contra Redis real

- **WHEN** corre la suite de integración de la cola
- **THEN** los trabajos se encolan y se ejecutan contra un Redis real levantado para la corrida, y los
  casos de Redis caído, congelado y lento se prueban sobre un contenedor real

#### Scenario: Versión de PostgreSQL desalineada

- **WHEN** la imagen del contenedor de PostgreSQL o de Redis que corrió en los tests difiere de la
  declarada en Compose
- **THEN** un test falla y nombra las dos imágenes

#### Scenario: La imagen de los tests no está escrita a mano

- **WHEN** se lee la configuración de los tests de integración
- **THEN** las imágenes de PostgreSQL y de Redis se derivan del archivo de Compose y no aparecen
  escritas como literal

### Requirement: Prueba de humo del stack detrás del proxy

El CI SHALL levantar el stack completo con Compose y verificar que `GET /api/salud` a través del
proxy responde 200 con la base y la cola conectadas, que el único servicio con puertos publicados es
el proxy, que el worker está saludable, que el `request_id` asignado por el proxy aparece en el log
de la API tanto en un pedido directo como en uno que pasa por la web, que un backup se generó solo y
que ese backup se restaura en una base aparte. Todo comando destructivo del humo MUST apuntar al
proyecto de Compose `proptech` o a bases con el prefijo `proptech_`.

#### Scenario: Humo en el CI

- **WHEN** corre el paso de humo
- **THEN** el stack se levanta, el endpoint de salud responde 200 a través del proxy, la verificación
  de puertos publicados pasa, el `request_id` se sigue de punta a punta, el backup automático aparece
  y se restaura, y el stack se baja al terminar, aun si el paso falló

#### Scenario: Request id malicioso en el humo

- **WHEN** el humo manda un pedido con un `X-Request-ID` malicioso a través del proxy
- **THEN** la respuesta trae un UUID distinto y el valor malicioso no aparece en los logs de ningún
  servicio
