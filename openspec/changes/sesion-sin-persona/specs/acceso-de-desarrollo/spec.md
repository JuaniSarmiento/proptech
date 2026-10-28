## ADDED Requirements

### Requirement: La cuenta de desarrollo se vincula con el comando del ejemplo

El comando que carga el edificio de ejemplo SHALL aceptar `--clerk-usuario <id>`, que vincula la
persona `super_admin` del ejemplo a ese id de Clerk, en la transacción de la carga o, si el ejemplo ya
estaba, en una propia. MUST respetar la guarda de D-112 (sin `PROPTECH_ENTORNO=desarrollo` no se
conecta ni escribe), MUST correr como `proptech_app` y MUST NOT tocar otra administración ni persona.

#### Scenario: Vincular al cargar por primera vez

- **WHEN** con `PROPTECH_ENTORNO=desarrollo` y el emisor de una instancia de desarrollo de Clerk se
  corre la carga con `--clerk-usuario user_Dev123` sobre una base sin el ejemplo
- **THEN** el ejemplo queda cargado, su `super_admin` queda vinculado a `user_Dev123` y el comando
  termina con código 0

#### Scenario: Vincular un ejemplo ya cargado

- **WHEN** el ejemplo ya está cargado sin vínculo y se corre la carga con `--clerk-usuario user_Dev123`
- **THEN** el comando dice que el ejemplo ya estaba, vincula al `super_admin` y termina con código 0, y
  los conteos de las tablas del ejemplo no cambian

#### Scenario: La opción no saltea la guarda

- **WHEN** se corre con `--clerk-usuario user_Dev123` sin `PROPTECH_ENTORNO=desarrollo`
- **THEN** termina con código distinto de 0, no se conecta a la base y no escribe nada

#### Scenario: Entrar con la cuenta vinculada

- **WHEN** después de vincular `user_Dev123` llega a `GET /api/sesion` un token válido de esa cuenta
- **THEN** la respuesta es 200 con la administración de ejemplo como única administración

### Requirement: La función de vinculación sólo conoce al ejemplo

La función de `acceso.aplicacion` que escribe el vínculo de desarrollo SHALL aceptar sólo la
administración y la persona fijas del ejemplo, declaradas en `acceso`. Con cualquier otra MUST negarse
sin ejecutar ninguna escritura.

#### Scenario: La función de vinculación con otra persona

- **WHEN** se llama a la función de vinculación de desarrollo con una persona o una administración que
  no son las fijas del ejemplo
- **THEN** se niega sin ejecutar ninguna escritura

### Requirement: Sólo se vincula una cuenta de una instancia de desarrollo de Clerk

Con `--clerk-usuario`, el comando SHALL negarse, antes de conectarse a la base, si la instancia de Clerk
configurada no es de desarrollo, aunque `PROPTECH_ENTORNO=desarrollo` esté puesto. La señal MUST ser
`CLERK_EMISOR`, el emisor contra el que la API verifica los tokens del id que se vincula: `https://` y
un host que termina en `.clerk.accounts.dev`, sin puerto ni ruta. Sin emisor MUST negarse también. El
mensaje MUST NOT repetir el emisor ni el id.

#### Scenario: Instancia de producción

- **WHEN** con `PROPTECH_ENTORNO=desarrollo` y `CLERK_EMISOR=https://clerk.proptech.invalid` se corre con
  `--clerk-usuario user_Dev123`
- **THEN** termina con código distinto de 0 antes de conectarse a la base, sin escribir nada y sin
  repetir el emisor ni el id

#### Scenario: Emisor que sólo contiene el dominio de desarrollo

- **WHEN** el emisor es `https://clerk.accounts.dev.proptech.invalid`, `http://x.clerk.accounts.dev` o
  `https://x.clerk.accounts.dev:8443`
- **THEN** el comando se niega igual que con una instancia de producción

#### Scenario: Sin emisor

- **WHEN** no hay `CLERK_EMISOR` configurado y se corre con `--clerk-usuario user_Dev123`
- **THEN** termina con código distinto de 0 antes de conectarse a la base

#### Scenario: La carga sin la opción no cambia

- **WHEN** con `PROPTECH_ENTORNO=desarrollo` y sin `CLERK_EMISOR` se corre la carga sin `--clerk-usuario`
- **THEN** el ejemplo se carga como hoy

### Requirement: El id de Clerk se valida antes de conectarse

El id de `--clerk-usuario` SHALL validarse antes de abrir la conexión, con coincidencia completa y sólo
ASCII contra el formato que exige la base (`user_` y de 1 a 64 letras o dígitos). Un id inválido MUST
terminar con código distinto de 0, sin escribir y sin repetir el valor recibido, ni en la salida
estándar ni en la de errores: la validación MUST NOT hacerse con `type=` ni `choices` de `argparse`, que
repiten el valor en su mensaje.

#### Scenario: Id con otra forma

- **WHEN** se corre con `--clerk-usuario` igual a `usr_Dev123`, `user_`, `user_` seguido de 65
  caracteres, un id con un carácter no ASCII o un id con un salto de línea al final
- **THEN** termina con código distinto de 0 antes de conectarse a la base, sin escribir nada y sin
  repetir el valor recibido en la salida estándar ni en la de errores

### Requirement: La vinculación de desarrollo no pisa otra cuenta

Vincular el id que la persona ya tiene SHALL terminar con código 0 sin escribir nada. Si la persona ya
está vinculada a otro id, el comando MUST terminar con código distinto de 0 sin escribir nada. Si el id
ya está vinculado a otra persona de la administración de ejemplo, MUST comprobarlo antes de escribir y
terminar con código distinto de 0, con un mensaje propio, sin traceback y sin repetir el id.

#### Scenario: Vincular dos veces el mismo id

- **WHEN** se corre dos veces seguidas con `--clerk-usuario user_Dev123`
- **THEN** la segunda termina con código 0 sin escribir nada

#### Scenario: Ya vinculado a otra cuenta

- **WHEN** el `super_admin` de ejemplo ya está vinculado a `user_Dev123` y se corre con
  `--clerk-usuario user_Otro456`
- **THEN** termina con código distinto de 0, dice que ya está vinculado a otra cuenta y el vínculo
  sigue siendo `user_Dev123`

#### Scenario: El id ya es de otra persona del ejemplo

- **WHEN** otra persona de la administración de ejemplo ya tiene `user_Dev123` (por ejemplo, aceptó una
  invitación ahí) y se corre con `--clerk-usuario user_Dev123`
- **THEN** termina con código distinto de 0, dice que esa cuenta ya está vinculada a otra persona del
  ejemplo, no muestra un traceback ni el id, y nada cambió

### Requirement: La vinculación de desarrollo aguanta dos corridas a la vez

La escritura del vínculo SHALL ser condicional en la base: sólo si el vínculo está vacío o ya es ese
id, mirando cuántas filas cambió. Dos corridas a la vez con ids distintos MUST NOT poder dejar el
vínculo de la que terminó con error.

#### Scenario: Dos cargas a la vez con ids distintos

- **WHEN** dos corridas sobre el ejemplo sin vínculo intentan a la vez vincular `user_Dev123` y
  `user_Otro456`
- **THEN** una termina con código 0 y la otra con código distinto de 0, y el vínculo es el id de la que
  terminó con 0

## MODIFIED Requirements

### Requirement: Se recorre con el login real, no con un bypass

Con el edificio de ejemplo cargado, el recorrido de las pantallas del administrador contra la API real
SHALL hacerse entrando con una cuenta de Clerk de desarrollo vinculada a la persona titular de la
administración de ejemplo (su `super_admin`), nunca reemplazando la identidad por otro medio. La
vinculación MUST hacerse con la opción `--clerk-usuario` del comando del ejemplo, siguiendo los pasos
documentados en el repositorio, y nunca con SQL escrito a mano.

#### Scenario: Entrar a las pantallas con el ejemplo cargado

- **WHEN** con el ejemplo cargado se entra a "Mis edificios" con la cuenta de Clerk de desarrollo
  vinculada a la administración de ejemplo
- **THEN** se ve el edificio de ejemplo y sólo ése

#### Scenario: Otra persona repite el recorrido

- **WHEN** una persona distinta de quien escribió los pasos los sigue tal cual, con su propia cuenta de
  Clerk de desarrollo y una base limpia
- **THEN** llega a "Mis edificios" con el edificio de ejemplo sin escribir SQL ni pedir ayuda
