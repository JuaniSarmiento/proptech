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

- [ ] 1.1 **Migración `0023`, parte A: `cuenta`, `candado_de_cuenta`, `emision`, `evento_de_emision`.**
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
- [ ] 1.2 **Migración `0023`, parte B: `tipo_de_movimiento`, `obligacion`, `movimiento`, `imputacion`.** Tests como en 1.1, más:
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
  administraciones, inválido. CHECK acotados para destinos conocidos, sin cerrar futuros tipos.
  `imputacion` lleva secuencia monótona de orden; ni `now()` ni UUID deciden E7. Cada índice restante
  nombra su consulta SQL y se elimina el que no sirve a ninguna (DB-6). Escenarios adicionales:
  `libro-de-movimientos` › Tipos anticipados válidos; › Enlace entre cuentas de la administración;
  › Los casos de NULL y cuenta ajena se rechazan; › Edificio y período coherentes;
  `imputacion-de-creditos` › Dos imputaciones con la misma fecha de registro (E7).
- [ ] 1.3 **Las seis tablas en la lista única; `roles despues` y el chequeo de arranque las cubren.**
  Sumar las seis a `compartido/tablas_protegidas.py` con su texto y sus tres triggers (D1 del 4a); cambiar `despues()` de `roles.py` para dar al migrador
  `GRANT REFERENCES` sobre las seis tablas del libro y `candado_de_cuenta` (E15, AR-1). Tests: `despues()` transfiere tablas y funciones y verifica por el efecto; la API y el
  worker no arrancan con `imputacion` del migrador; el test de catálogo da rojo si `movimiento` sale de la
  lista; `candado_de_cuenta` no está en la lista. **RB-4**: tabla homónima en otro esquema creada antes y
  después que la de `public`, y el mutante que saca `schemaname = 'public'` rojo en los dos órdenes.
  **QA-15**: función de bloqueo con otro dueño, y función con el texto de otra tabla, rojas en `despues()`.
  RED: sin las seis en la lista, el test de catálogo nombra cada una. Como migrador después del `roles despues` real, crear una tabla de prueba con FK a
  `movimiento`: RED sin el grant da `42501`, GREEN permite crearla; comprobar también REFERENCES en
  cada tabla del alcance. El grant no debe conferir ALTER, CREATE INDEX, DROP INDEX ni escritura del
  libro al migrador. Reversión del permiso: REVOKE. **Verde = la suite completa** de
  backend (L-041), con el número de tests antes y después. Escenarios: `aislamiento-por-administracion` ›
  El paso de roles verifica las seis por el efecto; › Una tabla del libro sin declarar; › La API no
  arranca con una tabla del libro del migrador; › Una tabla homónima en otro esquema no hace pasar el
  chequeo; › El candado no es de sólo agregar; › Tabla futura con FK al libro. Lecciones: L-016, L-018, L-022, L-036, L-041.
- [ ] 1.4 **Ensayo de roles y rollback, corridos.** `infra/ci/ensayo-roles.sh`: antes de bajar de `0023`,
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

- [ ] 2.1 **Orden de imputación y destinos fijos.** `dominio/imputacion.py` con `Componente`,
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
- [ ] 2.2 **Estado de una cuenta: residual, crédito a favor y saldo anterior.** `dominio/estado.py` con
  `calcular_estado`. Tests, sin base: capital desglosado en tres componentes; residual nunca negativo;
  crédito a favor por crédito; deuda total sin duplicar la obligación vieja (R06); saldo anterior sin la
  emisión pedida, con y sin crédito a favor (semántica exacta de D12); el 7 debe guardar al emitir el
  valor calculado en esa transacción, que no se reconstruye con una lectura actual posterior. **Propiedad con `hypothesis`** (perfil `ci`): la invariante de D8 con un oráculo que suma
  débitos y créditos sin pasar por los componentes ni por `imputar`, y sin importar el
  predicado de exclusión de producción. Además de la identidad, exigir por componente residual ≥ 0 e
  imputado que cuenta ≤ debido, por crédito favor ≥ 0; con capital positivo, sin débitos adicionales y
  con una imputación positiva que cuenta, deuda < suma del capital (QA-2). Acotar generadores: hasta
  20 obligaciones y 20 créditos de hasta $1.000.000 cada uno, suma absoluta menor al máximo
  `999999999999.99`; probar aparte el límite y el desborde, que da `MontoInvalido` (QA-10). RED contra `calcular_estado` vacío.
  Mutantes separados: sin el tope del paso 3 de D8 (residual negativo después de corregir
  interés ya cubierto) e ignora imputaciones (no baja la deuda); registrar la aserción exacta que cae,
  no aceptar sólo la identidad como oráculo. Escenarios: `libro-de-movimientos` ›
  Capital desglosado; › Saldo anterior sin débito nuevo; › Pagar marzo lo saca del saldo anterior; `imputacion-de-creditos` › Imputaciones efectivas reducen
  deuda; › Tope luego de corregir el interés.
  Lecciones: L-019, L-034, L-035.
- [ ] 2.3 **Lo que no cuenta: emisión anulada, contra-asiento, ajuste enlazado y exceso.** Tests, sin
  base: anular deja la deuda como antes de emitir; el pago imputado a la emisión anulada vuelve como
  crédito; el ajuste que compensaba el interés anulado tampoco cuenta (D-085); el par corregido no cuenta y
  las imputaciones de otros créditos no se tocan; corregir un interés ya cubierto devuelve el exceso al
  crédito de la imputación más reciente a la más antigua (secuencia, E7). La propiedad de 2.2 extendida con anulaciones y correcciones aleatorias. RED contra
  la versión de 2.2 (sin exclusiones). Mutantes: exceso devuelto según fecha del crédito en vez de orden de la imputación (rojo en el
  escenario pago A / pago B de AN-02); ajuste enlazado que sigue contando (rojo en D-085). Incluir bonificación de $2.000 de
  noviembre, emisión anulada y diciembre $40.000: sigue atada al destino anulado y diciembre debe
  $40.000 hasta reversión por el 8 (E16); mutante que la reimputa por R04 da rojo. Pago con fecha valor
  anterior a una corrección posterior: pendientes se ordenan por `fecha_valor`, sin reescribir hechos
  anteriores (AN-12). Cadena de E6: interés I débito, C1 contra-asiento crédito y C2 contra-asiento
  débito de C1; el cálculo parte del extremo más reciente, excluye C2/C1 y restaura I. Mutante que
  excluye todos los pares sin resolver la cadena da rojo en el residual. Escenarios: `libro-de-movimientos` ›
  Anular deja la deuda como antes de emitir; › El ajuste que compensaba el interés anulado;
  `imputacion-de-creditos` › Un pago imputado a una emisión que se anula vuelve como crédito;
  `correccion-de-movimientos` › Las imputaciones de otros créditos no se rehacen. Lecciones: L-019,
  L-034.

## 3. Casos de uso sobre la base (design D2 a D5, D7, D8, D12)

- [ ] 3.1 **Cuenta de unidad y candado.** `aplicacion/cuentas.py`: `cuenta_de_unidad` (crea si falta,
  `ON CONFLICT (administracion_id, unidad_id) WHERE unidad_id IS NOT NULL DO NOTHING` y lee) y `bloquear_cuentas`. Tests contra PostgreSQL: dos pedidos, y dos
  transacciones simultáneas, devuelven la misma cuenta; una unidad de otro edificio da `NoEncontrado`;
  `bloquear_cuentas` sin una fila de candado la recrea; el candado nace en la misma transacción
  que la cuenta; rollback no deja ninguno de los dos. Todos los casos de uso fuera de transacción dan
  `RegistroFueraDeTransaccion`; `administracion_id` sale de `current_setting('app.administracion_id')`
  y, en las funciones que reciben identidad, se exige coincidencia antes del INSERT (BE-5.2-5). El llamador autoriza la acción y
  reúne todas las cuentas para llamar a `bloquear_cuentas` una sola vez por transacción. Chequear
  `current_setting('transaction_isolation') = 'read committed'`; en REPEATABLE READ, antes de escribir,
  `AislamientoNoAdmitido` (DB-4). Dos conexiones con snapshot vieja, barrera y pagos $60.000/$60.000
  sobre $100.000: sin chequeo la foto vieja permite imputar $120.000; el test registra ese
  resultado y exige el rechazo por aislamiento, de modo que el mutante cae en esa aserción; con chequeo
  la segunda rechaza y no escribe. Probar también READ COMMITTED exitoso, no sólo el rechazo. RED contra funciones que
  insertan sin `ON CONFLICT` (la segunda llamada falla con `23505` en vez de devolver el id). Escenarios:
  `libro-de-movimientos` › Pedir dos veces la cuenta de una unidad; `imputacion-de-creditos` ›
  REPEATABLE READ no usa una foto vieja; `aislamiento-por-administracion` › La app no borra candados. Lecciones: L-034.
- [ ] 3.2 **`registrar_emision`.** Tests contra PostgreSQL: registra emisión y obligaciones; la misma dos
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
- [ ] 3.3 **`anular_emision`.** Tests contra PostgreSQL: agrega el evento con motivo y responsable sin
  tocar otra fila (conteo de filas por tabla antes y después); motivo en blanco rechazado con el campo;
  la segunda anulación se rechaza siempre con `Conflicto("emision_id")`, mismo o distinto
  motivo, y sigue habiendo un solo evento (R17); `emision_id` inexistente y de otra administración dan `NoEncontrado` sin insertar (QA-3);
  el libro es autoridad de anulada para el saldo; el 7 debe derivar su estado o registrar su evento y
  auditoría en la misma transacción (AR-5). El estado de la cuenta vuelve al de antes de emitir, y re-emitir el período imputa el pago devuelto. RED contra la función vacía.
  Escenarios: `libro-de-movimientos` › Anular deja la deuda como antes de emitir; › Anular sin motivo; ›
  Anular dos veces; `imputacion-de-creditos` › Un pago imputado a una emisión que se anula vuelve como
  crédito (contra la base). Lecciones: L-034.
- [ ] 3.4 **`registrar_credito`.** Tests contra PostgreSQL: bloquea la cuenta, corre `imputar_pendientes`
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
- [ ] 3.5 **`corregir`.** Tests contra PostgreSQL: contra-asiento de un pago (la cuenta vuelve a deber, los
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
  Empate de E7 contra PostgreSQL: dos créditos a favor se imputan dentro de la misma emisión y
  comparten `registrada_en`; corregir el interés ya cubierto devuelve el exceso según la secuencia de
  `imputacion`, no UUID ni fecha del crédito. Repetir 20 veces con ids distintos y resultado estable;
  mutante que usa `now()`/UUID da rojo. Caso AN-02 con importes: pago A del 1/9 conserva $4.000 a
  favor, B del 15/10 cubre $6.000 del interés de octubre y el 1/11 se imputan los $4.000 de A al mismo
  interés de octubre de $10.000 (dos movimientos de cortes distintos: I1 $4.000 e I2 $6.000); al
  contra-asentar sólo I1 quedan $6.000 debidos, B conserva $6.000 imputados y A recupera $4.000.
  Verificar la atribución por crédito, no sólo el total
  devuelto (AN-02, QA-4).
- [ ] 3.6 **Concurrencia contra PostgreSQL real.** Con dos conexiones y barreras en los puntos de decisión: dos pagos de $60.000
  a la vez sobre $100.000 de deuda (deuda cero, $20.000 a favor, imputaciones suman $100.000); dos
  emisiones del mismo período (una pasa, la otra `Conflicto("periodo")` por el único de `intento`); una
  emisión de diez cuentas de $40.000 cada una y un pago de $40.000 de una de ellas desde deuda cero,
  en ambos órdenes, dejan esa cuenta con deuda/favor cero e imputaciones de $40.000; dos emisiones con
  unidades NUEVAS cruzadas crean cuentas ordenadas por `unidad_id` en una sentencia y candados en la
  misma transacción, sin `40P01` (DB-3, QA-7);
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
- [ ] 3.7 **Lecturas.** `estado_de_cuenta`, `deuda_del_edificio` y `saldo_anterior`. Tests contra
  PostgreSQL: lecturas con una sola sentencia SQL (CTEs) y por tanto una sola snapshot en READ
  COMMITTED; una escritura concurrente no produce mezcla de movimientos e imputaciones (BE-6).
  Para edificio, partir de `cuenta` con JOIN o `= ANY(ids)`; nunca filtrar sólo por `complejo_id`
  sobre las tablas grandes. Cargar varios edificios y administraciones, correr ANALYZE y fijar
  `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` como app con tenant: el test rechaza `Seq Scan` y
  `Parallel Seq Scan` sobre `obligacion`, `movimiento` e `imputacion` (DB-2), sin desactivar seqscan
  para fabricar el verde. Mutante de consulta que abandona el acceso por cuenta debe caer en el plan.
  La deuda del edificio coincide, cuenta por cuenta, con `estado_de_cuenta`; saldo anterior de
  abril con marzo impago y de mayo con marzo pagado; saldo anterior con deuda cero y crédito a favor, excluyendo la emisión pedida según D12;
  distinguir el snapshot guardado al emitir por el 7 de la lectura actual después de pagar (AN-06);
  ninguna lectura escribe (conteos); B no ve el edificio
  de A (cero filas, nunca un error). RED contra funciones vacías. Escenarios: `libro-de-movimientos` ›
  Deuda de un edificio; › Saldo anterior sin débito nuevo (contra la base); › Pagar marzo lo saca del saldo
  anterior (contra la base); › Saldo anterior con crédito a favor; › Lectura durante una confirmación;
  › Plan del edificio con datos de varios edificios. Lecciones: L-016, L-034.

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
- [ ] 4.2 **Permiso `corregir_movimiento`, migración `0024` y auditoría de la corrección.** `Accion` y
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
  401 / 422 cuerpo / 404 edificio / 403 permiso / 404 recurso / 409-422 dominio (BE-7, BE-8); el OpenAPI declara 201, 401, 403, 404, 409, 422, 500 y 503 con sus
  esquemas; la ruta está en el barrido. Casos de SQLSTATE en SAVEPOINT: 23505 por nombre de constraint
  a 409 con su campo; 23503 a 404; 23514 y 42501 a 500 `{"error":"interno","request_id":...}`;
  40P01/40001 a 503 declarado, sin retry automático. No filtrar DETAIL ni valores a respuesta o logs;
  tras el error traducido, probar que la transacción exterior no queda abortada (BE-1, BE-5.1). RED: la ruta sin `responses=` da rojo en el test del OpenAPI; sin
  el chequeo de permiso, el de 403 da rojo en el código de estado. Escenarios:
  `correccion-de-movimientos` › Administrador por edificio; › Movimiento de otro edificio; › Super admin
  corrige; › El OpenAPI declara todas las respuestas; › Sin identidad; › Cuerpo con un campo de más; ›
  Importe con decimales de más; › La misma corrección dos veces; › El mismo `operacion_id` con otro motivo;
  `autorizacion-por-rol` › La ruta nueva está en el barrido. Lecciones: L-007, L-017, L-027, L-034.

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
