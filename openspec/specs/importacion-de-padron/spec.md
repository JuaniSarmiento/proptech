# importacion-de-padron Specification

## Purpose
Carga el padrón de un edificio desde la plantilla de Excel (unidades y propietarios) validando el archivo
entero antes de escribir nada, con un informe por hoja, fila, columna y motivo (HU-A2, R09, D-128).

## Requirements

### Requirement: La plantilla se lee por nombre de hoja y de encabezado

El importador SHALL buscar las hojas `Unidades`, `Saldos` y `Control` y sus encabezados por nombre exacto
en la fila 1, cualquiera sea su orden. Un archivo que no es un `.xlsx` válido, que supera 2 MiB, con una
hoja de más de 2.000 filas, sin una hoja obligatoria o sin un encabezado obligatorio MUST rechazarse
entero sin leer filas, nombrando el problema.

#### Scenario: Columnas en otro orden

- **WHEN** la hoja `Unidades` trae las columnas en el orden `Email, Piso, Unidad, Superficie m2, Tipo,
  Coeficiente, Propietario`
- **THEN** el archivo se lee igual que con el orden de la plantilla

#### Scenario: Falta un encabezado

- **WHEN** la hoja `Unidades` no tiene la columna `Coeficiente`
- **THEN** se rechaza el archivo nombrando la hoja `Unidades` y la columna `Coeficiente`, y no se crea
  ninguna unidad

#### Scenario: No es un Excel

- **WHEN** se sube un `.csv` o un PDF renombrado a `.xlsx`
- **THEN** se rechaza nombrando el archivo y no se escribe nada

#### Scenario: Archivo enorme

- **WHEN** se sube un archivo de 3 MiB, o una hoja con 2.001 filas de datos
- **THEN** se rechaza nombrando el límite y no se escribe nada

### Requirement: Todo o nada, con todos los errores juntos

Ante cualquier error de fila, el importador SHALL rechazar la carga entera, sin crear unidades, personas
ni borrador, y MUST informar **todos** los errores del archivo, cada uno con hoja, fila del Excel (el
encabezado es la fila 1), columna y motivo.

#### Scenario: Un solo error no carga nada

- **WHEN** un archivo de 12 unidades tiene el piso `Entrepiso` en la fila 9
- **THEN** no se crea ninguna unidad y el informe trae un error: hoja `Unidades`, fila 9, columna `Piso`

#### Scenario: Varios errores juntos

- **WHEN** un archivo tiene la fila 3 con `Tipo` vacío y la fila 7 con `Superficie m2` en `0`
- **THEN** el informe trae los dos errores y no se crea nada

### Requirement: Cada fila de Unidades se valida como el alta manual

Cada fila SHALL validarse con las reglas del alta manual: `Unidad` de 1 a 40 caracteres sin caracteres de
control, única en el archivo y en el edificio; `Tipo` exacto (`departamento`, `cochera`, `baulera`,
`local`); `Piso` exacto del vocabulario del edificio (`SS1`…, `PB`, `1`…), sin recortar ni traducir;
`Coeficiente` mayor que 0, hasta 1 y con hasta 6 decimales; `Superficie m2` mayor que 0 con hasta 2
decimales. El edificio MUST tener pisos y subsuelos configurados.

#### Scenario: Unidad repetida

- **WHEN** las filas 4 y 11 tienen la unidad `2B`
- **THEN** se rechaza con un error en la fila 11 que nombra la fila 4

#### Scenario: Piso fuera del vocabulario

- **WHEN** el edificio tiene 3 pisos y 1 subsuelo, y una fila trae `4`, otra `1°` y otra ` PB`
- **THEN** las tres son error de la columna `Piso`

#### Scenario: Celda vacía obligatoria

- **WHEN** una fila tiene `Piso` vacío
- **THEN** es error de la columna `Piso`

#### Scenario: Edificio sin pisos configurados

- **WHEN** el edificio no tiene pisos ni subsuelos cargados
- **THEN** se rechaza el archivo nombrando `piso` y pidiendo configurarlos primero

### Requirement: Los números nunca pasan por float

Una celda numérica SHALL convertirse a decimal exacto desde su representación (una celda `8.3e-05` es
`0.000083`); un texto con coma decimal (`1.234,56`, `0,083333`) o con punto decimal sin coma
(`1234.56`) se acepta; un texto ambiguo (`1.234`) o con más decimales de los permitidos MUST ser error de
fila, nunca se redondea. Una fórmula se lee por su valor en caché; sin valor en caché es error de fila.

#### Scenario: Coma decimal

- **WHEN** el coeficiente viene como texto `0,083333`
- **THEN** la unidad queda con coeficiente `0.083333`

#### Scenario: Siete decimales

- **WHEN** el coeficiente es `0.0833333`
- **THEN** es error de la columna `Coeficiente`, sin redondear

#### Scenario: Fórmula sin valor en caché

- **WHEN** una celda de `Superficie m2` tiene la fórmula `=40+5` guardada sin su resultado
- **THEN** es error de esa celda

### Requirement: La suma de coeficientes respeta la tolerancia de R01

La suma de `Coeficiente` de todas las filas SHALL compararse con 1 con la tolerancia de R01 (±0,0001,
borde incluido): fuera de la tolerancia MUST rechazarse el archivo; dentro, distinta de 1, se carga con
una advertencia (E4).

#### Scenario: Suma 0,9999

- **WHEN** los coeficientes suman `0.9999`
- **THEN** se carga el padrón con la advertencia "los coeficientes suman 0,9999"

#### Scenario: Suma 0,9998

- **WHEN** los coeficientes suman `0.9998`
- **THEN** se rechaza el archivo con un error que nombra la suma y la tolerancia, y no se crea nada

### Requirement: El padrón crea unidades y propietarios sin invitar

Con el archivo válido, el importador SHALL crear cada unidad (con su auditoría de alta), agregarla al
grupo general con su coeficiente y, si la fila trae `Propietario`, crear o reusar por email la persona y su
asignación de vecino propietario sobre la unidad, **sin enviar invitación** (E3). Un email repetido en
dos filas es la misma persona propietaria de las dos unidades.

#### Scenario: Doce unidades con propietarios

- **WHEN** se importa un archivo válido de 12 unidades, 10 con propietario y email
- **THEN** el edificio tiene 12 unidades, 10 propietarios asignados y ninguna invitación encolada

#### Scenario: Propietario sin email

- **WHEN** una fila trae `Propietario` = `Persona Ficticia Uno` sin email
- **THEN** se crea la persona sin email, asignada como propietaria

#### Scenario: Email inválido

- **WHEN** una fila trae el email `no-es-un-email`
- **THEN** es error de la columna `Email`

### Requirement: Un padrón ya cargado no se vuelve a importar

Si el edificio ya tiene unidades, la hoja `Unidades` SHALL faltar o venir vacía; una fila en ella MUST ser
error. El mismo archivo (misma huella SHA-256) subido de nuevo al mismo edificio MUST rechazarse
nombrando la importación anterior (E7).

#### Scenario: Mismo archivo dos veces

- **WHEN** se sube dos veces el mismo `padron-torre-ficticia.xlsx`
- **THEN** la segunda se rechaza con conflicto en `archivo` y el edificio sigue con 12 unidades

#### Scenario: Padrón sobre unidades existentes

- **WHEN** el edificio ya tiene unidades y el archivo trae filas en `Unidades`
- **THEN** se rechaza nombrando la hoja `Unidades`

### Requirement: Importar respeta permisos, tenant y estado

Subir SHALL exigir el permiso `importar_padron_y_saldos` (super admin, administrador principal o
administrador del edificio) en el edificio, que MUST ser de la administración de la sesión y estar con la
migración `pendiente`. Se audita.

#### Scenario: Consejo o vecino

- **WHEN** un miembro del consejo o un vecino intenta importar
- **THEN** se rechaza con 403 y no se escribe nada

#### Scenario: Edificio de otra administración

- **WHEN** la administración B importa sobre un edificio de A
- **THEN** se rechaza con 404

#### Scenario: Importador cerrado

- **WHEN** el edificio está en `confirmada` o `sin_saldos_previos`
- **THEN** se rechaza con conflicto en `estado_migracion`
