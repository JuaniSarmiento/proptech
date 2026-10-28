# categorias-de-gasto Specification

## Purpose
Define las categorías de gasto de cada edificio (R16, D-041): arrancan con las de los parámetros y el
administrador las crea, renombra, ordena y desactiva, sin afectar a otros edificios y sin borrar nunca
una categoría.

## Requirements

### Requirement: Categorías propias de cada edificio

Cada edificio SHALL tener sus propias categorías, que arrancan con las de los parámetros al crearlo.
Crear, renombrar, ordenar o desactivar una categoría en un edificio MUST NOT cambiar las de ningún
otro. La clave MUST ser única dentro del edificio y el nombre también, sin distinguir mayúsculas; una
repetición MUST responder 409.

La clave de una categoría nueva SHALL derivarse del nombre cuando el pedido no la traiga, con la misma
regla que los grupos de reparto: minúsculas, sin tildes, los caracteres que no son letras ni dígitos
ASCII reemplazados por guion bajo sin repetirlo, empezando por una letra y recortada a 40 caracteres, y
desempatada con un sufijo numérico si ya existe en el edificio. Un nombre del que no sale ninguna clave
válida MUST responder 422 nombrando el nombre. La API MUST seguir aceptando una clave explícita, para
los parámetros y el importador. La clave de una categoría existente MUST NOT cambiar al renombrarla.

#### Scenario: Agregar una categoría

- **WHEN** el titular agrega "Seguridad nocturna" en el edificio A
- **THEN** A la tiene activa, con la clave `seguridad_nocturna`, y el edificio B de la misma
  administración no

#### Scenario: Renombrar una categoría

- **WHEN** el titular renombra "Limpieza" a "Limpieza y residuos" en A
- **THEN** A muestra el nombre nuevo, la clave sigue siendo `limpieza` y B sigue con "Limpieza"

#### Scenario: Nombre repetido

- **WHEN** se crea "limpieza" en un edificio que ya tiene "Limpieza"
- **THEN** la respuesta es 409

#### Scenario: Clave derivada repetida

- **WHEN** el edificio ya tiene una categoría con clave `varios` y se crea "Varios extra", cuya clave
  derivada colisiona después de recortar
- **THEN** la clave del nuevo se desempata con un sufijo numérico y las dos conviven

#### Scenario: Nombre del que no sale ninguna clave

- **WHEN** el nombre es "123" o "— —"
- **THEN** la respuesta es 422 nombrando el nombre y la categoría no se crea

#### Scenario: Clave explícita inválida

- **WHEN** un cliente de la API manda la clave `Pileta`, `pileta-1` o `1pileta`
- **THEN** la respuesta es 422 nombrando la clave, con el motivo de la regla, sin repetir el valor

### Requirement: Una categoría se desactiva, nunca se borra

Una categoría MUST NOT poder borrarse por la API: se desactiva y se puede reactivar. Una categoría
desactivada MUST seguir existiendo con su nombre, para que los gastos que la usen (cambio 6) la
conserven.

#### Scenario: Desactivar

- **WHEN** el titular desactiva "Varios"
- **THEN** la categoría sigue en el edificio, marcada inactiva, y no aparece entre las activas

#### Scenario: Borrar

- **WHEN** se intenta borrar una categoría
- **THEN** no existe ruta que lo permita y la categoría sigue

### Requirement: Orden explícito

Las categorías de un edificio SHALL tener un orden explícito que el administrador puede cambiar, y la
API MUST devolverlas en ese orden. Reordenar MUST recibir el orden completo de las categorías del
edificio; un orden que omite o repite una categoría, o trae una de otro edificio, MUST rechazarse con
422 sin cambiar nada.

#### Scenario: Reordenar

- **WHEN** el titular manda el orden completo con "Seguridad" primero
- **THEN** la lista vuelve en ese orden

#### Scenario: Orden incompleto

- **WHEN** el orden mandado omite una categoría del edificio
- **THEN** la respuesta es 422 y el orden anterior queda intacto
