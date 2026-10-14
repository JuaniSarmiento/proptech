# Preguntas abiertas para Alberto

> Las respuestas que sólo Alberto puede dar o conseguir, ordenadas por urgencia. Cada una tiene el
> contexto, las opciones y lo que proponemos, para que alcance con un "sí" o con un comentario. La
> lista completa de preguntas abiertas, con las que no dependen de él, está al final de
> [`decisiones.md`](decisiones.md). Cada respuesta se convierte en una decisión nueva ahí.

**Cómo contestar**: citando el número de cada pregunta, por mensaje o editando la tabla del final. Si
alguna no la sabés, ponelo así: también es una respuesta.

## Lo urgente

### P1 · El edificio piloto

- **Contexto**: es la prueba de que todo funciona. El primer hito es reproducir al centavo la última
  liquidación de un edificio real; sin sus datos no hay contra qué medir.
- **Opciones**: un edificio con contacto directo tuyo.
- **Lo que proponemos**: que nos digas cuál es y nos consigas, de un mes, el padrón con coeficientes,
  las facturas, el recibo del encargado y la liquidación de ese mes, y si se puede, el extracto del
  banco.
- **Cuándo**: ya. El tiempo que tarde corre en paralelo con el resto.

### P19 · ¿El piloto usa doble vencimiento?

- **Contexto**: algunos edificios tienen un primer vencimiento y un segundo con recargo escalonado. Hoy
  la base asume un único vencimiento con interés simple.
- **Opciones**: vencimiento único, o primer y segundo vencimiento con recargo.
- **Lo que proponemos**: lo que use el piloto; si no lo sabés, vencimiento único.
- **Cuándo**: antes del cambio 3.

### P22 · ¿Quién usa el editor de reglas?

- **Contexto**: el editor visual de GoRules permite cambiar las reglas de cada edificio.
- **Opciones**: sólo el equipo de PropTech; o el titular cambia valores (porcentajes, montos) y la
  estructura la armamos nosotros.
- **Lo que proponemos**: los dos niveles. El titular cambia valores con el modo "sólo valores" de
  jdm-editor, y la estructura de una regla la armamos nosotros.
- **Cuándo**: antes del cambio 6b, el del motor de reglas.

### P42 · Un administrador o contador de Mendoza para validar la plata

- **Contexto**: hay valores que decidimos nosotros y conviene que los mire alguien del oficio: la tasa
  de interés por defecto (3% mensual simple), los días de gracia, el modo de redondeo al centavo (P10),
  qué pasa cuando una unidad cambia de titular a mitad de mes (P11), el IVA de los consorcios (P17) y
  algunos casos de deuda. Las reglas que dependen de esto llevan "a validar (P42)" en su título.
- **Opciones**: una charla de una hora con un administrador o contador de tu confianza.
- **Lo que proponemos**: que nos presentes a alguien; llevamos la lista de puntos armada.
- **Cuándo**: antes del cambio 4, la cuenta corriente.

## Lo que puede esperar un poco

### P9 · Qué traen los extractos de los bancos de Mendoza

- **Contexto**: para cruzar pagos con el banco necesitamos saber si cada banco informa el CBU o el
  nombre de quien transfirió y el concepto completo.
- **Opciones**: un extracto de muestra de cada banco que usan los administradores, con los datos
  personales tapados.
- **Lo que proponemos**: que nos consigas uno o dos extractos reales, anonimizados.
- **Cuándo**: antes del cambio 9.

### P14 · El plazo para entregar el libre deuda

- **Contexto**: ya está definido quién firma el certificado y qué incluye. Falta en cuántos días hay
  que entregarlo.
- **Opciones**: lo que diga la normativa o la práctica en Mendoza.
- **Lo que proponemos**: lo que uses vos hoy.
- **Cuándo**: antes del cambio 10b.

### P15 · Si un mes los ingresos superan los gastos

- **Contexto**: un consorcio que alquila cocheras o la terraza puede tener un mes con más ingresos que
  gastos ordinarios. Hoy el sistema frena la emisión en ese caso.
- **Opciones**: pasa como crédito al mes siguiente; va al fondo de reserva; otra cosa.
- **Lo que proponemos**: crédito al mes siguiente, salvo que el reglamento diga otra cosa.
- **Cuándo**: antes del cambio 6.

### P16 · La parte de las unidades del propio consorcio

- **Contexto**: una portería o un departamento del consorcio no paga intereses. Falta saber qué pasa
  con su parte de cada gasto.
- **Opciones**: se reparte entre las demás unidades; o se registra como gasto del consorcio.
- **Lo que proponemos**: lo que diga el reglamento; si no lo dice, se reparte entre las demás.
- **Cuándo**: antes del cambio 3.

### P20 · Quién aprueba una condonación de intereses

- **Contexto**: cuando un vecino discute un recargo y se lo perdonan.
- **Opciones**: el titular solo, con registro; o el consejo cuando supera un monto.
- **Lo que proponemos**: el titular solo, con el motivo registrado y visible para el consejo.
- **Cuándo**: antes del cambio 10b.

### P45 · Validar la propuesta de valor y el precio

- **Contexto**: el precio de partida sale de tu landing, frente a los ARS 2.950 por unidad de los
  líderes, pero nadie del rubro lo confirmó todavía.
- **Opciones**: entre 3 y 5 entrevistas cortas con administradores de Mendoza; o seguir sin validar.
- **Lo que proponemos**: las entrevistas, con una guía corta que armamos nosotros. Necesitamos que nos
  presentes a los administradores.
- **Cuándo**: antes del hito M2.

## Sobre el repositorio

### P43 · El material de ProTecc en el repositorio público

- **Contexto**: el repositorio es público. Tus documentos originales no están, pero la base cita casos
  de ProTecc v3.5 y una exploración (`openspec/exploraciones/2026-10-12-dolores-protecc.md`) resume
  tus principios, tus casos y tus preguntas.
- **Opciones**: puede quedar público; o lo sacamos del repositorio, también del historial.
- **Lo que proponemos**: que nos digas si te parece bien que quede. Si preferís que no, lo movemos a
  una carpeta privada y las citas quedan como "principio N de Alberto".
- **Cuándo**: antes de darle visibilidad al repositorio.

### P44 · Licencia del código

- **Contexto**: sin una licencia, nadie puede reutilizar el código legalmente, aunque esté público.
  También falta decir cómo se reporta un problema de seguridad.
- **Opciones**: reservar el código (sin licencia, o pasar el repositorio a privado); o licenciarlo.
- **Lo que proponemos**: reservarlo por ahora y sumar un `SECURITY.md` con un contacto para reportar
  problemas de seguridad.
- **Cuándo**: antes del primer despliegue público.

### P46 · Nombres propios en el repositorio público

- **Contexto**: `CLAUDE.md`, el README y `decisiones.md` nombran a tu familia y a un docente.
- **Opciones**: quedan como están; o los reemplazamos por roles ("el socio", "el docente").
- **Lo que proponemos**: que nos confirmes si te parece bien. Si no, los sacamos.
- **Cuándo**: antes de darle visibilidad al repositorio.

## Hoja de respuesta

| Pregunta | Respuesta | Comentario |
|---|---|---|
| P1 · Edificio piloto y sus datos | ☐ Te los paso ☐ Todavía no | |
| P19 · Doble vencimiento | ☐ Único ☐ Doble | |
| P22 · Editor de reglas | ☐ Dos niveles ☐ Otra | |
| P42 · Charla con administrador o contador | ☐ Te presento a ☐ No | |
| P9 · Extractos de muestra | ☐ Te los paso ☐ No | |
| P14 · Plazo del libre deuda | Días: | |
| P15 · Ingresos mayores que gastos | ☐ Crédito ☐ Fondo ☐ Otra | |
| P16 · Unidades del consorcio | ☐ Se reparte ☐ Gasto | |
| P20 · Aprobar condonación | ☐ Titular ☐ Consejo | |
| P45 · Entrevistas de precio | ☐ Te presento a ☐ No | |
| P43 · ProTecc público | ☐ Sí ☐ Sacarlo | |
| P44 · Licencia | ☐ Reservar ☐ Licenciar | |
| P46 · Nombres propios | ☐ Quedan ☐ Sacarlos | |
