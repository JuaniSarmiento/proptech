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
