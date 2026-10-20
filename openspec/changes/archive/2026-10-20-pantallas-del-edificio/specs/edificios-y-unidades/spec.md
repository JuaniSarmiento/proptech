## ADDED Requirements

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
