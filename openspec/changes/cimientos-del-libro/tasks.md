Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el rojo
se anota en el informe con el comando, su salida y la hora. **El rojo cuenta sólo si cae en la aserción
que el test dice probar** (L-034): un `ModuleNotFoundError` o un `ImportError` no es un rojo. Cuando el
módulo todavía no existe, primero se crea vacío (la función existe y devuelve vacío o `None`) y el rojo
se mide contra eso. "Verde" en el backend es `bash infra/ci/test-backend.sh` sobre los archivos tocados,
más `ruff check`, `ruff format --check` y `mypy` (L-005). Cada tarea nombra los escenarios que cubre
(`capability` › escenario) y las lecciones que aplica.

**NO CONSTRUIR**: el change es **HIGH**. Precondición: la sección "Aprobación" de `proposal.md`
firmada por Juani, Alberto o Emiliano, con nombre, fecha y la respuesta a cada elección (D-094, D-111).
Una regla nueva que entre después de la firma necesita firma propia (L-029).

**Orden obligatorio**: el grupo 3 (la columna nueva de `configuracion_versionada`) va **antes** del
grupo 5 (la tabla pasa al rol de arranque). Al revés, la migración `0021` falla por no ser el migrador
el dueño (design D8).

## 1. Fronteras entre módulos (design D4)

- [ ] 1.1 **Paquete `cuenta_corriente/` vacío y regla (a), sin ciclos.** Crear
  `proptech_core/cuenta_corriente/` con `__init__.py`, `dominio/__init__.py` y `aplicacion/__init__.py`
  vacíos. Test nuevo en `tests/unitarios/test_fronteras_de_modulos.py`: arma el grafo módulo → módulo
  (sin `compartido`) con todas las capas y exige que no tenga ciclos, listando los módulos recorridos.
  RED: con la función de detección devolviendo siempre "sin ciclos", el mutante en copia (agregar a
  `acceso` un import de `complejos.aplicacion`) **pasa**; se escribe la detección y el mutante da rojo
  nombrando `acceso → complejos → acceso`. Verificación: árbol real en verde, mutante en rojo.
  Escenarios: `fronteras-de-modulos` › El código de hoy no tiene ciclos; › Un ciclo agregado a una
  copia. Lecciones: L-013, L-019, L-035.
- [ ] 1.2 **Regla (b), entre módulos sólo `aplicacion`.** Test con el diccionario de excepciones por
  submódulo destino y su motivo (`acceso.dominio.identidad`, `acceso.dominio.permisos`,
  `acceso.dominio.eventos`), `proptech_api` y `proptech_worker` fuera. RED: sin la excepción de
  `acceso.dominio.eventos`, el árbol real da rojo en `complejos/aplicacion/ejemplo.py:39` (prueba de
  que la regla mira de verdad); con la excepción, verde. Dos mutantes en copia: un import de
  `acceso.dominio.token` y uno de `acceso.adaptadores` desde `complejos`, cada uno rojo nombrando
  archivo y destino. Escenarios: `fronteras-de-modulos` › Las excepciones de hoy pasan; › Un import de
  dominio ajeno sin excepción; › Un import de adaptadores ajenos. Lecciones: L-013, L-021 (el mutante
  de adaptadores no es el mismo camino que el de dominio), L-035.
- [ ] 1.3 **Regla (c), `dominio/` sólo usa lo puro de `compartido`, y regla (d) de
  `cuenta_corriente`.** Lista permitida (`dinero`, `coeficientes`, `porcentaje`, `superficie`,
  `texto`, `tipos_de_unidad`, `reparto`) con `parametros` como excepción con motivo; `cuenta_corriente`
  no importa `compartido.cola` ni `liquidacion`. RED de (c): sin `parametros` en la excepción, el árbol
  real da rojo en `complejos/dominio/configuracion.py:11`. Mutantes en copia: `dominio/` importando
  `compartido.base_de_datos`; un `compartido/nuevo.py` creado en la copia e importado desde `dominio/`
  (rojo sin que nadie lo haya escrito en ninguna lista); `cuenta_corriente/aplicacion` importando
  `compartido.cola`. Escenarios: `fronteras-de-modulos` › El dominio de hoy pasa; › El dominio importa
  la base; › Un submódulo nuevo de compartido; › El paquete existe y pasa; › La cuenta corriente
  importa la cola. Lecciones: L-013, L-022 (lista permitida, no de prohibidos).

## 2. Montos y reparto (design D5 a D7)

- [ ] 2.1 **`hypothesis` y aritmética de `Dinero`.** Sumar `hypothesis` con versión exacta al grupo
  `dev` y a `uv.lock`, con los perfiles `ci` (`derandomize=True`) y local. Tests en
  `tests/unitarios/test_dinero.py`: suma y resta exactas, negación, `sumar([])` da `"0.00"`, operandos
  `int`, `float`, `Decimal` y texto dan `TypeError`, desborde de `NUMERIC(14,2)` da `MontoInvalido`,
  multiplicar y dividir dan `TypeError`. RED: con `__add__`, `__sub__`, `__neg__` y `sumar` existiendo y
  devolviendo `Dinero("0.00")`, falla la aserción de valor. Actualizar el docstring de `dinero.py`.
  Escenarios: `representacion-de-montos` › Suma y resta exactas; › Sumar un número que no es monto;
  › Desborde; › Sumar una lista vacía; › Sin multiplicación. Lecciones: L-034.
- [ ] 2.2 **Redondeo medio hacia arriba para montos sueltos.** `redondear_al_centavo` en
  `compartido/reparto.py`. Tests: 0.125 → 0.13, 0.124999 → 0.12, -0.125 → -0.13, `float` rechazado,
  `NaN` e infinito rechazados. RED: con la función devolviendo `ROUND_HALF_EVEN` (mutante deliberado
  en la versión vacía, anotado), 0.125 da 0.12 y falla la aserción. Escenarios: `reparto-de-montos`
  › El medio sube; › Float rechazado. Lecciones: L-034, L-008.
- [ ] 2.3 **Orden natural para el desempate.** `clave_de_orden_natural(identificador, id)`. Tests:
  "1" < "2" < "10"; "2B" < "10A"; "a2" y "A2" no empatan al final (desempata el texto original y luego
  el UUID); dos identificadores iguales ordenan por UUID; dígitos no ASCII no se leen como número
  (L-008). RED: con la clave devolviendo el texto plano, "10" queda antes que "2". Escenarios:
  `reparto-de-montos` › Orden natural, no de texto. Lecciones: L-008.
- [ ] 2.4 **`repartir` por mayor resto, con ejemplos.** Tests de ejemplo de R07 y de la spec: un
  millón entre 150 (100 partes de 6.666,67 y 50 de 6.666,66), una sola parte, pesos que no suman 1,
  total cero, $2,00 entre tres (y la comparación explícita con medio hacia arriba que daría 2,01), el
  centavo al mayor resto, total negativo, "1", "2", "10" con el centavo por orden natural, el mismo
  reparto 100 veces con las partes en otro orden, y cada rechazo de `RepartoInvalido` (total `float`,
  sin partes, peso negativo, peso `float`, pesos en cero, claves repetidas). RED: con `repartir`
  existiendo y devolviendo cada parte en cero, falla la suma. Escenarios: `reparto-de-montos` › los
  cuatro de "El reparto suma exacto el total", los tres de "Cada parte se trunca...", los dos de "El
  empate se resuelve siempre igual" y los dos de "El reparto rechaza entradas...". Lecciones: L-034.
- [ ] 2.5 **Propiedades del reparto con `hypothesis` y oráculo propio.** Test en
  `tests/unitarios/test_reparto_propiedades.py`: totales y pesos generados (incluido el borde de 12
  dígitos y pesos con 6 decimales), oráculo con `fractions.Fraction` que **no** importa ni repite la
  función de producción; propiedades: suma exacta, distancia menor a un centavo, centavo extra sólo a
  restos mayores o iguales, independencia del orden. RED real: en una copia de `reparto.py` (L-013),
  cambiar el truncado por `ROUND_HALF_UP` y ver que la propiedad de suma exacta encuentra un
  contraejemplo; restaurar y ver verde. Escenarios: `reparto-de-montos` › Un error de fórmula
  compartido no pasa. Lecciones: L-013, L-019, L-035.

## 3. Umbral de saldos chicos (R30, design D8), antes del grupo 5

- [ ] 3.1 **El umbral en `parametros.yaml`.** Sección `cuenta_corriente.umbral_saldo_chico: "500.00"`
  y su validación. Tests en el lector: el archivo del repositorio devuelve 500.00; el umbral faltante,
  vacío, en blanco, `"-0.01"`, con tres decimales y como número YAML falla nombrando
  `cuenta_corriente.umbral_saldo_chico` sin repetir el valor; `"0.00"` se acepta. RED: con el campo
  declarado y opcional, el archivo sin umbral pasa y falla la aserción de "falta". Escenarios:
  `parametros-del-sistema` › El archivo del repositorio es válido y tiene los defaults; › Umbral de
  saldos chicos inválido; › Umbral en cero. Lecciones: L-002, L-007, L-008.
- [ ] 3.2 **Migración `0021`: la columna, sus versiones viejas y su bajada.** Tests de integración
  contra PostgreSQL real: subir sobre una base en `0020` con versiones cargadas deja cada una con
  "500.00" y ninguna otra columna cambia (comparación fila por fila); el trigger de `UPDATE` no se
  dispara al subir; después de subir no hay default en la columna (un `INSERT` sin umbral falla por
  `NOT NULL`); `CHECK` rechaza un negativo; `proptech_app` no puede `UPDATE` del umbral; bajar como
  dueño restaura el esquema exacto de `0020` y volver a subir funciona. Antes de cerrar: `rg` de todo
  `INSERT INTO configuracion_versionada` en el repo entero (backend, `infra/`, semillas) y ajustar los
  que la columna sin default rompe (L-023). RED: con `0021` vacía, falla la aserción de la columna.
  Escenarios: `configuracion-versionada` › Versiones anteriores a este cambio; › El umbral no se edita
  por SQL. Lecciones: L-023, L-018.
- [ ] 3.3 **El umbral en el dominio, la versión nueva y la API.** `ConfiguracionEdificio` con el
  campo opcional; `desde_parametros` lo toma del archivo; `crear_version_de_configuracion` hereda el de
  la versión inmediatamente anterior en vigencia o, si no hay, el de parámetros; lectura y API lo
  devuelven como texto; el cuerpo lo acepta opcional y rechaza `500` (número JSON), "-1.00", "1.001" y
  "abc" con 422 nombrando el campo. Web: regenerar los fixtures que salen de la API real y sumar el
  campo al tipo de la respuesta; `pnpm biome ci`, `pnpm tsc --noEmit` y `bash infra/ci/test-web.sh` en
  verde, ninguna pantalla cambia. RED: con el campo existiendo y el caso de uso ignorándolo, la versión
  nueva queda con 500 en vez de heredar 300. Escenarios: `configuracion-versionada` › Versión nueva sin
  umbral; › Primera versión de un edificio nuevo; › Umbral explícito; › Umbral inválido. Lecciones:
  L-027 (la API falsa acepta el campo sólo como lo acepta la real), L-009.

## 4. Auditoría de los cambios del padrón (design D9)

- [ ] 4.1 **Vocabulario: migración `0022` y `EventoDelPadron`.** Los cinco eventos al vocabulario de
  `accion_de_auditoria` y al enum; `registrar()` los acepta con el detalle `{complejo_id, campos}`.
  Tests: la base acepta cada evento nuevo y rechaza uno inventado; el detalle con una clave extra o con
  un valor (por ejemplo `coeficiente_nuevo`) se rechaza antes de escribir, sin repetir el valor; bajar
  `0022` restaura el vocabulario de `0021` y no baja si un evento ya se usó. RED: con el enum
  existiendo y `0022` vacía, la base rechaza `editar_unidad` y falla la aserción de aceptación.
  Escenarios: `auditoria-de-acciones` › Acción fuera de la lista; › Clave no permitida en el detalle.
  Lecciones: L-007, L-034.
- [ ] 4.2 **Los cinco casos de uso auditan en su transacción.** `editar_unidad`, `editar_grupo`,
  `fijar_unidades`, `editar_categoria` y `reordenar_categorias` reciben `identidad` y `request_id`, la
  API se los pasa, y registran su evento sólo si algo cambió. Tests de integración contra PostgreSQL
  real: cambiar el coeficiente deja `editar_unidad` con `campos: ["coeficiente"]` y sin los valores;
  fijar unidades deja `fijar_unidades`; un identificador repetido no deja fila y la unidad sigue igual;
  los cinco una vez cada uno dejan cinco filas con cinco eventos distintos; la suite de "una acción por
  caso de uso" sigue en verde. RED: con los parámetros nuevos recibidos y sin llamar a `registrar()`,
  falla la aserción de la fila. Mutante extra: registrar fuera de la transacción (después del commit)
  hace que el caso que falla deje fila (L-019). Escenarios: `auditoria-de-acciones` › Cambiar el
  coeficiente de una unidad; › Fijar las unidades de un grupo; › El cambio que falla no deja
  auditoría; › Cada caso de uso con su evento; › Dos casos de uso con la misma acción. Lecciones:
  L-019, L-034.

## 5. Dueño de las tablas de sólo agregar (design D1 a D3), después del grupo 3

- [ ] 5.1 **El rol de arranque es dueño de `configuracion_versionada`.** Borrar el
  `xfail(strict=True)` de `test_dueno_de_tablas_solo_agregar.py`: RED, el caso
  `configuracion_versionada` da rojo en su aserción (el migrador puede `NO FORCE`). Generalizar
  `_TABLA_EXCLUIDA_DE_LA_REASIGNACION` a conjunto y transferir en `despues()` la tabla y las funciones
  de sus triggers; GREEN. Tests nuevos: volumen del 3a (tabla del migrador, `0021` pendiente) migra y
  termina del rol de arranque; con la tabla ya del rol de arranque, una migración de prueba con un
  `ALTER TABLE` falla con `must be owner` sin quedar a medias; bajar `0021` como migrador falla y, con
  la tabla devuelta por el rol de arranque, baja y vuelve a subir sin perder versiones (patrón de
  `test_auditoria_tabla.py:1052`). Adaptar los tests que bajan migraciones después de `despues()`.
  Escenarios: `aislamiento-por-administracion` › El migrador no es dueño de una tabla de sólo agregar;
  › Volumen del 3a, donde el migrador era dueño; › Una migración futura sobre una tabla protegida;
  › Bajar la migración que agrega el umbral; › Arranque repetido. Lecciones: L-036, L-035.
- [ ] 5.2 **`despues()` verifica la protección por el efecto en cada tabla.** Generalizar la
  verificación de `auditoria` a toda tabla del conjunto (design D2): RLS y `FORCE`, triggers y sus
  funciones, `UPDATE` y `DELETE` reales con el SQLSTATE y el texto de **esa** tabla, `TRUNCATE`
  ejecutado donde no hay FK entrante y por catálogo donde sí (dicho en el docstring), filas padre
  armadas en el `SAVEPOINT` cuando la tabla está vacía. Tests, cada uno con su mutante sobre la base
  de prueba antes de correr `despues()`: trigger de `UPDATE` deshabilitado; función reemplazada por una
  que devuelve la fila; un `DELETE` frenado por otro error; tabla vacía (la verificación igual prueba
  el bloqueo); los cuatro rojos nombran la tabla y no confirman ningún cambio de dueño. RED: con la
  verificación generalizada devolviendo "sin faltantes", el trigger deshabilitado pasa. Escenarios:
  `aislamiento-por-administracion` › Trigger deshabilitado; › Función de bloqueo reemplazada por una
  que no hace nada; › Otro error frena el intento. Lecciones: L-018, L-022, L-034.
- [ ] 5.3 **Los procesos no arrancan si una tabla protegida tiene otro dueño.**
  `verificar_tablas_de_solo_agregar(engine)` en `base_de_datos.py`, llamada en la API, el worker,
  `alta_inicial` y `ejemplo` junto al chequeo de rol que ya existe. Tests: con
  `configuracion_versionada` del migrador, la API no arranca y el log nombra la tabla y el motivo sin
  ningún valor; con una tabla del conjunto inexistente, tampoco; con todo en orden arranca; el conjunto
  comparado es exactamente `auditoria` más `_TABLAS_DE_SOLO_AGREGAR` (mutante: sacar una tabla del
  conjunto del chequeo y ver rojo). Revisar los tests que levantan la app sin migrar. RED: con la
  función existiendo y sin consultar el catálogo, la API arranca con la tabla del migrador.
  Escenarios: `aislamiento-por-administracion` › Una tabla quedó del migrador; › Todo en orden.
  Lecciones: L-016, L-018, L-022, L-007.

## 6. Deuda D-053 (design D10)

- [ ] 6.1 **`except TypeError` muerto y ceros de más.** Tests primero: en `leer_parametros`, raíz que
  no es un mapa y claves que no son texto fallan con `ParametrosInvalidos` cortados por `cargar_yaml`,
  sin traceback; el mismo par en el lector de la semilla (L-009); `Dinero("1.0000")` y
  `Dinero("1.000")` fallan. Después se borra el `except TypeError` y los tests siguen en verde. RED:
  mutar en una copia (L-013) `cargar_yaml` para que deje pasar una raíz lista y ver que el test cae en
  su aserción (no en un `TypeError` sin atrapar que el test confunda con el error esperado). Escenarios:
  `representacion-de-montos` › Ceros de más. Lecciones: L-009, L-013, L-007.

## 7. Cierre

- [ ] 7.1 **Corrida de cierre después de la última vuelta.** Sobre el último commit del change, con el
  SHA anotado: `bash infra/ci/test-backend.sh` completo, `bash infra/ci/humo.sh`, la suite de web, y el
  número de tests comparado con el de `main` en `de3c710` (si bajó, explicar). Push de la rama y el CI
  completo de GitHub Actions leído en verde antes de decir "listo". Si el código cambia después, la
  corrida queda vencida y se repite. Lecciones: L-003, L-010, L-031, L-037.

## Workflow follow-up

- Romper y auditar (ciclo completo, `14_forma_de_trabajo.md`); rompedor y auditor de una familia de
  modelo distinta del constructor (L-025).
- Archivar con el OK del auditor y actualizar `knowledge-base/` según "Knowledge Base Impact" de
  `proposal.md` (decisiones nuevas sólo se agregan).
