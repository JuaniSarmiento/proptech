## MODIFIED Requirements

### Requirement: Configuración sólo por variables de entorno y sin secretos en el repositorio

Toda configuración que varía entre entornos (cadena de conexión, contraseñas de la base y de Redis,
dirección del sitio, ruta del archivo de parámetros) SHALL leerse de variables de entorno. El
repositorio MUST incluir sólo `.env.example` con valores de ejemplo no válidos como credencial real, y
MUST NOT versionar ningún archivo `.env` real. Las imágenes construidas MUST NOT contener archivos
`.env`. Toda variable obligatoria que falte, esté vacía, en blanco, tenga un tipo equivocado o esté
fuera de rango MUST hacer terminar al proceso con un error que nombre cada variable con problema sin
mostrar nunca su valor. El trabajo de migraciones MUST necesitar sólo las variables de la base.

#### Scenario: Archivo de entorno ignorado

- **WHEN** existe `infra/.env` en la copia local y se consulta el estado de git
- **THEN** git no lo lista como archivo a versionar

#### Scenario: Imagen sin archivo de entorno

- **WHEN** se construyen las imágenes de la API y de la web con un `.env` presente en su carpeta
- **THEN** ninguna imagen contiene un archivo `.env`

#### Scenario: API sin cadena de conexión

- **WHEN** la API arranca sin la variable de la cadena de conexión
- **THEN** el proceso termina con un error que nombra la variable faltante y no muestra ningún valor
  secreto

#### Scenario: Variables de Redis rotas

- **WHEN** la API arranca con `REDIS_HOST` o `REDIS_PASSWORD` faltante, vacía o en blanco, o con
  `REDIS_PORT` igual a `abc`, `0` o `70000`
- **THEN** el proceso termina con un error que nombra cada variable con problema y no contiene el
  valor de ninguna contraseña

#### Scenario: Archivo de parámetros inexistente

- **WHEN** la API arranca con `PROPTECH_PARAMETROS` apuntando a un archivo que no existe
- **THEN** el proceso termina con un error que nombra `PROPTECH_PARAMETROS`

#### Scenario: Migraciones sólo con las variables de la base

- **WHEN** el trabajo de migraciones corre con las variables de PostgreSQL y sin ninguna variable de
  Redis ni `PROPTECH_PARAMETROS`
- **THEN** las migraciones se aplican sin error de configuración

#### Scenario: El stack pasa la configuración nueva a la API

- **WHEN** se lee la configuración de Compose
- **THEN** la API recibe las variables de Redis (la contraseña desde el archivo de entorno, obligatoria)
  y la ruta del archivo de parámetros, con la carpeta `config/` montada de sólo lectura, y
  `.env.example` incluye un valor de ejemplo para la contraseña de Redis
