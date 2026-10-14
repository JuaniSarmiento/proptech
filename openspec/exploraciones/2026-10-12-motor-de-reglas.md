# Exploración: motor de reglas de negocio (enfoque híbrido)

> **Aviso (13/10)**: lo que esta exploración dice sobre que ZEN "usa float" quedó corregido por D-067:
> ZEN calcula con decimales exactos; el riesgo real son las tablas que caen en silencio. El diseño
> vigente está en `conocimiento/motor-de-reglas.md`.

> Explore mode. No se escribió código ni se tocó `conocimiento/`. Lo que sigue son hallazgos y
> una propuesta de diseño para que Juani decida; nada de esto es una decisión tomada.

**Fecha**: 12/10/2026
**Disparador**: D-054 ("después se investiga el motor de reglas de negocio que pidió Alberto y
cómo integrarlo"). Responde también a la propuesta de Alberto en
`especificacion/documentos-alberto/motor-de-reglas.md`.

**Fuentes leídas del repo**: `conocimiento/reglas-de-negocio.md` (R01 a R16), `decisiones.md`
(D-010, D-014, D-021, D-040, D-046, D-054 completo), `forma-de-trabajo.md`, `lecciones.md` (L-002,
L-007, L-008, L-009), `openspec/changes/archive/2026-10-11-arranque-del-sistema/design.md` (tipo
`Dinero`, `parametros.yaml`), `especificacion/documentos-alberto/motor-de-reglas.md` (propuesta de
Alberto), partes de `especificacion/documentos-alberto/ProTecc_problemas_y_reglas_v3.5.md` (12.5
control antes de emitir, 12.6 plan de pago, M1 moroso crítico, DEC-07/DEC-08 amenities), y
`openspec/exploraciones/2026-10-12-dolores-protecc.md` (clasificación de los 42 casos contra el
MVP, hecha en la primera mitad de D-054).

**Fuentes externas**: PyPI (`zen-engine`, `business-rule-engine`), GitHub API (`gorules/zen`,
`gorules/jdm-editor`, `MAIF/arta`), npm registry (`@gorules/jdm-editor`), docs.gorules.io. Fechas
de consulta: 12/10/2026 (todas). No se usó WebSearch (presupuesto agotado); todo salió de
WebFetch y `curl` a APIs oficiales.

---

## 0. El punto de partida: qué pide el enfoque híbrido

Juani ya aprobó la forma, no sólo la herramienta:

- **El core financiero sigue en código con tests**: R03 (interés), R04 (orden de imputación),
  R05/R06 (parciales, saldo arrastrado), R07 (redondeo por mayor resto), R08 (libro de sólo
  agregar), R10 (aislamiento). Nada de esto se mueve a un motor de reglas.
- **Al motor sólo van las políticas por edificio**: recargos del reglamento, descuentos por pago
  temprano, bloqueo de amenities para morosos críticos, la definición de "moroso crítico",
  bloqueante vs advertencia en el control antes de emitir, canon de obra y cargos por estado de
  unidad.
- **Regla de oro**: el motor decide **qué** cobrar o descontar; el core decide **cómo** se
  registra. Todo lo que el motor devuelve se convierte en un movimiento de la cuenta corriente con
  motivo (R08); el motor nunca escribe plata por sí mismo.

Esto importa para leer todo lo que sigue: cualquier opción que mezcle "decidir" con "calcular"
(como hace la propuesta de Alberto, ver sección 2) queda descartada de entrada, no por ser mala
herramienta sino por romper la regla de oro.

---

## 1. GoRules ZEN (`zen-engine`)

### 1.1 Qué es

Motor de reglas de negocio de código abierto, escrito en Rust, con el formato **JDM** (JSON
Decision Model): un grafo de nodos (`inputNode`, `decisionTableNode`, `outputNode`, también
`switchNode`, `expressionNode`, `functionNode`) conectado por `edges`, serializado como JSON
versionable. La idea de GoRules es "lógica de negocio que una persona puede leer y una máquina
puede correr".

- **Licencia**: MIT, confirmada en `https://api.github.com/repos/gorules/zen` (campo `license`) y
  en el `package.json` de `@gorules/jdm-editor` en el registro de npm. Sin costo de licencia, en
  línea con el criterio general del proyecto (D-043).
- **Repositorio**: `github.com/gorules/zen`. 2056 estrellas, 616 commits, `pushed_at`
  2026-10-09 (consultado 12/10/2026 vía API de GitHub): mantenido activamente, no abandonado.
- **Bindings**: Node.js, Python, Go, Java, Kotlin, .NET, más Swift (iOS) y Android (AAR), y
  WASM/WASI. El paquete Python se llama `zen-engine` en PyPI, versión instalada en el spike:
  **2.1.3** (requiere Python >=3.7; el proyecto usa 3.14, sin problema).
- **Editor**: `@gorules/jdm-editor`, componente React embebible (npm, versión 1.52.0, licencia
  MIT, `peerDependencies: react >= 18, react-dom >= 18`), compatible con Next.js (D-036). También
  existe un editor standalone autohospedable por Docker (`docker run -p 3000:3000 gorules/editor`)
  con **simulador incorporado**: "Built-in simulator - Test rules with sample data and view
  execution traces" (docs.gorules.io/developers/jdm/standalone-editor, 12/10/2026). No encontré
  mención de replay por lotes/histórico en esa página; el simulador es para casos sueltos.

### 1.2 Números: el hallazgo que más importa para nosotros

El README del repo (vía WebFetch, 12/10/2026) dice textualmente que **"la versión 2.0 quitó la
precisión arbitraria como default (aunque sigue disponible por feature flag)"**. Eso ya es una
alerta: el *paquete de PyPI* es un binario prearmado (wheel con extensión Rust); activar ese
feature flag significaría compilar nosotros mismos con `maturin` desde el código fuente, no
instalar `zen-engine` de PyPI. Nadie en el repo tiene hoy esa necesidad de build, así que en la
práctica **el paquete que instalamos usa `f64` (float de 64 bits) para los números del JSON**, lo
confirmé en el spike (sección 3). Esto es incompatible de raíz con D-046 (`Decimal`, nunca
`float`) si se usara el motor para *calcular* plata. Confirma por otra vía la regla de oro: el
motor no puede ser responsable de ninguna cuenta.

### 1.3 Formato JDM, con ejemplo real

Bajé el ejemplo oficial del repo (`test-data/table.json`, rama `master`, 12/10/2026) para no
adivinar el esquema:

```json
{
  "nodes": [
    { "id": "...", "type": "inputNode", "name": "Request", "position": {...} },
    {
      "id": "...", "type": "decisionTableNode", "name": "Hello", "position": {...},
      "content": {
        "hitPolicy": "first",
        "inputs":  [{ "field": "input",  "id": "xWauegxfG7", "name": "Input",  "type": "expression" }],
        "outputs": [{ "field": "output", "id": "qGAHmak0xj", "name": "Output", "type": "expression" }],
        "rules": [
          { "_id": "...", "xWauegxfG7": "> 10", "qGAHmak0xj": "10" },
          { "_id": "...", "xWauegxfG7": "",     "qGAHmak0xj": "0" }
        ]
      }
    },
    { "id": "...", "type": "outputNode", "name": "Response", "position": {...} }
  ],
  "edges": [ { "id": "...", "sourceId": "...", "type": "edge", "targetId": "..." }, ... ]
}
```

Cada columna de la tabla de decisión es un `id` (clave en `rules`), con un `field` (la ruta al
dato de entrada o de salida) y una condición en el lenguaje de expresiones ZEN: comparación
(`> 10`), rango (`[1..10]`), texto exacto (`'gold'`) o vacío (`""`, matchea cualquier valor).
`hitPolicy` puede ser `"first"` (la primera regla que matchea) o `"collect"` (todas las que
matchean).

### 1.4 API en Python

```python
from zen import ZenEngine
engine = ZenEngine()
decision = engine.create_decision(grafo_jdm)        # sincrónico
resultado = decision.evaluate(payload)               # -> {"performance": "...", "result": {...}}
resultado = decision.evaluate(payload, {"trace": True})  # agrega "trace" con el detalle por nodo
# Carga: static (en memoria), fs (directorio), zip, o un callback propio (custom loader)
# Async: engine.async_evaluate(key, context); batch: engine.evaluate_batch([...])
```

No encontré en la documentación oficial (ni la pude confirmar con el spike salvo lo que sigue)
una forma explícita de pasar `Decimal` como input: lo intenté y falla (sección 3.1).

---

## 2. El spike (en `/tmp/.../scratchpad/spike-zen/`, corrido con `uv run --with zen-engine python ...`)

Instalación limpia con `uv`:

```
$ uv run --with zen-engine python spike.py
Downloading zen-engine (10.2MiB)
Installed 1 package in 5ms
zen-engine version instalada: 2.1.3
```

### 3.1 Dinero como texto vs número, y `Decimal` nativo

Tabla de decisión: columna `dia_pago` (regla: `<= 5` → descuento) y columna `monto` (sin
condición), con salidas `monto_con_descuento`, `porcentaje_aplicado`, `motivo`.

| Entrada | `monto_con_descuento` | tipo Python | ¿Qué pasó? |
|---|---|---|---|
| `monto="76300.42"` (texto), `dia_pago=3` | `"76300.42"` | `str` | **No aplicó el descuento.** Matcheó la regla *default*, no la de `dia<=5`. |
| `monto=76300.42` (float), `dia_pago=3` | `68670.378` | `float` | Aplicó el descuento con aritmética float. |
| `monto=Decimal("76300.42")`, `dia_pago=3` | no aplica | no aplica | `TypeError: argument 'ctx': unsupported type Decimal` (el binding Python no acepta `Decimal`, hay que pasar `str` o un número JSON). |

### 3.2 El hallazgo crítico: la regla se salta en silencio, sin ningún error

Esto no es "el motor convierte mal el texto": es más grave. Aislé la causa con cuatro scripts
(`spike2.py`, `minimal.py`, `minimal2.py`, `bisect.py`, `bisect2.py` en el spike):

- Con **una sola columna de salida** y contenido puramente literal (`'descuento'` / `'sin_descuento'`),
  la tabla matchea bien la condición `dia_pago <= 5` **sin importar el tipo de `monto`** (ni
  siquiera tiene que estar presente).
- En cuanto **alguna** columna de salida de la regla candidata contiene una expresión que no se
  puede evaluar para el tipo recibido (`monto * 0.90` cuando `monto` es `str`), **la tabla entera
  deja de considerar esa regla como matcheada y sigue a la siguiente (hit policy `first`),
  sin levantar ninguna excepción en Python y sin ningún campo de error en el resultado.**
  Confirmado con `trace: True`: el `traceData.rule` muestra explícitamente que se eligió la regla
  *default* (`r2`), no la de la condición cumplida (`r1`).

Reproducción mínima (`bisect2.py`, caso D, `field="motivo"` para no confundir con el nombre del
campo, aritmética en la regla 1):

```
D: field=motivo, aritmetica con monto (nombre no choca) | monto=string -> {'motivo': '76300.42'}
D: field=motivo, aritmetica con monto (nombre no choca) | monto=float  -> {'motivo': 68670.378}
```

Con **tres** columnas de salida (como en el caso real, `descuento.json`), con trace:

```
string -> result: {'monto_con_descuento': '76300.42', 'porcentaje_aplicado': 0, 'motivo': 'sin_descuento'}
   regla elegida (traceData.rule): {'_id': 'r2', 'dia_pago[col_dia]': '', 'monto[col_monto]': ''}
float  -> result: {'monto_con_descuento': 68670.378, 'porcentaje_aplicado': 10, 'motivo': 'descuento_pago_temprano'}
   regla elegida (traceData.rule): {'_id': 'r1', 'monto[col_monto]': '', 'dia_pago[col_dia]': '<= 5'}
```

**Por qué importa**: si una política por edificio tiene un error de tipeo (un campo de dinero que
llega como texto y una regla que intenta multiplicarlo sin convertir), el sistema no explota ni
avisa: **cae en silencio a la regla por defecto**, que en nuestro diseño normalmente es "no
corresponde descuento/recargo". Es el peor tipo de falla posible en un sistema de plata: no hace
nada raro, simplemente no hace lo que el reglamento dice, y nadie se entera salvo auditando a
mano. Esto es, en el lenguaje de `lecciones.md`, una familia nueva (candidata a L-0XX si en algún
momento este motor entra en construcción): *"un tipo de dato equivocado dentro de una expresión no
levanta error: hace que la regla se salga de la tabla de decisión sin avisar"*.

### 3.3 El patrón seguro: literales de texto, nunca aritmética

Cuando las salidas son **literales de texto ya formateados como `Dinero`** (sin ninguna
operación), el motor los devuelve exactos, sin tocarlos:

```
estado='en_obra'  -> {'canon_obra': '20000.00', 'motivo': 'canon_de_obra'} (tipo: str)
estado='habitado' -> {'canon_obra': '0.00',     'motivo': 'sin_cargo'}     (tipo: str)
```

Esto es justo lo que permite la regla de oro: el motor elige **cuál** importe/porcentaje/bandera
corresponde (comparando `estado_unidad` contra texto), nunca calcula nada. El texto `"20000.00"`
sale idéntico al que entra en la regla, listo para que `Dinero("20000.00")` lo parsee en el core.

Con `number(monto) * 0.90` (la forma "correcta" de convertir texto a número en el lenguaje ZEN)
sobre `"76300.42"` sí aplica el descuento (`68670.378`), pero **vuelve a ser un `float` de
Python**, no algo compatible con `Decimal`. Y con un texto corrupto `"SECRETO-ABC-123"` que
`number()` no puede convertir, **tampoco hay excepción**: la tabla cae otra vez a la regla
default, cuya salida en ese caso particular era un passthrough (`monto` tal cual), así que el
valor corrupto aparece igual en el resultado, no por una fuga en un mensaje de error (L-007) sino
porque la regla por defecto lo repite sin querer. Dos caminos distintos al mismo problema: nunca
hacer aritmética en el motor, y nunca usar un passthrough de un campo sin validar antes de
pasarlo.

### 3.4 Precisión float "a secas" (sin erial visible, pero igual prohibida)

```
0.1 + 0.2                     -> 0.3        (float)
76300.42 * 0.10                -> 7630.042   (float)
number('76300.42') * 0.10      -> 7630.042   (float)
76300.42 * 0.90                -> 68670.378  (float)
```

Ninguno de estos casos mostró el artefacto clásico (`7630.0420000001`), pero **eso es suerte del
valor elegido, no una garantía**: siguen siendo `float` de Python (`type()` lo confirma), y D-046
prohíbe `float` para plata sin excepción, independientemente de si en un caso puntual "se ve
bien". No hay forma de hacer que esto sea seguro salvo no calculando plata ahí.

### 3.5 Errores que SÍ son visibles (para contraste)

- Grafo con un `edge` que apunta a un nodo inexistente: **sí** levanta una excepción clara,
  `RuntimeError: {"type":"InvalidGraph","source":{"type":"missingNode","nodeId":"..."}}`. Los
  errores de **estructura** del grafo (no del contenido de una expresión) se detectan bien.
- Una expresión con error de sintaxis (`"x +"`, incompleta) **no** levanta excepción ni al crear
  la decisión ni al evaluarla: el resultado es simplemente `{}` (vacío), sin ningún campo. Mismo
  patrón que 3.2: una falla de autoría se traduce en "no pasó nada" en lugar de un error.

**Conclusión del spike, en una frase**: ZEN es rápido, bien tipado para texto/estructura, y el
patrón de literales-de-texto es seguro para dinero; pero el motor **no avisa de los errores de
contenido de una regla** (tipos que no combinan, sintaxis rota): los convierte en "esta regla no
aplicó" sin ningún rastro salvo el trace explícito. Cualquier integración tiene que asumir que el
motor puede fallar en silencio y diseñar la validación de contrato (sección 5) pensando en eso,
no como algo opcional.

---

## 3. Alternativas

### 3.1 Arta (MAIF, Apache-2.0)

`github.com/MAIF/arta`, Python puro, "A Python Rules Engine - Make rule handling simple". Datos de
`https://api.github.com/repos/MAIF/arta` (12/10/2026): licencia Apache-2.0, 67 estrellas,
`pushed_at` 2026-05-01, no archivado. Las reglas se escriben en YAML (no JSON ni visual), evaluadas
contra un contexto Python. Más chico y mucho menos usado que ZEN (67 vs 2056 estrellas), sin editor
visual embebible, sin bindings para otros lenguajes (no hace falta, pero tampoco suma nada que ZEN
no tenga). No encontré evidencia de que maneje números de forma distinta a Python nativo (es
Python puro, así que en principio podría usar `Decimal` si uno programa las reglas para eso, a
diferencia de ZEN que fija `f64`). Candidato razonable si se quisiera **evitar la dependencia en
Rust/bindings nativos** y aceptar que las reglas se escriben en YAML en vez de visualmente, pero no
trae nada que resuelva mejor nuestro problema específico (reglas simples de selección, no cálculo).

### 3.2 `business-rule-engine` / `business-rules` (Python)

- `business-rule-engine` (PyPI, MIT, última versión 1.0.0): "Python DSL for setting up business
  intelligence rules". Es una gramática propia para reglas tipo `if-then` en texto plano.
- `business-rules` (la de Venmo, PyPI, última versión 1.1.1): generador de reglas también en
  Python, pensado para condiciones sobre atributos de un objeto.

Ninguna de las dos tiene editor visual, ninguna está pensada para multi-tenant con reglas por
edificio versionadas, y la segunda lleva varios años sin una release mayor (último salto real fue
2021 según el historial de versiones). Sirven para "DSL propio en Python", pero si vamos a escribir
igual nuestro propio puerto y contrato (sección 5), no justifican la dependencia externa frente a
seguir con `parametros.yaml` + un validador propio (la opción 3.3).

### 3.3 DSL propio sobre `parametros.yaml` (lo que ya hacemos)

D-010 (intereses) y D-014 (estado de unidad) ya resuelven "variabilidad por edificio" sin ningún
motor: un **menú cerrado** de opciones en `parametros.yaml`/la configuración del edificio, validado
con pydantic estricto, nunca una fórmula libre. Es el patrón más barato, el más testeable (un test
por combinación posible, acotada) y el que ya pasó por tres vueltas de rompedor/auditor (D-051 a
D-053) sin encontrarle agujeros de ese estilo. Su límite es que **no escala a reglas realmente
abiertas**: "si el reglamento del consorcio permite bloquear amenities y el vecino tiene 2+
períodos vencidos" es todavía un menú cerrado razonable (un booleano + un umbral), pero "recargo
del 50% si está en obra hace más de 12 meses Y el metraje supera los 400m²" ya es una combinación
de condiciones que un YAML de configuración plano empieza a modelar mal (necesitaría su propio
mini-lenguaje de condiciones, que es exactamente lo que ZEN ya resuelve).

### 3.4 Tabla comparativa

| | GoRules ZEN | Arta (MAIF) | business-rule(s) (Python) | DSL propio / `parametros.yaml` |
|---|---|---|---|---|
| Licencia | MIT | Apache-2.0 | MIT | no aplica (nuestro) |
| Mantenimiento | Activo, 2056★, commit 09/10/2026 | Activo, 67★, commit 05/2026 | `business-rules` casi sin releases desde 2021 | Nosotros |
| Formato de reglas | JSON (JDM), visual o texto | YAML | Python / texto propio | YAML cerrado |
| Editor visual embebible | Sí (`@gorules/jdm-editor`, MIT, React) | No | No | No (formulario propio, a construir) |
| Simulación antes de activar | Sí (editor standalone con Docker) | No | No | A construir |
| Números para dinero | `f64` (float); `Decimal` nativo de Python no se puede pasar | Python nativo (podría usar `Decimal` si se programa así) | Python nativo | `Decimal` (ya lo tenemos) |
| Errores de tipo/sintaxis en una regla | **Silenciosos** (cae a la regla default, sin excepción) | No investigado en este spike | No investigado | Lo que nosotros programemos (pydantic ya es explícito, L-002) |
| Condiciones complejas (rangos, AND/OR) | Sí, nativo | Sí (Python) | Sí (Python) | Limitado, requiere ampliar el esquema a mano |
| Multi-tenant / versionado de reglas | No lo trae; hay que construirlo (sección 5) | No lo trae | No lo trae | Ya tenemos el patrón (D-010: "cada liquidación guarda la configuración usada") |
| Costo de aprender/operar | Medio (JDM + lenguaje de expresiones + editor) | Bajo (YAML + Python) | Bajo | Ya lo sabemos |

---

## 4. Diseño propuesto para PropTech

### 4.1 Dónde vive

Un módulo/puerto nuevo, siguiendo D-021/D-040: `proptech_core/politicas/`, con `dominio/`
(contratos puros, sin ZEN), `aplicacion/` (casos de uso: "evaluar políticas de un edificio para
una liquidación"), `puertos.py` (interfaz `MotorDePoliticas`) y `adaptadores/` (uno
`adaptador_zen.py` con `zen-engine`, intercambiable). Ningún otro módulo importa `zen` directamente;
sólo habla con el puerto. Si el día de mañana ZEN deja de convenir, se cambia el adaptador, no el
dominio.

### 4.2 El contrato: hechos adentro, acciones propuestas afuera, todo en texto

```
entrada (hechos)                       salida (acciones propuestas)
────────────────────────               ─────────────────────────────
edificio_id, periodo                   [
estado_unidad: "en_obra"                 { "tipo": "cargo_fijo", "concepto": "canon_de_obra",
dias_de_atraso_pago: 3                      "monto": "20000.00", "motivo": "estado=en_obra" },
periodos_vencidos: 0                     { "tipo": "descuento", "concepto": "pago_temprano",
monto_base: "76300.42" (texto)              "porcentaje": "10.00", "motivo": "dia<=5" }
...                                     ]
```

- **Los hechos nunca incluyen un monto ya calculado por una regla anterior**: cada evaluación es
  independiente, siempre a partir de datos del core (estado de la unidad, antigüedad de la deuda,
  fecha de pago), nunca encadenando una salida del motor como entrada de otra regla.
- **Toda acción propuesta trae su motivo** (igual que R08 exige motivo para cada movimiento). El
  core nunca inventa un motivo: lo toma literal de lo que devolvió la política.
- **Las reglas sólo devuelven literales de texto** (montos ya formateados como `"20000.00"`,
  porcentajes como `"10.00"`, banderas como `true`/`false`, o `motivo` como texto fijo). Nunca una
  expresión aritmética sobre un campo de dinero (sección 3.2/3.3). Esto se impone con una
  convención de autoría, no con algo que ZEN obligue solo: hace falta un validador propio.
- **El core valida el contrato de salida antes de tocar la cuenta corriente**: cada acción
  propuesta se parsea con `Dinero(texto)` (que ya rechaza lo que no sea texto bien formado,
  D-053); si algo no cumple el esquema esperado (falta un campo, un tipo no es el declarado, el
  resultado viene vacío como en 3.5), **se trata como fallo del motor, nunca como "no hay
  política"**: bloquea la emisión con alerta (como el resto de los bloqueos de 12.5 de Alberto),
  no sigue en silencio. Esto es la defensa concreta contra el hallazgo de 3.2: el motor puede
  fallar en silencio, así que el core es el que *no* puede.

### 4.3 Versionado por edificio

Mismo patrón que D-010 ("cada liquidación guarda la configuración con la que se calculó"): cada
edificio tiene un conjunto de políticas activo, identificado con una versión (podría ser tan simple
como un hash del JDM + un número incremental). **Cada liquidación guarda qué versión de las
políticas usó**, igual que guarda la tasa de interés vigente en ese momento. Cambiar una política
no altera liquidaciones ya emitidas, exactamente la misma garantía que ya tenemos para R03 y R15.

### 4.4 Quién edita, en el MVP

Recomiendo **un formulario propio y acotado** (menú cerrado, en la línea de D-010/D-014), no el
editor visual de GoRules, para la primera versión de cualquier política que se construya: menos
superficie de error, reusa el patrón de validación que ya pasó auditoría tres veces, y no agrega
una dependencia de frontend (React + `@gorules/jdm-editor`) para algo que todavía no sabemos si
vale la pena. El editor visual (`jdm-editor`, standalone o embebido) queda como alternativa cuando
haya **más de un administrador externo (no Juani/Alberto)** pidiendo reglas que un menú cerrado no
pueda expresar, porque ahí es donde el costo de "cada regla nueva es un deploy" empieza a doler de
verdad. Mientras el único que programa es Juani (D-022), un formulario cerrado que genera el JDM
por detrás es más seguro y más barato que un editor visual completo.

### 4.5 Simulación antes de activar

"Volver a correr el último mes" (lo que pide la tarea): tomar los hechos ya registrados de la
última liquidación de un edificio, correr la política candidata contra esos hechos, y mostrar el
diff contra lo que realmente se liquidó, **sin tocar ningún movimiento real**. Esto es barato de
construir porque ya tenemos los hechos (la cuenta corriente es el libro de origen, R08) y el motor
ya es una función pura (hechos → acciones propuestas) que no necesita que exista una liquidación en
curso para correr. El editor standalone de GoRules trae un simulador parecido, pero sólo para
datos de prueba sueltos, no para "repetir el mes pasado de este edificio real": esa parte hay que
construirla nosotros, sea cual sea el motor.

### 4.6 Auditoría y aislamiento por tenant

- **Auditoría**: cada acción que el motor propuso y el core aplicó queda en el movimiento de la
  cuenta corriente (R08 ya lo exige: motivo, responsable, referencia). Ese motivo incluye qué regla
  y qué versión de política la generó. No hace falta una tabla de auditoría nueva: R08 ya es el
  libro de auditoría.
- **Aislamiento (R10)**: las políticas son datos de un edificio como cualquier otro; se cargan y
  evalúan con el mismo candado que el resto (tenant desde la identidad autenticada, nunca de un
  parámetro del cliente). El motor en sí (ZEN, embebido en el proceso) no comparte estado entre
  evaluaciones: cada `evaluate()` es una llamada aislada con sus propios hechos, no hay sesión ni
  caché compartida que pueda filtrar datos de otro edificio si el adaptador arma bien el payload.

### 4.7 Modos de falla

Tres casos distintos, con la misma respuesta de fondo ("el motor nunca escribe plata, el core
decide qué hacer con la duda"):

1. **El motor devuelve algo que no cumple el contrato** (campo faltante, tipo equivocado, vacío
   por una regla rota, sección 3.5): bloqueante en el control antes de emitir (12.5 de Alberto),
   nunca "se ignora y se sigue".
2. **El motor tarda o no responde** (si en algún momento corre fuera de proceso; hoy, embebido en
   Python, esto es poco probable salvo un bug infinito en una regla, pero L-001 ya nos enseñó a no
   asumirlo): mismo tratamiento que cualquier dependencia externa, timeout acotado y bloqueo con
   alerta, nunca "seguir sin la política".
3. **No hay política configurada para ese edificio** (caso normal, no un error): el core usa su
   default documentado (por ejemplo, sin descuento, sin recargo adicional más allá de R03), igual
   que hoy un edificio sin fondo de reserva configurado simplemente no tiene esa línea (R15).

---

## 5. Qué se movería al motor, en el MVP y después

Cruzando esto con la clasificación ya hecha en `2026-10-12-dolores-protecc.md`:

| Candidato | Hoy | Recomendación |
|---|---|---|
| Canon de obra / cargo por estado de unidad (R02) | Ya resuelto con menú cerrado en `parametros.yaml` (D-014), auditado tres vueltas | **No mover.** Ya es más simple y más seguro que una regla de motor; moverlo sería reescribir algo que funciona para ganar nada. |
| Definición de "moroso crítico" | Clasificado como "Hueco MVP" en el documento de dolores: se agrega a HU-A8 (cambio 10) **sin** bloqueo de amenities | **No necesita motor todavía.** Es un umbral (2+ períodos vencidos, configurable como mucho en la cantidad) que un menú cerrado cubre igual de bien. Candidato a motor sólo si más adelante el umbral deja de ser "2+ períodos" y pasa a combinar antigüedad + monto + excepciones (plan de pago, gestión judicial), que es cuando un menú cerrado empieza a no alcanzar. |
| Bloqueo de amenities para moroso crítico | **Fuera del MVP** (no hay módulo de reservas) | No aplica todavía. Cuando entre (v1.1/`proyecto-final.md`), es un buen candidato real a motor: depende del reglamento de cada consorcio (DEC-08), que varía mucho más que un menú cerrado. |
| Descuento por pago temprano | No existe hoy en `reglas-de-negocio.md`: es una regla nueva que viene de Alberto, no decidida | Si Juani la aprueba, **es el primer candidato limpio para el motor** en el MVP: una condición simple (día de pago) contra un porcentaje, exactamente el patrón seguro de 3.3 (literal de texto, sin aritmética adentro). |
| Recargos del reglamento (más allá de R03) | No existe hoy; R03 ya cubre el interés por mora, que **no es configurable en fórmula** (D-011 descartó "fórmula libre") | Mismo caso que el descuento: si aparece una variabilidad real por edificio (no sólo la tasa, que ya es configurable), es candidato a motor. Si sigue siendo "una tasa y unos días de gracia", sigue siendo menú cerrado. |
| Bloqueante vs advertencia en el control antes de emitir (12.5 de Alberto) | No existe hoy; `liquidacion-y-emision` (cambio 7) no tiene todavía esta lista | Es una lista fija de controles (saldos iniciales, extracto, facturas con alerta, duplicados, diferencia de caja), no una regla que varíe por edificio en su mayoría. **Candidato débil al motor**: es más una lista de validaciones del propio core que una política de negocio configurable. Lo único configurable por edificio ahí es si el administrador puede o no emitir con alertas aceptadas, que ya es un booleano simple. |
| Plan de pago | **Fuera del MVP**, va a `proyecto-final.md` | No aplica todavía. Candidato futuro cuando exista el módulo. |

**Resumen**: dentro del alcance actual del MVP (los 15 cambios de `roadmap.md`), **no hay ningún
candidato urgente** para un motor de reglas. Lo único nuevo y config-variable-por-edificio que
podría entrar ya (descuento por pago temprano) es chico y cabe perfectamente en el patrón
"menú cerrado + `parametros.yaml`" que ya tenemos probado, sin agregar una dependencia nueva
(Rust, bindings, un lenguaje de expresiones) para un caso de uso que todavía no la necesita.

### Impacto en el roadmap

No propongo ni abro un cambio de OPSX nuevo en esta exploración (D-054 lo pide así: "mientras
tanto no se escribe código", y abrir un `openspec/changes/` ya sería empezar a construir). Si
Juani decide avanzar con el motor, mi recomendación es que entre como un cambio **después de M2**
(cuando amenities y plan de pago, los casos que de verdad lo justifican, entren al alcance), no
dentro de los 15 cambios actuales. El único lugar donde podría valer la pena adelantarlo es si
Juani aprueba el descuento por pago temprano para el MVP: en ese caso **sigue sin hacer falta
motor**, entra como una opción más de `parametros.yaml` dentro del cambio 7 o 10, con el mismo
patrón de D-010.

---

## 6. Riesgos

- **El hallazgo de 3.2 (fallas silenciosas) es el riesgo central de cualquier integración con ZEN.**
  Si en algún momento se construye el adaptador, el validador de contrato de salida (4.2) no es
  una mejora opcional: sin él, un error de tipeo en una regla no se nota hasta que alguien audita
  a mano por qué un edificio no tuvo el descuento que debería.
- **Dependencia en un binario Rust prearmado.** `zen-engine` es un wheel con extensión nativa; si
  en algún momento hace falta la precisión arbitraria (Decimal real adentro del motor, que hoy no
  tenemos ninguna razón para necesitar porque la regla de oro lo prohíbe), haría falta compilar
  desde la fuente con `maturin`, un costo de build que hoy nadie tiene instalado ni probado.
- **Costo de aprender un lenguaje de expresiones nuevo** (ZEN) para algo que, en el alcance actual,
  el equipo (Juani solo, D-022) puede seguir resolviendo con pydantic y YAML, que ya domina y que
  ya pasó por auditoría.
- **El editor visual es una tentación de alcance.** Es gratis y se ve bien, pero sumarlo ahora
  significa una dependencia de frontend (React, `@gorules/jdm-editor`) y una superficie de
  configuración que el único usuario de la administración (Juani/Alberto) no necesita todavía.
- **Nada de esto es gratis en tiempo de research**: el paquete está vivo y bien documentado, pero
  la documentación pública no cubre JDM a fondo (tuve que bajar el ejemplo real del repo porque
  la página de node-types no alcanzaba) ni el comportamiento de errores (tuve que armar el spike
  para encontrar 3.2; no está en ningún lado de la documentación oficial).

---

## 7. Decisiones que necesita Juani

1. **¿Se adopta GoRules ZEN como motor, o se posterga la decisión de herramienta hasta que exista
   un caso de uso real (amenities o plan de pago, en v1.1)?**
   Recomiendo: **postergar la elección de herramienta**, pero dejar este documento como la
   investigación ya hecha para cuando haga falta. Nada en el MVP actual lo necesita con urgencia
   (sección 5). Alternativa: adoptarlo ya como piso técnico para no reinvestigar más adelante,
   aceptando el costo de una dependencia sin uso inmediato.

2. **¿El descuento por pago temprano entra al MVP?** Hoy no existe en `reglas-de-negocio.md`; es
   una regla nueva de la propuesta de Alberto.
   Recomiendo: **si entra, que sea como opción de `parametros.yaml`** (menú cerrado: porcentaje y
   día límite), no como motor, siguiendo el patrón de D-010. Alternativa: usarlo como piloto real
   del motor de reglas dentro del MVP, aceptando el costo de sección 4 completo (contrato,
   validador, versionado) para un caso que el menú cerrado ya resuelve.

3. **¿Se confirma la definición de "moroso crítico" por antigüedad (2+ liquidaciones vencidas,
   configurable sólo en la cantidad) para el cambio 10, sin bloqueo de amenities?** Esto ya estaba
   preguntado en `2026-10-12-dolores-protecc.md` (pregunta 4 de ese documento); lo repito acá
   porque define si esa regla necesita motor (no, si se mantiene simple) o no.
   Recomiendo: **confirmar la definición simple**, tal como la deja el documento de dolores.
   Alternativa: dejarla abierta a excepciones (plan de pago, gestión judicial) desde ya, lo que la
   acerca más a necesitar el motor antes de tiempo.

4. **Cuando llegue el momento de construir el motor (post-M2): ¿editor visual embebido
   (`@gorules/jdm-editor`) o un formulario propio sobre JDM generado por detrás?**
   Recomiendo: **formulario propio primero** (sección 4.4), con el editor visual como opción para
   cuando haya administradores externos. Alternativa: ir directo al editor visual para ahorrar el
   trabajo de construir el formulario, aceptando más superficie de configuración de la que hace
   falta mientras el único que edita reglas es Juani o Alberto.

5. **¿Quién valida que el contrato de salida del motor (sección 4.2) se corte en seco ante una
   regla que devuelve algo inesperado, antes de que exista una sola línea de ese módulo?** Esto es
   una decisión de diseño que el *design* del cambio correspondiente tendría que fijar explícito,
   no dejarlo implícito en el código del adaptador.
   Recomiendo: **que quede escrito como regla de negocio nueva** (candidata a R17) el día que se
   proponga el cambio, igual que R07 fija la garantía de redondeo. Alternativa: resolverlo sólo en
   el *design* del cambio, sin regla formal, aceptando que quede menos visible para el próximo que
   lea `reglas-de-negocio.md`.
