# Forma de trabajo

Cómo se construye cada cambio del MVP. **Se reescribe** cuando cambia el proceso; el porqué va a
`09_decisiones_y_supuestos.md` (D-048, D-146).

Conviven dos ciclos sobre el mismo repositorio (D-146):

- **El de Juani, con Rein** (desde el 10/11/2026, D-146): historias con aceptación congelada antes de
  construir y demo ante Juani. Método completo en `.rein/METODO.md`; este archivo dice cómo se aplica
  en PropTech.
- **El de Alberto y el equipo, con OPSX de Active Stack v1** (D-093, D-138): `explore`, `propose`,
  `apply`, `verify` y `archive`, como dice `CLAUDE.md`.

## Quiénes

- **Juani**: dueño del proyecto y desarrollador. Decide el alcance, aprueba la aceptación de cada
  historia y es el único que pasa una historia suya a Terminada. Las propuestas CRITICAL y HIGH las
  puede aprobar él, Alberto o Emiliano, por escrito y con fecha (D-094, D-111).
- **Alberto y el equipo de desarrollo** (desde el 30/10/2026, D-138): Emiliano, Gianfranco, Neyen,
  Matías, Giuliano y Juan Cruz, cada uno con un change propio (tabla en `CHANGES.md`, "Deuda
  adelantada"). Quien recién se suma toma sólo changes LOW o MEDIUM; lo CRITICAL lo construye o lo
  supervisa un firmante de D-111.
- **Claude, el orquestador** (perfil `rein-orchestrator`): la sesión que habla con Juani. Acuerda la
  historia, escribe su aceptación ejecutable, arma el brief, delega, verifica contra el SHA aprobado y
  presenta la demo. No escribe el código de producción, salvo un cambio chico y local que Juani le pida.
- **Los agentes**, cada uno con un solo trabajo y sin ver las conclusiones de los otros salvo lo que el
  orquestador les pase:

| Agente | Trabajo | Modelo | Puede editar |
|---|---|---|---|
| **Constructor** (`rein-constructor`) | Implementa una historia con el menor cambio razonable, TDD según el riesgo; escribe sus tests de apoyo | Lo elige Juani: Codex `xhigh` si hay cuota, si no Sonnet | Sí, salvo `aceptacion/` |

**Sin rompedor (D-152)**: ninguna historia lleva revisión adversarial aparte, cualquiera sea su riesgo.
Lo que antes buscaba el rompedor (entradas límite, concurrencia, otro edificio u otra administración,
datos raros) va como criterios que tienen que fallar en la aceptación, escritos antes de construir.

## Los archivos

| Archivo | Qué lleva |
|---|---|
| `HISTORIAS.md` | El backlog de Juani: cada historia con su estado, criterios, SHA aprobado, comando y evidencia |
| `aceptacion/<H-xxx>/` | Las pruebas que deciden la historia. Las escribe el orquestador, nunca el constructor |
| `openspec/changes/<change>/` | `proposal.md` (con la firma de CRITICAL y HIGH) y `design.md` del change; sus specs |
| `obsidian.md` | El estado: qué está en curso, qué bloquea y el próximo paso. No hay `ORQUESTADOR.md` |
| `CHANGES.md` y `12_fichas_de_changes.md` | El roadmap y el detalle de cada change, como siempre |

Identificadores: las historias son `H-001`, `H-002`… y sus criterios `H-001.C01`, para no chocar con
las `HU-*` de `06_funcionalidades.md` ni con los `C-23` a `C-30` de la deuda adelantada.

## El ciclo de una historia

```
1. Acordar ──► 2. Aceptación ──► 3. Construir ──► 4. Verificar ──► 5. Demo
   (Juani)       (SHA aprobado)                                      │
                                     ▲                 │             │
                                     └── fallas ───────┴── rechazo ──┘
```

1. **Acordar.** Se parte del change de `CHANGES.md` y de su ficha. Orquestador y Juani acuerdan cada
   historia: resultado observable, qué incluye y qué no, dificultad y riesgo (son distintos), criterios
   con identificador y guion de demo. Para CRITICAL y HIGH, la propuesta del change en OpenSpec tiene
   que estar firmada antes del paso 3 (D-094, D-111). La historia se anota en `HISTORIAS.md` y en el
   tablero de Jarvis (`registrar_historia`).
2. **Aceptación.** El orquestador escribe las pruebas de cada criterio en `aceptacion/<H-xxx>/`, las ve
   fallar por aserción (no por un error de setup), Juani las aprueba, se commitean y el SHA y el comando
   quedan en la historia. Un criterio de interfaz se prueba en un navegador real.
3. **Construir.** Un constructor por historia, con un brief acotado: la historia, el SHA de la
   aceptación, los archivos que le tocan y `15_lecciones.md`. Construye con TDD según el riesgo (estricto
   en el núcleo y en todo lo que toca plata) y devuelve lo que hizo, los comandos y su salida. No toca
   `aceptacion/`; si un criterio está mal, pide la decisión y, si Juani la cambia, va otro commit y otro
   SHA con el motivo.
4. **Verificar.** El orquestador recupera `aceptacion/<H-xxx>/` del SHA aprobado en un worktree o con
   `git show`, nunca de la copia del constructor, y la corre contra el código entregado. Compara los
   casos esperados con los ejecutados: un faltante o un skip no es éxito. La historia pasa a **Lista**
   con la evidencia y lo que quede sin verificar.
5. **Demo.** El orquestador recorre el guion criterio por criterio con Juani. **Sólo Juani pasa la
   historia a Terminada, con un sí explícito**; el silencio no es aceptación. Si la rechaza, vuelve a En
   proceso con el motivo; si la posterga, a Pendiente con el motivo.

**Archivar un change**: cuando todas sus historias están Terminadas, corre el CI de GitHub sobre la rama
del change (D-154) y, en verde, se actualiza `knowledge-base/`
(ver "Documentación viva"), se corre `openspec archive`, se marca en `CHANGES.md` y se commitea y
pushea a `main` sin preguntar (D-049).

## Documentación viva: Rein más la base de conocimiento

Rein pide que la documentación crezca con el producto. En PropTech esa documentación es
**`knowledge-base/`**, que sigue siendo la fuente de verdad, más `HISTORIAS.md` y `obsidian.md`. Un
change no está terminado hasta que su documentación lo está, en el mismo trabajo y no después.

| Cuándo | Qué se actualiza |
|---|---|
| **Al acordar una historia** | `HISTORIAS.md` (la historia, sus criterios y el guion de demo); si de la charla sale una decisión, una D nueva en `09_decisiones_y_supuestos.md`; si sale una pregunta, `10_preguntas_abiertas.md` |
| **Al cambiar de estado una historia** | `HISTORIAS.md` (estado, SHA, evidencia, motivo de un rechazo) y el tablero de Jarvis |
| **Al cerrar cada día de trabajo** | `obsidian.md`: se reescribe el presente (`estado`, `ultimo`, Estado actual, Próximos pasos) y se apila el historial |
| **Al archivar el change** | La sección "Knowledge Base Impact" de su propuesta, aplicada: los archivos que se reescriben (`04` modelo de datos, `05` reglas, `06` funcionalidades, `07` flujos, `08` arquitectura, `11` glosario, `12` fichas con la deuda del cierre, `02` si cambió el stack) quedan con lo vigente; los que sólo se agregan (`09` decisiones, `15` lecciones) suman lo nuevo; `CHANGES.md`, el estado de `CLAUDE.md`/`AGENTS.md` (idénticos) y el README si cambió cómo se corre |

La KB describe el sistema; `HISTORIAS.md` describe cómo se construyó y se aceptó cada pedazo. No se
copia una en la otra: la historia enlaza la regla o la decisión (`R03`, `D-143`) y la KB no repite la
evidencia de las historias.

Estados: **Pendiente → En proceso → Lista → Terminada.** Lista no es aceptación.

**Cerrar antes de abrir**: con dos historias en Lista no se construye nada nuevo; el orquestador
propone una sesión de demos. Sólo Juani levanta ese límite, por escrito y para una historia concreta.
Una sola historia en construcción salvo paralelismo explícito.

**Tope de vueltas (D-092)**: si entre construir y verificar se dan tres vueltas sin llegar a Lista, no
se sigue iterando a ciegas. El orquestador le pasa a Juani el diagnóstico de cada criterio que no pasa
(qué falla, si está demostrado, impacto hoy y a futuro, recomendación), y Juani decide si la historia
sigue, se parte o se cierra con la deuda anotada.

**Mutar para ver el rojo sin commitear (D-092, L-013)**: antes de mutar código a propósito, sacar una
copia previa (`git stash` o un commit local temporal que se descarta) y comparar con un diff real
contra esa copia. Decirlo en el informe.

## Escalado por riesgo

| Riesgo | Qué lleva la historia |
|---|---|
| **CRITICAL** (cuenta corriente, cobros, liquidación, acceso, importación, 10b) | Firma de la propuesta antes de construir; aceptación con criterios que tienen que pasar y criterios que tienen que fallar (rechazos, aislamiento, concurrencia, bordes); TDD estricto con mutantes nombrados en lo que toca plata o seguridad |
| **HIGH** | Firma de la propuesta; aceptación con criterios que tienen que pasar y que tienen que fallar |
| **MEDIUM** | Aceptación con ejemplos de borde; TDD donde aporte |
| **LOW** | Aceptación focalizada; se resuelve con tests y CI |

Dificultad y riesgo son distintos: un cambio chico que toca plata o datos personales va por la fila de
su riesgo. El orquestador puede subir una historia de fila si aparece algo serio.

**Tests (D-146, D-154)**: el constructor corre sólo los tests de los archivos que toca, más `ruff` y
`mypy`; el orquestador corre la aceptación de la historia y la demo. **Una historia no espera al CI**:
todas las historias de un change se construyen en la misma rama `change/<nombre>`, una detrás de otra.
**El CI de GitHub y la suite completa corren una vez, al cerrar el change**: con todas sus historias
Terminadas se abre o actualiza el PR, se espera el CI en verde (lo que rompa se arregla ahí), se
archiva y se mergea a `main`. El orquestador dice en cada brief qué corre cada uno y por qué.

**Verificación real con un servicio externo de identidad** (desde el 2b `login-y-usuarios`,
22/10/2026): cuando una historia integra un proveedor externo de autenticación (Clerk y lo que venga
después), no alcanza con tests contra un doble falso, aunque pasen todos. En la demo, **el socio que
corresponda se sienta al teclado** y recorre el camino real contra la instancia de desarrollo del
proveedor (alta, invitación, aceptación, ingreso, revocación), con el orquestador anotando hora y la
fila de auditoría que deja cada paso. Es la única forma en que se encontró el `__clerk_ticket` perdido
(L-032). El alcance puede acortarse por decisión del socio, dejando el resto como deuda declarada,
nunca asumida como probada.

## Lecciones

Antes de empezar cada historia, **el orquestador y el constructor leen `15_lecciones.md`**: es la
lista de ataques y puntos ciegos que ya nos costaron una vuelta, y de ahí salen los criterios que
tienen que fallar. Al archivar el change, el orquestador agrega
lo que enseñó (como regla general, o "ninguna") a `15_lecciones.md`.

## Lo que cada agente devuelve

Todos informan en tres secciones, sólo las que tengan contenido:
- **EVIDENCIA**: lo que corrieron, con el comando y su salida.
- **JUICIO**: lo que opinan, con qué lo compararon y su confianza.
- **SUPUESTOS**: lo que dieron por cierto sin verificarlo.

## Constructor con Codex (desde el 3a)

El constructor puede ser **Codex (GPT-6.1-Sol, esfuerzo `xhigh`)**, con el perfil
`.codex/agents/rein-constructor.toml`, o un agente de Claude con `.claude/agents/rein-constructor.md`.
Lo elige Juani; cambiarlo (por ejemplo, por falta de cuota) pide su OK y queda anotado en la historia.

- **Un brief por historia**, en `.git/informes-<change>/brief-<H-xxx>.md`, con reglas comunes (TDD según
  el riesgo, no tocar `aceptacion/`, tope de evidencia, conventional commits **sin** atribución a IA ni
  `Co-Authored-By`). Un brief nombra sólo lo que esa historia necesita leer; los consumidores fuera del
  área que toca hay que nombrarlos a propósito cuando aplique (L-023, L-025).
- **Acceso total, autorizado por Juani el 19/10/2026**: Codex corre sin sandbox, en la máquina de Juani,
  con permiso para usar Docker (sólo a través de los tests o de `infra/ci/*.sh`, nunca comandos sueltos
  que toquen contenedores de otros proyectos), leer el repo entero y commitear. El sandbox
  `workspace-write` no sirve para este rol: no llega a Docker ni puede commitear.
- **El orquestador compara `docker ps`** antes y después de cada historia (mismos contenedores, ningún
  `proptech`/`proptech-clon` quedando atrás) y **revisa la atribución de cada commit** antes de seguir.
- **Lo que Codex no puede terminar, lo termina el orquestador**: commitear lo que quedó sin commit y la
  verificación independiente (L-023, L-024). La suite completa sigue siendo del CI o de Juani.
- **Mediciones**: con Codex, el 3a hizo 22 tareas en unas 2 horas reales (aprox. 1,3 millones de tokens;
  la ventana de 5 horas de Plus se agotó en 2,5). Con Claude Sonnet, en el 3b, cada bloque tardó cerca
  de una hora y entre 450 y 550 mil tokens; Codex resolvía uno comparable en unos 20 minutos. El
  orquestador mira las pantallas en un navegador real después de cada historia con UI (L-026).

## Reglas del proceso

- **Una historia en construcción por vez**, en el orden de `CHANGES.md`, salvo paralelismo explícito.
- **Ningún agente lanza otros agentes.**
- **Git**: el ciclo de Juani trabaja sobre `main`; el equipo trabaja en ramas `change/*` con PR (P47
  sigue abierta para el criterio general). Al archivar un change con todas sus historias Terminadas,
  se commitea y se pushea a `main` sin preguntar (D-049). Cualquier otro push se pregunta.
- **Toda pantalla lleva su ayuda "?"** (D-102, The Always-Help Rule de `DESIGN.md`, HU-T1): una pantalla
  sin su "?" y sin las tres partes del texto no está terminada, y la aceptación lo prueba.
- **El repositorio es público**: nunca secretos ni datos personales reales, ni en código ni en tests.
- **Nada se da por probado sin la salida del comando** que lo prueba, y de esta versión del código.
