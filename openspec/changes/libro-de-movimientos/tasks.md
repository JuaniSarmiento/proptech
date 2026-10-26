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
  que impide apuntar a otra administración; RLS (B no ve lo de A); `UPDATE`, `DELETE ... WHERE false`,
  `INSERT ... ON CONFLICT DO UPDATE` y `TRUNCATE ... CASCADE` (éste como rol de arranque, en savepoint)
  rechazados con `P0001` y el texto de cada tabla; `candado_de_cuenta` sí admite `UPDATE` y `SELECT ... FOR
  UPDATE` como la app. RED: cada restricción probada contra la tabla creada sin ella (una por vez, en una
  copia de la migración), y cada trigger con su tabla sin el trigger. `downgrade` que se niega si hay filas
  (como dueño, con `NO FORCE`, design Migration Plan), visto rojo con una fila. Escenarios:
  `libro-de-movimientos` › Editar un movimiento por SQL directo (para estas cuatro); › Borrar sin filas
  también se rechaza; › Vaciar una tabla con hijas; › Upsert sobre el libro; › Otra administración no ve la
  cuenta; › Cuenta sin dueño; › Cuenta con los dos dueños; › Período que no es un mes. Lecciones: L-018,
  L-023, L-034, L-036.
- [ ] 1.2 **Migración `0023`, parte B: `obligacion`, `movimiento`, `imputacion`.** Tests como en 1.1, más:
  importe negativo y obligación en cero rechazados; `num_nonnulls(emision_id, operacion_id)`; los únicos
  de D5 (obligación por emisión y cuenta, `operacion_id`, interés por obligación y corte, `corrige_a` una
  sola vez); coherencia `tipo`/`sentido`/destino fijo; imputación de un débito rechazada **por la FK** de
  `sentido_del_movimiento`; imputación a una obligación de otra cuenta rechazada por la FK; contra-asiento
  de otro importe, de otra cuenta o de una corrección rechazados por la FK de `corrige_a`; ninguna columna
  `saldo`, `residual` ni `pagad` (catálogo). RED: cada restricción vista fallar contra la tabla sin ella;
  el catálogo, con una columna `saldo` agregada en una copia. Escenarios: `libro-de-movimientos` › Una
  obligación no puede apuntar a una cuenta ajena; › Obligación con importe negativo; › Catálogo sin
  columnas de saldo; `correccion-de-movimientos` › Corregir una corrección (la parte de la base).
  Lecciones: L-018, L-034, L-035.
- [ ] 1.3 **Las seis tablas en la lista única; `roles despues` y el chequeo de arranque las cubren.**
  Sumar las seis a `compartido/tablas_protegidas.py` con su texto y sus tres triggers (sin tocar la lógica
  de `roles.py`). Tests: `despues()` transfiere tablas y funciones y verifica por el efecto; la API y el
  worker no arrancan con `imputacion` del migrador; el test de catálogo da rojo si `movimiento` sale de la
  lista; `candado_de_cuenta` no está en la lista. **RB-4**: tabla homónima en otro esquema creada antes y
  después que la de `public`, y el mutante que saca `schemaname = 'public'` rojo en los dos órdenes.
  **QA-15**: función de bloqueo con otro dueño, y función con el texto de otra tabla, rojas en `despues()`.
  RED: sin las seis en la lista, el test de catálogo nombra cada una. **Verde = la suite completa** de
  backend (L-041), con el número de tests antes y después. Escenarios: `aislamiento-por-administracion` ›
  El paso de roles verifica las seis por el efecto; › Una tabla del libro sin declarar; › La API no
  arranca con una tabla del libro del migrador; › Una tabla homónima en otro esquema no hace pasar el
  chequeo; › El candado no es de sólo agregar. Lecciones: L-016, L-018, L-022, L-036, L-041.
- [ ] 1.4 **Ensayo de roles y rollback, corridos.** `infra/ci/ensayo-roles.sh`: antes de bajar de `0023`,
  comprobar como rol de arranque que las seis tablas están vacías y devolver tablas y funciones al
  migrador (Migration Plan, paso 1); corregir el mensaje `ciclo 0018/0016/0018`; ajustar
  `test_ensayo_login.py` a las revisiones nuevas. Correrlo entero con un `COMPOSE_PROJECT_NAME` propio,
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
  bonificación, y su sobrante cuando el componente no absorbe; dos créditos seguidos que superan la deuda;
  ningún residual negativo; montos `Dinero` y nunca `float`. RED contra `imputar` vacío (devuelve `([],
  importe)`). Mutantes: fondo antes de la ordinaria (rojo en el escenario del fondo); orden por obligación
  en vez de por período (rojo en el ejemplo de R04); destino fijo ignorado (rojo en condonación).
  Escenarios: `imputacion-de-creditos` › El ejemplo de R04; › Un pago parcial cubre la ordinaria antes que
  la extraordinaria; › El fondo de reserva, entre la ordinaria y la extraordinaria; › Un pago que cubre
  exacto un período; › Pago mayor que la deuda; › Una condonación baja sólo el interés condonado; › Un
  ajuste de interés baja sólo el interés que compensa; › Una bonificación va a la ordinaria de su período;
  › Destino fijo sin un componente que absorba; › Dos créditos que juntos superan la deuda. Lecciones:
  L-019, L-034.
- [ ] 2.2 **Estado de una cuenta: residual, crédito a favor y saldo anterior.** `dominio/estado.py` con
  `calcular_estado`. Tests, sin base: capital desglosado en tres componentes; residual nunca negativo;
  crédito a favor por crédito; deuda total sin duplicar la obligación vieja (R06); saldo anterior sin la
  emisión pedida. **Propiedad con `hypothesis`** (perfil `ci`): la invariante de D8 con un oráculo que suma
  débitos y créditos sin pasar por los componentes ni por `imputar`. RED contra `calcular_estado` vacío.
  Mutante: el residual sin el `max(0, ...)` rojo en la propiedad. Escenarios: `libro-de-movimientos` ›
  Capital desglosado; › Saldo anterior sin débito nuevo; › Pagar marzo lo saca del saldo anterior.
  Lecciones: L-019, L-034, L-035.
- [ ] 2.3 **Lo que no cuenta: emisión anulada, contra-asiento, ajuste enlazado y exceso.** Tests, sin
  base: anular deja la deuda como antes de emitir; el pago imputado a la emisión anulada vuelve como
  crédito; el ajuste que compensaba el interés anulado tampoco cuenta (D-085); el par corregido no cuenta y
  las imputaciones de otros créditos no se tocan; corregir un interés ya cubierto devuelve el exceso al
  crédito más reciente. La propiedad de 2.2 extendida con anulaciones y correcciones aleatorias. RED contra
  la versión de 2.2 (sin exclusiones). Mutantes: exceso devuelto al crédito más viejo (rojo en el escenario
  del exceso); ajuste enlazado que sigue contando (rojo en D-085). Escenarios: `libro-de-movimientos` ›
  Anular deja la deuda como antes de emitir; › El ajuste que compensaba el interés anulado;
  `imputacion-de-creditos` › Un pago imputado a una emisión que se anula vuelve como crédito;
  `correccion-de-movimientos` › Las imputaciones de otros créditos no se rehacen. Lecciones: L-019,
  L-034.

## 3. Casos de uso sobre la base (design D2 a D5, D7, D8, D12)

- [ ] 3.1 **Cuenta de unidad y candado.** `aplicacion/cuentas.py`: `cuenta_de_unidad` (crea si falta,
  `ON CONFLICT DO NOTHING` y lee) y `bloquear_cuentas`. Tests contra PostgreSQL: dos pedidos, y dos
  transacciones simultáneas, devuelven la misma cuenta; una unidad de otro edificio da `NoEncontrado`;
  `bloquear_cuentas` sin una fila de candado la recrea; exigen transacción. RED contra funciones que
  insertan sin `ON CONFLICT` (la segunda llamada falla con `23505` en vez de devolver el id). Escenarios:
  `libro-de-movimientos` › Pedir dos veces la cuenta de una unidad. Lecciones: L-034.
- [ ] 3.2 **`registrar_emision`.** Tests contra PostgreSQL: registra emisión y obligaciones; la misma dos
  veces no duplica; el mismo id con otro importe da `Conflicto("emision_id")`; segunda del período sin
  anular da `Conflicto("periodo")`; después de anular, intento 2; período inválido, sin obligaciones o con
  una unidad repetida dan `EntradaInvalida` con el campo; el crédito a favor de una cuenta se imputa a la
  obligación nueva. RED contra la función vacía (devuelve sin escribir), en cada aserción. Mutante: sin el
  paso 2 de D4 (sin mirar anuladas), la segunda emisión sólo la frena el único de `intento` cuando es
  concurrente; el test secuencial da rojo. Escenarios: `libro-de-movimientos` › Segunda emisión del mismo
  período; › Emitir de nuevo después de anular; › La misma emisión dos veces; › El mismo id con otras
  obligaciones; `imputacion-de-creditos` › El crédito a favor se imputa en la emisión siguiente.
  Lecciones: L-017, L-034.
- [ ] 3.3 **`anular_emision`.** Tests contra PostgreSQL: agrega el evento con motivo y responsable sin
  tocar otra fila (conteo de filas por tabla antes y después); motivo en blanco rechazado con el campo;
  dos veces, un solo evento; con otro motivo, `Conflicto("motivo")`; el estado de la cuenta vuelve al de
  antes de emitir, y re-emitir el período imputa el pago devuelto. RED contra la función vacía.
  Escenarios: `libro-de-movimientos` › Anular deja la deuda como antes de emitir; › Anular sin motivo; ›
  Anular dos veces; `imputacion-de-creditos` › Un pago imputado a una emisión que se anula vuelve como
  crédito (contra la base). Lecciones: L-034.
- [ ] 3.4 **`registrar_credito`.** Tests contra PostgreSQL: bloquea la cuenta, corre `imputar_pendientes`
  e imputa con R04 o con su destino fijo; el mismo `operacion_id` dos veces, un movimiento y un juego de
  imputaciones; con otro importe, `Conflicto("operacion_id")`; `correccion` y `saldo_inicial` rechazados
  como tipo; destino fijo sin destino rechazado. El ejemplo de R04 y el pago mayor que la deuda, contra la
  base. RED contra la función vacía. Mutante: imputar antes de bloquear (lo ve 3.6). Escenarios:
  `imputacion-de-creditos` › El ejemplo de R04 (contra la base); › Pago mayor que la deuda;
  `libro-de-movimientos` › El mismo crédito dos veces. Lecciones: L-017, L-034.
- [ ] 3.5 **`corregir`.** Tests contra PostgreSQL: contra-asiento de un pago (la cuenta vuelve a deber, los
  dos quedan, la corrección referencia); de un interés ya cubierto (el exceso vuelve como crédito);
  segunda corrección del mismo movimiento, corrección de una corrección y de un movimiento de una emisión
  anulada dan `Conflicto("movimiento_id")`; crédito de corrección imputado con R04; importe cero o
  negativo, y motivo en blanco, rechazados con el campo; idempotencia por `operacion_id`. RED contra la
  función vacía. Escenarios: `correccion-de-movimientos` › Corregir un pago registrado de más; › Corregir
  dos veces el mismo movimiento; › Corregir una corrección; › Un cargo cobrado de más; › Importe que no es
  positivo; › Corrección sin motivo. Lecciones: L-007, L-034.
- [ ] 3.6 **Concurrencia contra PostgreSQL real.** Con dos conexiones y una barrera: dos pagos de $60.000
  a la vez sobre $100.000 de deuda (deuda cero, $20.000 a favor, imputaciones suman $100.000); dos
  emisiones del mismo período (una pasa, la otra `Conflicto("periodo")` por el único de `intento`); una
  emisión de diez cuentas y un pago de una de ellas, y dos emisiones con cuentas cruzadas, sin `40P01`;
  pagos en dos cuentas distintas con una demorada antes de confirmar: la otra confirma sin esperarla;
  candado borrado antes de dos pagos simultáneos. RED: con `bloquear_cuentas` reemplazado por un no-op en
  una copia, el de dos pagos da rojo en la suma de imputaciones (no por un error de otra cosa, L-034).
  Escenarios: `imputacion-de-creditos` › Dos pagos simultáneos; › Una emisión y un pago a la vez; ›
  Cuentas distintas no se esperan; `libro-de-movimientos` › Dos emisiones simultáneas del mismo período;
  `aislamiento-por-administracion` › Un candado borrado no abre un hueco. Lecciones: L-011, L-020, L-034.
- [ ] 3.7 **Lecturas.** `estado_de_cuenta`, `deuda_del_edificio` y `saldo_anterior`. Tests contra
  PostgreSQL: la deuda del edificio coincide, cuenta por cuenta, con `estado_de_cuenta`; saldo anterior de
  abril con marzo impago y de mayo con marzo pagado; ninguna lectura escribe (conteos); B no ve el edificio
  de A (cero filas, nunca un error). RED contra funciones vacías. Escenarios: `libro-de-movimientos` ›
  Deuda de un edificio; › Saldo anterior sin débito nuevo (contra la base); › Pagar marzo lo saca del saldo
  anterior (contra la base). Lecciones: L-016, L-034.

## 4. Fronteras, permiso y ruta de corrección (design D9 a D11)

- [ ] 4.1 **El SQL de cada módulo sólo nombra sus tablas.** Test nuevo en `test_fronteras_de_modulos.py`
  con el mapa tabla → módulo (`administracion` de `acceso`) y las tres excepciones de E11, cada una con su
  motivo. RED: sin las excepciones, el árbol real da rojo nombrando `escritura.py`, `lectura.py` y
  `ejemplo.py` con sus tablas, y nada más (si aparece otra, se trae al orquestador, L-030). Mutantes en
  copia: `liquidacion/aplicacion/` con `FROM movimiento`; `cuenta_corriente/aplicacion/` con `JOIN unidad`;
  una tabla que no está en el mapa. Escenarios: `fronteras-de-modulos` › El código de hoy pasa con sus
  excepciones; › La liquidación nombra una tabla del libro; › La cuenta corriente nombra una tabla de
  complejos; › Sin la excepción de lectura; › Una tabla sin dueño declarado. Lecciones: L-013, L-022,
  L-029.
- [ ] 4.2 **Permiso `corregir_movimiento`, migración `0024` y auditoría de la corrección.** `Accion` y
  `_MATRIZ` (`{_SA, _AP}`); `0024` con el literal; modelo de detalle `extra="forbid"` sin motivo ni
  importe; `corregir` registra en la misma transacción y no repite en la idempotencia. Tests: la fila de la
  matriz para los nueve perfiles; el vocabulario contiene el valor; la fila de auditoría y su detalle; una
  auditoría que falla deja el libro sin la corrección ni sus imputaciones. RED: sin la fila, SA y AP dan
  `False`; sin `0024`, `registrar` choca con la FK (rojo en la aserción de la fila de auditoría, no en el
  arranque). Escenarios: `autorizacion-por-rol` › La fila de la matriz; `auditoria-de-acciones` ›
  Corrección auditada; › Falla la auditoría; › El vocabulario nuevo. Lecciones: L-007, L-034.
- [ ] 4.3 **Ruta `POST /api/complejos/{complejo_id}/correcciones` y su contrato.** Router
  `proptech_api/cuenta_corriente.py`, `proptech_api/errores.py` con las cinco formas y
  `RESPUESTAS_DE_ERROR`, manejador de los errores del libro. Tests contra la app real: 401 sin identidad
  sin tocar la base; 404 para un movimiento de otra administración igual que para uno inexistente (misma
  respuesta, L-017); 403 para el administrador por edificio con `corregir_movimiento`; 201 para SA y AP;
  422 por campo de más y por `"10.005"`, sin repetir el valor; 409 por `operacion_id` con otro motivo;
  repetición idempotente 201 con el mismo id; el OpenAPI declara 201, 401, 403, 404, 409 y 422 con sus
  esquemas; la ruta está en el barrido. RED: la ruta sin `responses=` da rojo en el test del OpenAPI; sin
  el chequeo de permiso, el de 403 da rojo en el código de estado. Escenarios:
  `correccion-de-movimientos` › Administrador por edificio; › Movimiento de otro edificio; › Super admin
  corrige; › El OpenAPI declara las cinco respuestas; › Sin identidad; › Cuerpo con un campo de más; ›
  Importe con decimales de más; › La misma corrección dos veces; › El mismo `operacion_id` con otro motivo;
  `autorizacion-por-rol` › La ruta nueva está en el barrido. Lecciones: L-007, L-017, L-027, L-034.

## 5. Deuda del 4a (design D13)

- [ ] 5.1 **RB-7 y QA-6, QA-7, QA-9, QA-12, QA-14.** RB-7: `Dinero("1.00")` bajo un `localcontext` con
  `prec=2` no levanta `InvalidOperation` (RED con el constructor de hoy). Para cada QA: buscar el test del
  4a que lo cubre y anotarlo con su ruta y nombre (EVIDENCIA); si no existe, escribirlo y verlo fallar con
  su mutante (QA-6: `scaleb` contra `10 ** -exp` con `1E+2`; QA-7: aritmética bajo un contexto ajeno;
  QA-9: SQLSTATE del `UPDATE` del umbral y el borde `0.00` del `CHECK`; QA-12: el modelo de detalle del
  padrón rechaza un campo de más; QA-14: migración de prueba que hace algo antes de un `ALTER` sobre una
  tabla protegida falla con `must be owner` sin dejar nada a medias). Lo que no entre en medio día se
  anota como deuda con dueño propuesto, nunca se marca hecho. Lecciones: L-012, L-019, L-035.

## 6. Cierre

- [ ] 6.1 **Corrida de cierre después de la última vuelta.** Sobre el último commit del change, con el SHA
  anotado (`git rev-parse HEAD`): `bash infra/ci/test-backend.sh` **completo** (no por grupo, L-041), con el
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
