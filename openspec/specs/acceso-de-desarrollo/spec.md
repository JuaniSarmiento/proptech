# acceso-de-desarrollo Specification

## Purpose

Permite recorrer las pantallas del administrador contra la API real en desarrollo, con el edificio de
ejemplo cargado, entrando siempre por el login real (Clerk de desarrollo) y sin ningún camino que
saltee la identidad — ni en desarrollo —, cargando el ejemplo por el camino de alta inicial (D10 de
`login-y-usuarios`) en vez de un punto de entrada propio sin login (D11 del mismo design, E12). Se
construye sólo con la firma HIGH de un socio (D-094).

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
administración de ejemplo (su `super_admin`), nunca reemplazando la identidad por otro medio.

#### Scenario: Entrar a las pantallas con el ejemplo cargado

- **WHEN** con el ejemplo cargado se entra a "Mis edificios" con la cuenta de Clerk de desarrollo
  vinculada a la administración de ejemplo
- **THEN** se ve el edificio de ejemplo y sólo ése
