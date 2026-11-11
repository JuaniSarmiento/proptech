# propose · intento 4 · plan-reviewer

- Rol: revisor del plan, intento 4 ACOTADO a PR-13 y PR-14, autorizado expresamente por el humano.
- Ejecutor y autor: Codex, sesión actual, proveedor OpenAI. No se usó un subagente ni se verificó un identificador de modelo. El rótulo `codex:codex-rescue` de tasks.md no constituye evidencia de un transporte usado en esta sesión.
- Fecha: 30/10/2026, Argentina (UTC-03:00).
- Revisión: árbol sin commit sobre `533a44027d16819fd774c404372b5e5dbd39917d`; change sin seguimiento. Revisión estática, sin construcción.

## Fuentes

Rutas relativas a este change, salvo indicación:

- `informes/propose-3-plan-reviewer.md:59-69`: hallazgos originales. Su cierre previo y las secciones posteriores se leyeron como contexto, sin reabrirlos.
- `informes/propose-4-planner.md:1-62`: respuesta completa del planner.
- `tasks.md:1-35,85-105,136-155,170-201,231-236`: autorización, correcciones, propiedades y conservación del hueco.
- `design.md:144-195,216-245`: base diaria, cobertura, formas y CHECK.
- `specs/intereses-por-mora/spec.md:1-336`: contraste del contrato de interés, especialmente :38-41, :86-114, :118-146 y :238-256.
- `CLAUDE.md` y `obsidian.md`: instrucciones y contexto de inicio. KB real declarada: `knowledge-base/`; no se reabrió su contenido ni su mapa histórico en este intento acotado.
- Estado e instrucciones del CLI OpenSpec consultados antes de revisar los artefactos.

## EVIDENCIA

### Estado y validación

Ejecutados en esta sesión, revisión indicada arriba:

- `git status --short`: `?? openspec/changes/intereses-saldo-inicial-y-moroso/`.
- `openspec list --json`: change `in-progress`, 0/24 tareas completas.
- `openspec status --change intereses-saldo-inicial-y-moroso --json`: proposal, specs, design y tasks `done`. Es estado de artefactos, no implementación aprobada.
- `openspec instructions proposal --change intereses-saldo-inicial-y-moroso --json`: contrato recuperado del CLI.
- `openspec validate intereses-saldo-inicial-y-moroso --strict`: salida `Change 'intereses-saldo-inicial-y-moroso' is valid`, exit 0. Hora registrada inmediatamente después: **2026-10-30T20:45:05-03:00**.
- `git rev-parse HEAD`: `533a44027d16819fd774c404372b5e5dbd39917d`.

La lectura numerada se ejecutó con `python3`, `Path.read_text().splitlines()` y `enumerate(..., 1)`. Un intento previo con `python` terminó en `command not found`; no se presenta como chequeo exitoso.

### Recálculos independientes

Ejecutado con `python3` a **2026-10-30T20:45:16-03:00**, importando `Decimal`, `ROUND_HALF_UP`, `date` y `timedelta`. Expresiones y salida relevante:

```python
D = Decimal
(D('100000') * D('3') / D('100') / D('30') * D('10')).quantize(D('.01'), rounding=ROUND_HALF_UP)
# 1000.00
(D('100000') * D('3') / D('100') / D('30') * D('50')).quantize(D('.01'))
# 5000.00
D('100000') * D('3') / D('100')
# 3000
```

El pago con fecha valor 20/09 baja la base desde el 21/09 (`design.md:163-165`): 11/09 a 20/09 son diez días inclusivos. El caso proporcional nuevo de `specs/intereses-por-mora/spec.md:251-256` y `tasks.md:140-149` es correcto: $1.000,00 y un solo tramo 11/09-20/09. El mutante de estirarlo al 30/09 tiene una aserción de fechas explícita.

Para cada par `(desde, hasta)` se evaluó:

```python
dias = (hasta - desde).days + 1
fin_mes = (hasta + timedelta(days=1)).day == 1
mismo_mes = desde > hasta - timedelta(days=hasta.day)
```

| Fechas de 2026 | días | fin de mes | mismo mes | CHECK completo | sin mismo mes | sin fin de mes |
|---|---:|---|---|---|---|---|
| 30/09 a 31/10 | 32 | verdadero | falso | rechaza | admite | rechaza |
| 01/10 a 30/10 | 30 | falso | verdadero | rechaza | rechaza | admite |

Esto verifica algebraicamente los negativos de `tasks.md:94` y `design.md:239-241`, con los demás campos válidos. No es ejecución SQL ni ejecución de mutantes.

El hueco conserva $5.000,00 y dos intervalos de 20 + 30 días (`tasks.md:173-184`; spec :100-107). La propiedad de no solapamiento sigue separada (`tasks.md:190-191`; diseño :243-245).

### Identificación del contenido revisado

SHA-256 calculados en la misma lectura de las 20:45:16:

```text
tasks.md 6dff41391a7da109b13ff14d6950dfe137fe032d8b1df93cf9c822a4fe4ffa8f
design.md 3c74fab1be8b5bba24dfc7a8b73bef1f30affd238144b1509745bdb9de2f62fb
specs/intereses-por-mora/spec.md 5749c6cd6addf7c441c58ec3fd176b3f34c73fd79493413b18e8a258d5bc7bf0
informes/propose-4-planner.md 73d258c7024572a84f4b488112f9ab71ac1fdd6e7b31fcc4fbc49c7eb0aae41c
informes/propose-3-plan-reviewer.md 1b05ea314292c2399932ce16e84616a6431a9d6c40f4856aaf96254505063fc6
```

## Cierre de PR-13 y PR-14

- **PR-13: PARCIAL.** El caso proporcional, su ejemplo fijo y su mutante están incorporados correctamente. La cobertura ahora depende de los tramos que asigna el oráculo y conserva no solapamiento y hueco. Sin embargo, la frase nueva de `tasks.md:194` excluye universalmente días con base diaria cero, también cuando el generador usa mes entero. Introduce la contradicción local detallada abajo.
- **PR-14: CERRADO.** Los dos negativos aíslan cada condición y el plan exige quitar sólo la defensa correspondiente. No aparece contradicción nueva en esta corrección.

## Hallazgo nuevo introducido por la corrección

### PR-15 · La exclusión universal de días con base cero contradice el tramo de mes entero

- **Fuente:** frase nueva `tasks.md:194-197`, frente a `design.md:163-174,236-241` y `specs/intereses-por-mora/spec.md:118-121`.
- **Observación:** la primera parte de la propiedad habla de días asignados por el oráculo a un tramo con base positiva, pero agrega sin distinguir forma: “los días que caen en base cero quedan sin cubrir y no aparecen en ningún tramo”. El generador incluye mes entero y pagos totales. Tomando el mismo pago total del ejemplo nuevo y cambiando únicamente la forma a mes entero: vence 10/09, $100.000 al 3%, gracia 0, pago total con fecha valor 20/09, corte 30/09. La base diaria es cero desde el 21/09, pero el diseño cobra $3.000,00 sobre la base del primer día a cobrar (11/09), con tramo 11/09-30/09 y base de tramo positiva. Excluir 21/09-30/09 exigiría terminarlo el 20/09, contradiciendo el diseño y el CHECK de fin de mes. La corrección volvió a confundir base diaria y base de tramo para esta forma. Es una contradicción estática del criterio nuevo, no una falla runtime ni reapertura de la decisión de meses calendario.
- **Disposición: CORREGIR.** Acotar la exclusión de días con base diaria cero al proporcional. En mes entero, definir la cobertura con el tramo mensual y la base de su primer día a cobrar según el contrato existente, aunque después haya un pago total. Mantener el ejemplo proporcional de $1.000,00, no solapamiento y hueco de $5.000,00. Agregar este caso discriminante al criterio del generador para evitar ambas lecturas. No requiere otra decisión financiera.

## JUICIO

Autor: Codex, plan-reviewer, intento 4. Confianza alta en los recálculos y en el cierre de PR-14. PR-13 mejora el criterio proporcional pero deja una contradicción textual nueva al extender la exclusión a mes entero. La validación estructural pasa; no resuelve esta incompatibilidad. No se revisaron nuevamente los hallazgos ya CERRADOS ni las elecciones pendientes de firma. Este informe no autoriza construcción ni un quinto intento automático.

## SUPOSICIÓN

- No se ejecutaron suite, build, tests, PostgreSQL, migraciones ni mutantes. No se afirma comportamiento probado de código inexistente.
- El análisis del CHECK supone campos restantes válidos y evalúa su fórmula con fechas; la prueba real queda para construcción.
- No se recuperó Engram ni se modificó Obsidian, tasks o LEEME: esta sesión está limitada a escribir únicamente este informe. No se compararon fechas de autor de documentos de KB con archivos históricos.
- La atribución del planner a Claude Opus 5.5 proviene de su informe, no fue verificada por este ejecutor.
- El límite de escritura por archivo se respetó operativamente; no se afirma aislamiento técnico exclusivo para esta ruta.

## Contaminación

Revisión deliberadamente guiada por PR-13, PR-14 y la respuesta del planner del intento 4. Se leyeron directamente los artefactos y se recalcularon importes y fechas, sin tomar el resultado declarado por el planner como prueba. No se consultaron conclusiones de otros revisores para fabricar acuerdo.

## Veredicto

VUELVE AL PLANNER
