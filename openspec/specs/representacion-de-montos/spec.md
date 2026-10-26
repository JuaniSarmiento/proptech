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
que no es monto MUST NOT dar igual. El tipo MUST NOT ofrecer multiplicación, división ni ninguna otra
aritmética fuera de la suma, la resta y la negación entre montos.

#### Scenario: Igualdad por valor

- **WHEN** se comparan los montos `"5"` y `"5.00"`
- **THEN** son iguales y tienen el mismo hash

#### Scenario: Comparación con float

- **WHEN** se compara el monto `"0.10"` con el `float` `0.1`
- **THEN** no son iguales

#### Scenario: Sin multiplicación

- **WHEN** se intenta multiplicar o dividir un monto por un número o por otro monto
- **THEN** la operación falla con un error de tipo

### Requirement: Un monto se guarda como NUMERIC(14,2)

Un monto SHALL guardarse en PostgreSQL como `NUMERIC(14,2)` y leerse de vuelta como monto, sin pasar
por `float` en ningún momento.

#### Scenario: Ida y vuelta por PostgreSQL real

- **WHEN** se guarda el monto `"999999999999.99"` en una columna de monto y se lee de vuelta
- **THEN** el valor leído es exactamente `"999999999999.99"` y su tipo es monto

#### Scenario: Float hacia la columna

- **WHEN** se intenta guardar un `float` en una columna de monto
- **THEN** la operación falla antes de llegar a la base

### Requirement: Un monto se puede copiar y serializar sin perder la validación

Un monto SHALL poder copiarse (`copy.copy`, `copy.deepcopy`, `model_copy(deep=True)` de pydantic) y
serializarse con `pickle` en cualquier protocolo. Como es inmutable, una copia MUST devolver el mismo
objeto. La serialización MUST reconstruir el monto desde su texto, de modo que la reconstrucción pase
por la misma validación que la construcción y un contenido inválido falle con el error de monto
inválido.

#### Scenario: Ida y vuelta por pickle

- **WHEN** se serializa un monto con `pickle` en cada protocolo disponible y se lo vuelve a cargar
- **THEN** el resultado es un monto igual al original, con el mismo texto

#### Scenario: Copia superficial y profunda

- **WHEN** se copia un monto con `copy.copy` y con `copy.deepcopy`
- **THEN** las dos devuelven el mismo objeto, sin error

#### Scenario: Copia profunda de un modelo con montos

- **WHEN** un modelo de pydantic con un campo de monto se copia con `model_copy(deep=True)` y se
  serializa y carga con `pickle`
- **THEN** las dos operaciones terminan sin error y el monto conserva su valor

#### Scenario: Pickle con un monto inválido

- **WHEN** se carga un pickle armado a mano cuyo texto de monto es inválido (por ejemplo `"1e3"`)
- **THEN** la carga falla con el error de monto inválido

### Requirement: Suma, resta y negación entre montos

Un monto SHALL sumarse y restarse con otro monto y negarse, devolviendo un monto exacto. Operar con
algo que no es monto (`int`, `float`, `Decimal`, texto) MUST fallar con un error de tipo. Un resultado
fuera del rango de `NUMERIC(14,2)` MUST fallar con el error de monto inválido, nunca truncarse.

#### Scenario: Suma y resta exactas

- **WHEN** se suman `"0.10"` y `"0.20"`, y se resta `"0.30"` al resultado
- **THEN** la suma es `"0.30"` y la resta `"0.00"`

#### Scenario: Negación

- **WHEN** se niega el monto `"12.50"` y el monto `"0.00"`
- **THEN** dan `"-12.50"` y `"0.00"`

#### Scenario: Sumar un número que no es monto

- **WHEN** se suma el monto `"1.00"` con el `int` `1`, el `float` `0.5` o el `Decimal` `"0.5"`
- **THEN** cada operación falla con un error de tipo

#### Scenario: Desborde

- **WHEN** se suman dos montos de `"999999999999.99"`
- **THEN** la suma falla con el error de monto inválido

#### Scenario: Sumar una lista vacía

- **WHEN** se suman los montos de una lista vacía con la función de suma de montos
- **THEN** el resultado es `"0.00"`

### Requirement: Un decimal de la base con ceros de más se acepta si el valor no cambia

Convertir un valor decimal que llega de la base (incluido el resultado de un `SUM()` o de una columna
sin escala) SHALL aceptar ceros de más cuando llevarlo a dos decimales no cambia el valor, y MUST
rechazar con el error de monto inválido todo valor que cambiaría o perdería precisión. Un texto con más
de dos decimales MUST seguir rechazándose, aunque sean ceros (D-114.6, corrige la nota de D-053).

#### Scenario: Ceros de más desde la base

- **WHEN** se convierte el decimal `1.0000`, o el `0.3000` que devuelve un `SUM()` sobre una columna
  sin escala
- **THEN** el monto es `"1.00"` y `"0.30"`, respectivamente

#### Scenario: Un decimal que cambiaría

- **WHEN** se convierte el decimal `1.005` o `1.0001`
- **THEN** la conversión falla con el error de monto inválido, en lugar de redondear

#### Scenario: Ceros de más en texto

- **WHEN** se construye un monto desde el texto `"1.0000"` o `"1.000"`
- **THEN** cada construcción falla con el error de monto inválido
