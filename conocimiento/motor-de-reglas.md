# Motor de reglas

Cómo entra al sistema el reglamento propio de cada edificio sin programar un edificio por vez.
**Se reescribe** cuando cambia el diseño; el porqué de cada cambio va a `decisiones.md`.

## Estado

- **Puerto de políticas** (D-064): decidido.
- **GoRules ZEN + editor visual jdm-editor detrás del puerto, con validador propio** (D-066):
  decidido el 12/10, a pedido de Alberto. Reemplaza al motor propio de plantillas (D-065).
- Todavía **no se escribe código** del motor. Los detalles abiertos se cierran en el explore del
  cambio 3.
- Fuentes: `openspec/exploraciones/2026-10-12-motor-de-reglas.md` (prueba de GoRules con montos
  reales) y el demo BRE que pasó Alberto (FastAPI + ZEN, React + jdm-editor; fuera del repositorio).

## La idea en una línea

Las reglas de cada edificio se **dibujan** en un editor visual como un grafo (entrada, tabla de
decisión, salida), se guardan como JSON (formato JDM) y el motor ZEN las ejecuta cuando se arma la
liquidación. El motor **decide** qué corresponde; el núcleo **calcula** la plata y la registra.

Ejemplo: el reglamento dice que quien paga antes del día 5 tiene 10% de descuento. En el editor se
arma una tabla: si `dia_pago <= 5`, entonces `bonificacion = "10.00"` y `motivo = "pronto pago"`. El
núcleo recibe ese `"10.00"`, calcula el descuento con `Dinero` y lo registra.

## Las dos herramientas

| | Qué es | Dónde corre |
|---|---|---|
| **ZEN Engine** (`zen-engine`) | El motor: recibe datos y un grafo JDM, devuelve el resultado. Escrito en Rust, se usa desde Python | Dentro del backend, en `proptech_core` |
| **jdm-editor** (`@gorules/jdm-editor`) | El editor visual: una librería React para armar los grafos y exportarlos como JDM. Trae un simulador para probar con datos sueltos | En el frontend Next.js, área de administración |

## Qué cambia en la arquitectura

**Poco**, porque el puerto ya estaba decidido: lo que cambia es qué hay detrás.

| Pieza | Dónde | Qué es |
|---|---|---|
| Módulo `politicas` | `backend/src/proptech_core/politicas/` | Mismo formato que el resto (D-040): `dominio/`, `aplicacion/`, `puertos.py`, `adaptadores/` |
| Puerto `MotorDePoliticas` | `politicas/puertos.py` | Lo único que ven los demás módulos |
| Adaptador ZEN | `politicas/adaptadores/` | El único lugar que importa `zen-engine`. Si ZEN deja de convenir, se cambia el adaptador y nada más |
| Validador | `politicas/dominio/` | Nuestro. Revisa las reglas al guardarlas y cada respuesta del motor |
| Reglas por edificio | tabla nueva en la base | El JDM de cada regla, por edificio, con versión, fecha y autor |
| Editor | `web/`, área de administración | jdm-editor como componente de cliente. Exige `antd` 5.21.2 fijo |

**No se suma infraestructura**: ZEN corre dentro del proceso de Python, sin servicio ni contenedor
aparte.

**Lo que no cambia**: el núcleo financiero sigue en código con sus tests. Los intereses simples
(R03), la imputación (R04), los pagos parciales (R05), el reparto sin perder centavos (R07), la
cuenta corriente que sólo agrega movimientos (R08) y el aislamiento entre edificios (R10) **no pasan
al motor** (D-064).

## Los dos problemas de ZEN y cómo se manejan

La prueba del 12/10 encontró dos problemas. Siguen ahí: no los arregla nadie más que nosotros.

### 1. Usa `float`

El paquete de PyPI trabaja los números como `float`. Si una regla hace `monto * 0.90`, el resultado
sale con error de redondeo.

**Cómo se maneja: el motor decide, no calcula.**

- Las reglas devuelven **literales**: porcentajes y montos fijos como texto (`"10.00"`,
  `"20000.00"`), banderas y motivos. La prueba mostró que un literal de texto sale idéntico a como
  entró.
- **Ninguna regla hace una cuenta sobre un campo de plata.** El validador lo rechaza al guardar.
- Toda cuenta de plata la hace el núcleo con `Dinero` (D-046).
- Para **comparar** montos dentro de una regla (por ejemplo "si la deuda supera $100.000"), la
  propuesta es pasar el monto en **centavos enteros**: un `float` representa enteros exactos hasta
  2^53, muy por encima de cualquier monto real. *Pendiente: confirmarlo con una prueba en el
  explore del cambio 3.*

### 2. Saltea en silencio una regla con error

Si un dato llega con un tipo inesperado, ZEN no avisa: saltea esa fila de la tabla y aplica la
siguiente, o la regla por defecto. Puede terminar en una expensa mal cobrada sin que nadie lo note.

**Cómo se maneja: un validador propio en dos momentos.**

| Momento | Qué revisa | Si falla |
|---|---|---|
| **Al guardar** una regla | Que no haya cuentas sobre campos de plata; que las salidas tengan los campos y tipos del contrato; que la regla por defecto no devuelva un campo de entrada sin validar | No se guarda, y el editor dice qué está mal |
| **Al evaluar** en la liquidación | Que la respuesta cumpla el contrato: campos presentes, tipos correctos, montos legibles con `Dinero`, no vacía | **Bloquea la emisión** con una alerta que dice qué regla y qué unidad. Nunca se toma como "no hay regla" |

Además, el núcleo arma los datos de entrada con tipos fijos antes de llamar al motor, así ZEN nunca
recibe un tipo inesperado.

## El contrato: hechos adentro, propuestas afuera

```
hechos (los arma el núcleo)            respuesta del motor (sólo literales)
edificio, período                      { "aplica": true,
unidad, estado de la unidad              "tipo": "bonificacion",
dia_pago: 3                              "porcentaje": "10.00",
deuda_centavos: 7630042                  "motivo": "pago el día 3, límite día 5" }
periodos_vencidos: 0
```

1. El núcleo arma los datos del mes de cada unidad, con tipos fijos.
2. El motor evalúa las reglas activas del edificio y devuelve decisiones.
3. El validador revisa la respuesta.
4. El núcleo calcula los montos con `Dinero` y los registra como movimientos, con un motivo que dice
   qué regla y qué versión los generó.

Reglas del contrato:

- Los datos de entrada salen siempre del núcleo, **nunca de la salida de otra regla**.
- **Toda respuesta trae su motivo** (R08).
- Una respuesta fuera de contrato es **un fallo**, nunca "no aplica".

## Qué reglas pasan por el motor en el MVP

| Regla | Qué decide el motor | Qué calcula el núcleo | Cambio |
|---|---|---|---|
| Intereses por mora | Tasa y días de gracia que corresponden | El interés simple (R03) | 3 |
| Fondo de reserva | Porcentaje sobre la ordinaria | El monto (R15) | 3 |
| Cargo por estado de la unidad | Factor y cargo fijo por estado. Apagada en edificios (D-030) | El cargo (R02) | 3 |
| Alertas antes de emitir | Qué controles bloquean y cuáles sólo avisan | Ejecuta los controles | 7 |
| Bonificación por pronto pago | Si aplica y qué porcentaje. Apagada por defecto | El descuento | 7 |
| Cargo recurrente del reglamento | Concepto, monto fijo y a qué unidades (ej.: canon por cochera) | El movimiento | 7 |
| Moroso crítico | Si una unidad lo es, según cuántas liquidaciones vencidas tiene | Nada: es una marca (R20) | 10 |

**Fuera del MVP**: bloqueo de amenities a morosos, planes de pago y multas con escalas o
reincidencia. Con el motor ya instalado, se suman como reglas nuevas en el editor, siempre que
respeten el contrato.

## Versiones y auditoría

- Cada vez que se guarda una regla de un edificio queda una **versión nueva** con fecha y autor. Las
  viejas no se editan.
- **Cada liquidación guarda qué versión de cada regla usó.** Si en abril el descuento pasa del 10% al
  15%, la expensa de marzo se sigue explicando con el 10% (misma garantía que D-010).
- El motivo de cada movimiento (R08) dice qué regla y qué versión lo generó: no hace falta una tabla
  de auditoría aparte.
- Las reglas son datos del edificio: se leen con el mismo aislamiento por identidad y Row-Level
  Security (R10). Cada evaluación de ZEN es una llamada aislada, sin estado compartido.

## Antes de activar una regla

- **Simulador del editor**: prueba la regla con datos sueltos, ya viene con jdm-editor.
- **Repetir el mes pasado** (lo construimos nosotros): correr la regla nueva contra los datos reales
  de la última liquidación del edificio y mostrar la diferencia con lo que se cobró, sin tocar ningún
  movimiento.
- La **preliquidación** muestra, línea por línea, qué regla generó cada cargo o bonificación.

## Quién usa el editor

*Pendiente.* Propuesta para el MVP: **sólo el equipo de PropTech**, configurando las reglas por el
administrador. Una regla mal dibujada le cobra mal a todo un edificio, y el editor permite armar
cosas que el validador tiene que atajar. Abrírselo al titular se decide después, con experiencia
real.

## Qué tan difícil es

- **Instalar ZEN y el editor es fácil**: el demo de Alberto ya muestra cómo se conectan.
- **Lo difícil es lo que el demo no tiene**: el validador, las reglas en la base por edificio con
  versiones, y repetir el mes pasado. Eso es todo nuestro.
- **El riesgo es confiar en el editor.** Que dibujar una regla sea fácil no la hace correcta. El
  validador y la prueba contra el mes pasado no son opcionales.

## Dónde entra en el roadmap

No es un cambio aparte; se reparte en tres que ya existen. Las fichas de `roadmap.md` se actualizan
en el propose de cada uno.

| Cambio | Qué agrega |
|---|---|
| 3 · `configuracion-del-edificio` | El módulo `politicas`, el puerto, el adaptador ZEN, el validador, las reglas versionadas en la base, el editor en el frontend y las reglas de intereses, fondo de reserva y cargo por estado |
| 7 · `liquidacion-y-emision` | La liquidación consulta el puerto y guarda las versiones usadas; alertas antes de emitir, bonificación por pronto pago y cargo recurrente; repetir el mes pasado; la preliquidación muestra qué regla generó cada línea |
| 10 · `morosidad` | La regla de moroso crítico |

## Pendiente

- [ ] Confirmar con una prueba que los montos en centavos enteros se comparan sin error dentro de
  ZEN (explore del cambio 3).
- [ ] Bajar y revisar el código del demo BRE (backend y frontend) antes del explore del cambio 3.
- [ ] Decidir quién usa el editor en el MVP.
- [ ] Probar jdm-editor dentro de Next.js con `antd` 5.21.2.
