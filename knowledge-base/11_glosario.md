# Glosario

El idioma común del proyecto. Si una palabra se usa en código, tests, specs o charlas con
administradores, significa lo que dice acá. **Se reescribe** cuando un término cambia.

> Las tres palabras que más confunden: una expensa **emitida** no está **pagada**; un pago
> **acreditado** no está **imputado**; una unidad **al día** no es lo mismo que una con
> **crédito a favor**. La mitad de los bugs de la especificación original nacieron de mezclarlas.

## La interfaz

- **Ayuda de pantalla ("?")**: el botón que tiene toda pantalla, junto a su título, y que abre una
  explicación didáctica en tres partes: para qué sirve la pantalla, qué se hace ahí y qué pasa
  después. Obligatoria en todas (D-102, HU-T1).

## El complejo y sus partes

- **Administración**: el cliente que paga PropTech: una empresa o persona que administra uno o varios complejos. Es el **tenant**: todo dato pertenece a una administración y ninguna ve los datos de otra (R10, D-076).
- **Complejo**: la comunidad que se administra, siempre dentro de una administración. En el MVP es un **edificio** en propiedad horizontal; después también un **barrio privado** (o country). Es un **alcance**: cada persona ve los complejos que le permite su perfil (D-076, D-106). Un barrio con torres o sectores es un solo consorcio; sus sectores son grupos de reparto (D-106). En el modelo de datos de la especificación se llamaba `consorcios`.
- **Consorcio**: en sentido legal, el conjunto de propietarios de un edificio en propiedad horizontal, con CUIT propio. En los barrios suele ser una asociación civil o similar.
- **Unidad funcional (UF)**: el objeto sobre el que se liquida la expensa. En un edificio, un departamento (piso y letra), una cochera, una baulera o un local; en un barrio, un **lote** (manzana y número). Su identificador sólo es único dentro de su complejo.
- **Tipo de unidad**: departamento, cochera, baulera o local en un edificio; lote en un barrio. Cada una tiene su coeficiente y se liquida por separado.
- **Estado de la unidad**: baldío, en obra, habitado o desocupado. Se usa en barrios; en edificios está desactivado.
- **Propietario**: titular de una unidad; ve todas sus expensas. Puede haber varios propietarios con cuenta propia para la misma unidad. **Inquilino**: ocupa la unidad y ve sólo sus expensas ordinarias. Son valores de `vinculo` en la relación persona-unidad, no atributos de la persona (D-106). **Usuario**: la persona que entra al sistema; puede tener varias unidades y vínculos distintos.

## Las personas

- **Super admin**: perfil que administra toda la empresa, incluidos edificios, usuarios y roles.
- **Administrador**: opera y configura los edificios de su alcance; emite liquidaciones y confirma pagos.
- **Administrador principal**: administrador con alcance sobre toda la empresa. Además puede anular,
  revertir o reimputar, condonar, dar de baja deuda, aceptar alertas bloqueantes y confirmar "sin saldos
  previos", igual que el super admin (D-106).
- **Administrador por edificio**: el mismo perfil, limitado a sus edificios asignados; configura y emite,
  pero las correcciones reservadas requieren super admin o administrador principal.
- **Contador**: perfil de lectura contable, principal o por edificio; exporta cuando el módulo lo ofrece.
- **Auxiliar**: perfil de sólo lectura por edificio.
- **Consejo** o **comisión directiva**: propietarios que controlan las cuentas; en el sistema sólo leen
  gastos, liquidaciones, comprobantes, morosidad y configuración. Una asignación por persona y edificio
  (RR-3); la aprobación adicional para condonar por encima de un umbral sigue abierta (P20).
- **Vecino**: propietario o inquilino que usa el portal e informa pagos de sus unidades.
- **Alcance**: qué parte de la administración cubre una asignación. Principal significa toda la
  empresa (`complejo_id` nulo); por edificio, el complejo asignado; por unidad, la del vínculo vecino.
  Principal y por edificio son alcances del mismo perfil, no roles distintos.
- **Titular y colaborador (vocabulario anterior al 20/10/2026)**: "titular" en specs y decisiones
  anteriores significa super admin. Colaborador que editaba pasó a administrador por edificio;
  colaborador que sólo veía, a auxiliar. El titular de una unidad sigue significando propietario.
- **Encargado** (edificio) o **intendente** (barrio): personal que reporta novedades y da conformidad de trabajos. En el MVP, su sueldo entra como gasto desde el recibo del contador (D-028).
- **Proveedor**: quien presta un servicio y factura al complejo.

## Gastos y reparto

- **Gasto**: un comprobante de proveedor asociado a un período, un concepto, un importe, una categoría (R16) y un grupo de reparto (R01). Tiene cuatro estados: **borrador** (cargado sin aprobar), **sin IA** (la lectura automática falló y espera carga manual), **en revisión** (la IA leyó con alertas) y **aprobado** (confirmado por el administrador). Sólo el aprobado entra en la liquidación (D-075).
- **Categoría de gasto** (antes "centro de costo"): en qué se gasta la plata (seguridad, limpieza, ascensor...). La define el administrador; ordena la expensa y los reportes, no cambia los cálculos (R16). No confundir con el grupo de reparto, que dice quién paga.
- **Archivo de parámetros**: `config/parametros.yaml`, con los valores con que arranca cada edificio nuevo (D-042).
- **Gasto común**: se reparte entre varias unidades. **Cargo particular**: se carga a una sola unidad (por ejemplo, la limpieza del quincho que usó, R14).
- **Expensa ordinaria**: la de la operación habitual. **Expensa extraordinaria**: la de una obra o necesidad puntual.
- **Coeficiente**: la proporción con la que una unidad participa de un grupo de reparto. La suma de los coeficientes de un grupo es 1 (100%), con una tolerancia de ±0,0001 (R01).
- **Grupo de reparto**: conjunto de unidades que comparten un tipo de gasto, con su método de reparto (coeficiente, superficie o partes iguales). Todo complejo tiene al menos el grupo "Generales" (R01).
- **Factor por estado**: el porcentaje con que una unidad participa del reparto según su estado (por ejemplo, baldío al 50%). La diferencia la absorben las demás unidades del grupo (R02).
- **Cargo fijo por estado**: un débito mensual propio de la unidad según su estado (por ejemplo, canon de obra) (R02).
- **Prorrateo**: repartir un gasto entre las unidades según su coeficiente, su superficie o en partes iguales.
- **Fondo de reserva**: en el MVP, un porcentaje sobre la **ordinaria prorrateada** que se cobra como línea propia (R15). El sistema no lleva su saldo acumulado.
- **Ordinaria prorrateada**: la parte de cada unidad en los gastos ordinarios de sus grupos, neta de notas de crédito e ingresos; sin cargos particulares, intereses ni fondo. Es la base del fondo de reserva y de la bonificación (R13, D-081).
- **Fondo**: de dónde sale y adónde va la plata (operativo, de reserva, de obras). No son lo mismo; en el MVP el fondo de reserva es sólo un concepto de la expensa (D-031).

## Liquidación

- **Período**: el mes que se liquida.
- **Preliquidación**: el cálculo provisorio que el administrador revisa antes de emitir. No genera deuda.
- **Emisión** (o liquidación emitida): genera la **obligación** de cada unidad para el período y su comprobante.
- **Distribución** (o liquidación distribuida): el momento en que la liquidación llega a los vecinos, por la acción "distribuir" del administrador, el primer email o la primera vista en el portal. Desde ahí no se puede anular (R17, D-074).
- **Anulación**: pasar una liquidación emitida y no distribuida a anulada. Es un cambio de estado: no borra movimientos y la deuda queda como antes de emitir (D-073).
- **Obligación**: lo que una unidad debe por un período, con el capital desglosado en ordinario y extraordinario (R13). Los cargos particulares van dentro de la ordinaria (R14) y los intereses se registran como débitos aparte (R03).
- **Liquidación**: el cálculo de todo un período para un edificio. Se preliquida, se emite y se distribuye. **Expensa** (o boleta): lo que le toca a una unidad en una liquidación, con su PDF.
- **Vencimiento**: la fecha a partir de la cual corre la mora. Si cae en un día inhábil, se corre al primer día hábil siguiente (R35, propuesta).
- **Ingreso del consorcio**: lo que el consorcio cobra (alquiler de una cochera común, de la terraza, el SUM a terceros). Se resta de los gastos ordinarios de su grupo antes de repartir (R38, propuesta).
- **Unidad del consorcio**: una unidad que pertenece al propio consorcio, como la portería. No genera intereses (R39, propuesta).
- **Baja de deuda**: dar por perdida una deuda incobrable, con respaldo, sin borrar los movimientos (R41, propuesta).
- **Puerto de políticas**: la única entrada por la que el reglamento propio de cada edificio llega a la liquidación. Recibe hechos y devuelve acciones propuestas; el núcleo las valida y las registra (D-064, `13_motor_de_reglas.md`).
- **Regla (del motor)**: una regla propia de un edificio, dibujada en el editor visual (jdm-editor) y guardada en formato JDM; la ejecuta GoRules ZEN. Decide qué corresponde y puede calcular, siempre devolviendo la plata como texto; el redondeo al centavo lo hace el núcleo (D-066, D-067). No confundir con las reglas de negocio R01 a R41, que viven en código (`05_reglas_de_negocio.md`). Detalle completo del motor en `13_motor_de_reglas.md`.
- **Validador (de reglas)**: el control propio que revisa cada regla al guardarla y cada respuesta del motor al evaluarla. Si algo no cumple el contrato, bloquea la emisión (D-066).
- **Acción propuesta**: lo que devuelve el motor: un cargo, una bonificación o una alerta, con monto en texto y motivo. No es un movimiento hasta que el núcleo la valida.
- **Versión de reglas**: las reglas de un edificio en un momento dado. Cada cambio crea una nueva; cada liquidación guarda las que usó.
- **Certificado de libre deuda**: la constancia, para una venta, del saldo de una unidad a una fecha
  de corte. Lo firma el administrador; nunca incluye una estimación de gastos del período en curso
  (R21).

## Cuenta corriente y pagos

- **Cuenta corriente**: el historial de débitos y créditos de una unidad. El saldo sale de ahí, nunca se guarda suelto.
- **Débito**: aumenta lo que la unidad debe (emisión, interés, cargo). **Crédito**: lo disminuye (pago, corrección, condonación). La nota de crédito de un proveedor no es un crédito de la unidad: reduce el gasto antes de prorratear (R22).
- **Pago**: plata que entra para una unidad. Tiene una fecha real y un canal.
- **Comprobante de pago**: la captura o el PDF de una transferencia que sube el vecino. No es una factura.
- **Pago informado**: un pago que el vecino declaró subiendo su comprobante. No afecta la deuda (R11).
- **Pago confirmado**: un pago informado que el administrador aprobó. Recién ahí se imputa (R11).
- **Pago rechazado**: un pago informado que el administrador descartó, con motivo visible para el vecino.
- **Pago revertido**: un pago confirmado que el banco devuelve después (cheque rechazado, contracargo,
  transferencia revertida). Nunca se borra ni pasa a rechazado: queda en estado revertido y genera un
  contra-movimiento que vuelve a subir la deuda (R18).
- **CBU histórico**: los CBU que pagaron cada unidad, guardados cuando se conocen. Al cruzar el
  extracto, un movimiento de uno de esos CBU se sugiere para esa unidad; nunca se asigna solo (R19).
- **Código de unidad**: el código corto de una unidad que la boleta sugiere escribir en el concepto
  de la transferencia, para identificar el pago sin tocar el modelo de datos (R19).
- **Reimputación**: dos movimientos enlazados que corrigen un pago confirmado en la unidad
  equivocada: restan en la unidad donde se cargó por error y suman como crédito en la correcta (R25).
- **Número de operación**: el identificador de la transferencia en el comprobante. No se repite dentro de un complejo (R11).
- **Extracto**: el listado de movimientos de la cuenta bancaria del consorcio, que el administrador sube para validar los pagos informados.
- **Acreditación**: el momento en que la plata llega a la cuenta del complejo.
- **Imputación**: asignar un pago, total o parcialmente, a una o varias obligaciones. Un pago puede tener varias imputaciones.
- **Pago parcial**: cubre parte de una obligación; queda un residual pendiente.
- **Crédito a favor**: lo que sobra de un pago después de imputarlo; se compensa en la próxima liquidación.
- **Saldo inicial**: la deuda o el crédito con que una unidad entra al sistema al migrar.
- **Corrección**: un movimiento nuevo con motivo y responsable. Nunca se edita un movimiento existente.

## Facturas de proveedores

- **Factura**: el comprobante que emite un proveedor al consorcio. Origina un gasto. No confundir con el comprobante de pago del vecino.
- **QR de ARCA**: el código obligatorio de toda factura electrónica. Contiene fecha, CUIT del emisor, punto de venta, tipo y número de comprobante, importe, moneda, receptor y código de autorización (R12).
- **CAE**: el código de autorización que ARCA otorga a cada factura electrónica.
- **Factura duplicada**: la que repite CUIT del emisor, punto de venta, tipo y número dentro del mismo complejo (R12).
- **Nota de crédito**: el comprobante de un proveedor que corrige una factura ya cargada. Queda
  asociada a esa factura y su monto no puede superarla; se descuenta del gasto antes de prorratear
  (R22).

## Mora

- **Mora**: atraso en el pago después del vencimiento.
- **Interés por mora**: el recargo que genera la mora, según la política del complejo.
- **Anatocismo**: cobrar intereses sobre intereses. El art. 770 del Código Civil y Comercial lo limita.
- **Moroso crítico**: una unidad con dos o más liquidaciones vencidas con saldo impago, calculado
  desde las imputaciones. Se define por antigüedad, nunca por monto (R20). En el MVP no bloquea
  amenities porque las reservas no están en el alcance.
- **Gestión judicial**: marca de una unidad cuya deuda ya está en manos del abogado del complejo.
  Frena los recordatorios automáticos de mora y la saca del cálculo de moroso crítico (R31, propuesta).
- **Condonación de interés**: un movimiento que neutraliza un recargo por mora, total o parcialmente,
  con motivo obligatorio. Nunca borra el recargo original (R29, propuesta).
- **Ventana de anulación**: el período acotado en que una liquidación emitida se puede anular en vez
  de corregir: mientras esté emitida y todavía no distribuida a ningún vecino (R17).

## Cobro y conciliación

- **Medio de cobro** (o canal): Mercado Pago, transferencia, y más adelante recaudadores como Red Link o Rapipago.
- **Referencia de pago**: el dato que liga un pago con su unidad y período (en Mercado Pago, `external_reference`).
- **Conciliación**: cruzar los movimientos del banco o del recaudador con los pagos e imputaciones.
- **Rendición**: el archivo que entrega un recaudador con los pagos que cobró.
- **Fondo pendiente de identificar**: un pago recibido que todavía no se pudo asignar a una unidad.

## Términos de las reglas de plata

- **Mayor resto**: el método de reparto que redondea cada parte al centavo y asigna los centavos que faltan, de a uno, a las unidades con mayor fracción descartada. La suma da siempre exacta (R07).
- **Ajuste de interés**: el crédito que se registra al confirmar un pago cuando una emisión ya había cobrado interés por días posteriores a la transferencia. Queda enlazado al pago y a esa emisión (R11).
- **Bonificación por pronto pago**: el descuento sobre la ordinaria prorrateada para quien paga todo lo del período hasta el día límite. Se registra al confirmar el pago (R37, propuesta).
- **Control bloqueante**: un control antes de emitir que impide emitir; si es **duro**, no se puede aceptar (saldos iniciales sin validar, factura duplicada, ingresos mayores que los gastos). Una **advertencia** sólo avisa (R34).
- **Gasto mensual obligatorio**: un gasto que tiene que aparecer todos los meses (el abono del ascensor, el seguro); si falta, hay una advertencia antes de emitir (R34, propuesta; dónde se marca: P37).
- **Doble vencimiento**: el esquema de primer y segundo vencimiento con recargo escalonado, alternativa a R03 que todavía no se decidió (R26, P19).

## Términos técnicos

- **Libro de movimientos**: la cuenta corriente de cada unidad, donde los movimientos sólo se agregan (R08).
- **Residual**: lo que queda impago de una obligación: su importe menos todas sus imputaciones (R05).
- **Saldo arrastrado**: la deuda vieja que la expensa nueva muestra sin volver a cobrarla (R06).
- **Fecha valor**: la fecha de la transferencia, que es la que cuenta para los intereses, distinta de la fecha en que se confirma el pago (R11).
- **Link firmado**: un enlace de descarga que vence y deja de funcionar si se modifica (D-070).
- **Cargo recurrente**: un cargo particular que se repite cada período para ciertas unidades (R14, propuesta).
- **Worker**: el proceso que hace de fondo el trabajo lento (PDFs, emails, IA), tomándolo de la cola de Redis.
- **Trabajo / tarea del worker**: una unidad de trabajo encolada en Redis para que el worker la ejecute aparte de la API (por ejemplo, la tarea de prueba del cambio 1c); se identifica con su clave de idempotencia y su número de seguimiento.
- **Idempotencia**: que repetir una tarea no duplique su efecto.
- **Clave de idempotencia**: el identificador propio de una tarea (armado por quien la encola, a partir de datos estables de la operación, nunca de la hora) que la cola y la base usan para no ejecutarla ni registrarla dos veces.
- **Número de seguimiento (`request_id`)**: el identificador (UUID) que acompaña cada pedido de punta a punta (Caddy, la web, la API, la base y el worker) y que aparece en cada línea de log para reconstruir su historia.
- **RLS** (Row-Level Security): el filtro de PostgreSQL que deja a cada administración ver sólo sus filas (R10).
- **Respaldo y restauración**: la copia diaria de la base y la forma de volver a cargarla en otra base para probarla (cambio 1d).

