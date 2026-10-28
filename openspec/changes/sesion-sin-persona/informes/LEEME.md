# Informes de apply · vuelta 1

|Archivo|Autor y modelo/proveedor declarado|Familia|SHA y procedencia|Mediación y alcance|
|---|---|---|---|---|
|apply-vuelta-1.md|Constructor `/root/apply_v1`, Codex/OpenAI; versión exacta no expuesta|Heredada, compartida con orquestador; sin independencia acreditada|Base firmada7a49eff; grupos2/3 en487fae1/0fa013c; grupo5 en el commit que versiona este índice; SHA de cierre en anexo externo|Retorno completo previo al cierre; brief mediado por orquestador. Grupos1,2,3,5;5.4humana pendiente|
|evidencia-api-v1.md|Mismo constructor|Misma familia|Comandos/horas/diffs originales en cada entrada|13 mutantes ejecutados, copias restauradas|
|evidencia-web-v1.md|Mismo constructor|Misma familia|Comandos/horas/diffs originales en cada entrada|20 mutantes ejecutados, copias restauradas|
|evidencia-ejemplo-v1.md|Mismo constructor|Misma familia|Comandos/horas/diffs originales en cada entrada|15 mutantes ejecutados, copias restauradas|

SUPUESTO: el identificador exacto del modelo no está expuesto por el harness; el dispatch usó modelo heredado sin override. No se afirma aislamiento de herramientas ni independencia entre proveedores.

JUICIO (constructor, confianza alta contra tabla de fases): no faltan retornos de revisores de esta fase porque no se convocaron revisores en apply. Conformidad, rompedor, senior y auditor no se ejecutaron; no hay aprobación de verify ni autorización de archive. El informe externo solicitado `../informe-2d-v1.md` respecto de la raíz del worktree contiene el anexo de cierre posterior al último commit; esta copia conserva el retorno completo previo a ese cierre.
