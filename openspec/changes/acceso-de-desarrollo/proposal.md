## Why

El 3b (`pantallas-del-edificio`) construyó las siete pantallas del administrador completas (grupos 1 a
6, MEDIUM) y las dejó probadas sin este acceso: con la API simulada, con una API falsa servida desde
fixtures y con fixtures que la API real genera con identidad inyectada (D3 y D4 del design del 3b). Lo
único que falta es entrar a esas pantallas contra la **API real**, sin login, sólo en una máquina de
desarrollo (D11 del 3a, E2). Eso es HIGH: toca cómo se saltea la identidad, aunque sea fuera de `src/`,
y Juani no estaba para firmarlo mientras se construían los grupos 1 a 6. El 3b se archivó sin esto
(20/10/2026); este change junta lo que quedó pendiente de firma.

Suma, además, la carga del edificio de ejemplo en la base (la 7.2 del 3a, D9 del 3a, E6 y E10 firmadas):
no depende del acceso de desarrollo (es al revés, el acceso la necesita), pero quedó bloqueada en el
mismo punto: el usuario `proptech_migrador` no tiene `GRANT` sobre `auditoria`, y dar ese permiso es un
cambio sobre el log de auditoría — CRITICAL — que tampoco decide un agente solo.

Cubre: **E2 del 3a** (el acceso de desarrollo), **D11 del 3a**, **D12** del design del 3b (las
decisiones del acceso), y la carga del ejemplo (D9/E6/E10 del 3a). Ninguna pantalla ni regla de negocio
se toca: todo lo observable para el administrador ya está en producción desde el 3b.

## Gobernanza

Todo el change es **HIGH**: no se construye nada hasta que la sección "Aprobación" quede firmada por
Juani o Alberto, con nombre, fecha y las dos respuestas. Mientras no se firme, estas tareas no se tocan.

Hay dos decisiones distintas, y pueden firmarse por separado:

1. **Construir el acceso de desarrollo** (D11 del 3a, D12 del 3b): HIGH, toca cómo se saltea la
   identidad.
2. **El `GRANT INSERT ON auditoria TO proptech_migrador`**, necesario para la carga del ejemplo
   (tarea 1.0): CRITICAL, toca el log de auditoría. Se decide junto con la firma de este grupo, no lo
   decide el constructor solo.

Si sólo se firma (2), la tarea 1.0 se construye sola (no depende de 1.1-1.3). Si sólo se firma (1),
1.0 sigue bloqueada por el `GRANT` y 1.1-1.3 se construyen sin ella (1.3 queda bloqueada a su vez, porque
necesita el ejemplo cargado).

## What Changes

- **El punto de entrada de desarrollo** (`backend/desarrollo/app_de_desarrollo.py`, fuera de `src/`):
  arma `crear_app()` y reemplaza la identidad con la del titular de la administración de ejemplo; se
  niega a arrancar sin esa administración o con otra administración en la base (PR4 del 3a).
  `infra/compose.desarrollo.yaml` lo monta y publica la API sólo en `127.0.0.1`.
- **Las guardas, antes que el punto de entrada**: nada en la imagen de producción, nada en
  `compose.yaml`, ningún archivo con `COMPOSE_FILE` apuntando al override, `humo.sh` con `-f
  compose.yaml` explícito, y 401 sin identidad en producción.
- **La carga del edificio de ejemplo en la base**: comando `python -m
  proptech_core.complejos.aplicacion.ejemplo cargar`, como `proptech_migrador`, con el `GRANT INSERT ON
  auditoria` que lo habilita.
- **El recorrido contra la API real**: con el ejemplo cargado y el acceso levantado, las siete
  pantallas del 3b en el navegador a 320 px y 1280 px, con capturas y teclado.

Nada de esto agrega ni cambia una pantalla, una regla de negocio o un permiso de producción.

## Capabilities

### New Capabilities

- `acceso-de-desarrollo`: entrar a las pantallas del administrador contra la API real sin login, sólo
  en una máquina de desarrollo, sin rastro en producción (D11 y E2 del 3a). Delta spec movida sin
  cambios desde `pantallas-del-edificio` (archivada 20/10/2026).

### Modified Capabilities

Ninguna. `pantallas-del-edificio`, `edificios-y-unidades` y `configuracion-versionada` ya quedaron
completas y archivadas con el 3b; nada de sus requisitos dependía de este acceso.

## Impact

- **Backend**: `backend/desarrollo/` (nuevo, fuera de `src/`); el comando de carga del ejemplo en
  `complejos/aplicacion/` (implementación ya escrita, ver abajo); una migración o `GRANT` manual que
  suma `INSERT` sobre `auditoria` para `proptech_migrador`.
- **Infra**: `infra/compose.desarrollo.yaml`; tests en `tests/infra/` para las guardas.
- **Nada de `web/`**: las pantallas no cambian; sólo se prueban contra datos reales en vez de fixtures.

## Trabajo ya adelantado (del 3b, sin commitear)

El constructor del 3b dejó la implementación de la carga del ejemplo (1.0) lista pero bloqueada por el
`GRANT`, guardada sin commitear: `ejemplo.py` y `test_ejemplo_casos_de_uso.py` en
`.git/informes-3b/2.3-wip/`, y el fixture `fabrica_migrador` como patch en
`.git/informes-3b/2.3-wip.patch` (contra `backend/tests/integracion/conftest.py`). Se aplica recién
junto con el `GRANT` firmado; `.git/` no se versiona así que ese trabajo vive sólo en el disco de quien
lo generó hasta que se aplique.

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 20/10/2026): `01` a `16` y `README.md`.

- `12_fichas_de_changes.md`: **APPEND** al cerrar este change (ficha propia, "Deuda del cierre del 3b"
  ya la nombra como dueño propuesto). Mientras esté abierto, **none**.
- `08_arquitectura_propuesta.md`: **REWRITE** al archivar, si se construye: el punto de entrada de
  desarrollo y el migrador como credencial de la carga del ejemplo.
- `09_decisiones_y_supuestos.md`: **APPEND** al archivar, con el resultado de las dos firmas (se
  construyó o no, y por qué).
- `04_modelo_de_datos.md`: **REWRITE** al archivar si se carga el ejemplo (ya se adelantó al archivar
  el 3b, sección de la semilla).
- El resto: **none**. No cambia ninguna pantalla, regla, rol ni permiso de producción.

## Aprobación

Gobernanza HIGH y CRITICAL (ver Gobernanza). La completa, a mano, Juani o Alberto. Ningún agente la
escribe.

| Elección | Propuesta | Aprobada (sí / no, con motivo) |
|---|---|---|
| (1) Construir el acceso de desarrollo de E2 (D11 del 3a, D12 del 3b) | Sí, tal como lo firmó E2: punto de entrada fuera de `src/`, `compose.desarrollo.yaml` aparte, identidad fija del titular de ejemplo, con sus seis guardas en test, y la respuesta a PR4 (el punto de entrada se niega a arrancar si la base tiene alguna administración que no sea la de ejemplo). Alternativa: no construirlo y esperar al 2b (las pantallas ya quedan probadas con la API falsa y los fixtures, D3/D4 del 3b) | |
| (2) `GRANT INSERT ON auditoria TO proptech_migrador`, para que la carga del ejemplo pueda auditar `crear_edificio` y `confirmar_sin_saldos_previos` | Sí, acotado a `INSERT` (no `UPDATE` ni `DELETE`) y sólo para `proptech_migrador`. Alternativa: no dar el `GRANT` y hacer que la carga del ejemplo no audite (pierde la paridad con los casos de uso reales que D9/E10 pedía reusar) | |

| Socio (Juani o Alberto) | Fecha | Alcance aprobado |
|---|---|---|
| | | |
