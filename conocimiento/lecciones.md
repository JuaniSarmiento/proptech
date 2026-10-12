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
