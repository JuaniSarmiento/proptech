**EVIDENCIA**

`python3` con `ast.parse` del archivo modificado → `AST válido; sleeps: False; 11 casos` (27/10/2026, 08:36:51 -03). No ejecuté tests ni contenedores.

**JUICIO (constructor auxiliar, confianza alta)**

Único archivo editado: `backend/tests/integracion/test_cc_replay_carrera.py`.

- CX-02 usa escritor en hilo, eventos y `pg_blocking_pids`, sin sleeps. Admite tanto bloqueo real como escritor terminado para continuar; exige bloqueo mediante aserción y compara las dos fotos exactas.
- La transacción lectora libera los candados antes del `join`. Se comprueba que el escritor terminó sin error y produjo el estado posterior esperado.
- Los replay concurrentes comparan conteos de siete tablas entre ganador y repetición.
- Los casos intercalados de emisión y crédito verifican conteos.
- Agregué cobertura de crédito de corrección parametrizando el caso que no debe reimputar: ahora son 11 casos.

**SUPUESTO**

La primera consulta `_replay` seguirá siendo optimista; las barreras heredadas dependen de ese punto anterior al candado. Verde, mutantes y formato quedan pendientes de ejecución por el constructor principal.
