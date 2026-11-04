# Constructor · apply · intento 2 · ejemplo-robusto (C-27)

- **Rol**: constructor, subagente nativo `role-constructor`, agente nuevo: el del intento 1 no se pudo retomar. Sin sustitución.
- **Executor declarado**: Claude Opus 5.5. Familia: Claude.
- **Fecha**: 31/10/2026, de 16:59 a 18:02 (-03:00).
- **Revisión**: base `9649471` más el árbol sin commit descrito en "Revisión entregada". No hice commits ni push.
- **Resultado**: H-1 y H-2 corregidas con TDD. Marqué 1.2, 1.4, 5.3 y 8.2: 20 de 21 tareas. 8.1 sigue sin marcar.
- **Lo que falta: la suite completa no tiene resultado sobre esta revisión.** El sistema la cortó por falta de memoria y el aviso pide no relanzarla sin que lo pidan. No la relancé, ni en Linux ni en Windows. **Decide el orquestador** (ver A2-1 y "Decisión pendiente").

## Fuentes leídas

- **Lecciones**: `knowledge-base/15_lecciones.md`, completo (L-001 a L-067).
- `openspec/changes/ejemplo-robusto/`: `informes/propose-2-plan-reviewer.md`, `informes/apply-1-constructor.md`, `design.md`, `specs/datos-semilla/spec.md` y `tasks.md`.
- **Código**: `complejos/aplicacion/ejemplo.py`; `compartido/base_de_datos.py:285-318` y el diff contra la base de ese archivo y de `configuracion.py`; `migraciones/versions/0005_edificio_y_unidad.py:36-57`, para ver qué columnas de `unidad` admiten nulos.
- **Tests**: `tests/integracion/test_arranque_tablas_protegidas.py` entero y `tests/integracion/test_ejemplo_casos_de_uso.py:1-644`, `:1019-1108`, `:1225-1254` y `:1525-1574`.
- **Infra**: `infra/compose.yaml`, `backend/Dockerfile`, `infra/ci/test-backend.sh`, los pasos de `.github/workflows/ci.yml` y `README.md:100-140`.
- **Sin leer**: `infra/.env` y `infra/.env.example`, como manda el brief; no imprimí `docker compose config`, sólo `config --quiet` con mi archivo de contraseñas inventadas. Tampoco los informes de `.git/informes-*`. Las copias de mutantes del intento 1 no están a mi alcance.

## Contaminación por otros informes

Leí `apply-1-constructor.md` y `propose-2-plan-reviewer.md` porque el brief lo manda: sus hallazgos, sus decisiones y su lista de mutantes condicionaron lo que miré. El diseño de las correcciones viene del brief y del plan corregido, no de una mirada independiente. No hay todavía informes de rompedor ni de auditor.

## EVIDENCIA

Los logs completos están en mi directorio temporal, que no viaja con el repo: `C:\Users\espej\AppData\Local\Temp\claude\C--Programacion-proptech\19e1c5b0-3037-4aa8-9599-2cf049059770\scratchpad\c27-apply2\`. La evidencia por tarea, con comando, hora y salida, está debajo de 1.2, 1.4, 5.3, 8.1 y 8.2 en `tasks.md`.

### Antes de cambiar nada

El árbol estaba como dice el brief: `git diff | sha256sum` en `1946d4ce...` y los seis `sha256sum` iguales a los del intento 1.

**Línea de base** (17:01:01 a 17:16:09): `uv run pytest tests/integracion/test_ejemplo_casos_de_uso.py tests/integracion/test_arranque_tablas_protegidas.py tests/unitarios/test_fronteras_de_modulos.py -q -p no:cacheprovider --tb=line --no-header`: `5 failed, 279 passed, 1 warning in 896.92s`. Las 5 son las conocidas: `test_cada_proceso_frena[configuracion_versionada-ejemplo]` e `[imputacion-ejemplo]` (H-1), más `test_regla_sql_vigila_composicion[proptech_api]`, `[proptech_worker]` y `test_vinculacion_de_desarrollo_solo_desde_ejemplo` (separador de ruta de Windows).

### RED y GREEN de H-1 y H-2

- **Comando de los dos**: `uv run pytest tests/integracion/test_ejemplo_casos_de_uso.py tests/integracion/test_arranque_tablas_protegidas.py -q -p no:cacheprovider --tb=short --no-header -k "cada_dato_comparado or cada_campo_de_la_unidad or semilla_sin_alterar or ciclo_completo or desprotegidas_terminan_con_4 or cada_proceso_frena"`.
- **RED** (17:17:33 a 17:20:31, `ejemplo.py` sin cambios, `3ec660d3...`): `10 failed, 16 passed, 194 deselected in 170.32s`. Leí cada traceback: las 10 caen en su aserción propia (L-034, L-049).

| Test | Falla |
|---|---|
| `[tipo_de_unidad]`, `[piso_de_unidad]`, `[superficie_de_unidad]` | `Regex pattern did not match. Expected regex: '\\Aunidades\\[1A\\]\\.tipo: difiere de la semilla\\Z'. Actual message: 'unidades[1A]: difiere de la semilla'`, cada uno con su campo |
| `test_ciclo_completo_de_carga_del_ejemplo` | Lo mismo con `.coeficiente` |
| `test_cada_campo_de_la_unidad_que_difiere_suma_su_mensaje` | `At index 0 diff: 'unidades[1A]: difiere de la semilla' != 'unidades[1A].coeficiente: difiere de la semilla'` |
| `test_tablas_de_solo_agregar_desprotegidas_terminan_con_4`, 3 casos | `assert 'imputacion: dueño no superusuario' in 'la base no es segura para este comando: hay tablas de sólo agregar sin proteger o sin crear; no se escribió nada\n'`, cada uno con su tabla y motivo |
| `test_cada_proceso_frena[...-ejemplo]`, 2 casos | `assert 'imputacion' in 'la base no es segura...'`, después de pasar el `== 4` |

- **GREEN** (17:21:00 a 17:22:42): `26 passed, 194 deselected, 1 warning in 98.59s`. Los casos `api`, `worker` y `alta_inicial` no cambiaron y pasan.

**Producción**, sólo dos lugares de `ejemplo.py`:

- `:265-272` (D9): una tupla `(campo, distinto)` por cada uno de los cuatro campos y un `diferencias.append(f"unidades[{identificador}].{campo}: difiere de la semilla")` por cada uno que difiere. Comprobé en las migraciones `0005` y `0026` que `coeficiente` y `superficie_m2` son `NOT NULL`, así que evaluar los `Decimal` sin cortocircuito no agrega un `TypeError`; `piso` admite nulos y se compara con `!=`.
- `:595-601` (D4): `f"la base no es segura para este comando: {error}; no se escribió nada"`. La excepción sólo se lanza en `base_de_datos.py:315`, con cada tabla y uno de dos motivos fijos.

### Mutantes

Cada uno se aplicó sobre una copia previa propia (no hay commit, L-013), se corrió, se restauró y se comparó byte a byte: **11 de 11 `revertido contra copia: identico`, 0 `DISTINTO`**. Una trampa restauraba ante cualquier corte.

| Mutante | Qué | Resultado |
|---|---|---|
| MA2.1 | Tipo apagado | `DID NOT RAISE` sólo en `[tipo_de_unidad]`, más `test_cada_campo_...` |
| MA2.2 | Piso apagado | `DID NOT RAISE` sólo en `[piso_de_unidad]`, más `test_cada_campo_...` |
| MA2.3 | Coeficiente apagado | `DID NOT RAISE` sólo en `test_ciclo_completo_...`, más `test_cada_campo_...` |
| MA2.4 | Superficie apagada | `DID NOT RAISE` sólo en `[superficie_de_unidad]`, más `test_cada_campo_...` |
| MA2.5 | Confunde los nombres de tipo y piso | `Actual message: 'unidades[1A].piso: ...'` en `[tipo_de_unidad]` y al revés en `[piso_de_unidad]` |
| MA2.6 | Confunde los nombres de coeficiente y superficie | Lo mismo en `[superficie_de_unidad]` y en `test_ciclo_completo_...` |
| MA2.7 | Corta en el primer campo | Sólo `test_cada_campo_...` |
| MA2.8 | Muestra el valor | `Actual message: '...difiere de la semilla departamento'`, en los 5 tests |
| MA1.1 | Vuelve al texto fijo | Rojo en **los dos tests** del brief, sus 5 casos |
| MA1.2 | Sin "no se escribió nada" | `assert False` del `endswith`, sólo en `test_tablas_...` |
| MA1.3 | Sin la rama | `assert 9 == 4` en los dos tests, con `error inesperado: TablasDeSoloAgregarDesprotegidas` |

### Orden de cierre

**1. Focalizados** (17:32:18 a 17:43:53), los tres archivos: `3 failed, 283 passed, 1 warning in 691.64s`. Las 3 son las de `test_fronteras_de_modulos.py` por el separador de ruta, igual que en la línea de base.

**2. Lint, formato y tipos** sobre el árbol entero, desde `backend/`:

| Hora | Comando | Salida |
|---|---|---|
| 17:44:30 | `uv run ruff check .` | `All checks passed!` |
| 17:44:31 | `uv run ruff format --check .` | `405 files already formatted` |
| 17:44:37 | `uv run mypy --platform linux` | `Success: no issues found in 368 source files` |
| 17:45:33 | `uv run mypy` | `tests\infra\test_respaldos.py:554`, `"killpg"` y `"SIGKILL"`, `Found 2 errors in 1 file (checked 368 source files)`: los 2 previos |

**3. Tarea 8.2, comando real con `-p proptech-c27`** (17:52:08 a 17:54:28). La salida completa está en `tasks.md`. Dio lo pedido:

- Carga, segunda carga y sin variables de Redis: 0.
- Los mismos errores de antes: 1, 1, 2, 3, 3, 4 (rol), 6 (semilla alterada) y 5 (`stop db`).
- **Un mensaje por campo editando la base de verdad**: cada `UPDATE` da su `unidades[1A].<campo>: difiere de la semilla`, y el de los cuatro campos da las cuatro líneas. Con 1A devuelta a la semilla, 0.
- **Código 4 por tablas desprotegidas**: `imputacion: dueño no superusuario` e `imputacion: no existe en public`. Con la tabla devuelta, 0.
- **Código 7**, que el brief no pedía: con ids y emisor inventados, porque `vincular` no habla con Clerk.
- **Limpieza**: 0 contenedores, volúmenes, redes e imágenes con `c27`. La foto de `proptech` (ocho contenedores con id y estado, cuatro volúmenes, cuatro redes, dos imágenes) es igual byte a byte antes y después, también los contenedores a las 18:00:46.

**4. Suite completa: sin resultado** (ver A2-1).

- Lanzada a las 17:54:55 en `python:3.14.8-slim-trixie`, `uv` 0.12.24, Python 3.14.8, con el repo montado de sólo lectura y el socket de Docker. `uv sync --locked` sobre la copia, sin cambios en `uv.lock`.
- **La colecta sí llegó**: `4901 tests collected in 13.14s`.
- La suite arrancó a las 17:56:58 y el log termina en `[ 25%]`, sin resumen.
- `tests/infra/test_respaldos.py`, que iba después sin root, **no llegó a correr**.

**5. Revisión contra la lista de mutantes del intento 1** (18:00:46): **no quedó ninguno en `ejemplo.py`, `configuracion.py` ni `base_de_datos.py`.**

- Leí `ejemplo.py` entero y el diff de los otros dos. Comprobé una por una las ramas de M1.x, M2.2, M3.x, M5.1, M5.2, M5.3c a e y M5.4, y que M4.2 y M4.3 no están.
- `rg` de `if False|and False|or False|= False or|range\(1\)|edificios\[0\]|len\(coinciden\) == 0|\["vinculado"\]|coeficiente_base is not None and` sobre los tres: sin coincidencias, código 1.
- **Controles**, para que ese vacío signifique algo (L-016): los 21 textos correctos aparecen, por ejemplo `if set(grupos_base) != set(grupos_semilla)`, `for _ in range(intentos)`, `.replace(ruta_semilla` y `le=50`. `redis_host: str` y `redis_password` siguen sin valor por defecto, y el diff no toca ninguna línea de Redis. M5.3a y M5.3b: `base_de_datos.py:65` sigue con `"connect_timeout": configuracion.db_connect_timeout_s`, y el único `connect_timeout` del diff es el campo del `Protocol`.
- **Es una revisión por lectura y por texto**, no el `sha256sum -c` contra las copias del intento 1, que no tengo. El rompedor mira el diff entero.
- `ejemplo.py` es idéntico (`cmp`) a mi copia previa a los mutantes MA.

### Conteos, contados por mí

| Medición | Intento 1 | Ahora | Por qué |
|---|---|---|---|
| `test_ejemplo_casos_de_uso.py` | 206 | 208 | `test_cada_campo_...` y `[imputacion_que_no_existe]` |
| `test_arranque_tablas_protegidas.py` | 12 | 12 | |
| `test_fronteras_de_modulos.py` | 66 | 66 | |
| `test_puntos_de_entrada_prohibidos.py` | 3 | 3 | |
| Repo entero, `pytest --collect-only -q`, en el clon Linux | 4899 | 4901 | Los mismos 2. No se borró ningún test |

### Revisión entregada

Base `9649471`, sin commits. Hashes del 31/10/2026 a las 18:01:44, los mismos que a las 17:54:50 al lanzar la suite para el código.

```
$ git diff | sha256sum
22bb0402eb35deb1fd38d49c209ddfe77d1a8d5b1522fce7ef9af0e199373d41 *-

$ sha256sum <archivos del change>
c85946595037b618740ba5309cc3e050e62e0b9121b23daadfe4b0bcac7dd536 *README.md
1ff9517dc5bae1e130c240a4b5d152132a01aa03330d84d8e7ca6fbdbbab8756 *backend/src/proptech_core/compartido/base_de_datos.py
46a3a499ba0472f5efba33820e9bb15513e8588931b86bf9f88ed8401958e69e *backend/src/proptech_core/compartido/configuracion.py
4de87667144c05ca60a388c3913ecd1c5dc8c6bc964fa26ff14a71b1781a2267 *backend/src/proptech_core/complejos/aplicacion/ejemplo.py
f9521fd9a487701fa092d3f71d4acd028a234ee0c4ffb9d15794953e8bcfa602 *backend/tests/integracion/test_arranque_tablas_protegidas.py
5b18ea14ed384df165d99b18bd96248c58079533bf888a8c28f08a3116495ae8 *backend/tests/integracion/test_ejemplo_casos_de_uso.py
af17cd1fdd72c17d4e6a253ad3cf8087661102374316bd014396042ecb0871a2 *backend/tests/unitarios/test_puntos_de_entrada_prohibidos.py

$ sha256sum <los que no toqué, marcados por el fin de línea>
62a32f7f701c48a424a3673527c90ec45302d7f2dcb975c6776be4415dfe7c46 *infra/respaldos/respaldar.sh
6266eec41ccddfe9e7cc6454ee8be3a22766614d5cdfae0b20cc2d2e555ed262 *infra/respaldos/restaurar.sh

$ git status --short
 M README.md
 M backend/src/proptech_core/compartido/base_de_datos.py
 M backend/src/proptech_core/compartido/configuracion.py
 M backend/src/proptech_core/complejos/aplicacion/ejemplo.py
 M backend/tests/integracion/test_arranque_tablas_protegidas.py
 M backend/tests/integracion/test_ejemplo_casos_de_uso.py
 M infra/respaldos/respaldar.sh
 M infra/respaldos/restaurar.sh
?? backend/tests/unitarios/test_puntos_de_entrada_prohibidos.py
?? openspec/changes/ejemplo-robusto/
```

- **Tocados en este intento**: `ejemplo.py`, `test_ejemplo_casos_de_uso.py`, `test_arranque_tablas_protegidas.py` (sólo el caso `ejemplo`), `openspec/changes/ejemplo-robusto/tasks.md` y este informe. `README.md` no cambió (`cmp`): lo leí y nada dejó de ser cierto.
- `git diff` no cubre lo que no está trackeado: el test de guarda va con su `sha256sum`. `backend/uv.lock` no aparece modificado.
- `tasks.md` cambió después de esos hashes de código, pero no entra en ninguna corrida.

## Hallazgos

### A2-1. La suite completa no tiene resultado, y hoy no se puede afirmar nada de las regresiones. **Decide el orquestador**

- **Qué pasó**: el sistema mató el `docker run` local antes de las 17:58:13: `stopped because the system is running low on memory`. Medí `RAM libre MB: 202 de 7915`, y la VM de Docker tiene 3.69 GiB. El aviso dice: no es una falla del comando, y no relanzarla por mi cuenta, porque la memoria puede seguir corta. A las 18:01:44 había 901 MB libres.
- **Lo que hice**: el corte sólo mató al cliente, y el contenedor `proptech-c27-suite` siguió corriendo, así que lo frené yo: es mío y era la carga que el sistema quiso cortar. A las 17:59:59 estaba detenido y sólo quedaba su ryuk, que se fue solo; a las 18:00:46 había 0 contenedores de testcontainers y 0 con `proptech-c27`.
- **Lo que no hice**: no la relancé en Linux, y **no usé la corrida de Windows que el brief da como salida, porque es la misma carga bajo el mismo aviso.**
- **Por lo tanto**: 8.1 no tiene resultado local de suite. La última corrida completa sigue siendo la del intento 1, vencida.

### A2-2. El contenedor Linux daba `E` en masa antes del corte, y no sé por qué

- **Lo observado**: `..FFF................F....` al principio, y desde el 4 % casi todo `E`, con tramos de `.` en el medio y algunas `F`. Es lo que queda en `suite.log`; no vale como resultado de nada.
- **Lo que falta**: le mandé `SIGINT` a `pytest` (PID 1870) para que volcara las causas, pero no imprimió resumen antes de detener el contenedor. **No sé qué tests son ni por qué fallan.**
- **Consecuencia práctica**: relanzar la suite entera ahí sin mirar antes un solo test puede gastar la corrida. El intento 1 corrió sólo 59 ids en un contenedor parecido, con 32 en verde y fallas ya explicadas. Ver SUPOSICIÓN.

### A2-3. La copia del contenedor no es un `cp` crudo: es un clon más lo entregado, y eso se aparta de la letra del brief

La copia de Windows tiene CRLF en `infra/ci/*.sh` (`git ls-files --eol`: `i/lf w/crlf`), y `bash infra/ci/test-backend.sh` no corre así en Linux. El guion hace `git clone` de `9649471`, copia encima los 7 archivos entregados con LF y hace `git add -A` en el clon descartable, sin commit, para que `git ls-files` vea el test nuevo como en el CI (`test_vocabulario_vigente.py` lo usa). `infra/.env` no está en el clon. Los blobs del clon son iguales a los de Windows (`git hash-object`, `diff` vacío a las 17:56).

### A2-4. Lo que sumé sin que el brief lo nombrara, dentro de los archivos autorizados

- **`test_cada_campo_de_la_unidad_que_difiere_suma_su_mensaje`**: sin él, MA2.7 sobrevive, porque un caso de un solo campo no distingue "un mensaje por cada campo" de uno que corta en el primero. **Costo**: el brief pide que cada mutante de condición mate sólo a su caso, y éstos matan a su caso **y a este test**, a propósito. Entre los casos de un solo campo, cada uno mata sólo al suyo.
- **`[imputacion_que_no_existe]`**: el escenario del spec dice "no existe en `public` o su dueño no es superusuario", y el test sólo cubría la segunda.
- **`f"{tabla}: {motivo}"` y el `endswith`** en `test_tablas_...`: el brief pedía la tabla; esto también ata el motivo y el final del mensaje.
- **`contextlib.redirect_stderr` en lugar de `capsys`** (el brief admite un equivalente): `capsys` en la firma también entra en los casos `api` y `worker`, y un handler de logs creado en `crear_app` podría quedarse con un stream que `capsys` cierra al terminar. **Eso no lo probé**: lo evité para que esos consumidores no cambien en nada.

### A2-5. Dos corridas de 8.2 que no cuentan

Las de las 17:46 y 17:49 dieron los mismos códigos, pero mi guion filtraba la salida con `rg`, que no existe en un `bash` hijo, y los mensajes se perdieron. Sin mensajes no hay evidencia del mensaje por campo, así que la repetí con `grep`. Bajaron su `proptech-c27` con `down -v` igual que la buena.

## JUICIO

- **Autor**: constructor. **Comparación**: lo construido contra el brief, D4, D9 y los dos escenarios nuevos del spec.
- **Confianza alta**: que H-1 y H-2 están corregidas como pide el plan. RED por aserción propia, GREEN, 11 mutantes y el comando real editando la base lo muestran por caminos distintos.
- **Confianza alta**: que `api`, `worker` y `alta_inicial` no cambiaron. El diff de `test_arranque_tablas_protegidas.py` sólo mueve el caso `ejemplo`, y los 12 pasan en los focalizados.
- **Confianza media**: que no rompí nada fuera de los tres archivos focalizados. Toqué poco y `mypy` y `ruff` dan limpio, pero la suite entera es justamente lo que falta (L-041, L-055, L-064). El intento 1 encontró H-6 sólo con ella.
- **Confianza alta**: que reenviar el texto de la excepción no expone datos: se arma con constantes de tabla y dos motivos fijos, y `_afirmar_salida_limpia` sigue en el test.
- **Autoría**: escribí el test, el código y el mutante. No es una revisión independiente (L-025): el rompedor y el auditor son los primeros ojos de afuera.
- **Marqué 5.3** con RED, GREEN y mutantes de lo que pedía. La regresión global no está cubierta por esa marca: queda en 8.1.

## SUPOSICIÓN

- **Por qué las `E`**: no lo verifiqué, porque no hay traceback y correr algo más en Docker iba contra el aviso de memoria. Puede ser la misma falta de memoria (la VM sin lugar para Postgres), o algo de mi contenedor distinto del que usó el intento 1, cuya receta exacta no está en su informe. Ninguna de las dos está comprobada, y no la presento como defecto del código.
- **Que las 3 fallas de `test_fronteras_de_modulos.py` sean sólo el separador de ruta en esta revisión**: lo tomo de sus mensajes, iguales a los de 0.1. No las corrí en Linux en este intento.
- **La hora exacta del corte**: entre las 17:56:58 y las 17:58:13. No tengo un dato más fino.

## Chequeos no ejecutados y límites

- **Suite completa sin filtros**: sin resultado (A2-1). Es el paso 4 del brief.
- **`tests/infra/test_respaldos.py` sin root**: no corrió, porque iba después de la suite.
- **CI del PR**: no existe, porque no hay push ni PR. 8.1 sigue sin marcar.
- **`sha256sum -c` contra las copias del intento 1**: no se puede, ya lo sabía el plan (PR2-4).
- **Códigos 8 y 9 en el stack real**: probados por tests, no en 8.2.
- **`infra/ci/humo.sh`**: no lo corrí ni lo toqué.
- **Sin tocar**: `infra/respaldos/*.sh` (mismos `sha256sum`), `acceso`, la matriz de permisos y `cuenta_corriente`.

## Decisión pendiente

La suite es lo único que falta para el cierre del constructor. No cambié código después de la revisión `22bb0402...`, así que una corrida futura sobre este árbol vale, si esos hashes siguen iguales.

Alguien tiene que pedirla, con memoria disponible. Opciones:

1. **Liberar memoria y correr primero un solo test de integración** en el contenedor, para ver la causa de las `E`, y recién después la suite. Es la que recomiendo: una corrida entera tarda cerca de una hora, y A2-2 dice que puede perderse.
2. **Ir directo a la corrida de Windows**, la salida que da el brief: `bash infra/ci/test-backend.sh -q -p no:cacheprovider --tb=line`, separando las fallas contra la tabla del intento 1. Tardó 4105 s en la primera corrida y deja sin mirar lo que Windows enmascara.
3. **Mandar al rompedor sin suite**, declarándolo. El brief la pide antes, así que esto ya es una decisión que no me corresponde.

El aviso del sistema dice que Giuliano puede desactivar ese corte arrancando Claude Code con `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` en su entorno, y que ponerla desde un comando no tiene efecto. No lo hice ni lo recomiendo por encima de liberar memoria: es su decisión.

El guion de la corrida (`suite-linux\correr.sh`) y el del stack (`c27-stack\recorrido.sh`) quedan en mi directorio temporal. Si esa carpeta no sobrevive, la receta está en A2-3 y en "Orden de cierre".
