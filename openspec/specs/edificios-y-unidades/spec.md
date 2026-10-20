# edificios-y-unidades Specification

## Purpose
Define cómo nace un edificio dentro de una administración, con los valores de los parámetros del
sistema, cómo se cargan sus unidades con tipo, coeficiente y superficie, y en qué estado de migración
está, sin que ningún dato cruce de edificio ni de administración.

## Requirements

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
una unidad MUST NOT poder cambiar su edificio ni su administración. La base MUST rechazar cualquier
cambio de `complejo_id` o `administracion_id`, también hacia otro edificio de la misma administración
(decisión de Juani, 19/10/2026, R3B-5). Reasignar los mismos valores MUST seguir permitido.

#### Scenario: Mover una unidad por la API

- **WHEN** se edita una unidad mandando otro `complejo_id`
- **THEN** la respuesta es 422 y la unidad sigue en su edificio

#### Scenario: Mover una unidad por SQL

- **WHEN** conectado como `proptech_app` con el tenant de A se actualiza el `complejo_id` de una unidad
  a un edificio de B
- **THEN** la base rechaza la escritura

#### Scenario: Mover una unidad por SQL dentro de la misma administración

- **WHEN** conectado como `proptech_app` con el tenant de A se actualiza el `complejo_id` de una unidad
  a otro edificio de A, sin colisiones de identificador ni referencias que impidan la escritura
- **THEN** la base rechaza la escritura con un error claro y la unidad conserva su edificio

#### Scenario: Cambiar la administración de una unidad por SQL

- **WHEN** conectado como `proptech_app` se cambia `administracion_id`, solo o junto con `complejo_id`
- **THEN** la base rechaza la escritura con el error de pertenencia inmutable

#### Scenario: Editar datos o reasignar las mismas claves por SQL

- **WHEN** conectado como `proptech_app` se edita el identificador o piso sin cambiar la pertenencia,
  incluso asignando a `complejo_id` y `administracion_id` sus valores actuales
- **THEN** la base permite la edición

### Requirement: Estado de migración del edificio

Cada edificio SHALL tener un estado de migración: `pendiente`, `confirmada` o `sin_saldos_previos`
(R09, D-083). Un edificio nuevo MUST nacer `pendiente`. Sólo el super admin y el administrador con
alcance principal MUST poder confirmar "sin saldos previos" (E4 de `roles-de-la-empresa`), y sólo
desde `pendiente`; esa confirmación MUST quedar auditada y MUST NOT poder deshacerse por la API. El
estado `confirmada` MUST NOT poder fijarse desde ninguna ruta de este cambio: lo fija el cambio 5 al
confirmar una importación.

#### Scenario: Confirmar sin saldos previos

- **WHEN** el super admin confirma "sin saldos previos" en un edificio `pendiente`
- **THEN** el estado pasa a `sin_saldos_previos` y queda una fila de auditoría con esa acción

#### Scenario: Un administrador principal confirma

- **WHEN** un administrador principal confirma "sin saldos previos" en un edificio `pendiente` que
  nadie le asignó
- **THEN** el estado pasa a `sin_saldos_previos` y queda una fila de auditoría con esa acción

#### Scenario: Confirmar dos veces

- **WHEN** el super admin confirma "sin saldos previos" en un edificio que ya lo está
- **THEN** la respuesta es 409 y no se agrega otra fila de auditoría

#### Scenario: Volver atrás

- **WHEN** se intenta pasar un edificio `sin_saldos_previos` a `pendiente` o a `confirmada` por la API
- **THEN** no existe ruta que lo permita y el estado no cambia

#### Scenario: Un colaborador confirma

- **WHEN** un administrador por edificio (antes, colaborador "editar") intenta confirmar "sin saldos previos" en su edificio
- **THEN** la respuesta es 403 con el permiso faltante y el estado no cambia

### Requirement: Edificios y unidades sólo dentro del alcance

Listar edificios SHALL devolver sólo los del alcance de la identidad: con alguna asignación de alcance
principal, todos los de su administración; si no, los de sus asignaciones por edificio y los complejos
de sus unidades. Ver, editar o configurar un edificio o una unidad fuera del alcance, de otra
administración o inexistente MUST responder 404, con la misma respuesta en los tres casos.

#### Scenario: Lista de un colaborador

- **WHEN** un administrador por edificio (antes, colaborador) con un solo edificio asignado lista los edificios
- **THEN** recibe sólo ese edificio

#### Scenario: Lista de un contador principal

- **WHEN** un contador principal lista los edificios de una administración con tres edificios
- **THEN** recibe los tres

#### Scenario: Unidad de otra administración

- **WHEN** el super admin de A pide o edita una unidad de B por su id (formato válido, fila que existe)
- **THEN** la respuesta es 404, igual que para un id que no existe

### Requirement: Resumen y puesta a punto del edificio

El resumen de un edificio SHALL informar su nombre, su localidad, la cantidad de unidades, su estado
de migración, el informe de coeficientes de R01 y los seis pasos de puesta a punto, cada uno `hecho` o
`falta`, más `listo_para_liquidar`, que MUST ser verdadero sólo si los seis están `hecho`. El criterio
de cada paso MUST vivir en el servidor y MUST ser éste:

1. **unidades**: el edificio tiene al menos una unidad.
2. **coeficientes**: el edificio tiene unidades y el informe de R01 de "Generales" está `ok` o
   `advertencia`.
3. **grupos**: todo grupo parcial tiene al menos una unidad y todo grupo con coeficientes propios
   tiene su informe `ok` o `advertencia`.
4. **categorías**: el edificio tiene al menos una categoría activa.
5. **intereses y vencimiento**: hay una versión de configuración vigente hoy, en hora de Mendoza.
6. **saldos previos**: el estado de migración no es `pendiente`.

Leer el resumen MUST exigir el mismo permiso que leer la configuración del edificio, con las mismas
respuestas fuera de alcance (404) y sin permiso (403). Montos y proporciones MUST viajar como texto.

#### Scenario: Edificio recién creado

- **WHEN** el titular pide el resumen de un edificio recién creado, sin unidades
- **THEN** recibe nombre, localidad, 0 unidades, estado `pendiente`, los pasos unidades, coeficientes y
  saldos previos en `falta`, los pasos grupos, categorías e intereses y vencimiento en `hecho` (nacen
  con los valores de los parámetros, D-042), y `listo_para_liquidar` falso

#### Scenario: Coeficientes en advertencia

- **WHEN** las unidades de un edificio suman 0,9999
- **THEN** el paso coeficientes está `hecho` y el informe dice `advertencia` con la diferencia

#### Scenario: Coeficientes fuera de tolerancia

- **WHEN** las unidades de un edificio suman 0,9998
- **THEN** el paso coeficientes está `falta` y `listo_para_liquidar` es falso

#### Scenario: Grupo parcial vacío

- **WHEN** el edificio tiene un grupo parcial sin unidades
- **THEN** el paso grupos está `falta`

#### Scenario: Edificio listo para liquidar

- **WHEN** el edificio tiene unidades que suman 1, grupos completos, una categoría activa, una versión
  vigente y estado `sin_saldos_previos`
- **THEN** los seis pasos están `hecho` y `listo_para_liquidar` es verdadero

#### Scenario: El vecino pide el resumen

- **WHEN** un vecino pide el resumen de su edificio
- **THEN** la respuesta es 403, como para el resto de la configuración
