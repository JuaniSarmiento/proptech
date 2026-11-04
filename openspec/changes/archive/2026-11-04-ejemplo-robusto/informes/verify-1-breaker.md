# Rompedor · verify · intento 1 · ejemplo-robusto (C-27)

- **Rol**: rompedor, subagente nativo `role-breaker`. Una sola vuelta, por LOW.
- **Executor declarado**: Claude Opus 5.5, por la declaración del entorno. **Familia**: Claude, la misma del constructor. El proyecto no declara `## Role executors`; L-025 pide otra familia, así que la independencia es limitada.
- **Fecha**: 31/10/2026, de 18:13 a 19:00 aproximadamente (-03:00).
- **Revisión**: base `9649471` sin commits, `git diff | sha256sum` `22bb0402eb35deb1fd38d49c209ddfe77d1a8d5b1522fce7ef9af0e199373d41`, y `test_puntos_de_entrada_prohibidos.py` en `af17cd1fdd72c17d4e6a253ad3cf8087661102374316bd014396042ecb0871a2`.
- **Resultado**: las cuatro promesas centrales aguantan por el comando real (detecta el ejemplo cambiado, dos cargas a la vez, códigos sin traceback en el camino de error normal, sin Redis). **Hay 4 fallas reproducidas de severidad baja y 5 mutantes sobrevivientes.** Vuelven al constructor por TDD; F4 y las observaciones O1 y O4 necesitan antes una decisión del plan. Este informe no aprueba nada: decide el auditor.

## Fuentes leídas, en orden

1. `knowledge-base/15_lecciones.md`, completo (L-001 a L-067).
2. `openspec/changes/ejemplo-robusto/proposal.md`, `design.md`, `specs/datos-semilla/spec.md`.
3. `complejos/aplicacion/ejemplo.py` entero; `git diff` de `configuracion.py`, `base_de_datos.py`, `test_arranque_tablas_protegidas.py` y `README.md`; `test_puntos_de_entrada_prohibidos.py`.
4. `compartido/semilla.py`, `georef.py`, `cargador_yaml.py`, `base_de_datos.py`, `configuracion.py:1-420`, `parametros.py:289-301`; `acceso/aplicacion/vinculacion_de_desarrollo.py`, `alta_inicial.py`, `usuarios.py:245-302`.
5. `tests/integracion/test_ejemplo_casos_de_uso.py`: `:1-240`, `:641-706`, `:749-795`, `:798-818`, `:851-890`, `:934-975`, `:992-1020`, `:1054-1133`, `:1224-1250`, `:1253-1542`, `:1642-1666`, `:1767-1779`, `:2160-2332`. También `tests/conftest.py:1-140` y `tests/integracion/_edificios.py:24-82`.
6. `migraciones/versions/0005` y `0013`; `compartido/texto.py`; `complejos/aplicacion/escritura.py:140-200`, `unidades.py:31-75`; `proptech_api/app.py:100-125`; `proptech_worker/ajustes.py:205-225`; `openspec/specs/acceso-de-desarrollo/spec.md:24-35`; `README.md:88-140`; `config/semilla/edificio-ejemplo.yaml`.
7. **Después de atacar** (18:46): `informes/apply-2-constructor.md`, `propose-2-plan-reviewer.md`, `propose-1-plan-reviewer.md`, `apply-1-constructor.md`, `tasks.md:1-40` y `:120-226`, `LEEME.md`.

**Sin leer**: `infra/.env` e `infra/.env.example`. No imprimí `docker compose config`. Tampoco abrí `.git/informes-*`.

## Contaminación por otros informes

- Hasta las 18:46 no había leído ningún informe del constructor ni del revisor del plan. Lo único que conocía de ellos era lo que trae el brief: decisiones que no son defectos, chequeos vigentes y que la línea del `replace` era mía.
- **F1, F2, F3 y F4 y los mutantes M1 a M7 salieron antes de leerlos.** `apply-1-constructor.md` ya anotaba que `SemillaInvalida` nombra identificadores (H-4) y que `KeyboardInterrupt` no pasa por el 9 (SUPOSICIÓN): los encontré por mi cuenta y coincidimos en el hecho, pero el constructor los dio por aceptables y yo los reporto contra el texto del spec y de D4.
- **Después de leerlos** corrí M15 y M16, el `lock_timeout`, los tests rojos y los consumidores. La idea de M15 y M16 salió de leer `test_otro_edificio_...`, no de un informe.
- M3, M5 y M7 tocan las mismas garantías que M2.1, M3.3 y M2.2 del constructor. Los elegí antes de leer su lista, y M3 va por otro camino: un `pg_advisory_xact_lock` en producción, no un `Lock` en el test.
- Sin Engram: la herramienta no está disponible en este subagente.

## EVIDENCIA

Todo sobre la revisión del encabezado, en Windows, con el `.venv` del repo. Los guiones y logs quedan en `C:\Users\espej\AppData\Local\Temp\claude\C--Programacion-proptech\19e1c5b0-3037-4aa8-9599-2cf049059770\scratchpad\rompedor\` (no viajan con el repo). Los mutantes corrieron sobre una **copia de `backend/src`** en ese directorio, con `PYTHONPATH`, sin tocar el repo (L-013). La base es un único Postgres descartable, `proptech-c27-rompedor`, `postgres:18.6-trixie`, `--memory=450m`, con una base plantilla migrada por `roles antes`, `alembic upgrade head` y `roles despues`, y una copia por caso (`CREATE DATABASE ... TEMPLATE`).

**Antes de cada caso con base guardé una foto** de todas las tablas de `public`: `count(*)` y `md5` de `ctid`, `xmin` y la fila. "No escribió nada" quiere decir que esa foto dio igual, también `xmin`.

| Hora | Qué | Resultado |
|---|---|---|
| 18:13:07 | `git rev-parse HEAD`, `git diff \| sha256sum`, `sha256sum` del test sin trackear | `9649471`, `22bb0402...`, `af17cd1f...` |
| 18:19 a 18:24 | Comando real sin base (puerto 1): guarda, argumentos, emisor, `--semilla`, contenido de semilla, parámetros, Georef, variables. 73 corridas | Códigos 1, 2 y 3 correctos salvo F1 y O1 |
| 18:26 a 18:28 | Primera, segunda y tercera carga; parámetros cambiados | 0, foto igual desde la segunda |
| 18:29 a 18:32 | 33 ediciones por SQL sobre el ejemplo cargado, una base por caso | 24 con 6 y su dato nombrado; 5 con 0 esperado; 4 observaciones |
| 18:32 a 18:33 | Procesos reales en paralelo y corte de conexión | Sin defectos |
| 18:34 a 18:36 | Códigos 4, 5, 7 y 8 reales | Sin defectos |
| 18:36 a 18:39 | Semillas aceptadas, espera, servidor mudo y con basura, pool de borde | F2; S1 |
| 18:40:36 | Ctrl-C durante la espera | F3 |
| 18:42 a 18:43 | Comparación por valor, orden, bordes del nombre, semillas rechazadas por el caso de uso | F2 |
| 18:44 a 18:50 | Mutantes M1 a M7, M15 y M16 | 5 sobreviven |
| 18:48:19 | `lock_timeout`, `statement_timeout`, sólo lectura, variantes de la guarda | O3, O5 |
| 18:50 y 18:51 | `pytest` de los rojos, dos corridas | `12 failed in 25.51s`, `12 failed in 23.00s` |
| 18:40 a 18:53 | Consumidores | Ver "Conteo de tests propio" |

## Lente 1: correctitud

### Cada código de salida, por el proceso real

| Código | Entradas probadas | Resultado |
|---|---|---|
| 0 | Primera carga, segunda, parámetros cambiados, misma semilla por `--semilla`, escala distinta (`"0.1"`, `"60"`), unidades en otro orden, nombre con bordes y NBSP, vinculada, otra persona, asignación de más, otro edificio con unidad `1A` propia, pool en 1 | Correcto |
| 1 | Sin `PROPTECH_ENTORNO` y sin ninguna otra variable; `produccion`; con `--clerk-usuario xx` | Correcto |
| 2 | Sin valor, `--clerk-usuario=`, abreviatura, id como subcomando, dos `cargar`, salto final, dígitos no ASCII, 65 caracteres | Correcto, sin repetir el valor |
| 3 | 12 variantes de `CLERK_EMISOR`; variables rotas; semilla vacía, binaria, latin-1, UTF-16, raíz no mapa, clave no texto, duplicada, anidada 5000 niveles, alias cíclico, tag Python, más de 1 MiB; parámetros y Georef rotos | Correcto, salvo F1 y F4 |
| 4 | Migrador, superusuario, respaldo (`BYPASSRLS`), tabla con otro dueño, tabla faltante, base sin migrar | Correcto, foto igual, nombra la tabla |
| 5 | Puerto cerrado, clave equivocada, base y rol inexistentes, host con espacio, servidor mudo a 2 s y 5 s, servidor que contesta basura, `pg_terminate_backend` a mitad de la carga | Correcto, sin datos de la conexión. Ver O3 y S1 |
| 6 | Ver la tabla de abajo | Correcto |
| 7 | Otra cuenta, cuenta de otra persona del ejemplo, carrera con dos cuentas | Correcto, foto igual, sin repetir el id |
| 8 | `IntegrityError` real (la persona de id fijo en otra administración), `REVOKE SELECT ON invitacion`, base de sólo lectura, espera agotada (10.6 s totales) | Correcto, sin parámetros del driver, foto igual |
| 9 | `NotImplementedError` y `EntradaInvalida` reales | Nombra sólo el tipo. Ver F2 |

### Ediciones por SQL con el comando real

El constructor altera la semilla (D1). **Yo edité la base** como superusuario, otro camino hacia la misma promesa (L-004). Cada caso sobre una base nueva, todos con foto igual:

- **Código 6 y dato nombrado**: `estado_migracion`, `unidades[1A].tipo`, `.piso`, `.piso` en NULL, `.coeficiente`, `.superficie_m2`, unidad de menos, de más y renombrada, grupo de más y de menos, `grupos.ascensor.modo`, miembro de más y de menos, coeficiente propio editado y en NULL, edificio renombrado, en mayúsculas y duplicado, `persona.nombre`, `.email`, `.email` en NULL, sin asignación, con otro rol, persona borrada, y cinco diferencias a la vez (las cinco aparecen).
- **Coeficiente propio**: la semilla del repo no tiene grupos `propios`, así que cargué una con `cocheras` en `propios` y edité la base: `grupos.cocheras.unidades[C1].coeficiente: difiere de la semilla`.

### Escenarios del spec

Todos los escenarios de `datos-semilla` corrieron por el proceso real salvo "La API y el worker siguen exigiendo Redis", que es por sus tests. Los más pesados:

- **Dos cargas a la vez**: 3 rondas de 3 procesos sin barrera: siempre 1 `ejemplo cargado`, 2 `ya estaba`, 13 unidades y 18 filas de auditoría. Con la misma cuenta: `vinculado` y `ya estaba vinculado`. Con dos cuentas: una vincula y la otra da 7.
- **Corte a mitad de la carga** (L-020): ganador retenido por un `LOCK TABLE auditoria`, perdedor esperando en el `ON CONFLICT`, `pg_terminate_backend` al ganador. El ganador da 5 sin traceback, y el perdedor toma la carga y da 0 con 13 unidades. Sin perdedor: 5 y cero filas.
- **El edificio aparece durante la espera**: moví el edificio a otra administración, esperé a ver la consulta en `pg_stat_activity` y lo devolví: 0 y `ya estaba`.
- **Otras administraciones**: otra con el mismo nombre de edificio, el mismo email y la misma cuenta: 0, `md5` y `xmin` iguales.
- **Sin Redis**: sin variables de Redis y con basura en `REDIS_PORT`, `CLERK_JWT_KEY`, `INVITACIONES_CLAVE_CIFRADO` y `PROPTECH_URL_PUBLICA`: 0.

**Resultado de la lente**: F1, F2, F3 y F4, más O1, O2, O3 y O4.

## Lente 2: cableado

- **El camino se alcanza por el comando real**: todas las corridas de arriba son `python -m proptech_core.complejos.aplicacion.ejemplo` en un proceso aparte. `git grep` en `infra/`, `.github/` y el `Dockerfile`: nadie más corre este comando. `infra/ci/humo.sh:831` corre `compartido.semilla`, otro comando, cuyo `_main` no cambió. Ningún script depende de los códigos. El uso real está en `README.md:109`.
- **`Configuracion` sin `clerk_emisor=`**: `git grep` de `Configuracion(clerk_emisor` y `clerk_emisor=` en `backend/`, `infra/`, `.github/` y `web/`: sin coincidencias. Nadie usa `base_de_datos.Configuracion`.
- **Quienes llaman a `crear_engine`**: `proptech_api/app.py:90`, `proptech_worker/ajustes.py:197`, `alta_inicial.py:160` y `ejemplo.py:567`. Las cuatro pasan un objeto con todos los campos del `Protocol`. `crear_engine` no lee nada fuera del `Protocol` (`base_de_datos.py:64-75`).
- **La API y el worker siguen exigiendo Redis**: `test_la_api_y_el_worker_siguen_exigiendo_redis`, 4 casos en verde. `redis_host` y `redis_password` siguen sin valor por defecto en `_LectorDeApp`. Sus tests de arranque y de configuración: 156 en verde.
- **`test_arranque_tablas_protegidas.py`**: 12 en verde; el diff sólo mueve el caso `ejemplo`, los de `api`, `worker` y `alta_inicial` siguen dentro del `pytest.raises`.
- **`test_fronteras_de_modulos.py`**: 3 en rojo, las esperadas. Las leí: las tres fallan en la comparación y el contenido es correcto salvo el separador, incluida `test_vinculacion_de_desarrollo_solo_desde_ejemplo`, que da `['proptech_core\complejos\aplicacion\ejemplo.py']` como único importador. Es la que importa a este change. **No la corrí en Linux.**
- **`test_vocabulario_vigente.py`**: en verde.
- **`README.md`**: tabla igual a la del spec en los 10 códigos; lo que agrega en 1 y 6 es cierto. La vinculación por `docker compose exec` no la corrí: uso la evidencia de 8.2.
- **`--semilla` y `PROPTECH_PARAMETROS` llegan al lector**: una semilla con `pisos: 9` da 0 (O2) y una con otra localidad da 3, así que el archivo se lee de verdad.

**Resultado de la lente**: limpia en consumidores. Los huecos que encontré son de tests: F5 a F9.

## Lente 3: veracidad

| Texto | Contra | Resultado |
|---|---|---|
| D4: `ConfiguracionInvalida`, `ParametrosInvalidos`, `SemillaInvalida` y `GeorefInvalido` "no repiten valores, salvo la ruta del lector" | Corrí variantes de los cuatro | **Falso para `SemillaInvalida`**: F4. Cierto para los otros tres, con `VALOR_SEMBRADO` en un valor de parámetros (18:53) |
| Spec, "Configuración rota": "sin mostrar el valor recibido" | Lo mismo | **Falso para la semilla**: F4 |
| `ejemplo.py:91-93`: "`_main` no deja escapar ninguna excepción" | Ctrl-C real por doble de `time.sleep` | **Falso para `KeyboardInterrupt`**: F3 |
| `_ejecutar`: "El orden es parte del contrato (D4): guarda, id, ..." | Corrida fuera de desarrollo con un argumento roto | **Incompleto**: `_leer_argumentos` va antes de la guarda. O1 |
| D4, mensaje del 5: "no se pudo conectar o se cortó la conexión" | `lock_timeout` | **Falso en ese caso**: O3 |
| `test_puntos_...`, docstring: "la guarda del escenario" | Spec `acceso-de-desarrollo:29` | **Parcial**: O5 |
| `test_el_comando_real_con_la_espera_agotada`, docstring: "Son los 50 intentos reales, unos 5 segundos" | Mutante `intentos=1` | Cierto en producción (10.6 s totales), **sin aserción que lo vigile**: F6 |
| `_LectorDelEjemplo`: "`test_ejemplo_casos_de_uso.py` les pasa los mismos valores" | `:1310-1333` | Cierto, pero no alcanza para el validador ASCII: F5 |
| Comentario `ejemplo.py:456-461`: una corrida en paralelo no llega a la espera | Carrera real con el ganador retenido | Cierto: el perdedor nunca dio 8 |
| D2, tabla de edificios | Renombrado, duplicado y otro con otro nombre | Cierto, y sin esperar: 3.9 a 4.3 s totales, contra 10.6 de la espera |
| D3, "alcanza con tiene": asignación de más y otra persona | SQL real | Cierto |
| D4, `TablasDeSoloAgregarDesprotegidas` sólo trae la tabla y el motivo | Lectura y corridas reales | Cierto |
| Docstring de `ejemplo.py:15-21`, lo que se compara y lo que no | SQL real | Cierto |
| `apply-1-constructor.md`, JUICIO, confianza alta: "los códigos 0 a 9 se comportan como dice la tabla" | F2 y O3 | **Exagerado** |
| `apply-2-constructor.md` y `tasks.md`: conteos 208, 12, 66 y 3 | `pytest --collect-only`, `289 tests collected` | Cierto |
| `tasks.md` 8.2, "Límite": 8 y 9 sin el stack real | Lo que declara | Cierto. Yo corrí 8 y 9 por el proceso real, sin compose |
| `tasks.md` 5.1, "Se sumó (H-4)": `--semilla` puede ser el id | `--semilla user_Sembrado1`, también en una carpeta | Cierto: `<semilla>`, el id no sale. Efecto colateral: F1 |

**Resultado de la lente**: F4 y F3 son textos falsos con reproducción. Lo demás, como dice la tabla.

## Fallas reproducidas

Los tests rojos están en `...\scratchpad\rompedor\rojos\test_rompedor_rojos.py`, y usan `comun.py` y `bd.py` de la carpeta de arriba. Corrida: `.venv/Scripts/python.exe -X utf8 -m pytest <ese archivo> -q -p no:cacheprovider --tb=line --no-header --show-capture=no` desde `backend/`, 18:51:29 a 18:51:53: **`12 failed in 23.00s`**, cada uno en su aserción (L-034). Como esa carpeta no viaja, cada falla trae el caso para escribirlo de nuevo con TDD.

Base común del entorno para F1 y F4: `PROPTECH_ENTORNO=desarrollo PROPTECH_PARAMETROS=<ruta> POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=1 POSTGRES_DB=x POSTGRES_APP_USER=proptech_app POSTGRES_APP_PASSWORD=x`.

### F1. El reemplazo de la ruta deforma el mensaje si `--semilla` es corta o es una palabra del texto. Severidad baja

Es la línea que el plan dejó a mi cargo (`ejemplo.py:560-565`). **Para lo que fue escrita funciona**: con el id como ruta, en una carpeta, en un directorio o sin el archivo, el id no sale nunca. El problema es que `str.replace` corre sobre el mensaje entero, no sobre la ruta.

```
$ ... python -m proptech_core.complejos.aplicacion.ejemplo cargar --semilla e     # 18:57:01
no s<semilla> pu<semilla>d<semilla> l<semilla><semilla>r <semilla>l archivo: <semilla>
codigo: 3

$ printf 'version: 2\n' > s; ... cargar --semilla s
<semilla>emilla inválida:
ver<semilla>ion: Input <semilla>hould be 1
edificio: Field required
unidade<semilla>: Field required
grupo<semilla>: Field required
codigo: 3

$ ... cargar --semilla unidades      # archivo con un identificador repetido, 18:22
<semilla>: hay identificadores repetidos: '1A'
grupos.ascensor: el identificador '1B' no existe en <semilla>
```

- **Contra qué**: spec, "Configuración rota": "nombra el problema".
- **Test rojo**: con `--semilla a`, `e` y `archivo` sin archivo, exigir `no se puede leer el archivo` en la salida de errores; con un archivo `s` inválido, exigir `version:`; con un archivo `unidades` inválido, exigir `unidades: hay identificadores repetidos`. Los 5 dan rojo: `AssertionError: no se puede leer el <semilla>rchivo: <semilla>`.
- **El gemelo**: el `replace` de `<parámetros>` tiene la misma forma, con una ruta relativa corta. **No lo corrí**, porque `PROPTECH_PARAMETROS` lo controla quien despliega, no lo que se tipea.

### F2. Una semilla que el lector acepta y el caso de uso rechaza termina en 9, sin decir qué tiene. Severidad baja

```
$ python -m ...ejemplo cargar --semilla <identificador de 41 caracteres>      # 18:42:51, base migrada sin el ejemplo
error inesperado: EntradaInvalida        rc=9   foto igual

$ ... --semilla <pisos: 0, todas las unidades en PB>
error inesperado: EntradaInvalida        rc=9   foto igual

$ ... --semilla <estado_migracion: confirmada>       # 18:36:36
error inesperado: NotImplementedError    rc=9   foto igual
```

- **Causa**: `leer_semilla` deja pasar `pisos` desde 0 (`semilla.py:63`) e `identificador` de cualquier largo, y `crear_edificio` y `DatosUnidad` piden `pisos >= 1` y hasta 40 caracteres. `Literal` acepta `confirmada`, y `_crear_desde_cero:226` lanza `NotImplementedError`. Nada en `_ejecutar` captura `EntradaInvalida`, así que cae en la red del 9.
- **Contra qué**: tabla del spec, código 3 ("semilla ... inválidos"); escenario "Configuración rota", que además pide no conectarse; y el Goal de `design.md`: "que un error se entienda sin leer un traceback". El 9 nombra el tipo y no el campo, y D4 dice que para depurarlo hay que llamar a `cargar()` desde un test.
- **Test rojo**: los tres casos, sobre una base migrada, exigir código 3: `AssertionError: error inesperado: EntradaInvalida`.
- **Alcance**: sólo se llega con `--semilla` o editando el archivo. La semilla del repo carga bien. No queda nada a medias: la transacción revierte.
- **No probé** `Conflicto`, la otra excepción propia de `complejos/aplicacion/errores.py`, porque `leer_semilla` ya frena los repetidos.

### F3. Ctrl-C deja traceback, y un comentario dice que no. Severidad baja

Es la única salida que tiene una persona con el comando colgado: no hay `statement_timeout` (fuera del change), y lo vi quedarse esperando con un `LOCK` hasta que le corté la conexión, a los 18 s de arrancar.

```
$ python -c "<doble: ejemplo.time.sleep lanza KeyboardInterrupt; sys.argv con --clerk-usuario; ejemplo.main()>"     # 18:40:36, administración sin edificio
rc 3221225786 0xc000013a
traceback en stderr: True | id en stderr: False | clave: False
  File "...\ejemplo.py", line 626, in _main
  File "...\ejemplo.py", line 574, in _ejecutar
  File "...\ejemplo.py", line 462, in cargar
KeyboardInterrupt
```

- **Contra qué**: `ejemplo.py:91-93` ("`_main` no deja escapar ninguna excepción"); spec: "sin traceback" y "una excepción que ninguna familia contempla". El traceback no trae el id ni la contraseña. El 1 sigue siendo exclusivo de la guarda.
- **Contra lo declarado**: `apply-1-constructor.md` lo deja en SUPOSICIÓN, "a propósito, y no lo probé". Ni el spec ni D4 lo dicen.
- **Test rojo**: doble de `crear_engine` que lanza `KeyboardInterrupt`; `_main(["cargar"])` no tiene que dejarlo escapar: `Failed: _main dejo escapar KeyboardInterrupt`.
- **Decisión**: qué código le toca. El spec no tiene uno; lo habitual es 130. O se corrige el comentario y el spec lo declara fuera.

### F4. El spec y D4 prometen que la semilla inválida no repite el valor, y lo repite. Severidad baja, de texto

```
$ ... cargar --semilla <miembro "VALOR_SEMBRADO">       # 18:23:02
semilla inválida:
grupos.cocheras: el identificador 'VALOR_SEMBRADO' no existe en unidades
rc=3
$ ... <identificador "VALOR_SEMBRADO", piso "99">
unidades[1].piso: fuera del vocabulario del edificio (identificador 'VALOR_SEMBRADO')
$ ... <"1B" cambiado por "1A">
unidades: hay identificadores repetidos: '1A'
```

- **Contra qué**: escenario nuevo "Configuración rota": "o el archivo de parámetros, la semilla o Georef son inválidos ... nombra el problema sin mostrar el valor recibido". D4: "No repiten valores (L-002, L-007), salvo la ruta".
- **Por qué es de texto**: el requisito viejo de `datos-semilla` pide nombrar la unidad (`semilla.py:182-186`), y H-4 del constructor lo sabía. **Lo que el plan corrigió fue la ruta, no esto**, y los dos textos quedaron enfrentados en la misma capability. No es un secreto, salvo que alguien lo escriba en el archivo.
- **Test rojo**: los tres casos, exigir que el valor entre comillas no aparezca: `assert "'1A'" not in 'semilla inválida...'`.
- **Va al plan, no al constructor**: o el spec y D4 exceptúan el identificador de unidad, o cambia el lector. Yo elegiría exceptuarlo, porque el mensaje sin el identificador no sirve.

### Mutantes sobrevivientes: F5 a F9

**La producción está bien en los cinco**: lo comprobé con el comando real. Son garantías que nadie vigila (L-035). Se resuelven agregando el caso que falta, y cada uno se ve fallar con el mutante.

F5 es M1, F6 es M2, F7 es M4, F8 es M15 y F9 es M16. Forma de correrlos: copia de `backend/src`, mutante sobre la copia, `PYTHONPATH=<copia>`, `.venv/Scripts/python.exe -m pytest tests/integracion/test_ejemplo_casos_de_uso.py -q -p no:cacheprovider --tb=line --no-header -k "<selección>"`. Comprobé con `proptech_core.__file__` que se importa la copia, y con `diff -q` que difiere del repo.

| # | Mutante, en la copia | Selección | Salida | Hora | El caso que falta |
|---|---|---|---|---|---|
| F5 | `_LectorDelEjemplo._enteros_del_pool_ascii_estrictos` sólo con `db_pool_size`: saca `db_pool_recycle_s`, `db_pool_timeout_s` y `db_connect_timeout_s` | `test_la_configuracion_rota_se_nombra_sin_mostrar_el_valor` | `94 passed, 114 deselected` | 18:44:01 | `" 5"` y `"5_0"` en esas tres variables, en los dos lectores. Con el mutante, `DB_POOL_RECYCLE_S=" 900"` se acepta (`900`); sin él, `ConfiguracionInvalida` |
| F6 | `intentos: int = 1` por defecto en `cargar`: el comando ya no espera | `test_el_comando_real_con_la_espera_agotada or test_el_edificio_que_aparece or test_la_administracion_sin_edificio` | `3 passed, 205 deselected` | 18:44:53 | Los dos que llaman a `cargar()` pasan `intentos` a mano, y el del comando no mira la duración. Falta un piso de tiempo, o el escenario por el proceso real |
| F7 | `if not super_admin["asignaciones"]:` en lugar de `any(... rol == "super_admin")` | `test_el_super_admin_del_ejemplo_cambio` | `3 passed, 205 deselected` | 18:44:20 | `UPDATE asignacion_rol SET rol='contador'`. El test sólo borra la asignación. En el real da 6 con `persona.asignaciones` |
| F8 | `FROM unidad WHERE complejo_id IS NOT NULL OR complejo_id=:id`: mira las unidades de toda la administración | `test_otro_edificio_con_otro_nombre or test_la_semilla_sin_alterar` | `2 passed, 206 deselected` | 18:49:12 | Otro edificio **con unidades**. El de `_crear_otro_edificio` nace vacío (L-017). En el real da 0 con una unidad `1A` en el otro edificio |
| F9 | `WHERE (complejo_id IS NOT NULL OR complejo_id=:id) AND NOT es_generales`: mira los grupos de toda la administración | La misma | `2 passed, 206 deselected` | 18:49:40 | Otro edificio **con un grupo propio**. El otro edificio sólo tiene Generales, que la consulta excluye |

**Límite de F5 a F9**: corrí la selección, no el archivo entero bajo cada mutante, por tiempo y memoria. Para afirmar que nadie más los mata me apoyo en esto: `rg` sobre el archivo muestra `intentos=` sólo en `:739` y `:783`; ningún `SET rol`; y `_crear_otro_edificio` no agrega unidades ni grupos. Correr el archivo entero bajo cada uno lo confirmaría.

**Mutantes que sí murieron**, y prueban que esos tests vigilan:

| Mutante | Salida |
|---|---|
| M3: `SELECT pg_advisory_xact_lock(4242)` antes del `INSERT` en `cargar`, serializa en producción | `threading.BrokenBarrierError`, `1 failed`, 18:45:32 |
| M5: compara la primera persona de la lista, no la de id fijo | `EjemploDistinto` en `[otra_persona]`, `1 failed, 2 passed`, 18:46:01 |
| M7: no reintenta después de la espera | `Failed: no volvió a mirar después de la espera`, 18:46:28 |

## Observaciones reproducidas que dependen de una decisión

Las corrí, pero el texto vigente no alcanza para llamarlas defecto, o el plan las deja afuera a propósito.

- **O1. La guarda va después de `argparse`** (18:19). Con `PROPTECH_ENTORNO=produccion`: `cargar --foo`, sin subcomando o `borrar` dan **2** y no dicen nada de `PROPTECH_ENTORNO`; `cargar --help` da **0**. Con `cargar --clerk-usuario xx` da 1, correcto. No conecta ni escribe nada. D-112 dice "sin eso termina con código distinto de 0, **lo dice**", y `_ejecutar` no nombra a `argparse` en su orden. Decide el plan si un error de uso fuera de desarrollo cuenta como correr el comando.
- **O2. Lo que la comparación no mira**, código 0 con `ya estaba` (18:32, 18:37): `activo=false` en un grupo, `pisos`, `subsuelos` y ubicación cambiados, una semilla con `pisos: 9`, y Generales borrado. Lo último exige apagar los triggers, y el spec enumera sólo "unidades, grupos y estado de migración", así que **no es defecto del spec**. Sí es cierto que `pisos`, `subsuelos` y la ubicación salen de la semilla, y que `activo` se cambia desde la API (3c, por lectura). "Un grupo de menos" podría leerse como desactivado.
- **O3. No todo `OperationalError` es base caída** (18:48). `ALTER DATABASE ... SET lock_timeout='300ms'` con la tabla bloqueada, y `statement_timeout='1ms'`: código 5, "no se pudo conectar o se cortó la conexión". Es lo que D4 pide, pero la tabla del spec dice "otro error de la base" para el 8, y el mensaje no es cierto en esos casos. Sólo se llega con esos ajustes en la base. Ningún dato sale.
- **O4. `--semilla=` vacío usa la semilla por defecto sin avisar** (18:20). Llega a conectarse: código 5 con la base cerrada. `args.semilla or ...` en `ejemplo.py:552`. Su gemelo, `--clerk-usuario=`, da 2. Un `--semilla "$VARIABLE"` sin definir carga el edificio con otra semilla. El spec no lo menciona.
- **O5. La guarda de QA-5 no ve variantes** (18:48): `compose.desarrollo.yaml` en la raíz, `backend/compose.desarrollo.yaml` e `infra/compose.desarrollo.yml` dan `guarda ve: []`. Tampoco mira "ni una variable que lo active". `proposal.md` acota a los dos que mira, así que cumple su tarea; lo que se excede es el docstring, que dice "la guarda del escenario".

## Sospechas sin reproducir

- **S1. El límite de conexión es por dirección.** Servidor mudo sólo en `127.0.0.1`, límite de 2 s: 5.9 s con `127.0.0.1` y **8.2 s con `localhost`**, con unos 3.6 s de arranque. El spec dice "dentro del límite". Medí la diferencia, no la causa. **Falta**: resolver `localhost` en esa corrida y medir por dirección, también en Linux.
- **S2. `print` después del commit.** Si la salida está cerrada, `print` lanza dentro del `try` y da 9 con la carga ya confirmada. Por lectura de `ejemplo.py:582-588`. **Falta**: correrlo con la salida cerrada, en Linux (`/dev/full`).
- **S3. `--semilla` con un archivo especial.** `leer_archivo` lee todo antes del tope de 1 MiB (`cargador_yaml.py:68` y `:112`), así que `/dev/zero` o `CON` podrían colgarlo o agotar la memoria. Por lectura, y no lo corrí por el límite de memoria. **Falta**: Linux con `ulimit`.
- **S4. Archivo de parámetros existente que no se deja leer.** El constructor lo prueba con un doble, y yo tampoco lo corrí real: en Windows no armé el permiso. **Falta**: `chmod 000` en Linux, sin root.

## Qué vuelve al constructor, y qué al plan

| Hallazgo | Destino | Qué hace falta |
|---|---|---|
| F1 | Constructor, TDD | Sacar la ruta del mensaje sin tocar el resto del texto. `cargador_yaml.py` está fuera de los archivos del change; si la corrección lo exige, se avisa |
| F2 | Constructor, TDD | Traducir el rechazo del caso de uso a su código. `EntradaInvalida` no está importada en `ejemplo.py` hoy |
| F3 | Plan, después constructor | Qué código le toca al Ctrl-C, o declararlo fuera y corregir el comentario |
| F4 | Plan | Exceptuar el identificador de unidad en el spec y en D4, o cambiar el lector |
| F5 a F9 | Constructor, TDD | Sólo tests: el caso que falta, visto fallar con el mutante |
| O1, O4 | Plan | Decidir, y si es defecto, TDD |
| O2, O3, O5 | Plan o auditor | Decidir si queda como está, y dejarlo escrito |

Ninguno exige tocar `acceso`, la matriz de permisos ni `cuenta_corriente`. Las correcciones cambian la revisión: la suite completa que el orquestador corre después de esta vuelta tiene que esperarlas.

## Conteo de tests propio

Contado por mí, sin heredar el del constructor.

**Sobre la revisión entregada, sin `PYTHONPATH`:**

| Selección | Hora | Salida |
|---|---|---|
| `test_fronteras_de_modulos.py`, `acceso/test_vocabulario_vigente.py`, `test_puntos_de_entrada_prohibidos.py` | 18:40:51 a 18:41:44 | `3 failed, 67 passed in 47.34s`. Las 3, por separador de ruta |
| `test_configuracion.py`, `test_configuracion_pool.py`, `test_base_de_datos_pool.py`, `test_arranque_api.py`, `test_arranque_worker.py` | 18:52:07 a 18:52:22 | `156 passed in 11.94s` |
| `test_arranque_tablas_protegidas.py` | hasta 18:53:01 | `12 passed, 1 warning in 35.59s` |
| `test_ejemplo_casos_de_uso.py -k` Redis de la API y el worker (4), carga sin Redis (1), dos cargas (1) | hasta 18:53:32 | `6 passed, 202 deselected, 1 warning in 28.16s` |
| **Total** | | **244 tests: 241 pasan y 3 fallan, las conocidas** |

- **Colecta**: `289 tests collected` en los cuatro archivos del change, y **`4901 tests collected in 5.04s` en el repo entero** (18:58:40, en Windows). Iguales a los del constructor: no bajó el número. La colecta no dice cuántos se saltean: eso lo da la suite completa. Los `deselected` de arriba son por mi `-k`.
- **Bajo mutantes, sobre la copia**: 109 ejecuciones (94, 3, 3, 1, 3, 1, 2 y 2). No cuentan como verde de la entrega.
- **Mis rojos**: 12 tests, 2 corridas, 12 en rojo las dos veces.
- **Comando real en proceso aparte**: 192 corridas, sin contar las que lanzan los tests.
- **Dos corridas que no cuentan**: a las 18:48, `mutar.py` tenía un error de sintaxis, así que M15 y M16 corrieron sobre la copia limpia (`1 passed` cada una). Las repetí a las 18:49 con `diff -q` que muestra el mutante aplicado; los números de arriba son los de la repetición.
- **Mis guiones que se cortaron por mi propio SQL**: cuatro veces, por `CHECK`, FK y unicidad al editar la base. No son fallas del código. Corregí el SQL y seguí desde ese caso.

## JUICIO

- **Autor**: rompedor. **Comparación**: código entregado contra `proposal.md`, D1 a D9, el spec y los consumidores del brief.
- **Confianza alta**: las cuatro promesas centrales se cumplen por el comando real en Windows: detecta cada dato editando la base, 5 cargas paralelas sin carrera perdida, corte de conexión sin carga a medias y sin traceback, y corre sin Redis. Lo probé por otro camino que el del constructor (L-004).
- **Confianza alta**: F1 a F4 existen. Cada una tiene comando, salida y test en rojo en su aserción.
- **Confianza media**: la severidad baja de las cuatro. Es un comando de desarrollo, con la guarda de D-112, y ninguna expone el id, la contraseña ni la conexión: `id en stderr: False` y `clave: False`. Otro lector podría pesar más F2, porque el Goal del design es entender el error sin traceback.
- **Confianza media**: que ningún otro test mate a F5 a F9, por el límite que declaro ahí.
- **Confianza alta**: no aparece nada que haga subir el change de LOW. Ningún hallazgo toca `acceso`, permisos ni `cuenta_corriente`.
- **La línea del `replace`**: cumple lo que promete sobre el id, en las formas que probé. El defecto es de alcance, no de filtración.
- Este informe no reemplaza el veredicto del auditor.

## SUPOSICIÓN

- **Linux y el CI**: todo corrió en Windows. El código de salida del Ctrl-C (`0xC000013A`) es de Windows; en Linux espero 130, sin haberlo corrido.
- **El stack real**: no corrí `docker compose exec ... api`, el camino del `README.md`. Uso la evidencia de la tarea 8.2 de `tasks.md`, con el cuidado de que es del constructor. Mis corridas son el mismo módulo contra Postgres real, desde Windows.
- **Ctrl-C**: lo provoqué con un doble de `time.sleep`, no con una señal real, porque en Windows no pude mandarla a un proceso aislado.
- **Ediciones por SQL**: las hice como superusuario y con `session_replication_role = replica`. Prueban la comparación, no que cada estado se alcance desde la API.
- **`activo` y `PATCH /complejos/{id}` desde la API**: por lectura de `CLAUDE.md`, sin ejecutarlos.
- **Las causas de F2**: `semilla.py` y `crear_edificio` por lectura; el código y el mensaje, ejecutados.

## Chequeos no ejecutados

- **Suite completa**: por instrucción del brief. El orquestador la corre después.
- **`test_ejemplo_casos_de_uso.py` entero sobre la revisión**: reuso la corrida del constructor de 17:32 a 17:43. Corrí 6 de los 208 en limpio, más los de los mutantes.
- **`ruff` y `mypy`**: reuso los de 17:44 a 17:45, porque no cambió ningún archivo que cubran. No agregué código al repo; mis tests rojos viven afuera y no pasaron por `ruff` ni `mypy` (L-005): no se entregan así.
- **Stack con `-p proptech-c27`**: no lo levanté, por memoria. Usé un Postgres suelto con ese prefijo.
- **Base lenta (L-001)**: fuera del change por `proposal.md`. Sí la probé bloqueada y con `lock_timeout`.
- **Linux**: `test_fronteras_de_modulos.py`, S1 a S4.
- **`infra/ci/humo.sh`**: no lo corrí. Lo revisé por `git grep`.
- **`alta_inicial.py`**: fuera del change.
- **No hubo cortes por memoria**: el mínimo que medí fue 1173 MB libres, a las 18:51.

## Integridad de la entrega

No reparé nada ni dejé cambios en el repo. Mi único archivo nuevo es este informe. No hubo commit ni push.

```
$ date; git diff | sha256sum; sha256sum backend/tests/unitarios/test_puntos_de_entrada_prohibidos.py     # 2026-10-31 18:59:21
22bb0402eb35deb1fd38d49c209ddfe77d1a8d5b1522fce7ef9af0e199373d41 *-
af17cd1fdd72c17d4e6a253ad3cf8087661102374316bd014396042ecb0871a2 *backend/tests/unitarios/test_puntos_de_entrada_prohibidos.py

$ sha256sum <ejemplo.py, configuracion.py y base_de_datos.py>       # iguales a los de apply-2-constructor.md
4de87667144c05ca60a388c3913ecd1c5dc8c6bc964fa26ff14a71b1781a2267 *backend/src/proptech_core/complejos/aplicacion/ejemplo.py
46a3a499ba0472f5efba33820e9bb15513e8588931b86bf9f88ed8401958e69e *backend/src/proptech_core/compartido/configuracion.py
1ff9517dc5bae1e130c240a4b5d152132a01aa03330d84d8e7ca6fbdbbab8756 *backend/src/proptech_core/compartido/base_de_datos.py

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

$ docker ps -a | rg c27; docker volume ls | rg c27; docker network ls | rg c27; docker ps -a --filter label=org.testcontainers=true
(sin líneas)
```

- **`proptech`**: sus ocho contenedores siguen detenidos, como los encontré. No lo pisé ni toqué sus volúmenes. Hay 11 volúmenes antes y después.
- **Mutantes**: sólo sobre la copia de mi directorio temporal, y el `sha256sum` de arriba muestra que ningún archivo de producción cambió. Es una garantía contra el hash del constructor, no contra un commit (L-013).
- **Sin leer ni imprimir**: `infra/.env`, `infra/.env.example`, `docker compose config`.
