# Forma de trabajo

Cómo se construye cada cambio del MVP. **Se reescribe** cuando cambia el proceso; el porqué va a
`decisiones.md` (D-048).

## Quiénes

- **Juani**: el único desarrollador y dueño del proyecto. Decide el alcance, aprueba las propuestas
  de los cambios críticos y recibe el veredicto final.
- **Claude, el orquestador**: la sesión que habla con Juani. No escribe código: arma cada pedido,
  lanza los agentes de a uno, lee lo que devuelven, decide el paso siguiente y le cuenta a Juani.
- **Los agentes**, cada uno con un solo trabajo y sin ver las conclusiones de los otros salvo lo que
  el orquestador les pase:

| Agente | Trabajo | Modelo | Puede editar |
|---|---|---|---|
| **Proponente** | Escribe la propuesta, el diseño y las tareas del cambio en `openspec/changes/` | opus | Sólo los artefactos del cambio |
| **Constructor** | Implementa las tareas con TDD estricto: ve fallar cada test antes de escribir el código | sonnet | Sí |
| **Rompedor** | Intenta romper lo construido: entradas límite, pagos simultáneos, otro edificio, datos raros, errores de red. Cada falla que encuentra la deja como un test que falla y la reproducción | sonnet | Sólo tests nuevos, nunca el código |
| **Auditor** | Lee lo que hizo y pensó cada uno (informes, diff, tests, salida de los comandos) y verifica el cambio contra su propuesta y contra `conocimiento/`. Da el veredicto | opus | No |

## El ciclo de cada cambio

```
1. Proponer ──► 2. Construir ──► 3. Romper ──► 4. Auditar ──► 5. Archivar
                     ▲               │             │
                     └── fallas ─────┘             │
                     ▲                             │
                     └──────── NO, con motivos ────┘
```

1. **Proponer.** El proponente escribe `proposal.md`, `design.md` y `tasks.md`, con las historias,
   reglas y decisiones que cubre y la sección "Knowledge Base Impact". En los cambios marcados con ⓔ
   en `mvp.md`, antes corre un explore. **Juani aprueba la propuesta de los cambios críticos**
   (acceso, cuenta corriente, liquidación y pagos); en los demás sigue el orquestador.
2. **Construir.** El constructor implementa las tareas en orden, con TDD, y devuelve qué hizo, qué
   comandos corrió y su salida.
3. **Romper.** El rompedor recibe el cambio terminado y trata de romperlo. Si encuentra fallas, vuelve
   al paso 2 con los tests que fallan. Si no encuentra nada, lo dice en una línea con lo que probó.
4. **Auditar.** El auditor revisa todo y responde **OK** o **NO con motivos**. Si es NO, vuelve al
   paso 2. **Un cambio está aprobado cuando el auditor da el OK.**
5. **Archivar.** Se actualiza `conocimiento/` según el "Knowledge Base Impact" (lo vigente se
   reescribe, las decisiones se agregan), se archiva el cambio en OpenSpec y se commitea.

**Tope de vueltas**: si entre construir, romper y auditar se dan tres vueltas sin llegar al OK, el
orquestador frena y le presenta a Juani el problema con opciones. No se sigue iterando a ciegas.

## Escalado por riesgo

| Tipo de cambio | Ciclo |
|---|---|
| **Toca plata** (2, 4, 5, 6, 7, 8 y 9 del roadmap; de esos, los críticos 2, 4, 7 y 8 además llevan la aprobación de Juani antes de codear) | Completo: constructor, rompedor y auditor por separado |
| **Chico o de sólo lectura** (10, 12, 13) | Constructor y después **una sola pasada que rompe y audita** (un agente con los dos trabajos) |
| **Infraestructura y el resto** (1a, 1b, 3, 11, 14, 15) | Completo |

El orquestador puede subir un cambio al ciclo completo si en la pasada única aparece algo serio.

## Lecciones

Antes de empezar cada cambio, **el constructor y el rompedor leen `lecciones.md`**: es la lista de
ataques y puntos ciegos que ya nos costaron una vuelta. **El auditor cierra su veredicto con una
sección LECCIONES** (lo que este ciclo enseñó, como regla general, o "ninguna") y el orquestador las
agrega a `lecciones.md` al archivar.

## Lo que cada agente devuelve

Todos informan en tres secciones, sólo las que tengan contenido:
- **EVIDENCIA**: lo que corrieron, con el comando y su salida.
- **JUICIO**: lo que opinan, con qué lo compararon y su confianza.
- **SUPUESTOS**: lo que dieron por cierto sin verificarlo.

El orquestador no resume ni suaviza el veredicto del auditor: se lo pasa a Juani tal cual.

## Reglas del proceso

- **De a un cambio por vez**, en el orden de `roadmap.md`, que tiene la ficha de cada uno. El siguiente arranca recién cuando el anterior
  está archivado.
- **Ningún agente lanza otros agentes.**
- **Git**: sin ramas, todo sobre `main`, porque trabaja una sola persona. Al archivar cada cambio,
  con el OK del auditor, se commitea y se pushea a `main` sin preguntar (autorizado por Juani,
  D-049). Cualquier otro push se pregunta.
- **El repositorio es público**: nunca secretos ni datos personales reales, ni en código ni en tests.
- **Nada se da por probado sin la salida del comando** que lo prueba, y de esta versión del código.
