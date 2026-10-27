# Informes de esta entrega de construcción

| Original completo | Autor | Modelo/proveedor declarado | Familia compartida | SHA | Procedencia y mediación | Ausencias |
|---|---|---|---|---|---|---|
| `apply-cx-entrega.md` | Constructor principal de esta sesión | Codex/OpenAI; variante exacta SUPUESTO | Sí, con auxiliar y rompedor Codex previo | Base 401bcd5; entrega en logs de cierre con git rev-parse HEAD | Informe escrito por su autor; evidencia ejecutada por él; retorno final completo adicional local en .git/informes-libro-de-movimientos/14-constructor-codex-cx.md | No es verify ni dictamen auditor |
| `apply-cx-auxiliar-tests.md` | `/root/cx_tests` | Codex/OpenAI heredado; variante exacta SUPUESTO | Sí | Árbol de construcción sobre 401bcd5 | Retorno final textual preservado literalmente por constructor; instrucciones de casos dadas por él; no independencia | No ejecutó suites. Su línea EVIDENCIA no contiene el comando íntegro de AST: no se toma como evidencia ejecutada por el principal |

No se solicitó una nueva ronda de verify. No se fabrican informes de conformidad, rompedor, senior
o auditor. Los informes históricos usados como fuente viven en `.git/informes-libro-de-movimientos/`
y son locales; este índice no afirma haberlos trasladado o recuperado todos.
