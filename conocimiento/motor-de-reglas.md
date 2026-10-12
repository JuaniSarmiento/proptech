# Motor de reglas

Cómo entra al sistema el reglamento propio de cada edificio sin programar un edificio por vez.
**Se reescribe** cuando cambia el diseño; el porqué de cada cambio va a `decisiones.md`.

## Estado

- **Puerto de políticas** (D-064): **decidido**.
- **Motor propio de plantillas** (D-065): **propuesta, falta que la valide Alberto**. Hasta entonces
  no se escribe código del motor y las fichas 3, 7 y 10 de `roadmap.md` no cambian.
- Fuentes: `openspec/exploraciones/2026-10-12-motor-de-reglas.md` (incluye la prueba de GoRules) y el
  PDF "PropTech · Motor de reglas" entregado a Alberto (fuera del repositorio).

## La idea en una línea

El administrador no escribe reglas: elige de un **catálogo de plantillas** que nosotros fabricamos y
probamos, activa las que dice el reglamento de su edificio y ajusta los números.

Ejemplo: el reglamento dice que quien paga antes del día 5 tiene 10% de descuento. El administrador
activa la plantilla *Bonificación por pronto pago*, carga `10` y `5`, y guarda. Desde la próxima
liquidación se aplica sola. Nadie escribió código.

## Por qué así y no otra cosa

| | GoRules ZEN | Motor genérico propio | Plantillas propias |
|---|---|---|---|
| Plata exacta | No: trabaja con punto flotante | Sí, si se hace bien | Sí |
| Errores visibles | No: ante un error de tipo saltea la regla en silencio | Depende de nosotros | Sí: bloquean la emisión |
| Flexibilidad | Total | Total | La del catálogo |
| Costo de construir | Bajo, más un validador propio | Alto: es un producto en sí | Bajo, crece de a una plantilla |
| Riesgo para el MVP | Alto | Alto | Bajo |

Lo que se resigna: el administrador no puede inventar una regla que no esté en el catálogo, la tiene
que pedir, y cada plantilla nueva es trabajo nuestro con sus tests.

## Qué cambia en la arquitectura

**Poco.** El motor es un módulo más de `proptech_core` y no suma infraestructura: ni servicio, ni
base, ni contenedor nuevo.

| Pieza | Dónde | Qué es |
|---|---|---|
| Módulo `politicas` | `backend/src/proptech_core/politicas/` | Mismo formato que el resto (D-040): `dominio/`, `aplicacion/`, `puertos.py`, `adaptadores/` |
| Puerto `MotorDePoliticas` | `politicas/puertos.py` | Lo único que ven los demás módulos. Nadie importa una plantilla directo |
| Catálogo | `politicas/dominio/` | Una plantilla por tipo de regla, con sus parámetros, su cálculo y sus tests |
| Configuración por edificio | tabla nueva en la base | Qué plantillas usa cada edificio y con qué valores, con versión |
| Valores iniciales | `config/parametros.yaml` | Los defaults de cada plantilla, como hoy (D-042) |

**Lo que no cambia**: el núcleo financiero sigue en código con sus tests. La imputación (R04), los
pagos parciales (R05), el reparto sin perder centavos (R07), la cuenta corriente que sólo agrega
movimientos (R08) y el aislamiento entre edificios (R10) **no pasan al motor**.

## El contrato: hechos adentro, propuestas afuera

```
hechos (los da el núcleo)              acciones propuestas (devuelve la plantilla)
edificio, período                      [ { tipo: "bonificacion",
unidad, estado de la unidad                concepto: "pronto_pago",
deuda y antigüedad                         monto: "7630.04",
fecha del pago                             motivo: "pago el día 3, límite día 5" } ]
monto base: "76300.42"
```

1. **El núcleo pasa los datos** del mes de cada unidad.
2. **Cada plantilla activa propone** cargos, bonificaciones o alertas, con el monto como texto
   `Dinero` y siempre con su motivo.
3. **El núcleo valida cada propuesta** (formato, signo, que el monto se pueda leer con `Dinero`) y la
   registra como movimiento con su motivo, que incluye la plantilla y la versión que la generó.

El motor decide **qué** corresponde; el núcleo decide **cómo** se registra. Ninguna plantilla escribe
plata por su cuenta.

Reglas del contrato:

- Los hechos salen siempre de datos del núcleo, **nunca de la salida de otra plantilla**. Cada
  plantilla se evalúa sola; no hay reglas encadenadas.
- Montos y porcentajes viajan como texto, nunca como `float` (D-046).
- La salida de una plantilla que no cumple el contrato es **un fallo**, nunca "no hay regla".

## El catálogo del MVP

| Plantilla | Qué configura el administrador | Origen | Cambio |
|---|---|---|---|
| Intereses por mora | Tasa mensual, días de gracia, por día o mes entero. Siempre interés simple | R03 (ya existe) | 3 |
| Fondo de reserva | Porcentaje sobre la ordinaria | R15 (ya existe) | 3 |
| Cargo por estado de la unidad | Factor y cargo fijo por estado. Apagada en edificios (D-030) | R02 (ya existe) | 3 |
| Alertas antes de emitir | Qué controles bloquean la emisión y cuáles sólo avisan | ProTecc | 7 |
| Bonificación por pronto pago | Porcentaje y día límite. Apagada por defecto | Alberto (propuesta) | 7 |
| Cargo recurrente del reglamento | Concepto, monto y a qué unidades (ej.: canon por cochera) | Propuesta | 7 |
| Moroso crítico | Cuántas liquidaciones vencidas lo definen | R20 (D-058) | 10 |

Las tres primeras ya están decididas como menús cerrados: pasar a plantilla no cambia lo que hacen,
sólo cómo se enchufan.

**Fuera del MVP**: bloqueo de amenities a morosos, planes de pago y multas con escalas o
reincidencia. Cuando lleguen se suman al catálogo; si alguno no entra en una plantilla, recién ahí se
evalúa un motor libre **detrás del mismo puerto**.

## Versiones y auditoría

- Cada vez que un edificio activa, apaga o cambia una plantilla se guarda una **versión nueva** con
  fecha y autor. Las versiones viejas no se editan.
- **Cada liquidación guarda qué versión de cada plantilla usó.** Si en abril el descuento pasa del 10%
  al 15%, la expensa de marzo se sigue explicando con el 10%. Es la misma garantía que ya da D-010
  para la tasa de interés.
- No hace falta tabla de auditoría aparte: el motivo de cada movimiento (R08) ya dice qué plantilla y
  qué versión lo generó.
- La configuración es un dato del edificio como cualquier otro: se lee con el mismo aislamiento por
  identidad y Row-Level Security (R10).

## Ver antes de emitir

La **preliquidación** muestra, línea por línea, qué plantilla generó cada cargo o bonificación y por
qué. El administrador ve el efecto de una regla nueva antes de que le llegue a un vecino.

## Si algo falla

| Caso | Qué hace el sistema |
|---|---|
| Una plantilla no puede calcular (falta un dato, valor inválido) | Alerta que **bloquea la emisión** y dice qué plantilla y qué unidad. Nunca la saltea |
| La propuesta no cumple el contrato | Igual: bloqueo con alerta. Es un fallo del motor, no "no hay regla" |
| El edificio no tiene la plantilla activa | Caso normal: se usa el default documentado (sin descuento, sin recargo extra) |
| El administrador carga un parámetro fuera de rango | El formulario lo rechaza y dice qué campo está mal |

## Qué tan difícil es

- **Las plantillas son lo fácil.** Cada una es una regla con parámetros validados y tests escritos
  antes, igual que R01 a R31.
- **Lo difícil son las versiones.** Que cada liquidación quede atada a la configuración con la que se
  calculó, sin excepciones. Si eso falla, una expensa vieja deja de poder explicarse.
- **El riesgo es de alcance.** Si se pide que el administrador escriba reglas libres, eso es otro
  producto y trae los mismos errores silenciosos por los que se descartó GoRules. El catálogo cerrado
  es lo que mantiene el riesgo bajo.

## Dónde entra en el roadmap *(si Alberto lo valida)*

No es un cambio aparte; se reparte en tres que ya existen:

| Cambio | Qué agrega |
|---|---|
| 3 · `configuracion-del-edificio` | El módulo `politicas`, el puerto, el catálogo, el versionado y las plantillas de intereses, fondo de reserva y cargo por estado |
| 7 · `liquidacion-y-emision` | La liquidación consulta el puerto y guarda las versiones usadas; alertas antes de emitir, bonificación por pronto pago y cargo recurrente; la preliquidación muestra qué plantilla generó cada línea |
| 10 · `morosidad` | La plantilla de moroso crítico |

Los tres cambios crecen. Cuánto, se estima en el propose de cada uno, no antes.

## Para validar con Alberto

- [ ] El enfoque: plantillas propias detrás del puerto, en vez de GoRules o un motor genérico.
- [ ] El catálogo inicial; en particular si la bonificación por pronto pago y el cargo recurrente
  entran al MVP.
- [ ] Quién configura las reglas al principio: el administrador desde un formulario, o nosotros por
  él los primeros meses.
- [ ] Qué reglas reales tiene el reglamento del edificio piloto (P1): es la prueba de que el catálogo
  alcanza.
