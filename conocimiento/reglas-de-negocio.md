# Reglas de negocio

Cómo se comporta el sistema con la plata. **Cada regla vigente se convierte en uno o más tests**
antes de que exista el código que la cumple. **Se reescribe** cuando una regla cambia; el
porqué del cambio va a `decisiones.md`.

Estados: **Pendiente** (no decidida) · **Propuesta** (hay una propuesta, falta validarla con un
administrador o contador) · **Vigente** (decidida y registrada en `decisiones.md`).

> Se completa en la charla de la pregunta P4.

---

## R01 · Prorrateo de gastos · Vigente (D-013)

- **Grupos de reparto**: cada complejo define sus grupos (por ejemplo "Generales", "Pileta",
  "Obra calle 5"). Cada grupo tiene:
  - las unidades que participan;
  - el método: por coeficiente, por superficie o en partes iguales.
- **Cada gasto se asigna a un grupo** y se reparte sólo entre sus unidades. El grupo dice **quién
  paga**; la categoría (R16) dice **en qué se gastó**. Son independientes.
- **Default**: un complejo nuevo arranca con un grupo "Generales", todas las unidades, por coeficiente.
- **Validación**: los coeficientes de un grupo suman 1. La tolerancia y dónde va la diferencia de
  redondeo se definen en R07.
- **Historia**: la liquidación guarda la composición de cada grupo usada en ese período.
- **Grupos típicos de un edificio**: Generales (todas las unidades), Ascensor (sin planta baja ni
  locales), Cocheras, Servicios centrales. En barrios: Generales, Pileta, Obra calle 5.
- **Tests mínimos**: gasto general entre todos; gasto de un grupo parcial no toca a los demás;
  partes iguales; la suma repartida es igual al gasto, al centavo.

## R02 · Estado de la unidad · Vigente (D-014) · desactivada por default en edificios (D-030)

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

## R03 · Intereses por mora · Vigente (D-010) · falta validar con un administrador

- **Tipo**: interés **simple**, siempre. No se cobra interés sobre interés (art. 770 del Código
  Civil y Comercial). No es configurable.
- **Base**: lo que sigue impago de cada obligación (su residual según R05). No es configurable.
- **Configurable por complejo** (menú cerrado, no fórmula libre):

  | Opción | Valores | Default |
  |---|---|---|
  | Tasa mensual | porcentaje | 3% |
  | Días de gracia | entero desde 0 | 0 |
  | Forma de cálculo | proporcional por día de atraso · mes entero al pasar el vencimiento | proporcional por día |

- **Cuándo se registra**: al emitir la liquidación siguiente, como un débito con su detalle
  (obligación, días, tasa, base). El número no cambia cada vez que el vecino entra al portal.
- **Historia**: cada liquidación guarda la configuración con la que se calculó. Cambiar la tasa
  no altera liquidaciones ya emitidas.
- **Tests mínimos**: pago parcial reduce la base; días de gracia no generan interés; cambio de
  tasa entre períodos; nunca hay interés calculado sobre un interés.

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

## R05 · Pagos parciales y excedentes · Vigente (D-012)

- **Qué define**: qué queda después de un pago que no cubre o que supera la deuda.
- **Regla**: cada imputación se registra; el residual de cada obligación se calcula a partir
  de sus imputaciones, nunca con una marca de "pagada" (análisis H04). El excedente queda como
  crédito a favor y se compensa en la siguiente liquidación (H07).

## R06 · Saldo arrastrado · Vigente (D-012)

- **Qué define**: cómo se muestra la deuda vieja en la expensa nueva sin cobrarla dos veces.
- **Regla**: la deuda vieja vive en sus obligaciones originales; la expensa nueva la **muestra**
  como saldo anterior pero no genera un débito nuevo por ella (análisis H06).

## R07 · Precisión y redondeo · Vigente (D-015, D-046)

- **Representación** (D-046): todo importe es `Decimal` en Python, construido desde texto
  (`Decimal("0.10")`, nunca `Decimal(0.1)`), `NUMERIC(14,2)` en la base y texto en el JSON. Nunca
  `float`. El frontend no calcula montos: sólo los formatea.
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

## R09 · Saldo inicial al migrar · Vigente (D-015, D-068)

- **Con detalle por período** (si el complejo lo tiene): se carga cada obligación vieja con su
  período y vencimiento; los intereses viejos se calculan con R03 como cualquier otra.
- **Sólo con un total**: se carga una obligación "saldo inicial" con vencimiento en la fecha de
  migración; los intereses corren desde ahí.
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
- **Tests mínimos**: saldo con detalle genera sus obligaciones; total único genera una sola;
  crédito negativo entra como crédito; la suma importada coincide con el archivo de origen; dos
  errores de signo opuesto en dos unidades (+10.000 y -10.000) dan el total correcto y aun así
  aparecen como dos diferencias; el borrador no genera movimientos hasta confirmar; aceptar
  diferencias deja registro; con el importador cerrado, un segundo intento de importar se rechaza.

## R10 · Aislamiento entre complejos · Vigente (D-016)

- **Regla**: todo dato pertenece a un complejo y ninguna consulta, archivo, caché o proceso
  devuelve datos de otro. El complejo sale de la identidad autenticada, nunca de un parámetro que
  manda el cliente (análisis H02, H14, H27).

## R11 · Registro de pagos en el MVP · Vigente (D-017)

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
  extracto si existe), no la de confirmación. Es la que cuenta para los intereses (R03).
- **Ayuda del extracto**: el administrador sube el extracto del banco (CSV o Excel) y el sistema
  marca para cada pago informado si encontró un movimiento coincidente (importe y fecha, más el
  CUIT de origen cuando el banco lo informa) o no.
  También muestra movimientos del banco sin comprobante, como fondos pendientes de identificar.
- **Duplicados**: un mismo movimiento del banco no puede confirmar dos pagos.
- **Datos de prueba**: comprobantes de ejemplo con datos inventados, en los formatos reales de
  BNA+ y Mercado Pago. Nunca comprobantes reales con datos personales en el repositorio.
- **Tests mínimos**: número de operación repetido se rechaza; pago informado no cambia la deuda;
  confirmado imputa con la fecha del comprobante; rechazado no imputa; un movimiento bancario no confirma dos pagos; pago confirmado
  tarde no genera intereses por los días de demora del administrador.

## R12 · Registro de gastos desde facturas · Vigente (D-019)

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
  gasto queda marcado como "sin QR" para que el administrador lo revise con más cuidado.
- **Factura duplicada**: `cuit + ptoVta + tipoCmp + nroCmp` no se repite dentro del complejo. Se frena al cargarla.
- **Receptor equivocado**: si `nroDocRec` existe y no es el CUIT del complejo, se avisa antes de confirmar.
- **Siempre borrador**: ningún dato leído (por QR o por IA) entra en la liquidación sin que el
  administrador confirme el gasto. La IA no inventa datos ausentes: los marca como faltantes.
- **Tests mínimos**: decodifica el ejemplo oficial de ARCA; acepta los dos dominios; rechaza un
  duplicado; avisa receptor distinto; moneda extranjera convierte con `ctz`; sin QR queda marcado.

## R13 · Expensa ordinaria y extraordinaria · Vigente (D-024)

- **Cada gasto se marca** como ordinario o extraordinario al cargarlo. Default: ordinario.
- **Una obligación por unidad y período**, con el capital desglosado en ordinario y extraordinario.
  La expensa del vecino los muestra en bloques separados, con su subtotal.
- **Imputación**: dentro del período, intereses, después ordinaria, después extraordinaria (R04).
- **Escala**: la separación queda guardada porque más adelante importa quién paga cada una
  (en Argentina, la extraordinaria suele corresponder al propietario y no al inquilino).
- **Tests mínimos**: un gasto extraordinario aparece en su bloque; los subtotales suman el total;
  un pago parcial cubre primero la ordinaria.

## R14 · Cargos particulares · Vigente (D-025)

- **Qué es**: un importe que se carga a una sola unidad (limpieza del quincho, una multa aprobada,
  un consumo, un arreglo que causó ese lote). Distinto del cargo fijo por estado (R02), que es mensual
  y automático.
- **Carga**: el administrador lo registra con unidad, concepto, importe, período y motivo; o los
  importa en lote desde un Excel (unidad, concepto, importe). Queda en borrador hasta aprobarlo.
- **Liquidación**: los aprobados del período entran en la expensa de esa unidad, como líneas propias
  dentro de la parte ordinaria, sin afectar el reparto de los demás.
- **Créditos particulares** (una bonificación, una devolución) no son cargos negativos: se registran
  como corrección (R08).
- **Tests mínimos**: un cargo particular sólo afecta a su unidad; no cambia lo que pagan los demás;
  la importación desde Excel rechaza unidades inexistentes; un cargo en borrador no entra.

## R15 · Fondo de reserva · Vigente (D-031)

- **Configurable por edificio**: un porcentaje sobre la expensa ordinaria del período. Default: 0%
  (sin fondo de reserva).
- **En la liquidación**: aparece como línea propia de la expensa de cada unidad, calculada sobre su
  ordinaria y redondeada con R07; la suma de las partes da exacto el total del fondo del período.
- **Imputación**: forma parte de la ordinaria (R04, R13).
- **Sin tesorería**: el sistema no lleva el saldo acumulado del fondo ni el saldo de caja (D-023).
- **Historia**: cada liquidación guarda el porcentaje usado.
- **Tests mínimos**: con 0% no aparece la línea; con 5% cada unidad paga el 5% de su ordinaria;
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

## R17 · Ventana de anulación antes de distribuir · Vigente (D-055) · refina R08

- **Regla**: una liquidación **emitida** se puede **anular** sólo mientras esté en estado emitida y
  todavía no distribuida. Se considera distribuida desde que sale el primer email de aviso al
  responsable de pago, o desde que alguien la ve en el portal, lo que pase primero.
- **Anulación**: requiere motivo obligatorio y queda registrada con responsable y fecha. No genera
  ninguna obligación ni movimiento de cuenta corriente (como si nunca se hubiera emitido).
- **Después de distribuida**: rige R08 sin excepciones. Ningún movimiento se edita ni se borra; todo
  error se corrige con un movimiento nuevo (ajuste).
- **Tests mínimos**: anular antes del primer envío borra la obligación sin dejar movimiento; intentar
  anular después de que un vecino la vio en el portal lo rechaza; la anulación sin motivo se
  rechaza; una liquidación anulada permite volver a emitir el período.

## R18 · Estado "revertido" de un pago confirmado · Vigente (D-056) · extiende R11

- **Regla**: un pago **confirmado** (o conciliado) puede pasar a **revertido** cuando el banco lo
  rechaza o lo devuelve después de confirmado (cheque rechazado, contracargo, transferencia
  revertida). El pago original nunca se borra ni pasa a "rechazado".
- **Efecto**: se registra un movimiento de **reversión de pago** (débito) que referencia al pago
  original, con motivo obligatorio (por ejemplo, "cheque rechazado, fondos insuficientes").
- **Morosidad**: al revertirse un pago, la unidad se reevalúa contra R20 (moroso crítico).
- **Tests mínimos**: revertir un pago confirmado genera el contra-movimiento y sube la deuda; el pago
  original sigue visible con su nuevo estado; revertir un pago que no está confirmado se rechaza;
  revertir vuelve a evaluar la morosidad de la unidad.

## R19 · Identificación reforzada: código de unidad y CBU histórico · Vigente (D-057) · extiende R11

- **Código de unidad**: la boleta incluye un código corto de la unidad para que el vecino lo escriba
  en el concepto de la transferencia. Sólo cambia la plantilla de la boleta; no es obligatorio que el
  vecino lo use.
- **CBU histórico**: cuando el administrador confirma un pago, el sistema guarda qué CBU lo originó,
  asociado a esa unidad. El mes siguiente, un movimiento del mismo CBU es una sugerencia para esa
  unidad.
- **Nunca asigna solo**: los dos mecanismos sólo generan una **sugerencia de confianza alta** en la
  bandeja de confirmación (HU-A6, HU-A7); el administrador siempre confirma con un clic (principio
  P3 de Alberto). El primer pago de un CBU nuevo no tiene sugerencia por este mecanismo.
- **Tests mínimos**: un movimiento con el código de la unidad en el concepto aparece como sugerencia
  de esa unidad; un CBU que ya pagó por una unidad sugiere esa unidad el mes siguiente; ninguno de
  los dos confirma un pago sin que el administrador haga el clic; un CBU nuevo sin otra señal no
  genera sugerencia.

## R20 · Moroso crítico por antigüedad · Vigente (D-058)

- **Definición**: una unidad es **moroso crítico** cuando tiene **dos o más liquidaciones vencidas
  con saldo impago**, calculado desde las imputaciones (nunca desde una marca de "pagada").
- **No es por monto**: una fórmula por monto de deuda no se usa (se rompe porque la expensa cambia de
  mes a mes y los pagos parciales la confunden).
- **Exclusiones**: quedan excluidas las unidades con un plan de pago al día o con la deuda en
  gestión judicial, **si esos conceptos existen en el MVP**. Hoy no existen (ver R31 y
  `proyecto-final.md`, G1): mientras no se construyan, la exclusión no se puede aplicar y queda
  anotada como límite conocido de esta regla.
- **Sin bloqueo de amenities**: las reservas de espacios comunes no están en el MVP, así que no hay
  ningún bloqueo asociado a esta marca.
- **Tests mínimos**: una unidad con una sola liquidación vencida no es moroso crítico; dos vencidas
  con saldo, sí; un pago parcial que no cubre ninguna por completo sigue contando esa liquidación
  como vencida; revertir un pago (R18) puede volver a marcar moroso crítico a una unidad.

## R21 · Certificado de libre deuda · Vigente (D-059)

- **Qué es**: un certificado que resume la deuda de una unidad a una fecha de corte, para que el
  escribano pueda escriturar una venta sin esperar a que el administrador revise la cuenta a mano.
- **Contenido**: identificador único, fecha de corte, saldo de la unidad a esa fecha (calculado desde
  la cuenta corriente, nunca estimado), y los pagos informados todavía no confirmados, listados por
  separado como "en revisión" sin restarlos del saldo.
- **Nunca estima**: no incluye ningún gasto del período en curso que todavía no se liquidó.
- **Firma**: lo firma el administrador titular.
- **Tests mínimos**: una unidad sin saldo pendiente genera "libre de deuda" con saldo cero; una unidad
  con saldo lo muestra a la fecha de corte exacta; un pago informado no confirmado aparece aparte,
  sin restar del saldo; el certificado no cambia si se generan gastos nuevos después de la fecha de
  corte.

## R22 · Nota de crédito asociada a la factura · Vigente (D-061) · extiende R12

- **Regla**: una nota de crédito de un proveedor queda **asociada a la factura que corrige** y su
  monto **no puede superar** el de esa factura.
- **Efecto en el gasto**: se descuenta del gasto antes de prorratear, dentro del mismo grupo de
  reparto de la factura original (no es un gasto negativo suelto).
- **Duplicados**: el control de factura duplicada de R12 (`cuit + ptoVta + tipoCmp + nroCmp`) suma el
  **tipo de comprobante**, porque una factura y su nota de crédito pueden compartir número al
  numerarse por separado.
- **Tests mínimos**: una nota de crédito menor al monto de la factura reduce el gasto repartido; una
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

## R24 · Modo degradado de emisión · Propuesta (ProTecc A4, principio P6)

- **Qué resuelve**: que la emisión de la liquidación no dependa de un servicio externo (lectura del
  extracto, IA de facturas). Si ese servicio falla el día de emitir, la liquidación tiene que poder
  salir igual.
- **Propuesta**: si falla la IA al leer una factura, el gasto queda marcado "sin IA" para carga
  manual, sin bloquear la emisión de los demás gastos ya aprobados; si falla la lectura del
  extracto, la preliquidación y la emisión siguen sin él (la conciliación se hace después).
- **Falta decidir**: el detalle se resuelve en el *design* del cambio 7 `liquidacion-y-emision`
  (D-047 punto 7 ya pedía definir qué pasa si falla el encolado del PDF; esta regla agrega qué pasa
  si falla el extracto o la IA el día de emitir).
- **Tests mínimos** (a definir en el design): emitir con la IA caída no bloquea la liquidación;
  emitir sin el extracto procesado no bloquea la liquidación (sólo posterga la conciliación).

## R25 · Asistente de reimputación entre unidades · Propuesta (ProTecc B2)

- **Qué resuelve**: un pago confirmado en la unidad equivocada (el vecino de 7A cargó el pago a 7B).
- **Propuesta**: el pago original no se edita. Se generan, en una sola transacción, dos movimientos
  de **reimputación** enlazados: uno que resta en la unidad equivocada (restituye la deuda) y otro
  que suma como crédito en la unidad correcta, los dos con motivo obligatorio y referencia al pago
  original. Se reevalúa la morosidad (R20) de las dos unidades.
- **Tests mínimos**: reimputar genera los dos movimientos enlazados en una sola transacción; si falla
  un paso, no se aplica ninguno; las dos unidades se reevalúan contra R20 después de reimputar.

## R26 · Recargo escalonado por primer y segundo vencimiento · Pendiente (ProTecc G4, Q9) · alternativa a R03

- **Qué resuelve**: Alberto describe un esquema de primer y segundo vencimiento con un recargo que
  escala entre uno y otro, distinto del interés simple continuo desde un único vencimiento que ya
  tiene R03.
- **Pendiente**: preguntarle a Alberto si el edificio piloto usa este esquema antes de tocar R03, que
  ya está marcada "falta validar". No se decide sin esa respuesta.
- **Tests mínimos**: a definir si se confirma el esquema.

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

## R29 · Condonación de intereses · Propuesta (ProTecc B5, Q1)

- **Qué resuelve**: un recargo por mora que el vecino discute y el administrador decide perdonar,
  total o parcialmente.
- **Propuesta**: una condonación nunca borra el recargo original. Genera un movimiento de
  **condonación de interés** (crédito) que lo neutraliza, con motivo obligatorio y visible para el
  vecino (P7) y para el consejo.
- **Falta decidir** (Q1 de Alberto): quién aprueba la condonación (el administrador solo, con
  auditoría posterior, o un nivel de aprobación del consejo por encima de un umbral). No se decide
  sin esa respuesta.
- **Tests mínimos** (a definir con la aprobación): una condonación genera el movimiento de crédito
  sin borrar el recargo; el vecino ve el motivo; la unidad se reevalúa contra R20 después de
  condonar.

## R30 · Umbral mínimo de saldos por redondeo · Propuesta (ProTecc D3) · extiende R07

- **Qué resuelve**: saldos chicos (a favor o en contra) que quedan de intereses o pagos parciales,
  por debajo de lo que tiene sentido reclamar o devolver.
- **Propuesta**: definir un umbral mínimo (por ejemplo, configurable por edificio) por debajo del
  cual el saldo no genera reclamo de cobranza ni devolución automática, y se arrastra con R06 hasta
  que se acumula o se liquida junto con otro movimiento.
- **Falta decidir**: el valor del umbral y si es fijo o configurable por edificio.
- **Tests mínimos** (a definir con el umbral): un saldo por debajo del umbral no dispara un aviso de
  mora; un saldo por encima sigue el camino normal de R03/R20.

## R31 · Marca de gestión judicial · Propuesta (ProTecc G2)

- **Qué resuelve**: una deuda que ya está en manos del abogado del consorcio, donde un recordatorio
  automático de mora puede interferir con el juicio.
- **Propuesta**: marcar una unidad como "en gestión judicial" suspende los recordatorios automáticos
  de mora (HU-V6) y la excluye del cálculo de moroso crítico (R20), igual que un plan de pago al día.
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

## R33 · Datos completos y tipados antes de consultar el motor de reglas · Vigente (D-066, D-067)

- **Qué resuelve**: las tablas de decisión de ZEN eligen la fila por defecto en silencio si un dato
  llega con tipo incorrecto o falta (prueba del 13/10).
- **Regla**: el núcleo arma los datos de cada unidad con tipos fijos y verifica que estén todos
  antes de llamar al motor; la respuesta pasa por el validador (`motor-de-reglas.md`). Cualquier
  dato faltante, mal tipado o respuesta fuera de contrato bloquea la emisión con una alerta que dice
  qué regla y qué unidad.
- **Tests mínimos**: un dato numérico que llega como texto bloquea la emisión y no aplica la fila por
  defecto; un dato faltante bloquea la emisión; una respuesta con un monto como número en vez de
  texto se rechaza; una respuesta vacía se rechaza; una respuesta correcta se registra con su regla y
  versión en el motivo.

## R34 · Controles antes de emitir y emisión con alertas aceptadas · Vigente (D-069)

- **Qué resuelve**: emitir con un problema que nadie vio (saldos sin validar, una factura cargada dos
  veces, pagos sin asignar que hacen figurar moroso a quien pagó).
- **Cómo funciona**: al preliquidar y al emitir, el sistema corre una lista de controles. Cada uno es
  **bloqueante** (no se puede emitir) o **advertencia** (se puede emitir y se muestra). Cada alerta
  dice qué pasa y dónde.
- **Emisión con alertas aceptadas**: con un bloqueo activo, el administrador puede emitir igual sólo
  si confirma de forma explícita qué alertas acepta. Queda registrado quién, cuándo y cuáles. Es
  distinto del modo degradado (R24), que cubre la caída de un servicio externo.
- **Una diferencia nunca se tapa**: no se carga un movimiento inventado para que un control dé bien.
- **Controles del MVP**:

  | Control | Se dispara cuando | Nivel | Cambio |
  |---|---|---|---|
  | Saldos iniciales sin validar | El edificio es nuevo y la migración no está confirmada (R09) | Bloqueante | 7 |
  | Factura duplicada | Dos gastos con el mismo proveedor, punto de venta y número de comprobante | Bloqueante | 7 |
  | Facturas leídas por IA con alertas | Hay gastos en revisión por alertas de la lectura automática | Bloqueante | 14 |
  | Pagos sin asignar | Hay pagos informados sin confirmar o sin unidad: si se emite así, esos vecinos figuran morosos | Advertencia | 8 |
  | Unidades sin contacto válido | Alguna unidad no tiene un email válido (R28) | Advertencia | 13 |
  | Extracto incompleto | El extracto procesado no llega a la fecha de cierre | Advertencia | 9 |

  Cada control entra con el cambio que construye lo que revisa. El extracto es advertencia y no
  bloqueante porque en el MVP es una ayuda: los pagos entran por comprobante (D-017, R24).
- **Fuera del MVP**: medidores (D-026), diferencia entre caja y banco (D-023) y conexión de WhatsApp.
  Se suman a la lista cuando existan esas funciones.
- **Tests mínimos**: un bloqueo activo impide emitir; aceptarlo de forma explícita permite emitir y
  deja registro con usuario, fecha y alertas; una advertencia no impide emitir; una factura cargada
  dos veces dispara el bloqueo con proveedor, número y monto; un edificio sin saldos confirmados no
  emite su primera liquidación sin aceptar la alerta; ningún control genera movimientos.

