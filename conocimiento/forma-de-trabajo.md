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
   (acceso, cuenta corriente, importación desde Excel, liquidación, pagos y 10b, D-077); en los demás sigue el orquestador.
2. **Construir.** El constructor implementa las tareas en orden, con TDD, y devuelve qué hizo, qué
   comandos corrió y su salida.
3. **Romper.** El rompedor recibe el cambio terminado y trata de romperlo. Si encuentra fallas, vuelve
   al paso 2 con los tests que fallan. Si no encuentra nada, lo dice en una línea con lo que probó.
   **Salvo que ya se dieron tres vueltas** (tope de vueltas, D-092, más abajo): ahí el rompedor no
   vuelve al paso 2, va directo al paso 4 con su informe final.
4. **Auditar.** El auditor revisa todo y responde **OK** o **NO con motivos**. Si es NO, vuelve al
   paso 2. **Un cambio está aprobado cuando el auditor da el OK.**
5. **Archivar.** Se actualiza `conocimiento/` según el "Knowledge Base Impact" (lo vigente se
   reescribe, las decisiones se agregan), se archiva el cambio en OpenSpec y se commitea.

**Tope de vueltas (D-092)**: si entre construir, romper y auditar se dan tres vueltas sin llegar al
OK, el rompedor **ya no vuelve al constructor**. En vez de eso: el rompedor entrega su informe final
con el diagnóstico de cada hallazgo (severidad, si lo demostró, impacto hoy y a futuro, recomendación)
directo al auditor; el auditor separa lo que bloquea de lo que es deuda aceptable y da su veredicto
sobre esa base; el veredicto llega **textual** a Juani (ver "Lo que cada agente devuelve"), que decide
si se cierra con la deuda anotada o se pide otra vuelta. No se sigue iterando a ciegas entre
constructor y rompedor.

**La corrida de cierre va después de la última vuelta (D-092, L-010)**: la tarea de cierre (7.1 o la
que corresponda, L-003) se corre **después de la última vuelta de correcciones**, nunca antes. Si el
código cambia después de esa corrida, la corrida queda vencida aunque siga en verde y hay que
repetirla sobre el código final.

**El auditor lee los informes originales (D-092)**: nunca un resumen armado por el orquestador. El
orquestador puede transcribirlos para pasarlos de un agente a otro, pero el auditor trabaja sobre lo
que cada agente escribió, no sobre una síntesis.

**Mutar para ver el rojo sin commitear (D-092, L-013)**: mientras un cambio no está commiteado, no
hay `git diff` posible contra "el código antes de mutarlo". Antes de mutar código a propósito (para
una prueba de mutación, por ejemplo), sacar una copia previa (`git stash`, o un commit local temporal
que se descarta después) y comparar con un diff real contra esa copia antes de seguir. Decirlo en el
informe.

## Escalado por riesgo

| Tipo de cambio | Ciclo |
|---|---|
| **Toca plata o tiene peso legal** (2, 4, 5, 6, 7, 8, 9 y 10b del roadmap; de esos, 2, 4, 5, 7, 8 y 10b además llevan la aprobación de Juani antes de codear, D-077) | Completo: constructor, rompedor y auditor por separado |
| **Chico o de sólo lectura** (10a, 12, 13; el 12 con revisión previa por ser HIGH) | Constructor y después **una sola pasada que rompe y audita** (un agente con los dos trabajos) |
| **Infraestructura y el resto** (1a, 1b, 1c, 1d, 3, 6b, 11, 14, 15; el 1d, el 3 y el 12 son HIGH: se propone y se espera la revisión de Juani, D-087) | Completo |

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
