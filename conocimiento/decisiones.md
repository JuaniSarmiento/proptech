# Decisiones

Registro de cómo llegamos a lo que hay. **Sólo se agrega, nunca se borra**: si una decisión
cambia, se escribe una nueva que la reemplaza y se marca la vieja como `reemplazada por D-0XX`.
Lo vigente se refleja en `mvp.md`, `reglas-de-negocio.md` y `proyecto-final.md`.

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

## D-003 · El MVP se construye en tres hitos demostrables

- **Fecha**: 08/10/2026
- **Decisión**: **M1 Liquida** (decisiones, base, importación, motor financiero, liquidación),
  **M2 Cobra** (Mercado Pago, conciliación, portal, recordatorios), **M3 Piloto** (lectura de
  facturas con IA y un mes en paralelo). El historial de activos va en la v1.1.
- **Descartado**: nueve fases en cascada, donde recién en la sexta un usuario veía algo útil.
- **Por qué**: cada hito se puede mostrar a un administrador real; si el modelo financiero
  está mal pensado, aparece en el primer mes y no en el tercero.
- **Quién**: Juani.

## D-004 · Un barrio piloto real desde el inicio

- **Fecha**: 08/10/2026
- **Decisión**: el piloto se consigue en la fase 0, no al final. Su padrón, sus facturas y su
  última liquidación son el test de aceptación de M1.
- **Descartado**: construir con datos inventados y buscar piloto al terminar.
- **Quién**: Juani. **Pendiente**: quién es el piloto (ver preguntas abiertas).

## D-005 · La plata nunca pasa por una cuenta de PropTech

- **Fecha**: 08/10/2026
- **Decisión**: los cobros van directo a la cuenta del consorcio. PropTech sólo recibe los datos
  para imputar. La consulta legal por la Resolución UIF 200/2024 arranca en la fase 0 y se
  resuelve antes del primer cobro en producción.
- **Descartado**: recaudar en una cuenta propia y transferir al consorcio.
- **Por qué**: custodiar fondos de terceros activa el régimen de proveedor de servicios de pago
  del BCRA. Aun sin custodia, la UIF podría alcanzar a quien facilita el inicio del pago.
- **Quién**: Juani.

## D-006 · Recordatorios por email en el MVP *(propuesta, sin confirmar)*

- **Fecha**: 08/10/2026
- **Decisión**: los avisos de vencimiento y mora salen por email. WhatsApp queda para después.
- **Por qué**: la API oficial de WhatsApp exige verificar el negocio ante Meta y cotizar con un proveedor.
- **Quién**: Juani.

## D-007 · La base de conocimiento son cinco archivos

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

## D-009 · Usuarios del MVP: administrador, vecino y consejo en sólo lectura

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

## D-016 · Correcciones como movimientos nuevos y aislamiento por identidad

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

## D-019 · Las facturas se leen primero por el QR de ARCA y la IA completa el resto

- **Fecha**: 08/10/2026
- **Decisión**: el monto, el proveedor y el identificador de la factura salen del QR oficial; la IA
  completa concepto, período y grupo de reparto; se frenan duplicados y se avisa si el receptor no
  es el barrio. Todo queda en borrador hasta que confirma el administrador. Detalle en R12.
- **Descartado**: leer toda la factura con IA, como proponía la especificación original (más caro
  y con riesgo de leer mal el monto); y el prompt original que pedía "inferir" datos ausentes.
- **Fuente**: especificación oficial del QR en arca.gob.ar, versión 1 (febrero de 2025), verificada
  decodificando su ejemplo.
- **Quién**: Juani.

## D-020 · Stack del MVP

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

## D-021 · Arquitectura: monolito modular, hexagonal por módulo, en español

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

## D-022 · Juani programa el MVP

- **Fecha**: 08/10/2026
- **Decisión**: el desarrollo del MVP lo hace Juani. El roadmap se planifica para un solo desarrollador.
- **Quién**: Juani.

## D-023 · Tesorería y contabilidad integral quedan fuera del MVP

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

## D-030 · El estado de unidad queda apagado en edificios

- **Fecha**: 09/10/2026
- **Decisión**: la regla R02 (factor y cargo por estado) sigue en el sistema para los barrios,
  desactivada por default en edificios.
- **Quién**: Juani (recomendación de Claude).

## D-031 · Fondo de reserva como concepto de la expensa, sin tesorería

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

## D-039 · Del resto del documento de Alberto se mantiene lo ya acordado

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

## D-045 · El MVP se construye en 15 cambios de OPSX

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

## D-047 · Ajustes al plan de cambios después del explore general

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

## D-048 · Forma de trabajo: orquestador y agentes en secuencia, aprueba el auditor

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

---

## Preguntas abiertas

Se resuelven en este orden. Cada respuesta se convierte en una decisión nueva arriba.

- [ ] **P1 · Piloto** (ahora un edificio, D-033): quién es, qué datos puede dar (padrón, facturas, última liquidación) y cuándo. *08/10: Juani no lo sabe; se le pregunta a Alberto. Mientras tanto se diseña con un edificio de ejemplo, pero M1 no se da por cumplido sin datos reales.*
- [x] **P2 · Tipo de complejo del MVP**: edificios primero, diseño preparado para barrios (D-027, reemplaza D-008).
- [x] **P3 · Usuarios y roles del MVP**: administrador, vecino y consejo en sólo lectura (D-009).
- [x] **P4 · Política financiera**: decidida (D-010 a D-015). R08 y R10 vigentes (D-016). **Falta validar los defaults con un administrador o contador de Mendoza.**
- [x] **P5 · Medios de cobro del MVP**: comprobante + OK del administrador, extracto como ayuda (D-017). La consulta UIF queda como requisito antes de integrar Mercado Pago.
- [x] **P6 · Stack**: definido (D-020).
- [x] **P7 · Equipo**: Juani programa (D-022).
- [ ] **P8 · Precio y modelo comercial**: sin definir. Punto de partida: la landing de Alberto (ARS 2.900 por unidad, Profesional 4.200, 10 fundadores con migración gratis) (D-035). Sin definir todavía (08/10). El documento de Alberto lo presenta como tema abierto, con los datos de mercado como referencia.
