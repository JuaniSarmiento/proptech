Convención (la del 4a): en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN);
el rojo se anota en esta tarea con el comando, su salida y la hora. **El rojo cuenta sólo si cae en la
aserción que el test dice probar** (L-034): un `ModuleNotFoundError`, un `ImportError` o una tabla que
no existe no son un rojo. Cuando el módulo o la tabla todavía no existen, primero se crea vacío (la
función existe y devuelve vacío o `None`; la tabla existe sin la restricción que se prueba) y el rojo se
mide contra eso. Un test que nace verde porque la garantía ya existe se declara **fijación** y se lo ve
fallar con un mutante en una copia o en un `SAVEPOINT`, después de sacar una copia previa y diciéndolo
(L-013, L-019, L-035). "Verde" en el backend es `bash infra/ci/test-backend.sh` sobre los archivos
tocados, más `ruff check`, `ruff format --check` y `mypy` (L-005). Toda garantía que vive en PostgreSQL
se prueba contra PostgreSQL real, nunca contra un doble (D-120). Cada tarea nombra los escenarios que
cubre (`capability` › escenario) y las lecciones que aplica.

**NO CONSTRUIR**: el change es **CRITICAL**. Precondición: la sección "Aprobación" de `proposal.md`
firmada por Juani, Alberto o Emiliano, con nombre, fecha y la respuesta a cada elección (D-094, D-111).
Una regla nueva que entre después de la firma necesita firma propia (L-029). Las excepciones nuevas
(escaneo de tablas, permisos) no las agrega el constructor: las trae (L-030).

**Orden obligatorio**: el grupo 1 (tablas y protección) antes que todo lo que escribe en el libro; 2
(dominio puro) antes que 3; 1.3 cierra con la suite completa (L-041).

**Cantidad**: 19 tareas, debajo del límite de `config.yaml`. **Si en la construcción alguna no entra en
medio día**, el corte propuesto es: **4b-1** grupos 1, 2 y 3 sin la 3.5 (el libro, la imputación y las
lecturas, que es lo que el 4c y el 7 necesitan) y **4b-2** la 3.5, el grupo 4 y el 5 (la corrección
HU-A9 con su permiso, su ruta y su contrato, el escaneo de tablas y la deuda del 4a). No se parte sin
avisarle a Juani antes.

## 1. Tablas del libro y su protección (design D1, D2, D5, D13)

- [x] 1.1 **Migración `0023`, parte A: `cuenta`, `candado_de_cuenta`, `emision`, `evento_de_emision`.**
  Antes de escribirla, `rg` del repo entero por `0023` (choque con el 3c) y por escrituras en estas tablas
  desde `infra/` (L-023). Tests de integración, como `proptech_app` con tenant: los dos dueños y ninguno
  rechazados; único de la cuenta de unidad; período que no es primer día de mes rechazado; único de
  `intento`; evento sin motivo o en blanco rechazado; un solo evento `anulada` por emisión; FK compuesta
  que impide apuntar a otra administración; RLS (B no ve lo de A). Sobre la base del deploy, la app recibe `42501` en `UPDATE`,
  `DELETE ... WHERE false`, `INSERT ... ON CONFLICT DO UPDATE` y `TRUNCATE ... CASCADE`; en casos
  separados, el rol de arranque recibe `P0001` con el texto de cada tabla por sus triggers (también vale
  app con el `GRANT` pertinente dentro de un savepoint que se revierte, patrón `test_catalogo_rls.py`).
  El RED del trigger se observa quitando sólo ese trigger con los permisos ya concedidos (QA-1); `candado_de_cuenta` sí admite `UPDATE` y `SELECT ... FOR
  UPDATE` como la app, pero `DELETE` está revocado y da `42501` (DB-11). RED: cada restricción probada contra la tabla creada sin ella (una por vez, en una
  copia de la migración), y cada trigger con su tabla sin el trigger, usando el rol que puede llegar a él. `downgrade` que se niega si hay filas
  (como dueño, con `NO FORCE`, design Migration Plan), visto rojo con una fila. Mutante
  QA-16: quitar `NO FORCE ROW LEVEL SECURITY`; la conexión de Alembic no fija tenant y el test exige
  que no se borre la fila, con lo que ese mutante cae en la aserción de conservación. Escenarios:
  `libro-de-movimientos` › Editar un movimiento por SQL directo (para cuenta, emision y evento_de_emision); › Borrar sin filas
  también se rechaza; › Vaciar una tabla con hijas; › Upsert sobre el libro; › Otra administración no ve la
  cuenta; › Cuenta sin dueño; › Cuenta con los dos dueños; › Período que no es un mes. Lecciones: L-018,
  L-023, L-034, L-036.
  Escenarios adicionales (RC-09): `libro-de-movimientos` › Los triggers frenan aun con permiso de escritura.

- [x] 1.2 **Migración `0023`, parte B: `tipo_de_movimiento`, `obligacion`, `movimiento`, `imputacion`.** Tests como en 1.1, más:
  importe negativo y obligación en cero rechazados; `num_nonnulls(emision_id, operacion_id)`; los únicos
  de D5 (obligación por emisión y cuenta, `operacion_id`, interés por obligación y corte, `corrige_a` una
  sola vez); coherencia `tipo`/`sentido`/destino fijo; imputación de un débito rechazada **por la FK** de
  `sentido_del_movimiento`; imputación a una obligación de otra cuenta rechazada por la FK; contra-asiento
  de otro importe o de otra cuenta rechazados por la FK de `corrige_a`; crédito de corrección
  que sí admite un contra-asiento una sola vez (E6); ninguna columna
  `saldo`, `residual` ni `pagad` (catálogo). RED: cada restricción vista fallar contra la tabla sin ella;
  el catálogo, con una columna `saldo` agregada en una copia. Escenarios: `libro-de-movimientos` › Una
  obligación no puede apuntar a una cuenta ajena; › Obligación con importe negativo; › Catálogo sin
  columnas de saldo; `correccion-de-movimientos` › Corregir una corrección (la parte de la base).
  Lecciones: L-018, L-034, L-035.
  Casos de DB-1: **B**, imputación con `sentido_del_movimiento NULL`, rechazada por NOT NULL;
  **D**, contra-asiento de $999 sobre interés de $50 con `tipo_corregido NULL`, rechazado por el CHECK
  del par nulo; **E**, movimiento con obligación de otra cuenta, rechazado por FK; **F**, movimiento con
  cuenta inexistente, rechazado por FK. Agregar C (movimiento inexistente con sentido nulo) y cruces de
  `complejo_id` y `periodo` repetidos (DB-9). Cada FK y único de D1 se prueba con fila válida y violación;
  el par `(corrige_a, tipo_corregido)` lleva `CHECK num_nulls(...) IN (0,2)`, no MATCH FULL sobre columnas
  de tenant obligatorias. La FK `(tipo, sentido)` referencia el vocabulario ampliable con INSERT; probar
  alta de un tipo nuevo sin ALTER y rechazo de un par no declarado. Un INSERT válido por cada tipo y
  sentido anticipado (QA-12): `interes` débito con corte; `pago` crédito; `correccion` en ambos sentidos;
  `condonacion`, `ajuste_de_interes` enlazado, `bonificacion`, `baja_de_deuda`, `saldo_inicial` con
  `operacion_id`; `reversion_de_pago` débito, `reimputacion` y `traslado` en débito y crédito. Enlace
  `(administracion_id, enlazado_a)` entre cuentas distintas de la misma administración válido; entre
  administraciones, inválido. CHECK acotados para destinos conocidos, sin cerrar futuros tipos. Caso RC-02: INSERT
  `correccion/debito` con obligación, componente, operación y motivo válidos pero `corrige_a` y
  `tipo_corregido` nulos da `23514`; quitar sólo el CHECK que exige `corrige_a` da rojo en la
  aserción de rechazo. Probar también el CHECK de crédito de corrección libre con obligación.
  Comparar cada regla por tipo de la tabla de conservación de D1 contra `4823515`, sin omisiones.
  `imputacion` lleva secuencia monótona de orden; ni `now()` ni UUID deciden E7. Cada índice restante
  nombra su consulta SQL y se elimina el que no sirve a ninguna (DB-6). Escenarios adicionales:
  `libro-de-movimientos` › Tipos anticipados válidos; › Enlace entre cuentas de la administración;
  › Los casos de NULL y cuenta ajena se rechazan; › Edificio y período coherentes;
  `imputacion-de-creditos` › Dos imputaciones con la misma fecha de registro (E7).
  Escenarios adicionales (RC-09): `libro-de-movimientos` › Débito de corrección sin referencia.

- [x] 1.3 **Las seis tablas en la lista única; `roles despues` y el chequeo de arranque las cubren.**
  Sumar las seis a `compartido/tablas_protegidas.py` con su texto y sus tres triggers (D1 del 4a); cambiar `despues()` de `roles.py` para dar al migrador
  `GRANT REFERENCES` sobre las seis tablas protegidas del libro (E15, AR-1); no sobre
  `candado_de_cuenta`, que ya pertenece al migrador. Agregar `tipo_de_movimiento` a
  `_TABLAS_EXCLUIDAS_DEL_GRANT_A_LA_APP` y en `despues()` hacer `REVOKE INSERT, UPDATE, DELETE`,
  dejando SELECT, como con `accion_de_auditoria` (RC-01). Test tras el ciclo real antes/migrar/despues:
  app intenta INSERT en el vocabulario -> `42501`, SELECT válido; repetir el ciclo y exigir lo mismo.
  RED: mutante que omite exclusión y REVOKE permite INSERT y falla la aserción de permiso. Tests: `despues()` transfiere tablas y funciones y verifica por el efecto; la API y el
  worker no arrancan con `imputacion` del migrador; el test de catálogo da rojo si `movimiento` sale de la
  lista; `candado_de_cuenta` no está en la lista. **RB-4**: tabla homónima en otro esquema creada antes y
  después que la de `public`, y el mutante que saca `schemaname = 'public'` rojo en los dos órdenes.
  **QA-15**: función de bloqueo con otro dueño, y función con el texto de otra tabla, rojas en `despues()`.
  RED: sin las seis en la lista, el test de catálogo nombra cada una. Como migrador después del `roles despues` real, crear una tabla de prueba con FK a
  `movimiento`: RED sin el grant da `42501`, GREEN permite crearla; comprobar también REFERENCES en
  cada tabla del alcance. El grant no debe conferir ALTER, CREATE INDEX, DROP INDEX ni escritura del
  libro al migrador. Reversión del permiso: REVOKE impide FK nuevas pero no elimina las existentes
  (RC-14). Test: crear FK como migrador, revocar REFERENCES como dueño, comprobar la FK en catálogo
  y su rechazo de referencia inválida; crear otra FK falla `42501`. Reponer permiso y limpiar sólo
  la tabla de prueba como su dueño, sin modificar el libro. **Verde = la suite completa** de
  backend (L-041), con el número de tests antes y después. Escenarios: `aislamiento-por-administracion` ›
  El paso de roles verifica las seis por el efecto; › Una tabla del libro sin declarar; › La API no
  arranca con una tabla del libro del migrador; › Una tabla homónima en otro esquema no hace pasar el
  chequeo; › El candado no es de sólo agregar; › Tabla futura con FK al libro. Lecciones: L-016, L-018, L-022, L-036, L-041.
  Escenarios adicionales (RC-09): `aislamiento-por-administracion` › La app no amplía el vocabulario.

- [x] 1.4 **Ensayo de roles y rollback, corridos.** `infra/ci/ensayo-roles.sh`: antes de bajar de `0023`,
  comprobar como rol de arranque que las seis tablas están vacías y devolver tablas y funciones al
  migrador (Migration Plan, paso 1); corregir el mensaje `ciclo 0018/0016/0018`; ajustar
  `test_ensayo_login.py` a las revisiones nuevas. El test estático deriva la lista de
  `TABLAS_DE_SOLO_AGREGAR` y exige `ALTER TABLE ... OWNER` por cada tabla, sin una lista paralela
  (QA-13); mutante que omite sólo `movimiento` da rojo. En `0022`, guardar `pg_dump --schema-only`
  antes y después de subir a `0024` y bajar a `0022`, con dueños, permisos, políticas y funciones;
  normalizar sólo ruido de versión/identificadores de dump y exigir `diff` vacío, conservando los dos
  dumps y el comando (DB-8). Volver a subir a `0024` y comprobar revisión y conteos. Correrlo entero con un `COMPOSE_PROJECT_NAME` propio,
  nunca `proptech`, y pegar comando y salida (`ENSAYO ROLES OK`). RED: el script de hoy corrido sobre una
  base con `0023`/`0024` falla con `must be owner` (pegar la salida). Test del punto de no retorno: con
  una corrección auditada, bajar `0024` falla con `23503`; con una fila en `cuenta`, el `downgrade` de
  `0023` se niega. Escenarios: `auditoria-de-acciones` › El vocabulario nuevo (la bajada). Lecciones:
  L-006, L-043.

## 2. Reglas puras del libro (design D0, D6, D8)

- [x] 2.1 **Orden de imputación y destinos fijos.** `dominio/imputacion.py` con `Componente`,
  `ORDEN_DE_IMPUTACION` e `imputar(deudas, importe, destino)`. Tests, sin base: el ejemplo de R04; pago
  parcial que cubre la ordinaria antes que la extraordinaria; el fondo entre ordinaria y extraordinaria
  (E5, provisorio); pago exacto de un período; sobrante; destino fijo de condonación, ajuste de interés y
  bonificación. Si el componente no absorbe el importe completo, rechazar el pedido completo que contiene parte
  sobrante con `EntradaInvalida("destino")` antes de persistir, sin desviarla a R04 (E16); dos créditos seguidos que superan la deuda;
  cero y negativos rechazados por `EntradaInvalida("importe")` también en `imputar` puro;
  ningún residual negativo; montos `Dinero` y nunca `float`. RED contra `imputar` vacío (devuelve `([],
  importe)`). Mutantes: fondo antes de la ordinaria (rojo en el escenario del fondo); orden por obligación
  en vez de por período (rojo en el ejemplo de R04); destino fijo ignorado (rojo en condonación); sobrante fijo que se vuelve crédito libre (rojo:
  condonación $4.000 sin interés rechazada y luego diciembre $40.000 sigue en $40.000).
  Escenarios: `imputacion-de-creditos` › El ejemplo de R04; › Un pago parcial cubre la ordinaria antes que
  la extraordinaria; › El fondo de reserva, entre la ordinaria y la extraordinaria; › Un pago que cubre
  exacto un período; › Pago mayor que la deuda; › Una condonación baja sólo el interés condonado; › Un
  ajuste de interés baja sólo el interés que compensa; › Una bonificación va a la ordinaria de su período;
  › Destino fijo sin un componente que absorba; › Dos créditos que juntos superan la deuda; › Importe no positivo; › Bonificación de una emisión anulada. Lecciones:
  L-019, L-034.
- [x] 2.2 **Estado de una cuenta: residual, crédito a favor y saldo anterior.** `dominio/estado.py` con
  `calcular_estado`. Tests, sin base: capital desglosado en tres componentes; residual nunca negativo;
  crédito a favor por crédito; deuda total sin duplicar la obligación vieja (R06); saldo anterior sin la
  emisión pedida, con y sin crédito a favor (semántica exacta de D12). Guardar el snapshot publicado
  es prueba del 7, fuera de la cobertura del 4b; acá se verifica el valor puro y el retorno de 3.2. **Propiedad con `hypothesis`** (perfil `ci`): la invariante de D8 con un oráculo que suma
  débitos y créditos sin pasar por los componentes ni por `imputar`, y sin importar el
  predicado de exclusión de producción. Además de la identidad, exigir por componente residual ≥ 0 e
  imputado que cuenta ≤ debido, por crédito favor ≥ 0; con capital positivo, sin débitos adicionales y
  con una imputación positiva que cuenta, deuda < suma del capital (QA-2). Acotar generadores: hasta
  20 obligaciones y 20 créditos de $0,01 a $1.000.000,00 cada uno, suma absoluta de todos los importes
  generados <= $40.000.000,00, igual que D8 y dentro de NUMERIC(14,2); probar aparte el límite y el desborde, que da `MontoInvalido` (QA-10). RED contra `calcular_estado` vacío.
  Mutantes separados: sin el tope del paso 3 de D8 (residual negativo después de corregir
  interés ya cubierto) e ignora imputaciones (no baja la deuda); registrar la aserción exacta que cae,
  no aceptar sólo la identidad como oráculo. Escenarios: `libro-de-movimientos` ›
  Capital desglosado; › Saldo anterior sin débito nuevo; › Pagar marzo lo saca del saldo anterior; `imputacion-de-creditos` › Imputaciones efectivas reducen
  deuda; › Tope luego de corregir el interés.
  Lecciones: L-019, L-034, L-035.
- [x] 2.3 **Lo que no cuenta: emisión anulada, contra-asiento, ajuste enlazado y exceso.** Tests, sin
  base: anular deja la deuda como antes de emitir; el pago imputado a la emisión anulada vuelve como
  crédito; el ajuste que compensaba el interés anulado tampoco cuenta (D-085); el par corregido no cuenta y
  las imputaciones de otros créditos no se tocan; corregir un interés ya cubierto devuelve el exceso al
  crédito de la imputación más reciente a la más antigua (secuencia, E7). La propiedad de 2.2 extendida con anulaciones y correcciones aleatorias. RED contra
  la versión de 2.2 (sin exclusiones). Mutantes: exceso devuelto según fecha del crédito en vez de orden de la imputación (rojo en el
  escenario Crédito retroactivo con imputación posterior de RC-04); ajuste enlazado que sigue contando (rojo en D-085). Incluir bonificación de $2.000 de
  noviembre, emisión anulada y diciembre $40.000: sigue atada al destino anulado y diciembre debe
  $40.000 hasta reversión por el 8 (E16); devolver total a favor $2.000, aplicable $0 y retenido
  $2.000, con campos separados; mutante que la reimputa por R04 da rojo. Pago con fecha valor
  anterior a una corrección posterior: pendientes se ordenan por `fecha_valor`, sin reescribir hechos
  anteriores (AN-12). Cadena de E6: interés I débito, C1 contra-asiento crédito y C2 contra-asiento
  débito de C1; el cálculo parte del extremo más reciente, excluye C2/C1 y restaura I. Mutante que
  excluye todos los pares sin resolver la cadena da rojo en el residual. Escenarios: `libro-de-movimientos` ›
  Anular deja la deuda como antes de emitir; › El ajuste que compensaba el interés anulado;
  `imputacion-de-creditos` › Un pago imputado a una emisión que se anula vuelve como crédito;
  `correccion-de-movimientos` › Las imputaciones de otros créditos no se rehacen. Lecciones: L-019,
  L-034.

## 3. Casos de uso sobre la base (design D2 a D5, D7, D8, D12)

- [x] 3.1 **Cuenta de unidad y candado.** `aplicacion/cuentas.py`: `cuenta_de_unidad` (crea si falta,
  `ON CONFLICT (administracion_id, unidad_id) WHERE unidad_id IS NOT NULL DO NOTHING` y lee) y `bloquear_cuentas`. Tests contra PostgreSQL: dos pedidos, y dos
  transacciones simultáneas, devuelven la misma cuenta; una unidad de otro edificio da `NoEncontrado`;
  `bloquear_cuentas` sin una fila de candado la recrea; el candado nace en la misma transacción
  que la cuenta; rollback no deja ninguno de los dos. Todos los casos de uso fuera de transacción dan
  `RegistroFueraDeTransaccion`; `administracion_id` sale de `current_setting('app.administracion_id')`
  y, en las funciones que reciben identidad, se exige coincidencia antes del INSERT (BE-5.2-5). El llamador autoriza la acción y
  si va a tocar más de una cuenta reúne **todas** y llama a la API pública `bloquear_cuentas(ids)`
  en una llamada ordenada antes de escribir; el rebloqueo en la misma transacción es idempotente.
  Probar dos llamadas idénticas y dos operaciones unitarias con bloqueo interno tras prebloquear
  A/B. Dos transacciones componen operaciones A/B y B/A prebloqueando ambas cuentas; con barreras y
  timeout del servidor, ambas terminan sin `40P01`. Mutante: omitir el prebloqueo y adquirir A/B y B/A
  incrementalmente; la aserción de éxito de ambas cae por deadlock (RC-05).
  Coincidencia de tenant (RC-09): identidad de A en sesión con tenant B, cuenta y recursos visibles de
  B; exigir rechazo **antes del INSERT** y cero sentencias de escritura. Mutante que quita sólo la
  comparación debe llegar al INSERT (aunque RLS lo rechace después con 42501) y caer en la aserción
  de cero INSERT, no en un rechazo genérico que RLS también produciría. Chequear
  `current_setting('transaction_isolation') = 'read committed'`; en REPEATABLE READ, antes de escribir,
  `AislamientoNoAdmitido` (DB-4). Dos conexiones con snapshot vieja, barrera y pagos $60.000/$60.000
  sobre $100.000: sin chequeo la foto vieja permite imputar $120.000; el test registra ese
  resultado y exige el rechazo por aislamiento, de modo que el mutante cae en esa aserción; con chequeo
  la segunda rechaza y no escribe. Probar también READ COMMITTED exitoso, no sólo el rechazo. RED contra funciones que
  insertan sin `ON CONFLICT` (la segunda llamada falla con `23505` en vez de devolver el id). Escenarios:
  `libro-de-movimientos` › Pedir dos veces la cuenta de una unidad; `imputacion-de-creditos` ›
  REPEATABLE READ no usa una foto vieja; `aislamiento-por-administracion` › La app no borra candados. Lecciones: L-034.
  Escenarios adicionales (RC-09): `imputacion-de-creditos` › Varias cuentas prebloqueadas y rebloqueo interno.

- [x] 3.2 **`registrar_emision`.** Tests contra PostgreSQL: registra emisión y obligaciones; la misma dos
  veces no duplica; el mismo id con otro importe da `Conflicto("emision_id")`; segunda del período sin
  anular da `Conflicto("periodo")`; después de anular, intento 2; período inválido, sin obligaciones o con
  una unidad repetida dan `EntradaInvalida` con el campo; el crédito a favor de una cuenta se imputa a la
  obligación nueva. RED contra la función vacía (devuelve sin escribir), en cada aserción. Orden de D4: buscar replay por id, leer intentos, calcularlo y recién INSERT con
  `ON CONFLICT (id) DO NOTHING`; cuentas en una sola sentencia ordenada por `unidad_id`. Mutante
  QA-14: conservar `max(intento)+1` pero omitir comprobar si el anterior está anulado; la segunda
  emisión secuencial no anulada entra y cae la aserción de rechazo (no usar `intento=1` fijo). Escenarios: `libro-de-movimientos` › Segunda emisión del mismo
  período; › Emitir de nuevo después de anular; › La misma emisión dos veces; › El mismo id con otras
  obligaciones; `imputacion-de-creditos` › El crédito a favor se imputa en la emisión siguiente.
  Lecciones: L-017, L-034.
- [x] 3.3 **`anular_emision`.** Tests contra PostgreSQL: agrega el evento con motivo y responsable sin
  tocar otra fila (conteo de filas por tabla antes y después); motivo en blanco rechazado con el campo;
  la segunda anulación se rechaza siempre con `Conflicto("emision_id")`, mismo o distinto
  motivo, y sigue habiendo un solo evento (R17); `emision_id` inexistente y de otra administración dan `NoEncontrado` sin insertar (QA-3);
  el libro es autoridad de anulada para el saldo; comprobar que `anular_emision` no agrega una
  auditoría duplicada. La composición con auditoría y estado de liquidación lo prueba el 7, fuera
  del 4b (AR-5). El estado de la cuenta vuelve al de antes de emitir, y re-emitir el período imputa el pago devuelto. RED contra la función vacía.
  Escenarios: `libro-de-movimientos` › Anular deja la deuda como antes de emitir; › Anular sin motivo; ›
  Anular dos veces; `imputacion-de-creditos` › Un pago imputado a una emisión que se anula vuelve como
  crédito (contra la base). Lecciones: L-034.
  Escenarios adicionales (RC-09): `libro-de-movimientos` › Anular una emisión inexistente; › `libro-de-movimientos` › Anular una emisión de otra administración.

- [x] 3.4 **`registrar_credito`.** Tests contra PostgreSQL: bloquea la cuenta, corre `imputar_pendientes`
  e imputa con R04 o con su destino fijo; el mismo `operacion_id` dos veces, un movimiento y un juego de
  imputaciones; con otro importe, `Conflicto("operacion_id")`; `correccion` y `saldo_inicial` rechazados
  como tipo; destino fijo sin destino rechazado con `EntradaInvalida("destino")`;
  cero/negativo con `EntradaInvalida("importe")`; cuenta inexistente y de otra administración con
  `NoEncontrado` (QA-3, QA-10); destino fijo insuficiente con el error de E16. Primero buscar por
  `operacion_id`, luego validar: replay no vuelve a imputar aunque entre ambas llamadas se anule una
  emisión. Comparar `cuenta_id`, `tipo`, sentido, `destino` (obligación y componente), importe,
  `fecha_valor`, motivo normalizado y `complejo_id`; excluir `request_id` y `registrado_por`. Reusar
  operación con cuenta, tipo o destino diferentes da `Conflicto("operacion_id")` (QA-9). El ejemplo de R04 y el pago mayor que la deuda, contra la
  base. RED contra la función vacía. Mutante: imputar antes de bloquear (lo ve 3.6). Escenarios:
  `imputacion-de-creditos` › El ejemplo de R04 (contra la base); › Pago mayor que la deuda;
  `libro-de-movimientos` › El mismo crédito dos veces; › Registrar crédito en cuenta inexistente;
  › Registrar crédito en cuenta de otra administración. Lecciones: L-017, L-034.
- [x] 3.5 **`corregir`.** Tests contra PostgreSQL: contra-asiento de un pago (la cuenta vuelve a deber, los
  dos quedan, la corrección referencia); de un interés ya cubierto (el exceso vuelve como crédito);
  segunda corrección del mismo movimiento y de un movimiento de una emisión
  anulada dan `Conflicto("movimiento_id")`; un crédito de corrección equivocado ($50.000 en vez de
  $5.000) admite un contra-asiento total una sola vez; se permite también corregir el contra-asiento crédito de un interés, pero no un débito
  de corrección ni un débito libre (E6); crédito de corrección y crédito particular de R14 imputados con R04, incluyendo deuda
  más vieja que la obligación referenciada para distinguir el orden (AN-10); importe cero o
  negativo, y motivo en blanco o mayor de 500 caracteres, rechazados con el campo; observar
  responsable y fecha del registro (AN-08). `obligacion_id` inexistente o de otra administración y
  recurso de otro edificio de la misma administración dan `NoEncontrado`; obligación de emisión anulada
  da conflicto (QA-3, AN-09). Idempotencia: repetir el contra-asiento con el mismo `operacion_id`
  devuelve el mismo id antes del chequeo ya tiene corrección, sin otra auditoría ni imputación; probar
  cambios de motivo normalizado, recurso y edificio de ruta. Árbitro explícito
  `ON CONFLICT (administracion_id, operacion_id) WHERE operacion_id IS NOT NULL DO NOTHING`; mutante
  sin chequeo ya tiene corrección: la segunda operación distinta sigue dando `23505` de `corrige_a`
  traducido a `Conflicto("movimiento_id")`, nunca vacío ni 201. Un segundo mutante sin árbitro debe
  hacer caer esa misma aserción (BE-2). Traducción de IntegrityError en `begin_nested`, como complejos:
  después de 409, la transacción externa permite un SELECT, sin `25P02` (BE-5.1). RED contra la
  función vacía. Escenarios: `correccion-de-movimientos` › Corregir un pago registrado de más; › Corregir
  dos veces el mismo movimiento; › Corregir una corrección; › Un cargo cobrado de más; › Importe que no es
  positivo; › Corrección sin motivo; › Responsable y fecha observables; › Replay antes de validar si ya está
  corregido; › Único de corrección aunque falte el chequeo previo. Lecciones: L-007, L-034.
  Empate de E7 contra PostgreSQL: dos créditos pendientes se imputan en la misma transacción
  mediante `imputar_pendientes`, con intereses anticipados de cortes distintos I1 $4.000 e I2
  $6.000 en la fixture y `registrada_en` iguales; corregir I1 devuelve el exceso según la secuencia.
  No insertar imputaciones manualmente. Repetir 20 veces con ids distintos y atribución estable;
  mutante que desempata con `now()`/UUID da rojo.
  RC-04: ejecutar el caso **Crédito retroactivo con imputación posterior**, paso a paso como D8:
  obligación octubre $40.000 e I1/I2 $4.000/$6.000; registrar B $6.000 el 15/10 con fecha valor 15/10,
  A $4.000 el 16/10 con fecha valor 1/9, contra-asentar I1 el 17/10. Antes de cada crédito no hay
  sobrante pendiente; B tiene orden 1 y A orden 2. Después, B conserva $6.000 imputados y $0 a favor,
  A queda con $0 imputados y $4.000 a favor, capital $40.000; mutante que ordena por fecha valor de
  crédito deja A aplicado y devuelve $4.000 de B: rojo en la atribución por crédito, no sólo el total.
  El flujo usa `registrar_credito` y `corregir`, con la fecha de registro controlada; sólo las filas
  anticipadas de interés vienen de fixture del 4c. No confundir fecha valor con fecha de registro.
  RC-12: probar sentido igual al blanco y débito de corrección rechazados por aplicación bajo candado,
  aunque el esquema admita tales blancos; después de I/C1/C2, un nuevo contra-asiento de I con otra
  operación da `Conflicto("movimiento_id")`. Mutantes que quitan cada validación deben fallar en su
  aserción, conservando FK/únicos; para sentido igual el test exige rechazo antes del INSERT.
  Escenarios adicionales (RC-09): `correccion-de-movimientos` › Contra-asiento de un interés cubierto; › `correccion-de-movimientos` › Corregir el crédito que contra-asentó un interés; › `correccion-de-movimientos` › Contra-asiento de un débito de corrección; › `correccion-de-movimientos` › Contra-asiento sobre emisión anulada; › `correccion-de-movimientos` › Crédito sobre obligación que no cuenta; › `correccion-de-movimientos` › Obligación inexistente; › `correccion-de-movimientos` › Obligación de otra administración; › `correccion-de-movimientos` › Replay con otros datos de negocio; › `correccion-de-movimientos` › Error de base con transacción recuperable; › `correccion-de-movimientos` › El original restaurado no se contra-asienta otra vez; › `correccion-de-movimientos` › Corrección con el mismo sentido que su blanco.

- [x] 3.6 **Concurrencia contra PostgreSQL real.** Con dos conexiones y barreras en los puntos de decisión: dos pagos de $60.000
  a la vez sobre $100.000 de deuda (deuda cero, $20.000 a favor, imputaciones suman $100.000); dos
  emisiones del mismo período (una pasa, la otra `Conflicto("periodo")` por el único de `intento`); una
  emisión de diez cuentas de $40.000 cada una y un pago de $40.000 de una de ellas desde deuda cero,
  en ambos órdenes, dejan esa cuenta con deuda/favor cero e imputaciones de $40.000; dos emisiones con
  unidades NUEVAS A/B en orden cruzado, en el mismo edificio pero en **períodos distintos**
  (octubre y noviembre), crean cuentas ordenadas por `unidad_id` en una sentencia y candados en la
  misma transacción; ambas emisiones tienen éxito sin `40P01`. Mutante: crear las cuentas en orden
  cruzado A/B y B/A con barreras tras la primera inserción; debe caer en el éxito de ambas por
  deadlock, sin que el único de emisión del mismo período tape el defecto (RC-03);
  pagos en dos cuentas distintas con una demorada antes de confirmar: la otra confirma sin esperarla;
  candado borrado antes de dos pagos simultáneos. Pagos: barrera entre leer el estado e
  imputar (no antes de empezar); con candado real, la instrumentación no exige que ambas conexiones
  entren a una barrera que el propio candado serializa. Emisiones: barrera tras leer intentos/calcular
  el paso 2; mutante que quita sólo el único de intento deja entrar ambas y cae la aserción de una
  sola emisión activa (QA-5). Borrado intercalado: como rol de arranque borrar el candado después del
  INSERT y antes del FOR UPDATE; se exige `CandadoIncompleto` con tantas filas como ids, sin escribir
  plata. Mutante que omite el chequeo de cantidad da rojo (QA-6). App no puede borrar el candado,
  verificado con `42501`, y las transacciones de prueba tienen corte del lado de PostgreSQL (L-011). RED: con `bloquear_cuentas` reemplazado por un no-op en
  una copia, el de dos pagos da rojo en la suma de imputaciones (no por un error de otra cosa, L-034).
  Escenarios: `imputacion-de-creditos` › Dos pagos simultáneos; › Una emisión y un pago a la vez; ›
  Cuentas distintas no se esperan; `libro-de-movimientos` › Dos emisiones simultáneas del mismo período;
  `aislamiento-por-administracion` › Un candado borrado no abre un hueco; › Borrado entre insertar y bloquear; `imputacion-de-creditos` ›
  Emisiones con unidades nuevas cruzadas. Lecciones: L-011, L-020, L-034.
- [x] 3.7 **Lecturas.** `estado_de_cuenta`, `deuda_del_edificio` y `saldo_anterior`. Tests contra
  PostgreSQL: lecturas con una sola sentencia SQL (CTEs) y por tanto una sola snapshot en READ
  COMMITTED; una escritura concurrente no produce mezcla de movimientos e imputaciones (BE-6).
  Para edificio, partir de `cuenta` con JOIN o `= ANY(ids)`; nunca filtrar sólo por `complejo_id`
  sobre las tablas grandes. Cargar exactamente 3 administraciones, 100 edificios por administración,
  20 cuentas por edificio, 12 obligaciones y 12 movimientos por cuenta y 24 imputaciones por cuenta:
  6.000 cuentas, 72.000 obligaciones, 72.000 movimientos y 144.000 imputaciones. Distribuir por cuenta
  y edificio; ejecutar `ANALYZE cuenta, obligacion, movimiento, imputacion` antes de capturar los planes.
  Este volumen selectivo evita planes de tabla chica, sin forzar opciones del planificador. Fijar
  `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` como app con tenant: el test rechaza `Seq Scan` y
  `Parallel Seq Scan` sobre `obligacion`, `movimiento` e `imputacion` (DB-2), sin desactivar seqscan
  para fabricar el verde. Capturar también EXPLAIN de `estado_de_cuenta(cuenta_id)` sin edificio,
  sobre ese mismo volumen y después de ANALYZE, exigiendo acceso por administración/cuenta y sin
  barrido completo de las tres tablas; conservar `movimiento(administracion_id,cuenta_id)` y nombrar
  esa consulta (RC-15). Verificar campos `credito_a_favor`, `credito_a_favor_aplicable` y
  `credito_a_favor_retenido` en ambas lecturas para la bonificación retenida de $2.000 y deuda
  diciembre $40.000 (RC-13), sin construir pantalla. Mutante de consulta que abandona el acceso por cuenta debe caer en el plan.
  La deuda del edificio coincide, cuenta por cuenta, con `estado_de_cuenta`; saldo anterior de
  abril con marzo impago y de mayo con marzo pagado; saldo anterior con deuda cero y crédito a favor, excluyendo la emisión pedida según D12;
  distinguir el snapshot devuelto en `EmisionRegistrada` de la lectura actual después de pagar
  (AN-06); guardarlo en el documento publicado lo prueba el 7, no el 4b;
  ninguna lectura escribe (conteos); B no ve el edificio
  de A (cero filas, nunca un error). RED contra funciones vacías. Escenarios: `libro-de-movimientos` ›
  Deuda de un edificio; › Saldo anterior sin débito nuevo (contra la base); › Pagar marzo lo saca del saldo
  anterior (contra la base); › Saldo anterior con crédito a favor; › Lectura durante una confirmación;
  › Plan del edificio con datos de varios edificios. Lecciones: L-016, L-034.
  Escenarios adicionales (RC-09): `libro-de-movimientos` › Plan de una cuenta sin filtro de edificio.

## 4. Fronteras, permiso y ruta de corrección (design D9 a D11)

- [ ] 4.1 **El SQL de cada módulo sólo nombra sus tablas.** Test nuevo en `test_fronteras_de_modulos.py`
  insensible a mayúsculas con el mapa tabla → módulo (`administracion` de `acceso`) y las tres excepciones de E11, cada una con su
  motivo. También escanear `proptech_api` y `proptech_worker`: no pueden nombrar en SQL las
  seis tablas del libro ni `candado_de_cuenta`, deben llamar aplicación (AR-4). Excluir sintaxis
  `FOR UPDATE OF` y funciones en FROM como `unnest` y `generate_series`, con casos positivos que
  prueban que siguen detectándose tablas reales (QA-8). RED: sin las excepciones, el árbol real da rojo nombrando `escritura.py`, `lectura.py` y
  `ejemplo.py` con sus tablas, y nada más (si aparece otra, se trae al orquestador, L-030). Mutantes en
  copia: `liquidacion/aplicacion/` con `FROM movimiento`; `cuenta_corriente/aplicacion/` con `JOIN unidad`;
  una tabla que no está en el mapa; `from movimiento` minúscula desde API y worker, cada uno
  rojo en la regla de composición. Escenarios: `fronteras-de-modulos` › El código de hoy pasa con sus
  excepciones; › La liquidación nombra una tabla del libro; › La cuenta corriente nombra una tabla de
  complejos; › Sin la excepción de lectura; › Una tabla sin dueño declarado; › SQL del libro fuera del módulo; › OF y funciones no son tablas. Lecciones: L-013, L-022,
  L-029.
- [ ] 4.2 **Permiso `corregir_movimiento`, migración `0024` y auditoría de la corrección.**
  **Recibe de la 1.4 (F1-04)**: el ciclo `pg_dump` hasta `0024` y vuelta, que bajar `0024` con una
  corrección auditada dé `23503` y volver a subir a `0024` con revisión y conteos. `Accion` y
  `_MATRIZ` (`{_SA, _AP}`); `0024` con el literal; modelo de detalle `extra="forbid"` sin motivo ni
  importe; `corregir` registra en la misma transacción y no repite en la idempotencia. Tests: la fila de la
  matriz para los nueve perfiles; el vocabulario contiene el valor; la fila de auditoría y su detalle; una
  auditoría que falla deja el libro sin la corrección ni sus imputaciones. Este caso va por
  la API real, que es quien confirma: hacer fallar `registrar`, recibir 500 y leer desde otra conexión
  que no queda corrección ni imputaciones; no fabricar el resultado con rollback del test (QA-11). RED: sin la fila, SA y AP dan
  `False`; sin `0024`, `registrar` choca con la FK (rojo en la aserción de la fila de auditoría, no en el
  arranque). Escenarios: `autorizacion-por-rol` › La fila de la matriz; `auditoria-de-acciones` ›
  Corrección auditada; › Falla la auditoría; › El vocabulario nuevo. Lecciones: L-007, L-034.
- [ ] 4.3 **Ruta `POST /api/complejos/{complejo_id}/correcciones` y su contrato.** Router
  `proptech_api/cuenta_corriente.py`, `proptech_api/errores.py` con las formas declaradas (incluidos 500 y 503) y
  `RESPUESTAS_DE_ERROR`, manejador de los errores del libro. Tests contra la app real: 401 sin identidad
  sin tocar la base; 404 para un movimiento de otra administración igual que para uno inexistente (misma
  respuesta, L-017), y caso separado de otro edificio dentro de la misma administración para movimiento
  y obligación; 403 para el administrador por edificio con `corregir_movimiento`; 201 para SA y AP;
  422 por campo de más y por `"10.005"`, sin repetir el valor; 409 por `operacion_id` con otro motivo;
  repetición idempotente del contra-asiento 201 con el mismo id; motivo de 1 y 500 caracteres
  válido, vacío/501 inválido; UUID real de texto aceptado mediante `Field(strict=False)` y negativos
  rechazados por el modelo del cuerpo; `forma="debito"` rechazada con 422. Fijar el orden de errores
  401 / 422 cuerpo / 404 edificio / 403 permiso / replay / 404 recurso nuevo / 409-422 dominio.
  RC-07: operación ya usada con otro `movimiento_id` u `obligacion_id` inexistente da **409
  operacion_id**, no 404, sin nueva auditoría/imputación; con operación nueva sí da 404. Mutante que
  busca recurso antes del replay cae en esa aserción. El mismo orden rige con recurso ajeno (BE-7, BE-8); el OpenAPI declara 201, 401, 403, 404, 409, 422, 500 y 503 con sus
  esquemas; la ruta está en el barrido. Casos de SQLSTATE en SAVEPOINT: 23505 por nombre de constraint
  a 409 con su campo; 23503 a 404; 23514 y 42501 a 500 `{"error":"interno","request_id":...}`;
  40P01/40001 a 503 declarado, sin retry automático. No filtrar DETAIL ni valores a respuesta o logs;
  tras el error traducido, probar que la transacción exterior no queda abortada (BE-1, BE-5.1). RED: la ruta sin `responses=` da rojo en el test del OpenAPI; sin
  el chequeo de permiso, el de 403 da rojo en el código de estado. Escenarios:
  `correccion-de-movimientos` › Administrador por edificio; › Movimiento de otro edificio; › Super admin
  corrige; › El OpenAPI declara todas las respuestas; › Sin identidad; › Cuerpo con un campo de más; ›
  Importe con decimales de más; › La misma corrección dos veces; › El mismo `operacion_id` con otro motivo;
  `autorizacion-por-rol` › La ruta nueva está en el barrido. Lecciones: L-007, L-017, L-027, L-034.
  Escenarios adicionales (RC-09): `correccion-de-movimientos` › El OpenAPI declara las respuestas de error; › `correccion-de-movimientos` › Movimiento de otra administración; › `correccion-de-movimientos` › Obligación de otro edificio de la misma administración; › `correccion-de-movimientos` › Motivo de longitud inválida; › `correccion-de-movimientos` › Errores internos y transitorios declarados; › `correccion-de-movimientos` › Un usuario sin permiso no averigua si existe el recurso; › `correccion-de-movimientos` › UUID de texto y montos no positivos; › `correccion-de-movimientos` › Traducción de clave foránea y único desconocido; › `correccion-de-movimientos` › Replay cambiado con recurso inexistente.

## 5. Deuda del 4a (design D13)

- [ ] 5.1 **RB-7 y QA-6, QA-7, QA-9, QA-12, QA-14.** RB-7: `Dinero("1.00")` bajo un `localcontext` con
  `prec=2` no levanta `InvalidOperation` (RED con el constructor de hoy). Para cada QA: buscar el test del
  4a que lo cubre y anotarlo con su ruta y nombre; exista o se escriba ahora, verlo fallar con
  su mutante específico, pegar comando, salida, hora y aserción fallida; encontrarlo no cierra el ítem
  (QA-15, L-035). Mutantes (QA-6: `scaleb` contra `10 ** -exp` con `1E+2`; QA-7: aritmética bajo un contexto ajeno;
  QA-9: SQLSTATE del `UPDATE` del umbral y el borde `0.00` del `CHECK`; QA-12: el modelo de detalle del
  padrón rechaza un campo de más; QA-14: migración de prueba que hace algo antes de un `ALTER` sobre una
  tabla protegida falla con `must be owner` sin dejar nada a medias). Lo que no entre en medio día se
  anota como deuda con dueño propuesto, nunca se marca hecho. Lecciones: L-012, L-019, L-035.

## 6. Cierre

- [ ] 6.1 **Corrida de cierre después de la última vuelta.** Sobre el último commit del change, con el SHA
  anotado (`git rev-parse HEAD`): antes del merge, `git fetch origin` y comparar
  `backend/migraciones/versions/` con `origin/main`; si ya hay `0023` o posteriores ajenas, quien
  mergea segundo renumera `revision` y reencadena `down_revision`, actualiza ensayo y fixtures y repite
  la suite completa. Si falla fetch, no se afirma que no hay choque. Revisar coordinación con 3c en
  `unidades.py`, `grupos.py` (auditoría), `_edificios.py`, tipos y fixtures web; resolver por alcance
  firmado sin pisar cambios ajenos. Después de esa conciliación y del último commit: `bash infra/ci/test-backend.sh` **completo** (no por grupo, L-041), con el
  número de tests comparado con el de `main` en `84badd1` (el último número publicado del 4a es 2843 + 1 xfailed, CI de `6f6fe6b`,
  D-119; si bajó, explicar); `bash infra/ci/test-web.sh` y `bash infra/ci/test-web-navegador.sh` (la web no cambia,
  pero se corre igual); `bash infra/ci/humo.sh`; el ensayo de roles de 1.4 repetido sobre este SHA si el
  código cambió después. Push de la rama `change/libro-de-movimientos` (nunca a `main`), y como el CI no
  corre en una rama sin PR (L-042): `gh run list --commit <sha>`; si está vacío, `gh workflow run CI --ref
  change/libro-de-movimientos` y `gh run view <id> --json headSha,conclusion,jobs` leído en verde **sobre
  ese mismo SHA**, con los cinco jobs. Si el código cambia después, la corrida queda vencida y se repite
  entera (L-010, L-031, L-037). Lecciones: L-003, L-010, L-031, L-037, L-041, L-042, L-043.

## Workflow follow-up

- Revisión del propose por los roles que convoque el orquestador (arquitecto, backend, DBA, QA y el piso
  de plata), en directorios separados (L-045), y firma de la sección "Aprobación".
- **Compromisos fuera del 4b (RC-09): lo prueba el 7**, con sus funciones reales: escenario
  "Anulación y auditoría del llamador", evento del libro y `ANULAR_LIQUIDACION` en la misma
  transacción, estado anulada derivado del libro y sin duplicación. También guarda el snapshot de
  `saldo_anterior` devuelto por el 4b y verifica que el documento publicado no cambia tras un pago.
  Se retiraron estos MUST y el escenario de auditoría de las specs del 4b; D9/D12 y el Knowledge
  Base Impact mantienen el contrato para sus fichas. **Lo prueba el 8**: acciones reales de pago,
  reversión y reimputación, incluida reversión de bonificación retenida. **Lo prueba el 11**: mostrar
  al vecino los créditos aplicable y retenido separados. El 4b verifica sólo su API de aplicación,
  tipos anticipados y campos de lectura; no acredita esos flujos futuros.
- Romper y auditar (ciclo completo, `14_forma_de_trabajo.md`); rompedor y auditor de una familia de
  modelo distinta del constructor (L-025). Para el rompedor, la lista de la ficha 4 ("Que intente romper").
- Archivar con el OK del auditor y actualizar `knowledge-base/` según "Knowledge Base Impact" de
  `proposal.md` (decisiones nuevas sólo se agregan).

## Registro de esta corrección documental (26/10/2026)

**JUICIO (coordinador de correcciones, confianza alta)**: el alcance es el brief
`/home/juanisarmiento/.claude/jobs/f3e370f0/tmp/correcciones-4b.md`, comparado contra los seis informes
completos de `.git/informes-libro-de-movimientos/`. Se corrigieron artefactos, no se ejecutaron estas
19 tareas ni se emitió una aprobación nueva. Ninguna casilla ni firma se completa.

Despacho: un constructor coordinó `proposal.md`, `design.md` y `10_preguntas_abiertas.md`; en paralelo,
un constructor recibió sólo los siete `specs/*/spec.md` y otro sólo este `tasks.md`. Después de ambos
retornos, el coordinador integró consistencia, incluyendo el caso AN-02 de devolución parcial y las
cadenas de E6. Son constructores de documentos de una misma familia, no revisores independientes.

El orquestador informó que corrió `active-stack roles --json` antes de editar, con `files=[]`;
backend, DBA, frontend, DevOps y QA no se convocaron en una ronda nueva por diff vacío inicial;
arquitecto y analista devolvieron `not-decided-by-diff`. Aquí se aplican sus informes ya existentes,
sin atribuirles aprobación de los textos corregidos. No se volvió a convocar auditor, senior ni
rompedor: no es verify del código ni otra ronda de revisión, es la corrección solicitada del propose.
La validación estructural final se informa con comando y hora en la entrega del commit.

Trazabilidad de decisiones y notas incorporadas:

| fuente | destino de la corrección |
|---|---|
| AR-1, AR-2, AN-04 | D1, E10/E14/E15; 1.2/1.3; specs de vocabulario y REFERENCES |
| DB-1, DB-9 | D1 lista exhaustiva, NOT NULL y par nulo; 1.2 B/D/E/F y coherencia período/edificio |
| DB-2, BE-6 | D12, E12, 3.7; snapshot de una sentencia y EXPLAIN vía cuenta |
| DB-3/4/10/11, QA-5/6/7/14 | D2/D4, 3.1/3.2/3.6; orden de creación, READ COMMITTED y barreras |
| BE-1/2/3/5, QA-9 | D3/D5/D10, E4/E9, 3.4/3.5/4.3; árbitros, SAVEPOINT y errores |
| AN-01/02/03, QA-4 | D6/D7/D8, E6/E7/E16, 2.1/2.3/3.5; destinos y correcciones |
| QA-1/2/3 | 1.1/2.2/3.3/3.4/4.3 y specs; privilegios vs trigger, propiedades, ids ajenos |
| AR-3/4/5/6/7, DB-5/6/7/8 | D0/D1/D5/D9/D11, riesgos; P52/P53/P54; 1.4; índices con consulta |
| AN-05/06/07/08/09/10/11/12/13 | actores, importes y escenarios en specs; D7/D12; R14, P53/A-4; Knowledge Base Impact |
| BE-4/7/8, QA-8/10/11/12/13/15/16/17 | 1.2/1.4/2.2/4.1/4.2/4.3/5.1 y specs; SQL scanner, borde, auditoría por API y mutantes |
| Auditor: 3c y KB Impact | riesgos, 6.1 fetch/renumeración, proposal: secciones exactas de 04 y APPEND 09/15 |

No hay notas descartadas. Los comportamientos nuevos quedan propuestos y sin firma; E6/E7/E16
siguen a validar con Alberto (A-4/P42), sin inventar una regla R42 ni una decisión humana D-121.

## Registro de la segunda corrección documental (26/10/2026)

**EVIDENCIA (orquestador, informado al constructor)**: `openspec list --json` encontró sólo
`libro-de-movimientos`, 0/19 tareas; `openspec status --change libro-de-movimientos --json` devolvió
proposal/specs/design/tasks `done`; `git status --short` vacío y `git rev-parse HEAD` devolvió
`4d94532b188aac96fa3f7d9144c22b31d225a368`. Baseline comunicado con hora
2026-10-26T17:47:19-03:00: `openspec validate libro-de-movimientos --strict` ->
`Change 'libro-de-movimientos' is valid`. No son pruebas ejecutadas de las tareas de construcción.

**EVIDENCIA (orquestador, antes del despacho)**: `active-stack roles --json` devolvió `files=[]`;
DBA `no-schema`, backend `no-endpoint`, frontend `no-ui-tree`, DevOps `no-deploy`, QA
`nothing-to-review`, arquitecto y analista `not-decided-by-diff`. El registro de la conversación
conserva el orden del comando antes del despacho; la hora exacta de ese comando no se recuperó.

**JUICIO (orquestador, confianza alta, alcance comparado contra el brief v2)**: se despachó un único
constructor para `proposal.md`, `design.md`, `tasks.md` y los siete `specs/*/spec.md`, con RC-01 a
RC-15 y fuentes 01 a 07 de `.git/informes-libro-de-movimientos/`. No hubo trabajos paralelos. Los
roles de capa, arquitecto, analista, rompedor, senior y auditor no se volvieron a convocar: este
encargo corrige documentos a partir de sus informes existentes, sin pedir firma, aprobación o
cierre. La ausencia de una revisión nueva no acredita estos textos como aprobados. La lista del
comando refleja el árbol limpio inicial, no una evaluación del alcance financiero propuesto.

**SUPUESTO (identidad de modelo no acreditada por despacho)**: constructor en Codex/OpenAI de la
misma familia disponible en la sesión; no se dispuso de los modelos Opus/Sonnet nombrados por las
instrucciones. No se afirma equivalencia ni independencia entre proveedores. Fuentes leídas:
ambos briefs, informes 01 a 07, skill `openspec-propose`, contexto/config de OpenSpec, CHANGES,
ficha 4, lecciones completas en `knowledge-base/15_lecciones.md`, D1 de `4823515`, artefactos
actuales y las zonas de permisos de `roles.py`. El brief dictó las correcciones; no es una revisión
independiente ni un ciclo TDD. No se construyó código ni se completaron tareas o firmas.


**EVIDENCIA (constructor documental, 2026-10-26T17:55:39-03:00)**:
`python3 /tmp/verificar_4b_v2.py` -> `125 escenarios; 0 sin tarea dentro de las 19 tareas;
19/19 pendientes; 16/16 elecciones sin firmar; firmante vacío`; `0 frases genéricas; 0 em dashes;
10 artefactos modificados; 0 archivos ajenos o nuevos`. El script coteja títulos normalizando
saltos de línea sólo dentro de las tareas, excluyendo Workflow follow-up y los registros históricos.
`openspec validate libro-de-movimientos --strict` -> `Change 'libro-de-movimientos' is valid`;
`git diff --check` -> sin salida, exit 0 (2026-10-26T17:55:40-03:00).
`git rev-parse HEAD` -> `4d94532b188aac96fa3f7d9144c22b31d225a368`; cambios sólo en el árbol,
sin commit ni push. Estas verificaciones documentales no prueban el comportamiento propuesto de la
futura implementación ni sustituyen la revisión de especialistas y la firma humana.


## Registro del apply, fases 1 a 3 (26/10/2026)

Constructor: Claude (Opus), en la sesión de Juani, con la tabla de Aprobación firmada por él
(commit `891ac38`). La fase 1 la empezó Codex (sin cuota a mitad); su trabajo se revisó contra la
auditoría `.git/informes-libro-de-movimientos/10-dba-fase1-parcial.md` y se completó. Rojos,
verdes y mutantes, con comando y salida, en `.git/4b-fase1-logs/` (los de Codex) y
`.git/4b-fase1-logs/claude/` (los de esta construcción).

- 1.4: `PROPTECH_COMPOSE_PROYECTO=proptech-ensayo-4b bash infra/ci/ensayo-roles.sh` (26/10/2026
  20:32 -03) terminó en `ENSAYO ROLES OK: respaldo restaurado, 10 asignaciones, ciclo
  0023/0016/0023 y origen intacto` y `ESQUEMA RESTAURADO: diff vacío entre esquema_antes.sql y
  esquema_downgrade.sql` (dumps conservados en `.git/informes-login-bloque-a/3.3-M07Rc9/`). El
  rojo del script viejo (`must be owner of table cuenta`) es el de Codex,
  `.git/4b-fase1-logs/ensayo-red.log`. El diff de forma en `0022` lo hace `test_libro_rollback.py`; el
  ensayo lo hace en `0016`, que es su punto de bajada. Lo que depende de `0024` pasó a la 4.2 (F1-04).
- Desvíos con su porqué:
  - `0023` suma FK directas a `complejo` en `evento_de_emision`, `obligacion`, `movimiento` e
    `imputacion`: la regla de catálogo de D5 (`test_catalogo_rls`) las exige y no se pueden agregar
    después de `roles despues` (DB-5).
  - La sonda de `roles despues` compara el mensaje por prefijo (`startswith(mensaje)`), no por
    subcadena ni con la operación: `emision no admite` está dentro de `evento_de_emision no admite`
    (QA-15) y la sonda heredada pedía la operación, que rompía la fijación de
    `test_roles_solo_agregar`.
  - `antes()` le da al candado `SELECT, INSERT, UPDATE` (sin DELETE) también en un segundo deploy
    (F1-06); la `0023` revoca DELETE después de `aislar_por_administracion` (F1-01).
  - El libro no nombra `unidad` ni `complejo` en su SQL (E11): la unidad o el edificio ajenos los
    rechaza la FK compuesta, traducida a `NoEncontrado` dentro de un SAVEPOINT.
  - "Hoy" de la corrección: `complejos.hoy_en_mendoza` no se puede importar (D0); el libro repite la
    regla (Mendoza, instante con zona) con un `reloj` inyectable.
  - El criterio del plan de 3.7 exige además que el índice usado sobre las tablas grandes tenga
    `cuenta_id` en su condición: con tres administraciones el prefijo de la RLS solo no aparece como
    `Seq Scan` y el mutante "sin acceso por cuenta" sobrevivía.
- Pendiente dentro de lo construido (no bloquea las fases 1 a 3, se anota para el rompedor):
  - 3.5 no audita: la auditoría y el permiso `corregir_movimiento` son de la 4.2.
  - 3.6: el mutante que quita sólo el único de `intento` no se corrió (el único es del arranque).
  - 3.1: la coincidencia de tenant se prueba en `exigir_identidad` y en `registrar_emision`; el
    mutante que la quita no se corrió por función.
  - F1-09 y F1-10 de la auditoría quedan como notas (listas paralelas en `roles.py` y en el ensayo;
    `test_unicos` sin `constraint_name`).

## Registro de los arreglos tras rompedor y auditor (26/10/2026)

Informes: `.git/informes-libro-de-movimientos/11-rompedor-fases-1-3.md` (RB4B-) y
`12-auditor-fases-1-3.md`. Constructor: Claude (Opus), en la sesión de Juani; la enmienda E7 la firmó
Juani (`a4e0ded`). Cada rojo y cada mutante guarda la línea de comando, la hora y la línea `E` que
falló en `.git/4b-fase1-logs/claude-arreglos/` (`correr.sh` para los rojos, `mutantes.py` para los
mutantes; resumen en `mutantes-resumen.log`). Los mutantes restauran el archivo desde memoria.

- **El orden TDD se rompió en la construcción de las fases 2 y 3**: `estado.py` y la capa de
  aplicación de la sección 3 se escribieron antes que sus tests y el rojo se vio después, contra
  stubs. El auditor encontró que eso invalidó rojos: los 15 de `test_cc_correcciones` caían en el
  helper `emitir` (`NoResultFound`) porque el stub de emisión no escribía, y en 2.2/2.3 había tres
  `KeyError` y dos tests que nunca se vieron en rojo. Se rehízo así:
  - 3.5: stub sólo de `corregir` (emisión y créditos reales), `mut-stub_corregir_vacio.log`: los 21
    tests caen en su aserción o en `DID NOT RAISE` (dos lecturas pasaron a `one_or_none` para que el
    rojo no sea `NoResultFound`).
  - 2.2/2.3: stub de cálculo ingenuo (capital sin débitos, sin imputaciones, todo cuenta),
    `mut-stub_calcular_estado_ingenuo.log`: 17 caen en su aserción, ningún `KeyError`. Los 6 que el
    ingenuo deja pasar prueban el camino del capital solo; cada uno se vio en rojo con su mutante:
    `capital_sin_fondo`, `deuda_duplica_la_obligacion_vieja`, `saldo_anterior_sin_filtro`,
    `suma_sin_desborde`, `sin_tope_del_paso_3` (también tumba la propiedad sin exclusiones).
- **RB4B-01** (enmienda E7): tope por crédito en el paso 3 de D8 (`6be1b2f`). Rojo:
  `01-rb4b01-rojo.log` (unitarios, propiedades con el generador nuevo y los dos caminos contra
  PostgreSQL). Mutante `rb4b01_tope_solo_por_componente`.
- **RB4B-02**: `bloquear_cuentas` ejecuta siempre el `FOR UPDATE` (`2ec8572`). Rojo
  `02-rb4b02-rojo.log`; mutante `rb4b02_saltea_for_update_si_cache`.
- **RB4B-03**: pasos 3 y 4 de `registrar_emision` en un SAVEPOINT, y D3 dice qué obliga a deshacer
  (`9971c9a`). Rojo `03-rb4b03-rojo.log`; mutante `rb4b03_sin_savepoint`. Consecuencia escrita en D4:
  dos emisiones con cuentas cruzadas en la misma transacción dan `BloqueoFueraDeOrden` (RC2-01).
- **RB4B-05**: destino inexistente, ajeno o de otra cuenta es `NoEncontrado` antes de escribir; el
  replay de emisión devuelve el saldo anterior recalculado (`a8ed466`). Rojo `05-rb4b05-rojo.log`.
- **RB4B-04**, sobrevivientes del rompedor, cada uno con su test y su mutante en rojo: las tres
  funciones sin `exigir_identidad` (mueren con el 42501 de la RLS, que es justamente el defecto),
  replay sin destino, pago con destino, crédito de corrección y cuenta de otro edificio, contra-asiento
  sin pendientes, fecha en UTC, movimiento de emisión anulada, y RB6 (ajuste enlazado fuera de la
  cuenta: no cuenta, decidido en D8 paso 1). `pendientes_sin_tope_destino` era código muerto y se
  sacó: un crédito de destino fijo sólo tiene crédito a favor si una fila suya topó contra lo que se
  debe en su destino, y entonces el residual es cero y queda retenido.
- **Auditor**: las 4 FK directas a `complejo` caen en `test_el_esquema_real_no_tiene_ningun_problema`
  cuando se sacan (`mut-sin_fk_*.log`); son redundantes con las FK compuestas a `cuenta` y `emision`,
  por eso ningún test de `test_fk` las nombra. `lecturas.py` tiene seis mutantes, todos en rojo (el
  de "movimientos de todas las cuentas" sobrevivía y llevó a sumar el crédito a favor por cuenta al
  test de la deuda del edificio, y "edificio sin filtro" a un test nuevo). El mutante combinado de la
  3.5: `corr_sin_chequeo_previo` y `corr_sin_traduccion_de_corrige_a` sobreviven por separado porque
  se cubren entre sí (el chequeo previo y el único `uq_mov_corrige_a` traducido a
  `Conflicto("movimiento_id")`); juntos, el 23505 llega sin traducir.
- Notas F1 de la auditoría del DBA: F1-07 aceptada (la consulta que usa los tres índices los nombra
  en `lecturas.py` y el EXPLAIN de 3.7 lo verifica); F1-08 aceptada (nadie borra `persona`, `unidad`
  ni `complejo`; un change que los borre necesita el préstamo de D-115.3); F1-11 ya atendida
  (`DROP INDEX IF EXISTS` en el `finally`); F1-13 aceptada (la base de prueba tiene el dueño del
  compose); F1-15: `mypy` con comando y salida en `cierre-mypy.log`.
