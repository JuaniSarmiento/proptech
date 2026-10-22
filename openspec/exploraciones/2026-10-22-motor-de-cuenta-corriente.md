# Exploración: motor de cuenta corriente (cambio 4, C-07)

> Explore mode. No se escribió código, no se tocó `knowledge-base/`, no se corrió `openspec new` ni
> se creó el change. Lo que sigue son hallazgos y recomendaciones para que decidan Juani y Alberto;
> nada acá es una decisión tomada. El cambio es **CRITICAL** (D-094): cada propose que salga de acá
> necesita la aprobación escrita y fechada de uno de los dos socios antes de escribir código, y
> esta exploración no la reemplaza.

**Fecha**: 22/10/2026 · **HEAD al cerrar**: `79037b5`
**Disparador**: `CHANGES.md` [C-07], el próximo del camino crítico a M1. La auditoría de cimientos
(`2026-10-22-cimientos-antes-del-4.md`) dejó doce decisiones de diseño que el propose del 4 tiene
que traer resueltas, y D-109 respondió cinco de las seis preguntas de negocio.

**Roles convocados** (de a uno, con prompts independientes; ninguno vio el informe del otro):

| rol | informe textual | qué miró |
|---|---|---|
| analista funcional (`role-analyst`, opus) | `.git/informes-explore-4/01-analista.md` | reglas, D-109, modelo, ficha; 34 requisitos y 18 huecos |
| arquitecto (`role-architect`, opus) | `.git/informes-explore-4/02-arquitecto.md` | código de `compartido`, `acceso`, `complejos`, migraciones, tests de fronteras y de dueño; 14 decisiones |

**No convocados** (JUICIO del orquestador, confianza alta): backend, DBA, DevOps, QA y frontend.
En explore el método del repo convoca sólo analista y arquitecto; los cinco ya auditaron estos
mismos cimientos hoy (informes 02 a 06 de `.git/informes-cimientos/`) y sus hallazgos están
incorporados abajo con su id. QA y los especialistas de capa entran en el propose y en el verify.
**Tampoco se convocó al senior**: no estaba pedido en este encargo; queda dicho para que su
silencio no se lea como aprobación.

**Fuentes leídas por el orquestador**: `CLAUDE.md`, `CHANGES.md` §C-07 a C-10,
`12_fichas_de_changes.md` §4 a §8, `05_reglas_de_negocio.md` (dominio cuenta corriente, R11, R13,
R17, R18, R20, R21, R29, R31, R32, R39, R41), `04_modelo_de_datos.md`, `06` §HU-A9, `08`,
`09` (D-010 a D-016, D-021, D-024, D-040, D-046, D-068, D-073, D-074, D-079 a D-089, D-109, SU-02),
`10` (P24 a P42), `15` (L-034 a L-037), `openspec/config.yaml`, la exploración de cimientos y los
nueve informes, y el código: `compartido/dinero.py`, `idempotencia.py`, `roles.py` (encabezado,
`despues()`), `acceso/dominio/permisos.py`, `acceso/aplicacion/auditoria.py`,
`migraciones/ayudas_rls.py`, `0009`, `tests/unitarios/test_fronteras_de_modulos.py`,
`tests/integracion/test_dueno_de_tablas_solo_agregar.py`.

---

## 1. Qué es el cambio, en castellano llano

Es el lugar donde vive la deuda de cada unidad. Hoy el sistema sabe qué edificios hay, qué unidades
tienen y cuánto paga cada una de cada gasto (coeficientes); no sabe cuánto debe nadie. El cambio 4
construye **el libro**: una lista de movimientos que sólo crece (nunca se edita ni se borra), de la
que sale todo lo demás. Cuánto debe una unidad, si está en mora, cuánto interés corresponde, a qué
deuda se aplica un pago: todo se **calcula** desde el libro, nunca se guarda como un número suelto
que alguien pueda pisar.

```
                    ┌────────────────────────────────────────────┐
  7 emite  ───────► │  emision ─┬─► obligacion (unidad, período, │
  (después)         │           │     ordinaria/extraordinaria)  │
                    │           └─► movimiento (interés, ...)    │
  8 confirma pago ► │  movimiento (crédito) ─► imputacion (R04)  │ ──► saldo, residual,
  (después)         │  corrección HU-A9 (R08), saldo inicial R09 │     moroso crítico (R20),
  5 importa ──────► │                                            │     deuda a una fecha
                    │  cuenta = unidad  o  persona (D-109.2)     │
                    └────────────────────────────────────────────┘
                     sólo agregar · RLS por administración · FOR UPDATE por cuenta
```

Lo que el 4 entrega son **piezas que otros llaman**: el 7 registra la emisión con ellas, el 8
imputa pagos, el 5 carga saldos iniciales, el 10 pregunta quién es moroso crítico. Por eso casi
todos sus tests arman a mano la emisión, el pago o la anulación (D-079), y los changes posteriores
los repiten con lo real.

## 2. Alcance

**Entra** (ficha §4 y D-109): libro de sólo agregar sin campo saldo; obligaciones, imputaciones y
créditos que no son pagos con su destino fijo (R05, D-086); orden de imputación (R04, R13); saldo
arrastrado (R06); reparto por mayor resto como función pública (R07); correcciones con
contra-asiento (R08, HU-A9); caso de uso de saldo inicial (R09, sólo la parte del libro); intereses
simples calculados y registrados (R03); función pura de moroso crítico (R20, con P31 de D-109);
umbral de saldos chicos (R30, que D-109 volvió vigente, sólo en su efecto sobre R20); contrato
mínimo de emisión (D-086); bloqueo de la cuenta ante pagos simultáneos; cuenta de persona (D-109.2);
la deuda técnica del 1b que la ficha le asigna (D-053).

**No entra**:

| qué | dónde va | por qué |
|---|---|---|
| Cálculo de la liquidación, preliquidación, controles, PDF, distribución | 7 | El 4 sólo registra lo que el 7 decide emitir |
| Gastos, cargos particulares, notas de crédito | 6 | Usan el reparto del 4, no escriben en el libro (SUPUESTO S-04 del arquitecto) |
| Motor de reglas | 6b | D-080: intereses son menú, no regla del motor; ninguna regla vigente pasa por el motor (D-089) |
| Pagos informados, confirmación, reversión, ajuste de R11 | 8 | El 4 expone `imputar`; el pago real nace en el 8 |
| Borrador del importador, comparación por unidad, cierre | 5 | El 4 sólo trae el caso de uso que el 5 llama al confirmar |
| Libre deuda | 10b | Usa la deuda a una fecha que expone el 4 |
| Aviso de mora y el "no dispara aviso" de R30 | 13 | |
| Prorrateo por días del mes de la venta (R32) | 7 o un 4d posterior | Necesita el cálculo de la liquidación: dependencia hacia adelante (analista H-01) |
| Outbox, barredor, alerta de `tarea_agotada` | 7 y 15 | El 4 no encola nada (arquitecto A-10) |

## 3. Modelo de datos propuesto

Todo bajo la convención B2: `administracion_id NOT NULL` con RLS forzada
(`aislar_por_administracion`), `complejo_id` con FK compuesta, permisos de la app reducidos a
`SELECT, INSERT`, triggers que rechazan `UPDATE`, `DELETE` y `TRUNCATE` para cualquier rol, y dueño
el rol de arranque (decisión 1). Nombres tentativos; el design los fija.

| tabla | qué es | clave natural (idempotencia) | índices | nota |
|---|---|---|---|---|
| `cuenta` | a quién se le debe: una unidad **o** una persona | único parcial `(administracion_id, unidad_id)` y `(administracion_id, persona_id)` | PK, los dos parciales | `CHECK num_nonnulls(unidad_id, persona_id) = 1`; es la fila que se bloquea (A-11, A-12) |
| `emision` | contrato mínimo de D-086: id, edificio, período | `(administracion_id, complejo_id, periodo)` único **entre las no anuladas** (ver riesgo R-4) | PK, `(administracion_id, complejo_id, periodo)` | sin columna de estado: "emitida" = la fila existe; el 7 crea su `liquidacion` con el **mismo id** (A-03) |
| `evento_de_emision` | eventos de sólo agregar de la emisión; en el 4, sólo `anulada` con motivo y responsable | `(administracion_id, emision_id, tipo)` | `(administracion_id, emision_id)` | el 7 decide cuándo se puede anular (R17); el 4 sólo lo registra |
| `obligacion` | lo que una cuenta debe de un período, capital desglosado en ordinario y extraordinario (R13) | `(administracion_id, emision_id, cuenta_id, concepto)`; saldo inicial: `operacion_id` | `(administracion_id, cuenta_id, vencimiento)` | `emision_id` **opcional**: el saldo inicial no nace de una emisión (analista H-03) |
| `movimiento` | todo débito o crédito: interés, pago, corrección, condonación, ajuste, bonificación, traslado | interés: `(administracion_id, obligacion_id, corte)`; operaciones del usuario: `operacion_id` | `(administracion_id, cuenta_id, fecha_valor)` | dos fechas (registro y valor); `corrige_a` / `enlazado_a` hacia otro movimiento; motivo y responsable obligatorios en correcciones |
| `imputacion` | qué parte de un crédito bajó qué parte de qué obligación (R05) | `(administracion_id, movimiento_id, obligacion_id, componente)` | `(administracion_id, obligacion_id)` | el residual = importe − Σ imputaciones; **ninguna columna "pagada" ni "saldo"** (RQ-20) |

Montos `NUMERIC(14,2)` con `Dinero`; la base no calcula. Sin particionar (DBA-6: ~3 M filas por
año con 1000 edificios). La exclusión de emisiones anuladas es un join indexado dentro de estas
tablas (`evento_de_emision`), nunca contra tablas del 7.

**Columnas nuevas en `configuracion_versionada`** que el 4 necesita: umbral de R30 ($500 por
default, D-109.3) y, si Juani lo elige así en la pregunta P-3 de la sección 9, el día de cierre del
período. El umbral de R23 conviene sumarlo en la misma migración aunque lo consuma el 6 o el 14:
después de la decisión 1 esa tabla deja de ser del migrador y cada `ALTER` posterior cuesta el
mecanismo de préstamo de A-07 (JUICIO del orquestador, confianza media).

## 4. Las doce decisiones de diseño

Cada fila del cuadro de cimientos, con la recomendación. Detalle completo de las opciones en el
informe del arquitecto (A-xx). Todo lo que sigue es **JUICIO**; lo marcado EVIDENCIA lleva su fuente.

### 4.1 Dueño de las tablas de sólo agregar (DBA-1) · A-07, A-08

- **Recomendación**: (a) el rol de arranque es dueño de `auditoria` **y** de todo
  `_TABLAS_DE_SOLO_AGREGAR`, que suma `configuracion_versionada` y las seis tablas del libro.
  `_TABLA_EXCLUIDA_DE_LA_REASIGNACION` pasa a ser un conjunto. Un chequeo de arranque nuevo en
  `base_de_datos.py` (junto al de superusuario/BYPASSRLS, `:252`) hace que la API no arranque si
  alguna de esas tablas quedó con dueño el migrador. El `xfail(strict=True)` de
  `configuracion_versionada` **se borra**: con la tabla protegida daría XPASS y rojo.
- **Trampa que hay que evitar** (A-08): la sonda de `despues()` hoy **ejecuta** `TRUNCATE` y exige
  el SQLSTATE del trigger; en tablas con FK entrante (`obligacion → emision`, `imputacion →
  movimiento`, todo → `cuenta`) PostgreSQL contesta antes con `0A000` (deuda D-2 del 2a,
  `12_fichas:957`). Copiarla frena cada arranque; aflojarla la deja ciega. Para esas tablas, el
  trigger de `TRUNCATE` se verifica por catálogo (`pg_trigger`) y sólo se ejecutan `UPDATE` y
  `DELETE`.
- **Migraciones futuras** que necesiten `ALTER TABLE` sobre esas tablas: fallan ruidosas
  (`must be owner`). La salida queda escrita como decisión y se construye cuando haga falta: la
  migración declara qué tablas protegidas toca, `antes()` le presta la propiedad sólo de ésas y sólo
  si esa migración está pendiente, `despues()` la devuelve y verifica.
- **Rechazadas**: (b) migrador dueño (una migración podría `NO FORCE` y reescribir el libro); (c)
  rol de propiedad aparte (equivale a (a) o a (b) según tenga membresía); préstamo general en cada
  `antes()` (anula la protección justo mientras corre código de migración).
- **Costo de revertir**: `roles.py` y el chequeo de arranque, un deploy; sin migración de datos.
- **Salvedad honesta** (EVIDENCIA, `infra/compose.yaml:83-85`): el servicio de migraciones ya tiene
  la credencial del rol de arranque. (a) protege contra un archivo de migración o la credencial del
  migrador sola, no contra quien controle ese contenedor.

### 4.2 Dueño de `emision` (ARQ-1) · A-03

- **Recomendación**: `cuenta_corriente` es dueño de `emision` y de `evento_de_emision`; el 7 crea su
  propia `liquidacion` (borrador, preliquidación, controles, distribuida) con **el mismo id** y
  llama al libro para emitir y anular. Dirección única `liquidacion → cuenta_corriente`.
- **Nombre**: "emisión" para la tabla del libro (D-086 y `11_glosario.md:70` ya la llaman así);
  "liquidación" para el documento del 7. Hay que reescribir `04_modelo_de_datos.md`, que hoy dice
  `liquidacion · planificada (cambio 4, contrato mínimo)`, y registrar una decisión nueva que ajuste
  D-086 ("el 7 la completa" deja de ser literal: el 7 crea la suya).
- **Rechazadas**: `liquidacion` entera en el libro (el 7 agregaría columnas a una tabla ajena,
  D-021); `liquidacion` dueña y el libro la lee por un puerto (el 4 construye un pedazo del 7, el
  saldo pasa por un puerto y la dependencia en ejecución queda circular).
- **Costo de revertir después del 7**: con ids iguales, sólo DDL (reapuntar la FK con
  `NOT VALID` + `VALIDATE`, sin reescribir filas). Sin ids iguales sería reescribir la FK de cada
  movimiento de un libro que no admite `UPDATE`: por eso el mismo id es la parte innegociable.
- **Test que la vigila**: `cuenta_corriente` no importa `liquidacion`; sin ciclos; escaneo de
  nombres de tabla en literales SQL (el código de `liquidacion` no puede nombrar tablas del libro).
  Ese escaneo da rojo hoy en `complejos/escritura.py:59` (decidido en el 2.2a, ARQ-3) y
  `lectura.py:144` (JOIN a `persona`, **sin decisión**: excepción con motivo o aceptarlo por
  escrito).

### 4.3 Reglas nuevas del test de fronteras (ARQ-2) · A-04

- **Recomendación**: (a) sin ciclos entre módulos, en todas las capas; (b) entre módulos sólo
  `aplicacion`, con excepciones por **submódulo destino** y motivo escrito:
  `acceso.dominio.identidad` y `acceso.dominio.permisos` (`Identidad` y `Accion` viajan en todo
  caso de uso auditado); `proptech_api` y `proptech_worker` fuera, por ser la raíz de composición;
  (c) `dominio/` sólo importa de `compartido` una **lista permitida** (`dinero`, `coeficientes`,
  `porcentaje`, `superficie`, `texto`, `tipos_de_unidad`, `reparto`), con `parametros` como
  excepción con motivo (EVIDENCIA del arquitecto: `complejos/dominio/configuracion.py:11` la importa
  hoy).
- **Rechazadas**: lista de prohibidos (falla abierta ante un módulo nuevo de infraestructura);
  relajar (b) a "no importar `adaptadores`"; mover `Identidad` y `Accion` a `compartido`.
- **Criterio de terminado**: un mutante por regla sobre una copia temporal da rojo en la aserción
  de esa regla (L-013, L-034).

### 4.4 Idempotencia de punta a punta (BKS-1, FE-2, DBA-6, OPS-9) · A-09

- **Recomendación**: la garantía vive **en el libro**, con restricciones únicas con prefijo
  `administracion_id` (las de la tabla de la sección 3). Para operaciones del usuario sin clave
  natural (corrección HU-A9, saldo inicial), el que llama manda un `operacion_id` UUID generado al
  mostrar el formulario, único en el libro y bajo RLS. Un `Idempotency-Key` HTTP aparte no hace
  falta si cada escritura del 4 lleva su `operacion_id`. El botón deshabilitado con "Guardando…"
  aplica cuando haya pantalla (ver 4.7).
- **Rechazadas**: reusar `trabajos_hechos` (EVIDENCIA, `04_modelo_de_datos.md:153`: PK global, sin
  tenant; DBA-6: la app puede borrar filas); `Idempotency-Key` como única defensa (dos pestañas o
  una server action que regenera la clave duplican igual).
- **Costo de revertir**: asimétrico. Sacar un índice único es trivial; **agregarlo después** sobre
  un libro con duplicados es imposible, porque no se pueden borrar filas. Por eso va desde la
  primera migración.

### 4.5 Redondeo y precisión del reparto (DBA-4, QA-4, P10, P42) · A-02 + analista H-07, H-08

- **Recomendación**: `compartido/reparto.py` (lo usan el 4, el 6 y el 7; en `cuenta_corriente`
  crearía `gastos → cuenta_corriente` por una sola función), junto con la aritmética mínima que
  `Dinero` no tiene a propósito (`dinero.py:3-5`). Dos pasos distintos, nunca mezclados en el mismo:
  - **Reparto** (R07): cada parte exacta se **trunca** al centavo y los centavos que faltan van, de
    a uno, a las mayores fracciones descartadas (mayor resto). Así la suma da exacta siempre.
  - **Montos sueltos** (interés): precisión completa y **medio hacia arriba** (`ROUND_HALF_UP`)
    una sola vez, al registrarse (D-109.1).
  - **Desempate**: R07 dice "identificador", D-109 dice "menor número de unidad", e `identificador`
    es texto ("10A" antes que "2B" en orden de texto). Recomendación provisoria: orden natural del
    identificador y el UUID como último desempate, pendiente de la pregunta a Alberto (sección 9).
  - **Pruebas**: `hypothesis` (hoy no está en el proyecto) con un oráculo que **no reusa** la fórmula
    de producción (por ejemplo, aritmética con `fractions.Fraction`): la suma da exacta al centavo,
    ninguna parte se aleja más de un centavo de su parte exacta, los empates son deterministas.
- **Rechazada**: medio hacia arriba por parte en el reparto (la suma puede pasarse del total);
  oráculo que recalcula con la misma fórmula (QA-4: un error de fórmula compartido no lo ve nadie).
- **SUPUESTO** (analista y orquestador): que "medio hacia arriba" de D-109 aplica a montos sueltos y
  no al reparto. Ninguna decisión lo escribe; es la única lectura en la que R07 y D-109 no se
  contradicen, y la tiene que confirmar Juani.

### 4.6 Commit y encolar con outbox (BKS-2, OPS-9) · A-10

- **Recomendación**: el 4 **no** construye outbox, porque no encola nada (no hay PDF, email ni
  trabajo programado: R03 registra el interés al emitir, así que no hace falta cron; analista H-17).
  Lo que sí trae: todo caso de uso de `cuenta_corriente.aplicacion` recibe la `Session` del que
  llama, exige estar en transacción y **nunca** hace commit ni encola. Eso deja al 7 escribir su
  fila de outbox en la misma transacción de la emisión. Estado por emisión, barredor y alerta de
  `tarea_agotada`: 7 (con F2c) y 15 (OPS-3).
- **Rechazada**: construir el outbox en el 4 sin un productor real que lo ejercite.
- **Criterio de terminado en el 4**: un test de fronteras que impide que `cuenta_corriente` importe
  `compartido.cola`.

### 4.7 Errores de campo y `pesos()` (FE-1, FE-3)

- **Recomendación del orquestador** (JUICIO, confianza media): el 4 **sin pantallas**. La única
  historia del 4 es HU-A9 (corrección), que necesita una ruta de API con su permiso (RQ-23, RQ-24),
  no necesariamente una pantalla. Si es así, FE-1 y FE-3 siguen siendo precondición, pero de la
  **primera pantalla con plata**, que el propose de ese change trae resuelta (función única
  `pesos()`, su parser de entrada `"1.234,50" → "1234.50"`, campos enlazados por id y
  `aria-invalid`, botón deshabilitado).
- **Alternativa**: que el 4 traiga la pantalla de corrección; entonces `pesos()` y el parser van en
  su primera tarea de web, antes de la pantalla. Es la pregunta P-6 de la sección 9.

### 4.8 Contrato de error uniforme (BKS-3)

- **Recomendación**: un único esquema de error (`{"detail": {"tipo", "campo"?, "detalle"?}}` o el
  que el design fije) definido una vez en `proptech_api`, y **toda ruta nueva del 4** declara
  `responses=` con 401, 403, 404, 409 y 422 en esa forma; el OpenAPI generado lo refleja y un test
  lo compara. Las rutas viejas no se retocan en el 4 (se uniforman cuando se toquen).
- **Rechazada**: uniformar todas las rutas existentes dentro del 4 (agranda un change CRITICAL con
  trabajo que no es de plata).

### 4.9 Puertos y adaptadores del libro (ARQ-4) · A-05

- **Recomendación**: **sin puerto de repositorio**. Reglas puras en `dominio/`, probadas sin base;
  persistencia con SQL sobre la `Session` en `aplicacion/`, igual que `complejos`. La garantía del
  libro vive en PostgreSQL (triggers, RLS, `FOR UPDATE`, claves únicas): un doble en memoria daría
  verdes que la base real rechaza. Se registra como decisión nueva que **acota D-040**: `puertos.py`
  y `adaptadores/` cuando hay un sistema externo o un reemplazo real (Clerk, cola, motor de reglas),
  no para la propia base. Regulariza de paso a `complejos`.
- **Rechazada**: lo literal de D-040 (`Protocol` de repositorio, adaptador SQL, doble en memoria).
- **Costo de revertir**: refactor mecánico, sin migración.
- **Ojo**: contradice el texto de D-040, así que **la firma un socio**; no es una elección del
  constructor.

### 4.10 Auditoría del coeficiente (BKS-5, D-016)

- **Recomendación del orquestador** (JUICIO, confianza media): auditarlas, en el primer
  sub-change. El coeficiente decide cuánto paga cada unidad de cada gasto, y desde el 4 eso termina
  en deuda: "nadie sabe quién lo cambió" deja de ser una incomodidad y pasa a ser un reclamo de un
  vecino sin respuesta. Costo: una migración que suma cinco acciones a `accion_de_auditoria`
  (`editar_unidad`, `editar_grupo`, `fijar_unidades`, `editar_categoria`, `reordenar_categorias`) y
  pasar la `Identidad` por esos cinco casos de uso.
- **Alternativa**: una decisión escrita que diga que D-016 no las alcanza, con el porqué. Es
  barata hoy y cara de sostener cuando el primer vecino pregunte.

### 4.11 Contrato de la API falsa para formularios nuevos (seguimiento de QA-1, L-027)

- **Recomendación**: aplica a cada **formulario web nuevo**. Si el 4 sale sin pantallas (4.7), no
  hay caso que agregar en el 4; la obligación viaja con la primera pantalla de plata y su propose la
  hereda por escrito. Si el 4 trae la pantalla de corrección, su ruta tiene su caso en
  `web/e2e/api-falsa.ts` que rechaza lo que la API real rechaza (422/405), no sólo el Content-Type.

### 4.12 El canario no repite la suite (OPS-2)

- **EVIDENCIA**: `git show --stat 79037b5` (22/10/2026, 17:29): "fix(ci): el canario de backend ya
  no repite la suite completa"; toca `infra/ci/canario.sh` y `infra/ci/test-backend.sh` (el script
  pasa sus argumentos a pytest; el canario corre sólo el archivo roto).
- **SUPUESTO**: que el run de CI de ese commit dio verde. No se miró (L-037: hasta verlo, no está
  cerrado). Si dio verde, la fila sale de la lista del 4.

### 4.13 Dos decisiones más que salieron del explore

- **Concurrencia** (ficha: "cómo se bloquea la cuenta durante una imputación"; A-11):
  `SELECT 1 FROM cuenta WHERE id = :id FOR UPDATE` al principio de toda imputación, corrección o
  saldo inicial; la emisión bloquea sus cuentas con `ORDER BY id` en una sola sentencia (mismo orden
  para todos: sin interbloqueo); las lecturas de imputaciones van siempre **después** del bloqueo.
  Rechazadas: `FOR UPDATE` sobre `unidad` (frena el padrón y no sirve para la cuenta de persona),
  advisory lock (invisible y sin RLS), SERIALIZABLE (reintentos en todos los caminos, sin precedente
  en el repo). EVIDENCIA del arquitecto: `FOR UPDATE` sobre READ COMMITTED ya es el patrón en
  `escritura.py:252`, `unidades.py:122`, `grupos.py:52`, `usuarios.py:325`.
- **Cuenta de persona** (D-109.2; A-12): una tabla `cuenta` polimórfica (unidad **o** persona) de la
  que cuelgan obligaciones y movimientos. Rechazada: columnas `unidad_id`/`persona_id` excluyentes
  en cada tabla del libro. Es **la decisión más cara de revertir del change**: pasar de columnas a
  `cuenta` después exige `UPDATE` sobre un libro que no lo admite. Por eso `cuenta` nace en la
  primera migración del libro aunque el cambio de titular se construya más tarde.
- **El cambio de titular se orquesta desde `cuenta_corriente`** (A-13): si quedara en `acceso`,
  aparece el ciclo `acceso → cuenta_corriente → acceso`. Igual para el saldo inicial: el libro no
  hace `UPDATE complejo`; llama a una función nueva de `complejos.aplicacion`.

## 5. Lo que el 4 le expone al resto (A-06)

```
registrar_emision(sesion, identidad, *, emision_id, complejo_id, periodo,
                  obligaciones, request_id) -> None
calcular_intereses(sesion, *, complejo_id, corte) -> list[InteresCalculado]   # sin efectos
registrar_intereses(sesion, identidad, *, emision_id, corte, request_id) -> list[InteresRegistrado]
anular_emision(sesion, identidad, *, emision_id, motivo, request_id) -> None
imputar(sesion, identidad, *, cuenta_id, credito, request_id) -> ...         # lo llama el 8
corregir(sesion, identidad, *, movimiento_id, motivo, operacion_id, ...)     # HU-A9
cargar_saldo_inicial(sesion, identidad, *, complejo_id, filas, operacion_id) # lo llama el 5
deuda_por_cuenta(sesion, *, complejo_id, al) -> list[DeudaDeCuenta]
es_moroso_critico(...) / etiqueta_de_deuda(...)                               # R20, P31, R30
repartir(total, coeficientes) -> list[Dinero]                                 # compartido/reparto.py
```

Firmas tentativas (las primeras cinco las propuso el arquitecto; las demás las completa el
orquestador desde la ficha). Todas reciben la sesión, exigen transacción y no confirman. El 7
nunca escribe `obligacion` ni `movimiento`; la fórmula del interés existe una sola vez.

## 6. Requisitos del analista (resumen)

34 requisitos `RQ-01` a `RQ-34`, cada uno con actor, disparador, resultado observable y el caso
que falla hoy; texto completo en `.git/informes-explore-4/01-analista.md`. Agrupados:

| regla | requisitos | lo que más importa |
|---|---|---|
| R07 reparto | RQ-01 a RQ-05 | $1.000.000 entre 150 suma exacto; empate determinista en 100 corridas; `hypothesis` con oráculo propio; `float` rechazado |
| R03 intereses | RQ-06 a RQ-13 | dos tramos con un solo redondeo; gracia; mes entero; nunca interés sobre interés; versión de tasa por tramo; **calcular no registra** |
| R04/R13 imputación | RQ-14 a RQ-16 | el ejemplo de R04 ($4.000 + $80.000 + $16.000, residual $69.000) |
| R05 | RQ-17 a RQ-20 | excedente como crédito; cada crédito a su destino fijo; ninguna columna "pagada" |
| R06 | RQ-21 | el saldo anterior se muestra sin débito nuevo |
| R08/HU-A9 | RQ-22 a RQ-24 | `UPDATE`/`DELETE`/`TRUNCATE` por SQL rebota; corrección sin motivo rechazada; 403 para quien no es super admin ni administrador principal |
| R09 | RQ-25, RQ-26 | detalle por período o total único; interés traído no genera interés; origen archivo y fila |
| R20 | RQ-27 a RQ-30 | 1 vencida no, 2 sí; emisión anulada no cuenta; sólo interés da "deuda de intereses" |
| R30 | RQ-31 | debajo de $500 no es moroso crítico |
| D-086 | RQ-32 | segunda emisión del mismo período rechazada salvo anulada |
| concurrencia | RQ-33 | dos imputaciones simultáneas contra PostgreSQL real |
| idempotencia | RQ-34 | misma clave, un solo movimiento |

**Regla de oro del analista** (L-034): todos estos tests dan rojo hoy por `ModuleNotFoundError`, y
ese rojo **no cuenta**. Cada RED se mide contra una versión vacía del módulo (la función existe y
devuelve vacío), en la aserción que el test dice probar.

R32 quedó **sin requisito escrito**: con lo que dice la regla no se puede escribir un resultado
observable que no sea un invento (H-01, H-02).

## 7. Riesgos

| id | riesgo | qué lo frena |
|---|---|---|
| R-1 | Un índice único que falta en la primera migración no se puede agregar después si ya hay duplicados (no se borran filas) | Todas las claves naturales de la sección 3 desde la primera migración del libro (4.4) |
| R-2 | Elegir columnas excluyentes en lugar de `cuenta` obliga a reescribir el libro el día que entre la cuenta de persona | `cuenta` nace en la primera migración (4.13) |
| R-3 | La sonda de arranque copiada a tablas con FK entrante frena cada deploy, o aflojada queda ciega | Verificación por catálogo para `TRUNCATE` (4.1) |
| R-4 | "Una emisión por período salvo anulada" no se puede expresar con un único parcial si el estado vive en otra tabla (`evento_de_emision`) | El design elige: bloqueo + verificación en la aplicación con `FOR UPDATE` sobre el complejo, o una columna derivada de sólo agregar; con test de concurrencia (JUICIO del orquestador, confianza media) |
| R-5 | Interés registrado sin período definido hace que R20 cuente mal (H-05) | Pregunta P-4 antes del propose del sub-change de intereses |
| R-6 | El reparto y el interés usan modos de redondeo distintos y alguien los mezcla | Dos funciones con nombre distinto y un test que las distingue (4.5) |
| R-7 | Un doble en memoria del libro da verdes que la base rechaza | Sin puerto de repositorio (4.9); toda garantía del libro con test contra PostgreSQL real |
| R-8 | La ficha arrastra datos viejos que el constructor va a creer: R30 como propuesta, "marcas del 3a" para R35/R36/R39 que no existen, P10/P11/P42 como bloqueantes en `10:155,163` y `07:140` | Corregirlos en la KB antes del propose (sección 10) |
| R-9 | Un change CRITICAL de más de cuarenta tareas se revisa mal: el rompedor y el auditor leen un diff que no termina de moverse | Partición (sección 8) |
| R-10 | SU-02 (la deuda previa la hereda el comprador según el CCyC) sin verificar con abogado justo donde más se discute una venta | El default es configurable; validarlo antes del piloto junto con P42 |

## 8. Partición propuesta

**Sí conviene partir.** EVIDENCIA: `openspec/config.yaml` ("un cambio de más de unas veinte tareas
se parte"); la ficha suma R03 a R09, R13, R20, R30, la cuenta de persona y doce decisiones de
diseño, y cada regla lleva su tarea de test antes que la de implementación. JUICIO (arquitecto y
orquestador, confianza alta en partir, media en el corte exacto):

| orden | sub-change | gobernanza | contenido | por qué ahí |
|---|---|---|---|---|
| 1 | **4a `cimientos-del-libro`** | HIGH | reglas nuevas del test de fronteras (4.3) sobre un `cuenta_corriente/` vacío; dueño de las tablas de sólo agregar y chequeo de arranque (4.1); `compartido/reparto.py`, aritmética de `Dinero` y `hypothesis` (4.5); columnas nuevas de `configuracion_versionada` (umbral de R30, y R23 y día de cierre si se eligen); auditoría del coeficiente (4.10); deuda D-053 del 1b | Los controles tienen que existir antes de la primera tabla de plata, y el `ALTER` de `configuracion_versionada` tiene que correr **antes** de que deje de ser del migrador |
| 2 | **4b `libro-de-movimientos`** | CRITICAL | `cuenta`, `emision`, `evento_de_emision`, `obligacion`, `movimiento`, `imputacion` con sólo agregar, RLS y claves naturales; concurrencia; R04, R05, R06, R08, R13; HU-A9 (ruta, permiso y contrato de error); saldo sin anuladas; la API de la sección 5 | Es el núcleo que todo lo demás lee |
| 3 | **4c `intereses-saldo-inicial-y-moroso`** | CRITICAL | R03 con corte al cierre; R09 (caso de uso que llama el 5); R20 con "deuda de intereses" y R30 | Funciones sobre 4b; el 5 lo necesita |
| 4 | **4d `cambio-de-titular`** | CRITICAL | R32 / D-109.2: registro del cambio, las dos opciones, traspaso a la cuenta de persona, aviso sin bloqueo | Cruza tres módulos, carga SU-02, depende del 7 para el prorrateo por días y no está en el camino a M1; `cuenta` ya nace polimórfica en 4b, así que esperar no cuesta una migración |

**Lo que se gana**: el 6 sólo necesita el reparto, así que podría arrancar después del 4a si no
escribe en el libro (SUPUESTO S-04 del arquitecto, no verificado contra R14 y R25); el 5 necesita el
4c; el 7 necesita el 4b y el 4c. El 4d puede ir después del 7 sin bloquear M1.

**Rechazada**: un solo change de cuarenta y tantas tareas (excepción registrada como la del 1c,
D-088). El 1c era infraestructura; éste es plata, y el riesgo de un diff que no termina de moverse
lo paga el rompedor.

**Precedente**: el 2 se partió en 2a, 2b y 2c (D-097) y el 3 en 3a y 3b; el 2.2a se intercaló con
numeración propia sin renumerar el resto. Acá conviene lo mismo: 4a a 4d, sin renumerar C-08 en
adelante.

## 9. Preguntas que quedan

**Para Juani**, en castellano llano (las que bloquean un sub-change lo dicen):

- **P-1 · El cambio de titular** (H-01): ¿lo construimos entero (registro, las dos opciones y el
  aviso) en un sub-change propio después de la liquidación (4d), o sólo dejamos la cuenta de persona
  lista y el cambio de titular espera? *Bloquea 4d, no 4a a 4c.*
- **P-2 · La deuda a nombre del vendedor** (H-02): si queda a su nombre, ¿sigue sumando intereses?
  ¿El vendedor puede aparecer como moroso? ¿Cómo paga, si ya no tiene la unidad en el sistema?
  *Bloquea 4d.*
- **P-3 · El cierre del período** (H-04): para el período de octubre, ¿el cierre es el último día
  del mes, el día del vencimiento o un día que fija cada edificio? *Bloquea 4c, y si es un día por
  edificio, la columna tiene que entrar en 4a.*
- **P-4 · De qué mes es el interés** (H-05): el interés por la mora de agosto que aparece en la
  expensa de septiembre, ¿cuenta como deuda de agosto o de septiembre? (Decide si septiembre cuenta
  como "vencida" para el moroso crítico.) *Bloquea 4c.*
- **P-5 · El umbral de $500** (H-06, H-14): ¿se compara contra todo lo que debe la unidad o contra
  cada expensa? Por debajo de $500, ¿sigue corriendo interés? Y "vencida", para el moroso crítico,
  ¿es al día siguiente del vencimiento o recién después de los días de gracia? *Bloquea 4c.*
- **P-6 · ¿Pantalla de corrección en el 4?** (H-15): ¿la corrección de un error (HU-A9) trae
  pantalla, o alcanza con la API y la pantalla llega con la del pago (8)? *Decide 4.7 y 4.11.*
- **P-7 · El redondeo en dos pasos** (H-07): ¿te cierra que "medio hacia arriba" sea para el
  interés y los montos sueltos, y que el reparto de un gasto use mayor resto (truncar y repartir los
  centavos que faltan)? *Bloquea 4a.*
- **P-8 · El repositorio sin puerto** (4.9): esto contradice el texto de D-040 y necesita tu firma.
  *Bloquea 4b.*

**Para Alberto** (ninguna bloquea construir; se validan antes del piloto, como D-109):

- **A-1** (P10, H-07, H-08): cuando repartís un gasto en tu Excel y no cierra al centavo, ¿qué hacés
  con el centavo que sobra o falta? Si hay empate, ¿a qué unidad va?
- **A-2** (P34): ¿tu Excel corta el interés al cierre del período?
- **A-3** (H-10, R26): el doble vencimiento con recargo que ya acepta la configuración, ¿se usa en
  el edificio piloto, y cómo convive con el interés diario?
- **A-4** (H-11): ¿el fondo de reserva se cobra antes o después de la ordinaria cuando un pago no
  alcanza?

**Huecos menores sin pregunta propia** (el design los resuelve y los registra): H-03 (`emision_id`
opcional en `obligacion` y `movimiento`), H-12 (quién dispara la imputación del crédito a favor; el
4 expone `imputar` y lo llama el 7 al emitir, mismo problema que P38), H-13 (pago con fecha valor
anterior a imputaciones ya registradas: se imputa sobre la foto actual y el interés de más se
compensa con el ajuste de R11, que es del 8), H-18 (nombre `emision`, ver 4.2).

## 10. Correcciones a la base que el propose necesita antes de arrancar

EVIDENCIA del analista, sin tocar ahora (explore no escribe la base):

- `12_fichas_de_changes.md:454, 462`: R30 figura como propuesta; D-109 la volvió vigente
  (`05_reglas_de_negocio.md:292`).
- `12_fichas_de_changes.md:470`: "depende del 3a por las marcas que usan R35, R36 y R39"; esas
  marcas no existen en `unidad` ni en `configuracion_versionada` (`04_modelo_de_datos.md:202-209,
  388-396`).
- `10_preguntas_abiertas.md:155, 163` y `07_flujos_principales.md:140` siguen poniendo P10, P11 y
  P42 como bloqueantes del 4; D-109 punto 6 los liberó.
- `04_modelo_de_datos.md:460`: `liquidacion` como contrato mínimo del 4 (ver 4.2).
- R32 no figura en ninguna ficha ni en `CHANGES.md` como alcance de un change (`rg R32|titular`).

## Knowledge Base Impact

Anticipado para el propose de cada sub-change. **REWRITE** = el documento describe el estado nuevo
y el texto viejo se va; **APPEND** = historia fechada.

| documento | operación | qué |
|---|---|---|
| `04_modelo_de_datos.md` | REWRITE | dominio `cuenta_corriente` con `cuenta`, `emision`, `evento_de_emision`, `obligacion`, `movimiento`, `imputacion`; `liquidacion` pasa a ser del 7 con el mismo id; ERD; columnas nuevas de `configuracion_versionada`; dueño de las tablas de sólo agregar |
| `05_reglas_de_negocio.md` | REWRITE | R07 en dos pasos y desempate; R03 con la fecha de cierre (P-3) y el período del interés (P-4); R20 con "deuda de intereses" en definición y tests; R30 con la base del umbral (P-5). Sólo por respuestas a preguntas abiertas, como permite D-089 |
| `08_arquitectura_propuesta.md` | REWRITE | fronteras con las tres reglas nuevas y sus excepciones; `cuenta_corriente → complejos`, `liquidacion → cuenta_corriente`; sin puerto de repositorio; la tabla de módulos distinguiendo construido de planeado (deuda de la auditoría) |
| `09_decisiones_y_supuestos.md` | APPEND | decisiones nuevas: dueño de las tablas de sólo agregar y el préstamo acotado; `emision` del libro con el mismo id que la `liquidacion` del 7 (ajusta D-086); puertos sólo para lo externo (acota D-040); reparto y redondeo en dos pasos; idempotencia por clave del libro; `cuenta` polimórfica; partición del 4; las respuestas P-1 a P-8 |
| `10_preguntas_abiertas.md` | REWRITE | quitar P10/P11/P42 como bloqueantes del 4; sumar P-1 a P-5 y A-1 a A-4 si no se responden antes del propose |
| `11_glosario.md` | REWRITE | "cuenta" (de unidad o de persona), "emisión" frente a "liquidación", "imputación", "deuda de intereses" |
| `12_fichas_de_changes.md` | REWRITE | ficha 4 partida en 4a a 4d, R30 vigente, las marcas inexistentes, dueño de R32; fichas 5, 6 y 7 con la dependencia nueva (4a, 4b, 4c) |
| `CHANGES.md` y `CLAUDE.md` | REWRITE | sub-changes del 4 con dependencias y gobernanza; árbol y camino crítico |
| `07_flujos_principales.md` | REWRITE | línea 140 (bloqueantes viejos) |
| `15_lecciones.md` | APPEND | lo que enseñe la construcción; candidata ya: "un índice único que no nace con el libro no se puede agregar después" |
| `01`, `02`, `03`, `06`, `13`, `14`, `16` | none | el 4 no cambia visión, stack, actores, historias (HU-A9 ya existe), motor de reglas ni forma de trabajo |

## Para Juani y Alberto, en diez líneas

1. Los cimientos aguantan; el 4 conviene partirlo en cuatro: 4a cimientos (HIGH), 4b libro, 4c
   intereses, saldo inicial y moroso, 4d cambio de titular (los tres CRITICAL).
2. Las tablas del libro son del rol de arranque, no del migrador; `configuracion_versionada` también.
3. La `emision` es del libro y la `liquidacion` del 7 usa el mismo id: revertir cuesta sólo DDL.
4. La cuenta es de una unidad o de una persona, en una sola tabla, desde la primera migración.
5. Idempotencia con claves únicas dentro del libro, nunca con la tabla del worker.
6. Reparto por mayor resto (truncar y repartir centavos); medio hacia arriba sólo para el interés.
7. Sin outbox en el 4: no encola nada; los casos de uso nunca confirman ni encolan.
8. Sin puerto de repositorio para el libro: contradice D-040 y necesita firma.
9. Ocho preguntas para Juani (sección 9): P-7 (redondeo) y, si el cierre es un día por edificio,
   P-3 tocan el 4a; P-8 bloquea el 4b; P-3 a P-5 el 4c; P-1 y P-2 el 4d.
10. Antes del propose, corregir cinco datos viejos de la base (sección 10).
