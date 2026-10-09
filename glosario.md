# Glosario

El idioma común del proyecto. Si una palabra se usa en código, tests, specs o charlas con
administradores, significa lo que dice acá. **Se reescribe** cuando un término cambia.

> Las tres palabras que más confunden: una expensa **emitida** no está **pagada**; un pago
> **acreditado** no está **imputado**; una unidad **al día** no es lo mismo que una con
> **crédito a favor**. La mitad de los bugs de la especificación original nacieron de mezclarlas.

## El complejo y sus partes

- **Complejo**: la comunidad que se administra. Puede ser un **barrio privado** (o country) o un **edificio** en propiedad horizontal. En el modelo de datos de la especificación se llamaba `consorcios`.
- **Consorcio**: en sentido legal, el conjunto de propietarios de un edificio en propiedad horizontal, con CUIT propio. En los barrios suele ser una asociación civil o similar.
- **Unidad funcional (UF)**: el objeto sobre el que se liquida la expensa. En un barrio es un **lote** (manzana y número); en un edificio, un departamento (piso y letra). Su identificador sólo es único dentro de su complejo.
- **Tipo de unidad**: departamento, cochera, baulera o local en un edificio; lote en un barrio. Cada una tiene su coeficiente y se liquida por separado.
- **Estado de la unidad**: baldío, en obra, habitado o desocupado. Se usa en barrios; en edificios está desactivado.
- **Propietario**: el titular de la unidad. **Inquilino**: quien la ocupa sin ser titular. **Usuario**: la persona que entra al sistema; una misma persona puede tener varias unidades.

## Las personas

- **Administrador**: opera el complejo y es el comprador de PropTech.
- **Consejo** o **comisión directiva**: propietarios que controlan las cuentas y autorizan gastos.
- **Vecino**: propietario o inquilino que usa el portal.
- **Intendente** (barrio) o **encargado** (edificio): personal que reporta novedades y da conformidad de trabajos. En el MVP, su sueldo entra como gasto desde el recibo del contador (D-028).
- **Proveedor**: quien presta un servicio y factura al complejo.

## Gastos y reparto

- **Gasto**: un comprobante de proveedor asociado a un período, un concepto, un importe y un centro de costo. Pasa por **borrador** (cargado o leído por IA) y **aprobado** (confirmado por el administrador). Sólo el aprobado entra en la liquidación.
- **Categoría de gasto**: en qué se gasta la plata (seguridad, limpieza, ascensor...). La define el administrador; ordena la expensa y los reportes, no cambia los cálculos (R16). No confundir con el grupo de reparto, que dice quién paga.
- **Archivo de parámetros**: `config/parametros.yaml`, con los valores con que arranca cada edificio nuevo (D-042).
- **Gasto común**: se reparte entre varias unidades. **Gasto particular**: se carga a una sola (por ejemplo, la limpieza del quincho que usó).
- **Expensa ordinaria**: la de la operación habitual. **Expensa extraordinaria**: la de una obra o necesidad puntual.
- **Coeficiente**: la proporción con la que una unidad participa de un grupo de reparto. La suma de los coeficientes de un grupo es 1 (100%).
- **Grupo de reparto**: conjunto de unidades que comparten un tipo de gasto, con su método de reparto (coeficiente, superficie o partes iguales). Todo barrio tiene al menos el grupo "Generales" (R01).
- **Factor por estado**: el porcentaje con que una unidad participa del reparto según su estado (por ejemplo, baldío al 50%). La diferencia la absorben las demás unidades del grupo (R02).
- **Cargo fijo por estado**: un débito mensual propio de la unidad según su estado (por ejemplo, canon de obra) (R02).
- **Prorrateo**: repartir un gasto entre las unidades según su coeficiente, su superficie o en partes iguales.
- **Fondo de reserva**: en el MVP, un porcentaje sobre la expensa ordinaria que se cobra como línea propia (R15). El sistema no lleva su saldo acumulado.
- **Centro de costo**: clasifica el gasto (seguridad, parquización, administración...). **Fondo**: indica de dónde sale y adónde va la plata (operativo, de reserva, de obras). No son lo mismo.

## Liquidación

- **Período**: el mes que se liquida.
- **Preliquidación**: el cálculo provisorio que el administrador revisa antes de emitir. No genera deuda.
- **Emisión** (o liquidación emitida): genera la **obligación** de cada unidad para el período y su comprobante.
- **Obligación**: lo que una unidad debe por un período, desglosado en capital, gastos particulares e intereses.
- **Vencimiento**: la fecha a partir de la cual corre la mora.

## Cuenta corriente y pagos

- **Cuenta corriente**: el historial de débitos y créditos de una unidad. El saldo sale de ahí, nunca se guarda suelto.
- **Débito**: aumenta lo que la unidad debe (emisión, interés, cargo). **Crédito**: lo disminuye (pago, nota de crédito).
- **Pago**: plata que entra para una unidad. Tiene una fecha real y un canal.
- **Comprobante de pago**: la captura o el PDF de una transferencia que sube el vecino. No es una factura.
- **Pago informado**: un pago que el vecino declaró subiendo su comprobante. No afecta la deuda (R11).
- **Pago confirmado**: un pago informado que el administrador aprobó. Recién ahí se imputa (R11).
- **Pago rechazado**: un pago informado que el administrador descartó, con motivo visible para el vecino.
- **Número de operación**: el identificador de la transferencia en el comprobante. No se repite dentro de un barrio (R11).
- **Extracto**: el listado de movimientos de la cuenta bancaria del barrio, que el administrador sube para validar los pagos informados.
- **Acreditación**: el momento en que la plata llega a la cuenta del complejo.
- **Imputación**: asignar un pago, total o parcialmente, a una o varias obligaciones. Un pago puede tener varias imputaciones.
- **Pago parcial**: cubre parte de una obligación; queda un residual pendiente.
- **Crédito a favor**: lo que sobra de un pago después de imputarlo; se compensa en la próxima liquidación.
- **Saldo inicial**: la deuda o el crédito con que una unidad entra al sistema al migrar.
- **Corrección**: un movimiento nuevo con motivo y responsable. Nunca se edita un movimiento existente.

## Facturas de proveedores

- **Factura**: el comprobante que emite un proveedor al barrio. Origina un gasto. No confundir con el comprobante de pago del vecino.
- **QR de ARCA**: el código obligatorio de toda factura electrónica. Contiene fecha, CUIT del emisor, punto de venta, tipo y número de comprobante, importe, moneda, receptor y código de autorización (R12).
- **CAE**: el código de autorización que ARCA otorga a cada factura electrónica.
- **Factura duplicada**: la que repite CUIT del emisor, punto de venta, tipo y número dentro del mismo barrio (R12).

## Mora

- **Mora**: atraso en el pago después del vencimiento.
- **Interés por mora**: el recargo que genera la mora, según la política del complejo.
- **Anatocismo**: cobrar intereses sobre intereses. El art. 770 del Código Civil y Comercial lo limita.

## Cobro y conciliación

- **Medio de cobro** (o canal): Mercado Pago, transferencia, y más adelante recaudadores como Red Link o Rapipago.
- **Referencia de pago**: el dato que liga un pago con su unidad y período (en Mercado Pago, `external_reference`).
- **Conciliación**: cruzar los movimientos del banco o del recaudador con los pagos e imputaciones.
- **Rendición**: el archivo que entrega un recaudador con los pagos que cobró.
- **Fondo pendiente de conciliación**: un pago recibido que todavía no se pudo asignar a una unidad.
