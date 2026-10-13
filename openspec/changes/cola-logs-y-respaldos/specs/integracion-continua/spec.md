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
