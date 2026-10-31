## Why

El 1d `respaldos-y-restauracion` cerró el 14/10/2026 como **OK con deuda anotada** (D-095): cinco
hallazgos del rompedor (F4, F5, F6, F8 y "14 copias no son 14 días") se aceptaron como deuda porque
ninguno rompía la letra de la spec, y el dueño quedó en el 15 (piloto). El 2a, el 2b y el 3a sumaron
tres más: el volcado con el rol equivocado no tiene prueba con `pg_dump` real, `mkdir -p
infra/datos-respaldos` sigue siendo un paso manual del README, y no existe ningún procedimiento para
**conmutar la aplicación** a una base restaurada — `restaurar.sh` restaura siempre en una base aparte
y ahí termina.

D-138 (30/10/2026) junta esos ocho ítems en este change y los adelanta: dejar la recuperación de la
base para el 15 significa descubrir en el piloto, con datos reales de expensas, que un backup se
restaura pero nadie sabe cómo volver a producción con él. Un backup que se restaura en una base que
nadie usa todavía no es una recuperación.

Reglas y decisiones que cubre: D-043 y D-047 (punto 4, backups automáticos), D-087 (el 1d como
cambio HIGH), D-091 y D-095 (la deuda aceptada al cerrar), D-098 y D-110 (las filas de deuda del 2a y
de la regresión del 27/10/2026), D-130 (reparto de la regresión), D-138 (creación de este change) y
D-094/D-111 (quién firma HIGH). Avanza H46 (restauración probada) de M3. No toca ninguna regla de
negocio R01-R41: es infraestructura de recuperación, no cálculo.

## What Changes

- **F4 · retención con el reloj del host atrasado**: hoy `aplicar_retencion` ordena por nombre
  (`respaldar.sh:101`) y excluye por nombre exacto sólo el archivo del ciclo en curso; con el reloj
  atrasado, los backups nuevos ordenan como los más viejos y la retención deja **1 backup real de 7**.
  Pasa a conservar los `RESPALDO_CONSERVAR` más recientes por tiempo de modificación, no por nombre,
  sin dejar de respetar el patrón de nombre propio (L-006) ni de proteger el archivo del ciclo.
- **F5 · SIGTERM**: `respaldar.sh` no tiene ningún `trap`, así que `docker compose stop` espera 10 s y
  manda `KILL`. Se agrega manejo de `SIGTERM`/`SIGINT` que corta el `sleep` del modo continuo, borra
  el `.parcial` del volcado en curso y sale limpio, con su evento de log.
- **F6 · la carrera del 503**: un 503 de `GET /api/salud` puede salir **sin ninguna línea
  `salud_degradada`** (reproducido 1 de 18 veces por el rompedor del 1d; ventana de menos de 1 ms
  entre el vencimiento del plazo y el `_informar_una_sola_vez` del hilo). Primero se repite la ráfaga
  del rompedor y se pega su salida; si se reproduce, se arregla para que **ningún** 503 pueda salir sin
  su línea; si no se reproduce con la ráfaga corrida, se descarta por escrito con el comando y la
  salida (L-016: "0 apariciones" sólo vale nombrando qué puede producirlas).
- **F8 · logs en JSON**: `error_salir` (`respaldar.sh:14`) escribe `echo "error: $1"` a stderr, texto
  plano al lado del `printf` JSON de `logear`. Pasa a emitir una línea JSON con el mismo esquema
  (`ts`, `nivel`, `servicio`, `evento`), sin la salida de ninguna herramienta ajena (L-007).
- **"14 copias" no son 14 días**: `RESPALDO_CONSERVAR` cuenta archivos, no días; con muchos reinicios
  del stack, 14 copias pueden cubrir una tarde. Se decide y se escribe: se mantiene la retención por
  cantidad y se agrega un **piso por antigüedad** (`RESPALDO_CONSERVAR_DIAS`, validado con la misma
  batería de L-008), de modo que nunca se borre un backup que sea el más nuevo de su día dentro de la
  ventana. La alternativa descartada y el porqué quedan en `design.md`.
- **Conmutar la aplicación a una base restaurada**: herramienta nueva
  (`infra/respaldos/conmutar.sh`) y su paso en el README. Verifica que la base destino existe, que su
  revisión de Alembic es exactamente la cabeza del repositorio y que la RLS forzada y las políticas
  siguen puestas; recién entonces conmuta. Se niega a conmutar a una base que no pasó esas tres
  verificaciones, y nunca borra la base que deja de usarse.
- **`mkdir -p infra/datos-respaldos` sin paso manual**: hoy es una línea del README
  (`README.md:58,68-71`) y olvidarla deja la carpeta creada por Docker como root, con el contenedor de
  respaldos reiniciando en bucle. La carpeta se crea con el dueño correcto sin depender de quien
  levanta el stack.
- **Volcado con el rol equivocado contra `pg_dump` real**: hoy el escenario "Volcado con el rol
  equivocado" se prueba con un binario falso (`backend/tests/infra/test_respaldos.py:905-940`,
  `FAKE_PG_DUMP_FALLA`) más una garantía estática del compose (`test_compose.py:510`). Se agrega un
  test de integración que corre `pg_dump` real contra la base real con las credenciales de
  `proptech_app` y exige que el volcado falle, que no quede ningún `.dump` y que el servicio quede no
  saludable.

No hay cambios **BREAKING**: ninguna variable existente cambia de significado y
`RESPALDO_CONSERVAR_DIAS` nace con un valor por defecto que reproduce el comportamiento de hoy.

## Capabilities

### New Capabilities

Ninguna. Todo el scope cae en dos capacidades que ya existen; crear una tercera partiría en dos la
descripción de los respaldos.

### Modified Capabilities

- `respaldos-de-la-base`: la retención deja de ordenar por nombre y gana un piso por antigüedad (F4 y
  "14 copias"); el servicio responde a `SIGTERM` sin perder el ciclo ni dejar un `.parcial`
  (F5); todas las líneas de su log son JSON, incluidas las de error de configuración (F8); la carpeta
  del host se crea sola con el dueño correcto; el escenario "Volcado con el rol equivocado" exige
  `pg_dump` real; se agrega el requisito de **conmutar la aplicación** a una base restaurada con sus
  tres verificaciones previas.
- `entorno-de-ejecucion`: el requisito de salud de la API pasa de "exactamente una línea
  `salud_degradada` por verificación fallida" a "ningún 503 sale sin al menos una línea, y nunca más
  de una por dependencia y pedido" (F6).

## Impact

- **Código**: `infra/respaldos/respaldar.sh` (retención, `trap`, `error_salir`, variable nueva),
  `infra/respaldos/conmutar.sh` (nuevo), `infra/compose.yaml` (creación de la carpeta con el dueño
  correcto, variable nueva del servicio `respaldos`), `infra/.env.example`, `README.md` (el `mkdir`
  deja de ser un paso y aparece el procedimiento de conmutación, más la tabla de variables),
  `backend/src/proptech_api/salud.py` (sólo si F6 se reproduce).
- **Tests**: `backend/tests/infra/test_respaldos.py`, `test_restaurar.py`, `test_compose.py`,
  `test_readme_variables.py`, un archivo nuevo para la conmutación y uno de integración para el
  volcado con el rol equivocado; `backend/tests/unitarios/test_salud.py` si F6 se reproduce.
- **Infraestructura**: nada publicado a Internet, ningún puerto nuevo, ninguna migración de base. El
  rol de respaldo (`proptech_respaldo`) no cambia y no se agrega ningún `GRANT`.
- **Dominios CRITICAL**: este change **no escribe en `cuenta_corriente` ni en `pagos`** y no agrega ni
  modifica ninguna regla de plata. Pero la conmutación apunta la aplicación a otra base, y esa base
  contiene el libro de movimientos: conmutar a una base con la revisión de migraciones equivocada o
  con la RLS floja sería un daño sobre datos CRITICAL. Por eso la herramienta verifica las tres
  condiciones **antes** de conmutar y se niega si alguna falla, y por eso el change no se construye
  sin la firma de abajo. Si durante el apply apareciera la necesidad de tocar código de
  `cuenta_corriente` o `pagos`, ese pedazo sale del change y se propone aparte.

## Gobernanza

**Nivel: HIGH** (D-094, D-111). Tres motivos, cada uno suficiente por su cuenta: la conmutación
cambia a qué base apunta la aplicación en producción; `restaurar.sh` ya borra bases (`dropdb`) y la
herramienta nueva corre en el mismo vecindario; y el servicio toca el disco del host por un bind
mount con credenciales de la base.

> **Firma requerida antes del apply.** Este change necesita la aprobación escrita y con fecha de
> **Juani, Alberto o Emiliano** (D-094, extendido a Emiliano por D-111) antes de escribir una sola
> línea de código. La firma **no** hace falta para generar estos artefactos de planificación; sí para
> arrancar `/opsx:apply`. Emiliano es firmante y puede firmar su propio change: D-094 no exige que
> firme otro (precedente: Alberto firma los suyos; `acceso-de-desarrollo`, D-110/D-111).
>
> **Firma: Emiliano Caceres, 2026-10-31.** Firmo el scope completo de "What Changes". Sobre la Open
> Question D7 (`design.md`): no se reabre el requisito de `entorno-de-ejecucion` sobre contenedores
> sin privilegios de root del `2c` — el camino documentado (script de arranque propio, README/humo/CI)
> queda como está escrito; se acepta el límite declarado de que un `docker compose up` manual, fuera
> del camino documentado, puede seguir creando la carpeta como root.

Además, L-048 y L-060 aplican: ningún sub-agente constructor arranca este change por su cuenta
mientras esta sección diga "pendiente".

## Qué queda fuera

- **La prueba de restauración con los datos del edificio piloto**: queda en el 15, como dice la ficha
  1e. Acá se prueba con datos inventados de dos administraciones.
- **Métricas y alertas de un respaldo fallido (OPS-3)** y cualquier monitoreo externo: queda en el 15.
  Este change deja la salud observable (`--salud`, `.ultimo-fallo`), no un canal de alerta.
- **Copia fuera del servidor y cifrado del `.dump`**: sigue con el despliegue, como decidió el 1d.
- **Backups de Redis**: el 1d ya los dejó afuera y no vuelven acá.
- **Restaurar directamente sobre la base en uso**: se mantiene prohibido. La conmutación apunta la
  aplicación a otra base; nunca restaura encima de la que está sirviendo.
- **`humo.sh` con `-p proptech` fijo (L-047)**: es deuda del C-23 `humo-y-ci`, no de este change.
  Acá sólo se cuida que la herramienta nueva lea `PROPTECH_COMPOSE_PROYECTO` como ya hace
  `restaurar.sh`.
- **V2-3, V3-4, V3-6 y V3-7** (deuda de roles y RLS del 2a): van al C-29 `base-y-rls`, que es
  CRITICAL.
- **Cambiar la matriz de permisos o cualquier `GRANT`**: subiría el change a CRITICAL y sale del
  scope.

## Knowledge Base Impact

| Archivo | Modo | Qué |
|---|---|---|
| `knowledge-base/12_fichas_de_changes.md` | **REWRITE** | La ficha §1e pasa de "pendiente" a cerrada con qué entró, qué no y su deuda; en "Deuda del cierre del 1d" se marcan cerradas las filas F4, F5, F6, F8 y "14 copias"; en "Deuda del cierre del 2a" la fila del volcado con el rol equivocado; y la fila del `mkdir` en la tabla del cierre que la tiene. Se borra el texto que decía que el dueño era el 15 |
| `CHANGES.md` | **REWRITE** | El estado de `[C-24] respaldos-2 · 1e` y su línea en el mapa de "DEUDA ADELANTADA" |
| `knowledge-base/09_decisiones_y_supuestos.md` | **APPEND** | La decisión sobre "14 copias" (cantidad más piso por antigüedad, con la alternativa descartada), la de la conmutación verificada y el resultado de F6 (arreglado o descartado con evidencia). Nunca se edita D-091 ni D-095 |
| `knowledge-base/15_lecciones.md` | **APPEND** | Lo que enseñe el change; como mínimo la lección de F4 (ordenar por nombre es ordenar por el reloj de otro) si el arreglo la confirma |
| `knowledge-base/02_descripcion_general.md` | **REWRITE** | La sección de despliegue e infraestructura nombra hoy `respaldar.sh` y `restaurar.sh`; suma `conmutar.sh` y la variable nueva |
| `knowledge-base/05_reglas_de_negocio.md` | none | Ninguna regla R01-R41 cambia: el change es infraestructura de recuperación |
| `knowledge-base/04_modelo_de_datos.md` | none | Sin migraciones ni entidades nuevas |

## Lecciones que aplican (`knowledge-base/15_lecciones.md`)

| Lección | Cómo la cubre este change |
|---|---|
| **L-001** · probar una dependencia que no responde, no sólo apagada | El test de SIGTERM (F5) corta un volcado **en curso** con la base lenta, no con la base caída; el del rol equivocado usa una base viva que rechaza al rol |
| **L-006** · un comando destructivo apunta a un nombre único del proyecto | `conmutar.sh` lee `PROPTECH_COMPOSE_PROYECTO` como `restaurar.sh` y valida el nombre de la base con la misma expresión cerrada; la retención nueva sigue filtrando por el patrón propio antes de borrar |
| **L-007** · el mensaje de error de una librería también es una salida | El `error_salir` en JSON de F8 no copia la salida de `pg_dump`; `conmutar.sh` nombra el paso que falló, no el texto de la herramienta |
| **L-008** · validar con coincidencia completa y sólo ASCII | `RESPALDO_CONSERVAR_DIAS` pasa por `validar_entero` y tiene su escenario con `0`, `060`, `+1`, vacío, con espacios y con dígitos de otro alfabeto |
| **L-013** · mutar para ver el rojo exige una copia previa y decirlo | Cada test de F4, F5, F8 y del rol equivocado se ve en rojo con el defecto presente (o con un mutante declarado y revertido), con comando, hora y salida pegados en `tasks.md` |
| **L-014** · `set -e` no actúa dentro de una función a la izquierda de `||` | El `trap` de F5 y la retención nueva se escriben con `if !` explícito: el modo continuo llama `ciclo_backup \|\| true` y nada ahí puede confiar en `set -e` |
| **L-016** · una observación tiene que poder dar otro resultado | F6 no se cierra con "no se reprodujo": o se arregla, o se descarta nombrando la ráfaga corrida, cuántas veces y su salida |
| **L-018** · un chequeo de arranque verifica el efecto, no la forma | Las tres verificaciones de `conmutar.sh` miran el efecto (la revisión que informa la base, `relrowsecurity`, las políticas presentes), no que el compose tenga una línea escrita |
| **L-019** · un test que no puede dar rojo es peor que no tenerlo | El test del rol equivocado con binario falso se **reemplaza** (no se duplica) por el que corre `pg_dump` real: el viejo no podía distinguir un compose correcto de un rol realmente rechazado |
| **L-033** · un test de infraestructura no supone una carpeta real vacía | Los tests nuevos no asumen `infra/datos-respaldos/` vacía: recuerdan si existía, usan nombres propios y no leen binarios como texto |
| **L-043** · un script que no está en el CI se ejecuta en su test o en el cierre | `conmutar.sh` se ejecuta de verdad: o en el humo, o en el cierre con comando y salida pegados; nunca sólo con un test estático de su texto |
| **L-047** · `humo.sh` fija su propio proyecto de Compose | `conmutar.sh` nace leyendo `PROPTECH_COMPOSE_PROYECTO`; quien lo corra sobre un stack real comprueba primero con qué `-p` va |
| **L-048** y **L-060** · la firma humana y las tareas que hay que frenar | La sección "Gobernanza" bloquea el apply mientras diga "pendiente", y la primera tarea de `tasks.md` es registrar la firma |
| **L-055** · "suite completa" puede ser una selección | La corrida de cierre es la suite entera sobre el SHA final, con `git rev-parse HEAD` al lado |
