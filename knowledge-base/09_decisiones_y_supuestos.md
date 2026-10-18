# Decisiones y Supuestos

Registro de cómo llegamos a lo que hay. **Sólo se agrega, nunca se borra**: si una decisión
cambia, se escribe una nueva que la reemplaza y se marca la vieja como `reemplazada por D-0XX`.
Lo vigente se refleja en el resto de los archivos que "se reescriben" (ver la tabla de
`README.md`); acá sólo queda el porqué de cada uno.

Formato: fecha · decisión · alternativa descartada · por qué · quién decidió.

---

## D-001 · El nombre del proyecto es PropTech · *corregida en parte por D-035*

- **Fecha**: 08/10/2026
- **Decisión**: el nombre final es **PropTech**. "PropTech OS" de la especificación era nombre técnico.
- **Descartado**: Kooris, que es otro proyecto del mismo rubro en Mendoza y queda como competidor.
- **Quién**: Juani, con la aclaración de Alberto.

## D-002 · La especificación es insumo; el código original se descarta

- **Fecha**: 08/10/2026
- **Decisión**: los 19 módulos y el análisis de coherencia (48 observaciones) son la base para
  diseñar. El código original va a la papelera y no se reutiliza.
- **Descartado**: partir del código del zip y corregirlo.
- **Por qué**: eran fragmentos sueltos de una charla con un chatbot, con fallas críticas
  verificadas (login que acepta cualquier token, función de mora que usa una variable no
  declarada). Corregirlo cuesta más que escribirlo bien con tests.
- **Quién**: Juani.

## D-003 · El MVP se construye en tres hitos demostrables · *corregida en parte por D-017*

- **Fecha**: 08/10/2026
- **Decisión**: **M1 Liquida** (decisiones, base, importación, motor financiero, liquidación),
  **M2 Cobra** (Mercado Pago, conciliación, portal, recordatorios), **M3 Piloto** (lectura de
  facturas con IA y un mes en paralelo). El historial de activos va en la v1.1.
- **Descartado**: nueve fases en cascada, donde recién en la sexta un usuario veía algo útil.
- **Por qué**: cada hito se puede mostrar a un administrador real; si el modelo financiero
  está mal pensado, aparece en el primer mes y no en el tercero.
- **Quién**: Juani.

## D-004 · Un barrio piloto real desde el inicio · *corregida en parte por D-027 y D-033*

- **Fecha**: 08/10/2026
- **Decisión**: el piloto se consigue en la fase 0, no al final. Su padrón, sus facturas y su
  última liquidación son el test de aceptación de M1.
- **Descartado**: construir con datos inventados y buscar piloto al terminar.
- **Quién**: Juani. **Pendiente**: quién es el piloto (ver preguntas abiertas).

## D-005 · La plata nunca pasa por una cuenta de PropTech · *corregida en parte por D-017*

- **Fecha**: 08/10/2026
- **Decisión**: los cobros van directo a la cuenta del consorcio. PropTech sólo recibe los datos
  para imputar. La consulta legal por la Resolución UIF 200/2024 arranca en la fase 0 y se
  resuelve antes del primer cobro en producción.
- **Descartado**: recaudar en una cuenta propia y transferir al consorcio.
- **Por qué**: custodiar fondos de terceros activa el régimen de proveedor de servicios de pago
  del BCRA. Aun sin custodia, la UIF podría alcanzar a quien facilita el inicio del pago.
- **Quién**: Juani.

## D-006 · Recordatorios por email en el MVP *(propuesta, sin confirmar)* · *confirmada: los avisos por email entran en el cambio 13*

- **Fecha**: 08/10/2026
- **Decisión**: los avisos de vencimiento y mora salen por email. WhatsApp queda para después.
- **Por qué**: la API oficial de WhatsApp exige verificar el negocio ante Meta y cotizar con un proveedor.
- **Quién**: Juani.

## D-007 · La base de conocimiento son cinco archivos · *corregida: la base hoy tiene diez archivos (ver `README.md`); corregida en parte por D-093*

- **Fecha**: 08/10/2026
- **Decisión**: `mvp.md`, `proyecto-final.md` y `reglas-de-negocio.md` describen cómo es el
  sistema y se **reescriben**; `decisiones.md` cuenta cómo llegamos y sólo se **agrega**;
  `glosario.md` fija el idioma común. El documento para Alberto se genera a partir de estos.
- **Descartado**: tres archivos (mezclaba lo vigente con la historia) y diez archivos al estilo
  de una base completa (se desactualiza antes de que exista código). Arquitectura y modelo de
  datos viven en el *design* de cada change de OPSX.
- **Quién**: Juani.

## D-008 · El MVP es para barrios privados; el diseño escala a edificios · *reemplazada por D-027*

- **Fecha**: 08/10/2026
- **Decisión**: el MVP atiende sólo barrios privados. Desde el día uno, el modelo de datos
  soporta varios administradores, varios complejos y el tipo de complejo (barrio o edificio),
  para que sumar edificios sea configuración y no reescritura.
- **Descartado**: barrios y edificios a la vez (más alcance, y en edificios compiten de frente
  CONSO y AdminProp); y sólo barrios con un modelo cerrado que después haya que rehacer.
- **Por qué**: en Mendoza los barrios son el segmento menos atendido y la especificación arranca
  por ahí. Escalar significa diseñar bien los datos y los permisos, no sumar infraestructura
  antes de tener clientes.
- **Quién**: Juani.

## D-009 · Usuarios del MVP: administrador, vecino y consejo en sólo lectura · *ampliada por D-037*

- **Fecha**: 08/10/2026
- **Decisión**: tres roles. **Administrador** (opera todo), **vecino** (su unidad: deuda,
  expensa, pago, comprobantes) y **consejo** (sólo lectura de morosidad, gastos y liquidaciones de
  su barrio). En el MVP, quien paga es la persona registrada como contacto de la unidad, sea
  propietario o no.
- **Descartado**: el rol de inquilino separado del propietario. Pasa a la versión siguiente.
- **Por qué**: el consejo es barato de hacer y es quien aprueba contratar el sistema; el inquilino
  obliga a definir qué ve cada persona de la misma unidad, y no hace falta para validar el MVP.
- **Quién**: Juani.

## D-010 · Intereses por mora: simples y configurables por barrio con un menú cerrado

- **Fecha**: 08/10/2026
- **Decisión**: interés simple sobre lo impago, sin capitalización. Cada barrio configura tasa
  mensual, días de gracia y forma de cálculo (proporcional por día o mes entero). Se registra al
  emitir la liquidación siguiente y cada liquidación guarda la configuración usada. Detalle en R03.
- **Descartado**: la capitalización diaria de la especificación (choca con el art. 770 del
  CCyC), una tasa única para todos, y una fórmula libre configurable (más riesgo de cobrar mal y
  tests imposibles de acotar).
- **Pendiente**: validar los defaults con un administrador o contador de Mendoza.
- **Quién**: Juani.

## D-011 · Orden de imputación único: lo más viejo primero, interés antes que capital

- **Fecha**: 08/10/2026
- **Decisión**: una sola regla para todos los barrios (detalle y ejemplo en R04).
- **Descartado**: hacerlo configurable por barrio.
- **Por qué**: es el estándar del rubro, y si cada barrio imputa distinto se vuelve imposible
  explicarle a un vecino dónde se aplicó su pago.
- **Quién**: Juani.

## D-012 · Cada peso de deuda vive en un solo lugar

- **Fecha**: 08/10/2026
- **Decisión**: el residual de cada obligación se calcula desde sus imputaciones; el excedente
  queda como crédito a favor; la expensa nueva muestra el saldo anterior sin volver a debitarlo.
  Lo que se muestra siempre se calcula desde la fuente. Detalle en R05 y R06.
- **Descartado**: la marca binaria pagada/impaga y la suma del saldo anterior dentro de la
  expensa nueva, ambas de la especificación original (análisis H04 y H06).
- **Quién**: Juani.

## D-013 · El prorrateo usa grupos de reparto definidos por cada barrio

- **Fecha**: 08/10/2026
- **Decisión**: cada barrio define grupos con sus unidades y su método (coeficiente, superficie o
  partes iguales); cada gasto va a un grupo. Default: un grupo "Generales". Detalle en R01.
- **Descartado**: los tres coeficientes fijos por unidad de la especificación (generales,
  amenities, obras), que no cubren un espacio que pagan sólo algunos lotes.
- **Por qué**: casi el mismo trabajo, cubre cualquier barrio y sirve igual para edificios.
- **Quién**: Juani.

## D-014 · El estado del lote modifica la expensa con un factor y un cargo fijo configurables

- **Fecha**: 08/10/2026
- **Decisión**: por estado, cada barrio configura un factor sobre la participación en el reparto y
  un cargo fijo mensual. El factor se redistribuye entre los demás lotes para cubrir el gasto. Se
  usa el estado al momento de emitir. Detalle en R02.
- **Descartado**: reglas por estado escritas a medida para cada barrio, y la penalidad por plazo
  de construcción vencido de la especificación (queda fuera del MVP).
- **Quién**: Juani. La redistribución del factor la propuso Claude al registrar la regla: sin ella
  el barrio no cubre sus gastos.

## D-015 · Redondeo por mayor resto y saldo inicial con o sin detalle · *representación en centavos reemplazada por D-046*

- **Fecha**: 08/10/2026
- **Decisión**: montos en centavos enteros, reparto con el método del mayor resto para que la suma
  dé exacta (R07). El saldo inicial acepta el detalle por período o un total único con fecha de
  migración; los créditos entran como crédito (R09).
- **Descartado**: decimales flotantes; mandar la diferencia de redondeo a una unidad fija; exigir
  siempre el detalle por período (muchos barrios no lo tienen) o aceptar sólo el total (se
  pierden los intereses viejos).
- **Quién**: Juani.

## D-016 · Correcciones como movimientos nuevos y aislamiento por identidad · *corregida en parte por D-076*

- **Fecha**: 08/10/2026
- **Decisión**: la cuenta corriente no se edita ni se borra; un error se corrige con un movimiento
  nuevo con motivo y responsable (R08). Ningún barrio ve datos de otro y el barrio sale de la
  identidad autenticada, nunca de un parámetro del cliente (R10).
- **Por qué**: permite reconstruir cualquier reclamo de un vecino y es la base para operar muchos
  administradores y barrios en el mismo sistema.
- **Quién**: Juani.

## D-017 · En el MVP los pagos se registran con comprobante y confirmación del administrador

- **Fecha**: 08/10/2026
- **Decisión**: el vecino transfiere como hoy y sube el comprobante en el portal; el administrador
  lo confirma desde una bandeja y recién ahí se imputa (R11). El extracto bancario se sube como
  ayuda: el sistema marca qué comprobantes coinciden con un movimiento del banco. Mercado Pago es
  lo primero después del MVP.
- **Descartado**: integrar Mercado Pago en el MVP.
- **Por qué**: PropTech no inicia pagos, sólo registra lo confirmado, así que la consulta UIF de
  D-005 deja de bloquear el MVP (pasa a ser requisito de la integración con Mercado Pago). Es una
  integración menos, replica cómo trabajan hoy los administradores y baja el riesgo del piloto.
- **Costo aceptado**: se pierde el "pagar con un botón" en el MVP.
- **Quién**: Juani (la idea es suya).

## D-018 · Lectura del comprobante de pago con IA y número de operación único

- **Fecha**: 08/10/2026
- **Decisión**: la unidad sale de quién sube el comprobante; la IA precarga monto, fecha y número
  de operación y el vecino los confirma; el número de operación no se repite dentro del barrio.
  Detalle en R11.
- **Por qué**: se revisaron dos comprobantes reales (BNA+ y Mercado Pago): formatos distintos,
  sin QR, uno sin datos de origen y ambos con motivo "Varios".
- **Quién**: Juani.

## D-019 · Las facturas se leen primero por el QR de ARCA y la IA completa el resto · *corregida en parte por D-075*

- **Fecha**: 08/10/2026
- **Decisión**: el monto, el proveedor y el identificador de la factura salen del QR oficial; la IA
  completa concepto, período y grupo de reparto; se frenan duplicados y se avisa si el receptor no
  es el barrio. Todo queda en borrador hasta que confirma el administrador. Detalle en R12.
- **Descartado**: leer toda la factura con IA, como proponía la especificación original (más caro
  y con riesgo de leer mal el monto); y el prompt original que pedía "inferir" datos ausentes.
- **Fuente**: especificación oficial del QR en arca.gob.ar, versión 1 (febrero de 2025), verificada
  decodificando su ejemplo.
- **Quién**: Juani.

## D-020 · Stack del MVP · *corregida en parte por D-036 y D-038*

- **Fecha**: 08/10/2026
- **Decisión**: backend en Python + FastAPI + SQLAlchemy sobre PostgreSQL; sin Redis en el MVP.
  Frontend: una sola app web en React + TypeScript con área de administrador, de consejo y de
  vecino, adaptada al celular e instalable (PWA); sin app nativa. PDFs con WeasyPrint, emails con
  un servicio transaccional, despliegue en un VPS con Docker. Las interfaces pasan por la skill
  impeccable cuando arranque su diseño.
- **Descartado**: Redis (sin reservas ni bot no hace falta: la concurrencia de pagos se resuelve
  con transacciones y bloqueos de PostgreSQL); app nativa (Flutter o React Native) en el MVP.
- **Por qué**: es el stack que Juani ya usó en AI-Native, y el que proponía la especificación.
- **Quién**: Juani.

## D-021 · Arquitectura: monolito modular, hexagonal por módulo, en español · *corregida en parte por D-040, D-046 y D-076*

- **Fecha**: 08/10/2026
- **Decisión**:
  - Una sola aplicación dividida en módulos por dominio: `barrios`, `acceso`, `gastos`,
    `liquidacion`, `cuenta_corriente`, `pagos`, `avisos`, más `compartido` (dinero en centavos,
    sesión de base, tenancy, auditoría).
  - Cada módulo con capas `dominio` (reglas puras), `aplicacion` (casos de uso),
    `infraestructura` (base de datos) y `api` (FastAPI). Las dependencias apuntan hacia adentro.
  - Los módulos se comunican sólo por su capa `aplicacion`; nunca tocan tablas ajenas.
  - Muchos barrios en una sola base, cada fila con su barrio, y Row-Level Security de PostgreSQL
    como segundo candado de R10.
  - La cuenta corriente es un libro de sólo agregar movimientos (R08).
  - Tests en tres niveles: unitarios (reglas, sin base), integración (PostgreSQL real en Docker)
    y aceptación (la liquidación del piloto al centavo).
  - Nombres del dominio en español, iguales al glosario.
- **Descartado**: microservicios ("motores" separados de la especificación), que multiplican el
  costo de despliegue y depuración para un equipo chico; una base por barrio; código en inglés.
- **Fuera de esta decisión**: tablas, endpoints y pantallas concretas, que van en el *design* de
  cada change de OPSX (D-007).
- **Quién**: Juani.

## D-022 · Juani programa el MVP · *corregida en parte por D-093*

- **Fecha**: 08/10/2026
- **Decisión**: el desarrollo del MVP lo hace Juani. El roadmap se planifica para un solo desarrollador.
- **Quién**: Juani.

## D-023 · Tesorería y contabilidad integral quedan fuera del MVP · *corregida en parte por D-031*

- **Fecha**: 08/10/2026
- **Decisión**: el MVP lleva la cuenta corriente de cada unidad, no el saldo de caja del barrio,
  los fondos (operativo, de reserva, de obras) ni una contabilidad integral con plan de cuentas.
  También se confirman las historias HU-A1 (configurar el barrio), HU-A9 (corregir sin perder
  historial) y HU-V1 (entrar con email e instalar el portal), derivadas de decisiones anteriores.
- **Por qué**: el objetivo del MVP es liquidar y cobrar; la tesorería no hace falta para
  reproducir una liquidación ni para imputar pagos. Pasa a la fase F6.
- **Quién**: Juani (propuesto por Claude al escribir `mvp.md`).

## D-024 · Ordinaria y extraordinaria separadas, ordinaria primero al imputar

- **Fecha**: 08/10/2026
- **Decisión**: cada gasto es ordinario o extraordinario; una obligación por unidad y período con el
  capital desglosado; la expensa muestra los dos bloques; al imputar, intereses, ordinaria y después
  extraordinaria. Detalle en R13 y R04.
- **Descartado**: dos obligaciones separadas por período (duplica vencimientos y avisos) y no
  distinguirlas (la especificación las distingue y más adelante importa quién paga cada una).
- **Quién**: Claude, por delegación explícita de Juani ("decidilas vos con lo más recomendado").

## D-025 · Cargos particulares a una sola unidad, manuales o por Excel

- **Fecha**: 08/10/2026
- **Decisión**: el administrador puede cargar importes a una unidad puntual, sueltos o importados
  desde un Excel, con aprobación previa. Entran como líneas propias de la parte ordinaria. Los
  créditos particulares van como corrección. Detalle en R14.
- **Por qué**: la especificación los prevé (quincho, canon, consumos) y sin ellos el administrador
  tendría que seguir llevando una planilla aparte.
- **Quién**: Claude, por delegación explícita de Juani.

## D-026 · El consumo variable de agua no se calcula en el MVP

- **Fecha**: 08/10/2026
- **Decisión**: no hay lecturas de medidor ni tarifas por rango en el MVP. Un barrio que cobra agua
  por consumo la carga como cargos particulares importados desde un Excel (R14).
- **Descartado**: modelar medidores, lecturas y rangos de litros ahora.
- **Por qué**: pocos barrios miden por lote y el cálculo por rangos es un módulo en sí mismo; la
  importación cubre el caso sin construirlo. El cálculo automático pasa a la fase F6.
- **Quién**: Claude, por delegación explícita de Juani.

## D-027 · El MVP arranca por edificios; los barrios privados vienen después

- **Fecha**: 09/10/2026
- **Decisión**: el MVP atiende edificios en propiedad horizontal. El modelo sigue soportando
  barrios desde el día uno (D-008 en lo que hace al diseño), pero no se configuran ni se prueban
  en el MVP. **Reemplaza a D-008** en cuanto al orden.
- **Descartado**: barrios primero.
- **Por qué**: pedido de Alberto (audios del 09/10): el contacto con edificios se consigue más
  directo. Costo aceptado: en edificios se compite de frente con CONSO y AdminProp, así que la
  diferencia tiene que estar en la cercanía, la transparencia para el vecino y el historial de
  activos (el ascensor y la bomba son el caso típico).
- **Quién**: Alberto, aceptado por Juani.

## D-028 · El sueldo del encargado entra como gasto, no se calcula

- **Fecha**: 09/10/2026
- **Decisión**: el administrador carga el recibo que liquidó el contador (sueldo y cargas
  sociales) como un gasto más. El cálculo con la escala SUTERH queda para la fase F4.
- **Descartado**: liquidar sueldos en el MVP, aunque CONSO lo ofrece como diferencial.
- **Por qué**: hoy lo liquida un contador; calcularlo trae riesgo laboral alto y un módulo entero.
- **Quién**: Juani (recomendación de Claude).

## D-029 · Tipos de unidad y agrupación por persona

- **Fecha**: 09/10/2026
- **Decisión**: departamento, cochera, baulera y local son unidades funcionales con su propio
  coeficiente. Se liquida por unidad; el portal agrupa todas las unidades de la misma persona de
  contacto y, al informar un pago, el vecino elige a qué unidad va o lo reparte.
- **Quién**: Juani (recomendación de Claude).

## D-030 · El estado de unidad queda apagado en edificios · *ampliada por D-089*

- **Fecha**: 09/10/2026
- **Decisión**: la regla R02 (factor y cargo por estado) sigue en el sistema para los barrios,
  desactivada por default en edificios.
- **Quién**: Juani (recomendación de Claude).

## D-031 · Fondo de reserva como concepto de la expensa, sin tesorería · *corregida en parte por D-081*

- **Fecha**: 09/10/2026
- **Decisión**: cada edificio configura un porcentaje de fondo de reserva sobre la expensa ordinaria,
  que aparece como línea propia en la liquidación (R15). No se lleva el saldo acumulado ni el saldo
  de caja: la tesorería sigue fuera del MVP. **Ajusta a D-023** en ese punto.
- **Por qué**: en edificios el fondo de reserva es una línea habitual de la expensa; sin ella no se
  reproduce la liquidación del piloto.
- **Quién**: Juani (recomendación de Claude).

## D-032 · El inquilino sigue fuera del MVP, como riesgo a validar

- **Fecha**: 09/10/2026
- **Decisión**: se mantiene D-009: paga la persona de contacto de la unidad. Como en edificios los
  inquilinos son frecuentes, se valida con el piloto que alcance.
- **Quién**: Juani (recomendación de Claude).

## D-033 · El piloto es un edificio con contacto directo de Alberto

- **Fecha**: 09/10/2026
- **Decisión**: el piloto de M1 es un edificio que consigue Alberto. Responde en parte a P1: falta
  saber cuál es y cuándo entrega sus datos.
- **Quién**: Alberto.

## D-034 · El documento para Alberto se rehace para edificios, con el prompt como anexo

- **Fecha**: 09/10/2026
- **Decisión**: el informe de MVP y roadmap se regenera con el enfoque en edificios, y al final
  lleva el prompt literal que permite producir documentos de este tipo en otros proyectos.
- **Quién**: Alberto (pedido) y Juani.

## D-035 · Koris y PropTech son el mismo proyecto

- **Fecha**: 09/10/2026
- **Decisión**: "koris" (o Kooris) es el nombre con que Alberto trabaja el mismo proyecto. La landing
  kooris-explora.vercel.app y el documento "Arquitectura de koris, contada a lo criollo" (7/10/2026)
  son de este proyecto. El nombre de trabajo sigue siendo PropTech (D-001).
- **Corrige**: D-001 trataba a Kooris como competidor. Los precios de la landing (ARS 2.900 por
  unidad, Profesional ARS 4.200) y su programa de 10 administradores fundadores son una propuesta de
  Alberto: pasan a ser el punto de partida de P8. La investigación de mercado del 08/10 (informe "Discovery Kooris Mendoza") era,
  sin saberlo, sobre el propio proyecto.
- **Fuente de arquitectura**: el documento de Alberto queda en
  `../especificacion/arquitectura-alberto/`. Lo que el MVP toma o posterga de él está en D-036 a D-039.
- **Quién**: Juani.

## D-036 · El frontend es Next.js

- **Fecha**: 09/10/2026
- **Decisión**: la app web se hace con Next.js (App Router) y TypeScript, sigue siendo instalable
  como PWA. El servidor de Next guarda el token de sesión (el navegador nunca lo ve) y genera el
  número de seguimiento de cada pedido. **Ajusta a D-020.**
- **Descartado**: una app React que corre sólo en el navegador.
- **Por qué**: es lo que define la arquitectura de Alberto, la seguridad de su diseño depende de ese
  servidor intermedio, Juani ya lo usó en Misresumenes (Next.js 16) y van a trabajar a la par.
- **Costo aceptado**: un contenedor Node más y separar bien qué corre en servidor y qué en navegador.
- **Quién**: Juani.

## D-037 · Permisos del MVP: la forma de Alberto con cuatro roles

- **Fecha**: 09/10/2026
- **Decisión**: se mantienen las tres capas de la arquitectura de Alberto (administración deducida
  del login, alcance por edificio, permiso por rol), con cuatro roles:
  - **Titular**: todo, incluido cerrar liquidaciones y anular pagos.
  - **Colaborador**: sólo los edificios asignados, nivel "ver" o "editar"; no cierra ni anula.
  - **Consejo**: sólo lectura de su edificio.
  - **Vecino**: sus unidades.
  Fuera de alcance responde 404; sin permiso, 403 con el permiso faltante. **Amplía a D-009.**
- **Descartado**: las ~15 áreas con 3 niveles del documento de Alberto (se suman cuando un cliente
  las pida) y los actores contador, encargado y proveedor como usuarios.
- **Quién**: Juani.

## D-038 · Redis y un worker entran en el MVP

- **Fecha**: 09/10/2026
- **Decisión**: Redis como cola y contador, con un worker aparte (ARQ, como propone Alberto) para
  PDFs, emails y lectura de facturas con IA, con reintentos espaciados e idempotencia. La API y el
  worker comparten el mismo código de dominio. **Ajusta a D-020**, que descartaba Redis.
- **Por qué**: el MVP ya genera PDFs, manda emails y llama a la IA; hacerlo mientras el usuario
  espera no escala ni con un edificio de 40 unidades. Juani: "no es algo de otro mundo".
- **Quién**: Juani.

## D-039 · Del resto del documento de Alberto se mantiene lo ya acordado · *corregida en parte por D-046 y D-047*

- **Fecha**: 09/10/2026
- **Decisión**: para lo demás rigen las decisiones previas. En particular:
  - **Montos en centavos enteros (R07)**. El documento de Alberto usa Decimal (NUMERIC 14,2). Las dos
    opciones son correctas y el reparto por mayor resto es el mismo; queda anotado como diferencia a
    validar con él.
  - **No entran en el MVP**: cifrado de datos personales con índice ciego, patrón outbox, copiloto
    de IA, bandeja de WhatsApp, Cloudflare Turnstile.
  - **El método de login** (Clerk para el personal y enlace mágico para vecinos, según Alberto) no se
    decidió en esta charla: se resuelve en el *design* del primer change de OPSX.
- **Coincidencias con su documento que confirman lo decidido**: monolito modular hexagonal, RLS con
  `SET LOCAL`, mayor resto, libro de sólo agregar, dos fechas por pago, mora registrada por eventos,
  IA que sólo propone, extractos subidos a mano, Docker en un VPS.
- **Quién**: Juani.

## D-040 · Estructura del repositorio con un paquete de dominio compartido

- **Fecha**: 09/10/2026
- **Decisión**: un solo repositorio con `conocimiento/`, `openspec/`, `web/` (Next.js, con áreas
  `(admin)`, `(consejo)` y `(vecino)`), `backend/` e `infra/` (docker-compose, Caddyfile, backups).
  En `backend/src/`, tres paquetes: `proptech_core` (dominio compartido, equivalente a `koris_core`),
  `proptech_api` (routers FastAPI) y `proptech_worker` (tareas). Cada módulo de `proptech_core`
  tiene `dominio/`, `aplicacion/`, `puertos.py` y `adaptadores/`. El módulo `barrios` pasa a llamarse
  `complejos`, porque sirve a edificios y barrios.
- **Ajusta a D-021**: la capa `api` sale de cada módulo y vive en `proptech_api`, porque el dominio
  lo comparten la API y el worker (D-038).
- **Quién**: Juani (estructura propuesta por Claude para el informe).

## D-041 · Categorías de gasto parametrizables por el administrador

- **Fecha**: 09/10/2026
- **Decisión**: además del grupo de reparto (quién paga) y del tipo (ordinario o extraordinario),
  cada gasto tiene una **categoría** (en qué se gasta): encargado y cargas sociales, seguridad,
  limpieza, ascensor, mantenimiento, servicios, seguros, administración, varios. El administrador
  crea, renombra y ordena las categorías de su edificio; arranca con las precargadas del archivo de
  parámetros (D-042). La expensa y el portal muestran los gastos en los bloques ordinaria y
  extraordinaria y, dentro de cada uno, agrupados por categoría con su subtotal. Detalle en R16.
- **Por qué**: pedido de Alberto (audio del 09/10): un edificio puede tener portero y además
  seguridad o limpieza contratadas, y el vecino tiene que ver de un vistazo en qué se va la plata.
  Refuerza la transparencia, que es el diferencial frente a la competencia.
- **Descartado**: usar los grupos de reparto como categorías (mezcla quién paga con en qué se gasta).
- **Quién**: Alberto (pedido) y Juani.

## D-042 · Archivo de parámetros generales para arrancar

- **Fecha**: 09/10/2026
- **Decisión**: el repositorio tiene un archivo `config/parametros.yaml` con los valores iniciales:
  tasa de interés, días de gracia, forma de cálculo, porcentaje de fondo de reserva, categorías de
  gasto precargadas, grupos de reparto típicos, tipos de unidad y estados. Al crear un edificio esos
  valores se copian a su configuración, que el administrador ajusta desde la pantalla (HU-A1).
  Cambiar el archivo no altera edificios ya creados.
- **Por qué**: pedido de Alberto (audio del 09/10): para el MVP y el piloto hace falta un lugar
  único y editable donde están los parámetros con que arranca el sistema, sin tocar código.
- **Descartado**: defaults escritos dentro del código.
- **Quién**: Alberto (pedido) y Juani.

## D-043 · Caddy como proxy; se prefieren alternativas sin costo

- **Fecha**: 09/10/2026
- **Decisión**: se confirma Caddy como única puerta a Internet: es libre y gratuito y renueva solo
  los certificados HTTPS. Nginx, igual de gratuito, queda como alternativa si algún día hace falta.
  Criterio general del proyecto: ante dos opciones equivalentes, la que no tiene costo de licencia ni
  cobro por uso.
- **Por qué**: Alberto pidió buscar siempre alternativas que no sean onerosas y preguntó por Nginx.
  Con un solo servidor y un equipo chico, la ventaja de Caddy (HTTPS sin configuración) pesa más.
- **Quién**: Juani, con la consulta de Alberto.

## D-044 · Los cálculos en Python del zip se revisaron como referencia

- **Fecha**: 09/10/2026
- **Decisión**: se recuperaron del zip original de la especificación (`Funcionalidades_PropTech.zip`)
  y se revisaron los cálculos que Alberto señaló. Siguen sin reutilizarse como código (D-002), pero
  quedan como referencia de la intención del negocio:
  - **Imputación (B06)**: aplica el pago a lo más viejo, pero un pago parcial deja la expensa como
    impaga sin registrar cuánto se cubrió, y no separa intereses de capital. Corregido en R04 y R05.
  - **Mora (B33)**: capitaliza diario y usa una variable no declarada. Corregido en R03.
  - **Sueldo del encargado (B18)**: básico más antigüedad más plus por unidad, horas extra al 50% y
    100% con divisor 200, aportes 11%, 3% y 3%, cargas patronales 24%. Es la referencia para la fase
    F4; esos valores irán al archivo de parámetros y se validan con un contador.
  - **Migración (B44)**: tolerancia de coeficientes de 0,9999 a 1,0001 y sólo saldos positivos.
    R09 cubre también los créditos.
  - Coincidencia a favor de Alberto: B06 usa Decimal, igual que su documento de arquitectura (ver D-039).
- **Quién**: Juani.

## D-045 · El MVP se construye en 15 cambios de OPSX · *corregida por D-047, D-049, D-052 y D-077*

- **Fecha**: 09/10/2026
- **Decisión**: OpenSpec quedó inicializado en el repositorio (`openspec/`, idioma español, con
  `conocimiento/` como fuente de verdad en su configuración). Se saltea el paso de generar una base de
  conocimiento automática: la base es `conocimiento/`. El MVP se divide, como propuesta inicial, en:
  - **M1 · Liquida**: 1 `base-del-proyecto`, 2 `acceso-y-aislamiento`, 3 `configuracion-del-edificio`,
    4 `importacion-desde-excel`, 5 `motor-de-cuenta-corriente`, 6 `gastos-y-cargos`,
    7 `liquidacion-y-emision`.
  - **M2 · Cobra**: 8 `pagos-informados`, 9 `extracto-bancario`, 10 `morosidad`,
    11 `portal-del-vecino`, 12 `vista-del-consejo`, 13 `avisos-por-email`.
  - **M3 · Piloto**: 14 `lectura-de-facturas`, 15 `piloto-en-paralelo`.
  Cada cambio pasa por el ciclo completo antes de arrancar el siguiente. Un explore general sobre
  todo el MVP confirma el orden y las dependencias; después, explore por cambio sólo si hace falta.
- **Pendiente**: el resultado del explore general puede ajustar esta lista (se registrará como
  decisión nueva).
- **Quién**: Juani.

## D-046 · Los montos son Decimal, no centavos enteros

- **Fecha**: 09/10/2026
- **Decisión**: todo importe es `Decimal` en Python (construido siempre desde texto, nunca desde
  `float`), `NUMERIC(14,2)` en PostgreSQL y texto en el JSON (`"20000.00"`). El frontend nunca calcula
  montos, sólo los formatea. El reparto sigue siendo por mayor resto (R07). **Reemplaza la
  representación en centavos de D-015 y D-039.**
- **Descartado**: centavos enteros. Igual de correctos, pero distintos de lo que eligieron el
  documento de arquitectura de Alberto y el código original.
- **Por qué**: hay que decidirlo antes del primer cambio porque toca todas las tablas con plata, y
  conviene arrancar alineados con Alberto, que va a trabajar a la par. Es además más legible.
- **Quién**: Claude, por delegación explícita de Juani ("como vos lo veas mejor").

## D-047 · Ajustes al plan de cambios después del explore general · *corregida en parte por D-049 y D-080*

- **Fecha**: 09/10/2026
- **Decisión**: se aceptan las propuestas del explore general
  (`openspec/exploraciones/2026-10-09-estructura-del-mvp.md`):
  1. `motor-de-cuenta-corriente` pasa a ser el cambio 4 e `importacion-desde-excel` el 5, porque el
     saldo inicial (R09) genera obligaciones y créditos que define el motor. **Ajusta a D-045.**
  2. El método de login se decide en el *design* de `acceso-y-aislamiento` (cambio 2). **Precisa a D-039.**
  3. La gestión del edificio piloto (P1) arranca ya, en paralelo al cambio 1.
  4. `base-del-proyecto` incluye: CI que corre los tests en cada push, `config/parametros.yaml` y su
     lector, un edificio de ejemplo como datos semilla, logs estructurados con número de seguimiento
     y backups automáticos. Si al proponerlo queda demasiado grande, se parte en dos.
  5. `liquidacion-y-emision` sigue siendo un cambio, con sus tareas en dos bloques: preliquidación
     (sin efectos) y emisión (con efectos).
  6. Explore propio antes del propose para `acceso-y-aislamiento`, `motor-de-cuenta-corriente` y
     `liquidacion-y-emision`; los demás van directo a propose.
  7. El *design* de `liquidacion-y-emision` resuelve qué pasa si falla el encolado del PDF después de
     emitir (sin outbox): como mínimo, un estado por emisión y una forma de reprocesar.
  8. El PDF de la expensa cuenta como interfaz: pasa por la skill impeccable.
- **Quién**: Claude, por delegación explícita de Juani.

## D-048 · Forma de trabajo: orquestador y agentes en secuencia, aprueba el auditor · *corregida en parte por D-049 y D-093*

- **Fecha**: 09/10/2026
- **Decisión**: Juani trabaja solo. Cada cambio sigue un ciclo secuencial que orquesta Claude:
  proponer, construir (un agente codea con TDD), romper (otro agente intenta romperlo y deja las
  fallas como tests), auditar (otro agente revisa lo que hizo y pensó cada uno) y archivar. **Un
  cambio está aprobado cuando el auditor da el OK.** Detalle en `forma-de-trabajo.md`.
- **Agregado por Claude**: Juani aprueba la propuesta de los cambios críticos; tope de tres vueltas
  antes de frenar y consultar. **Sin ramas** (Juani: "si lo trabajo yo nomás"): todo sobre `main`,
  commit al archivar cada cambio y push siempre consultado.
- **Descartado**: el esquema completo de la configuración global (senior en cada fase, tres pases
  adversariales independientes, especialistas por capa), por costo; y PRs revisados por Alberto,
  porque el desarrollo es de Juani.
- **Quién**: Juani.

## D-049 · Roadmap de 16 cambios y push al cerrar cada cambio · *corregida en parte por D-052, D-077 y D-094*

- **Fecha**: 09/10/2026
- **Decisión**: el plan queda escrito en `roadmap.md`, con una ficha por cambio que sirve de entrada
  al propose. Ajustes sobre D-047, decididos por Claude con delegación de Juani después del borrador
  del explore:
  - El cambio 1 se parte en **1a `infraestructura-base`** y **1b `arranque-del-sistema`**.
  - El reparto por mayor resto (R07) es una función pública del cambio 4; el cambio 6 la usa para R01.
  - Decimal queda cerrado por D-046; a Alberto sólo se le informa.
  - El cambio 9 va después del 8; el 6 deja la lectura de facturas para el 14.
  - El cambio 4 depende también del 2 (persistir con el tenant fijado).
- **Push**: Juani autoriza commit y push a `main` al archivar cada cambio con el OK del auditor
  ("queda perfecto, commit y push"). Ajusta la regla general de preguntar siempre, sólo para este
  proyecto y sólo en ese momento del ciclo.
- **Quién**: Juani, con las decisiones de detalle delegadas a Claude.

## D-050 · Lecciones aprendidas y escalado del ciclo por riesgo · *escrita antes de la cuarta vuelta del 1a (D-051)*

- **Fecha**: 09/10/2026
- **Decisión**: se crea `lecciones.md`, de sólo agregar: el auditor propone en cada veredicto lo que el
  ciclo enseñó y el orquestador lo registra al archivar; constructor y rompedor lo leen antes de cada
  cambio. Además, el ciclo se escala por riesgo: completo para los cambios críticos, los que tocan
  plata y la infraestructura; una pasada única de romper y auditar para los chicos o de sólo lectura.
  Detalle en `forma-de-trabajo.md`.
- **Por qué**: en el cambio 1a el auditor encontró dos bugs que el constructor y el rompedor no vieron,
  y hicieron falta tres vueltas. Con las lecciones de entrada, el rompedor ataca esos puntos ciegos
  desde la primera vuelta. El ciclo completo cuesta mucho para cambios chicos.
- **Quién**: Juani (propuesta de Claude).

## D-051 · Herramientas y versiones de la infraestructura base (cambio 1a) · *sus notas para el cambio 2 quedaron en su ficha*

- **Fecha**: 09/10/2026
- **Decisión** (detalle en `openspec/changes/archive/*-infraestructura-base/design.md`, D1 a D11):
  - **Python 3.14** con **uv**; FastAPI 0.143, SQLAlchemy 2.1, Alembic 1.20, psycopg 3.3,
    pydantic-settings 2.15. **Ruff** (lint y formato), **mypy estricto** con el plugin de pydantic,
    **pytest** con **testcontainers** (PostgreSQL real, la misma imagen que Compose).
  - **Node 24** con **pnpm**; Next.js 16.4, React 19.3, **TypeScript 6.0.3** (no 7, por compatibilidad
    con Next), **Biome** (lint y formato), **Vitest** 5 con Vite fijado en 7.3.7.
  - Imágenes con versión de parche exacta: `postgres:18.6-trixie`, `caddy:2.11.7-alpine`,
    `python:3.14.8-slim-trixie`, `node:24.21.0-alpine`. Contenedores sin root.
  - **GitHub Actions** con acciones fijadas por SHA, jobs `backend`, `web`, `humo` y `secretos`
    (gitleaks 8.30.1) y un **canario** que prueba que el CI falla con un test roto sin pushear uno.
  - Compose con nombre de proyecto `proptech`, migraciones como servicio aparte, sólo Caddy con puertos
    públicos, red `interna` sin salida a Internet.
- **Descartado**: services de PostgreSQL de GitHub Actions (obligaban a publicar el puerto en local),
  Postgres en Alpine, TypeScript 7, ESLint y Prettier (reemplazados por Biome), pushear un test roto
  para probar el CI.
- **Notas para cambios siguientes**: separar web y base de red en el cambio 2; ocultar los encabezados
  `Via` y `X-Powered-By` y revisar HEAD en el cambio 2; comillas en `pg_isready` y el test tautológico
  del fixture en el 1b.
- **Quién**: proponente y constructor del cambio 1a, aprobado por el auditor (vuelta 4).

## D-052 · El cambio 1b se parte: arranque mínimo en 1b, cola, logs y respaldos aparte · *corregida en parte por D-077*

- **Fecha**: 09/10/2026
- **Decisión**: el cambio 1b tenía 90 tareas y el constructor completó sólo la primera parte con
  evidencia. Se parte en:
  - **1b `arranque-del-sistema`**: configuración (incluidas las variables de Redis, conectadas ya en
    Compose), tipo `Dinero`, `parametros.yaml` con su lector validado y el edificio de ejemplo como
    archivo validado (se carga en la base en el cambio 3). Las migraciones dependen sólo de PostgreSQL.
  - **1c `cola-logs-y-respaldos`**: logs estructurados con número de seguimiento de punta a punta,
    Redis y el worker ARQ con idempotencia, `/salud-web`, respaldos con prueba de restauración, humo y README.
  - **Propuesta pendiente**: si 1c supera lo que entra en una vuelta del constructor (unas 20 tareas),
    se parte otra vez dejando respaldos, humo y README como 1d.
- **Por qué**: un ciclo tiene que poder revisarse entero; un rompedor y un auditor sobre 90 tareas es
  donde se escapan los errores.
- **Quién**: Juani.

## D-053 · Elecciones del cambio 1b (arranque del sistema) · *sus notas quedaron en la ficha del cambio 4*

- **Fecha**: 11/10/2026
- **Decisión** (detalle en `openspec/changes/archive/*-arranque-del-sistema/design.md`):
  - `Configuracion` exige también `REDIS_*` y `PROPTECH_PARAMETROS`; las migraciones usan
    `ConfiguracionBaseDeDatos`, que sólo depende de PostgreSQL.
  - `Dinero` sobre `Decimal`: sólo desde texto con coincidencia completa y dígitos ASCII, sin
    aritmética; `TipoDinero` como `NUMERIC(14,2)`; `desde_decimal` rechaza en vez de redondear.
  - `parametros.yaml` y la semilla se leen con un cargador propio que rechaza claves duplicadas y
    claves que no son texto, limita el tamaño a 1 MiB, convierte cualquier falla del parser en un error
    propio con línea y columna, y nunca repite valores (las claves sí pueden aparecer, son la ruta).
  - El edificio de ejemplo es un archivo validado (`config/semilla/edificio-ejemplo.yaml`, 13
    unidades); se carga en la base en el cambio 3.
- **Notas**: `leer_parametros` tiene un `except TypeError` que hoy no se alcanza (código muerto a
  limpiar); `Dinero` acepta ceros de más (`1.0000` → `1.00`).
- **Quién**: proponente y constructor del 1b, aprobado por el auditor (vuelta 4).

## D-054 · El MVP sigue siendo el nuestro; los documentos de Alberto aportan dolores y el motor de reglas

- **Fecha**: 12/10/2026
- **Decisión**: el MVP sigue siendo sólo edificios y el de `mvp.md`. El documento de Alberto "ProTecc,
  problemas operativos y reglas v3.5" (10/10/2026) se usa como fuente de **dolores y problemas**: se
  analizan sus 42 casos, se resuelven los que tocan al MVP y se integran a la base de conocimiento; lo
  que excede el MVP (barrios, egresos y otros) va a `proyecto-final.md`. Después se investiga el motor
  de reglas de negocio que pidió Alberto y cómo integrarlo. Mientras tanto no se escribe código.
- **Fuentes**: `especificacion/documentos-alberto/` (fuera del repositorio público).
- **Quién**: Juani.

## D-055 · Ventana de anulación de una liquidación emitida y no distribuida · ajusta R08/D-016 · *corregida en parte por D-073 y D-074*

- **Fecha**: 12/10/2026
- **Decisión**: una liquidación emitida se puede anular sólo si todavía no fue distribuida: no
  salió el primer email de aviso y ningún vecino la vio en el portal. La anulación queda registrada
  con motivo y responsable. Desde el momento en que se distribuye, rige R08/D-016 sin excepciones:
  todo error se corrige con un movimiento nuevo. Detalle en R17.
- **Descartado**: anular en cualquier momento después de emitida (contradice R08 de lleno); exigir
  siempre el ajuste del mes siguiente aunque el error se detecte antes de que cualquier vecino la vea.
- **Por qué**: es el único punto donde el documento de Alberto choca con nuestra decisión D-016. La
  ventana acotada (emitida y todavía no vista por nadie) no abre la puerta a editar en silencio lo
  que un vecino ya vio; protege la misma transparencia que D-016 buscaba, sin la rigidez de esperar
  un mes por un error que nadie llegó a ver.
- **Fuente**: `openspec/exploraciones/2026-10-12-dolores-protecc.md` (caso ProTecc A5, pregunta Q10
  de Alberto).
- **Quién**: Juani.

## D-056 · Estado "revertido" para un pago confirmado que el banco devuelve · *corregida en parte por D-074*

- **Fecha**: 12/10/2026
- **Decisión**: se agrega el estado **revertido** a R11, para un pago confirmado que el banco
  rechaza o devuelve (cheque rechazado, contracargo, transferencia revertida). Se registra como un
  movimiento de reversión (débito) que referencia al pago original; el pago original nunca se borra
  ni pasa a "rechazado". La unidad se reevalúa para morosidad. Detalle en R18.
- **Descartado**: tratarlo sólo como una corrección genérica de R08, sin estado propio.
- **Por qué**: aplica a edificios igual que a barrios (un cheque se puede rechazar en cualquiera) y
  le da trazabilidad al vecino y al administrador sobre qué pasó realmente con ese pago.
- **Fuente**: análisis citado (caso ProTecc D4).
- **Quién**: Juani.

## D-057 · Código de unidad en el concepto y CBU histórico, como sugerencias de alta confianza

- **Fecha**: 12/10/2026
- **Decisión**: se adoptan dos mecanismos de R11: la boleta sugiere al vecino un código corto de su
  unidad para escribirlo en el concepto de la transferencia, y el sistema recuerda el CBU que pagó
  una unidad la última vez. Los dos entran a la bandeja de confirmación como sugerencias de
  confianza alta; ninguno asigna un pago en forma automática (principio P3 de Alberto). Detalle en
  R19.
- **Descartado**: esperar a medir con extractos reales antes de adoptarlos; construir ya la cola de
  excepciones completa con sugerencias ordenadas por confianza (queda para después del MVP, ver
  `proyecto-final.md`).
- **Por qué**: son baratos (no tocan el modelo de datos decidido ni el diseño de la boleta más que
  agregar un código) y reducen directamente los casos A1 y E3 de Alberto.
- **Fuente**: análisis citado (sección 3, casos ProTecc A1 y E3).
- **Quién**: Juani.

## D-058 · "Moroso crítico" se define por antigüedad, sin bloqueo de amenities · *corregida en parte por D-078*

- **Fecha**: 12/10/2026
- **Decisión**: una unidad es **moroso crítico** cuando tiene dos o más liquidaciones vencidas con
  saldo impago. Quedan excluidas las unidades con un plan de pago al día o con la deuda en gestión
  judicial, **si esos conceptos existen en el MVP**; hoy no existen (no hay plan de pago ni marca de
  gestión judicial en `mvp.md`), así que la exclusión queda anotada como límite conocido hasta que
  esos conceptos se construyan (ver R31 y `proyecto-final.md`, G1). No hay bloqueo de reservas de
  amenities: las reservas no están en el MVP. Detalle en R20.
- **Descartado**: una fórmula por monto de deuda (se rompe porque la expensa cambia de mes a mes y
  los pagos parciales la confunden, el mismo problema que Alberto marca en su v2); esperar a que el
  piloto lo pida.
- **Por qué**: es una consulta sobre datos que el MVP ya tiene (cuenta corriente, liquidaciones);
  sirve para priorizar cobranza desde el primer mes sin construir nada nuevo.
- **Fuente**: análisis citado (caso ProTecc M1, DEC-07/DEC-08 de Alberto).
- **Quién**: Juani.

## D-059 · El certificado de libre deuda por venta de unidad entra al MVP · *corregida en parte por D-077*

- **Fecha**: 12/10/2026
- **Decisión**: se agrega el certificado de libre deuda (o de deuda, si corresponde) para la venta
  de una unidad. Se genera desde la cuenta corriente con una fecha de corte, muestra el saldo a esa
  fecha e informa los pagos en revisión por separado, sin restarlos del saldo; lo firma el
  administrador. Nunca incluye una estimación de gastos del período en curso. Entra al cambio 10
  `morosidad` del roadmap (justificación en `roadmap.md`: se apoya en la misma cuenta corriente que
  ya alimenta la vista de morosidad, sin agregar una dependencia nueva). Detalle en R21.
- **Descartado**: dejarlo fuera del MVP y seguir resolviéndolo a mano, como hace hoy cualquier
  administrador sin sistema.
- **Por qué**: Alberto lo marca como frecuente y urgente en edificios reales (compraventas); es
  barato de construir sobre una cuenta corriente que el MVP ya tiene.
- **Fuente**: análisis citado (caso ProTecc G3).
- **Quién**: Juani.

## D-060 · Investigar los requisitos legales de la liquidación en Mendoza antes del design del cambio 7

- **Fecha**: 12/10/2026
- **Decisión**: antes de cerrar el *design* de `liquidacion-y-emision` (cambio 7), se investiga qué
  exige la normativa de Mendoza para una expensa. Alberto cita como referencia la Ley 941 de CABA,
  que no aplica en Mendoza; hay que relevar qué rige acá. Se agrega como prerrequisito del cambio 7
  en `roadmap.md`.
- **Descartado**: asumir que no hay requisitos especiales y corregir recién si aparece un reclamo.
- **Por qué**: es una tarea de investigación chica y barata, comparada con el costo de rehacer la
  plantilla de la expensa (que pasa por la skill impeccable) después de ya estar emitiendo con ella.
- **Fuente**: análisis citado (caso ProTecc H4, pregunta Q12 de Alberto).
- **Quién**: Juani.

## D-061 · La nota de crédito es una entidad asociada a la factura que corrige

- **Fecha**: 12/10/2026
- **Decisión**: una nota de crédito queda asociada a la factura de proveedor que corrige y su monto
  no puede superar el de esa factura; se descuenta del gasto antes de prorratear, dentro del mismo
  grupo de reparto. Entra al cambio 6 `gastos-y-cargos`. Detalle en R22.
- **Descartado**: cargarla como un gasto negativo suelto, sin asociarla a la factura original (más
  simple, pero pierde la trazabilidad que R08 pide para toda corrección).
- **Por qué**: evita cobrarle de más a los vecinos por un gasto que el proveedor ya corrigió.
- **Fuente**: análisis citado (caso ProTecc H1, 12.13).
- **Quién**: Juani.

## D-062 · Centavos identificadores por unidad quedan para después del MVP

- **Fecha**: 12/10/2026
- **Decisión**: se posterga la asignación de centavos únicos por unidad en el monto de la boleta.
  Queda en `proyecto-final.md`, condicionada a responder primero la pregunta Q2 de Alberto (qué
  traen los extractos de los bancos de Mendoza) y Q18 (cómo convive con el prorrateo y el recargo),
  y a medir primero cuánto bajan los casos A1 y E3 los mecanismos ya adoptados en D-057.
- **Descartado**: adelantarlo ya, aceptando el riesgo de diseñarlo sin esa validación.
- **Por qué**: toca R07 (redondeo) y el diseño de la boleta, y el propio documento de Alberto lo
  condiciona a una métrica que todavía no existe (el 20% de pagos sin identificar de DEC-10).
- **Fuente**: análisis citado (sección 3).
- **Quién**: Juani.

## D-063 · Integración de los dolores de ProTecc (resumen) · *corregida en parte por D-075*

- **Fecha**: 12/10/2026
- **Decisión**: se integran a la base de conocimiento los 42 casos del documento de Alberto
  "ProTecc, problemas operativos y reglas v3.5" (10/10/2026), según el análisis
  `openspec/exploraciones/2026-10-12-dolores-protecc.md`:
  - **Entraron al MVP, decididos por Juani**: la ventana de anulación (D-055, R17), el estado
    revertido (D-056, R18), el código de unidad y el CBU histórico (D-057, R19), el moroso crítico
    por antigüedad (D-058, R20), el certificado de libre deuda (D-059, R21), la investigación de los
    requisitos legales de Mendoza antes del cambio 7 (D-060) y la nota de crédito asociada a la
    factura (D-061, R22).
  - **Entraron al MVP como propuesta, sin validar todavía con un administrador o contador**: los
    nueve huecos restantes del catálogo de 42 casos (ProTecc A2, A4, B2, G4, W3, W4, B5, D3, G2), como
    R23 a R31 en `reglas-de-negocio.md`, con sus criterios en las historias de usuario y su lugar en
    el roadmap. Ninguno de los nueve reabre una decisión vigente; se agregan como reglas en estado
    Propuesta o Pendiente, igual que R03 hoy.
  - **Quedaron para después del MVP, en `proyecto-final.md`**: los centavos identificadores (D-062),
    el pago en efectivo con recibo (ProTecc D5), las fallas y riesgos de WhatsApp (ProTecc W1, W2,
    W5), el plan de pago o convenio de deuda (ProTecc G1), la conciliación completa de caja y banco
    (ProTecc H3), los fondos como subcuentas independientes (ProTecc C3, ya fuera por D-023/D-031) y
    la excepción como entidad con sus métricas y la cola de sugerencias completa con dos señales
    independientes (principios P3 y P8 de Alberto, DEC-12).
  - **No se tocó ninguna decisión vigente**: donde Alberto propone algo distinto de lo ya decidido
    (centavos identificadores, cola de sugerencias completa), se posterga en vez de reabrir lo
    decidido.
- **Fuente**: `openspec/exploraciones/2026-10-12-dolores-protecc.md`.
- **Quién**: Juani.

## D-064 · Puerto de políticas desde ahora; motor de reglas de terceros cuando haga falta · *corregida en parte por D-066, D-067, D-074 y D-080*

- **Fecha**: 12/10/2026
- **Decisión**: la arquitectura incorpora desde ya un **puerto de políticas** en `proptech_core`: toda
  regla propia de cada edificio (recargos, multas, bonificaciones, cargos por estado, criterios de
  morosidad, alertas antes de emitir) entra por ahí. Recibe hechos y devuelve acciones propuestas con
  montos como texto `Dinero`; el núcleo valida todo lo que sale y corta en seco si algo no cierra, y
  cada acción se registra como movimiento con motivo (el motor decide qué, el núcleo decide cómo). En
  el MVP el puerto se implementa con los menús cerrados de `parametros.yaml`. Un motor de terceros
  (GoRules ZEN u otro) se enchufa detrás del mismo puerto cuando lleguen amenities o planes de pago.
- **Descartado**: llevar toda la lógica a un motor (el núcleo financiero R03 a R08 y R10 queda en
  código con tests); adoptar GoRules ya: la prueba del 12/10 mostró que trabaja con `float` y que ante
  un error de tipo saltea la regla en silencio y aplica la siguiente.
- **Fuente**: `openspec/exploraciones/2026-10-12-motor-de-reglas.md`.
- **Quién**: Juani, a partir del pedido de Alberto (12/10).

## D-065 · Motor de reglas propio en forma de catálogo de plantillas · *reemplazada por D-066*

- **Fecha**: 12/10/2026
- **Decisión propuesta**: el puerto de políticas (D-064) se implementa con un **motor propio de
  plantillas**: cada tipo de regla (intereses, fondo de reserva, cargo por estado, moroso crítico,
  alertas antes de emitir, bonificación por pronto pago, cargo recurrente del reglamento) es una pieza
  de código con parámetros validados, los datos que necesita, la acción que propone y sus tests. Cada
  edificio activa y ajusta las suyas; cada cambio de configuración es una versión con fecha y autor, y
  cada liquidación guarda las versiones que usó. Una regla que no puede calcularse genera una alerta
  que bloquea la emisión. Se construye dentro de los cambios 3, 7 y 10 del roadmap.
- **Descartado**: GoRules ZEN para el MVP (punto flotante y errores silenciosos) y un motor genérico
  propio con lenguaje libre (es un producto en sí mismo y trae el mismo riesgo de errores silenciosos).
- **Pendiente**: que Alberto valide el enfoque, el catálogo inicial y quién configura las reglas; recién
  entonces se actualizan las fichas 3, 7 y 10 del roadmap.
- **Documento**: "PropTech · Motor de reglas" (PDF entregado a Alberto, fuera del repositorio).
- **Quién**: Juani.

## D-066 · GoRules ZEN con editor visual detrás del puerto de políticas, con validador propio · *corregida en parte por D-067, D-080 y D-087; la propuesta de quién usa el editor pasó a dos niveles (P22)*

- **Fecha**: 12/10/2026
- **Decisión**: el puerto de políticas (D-064) se implementa con **GoRules ZEN** (`zen-engine`) y su
  editor visual **jdm-editor**, como en el material que pasó Alberto (demo BRE de la cátedra del
  Mgter. Ing. Carlos Martínez: FastAPI + ZEN, React + jdm-editor). Se adelanta al MVP lo que D-064
  dejaba para después. Las condiciones que lo hacen apto para plata:
  - **El motor decide, no calcula**: las reglas devuelven decisiones, porcentajes como texto,
    banderas y motivos; nunca una cuenta sobre un monto. Los montos los calcula el núcleo con
    `Dinero` (D-046).
  - **Validador propio en dos momentos**: al guardar una regla (rechaza aritmética sobre campos de
    plata y salidas que no cumplen el contrato) y al evaluarla (toda respuesta fuera de contrato o
    vacía bloquea la emisión con alerta, nunca se toma como "no hay regla").
  - **Reglas en la base, por edificio y versionadas**, con fecha y autor; cada liquidación guarda
    las versiones que usó. No archivos en disco como en el demo.
  - Detalle en `motor-de-reglas.md`.
- **Reemplaza a D-065**: Alberto prefiere no construir un motor propio (12/10).
- **Riesgo aceptado**: ZEN usa `float` y saltea en silencio una regla con error de tipo (prueba del
  12/10). Se mitiga con las condiciones de arriba; el validador es nuestro y es obligatorio.
- **Pendiente**: quién usa el editor en el MVP (propuesta: sólo el equipo de PropTech) y cómo se
  comparan montos dentro de una regla sin `float` (propuesta: en centavos enteros); se cierran en el
  explore del cambio 3.
- **Quién**: Alberto (pedido del 12/10, "vamos con lo que te paso"); Juani acepta.

## D-067 · ZEN calcula con decimales exactos; el riesgo real son las tablas que caen en silencio

- **Fecha**: 13/10/2026
- **Corrige a D-064 y D-066**: decían que ZEN "trabaja con `float`". Es falso. La prueba del 13/10 con
  `zen-engine` 2.1.3 muestra que calcula por dentro con decimales exactos (`0.1 + 0.2` da `0.3`;
  `string(number("100") / 3)` da `"33.333333333333333333333333333"`); el `float` aparece sólo al
  devolver un número a Python. La prueba del 12/10 vio ese `float` de salida y lo tomó como el
  cálculo. Alberto lo había señalado ("funcionan los decimales").
- **Decisión**: una regla **puede calcular plata** siempre que la devuelva como texto con
  `string(...)`; el validador rechaza cualquier salida de plata que no sea texto. El redondeo al
  centavo lo hace el núcleo, una sola vez, al registrar (R07). Se cae la propuesta de pasar montos en
  centavos enteros: ya no hace falta.
- **Lo que sigue en pie**: las tablas de decisión eligen la fila por defecto en silencio si un dato
  llega con tipo incorrecto o falta (confirmado el 13/10). Lo cubren los datos de entrada con tipos
  fijos y el validador (R33).
- **Quién**: Juani, a partir del aviso de Alberto (12/10) y la prueba del 13/10.

## D-068 · El saldo inicial se compara unidad por unidad, no sólo el total

- **Fecha**: 13/10/2026
- **Decisión**: al migrar un edificio, los saldos importados quedan en un borrador y se comparan
  unidad por unidad contra el saldo de cada unidad según el administrador; el total queda como
  control adicional. Las diferencias se corrigen o se aceptan con registro. Al confirmar, el
  importador se cierra y los errores posteriores se corrigen con ajustes con motivo (R08). Detalle
  en R09.
- **Por qué**: con un solo total, dos errores de signo opuesto se compensan y nadie se entera. Es una
  corrección que Alberto hizo en su propio documento (ProTecc v3.5, sección 12.2).
- **Descartado**: comparar sólo el total (lo que decía R09 hasta hoy); bloquear la confirmación hasta
  que no quede ninguna diferencia, porque a veces la diferencia la tiene el Excel del administrador y
  no la importación.
- **Quién**: Juani, a partir del material de Alberto.

## D-069 · Controles antes de emitir con dos niveles y emisión con alertas aceptadas · *corregida en parte por D-078, D-080 y D-081*

- **Fecha**: 13/10/2026
- **Decisión**: antes de emitir, el sistema corre una lista de controles, cada uno bloqueante o
  advertencia. Con un bloqueo activo se puede emitir sólo aceptando la alerta de forma explícita, y la
  aceptación queda registrada. Una diferencia nunca se tapa con un movimiento inventado. Detalle y
  lista del MVP en R34; se construye en el cambio 7 y cada control entra con su cambio.
- **Por qué**: es el pedido de Alberto (ProTecc v3.5, secciones 7.2 y 12.5): lo que salva al
  administrador el día que algo sale mal. La exploración del 12/10 ya lo recomendaba para el MVP.
- **Adaptado al MVP**: de su lista quedan afuera medidores (D-026), diferencia entre caja y banco
  (D-023) y WhatsApp, porque esas funciones no están en el MVP. El extracto incompleto pasa de
  bloqueante a advertencia, porque en el MVP el extracto es una ayuda y no el camino de los pagos
  (D-017).
- **Quién**: Juani, a partir del material de Alberto.

## D-070 · Links de descarga firmados y con vencimiento

- **Fecha**: 13/10/2026
- **Decisión**: ningún archivo del sistema (PDF de expensas, comprobantes de pago, facturas) tiene una
  dirección pública. Cada descarga usa un link **firmado**, que deja de funcionar si alguien lo
  modifica, y que **vence** entre un minuto y una hora. Un link vencido, modificado o pedido por quien
  no tiene acceso a esa unidad responde "no encontrado", sin decir si el archivo existe. El mecanismo
  se arma en el cambio 7 (PDF de la expensa) y lo reusan el 8 (comprobantes), el 11 (portal) y el 14
  (facturas).
- **Por qué**: un link fijo que se reenvía por mail o en el grupo del edificio deja ver la deuda y los
  datos de una unidad. Es pedido de Alberto (arquitectura de koris, "candados en capas"), que lo pone
  entre sus prioridades de calidad, después de la plata. Hacerlo desde el principio cuesta poco;
  agregarlo después obliga a cambiar cada descarga.
- **Quién**: Juani, a partir del material de Alberto.

## D-071 · Diez huecos del catálogo de 100 casos de Alberto, resueltos como propuestas · *corregida en parte por D-079*

- **Fecha**: 13/10/2026
- **Origen**: el documento de Alberto con 100 casos de negocio y de borde (13/10). La mayoría ya estaba
  en la base o quedó fuera del MVP a propósito. Diez eran huecos reales.
- **Decisión**: cada hueco queda resuelto en la base como **propuesta**, a validar con Alberto o con un
  administrador: vencimiento en día inhábil (R35, caso 25); tasa propia para la extraordinaria (R36,
  caso 26); condiciones de la bonificación por pronto pago, incluido que una multa nunca se bonifica
  (R37, casos 5, 14 y 43); ingresos del consorcio (R38, casos 42 y 49); unidades del propio consorcio
  (R39, caso 33); períodos en orden (R40, caso 94); baja de deuda incobrable (R41, caso 78); control de
  gasto mensual obligatorio faltante (R34, caso 96); IVA incluido en el gasto (R12, caso 97).
- **Descartado del documento**: redondear hacia arriba a favor del consorcio (caso 11; choca con R07,
  la suma da exacta); capitalizar intereses (caso 31; prohibido por el art. 770 salvo orden judicial);
  repartir por días la deuda en una venta (caso 86; es la pregunta P11 y su respuesta no está validada);
  presentar el libre deuda como de "validez jurídica absoluta" (caso 100; lo firma el administrador,
  R21). Lo de medidores, dólares, tesorería, débito automático y rendiciones de cobranza ya estaba
  fuera del MVP (D-023, D-026, D-017).
- **Quién**: Juani, a partir del material de Alberto.

## D-072 · No se suman MinIO ni APScheduler

- **Fecha**: 13/10/2026
- **Decisión**: los links firmados y con vencimiento (D-070) los genera el propio backend, sin un
  servidor de archivos aparte. Las tareas programadas (avisos, cierres, intereses) van en el worker ARQ
  ya decidido (D-038), que también programa tareas por fecha.
- **Por qué**: la edición libre de MinIO quedó archivada en abril de 2026, sin actualizaciones y con
  fallas de seguridad conocidas sin parchear (verificado el 13/10). APScheduler duplicaría lo que ya
  hace ARQ y, corriendo dentro de la API con varios procesos, puede ejecutar dos veces la misma tarea.
- **Queda para después**: Apprise, para avisos por varios canales (por ejemplo, alertas internas por
  Telegram), si hace falta más allá del email.
- **Quién**: Juani, a partir del documento de herramientas de Alberto.

## D-073 · Anular una liquidación es un cambio de estado, no un borrado · *corregida en parte por D-079 y D-081*

- **Fecha**: 13/10/2026
- **Decisión**: anular una liquidación emitida y todavía no distribuida (R17) **no borra ningún
  movimiento**. La liquidación pasa de *emitida* a *anulada*, con motivo, responsable y fecha. El
  saldo de cada unidad se calcula sólo con las obligaciones de liquidaciones que no están anuladas, y
  el período queda libre para volver a emitirse. El estado de la liquidación se guarda como su propia
  secuencia de eventos de sólo agregar (emitida, distribuida, anulada), coherente con el libro de la
  cuenta corriente (R08).
- **Corrige a R17 y D-055**: el test "anular borra la obligación sin dejar movimiento" contradecía el
  libro de sólo agregar del cambio 4, donde modificar o borrar un movimiento rebota. Las dos cosas no
  podían ser ciertas a la vez.
- **Por qué**: lo que el administrador necesita es que la deuda vuelva a quedar como antes de emitir,
  no que desaparezca la evidencia de que emitió. Con el estado queda rastro de por qué un período se
  emitió dos veces; con el borrado, no.
- **Descartado**: permitir borrados en el libro sólo para este caso (la garantía de sólo agregar deja
  de valer) y guardar el estado como una columna que se sobrescribe (pierde la historia).
- **Quién**: Juani, a partir del análisis de contradicciones de Alberto (13/10).

## D-074 · La distribución es un concepto propio del cambio 7, y el moroso crítico es una función del cambio 4 · *corregida en parte por D-077*

- **Fecha**: 13/10/2026
- **Decisión**:
  - **Distribución**: el cambio 7 define la máquina de estados de la liquidación (borrador, emitida,
    distribuida, y anulada sólo desde emitida), un **puerto para registrar la distribución** y una
    acción manual del administrador, **"distribuir"**. Con eso el cambio 7 se construye y se prueba
    solo. Después, el cambio 11 llama a ese puerto la primera vez que un vecino abre la liquidación, y
    el 13 cuando sale el primer email. Ninguno redefine nada: se enchufan. El cambio 7 encola el PDF,
    no el email.
  - **Moroso crítico**: R20 ya se calcula desde las imputaciones, nunca desde una marca guardada, así
    que no hay nada que "reevaluar": su resultado se deriva del libro cada vez que se pide. La función
    pura de R20 se construye en el **cambio 4**, como consulta sobre el libro; el cambio 10 se queda con
    el listado, la exportación y la presentación. R18, R25 y R29 dicen "la unidad pasa a cumplir R20"
    en lugar de "se reevalúa".
- **Por qué**: el cambio 7 dependía de eventos (el primer email, la primera vista en el portal) que
  recién existen en los cambios 13 y 11, y R18 y R25 (cambio 8) dependían de R20 (cambio 10). Las dos
  eran dependencias hacia adelante: no se podían probar en su cambio.
- **Quién**: Juani, a partir del análisis de contradicciones de Alberto (13/10).

## D-075 · Los estados del gasto separan la IA caída de la IA con dudas · *corregida en parte por D-079*

- **Fecha**: 13/10/2026
- **Decisión**: un gasto tiene cuatro estados, de punta a punta:
  - **borrador**: cargado y sin aprobar. No entra en ningún cálculo.
  - **sin IA**: la lectura automática falló y espera carga manual. No entra en el cálculo y dispara una
    **advertencia** antes de emitir ("hay N facturas sin cargar"). La liquidación puede salir (R24),
    pero nadie se olvida de ellas.
  - **en revisión**: la IA leyó con alertas (un CUIT ilegible, un total que no cierra, un monto
    atípico). Dispara el **bloqueante** de R34, que el administrador puede levantar aceptándolo de
    forma explícita.
  - **aprobado**: entra en el cálculo.
  R24 pasa a vigente.
- **Por qué**: R24 prometía que la caída de la IA no frena la emisión y R34 bloquea las facturas con
  alertas, pero ningún texto definía los estados que separan esos dos casos. Sin ellos, un gasto "sin
  IA" podía bloquear lo que R24 prometió no bloquear, o quedar afuera de la liquidación en silencio.
- **Quién**: Juani, a partir del análisis de contradicciones de Alberto (13/10).

## D-076 · El tenant es la administración; el edificio es un alcance dentro de ella

- **Fecha**: 13/10/2026
- **Decisión**: el **tenant** (el dueño de los datos, sobre el que se construye el aislamiento con
  Row-Level Security) es la **administración**: el cliente que paga PropTech. El **complejo** (un
  edificio, y más adelante un barrio) es un **alcance dentro de la administración**, que se controla
  con permisos por rol (D-037). Son dos candados distintos: el aislamiento entre administraciones y el
  alcance por edificio.
- **Corrige**: R10 hablaba de "aislamiento entre complejos", D-016 y `CLAUDE.md` decían "el barrio
  sale del login" (un resto de cuando el MVP era para barrios). D-037 ya tenía la forma correcta.
- **Por qué**: un administrador real maneja muchos edificios. Si el tenant fuera el edificio, tendría
  que "cambiar de tenant" en cada uno, y la política de la base no podría expresar "este colaborador
  ve los edificios 3 y 7 de su administración".
- **Pendiente para el explore del cambio 2** (P18): un vecino con unidades en edificios de dos
  administraciones distintas, ¿tiene una identidad global con membresías por administración, o una
  cuenta por administración?
- **Quién**: Juani, a partir del análisis de contradicciones de Alberto (13/10).

## D-077 · El cambio 10 se parte en 10a y 10b, y el cambio 5 pasa a pedir aprobación · *corregida en parte por D-087, D-088 y D-094*

- **Fecha**: 13/10/2026
- **Decisión**:
  - **10a · `morosidad`**: el listado de deudores, la exportación y la presentación del moroso
    crítico, que ya viene calculado desde el cambio 4 (D-074). Es de sólo lectura: ciclo de una pasada.
  - **10b · `condonacion-judicial-y-libre-deuda`**: la condonación de intereses (R29), la marca de
    gestión judicial (R31) y el certificado de libre deuda (R21). Escribe en la cuenta corriente o
    tiene peso legal: **ciclo completo y aprobación de Juani antes de codear**.
  - **El cambio 5** (importación desde Excel) también pasa a pedir la aprobación de Juani antes de
    codear, porque sus saldos iniciales escriben en la cuenta corriente.
  El roadmap pasa de 17 a 18 cambios; los números de los demás no cambian.
- **Por qué**: la tabla de escalado ponía al 10 como "chico o de sólo lectura", pero adentro tenía
  movimientos de crédito, una marca que cambia el cálculo de morosidad y un documento con peso legal.
  Partirlo además aísla R29, que todavía espera saber quién aprueba una condonación (Q1), sin frenar el
  resto.
- **Quién**: Juani, a partir del análisis de contradicciones de Alberto (13/10).

## D-078 · Ajustes de coherencia tras la revisión final del 13/10

- **Fecha**: 13/10/2026
- **Decisión**: la revisión completa de la base, después de D-073 a D-077, encontró huecos que esas
  decisiones dejaban abiertos. Se resuelven así:
  - **HU-A11** (nueva): la condonación (R29) y la gestión judicial (R31) salen de HU-A8, que queda de
    sólo lectura para el cambio 10a, y pasan a una historia propia del cambio 10b.
  - **Gestión judicial y avisos**: el 10b expone la marca como consulta; el cambio 13 la usa para
    saltear los avisos de mora y lo prueba. El 13 pasa a depender del 8 y del 10b, para que ningún
    test dependa de un cambio posterior.
  - **Exclusión en R20**: el 10b agrega la exclusión por gestión judicial a la función de moroso crítico
    del cambio 4. El plan de pago sigue fuera del MVP.
  - **Estados del gasto**: los cuatro estados de D-075 los crea el cambio 6. El cambio 7 prueba R24
    armando gastos sin IA y en revisión a mano, sin esperar a los cambios 9 y 14.
  - **Niveles de los controles**: el nivel de cada control de R34 es un piso fijo. Un edificio puede
    sumar controles propios o subir una advertencia a bloqueante desde el motor, pero nunca bajar un
    bloqueante de R34.
- **Por qué**: sin estos ajustes, el cambio 10a no se podía terminar sin escribir en la cuenta
  corriente, el 10b dependía del 13 (una dependencia hacia adelante, el problema que D-074 vino a
  resolver) y R24 no tenía un cambio donde probarse antes del 14.
- **Quién**: Juani, a partir de la revisión final de la base.

## D-079 · Correcciones de la segunda revisión completa (13/10) · *corregida en parte por D-080 y D-081*

- **Fecha**: 13/10/2026
- **Decisión**:
  - **Anular excluye todo lo que generó la emisión** (corrige a D-073): el saldo excluye todo movimiento
    generado por una emisión anulada (obligaciones, intereses, bonificaciones), no sólo sus
    obligaciones. Si no, anular y volver a emitir cobraba dos veces el interés de la deuda vieja.
  - **La cuenta de la preliquidación**: lo prorrateado entre las unidades es igual a los gastos
    aprobados menos notas de crédito e ingresos, más el fondo de reserva; los cargos particulares,
    intereses y bonificaciones se suman aparte, unidad por unidad (HU-A4).
  - **Los controles sobre los gastos nacen en el cambio 7**, incluidos los de gastos sin IA y en
    revisión y los que usan consultas del cambio 6; el 14 sólo deja cada gasto en su estado (corrige el
    reparto de R34 de D-071 y D-075). Así ningún cambio prueba algo que se construye después.
  - **Factura duplicada** usa la clave completa de R12 (CUIT, punto de venta, tipo y número), para no
    confundir una factura con su nota de crédito.
  - **Fichas de los cambios 3 y 4**: lo que necesita una liquidación emitida o anulada se prueba en el 7,
    o con datos armados en el test.
  - **Las propuestas en las fichas** dicen "entra si se valida": no son alcance comprometido.
- **Por qué**: la segunda revisión completa de la base encontró estos huecos; son correcciones, no
  cambios de criterio.
- **Quién**: Juani, a partir de la revisión.

## D-080 · Cuatro definiciones pendientes de la segunda revisión · *corregida en parte por D-081, D-083 y D-087*

- **Fecha**: 13/10/2026
- **Decisión**:
  - **Intereses, fondo de reserva y cargo por estado son menús de configuración, no reglas del
    motor**, como decidió D-010 (menú cerrado, sin fórmula libre). El motor queda para las reglas
    propias de cada edificio (bonificaciones, cargos recurrentes, controles propios). El cambio 3
    construye la base del motor (módulo, puerto, adaptador, validador, versiones y editor), pasa a
    tener explore propio y a tamaño grande; las reglas concretas llegan en el 7.
  - **Dos controles duros**: "saldos iniciales sin validar" e "ingresos mayores que los gastos" no se
    pueden aceptar. El resto de los bloqueantes de R34 sí, con registro.
  - **La bonificación por pronto pago se registra al confirmar el pago** (cambio 8), si la transferencia
    es anterior al día límite y cubre la ordinaria con el descuento aplicado. La expensa muestra los dos
    importes. Así, quien paga el importe con descuento no queda como un pago parcial.
  - **El moroso crítico cuenta la deuda migrada**: cada período vencido cargado con detalle cuenta como
    una liquidación vencida; un saldo inicial de total único cuenta como una.
- **Corrige**: `motor-de-reglas.md`, que ponía la tasa, el fondo y el cargo por estado como reglas del
  motor (D-065 y D-066 los habían heredado del catálogo de plantillas).
- **Por qué**: la segunda revisión encontró que la base decía dos cosas sobre cada uno de estos puntos.
- **Quién**: Juani, que delegó la decisión el 13/10 siguiendo las recomendaciones de la revisión.

## D-081 · Correcciones de la tercera revisión completa (13/10) · *corregida en parte por D-085*

- **Fecha**: 13/10/2026
- **Decisión**:
  - **La bonificación por pronto pago no es parte de la liquidación**: se registra sólo al confirmar el
    pago (cambio 8, D-080). En el cambio 7 la regla del motor sólo calcula el importe con descuento que
    muestra el PDF. Corrige a D-079, que la sumaba al total de la liquidación y a lo que excluye una
    anulación.
  - **Factura duplicada es un control duro**, junto con los dos de D-080: con la clave completa de R12 es
    la misma factura, y aceptarla repartiría el gasto dos veces.
  - **Ordinaria prorrateada**: la parte de cada unidad en los gastos ordinarios de sus grupos, neta de
    notas de crédito e ingresos, sin cargos particulares, intereses ni fondo. Es la base del fondo de
    reserva y de la bonificación (R13, R15, R37).
  - **Pago imputado a una emisión que se anula**: la imputación deja de valer y el pago vuelve como
    crédito a favor, que se imputa en la nueva emisión (R17).
  - **Libre deuda con interés corrido**: el certificado informa en una línea aparte el interés corrido
    hasta la fecha de corte, calculado y sin registrar (R21).
  - **Días de gracia**: si se superan, el interés corre desde el vencimiento (R03; a validar con un
    administrador junto con el resto de R03).
  - **El extracto incompleto** se prueba en el cambio 9 (HU-A7), y la **sugerencia por CBU histórico**
    también (R19): en el cambio 8 sólo se guarda el CBU cuando se conoce.
- **Por qué**: la tercera revisión completa de la base encontró estos puntos; son correcciones y
  definiciones de detalle, sin cambio de criterio.
- **Quién**: Juani, que delegó las decisiones el 13/10.

## D-082 · Definiciones de plata de la cuarta revisión (13/10) · *corregida en parte por D-083 y D-084*

- **Fecha**: 13/10/2026
- **Decisión** (las que tocan montos quedan a validar con un administrador, como R03):
  - **La bonificación queda enlazada a su pago**: si el pago se revierte, se reimputa o su imputación cae
    por una anulación, la bonificación se revierte con un contra-movimiento (R37, R18).
  - **Interés ya registrado por días posteriores a la transferencia**: al confirmar el pago se registra
    solo un ajuste por el interés de más (R11).
  - **El interés anterior a la migración no se recalcula**: entra como lo trae el administrador, en una
    columna de la hoja opcional de saldos por período, y R03 corre desde la migración (R09).
  - **Edificio sin saldos previos**: se confirma con esa acción, que cierra el importador en cero; así el
    control duro de saldos iniciales no lo bloquea (R09, R34).
  - **Tolerancia de coeficientes**: ±0,0001, con advertencia y reparto proporcional a la suma real (R01,
    R07).
  - **Los ingresos se restan de los gastos ordinarios** de su grupo, nunca de la extraordinaria (R38).
  - **Nota de crédito de una factura ya liquidada**: se descuenta en el período en que se carga, sin
    reabrir el emitido (R22).
  - **Feriados nacionales en un calendario del sistema**, actualizable cada año (R35).
  - **Cargos recurrentes del reglamento** como cargos particulares generados por el motor (R14).
  - **El cambio 2 crea las tablas mínimas** que necesita para probar el acceso; el 3 las completa.
- **Por qué**: la cuarta revisión completa encontró estos casos sin definir; todos afectan un monto o
  impiden probar un cambio.
- **Quién**: Juani, que delegó las decisiones el 13/10.

## D-083 · Correcciones de la quinta revisión completa (13/10) · *corregida en parte por D-084*

- **Fecha**: 13/10/2026
- **Decisión**:
  - **Bonificación por pronto pago**: la transferencia vale hasta el día límite inclusive y tiene que
    cubrir todo lo que la unidad debe del período, con el descuento aplicado sólo a la ordinaria
    prorrateada (R37). Corrige la redacción de D-080.
  - **El ajuste de interés de R11 queda enlazado a su pago** y se revierte con él, igual que la
    bonificación (R11, R18).
  - **Estado de migración del edificio** (pendiente, confirmada o sin saldos previos): lo agrega el
    cambio 3 a la semilla y a su validador; el edificio de ejemplo queda "sin saldos previos" y el
    cambio 5 usa ese estado (R09).
  - **Saldo inicial de total único**: el interés corre sólo sobre el capital; el interés que traiga el
    administrador va en una columna aparte que no genera interés (R09, R03).
  - Los casos de negocio sin definir que encontró la revisión pasan a la lista de preguntas abiertas
    (P24 a P32), cada uno con el cambio antes del cual se decide.
- **Por qué**: la quinta revisión completa encontró estas contradicciones, efecto de correcciones
  anteriores.
- **Quién**: Juani, que delegó las decisiones el 13/10.

## D-084 · Correcciones de la sexta revisión completa (13/10) · *corregida en parte por D-085*

- **Fecha**: 13/10/2026
- **Decisión**:
  - **El ajuste de interés de R11 se enlaza también a la emisión cuyo interés compensa**: si esa
    emisión se anula, el ajuste queda excluido junto con el interés, y no sobrevive como crédito de más.
  - **El cambio 4 depende del 2 y del 3**, porque usa el menú de intereses versionado y las marcas que
    construye el 3.
  - **La ficha del cambio 2 recoge las notas de seguridad del 1a** (D-051) y **la del 4, las del 1b**
    (D-053).
  - **Tolerancia de coeficientes con el borde incluido**; R40 cuenta como emitido un período
    distribuido, y una liquidación anulada se puede volver a emitir.
  - Los casos de negocio sin definir que encontró la revisión pasan a la lista (P33 a P41).
- **Por qué**: la sexta revisión completa; sólo un hallazgo afectaba plata.
- **Quién**: Juani, que delegó las decisiones el 13/10.

## D-085 · Correcciones de la séptima revisión completa (13/10)

- **Fecha**: 13/10/2026
- **Decisión**:
  - **El ajuste de interés de R11 sigue al interés**: si se anula la emisión que registró el interés que
    compensa, el ajuste queda excluido con él, sin contra-movimiento, aunque esa anulación haga caer
    también la imputación del pago. Sólo se revierte con contra-movimiento cuando el pago se revierte o
    se reimputa.
  - **La regla de bonificación devuelve un porcentaje**, y el núcleo calcula el monto. Al emitir se
    evalúa con el día límite, para el importe con descuento del PDF; al confirmar un pago, con el día de
    la transferencia. Así no falta ningún dato al emitir (R33).
  - **La plantilla de Excel** suma la columna de interés devengado (que no genera interés) y el
    vencimiento en la hoja por período.
  - **Una factura sin QR** queda en revisión, con la nota "sin QR".
- **Por qué**: la séptima revisión completa no encontró hallazgos graves; éstos eran los medios.
- **Quién**: Juani, que delegó las decisiones el 13/10.

## D-086 · Cómo bajan la deuda los créditos que no son pagos, y el contrato mínimo de emisión

- **Fecha**: 13/10/2026
- **Decisión**:
  - **Créditos que no son pagos** (resuelve P35): cada uno baja el residual con una imputación propia y
    un destino fijo: la condonación, al interés que condona; el ajuste de interés, al interés que
    compensa; la bonificación, a la ordinaria del período bonificado; la corrección y la reimputación,
    con el orden de R04, como un pago; la baja de deuda, a todas las obligaciones impagas con R04. El
    residual es el importe menos todas las imputaciones (R05; a validar con un administrador).
  - **R05, R06 y R08 tienen sus tests mínimos**, que faltaban aunque eran vigentes.
  - **Contrato mínimo de emisión en el cambio 4**: la entidad emisión con identificador, período,
    edificio y estado, y cada movimiento referencia la emisión que lo generó; el 7 la completa.
- **Por qué**: la auditoría de Alberto del 13/10 marcó que las reglas centrales de la cuenta corriente,
  dominio CRITICAL, estaban incompletas antes del cambio 4, y que el 4 dependía en silencio de una
  entidad que nacía en el 7.
- **Quién**: Juani, a partir de la auditoría de Alberto.

## D-087 · Ajustes de método y de roadmap de la auditoría de Alberto (13/10) · *corregida en parte por D-088, D-089 y D-090*

- **Fecha**: 13/10/2026
- **Decisión**:
  - **Reglas congeladas**: no se agregan reglas nuevas (R42 en adelante) hasta cerrar el hito M1. Lo
    nuevo que aparezca va como pregunta abierta. Las fichas del roadmap listan las reglas vigentes y,
    en una línea aparte, las propuestas que entran si se validan.
  - **El motor de reglas sale del cambio 3 a un cambio propio, el 6b**, justo antes del 7, que es el que
    lo usa. El 6b lleva explore propio (el demo BRE y la compatibilidad de jdm-editor con React 19.3
    son su prerrequisito). El roadmap pasa de 18 a 19 cambios. Corrige a D-080 en este punto.
  - **Gobernanza**: el cambio 3 (configuración versionada de intereses) y el 12 (vista del consejo, cuyo
    riesgo es mostrar datos de más) pasan a HIGH: se propone y se espera la revisión de Juani.
  - **Plan de Row-Level Security**, escrito en la ficha del cambio 2: dos roles de base, la columna
    `administracion_id` en toda tabla de una administración, RLS forzada con una política de lectura y
    escritura, y el valor fijado por transacción desde la identidad autenticada (o por tarea en el
    worker).
  - **El cambio 1c se re-propone partido en 1c y 1d**: el 1c con logs, request_id, Redis, worker y web;
    el 1d con respaldos, restauración, humo y README, con la aprobación HIGH escrita en su propuesta. Se
    suman las lecciones L-007 a L-009 a sus tareas.
  - **Las preguntas abiertas mantienen la letra P**; los principios de Alberto se citan como
    "principio N de Alberto", sin letra, para no confundirlos.
  - **Lo de código de la auditoría** (que `Dinero` se pueda copiar y serializar, declarar pydantic, las
    cabeceras de seguridad, los volúmenes de Caddy, el CI en los pull requests, los tipos Porcentaje y
    Superficie, la convención de nombres de la base y el engine único del endpoint de salud) queda
    anotado para cuando se retome el código: Alberto pidió terminar primero la documentación.
- **Por qué**: la auditoría de Alberto del 13/10 encontró que el diseño avanzaba más rápido que el
  código y propuso estos ajustes.
- **Quién**: Juani, a partir de la auditoría de Alberto.

## D-088 · El roadmap tiene 20 cambios, y el 1c queda en 29 tareas · *corregida en parte por D-090*

- **Fecha**: 13/10/2026
- **Decisión**:
  - **El roadmap tiene 20 cambios**: los 18 de D-077, más el 6b (motor de reglas) y el 1d (respaldos y
    restauración), los dos de D-087. Corrige la cuenta de D-087, que decía 19.
  - **El 1c queda en 29 tareas, como excepción registrada** a la regla de partir pasadas unas veinte
    (D-052, `openspec/config.yaml`). El alcance es el del corte de D-087 (logs, request_id, cola, worker y
    web, unas 23 tareas); lo que sumó tareas fue cumplir la otra regla, tareas de medio día como
    máximo, más la sección de cierre que pide L-003. Si en la construcción se traba, el corte natural es
    sacar la web y el proxy a un cambio propio.
- **Por qué**: la revisión final después de la auditoría de Alberto marcó las dos cosas.
- **Quién**: Juani, que delegó las decisiones el 13/10.

## D-089 · Documentación de la tercera auditoría de Alberto (13/10) y congelamiento de la base

- **Fecha**: 14/10/2026
- **Decisión**:
  - **El motor de reglas (6b) sale del camino a M1**: va después del 7 y el 8. Ninguna regla vigente
    pasa por el motor; si R37 o R14 se validan antes, se construyen como código simple y el 6b las migra.
    Corrige a D-087 en este punto.
  - **"Vigente" se separa de "a validar"**: las reglas vigentes cuyos valores o criterios de plata no
    revisó nadie del rubro (R01, R03, R05, R09, R11, R22) llevan "a validar (P42)" en el título.
  - **R02 se construye con barrios** (v1.2): en el MVP sólo queda el campo de estado desactivado.
  - **Cada ficha del roadmap tiene "Bloqueado por"**, con las preguntas que la frenan.
  - **Tests mínimos completados** en R01 (tolerancia), R03 (mes entero), R10 (escritura cruzada,
    worker, links y consejo), R11 (pago repartido), R12 (QR corrupto) y R18 (movimientos enlazados).
  - **Deuda técnica de las auditorías** en una tabla del roadmap, cada ítem con su cambio.
  - **La base queda congelada**: no se reabre salvo por hallazgos que salgan del código o por las
    respuestas a las preguntas abiertas (pedido de la auditoría, M1).
- **Por qué**: la tercera auditoría de Alberto del 13/10.
- **Quién**: Juani, a partir de la auditoría de Alberto.

## D-090 · La deuda técnica del 1c y el 1d entra en sus tareas: 35 y 19 · *corregida en parte por D-095*

- **Fecha**: 14/10/2026
- **Decisión**:
  - **El 1c queda en 35 tareas** y sigue como excepción registrada a la regla de partir pasadas unas
    veinte. Las seis nuevas son la deuda de código de la tercera auditoría que toca lo que el 1c ya
    construye: línea de base sobre un clon con historial, pyyaml 6.0.3, `SecretStr`, un solo engine con
    su pool, `Dinero` copiable y serializable, y los logs de ARQ sin argumentos. El resto de esa deuda
    entró como casos dentro de tareas existentes. Corrige a D-088, que fijaba 29.
  - **El 1d queda en 19 tareas**: rebasar los requisitos que modifica sobre lo que deje el 1c y
    shellcheck en el CI.
  - **Lo de código que D-087 dejaba "para cuando se retome el código"** se reparte así: `Dinero`, el
    engine único y lo demás que toca el 1c, en el 1c; el resto, en los cambios de la tabla de deuda
    técnica del roadmap. Corrige a D-087 en este punto.
  - **El corte de emergencia no cambia**: si el 1c se traba, la web y el proxy salen a un cambio propio.
- **Por qué**: la tercera auditoría de Alberto dijo que el 1c puede arrancar con esta deuda adentro;
  dejarla para después era abrir un cambio sólo para tocar los mismos archivos otra vez.
- **Quién**: Juani, que delegó las decisiones el 13/10.

## D-091 · Las elecciones de código del cierre del 1c (14/10)

- **Fecha**: 14/10/2026
- **Decisión**:
  - **Versiones**: imagen de Redis `redis:8.10.2-trixie`, `arq==0.28.0`, `redis[hiredis]>=5.3.1,<6`
    (ARQ exige `<6`); quedaron fijadas en `backend/pyproject.toml`.
  - **JSON en vez de `pickle`** para serializar los trabajos de la cola: el default de ARQ es
    `pickle`, y quien pudiera escribir en Redis ejecutaría código en el worker.
  - **Formato del log**: una línea JSON por evento, con una lista cerrada de campos. Dos excepciones
    conocidas: las dos líneas que ARQ escribe antes del `on_startup` del worker, sin datos de un
    trabajo (conteo de funciones, estadísticas de la conexión a Redis); y los eventos fijos
    `excepcion_como_mensaje` (cuando `record.msg` es la excepción misma) y
    `traceback_crudo_descartado` (cuando el mensaje ya es un traceback formateado como texto), que
    reemplazan el mensaje original para que nunca se cuele el texto de una excepción de terceros.
  - **`request_id`**: UUID, que Caddy pisa siempre (nunca el que elige el cliente), con una tabla de
    casos (`config/contratos/request-id.json`) compartida entre los tests de pytest y de Vitest.
  - **Idempotencia** con la tabla técnica `trabajos_hechos` (clave primaria, una sola transacción con
    el efecto).
  - **Desvíos de diseño aceptados en la construcción**: `/salud-web` usa `AbortController` + `setTimeout`
    propios en vez de `AbortSignal.timeout` (los temporizadores falsos de Vitest no disparan ese
    mecanismo interno); `validarRequestId` queda exportado en la web para probarlo solo contra la
    tabla de casos; el verificador de cola de `/api/salud` crea un cliente de Redis nuevo por pedido
    (a diferencia del engine único de base); el prefijo `/api` se fijó en `salud.router`
    (`APIRouter(prefix="/api")`) y se sacó el `router_api` intermedio; `_ruta_de` lee el atributo
    interno de FastAPI `scope["fastapi"]["effective_route_context"].path_format` (FastAPI fijado
    `<0.144`, con un test que detecta si deja de existir); `COTA_OPERACION_S = 1.5` como cota fija y
    genérica (con su advertencia: no sirve para una tarea larga, cota por tarea en el cambio 7);
    `url_sqlalchemy()` sigue devolviendo `str` con la contraseña interpolada en vez del objeto `URL`
    renderizado sólo en el borde que había pedido Alberto (M12 a medias, deuda para el cambio 2).
  - **Cierre**: el auditor dio **OK con deuda anotada** (la tabla de deuda técnica del roadmap, con
    F2c y F12b entre otras); Juani aceptó esa tabla.
- **Por qué**: dejar registradas las elecciones de código de este cambio para que el cambio 7 y los
  que lo siguen no las reinventen ni las contradigan sin saberlo.
- **Quién**: Juani, a partir del veredicto del auditor del 14/10.

## D-092 · Cambio de método después del tope de vueltas

- **Fecha**: 14/10/2026
- **Decisión**:
  - **Después de la tercera vuelta** entre constructor y rompedor sin llegar al OK, el rompedor **ya
    no vuelve al constructor**: entrega su informe final, con el diagnóstico de cada hallazgo
    (severidad, si lo demostró, impacto hoy y a futuro, recomendación), directo al auditor.
  - **El auditor separa lo que bloquea de lo que es deuda aceptable** y da su veredicto sobre esa
    base, en vez de pedir otra vuelta de construcción.
  - **El veredicto llega textual a Juani** (el orquestador no lo resume ni lo suaviza, como ya decía
    `forma-de-trabajo.md`), y es **Juani quien decide** si se cierra con la deuda anotada o se pide
    otra vuelta.
  - **La corrida equivalente al CI (la tarea de cierre, L-003) se hace después de la última vuelta de
    correcciones, nunca antes**: si el código cambia después de esa corrida, la corrida queda vencida
    aunque siga en verde.
  - **El auditor lee los informes originales** de cada agente (constructor, rompedor), no un resumen
    armado por el orquestador.
  - **Mientras nada está commiteado**, mutar código a propósito para ver un rojo exige sacar una copia
    previa (o un `git stash` o un commit local temporal) y un diff que compare contra esa copia antes
    de seguir: sin eso no hay forma de probar que el código volvió a ser el mismo.
- **Por qué**: con el tope de tres vueltas de `forma-de-trabajo.md`, el rompedor podía seguir devolviendo
  trabajo al constructor sin llegar nunca al auditor; separar bloqueante de deuda es exactamente el
  criterio del auditor, y la decisión de cerrar con deuda o seguir iterando es de Juani, no del
  orquestador ni del auditor.
- **Quién**: Juani, 14/10/2026 (pedido explícito de cambio de método, durante el cierre del 1c).

## D-093 · Se adopta la estructura de Active Stack v1 · corrige en parte a D-007

- **Fecha**: 14/10/2026
- **Decisión**: el repositorio pasa de `conocimiento/` (diez archivos con nombres descriptivos) a
  `knowledge-base/` con los diez archivos canónicos de Active Stack v1 (`01_vision_y_objetivos.md` a
  `10_preguntas_abiertas.md`, más extras `11_` en adelante) y `README.md` como índice. **Corrige a
  D-007** en la forma de la base (que ya había pasado de cinco a diez archivos): la base sigue
  teniendo diez archivos de fondo, pero ahora con los nombres y la estructura de secciones que exige
  la v1, para que Alberto pueda trabajar con `openspec` y el ciclo OPSX de la
  v1 sobre este mismo repositorio.
  - **Ningún ID se renumera**: las reglas (R01-R41), las decisiones (D-001 en adelante), las
    preguntas (P1-P46), las historias (HU-\*) y las lecciones (L-001-L-013) conservan su numeración
    original. La v1 usa sus propios prefijos (RN, DD, US, SU, IN) para proyectos nuevos; acá, donde ya
    había un esquema con historia propia, prevalece el esquema existente.
  - **Fuente única**: `conocimiento/` deja de existir. Todo lo que señalaba a esa carpeta (el lector
    funcional de `openspec/config.yaml`, `CLAUDE.md`, `AGENTS.md`, `README.md`,
    `prompt-documento-mvp.md`, los links internos de la base, el change activo
    `respaldos-y-restauracion`, las exploraciones y la nota del vault) pasa a apuntar a
    `knowledge-base/`. Las menciones de `conocimiento/` dentro de decisiones ya escritas (D-001 a
    D-092) **no se tocan**: son historia y esta base nunca se reescribe hacia atrás; son justamente
    las menciones históricas que esta decisión documenta.
  - **Juani sigue con su propio método** (constructor, rompedor, auditor en secuencia,
    `14_forma_de_trabajo.md`) sobre este mismo repositorio; Alberto usa el ciclo OPSX de Active Stack
    v1 (`/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:verify`, `/opsx:archive`). Los dos
    ciclos terminan en el mismo lugar: `openspec archive` y una actualización de `knowledge-base/`.
  - **Qué no se corre nunca en este repositorio**: `active-orchestrator` (tampoco elegir
    "Regenerar" si lo pregunta), `kb-creator`, `roadmap-generator`, `agent-instruction`,
    `openspec init` ni `openspec update`. La base ya existe y está escrita a mano; correr cualquiera
    de esas herramientas la pisa o la regenera con contenido que no es el nuestro. El detalle completo
    va en `CLAUDE.md`/`AGENTS.md`, sección "Reglas duras".
  - **openspec fijado en 1.13.0**: Alberto instala `npm install -g @fission-ai/openspec@1.13.0`, sin
    rango abierto. La versión pública de npm hoy (1.14.1) y cualquier futura siguen adelante; un
    `openspec update` en este repo reescribe `.claude/skills/openspec-*` y `.claude/commands/opsx/*`
    con una versión más nueva, que puede no coincidir con las skills ya versionadas acá.
- **Descartado**: mantener `conocimiento/` con sus nombres actuales y escribir sólo una capa de
  traducción para la v1 (deja dos fuentes de verdad parcialmente superpuestas, que es exactamente el
  problema que D-016 y el principio de "fuente única" vienen evitando en todo lo demás del proyecto).
- **Por qué**: Alberto va a trabajar con Active Stack v1 sobre este repositorio y la v1 no detecta la
  fundación por el contenido de los artefactos: sólo mira si existe `openspec/` y un
  `CLAUDE.md`/`AGENTS.md` "completo". Sin esta adaptación, la primera vez que Alberto (o cualquier
  instalación de la v1) corra su flujo de arranque, va a ofrecer correr `active-orchestrator` sobre un
  repositorio que ya tiene meses de decisiones y 20 cambios planificados, con el riesgo real de pisar
  `.claude/skills/openspec-*` si alguien elige "Regenerar".
- **Quién**: Juani, 14/10/2026 (preparación del repositorio para que Alberto empiece a usar Active
  Stack v1).

## D-094 · Gobernanza compartida entre los dos socios para CRITICAL y HIGH

- **Fecha**: 14/10/2026
- **Decisión**: los cambios de nivel **CRITICAL** y **HIGH** los puede aprobar **cualquiera de los
  dos socios, Juani o Alberto**, dejándolo **por escrito y con fecha** en la propuesta del cambio (el
  mismo lugar donde hoy queda la aprobación de Juani, por ejemplo en `respaldos-y-restauracion` para
  HIGH o en los cambios críticos del roadmap para CRITICAL). No hace falta que apruebe el que no
  programa ese cambio puntual: alcanza con que uno de los dos lo haga constar, con su nombre y la
  fecha.
  - Se actualiza `openspec/config.yaml` (la gobernanza citada en `context` y en `rules`) y
    `14_forma_de_trabajo.md` donde describe quién aprueba los cambios críticos.
  - El resto del esquema no cambia: MEDIUM se implementa con checkpoints y sin aprobación previa;
    LOW es autónomo si pasan los tests; el tope de tres vueltas y el cambio de método después de él
    (D-092) siguen iguales.
- **Descartado**: que sólo Juani apruebe (es el esquema de D-049/D-077, pensado para cuando programaba
  sólo él) y que cada socio apruebe únicamente lo que programa (deja sin aprobador a un cambio CRITICAL
  que programe el otro, si el primero no está disponible).
- **Por qué**: con Alberto trabajando cambios propios sobre el mismo repositorio, exigir siempre la
  aprobación de Juani específicamente frena cambios CRITICAL o HIGH que Alberto puede evaluar y
  aprobar él mismo con el mismo criterio de socio. La gobernanza sigue siendo humana y explícita
  (nunca un agente la completa, D-087): sólo se amplía quién puede ser ese humano.
- **Quién**: Juani, 14/10/2026 (acordado para que Alberto pueda trabajar con autonomía real sobre sus
  propios cambios).

## D-095 · El cierre del 1d: elecciones de código y aceptación de la deuda (14/10) · corrige en parte a D-090

- **Fecha**: 14/10/2026
- **Decisión**:
  - **Backups**: `pg_dump --format=custom` desde la imagen de PostgreSQL (`postgres:18.6-trixie`),
    volcados a una carpeta del host por bind mount (`PROPTECH_DIR_RESPALDOS`), 14 copias
    (`RESPALDO_CONSERVAR`) y cada volcado acotado por `RESPALDO_LIMITE_SEGUNDOS`; restauración con
    destino validado por la expresión cerrada `^proptech_[a-z0-9_]{1,50}$`, distinto de la base en
    uso (`POSTGRES_DB`).
  - **`/api/salud`**: las dos verificaciones (base y cola) corren en hilos paralelos con un plazo total
    de 1,5 s (`PLAZO_TOTAL_SALUD_S`), cada hilo con su propia `contextvars.copy_context()` (B1, L-015);
    una sola línea `salud_degradada` por verificación fallida, con el `request_id` del pedido.
  - **Tracebacks crudos y mensajes que no son texto** se registran con un evento fijo, sin parsear su
    contenido (`traceback_crudo_descartado`, `mensaje_no_texto`, `excepcion_como_mensaje`).
  - **El 1d quedó en 20 tareas**, no 19: corrige el número de D-090.
  - **Cierre**: tres vueltas entre constructor, rompedor y auditor. En la vuelta 2 el auditor bloqueó
    por B1 a B5 (hilos sin copia de contexto, pasos del modo continuo sin chequeo explícito, antigüedad
    negativa aceptada, marcas `[x]` sin el rojo escrito, conteo del humo sólo en `respaldos`) y por
    B4-bis (el paso 7 del humo probado con una entrada que la API ya descartaba, no con la que el humo
    realmente manda, L-017); el constructor los resolvió todos con test en rojo visto antes del código
    (B4 con la demostración directa que pedía el criterio) y el auditor dio **OK con deuda anotada** en
    su vuelta 3, el 14/10/2026. Backend 516 → 606 tests (+1 xfailed); web sin cambios (16).
  - **Deuda aceptada**: la tabla "Deuda del cierre del 1d" de `knowledge-base/12_fichas_de_changes.md`,
    con dueño por ítem (mayormente el cambio 15 y el cambio 2); las tres filas de deuda del 1c con
    dueño el 1d (F13, `salud_degradada` duplicado, F7c) quedan resueltas por este cambio.
- **Por qué**: dejar registradas las elecciones de código de este cambio para que el cambio 2 y los
  que lo siguen no las reinventen ni las contradigan sin saberlo (mismo criterio que D-091 para el 1c).
- **Quién**: Juani, a partir del veredicto del auditor de la vuelta 3 del 14/10/2026.

## D-096 · Una cuenta por administración y permisos por acción (P18, P23)

- **Fecha**: 15/10/2026
- **Decisión**:
  - **P18 · Vecino con unidades en dos administraciones**: para el MVP, **una cuenta por
    administración**. Si un vecino tiene unidades en edificios de dos administraciones distintas,
    tiene dos cuentas, una en cada una; puede usar el mismo email en las dos, porque la unicidad del
    usuario es por administración y no global. La tabla de usuarios se diseña para poder unificar
    cuentas en v1.1 sin migración destructiva.
  - **P23 · Permisos por acción**: principio general: todo lo que mueve plata de forma irreversible o
    tiene peso legal es sólo del titular; el colaborador hace lo que se puede deshacer o lo revisa el
    titular; el consejo mira; el vecino ve lo suyo. Matriz:

    | Acción | Titular | Colaborador (sus edificios) | Consejo | Vecino |
    |---|---|---|---|---|
    | Cargar gastos y preparar la liquidación | Sí | Sí | Ve | No |
    | Emitir y distribuir la liquidación | Sí | No | No | No |
    | Anular una liquidación | Sí | No | No | No |
    | Confirmar un pago informado | Sí | Sí | No | No |
    | Revertir o reimputar un pago | Sí | No | No | No |
    | Condonar intereses (con motivo, visible al consejo) | Sí | No | Ve | No |
    | Dar de baja una deuda | Sí | No | No | No |
    | Aceptar alertas que no bloquean | Sí | Sí | No | No |
    | Aceptar alertas que bloquean | Sí | No | No | No |
    | Invitar usuarios y asignar edificios | Sí | No | No | No |
    | Ver su cuenta e informar pagos | | | | Sí |

    Esta matriz aplica al colaborador con nivel "editar" (D-037); un colaborador de sólo "ver" no
    hace ninguna de estas acciones, cierre o no cierre.
- **Descartado**:
  - Para P18: identidad global con membresías por administración. El login tendría que elegir de qué
    administración mirar, sumando complejidad justo en el punto que D-016 y D-076 buscan mantener
    simple ("la administración sale del login", un login es de una sola administración).
- **Por qué**:
  - P18: mantiene la regla central de que la administración sale del login (D-016, D-076): cada
    login pertenece a una sola administración y el aislamiento por Row-Level Security queda simple.
    El costo es mínimo en el MVP, con un solo edificio piloto.
  - P23: separa lo irreversible o legal (lo hace sólo el titular) de lo que se puede deshacer o
    revisar (lo puede hacer el colaborador con nivel "editar", bajo la mirada del titular). Es
    coherente con lo ya registrado: R41 (propuesta) ya proponía que sólo el titular dé de baja una
    deuda, y D-037 ya fijaba que el colaborador no cierra ni anula liquidaciones; esta decisión
    extiende ese mismo criterio al resto de las acciones que P23 dejaba sin definir.
  - **P20 sigue abierta**: esta matriz fija que condonar es una acción del titular (nadie más tiene el
    permiso), pero no responde si por encima de un monto el titular necesita además la aprobación del
    consejo antes de condonar; esa es la pregunta de P20 y queda sin resolver.
- **Quién**: Juani, como socio (D-094). Alberto puede revisarla antes de que se codee el cambio 2.

## D-097 · El cambio 2 se parte en 2a (el candado), 2b (el login) y 2c (el endurecimiento), y el método de login

- **Fecha**: 15/10/2026 (ajustada el mismo día, antes de publicarse, con la revisión del arquitecto que
  Juani aprobó aplicar)
- **Decisión**:
  - **Partición**: el cambio 2 `acceso-y-aislamiento` se parte en tres, con el mismo criterio que partió
    el 1 en 1a a 1d (piezas con perfil de riesgo distinto se revisan mejor por separado):
    - **2a `aislamiento-por-administracion`, el candado** (CRITICAL): roles de PostgreSQL separados,
      Row-Level Security con `SET LOCAL` por administración, alcance por edificio (404) y permiso por
      acción según D-096 (403), auditoría de acciones sensibles (D-016), el tenant del worker y la web
      fuera de la red de la base. Se prueba entero sin login: la identidad se inyecta en los tests.
    - **2b, el login** (CRITICAL): el método de abajo, la sesión del lado de Next.js (D-036), el límite
      de intentos, la auditoría de los ingresos sobre la tabla del 2a y la CSP de Next. Depende del 2a.
    - **2c `endurecimiento-de-infraestructura`** (MEDIUM): la deuda de infraestructura con dueño "2"
      que no hace al candado (cabeceras y volúmenes de Caddy, `Via`, `X-Powered-By`, HEAD, CI en pull
      requests con límite de tiempo y gitleaks por digest, contenedores endurecidos y PID 1 no root por
      servicio, el resto de F7 y la doble congelada del humo, la tabla de variables del README).
      Depende del 2a porque toca los mismos archivos.
  - **Dependencias**: el cambio 3 depende del **2a** para construirse (sus tests inyectan la identidad
    igual que los del 2a). El **2b** es requisito para que una persona lo use y para el despliegue, no
    para construirlo: lo piden el portal (11), la vista del consejo (12, por el 11) y el piloto (15).
    El roadmap pasa de 20 a 22 cambios; en `CHANGES.md` quedan como **C-05a**, **C-05b** y **C-05c**,
    para no renumerar los códigos siguientes (D-093).
  - **Método de login**: **link mágico por mail sólo para el vecino**; el personal (titular,
    colaborador y consejo) entra **con contraseña**. Resuelve la pregunta que D-039 dejó para el design.
  - **Queda abierto un hueco**, que bloquea el 2b: a qué administración entra un email que tiene
    cuenta en dos (D-096 lo permite y nadie definió el mecanismo). Es **P48**.
- **Descartado**:
  - El cambio 2 en una sola pieza, o en dos con el endurecimiento dentro del candado: la aprobación
    CRITICAL del candado cargaría con trabajo de otro perfil de riesgo (revisión del arquitecto).
  - Que el 3 espere al 2b: frenaría el camino a M1 por una pantalla que el 3 no necesita para
    construirse.
  - Clerk para el personal (la propuesta del documento de Alberto): suma un servicio pago con pocos
    usuarios por administración (D-043) y manda los emails del personal a un tercero antes de tener
    resuelta P12.
  - Link mágico también para el personal: para quien anula liquidaciones y revierte pagos, una bandeja
    de entrada comprometida sería la llave completa.
  - Contraseña también para el vecino: HU-V1 pide "entrar desde el celular con mi email", y cada
    contraseña olvidada de un vecino que entra una vez por mes es un ticket de soporte (P13).
- **Por qué**: el explore del 15/10/2026 (`openspec/exploraciones/2026-10-15-acceso-y-aislamiento.md`,
  secciones 1 y 7) mostró que el candado es irreductiblemente crítico y testeable de punta a punta sin
  login, y que el login depende de decisiones de producto; la revisión del arquitecto del mismo día
  separó además lo que el candado no necesita. El link mágico del vecino necesita mandar un mail antes
  del cambio 13 (`avisos-por-email`): cómo se manda queda para el design del 2b.
- **Quién**: Juani, 15/10/2026 (la partición, el método de login con su alcance por perfil, y los
  ajustes del arquitecto).

## D-098 · El cierre del 2a: opción B en la vuelta 3, regla de cierre y la deuda aceptada (15/10/2026)

- **Fecha**: 15/10/2026
- **Decisión**:
  - **Cierre en cuatro vueltas**: constructor, rompedor y auditor. El auditor bloqueó en la vuelta 1
    (R1 a R4, R7, R8 y R10) y en la vuelta 2 (V2-1, V2-2 y V2-4); el constructor los resolvió todos. En
    la vuelta 3 el auditor encontró tres bloqueantes más (V3-1, V3-2 y V3-4) y le dio a elegir a Juani
    entre dos opciones: (A) cerrar con esos tres anotados como deuda, o (B) abrirlos una vuelta más.
  - **Opción B**, elegida por Juani el 15/10/2026, con la **regla de cierre de la vuelta 4**: "el
    rompedor verifica sólo los cuatro puntos (V3-1, V3-2, V3-4 y V3-10) y la corrida de cierre; lo que
    encuentre fuera de esos cuatro puntos va a 'deuda nueva' y no bloquea". El rompedor de la vuelta 4
    cerró V3-1, V3-2 y V3-4 (M8 y M5) con esa regla; V3-10 se cerró aparte, en el commit `3bbd2a6`, con
    dos frases falsas de `tasks.md` 12.2 corregidas de verdad. Corrida de cierre: backend 863 passed +
    1 xfailed, web 16 passed, humo OK con el segundo `up` incluido.
  - **Deuda aceptada**: la tabla "Deuda del cierre del 2a" de `knowledge-base/12_fichas_de_changes.md`,
    con dueño por ítem (mayormente el 2b y el 15), más la deuda nueva D-1, D-2, D-4, D-5 y D-6 de la
    vuelta 4 (D-3 se corrigió en la misma pasada que V3-10 y no entra como deuda abierta).
  - **La verificación de las políticas de las tablas de negocio queda prometida, no sin dueño**: el
    chequeo 5 de la vuelta 3 encontró que `despues()` sólo mira `pg_policy` de `auditoria` (arreglado
    por V3-1), nunca de `complejo`, `unidad` ni el resto de las tablas de negocio; nadie lo prometió
    para esas tablas. Juani decidió prometerlo: **queda como deuda del cambio 15** (piloto), antes de
    operar la base real, y no como "no prometido".
- **Descartado**: la opción A (cerrar ya con V3-1, V3-2 y V3-4 como deuda anotada): Juani prefirió pagar
  una vuelta más porque los tres bloqueantes tocaban directamente el candado (una política de
  `auditoria` tocada a mano, o una FK hacia `auditoria`, pasando desapercibidas); dejarlos abiertos como
  deuda del cambio más crítico del roadmap pesaba más que una vuelta extra del rompedor.
- **Por qué**: dejar registrada la elección de Juani y la regla de cierre de la vuelta 4, para que el
  2b, el 2c, el 3 y el 15 no reabran lo ya cerrado ni pierdan de vista la deuda que queda con su dueño
  (mismo criterio que D-091 y D-095 para el 1c y el 1d).
- **Quién**: Juani, 15/10/2026, a partir del veredicto del auditor en la vuelta 3.

## D-099 · P48: el selector de administración después de autenticarse (16/10/2026)

- **Fecha**: 16/10/2026
- **Decisión**: si un email tiene cuenta en más de una administración (lo permite D-096), la persona se
  autentica primero (contraseña para el personal, link mágico para el vecino, D-097) y después el
  sistema le muestra un selector "¿A cuál querés entrar?" con sus administraciones. Si tiene una sola
  cuenta, entra directo, sin selector. Vale igual para los dos métodos de ingreso.
- **Descartado**:
  - una dirección o código propio por administración en el ingreso: es más prolijo para la marca de
    cada administración, pero le suma al vecino algo que tiene que saber; se puede agregar más adelante
    sin romper esta decisión;
  - que el link mágico ya traiga la administración, pedido desde el portal del edificio: resuelve sólo
    al vecino y el personal igual necesita una de las otras dos.
- **Por qué**: es la opción que menos le pide al usuario y sirve para los dos tipos de ingreso.
- **Quién**: Juani, 16/10/2026 (D-094: decide cualquiera de los dos socios).

## D-100 · P19, P33 y P24: vencimientos y grupos parciales, configurables (16/10/2026)

- **Fecha**: 16/10/2026
- **Decisión**:
  - **P19, doble vencimiento**: el sistema soporta las dos formas. Cada edificio elige en su
    configuración versionada: vencimiento único (R03) o doble vencimiento, con un recargo para el
    segundo. El doble se modela sumando campos opcionales, sin cambiar el caso único.
  - **P33, cómo se fija el vencimiento**: un día fijo en la configuración del edificio (por ejemplo el
    10), que se puede correr al emitir una liquidación puntual (un feriado, un ajuste), dejando
    registrado el cambio.
  - **P24, grupos parciales** (Ascensor, Cocheras): dos modos por grupo. Por defecto, los coeficientes
    generales se renormalizan entre las unidades del grupo; si el reglamento fija porcentajes propios,
    el grupo lleva coeficientes propios por unidad, que tienen que sumar 1 dentro del grupo.
- **Descartado**: fijar una sola variante en cada caso (sólo vencimiento único, sólo día fijo sin
  ajuste, sólo renormalizar o sólo coeficientes propios): cada una deja afuera reglamentos reales y
  obliga a migrar datos el día que llegue el primer edificio distinto.
- **Por qué**: son prácticas habituales en los consorcios argentinos y el reglamento del edificio
  piloto todavía no está a mano; soportar las variantes cuesta pocas columnas y no cierra puertas.
  Cuando Alberto confirme cómo es el piloto, sólo se elige la variante en la configuración.
- **Quién**: Juani, 16/10/2026 (D-094). Pendiente de contrastar con el reglamento del piloto (Alberto).

## D-101 · El cierre del 2c: sin vuelta 3, límites declarados y deuda al 15 (16/10/2026)

- **Contexto**: la auditoría de la vuelta 2 del 2c dejó tres bloqueantes (C2V2-1, el respaldo del proxy
  sólo en `:80`; C2V2-2, el test del log que sólo mira ERROR; C2V2-3, el humo que cuenta políticas de
  RLS en vez de compararlas) y dos bifurcaciones para Juani (C2V2-1 y C2V2-8). Los tres son la misma
  familia: el chequeo compara un resumen y no el conjunto. Ninguno es una fuga hoy: la RLS de la base en
  uso está intacta, el `Caddyfile` sirve bien en HTTP y la captura sólo-ERROR es anterior al 2c.
- **Decisión**: cerrar sin vuelta 3, como con el 2a (D-098). C2V2-1 y C2V2-8, opción (b): las specs
  acotan el requisito (HTTP; los `exit 1` del humo) y nombran la excepción. C2V2-3: el comentario de
  `humo.sh` deja de afirmar lo que el chequeo no ve y declara el límite. C2V2-4 (un aserto que no podía
  dar rojo) se borró; C2V2-5 (la frase falsa sobre V3-14 en `08` y la reescritura de su sección de
  seguridad) se hizo. El resto va a la tabla "Deuda del cierre del 2c" de `12_fichas_de_changes.md`.
- **Elecciones de código del 2c** (prometidas por la propuesta): capacidades por servicio `db`
  (`CHOWN`, `DAC_OVERRIDE`, `SETUID`, `SETGID`), `redis` (`SETUID`, `SETGID`) y `caddy`
  (`NET_BIND_SERVICE`), el resto ninguna; los errores de Caddy pasan por `handle_errors` con las mismas
  cabeceras; un sitio de respaldo `:80` responde `421`; una sola tabla de variables, en el README.
- **Descartado**: una vuelta 3 que arregle la familia entera (F1 a F5 del auditor). Cuesta otra ronda
  completa de constructor, rompedor y auditor, y lo que cubre (HTTPS real, el contenido de las
  políticas, los niveles de log) recién muerde con el despliegue.
- **Costo**: el 15 hereda la familia entera escrita como deuda, no resuelta.
- **Quién**: Juani, 16/10/2026, por falta de presupuesto de IA para otra ronda.

## D-102 · Toda pantalla lleva su ayuda "?" (17/10/2026)

- **Contexto**: arranca el frontend (3b) y los usuarios incluyen vecinos mayores que entran pocas veces
  al mes desde el celular, y administradores que hoy dependen del Excel. Alberto lo pidió explícitamente
  y como "super importante".
- **Decisión**: toda pantalla del sistema, de cualquier actor, tiene un botón "?" junto al título que
  abre una explicación didáctica en tres partes: para qué sirve la pantalla, qué se hace ahí (pasos
  numerados) y qué pasa después. Se abre tocando o con teclado, nunca sólo al pasar el mouse; se lee al
  tamaño del cuerpo de texto; se cierra con un botón y con `Esc`. Una pantalla sin su "?" no está
  terminada. Vive en `DESIGN.md` (The Always-Help Rule), en HU-T1 de `06_funcionalidades.md`, en las
  reglas del proceso de `14_forma_de_trabajo.md` y en la regla transversal de `12_fichas_de_changes.md`.
- **Descartado**: un centro de ayuda aparte o un manual en PDF (nadie lo abre en el momento en que lo
  necesita); tooltips al pasar el mouse (en el celular no existen y el texto queda chico).
- **Por qué**: lo que ve el vecino es la cara del administrador (principio 5 de `PRODUCT.md`); una
  pantalla que se explica sola baja las preguntas al administrador, que es el éxito del producto.
- **Quién**: Alberto, 17/10/2026; registrado por Juani.

## Supuestos

*(Sección nueva de Active Stack v1. Vacía por ahora: ningún supuesto del proyecto se había
registrado antes con este formato. Lo que se daba por cierto sin verificar vive disperso dentro de
cada decisión, marcado "a validar" o "pendiente"; ver especialmente las reglas marcadas "a validar
(P42)" en `05_reglas_de_negocio.md` y las preguntas abiertas en `10_preguntas_abiertas.md`. Un
supuesto nuevo se agrega acá como `SU-01`, con su origen, el riesgo si es falso y cómo validarlo; no
se migran retroactivamente los existentes para no inventar un origen que no quedó registrado como
tal en su momento.)*
