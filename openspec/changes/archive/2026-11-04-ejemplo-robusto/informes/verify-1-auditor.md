# Auditor · verify · intento 1 · ejemplo-robusto (C-27, 3f, LOW)

- **Rol**: auditor final, subagente nativo `role-auditor`. Sin sustitución.
- **Executor declarado**: Claude Opus 5.5 (declaración del entorno). **Familia**: Claude, la misma del orquestador (plan y revisión del plan), de los tres constructores y del rompedor. El proyecto no declara `## Role executors`.
- **Fecha**: 03/11/2026, de 21:20 a 21:35 aproximadamente (-03:00).
- **Revisión auditada**: base `9649471` sin commits; `git diff | sha256sum` `6dd4630f9af6d83dd1ba09a92378ad548faaeae86055b2707599f650548ba5d3`; `backend/tests/unitarios/test_puntos_de_entrada_prohibidos.py` sin trackear en `97fee65ceaa3d7afbae5570126c2c9a152799c000726933715c1ecf7afebe29b`. Recomprobados por mí al empezar y al terminar (21:25:54): iguales.
- **Veredicto**: **BLOQUEANTES** (al final). No encontré defectos de código; los dos bloqueantes son de evidencia que falta sobre la revisión entregada.

## Fuentes leídas

- **Artefactos del change**: `proposal.md`, `design.md` (D1 a D10 y Risks), `specs/datos-semilla/spec.md`, `tasks.md` entero (`## Estado del flujo` y la evidencia de los grupos 0 a 9), `informes/LEEME.md`.
- **Informes originales, todos completos**: `propose-1-plan-reviewer.md`, `propose-2-plan-reviewer.md`, `propose-3-plan-reviewer.md`, `apply-1-constructor.md`, `apply-2-constructor.md`, `apply-3-constructor.md`, `verify-1-breaker.md`.
- **Código**: `git diff` entero de `README.md`, `compartido/base_de_datos.py`, `compartido/configuracion.py`, `complejos/aplicacion/ejemplo.py` y `tests/integracion/test_arranque_tablas_protegidas.py`; `complejos/aplicacion/errores.py` (clases); `ejemplo.py` de `9649471` (`_main`, por `git show`); en `configuracion.py`, las líneas de `_LectorDeApp` y `_LectorDelEjemplo`.
- **Tests**: `test_ejemplo_casos_de_uso.py:1555-1670` y `:2330-2604` (los del grupo 9); `tests/infra/test_readme_variables.py:1-150` (cómo lee el README); `tests/unitarios/acceso/test_vocabulario_vigente.py:1-30` (su patrón).
- **Base de conocimiento**: `knowledge-base/15_lecciones.md` (lista de títulos L-001 a L-067, 67 lecciones, y el texto de L-013, L-025, L-041, L-055, L-061, L-064 y L-067); D-112 de `knowledge-base/09_decisiones_y_supuestos.md:1999-2018`.
- **Memoria del proyecto**: los artefactos del change y la lista de `openspec/changes/archive/` (17 changes; ninguno es `ejemplo-robusto`; el origen de esta deuda es `2026-10-24-acceso-de-desarrollo`). **Engram: no lo usé.** Tampoco `obsidian.md`.
- **Sin leer**: `infra/.env`, `infra/.env.example`, `.git/informes-*`. Un `rg -l` sobre `infra/` listó `infra/.env.example` como archivo que coincide con `aplicacion\.ejemplo`; no se mostró ni leí su contenido.

## Contaminación por otros informes

- Leí todos los informes antes de hacer mis comprobaciones. Mis corridas del comando real repiten casos que eligió el rompedor (F1, O4, O1): confirman la corrección sobre la revisión entregada, pero la selección no es independiente.
- Comparto familia y modelo con todos los roles del change. Mi independencia es de contexto (no construí ni rompí nada), no de proveedor (L-025).
- No busqué conclusiones de otros revisores en ninguna memoria.

## EVIDENCIA

Todo desde `backend/` con `export PATH="$HOME/.local/bin:$PATH"` y `uv run`, en Windows, sobre la revisión del encabezado. **No ejecuté ningún test.**

| Hora | Comando | Resultado |
|---|---|---|
| 21:20 | `git rev-parse HEAD`; `git diff \| sha256sum`; `sha256sum` del test sin trackear | `9649471...`, `6dd4630f...`, `97fee65c...`: coinciden con el brief y con `apply-3-constructor.md` |
| 21:20 | `sha256sum` de los seis archivos trackeados del change y de `infra/respaldos/*.sh` | Iguales a "Estado final" de `apply-3-constructor.md`. `configuracion.py` `46a3a499...`, `base_de_datos.py` `1ff9517d...` y `test_arranque_tablas_protegidas.py` `f9521fd9...` son además iguales a los que verificó el rompedor sobre `22bb0402` |
| 21:20 | `git diff --ignore-cr-at-eol --stat -- infra/` | Vacío: `infra/respaldos/*.sh` difieren sólo en el fin de línea |
| 21:20 | `git diff --name-only \| rg "acceso\|permisos\|cuenta_corriente\|migraciones"` | Sin coincidencias (código 1) |
| 21:22:39 a 21:23:05 | `uv run pytest --collect-only -q -p no:cacheprovider` sobre los cuatro archivos del change, cada uno y el repo entero | `322 tests collected`; por archivo `241`, `12`, `66`, `3`; repo entero `4934 tests collected in 4.86s` |
| 21:23:52 a 21:24:11 | Comando real `uv run --project backend python -m proptech_core.complejos.aplicacion.ejemplo ...` desde mi scratchpad, sin `REDIS_HOST` ni `REDIS_PASSWORD`, base en `127.0.0.1:1`, contraseña inventada | Ver el bloque de abajo |
| 21:24 a 21:25 | `rg -i` con el patrón de `test_vocabulario_vigente.py` sobre los seis archivos de código y test del change | Sin coincidencias (código 1). Control: `11_glosario.md` da 5 |
| 21:24 a 21:25 | `rg -n "^#{1,3} " README.md` | La tabla de códigos está en `### Entrar con el edificio de ejemplo` (línea 93), dentro de `## Cómo levantarlo`; `## Variables de entorno` empieza en la 184, y `test_readme_variables.py` sólo parsea esa sección |
| 21:24 a 21:25 | `git show 9649471:.../ejemplo.py \| rg "parse_known_args\|parser.error\|PROPTECH_ENTORNO"` | `:432` `parse_known_args` y `:434` `parser.error` van antes de la guarda (`:436`): O1 ya existía antes del change |
| 21:24 a 21:25 | `rg "^class " complejos/aplicacion/errores.py` | `Conflicto(Exception)` y `EntradaInvalida(ValueError)`: `Conflicto` no cae en el `except EntradaInvalida` y sigue en 9, como dice D10 |
| 21:24 a 21:25 | `rg "crear_engine\(\|Configuracion\("` en `backend/src` | API (`app.py:65`, `:90`), worker (`ajustes.py:149`, `:197`), `salud.py:160` y `alta_inicial.py:159-160` siguen con `Configuracion()` sin argumentos; `ejemplo.py:586` usa `ConfiguracionDelEjemplo` |
| 21:25:54 | Docker: contenedores, volúmenes, redes e imágenes con `c27`; contenedores de testcontainers. Hashes otra vez | Ninguno; 0. `6dd4630f...` y `97fee65c...` |

**Comando real** (salida recortada; los acentos rotos son de la consola de Windows, no del comando):

```
dev --semilla e (no existe)            rc=3 | no se puede leer el archivo: <semilla>
dev --semilla s (version 2)            rc=3 | semilla inválida: version: Input should be 1 edificio: Field required unidades: Field required grupos: Field required
dev --semilla=                         rc=2 | --semilla no puede estar vacío; no se escribió nada
dev --semilla user_Aud1tor             rc=3 | no se puede leer el archivo: <semilla>
dev id como subcomando                 rc=2 | usage: ... [-h] {cargar} ... argumentos no reconocidos; no se escribió nada
dev semilla por defecto, base cerrada  rc=5 | la base no está disponible: no se pudo conectar o se cortó la conexión
prod cargar                            rc=1 | este comando es sólo para desarrollo: no corre sin PROPTECH_ENTORNO=desarrollo; no se escribió nada
prod cargar --foo (O1)                 rc=2 | usage: ... argumentos no reconocidos; no se escribió nada
prod --help (O1)                       rc=0 | usage: ... cargar [-h] [--semilla SEMILLA] [--clerk-usuario CLERK_USUARIO] ...
```

Ninguna salida trae `Traceback`, la contraseña inventada ni el id. La corrida con la semilla por defecto llega al 5 sin variables de Redis: la configuración se lee sin ellas (QA-3).

**Por qué no corrí tests**: Giuliano pidió no correrlos salvo necesidad. Los casos que quise confirmar sobre la revisión entregada (F1, O4, la guarda, O1 y Redis) se ven por el comando real sin base y sin Docker, en segundos. El vocabulario y el README, que no entraron en la corrida focalizada final, los resolví por lectura y `rg`, con control. Lo que sigue sin evidencia (la suite entera y una vuelta de rompedor) no lo suple un test suelto mío.

## Cobertura afirmada contra lo examinado

| Afirmación | Quién | Lo que examiné | Resultado |
|---|---|---|---|
| 322 tests en los cuatro archivos, 241 en el del comando (+33 del grupo 9) | `apply-3-constructor.md` | Colecta propia | **Cierto**: 322 y 241. El repo pasa de 4901 (verify 1) a 4934, +33 |
| Ningún archivo de `acceso`, permisos, `cuenta_corriente` ni migraciones | Todos los informes | `git diff --name-only` | **Cierto**. `ejemplo.py` importa `listar_personal` de `acceso.aplicacion` sin modificarlo (D3) |
| `infra/respaldos/*.sh` sólo por fin de línea | Brief y constructores | `--ignore-cr-at-eol` | **Cierto** |
| Sin mutantes entregados | `apply-3-constructor.md` | Hashes: tres archivos iguales a los de `22bb0402`; diff completo de `ejemplo.py` leído | **Cierto por lectura** en las garantías de F1 a F9 (consultas de unidades y grupos con `complejo_id`, `any(... == "super_admin")`; `intentos` no aparece en el diff porque no cambió). No hay copia contra la que hacer `cmp` (L-013) |
| F1 y O4 corregidos | `apply-3-constructor.md`, 9.1 y 9.3 | Comando real | **Cierto** sobre `6dd4630f` |
| F2: `pisos: 0` da 3 | `apply-3-constructor.md`, 8.2 acotada | Lectura del diff y del test `:2427-2450`; no lo corrí (necesita base) | Correcto por lectura; la evidencia ejecutada es sólo del constructor |
| F3: Ctrl-C da 130 | `apply-3-constructor.md`, 9.3 | Lectura de `_main` y de los tests `:2453-2507` | Correcto por lectura; con un doble, no con una señal real |
| F5 a F9 vigilados | `apply-3-constructor.md`, 9.4 | Lectura del test de F6 (`esperas == [0.1] * 50`) | Los tests pueden dar rojo; los mutantes corrieron con su selección, no con el archivo entero |
| RED antes de producción en 9.1 a 9.3 | `apply-3-constructor.md` | La reversión y su coincidencia con las salidas de `verify-1-breaker.md` | **Es RED contra la producción anterior reconstruida**, no RED antes de escribir producción. Juicio abajo |
| Lint, formato y `mypy --platform linux` limpios | `apply-3-constructor.md`, 21:02 a 21:03 | No los repetí: cubren la revisión entregada | Vigentes |
| Sin regresiones fuera de los archivos focalizados | Nadie lo afirma sobre `6dd4630f` | Vocabulario y README por lectura; consumidores de `Configuracion` y `crear_engine` por `rg` | **Sin evidencia de suite**: la última completa es de `769b969e` (30/10), vencida |
| Las correcciones del grupo 9 no rompen otra cosa | `apply-3-constructor.md`, SUPOSICIÓN: "las miré yo, que también las probé" | Nadie las atacó | **Sin rompedor** sobre el delta `22bb0402` a `6dd4630f` |

## Frescura de cada evidencia contra `6dd4630f`

| Evidencia | Revisión | Estado |
|---|---|---|
| Línea de base 0.1 | `9649471` | Vigente como línea de base |
| RED, GREEN y mutantes de los grupos 1 a 6 | `9649471` más los árboles `1946d4ce` y `22bb0402` | GREEN renovado por la corrida focalizada final (`3 failed, 319 passed`, las 3 de Windows). Los mutantes no se repitieron sobre `6dd4630f`; las ramas que vigilan no cambiaron en el grupo 9 |
| RED y GREEN del grupo 9 | árbol `bb902f98`; entregado `6dd4630f` | Vigente: entre los dos sólo cambió el comentario de `ejemplo.py:91-95` |
| Corrida focalizada final, 322 tests | `6dd4630f`, 21:03 a 21:09 | **Vigente** |
| `ruff check`, `ruff format --check`, `mypy --platform linux` | `6dd4630f`, 21:02 a 21:03 | **Vigentes**. `mypy` de Windows no corrió (2 errores previos de `test_respaldos.py:554`) |
| 8.2, `pisos: 0` y `--semilla=` | `6dd4630f` | Vigente |
| 8.2, códigos 4, 5, 6, 7, mensaje por campo y Redis | `22bb0402` | **Vencida para el comando real**; esos caminos están en la focalizada vigente |
| Rompedor, verify 1 | `22bb0402` | **Desactualizado** para el grupo 9 |
| Suite completa | `769b969e` (30/10) | **Vencida**; la de apply 1 de las 21:40 y la de apply 2 se cortaron sin resultado |
| CI del PR (8.1) | No existe | **Falta** |
| Mis comprobaciones | `6dd4630f`, 21:20 a 21:26 | Vigentes |

## JUICIO

- **Autor**: auditor. **Comparación**: plan revisado, diff entregado y los siete informes, contra el spec, las decisiones fechadas y las lecciones.

**Código.** Confianza alta en que cumple el spec en lo que examiné: la tabla de códigos está en `_ejecutar` y `_main` en el orden de D4 y D10; el edificio se identifica por nombre (D2); la persona se lee con `listar_personal` (D3); la configuración del comando no exige Redis y la de la API y el worker sigue igual (D5); un mensaje por campo (D9). No encontré defectos nuevos.

**Duplicación.** No reescribe nada que ya exista: `_LectorDelEjemplo` hereda de `_LectorDeAppSoloPostgres` y `ConfiguracionDelEjemplo` usa `_cargar`, en lugar de copiar la lectura de credenciales. Sí duplica, a propósito (D5), los cuatro campos del pool, su validador ASCII y el chequeo del archivo de parámetros de `_LectorDeApp`. Está declarado como gemelo (L-009) y lo vigilan los mismos valores en los dos lectores (4.2 y F5). No bloquea; queda como deuda.

**Código crítico.** Nadie tocó `acceso`, la matriz de permisos, `cuenta_corriente` ni migraciones. `configuracion.py` y `base_de_datos.py` son compartidos con la API y el worker, pero el cambio estaba pedido y revisado (D5, 4.3), y sus tests de arranque y configuración corrieron sobre los mismos hashes (`156 passed`, rompedor, 31/10, 18:52). LOW se sostiene.

**Hueco 1: sin rompedor después de las correcciones. Bloqueante (B1).** La regla del flujo dice, para cualquier nivel, que una falla reproducida reabre la vuelta y que el código corregido pasa por los tests pertinentes y otra vez por el rompedor. El rompedor reprodujo F1 a F4 y dejó cinco mutantes sobrevivientes; el grupo 9 cambió producción en cinco lugares de `ejemplo.py` y sumó 33 tests. La decisión de Giuliano del 03/11/2026 está registrada con fecha y texto, y la respeto en lo que pide (no corrí tests ni la suite), pero no fabrica esa revisión: `informes/LEEME.md` la lista como faltante y el informe del rompedor está desactualizado para la revisión entregada. La evidencia del constructor es buena (cada reversión reproduce la salida que pegó el rompedor, y mis corridas confirman F1 y O4), pero es la del autor mirando su propia corrección (L-025). Mis comprobaciones son de auditor, no una vuelta de ataque. No puedo dar APROBADO con un informe requerido desactualizado.

**Hueco 2: sin suite completa sobre la revisión entregada. Bloqueante (B2).** 8.1 está sin marcar. Desde la última suite completa cambiaron `configuracion.py` (el refactor de `_cargar`, que usan las cinco clases de configuración), `ejemplo.py` y los tests. L-055 y L-064 dicen que el cierre exige la suite entera sobre el SHA final, porque los tests estructurales ven lo que no ve una selección: H-6 de este mismo change sólo apareció así. Que el juez sea el CI del PR es una decisión válida (D-110, Risks del design), pero el CI no existe todavía (L-042: sin PR no corre). Decidir quién juzga la suite no es tener el resultado de la suite.

**Hueco 3: RED sobre código ya escrito. No bloquea.** El agente detenido el 01/11 escribió producción y tests sin evidencia; el segundo agente la trató como no probada y obtuvo el RED revirtiendo cada corrección a la forma que describe `verify-1-breaker.md`, con `cmp` al restaurar. Es lo que L-013 permite cuando el código existe, y pesa más que un mutante cualquiera porque cada reversión reprodujo la salida exacta del rompedor (`no s<semilla> pu<semilla>d...`, `error inesperado: EntradaInvalida`, el 5 de `--semilla=`). No es "RED antes de producción" en sentido estricto (L-061), y así queda dicho. Confianza media en que la reversión sea idéntica al código de `22bb0402`, por el mismo motivo que declara el constructor.

**Hueco 4: O1. No bloquea.** Que un error de uso fuera de desarrollo dé 2 y no 1 no lo introdujo este change: en `9649471` el `parser.error` ya iba antes de la guarda, con el 2 de `argparse`. El change lo documenta (spec, docstring de `_ejecutar`, README). Se cumple el propósito de D-112 (no se conecta ni escribe nada; lo reproduje con `cargar --foo` y `--help` en `produccion`), pero D-112 dice "sale con código 1, lo dice": la lectura de que un error de uso no es correr el comando es del orquestador. Como D-112 no se edita, la decisión de cierre tiene que nombrar esa interpretación para que Juani, que la firmó, la ratifique o la cambie.

**Hueco 5: independencia. No bloquea este change, pero se declara.** Todos los roles y yo somos Claude Opus 5.5. L-025 pide que rompedor y auditor sean de otra familia que el constructor; el proyecto no declara `## Role executors` y la regla global no deja afirmar independencia porque cambien los nombres de los agentes. Hubo independencia de contexto (el rompedor atacó antes de leer los informes; yo no construí ni rompí), no de proveedor.

**Hueco 6: sospechas y deuda.** S1 a S4 siguen sin reproducir y no las promuevo. O2 y `alta_inicial.py` son deuda bien justificada: O2 queda fuera del spec vigente (que enumera unidades, grupos y estado de migración) y `alta_inicial.py` está en `acceso`, que el change no podía tocar. O3 quedó aceptado y escrito en D4.

**Intentos.** Según `tasks.md`, verify 1 del rompedor fue el primer intento fallido de esta etapa. Este veredicto sería el segundo resultado no aprobado de verify; la cuenta la lleva el orquestador. Con un tercero, el flujo exige frenar y ofrecerle a Giuliano las tres opciones (alcance nuevo aprobado, deuda justificada aceptada o parar el change), con su respuesta escrita en `tasks.md`.

**Tensión que tiene que resolver Giuliano.** B2 pide el CI, y el CI pide push y PR (L-042). La regla global de publicación pide aprobación del auditor antes de cualquier push. Tal como están escritas no caben las dos: o Giuliano autoriza por escrito un push de la rama y un PR sin merge sólo para obtener el CI (como en los PR #3 y #4, revisados antes del merge), o pide la suite completa en local. Yo no elijo por él.

## SUPOSICIÓN

- **Linux**: no corrí nada en Linux. El 130 por una señal real, S1 a S4 y las tres fallas de `test_fronteras_de_modulos.py` en Linux quedan como las dejaron los informes.
- **Sin tests propios**: F2, F3 y F5 a F9 los juzgo por lectura del diff y de los tests, más la evidencia del constructor. No los ejecuté.
- **Mutantes de los grupos 1 a 6**: no se repitieron sobre la revisión entregada. Supongo que siguen valiendo porque las ramas que vigilan no cambiaron en el grupo 9; no lo comprobé corriéndolos.
- **`test_puntos_de_entrada_prohibidos.py`**: su hash cambió de `af17cd1f` a `97fee65c` (9.5, docstring). No tengo la versión anterior para comparar; sus 3 tests entraron en la corrida focalizada final.
- **Procesos**: `tasklist` muestra dos `python3.13.exe` vivos (PID 9480 y 15236), compatibles con el `python3` colgado que declara `apply-3-constructor.md`. No son míos y no los toqué.

## Chequeos no ejecutados

- Suite completa, por el pedido de Giuliano y el límite del brief.
- Ningún test, ni focalizado: ver EVIDENCIA.
- `mypy` de Windows, `ruff` y formato: reuso los de 21:02 a 21:03, que cubren la revisión entregada.
- El comando real contra una base: no levanté Postgres. Uso 8.2 del constructor.
- `test_readme_variables.py` y `test_vocabulario_vigente.py`: resueltos por lectura y `rg`, sin correrlos (el primero lee `infra/.env.example`).

## Integridad

No modifiqué código, tests ni artefactos: mi único archivo nuevo en el repo es este informe. Un archivo `s` de prueba quedó en mi scratchpad, fuera del repo. Sin commit ni push. Nada con `c27` en Docker, y no toqué el proyecto `proptech`.

## VEREDICTO

**BLOQUEANTES**

| # | Bloqueante | Evidencia | Responsable | Qué lo levanta |
|---|---|---|---|---|
| B1 | El grupo 9 (correcciones de F1 a F9) no pasó por el rompedor. `verify-1-breaker.md` es de `22bb0402`, desactualizado para `6dd4630f`, y la regla del flujo pide otra vuelta después de una falla reproducida | `informes/LEEME.md`, "Faltan"; hashes de `ejemplo.py` (`4de87667` a `32648461`) y de `test_ejemplo_casos_de_uso.py` (`5b18ea14` a `04201ab2`) | Orquestador, que despacha al rompedor; si encuentra algo, constructor por TDD | `informes/verify-2-breaker.md` sobre la revisión entregada. Alcanza una vuelta acotada al delta `22bb0402` a `6dd4630f` (las cinco correcciones de `ejemplo.py`, los 33 tests y los textos de 9.5), más sus consumidores |
| B2 | No hay suite completa sobre la revisión entregada y 8.1 está sin marcar | `tasks.md` 8.1; última completa en `769b969e` (30/10), vencida; L-055 y L-064 | Constructor u orquestador, con la decisión previa de Giuliano sobre cómo obtenerla | El CI del PR leído por run sobre el SHA del commit (L-042), o la suite local entera si Giuliano la pide, con las fallas separadas contra `apply-1-constructor.md:121-133` |

Cualquier corrección que salga de B1 invalida la corrida focalizada, el lint y 8.2 en lo afectado, y hay que repetirlos antes de un nuevo veredicto. Con B1 y B2 resueltos sin hallazgos, el nuevo veredicto puede ser una lectura liviana de esas dos evidencias.

No encontré defectos de código. No hace falta ni existe aprobación humana HIGH o CRITICAL: el change es LOW.

### DEUDA

| # | Deuda | Origen | Destino |
|---|---|---|---|
| DE-1 | La comparación no mira `pisos`, `subsuelos`, la ubicación ni `activo` de un grupo (O2) | `verify-1-breaker.md`, O2; `proposal.md`, "Fuera de este cambio" | Próximo change que toque `ejemplo.py`; anotarla en la ficha 3f de `12_fichas_de_changes.md` |
| DE-2 | `acceso/aplicacion/alta_inicial.py`, el gemelo: traceback y exigencia de Redis (L-009) | `propose-1-plan-reviewer.md`, PR-9 | Primer change que toque `alta_inicial.py`, con su propia clasificación (está en `acceso`) |
| DE-3 | O1: un error de uso fuera de desarrollo da 2. Comportamiento previo al change, que el change documenta como interpretación de D-112 | `propose-3-plan-reviewer.md`; `9649471:ejemplo.py:432-436` | Decisión de cierre del change (la próxima libre es D-145), que lo nombre como interpretación para que Juani la ratifique o la cambie |
| DE-4 | S1 (límite de conexión por dirección), S2 (`print` después del commit con la salida cerrada) y S4 (parámetros sin permiso de lectura), sin reproducir | `verify-1-breaker.md` | Próximo change que toque `ejemplo.py`, con una corrida en Linux |
| DE-5 | S3: `--semilla` con un archivo especial puede agotar la memoria antes del tope de 1 MiB | `verify-1-breaker.md`, S3 | Primer change que toque `compartido/cargador_yaml.py` |
| DE-6 | `Conflicto` sigue en el 9, sin reproducir; base lenta sin `statement_timeout` (L-001), declarada no cubierta | D10; `proposal.md` | Próximo change que toque `ejemplo.py` |
| DE-7 | Los validadores del pool y del archivo de parámetros viven en dos lectores (`_LectorDeApp` y `_LectorDelEjemplo`) | D5 | Próximo change que toque `compartido/configuracion.py`: un solo lugar para los dos |
| DE-8 | Todos los roles del change son de la familia Claude; el proyecto no declara `## Role executors` (L-025) | Este informe, hueco 5 | C-28 `revisiones-independientes` |
| DE-9 | Fallas de Windows que D-110 no nombra (separador de ruta en `test_fronteras_de_modulos.py`, `test_umbral_cero` y las familias de `apply-1-constructor.md:123-133`); `mypy` de Windows con 2 errores en `test_respaldos.py:554` | `apply-1-constructor.md`, H-7 | Registrar al cierre en la ficha 3b-bis; la parte de `respaldos`, a C-24 `respaldos-2` |
| DE-10 | CRLF de `infra/respaldos/*.sh` en Windows, sin `.gitattributes` | `proposal.md`, "Fuera de este cambio"; `propose-2-plan-reviewer.md` | C-24 `respaldos-2`, que ya agrega el `.gitattributes` |

### LECCIONES

Propuestas para `knowledge-base/15_lecciones.md` (sólo agregar), con el número que corresponda al cerrar:

- **L-068 · Un constructor detenido deja código sin evidencia: el siguiente lo prueba revirtiendo a la forma que describió el rompedor.** Origen: C-27, apply 3 (03/11/2026). Qué pasó: el agente cortado el 01/11 dejó escritas la producción y los tests del grupo 9 sin ningún RED; el agente nuevo no dio nada por probado, obtuvo cada rojo volviendo la producción a la forma que pegó `verify-1-breaker.md` y comparó la salida con la del rompedor. Regla: el código que deja un agente detenido es código sin evidencia; el RED se obtiene revirtiendo a la versión anterior documentada, y vale si reproduce la salida que ya había registrado otro rol. Se declara como "RED contra la producción anterior", no como RED antes de producción (L-061). Aplica a constructor y auditor.
- **L-069 · Para ocultar un valor tipeado en un mensaje se compara el mensaje entero, nunca se reemplaza la subcadena.** Origen: C-27, F1 de verify 1 (31/10/2026). Qué pasó: `str.replace(ruta, "<semilla>")` sobre todo el mensaje convirtió `--semilla e` en `no s<semilla> pu<semilla>d<semilla>...` y borró el nombre del campo cuando el archivo se llamaba `unidades`. Regla: si un texto de error trae un valor del usuario que no debe salir, se reconoce el mensaje conocido por igualdad y se reescribe entero; un reemplazo de subcadena falla con valores cortos o que son palabras del propio mensaje (L-007). Aplica a constructor y rompedor.
- **L-070 · Ahorrar la segunda vuelta del rompedor o la suite de cierre no las reemplaza: se acotan, no se saltean.** Origen: C-27, decisión de Giuliano del 03/11/2026 y este veredicto. Qué pasó: para ahorrar tiempo y memoria se pidió no repetir el rompedor ni la suite; el change llegó al auditor con las correcciones sin atacar y sin regresiones medidas, y no pudo aprobarse. Regla: cuando la corrección es chica, la vuelta del rompedor se acota al delta y a sus consumidores, y la suite se delega al CI con el PR armado antes de pedir el veredicto. Aplica a orquestador y auditor.
