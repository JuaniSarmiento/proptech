# Actores y Roles

## Actores del sistema

| Rol | Qué hace |
|---|---|
| **Administrador titular** | Configura el edificio, carga gastos, liquida, confirma pagos, ve la morosidad; las acciones exclusivas del titular están en la matriz de D-096 |
| **Colaborador** | Personal de la administración: sólo los edificios que le asignan, con nivel "ver" o "editar" |
| **Vecino** | Persona de contacto de una o varias unidades (propietario o no): ve su deuda, entiende su expensa, informa pagos |
| **Consejo** | Sólo lectura de morosidad, gastos y liquidaciones de su edificio |

El inquilino como rol separado queda para después del MVP; en edificios es frecuente, así que se
valida con el piloto que la persona de contacto alcance (D-032).

### Las dos capas de aislamiento (D-076)

- **Administración** (el tenant): el cliente que paga PropTech. Todo dato pertenece a una
  administración y ninguna consulta, archivo, caché o proceso devuelve datos de otra. Sale de la
  identidad autenticada, nunca de un parámetro que manda el cliente (R10).
- **Alcance por edificio**: dentro de su administración, cada persona ve sólo los complejos que le
  corresponden según su rol: el titular, todos; el colaborador, los asignados; el consejo, el suyo; el
  vecino, sus unidades. Fuera de alcance responde 404; sin permiso, 403 con el permiso faltante
  (D-037).

### Los cuatro roles del MVP (D-037, amplía D-009)

Se mantienen las tres capas de la arquitectura de Alberto (administración deducida del login, alcance
por edificio, permiso por rol), con cuatro roles:

- **Titular**: todo, incluido cerrar liquidaciones y anular pagos.
- **Colaborador**: sólo los edificios asignados, nivel "ver" o "editar"; no cierra ni anula.
- **Consejo**: sólo lectura de su edificio.
- **Vecino**: sus unidades.

Descartado: las ~15 áreas con 3 niveles del documento de arquitectura de Alberto (se suman cuando un
cliente las pida) y los actores contador, encargado y proveedor como usuarios del sistema (entran
como datos del dominio, no como roles que inician sesión).

## RBAC · Matriz de permisos

Lo que D-037, D-076 y R10 ya deciden, por nivel de alcance (la primera capa del aislamiento), más la
tercera capa, el **permiso por acción**, que fijó D-096 (resuelve P23).

| Rol | Alcance (D-037, D-076) | Lectura | Escritura general | Acciones de D-096 (emitir, distribuir, anular, confirmar/revertir pago, condonar, dar de baja, aceptar alerta) |
|---|---|---|---|---|
| **Titular** | Todos los complejos de su administración | Todo | Todo, incluido cerrar liquidaciones y anular pagos (D-037) | Todas: emite y distribuye, anula, confirma y revierte pagos, condona, da de baja una deuda, acepta cualquier alerta |
| **Colaborador** | Sólo los complejos que le asignan dentro de su administración | Según su nivel | Nivel "ver" (sólo lectura) o "editar" (según D-037); **no cierra ni anula** liquidaciones | Con nivel "editar": carga gastos y prepara la liquidación, confirma un pago informado, acepta alertas que no bloquean. **No** emite, no distribuye, no anula, no revierte un pago, no condona, no da de baja una deuda, no acepta una alerta que bloquea. Con nivel "ver", ninguna acción de escritura |
| **Consejo** | Su complejo, dentro de la administración | Morosidad, gastos y liquidaciones de su complejo | Ninguna (sólo lectura, D-037) | Ninguna: ve la carga de gastos y ve cuándo se condona un interés (con el motivo), pero no ejecuta ninguna acción |
| **Vecino** | Sus unidades, dentro de la administración | Su deuda, su expensa, sus pagos y comprobantes | Informa sus propios pagos (R11); no confirma, no condona, no anula | Ve su cuenta e informa pagos (R11); **confirmarlo** es acción del administrador |

**Las dos capas siguen siendo distintas** (D-076): esta tabla cubre el **alcance por edificio** (quién
ve qué complejo), el **permiso general por rol** (D-037) y, ahora, el **permiso por acción** (D-096).
Fuera de alcance responde 404; dentro de alcance pero sin el permiso de esa acción, 403 con el permiso
faltante (D-037).

**Sigue abierta P20**: la matriz fija que condonar es acción exclusiva del titular, pero no si por
encima de un monto hace falta además la aprobación del consejo antes de condonar; esa parte de la
pregunta no se cierra acá.

**R41 (propuesta)** ya proponía que sólo el titular da de baja una deuda; D-096 lo confirma para el
resto de la columna de acciones.

## Rutas públicas

**Hoy**, antes del cambio 2 (que es quien construye el acceso), el sistema no tiene ninguna ruta de
dominio ni autenticación: lo único que existe son dos sondas de orquestación, pensadas para no
necesitar sesión porque no exponen datos de ningún complejo ni unidad:

- `GET /api/salud` (`backend/src/proptech_api/salud.py`): informa si la API, la base y la cola
  responden (`{"estado", "base", "cola"}`); 503 si alguna está degradada. Existe desde el cambio 1a/1c.
- `GET /salud-web` (`web/src/app/salud-web/route.ts`): el equivalente del lado de Next.js. Existe desde
  el cambio 1c.

Estas dos rutas **no son una decisión de negocio sobre qué queda público**: son endpoints técnicos
que no tienen por qué pasar por el login, igual que cualquier healthcheck de Compose. Ninguna otra
ruta existe todavía: el esqueleto de `web/src/app/` (`layout.tsx`, `page.tsx`) no tiene pantallas de
dominio.

**Lo que queda por decidir** (no se asume "ninguna" sin confirmarlo en el *design* del cambio 2, D-039):
qué pantallas del portal del vecino o del login quedan accesibles sin sesión (por ejemplo, la propia
pantalla de login); y si un **link firmado** de descarga (D-070: PDF de la expensa, comprobantes,
facturas, con vencimiento entre un minuto y una hora) cuenta como "ruta pública" en el sentido de este
documento o es un mecanismo aparte que no requiere sesión activa pero sí una firma válida: ese punto
tampoco está resuelto todavía y se deja así, sin asumir una respuesta. Se completa junto con el
explore del cambio 2 (login del personal y del vecino, D-039). Ya no queda condicionado por P18 (una
cuenta por administración, D-096): el login resuelve siempre dentro de una sola administración.
