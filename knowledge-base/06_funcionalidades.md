# Funcionalidades

Historias de usuario del MVP, organizadas por **épica** (el actor) y después por historia, en el
formato propio del proyecto (**HU-\***, no se renumera a `US-NNN`, D-093). Formato de los criterios:
**dado** (situación) · **cuando** (acción) · **entonces** (resultado observable). El detalle de cada
regla citada vive en `05_reglas_de_negocio.md`.

---

## Transversal: ayuda en cada pantalla

### HU-T1 · Entender para qué sirve cada pantalla

**Como** cualquier usuario (super admin, administrador, contador, auxiliar, vecino o consejo) **quiero** tocar un "?" en
cada pantalla y leer para qué sirve y qué hago ahí **para** usarla sin preguntarle a nadie.
Pedido de Alberto (17/10/2026, D-102). Vale para **todas** las historias de abajo.

- **Dado** cualquier pantalla del sistema · **cuando** la abro · **entonces** veo un botón "?" junto
  al título, siempre en el mismo lugar.
- **Dado** el "?" · **cuando** lo toco, lo clickeo o lo activo con el teclado · **entonces** se abre
  una explicación didáctica, en castellano simple, con tres partes: para qué sirve la pantalla, qué
  hago acá (pasos numerados) y qué pasa después.
- **Dado** la explicación abierta · **cuando** toco "Cerrar" o aprieto `Esc` · **entonces** se cierra y
  vuelvo a donde estaba, sin perder lo que había cargado.
- **Dado** un celular · **cuando** uso el "?" · **entonces** funciona tocándolo (no depende de pasar
  el mouse) y el texto se lee al tamaño normal de la pantalla.

**Construido** (3b, `pantallas-del-edificio`): las siete pantallas del administrador (Mis edificios,
Resumen, Padrón de unidades, Grupos de reparto, Categorías de gasto, Intereses y vencimiento, Confirmar
"sin saldos previos") tienen su "?" con las tres partes. Las pantallas del vecino, del consejo y el
login todavía no existen (2b en adelante).

---

## Épica: Administrador

Los actores siguen la matriz de D-106: super admin y todo administrador del edificio operan,
configuran y emiten. Anular, revertir o reimputar, condonar, dar de baja deuda, aceptar alertas
bloqueantes y confirmar "sin saldos previos" requieren super admin o administrador principal.
Crear edificios e invitar usuarios es exclusivo del super admin. Las historias conservan su alcance;
contador, auxiliar y consejo sólo leen dentro del suyo.

### HU-A1 · Configurar el edificio

Como administrador, quiero configurar las reglas de mi edificio (intereses, grupos de reparto,
categorías de gasto, fondo de reserva) **y sus datos** (ubicación, calle, cantidad de pisos y
subsuelos) para que el sistema liquide como dice su reglamento y para que cada unidad elija su piso de
una lista real, no de texto libre.

**Criterios de aceptación**:
- Dado un edificio nuevo, cuando lo creo como super admin, entonces arranca con los valores del archivo de
  parámetros (D-042): 3% mensual simple, 0 días de gracia, cálculo proporcional por día, un grupo
  "Generales" con todas las unidades por coeficiente, las categorías precargadas, sin fondo de
  reserva y con los estados de unidad desactivados (R01, R02, R03, R15, R16).
- Dadas las categorías precargadas, cuando agrego "Seguridad nocturna" o renombro "Limpieza",
  entonces quedan disponibles para los gastos de mi edificio sin afectar a otros edificios.
- Dado un edificio, cuando cambio la tasa o el porcentaje del fondo de reserva, entonces queda una
  versión nueva de la configuración con fecha y autor, y la anterior se conserva. *Que una liquidación
  ya emitida no cambie se prueba en el cambio 7, que es el que emite.*
- Dado un edificio, cuando configuro el interés, entonces queda un único vencimiento con interés
  simple (R03).
- **Ubicación del edificio (3c, D1, D2, D-128)**: dado el alta o la edición del edificio, cuando elijo
  provincia, entonces la lista de departamentos se filtra a esa provincia, y al elegir departamento, la
  de localidades se filtra a ese departamento (listas encadenadas); cambiar una lista de arriba vacía
  las de abajo, nunca deja un trío incoherente en pantalla. La calle y el número son texto libre, sin
  validar contra ningún dataset (P62). El servidor es la autoridad: un trío que no exista en el archivo
  de Georef se rechaza aunque el pedido venga armado a mano, aunque la web lo deje pasar.
- **Pisos y subsuelos (3c, D3, D-128)**: dado el alta o la edición del edificio, cuando fijo la
  cantidad de pisos (1 a 60) y de subsuelos (0 a 5), entonces el vocabulario de piso de cada unidad
  pasa a ser exactamente `SS1`…`SS<subsuelos>`, `PB` y `1`…`<pisos>`; si intento bajar la cantidad con
  unidades cargadas por encima del nuevo máximo, el pedido se rechaza nombrando cuáles.
- **Editar el edificio (3c, D5, D-128)**: dado un edificio ya creado, cuando el administrador (o el
  super admin) corrige su ubicación, calle, pisos o subsuelos, entonces el cambio se guarda, queda
  auditado con los **nombres** de los campos cambiados (nunca otros valores) y un pedido que no cambia
  nada no deja registro. Antes del 3c esta edición **no existía** (sólo había alta).
- **Edificios ya cargados (3c, E3, D-128)**: dado un edificio creado antes del 3c, cuando entro a su
  puesta a punto, entonces veo "ubicación" como paso pendiente (antes de los seis que ya tenía el 3b) y
  completarla no inventa ningún valor: arranca en blanco.
- *Pendiente, no es criterio todavía*: el esquema de primer y segundo vencimiento con recargo
  escalonado (R26) entra acá si Alberto confirma que el piloto lo usa (ProTecc G4, Q9).

**Construido** (3b `pantallas-del-edificio`, ampliado por 3c `pulido-de-la-configuracion`): desde el
navegador, sin `curl`, "Mis edificios" (crear el edificio con su ubicación, calle y pisos, sólo super
admin), "Resumen" (el checklist de puesta a punto con siete pasos y "listo para liquidar", calculados
por la API, con el botón "Editar" que abre el formulario completo), "Padrón de unidades" (el piso de
cada unidad elegido de la lista del edificio, con "Sin completar" explícito para una unidad migrada sin
piso elegido), "Grupos de reparto" (desactivar/reactivar, sin clave a mano), "Categorías de gasto"
(sin clave a mano) e "Intereses y vencimiento" (cambiar la tasa o el fondo de reserva, con la versión
anterior conservada).

**Reglas relacionadas**: R01, R02, R03, R15, R16 (R26, propuesta, a confirmar).

### HU-A2 · Cargar el edificio desde un Excel

Como administrador, quiero cargar las unidades desde un Excel (piso, departamento, tipo de unidad,
propietario, contacto, coeficiente, saldo inicial e interés ya devengado, y opcionalmente el detalle
por período con su vencimiento) para no tipearlo a mano.

**Criterios de aceptación**:
- Dado un Excel válido, cuando lo importo, entonces se crean todas las unidades (departamentos,
  cocheras, bauleras, locales) con sus saldos y la suma importada coincide con la del archivo (R09).
- Dado un Excel con errores (coeficientes de un grupo que se apartan de 1 más que la tolerancia de R01,
  unidades repetidas, columnas faltantes),
  cuando lo importo, entonces no se carga nada y recibo un informe fila por fila con cada error.
- Dado un edificio ya importado, cuando subo el mismo Excel otra vez, entonces el sistema lo
  detecta y no duplica unidades ni saldos.
- Dado un borrador de saldos y mi listado de saldos por unidad, cuando los comparo, entonces veo
  cada unidad que no coincide con su diferencia, aunque el total dé igual (R09).
- Dadas diferencias, cuando las acepto igual, entonces la aceptación queda registrada y recién ahí
  puedo confirmar los saldos.
- **Qué acepta la columna "piso" (3c, borde fijado para el importador del cambio 5, D3, D-128)**: el
  3c **no construye** el importador, pero fija el contrato que su columna "piso" va a tener que
  respetar: exactamente el vocabulario del edificio destino (`SS1`…`SS<subsuelos>`, `PB`,
  `1`…`<pisos>`), coincidencia completa, sin recortar espacios ni traducir variantes ("Entrepiso",
  "planta alta", "1°") — eso es **BREAKING** respecto de lo que `unidad.piso` aceptaba como texto libre
  antes del 3c. Una fila con un piso fuera de ese vocabulario, o con una celda vacía, se trata igual que
  cualquier otro error de fila de esta historia: no se carga nada y se informa cuál.

**Reglas relacionadas**: R09.

### HU-A3 · Cargar gastos

Como administrador, quiero cargar los gastos del mes a mano o subiendo la factura, para que entren
en la liquidación.

**Criterios de aceptación**:
- Dado un gasto cargado a mano, cuando lo guardo, entonces queda en borrador con proveedor,
  concepto, categoría, período, importe, grupo de reparto y si es ordinario o extraordinario; si tengo
  la factura, también su punto de venta, tipo y número, para que el control de duplicados funcione
  (R12, R34).
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

**Reglas relacionadas**: R12, R16, R22, R34 (R23, propuesta).

### HU-A3b · Cargar cargos particulares

Como administrador, quiero cargarle un importe a una unidad puntual (o importar varios desde un
Excel), para cobrar el uso del SUM, una multa o un consumo.

**Criterios de aceptación**:
- Dado un cargo particular aprobado, cuando liquido, entonces aparece sólo en la expensa de esa
  unidad y no cambia lo que pagan las demás (R14).
- Dado un gasto marcado como extraordinario, cuando liquido, entonces la expensa lo muestra en su
  propio bloque con subtotal (R13).

**Reglas relacionadas**: R13, R14.

### HU-A4 · Revisar la preliquidación

Como administrador, quiero ver una preliquidación antes de emitir, para corregir errores antes de
que se generen deudas.

**Criterios de aceptación**:
- Dados los gastos aprobados del período, cuando pido la preliquidación, entonces veo lo que paga
  cada unidad, desglosado por grupo de reparto, ordinaria y extraordinaria, fondo de reserva,
  cargos particulares e intereses.
- Dada una preliquidación, entonces lo **prorrateado** entre las unidades es igual, al centavo, a los
  gastos aprobados del período menos sus notas de crédito y los ingresos del consorcio, más el fondo
  de reserva (R07, R15, R22, R38). Los cargos particulares (incluidos los recurrentes del motor, R14, si se validan) y los intereses se suman aparte,
  unidad por unidad (la bonificación por pronto pago no es parte de la liquidación: se registra al
  confirmar el pago, R37), y el total de la liquidación es la suma de todo eso.
- Dada una preliquidación, cuando no la emito, entonces no se generó ninguna deuda.

**Reglas relacionadas**: R07, R14, R15, R22 (R14 recurrente, R37 y R38: propuestas).

### HU-A5 · Emitir la liquidación

Como administrador, quiero emitir la liquidación del mes y que cada unidad reciba su comprobante.

**Criterios de aceptación**:
- Dada una preliquidación revisada, cuando emito, entonces se genera una obligación por unidad y
  período, con su PDF. El aviso por email llega con HU-V6 (cambio 13).
- Dada una liquidación emitida, cuando la distribuyo, entonces queda distribuida y ya no se puede
  anular (D-074).
- Dado un período ya emitido, cuando intento emitirlo otra vez, entonces el sistema lo impide, salvo que
  esa liquidación esté anulada (R17).
- Dada una preliquidación con un control bloqueante aceptable (por ejemplo, facturas leídas por IA
  con alertas), cuando intento emitir, entonces el sistema me lo muestra y no emite, salvo que acepte esa alerta de
  forma explícita; la aceptación queda registrada (R34).
- Dada una liquidación emitida pero todavía no distribuida, cuando la anulo con un motivo, entonces
  pasa a anulada, la deuda de cada unidad queda igual que antes de emitir y ningún movimiento se
  borra (R17, D-073, ProTecc A5). Una vez distribuida, no se puede anular: se corrige con un
  ajuste (R08).
- Dados gastos que la IA no pudo leer (estado "sin IA"), cuando emito, entonces la liquidación sale
  sin ellos y veo la advertencia "hay N facturas sin cargar"; dados gastos que la IA leyó con alertas
  ("en revisión"), entonces no emito salvo que acepte la alerta (R24, R34, D-075, ProTecc A4).
- Dado que el extracto del banco no está procesado, cuando emito, entonces la liquidación sale igual
  (R24).
- Dada una unidad con deuda anterior, entonces su expensa nueva muestra el saldo anterior sin
  volver a cobrarlo (R06), y los intereses del período se registran como débito con su detalle (R03).
- Dada la boleta de cualquier unidad, entonces incluye un código corto de esa unidad para que el
  vecino lo escriba en el concepto de su transferencia (R19, ProTecc A1/E3).

**Reglas relacionadas**: R03, R06, R08, R17, R19, R24, R34.

### HU-A6 · Confirmar pagos informados

Como administrador, quiero una bandeja con los comprobantes que subieron los vecinos para
confirmarlos o rechazarlos, y que al confirmar se imputen solos.

**Criterios de aceptación**:
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
  deuda; si ahora tiene dos o más liquidaciones vencidas, pasa a ser moroso crítico (R18, R20,
  ProTecc D4).
- Dado un pago confirmado en la unidad equivocada, cuando uso el asistente de reimputación hacia la
  unidad correcta, entonces se generan los dos movimientos enlazados en una sola operación y el
  moroso crítico de las dos unidades queda bien calculado (R25, R20, propuesta, ProTecc B2).

**Reglas relacionadas**: R04, R05, R11, R18, R20 (R25, propuesta).

### HU-A7 · Validar con el extracto del banco

Como administrador, quiero subir el extracto del banco y que el sistema me marque qué comprobantes
coinciden con un movimiento y qué movimientos no tienen comprobante.

**Criterios de aceptación**:
- Dado un extracto en CSV o Excel, cuando lo subo, entonces cada pago informado queda marcado como
  "coincide" o "no encontrado" (importe y fecha, y CUIT de origen si el banco lo informa).
- Dado un movimiento del banco sin comprobante, entonces aparece como fondo pendiente de identificar.
- Dado un movimiento del banco ya usado para confirmar un pago, entonces no puede confirmar otro.
- Dado que el extracto del período no está completo, cuando preliquido o emito, entonces veo la
  advertencia "extracto incompleto" (R34).
- Dado un movimiento que coincide por el código de unidad en el concepto o por el CBU histórico de
  esa unidad, entonces aparece en la bandeja como sugerencia de confianza alta, y confirmo con un
  clic; el sistema nunca lo asigna solo (R19, principio 3 de Alberto, ProTecc A1/E3).

**Reglas relacionadas**: R11, R19, R34.

### HU-A8 · Ver la morosidad

Como administrador, quiero ver quién debe, cuánto y desde cuándo.

**Criterios de aceptación**:
- Dado el edificio, cuando abro morosidad, entonces veo por unidad la deuda vencida, la antigüedad
  de la deuda más vieja y los intereses, calculados desde las imputaciones (nunca desde una marca
  de "pagada").
- Dada una unidad con dos o más liquidaciones vencidas con saldo impago, entonces aparece marcada
  como **moroso crítico** (R20, ProTecc M1); no hay bloqueo de amenities porque las reservas no
  están en el MVP.
- Dada la lista, cuando la exporto, entonces obtengo un Excel con los mismos números.

**Reglas relacionadas**: R20.

### HU-A9 · Corregir un error

Como super admin o administrador principal, quiero corregir un pago o un cargo mal registrado sin
perder el historial.

**Criterios de aceptación**:
- Dado un movimiento equivocado, cuando lo corrijo, entonces se agrega un movimiento nuevo con
  motivo y responsable, y el original sigue visible (R08).

**Reglas relacionadas**: R08.

### HU-A10 · Emitir un certificado de libre deuda

Como administrador, quiero generar un certificado de deuda de una unidad para una venta, para que
el escribano pueda escriturar sin esperar a que yo revise la cuenta a mano (R21, ProTecc G3).

**Criterios de aceptación**:
- Dada una unidad sin saldo pendiente, cuando genero el certificado con una fecha de
  corte, entonces el sistema muestra "libre de deuda" con saldo cero a esa fecha y yo lo firmo.
- Dada una unidad con saldo pendiente, cuando genero el certificado, entonces muestra el saldo a la
  fecha de corte y, si hay pagos informados todavía no confirmados, los lista aparte como "en
  revisión", sin restarlos del saldo.
- Dado un certificado ya generado, entonces nunca incluye una estimación de gastos del período en
  curso: sólo la deuda liquidada a la fecha de corte, más una línea aparte con el interés corrido
  hasta esa fecha, calculado y sin registrar (R21, D-081).

**Reglas relacionadas**: R21.

### HU-A11 · Condonar intereses y marcar la gestión judicial *(propuesta, cambio 10b, D-078)*

Como super admin o administrador principal, quiero condonar un recargo discutido y marcar las
unidades que están en juicio, para que el sistema las trate como corresponde.

**Criterios de aceptación**:
- Dado un recargo por mora que el vecino discute, cuando lo condono con un motivo, entonces se
  registra un movimiento de condonación que neutraliza el recargo sin borrarlo, visible para el
  vecino (R29, propuesta, falta decidir quién aprueba, ProTecc B5).
- Dada una unidad que marco "en gestión judicial", entonces deja de contar como moroso crítico
  (R31, propuesta, ProTecc G2), y los avisos automáticos de mora del cambio 13 la saltean.

**Reglas relacionadas**: R29, R31 (ambas propuestas).

---

## Épica: Vecino

El propietario ve todas las expensas de sus unidades; el inquilino, sólo las ordinarias, también en
los PDFs y comprobantes descargables (D-106). Una persona puede tener ambos vínculos en unidades
distintas. Varios propietarios de la misma unidad ven su cuenta completa y cualquiera informa pagos.

### HU-V1 · Entrar al portal

Como vecino, quiero entrar desde el celular con mi usuario y contraseña de Clerk, con link mágico o
con Google, para ver lo de mis unidades (D-107, D-108).

**Construido por el 2b `login-y-usuarios`** (archivado 22/10/2026): el ingreso, el selector de
administración y la invitación. Ver "lo de mis unidades" (el portal propiamente dicho) **lo construye
el cambio 11**: hoy, al entrar, el vecino sólo ve el estado vacío del portal.

**Criterios de aceptación**:
- Dado un vecino de alta desde el padrón, con vínculo e invitación por mail para una o varias
  unidades, cuando entra, entonces ve todas las suyas juntas (por ejemplo, su departamento y su
  cochera), también en edificios distintos, y nunca unidades ajenas (R10, D-029, D-106). **Pendiente
  de 11**: hoy no hay nada que mostrar todavía.
- Dado un vecino invitado, cuando acepta la invitación con contraseña, con el link del mail o con
  Google (el email verificado de Google tiene que coincidir con el invitado), entonces queda
  vinculado a esa persona y entra; con otro Gmail no entra (construido, 2b).
- Dado un vecino con iPhone, cuando entra por primera vez, entonces el portal le ofrece instalarlo
  en la pantalla de inicio. **Pendiente de 11**.

**Reglas relacionadas**: R10.

### HU-SA1 · Invitar y gestionar usuarios (super admin)

Como super admin, quiero invitar al personal con su perfil y alcance, y dar de alta vecinos desde el
padrón, para que cada uno entre con su propia cuenta (RA-6, D-106, D-107).

**Construido por el 2b `login-y-usuarios`** (archivado 22/10/2026).

**Criterios de aceptación**:
- Dado el super admin en `/personal`, cuando invita a alguien con un perfil y alcance válidos,
  entonces se crea la invitación, el worker la envía por Clerk y queda `enviada` hasta que se acepte.
- Dado el super admin en el padrón de un edificio, cuando da de alta un vecino con su unidad y
  vínculo (propietario o inquilino), entonces puede haber varios propietarios por unidad y vínculos
  distintos de una misma persona en unidades distintas.
- Dado el super admin, cuando revoca una invitación `enviada`, entonces queda `revocada` y Clerk la
  marca revocada; el link ya no sirve para aceptar.
- Dado alguien que no es super admin, cuando abre `/personal`, entonces no ve los controles de
  invitar, revocar ni quitar.

**Reglas relacionadas**: R10, D-106.

### HU-V2 · Ver cuánto debo

Como vecino, quiero ver cuánto debo y cuándo vence.

**Criterios de aceptación**:
- Dadas mis unidades, cuando entro, entonces veo el total a pagar por unidad y en conjunto, el
  vencimiento, la deuda anterior y el crédito a favor si lo hay, y los números coinciden con los del
  administrador.

**Reglas relacionadas**: R05, R06.

### HU-V3 · Entender mi expensa

Como vecino, quiero entender en qué se gastó la plata y por qué cambió mi expensa.

**Criterios de aceptación**:
- Dada una liquidación emitida, cuando la abro como propietario, entonces veo ordinarias y
  extraordinarias; como inquilino, sólo ordinarias (D-106). Dentro de los bloques que me corresponden
  veo los gastos agrupados por categoría (encargado, seguridad, limpieza, ascensor, servicios), con
  subtotal y porcentaje, mi parte de cada grupo de reparto, fondo de reserva e intereses (R16).
- Dadas dos liquidaciones seguidas, entonces veo cuánto cambió mi expensa y qué conceptos explican
  la diferencia.

**Reglas relacionadas**: R16.

### HU-V4 · Informar un pago

Como vecino, quiero subir el comprobante de mi transferencia y ver si el administrador lo confirmó.

**Criterios de aceptación**:
- Dado un comprobante de BNA+, Mercado Pago u otro banco, cuando lo subo, entonces el sistema
  precarga monto, fecha y número de operación, y yo los reviso antes de enviar (R11).
- Dado un número de operación ya usado en el edificio, cuando subo ese comprobante, entonces el
  sistema lo frena.
- Dado un pago informado, entonces veo su estado: informado, confirmado, rechazado con motivo o
  revertido (R18).

**Reglas relacionadas**: R11, R18.

### HU-V5 · Descargar comprobantes

Como vecino, quiero descargar el PDF de mis expensas y el detalle de mis pagos confirmados.

**Criterios de aceptación**:
- Dado un período emitido de mi unidad, cuando pido su PDF, entonces descargo el comprobante
  de mi vínculo, con el código de la unidad; como inquilino no recibo extraordinarias (D-106).
- Dado un período todavía no emitido, entonces no aparece para descargar.
- Dado que pido el detalle de pagos, entonces veo sólo los confirmados de mis unidades, nunca los de
  otra unidad ni los que siguen informados o fueron rechazados (R10, R11).

**Reglas relacionadas**: R10, R11.

### HU-V6 · Recibir avisos

Como vecino, quiero recibir un email antes del vencimiento y otro si quedé en mora.

**Criterios de aceptación**:
- Dada una expensa que vence en dos días, entonces recibo un aviso por email una sola vez.
- Dado un pago confirmado antes del aviso, entonces no recibo el aviso de mora.
- Dado un aviso que cae en sábado, domingo o feriado, entonces sale el primer día hábil siguiente
  (R27, propuesta, ProTecc W3).
- Dado un contacto cuyo email no tiene formato válido o cuyo envío rebota, entonces el administrador
  ve esa unidad en una lista de "unidades sin contacto válido" (R28, propuesta, ProTecc W4).

**Reglas relacionadas**: R27, R28 (ambas propuestas).

---

## Épica: Consejo

### HU-C1 · Controlar las cuentas

Como miembro del consejo de propietarios, quiero ver la morosidad, los gastos y las liquidaciones
de mi edificio sin poder modificar nada.

**Criterios de aceptación**:
- Dado un usuario del consejo, cuando entra, entonces ve los mismos números que el administrador
  en morosidad, gastos aprobados y liquidaciones emitidas, y ningún botón de acción.

**Reglas relacionadas**: R10 (alcance por edificio, sólo lectura).
