# Exploración: cimientos antes del change 4 (22/10/2026)

Auditoría de cimientos completa sobre el repositorio, convocada por Juani antes de proponer el
change 4 `motor-de-cuenta-corriente` (el primero que toca plata de verdad). Nueve informes, HEAD
`55e18a0`: `01-arquitecto.md`, `02-backend-seguridad.md`, `03-dba.md`, `04-devops.md`, `05-qa.md`,
`06-frontend.md`, `07-deuda-y-kb.md`, `08-auditor.md` (consolidado) y `09-cotejo-permisos-y-rr.md`,
todos en `.git/informes-cimientos/`. Esta nota organiza sus hallazgos para que se resuelvan en el
change 4 y en los posteriores, como pidió Juani el 22/10/2026.

## Veredicto

**Los cimientos aguantan.** Ningún informe encontró un defecto que tape al 4; lo que encontraron es
una lista de decisiones que su propose tiene que traer resueltas, y seis preguntas de negocio que
sólo responden Juani y Alberto.

Lo que sostiene el veredicto, con evidencia propia de cada rol (no repetida acá; está en cada
informe): aislamiento multi-tenant con RLS forzada e indexada, token RS256 validado a fondo,
secretos nunca en texto plano, montos siempre `NUMERIC`/`Decimal` sin un sólo `float`, downgrades de
migración que restauran el esquema exacto, foco visible y sin scroll horizontal en las nueve
pantallas construidas, CSP estricta sin `unsafe-inline`.

**Verificación con mutantes (QA, 05-qa.md)**: 18 mutantes manuales sobre producción, en un worktree
propio. 15 murieron por la aserción correcta (coeficientes, dinero, token, permisos, RLS,
configuración, consejo, invitaciones, formato de porcentaje en el frontend). Los 3 sobrevivientes
son justamente los tres hallazgos de QA de este informe (QA-1, QA-2, QA-3, abajo). Ningún mutante
murió por un 401 ni por un error de import (lección L-034: eso no prueba lo que dice probar).

## Lo arreglado en commits propios (22/10/2026)

Cuatro de los once bloqueantes que listó el auditor (08-auditor.md) ya se resolvieron, verificados
con `git log`:

- **#6 — tenant por transacción sin test que diera rojo (D-02/N-c)**: `7555b59` agrega
  `test_tenant_por_transaccion.py`, un test que liga dos sesiones a la misma `Connection` abierta a
  mano (sin pasar por el pool) para que el `SET LOCAL` de D4 sólo dé cero filas si es realmente local
  a la transacción; antes, el reset de checkin (R7) tapaba cualquier mutante a `SET` de sesión.
  `d63a409` cierra la fila de N-c en `knowledge-base/12_fichas_de_changes.md`.
- **#7 — correr `test_catalogo_rls.py` y que controle también el dueño de la tabla (DBA-1, D-22)**:
  `8b8ee52` agrega `test_dueno_de_tablas_solo_agregar.py`: el discriminante real es
  `NO FORCE ROW LEVEL SECURITY` (sólo lo puede el dueño), no `DISABLE TRIGGER ALL` (los triggers
  internos de una FK exigen superusuario sin importar el dueño, y por eso fallan igual para
  `auditoria` que para `configuracion_versionada`, escondiendo la diferencia real — ver L-036).
  `437466b` suma `auditoria` como caso **verde** del mismo test: el primer commit sólo tenía
  `configuracion_versionada` en `xfail(strict=True)`, sin un sólo caso que pasara (ver L-035). La
  decisión de **quién** es el dueño real de las tablas de sólo agregar futuras (opciones a/b/c del
  informe 03) sigue abierta para el propose del 4 (ver DBA-1 más abajo).
- **#8 — cotejo de las 144 celdas de permisos + revisión independiente de RR-1 a RR-4 (D-01)**:
  resuelto por el informe `09-cotejo-permisos-y-rr.md` (el rol de QA, independiente de quien escribió
  el 2.2a): las 144 celdas de `permisos.py` contra la matriz de D-106 no tienen diferencias, y las
  cuatro RR (409 al repetir perfil, auditoría con persona destinataria, consejo único, texto del 403)
  dan rojo con su mutante inverso. Sin commit propio: es una verificación, no un cambio de código.
- **#9 — la API falsa de los e2e acepta cualquier cuerpo de escritura (QA-1, L-027)**: `1a979dd`
  hace que `api-falsa.ts` valide Content-Type antes que cualquier escenario, y declare método y
  campos por ruta como la API real (`extra="forbid"`); los 6 casos que antes daban 200 ahora dan 422
  o 405 como la real.

**CI**: `ad5bc90` (falsos positivos de gitleaks, `rg` ausente del runner, shellcheck de `web/e2e`,
timeout del backend) y `55e18a0` (el test de timeouts acompaña el nuevo límite de 30 minutos). `main`
verde en el run 39804571438; el job backend tardó 19m52s contra el límite de 30. Dos rojos de `main`
en un mismo día por no esperar el CI completo antes de decir "listo" — ver L-037.

## Decisiones de diseño que el propose del 4 tiene que traer resueltas

Ningún código se escribe para esto ahora: es la lista que el *design* del change 4 tiene que decidir
y registrar (con la opción descartada y su porqué) antes de que el constructor toque el libro de
movimientos.

| id de origen | qué hay que decidir o hacer | criterio de terminado observable |
|---|---|---|
| **DBA-1** (03-dba.md) | Dueño real de las tablas de sólo agregar futuras (el libro de movimientos). El test ya existe (`test_dueno_de_tablas_solo_agregar.py`) con `configuracion_versionada` en `xfail(strict=True)`; falta elegir entre: (a) dueño el rol de arranque, como `auditoria`, generalizando `_TABLA_EXCLUIDA_DE_LA_REASIGNACION` a un conjunto; (b) aceptar que el migrador sea dueño y escribirlo como decisión; (c) un rol de propiedad aparte. | El design registra la opción elegida como decisión nueva (con la descartada y el costo de revertir); el `xfail` de `configuracion_versionada` se resuelve explícitamente (pasa a xpass documentado o se excluye con motivo), y las tablas nuevas del 4 (`movimiento`, `obligacion`, `libro`) nacen con el dueño correcto, cubiertas por el mismo test sin tocarlo. |
| **ARQ-1** (01-arquitecto.md) | Dueño de la entidad `emision` entre `cuenta_corriente` y `liquidacion`: D-086 la crea en el 4 y la completa en el 7, y ninguna decisión fija la dirección de la dependencia. Opción (a) `emision` vive en `cuenta_corriente` y `liquidacion` depende de ella; opción (b) vive en `liquidacion` y el libro la lee por un puerto. | El design elige una opción, la registra con la descartada y el costo de revertir después del 7 (migrar la FK de cada movimiento de un libro append-only), y existe un test de frontera `cuenta_corriente↔liquidacion` que falla si se viola. |
| **ARQ-2** (01-arquitecto.md) | `test_fronteras_de_modulos.py` hoy sólo prueba que `compartido` es hoja. Faltan tres reglas: (a) ningún ciclo entre módulos de dominio en general; (b) "los módulos se hablan sólo por `aplicacion`" (CLAUDE.md:119), que hoy no se cumple ni se prueba (`complejos` ya importa `acceso.dominio`); (c) que `dominio/` no importe infraestructura de `compartido` (base de datos, cola). | Las tres reglas están sumadas al test antes de escribir el libro de movimientos, y el test falla de verdad ante cada una (se verifica con un mutante). |
| **Idempotencia de punta a punta** (BKS-1, FE-2, DBA-6, OPS-9) | No hay `Idempotency-Key` HTTP (`ejecutar_una_vez` sólo la usa el worker); ningún formulario de escritura la manda; 9 de 11 pantallas no deshabilitan su botón mientras la acción está pendiente; el libro necesita una clave natural por movimiento, aislada por tenant, para no duplicar un pago con un doble clic. | Un POST repetido con la misma clave (HTTP) o el mismo dato natural (el libro) no duplica el efecto, probado contra PostgreSQL real; el botón de cada formulario de montos queda deshabilitado y dice "Guardando…" mientras está pendiente. |
| **Redondeo y precisión del reparto** (DBA-4, QA-4, D-09/P10, D-14/P42) | Sin modo de redondeo fijado (P10, grupo B); sin precisión intermedia decidida para el reparto; sin `hypothesis` en el proyecto; el único test "de propiedades" de coeficientes recalcula con la misma fórmula que producción (no es un oráculo independiente: un mutante en el operador lo hace fallar igual, pero no detecta un error de fórmula compartido). | `hypothesis` corre sobre el reparto por mayor resto con las invariantes: la suma repartida da exacto el total al centavo, ninguna unidad recibe más de un centavo de diferencia, los empates son deterministas; el oráculo del test no reutiliza la fórmula de producción. |
| **Commit-y-encolar con outbox y reproceso** (BKS-2, OPS-9) | `personal.py:108` hace `commit()` y recién ahí encola; con Redis caído, la invitación queda `pendiente` sin nada que la reintente. El libro de movimientos va a tener el mismo patrón (registrar y avisar) y el worker financiero (cierre mensual, intereses) no tiene cron ni dueño de reproceso. | Existe un estado por emisión/tarea y una forma de reprocesar documentada (outbox o barredor), y una alerta cuando una tarea queda `tarea_agotada` (hoy el evento existe en `reintentos.py:107` pero nadie la mira, OPS-3/OPS-9). |
| **Errores de formulario asociados al campo + `pesos()` y su parser** (FE-1, FE-3) | Los selects de rol, alcance, tipo, vínculo y método no tienen `id="campo-x"` ni `aria-invalid`: el enlace del resumen de error apunta a un id inexistente. No existe una función única de montos (`pesos()`) ni su parser de entrada; `decimalParaApi("1.234,50")` hoy pasa sin tocar y la API daría 422. | Todo campo nuevo de monto o selección queda enlazado a su error por id/`aria-invalid` (no sólo por posición); existe `pesos()` y un parser de entrada únicos, reusados por toda pantalla nueva con plata, antes de construir la primera. |
| **Contrato de error uniforme** (BKS-3) | Cumplido en los tests pero no declarado: ninguna ruta usa `responses=`, el OpenAPI sólo documenta 200 y 422; las formas de error no son uniformes (403 con `{"detail":"sin_permiso"}` en un lado y `{"detail":{"detalle","permiso_faltante"}}` en otro; 500 con `{"error","request_id"}`; 401 sin `WWW-Authenticate`). | Toda ruta nueva del 4 declara `responses=` con una forma de error única para sus caminos de falla (no sólo el feliz), y el OpenAPI generado la refleja. |
| **Patrón puertos/adaptadores del libro** (ARQ-4) | D-040/CLAUDE.md/08 dicen `puertos.py` + `adaptadores/` por módulo; `complejos` no tiene ninguno (SQL con `text()` sobre `Session` directo) y no hay decisión que registre esa excepción. | El design del 4 dice explícitamente qué patrón usa el módulo del libro: puertos y adaptadores como pide D-040, o la decisión que lo reemplaza con su porqué. |
| **Auditoría del coeficiente** (BKS-5, D-016) | `editar_unidad` (incluye el coeficiente), `editar_grupo`, `fijar_unidades`, `editar_categoria` y `reordenar_categorias` no llaman a `registrar()` ni reciben identidad: cumplen D-016 tal como está escrita, pero el coeficiente decide el prorrateo de todo el edificio y hoy nadie sabe quién lo cambió. | Esas cinco operaciones quedan en `accion_de_auditoria`, o el design explica por escrito por qué D-016 no las alcanza y queda como decisión, no como olvido. |
| **Contrato de la API falsa contra el OpenAPI real** (seguimiento de QA-1/L-027) | `1a979dd` corrigió los 6 casos conocidos; cada formulario **nuevo** de montos que construya el 4 necesita su propio caso en `api-falsa.ts` validado contra lo que la API real rechaza (422/405), no sólo Content-Type. | Cada ruta de escritura nueva del 4 tiene un caso en `api-falsa.ts` que falla si la falsa acepta algo que la real (según su OpenAPI) rechazaría. |
| **El canario no repita la suite entera** (OPS-2) | `infra/ci/canario.sh:49` llama a `test-backend.sh` completo: 9 a 15 minutos por corrida, cancelado una vez a los 20. El 4 es el change más grande del roadmap y va a necesitar corridas de canario frecuentes. | `test-backend.sh` acepta qué test(s) correr como argumento, y el canario corre sólo el que falló, no la suite completa. |

## Preguntas de negocio para Juani y Alberto, antes del propose

**Actualizado 22/10/2026**: Juani respondió cinco de las seis preguntas en conversación con el
orquestador; quedan registradas en D-109 (`09_decisiones_y_supuestos.md`). P42 sigue abierta y ya no
bloquea el propose (se valida antes del piloto, 15). Dos sub-preguntas quedan para Alberto (marcadas
abajo).

| id | la pregunta, en castellano llano | por qué importa para la plata | respuesta (D-109, 22/10/2026) |
|---|---|---|---|
| **P10** | ¿Redondeás al centavo "a lo bancario" (0,125 → 0,12) o "medio hacia arriba" (0,125 → 0,13)? | Decide a qué unidad le toca el centavo sobrante en **cada** reparto, todos los meses; sin esto no hay invariante que probar. | **Resuelta**: medio hacia arriba, como `REDONDEAR` de Excel. Queda para Alberto a qué unidad va el centavo sobrante en su planilla. |
| **P11** | Cuando una unidad cambia de titular a mitad de período (venta), ¿quién responde la expensa de ese período y la deuda anterior: quien vendía o quien compra? | Define a quién se le factura y a quién se le reclama la mora justo en el momento en que más se discute una expensa. | **Resuelta**: lo decide el administrador por cada cambio, con dos opciones configurables y sus defaults (R32): expensa del mes a la unidad entera (o prorrateo por días) y deuda previa al comprador (o a nombre del vendedor, con cuenta de persona). Deuda previa al comprador es SUPUESTO sin verificar con abogado (SU-02). |
| **P21** | ¿A partir de qué monto un gasto se marca "atípico" para revisión (R23), y por debajo de qué saldo un deudor chico no genera interés ni se persigue (R30)? | Fija el umbral entre "vale la pena revisar/cobrar" y "ruido"; sin número, R23 y R30 no tienen con qué comparar. | **Resuelta**: atípico es más del doble o menos de la mitad del promedio de 6 períodos del proveedor (sin historial, no se marca); saldo chico es $500. Ambos configurables por edificio. |
| **P31** | Si el saldo vencido de una unidad es sólo interés (el capital ya está pagado), ¿cuenta igual como "moroso crítico"? | De eso depende si se bloquean beneficios a alguien que, en los hechos, ya pagó el capital. | **Resuelta**: no cuenta como moroso crítico; etiqueta propia "deuda de intereses" con aviso más suave. Un saldo bajo el umbral de R30 tampoco cuenta como vencido. |
| **P34** | El interés de una emisión, ¿corre hasta la fecha de emisión, hasta el cierre del período o hasta el vencimiento siguiente? | Cambia el monto exacto que ve el vecino en cada expensa con mora; es el cálculo más replicado del sistema. | **Resuelta**: hasta el cierre del período. Queda para Alberto confirmar que su Excel corta igual. |
| **P42** | ¿Conseguimos a un contador o administrador real de Mendoza para validar los valores por defecto (tasa 3% mensual, días de gracia, redondeo)? | El 4 arranca codeando con esos defaults; migrar liquidaciones ya emitidas si están mal es mucho más caro que preguntar antes. | **Sigue abierta**: sin nombre todavía. No bloquea construir el 4; se valida antes del piloto (15). |

## Lo que va a otros changes (no bloquea el propose del 4)

| id de origen | qué es | destino | por qué ese destino |
|---|---|---|---|
| OPS-3 + OPS-7 | Ningún modo de falla tiene métrica ni alerta (respaldo fallido, tarea agotada); deploy a producción sin documentar (sin procedimiento de VPS ni rollback de imagen ensayado en producción real) | **15** (piloto) | Son huecos de producción; el proyecto no tiene producción todavía (SUPUESTO del propio informe 04) |
| OPS-4 | `respaldar.sh` descarta el `stderr` de `pg_dump`; faltan campos propios en los logs (código de salida, nombre de tarea) | **15** | Mismo patrón que el resto de la deuda operacional de backups, ya con dueño 15 |
| OPS-5 | El `mkdir -p infra/datos-respaldos` del README falla en silencio si se saltea: Docker crea la carpeta como `root` | **15** | Documentar o automatizar el `mkdir`; es DevOps de despliegue, no del dominio |
| OPS-6 | `humo.sh` y `ensayo-roles.sh` usan `-p proptech` con `down -v`: borran los volúmenes del stack manual si se corren ahí por error | **15** | Mismo ciclo de endurecimiento de scripts de operación |
| OPS-8 | Las imágenes de ejecución van sólo por tag, no por digest (las de CI sí) | **15** | Ya existe la fila gemela "imágenes por digest" en la deuda del 13/10 con dueño 15 |
| DBA-2 | `grupos.py:90` escanea `grupo_unidad` completo (Seq Scan, 62k filas descartadas sobre 125k sintéticas); falta un índice con prefijo `(administracion_id, complejo_id)`; 8 FK más sin índice | **7** (`liquidacion-y-emision`) | Es la consulta de la liquidación mensual; el propio informe 03 la ubica ahí |
| FE-4 a FE-8 + hallazgos de pantalla (menú de Personal armado a mano, botón Quitar sobre el único super admin, auto-envío del selector de administración, `ClerkProvider` sin `signInUrl`/`signUpUrl`, `/` sin armazón) | Deuda visual y de affordance de pantallas ya construidas (2b, 3b) | **Sin change de pulido hoy**: se anota para cuando se toque `personal/`, `elegir-administracion/` o `layout.tsx` | No hay un change de "pulido de UI" en el roadmap actual; forzar uno nuevo para esto es más caro que esperar al próximo cambio que abra esos archivos |
| QA-2 | `validar_rango_recargo` (configuración de intereses) sin un test que lo cubra; un mutante lo deja verde en 67 tests | **Cuando se toque** `configuracion.py` (3a, archivado) | No es del dominio del 4; es deuda de tests de un change ya cerrado |
| QA-3 | El vencimiento de la fila de invitación nunca se prueba separado del vencimiento del sobre (la fixture los iguala) | **Cuando se toque** `invitaciones.py` (2b, archivado) | Mismo patrón: deuda de cobertura de un change cerrado |
| QA-5 | El Clerk falso de los tests promete más de lo que hace (su docstring dice que valida la forma del cuerpo; no mira ruta ni cuerpo) | **Cuando se toque** el Clerk falso o los tests de invitaciones | Infraestructura de test, no dominio de negocio |
| QA-6 | `test_compose.py:412` escribe en la carpeta real `infra/datos-respaldos` del repositorio | **DevOps, cuando se toque** `test_compose.py` | Mismo patrón que L-033 (un test no debe asumir ni ensuciar una carpeta real) |
| RR-2-rev-b | `quitar_asignacion` guarda `detalle={}` y borra la fila: no se puede reconstruir qué perfil/alcance se quitó | **Cuando se toque** `usuarios.py` | Llegó con el 2b (E14); no es bloqueante, es mejora de auditoría |
| RR-3-rev-b | Falta un test: invitar a alguien ya consejo del mismo edificio con rol consejo tiene que dar 409 en el campo "rol"; el mutante que lo rompe sobrevive hoy | **Cuando se toque** `personal/invitaciones` | Deuda de cobertura puntual, no de diseño |
| PER-1 (redacción) | D-106 dice que el super admin puede "Todo"; el código y su test le niegan `informar_pago` a propósito (sólo propietario e inquilino informan pagos) | **Resuelto hoy**, ver la aclaración agregada a D-106 en `09_decisiones_y_supuestos.md` | Es exactamente el encargo del punto 4 de esta tarea |
| PER-2 (redacción) | Docstrings de `permisos.py` y `test_permisos.py` todavía citan "de D-096", reemplazada por D-106 | **Cuando se toque** `permisos.py`/`test_permisos.py` | Limpieza de comentario, sin efecto en el comportamiento |
| KB: 8 módulos en presente | `knowledge-base/02_descripcion_general.md` y `CLAUDE.md` describen los 8 módulos de dominio de `proptech_core` en tiempo presente; hoy sólo existen `complejos/`, `acceso/` y `compartido/` (confirmado con `fdfind -d1 -t d . backend/src/proptech_core`). Los otros 5 están planificados (C-07 a C-12 de `CHANGES.md`, todos `[ ]`) | **Corregir cuando se reescriban esos documentos** (02 y CLAUDE.md "se reescriben" según su propia tabla; no se tocan en esta auditoría, que es sólo documentación de precondiciones) | El resto de cada documento sí distingue construido de planeado; sólo esa tabla puntual induce a error |

## Lo que el auditor marcó como ya resuelto o ya conocido (no entra en ninguna lista anterior)

- **ARQ-3** (complejos escribe `asignacion_rol` de `acceso` directamente, violación de frontera) ya
  tiene una decisión que lo justifica: `design.md:80-92` del 2.2a archivado (D-29 del informe 07,
  "decidido no arreglar ahora"). No es un hallazgo nuevo del 4; queda como está, documentado.
- **BKS-6** (`verificar_token_de_sesion` acepta un `str` donde se declaró `Collection[str]`, y la
  comparación pasaría a subcadena) bajó de nota a verificado-sin-riesgo: la configuración pública
  siempre entrega una tupla (`test_configuracion_clerk.py`, 53 passed). Queda como trampa para quien
  llame a esa función con otro tipo en el futuro, no como deuda del 4.

## Lo que nadie miró (declarado por los propios informes)

Para que la cobertura de esta auditoría no se lea como más completa de lo que fue: nadie abrió
`acceso/aplicacion/auditoria.py` ni `autorizacion.py` más allá de `rg` dirigido, ni
`proptech_worker/tareas.py`; nadie corrió Playwright, el humo completo ni las suites enteras (QA);
nadie levantó el stack real (DevOps); la Tarea B del informe 07 (fechas de la KB, "24 afirmaciones
verdaderas") se reportó sin el comando que la respalda — una afirmación con etiqueta de evidencia,
no evidencia (observación del propio auditor en 08-auditor.md).

## Siguiente paso

El grupo de preguntas de negocio quedó respondido por D-109 (22/10/2026): P10, P11, P21, P31 y P34.
P42 sigue abierta, sin bloquear el propose (se valida antes del piloto, 15), igual que las dos
sub-preguntas que quedaron para Alberto (P10 y P34, ver tabla arriba). El propose del change 4 puede
arrancar; el design del 4 trae resuelta la lista de decisiones de diseño de arriba, con cada opción
descartada y su costo de reversión por escrito, como pide `14_forma_de_trabajo.md`.
