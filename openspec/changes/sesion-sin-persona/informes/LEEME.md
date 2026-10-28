# Informes de apply · vuelta 1

|Archivo|Autor y modelo/proveedor declarado|Familia|SHA y procedencia|Mediación y alcance|
|---|---|---|---|---|
|apply-vuelta-1.md|Constructor `/root/apply_v1`, Codex/OpenAI; versión exacta no expuesta|Heredada, compartida con orquestador; sin independencia acreditada|Base firmada7a49eff; grupos2/3 en487fae1/0fa013c; grupo5 en el commit que versiona este índice; SHA de cierre en anexo externo|Retorno completo previo al cierre; brief mediado por orquestador. Grupos1,2,3,5;5.4humana pendiente|
|evidencia-api-v1.md|Mismo constructor|Misma familia|Comandos/horas/diffs originales en cada entrada|13 mutantes ejecutados, copias restauradas|
|evidencia-web-v1.md|Mismo constructor|Misma familia|Comandos/horas/diffs originales en cada entrada|20 mutantes ejecutados, copias restauradas|
|evidencia-ejemplo-v1.md|Mismo constructor|Misma familia|Comandos/horas/diffs originales en cada entrada|15 mutantes ejecutados, copias restauradas|

SUPUESTO: el identificador exacto del modelo no está expuesto por el harness; el dispatch usó modelo heredado sin override. No se afirma aislamiento de herramientas ni independencia entre proveedores.

JUICIO (constructor, confianza alta contra tabla de fases): no faltan retornos de revisores de esta fase porque no se convocaron revisores en apply. Conformidad, rompedor, senior y auditor no se ejecutaron; no hay aprobación de verify ni autorización de archive. El informe externo solicitado `../informe-2d-v1.md` respecto de la raíz del worktree contiene el anexo de cierre posterior al último commit; esta copia conserva el retorno completo previo a ese cierre.


## Arreglos vuelta2 (28/10/2026)

|Archivo|Autor y modelo/proveedor declarado|Familia|SHA y procedencia|Mediación y alcance|
|---|---|---|---|---|
|apply-arreglos-v2.md|Constructor `/root/arreglos_2d`, Codex/OpenAI, versión exacta no expuesta|Heredada, compartida con orquestador|Código cfb99ce; retorno original propio, cierre final en anexo externo|Brief e informe rompedor recibidos por orquestador; R1/R2/R3 y enmienda E10|
|dispatch-apply-arreglos-v2.md|Mismo constructor, registro del dispatch recibido|Misma familia|Estado CLI y roles, por archivo|Sin revisores en fase apply, sin independencia acreditada|
|evidencia-arreglos-v2/|Mismo constructor|Misma familia|Logs originales RED/GREEN/mutantes, comandos y horas|10mutantes, copias restauradas; no se versionan backups de producción|

SUPUESTO: identidad exacta sin telemetría; el dispatch heredó modelo, sin sustitución silenciosa por
Claude. No se omitió ningún retorno de un revisor convocado: no hubo revisores en este apply. Verify,
rompedor, senior y auditor siguen sin ejecutar para estos arreglos; no hay aprobación de cierre.
Anexo final solicitado: `../informe-2d-arreglos-v2.md` respecto de raíz del worktree, con SHA final,
checks postcommit y resultado de navegador. Los logs de cierre se conservan en el change.
