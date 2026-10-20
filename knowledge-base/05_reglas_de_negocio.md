# Reglas de negocio

Cómo se comporta el sistema con la plata. **Cada regla vigente se convierte en uno o más tests**
antes de que exista el código que la cumple. **Se reescribe** cuando una regla cambia; el
porqué del cambio va a `09_decisiones_y_supuestos.md`.

Estados: **Pendiente** (no decidida) · **Propuesta** (hay una propuesta, falta validarla con un
administrador o contador) · **Vigente** (decidida y registrada en `09_decisiones_y_supuestos.md`). Una vigente cuyos
valores o criterios de plata no revisó todavía nadie del rubro lleva además **a validar (P42)** en el
título (D-089): se construye igual, pero sus números pueden cambiar después de esa revisión.

Las reglas se agrupan por dominio (adaptación al formato v1 de Active Stack, D-093); **los
identificadores no se renumeran**: siguen siendo R01 a R41 en el orden en que se decidieron, cada uno
dentro del dominio donde vive hoy. Un mismo número de regla no se repite entre dominios.

---

## Dominio: Acceso y aislamiento

## R10 · Aislamiento entre administraciones y alcance por edificio · Vigente (D-016, D-076)

- **Regla**: todo dato pertenece a una **administración** (el tenant, el cliente que paga) y ninguna
  consulta, archivo, caché o proceso devuelve datos de otra. La administración sale de la identidad
  autenticada, nunca de un parámetro que manda el cliente (análisis H02, H14, H27). Row-Level
  Security es el segundo candado.
- **Alcance por edificio**: dentro de su administración, cada persona ve sólo los complejos que le
  corresponden según perfil y alcance (D-106): los perfiles principales, todos; los perfiles por
  edificio, los asignados; el vecino, sus unidades y lo que corresponde a su vínculo. Fuera de alcance responde 404.
- **Tests mínimos**: un pedido con el identificador de otra administración no devuelve nada; una
  consulta a la base sin fijar la administración no devuelve filas; un administrador por edificio no ve un edificio
  no asignado de su propia administración; un vecino no ve la unidad de otro vecino; una escritura con
  el identificador de otra administración se rechaza; el worker sin administración fijada no lee nada;
  un link firmado de otra administración responde "no encontrado"; el consejo ve sólo su edificio y
  no puede escribir.

---

## Dominio: Complejos (configuración del edificio)

## R01 · Prorrateo de gastos · Vigente (D-013) · a validar (P42)

- **Grupos de reparto**: cada complejo define sus grupos (por ejemplo "Generales", "Pileta",
  "Obra calle 5"). Cada grupo tiene:
  - las unidades que participan;
  - el método: por coeficiente, por superficie o en partes iguales.
- **Cada gasto se asigna a un grupo** y se reparte sólo entre sus unidades. El grupo dice **quién
  paga**; la categoría (R16) dice **en qué se gastó**. Son independientes.
- **Default**: un complejo nuevo arranca con un grupo "Generales", todas las unidades, por coeficiente.
- **Coeficientes de un grupo parcial** (D-100, P24): cada grupo parcial por coeficiente elige su modo.
  Por defecto, **renormalizado**: cada unidad usa su coeficiente general dividido por la suma de los
  generales de las unidades del grupo. Si el reglamento fija porcentajes propios, **coeficientes
  propios**: cada unidad del grupo lleva el suyo, y tienen que sumar 1 dentro del grupo. Un grupo por
  superficie o en partes iguales no tiene coeficientes propios.
- **Validación** (D-082, a validar con un administrador): los coeficientes de "Generales" y los de
  cada grupo con coeficientes propios suman 1 con una tolerancia de ±0,0001, con el borde incluido
  (0,9999 y 1,0001 están dentro). **La carga no se rechaza** (E5 del 3a): cargar el padrón de a una
  unidad pasa necesariamente por sumas parciales que no dan 1. **Se informa siempre la suma, la
  diferencia y su estado**: "ok" si es exactamente 1, "advertencia" dentro de la tolerancia y "fuera de
  tolerancia" si se aparta más. **La emisión se bloquea**: un grupo fuera de tolerancia dispara el
  control duro "Coeficientes fuera de tolerancia" de R34 (cambio 7). Dentro de la tolerancia, el
  reparto usa cada coeficiente dividido por la suma real, así el total sigue exacto con R07.
- **Historia**: la liquidación guarda la composición de cada grupo usada en ese período.
- **Grupos típicos de un edificio**: Generales (todas las unidades), Ascensor (sin planta baja ni
  locales), Cocheras, Servicios centrales. En barrios: Generales, Pileta, Obra calle 5.
- **Tests mínimos**: gasto general entre todos; gasto de un grupo parcial no toca a los demás;
  partes iguales; la suma repartida es igual al gasto, al centavo; coeficientes que suman 0,9999 dan
  advertencia y el total sigue exacto; coeficientes que suman 0,9998 se guardan, se informan "fuera de
  tolerancia" y la emisión no sigue; un grupo renormalizado reparte entre sus unidades en proporción a
  sus coeficientes generales; un grupo con coeficientes propios que suman 0,8 se informa fuera de
  tolerancia.

## R02 · Estado de la unidad · Vigente (D-014) · desactivada en edificios (D-030) · se construye con barrios (v1.2, D-089)

- **Estados**: baldío, en obra, habitado, desocupado.
- **Configurable por complejo, por estado** (menú cerrado):

  | Opción | Ejemplo | Default |
  |---|---|---|
  | Factor sobre la participación en el reparto | baldío 50% | 100% |
  | Cargo fijo mensual | en obra: canon de $20.000 | $0 |

- **El factor se redistribuye**: un lote con factor 50% pesa la mitad en el reparto y la
  diferencia la absorben los demás lotes del grupo, de modo que el gasto total queda cubierto
  al centavo. (El factor modifica el peso del lote y el reparto se renormaliza.)
- **El cargo fijo** es un débito propio de la unidad, separado del prorrateo.
- **Momento**: se toma el estado del lote al emitir y queda guardado en la liquidación. Un cambio
  posterior no altera liquidaciones emitidas.
- **Tests mínimos**: complejo con defaults reparte igual que sin estados; baldío al 50% paga la mitad
  y el total sigue cubierto; canon de obra aparece como débito aparte; cambio de estado después de
  emitir no modifica esa liquidación.

## R15 · Fondo de reserva · Vigente (D-031)

- **Configurable por edificio**: un porcentaje sobre la **ordinaria prorrateada** del período (R13). Default: 0%
  (sin fondo de reserva).
- **En la liquidación**: aparece como línea propia de la expensa de cada unidad, calculada sobre su
  ordinaria prorrateada y redondeada con R07; la suma de las partes da exacto el total del fondo del período.
- **Imputación**: forma parte de la ordinaria (R04, R13).
- **Sin tesorería**: el sistema no lleva el saldo acumulado del fondo ni el saldo de caja (D-023).
- **Historia**: cada liquidación guarda el porcentaje usado.
- **Tests mínimos**: con 0% no aparece la línea; con 5% cada unidad paga el 5% de su ordinaria
  prorrateada, sin contar sus cargos particulares;
  la suma del fondo es exacta; cambiar el porcentaje no altera liquidaciones emitidas.

## R16 · Categorías de gasto · Vigente (D-041)

- **Qué es**: la clasificación de un gasto según en qué se gasta (encargado y cargas sociales,
  seguridad, limpieza, ascensor, mantenimiento, servicios, seguros, administración, varios).
- **Parametrizable**: cada edificio arranca con las categorías del archivo de parámetros (D-042) y el
  administrador puede crear, renombrar, ordenar y desactivar las suyas. Una categoría con gastos no
  se borra: se desactiva.
- **Cada gasto tiene una categoría obligatoria**, además de su grupo de reparto (R01) y su tipo
  ordinario o extraordinario (R13). La IA sugiere la categoría al leer la factura (R12) y el
  administrador la confirma.
- **No cambia los cálculos**: la categoría sólo ordena la presentación y los reportes.
- **Presentación**: la expensa (PDF y portal) muestra dos bloques, ordinaria y extraordinaria; dentro
  de cada uno, los gastos agrupados por categoría con su subtotal y el porcentaje que representa.
- **Historia**: la liquidación guarda el nombre de la categoría vigente al emitir; renombrarla después
  no cambia expensas ya emitidas.
- **Tests mínimos**: los subtotales por categoría suman el total del bloque; un mismo concepto puede
  ser ordinario o extraordinario y cae en su bloque; renombrar no altera una liquidación emitida;
  un gasto sin categoría no se puede aprobar.

## R36 · Tasa propia para la expensa extraordinaria · Propuesta (D-071)

- **Qué resuelve**: la asamblea que aprueba una obra puede fijar un interés por mora distinto para esas
  cuotas que para la expensa ordinaria.
- **Propuesta**: R03 suma una opción al menú de cada edificio: la extraordinaria usa la misma tasa que la
  ordinaria (default) o una tasa propia. Siempre interés simple, igual que R03.
- **Tests mínimos**: sin tasa propia, la extraordinaria usa la de la ordinaria; con tasa propia, cada
  capital genera interés con su tasa; un pago parcial sigue el orden de R04 y cada parte deja de
  generar interés con su propia tasa.

## R39 · Unidades del propio consorcio · Propuesta (D-071)

- **Qué resuelve**: unidades que son del consorcio (la portería, un departamento propio que se
  alquila). El consorcio no puede cobrarse intereses a sí mismo.
- **Propuesta**: una unidad marcada como "del consorcio" **no genera intereses**, no recibe
  bonificaciones, no cuenta como moroso crítico (R20) y no recibe avisos de mora.
- **Pendiente** (P16): cómo se trata su parte de cada gasto: si se reparte entre las demás unidades o
  si se registra como gasto del consorcio. Depende del reglamento; se valida con Alberto.
- **Tests mínimos**: una unidad del consorcio con saldo vencido no genera interés; no aparece en la
  lista de morosos; desmarcarla la vuelve a tratar como cualquier unidad desde el período siguiente.

---

## Dominio: Cuenta corriente

## R03 · Intereses por mora · Vigente (D-010) · a validar (P42)

- **Tipo**: interés **simple**, siempre. No se cobra interés sobre interés (art. 770 del Código
  Civil y Comercial). No es configurable.
- **Base**: lo que sigue impago de cada obligación (su residual según R05). No es configurable.
- **Configurable por complejo** (menú cerrado, no fórmula libre):

  | Opción | Valores | Default |
  |---|---|---|
  | Tasa mensual | porcentaje | 3% |
  | Días de gracia | entero desde 0; si se superan, el interés corre desde el vencimiento (D-081) | 0 |
  | Forma de cálculo | proporcional por día de atraso · mes entero al pasar el vencimiento | proporcional por día |

- **Propuestas relacionadas**: vencimiento en día inhábil (R35) y tasa propia para la extraordinaria
  (R36).
- **Cuándo se registra**: al emitir la liquidación siguiente, como un débito con su detalle
  (obligación, días, tasa, base). El número no cambia cada vez que el vecino entra al portal.
- **Historia**: cada liquidación guarda la configuración con la que se calculó. Cambiar la tasa
  no altera liquidaciones ya emitidas.
- **Tests mínimos**: pago parcial reduce la base; días de gracia no generan interés; un pago después
  de los días de gracia genera interés desde el vencimiento; cambio de tasa entre períodos; nunca hay
  interés calculado sobre un interés; con "mes entero", un día de atraso cobra el mes completo.

## R04 · Orden de imputación · Vigente (D-011)

- **Regla única, no configurable**:
  1. Primero la obligación con el período más antiguo.
  2. Dentro de cada período, primero los intereses, después la expensa ordinaria (incluidos los
     cargos particulares) y por último la extraordinaria.
  3. Lo que sobra sigue con el período siguiente; si se cancela todo, el resto queda como crédito a favor (R05).
- **Ejemplo**: el lote debe agosto ($80.000 + $4.000 de interés) y septiembre ($85.000) y paga
  $100.000. Se imputan $4.000 al interés de agosto, $80.000 al capital de agosto y $16.000 a
  septiembre, que queda con $69.000 pendientes.
- **Concurrencia**: dos pagos de la misma unidad que llegan a la vez se imputan uno después del
  otro, nunca sobre la misma foto de la deuda (análisis H05).
- **Por qué ordinaria antes que extraordinaria**: la ordinaria sostiene la operación diaria del
  complejo (seguridad, luz, encargado); con pagos parciales, primero se cubre lo que no puede dejar de pagarse.
- **Tests mínimos**: el ejemplo de arriba; pago parcial cubre intereses y ordinaria antes que extraordinaria; pago que cubre exacto un período; pago que cancela
  todo y deja crédito; dos pagos simultáneos de la misma unidad.

## R05 · Pagos parciales y excedentes · Vigente (D-012, D-086) · a validar (P42)

- **Qué define**: qué queda después de un pago que no cubre o que supera la deuda.
- **Regla**: cada imputación se registra; el residual de cada obligación se calcula a partir
  de sus imputaciones, nunca con una marca de "pagada" (análisis H04). El excedente queda como
  crédito a favor y se compensa en la siguiente liquidación (H07).
- **Créditos que no son pagos** (D-086, resuelve P35): bajan el residual con una imputación propia,
  igual que un pago, y cada uno va a un destino fijo:
  - **Condonación** (R29): al interés que condona.
  - **Ajuste de interés** (R11): al interés que compensa.
  - **Bonificación** (R37): a la ordinaria del período bonificado.
  - **Corrección** (R08) y **reimputación** (R25): con el orden de R04, como un pago.
  - **Baja de deuda** (R41): a todas las obligaciones impagas de la unidad, con R04.
  El residual de una obligación es su importe menos todas sus imputaciones, sean de pagos o de
  créditos.
- **Tests mínimos**: un pago parcial deja el residual exacto de cada obligación; un pago mayor que la
  deuda deja el excedente como crédito a favor; el crédito a favor se imputa con R04 en la liquidación
  siguiente; una condonación baja sólo el residual del interés condonado; un ajuste de interés baja sólo
  el interés que compensa; ninguna obligación queda con residual negativo.

## R06 · Saldo arrastrado · Vigente (D-012)

- **Qué define**: cómo se muestra la deuda vieja en la expensa nueva sin cobrarla dos veces.
- **Regla**: la deuda vieja vive en sus obligaciones originales; la expensa nueva la **muestra**
  como saldo anterior pero no genera un débito nuevo por ella (análisis H06).
- **Tests mínimos**: una unidad con deuda de marzo ve en la expensa de abril el saldo anterior y su
  deuda total es la suma de las dos obligaciones, sin duplicar la de marzo; pagar la de marzo la saca
  del saldo anterior en la expensa siguiente; el saldo anterior que muestra la expensa coincide con el
  calculado desde el libro a la fecha de emisión.

## R07 · Precisión y redondeo · Vigente (D-015, D-046)

- **Representación** (D-046): todo importe es `Decimal` en Python, construido desde texto
  (`Decimal("0.10")`, nunca `Decimal(0.1)`), `NUMERIC(14,2)` en la base y texto en el JSON. Nunca
  `float`. El frontend no calcula montos: sólo los formatea.
- **Coeficientes que no suman exacto 1**: ver R01 (tolerancia ±0,0001; se reparte proporcional a la
  suma real).
- **Reparto**: cada parte se redondea al centavo; la diferencia hasta el total exacto se asigna de
  a un centavo a las unidades con mayor fracción descartada (método del mayor resto). En empate,
  por orden de identificador de la unidad, para que el resultado sea determinista.
- **Garantía**: la suma de las partes es siempre igual al gasto, al centavo; ninguna unidad se
  aparta más de un centavo de su parte exacta.
- **Intereses**: se calculan con precisión completa y se redondean al centavo una sola vez, al registrarse.
- **Modo de redondeo**: *pendiente (P10)*. Bancario o medio hacia arriba; hasta decidirlo, ningún
  test fija el resultado de un caso que termine exactamente en medio centavo.
- **Tests mínimos**: un `float` en un monto hace fallar la prueba; $1.000.000 entre 150 unidades suma exacto; empate de fracciones es
  determinista; un reparto entre 1 unidad devuelve el total.

## R08 · Correcciones · Vigente (D-016)

- **Regla**: ningún movimiento de la cuenta corriente se edita ni se borra. Una corrección es
  un movimiento nuevo con motivo, responsable y referencia al que corrige (análisis H03, H16).
- **Tests mínimos**: un UPDATE o un DELETE sobre un movimiento rebota en la base, también por SQL
  directo; una corrección sin motivo se rechaza; una corrección referencia al movimiento que corrige y
  los dos quedan visibles; el saldo después de una corrección es el correcto.

## R09 · Saldo inicial al migrar · Vigente (D-015, D-068) · a validar (P42)

- **Con detalle por período** (si el complejo lo tiene): se carga cada obligación vieja con su
  período, concepto y vencimiento desde una hoja opcional de la plantilla (unidad, concepto, período,
  vencimiento, monto, interés acumulado). **El interés anterior a la migración no se recalcula** (D-082, a validar con un administrador): entra como
  el administrador lo trae, en su columna, y R03 corre sólo desde la fecha de migración. Así no se
  cobra dos veces.
- **Sólo con un total**: se carga una obligación "saldo inicial" con vencimiento en la fecha de
  migración; los intereses corren desde ahí, sólo sobre el capital. Si el administrador trae interés ya
  devengado, va en una columna aparte que **no genera interés** (R03, D-083).
- **Edificio sin saldos previos** (D-082): un edificio nuevo, creado a mano o el de ejemplo, se
  confirma con "sin saldos previos", que cierra el importador con todas las unidades en cero. Así el
  control duro de R34 no lo bloquea para siempre. El edificio de ejemplo trae esa confirmación en la
  semilla: el cambio 3 suma a la semilla y a su validador el **estado de migración** del edificio
  (pendiente, confirmada o sin saldos previos, D-083).
- **Crédito a favor**: entra como crédito y se compensa en la primera liquidación.
- **Trazabilidad**: cada saldo inicial guarda el archivo y la fila de origen.
- **Comparación por unidad** (D-068): lo importado queda primero en un **borrador** que no toca la
  cuenta corriente. El sistema lo compara **unidad por unidad** contra el saldo de cada unidad según
  el administrador, y muestra cada diferencia con su unidad. El total se compara también, como
  control adicional. Sin diferencias, se habilita "Confirmar saldos". Con diferencias, el
  administrador las corrige o las acepta igual, y la aceptación queda registrada (quién, cuándo y qué
  diferencias).
- **Después de confirmar**: el importador se cierra para ese edificio. Un saldo inicial mal cargado
  se corrige con un ajuste con motivo (R08), nunca reabriendo la migración.
- **Tests mínimos**: el interés acumulado que trae el administrador entra tal cual y no genera
  interés; el interés corre sólo desde la fecha de migración; saldo con detalle genera sus obligaciones; total único genera una sola;
  crédito negativo entra como crédito; la suma importada coincide con el archivo de origen; dos
  errores de signo opuesto en dos unidades (+10.000 y -10.000) dan el total correcto y aun así
  aparecen como dos diferencias; el borrador no genera movimientos hasta confirmar; aceptar
  diferencias deja registro; con el importador cerrado, un segundo intento de importar se rechaza.

## R26 · Recargo escalonado por primer y segundo vencimiento · Pendiente (ProTecc G4, Q9) · alternativa a R03

- **Qué resuelve**: Alberto describe un esquema de primer y segundo vencimiento con un recargo que
  escala entre uno y otro, distinto del interés simple continuo desde un único vencimiento que ya
  tiene R03.
- **Pendiente**: preguntarle a Alberto si el edificio piloto usa este esquema antes de tocar R03, que
  ya está marcada "falta validar". No se decide sin esa respuesta.
- **Tests mínimos**: a definir si se confirma el esquema.

## R30 · Umbral mínimo de saldos por redondeo · Propuesta (ProTecc D3) · extiende R07

- **Qué resuelve**: saldos chicos (a favor o en contra) que quedan de intereses o pagos parciales,
  por debajo de lo que tiene sentido reclamar o devolver.
- **Propuesta**: definir un umbral mínimo (por ejemplo, configurable por edificio) por debajo del
  cual el saldo no genera reclamo de cobranza ni devolución automática, y se arrastra con R06 hasta
  que se acumula o se liquida junto con otro movimiento.
- **Falta decidir**: el valor del umbral y si es fijo o configurable por edificio.
- **Tests mínimos** (a definir con el umbral): un saldo por debajo del umbral no dispara un aviso de
  mora; un saldo por encima sigue el camino normal de R03/R20.

---

## Dominio: Gastos y cargos

## R12 · Registro de gastos desde facturas · Vigente (D-019)

- **IVA** *(propuesta, D-071, P17)*: el gasto se registra por el **total de la factura, con el IVA
  incluido**, porque el consorcio en general no lo descuenta: para él es parte del costo. Si algún
  consorcio fuera responsable inscripto, eso se trata aparte y fuera del MVP. A confirmar con un
  contador.
- **Primero el QR de ARCA.** Toda factura electrónica lleva un QR con el texto
  `https://www.arca.gob.ar/fe/qr/?p={JSON en Base64}` (las anteriores al cambio de nombre dicen
  `afip.gob.ar`: se aceptan los dos). Especificación oficial, versión 1, publicada en
  febrero de 2025: `https://www.arca.gob.ar/fe/qr/documentos/QRespecificaciones.pdf`.
  Campos del JSON:

  | Campo | Contenido | Uso en PropTech |
  |---|---|---|
  | `ver` | versión del formato (1) | rechazar versiones desconocidas con aviso |
  | `fecha` | fecha de emisión (AAAA-MM-DD) | período sugerido del gasto |
  | `cuit` | CUIT del emisor | identificar al proveedor |
  | `ptoVta`, `tipoCmp`, `nroCmp` | punto de venta, tipo y número | identificador único junto con `cuit` |
  | `importe`, `moneda`, `ctz` | importe total, moneda, cotización | monto del gasto (en pesos: `importe × ctz`) |
  | `tipoDocRec`, `nroDocRec` | documento del receptor (de corresponder) | verificar que la factura es a nombre del complejo |
  | `tipoCodAut`, `codAut` | CAE o CAEA y su código | validación contra ARCA más adelante (WSCDC) |

- **La IA completa lo que el QR no trae**: el concepto (seguridad, jardinería...), el período del
  servicio y el grupo de reparto sugerido. Si la factura no tiene QR legible, la IA lee todo y el
  gasto queda **en revisión** (D-075), con la nota "sin QR", para que el administrador lo revise con
  más cuidado (D-085).
- **Factura duplicada**: `cuit + ptoVta + tipoCmp + nroCmp` no se repite dentro del complejo. Se frena al cargarla.
- **Receptor equivocado**: si `nroDocRec` existe y no es el CUIT del complejo, se avisa antes de confirmar.
- **Nunca aprobado sin confirmación**: ningún dato leído (por QR o por IA) entra en la liquidación sin
  que el administrador confirme el gasto. Según cómo salió la lectura, el gasto queda en borrador, sin
  IA o en revisión (D-075). La IA no inventa datos ausentes: los marca como faltantes.
- **Tests mínimos**: decodifica el ejemplo oficial de ARCA; acepta los dos dominios; rechaza un
  duplicado; avisa receptor distinto; moneda extranjera convierte con `ctz`; sin QR queda en revisión con la nota "sin QR"; un QR corrupto o de versión desconocida
  deja el gasto en revisión con su aviso.

## R13 · Expensa ordinaria y extraordinaria · Vigente (D-024)

- **Cada gasto se marca** como ordinario o extraordinario al cargarlo. Default: ordinario.
- **Una obligación por unidad y período**, con el capital desglosado en ordinario y extraordinario.
  La expensa del vecino los muestra en bloques separados, con su subtotal.
- **Imputación**: dentro del período, intereses, después ordinaria, después extraordinaria (R04).
- **Ordinaria prorrateada** (D-081): la parte de cada unidad en los gastos ordinarios de sus grupos,
  neta de notas de crédito (R22) e ingresos (R38; mientras R38 sea propuesta, no hay ingresos que restar). No incluye cargos particulares, intereses ni el
  fondo de reserva. Es la base del fondo de reserva (R15) y de la bonificación por pronto pago (R37).
  Ejemplo: una unidad con $40.000 de ordinaria prorrateada, una multa de $5.000 y un fondo del 5%
  paga $40.000 + $2.000 de fondo + $5.000 de multa = $47.000.
- **Escala**: la separación queda guardada porque más adelante importa quién paga cada una
  (en Argentina, la extraordinaria suele corresponder al propietario y no al inquilino).
- **Tests mínimos**: un gasto extraordinario aparece en su bloque; los subtotales suman el total;
  un pago parcial cubre primero la ordinaria; la ordinaria prorrateada no incluye una multa del
  período (el ejemplo de $47.000).

## R14 · Cargos particulares · Vigente (D-025)

- **Qué es**: un importe que se carga a una sola unidad (limpieza del quincho, una multa aprobada,
  un consumo, un arreglo que causó ese lote). Distinto del cargo fijo por estado (R02), que es mensual
  y automático.
- **Carga**: el administrador lo registra con unidad, concepto, importe, período y motivo; o los
  importa en lote desde un Excel (unidad, concepto, importe). Queda en borrador hasta aprobarlo.
- **Liquidación**: los aprobados del período entran en la expensa de esa unidad, como líneas propias
  dentro de la parte ordinaria, sin afectar el reparto de los demás.
- **Cargos recurrentes del reglamento** *(propuesta, D-082)*: un cargo particular que la regla del motor
  genera cada período para ciertas unidades (por ejemplo, un canon por cochera). Entra en la expensa
  como cualquier cargo particular. Tests: el cargo aparece cada período en las unidades indicadas y
  en ninguna otra; apagar la regla lo deja de generar desde el período siguiente.
- **Créditos particulares** (una bonificación excepcional, una devolución; no la bonificación por pronto
  pago de R37, que tiene su propio destino en R05) no son cargos negativos: se registran
  como corrección (R08).
- **Tests mínimos**: un cargo particular sólo afecta a su unidad; no cambia lo que pagan los demás;
  la importación desde Excel rechaza unidades inexistentes; un cargo en borrador no entra.

## R22 · Nota de crédito asociada a la factura · Vigente (D-061) · extiende R12 · a validar (P42)

- **Regla**: una nota de crédito de un proveedor queda **asociada a la factura que corrige** y su
  monto **no puede superar** el de esa factura.
- **Efecto en el gasto**: se descuenta del gasto antes de prorratear, dentro del mismo grupo de
  reparto de la factura original (no es un gasto negativo suelto). Si la factura ya se liquidó en un
  período emitido, la nota de crédito se descuenta en el período en que se carga, dentro del mismo
  grupo: nunca reabre una liquidación emitida (D-082, a validar con un administrador).
- **Duplicados**: el control de factura duplicada de R12 usa la clave `cuit + ptoVta + tipoCmp + nroCmp`,
  que incluye el **tipo de comprobante** porque una factura y su nota de crédito pueden compartir número
  al numerarse por separado.
- **Tests mínimos**: una nota de crédito de una factura liquidada en un período ya emitido se descuenta en el período en
  que se carga y no cambia la liquidación emitida; una nota de crédito menor al monto de la factura reduce el gasto repartido; una
  nota de crédito que supera el monto de su factura se rechaza; una nota de crédito sin factura
  asociada se rechaza; una factura y su nota de crédito con el mismo número no se marcan como
  duplicadas entre sí.

## R23 · Control de monto atípico contra el historial del proveedor · Propuesta (ProTecc A2)

- **Qué resuelve**: una factura leída por IA con un monto mal leído (por ejemplo, $38.900 en vez de
  $389.000).
- **Propuesta**: antes de aprobar un gasto leído por IA, comparar su importe contra el historial de
  ese proveedor en el edificio (últimos períodos) y marcarlo para revisión manual si se aparta mucho
  de lo habitual.
- **Falta decidir**: el umbral de "atípico" y si se valida con un administrador o contador antes de
  fijarlo.
- **Tests mínimos** (a definir con el umbral): un monto dentro de lo habitual no se marca; un monto
  muy por encima o por debajo del historial se marca para revisión; un proveedor sin historial previo
  no genera falso positivo por falta de datos.

## R38 · Ingresos del consorcio · Propuesta (D-071)

- **Qué resuelve**: lo que el consorcio cobra (alquiler de una cochera o baulera común, de la terraza
  para una antena, el uso del SUM por terceros) tiene que bajar lo que pagan todos. Hoy la base sólo
  tiene gastos.
- **Propuesta**: el administrador registra un **ingreso** con concepto, importe, período, grupo de
  reparto y respaldo. Al liquidar, los ingresos aprobados se restan de los **gastos ordinarios** de su
  grupo (nunca de la extraordinaria), y sobre el neto se aplica el reparto de R01 y R07 (D-082). La expensa los muestra en un bloque propio,
  "Ingresos", con su detalle.
- **Si quien paga es un vecino** (por ejemplo, alquila una cochera común): se le carga como cargo
  particular a su unidad (R14) y el mismo importe entra como ingreso del consorcio.
- **Pendiente** (P15): qué pasa si en un mes los ingresos superan los gastos ordinarios del grupo. Hasta
  decidirlo, el sistema lo frena con un control duro de R34, que no se puede aceptar (D-080).
- **Tests mínimos**: un ingreso baja el total a repartir de su grupo y no el de otros grupos; el reparto
  del neto sigue sumando exacto; un ingreso en borrador no entra; un ingreso mayor que los gastos frena
  la emisión.

---

## Dominio: Liquidación y emisión

## R17 · Ventana de anulación antes de distribuir · Vigente (D-055, D-073, D-074, D-079, D-081) · refina R08

- **Regla**: una liquidación **emitida** se puede **anular** sólo mientras esté en estado emitida y
  todavía no distribuida. Estados: borrador, emitida, distribuida y anulada (sólo desde emitida).
- **Anulación** (D-073, D-079): es un **cambio de estado**, no un borrado. La liquidación pasa de
  emitida a anulada, con motivo obligatorio, responsable y fecha. Ningún movimiento del libro se
  modifica ni se borra: el saldo de cada unidad excluye **todo movimiento generado por la emisión
  anulada** (sus obligaciones, los intereses que registró y los ajustes de interés que los compensaban,
  R11), así que la deuda queda igual que antes de emitir
  y volver a emitir no duplica nada. Si antes de anular se había imputado un pago a esas obligaciones,
  la imputación deja de valer y el pago vuelve como **crédito a favor** de la unidad, que se imputa con
  R04 en la nueva emisión (D-081).
- **Distribuida** (D-074): una liquidación pasa a distribuida cuando el administrador la **distribuye**
  (acción manual del cambio 7), cuando sale el primer email (cambio 13) o cuando un vecino la abre en
  el portal (cambio 11), lo que pase primero. Los tres caminos registran el mismo evento por un único
  puerto.
- **Después de distribuida**: rige R08 sin excepciones. Ningún movimiento se edita ni se borra; todo
  error se corrige con un movimiento nuevo (ajuste).
- **Tests mínimos**: anular una liquidación emitida deja el saldo de cada unidad igual al de antes de
  emitir, sin modificar ni borrar ningún movimiento, y registra la anulación con motivo y responsable;
  anular y volver a emitir no cobra dos veces el interés de la deuda vieja; un pago imputado a una
  emisión que se anula queda como crédito a favor; anular la emisión cuyo interés compensaba un ajuste
  de R11 excluye los dos y la unidad no queda debiendo ni con crédito de más; intentar anular una
  liquidación distribuida (por la acción "distribuir", por un email o por una vista
  en el portal) lo rechaza; la anulación sin motivo se rechaza; una liquidación anulada permite volver a
  emitir el período; anular una liquidación en borrador o ya anulada se rechaza.

## R24 · Modo degradado de emisión · Vigente (D-075, ProTecc A4, principio 6 de Alberto)

- **Qué resuelve**: que la emisión de la liquidación no dependa de un servicio externo (lectura del
  extracto, IA de facturas). Si ese servicio falla el día de emitir, la liquidación tiene que poder
  salir igual.
- **Estados del gasto** (D-075): **borrador** (no entra en ningún cálculo); **sin IA** (la lectura
  automática falló y espera carga manual: no entra en el cálculo y dispara la advertencia "hay N
  facturas sin cargar" de R34); **en revisión** (la IA leyó con alertas: dispara el bloqueante de R34);
  **aprobado** (entra en el cálculo).
- **Regla**: si falla la IA al leer una factura, el gasto queda **sin IA** y la emisión de los demás
  gastos aprobados sigue. Si falla la lectura del extracto, la preliquidación y la emisión siguen sin
  él (la conciliación se hace después). Lo que falte del encolado del PDF después de emitir se decide
  en el design del cambio 7 (D-047, punto 7).
- **Tests mínimos**: emitir con la IA caída no bloquea la liquidación; un gasto sin IA no entra en el
  cálculo y dispara la advertencia; un gasto en revisión dispara el bloqueante; emitir sin el extracto
  procesado no bloquea la liquidación (sólo posterga la conciliación).

## R33 · Datos completos y tipados antes de consultar el motor de reglas · Vigente (D-066, D-067)

- **Qué resuelve**: las tablas de decisión de ZEN eligen la fila por defecto en silencio si un dato
  llega con tipo incorrecto o falta (prueba del 13/10).
- **Regla**: el núcleo arma los datos de cada unidad con tipos fijos y verifica que estén todos
  antes de llamar al motor; la respuesta pasa por el validador (`13_motor_de_reglas.md`). Cualquier
  dato faltante, mal tipado o respuesta fuera de contrato bloquea la emisión con una alerta que dice
  qué regla y qué unidad.
- **Tests mínimos**: un dato numérico que llega como texto bloquea la emisión y no aplica la fila por
  defecto; un dato faltante bloquea la emisión; una respuesta con un monto como número en vez de
  texto se rechaza; una respuesta vacía se rechaza; una respuesta correcta se registra con su regla y
  versión en el motivo.

## R34 · Controles antes de emitir y emisión con alertas aceptadas · Vigente (D-069)

- **Qué resuelve**: emitir con un problema que nadie vio (saldos sin validar, una factura cargada dos
  veces, pagos sin confirmar que hacen figurar moroso a quien pagó).
- **Cómo funciona**: al preliquidar y al emitir, el sistema corre una lista de controles. Cada uno es
  **bloqueante** (no se puede emitir) o **advertencia** (se puede emitir y se muestra). Cada alerta
  dice qué pasa y dónde.
- **Emisión con alertas aceptadas**: con un bloqueo activo (salvo los controles duros), el administrador puede emitir igual sólo
  si confirma de forma explícita qué alertas acepta. Queda registrado quién, cuándo y cuáles. Es
  distinto del modo degradado (R24), que cubre la caída de un servicio externo.
- **Controles duros** (D-080, D-081, E5 del 3a): "saldos iniciales sin validar", "ingresos mayores que
  los gastos", "factura duplicada" y "coeficientes fuera de tolerancia" **no se pueden aceptar**: la
  emisión sólo sigue cuando se resuelven. Emitir sin los saldos iniciales
  confirmados dejaría la deuda vieja afuera del libro (R09, R40), y emitir con ingresos mayores que los
  gastos daría expensas negativas (R38). **Factura duplicada** también es duro (D-081): con la clave
  completa de R12 es la misma factura, y aceptarla repartiría el gasto dos veces. **Coeficientes fuera de tolerancia** es duro porque
  repartiría mal entre todas las unidades: R01 deja cargar el padrón sin bloquear y este control es el
  que la hace cumplir. El resto de los bloqueantes se puede aceptar con registro.
- **Una diferencia nunca se tapa**: no se carga un movimiento inventado para que un control dé bien.
- **Controles del MVP**:

  | Control | Se dispara cuando | Nivel | Cambio |
  |---|---|---|---|
  | Saldos iniciales sin validar | El edificio es nuevo y su estado de migración no es confirmada ni sin saldos previos (R09) | Bloqueante (duro) | 7 |
  | Factura duplicada | Dos gastos con el mismo CUIT del proveedor, punto de venta, tipo y número de comprobante (la clave de R12) | Bloqueante (duro) | 7 |
  | Coeficientes fuera de tolerancia | "Generales" o un grupo con coeficientes propios suma fuera de 1 ± 0,0001 (R01, D-082, D-100), según el mismo informe que da la API del cambio 3a | Bloqueante (duro) | 7 |
  | Facturas leídas por IA con alertas | Hay gastos **en revisión** por alertas de la lectura automática (D-075) | Bloqueante | 7 |
  | Facturas sin cargar | Hay gastos **sin IA**: la lectura falló y esperan carga manual (D-075, R24) | Advertencia | 7 |
  | Pagos sin confirmar | Hay pagos informados todavía sin confirmar: si se emite así, esos vecinos figuran morosos | Advertencia | 8 |
  | Unidades sin contacto válido *(propuesta, R28)* | Alguna unidad no tiene un email válido | Advertencia | 13 |
  | Extracto incompleto | El extracto procesado no llega a la fecha de cierre | Advertencia | 9 |
  | Gasto mensual obligatorio faltante *(propuesta, D-071)* | Falta este mes un gasto marcado como mensual obligatorio (abono del ascensor, seguro, sueldo del encargado) | Advertencia | 7 (el 6 expone la consulta) |
  | Ingresos mayores que los gastos *(propuesta, R38)* | Los ingresos de un grupo superan sus gastos **ordinarios** del período | Bloqueante (duro) | 7 (el 6 expone la consulta) |

  Las filas marcadas como propuesta entran sólo si se valida la regla que revisan.
  La lista y los controles sobre los gastos nacen en el cambio 7; los que revisan pagos, extractos o
  contactos los suma el cambio que construye eso (8, 9 y 13). El extracto es advertencia y no
  bloqueante porque en el MVP es una ayuda: los pagos entran por comprobante (D-017, R24).
- **Fuera del MVP**: medidores (D-026), diferencia entre caja y banco (D-023) y conexión de WhatsApp.
  Se suman a la lista cuando existan esas funciones.
- **Tests mínimos**: un bloqueo activo impide emitir; aceptarlo de forma explícita permite emitir y
  deja registro con usuario, fecha y alertas; una advertencia no impide emitir; una factura cargada
  dos veces dispara el bloqueo con proveedor, número y monto y no se puede aceptar; "ingresos mayores que
  los gastos" no se puede aceptar; un padrón que suma 0,9998 dispara "coeficientes fuera de tolerancia"
  con el grupo y la diferencia, y aceptarlo se rechaza; un edificio sin
  saldos confirmados no emite su primera liquidación, y aceptar esa alerta se rechaza: la emisión
  recién sigue cuando se confirman los saldos o se confirma "sin saldos previos" (R09); ningún control
  genera movimientos.

## R35 · Vencimiento en día inhábil · Propuesta (D-071)

- **Qué resuelve**: un vencimiento que cae sábado, domingo o feriado, cuando el vecino no puede hacer
  todos los trámites y los bancos no acreditan igual que un día hábil.
- **Propuesta**: si el vencimiento cae en un día inhábil, se corre al primer día hábil siguiente, y los
  intereses (R03) cuentan desde ese día. El PDF de la expensa muestra la fecha ya corrida.
- **Feriados** (D-082): los nacionales viven en un **calendario del sistema**, común a todos los
  edificios y actualizable cada año sin tocar la configuración de cada edificio (no en
  `parametros.yaml`, que sólo se copia al crear). Cada edificio puede sumar feriados provinciales o
  locales.
- **Tests mínimos**: un vencimiento en domingo pasa al lunes; un pago el lunes no genera interés; un
  vencimiento en un feriado seguido de fin de semana pasa al siguiente día hábil; un día hábil normal
  no se mueve.

## R40 · Los períodos se liquidan en orden · Propuesta (D-071)

- **Qué resuelve**: preliquidar mayo con abril sin emitir rompe los saldos arrastrados (R06) y los
  intereses.
- **Propuesta**: no se puede preliquidar ni emitir un período si el anterior no está emitido o
  distribuido (una liquidación anulada no cuenta). Única
  excepción: el primer período después de la migración (R09), que arranca desde los saldos
  iniciales confirmados.
- **Tests mínimos**: con abril sin emitir, preliquidar mayo se rechaza con un mensaje claro; con abril
  emitido, mayo se preliquida; el primer período después de la migración se puede emitir.

---

## Dominio: Pagos

## R11 · Registro de pagos en el MVP · Vigente (D-017) · a validar (P42)

- **Origen**: el vecino sube el comprobante desde el portal (o el administrador lo carga por él).
  Queda como **pago informado**, sin efecto sobre la deuda.
- **A qué unidad corresponde**: a la del vecino que lo sube (identidad autenticada, R10). Si la
  persona es contacto de varias unidades (departamento y cochera), elige una o reparte el pago
  entre ellas; cada parte se imputa en su unidad con R04. No se
  depende del comprobante: muchos no muestran el origen (BNA+ sólo muestra el destinatario) y el
  campo "motivo" suele decir "Varios".
- **Lectura**: cada banco o billetera tiene su formato y no traen QR. La IA lee el comprobante y
  precarga monto, fecha y hora, y número de operación; el vecino revisa y confirma esos datos.
- **Número de operación único**: no puede repetirse dentro del complejo. Un comprobante subido dos
  veces, o para dos unidades, se frena al subirlo.
- **Confirmación**: sólo el administrador lo pasa a **confirmado**. Nunca es automático. Al
  confirmarse se imputa con R04.
- **Rechazo**: el administrador puede rechazarlo con un motivo; el vecino lo ve.
- **Fecha del pago**: la fecha real de la transferencia (del comprobante, validada contra el
  extracto si existe), no la de confirmación. Es la que cuenta para los intereses (R03). Si entre la
  transferencia y la confirmación hubo una emisión que ya registró interés por esos días, al confirmar
  se registra automáticamente un **ajuste** (crédito con motivo, R08) por el interés cobrado de más
  (D-082, a validar con un administrador), **enlazado a ese pago y a la emisión cuyo interés compensa**. El ajuste sigue al interés
  (D-085): si se anula la emisión que registró ese interés, el ajuste queda excluido junto con él, sin
  contra-movimiento, aunque esa misma anulación también haga caer la imputación del pago; si el pago
  se revierte o se reimputa, el ajuste se revierte con un contra-movimiento (D-083).
- **Ayuda del extracto**: el administrador sube el extracto del banco (CSV o Excel) y el sistema
  marca para cada pago informado si encontró un movimiento coincidente (importe y fecha, más el
  CUIT de origen cuando el banco lo informa) o no.
  También muestra movimientos del banco sin comprobante, como fondos pendientes de identificar.
- **Duplicados**: un mismo movimiento del banco no puede confirmar dos pagos.
- **Datos de prueba**: comprobantes de ejemplo con datos inventados, en los formatos reales de
  BNA+ y Mercado Pago. Nunca comprobantes reales con datos personales en el repositorio.
- **Tests mínimos**: número de operación repetido se rechaza; pago informado no cambia la deuda;
  confirmado imputa con la fecha del comprobante; rechazado no imputa; un movimiento bancario no confirma dos pagos; pago confirmado
  tarde no genera intereses por los días de demora del administrador; un pago confirmado después de una
  emisión que cobró interés por días posteriores a la transferencia genera el ajuste exacto; un pago
  repartido entre el departamento y la cochera imputa cada parte en su unidad con R04.

## R18 · Estado "revertido" de un pago confirmado · Vigente (D-056) · extiende R11

- **Regla**: un pago **confirmado** puede pasar a **revertido** cuando el banco lo
  rechaza o lo devuelve después de confirmado (cheque rechazado, contracargo, transferencia
  revertida). El pago original nunca se borra ni pasa a "rechazado".
- **Efecto**: se registra un movimiento de **reversión de pago** (débito) que referencia al pago
  original, con motivo obligatorio (por ejemplo, "cheque rechazado, fondos insuficientes").
- **Morosidad**: al revertirse un pago, la unidad puede pasar a cumplir R20 (moroso crítico), que se
  calcula siempre desde el libro (D-074).
- **Movimientos enlazados**: si el pago tenía una bonificación por pronto pago (R37) o un ajuste de
  interés (R11) enlazados, se revierten con él (D-082, D-083).
- **Tests mínimos**: revertir un pago confirmado genera el contra-movimiento y sube la deuda; el pago
  original sigue visible con su nuevo estado; revertir un pago que no está confirmado se rechaza;
  después de revertir, la función de R20 marca a la unidad si ahora tiene dos o más liquidaciones
  vencidas con saldo; revertir un pago con bonificación o ajuste de interés enlazados revierte también
  esos movimientos.

## R19 · Identificación reforzada: código de unidad y CBU histórico · Vigente (D-057) · extiende R11

- **Código de unidad**: la boleta incluye un código corto de la unidad para que el vecino lo escriba
  en el concepto de la transferencia. Sólo cambia la plantilla de la boleta; no es obligatorio que el
  vecino lo use.
- **CBU histórico**: cuando el administrador confirma un pago y el CBU de origen se conoce (porque lo
  trae el comprobante o porque el pago se cruzó con el extracto), el sistema lo guarda asociado a esa
  unidad (cambio 8). La sugerencia por CBU aparece al cruzar el extracto (cambio 9): un movimiento del
  mismo CBU es una sugerencia para esa unidad.
- **Nunca asigna solo**: los dos mecanismos sólo generan una **sugerencia de confianza alta** en la
  bandeja de confirmación (HU-A6, HU-A7); el administrador siempre confirma con un clic (principio
  3 de Alberto). El primer pago de un CBU nuevo no tiene sugerencia por este mecanismo.
- **Tests mínimos**: un movimiento con el código de la unidad en el concepto aparece como sugerencia
  de esa unidad; un CBU que ya pagó por una unidad sugiere esa unidad el mes siguiente; ninguno de
  los dos confirma un pago sin que el administrador haga el clic; un CBU nuevo sin otra señal no
  genera sugerencia.

## R25 · Asistente de reimputación entre unidades · Propuesta (ProTecc B2)

- **Qué resuelve**: un pago confirmado en la unidad equivocada (el vecino de 7A cargó el pago a 7B).
- **Propuesta**: el pago original no se edita. Se generan, en una sola transacción, dos movimientos
  de **reimputación** enlazados: uno que resta en la unidad equivocada (restituye la deuda) y otro
  que suma como crédito en la unidad correcta, los dos con motivo obligatorio y referencia al pago
  original. Después, cada una de las dos unidades puede pasar a cumplir o dejar de cumplir R20, que se
  calcula desde el libro (D-074).
- **Tests mínimos**: reimputar genera los dos movimientos enlazados en una sola transacción; si falla
  un paso, no se aplica ninguno; después de reimputar, la función de R20 da el resultado correcto
  para las dos unidades.

## R37 · Condiciones de la bonificación por pronto pago · Propuesta (D-071)

- **Qué resuelve**: dejar escrito cuándo corresponde la bonificación por pronto pago (regla del motor,
  `13_motor_de_reglas.md`), para que dos edificios no la interpreten distinto.
- **Propuesta** (son los valores por defecto de la regla; cada edificio los ajusta en el editor):
  - Se bonifica sólo la **ordinaria prorrateada del período** (R13). Nunca la extraordinaria, los intereses ni
    los cargos particulares, y en especial **nunca una multa**.
  - Sólo si la unidad **no tenía deuda vencida** de períodos anteriores al día del pago.
  - Sólo si la transferencia es **hasta el día límite inclusive** y **cubre todo lo que la unidad debe
    del período** (ordinaria, extraordinaria, fondo y cargos particulares), con el descuento aplicado sólo
    a la ordinaria prorrateada (D-083). Un pago menor no bonifica.
  - Vale la fecha de la transferencia, no la de la confirmación (R11).
- **Cuándo se registra** (D-080): **al confirmar el pago** (cambio 8), como un movimiento de
  bonificación con su motivo, en la misma operación que la imputación y **enlazado a ese pago**
  (D-082). Si el pago se revierte (R18), se reimputa (R25) o su imputación deja de valer por una
  anulación (R17), la bonificación se revierte con él, con un contra-movimiento. La expensa (cambio 7) muestra
  los dos importes: "si pagás hasta el día X: $Y" y el total sin descuento.
- **Tests mínimos**: un pago del importe con descuento antes del límite bonifica y deja la ordinaria
  saldada; un pago menor no; una unidad con deuda anterior no bonifica aunque pague a término; una
  multa del período no se bonifica; un pago el día límite bonifica y uno al día siguiente no; el PDF
  muestra los dos importes; revertir un pago bonificado devuelve la deuda completa.

---

## Dominio: Morosidad y gestión de deuda

## R20 · Moroso crítico por antigüedad · Vigente (D-058, D-074)

- **Definición**: una unidad es **moroso crítico** cuando tiene **dos o más liquidaciones vencidas
  con saldo impago**, calculado desde las imputaciones (nunca desde una marca de "pagada").
- **Dónde vive** (D-074): es una función pura sobre el libro de la cuenta corriente y se construye en
  el cambio 4. No hay nada que "reevaluar": el resultado se deriva del libro cada vez que se pide. El
  cambio 10a se encarga del listado, la exportación y la presentación.
- **Saldo inicial** (D-080): la deuda traída al migrar cuenta. Si se cargó con detalle por período,
  cada período vencido cuenta como una liquidación vencida; si vino como un total único, cuenta como
  una sola.
- **No es por monto**: una fórmula por monto de deuda no se usa (se rompe porque la expensa cambia de
  mes a mes y los pagos parciales la confunden).
- **Exclusiones**: quedan excluidas las unidades con la deuda en **gestión judicial** (R31), cuando el
  cambio 10b construya esa marca y la agregue a esta función (D-078), y las **unidades del consorcio** (R39), si
  se valida. El plan de pago está fuera del
  MVP (`16_proyecto_final.md`, G1), así que esa exclusión queda como límite conocido.
- **Sin bloqueo de amenities**: las reservas de espacios comunes no están en el MVP, así que no hay
  ningún bloqueo asociado a esta marca.
- **Tests mínimos**: una unidad con una sola liquidación vencida no es moroso crítico; dos vencidas
  con saldo, sí; un pago parcial que no cubre ninguna por completo sigue contando esa liquidación
  como vencida; revertir un pago (R18) puede volver a marcar moroso crítico a una unidad; una unidad
  migrada con dos períodos vencidos en el saldo inicial es moroso crítico; un saldo inicial de total
  único cuenta como una sola liquidación vencida.

## R21 · Certificado de libre deuda · Vigente (D-059)

- **Qué es**: un certificado que resume la deuda de una unidad a una fecha de corte, para que el
  escribano pueda escriturar una venta sin esperar a que el administrador revise la cuenta a mano.
- **Contenido**: identificador único, fecha de corte, saldo de la unidad a esa fecha (calculado desde
  la cuenta corriente, nunca estimado), y los pagos informados todavía no confirmados, listados por
  separado como "en revisión" sin restarlos del saldo.
- **Nunca estima**: no incluye ningún gasto del período en curso que todavía no se liquidó.
- **Interés corrido** (D-081): si la fecha de corte es posterior a un vencimiento, el certificado informa
  en una línea aparte el interés corrido hasta esa fecha según R03, calculado y sin registrarlo en la
  cuenta corriente (se registra con la emisión siguiente).
- **Firma**: lo firma el super admin (antes, administrador titular).
- **Tests mínimos**: una unidad sin saldo pendiente genera "libre de deuda" con saldo cero; una unidad
  con saldo lo muestra a la fecha de corte exacta; un pago informado no confirmado aparece aparte,
  sin restar del saldo; el certificado no cambia si se generan gastos nuevos después de la fecha de
  corte; con un corte posterior al vencimiento, muestra el interés corrido en una línea aparte sin
  registrarlo en la cuenta corriente.

## R29 · Condonación de intereses · Propuesta (ProTecc B5, Q1)

- **Qué resuelve**: un recargo por mora que el vecino discute y el administrador decide perdonar,
  total o parcialmente.
- **Propuesta**: una condonación nunca borra el recargo original. Genera un movimiento de
  **condonación de interés** (crédito) que lo neutraliza, con motivo obligatorio y visible para el
  vecino (principio 7 de Alberto) y para el consejo.
- **Falta decidir** (Q1 de Alberto): si la condonación, que ejecutan el super admin o el administrador principal (D-106),
  necesita además aprobación del consejo por encima de un umbral. No se decide
  sin esa respuesta.
- **Tests mínimos** (a definir con la aprobación): una condonación genera el movimiento de crédito
  sin borrar el recargo; el vecino ve el motivo; después de condonar, la función de R20 da el
  resultado correcto para la unidad.

## R31 · Marca de gestión judicial · Propuesta (ProTecc G2)

- **Qué resuelve**: una deuda que ya está en manos del abogado del consorcio, donde un recordatorio
  automático de mora puede interferir con el juicio.
- **Propuesta**: marcar una unidad como "en gestión judicial" suspende los recordatorios automáticos
  de mora (HU-V6) y la excluye del cálculo de moroso crítico (R20).
  Las consultas de esa unidad se derivan al administrador.
- **Tests mínimos**: una unidad marcada no recibe el aviso automático de mora; no cuenta como moroso
  crítico aunque tenga dos o más liquidaciones vencidas; desmarcarla la vuelve a incluir en ambos
  cálculos.

## R32 · Cambio de titular a mitad de período · Pendiente (P11)

- **Qué resuelve**: una unidad que se vende o cambia de titular con un período en curso o con deuda
  anterior. Hoy ninguna regla dice a quién se le imputa cada cosa ni qué ve cada uno en el portal.
- **A definir**: si la expensa del período sigue a la unidad o a la persona; qué pasa con la deuda
  anterior y con el crédito a favor; cómo se relaciona con el certificado de libre deuda (R21).
- **Tests mínimos**: a definir cuando se responda P11.

## R41 · Baja de deuda incobrable · Propuesta (D-071)

- **Qué resuelve**: una deuda que el consorcio da por perdida (por ejemplo, después de un remate que no
  alcanzó a cubrirla) y que la asamblea decide dar de baja.
- **Propuesta**: el super admin o el administrador principal registra una **baja de deuda** sobre la unidad, con motivo y
  el respaldo adjunto (acta de asamblea u orden judicial). Es un movimiento nuevo (R08): la deuda
  original no se borra y la baja queda en un reporte propio de deudas dadas de baja. Sólo esos dos perfiles
  pueden hacerlo (D-106).
- **Alcance**: va junto con la marca de gestión judicial (R31); se decide si entra al MVP cuando se
  valide R31.
- **Tests mínimos**: la baja deja el saldo en cero sin borrar movimientos; sin respaldo adjunto se
  rechaza; un administrador por edificio no puede registrarla; aparece en el reporte de bajas.

---

## Dominio: Avisos

## R27 · Aviso que cae en fin de semana o feriado · Propuesta (ProTecc W3)

- **Qué resuelve**: un vencimiento o un recordatorio que cae en fin de semana o feriado.
- **Propuesta**: si la fecha del aviso cae en sábado, domingo o feriado, se envía el primer día hábil
  siguiente, dentro del horario que defina el cambio 13 `avisos-por-email`.
- **Tests mínimos**: un aviso que cae en domingo se reprograma al lunes (o al primer día hábil); un
  aviso en día hábil no se mueve.

## R28 · Validación de contactos y unidades sin contacto válido · Propuesta (ProTecc W4)

- **Qué resuelve**: un email inválido o inexistente que hace que ningún aviso llegue, sin que nadie
  se entere.
- **Propuesta**: validar el formato del contacto al cargarlo; si un envío rebota, marcar el contacto
  como inválido y mostrar al administrador una lista de "unidades sin contacto válido".
- **Tests mínimos**: un contacto con formato inválido se rechaza al cargarlo; un envío que rebota
  marca el contacto como inválido; la lista de unidades sin contacto válido incluye esa unidad.
