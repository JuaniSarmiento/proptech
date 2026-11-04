# Rompedor · verify · intento 2 · ejemplo-robusto (C-27)

- **Rol**: rompedor, subagente nativo (`role-breaker`), vuelta acotada al grupo 9 por decisión de Giuliano (brief del orquestador, para levantar B1 de `verify-1-auditor.md`).
- **Executor declarado**: Claude Opus 5.5, por la declaración del entorno. **Familia**: Claude, la misma del constructor del intento 3, del rompedor de verify 1 y del orquestador. El proyecto no declara `## Role executors`; la independencia es limitada (L-025).
- **Fecha**: 03/11/2026, de 23:30 a 23:45 aproximadamente (-03:00), en Windows.
- **Revisión atacada**: rama `change/ejemplo-robusto`, `HEAD` `7110aacb69a8a4db2183945c6376198743085812` (base `9649471`). `ejemplo.py` `32648461...`, `test_ejemplo_casos_de_uso.py` `04201ab2...` y `cargador_yaml.py` `0cf45d0c...`; los dos primeros son los que el auditor da como entregados (`6dd4630f`). El árbol de trabajo ya tenía `infra/respaldos/*.sh` (sólo fin de línea) e `informes/LEEME.md` modificados; `git diff | sha256sum` `e5edff7a...` al empezar y al terminar.
- **Resultado**: **ninguna falla de producción reproducida.** Las cinco correcciones del grupo 9 hacen lo que dicen, por el comando real y por `_main`. Hay **2 mutantes sobrevivientes nuevos** (F10 y F11, severidad baja, sólo tests), 2 observaciones y 1 sospecha. Por la regla del flujo, F10 y F11 vuelven al constructor por TDD vía orquestador, salvo que el orquestador o Giuliano decidan otra cosa. Este informe no aprueba nada: decide el auditor.

## Fuentes leídas, en orden

1. `knowledge-base/15_lecciones.md`: lista de títulos (67 lecciones) y texto completo de L-007, L-008, L-009, L-013, L-019, L-034 y L-035.
2. `informes/verify-1-breaker.md` completo (mi ronda anterior).
3. `backend/src/proptech_core/complejos/aplicacion/ejemplo.py` entero.
4. `compartido/cargador_yaml.py` entero; `compartido/semilla.py:36-135` y `:150-300`; `compartido/parametros.py:285-302`; `complejos/aplicacion/errores.py` entero; `rg` de `EntradaInvalida(`, `error_de_validacion` y `Conflicto(` en `escritura.py`, `unidades.py`, `grupos.py`, `alta_inicial.py` y `vinculacion_de_desarrollo.py`; `unidades.py:25-130`; `grupos.py:120-165`; `compartido/texto.py:63-67`; `rg` de la unicidad de `unidad` en `migraciones/versions`.
5. `design.md` D4 y D10 (`:49-58`, `:88-102`); `tasks.md:255-295` (grupo 9); `specs/datos-semilla/spec.md:125-185`.
6. `informes/verify-1-auditor.md`: sólo las líneas del B1 (`:105`, `:147`, `:150`).
7. `informes/apply-3-constructor.md:1-60`, `:69`, `:97` y `:118`.
8. `tests/integracion/test_ejemplo_casos_de_uso.py:1130-1173`, `:1296-1331`, `:1500-1670`, `:1989-1995` y `:2296-2590`, más los nombres de los tests desde `:1540`.
9. `README.md:104-141`.

**Sin leer**: `informes/propose-3-plan-reviewer.md` (la disposición de mis hallazgos la tomé de D10 y de `tasks.md`), el resto de `verify-1-auditor.md`, `infra/.env`, `infra/.env.example` y `.git/informes-*`. No imprimí `docker compose config`.

## Contaminación por otros informes

- El blanco de la vuelta sale de mi informe anterior y de `tasks.md` y `apply-3-constructor.md`, que dicen qué cambió y qué mutantes ya corrió el constructor (R9.1, R9.2a/b, M9.2c, R9.3a/b, M9.3c/d, M9.4a a f). **Elegí a propósito mutantes distintos** para no repetir su evidencia.
- Del auditor leí sólo el B1. No usé ninguna de sus conclusiones.
- Sin Engram: la herramienta no está disponible en este subagente.

## EVIDENCIA

Todo desde `backend/`, con `uv run` y el `.venv` del repo. Los mutantes corrieron sobre copias de `backend/src` en `C:\Users\espej\AppData\Local\Temp\claude\56b680c42cc5a2e7\19e1c5b0-3037-4aa8-9599-2cf049059770\scratchpad\rompedor2\` (`src_limpia` y una `src_<mutante>` por mutante). Los apliqué con `mutar.py`, que exige una sola coincidencia y respeta el CRLF, y los comprobé con `diff -rq` contra `src_limpia`. Se importan por `PYTHONPATH`: verifiqué con `proptech_core.__file__` que se carga la copia (`...\rompedor2\src_B1\proptech_core\__init__.py`), y los tests de proceso real heredan `PYTHONPATH` porque `_entorno_limpio()` copia `os.environ`. **El repo no se mutó nunca.** La garantía de integridad es `git diff` y `sha256sum` contra `7110aac` más el árbol inicial (L-013). Mis tests propios están en `...\rompedor2\pruebas\test_rompedor2.py` y no viajan con el repo.

Comando base de los mutantes: `PYTHONPATH=<copia> uv run pytest tests/integracion/test_ejemplo_casos_de_uso.py -q -p no:cacheprovider --tb=line --no-header -k "<selección>"`.

| Hora | Qué | Resultado |
|---|---|---|
| 23:30:29 | `git rev-parse HEAD`, `git diff` con `sha256sum`, `sha256sum` de `ejemplo.py`, `cargador_yaml.py` y el test | `7110aac`, `e5edff7a...`, `32648461...`, `0cf45d0c...`, `04201ab2...` |
| 23:31:20 | B1 (F1): `if mensaje.startswith(_ARCHIVO_ILEGIBLE):` en la rama de la semilla | `1 failed, 9 passed, 231 deselected`. Lo mata `test_la_ruta_de_los_parametros_no_se_repite` |
| 23:31:51 | B2 (F1, gemelo): la rama de parámetros compara contra otra ruta | `1 failed, 9 passed`. Falla `:1560`, que espera `<parámetros>` y recibe la ruta de `parametros.yaml` |
| 23:32:09 | B3 (consumidor `cargador_yaml.py`): el mensaje pasa a `no se pudo leer el archivo: {ruta}` | `6 failed, 4 passed`: `:1541` y los cinco `[ruta]` de `:1574`, con la ruta entera e `user_Sembrado1` en la salida. **Sigue verde** `test_la_ruta_de_los_parametros_no_se_repite` (O6) |
| 23:32:47 | B4 (O4, orden): el chequeo de `--semilla` vacío pasa a después de `ConfiguracionDelEjemplo()` | **`10 passed, 231 deselected`: sobrevive** (F11) |
| 23:33:39 | B5 (F3): `except BaseException` en lugar de `except KeyboardInterrupt` en `_main` | `7 failed, 26 passed`. Lo matan `test_argumentos_no_reconocidos_no_repiten_el_id` (4) y `test_opcion_clerk_valida_antes_de_conectar...` (3), que reciben 130 |
| 23:34:01 | Comando real `cargar --semilla=` sin `POSTGRES_APP_PASSWORD`, en la copia limpia y en B4 | Limpia: `rc=2`, `--semilla no puede estar vacío...`. B4: `rc=3`, `falta configurar: POSTGRES_APP_PASSWORD` |
| 23:34:19 | B7 (F2): `except ValueError` con `getattr(error, 'campo', type(error).__name__)` en lugar de `except EntradaInvalida` | **`13 passed, 228 deselected`** con `cada_familia_de_error or la_semilla_que_el_caso_de_uso_rechaza or no_prevista`: **sobrevive** (F10) |
| 23:35:31 | Mis tests sobre la revisión limpia, primera corrida | `4 failed, 1 passed`. **No cuenta**: falla de mi arnés (faltaba `PROPTECH_PARAMETROS`, que pone un `conftest` que no cargué) |
| 23:36:13 | Mis tests sobre la revisión limpia, con el arnés corregido | `5 passed in 31.66s` |
| 23:36:58 | Mis tests bajo B7 (`-k "value_error or semilla_vacia"`) | `1 failed, 1 passed`. Sale `la semilla o los parámetros no se pueden cargar: ValueError; no se escribió nada` en lugar del 9 |
| 23:37:14 | Mis tests bajo B4 | `1 failed, 1 passed`: `test_rompedor2.py:70`, `assert 3 == 2` |
| 23:37:59 | Comando real con `PROPTECH_ENTORNO=produccion`: `cargar --help`, `cargar --foo` y `cargar` | `rc=0` sin salida de error; `rc=2` con `argumentos no reconocidos`; `rc=1` con la guarda |
| 23:38 | `import proptech_core.complejos.aplicacion.ejemplo`, dos veces | `1.29 s` y `1.28 s` (S5) |
| 23:38:26 | `test_arranque_tablas_protegidas.py -k ejemplo` sobre la revisión limpia | `2 passed, 10 deselected in 21.87s` |
| 23:39:11 | Integridad (ver al final) | Igual que al empezar |
| 23:39:37 | `PROPTECH_PARAMETROS` apuntando a un directorio, en la copia limpia y en B3 | Las dos `rc=3`, `valor inválido en: PROPTECH_PARAMETROS`: el lector de variables frena antes. El gemelo real sólo se alcanza con un archivo sin permiso de lectura (O6) |

Los tres casos de Ctrl-C a mitad de la carga real son `test_ctrl_c_a_mitad_de_la_carga_no_deja_nada_y_se_puede_repetir[crear_grupo|confirmar_sin_saldos_previos|vincular]`, de la corrida de 23:36:13. Con un doble que lanza `KeyboardInterrupt` en ese punto, sobre `base_fresca` y la conexión real como `proptech_app`, `_main` da 130 sin traceback y `_filas_escritas == _SIN_ESCRITURAS`. Al sacar el doble, la corrida siguiente da 0 con `ejemplo cargado`.

## Lente 1: correctitud

| Corrección | Ataque | Resultado |
|---|---|---|
| 9.1 / F1, la ruta sólo con el mensaje entero | B1 (prefijo en vez de igualdad), B2 (gemelo de parámetros mal cableado), B3 (el lector cambia su texto). Lectura de todos los mensajes de `cargador_yaml.py`, `semilla.py`, `parametros.py` y `georef.py`: el único que trae la ruta es `leer_archivo` (`cargador_yaml.py:115`); Georef nombra sólo el archivo (`georef.py:108`) | **Aguanta.** Los tres mutantes mueren. La igualdad depende del texto exacto de `leer_archivo`, y B3 muestra que si ese texto cambia, la ruta (que puede ser el id) sale entera. Para `--semilla` lo vigilan `:1541` y `:1574`; para parámetros no (O6) |
| 9.2 / F2, `EntradaInvalida` a 3 con `campo` | B7 (atrapar todo `ValueError`). Lectura de cada `EntradaInvalida(` en `complejos/aplicacion`: todos los `campo` son nombres fijos o salen de `error_de_validacion`, que une los `loc` de Pydantic (nombres e índices, no valores). `Conflicto` no se alcanza desde la semilla: el lector frena los repetidos de unidades y de miembros (`semilla.py:181-195` y `:213-218`), y la unicidad de `unidad` distingue mayúsculas sobre un texto que los dos lados recortan igual | **Aguanta**, pero **B7 sobrevive** a los 13 tests de la familia: F10 |
| 9.2, `_crear_desde_cero` lanza `EntradaInvalida` con `confirmada` | Lectura; el constructor ya corrió R9.2b | Aguanta. No lo repetí |
| 9.3 / F3, Ctrl-C a 130 | B5 (atrapar `BaseException`); Ctrl-C a mitad de la transacción en tres puntos, con la base real, y otra corrida después | **Aguanta.** B5 muere. "Una carga a medias no queda" es cierto en los tres puntos: cero filas, y la corrida siguiente carga (no queda una administración sin edificio que termine en 8). La ventana de los imports queda fuera de `_main` (S5) |
| 9.3 / O4, `--semilla=` a 2 | B4 (el chequeo después de la configuración); `--semilla` con espacios (lo cubre el `[   ]` de `:1564`, que espera 3 por archivo ilegible); `--help`, `--foo` y sin argumentos fuera de desarrollo | **Aguanta** el comportamiento. **B4 sobrevive** a los 10 tests de orden, guarda, id y emisor: F11 |

**Resultado de la lente**: sin fallas de producción. F10 y F11 son mutantes sobrevivientes.

## Lente 2: cableado

- **Cada rama se alcanza desde el comando real.** F1, por `python -m ... cargar --semilla <ruta>`: los tests de proceso de `:1564` a `:1615`, que corrí bajo B1 a B3; en cada corrida quedaron verdes los que el mutante no tocaba. O4, por el proceso real (23:34:01 y `:1648`). La guarda y `argparse`, por el proceso real (23:37:59). F2 llega por `_main` con la base real (mi test de `ValueError`: verde en limpio, rojo bajo B7) y, por el proceso real, por `test_la_semilla_que_el_caso_de_uso_rechaza_termina_con_3`, que corrí sólo bajo B7, en verde. F3, por `_main` con la base real (mis tres casos); el de `main()` en un proceso aparte (`:2482`) lo corrí sólo bajo B5.
- **`test_arranque_tablas_protegidas.py`, caso `ejemplo` (código 4)**: `2 passed` en limpio. El delta no toca la rama del 4.
- **`compartido/cargador_yaml.py`**: es el origen del texto que compara `_sin_la_ruta_del_archivo`. B3 prueba que el acople está vigilado para la semilla y no para parámetros (O6).
- **`compartido/semilla.py`**: sus mensajes no traen la ruta. Los tests de `s` y de `unidades` (`:1577` y `:1588`) ya prueban que no se deforman.
- **`complejos/aplicacion/errores.py`**: `EntradaInvalida.campo` se usa tal cual (ver la lente 1).
- **README, tabla de códigos**: los 11 renglones coinciden con el spec (`spec.md:125-135`) y con el código (`ejemplo.py:97-106`).

**Resultado de la lente**: limpia.

## Lente 3: veracidad

| Texto | Contra | Resultado |
|---|---|---|
| `ejemplo.py:92-95`: el 1 es sólo de la guarda, no escapa `Exception`, `KeyboardInterrupt` sale con 130, `argparse` sale por su `SystemExit` | Corridas de 23:37:59 y mis tests de Ctrl-C | Cierto |
| Docstring de `_ejecutar` y orden de D4: argumentos, guarda, `--semilla` vacío, id, emisor, configuración, archivos, base y carga | Código `:550-586`; B4 | Cierto en el código. **Ningún test vigila** que `--semilla` vacío vaya antes de la configuración: F11 |
| `_sin_la_ruta_del_archivo`: "se saca sólo si el mensaje entero es ése" y "Georef ya nombra sólo el archivo" | `cargador_yaml.py:115`, `georef.py:108`; B1 a B3 | Cierto |
| `ejemplo.py:633`: "sólo su `campo`, porque el `motivo` no llega nunca al cliente" | `errores.py:23-41` | Cierto |
| `ejemplo.py:652`: el 130 no dice "no se escribió nada" | El mensaje real | Cierto |
| D10: "El rechazo del caso de uso es un 3", y "`Conflicto` sigue en el 9 ... nadie lo reprodujo" | Lectura del lector y de los casos de uso | Cierto. Yo tampoco encontré un camino a `Conflicto` desde la semilla |
| D10: "Ctrl-C es un 130 ... la promesa es que no haya traceback" | S5 | Cierto desde que corre `_main`; durante los imports, no (sospecha) |
| Spec, "Se interrumpe con Ctrl-C": "una carga a medias no queda" | Mis tres casos con la base real | **Cierto**, con evidencia nueva: ningún test con base lo vigilaba |
| Spec, "El caso de uso rechaza la semilla" y "`--semilla` vacío" | Corridas y tests | Cierto |
| README `:130`, `:131` y `:138` | Spec y código | Cierto |
| D4, "Orden": "Las líneas `:460` y `:461` hoy están fuera de todo `try`, igual que `:471` y `:473-477` ... La ficha cita `:463-466`" | `ejemplo.py` en `7110aac` | **Desactualizado**: hoy `:460-461` es el `return ResultadoCarga` de `cargar`, `:471` es el texto de `EsperaAgotada` y `:473-477` el principio de `_emisor_de_desarrollo`. Describe el código de partida del plan con la palabra "hoy" (O7) |

**Resultado de la lente**: limpia salvo O7, de texto, y lo que F11 deja sin vigilar.

## Hallazgos reproducidos (mutantes sobrevivientes)

**En los dos casos la producción está bien**: lo comprobé por el comando real o por `_main` con la base real. Son garantías declaradas que nadie vigila (L-035). Cada uno trae el test que lo distingue, escrito y visto en rojo bajo el mutante y en verde en limpio. Ese test vive fuera del repo, así que se reescribe por TDD.

### F10. Atrapar todo `ValueError` en vez de `EntradaInvalida` no rompe ningún test. Severidad baja

- **Mutante B7**, en `_ejecutar`: `except ValueError as error:`, con `{getattr(error, 'campo', type(error).__name__)}` en el mensaje. `EntradaInvalida` hereda de `ValueError` (`errores.py:23`).
- **Sobrevive**: `-k "cada_familia_de_error or la_semilla_que_el_caso_de_uso_rechaza or no_prevista"`, 23:34:19, `13 passed, 228 deselected`.
- **Qué deja pasar**: un `ValueError` no previsto durante la carga (también un `ValidationError` de Pydantic sin envolver, que es un `ValueError`) saldría con 3 y "la semilla o los parámetros no se pueden cargar". D4 y el spec dicen que lo no previsto es un 9 que nombra sólo su tipo.
- **Test que lo distingue**: un doble de `ejemplo.crear_grupo` que lanza `ValueError("valor-sembrado")`, sobre `base_fresca`. Exige `_main(["cargar"]) == 9` y `stderr.strip() == "error inesperado: ValueError"`. Verde en limpio (23:36:13) y rojo bajo B7, en la aserción del código (23:36:58). Entra como un parámetro más de `test_cada_familia_de_error_de_la_carga_tiene_su_codigo`: `ValueError(_VALOR_SEMBRADO)`, 9, `"ValueError"`.

### F11. Nadie vigila que `--semilla` vacío vaya antes que la configuración. Severidad baja

- **Mutante B4**: el bloque `if args.semilla == "": return _fallar(CODIGO_USO, ...)` se mueve a después del `try: configuracion = ConfiguracionDelEjemplo()`.
- **Sobrevive**: `-k "la_semilla_vacia or fuera_de_desarrollo or el_id_con_formato or el_emisor_que_no"`, 23:32:47, `10 passed, 231 deselected`. `:1648` usa una configuración completa con la base cerrada, así que no distingue el orden; `:1658` sólo prueba que la guarda va antes.
- **Observación que lo distingue**: comando real sin `POSTGRES_APP_PASSWORD`, 23:34:01.

```
$ env -u POSTGRES_APP_PASSWORD PROPTECH_ENTORNO=desarrollo PROPTECH_PARAMETROS=<config/parametros.yaml> \
    POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=1 POSTGRES_DB=x POSTGRES_APP_USER=proptech_app \
    uv run python -m proptech_core.complejos.aplicacion.ejemplo cargar --semilla=
[limpia] --semilla no puede estar vacío; no se escribió nada                     rc=2
[B4]     Configuración inválida — falta configurar: POSTGRES_APP_PASSWORD         rc=3
```

- **Contra qué**: D4 ("Orden: argumentos (2), guarda (1), `--semilla` vacío y formato del id (2), emisor (3), configuración (3)...") y el docstring de `_ejecutar` ("El orden es parte del contrato").
- **Test que lo distingue**: `--semilla=` con `PROPTECH_ENTORNO=desarrollo` y sin variables de PostgreSQL, por `_main`. Exige el código 2 y `--semilla` en la salida. Verde en limpio (23:36:13) y rojo bajo B4, en `assert 3 == 2` (23:37:14).

## Observaciones

- **O6. El gemelo de parámetros de F1 se prueba con un doble que repite el formato del mensaje.** `test_la_ruta_de_los_parametros_no_se_repite` (`:1553-1554`) arma él mismo el texto `no se puede leer el archivo: {ruta}`. Por eso, bajo B3 (el lector cambia su texto), sigue verde mientras la ruta real de `PROPTECH_PARAMETROS` saldría entera. El camino real no se alcanza en Windows: un directorio lo frena antes el lector de variables (23:39:37, `rc=3`, `valor inválido en: PROPTECH_PARAMETROS`), y un archivo sin permiso de lectura exige Linux (S4 de verify 1). La ruta la fija quien despliega, no es algo que se tipea, así que no la llamo defecto. **Para confirmarlo como hallazgo** falta un caso real con `chmod 000` en Linux, o decidir que el doble alcanza.
- **O7. D4 cita líneas "de hoy" que ya no lo son.** Ver la lente 3. Es texto del plan sobre el código de partida y no cambia ningún comportamiento.

## Sospechas sin reproducir

- **S5. Ctrl-C durante los imports deja traceback.** `_main` empieza a proteger cuando arranca `main()`. Los imports de `ejemplo.py:27-81` tardan unos 1.3 s (23:38), y en esa ventana un `KeyboardInterrupt` sale con el traceback de Python. No escribe nada ni muestra datos. **Falta**: una señal real en Linux durante esa ventana. En Windows no pude mandarla a un proceso aislado, y un doble no prueba nada en este caso. Si esa ventana entra o no en "mientras corre", lo decide el plan.

## Qué vuelve, y a quién

| Hallazgo | Destino | Qué hace falta |
|---|---|---|
| F10 | Constructor, TDD | Sólo un test: `ValueError` da 9, visto en rojo con B7 |
| F11 | Constructor, TDD | Sólo un test: `--semilla=` sin configuración da 2, visto en rojo con B4 |
| O6 | Plan o auditor | Aceptar el doble o pedir el caso real en Linux |
| O7 | Plan | Corregir la referencia de líneas de D4, o marcarla como histórica |
| S5 | Plan | Decidir si la ventana de los imports entra en el escenario |

Ninguno toca producción, `acceso`, la matriz de permisos ni `cuenta_corriente`. Si se corrigen F10 y F11, cambia sólo `test_ejemplo_casos_de_uso.py`: alcanza con repetir la corrida focalizada de ese archivo, más `ruff` y `mypy` sobre él.

## Conteo de tests propio

Lo conté yo; no heredé el número del constructor.

| Qué | Revisión | Salida |
|---|---|---|
| `test_rompedor2.py`, 23:36:13: 3 de Ctrl-C a mitad de la carga, 1 de `ValueError` y 1 de orden | Limpia | `5 passed` |
| `test_arranque_tablas_protegidas.py -k ejemplo`, 23:38:26 | Limpia | `2 passed` |
| **Total en limpio** | | **7 tests, los 7 pasan** |
| Bajo mutantes, archivo del repo: B1 10, B2 10, B3 10, B4 10, B5 33, B7 13 | Copias | 86 ejecuciones. No cuentan como verde de la entrega |
| Bajo mutantes, mis tests: B7 2, B4 2 | Copias | 4 ejecuciones |
| Corrida descartada por mi arnés, 23:35:31 | Limpia | 5 ejecuciones. No cuentan |
| Comando real en un proceso aparte | Limpia y copias | 8 corridas: 2 de F11, 3 de `argparse` y la guarda, 2 del directorio de parámetros y la de `__file__` |

- **Colecta**: `test_ejemplo_casos_de_uso.py` tiene **241** tests (`10 selected` más `231 deselected` en la corrida de 23:31:20). En verify 1 conté 208 en ese archivo: son **+33**, lo que dice el brief.
- **Sólo corrí en limpio** la selección de `test_arranque_tablas_protegidas.py` y mis tests. El verde en limpio de los tests de F1 a F9 es del constructor (21:03:24 a 21:09:41, `3 failed, 319 passed`), y los archivos no cambiaron desde entonces (mismos `sha256`).

## JUICIO

- **Autor**: rompedor. **Comparación**: las cinco correcciones del grupo 9 y sus tests contra D4, D10, el spec delta, el README y los consumidores del brief, con mutantes distintos de los del constructor.
- **Confianza alta**: F1, F2, F3 y O4 quedaron corregidos en producción. Lo probé por caminos que el constructor no usó: tres mutantes nuevos sobre F1 (uno de ellos en el consumidor), Ctrl-C a mitad de la transacción con la base real, y `argparse` y la guarda fuera de desarrollo.
- **Confianza alta**: F10 y F11 existen como mutantes sobrevivientes. Cada uno tiene su corrida verde del archivo del repo bajo el mutante y un test propio que lo mata en la aserción que nombra (L-034).
- **Confianza media**: que ningún otro test del archivo mate a B4 y a B7. Corrí la selección, no los 241, por memoria y tiempo. Para B7 me apoyo en que no encontré ningún `ValueError` sembrado durante la carga en los tests que leí; para B4, en que los únicos tests con `--semilla=` son `:1648` y `:1658`.
- **Confianza media**: la severidad baja de los dos. No exponen datos y la producción está bien. Otro lector podría preferir aceptar F11 como deuda, porque es un detalle de orden entre dos códigos que no se pisan.
- Este informe no reemplaza el veredicto del auditor.

## SUPOSICIÓN

- **Windows**: todo corrió en Windows. El 130 de `sys.exit` es igual en Linux; el de una señal real no lo medí.
- **Ctrl-C**: lo provoqué con dobles que lanzan `KeyboardInterrupt` en tres casos de uso, no con una señal. Prueba la transacción y el manejo, no la entrega de la señal mientras `psycopg` está bloqueado en C.
- **Mis tests importan fixtures** de `tests/conftest.py` y del archivo del change, sin cargar los `conftest.py` del repo de forma automática. Por eso el primer intento falló sin `PROPTECH_PARAMETROS`. Después del ajuste usan la misma base, los mismos roles y la misma conexión que los tests del repo.
- **Otros `ValueError` posibles durante la carga** (F10): los dejo por lectura. No encontré uno real que llegue sin envolver, así que F10 es un hueco de vigilancia, no una falla.

## Chequeos no ejecutados

- **Suite completa**: por instrucción del brief; la corre el CI del PR.
- **`test_ejemplo_casos_de_uso.py` entero en limpio**: reuso la corrida final del constructor (21:03:24 a 21:09:41), sin cambios de archivos desde entonces (mismos `sha256`).
- **`ruff` y `mypy`**: reuso los del constructor (21:02:34 a 21:03:04). No agregué código al repo. Mis tests no pasaron por `ruff` ni por `mypy` y no se entregan así (L-005).
- **8.2 por el stack real** (`docker compose exec`): no lo corrí. No levanté ningún compose; los tests usaron `testcontainers`, que se limpió solo.
- **Linux**: S5 y el camino real de O6.

## Integridad de la entrega

No reparé nada ni dejé cambios en el repo. Mi único archivo nuevo es este informe. No hubo commit ni push, y no usé `git stash`.

```
$ date; git diff | sha256sum                                     # 2026-11-03 23:39:11
e5edff7a9b49b0858a80a9b61215094caca0601fc5a3cf8507c091043b63c015 *-        (igual que a las 23:30:29)
$ git diff --quiet -- . ':(exclude)infra/respaldos/respaldar.sh' ':(exclude)infra/respaldos/restaurar.sh' \
    ':(exclude)openspec/changes/ejemplo-robusto/informes/LEEME.md'; echo $?
0
$ sha256sum ejemplo.py cargador_yaml.py test_ejemplo_casos_de_uso.py
32648461d798f397617101d6f119b8d82f512c25768f9cb7779b485de6ccfe64
0cf45d0cce80bacd9c1b8306a262031010f9c5584d5f6061b65d0c58abad80f4
04201ab2b6af0d567df6f41ccf57d950717f04e72e626d358d73df4a1ffa8988
$ git status --short
 M infra/respaldos/respaldar.sh
 M infra/respaldos/restaurar.sh
 M openspec/changes/ejemplo-robusto/informes/LEEME.md
```

- `LEEME.md` e `infra/respaldos/*.sh` ya estaban modificados al empezar, y no los toqué.
- **Proyecto `proptech`**: sus ocho contenedores siguen como estaban. No los usé ni toqué sus volúmenes. No quedó ningún contenedor de `testcontainers` al terminar.
- **Sin leer ni imprimir**: `infra/.env`, `infra/.env.example` y `docker compose config`.
