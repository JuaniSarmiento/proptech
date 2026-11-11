<!-- Guardado textual por el orquestador el 04/11/2026: el subagente auditor no tiene herramienta de escritura y devolvió el informe en su mensaje de entrega. -->

# Auditor · verify · intento 2 · ejemplo-robusto (C-27, 3f, LOW)

- **Rol**: auditor final, subagente nativo `role-auditor`, sin sustitución. **Ejecutor declarado**: Claude Opus 5.5 (lo dice el entorno). Es de la familia Claude, la misma que el orquestador, los cuatro constructores y los tres rompedores. El proyecto no declara `## Role executors`.
- **Fecha**: 04/11/2026, de 00:50 a 00:58 aproximadamente (-03:00).
- **Revisión auditada**: `1d090f6f79c6f3ed8ff7824ae629bda982f66424`, que es `HEAD` y también `origin/change/ejemplo-robusto` (PR #7). El árbol local sólo tiene cambios en `tasks.md`, `informes/LEEME.md` e `infra/respaldos/*.sh` (fin de línea).
- **Alcance**: hice la lectura liviana de B1 y B2 que propuse en `verify-1-auditor.md`. No es una auditoría completa nueva.
- **Persistencia**: no escribí `informes/verify-2-auditor.md`. El brief es de sólo lectura, y el entorno de este subagente me prohíbe escribir archivos de informe. El orquestador tiene que guardar este texto tal cual en `C:\Programacion\proptech\openspec\changes\ejemplo-robusto\informes\verify-2-auditor.md`.

## Fuentes leídas

- **Informes originales**: `verify-1-auditor.md` (el mío, entero), `verify-2-breaker.md`, `apply-4-constructor.md` y `verify-3-breaker.md`, enteros.
- **Artefactos**: `tasks.md` ("Estado del flujo", 8.1 y grupo 10), `informes/LEEME.md` (índice, "Faltan" y despachos), `git diff` local de los dos.
- **Código y CI**: `.github/workflows/ci.yml:1-45`, `infra/ci/test-backend.sh` y `addopts` de `backend/pyproject.toml`.
- **Lecciones**: `knowledge-base/15_lecciones.md`, texto de L-042, L-055 y L-064. La última es L-067.
- **Memoria del proyecto**: los artefactos del change. No volví a listar `openspec/changes/archive/`: uso la lista de mi verify 1, que tiene 17 changes y ninguno es este. **Engram: no lo usé.** Tampoco `obsidian.md`.
- **No leí**: `infra/.env`, `infra/.env.example` ni `.git/informes-*`.

## Contaminación

- El brief resume el resultado de cada informe. No usé ese resumen como evidencia: lo comparé contra los originales y contra mis propios comandos.
- Leí la conclusión del rompedor (F10 y F11 cerrados) antes de comprobar nada, y no repetí sus mutantes. En ese punto mi juicio se apoya en su evidencia.
- Todos los roles comparten familia (L-025, DE-8).

## EVIDENCIA

| Hora (-03:00) | Comando | Resultado |
|---|---|---|
| 00:53 | `git rev-parse HEAD` y `origin/change/ejemplo-robusto` | Los dos dan `1d090f6f79c6...` |
| 00:53 | `git diff 1d090f6 --stat -- backend README.md` | Vacío: no hay código local distinto del que corrió el CI |
| 00:53 | `git diff 7110aac 1d090f6 -- backend/src` | Vacío: la producción no cambió después de `7110aac` |
| 00:53 | `git diff 7110aac 1d090f6 --stat` | Sólo el test (+36), `design.md` (4 líneas), `tasks.md`, `LEEME.md` y tres informes |
| 00:54 | `git diff 7110aac 1d090f6 -- backend \| rg "def test_"` | Exactamente dos tests nuevos: `test_la_semilla_vacia_va_antes_que_la_configuracion` y `test_un_value_error_no_previsto_en_la_carga_termina_con_9`. Ninguno borrado |
| 00:54 | `sha256sum` de `configuracion.py`, `base_de_datos.py`, `test_arranque_tablas_protegidas.py`, `ejemplo.py` y `test_puntos_de_entrada_prohibidos.py` | `46a3a499`, `1ff9517d`, `f9521fd9`, `32648461` y `97fee65c`: iguales a los que audité sobre `6dd4630f` en verify 1 |
| 00:54:11 | `uv run pytest --collect-only -q -p no:cacheprovider` sobre el archivo del change y sobre el repo entero (colecta propia, no ejecuta tests) | Archivo: `243 tests collected`, coincide con el `243 passed` del constructor. Repo: `4936 tests collected`, que son los 4934 de verify 1 más 2 |
| 00:53:21 | `curl` a `/actions/runs?head_sha=1d090f6f...` | HTTP 200, `total_count 1`: run `41767075030`, `CI`, `pull_request`, rama `change/ejemplo-robusto`, PR `[7]`, `completed/success`, `run_attempt 1`, de 03:25:50Z a 03:49:14Z |
| 00:54 | `curl` a `/actions/runs/41767075030/jobs` | `total_count 5`. Todos `completed/success` sobre `1d090f6`: `shellcheck`, `humo`, `web` (Lint, Tipos, Tests, navegador real y Canario), `backend` (Lint, Formato, Tipos, "Tests (incluye integración contra PostgreSQL real)" y Canario) y `secretos` (gitleaks). Ningún paso `skipped` ni `cancelled` |
| 00:55 | Lectura de `ci.yml` e `infra/ci/test-backend.sh` | El paso de tests corre `bash infra/ci/test-backend.sh` sin argumentos, es decir `uv run pytest` sin filtro. `addopts` sólo agrega `--strict-markers`. `push` se dispara sólo en `main`, así que la única corrida posible sobre la rama es la del PR (L-042) |
| 00:55 | `git diff --name-only 1d090f6...origin/main` | En `main` sólo cambió documentación (`AGENTS.md`, `CHANGES.md`, `CLAUDE.md`, `knowledge-base/*`) |

## JUICIO

Autor: el auditor. Comparé B1 y B2 de mi verify 1 contra los informes nuevos, el diff y el CI.

**B1 queda levantado. Confianza alta.**
- `verify-2-breaker.md` atacó `7110aac` con las tres lentes. Su `ejemplo.py` y su test tienen los hashes que yo había dado como entregados.
- Usó mutantes distintos de los del constructor y llegó a los consumidores: `cargador_yaml.py`, `semilla.py`, `errores.py`, el caso `ejemplo` de `test_arranque_tablas_protegidas.py` y el comando real dentro y fuera de desarrollo.
- Aportó evidencia nueva: Ctrl-C a mitad de la carga con la base real no deja filas.
- No hay fallas de producción. F10 y F11 son mutantes sobrevivientes: los reprodujo, cada uno con un test propio que lo mata.
- El grupo 10 los cerró por TDD, con RED en la aserción (`3 == 9` y `3 == 2`) bajo los mismos mutantes, GREEN y restauración por `git hash-object`.
- `verify-3-breaker.md` confirmó el cierre sobre `5fd45c0` con B7, B4 y una variante de cada uno.
- Después de `7110aac` no cambió producción.
- La cobertura afirmada coincide con lo examinado. Mi colecta da los mismos 243 y la misma diferencia de +2.

**B2 queda levantado. Confianza alta. El conteo que falta no bloquea.**
- Hay una sola corrida sobre el SHA de la cabeza, del evento `pull_request`, verde en los cinco jobs que define `ci.yml`. Lo leí yo, no lo heredé.
- L-055 pide pegar `N passed` para descartar que la "suite completa" sea una selección. Acá ese riesgo lo descarta la definición del paso: el script corre `pytest` sin argumentos, y un `success` exige código 0. Con un solo test fallido, o con cero tests colectados (código 5), el paso habría dado `failure`.
- El riesgo de L-064 (tests estructurales que una selección no ve) queda cubierto por esa corrida entera.
- Lo que el conteo agregaría es comparar contra los ~4936 esperados, para detectar un salto masivo. Es un hueco de evidencia menor, con un dueño que lo cierra fácil (DE-13), no un defecto.
- Lint, formato y `mypy` del árbol entero, que en verify 1 estaban vencidos, también quedan cubiertos por el job `backend`.

**O6 y S5 no se reprodujeron y no los promuevo a hallazgos.**
- **O6**: el doble repite el formato del mensaje de `cargador_yaml.py`. La ruta de parámetros la fija quien despliega, no la tipea el usuario. Queda como deuda (DE-11).
- **S5**: Ctrl-C durante el segundo de imports deja traceback, pero no escribe nada ni muestra datos. Lo sumo a DE-4, la deuda de sospechas que piden Linux.
- **O7** quedó corregido, y la cita de D5 también. El rompedor 3 los verificó.
- La disposición del orquestador en `tasks.md:301` coincide con esto.

**El conteo de intentos tiene una inconsistencia de registro. No bloquea.**
- `tasks.md:13` cuenta resultados no aprobados de toda la etapa verify: rompedor 1 y auditor 1 suman dos, y dice que con un tercero se frena.
- Con esa misma cuenta, `verify-2-breaker.md`, que reprodujo F10 y F11, fue el tercero. `tasks.md:15` reabrió el grupo 10 sin decirlo y sin una respuesta escrita nueva de Giuliano.
- La regla global habla de "tres intentos fallidos **en una gate**". Contando por gate, el rompedor tiene 2 fallidos y 1 limpio, y el auditor tiene 1 fallido y este. Ninguna gate llegó a tres, así que no hay una violación demostrada.
- Además, la decisión escrita de Giuliano (línea 14) pidió justo esa vuelta del rompedor, y la corrección fue sólo de tests.
- Lo que falta es que el registro diga qué cuenta usa y la aplique de forma coherente. Lo corrige el orquestador antes de archivar.

**`LEEME.md`, sección "Faltan", quedó vieja.** Dice que el rompedor 2 no corre y que el CI no existe. No es un informe original, pero el índice tiene que reflejar el estado real antes de archivar. Lo corrige el orquestador.

**Lo de verify 1 sigue en pie.** No hay duplicación ni código crítico tocado sin pedido, y LOW se sostiene. El push sin APROBADO quedó registrado como excepción escrita de Giuliano (`tasks.md:14`), sin merge. No lo cuento como aprobación de nadie.

## SUPOSICIÓN

- **Ejecución**: no corrí ningún test, sólo la colecta. F10 y F11 cerrados, el `243 passed` y las corridas bajo mutantes son evidencia de otros roles. Comprobé su coherencia (hashes, diff y conteo de colecta), no su ejecución.
- **Merge sintético**: en `pull_request`, `actions/checkout` toma el merge sintético con `main`. Los tests corrieron sobre `1d090f6` más los commits de `main`, que son sólo de documentación. El `head_sha` del run es el SHA de origen, como pide la regla.
- **Conteo**: no leí el `N passed` del CI. Los logs piden login y quedaba poco límite de la API: `X-RateLimit-Remaining 41` después de la primera consulta.
- **Skips**: no puedo descartar que haya tests marcados `skip` en Linux. El conteo lo diría (DE-13).
- **Zona horaria**: `date` no mostró la zona. Asumo -03:00, coherente con los horarios Z del run.

## Chequeos no ejecutados

- Ningún test, ni focalizado ni completo (por el brief).
- No repetí los mutantes de los rompedores.
- Logs del CI (piden login).
- Nada en Linux.

## Integridad

No modifiqué archivos del repo. Los JSON de la API quedaron en `C:\Users\espej\AppData\Local\Temp\claude\56b680c42cc5a2e7\19e1c5b0-3037-4aa8-9599-2cf049059770\scratchpad\runs.json` y `jobs.json`. No hice commit ni push, y no comenté en el PR.

## VEREDICTO

**APROBADO**

- **B1 levantado**: `verify-2-breaker.md` cubrió el grupo 9 y sus consumidores. F10 y F11 se cerraron por TDD (`apply-4-constructor.md`) y los confirmó `verify-3-breaker.md`. `git diff 7110aac 1d090f6 -- backend/src` está vacío.
- **B2 levantado**: el run `41767075030` sobre `1d090f6f79c6f3ed8ff7824ae629bda982f66424` es la única corrida sobre ese SHA, y sus cinco jobs están en `success`. Lo leí yo a las 00:53 y 00:54 del 04/11/2026. El paso de tests corre la suite sin filtro. `git diff 1d090f6 -- backend README.md` está vacío.
- No hay defectos de código abiertos. No hace falta ni existe aprobación humana HIGH o CRITICAL: el change es LOW.

Este APROBADO habilita sólo el cierre documental. No autoriza merge, otro push ni más alcance. Antes de archivar, el orquestador tiene que:

1. Guardar este informe tal cual en `informes/verify-2-auditor.md` e indexarlo en `LEEME.md`.
2. Actualizar la sección "Faltan" de `LEEME.md`: el rompedor 2 y 3 ya corrieron, el CI existe, y queda sólo el hueco del conteo.
3. Dejar escrito en `tasks.md` qué cuenta de intentos rige (por gate) y cómo queda cada gate: rompedor 2 fallidos y 1 limpio, auditor 1 fallido y 1 aprobado. Así se resuelve la contradicción entre `tasks.md:13` y `:15`.
4. Pushear esas anotaciones. Como son sólo documentación, invalidan el CI de `1d090f6` sólo como evidencia del SHA nuevo: el SHA que se mergee necesita su propio CI verde, leído por run.

### DEUDA

| # | Deuda | Origen | Destino |
|---|---|---|---|
| DE-1 | La comparación no mira `pisos`, `subsuelos`, la ubicación ni `activo` de un grupo (O2) | `verify-1-breaker.md` | Próximo change que toque `ejemplo.py`; anotarla en la ficha 3f |
| DE-2 | `acceso/aplicacion/alta_inicial.py`, el gemelo: traceback y exigencia de Redis (L-009) | `propose-1-plan-reviewer.md`, PR-9 | Primer change que toque `alta_inicial.py`, con su propia clasificación |
| DE-3 | O1: un error de uso fuera de desarrollo da 2. Es previo al change y se documenta como interpretación de D-112 | `propose-3-plan-reviewer.md`; `9649471:ejemplo.py:432-436` | Decisión de cierre (D-145 o la próxima libre), que la nombre para que Juani la ratifique o la cambie |
| DE-4 | Sin reproducir: S1 (límite de conexión), S2 (`print` con la salida cerrada), S4 (parámetros sin permiso de lectura) y S5 (Ctrl-C durante los imports deja traceback, sin escribir ni mostrar datos) | `verify-1-breaker.md`; `verify-2-breaker.md` | Próximo change que toque `ejemplo.py`, con una corrida en Linux y una señal real |
| DE-5 | S3: `--semilla` con un archivo especial puede agotar la memoria antes del tope de 1 MiB | `verify-1-breaker.md` | Primer change que toque `compartido/cargador_yaml.py` |
| DE-6 | `Conflicto` sigue en el 9 sin reproducir; base lenta sin `statement_timeout` (L-001) | D10; `proposal.md` | Próximo change que toque `ejemplo.py` |
| DE-7 | Los validadores del pool y del archivo de parámetros viven en dos lectores | D5 | Próximo change que toque `compartido/configuracion.py` |
| DE-8 | Todos los roles son de la familia Claude; el proyecto no declara `## Role executors` (L-025) | `verify-1-auditor.md`, hueco 5 | C-28 `revisiones-independientes` |
| DE-9 | Fallas de Windows que D-110 no nombra; `mypy` de Windows con 2 errores en `test_respaldos.py:554` | `apply-1-constructor.md`, H-7 | Ficha 3b-bis al cierre; la parte de `respaldos`, a C-24 |
| DE-10 | CRLF de `infra/respaldos/*.sh` en Windows, sin `.gitattributes` | `proposal.md`; `propose-2-plan-reviewer.md` | C-24 `respaldos-2` |
| DE-11 | O6: el gemelo de parámetros de F1 se prueba con un doble que repite el formato de `leer_archivo`. Si ese texto cambia, la ruta de `PROPTECH_PARAMETROS` saldría entera sin que ningún test lo note. Sin reproducir por el camino real | `verify-2-breaker.md`, O6 | Primer change que toque `cargador_yaml.py` o `ejemplo.py`: un caso real con `chmod 000` en Linux, o un test que lea el mensaje del propio lector |
| DE-12 | Conteo `N passed` del run `41767075030` sin leer (los logs piden login) | `tasks.md` 8.1; este informe | Giuliano o quien tenga login: pegar el conteo desde la página del run en 8.1 al archivar. Si no se puede, queda declarado; no bloquea, ver JUICIO |

### LECCIONES

Propuestas para `knowledge-base/15_lecciones.md` (sólo se agrega), con el número que corresponda al cerrar. Siguen en pie L-068, L-069 y L-070 de `verify-1-auditor.md`. La L-070 se confirmó en este change: el rompedor acotado al delta encontró dos huecos reales en minutos, y el CI del PR resolvió la suite sin la corrida local de más de una hora. Agrego dos:

- **L-071 · Sin login, el CI verde se certifica por la definición del paso y su conclusión; el conteo es un complemento.** Origen: C-27, B2 de verify 1 y 8.1 (04/11/2026). Qué pasó: la API pública de GitHub da la conclusión de cada paso pero no sus logs, y `gh` no estaba instalado, así que el `N passed` que pide L-055 no se pudo leer. Regla: el run sobre el SHA de origen, con su paso de tests leído en `ci.yml` y en el script que llama (sin filtro de archivo ni de `-k`) y en `success`, certifica la suite entera. El conteo se pide aparte a quien tenga login y se declara como hueco si falta; no se inventa ni se da por leído. Aplica a orquestador y auditor.
- **L-072 · La cuenta de intentos se declara por gate y se aplica en cada vuelta.** Origen: C-27, `tasks.md:13` y `:15` (03/11/2026). Qué pasó: el registro contó los resultados no aprobados de toda la etapa verify ("con un tercero se frena"), y en la vuelta siguiente reabrió el grupo 10 sin aplicar esa misma cuenta. Contada por gate, como dice la regla global, nadie llegó a tres. Regla: `tasks.md` dice qué cuenta usa (por gate: rompedor y auditor por separado) y, en cada resultado no aprobado, anota el número de esa gate. Así la frenada en el tercero no depende de una interpretación hecha a posteriori. Aplica al orquestador.
