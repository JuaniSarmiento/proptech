Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el rojo
se anota en el informe con el comando, su salida y la hora. "Verde" en la web es `pnpm biome ci`, `pnpm
tsc --noEmit` y `bash infra/ci/test-web.sh`; en el backend, `bash infra/ci/test-backend.sh` sobre los
archivos tocados (L-005). Cada tarea nombra los escenarios que cubre.

**NO CONSTRUIR**: todo el change es **HIGH** (y la tarea 1.0, además, necesita un `GRANT` **CRITICAL**
sobre `auditoria`). Precondición: la sección "Aprobación" de `proposal.md` firmada por Juani o Alberto,
con nombre, fecha y las dos respuestas. Si PR4 se responde distinto de lo propuesto en D12 del 3b, se
corrige antes de empezar. Movido del change `pantallas-del-edificio` (20/10/2026), grupo 7, sin cambiar
su contenido salvo la numeración.

## 1. Acceso de desarrollo sin login (HIGH): NO CONSTRUIR, espera la firma HIGH de Juani (D-094)

- [ ] 1.0 **Carga del edificio de ejemplo en la base** (bloqueada, ver nota; necesita además el
  `GRANT` CRITICAL). Carga del edificio de ejemplo en la base (la 7.2 del 3a, D9 del 3a, E6 y E10
  firmadas): comando `python -m proptech_core.complejos.aplicacion.ejemplo cargar`, como
  `proptech_migrador` con el tenant de la administración de ejemplo fijado a propósito, por los mismos
  casos de uso que la API, todo en una transacción. Tests contra PostgreSQL real, primero en rojo (el
  comando no existe): primera carga con 13 unidades y la auditoría de crear y confirmar; segunda carga
  igual sin cambios; segunda carga después de cambiar la tasa en `parametros.yaml` da "ya estaba"; dos
  cargas en paralelo dejan un solo ejemplo; con una unidad editada falla sin escribir y dice qué
  difiere; otra administración con datos queda idéntica (comparación fila por fila); sin tenant no
  escribe nada. Escenarios: `datos-semilla` › Primera carga; › Segunda carga igual; › Cambiar los
  parámetros no hace fallar la carga; › Dos cargas a la vez; › El ejemplo cambió en la base; › Otras
  administraciones no se tocan. Lecciones: L-006, L-016.
  - **Por qué está acá y no en el grupo 2 del 3b**: el constructor la frenó ahí porque
    `proptech_migrador` no tiene `GRANT` sobre `auditoria` (ownership pasa al rol de arranque en
    `roles.despues()`; sólo `proptech_app` recibe `SELECT, INSERT`,
    `src/proptech_core/compartido/roles.py:701-735`), y los casos de uso que D9/E10 pide reusar
    (`crear_edificio`, `confirmar_sin_saldos_previos`) auditan con `registrar()`, que exige `INSERT`.
    RED real contra Postgres: `psycopg.errors.InsufficientPrivilege: permission denied for table
    auditoria` (`uv run pytest tests/integracion/test_ejemplo_casos_de_uso.py -q` → `6 failed, 1
    passed`). Decisión del orquestador: el `GRANT INSERT ON auditoria TO proptech_migrador` es un
    cambio de permisos sobre el log de auditoría — **CRITICAL** — y la decide Juani junto con la firma
    de este grupo, no el constructor solo.
  - **Ninguno de los grupos 1 a 6 del 3b la importa ni la necesita**: las pantallas y la base de test
    de la web no leen nada de la administración de ejemplo; sólo el recorrido contra la API real de la
    1.3 depende de que esté cargada.
  - El trabajo (implementación + 7 tests, `ruff`/`mypy` limpios) está guardado sin commitear en
    `.git/informes-3b/2.3-wip/` (`ejemplo.py`, `test_ejemplo_casos_de_uso.py`) y el fixture
    `fabrica_migrador` como patch en `.git/informes-3b/2.3-wip.patch` (contra
    `backend/tests/integracion/conftest.py`). Se aplica recién junto con el `GRANT` firmado.
- [ ] 1.1 Las guardas, antes que el punto de entrada (D11 del 3a, D12 del 3b): tests en `tests/infra/`
  que fallan si la imagen del backend contiene `desarrollo`, si `compose.yaml` lo referencia, si algún
  archivo del repositorio pone `COMPOSE_FILE` con `desarrollo`, o si `humo.sh` llama a `docker compose`
  sin `-f compose.yaml`; y uno que verifica 401 sin identidad en la app de producción. Rojo de cada uno
  sobre una copia que lo viola (L-013). Escenarios: `acceso-de-desarrollo` › La imagen de producción; ›
  Producción sin identidad; › Un archivo que activa el override; › El humo sin archivo explícito.
  Lecciones: L-019, L-022.
- [ ] 1.2 El punto de entrada: `backend/desarrollo/app_de_desarrollo.py` (fuera de `src/`), que arma
  `crear_app()` y reemplaza la identidad con la del titular de ejemplo; se niega a arrancar sin la
  administración de ejemplo o con otra administración en la base (PR4); `infra/compose.desarrollo.yaml`
  que lo monta y publica la API sólo en `127.0.0.1`. Tests primero de las dos negativas. Escenarios:
  `acceso-de-desarrollo` › Base sin el ejemplo; › Base con otra administración. Lecciones: L-006,
  L-016.
- [ ] 1.3 Recorrido contra la API real: con el ejemplo cargado (1.0) y el acceso levantado, las siete
  pantallas del 3b en el navegador a 320 px y a 1280 px, con capturas y el recorrido de teclado, y la
  corrida de cierre del grupo (`test-backend.sh`, `humo.sh` y `test-web-navegador.sh`). Verificación: el
  informe trae las capturas, los comandos y su salida. Escenarios: `acceso-de-desarrollo` › Las
  pantallas contra la API real. Lecciones: L-010.
