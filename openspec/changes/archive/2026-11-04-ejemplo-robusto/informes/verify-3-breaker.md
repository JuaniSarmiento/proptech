# verify 3 · rompedor · ejemplo-robusto (C-27, LOW)

- **Rol**: rompedor, intento 3 de verify. **Executor declarado**: Claude Opus 5.5 (subagente), según el entorno. Es la misma familia que el constructor, el orquestador y los rompedores de verify 1 y 2, así que la independencia es limitada (L-025). El proyecto no declara `## Role executors`.
- **Fecha**: 03/11/2026 23:58 a 04/11/2026 00:02 (-03:00), Windows.
- **Revisión atacada**: `5fd45c0e9f1b751b79fc3082d1df817c4061edfe` (la anterior atacada fue `7110aac`). El blob de `ejemplo.py` es `875f44704d0d1b05bef858c9a25129919d93056c`, igual al de `5fd45c0` antes y después de los mutantes.
- **Alcance (brief)**: sólo confirmar el cierre de F10 y F11 de `verify-2-breaker.md` y contrastar D4 y D5 de `design.md` con el código. No ataqué nada más.
- **Resultado**: **F10 y F11 cerrados.** Los dos tests nuevos matan B7 y B4 en la aserción que nombran, y también una variante de cada uno. Las citas nuevas de D4 y D5 son ciertas. **No reproduje ninguna falla nueva.** Este informe no aprueba: decide el auditor.

## Fuentes leídas

- `knowledge-base/15_lecciones.md`: L-019, L-034 y L-035 (encabezado y "Qué pasó").
- `openspec/changes/ejemplo-robusto/informes/verify-2-breaker.md`: mi informe anterior (F10, F11, B4, B7 y O7).
- `git diff 7110aac 5fd45c0 -- backend/ openspec/changes/ejemplo-robusto/design.md`.
- `backend/src/proptech_core/complejos/aplicacion/ejemplo.py` en `5fd45c0`: `_ejecutar` y `_main` (`:544-662`).
- `ejemplo.py` en `9649471`, líneas `:455-505`, para las citas nuevas de D4, y `git grep clerk_emisor 9649471 -- backend/src`, para D5.
- Helpers del archivo de tests: `_entorno_limpio` (`:1296`) y `_correr_comando` (`:1130`).
- No leí `tasks.md` ni `apply-4-constructor.md`, que quedan fuera del encargo. No leí `infra/.env*` ni `.git/informes-*`.

## Contaminación

El brief del orquestador resume el delta y el resultado del constructor (`243 passed`, ruff y mypy); no lo usé como evidencia propia. Los mutantes que reapliqué salen de mi informe de verify 2. No leí informes de otros roles de este intento.

## EVIDENCIA

Comando de las corridas, desde `backend/`: `uv run pytest tests/integracion/test_ejemplo_casos_de_uso.py -k "test_un_value_error_no_previsto_en_la_carga_termina_con_9 or test_la_semilla_vacia_va_antes_que_la_configuracion" -q -p no:cacheprovider`. Los mutantes se aplicaron con `uv run python -I <scratchpad>/mutar.py` sobre `ejemplo.py` en su lugar, con un respaldo previo en el scratchpad. Cada corrida partió de una copia del respaldo.

| Hora (-03:00) | Acción | Salida relevante |
|---|---|---|
| 23:58 | `git rev-parse HEAD` y `git diff 7110aac 5fd45c0 -- backend/src` contado con `wc -l` | `5fd45c0e...` y `0`: la producción no cambió |
| 23:58 | `git rev-parse 5fd45c0:backend/src/.../ejemplo.py` y `git hash-object` del árbol | los dos dan `875f4470...` |
| 23:58:44 | Los dos tests en limpio | `2 passed, 241 deselected in 13.98s` |
| 23:59:11 y 23:59:29 | Intento de B7 con `sd`: `sd: command not found`, así que el archivo **no se mutó** | `2 passed` las dos veces. **No cuentan como corridas bajo mutante**: son dos corridas limpias de más |
| 00:00:04 | **B7**: `except EntradaInvalida` pasa a `except ValueError`, con `getattr(error, 'campo', type(error).__name__)` en el mensaje (diff verificado) | `1 failed, 1 passed`. Falla `test_un_value_error_no_previsto_en_la_carga_termina_con_9` en `assert _codigo_de_main() == 9`, con `assert 3 == 9` |
| 00:00:23 | **B7e**, la variante: `except Exception` con el mismo mensaje | `1 failed, 1 passed`. Falla el mismo test, en la misma aserción: `assert 3 == 9` |
| 00:00:41 y 00:01:01 | Primer intento de B4 y B4b: por el CRLF, mi script no encontró el bloque y **abortó sin escribir** | `2 passed` las dos veces. **No cuentan**: son corridas limpias de más |
| 00:01:43 | **B4**: el bloque `if args.semilla == "": return _fallar(CODIGO_USO, ...)` pasa a después del `try` de `ConfiguracionDelEjemplo()` (diff verificado) | `1 failed, 1 passed`. Falla `test_la_semilla_vacia_va_antes_que_la_configuracion` en `assert resultado.returncode == 2`, con `assert 3 == 2` y `falta configurar: POSTGRES_APP_PASSWORD, POSTGRES_APP_USER, POSTGRES_DB, POSTGRES_HOST, PROPTECH_PARAMETROS` en la salida |
| 00:02:02 | **B4b**, la variante: el bloque pasa a justo antes de `crear_engine(configuracion)`, después de los lectores | `1 failed, 1 passed`. Falla el mismo test con `assert 3 == 2` |
| 00:02 | Restauración: copia del respaldo, `git hash-object` y `git diff --quiet -- src` | `875f44704d0d1b05bef858c9a25129919d93056c` y `SRC_LIMPIO` |
| 00:02:28 | `git status --short` | Sólo `infra/respaldos/respaldar.sh`, `restaurar.sh` e `informes/LEEME.md`, igual que al empezar |

## Lentes

### Correctitud

- **F10**: el test reemplaza `ejemplo.crear_grupo` por un doble que lanza `ValueError` con un valor sembrado, y corre por `_main` sobre `base_fresca`. Exige 9, `stderr.strip() == "error inesperado: ValueError"`, una salida sin el valor sembrado ni la contraseña, y cero filas escritas. Mata B7 y B7e en la aserción del código. **Cerrado.**
- **F11**: el test corre el proceso real con `PROPTECH_ENTORNO=desarrollo` y sin ninguna variable `POSTGRES_`, `PROPTECH_` ni `CLERK_` (`_entorno_limpio`). Exige 2 y el texto de `--semilla`. Mata B4 y B4b en `returncode == 2`. **Cerrado.**

### Cableado

- El doble de F10 reemplaza el nombre `crear_grupo` del módulo `ejemplo` (`:80`), el mismo que llama `cargar` (`:215`). B7 lo confirma: con la rama ancha, el `ValueError` llegó a ella y salió con 3.
- F11 entra por `python -m proptech_core.complejos.aplicacion.ejemplo cargar`, que es el consumidor real del comando.

### Documentación

- **D4, "Orden"**: en `9649471`, `Configuracion(clerk_emisor=...)` (`:460`) y `leer_parametros` (`:461`) están fuera de todo `try`. También lo está `crear_engine` (`:471`). Las verificaciones y los `registrar_*` (`:473-477`) están dentro de un `try` que sólo tiene `finally`, sin ningún `except` para errores de base. `leer_georef` y `leer_semilla` (`:463-466`) sí están dentro de un `try ... except Exception`. En `5fd45c0`, `ConfiguracionDelEjemplo()` (`:571-574`) y los tres lectores (`:576-584`) tienen su `try`, y las verificaciones van dentro del `try` de la carga (`:587-646`). `crear_engine` (`:586`) queda fuera, así que lo que lanzara lo toma el `except Exception` de `_main` (`:657`) como 9. **Cierto.** Esto cierra también O7 de verify 2.
- **D5, `clerk_emisor=`**: en `9649471`, la única llamada en `backend/src` que pasa el argumento `clerk_emisor=` es `ejemplo.py:460`. `proptech_api/acceso.py:47` lee el atributo `configuracion.clerk_emisor`, pero no pasa el argumento. **Cierto**, leído como argumento del constructor, que es lo que dice el texto.
- Los docstrings de los dos tests dicen lo que hacen y nombran el mutante que distinguen. **Ciertos.**

## JUICIO

- **Autor**: rompedor. **Comparación**: los dos tests nuevos contra B7 y B4 de verify 2 y contra una variante de cada uno, y las citas de D4 y D5 contra `ejemplo.py` en `9649471` y en `5fd45c0`.
- **Confianza alta**: F10 y F11 quedaron cerrados. Cada test pasa en limpio y falla bajo su mutante y bajo su variante, en la aserción que distingue el comportamiento (el código de salida) y no por un error de armado. Eso cumple L-019 (el test puede dar rojo), L-034 (falla por el motivo correcto) y L-035 (vigila de verdad).
- **No son tautológicos ni espejo de la implementación**: F10 no repite la cadena de `except`, sino que afirma el código y la salida que se observan. F11 afirma el código del proceso real con el entorno vacío, que es justo lo que distingue el orden.
- **Confianza alta**: las citas nuevas de D4 y D5 son ciertas.
- No reproduje ninguna falla nueva dentro de este alcance acotado.

## SUPOSICIÓN

- No corrí el archivo entero, ni ruff ni mypy: según el brief, el constructor los corrió sobre los mismos archivos. Mis corridas cubren sólo los dos tests.
- No ataqué nada fuera de F10, F11, D4 y D5. El resto del change se apoya en la evidencia de verify 2.
- Las variantes que probé (B7e y B4b) son las obvias. No probé, por ejemplo, atrapar el `ValueError` en otra capa, como dentro de `cargar`.

## Conteo de tests propio

| Corrida | Estado | Resultado |
|---|---|---|
| 23:58:44 | Limpio | 2 tests ejecutados, 2 passed |
| 23:59:11, 23:59:29, 00:00:41 y 00:01:01 | Limpio, por una falla de mi arnés (el mutante no se aplicó) | 8 ejecuciones, 8 passed. No cuentan como mutantes |
| B7, B7e, B4 y B4b | Mutantes | 8 ejecuciones: 4 failed (en cada caso, el test que corresponde) y 4 passed (el otro test) |
| **Total** | | 18 ejecuciones de los dos tests. Verde en limpio de la entrega: 2 tests |

## Chequeos no ejecutados

La suite completa, el archivo completo, ruff y mypy (por el brief) y el CI.
