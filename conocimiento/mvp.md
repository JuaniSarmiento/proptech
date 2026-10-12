# MVP de PropTech

> Alcance acordado entre el 08/10/2026 y hoy (decisiones D-003 a D-063). **El MVP arranca por
> edificios** (D-027); los barrios privados vienen después. Las reglas que citan las historias
> (R01 a R31) están en `reglas-de-negocio.md`; los términos, en `glosario.md`. **Se reescribe**
> cuando cambia una decisión.

## Objetivo

Que un administrador de edificios en propiedad horizontal **liquide y cobre su edificio de punta
a punta, mejor que con su Excel**.

**Se da por cumplido cuando** un edificio piloto corre un mes en paralelo con su método actual y
el cierre da igual al centavo.

## Para quién

- **Tipo de complejo**: edificios en propiedad horizontal (D-027). El modelo soporta barrios
  privados desde el día uno (estados de lote, cargos por estado), pero no se configuran ni se
  prueban en el MVP.
- **Desarrollo**: Juani, como único desarrollador (D-022).
- **Piloto**: un edificio con contacto directo de Alberto (D-033). Mientras no estén sus datos se
  diseña con un edificio de ejemplo; M1 no se cumple sin datos reales.

## Usuarios (D-009, D-037)

| Rol | Qué hace |
|---|---|
| **Administrador titular** | Configura el edificio, carga gastos, liquida, confirma pagos, ve la morosidad; único que cierra liquidaciones y anula pagos |
| **Colaborador** | Personal de la administración: sólo los edificios que le asignan, con nivel "ver" o "editar" |
| **Vecino** | Persona de contacto de una o varias unidades (propietario o no): ve su deuda, entiende su expensa, informa pagos |
| **Consejo** | Sólo lectura de morosidad, gastos y liquidaciones de su edificio |

El inquilino como rol separado queda para después del MVP; en edificios es frecuente, así que se
valida con el piloto que la persona de contacto alcance (D-032).

---

## Historias de usuario

Formato de los criterios: **dado** (situación) · **cuando** (acción) · **entonces** (resultado observable).

### Administrador

**HU-A1 · Configurar el edificio**
Como administrador, quiero configurar las reglas de mi edificio (intereses, grupos de reparto,
categorías de gasto, fondo de reserva) para que el sistema liquide como dice su reglamento.
- Dado un edificio nuevo, cuando lo creo, entonces arranca con los valores del archivo de
  parámetros (D-042): 3% mensual simple, 0 días de gracia, cálculo proporcional por día, un grupo
  "Generales" con todas las unidades por coeficiente, las categorías precargadas, sin fondo de
  reserva y con los estados de unidad desactivados (R01, R02, R03, R15, R16).
- Dadas las categorías precargadas, cuando agrego "Seguridad nocturna" o renombro "Limpieza",
  entonces quedan disponibles para los gastos de mi edificio sin afectar a otros edificios.
- Dado un edificio con liquidaciones emitidas, cuando cambio la tasa o el porcentaje del fondo de
  reserva, entonces las liquidaciones ya emitidas no cambian y el cambio rige desde la próxima.
- Dado un edificio, cuando configuro el interés, entonces elijo entre un único vencimiento (R03,
  default) o el esquema de primer y segundo vencimiento con recargo escalonado (R26), pendiente de
  confirmar con Alberto si el piloto lo usa (ProTecc G4, Q9).

**HU-A2 · Cargar el edificio desde un Excel**
Como administrador, quiero cargar las unidades desde un Excel (piso, departamento, tipo de unidad,
propietario, contacto, coeficiente, saldo inicial) para no tipearlo a mano.
- Dado un Excel válido, cuando lo importo, entonces se crean todas las unidades (departamentos,
  cocheras, bauleras, locales) con sus saldos y la suma importada coincide con la del archivo (R09).
- Dado un Excel con errores (coeficientes que no suman 1, unidades repetidas, columnas faltantes),
  cuando lo importo, entonces no se carga nada y recibo un informe fila por fila con cada error.
- Dado un edificio ya importado, cuando subo el mismo Excel otra vez, entonces el sistema lo
  detecta y no duplica unidades ni saldos.

**HU-A3 · Cargar gastos**
Como administrador, quiero cargar los gastos del mes a mano o subiendo la factura, para que entren
en la liquidación.
- Dado un gasto cargado a mano, cuando lo guardo, entonces queda en borrador con proveedor,
  concepto, categoría, período, importe, grupo de reparto y si es ordinario o extraordinario.
- Dado el sueldo del encargado, cuando lo cargo desde el recibo que liquidó el contador (sueldo y
  cargas sociales), entonces entra como un gasto más del grupo que corresponda (D-028).
- Dada una factura electrónica con QR, cuando la subo, entonces el monto, el CUIT del proveedor y
  el número salen del QR y la IA completa concepto, período, categoría y grupo sugeridos (R12, R16).
- Dada una factura ya cargada, cuando la subo otra vez, entonces el sistema la frena como duplicada.
- Dada una factura cuyo receptor no es el CUIT del consorcio, cuando la subo, entonces el sistema
  me avisa antes de confirmar.
- Dada una factura leída por IA con un monto que se aparta mucho del historial de ese proveedor en
  el edificio, cuando la subo, entonces queda marcada para que la revise con más cuidado antes de
  aprobarla (R23, propuesta, ProTecc A2).
- Dada una nota de crédito de un proveedor, cuando la cargo asociada a su factura, entonces se
  descuenta del gasto antes de prorratear y su monto no puede superar el de esa factura (R22,
  ProTecc H1).
- Dado cualquier gasto en borrador, entonces no entra en la liquidación hasta que lo apruebo.

**HU-A3b · Cargar cargos particulares**
Como administrador, quiero cargarle un importe a una unidad puntual (o importar varios desde un
Excel), para cobrar el uso del SUM, una multa o un consumo.
- Dado un cargo particular aprobado, cuando liquido, entonces aparece sólo en la expensa de esa
  unidad y no cambia lo que pagan las demás (R14).
- Dado un gasto marcado como extraordinario, cuando liquido, entonces la expensa lo muestra en su
  propio bloque con subtotal (R13).

**HU-A4 · Revisar la preliquidación**
Como administrador, quiero ver una preliquidación antes de emitir, para corregir errores antes de
que se generen deudas.
- Dados los gastos aprobados del período, cuando pido la preliquidación, entonces veo lo que paga
  cada unidad, desglosado por grupo de reparto, ordinaria y extraordinaria, fondo de reserva,
  cargos particulares e intereses.
- Dada una preliquidación, entonces la suma de lo asignado a las unidades es igual a la suma de los
  gastos más el fondo de reserva, al centavo (R07, R15).
- Dada una preliquidación, cuando no la emito, entonces no se generó ninguna deuda.

**HU-A5 · Emitir la liquidación**
Como administrador, quiero emitir la liquidación del mes y que cada unidad reciba su comprobante.
- Dada una preliquidación revisada, cuando emito, entonces se genera una obligación por unidad y
  período, con su PDF, y la persona de contacto recibe un email avisando.
- Dado un período ya emitido, cuando intento emitirlo otra vez, entonces el sistema lo impide.
- Dada una liquidación emitida pero todavía no distribuida (ningún email salió y ningún vecino la
  vio en el portal), cuando la anulo con un motivo, entonces se borra sin dejar movimiento, como si
  no se hubiera emitido (R17, ProTecc A5). Una vez distribuida, no se puede anular: se corrige con un
  ajuste (R08).
- Dada una falla del extracto bancario o del servicio de IA el día de emitir, cuando emito,
  entonces la liquidación sale igual, por el camino manual que corresponda (R24, principio P6 de
  Alberto, ProTecc A4).
- Dada una unidad con deuda anterior, entonces su expensa nueva muestra el saldo anterior sin
  volver a cobrarlo (R06), y los intereses del período se registran como débito con su detalle (R03).
- Dada la boleta de cualquier unidad, entonces incluye un código corto de esa unidad para que el
  vecino lo escriba en el concepto de su transferencia (R19, ProTecc A1/E3).

**HU-A6 · Confirmar pagos informados**
Como administrador, quiero una bandeja con los comprobantes que subieron los vecinos para
confirmarlos o rechazarlos, y que al confirmar se imputen solos.
- Dado un pago informado, cuando lo confirmo, entonces se imputa con R04 usando la fecha de la
  transferencia, no la de mi confirmación (R11).
- Dado un pago informado, cuando lo rechazo con un motivo, entonces no afecta la deuda y el vecino
  ve el motivo.
- Dado un pago que supera la deuda, cuando lo confirmo, entonces el excedente queda como crédito a
  favor (R05).
- Dado un vecino con un departamento y una cochera, cuando informa un pago, entonces elige a qué
  unidad corresponde o lo reparte entre ellas.
- Dado un pago confirmado que el banco devuelve (cheque rechazado, contracargo), cuando lo marco
  como revertido con un motivo, entonces se registra un contra-movimiento que vuelve a subir la
  deuda y la unidad se reevalúa para morosidad (R18, ProTecc D4).
- Dado un pago confirmado en la unidad equivocada, cuando uso el asistente de reimputación hacia la
  unidad correcta, entonces se generan los dos movimientos enlazados en una sola operación y las dos
  unidades se reevalúan para morosidad (R25, propuesta, ProTecc B2).

**HU-A7 · Validar con el extracto del banco**
Como administrador, quiero subir el extracto del banco y que el sistema me marque qué comprobantes
coinciden con un movimiento y qué movimientos no tienen comprobante.
- Dado un extracto en CSV o Excel, cuando lo subo, entonces cada pago informado queda marcado como
  "coincide" o "no encontrado" (importe y fecha, y CUIT de origen si el banco lo informa).
- Dado un movimiento del banco sin comprobante, entonces aparece como fondo pendiente de identificar.
- Dado un movimiento del banco ya usado para confirmar un pago, entonces no puede confirmar otro.
- Dado un movimiento que coincide por el código de unidad en el concepto o por el CBU histórico de
  esa unidad, entonces aparece en la bandeja como sugerencia de confianza alta, y confirmo con un
  clic; el sistema nunca lo asigna solo (R19, principio P3 de Alberto, ProTecc A1/E3).

**HU-A8 · Ver la morosidad**
Como administrador, quiero ver quién debe, cuánto y desde cuándo.
- Dado el edificio, cuando abro morosidad, entonces veo por unidad la deuda vencida, la antigüedad
  de la deuda más vieja y los intereses, calculados desde las imputaciones (nunca desde una marca
  de "pagada").
- Dada una unidad con dos o más liquidaciones vencidas con saldo impago, entonces aparece marcada
  como **moroso crítico** (R20, ProTecc M1); no hay bloqueo de amenities porque las reservas no
  están en el MVP.
- Dada una unidad marcada "en gestión judicial", entonces no recibe recordatorios automáticos de
  mora y no cuenta como moroso crítico (R31, propuesta, ProTecc G2).
- Dado un recargo por mora que el vecino discute, cuando el administrador lo condona con un motivo,
  entonces se registra un movimiento de condonación que neutraliza el recargo sin borrarlo, visible
  para el vecino (R29, propuesta, falta decidir quién aprueba, ProTecc B5).
- Dada la lista, cuando la exporto, entonces obtengo un Excel con los mismos números.

**HU-A9 · Corregir un error**
Como administrador, quiero corregir un pago o un cargo mal registrado sin perder el historial.
- Dado un movimiento equivocado, cuando lo corrijo, entonces se agrega un movimiento nuevo con
  motivo y responsable, y el original sigue visible (R08).

**HU-A10 · Emitir un certificado de libre deuda**
Como administrador, quiero generar un certificado de deuda de una unidad para una venta, para que
el escribano pueda escriturar sin esperar a que yo revise la cuenta a mano (R21, ProTecc G3).
- Dada una unidad sin saldo pendiente ni plan de pago, cuando genero el certificado con una fecha de
  corte, entonces el sistema muestra "libre de deuda" con saldo cero a esa fecha y yo lo firmo.
- Dada una unidad con saldo pendiente, cuando genero el certificado, entonces muestra el saldo a la
  fecha de corte y, si hay pagos informados todavía no confirmados, los lista aparte como "en
  revisión", sin restarlos del saldo.
- Dado un certificado ya generado, entonces nunca incluye una estimación de gastos del período en
  curso: sólo la deuda liquidada a la fecha de corte.

### Vecino

**HU-V1 · Entrar al portal**
Como vecino, quiero entrar desde el celular con mi email para ver lo de mis unidades.
- Dado un vecino registrado como contacto de una o varias unidades, cuando entra, entonces ve todas
  las suyas juntas (por ejemplo, su departamento y su cochera) y nunca las de otro vecino ni las de
  otro edificio (R10, D-029).
- Dado un vecino con iPhone, cuando entra por primera vez, entonces el portal le ofrece instalarlo
  en la pantalla de inicio.

**HU-V2 · Ver cuánto debo**
Como vecino, quiero ver cuánto debo y cuándo vence.
- Dadas mis unidades, cuando entro, entonces veo el total a pagar por unidad y en conjunto, el
  vencimiento, la deuda anterior y el crédito a favor si lo hay, y los números coinciden con los del
  administrador.

**HU-V3 · Entender mi expensa**
Como vecino, quiero entender en qué se gastó la plata y por qué cambió mi expensa.
- Dada una liquidación emitida, cuando la abro, entonces veo los gastos en dos bloques (ordinaria
  y extraordinaria) y, dentro de cada uno, agrupados por categoría (encargado, seguridad, limpieza,
  ascensor, servicios) con su subtotal y su porcentaje; además, mi parte de cada grupo de reparto,
  el fondo de reserva y mis intereses (R16).
- Dadas dos liquidaciones seguidas, entonces veo cuánto cambió mi expensa y qué conceptos explican
  la diferencia.

**HU-V4 · Informar un pago**
Como vecino, quiero subir el comprobante de mi transferencia y ver si el administrador lo confirmó.
- Dado un comprobante de BNA+, Mercado Pago u otro banco, cuando lo subo, entonces el sistema
  precarga monto, fecha y número de operación, y yo los reviso antes de enviar (R11).
- Dado un número de operación ya usado en el edificio, cuando subo ese comprobante, entonces el
  sistema lo frena.
- Dado un pago informado, entonces veo su estado: informado, confirmado o rechazado con motivo.

**HU-V5 · Descargar comprobantes**
Como vecino, quiero descargar el PDF de mis expensas y el detalle de mis pagos confirmados.

**HU-V6 · Recibir avisos**
Como vecino, quiero recibir un email antes del vencimiento y otro si quedé en mora.
- Dada una expensa que vence en dos días, entonces recibo un aviso por email una sola vez.
- Dado un pago confirmado antes del aviso, entonces no recibo el aviso de mora.
- Dado un aviso que cae en sábado, domingo o feriado, entonces sale el primer día hábil siguiente
  (R27, propuesta, ProTecc W3).
- Dado un contacto cuyo email no tiene formato válido o cuyo envío rebota, entonces el administrador
  ve esa unidad en una lista de "unidades sin contacto válido" (R28, propuesta, ProTecc W4).

### Consejo

**HU-C1 · Controlar las cuentas**
Como miembro del consejo de propietarios, quiero ver la morosidad, los gastos y las liquidaciones
de mi edificio sin poder modificar nada.
- Dado un usuario del consejo, cuando entra, entonces ve los mismos números que el administrador
  en morosidad, gastos aprobados y liquidaciones emitidas, y ningún botón de acción.

---

## Alcance

**Entra**: configuración del edificio, alta desde Excel con tipos de unidad (departamento, cochera,
baulera, local), archivo de parámetros iniciales, categorías de gasto parametrizables, gastos manuales y desde factura (QR de ARCA más IA, siempre en borrador), sueldo
del encargado cargado como gasto, expensa ordinaria y extraordinaria, fondo de reserva como
concepto de liquidación, cargos particulares, preliquidación, emisión con PDF, cuenta corriente con
imputaciones e intereses, pagos por comprobante con confirmación del administrador, ayuda del
extracto bancario, morosidad, correcciones, portal del vecino con todas sus unidades juntas, vista
del consejo, avisos por email, login real, roles, aislamiento entre edificios, auditoría y backups
probados.

**No entra**: barrios privados en producción, cálculo del sueldo del encargado (escala SUTERH),
inquilino como rol, Mercado Pago y otros medios de cobro integrados (MODO, débito, Red Link,
Rapipago, SIRO), reservas del SUM, bot de WhatsApp, consultas de reglamento con IA, asambleas,
órdenes de compra, tableros complejos, tesorería (saldo de caja y saldo acumulado del fondo de
reserva), contabilidad integral, cálculo de consumos por medidor (se cargan como cargos
particulares). El historial de activos y Mercado Pago van en la v1.1.

## Hitos

| Hito | Historias | Se demuestra cuando |
|---|---|---|
| **M1 · Liquida** | A1, A2, A3 (carga manual), A3b, A4, A5, A9 | Con los datos del edificio piloto, el sistema reproduce su última liquidación al centavo |
| **M2 · Cobra** | A6, A7, A8, A10, V1 a V6, C1 | Un vecino informa un pago, el administrador lo confirma en un clic y queda imputado con la fecha correcta |
| **M3 · Piloto** | A3 (factura con QR e IA) | Un mes completo en paralelo con el método actual y el cierre coincide |

## Cambios de OPSX (detalle y fichas en `roadmap.md`)

| Hito | Cambios, en orden |
|---|---|
| **M1** | 1a `infraestructura-base` · 1b `arranque-del-sistema` · 2 `acceso-y-aislamiento` ⓔ · 3 `configuracion-del-edificio` · 4 `motor-de-cuenta-corriente` ⓔ · 5 `importacion-desde-excel` · 6 `gastos-y-cargos` · 7 `liquidacion-y-emision` ⓔ |
| **M2** | 8 `pagos-informados` · 9 `extracto-bancario` · 10 `morosidad` · 11 `portal-del-vecino` · 12 `vista-del-consejo` · 13 `avisos-por-email` |
| **M3** | 14 `lectura-de-facturas` · 15 `piloto-en-paralelo` |

ⓔ = lleva su propio explore antes del propose. En paralelo al cambio 1: conseguir los datos del edificio piloto (P1).

## Observaciones del análisis que cierra cada hito

El análisis de coherencia de la especificación (`../especificacion/analisis/Analisis_de_coherencia.md`)
marcó 48 observaciones. Así se reparten:

| Hito | Observaciones | Cómo |
|---|---|---|
| **M1** | H01, H02, H03, H04, H05, H06, H09, H10, H11, H12, H13, H14, H15, H16, H20, H43, H44, H45 | Migraciones ordenadas, aislamiento con RLS, cuenta corriente de movimientos con imputaciones, intereses simples registrados al emitir, montos en Decimal, login y permisos reales, secretos fuera del repo, importación validada y atómica |
| **M2** | H07, H08, H28, H41, H42 | Excedentes como crédito, extracto en lugar de rendiciones de recaudadores, avisos con destinatarios reales y sin duplicados, morosidad calculada desde imputaciones |
| **M3** | H21, H22, H46, H48 | Lectura por QR y borrador obligatorio, duplicados frenados, restauración de backup probada, piloto como evidencia antes de hablar de producción |
| **Fuera del MVP** | H17, H18, H19, H23 a H27, H29 a H40, H47 | Módulos que no entran (reservas, accesos, comunicación, cálculo de sueldos, asambleas, compras, activos) o el modelo comercial (P8, sin definir) |

## Cómo se valida

1. **Tests unitarios** de las reglas R01 a R31: cada regla con sus tests mínimos, escritos antes que el código.
2. **Tests de integración** contra PostgreSQL real, incluidos dos pagos simultáneos de la misma unidad.
3. **Test de aceptación de M1**: la última liquidación del edificio piloto, reproducida al centavo.
4. **Mes en paralelo (M3)**: el cierre de PropTech coincide con el método actual del piloto.
5. **Métricas de soporte, después del MVP**: el principio P8 de Alberto ("cada problema se mide")
   queda sin mecanismo en el MVP. No hay entidad de excepción ni métricas todavía; cuando se
   construyan (ver `proyecto-final.md`, fase F6), son las que deciden si conviene pasar a la Etapa 2
   de identificación de pagos (CVU por unidad) de DEC-10.

## Diferencias con la especificación original

La especificación de Alberto (`../especificacion/`) es la base. Esto es lo que el MVP cambia o
posterga, para validarlo con él:

| Tema | Especificación | MVP | Por qué |
|---|---|---|---|
| Por dónde empezar | Barrios privados primero | Edificios primero | Pedido de Alberto: el contacto con edificios es más directo (D-027) |
| Medios de cobro | Recaudadores (Red Link, SIRO), Mercado Pago, MODO, CVU por unidad, rendiciones bancarias | Comprobante del vecino + confirmación del administrador | Valida el producto sin la consulta legal UIF ni integraciones (D-017). Posterga la comisión por procesamiento como ingreso |
| Sueldo del encargado | Liquidación completa con escala SUTERH | Se carga como gasto desde el recibo del contador | Es un módulo con riesgo laboral alto; el contador ya lo liquida hoy (D-028) |
| Historial de activos | Requerimiento explícito, parte de la visión | v1.1, apenas validado el MVP | Primero la plata tiene que funcionar (D-003) |
| Intereses | 3% mensual con capitalización diaria | Interés simple, configurable por edificio | Art. 770 del CCyC (D-010) |
| Coeficientes | Tres fijos por unidad | Grupos de reparto definidos por edificio | Cubre más casos con el mismo trabajo (D-013) |
| Lectura de facturas | Todo con IA | Primero el QR de ARCA, IA para el resto | Monto exacto y más barato (D-019) |
| Fondos y tesorería | Fondo operativo, de reserva y de obras con su saldo | Fondo de reserva sólo como concepto de la expensa, sin saldo de caja | Lo que el vecino paga se refleja; el saldo acumulado no hace falta para liquidar (D-031) |
| Roles | Inquilino, contador, proveedor, encargado, guardia | Administrador, vecino y consejo | Lo mínimo para validar (D-009, D-032) |
| Consumo de agua | Por rangos de litros | Cargo particular importado por Excel | Cubre el caso sin construir medidores (D-026) |
| Código | 48 fragmentos | Descartado | Errores verificados (D-002) |

Y respecto del documento de arquitectura de Alberto (`../especificacion/arquitectura-alberto/`), que
el MVP sigue en su forma (D-035 a D-039):

| Tema | Documento de Alberto | MVP | Por qué |
|---|---|---|---|
| Permisos | ~15 áreas con 3 niveles | Titular, colaborador, consejo y vecino, con las mismas tres capas | Lo mínimo para validar (D-037) |
| Montos | Decimal (NUMERIC 14,2) | Decimal (NUMERIC 14,2), igual que su documento | Alineado con Alberto (D-046) |
| Cifrado con índice ciego, outbox, copiloto, bandeja de WhatsApp | Incluidos | Después del MVP | Alcance (D-039) |
| Login | Clerk para el personal, enlace mágico para vecinos | Se define en el primer change de OPSX | No se decidió todavía (D-039) |
