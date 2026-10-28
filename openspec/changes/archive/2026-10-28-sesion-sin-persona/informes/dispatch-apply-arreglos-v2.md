# Dispatch · arreglos vuelta 2

EVIDENCIA (orquestador/constructor, 28/10/2026): `openspec list --json` y `openspec status --change
sesion-sin-persona --json`, consultados al inicio por el orquestador: change activo, 27/30 tareas,
artefactos completos, árbol limpio. `openspec instructions apply --change sesion-sin-persona --json`
por constructor: `state=ready`, mismo progreso, contextFiles de propuesta, design, specs y tareas.

EVIDENCIA (registro de dispatch): un único constructor `/root/arreglos_2d` fue despachado por `/root`.
Scope recibido: R2D-R1/R2/R3 del informe `07-rompedor-vuelta2-codex.md`; `unidades/page.tsx` y su test
consumidor, `unidades/Pantalla.tsx`, `configuracion/Pantalla.tsx`, `saldos-previos/Pantalla.tsx`, tres
comentarios, `invitacion/Pantalla.tsx` y `[sobre]/page.tsx` para la enmienda E10 firmada; evidencias en
7.6/7.8 y ajuste de 8.2(e). Un agente, sin trabajo paralelo ni otros agentes. Sin push ni archive.
Brief original: `<local>`.

JUICIO (constructor, confianza alta contra brief y tabla de fases): es apply acotado, no verify.
No se convocan revisores sobre el diff en movimiento. Los controles y la corrección del cierre de
sesión necesitan revisión posterior de verify; esta entrega no fabrica auditor ni APROBADO. Los
modelos Anthropic pedidos por la tabla del proyecto no están disponibles en esta sesión; sustitución
explícita por Codex/OpenAI heredado. No se afirma independencia de familia con el orquestador ni
restricción técnica de las herramientas de un revisor.

EVIDENCIA: `active-stack roles --json` al inicio, por orquestador, devolvió diff vacío. Constructor lo
repitió sobre diff completo antes de commit, 28/10/2026 15:59 ART; original completo en
`evidencia-arreglos-v2/20-roles.json`. Resultado del clasificador:

- `role-dba`: `no-schema`; no corresponde: ninguna migración, esquema ni consulta en el diff.
- `role-backend`: `no-endpoint`; no corresponde: ningún endpoint, handler ni validación en el borde.
- `role-frontend`: `ui-tree`; archivo bajo el árbol de UI.
- `role-devops`: `no-deploy`; no corresponde: deploy y configuración sin cambios.
- `role-qa`: `always`; siempre.
- `role-architect`: `not-decided-by-diff`; no lo decide el diff: una frontera no se lee por ruta. Se convoca por fase (propose siempre) o si el cambio movió una frontera.
- `role-analyst`: `not-decided-by-diff`; no lo decide el diff: el analista funcional se convoca por fase (explore y archive), no por un hecho del diff.

JUICIO (constructor, confianza alta contra fase apply): no convocados backend, DBA, frontend, DevOps,
QA, arquitecto y analista porque esta entrega es construcción, no el verify del change. El clasificador
no activa el piso (`floor.triggered=false`) para este diff; eso NO equivale a ausencia de autenticación:
E10 toca cierre de sesión. El piso de autenticación y los revisores del change completo siguen
correspondiendo a verify. Senior, rompedor y auditor tampoco se ejecutan en este apply. La evidencia
mecánica se ejecuta una vez por estado; las repeticiones son por modificaciones o restauración de
mutantes, no por pagar el mismo dato a varios revisores.

JUICIO (constructor, confianza media): la KB puede estar atrasada en estos documentos. Comparación
realizada antes de implementar y transmitida al orquestador; fechas de autor Git por documento,
`git log -1 --format=%aI -- <ruta>`, contra días en nombres de directorios de archive. No se tocó KB:
las fechas datan bytes, no una revisión de vigencia. Se registran por documento los changes de día
posterior, sin atribuirles impacto semántico automático.

| Documento | Fecha de autor | Archives de día posterior |
|---|---|---|
| `01_vision_y_objetivos.md` | 2026-10-20T16:45:56-03:00 | 2026-10-22-login-y-usuarios, 2026-10-24-acceso-de-desarrollo, 2026-10-26-cimientos-del-libro, 2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion |
| `02_descripcion_general.md` | 2026-10-26T15:21:27-03:00 | 2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion |
| `03_actores_y_roles.md` | 2026-10-27T13:16:20-03:00 | 2026-10-28-pulido-de-la-configuracion |
| `04_modelo_de_datos.md` | 2026-10-28T09:35:44-03:00 | ninguno de día posterior; no acredita vigencia |
| `05_reglas_de_negocio.md` | 2026-10-27T15:23:10-03:00 | 2026-10-28-pulido-de-la-configuracion |
| `06_funcionalidades.md` | 2026-10-27T15:23:10-03:00 | 2026-10-28-pulido-de-la-configuracion |
| `07_flujos_principales.md` | 2026-10-26T15:21:27-03:00 | 2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion |
| `08_arquitectura_propuesta.md` | 2026-10-28T09:35:44-03:00 | ninguno de día posterior; no acredita vigencia |
| `09_decisiones_y_supuestos.md` | 2026-10-28T09:37:45-03:00 | ninguno de día posterior; no acredita vigencia |
| `10_preguntas_abiertas.md` | 2026-10-28T09:36:32-03:00 | ninguno de día posterior; no acredita vigencia |
| `11_glosario.md` | 2026-10-27T15:23:10-03:00 | 2026-10-28-pulido-de-la-configuracion |
| `12_fichas_de_changes.md` | 2026-10-28T09:37:45-03:00 | ninguno de día posterior; no acredita vigencia |
| `13_motor_de_reglas.md` | 2026-10-20T16:45:56-03:00 | 2026-10-22-login-y-usuarios, 2026-10-24-acceso-de-desarrollo, 2026-10-26-cimientos-del-libro, 2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion |
| `14_forma_de_trabajo.md` | 2026-10-27T13:16:20-03:00 | 2026-10-28-pulido-de-la-configuracion |
| `15_lecciones.md` | 2026-10-28T09:35:44-03:00 | ninguno de día posterior; no acredita vigencia |
| `16_proyecto_final.md` | 2026-10-14T17:46:18-03:00 | 2026-10-15-aislamiento-por-administracion, 2026-10-16-endurecimiento-de-infraestructura, 2026-10-19-configuracion-del-edificio, 2026-10-20-pantallas-del-edificio, 2026-10-20-roles-de-la-empresa, 2026-10-22-login-y-usuarios, 2026-10-24-acceso-de-desarrollo, 2026-10-26-cimientos-del-libro, 2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion |
| `README.md` | 2026-10-15T09:57:44-03:00 | 2026-10-16-endurecimiento-de-infraestructura, 2026-10-19-configuracion-del-edificio, 2026-10-20-pantallas-del-edificio, 2026-10-20-roles-de-la-empresa, 2026-10-22-login-y-usuarios, 2026-10-24-acceso-de-desarrollo, 2026-10-26-cimientos-del-libro, 2026-10-27-libro-de-movimientos, 2026-10-28-pulido-de-la-configuracion |

SUPUESTO: la fecha prefijada del directorio corresponde al día de archivo. La comparación por día no
ordena documentos y archives del mismo día ni prueba vigencia. El drift se reporta; no se repara de
oficio ni amplía este alcance firmado.
