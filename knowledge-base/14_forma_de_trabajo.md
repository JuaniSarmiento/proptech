# Forma de trabajo

Cómo se construye cada cambio del MVP. **Se reescribe** cuando cambia el proceso; el porqué va a
`09_decisiones_y_supuestos.md` (D-048).

## Quiénes

- **Juani**: dueño del proyecto y desarrollador. Desde el 14/10/2026 Alberto también programa, y
  Emiliano Caceres es desarrollador del equipo; cada cambio lo programa uno solo (D-022, D-093).
  Decide el alcance y recibe el veredicto final de sus propios cambios. Las propuestas CRITICAL y HIGH
  las puede aprobar él, Alberto o Emiliano, por escrito y con fecha (D-094, D-111).
- **Claude, el orquestador**: la sesión que habla con Juani. No escribe código: arma cada pedido,
  lanza los agentes de a uno, lee lo que devuelven, decide el paso siguiente y le cuenta a Juani.
- **Los agentes**, cada uno con un solo trabajo y sin ver las conclusiones de los otros salvo lo que
  el orquestador les pase:

| Agente | Trabajo | Modelo | Puede editar |
|---|---|---|---|
| **Proponente** | Escribe la propuesta, el diseño y las tareas del cambio en `openspec/changes/` | opus | Sólo los artefactos del cambio |
| **Constructor** | Implementa las tareas con TDD estricto: ve fallar cada test antes de escribir el código | sonnet | Sí |
| **Rompedor** | Intenta romper lo construido: entradas límite, pagos simultáneos, otro edificio, datos raros, errores de red. Cada falla que encuentra la deja como un test que falla y la reproducción | sonnet | Sólo tests nuevos, nunca el código |
| **Auditor** | Lee lo que hizo y pensó cada uno (informes, diff, tests, salida de los comandos) y verifica el cambio contra su propuesta y contra `knowledge-base/`. Da el veredicto | opus | No |

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
   en `01_vision_y_objetivos.md`, antes corre un explore. **La propuesta de los cambios críticos la
   aprueba Juani, Alberto o Emiliano, por escrito y con fecha** (acceso, cuenta corriente, importación
   desde Excel, liquidación, pagos y 10b, D-077, D-094, D-111); en los demás sigue el orquestador.
2. **Construir.** El constructor implementa las tareas en orden, con TDD, y devuelve qué hizo, qué
   comandos corrió y su salida.
3. **Romper.** El rompedor recibe el cambio terminado y trata de romperlo. Si encuentra fallas, vuelve
   al paso 2 con los tests que fallan. Si no encuentra nada, lo dice en una línea con lo que probó.
   **Salvo que ya se dieron tres vueltas** (tope de vueltas, D-092, más abajo): ahí el rompedor no
   vuelve al paso 2, va directo al paso 4 con su informe final.
4. **Auditar.** El auditor revisa todo y responde **OK** o **NO con motivos**. Si es NO, vuelve al
   paso 2. **Un cambio está aprobado cuando el auditor da el OK.**
5. **Archivar.** Se actualiza `knowledge-base/` según el "Knowledge Base Impact" (lo vigente se
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
| **Toca plata o tiene peso legal** (2, 4, 5, 6, 7, 8, 9 y 10b del roadmap; de esos, 2, 4, 5, 7, 8 y 10b además llevan la aprobación de Juani, Alberto o Emiliano antes de codear, D-077, D-094, D-111) | Completo: constructor, rompedor y auditor por separado |
| **Chico o de sólo lectura** (10a, 12, 13; el 12 con revisión previa por ser HIGH) | Constructor y después **una sola pasada que rompe y audita** (un agente con los dos trabajos) |
| **Infraestructura y el resto** (1a, 1b, 1c, 1d, 3, 6b, 11, 14, 15; el 1d, el 3 y el 12 son HIGH: se propone y se espera la revisión de Juani, Alberto o Emiliano, D-087, D-094, D-111) | Completo |

El orquestador puede subir un cambio al ciclo completo si en la pasada única aparece algo serio.

**Revisión proporcional al riesgo** (aprobada por Juani el 27/10/2026, al cerrar el 4b; detalle y
alternativa descartada en `knowledge-base/09_decisiones_y_supuestos.md` D-125): CRITICAL convoca
revisores de rol sólo en `propose` (nunca mientras el `apply` sigue escribiendo), un rompedor por
tanda alternando Claude y Codex, y un auditor al final; HIGH/MEDIUM se quedan con un revisor más un
rompedor; LOW se resuelve con tests y CI. Esta tabla de arriba (escalado por tipo de cambio) sigue
rigiendo qué agentes se convocan; D-125 fija cuántas pasadas de cada uno, por gobernanza.

**Verificación real con un servicio externo de identidad** (desde el 2b `login-y-usuarios`,
22/10/2026): cuando un cambio integra un proveedor externo de autenticación (Clerk y lo que venga
después), el cierre no se da por completo con tests contra un doble falso, aunque pasen todos. Antes
de archivar, **el socio que corresponda se sienta al teclado** y recorre el camino real contra la
instancia de desarrollo del proveedor (alta, invitación, aceptación, ingreso, revocación), con el
orquestador anotando hora y la fila de auditoría que deja cada paso. Es la única forma en que se
encontró el hallazgo del `__clerk_ticket` perdido (L-032): el doble falso de los tests e2e no modela
el modo restringido del proveedor real. El alcance de esa corrida puede acortarse por decisión del
socio (como pasó en el 2b, decisión de cierre 2), dejando el resto como deuda declarada, nunca
asumida como probada.

## Lecciones

Antes de empezar cada cambio, **el constructor y el rompedor leen `15_lecciones.md`**: es la lista de
ataques y puntos ciegos que ya nos costaron una vuelta. **El auditor cierra su veredicto con una
sección LECCIONES** (lo que este ciclo enseñó, como regla general, o "ninguna") y el orquestador las
agrega a `15_lecciones.md` al archivar.

## Lo que cada agente devuelve

Todos informan en tres secciones, sólo las que tengan contenido:
- **EVIDENCIA**: lo que corrieron, con el comando y su salida.
- **JUICIO**: lo que opinan, con qué lo compararon y su confianza.
- **SUPUESTOS**: lo que dieron por cierto sin verificarlo.

El orquestador no resume ni suaviza el veredicto del auditor: se lo pasa a Juani tal cual.

## Constructor con Codex (desde el 3a)

Desde el cambio 3a, el constructor puede ser **Codex (GPT-6.1-Sol, esfuerzo `xhigh`)** en vez de un
agente de Claude. Rompedor, auditor y los revisores de rol siguen siendo siempre de Claude, de otra
familia de modelo que el constructor (L-025).

- **Briefs por bloque**: las tareas del cambio se agrupan en bloques de 3 a 6, cada uno con su propio
  brief (`.git/informes-<cambio>/codex-<cambio>/brief-bloque-X.md`) más unas reglas comunes a todos los
  bloques (TDD estricto, rojo y verde pegados en `tasks.md`, tope de evidencia, conventional commits
  **sin** atribución a IA ni `Co-Authored-By`). Un brief nombra sólo lo que esa tarea necesita leer; no
  nombra, por defecto, los consumidores fuera del área que toca (L-023, L-025): eso hay que escribirlo
  a propósito cuando aplique.
- **Acceso total, autorizado por Juani el 19/10/2026**: Codex corre sin sandbox, en la máquina de
  Juani, con permiso explícito para usar Docker (sólo a través de los tests o de `infra/ci/*.sh`,
  nunca comandos sueltos que toquen contenedores de otros proyectos de la máquina), leer el repo entero
  y commitear. El **sandbox `workspace-write` no sirve** para este rol: no llega a Docker (ni siquiera
  a través de los tests) y no puede commitear, así que cada tarea con integración real o con un commit
  pendiente queda a medio hacer.
- **El orquestador compara `docker ps`** antes y después de cada bloque (mismos contenedores, ningún
  `proptech`/`proptech-clon` quedando atrás) y **revisa la atribución de cada commit** del bloque antes
  de seguir, porque es la regla más fácil de pasar por alto en una corrida larga y sin supervisión
  línea por línea.
- **Lo que Codex no puede terminar, lo termina el orquestador**: correr la suite completa o el humo
  cuando el sandbox no alcanza, commitear una tarea que Codex dejó sin commit, y la verificación
  independiente de cada bloque cerrado (L-023, L-024).
- **Medición del 19/10/2026** (cambio 3a): 22 tareas completadas en unas 2 horas de trabajo real,
  aproximadamente 1,3 millones de tokens de la cuota de ChatGPT consumidos; la ventana de 5 horas de
  Plus se agotó en aproximadamente 2,5 horas (quedó sin cuota antes de cerrar el bloque E, que terminó
  el orquestador).
- **Medición del 20/10/2026** (cambio 3b): con **Claude Sonnet como constructor** (TDD estricto, una
  vuelta de rompedor y auditor Claude Opus), cada bloque tardó alrededor de 1 hora real y consumió
  entre 450 y 550 mil tokens; Codex, sobre tareas comparables del 3a, resolvía un bloque en unos 20
  minutos. Codex vuelve a ser el constructor cuando tiene cuota disponible. El orquestador mira las
  pantallas en un navegador real después de cada bloque de UI (L-026), no sólo al final del cambio.

**Esquema del 2.2a (20/10/2026)**: Codex construye, Claude rompe y audita; Juani corre el script de
firma de la propuesta y firma aparte las correcciones posteriores que agregan reglas (RR-1 a RR-4,
`610eb4a`, L-029).

## Reglas del proceso

- **De a un cambio por vez**, en el orden de `CHANGES.md`, con la ficha detallada de cada uno en
  `12_fichas_de_changes.md`. El siguiente arranca recién cuando el anterior
  está archivado.
- **Ningún agente lanza otros agentes.**
- **Git**: sin ramas, todo sobre `main`; así se decidió cuando trabajaba una sola persona. Con dos
  desarrolladores (D-093), el criterio de ramas o turnos está abierto (P47). Al archivar cada cambio,
  con el OK del auditor, se commitea y se pushea a `main` sin preguntar (autorizado por Juani,
  D-049). Cualquier otro push se pregunta.
- **Toda pantalla lleva su ayuda "?"** (D-102, The Always-Help Rule de `DESIGN.md`, HU-T1): en un
  cambio con frontend, una pantalla sin su "?" y sin las tres partes del texto escritas no está
  terminada, y el rompedor lo verifica pantalla por pantalla.
- **El repositorio es público**: nunca secretos ni datos personales reales, ni en código ni en tests.
- **Nada se da por probado sin la salida del comando** que lo prueba, y de esta versión del código.
