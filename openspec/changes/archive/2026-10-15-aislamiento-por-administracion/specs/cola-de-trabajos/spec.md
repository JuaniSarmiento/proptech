## ADDED Requirements

### Requirement: Las tareas con datos de una administración llevan el tenant validado

Toda tarea que lea o escriba datos de una administración SHALL recibir `administracion_id` como
argumento, validado en modo estricto como UUID antes de tocar la base. Sin él, o con un valor vacío,
malformado o de otro tipo, la tarea MUST fallar sin reintentar, sin ejecutar su efecto y sin escribir
el valor recibido en el log. Con un valor válido, el tenant MUST valer durante toda la tarea, incluidos
los hilos que lance, y MUST NOT pasar a la tarea siguiente del mismo worker.

#### Scenario: Trabajo sin administración

- **WHEN** el worker recibe un trabajo de una tarea con tenant sin `administracion_id` (por ejemplo,
  encolado antes de este cambio)
- **THEN** el trabajo falla una sola vez, sin reintentos, sin efecto, y el log no trae el valor

#### Scenario: Administración malformada

- **WHEN** `administracion_id` llega vacío, en blanco, como número o como texto que no es un UUID
- **THEN** el trabajo falla igual que sin administración

#### Scenario: Dos tareas seguidas

- **WHEN** el mismo worker corre una tarea con el tenant de A y después una con el tenant de B
- **THEN** la segunda ve sólo datos de B

#### Scenario: El tenant llega al hilo

- **WHEN** una tarea con el tenant de A hace su consulta en un hilo
- **THEN** la consulta corre con el tenant de A
