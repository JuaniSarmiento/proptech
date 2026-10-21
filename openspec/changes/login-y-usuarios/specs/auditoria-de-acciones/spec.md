## MODIFIED Requirements

### Requirement: Vocabulario cerrado y detalle sin datos sensibles

La acción SHALL ser una de una lista cerrada, formada por los permisos de la matriz de D-106 más los
eventos de acceso que no son permisos (`ingreso_exitoso`, `ingreso_fallido`, `alta_inicial`,
`invitar_personal`, `dar_de_alta_vecino`, `aceptar_invitacion`, `revocar_invitacion`,
`quitar_asignacion`), controlada también por la base: sumar una acción o un evento exige una migración.
El detalle MUST aceptar sólo las claves permitidas para esa acción y MUST NOT contener contraseñas,
tokens, emails, ids de Clerk en claro ni el texto de un error de terceros. Un mismo caso de uso sensible
MUST registrarse con una sola acción y una acción MUST NOT quedar registrada por dos casos de uso que se
pisen sin que la suite lo note.

#### Scenario: Acción fuera de la lista

- **WHEN** se intenta registrar una acción que no está en la lista
- **THEN** la base la rechaza

#### Scenario: Clave no permitida en el detalle

- **WHEN** el detalle trae una clave fuera de las permitidas para esa acción
- **THEN** el registro se rechaza antes de escribir, sin repetir el valor en el error

#### Scenario: Evento de acceso

- **WHEN** se registra `ingreso_exitoso` con el detalle permitido
- **THEN** la base lo acepta, y el detalle no tiene email, token ni id de Clerk

#### Scenario: Dos casos de uso con la misma acción

- **WHEN** dos casos de uso distintos se marcan como sensibles con la misma acción
- **THEN** la suite falla nombrando la acción y los dos casos de uso
