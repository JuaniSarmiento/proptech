# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
