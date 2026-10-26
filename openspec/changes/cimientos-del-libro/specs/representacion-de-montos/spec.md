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

#### Scenario: Sumar un número que no es monto

- **WHEN** se suma el monto `"1.00"` con el `int` `1`, el `float` `0.5` o el `Decimal` `"0.5"`
- **THEN** cada operación falla con un error de tipo

#### Scenario: Desborde

- **WHEN** se suman dos montos de `"999999999999.99"`
- **THEN** la suma falla con el error de monto inválido

#### Scenario: Sumar una lista vacía

- **WHEN** se suman los montos de una lista vacía con la función de suma de montos
- **THEN** el resultado es `"0.00"`

### Requirement: Un monto con ceros de más se rechaza

Un texto con más de dos decimales SHALL rechazarse aunque los decimales sobrantes sean ceros: el monto
nunca normaliza en silencio la entrada (deuda D-053).

#### Scenario: Ceros de más

- **WHEN** se construye un monto desde `"1.0000"` o `"1.000"`
- **THEN** cada construcción falla con el error de monto inválido
