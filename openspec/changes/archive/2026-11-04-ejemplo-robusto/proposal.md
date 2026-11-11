## Why

El comando que carga el edificio de ejemplo dice que detecta un ejemplo cambiado y que aguanta dos cargas a la vez, pero sus tests no lo vigilan: cuatro mutantes de la comparación sobreviven, el test de concurrencia pasa aunque los hilos corran uno después del otro y los errores de configuración, rol o base salen como traceback con el mismo código. Es la deuda que la revisión del PR #1 de `acceso-de-desarrollo` dejó para "el próximo cambio que toque `ejemplo.py`" (D-110) y que D-138 adelantó a este change (ficha 3f, C-27).

Hay además un defecto que la deuda daba por imposible: la ficha dice que "nada crea" un segundo edificio en la administración de ejemplo, pero un `super_admin` vinculado con `--clerk-usuario` lo puede crear desde la API (`POST /complejos`, `Accion.CREAR_EDIFICIO`). Con eso, `LIMIT 1` sin `ORDER BY` puede comparar contra el edificio equivocado y dar un falso "el ejemplo cambió".

## What Changes

- **QA-2**: un test por cada rama de la comparación, con su propia aserción. Cubre los mutantes M5 a M8 (modo de los grupos, estado de migración, tipo y piso de la unidad, conjunto de grupos) y también las ramas que tampoco tienen test y la ficha no nombra: superficie, conjunto de unidades, miembros del grupo y coeficiente del miembro. El mensaje de una unidad pasa a nombrar el campo (`unidades[1A].piso`), porque hoy sólo nombra la unidad.
- **QA-7 y DB-3**: el test de dos cargas fuerza la carrera con una barrera y da rojo si los hilos se serializan. La rama de "se agotaron los intentos" y la de "el edificio apareció entre dos intentos" tienen su test.
- **DB-4**: el edificio del ejemplo se identifica por el nombre de la semilla, sin `LIMIT 1`. Otro edificio con otro nombre no molesta; un ejemplo renombrado o con el nombre duplicado termina como "ejemplo distinto". La comparación también mira al super admin del ejemplo, leído con `listar_personal` de `acceso.aplicacion`, sin SQL nuevo ni cambios en `acceso`.
- **BE-3**: cada familia de error tiene su mensaje propio, sin traceback ni datos de la conexión, y su código de salida. **BREAKING** sólo para quien mire el código numérico: las fallas que hoy salen con 1 pasan a tener otro código, salvo la guarda de entorno, que conserva el 1 por D-112. Ningún script del repo depende de esos códigos (`rg` sobre `infra/` y `.github/`).
- **QA-3**: el comando deja de exigir `REDIS_HOST` y `REDIS_PASSWORD`, con una lectura de configuración propia. La API y el worker siguen exigiéndolas.
- **QA-5**: un test de guarda da rojo si aparece `backend/desarrollo/` o `infra/compose.desarrollo.yaml`.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `datos-semilla`: la comparación suma al super admin del ejemplo y la identificación del edificio por nombre; se agregan el contrato de errores del comando y que corre sin Redis.

`acceso-de-desarrollo` no cambia: sus escenarios piden "código distinto de 0" y siguen valiendo; QA-5 sólo vigila un escenario que ya existe.

## Impact

- `backend/src/proptech_core/complejos/aplicacion/ejemplo.py`: identificación del edificio, comparación de la persona y contrato de errores en `_main`.
- `backend/src/proptech_core/compartido/configuracion.py`: lectura nueva para el comando y salida del parámetro `clerk_emisor` de `Configuracion`, que sólo usa `ejemplo.py`. **Consumidores que no pueden cambiar**: `proptech_api` y `proptech_worker` siguen con `Configuracion` y su exigencia de Redis.
- `backend/src/proptech_core/compartido/base_de_datos.py`: sólo el tipo que acepta `crear_engine`.
- `backend/tests/integracion/test_ejemplo_casos_de_uso.py`: tests nuevos y ajuste de los que fijan el código 1 (`:554`, `:642`, `:1020`).
- `backend/tests/integracion/test_arranque_tablas_protegidas.py`: sólo el caso `ejemplo`, que deja de esperar la excepción y exige el código 4 con la tabla en el mensaje. Es el único consumidor de `_main` fuera del test del comando. **Consumidores que no pueden cambiar**: sus casos `api`, `worker` y `alta_inicial`.
- Un test nuevo de guarda en `backend/tests/unitarios/`.
- `README.md`: tabla de códigos de salida en "Entrar con el edificio de ejemplo".
- Sin migraciones, sin permisos nuevos y sin cambios en la web.

## Fuera de este cambio

- AR-5: mover `ejemplo.py` a una raíz de composición (descartado en el 2d, D7/E7).
- DB-5: borrar el ejemplo (no se puede, por diseño).
- El recorrido del README por otra persona (5.4 del 2d).
- `acceso/aplicacion/alta_inicial.py`, gemelo de este comando con el mismo traceback y la misma exigencia de Redis. Está en `acceso`, así que no se toca y queda como deuda propuesta para el cierre (L-009).
- Comparar `pisos`, `subsuelos`, la ubicación del edificio y `activo` de un grupo: el spec enumera unidades, grupos y estado de migración. Una semilla que sólo cambia esos datos da "ya estaba" (O2 del rompedor). Queda como deuda propuesta para el próximo change que toque `ejemplo.py`.
- Una base lenta (L-001): el comando no tiene `statement_timeout`. Es un comando de desarrollo que un humano corre a mano; se prueba apagada y sin responder, y lenta queda declarada como no cubierta.
- El CRLF de los scripts de `infra/` en Windows, que hace caer a `respaldos` (repo sin `.gitattributes`): no es de este change; se avisa a Juani y a Gianfranco.

## Gobernanza

**LOW** (D-138, ficha 3f): comando de desarrollo y datos de ejemplo, protegido por la guarda de D-112, sin migraciones, sin permisos y sin escritura nueva. No requiere firma de D-094/D-111. Plan y revisión se juntan en el orquestador (registrado en `tasks.md`); constructor con TDD, rompedor y auditor corren por separado.

**Sube de nivel si**: construir exige tocar `acceso`, la matriz de permisos o `cuenta_corriente`. En ese caso el constructor frena y el ítem sale del change, hacia un firmante.

## Referencias

- **Decisiones**: D-138 (reparto), D-110 (cierre de `acceso-de-desarrollo`), D-112 (guarda y código 1), D-133 (`--clerk-usuario` y sin SQL de `acceso` en `ejemplo.py`), D-042 (la configuración viene de parámetros, fuera de la comparación), D-021 y D-116 (fronteras).
- **Reglas de negocio**: R09 (estado de migración), sólo como dato comparado. Este cambio no modifica ninguna regla.
- **Historias**: no cubre ninguna HU; es una herramienta de desarrollo.

## Lecciones que aplican

| Lección | Cómo se cubre |
|---|---|
| L-019, L-035 (test que no puede dar rojo) | Grupos 1 y 2: cada test se ve fallar con un mutante dirigido |
| L-034, L-049 (el rojo cae en la aserción propia) | 1.1 a 1.4: `match` nombra la rama; el caso "sobra" de M8 evita morir por un `KeyError` |
| L-013, L-061 (mutar y guardar el RED) | Grupos 1 a 6: cada RED con comando, hora y salida en `tasks.md`, antes del commit de producción |
| L-001 (dependencia apagada y sin responder) | 5.3 |
| L-002 (la configuración se rompe de muchas formas) | 4.2: faltante, vacía, en blanco, tipo equivocado y fuera de rango, sin mostrar el valor |
| L-007 (el error de una librería también es salida) | 5.1 a 5.4: mensajes propios; contraseña, id de Clerk y `[parameters:` nunca salen |
| L-009 (el gemelo) | 4.2 para los dos lectores; `alta_inicial.py` declarado como deuda |
| L-016, L-033 (observación que puede dar otro resultado) | 6.1: la guarda exige que exista `infra/` y se prueba contra una copia con el archivo prohibido |
| L-017 (la entrada del escenario) | 3.1: el segundo edificio real, no un resultado simulado |
| L-039 (verificación manual con su paso escrito) | 8.2: comandos y salida del comando real |
| L-005, L-041, L-055, L-063, L-064 (cierre) | 8.1: suite entera, lint, formato y `mypy` igual que el CI, sobre el SHA final |

## Knowledge Base Impact

- `knowledge-base/12_fichas_de_changes.md`: **REWRITE**. Estado de 3f, cierre de sus filas de deuda y corrección de "nada la crea con dos". Suma la deuda de `alta_inicial.py`.
- `knowledge-base/09_decisiones_y_supuestos.md`: **APPEND**. Una decisión de cierre con la tabla de códigos y la identificación del edificio por nombre.
- `knowledge-base/15_lecciones.md`: **APPEND**, sólo si el auditor propone lecciones.
- `CHANGES.md`, `CLAUDE.md` y `AGENTS.md`: estado de C-27, idénticos entre sí los dos últimos.
