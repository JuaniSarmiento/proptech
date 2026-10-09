# Exploración: estructura del MVP (orden, dependencias, cortes, riesgos)

> Explore mode. No se escribió código ni se tocó `conocimiento/`. Lo que sigue son hallazgos y
> propuestas para que Juani decida; nada de esto es una decisión tomada.

**Fecha**: 2026-10-09
**Disparador**: D-045 pide un explore general sobre los 15 cambios de OPSX antes de arrancar,
para confirmar orden y dependencias.

**Fuentes leídas**: `conocimiento/mvp.md`, `reglas-de-negocio.md`, `decisiones.md` (D-001 a D-045
y preguntas abiertas), `glosario.md`, `proyecto-final.md`, `README.md`, `CLAUDE.md`,
`openspec/config.yaml`, `especificacion/arquitectura-alberto/arquitectura_koris_a_lo_criollo.md`
completo, y de `especificacion/analisis/Analisis_de_coherencia.md` los títulos de las 48
observaciones (H01-H48) más la sección 09 "Secuencia propuesta" completa.

---

## 1. El hallazgo principal: el orden tiene un problema de dependencia real

La propuesta de D-045 pone `importacion-desde-excel` (4) antes de `motor-de-cuenta-corriente` (5).
Pero R09 (saldo inicial al migrar) dice textualmente:

> "Con detalle por período: se carga cada obligación vieja con su período y vencimiento (...)
> Sólo con un total: se carga una obligación 'saldo inicial' (...) Crédito a favor: entra como
> crédito y se compensa en la primera liquidación."

Esto es: **importar el Excel genera Obligaciones y Créditos**, que son conceptos del módulo
`cuenta_corriente` (Obligación, Movimiento, Imputación, Crédito a favor). Si `importacion-desde-excel`
se construye antes de que exista el modelo de cuenta corriente, o bien no se puede cumplir R09
de verdad (se carga un número suelto, no una obligación real) o el cambio 4 termina construyendo
él mismo parte del dominio que le corresponde al cambio 5, duplicando trabajo.

Esto coincide con lo que dice el análisis de coherencia original (sección 09, "Secuencia
propuesta"), que agrupa en la **misma primera etapa** "el modelo de obligación, pago e
imputación, la política de mora **y el tratamiento del saldo de apertura**", separado de la carga
de unidades. Es la misma conclusión por otra vía: el saldo inicial es un problema de cuenta
corriente, no de importación de planillas.

**Recomendación**: invertir el orden de 4 y 5. `motor-de-cuenta-corriente` se construye primero
(su capa de dominio es funciones puras: R01, R04, R05, R06, R07, R08, R09 no necesitan una unidad
real, se prueban con fixtures). `importacion-desde-excel` se construye después y, para el saldo
inicial, **llama** al caso de uso de cuenta corriente que ya existe, en vez de inventar el suyo.

Esto no es una reestructuración grande: sigue habiendo 15 cambios, mismo contenido, nomás se
cruzan el 4 y el 5.

---

## 2. Grafo de dependencias real (los 15 cambios, con el cruce aplicado)

```
1 base-del-proyecto
   │
   ▼
2 acceso-y-aislamiento  (login + roles + RLS; CRITICAL)
   │
   ▼
3 configuracion-del-edificio  (reglas: intereses, grupos, categorías, fondo)
   │
   ├──────────────┐
   ▼              │
5* motor-de-cuenta-corriente   │   (*ex-4; dominio puro, necesita 1 para persistir)
   │              │
   ▼              │
4* importacion-desde-excel  ◄──┘   (*ex-5; usa el caso de uso de saldo inicial de 5*)
   │
   ▼
6 gastos-y-cargos  (necesita 3: categorías y grupos)
   │
   ▼
7 liquidacion-y-emision  (necesita 3,4*,5*,6 todos juntos; el cambio más grande del MVP)
   │
   ├─────────────────────────────┐
   ▼                             ▼
8 pagos-informados          10 morosidad (necesita 7 y 8 para antigüedad real)
   │                             │
   ▼                             │
9 extracto-bancario               │
   │                             │
   └──────────────┬──────────────┘
                   ▼
           11 portal-del-vecino  (necesita 7, 8, 10: expensa + deuda + estado de pago)
                   │
                   ▼
           12 vista-del-consejo  (necesita 6, 7, 10; chica, read-only)
                   │
                   ▼
           13 avisos-por-email  (necesita 7 para vencimientos, worker de 1)
                   │
                   ▼
           14 lectura-de-facturas  (enriquece a 6; necesita worker de 1 + puerto de IA)
                   │
                   ▼
           15 piloto-en-paralelo  (necesita TODO M1+M2 + datos reales del piloto, P1)
```

### Tabla de dependencias

| # | Cambio | Depende de (real) | Por qué |
|---|---|---|---|
| 1 | base-del-proyecto |: | infra, repo, Docker, migraciones, worker, CI |
| 2 | acceso-y-aislamiento | 1 | necesita DB y esqueleto de API/web para login y RLS |
| 3 | configuracion-del-edificio | 1, 2 | necesita tenancy y el edificio como entidad aislada |
| 5\* | motor-de-cuenta-corriente | 1 (sólo para persistir; el dominio puro no depende de nada) | R01-R09 son funciones; la tabla de movimientos necesita migraciones |
| 4\* | importacion-desde-excel | 3, 5\* | crea unidades reales de 3; usa el caso de uso de saldo inicial de 5\* (R09) |
| 6 | gastos-y-cargos | 3 | categorías (R16) y grupos de reparto (R01) ya tienen que existir |
| 7 | liquidacion-y-emision | 3, 4\*, 5\*, 6 | junta reglas, gastos aprobados, cargos particulares, fondo, PDF, email |
| 8 | pagos-informados | 7 (hay deuda que pagar), 2 (login de vecino) | sin liquidación emitida no hay nada que confirmar |
| 9 | extracto-bancario | 8 | concilia contra pagos informados ya existentes |
| 10 | morosidad | 7, 8 | antigüedad y deuda se calculan desde imputaciones reales |
| 11 | portal-del-vecino | 7, 8, 10 | muestra expensa, estado de pago y deuda juntos |
| 12 | vista-del-consejo | 6, 7, 10 | sólo lectura de lo que ya existe |
| 13 | avisos-por-email | 7, 1 (worker) | vencimientos vienen de la liquidación emitida |
| 14 | lectura-de-facturas | 6, 1 (worker) | enriquece la carga de gastos con QR + IA |
| 15 | piloto-en-paralelo | todo M1 y M2, + dato real del piloto (P1) | es la validación, no una funcionalidad nueva |

---

## 3. Lista final recomendada, en orden, una línea cada una

1. **base-del-proyecto**: repo, Docker Compose, Postgres+Alembic, esqueleto FastAPI/Next.js,
   Redis+worker ARQ, Caddy, CI, `config/parametros.yaml` y su loader, seed de un edificio de
   ejemplo, logging estructurado.
2. **acceso-y-aislamiento**: login (decidir Clerk+enlace mágico o alternativa), los 4 roles de
   D-037, RLS con `SET LOCAL`, 404 fuera de alcance vs 403 sin permiso. CRITICAL.
3. **configuracion-del-edificio**: HU-A1: intereses, grupos de reparto, categorías, fondo de
   reserva, valores default desde `parametros.yaml`.
4. **motor-de-cuenta-corriente** *(antes 5)*: R01, R04, R05, R06, R07, R08, R09: el libro de
   movimientos, imputación, redondeo por mayor resto, correcciones, saldo inicial. CRITICAL.
5. **importacion-desde-excel** *(antes 4)*: HU-A2: unidades desde Excel, validación fila por
   fila, no duplicar, saldo inicial usando el caso de uso de (4).
6. **gastos-y-cargos**: HU-A3 (manual), HU-A3b: gastos en borrador/aprobado, ordinaria/
   extraordinaria (R13), cargos particulares (R14).
7. **liquidacion-y-emision**: HU-A4, HU-A5: preliquidación, emisión, PDF, email. El cambio más
   grande; candidato a explore propio y a partirse en dos tareas grandes (ver sección 5).
8. **pagos-informados**: HU-A6, HU-V4: comprobante del vecino, bandeja de confirmación, R11.
   CRITICAL.
9. **extracto-bancario**: HU-A7: conciliación contra el CSV/Excel del banco.
10. **morosidad**: HU-A8: deuda, antigüedad, intereses, export a Excel.
11. **portal-del-vecino**: HU-V1, V2, V3, V5: entrar, ver deuda, entender la expensa, descargar.
12. **vista-del-consejo**: HU-C1: sólo lectura de morosidad, gastos y liquidaciones.
13. **avisos-por-email**: HU-V6: aviso de vencimiento y de mora, sin duplicar.
14. **lectura-de-facturas**: HU-A3 (factura con QR+IA): R12 completo.
15. **piloto-en-paralelo**: un mes real contra el método actual del piloto; backups con restore
    probado; evidencia de aislamiento.

---

## 4. Camino crítico al test de aceptación de M1

El test de M1 ("reproduce la última liquidación del piloto al centavo") sólo se puede correr
cuando están **1 → 2 → 3 → 4\* → 5\* → 6 → 7** completos, Y ADEMÁS existen los datos reales del
piloto (P1). Son dos caminos independientes que convergen:

```
Camino técnico:  1 → 2 → 3 → motor-cta-cte → importación → 6 → 7 ──┐
                                                                      ├──► TEST M1
Camino de datos: gestionar el piloto con Alberto (P1) ───────────────┘
```

**Hoy (09/10) el camino de datos está en cero**: D-033 dice que el piloto lo consigue Alberto,
pero la fecha "cuándo entrega sus datos" sigue sin respuesta (P1 no resuelta). Si ese camino no
arranca en paralelo desde el cambio 1, M1 queda con el código listo y sin forma de demostrarse,
que es exactamente el riesgo que D-004 quería evitar ("el piloto se consigue en la fase 0, no al
final"). **El camino más corto a M1 no es sólo técnico: es pedirle a Alberto el padrón, las
facturas y la última liquidación del edificio piloto desde ahora, no cuando el cambio 7 esté
cerca de terminar.**

---

## 5. Decisiones bloqueantes, con su fecha límite

| Decisión pendiente | Bloquea | Último momento para decidirla | Por qué ese momento |
|---|---|---|---|
| Centavos enteros vs `Decimal` (D-039, hoy "Vigente" R07 pero marcada "a validar con Alberto") | **Cambio 1** (esquema de cualquier columna de dinero) y de ahí todo lo demás | Antes del *design* de `base-del-proyecto` | Es la decisión más cara de revertir de todo el proyecto: toca cada tabla con plata. Validarla después de construir el cambio 4 (cuenta corriente) significa migrar todo. |
| Método de login (Clerk + enlace mágico, forma concreta) (D-039: "se resuelve en el design del primer change de OPSX") | **Cambio 2** (acceso-y-aislamiento) | Antes del *design* del cambio 2 | D-039 dice "el primer change", y el primero de la lista es `base-del-proyecto` (1), no `acceso-y-aislamiento` (2). Si nadie lo nota, el cambio 1 pasa sin decidirlo y el 2 arranca sin la decisión que D-039 le asignó. Conviene aclarar ahora que es el cambio 2 el que la resuelve. |
| Edificio piloto: cuál es y cuándo entrega datos (P1) | El **test de aceptación de M1**, no el código de M1 | Ya, en paralelo desde el cambio 1 | Sin esto M1 no se puede dar por cumplido aunque 1 a 7 estén terminados y verificados. |
| Defaults de intereses sin validar con administrador/contador (R03) | Calidad del dato en **cambio 3**, no bloquea construir | Antes de M3 (piloto en paralelo); no antes de M1 | Es configurable por edificio y no altera liquidaciones ya emitidas: se puede construir con el default y corregir después. |
| Proveedor de IA para lectura de facturas (D-039: sin elegir) | **Cambio 14** | Antes del *design* del cambio 14 | El puerto (D-021, arquitectura de Alberto) ya aísla al dominio del proveedor; no hace falta elegirlo antes, sólo antes de ese cambio puntual. |
| Precio y modelo comercial (P8) | Nada técnico de los 15 cambios | Antes de vender, no antes de M3 | No aparece en ninguna historia de usuario del MVP. |

---

## 6. Tamaño por cambio: ¿entra cada uno en un ciclo propose/apply/verify/archive?

La mayoría sí. Dos candidatos a quedar grandes:

- **7 · liquidacion-y-emision**: junta HU-A4 (preliquidación, sin efectos) y HU-A5 (emisión, con
  efectos: congela importes, genera obligación por unidad, PDF, email). Es la intersección de
  casi todas las reglas (R01, R03, R04, R07, R13, R15, R16) más la frontera de transacción que
  describe la arquitectura de Alberto (qué pasa si Redis se cae justo después del commit, antes
  de encolar el PDF). Riesgo real de que las tareas de un solo cambio superen "medio día cada
  una" (regla de `openspec/config.yaml`). **Sugerencia**: mantenerlo como un cambio, pero con
  `tasks.md` separando explícitamente "preliquidación y revisión" (sin escribir nada) de "emisión,
  freeze y disparo del worker" (con efectos), para que si hay que frenar a mitad de camino, se
  frena en un borde limpio.
- **4\* · motor-de-cuenta-corriente** (el ex-5): ocho reglas de negocio (R01, R04-R09) en un solo
  cambio. Merece su propio explore antes del propose (ver sección 7), no necesariamente partirse.

El resto (2, 3, 5\*, 6, 8, 9, 10, 11, 12, 13, 14) tiene un alcance que se corresponde con una
historia de usuario o un grupo chico de ellas; parecen del tamaño correcto para un desarrollador
solo.

---

## 7. Qué cambios merecen su propio explore antes del propose

- **motor-de-cuenta-corriente**: el modelo del libro mayor, la concurrencia de dos pagos
  simultáneos (R04, H05 del análisis original) y el algoritmo de mayor resto determinista (R07)
  tienen varias formas válidas de implementarse; vale la pena pensarlo antes de fijar tablas.
- **acceso-y-aislamiento**: hay que resolver login (Clerk+enlace mágico) y decidir en qué capa
  vive cada uno de los tres controles (administración, alcance, permiso) antes de tocar código,
  porque es CRITICAL y pisa autenticación y datos de usuario (floor del governance de OPSX).
- **liquidacion-y-emision**: la frontera de la transacción (qué queda dentro del commit y qué
  queda para el worker) y qué pasa si falla justo después, sin patrón outbox (descartado para el
  MVP por D-039), es una decisión de diseño real, no mecánica.
- **importacion-desde-excel**: no por sí sola, sino para fijar junto con motor-de-cuenta-corriente
  la interfaz exacta entre ambos (qué caso de uso llama el importador para el saldo inicial).

El resto puede ir directo a `/opsx:propose` sin explore dedicado.

---

## 8. Qué falta en el plan de 15 cambios

- **Datos semilla / edificio de ejemplo**: `mvp.md` dice "mientras no estén sus datos se diseña
  con un edificio de ejemplo", pero ningún cambio lo entrega como artefacto explícito. Debería
  ser una tarea chica dentro de `base-del-proyecto` (o `configuracion-del-edificio`).
- **CI**: ningún cambio menciona correr los tests automáticamente en cada push. Dado que el
  proyecto exige TDD estricto, conviene que `base-del-proyecto` lo deje andando desde el día uno,
  no como an afterthought.
- **`config/parametros.yaml` y su loader** (D-042): se nombra en varias historias pero no aparece
  como entregable de ningún cambio puntual; lógicamente es `base-del-proyecto` quien crea el
  archivo y `configuracion-del-edificio` quien lo consume al crear un edificio.
- **Backups y su restauración probada**: `mvp.md` lo asigna como observación de M3 (H46), pero
  configurar el backup automático no puede esperar a `piloto-en-paralelo` si para entonces ya hay
  datos reales de un edificio (cambio 15 llega después de M1 y M2 completos). Sugerencia:
  backups automáticos desde `base-del-proyecto`; la prueba formal de restauración, en
  `piloto-en-paralelo`, pero antes de que el piloto cargue datos reales si es posible.
- **Plantilla del PDF de la expensa**: vive implícita en el cambio 7, pero no está nombrada como
  tarea. D-020 dice "las interfaces pasan por la skill impeccable cuando arranque su diseño"; vale
  la pena decidir si un PDF de expensa cuenta como "interfaz" a esos fines.
- **Observabilidad básica** (logs estructurados con `request_id`, que describe la arquitectura de
  Alberto): no aparece como entregable de ningún cambio; encaja en `base-del-proyecto`.
- **Riesgo sin mitigación explícita**: qué pasa si Redis se cae justo después del commit de una
  emisión, antes de encolar el PDF (el patrón outbox queda fuera del MVP por D-039). No bloquea
  nada, pero si nadie lo decide en el *design* del cambio 7, el sistema puede emitir una
  liquidación sin que el vecino nunca reciba su comprobante y sin que quede ningún rastro de que
  falta. Mínimo viable: una columna de estado en la obligación/emisión más una forma manual de
  reprocesar, decidida explícitamente en el *design*, no descubierta en producción.

---

## 9. Propuestas de decisión (para que Juani las acepte o las descarte; nada de esto se escribió en `conocimiento/`)

1. **Invertir el orden de `importacion-desde-excel` y `motor-de-cuenta-corriente`** dentro de M1
   (sección 1 y 2 de este documento).
2. **Aclarar que "el primer change" de D-039 (método de login) es `acceso-y-aislamiento` (2)**, no
   `base-del-proyecto` (1), para que la decisión no quede sin dueño.
3. **Confirmar centavos enteros vs `Decimal` con Alberto antes del *design* de `base-del-proyecto`**,
   no dejarlo para cuando se construya la cuenta corriente.
4. **Arrancar la gestión del piloto (P1) ya, en paralelo al cambio 1**, no esperar a acercarse al
   cambio 7.
5. **Agregar a `base-del-proyecto`** como tareas explícitas: CI corriendo tests, `config/
   parametros.yaml` + loader, seed de un edificio de ejemplo, logging estructurado con
   `request_id`, backups automáticos.
6. **Partir `tasks.md` de `liquidacion-y-emision` en dos bloques** (preliquidación sin efectos /
   emisión con efectos) aunque siga siendo un solo cambio de OPSX.
7. **Explore dedicado antes del propose** de `motor-de-cuenta-corriente`, `acceso-y-aislamiento` y
   `liquidacion-y-emision`.
8. **Decidir explícitamente en el *design* de `liquidacion-y-emision`** qué pasa si falla el
   encolado del PDF después del commit de la emisión (sin outbox), en vez de descubrirlo con el
   piloto.

## 10. Lo que no se tocó en esta exploración

No se abrió ninguna discusión sobre tablas, endpoints o pantallas concretas (eso es *design* de
cada cambio, D-007). No se investigó precio (P8): no bloquea ningún cambio técnico. No se
cuestionó el contenido de los hitos M1/M2/M3 ni las historias de usuario, sólo el orden y las
dependencias entre los 15 cambios que ya están decididos en D-045.
