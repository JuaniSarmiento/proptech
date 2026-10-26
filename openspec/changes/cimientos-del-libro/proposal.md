## Why

El cambio 4 (`motor-de-cuenta-corriente`, C-07) construye el libro de movimientos: el primer lugar del
sistema donde vive la deuda de cada unidad. La exploración del 22/10/2026
(`openspec/exploraciones/2026-10-22-motor-de-cuenta-corriente.md`, sección 8) lo parte en cuatro
sub-changes y deja este, el **4a**, como el primero: los controles tienen que existir **antes** de la
primera tabla de plata, no al lado. Hoy el test de fronteras sólo prueba que `compartido` es hoja; el
dueño de `configuracion_versionada` es el migrador (un `xfail` que espera esta decisión, DBA-1); no hay
reparto por mayor resto ni aritmética de montos (`Dinero` no la tiene a propósito, D-053); el umbral de
R30 no tiene dónde guardarse; y el coeficiente, que desde el 4 termina en deuda, cambia sin que nadie
sepa quién lo cambió (BKS-5).

Hay además un orden que no se puede invertir: la columna nueva de `configuracion_versionada` tiene que
entrar **antes** de que la tabla deje de ser del migrador. Después, cada `ALTER` sobre ella necesita un
mecanismo de préstamo que hoy no existe.

Cubre: **R07** (reparto y redondeo, con la respuesta P-7 de hoy), **R30** (sólo dónde vive el
umbral; su efecto sobre R20 es del 4c), **D-016** (alcance de la auditoría), **D-021** y **D-040**
(fronteras entre módulos), **D-046** (montos), **D-053** (su deuda: el `except TypeError` muerto y los
ceros de más de `Dinero`, con su nota corregida por D-114.6), **D-109** puntos 1 y 3, y las decisiones
nuevas **D-113** (P-7 y P-3) y **D-114** (las siete elecciones de Juani después de la revisión del
propose), las dos del 26/10/2026. Ninguna historia de usuario nueva: no hay pantalla.

## Qué queda fuera

| qué | dónde va | por qué |
|---|---|---|
| Las seis tablas del libro (`cuenta`, `emision`, `evento_de_emision`, `obligacion`, `movimiento`, `imputacion`), concurrencia, R04, R05, R06, R08, R13, HU-A9, idempotencia (4.4), contrato de error (4.8), sin puerto de repositorio (4.9) | 4b `libro-de-movimientos` | Es el núcleo; necesita los controles de este change ya puestos |
| R03, R09, R20 y el efecto de R30 sobre el moroso crítico | 4c | Funciones sobre el 4b |
| Cambio de titular, R32, cuenta de persona en uso | 4d | Bloqueado por P-1 y P-2 |
| El escaneo de nombres de tabla en SQL (4.2) | 4b | Da rojo hoy en `complejos` y sólo tiene sentido con las tablas del libro existiendo |
| El mecanismo de préstamo de la propiedad para una migración futura (4.1) | El primer change que necesite un `ALTER` sobre una tabla protegida | Se escribe como decisión; construirlo sin un caso real es código que nadie ejercita |
| Columnas de R23 (gasto atípico) en `configuracion_versionada` | 6 o 14 | No pedido para el 4a; ver "Decisiones de esta propuesta" |
| Columna de día de cierre por edificio | Ninguno por ahora | P-3 (D-113): el cierre es el último día del mes; se agrega si Alberto lo pide (A-2) |
| Campo del umbral en la pantalla de intereses | El primer change que lo necesite editar en pantalla (probablemente 4c) | El 4a no trae pantallas (4.7) |
| `pesos()`, errores de campo, API falsa (4.7, 4.11) | Primera pantalla con plata | Sin pantalla en el 4a no hay caso |
| Outbox (4.6) y el canario (4.12) | 7 y 15; el canario ya se arregló en `79037b5` | El 4a no encola nada |

## Gobernanza

**HIGH** (D-094, D-111): toca la propiedad de tablas en PostgreSQL, un chequeo que puede impedir que la
API arranque, una migración sobre una tabla de sólo agregar y la auditoría. No toca plata de nadie
todavía (no hay libro), por eso no es CRITICAL; los tres sub-changes siguientes sí lo son. **No se
construye nada** hasta que la sección "Aprobación" quede firmada por Juani, Alberto o Emiliano, con
nombre, fecha y la respuesta a cada elección.

## Preguntas abiertas de las que el 4a no depende

Juani respondió hoy P-7 y P-3 (D-113). Las demás **no bloquean** este change y no se deciden acá:

- **P-1, P-2** (cambio de titular, deuda a nombre del vendedor): bloquean el 4d.
- **P-4, P-5** (de qué mes es el interés; base del umbral de $500 y desde cuándo algo está vencido):
  bloquean el 4c. El 4a sólo guarda el **número** del umbral, no decide contra qué se compara.
- **P-6** (pantalla de corrección en el 4): decide el 4b; el 4a no tiene pantalla.
- **P-8** (repositorio sin puerto, contra D-040): bloquea el 4b.
- **A-1** (Alberto: a qué unidad va el centavo en su Excel): el 4a fija un desempate determinista
  provisorio (E3); si la respuesta de Alberto es otra, cambia una función pura y sus tests, sin tocar
  datos.
- **A-2, A-3, A-4**: corte del interés en su Excel, doble vencimiento en el piloto, orden del fondo de
  reserva. Ninguno toca el 4a.

## What Changes

- **Fronteras entre módulos con cinco reglas nuevas** sobre un paquete `cuenta_corriente/` vacío: sin
  ciclos entre módulos; entre módulos sólo se importa `aplicacion`, con excepciones nombradas y con
  motivo; `dominio/` sólo importa de `compartido` una lista permitida; y `dominio/` no importa su propia
  infraestructura ni `sqlalchemy` o `psycopg` (D-114.7). Además, `cuenta_corriente` no importa la cola ni
  `liquidacion`. Cada regla con sus mutantes en copias temporales, uno por forma de import.
- **Las tablas de sólo agregar pasan a ser del rol de arranque**, como `auditoria`:
  `configuracion_versionada` hoy, y las seis del libro cuando el 4b las declare en una sola lista
  (`compartido/tablas_protegidas.py`) y las cree con un trigger de bloqueo por sentencia. El paso de
  roles verifica su protección **por el efecto**, sin armar filas (D-114.4), y la API y el worker no
  arrancan si alguna quedó con dueño equivocado. El `xfail` de `configuracion_versionada` se borra.
- **Reparto por mayor resto** como función pública en `compartido` (la usan el 4, el 6 y el 7): cada
  parte se trunca al centavo y los centavos que faltan van a los restos más grandes, con desempate
  determinista. **Redondeo medio hacia arriba** como función aparte, para el interés y los montos
  sueltos (D-113). Pruebas de propiedades con `hypothesis` y un oráculo que no reusa la fórmula.
- **Suma y resta entre montos**: la aritmética mínima que `Dinero` no tenía. **BREAKING** para la spec
  `representacion-de-montos`, que hoy prohíbe toda aritmética "en este cambio".
- **Umbral de saldos chicos (R30) por versión de configuración**: columna nueva en
  `configuracion_versionada`, más el trigger de bloqueo por sentencia, en la misma migración; default de
  `config/parametros.yaml` ($500, D-109); una versión sin umbral hereda el de la anterior por
  `vigente_desde` (D-114.1); visible y opcional en la API de versiones y en el alta del edificio.
- **Siete cambios del padrón auditados**: crear y editar unidad, crear y editar grupo, fijar las
  unidades de un grupo, editar categoría y reordenar categorías, con el coeficiente anterior y el nuevo
  (D-114.2, D-114.3).
- **Deuda D-053 cerrada**: se borra el `except TypeError` que no se alcanza en `leer_parametros`, con
  tests que prueban que esos caminos ya los corta otra capa; queda escrito y probado con mutantes que
  `Dinero.desde_decimal` acepta ceros de más sin cambiar el valor y que el texto los rechaza (D-114.6).
- **Rollback escrito con su punto de no retorno** (D-114.5): el primer evento del padrón registrado.
- **D-113 y D-114** agregadas a `knowledge-base/09_decisiones_y_supuestos.md` (Juani, 26/10/2026).

## Capabilities

### New Capabilities

- `fronteras-de-modulos`: qué puede importar cada módulo de `proptech_core` y cómo se prueba que el
  test lo vigila de verdad.
- `reparto-de-montos`: repartir un total entre partes con suma exacta al centavo, y redondear un monto
  suelto; los dos modos, separados.

### Modified Capabilities

- `aislamiento-por-administracion`: el rol de arranque pasa a ser dueño de toda tabla de sólo agregar
  (no sólo de la auditoría); el paso de roles lo verifica por el efecto y los procesos no arrancan si
  no se cumple.
- `representacion-de-montos`: el monto suma, resta y se niega, sin salir de `NUMERIC(14,2)`; un
  decimal de la base con ceros de más se acepta si el valor no cambia.
- `configuracion-versionada`: cada versión lleva su umbral de saldos chicos, heredado de la anterior
  por `vigente_desde` si no viene.
- `parametros-del-sistema`: el archivo trae el umbral de saldos chicos con su rango.
- `auditoria-de-acciones`: los cambios del padrón que deciden el reparto quedan auditados, con el
  coeficiente anterior y el nuevo.

## Impact

- **Backend**: `compartido/roles.py`, `compartido/base_de_datos.py`, `compartido/dinero.py`,
  `compartido/parametros.py`, nuevos `compartido/reparto.py` y `compartido/tablas_protegidas.py`; nuevo paquete `cuenta_corriente/`
  (vacío); `complejos/aplicacion/` (unidades, grupos, categorías, escritura y lectura de versiones);
  `complejos/dominio/configuracion.py`; `acceso/dominio/eventos.py` y `acceso/aplicacion/auditoria.py`;
  `proptech_api/complejos.py`, `proptech_api/app.py` y `proptech_worker/ajustes.py` (el log del
  chequeo nuevo). Dos migraciones nuevas (`0021`, `0022`).
- **Tests**: `test_fronteras_de_modulos.py` y `test_dueno_de_tablas_solo_agregar.py` crecen; los que
  hacen `downgrade` después de `despues()` se adaptan al patrón que ya usa `test_auditoria_tabla.py`.
- **Dependencias**: `hypothesis` en el grupo `dev`, con versión exacta.
- **Configuración**: `config/parametros.yaml` suma el umbral.
- **Web**: sólo los fixtures que salen de la API real y el tipo de la respuesta de versiones (un campo
  nuevo). Ninguna pantalla cambia.
- **Infra**: nada en `compose.yaml`; el paso de roles ya corre `antes` y `despues`. `humo.sh` no
  escribe en `configuracion_versionada` (`rg`, 26/10/2026), así que la columna sin default no lo rompe
  (L-023, a repetir en la tarea).

## Lecciones que aplican (15_lecciones.md)

| lección | cómo la cubre | tarea |
|---|---|---|
| L-013, L-019, L-035 | Cada regla de fronteras, cada propiedad del reparto y cada verificación de `despues()` tiene su mutante; los tests que nacen verdes se declaran fijación y se ven fallar con un mutante | 1.1 a 1.4, 2.5, 4.1 a 4.3, 5.2, 6.1 |
| L-018 | La protección de cada tabla se prueba por el efecto: `UPDATE` y `DELETE` sin filas contra el trigger por sentencia, y `TRUNCATE` ejecutado (con `CASCADE` si hay FK entrante) | 5.2 |
| L-034 | El rojo de cada test cae en la aserción que dice probar, nunca en un `ModuleNotFoundError`: se mide contra un módulo que existe y devuelve vacío | todas las de los grupos 2 y 3 |
| L-036 | La sonda de dueño sigue siendo `NO FORCE ROW LEVEL SECURITY` | 5.1 |
| L-016, L-022 | El chequeo de arranque compara el conjunto entero de tablas protegidas contra su fuente | 5.3 |
| L-023 | `rg` de todo `INSERT INTO configuracion_versionada` en el repo entero antes de cerrar la migración | 3.2 |
| L-002, L-007, L-008 | El umbral se prueba faltante, vacío, en blanco, de otro tipo y fuera de rango; los errores no repiten el valor | 3.1 |
| L-009 | El arreglo del lector de parámetros (D-053) se mira también en el lector de la semilla | 6.1 |
| L-010, L-031, L-037 | La corrida de cierre va después de la última vuelta, con el SHA anotado, y se espera el CI completo | 7.1 |
| L-029 | Una regla nueva que entre después de la firma necesita firma propia | toda vuelta de correcciones |

## Decisiones de esta propuesta

Juani ya decidió, el 26/10/2026, las siete de la revisión (D-114): herencia del umbral por
`vigente_desde`, coeficiente anterior y nuevo en la auditoría, auditar `crear_unidad` y `crear_grupo`,
trigger por sentencia para la sonda, rollback con punto de no retorno, `desde_decimal` acepta ceros de
más sin cambiar el valor, y la regla (e) de fronteras. Quedan para quien firme, tomadas por el
proponente:

1. **Excepción nueva en la regla (b)**: `acceso.dominio.eventos`, que hoy usa
   `complejos/aplicacion/ejemplo.py:39` y que van a usar los siete casos de uso del padrón (E2).
2. **Desempate del mayor resto**: orden natural del identificador, con los números antes que las
   letras, y el id de la unidad como último desempate (E3).
3. **Total negativo simétrico**: un total negativo se reparte como el positivo con el signo cambiado,
   truncando hacia cero; ni R07 ni D-113 lo dicen (E8).
4. **R23 no entra**: la exploración recomendaba sumarla en la misma migración (confianza media); acá
   queda afuera porque el 4a pedido es R30 sola, y su `ALTER` posterior va a necesitar el préstamo
   (E7).

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 26/10/2026): `01` a `16` y `README.md`.

| documento | operación | qué |
|---|---|---|
| `09_decisiones_y_supuestos.md` | **APPEND** (ya, en este propose) | D-113: P-7 (redondeo en dos pasos) y P-3 (cierre el último día del mes); D-114: las siete elecciones de Juani después de la revisión (incluye la corrección de la nota de D-053) |
| `09_decisiones_y_supuestos.md` | **APPEND** (al archivar) | Dueño de las tablas de sólo agregar, la sonda por sentencia y el préstamo acotado por escrito (DBA-1); las reglas de fronteras con sus excepciones; la partición del 4 en 4a a 4d; el desempate y el total negativo si se firman |
| `04_modelo_de_datos.md` | **REWRITE** | `configuracion_versionada` con la columna del umbral y el trigger por sentencia; dueño de las tablas de sólo agregar; vocabulario de `accion_de_auditoria` con los siete eventos del padrón |
| `05_reglas_de_negocio.md` | **REWRITE** | R07: "cada parte se trunca" en vez de "se redondea", el desempate y los dos pasos; R30: dónde vive el umbral; R03: el cierre del período es el último día del mes (D-113). Por respuesta a preguntas abiertas, como permite D-089 |
| `08_arquitectura_propuesta.md` | **REWRITE** | Sección "Fronteras entre módulos" con las cinco reglas y sus excepciones; `reparto` en `compartido`; dueño de las tablas de sólo agregar y el chequeo de arranque |
| `02_descripcion_general.md` | **REWRITE** | `hypothesis` en la tabla de versiones del stack |
| `10_preguntas_abiertas.md` | **REWRITE** | Quitar P10 y P11 como bloqueantes del 4 (`:155`) y P42 "antes del cambio 4" (`:163`); P-3 y P-7 respondidas (D-113); **sumar P-1, P-2, P-4, P-5, P-6 y P-8**, cada una con el sub-change que bloquea, y **A-1 a A-4** en la sección "Para Alberto": hoy sólo viven en la exploración |
| `07_flujos_principales.md` | **REWRITE** | `:140`, los bloqueantes viejos |
| `11_glosario.md` | **REWRITE** | "reparto por mayor resto", "redondeo medio hacia arriba", "cierre del período" |
| `12_fichas_de_changes.md` | **REWRITE** | Ficha 4 partida en 4a a 4d; R30 vigente; las marcas de R35, R36 y R39 que no existen; deuda D-053 cerrada con el texto de D-114.6 (no "rechaza ceros de más"); dependencia del 6 hacia el 4a; para el 4b, el trigger por sentencia y `ON CONFLICT DO NOTHING` |
| `CHANGES.md`, `CLAUDE.md`, `AGENTS.md` | **REWRITE** | Sub-changes del 4 con gobernanza y estado |
| `15_lecciones.md` | **APPEND** | Lo que enseñe la construcción |
| `01`, `03`, `06`, `13`, `14`, `16`, `README.md` | none | El 4a no cambia visión, actores, historias, motor de reglas, forma de trabajo ni fases posteriores |

## Aprobación

Gobernanza HIGH (D-094, D-111). La completa, a mano, Juani, Alberto o Emiliano. Ningún agente la
escribe. Cada elección tiene su alternativa descartada y el costo de revertir en `design.md`.

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · Dueño de las tablas de sólo agregar | El rol de arranque, como `auditoria`, para `configuracion_versionada` y toda tabla futura del conjunto, declarado en un solo lugar; `despues()` verifica la protección por el efecto con el trigger por sentencia (D-114.4), **salvo `auditoria`**, que queda con su trigger por fila y su sonda actual porque es del rol de arranque desde el 2a y el migrador ya no puede alterarla: es una excepción a la letra de D-114.4 que se firma acá; la API, el worker y los comandos no arrancan si el dueño es otro, sin forma de saltearlo; el préstamo para migraciones futuras queda escrito y sin construir; rollback con punto de no retorno (D-114.5) (D0 a D3, Migration Plan) | Sí |
| E2 · Reglas de fronteras | Sin ciclos; entre módulos sólo `aplicacion`, con excepciones `acceso.dominio.identidad`, `acceso.dominio.permisos` y `acceso.dominio.eventos` (esta última, nueva); `dominio/` sólo importa de `compartido` una lista permitida, con `parametros` como excepción; `dominio/` no importa su propia infraestructura (D-114.7); `cuenta_corriente` no importa la cola ni `liquidacion` (D4) | Sí |
| E3 · Desempate del mayor resto | Orden natural del identificador, números antes que letras ("1A", "10A", "B1", "C1", "L-PB"), y el id como último desempate; provisorio hasta A-1 (D6) | Sí |
| E4 · Aritmética de `Dinero` | Sólo suma, resta y negación entre montos, sin salir de `NUMERIC(14,2)`; el redondeo es una función aparte y el reparto trabaja en centavos enteros (D5, D7) | Sí |
| E5 · Umbral de R30 | Columna `NOT NULL` en `configuracion_versionada`, las versiones existentes en $500, sin default en la base; en una versión nueva, si no viene, se hereda de la inmediatamente anterior por `vigente_desde`, aunque sea futura (D-114.1); en el alta del edificio, de `parametros.yaml`; en la API sí, en la pantalla no (D8) | Sí |
| E6 · Auditoría del padrón | Siete eventos nuevos, incluidos `crear_unidad` y `crear_grupo` (D-114.3); el detalle guarda edificio, nombres de campos cambiados y el coeficiente anterior y el nuevo (D-114.2), nunca otros valores (D9) | Sí |
| E7 · Lo que no entra | Ni R23 ni el día de cierre por edificio (P-3, D-113) | Sí |
| E8 · Total negativo simétrico | Un total negativo se reparte como el positivo con el signo cambiado (truncando hacia cero); ni R07 ni D-113 lo dicen (D7) | Sí |
| Firmante (Juani, Alberto o Emiliano) | Fecha | Alcance aprobado |
|---|---|---|
| Juani | 26/10/2026 | E1 a E8 tal como están en esta sección, con la excepción de `auditoria` de E1 |
