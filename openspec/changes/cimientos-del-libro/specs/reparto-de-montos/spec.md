# Spec Delta

## Purpose

Reparte un total entre partes con suma exacta al centavo (R07, mayor resto) y redondea un monto suelto
medio hacia arriba (D-109.1), como dos operaciones distintas que nunca se mezclan (D-113).

## ADDED Requirements

### Requirement: El reparto suma exacto el total

Repartir un monto entre partes con peso SHALL devolver un monto por parte cuya suma es exactamente el
total, al centavo. Cada parte exacta es el total por su peso dividido por la suma real de los pesos
(R01), sin importar si los pesos suman 1.

#### Scenario: Un millón entre ciento cincuenta

- **WHEN** se reparten $1.000.000,00 entre 150 partes de igual peso
- **THEN** la suma de las 150 partes es $1.000.000,00, 100 partes reciben $6.666,67 y 50 reciben
  $6.666,66

#### Scenario: Una sola parte

- **WHEN** se reparten $1.234,56 entre una sola parte
- **THEN** esa parte recibe $1.234,56

#### Scenario: Pesos que no suman uno

- **WHEN** se reparten $100,00 entre dos partes con pesos 0.4999 y 0.5
- **THEN** la primera recibe $49,99 y la segunda $50,01 (cada parte sobre 0.9999, no sobre 1), y la
  suma da $100,00

#### Scenario: Total cero

- **WHEN** se reparten $0,00 entre tres partes
- **THEN** las tres reciben $0,00

### Requirement: Cada parte se trunca y los centavos que faltan van a los mayores restos

Cada parte exacta SHALL truncarse al centavo hacia cero; los centavos que faltan para el total MUST
asignarse de a uno a las partes con mayor fracción descartada. Ninguna parte MUST apartarse un centavo
o más de su parte exacta. Un total negativo se reparte como el positivo, con el signo cambiado.

#### Scenario: El redondeo por parte se pasaría del total

- **WHEN** se reparten $2,00 entre tres partes de igual peso
- **THEN** dos partes reciben $0,67 y una $0,66, y la suma es $2,00 (redondear cada parte medio hacia
  arriba daría $2,01)

#### Scenario: El centavo va al mayor resto

- **WHEN** se reparten $100,00 entre tres partes con pesos 0.333333, 0.333333 y 0.333334
- **THEN** la tercera recibe $33,34 y las otras dos $33,33

#### Scenario: Mayor resto, no mayor peso

- **WHEN** se reparten $0,05 entre tres partes con pesos 0.6, 0.25 y 0.15
- **THEN** reciben $0,03, $0,01 y $0,01 (dar el centavo al de mayor peso daría $0,04, $0,01 y $0,00)

#### Scenario: Total negativo

- **WHEN** se reparten -$2,00 entre las mismas tres partes de igual peso
- **THEN** reciben -$0,67, -$0,67 y -$0,66, en las mismas partes que en el caso positivo

### Requirement: El empate se resuelve siempre igual

Ante restos iguales, el centavo SHALL ir primero a la parte con menor clave de orden. La clave MUST
ordenar los identificadores en orden natural: tramos de dígitos ASCII como número, tramos de texto sin
distinguir mayúsculas, y un tramo de dígitos antes que uno de texto; el id es el último desempate. El
resultado MUST NOT depender del orden en que llegan las partes.

#### Scenario: Orden natural, no de texto

- **WHEN** se reparten $2,00 en partes iguales entre las unidades "1", "2" y "10"
- **THEN** "1" y "2" reciben $0,67 y "10" recibe $0,66

#### Scenario: Identificadores que empiezan con letra y con número

- **WHEN** se ordenan con la clave los identificadores "L-PB", "1A", "C1", "B1" y "10A" (los de la
  semilla del edificio de ejemplo)
- **THEN** el orden es "1A", "10A", "B1", "C1", "L-PB", sin error

#### Scenario: Mismo resultado con las partes en otro orden

- **WHEN** se repite el reparto anterior 100 veces, con las partes en un orden distinto cada vez
- **THEN** las 100 corridas asignan los mismos montos a las mismas unidades

### Requirement: El reparto rechaza entradas que no puede repartir

Repartir SHALL fallar con un error propio, sin devolver partes, cuando el total no es un monto (un
`float` incluido), no hay partes, una parte tiene peso negativo o que no es decimal exacto, todos los
pesos son cero o dos partes comparten clave.

#### Scenario: Un float como total

- **WHEN** se intenta repartir el `float` `100.0`
- **THEN** falla con el error de reparto y no devuelve partes

#### Scenario: Pesos imposibles

- **WHEN** se intenta repartir entre cero partes, con un peso -0.1, con un peso `float` o con todos los
  pesos en cero
- **THEN** cada intento falla con el error de reparto

### Requirement: Las propiedades del reparto se prueban con entradas generadas

El reparto SHALL tener pruebas de propiedades sobre totales y pesos generados, con un oráculo que
calcula la parte exacta con aritmética racional y no reusa la función de producción. Las propiedades
MUST incluir: suma exacta, distancia menor a un centavo, centavo extra sólo a restos mayores o iguales,
y resultado independiente del orden; la generación MUST forzar empates de resto y mezclar
identificadores que empiezan con letra y con número.

#### Scenario: Un error de fórmula compartido no pasa

- **WHEN** en una copia de la función de producción se reemplaza el truncado por un redondeo medio
  hacia arriba
- **THEN** la prueba de propiedades encuentra un contraejemplo y da rojo en la aserción de suma exacta

#### Scenario: Cada propiedad tiene su mutante

- **WHEN** en copias de la función se desempata por la posición de entrada, se da el centavo al mayor
  peso en vez de al mayor resto, o se deja de normalizar por la suma de los pesos
- **THEN** cada copia da rojo en la propiedad que le corresponde (orden, restos y distancia)

### Requirement: Un monto suelto se redondea medio hacia arriba

Redondear un valor decimal al centavo SHALL usar medio hacia arriba, alejándose del cero en los
negativos, como `REDONDEAR` de Excel (D-109.1, D-113). Es una operación distinta del reparto: el
reparto MUST NOT usarla para sus partes. Un `float` MUST rechazarse.

#### Scenario: El medio sube

- **WHEN** se redondean 0.125, 0.124999 y -0.125
- **THEN** dan $0,13, $0,12 y -$0,13

#### Scenario: Float rechazado

- **WHEN** se intenta redondear el `float` `0.125`
- **THEN** falla con el error de monto inválido
