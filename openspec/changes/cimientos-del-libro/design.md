## Context

Motivación y alcance en `proposal.md`. Lo que sigue es el estado del código que condiciona el cómo
(HEAD `de3c710`, 26/10/2026):

- `compartido/roles.py` reasigna al migrador todo lo que el rol de arranque crea, salvo
  `_TABLA_EXCLUIDA_DE_LA_REASIGNACION = "auditoria"` (un texto, no un conjunto). `despues()` sólo
  transfiere y verifica `auditoria`; para `_TABLAS_DE_SOLO_AGREGAR` (hoy sólo
  `configuracion_versionada`) sólo ajusta `GRANT`. Su verificación de `auditoria` ya prueba el bloqueo
  por el efecto (inserta una fila en un `SAVEPOINT`, intenta `UPDATE`, `DELETE` y `TRUNCATE`, exige el
  SQLSTATE y el texto del trigger, revierte).
- `tests/integracion/test_dueno_de_tablas_solo_agregar.py` controla `auditoria` (verde) y
  `configuracion_versionada` (`xfail(strict=True)`, esperando esta decisión). Su sonda es
  `NO FORCE ROW LEVEL SECURITY` (L-036).
- `compartido/base_de_datos.py:verificar_rol_de_aplicacion_seguro` ya frena el arranque de la API y el
  worker si su rol es superusuario, tiene `BYPASSRLS` o es dueño de alguna tabla.
- `tests/unitarios/test_fronteras_de_modulos.py` recorre imports con `ast` y sólo prueba que
  `compartido` no importa módulos de dominio y que `acceso` no importa `complejos`, con mutantes en
  copias temporales.
- `compartido/dinero.py` no tiene aritmética, por diseño del 1b ("el reparto y las sumas son del
  cambio 4"); la spec `representacion-de-montos` lo prohíbe "en este cambio".
- `configuracion_versionada` (migración `0009`) bloquea `UPDATE`, `DELETE` y `TRUNCATE` con triggers
  para todo rol. `ALTER TABLE ... ADD COLUMN` no dispara triggers de fila.
- Los cinco casos de uso del padrón (`editar_unidad`, `editar_grupo`, `fijar_unidades`,
  `editar_categoria`, `reordenar_categorias`) no reciben `Identidad` ni `request_id`.
- `complejos/aplicacion/ejemplo.py:39` importa `acceso.dominio.eventos` (llegó el 24/10, después del
  explore).

## Goals / Non-Goals

**Goals:**

- Que los cinco controles (fronteras, dueño, reparto, umbral, auditoría del padrón) existan y den rojo
  ante su violación **antes** de que el 4b cree la primera tabla de plata.
- Que la columna nueva de `configuracion_versionada` entre en el mismo deploy en que la tabla pasa al
  rol de arranque, y antes de ese paso.

**Non-Goals:**

- Nada del libro (4b), de intereses ni del moroso crítico (4c), ni del cambio de titular (4d).
- No construir el préstamo de propiedad para migraciones futuras (D3).
- No tocar pantallas.

## Decisions

### D1 · El rol de arranque es dueño de toda tabla de sólo agregar (DBA-1, opción a)

`_TABLA_EXCLUIDA_DE_LA_REASIGNACION` pasa a ser un conjunto: `{"auditoria"} | _TABLAS_DE_SOLO_AGREGAR`.
`antes()` no reasigna ninguna de esas tablas al migrador. `despues()`, para cada tabla del conjunto que
exista: `ALTER TABLE ... OWNER TO` el rol de arranque, lo mismo con las funciones de sus triggers
(con `SET search_path = ''`), `REVOKE UPDATE, DELETE, TRUNCATE` y `GRANT SELECT, INSERT` a la app, y
recién después la verificación de D2. Todo en la misma transacción que hoy.

El 4b suma sus seis tablas a `_TABLAS_DE_SOLO_AGREGAR` y quedan cubiertas sin cambiar `roles.py` ni el
test de dueño.

- **Descartadas**: (b) el migrador dueño, escrito como decisión: un archivo de migración podría
  `NO FORCE` y reescribir el libro; (c) un rol de propiedad aparte: con membresía equivale a (b), sin
  ella equivale a (a) con un rol más que mantener.
- **Costo de revertir**: `roles.py` y el chequeo de D3, un deploy; sin migración de datos.
- **Salvedad** (EVIDENCIA del explore, `infra/compose.yaml:83-85`): el servicio de migraciones ya
  tiene la credencial del rol de arranque. Esto protege contra una migración o la credencial del
  migrador, no contra quien controla ese contenedor.

### D2 · La protección se verifica por el efecto, tabla por tabla (L-018)

`_verificar_auditoria_protegida` se generaliza a `_verificar_tabla_protegida(cur, tabla, arranque)` y
corre para cada tabla del conjunto. Comprueba: `relrowsecurity` y `relforcerowsecurity`; los triggers
de bloqueo esperados de esa tabla, presentes y con `tgenabled = 'O'`; las funciones de sus triggers con
dueño el rol de arranque; y el bloqueo de verdad:

- **`UPDATE` y `DELETE`** sobre una fila real dentro de un `SAVEPOINT`, exigiendo el SQLSTATE `P0001`
  y el texto del `RAISE` de **esa** tabla (cada tabla declara su texto esperado; nunca "cualquier
  error"). La fila sale de la propia tabla si tiene alguna; si está vacía, la verificación inserta
  dentro del `SAVEPOINT` las filas padre mínimas (administración, complejo, persona) y una fila de
  prueba, todo revertido al final. Si no logra armar la fila, **falla diciéndolo**: nunca pasa en
  silencio.
- **`TRUNCATE`**: ejecutado, igual que hoy en `auditoria`, en toda tabla **sin FK entrante**. En una
  tabla con FK entrante (las del 4b), PostgreSQL contesta `0A000` antes que el trigger, así que ahí se
  verifica por catálogo: un trigger `BEFORE TRUNCATE` habilitado cuya función es la misma que bloquea
  `UPDATE` y `DELETE` (que sí se probó por el efecto). Esta es la única verificación por forma y queda
  escrita como tal en el docstring y en el informe del constructor.

La política de RLS de `auditoria` se sigue comparando entera (V3-1); para las demás tablas, la
política la vigila `test_catalogo_rls.py` como hoy (deuda del 15, decisión de Juani en el 2a).

- **Descartada**: copiar la sonda de `auditoria` tal cual a todas las tablas (frena cada deploy del 4b
  por el `0A000`), o aflojarla a "cualquier error" (queda ciega, V3-2).
- **Costo de revertir**: una función; sin datos.

### D3 · Los procesos no arrancan si una tabla protegida tiene otro dueño; el préstamo queda escrito

Nueva `verificar_tablas_de_solo_agregar(engine)` en `base_de_datos.py`, llamada junto a
`verificar_rol_de_aplicacion_seguro` en la API, el worker y los dos comandos que ya la llaman
(`alta_inicial`, `ejemplo`). Compara el **conjunto entero** (L-022) de `auditoria` más
`_TABLAS_DE_SOLO_AGREGAR` contra `pg_tables` y `pg_roles`: cada una tiene que existir y su dueño tiene
que ser superusuario. Nombra cada tabla con problema; nunca un valor (L-007). `proptech_app` puede leer
esos catálogos sin permiso nuevo.

"Superusuario" y no "el rol de arranque por nombre": la app no conoce ese nombre (su configuración es
`ConfiguracionDeAppSoloPostgres`) y el migrador nunca lo es (`roles.py` lo exige).

**Migraciones futuras sobre una tabla protegida** (no se construye ahora): la migración declara qué
tablas protegidas toca; `antes()` le presta la propiedad al migrador sólo de ésas y sólo si esa
migración está pendiente; `despues()` la devuelve y verifica con D2. Se agrega a `09` al archivar.
Mientras tanto, un `ALTER` falla con `must be owner` (escenario de la spec), que es el comportamiento
seguro.

- **Descartado**: préstamo general en cada `antes()` (anula la protección justo mientras corre código
  de migración); comparar contra el nombre del rol de arranque (obliga a dárselo a la app).
- **Costo de revertir**: una función y cuatro llamadas.

### D4 · Tres reglas de fronteras, por lista permitida (ARQ-2)

En `test_fronteras_de_modulos.py`, sobre el mismo recorrido con `ast`:

- **(a) Sin ciclos**: grafo módulo → módulo (sin contar `compartido`) armado con todas las capas;
  detección de ciclos con el nombre del ciclo en el mensaje.
- **(b) Entre módulos sólo `aplicacion`**: todo import de `proptech_core.<otro>` tiene que ser
  `proptech_core.<otro>.aplicacion[...]` o uno de los destinos exceptuados, cada uno con su motivo en un
  diccionario del test: `acceso.dominio.identidad` y `acceso.dominio.permisos` (`Identidad` y `Accion`
  viajan en todo caso de uso auditado); `acceso.dominio.eventos` (el vocabulario de auditoría viaja con
  `registrar()`; **nueva**, ver `ejemplo.py:39`). Fuera de la regla: `proptech_api` y
  `proptech_worker` (raíz de composición).
- **(c) Lista permitida para `dominio/`**: de `compartido` sólo `dinero`, `coeficientes`,
  `porcentaje`, `superficie`, `texto`, `tipos_de_unidad` y `reparto`; `parametros` como excepción con
  motivo (`complejos/dominio/configuracion.py:11`, para `desde_parametros`).
- **(d) `cuenta_corriente`** no importa `compartido.cola` (4.6: sus casos de uso nunca encolan) ni
  `liquidacion` (4.2: la dependencia va de `liquidacion` a `cuenta_corriente`).

Cada regla con un mutante en copia temporal (patrón que ya tiene el archivo) que da rojo en **su**
aserción. Se crea `proptech_core/cuenta_corriente/` con `__init__.py`, `dominio/__init__.py` y
`aplicacion/__init__.py`, vacíos.

- **Descartadas**: lista de prohibidos (falla abierta ante un submódulo nuevo); relajar (b) a "no
  importar `adaptadores`"; mover `Identidad`, `Accion` y los eventos a `compartido` (los saca del
  dominio que los define).
- **Costo de revertir**: un archivo de test.

### D5 · Aritmética de `Dinero`: suma, resta y negación, nada más

`__add__`, `__sub__` y `__neg__` entre `Dinero`, y `sumar(montos: Iterable[Dinero]) -> Dinero` (cero
para la lista vacía). Todo otro operando devuelve `NotImplemented` (Python levanta `TypeError`). El
resultado pasa por `Dinero.desde_decimal`, que ya rechaza lo que no entra en `NUMERIC(14,2)`. Sin
`__mul__`, `__truediv__` ni `__radd__` con números: el reparto y el redondeo trabajan fuera del tipo.
El docstring del módulo deja de decir "sin aritmética".

- **Descartada**: aritmética completa con `Decimal` (abre la puerta a multiplicar por un `float`
  convertido); que el reparto use `Decimal` suelto sin tipo (pierde el control de rango al devolver).
- **Costo de revertir**: tres métodos; nada persiste.

### D6 · Desempate del mayor resto: orden natural del identificador, después el id

`compartido/reparto.py` expone `ParteARepartir(clave, peso: Decimal, orden: tuple)` y
`clave_de_orden_natural(identificador: str, id: UUID) -> tuple`. El orden natural parte el
identificador en tramos de dígitos (comparados como entero) y de texto (comparados con `casefold`); a
igual tramo, el texto original y por último el UUID. "1" < "2" < "10"; "2B" < "10A". El reparto no sabe
qué es una unidad: recibe la clave de orden ya armada.

- **Descartadas**: orden de texto plano (R07 dice "identificador": "10A" quedaría antes que "2B"); el
  "menor número de unidad" de D-109 como número puro (los identificadores son texto libre, 3b); el UUID
  solo (determinista pero arbitrario para el administrador).
- **Provisoria**: A-1 (Alberto) puede cambiarla; cambiar la función y sus tests no toca datos (el
  reparto todavía no se persiste en el 4a).

### D7 · El reparto trabaja en centavos enteros; el redondeo suelto es otra función

`repartir(total: Dinero, partes: Sequence[ParteARepartir]) -> dict[clave, Dinero]`:

1. Valida (error propio `RepartoInvalido`): total `Dinero`; al menos una parte; claves únicas; pesos
   `Decimal` finitos y no negativos (nunca `float`); suma de pesos mayor que cero.
2. Total en centavos enteros (`int`), signo aparte. Pesos escalados a enteros por la potencia de diez
   de su mayor cantidad de decimales. Parte exacta en centavos = `total_c * peso_i / suma`, calculada con
   `divmod` de enteros: cociente = parte truncada, resto = fracción descartada (comparable entre partes
   porque el divisor es común).
3. Faltan `total_c - Σ cocientes` centavos (siempre menos que la cantidad de partes): van de a uno a las
   partes ordenadas por resto descendente y, a igual resto, por `orden` ascendente.
4. Se reaplica el signo y se devuelve `Dinero` por parte.

`redondear_al_centavo(valor: Decimal) -> Dinero` con `ROUND_HALF_UP` (en Python se aleja del cero en
los negativos, igual que `REDONDEAR` de Excel); rechaza todo lo que no sea `Decimal` finito.

**Pruebas de propiedades**: `hypothesis` (versión exacta en el grupo `dev` de `pyproject.toml` y en
`uv.lock`). El oráculo calcula cada parte exacta con `fractions.Fraction` y comprueba: suma exacta;
`|parte − exacta| < 0,01`; toda parte con centavo extra tiene resto mayor o igual que toda parte sin
él; mismo resultado con las partes permutadas. Perfil de CI con `derandomize=True` para que un rojo se
reproduzca igual en cualquier máquina, y un perfil local aleatorio.

- **Descartadas**: medio hacia arriba por parte (la suma se pasa, D-113); `Decimal` con precisión de
  contexto (depende de `getcontext().prec` y de su redondeo); un oráculo que llama a la función de
  producción o repite su fórmula en enteros (QA-4).
- **Costo de revertir**: funciones puras; nada persiste en el 4a.

### D8 · El umbral de R30 vive en cada versión de configuración

- **`config/parametros.yaml`**: sección nueva `cuenta_corriente: { umbral_saldo_chico: "500.00" }`,
  validada como `Dinero` no negativo, con los errores del lector (rutas, nunca valores).
- **Migración `0021`**: `ADD COLUMN umbral_saldo_chico NUMERIC(14,2) NOT NULL DEFAULT 500.00`,
  `CHECK (umbral_saldo_chico >= 0)` y, en la misma migración, `ALTER COLUMN ... DROP DEFAULT`. El 500 es
  el valor de D-109 escrito como hecho histórico para las filas existentes; de ahí en más el valor lo
  pasa siempre la aplicación (D-042). El `ADD COLUMN` con default constante no reescribe filas ni
  dispara el trigger de `UPDATE`; el test lo prueba contra una base con versiones. `downgrade`:
  `DROP COLUMN` (sólo como dueño; ver D1).
- **Dominio**: `ConfiguracionEdificio` suma `umbral_saldo_chico: Dinero | None = None`; `desde_parametros`
  lo toma de `parametros.yaml`.
- **Aplicación**: `crear_version_de_configuracion`, si llega `None`, toma el de la versión
  inmediatamente anterior en vigencia del mismo edificio (la de mayor `vigente_desde` menor que la
  nueva), leída dentro de la misma transacción; si no hay ninguna, el de `parametros.yaml`. La lectura
  de versiones lo devuelve como texto.
- **API**: el cuerpo de versión lo acepta opcional; la respuesta lo trae. **Web**: sólo los fixtures
  que salen de la API real y el tipo de la respuesta; ninguna pantalla lo muestra todavía.

- **Descartadas**: una tabla de parámetros aparte (otro mecanismo de vigencia para lo mismo que ya
  versiona `configuracion_versionada`, D-080); dejar el `DEFAULT 500.00` en la base (un default de
  negocio escrito en una migración, contra D-042); heredar siempre de `parametros.yaml` (un edificio que
  bajó el umbral lo perdería al cambiar la tasa).
- **Costo de revertir**: después de D1, bajar `0021` exige devolver la tabla al migrador (escenario de
  la spec). Por eso entra **antes** que D1 en `tasks.md`.
- **Orden de deploy** (por qué funciona en un solo deploy): `antes()` con el código nuevo no le
  devuelve `configuracion_versionada` al migrador, pero en una base del 3a la tabla **ya es** del
  migrador, así que `0021` corre; recién `despues()` la transfiere.

### D9 · Cinco eventos del padrón, con detalle sin valores (BKS-5, D-016)

Enum nuevo `EventoDelPadron` en `acceso/dominio/eventos.py` (`editar_unidad`, `editar_grupo`,
`fijar_unidades`, `editar_categoria`, `reordenar_categorias`), aceptado por `registrar()`. Migración
`0022` suma los cinco al vocabulario de `accion_de_auditoria` (mismo patrón que `0010`). Un modelo de
detalle `{complejo_id, campos: list[str]}` con `campos` limitado a los nombres de campo de cada caso
de uso. Los cinco casos de uso pasan a recibir `identidad` y `request_id`; la API se los pasa. Se
registra **sólo si algo cambió** (`campos` no vacío) y siempre en la misma transacción.

- **Descartadas**: reusar `configurar_padron` (la acción del permiso) para los cinco (pierde qué se
  hizo y choca con la regla de "una acción por caso de uso"); una decisión que diga que D-016 no los
  alcanza (barata hoy, cara cuando el primer vecino pregunte); guardar los valores anterior y nuevo
  (más útil para reconstruir, pero rompe el criterio de la configuración, que no guarda valores: es la
  alternativa E6 que puede elegir quien firma).
- **Costo de revertir**: `0022` baja sólo si nadie usó los eventos (la FK de auditoría lo impide,
  igual que `0010`).

### D10 · Deuda D-053

El `except TypeError` de `leer_parametros` se borra después de dos tests que lo hacen inalcanzable por
otra capa: raíz que no es un mapa y claves que no son texto, los dos cortados por `cargar_yaml` con
`ParametrosInvalidos` y sin traceback. El lector de la semilla, que tiene la misma forma, se revisa con
el mismo par de tests (L-009). Un test fija que `Dinero("1.0000")` falla.

## Risks / Trade-offs

- [El 4b agrega tablas con FK entrante y la verificación de `TRUNCATE` por catálogo es forma, no
  efecto] → Se acota a esa operación, la función que la ejecuta es la misma que se probó por el efecto
  con `UPDATE` y `DELETE`, y queda escrita como verificación por forma.
- [La verificación de D2 arma filas padre para una tabla vacía y una columna `NOT NULL` nueva en
  `complejo` o `persona` la rompe (L-023)] → Falla ruidosa nombrando la tabla, nunca un pase silencioso;
  el `rg` de L-023 en cada migración que toque esas tablas incluye `roles.py`.
- [Un deploy con el orden invertido: `0021` en un deploy posterior al cambio de dueño] → `0021` y D1 van
  en el mismo change y en ese orden de tareas; si una base local igual quedó así, el constructor lo dice
  en el informe del bloque y Juani decide si se rehace (nunca un `down -v` por su cuenta, L-006).
- [Tests que bajan migraciones como migrador después de `despues()`] → Se adaptan al patrón de
  `test_auditoria_tabla.py:1052` (bajar exige devolver la tabla con el rol de arranque).
- [El chequeo de arranque frena la API en un entorno donde las migraciones no corrieron] → Es el
  comportamiento buscado; el log nombra qué falta (spec `entorno-de-ejecucion`, causa del arranque
  rechazado). Los tests que levantan la app sin migrar se revisan en la tarea.
- [`hypothesis` aleatorio da un rojo que no se reproduce] → Perfil `derandomize` en CI y el ejemplo
  mínimo impreso en el mensaje.
- [El desempate provisorio difiere del Excel de Alberto] → A-1; cambiarlo no toca datos mientras no
  haya reparto persistido (llega con el 6 y el 7).

## Migration Plan

1. Deploy normal: `roles antes` → `alembic upgrade head` (`0021`, `0022`, como migrador) →
   `roles despues` (transfiere y verifica) → API y worker (chequeo de D3).
2. Rollback del código antes de `despues()`: sin efecto en datos. Rollback después: el código viejo
   corre igual (su `antes()` reasigna sólo lo del rol de arranque que no está excluido, y con el código
   viejo `configuracion_versionada` vuelve al migrador en el siguiente `antes()`; la columna nueva queda
   y el código viejo no la nombra, pero su `INSERT` falla por `NOT NULL` sin default). **Por eso el
   rollback de este change exige también bajar `0021`** con la tabla devuelta al migrador. Ensayado en
   la tarea 3.2.
3. Ninguna migración reescribe filas.

## Open Questions

Ninguna cambia las specs ni las tareas si se responde después:

- ¿`crear_unidad` (que fija el coeficiente inicial) también se audita? Hoy no y la exploración no lo
  pidió; se puede sumar al grupo 4 sin cambiar la forma.
- A-1 (Alberto): el centavo del Excel. Si cambia, es D6 y sus tests.
