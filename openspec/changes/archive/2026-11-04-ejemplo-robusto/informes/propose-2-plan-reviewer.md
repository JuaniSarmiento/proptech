# Revisor del plan · propose · intento 2 · ejemplo-robusto (C-27)

- **Rol**: corrección y revisión del plan hechas por el orquestador, como permite LOW. No hubo subagente.
- **Independencia**: ninguna. El autor del plan corrige sus propios huecos. El rompedor y el auditor siguen siendo los primeros ojos independientes.
- **Executor declarado**: Claude Opus 5.5, sesión principal de Giuliano. Familia: Claude.
- **Fecha**: 31/10/2026, 16:56 (-03:00).
- **Revisión**: base `9649471` más el árbol sin commit, con `git diff | sha256sum` en `1946d4ce3685097e815d5f05ea6758e8a0c242a7df6690afad2dec06a798a661` antes de corregir el plan. Ese diff no incluye `openspec/changes/`, que no está trackeado.
- **Veredicto**: **APTO PARA CONSTRUIR LA CORRECCIÓN**. Sólo cambian las tareas 1.2, 1.4, 5.3 y 8.2; 8.1 sigue abierta hasta tener CI.

## Fuentes leídas

- `informes/apply-1-constructor.md` completo y `tasks.md` completo.
- `specs/datos-semilla/spec.md`, `design.md` y `proposal.md`.
- `backend/src/proptech_core/complejos/aplicacion/ejemplo.py` completo y `compartido/base_de_datos.py:293-317`.
- `backend/tests/integracion/test_arranque_tablas_protegidas.py:52-133`, `test_ejemplo_casos_de_uso.py:1531-1563` y `tests/unitarios/acceso/test_vocabulario_vigente.py`.
- **Sin leer**: los informes de `.git/informes-*`, que están en la máquina de Juani, e `infra/.env`.

## Contaminación por otros informes

Este informe parte de los hallazgos del constructor, así que hereda lo que su informe eligió mirar. H-1, H-2 y H-6 se comprobaron contra el código. H-3, H-4, H-5 y H-7 se toman de su informe, sin volver a ejecutarlos.

## EVIDENCIA

| Comprobación | Comando | Resultado |
|---|---|---|
| El árbol sigue como quedó al apagar | `git diff \| sha256sum` y `sha256sum` de los seis archivos | Iguales a los de `apply-1-constructor.md` |
| El plan corregido es válido | `openspec validate ejemplo-robusto --strict`, 16:55:58 | `Change 'ejemplo-robusto' is valid` |
| Tareas | `openspec instructions apply` | `total 21`, `complete 16`, `state ready`. Bajó de 17 a 16 porque se desmarcó 8.2 |
| Consumidores de `_main` y del comando | `rg "aplicacion\.ejemplo\|aplicacion import ejemplo\|\bejemplo\._main\b"` en el repo, sin specs ni KB | Además del propio test del comando, sólo `test_arranque_tablas_protegidas.py:119,126`, `README.md:109` y un docstring de `alta_inicial.py:53` |
| Texto de la excepción | `base_de_datos.py:307-317` | Sólo nombre de tabla más `no existe en public` o `dueño no superusuario`. **Por lectura, sin ejecutar** |
| La palabra prohibida | `test_vocabulario_vigente.py:8`; `rg -i` sobre el change | El test la arma por partes, por eso una búsqueda literal en ese archivo no la encuentra. Ya no queda en el change |
| Sin guiones largos | `rg` sobre `proposal.md`, `design.md` y el spec | Sin coincidencias |
| `main` avanzó | `git fetch origin`; `git diff --stat HEAD origin/main` | `f1231b0`, dos commits adelante (D-143 y D-144): sólo documentación y `AGENTS.md`/`CLAUDE.md`. La próxima decisión libre es D-145 |
| Ramas de otros | `git diff --name-only` de `change/humo-y-ci` y `change/respaldos-2` | Tocan `README.md` en otras secciones. `respaldos-2` agrega `.gitattributes` con `infra/**/*.sh text eol=lf`, que es el arreglo del CRLF, y toca `respaldar.sh` |

No se corrió ningún test en esta revisión: las correcciones todavía no existen.

## Hallazgos del constructor y su disposición

| # | Hallazgo | Disposición |
|---|---|---|
| H-1 | El caso `ejemplo` de `test_cada_proceso_frena` espera la excepción, y el spec pide código 4 | **Hueco del plan, corregido**. Se autoriza ese caso, se agrega el escenario "Hay tablas de sólo agregar desprotegidas" y cambia D4. **Se rechaza el diff que proponía**: el `raise` dentro de `pytest.raises(..., match=tabla)` se cumple solo |
| H-2 | Tipo, piso, coeficiente y superficie comparten un mensaje que no nombra el campo | **Hueco del plan, corregido**. Opción (a): nuevo D9 y escenario "El mensaje nombra el campo de la unidad" |
| H-3 | El falso "distinto" no depende del orden físico | **Corregido** en Risks y en el escenario "Otro edificio". La ficha se corrige al cerrar |
| H-4 | El lector de archivos repite la ruta, contra lo que decía D4 | **Corregido** en D4. La línea del `replace` queda para que la mire el rompedor |
| H-5 | `argparse` repetía el id | **Incorporado** a D4 |
| H-6 | El spec usaba una palabra que el código tiene prohibida | **Corregido**: spec, propuesta y tareas dicen "super admin del ejemplo" |
| H-7 | Fallas de Windows que D-110 no nombra | **Anotado** en Risks. Se registra al cerrar; no se arregla acá |

## Hallazgos de esta revisión

| # | Hallazgo | Disposición |
|---|---|---|
| PR2-1 | La causa de H-1 está en mi primera revisión: busqué los tests que fijan el código 1 sólo en el test del comando, y los consumidores sólo en `infra/` y `.github/` | **Corregido**: la búsqueda de arriba cubre `backend/tests` entero |
| PR2-2 | 8.2 seguía marcada con evidencia anterior al refactor de `_cargar`, y la producción va a cambiar otra vez | **Desmarcada**: se repite sobre la revisión entregada |
| PR2-3 | En `tasks.md` anoté que quizá faltaba la evidencia del grupo 3 | **Descartado**: 3.1 a 3.3 tienen la evidencia con los nombres finales |
| PR2-4 | Falta el `sha256sum -c` final del intento 1 contra las copias de los mutantes, y el constructor de ese intento no se pudo retomar | **No se puede hacer**: el agente nuevo no conoce esas copias. Revisa el código contra la lista de mutantes del informe, y el rompedor mira el diff entero |

## JUICIO

- **Autor**: orquestador. **Comparación**: plan contra informe del constructor, código y tests.
- **Confianza alta**: que H-1 y H-2 son huecos del plan y no defectos de construcción, y que no hace falta tocar `acceso`, la matriz ni `cuenta_corriente`. LOW se sostiene.
- **Confianza alta**: que reenviar el texto de `TablasDeSoloAgregarDesprotegidas` no expone datos: se arma con constantes de tabla y dos motivos fijos.
- **Confianza media**: que no quede otro consumidor que dependa del texto. La búsqueda cubre `_main` y el nombre del módulo, no a quien lea el mensaje a mano.

## SUPOSICIÓN

- Que la corrida completa entre en el contenedor Linux del intento 1: ese contenedor sólo corrió 59 ids y `test_respaldos.py`. Si no se puede, el constructor lo declara y corre en Windows.
- Que `README.md` no choque con las ramas de otros al integrar: las secciones son distintas, pero no se probó el merge. Se ve al armar el PR.
