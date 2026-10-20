## MODIFIED Requirements

### Requirement: Estados de cada pantalla

Cada pantalla SHALL tener sus estados de carga (un esqueleto con la forma del contenido, sin girador a
pantalla completa), vacío (con el siguiente paso), error de carga (qué pasó en una línea y
"Reintentar", nunca el texto técnico), sin permiso (403: qué no puede hacer y quién sí: el super
admin de la empresa para los permisos de estas pantallas; propietario o inquilino para `informar_pago`), no existe (404: "No encontramos este edificio" con enlace a "Mis edificios") y
sin sesión (401). Cada estado MUST poder alcanzarse a pedido, sin tocar el código. Ningún texto de la
web MUST nombrar al "titular" ni al "colaborador".

#### Scenario: Error de la API con texto técnico

- **WHEN** la API responde 500 con un texto técnico en el cuerpo
- **THEN** la pantalla dice qué pasó en castellano simple, ofrece "Reintentar" y no muestra el texto
  técnico

#### Scenario: Edificio de otra administración

- **WHEN** el administrador abre la dirección de un edificio que la API responde con 404
- **THEN** ve "No encontramos este edificio" con un enlace a "Mis edificios"

#### Scenario: Sin permiso

- **WHEN** un auxiliar o un administrador por edificio intenta una acción que la API responde con 403
- **THEN** ve qué no puede hacer y que lo puede hacer el super admin de la empresa, sin perder lo
  cargado

#### Scenario: Crear un edificio sin permiso

- **WHEN** un administrador intenta crear un edificio y la API responde 403
- **THEN** el formulario dice que no puede crear un edificio y que lo puede hacer el super admin de la
  empresa

#### Scenario: Sin permiso para informar un pago

- **WHEN** una acción responde 403 con `permiso_faltante=informar_pago`
- **THEN** el estado dice que puede hacerlo la persona propietaria o inquilina de la unidad
- **AND** no muestra que lo puede hacer el super admin
