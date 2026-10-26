## Why

El 4a dejó los controles puestos (fronteras, dueño de las tablas de sólo agregar, reparto, umbral) sobre
un `cuenta_corriente/` vacío. Hoy el sistema sabe cuánto paga cada unidad de cada gasto, pero **no sabe
cuánto debe nadie**: no hay dónde registrar una emisión, una obligación, un pago ni una corrección. Este
change, el **4b** (exploración del 22/10/2026, §8; D-117), construye el núcleo que todo lo demás lee: el
libro de sólo agregar del que sale la deuda de cada cuenta, el orden en que un crédito la baja y la
corrección de un error sin perder el historial. El 4c, el 5, el 7, el 8 y el 10 llaman a estas piezas;
ninguno puede arrancar su parte de plata sin ellas.

Cubre: **HU-A9** (sólo la API: ruta, permiso y contrato de error, D-120), **R04**, **R05** (con los
créditos que no son pagos de D-086), **R06**, **R08**, **R13**, **R14** (orden de imputación por componente),
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
| Cargo cobrado de menos; ajuste de saldo inicial bajo R09 | 7: cargo complementario con motivo y vínculo al origen; 4c: ajuste trazable del saldo inicial bajo | E6 no agrega débito libre; sí permite restablecer deuda al contra-asentar un crédito de corrección |
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

- **Ocho tablas nuevas en `cuenta_corriente`** (migración `0023`): `cuenta` (de una unidad o de una
  persona), `emision`, `evento_de_emision`, `obligacion`, `movimiento` e `imputacion`, las seis de sólo
  agregar, del rol de arranque, con RLS forzada, claves compuestas con la administración y claves
  naturales para la idempotencia; y `candado_de_cuenta`, que **no** es de sólo agregar y existe sólo
  para serializar las escrituras de una cuenta (E2: la app no puede `SELECT ... FOR UPDATE` sobre una
  tabla sin permiso de `UPDATE`, EVIDENCIA en design D2). Se suma `tipo_de_movimiento`, vocabulario global ampliable por INSERT con PK `(tipo,sentido)` (E14).
- **Una emisión por período salvo anulada**, sostenida por la base con un número de intento único por
  edificio y período (E3), sin bloquear el edificio.
- **Orden de imputación** (R04, R13) por período y por componente, con el fondo de reserva provisorio
  (E5) y los destinos fijos de D-086; el excedente libre queda como crédito a favor (R05); con destino fijo se rechaza lo que no puede absorber (E16).
- **Estado de la cuenta calculado desde el libro**: residual por obligación y componente, crédito a
  favor y saldo anterior (R06), **sin ninguna columna "saldo" ni "pagada"**, excluyendo lo que generó
  una emisión anulada y los movimientos corregidos (E7).
- **Corrección de un error** (R08, HU-A9): contra-asiento de un movimiento, o crédito de corrección por
  un importe imputado con R04 (E6); con motivo obligatorio, responsable e idempotencia por
  `operacion_id`.
- **Permiso nuevo `corregir_movimiento`** para super admin y administrador principal, en la matriz y en
  el vocabulario de la auditoría (migración `0024`, E8).
- **Ruta `POST /api/complejos/{complejo_id}/correcciones`** con 401, 403, 404, 409, 422, 500 y 503 declarados en
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
  declarados una vez). Dos migraciones nuevas (`0023`, `0024`). `roles.py:despues()` **cambia su lógica** para
  dar `GRANT REFERENCES` al migrador sobre las seis tablas del libro y `candado_de_cuenta` (E15),
  además de reforzar la revocación de DELETE a la app sobre el candado.
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
4. La corrección como contra-asiento total o crédito con R04, permitiendo deshacer un crédito de corrección una sola vez y sin débito libre
   (E6).
5. Las imputaciones en exceso vuelven de la imputación más reciente a la más antigua, por secuencia monótona (E7).
6. Los formatos de error de hoy, declarados una vez, en vez del esquema nuevo `{tipo, campo}` del explore
   4.8 (E9).
7. Columnas que el 4c y el 8 necesitan, ya en `0023`; lo demás en tablas nuevas con REFERENCES; cambios estructurales necesitan préstamo D-115.3 (E10).
8. El dueño de `administracion` (`acceso`) y las dos excepciones nuevas del escaneo, `lectura.py` y
   `ejemplo.py` (E11). El explore contaba dos rojos; un `rg` de hoy encuentra también `ejemplo.py` (design
   D11).
9. Sólo el estado actual de la cuenta, y la emisión imputa el crédito a favor pendiente (E12).
10. Las funciones del libro no auditan emitir ni anular: lo hace el 7 con sus acciones; sólo la
    corrección registra en `auditoria` (E8).
11. `imputacion` lleva `corrida_id` como trazabilidad y secuencia `orden`; no un único redundante de
    corrida (DB-6). El vocabulario anticipa reversión, reimputación en ambos sentidos y traslado (E14).
12. `REFERENCES` permite tablas futuras con FK, sin propiedad del libro (E15).
13. Destino fijo sin sobrante libre, y bonificación de emisión anulada retenida hasta su reversión (E16).

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 26/10/2026): `01` a `16` y `README.md`.

| documento | operación | qué |
|---|---|---|
| `09_decisiones_y_supuestos.md` | **APPEND** (ya, en este propose) | D-120: P-8 (sin puerto de repositorio para el libro; acota D-040) y P-6 (corrección sólo API en el 4b). D-040 marcada en su título "corregida en parte por D-120" |
| `09_decisiones_y_supuestos.md` | **APPEND** (al archivar) | Las elecciones E1 a E16 firmadas: modelo del libro, candado, intento, idempotencia, orden provisorio del fondo, corrección, exclusiones, permiso, contrato de error, columnas anticipadas, escaneo, lecturas, deuda del 4a; el cierre del 4b con su firma y resultado |
| `04_modelo_de_datos.md` | **REWRITE** | Secciones `Dominios` (obligaciones pertenecen al libro); `ERD / Existente hoy` y `Planificado, por cambio` (quitar vínculos directos unidad→movimiento y liquidación→obligación y reemplazar por cuenta/emisión); `Entidades / Planificado, dominio liquidacion / liquidacion` (mismo id que emision del libro; distribuida sigue del 7); mover `obligacion` a `cuenta_corriente` y reemplazar `Planificado, dominio cuenta_corriente / movimiento` por las ocho tablas reales, incluidos `tipo_de_movimiento` global y `candado_de_cuenta` por tenant; describir todas FK/únicos, secuencia orden y CHECK de D1; `Dueño de las tablas de sólo agregar` (las seis, GRANT REFERENCES y sin ALTER/CREATE INDEX/DROP INDEX del migrador); `accion_de_auditoria` suma corregir_movimiento. Eliminar en esas secciones la promesa de modelo "a decidir" y libro planificado, sin declarar construido lo que siga pendiente del 4c/4d/7/8 |
| `05_reglas_de_negocio.md` | **REWRITE** | R04 y R15: dónde va el fondo de reserva (provisorio hasta A-4); R05: exceso por secuencia y destino fijo sin sobrante libre (E7/E16, a validar P42); R08: contra-asiento del crédito de corrección (E6, a validar P42); R14: créditos particulares por la misma ruta; "Dónde vive" en R04, R05, R06 y R08. Por respuestas a preguntas abiertas y hallazgos del código, como permite D-089 |
| `03_actores_y_roles.md` | **REWRITE** | Fila "Corregir un movimiento" en la matriz (SA y AP) |
| `08_arquitectura_propuesta.md` | **REWRITE** | Sin puerto de repositorio para la propia base (D-120); regla del escaneo de tablas; `cuenta_corriente` construido; candado por cuenta |
| `10_preguntas_abiertas.md` | **REWRITE** | P55 y P56 respondidas (D-120); P52 cuenta personal por edificio; P53/P54 único de interés y prohibición de reinscribir mismo corte; P60/A-4 con E5/E6/E7/E16 a validar P42 |
| `11_glosario.md` | **REWRITE** | "cuenta" (de unidad o de persona), "emisión" frente a "liquidación", "obligación", "componente", "imputación", "crédito a favor", "contra-asiento", "intento de emisión" |
| `12_fichas_de_changes.md` | **REWRITE** | Ficha 4b con lo construido y su deuda; "4a · deuda del cierre" con lo que el 4b cerró o reasignó; ficha 4c con `ajuste de saldo inicial bajo R09` con motivo y origen; ficha 7 con `cargo cobrado de menos` complementario con vínculo al origen, snapshot de saldo_anterior guardado al emitir y autoridad anulada del libro/auditoría del llamador; fichas 8 y 4d con vocabulario y enlace entre cuentas, y 8 con reversión de bonificación retenida (R37); columnas anticipadas, `registrar_credito`, `anular_emision`, y condición de préstamo si necesitan cambiar restricciones |
| `CHANGES.md`, `CLAUDE.md`, `AGENTS.md` | **REWRITE** | Estado del 4b |
| `15_lecciones.md` | **APPEND** | Sólo lecciones propuestas por el auditor del ciclo, fechadas y con costo y evidencia; candidatas a someterle: FOR UPDATE necesita UPDATE; ON CONFLICT debe nombrar árbitro parcial; un GRANT REFERENCES no da ALTER; los tests de exceso deben distinguir a qué crédito vuelve, no sólo el total. No agregar como lección validada una deducción de esta corrección documental |
| `01`, `02`, `06`, `07`, `13`, `14`, `16`, `README.md` | none | El 4b no cambia visión, stack, historias (HU-A9 ya existe), flujos, motor de reglas, forma de trabajo ni fases posteriores |

## Aprobación

Gobernanza CRITICAL (D-094, D-111). La completa, a mano, Juani, Alberto o Emiliano. Ningún agente la
escribe. Cada elección tiene su alternativa descartada y el costo de revertir en `design.md`.

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · Modelo del libro | Seis tablas de sólo agregar, candado por cuenta y vocabulario global (ocho tablas), con las FK, únicos y NOT NULL exhaustivos de D1; fondo separado. Descartado: FK incompletas o MATCH FULL para referencias opcionales con tenant obligatorio. Revertir: recrear vacío o préstamo y migración hacia adelante con datos. | |
| E2 · Candado por cuenta | Candado separado, nace con cuenta; crear cuentas en una sentencia ordenada por unidad_id y candados por cuenta_id, bloquear una sola vez por transacción; exige READ COMMITTED (AislamientoNoAdmitido), comprueba filas (CandadoIncompleto), app sin DELETE. Descartado: FOR UPDATE sobre cuenta sin UPDATE, órdenes cruzados y REPEATABLE READ. Revertir: función/permisos y tabla sin plata (D2). | |
| E3 · Una emisión por período | Intento único por administración/edificio/período, leído y calculado antes de INSERT; anterior activo se rechaza. Descartado: estado mutable o bloqueo de complejo. Revertir: préstamo para cambiar columna/único tras roles (D4). | |
| E4 · Idempotencia | Árbitro y predicado explícitos por escritura (D5); replay primero por operacion_id, comparación de cuenta/tipo/destino/importe/motivo normalizado/complejo y demás datos del pedido, sin request_id/registrado_por; todo otro único se traduce. Anular dos veces se rechaza (R17). Descartado: ON CONFLICT sin árbitro y validar antes del replay. Revertir: lógica y préstamo para cambiar únicos con datos. | |
| E5 · Orden de imputación y fondo de reserva | Período más antiguo primero; dentro del período: interés, ordinaria, **fondo de reserva**, extraordinaria; destinos fijos de D-086; **provisorio hasta A-4 (P60)** (D6) | |
| E6 · Corrección | Contra-asiento total o crédito de corrección con R04; un crédito de corrección equivocado admite contra-asiento una sola vez, incluso si contra-asentaba un interés (D7/D8). No débito libre ni contra-asiento de débito de corrección. Cargo cobrado de menos queda nombrado para el 7; saldo inicial bajo R09 para el 4c. Descartado: corrección irreversible y editar filas; revertir: funciones/ruta, conservar hechos ya registrados. A validar (P42, A-4). | |
| E7 · Exclusiones calculadas | Exclusiones calculadas; pares de corrección desde el extremo más reciente para poder restaurar el original. El exceso vuelve de la imputación más reciente a la más antigua, con secuencia monótona orden en imputacion (D8), no fecha de pago ni now/UUID. Descartado: crédito más reciente o empate aleatorio. Revertir: función de cálculo; cambiar estructura exige préstamo. A validar (P42, A-4). | |
| E8 · Permiso y auditoría | SA/AP pueden corregir; corrección auditada en su transacción (0024), replay sin auditoría nueva; emitir/anular audita el llamador 7 y anulada del libro es autoridad. Descartado: doble auditoría o dar permiso a AE. Revertir: matriz; 0024 baja sólo sin referencias de auditoria (D9). | |
| E9 · Contrato de error | Formas actuales 401/403/404/409/422 más 500 del middleware y 503 temporal declaradas; tabla SQLSTATE de D10 y SAVEPOINT begin_nested. 40P01/40001 -> 503 sin retry interno. Orden 401/422/404 edificio/403/404 recurso/409-422. UUID strict=False e importe positivo al borde. Descartado: nuevo esquema {tipo,campo} o retry de una parte de la transacción. Revertir: modelos/handler/tests (D10). | |
| E10 · Columnas anticipadas | corte, enlazado_a, emision_id y operacion_id anticipados en 0023; vocabulario cubre nuevos pares tipo/sentido por INSERT y E15 permite FK desde tablas futuras. No promete nunca ALTER: después de roles el migrador no puede ALTER, CREATE INDEX ni DROP INDEX sobre las seis tablas. Cambiar columnas/CHECK/únicos requiere préstamo D-115.3, incluido único de interés obligación/corte. Descartado: suponer que crear tabla concede REFERENCES o que quitar un único es trivial; revertir: préstamo y migración con datos (D1/D5). | |
| E11 · Escaneo de tablas en SQL | SQL sólo de tablas propias; administracion es de acceso, excepciones nominadas escritura/lectura/ejemplo (D11). Escaneo insensible a mayúsculas alcanza API/worker para tablas del libro/candado, excluye FOR UPDATE OF y funciones FROM. Descartado: raíces de composición sin vigilancia; revertir: test y excepciones firmadas. | |
| E12 · Lecturas y crédito pendiente | Estado actual en una sentencia SQL con snapshot consistente READ COMMITTED; edificio vía cuenta (JOIN/ANY) y EXPLAIN sin Seq Scan de tablas crecientes. saldo_anterior es residual no negativo sin emisión, crédito separado; 7 guarda foto después de imputar pendientes al emitir. Deuda pasada al 4c/10b. Descartado: varias lecturas sin snapshot o saldo neto implícito; revertir: consultas/API del 7 (D12). | |
| E13 · Deuda del 4a y rollback | Cerrar deuda 4a nombrada en D13, probar mutantes también de tests existentes; ensayo completo y pg_dump schema-only antes/después con diff vacío; sin NO FORCE el mutante debe fallar. Rollback sólo vacío/sin corrección auditada. Descartado: validar sólo texto/conteos; revertir: scripts/tests, los datos impiden downgrade. | |
| E14 · Vocabulario ampliable | Vocabulario tipo_de_movimiento(tipo,sentido), PK y FK compuesta, ampliable por INSERT como accion_de_auditoria. Sembrar actuales más reversion_de_pago débito, reimputacion y traslado en ambos sentidos; enlazado_a FK administración/id entre cuentas. CHECK acotados por tipo para destinos fijos conocidos, no lista cerrada de débitos. Traslado omitido del explore se restituye. Descartado: CHECK IN cerrado o metadatos duplicados en movimiento; revertir: préstamo para cambiar FK/CHECK y migración hacia adelante (D1). | |
| E15 · REFERENCES al migrador | despues() de roles.py otorga GRANT REFERENCES al migrador sobre seis tablas del libro y candado_de_cuenta; test crea como migrador una tabla con FK a movimiento después de roles. Descartado: UUID sin FK o préstamo sólo para crear referencia. Revertir: REVOKE REFERENCES, considerando las FK ya creadas (D1). | |
| E16 · Destino fijo sin sobrante libre | Destino fijo que no absorbe todo rechaza el pedido con 422 campo destino, sin registro parcial. Bonificación ya imputada cuya emisión se anula queda atada al destino y pendientes la saltea hasta reversión del 8. Descartado: condonación que paga capital futuro o crédito libre; revertir: lógica y conservar historia, revisar créditos existentes antes de cambiar. A validar (P42, A-4; D6/D8). | |

| Firmante (Juani, Alberto o Emiliano) | Fecha | Alcance aprobado |
|---|---|---|
| | | |
