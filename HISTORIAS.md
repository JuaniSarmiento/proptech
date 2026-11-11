# Historias

Backlog del ciclo de Juani con Rein (D-146). Cómo se usa: `knowledge-base/14_forma_de_trabajo.md`;
método: `.rein/METODO.md`. El estado y el próximo paso viven en `obsidian.md`; las reglas y decisiones,
en `knowledge-base/` (acá se enlazan, no se copian).

Estados: Pendiente · En proceso · Lista · Terminada. Sólo Juani pasa una historia a Terminada.

Identificadores: historias `H-001`, `H-002`…; criterios `H-001.C01`. La aceptación de cada historia
vive en `aceptacion/<H-xxx>/`.

| HU | Change | Resultado esperado | Dificultad / riesgo | Estado |
|---|---|---|---|---|

## Changes por partir en historias

- **4c `intereses-saldo-inicial-y-moroso`** (CRITICAL): propuesta y diseño en
  `openspec/changes/intereses-saldo-inicial-y-moroso/`, sin commitear y sin la firma de D-094. Falta
  acordar con Juani cómo se parte en historias.

## Plantilla de historia

### H-xxx · título

- Change: (de `CHANGES.md`) y reglas o decisiones que cubre (`R03`, `D-143`…)
- Resultado para la persona:
- Alcance y exclusiones:
- Criterios de aceptación (`H-xxx.C01`…, con ejemplos):
- Dificultad y riesgo (LOW, MEDIUM, HIGH o CRITICAL):
- Constructor (modelo elegido por Juani; cualquier cambio, con su OK y el motivo):
- Brief y archivos relevantes:
- Aceptación aprobada: SHA, comando y casos esperados:
- Rompedor (CRITICAL y HIGH): informe y fallas devueltas:
- Evidencia: aceptación del SHA aprobado, suite completa (CI o Juani), pendientes:
- Demo y aprobación de Juani (fecha, o motivo del rechazo o la postergación):
