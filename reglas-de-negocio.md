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

## R07 · Precisión y redondeo · Vigente (D-015)

- **Representación**: todos los montos en **centavos enteros**. Nunca `float`.
- **Reparto**: cada parte se redondea al centavo; la diferencia hasta el total exacto se asigna de
  a un centavo a las unidades con mayor fracción descartada (método del mayor resto). En empate,
  por orden de identificador de la unidad, para que el resultado sea determinista.
- **Garantía**: la suma de las partes es siempre igual al gasto, al centavo; ninguna unidad se
  aparta más de un centavo de su parte exacta.
- **Intereses**: se calculan con precisión completa y se redondean al centavo una sola vez, al registrarse.
- **Tests mínimos**: $1.000.000 entre 150 unidades suma exacto; empate de fracciones es
  determinista; un reparto entre 1 unidad devuelve el total.

## R08 · Correcciones · Vigente (D-016)

- **Regla**: ningún movimiento de la cuenta corriente se edita ni se borra. Una corrección es
  un movimiento nuevo con motivo, responsable y referencia al que corrige (análisis H03, H16).

## R09 · Saldo inicial al migrar · Vigente (D-015)

- **Con detalle por período** (si el complejo lo tiene): se carga cada obligación vieja con su
  período y vencimiento; los intereses viejos se calculan con R03 como cualquier otra.
- **Sólo con un total**: se carga una obligación "saldo inicial" con vencimiento en la fecha de
  migración; los intereses corren desde ahí.
- **Crédito a favor**: entra como crédito y se compensa en la primera liquidación.
- **Trazabilidad**: cada saldo inicial guarda el archivo y la fila de origen.
- **Tests mínimos**: saldo con detalle genera sus obligaciones; total único genera una sola;
  crédito negativo entra como crédito; la suma importada coincide con el archivo de origen.

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
