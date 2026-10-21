# Shape: pantallas del login y de usuarios (2b, tarea 7.0)

Brief de `impeccable shape` para el grupo 7 del change `login-y-usuarios`. Pedido de Juani (21/10/2026):
**"algo muy similar a lo que ya está, siguiendo esa lógica"**. Por eso este brief no abre una dirección
nueva: hereda entero el shape aprobado de las pantallas del edificio y su enmienda del 20/10
(`2026-10-19-shape-pantallas-del-edificio.md`), `PRODUCT.md` y `DESIGN.md` (tokens reales, Source Sans 3,
terracota, The Always-Help Rule). Lo que sigue es sólo lo propio de estas pantallas.

## Lo que se hereda sin cambios

Tema claro, neutros tibios, terracota para la acción principal y "lo que necesita atención"; todo el ancho
con paneles de borde suave (panel principal + panel lateral de apoyo); menú lateral agrupado con íconos y
barra superior; filas con ícono, título y línea gris; formularios en el panel lateral (no modales); la
ayuda "?" acoplada a la derecha que empuja el contenido, con sus tres partes; estados de carga, vacío y
error; números tabulares; teclado y foco visible; 320 px sin scroll horizontal; castellano rioplatense.

## Las pantallas

1. **Ingresar** (`/ingresar`, sin sesión): el componente de Clerk en castellano (E13), vestido con
   nuestros tokens (papel, tinta, terracota, Source Sans 3, bordes suaves) para que no parezca otra app.
   Centrado en una columna con el nombre "PropTech" arriba y, debajo del formulario, una línea "¿Te
   invitaron? Revisá tu mail: el enlace te trae acá." y el enlace al aviso de privacidad. No hay
   "registrarse" suelto: el registro sólo existe desde una invitación (E7).
2. **Elegir administración** (después de ingresar, sólo si la persona tiene más de una): lista a todo el
   ancho, una fila por administración con su nombre, tu perfil ahí y cuántos edificios; tocar la fila
   entra. Si tiene una sola, entra directo.
3. **Aceptar invitación** (`/invitacion/...`, sin sesión o con una sesión distinta): un panel centrado
   que dice quién te invita, a qué administración y con qué perfil o unidad; la acción principal
   "Aceptar e ingresar" (lleva al registro o ingreso de Clerk con el email de la invitación). Estados:
   invitación vencida, ya usada o revocada, todos con el mismo mensaje simple y sin revelar de quién es
   ("Este enlace ya no sirve. Pedile a tu administración que te invite de nuevo."). Si el email con el
   que ingresaste no coincide: decirlo en simple y ofrecer cerrar sesión.
4. **Aviso de privacidad** (sin sesión, ley 25.326): página de lectura, columna de texto cómoda
   (65 a 75 caracteres), títulos claros: qué datos guarda Clerk (email y nombre) y dónde (fuera del país),
   para qué, cuánto tiempo, tus derechos y a quién escribir. Sin jerga legal innecesaria.
5. **Barra superior con el usuario real**: reemplaza "Administración" por el nombre de la persona y el
   de la administración actual; el menú del usuario tiene "Cambiar de administración" (si tiene más de
   una) y "Cerrar sesión".
6. **Personal** (`/personal`, nueva sección del menú lateral, grupo "Mi administración"): lista a todo el
   ancho con cada persona, su perfil, su alcance (toda la empresa o el edificio) y el estado de la
   invitación (pendiente, enviada, aceptada, vencida), estados siempre con texto. Panel lateral de apoyo:
   cuántos hay por perfil y una explicación corta de cada perfil (qué puede y qué no). Acción principal
   "Invitar a alguien": abre el panel lateral con nombre, email, perfil y alcance (si el perfil lo
   permite, elegir edificio). En cada fila: "Reenviar", "Revocar" o "Quitar" según el estado. Sólo el
   super admin ve las acciones; el resto ve la lista en lectura (si su perfil la puede ver).
7. **Vecinos en el padrón**: en la pantalla de Unidades, al tocar una unidad, el panel lateral suma una
   sección "Vecinos" con cada persona vinculada, su vínculo (propietario o inquilino) y el estado de la
   invitación; "Agregar vecino" abre los campos nombre, email y vínculo dentro del mismo panel. En la
   tabla del padrón, una columna "Vecinos" con la cantidad y si hay invitaciones pendientes.

## Estados que no se olvidan

Sin sesión → Ingresar. Sesión vencida a mitad de una acción → volver a Ingresar y regresar a donde
estaba. Sin permiso → el mismo estado "Sin permiso" del 3b. Invitación inválida → el mensaje único de
arriba. Error al enviar una invitación (Clerk no responde) → la fila queda "No se pudo enviar" con
"Reintentar".

## Ayuda "?"

Cada pantalla con su ayuda de tres partes. Ejemplo para Personal: "Acá ves quién trabaja con vos y qué
puede hacer cada uno. 1. Tocá 'Invitar a alguien'. 2. Elegí su perfil y dónde trabaja. 3. Le llega un mail
para entrar. Cuando acepte, aparece como 'Aceptada' y ya puede ingresar."

## Preguntas abiertas (las resuelve quien construye y las declara)

- Hasta dónde se puede vestir el componente de Clerk con nuestros tokens (su `appearance`).
- Si "Personal" muestra también a los vecinos o sólo al personal (propuesta: sólo personal; los vecinos
  viven en el padrón).

OK del brief: **Juani, 21/10/2026** (en la conversación: "sisi").

## Ajustes al construir

Ajuste del shape resuelto por el orquestador, 21/10/2026, para respetar el contrato firmado:

- 7.1: aceptar no consulta la invitación. Dice "Aceptá tu invitación", explica la acción y ofrece
  "Aceptar e ingresar". Los nombres se consultan sólo después del éxito. Todo rechazo muestra
  "Este enlace ya no sirve. Pedile a tu administración que te invite de nuevo."; con sesión ofrece
  "Cerrar sesión" sin distinguir el motivo. Selector: sólo nombres entregados por GET /api/sesion.
- 7.3 y 7.4: sin Reenviar ni Reintentar invitaciones. Estado fallida: "No se pudo enviar todavía;
  se reintenta solo". Revocar y Quitar usan exclusivamente los contratos existentes.
  **Corrección del auditor del 2b (fila 2, 21/10/2026):** ese texto es falso; el worker NO
  reintenta un 4xx definitivo (`backend/src/proptech_worker/tareas.py:278-292`, spec
  `gestion-de-usuarios` "sin reintentos"). Texto real: "No se pudo enviar. Revocala e invitá de
  nuevo.", usando la acción "Revocar" que ya existe en esa fila.
- 7.2 sigue siendo borrador, con responsable, contacto y conservación visiblemente pendientes de
  Juani; no se marca completa.
- Capturas a 1440 y 320 px, según el brief de esta segunda vuelta.

Decisión del constructor (21/10/2026, L-030): Personal filtra las asignaciones del personal; vecinos
se muestran en el padrón. El GET /api/personal exige super admin: otros perfiles ven Sin permiso,
como establece D5; no se amplía su lectura. Se conserva el sistema visual existente; no hacen falta
probes ni mock nuevos porque el shape cerrado fija composición, componentes y tokens.

OK de los ajustes al construir: **Juani, 21/10/2026**, tal como quedaron en `e74a1d1` y `3f3b0a0` (con el texto corregido de la invitación fallida).
