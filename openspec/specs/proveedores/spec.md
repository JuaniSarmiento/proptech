# proveedores Specification

## Purpose
Define los proveedores de cada edificio (R12, D-019): quién emite las facturas que el administrador
carga como gastos, identificado por su CUIT, desactivable y nunca borrable, de modo que un gasto ya
cargado conserve siempre a su proveedor.

## Requirements

### Requirement: Alta de un proveedor del edificio

Cada edificio SHALL tener sus propios proveedores. Un proveedor MUST llevar razón social (de 1 a 200
caracteres, sin quedar en blanco) y CUIT. El CUIT MUST validarse con coincidencia completa y sólo
ASCII: once dígitos y el dígito verificador correcto; un CUIT inválido MUST responder 422 nombrando el
campo y el formato esperado, sin repetir el valor recibido. El CUIT MUST ser único dentro del edificio;
una repetición MUST responder 409. Dos edificios distintos MUST poder tener el mismo CUIT sin
conflicto. Un proveedor MUST pertenecer al mismo edificio y a la misma administración que quien lo
crea, y la base MUST rechazarlo aunque la aplicación se equivoque.

#### Scenario: Alta con CUIT válido
- **WHEN** el administrador crea un proveedor con razón social y un CUIT de once dígitos con el dígito verificador correcto
- **THEN** el proveedor queda creado y activo, y la API lo devuelve entre los proveedores de ese edificio

#### Scenario: CUIT con dígito verificador incorrecto
- **WHEN** el administrador crea un proveedor con un CUIT de once dígitos cuyo dígito verificador no cierra
- **THEN** la API responde 422, nombra el campo `cuit` y describe el formato esperado, sin incluir el valor recibido

#### Scenario: CUIT con caracteres no ASCII o con espacios al borde
- **WHEN** el CUIT llega con dígitos de otro alfabeto, con espacios o con un salto de línea al principio o al final
- **THEN** la API responde 422 y no crea ningún proveedor

#### Scenario: CUIT repetido en el mismo edificio
- **WHEN** el administrador crea un proveedor con un CUIT que ya tiene otro proveedor de ese edificio
- **THEN** la API responde 409 y no crea nada

#### Scenario: El mismo CUIT en dos edificios
- **WHEN** dos edificios de la misma administración dan de alta un proveedor con el mismo CUIT
- **THEN** los dos quedan creados, cada uno en su edificio

#### Scenario: Proveedor de otro edificio por SQL
- **WHEN** se intenta insertar por SQL directo un proveedor cuyo `complejo_id` pertenece a otra administración
- **THEN** la base lo rechaza

### Requirement: Un proveedor se desactiva, nunca se borra

Un proveedor MUST NOT poder borrarse por la API: se desactiva y se puede reactivar, igual que una
categoría de gasto y un grupo de reparto (R16). Un proveedor desactivado MUST seguir existiendo con su
razón social y su CUIT, para que los gastos ya cargados lo conserven, y MUST NOT aparecer entre los
proveedores disponibles para cargar un gasto nuevo. Un gasto ya cargado contra un proveedor
desactivado MUST seguir siendo válido y MUST seguir entrando en el cálculo si está aprobado.

#### Scenario: No existe ruta de borrado
- **WHEN** se busca en la API una operación que borre un proveedor
- **THEN** no existe: la única baja es la desactivación

#### Scenario: Un proveedor desactivado conserva sus gastos
- **WHEN** se desactiva un proveedor que tiene gastos aprobados en el período
- **THEN** esos gastos siguen existiendo con su proveedor y siguen entrando en el cálculo del período

#### Scenario: Un proveedor desactivado no se ofrece para un gasto nuevo
- **WHEN** se piden los proveedores disponibles para cargar un gasto
- **THEN** los desactivados no figuran

#### Scenario: Reactivar
- **WHEN** se reactiva un proveedor desactivado
- **THEN** vuelve a figurar entre los disponibles, con la misma razón social y el mismo CUIT

### Requirement: Alcance y aislamiento de los proveedores

Los proveedores de un edificio SHALL verse sólo desde ese edificio. Un pedido sobre un proveedor de un
edificio fuera del alcance de quien lo hace MUST responder 404, y uno sin el permiso necesario MUST
responder 403, con el orden de chequeo de D7 (cargar el recurso, 404 si no alcanza, 403 si no puede).
Crear, editar, desactivar o reactivar un proveedor MUST exigir el permiso
`cargar_gastos_y_preparar_liquidacion` de la matriz de D-106. El contador y el consejo MUST poder
leerlos dentro de su alcance y MUST NOT poder escribirlos.

#### Scenario: Proveedor de un edificio fuera del alcance
- **WHEN** un administrador con alcance sobre el edificio A pide un proveedor del edificio B
- **THEN** la API responde 404, sin revelar que existe

#### Scenario: Lectura del contador
- **WHEN** un contador con alcance sobre el edificio lista sus proveedores
- **THEN** los ve

#### Scenario: Escritura del contador
- **WHEN** un contador intenta crear un proveedor
- **THEN** la API responde 403

#### Scenario: Aislamiento entre administraciones
- **WHEN** una identidad de la administración A consulta los proveedores con el identificador de un edificio de la administración B
- **THEN** no obtiene ninguna fila, por Row-Level Security además del chequeo de alcance

### Requirement: Crear y editar un proveedor quedan auditados

Crear y editar un proveedor SHALL registrarse en la auditoría, en la misma transacción que la acción,
con la persona, el `request_id` y el edificio. Un pedido de edición que no cambia nada MUST NOT dejar
registro. El detalle MUST guardar el edificio, el id del proveedor y los nombres de los campos que
cambiaron, y MUST NOT guardar el CUIT ni ningún otro valor. Si la acción o su registro fallan, MUST NOT
quedar ni el cambio ni la fila.

#### Scenario: Alta auditada
- **WHEN** se crea un proveedor
- **THEN** queda exactamente una fila de auditoría con la persona, el `request_id`, el edificio y el id del proveedor, sin el CUIT

#### Scenario: Edición sin cambios
- **WHEN** se edita un proveedor mandando exactamente los mismos valores
- **THEN** no queda ninguna fila de auditoría

#### Scenario: La auditoría falla y la acción se revierte
- **WHEN** la escritura de la fila de auditoría falla
- **THEN** el proveedor no queda creado ni editado
