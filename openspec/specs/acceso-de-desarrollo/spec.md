# acceso-de-desarrollo Specification

## Purpose

Permite recorrer las pantallas del administrador contra la API real en desarrollo, con el edificio de
ejemplo cargado, entrando siempre por el login real (Clerk de desarrollo) y sin ningún camino que
saltee la identidad — ni en desarrollo —, cargando el ejemplo por el camino de alta inicial (D10 de
`login-y-usuarios`) en vez de un punto de entrada propio sin login (D11 del mismo design, E12). Se
construye sólo con la firma HIGH de Juani, Alberto o Emiliano (D-094, D-111).

## Requirements

### Requirement: Ningún camino entra sin login, ni en desarrollo

El sistema SHALL mantener un solo camino de identidad — el login real de `login-y-usuarios` — en
cualquier entorno. Ningún archivo de este change SHALL agregar un punto de entrada, variable de
entorno o archivo de Compose que reemplace o saltee esa identidad. La app SHALL responder 401 a todo
pedido de dominio sin sesión válida, en desarrollo igual que en producción.

#### Scenario: Pedido de dominio sin sesión, en desarrollo

- **WHEN** se pide una ruta de dominio a la API de desarrollo sin un token de sesión válido
- **THEN** la respuesta es 401, igual que en producción

#### Scenario: El repositorio no tiene un punto de entrada propio

- **WHEN** se busca en el repositorio un punto de entrada que reemplace la identidad por fuera del
  login
- **THEN** no existe ninguno: ni `backend/desarrollo/`, ni `compose.desarrollo.yaml`, ni una variable
  que lo active

### Requirement: La carga del ejemplo usa la identidad de `proptech_app`, por el camino de D10

El comando que carga el edificio de ejemplo (capability `datos-semilla`) SHALL correr con las
credenciales de `proptech_app` — las mismas que usan la API y el worker en producción — fijando el
tenant de la administración de ejemplo y creando su `super_admin` en la misma transacción, siguiendo
la misma forma que D10 usa para el alta inicial. El comando MUST NOT requerir ni otorgar ningún
permiso nuevo sobre `auditoria` ni sobre ninguna otra tabla.

#### Scenario: La carga corre como `proptech_app`

- **WHEN** se corre el comando de carga del edificio de ejemplo
- **THEN** se conecta con las credenciales de `proptech_app`, nunca con las de `proptech_migrador`

#### Scenario: Ningún permiso nuevo sobre `auditoria`

- **WHEN** se revisan los permisos de `proptech_migrador` después de este change
- **THEN** sigue sin `INSERT`, `UPDATE` ni `DELETE` sobre `auditoria`; no se otorgó ningún `GRANT`
  nuevo a ningún rol para este change

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
`CLERK_EMISOR`, el emisor contra el que la API verifica los tokens del id que se vincula, con la forma
del requisito siguiente. Sin emisor MUST negarse también. El mensaje MUST NOT repetir el emisor ni el
id.

#### Scenario: Instancia de producción

- **WHEN** con `PROPTECH_ENTORNO=desarrollo` y `CLERK_EMISOR=https://clerk.proptech.invalid` se corre con
  `--clerk-usuario user_Dev123`
- **THEN** termina con código distinto de 0 antes de conectarse a la base, sin escribir nada y sin
  repetir el emisor ni el id

#### Scenario: Emisor que sólo contiene el dominio de desarrollo

- **WHEN** el emisor es `https://clerk.accounts.dev.proptech.invalid`,
  `https://x.clerk.accounts.dev.evil.com`, `http://x.clerk.accounts.dev` o
  `https://x.clerk.accounts.dev:8443`
- **THEN** el comando se niega igual que con una instancia de producción

#### Scenario: Sin emisor

- **WHEN** no hay `CLERK_EMISOR` configurado y se corre con `--clerk-usuario user_Dev123`
- **THEN** termina con código distinto de 0 antes de conectarse a la base

#### Scenario: La carga sin la opción no cambia

- **WHEN** con `PROPTECH_ENTORNO=desarrollo` y sin `CLERK_EMISOR` se corre la carga sin `--clerk-usuario`
- **THEN** el ejemplo se carga como hoy

### Requirement: El emisor de desarrollo se valida como URL completa

`CLERK_EMISOR` SHALL aceptarse sólo si, leído como URL, tiene esquema `https`, un host normalizado a
minúsculas que termina en `.clerk.accounts.dev`, ni usuario ni contraseña, ni query ni fragmento, ningún
puerto o el 443, y ruta vacía o `/`. Un emisor que no se puede leer como URL MUST tratarse como rechazo.

#### Scenario: Emisor de desarrollo con partes de más

- **WHEN** el emisor es `https://u:p@x.clerk.accounts.dev`, `https://x.clerk.accounts.dev?x=1`,
  `https://x.clerk.accounts.dev#f`, `https://x.clerk.accounts.dev/ruta` o tiene un puerto que no se
  puede leer
- **THEN** el comando se niega antes de conectarse a la base, sin repetir el emisor ni el id

#### Scenario: Emisor de desarrollo en sus formas válidas

- **WHEN** el emisor es `https://X.CLERK.ACCOUNTS.DEV`, `https://x.clerk.accounts.dev/` o
  `https://x.clerk.accounts.dev:443`
- **THEN** la traba del emisor lo acepta

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

### Requirement: La carrera con otra vinculación da el mismo mensaje

Si otra persona de la administración de ejemplo queda vinculada al id entre la comprobación previa y la
escritura, la violación de unicidad de la base SHALL terminar con el mismo mensaje fijo de "esa cuenta
ya está vinculada a otra persona del ejemplo", sin traceback, sin el id y sin escribir.

#### Scenario: Otra persona del ejemplo se vincula entre la comprobación y la escritura

- **WHEN** la comprobación previa no encontró el id, pero antes del `UPDATE` otra persona de la
  administración de ejemplo queda vinculada a `user_Dev123`, y la escritura viola
  `uq_persona_clerk_administracion`
- **THEN** el comando termina con código distinto de 0 con el mismo mensaje de "esa cuenta ya está
  vinculada a otra persona del ejemplo", sin traceback, sin el id y sin el `[parameters: …]` del driver,
  y el vínculo de la persona `super_admin` no cambió

### Requirement: La vinculación de desarrollo aguanta dos corridas a la vez

La escritura del vínculo SHALL ser condicional en la base: sólo si el vínculo está vacío o ya es ese
id, mirando cuántas filas cambió. Dos corridas a la vez con ids distintos MUST NOT poder dejar el
vínculo de la que terminó con error.

#### Scenario: Dos cargas a la vez con ids distintos

- **WHEN** dos corridas sobre el ejemplo sin vínculo intentan a la vez vincular `user_Dev123` y
  `user_Otro456`
- **THEN** una termina con código 0 y la otra con código distinto de 0, y el vínculo es el id de la que
  terminó con 0
