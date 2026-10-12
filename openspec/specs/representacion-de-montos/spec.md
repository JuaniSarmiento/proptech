# representacion-de-montos Specification

## Purpose
Define la única forma de representar un monto en el sistema (D-046, R07): decimal exacto construido
desde texto, texto en el JSON y `NUMERIC(14,2)` en la base, de modo que un `float` no pueda colarse en
ningún punto.

## Requirements

### Requirement: Un monto se construye sólo desde texto

El sistema SHALL representar todo importe con un tipo de monto que se construye desde un texto con el
formato `-?dígitos(.dígitos)?`, con hasta 12 dígitos enteros y hasta 2 decimales. MUST rechazar con
un error propio: `float`, `int`, `bool`, `None`, texto vacío o con espacios, coma decimal, signo `+`,
notación científica, `NaN`, infinito, más de dos decimales y más de 12 dígitos enteros.

#### Scenario: Float rechazado

- **WHEN** se intenta construir un monto desde el `float` `0.1`
- **THEN** la construcción falla con el error de monto inválido

#### Scenario: Texto válido

- **WHEN** se construye un monto desde `"20000"`, `"20000.5"` o `"-730.00"`
- **THEN** el monto queda con exactamente dos decimales: `20000.00`, `20000.50` y `-730.00`

#### Scenario: Entradas inválidas

- **WHEN** se construye un monto desde `"1,50"`, `"1e3"`, `"NaN"`, `" 1.00"`, `"1.005"`, `""`, `True`
  o `100`
- **THEN** cada construcción falla con el error de monto inválido

#### Scenario: Límite de NUMERIC(14,2)

- **WHEN** se construye un monto con 12 dígitos enteros y otro con 13
- **THEN** el primero se acepta y el segundo se rechaza

### Requirement: Un monto se serializa como texto con dos decimales

Un monto SHALL serializarse siempre como texto con dos decimales (`"20000.00"`), tanto al convertirlo
a texto como en el JSON de la API. El cero negativo MUST normalizarse a `"0.00"`. En los modelos de
entrada de la API, un monto MUST rechazarse si llega como número JSON en lugar de texto.

#### Scenario: Ida y vuelta por texto

- **WHEN** un monto construido desde `"1000.1"` se serializa y se vuelve a construir desde ese texto
- **THEN** el texto es `"1000.10"` y el segundo monto es igual al primero

#### Scenario: Número JSON en el cuerpo

- **WHEN** un modelo de entrada con un campo monto recibe `{"importe": 20000.0}`
- **THEN** la validación falla con 422 nombrando el campo; con `{"importe": "20000.00"}` pasa

### Requirement: Comparación sólo entre montos

Dos montos SHALL compararse por igualdad y orden por su valor exacto. Comparar un monto con un número
que no es monto MUST NOT dar igual. El tipo MUST NOT ofrecer suma, resta ni ninguna otra aritmética
en este cambio.

#### Scenario: Igualdad por valor

- **WHEN** se comparan los montos `"5"` y `"5.00"`
- **THEN** son iguales y tienen el mismo hash

#### Scenario: Comparación con float

- **WHEN** se compara el monto `"0.10"` con el `float` `0.1`
- **THEN** no son iguales

### Requirement: Un monto se guarda como NUMERIC(14,2)

Un monto SHALL guardarse en PostgreSQL como `NUMERIC(14,2)` y leerse de vuelta como monto, sin pasar
por `float` en ningún momento.

#### Scenario: Ida y vuelta por PostgreSQL real

- **WHEN** se guarda el monto `"999999999999.99"` en una columna de monto y se lee de vuelta
- **THEN** el valor leído es exactamente `"999999999999.99"` y su tipo es monto

#### Scenario: Float hacia la columna

- **WHEN** se intenta guardar un `float` en una columna de monto
- **THEN** la operación falla antes de llegar a la base
