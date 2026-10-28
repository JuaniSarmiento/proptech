# Constructor · arreglos vuelta 2 de sesion-sin-persona

JUICIO (constructor Codex/OpenAI, confianza alta contra el brief): entregados R2D-R1/R2/R3 y enmienda
E10 firmada por Juani, en el worktree autorizado. Código en `cfb99ce499f900731043043e1590ffc14d38d273`.
Esta es construcción, no conformidad ni una aprobación de verify. El SHA documental final y el anexo
postcommit viven en `../informe-2d-arreglos-v2.md` respecto de la raíz del worktree.

## Fuentes, identidad y límites de independencia

JUICIO (constructor, confianza alta sobre fuentes que abrió): brief completo e informe rompedor
`<local>` completo;
proposal con enmienda E10, design D10/D11 y contratos del change, tasks7.6/7.8/8.2 y sus deltas de
usuarios/autorización; `knowledge-base/15_lecciones.md` (incluidas L013/L019/L029/L030/L031/L032/L034);
componentes y consumidores de unidades, configuración, saldos, invitación; sesión y layout, API web
de vecinos/personal/unidades, scripts de web y navegador, e2e de invitación, configuración Playwright.
Skills usadas: `.claude/skills/openspec-apply-change/SKILL.md`, `impeccable` y
`test-driven-development` desde `~/.claude/skills/`. Loader de PRODUCT.md/DESIGN.md ejecutado,
contexto válido. Corrección sobre diseño existente, sin nuevo shape, imágenes ni CSS.

SUPUESTO: el modelo exacto no está expuesto. Identidad declarada Codex/OpenAI, modelo heredado sin
override, familia compartida con orquestador; no hay otro proveedor disponible y no se afirma
independencia. Contaminación reconocida: el brief exige leer conclusiones/casos del rompedor; estos
arreglos parten de ellos. No hubo auditor dictando casos nuevos ni una revisión independiente.

## Cambios y resolución de texto

JUICIO (constructor, confianza alta contra D11 y DOM): unidades deja lectura textual sin acción de
editar al carecer de `configurar_padron`; no monta formulario ni Guardar sin ese permiso. La gestión
de vecinos exige `invitar_usuarios_y_asignar_edificios`, además de datos disponibles; GET personal200
no concede esa acción. El nuevo test consumidor renderiza página real y Pantalla con respuesta200 y
Map vacío, con/sin permiso de invitar. Configuración oculta Cambiar configuración sin
`crear_version_de_configuracion`; saldos mantiene información y oculta formulario/Confirmar sin
`confirmar_sin_saldos_previos`. Casos sin contexto, lectura y permiso de edificio ajeno están cubiertos;
se preservan guardas de escritura permitida.

JUICIO (constructor, confianza alta contra E10): Usar otra cuenta es botón que monta Clerk sólo al
pedir salir, espera ClerkLoaded y llama signOut con la URL de la misma invitación y ticket seguro.
La página arma esa URL desde el sobre escapado y ticket validado. Ingreso y registro conservan sus
links independientes. El proveedor no se monta leyendo o rechazando la invitación: se preserva
la restricción previa de recursos de terceros; el e2e cambia su consulta de enlace a botón.

JUICIO (constructor, confianza alta contra firma posterior): donde D10/specs anteriores dicen ir a
/ingresar, prevalece la enmienda E10 firmada posterior. Tareas7.8/8.2(e) se actualizan; la evidencia
manual histórica queda intacta. No se modifica firma ni se declara validado un recorrido real nuevo.
Los comentarios ya no equiparan lectura de personal con super admin, describen el UUID que el caller
de alta inicial pasa, y no confunden tests del componente con Clerk real. Backend sólo cambia ese
comentario, sin SQL ni comportamiento ni nuevas reglas.

## EVIDENCIA · TDD

- `corepack pnpm@12.10.1 --dir web vitest run` con los cinco archivos originales de unidades,
  configuración, saldos e invitación: 51 passed en5files, 15:51 ART, baseline f7e69d9.
- Nuevo `unidades/permisos.test.tsx`, mismo runner dirigido:10 failed/4passed en DOM,15:51:45.
  Gates implementados y regresión de4files:53passed,15:52:19.
- E10 pantalla+página, mismo runner dirigido:5failed/12passed en signOut/URL,15:53:02;
  verde con consumidor:19passed,15:53:36.
- Preservar no montar proveedor al leer/rechazar, Pantalla.test:1failed/7passed15:56:12;
  verde E10 pantalla+página18passed15:56:35.
- `python3 /tmp/2d-arreglos-v2-evidencia/mutantes.py`: diez mutantes dirigidos muertos. Diffs,
  comandos, horas y aserciones bajo tareas7.6/7.8 y logs completos en evidencia-arreglos-v2.
  M1editar3fallos; M2guardar1; M3configuración3; M4saldos3; M5vecinos2 incluyendo page consumidor;
  M6cerrar2; M7volver a ingreso3; M8perder ticket1; M9proveedor anticipado1 con filtro/7skipped;
  M10control de editar en consumidor e2e1fallo en aserción de ausencia.
  No se suman ejecuciones como tests únicos. Backups propios antes de mutar implementación sin commit,
  restaurados por finally; ningún mutante queda en producción. Tests nacidos verdes declarados en tasks.
- Regresión focal tras restaurar:74passed/7files,15:57:30–15:57:41 ART. Las dos pruebas de consumidor
  nacieron verdes; M5 acredita el negativo. La guarda adicional de Guardar nace verde y M2 la acredita.
- Primer setup de page consumidor falló por resolución server-only; no cuenta como RED. Se usa
  el helper puro real de vecinos en el doble servidor, sin cambiar la implementación por ese fallo.

## EVIDENCIA · Cierre sobre código cfb99ce

- `bash infra/ci/test-web.sh`,15:59:40–16:00:31 ART:76files,541passed,51.25s,exit0.
- `cd web && pnpm biome ci`,16:00:41–16:00:42 ART:213files,exit0,7warnings y6infos.
- `cd web && npx tsc --noEmit`,16:00:42–16:00:44 ART:sin salida,exit0.
- `PROPTECH_PUERTO_API_FALSA=43218 PROPTECH_PUERTO_WEB=43219 bash infra/ci/test-web-navegador.sh
  acceso-pantallas.spec.ts ticket-de-invitacion.spec.ts escrituras-unidades.spec.ts vecinos-del-padron.spec.ts
  bloque-c.spec.ts pulido.spec.ts sesion.spec.ts estado-de-carga.spec.ts barrido-completo.spec.ts`,
  16:00:59–16:05:44 ART, SHA cfb99ce:160tests/1worker/Chromium,155passed/5failed,exit1.
  Cuatro ENOTDIR en mkdir `.git/informes-2b/pantallas` (acceso2,vecinos2). Quinto: test anterior
  intentaba click editar1A con sesión sin permisos; ahora debe ser lectura. Se adapta esa expectativa
  del consumidor, sin tocar producción ni el entorno. No se presenta la selección como verde.
- M10, mismo script con `vecinos-del-padron.spec.ts -g 'sin permiso para leer personal'`,
  16:06:33–16:06:47 ART:restaurar botón sin permiso causa1fallo en su aserción de ausencia,
  Expected0 Received1, vecinos-del-padron:69. Archivo original comprometido en cfb99ce, restaurado.
  GREEN mismo comando16:07:09–16:07:17 ART:1passed(1.3s),exit0.
- Build/TypeScript del script de navegador pasaron. El rechazo de invitación sin recursos de terceros
  pasó los4casos. No se visitó Clerk real. El anexo externo tiene comprobaciones postcommit final;
  no se repite el barrido132 por documentación, se repiten los4specs directamente afectados.

JUICIO (constructor, confianza alta contra diff y runner): las advertencias de canvas/jsdom de la
suite ya estaban en baseline; biome mantiene advertencias/infos fuera de estos cambios. No equivalen
al resultado de CI remoto. Este retorno previo al anexo final queda completo con los logs de la
corrida actual; el anexo externo registra las corridas posteriores al último commit documental.

## SUPUESTOS y pendientes

- No hubo login en Clerk real, lectura/copia/impresión de `.env`, humo, Compose, push, pkill ni pgrep-f.
- SDK de Clerk es doble en unitarios; probar que se pidió signOut con redirectUrl correcto no prueba
  cierre real en el proveedor. Repetir8.2(e) con Juani al teclado queda pendiente. El estado global de
  8.2 y8.1 no se marca completo por esta entrega;5.4humana tampoco se toca.
- Backend completo, ruff/mypy, humo y CI remoto quedan fuera del brief acotado; no se presentan verdes.
- Ningún revisor, senior, rompedor ni auditor fue convocado en este apply. No se afirma APROBADO ni
  cierre del change. Justificación por rol y fuentes del clasificador en dispatch-apply-arreglos-v2.md.
- KB no se reescribe. Drift por documento se registra en dispatch y se transmitió al orquestador.
- No se toca CSS de Clerk; la deuda visual previa sigue fuera de este arreglo.
