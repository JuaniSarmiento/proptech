# Knowledge base report · 3f `ejemplo-robusto` (C-27, 04/11/2026)

Unión del Knowledge Base Impact de `proposal.md` y del diff real del change (`9649471..` la rama
`change/ejemplo-robusto`, con `main` integrado en `f1231b0`).

| Documento | Estado | Qué |
|---|---|---|
| `08_arquitectura_propuesta.md` | REWRITTEN | El comando del ejemplo corre sin Redis (`ConfiguracionDelEjemplo`) y sale con un código por familia de error. No estaba en el impacto del proposal: lo pide el diff de `configuracion.py` |
| `09_decisiones_y_supuestos.md` | APPENDED | D-145: códigos de salida, edificio por nombre, sin Redis, O1 como interpretación de D-112 (para Juani), excepción de publicación de Giuliano y cuenta de intentos por gate |
| `12_fichas_de_changes.md` | REWRITTEN | Ficha 3f archivada, con la corrección de "nada la crea con dos"; filas del 3f de la deuda de `acceso-de-desarrollo` marcadas como cerradas; tabla nueva "Deuda del cierre del 3f" (DE-1 a DE-12) |
| `15_lecciones.md` | APPENDED | L-068 a L-072, las que propuso el auditor |
| `CHANGES.md` | REWRITTEN | C-27 `[x]` y ✅ en el árbol |
| `CLAUDE.md` / `AGENTS.md` | REWRITTEN | Estado: 3f archivado; idénticos (`diff` vacío) |
| `openspec/specs/datos-semilla/spec.md` | REWRITTEN (sync) | Requisito de la carga modificado y dos requisitos nuevos (errores y códigos; sin Redis) |

**Sin cambios**: `01`, `02`, `03`, `04`, `05`, `06`, `07`, `10`, `11`, `13`, `14`, `16`. El change no
toca el modelo de datos, las reglas, los permisos ni la web. La tabla de códigos vive en el spec y en el
`README.md`, que el change ya actualizó.

**PENDING**:
- O1 (DE-3): Juani ratifica o cambia la interpretación de D-112 que registra D-145.
- DE-12: el conteo `N passed` del run `41767075030`, si alguien con login lo pega en `tasks.md` 8.1.
- `obsidian.md`: no existe en esta máquina (es el symlink local de Juani); no se actualizó.
- Heredado del 6 (`2026-10-30-gastos-y-cargos/knowledge-base-report.md`): D12, resuelto después por
  D-144 (31/10/2026). No queda pendiente heredado.
