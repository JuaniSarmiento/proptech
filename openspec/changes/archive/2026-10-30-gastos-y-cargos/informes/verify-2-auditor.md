# verify · intento 2 · AUDITOR · `gastos-y-cargos` (6, MEDIUM)

- **Autor**: role-auditor, subagente nativo de Claude (Claude Code, Opus), despachado por el orquestador.
  Es el mismo ejecutor y el mismo contexto que el intento 1 (`verify-1-auditor.md`).
- **Fecha**: 30/10/2026.
- **Revisión auditada**: `25011bf`. El código es idéntico a `51a7ff3` y el de producción está vigente
  desde `f432055`.
- **Lecciones**: las leí en el intento 1 (`knowledge-base/15_lecciones.md`, L-001 a L-064). No cambiaron
  desde entonces.

## Veredicto: **APROBADO**

No queda ningún bloqueante. B1 y B2 se resolvieron con una decisión de Juani escrita y fechada en
`tasks.md`. La evidencia técnica del intento 1 sigue vigente porque el código no cambió.

## EVIDENCIA

| # | Comando | Resultado |
|---|---|---|
| E1 | `git diff 51a7ff3..25011bf --stat` | 3 archivos: `informes/LEEME.md`, `informes/verify-1-auditor.md` y `tasks.md` (279 inserciones, 1 borrado) |
| E2 | `git diff 51a7ff3..25011bf --name-only -- backend infra web knowledge-base CHANGES.md CLAUDE.md AGENTS.md .gitleaks.toml \| wc -l` | `0` |
| E3 | `git log 51a7ff3..25011bf` | `fdaa424` (informe del auditor 1), `1b4ecac` (estado), `25011bf` (decisiones de Juani, 30/10/2026 16:50:27 -0300) |
| E4 | `tasks.md:342-347`, "Decisiones de Juani sobre los bloqueantes del auditor (30/10/2026)" | B1 se acepta como deuda justificada (D13) con la evidencia sustituta. B2 se ratifica tal como está en D-141, sin cambio de código. Palabras de Juani: "si" a "¿Las ratificás?" |

Reuso, sin repetirlo, lo que corrí yo mismo en el intento 1 sobre `51a7ff3`, en un clon normal:
- `alembic heads`: `0033 (head)`.
- `ruff check`, `ruff format --check` y `mypy`: limpios (404 archivos formateados, 367 fuentes tipadas).
- Suite completa con `test-backend.sh`: **`4736 passed, 1 xfailed`** (16:19:39 a 16:39:57). Mi conteo
  propio da 4737, igual a lo recolectado, y ninguna `F` ni `E`.
- gitleaks sobre toda la historia: sin hallazgos.
- `openspec validate`: válido.

Como E2 muestra que ningún archivo que esos chequeos cubren cambió, siguen valiendo para `25011bf`.

## JUICIO

Autor: role-auditor (Claude). Comparé los bloqueantes del intento 1 con la decisión escrita y verifiqué
la frescura con E1 y E2. Confianza: alta.

- **B1, cerrado como deuda (D13).** Juani lo decidió por escrito con el mismo criterio que BJ-1 del 3d
  (D-139). La evidencia sustituta está en el informe del intento 1: tres rondas de rompedor con 8
  hallazgos reproducidos y cerrados, los mutantes M1 a M6, los cuatro mutantes permanentes de Emiliano
  y la suite A5.
- **B2, cerrado por ratificación.** Juani ratificó P36 y P37 tal como están en D-141 y el código
  implementa exactamente eso, así que no hay nada que rehacer.
- **Pendiente al archivar**: D-141 todavía dice `Quién: Emiliano Caceres`. Como `09` sólo se agrega,
  la ratificación se registra al cerrar como decisión nueva o en la entrada de cierre del 6. D-141 no
  se edita. Lo anoto en D9b.
- No queda ningún hallazgo técnico abierto. La deuda D1 a D12 del intento 1 sigue igual, con su destino.

## SUPOSICIÓN

- La decisión de Juani llega a través de `tasks.md`, escrita por el orquestador con la identidad de git
  de Juani y una cita textual ("si"). No tengo un canal para verificar la conversación humana. Tomo el
  registro escrito y fechado como la decisión, tal como piden las reglas, y no la amplío.
- Siguen sin verificar, como en el intento 1:
  - `ensayo-roles.sh` sin ejecutar y `shellcheck` sin correr;
  - la web no la corrí (no cambió);
  - **CI remoto sin mirar sobre el SHA final**;
  - openspec 1.14.3 en vez de 1.13.0;
  - la carrera entre editar el importe y cargar una nota;
  - el costo del bucle de consultas al padrón por fila.
- No usé Engram.

## DEUDA (final)

| # | Deuda | Destino sugerido |
|---|---|---|
| D1 | El importador de Excel no limita bytes ni filas y hace una consulta al padrón por fila (contra `design.md` · Risks y D6) | **C-08 `importacion-desde-excel`**; a más tardar, el change de pantallas de gastos antes de exponer la ruta |
| D2 | El comentario de `gastos/adaptadores/excel.py` es falso: una fórmula con valor en caché entra como su valor (reproducido) | **C-08** |
| D3 | El vecino no ve por id su propio cargo particular | **C-16 `portal-del-vecino`** |
| D4 | `complejos/aplicacion/errores.py` (viene del 3a) pierde la explicación del validador en el 422 | **C-26 `pulido-web-3`** |
| D5 | El guardia de F2-1 sólo se prueba con dobles (por HTTP es inalcanzable) | **C-08**, o el primer consumidor que llame a `editar_gasto` sin pasar por HTTP |
| D6 | No hay test de concurrencia entre editar el importe y cargar una nota | **C-28 `revisiones-independientes`** |
| D7 | `ensayo-roles.sh` con cabeza `0033` sin ejecutar; `shellcheck` sin correr localmente | **C-23 `humo-y-ci`** |
| D8 | `.gitleaks.toml` y `.gitleaksignore` cubren el mismo falso positivo de `a6bb954` | **C-23** (junto con DA-12) |
| D9 | `test_gastos.py` cita `D-141-bis` (la columna `complejo.cuit`), que no existe en `09` | **el cierre de este change**: decisión nueva o quitar la cita |
| D9b | Registrar en `09` que Juani ratificó P36 y P37 (30/10/2026) sin editar D-141 | **el cierre de este change** |
| D10 | openspec instalado 1.14.3, fijado 1.13.0 | **C-23** |
| D11 | Sin CI sobre el SHA final | **quien mergee el PR #4**, antes del merge (L-042) |
| D12 | El change de pantallas de HU-A3/HU-A3b no tiene nombre ni lugar en el roadmap (D-140) | **Juani**, al planificar |
| D13 | Faltan los informes originales de revisor del plan, rompedor y auditor de Emiliano, y su RED de los bloques 2 a 5 es de setup (`ImportError`/`ModuleNotFoundError`). Aceptado por Juani el 30/10/2026 con evidencia sustituta | **Cerrada como deuda aceptada** (como DA-11 del 3d); queda declarada en `LEEME.md` y se cita en la ficha 6 al archivar. Prevención: la lección de abajo, para **C-28** y para quien planifique el próximo change de un desarrollador nuevo |

## LECCIONES

Son las mismas dos que propuse en el intento 1, para agregar a `15_lecciones.md` al cerrar:

- **Un comentario que describe lo que hace una librería se prueba contra la librería.** Si un
  comentario o un design promete un comportamiento de seguridad de una dependencia (que no evalúa, que
  no sigue enlaces, que acota el tamaño), tiene que haber un test con la entrada adversaria mínima, o
  el texto dice "no verificado". El caso fue `openpyxl` con `data_only=True`.
- **La revisión independiente de un PR ajeno no reemplaza al revisor del plan.** Pasó en el 3d y en el
  6: los dos terminaron en una decisión de Juani sobre informes faltantes. Con MEDIUM o más, el revisor
  del plan corre antes del apply, o su falta se declara en el proposal desde el principio.

## Fuentes leídas

- **Memoria**: los artefactos del change (`tasks.md`, incluida la sección de decisiones de Juani), mi
  `verify-1-auditor.md`, `LEEME.md` y la lista de `openspec/changes/archive/` (16 changes, ya revisada
  en el intento 1). No usé Engram.
- Los diffs y el log de E1 a E3.

## Contaminación

Este informe sale del mismo contexto que el intento 1, así que no es una mirada nueva e independiente.
La decisión de Juani llegó por el brief del orquestador y la contrasté con el texto de `tasks.md`
(E4).

## Próxima acción

El orquestador puede seguir con el cierre documental: el archivo del change, la KB según Knowledge Base
Impact, D9 y D9b, las lecciones y la deuda en la ficha 6. APROBADO no autoriza push ni merge del PR #4.
Antes de mergear hace falta CI verde sobre el SHA final (D11).
