# Constructor · apply · intento 3 · ejemplo-robusto (C-27)

- **Rol**: constructor, subagente nativo `role-constructor`, segundo agente del intento 3. El primero quedó detenido el 01/11/2026 y no se pudo retomar. Sin sustitución.
- **Executor declarado**: Claude Opus 5.5. **Familia**: Claude, la misma del rompedor de verify 1 y del orquestador.
- **Fecha**: 03/11/2026, de 20:40 a 21:20 (-03:00).
- **Revisión de partida**: base `9649471` sin commits, `git diff | sha256sum` `bb902f98039cd106d19763cab4d61b944313f4aba693b437e4d4ea6a11599dbe`, `test_puntos_de_entrada_prohibidos.py` en `97fee65c...`. Coincidían con el brief.
- **Revisión entregada**: base `9649471` sin commits, `git diff | sha256sum` `6dd4630f9af6d83dd1ba09a92378ad548faaeae86055b2707599f650548ba5d3`, `test_puntos_de_entrada_prohibidos.py` en `97fee65ceaa3d7afbae5570126c2c9a152799c000726933715c1ecf7afebe29b`. Sin commit ni push.
- **Resultado**: 9.1 a 9.5 marcadas con evidencia propia; 8.2 marcada, acotada a `pisos: 0` y `--semilla=` como pidió Giuliano. 8.1 sigue sin marcar. El único cambio de archivo del repo que hice es el comentario de `ejemplo.py:91-95` (9.5); el resto del código del grupo 9 lo había escrito el agente anterior, y acá lo probé.

## Fuentes leídas

- **Lecciones**: `knowledge-base/15_lecciones.md`. Leí la lista completa de títulos (L-001 a L-067) y el texto de L-013 y L-066 a L-067; el resto, por título y por las citas de `tasks.md`.
- `openspec/changes/ejemplo-robusto/`: `tasks.md` (estado del flujo y todos los grupos), `informes/verify-1-breaker.md` completo, `informes/propose-3-plan-reviewer.md` completo, `design.md` (D4 a D10 y Risks), `specs/datos-semilla/spec.md` (la tabla y los escenarios nuevos), `informes/LEEME.md` y el encabezado de `informes/apply-2-constructor.md`.
- **Código**: `complejos/aplicacion/ejemplo.py` entero; `compartido/configuracion.py:265-290` y `:400-445`; `complejos/aplicacion/errores.py:1-45`.
- **Tests**: `test_ejemplo_casos_de_uso.py:795-1000`, `:1130-1175`, `:1296-1430`, `:1500-1670` y `:2310-2603`; `tests/conftest.py:1-140`; `tests/integracion/conftest.py:30-50`; `tests/integracion/_edificios.py:24-82`; `test_puntos_de_entrada_prohibidos.py` entero; `README.md:104-141`.
- **No existían**: los tests rojos del rompedor (`...\19e1c5b0-...\scratchpad\rompedor\rojos\test_rompedor_rojos.py`) y cualquier copia del agente anterior. Mi scratchpad estaba vacío.
- **Sin leer**: `infra/.env`, `infra/.env.example`, `.git/informes-*`. No imprimí `docker compose config`.

## Contaminación por otros informes

- Trabajé desde el informe del rompedor y la disposición del plan, como manda el brief: los casos, los mutantes F5 a F9 y la forma del código previo salen de ahí. No es una mirada independiente.
- Los tests y la producción del grupo 9 ya estaban escritos por el agente anterior. Los leí y los usé; no los escribí. Lo que pongo en EVIDENCIA es lo que corrí yo, no lo que él haya corrido.
- Sin Engram: no lo usé.

## Lo que el corte anterior invalidó, y qué di por válido

- **Ninguna corrida del agente detenido cuenta.** No dejó evidencia, y la que pudiera haber tenido no la vi.
- **Mutantes que pudieran haber quedado**: por hash, `configuracion.py` (`46a3a499...`), `base_de_datos.py` (`1ff9517d...`) y `test_arranque_tablas_protegidas.py` (`f9521fd9...`) son iguales a los que verificó el rompedor sobre `22bb0402`, así que ahí no hay nada aplicado. `ejemplo.py` cambió (`24d1ef70...`) y lo leí entero: cada garantía que atacaron verify 1 y los grupos 1 a 5 está en su forma correcta (`intentos: int = 50`, la consulta de unidades y la de grupos con `complejo_id=:id`, `any(... rol == "super_admin")`, las ramas de cada campo). Es una revisión por lectura, no un `cmp` contra una copia anterior, que no existe (L-013).
- **Lo que di por válido después de probarlo**: la producción de 9.1 a 9.3 y los tests de 9.1 a 9.4. Lo validó el RED de cada tarea, que obtuve revirtiendo cada corrección a la forma que describe verify 1, más un mutante en cada aserción que nacía verde. Cada reversión reprodujo la salida que pegó el rompedor (`no s<semilla> pu<semilla>d...`, `error inesperado: EntradaInvalida`, `error inesperado: NotImplementedError`, el código 5 de `--semilla=`).
- **Los textos de 9.5** (README, docstring de `_ejecutar`, docstring del test de la guarda) los di por buenos sólo después de leerlos contra el comportamiento. El comentario de `ejemplo.py:91-93` no era cierto del todo y lo corregí.

## EVIDENCIA

Todo en Windows, desde `backend/`, con `uv` y el `.venv` del repo. Comando base: `uv run pytest tests/integracion/test_ejemplo_casos_de_uso.py -k "<selección>" -q -p no:cacheprovider --tb=line --no-header`. Mutantes y reversiones con copia previa en mi scratchpad (`ejemplo.py` `24d1ef70...`, `configuracion.py` `46a3a499...`), aplicados con un guion que exige una sola coincidencia y respeta el CRLF, y restaurados con `cp` más `cmp`: cada uno terminó en `revertido contra copia: identico`. Logs en `C:\Users\espej\AppData\Local\Temp\claude\56b680c42cc5a2e7\19e1c5b0-3037-4aa8-9599-2cf049059770\scratchpad\`, que no viaja con el repo. El detalle por tarea, con las líneas de cada falla, está bajo 9.1 a 9.5 y 8 en `tasks.md`.

### Línea de base

| Hora | Qué | Resultado |
|---|---|---|
| 20:46:28 | Árbol al arrancar (`bb902f98...`), tests sin base de 9.1, 9.3 y F5 | `123 passed, 118 deselected` |

Docker Desktop estaba apagado. Lo encendí a las 20:51 para los tests con base y lo dejé encendido.

### 9.1 (F1)

| Hora | Corrida | Resultado |
|---|---|---|
| 20:47:59 | `R9.1`: el cuerpo de `_sin_la_ruta_del_archivo` vuelve al `replace` sobre el mensaje entero | `7 failed, 3 passed`. `[a]`, `[e]`, `[archivo]`, `[   ]` en `:1574`; archivo `s` en `:1584`; archivo `unidades` en `:1601`; `PROPTECH_PARAMETROS=e` en `:1614`. Verdes los 3 del id |
| 20:48:18 | GREEN | `10 passed, 231 deselected` |

### 9.2 (F2)

| Hora | Corrida | Resultado |
|---|---|---|
| 20:51:47 a 20:54:15 | **No cuentan**: con `PYTHONIOENCODING=utf-8`, que hereda el subproceso y rompe la decodificación del test | Mojibake en `:2447` |
| 20:54:30 | `R9.2a`: sin el `except EntradaInvalida` | `4 failed`: `:2368` `assert 9 == 3`; tres veces `:2446` `error inesperado: EntradaInvalida` |
| 20:57:13 | `R9.2b`: vuelve el `NotImplementedError` | `1 failed, 3 passed`: sólo `[confirmada]`, `:2446` `error inesperado: NotImplementedError` |
| 20:57:50 | `M9.2c`: el mensaje con `{error}`, que trae el `motivo` | `4 failed`: `:2370` con `pisos: valor-sembrado`; tres en `:2447` |
| 20:58:26 | GREEN | `4 passed, 237 deselected` |

Los tres casos del comando real comparan el mensaje entero y exigen `_filas_escritas == _SIN_ESCRITURAS`.

### 9.3 (F3 y O4)

| Hora | Corrida | Resultado |
|---|---|---|
| 20:48:49 | `R9.3a`: sin el `except KeyboardInterrupt` | `4 failed, 3 passed`: tres en `:2473` `_main dejó escapar KeyboardInterrupt`; el del proceso en `:2505` con `Traceback` |
| 20:49:00 | `R9.3b`: sin el chequeo de `--semilla` vacío | `2 failed`: `[con_igual]` y `[separado]` en `:1653`, `la base no está disponible`: se conectó con la semilla por defecto |
| 20:49:27 | `M9.3c`: el 130 dice "no se escribió nada" | `3 failed` en `:2478` |
| 20:49:38 | `M9.3d`: el chequeo de `--semilla` vacío antes de la guarda | `1 failed`: `test_la_semilla_vacia_fuera_de_desarrollo_termina_con_1` en `:1662` |
| 20:49:49 | GREEN | `7 passed, 234 deselected` |

### 9.4 (F5 a F9)

| Hora | Mutante | Resultado |
|---|---|---|
| 20:50:10 | `M9.4a` (F5, el del rompedor): `_LectorDelEjemplo` valida sólo `db_pool_size` | `6 failed, 100 passed`, los seis `[comando-...]` nuevos en `:1398` `DID NOT RAISE ConfiguracionInvalida` |
| 20:50:15 | `M9.4b` (F5, gemelo L-009): `_LectorDeApp` igual | Los mismos seis en `[api_y_worker-...]` |
| 20:50:22 | GREEN de F5 | `106 passed` |
| 20:59:25 | `M9.4c` (F6): `intentos: int = 1` | `test_el_comando_espera_de_verdad_antes_de_rendirse` en `:2584`, `assert [0.1] == [0.1, 0.1, ...]`. El de la espera por el proceso sigue verde |
| 20:59:48 | `M9.4d` (F7): `if not super_admin["asignaciones"]:` | Sólo `[asignacion_con_otro_rol]`, `:1007` `DID NOT RAISE EjemploDistinto` |
| 21:00:21 | `M9.4e` (F8): unidades de toda la administración | `:917` `falso 'el ejemplo cambió': unidades: faltan [], sobran ['9Z']` |
| 21:00:37 | `M9.4f` (F9): grupos de toda la administración | `:917` `grupos: faltan [], sobran ['solo_del_otro']` |
| 21:00:53 | GREEN de F6 a F9 | `7 passed, 234 deselected` |

### 9.5

Validación de contrato por lectura, sin comportamiento ejecutable: `README.md:130`, `:131` y `:138`; docstring de `_ejecutar`; docstring de `test_puntos_de_entrada_prohibidos.py`. Corregí `ejemplo.py:91-95`: decía que `_main` no deja escapar `KeyboardInterrupt` porque Python usa 1 para una excepción sin capturar. Eso vale para `Exception`; para Ctrl-C la razón es el traceback, y sale con 130.

### Chequeos sobre la revisión entregada (`6dd4630f...`)

| Hora | Comando | Resultado |
|---|---|---|
| 21:02:34 | `uv run ruff check .` | `All checks passed!` |
| 21:02:36 | `uv run ruff format --check .` | `405 files already formatted` |
| 21:03:04 | `uv run mypy --platform linux` | `Success: no issues found in 368 source files` |
| 21:03:24 a 21:09:41 | `uv run pytest tests/integracion/test_ejemplo_casos_de_uso.py tests/integracion/test_arranque_tablas_protegidas.py tests/unitarios/test_fronteras_de_modulos.py tests/unitarios/test_puntos_de_entrada_prohibidos.py -q -p no:cacheprovider --tb=short --no-header` | `3 failed, 319 passed, 1 warning in 373.39s`. Las 3 de `test_fronteras_de_modulos.py`, por el separador de ruta, las mismas de 0.1 |

### 8.2 acotada

Postgres suelto `proptech-c27-constructor` (`postgres:18.6-trixie`, `--memory=450m`, puerto en `127.0.0.1:55432`, contraseñas inventadas), migrado como `base_fresca`. El comando corre como `proptech_app`, sin Redis. Una primera corrida (21:10:24) **no cuenta**: mi guion escribió la semilla en cp1252 y dio `YAML mal formado`. La que vale, 21:14:03 a 21:14:27:

```
filas antes (administracion persona complejo unidad auditoria): 0 0 0 0 0
semilla con pisos: 0                     codigo: 3  la semilla o los parámetros no se pueden cargar: pisos; no se escribió nada
filas despues de pisos 0: 0 0 0 0 0
--semilla= (vacio)                       codigo: 2  --semilla no puede estar vacío; no se escribió nada
filas despues de --semilla=: 0 0 0 0 0
--semilla= sin PROPTECH_ENTORNO          codigo: 1  este comando es sólo para desarrollo: no corre sin PROPTECH_ENTORNO=desarrollo; no se escribió nada
control: semilla por defecto             codigo: 0  ejemplo cargado: 00000000-0000-4000-8000-0000000000e0
filas despues del control: 1 1 1 13 18
```

El control muestra que la base andaba: los ceros de arriba son reversión, no una base rota.

## Conteos propios

- `--collect-only`, por archivo: `test_ejemplo_casos_de_uso.py` **241**, `test_arranque_tablas_protegidas.py` **12**, `test_fronteras_de_modulos.py` **66**, `test_puntos_de_entrada_prohibidos.py` **3**. Suman 322, lo mismo que `3 failed + 319 passed` de la corrida final.
- `test_ejemplo_casos_de_uso.py` pasa de 208 (apply 2 y verify 1) a 241: **+33**. Cuadran así: F1, 8 (5 rutas, `s`, `unidades`, `PROPTECH_PARAMETROS=e`); F2, 4 (3 por el comando más `[rechazo_del_caso_de_uso]`); F3, 4 (3 de `_main` más el del proceso); O4, 3; F5, 12 (2 valores por 3 variables por 2 lectores); F6, 1; F7, 1. F8 y F9 no suman tests: endurecen `test_otro_edificio_con_otro_nombre_no_cambia_el_resultado` con `_sumar_unidad_y_grupo`.
- Corridas bajo reversión o mutante: 14 (más 3 que no cuentan por `PYTHONIOENCODING`). No cuentan como verde.
- Comando real contra el Postgres suelto: 4 corridas válidas, más 4 de la corrida que no cuenta.

## Estado final

```
$ git diff | sha256sum                       # 21:15
6dd4630f9af6d83dd1ba09a92378ad548faaeae86055b2707599f650548ba5d3 *-

$ sha256sum <archivos del change>
ad02bd63f7675bd95ce017f3843ff207016b2d34e6eb1bf104e8472827272b7e *README.md
1ff9517dc5bae1e130c240a4b5d152132a01aa03330d84d8e7ca6fbdbbab8756 *backend/src/proptech_core/compartido/base_de_datos.py
46a3a499ba0472f5efba33820e9bb15513e8588931b86bf9f88ed8401958e69e *backend/src/proptech_core/compartido/configuracion.py
32648461d798f397617101d6f119b8d82f512c25768f9cb7779b485de6ccfe64 *backend/src/proptech_core/complejos/aplicacion/ejemplo.py
f9521fd9a487701fa092d3f71d4acd028a234ee0c4ffb9d15794953e8bcfa602 *backend/tests/integracion/test_arranque_tablas_protegidas.py
04201ab2b6af0d567df6f41ccf57d950717f04e72e626d358d73df4a1ffa8988 *backend/tests/integracion/test_ejemplo_casos_de_uso.py
97fee65ceaa3d7afbae5570126c2c9a152799c000726933715c1ecf7afebe29b *backend/tests/unitarios/test_puntos_de_entrada_prohibidos.py

$ sha256sum <los que no se tocan, marcados por el fin de línea>   # iguales a los de apply 2
62a32f7f701c48a424a3673527c90ec45302d7f2dcb975c6776be4415dfe7c46 *infra/respaldos/respaldar.sh
6266eec41ccddfe9e7cc6454ee8be3a22766614d5cdfae0b20cc2d2e555ed262 *infra/respaldos/restaurar.sh
```

- **Respecto del árbol al arrancar** (`bb902f98...`), lo único que cambió en el repo es el comentario de `ejemplo.py:91-95`. `git diff --no-index` contra mi copia previa muestra sólo esas líneas.
- **Docker**: 0 contenedores, volúmenes, redes e imágenes con `c27`; 0 contenedores de testcontainers. La foto de `proptech` (ocho contenedores con id y estado, volúmenes, redes y `proptech-backend:local` `d681bd868971`, `proptech-web:local` `161136f89453`) es igual antes y después. No lo pisé ni toqué sus volúmenes.
- **Mutantes**: ninguno entregado. Cada uno se revirtió con `cmp` idéntico contra su copia, y `configuracion.py` terminó en el mismo hash que verificó el rompedor.

## JUICIO

- **Autor**: constructor, intento 3, segundo agente. **Comparación**: el código y los tests del árbol contra el grupo 9, D4, D10, el spec y los casos de verify 1.
- **Confianza alta**: 9.1 a 9.4 están construidas y vigiladas. Cada test nuevo cae rojo en su aserción contra el código de `22bb0402` reconstruido por la reversión, o contra un mutante dirigido, y vuelve a verde con la copia restaurada.
- **Confianza media**: que la reversión sea el código de `22bb0402`. No tengo esa revisión: la reconstruí desde la descripción de verify 1, y lo que la respalda es que reproduce las mismas salidas que pegó el rompedor.
- **Confianza media**: la autoría. La producción y los tests los escribió el agente detenido; yo los revisé y los probé. Un auditor que quiera la cadena "RED antes de producción" en sentido estricto no la tiene: tiene "RED contra la producción anterior", que es lo que L-013 permite cuando el código ya existe.
- **Confianza alta**: nada de esto toca `acceso`, la matriz de permisos ni `cuenta_corriente`, ni `semilla.py` o `cargador_yaml.py`.

## SUPOSICIÓN

- **Linux**: todo corrió en Windows. El 130 del proceso se probó con un doble de `crear_engine`, no con una señal real.
- **Sin rompedor sobre esta revisión**: por la decisión de Giuliano del 03/11/2026, el grupo 9 llega al auditor sin verify 2. Las correcciones las miré yo, que también las probé.
- **F5 a F9**: cada mutante corrió con su selección, no con el archivo entero bajo cada uno. Que ningún otro test lo mate no lo comprobé.
- **`Conflicto`** sigue en el 9 (D10), sin reproducir.

## Chequeos no ejecutados

- **Suite completa**: por decisión de Giuliano. El juez es el CI del PR (8.1), que no existe todavía.
- **`mypy` de Windows**: no lo corrí. En apply 2 daba los 2 errores previos de `tests/infra/test_respaldos.py:554`.
- **8.2 completa**: sólo `pisos: 0`, `--semilla=` y su gemelo fuera de desarrollo, más el control. Los códigos 4, 5, 6 y 7 por el comando real son la evidencia de apply 2, sobre `22bb0402`.
- **Los rojos del rompedor**: su archivo ya no existía; los casos se tomaron de su informe.

## Incidentes de esta corrida

- **Un `python3` colgado**: al editar mi guion de 8.2 usé `python3`, que en esta máquina es el alias de la tienda de Windows, y quedó en segundo plano sin terminar (tarea `btesi1hf3`). No escribió nada (el guion conservó su hash) y no toca el repo. Quise detenerlo y el sistema de permisos no lo dejó, así que **sigue vivo** y queda para el orquestador o para Giuliano.
- **Docker Desktop** quedó encendido; estaba apagado al empezar.
- **Memoria**: llegó a 340 MB libres con Docker encendido. Ningún comando lo cortó el sistema.
