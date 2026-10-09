# Roadmap de ejecución del MVP

El plan cambio por cambio, del primero al último. Cada ficha es **la entrada del `/opsx:propose`**
de ese cambio: el proponente parte de acá y de los archivos que la ficha cita. **Se reescribe**
cuando cambia el plan; el porqué va a `decisiones.md` (D-045, D-047, D-049).

El ciclo de cada cambio está en `forma-de-trabajo.md`: proponer, construir, romper, auditar y
archivar con commit y push. Un cambio arranca cuando el anterior está archivado.

## Resumen

| # | Cambio | Hito | Depende de | Explore propio | Crítico | Tamaño |
|---|---|---|---|---|---|---|
| 1a | `infraestructura-base` | M1 | ninguno | no | no | mediano |
| 1b | `arranque-del-sistema` | M1 | 1a | no | no | mediano |
| 2 | `acceso-y-aislamiento` | M1 | 1b | **sí** | **sí** | grande |
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
Código:  1a → 1b → 2 → 3 → 4 → 5 → 6 → 7 ──┐
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

### 1b · `arranque-del-sistema`

- **Objetivo**: dejar listas las piezas transversales que usan todos los cambios siguientes.
- **Decisiones**: D-038, D-042, D-046, D-047 (punto 4).
- **Entra**: Redis y el worker ARQ (con una tarea de prueba, reintentos espaciados e idempotencia);
  `config/parametros.yaml` con los valores iniciales de D-042 y su lector validado; tipo `Dinero`
  sobre `Decimal` en `proptech_core/compartido` (sólo la representación: construir desde texto,
  serializar como texto, rechazar `float`); logs estructurados en JSON con número de seguimiento
  (`request_id`) que viaja de la web a la API, a la base y al worker; backups automáticos de
  PostgreSQL fuera del contenedor; datos semilla de un edificio de ejemplo (sólo lo que el esquema
  permita a esta altura; se completa en 3).
- **No entra**: el reparto por mayor resto (4); usuarios y login (2).
- **Depende de**: 1a. **Habilita**: 2.
- **Decidir en el design**: dónde se guardan los backups y cada cuánto; formato del log.
- **Que intente romper el rompedor**: un `parametros.yaml` mal formado o con una tasa negativa; un
  `float` colado en un monto; una tarea del worker que se ejecuta dos veces; un pedido sin
  `request_id` o con uno malicioso; datos personales en los logs.
- **Terminado cuando**: el worker reintenta una tarea que falla y no la duplica; el lector rechaza
  parámetros inválidos con un mensaje claro; un monto `float` hace fallar un test; el backup se
  genera solo.

### 2 · `acceso-y-aislamiento` · crítico · explore propio

- **Objetivo**: que cada persona entre y vea sólo lo suyo, aunque el código tenga un error.
- **Historias**: HU-V1 (entrada del vecino). **Reglas**: R08 (auditoría), R10.
- **Decisiones**: D-009, D-016, D-021, D-036, D-037, D-039.
- **Entra**: login del personal y del vecino; los cuatro roles (titular, colaborador, consejo,
  vecino); alcance por edificio; Row-Level Security con `SET LOCAL` y un rol de base sin
  privilegios; auditoría en la misma transacción; 404 fuera de alcance y 403 sin permiso;
  límite de pedidos en el login.
- **No entra**: la pantalla del portal (11) y la del consejo (12): acá sólo el acceso.
- **Depende de**: 1b. **Habilita**: 3, 4.
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
  completar los datos semilla del edificio de ejemplo.
- **No entra**: carga masiva desde Excel (5); cálculos (4, 7).
- **Depende de**: 2. **Habilita**: 5, 6.
- **Decidir en el design**: cómo se guarda la configuración vigente en cada liquidación (historia).
- **Que intente romper el rompedor**: coeficientes de un grupo que no suman 1; una unidad repetida;
  borrar una categoría con gastos; cambiar la tasa y ver si toca algo ya emitido; editar la
  configuración de otro edificio.
- **Terminado cuando**: se cumplen los criterios de HU-A1; un edificio nuevo arranca con los valores
  de `parametros.yaml`; cambiar el archivo no altera edificios existentes.

### 4 · `motor-de-cuenta-corriente` · crítico · explore propio

- **Objetivo**: el corazón de la plata: que cada peso de deuda viva en un solo lugar y nunca se pierda un centavo.
- **Historias**: HU-A9 (correcciones). **Reglas**: R03, R04, R05, R06, R07, R08, R09 (el caso de uso
  de saldo inicial), R13 (orden de imputación por tipo).
- **Decisiones**: D-010, D-011, D-012, D-015, D-016, D-024, D-046.
- **Entra**: libro de movimientos de sólo agregar, sin campo saldo; obligaciones, pagos e
  imputaciones; intereses simples calculados al registrarse; reparto por **mayor resto** como función
  pública de `proptech_core` (la usa el cambio 6); correcciones con contra-asiento; dos fechas por
  pago (registro y valor); caso de uso de saldo inicial (con detalle por período o total único);
  bloqueo para pagos simultáneos de la misma unidad.
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
- **Decisiones**: D-015, D-029.
- **Entra**: plantilla de Excel (piso, departamento, tipo, propietario, contacto, coeficiente, saldo
  inicial); validación fila por fila con informe de errores; carga atómica (todo o nada); detección
  de reimportación; saldos iniciales usando el caso de uso del cambio 4.
- **No entra**: importar gastos o cargos (6).
- **Depende de**: 3, 4. **Habilita**: 7 y el test de M1.
- **Que intente romper el rompedor**: un archivo con columnas cambiadas de lugar, celdas vacías,
  números con coma y con punto, coeficientes que suman 0,9999; el mismo archivo subido dos veces; un
  archivo enorme; un archivo que no es Excel.
- **Terminado cuando**: se cumplen los criterios de HU-A2; un archivo con un solo error no carga
  nada y lo informa; la suma importada coincide con la del archivo.

### 6 · `gastos-y-cargos`

- **Objetivo**: cargar los gastos del mes y los cargos de cada unidad, listos para liquidar.
- **Historias**: HU-A3 (carga manual, incluido el sueldo del encargado), HU-A3b. **Reglas**: R01
  (reparto de cada gasto en su grupo, usando el mayor resto del cambio 4), R13, R14, R16.
- **Decisiones**: D-013, D-024, D-025, D-026, D-028, D-041.
- **Entra**: proveedores; gastos en borrador y aprobados con categoría, grupo y tipo ordinario o
  extraordinario; sueldo del encargado como gasto; cargos particulares sueltos o importados desde
  Excel; aprobación.
- **No entra**: la lectura de facturas por QR e IA (14): acá la carga es manual.
- **Depende de**: 3, 4. **Habilita**: 7, 14.
- **Que intente romper el rompedor**: un gasto sin categoría que se aprueba; un cargo particular que
  termina repartido entre todos; un gasto de otro edificio; un importe con tres decimales; aprobar
  dos veces el mismo gasto.
- **Terminado cuando**: se cumplen los criterios de HU-A3 (manual) y HU-A3b; un gasto en borrador no
  aparece en ningún cálculo.

### 7 · `liquidacion-y-emision` · crítico · explore propio

- **Objetivo**: convertir los gastos del mes en la expensa de cada unidad, revisable antes de emitir.
- **Historias**: HU-A4, HU-A5. **Reglas**: R01, R03, R06, R07, R13, R15, R16.
- **Decisiones**: D-024, D-031, D-041, D-047 (puntos 5, 7 y 8).
- **Entra**, en dos bloques de tareas:
  - **Preliquidación (sin efectos)**: reparto de los gastos aprobados, fondo de reserva, cargos
    particulares e intereses, agrupado por ordinaria y extraordinaria y por categoría; no escribe deuda.
  - **Emisión (con efectos)**: congela importes y configuración, genera una obligación por unidad y
    período en una sola transacción, encola el PDF y el email en el worker.
  - Plantilla del PDF de la expensa (pasa por la skill impeccable).
- **No entra**: el portal donde el vecino la ve (11); los avisos de vencimiento (13).
- **Depende de**: 5, 6. **Habilita**: 8, 10, 11, 12, 13 y el test de M1.
- **Decidir en el design** (y en su explore): la frontera de la transacción; **qué pasa si falla el
  encolado del PDF después de emitir** (como mínimo, estado por emisión y una forma de reprocesar).
- **Que intente romper el rompedor**: emitir dos veces el mismo período; una preliquidación que
  escribe algo; la suma de las unidades que no da el total de gastos más el fondo; Redis caído justo
  después de emitir; renombrar una categoría después de emitir.
- **Terminado cuando**: se cumplen HU-A4 y HU-A5; **con los datos del piloto, reproduce su última
  liquidación al centavo** (test de aceptación de M1; si los datos todavía no están, se corre con el
  edificio de ejemplo y M1 queda pendiente de ese test).

---

## M2 · Cobra

### 8 · `pagos-informados` · crítico

- **Objetivo**: que el vecino informe su pago con el comprobante y el administrador lo confirme en un clic.
- **Historias**: HU-A6, HU-V4. **Reglas**: R05, R11.
- **Decisiones**: D-017, D-018, D-029.
- **Entra**: subir comprobante; lectura con IA que precarga monto, fecha y número de operación;
  número de operación único por edificio; bandeja de confirmación y rechazo con motivo; imputación
  con la fecha de la transferencia usando el motor del cambio 4; repartir un pago entre varias
  unidades de la misma persona.
- **No entra**: el cruce con el extracto (9).
- **Depende de**: 7. **Habilita**: 9, 10, 13.
- **Decidir en el design**: el proveedor de IA para leer comprobantes (detrás de un puerto).
- **Que intente romper el rompedor**: el mismo comprobante dos veces o para dos unidades; un
  comprobante de otro edificio; una confirmación tardía que genera intereses; doble clic en confirmar;
  una imagen con texto que intenta darle órdenes a la IA.
- **Terminado cuando**: se cumplen HU-A6 y HU-V4; la fecha que cuenta para los intereses es la de la
  transferencia.

### 9 · `extracto-bancario`

- **Objetivo**: que el administrador valide los pagos informados contra el banco.
- **Historias**: HU-A7. **Reglas**: R11.
- **Entra**: subir el extracto en CSV o Excel; un adaptador por banco y formato; marcar coincidencias;
  movimientos sin comprobante como fondos pendientes; un movimiento no confirma dos pagos.
- **Depende de**: 8.
- **Que intente romper el rompedor**: formatos de distintos bancos; el mismo extracto dos veces; dos
  pagos con el mismo importe y fecha.
- **Terminado cuando**: se cumplen los criterios de HU-A7.

### 10 · `morosidad`

- **Objetivo**: ver quién debe, cuánto y desde cuándo.
- **Historias**: HU-A8.
- **Entra**: listado por unidad calculado desde las imputaciones; exportación a Excel.
- **Depende de**: 8. **Habilita**: 11, 12.
- **Que intente romper el rompedor**: una deuda pagada en partes que sigue figurando; diferencias
  entre la pantalla y el Excel.
- **Terminado cuando**: se cumplen los criterios de HU-A8.

### 11 · `portal-del-vecino`

- **Objetivo**: que el vecino entienda su expensa y pague desde el celular.
- **Historias**: HU-V1 (pantallas), HU-V2, HU-V3, HU-V5. **Reglas**: R16 (presentación).
- **Entra**: todas las unidades de la persona juntas; deuda y vencimiento; expensa por ordinaria,
  extraordinaria y categoría, con la comparación contra el mes anterior; descarga de PDFs; app
  instalable. Pasa por la skill impeccable.
- **Depende de**: 10. **Habilita**: 12.
- **Que intente romper el rompedor**: ver la unidad de otro vecino; números distintos a los del
  administrador; un iPhone sin instalar la app; pantalla de 320 px.
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
- **Historias**: HU-V6.
- **Entra**: puerto de email con su adaptador; aviso de vencimiento y de mora; un aviso por evento,
  con clave de idempotencia; no avisar a quien ya pagó.
- **Depende de**: 8.
- **Decidir en el design**: el proveedor de email (detrás de un puerto, sin costo o el más barato, D-043).
- **Que intente romper el rompedor**: el worker que se cae a mitad del envío; dos avisos el mismo día;
  aviso de mora a alguien con el pago confirmado.
- **Terminado cuando**: se cumple HU-V6.

---

## M3 · Piloto

### 14 · `lectura-de-facturas`

- **Objetivo**: que el administrador cargue una factura con una foto.
- **Historias**: HU-A3 (factura con QR e IA). **Reglas**: R12, R16.
- **Decisiones**: D-019.
- **Entra**: lectura del QR de ARCA (los dos dominios); la IA completa concepto, período, categoría
  y grupo; factura duplicada frenada; aviso si el receptor no es el consorcio; siempre en borrador;
  registro del costo de cada llamada a la IA.
- **Depende de**: 6.
- **Decidir en el design**: el proveedor de IA (puede ser el mismo del cambio 8).
- **Que intente romper el rompedor**: el ejemplo oficial de ARCA; una factura en dólares; una sin QR;
  una con instrucciones escondidas para la IA; la misma factura dos veces.
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
- **Login** y **proveedores de IA y email**: se deciden en el design de los cambios 2, 8, 13 y 14.
