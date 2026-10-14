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
- **Regla**: antes de poner un dueño a un ítem de deuda, revisar `roadmap.md` y preguntar qué cambio
  es el primero que de verdad necesita que esa pieza esté resuelta. Asignarlo a cualquier otro deja la
  deuda sin dueño real: nadie la mira hasta que ya rompió algo.
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
