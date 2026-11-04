# apply 4, constructor: `ejemplo-robusto` (C-27, LOW), grupo 10

- **Autor**: subagente constructor, despachado por el orquestador el 03/11/2026. Ejecutor declarado: Claude (Opus 5.5), subagente nativo. Familia compartida con el orquestador y el rompedor de verify 2: Claude.
- **Revisión de partida**: `7110aac`, con el árbol sucio que ya traía (`infra/respaldos/*.sh`, `informes/LEEME.md`, `tasks.md`, `informes/verify-2-breaker.md`), que no toqué salvo `tasks.md`.
- **Archivos cambiados**: `backend/tests/integracion/test_ejemplo_casos_de_uso.py` (2 tests, +36 líneas), `openspec/changes/ejemplo-robusto/design.md` (D4, 1 línea), `openspec/changes/ejemplo-robusto/tasks.md` (evidencia del grupo 10). Producción sin cambios.
- **Diff entregado** (`git diff -- <test> <design.md> | sha256sum`): `26b9a96b9aa4229fed06e683772c01084fa3f685185669854db4dd636edbb8f7`, antes de anotar `tasks.md`.

## EVIDENCIA

| Hora (-03:00) | Comando (desde `backend/`) | Resultado |
|---|---|---|
| 23:46:37 | `uv run pytest tests/integracion/test_ejemplo_casos_de_uso.py -q -p no:cacheprovider -k "cada_familia_de_error or la_semilla_vacia"` (baseline, sin cambios) | `12 passed, 229 deselected` |
| 23:47:0x | copia de `ejemplo.py` a `scratchpad/constructor4/ejemplo.py.orig` con `cp -p` | `sha256` `32648461d798f397617101d6f119b8d82f512c25768f9cb7779b485de6ccfe64` en los dos; `git hash-object` `875f44704d0d1b05bef858c9a25129919d93056c` = `git rev-parse 7110aac:backend/src/.../ejemplo.py` |
| 23:47:37 | B7 aplicado; `-k test_un_value_error_no_previsto_en_la_carga_termina_con_9` | **RED** `1 failed, 242 deselected`: `:2407 assert 3 == 9`; stderr `la semilla o los parámetros no se pueden cargar: ValueError; no se escribió nada` |
| 23:48:05 | restaurado con la copia; mismo test | `sha256` `32648461...`; `git status --short -- src` vacío; **GREEN** `1 passed, 242 deselected` |
| 23:48:30 | B4 aplicado; `-k test_la_semilla_vacia_va_antes_que_la_configuracion` | **RED** `1 failed, 242 deselected`: `:1672 assert 3 == 2`; stderr `Configuración inválida — falta configurar: POSTGRES_APP_PASSWORD, POSTGRES_APP_USER, POSTGRES_DB, POSTGRES_HOST, PROPTECH_PARAMETROS` |
| 23:48:41 | restaurado con la copia; mismo test | `sha256` `32648461...`, `git hash-object` `875f4470...`; **GREEN** `1 passed, 242 deselected` |
| 23:48:49 | `uv run ruff check` y `ruff format --check` sobre el test | E501 y "would reformat" sólo en la línea nueva de F11 (`:1670`) |
| 23:48:56 | `uv run ruff format <test>`; `ruff check`; `ruff format --check`; `uv run mypy --platform linux <test>` | `All checks passed!`; `1 file already formatted`; `Success: no issues found in 1 source file`. El diff sigue siendo sólo +36 líneas |
| ~23:49 | `openspec validate ejemplo-robusto` (desde la raíz) | `Change 'ejemplo-robusto' is valid` |
| 23:49:57 a 23:56:10 | `uv run pytest tests/integracion/test_ejemplo_casos_de_uso.py -q -p no:cacheprovider` (archivo entero, una vez, revisión entregada) | `243 passed, 1 warning in 368.90s`, rc 0 |

Mutantes, diffs (`diff --strip-trailing-cr` contra la copia; guardados en `scratchpad/constructor4/B7.diff` y `B4.diff`):

```
B7
632c632
<     except EntradaInvalida as error:
>     except ValueError as error:
636c636
<             f"la semilla o los parámetros no se pueden cargar: {error.campo}; no se escribió nada",
>             f"la semilla o los parámetros no se pueden cargar: {getattr(error, "campo", type(error).__name__)}; no se escribió nada",

B4
557,559d556
<     if args.semilla == "":
<         return _fallar(CODIGO_USO, "--semilla no puede estar vacío; no se escribió nada")
<
574a572,573
>     if args.semilla == "":
>         return _fallar(CODIGO_USO, "--semilla no puede estar vacío; no se escribió nada")
```

B7 se aplicó con `sed -i`, que dejó el archivo en LF; B4 con un script de Python (`uv run python -I`) que conserva CRLF. Las dos veces se restauró copiando la copia previa, y el `sha256` volvió a `32648461...` (L-013: la garantía es contra mi copia, confirmada además con `git hash-object` contra el blob de `7110aac`).

Tests nuevos:

- `test_un_value_error_no_previsto_en_la_carga_termina_con_9` (cerca de `:2390`): `base_fresca`, `_entorno_clerk`, doble de `ejemplo.crear_grupo` que lanza `ValueError(_VALOR_SEMBRADO)`. Exige 9, `stderr.strip() == "error inesperado: ValueError"`, que no salgan el valor sembrado ni `APP_PASSWORD_DE_SESION`, y `_filas_escritas == _SIN_ESCRITURAS`.
- `test_la_semilla_vacia_va_antes_que_la_configuracion` (cerca de `:1665`): proceso real con `_entorno_limpio()` + `PROPTECH_ENTORNO=desarrollo`, `--semilla=`. Exige 2, `--semilla no puede estar vacío` en stderr y la salida limpia.

10.3: D4 de `design.md` ya no cita `:460`, `:461`, `:471`, `:473-477` ni `:463-466`; los reemplacé por los nombres de las sentencias del código de partida (`ejemplo.py` en `9649471`, sin cambios desde `8b19192`), que leí con `git show 9649471:...` (líneas 460, 461, 463-466, 471, 473-477), y agregué cómo queda en `_ejecutar`.

Hashes finales:

- `backend/src/proptech_core/complejos/aplicacion/ejemplo.py`: `sha256` `32648461d798f397617101d6f119b8d82f512c25768f9cb7779b485de6ccfe64` (copia de trabajo con CRLF), `git hash-object` `875f44704d0d1b05bef858c9a25129919d93056c`, igual al blob de `7110aac`.
- `backend/tests/integracion/test_ejemplo_casos_de_uso.py`: `sha256` `14172b75885e20631e453f2e6a102168e25e2d43f05f4f261ce556208e6ebc5e`.
- `openspec/changes/ejemplo-robusto/design.md`: `sha256` `f9c5dc517192b6fd557e1201b3b9ce052aa1982616efd0efa48d9fcee2c23954`.

## JUICIO

- Constructor, confianza alta: cada test nuevo falla en la aserción que dice probar (el código: `3 == 9` y `3 == 2`), no en un paso previo (L-034), y pasa con la producción de `7110aac`. F10 y F11 quedan vigilados (L-035).
- Constructor, confianza alta: F10 se prueba sobre la carga real (doble de `crear_grupo`, no de `cargar`) como pedía el brief; además vigila que la transacción no deja nada escrito.
- Constructor, confianza media: la frase nueva de D4 dice que `crear_engine(...)` queda fuera de un `try` en `_ejecutar` y que lo que lanzara lo toma `_main` como 9. Lo primero lo leí en el código; lo segundo sale de `_main` (`except Exception`). No probé un fallo real de `crear_engine`.

## SUPOSICIÓN

- El hash `sha256` de `ejemplo.py` (`32648461...`) no coincide con el `sha256` del blob de `7110aac` (`89828fcb...`) sólo por los finales de línea (`core.autocrlf=true`, la copia de trabajo es CRLF). La igualdad la sostengo con `git hash-object`, que normaliza.
- `git` avisa que `test_ejemplo_casos_de_uso.py` y `design.md` quedan en LF en la copia de trabajo. Para el test, el `sha256` de partida (`04201ab2...`) coincide con el blob LF de `7110aac`, así que ya estaba en LF antes. No afecta el diff normalizado.
- No corrí la suite completa (el brief la deja al CI del PR) ni otra corrida de los mutantes fuera de la selección de cada test.
- **Fuera de alcance, sin tocar**: D5 (`design.md:65`) todavía cita `ejemplo.py:460` como consumidor de `clerk_emisor=`, con el mismo problema que O7. Lo dejo para que el orquestador decida (texto, sin comportamiento).
- No quedó ningún proceso colgado. Testcontainers no dejó contenedores aparte de los `proptech-*` detenidos, que no toqué.

## Fuentes leídas

- `knowledge-base/15_lecciones.md`: L-013, L-019, L-034, L-035 (ruta leída).
- `openspec/changes/ejemplo-robusto/informes/verify-2-breaker.md` (F10, F11, O7, B4, B7, y las lentes que los citan).
- Scratchpad del rompedor: `.../scratchpad/rompedor2/pruebas/test_rompedor2.py` (referencia; no copié el archivo).
- `openspec/changes/ejemplo-robusto/tasks.md` (grupo 10 y estado), `design.md` (D4, D5).
- `backend/src/proptech_core/complejos/aplicacion/ejemplo.py` (`_ejecutar`, `_main`), `git show 9649471:` del mismo archivo (líneas 440-490), `compartido/base_de_datos.py` (`crear_engine`, por encima).
- `backend/tests/integracion/test_ejemplo_casos_de_uso.py` (helpers, fixtures y los tests vecinos).

## Contaminación por otros informes

- Los mutantes B4 y B7 y el diseño de los dos tests vienen de `verify-2-breaker.md` y de su scratchpad. Reescribí los tests, los corrí y vi su rojo y su verde yo; las conclusiones sobre la producción (que está bien) son del rompedor, y las confirmé sólo en lo que vigilan estos dos tests.
- No leí otros informes de `informes/`.
