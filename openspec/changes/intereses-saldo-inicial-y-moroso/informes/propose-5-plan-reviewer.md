# propose · intento 5 · plan-reviewer

- Rol: revisor del plan, intento 5, alcance acotado a PR-15 por instrucción humana expresa.
- Autor y ejecutor: Codex, sesión actual, proveedor OpenAI. Sin delegación; no se verificó un identificador de modelo.
- Fecha: 30/10/2026, Argentina (UTC-03:00).
- Revisión: árbol sin commit sobre `533a44027d16819fd774c404372b5e5dbd39917d`. Esta revisión no autoriza construcción ni reemplaza la firma humana CRITICAL.

## Fuentes leídas

Rutas relativas a `openspec/changes/intereses-saldo-inicial-y-moroso/`, salvo indicación:

- `informes/propose-4-plan-reviewer.md:1-111`, especialmente :80-91: estado previo de PR-13 y disposición de PR-15. Los cierres anteriores se tomaron como antecedentes, sin reabrirlos.
- `informes/propose-5-planner.md:1-40`: respuesta completa.
- `tasks.md:136-215`, especialmente :171-174 y :195-205: escenarios, mutantes y propiedades afectados.
- `specs/intereses-por-mora/spec.md:86-124,200-265`: contrato y escenarios, especialmente :251-264.
- `design.md:144-245`: cobertura, base, formas y CHECK. Se consultó además :1-143 y :246-479 como contexto del mismo documento, sin ampliar la revisión.
- `CLAUDE.md:1-377` y `obsidian.md:1-78`: reglas y contexto de inicio. La salida conjunta de contexto fue truncada; no se usa como evidencia financiera ni se afirma una lectura íntegra verificable de esas instrucciones por esa salida.
- Estado e instrucciones de OpenSpec consultados antes de leer los artefactos del cambio.

## EVIDENCIA

### Comandos y revisión identificada

Ejecutados desde la raíz del repositorio el 30/10/2026, alrededor de las 20:50 (UTC-03:00):

- `git status --short`: `?? openspec/changes/intereses-saldo-inicial-y-moroso/`.
- `openspec list --json`: cambio `in-progress`, 0/24 tareas completas.
- `openspec status --change intereses-saldo-inicial-y-moroso --json`: los cuatro artefactos de planificación figuran `done`. Esto describe artefactos, no implementación.
- `openspec instructions tasks --change intereses-saldo-inicial-y-moroso --json`: instrucciones del artefacto recuperadas.
- `openspec validate intereses-saldo-inicial-y-moroso --strict`, salida completa relevante, exit 0:

```text
Change 'intereses-saldo-inicial-y-moroso' is valid
```

- `python3` con `datetime.now().astimezone().isoformat()`: `2026-10-30T20:50:22.871577-03:00`, inmediatamente después de validar.
- `git rev-parse HEAD`: `533a44027d16819fd774c404372b5e5dbd39917d`.
- Lecturas numeradas con `python3`, `Path.read_text().splitlines()` y `enumerate(..., 1)`. El primer intento con `python` falló con `command not found`; se corrigió a `python3`.

SHA-256 de los documentos revisados, calculados a las 20:50:22:

```text
tasks.md a397d94824c6959456c6d98cd251d24f000e3fe1ad98804494e3bd952c885061
design.md 3c74fab1be8b5bba24dfc7a8b73bef1f30affd238144b1509745bdb9de2f62fb
specs/intereses-por-mora/spec.md ba6e18ab59c3004f75db9c16933b8bbbe57b0195d16fff32308a26a3d41faef5
informes/propose-4-plan-reviewer.md 6af29d512748fb75bf7ce56330b8003831522d09452624296bbd186ea2255027
informes/propose-5-planner.md baa3d3db5c91c251ad8017cdaa641ee929324998567fedc1cb84c3c4dbecd186
```

### Contraste estático de la corrección

1. La exclusión ahora depende explícitamente de la forma: sólo proporcional excluye días con base diaria cero; mes entero conserva el tramo mensual completo y usa la base de su primer día a cobrar, aunque un pago posterior deje la base diaria en cero (`tasks.md:195-205`). El escenario nuevo expresa exactamente esa distinción (`specs/intereses-por-mora/spec.md:258-264`). Coincide con la respuesta del planner (`informes/propose-5-planner.md:8-19`).
2. El caso mensual está asignado a 4.3 con importe y fechas. El mutante previsto aplica indebidamente la exclusión proporcional a mes entero: produciría 11/09-20/09 en lugar de 11/09-30/09, por lo que la aserción de fechas discrimina la regresión (`tasks.md:171-174`). Se confirma su especificación en el plan, no su ejecución ni un RED observado.
3. Se conserva el caso proporcional de $1.000,00, un solo tramo 11/09-20/09 y ninguno en 21/09-30/09, junto con el mutante de estirarlo hasta el corte (`tasks.md:140-149`; `specs/intereses-por-mora/spec.md:251-256`). También permanece como ejemplo fijo en la propiedad (`tasks.md:202-203`).
4. Se conserva la propiedad separada de no solapamiento entre intereses que cuentan (`tasks.md:193-194`), compatible con la responsabilidad del dominio indicada en `design.md:243-245`.
5. Se conserva el hueco de $5.000,00, con intervalos 11/09-30/09 y 01/11-30/11, y sus mutantes discriminantes (`tasks.md:176-188`; `specs/intereses-por-mora/spec.md:100-107`). El diseño conserva la unión de intervalos y rechaza usar el máximo de los finales (`design.md:146-154`).
6. No hay contradicción nueva con el diseño: mes entero toma la base del primer día a cobrar y termina el tramo en fin de mes (`design.md:168-174`), como el escenario corregido (`specs/intereses-por-mora/spec.md:260-264`). El CHECK exige base positiva del tramo, mismo mes y final de mes (`design.md:236-241`), no base diaria positiva en todos sus días. Para 11/09-30/09: 30/09 + 1 = 01/10, cuyo día es 1; 30/09 − 30 días = 31/08, y 11/09 > 31/08. La base del tramo es $100.000, positiva. Recortarlo al 20/09 incumpliría el final de mes. Es evaluación estática del contrato, sin ejecutar SQL.

### Recálculo manual y comprobación con Decimal

Los dígitos incompletos del encargo se resuelven con el caso completo de los documentos: capital $100.000,00 e interés mensual esperado $3.000,00 (`informes/propose-4-plan-reviewer.md:90-91`; `specs/intereses-por-mora/spec.md:260-264`).

Vence el 10/09; inicio natural 11/09 (`design.md:144-145`). El pago con fecha valor 20/09 baja la base diaria desde el 21/09 por la comparación estricta de fechas (`design.md:163-165`). Con gracia 0 y corte 30/09, septiembre cobra una mensualidad sobre la base del 11/09, $100.000, y guarda 11/09-30/09 (`design.md:161-174`; `specs/intereses-por-mora/spec.md:260-264`). No se multiplica por una fracción de días.

Cálculo a mano: 100.000 × 3 / 100 = 3.000; redondeado al centavo = **$3.000,00**. La reducción diaria posterior no altera la base inicial del tramo mensual.

Comprobación aritmética aislada ejecutada con `python3` a las 20:50:22, sin importar código del proyecto y sin float:

```python
from decimal import Decimal as D, ROUND_HALF_UP
(D('100000') * D('3') / D('100')).quantize(D('0.01'), rounding=ROUND_HALF_UP)
# 3000.00
(D('100000') * D('3') / D('100') / D('30') * D('10')).quantize(D('0.01'), rounding=ROUND_HALF_UP)
# 1000.00
(D('100000') * D('3') / D('100') / D('30') * (D('20') + D('30'))).quantize(D('0.01'), rounding=ROUND_HALF_UP)
# 5000.00
```

Los dos últimos cálculos corroboran los importes preservados del proporcional y del hueco (`specs/intereses-por-mora/spec.md:251-256,100-107`). Son aritmética del plan, no pruebas de comportamiento de una implementación.

## Cierre explícito de PR-13 y PR-15

- **PR-13: CERRADO.** Su cierre era parcial sólo por extender a mes entero la exclusión de días con base diaria cero (`informes/propose-4-plan-reviewer.md:82,89-91`). Esa extensión queda corregida en `tasks.md:195-205` y `specs/intereses-por-mora/spec.md:258-264`; se conservan el proporcional de $1.000,00 (`tasks.md:140-149,202-203`), no solapamiento (`tasks.md:193-194`) y el hueco de $5.000,00 (`tasks.md:176-188`).
- **PR-15: CERRADO.** La exclusión queda acotada al proporcional; mes entero conserva 11/09-30/09 sobre la base del primer día a cobrar, $100.000, con interés $3.000,00, ejemplo fijo y mutante específico por fechas (`tasks.md:171-174,195-205`; `specs/intereses-por-mora/spec.md:258-264`). Esto cumple la disposición anterior (`informes/propose-4-plan-reviewer.md:91`) y el contrato y CHECK existentes (`design.md:168-174,236-241`).

## Hallazgos nuevos

Ninguno dentro del alcance autorizado. No se reabrió PR-14 ni ningún otro hallazgo cerrado. La revisión de conservación contrasta los contratos actuales con los antecedentes indicados; no atribuye a un diff histórico no disponible una comprobación byte por byte.

## JUICIO

Autor: Codex, plan-reviewer, intento 5. Comparé la disposición de PR-15 y el cierre parcial de PR-13 con la respuesta del planner y los criterios actuales de tareas, spec y diseño citados arriba. Confianza alta para este alcance estático: el caso discriminante está definido, el mutante previsto distingue el error por fechas y el cálculo Decimal es coherente. La validación estructural pasa. El veredicto habilita pasar a firma en este alcance; no declara implementación verificada ni revisa de nuevo el resto del plan.

## SUPOSICIÓN

- No ejecuté suite de tests, build, PostgreSQL, migraciones ni mutantes. No hay RED/GREEN observado ni comportamiento de producción probado en esta revisión.
- La aplicación real del CHECK y la capacidad del test futuro de matar el mutante quedan pendientes de construcción y verificación. La comprobación del CHECK aquí es sólo algebraica y supone los demás campos válidos.
- No se auditó el resto del cambio ni las firmas humanas. No se recuperó Engram ni se revisó deriva histórica de la KB: alcance acotado a PR-15 y fuentes locales suficientes para ese juicio.
- La atribución del planner a Claude Opus 5.5 es su declaración (`informes/propose-5-planner.md:3`), no una identidad verificada por esta sesión.
- No faltó ninguna de las fuentes requeridas. No se editó Obsidian, tasks, LEEME ni otro artefacto: la autorización permite escribir sólo este informe. El límite se respetó operativamente; no se afirma un sandbox exclusivo por archivo.

## Contaminación por otros informes

Leí el informe completo `informes/propose-4-plan-reviewer.md:1-111`, además de su sección requerida :80-91, y `informes/propose-5-planner.md:1-40`. No leí directamente otros informes. El informe del intento 4 incluye referencias y conclusiones de intentos anteriores (`informes/propose-4-plan-reviewer.md:12-16,80-83`): esa exposición es contexto histórico indirecto y no verificación independiente de aquellos intentos. El juicio presente está guiado por PR-15, con lectura directa de los artefactos y recálculo propio.

## Veredicto

PLAN LISTO PARA FIRMA
