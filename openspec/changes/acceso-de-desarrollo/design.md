## Context

Las decisiones de forma ya están tomadas en otros dos lugares; este design no las rediscute, sólo
remite:

- **D11 · Cómo se entra a las pantallas sin login, en desarrollo (E2)**, en
  `openspec/changes/archive/2026-10-19-configuracion-del-edificio/design.md`: el acuerdo original
  (punto de entrada fuera de `src/`, Compose aparte, identidad fija del titular de ejemplo).
- **D12 · El acceso de desarrollo (grupo 7, espera la firma)**, en
  `openspec/changes/archive/2026-10-20-pantallas-del-edificio/design.md`: la respuesta propuesta a
  PR4 (el punto de entrada se niega a arrancar si la base tiene alguna administración que no sea la de
  ejemplo) y la lista de guardas que se escriben antes que el punto de entrada.

Este change no agrega una decisión de diseño nueva sobre el acceso: junta lo que D11 y D12 ya
resolvieron y que seguía sin la firma HIGH para construirse. La única decisión nueva es la del `GRANT`
(ver proposal.md › Aprobación), que no es de diseño sino de permisos sobre `auditoria`.

## Decisions

Ninguna. D11 (3a) y D12 (3b) ya deciden la forma; la tarea 1.0 (carga del ejemplo) ya está
implementada (ver proposal.md › "Trabajo ya adelantado"). Lo único pendiente es la firma.

## Risks / Trade-offs

- [El `GRANT` es permanente una vez dado] → acotado a `INSERT` sobre `auditoria`, sólo para
  `proptech_migrador`, nunca `UPDATE` ni `DELETE` (ver proposal.md).
- [El grupo sin firma] → las pantallas del 3b ya quedaron probadas sin este acceso (D3/D4 del design
  del 3b); el riesgo que queda es de comportamiento real (tiempos, datos grandes), no de contrato.

## Open Questions

- **PR4 del 3a**: la respuesta propuesta está en D12 del 3b; se confirma o se corrige al firmar.
