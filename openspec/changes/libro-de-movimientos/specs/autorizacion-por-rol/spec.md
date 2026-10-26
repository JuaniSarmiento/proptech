# Spec Delta

## ADDED Requirements

### Requirement: Corregir un movimiento es de super admin y administrador principal

La matriz de permisos SHALL sumar la acción `corregir_movimiento`, permitida sólo a super admin (SA) y a
administrador principal (AP), con las mismas reglas de alcance que el resto de la matriz: fuera del
alcance 404, dentro y sin permiso 403 con el permiso faltante.

#### Scenario: La fila de la matriz

- **WHEN** se evalúa `corregir_movimiento` en un edificio para cada perfil y alcance
- **THEN** sólo SA y AP pueden; AE, CP, CE, AX, CO, VP y VI no

#### Scenario: La ruta nueva está en el barrido

- **WHEN** corre el barrido de rutas protegidas
- **THEN** la ruta de corrección está en la lista y responde 401 sin identidad, sin tocar la base
