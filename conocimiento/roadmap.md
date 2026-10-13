# Roadmap de ejecución del MVP

El plan cambio por cambio, del primero al último. Cada ficha es **la entrada del `/opsx:propose`**
de ese cambio: el proponente parte de acá y de los archivos que la ficha cita. **Se reescribe**
cuando cambia el plan; el porqué va a `decisiones.md` (D-045, D-047, D-049).

El ciclo de cada cambio está en `forma-de-trabajo.md`: proponer, construir, romper, auditar y
archivar con commit y push. Un cambio arranca cuando el anterior está archivado.

## Resumen

| # | Cambio | Hito | Depende de | Explore propio | Crítico | Tamaño |
|---|---|---|---|---|---|---|
| 1a | `infraestructura-base` ✅ | M1 | ninguno | no | no | mediano |
| 1b | `arranque-del-sistema` ✅ | M1 | 1a | no | no | mediano |
| 1c | `cola-logs-y-respaldos` | M1 | 1b | no | no | mediano (puede partirse en 1d) |
| 2 | `acceso-y-aislamiento` | M1 | 1c | **sí** | **sí** | grande |
| 3 | `configuracion-del-edificio` | M1 | 2 | no | no | mediano |
| 4 | `motor-de-cuenta-corriente` | M1 | 2 | **sí** | **sí** | grande |
| 5 | `importacion-desde-excel` | M1 | 3, 4 | no | no | mediano |
| 6 | `gastos-y-cargos` | M1 | 3, 4 | no | no | mediano |
| 7 | `liquidacion-y-emision` | M1 | 5, 6 | **sí** | **sí** | grande |
| 8 | `pagos-informados` | M2 | 7 | no | **sí** | mediano |
| 9 | `extracto-bancario` | M2 | 8 | no | no | chico |
| 10 | `morosidad` | M2 | 8 | no | no | chico |
| 11 | `portal-del-vecino` | M2 | 10 | no | no | mediano |
| 12 | `vista-del-consejo` | M2 | 11 | no | no | chico |
| 13 | `avisos-por-email` | M2 | 8 | no | no | chico |
| 14 | `lectura-de-facturas` | M3 | 6 | no | no | mediano |
| 15 | `piloto-en-paralelo` | M3 | todos + datos del piloto | no | no | mediano |

**Crítico**: Juani aprueba la propuesta antes de que se codee. **Explore propio**: se corre un
`/opsx:explore` del cambio antes del propose.

**Camino al test de M1** (reproducir la última liquidación del piloto al centavo):

```
Código:  1a → 1b → 1c → 2 → 3 → 4 → 5 → 6 → 7 ──┐
                                            ├──► TEST M1
Datos:   pedirle a Alberto los datos del piloto (P1), desde ya ──┘
```

Los datos del piloto no frenan el código, pero sin ellos M1 no se puede dar por cumplido.

---

## M1 · Liquida

### 1a · `infraestructura-base`

- **Objetivo**: que el proyecto arranque entero con un comando y que los tests corran solos en cada push.
- **Decisiones**: D-020, D-036, D-038, D-040, D-043, D-046.
- **Entra**: estructura de carpetas de D-040 (`config/`, `web/`, `backend/` con `proptech_core`,
  `proptech_api` y `proptech_worker`, `infra/`); Docker Compose con PostgreSQL, Caddy, la API y la
  web; Alembic con una primera migración vacía; esqueleto de FastAPI con un endpoint de salud;
  esqueleto de Next.js; CI que corre los tests y el linter; `.env.example` sin secretos; sólo Caddy
  con puertos públicos.
- **No entra**: Redis, worker, parámetros, datos semilla y logs (1b); login (2).
- **Habilita**: 1b.
- **Decidir en el design**: versiones fijadas de cada imagen; herramienta de lint y formato de
  Python y TypeScript; cómo corre PostgreSQL real en el CI para los tests de integración.
- **Que intente romper el rompedor**: levantar desde un clon limpio siguiendo sólo el README; que la
  base o algún servicio interno quede expuesto a Internet; que el CI pase con un test roto; secretos
  en el repo o en las imágenes.
- **Terminado cuando**: `docker compose up` levanta todo desde un clon limpio; el endpoint de salud
  responde a través de Caddy; el CI está en verde y falla a propósito con un test roto.

### 1b · `arranque-del-sistema` ✅

- **Objetivo**: las piezas transversales que todos los cambios usan (re-alcanzado por D-052).
- **Decisiones**: D-042, D-046, D-052, D-053.
- **Entró**: configuración con las variables de Redis y el archivo de parámetros conectadas en Compose;
  migraciones que dependen sólo de PostgreSQL; tipo `Dinero` sobre `Decimal`; `config/parametros.yaml`
  con su lector validado; el edificio de ejemplo como archivo validado y su comando de verificación.
- **Pasó a 1c**: Redis y el worker, logs y número de seguimiento, respaldos, `/salud-web`, humo y README.
- **Habilita**: 1c.

### 1c · `cola-logs-y-respaldos`

- **Objetivo**: la cola de trabajos, los logs con número de seguimiento y los respaldos, separados del 1b (D-052).
- **Entra**: lo que el 1b tenía en sus secciones 6 a 12 (ver `openspec/changes/cola-logs-y-respaldos/`).
- **Depende de**: 1b. **Habilita**: 2.
- **Terminado cuando**: lo que diga su propuesta; si supera unas 20 tareas, se parte en 1d.

### 2 · `acceso-y-aislamiento` · crítico · explore propio

- **Objetivo**: que cada persona entre y vea sólo lo suyo, aunque el código tenga un error.
- **Historias**: HU-V1 (entrada del vecino). **Reglas**: R08 (auditoría), R10.
- **Decisiones**: D-009, D-016, D-021, D-036, D-037, D-039.
- **Entra**: login del personal y del vecino; los cuatro roles (titular, colaborador, consejo,
  vecino); alcance por edificio; Row-Level Security con `SET LOCAL` y un rol de base sin
  privilegios; auditoría en la misma transacción; 404 fuera de alcance y 403 sin permiso;
  límite de pedidos en el login.
- **No entra**: la pantalla del portal (11) y la del consejo (12): acá sólo el acceso.
- **Depende de**: 1c. **Habilita**: 3, 4.
- **Decidir en el design** (y en su explore): **el método de login** (Clerk para el personal y enlace
  mágico para vecinos, según el documento de Alberto, o una alternativa sin costo por usuario,
  D-043); dónde vive cada uno de los tres controles; cómo fija el tenant el worker.
- **Que intente romper el rompedor**: ver un edificio de otra administración tipeando la URL o
  mandando otro `tenant_id`; consultar la base sin fijar el tenant; que un `SET` sin `LOCAL` contagie
  el tenant al pedido siguiente; un colaborador entrando a un edificio no asignado; un vecino
  abriendo pantallas del personal; fuerza bruta contra el login.
- **Terminado cuando**: hay tests contra PostgreSQL real que intentan cruzar administraciones y
  fallan cerrados; cada rol ve exactamente lo de D-037; la auditoría registra cada acción sensible.

### 3 · `configuracion-del-edificio`

- **Objetivo**: que el administrador cree un edificio y lo configure como dice su reglamento.
- **Historias**: HU-A1. **Reglas**: R01 (sólo la definición de grupos), R02 (desactivado), R03 (su
  configuración), R15 (porcentaje), R16 (categorías).
- **Decisiones**: D-010, D-013, D-029, D-030, D-031, D-041, D-042.
- **Entra**: edificios, unidades con su tipo (departamento, cochera, baulera, local) y coeficiente;
  grupos de reparto con sus unidades y método; categorías de gasto (crear, renombrar, ordenar,
  desactivar); configuración de intereses y fondo de reserva tomada de `parametros.yaml` al crear;
  **cargar en la base el edificio de ejemplo** de `config/semilla/edificio-ejemplo.yaml` (validado en 1b).
- **No entra**: carga masiva desde Excel (5); cálculos (4, 7).
- **Depende de**: 2. **Habilita**: 5, 6.
- **Decidir en el design**: cómo se guarda la configuración vigente en cada liquidación (historia);
  si el edificio piloto usa primer y segundo vencimiento con recargo escalonado (R26, pendiente de
  confirmar con Alberto, ProTecc G4, Q9) en vez del vencimiento único de R03.
- **Que intente romper el rompedor**: coeficientes de un grupo que no suman 1; una unidad repetida;
  borrar una categoría con gastos; cambiar la tasa y ver si toca algo ya emitido; editar la
  configuración de otro edificio.
- **Terminado cuando**: se cumplen los criterios de HU-A1; un edificio nuevo arranca con los valores
  de `parametros.yaml`; cambiar el archivo no altera edificios existentes.

### 4 · `motor-de-cuenta-corriente` · crítico · explore propio

- **Objetivo**: el corazón de la plata: que cada peso de deuda viva en un solo lugar y nunca se pierda un centavo.
- **Historias**: HU-A9 (correcciones). **Reglas**: R03, R04, R05, R06, R07, R08, R09 (el caso de uso
  de saldo inicial), R13 (orden de imputación por tipo).
- **Decisiones**: D-010, D-011, D-012, D-015, D-016, D-024, D-046, D-068.
- **Entra**: libro de movimientos de sólo agregar, sin campo saldo; obligaciones, pagos e
  imputaciones; intereses simples calculados al registrarse; reparto por **mayor resto** como función
  pública de `proptech_core` (la usa el cambio 6); correcciones con contra-asiento; dos fechas por
  pago (registro y valor); caso de uso de saldo inicial (con detalle por período o total único);
  bloqueo para pagos simultáneos de la misma unidad; umbral mínimo para saldos chicos de redondeo
  (R30, propuesta, ProTecc D3).
- **No entra**: la pantalla para confirmar pagos (8); la importación del Excel (5); la emisión (7).
- **Depende de**: 2. **Habilita**: 5, 6, 7.
- **Decidir en el design** (y en su explore): el modelo de tablas del libro; cómo se bloquea la
  cuenta durante una imputación; el desempate determinista del mayor resto.
- **Que intente romper el rompedor**: dos pagos simultáneos a la misma unidad; un pago parcial
  seguido de otro que completa; un pago mayor a la deuda; un pago con fecha valor anterior a una
  corrección; intereses sobre intereses; un reparto que pierde o gana un centavo; editar o borrar un
  movimiento por SQL directo.
- **Terminado cuando**: los tests mínimos de R03 a R09 y R13 pasan; hay pruebas de propiedades del
  mayor resto (la suma siempre da exacta); el test de concurrencia contra PostgreSQL real pasa; un
  intento de modificar un movimiento rebota.

### 5 · `importacion-desde-excel`

- **Objetivo**: cargar un edificio real desde su Excel sin tipear nada.
- **Historias**: HU-A2. **Reglas**: R09.
- **Decisiones**: D-015, D-029, D-068.
- **Entra**: plantilla de Excel (piso, departamento, tipo, propietario, contacto, coeficiente, saldo
  inicial); validación fila por fila con informe de errores; carga atómica (todo o nada); detección
  de reimportación; saldos en un **borrador** que no toca la cuenta corriente, comparado **unidad por
  unidad** contra el listado del administrador, con aceptación registrada de las diferencias y cierre
  del importador al confirmar (D-068); saldos iniciales usando el caso de uso del cambio 4.
- **No entra**: importar gastos o cargos (6).
- **Depende de**: 3, 4. **Habilita**: 7 y el test de M1.
- **Que intente romper el rompedor**: un archivo con columnas cambiadas de lugar, celdas vacías,
  números con coma y con punto, coeficientes que suman 0,9999; el mismo archivo subido dos veces; un
  archivo enorme; un archivo que no es Excel; dos errores de signo opuesto en dos unidades que dan el
  total correcto; importar de nuevo con el importador cerrado.
- **Terminado cuando**: se cumplen los criterios de HU-A2; un archivo con un solo error no carga
  nada y lo informa; la suma importada coincide con la del archivo; cada diferencia por unidad se
  muestra aunque el total coincida.

### 6 · `gastos-y-cargos`

- **Objetivo**: cargar los gastos del mes y los cargos de cada unidad, listos para liquidar.
- **Historias**: HU-A3 (carga manual, incluido el sueldo del encargado), HU-A3b. **Reglas**: R01
  (reparto de cada gasto en su grupo, usando el mayor resto del cambio 4), R13, R14, R16.
- **Decisiones**: D-013, D-024, D-025, D-026, D-028, D-041.
- **Entra**: proveedores; gastos en borrador y aprobados con categoría, grupo y tipo ordinario o
  extraordinario; sueldo del encargado como gasto; cargos particulares sueltos o importados desde
  Excel; aprobación; nota de crédito asociada a la factura que corrige, con su monto topeado al de
  esa factura (R22, ProTecc H1).
- **No entra**: la lectura de facturas por QR e IA (14): acá la carga es manual.
- **Depende de**: 3, 4. **Habilita**: 7, 14.
- **Que intente romper el rompedor**: un gasto sin categoría que se aprueba; un cargo particular que
  termina repartido entre todos; un gasto de otro edificio; un importe con tres decimales; aprobar
  dos veces el mismo gasto; una nota de crédito que supera el monto de su factura; una nota de
  crédito sin factura asociada.
- **Terminado cuando**: se cumplen los criterios de HU-A3 (manual) y HU-A3b; un gasto en borrador no
  aparece en ningún cálculo.

### 7 · `liquidacion-y-emision` · crítico · explore propio

- **Objetivo**: convertir los gastos del mes en la expensa de cada unidad, revisable antes de emitir.
- **Historias**: HU-A4, HU-A5. **Reglas**: R01, R03, R06, R07, R13, R15, R16, R34.
- **Decisiones**: D-024, D-031, D-041, D-047 (puntos 5, 7 y 8), D-069.
- **Entra**, en dos bloques de tareas:
  - **Preliquidación (sin efectos)**: reparto de los gastos aprobados, fondo de reserva, cargos
    particulares e intereses, agrupado por ordinaria y extraordinaria y por categoría; no escribe deuda.
  - **Emisión (con efectos)**: congela importes y configuración, genera una obligación por unidad y
    período en una sola transacción, encola el PDF y el email en el worker; permite anular mientras
    la liquidación no fue distribuida (ningún email salió ni ningún vecino la vio), con motivo
    registrado (R17, ProTecc A5, D-055); después de distribuida sólo se corrige con un ajuste (R08).
  - **Controles antes de emitir** (R34, D-069): la lista con bloqueantes y advertencias, la emisión
    con alertas aceptadas y su registro, y los dos controles de este cambio (saldos iniciales sin
    validar y factura duplicada). Los demás controles los suma el cambio que construye lo que revisan.
  - **Links de descarga firmados y con vencimiento** (D-070): el PDF de la expensa nunca tiene una
    dirección pública; este cambio arma el mecanismo que reusan los demás.
  - Plantilla del PDF de la expensa (pasa por la skill impeccable), con el código corto de la unidad
    en el concepto sugerido de la transferencia (R19, ProTecc A1/E3).
- **No entra**: el portal donde el vecino la ve (11); los avisos de vencimiento (13).
- **Depende de**: 5, 6. **Habilita**: 8, 10, 11, 12, 13 y el test de M1.
- **Prerrequisito**: investigar qué exige la normativa de Mendoza para una expensa antes de cerrar
  el PDF (H4, Q12 de Alberto, D-060); Alberto cita la Ley 941 de CABA sólo como ejemplo, no aplica acá.
- **Decidir en el design** (y en su explore): la frontera de la transacción; **qué pasa si falla el
  encolado del PDF después de emitir** (como mínimo, estado por emisión y una forma de reprocesar);
  **qué pasa si falla el extracto bancario o el servicio de IA el día de emitir** (R24, principio P6
  de Alberto, ProTecc A4): la liquidación tiene que poder salir igual, por un camino manual.
- **Que intente romper el rompedor**: emitir dos veces el mismo período; una preliquidación que
  escribe algo; la suma de las unidades que no da el total de gastos más el fondo; Redis caído justo
  después de emitir; renombrar una categoría después de emitir; anular una liquidación después de
  que un vecino ya la vio en el portal; anular sin motivo; emitir con un bloqueo activo sin aceptarlo; aceptar una alerta sin que quede
  registro.
- **Terminado cuando**: se cumplen HU-A4 y HU-A5; **con los datos del piloto, reproduce su última
  liquidación al centavo** (test de aceptación de M1; si los datos todavía no están, se corre con el
  edificio de ejemplo y M1 queda pendiente de ese test).

---

## M2 · Cobra

### 8 · `pagos-informados` · crítico

- **Objetivo**: que el vecino informe su pago con el comprobante y el administrador lo confirme en un clic.
- **Historias**: HU-A6, HU-V4. **Reglas**: R05, R11, R34.
- **Decisiones**: D-017, D-018, D-029, D-069, D-070.
- **Entra**: subir comprobante; lectura con IA que precarga monto, fecha y número de operación;
  número de operación único por edificio; bandeja de confirmación y rechazo con motivo; imputación
  con la fecha de la transferencia usando el motor del cambio 4; repartir un pago entre varias
  unidades de la misma persona; recordar el CBU que confirmó el último pago de cada unidad, como
  sugerencia de alta confianza en la bandeja (R19, ProTecc A1/E3); estado **revertido** para un pago
  confirmado que el banco devuelve, con su contra-movimiento (R18, ProTecc D4); asistente de
  reimputación entre dos unidades, con los dos movimientos enlazados en una sola transacción (R25,
  propuesta, ProTecc B2); los comprobantes se descargan con links firmados y con vencimiento
  (D-070); el control "pagos sin asignar" en la lista antes de emitir, como advertencia (R34).
- **No entra**: el cruce con el extracto (9).
- **Depende de**: 7. **Habilita**: 9, 10, 13.
- **Decidir en el design**: el proveedor de IA para leer comprobantes (detrás de un puerto).
- **Que intente romper el rompedor**: el mismo comprobante dos veces o para dos unidades; un
  comprobante de otro edificio; una confirmación tardía que genera intereses; doble clic en confirmar;
  una imagen con texto que intenta darle órdenes a la IA; revertir un pago que no está confirmado;
  reimputar y que falle a mitad de camino (no tiene que dejar un solo movimiento aplicado); abrir el
  comprobante de otra unidad con un link modificado o vencido.
- **Terminado cuando**: se cumplen HU-A6 y HU-V4; la fecha que cuenta para los intereses es la de la
  transferencia.

### 9 · `extracto-bancario`

- **Objetivo**: que el administrador valide los pagos informados contra el banco.
- **Historias**: HU-A7. **Reglas**: R11, R34.
- **Entra**: subir el extracto en CSV o Excel; un adaptador por banco y formato; marcar coincidencias;
  movimientos sin comprobante como fondos pendientes; un movimiento no confirma dos pagos; el
  control "extracto incompleto" en la lista antes de emitir, como advertencia (R34, D-069).
- **Depende de**: 8.
- **Prerrequisito**: responder qué traen los extractos de los bancos que usan los administradores
  de Mendoza (CBU o nombre del originante, concepto completo): es la pregunta Q2 de Alberto,
  prioridad 0 de su documento, y condiciona si R19 (código de unidad y CBU histórico) funciona como
  está pensado (D-063).
- **Que intente romper el rompedor**: formatos de distintos bancos; el mismo extracto dos veces; dos
  pagos con el mismo importe y fecha.
- **Terminado cuando**: se cumplen los criterios de HU-A7.

### 10 · `morosidad`

- **Objetivo**: ver quién debe, cuánto y desde cuándo.
- **Historias**: HU-A8, HU-A10 (certificado de libre deuda).
- **Entra**: listado por unidad calculado desde las imputaciones; exportación a Excel; definición de
  **moroso crítico** por antigüedad, dos o más liquidaciones vencidas con saldo impago, sin bloqueo
  de amenities (R20, ProTecc M1); marca de "gestión judicial" por unidad que frena los recordatorios
  automáticos y la saca del cálculo de moroso crítico (R31, propuesta, ProTecc G2); condonación de
  interés como movimiento con motivo, sin borrar el recargo original (R29, propuesta, falta decidir
  quién aprueba, ProTecc B5, Q1); **certificado de libre deuda** por venta de unidad, con fecha de
  corte, saldo calculado desde la cuenta corriente y pagos en revisión listados aparte (R21, ProTecc
  G3).
- **Depende de**: 8. **Habilita**: 11, 12.
- **Que intente romper el rompedor**: una deuda pagada en partes que sigue figurando; diferencias
  entre la pantalla y el Excel; una unidad con una sola liquidación vencida marcada como moroso
  crítico; un certificado de libre deuda que incluye una estimación del período en curso; generar el
  certificado dos veces y que cambie el saldo sin que cambie la cuenta corriente.
- **Terminado cuando**: se cumplen los criterios de HU-A8 y HU-A10.

### 11 · `portal-del-vecino`

- **Objetivo**: que el vecino entienda su expensa y pague desde el celular.
- **Historias**: HU-V1 (pantallas), HU-V2, HU-V3, HU-V5. **Reglas**: R16 (presentación).
- **Entra**: todas las unidades de la persona juntas; deuda y vencimiento; expensa por ordinaria,
  extraordinaria y categoría, con la comparación contra el mes anterior; descarga de PDFs con links
  firmados y con vencimiento (D-070); app instalable. Pasa por la skill impeccable.
- **Depende de**: 10. **Habilita**: 12.
- **Que intente romper el rompedor**: ver la unidad de otro vecino; números distintos a los del
  administrador; un iPhone sin instalar la app; pantalla de 320 px; abrir un link de descarga
  vencido, modificado o de otra unidad.
- **Terminado cuando**: se cumplen HU-V1, V2, V3 y V5.

### 12 · `vista-del-consejo`

- **Objetivo**: transparencia para el consejo de propietarios.
- **Historias**: HU-C1.
- **Entra**: morosidad, gastos y liquidaciones en sólo lectura.
- **Depende de**: 11.
- **Que intente romper el rompedor**: cualquier acción de escritura desde un usuario del consejo.
- **Terminado cuando**: se cumple HU-C1.

### 13 · `avisos-por-email`

- **Objetivo**: avisar antes del vencimiento y en mora, sin molestar de más.
- **Historias**: HU-V6. **Reglas**: R27, R28, R34.
- **Entra**: puerto de email con su adaptador; aviso de vencimiento y de mora; un aviso por evento,
  con clave de idempotencia; no avisar a quien ya pagó; un aviso que cae en sábado, domingo o
  feriado se reprograma al primer día hábil siguiente (R27, propuesta, ProTecc W3); validar el
  contacto al cargarlo y, si un envío rebota, mostrar al administrador la lista de "unidades sin
  contacto válido" (R28, propuesta, ProTecc W4); el control "unidades sin contacto válido" en la
  lista antes de emitir, como advertencia (R34, D-069).
- **Depende de**: 8.
- **Decidir en el design**: el proveedor de email (detrás de un puerto, sin costo o el más barato, D-043).
- **Que intente romper el rompedor**: el worker que se cae a mitad del envío; dos avisos el mismo día;
  aviso de mora a alguien con el pago confirmado; un aviso programado para un sábado que no se mueve;
  un contacto con formato inválido que igual queda en la lista de envío.
- **Terminado cuando**: se cumple HU-V6.

---

## M3 · Piloto

### 14 · `lectura-de-facturas`

- **Objetivo**: que el administrador cargue una factura con una foto.
- **Historias**: HU-A3 (factura con QR e IA). **Reglas**: R12, R16, R34.
- **Decisiones**: D-019, D-069, D-070.
- **Entra**: lectura del QR de ARCA (los dos dominios); la IA completa concepto, período, categoría
  y grupo; factura duplicada frenada; aviso si el receptor no es el consorcio; siempre en borrador;
  registro del costo de cada llamada a la IA; control de monto atípico contra el historial de ese
  proveedor en el edificio, para marcar para revisión una factura que la IA pudo leer mal (R23,
  propuesta, falta el umbral, ProTecc A2); las facturas se descargan con links firmados y con
  vencimiento (D-070); el control "facturas leídas por IA con alertas" en la lista antes de emitir,
  como bloqueante (R34).
- **Depende de**: 6.
- **Decidir en el design**: el proveedor de IA (puede ser el mismo del cambio 8).
- **Que intente romper el rompedor**: el ejemplo oficial de ARCA; una factura en dólares; una sin QR;
  una con instrucciones escondidas para la IA; la misma factura dos veces; un monto leído diez veces
  más grande o más chico que el historial del proveedor.
- **Terminado cuando**: se cumple HU-A3 en su parte de factura; decodifica el ejemplo oficial.

### 15 · `piloto-en-paralelo`

- **Objetivo**: demostrar que PropTech reemplaza el método actual del edificio piloto.
- **Entra**: carga de los datos reales del piloto; un mes completo en paralelo; comparación al
  centavo; prueba de restauración de un backup; evidencia de aislamiento entre edificios.
- **Depende de**: todos los anteriores y los datos del piloto (P1).
- **Terminado cuando**: el cierre del mes coincide con el del administrador y un backup se restauró
  con éxito.

---

## Antes de arrancar el cambio 1a

- [ ] Pedirle a Alberto los datos del edificio piloto: padrón con coeficientes, facturas y recibo del
  encargado de un mes, y la liquidación de ese mes (P1).
- [ ] Contarle a Alberto que los montos van en Decimal, como en su documento (D-046).
- [ ] Repositorio limpio y OpenSpec listo (hecho).

## Preguntas abiertas que afectan el roadmap

- **P1 · Piloto**: sin sus datos, M1 queda pendiente del test de aceptación.
- **P8 · Precio**: no afecta ningún cambio.
- **D-066 · Motor de reglas (GoRules ZEN + editor visual)**: suma trabajo a los cambios 3, 7 y 10;
  sus fichas se actualizan en el propose de cada uno (detalle en `motor-de-reglas.md`).
- **Login** y **proveedores de IA y email**: se deciden en el design de los cambios 2, 8, 13 y 14.
