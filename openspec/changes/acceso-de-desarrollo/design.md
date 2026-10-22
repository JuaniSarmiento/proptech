## Context

Las decisiones de forma de este change ya no están en los dos lugares que citaba la versión anterior
de este archivo. **D11 del 3a** (`openspec/changes/archive/2026-10-19-configuracion-del-edificio/design.md`)
y **D12 del 3b** (`openspec/changes/archive/2026-10-20-pantallas-del-edificio/design.md`) describían el
punto de entrada sin login que este change iba a construir. Esa forma quedó **reemplazada** por una
decisión posterior, tomada ya con el login construido:

- **D11 · `acceso-de-desarrollo` (E12)**, en `openspec/changes/login-y-usuarios/design.md`: "con el
  login, la puerta sin login sobra y es una puerta más que puede llegar a producción"; cierra el acceso
  de desarrollo (no construye `backend/desarrollo/` ni `compose.desarrollo.yaml`) y reduce este change
  a la carga del ejemplo, reescrita sobre el camino de **D10 · Alta inicial (E11)** (mismo archivo):
  `proptech_app`, nunca `proptech_migrador`, con el tenant de la administración de ejemplo y su super
  admin. Para recorrer las pantallas se entra con Clerk de desarrollo (D12/E13 del 2b).

Este change no agrega una decisión de diseño nueva: aplica D10 y D11 del 2b a su propio alcance. La
única pieza de implementación específica de este change es **cómo** se adapta el comando de carga del
ejemplo para seguir el camino de D10 (ver abajo); no hay decisión de permisos pendiente, porque D11 ya
descarta el `GRANT`.

## Decisions

### D1 · La carga del ejemplo corre como `proptech_app`, por el camino de D10

El comando de carga reutiliza la forma de `backend/src/proptech_core/acceso/aplicacion/alta_inicial.py`
(D10): abre sesión con las credenciales de `proptech_app`, fija el tenant de la administración de
ejemplo (id fijo, no generado, para que el comando sea idempotente — a diferencia de D10, que genera
un id nuevo por cada alta), y en una sola transacción:

1. Si la administración de ejemplo no existe, la crea junto con su `persona` titular y su
   `asignacion_rol` de `super_admin` (mismo patrón que `crear()` en `alta_inicial.py`).
2. Carga el edificio por los casos de uso reales (`crear_edificio`, `confirmar_sin_saldos_previos`),
   que auditan con `registrar()`.

**Permiso existente, no supuesto** (mismo argumento que D10): `proptech_app` ya tiene `GRANT SELECT,
INSERT ON auditoria` (`backend/src/proptech_core/compartido/roles.py:735`) y los cuatro permisos
(`SELECT, INSERT, UPDATE, DELETE`) sobre las tablas de dominio que no están en
`_TABLAS_EXCLUIDAS_DEL_GRANT_A_LA_APP` (`roles.py:219-250`). No hace falta ningún `GRANT` nuevo: es la
misma identidad que ya usan la API y el worker en producción.

**Descartado**: correrlo como `proptech_migrador` con un `GRANT INSERT ON auditoria` propio (el
alcance original de este change, antes de D11 del 2b). Costo de revertir: ya se revirtió con D11; este
design documenta el estado posterior.

### D2 · Ningún punto de entrada reemplaza la identidad, ni en desarrollo

Para recorrer las pantallas con el ejemplo cargado, se entra por el login real con una cuenta de Clerk
de desarrollo vinculada a la administración de ejemplo (persona titular creada en D1, con su
`asignacion_rol` de `super_admin`), igual que entraría cualquier super admin. No se construye
`backend/desarrollo/app_de_desarrollo.py` ni `infra/compose.desarrollo.yaml`: no existe ningún archivo
de este change que reemplace la identidad por fuera del login.

**Descartado**: el punto de entrada propio de D12/D11 del 3a y 3b (ya descartado por D11 del 2b).
**Costo de revertir**: no aplica — nada de esto se construye.

## Risks / Trade-offs

- [`proptech_app` escribe datos de ejemplo con las mismas credenciales que usa la API en producción] →
  acotado por la RLS (el tenant fijo de la administración de ejemplo) y por el mismo chequeo que D10
  ya tiene: si la administración de ejemplo ya tiene un `super_admin`, el comando falla sin escribir en
  vez de duplicar. El riesgo de permisos excesivos que tenía el `GRANT` propuesto originalmente
  (CRITICAL) no existe más: no se pide ningún permiso nuevo.
- [El grupo sigue sin firma propia, L-029] → las pantallas del 3b ya quedaron probadas sin este acceso
  (D3/D4 del design del 3b); el riesgo que queda es de comportamiento real contra la API real (tiempos,
  datos grandes), no de contrato.

## Open Questions

Ninguna. **PR4 del 3a** (si el punto de entrada se niega a arrancar con otra administración en la
base) queda sin objeto: D11 del 2b cierra el punto de entrada entero, así que la pregunta no aplica más.
