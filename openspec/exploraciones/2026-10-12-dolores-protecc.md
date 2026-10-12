# Dolores de ProTecc contra el MVP de edificios

> Exploración, no propuesta. Mapea los 9 principios, los 42 casos y las ideas del documento de
> Alberto (`especificacion/documentos-alberto/ProTecc_problemas_y_reglas_v3.5.md`, v3.5,
> 10/10/2026) contra nuestra base de conocimiento (`mvp.md`, `reglas-de-negocio.md`,
> `decisiones.md`, `glosario.md`, `proyecto-final.md`). Responde a D-054: el MVP sigue siendo el
> nuestro, sólo edificios; este documento junta los dolores y problemas de Alberto para decidir
> cuáles tocan al MVP y cuáles van a `proyecto-final.md`. No se tocó código ni `conocimiento/`.
>
> Convención: cada fila cita de dónde sale (HU-X, R0X, D-0XX, o el ID de Alberto). Donde no hay
> cita posible porque es una lectura mía del cruce, va marcado **(propuesta)**.

---

## 1. Principios de Alberto contra nuestras decisiones

| # | Principio de Alberto | Nuestra decisión/regla | Estado | Nota |
|---|---|---|---|---|
| P1 | La liquidación emitida no se edita; toda corrección es un movimiento nuevo | D-016, R08, HU-A9, HU-A5 ("intento emitirlo otra vez, el sistema lo impide") | Coincide | Alberto agrega una excepción acotada (ventana de anulación antes de distribuir, A5/Q10) que nuestra base no contempla. Ver caso A5 abajo: **choca** en ese punto específico. |
| P2 | Toda corrección es un movimiento nuevo | D-016, R08 | Coincide | Mismo mecanismo, mismas palabras. |
| P3 | ProTecc sugiere y el administrador decide; nada se asigna solo | DEC-12 (dos señales) no tiene equivalente; nuestro R11/HU-A7 sólo marca "coincide" o "no encontrado", sin cola de sugerencias ordenadas | Falta | No hay nada en nuestra base que contradiga el principio, pero tampoco el mecanismo (cola de excepciones con sugerencias). Ver A1 abajo. |
| P4 | Sólo un pago confirmado cancela deuda | D-017, R11, HU-A6 | Coincide | Idéntico: "pendiente de comprobante"/"informado" no cambia el saldo, sólo "confirmado". |
| P5 | Todo pago tiene que poder identificarse (centavos, código, CBU histórico, CVU) | R11 sólo identifica por número de operación único + comparación con extracto (importe, fecha, CUIT si el banco lo informa) | Difiere | Cubrimos la mitad del problema (evitar duplicados) pero no tenemos los tres mecanismos de refuerzo de DEC-10. Ver sección 3. |
| P6 | La emisión no depende de servicios externos | Ninguna decisión lo dice explícitamente; HU-A5 no menciona fallas externas | Falta | No hay contradicción, pero tampoco un "modo degradado" escrito. Ver caso A4. |
| P7 | El vecino siempre ve el estado de su situación | HU-V2, HU-V3, HU-V4 (estado: informado/confirmado/rechazado) | Coincide | |
| P8 | Cada problema se mide | Sin métricas ni entidad de excepción en el MVP | Falta | Ver sección 3, "Excepción como entidad". Queda para después del MVP (ver abajo). |
| P9 | ProTecc nunca custodia fondos | D-005, D-017 | Coincide | Idéntico, con el mismo argumento regulatorio (BCRA/UIF). |

**Resumen**: 5 coinciden (P1 en lo general, P2, P4, P7, P9), 1 difiere (P5), 3 faltan como mecanismo
aunque no como principio (P3, P6, P8). Ninguno choca de lleno; el único punto de choque real está
en la excepción que Alberto le agrega a P1 (ver A5).

---

## 2. Los 42 casos

Clasificación: **Cubierto** (ya resuelto, cito HU/R/D) · **Hueco MVP** (aplica a edificios, no
resuelto, propongo cómo) · **Fuera del MVP** (va a `proyecto-final.md`) · **Choca** (contradice una
decisión nuestra).

### M0-M1 · Incorporación y preparación

| ID | Problema | Clasificación | Por qué / qué hacer |
|---|---|---|---|
| F1 | Saldos iniciales al migrar | Cubierto | HU-A2, R09 (saldo con o sin detalle, trazabilidad por archivo y fila). |
| A2 | Factura mal leída por IA | Hueco MVP | R12 cubre duplicados y receptor equivocado, pero no la "comparación con el historial del proveedor" (confianza por campo) que pide Alberto. **(propuesta)** agregar un chequeo de monto atípico contra el historial del proveedor al control antes de emitir (cambio 7 `liquidacion-y-emision` o 14 `lectura-de-facturas`). |
| C1 | Gasto particular de una unidad | Cubierto | R14, HU-A3b. |
| C2 | Gastos por sector o torre | Cubierto | R01 (grupos de prorrateo). |
| C4 | Cargo por uso o daño de amenity | Cubierto (manual) | R14 permite cargarlo a mano. El módulo automático de reservas que genera el cargo solo queda fuera del MVP (ya está en `proyecto-final.md`, F3 Comunidad). |
| C5 | Consumos por medidor | Cubierto (por decisión) | D-026: se cargan como cargos particulares importados por Excel. El módulo de medidores real queda en F6 (ya documentado). |
| H1 | Factura de proveedor duplicada o nota de crédito | Hueco MVP | La parte de duplicados ya está (R12: `cuit+ptoVta+tipoCmp+nroCmp`). Falta modelar la nota de crédito como entidad asociada a la factura que corrige, con su monto topeado al de esa factura (12.13 de Alberto). **(propuesta)** agregar a `gastos-y-cargos` (cambio 6) o `lectura-de-facturas` (cambio 14). |
| H2 | Sueldos y cargas sociales del personal | Cubierto | D-028, HU-A3 (sueldo entra como gasto desde el recibo del contador). |

### M2 · Emisión

| ID | Problema | Clasificación | Por qué / qué hacer |
|---|---|---|---|
| A3 | El total no cierra con el Excel | Cubierto | HU-A4, criterio de M1 ("reproduce su última liquidación al centavo") y M3 (mes en paralelo). |
| A4 | Falla externa el día de emisión | Hueco MVP | No existe un "modo degradado" escrito. **(propuesta)** nombrar el principio P6 en `reglas-de-negocio.md` y definir, en el *design* de `liquidacion-y-emision`, qué pasa si falla la lectura del extracto o la IA el día de emitir. |
| A5 | Error grave detectado antes de distribuir | **Choca** | Ver detalle abajo. |
| C3 | Fondo de reserva mezclado con la caja | Fuera del MVP | Ya decidido: D-023/D-031 sacan la tesorería y el saldo de caja del MVP. Las "subcuentas de fondo" quedan en F6. |
| C7 | Obra con cuota extraordinaria | Cubierto (en parte) | La cuota extraordinaria en sí está cubierta por R13/HU-A3b. La subcuenta de obra (entra lo recaudado, sale lo pagado a la constructora) es tesorería, fuera del MVP (F6). |
| H4 | Requisitos legales de la liquidación | Hueco MVP | Nadie en nuestra base revisó qué exige la normativa de Mendoza para una expensa (Alberto cita la Ley 941 de CABA como ejemplo). **(propuesta)** tarea de investigación antes de cerrar el PDF de la expensa en el cambio 7; comparte la pregunta abierta Q12 de Alberto. |

### M3 · Vencimiento y cobranza

| ID | Problema | Clasificación | Por qué / qué hacer |
|---|---|---|---|
| A1 | Pago que no se puede asignar | Hueco MVP | HU-A7 sólo marca "coincide"/"no encontrado". No hay cola de excepciones con sugerencias ordenadas por confianza. Depende de qué tan lejos queramos llevar la identificación (sección 3). |
| B1 | Pagó dos veces o de más | Cubierto | R05 (excedente como crédito a favor), HU-A6. |
| B2 | Pagó con el número de otra unidad | Hueco MVP | No existe un "asistente de reimputación" con los dos movimientos enlazados que pide Alberto (12.3). R08 permite corregirlo como corrección genérica, pero sin ese flujo específico ni la reevaluación de morosidad enlazada. **(propuesta)** agregarlo al cambio 10 `morosidad` o 8 `pagos-informados`. |
| B3 | Transferencia a la cuenta vieja | Cubierto | El flujo general de R11 ya lo resuelve: el administrador confirma a mano aunque el origen sea otro, no hay bloqueo por cuenta de origen. |
| B4 | "Pagué y me figura deuda" | Cubierto | HU-V4 (estado visible: informado/confirmado/rechazado). |
| D1 | Un pago para varias unidades | Cubierto | HU-A6 (el vecino reparte el pago entre sus unidades), R11. |
| D2 | Pago parcial | Cubierto | R05, R04 (orden de imputación). |
| D5 | Pago en efectivo en la administración | Fuera del MVP | El alcance del MVP sólo contempla comprobante + confirmación (D-017); no hay recibo numerado para efectivo. Comparte la pregunta abierta Q13 de Alberto. |
| E1 | Comprobante falso o equivocado | Cubierto (diseño distinto) | D-018/R11: la IA extrae datos del comprobante y el vecino los confirma, en vez de que el vecino declare y el sistema compare contra lo extraído. Logra el mismo objetivo (precisión) por otro camino. |
| E2 | Mismo comprobante subido dos veces | Cubierto | R11 (número de operación único). Mejora menor pendiente: Alberto agrega huella del archivo para capturas de pantalla distintas de la misma transferencia; no está en R11. **(propuesta, chica)** sumarla al cambio 8. |
| E3 | Vecino que nunca sube el comprobante | Hueco MVP | Depende de CBU histórico (sección 3), que no implementamos. Sin eso, el pago queda sin identificar hasta que alguien lo revisa a mano. |
| G4 | Pago entre primer y segundo vencimiento | Hueco MVP | R03 modela un interés simple continuo desde un único vencimiento; Alberto describe un esquema de primer y segundo vencimiento con recargo escalonado. No sabemos si el edificio piloto usa ese esquema. **(propuesta)** preguntarlo antes de tocar R03, que ya está marcada "falta validar". |
| W1 | Número de WhatsApp bloqueado | Fuera del MVP | D-006: WhatsApp queda para después, el MVP usa email. |
| W2 | Canal de WhatsApp caído | Fuera del MVP | Mismo motivo que W1. |
| W3 | Recordatorio en domingo o feriado | Hueco MVP (chico) | Aplica igual al email: HU-V6 no dice qué pasa si el aviso cae en fin de semana. **(propuesta)** regla simple en el cambio 13 `avisos-por-email`. |
| W4 | Contacto inválido | Hueco MVP | No hay validación de contactos ni lista de "unidades sin contacto válido". **(propuesta)** cambio 13 o 11 `portal-del-vecino`. |
| W5 | El vecino responde por el chat | Fuera del MVP | Depende de WhatsApp (W1/W2). |

### M4-M5 · Cierre, morosidad y eventos fuera de ciclo

| ID | Problema | Clasificación | Por qué / qué hacer |
|---|---|---|---|
| B5 | Intereses que el vecino discute (condonación) | Hueco MVP | No existe la entidad Condonación ni un movimiento que neutralice un recargo. Comparte la pregunta abierta Q1 de Alberto (quién aprueba). **(propuesta)** nueva regla (¿R17?) en el cambio 10. |
| D3 | Saldos insignificantes por redondeo | Hueco MVP (chico) | R07 ya resuelve el redondeo del reparto (mayor resto), pero no hay un umbral mínimo para saldos chicos que quedan de intereses o pagos parciales. |
| G1 | Plan de pago o convenio de deuda | Fuera del MVP | No está en el alcance "Entra" de `mvp.md`. Es un módulo entero (cuotas, estado vigente/caído) que no hace falta para liquidar y cobrar la primera vez. Debería anotarse en `proyecto-final.md`, que hoy no lo menciona explícitamente. |
| G2 | Deuda en gestión judicial | Hueco MVP (chico) | No hay marca de "gestión judicial" que frene el aviso de mora (HU-V6). Bajo riesgo en el MVP porque no hay recordatorios automáticos complejos, pero existe. |
| H3 | Diferencia entre caja y banco | Fuera del MVP | Conciliación completa de ingresos y egresos es tesorería (D-023), fuera del MVP. HU-A7 sólo concilia ingresos de vecinos contra comprobantes. |
| M1 | Moroso crítico | Hueco MVP | HU-A8 muestra deuda y antigüedad pero no define "moroso crítico" (2+ liquidaciones vencidas). El bloqueo de amenities queda fuera porque las reservas no están en el MVP, pero la definición en sí es barata y útil para priorizar cobranza. |
| B6 | Paga el inquilino y figura el propietario | Cubierto | D-029 (persona de contacto, propietario o no), D-032 (inquilino se valida con el piloto). |
| B7 | Corregir una liquidación emitida | Cubierto | R08, HU-A9. El detalle de "aparece en la boleta siguiente en línea propia" (12.14) no está en el texto de la HU, pero no lo contradice; queda para el *design* del cambio. |
| C6 | Cochera separada del departamento | Cubierto | D-029 (cada tipo de unidad es independiente, con su propio coeficiente). |
| D4 | Pago confirmado que se revierte | Hueco MVP | R11 sólo tiene informado/confirmado/rechazado; no existe el estado "revertido" ni el contra-movimiento. Aplica a edificios igual que a barrios (un cheque se puede rechazar en cualquiera). |
| G3 | Certificado de libre deuda por venta | Fuera del MVP | No está en el alcance "Entra" de `mvp.md`. Es frecuente en edificios reales (compraventas) y Alberto lo marca urgente. Candidato a revisar si entra antes de lo planeado (ver sección 5). |

**Conteo**: Cubiertos 18 (F1, C1, C2, C4, C5, H2, A3, C7, B1, B3, B4, D1, D2, E1, E2, B6, B7, C6) ·
Huecos MVP 15 (A2, H1, A4, H4, A1, B2, E3, G4, W3, W4, B5, D3, G2, M1, D4) · Fuera del MVP 8 (C3, D5,
W1, W2, W5, G1, H3, G3) · Choca 1 (A5).

---

## 3. Ideas valiosas que no son "un caso"

| Idea | Adoptar | Por qué | Impacto en nuestro modelo |
|---|---|---|---|
| Código de unidad en el concepto de la transferencia | **En el MVP** | Costo casi nulo (es texto en la boleta), reduce A1 y B2 sin tocar el modelo de datos. | Ninguno: sólo cambia la plantilla de la boleta (cambio 7). |
| CBU histórico recordado por unidad | **En el MVP** | Captura de datos barata (guardar qué cuenta pagó la última vez) con payoff real en A1 y E3. | Agrega un campo/tabla chica al módulo de pagos (cambio 8 o 9). No reescribe nada decidido. |
| Centavos identificadores por unidad | **Después** | Alto valor pero toca la emisión (asignar centavos únicos sin romper el prorrateo, Q18 de Alberto sigue abierta) y la conciliación del extracto. Alberto mismo lo valida con el 20% de pagos sin identificar antes de ir a CVU; conviene medir primero con extractos reales (Q2) antes de meterse con esto. | **Requiere decisión de Juani**: toca R07 (redondeo/montos) y el diseño de la boleta. Marcado abajo. |
| Control automático antes de emitir, con bloqueantes y advertencias (7.2/12.5) | **En el MVP** | Ya tenemos el germen (HU-A5 impide reemitir); formalizarlo como lista de chequeos con dos niveles es barato y mejora la confianza del primer mes. | Se integra a la preliquidación (HU-A4) y al *design* del cambio 7, sin tocar reglas decididas. |
| Estados del pago completos (pendiente, informado, revisión, confirmado, rechazado, conciliado, **revertido**) | **Parcial, en el MVP** | "Revertido" ya salió como hueco (D4) y conviene resolverlo junto. Los demás estados (conciliado distinto de confirmado, revisión distinta de informado) son más finos de lo que R11 necesita hoy. | **Requiere decisión de Juani**: agregar "revertido" toca R11/D-017, que están vigentes. Marcado abajo. |
| Excepción como entidad propia (con sugerencias, resolución, tiempo) | **Después** | Es el soporte de las métricas (P8) y de la cola de sugerencias (P3), pero es un módulo nuevo entero. El MVP no necesita medir "soporte por consorcio" todavía: tiene un piloto, no una cartera. | Ninguno ahora. Queda como entrada para `proyecto-final.md`. |
| Morosidad por antigüedad ("moroso crítico": 2+ liquidaciones vencidas) | **En el MVP** | Es una consulta sobre datos que ya vamos a tener (cuenta corriente, liquidaciones). No requiere el bloqueo de amenities (que depende de reservas, fuera del MVP). | Se agrega a HU-A8 (cambio 10), sin tocar reglas decididas. |
| Roles propietario/residente/responsable de pago separados, con vigencia | **Ya decidido que no, por ahora** | D-032 ya resolvió esto: se valida con el piloto si "persona de contacto" alcanza antes de separar roles. No hay nada nuevo que cambie esa decisión. | Ninguno. Mantener D-032 como está. |

---

## 4. Preguntas abiertas de Alberto que también nos bloquean

- **Q2** (qué trae el extracto de cada banco: CBU, nombre del originante, concepto completo). Es la
  pregunta de prioridad 0 del propio documento de Alberto, y bloquea directamente nuestro HU-A7 y
  el diseño del cambio 9 `extracto-bancario`. Nuestra base ya anticipa parte de esto ("CUIT de
  origen cuando el banco lo informa" en R11), pero no probamos con extractos reales de los bancos
  que usan los administradores de Mendoza.
- **Q10** (ventana de anulación antes de distribuir). Bloquea el caso A5, que choca con nuestro P1.
- **Q1** (quién aprueba una condonación de interés). Bloquea el hueco B5.
- **Q9** (cómo funcionan el primer y segundo vencimiento y el interés sobre pagos parciales).
  Bloquea el hueco G4 y la validación pendiente de R03.
- **Q13** (¿se acepta efectivo?). Bloquea D5, hoy fuera del MVP por decisión, no por investigación.
- **Q12** (requisitos legales por jurisdicción). Bloquea H4.
- **Q18** (cómo convive el centavo identificador con el prorrateo y el recargo). Bloquea la
  adopción de centavos identificadores de la sección 3.
- **Q11** (quién firma el libre deuda y en cuánto tiempo). Relevante sólo si G3 entra al MVP (ver
  sección 5).

---

## 5. Decisiones que necesita Juani

1. **¿Agregamos una ventana de anulación de liquidación antes de distribuir (A5/Q10)?**
   Recomendación: sí, acotada a "emitida y todavía no distribuida ni vista por nadie", con motivo
   registrado. Alternativa: mantener P1/D-016 estricto, sin excepciones, y corregir todo con un
   ajuste al mes siguiente aunque el error se vea antes de enviar nada.

2. **¿Agregamos el estado "revertido" (pago confirmado que el banco devuelve) a R11?**
   Recomendación: sí, aplica a edificios igual que a barrios (un cheque se puede rechazar en
   cualquiera). Alternativa: tratarlo como una corrección genérica con R08, sin estado propio
   (más simple de implementar, menos trazable para el vecino y el administrador).

3. **¿Adoptamos ya el código de unidad en el concepto y el CBU histórico (sección 3), aunque sea sin la cola de sugerencias completa?**
   Recomendación: sí a los dos, son baratos y no tocan nada decidido. Alternativa: esperar a medir
   cuánto de A1/E3 se explica sin ellos, para no construir algo que el piloto no necesite.

4. **¿Adoptamos la definición de "moroso crítico" por antigüedad en HU-A8, sin bloqueo de amenities?**
   Recomendación: sí, es una consulta sobre datos que ya vamos a tener. Alternativa: dejar la
   morosidad como está (sólo deuda y antigüedad simple) hasta que el piloto lo pida.

5. **¿El certificado de libre deuda por venta de unidad (G3) entra al MVP o se queda en `proyecto-final.md`?**
   Es frecuente y urgente en edificios reales (compraventas), y hoy no está en nuestro alcance.
   Recomendación: preguntarle a Alberto si aparece seguido en su cartera actual antes de decidir;
   si sí, evaluar moverlo a M2 o M3. Alternativa: dejarlo afuera y resolverlo a mano como hoy, igual
   que cualquier administrador sin sistema.

6. **¿Centavos identificadores por unidad (sección 3): lo evaluamos para el MVP o lo dejamos para después de medir con extractos reales?**
   Recomendación: después. Depende de responder primero Q2 (qué traen los extractos) y Q18 (cómo
   convive con el prorrateo), y Alberto mismo lo condiciona a una métrica que todavía no existe.
   Alternativa: adelantarlo ya, aceptando el riesgo de diseñarlo sin esa validación.

7. **¿Investigamos los requisitos legales de la liquidación en Mendoza antes de cerrar el PDF de la expensa (H4/Q12)?**
   Recomendación: sí, una tarea de investigación chica antes de terminar el *design* del cambio 7.
   Alternativa: asumir que no hay requisitos especiales y corregir si aparece un reclamo.

8. **¿Agregamos la nota de crédito como entidad asociada a la factura (H1)?**
   Recomendación: sí, es chica y evita cobrarle de más a los vecinos por un gasto ya corregido por
   el proveedor. Alternativa: seguir cargándola como un gasto negativo suelto, sin asociarla a la
   factura original (más simple, pierde la trazabilidad de 12.13).

9. **¿Respondemos la Q2 de Alberto (qué traen los extractos de los bancos que usan los administradores de Mendoza) antes de diseñar el cambio 9?**
   Recomendación: sí, es la pregunta de prioridad 0 del propio documento de Alberto y condiciona
   directamente nuestro HU-A7. Alternativa: diseñar con los supuestos que ya tenemos en R11 y
   ajustar cuando aparezcan diferencias.
