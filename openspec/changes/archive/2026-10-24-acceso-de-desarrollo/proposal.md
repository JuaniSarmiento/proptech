## Why

El 3b (`pantallas-del-edificio`) construyó las siete pantallas del administrador completas (grupos 1 a
6, MEDIUM) y las dejó probadas sin este acceso: con la API simulada, con una API falsa servida desde
fixtures y con fixtures que la API real genera con identidad inyectada (D3 y D4 del design del 3b). Lo
que faltaba era entrar a esas pantallas contra la **API real** con datos de ejemplo, y hasta el 2b
(`login-y-usuarios`) la única forma propuesta era un punto de entrada que saltea la identidad, sólo en
una máquina de desarrollo (D11 del 3a, E2).

El 2b construyó el login real y Juani firmó **E12** (proposal.md del 2b, 21/10/2026): "Cerrar el
acceso sin login y cargar el ejemplo por el camino de E11, sin `GRANT INSERT ON auditoria` al
migrador (D11)". **D11 del design del 2b** (`openspec/changes/login-y-usuarios/design.md`) dice en
detalle por qué y cómo: con el login, la puerta sin login sobra y es una puerta más que puede llegar a
producción; se cierra (no se construye `backend/desarrollo/` ni `compose.desarrollo.yaml`) y el change
se reduce a cargar el edificio de ejemplo reescrita sobre el camino de **D10 · Alta inicial** (el
comando `python -m proptech_core.acceso.aplicacion.alta_inicial`, corrido con las credenciales de
`proptech_app`, nunca de `proptech_migrador`): para recorrer las pantallas con el ejemplo se entra con
Clerk de desarrollo (E13 del 2b), no con un bypass.

Esto reemplaza por completo el alcance anterior de este change (el punto de entrada sin login, sus
guardas, y el `GRANT INSERT ON auditoria TO proptech_migrador`): los tres quedan descartados por D11.
Lo único que este change sigue construyendo es la carga del edificio de ejemplo (la 7.2 del 3a, D9 del
3a, E6 y E10 firmadas) y el recorrido de las siete pantallas del 3b contra la API real con ese ejemplo
cargado, entrando por el login de verdad.

**L-029** (la firma de un change no firma por sí sola sus correcciones posteriores): E12 aprueba la
*decisión de forma* en el proposal del 2b, no estos artefactos reescritos. Este change sigue
necesitando su propia firma en su sección "Aprobación", de nuevo, con la redacción que sigue.

Cubre: **D10 y D11 del design de `login-y-usuarios`**, **E11 y E12** de su proposal (firmadas,
21/10/2026), y la carga del ejemplo (D9/E6/E10 del 3a). Ninguna pantalla ni regla de negocio se toca:
todo lo observable para el administrador ya está en producción desde el 3b.

## Qué queda fuera

- **El punto de entrada de desarrollo sin login** (`backend/desarrollo/`, `compose.desarrollo.yaml`) y
  sus guardas: D11 los cierra. No se construyen.
- **El `GRANT INSERT ON auditoria TO proptech_migrador`**: D11 lo da por innecesario, porque la carga
  corre como `proptech_app`, que ya tiene `SELECT, INSERT` sobre `auditoria`
  (`backend/src/proptech_core/compartido/roles.py:735`, el mismo permiso del que depende D10). No se
  pide ni se otorga.
- **Ninguna pantalla, regla de negocio ni permiso de producción**: las siete del 3b ya están completas
  y en producción; esto sólo las recorre con datos de ejemplo.
- **El método de login en sí**: ya está construido y firmado en `login-y-usuarios` (E1 a E17); este
  change no lo rediscute.

## Gobernanza

El change sigue siendo **HIGH**: toca cómo se carga identidad y datos en el log de auditoría, aunque
sea con el mismo mecanismo que ya usa D10 y sin bypass de ningún tipo (D-094). No se construye nada
hasta que la sección "Aprobación" quede firmada por Juani o Alberto, con nombre, fecha y la respuesta.
Ya no hay una segunda decisión CRITICAL: al no pedirse el `GRANT`, no queda nada que toque permisos
sobre `auditoria` por fuera de lo que D10 ya firmó con E11.

## What Changes

- **La carga del edificio de ejemplo en la base**, reescrita sobre el camino de D10: un comando que
  corre con las credenciales de `proptech_app` (nunca `proptech_migrador`), fija el tenant de la
  administración de ejemplo, crea su fila `super_admin` en la misma transacción (igual que D10 arma el
  alta inicial) y después carga el edificio por los mismos casos de uso que la API
  (`crear_edificio`, `confirmar_sin_saldos_previos`), auditando con `registrar()` sin necesitar ningún
  `GRANT` nuevo.
- **El recorrido contra la API real**: con el ejemplo cargado, las siete pantallas del 3b en el
  navegador a 320 px y 1280 px, con capturas y teclado, entrando con una cuenta de Clerk de desarrollo
  vinculada a la administración de ejemplo (E13 del 2b) — nunca con un punto de entrada que reemplace
  la identidad.
- **Nada en `backend/desarrollo/`, nada en `infra/compose.desarrollo.yaml`, ningún `GRANT` manual**:
  los tres quedan descartados por D11.

Nada de esto agrega ni cambia una pantalla, una regla de negocio o un permiso de producción.

## Capabilities

### New Capabilities

- `acceso-de-desarrollo`: recorrer las pantallas del administrador contra la API real en desarrollo,
  con el edificio de ejemplo cargado y entrando por el login real, sin ningún camino que saltee la
  identidad (D10 y D11 de `login-y-usuarios`, E11 y E12). Reemplaza por completo la delta spec anterior
  (movida sin cambios desde `pantallas-del-edificio`, archivada 20/10/2026), que describía el punto de
  entrada sin login ya descartado.

### Modified Capabilities

Ninguna. `pantallas-del-edificio`, `edificios-y-unidades`, `configuracion-versionada` y
`login-y-usuarios` ya quedaron completas (o, en el caso del login, con su propia firma) y archivadas o
en curso por su cuenta; nada de sus requisitos depende de este change. La capability `datos-semilla`
(`openspec/specs/datos-semilla/spec.md`) ya describe el comando de carga sin nombrar un actor
específico — no necesita delta: el cambio de `proptech_migrador` a `proptech_app` es de identidad, no
de contrato.

## Impact

- **Backend**: el comando de carga del ejemplo, reescrito sobre `backend/src/proptech_core/acceso/aplicacion/alta_inicial.py`
  (D10) para correr como `proptech_app` en vez de `proptech_migrador`; vive bajo `complejos/aplicacion/`
  igual que antes. Sin migraciones ni `GRANT` manuales.
- **Infra**: nada. No hay `compose.desarrollo.yaml` ni archivo de Compose propio para este change.
- **Nada de `web/`**: las pantallas no cambian; sólo se prueban contra datos reales en vez de fixtures,
  entrando con Clerk de desarrollo.

## Trabajo ya adelantado (del 3b, sin commitear) — a revisar, no a aplicar tal cual

El constructor del 3b dejó una implementación de la carga del ejemplo (1.0) guardada sin commitear:
`ejemplo.py` y `test_ejemplo_casos_de_uso.py` en `.git/informes-3b/2.3-wip/`, y el fixture
`fabrica_migrador` como patch en `.git/informes-3b/2.3-wip.patch` (contra
`backend/tests/integracion/conftest.py`). Esa implementación asumía `proptech_migrador` y el `GRANT`
que D11 descarta: **no se aplica tal cual**. Sirve como punto de partida para la tarea 1.0 de
`tasks.md`, que la reescribe sobre `proptech_app` y el camino de D10 (fixture `fabrica_app`, no
`fabrica_migrador`). `.git/` no se versiona, así que ese trabajo vive sólo en el disco de quien lo
generó hasta que se reescriba.

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 21/10/2026): `01` a `16` y `README.md`.

- `12_fichas_de_changes.md`: **APPEND** al cerrar este change (ficha propia "3b-bis", ya la nombra
  "HIGH y CRITICAL, sin firmar"; se corrige a sólo HIGH y se cierra con el resultado). Mientras esté
  abierto, **none**.
- `08_arquitectura_propuesta.md`: **REWRITE** al archivar, si se construye: la carga del ejemplo como
  `proptech_app` por el camino de D10, en vez del migrador; sin punto de entrada de desarrollo.
- `09_decisiones_y_supuestos.md`: **APPEND** al archivar, con el resultado de la firma (se construyó o
  no, y por qué) y la referencia a D-107/D11 del 2b como la decisión que reemplazó el alcance original.
- `04_modelo_de_datos.md`: **REWRITE** al archivar si se carga el ejemplo (ya se adelantó al archivar
  el 3b, sección de la semilla).
- El resto: **none**. No cambia ninguna pantalla, regla, rol ni permiso de producción.

## Aprobación

Gobernanza HIGH (ver Gobernanza). La completa, a mano, Juani o Alberto (desde D-111, también Emiliano, que ratifica la firma de abajo). Ningún agente la escribe.

| Elección | Propuesta | Aprobada (sí / no, con motivo) |
|---|---|---|
| Cargar el edificio de ejemplo por el camino de D10 (E11), sin punto de entrada sin login ni `GRANT INSERT ON auditoria` a `proptech_migrador` (D11 del design de `login-y-usuarios`, E12) | Sí: reescribir la carga del ejemplo para correr como `proptech_app` (D10), crear la fila `super_admin` de la administración de ejemplo en la misma transacción y cargar el edificio por los casos de uso reales; recorrer las pantallas del 3b entrando con Clerk de desarrollo (E13 del 2b). Alternativa descartada: mantener el punto de entrada sin login y el `GRANT` a `proptech_migrador` (alcance original de este change, ya descartado por D11) | Sí |

| Firmante (Juani, Alberto o Emiliano; D-111 ratifica esta firma) | Fecha | Alcance aprobado |
|---|---|---|
| Emiliano Caceres | 24/10/2026 | Cargar el edificio de ejemplo por el camino de D10 (como proptech_app, sin GRANT nuevo ni punto de entrada sin login) y recorrer las 7 pantallas del 3b con ese ejemplo, entrando por Clerk de desarrollo |
