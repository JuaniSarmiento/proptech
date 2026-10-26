## Why

El 4a dejó los controles puestos (fronteras, dueño de las tablas de sólo agregar, reparto, umbral) sobre
un `cuenta_corriente/` vacío. Hoy el sistema sabe cuánto paga cada unidad de cada gasto, pero **no sabe
cuánto debe nadie**: no hay dónde registrar una emisión, una obligación, un pago ni una corrección. Este
change, el **4b** (exploración del 22/10/2026, §8; D-117), construye el núcleo que todo lo demás lee: el
libro de sólo agregar del que sale la deuda de cada cuenta, el orden en que un crédito la baja y la
corrección de un error sin perder el historial. El 4c, el 5, el 7, el 8 y el 10 llaman a estas piezas;
ninguno puede arrancar su parte de plata sin ellas.

Cubre: **HU-A9** (sólo la API: ruta, permiso y contrato de error, D-120), **R04**, **R05** (con los
créditos que no son pagos de D-086), **R06**, **R08**, **R13** (orden de imputación por componente),
**R17** en su efecto sobre el saldo (la emisión anulada no cuenta; la acción de anular la construye el
7), y las decisiones **D-011**, **D-012**, **D-016**, **D-024**, **D-046**, **D-073**, **D-079**,
**D-081**, **D-085**, **D-086**, **D-109.2** (la cuenta de persona, sólo como forma de la tabla),
**D-114.4** y **D-115** (heredadas del 4a), **D-116** y la decisión nueva **D-120** (Juani,
26/10/2026: sin puerto de repositorio para el libro, P-8; la corrección sólo como API, P-6).

## Qué queda fuera

| qué | dónde va | por qué |
|---|---|---|
| Intereses (R03): cálculo, registro y su detalle (días, tasa, base) | 4c | Bloqueado por P53 y P54; el 4b deja la columna `corte` y el tipo de movimiento `interes` para no necesitar un `ALTER` (E10) |
| Saldo inicial (R09), moroso crítico (R20) y el efecto de R30 | 4c | Funciones sobre el 4b; P53 y P54 |
| Deuda **a una fecha pasada** (R20 "vencida", R21 libre deuda) | 4c y 10b | El 4b expone sólo el estado actual (E12); la fecha de corte la define quien la usa |
| Cambio de titular (R32) y la cuenta de persona **en uso** | 4d | Bloqueado por P51 y P52; la tabla `cuenta` ya admite una persona (E1) |
| La acción de anular una liquidación (R17: ventana, motivo en pantalla, distribuida) | 7 | El 4b sólo registra el evento `anulada` y lo excluye del saldo |
| Confirmar, revertir y reimputar pagos (R11, R18, R25) | 8 | El 4b expone el registro de un crédito; el pago real nace en el 8 |
| Condonación (R29), bonificación (R37), baja de deuda (R41) como acciones | 10b, 8 | Son propuestas; el 4b sólo deja su tipo y su destino fijo (D-086) escritos en el libro |
| Pantalla de corrección, `pesos()`, errores de campo, API falsa (explore 4.7, 4.11) | 8 (primera pantalla con plata) | D-120 (P-6): el 4b no trae pantalla, así que no lleva shape de impeccable |
| Una corrección que **sube** la deuda (se cobró de menos) | 7, con un cargo en la emisión siguiente | E6; si Juani la quiere en el 4b, es un tipo más y una tarea más |
| Outbox y encolar | 7 y 15 | El 4b no encola nada (D-116.d) |
| El préstamo de propiedad para un `ALTER` sobre una tabla protegida | El primer change que lo necesite (R23, 6 o 14) | D-115.3; el 4b crea sus tablas desde cero y no altera ninguna protegida |
| R32 sin requisito escrito | 4d | H-01 y H-02 del explore |

## Gobernanza

**CRITICAL** (D-094, D-111): es el libro de la plata de cada unidad, toca la propiedad de tablas en
PostgreSQL, el chequeo de arranque, la matriz de permisos (acceso) y la auditoría. **No se escribe
código** hasta que la sección "Aprobación" quede firmada por Juani, Alberto o Emiliano, con nombre,
fecha y la respuesta a cada elección. Una regla nueva que entre después de la firma necesita firma
propia (L-029).

## Preguntas abiertas de las que el 4b depende, y de las que no

- **P55 y P56** (P-6 y P-8): respondidas por Juani hoy, registradas en D-120.
- **P60 (A-4, Alberto): el fondo de reserva cuando un pago no alcanza.** **El 4b depende de ella**: el
  orden de imputación dentro de un período tiene que poner el fondo de reserva en algún lugar. R15 dice
  que "forma parte de la ordinaria" y no dice si va antes o después del resto de la ordinaria. **Default
  provisorio, a firmar por Juani (E5)**: interés, ordinaria, **fondo de reserva**, extraordinaria. Para
  que la respuesta de Alberto no cueste una migración sobre una tabla que no admite `UPDATE`, el fondo
  se guarda en su propia columna desde el día uno; si Alberto contesta otra cosa, cambia una función
  pura y sus tests, y las imputaciones ya registradas quedan como hechos con el orden que regía cuando
  se hicieron.
- **P51 a P54** (4c y 4d), **P57 a P59** (A-1 a A-3): no se deciden acá y no bloquean el 4b. A-1 cambia
  el desempate del reparto, que el 4b no usa (el reparto lo usa el 7 al armar las obligaciones).

## What Changes

- **Siete tablas nuevas en `cuenta_corriente`** (migración `0023`): `cuenta` (de una unidad o de una
  persona), `emision`, `evento_de_emision`, `obligacion`, `movimiento` e `imputacion`, las seis de sólo
  agregar, del rol de arranque, con RLS forzada, claves compuestas con la administración y claves
  naturales para la idempotencia; y `candado_de_cuenta`, que **no** es de sólo agregar y existe sólo
  para serializar las escrituras de una cuenta (E2: la app no puede `SELECT ... FOR UPDATE` sobre una
  tabla sin permiso de `UPDATE`, EVIDENCIA en design D2).
- **Una emisión por período salvo anulada**, sostenida por la base con un número de intento único por
  edificio y período (E3), sin bloquear el edificio.
- **Orden de imputación** (R04, R13) por período y por componente, con el fondo de reserva provisorio
  (E5) y los destinos fijos de D-086; el excedente queda como crédito a favor (R05).
- **Estado de la cuenta calculado desde el libro**: residual por obligación y componente, crédito a
  favor y saldo anterior (R06), **sin ninguna columna "saldo" ni "pagada"**, excluyendo lo que generó
  una emisión anulada y los movimientos corregidos (E7).
- **Corrección de un error** (R08, HU-A9): contra-asiento de un movimiento, o crédito de corrección por
  un importe imputado con R04 (E6); con motivo obligatorio, responsable e idempotencia por
  `operacion_id`.
- **Permiso nuevo `corregir_movimiento`** para super admin y administrador principal, en la matriz y en
  el vocabulario de la auditoría (migración `0024`, E8).
- **Ruta `POST /api/complejos/{complejo_id}/correcciones`** con 401, 403, 404, 409 y 422 declarados en
  el OpenAPI con los formatos que la API ya usa (E9).
- **Regla de fronteras nueva**: el SQL de cada módulo sólo nombra sus tablas, con excepciones con
  motivo (E11; explore 4.2, diferida por el 4a).
- **Deuda del 4a asignada al 4b** (E13): RB-4, RB-7, QA-6, QA-7, QA-9, QA-12, QA-14, QA-15 y el ensayo de
  roles, que este change vuelve a romper si no se toca.
- **Rollback escrito con su punto de no retorno** (D-114.5): la primera fila en cualquier tabla del libro
  o la primera corrección auditada.
- **D-120** agregada a `knowledge-base/09_decisiones_y_supuestos.md`, y D-040 marcada "corregida en
  parte por D-120".

## Capabilities

### New Capabilities

- `libro-de-movimientos`: qué guarda el libro (cuentas, emisiones, obligaciones, movimientos,
  imputaciones), que sólo se agrega, cómo se identifica cada escritura para no duplicarla y cómo se
  calcula el estado de una cuenta desde él.
- `imputacion-de-creditos`: en qué orden y a qué destino baja la deuda un crédito, qué pasa con lo que
  sobra y cómo se serializan dos créditos de la misma cuenta.
- `correccion-de-movimientos`: cómo se corrige un error sin editar ni borrar, quién puede hacerlo y qué
  contesta la API.

### Modified Capabilities

- `aislamiento-por-administracion`: las seis tablas del libro entran a la lista de sólo agregar;
  `candado_de_cuenta` queda aislada pero fuera de esa lista.
- `autorizacion-por-rol`: la matriz suma `corregir_movimiento`.
- `auditoria-de-acciones`: la corrección de un movimiento queda auditada.
- `fronteras-de-modulos`: el SQL de cada módulo sólo nombra sus propias tablas.

## Impact

- **Backend**: `compartido/tablas_protegidas.py` (seis entradas); `compartido/dinero.py` (RB-7);
  `cuenta_corriente/dominio/` (orden de imputación y estado de cuenta, puros) y
  `cuenta_corriente/aplicacion/` (SQL sobre la `Session` del que llama, D-120); `acceso/dominio/permisos.py`
  (`Accion.CORREGIR_MOVIMIENTO` y su fila); `proptech_api/` (router nuevo y los modelos de error
  declarados una vez). Dos migraciones nuevas (`0023`, `0024`). `roles.py` **no cambia su lógica**: lee
  la lista de D0 (design D1 del 4a).
- **Numeración de migraciones**: el 3c `pulido-de-la-configuracion` (Emiliano) puede tomar también
  `0023`. Quien mergee segundo renumera (`revision` y `down_revision`) y corre la suite completa.
- **Tests**: integración contra PostgreSQL real para todo lo que garantiza la base (L-027 en su sentido
  general: ningún doble en memoria del libro, D-120); `test_fronteras_de_modulos.py`,
  `test_dueno_de_tablas_solo_agregar.py`, `test_catalogo_rls.py`, el barrido de rutas y la matriz crecen.
- **Infra**: `infra/ci/ensayo-roles.sh` tiene que devolver también las seis tablas y sus funciones al
  migrador antes de bajar de `0023` (el mismo defecto que RB-1 del 4a, L-043). `humo.sh` no escribe en
  el libro (a repetir con `rg` en la tarea, L-023).
- **Web**: nada. Sin pantalla (D-120); la corrida de cierre igual corre la suite de web.
- **Dependencias**: ninguna nueva.

## Lecciones que aplican (15_lecciones.md)

| lección | cómo la cubre | tarea |
|---|---|---|
| L-034, L-035 | Todo rojo cae en la aserción que el test dice probar: el módulo existe y devuelve vacío antes del RED; cada garantía nueva tiene un caso verde y un mutante dirigido | todas |
| L-013, L-019 | Los tests que nacen verdes (fijación) se ven fallar con un mutante en una copia o en un `SAVEPOINT`, dicho en el informe | 1.3, 2.x, 3.x, 4.1 |
| L-018, L-036 | La protección de las seis tablas se prueba por el efecto (`UPDATE`, `DELETE`, `TRUNCATE ... CASCADE`, `ON CONFLICT DO UPDATE`); el dueño, con `NO FORCE ROW LEVEL SECURITY` | 1.1, 1.2, 1.3 |
| L-016, L-022 | El chequeo de arranque y el test de catálogo comparan el conjunto entero de tablas protegidas contra su fuente; RB-4 se cierra con un caso que no depende del orden del catálogo | 1.3 |
| L-041 | 1.3 agrega tablas a un chequeo que bloquea el arranque: su verde es la suite completa | 1.3 |
| L-043 | El ensayo de roles y el rollback se corren en un compose aislado y se pega la salida | 1.4 |
| L-007, L-017 | Los errores de la API nombran el campo, nunca el valor; la entrada del RED es la del escenario real | 3.5, 4.3 |
| L-027 | No hay API falsa (sin pantalla); el contrato se prueba contra la app real y su OpenAPI | 4.3 |
| L-029, L-030 | Toda excepción nueva a una regla (escaneo de tablas, permisos) la firma un socio; el constructor no la agrega por su cuenta | 4.1, 4.2 |
| L-031, L-037, L-042 | La corrida de cierre va después de la última vuelta, con el SHA; el CI de la rama se dispara con `workflow_dispatch` y se lee sobre ese SHA | 6.1 |
| L-012 | La deuda del 4a con dueño 4b se cierra o se reasigna con firma, nunca se arrastra en silencio | 5.1, E13 |
| L-045, L-046 | Para los revisores del propose (orquestador): directorios separados; una prueba sobre código propio del revisor es evidencia de ese código | revisión |

## Decisiones de esta propuesta

Juani decidió hoy P-8 y P-6 (D-120). **Tomadas por el proponente, para quien firme**, cada una con su
alternativa descartada y su costo de revertir en `design.md`:

1. `candado_de_cuenta` en vez de `FOR UPDATE` sobre `cuenta` (E2): corrige la premisa de la exploración
   (4.13), que no contó que la app no tiene `UPDATE` sobre una tabla protegida.
2. La columna `intento` para "una emisión por período salvo anulada" (E3), que resuelve el riesgo R-4 del
   explore sin bloquear el edificio.
3. El fondo de reserva en su columna y en tercer lugar del orden (E5), provisorio hasta A-4.
4. La corrección como contra-asiento total o como crédito con R04, y sin corrección que suba la deuda
   (E6).
5. Las imputaciones en exceso vuelven al crédito más reciente (E7).
6. Los formatos de error de hoy, declarados una vez, en vez del esquema nuevo `{tipo, campo}` del explore
   4.8 (E9).
7. Columnas que el 4c y el 8 necesitan, ya en `0023`; lo demás en tablas nuevas, nunca un `ALTER` (E10).
8. El dueño de `administracion` (`acceso`) y las dos excepciones nuevas del escaneo, `lectura.py` y
   `ejemplo.py` (E11). El explore contaba dos rojos; un `rg` de hoy encuentra también `ejemplo.py` (design
   D11).
9. Sólo el estado actual de la cuenta, y la emisión imputa el crédito a favor pendiente (E12).
10. Las funciones del libro no auditan emitir ni anular: lo hace el 7 con sus acciones; sólo la
    corrección registra en `auditoria` (E8).
11. La clave de `imputacion` lleva la corrida (`corrida_id`), no sólo `(movimiento, obligación,
    componente)` como decía el explore (design D3).

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 26/10/2026): `01` a `16` y `README.md`.

| documento | operación | qué |
|---|---|---|
| `09_decisiones_y_supuestos.md` | **APPEND** (ya, en este propose) | D-120: P-8 (sin puerto de repositorio para el libro; acota D-040) y P-6 (corrección sólo API en el 4b). D-040 marcada en su título "corregida en parte por D-120" |
| `09_decisiones_y_supuestos.md` | **APPEND** (al archivar) | Las elecciones E1 a E13 firmadas: modelo del libro, candado, intento, idempotencia, orden provisorio del fondo, corrección, exclusiones, permiso, contrato de error, columnas anticipadas, escaneo, lecturas, deuda del 4a; el cierre del 4b con su firma y resultado |
| `04_modelo_de_datos.md` | **REWRITE** | Dominio `cuenta_corriente` con las siete tablas reales (sacar "planificada" y "a decidir en el design" de `obligacion` y `movimiento`); `liquidacion` del 7 con el mismo id que `emision` (explore 4.2); ERD de lo existente; "Dueño de las tablas de sólo agregar" con las seis; `accion_de_auditoria` con `corregir_movimiento` |
| `05_reglas_de_negocio.md` | **REWRITE** | R04 y R15: dónde va el fondo de reserva (provisorio hasta A-4); R05: qué pasa con una imputación en exceso; R08: las dos formas de corrección; "Dónde vive" en R04, R05, R06 y R08. Por respuestas a preguntas abiertas y hallazgos del código, como permite D-089 |
| `03_actores_y_roles.md` | **REWRITE** | Fila "Corregir un movimiento" en la matriz (SA y AP) |
| `08_arquitectura_propuesta.md` | **REWRITE** | Sin puerto de repositorio para la propia base (D-120); regla del escaneo de tablas; `cuenta_corriente` construido; candado por cuenta |
| `10_preguntas_abiertas.md` | **REWRITE** | P55 y P56 respondidas (D-120); P60 con el default provisorio que firme Juani |
| `11_glosario.md` | **REWRITE** | "cuenta" (de unidad o de persona), "emisión" frente a "liquidación", "obligación", "componente", "imputación", "crédito a favor", "contra-asiento", "intento de emisión" |
| `12_fichas_de_changes.md` | **REWRITE** | Ficha 4b con lo construido y su deuda; "4a · deuda del cierre" con lo que el 4b cerró o reasignó; fichas 4c, 7 y 8 con lo que reciben hecho (columnas anticipadas, `registrar_credito`, `anular_emision`) |
| `CHANGES.md`, `CLAUDE.md`, `AGENTS.md` | **REWRITE** | Estado del 4b |
| `15_lecciones.md` | **APPEND** | Lo que enseñe la construcción; candidata ya: "un `FOR UPDATE` necesita permiso de `UPDATE`: en una tabla de sólo agregar no sirve de candado" |
| `01`, `02`, `06`, `07`, `13`, `14`, `16`, `README.md` | none | El 4b no cambia visión, stack, historias (HU-A9 ya existe), flujos, motor de reglas, forma de trabajo ni fases posteriores |

## Aprobación

Gobernanza CRITICAL (D-094, D-111). La completa, a mano, Juani, Alberto o Emiliano. Ningún agente la
escribe. Cada elección tiene su alternativa descartada y el costo de revertir en `design.md`.

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · Modelo del libro | Seis tablas de sólo agregar (`cuenta` de unidad o de persona, `emision`, `evento_de_emision`, `obligacion` con ordinaria, fondo de reserva y extraordinaria en columnas separadas, `movimiento` de débito o crédito, `imputacion` por componente), todas con `administracion_id`, RLS forzada y FK compuestas; ninguna columna "saldo" ni "pagada" (D1, D3) | |
| E2 · Candado por cuenta | Tabla `candado_de_cuenta` (no protegida, aislada por administración), una fila por cuenta que se crea si falta (`ON CONFLICT DO NOTHING`) y se bloquea con `FOR UPDATE` al principio de toda escritura de esa cuenta; la emisión las bloquea en orden de id; una fila borrada no abre un hueco. Descartado: `FOR UPDATE` sobre `cuenta` (la app no tiene `UPDATE`) y darle `UPDATE` de una columna a la app sobre una tabla protegida (D2) | |
| E3 · Una emisión por período | Columna `intento` con único `(administracion_id, complejo_id, periodo, intento)`; el intento N+1 sólo si los N anteriores están anulados (D4) | |
| E4 · Idempotencia | Claves naturales y `operacion_id` obligatorio en toda escritura del usuario; `ON CONFLICT DO NOTHING` y leer la fila existente; la misma clave con otros datos da 409 (D5) | |
| E5 · Orden de imputación y fondo de reserva | Período más antiguo primero; dentro del período: interés, ordinaria, **fondo de reserva**, extraordinaria; destinos fijos de D-086; **provisorio hasta A-4 (P60)** (D6) | |
| E6 · Corrección | Dos formas: contra-asiento total de un movimiento (el par deja de contar) o crédito de corrección por un importe, imputado con R04; motivo obligatorio; sin corrección que suba la deuda en el 4b; no se rehacen las imputaciones de otros créditos (D7) | |
| E7 · Exclusiones calculadas | No cuentan las obligaciones y movimientos de una emisión anulada, ni los ajustes de interés que compensaban su interés, ni el par corregido; lo imputado en exceso sobre un componente vuelve como crédito a favor, del crédito más reciente al más antiguo (D8) | |
| E8 · Permiso y auditoría | `corregir_movimiento` para SA y AP; la corrección se audita en su transacción (migración `0024`); emitir y anular no se auditan desde el libro, lo hace el 7 (D9) | |
| E9 · Contrato de error | Los formatos que la API ya usa (401, 403 con el permiso faltante, 404 "no encontrado", 409 con el campo, 422 de FastAPI), declarados una vez y exigidos en el OpenAPI de la ruta nueva; descartado el esquema `{tipo, campo}` del explore 4.8 (D10) | |
| E10 · Columnas anticipadas | `movimiento.corte`, `enlazado_a`, `emision_id` y los tipos de crédito de D-086 nacen en `0023`; lo que el 4c o el 8 necesiten además va en una tabla nueva, nunca en un `ALTER` sobre una tabla protegida (D3) | |
| E11 · Escaneo de tablas en SQL | Cada módulo nombra en SQL sólo sus tablas; `administracion` es de `acceso` (el tenant sale del login, D-076); excepciones con motivo: `complejos/aplicacion/escritura.py` (`asignacion_rol`, decidida en el 2.2a), y dos **nuevas**: `complejos/aplicacion/lectura.py` (`persona`, para el autor de una versión) y `complejos/aplicacion/ejemplo.py` (`administracion`, `persona`, `asignacion_rol`: es un comando de carga, AR-5 del 4a) (D11) | |
| E12 · Lecturas y crédito pendiente | El libro expone el estado actual de una cuenta y de un edificio, y el saldo anterior de una emisión; la deuda a una fecha pasada queda para el 4c y el 10b; `registrar_emision` imputa el crédito a favor pendiente de cada cuenta que toca (D12) | |
| E13 · Deuda del 4a y rollback | El 4b cierra RB-4, RB-7, QA-6, QA-7, QA-9, QA-12, QA-14, QA-15 y arregla y corre el ensayo de roles; rollback con punto de no retorno en la primera fila del libro o la primera corrección auditada (D13, Migration Plan) | |

| Firmante (Juani, Alberto o Emiliano) | Fecha | Alcance aprobado |
|---|---|---|
| | | |
