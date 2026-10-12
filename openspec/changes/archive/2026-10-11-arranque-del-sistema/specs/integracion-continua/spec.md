## MODIFIED Requirements

### Requirement: Tests de integración contra PostgreSQL real

Los tests de integración SHALL correr contra un PostgreSQL real de la misma versión que usa Compose, y
MUST NOT reemplazarlo por otro motor de base de datos. El mismo mecanismo MUST funcionar en la
máquina del desarrollador y en el CI. La verificación de que las versiones coinciden MUST mirar la
imagen del contenedor que efectivamente corrió en los tests, no una constante derivada del propio
archivo de Compose.

#### Scenario: Migraciones en el CI

- **WHEN** corre la suite de integración en el CI
- **THEN** las migraciones se aplican y se revierten contra un PostgreSQL real levantado para la
  corrida

#### Scenario: Versión de PostgreSQL desalineada

- **WHEN** la imagen del contenedor de PostgreSQL que corrió en los tests difiere de la declarada en
  Compose
- **THEN** un test falla y nombra las dos imágenes

#### Scenario: La imagen de los tests no está escrita a mano

- **WHEN** se lee la configuración de los tests de integración
- **THEN** la imagen de PostgreSQL se deriva del archivo de Compose y no aparece escrita como literal
