# Planner · propose · intento 3

- Rol: planner (role-planner nativo de Claude Code, despachado por el orquestador). Modelo declarado por el entorno: Claude Opus 5.5 (1M). Familia compartida con el orquestador (Claude); distinta del plan-reviewer (Codex).
- Fecha: 30/10/2026, Argentina (UTC-03). Validación final 18:48:54; estado 18:48:57.
- Revisión: `main` en `533a44027d16819fd774c404372b5e5dbd39917d` más el directorio del change sin commitear (`git status --short`: sólo `?? openspec/changes/intereses-saldo-inicial-y-moroso/`).
- Alcance: PR-10 y PR-12 (BLOQUEANTES), PR-11 (CORREGIR), lo PARCIAL de PR-03 y PR-07, según `informes/propose-2-plan-reviewer.md`. No reabrí lo que Codex dio por CERRADO (PR-01, PR-02, PR-04, PR-05, PR-06, PR-08, PR-09). No toqué `informes/propose-1-*`, `propose-2-*`, `LEEME.md` ni `## Estado del orquestador` de `tasks.md`. Sin commit, sin código de producción.

## Disposición por hallazgo

### PR-10 · mes entero: $3.000 frente a $6.000 · CORREGIDO con la decisión de Juani

Decisión de Juani del 30/10/2026 (meses calendario), aplicada así:

- `design.md` D2: borré los bloques de 30 días. "Mes entero" agrupa los días a cobrar por mes calendario: cada mes con al menos un día a cobrar cobra un mes entero, con la base del primer día a cobrar de ese mes, en un tramo que va de su primer a su último día a cobrar. Como el corte es siempre fin de mes (D-113, E2), ningún tramo pasa el corte. Agregué la invariante "días a cobrar contiguos dentro de un mes" con su justificación y un error explícito si no se cumple (nunca cobra dos meses por uno).
- `design.md` D4: el CHECK `dias = 30` en `mes_entero` pasa a "un solo mes calendario, terminado en su último día", escrito con `extract` (sin `date_trunc` sobre `date`, que resuelve a `timestamptz`).
- `design.md` E3: ahora tiene dos partes. E3.1 (divisor /30 del proporcional) sigue abierta. E3.2 (mes entero por meses calendario) queda **decidida por Juani el 30/10/2026**, para ratificar al firmar. E13 pasa a ser una ratificación: ya no hay anclaje que elegir.
- `specs/intereses-por-mora/spec.md`: reescribí el requisito de forma de cálculo. Escenarios: "Un día de atraso" (tramo 30/09-30/09), "El mes siguiente" (01/10-31/10), "De proporcional a mes entero" ($3.000,00, un solo tramo 01/10-31/10, "no $6.000,00"), "De mes entero a proporcional" ($3.100,00, antes $200,00), y dos nuevos: "Corte dentro de la gracia con mes entero" ($6.000,00 en dos tramos) y "Pago a mitad de mes con mes entero" ($3.000,00 y $1.800,00). El requisito "se corta al cierre" ya no habla de bloques.
- `tasks.md` 4.3: reescrita. El mutante clave es "bloques de 30 días" (el plan del intento 2), que da $6.000,00 en "De proporcional a mes entero" y $200,00 en "De mes entero a proporcional". Además: fracción que no cuenta, un mes cada 30 días completos, base del último día, tramo desde el día 1 y el error de no contiguos.

### PR-12 · el máximo no recupera huecos · CORREGIDO con el criterio del orquestador (intervalos)

- `design.md` D2: "días cubiertos" es la **unión de los intervalos** de los tramos de los intereses que cuentan. "Días a cobrar" son los días sin cubrir entre el inicio natural y el corte, y pueden formar varios intervalos, todos con la configuración del corte (E4). Un interés importado no tiene tramos y no aporta intervalos, porque sus días son anteriores al inicio natural.
- `design.md` D3: la foto trae todos los `(desde, hasta)` de cada interés (`json_agg` ordenado, dentro del objeto de cada movimiento, que ya se arma con `json_build_object` en `lecturas.py:49-54`). Sigue siendo una sola sentencia. `Movimiento.cubierto_hasta` pasa a `tramos`.
- `design.md` D4: los tramos de un movimiento pueden no ser contiguos. Que no se solapen lo vigila la propiedad de 4.5.
- `design.md` E17 (nuevo, para firma): propuesta por intervalos. Alternativas: (a) el máximo, que pierde el hueco, y (b) restringir las correcciones al último interés, que toca `correcciones.py:185-194` del 4b (frontera CRITICAL que nadie pidió tocar), cada una con su consecuencia. E1 y PA-2 quedan alineados.
- Spec: el requisito pasa a llamarse "Cada corte cobra los días que ningún interés que cuenta cubre". Agregué el escenario de Codex "Un hueco anterior se recupera aunque haya un interés posterior": $5.000,00 con tramos 11/09-30/09 y 01/11-30/11.
- Tareas: 3.2 tiene un RED con dos tramos no contiguos y el mutante "sólo el máximo". 4.4 tiene el escenario y el mutante "cobertura por máximo", que da $3.000,00 con un solo tramo. 4.5 suma la propiedad "cobertura exacta tras cada corte, con contra-asientos de cualquier interés" y su mutante de control. 5.3 lo corre contra la base con el contra-asiento real de `correcciones.py` y el mutante de la foto.

**Hallazgo propio derivado (E19):** con intervalos, igual que antes con el máximo, un corte que da $0,00 no registra nada y sus días quedan sin cubrir. Una tasa 0 **difiere** los días, no los perdona: con 0% en septiembre y 3% desde el 01/10, el corte 31/10 cobra 51 días al 3% ($5.100,00). Lo dejé visible como E19, con escenario, mutante (4.4) y prueba contra la base (5.3), en vez de esconderlo.

### PR-11 · replay que no distingue filas con iguales sumas · CORREGIDO

- `design.md` D5: agregué la columna `firma_del_pedido` a `carga_de_saldo_inicial` (`"v1:"` + SHA-256 del pedido validado y normalizado, en JSON canónico). La normalización: unidades ordenadas por `unidad_id`, filas ordenadas por la tupla completa, importes con dos decimales, sin `operacion_id`, `request_id`, identidad ni reloj. El replay compara firmas. CHECK de forma `^v1:[0-9a-f]{64}$`.
- Por qué la firma y no el aporte por fila en `origen_de_saldo_inicial`: es una columna y una función pura, sin SQL de reconstrucción. Además cubre todo el pedido (modo, archivo, filas en cero), y R09 pide archivo y fila, no importe por fila (`05_reglas_de_negocio.md:356`). La alternativa queda en E16 (b) con su costo.
- E16: corregí la afirmación de trazabilidad. Las dos opciones pierden el aporte por fila; la diferencia está en el replay y en E11.
- Spec saldo-inicial: el requisito de replay compara por firma. Escenarios nuevos: "Misma operación con iguales sumas y otras filas" ($85.000/$20.000 frente a $84.000/$21.000, conflicto) y "Mismo pedido en otro orden" (con `85000` frente a `85000.00`, replay). El Purpose y "Cada fila guarda su origen" quedan alineados.
- `tasks.md` 6.4: test unitario nuevo `test_firma_saldo_inicial.py`. RED: el replay que compara el libro devuelve lo registrado. Mutantes: firma por sumas, sin ordenar, sin normalizar importes, sin interés por fila. En 2.1 se sumó el CHECK de la firma a la fila de CHECK de la matriz.

### PR-03 (PARCIAL) · CERRADO en el plan

El caso migrado queda coherente con meses calendario y con R09. Vence 10/08, migra 15/10, 3% mes entero, $80.000: el corte 31/10 cobra octubre con tramo 16/10-31/10, $2.400,00 (nunca días anteriores a la migración). El corte 30/11 cobra noviembre, 01/11-30/11, $2.400,00. Septiembre da $2.550,00. Lo actualicé en la spec ("Mes entero después de migrar", "Segundo mes después de migrar") y en las tareas 4.3 y 6.3, con el mutante del vencimiento original recalculado a $6.560,00 (82 días). La continuidad general que Codex marcó en PR-12 queda resuelta por E17.

**Duda real de plata, E18:** con "mes entero", la fracción 16/10-31/10 cobra un mes entero. Si el interés importado del Excel ya cobró octubre, octubre se cobra dos veces. Recomiendo cobrarla (coincide con la regla de Juani y con R09), con dos mitigaciones: que el 5 lo muestre y que se le pregunte a Alberto en P58. Dejé las alternativas con sus consecuencias.

### PR-07 (PARCIAL) · CERRADO en el plan

La granularidad que faltaba para el replay por filas queda cubierta por la firma del pedido (PR-11). Agrupación, vencimientos, referencias múltiples y el choque con `0023:199-200` siguen como los dejó el intento 2.

## Otros archivos tocados

- `proposal.md`: What Changes (mes entero, intervalos, firma), lista de elecciones E1 a E19 con E3.2/E13 como ratificación, Knowledge Base Impact (R03, glosario, ficha del 5, P58) y el texto de `## Aprobación`, cuya tabla queda vacía.
- `design.md`: riesgos nuevos (huecos con otra configuración, mes de la migración), PA-2 y PA-3.
- `tasks.md`: "Antes de construir" (E1 a E19) y el seguimiento del rompedor y del archivo. Siguen siendo 24 tareas.

## EVIDENCIA

| Comando | Hora | Salida relevante |
|---|---|---|
| `python3` con `Decimal`, `ROUND_HALF_UP` y un oráculo propio por intervalos y meses calendario (scratchpad, no en el repo) | 18:45 aprox. (sin reloj capturado) | Mes entero: 1 día `3000.00` tramo 30/09-30/09; mes siguiente `3000.00` 01/10-31/10; prop→mes `2000.00` y `3000.00` 01/10-31/10; mes→prop `3100.00`; migrada `2400.00` y `2550.00` 16/10-31/10, segundo mes `2400.00` 01/11-30/11; gracia 5 `6000.00` en tramos 29/09-30/09 y 01/10-31/10; pago 20/09 `3000.00` y `1800.00`. Hueco por intervalos `5000.00`, 50 días (11/09-30/09 y 01/11-30/11); por máximo `3000.00`. E1/E19 51 días `5100.00`, al 6% `10200.00`. Proporcional migrada `1280.00`/`1360.00`. PR-11: `105000` y `105000` |
| `python3` con `Decimal` | 18:47 aprox. | Mutante del vencimiento original en agosto: 82 días, `6560.00`; interés importado en la base: `2520` |
| `bat` de `emisiones.py:70-125`, `correcciones.py:160-196`, `estado.py:85-126`, `lecturas.py:30-75`, `0023:78-92,195-210`, `05_reglas_de_negocio.md:173-202,340-372`, `09_decisiones_y_supuestos.md:2020-2046`; `rg` de `Trazabilidad`, `_firma` e `image: postgres` | 18:40 a 18:47 | `_firma` en `emisiones.py:72` y comparación en `:97-111`; correcciones bajo el candado en `:185-194` sin restricción de "último interés"; `ck_mov_importe CHECK (importe>0)` (`0023:84`); `uq_mov_interes` (`0023:205-206`); R09 "Trazabilidad" en `:356`; PostgreSQL `18.6` (`infra/compose.yaml:41`) |
| `openspec validate intereses-saldo-inicial-y-moroso --strict` (1.14.3) | 18:48:44 | Falló por dos avisos de requisitos de más de 500 caracteres (los míos); los acorté |
| `openspec validate intereses-saldo-inicial-y-moroso --strict` | 18:48:54 | `Change 'intereses-saldo-inicial-y-moroso' is valid` |
| `openspec status --change intereses-saldo-inicial-y-moroso --json` | 18:48:57 | `isPlanningComplete: true`, cuatro artefactos `done`. Es estado de artefactos, no aprobación |

## JUICIO

Autor: planner, intento 3. Comparé las correcciones con los números recalculados por un oráculo propio (independiente de producción, que no existe) y con las líneas de código citadas. Confianza alta en que PR-10, PR-11 y PR-12 quedan resueltos **en el plan**: los números del escenario y del algoritmo coinciden, y cada aserción nueva de plata tiene un mutante con su rojo nombrado. Confianza media-alta en la invariante "días a cobrar contiguos dentro de un mes": la deduje de que los cortes son fin de mes y de que un interés cuenta o deja de contar entero, pero no la ejecuté; por eso tiene un error explícito y una propiedad en 4.5. E18 y E19 son decisiones de plata reales que no corresponde que tome yo.

## SUPOSICIÓN

- No se ejecutó código, suite, mutantes ni PostgreSQL. Los rojos son objetivos de prueba, no hechos.
- La validación corrió con openspec 1.14.3, no con la 1.13.0 fijada por el proyecto. No toqué la instalación.
- Supongo que la contra-asiento de un interés por `correcciones.py` deja ese interés fuera del estado como par (`estado.py:112-124`). Lo leí en el código pero no lo ejecuté.
- La expresión del CHECK de mes entero (`extract(day FROM hasta + 1) = 1 AND desde > hasta - extract(day FROM hasta)::int`) no se probó contra PostgreSQL 18. La forma final la valida el constructor en la 2.1.
- No consulté Engram ni otros informes de revisores para buscar acuerdo. No actualicé `obsidian.md`, la KB ni `LEEME.md`.

## Fuentes

`informes/propose-2-plan-reviewer.md` (completo); `proposal.md`, `design.md`, `tasks.md`, `specs/intereses-por-mora/spec.md`, `specs/saldo-inicial/spec.md` (completos antes de editar); el código y la KB de la tabla de EVIDENCIA; `CLAUDE.md` del proyecto (en contexto).

## Contaminación

Este intento está guiado a propósito por el informe de Codex (`propose-2-plan-reviewer.md`) y por el brief del orquestador, que trae la decisión de Juani sobre PR-10 y el criterio de intervalos para PR-12. No es independiente de ellos. Recalculé con oráculo propio y verifiqué en el código cada número y cada línea que cito. No leí `propose-1-*` ni `propose-2-planner.md` en este intento.

## Para firmar

**(a) Cambian plata o el contrato con el 5 y necesitan una decisión real**

- **E1** · Re-emisión tras anular: los días pasan al corte siguiente, con la configuración de ese corte. Recomiendo la propuesta (no toca `0023` ni pide préstamo).
- **E2** · Corte = último día del mes anterior al período emitido. Recomiendo la propuesta.
- **E3.1** · Proporcional = tasa mensual / 30 por día. Recomiendo la propuesta y validarla con P58/P42 antes del piloto.
- **E4** · Una sola versión de configuración por corte, también para los huecos recuperados. Recomiendo la propuesta.
- **E5** · Base día por día con la fecha valor del crédito, gracia "pagado al vencimiento". Recomiendo la propuesta.
- **E7** · Un período con sólo interés no cuenta como liquidación vencida, tampoco en el caso mixto. Recomiendo la propuesta, sabiendo que es una elección adicional a R20.
- **E8** · R20 cuenta obligaciones vencidas con capital, no meses. Recomiendo la propuesta.
- **E11** · Se rechaza un período migrado con sólo interés y sin capital en ninguna fila. Recomiendo la propuesta y aceptar la limitación en el contrato del 5.
- **E14** · "A una fecha" = fecha de clasificación sobre el libro actual, sin historia. Recomiendo la propuesta.
- **E15** · El replay devuelve los mismos intereses y recalcula el saldo anterior. Recomiendo la propuesta.
- **E16** · El 4c agrupa las filas por período y el replay compara la firma del pedido. Recomiendo la propuesta (la firma en vez del aporte por fila).
- **E17** · Cobertura por intervalos, así un hueco se recupera aunque haya un interés posterior. Recomiendo la propuesta.
- **E18** · Con "mes entero", la fracción del mes de la migración se cobra como mes entero. Recomiendo cobrarla, más el aviso en el 5 y la pregunta a Alberto en P58.
- **E19** · Una tasa 0 (o un importe $0,00) difiere los días, no los perdona. Recomiendo aceptarla en el 4c como comportamiento declarado, con confianza media: si Juani prevé edificios que pasen de 0% a una tasa, conviene la alternativa de días exentos, que vuelve al planner.

**(b) Ratifican reglas o decisiones ya existentes**

- **E3.2** · "Mes entero" por meses calendario: la decisión de Juani del 30/10/2026. Ratificar.
- **E13** · Mes entero de una migrada y al cambiar de forma, sin anclaje: consecuencia de E3.2. Ratificar.
- **E6** · Umbral de R30 con `>=` ("$500 o más", D-143). Ratificar.
- **E9** · Saldo inicial según D5 (una carga por edificio, `pendiente`, interés importado con corte en la migración), lo que bajan R09/D-068/D-080/D-082/D-083 al libro. Ratificar.
- **E10** · Interés en todas las cuentas de unidad del edificio, con el candado único ordenado. Es una consecuencia de R03. Ratificar.
- **E12** · El 4c no autoriza ni audita; lo hacen el 5 y el 10a, como D9 del 4b. Ratificar.
- **PA-1** · No es una elección del 4c: queda como bloqueante del 5 (corrección posterior a confirmar en R09 frente a R08). Firmar que el 4c no la declara cumplida.
