## MODIFIED Requirements

### Requirement: Navegación común

Dentro de un edificio SHALL haber un menú lateral fijo con Resumen, Unidades, Grupos, Categorías e
Intereses y vencimiento, encabezado por el nombre del edificio y un enlace a "Mis edificios". La
sección actual MUST marcarse con texto o forma además de color, y por programa (`aria-current`). Por
debajo de 768 px de ancho el menú MUST plegarse a un botón "Secciones" que lo despliega con teclado. La
barra superior MUST mostrar el nombre de la persona que entró y la administración en uso, con "Salir"
y, si la persona tiene más de una administración, "Cambiar de administración"; nunca un nombre
inventado ni deducido.

#### Scenario: Sección actual

- **WHEN** el administrador está en el padrón de unidades
- **THEN** "Unidades" está marcada como la página actual por programa y no sólo con color

#### Scenario: Menú plegado

- **WHEN** el ancho es de 320 px y el administrador activa "Secciones" con el teclado
- **THEN** el menú se despliega, se recorre con `Tab` y se cierra con `Esc`

#### Scenario: Quién entró

- **WHEN** una persona entra a una administración
- **THEN** la barra superior muestra su nombre, el de la administración y "Salir", operables con
  teclado, y no muestra el texto fijo "Administración"

#### Scenario: Salir

- **WHEN** la persona activa "Salir"
- **THEN** su sesión de Clerk termina, la cookie de la administración elegida se borra y vuelve a la
  pantalla de ingreso

### Requirement: Estados de cada pantalla

Cada pantalla SHALL tener sus estados de carga (un esqueleto con la forma del contenido, sin girador a
pantalla completa), vacío (con el siguiente paso), error de carga (qué pasó en una línea y
"Reintentar", nunca el texto técnico), sin permiso (403: qué no puede hacer y quién sí: el super
admin de la empresa para los permisos de estas pantallas; propietario o inquilino para `informar_pago`), no existe (404: "No encontramos este edificio" con enlace a "Mis edificios") y
sin sesión (401: lleva a la pantalla de ingreso y, después de entrar, vuelve a la misma dirección si es
una dirección propia del sitio). Cada estado MUST poder alcanzarse a pedido, sin tocar el código. Ningún
texto de la web MUST nombrar al "titular" ni al "colaborador".

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

#### Scenario: Sesión vencida

- **WHEN** la API responde 401 al abrir el padrón de un edificio
- **THEN** la web lleva a la pantalla de ingreso y, después de entrar, vuelve al padrón

#### Scenario: Regreso a un sitio ajeno

- **WHEN** la dirección de regreso del ingreso apunta a otro dominio o a una dirección que empieza con
  `//`
- **THEN** después de entrar la web abre "Mis edificios" y no sale del sitio
