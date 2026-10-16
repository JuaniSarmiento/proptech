## Purpose

Define cómo nace un edificio dentro de una administración, con los valores de los parámetros del
sistema, cómo se cargan sus unidades con tipo, coeficiente y superficie, y en qué estado de migración
está, sin que ningún dato cruce de edificio ni de administración.

## ADDED Requirements

### Requirement: Un edificio nuevo arranca con los valores de los parámetros

Crear un edificio SHALL copiar, en ese momento, los valores de `config/parametros.yaml` que el proceso
leyó al arrancar: la primera versión de la configuración de intereses, vencimiento y fondo de reserva,
las categorías de gasto precargadas y el grupo "Generales" por coeficiente con todas las unidades. El
alta MAY traer la configuración inicial de intereses, vencimiento y fondo de reserva del reglamento
del edificio, con los mismos rangos y reglas que una versión; si la trae, la primera versión MUST ser
esa, vigente desde el día de alta, y no hace falta una segunda versión. El edificio MUST nacer con
estado de migración `pendiente` y con los estados de unidad de R02 desactivados. Cambiar el archivo de
parámetros después MUST NOT alterar ningún edificio ya creado.

#### Scenario: Edificio nuevo con los valores del archivo

- **WHEN** el titular crea un edificio con nombre y localidad
- **THEN** el edificio existe en su administración con 3.00 % mensual, 0 días de gracia, cálculo
  proporcional por día, vencimiento único el día por defecto de los parámetros, fondo de reserva
  0.00 %, las nueve categorías de los parámetros, el grupo "Generales" por coeficiente, estado de
  migración `pendiente` y estados de unidad desactivados

#### Scenario: Edificio nuevo con la configuración de su reglamento

- **WHEN** el titular crea un edificio mandando en el alta tasa "5.00", vencimiento el día 10 y fondo
  de reserva "2.00"
- **THEN** el edificio tiene una sola versión de configuración, vigente desde hoy, con esos valores, y
  ningún pedido posterior del mismo día hace falta para fijarlos

#### Scenario: Cambiar el archivo no toca edificios existentes

- **WHEN** después de crear un edificio se reinicia el proceso con un archivo de parámetros con otra
  tasa y se crea un segundo edificio
- **THEN** el primero conserva su tasa original y sólo el segundo arranca con la nueva

### Requirement: El servidor genera los ids de toda alta

Toda ruta que da de alta algo SHALL generar el id del lado del servidor y tomar la administración de
la identidad. Un cuerpo de alta que trae `id`, `administracion_id`, `complejo_id` o cualquier campo que
la ruta no declara MUST rechazarse con 422 que nombra el campo, sin escribir nada y sin repetir en la
respuesta el valor rechazado. Esto MUST valer para toda ruta de alta presente y futura, verificado por un barrido.

#### Scenario: Alta de edificio con id propio

- **WHEN** el titular manda un alta de edificio con un `id` elegido por él
- **THEN** la respuesta es 422 y no hay ningún edificio nuevo

#### Scenario: Alta de unidad con otra administración en el cuerpo

- **WHEN** el titular de A manda un alta de unidad con `administracion_id` de B
- **THEN** la respuesta es 422, no se escribe nada y la respuesta no trae el id de B

#### Scenario: Una ruta de alta nueva sin cuerpo estricto

- **WHEN** existe una ruta `POST` de dominio cuyo cuerpo acepta un `id` sin rechazarlo
- **THEN** la suite de tests falla nombrando la ruta

#### Scenario: Una ruta de alta nueva sin cuerpo de prueba

- **WHEN** existe una ruta `POST` de dominio para la que el barrido no tiene un cuerpo válido de prueba
- **THEN** la suite de tests falla nombrando la ruta, en vez de saltearla

### Requirement: Unidades con tipo, coeficiente y superficie

Cada unidad SHALL tener un identificador único dentro de su edificio, uno de los cuatro tipos de
D-029 (departamento, cochera, baulera, local), un piso, un coeficiente y una superficie. El
coeficiente MUST llegar como texto decimal ASCII, mayor que 0 y hasta 1, con hasta 6 decimales; la
superficie, como texto decimal ASCII positivo con hasta 2 decimales. Un número JSON en lugar de texto
MUST rechazarse con 422, nombrando el campo y sin repetir el valor. La API MUST devolver estos valores
como texto, nunca como número.

#### Scenario: Alta de unidad válida

- **WHEN** el titular da de alta la unidad "1A", departamento, piso "1", coeficiente "0.100000",
  superficie "60.00"
- **THEN** la unidad queda en el edificio con esos valores y la respuesta los devuelve como texto

#### Scenario: Identificador repetido

- **WHEN** se da de alta una segunda unidad "1A" en el mismo edificio
- **THEN** la respuesta es 409 y queda una sola "1A"

#### Scenario: Mismo identificador en otro edificio

- **WHEN** se da de alta una unidad "1A" en otro edificio de la misma administración
- **THEN** el alta es exitosa

#### Scenario: Coeficiente como número

- **WHEN** el coeficiente llega como `0.1` (número JSON) o la superficie como `60.5`
- **THEN** la respuesta es 422 nombrando el campo, sin el valor

#### Scenario: Coeficiente fuera de forma

- **WHEN** el coeficiente es "0", "-0.1", "1.000001", "0.1234567", "0.1\n" o trae un dígito no ASCII
- **THEN** la respuesta es 422 nombrando el campo

#### Scenario: Tipo desconocido

- **WHEN** la unidad tiene tipo "quincho"
- **THEN** la respuesta es 422 nombrando el campo tipo

### Requirement: Una unidad no cambia de edificio ni de administración

Una unidad SHALL pertenecer a un solo edificio de una sola administración durante toda su vida. Editar
una unidad MUST NOT poder cambiar su edificio ni su administración, y la base MUST rechazar, aunque la
aplicación se equivoque, una unidad que apunte a un edificio de otra administración.

#### Scenario: Mover una unidad por la API

- **WHEN** se edita una unidad mandando otro `complejo_id`
- **THEN** la respuesta es 422 y la unidad sigue en su edificio

#### Scenario: Mover una unidad por SQL

- **WHEN** conectado como `proptech_app` con el tenant de A se actualiza el `complejo_id` de una unidad
  a un edificio de B
- **THEN** la base rechaza la escritura

### Requirement: Estado de migración del edificio

Cada edificio SHALL tener un estado de migración: `pendiente`, `confirmada` o `sin_saldos_previos`
(R09, D-083). Un edificio nuevo MUST nacer `pendiente`. Sólo el titular MUST poder confirmar
"sin saldos previos", y sólo desde `pendiente`; esa confirmación MUST quedar auditada y MUST NOT poder
deshacerse por la API. El estado `confirmada` MUST NOT poder fijarse desde ninguna ruta de este cambio:
lo fija el cambio 5 al confirmar una importación.

#### Scenario: Confirmar sin saldos previos

- **WHEN** el titular confirma "sin saldos previos" en un edificio `pendiente`
- **THEN** el estado pasa a `sin_saldos_previos` y queda una fila de auditoría con esa acción

#### Scenario: Confirmar dos veces

- **WHEN** el titular confirma "sin saldos previos" en un edificio que ya lo está
- **THEN** la respuesta es 409 y no se agrega otra fila de auditoría

#### Scenario: Volver atrás

- **WHEN** se intenta pasar un edificio `sin_saldos_previos` a `pendiente` o a `confirmada` por la API
- **THEN** no existe ruta que lo permita y el estado no cambia

#### Scenario: Un colaborador confirma

- **WHEN** un colaborador "editar" del edificio intenta confirmar "sin saldos previos"
- **THEN** la respuesta es 403 con el permiso faltante

### Requirement: Edificios y unidades sólo dentro del alcance

Listar edificios SHALL devolver sólo los del alcance de la identidad (D-037). Ver, editar o configurar
un edificio o una unidad fuera del alcance, de otra administración o inexistente MUST responder 404,
con la misma respuesta en los tres casos.

#### Scenario: Lista de un colaborador

- **WHEN** un colaborador con un solo edificio asignado lista los edificios
- **THEN** recibe sólo ese edificio

#### Scenario: Unidad de otra administración

- **WHEN** el titular de A pide o edita una unidad de B por su id (formato válido, fila que existe)
- **THEN** la respuesta es 404, igual que para un id que no existe
