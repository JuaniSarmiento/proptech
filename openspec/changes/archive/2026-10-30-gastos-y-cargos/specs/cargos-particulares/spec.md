## Purpose

Define el cargo particular (R14, D-025): un importe que se carga a una sola unidad (el uso del quincho,
una multa aprobada, un consumo), suelto o importado en lote desde un Excel, en borrador hasta
aprobarse, que nunca se reparte entre las demás unidades del edificio.

## ADDED Requirements

### Requirement: Un cargo particular pertenece a una sola unidad

Un cargo particular SHALL llevar unidad, concepto (de 1 a 200 caracteres, sin quedar en blanco),
importe, período y motivo. La unidad MUST pertenecer al mismo edificio y a la misma administración que
el cargo; una unidad de otro edificio MUST responder 404 y la base MUST rechazarlo aunque la aplicación
se equivoque. El importe MUST llegar como texto decimal ASCII de hasta dos decimales, mayor que cero,
guardarse como `NUMERIC(14,2)` y devolverse como texto. El período MUST ser el primer día de un mes. Un
cargo particular MUST NOT llevar grupo de reparto: no se reparte.

#### Scenario: Alta de un cargo particular
- **WHEN** el administrador carga un cargo de 5.000,00 a la unidad 3B con concepto, período y motivo
- **THEN** el cargo queda creado en `borrador`, asociado sólo a esa unidad

#### Scenario: Unidad de otro edificio
- **WHEN** el cargo apunta a una unidad de otro edificio
- **THEN** la API responde 404 y no crea nada; un intento por SQL directo también es rechazado por la base

#### Scenario: Importe con tres decimales
- **WHEN** el importe llega con tres decimales
- **THEN** la API responde 422 nombrando el campo y el formato esperado

#### Scenario: Un cargo no tiene grupo de reparto
- **WHEN** se intenta cargar un cargo particular indicando un grupo de reparto
- **THEN** la API lo rechaza con 422: el campo no existe en el contrato

### Requirement: Un cargo particular aprobado no cambia lo que pagan las demás unidades

Un cargo particular aprobado SHALL afectar únicamente a la cuenta de su unidad. MUST NOT entrar en
ningún total de grupo de reparto, MUST NOT cambiar el importe prorrateado de ninguna otra unidad y MUST
NOT alterar la base de la ordinaria prorrateada de R13. La lectura de cargos aprobados del período MUST
devolverlos agrupados por unidad, como líneas propias, separados de los gastos.

#### Scenario: Sólo afecta a su unidad
- **WHEN** la unidad 3B tiene un cargo particular aprobado de 5.000,00 en el período
- **THEN** la lectura del período devuelve ese cargo sólo bajo la unidad 3B

#### Scenario: No cambia lo que pagan las demás
- **WHEN** se compara el total de cada grupo de reparto con y sin ese cargo particular aprobado
- **THEN** los totales de los grupos son idénticos en los dos casos

#### Scenario: No entra en la base de la ordinaria prorrateada
- **WHEN** se lee la base prorrateable del período
- **THEN** no incluye ningún cargo particular

#### Scenario: Líneas separadas de los gastos
- **WHEN** se lee el período
- **THEN** los cargos particulares llegan en su propia lista por unidad, nunca mezclados con los gastos por grupo

### Requirement: Aprobar un cargo particular

Un cargo particular SHALL nacer en `borrador` y MUST NOT entrar en ningún cálculo hasta aprobarse.
Aprobarlo MUST exigir el permiso `cargar_gastos_y_preparar_liquidacion` y MUST registrarse en la
auditoría en la misma transacción, con la persona, el `request_id`, el edificio, la unidad y el id del
cargo, sin el importe. Aprobar un cargo ya aprobado MUST ser idempotente y MUST NOT dejar una segunda
fila de auditoría. Un cargo aprobado MUST NOT poder cambiar su importe, su unidad ni su período.

#### Scenario: Un cargo en borrador no entra
- **WHEN** la unidad 3B tiene un cargo en `borrador`
- **THEN** la lectura de cargos aprobados del período no lo devuelve

#### Scenario: Aprobación
- **WHEN** el administrador aprueba el cargo
- **THEN** pasa a `aprobado` y aparece en la lectura del período, con una fila de auditoría

#### Scenario: Aprobar dos veces
- **WHEN** el administrador aprueba dos veces el mismo cargo
- **THEN** el cargo aparece una sola vez en la lectura y la auditoría tiene una sola fila

#### Scenario: Editar un cargo aprobado
- **WHEN** se intenta cambiar el importe de un cargo ya aprobado
- **THEN** la API lo rechaza y el importe no cambia

#### Scenario: Sin permiso
- **WHEN** un auxiliar sin el permiso intenta aprobar un cargo
- **THEN** la API responde 403

### Requirement: Importación de cargos particulares desde un Excel

El administrador SHALL poder importar cargos particulares en lote desde una planilla con unidad,
concepto e importe (R14, D-025, D-026). La importación MUST ser **todo o nada**: si alguna fila es
inválida, MUST NOT quedar creado ningún cargo. MUST rechazarse, nombrando la fila y el motivo: una
unidad que no existe en el edificio, una unidad de otro edificio, un importe con más de dos decimales,
un importe cero o negativo, un concepto vacío y una fila sin unidad. Los cargos importados MUST quedar
en `borrador`, igual que los cargados a mano. La respuesta MUST informar cuántos cargos se crearon y,
ante el rechazo, la lista completa de filas con problema, nunca sólo la primera.

#### Scenario: Importación válida
- **WHEN** se importa una planilla con tres filas válidas
- **THEN** quedan creados tres cargos en `borrador` y la respuesta informa que se crearon tres

#### Scenario: Una unidad inexistente aborta todo
- **WHEN** una de las tres filas apunta a una unidad que no existe en el edificio
- **THEN** no queda creado ningún cargo y la respuesta nombra esa fila y el motivo

#### Scenario: Se informan todas las filas con problema
- **WHEN** dos de cinco filas tienen problemas distintos
- **THEN** la respuesta nombra las dos, con su número de fila y su motivo

#### Scenario: Unidad de otro edificio en la planilla
- **WHEN** una fila apunta a una unidad de otro edificio
- **THEN** la importación se rechaza entera

#### Scenario: Importe inválido en la planilla
- **WHEN** una fila trae un importe con tres decimales, o cero, o negativo
- **THEN** la importación se rechaza entera, nombrando esa fila

#### Scenario: Los importados quedan en borrador
- **WHEN** la importación termina bien
- **THEN** ninguno de los cargos creados está aprobado

### Requirement: Un crédito a una unidad no es un cargo negativo

Un cargo particular MUST NOT admitir importes negativos. Una bonificación excepcional o una devolución
a una unidad SHALL registrarse como corrección por la ruta de crédito de corrección del libro,
construida en el cambio 4b (R08, R14), y MUST NOT tener ninguna ruta propia en este módulo.

#### Scenario: Importe negativo rechazado
- **WHEN** se intenta cargar un cargo particular con importe negativo
- **THEN** la API responde 422 y no crea nada

#### Scenario: No hay ruta de crédito en gastos
- **WHEN** se busca en la API de gastos y cargos una operación que acredite plata a una unidad
- **THEN** no existe: ese camino es el de correcciones del libro
