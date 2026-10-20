# Motor de reglas

Cómo entra al sistema el reglamento propio de cada edificio sin programar un edificio por vez.
**Se reescribe** cuando cambia el diseño; el porqué de cada cambio va a `09_decisiones_y_supuestos.md`.

## Estado

- **Puerto de políticas** (D-064): decidido.
- **Corrección del 13/10** (D-067): ZEN calcula con decimales exactos; lo que había que cuidar no era
  el `float` sino las tablas que caen en silencio.
- **GoRules ZEN + editor visual jdm-editor detrás del puerto, con validador propio** (D-066):
  decidido el 12/10, a pedido de Alberto. Reemplaza al motor propio de plantillas (D-065).
- Todavía **no se escribe código** del motor. Los detalles abiertos se cierran en el explore del
  cambio 6b (D-087).
- Fuentes: `openspec/exploraciones/2026-10-12-motor-de-reglas.md` (prueba de GoRules con montos
  reales) y el demo BRE que pasó Alberto (FastAPI + ZEN, React + jdm-editor; fuera del repositorio).

## La idea en una línea

Las reglas de cada edificio se **dibujan** en un editor visual como un grafo (entrada, tabla de
decisión, salida), se guardan como JSON (formato JDM) y el motor ZEN las ejecuta cuando se arma la
liquidación. El motor **decide y puede calcular**, devolviendo la plata como texto; el núcleo
**redondea y registra**.

Ejemplo: el reglamento dice que quien paga hasta el día 5 inclusive tiene 10% de descuento. En el editor se
arma una tabla: si `dia_pago <= 5`, entonces `bonificacion = "10.00"` y `motivo = "pronto pago"`. El
núcleo recibe ese `"10.00"`, calcula el descuento y lo registra.

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
cuenta corriente que sólo agrega movimientos (R08) y el aislamiento entre administraciones (R10) **no pasan
al motor** (D-064).

## Lo que hace bien ZEN y lo que no

Prueba del 13/10 con `zen-engine` 2.1.3 (corrige lo que decía la prueba del 12/10; D-067).

### Los números: calcula con decimales exactos

```
0.1 + 0.2                                  -> 0.3     (Python con float da 0.30000000000000004)
1.1 * 1.1                                  -> 1.21    (Python con float da 1.2100000000000002)
string(number("100") / 3)                  -> "33.333333333333333333333333333"
string(number("999999999999.99") * 1.05)   -> "1049999999999.9895"
number("SECRETO-123") * 0.9                -> error (no sigue en silencio)
```

ZEN **calcula por dentro con decimales exactos**. El `float` aparece sólo al devolver un número a
Python. Por eso:

- **Una regla puede calcular**, siempre que devuelva el resultado **como texto con `string(...)`**.
  El validador rechaza al guardar cualquier salida de plata que no sea texto.
- **El redondeo al centavo nunca lo hace el motor.** El núcleo lo aplica una sola vez, al registrar,
  con el modo de R07 (pendiente, P10). Así `"86.4192"` llega entero y el núcleo decide cómo queda.
- Los montos entran al motor como texto y la regla los convierte con `number(...)`. Una conversión
  imposible tira error, y el error bloquea la emisión.

### Las tablas de decisión: caen en silencio a la fila por defecto

```
tabla dia_pago <= 5 -> "10.00", si no -> "0.00"
{"dia_pago": 3}     -> "10.00"
{"dia_pago": "3"}   -> "0.00"   (texto en vez de número: no avisa)
{}                  -> "0.00"   (falta el dato: no avisa)
```

Es el riesgo real de ZEN: un dato mal tipado o ausente hace que la tabla elija la fila por defecto,
sin error. Se maneja con tres capas (R33):

1. **El núcleo arma los datos de entrada con tipos fijos** y verifica que estén todos antes de
   llamar al motor. ZEN nunca recibe un tipo inesperado ni un dato faltante.
2. **Validador al guardar**: salidas con los campos y tipos del contrato; plata siempre como texto;
   la fila por defecto no devuelve un campo de entrada sin validar.
3. **Validador al evaluar**: campos presentes, tipos correctos, montos legibles, respuesta no vacía.
   Si falla, **bloquea la emisión** con una alerta que dice qué regla y qué unidad. Nunca se toma
   como "no hay regla".

## El contrato: hechos adentro, propuestas afuera

```
hechos (los arma el núcleo)            respuesta del motor
edificio, período                      { "aplica": true,
unidad, estado de la unidad              "tipo": "bonificacion",
dia_pago: 3                              "porcentaje": "10.00",
periodos_vencidos: 0                     "motivo": "pago el día 3, límite día 5" }
```

1. El núcleo arma los datos del mes de cada unidad, con tipos fijos y completos.
2. El motor evalúa las reglas activas del edificio.
3. El validador revisa la respuesta.
4. El núcleo redondea al centavo (R07) y registra cada movimiento con un motivo que dice qué regla y
   qué versión lo generó.

Con qué dato se evalúa la bonificación (D-085): **al emitir** (cambio 7), con `dia_pago` igual al día
límite, para calcular el importe con descuento que muestra el PDF; **al confirmar un pago** (cambio
8), con el día de la transferencia. El motor devuelve el **porcentaje** como texto y el núcleo calcula
el monto sobre la ordinaria prorrateada (R37) y lo redondea. Así ningún dato falta al emitir (R33).

Reglas del contrato:

- Los datos de entrada salen siempre del núcleo, **nunca de la salida de otra regla**.
- **Toda respuesta trae su motivo** (R08).
- **Toda plata sale como texto**; nunca un número.
- Una respuesta fuera de contrato es **un fallo**, nunca "no aplica".

## Qué reglas pasan por el motor en el MVP

| Regla | Qué decide el motor | Qué hace el núcleo | Cambio |
|---|---|---|---|
| Alertas antes de emitir | Controles propios del edificio que se suman a los de R34, o subir una advertencia a bloqueante. Nunca bajar un bloqueante de R34 (D-078) | Ejecuta los controles | 6b |
| Bonificación por pronto pago *(propuesta, R37)* | Si aplica y qué porcentaje. Apagada por defecto | En el 7 calcula el importe con descuento para el PDF; en el 8, al confirmar el pago, registra la bonificación (R37, D-080) | 6b (antes, código simple en el 7 y el 8) |
| Cargo recurrente del reglamento *(propuesta, R14)* | Concepto, monto fijo y a qué unidades (ej.: canon por cochera) | El movimiento | 6b (antes, código simple en el 7) |

**Los intereses, el fondo de reserva y el cargo por estado no pasan por el motor** (D-080): son menús
cerrados de la configuración del edificio (R03, R15, R02, D-010), con su versión en cada liquidación.
El motor queda para las reglas propias de cada edificio.

**El moroso crítico no pasa por el motor**: R20 lo define fijo (dos o más liquidaciones vencidas con
saldo) y lo calcula una función pura del cambio 4 sobre el libro (D-074).

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

*Pendiente, a acordar con Alberto.* Propuesta para el MVP, en dos niveles:

| Qué se toca | Quién | Por qué |
|---|---|---|
| **Valores** de una regla que ya existe: días, porcentajes, montos fijos | El super admin (antes, titular) | Es lo que cambia en una asamblea (por ejemplo, la bonificación pasa del 10% al 15%). La tasa de interés no está acá: es un menú de configuración (D-080). Cambiar un número en una tabla probada es de bajo riesgo, y el validador lo revisa igual |
| **Estructura** de una regla: condiciones, nodos, salidas, reglas nuevas | El equipo de PropTech | Una regla mal dibujada le cobra mal a todo un edificio, y el editor permite armar cosas que el validador tiene que atajar |

Falta verificar si jdm-editor permite un modo "sólo valores". Si no lo permite, los valores se
cambian desde un formulario propio que reescribe la tabla.

## Qué tan difícil es

- **Instalar ZEN y el editor es fácil**: el demo de Alberto ya muestra cómo se conectan.
- **Lo difícil es lo que el demo no tiene**: el validador, las reglas en la base por edificio con
  versiones, y repetir el mes pasado. Eso es todo nuestro.
- **El riesgo es confiar en el editor.** Que dibujar una regla sea fácil no la hace correcta. El
  validador y la prueba contra el mes pasado no son opcionales.

## Dónde entra en el roadmap

Tiene un cambio propio, el 6b, **después del 7 y el 8 y fuera del camino a M1** (D-087, D-089): ninguna
regla vigente pasa por el motor. Si R37 o R14 se validan antes, el 7 y el 8 las construyen como código
simple y el 6b las migra al motor.

| Cambio | Qué agrega |
|---|---|
| 6b · `motor-de-reglas` (después del 8) | El módulo `politicas`, el puerto, el adaptador ZEN, el validador, las reglas versionadas en la base, el editor en el frontend y el mecanismo de "repetir el mes pasado" contra datos de prueba; migra las reglas que el 7 y el 8 construyeron como código simple y suma los controles propios |
| 7 · `liquidacion-y-emision` | Sin motor. Si se validan, el importe con descuento de la bonificación y el cargo recurrente como código simple |
| 8 · `pagos-informados` | Sin motor. Si se valida R37, registra la bonificación al confirmar el pago, como código simple |

## Pendiente

- [ ] Bajar y revisar el código del demo BRE (backend y frontend) antes del explore del cambio 6b.
- [ ] Acordar con Alberto quién usa el editor: valores para el super admin, estructura para el equipo (P22 sigue abierta).
- [ ] Confirmar en gorules.io que el copiloto de IA y el servidor MCP son de la plataforma paga y no
  de las librerías libres (la investigación del 13/10 dice que sí, desde unos €500 por mes).
- [ ] Probar jdm-editor dentro de Next.js con `antd` 5.21.2 y React 19.3: nadie verificó que sean
  compatibles. Si no lo son, hay que elegir entre bajar React o subir `antd`.
