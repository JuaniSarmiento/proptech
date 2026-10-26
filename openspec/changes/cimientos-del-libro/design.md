## Context

Motivación y alcance en `proposal.md`. Lo que sigue es el estado del código que condiciona el cómo
(HEAD `de3c710`, 26/10/2026), revisado por cinco roles y el auditor (`.git/informes-cimientos-del-libro/`)
y corregido con D-114:

- `compartido/roles.py` reasigna al migrador todo lo que el rol de arranque crea, salvo
  `_TABLA_EXCLUIDA_DE_LA_REASIGNACION = "auditoria"` (un texto, no un conjunto). `despues()` sólo
  transfiere y verifica `auditoria`; para `_TABLAS_DE_SOLO_AGREGAR` (`roles.py:59`, hoy sólo
  `configuracion_versionada`) sólo ajusta `GRANT`. Su verificación de `auditoria` prueba el bloqueo por
  el efecto con una fila insertada en un `SAVEPOINT` (`roles.py:405-515`), atada a esa tabla.
- `configuracion_versionada` (`0009`) bloquea con triggers **por fila** (`UPDATE`, `DELETE`) y uno de
  `TRUNCATE` por sentencia. Un trigger por fila no se dispara sin filas.
- `tests/integracion/test_dueno_de_tablas_solo_agregar.py` controla `auditoria` (verde) y
  `configuracion_versionada` (`xfail(strict=True)`). Su sonda es `NO FORCE ROW LEVEL SECURITY` (L-036).
- `compartido/base_de_datos.py:verificar_rol_de_aplicacion_seguro` frena el arranque si el rol es
  superusuario, tiene `BYPASSRLS` o es dueño de tablas; `app.py:88-93` y `ajustes.py:210-214` atrapan
  sólo `RolDeAplicacionInseguro` para el log `arranque_fallido`.
- `tests/unitarios/test_fronteras_de_modulos.py` recorre imports con `ast`; su recolector pierde el
  submódulo en la forma `from proptech_core.compartido import cola` (EVIDENCIA de QA-2, ya usada en
  `semilla.py:21`) y su `_primer_segmento_relevante` no resuelve bien imports relativos (AR-8; hoy hay
  cero).
- `compartido/dinero.py` no tiene aritmética; `Dinero("1.0000")` ya se rechaza y
  `Dinero.desde_decimal(Decimal("1.0000"))` ya devuelve `1.00` (EVIDENCIA de BE-2, 09:49).
- `migraciones/env.py` corre todas las migraciones pendientes en una sola transacción (DB-9).
- Los casos de uso del padrón no reciben `Identidad` ni `request_id`; `editar_unidad` lee el coeficiente
  como texto de seis decimales (`unidades.py:120`); `crear_grupo` y `fijar_unidades` comparten
  `_reemplazar` (`grupos.py:116`), que borra y vuelve a insertar miembros.
- `complejos/aplicacion/ejemplo.py:39` importa `acceso.dominio.eventos`.

## Goals / Non-Goals

**Goals:**

- Que los controles (fronteras, dueño, reparto, umbral, auditoría del padrón) existan y den rojo ante
  su violación **antes** de que el 4b cree la primera tabla de plata.
- Que la columna nueva y el trigger por sentencia de `configuracion_versionada` entren en el mismo
  deploy en que la tabla pasa al rol de arranque, y antes de ese paso.

**Non-Goals:**

- Nada del libro (4b), de intereses ni del moroso crítico (4c), ni del cambio de titular (4d).
- No construir el préstamo de propiedad para migraciones futuras (D3).
- No tocar pantallas.

## Decisions

### D0 · Una sola fuente para el conjunto de tablas protegidas (AR-4)

Módulo nuevo `compartido/tablas_protegidas.py`, sin dependencias más que la biblioteca estándar. Declara
`TABLAS_DE_SOLO_AGREGAR: Mapping[str, TablaProtegida]` con, por tabla, el texto exacto del `RAISE` de su
función de bloqueo y los nombres de sus triggers esperados. `auditoria` figura con un marcador propio:
su verificación sigue siendo la de hoy (D2). Lo importan `roles.py`, `base_de_datos.py` y los tests;
nadie más declara la lista (L-022). Se descarta que `base_de_datos.py` importe `roles.py` (dirección
"arranque de la API → herramienta de deploy") y duplicar la lista. Revertir cuesta mover una constante.

### D1 · El rol de arranque es dueño de toda tabla de sólo agregar (DBA-1, opción a)

`antes()` excluye de la reasignación todo el conjunto de D0 (deja de ser un texto). `despues()`, para
cada tabla del conjunto que exista: `ALTER TABLE ... OWNER TO` el rol de arranque, lo mismo con las
funciones de sus triggers (con `SET search_path = ''`), `REVOKE UPDATE, DELETE, TRUNCATE` y
`GRANT SELECT, INSERT` a la app, y recién después la verificación de D2. Una tabla del conjunto que
todavía no existe se saltea y se dice en la salida; el chequeo de D3 es el que la rechaza. Todo en la
misma transacción que hoy.

**Qué hace el 4b, exactamente** (corrige la frase de la primera versión, AR-1): (1) suma sus seis
tablas a `compartido/tablas_protegidas.py`, con el texto del `RAISE` de su función y los nombres de sus
triggers; (2) crea cada tabla en su migración con sus triggers por fila de `UPDATE` y `DELETE`, su
trigger `BEFORE TRUNCATE` y el trigger `BEFORE UPDATE OR DELETE ... FOR EACH STATEMENT` de D-114.4, los
tres con la misma función. **No** toca la lógica de `roles.py` ni escribe ningún armador de filas: la
sonda de D2 no necesita filas. El test de dueño tampoco cambia: lee el conjunto de D0.

- **Descartadas**: (b) el migrador dueño, escrito como decisión: un archivo de migración podría
  `NO FORCE` y reescribir el libro; (c) un rol de propiedad aparte: con membresía equivale a (b), sin
  ella equivale a (a) con un rol más que mantener.
- **Costo de revertir**: ver el Migration Plan (D-114.5).
- **Salvedad** (EVIDENCIA del explore, `infra/compose.yaml:83-85`): el servicio de migraciones ya
  tiene la credencial del rol de arranque. Esto protege contra una migración o la credencial del
  migrador, no contra quien controla ese contenedor.

### D2 · La protección se verifica por el efecto, sin armar filas (L-018, D-114.4)

`_verificar_tabla_protegida(cur, tabla, declaracion, arranque)` corre para cada tabla del conjunto
salvo `auditoria`, que conserva su verificación actual (`auditoria` es del rol de arranque desde el
2a: el migrador ya no puede sumarle un trigger por sentencia, y su sonda con fila no necesita padres).
Comprueba:

- `relrowsecurity` **y** `relforcerowsecurity` (el gemelo de L-018: RLS deshabilitada con `FORCE`
  intacto falla);
- los triggers declarados en D0, presentes y con `tgenabled = 'O'`, y sus funciones del rol de
  arranque;
- el bloqueo de verdad, cada intento en su `SAVEPOINT` revertido, exigiendo SQLSTATE `P0001` **y** el
  texto del `RAISE` de esa tabla (nunca "cualquier error", V3-2):
  - `UPDATE <tabla> SET <primera columna> = <primera columna> WHERE false`;
  - `DELETE FROM <tabla> WHERE false`;
  - `TRUNCATE <tabla>` si nadie la referencia, y `TRUNCATE <tabla> CASCADE` si tiene FK entrante: con
    `CASCADE` el trigger de la tabla nombrada se dispara antes del chequeo de FK (EVIDENCIA de DB-4,
    09:44:12). Si el trigger estuviera roto, el `CASCADE` vaciaría las tablas que la referencian sólo
    dentro del savepoint, que se revierte. Cuesta un `ACCESS EXCLUSIVE` breve mientras corre `despues()`.

Con esto no queda ninguna verificación por forma (la primera versión dejaba el `TRUNCATE` con FK por
catálogo, sobre una premisa que DB-4 mostró falsa).

El trigger por sentencia **bloquea también `INSERT ... ON CONFLICT DO UPDATE`**, aunque no haya
conflicto (EVIDENCIA de DB-5, 09:45:11); `ON CONFLICT DO NOTHING` y `MERGE ... WHEN NOT MATCHED THEN
INSERT` no lo disparan. El 4b lo tiene que saber para su idempotencia (explore 4.4): en una tabla de
sólo agregar, el camino es `DO NOTHING` y leer la fila existente.

La política de RLS de `auditoria` se sigue comparando entera (V3-1); para las demás tablas la vigila
`test_catalogo_rls.py` como hoy (deuda del 15, decisión de Juani en el 2a).

- **Descartadas**: armar filas padre dentro del `SAVEPOINT` (deja a `compartido` conociendo el esquema
  de `complejos` y `cuenta_corriente`, y se rompe con cada `NOT NULL` nuevo en una tabla padre, L-023);
  copiar la sonda de `auditoria` tal cual (necesita filas); `TRUNCATE` por catálogo.
- **Costo de revertir**: una función y, por tabla, una migración que saque el trigger por sentencia
  (con el préstamo de D3).

### D3 · Los procesos no arrancan si una tabla protegida tiene otro dueño; el préstamo queda escrito

Nueva `verificar_tablas_de_solo_agregar(engine)` en `base_de_datos.py`, con su excepción propia
`TablasDeSoloAgregarDesprotegidas`. Se llama junto a `verificar_rol_de_aplicacion_seguro` en la API,
el worker, `alta_inicial` y `ejemplo`; la API y el worker la atrapan igual que a
`RolDeAplicacionInseguro` y registran `arranque_fallido` con la causa (BE-7). Compara el **conjunto
entero** de D0 contra `pg_tables` filtrado por `schemaname = 'public'` (una tabla homónima en otro
esquema o temporal no la hace pasar, DB-6) y `pg_roles`: cada una tiene que existir y su dueño ser
superusuario. Nombra cada tabla con problema; nunca un valor (L-007). `proptech_app` lee esos catálogos
sin permiso nuevo (EVIDENCIA de DB-6).

**No hay forma de saltear el chequeo por configuración**: ninguna variable de entorno ni bandera. Los
tests que levantan la app sin migrar lo reemplazan con `monkeypatch`, nunca con una opción de
producción.

"Superusuario" y no "el rol de arranque por nombre": la app no conoce ese nombre y el migrador nunca lo
es (`roles.py` lo exige).

Un test aparte compara el conjunto de D0 contra el catálogo: toda tabla de `public` con `FORCE ROW
LEVEL SECURITY` y un trigger cuya función bloquea `UPDATE` tiene que estar en el conjunto (QA-16). Así
una tabla del 4b que alguien olvide declarar da rojo.

**Migraciones futuras sobre una tabla protegida** (no se construye ahora): la migración declara qué
tablas protegidas toca; `antes()` le presta la propiedad al migrador sólo de ésas y sólo si esa
migración está pendiente; `despues()` la devuelve y verifica con D2. Se agrega a `09` al archivar.
Mientras tanto, un `ALTER` falla con `must be owner`, que es el comportamiento seguro.

- **Descartado**: préstamo general en cada `antes()`; comparar contra el nombre del rol de arranque;
  una variable para saltear el chequeo en desarrollo.
- **Costo de revertir**: una función, una excepción y cuatro llamadas.

### D4 · Cinco reglas de fronteras, por lista permitida (ARQ-2, D-114.7)

Primero se corrige el recolector de imports del test: registra el submódulo en las tres formas
(`import a.b.c`, `from a.b import c`, `from a import b`) y resuelve los relativos por `level`; los
imports relativos **entre módulos** quedan prohibidos (AR-8, QA-2). Sobre ese recorrido:

- **(a) Sin ciclos**: grafo módulo → módulo (sin `compartido`) con todas las capas; detección de
  ciclos de cualquier largo, con el ciclo en el mensaje. Mutantes de dos y de tres nodos (AR-3).
- **(b) Entre módulos sólo `aplicacion`**: todo import de `proptech_core.<otro>` es
  `proptech_core.<otro>.aplicacion[...]` o un destino exceptuado, comparado por segmentos completos
  (`acceso.dominio.identidad_x` no entra por la excepción de `identidad`). Excepciones, cada una con su
  motivo: `acceso.dominio.identidad` y `acceso.dominio.permisos` (`Identidad` y `Accion` viajan en todo
  caso de uso auditado); `acceso.dominio.eventos` (**nueva**: el vocabulario de auditoría viaja con
  `registrar()`; la sostienen los eventos del padrón de D9, no sólo `ejemplo.py:39`, AR-5). Las
  excepciones son globales por destino: `cuenta_corriente` también podrá importar los eventos. Fuera de
  la regla: `proptech_api` y `proptech_worker` (raíz de composición).
- **(c) Lista permitida para `dominio/`**: de `compartido` sólo `dinero`, `coeficientes`,
  `porcentaje`, `superficie`, `texto`, `tipos_de_unidad` y `reparto`; `parametros` como excepción con
  motivo (`complejos/dominio/configuracion.py:11`, para `desde_parametros`).
- **(d) `cuenta_corriente`** no importa `compartido.cola` ni `liquidacion`.
- **(e) El dominio no depende de su propia infraestructura** (D-114.7): un archivo de `dominio/` no
  importa la `aplicacion`, los `adaptadores` ni los `puertos` de su módulo, ni `sqlalchemy` ni
  `psycopg`. Pasa hoy sin tocar nada (EVIDENCIA de AR-2, 09:35:55).

Cada regla con mutantes en copia temporal que dan rojo en **su** aserción, uno por forma de import
donde aplica. Se crea `proptech_core/cuenta_corriente/` con `__init__.py`, `dominio/__init__.py` y
`aplicacion/__init__.py`, vacíos.

**Límite declarado** (AR-7): las reglas miran imports directos. La excepción `parametros` arrastra la
lectura de archivos de forma transitiva, nada obliga a que la lista permitida siga siendo pura, y
`cuenta_corriente → acceso.aplicacion.<algo que encola>` pasaría (d). Queda escrito, no vigilado.

- **Descartadas**: lista de prohibidos (falla abierta); relajar (b) a "no importar `adaptadores`";
  mover `Identidad`, `Accion` y los eventos a `compartido`; mover `ejemplo.py` a una raíz de
  composición (AR-5, alternativa válida que se deja para cuando se toque ese archivo).
- **Costo de revertir**: un archivo de test.

### D5 · Aritmética de `Dinero`: suma, resta y negación, nada más

`__add__`, `__sub__` y `__neg__` entre `Dinero`, y `sumar(montos: Iterable[Dinero]) -> Dinero` (cero
para la lista vacía). Todo otro operando devuelve `NotImplemented` (Python levanta `TypeError`). El
resultado pasa por `Dinero.desde_decimal`, que rechaza lo que no entra en `NUMERIC(14,2)`. La cuenta se
hace dentro de un `localcontext` propio con precisión suficiente, así el resultado no depende del
contexto decimal de quien llama (QA-7). Sin `__mul__`, `__truediv__` ni `__radd__`. El docstring del
módulo deja de decir "sin aritmética".

**`desde_decimal` y los ceros de más (D-114.6)**: acepta `Decimal("1.0000")` (y el `0.3000` de un
`SUM()`), porque el valor no cambia; rechaza `1.005` y `1.0001`. Es el comportamiento de hoy, que pasa
a estar escrito y probado; la nota de D-053 queda corregida por D-114.6.

- **Descartada**: aritmética completa con `Decimal`; que `desde_decimal` rechace los ceros de más
  (rompería la lectura de sumas de la base).
- **Costo de revertir**: tres métodos; nada persiste.

### D6 · Desempate del mayor resto: orden natural del identificador, después el id

`compartido/reparto.py` expone `ParteARepartir(clave, peso: Decimal, orden: tuple)` y
`clave_de_orden_natural(identificador: str, id: UUID) -> tuple`. El identificador se parte en tramos
de dígitos ASCII y tramos de lo demás (`re.ASCII`). **Cada tramo va etiquetado con su tipo**: un tramo
de dígitos es `(0, int)` y uno de texto `(1, texto.casefold())`, así **un número va antes que una
letra** y nunca se comparan un entero y un texto (AN-1, BE-1, QA-3). Después de los tramos, el texto
original y por último el UUID. Los dígitos no ASCII son texto.

Orden fijado por test con los identificadores de la semilla: **"1A", "10A", "B1", "C1", "L-PB"**; y
"1", "1A", "A1", "PB". El reparto no sabe qué es una unidad: recibe la clave ya armada.

- **Descartadas**: orden de texto plano ("10A" antes que "2B"); el "menor número de unidad" de D-109
  como número puro (los identificadores son texto libre); el UUID solo; letras antes que números.
- **Provisoria**: A-1 (Alberto) puede cambiarla; no toca datos mientras el reparto no se persista.

### D7 · El reparto trabaja en centavos enteros; el redondeo suelto es otra función

**Ubicación**: `compartido/reparto.py`. Se descarta ponerlo en `cuenta_corriente` (crearía
`gastos → cuenta_corriente` por una sola función); revertirlo es barato hasta que el 6 lo use (AR-6).
**Firma que manda**: `repartir(total: Dinero, partes: Sequence[ParteARepartir]) -> dict[clave, Dinero]`;
la de la sección 5 del explore (`repartir(total, coeficientes) -> list[Dinero]`) queda reemplazada.

1. Valida con `RepartoInvalido` (subclase de `ValueError`): total `Dinero`; al menos una parte; claves
   únicas; pesos `Decimal` finitos y no negativos, con a lo sumo 6 decimales y 12 dígitos enteros
   (tope que evita escalar un `1E-999999`, BE-8); un `int` o un `float` como peso se rechaza; suma de
   pesos mayor que cero.
2. Total en centavos enteros, signo aparte. Pesos escalados a enteros con aritmética entera
   (`Decimal.scaleb` o `as_integer_ratio`, nunca `10 ** -exp`, que da `float` con `1E+2`, QA-6).
   Parte exacta en centavos = `total_c * peso_i / suma`, con `divmod` de enteros: cociente = parte
   truncada, resto = fracción descartada.
3. Faltan `total_c - Σ cocientes` centavos (menos que la cantidad de partes): van de a uno a las partes
   por resto descendente y, a igual resto, por `orden` ascendente.
4. Se reaplica el signo (**total negativo simétrico**: la regla que se firma en E8) y se devuelve
   `Dinero` por parte.

`redondear_al_centavo(valor: Decimal) -> Dinero` con `ROUND_HALF_UP` en un `localcontext` propio (se
aleja del cero en los negativos, como `REDONDEAR` de Excel); rechaza todo lo que no sea `Decimal`
finito, y convierte un valor fuera de rango en `MontoInvalido`.

**Pruebas de propiedades**: `hypothesis` con versión exacta en el grupo `dev` y en `uv.lock`. El
oráculo calcula cada parte exacta con `fractions.Fraction` y no importa ni repite la función de
producción. Propiedades: suma exacta; `|parte − exacta| < 0,01`; toda parte con centavo extra tiene
resto mayor o igual que toda parte sin él; mismo resultado con las partes permutadas. La estrategia
**fuerza empates** (pesos de `sampled_from` de un conjunto chico y pesos iguales) y mezcla
identificadores que empiezan con letra y con número; con pesos aleatorios de 6 decimales casi no hay
empates (EVIDENCIA de QA-4: 0 en 2000). Un mutante por propiedad: desempate por posición (orden),
centavo al mayor peso (restos), sin normalizar por la suma (distancia), `ROUND_HALF_UP` por parte
(suma). Perfil `ci` con `derandomize=True` y `deadline=None`, elegido por variable de entorno en
`infra/ci/test-backend.sh`, con un test de infra que lo fija (QA-17).

- **Descartadas**: medio hacia arriba por parte (la suma se pasa, D-113); `Decimal` con precisión de
  contexto; un oráculo que repite la fórmula (QA-4 del cimientos).
- **Costo de revertir**: funciones puras; nada persiste en el 4a.

### D8 · El umbral de R30 vive en cada versión de configuración

- **`config/parametros.yaml`**: sección nueva `cuenta_corriente: { umbral_saldo_chico: "500.00" }`,
  validada como `Dinero` no negativo, escrito como texto, con los errores del lector (rutas, nunca
  valores).
- **Migración `0021`**, en este orden: `ADD COLUMN umbral_saldo_chico NUMERIC(14,2) NOT NULL DEFAULT
  500.00`, `CHECK (umbral_saldo_chico >= 0)`, `ALTER COLUMN ... DROP DEFAULT`, y el trigger
  `trg_configuracion_sin_update_delete_por_sentencia BEFORE UPDATE OR DELETE ... FOR EACH STATEMENT`
  con `fn_configuracion_versionada_bloqueada` (D-114.4). El `ADD COLUMN` con default constante no
  reescribe filas ni dispara el trigger de `UPDATE` (EVIDENCIA de DB-2: mismo `relfilenode` sobre 10.000
  filas, `attmissingval {500.00}`). Nunca un relleno con `UPDATE`: como migrador, con `FORCE`, vería
  cero filas y no haría nada (DB-3). El 500 es el valor de D-109 escrito como hecho histórico para las
  filas existentes; de ahí en más el valor lo pasa la aplicación (D-042). `downgrade`: saca el trigger
  por sentencia y la columna (sólo como dueño, ver D1); bajar y volver a subir deja todo en 500.
- **Dominio**: `ConfiguracionEdificio` suma `umbral_saldo_chico: Dinero | None = None`, con validación
  de no negativo; `desde_parametros` lo toma de `parametros.yaml`.
- **Aplicación** (D-114.1): si llega `None` (campo ausente o `null`),
  `crear_version_de_configuracion` toma el de la versión **inmediatamente anterior por
  `vigente_desde`** del mismo edificio, aunque sea futura (la de mayor `vigente_desde` menor que la
  nueva), leída en la misma transacción; si no hay ninguna, el de `parametros.yaml`. La consulta usa
  `uq_configuracion_vigencia` (`Index Scan Backward`, una búsqueda, EVIDENCIA de DB-7); no hace falta
  índice nuevo. **`crear_edificio`** (`POST /api/complejos`) con `configuracion_inicial` sin umbral toma
  el de `parametros.yaml`, y lo acepta y valida igual que en versiones (BE-3): sin esto, inserta `NULL`
  y responde 500.
- **API**: el umbral es opcional en el cuerpo de versión y en el de alta; la respuesta lo trae. **Web**:
  sólo los fixtures que salen de la API real y el tipo de la respuesta; ninguna pantalla lo muestra.

- **Descartadas**: una tabla de parámetros aparte; dejar el `DEFAULT 500.00` en la base (contra
  D-042); heredar de la versión vigente hoy (D-114.1); heredar siempre de `parametros.yaml`.
- **Orden de deploy**: `antes()` con el código nuevo no le devuelve `configuracion_versionada` al
  migrador, pero en una base del 3a la tabla **ya es** del migrador, así que `0021` corre; recién
  `despues()` la transfiere (reproducido por el DBA, 09:43:40 y 09:44:26). Por eso `0021` va antes que
  D1 en `tasks.md`.

### D9 · Siete eventos del padrón, con el coeficiente anterior y el nuevo (BKS-5, D-016, D-114.2/3)

Enum nuevo `EventoDelPadron` en `acceso/dominio/eventos.py`: `crear_unidad`, `editar_unidad`,
`crear_grupo`, `editar_grupo`, `fijar_unidades`, `editar_categoria`, `reordenar_categorias`. Migración
`0022` los suma al vocabulario de `accion_de_auditoria` (patrón de `0010`). Queda en `acceso` porque la
auditoría es de ese dominio (KB 08) y el precedente es `Accion.CREAR_EDIFICIO`; la alternativa, que cada
módulo defina su enum y `registrar` acepte cualquier `StrEnum`, cuesta sólo código si se quiere después
(AR-9).

**Detalle**, un modelo por evento con `extra="forbid"`:

- todos: `complejo_id` y `campos` (lista limitada a los campos de **ese** evento);
- `crear_unidad` y `editar_unidad`: además `coeficiente: {anterior, nuevo}` (texto, `anterior` vacío en
  el alta), sólo si el coeficiente cambió;
- `crear_grupo` y `fijar_unidades`: además `coeficientes: [{unidad_id, anterior, nuevo}]` para cada
  miembro con coeficiente propio que cambió, entró (`anterior` vacío) o salió (`nuevo` vacío);
- de los demás campos (identificador, piso, superficie, nombre, orden), sólo el nombre.

**"Sólo si algo cambió"**: se compara contra los valores normalizados de cada modelo (`DatosUnidad`,
`Coeficiente`), nunca contra el texto crudo: "0.05" contra el "0.050000" guardado no es un cambio
(BE-9). En `fijar_unidades`, que borra y vuelve a insertar, se compara el conjunto de miembros con sus
coeficientes antes y después. Los siete casos de uso reciben `identidad` y `request_id`; la API se los
pasa; `registrar()` corre en la misma sesión y transacción, así un fallo de la auditoría revierte el
cambio.

- **Descartadas**: reusar `configurar_padron` para todos; no auditar (D-016 escrita); no guardar
  valores (D-114.2); auditar sólo ediciones (D-114.3).
- **Costo de revertir**: `0022` baja sólo si nadie usó los eventos (FK de `auditoria`, `23503`), igual
  que `0010`. Ese es el punto de no retorno del Migration Plan.

### D10 · Deuda D-053

El `except TypeError` de `leer_parametros` se borra después de dos tests que lo hacen inalcanzable por
otra capa (raíz que no es un mapa, claves que no son texto, los dos cortados por `cargar_yaml` con
`ParametrosInvalidos`); el lector de la semilla, de la misma forma, lleva el mismo par (L-009). El
mutante de `cargar_yaml` se corre **después** de borrar el `except` (con el `except` todavía, lo
atraparía y el test quedaría verde, QA-8). Para `Dinero`, los tests de D5 (`desde_decimal` acepta ceros
sin cambiar el valor, rechaza lo que cambiaría; el texto rechaza ceros de más) se ven fallar con
mutantes: `desde_decimal` sin la comparación `cuantizado != valor` (acepta `1.005`), y el patrón del
texto con `\d{1,4}` y `quantize` (acepta `"1.0000"`).

## Risks / Trade-offs

- [El trigger por sentencia bloquea `INSERT ... ON CONFLICT DO UPDATE`] → Escrito en D2 y en la spec;
  el 4b usa `DO NOTHING` para su idempotencia.
- [`TRUNCATE ... CASCADE` en la sonda toma un `ACCESS EXCLUSIVE` breve sobre las tablas que referencian]
  → Corre sólo en `despues()`, durante el deploy, dentro de un savepoint que se revierte.
- [Un deploy con el orden invertido: `0021` en un deploy posterior al cambio de dueño] → `0021` y D1 van
  en el mismo change y en ese orden de tareas; si una base local quedó así, el constructor lo dice en el
  informe del bloque y Juani decide si se rehace (nunca un `down -v` por su cuenta, L-006).
- [Tests que bajan migraciones como migrador después de `despues()`] → Se adaptan al patrón de
  `test_auditoria_tabla.py:1052`.
- [El chequeo de arranque frena la API donde las migraciones no corrieron] → Comportamiento buscado; los
  tests lo reemplazan con `monkeypatch` (D3).
- [Comparaciones "fila por fila" leídas como migrador sin tenant comparan dos conjuntos vacíos (DB-3)]
  → Los tests de `0021` leen como rol de arranque.
- [El desempate provisorio difiere del Excel de Alberto] → A-1; no toca datos mientras no haya reparto
  persistido.

### Deuda aceptada de la revisión (no bloquea, queda registrada)

- **Arquitecto**: AR-5 (mover `ejemplo.py` a una raíz de composición), AR-6 resuelta en D7, AR-7
  (límite de las reglas, escrito en D4), AR-8 resuelta en D4, AR-9 (dirección de los eventos, escrita en
  D9).
- **Backend**: BE-8 resuelta en D7 (tope de decimales); el resto de BE quedó en las tareas.
- **DBA**: DB-2 (comparar el esquema de `0020` con `pg_dump -s` o `information_schema`, no con
  `pg_attribute` crudo, que conserva la columna borrada), DB-3 (leer como rol de arranque), DB-7 (índice
  nombrado en D8).
- **Analista**: AN-7 (la negación ya tiene escenario; el requisito relajado de comparación no tiene caso
  que falle hoy, es esperable), AN-9 (actor "cliente de la API" en la spec).
- **QA**, sin tarea propia en el 4a: QA-6 y QA-7 en D7 y D5 sin test dedicado más allá de lo que listan
  2.1, 2.2 y 2.4; QA-9 (SQLSTATE del `UPDATE` del umbral y borde "0.00" del `CHECK`, en la 3.2); QA-12
  (modelo de detalle permisivo, en la 4.1); QA-14 (migración de prueba que hace algo antes del `ALTER`,
  en la 5.1); QA-15 (función con otro dueño, texto de `auditoria` en la función de
  `configuracion_versionada`: van a la 5.2 si entran en el medio día, si no quedan como deuda del 4b); el
  test de que el CI usa el perfil `ci` va en la 2.5. Lo que no entre se anota en el informe del
  constructor como deuda con dueño 4b.
- **Rompedor del apply** (`11-rompedor.md`; RB-1, RB-2, RB-3, RB-8 y RB-9 se corrigieron en la vuelta 2):
  - RB-4: el mutante que saca `WHERE t.schemaname='public'` de `verificar_tablas_de_solo_agregar`
    sobrevive; el test de la tabla homónima pasa por el orden del catálogo, no por el filtro.
  - RB-5: el mutante que no registra `modo_de_coeficientes` en `campos` de `fijar_unidades` sobrevive;
    tampoco se registra qué unidades entran o salen de un grupo `renormalizado`.
  - RB-6: `redondear_al_centavo` con |valor| ≥ ~1e30 levanta `decimal.InvalidOperation`, no
    `MontoInvalido` como dice D7. Hoy no tiene consumidor.
  - RB-7 (anterior al 4a): `Dinero(texto)` construido bajo un contexto de baja precisión levanta
    `InvalidOperation`; la aritmética sí está aislada, el constructor no.
  - RB-10: al archivar, agregar a D-114.4 de la KB 09 la excepción de `auditoria` (E1).
  - RB-11: la 4.1 no tiene el rojo de la aceptación con `0022` vacía; lo reemplazan dos mutantes.
  - El ensayo de roles sólo se prueba corriéndolo: `test_ensayo_login.py` fija el número de revisión y
    el orden del paso 1 del rollback en el texto del script, no que el script funcione. No corre en CI.

## Migration Plan

**Deploy** (D-114.5): `roles antes` → `alembic upgrade head` (`0021` y `0022` juntas, en una sola
transacción por `env.py`) → `roles despues` (transfiere y verifica) → API y worker (chequeo de D3).
Cualquier corte deja la base consistente: en `0020`, o con la tabla todavía del migrador y la API sin
arrancar (DB-9).

**Rollback, mientras ningún evento del padrón se haya registrado**. El código viejo **no** arranca
sobre la base nueva: su `alembic upgrade head` no encuentra `0022` y el servicio de migraciones termina
en error, así que nada levanta (EVIDENCIA de DB-1, 09:44:54). El procedimiento real, en orden:

1. Con el código **nuevo** todavía desplegado, como rol de arranque:
   `ALTER TABLE configuracion_versionada OWNER TO proptech_migrador;` y
   `ALTER FUNCTION fn_configuracion_versionada_bloqueada() OWNER TO proptech_migrador;` (el `antes()`
   viejo devuelve la tabla pero no la función, DB-8).
2. Con el código nuevo, como migrador: `alembic downgrade 0020`. Baja `0022` (vocabulario) y `0021`
   (trigger por sentencia y columna). Los umbrales cargados se pierden.
3. Recién entonces, desplegar el código viejo.

**Punto de no retorno**: el primer evento del padrón registrado en `auditoria`. Desde ahí, bajar `0022`
falla con `23503` (`fk_auditoria_accion`), porque la auditoría no se borra; la única vuelta atrás es
restaurar el respaldo, o arreglar hacia adelante. Se acepta así porque todavía no hay producción
(D-114.5). La tarea 3.2 ensaya la bajada de `0021` suelta y la 5.1 el procedimiento con la tabla
devuelta; el punto de no retorno se fija con un test en la 4.1.

Ninguna migración reescribe filas.
