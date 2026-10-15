## ADDED Requirements

### Requirement: El backup trae todas las administraciones

El servicio de respaldos SHALL volcar la base con un rol al que Row-Level Security no le filtra
filas, de modo que el backup tenga los datos de todas las administraciones. MUST NOT usar las
credenciales de `proptech_app` ni las de `proptech_migrador`.

#### Scenario: Backup con dos administraciones

- **WHEN** la base tiene complejos de dos administraciones, se genera un backup y se restaura en una
  base aparte
- **THEN** la base restaurada tiene los complejos de las dos, en la misma cantidad que la original

#### Scenario: Credenciales del servicio

- **WHEN** se inspecciona la configuración del servicio de respaldos
- **THEN** su usuario es el rol de arranque, nunca `proptech_app` ni `proptech_migrador`
