Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el rojo
se anota en el informe con el comando, su salida y la hora. "Verde" en la web es `pnpm biome ci`, `pnpm
tsc --noEmit` y `bash infra/ci/test-web.sh`; en el backend, `bash infra/ci/test-backend.sh` sobre los
archivos tocados (L-005). Cada tarea nombra los escenarios que cubre.

**NO CONSTRUIR**: todo el change es **HIGH**. Precondición: la sección "Aprobación" de `proposal.md`
firmada por Juani o Alberto (desde D-111, también Emiliano), con nombre, fecha y la respuesta. Este `tasks.md` reemplaza por completo
la versión anterior (el punto de entrada sin login, sus guardas, y la carga del ejemplo como
`proptech_migrador` con `GRANT`): los tres quedan descartados por D11 del design de `login-y-usuarios`
(E12, firmada 21/10/2026). L-029 aplica: esa firma no cubre estas tareas reescritas, que necesitan la
suya propia.

## 1. Carga del ejemplo por el camino de D10 (HIGH): NO CONSTRUIR, espera la firma de Juani o Alberto (D-094)

- [x] 1.0 **Carga del edificio de ejemplo en la base, como `proptech_app`**: comando que reescribe
  `alta_inicial.py` (D10) para este caso — abre sesión con las credenciales de `proptech_app` (nunca
  `proptech_migrador`), fija el tenant de la administración de ejemplo con id fijo (no generado, para
  que el comando sea idempotente), crea su `persona` titular y su `asignacion_rol` de `super_admin` si
  no existen, y carga el edificio por los mismos casos de uso que la API (`crear_edificio`,
  `confirmar_sin_saldos_previos`), todo en una transacción. Tests contra PostgreSQL real, primero en
  rojo (el comando no existe, o existe con `fabrica_migrador` y falla por permisos): primera carga con
  13 unidades, el `super_admin` creado y la auditoría de crear y confirmar; segunda carga igual sin
  cambios; segunda carga después de cambiar la tasa en `parametros.yaml` da "ya estaba"; dos cargas en
  paralelo dejan un solo ejemplo; con una unidad editada falla sin escribir y dice qué difiere; otra
  administración con datos queda idéntica (comparación fila por fila); sin tenant no escribe nada.
  Escenarios: `datos-semilla` › Primera carga; › Segunda carga igual; › Cambiar los parámetros no hace
  fallar la carga; › Dos cargas a la vez; › El ejemplo cambió en la base; › Otras administraciones no
  se tocan; `acceso-de-desarrollo` › La carga corre como `proptech_app`; › Ningún permiso nuevo sobre
  `auditoria`. Lecciones: L-006, L-016, L-029.
  - **Por qué cambia de rol respecto de la versión anterior de esta tarea**: `proptech_migrador` no
    tiene `GRANT` sobre `auditoria` (ownership pasa al rol de arranque en `roles.despues()`; sólo
    `proptech_app` recibe `SELECT, INSERT`, `backend/src/proptech_core/compartido/roles.py:701-735`), y
    los casos de uso que D9/E10 pide reusar auditan con `registrar()`, que exige `INSERT`. D11 del
    design de `login-y-usuarios` (E12) decide no pedir ese `GRANT`: en vez de darle el permiso al
    migrador, la carga corre como `proptech_app`, que ya lo tiene, igual que D10.
  - **Trabajo de partida, no para aplicar tal cual**: el constructor del 3b dejó una implementación
    guardada sin commitear en `.git/informes-3b/2.3-wip/` (`ejemplo.py`,
    `test_ejemplo_casos_de_uso.py`) y el fixture `fabrica_migrador` como patch en
    `.git/informes-3b/2.3-wip.patch` (contra `backend/tests/integracion/conftest.py`). Esa
    implementación asume `proptech_migrador` y el `GRANT`: sirve de referencia para la lógica de
    casos de uso, pero el fixture y la apertura de sesión se reescriben sobre `proptech_app` (D10), no
    se aplican como patch.
  - **Ninguno de los grupos 1 a 6 del 3b la importa ni la necesita**: las pantallas y la base de test
    de la web no leen nada de la administración de ejemplo; sólo el recorrido de la tarea 1.1 depende
    de que esté cargada.
- [x] 1.1 **Recorrido contra la API real, entrando por el login**: con el ejemplo cargado (1.0), las
  siete pantallas del 3b en el navegador a 320 px y a 1280 px, con capturas y el recorrido de teclado,
  entrando con una cuenta de Clerk de desarrollo vinculada a la persona titular de la administración de
  ejemplo (su `super_admin`) — nunca con un punto de entrada que reemplace la identidad — y la corrida
  de cierre del grupo (`test-backend.sh`, `humo.sh` y `test-web-navegador.sh`). Verificación: el
  informe trae las capturas, los comandos y su salida, y confirma que no hay en el repositorio ningún
  archivo bajo `backend/desarrollo/` ni `infra/compose.desarrollo.yaml`. Escenarios:
  `acceso-de-desarrollo` › Pedido de dominio sin sesión, en desarrollo; › El repositorio no tiene un
  punto de entrada propio; › Entrar a las pantallas con el ejemplo cargado. Lecciones: L-010, L-022.
