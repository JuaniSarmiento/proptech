## MODIFIED Requirements

### Requirement: Estado de migración del edificio

Cada edificio SHALL tener un estado de migración: `pendiente`, `confirmada` o `sin_saldos_previos`
(R09, D-083). Un edificio nuevo MUST nacer `pendiente`. Sólo el super admin y el administrador con
alcance principal MUST poder confirmar "sin saldos previos" (E4 de `roles-de-la-empresa`), y sólo
desde `pendiente`; esa confirmación MUST quedar auditada y MUST NOT poder deshacerse por la API. El
estado `confirmada` MUST NOT poder fijarse desde ninguna ruta de este cambio: lo fija el cambio 5 al
confirmar una importación.

#### Scenario: Confirmar sin saldos previos

- **WHEN** el super admin confirma "sin saldos previos" en un edificio `pendiente`
- **THEN** el estado pasa a `sin_saldos_previos` y queda una fila de auditoría con esa acción

#### Scenario: Un administrador principal confirma

- **WHEN** un administrador principal confirma "sin saldos previos" en un edificio `pendiente` que
  nadie le asignó
- **THEN** el estado pasa a `sin_saldos_previos` y queda una fila de auditoría con esa acción

#### Scenario: Confirmar dos veces

- **WHEN** el super admin confirma "sin saldos previos" en un edificio que ya lo está
- **THEN** la respuesta es 409 y no se agrega otra fila de auditoría

#### Scenario: Volver atrás

- **WHEN** se intenta pasar un edificio `sin_saldos_previos` a `pendiente` o a `confirmada` por la API
- **THEN** no existe ruta que lo permita y el estado no cambia

#### Scenario: Un colaborador confirma

- **WHEN** un administrador por edificio (antes, colaborador "editar") intenta confirmar "sin saldos previos" en su edificio
- **THEN** la respuesta es 403 con el permiso faltante y el estado no cambia

### Requirement: Edificios y unidades sólo dentro del alcance

Listar edificios SHALL devolver sólo los del alcance de la identidad: con alguna asignación de alcance
principal, todos los de su administración; si no, los de sus asignaciones por edificio y los complejos
de sus unidades. Ver, editar o configurar un edificio o una unidad fuera del alcance, de otra
administración o inexistente MUST responder 404, con la misma respuesta en los tres casos.

#### Scenario: Lista de un colaborador

- **WHEN** un administrador por edificio (antes, colaborador) con un solo edificio asignado lista los edificios
- **THEN** recibe sólo ese edificio

#### Scenario: Lista de un contador principal

- **WHEN** un contador principal lista los edificios de una administración con tres edificios
- **THEN** recibe los tres

#### Scenario: Unidad de otra administración

- **WHEN** el super admin de A pide o edita una unidad de B por su id (formato válido, fila que existe)
- **THEN** la respuesta es 404, igual que para un id que no existe
