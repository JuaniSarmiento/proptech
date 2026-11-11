# Método Rein

Trabajamos por historias de usuario verticales, con documentación breve y progresiva. La persona decide el resultado esperado; el orquestador coordina y verifica; el constructor implementa. Las instrucciones orientan al agente: no constituyen un sandbox ni bloquean técnicamente sus herramientas.

## Inicio del proyecto

Conversar antes de programar: propósito, usuarios, alcance de la primera versión, exclusiones, fuentes de datos y stack. Registrar sólo decisiones acordadas en README.md y las historias principales en HISTORIAS.md. No generar una especificación extensa por anticipado. La primera historia entrega un esqueleto andante: aplicación ejecutable, una rebanada mínima de las capas necesarias y una forma de comprobarla.

## Entorno

Al arrancar el proyecto, y cuando cambie, el orquestador comprueba con un intento real qué puede ejecutar (contenedores, red, base de datos, navegador) y lo registra en el archivo de estado junto con lo que le toca correr a la persona. Con esa tabla prepara de entrada los comandos que la persona ejecutará; no reintenta en cada historia lo que ya sabe bloqueado ni presenta como ejecutado lo que delegó.

## Precedencia

Dentro de un proyecto con Rein, este método define el circuito de trabajo. Si instrucciones globales del cliente proponen otro flujo (otros roles, otras etapas, otros artefactos), prevalece este método; las preferencias personales que no lo contradicen, como idioma o herramientas, siguen vigentes. Ante una contradicción concreta, avisar a la persona en lugar de mezclar los dos circuitos.

## Roles y contexto

El agente principal actúa como orquestador. Habla con la persona, mantiene el backlog, prepara el brief, delega la implementación y comprueba la entrega. El constructor es un subagente separado que desarrolla la historia. Si el entorno no permite delegación, informar la limitación antes de sustituir ese circuito; no fingir que hubo un subagente.

El constructor recibe el brief y lee README.md, la historia, el archivo de estado (`obsidian.md` si el proyecto lo tiene, si no `ORQUESTADOR.md`) y las instrucciones aplicables. No recibe una tarea cruda ni necesita reconstruir toda la conversación. Debe comunicar contradicciones, decisiones pendientes o bloqueos al orquestador.

Un constructor por historia, con un brief acotado al contexto que necesita. Qué modelo o herramienta construye lo decide la persona; si hay que sustituirlo (por ejemplo, por falta de cupo), se pide su OK y la sustitución queda registrada en la historia.

## Brief de una historia

Dentro de HISTORIAS.md, registrar: identificador, estado, objetivo observable, alcance y exclusiones, criterios de aceptación con identificadores, dificultad, riesgos, dependencias y guion de demo. Añadir decisiones técnicas sólo cuando ayuden a ejecutar. Dificultad y riesgo son distintos: una modificación pequeña puede afectar datos sensibles.

- Baja: cambio acotado, comprobaciones focalizadas.
- Media: integración o lógica relevante, ejemplos de borde y pruebas de regresión focalizadas; TDD donde aporte.
- Alta o riesgo alto: investigar incertidumbres antes de construir, pruebas de bordes y fallos, TDD en lógica crítica y revisión adversarial con enfoque independiente.

Una revisión adversarial puede ser una sesión independiente del orquestador; no exige un tercer perfil instalado. Cambiar de modelo puede ayudar, pero no garantiza independencia ni corrección. Fijar presupuesto y condición de parada para investigaciones; se puede cerrar una investigación con resultado negativo, sin presentar una funcionalidad inexistente.

## Aceptación antes de implementación

El constructor no escribe ni modifica las pruebas que deciden la aceptación de su propia entrega. El orquestador transforma los criterios acordados en pruebas ejecutables en aceptacion/<HU>/ antes de delegar. La persona y el orquestador aprueban el contrato, los identificadores esperados y el guion de demo. Congelar en Git y anotar en la historia el SHA aprobado y el comando de ejecución. Si faltan Git, la aprobación o una forma ejecutable de verificar un criterio, señalarlo y resolverlo antes de declarar congelada la aceptación.

El constructor puede escribir pruebas unitarias y de integración de apoyo. No cambia el contrato de aceptación para conseguir un resultado verde. Si descubre un criterio incorrecto, solicita una decisión; un cambio aprobado exige otro commit y otro SHA, con el motivo registrado.

Un criterio de interfaz se verifica en un navegador real con la pantalla renderizada (clics, nombres accesibles, errores de consola): las pruebas de la API solas no alcanzan. Si sólo existe el sistema en uso, la prueba lo recorre en sólo lectura e intercepta las escrituras.

Al verificar, el orquestador recupera aceptacion/<HU>/ del commit aprobado en un entorno separado, mediante git show o un worktree; no confía en la copia del constructor. Ejecuta ese contrato contra el código entregado y compara casos esperados con casos realmente ejecutados: faltantes, skips o selección parcial no cuentan como éxito. No basta comprobar que la carpeta local tenga el SHA correcto. Este aislamiento simple no impide que código malicioso manipule el proceso: no es una barrera de seguridad.

## Construcción y validación

Trabajar una historia a la vez salvo paralelismo explícito, con límites de archivos y dependencias definidos. Cada historia cruza base de datos, backend y frontend cuando el comportamiento lo necesita; no dividir automáticamente por capa.

El constructor corre sólo comprobaciones focalizadas al cambio y comunica comandos, resultados y límites. Ningún agente corre la suite completa: la persona la ejecuta cuando corresponda y comparte la evidencia. El orquestador identifica qué regresiones y comprobaciones adicionales son necesarias; no afirma haberlas ejecutado sin evidencia. Las pruebas de aceptación de la historia se ejecutan de manera focalizada por el orquestador. Usar datos y entornos aislados; no tocar bases personales o producción para validar.

Si el sistema ya está en uso (un servicio corriendo, archivos servidos en vivo), el constructor construye y prueba en una copia o rama aparte y activa en un solo paso al final, con respaldo de los datos que migre. Nunca deja a la persona frente a un despliegue a medio hacer.

## Estados y cierre

HISTORIAS.md contiene cuatro estados: Pendiente, En proceso, Lista y Terminada.

- Pendiente: identificada, todavía no se implementa.
- En proceso: se acuerda el contrato o se construye y corrige.
- Lista: entrega preparada para revisión; registrar evidencia disponible y verificaciones pendientes. No equivale a aceptación.
- Terminada: el orquestador verificó el contrato congelado y las regresiones requeridas, y la persona recorrió la demo y aceptó explícitamente.

Si la persona rechaza la demo, volver a En proceso y anotar el motivo. El silencio no es aceptación. No marcar Terminada sólo porque el constructor diga que terminó o las pruebas pasen.

## Cerrar antes de abrir

Una entrega sin demo es trabajo a medio terminar. Con dos historias en Lista no se delega construcción nueva: el orquestador propone una sesión de demos. Sólo la persona puede levantar ese límite, por escrito y para una historia concreta.

En la sesión de demos, el orquestador presenta cada historia en Lista con su guion criterio por criterio, la evidencia verificada y lo que falta, y la persona decide: Terminada, o de vuelta a En proceso con el motivo. Si prefiere postergarla, vuelve a Pendiente con el motivo; no hay un quinto estado. Al terminar, HISTORIAS.md y el archivo de estado reflejan cada decisión.

## Documentación viva

Mantener README.md (cómo ejecutar y decisiones vigentes), HISTORIAS.md (backlog, contratos y evidencia) y el archivo de estado (contexto mínimo para retomar, bloqueos y próximo paso). Actualizarlos al cerrar y al cambiar una decisión importante. Eliminar contexto obsoleto y enlazar evidencia, sin copiar logs enormes. Registrar restricciones concretas con su razón; no acumular mandatos vagos.

El archivo de estado es `obsidian.md` si el proyecto lo tiene (archivo o enlace a su nota viva) y reemplaza a ORQUESTADOR.md, que entonces no se crea; si no, es ORQUESTADOR.md. Con `obsidian.md`, las cinco secciones de estado viven en la nota (frontmatter `estado` y `ultimo`, Estado actual, Próximos pasos e Historial) y se actualiza al cerrar cada día de trabajo: se reescribe lo que describe el presente y se apila lo histórico con fecha. Sin él, ORQUESTADOR.md no supera unas cuarenta líneas y mantiene cinco secciones fijas: Objetivo, Entorno, Historias abiertas (una línea por historia no Terminada: estado, qué falta, bloqueo si lo hay, próximo paso), Decisiones vigentes y Próximo paso. Se reescribe, no se apila: al actualizarlo se borra lo que dejó de ser cierto. Lo aceptado no se repite acá: las historias Terminadas, su evidencia, SHA y comandos viven en HISTORIAS.md. Si un ORQUESTADOR.md existente no tiene este formato, el orquestador lo reescribe así la próxima vez que lo actualiza, conservando sólo lo vigente. Si una restricción se repite en varios párrafos, se escribe una vez como decisión vigente.

No agregar tres documentos nuevos por cada cambio. Los archivos de aceptación, datos de evidencia y documentación técnica específica se crean sólo cuando hacen falta. No registrar secretos. El instalador no descarga skills ni configura permisos, servicios o credenciales. Protecciones con señuelos, dependencias externas fijadas y auditoría ampliada quedan para una evolución explícita del circuito.
