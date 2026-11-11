# Plan-reviewer · intento 3

- Rol: plan-reviewer. Ejecutor declarado: Codex, ejecución directa de esta sesión, sin proceso Codex anidado. No se infiere un modelo o effort no expuesto por el entorno.
- Número de revisión: 3, última revisión antes de la decisión humana.
- Fecha: 30/10/2026, Argentina (UTC-03).
- Revisión: `main` en `533a44027d16819fd774c404372b5e5dbd39917d`, más los artefactos sin commitear del change. Alcance limitado a las correcciones reclamadas y sus consecuencias nuevas. Única escritura: este informe.

## Fuentes leídas

Las rutas cortas de artefactos son relativas a `openspec/changes/intereses-saldo-inicial-y-moroso/`.

- `informes/propose-2-plan-reviewer.md`, primero; `informes/propose-3-planner.md`, después; `informes/propose-1-plan-reviewer.md`, para recuperar antecedentes y declarar contaminación. Lecturas numeradas y focalizadas para completar salidas extensas truncadas.
- `proposal.md`, `design.md`, `tasks.md`; los cinco `specs/*/spec.md`: intereses-por-mora, saldo-inicial, situacion-de-cobranza, libro-de-movimientos y reparto-de-montos. Foco en D2-D5, E1-E19, tareas 2.1/3.2/4.3-4.5/5.3/6.3-6.4.
- `CLAUDE.md`, instrucciones AGENTS aportadas y `obsidian.md:1-65`, sólo lectura.
- `knowledge-base/05_reglas_de_negocio.md:173-202,340-372` y `knowledge-base/09_decisiones_y_supuestos.md:2020-2046,2926-2953`.
- `backend/src/proptech_core/cuenta_corriente/aplicacion/lecturas.py:30-75`, `emisiones.py:70-125`, `correcciones.py:160-196`, `dominio/estado.py:85-130`.
- `backend/migraciones/versions/0023_libro_de_movimientos.py:78-92,195-210`.

## EVIDENCIA

Todo corresponde a la revisión del encabezado. Los recálculos son oráculos de aritmética del plan, sin importar producción. Las lecturas y sus salidas están en la transcripción de herramientas, sin archivo de logs adicional.

| Comando ejecutado | Hora local | Salida relevante |
|---|---|---|
| `pwd`; `git status --short`; `git rev-parse HEAD`; `openspec list --json` | Sin reloj capturado, antes de 18:51:55 | Repo esperado; HEAD del encabezado; sólo `?? openspec/changes/intereses-saldo-inicial-y-moroso/`; 0/24 tareas, `in-progress` |
| `openspec status --change intereses-saldo-inicial-y-moroso --json`; `openspec instructions design --change intereses-saldo-inicial-y-moroso --json` | Sin reloj capturado, antes de 18:51:55 | Cuatro artefactos `done`, `isPlanningComplete: true`; contexto y contrato de diseño recuperados. No equivale a implementación ni aprobación |
| `python` para lectura inicial | Sin reloj capturado | Salida 127, `python: command not found`. Se repitió con `python3`; no cuenta como chequeo válido |
| `python3` con `Path.read_text().splitlines()` numerado | Antes de 18:51:55 y lecturas posteriores, sin reloj individual | Fuentes y citas de este informe; no ejecutó módulos del proyecto |
| `date -Iseconds`; `openspec --version`; `openspec validate intereses-saldo-inicial-y-moroso --strict` | 18:51:55 | Versión disponible `1.14.3`; salida 0: `Change 'intereses-saldo-inicial-y-moroso' is valid` |
| `date -Iseconds`; `python3` con `Decimal` desde texto, `ROUND_HALF_UP`, `datetime`, JSON y SHA-256 | 18:52:47 | Resultados detallados debajo. Sin PostgreSQL ni tests |

La versión disponible no es la 1.13.0 fijada por el proyecto. No se instaló ni actualizó nada. La validación certifica estructura con 1.14.3, no semántica financiera ni compatibilidad ejecutada con 1.13.0.

### Recálculos propios

- Sobre $100.000 al 3% proporcional, cada día vale $100: septiembre 11/09-30/09, 20 días = **$2.000,00**; octubre 01/10-31/10, 31 días = **$3.100,00**.
- E17: al quitar sólo el interés registrado en octubre, queda descubierto septiembre, no octubre. Al corte 30/11 se cobran 20 + 30 días = **$5.000,00**, en 11/09-30/09 y 01/11-30/11. Volver al máximo 31/10 cobra sólo 30 días = **$3.000,00**. El contra-asiento de un interés anterior es admisible estáticamente: `correcciones.py:185-194` no exige que sea el último; `estado.py:112-124` excluye el par corregido.
- Mes entero: $100.000 × 0,03 = **$3.000,00** por mes calendario. Proporcional hasta 30/09 y mes entero en octubre da $2.000,00 y $3.000,00; la dirección inversa de la spec da $3.000,00 y $3.100,00. El mutante viejo da dos bloques en octubre, **$6.000,00**; en la dirección inversa su bloque 30/09-29/10 deja sólo 30/10-31/10, **$200,00**. Es coherente como mutación del algoritmo y de la cobertura anterior, no como cambio de divisor del proporcional.
- Migración 15/10: 16/10-31/10 son 16 días. $80.000 y $85.000 al 3% proporcional dan **$1.280,00/$1.360,00**; con mes entero dan **$2.400,00/$2.550,00**. Noviembre sobre $80.000 da otros **$2.400,00**. Capitalizar $4.000 importados daría **$2.520,00**, diferente. El mutante proporcional desde 11/08 hasta 31/10 suma 82 días, **$6.560,00**.
- Gracia cruzando septiembre: dos meses calendario pendientes dan **$6.000,00**. Pago parcial de $40.000: base inicial $100.000 da **$3.000,00** en septiembre y base $60.000 da **$1.800,00** en octubre.
- E19: 20 + 31 días al 3% dan **$5.100,00**. El mutante que exime septiembre da **$3.100,00**. Los mismos 51 días al 6% de E1/E4 dan **$10.200,00**.
- Firma: redistribuir capital $85.000/$20.000 a $84.000/$21.000 conserva $105.000; redistribuir interés $5.000/$0 a $4.000/$1.000 conserva $5.000. Un JSON canónico ilustrativo por filas con importes normalizados genera firmas diferentes; reordenar y escribir `85000.00` en vez de `85000` conserva la firma. Es demostración del criterio, no ejecución de la futura función de firma.
- CHECK: con `hasta >= desde`, exigir `desde > hasta - día(hasta)` restringe `desde` al mismo mes; exigir que `hasta + 1` sea día 1 exige fin de mes. 16/10-31/10 cumple ambas. 30/09-31/10 viola sólo la primera; 01/10-30/10 viola sólo la segunda. Se evaluaron fechas con Python, no la expresión SQL en PostgreSQL.

## Tabla de cierre

CERRADO significa resuelto en el plan, no comportamiento implementado o probado.

| Hallazgo | Estado | Evidencia concreta |
|---|---|---|
| PR-03 | CERRADO | `design.md:144-190,415`; `specs/saldo-inicial/spec.md:100-131`; `tasks.md:154-168,289-296`: inicio posterior a migración, meses calendario, $2.400 en octubre y noviembre y $2.550 sobre septiembre, con y sin interés importado. La continuidad general se define por intervalos, no por un máximo. E18 hace visible la decisión sobre la fracción |
| PR-07 | CERRADO | `design.md:254-290,301-317,418`; `specs/saldo-inicial/spec.md:38-63,150-167,212-242`; `tasks.md:270-313`: agrupación en 4c, vencimiento común, referencias múltiples y pérdida del aporte individual declarada; firma persistida para replay. Compatible con el único real de `0023:199-200` |
| PR-10 | CERRADO | `design.md:168-190,236-243,405,415`; `specs/intereses-por-mora/spec.md:116-168`; `tasks.md:154-170`: algoritmo, CHECK y ejemplos usan meses calendario; los montos y mutante de bloques cierran. No se reabre la decisión de Juani |
| PR-11 | CERRADO | `design.md:273-308`; `specs/saldo-inicial/spec.md:212-242`; `tasks.md:297-312`: firma `v1:` + SHA-256, JSON canónico, importes a dos decimales, orden por unidad y tupla completa de fila. Incluye edificio, migración, origen, modo y datos por fila; excluye operación, request, identidad y reloj. Hay mutantes para agrupar antes de firmar, no ordenar, no normalizar e ignorar interés por fila. El escenario $5.000/$0 frente a $4.000/$1.000 está contemplado como caso extra unitario en `tasks.md:311-312`, aunque no sea un escenario separado de la spec |
| PR-12 | CERRADO | `design.md:146-157,202-243,419`; `specs/intereses-por-mora/spec.md:86-114`; `tasks.md:119-129,171-196,226-239`: unión de intervalos de intereses que cuentan, hueco anterior recuperado, mutante máximo y test de dos tramos en foto. D3 conserva una sentencia mediante subselect correlacionado sobre el JSON existente de `lecturas.py:49-54`. No hace falta `obligacion_id` duplicado en tramo: lo aporta el movimiento y lo exige `0023:87-89`; la coherencia de tipo se declara responsabilidad de aplicación en D4 |

## Hallazgos nuevos

### PR-13 · La propiedad de cobertura exacta incluye días de base cero que no pueden persistirse como tramo

- **Fuente:** `tasks.md:184-196`, especialmente `:188-190`; `design.md:158-167,191-193,236`; `specs/intereses-por-mora/spec.md:38-41,62-65`.
- **Observación:** la propiedad nueva exige que, después de un corte que registra, la unión cubierta sea exactamente todo el intervalo desde el inicio natural al corte. Contraejemplo aritmético: obligación $100.000, vence 10/09, gracia 0, 3% proporcional, pago total con fecha valor 20/09. El interés positivo es $1.000 por 11/09-20/09; 21/09-30/09 tiene base cero. El CHECK `base > 0` impide persistir ese segundo tramo con su base real. Por lo tanto hay un corte que registra y cuya cobertura no puede ser el intervalo completo. Guardar el tramo positivo hasta 30/09 falsearía el detalle y el importe. E19 además declara que días sin importe pueden quedar descubiertos. Esto no invalida la solución por intervalos de PR-12, sí su propiedad universal de prueba.
- **Disposición: CORREGIR.** Acotar la propiedad a los días con base positiva que efectivamente corresponda registrar bajo la configuración del corte, conservando por separado la propiedad de no solapamiento y el caso fijo del hueco de $5.000. Agregar este pago total al generador o como caso discriminante. Se puede corregir el criterio del plan sin cambiar la decisión financiera ni ampliar código. No se presenta como falla runtime.

### PR-14 · Los negativos del CHECK no discriminan la restricción de un solo mes

- **Fuente:** `design.md:236-239`; matriz de `tasks.md:94`, frente a la exigencia de mutante por aserción de `tasks.md:31-34`.
- **Observación:** los negativos propuestos son 30/09-29/10 y 01/10-30/10. Ambos terminan antes del fin de mes. Si se elimina únicamente `desde > hasta - extract(day FROM hasta)::int`, ambos siguen rechazados por la condición de fin de mes. Esos dos ejemplos no prueban de manera discriminante la aserción distinta de que el tramo pertenece a un solo mes. La fórmula propuesta es coherente; la debilidad está en su criterio de prueba.
- **Disposición: CORREGIR.** Añadir 30/09-31/10, con `dias = 32` y demás campos válidos, y el mutante que quita sólo la restricción de mismo mes. Debe entrar con ese mutante y rechazarse con el CHECK completo. Conservar 01/10-30/10 para quitar sólo la condición de fin de mes. Es una precisión local de la matriz, sin decisión humana nueva.

## Evaluación de E18 y E19

**E18:** la pregunta está bien planteada: identifica la fracción 16/10-31/10, el importe, el riesgo del Excel y qué cambia si se elige otra opción (`design.md:420`). Cobrar $2.400 sin tramos anteriores a migrar cumple el corte de R09 y la convención de meses calendario ya decidida. No demuestra ausencia de duplicación económica si el importe importado ya incluía octubre completo: R09:344-346 busca evitarla y el plan la reconoce. El aviso del 5 y P58 son mitigaciones propuestas, no evidencia de que el Excel corte así. La aceptación de ese riesgo sigue siendo una elección explícita. D-113 fija cierre y redondeo; D-143 fija pertenencia a la obligación, no resuelve esa superposición. Nunca se capitalizan los $4.000 importados. No corresponde reabrir meses calendario ni inventar un bloqueante por no haber inspeccionado el Excel.

**E19:** pregunta explícita y numéricamente coherente con E4/E17: muestra que pasar de 0% a 3% puede cobrar días de septiembre al 3%, y ofrece eximirlos como alternativa con costo técnico (`design.md:421`). R03:196-197 protege los importes ya registrados; el plan no los modifica, ni capitaliza intereses. R03 no establece que tasa cero sea diferimiento, por lo que la propuesta debe aprobarse como decisión adicional, no como consecuencia obligatoria de R03 o como condonación ya definida. D-113 y D-143 tampoco la deciden. La descripción de R29 como propuesta no la vuelve disponible. PR-13 exige distinguir cobertura persistida de días sin base, pero no cuestiona el monto $5.100 del escenario E19.

### Correspondencia de “Para firmar”

`informes/propose-3-planner.md:86-113` y `design.md:403-421` contienen exactamente E1 a E19; E3 aparece desdoblada en E3.1/E3.2 en el informe y en dos partes dentro de E3 en diseño. No falta ni sobra una elección E. Coinciden las propuestas y la separación de ratificaciones E3.2/E6/E13. E9/E10/E12 figuran en ambos como alcance/contrato ratificado. PA-1 está separado y no se confunde con una E. No se señala la firma humana pendiente como hallazgo.

Como precisión informativa, `proposal.md:78-85` no enumera E4/E5/E8 al decir cuáles piden elección real, mientras diseño e informe sí las incluyen. La remisión a E1-E19 y el detalle para firma están presentes; es una omisión de resumen, no un impedimento adicional ni una decisión ausente.

## JUICIO

Autor: Codex, plan-reviewer, intento 3. Comparé el informe del planner con los artefactos actuales, los contratos reales citados del libro y R03/R09/D-113/D-143. Confianza alta en los cierres estáticos y los recálculos; alta en PR-13 como incompatibilidad entre propiedad universal y CHECK de base positiva, y en PR-14 como mutante tapado por otra condición. No se encontró un nuevo BLOQUEANTE de algoritmo o importe en el alcance pedido. Quedan dos correcciones locales de criterios de prueba antes de presentar el plan como terminado. La validación estructural pasa, pero no sustituye esas precisiones.

Las restricciones de montos sin float, NUMERIC(14,2), sólo agregar, interés simple, RLS forzada y comunicación por aplicación siguen explícitas en `tasks.md:28-35`, `design.md:191-196,218-243,379-393` y `proposal.md:119-121`. La firma y los intervalos no requieren editar el libro existente. No se reauditaron las defensas ya cerradas en intentos anteriores.

## SUPOSICIÓN

- No se ejecutaron suite, tests aislados, mutantes, build, Docker, PostgreSQL, migraciones ni EXPLAIN. Los futuros rojos son objetivos, no resultados observados. El SQL del CHECK sólo se evaluó algebraicamente con fechas.
- El JSON con SHA-256 del recálculo es ilustrativo del contrato por filas, no implementación ni verificación exhaustiva de todos sus campos. No se verificó rendimiento ni resistencia criptográfica experimental.
- No se consultó Excel real ni legislación externa; se contrastó el contrato de dominio suministrado, sin asesoramiento jurídico.
- No se recuperó Engram ni se actualizó memoria, Obsidian, tasks o LEEME por el límite de única escritura. No se compararon fechas de autor de toda la KB con el archivo histórico; no se autoriza reescribirla desde esta revisión.
- La sesión permite técnicamente escribir otras rutas: el límite a este informe se respetó operativamente, no se afirma un sandbox por archivo.
- No corresponde ejecutar un cuarto intento automáticamente. Este informe entrega el estado para que el humano decida el siguiente paso.

## Contaminación

Leí `propose-3-planner.md` y mis informes previos `propose-1-plan-reviewer.md` y `propose-2-plan-reviewer.md`. La revisión está deliberadamente guiada por sus hallazgos y correcciones; no es ciega ni independiente de esos antecedentes. Las fuentes de código y los recálculos usados como evidencia se verificaron directamente en esta sesión. No leí originales nuevos de otros revisores para buscar acuerdo.

## Veredicto

VUELVE AL PLANNER

- PR-13, CORREGIR: acotar la propiedad de cobertura para días con base cero.
- PR-14, CORREGIR: agregar el negativo y el mutante que discriminan la condición de un solo mes del CHECK.

Los cinco hallazgos anteriores revisados quedan CERRADOS en el plan. No hay nuevos BLOQUEANTES ni se reclama la firma humana en esta etapa. Al ser el intento 3, este veredicto no autoriza una cuarta ronda automática: la continuidad la decide el humano.
