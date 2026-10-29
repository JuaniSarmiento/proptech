# Lecciones aprendidas

Lo que cada cambio enseñó sobre **cómo se rompe el sistema y cómo se nos escapan los errores**.
El constructor y el rompedor lo leen antes de empezar cada cambio; el auditor lo usa para revisar.

**Cómo se alimenta**: el auditor, en su veredicto, propone las lecciones de ese ciclo; el
orquestador las agrega acá al archivar el cambio. **Sólo se agrega.** Si dos lecciones dicen lo
mismo, se suma la nueva como ocurrencia de la vieja en vez de duplicarla. Una lección tiene que
ser una regla que sirva en el próximo cambio, no la anécdota de éste.

Formato: **L-NNN · regla** · origen (cambio y vuelta) · qué pasó · a quién aplica.

---

## L-001 · Probar una dependencia que no responde, no sólo una apagada

- **Origen**: cambio 1a, vuelta 1.
- **Qué pasó**: el timeout de 2 segundos de la base no existía (se pasaba a una opción que SQLAlchemy
  ignora). Los tests y el rompedor probaron la base apagada, que rechaza al instante, y nunca una que
  no contesta. El auditor lo encontró contra una IP que no responde: el pedido quedaba colgado 30 s.
- **Regla**: toda dependencia externa (base, Redis, proveedores de email o IA, bancos) se prueba en tres
  estados: **apagada**, **que no responde** (pausada o en una IP que no contesta) y **lenta**. El
  test de "no responde" tiene que estar acotado por tiempo.
- **Aplica a**: constructor y rompedor.

## L-002 · La configuración se rompe de muchas formas, no sólo faltando

- **Origen**: cambio 1a, vueltas 1 y 2.
- **Qué pasó**: primero, una variable faltante dejaba arrancar la API y el error se disfrazaba de base
  caída. El arreglo cubrió sólo el caso "falta": con la contraseña vacía o el puerto en `abc`, el
  problema volvía.
- **Ocurrencias**: cambio 1b, vuelta 2 (se arreglaron los dígitos Unicode y quedó el salto de línea final en los mismos patrones); cambio 1b, vuelta 3 (claves no texto en la semilla).
- **Regla**: toda configuración se prueba **faltante, vacía, en blanco, con tipo equivocado y fuera de
  rango**, y el error tiene que nombrar cada variable con problema **sin mostrar nunca su valor**. Un
  arreglo cierra la familia de errores, no el caso puntual.
- **Aplica a**: constructor y rompedor.

## L-003 · Contar los tests, no creerle a quien dice cuántos pasan

- **Origen**: cambio 1a, vuelta 3.
- **Qué pasó**: un informe decía "4 passed" en un lugar y "55 passed" en otro.
- **Ocurrencias**: cambio 1a, vuelta 3 (el rompedor contó bien los tests, pero contó sólo tests: ver L-005).
- **Regla**: el rompedor y el auditor corren la suite ellos mismos y comparan el número de tests con el
  anterior: si bajó, algo se dejó de correr; si hay tests salteados o deseleccionados, se explica por qué.
- **Aplica a**: rompedor y auditor.

## L-004 · Si dos revisores llegan por el mismo camino, no son dos revisiones

- **Origen**: cambio 1a, vuelta 1.
- **Qué pasó**: el constructor y el rompedor validaron `/api/salud` con el mismo escenario, y el "no
  pude romperlo" valía sólo para ese escenario.
- **Regla**: el rompedor no repite las verificaciones del constructor como ataque: las usa como punto
  de partida y busca **otro camino** hacia la misma promesa. El auditor marca cuando dos informes
  coinciden por la misma ruta.
- **Aplica a**: rompedor y auditor.

## L-005 · Lo que agrega un revisor pasa por las mismas puertas que el código del constructor

- **Origen**: cambio 1a, vuelta 3 (auditor).
- **Qué pasó**: el rompedor agregó 10 tests que pasaban y dijo "no pude romperlo", pero su archivo no
  pasaba ni el formato ni mypy. El siguiente push dejaba el CI en rojo.
- **Regla**: "verde" quiere decir **todos los pasos del workflow**, no sólo los tests. El que agrega un
  archivo, sea quien sea, corre lint, formato, tipos y tests antes de informar. El auditor corre los
  mismos pasos que el CI.
- **Aplica a**: constructor, rompedor y auditor.

## L-006 · Un comando destructivo apunta a un nombre único del proyecto

- **Origen**: cambio 1a, vuelta 3 (auditor).
- **Qué pasó**: `docker compose down -v` apuntaba a un proyecto llamado `infra`, el nombre de la carpeta,
  en una máquina con otros proyectos.
- **Regla**: todo lo que borra (volúmenes, contenedores, bases) apunta a un identificador propio de
  PropTech, nunca a uno derivado de una ruta genérica.
- **Aplica a**: constructor.

## L-007 · El mensaje de error de una librería también es una salida

- **Origen**: cambio 1b, auditoría de la vuelta 2.
- **Qué pasó**: el lector de YAML reenviaba el texto del error de PyYAML, que incluye la línea rota del
  archivo: el contenido terminaba en el mensaje, aunque el diseño decía que no.
- **Regla**: nunca reenviar `str(error)` de un tercero sin probar que no repite la entrada. Se informa
  la posición y una descripción propia.
- **Aplica a**: constructor y rompedor.

## L-008 · Validar texto con coincidencia completa y sólo ASCII

- **Origen**: cambio 1b, rompedor y auditoría de la vuelta 2.
- **Qué pasó**: los patrones con `^...$` aceptaban un salto de línea final y los que usaban `\d` sin la
  bandera ASCII aceptaban dígitos de otros alfabetos; `Decimal()` los normalizaba sin avisar.
- **Regla**: todo texto externo se valida con `fullmatch` (o `\A...\Z`) y `re.ASCII`, y se prueba con
  espacios, tabulaciones, saltos de línea al principio y al final, y dígitos no ASCII.
- **Aplica a**: constructor y rompedor.

## L-009 · Un arreglo en un módulo se aplica y se prueba en su gemelo

- **Origen**: cambio 1b, auditoría de la vuelta 3.
- **Qué pasó**: el lector de parámetros atrapaba una clave que no era texto en la raíz; el lector de la
  semilla, con la misma forma, dejaba escapar un `TypeError` con traceback.
- **Regla**: si dos módulos comparten forma (los dos lectores de YAML, dos endpoints parecidos, dos
  importadores), cada defecto que se arregla en uno lleva su test en el otro.
- **Aplica a**: constructor y rompedor.

## L-010 · La corrida de cierre va después de la última vuelta, nunca en la primera

- **Origen**: cambio 1c, cierre (auditoría de la vuelta 3, 14/10).
- **Qué pasó**: la corrida equivalente al CI (la tarea de cierre, L-003) se puede correr temprano y
  quedar en verde, pero si el código sigue cambiando después (nuevas correcciones de una vuelta
  siguiente), esa corrida ya no describe el código final.
- **Regla**: la corrida equivalente al CI que cierra un cambio se hace **después de la última
  vuelta de correcciones**, nunca antes. Si el código cambia después de esa corrida, la corrida queda
  **vencida** aunque siga en verde: hay que repetirla sobre el código final.
- **Aplica a**: constructor y auditor.

## L-011 · Un plazo que abandona un hilo no cancela su transacción

- **Origen**: cambio 1c, cierre (hallazgo F2c del rompedor, vuelta 3).
- **Qué pasó**: `asyncio.wait_for(asyncio.to_thread(...))` corta la ESPERA del event loop, no el
  hilo: no hay forma de matar un hilo de Python desde afuera. Si la base queda congelada más tiempo
  que todos los reintentos, el hilo del primer intento sigue corriendo en segundo plano y puede
  confirmar su efecto después de que el trabajo ya quedó marcado agotado.
- **Regla**: un timeout del lado del cliente (`wait_for`, `asyncio.timeout`) acota cuánto se espera
  una respuesta, nunca si la operación de fondo sigue corriendo. Para una operación con un efecto que
  importa (escribir en la base, mandar un email), el corte tiene que estar del lado del servidor
  (`statement_timeout` de PostgreSQL o equivalente) o en el hilo mismo, no sólo en quien espera.
- **Aplica a**: constructor y rompedor.

## L-012 · La deuda se asigna al primer cambio que usa la pieza, no al más obvio

- **Origen**: cambio 1c, cierre (tabla de deuda del veredicto, 14/10).
- **Qué pasó**: varios hallazgos de la auditoría (F2c, F12b, `repr(RedisSettings)`) parecían deuda
  "del worker en general", pero el dueño real es el primer cambio que de hecho ejercita esa pieza con
  algo que importa (el cambio 7, primera tarea real del worker), no el cambio donde se encontró el
  hallazgo ni el que suena más relacionado a simple vista.
- **Regla**: antes de poner un dueño a un ítem de deuda, revisar `CHANGES.md` y `12_fichas_de_changes.md`
  y preguntar qué cambio es el primero que de verdad necesita que esa pieza esté resuelta. Asignarlo a
  cualquier otro deja la deuda sin dueño real: nadie la mira hasta que ya rompió algo.
- **Aplica a**: auditor.

## L-013 · Mutar para ver el rojo, sin commit, exige una copia previa y decirlo

- **Origen**: cambio 1c, cierre (constructor, verificación B2 de mutación).
- **Qué pasó**: con nada commiteado en el repo, no hay `git diff` posible contra "el código antes de
  la mutación": un `git diff` sobre un archivo sin trackear no compara nada. El constructor resolvió
  sacando una copia a un directorio temporal antes de cada mutación y comparando con `diff` contra esa
  copia, y lo dejó dicho explícitamente en vez de asumir que `git diff` alcanzaba.
- **Regla**: mientras un cambio no está commiteado, mutar código a propósito para ver un rojo exige
  sacar una copia previa (`git stash`, o un commit local temporal que se descarta después) y un diff
  real contra esa copia antes de seguir. Decirlo en el informe: una garantía contra una copia propia es
  más débil que `git diff` contra un commit conocido, y el que lee el informe tiene que saber cuál de
  las dos está mirando.
- **Aplica a**: constructor y rompedor.

## L-014 · `set -e` no actúa dentro de una función llamada a la izquierda de `||`

- **Origen**: cambio 1d, auditoría de la vuelta 2 (B2).
- **Qué pasó**: el modo continuo de `respaldar.sh` llama a cada ciclo como `ciclo_backup || true`
  (para no terminar el proceso ante una falla). Ese `|| true` apaga la propagación de `set -e` dentro
  de esa invocación: un paso posterior al volcado (el `mv`, la escritura de la marca, la retención)
  podía fallar sin frenar el script ni loguear la falla.
- **Regla**: todo paso que importa lleva su propio chequeo explícito (`if ! paso; then ...; fi`); no
  confiar en que `set -e` se vaya a propagar dentro de un contexto donde ya se usó `|| true` o
  equivalente. Los tests ejercitan el modo en que corre producción (el modo continuo), no sólo una
  corrida de un solo ciclo.
- **Aplica a**: constructor y rompedor.

## L-015 · Un `threading.Thread` no hereda las `ContextVar`, y una copia de contexto no se comparte entre hilos

- **Origen**: cambio 1d, auditoría de la vuelta 2 (B1).
- **Qué pasó**: lanzar las dos verificaciones de salud en hilos paralelos sin copiar el contexto
  perdía el `request_id` en el log de la verificación que terminaba tarde; usar una sola
  `contextvars.copy_context()` compartida entre los dos `Thread` daba
  `RuntimeError: cannot enter context: ... is already entered`.
- **Regla**: cada hilo que corre dentro de un pedido lleva su propia `contextvars.copy_context()`,
  nunca una compartida con otro hilo. Un test exige el `request_id` en las líneas de log de cada hilo.
- **Aplica a**: constructor.

## L-016 · Una observación tiene que poder dar otro resultado

- **Origen**: cambio 1d, auditoría de la vuelta 2 (B5).
- **Qué pasó**: el humo contaba los eventos `traceback_crudo_descartado` y `mensaje_no_texto` sólo en
  el servicio `respaldos`, que por ser un script de Bash nunca puede emitirlos: "0 apariciones" era
  estructuralmente cierto, sin decir nada sobre `api` ni `worker`, que sí pueden producirlos.
- **Regla**: antes de informar "0 apariciones" de un evento, nombrar qué servicio puede producir ese
  evento y mirar ahí. Una observación que no puede dar otro resultado no verifica nada.
- **Aplica a**: constructor y auditor.

## L-017 · La entrada de un chequeo es la del escenario, no una que otra capa ya rechaza

- **Origen**: cambio 1d, auditoría de la vuelta 2 (B4-bis).
- **Qué pasó**: el paso 7 del humo mandaba un `valor_cliente` que no era un UUID; la API ya lo
  descartaba y devolvía un UUID propio sin que Caddy tuviera que pisar nada, así que el chequeo pasaba
  aunque Caddy no cumpliera la propiedad que el paso dice probar. El rojo que respaldaba la marca `[x]`
  de la tarea se había mostrado con otra entrada (un UUID, pegándole directo a la API), no con la que
  el humo realmente manda.
- **Regla**: si una capa anterior descarta o reemplaza la entrada, el chequeo que sigue pasa sin tocar
  la capa que dice probar. Verlo fallar con otra entrada no prueba el chequeo tal como quedó escrito;
  la entrada de la demostración tiene que ser la del escenario real.
- **Aplica a**: constructor, rompedor y auditor.

## L-018 · Un chequeo de arranque tiene que verificar el efecto, no la forma

- **Origen**: cambio 2a, tres vueltas seguidas de auditoría (vuelta 1, R4; vuelta 2, V2-2; vuelta 3,
  V3-1).
- **Qué pasó**: el mismo defecto apareció disfrazado tres veces. En la vuelta 1, `despues()` prometía
  "verificar que el trigger y el `FORCE` sigan activos" y no verificaba nada (R4). En la vuelta 2, el
  gemelo: `DISABLE ROW LEVEL SECURITY` con el `FORCE` intacto pasaba `despues()` con `exit 0`, porque el
  chequeo miraba el atributo de catálogo (`FORCE` prendido) y no si RLS de verdad estaba habilitada
  (V2-2). En la vuelta 3, otro gemelo: `despues()` no miraba `pg_policy` en absoluto, así que una
  política de `auditoria` tocada a mano, o reemplazada por una más débil, pasaba con `exit 0` sin que
  nadie lo notara (V3-1).
- **Regla**: un chequeo de arranque que lee el catálogo (`FORCE`, un nombre de política, un trigger
  declarado) no prueba que el efecto exista; prueba que la forma está. Verificar el conjunto completo de
  lo que importa (la política entera, no su nombre; el comportamiento bloqueado, no el flag que debería
  bloquearlo) y, donde se pueda, probarlo con una caja negra real.
- **Costo**: tres vueltas completas de auditoría del mismo cambio gastadas en variantes del mismo
  defecto, cada una creyendo que la anterior ya lo había cerrado; de no aparecer en la vuelta 3, una
  política de `auditoria` editada a mano habría pasado el arranque sin que nadie se enterara.
- **Aplica a**: constructor y auditor.

## L-019 · Un test que no puede dar rojo es peor que no tenerlo

- **Origen**: cambio 2a, auditoría de la vuelta 1 (`test_roles.py:231`) y de la vuelta 2
  (`test_auditoria_transaccion.py:416`).
- **Qué pasó**: dos veces en el mismo cambio, un test nuevo estuvo en verde con el bloqueante todavía
  abierto. En la vuelta 1, `test_segunda_corrida_termina_sin_error_y_con_los_mismos_atributos`
  (`tests/integracion/test_roles.py:231`) corría `antes` dos veces sin la migración 0004 entre medio, y
  por eso pasaba con R1 abierto (el segundo `up` no levantaba nada). En la vuelta 2,
  `test_rojo_un_caso_marcado_que_no_registra_no_pasa_el_sweep`
  (`tests/integracion/test_auditoria_transaccion.py:416`) no corría el sweep, así que pasaba sin que
  V2-7 estuviera resuelto.
- **Regla**: un test marcado `[x]` como prueba de un arreglo tiene que mutarse a mano para verlo fallar
  con el defecto todavía presente (L-013, L-016), no alcanza con que pase después del arreglo: un test
  que nunca pudo dar rojo certifica silencio, no corrección, y ese silencio costó dos vueltas completas
  de auditoría en este mismo cambio.
- **Aplica a**: constructor y auditor.

## L-020 · Arreglar un bloqueante puede crear otro

- **Origen**: cambio 2a, auditoría de la vuelta 2 (V2-1).
- **Qué pasó**: el arreglo de R7 (que un `RESET` defensivo impida que el tenant contagie la conexión
  siguiente al volver al pool) rompía el pool entero ante un corte real de la base: un
  `pg_terminate_backend` hacía que el evento de "devolución al pool" disparara un `AttributeError` en
  vez del `OperationalError` esperado, y las dos conexiones siguientes se agotaban por `TimeoutError`.
  La corrección de un bloqueante (R7) generó uno nuevo y más grave (V2-1): el sistema quedaba
  inoperable ante cada corte de conexión, no sólo ante el error original.
- **Regla**: el arreglo de un bloqueante que toca el ciclo de vida de una conexión, una sesión o un
  recurso compartido necesita su propio ataque dedicado (acá, un corte real de la conexión con el
  evento cableado), no sólo la reproducción del caso que lo motivó. Cerrar R7 no probaba que el cierre
  no abriera V2-1.
- **Aplica a**: constructor y rompedor.

## L-021 · La instrucción del auditor acota lo que los demás miran

- **Origen**: cambio 2a, auditoría de las vueltas 2 y 3 ("acuerdo sospechoso").
- **Qué pasó**: en la vuelta 2, el auditor dictó exactamente qué casos re-correr para R4, R8 y R10; el
  rompedor los corrió y los dos coincidieron en "cerrado en su caso". Esa coincidencia no era dos
  revisiones independientes: era el mismo encuadre del auditor, copiado dos veces. Recién cuando el
  rompedor salió de ese encuadre por su cuenta aparecieron V2-2 y V2-4, que bloquearon. En la vuelta 3
  pasó lo mismo con V2-2: los dos verificaron sólo los tres casos que el auditor había dictado, y de ahí
  no salió nada nuevo; cuando el rompedor probó ocho variantes más por su cuenta, salieron V3-1, V3-2 y
  V3-3.
- **Regla**: cuando el auditor prescribe el caso exacto a verificar, un acuerdo entre auditor y rompedor
  sobre ese caso no es convergencia: es la misma instrucción leída dos veces. La verificación
  independiente tiene que incluir casos que el auditor no nombró, o declarar explícitamente que no los
  hubo.
- **Costo**: dos vueltas en las que el "acuerdo" entre auditor y rompedor dio una falsa sensación de
  revisión cerrada; los tres bloqueantes reales de cada vuelta (V2-2 y V2-4 en la 2; V3-1, V3-2 y V3-3
  en la 3) aparecieron recién cuando alguien salió del encuadre dictado, no cuando coincidieron dentro
  de él.
- **Aplica a**: auditor.
- **Ocurrencia (4a `cimientos-del-libro`, revisión del propose, 26/10/2026, `06-auditor.md`)**: la misma
  falla con otro canal. Al DBA le llegó como pregunta la hipótesis del arquitecto (AR-1, opción 2: "¿un
  trigger `FOR EACH STATEMENT` se dispara con `UPDATE t SET c = c WHERE false`?"), que no estaba en el
  brief común; la coincidencia entre AR-1 y DB-5 fue una verificación encadenada, no dos opiniones.
  Pasarle a un revisor la hipótesis de otro sirve para verificarla, pero **rompe la independencia**: si
  se hace, se declara en el informe consolidado y el acuerdo cuenta como uno.

## L-022 · Un chequeo que compara un resumen no ve lo que el resumen esconde

- **Origen**: cambio 2c, auditoría de la vuelta 2 (D-101).
- **Qué pasó**: cada arreglo de la vuelta 2 cerró el caso que lo había hecho caer, y el rompedor
  encontró el mismo agujero un nivel más abajo: el proxy cubría el puerto 80 y no el 443; el test del
  log miraba ERROR y no WARNING; el humo contaba políticas de RLS y no las leía, mientras un comentario
  afirmaba que una política más débil "también se ve".
- **Regla**: un chequeo de seguridad compara el conjunto completo contra su fuente (todo puerto
  publicado, todo nivel, la tupla entera de la política, la lista de servicios sacada de Compose), o
  declara en el mismo lugar qué deja afuera. Ningún comentario ni `[x]` afirma una cobertura sin el
  mutante que la muestra en rojo.
- **Costo**: tres bloqueantes en la vuelta 2 y la familia entera pasada como deuda al 15.

## L-023 · Una migración que agrega NOT NULL o CHECK rompe también fuera de `backend/`

- **Origen**: cambio 3a, cierre del bloque D (19/10/2026).
- **Qué pasó**: la migración `0005` agregó `localidad NOT NULL` a `complejo`. La suite de `backend/`
  no tenía ningún INSERT que la dejara afuera y pasó en verde; `infra/ci/humo.sh` siembra con `psql`
  directo, fuera de `backend/`, y nadie lo miró hasta la corrida completa después del bloque D: el humo
  rompió con "null value in column \"localidad\" violates not-null constraint". El arreglo fue sumar la
  columna a la siembra del humo (commit `05eaddd`).
- **Regla**: antes de cerrar una migración que agrega `NOT NULL` o un `CHECK`, buscar con `rg` todo
  `INSERT` a esa tabla en el repositorio entero, no sólo en `backend/`: el humo, los scripts de
  `infra/ci/` y cualquier semilla fuera del dominio pueden escribir en esa tabla sin pasar por la
  aplicación.
- **Costo**: una corrida de humo en rojo y un commit de arreglo (`05eaddd`).
- **Aplica a**: constructor, orquestador (en la verificación independiente de cada bloque).

## L-024 · Cada vuelta de arreglos es código nuevo sin mirada independiente

- **Origen**: cambio 3a, auditoría vuelta 1 (fila 4) y vuelta 2 (filas 1 y 2).
- **Qué pasó**: cada vuelta de correcciones la escribió, la probó y la dio por buena el mismo autor
  (Codex). El auditor lo marcó en la vuelta 1 ("nada de la vuelta de correcciones tuvo una segunda
  mirada": el trigger de `0011`, `texto.py` y el arreglo final los dio por buenos su propio autor) y
  otra vez en la vuelta 2 (fila 1: la guarda de autenticación, reescrita por Codex, sin revisor
  posterior; fila 2: las migraciones `0012`/`0013`, que cambian datos y permisos sobre bases
  existentes, "sólo las miró su autor"). Recién los revisores de rol de backend y DBA, convocados sobre
  el HEAD final (`334daf5`), encontraron RF-B-1 a RF-B-4 y RF-D-1 a RF-D-4; RF-D-1 (Generales mudable de
  edificio, por SQL) vivía en una migración ya aplicada (`0011`) y exigió una migración nueva (`0015`).
- **Regla**: cerrar una vuelta de arreglos con revisores de rol de sólo lectura sobre lo que tocó esa
  última vuelta, no con otra vuelta entera de rompedor sobre el cambio completo: el rompedor que ya
  recorrió el cambio entero tiende a no releer lo recién escrito con la misma sospecha.
- **Costo**: dos vueltas señaladas por el auditor sin corregirse hasta el cierre; un hallazgo real
  (RF-D-1) que vivía desde antes y se encontró recién al convocar un rol distinto.
- **Aplica a**: auditor, orquestador.

## L-025 · Un constructor no se revisa a sí mismo, y obedece el brief al pie de la letra

- **Origen**: cambio 3a, bloques B a E y las dos vueltas de corrección (Codex como constructor).
- **Qué pasó**: con el mismo autor escribiendo el test, el código y el mutante que lo prueba, el
  rompedor encontró 6 hallazgos en la vuelta 1 (R3A-1 a R3A-6) y 12 en la vuelta 2 (R3B-1 a R3B-12),
  todos en código que Codex había dado por terminado y probado. Codex además se ciñó al brief al pie de
  la letra: lo que el brief no nombraba (como la siembra del humo fuera de `backend/`, L-023) no lo
  miró, sin que eso fuera una falla de instrucción, sino el límite declarado de su alcance.
- **Regla**: con un constructor que no es el mismo modelo que revisa (Codex, u otro), el brief nombra
  explícitamente los consumidores fuera del área que toca (otros módulos, `infra/`, scripts); y el
  rompedor y el auditor son siempre de una familia distinta a la del constructor, nunca el mismo modelo
  revisándose.
- **Costo**: 18 hallazgos entre las dos vueltas, todos en la primera lectura externa del código de
  Codex.
- **Aplica a**: orquestador (al armar el brief), auditor.

## L-026 · Todos los tests en verde no dice nada sobre cómo se ve la pantalla

- **Origen**: cambio 3b, cierre (20/10/2026).
- **Qué pasó**: el bloque C (las cuatro primeras pantallas) cerró con biome, tsc, vitest y el barrido
  de Playwright en verde, y el orquestador no abrió el navegador hasta después de cerrado todo el
  bloque. Lo que vio ahí no lo mostraba ningún test: una columna angosta centrada con demasiado aire,
  sin lugar para la ayuda acoplada que pedía el shape. Hizo falta un pulido y, después, un rediseño a
  todo el ancho (D-105a) sobre un cambio ya "terminado" según su propia suite.
- **Regla**: cerrar una tarea de UI incluye mirarla con un navegador real, no sólo correr su suite; la
  mirada va después de cada bloque de UI, no sólo al final del cambio (axe y los chequeos de 320px
  prueban accesibilidad y layout roto, no si el diseño funciona).
- **Costo**: aproximadamente 1 hora de Opus en el pulido y rediseño, más una vuelta de revisión de
  Juani sobre las capturas de antes y después.
- **Aplica a**: orquestador (después de cada bloque de UI), constructor.

## L-027 · Una API falsa que acepta cualquier escritura esconde los errores de contrato

- **Origen**: cambio 3b, hallazgo R3C-1 del rompedor, destapado por R3C-10.
- **Qué pasó**: toda escritura real de la web (`fetch` del servidor de Next hacia la API) mandaba el
  cuerpo como `text/plain` en vez de `application/json`; contra la API real, FastAPI respondía 422 en
  cada guardado. Los 132 tests del barrido de Playwright (D7) pasaron igual: la API falsa de 3.8
  contestaba 200 con el fixture de lectura a cualquier `POST`/`PATCH`/`PUT`, sin mirar el
  `Content-Type` ni el cuerpo (R3C-10). El contrato estaba roto desde la primera pantalla y ningún
  test lo vio hasta el rompedor, con la API real.
- **Regla**: una API falsa para el navegador tiene que validar como la real (método, `Content-Type`,
  forma del cuerpo), no sólo devolver el fixture correcto; y los fixtures de lectura y escritura tienen
  que salir de la API real (D4), nunca de una API falsa que no se prueba a sí misma contra ese
  contrato.
- **Costo**: un hallazgo CRÍTICO del rompedor sobre algo que, de llegar a producción con el 2b, hubiera
  roto el 100% de las escrituras; arreglado en el mismo cierre, pero quedó abierto (MEDIA) que ningún
  spec de Playwright ejercita una escritura real contra la API falsa ya corregida.
- **Aplica a**: constructor (al escribir una API falsa), rompedor, auditor.

## L-028 · Las combinaciones de capas son donde fallan el foco y el Esc, y un componente solo no las ve

- **Origen**: cambio 3b, revisión de rol de frontend sobre el HEAD final (RF-F-1 a RF-F-4).
- **Qué pasó**: cada capa (menú, ayuda, panel lateral) tenía su test y pasaba sola. Combinadas,
  fallaron cuatro casos que ningún test de un componente aislado podía ver: `MenuDelEdificio`
  escuchaba `Esc` por su cuenta, fuera de la pila compartida, así que un `Esc` cerraba ayuda y menú a
  la vez por debajo de 768px (RF-F-1); abrir el panel desde el estado vacío y guardar dejaba el foco
  en `body` tras la revalidación (RF-F-2); con el panel abierto, abrir y cerrar la ayuda con `Esc`
  mandaba el foco al botón "Ayuda" en vez de quedarse en el panel (RF-F-3); y con ayuda y panel
  abiertos a la vez (desde 1024px), cerrar la ayuda con teclado exigía cerrar el panel entero (RF-F-4).
- **Regla**: las combinaciones de capas que coexisten en una pantalla real (menú + ayuda, ayuda + panel,
  las tres juntas) necesitan su propio test de integración, además del test de cada componente por
  separado: el aislamiento que hace fácil probar un componente es exactamente lo que esconde estos
  cuatro casos.
- **Costo**: cuatro hallazgos de foco/teclado (una MEDIA, dos BAJA) recién vistos en la revisión de rol
  sobre el HEAD final, no en ninguna de las suites de los componentes.
- **Aplica a**: constructor (al escribir el test de una pantalla con más de una capa abierta), revisor
  de rol de frontend.
- **Aplica a**: constructor y rompedor.

## L-029 · La firma del cambio no firma por sí sola sus correcciones posteriores

- **Origen**: cambio 2.2a, auditoría, hallazgo ALTO, 20/10/2026.
- **Qué pasó**: después de la firma de E1 a E8 entraron una regla nueva de base (consejo único,
  migración 0018) y un texto nuevo de 403. El brief del orquestador decía que corregir al rompedor
  estaba dentro del alcance, pero eso no era una firma del socio sobre esas reglas nuevas. Juani
  firmó RR-1 a RR-4 aparte en `610eb4a`.
- **Regla**: una regla nueva de base o de texto que entra después de la firma necesita su propia
  aprobación escrita y fechada del socio; el constructor no atribuye esa aprobación al socio por
  inferencia del brief.
- **Aplica a**: orquestador, constructor y auditor.

## L-030 · El brief separa las resoluciones de orden de las decisiones de permisos

- **Origen**: cambio 2.2a, primera vuelta del bloque A, 20/10/2026.
- **Qué pasó**: con el pedido "no improvises", Codex completó sólo 1.1 y frenó ante conflictos de
  orden o redacción. Hizo falta otro brief para distinguir esos ajustes de las decisiones sobre
  quién puede hacer qué.
- **Regla**: el brief declara qué conflictos de orden o texto puede resolver el constructor, dejando
  autoría y motivo, y qué cambios de permisos debe llevar al socio. "No improvises" solo no define
  ese límite.
- **Aplica a**: orquestador (al escribir el brief) y constructor.

## L-031 · La evidencia de cierre corresponde al último commit del bloque

- **Origen**: cambio 2.2a, cierre 7.2, 20/10/2026; precisa L-010.
- **Qué pasó**: una corrida previa a los últimos commits del bloque obligó a repetir el backend para
  tener evidencia del código final; costó unos 8 minutos adicionales en 7.2.
- **Regla**: las suites de cierre van después de los últimos commits del bloque; se anota el SHA de
  cada corrida. Si cambia el código después, se repite la verificación sobre el commit final antes
  de marcar el cierre.
- **Aplica a**: constructor, orquestador y auditor.

## L-032 · El doble falso de un proveedor de identidad no modela su modo restringido

- **Origen**: cambio 2b `login-y-usuarios`, verificación real (8.2), 21/10/2026.
- **Qué pasó**: contra Clerk real en modo *invite-only*, el mail de invitación llega a
  `/invitacion/<sobre>` con `__clerk_ticket` en la URL. Esa página y el link "Crear cuenta desde mi
  invitación" armaban los links a `/ingresar` y `/registrarse` sólo con `regreso`: `<SignUp>` nunca
  veía el ticket y Clerk respondía "El acceso a esta funcionalidad está restringido en este momento".
  Todos los tests e2e pasaban: el Clerk falso de ese arnés (`web/e2e/prueba.ts` aborta toda red hacia
  `clerk.*`/`cloudflare.*`) no tiene frontend API falso de Clerk, así que ningún test podía ver el
  rechazo por falta de ticket.
- **Regla**: cuando un proveedor externo tiene un modo restringido o invite-only, el doble falso de
  los tests automáticos no alcanza para probarlo: ese modo se verifica contra la instancia real del
  proveedor (ver `14_forma_de_trabajo.md`, "Verificación real con un servicio externo de identidad”),
  y se declara como SUPUESTO mientras no haya un doble falso que lo modele.
- **Costo**: un hallazgo que sólo apareció con Juani al teclado contra Clerk real, después de que 2259
  tests de backend y 385 de web pasaran en verde; arreglado el mismo día (`90131a6`).
- **Aplica a**: constructor (al escribir el doble falso de un proveedor externo), orquestador (al
  decidir qué va a verificación real).

## L-033 · Un test de infraestructura no puede suponer una carpeta real vacía

- **Origen**: cambio 2b, corrida de cierre (9.2), 21-22/10/2026.
- **Qué pasó**: dos tests de `backend/tests/infra/` suponían que `infra/datos-respaldos/` estaba
  vacía: uno creaba un archivo de prueba y hacía `rmdir()` al final; el otro recorría `infra/**/*` con
  `rglob` y leía cada archivo como texto. En cuanto el README manda crear esa carpeta y el stack real
  la llena con backups (`.dump` binarios), los dos fallan: `rmdir()` con "Directory not empty" y el
  `rglob` con `UnicodeDecodeError` al leer un binario como UTF-8.
- **Regla**: un test que toca una carpeta real del repositorio (no una temporal propia) nunca asume su
  contenido; recuerda si existía antes de tocarla, usa un nombre de archivo propio que no pueda pisar
  un dato real, y recorre sólo lo versionado (`git ls-files`) en vez de todo el filesystem cuando lo
  que busca es código, no datos.
- **Costo**: dos corridas completas de `test-backend.sh` (≈20 minutos) repetidas por una falla de
  infraestructura, no del código del cambio.
- **Aplica a**: constructor (al escribir un test contra una carpeta real), rompedor.

## L-034 · Un mutante que rompe la autenticación no prueba una aserción de aislamiento

- **Origen**: cambio 2b, corrección post-rompedor RB2b-post-4, 21/10/2026.
- **Qué pasó**: el RED de un test de aislamiento (identidad vinculada sólo a B no ve nada de A) mutaba
  `info={"identidad_clerk": sub}` → `info={"identidad_clerk_mutada": sub}` en `base_de_datos.py`. Eso
  rompe la autenticación entera (401 en vez del 200 esperado) y el test falla, pero por el motivo
  equivocado: no prueba que la política de aislamiento filtre, prueba que sin identidad nada entra,
  algo que ya cubren otros tests.
- **Regla**: un mutante que hace fallar un test tiene que fallar **en la aserción que el test dice
  probar**, no en un paso anterior de la cadena (acá, la resolución de identidad). Con defensa en
  profundidad (dos capas independientes, como `identidad.py` y la política RLS de la migración 0019),
  se verifica cada capa por separado antes de combinarlas: mutar sólo una tiene que dejar a la otra
  filtrando igual y el test en verde; el rojo real sale de quitar el filtro en las dos a la vez.
- **Costo**: un RED mal elegido que parecía válido (el test fallaba) pero no ejercitaba lo que decía
  probar; corregido en la misma vuelta, sin cambiar el código de producción.
- **Aplica a**: constructor y rompedor (al elegir qué mutar para un RED), auditor (al leer si el rojo
  cae en la aserción correcta).

## L-035 · Un test que existe no es un test que vigila

- **Origen**: auditoría de cimientos, 22/10/2026 (informes `03-dba.md` y `07-deuda-y-kb.md`, cierre
  en `7555b59`/`d63a409` y `8b8ee52`/`437466b`).
- **Qué pasó**: dos garantías distintas tenían un archivo de test, y ninguna estaba realmente
  vigilada. El tenant por transacción (D4) tenía su test en verde, pero el reset de checkin (R7) lo
  tapaba: cualquier mutante que cambiara el `SET LOCAL` por un `SET` de sesión seguía dando verde,
  porque el cinturón de seguridad entraba antes de que el mutante importara. El control de dueño de
  las tablas de sólo agregar tenía un sólo caso (`configuracion_versionada`), marcado `xfail`: el
  archivo existía, corría en CI, y no tenía ni un caso **verde** que probara que el discriminante
  funcionaba cuando debía fallar.
- **Regla**: que un test exista y corra en CI no dice que vigile la garantía que nombra. Antes de
  confiar en él, se verifica que (a) tenga al menos un caso verde real, no sólo casos `xfail`, y (b)
  un mutante dirigido a la garantía específica (no a un paso anterior de la cadena, L-034) lo haga
  fallar. Un test sin esas dos cosas es un archivo con el nombre de una garantía, no la garantía.
- **Costo**: dos garantías centrales del aislamiento multi-tenant (D4 y el dueño de las tablas de
  sólo agregar) llevaban días o semanas sin vigilancia real, descubierto sólo por la auditoría de
  cimientos, no por el ciclo normal de construcción.
- **Aplica a**: constructor (al escribir el primer test de una garantía nueva), rompedor, auditor.

## L-036 · El discriminante de un permiso de dueño en Postgres es `NO FORCE ROW LEVEL SECURITY`, no `DISABLE TRIGGER ALL`

- **Origen**: auditoría de cimientos, 22/10/2026 (`03-dba.md`, DBA-1; test en `8b8ee52`).
- **Qué pasó**: la sonda obvia para probar "quién es dueño de esta tabla" parecía ser
  `ALTER TABLE ... DISABLE TRIGGER ALL`: si el rol puede desactivar los triggers, es dueño. Falla
  como discriminante porque toda tabla con una foreign key tiene triggers internos de Postgres
  (`RI_ConstraintTrigger_*`, marcados `tgisinternal=true`) que exigen **superusuario** para
  desactivarse con `ALL`, sin importar quién sea el dueño real: tanto `auditoria` (dueño el rol de
  arranque) como `configuracion_versionada` (dueño el migrador) daban el mismo
  "permission denied: ... is a system trigger", escondiendo la diferencia real entre las dos.
  `ALTER TABLE ... NO FORCE ROW LEVEL SECURITY` sí discrimina: Postgres lo exige únicamente al dueño
  (o a un superusuario), sin triggers de por medio, y es universal para cualquier tabla con RLS
  forzada (D5 ya lo exige en todas las de `_TABLAS_DE_SOLO_AGREGAR`).
- **Regla**: al probar quién es dueño de una tabla en PostgreSQL, el discriminante es una operación
  que **sólo el dueño** puede hacer sin más permiso (como `NO FORCE ROW LEVEL SECURITY` o cambiar su
  dueño), nunca una que además requiera un privilegio de servidor (superusuario) que tapa la
  diferencia entre "dueño" y "no dueño". Antes de adoptar una sonda de permisos, confirmarla a mano
  contra dos tablas con dueños distintos conocidos.
- **Costo**: ninguno en producción; detectado y corregido dentro del mismo informe, antes de
  commitear el test con la sonda equivocada.
- **Aplica a**: DBA, constructor (al escribir un test de permisos sobre PostgreSQL).

## L-037 · Después de un push a `main`, se espera el CI completo antes de decir "listo"

- **Origen**: auditoría de cimientos, 22/10/2026 (`04-devops.md`, OPS-1; arreglos `ad5bc90` y
  `55e18a0`).
- **Qué pasó**: dos rojos de `main` el mismo día, los dos por la misma causa raíz. `ad5bc90` subió el
  timeout del job `backend` a 30 minutos para que el canario no lo cortara, pero no esperó a que el
  propio CI corriera `test_ci_workflow.py` (que fija ese número en un test) antes de considerar
  resuelto el problema: ese test seguía esperando 20 minutos, y `main` quedó en rojo
  (run 39795326523) hasta `55e18a0`. El mismo día, un arreglo anterior (`rg` ausente del runner de
  GitHub en el script de humo) se dio por bueno sin ver el run completo en verde.
- **Regla**: un arreglo de CI (o cualquier push a `main`) no se declara terminado por "el cambio es
  correcto a simple vista" ni por corridas locales: se espera el run completo de GitHub Actions sobre
  ese commit y se lee su resultado antes de decir "listo" o de seguir con el siguiente arreglo. Si el
  run tarda, se espera; no se apila un segundo arreglo sobre un primero sin confirmar.
- **Costo**: dos rojos de `main` en un mismo día, con el arreglo correcto demorado por no haber
  esperado la confirmación del primero.
- **Aplica a**: quien toca `.github/workflows/`, orquestador (antes de reportar un arreglo de CI como
  cerrado).

## L-038 · Quien firma no puede agregarse a la lista de firmantes en su propio PR

- **Origen**: revisión del PR #1 de `acceso-de-desarrollo`, 25/10/2026 (`04-arquitecto.md`, AR-1 a
  AR-3; `05-auditor.md`). Corregido con D-111.
- **Qué pasó**: el PR que cerraba el change reescribió D-094 para sumar a Emiliano como firmante
  (en un archivo que "sólo se agrega"), le atribuyó a Juani, con fecha 14/10, una ampliación que el
  repo no registraba, y en ese mismo PR Emiliano firmó el change con esa habilitación. Además dejó a
  `CLAUDE.md` diciendo tres nombres y a `config.yaml` y a otras líneas del propio `CLAUDE.md`
  diciendo dos: quién firmaba el próximo change CRITICAL pasaba a depender de qué archivo leía primero
  cada agente.
- **Regla**: ampliar quién firma es una decisión nueva (D-NNN) con Juani como Quién, que corrige en
  parte a la anterior sin reescribirla, y que se mergea **antes** y en otro PR que el de la primera
  firma que la usa. En ese mismo cambio se alinean todas las fuentes que nombran firmantes
  (`config.yaml`, `14`, `CLAUDE.md`, `AGENTS.md`).
  La propia D-111 entró en el mismo PR que la firma que ratifica: fue una excepción autorizada por
  Juani el 25/10/2026, porque el change ya estaba construido y firmado; no es precedente.
- **Costo**: la firma del change, su "archivado OK" y las tareas marcadas quedaron en duda hasta que
  Juani ratificó con D-111; un PR de cierre volvió a revisión.
- **Aplica a**: quien firma, orquestador (al aceptar una firma), auditor.

## L-039 · "Verificado a mano" a través del login necesita escrito el paso de vinculación de identidad

- **Origen**: revisión del PR #1 de `acceso-de-desarrollo`, 25/10/2026 (BE-1, DB-6, AR-7 y QA-4;
  `05-auditor.md`).
- **Qué pasó**: el cierre decía que las siete pantallas se recorrieron entrando con Clerk de
  desarrollo como el `super_admin` del ejemplo, pero esa persona se crea sin `clerk_usuario_id` y el
  código no tiene otro camino para vincularla que aceptar una invitación, que el ejemplo no crea.
  Cuatro revisores llegaron a "debió ser un `UPDATE` a mano" y ninguno lo pudo verificar: la
  coincidencia de los cuatro no la volvió evidencia.
- **Regla**: una verificación manual que pasa por el login no está hecha hasta que quede escrito,
  paso por paso, cómo la cuenta usada quedó vinculada a la persona (comando, rol, base), con las
  capturas o la salida. Sin ese paso no se puede repetir, y lo que no se puede repetir no cuenta como
  evidencia, por más revisores que lo deduzcan igual.
- **Costo**: la tarea 1.1 quedó sin poder reproducirse; el vínculo queda como deuda a cargo de
  Emiliano ("Deuda del cierre de `acceso-de-desarrollo`", `12_fichas_de_changes.md`).
- **Aplica a**: constructor (al cerrar una tarea con verificación manual), rompedor, auditor.

## L-040 · Un email de prueba que no llega puede ser el proveedor, no el rol: cambiar una variable por vez

- **Origen**: QA manual del 23/10/2026 sobre el 2b, previo a `acceso-de-desarrollo` (antes en la
  sección de hallazgos de `CLAUDE.md`; pasó acá el 26/10/2026 con la exploración del 3c).
- **Qué pasó**: las invitaciones a direcciones de prueba cuya parte local contenía la palabra "admin"
  no llegaban: cuatro rechazadas por Clerk de desarrollo (HTTP 422 y 400 en los logs del worker),
  mientras tres sin "admin" llegaban. Como esas direcciones eran justo las de los roles de
  administrador, la primera lectura fue un bug de rol. Una segunda ronda con dos direcciones nuevas
  sin "admin" llegó en segundos; según el QA, el resultado no dependía del rol asignado. El código de invitación
  (`backend/src/proptech_core/acceso/aplicacion/usuarios.py`) no tiene ninguna rama distinta según el
  rol. Lo más probable es un filtro anti-phishing de Clerk sobre el texto del email; **no está
  confirmado con Clerk**.
- **Regla**: las direcciones de prueba no llevan "admin" (ni otras palabras de cuenta privilegiada) en
  la parte local. Y cuando una prueba de punta a punta con un proveedor externo falla, antes de buscar
  el bug en el dominio se cambia **una sola variable por vez** (el texto del email con el mismo rol, y
  el rol con el mismo texto) y se lee la respuesta del proveedor en los logs. Las direcciones usadas no
  se escriben en el repo: es público y las bandejas de Mailinator también (BE-7, P67).
- **Costo**: dos rondas de prueba y un hallazgo de "bug de rol" que no era del código.
- **Aplica a**: QA, rompedor y quien verifique a mano algo que manda emails (2b, 13, 15).

## L-041 · Si una tarea agrega un chequeo que bloquea el arranque, su verde es la suite completa

- **Origen**: 4a `cimientos-del-libro`, auditoría del apply, vuelta 1 (`12-auditor-apply.md`, 26/10/2026).
- **Qué pasó**: la 5.3 agregó el chequeo que impide arrancar si una tabla de sólo agregar tiene otro
  dueño y marcó verde con su grupo ("102 passed"). Ese mismo cambio rompió 357 tests de otros
  archivos, que levantaban la app o armaban bases sin el paso de roles; salieron recién en la corrida
  de cierre (7.1). El `[x]` era verdadero sobre lo que corrió y falso sobre lo que rompió.
- **Regla**: una tarea que agrega un chequeo de arranque (o cualquier cosa que corre en toda fixture
  que levante la app o la base) cierra con la suite completa, no con la de su grupo. "No hay fallos
  pendientes de esos conjuntos" no es un verde.
- **Costo**: dos informes de constructor (uno con un diagnóstico equivocado de la causa) y el commit
  `e57ccd0` para rearmar las bases de test como el deploy real.
- **Aplica a**: constructor, auditor (al leer un `[x]`).

## L-042 · Este repo no corre CI en una rama sin PR: "pusheé" no es "leí el CI verde"

- **Origen**: 4a `cimientos-del-libro`, auditoría del apply, vuelta 1 (`12-auditor-apply.md`).
- **Qué pasó**: la rama `change/cimientos-del-libro` estaba pusheada y se daba por corriendo en CI,
  pero `.github/workflows/ci.yml` sólo se dispara con push a `main`, `pull_request` o
  `workflow_dispatch`: `gh run list --commit 25bbaa7` estaba vacío. Se cerró con `gh workflow run CI
  --ref change/cimientos-del-libro` sobre el SHA final.
- **Regla**: antes de citar el CI de una rama, `gh run list --commit <sha>`; si está vacío, se dispara
  (`workflow_dispatch` o un PR) y se lee el run sobre ese SHA. Complementa L-037, que es sobre `main`.
- **Costo**: la 7.1 bloqueada una vuelta por un CI que nunca había existido.
- **Aplica a**: orquestador, constructor, auditor.

## L-043 · Un script de mantenimiento que no está en el CI se ejecuta en su test o en el cierre

- **Origen**: 4a `cimientos-del-libro`, RB-1 del rompedor y auditoría del apply (`11-rompedor.md`,
  `12-auditor-apply.md`, `14-auditor-final.md`).
- **Qué pasó**: `infra/ci/ensayo-roles.sh` quedó roto por el 4a (no devolvía `configuracion_versionada`
  al migrador antes del `downgrade 0016`, `must be owner`). `test_ensayo_login` sólo compara un número
  de revisión en el texto del script, así que siguió verde. Dos agentes lo afirmaron con "confianza
  alta" sin correrlo; recién al correrlo en un compose aislado se vio el rojo y después el verde.
- **Regla**: si un script de mantenimiento (ensayo, restauración, rollback) no corre en CI, o su test
  lo ejecuta, o el cierre del change que lo toca lo corre y pega comando y salida. Leer el texto no lo
  prueba. Se corre con un `COMPOSE_PROJECT_NAME` propio, nunca contra `proptech`.
- **Costo**: una vuelta de verify entera (RB-1 bloqueante) y el arreglo `c345467`; el ensayo sigue sin
  CI (deuda del 4a).
- **Aplica a**: constructor, rompedor, auditor.

## L-044 · Un timeout se sube mirando el tiempo de cada paso, no el del job

- **Origen**: 4a `cimientos-del-libro`, auditoría final (`14-auditor-final.md`, 26/10/2026).
- **Qué pasó**: el job `web` se cortó dos veces por el límite de 15 minutos (run 40357665108). Por paso,
  la instalación de Chromium tardaba 10 minutos y los tests del navegador ya daban success en el
  intento 2; el cuello no eran los tests. Se subió a 25 minutos (`6f6fe6b`); la corrida siguiente
  instaló Chromium en 25 segundos y el job entero tardó 7.
- **Regla**: antes de tocar un `timeout-minutes`, leer la duración de cada paso del run cortado y
  nombrar el que se pasa. Si es un paso de instalación, el arreglo de fondo es cachearlo; subir el
  límite sólo compra margen. Y como dice L-037, `test_ci_workflow.py` fija ese número: se espera el run.
- **Costo**: dos corridas del job `web` perdidas y un commit de CI extra antes de poder cerrar la 7.1.
- **Aplica a**: quien toca `.github/workflows/`, orquestador.

## L-045 · El scratchpad es un canal compartido entre revisores que ningún prompt cierra

- **Origen**: 4a `cimientos-del-libro`, revisión del propose (`06-auditor.md`, 26/10/2026).
- **Qué pasó**: los cinco revisores de rol escribían en el mismo scratchpad; QA pudo ver `reglas.py` e
  `imports.py` del arquitecto. No se sabe si los abrió, y por eso no se puede afirmar que su acuerdo con
  el arquitecto fuera independiente.
- **Regla**: revisores que tienen que ser independientes trabajan en directorios separados (uno por
  revisor) y no leen el de los otros. Si eso no se puede garantizar, el informe consolidado lo declara
  y un acuerdo entre ellos cuenta como una sola opinión.
- **Costo**: la independencia de QA quedó como supuesto en el veredicto del propose.
- **Aplica a**: orquestador (al lanzar revisores), auditor.

## L-046 · Una prueba sobre la implementación propia del revisor es evidencia de esa implementación, no del design

- **Origen**: 4a `cimientos-del-libro`, revisión del propose (`06-auditor.md`, QA-3 y AN-1).
- **Qué pasó**: QA escribió su propia versión del orden natural y mostró que levantaba `TypeError` al
  comparar un entero con un texto; lo informó con confianza alta como falla del design. El `TypeError`
  dependía de cómo QA lo había implementado ("la implementación ingenua"), no de lo que el design
  decía.
- **Regla**: si un revisor prueba un design escribiendo su propio código, el resultado se archiva como
  evidencia de **ese** código y la conclusión sobre el design como juicio, con la confianza bajada a
  media. Lo que cuenta es mostrar que el design permite o exige esa implementación.
- **Costo**: un hallazgo sobrecalibrado que el auditor tuvo que bajar; el design terminó fijando los
  tramos etiquetados `(0, int)` y `(1, texto)` para que no haya lectura posible que compare tipos
  distintos.
- **Aplica a**: revisores de rol (QA, analista), auditor.

## L-047 · `humo.sh` fija su propio proyecto de Compose e ignora la variable que lo parametriza

- **Origen**: 4b `libro-de-movimientos`, constructor Codex de las fases 4 a 6
  (`.git/informes-libro-de-movimientos/15-constructor-codex-fases-4-6.md`, SUPUESTO/límites).
- **Qué pasó**: `infra/ci/humo.sh` corre con `-p proptech` fijo en el script, sin leer
  `PROPTECH_COMPOSE_PROYECTO`. El cierre de este change lo esquivó con un clon limpio y un envoltorio
  de Docker que exige `PROPTECH_COMPOSE_PROYECTO=proptech-cierre-4b` y fuerza `-p` aislado desde
  afuera del script; si ese envoltorio no se usa, `humo.sh` corre sobre el proyecto `proptech` real
  sin avisar, con el riesgo de pisar o destruir el stack que ya está corriendo.
  - 4a ya había dejado una deuda parecida (`RB-7`, variable `PROPTECH_COMPOSE_PROYECTO` exportada que
    se filtra a `restaurar.sh`, en `knowledge-base/12_fichas_de_changes.md` §"4a · deuda del cierre").
- **Regla**: ningún script de `infra/ci/` que compone contra una base real asume su propio nombre de
  proyecto; lee la variable de entorno o falla si no está, y quien lo corre sobre un entorno que no es
  descartable comprueba primero con qué `-p` va a correr.
- **Costo**: deuda que sigue abierta (el script no se reescribió en este scope); el riesgo real es
  correrlo una vez sin el envoltorio contra un `proptech` con datos reales.
- **Aplica a**: quien toque `infra/ci/humo.sh` o `restaurar.sh` (ya nombrado en la ficha 4, deuda del
  4a).

## L-048 · El role-implementer no construye CRITICAL por su cuenta: la firma humana no le llega por ningún canal que pueda verificar

- **Origen**: 4b `libro-de-movimientos`. **JUDGMENT** (confianza media, no es una cita literal):
  `openspec/changes/archive/2026-10-27-libro-de-movimientos/tasks.md:651` registra "Constructor:
  Claude (Opus), **en la sesión de Juani**, con la tabla de Aprobación firmada por él", y la fase 1 la
  empezó Codex; la regla general que explica por qué está en `~/.claude/agents/role-implementer.md`
  ("Ahí la aprobación es humana, y la aprobación humana vive en la conversación entre la persona y el
  orquestador. No viaja hasta vos por ningún medio que puedas verificar").
- **Qué pasó**: el apply de las fases CRITICAL de este change no lo hizo un `role-implementer`
  despachado como sub-agente aparte: lo hizo Claude corriendo directamente en la sesión de Juani (que
  sí puede ver la firma en la conversación) o Codex.
- **Regla**: el apply de una tarea CRITICAL no se despacha a un `role-implementer` genérico esperando
  que encuentre la firma en `tasks.md` o en su propio prompt; ninguno de los dos es un canal
  verificable. Va a Codex, o a un fork del orquestador que ya tiene la conversación con el OK directo
  de la persona.
- **Costo**: ninguno nuevo en este change (el patrón ya se usó), pero sin esta nota el próximo
  constructor podría intentar despachar un `role-implementer` suelto a una tarea CRITICAL y
  encontrarse con el mismo freno sin saber por qué.
- **Aplica a**: orquestador, al decidir quién construye una tarea CRITICAL.

## L-049 · Un "rojo" contra stubs vacíos puede caer en un helper, no en la aserción que el test dice probar

- **Origen**: 4b `libro-de-movimientos`, auditoría de las fases 1 a 3
  (`.git/informes-libro-de-movimientos/12-auditor-fases-1-3.md`, hallazgo 1).
- **Qué pasó**: los 15 rojos de `test_cc_correcciones.py` (sección 3.5) morían en el helper `emitir`
  (`test_cc_correcciones.py:59`, `NoResultFound`) porque el stub de emisión no escribía nada; ningún
  test llegó a su propia aserción. El registro del constructor no decía esto, y el salto de TDD
  tampoco figuraba en `tasks.md`.
- **Regla**: un RED contra stubs vacíos se lee línea por línea del traceback para confirmar que cae
  en la aserción propia del test, no en un helper compartido; si cae en el helper, ese rojo no vale y
  hay que repetirlo después de que el helper funcione lo mínimo.
- **Costo**: 15 rojos de la fase 3 quedaron sin valer como evidencia; los mutantes de esa sección
  compensaron parte del hueco, pero no todo (ver también las 4 FK a `complejo` sin revisar, mismo
  informe).
- **Aplica a**: constructor (quien declara el rojo), auditor (quien lo revisa).

## L-050 · El navegador local puede dar rojo por el entorno de sesión de Clerk sin que la web haya cambiado: el juez es el job `web` del CI

- **Origen**: 4b `libro-de-movimientos`. Local: `.git/4b-fase1-logs/cierre-6.1/03-cierre-navegador.log`
  (34 failed, 138 passed; fallas en `sesion.spec.ts` y otros specs por el handshake de Clerk). CI:
  `.git/informes-libro-de-movimientos/16-auditor-final.md` (`$ gh run view 40529402406 --json
  headSha,conclusion,jobs` -> `headSha 8d25bd68… success`, con `secretos/shellcheck/backend/humo/web =
  success`).
- **Qué pasó**: la corrida de navegador local del cierre 6.1 dio 34 tests caídos por el handshake de
  sesión de Clerk, pero corrió sobre un SHA anterior (`c08b623`/`7ffc2fc`) y en un entorno cuya sesión
  de Clerk no está armada igual que el runner del CI. El run real del CI sobre el SHA que importaba
  (`8d25bd6`) tuvo el job `web` en `success`.
- **Regla**: un rojo del navegador corrido a mano no se lee como "la web se rompió" sin mirar antes
  sobre qué SHA corrió y si el entorno de sesión de Clerk es comparable al del CI; el juez de la web
  es el job `web` del workflow, no la corrida local.
- **Costo**: casi una alarma falsa de "la web se rompió" durante el cierre; se resolvió comparando
  SHAs antes de escalarlo.
- **Aplica a**: quien cierra un change y corre el navegador a mano antes del CI.

## L-051 · Arreglar el campo que encontró el QA no deja una regla para el campo que todavía no existe

- **Origen**: QA manual del 23/10/2026 (identificador de unidad, coeficiente, clave de grupos y
  categorías); propose del 3c `pulido-de-la-configuracion`, 26/10/2026 (observación de Emiliano sobre
  el design).
- **Qué pasó**: los tres hallazgos (G-1, G-2, G-3) se arreglaron con tres constantes nuevas, una por
  campo (D7 del 3c): el máximo del identificador, el rango del coeficiente y el patrón de la clave,
  usados en el input, la ayuda y el mensaje de error. Cada arreglo es correcto para su campo, pero
  ninguno queda escrito como regla que un campo nuevo, en otra pantalla, en otro change, tenga que
  seguir. El próximo campo que alguien agregue puede repetir exactamente el mismo problema (un mensaje
  genérico que no dice el formato esperado) sin que nada del código ni de la revisión lo atrape.
- **Regla**: cuando un hallazgo de QA es "este campo no dice su formato antes de fallar", el arreglo
  tiene dos partes: la constante puntual del campo (como D7) **y** una línea en `impeccable` o en la
  convención de formularios del proyecto que diga, en general, "todo campo con un límite o un patrón
  lo muestra en la ayuda y en el error, desde una constante compartida con el backend" — para que el
  próximo campo nazca cumpliéndola, en vez de que alguien tenga que encontrarla rota de nuevo.
- **Costo**: ninguno todavía — se detectó antes de construir, al revisar el propose del 3c, no después
  de que el próximo campo repitiera el bug.
- **Aplica a**: quien proponga un change con formularios nuevos; frontend al revisar; `impeccable` como
  dueña de la convención transversal.

## L-052 · Un `<select>` no controlado necesita una opción vacía explícita, o selecciona la primera sin que nadie la haya elegido

- **Origen**: 3c `pulido-de-la-configuracion`, tarea 6.2 (`unidades/Pantalla.tsx`), hallazgo F2 del
  design (corrección sobre el propose del 26/10/2026) y confirmado al construir el 27/10/2026.
- **Qué pasó**: el campo "Piso" del padrón se renderiza con `CampoDeLista` +
  `vocabularioDePisos(pisos, subsuelos)`. Una unidad migrada sin piso elegido tiene `piso: null` en la
  API. Si el `<select>` arranca sin ninguna opción con `value=""`, el navegador selecciona la primera
  opción real de la lista al abrir el panel — y si el formulario se envía sin que nadie haya tocado el
  campo, el `FormData` manda esa primera opción como si el administrador la hubiera elegido: un piso
  inventado, exactamente lo que E5 del 3c prohíbe (migrar sin inventar ningún valor). El mismo riesgo
  aplica a cualquier `<select>` no controlado cuyo valor pueda ser `null`/"sin completar": las listas de
  ubicación (provincia/departamento/localidad) de la misma tarea 6.1 tienen el mismo problema y la misma
  solución.
- **Regla**: todo `<select>` que representa un campo que puede estar "sin completar" lleva una primera
  `<option value="">` explícita (deshabilitada si el navegador lo permite) y el `defaultValue`/`value`
  del campo usa `??  ""`, nunca deja que el `<select>` cayera en su comportamiento por default. Un test
  que abre el panel con el dato en `null` y verifica `piso.value === ""` (la opción vacía, no la
  primera real) antes de tocar nada, y que el `FormData` de un envío sin cambios manda `""`, nunca el
  primer valor del vocabulario.
- **Costo**: ninguno — se detectó en la corrección del propose (F2), antes de construir, y el test que
  lo prueba (`"Abrir una unidad migrada no guarda ningún piso solo"`) nació escribiéndose contra la
  implementación ya completa.
- **Aplica a**: cualquier `<select>` nuevo sobre un dato nullable, en cualquier pantalla; frontend al
  revisar un combobox nuevo.

## L-053 · Un overlay de "toda la fila clickeable" tapa cualquier botón propio que se agregue a esa fila después

- **Origen**: 3c `pulido-de-la-configuracion`, recorrido manual 7.1 (27/10/2026), pantalla de grupos.
- **Qué pasó**: `.lista-de-filas--tocable` (`tokens.css`) le agrega al link/botón del título un
  `::after` con `position: absolute; inset: 0`, que se estira contra el `<li>` entero (`position:
  relative`) para que toda la fila sea clickeable como el título — pensado para listas donde la fila
  entera navega a un solo destino (como "mis edificios"). La tarea 6.3 reusó esa misma clase de lista
  para grupos y categorías, pero les agregó un botón propio (Desactivar/Reactivar) en el costado
  (`fila-con-icono__fin`). Un elemento posicionado siempre pinta arriba de uno estático sin importar
  el orden del DOM, así que ese overlay invisible terminó tapando el botón del costado: clickear
  "Desactivar" en realidad activaba el link de "editar". No lo agarró ningún test porque
  `@testing-library/react` dispara el evento directo sobre el botón de JSX, sin simular el layout real
  del navegador (`getBoundingClientRect`/stacking context) — sólo apareció al click real en pantalla.
- **Regla**: antes de reusar una clase de lista "toda la fila clickeable" en una pantalla que además
  tiene botones propios en el costado de la fila, darle a esa zona (`fila-con-icono__fin` u
  equivalente) su propio `position: relative; z-index` por encima del overlay. Un test automatizado
  de click no alcanza para esto — hace falta probarlo con el mouse en el navegador real (o un test de
  Playwright que sí dispara el evento por coordenadas de pantalla), no sólo con `userEvent.click` sobre
  el nodo de React.
- **Costo**: cero funcionalidad perdida — el botón estaba bien cableado (acción, formulario, lógica de
  backend), el bug era puramente visual/de stacking. Mismo recorrido manual encontró, con la misma
  causa raíz ("se construyó la pantalla pero no se la miró clickeada en el navegador"), dos gaps más de
  cobertura visual que un test de React tampoco agarra: el estado activo/desactivado de un grupo sin
  ningún indicador en la fila, y la ayuda del identificador de unidad sin ejemplos (G-1 de la tarea 5.4,
  quedó a mitad).
- **Aplica a**: cualquier pantalla que combine una lista "tocable" con acciones propias por fila;
  frontend y QA al revisar una pantalla nueva — un recorrido manual real en el navegador sigue siendo
  necesario incluso con la suite de tests en verde.

## L-054 · Verificar un chequeo "por el efecto" sólo en la función de trigger, sin su cierre de dependencias, deja una puerta trasera

- **Origen**: 3c `pulido-de-la-configuracion`, integración `integrar/3c-sobre-4b`, rompedor de PR #2
  (RE11-02, `.git/informes-pr2/05-rompedor-e11.md`), corregido por la Enmienda E11 (D-129).
- **Qué pasó**: `roles.py` verifica que una tabla de sólo agregar está protegida **por el efecto**
  (`UPDATE`/`DELETE`/`TRUNCATE` rechazados), no leyendo el código de la función de su trigger — una
  buena práctica, ya documentada (D-115). El error de la primera versión de E11 fue transferirle al
  migrador, durante la ventana de una migración, **todas** las funciones de `public` salvo la del
  trigger en sí: dejó afuera del chequeo cualquier función **auxiliar** que esa función de trigger
  llamara. El migrador reemplazó la auxiliar (no la protegida) por una que cambiaba de `true` a
  `false` después de que `roles despues` ya había verificado todo en verde, y esa sola auxiliar
  bastó para desactivar el bloqueo de una tabla "protegida" sin que ningún chequeo lo notara.
- **Regla**: cuando se protege una función por transferencia de propiedad, el conjunto protegido no es
  "la función", es **el cierre de todo lo que esa función llama, transitivamente**. Calcular ese cierre
  una sola vez (`_cierre_de_dependencias`) y aplicar la misma transferencia (dueño + `search_path`
  vacío) a cada elemento, no sólo al nombre de primer nivel.
- **Costo**: una ronda de rompedor dedicada (PR #2) encontró el hueco antes de llegar a producción;
  cero incidentes reales. El costo real fue escribir la Enmienda E11 y su test después de haber dado
  por cerrada la primera versión de E11 ese mismo día.
- **Aplica a**: cualquier mecanismo de "transferir propiedad temporalmente, verificar, devolver" sobre
  funciones o procedimientos con dependencias internas — no sólo a este migrador. Quien diseñe un
  chequeo de seguridad "por el efecto" tiene que preguntarse qué otro código corre adentro del camino
  que mide, no sólo el nombre que aparece en el catálogo.

## L-055 · `mypy` por archivo tocado no detecta un choque de nombre entre módulos hermanos; sólo `mypy` sobre todo `src/` lo ve

- **Origen**: 6 `gastos-y-cargos`, cierre (tarea 9.2, 29/10/2026).
- **Qué pasó**: cada bloque del apply corrió `mypy` sólo sobre los archivos que tocaba
  (`src/proptech_core/gastos ...`), y pasó limpio bloque por bloque. Al cerrar, `mypy src/` sobre el
  árbol completo encontró un error real en `proptech_api/app.py`: dos bucles `for tipo in (...)`
  seguidos, uno para los errores de `cuenta_corriente` y otro para los de `gastos`, reusaban el mismo
  nombre de variable (`tipo`). `mypy` infiere el tipo de `tipo` del primer bucle y lo reporta como
  incompatible en el segundo — un error que nunca aparece si se tipa sólo el módulo nuevo, porque la
  variable conflictiva vive en un archivo que ningún bloque de este change "tocó" en el sentido de
  escribir lógica nueva (sólo agregó tres líneas de wiring).
- **Regla**: el `mypy` de cierre (L-005 lo pide "igual que el CI") tiene que correr sobre **todo
  `src/`**, no sólo sobre los archivos que el change editó — el mismo motivo que L-041 ya daba para
  la suite de tests ("un chequeo de arranque cierra con la suite completa"). Un choque de nombres
  entre dos bloques de código que nunca se tocaron entre sí sólo aparece cuando se tipa el programa
  completo.
- **Costo**: cero en producción — lo encontró el propio cierre del change, antes de cualquier commit.
- **Aplica a**: cualquier change que agregue wiring a un archivo compartido (`app.py`, un router
  central, un registro de handlers) reusando un patrón de bucle/variable que ya existía para otro
  módulo. Renombrar la variable de cada bucle es más barato que depender de que nadie la reuse mal.

## L-056 · La suite completa de cierre encuentra lo que la suite por bloque no puede: tests estructurales que hardcodean "todo lo que existe hoy"

- **Origen**: 6 `gastos-y-cargos`, cierre (tarea 9.1, 29/10/2026).
- **Qué pasó**: cada bloque del apply corrió su propio grupo de tests y los dos preexistentes
  conocidos de Windows, nunca la suite entera. Al correr `tests/ -q` de punta a punta para el cierre,
  aparecieron 4 fallas reales (más las ya conocidas de Windows/worker) que ningún bloque podía haber
  visto porque viven en archivos que ningún bloque de este change tocó a propósito:
  - `test_rutas_protegidas.py`: una lista `_RUTAS_CUBIERTAS` que tiene que ser EXACTAMENTE el conjunto
    de rutas bajo `/api` — las 19 rutas nuevas de `gastos.py` nunca se agregaron ahí. Corregido: las 19
    rutas, más sus cuerpos de prueba en `_pedido`, más los ids de `mundo`.
  - `test_libro_rollback.py` y `test_vocabulario_configuracion.py`: hardcodeaban `alembic_version ==
    "0027"` y el conjunto de nombres de `accion_de_auditoria` sin el vocabulario de `EventoDelGasto`
    (10 eventos nuevos). Corregidos a `"0032"` y a incluir `EventoDelGasto` en la unión esperada.
  - `test_migracion_normaliza_textos.py`: no era un hardcodeo, era una fuga real de datos — la
    fixture compartida `api_edificio` (módulo-scoped en este archivo) sumó una persona `"contador"`
    con una fila de `asignacion_rol` real, commiteada, nunca limpiada; un guardia de downgrade de la
    migración `0018` hace un `count(*)` SIN FILTRAR por administración sobre `rol='contador'` en toda
    la tabla, y lo encontraba aunque el test que lo disparó no tuviera nada que ver con proveedores.
    Corregido con un `finally` en la fixture que borra esa fila puntual al terminar (no las otras
    cinco personas, que no disparan ningún guardia existente).
- **Regla**: agregar rutas, vocabulario de auditoría o una migración nueva **no termina en el código
  que las agrega** — hay tests estructurales en otros archivos que afirman "esto es TODO lo que existe
  hoy" y se desactualizan en silencio si nadie corre la suite completa antes de cerrar. L-041 ya decía
  esto para un chequeo de arranque; acá se confirma que el radio es más amplio: cualquier test con un
  conjunto hardcodeado (rutas, vocabulario, versión de migración) es candidato.
- **Regla (fixture compartida)**: una fixture module/session-scoped que **commitea** filas reales
  (no las envuelve en una transacción que haga rollback) tiene que limpiar lo que agrega si ese dato
  puede activar un guardia o un `count(*)` sin alcance en otro archivo — "nadie más lo necesitaba
  limpio hasta ahora" no es garantía de que seguirá siendo así.
- **Costo**: cero en producción — los cuatro hallazgos los encontró este mismo cierre, antes de
  cualquier commit. El costo real fue el tiempo de la corrida completa (~40 minutos en este entorno).
- **Aplica a**: cualquier change que agregue rutas, vocabulario de auditoría, una migración, o una
  persona/rol nuevo a una fixture compartida — correr la suite completa antes de declarar el cierre
  (L-041 generalizada), y revisar si la fixture que se extiende limpia lo que inserta.
