## Estado del orquestador

- Change: 4c `intereses-saldo-inicial-y-moroso` (C-07c), CRITICAL. Base: `main` en `533a440`.
- Rol activo: ninguno. Intento 4 de Codex VUELVE AL PLANNER (`informes/propose-4-plan-reviewer.md`): PR-14 cerrado, PR-13 parcial por PR-15 (CORREGIR: la exclusión de días con base cero debe valer sólo para proporcional). Decisión de Juani (30/10/2026, "1"): quinto intento acotado a PR-15. Planner intento 5 entregado (`informes/propose-5-planner.md`). Codex intento 5: PLAN LISTO PARA FIRMA (`informes/propose-5-plan-reviewer.md`). Rol activo: ninguno; esperando la firma de Juani en `proposal.md` `## Aprobación` (puntos E).
- Ejecutores: planner = role-planner nativo; plan-reviewer = Codex por pedido de Juani (el proyecto no tiene tabla `## Role executors`; no es sustitución silenciosa).
- Historia del gate de plan: intento 1 VUELVE (PR-01..PR-09); intento 2 VUELVE (PR-10..PR-12); intento 3 VUELVE sin bloqueantes (PR-13, PR-14). Informes originales en `informes/` e índice en `informes/LEEME.md`.
- Decisión de Juani (30/10/2026, "siis perfecto"): "mes entero" por meses calendario; cada corte (fin de mes, D-113) cobra los meses enteros desde lo ya cubierto. Resuelve PR-10.
- Decisión de Juani (30/10/2026, "dale 1"): tras agotar tres intentos, opción 1: cuarto intento acotado a PR-13 y PR-14.
- Criterio del orquestador para PR-12: cobertura por intervalos registrados, no por máximo (queda como E17 para firma).
- Bloqueos: construcción frenada hasta la firma de Juani en `proposal.md` `## Aprobación`; construye un firmante de D-111 (Juani, Alberto o Emiliano).
- Siguiente: si Codex da PLAN LISTO PARA FIRMA, presentar a Juani los puntos E (grupo (a) de a uno, grupo (b) en bloque).
- Alcance de pruebas: no aplica en propose.

<!-- El planner escribe las tareas debajo de esta sección, sin borrarla. -->

# Tasks

## Antes de construir (no son tareas del constructor)

- Firma CRITICAL en `proposal.md` `## Aprobación`, con fecha y alcance, de Juani, Alberto o Emiliano
  (D-094, D-111), incluidas E1 a E19 de `design.md` (E6 ratifica D-143; E3.2 y E13 ratifican la decisión
  de Juani del 30/10/2026 sobre "mes entero"). Si quien firma elige
  otra opción en alguna, el plan vuelve al planner antes de construir; la columna "Si se elige otra" de
  `design.md` dice qué tareas cambian.
- Quién construye: Codex o un fork del orquestador con la conversación de quien firmó, nunca un
  constructor genérico (L-048).
- Constructor y rompedor leen `knowledge-base/15_lecciones.md` (L-001 a L-067) y dejan anotada la ruta.
- Reglas comunes a todas las tareas: RED antes del código, leído en el traceback hasta la aserción del
  test (L-049) y guardado con comando, hora y salida debajo de la tarea **antes** del commit de
  producción (L-061); un test que nace verde porque el comportamiento ya existe se prueba con su mutante,
  con copia previa y revertido (L-013, L-019); cada aserción de plata o de seguridad lleva el mutante
  nombrado en su tarea (nivel CRITICAL), y cada mutante dice **qué defensa apaga** y **en qué aserción**
  espera el rojo (L-034, L-036): si el rojo sale de otra aserción, de un error de setup o no sale, se
  informa antes de seguir. RED, GREEN y refactor corren sólo los tests tocados; la suite completa corre
  una vez en la 8.1. Montos siempre `Dinero`/`Decimal` desde texto, nunca `float`.
- Cantidad: 24 tareas, por encima de las ~20 de `openspec/config.yaml`. Justificación: tres son deuda
  obligatoria por D-130/D-138, una extiende RF-02 a las cuentas que sólo reciben interés (PR-02) y otras
  dos son regresión de consumidores; partir el 4c otra vez deja al 5 o al 7 esperando un sub-change más
  del camino crítico. El revisor del plan del intento 1 no recomendó partirlo.

## 1. Deuda heredada (antes de confiar en `registrar_emision` con interés)

- [x] 1.1 **RB-6, `redondear_al_centavo` con valores enormes.** Archivos: `backend/tests/unitarios/test_reparto.py`
  (test nuevo), `backend/src/proptech_core/compartido/reparto.py:13-18`. Escenario: reparto-de-montos
  "Valor enorme rechazado como monto inválido". RED: `pytest tests/unitarios/test_reparto.py -k enorme`
  muestra `decimal.InvalidOperation` saliendo de `redondear_al_centavo` con `1e30`, `-1e30` y `1e40`.
  GREEN: traducir `InvalidOperation` del `quantize` a `MontoInvalido`. Mutante: quitar la traducción
  vuelve a dar rojo. Consumidores: el cálculo de interés (4.1) y el reparto existente
  (`test_reparto.py`, `test_reparto_propiedades.py` siguen verdes).
  - RED (15:42, `cd backend && uv run pytest tests/unitarios/test_reparto.py -k enorme -q`): `3 failed,
    41 deselected`; los tres casos (`1E+30`, `-1E+30`, `1E+40`) terminan en `reparto.py:18`
    `valor.quantize(...)` con `decimal.InvalidOperation` dentro del `pytest.raises(MontoInvalido)`: el
    defecto es el esperado, no un error de import ni de setup.
  - GREEN (15:42): traducción `InvalidOperation` a `MontoInvalido` en `reparto.py`; `pytest
    tests/unitarios/test_reparto.py tests/unitarios/test_reparto_propiedades.py -q`: `48 passed`.
  - Mutante (15:42, copia previa en el scratchpad, revertido; defensa apagada: la traducción
    `InvalidOperation` a `MontoInvalido`): `pytest ... -k enorme -q` da `3 failed, 41 deselected`, con
    `decimal.InvalidOperation` en `reparto.py:18` dentro de `pytest.raises(MontoInvalido)`, los tres casos.
- [x] 1.2 **RF-01, una sola lectura final de todas las cuentas.** Archivo:
  `backend/tests/integracion/test_cc_anulacion_candado.py` (test nuevo, nueva y replay). Escenarios:
  libro-de-movimientos "Una sola lectura al publicar una emisión nueva" y "...al repetir una emisión".
  Observación: escucha `before_cursor_execute` de SQLAlchemy que registra cada ejecución de la sentencia
  de la foto, reconocida por su texto **compilado** (el `:ids` se expande en la ejecución; no comparar
  contra la plantilla sin confirmar su forma), con sus parámetros reales, durante `registrar_emision`;
  afirma que la última pide exactamente las cuentas de la emisión (L-016). El comportamiento ya existe,
  así que nace verde: la prueba es el mutante "una `foto` por cuenta" en `emisiones.py:224` (emisión
  nueva) y en `emisiones.py:117` (replay; la `:116` es el bloqueo), cada uno rojo por la aserción de
  cuentas pedidas (no por un error), con copia previa y revertido (L-013, L-034). Los dos tests RF-01/RF-04
  existentes quedan; su docstring dice que no matan este mutante (D-138). La 5.4 extiende este escucha a
  las cuentas que sólo reciben interés.
  - Nace verde (15:42, `cd backend && uv run pytest tests/integracion/test_cc_anulacion_candado.py -q -k
    ultima_foto`): `2 passed, 3 deselected`. Test: `_FotosObservadas` (escucha `before_cursor_execute`,
    reconoce `_FOTO` por `WITH t AS` + `cuentas AS` + `ANY(`, lee los `ids` reales) y los dos tests
    `test_rf01_la_ultima_foto_de_la_emision_nueva_...` y `..._del_replay_...`.
  - Mutante nueva (15:43, copia previa en el scratchpad, revertido; defensa apagada: una sola foto de todas
    las cuentas; `actuales = {c: foto(sesion, c) for c in sorted(cuentas.values())}` en
    `emisiones.py:224`): `1 failed, 1 passed`; rojo en `test_rf01_la_ultima_foto_de_la_emision_nueva_...`
    por `assert {UUID(...)} == {UUID(...)}` (la última foto pidió 1 de 2 cuentas; `Extra items in the
    right set`), el del replay sigue verde.
  - Mutante replay (15:43, mismo método, en `emisiones.py:117`): `1 failed, 1 passed`; rojo en
    `test_rf01_la_ultima_foto_del_replay_...` por el mismo `assert {..} == {..}`, el de la emisión nueva
    sigue verde.
- [x] 1.3 **RF-02 en forma contra-asiento.** Archivo: `backend/tests/integracion/test_cc_anulacion_candado.py:184`
  (parametrizar `credito` y `contra_asiento`; la segunda contra-asienta un crédito de corrección de una
  obligación de la emisión con `contra(...)` de `test_cc_correcciones.py:114`). El crédito original se
  registra y confirma **antes** de instalar la pausa sobre `_anulada`, para que la carrera observe el
  contra-asiento y no su preparación. Escenarios: libro-de-movimientos "Anulación durante un crédito de
  corrección" y "Anulación durante un contra-asiento". Nace verde; mutante: `anular_emision` sin
  `bloquear_cuentas` (`emisiones.py:265`) pone rojas las **dos** formas por `anuladas_al_escribir == 0`.
  Si la forma contra-asiento no se pone roja, el test no vigila (L-035) y se informa antes de seguir.
  - Nace verde (15:44, `uv run pytest tests/integracion/test_cc_anulacion_candado.py -q`): `6 passed`
    (los dos `[credito]` y `[contra_asiento]` del RF-02 incluidos).
  - Primer intento de mutante (15:43, `anular_emision` sin `bloquear_cuentas`, `emisiones.py:265`, con la
    pausa tras la primera llamada a `_anulada` en las dos formas): `[credito]` rojo por `assert 1 == 0`
    pero `[contra_asiento]` rojo por `Conflicto` en `correcciones.py:189`, no por la aserción. Causa: el
    blanco del contra-asiento (un crédito de corrección) no tiene `emision_id`, así que su primera
    llamada a `_anulada` devuelve `False` sin consultar y el chequeo real es la segunda
    (`emision_de_la_obligacion`); con la pausa tras la primera, la anulación ya estaba confirmada para
    la segunda. Ajuste de test: `_tras_la_primera_llamada(..., llamada=2)` en la forma contra-asiento
    (pausa tras el último chequeo, que es donde se abre la carrera).
  - Mutante (15:44, copia previa, revertido; defensa apagada: `bloquear_cuentas` en `anular_emision`):
    `pytest ... -k rf02 -q` da `2 failed, 4 deselected`; `[credito]` y `[contra_asiento]` rojos los dos
    por `AssertionError: la anulación se confirmó debajo de la corrección` / `assert 1 == 0`
    (`anuladas_al_escribir == 0`).
  - Arreglo previo de la tanda 3 (15:59, C17 de H-004): el test parametrizado cambiaba el id de
    `test_rf02_la_anulacion_no_se_confirma_bajo_una_correccion_en_curso` (pasaba a `[credito]`). Queda con
    su nombre original, sin parametrizar (forma crédito), y la forma contra-asiento es
    `..._en_curso_contra_asiento`; los dos comparten el helper
    `_rf02_la_anulacion_no_se_confirma_bajo_una_correccion`. `uv run pytest --collect-only -q
    tests/integracion -k "test_cc_ or test_libro"` lista el id original. Mutante repetido (15:59, copia previa
    en el scratchpad, revertido; defensa apagada: `bloquear_cuentas` en `anular_emision`,
    `emisiones.py:265`): `pytest tests/integracion/test_cc_anulacion_candado.py -q -k rf02 --tb=line` da
    `2 failed, 4 deselected`; los dos rojos por `AssertionError: la anulación se confirmó debajo de la
    corrección` / `assert 1 == 0` (`anuladas_al_escribir == 0`).

## 2. Esquema, protección y semilla

- [x] 2.1 **Migración `0034` y protección de las tablas nuevas.** Archivos:
  `backend/migraciones/versions/0034_intereses_y_saldo_inicial.py` (nuevo, design D4, D5, D10),
  `backend/src/proptech_core/compartido/tablas_protegidas.py` (tres entradas),
  `backend/tests/unitarios/test_fronteras_de_modulos.py` (`_DUENO_DE_TABLA`: las tres a
  `cuenta_corriente`), tests nuevos en `backend/tests/integracion/test_intereses_esquema.py`, parametrizados
  por tabla. Escenarios: intereses-por-mora "El detalle no se edita", "Otra administración no ve el
  detalle", "Un tramo no se cuelga de otra cuenta"; saldo-inicial "El origen no se edita", "Otra
  administración no ve la carga". RED: escribir primero la parte de la migración que crea las tablas sin
  protección y ver el rojo de cada aserción de protección; después proteger. Matriz de mutantes, **uno
  por defensa y por tabla** (tres corridas cada uno, uno a la vez, con copia previa y revertido):

  | Defensa apagada (las demás quedan) | Rojo esperado en | Por qué no lo tapa otra |
  |---|---|---|
  | Sin `FORCE` (queda `ENABLE` + política) | `test_catalogo_rls.py::test_el_esquema_real_no_tiene_ningun_problema` ("RLS no está activada y forzada" nombrando la tabla) y el chequeo de arranque de `roles despues` (`_verificar_tabla_protegida`) | El aislamiento visto por `proptech_app` **no** se pone rojo: la app no es dueña y `ENABLE` + política la filtran. No se usa ese test para este mutante |
  | Sin `ENABLE` ni política (sin `aislar_por_administracion`) | Test de aislamiento como `proptech_app` (precondición afirmada: `rolsuper` y `rolbypassrls` falsos): con filas de A y B, B ve filas de A | Ninguna otra defensa filtra lectura para la app |
  | Fuera de `TABLAS_DE_SOLO_AGREGAR` (sin `REVOKE`) | Test `42501` de `UPDATE`/`DELETE` como app: da `P0001` del trigger en vez de `42501` | El trigger rechaza, pero con otro SQLSTATE: la aserción mira el SQLSTATE |
  | Sin trigger por fila | Test `P0001` de `UPDATE` como arranque | El arranque tiene el privilegio; sólo el trigger lo frena |
  | Sin trigger por sentencia | Test de `TRUNCATE` y `DELETE WHERE false` como arranque, y el chequeo de arranque | El trigger por fila no se dispara sin filas |
  | FK de `tramo_de_interes` a `movimiento` sin `cuenta_id` (sólo administración e id) | "Un tramo no se cuelga de otra cuenta": el insert entra | Ningún CHECK mira la cuenta del movimiento |
  | FK de origen a `obligacion` o `movimiento` sin `cuenta_id` | Test de origen con la cuenta de otra unidad: el insert entra | Ídem |
  | FK a `complejo` ausente | `test_catalogo_rls.py` ("complejo_id ... sin FK") | La FK a `movimiento` no la reemplaza en el catálogo |
  | CHECK de `tramo_de_interes` (`dias = hasta - desde + 1`; en `mes_entero`, un solo mes calendario terminado en su último día), de la carga (importador/manual, `firma_del_pedido` con forma `v1:` + 64 hexadecimales) y de origen (una sola referencia) | El test del CHECK correspondiente: el insert inválido entra. Para `mes_entero`, con `dias` coherente y los demás campos válidos, un mutante por condición: quitar **sólo** la restricción de mismo mes (`desde > hasta - extract(day FROM hasta)::int`) → entra 30/09-31/10 con `dias = 32` (rechazado con el CHECK completo); quitar **sólo** la condición de fin de mes (`extract(day FROM hasta + 1) = 1`) → entra 01/10-30/10 (rechazado con el CHECK completo). El 30/09-29/10 puede quedar como negativo extra, pero no discrimina ninguna de las dos (PR-14) | Sin otra defensa en la base |

  Además, en la misma tarea, actualizar los tests que fijan la cabeza en `0033` o la lista de tablas
  protegidas (L-064): al menos `test_libro_rollback.py` (`:60`, `:86`, `:129`),
  `test_dueno_de_tablas_solo_agregar.py`, `test_arranque_tablas_protegidas.py`, `test_catalogo_rls.py`,
  `test_libro_proteccion.py`, `test_propiedad_protegida.py`; verificar con `rg -n '"0033"|0033'
  backend/tests` vacío salvo historia. Verificación: esos archivos verdes; `alembic upgrade head` y la
  bajada de `0034` con tablas vacías **dentro del ciclo real de devolución de propiedad** (como la bajada
  de `0023`), no con un `alembic downgrade -1` aislado.
  - Decisión del 11/11/2026 (orquestador, brief de la tanda 2): la `0034` crea **sólo** `tramo_de_interes`
    (`0034_tramo_de_interes.py`); las tablas de saldo inicial y origen van en una `0035` de H-005. Rigen sólo
    las filas de la matriz que valen para `tramo_de_interes`; los tests nuevos están en
    `test_intereses_esquema.py` (sólo esa tabla).
  - RED (15:49, `cd backend && uv run pytest tests/integracion/test_intereses_esquema.py -q --tb=line`, con la
    migración **sin protección**: tabla, CHECK, FK e índice, sin triggers, sin RLS, fuera de
    `TABLAS_DE_SOLO_AGREGAR`): `10 failed, 13 passed`. Por aserción: `tramo_de_interes no está en
    TABLAS_DE_SOLO_AGREGAR`; `Failed: DID NOT RAISE` de UPDATE y DELETE como app (la app edita; TRUNCATE
    ya da 42501 sin el REVOKE porque la app no recibe ese privilegio); `otra administración ve filas de
    tramo_de_interes` (`assert (1,) == (0,)`); `assert ('proptech_migrador',) == ('proptech_test',)` (dueño);
    `DID NOT RAISE RaiseException` de TRUNCATE, `DELETE WHERE false` y `UPDATE WHERE false` como arranque.
    Excepción: los dos `test_trigger_por_fila_sin_el_de_sentencia` dan `UndefinedObject` (el `ALTER TABLE ...
    DISABLE TRIGGER` del propio test, porque el trigger de sentencia no existe aún): rojo de setup, no de
    aserción; su rojo por aserción es el del mutante "sin trigger por fila". Los CHECK y las FK nacen verdes
    porque la tabla sin protección ya las lleva: su prueba es el mutante de cada uno.
  - GREEN (15:50, `uv run pytest tests/integracion/test_intereses_esquema.py tests/unitarios/test_fronteras_de_modulos.py
    -q`): `89 passed`. Commit de producción `7896ae0` (`0034_tramo_de_interes.py`, una entrada en
    `tablas_protegidas.py`, `tramo_de_interes` -> `cuenta_corriente` en `_DUENO_DE_TABLA`).
  - L-064: cabeza `0033` -> `0034` en `test_libro_rollback.py` (3 lugares) y `test_conmutar_politicas_reales.py`;
    `tramo_de_interes` en `_SONDA_SIN_FILA` de `test_catalogo_rls.py`; `devolver_libro` devuelve también la
    tabla nueva y un `devolver_tramos` en `test_libro_rollback.py` (lo usan `test_0024_con_correccion_...`
    y `test_rf_0024_down_up_vocabulario`, que ahora bajan la `0034` antes que la `0024` y fallaron con
    `must be owner of table tramo_de_interes` hasta devolverla). `rg -n '"0033"|0033' backend/tests`: vacío.
    Verdes (15:50): `test_libro_rollback`, `test_dueno_de_tablas_solo_agregar`,
    `test_arranque_tablas_protegidas`, `test_catalogo_rls`, `test_libro_proteccion`,
    `test_propiedad_protegida`, `test_conmutar_politicas_reales`, `test_migracion_0024_vocabulario`,
    `test_funciones_restauradas`, `test_sonda_tablas_protegidas` (175 passed + los 4 corregidos).
  - Aceptación de esquema (15:51, copiada del SHA `d2da37e` a un clon fuera del repo en `7896ae0`):
    `test_h004_esquema.py` y `test_h004_migracion.py` `12 passed` (incluye el ciclo de devolución de la 0034).
  - Mutantes (15:52 a 15:55, copia previa en el scratchpad, uno a la vez, revertidos con `git checkout`;
    `uv run pytest tests/integracion/test_intereses_esquema.py -q --tb=line`):
    - sin `ENABLE` ni política (`GRANT` sin `aislar_por_administracion`): **rojo por otra defensa**. El
      chequeo de arranque de `roles despues` (`_verificar_tabla_protegida`, que declara la tabla) frena
      antes: 22 errores de setup `la protección de tramo_de_interes no se pudo confirmar: ROW LEVEL
      SECURITY habilitada y FORCE`. Con ese chequeo apagado a propósito (`if False:` en `roles.py`,
      sólo para ver el test): `1 failed, 22 passed`, rojo en `test_otra_administracion_no_ve_el_detalle`
      por `otra administración ve filas de tramo_de_interes` (`assert (1,) == (0,)`). El mismo caso
      aplica a "sin `FORCE`": rojo por el chequeo de arranque con el mismo mensaje (probado con el test
      del catálogo, `test_el_esquema_real_no_tiene_ningun_problema`: error de setup de su fixture
      `esquema`, `roles despues` sale con 1 y el stderr es `la protección de tramo_de_interes no se
      pudo confirmar: ROW LEVEL SECURITY habilitada y FORCE`), no por la aserción `RLS no está activada
      y forzada` del catálogo, que no se alcanza.
    - fuera de `TABLAS_DE_SOLO_AGREGAR`: `4 failed, 19 passed`; `test_la_app_no_tiene_permiso_de_edicion`
      [UPDATE] y [DELETE] por `AssertionError: tramo_de_interes UPDATE: P0001` (da el trigger, no el
      `42501`), más `test_tramo_esta_declarado_...` y el dueño (`proptech_migrador`).
    - sin trigger por fila: **rojo por el chequeo de arranque** (22 errores de setup `trigger
      trg_tramo_de_interes_sin_update_delete no existe`). Quitando además el nombre de la declaración
      (`tablas_protegidas.py`, para que `roles despues` no lo busque): `3 failed, 20 passed`;
      `test_trigger_por_fila_sin_el_de_sentencia` [UPDATE] y [DELETE] por `DID NOT RAISE
      RaiseException`, más `test_tramo_esta_declarado_...` (declaración distinta, esperado).
    - sin trigger por sentencia: **rojo por el chequeo de arranque, por el efecto** (22 errores de setup
      `... no existe; admite UPDATE; admite DELETE`). Con la declaración sin el nombre y el chequeo
      por el efecto apagado en `roles.py:857` (sólo para verlo): `5 failed`;
      `test_trigger_por_sentencia_sin_filas` [DELETE WHERE false] y [UPDATE WHERE false] por `DID NOT
      RAISE RaiseException`; `[TRUNCATE]` sigue verde (lo frena su propio trigger); los dos de fila dan
      `UndefinedObject` (su `DISABLE TRIGGER`) y está el de declaración.
    - FK a `movimiento` sin `cuenta_id` (y sin edificio ni sentido): `2 failed`; `test_un_tramo_no_se_cuelga_
      de_otra_cuenta` y `..._de_un_movimiento_ajeno_en_otro_edificio` por `DID NOT RAISE ForeignKeyViolation`.
    - FK a `complejo` ausente: `test_catalogo_rls.py::test_el_esquema_real_no_tiene_ningun_problema`
      rojo por `tramo_de_interes: no tiene la FK compuesta (administracion_id, complejo_id) -> complejo
      (administracion_id, id)`; los tests de `test_intereses_esquema.py` quedan verdes (la FK compuesta a
      `movimiento` también fija el edificio), como dice la matriz.
    - CHECK, uno por uno, cada uno rojo sólo en el caso que nombra, por `DID NOT RAISE CheckViolation`:
      `ck_tramo_dias` ([dias_incoherentes]), `ck_tramo_orden` ([hasta_antes_de_desde]), `ck_tramo_base`
      ([base_cero], [base_negativa]), `ck_tramo_forma` ([forma_fuera_del_vocabulario]), `ck_tramo_sentido`
      ([sentido_credito], con un movimiento de crédito para que la FK no lo tape), y los dos de mes
      entero: sin la condición de mismo mes sólo entra 30/09-31/10 con `dias = 32`
      ([mes_entero_de_dos_meses]); sin la de fin de mes sólo entra 01/10-30/10
      ([mes_entero_sin_fin_de_mes]).
  - **H-005, tanda 1 (saldo inicial, `0035`)**: la parte de la 2.1 que H-004 dejó afuera. Tablas
    `carga_de_saldo_inicial` y `origen_de_saldo_inicial` en `0035_saldo_inicial.py`; tests propios en
    `backend/tests/integracion/test_saldo_inicial_esquema.py` (parametrizados por tabla). Decisión del
    constructor: se suma `ck_origen_sentido` (`(movimiento_id IS NULL) = (sentido_del_movimiento IS NULL)`),
    porque con el sentido nulo la FK compuesta a `movimiento` no se evalúa (MATCH SIMPLE) y un origen podría
    colgarse de un movimiento cualquiera; el design D5 no lo lista.
  - RED H-005 (18:24, `cd backend && uv run pytest tests/integracion/test_saldo_inicial_esquema.py -q --tb=line`,
    con la `0035` **sin protección**: tablas, CHECK, únicos, FK e índice, sin triggers, sin RLS, fuera de
    `TABLAS_DE_SOLO_AGREGAR`): `20 failed, 24 passed`. Por aserción: `carga_de_saldo_inicial no está en
    TABLAS_DE_SOLO_AGREGAR` (y la de origen); `AssertionError: tabla UPDATE/DELETE: 23503` y `Failed: DID NOT
    RAISE Error` (la app edita; el DELETE de la carga da 23503 por la FK del origen, no 42501); `otra
    administración ve filas de <tabla>` (`assert (1,) == (0,)`); `DID NOT RAISE RaiseException` de TRUNCATE,
    `DELETE WHERE false` y `UPDATE WHERE false` como arranque; `('proptech_migrador',) == ('proptech_test',)`
    (dueño, las dos). Excepción: los cuatro `test_trigger_por_fila_sin_el_de_sentencia` dan `UndefinedObject`
    (su `DISABLE TRIGGER`): rojo de setup; su rojo por aserción es el del mutante. CHECK, únicos y FK nacen
    verdes porque la tabla sin protección ya los lleva: su prueba es cada mutante.
  - GREEN H-005 (18:25, `uv run pytest tests/integracion/test_saldo_inicial_esquema.py
    tests/unitarios/test_fronteras_de_modulos.py tests/infra/test_ensayo_login.py -q`): `120 passed`; commit de
    producción `8dc11d4` (`0035_saldo_inicial.py`, dos entradas en `tablas_protegidas.py`, las dos tablas ->
    `cuenta_corriente` en `_DUENO_DE_TABLA`, `ensayo-roles.sh`: array de filas y dos bloques `OWNER TO`).
    L-064: cabeza `0034` -> `0035` en `test_libro_rollback.py` (3 lugares) y `test_conmutar_politicas_reales.py`;
    las dos tablas en `_SONDA_SIN_FILA` (`test_catalogo_rls.py`; sus NOT NULL hacen falsa la sonda mínima);
    `devolver_libro` y `devolver_tramos` cubren `POSTERIORES_AL_LIBRO` (las tres). `rg -n '"0034"' backend/tests`:
    sólo el texto de dos comentarios.
  - Barrido local de migraciones (D-154; 18:25 a 18:34, `uv run pytest -q $(rg -l "downgrade|\.migrar\(|
    alembic.*(up|down)grade|pg_restore" tests/integracion)` desde `backend/`, 43 archivos): `1315 passed, 4
    warnings in 543.47s`.
  - Mutantes H-005 (18:34 a 18:39, copia previa en el scratchpad, uno a la vez, revertidos; `uv run pytest
    tests/integracion/test_saldo_inicial_esquema.py -q --tb=line`), en las dos tablas salvo que se diga:
    - sin `ENABLE` ni política, sin `FORCE` y sin trigger por sentencia: **rojo por el chequeo de arranque**
      de `roles despues` (44 errores de setup `la protección de carga_de_saldo_inicial no se pudo confirmar:
      ROW LEVEL SECURITY habilitada y FORCE` / `trigger ..._por_sentencia no existe; admite UPDATE; admite
      DELETE`), igual que en H-004. Con ese chequeo apagado a propósito (`if faltantes and False:` en
      `roles.py:862`, sólo para verlo, revertido): sin `ENABLE` `2 failed` en `test_otra_administracion_no_ve_las_
      filas` por `otra administración ve filas de <tabla>`; sin trigger por sentencia `8 failed` (4 por
      `DID NOT RAISE RaiseException` de `DELETE`/`UPDATE WHERE false`, 4 `UndefinedObject` del `DISABLE TRIGGER`
      del test de fila); sin `FORCE` `44 passed` (la app no es dueña y `ENABLE` + política la filtran: la matriz
      lo anticipa), y con el chequeo encendido lo atrapan el arranque y `test_catalogo_rls.py` (fixture `esquema`).
    - fuera de `TABLAS_DE_SOLO_AGREGAR` (cada tabla): `4 failed, 40 passed`; `UPDATE`/`DELETE` como app por
      `AssertionError: <tabla> UPDATE: P0001` (da el trigger, no el `42501`), más la declaración y el dueño
      (`proptech_migrador`).
    - sin trigger por fila (`WHEN (false)`): `4 failed` por `DID NOT RAISE RaiseException`.
    - FK a `obligacion` sin `cuenta_id` (`(obligacion_id) -> obligacion (id)`) y FK a `movimiento` sin cuenta
      ni sentido: `1 failed` cada uno por `DID NOT RAISE ForeignKeyViolation`. FK a la carga sin `complejo_id`:
      `1 failed`, `'fk_origen_obligacion' == 'fk_origen_carga'` (el insert falla igual, por otra FK).
    - FK a `complejo` ausente (carga y origen): `1 failed` cada uno en `test_la_fila_no_se_cuelga_de_un_edificio_
      de_otra_administracion`; y `test_catalogo_rls.py`: `2 failed` (`no tiene la FK compuesta
      (administracion_id, complejo_id) -> complejo`). FK a `persona` ausente: `1 failed`.
    - CHECK uno por uno, cada uno rojo sólo en sus casos: `ck_carga_origen` (3), `ck_carga_firma` (3),
      `ck_origen_referencia` (2), `ck_origen_fila` (2), `ck_origen_sentido` (1); únicos `uq_carga_complejo` (1) y
      `uq_carga_operacion` (1), por `DID NOT RAISE`.
  - Aceptación H-005 de esquema y migración (SHA `0b4c5cb`, copiada a un directorio temporal de
    `backend/tests/integracion`, borrado): `12 passed, 1 failed`. La falla es
    `test_c19_una_carga_y_su_origen_bien_formados_entran`: inserta **dos** cargas del mismo edificio
    (importador y manual) y choca con `uq_carga_complejo`, que D5 y el brief exigen (único por edificio).
    Contradice el design; el constructor no toca `aceptacion/`: queda al orquestador.
- [x] 2.2 **Semilla con configuración.** **Decisión del orquestador (11/11/2026, H-004)**: la versión de configuración entra por `sembrar(base, con_configuracion=True)`, no por defecto: por defecto rompería C11 de la aceptación congelada (`d2da37e`, mundo sin configuración) y chocaría con `uq_configuracion_vigencia` en los tests que fijan su propia versión. La 5.5 pasa `con_configuracion=True` en los `test_cc_*` que emiten con deuda vencida. Archivo: `backend/tests/integracion/_cuenta_corriente.py::sembrar`
  (una versión de configuración con tasa 0,00, gracia 0, proporcional, umbral 500,00, vigente desde
  01/01/2026, para los tres edificios del mundo). Antes del cambio, correr `pytest tests/integracion -k
  test_cc_` y guardar conteo y fallas previas como línea de base; después, el mismo conteo y ninguna falla
  nueva. No es TDD de comportamiento (es fixture): se registra como validación. Consumidores: todos los
  `test_cc_*` del 4b que usan `sembrar` (`test_cc_auditoria_api.py` usa `ApiEdificio` y se revisa en 5.5).
  - **No se pudo hacer como dice el plan (11/11/2026, sin marcar):** sumar la versión a la `sembrar` por
    defecto contradice la aceptación congelada (`d2da37e`): sus tests siembran con `sembrar(base)` y
    (a) C11 `test_c11_sin_configuracion_vigente` espera `Conflicto("configuracion")` sobre un mundo sin
    versión, y (b) casi todos llaman `configurar(base, mundo)` con `desde=2026-01-01` por defecto, que
    chocaría con `uq_configuracion_vigencia`. Se hizo la variante que no la rompe: `sembrar(base, *,
    con_configuracion=False)` (parámetro opcional, por defecto igual que antes) que suma la versión pedida
    (tasa 0,00, gracia 0, proporcional, umbral 500,00, vigente desde 01/01/2026) a los tres edificios; la
    5.5 la pide en los `test_cc_*` del 4b que llaman `registrar_emision`. Test:
    `test_intereses_esquema.py::test_sembrar_con_configuracion_suma_una_version_por_edificio`.
  - Línea de base (15:46 a 15:48, `cd backend && uv run pytest tests/integracion -k test_cc_ -q`, antes de
    tocar nada): `182 passed, 2240 deselected in 88.44s`, sin fallas. Después (15:56 a 15:57, con la `0034`
    y la semilla opcional): `182 passed, 2265 deselected in 86.95s`, sin fallas nuevas (el valor por
    defecto de `sembrar` no cambió, así que ningún `test_cc_*` ve la configuración). Queda `[ ]`: el
    orquestador decide si esta variante cierra la 2.2 o si hay que revisar la aceptación.

## 3. Estado y foto: lo que el cálculo necesita

- [x] 3.1 **Partes de imputación que cuentan, `corte`, `tramos` e `interes_desde` en el
  dominio.** Archivos: `backend/src/proptech_core/cuenta_corriente/dominio/estado.py` (design D3),
  `backend/tests/unitarios/cuenta_corriente/test_estado.py`. RED: un test que pide la parte topeada de
  una imputación por encima de lo debido (caso E7 del 4b) falla porque el estado no la expone. GREEN:
  exponerla sin cambiar `residual`, `imputado` ni el crédito a favor. Mutante: devolver el importe
  original en vez de la parte topeada → rojo. `test_estado.py` y `test_estado_propiedades.py` siguen
  verdes sin tocar sus expectativas.
  - Decisión de la tanda 3: `ParteDeImputacion(movimiento_id, obligacion_id, componente, importe, orden)`
    y `EstadoDeCuenta.imputaciones_que_cuentan` (ordenadas por `orden`, sin las partes de importe cero).
    `Movimiento.corte`/`tramos` y `Obligacion.interes_desde` con defecto (`None`, `()`, vencimiento más un
    día) para no tocar a los tests existentes. En H-004 `interes_desde` es siempre el vencimiento más un
    día; el origen de saldo inicial es de H-005.
  - RED (16:00, `cd backend && uv run pytest tests/unitarios/cuenta_corriente/test_estado.py -q`): sin
    producción el módulo no importa (`ImportError: cannot import name 'ParteDeImputacion'`), un error de
    colección, no una aserción (L-049). Para leer la aserción se agregó **a mano y sin commitear** el
    andamiaje mínimo (clase `ParteDeImputacion`, `imputaciones_que_cuentan = ()` y los campos con su
    defecto, `interes_desde = date.min`) y se corrió `-k "partes or parte or corte or interes_desde or
    dia_siguiente or no_son_partes"`: `3 failed, 4 passed`. Rojos por aserción:
    `assert () == (ParteDeImputacion(...),)` (partes topeadas y tope por lo debido) y
    `assert datetime.date(1, 1, 1) == datetime.date(2026, 10, 11)` (`interes_desde`). Los otros cuatro
    (sin partes si no cuenta; `corte` y `tramos` por defecto) nacen verdes con el andamiaje: son
    campos de datos. El andamiaje se revirtió desde copia previa del scratchpad antes del commit.
  - GREEN (16:00): `ParteDeImputacion`, `imputaciones_que_cuentan` (paso 3 de `calcular_estado`, sólo
    partes mayores que cero), `Movimiento.corte`/`tramos` y `Obligacion.interes_desde` (defecto en
    `__post_init__`) en `estado.py`; `pytest tests/unitarios/cuenta_corriente/test_estado.py
    tests/unitarios/cuenta_corriente/test_estado_propiedades.py -q`: `28 passed`, sin tocar sus expectativas.
  - Mutante (16:00, copia previa en el scratchpad, revertido; defensa apagada: la parte topeada, se
    devuelve `i.importe` en vez de `parte`): `test_estado.py -q` da `2 failed, 23 passed`, rojos por
    `assert (ParteDeImputacion(...),) == (ParteDeImputacion(...),)` en
    `test_las_partes_de_imputacion_que_cuentan_salen_topeadas_...` (`:396`) y
    `test_una_parte_de_imputacion_no_pasa_de_lo_debido_...` (`:414`).
- [ ] 3.2 **Foto con `corte`, `tramos` e `interes_desde` (E17).** Archivos:
  `backend/src/proptech_core/cuenta_corriente/aplicacion/lecturas.py:37-69` y `_foto`,
  `backend/tests/integracion/test_cc_lecturas.py`. RED: la foto de una cuenta con un interés de corte
  30/11/2026 con dos tramos **no contiguos** (11/09-30/09/2026 y 01/11-30/11/2026), otro interés sin tramos
  (importado) y una obligación de saldo inicial (filas insertadas en el test) no trae el corte, ni los dos
  intervalos del primero en orden y una lista vacía para el segundo, ni el `interes_desde` igual a la
  migración más un día. GREEN: sumar `'corte'` y `'tramos'` (subselect con `json_agg` ordenado) al objeto
  de cada movimiento y el `LEFT JOIN` a `carga_de_saldo_inicial`, en la misma sentencia. Mutantes:
  `interes_desde` siempre igual al vencimiento más un día → rojo; la foto trae sólo el máximo `hasta` (o
  sólo el último tramo) → rojo por la aserción de los dos intervalos. Regresión: los dos ensayos de
  `EXPLAIN` de la foto ("Plan del edificio..." y "Plan de una cuenta...") siguen sin Seq Scan.
  - Ajuste de la tanda 3 por la partición en historias: la tabla `carga_de_saldo_inicial` no existe en
    H-004 (va en la `0035` de H-005). La foto suma `corte` y `tramos` (subselect con `json_agg` ordenado
    por `desde`) en la misma sentencia; **`interes_desde` en H-004 es siempre el vencimiento más un día**
    (el defecto de `Obligacion`, sin tocar el SQL). **Pendiente de H-005**: el `LEFT JOIN` a
    `carga_de_saldo_inicial` por `operacion_id` para el `interes_desde` de una obligación de saldo
    inicial (y su RED y su mutante "`interes_desde` siempre el vencimiento más un día"). La tarea 3.2
    queda `[ ]` por esa parte.
  - RED (16:01, `cd backend && uv run pytest tests/integracion/test_cc_lecturas.py -q --tb=short -k
    trae_corte`): `1 failed, 8 deselected`, por aserción: `assert None == datetime.date(2026, 11, 30)`
    en `f.movimientos[con_tramos].corte` (la foto no trae el corte). Test:
    `test_la_foto_trae_corte_tramos_e_interes_desde` (interés con dos tramos no contiguos insertados en
    orden inverso, otro sin tramos, un pago, y el `interes_desde` de dos obligaciones).
  - GREEN (16:02): `lecturas.py` suma `'corte', m.corte` y `'tramos'` (subselect con `json_agg` ordenado
    por `desde`, por `ix_tramo_movimiento`) al objeto de cada movimiento, en la misma sentencia (se
    conservan `WITH t AS`, `cuentas AS`, `ANY(`, `AS imputaciones` y `AS anuladas`); `_foto` los lee
    (`corte` a `date | None`, `tramos` a tupla de pares). `pytest tests/integracion/test_cc_lecturas.py -q`:
    `9 passed`, con los dos ensayos de `EXPLAIN` ("Plan del edificio..." y "Plan de una cuenta...") sin
    Seq Scan. Nota: `_barridos` sólo mira `obligacion`, `movimiento` e `imputacion` (`GRANDES`); el
    volumen del ensayo no carga `tramo_de_interes`, así que su acceso por `ix_tramo_movimiento` no se
    ensaya con volumen (queda para la 5.x o el 8.1 si se quiere).
  - Mutantes (16:02 y 16:03, copia previa en el scratchpad, revertidos; defensa apagada: la foto trae
    **todos** los intervalos, en orden): (a) sólo el máximo `hasta`: rojo por `assert ((9/11, 9/30), (11/1,
    11/30)) == ...` en `corte`/`tramos` de `con_tramos` (un solo intervalo); (b) sólo el último tramo
    (`ORDER BY desde DESC LIMIT 1`): rojo por la misma aserción de los dos intervalos (`At index 0 diff:
    (11/1, 11/30) != (9/11, 9/30)`, `Right contains one more item`); (c) sin `ORDER BY tr.desde`: rojo
    por la misma aserción (`At index 0 diff`), porque el test inserta los tramos en orden inverso.
  - Comprobaciones de la tanda (16:03): `uv run pytest tests/unitarios/cuenta_corriente/test_estado.py
    tests/unitarios/cuenta_corriente/test_estado_propiedades.py tests/integracion/test_cc_lecturas.py
    tests/integracion/test_cc_anulacion_candado.py -q`: `43 passed`; `ruff check`, `ruff format --check` y
    `mypy` (387 archivos) limpios.
  - H-005 tanda 3, RED (18:53, `cd backend && uv run pytest tests/integracion/test_cc_saldo_inicial.py -q
    --tb=short -k interes_desde`): `1 failed, 28 deselected`, por aserción: `assert {... (c1, 2026-08-01):
    date(2026, 8, 11) ...} == {... date(2026, 10, 16) ...}` en
    `test_la_foto_trae_el_interes_desde_el_dia_siguiente_a_la_migracion` (carga en detalle y en total único
    más una emisión de noviembre; la obligación migrada de agosto trae su vencimiento más un día, no la
    migración más un día; las emitidas y el total único ya coinciden). Los cuatro escenarios de saldo
    inicial del dominio (`test_primer_interes_despues_de_migrar`, `test_mes_entero_despues_de_migrar`,
    `..._con_interes_importado_no_suma_a_la_base`, `test_segundo_mes_despues_de_migrar`) nacen verdes
    (el dominio ya recibe `interes_desde`); se miden con mutantes en 4.2 y 4.3.

## 4. Cálculo del interés (dominio puro, R03)

Archivo de producción: `backend/src/proptech_core/cuenta_corriente/dominio/intereses.py` (nuevo, design
D2). Tests: `backend/tests/unitarios/cuenta_corriente/test_intereses.py` (nuevo). Sin base.

- [x] 4.1 **Proporcional, base, nunca interés sobre interés, tasa cero y redondeo único.** Escenarios:
  "Expensa de septiembre impaga en la emisión de octubre" ($2.000,00), "Nunca interés sobre interés"
  ($3.100,00), "Pago parcial reduce la base" ($1.600,00 en dos tramos), "Tasa cero", "Medio centavo
  hacia arriba" ($0,13 sobre $62,50), "Redondeo único sobre dos tramos" ($0,13 sobre $64,00 y $63,00),
  "Detalle de un pago parcial" (tramos 11/09-20/09 y 21/09-30/09), "Detalle de un pago total" ($1.000,00,
  un solo tramo 11/09-20/09 sobre $100.000 y ningún tramo en 21/09-30/09; PR-13). RED: cada test falla por su aserción
  contra la función todavía vacía (no por import). Mutantes, cada uno rojo en el escenario nombrado:
  redondear cada tramo y sumar → "Redondeo único sobre dos tramos" da $0,12 (el de $62,50 **no** lo
  detecta: es un solo tramo); `ROUND_HALF_EVEN` o truncar → "Medio centavo hacia arriba" da $0,12; la
  base suma el componente `interes` → "Nunca interés sobre interés" da $3.162,00; dividir por 31 o por
  365/12 → "Expensa de septiembre..." cambia de importe; la imputación baja la base desde su propio día en
  vez del siguiente → "Redondeo único sobre dos tramos" y "Pago parcial..." cambian; registrar $0,00 →
  "Tasa cero" registra un débito; estirar el último tramo con base positiva hasta el corte → "Detalle de un
  pago total" da un tramo 11/09-30/09, rojo por fechas.
  - RED (16:06, `cd backend && uv run pytest tests/unitarios/cuenta_corriente/test_intereses.py -q --tb=short`,
    contra `intereses.py` con la firma y `calcular_intereses` que devuelve `()`): `23 failed, 3 passed`. Los 23
    rojos son por aserción: `AssertionError: se esperaba un interés y hay 0` (`assert 0 == 1`, de `unico()`) o,
    en los de "dias no contiguos" y "corte que no es fin de mes", `Failed: DID NOT RAISE`. Nacen verdes tres
    negativos que el stub vacío ya cumple: "Tasa cero", "Pago dentro de la gracia" y "Los días no cobrados no
    pasan el corte"; su prueba es el mutante (registrar $0,00 y `<` en el borde de la gracia, abajo). El escenario
    "Un débito de capital suma a la base" es nuevo de esta tanda (la tarea no lo nombra): cubre la parte "débitos
    de capital que cuentan" de la base.
  - GREEN (16:07, `uv run pytest tests/unitarios/cuenta_corriente/test_intereses.py -q`): `26 passed`; con toda la
    carpeta `tests/unitarios/cuenta_corriente/`: `72 passed`. `ruff check`, `ruff format --check`, `mypy` (389
    archivos) y `tests/unitarios/test_fronteras_de_modulos.py` (66 passed) limpios.
  - Mutantes de 4.1 (16:07 y 16:08; copia previa `intereses.orig.py` en el scratchpad, uno a la vez, revertidos y
    verificados con `diff`; `uv run pytest tests/unitarios/cuenta_corriente/test_intereses.py -q --tb=line`). Todos
    rojos por aserción en el escenario nombrado:
    - redondear cada tramo y sumar: sólo `test_redondeo_unico_sobre_dos_tramos` (`assert Dinero("0.12") == Dinero("0.13")`);
      "Medio centavo" sigue verde (un solo tramo), como dice la tarea.
    - `ROUND_HALF_EVEN`: sólo `test_medio_centavo_hacia_arriba`; truncar (`ROUND_DOWN`): ese y "Redondeo único".
    - la base suma el componente `interes`: `test_nunca_interes_sobre_interes` (da $3.162,00 en la cuenta) y cuatro
      de mes entero y de cambio de forma que parten de un interés previo.
    - dividir por 31 y por 365/12 (`tasa * 12 / 100 / 365`): 13 y 12 rojos, incluido "Expensa de septiembre".
    - la imputación baja la base desde su propio día (`<=`): "Pago parcial reduce la base", "Redondeo único sobre
      dos tramos", "Detalle de un pago total" y "Pago un día después de la gracia".
    - registrar $0,00 (sin el `continue`): `test_tasa_cero` (y "Pago dentro de la gracia").
    - estirar el último tramo hasta el corte: `test_detalle_de_un_pago_total` (fechas) y "Pago un día después de la
      gracia".
    - ignorar los débitos de capital: `test_un_debito_de_capital_suma_a_la_base_desde_el_dia_siguiente`.
- [ ] 4.2 **Gracia e inicio natural.** Escenarios: "Pago dentro de la gracia", "Pago un día después de la
  gracia" ($600,00), "Corte dentro de la gracia" ($3.300,00 en noviembre), "Lo cubierto por un interés
  anterior no se vuelve a cobrar", saldo-inicial "Primer interés después de migrar" (sólo la parte de
  dominio: inicio el día siguiente a la migración). Mutantes: el interés corre desde `vencimiento +
  gracia`; `<` en vez de `<=` en el borde de la gracia; el inicio de una obligación migrada es su
  vencimiento; el inicio ignora lo cubierto por un interés que cuenta.
  - GREEN (16:07): mismas corridas que 4.1.
  - Mutantes de 4.2 (16:07, mismo método), rojos por aserción:
    - el interés corre desde `vencimiento + gracia` (el inicio se corre y las imputaciones dentro de la gracia
      no se tratan como pagadas al vencimiento): "Pago un día después de la gracia", "Corte dentro de la gracia",
      el borde del corte y "Corte dentro de la gracia con mes entero".
    - `<` en vez de `<=` en el borde de la gracia, uno por uno: en la imputación sólo
      `test_pago_dentro_de_la_gracia` (cobra 11/09-15/09); en el corte sólo
      `test_corte_en_el_ultimo_dia_de_la_gracia_no_cobra` (test agregado para este mutante: vence 25/09, gracia 5,
      corte 30/09).
    - el inicio de una obligación migrada es su vencimiento: los dos tests de `interes_desde`.
    - el inicio ignora lo cubierto: "Lo cubierto por un interés anterior..." y seis más que parten de un interés previo.
  - Escenarios de saldo inicial de 4.2 y 4.3 ("Primer interés después de migrar", "Mes entero después de migrar",
    "Segundo mes después de migrar"): **pendientes de H-005**. El dominio ya recibe `interes_desde`; dos tests
    (`..._obligacion_migrada_es_el_que_pasa_el_lector` y `mes_entero_respeta_el_inicio_...`) sólo prueban que lo
    respeta, y los mutantes de "inicio migrado" y "tramo desde el día 1" se ejercitan con ellos y con "Un día de
    atraso con mes entero".
- [ ] 4.3 **Mes entero por meses calendario (E3.2, E13, decisión de Juani del 30/10/2026).** Escenarios:
  "Un día de atraso con mes entero" ($3.000,00, tramo 30/09-30/09), "El mes siguiente con mes entero"
  ($3.000,00, tramo 01/10-31/10), "Corte dentro de la gracia con mes entero" ($6.000,00, tramos 29/09-30/09
  y 01/10-31/10), "Pago a mitad de mes con mes entero" ($3.000,00 y $1.800,00), "Febrero proporcional"
  (19 días, $1.900,00 en 2028), "De proporcional a mes entero" ($2.000,00 y $3.000,00, un solo tramo
  01/10-31/10), "De mes entero a proporcional" ($3.000,00 y $3.100,00), y la parte de dominio de
  saldo-inicial "Mes entero después de migrar" ($2.400,00 y $2.550,00, tramo 16/10-31/10) y "Segundo mes
  después de migrar" ($2.400,00, tramo 01/11-30/11). Cada test afirma importe **y** fechas de los tramos.
  Mutantes, cada uno con su rojo: bloques de 30 días anclados en el primer día a cobrar (el plan del
  intento 2) → "De proporcional a mes entero" da $6.000,00 (bloques 01/10-30/10 y 31/10-29/11) y "De mes
  entero a proporcional" da $200,00; una fracción de mes no cuenta como mes (sólo meses completos) → "Un
  día de atraso con mes entero" y "Mes entero después de migrar" dan $0,00; un mes por cada 30 días completos
  del intervalo (redondeo hacia abajo) en vez de por mes calendario → "Corte dentro de la gracia con mes entero" da $3.000,00; base
  del último día del mes en vez del primero a cobrar → "Pago a mitad de mes" da $1.800,00 en el corte
  30/09; el tramo de mes entero empieza el día 1 del mes aunque el primer día a cobrar sea posterior → rojo por fechas en "Mes entero después de migrar" (16/10) y en "Un día de atraso"
  (30/09); febrero de 28 días en año bisiesto en el proporcional; aplicar a mes entero la exclusión de
  días con base diaria cero del proporcional (el tramo termina en el último día con base positiva) → rojo
  por fechas en "Detalle de un pago total con mes entero" (PR-15: da 11/09-20/09 en vez de 11/09-30/09),
  que va en esta tarea con su importe ($3.000,00) y sus fechas. Además, el error de "días no contiguos
  dentro de un mes" (D2, invariante) con una entrada armada a mano: lanza y no devuelve importe.
  - GREEN (16:07): mismas corridas que 4.1. Esta tarea queda `[ ]` por los escenarios de saldo inicial (H-005).
  - Mutantes de 4.3 (16:07 y 16:08, mismo método), rojos por aserción:
    - bloques de 30 días anclados en el primer día a cobrar: "De proporcional a mes entero" (da $6.000,00), "El
      mes siguiente", "Corte dentro de la gracia", "Pago a mitad de mes" y el del corte que no es fin de mes.
      "De mes entero a proporcional" (la tarea esperaba $200,00) **no** da rojo: el mutante sólo toca el camino de
      mes entero y ese test calcula el corte 31/10 en proporcional, con el interés de septiembre como dato. Su
      aserción sigue vigilando el inicio en `01/10` por los mutantes del inicio y de lo cubierto.
    - una fracción de mes no cuenta: "Un día de atraso con mes entero" ($0,00 / sin interés), "Corte dentro de la
      gracia con mes entero", "Pago a mitad de mes", "Detalle de un pago total con mes entero" y el de `interes_desde`.
    - un mes por cada 30 días completos: los mismos cinco, incluido "Corte dentro de la gracia con mes entero".
    - base del último día en vez del primero: `test_pago_a_mitad_de_mes_con_mes_entero` (`assert Dinero("1800.00")
      == Dinero("3000.00")`, corte 30/09) y "Detalle de un pago total con mes entero".
    - el tramo empieza el día 1: "Un día de atraso" (fechas), "Corte dentro de la gracia", "Pago a mitad de mes",
      "Detalle de un pago total" y el de `interes_desde`.
    - febrero sin el 29 en 2028 (proporcional): sólo `test_febrero_proporcional`.
    - la exclusión de días con base cero aplicada a mes entero: sólo `test_detalle_de_un_pago_total_con_mes_entero`
      (PR-15, fechas).
    - sin la comprobación de contigüidad y de fin de mes: se ejercitan con los tests de error (`DID NOT RAISE
      EntradaInvalida`); el de "corte que no es fin de mes" lo agregué porque el CHECK de la base lo exige.
- [x] 4.4 **Huecos: días de un interés que no cuenta y de un corte sin importe (E1, E17, E19).**
  Escenarios: "Anular y volver a emitir no cobra dos veces", "El corte siguiente recupera el tramo" (51
  días, $5.100,00), "El tramo recuperado usa la tasa del corte siguiente" (51 días al 6%, $10.200,00), "Un
  hueco anterior se recupera aunque haya un interés posterior" ($5.000,00 en dos tramos, 11/09-30/09 y
  01/11-30/11) y "Los días de un corte con tasa cero se cobran después" ($5.100,00 en el corte 31/10).
  Mutantes: tomar como cubierto el corte de un interés aunque no cuente → rojo por días de menos;
  registrar otro interés en un corte ya ocupado → rojo por la aserción de "ninguno nuevo"; calcular los
  días recuperados con la tasa del interés anulado → rojo en el escenario del 6%; **cobertura por el
  máximo de los `hasta`** (el plan del intento 2) → "Un hueco anterior se recupera..." da $3.000,00 y un
  solo tramo 01/11-30/11, rojo por importe y por fechas; los dos intervalos guardados como un solo tramo
  11/09-30/11 → rojo por la aserción de fechas de los tramos (además, octubre quedaría cubierto por dos
  intereses que cuentan, y la propiedad de 4.5 sin solapamiento falla); tratar un corte con tasa 0
  como cubierto → "Los días de un corte con tasa cero..." da $3.100,00.
  - RED (16:12, `cd backend && uv run pytest tests/unitarios/cuenta_corriente/test_intereses.py -q --tb=line`, contra
    `intereses.py` de la t4, sin la regla E1): `3 failed, 30 passed`. Rojos por aserción: "Anular y volver a emitir no
    cobra dos veces" (`AssertionError: ninguno nuevo: el corte ya lo ocupa el interés anulado`: el dominio registra
    otro interés con corte 30/09) y, en cascada por ese segundo interés, "El corte siguiente recupera el tramo"
    (`assert Dinero("3100.00") == Dinero("5100.00")`) y "El tramo recuperado usa la tasa del corte siguiente"
    (`assert Dinero("3100.00") == Dinero("10200.00")`). Nacen verdes porque E17 (unión de intervalos) ya está en la t4:
    "Un hueco anterior se recupera...", "Los días de un corte con tasa cero...", "Un corte con interés que cuenta no
    recibe otro" y "Un corte sin importe por base chica no pierde sus centavos" (agregado); su prueba son los
    mutantes de abajo. Los escenarios encadenan cortes con la clase `Libro` del test (calcula, registra lo que
    devuelve el dominio y contra-asienta), así que un corte que "no registra" de verdad no deja cobertura.
  - GREEN (16:13, regla E1 en `_corte_ocupado` de `intereses.py`: cualquier `Movimiento` `interes` de la obligación con ese
    `corte`, cuente o no; se deriva de los movimientos que ya recibe, sin cambiar la firma):
    `uv run pytest tests/unitarios/cuenta_corriente -q` da `88 passed` (33 de `test_intereses.py`, 9 de propiedades);
    `ruff check`, `ruff format --check` y `mypy` (390 archivos) limpios; `tests/unitarios/test_fronteras_de_modulos.py`,
    66 passed.
  - Mutantes de 4.4 (16:13; copia previa `intereses.t5.orig.py` en el scratchpad, uno a la vez, revertidos y verificados
    con `diff`; `uv run pytest tests/unitarios/cuenta_corriente/test_intereses.py -q --tb=line`):
    - tomar como cubierto el corte de un interés aunque no cuente (se saca `m.id in estado.movimientos_que_cuentan` de
      `_cubiertos`): rojo por días de menos en "El corte siguiente recupera el tramo", "El tramo recuperado usa la tasa..."
      y "Un hueco anterior se recupera...".
    - registrar otro interés en un corte ya ocupado (`_corte_ocupado` devuelve `False`): rojo en "Anular y volver a emitir
      no cobra dos veces" (`ninguno nuevo`), más los dos de recuperación por cascada. Variante "sólo mira los intereses que
      cuentan": rojo igual, en el mismo test.
    - calcular los días recuperados con la tasa del interés anulado (el dominio no la recibe: se la deriva del importe y
      de los días del anulado, 3%): rojo sólo en "El tramo recuperado usa la tasa del corte siguiente" (da $5.100,00 en
      vez de $10.200,00).
    - cobertura por el máximo de los `hasta`: "Un hueco anterior se recupera..." da `$3.000,00` y un solo tramo
      01/11-30/11 (`assert Dinero("3000.00") == Dinero("5000.00")`); también rojo `test_dias_no_contiguos...` de 4.3.
    - los dos intervalos como un solo tramo (se saca la contigüidad de la fusión en `_proporcional`): rojo por fechas en
      "Un hueco anterior..." (`(11/09, 30/11, 50, ...)` contra `(11/09, 30/09, 20, ...)`).
    - tratar un corte con tasa 0 como cubierto (devuelve un interés de $0,00 con sus tramos y la prueba lo registra):
      rojo en "Los días de un corte con tasa cero se cobran después", "Un corte sin importe por base chica..." y
      `test_tasa_cero`.
- [x] 4.5 **Propiedades con `hypothesis`.** Archivo: `backend/tests/unitarios/cuenta_corriente/test_intereses_propiedades.py`.
  Oráculo independiente con `fractions.Fraction` día por día y su propia agrupación por mes calendario,
  que **no** reusa la función de producción (QA-4 del 4a): el importe es el redondeo medio hacia arriba de
  la suma exacta de los tramos; nunca negativo; con tasa 0 o base 0 no hay importe; agregar un pago nunca
  sube el interés; **no solapamiento** (propiedad aparte): ningún día queda cubierto dos veces por
  intereses que cuentan; **cobertura de lo cobrable** (PR-13): después de un corte que registra, la unión
  de lo cubierto por los intereses que cuentan es exactamente el conjunto de días entre el inicio natural
  y ese corte que el oráculo, con la configuración de cada corte, asigna a un tramo con base de tramo
  positiva. La exclusión depende de la forma (PR-15): en **proporcional**, los días con base diaria cero
  quedan sin cubrir y no aparecen en ningún tramo; en **mes entero**, la cobertura es el tramo mensual
  completo (primer día a cobrar del mes hasta el último día a cobrar, que es el fin del mes o el corte),
  cobrado con la base de su primer día a cobrar, aunque después un pago total deje la base diaria en cero.
  El generador cubre cambios de forma, anulaciones, contra-asientos de cualquier interés, no sólo del
  último, y pagos parciales y totales; van además como casos fijos `@example` el proporcional de "Detalle
  de un pago total" ($1.000,00, tramo 11/09-20/09, nada en 21/09-30/09) y el discriminante de mes entero
  de "Detalle de un pago total con mes entero" ($100.000, vence 10/09, gracia 0, 3% mes entero, pago total
  con fecha valor 20/09, corte 30/09 → $3.000,00, tramo 11/09-30/09 con base $100.000); en "mes
  entero", cada tramo es de un solo mes calendario, termina en su último día y hay a lo sumo un tramo por mes y obligación entre los intereses que cuentan; partir un
  tramo proporcional en dos cortes consecutivos suma lo mismo, salvo el redondeo de cada corte. Mutantes
  de control: el redondeo por tramo hace fallar la primera propiedad (además del escenario fijo de 4.1,
  que es el que garantiza el rojo); la cobertura por máximo hace fallar la de cobertura de lo cobrable (además
  del escenario fijo "Un hueco anterior se recupera..." de 4.4, que es el que garantiza el rojo).
  - RED (16:12, `cd backend && uv run pytest tests/unitarios/cuenta_corriente/test_intereses_propiedades.py -q --tb=short`,
    perfil local, 400 ejemplos por propiedad): `2 failed, 7 passed`. Rojos por aserción, ambos con el mismo contraejemplo
    mínimo (E1 sin construir: anular un interés y volver a emitir su corte): "el importe es el redondeo medio hacia
    arriba..." (`assert paso.resultado == ()` con un interés de $0,52 de más) y "lo cubierto es exactamente lo que
    asigna el oráculo" (`assert dias_de_produccion == paso.esperado.dias`). Las otras siete nacen verdes: su prueba son
    los mutantes de control y los de 4.4.
  - GREEN (16:13): con la regla E1 las nueve propiedades pasan (`88 passed` en la carpeta). Cuentan: 400 ejemplos por
    propiedad (`@settings(max_examples=400)`), perfil `local` aleatorio y `ci` derandomizado; dos `@example` fijos
    ("Detalle de un pago total", proporcional, y su discriminante de mes entero) en importe, cobertura y mes entero.
    Propiedades: importe = redondeo medio hacia arriba de la suma exacta de los tramos (y = al del oráculo), nunca
    negativo, tasa 0, base 0 (todo pagado al vencimiento), agregar un pago no sube, no solapamiento, cobertura de lo
    cobrable (PR-13, PR-15: con la base por día en proporcional y la del primer día en mes entero), mes entero (un mes
    por tramo, termina en fin de mes, uno por mes) y partir un tramo (diferencia de a lo sumo un centavo). El oráculo
    lleva su propio modelo de cobertura y de cortes ocupados, y calcula con `Fraction`; el dominio lanzando
    `EntradaInvalida` se compara con el oráculo (mes entero con días no contiguos o que no terminan en fin de mes).
    Los escenarios de saldo inicial del generador quedan para H-005, como pidió el brief.
  - Mutantes de control de 4.5 (copia previa, revertidos con `diff`; 3 corridas en `local` y 1 en `ci` cada uno, todas
    rojas): redondear cada tramo y sumar: rojo en "el importe es el redondeo medio hacia arriba..." (y en "lo cubierto
    es exactamente...", porque un tramo que redondea a $0,00 deja de registrar; en `ci` también "mes entero"); cobertura
    por el máximo de los `hasta`: rojo en "lo cubierto es exactamente lo que asigna el oráculo" y en "el importe...".
    Las corridas de `local` tardaron entre 9 y 54 s por el shrinking; ninguna dejó de fallar.

## 5. Interés en la emisión (aplicación, PostgreSQL real)

Archivos de producción: `backend/src/proptech_core/cuenta_corriente/aplicacion/emisiones.py`
(`registrar_emision`, `_replay`, `anular_emision`, `EmisionRegistrada`; design D0, D1). Tests:
`backend/tests/integracion/test_cc_intereses.py` (nuevo) y `test_cc_anulacion_candado.py`.

- [x] 5.1 **Registro del interés al emitir.** Escenarios: "Expensa de septiembre impaga en la emisión de
  octubre" (débito con corte 30/09, referencia a la emisión, tramos guardados), "Unidad sin obligación en
  la emisión nueva", "Emisión anulada no genera interés sobre sus obligaciones", "Saldo anterior con
  interés" ($102.000,00 y el interés en `EmisionRegistrada`), "Emitir a mitad de mes no adelanta
  interés", "Redondeo único sobre dos tramos" contra la base (el pago de $1,00 con el caso de uso de
  créditos del 4b). RED: cada test falla por su aserción (no por el helper `emitir`, L-049). Mutantes:
  corte en el último día del período emitido (E2); calcular sólo las cuentas de la emisión (E10);
  insertar el interés después de imputar pendientes (el crédito a favor no lo cubre); saldo anterior sin
  el interés; un tramo ligado al movimiento de otra cuenta (lo rechaza la FK de 2.1; acá se afirma que la
  aplicación nunca lo intenta). Consumidor: el 7 (contrato nuevo de `EmisionRegistrada`, anotado en la
  ficha del 7 al cerrar).
  - RED 5.1 (16:23, `cd backend && uv run pytest tests/integracion/test_cc_intereses.py tests/integracion/test_cc_anulacion_candado.py -k cc_ -q`, extracto de `.git/red_t6.txt`): 6 tests de 5.1 rojos por aserción: `se espera un interés
    con corte 2026-09-30, hay 0` (septiembre, anulada, redondeo, la tasa) y `EmisionRegistrada no informa
    intereses`; `unidad sin obligación`, `saldo anterior` y `mitad de mes` con la lista de intereses vacía.
    Ningún error de setup ni del helper `emitir`.
  - GREEN 5.1 (16:30, `cd backend && uv run pytest tests/integracion/test_cc_intereses.py tests/integracion/test_cc_anulacion_candado.py -q -k cc_`): `25 passed`; la aceptación sobre `2f1ce29` pasa C01 a C16 y C19 a C27. Decisiones:
    corte = `periodo - 1 día` (E2); `fecha_valor` del interés = su corte; se bloquean todas las cuentas de
    unidad del edificio (`complejo_id` y `unidad_id` no nulo) con las creadas, en un solo pedido; la
    configuración se lee sólo si alguna obligación que cuenta de esas cuentas vence antes del corte; se pasan
    a `calcular_intereses` todos los movimientos de la cuenta (también anulados o contra-asentados, E1).
    Test nuevo, nacido verde y probado con su mutante: el crédito a favor cubre el interés (R04).
  - Mutantes 5.1 (16:32 a 16:33, copia previa en el scratchpad comprobada con `git diff --quiet` tras revertir; un
    mutante a la vez): M1 corte en el último día del mes del período
    (defensa apagada: E2) rojo en `test_cc_interes_de_septiembre_en_la_emision_de_octubre` por
    `assert (importe, cuenta, emisión) == ...` (el interés de septiembre queda en la emisión de septiembre);
    M2 sólo cuentas de la emisión (E10) rojo por `assert [] == [Dinero("2000.00")]` en `unidad_sin_obligacion`;
    M3 imputar pendientes antes de registrar el interés rojo en `el_credito_a_favor_cubre_el_interes` por
    `assert Dinero("0.00") == Dinero("1000.00")` (el crédito fue a octubre); M4 saldo anterior sin el interés
    rojo por `assert Dinero("100000.00") == Dinero("102000.00")`; M5 un tramo ligado a otra cuenta: rojo por
    `ForeignKeyViolation fk_tramo_movimiento` (no por una aserción: lo rechaza la FK de 2.1, como anota la
    tarea; la aplicación nunca lo intenta).
- [x] 5.2 **Configuración al corte (PR-01).** Escenarios: "Cambio de tasa entre períodos" ($2.000,00 y
  $6.200,00, y el primero no cambia), "Sin configuración vigente" y "Sólo una versión futura"
  (`Conflicto("configuracion")` y `contar_escrituras` vacío), "Edificio de otra administración" (no
  encontrado). Usa `complejos.aplicacion.lectura.configuracion_vigente` (`lectura.py:213-227`): `None` se
  traduce a `Conflicto("configuracion")`; `NoEncontrado` **no** se traduce. Mutantes: leer la versión
  vigente a la fecha del reloj en vez del corte → "Sólo una versión futura" registra interés; seguir sin
  interés cuando devuelve `None` → los dos escenarios de conflicto quedan verdes sin rechazo, rojo. El
  escenario de otra administración nace verde (la FK de `emision` rechaza antes de leer la
  configuración): se deja como regresión, sin mutante propio en esta tarea; el mutante de traducir
  `NoEncontrado` lo mata la 7.2. Además: un test que el `configuracion_id` guardado en cada tramo es el
  de la versión vigente al corte (mutante: guardar el de la última versión → rojo en "Cambio de tasa").
  - RED 5.2 (16:23, mismo comando): `DID NOT RAISE Conflicto` en `sin configuración` y `sólo una versión futura`;
    `cambio de tasa` por `se espera un interés con corte 2026-09-30, hay 0`; `forma que no cierra` por `DID NOT RAISE
    Conflicto` (con `raising=False`: `emisiones` todavía no importa `calcular_intereses`). `otra administración`
    nace verde por la FK, como anota la tarea.
  - GREEN 5.2 (16:30, mismo comando): verde. Mutantes (16:33): M6 leer la versión a la fecha del reloj en vez
    del corte rojo por `DID NOT RAISE Conflicto` en `sólo una versión futura`; M7 seguir sin interés si no hay
    versión rojo por `DID NOT RAISE Conflicto` en `sin configuración vigente` (con `-x` corre el primero; el
    de la versión futura es el mismo camino); M8 guardar el id de la última versión rojo en
    `cambio_de_tasa_entre_periodos` por `assert {('3.00', v)} == {('3.00', v)}` (la versión del tramo de
    septiembre). M9 (decisión de mes entero, abajo): sin traducir el error del dominio rojo por
    `EntradaInvalida` en vez de `Conflicto`.
  - **Decisión (mes entero con días no contiguos).** El dominio lanza `EntradaInvalida` cuando, tras restar lo
    cubierto, los días de un mes no forman un bloque contiguo. La emisión lo traduce a `Conflicto("interes")` y
    se rechaza entera, sin escribir nada (el SAVEPOINT deshace lo ya insertado): saltear la obligación callaría
    un interés (plata perdida sin aviso) y dejaría un libro que el 7 no sabe que está incompleto. Queda a la
    vista del administrador, que puede volver la forma a proporcional o corregir. El caso real es difícil de
    armar con el libro (necesita un hueco dentro de un mes); el test lo fuerza sustituyendo
    `emisiones.calcular_intereses` y comprueba el código y que `conteos` no cambia. Si el 7 prefiere otra
    política, lo cambia ahí; no es un contrato de la aceptación.
- [x] 5.3 **Re-emisión, replay (E15) y concurrencia.** Escenarios: "Anular y volver a emitir no cobra dos
  veces", "El corte siguiente recupera el tramo" y "El tramo recuperado usa la tasa del corte siguiente"
  contra la base; "Un hueco anterior se recupera aunque haya un interés posterior" (E17) contra la base,
  con el contra-asiento hecho por el caso de uso real de correcciones del 4b (`correcciones.py`, que hoy
  admite corregir un interés que no es el último, `:185-194`) y la foto real de la 3.2, y "Los días de un
  corte con tasa cero se cobran después" (E19) con dos versiones reales de configuración; "Replay inmediato de una emisión con interés", "Replay después de un pago" ($2.000,00 y
  $72.000,00) y "Replay después de anular" ($2.000,00 y $100.000,00), sin filas nuevas, contadas con
  `contar_escrituras`; emisión concurrente con un pago de **otra** unidad del edificio (sin 40P01, el pago
  espera y ve el interés). Mutantes: el replay recalcula y escribe intereses → `contar_escrituras` no
  vacío; el replay devuelve sólo los intereses que cuentan → "Replay después de anular" sin interés;
  el replay arma el saldo sin los intereses → "Replay inmediato" da $100.000,00; bloquear las cuentas en
  dos pedidos (emisión y después el resto) da `BloqueoFueraDeOrden` o interbloqueo; la foto trae sólo el
  máximo `hasta` de cada interés (mutante de la 3.2 sobre el camino real) → "Un hueco anterior..." da
  $3.000,00, rojo.
  - RED 5.3 (16:23, mismo comando): hueco, tasa cero, recupera el tramo y no cobra dos veces rojos por `hay 0`;
    los tres replay por `EmisionRegistrada no informa intereses`; la concurrente por `el pago de U2 no esperó a
    la emisión que le registra interés` (hoy U2 no se bloquea ni tiene interés).
  - GREEN 5.3 (16:30, mismo comando): verde, con el contra-asiento hecho por `correcciones.corregir`.
    Mutantes (16:33 a 16:34): M10 replay devuelve sólo los intereses que cuentan rojo por `KeyError` al leer
    la cuenta en `replay_despues_de_anular...` (el interés ya no figura); M11 replay arma el saldo sin los
    intereses rojo por `assert Dinero("100000.00") == Dinero("102000.00")` en `replay_inmediato...`; M12
    bloquear en dos pedidos rojo por `BloqueoFueraDeOrden` en la concurrente (depende del orden de ids de
    cuenta: una corrida de la otra prueba quedó verde por azar del `uuid4`); M13 la foto con cobertura desde
    el principio hasta el máximo `hasta` (mutante de 3.2 sobre el camino real) rojo en `un_hueco_anterior...`
    por `assert Dinero("3000.00") == Dinero("5000.00")`. **Sin mutante, por equivalente**: "el replay
    recalcula y escribe intereses": un replay que recalculara encontraría el corte ocupado (E1) y no
    escribiría nada; lo vigilan `escrituras == []` y `conteos` iguales, que no se pueden poner rojos con un
    recálculo honesto de este diseño.
- [x] 5.4 **Cuentas alcanzadas: anulación y replay (PR-02, design D0).** Archivos:
  `emisiones.py` (`anular_emision`, hoy `:257-265`; `_replay`, `:85-121`, con el bloqueo y la foto en `:116-117`),
  `backend/tests/integracion/test_cc_anulacion_candado.py`. Escenarios: libro-de-movimientos "Anular
  bloquea también la cuenta que sólo recibió interés", "Anulación durante el contra-asiento de un interés
  de una cuenta sin obligación" y "La lectura incluye la cuenta que sólo recibió interés". RED (comportamiento
  nuevo): con el código de hoy, la carrera del contra-asiento del interés de U2 escribe sobre la emisión
  ya anulada (`anuladas_al_escribir != 0`), y el espía de `bloquear_cuentas` ve sólo U1. La emisión que
  registra el interés de U2 se confirma antes de instalar la pausa, como en 1.3. GREEN: la sentencia de
  cuentas alcanzadas de D0 en anulación y replay, un solo `bloquear_cuentas` ordenado. Mutantes: anular
  descubre cuentas sólo desde `obligacion` → la carrera y el espía rojos; dos llamadas a
  `bloquear_cuentas` (obligaciones y después intereses) → espía rojo o `BloqueoFueraDeOrden`; el replay
  bloquea y lee sólo las cuentas de sus obligaciones → el escucha de 1.2 rojo (la última lectura no pide
  U2).
  - RED 5.4 (16:23, mismo comando): `candados pedidos: [[<una cuenta>]]` en vez de `{u1, u2}`; `U2 no recibió el
    interés de septiembre en la emisión de octubre`; la última foto del registro pidió una sola cuenta en vez de
    `{u1, u2}`.
- [x] 5.5 **Regresión de los consumidores del 4b.** Correr `pytest tests/integracion -k "test_cc_ or
  test_libro"` y `tests/unitarios/cuenta_corriente`; comparar con la línea de base de la 2.2. Inventario
  de llamadas directas a `registrar_emision` (revisor del plan, intento 1), cada uno con su resultado
  anotado acá: `test_cc_lecturas.py:35,96`, `test_cc_emisiones.py:50,291`,
  `test_cc_creditos.py:38,189,214,324`, `test_cc_correcciones.py:42,463`,
  `test_cc_replay_carrera.py:250,305`, `test_cc_concurrencia.py:50`, `test_cc_anulacion_candado.py:110`,
  `test_cc_auditoria_api.py:59`. Para `test_cc_auditoria_api.py` (usa `ApiEdificio`, no `sembrar`),
  verificar si su emisión llega a leer configuración (hoy vencimiento de octubre y corte septiembre: no
  debería) en vez de suponerlo. Cada expectativa que cambie se explica en esta tarea (por qué el interés
  la cambia) o se corrige el código, nunca se ajusta en silencio. Incluye volver a correr los mutantes de
  1.2 y 1.3 sobre el código nuevo.

  - GREEN 5.4 (16:30, mismo comando): verde. Mutantes (16:34): M14 anular descubre cuentas sólo desde
    `obligacion` rojo por `candados pedidos: [[u1]]` (`assert [{u1}] == [{u1, u2}]`); M15 dos llamadas a
    `bloquear_cuentas` rojo por `candados pedidos: [[u1], [u2]]`; M16 el replay bloquea y lee sólo las cuentas de
    sus obligaciones rojo por `assert [{u1}] == {u1, u2}` en `la_lectura_del_replay_incluye...` (test
    agregado a 5.4 porque el escucha de 1.2 no tiene cuenta de sólo interés). La carrera del contra-asiento
    del interés de U2 queda verde con el código nuevo (el mutante M14 la pone roja junto con el espía; con `-x`
    se vio el espía primero).
  - Evidencia 5.5 (16:35; regresión de los consumidores del 4b, `cd backend && uv run pytest tests/integracion -k
  "test_cc_ or test_libro" -q`): `429 passed` (línea de base de `main` más la 2.2: 405; suma 24 tests nuevos
  de 5.1 a 5.4); `tests/unitarios/cuenta_corriente` y `test_fronteras_de_modulos.py`: `154 passed`; `ruff
  check`, `ruff format --check` y `mypy` limpios. Primera pasada con el interés: 15 tests rojos, todos
  `Conflicto("configuracion")` (emitir con deuda vencida sin versión de configuración). Se corrigió el
  **setup**, no la expectativa: cada uno pide `sembrar(base, con_configuracion=True)` (tasa 0,00, no registra
  interés) con una fixture `mundo_con_configuracion` en su archivo y un alias `mundo = ...`; ningún nombre de
  test cambió ni ninguna expectativa de importe. Inventario:
  `test_cc_lecturas.py` (`test_saldo_anterior`, `..._con_credito_a_favor`, `test_la_foto_trae_corte_tramos_e_interes_desde`:
  emiten dos períodos); `test_cc_emisiones.py` (`test_emitir_de_nuevo_despues_de_anular_imputa_el_pago_devuelto`,
  `test_credito_a_favor_se_imputa_en_la_emision_siguiente`, `test_replay_devuelve_el_saldo_anterior_por_cuenta`);
  `test_cc_creditos.py` (`test_ejemplo_de_r04_contra_la_base`, `test_destino_fijo_sin_destino_y_sin_capacidad`,
  `test_reusar_la_operacion_con_otro_destino`); `test_cc_correcciones.py`
  (`test_credito_de_correccion_va_con_r04_a_la_deuda_mas_vieja`); `test_cc_replay_carrera.py`
  (`test_el_replay_que_perdio_la_carrera_no_reimputa[pago|credito_correccion]`,
  `test_el_replay_de_emision_devuelve_una_sola_foto`); `test_cc_concurrencia.py`
  (`test_una_emision_y_un_pago_a_la_vez`, `test_emisiones_con_unidades_nuevas_cruzadas`);
  `test_cc_anulacion_candado.py` (los cuatro RF-01/RF-04 de emisión y replay, que emiten octubre con deuda de
  septiembre). Sin cambio y verdes: `test_cc_auditoria_api.py` (una sola emisión sobre un edificio sin deuda
  previa: no llega a leer la configuración, comprobado al pasar sin tocarlo) y las demás llamadas del
  inventario. Mutantes de 1.2 y 1.3 sobre el código nuevo (16:35, mismo método): "una foto por cuenta" al emitir
  (M17) rojo en `test_rf01_la_ultima_foto_de_la_emision_nueva_pide_todas_las_cuentas` por `assert {a} == {a, b}`;
  en el replay (M18) rojo en `..._del_replay_...` por el mismo `assert`; `anular_emision` sin `bloquear_cuentas`
  (M19) rojo en las dos formas de RF-02 por `anuladas_al_escribir == 0` (`assert 1 == 0`).

## 6. Saldo inicial (R09)

Archivos de producción: `backend/src/proptech_core/cuenta_corriente/aplicacion/saldo_inicial.py`
(nuevo, design D5). Tests: `backend/tests/integracion/test_cc_saldo_inicial.py` (nuevo).

- [x] 6.1 **Contrato de filas y validaciones (E11, E16).** Escenarios: "Vencimiento futuro", "Período con
  sólo interés", "Unidad repetida", "Fila repetida", "Mismo período con vencimientos distintos", "Carga
  manual sin motivo", y los demás rechazos de "La carga rechaza entradas que no puede registrar" (detalle
  y total mezclados, importe negativo, crédito no positivo, período que no es día 1 o posterior al mes de
  migración, fecha de migración futura). RED: cada rechazo falla por su aserción de campo. Mutantes:
  aceptar vencimiento igual a la migración + 1 día; tomar el vencimiento de la primera fila cuando
  difieren; no chequear filas repetidas; validar el capital por fila en vez de por período (rechaza
  "Fila de sólo interés junto a otra con capital", que tiene que entrar). Verificación extra: ninguna
  fila escrita (`contar_escrituras`).
  - RED (18:44, tanda 2, andamio sin comportamiento: `dominio/saldo_inicial.py` con los tipos y `normalizar_pedido`/
    `firmar_pedido` triviales, y `registrar_saldo_inicial` que devuelve un resultado vacío sin escribir):
    `uv run pytest tests/integracion/test_cc_saldo_inicial.py -q` da `25 failed, 3 passed`. Los rechazos de 6.1 fallan por
    `Failed: DID NOT RAISE EntradaInvalida` en `test_cada_rechazo_nombra_su_campo_y_no_escribe_nada` (primer caso del bucle,
    `vencimiento_un_dia_despues_de_la_migracion`) y en el resto de los de 6.1; los de registro, por
    `AssertionError: la unidad no tiene cuenta` (nada se escribió). Pasan en el andamio, y se prueban sólo con su mutante en la tanda de producción, los de
    replay (otro orden, tras confirmar) y `otra_administracion_no_ve_la_carga` (ver 6.4).
  - GREEN y mutantes de 6.1 (18:46 a 18:48, producción `be2c077`; copia previa en el scratchpad, uno a la vez, revertido;
    `pytest tests/integracion/test_cc_saldo_inicial.py -q`, `1 failed, 27 passed` salvo donde se indica). GREEN: `49 passed`
    (28 de integración y 21 del unitario de la firma). Defensa apagada y aserción roja:
    vencimiento hasta migración + 1 día (M1), rojo en `test_cada_rechazo_nombra_su_campo_y_no_escribe_nada` por
    `Failed: vencimiento_un_dia_despues_de_la_migracion: el pedido inválido se registró`; sin el chequeo de vencimientos distintos
    del mismo período (M2), `mismo_periodo_con_vencimientos_distintos: el pedido inválido se registró`; sin el chequeo de filas
    repetidas (M3), `fila_repetida_entre_unidades: ...`; vencimiento mirado sólo en la primera fila (M2b), rojo en el mismo test y
    en `test_el_vencimiento_se_compara_en_cada_fila_no_solo_en_la_primera` (`DID NOT RAISE EntradaInvalida`); capital medido por fila
    en vez de por período (M4), rojo en `test_fila_de_solo_interes_junto_a_otra_con_capital_entra` y en
    `test_una_fila_de_solo_interes_se_liga_al_interes_y_no_a_la_obligacion` por `EntradaInvalida: interes_acumulado` (el pedido que
    tiene que entrar se rechaza). Ninguna fila escrita: el bucle de rechazos afirma `escrituras == []` (`contar_escrituras`) y
    `conteos(s) == antes` en la misma transacción, y `test_la_transaccion_sigue_usable_despues_de_un_rechazo` registra después.
- [x] 6.2 **Registro con detalle, total único, interés importado y crédito.** Escenarios: "Dos períodos
  viejos", "Dos conceptos del mismo período", "Fila de sólo interés junto a otra con capital", "Total
  único", "Interés importado sin recalcular", "Total único con interés traído", "Unidad con saldo a
  favor", "Deuda y crédito en la misma unidad" ($7.000), "Origen del importador" (fila 7 de
  `saldos-octubre.xlsx`), "Origen de dos conceptos del mismo período" (filas 12 y 13). Mutantes: una
  obligación por fila → "Dos conceptos del mismo período" choca con `uq_obligacion_operacion` o deja dos
  obligaciones, rojo; el interés importado entra en otro componente (entraría en la base); el crédito no
  se imputa; el origen se liga a otra fila; el interés importado se liga a todas las filas del período →
  rojo porque la fila 13 queda ligada al interés. Consumidor: el 5 (el contrato de filas se copia a su
  ficha al cerrar, con el signo del crédito como responsabilidad del 5).
  - RED de 6.2: ver arriba (`test_dos_conceptos_*`, `test_el_interes_importado_*`, `test_total_unico_*`,
    `test_el_credito_se_imputa_*`, `test_el_origen_*`, `test_devuelve_cuentas_y_totales`, todos en rojo por `AssertionError`).
  - GREEN y mutantes de 6.2 (18:48, mismo método): una obligación por fila (M5), rojo en 11 tests, la primera
    mitad por `psycopg.errors.UniqueViolation: uq_obligacion_operacion` y `CheckViolation: ck_obligacion_importes` (la base, no una
    aserción: el brief prevé "choca con `uq_obligacion_operacion`"); el interés importado entra en la base de la obligación (M6, la
    base de datos impide otro componente: `ck_mov_interes`), rojo en `test_dos_conceptos_del_mismo_periodo_son_una_obligacion` por
    `assert ('10500.00', ...) == ('10000.00', ...)` y en `test_devuelve_cuentas_y_totales`; el crédito no se imputa (M7), rojo en
    `test_el_credito_se_imputa_a_la_deuda_con_r04` por `assert (Dinero("1000...` == (Dinero("7000...` (deuda $10.000 en vez de
    $7.000); el interés se liga a las filas de capital (M8) o a todas las filas del período (M9), rojo en
    `test_el_origen_liga_cada_fila_a_lo_que_formo` por `assert {12, 13} == {12}` y en
    `test_una_fila_de_solo_interes_...` por `assert {15} == {14}` / `{14, 15} == {14}`; el origen de capital ligado sólo a la primera
    fila (M9b), rojo por `assert {12} == {12, 13}` y `set() == {15}`.
- [ ] 6.3 **Interés desde la migración, contra la emisión (E3.2, E13, E18).** Escenarios: "Primer interés
  después de migrar" ($1.280,00 y $1.360,00 con corte 31/10/2026), el total único con gracia 0 ($800,00),
  "Mes entero después de migrar" ($2.400,00 y $2.550,00, tramo 16/10-31/10), "Mes entero después de
  migrar, con interés importado" ($2.400,00), "Segundo mes después de migrar" ($2.400,00, tramo
  01/11-30/11). Mutantes: el interés de una obligación migrada corre desde su vencimiento original → rojo
  por el monto proporcional ($1.280,00 pasa a $6.560,00 sobre agosto, 82 días) y por la fecha del tramo; el mes de la
  migración no se cobra (la alternativa (a) de E18) → $0,00 en el corte 31/10, rojo; el interés importado
  suma a la base → rojo en el escenario con interés importado ($2.520,00 sobre $84.000).
- [x] 6.4 **Estado de migración, carga única, replay por firma y tenant (PR-11).** Archivos además de los
  del grupo: `backend/tests/unitarios/cuenta_corriente/test_firma_saldo_inicial.py` (nuevo, la función pura
  que normaliza y firma el pedido, design D5). Escenarios: "Edificio sin saldos previos", "Importador
  cerrado sin carga previa", "Segunda carga con otra operación", "Dos cargas simultáneas" (PostgreSQL
  real, dos conexiones), "Replay de la carga" (después de confirmar), "Misma operación con otros datos",
  "Misma operación con iguales sumas y otras filas" ($85.000/$20.000 frente a $84.000/$21.000), "Mismo
  pedido en otro orden", "Unidad de otro edificio", "Otra administración no ve la carga". RED del replay
  por firma: con un replay que compara lo que quedó en el libro (obligaciones, intereses y filas ligadas,
  como `_replay` de emisiones), "Misma operación con iguales sumas..." devuelve lo registrado en vez de
  conflicto. Mutantes: sin el chequeo de `pendiente` → "Importador cerrado sin carga previa" registra; sin
  el único por edificio (la concurrencia registra dos); el replay después del chequeo de estado (el replay
  tras confirmar da conflicto); la firma calculada sobre las sumas por período y componente en vez de por
  fila → "iguales sumas" sin conflicto, rojo; la firma sin ordenar unidades y filas → "Mismo pedido en
  otro orden" da conflicto, rojo; importes sin normalizar a dos decimales → ídem por `85000` frente a
  `85000.00`; la firma sin el interés acumulado de cada fila → mover $1.000 de interés de la fila 12 a la
  13 pasa como replay, rojo (caso extra del test unitario). Consumidor: el 5; su contrato se copia a la
  ficha del 5 al cerrar, con PA-1 como bloqueante y el pedido de E18 (mostrar el mes de la migración).

  - RED de 6.4 (18:44): `tests/unitarios/cuenta_corriente/test_firma_saldo_inicial.py` da `16 failed, 5 passed`
    (`assert 'v1:000...' != 'v1:000...'` en las propiedades de "otra firma"; pasan, vacuamente, las de "misma firma", que
    se prueban con su mutante). En integración: `Failed: DID NOT RAISE Conflicto` en `test_solo_se_carga_con_la_migracion_pendiente`
    (las dos), `test_segunda_carga_con_otra_operacion`, `test_misma_operacion_con_*`; `AssertionError: se esperaba una sola carga,
    hay 2` en las dos cargas simultáneas; `DID NOT RAISE NoEncontrado` / `IdentidadDeOtraAdministracion` /
    `RegistroFueraDeTransaccion` en tenant y transacción.

  - GREEN y mutantes de 6.4 (18:49, mismo método): sin el chequeo de `pendiente` (M10), rojo en las dos de
    `test_solo_se_carga_con_la_migracion_pendiente` por `Failed: DID NOT RAISE Conflicto`; replay después del chequeo de estado (M12),
    rojo en `test_replay_despues_de_confirmar_devuelve_lo_registrado` por `Conflicto: conflicto` (de `estado_migracion`); sin el único
    por edificio (M11, se quita `uq_carga_complejo` de la migración 0035 en una copia, restaurada), rojo en
    `test_segunda_carga_con_otra_operacion` (`DID NOT RAISE Conflicto`) y en `test_dos_cargas_simultaneas_...` por
    `AssertionError: se esperaba una sola carga, hay 2`; firma sin ordenar unidades y filas (M14), rojo en
    `test_mismo_pedido_en_otro_orden_da_la_misma_firma` (`assert 'v1:18267c...' == 'v1:43895c...'`) y en
    `test_mismo_pedido_en_otro_orden_y_con_importes_sin_decimales_es_replay` (`Conflicto`); firma sobre las sumas por período y
    componente (M13), rojo en `test_iguales_sumas_con_otras_filas_dan_otra_firma` (`assert 'v1:e585...' != 'v1:e585...'`), en
    `test_mover_interes_de_una_fila_a_otra_da_otra_firma`, en `[numero_de_fila]` y, contra PostgreSQL,
    en `test_misma_operacion_con_iguales_sumas_y_otras_filas_es_conflicto` (`DID NOT RAISE Conflicto`); firma sin el interés
    acumulado de cada fila (M16), rojo en `test_mover_interes_...` y `[interes]` por `assert 'v1:eefa...' != 'v1:eefa...'`; origen
    sin recortar antes de firmar (M17), rojo en `test_el_archivo_se_normaliza_antes_de_firmar`.
    **Mutante no ejecutable, equivalente:** "importes sin normalizar a dos decimales": `Dinero` los cuantiza a dos decimales al
    construirse, así que `85000` y `85000.00` ya son el mismo valor antes de firmar; el caso queda cubierto por
    `test_el_importe_escrito_sin_decimales_da_la_misma_firma` y no hay mutante que lo distinga sin tocar `Dinero`.
    Aceptación: `python3 aceptacion/H-005/aceptar.py --codigo HEAD --sin-regresion` sobre `be2c077` (aceptación `2fcf6ba`): C01 a C03,
    C07 a C11 y C13 a C19 PASAN; C04 falla sólo en `test_c04_interes_importado_sin_recalcular` (`Dinero("6560.00") == Dinero("1280.00")`,
    el interés de R03 desde la migración: es de 6.3); C05, C06 (salvo "segundo mes", que ya pasa) y C12, de 6.3; C20, C21 y C22 no
    son de código.
## 7. Situación de cobranza (R20, R30)

- [ ] 7.1 **Clasificación pura.** Archivos: `backend/src/proptech_core/cuenta_corriente/dominio/cobranza.py`
  (nuevo, design D6), `backend/tests/unitarios/cuenta_corriente/test_cobranza.py`. Escenarios: "Dentro de
  la gracia", "Interés en su período" (dos liquidaciones, $169.000), "Saldo chico", "Dos saldos chicos
  que juntos pasan el umbral", "Justo en el umbral", "Una sola vencida", "Dos vencidas con saldo", "Pago
  parcial que no cancela ninguna", "Un saldo grande y uno chico", "Un período con sólo interés no
  cuenta" (caso mixto de E7), "Sólo intereses". Mutantes, cada uno rojo: `>` en vez de `>=` en el umbral
  (cumple D-143, E6); contar un período con sólo interés (E7); restar el crédito a favor del total
  vencido; vencida al día siguiente del vencimiento ignorando la gracia; umbral comparado por obligación
  en vez de por cuenta.
- [ ] 7.2 **Situación por cuenta y por edificio (E14, PR-01, PR-06).** Archivos:
  `backend/src/proptech_core/cuenta_corriente/aplicacion/cobranza.py` (nuevo),
  `backend/tests/integracion/test_cc_cobranza.py`. Escenarios: "Emisión anulada", "Deshacer un pago
  vuelve a marcar" (contra-asiento de un pago), "Migrada con dos períodos", "Migrada con total único",
  "El umbral no frena el interés", "Listado del edificio", "Un pago posterior cuenta aunque la fecha sea
  anterior", "Edificio de otra administración", "Sin configuración". Mutantes: incluir cuentas de
  persona; leer el umbral de `parametros.yaml` en vez de la versión vigente; filtrar movimientos por
  `fecha_valor <= fecha` → "Un pago posterior..." rojo (prueba que no se promete historia); traducir el
  `NoEncontrado` de `configuracion_vigente` a `Conflicto("configuracion")` → "Edificio de otra
  administración" rojo. **Filtro de tenant del SQL** (separado de RLS, L-034): ensayo con la conexión
  privilegiada de los tests (la que usa `test_catalogo_rls.py` antes de su `SET LOCAL ROLE`), con la
  precondición afirmada de que RLS no la filtra (`rolsuper` o `rolbypassrls` verdadero), `SET LOCAL
  app.administracion_id` en B, ejecutar la sentencia de cobranza del edificio de A y afirmar cero filas;
  transacción revertida, sin tocar login ni roles. Mutante: quitar `c.administracion_id = t.adm` de la
  sentencia → este ensayo rojo; el test de "Edificio de otra administración" como app queda verde, como
  se espera (lo tapa RLS) y se anota. Consumidores: 10a, 10b y 8, anotados en sus fichas al cerrar con el
  significado de la fecha (E14).

## 8. Cierre del constructor

- [ ] 8.1 **Fronteras, calidad y suite completa sobre el SHA entregado.** `pytest
  tests/unitarios/test_fronteras_de_modulos.py` verde con el import nuevo `cuenta_corriente →
  complejos.aplicacion.lectura` y sin SQL ajeno; `ruff check`, `ruff format --check` y `mypy` sobre todo
  `src/` (L-063); suite completa `pytest tests/` una vez, entera, sobre el SHA final (L-041, L-055,
  L-064), con conteo propio y fallas previas conocidas nombradas (por ejemplo, las de Windows de D-110 si
  aplica). Registrar comando, hora, SHA y resultado acá; lo que no se pudo correr queda como no
  ejecutado, no como verde.

## Workflow follow-up

- Rompedor (breaker) en rondas hasta limpio, con foco en: interés en bordes de fecha (fin de mes,
  bisiesto, gracia 31), cambios de forma entre cortes, meses calendario de "mes entero" (fracciones,
  gracia que cruza un mes, migración a mitad de mes), huecos por contra-asiento de un interés que no es
  el último (E17), cortes con tasa 0 (E19), réplica de una carga con iguales sumas (PR-11), pagos
  con fecha valor anterior a imputaciones ya registradas (H-13), anulación y re-emisión en la misma
  transacción, anulación frente a correcciones de cuentas que sólo recibieron interés, filas del Excel
  agrupadas por período, carga de saldo inicial concurrente, tenant de las tablas nuevas.
- Auditor con verificación independiente de conteos y de los mutantes de cada tarea.
- Archivo: actualizar la base según `## Knowledge Base Impact` de `proposal.md` (R03, R09, R17, R20,
  R30; modelo de datos; arquitectura; decisiones con E1 a E19 (E3.2 y E13 como la decisión de Juani del 30/10/2026); preguntas PA-1 a PA-3, con PA-1 como
  bloqueante del 5; glosario; fichas del 4c, 5, 7, 8, 10a y 10b), `CHANGES.md`, la sección "Estado" de
  `CLAUDE.md` y `AGENTS.md` (iguales) y `obsidian.md`.
