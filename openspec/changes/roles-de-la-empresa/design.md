## Context

Ver `proposal.md` (Why) y la exploración `openspec/exploraciones/2026-10-20-roles-de-la-empresa-y-login.md`
(puntos 1 a 9, decididos por Juani el 20/10/2026; no se rediscuten acá). Estado del código al
20/10/2026 (commit `4507759`; verificado: es el último commit que tocó código de aplicación antes de
este proposal. El HEAD de hoy, `c7113d0` ("docs(openspec): propose de roles-de-la-empresa"), sólo agrega
los ocho archivos de `openspec/changes/roles-de-la-empresa/` y no cambia nada de `backend/` ni `web/`,
así que el estado del código en `c7113d0` es idéntico al de `4507759`; se mantiene esta última como la
cita porque es el commit que de verdad tocó código):

- **`acceso/dominio/permisos.py`**: enums `Rol` (`titular | colaborador | consejo | vecino`), `Nivel`
  (`ver | editar`) y `Accion` (16 miembros); `Asignacion(rol, complejo_id, unidad_id, nivel)`; la
  matriz `_MATRIZ: {Accion: frozenset[(Rol, Nivel | None)]}`; `puede` trata al titular como
  "cualquier complejo" y al resto sólo en su `complejo_id`; `alcanza` igual, más el vecino por unidad.
  `puede(..., complejo_id=None)` sólo evalúa `crear_edificio`.
- **`asignacion_rol`** (migración `0003`): `rol`, `complejo_id` nulo sólo para el titular, `unidad_id`
  sólo para el vecino, `nivel` sólo para el colaborador; tres `CHECK`
  (`ck_asignacion_rol_rol_valido`, `ck_asignacion_rol_nivel_valido`,
  `ck_asignacion_rol_forma_por_rol`); FK compuestas a persona, complejo y unidad; RLS forzada con la
  política de D5 del 2a; sin ningún índice único además de la PK.
- **Quién lee y escribe esas filas**: `acceso/aplicacion/autorizacion.py::cargar_asignaciones` (lee
  `rol, complejo_id, unidad_id, nivel`), `complejos/aplicacion/escritura.py::asignar_complejo_a_persona`
  (inserta `rol` y `nivel`) y `proptech_api/complejos.py::CuerpoAsignacion` (`rol: colaborador |
  consejo`, `nivel` obligatorio para el colaborador). Ningún camino de producción crea titulares ni
  vecinos: los crean los tests (21 archivos con el vocabulario viejo). La carga del ejemplo guardada sin
  commitear en `.git/informes-3b/2.3-wip/` **no inserta en `asignacion_rol`** (RD-7, revisión del DBA):
  su riesgo real es otro, que llama al caso de uso `crear_edificio` con una persona que todavía no tiene
  ninguna asignación de rol.
- **Vocabulario de auditoría**: `accion_de_auditoria` tiene las 16 acciones (0004 y 0010). El detalle
  de la asignación guarda sólo `complejo_id`: ninguna fila de auditoría guarda un rol.
- **Precedente de migración de datos con RLS forzada**: `0013_normalizar_textos_legados` hace
  `NO FORCE ROW LEVEL SECURITY` dentro de la transacción, con `ACCESS EXCLUSIVE`, y devuelve el `FORCE`
  antes del commit; un error revierte todo, incluido el `NO FORCE` (DDL transaccional de PostgreSQL).
- **Web**: dos textos nombran al "titular de la administración" (`componentes/Estados.tsx`, estado
  `sinPermiso`; `app/edificios/acciones.ts`, crear edificio). El cliente ya recibe `permiso_faltante`.

## Goals / Non-Goals

**Goals:**

- Que el dominio, la base y la API hablen de los siete perfiles con alcance, con la matriz escrita
  celda por celda, y que ninguna celda cambie sin que un test escrito a mano lo note.
- Que la conversión de las filas existentes sea completa en todas las administraciones y que su vuelta
  atrás nunca dé más permiso del que había.
- Dejar en cada asignación de vecino la distinción propietario o inquilino que van a leer los cambios
  6, 7 y 11.

**Non-Goals:**

- Ninguna política de base nueva: el alcance por edificio y por unidad sigue en la aplicación (E2 del
  2a, D6 de abajo).
- Ninguna acción nueva en `Accion` ni migración de vocabulario de auditoría.
- Ningún endpoint nuevo: ni para asignar alcance principal, ni para dar de alta vecinos.
- Nada del login (2b).

## Cómo aplica cada lección

La tabla del proposal dice qué tarea cubre cada lección. Lo que cambia el diseño:

- **L-016 y L-018**: la migración se prueba leyendo como `proptech_app` con el tenant de **cada**
  administración, nunca contando filas como el rol de arranque (que ve todo y haría pasar una migración
  que no migró). El `CHECK` se prueba insertando cada forma inválida, no leyendo `pg_constraint`.
- **L-019 y L-022**: la tabla de casos de la matriz se escribe a mano desde la tabla de D3 (no se
  genera desde `_MATRIZ`) y se compara entera: 16 acciones por 9 columnas, 144 celdas.
- **L-020**: el `NO FORCE` temporal es un arreglo con su propio riesgo; tiene su ataque dedicado (una
  migración que falla a mitad y deja la tabla como estaba, con `FORCE`).
- **L-023**: antes de cerrar la migración se busca con `rg` todo `INSERT` a `asignacion_rol` del
  repositorio entero, incluidos `infra/`, `.git/informes-3b/` y los otros changes en curso.
- **L-012**: R5 del 2a (el contrato de error del endpoint de asignación) entra acá porque este cambio
  reescribe ese cuerpo; el resto de la deuda del 2a con dueño el 2b se queda en el 2b.

## Fronteras

No cambian. `complejos` → `acceso` → `compartido`; `acceso` sigue sin importar `complejos` y
`compartido` sin importar `acceso` (el test de fronteras del 2a lo sigue exigiendo). El perfil y el
alcance viven en `acceso.dominio`; la API sigue componiendo los dos módulos.

**Frontera cruzada que ya existe (RA-4, revisión del arquitecto)**: `complejos/aplicacion/escritura.py:54`
escribe por SQL crudo directamente en `asignacion_rol`, que es tabla del módulo `acceso`, no de
`complejos`. No es una frontera nueva de este cambio (ya la cruzaba `asignar_complejo_a_persona` antes
de D1/D2); este cambio la hereda sin tocarla.

**Vocabulario de roles asignables repetido en tres lugares (RA-4)**: el `Literal` de
`CuerpoAsignacion.rol` en `proptech_api/complejos.py`, el `CHECK ck_asignacion_rol_rol_valido` de la
base y el enum `Rol` (perfil) de `acceso/dominio/permisos.py` tienen que decir, cada uno por su lado, el
mismo conjunto de roles asignables por esta ruta. Nada los ata hoy: se pueden desincronizar sin que
ningún test lo note. Se agrega una tarea con un test de consistencia que falla si los tres dejan de
coincidir (tarea 4.4 de `tasks.md`).

**Decisión (RA-4)**: se mantiene la escritura directa de `complejos/escritura.py` a `asignacion_rol`;
no se migra a un caso de uso único `acceso.asignar`. **Alternativa descartada**: centralizar la
escritura en `acceso.asignar` significaría mover `asignar_complejo_a_persona` entero (el `INSERT`, el
`SAVEPOINT`/transacción compartida con la auditoría de D9, y el `@accion_sensible`) a un módulo que hoy
no existe, tocando el único punto de escritura de roles y su test de extremo a extremo, para mover una
frontera que ninguna historia de este cambio necesita mover. Se decide no pagar ese costo ahora,
documentando el motivo acá en vez de volver a decidirlo en silencio la próxima vez que se toque este
archivo.

## Decisions

### D1 · Perfil y alcance en `asignacion_rol` (E1)

- `rol` toma seis valores de base: `super_admin`, `administrador`, `contador`, `auxiliar`, `consejo`,
  `vecino`. Se mantiene el nombre de la columna (renombrarla obligaría a tocar cada consulta sin ganar
  nada).
- **El alcance se deduce**, no se guarda: `complejo_id IS NULL` es principal; `complejo_id` con
  `unidad_id IS NULL` es por edificio; con `unidad_id` es por unidad. Es lo que ya hacía el titular, y
  es lo que la exploración pide ("alcance principal = hoy `complejo_id IS NULL`").
- Se borra `nivel`: "ver" y "editar" pasan a ser perfiles distintos (auxiliar y administrador).
- Nuevo `CHECK ck_asignacion_rol_forma_por_rol` (mismo nombre, otra forma):
  - `super_admin`: sin complejo, sin unidad, sin vínculo;
  - `administrador`, `contador`: sin unidad, sin vínculo, con o sin complejo;
  - `auxiliar`, `consejo`: con complejo, sin unidad, sin vínculo;
  - `vecino`: con complejo, con unidad, con vínculo.
- `ck_asignacion_rol_rol_valido` con los seis valores; `ck_asignacion_rol_nivel_valido` se borra con la
  columna; `ck_asignacion_rol_vinculo_valido` (`vinculo IS NULL OR vinculo IN ('propietario',
  'inquilino')`).
- El guardián del catálogo no cambia: `asignacion_rol` sigue siendo la única excepción a `complejo_id
  NOT NULL`, ahora también por el administrador y el contador principales (se actualiza el comentario).

**Descartado**: una columna `alcance` explícita (`principal | edificio | unidad`). Repite lo que ya dicen
`complejo_id` y `unidad_id`, y obliga a un `CHECK` más que ate las tres columnas; una fila con
`alcance = 'edificio'` y `complejo_id` nulo sería exactamente el agujero que se quiere cerrar.

**Costo de revertir (RA-7, E1)**: es el `downgrade` de D5 completo (sólo corre sin datos nuevos: ningún
contador, ningún administrador principal, ningún inquilino) más deshacer, a mano, cada punto que ya lee
el alcance deducido en vez de `rol` y `nivel` (`cargar_asignaciones`, `permisos.py`, el cuerpo del
endpoint de D7). Con datos nuevos ya cargados, no hay vuelta sin restaurar un respaldo (Migration Plan).

### D2 · Propietario o inquilino: `vinculo` en la fila del vecino (E2)

- Columna `vinculo text` nula, obligatoria en el vecino y prohibida en el resto (D1). La fila del vecino
  **es** la relación persona y unidad: el atributo vive ahí, como pide el punto 5, y no en `persona`.
- Índice único parcial `uq_asignacion_rol_persona_unidad` sobre `(administracion_id, persona_id,
  unidad_id) WHERE rol = 'vecino'`: una persona tiene una sola relación con cada unidad (no puede ser
  propietaria e inquilina de la misma). Varios propietarios de una unidad son varias personas, cada una
  con su fila (punto 6): el índice no lo impide.
- En el dominio, el perfil es uno de siete: `SUPER_ADMIN`, `ADMINISTRADOR`, `CONTADOR`, `AUXILIAR`,
  `CONSEJO`, `VECINO_PROPIETARIO`, `VECINO_INQUILINO`. Se arma de `(rol, vinculo)` al leer la fila; la
  matriz y `alcanza` trabajan con el perfil, nunca con el texto de la base.

**Descartado**: dos valores de rol (`vecino_propietario`, `vecino_inquilino`). Es más corto para la
matriz, pero pone la diferencia en el perfil de la persona en vez de en su relación con la unidad (punto
5), y obliga a cada consulta que pregunte "¿es vecino de esta unidad?" a nombrar dos roles.

**Costo de revertir (RA-7, E2)**: borrar la columna `vinculo` y el índice `uq_asignacion_rol_persona_unidad`,
y volver a un solo perfil `VECINO` en el dominio. Es gratis mientras nada lea la distinción; en cuanto
los cambios 6 y 7 empiecen a leer `vinculo` para separar ordinarias de extraordinarias, revertir pierde
ese dato en cada fila existente, y no hay vuelta sin restaurar un respaldo (como el resto de este
cambio).

### D3 · La matriz nueva (D-106 propuesta)

`_MATRIZ: dict[Accion, frozenset[tuple[Perfil, Alcance]]]`, escrita a mano. Columnas como en la spec:
SA super admin (principal); AP y AE administrador principal y por edificio; CP y CE contador principal y
por edificio; AX auxiliar; CO consejo; VP y VI vecino propietario e inquilino (por unidad).

| Acción | SA | AP | AE | CP | CE | AX | CO | VP | VI | De dónde sale |
|---|---|---|---|---|---|---|---|---|---|---|
| `cargar_gastos_y_preparar_liquidacion` | Sí | Sí | Sí | | | | | | | punto 3 (operar: gastos) |
| `emitir_y_distribuir_liquidacion` | Sí | Sí | Sí | | | | | | | punto 4 (emite todo administrador) |
| `anular_liquidacion` | Sí | Sí | | | | | | | | punto 4 |
| `confirmar_pago_informado` | Sí | Sí | Sí | | | | | | | punto 3 (confirmar pagos) |
| `revertir_o_reimputar_pago` | Sí | Sí | | | | | | | | punto 4 |
| `condonar_intereses` | Sí | Sí | | | | | | | | punto 4 |
| `dar_de_baja_deuda` | Sí | Sí | | | | | | | | punto 4 |
| `aceptar_alertas_no_bloqueantes` | Sí | Sí | Sí | | | | | | | punto 3 (operar); como en D-096 |
| `aceptar_alertas_bloqueantes` | Sí | Sí | | | | | | | | punto 4 |
| `invitar_usuarios_y_asignar_edificios` | Sí | | | | | | | | | punto 3 (usuarios y roles), E5 |
| `informar_pago` | | | | | | | | Sí | Sí | puntos 3 y 6 |
| `crear_edificio` | Sí | | | | | | | | | punto 3 (edificios), E5 |
| `crear_version_de_configuracion` | Sí | Sí | Sí | | | | | | | punto 3 (configuración), E3 |
| `confirmar_sin_saldos_previos` | Sí | Sí | | | | | | | | analogía con dar de baja, E4 |
| `configurar_padron` | Sí | Sí | Sí | | | | | | | punto 3 (padrón) |
| `ver_configuracion_del_edificio` | Sí | Sí | Sí | Sí | Sí | Sí | Sí | | | punto 3 (lectura), E6 |

(En blanco es "No".)

- `puede(asignaciones, accion, complejo_id)`: una asignación principal cuenta en cualquier complejo de
  la administración; una por edificio, sólo si su `complejo_id` coincide; una por unidad, sólo si el
  complejo de su unidad coincide. Con `complejo_id=None` (crear un edificio) sólo cuentan las
  principales. La clave que se busca en la matriz es `(perfil, alcance)`. **Se conserva la guarda que ya
  existe en `permisos.py:109`** (RA-3, revisión del arquitecto): con `complejo_id=None` sólo se evalúa
  el permiso `crear_edificio`, nunca otra acción, aunque la asignación sea de alcance principal.
- `alcanza(asignaciones, complejo_id, unidad_id=None)`: principal, todo; por edificio, ese complejo y sus
  unidades; por unidad, su unidad y su complejo (sin unidad pedida). Igual que hoy, con "principal" en
  lugar de "titular".
- `Accion` no cambia: los 16 nombres siguen siendo el vocabulario de la matriz y de la auditoría, y
  `accion_de_auditoria` no necesita migración. Las filas de auditoría anteriores siguen diciendo quién
  y qué, nunca con qué rol: no hay nada que reescribir (y la tabla no se puede reescribir, D9 del 2a).

**Descartado**: una matriz por rol con el alcance como condición aparte (`if alcance is PRINCIPAL`
dentro de `puede`). La regla del punto 4 es justamente una celda por alcance; escrita como condición, la
tabla de casos dejaría de ser una tabla.

### D4 · Las celdas que la exploración no fijó (E3 a E6)

- **E3, crear una versión de configuración: super admin y todo administrador**. El punto 3 pone
  "configuración" entre lo que opera el administrador, y el punto 4 no la incluye entre lo que se reserva
  al principal, lo que **contradecía** la spec vigente de `configuracion-versionada` y la decisión del
  3a (sólo el titular, porque la tasa mueve plata). **Contradicción resuelta por decisión de Juani del
  20/10/2026**: queda la exploración, que es posterior al 3a. **Versión vigente desde esa fecha**: crea
  una versión de configuración el super admin y todo administrador con alcance sobre el edificio
  (principal o por ese edificio), no sólo el principal. Alternativa descartada: sólo super admin y
  administrador principal (lo más parecido al 3a que el punto 3 permite).
- **E4, confirmar "sin saldos previos": super admin y administrador principal**. No figura en la
  exploración. Declara que el edificio arranca sin deuda anterior: tiene el peso de dar de baja una
  deuda (punto 4). **Decidido por Juani el 20/10/2026**: sólo el super admin y el administrador
  principal, nunca cualquier administrador. Alternativas descartadas: sólo el super admin (como hoy el
  titular) o todo administrador.
- **E5, crear un edificio e invitar o asignar: sólo el super admin**. Punto 3: "todo, incluidos
  edificios, usuarios y roles" es lo que distingue al super admin. Alternativa: también el administrador
  principal. **Costo de revertir (RA-7)**: es cambiar una celda de la matriz (sumar AP a
  `crear_edificio` e `invitar_usuarios_y_asignar_edificios`) y dos escenarios de spec; no toca la base
  ni la migración.
- **E6, la lectura de la configuración: contador, auxiliar y consejo**. Es la única acción de lectura que
  existe; el padrón y los coeficientes son la base de lo contable (contador), el auxiliar lee "el
  edificio" y el consejo ya la leía desde el 3a. Las lecturas de gastos, liquidaciones y comprobantes
  nacen con los cambios 6, 7 y 12, con estos mismos perfiles. **Alternativa descartada (RA-7)**: que
  sólo leyera el consejo, como en el 3a, dejando afuera a contador y auxiliar hasta que tuvieran su
  propia pantalla; se descarta porque el contador necesita el padrón y los coeficientes desde ahora (son
  la base de la liquidación del cambio 6) y el auxiliar, que ya opera el edificio, quedaría sin ver lo
  mismo que ve el administrador sin que ninguna regla de negocio lo pida.

### D5 · La migración `0017_roles_de_la_empresa` (E7)

Corre como `proptech_migrador`, en una sola transacción, con el patrón de `0013`:

1. `LOCK TABLE asignacion_rol IN ACCESS EXCLUSIVE MODE` y `ALTER TABLE asignacion_rol NO FORCE ROW
   LEVEL SECURITY`: el migrador es dueño y, sin `FORCE`, la política no lo filtra; con `FORCE`, un
   `UPDATE` sin tenant toca cero filas y termina bien, en silencio.
2. Chequeo previo: si hay dos filas de vecino de la misma persona y unidad, `RAISE EXCEPTION` con la
   cantidad, sin ids ni nombres.
3. Borrar los tres `CHECK`, sumar `vinculo`, convertir: `titular` → `super_admin`; `colaborador` con
   `editar` → `administrador`; `colaborador` con `ver` → `auxiliar`; `vecino` → `vinculo =
   'propietario'`; borrar `nivel`; crear los `CHECK` nuevos y tres objetos nuevos:
   - `uq_asignacion_rol_persona_unidad` (D2): índice único parcial sobre `(administracion_id,
     persona_id, unidad_id) WHERE rol = 'vecino'`.
   - `uq_asignacion_rol_persona_alcance` (RA-5, decidido por Juani el 20/10/2026): una persona no
     puede tener dos asignaciones de rol de personal (`super_admin`, `administrador`, `contador`,
     `auxiliar`) en el mismo alcance, y el alcance "principal" (`complejo_id IS NULL`) queda protegido
     igual que el resto, no exento. Se crea como
     `CREATE UNIQUE INDEX uq_asignacion_rol_persona_alcance ON asignacion_rol (administracion_id,
     persona_id, complejo_id) NULLS NOT DISTINCT WHERE rol IN ('super_admin', 'administrador',
     'contador', 'auxiliar')`. `NULLS NOT DISTINCT` (soportado desde PostgreSQL 15; la imagen de este
     proyecto es `postgres:18.6-trixie`) hace que dos filas con `complejo_id` nulo del mismo alcance
     principal cuenten como el mismo valor para el único — que es justo el caso que, con un `UNIQUE`
     corriente, quedaba exento, porque ese tipo de índice trata cada `NULL` como distinto de cualquier
     otro. El índice no restringe `consejo` ni `vecino`: el consejo y el vínculo con una unidad son
     asignaciones de otro tipo y coexisten con un rol de personal de la misma persona (RA-5).
   - `ix_asignacion_rol_persona` (RD-1, revisión del DBA): índice no único `(administracion_id,
     persona_id)`, para la consulta de `cargar_asignaciones`
     (`acceso/aplicacion/autorizacion.py:31`), que lee todas las asignaciones de una persona dentro de
     su administración en cada pedido.
4. `ALTER TABLE asignacion_rol FORCE ROW LEVEL SECURITY` antes del commit. Si algo falla, PostgreSQL
   revierte todo, incluido el `NO FORCE`.

**El vecino de hoy pasa a propietario** (E7): es la forma que conserva lo que ya veía; hoy no hay datos
reales, así que no se le quita nada a nadie que exista.

**`downgrade`**, en el mismo patrón y en este orden explícito (RD-3, revisión del DBA):

1. `LOCK TABLE asignacion_rol IN ACCESS EXCLUSIVE MODE`.
2. `ALTER TABLE asignacion_rol NO FORCE ROW LEVEL SECURITY` (relaja la validación, igual que en el
   `upgrade`, antes de tocar ninguna fila).
3. Chequeo previo: si hay alguna fila sin forma en 0016, `RAISE EXCEPTION` **antes de tocar nada**, con
   la cantidad por tipo y sin ids ni nombres: `contador` (cualquier alcance), `administrador` con
   `complejo_id` nulo, `vecino` con `vinculo = 'inquilino'`.
4. Si no, la vuelta exacta: `super_admin` → `titular`; `administrador` → `colaborador` con `editar`;
   `auxiliar` → `colaborador` con `ver`; `vecino` sin vínculo; `nivel` vuelve. Se borran, en este orden
   (RD-4, revisión del DBA): el índice `uq_asignacion_rol_persona_unidad` (`DROP INDEX`), el índice
   `uq_asignacion_rol_persona_alcance` (RA-5) y el índice `ix_asignacion_rol_persona` (RD-1), y por
   último la columna `vinculo`; se recrean los tres `CHECK` de 0003 y se borra el `CHECK` nuevo. **No
   hay índice de 0003 ni de 0016 que restaurar**: `asignacion_rol` no tenía ningún índice más allá de la
   PK antes de esta migración, y `0016` no toca esta tabla (si algún texto anterior dice que el
   `downgrade` borra "índices de 0003 y 0016", es un error: esos índices no existen). El catálogo de
   antes y después queda comparado entero (tarea 3.3), **sin contar `ordinal_position` ni `dtd_identifier`** en las
   columnas (RD-4: cambian con el orden de creación y no son señal real de drift;
   resuelto por el orquestador, 20/10/2026: PostgreSQL usa el número de atributo
   también como `dtd_identifier`, verificado como 7 → 9 al recrear `nivel`).
5. `ALTER TABLE asignacion_rol FORCE ROW LEVEL SECURITY` antes del commit.

El inquilino falla aunque "vecino" exista en 0016: devolverlo como vecino borraría la restricción que
el punto 7 le pone, y el día que existan las extraordinarias el código viejo no sabría que no puede
verlas. Una vuelta atrás que da más permiso del que había no es una vuelta atrás. **Descartado**: un
`downgrade` con pérdida (inquilino → vecino, contador → colaborador "ver", administrador principal →
titular): la última convertiría a quien opera en quien asigna edificios.

### D6 · Las políticas de RLS no cambian

La exploración pedía "políticas RLS revisadas". Revisadas, no cambian: la política de `asignacion_rol`
y de toda tabla sigue siendo la de la administración (D5 del 2a), y el perfil y el alcance se evalúan en
la aplicación sobre filas ya filtradas por la base (E2 del 2a). Este cambio no mueve esa frontera: un
super admin de A sigue sin ver nada de B porque la base no se lo muestra, no porque `alcanza` lo niegue.
El riesgo de E2 del 2a (un vecino viendo a otro, un consejo viendo otro edificio) sigue igual y se suma
uno: un administrador por edificio viendo otro edificio. Se cubre con los mismos tests por perfil y por
endpoint (tarea 4.3).

### D7 · El endpoint de asignación

- `CuerpoAsignacion.rol: Literal["administrador", "contador", "auxiliar", "consejo"]`; `nivel` deja de
  existir. Como el cuerpo prohíbe campos extra, `nivel`, `vinculo` y `unidad_id` dan 422 nombrando el
  campo (D-104), nunca 500. `super_admin` y `vecino` no son asignables por esta ruta (el complejo sale
  del path y nunca hay unidad): 422, como hoy `titular` y `vecino` (R3A-4).
- Sólo el super admin lo pasa (`invitar_usuarios_y_asignar_edificios`, E5). Orden de siempre: complejo
  → alcance (404) → permiso (403) → persona destino (404).
- `asignar_complejo_a_persona` deja de recibir `nivel`. La auditoría suma al `detalle` el `rol`
  asignado y el alcance (RA-2, revisión del arquitecto): sigue guardando `complejo_id`, y agrega esos
  dos campos sólo en las filas que se escriban de acá en adelante. No es una migración de vocabulario:
  las filas de auditoría anteriores no se tocan (no se pueden reescribir, D9 del 2a).
- **R5 del 2a** (el contrato de error de `unidad_id` en este cuerpo): se verifica con el cuerpo nuevo en
  la tarea 4.2; si queda cubierto, la fila de deuda se cierra al archivar.

### D8 · La web (E8)

Los dos textos pasan a "Esto lo puede hacer el super admin de la empresa." El super admin puede todo,
así que la frase es cierta para cualquier 403 de las pantallas del 3b, sin mapear permiso por permiso.
"Empresa" y "super admin" son las palabras de Alberto y de la exploración; el resto de la web dice
"administración" para el tenant, y eso no cambia. Se actualizan `Estados.test.tsx` (hoy busca
`/titular/`) y el test de la acción de crear edificio, viéndolos fallar primero.

**Decidido por Juani el 20/10/2026**: el rol se muestra, en la interfaz, como "Super admin" (de la
empresa); es el texto que ve el usuario. Cierra la pregunta abierta sobre "super admin de la empresa" o
"superadministrador de la administración": queda la primera.

## Risks / Trade-offs

- [La migración corre sin `FORCE` unos milisegundos] → dentro de una transacción con `ACCESS EXCLUSIVE`:
  nadie más lee ni escribe la tabla mientras tanto; un error revierte el `NO FORCE`; el guardián y un
  test leen `relforcerowsecurity` y prueban el aislamiento como la app después.
- [Alcance por edificio en la aplicación, ahora con más perfiles] → la tabla de casos de `alcanza` por
  perfil y los tests por endpoint de la 4.3; blanco del rompedor.
- [E3 permite que un administrador por edificio cambie la tasa de interés] → queda auditado con autor
  (`configuracion-versionada`); decidido por Juani el 20/10/2026, no rechazado.
- [`downgrade` que falla con datos nuevos] → es el comportamiento buscado; con datos nuevos, volver
  atrás es restaurar un respaldo (como dice el Migration Plan del 2a desde el cambio 3).
- [La carga del ejemplo sin commitear (`.git/informes-3b/2.3-wip/`) llama a `crear_edificio` con una
  persona que todavía no tiene ninguna asignación de rol (RD-7: no inserta en `asignacion_rol`)] → la
  tarea 3.4 la busca (L-023) y deja escrito qué cambiar; no la toca, porque no está en el árbol ni es de
  este cambio.
- [Specs y decisiones anteriores siguen diciendo "titular"] → los escenarios que este cambio modifica
  dicen "(antes, titular)"; el glosario lo aclara al archivar. Los demás escenarios con "titular" son
  equivalentes a "super admin".

## Migration Plan

1. Con la aprobación firmada, construir por tareas. En una máquina con la base del 3b, `docker compose
   up --build` corre `roles antes`, `alembic upgrade head` (0017) y `roles despues`, como siempre.
2. **Rollback**: `alembic downgrade 0016` funciona mientras no haya contadores, administradores
   principales ni inquilinos; si los hay, falla sin tocar nada y el camino es restaurar un respaldo.
   Volver la imagen anterior sin bajar la migración no sirve: el código viejo lee `nivel`, que ya no
   existe, y falla ruidoso (no abre nada).

**Supuesto declarado (RD-2, revisión del DBA)**: no hay producción ni datos reales de este sistema —
nunca se desplegó (arriba, "Despliegue: no hay"). Como no hay un respaldo real contra el que probar la
migración, la prueba de `upgrade`/`downgrade`/`upgrade` de la tarea 3.5 (`tasks.md`) usa la copia más
fiel disponible: el stack de humo (`infra/ci/humo.sh`) con sus dos administraciones sembradas, volcado
con `compose exec -T respaldos /usr/local/bin/respaldar.sh --una-vez` y restaurado en una base aparte
con `bash infra/respaldos/restaurar.sh <archivo_dump> proptech_restauracion` (el mismo camino que usa
`humo.sh`). Sobre esa base restaurada corre `upgrade` a 0017, `downgrade` a 0016 y `upgrade` otra vez,
comparando conteos por `administracion_id` y por `rol` antes y después de cada paso.

## Open Questions

Ninguna cambia las specs ni las tareas; se responden al firmar o antes del cambio que las necesita.

- **El orden con `acceso-de-desarrollo`** (en curso, sin firmar): su punto de entrada usa "la identidad
  del titular de la administración de ejemplo"; la carga del ejemplo no inserta ese titular en
  `asignacion_rol` (RD-7), llama a `crear_edificio` con una persona que todavía no tiene ninguna
  asignación de rol, y esa asignación falta en el 3b. Si `acceso-de-desarrollo` se construye antes que
  este cambio, su tarea de carga tiene que SUMAR una fila `super_admin` para esa persona (no reemplazar
  lo que ya tenga) con el vocabulario nuevo después; si después, directamente con el vocabulario nuevo
  (RA-1, revisión del arquitecto; detalle en `tasks.md`, tarea 3.4, que ese change hereda y tiene que
  retomar). La exploración dice además que con el login ese change se reduce a la carga del ejemplo.
- **Quién gestiona usuarios y alcances principales — resuelto (RA-6, Juani, 20/10/2026)**: va en el
  change **2b**, junto con el login: el super admin invita al personal y le asigna perfil y alcance;
  los vecinos se dan de alta desde el padrón con su vínculo y reciben la invitación por mail (detalle
  en `proposal.md`, "Fuera del cambio"). Hoy sólo existe la asignación por edificio.
- **Las palabras de la pantalla — resuelto (E8, Juani, 20/10/2026)**: "Super admin" (de la empresa).
- **El consejo y la condonación**: D-096 decía que el consejo "ve" las condonaciones; P20 (si por encima
  de un monto hace falta el consejo) sigue abierta y no la toca este cambio.
