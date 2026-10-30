> Dónde se verifica cada tarea: **[WSL]** en el clon Linux (`~/proptech`, rama de prueba traída con
> `git fetch /mnt/c/Proyectos/proptech change/humo-y-ci:refs/heads/prueba-humo-y-ci --force`);
> **[GH]** sólo en un run de GitHub Actions, no se puede verificar local. Los tests de infra, humo y bash
> **no** se corren en Windows. TDD: en cada tarea el test se ve fallar (con el defecto puesto, copia
> previa y diff real, L-013) antes de escribir el arreglo, y se pega rojo y verde en este archivo.
> Commits en español, conventional commits, sin `Co-Authored-By` ni atribución a IA. Sin push ni PR sin
> OK de Gianfranco.

## 1. Baseline y medición

- [x] 1.1 [WSL] Baseline de integración sobre `origin/main` `60b3dd5` (`test-backend.sh -m integracion`):
  anotar pasados, fallidos (nombres) y duración, y verificar que `docker ps` queda igual que antes
  - **1833 pasados, 1 xfail, 0 fallidos, 18 min 41 s, exit 0**, 2446 deseleccionados. Sin contenedores
    sobrantes (`docker ps` vacío antes y después).
- [x] 1.2 [WSL] Baseline del resto: `pytest backend/tests/infra`, unitarios, `shellcheck infra/ci/*.sh` y
  tiempo de la suite completa en serie; anotar los números como línea de base del 9.3
  - Sobre `60b3dd5`, `-m "not integracion"` en serie: **2446 pasados, 94,6 s, exit 0**;
    `shellcheck -x infra/ci/*.sh` exit 0. Suite completa en serie = 94,6 s + 18 min 41 s ≈ 20 min 20 s.
- [x] 1.3 [WSL] Baseline del humo y del ensayo de roles, cada uno en su proyecto (`proptech-humo-base`,
  `proptech-ensayo-base`), con la salida real pegada y los pasos que tardan más
  - **Desvío**: el humo de `main` no se puede aislar (`-p proptech` escrito en el script, el defecto
    que arregla este change), así que corrió en el proyecto `proptech` con Docker vacío: `humo_exit=0`,
    **181 s**. El ensayo, en `proptech-ensayo-base`: `ENSAYO ROLES OK ... ciclo 0028/0016/0028`,
    `ensayo_exit=0`, **47 s**. El humo no imprime tiempos por paso; no se midieron.
  - Primer intento: el humo cayó a los 7 s por el error transitorio de BuildKit "parent snapshot does not
    exist" y el ensayo por falta de `infra/.env` en el clon (archivo ignorado por git, copiado). Se
    repitieron ambos; los números de arriba son los de la repetición.

## 2. `humo.sh` en un proyecto aislado (L-047)

- [x] 2.1 Test estático rojo: `humo.sh` sin `-p proptech` literal, con `PROPTECH_COMPOSE_PROYECTO`
  exportada; verde al cambiar `compose()` y el resto de los usos del script (reemplaza
  `test_toda_invocacion_de_docker_compose_lleva_p_proptech`, que fijaba lo contrario)
- [x] 2.2 Test rojo y verde de la restauración: una copia del humo que no exporta la variable llama a
  `restaurar.sh` sobre `proptech` (error real de `humo.sh:741`); con la variable exportada opera sobre el
  proyecto del humo. Se explica en el PR qué proyecto habría restaurado [WSL para verlo con Docker]
- [x] 2.3 Tests rojos y verdes del rechazo previo, uno por caso, sin ejecutar ningún `up` ni `down`:
  (a) sin variable, (b) `proptech` con contenedores corriendo, (c) puerto 80 o 443 ocupado; cada
  mensaje nombra la causa y cómo correrlo [WSL, con un stack `proptech` descartable y un puerto 80
  ocupado a propósito]
- [x] 2.4 El job `humo` del CI exporta su proyecto; `README` y `test_readme_variables.py` incluyen la
  variable y el rechazo; `test_ci_workflow.py` lo fija
> Evidencia grupo 2 [WSL, `~/apply-humo`, 30/10/2026]: rojo `6 failed, 5 passed` en
> `test_humo_aislamiento.py` antes del código; verde `43 passed` (humo, aislamiento, pasos, ci_workflow,
> readme, ensayo_login) y `ruff`/`mypy`/`shellcheck` limpios después. Con Docker real: sin variable,
> `proptech` con un contenedor etiquetado corriendo y puerto ocupado terminan con código 1 y mensaje
> propio, sin tocar nada. Baseline de integración de `origin/main` `60b3dd5`: `1833 passed, 2446
> deselected, 1 xfailed`, 0 fallos, 18 min 41 s.

- [ ] 2.5 Anotar la deuda "humo en paralelo con un stack real" (puertos y red fijos de
  `infra/compose.yaml`, `:22`, `:191`, `:368-375`) en la ficha 2e al cerrar

## 3. Pasos con línea y comando (C2-5, C2V2-8)

- [x] 3.1 Test de bash rojo: un script mínimo con `exit 1` explícito no nombra paso, línea ni comando;
  verde con `fallar_paso` en `pasos.sh`
- [x] 3.2 Test estático rojo que recorre `humo.sh` y señala cada `exit 1`/`if !` sin pasar por el
  formateador; verde al convertir los 25 caminos
- [x] 3.3 `compose()` informa la línea del llamado: test rojo con `BASH_LINENO[0]`, verde al arreglar
- [x] 3.4 [WSL] `humo.sh` entero en verde y una falla provocada que muestra paso, línea y comando

> Evidencia grupo 3 [WSL, 30/10/2026]: rojo `3 failed, 6 passed` en `test_pasos_humo.py` antes del
> código; verde `34 passed` (pasos, humo, aislamiento, ci_workflow), `shellcheck` y `ruff` limpios.
> Humo real en `proptech-humo-g3`: `humo_exit=0` (3 min 28 s). El primer intento cayó por un error
> transitorio de caché de BuildKit y mostró el formato nuevo: `paso 0 ... falló en la línea 77:
> docker compose -p "$PROPTECH_COMPOSE_PROYECTO" ... (llamado desde la línea 132)`. Los 22 `exit 1` de
> los pasos pasan por `fallar_paso` con su condición; el único `exit 1` fuera es el de `rechazar`.

## 4. Lo que el humo deja pasar

- [x] 4.1 C2V2-7: test estático rojo (noveno servicio en una copia de `compose.yaml` sin capacidades
  declaradas); verde con la lista derivada de `compose config --services`
- [x] 4.2 N9: test estático rojo que prohíbe `init: true` (hoy ningún servicio lo declara); nota en el
  humo; [WSL] mutante: agregarlo a `db` en una copia y ver el rojo del PID 1 de `db`
- [x] 4.3 C2-7: test de bash con un volcado que aparece a los 3 s (rojo con el conteo de hoy, verde
  con `esperar_dumps`); corregir el comentario falso de `humo.sh`
- [x] 4.4 N-a: tests de bash del verificador de cabeceras con fixtures (duplicado, valor con texto
  de más, valor bueno); rojos con el verificador de hoy, verdes con el nuevo

## 5. RLS restaurada por contenido (C2V2-3)

- [x] 5.1 Test que arma dos salidas de políticas (misma cantidad, `USING (true)` en una; nombre
  distinto en otra) y comprueba que la comparación las rechaza; rojo con el `count(*)` de hoy
- [x] 5.2 [WSL] En el humo real: mutante que debilita una política de la restaurada con la misma cantidad
  y ve el rojo nombrando tabla y política; restaurar y ver el verde

## 6. Caddy

- [x] 6.1 C2V2-6: test estático de `respond 421` en `:80` y paso del humo con los ocho métodos; [WSL]
  rojo con una copia del `Caddyfile` que responde 404
- [x] 6.2 C2V2-1: test estático que fija "sin `:443` ni HSTS" con mensaje que remite a la declaración;
  la declaración queda en el spec archivado al cerrar
- [x] 6.3 N2: timeouts de `reverse_proxy`; paso del humo que pausa `api` y mide que llega 502 o 504 antes
  del plazo más 5 s; [WSL] rojo sin los timeouts (los 100 s de hoy), verde con ellos; decidir y anotar
  los valores con la medición

## 7. `arranque_fallido` completo (C2-8)

- [x] 7.1 Tests rojos de la API con un puerto cerrado y con un `parametros.yaml` roto: línea
  `arranque_fallido` con causa, sin contraseña ni cadena de conexión; proceso distinto de 0
- [x] 7.2 Cambio mínimo en `proptech_api/app.py` hasta el verde; `mypy` y `ruff` limpios [WSL]
- [x] 7.3 Anotar si el worker tiene el mismo hueco (pregunta abierta 2); si lo tiene, ficha de deuda
  - Nota: `proptech_worker/ajustes.py:151,217` ya emite `arranque_fallido` con `str(error)` para otros
    fallos de arranque; no se verificó si un YAML roto o una base inalcanzable lo evitan. Queda como deuda
    para la ficha 2e (paridad del worker), sin tocar el worker en este change.

## 8. Tests del log (C2V2-2, N-b)

- [x] 8.1 Tests rojos: `WARNING` con el valor en otro logger pasa desapercibido; un campo con "123" da
  rojo falso con `valor=123`
  - Rojo (L-013): con `logging.getLogger("otro.fuga").warning("recibido", extra={"x": valor})` puesto en
    `_administracion_validada`, el test viejo de `test_worker_tenant.py` daba `10 passed` (el hueco);
    `test_registros_del_log.py` falló por `ModuleNotFoundError: tests._registros_del_log` hasta escribir el helper.
- [x] 8.2 Helper y comparación por igualdad de valor hasta el verde; el rompedor repite los dos
  mutantes con copia previa
  - `tests/_registros_del_log.py` (`capturar_todo`, `fugas_del_valor`): 5 tests verdes. Con el mismo
    mutante, el test nuevo da `4 failed, 6 passed` (los cuatro valores no triviales); código restaurado
    desde copia previa (`git diff -- backend/src` vacío). `ruff`, `format` y `mypy` limpios [WSL].
  - Decisión: la comparación es por hoja igual al valor o palabra aparte en el texto
    (`(?<![\w.])123(?![\w.])`), no igualdad estricta, para seguir viendo `valor=123` dentro de un texto.

## 9. CI

- [x] 9.1 L-043: `ensayo-roles.sh` con la cabeza de `alembic heads`; `test_ensayo_login.py` pasa a
  exigir que no haya literal de revisión; [WSL] el ensayo entero corrido en `proptech-ensayo` con la
  salida pegada, y el mutante de una migración nueva falsa que lo deja viejo en el script de hoy
  - Rojo: 4 tests fallaron contra el script viejo (cabeza escrita, `0028`/`0016` sueltos, mensaje fijo).
  - Verde [WSL], proyecto `proptech-ensayo-91`, 48 s: `REVISION RESTAURADA: 0028`, `0016`, `0028` y
    `ENSAYO ROLES OK: respaldo restaurado, 10 asignaciones, ciclo 0028/0016/0028 y origen intacto`,
    `ensayo_exit=0`.
  - Mutante (migración `0029_falsa` vacía sobre `0028`): script nuevo `ciclo 0029/0016/0029`,
    `ensayo_exit=0`; script de `HEAD` en la misma copia: `ERROR: revisión restaurada esperada=0028
    obtenida=0029`, `ensayo_exit=1`. Las dos corridas en copia congelada `~/ensayo-run`.
  - `REVISION_DE_ORIGEN="0016"` es el único número escrito a mano; `shellcheck -x infra/ci/*.sh` limpio.
- [~] 9.2 Job `ensayo-roles` en `ci.yml` con `timeout-minutes`, SHAs fijados y `test_ci_workflow.py`
  actualizado; [GH] el run del job leído sobre el SHA del PR
  - Hecho: job con `PROPTECH_COMPOSE_PROYECTO: proptech-ensayo`, checkout fijado por SHA,
    `timeout-minutes: 20` provisorio (el ensayo tardó 48 s en WSL), 2 tests nuevos/ajustados (rojo
    visto antes: 3 fallos). **Pendiente [GH]**: leer el run real y ajustar el timeout con ese tiempo.
- [~] 9.3 Backend en paralelo: `pytest-xdist` en `uv.lock`, marcador `serial` registrado, `test-backend.sh`
  con `-n`, unitarios y de integración como pasos separados; [WSL] mismos tests pasados que en serie y
  tiempo antes y después (los de 1.2), pico de memoria; [GH] el tiempo en el runner
  - `pytest-xdist==3.8.0` (+ `execnet`) en el grupo `dev`; `uv.lock` conserva `revision = 3` (uv 0.13.6 de
    WSL lo subía a 5; `uv lock --check` y `uv sync --locked` pasan con 3). Marcador `serial(reason)`
    registrado; ningún test lo necesita hoy, y `test_backend_paralelo.py` exige que, si alguien marca
    uno, tenga `reason=` y un paso propio con `-p no:xdist`.
  - CI: dos pasos, `-m "not integracion and not serial" -n 4` y `-m "integracion and not serial" -n 4`
    (`test-backend.sh` ya reenviaba los argumentos). 4 = los 4 vCPU del runner; nunca `auto`.
  - Medición [WSL, 20 núcleos, 15 GB; el runner tiene 4 vCPU, así que el tiempo del runner puede ser
    mayor]: no integración, mismo árbol, **serie 102,6 s / `-n 4` 51,0 s, 2500 pasados en ambos**
    (baseline en `main`: 2446 en 94,6 s, shellcheck 0). Integración **serie 18 min 41 s (1833 pasados,
    baseline en `main`) / `-n 4` 8 min 41 s (1833 pasados, 1 xfail)**, sin contenedores sobrantes; pico
    de memoria usada del sistema 4.235 MB.
  - Lo que la medición encontró (los fixtures de sesión por proceso NO bastaron, contra D11):
    1. Tres tests de `test_salud_cola_real.py` dependían del orden: usaban la base de sesión sin pedir
       `esquema_migrado`; en un worker donde corrían primero fallaban con `TablasDeSoloAgregarDesprotegidas`.
       Rojo en serie con el archivo solo (`3 failed`), verde al pedir el fixture.
    2. Carrera de arranque: `roles antes` recibía `Connection refused` cuando Postgres aún no aceptaba
       conexiones (uno de cada ~3 corridas con 4 workers sobre 4 archivos; antes, 1 en 6 corridas
       completas daba 42 errores). `conftest.py` ahora espera con `esperar_postgres` (conecta de verdad,
       30 s, y si vence dice estado y últimas líneas del contenedor); 7 corridas seguidas en verde.
       `roles_reales` y `test_rutas_protegidas._correr` dejan stdout/stderr en el fallo (antes un
       `CalledProcessError` mudo). Los Postgres propios de módulo (`contenedor` de varios archivos) no
       usan todavía la espera: deuda anotada si reaparece.
    3. Colección no determinista: `test_falla_con_marca_en_el_futuro` tenía un parámetro calculado con la
       hora (`999999999999 - int(time.time())`) y su valor era el id; con xdist cada trabajador veía un
       id distinto y abortaba con `Different tests were collected between gw0 and gw3` cuando el reloj
       cambiaba de segundo entre colecciones (visto 1 vez en 8 corridas). Rojo:
       `test_coleccion_determinista.py` (`primera != segunda`, ids `[998206606093]` vs `...131]`); verde
       con `pytest.param(..., id=...)`. Colección de unitarios (2506) e integración (1834) idéntica con
       tres semillas de hash y el reloj corriendo.
  - **Pendiente [GH]**: tiempo en el runner de 4 vCPU.
- [~] 9.4 Caché de Chromium en el job `web`; test estático de la clave y del paso; [GH] dos runs
  seguidos, el segundo con caché, con los tiempos por paso (L-044); ajustar `timeout-minutes` sólo con
  esos tiempos
  - Hecho: paso `actions/cache@27d5ce7…` (v5.0.5, SHA resuelto con `git ls-remote`) sobre
    `~/.cache/ms-playwright`, clave `playwright-${{ runner.os }}-${{ hashFiles('web/pnpm-lock.yaml') }}`,
    antes de la instalación (que sigue corriendo y pasa igual sin caché). Test estático nuevo.
    **Pendiente [GH]**: dos runs seguidos con sus tiempos; `timeout-minutes: 25` no se toca.
- [~] 9.5 `.github/dependabot.yml` con los cuatro ecosistemas y test estático de directorios; [GH] que
  Dependabot abra su primer PR (no verificable antes de pushear)
  - Hecho: `github-actions /`, `docker /backend` y `/web`, `uv /backend`, `npm /web`, semanal, tope de PR
    por ecosistema, agrupados. **Desvío de D13**: las imágenes de `infra/compose.yaml` van con el
    ecosistema `docker-compose` en `/infra`, no `docker` (que sólo lee Dockerfile; confirmado en la
    referencia de opciones de Dependabot). Si Dependabot reconoce `compose.yaml` (no `docker-compose.yml`)
    sólo se ve en GitHub. Test estático con rojo visto (archivo ausente → 4 fallos).
- [x] 9.6 [GH, condicional] `.gitleaksignore`: si el PR #4 se rebasó, quitar la línea de `a6bb954` y
  ver `secretos` en verde; si no, anotarlo como deuda (pregunta abierta 1)
  - **No se rebasó**: `git merge-base --is-ancestor a6bb954 origin/change/gastos-y-cargos` dice que el
    commit sigue en la rama (cabeza `5b10687`). La línea queda en `.gitleaksignore` y se anota como deuda
    en la ficha 2e: quitarla cuando se rebase el PR #4 (ver 10.3).

## 10. Cierre

- [x] 10.1 [WSL] Corrida final sobre el código final (L-010): `pytest` completo (infra, unitarios,
  integración), `shellcheck`, `humo.sh` y `ensayo-roles.sh` en proyectos aislados; pegar la salida y
  comparar con el baseline de 1.1 a 1.3
  - Por el camino prescrito (`git fetch /mnt/c/Proyectos/proptech change/humo-y-ci:refs/heads/prueba-humo-y-ci`,
    clon `~/proptech`), con los comandos del CI, Docker vacío antes y después:
    integración `-n 4`: **1833 pasados, 1 xfail, 0 fallidos, 7 min 9 s** (baseline 1833 / 18 min 41 s);
    `shellcheck -x infra/ci/*.sh` exit 0; humo en `proptech-humo` `humo_exit=0` 222 s (baseline 181 s, con
    pasos nuevos: 6c pausa 2×30 s); ensayo en `proptech-ensayo` `ENSAYO ROLES OK ... ciclo 0028/0016/0028`,
    `ensayo_exit=0` 48 s (baseline 47 s).
  - Unitarios e infra `-n 4`: la primera corrida dio `1 failed, 2504 passed`: `test_vocabulario_vigente`
    (el vocabulario retirado en una variable de `test_caddy_respaldo_y_timeouts.py`; sólo mira lo
    versionado, por eso no lo vio la corrida sobre el árbol sin commitear: L-010). Corregido; luego
    `2505 passed` tres veces seguidas, y `2506` con el test de colección nuevo.
- [~] 10.2 Rompedor (sólo tests, nunca código) y auditor sobre el diff, con L-043, L-044 y L-047 a mano;
  hallazgos como tests rojos
  - **Rompedor, ronda 1** (clon `~/rompedor`, parche en el scratchpad): 9 tests rojos y 5 mutantes que los
    tests del constructor no detectaban. Resueltos (tests integrados en `test_rompedor_humo_y_ci.py` y
    `test_rompedor_log_y_arranque.py`, 69 verdes junto a los del constructor, shellcheck limpio, humo real
    `humo_exit=0` con la verificación nueva):
    - R3: el bucle de los ocho métodos ahora verifica las cabeceras de seguridad de cada respuesta.
    - R4: dos pasos se llamaban `6c`; el de las pausas pasa a `6d`.
    - R5: `fallar_paso` dentro de un helper informa también "llamado desde la línea N" (cadena de `BASH_LINENO`).
    - R8/R9: el helper del log ve una fuga seguida de punto y la que sale por un logger con `propagate=False`.
    - R6, R7, M1, M2: tests que matan los mutantes (timeouts en todo `reverse_proxy`, cualquier sitio `https://`
      o `:443`, el 443 en los puertos por defecto, política que sobra en la restaurada).
  - **Abiertos, esperan decisión de Gianfranco** (los tests están en `scratchpad/rompedor/pendientes-de-decision.txt`
    y NO entraron al repo para no dejar el CI en rojo):
    - R1 (ALTA): el rechazo (b) mira `docker ps -q` (sólo corriendo). Con el stack `proptech` DETENIDO y sus
      volúmenes vivos, el humo con `PROPTECH_COMPOSE_PROYECTO=proptech` pasa el rechazo y su `down -v` borra los
      volúmenes. La spec aprobada dice "con contenedores corriendo": endurecerla cambia lo aprobado.
    - R2 (ALTA): `ensayo-roles.sh` (ahora en el CI) conserva `:-proptech` por defecto y no tiene los tres rechazos.
    - R10: el worker no deja `arranque_fallido` ante un YAML roto ni una base inalcanzable (verifica la 7.3).
  - Auditor: pendiente.
- [ ] 10.3 Knowledge Base Impact: `CHANGES.md` (C-23 `[x]`), ficha 2e, filas cerradas de "Deuda del
  cierre del 2c", decisión nueva en `09`, lecciones en `15`; `diff AGENTS.md CLAUDE.md` vacío y sin
  tocar ninguno de los dos
- [ ] 10.4 [GH] Con el OK de Gianfranco: push y PR; leer el run completo sobre el SHA antes de decir
  "listo" (L-037, L-042)
