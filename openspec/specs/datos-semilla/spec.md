# datos-semilla Specification

## Purpose
Define el edificio de ejemplo con el que se desarrolla y se demuestra el sistema mientras no hay datos
del piloto: un archivo versionado, ficticio y validado contra los parámetros, que el cambio 3 carga en
la base cuando existan sus tablas.

## Requirements

### Requirement: Edificio de ejemplo ficticio y versionado

El repositorio SHALL incluir `config/semilla/edificio-ejemplo.yaml` con un edificio ficticio que tiene
unidades de los cuatro tipos (departamento, cochera, baulera y local), cada una con identificador
único, tipo, piso, coeficiente y superficie, la pertenencia de las unidades a los grupos de reparto con
el modo de coeficientes de cada grupo parcial, y el estado de migración del edificio, que para el
edificio de ejemplo MUST ser `sin_saldos_previos` (R09, D-083). La versión del archivo MUST ser
exactamente 1. MUST NOT contener datos personales: ni nombres de personas, ni emails, ni teléfonos, ni
documentos, ni direcciones reales.

El edificio de ejemplo SHALL declarar su ubicación con los tres ids de Georef (provincia, departamento
y localidad) en lugar de la localidad como texto libre, y su cantidad de pisos sobre planta baja y de
subsuelos. El piso de cada unidad MUST salir del vocabulario de pisos de ese edificio: las cuatro
unidades que hoy dicen `"SS"` (las cocheras `C1` a `C3` y la baulera `B1`) MUST pasar al subsuelo
numerado. La calle y el número MUST ser una dirección inventada, nunca una real.

#### Scenario: El archivo no tiene datos personales

- **WHEN** se busca en el archivo de semilla cualquier campo de persona o contacto, o un texto con
  forma de email o teléfono
- **THEN** no hay ninguno

#### Scenario: Estado de migración del ejemplo

- **WHEN** se lee la semilla del repositorio
- **THEN** el estado de migración es `sin_saldos_previos`

#### Scenario: Versión distinta de 1

- **WHEN** la semilla declara `version: 2` o `version: "1"`
- **THEN** el lector falla nombrando el campo version

#### Scenario: Ubicación del ejemplo

- **WHEN** se lee la semilla del repositorio
- **THEN** el edificio trae los tres ids de ubicación, coherentes entre sí contra el archivo de Georef, y
  ya no una localidad de texto libre

#### Scenario: Pisos del ejemplo

- **WHEN** se lee la semilla del repositorio
- **THEN** el edificio declara 4 pisos y al menos 1 subsuelo, y cada unidad tiene un piso de ese
  vocabulario: `PB` el local, `1` a `4` los departamentos y el subsuelo numerado las tres cocheras y la
  baulera

#### Scenario: Semilla con un piso fuera del vocabulario

- **WHEN** la semilla declara una unidad en el piso `"5"` o en `"SS"` en un edificio de 4 pisos y 1
  subsuelo
- **THEN** el lector falla nombrando el campo piso y la unidad

#### Scenario: Semilla con una ubicación incoherente

- **WHEN** la semilla declara una localidad que no pertenece al departamento declarado
- **THEN** el lector falla nombrando el campo de la localidad

### Requirement: Semilla validada contra los parámetros

El lector de la semilla SHALL rechazar, nombrando el campo y la unidad, un archivo con: tipos de
unidad que no están en los parámetros, grupos que no están en los parámetros, identificadores de
unidad repetidos, unidades de un grupo que no existen, coeficientes que no son texto decimal positivo
con hasta 6 decimales, coeficientes de "Generales" o de un grupo con modo `propios` cuya suma se aparta
de 1 más de 0,0001, un modo de grupo fuera de `renormalizado` o `propios`, un miembro con coeficiente
propio en un grupo `renormalizado` o sin él en uno `propios`, un estado de migración fuera de
`pendiente`, `confirmada` o `sin_saldos_previos`, superficies que no son texto decimal positivo, y los
mismos errores de formato que el lector de parámetros (YAML mal formado, claves duplicadas, campos
faltantes o desconocidos). Un grupo sin modo MUST leerse como `renormalizado`. Una suma que se aparta
de 1 hasta 0,0001 inclusive MUST aceptarse con una advertencia que diga la diferencia (R01, D-082),
sin redondear para que cierre. La validación de la suma MUST usar la misma función que el informe de
la API.

#### Scenario: La semilla del repositorio es válida

- **WHEN** se lee la semilla del repositorio con los parámetros del repositorio
- **THEN** la lectura es exitosa, los coeficientes suman exactamente 1, sin advertencia, el grupo
  "Generales" abarca todas las unidades y los grupos parciales son `renormalizado`

#### Scenario: Coeficientes dentro de la tolerancia

- **WHEN** a la semilla se le cambia un coeficiente de modo que la suma da 0.9999
- **THEN** la lectura es exitosa con una advertencia que dice la diferencia "-0.000100"

#### Scenario: Coeficientes que no suman 1

- **WHEN** a la semilla se le cambia un coeficiente de modo que la suma da 0.9998
- **THEN** el lector falla diciendo que los coeficientes no suman 1 y la diferencia, sin redondear

#### Scenario: Grupo con coeficientes propios en la semilla

- **WHEN** a la semilla se le pone el grupo "Cocheras" en modo `propios` con coeficientes que suman
  0.9998
- **THEN** el lector falla nombrando el grupo y la diferencia; con coeficientes que suman 1, la lectura
  es exitosa

#### Scenario: Tipo de unidad desconocido

- **WHEN** una unidad tiene tipo `quincho`
- **THEN** el lector falla nombrando la unidad y el campo tipo

### Requirement: Verificación de la semilla por comando

El sistema SHALL ofrecer un comando que lee y valida la semilla contra los parámetros y termina con
código 0 si es válida o distinto de 0 con los errores si no. En este cambio el comando MUST NOT
escribir en la base.

#### Scenario: Comando sobre la semilla del repositorio

- **WHEN** se corre el comando de verificación sobre la semilla del repositorio, con
  `PROPTECH_PARAMETROS` apuntando a los parámetros del repositorio y sin ninguna variable de
  PostgreSQL definida
- **THEN** termina con código 0, sin intentar conectarse a la base

#### Scenario: Comando sobre una semilla inválida

- **WHEN** se corre el comando sobre una semilla con un error
- **THEN** termina con código 1 y muestra los errores nombrando unidad y campo

### Requirement: Carga del edificio de ejemplo en la base

El sistema SHALL ofrecer un comando explícito que carga el edificio de ejemplo, ya validado, en una
administración de ejemplo propia, con ids fijos, como un edificio más y por los mismos casos de uso
que la API: sus unidades, sus grupos, las categorías y la primera versión de configuración de los
parámetros, y su estado de migración. El comando MUST fijar el tenant de la administración de ejemplo
y MUST NOT tocar ninguna otra administración. Nada lo corre al arrancar. Correrlo otra vez MUST NOT
duplicar nada. El edificio del ejemplo MUST identificarse por el nombre de la semilla dentro de la
administración de ejemplo, de modo que otro edificio con otro nombre no cambie el resultado. La
comparación MUST abarcar lo que sale de la semilla (unidades, grupos y estado de migración) y al
super admin del ejemplo (nombre, email y su asignación de `super_admin`), no lo que viene de los
parámetros (D-042), ni el vínculo con una cuenta de Clerk, ni otras personas de esa administración: si
el ejemplo ya está cargado igual, termina con código 0 diciendo que no hizo nada; si está cargado
distinto, termina con código distinto de 0 sin escribir nada. Una carga a medias MUST NOT quedar: todo
en una transacción. Precondición (D-112): el comando MUST NOT correr salvo que `PROPTECH_ENTORNO` valga
exactamente `desarrollo`; sin eso termina con código distinto de 0, lo dice y no se conecta ni escribe
nada. Los escenarios de abajo suponen esa variable puesta, salvo "Fuera de desarrollo no corre".

#### Scenario: Primera carga

- **WHEN** se corre el comando sobre una base sin el ejemplo
- **THEN** existe la administración de ejemplo con el edificio, sus 13 unidades, sus grupos, sus
  categorías, su configuración y estado `sin_saldos_previos`, y el comando termina con código 0

#### Scenario: Segunda carga igual

- **WHEN** se corre el comando dos veces seguidas
- **THEN** la segunda termina con código 0, dice que el ejemplo ya estaba y los conteos de cada tabla
  no cambian

#### Scenario: Cambiar los parámetros no hace fallar la carga

- **WHEN** después de cargar el ejemplo se cambia la tasa en el archivo de parámetros y se corre el
  comando otra vez
- **THEN** termina con código 0 diciendo que el ejemplo ya estaba, y la configuración del ejemplo no
  cambia

#### Scenario: Dos cargas a la vez

- **WHEN** se corre el comando dos veces en paralelo sobre una base sin el ejemplo, y las dos llegan a
  crear la administración de ejemplo al mismo tiempo
- **THEN** queda un solo edificio de ejemplo, una corrida informa que lo cargó, la otra que ya estaba, y
  ninguna deja datos a medias

#### Scenario: El ejemplo cambió en la base

- **WHEN** después de cargarlo se edita una unidad del ejemplo y se corre el comando otra vez
- **THEN** termina con código distinto de 0, dice qué difiere y no escribe nada

#### Scenario: Cada dato comparado se detecta por separado

- **WHEN** el ejemplo cargado difiere de la semilla en uno solo de estos datos: estado de migración;
  tipo, piso, coeficiente o superficie de una unidad; una unidad de más o de menos; un grupo de más o de
  menos; el modo de un grupo; un miembro de más o de menos en un grupo; el coeficiente de un miembro
- **THEN** el comando termina con código distinto de 0, el mensaje nombra ese dato y no escribe nada

#### Scenario: El mensaje nombra el campo de la unidad

- **WHEN** una unidad del ejemplo difiere de la semilla sólo en su tipo, su piso, su coeficiente o su
  superficie
- **THEN** el mensaje nombra la unidad y ese campo (por ejemplo, `unidades[1A].piso`), y no los otros

#### Scenario: El super admin del ejemplo cambió

- **WHEN** el super admin del ejemplo tiene otro nombre, otro email o perdió su asignación de
  `super_admin`
- **THEN** el comando termina con código distinto de 0, el mensaje nombra ese dato y no escribe nada

#### Scenario: Lo que no cuenta como ejemplo cambiado

- **WHEN** el super admin del ejemplo está vinculado a una cuenta de Clerk, o la administración de
  ejemplo tiene otra persona además de ese super admin
- **THEN** el comando termina con código 0 diciendo que el ejemplo ya estaba

#### Scenario: Otro edificio en la administración de ejemplo

- **WHEN** la administración de ejemplo tiene, además del ejemplo, otro edificio con otro nombre, y la
  base devuelve primero cualquiera de los dos
- **THEN** la comparación mira sólo el del nombre de la semilla, termina con código 0 diciendo que el
  ejemplo ya estaba y el otro edificio no cambia

#### Scenario: El edificio del ejemplo no se puede identificar

- **WHEN** la administración de ejemplo tiene edificios pero ninguno con el nombre de la semilla, o más
  de uno con ese nombre
- **THEN** el comando termina con código distinto de 0 diciendo que el edificio difiere, sin esperar y
  sin escribir nada

#### Scenario: La administración de ejemplo quedó sin edificio

- **WHEN** la administración de ejemplo existe sin ningún edificio y ninguno aparece durante la espera
  acotada del comando
- **THEN** el comando termina con código distinto de 0 con un mensaje propio, sin escribir nada

#### Scenario: El edificio aparece durante la espera

- **WHEN** la administración de ejemplo existe sin edificio y otra corrida confirma el edificio antes de
  que se agote la espera
- **THEN** el comando vuelve a mirar con una sesión nueva, compara y termina con código 0 diciendo que
  el ejemplo ya estaba

#### Scenario: Fuera de desarrollo no corre

- **WHEN** se corre el comando sin `PROPTECH_ENTORNO=desarrollo` (ausente, otro valor, otra mayúscula
  o con espacios)
- **THEN** termina con código distinto de 0, dice que hace falta `PROPTECH_ENTORNO=desarrollo` y no
  se conecta a la base ni escribe nada

#### Scenario: Otras administraciones no se tocan

- **WHEN** se corre el comando en una base que ya tiene otra administración con datos
- **THEN** los datos de esa administración quedan idénticos

### Requirement: Cada error del comando de carga tiene su mensaje y su código

El comando que carga el edificio de ejemplo SHALL terminar cada familia de error con un mensaje propio
en la salida de errores y con su código de salida, sin traceback:

| Código | Significado |
|---|---|
| 0 | Cargado, ya estaba o vinculado |
| 1 | Fuera de desarrollo (D-112) |
| 2 | Uso: argumentos no reconocidos, `--semilla` vacío o id de cuenta con formato inválido |
| 3 | Configuración: variables, parámetros, semilla o Georef inválidos, semilla que el caso de uso rechaza, o instancia de Clerk que no es de desarrollo |
| 4 | La base no es segura para correr: rol con privilegios de más o tablas de sólo agregar desprotegidas |
| 5 | Base no disponible |
| 6 | El ejemplo cargado es distinto |
| 7 | Vinculación de la cuenta rechazada |
| 8 | La carga no se completó: violación de integridad, otro error de la base o espera agotada |
| 9 | Error inesperado: el mensaje nombra sólo su tipo |
| 130 | Interrumpido con Ctrl-C |

El mensaje MUST NOT incluir contraseñas, el id de la cuenta, el emisor, datos de la conexión ni los
parámetros del driver. La guarda de entorno MUST evaluarse antes de leer la configuración. Un error de
uso y `--help` no corren el comando: se resuelven antes de la guarda y no se conectan a la base.

#### Scenario: Fuera de desarrollo, sin ninguna otra variable

- **WHEN** se corre el comando sin `PROPTECH_ENTORNO=desarrollo` y sin ninguna variable de configuración
- **THEN** termina con código 1 por la guarda, no con el código de configuración

#### Scenario: Configuración rota

- **WHEN** una variable obligatoria falta, está vacía o en blanco, tiene un tipo equivocado o está fuera
  de rango, o el archivo de parámetros, la semilla o Georef son inválidos
- **THEN** termina con código 3, nombra el problema sin mostrar el valor recibido y sin traceback, y no
  se conecta a la base. Sólo el lector de la semilla repite un valor: el identificador de una unidad o
  la clave de un grupo, porque su requisito pide nombrarlos

#### Scenario: Un archivo que no se puede leer

- **WHEN** la ruta de `--semilla` o del archivo de parámetros no se puede leer
- **THEN** termina con código 3, dice que no se puede leer el archivo y no repite la ruta

#### Scenario: La ruta de la semilla es una palabra del mensaje

- **WHEN** `--semilla` es una ruta corta o una palabra que también aparece en el mensaje de error
- **THEN** el mensaje queda intacto salvo por la ruta del archivo que no se pudo leer

#### Scenario: El caso de uso rechaza la semilla

- **WHEN** una semilla pasa el lector y el caso de uso la rechaza al cargarla, por ejemplo con `pisos: 0`,
  un identificador de más de 40 caracteres o `estado_migracion: confirmada`
- **THEN** termina con código 3, nombra el campo, sin traceback y sin escribir nada. A diferencia de
  "Configuración rota", ya se conectó a la base, porque el rechazo ocurre durante la carga

#### Scenario: `--semilla` vacío

- **WHEN** se corre con `--semilla=`
- **THEN** termina con código 2, no usa la semilla por defecto y no se conecta a la base

#### Scenario: Se interrumpe con Ctrl-C

- **WHEN** el comando recibe una interrupción mientras corre
- **THEN** termina con código 130, sin traceback, y una carga a medias no queda

#### Scenario: Id de cuenta con formato inválido

- **WHEN** se corre con un `--clerk-usuario` que no tiene el formato permitido
- **THEN** termina con código 2, sin repetir el valor y sin conectarse a la base

#### Scenario: Instancia de Clerk que no es de desarrollo

- **WHEN** se corre con `--clerk-usuario` y un `CLERK_EMISOR` ausente o que no es de desarrollo
- **THEN** termina con código 3, sin repetir el emisor ni el id y sin conectarse a la base

#### Scenario: El rol no es seguro

- **WHEN** las credenciales de la app apuntan a un rol con privilegios de más
- **THEN** termina con código 4, sin traceback y sin escribir nada

#### Scenario: Hay tablas de sólo agregar desprotegidas

- **WHEN** una tabla de sólo agregar no existe en `public` o su dueño no es superusuario
- **THEN** termina con código 4, nombra la tabla, sin traceback y sin escribir nada

#### Scenario: La base está apagada

- **WHEN** nada escucha en el host y puerto configurados
- **THEN** termina con código 5, sin traceback y sin mostrar los datos de la conexión

#### Scenario: La base no responde

- **WHEN** el host configurado no contesta
- **THEN** termina con código 5 dentro del límite de conexión configurado, sin traceback

#### Scenario: El ejemplo es distinto

- **WHEN** el ejemplo cargado difiere de la semilla
- **THEN** termina con código 6 y dice qué difiere

#### Scenario: Vinculación rechazada

- **WHEN** la cuenta ya está vinculada a otra persona del ejemplo, o el ejemplo ya está vinculado a otra
  cuenta
- **THEN** termina con código 7, con su mensaje propio y sin repetir el id

#### Scenario: La carga no se completa

- **WHEN** la escritura viola una restricción de la base o se agota la espera del edificio
- **THEN** termina con código 8, sin traceback, sin los parámetros del driver y sin escribir nada

#### Scenario: Error inesperado

- **WHEN** ocurre una excepción que ninguna familia contempla
- **THEN** termina con código 9 nombrando sólo el tipo de la excepción, sin su texto ni traceback

### Requirement: El comando de carga corre sin Redis

El comando que carga el edificio de ejemplo SHALL correr sin `REDIS_HOST` ni `REDIS_PASSWORD`, porque no
usa Redis. La API y el worker MUST seguir negándose a arrancar sin ellas.

#### Scenario: Carga sin variables de Redis

- **WHEN** se corre el comando con la configuración de la base y de parámetros, y sin ninguna variable de
  Redis
- **THEN** carga el ejemplo y termina con código 0

#### Scenario: La API y el worker siguen exigiendo Redis

- **WHEN** se lee la configuración de la API y del worker sin `REDIS_HOST` o sin `REDIS_PASSWORD`
- **THEN** la lectura falla nombrando la variable, igual que antes de este cambio
