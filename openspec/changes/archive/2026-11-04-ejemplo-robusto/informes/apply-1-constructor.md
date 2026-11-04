# Constructor · apply · intento 1 · ejemplo-robusto (C-27)

- **Rol**: constructor, subagente nativo `role-constructor`. Sin sustitución.
- **Executor declarado**: Claude Opus 5.5. Familia: Claude.
- **Fecha**: 30/10/2026, de 18:55 a 21:56 (-03:00).
- **Revisión**: base `9649471` más el árbol sin commit descrito en "Revisión entregada". No hice commits ni push.
- **Resultado**: 17 de 21 tareas marcadas. Quedan sin marcar 1.2 y 1.4 (H-2), 5.3 (H-1) y 8.1 (falta el CI). **Quedan dos decisiones para el orquestador antes del rompedor: H-1 y H-2.** La corrida final de la suite se cortó porque se apaga la máquina, así que este árbol no tiene un resultado de suite completa.

## Fuentes leídas

- `openspec/changes/ejemplo-robusto/`: `proposal.md`, `design.md`, `tasks.md`, `specs/datos-semilla/spec.md`, `informes/LEEME.md` e `informes/propose-1-plan-reviewer.md`.
- **Lecciones**: `knowledge-base/15_lecciones.md`, completo (L-001 a L-067).
- `knowledge-base/09_decisiones_y_supuestos.md`: D-112 y D-133, completas. De D-110 y D-138 sólo lo que traen el brief y el plan.
- **Código**: `complejos/aplicacion/ejemplo.py`, `compartido/configuracion.py`, `compartido/base_de_datos.py`, `compartido/semilla.py`, `compartido/cargador_yaml.py` (el lector de archivos), `acceso/aplicacion/alta_inicial.py`, `acceso/aplicacion/vinculacion_de_desarrollo.py`, `acceso/aplicacion/usuarios.py:225-302`.
- **Tests**: `tests/integracion/test_ejemplo_casos_de_uso.py`, `tests/integracion/test_arranque_tablas_protegidas.py`, `tests/integracion/conftest.py`, `tests/integracion/_edificios.py`, `tests/conftest.py:1-80`, `tests/unitarios/conftest.py`, `tests/unitarios/test_configuracion.py:1-100`, `test_configuracion_pool.py:1-60`, `test_base_de_datos_pool.py`, `test_arranque_api.py`, `test_arranque_worker.py`, `acceso/test_vocabulario_vigente.py`, `test_umbral_parametros.py:1-35` y las líneas del ejemplo en `test_fronteras_de_modulos.py`.
- **Infra**: `infra/compose.yaml`, `infra/ci/test-backend.sh`, `backend/Dockerfile`, `backend/pyproject.toml`, los pasos de `.github/workflows/ci.yml`, `README.md:93-121`.
- **Sin leer**: `infra/.env` (prohibido por el brief), y `infra/.env.example` a propósito, porque una regla de permisos lo bloqueó. Una búsqueda recursiva de `PROPTECH_ENTORNO` devolvió dos líneas de comentario de ese archivo, sin valores. Tampoco los informes de `.git/informes-*`, que están en la máquina de Juani.

## Contaminación por otros informes

Leí `informes/propose-1-plan-reviewer.md` porque el brief lo manda, así que sus hallazgos PR-1 a PR-9 condicionaron lo que miré. No existen todavía informes de rompedor ni de auditor.

## EVIDENCIA

La evidencia por tarea, con comando, hora y salida, está debajo de cada tarea en `tasks.md`. Acá va lo que el rompedor necesita reutilizar. Los registros completos de cada mutante quedan en el directorio temporal del constructor, que no viaja con el repo.

### Conteos de tests

| Medición | Antes (`9649471`) | Después |
|---|---|---|
| `test_ejemplo_casos_de_uso.py` | 47 | 206 |
| `test_puntos_de_entrada_prohibidos.py` (nuevo) | 0 | 3 |
| `test_fronteras_de_modulos.py` | 66 | 66 |
| Repo entero, `pytest --collect-only -q` | 4737 (antes de cambiar nada) | 4899 (21:54:02, sin ejecutar tests) |

No se borró ningún test. Se reescribieron `test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores` (de `permitido` a su código exacto), y las aserciones de `test_el_comando_real_se_niega_a_correr_como_el_migrador`, `test_el_id_de_otra_persona_es_error_propio_sin_datos`, `test_carrera_de_unicidad_se_traduce_sin_parametros` y `test_otro_integrity_error_no_se_disfraza_de_cuenta_ajena`, todas para exigir el código nuevo.

### Línea de base (0.1)

- **Comando**: `uv sync --locked`; `uv run pytest tests/integracion/test_ejemplo_casos_de_uso.py tests/unitarios/test_fronteras_de_modulos.py -q`. **Hora**: 18:55 a 18:58.
- **Salida**: `3 failed, 110 passed, 1 warning in 153.06s`.
- **Las 3 son previas y de Windows** (separador de ruta): `test_regla_sql_vigila_composicion[proptech_api]`, `[proptech_worker]` y `test_vinculacion_de_desarrollo_solo_desde_ejemplo`.

### Tareas

| Tarea | Estado | RED | GREEN |
|---|---|---|---|
| 0.1 | Hecha | No aplica | Ver arriba |
| 1.1 | Hecha | Mutantes M1.1a y M1.1b | `14 passed` |
| 1.2 | **Sin marcar, H-2** | Mutantes M1.2a y M1.2b | `14 passed` |
| 1.3 | Hecha | Mutante M1.3 | `14 passed` |
| 1.4 | **Sin marcar, H-2** | Mutantes M1.4a a M1.4f | `14 passed` |
| 2.1 | Hecha | Mutantes M2.1 y M2.1b | `1 passed` |
| 2.2 | Hecha | RED real y mutante M2.2 | `3 passed` |
| 3.1 | Hecha | RED real, declarado en H-3, y mutante M3.1 | `9 passed` |
| 3.2 | Hecha | RED real y mutantes M3.2a a M3.2c | `9 passed` |
| 3.3 | Hecha | RED real y mutantes M3.3a a M3.3e | `9 passed` |
| 4.1 | Hecha | RED real | `102 passed` |
| 4.2 | Hecha | Mutantes M4.2a a M4.2d | `102 passed` |
| 4.3 | Hecha | Mutantes M4.3a y M4.3b; el parámetro se saca como refactor | `213 passed` en configuración |
| 5.1 | Hecha | RED real (19:33) y mutantes M5.1a y M5.1b | `46 passed` |
| 5.2 | Hecha | RED real (19:33) y mutante M5.2a | `46 passed` |
| 5.3 | **Sin marcar, H-1** | RED real (19:33) y mutantes M5.3a a M5.3e | `6 passed` |
| 5.4 | Hecha | RED real (19:33) y mutantes M5.4a a M5.4c | `18 passed` |
| 6.1 | Hecha | Mutantes M6.1a a M6.1c y el archivo prohibido en el repo real | `3 passed` |
| 7.1 | Hecha | Validación de contrato, sin comportamiento ejecutable | `rg` de los 10 significados |
| 8.1 | **Sin marcar, falta el CI** | No aplica | Ver "Suite completa" |
| 8.2 | Hecha | No aplica | Ver "Comando real" |

### Mutantes

Cada uno se aplicó sobre una copia previa en el directorio temporal (no hay commit, L-013), se corrió, se restauró y se comparó byte a byte contra esa copia. **Los 47 registros dicen `identico`** (`rg -l` cuenta 47 de 47, y ninguno con `DISTINTO`). Ninguno quedó entregado: la comprobación final está en "Revisión entregada".

| Mutante | Dónde y qué | Resultado |
|---|---|---|
| M1.1a | `ejemplo.py:210`, estado de migración apagado | `DID NOT RAISE`, sólo `[estado_migracion]` |
| M1.1b | `:287`, modo apagado | `DID NOT RAISE`, sólo `[modo_del_grupo]` |
| M1.2a | `:239`, tipo apagado | `DID NOT RAISE`, sólo `[tipo_de_unidad]` |
| M1.2b | `:240`, piso apagado | `DID NOT RAISE`, sólo `[piso_de_unidad]` |
| M1.3 | `:263`, conjunto de grupos apagado | `DID NOT RAISE` en `[grupo_que_sobra]`; `KeyError` en `[grupo_que_falta]` |
| M1.4a | `:242`, superficie apagada | `DID NOT RAISE`, sólo `[superficie_de_unidad]` |
| M1.4b | `:229`, conjunto de unidades apagado | `DID NOT RAISE` en `[unidad_de_mas_en_la_base]`; `KeyError` en el otro |
| M1.4c | `:292`, conjunto de miembros apagado | `DID NOT RAISE` en `[miembro_de_mas_en_la_base]`; `KeyError` en el otro |
| M1.4d | `:297`, `difiere = False or (` | **No cuenta**: muere con `decimal.InvalidOperation`, fuera de la aserción (L-034). Se reemplazó por M1.4f |
| M1.4e | `:299`, valor contra valor apagado | `DID NOT RAISE`, sólo `test_el_coeficiente_propio_de_un_miembro_se_compara_por_valor` |
| M1.4f | `:297`, `None` contra valor apagado | `DID NOT RAISE`, sólo `[coeficiente_del_miembro]` |
| M2.1 | `threading.Lock` en el test | `threading.BrokenBarrierError`, a los 15 s de la barrera |
| M2.1b | La barrera mira otro texto | `assert 0 == 2` en `len(cruces)` |
| M2.2 | `for _ in range(1):` | `Failed: no volvió a mirar después de la espera` |
| M3.1 | `complejo_id = edificios[0].id` | `Failed: falso 'el ejemplo cambió'`, y `DID NOT RAISE` en los dos de 3.2 |
| M3.2a | `if len(coinciden) == 0:` | `DID NOT RAISE`, sólo "dos con el nombre" |
| M3.2b | Ninguno compara el primero | `DID NOT RAISE`, sólo "ninguno" |
| M3.2c | Ninguno espera | `EsperaAgotada`, sólo "ninguno" |
| M3.3a a M3.3c | Compara `vinculado`; otras personas cuentan; sin la persona no difiere | Sólo `[cuenta_vinculada]`; sólo `[otra_persona]`; `DID NOT RAISE` sólo en `test_sin_el_super_admin_el_ejemplo_es_distinto`. Corridos dos veces: antes y después de H-6 |
| M3.3d y M3.3e | Email y asignación apagados | `DID NOT RAISE`, sólo `[email]` y sólo `[asignacion]` |
| M4.2a | Sin `le=50` en el lector nuevo | `DID NOT RAISE`, sólo `[comando-DB_POOL_SIZE-51]` |
| M4.2b | Sin chequear el archivo | `DID NOT RAISE`, sólo `[comando-PROPTECH_PARAMETROS-valor-sembrado]` |
| M4.2c | Sin el entero ASCII | `DID NOT RAISE` en `[comando-DB_POOL_SIZE-5_0]` y `[comando-DB_POOL_SIZE- 5]` |
| M4.2d | No asigna el pool | `assert 5 == 7` |
| M4.3a y M4.3b | `redis_host` y `redis_password` con valor por defecto | Rojo en `[api-...]` y `[worker-...]` de su variable |
| M5.1a y M5.1b | Repite la ruta de la semilla o de los parámetros | Cae en `_afirmar_salida_limpia` con la ruta en el mensaje |
| M5.2a | La configuración antes de la guarda | `error inesperado: ConfiguracionInvalida` en lugar del 1 |
| M5.3a | Sin `connect_timeout` en `crear_engine` | `Failed: el comando siguió esperando`, a los 60 s |
| M5.3b | Ignora `DB_CONNECT_TIMEOUT_S` | `AssertionError: 3.857...` en el piso de 8 s |
| M5.3c | `OperationalError` cae en el 8 | Rojo en la base apagada y en la cortada |
| M5.3d | Reenvía el texto del driver | `la base no está disponible: (builtins.Exception) valor-sembrado` |
| M5.3e | Sin la rama de tablas | `error inesperado: TablasDeSoloAgregarDesprotegidas` en los dos casos |
| M5.4a | El 9 repite el texto | `error inesperado: RuntimeError: valor-sembrado` |
| M5.4b | El 8 repite el driver | `(builtins.Exception) valor-sembrado` |
| M5.4c | Sin la red del 9 | `Failed: _main dejó escapar RuntimeError` |
| M6.1a | Saca la carpeta de la lista | `assert [] == ['backend/desarrollo']`. La primera versión **sobrevivió**, porque el `parametrize` leía la misma constante; se corrigió el test |
| M6.1b | La guarda no mira nada | `assert [] == [...]` en los dos casos |
| M6.1c | Raíz equivocada | `assert False` en el `is_file()` |

### Suite completa (8.1)

- **Comando**: `bash infra/ci/test-backend.sh -q -p no:cacheprovider`, sin filtros y sin `PYTHONUTF8`, con `--tb=short` en la primera corrida y `--tb=line` en la segunda.
- **Primera corrida**, 19:57:43 a 21:06:35, con `git diff | sha256sum` en `769b969ea80dec504192c8b3aa9508535d720a4a854ed6604ac6f4f6e4e348b5`: `59 failed, 4838 passed, 1 skipped, 1 xfailed, 4 warnings in 4105.05s`. Quedó vencida: encontró H-6, que era mío, y después cambiaron `ejemplo.py`, `configuracion.py` y `test_ejemplo_casos_de_uso.py`.
- **Segunda corrida**, sobre este árbol: arrancó a las 21:40:54 y **se cortó a las 21:53:22** con `taskkill` sobre el árbol de `pytest.exe`, porque Giuliano apaga la máquina. **Sin resultado**: el último progreso impreso fue `[ 14%]`, sin resumen, y no vale como veredicto. La última corrida completa sigue siendo la primera, vencida por H-6, y se repite tras las correcciones.

Separación de las fallas, sobre las 59 de la primera corrida:

| Familia | Cuántas | En `9649471`, Windows | En un contenedor Linux, árbol final |
|---|---|---|---|
| `test_arranque_tablas_protegidas.py::test_cada_proceso_frena[...-ejemplo]` | 2 | **Pasan**: las rompe este change (H-1) | Fallan igual: `DID NOT RAISE TablasDeSoloAgregarDesprotegidas` |
| `acceso/test_vocabulario_vigente.py` | 1 | No se pudo comparar: el export no tiene `git` | Pasa. **Era mía (H-6), arreglada** |
| `test_fronteras_de_modulos.py` (separador de ruta) | 3 | Fallan igual | Pasan |
| `test_umbral_parametros.py::test_umbral_cero` (`read_text()` sin `encoding`) | 1 | Falla igual | Pasa |
| `tests/infra/test_clerk_en_compose.py` | 2 | Fallan igual | Pasan |
| `tests/infra/test_pasos_humo.py` | 3 | Fallan igual | Pasan |
| `tests/infra/test_restaurar.py` | 8 | Fallan igual | Pasan |
| `tests/infra/test_respaldos.py` | 26 | Fallan igual | Sin root, `38 passed` el archivo entero |
| Worker e invitaciones por `arq`, `[asyncio]` | 13 | Fallan igual | Pasan |

- **Comparación con la base**: `git archive 9649471` en un directorio temporal, `uv sync --locked`, y `pytest @lista` con los 58 ids (21:08:38 a 21:10:28): `56 failed, 2 passed`. Las 2 que pasan son las de H-1.
- **Contenedor Linux**: `python:3.14.8-slim-trixie`, `uv sync --locked` sobre una copia del árbol, con el repo montado de sólo lectura y el socket de Docker, para que las fallas de Windows no enmascaren una regresión mía en el worker o en el arranque. Los 59 ids (21:34:24 a 21:36:44, después del último cambio de código): `27 failed, 32 passed`: 25 de `test_respaldos.py`, que no corre como root (`el servicio de respaldos no puede correr como root`), y las 2 de H-1. `test_respaldos.py` sin root (21:39:53 a 21:40:44): `38 passed in 19.68s`.

### Lint, formato y tipos

Los comandos son los del CI (`.github/workflows/ci.yml`). `configuracion.py` es el único archivo Python modificado después de la corrida de las 21:23 (su hora de modificación es 21:26:55).

| Hora | Alcance | Comando | Salida |
|---|---|---|---|
| 21:23:51 | Árbol entero, antes del refactor de `_cargar` | `uv run ruff check .` | `All checks passed!` |
| 21:23:51 | Árbol entero, antes del refactor | `uv run ruff format --check .` | `405 files already formatted` |
| 21:23:53 | Árbol entero, antes del refactor | `uv run mypy` (Windows) | `tests\infra\test_respaldos.py:554: error: Module has no attribute "killpg"`, lo mismo con `"SIGKILL"`, y `Found 2 errors in 1 file (checked 368 source files)`, en un archivo que no toqué |
| 21:24:22 | Árbol entero, antes del refactor | `uv run mypy --platform linux` | `Success: no issues found in 368 source files` |
| Antes de 21:33:42 | `configuracion.py` | `uv run ruff format` y `uv run ruff check` | `1 file left unchanged` y `All checks passed!` |
| Antes de 21:33:42 | Árbol entero, con el refactor | `uv run mypy --platform linux` | `Success: no issues found in 368 source files` |

**No ejecutados sobre este árbol exacto**, porque llegó el corte: `ruff check .` y `ruff format --check .` del árbol entero, y `uv run mypy` con la plataforma de Windows. En un contenedor Linux, `ruff check .`, `ruff format --check .` y `mypy` dieron verde en la corrida de las 21:26:32, pero no sé si su copia ya tenía el refactor.

### Comando real (8.2)

La evidencia, con comandos y salida, está debajo de 8.2 en `tasks.md`. La última corrida fue de 21:25:01 a 21:25:51, con la imagen construida justo antes (`docker build` desde las 21:24:36), y el proyecto `proptech-c27` se bajó después. **Es anterior al refactor de `_cargar`** (21:26:55) y no se repitió: ese cambio no pasó por el stack real.

### Revisión entregada

Base `9649471`, sin commits. Hashes del 30/10/2026 a las 21:54:02.

```
$ git diff | sha256sum
1946d4ce3685097e815d5f05ea6758e8a0c242a7df6690afad2dec06a798a661 *-

$ sha256sum <archivos tocados>
c85946595037b618740ba5309cc3e050e62e0b9121b23daadfe4b0bcac7dd536 *README.md
1ff9517dc5bae1e130c240a4b5d152132a01aa03330d84d8e7ca6fbdbbab8756 *backend/src/proptech_core/compartido/base_de_datos.py
46a3a499ba0472f5efba33820e9bb15513e8588931b86bf9f88ed8401958e69e *backend/src/proptech_core/compartido/configuracion.py
3ec660d36e1f76ffd5501a2692b4f4e48a12f773f8fdf7aa3e4da05efded254c *backend/src/proptech_core/complejos/aplicacion/ejemplo.py
59ca36363913c9440850bd0c57322bf8d01c731ad86d3f94783166de5901f50a *backend/tests/integracion/test_ejemplo_casos_de_uso.py
af17cd1fdd72c17d4e6a253ad3cf8087661102374316bd014396042ecb0871a2 *backend/tests/unitarios/test_puntos_de_entrada_prohibidos.py

$ sha256sum <los que no toqué, marcados por el fin de línea>
62a32f7f701c48a424a3673527c90ec45302d7f2dcb975c6776be4415dfe7c46 *infra/respaldos/respaldar.sh
6266eec41ccddfe9e7cc6454ee8be3a22766614d5cdfae0b20cc2d2e555ed262 *infra/respaldos/restaurar.sh

$ git status --short
 M README.md
 M backend/src/proptech_core/compartido/base_de_datos.py
 M backend/src/proptech_core/compartido/configuracion.py
 M backend/src/proptech_core/complejos/aplicacion/ejemplo.py
 M backend/tests/integracion/test_ejemplo_casos_de_uso.py
 M infra/respaldos/respaldar.sh
 M infra/respaldos/restaurar.sh
?? backend/tests/unitarios/test_puntos_de_entrada_prohibidos.py
?? openspec/changes/ejemplo-robusto/
```

`git diff` no cubre lo que no está trackeado: el test de guarda va con su `sha256sum`. `backend/uv.lock` no aparece modificado.

**Sin mutantes en el árbol** (21:53:46 a 21:54:02). El `sha256sum -c` compara cada archivo con la copia previa a su último mutante. `configuracion.py` y `test_ejemplo_casos_de_uso.py` se editaron después de su último mutante, así que no entran en esa comparación: para el primero va el `diff`, y para los dos, `rg` de los textos que introducían los mutantes.

```
$ sha256sum -c sin-mutantes.sha
src/proptech_core/complejos/aplicacion/ejemplo.py: OK
src/proptech_core/compartido/base_de_datos.py: OK
tests/unitarios/test_puntos_de_entrada_prohibidos.py: OK
tests/integracion/test_arranque_tablas_protegidas.py: OK

$ diff <copia previa a M5.3b> configuracion.py
315c315
<     def _cargar(self, lector_cls: type[_LectorPostgresComun]) -> None:
---
>     def _cargar[T: _LectorPostgresComun](self, lector_cls: type[T]) -> T:
326a327
>         return base
456,466c457
<         try:
<             base = _LectorDelEjemplo()
<         except ValidationError as error:
<             raise ConfiguracionInvalida(
<                 f"Configuración inválida [...] {_mensaje_configuracion_invalida(error)}"
<             ) from None
<         self.postgres_host = base.postgres_host
<         self.postgres_port = base.postgres_port
<         self.postgres_user = base.postgres_user
<         self.postgres_password = base.postgres_password
<         self.postgres_db = base.postgres_db
---
>         base = self._cargar(_LectorDelEjemplo)

$ rg -n 'candado|administracion_que_no_existe' test_ejemplo_casos_de_uso.py
(sin coincidencias, código 1)

$ rg -n <los textos de los mutantes de producción y de la guarda> ejemplo.py base_de_datos.py configuracion.py test_puntos_de_entrada_prohibidos.py
(sin coincidencias, código 1)
```

En el `diff`, `[...]` reemplaza un guion largo de la línea original.

**Procesos y contenedores del corte**: `taskkill //PID 14576 //T //F` terminó `pytest.exe` y sus cuatro descendientes; tres segundos después, ninguno de los seis que comprobé (`pytest.exe`, dos `python.exe`, `uv.exe` y dos `bash`) seguía vivo: `uv.exe` y `bash` terminaron solos. Los tres contenedores de testcontainers de esa corrida ya no estaban a las 21:53:46 ni a las 21:54:02 (`docker ps -a --filter label=org.testcontainers=true` vacío); no hizo falta sacarlos. Los ocho contenedores de `proptech` siguen detenidos.

## Hallazgos

### H-1. El plan no nombra un consumidor de `_main`, y este change lo rompe. **Decide el orquestador**

- **Qué pasa**: `tests/integracion/test_arranque_tablas_protegidas.py::test_cada_proceso_frena[configuracion_versionada-ejemplo]` y `[imputacion-ejemplo]` esperan que `ejemplo._main` deje escapar `TablasDeSoloAgregarDesprotegidas`. El spec pide código 4 sin traceback, así que `_main` devuelve 4 y el test da `Failed: DID NOT RAISE TablasDeSoloAgregarDesprotegidas`. No están ni en `proposal.md` ni en `design.md` ni en el brief, y ese archivo está fuera de los autorizados.
- **Reproducción**: `uv run pytest tests/integracion/test_arranque_tablas_protegidas.py -q` (19:49): `2 failed, 10 passed`. En `9649471` esos dos pasan.
- **Lo que no hice**: no toqué ese archivo, y no achiqué el código 4 para que el test siguiera pasando. Por eso 5.3 queda sin marcar y la suite tiene estas dos en rojo.
- **La garantía no quedó sin cubrir**: `test_tablas_de_solo_agregar_desprotegidas_terminan_con_4`, con las mismas dos tablas, por el proceso real.
- **Propuesta, probada de forma temporal** (`uv run pytest ... -k cada_proceso_frena`, 19:51:59: `8 passed`, y `sha256sum` idéntico al restaurar):

  ```diff
  -                ejemplo._main(["cargar"])
  +                assert ejemplo._main(["cargar"]) == 4
  +                raise TablasDeSoloAgregarDesprotegidas(tabla)
  ```

### H-2. El spec pide nombrar el dato, y el grupo 1 dice "sin cambios de producción". **Decide el orquestador**

- **Qué pasa**: el escenario "Cada dato comparado se detecta por separado" dice que "el mensaje nombra ese dato" para tipo, piso, coeficiente y superficie de una unidad. El mensaje actual es `unidades[1A]: difiere de la semilla`: nombra la unidad y no el campo. Los tests de 1.2 y 1.4 tienen `match` en `unidades\[1A\]` y cada mutante mata sólo a su caso, así que la verificación escrita de las tareas se cumple.
- **Por qué no lo absorbí**: arreglarlo es producción, y el grupo 1 lo prohíbe; dar por cumplido el spec sería achicarlo. Las demás ramas sí nombran su dato.
- **Opciones**: (a) mensaje por campo, `unidades[1A].piso: difiere de la semilla`, con unas seis líneas en `ejemplo.py` y el `match` apretado, sin romper `test_ciclo_completo_de_carga_del_ejemplo`; o (b) corregir el spec para que diga que nombra la unidad.
- **Recomendación**: (a), porque el objetivo del change es que se entienda qué difiere sin leer un traceback.

### H-3. El falso "distinto" no depende del orden físico, y es más probable de lo que dice el plan

- **Qué pasa**: `EXPLAIN (COSTS OFF)` de la consulta vieja da `Index Only Scan using uq_complejo_administracion_id`, en tres corridas. `LIMIT 1` devuelve el `id` más bajo, que es aleatorio. El `UPDATE` del design no lo mueve (el ctid del ejemplo pasó de `(0,2)` a `(0,4)` y el primero siguió siendo el mismo).
- **Consecuencia**: con un segundo edificio creado por `POST /complejos`, el comando daba un falso "el ejemplo cambió" a cara o cruz, sin ningún `UPDATE` (dos de tres en la sonda). `design.md` (Risks) y la ficha hablan de orden físico: conviene corregirlo al cerrar.
- **Cómo quedó el test**: fija el `id` más bajo con una fila propia, además del edificio real, y exige que `LIMIT 1` la elija con el plan preferido y recorriendo la tabla.

### H-4. El lector de archivos repite la ruta, contra lo que suponía D4. Resuelto dentro de `ejemplo.py`

D4 dice que los errores de los lectores "ya no repiten valores". `cargador_yaml.leer_archivo` sí repite la ruta (`no se puede leer el archivo: <ruta>`), y `--semilla` es algo que se tipeó, que puede ser el id de la cuenta, que el spec prohíbe mostrar. No toqué `cargador_yaml.py`: `_ejecutar` reemplaza esa ruta en el mensaje, con su test y su mutante. **Es una línea que el plan no pedía**: el rompedor debería mirarla. Los mensajes de `SemillaInvalida` siguen nombrando identificadores de unidad del archivo, porque el spec de la semilla lo exige, y no son secretos.

### H-5. `argparse` repetía el id en `invalid choice`. Resuelto dentro de `ejemplo.py`

`python -m ... user_Dev123` imprimía el id. RED en el caso `["user_Dev123"]` del test que ya existía, GREEN con `_Parser`, que da siempre el mismo mensaje y termina con 2.

### H-6. La palabra que usa el spec para la persona está prohibida en el código. Era una regresión mía, ya arreglada

`test_vocabulario_vigente.py` (L-022) prohíbe en `backend/` e `infra/` la palabra que el spec usa para esta persona. Lo escribí igual que el spec, en `ejemplo.py` y en los tests, y sólo lo vio la suite completa (L-064): los tests del archivo tocado pasaban. En el código ahora es "el super admin del ejemplo", sin agregar excepciones a ese test. El spec conserva su palabra, que no se puede citar en un docstring de test: **conviene cambiarla si el spec se reabre**.

### H-7. Fallas de Windows que D-110 no nombra

Además de las de D-110, en esta máquina fallan por el separador de ruta `test_fronteras_de_modulos.py` (3) y por la codificación `test_umbral_cero` (1). `uv run mypy` da en Windows `tests\infra\test_respaldos.py:554: error: Module has no attribute "killpg"` y `"SIGKILL"`, en un archivo que no toqué; con `--platform linux` da `Success`. No arreglé nada de esto.

## JUICIO

- **Autor**: constructor. **Comparación**: lo construido contra `proposal.md`, `design.md`, el spec y las lecciones.
- **Confianza alta**: que los códigos 0 a 9 se comportan como dice la tabla (test por familia, mutantes y comando real), y que no se tocó `acceso`, la matriz de permisos ni `cuenta_corriente`. `git diff --stat` lo muestra, y `listar_personal` se llama sin modificarse.
- **Confianza alta**: que no rompí la API ni el worker. Sus tests de arranque corren el proceso real, y las pruebas del worker, que Windows enmascara, pasan en Linux.
- **Confianza media**: que el juez real, el CI del PR, dé lo mismo que mi contenedor Linux, que no es su entorno.
- **Autoría**: escribí el test, el código y el mutante. Eso no es una revisión independiente (L-025): el rompedor y el auditor son los primeros ojos de afuera.

## SUPOSICIÓN

- **Qué mutante es cada número de M5 a M8** de la ficha: lo tomé del orden del plan, sin los informes del PR #1. Se cubren los cuatro.
- **La base lenta (L-001)** no está probada: `proposal.md` la deja fuera.
- **`KeyboardInterrupt`** no pasa por el código 9, a propósito: es `BaseException`, y no lo probé.
- **El piso de 8 s y el techo de 38 s** de `test_la_base_que_no_responde_termina_con_5_dentro_del_limite` se midieron en Windows (12.36 s) y pasaron en el contenedor Linux. En un CI muy cargado el techo podría quedar justo; no lo pude medir.

## Chequeos no ejecutados y límites

- **CI del PR**: no existe, porque no hay push ni PR, y `gh` no está instalado. Por eso 8.1 queda sin marcar.
- **Suite completa sobre este árbol**: cortada, sin resultado. Se repite tras las correcciones de H-1 y H-2.
- **`test_ejemplo_casos_de_uso.py` entero**: no tiene una corrida que se pueda atar a este árbol. La última en Windows fue de 21:17:43 a 21:22:51 (`3 failed, 273 passed`, con la guarda, el vocabulario y fronteras; las 3 son las de la línea de base), antes del refactor de `_cargar`. En Linux, de 21:26:32 a 21:30:46 (`3 failed, 295 passed`: las 2 de H-1 y el vocabulario, porque ese contenedor no tenía `git`), sin saber si su copia ya tenía el refactor. Después del refactor sólo corrió la selección de configuración (21:33:42, `319 passed`).
- **Códigos 7, 8 y 9 en el stack real**: probados por tests (8 también por el proceso real), no en 8.2.
- **`infra/ci/humo.sh`**: no lo corrí. No lo toqué, y corre otro comando (`compartido.semilla`), cuyo código no cambia.
- **`infra/.env.example`**: como no se pudo leer, los nombres del archivo de entorno de 8.2 salieron de los `:?falta` de `compose.yaml`, con contraseñas inventadas.
- **`git diff` de `infra/respaldos/*.sh`**: no los toqué; el `sha256sum` es el mismo al empezar y al terminar. `backend/uv.lock` no cambió.
