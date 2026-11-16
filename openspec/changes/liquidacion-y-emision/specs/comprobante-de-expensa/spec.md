# Spec Delta

## Purpose

El comprobante de la expensa de cada unidad: un PDF por variante, generado por el worker a partir de lo
emitido, archivado sin cambios (CCyC art. 2067 inc. i) y descargable sólo con un enlace firmado que vence
(R19, D-060, D-070, D-106, D-158).

## ADDED Requirements

### Requirement: Un PDF archivado por unidad y variante

Al emitir SHALL crearse un documento por unidad con obligación y por variante; el worker SHALL generarlo
desde lo guardado en la liquidación, a través del corte de H-016; un documento generado MUST NOT
reescribirse. Si la cola falla, la emisión SHALL salir igual y los documentos quedar pendientes.

### Requirement: Descarga sólo con enlace firmado

El PDF MUST NOT tener una dirección pública: se descarga con un enlace firmado que vence a los 15 minutos;
el inquilino sólo SHALL recibir la variante sin extraordinaria.

#### Scenario: Documentos de una emisión

- **WHEN** se emite noviembre
- **THEN** hay dos documentos por unidad (completa y sin extraordinaria) en pendiente, y al generarlos quedan generados

#### Scenario: Lo que dice la expensa

- **WHEN** se descarga la expensa completa de `1B`
- **THEN** dice el edificio, la unidad, el código `TF-1B`, el período, el vencimiento, las categorías, la multa, el fondo, el saldo anterior y el total de $48.350,00

#### Scenario: La expensa del inquilino

- **WHEN** se descarga la variante sin extraordinaria de `1B`
- **THEN** no muestra la extraordinaria y su total es $33.350,00

#### Scenario: Redis caído al emitir

- **WHEN** Redis no contesta al emitir
- **THEN** la emisión sale igual, los documentos quedan pendientes y el reproceso los encola

#### Scenario: Generación que falla

- **WHEN** el PDF de `1A` no se puede generar
- **THEN** queda fallido con su motivo y el reproceso lo deja generado

#### Scenario: Enlace firmado

- **WHEN** se pide un enlace
- **THEN** vence a los 15 minutos; vencido da 410 y alterado 403

#### Scenario: Quién descarga qué

- **WHEN** propietario e inquilino de `1B` piden enlaces
- **THEN** el propietario recibe las dos variantes y el inquilino sólo la sin extraordinaria

#### Scenario: El PDF archivado no se reescribe

- **WHEN** después de generarlo se renombra una categoría, cambia el fondo y se reprocesa
- **THEN** el PDF es el mismo byte por byte
