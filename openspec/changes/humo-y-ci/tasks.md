> Dónde se verifica cada tarea: **[WSL]** en el clon Linux (`~/proptech`, rama de prueba traída con
> `git fetch /mnt/c/Proyectos/proptech change/humo-y-ci:refs/heads/prueba-humo-y-ci --force`);
> **[GH]** sólo en un run de GitHub Actions, no se puede verificar local. Los tests de infra, humo y bash
> **no** se corren en Windows. TDD: en cada tarea el test se ve fallar (con el defecto puesto, copia
> previa y diff real, L-013) antes de escribir el arreglo, y se pega rojo y verde en este archivo.
> Commits en español, conventional commits, sin `Co-Authored-By` ni atribución a IA. Sin push ni PR sin
> OK de Gianfranco.

## 1. Baseline y medición

- [ ] 1.1 [WSL] Baseline de integración sobre `origin/main` `60b3dd5` (`test-backend.sh -m integracion`):
  anotar pasados, fallidos (nombres) y duración, y verificar que `docker ps` queda igual que antes
- [ ] 1.2 [WSL] Baseline del resto: `pytest backend/tests/infra`, unitarios, `shellcheck infra/ci/*.sh` y
  tiempo de la suite completa en serie; anotar los números como línea de base del 9.3
- [ ] 1.3 [WSL] Baseline del humo y del ensayo de roles, cada uno en su proyecto (`proptech-humo-base`,
  `proptech-ensayo-base`), con la salida real pegada y los pasos que tardan más

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
- [ ] 9.3 Backend en paralelo: `pytest-xdist` en `uv.lock`, marcador `serial` registrado, `test-backend.sh`
  con `-n`, unitarios y de integración como pasos separados; [WSL] mismos tests pasados que en serie y
  tiempo antes y después (los de 1.2), pico de memoria; [GH] el tiempo en el runner
- [ ] 9.4 Caché de Chromium en el job `web`; test estático de la clave y del paso; [GH] dos runs
  seguidos, el segundo con caché, con los tiempos por paso (L-044); ajustar `timeout-minutes` sólo con
  esos tiempos
- [ ] 9.5 `.github/dependabot.yml` con los cuatro ecosistemas y test estático de directorios; [GH] que
  Dependabot abra su primer PR (no verificable antes de pushear)
- [ ] 9.6 [GH, condicional] `.gitleaksignore`: si el PR #4 se rebasó, quitar la línea de `a6bb954` y
  ver `secretos` en verde; si no, anotarlo como deuda (pregunta abierta 1)

## 10. Cierre

- [ ] 10.1 [WSL] Corrida final sobre el código final (L-010): `pytest` completo (infra, unitarios,
  integración), `shellcheck`, `humo.sh` y `ensayo-roles.sh` en proyectos aislados; pegar la salida y
  comparar con el baseline de 1.1 a 1.3
- [ ] 10.2 Rompedor (sólo tests, nunca código) y auditor sobre el diff, con L-043, L-044 y L-047 a mano;
  hallazgos como tests rojos
- [ ] 10.3 Knowledge Base Impact: `CHANGES.md` (C-23 `[x]`), ficha 2e, filas cerradas de "Deuda del
  cierre del 2c", decisión nueva en `09`, lecciones en `15`; `diff AGENTS.md CLAUDE.md` vacío y sin
  tocar ninguno de los dos
- [ ] 10.4 [GH] Con el OK de Gianfranco: push y PR; leer el run completo sobre el SHA antes de decir
  "listo" (L-037, L-042)
