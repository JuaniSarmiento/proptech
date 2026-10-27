# Preguntas Abiertas

> `preguntas-para-alberto.md` se integró acá como sección "Para Alberto" (D-093): es un recorte del
> mismo listado de preguntas, con contexto y propuesta para que alcance con un sí o un comentario, y
> mantenerlo como archivo aparte hubiera duplicado la fuente. Cada respuesta se convierte en una
> decisión nueva en `09_decisiones_y_supuestos.md`.

## Inconsistencias detectadas

*(Vacío: la base está congelada desde D-089 y las siete revisiones completas de octubre de 2026
(D-073 a D-085) ya resolvieron las contradicciones internas que encontraron; quedan documentadas
como decisiones, no como inconsistencias abiertas. Las 48 observaciones del análisis de coherencia
de la especificación original (H01-H48) tampoco son inconsistencias de esta base: son hallazgos
sobre la especificación de partida, repartidas por hito en `01_vision_y_objetivos.md`. Una
inconsistencia nueva se agrega acá como `IN-01`, con lo que dice cada documento, el impacto y la
resolución propuesta, sin inventar una que no se haya detectado.)*

## Preguntas abiertas (priorizadas)

Se resuelven en este orden. Cada respuesta se convierte en una decisión nueva en
`09_decisiones_y_supuestos.md`.

- [ ] **P1 · Piloto** (ahora un edificio, D-033): quién es, qué datos puede dar (padrón, facturas, última liquidación) y cuándo. *08/10: Juani no lo sabe; se le pregunta a Alberto. Mientras tanto se diseña con un edificio de ejemplo, pero M1 no se da por cumplido sin datos reales.*
- [x] **P2 · Tipo de complejo del MVP**: edificios primero, diseño preparado para barrios (D-027, reemplaza D-008).
- [x] **P3 · Usuarios y roles del MVP**: perfil × alcance, super admin, administrador, contador, auxiliar,
  consejo de lectura y vecino propietario o inquilino (D-106, reemplaza la matriz de D-096).
- [x] **P4 · Política financiera**: decidida (D-010 a D-015). R08 y R10 vigentes (D-016). **Falta validar los defaults con un administrador o contador de Mendoza.**
- [x] **P5 · Medios de cobro del MVP**: comprobante + OK del administrador, extracto como ayuda (D-017). La consulta UIF queda como requisito antes de integrar Mercado Pago.
- [x] **P6 · Stack**: definido (D-020, ajustado por D-036 y D-038).
- [x] **P7 · Equipo**: Juani programa (D-022); Alberto suma cambios propios con Active Stack v1 (D-093).
- [ ] **P8 · Precio y modelo comercial**: sin definir. Punto de partida: la landing de Alberto (ARS 2.900 por unidad, Profesional 4.200, 10 fundadores con migración gratis) (D-035). Sin definir todavía (08/10). El documento de Alberto lo presenta como tema abierto, con los datos de mercado como referencia.
- [ ] **P9 · Qué traen los extractos bancarios en Mendoza** (Q2 del documento de Alberto, prioridad 0
  para él): si cada banco informa el CBU o el nombre de quien transfirió y el concepto completo.
  Condiciona directamente R19 (código de unidad y CBU histórico) y el *design* del cambio 9
  `extracto-bancario`. Se responde probando con extractos reales de los bancos que usan los
  administradores de Mendoza (D-063). 12/10: Juani no lo sabe; se le pregunta a Alberto.
- [x] **P10 · Modo de redondeo al centavo**: resuelta por D-109 (22/10/2026): medio hacia arriba, como
  `REDONDEAR` de Excel. Queda abierta la sub-pregunta para Alberto: a qué unidad va el centavo
  sobrante en su planilla.
- [x] **P11 · Cambio de titular a mitad de período**: resuelta por D-109 (22/10/2026): lo decide el
  administrador por cada cambio, con dos opciones configurables (expensa del mes de la venta y deuda
  previa) y sus defaults (R32).
- [ ] **P12 · Inscripción de la base de datos ante la AAIP** (ley 25.326): requisito a verificar antes
  del cambio 8, porque el sistema guarda datos personales reales de vecinos. Surge de la investigación
  del 13/10; no está confirmado con un abogado. **Cerrada para la autenticación** (D-107, Juani,
  20/10/2026): se adopta Clerk con aviso de privacidad y transferencia internacional, sólo email y
  nombre, vínculo por id de Clerk. Sigue abierta la inscripción de la base de negocio ante la AAIP.
- [ ] **P13 · Acceso de soporte a la cuenta de un cliente** (ProTecc 7.3 y arquitectura de Alberto):
  cuando alguien de PropTech necesite entrar a la cuenta de un administrador para ayudarlo, el acceso
  tiene que ser explícito, temporal y registrado, nunca con la contraseña del administrador. Hoy el
  soporte es sólo Juani (D-022), así que no bloquea el MVP; se decide antes de sumar a otra persona al
  soporte o al tener el primer cliente externo.
- [ ] **P14 · Plazo de entrega del certificado de libre deuda** (Q11 de Alberto): R21 define quién
  lo firma y qué incluye, pero no en cuántos días hay que entregarlo. Se responde con Alberto o con la
  normativa aplicable en Mendoza.
- [ ] **P15 · Ingresos mayores que los gastos** (R38): qué pasa si en un mes los ingresos de un grupo
  superan sus gastos ordinarios: crédito para el mes siguiente, fondo de reserva u otra cosa. Mientras tanto, la
  emisión se frena. Se responde con Alberto.
- [ ] **P16 · La parte de las unidades del consorcio** (R39): si su parte de cada gasto se reparte entre
  las demás unidades o se registra como gasto del consorcio. Se responde con Alberto, según el
  reglamento.
- [ ] **P17 · IVA de los consorcios** (R12): confirmar con un contador que el consorcio registra los
  gastos con el IVA incluido.
- [x] **P18 · El vecino con unidades en dos administraciones**: resuelta en D-096, una cuenta por
  administración (la unicidad del usuario es por administración, no global; puede repetir email).
- [x] **P19 · Doble vencimiento** (R26, Q9 de Alberto): si el edificio piloto usa primer y segundo
  vencimiento con recargo escalonado en vez del vencimiento único de R03. Afecta el test de M1. Se
  responde con Alberto antes del cambio 3. Resuelta en D-100 (16/10/2026).
- [ ] **P20 · Aprobación adicional de una condonación** (R29, Q1 de Alberto): D-106 reserva la ejecución
  al super admin y al administrador principal; falta decidir si además aprueba el consejo por encima
  de un umbral. Antes del cambio 10b.
- [x] **P21 · Umbrales**: resuelta por D-109 (22/10/2026): gasto atípico (R23) es más del doble o
  menos de la mitad del promedio de los últimos 6 períodos de ese proveedor en el edificio (sin
  historial, no se marca); saldo chico (R30) es $500. Los dos, configurables por edificio.
- [ ] **P22 · Quién usa el editor de reglas** (D-066, `13_motor_de_reglas.md`): propuesta en dos niveles,
  valores para el super admin (antes, titular) y estructura para el equipo. Antes del cambio 6b.
- [x] **P23 · Permisos por acción**: matriz vigente en D-106 (Juani, 20/10/2026), que reemplaza la
  de D-096. Emite todo administrador del edificio; las correcciones reservadas quedan para super
  admin y administrador principal; contador, auxiliar y consejo sólo leen. El umbral del consejo
  para condonar sigue abierto en P20.
- [x] **P24 · Coeficientes de grupos parciales**: un grupo como Ascensor o Cocheras, ¿lleva coeficientes
  propios por unidad o se renormalizan los generales entre sus unidades? Antes del cambio 3. Resuelta en D-100 (16/10/2026).
- [ ] **P25 · Nota de crédito mayor que los gastos del período** en que se carga (factura ya
  liquidada): qué pasa si el reparto daría negativo, y en qué bloque cae si la factura era
  extraordinaria. Antes del cambio 6.
- [ ] **P26 · Anular un período con el siguiente ya emitido**: si se permite y qué pasa con el
  siguiente. Antes del cambio 7.
- [ ] **P27 · La bonificación después de anular y volver a emitir**: si el pago que la había ganado la
  recupera en la nueva emisión. Antes de los cambios 7 y 8.
- [ ] **P28 · Bonificación y fondo de reserva**: si el descuento también achica el fondo, que se calcula
  sobre la misma base. Antes del cambio 7.
- [ ] **P29 · Interés sobre un pago revertido o reimputado**: si corre desde el vencimiento original.
  Antes del cambio 8.
- [ ] **P30 · Un mismo CBU que paga varias unidades** de la misma persona: qué unidad se sugiere. Antes
  del cambio 9.
- [x] **P31 · Moroso crítico y saldos chicos**: resuelta por D-109 (22/10/2026): una deuda que es sólo
  interés no es moroso crítico (etiqueta propia "deuda de intereses", aviso más suave); un saldo por
  debajo del umbral de R30 tampoco cuenta como vencido. En los dos casos la deuda sigue figurando en
  la cuenta y en el libre deuda.
- [ ] **P32 · Libre deuda y pagos confirmados después**: si el saldo a la fecha de corte se calcula por
  fecha de la transferencia o por fecha de registro. Antes del cambio 10b.
- [x] **P33 · Cómo se fija el vencimiento de cada liquidación** (y el día límite de R37): un día fijo del
  edificio o cargado al emitir. Antes del cambio 3. Resuelta en D-100 (16/10/2026).
- [x] **P34 · Hasta qué fecha calcula el interés cada emisión**: resuelta por D-109 (22/10/2026):
  hasta el cierre del período, no la emisión ni el vencimiento siguiente. Queda abierta la
  sub-pregunta para Alberto: confirmar que su Excel corta en la misma fecha.
- [x] **P35 · Cómo bajan el residual de una obligación los créditos que no son pagos**: con una
  imputación propia y un destino fijo por tipo de crédito (D-086, R05).
- [ ] **P36 · Un gasto de un período que quedó afuera** (sin IA, o en revisión con la alerta aceptada) y
  se aprueba después: si entra en el período siguiente. Antes del cambio 6.
- [ ] **P37 · Dónde y quién marca un "gasto mensual obligatorio"** (categoría, proveedor o gasto). Antes
  del cambio 6.
- [ ] **P38 · Con qué fecha se imputa el crédito que vuelve tras una anulación** (R17): la de la
  transferencia o la de la nueva emisión. Antes del cambio 7.
- [ ] **P39 · Si el consejo ve una liquidación emitida y no distribuida**, y si esa vista la distribuye.
  Antes del cambio 7.
- [ ] **P40 · Número de operación único por complejo**: si la clave incluye el banco, porque dos bancos
  pueden repetir número (R11). Antes del cambio 8.
- [ ] **P41 · Aviso de mora a un vecino con un pago informado y sin confirmar**. Antes del cambio 13.
- [ ] **P42 · Validar los valores de plata con un administrador o contador de Mendoza**: los defaults
  de R03 (tasa, gracia, forma de cálculo) y las definiciones de D-082, D-086 y D-109 marcadas "a
  validar". (P4 quedó cerrada como decisión, pero esta validación sigue pendiente.) **Validar antes
  del piloto, no bloquea construir el 4** (D-109, 22/10/2026).
- [ ] **P43 · El contenido derivado de ProTecc en el repositorio público**: la exploración de dolores y
  las reglas citan el documento privado ProTecc v3.5. Confirmar con Alberto que puede ser público, o
  sacarlo del repositorio. Antes de dar visibilidad al repositorio.
- [ ] **P44 · Licencia y política de seguridad del repositorio**: el repo es público y no tiene
  LICENSE ni SECURITY.md. Decidir con Alberto si se reserva el código o se licencia, y cómo se reporta
  una vulnerabilidad. Antes del primer despliegue público.
- [ ] **P45 · Validar la propuesta de valor y el precio**: entre 3 y 5 entrevistas con administradores de
  Mendoza, frente a los ARS 2.950 por unidad de los líderes. Antes de M2.
- [ ] **P46 · Nombres propios en el repositorio público**: `CLAUDE.md`, el README y `09_decisiones_y_supuestos.md` nombran
  a la familia de Alberto y a un docente. Confirmar que lo aprueban o sacar los nombres. Antes de dar
  visibilidad al repositorio.
- [ ] **P47 · Ramas o turnos con dos desarrolladores** (D-093): hasta el 14/10 se trabajaba sin ramas,
  todo sobre `main` (D-049), porque programaba una sola persona. Con Juani y Alberto haciendo cambios
  en el mismo repositorio, acordar si cada cambio va en su rama con pull request o si se turnan sobre
  `main`. Antes de que los dos tengan un cambio en curso al mismo tiempo.
- [x] **P48 · A qué administración entra una persona con cuenta en dos**: resuelta por Juani en
  D-099 (16/10/2026). Primero se autentica y después elige "¿A cuál querés entrar?" entre sus
  administraciones; con una sola cuenta entra directo. Vale para personal y vecinos; el método de
  autenticación actual es Clerk (D-107), sin enlazar personas sólo por email.
- [ ] **P49 · Doble factor para el personal**: Clerk lo ofrece; activarlo es una decisión de producto,
  no técnica. Surge del design del 2b (`openspec/changes/archive/2026-10-22-login-y-usuarios/design.md`,
  Open Questions). Antes de ofrecerlo al piloto (15) o antes, si Alberto lo pide.
- [ ] **P50 · Borrar el usuario de Clerk cuando se le quita la última asignación**: hoy sólo se corta el
  acceso (la próxima vez que pida algo da 401); el usuario sigue existiendo en el panel de Clerk. Surge
  del design del 2b. Antes del 15 o de una decisión de Juani.
- [ ] **P51 · El cambio de titular, entero o después** (P-1 de la exploración del 4, H-01): ¿se
  construye entero (registro, las dos opciones y el aviso) en un sub-change propio después de la
  liquidación (4d), o sólo queda lista la cuenta de persona y el cambio de titular espera? Bloquea el
  4d, no el 4a a 4c.
- [ ] **P52 · La deuda que queda a nombre del vendedor** (P-2, H-02): si queda a su nombre, ¿sigue
  sumando intereses? ¿Puede aparecer como moroso? ¿Cómo paga, si ya no tiene la unidad en el sistema?
  Bloquea el 4d.
- [ ] **P53 · De qué mes es el interés** (P-4, H-05): el interés por la mora de agosto que aparece en la
  expensa de septiembre, ¿cuenta como deuda de agosto o de septiembre? Decide si septiembre cuenta como
  "vencida" para el moroso crítico. Bloquea el 4c.
- [ ] **P54 · El umbral de $500** (P-5, H-06, H-14): ¿se compara contra todo lo que debe la unidad o
  contra cada expensa? Por debajo de $500, ¿sigue corriendo interés? Y "vencida", para el moroso
  crítico, ¿es al día siguiente del vencimiento o después de los días de gracia? Bloquea el 4c.
- [ ] **P55 · Pantalla de corrección en el 4** (P-6, H-15): la corrección de un error (HU-A9), ¿trae
  pantalla o alcanza con la API y la pantalla llega con la del pago (8)? Antes del 4b.
- [ ] **P56 · El libro sin puerto de repositorio** (P-8, §4.9 de la exploración del 4): contradice el
  texto de D-040 y necesita la firma de Juani. Bloquea el 4b.
- [ ] **P57 · El centavo del reparto en el Excel de Alberto** (A-1; formaliza la sub-pregunta de P10):
  cuando un gasto no cierra al centavo, ¿qué hace con el que sobra o falta, y a qué unidad va si hay
  empate? Mientras tanto el 4a desempata por orden natural del identificador (D-118); si la respuesta es
  otra, cambia una función pura sin tocar datos. Antes del piloto, no bloquea construir.
- [ ] **P58 · El corte del interés en el Excel de Alberto** (A-2; formaliza la sub-pregunta de P34): ¿su
  Excel corta el interés al cierre del período? El sistema lo corta el último día del mes (D-113); si
  Alberto usa otro día, se agrega un día de cierre por edificio. Antes del piloto.
- [ ] **P59 · Doble vencimiento e interés diario en el piloto** (A-3, H-10, R26): el doble vencimiento
  con recargo que ya acepta la configuración, ¿se usa en el edificio piloto, y cómo convive con el
  interés diario? Antes del piloto.
- [ ] **P60 · El fondo de reserva cuando un pago no alcanza** (A-4, H-11): ¿se cobra antes o después de
  la ordinaria? Antes del piloto.
- [ ] **P61 · Ubicación del edificio: ¿sólo Argentina?** (exploración del 3c,
  `openspec/exploraciones/2026-10-26-pulido-de-la-configuracion.md` §3): propuesta: sí, sin campo
  país. Antes del 3c.
- [ ] **P62 · Ubicación: calle y número** (§3 del 3c): ¿se agregan como texto libre, o el nombre del
  edificio sigue haciendo de dirección? Antes del 3c.
- [ ] **P63 · Ubicación de los edificios ya cargados** (§3 del 3c): hoy tienen `localidad` en texto
  libre; ¿quedan sin ubicación hasta que se completen, se intenta mapear el texto a Georef, o la
  ubicación es obligatoria desde ya? ¿La columna `localidad` se borra o queda? Antes del 3c.
- [ ] **P64 · Qué pisos tiene un edificio** (§4 del 3c): planta baja, subsuelos (cuántos y cómo se
  nombran), entrepiso o terraza, en qué piso van cocheras, bauleras y locales (la semilla usa "PB" y
  "SS"), y el máximo de pisos. Antes del 3c.
- [ ] **P65 · El piso de las unidades ya cargadas** (§4 del 3c): hoy es texto libre; ¿se mapea lo
  conocido y se marca el resto para corregir, o el texto convive con la lista hasta que se corrija?
  Antes del 3c.
- [ ] **P66 · `/personal` jerárquica** (sugerencia de Emiliano del 23/10/2026, §2.5 del 3c): que el
  Administrador de toda la empresa vea y gestione al personal por debajo suyo, nunca al super admin.
  Cambia D-106 (acceso, CRITICAL); si es que sí, va como decisión nueva y en un change de acceso
  propio. Sin fecha.
- [ ] **P67 · Las dos cuentas de Mailinator del Clerk de desarrollo** (BE-7, deuda del cierre de
  `acceso-de-desarrollo`): quedaron nombradas en el repositorio público y las bandejas de Mailinator
  son públicas; ¿se borran del Clerk de desarrollo? Desde el 26/10/2026 ya no están en `CLAUDE.md`,
  pero siguen en el historial. No bloquea ningún cambio.
- [ ] **P68 · Los ítems de acceso del QA, ¿dentro o fuera del 3c?** (§5 del 3c): la invitación abierta
  con la sesión de otra cuenta, el menú que se adapta al rol y reinvitar el mismo email son dominio de
  acceso. Si entran al pulido, el cambio pasa de HIGH a CRITICAL; la propuesta es un change de acceso
  aparte. Antes del propose del 3c.
- [ ] **P69 · Grupos y claves** (§2.2 del 3c, G-3 y G-6): ¿un grupo se desactiva en vez de borrarse,
  como las categorías (R16)? ¿La clave de grupos y categorías se genera sola desde el nombre? Antes
  del 3c.
- [ ] **P70 · Mapa interactivo para elegir la ubicación exacta** (sugerencia de Emiliano, 26/10/2026,
  al firmar E1/E2 del 3c): un mapa (Google Maps, Mapbox o Leaflet/OpenStreetMap) para marcar el punto
  exacto del edificio, en vez de (o además de) la cadena provincia/departamento/localidad y la calle
  en texto libre del 3c. Choca con reglas ya firmes del proyecto: la app no depende de un servicio
  externo para crear un edificio (D1 del 3c), la CSP estricta de 2b/2c no abre otro origen sin pasar
  por su propia aprobación HIGH, y D-043 prioriza lo que no cobra licencia ni uso (Google Maps cobra
  por volumen; Leaflet/OSM es gratis pero necesita tiles de un servidor ajeno o alojar los propios). Un
  mapa con arrastrar-y-soltar un pin tampoco suele ser operable por teclado, piso obligatorio de
  revisión frontend. Alternativa más barata ya anotada: guardar latitud/longitud como números y un
  link "Ver en el mapa" que abra Google Maps en una pestaña nueva, sin embeber nada. No bloquea el 3c;
  queda para un change futuro de ubicación más precisa, con su propio análisis de costo/CSP/accesibilidad.

## Resumen por el cambio al que bloquean

- **P1 · Piloto**: sin sus datos, M1 queda pendiente del test de aceptación.
- **P8 · Precio**: no afecta ningún cambio.
- **P18 y P23**: resueltas (D-096 para P18, D-106 para la matriz de P23); ya no bloquean el cambio 2 (2a y 2b, D-097).
- **P10 y P11**: resueltas en D-109 (22/10/2026); ya no bloquean el 4. Sus sub-preguntas para
  Alberto pasan a P57 y P58.
- **El 4 partido en 4a a 4d** (exploración del 4, §8): P56 bloquea el 4b y P55 lo decide; P53 y P54
  bloquean el 4c; P51 y P52 el 4d. P57 a P60 son de Alberto y se validan antes del piloto. P-3 y P-7
  de la exploración se resolvieron en D-113.
- **Pulido de la configuración (3c)**: P61 a P65 (ubicación y pisos), P68 (alcance) y P69 (grupos),
  antes de su propose. P66 (`/personal` jerárquica), P67 (cuentas de Mailinator) y P70 (mapa
  interactivo) no lo bloquean.
- **P9**: qué traen los extractos de Mendoza, antes del cambio 9.
- **P20**: quién aprueba una condonación, antes del 10b.
- **P25 a P32, P34 y P36 a P41** (P24 y P33 están resueltas, D-100; P35, D-086): casos de borde de la
  quinta y la sexta revisión, cada uno con el cambio antes del cual se decide.
- **P19**: resuelta en D-100 (vencimiento único o doble, por edificio); ya no bloquea el cambio 3.
- **P21**: resuelta en D-109; el umbral de R30 ya se guarda por versión de configuración desde el 4a, y el
  de R23 entra con el 6 o el 14.
- **P22**: quién usa el editor de reglas, antes del 6b.
- **P42**: validar los valores de plata con un administrador o contador, antes del piloto (D-109), junto con
  P10 y P17 en la misma sesión. P19, P24 y P33 ya no bloquean el cambio 3 (D-100); los rangos y
  defaults de vencimiento que fija el 3a entran en esta validación.
- **P12, P14 y P16**: la inscripción ante la AAIP (antes del 8), el plazo del libre deuda (antes del 10b)
  y la parte de las unidades del consorcio (antes del 3).
- **P45 y P46**: validar la propuesta de valor con administradores (antes de M2) y los nombres propios
  en el repositorio público.
- **P43 y P44**: el material de ProTecc en el repositorio público y la licencia, antes de darle
  visibilidad al repositorio y del primer despliegue.
- **P48**: resuelta en D-099 (selector después de autenticarse); ya no bloquea el 2b.
- **Login y usuarios**: **construido y archivado** (cambio 2b `login-y-usuarios`, 22/10/2026, D-107,
  D-108): Clerk autentica, también con contraseña y Google para vecinos, y la base autoriza; el super
  admin invita al personal con perfil y alcance y da de alta vecinos desde el padrón, con vínculo e
  invitación por mail. Quedan P49 (doble factor) y P50 (borrado en Clerk) como preguntas nuevas que
  dejó su design, y SU-01 como supuesto no verificado (invitar a un email que ya tiene usuario en
  Clerk; `09_decisiones_y_supuestos.md`).
- **Pendientes del design del 2.2a**: `acceso-de-desarrollo` quedó archivado el 24/10/2026 (D-110,
  firma ratificada por D-111): la fila `super_admin` se crea con la carga del ejemplo como
  `proptech_app` y el `GRANT INSERT ON auditoria` al migrador no se pidió. RA-6 y E8 quedaron respondidas;
  la aprobación adicional del consejo se mantiene en P20. Ver la ficha 3b-bis.
- **Costo de Clerk**: verificar en su página vigente antes del piloto (15, D-107).
- **Proveedores de IA y email**: se deciden en el design de 8, 13 y 14; el 2b resuelve los envíos de
  autenticación e invitaciones al integrar Clerk.

## Para Alberto

Las respuestas que sólo Alberto puede dar o conseguir, ordenadas por urgencia. Cada una tiene el
contexto, las opciones y lo que proponemos, para que alcance con un "sí" o con un comentario.

**Cómo contestar**: citando el número de cada pregunta, por mensaje o editando la tabla del final. Si
alguna no la sabés, ponelo así: también es una respuesta.

### Lo urgente

#### P1 · El edificio piloto

- **Contexto**: es la prueba de que todo funciona. El primer hito es reproducir al centavo la última
  liquidación de un edificio real; sin sus datos no hay contra qué medir.
- **Opciones**: un edificio con contacto directo tuyo.
- **Lo que proponemos**: que nos digas cuál es y nos consigas, de un mes, el padrón con coeficientes,
  las facturas, el recibo del encargado y la liquidación de ese mes, y si se puede, el extracto del
  banco.
- **Cuándo**: ya. El tiempo que tarde corre en paralelo con el resto.

#### P19 · ¿El piloto usa doble vencimiento?

- **Contexto**: algunos edificios tienen un primer vencimiento y un segundo con recargo escalonado. Hoy
  la base asume un único vencimiento con interés simple.
- **Opciones**: vencimiento único, o primer y segundo vencimiento con recargo.
- **Lo que proponemos**: lo que use el piloto; si no lo sabés, vencimiento único.
- **Cuándo**: antes del cambio 3.

#### P22 · ¿Quién usa el editor de reglas?

- **Contexto**: el editor visual de GoRules permite cambiar las reglas de cada edificio.
- **Opciones**: sólo el equipo de PropTech; o el super admin cambia valores (porcentajes, montos) y la
  estructura la armamos nosotros.
- **Lo que proponemos**: los dos niveles. El super admin cambia valores con el modo "sólo valores" de
  jdm-editor, y la estructura de una regla la armamos nosotros.
- **Cuándo**: antes del cambio 6b, el del motor de reglas.

#### P42 · Un administrador o contador de Mendoza para validar la plata

- **Contexto**: hay valores que decidimos nosotros y conviene que los mire alguien del oficio: la tasa
  de interés por defecto (3% mensual simple), los días de gracia, el modo de redondeo al centavo (P10),
  qué pasa cuando una unidad cambia de titular a mitad de mes (P11), el IVA de los consorcios (P17) y
  algunos casos de deuda. Las reglas que dependen de esto llevan "a validar (P42)" en su título.
- **Opciones**: una charla de una hora con un administrador o contador de tu confianza.
- **Lo que proponemos**: que nos presentes a alguien; llevamos la lista de puntos armada.
- **Cuándo**: antes del cambio 4, la cuenta corriente.

### Lo que puede esperar un poco

#### P9 · Qué traen los extractos de los bancos de Mendoza

- **Contexto**: para cruzar pagos con el banco necesitamos saber si cada banco informa el CBU o el
  nombre de quien transfirió y el concepto completo.
- **Opciones**: un extracto de muestra de cada banco que usan los administradores, con los datos
  personales tapados.
- **Lo que proponemos**: que nos consigas uno o dos extractos reales, anonimizados.
- **Cuándo**: antes del cambio 9.

#### P14 · El plazo para entregar el libre deuda

- **Contexto**: ya está definido quién firma el certificado y qué incluye. Falta en cuántos días hay
  que entregarlo.
- **Opciones**: lo que diga la normativa o la práctica en Mendoza.
- **Lo que proponemos**: lo que uses vos hoy.
- **Cuándo**: antes del cambio 10b.

#### P15 · Si un mes los ingresos superan los gastos

- **Contexto**: un consorcio que alquila cocheras o la terraza puede tener un mes con más ingresos que
  gastos ordinarios. Hoy el sistema frena la emisión en ese caso.
- **Opciones**: pasa como crédito al mes siguiente; va al fondo de reserva; otra cosa.
- **Lo que proponemos**: crédito al mes siguiente, salvo que el reglamento diga otra cosa.
- **Cuándo**: antes del cambio 6.

#### P16 · La parte de las unidades del propio consorcio

- **Contexto**: una portería o un departamento del consorcio no paga intereses. Falta saber qué pasa
  con su parte de cada gasto.
- **Opciones**: se reparte entre las demás unidades; o se registra como gasto del consorcio.
- **Lo que proponemos**: lo que diga el reglamento; si no lo dice, se reparte entre las demás.
- **Cuándo**: antes del cambio 3.

#### P20 · Quién aprueba una condonación de intereses

- **Contexto**: cuando un vecino discute un recargo y se lo perdonan.
- **Opciones**: super admin o administrador principal, con registro; o aprobación adicional del
  consejo cuando supera un monto.
- **Lo que proponemos**: super admin o administrador principal, con el motivo registrado y visible
  para el consejo; falta decidir el umbral de aprobación adicional (D-106).
- **Cuándo**: antes del cambio 10b.

#### P45 · Validar la propuesta de valor y el precio

- **Contexto**: el precio de partida sale de tu landing, frente a los ARS 2.950 por unidad de los
  líderes, pero nadie del rubro lo confirmó todavía.
- **Opciones**: entre 3 y 5 entrevistas cortas con administradores de Mendoza; o seguir sin validar.
- **Lo que proponemos**: las entrevistas, con una guía corta que armamos nosotros. Necesitamos que nos
  presentes a los administradores.
- **Cuándo**: antes del hito M2.

#### P57 a P60 · Cuatro preguntas de tu Excel para la cuenta corriente

- **Contexto**: el cambio 4 (la cuenta corriente) se puede construir sin estas respuestas, pero antes
  del piloto tenemos que saber si hacemos lo mismo que tu planilla.
- **Las preguntas**: P57, cuando repartís un gasto y no cierra al centavo, ¿qué hacés con el centavo
  que sobra o falta, y a qué unidad va si hay empate? P58, ¿tu Excel corta el interés al cierre del
  período? P59, el doble vencimiento con recargo, ¿se usa en el edificio piloto, y cómo convive con el
  interés diario? P60, cuando un pago no alcanza, ¿el fondo de reserva se cobra antes o después de la
  ordinaria?
- **Lo que proponemos**: que nos contestes con lo que hacés hoy; si no lo sabés, también sirve.
- **Cuándo**: antes del piloto.

### Sobre el repositorio

#### P43 · El material de ProTecc en el repositorio público

- **Contexto**: el repositorio es público. Tus documentos originales no están, pero la base cita casos
  de ProTecc v3.5 y una exploración (`openspec/exploraciones/2026-10-12-dolores-protecc.md`) resume
  tus principios, tus casos y tus preguntas.
- **Opciones**: puede quedar público; o lo sacamos del repositorio, también del historial.
- **Lo que proponemos**: que nos digas si te parece bien que quede. Si preferís que no, lo movemos a
  una carpeta privada y las citas quedan como "principio N de Alberto".
- **Cuándo**: antes de darle visibilidad al repositorio.

#### P44 · Licencia del código

- **Contexto**: sin una licencia, nadie puede reutilizar el código legalmente, aunque esté público.
  También falta decir cómo se reporta un problema de seguridad.
- **Opciones**: reservar el código (sin licencia, o pasar el repositorio a privado); o licenciarlo.
- **Lo que proponemos**: reservarlo por ahora y sumar un `SECURITY.md` con un contacto para reportar
  problemas de seguridad.
- **Cuándo**: antes del primer despliegue público.

#### P46 · Nombres propios en el repositorio público

- **Contexto**: `CLAUDE.md`, el README y `09_decisiones_y_supuestos.md` nombran a tu familia y a un docente.
- **Opciones**: quedan como están; o los reemplazamos por roles ("el socio", "el docente").
- **Lo que proponemos**: que nos confirmes si te parece bien. Si no, los sacamos.
- **Cuándo**: antes de darle visibilidad al repositorio.

### Hoja de respuesta

| Pregunta | Respuesta | Comentario |
|---|---|---|
| P1 · Edificio piloto y sus datos | ☐ Te los paso ☐ Todavía no | |
| P19 · Doble vencimiento | ☐ Único ☐ Doble | |
| P22 · Editor de reglas | ☐ Dos niveles ☐ Otra | |
| P42 · Charla con administrador o contador | ☐ Te presento a ☐ No | |
| P9 · Extractos de muestra | ☐ Te los paso ☐ No | |
| P14 · Plazo del libre deuda | Días: | |
| P15 · Ingresos mayores que gastos | ☐ Crédito ☐ Fondo ☐ Otra | |
| P16 · Unidades del consorcio | ☐ Se reparte ☐ Gasto | |
| P20 · Aprobación adicional de condonación | ☐ Sin aprobación adicional ☐ Consejo por umbral | |
| P45 · Entrevistas de precio | ☐ Te presento a ☐ No | |
| P57 · Centavo del reparto | | |
| P58 · Corte del interés en tu Excel | ☐ Al cierre ☐ Otro | |
| P59 · Doble vencimiento e interés diario | ☐ No se usa ☐ Se usa | |
| P60 · Fondo de reserva con pago parcial | ☐ Antes ☐ Después | |
| P43 · ProTecc público | ☐ Sí ☐ Sacarlo | |
| P44 · Licencia | ☐ Reservar ☐ Licenciar | |
| P46 · Nombres propios | ☐ Quedan ☐ Sacarlos | |
