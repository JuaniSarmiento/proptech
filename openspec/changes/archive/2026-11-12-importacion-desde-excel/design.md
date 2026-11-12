# Design

## Context

- **Qué hay hoy en `main`** (después del 4c, `519e586`):
  - `complejos`: alta y edición de unidades auditadas (`crear_unidad`, `DatosUnidad` con identificador,
    tipo, piso, coeficiente y superficie obligatoria > 0), grupos de reparto con su informe de
    tolerancia (R01, `informar_coeficientes`: ok / advertencia / fuera de tolerancia, ±0,0001 con el borde
    incluido), `estado_migracion` (`pendiente`, `confirmada`, `sin_saldos_previos`) y
    `confirmar_sin_saldos_previos` con `SELECT ... FOR UPDATE` sobre `complejo`.
  - `acceso`: personas (`nombre`, `email` único por administración), la relación persona-unidad
    (`asignacion_rol` con `rol='vecino'` y `vinculo` propietario o inquilino), `dar_de_alta_vecino` (que
    invita por Clerk), el vocabulario `Accion` (permiso y auditoría a la vez) y la matriz de D-106.
  - `gastos`: el único lector de Excel (`openpyxl`, `data_only=True`, columnas fijas, `str()` sobre la
    celda) y la validación "todo o nada" con informe por fila (`ImportacionInvalida` → 422 con
    `{"detail": [{"fila", "motivo"}]}`). Deuda que pasa al 5: D1 (sin límite de bytes ni filas, una
    consulta al padrón por fila), D2 (docstring falso sobre fórmulas, L-066), D5.
  - `cuenta_corriente`: `registrar_saldo_inicial` (4c, H-005) con su contrato de filas (detalle por
    período, total único, crédito), la firma del pedido, el replay, la carga única por edificio y el
    interés desde la migración. **No autoriza, no audita y no cambia el estado de migración**: eso es del
    5 (ficha 4c, "Para el 5").
- **Fronteras** (`test_fronteras_de_modulos.py`): sólo se importa entre módulos por `aplicacion`, sin
  ciclos; `cuenta_corriente` ya importa `complejos`, así que `complejos` no puede importar
  `cuenta_corriente`.
- **Web**: `edificios/[id]/saldos-previos` sólo ofrece "sin saldos previos"; el paso 7 del resumen dice
  "Confirmar que el edificio arranca sin saldos previos"; `textoDeEstados.ts` no traduce `confirmada`.
- **Decisiones que ya rigen**: R09 (saldo inicial), D-068 (borrador comparado unidad por unidad,
  aceptación registrada, cierre al confirmar), D-077 (CRITICAL), D-082/D-083 (sin saldos previos,
  interés que no genera interés), D-100 (coeficientes de grupos parciales, P24), D-128 (vocabulario del
  piso, coincidencia completa), D-153 (E16 y E18 del 4c), D-154 (CI al cerrar el change), D-155 (ajuste
  de saldo inicial, PA-1).

## Goals / Non-Goals

**Goals**
- Subir un Excel con el padrón y, opcionalmente, los saldos previos; validarlo entero (todo o nada) con
  un informe por fila; crear las unidades y sus propietarios; dejar los saldos en un borrador que no toca
  el libro.
- Comparar el borrador unidad por unidad contra el control del administrador, mostrar cada diferencia
  aunque el total coincida, registrar la aceptación de las diferencias y confirmar: el libro recibe el
  saldo inicial (4c), el edificio pasa a `confirmada` y el importador se cierra.
- Corregir después un saldo inicial cargado de menos con un ajuste con motivo (D-155).

**Non-Goals**
- Importar gastos o cargos (6), grupos parciales y sus coeficientes propios (se configuran en pantalla,
  D-100), inquilinos, teléfonos, invitar a los propietarios (la invitación sigue siendo la acción
  existente), corregir un saldo cargado de más (correcciones del 4b), reabrir una migración (R09).

## Decisions

### D0 · Un módulo nuevo `importacion`

El caso de uso que orquesta todo vive en `proptech_core/importacion/` (`dominio/`, `aplicacion/`,
`adaptadores/`, `puertos.py`), que importa `complejos.aplicacion`, `acceso.aplicacion` y
`cuenta_corriente.aplicacion`. Ninguno de ellos importa `importacion`: sin ciclos. Es dueño de sus tablas
(`_DUENO_DE_TABLA`). La ruta vive en `proptech_api/importacion.py`.

### D1 · La plantilla

Un `.xlsx` con hojas por nombre exacto (no por posición) y encabezados en la fila 1, buscados por nombre
exacto (no por posición: una columna cambiada de lugar se lee igual; una que falta es error de archivo):

- **`Unidades`** (obligatoria si el edificio no tiene unidades, E7): `Unidad` (identificador, 1 a 40),
  `Tipo` (`departamento`, `cochera`, `baulera`, `local`, exacto), `Piso` (vocabulario del edificio,
  D-128), `Coeficiente` (hasta 6 decimales), `Superficie m2` (> 0, hasta 2 decimales), `Propietario`
  (nombre, opcional), `Email` (opcional).
- **`Saldos`** (opcional): `Unidad`, `Período` (`AAAA-MM` o una fecha cuyo día es 1; vacío = total
  único), `Vencimiento` (fecha; vacío sólo en total único), `Concepto` (`Ordinaria`, `Fondo de reserva`,
  `Extraordinaria`; vacío en total único), `Importe` (negativo = crédito a favor), `Interés acumulado`
  (≥ 0, vacío = 0).
- **`Control`** (obligatoria si hay `Saldos`): `Unidad`, `Saldo según el administrador` (positivo debe,
  negativo a favor). Es el "listado del administrador" de D-068.

La fecha de migración se elige al subir (no está en el Excel) y no puede ser posterior a hoy.

### D2 · Lectura de celdas (nunca `float`)

`openpyxl` con `read_only=True, data_only=True` (las fórmulas se leen por su valor en caché; una fórmula
sin valor en caché es error de fila: corrige D2 del 6). Cada celda se normaliza a texto antes de
validar: una celda numérica se convierte con `Decimal(repr(valor))` y se escribe en notación fija (una
celda con `8.3e-05` es `0.000083`); una celda de fecha se lee como fecha. Los importes en texto aceptan
coma decimal con o sin punto de miles (`1.234,56`, `1234,56`) y punto decimal sin coma (`1234.56`); un
texto ambiguo (`1.234`: un solo punto y tres dígitos después) es error de fila. Más decimales de los
permitidos (2 en importes, 6 en coeficientes) es error de fila, nunca se redondea.

### D3 · Validación todo o nada, con informe por fila

Se valida todo el archivo antes de escribir nada y se devuelven **todos** los errores juntos, cada uno
con hoja, fila (la del Excel, contando el encabezado como 1), columna y motivo. Errores de archivo (no es
un `.xlsx`, supera el límite, falta una hoja obligatoria o un encabezado) cortan antes de leer filas.
Límites (D1 del 6): 2 MiB por archivo y 2.000 filas por hoja; el padrón se lee una sola vez.

### D4 · Padrón y propietarios

Por cada fila de `Unidades`: la unidad se crea con `crear_unidad` (misma validación y auditoría que el
alta manual, `EventoDelPadron.CREAR_UNIDAD`) y entra al grupo general del edificio con su coeficiente. Si
la fila trae `Propietario`, se crea (o se reusa por email dentro de la administración) la persona y su
asignación `vecino`/`propietario` sobre la unidad, **sin invitar** (E3). Todo en una transacción.

### D5 · Importación y borrador

Tabla `importacion` (una por subida aceptada): edificio, archivo (nombre), `huella` (SHA-256 de los bytes),
fecha de migración, estado (`borrador`, `descartada`, `confirmada`), quién y cuándo. Tablas
`fila_de_saldo_importada` (cada fila de `Saldos` ya normalizada, con su número de fila) y
`control_de_saldo` (cada fila de `Control`). El borrador **no toca el libro**. Una sola importación en
`borrador` por edificio (único parcial); subir otra con el padrón ya creado descarta el borrador anterior
(E7). Mismo archivo dos veces (misma `huella` en el mismo edificio, en cualquier estado salvo
`descartada`) → `Conflicto("archivo")` que nombra la importación existente.

### D6 · Comparación y aceptación

La comparación, para cada unidad con saldo o control, muestra: saldo del borrador (capital + interés
importado − crédito), saldo de control, diferencia, y si la forma de cálculo vigente es "mes entero", que
el primer interés del sistema cubre el mes de la migración (E18 del 4c). Un total igual no oculta
diferencias por unidad (dos errores de signo opuesto). Con diferencias, confirmar exige aceptarlas antes;
la aceptación guarda quién, cuándo y la lista exacta de diferencias aceptadas (tabla
`aceptacion_de_diferencias`) y se audita. Si el borrador cambia después de aceptar, la aceptación ya no
vale.

### D7 · Confirmar

En una transacción: permiso, `SELECT ... FOR UPDATE` sobre el complejo (vía `complejos.aplicacion`, como
`confirmar_sin_saldos_previos`; E8), estado `pendiente`, borrador vigente, diferencias aceptadas si las
hay, `registrar_saldo_inicial` con `operacion_id` = id de la importación (replay natural), el estado del
edificio a `confirmada`, la importación a `confirmada`, y la auditoría. Una importación sin hoja
`Saldos` no se confirma por acá: el edificio se cierra con "sin saldos previos" (E10). Cerrado el
importador, cualquier subida o confirmación da `Conflicto("estado_migracion")`.

### D8 · Ajuste de saldo inicial (D-155)

Ver E11. El ajuste es una **obligación nueva** sin emisión (con `operacion_id`, como las del saldo
inicial) más su registro en `ajuste_de_saldo_inicial` (tabla de sólo agregar: obligación, motivo, quién,
cuándo, `operacion_id` para el replay). No altera `movimiento` ni agrega tipos de movimiento.

### D9 · Permisos y auditoría

Ver E6. Acciones nuevas en `Accion` y en `accion_de_auditoria` (por migración, patrón de `0024`):
`importar_padron_y_saldos`, `aceptar_diferencias_de_saldos`, `confirmar_saldos_iniciales`,
`ajustar_saldo_inicial`. Rutas nuevas en `_RUTAS_CUBIERTAS` de `test_rutas_protegidas.py`.

### D10 · Migraciones

Una por historia que agrega tablas: `0036_importacion` (H-007: `importacion` y vocabulario de auditoría
de importar), `0037_borrador_de_saldos` (H-008: `fila_de_saldo_importada`, `control_de_saldo`,
`aceptacion_de_diferencias` y su vocabulario), `0038_confirmar_saldos` (H-009: vocabulario de confirmar),
`0039_ajuste_de_saldo_inicial` (H-010: la tabla protegida y su vocabulario). Las tablas de la
importación son mutables por la app con RLS forzada (el borrador cambia de estado); `ajuste_de_saldo_
inicial` y `aceptacion_de_diferencias` son de sólo agregar (`TABLAS_DE_SOLO_AGREGAR`), con el barrido de
migraciones y el ensayo de roles (L-083).

### D11 · Pantallas (D-102, D-105, impeccable)

- **Importar** (`edificios/[id]/importar`): elegir archivo y fecha de migración, descargar la plantilla,
  subir; estados: vacío, subiendo, rechazado (tabla de errores por hoja, fila, columna y motivo, sin
  cargar nada), aceptado (resumen: unidades creadas, propietarios, filas de saldo).
- **Comparar** (`edificios/[id]/importar/comparacion`): tabla por unidad (borrador, control, diferencia,
  aviso de mes entero), totales, botón "Aceptar diferencias" con confirmación, "Confirmar saldos"
  habilitado sólo sin diferencias o con ellas aceptadas; estado confirmado con fecha y quién.
- **Ajustar saldo inicial** (desde la cuenta de una unidad de un edificio confirmado): importe, período,
  motivo; confirmación.
- **Resumen del edificio**: el paso 7 ofrece "Importar desde Excel" y "Confirmar sin saldos previos";
  `confirmada` se muestra como "Saldos iniciales confirmados".

## Elecciones a firmar

Firmadas por adelantado por Juani (11/11/2026) en su recomendación. Si en la demo alguna no le cierra, la
historia vuelve a En proceso con el motivo.

| Elección | Propuesta (recomendación) | Alternativas y su consecuencia | Si se elige otra |
|---|---|---|---|
| **E1 · Superficie** | Columna `Superficie m2` obligatoria en la plantilla (es nuestra: el administrador la completa), > 0 y hasta 2 decimales, porque `unidad.superficie_m2` es obligatoria y no hay un valor por defecto honesto | Opcional con un default (inventa un dato que puede usar un reparto por superficie); reabrir el modelo para hacerla nullable (cambio de esquema del 3a) | H-007: plantilla, validación y escenarios |
| **E2 · Unidad, tipo y piso** | `Unidad` es el identificador (como en el alta manual); `Tipo` y `Piso` exactos del vocabulario, sin traducir variantes (coherente con D-128); el edificio tiene que tener pisos y subsuelos configurados o el archivo se rechaza nombrando `piso` | Traducir variantes ("Depto", "1°"): ambigüedad y BREAKING de D-128 | H-007 |
| **E3 · Propietarios** | Un propietario por fila (nombre, email opcional); crea la persona (o la reusa por email en la administración) y su asignación propietario **sin invitar**: la invitación es la acción existente, aparte. Copropietarios e inquilinos se agregan después a mano. Sin teléfono (no existe en el modelo) | Invitar al importar (manda emails reales en una carga masiva, sin revisión); varios propietarios por fila (formato frágil) | H-007 |
| **E4 · Coeficientes** | El importador **rechaza** el archivo si la suma de coeficientes de `Unidades` queda **fuera** de la tolerancia de R01 (±0,0001); dentro de la tolerancia pero distinta de 1 (por ejemplo 0,9999) carga con una advertencia. Menos riesgo de plata: un padrón importado de golpe con coeficientes mal sumados reparte mal toda la primera liquidación; R01 "no se rechaza" sigue valiendo para la edición en pantalla | Cargar siempre y bloquear en la emisión (R34): el error aparece recién al liquidar | H-007 |
| **E5 · Qué grupo se valida** | Sólo el grupo general (todas las unidades del archivo); los grupos parciales (Ascensor, Cocheras) se configuran en pantalla (D-100) | Hojas por grupo (plantilla mucho más compleja) | H-007 |
| **E6 · Permisos** | Importar y descartar: `importar_padron_y_saldos` = super admin, administrador principal y administrador por edificio (como `CONFIGURAR_PADRON`). Aceptar diferencias y confirmar: `aceptar_diferencias_de_saldos` y `confirmar_saldos_iniciales` = super admin y administrador principal (como `CONFIRMAR_SIN_SALDOS_PREVIOS`). Ajustar: `ajustar_saldo_inicial` = super admin y administrador principal (como `CORREGIR_MOVIMIENTO`). Contador, auxiliar, consejo y vecinos: nada | Que el administrador por edificio confirme (más gente puede cerrar el importador con plata) | H-007 a H-010 |
| **E7 · Padrón existente y reimportación** | Si el edificio **no** tiene unidades, la hoja `Unidades` es obligatoria y crea el padrón. Si ya tiene unidades (alta manual o una importación anterior), la hoja `Unidades` tiene que faltar o venir vacía y sólo se importan `Saldos` y `Control` contra los identificadores existentes; una fila de `Unidades` con el padrón ya cargado es error. "Reimportación" = el mismo archivo (misma huella SHA-256) en el mismo edificio → rechazado nombrando la importación anterior; otro archivo con el padrón ya creado reemplaza el borrador de saldos (descarta el anterior) | Fusionar filas con unidades existentes (actualizar coeficientes o pisos desde el Excel: edición masiva auditada fuera de alcance) | H-007, H-008 |
| **E8 · Candado** | Subir, aceptar y confirmar toman `SELECT ... FOR UPDATE` sobre el complejo antes de leer el estado, como "sin saldos previos": dos confirmaciones, o confirmar contra "sin saldos previos", se serializan y la segunda da conflicto | Confiar en el único de la carga del 4c (no cubre "sin saldos previos") | H-008, H-009 |
| **E9 · Límites y lectura** | 2 MiB y 2.000 filas por hoja; un solo `SELECT` del padrón; fórmulas por valor en caché y sin caché = error; corregir el docstring de `gastos/adaptadores/excel.py` (D2 del 6) | Sin límite (un archivo enorme tumba la API) | H-007 |
| **E10 · Confirmar sin hoja de saldos** | Si la importación no trae `Saldos`, no hay borrador que confirmar: el edificio se cierra con la acción existente "sin saldos previos". El importador sólo confirma importaciones con saldos | Confirmar una importación vacía como `confirmada` (dos caminos para lo mismo) | H-009 |
| **E11 · Ajuste de saldo inicial (D-155)** | Una **obligación nueva** sin emisión (`operacion_id` propio, como el saldo inicial; `ck_obligacion_origen` ya lo admite) con el capital del ajuste en el componente que elige el administrador, período el primer día del mes de la migración, vencimiento el día del ajuste (no retroactivo: el interés de R03 corre desde el día siguiente, con la gracia vigente), más su fila en `ajuste_de_saldo_inicial` (motivo 1 a 500 obligatorio, quién, cuándo). Sirve igual con la unidad en cero o con crédito (no necesita una obligación previa; un crédito a favor se imputa con R04). No altera `movimiento` (protegida) ni suma un tipo de movimiento: es deuda nueva con su motivo, que R08 admite. Para R20 cuenta como una liquidación más cuando vence, igual que un total único. Refina la redacción de D-155 ("movimiento nuevo"): se registra como decisión nueva al archivar | Un movimiento débito nuevo (`ajuste_de_saldo_inicial/debito`) colgado de una obligación existente: exige `ALTER` sobre `movimiento` para el motivo (préstamo D-115.3) y no sirve para una unidad sin obligación; vencimiento retroactivo (cobra interés por días que el sistema no conocía) | H-010 |
| **E12 · Textos de la web** | `confirmada` → "Saldos iniciales confirmados"; el paso 7 del resumen ofrece "Importar desde Excel" y "Confirmar sin saldos previos" | Dejar "Estado de migración desconocido" (hoy) | H-009 |
| **E13 · Aviso de E18** | La comparación muestra, por unidad con saldo, "El primer interés del sistema cubre el mes de la migración" cuando la forma vigente a la fecha de migración es "mes entero" | No mostrarlo (riesgo de doble cobro silencioso, E18 del 4c) | H-008 |
| **E14 · Números** | D2 de este diseño: nunca `float`, coma decimal argentina aceptada, texto ambiguo rechazado, más decimales de los permitidos rechazados (no se redondea) | Redondear en silencio (cambia montos) | H-007, H-008 |
| **E15 · Fecha de migración** | Se elige al subir, ≤ hoy, y queda en la importación; la valida otra vez `registrar_saldo_inicial` al confirmar | Columna en el Excel (se repite por fila) | H-007, H-009 |

## Risks / Trade-offs

- **Un padrón grande en una transacción** → 2.000 filas por hoja y una sola lectura del padrón; la
  creación de unidades reusa `crear_unidad` (una auditoría por unidad).
- **E4 contradice el texto de R01 para la carga** → se escribe como decisión al archivar; R01 sigue
  igual para la edición en pantalla.
- **E11 reinterpreta D-155** → decisión nueva al archivar; si Juani lo rechaza en la demo, vuelve H-010.
- **Tablas protegidas nuevas** → L-083: barrido local de migraciones y ensayo de roles en H-008 y H-010.
- **Una aceptación vieja atada a la cabeza** (L-082) → las aceptaciones prueban su migración, no "la
  última".

## Migration Plan

`0036` a `0039` crean tablas vacías y vocabulario; no tocan datos. Las bajadas, sólo con tablas vacías y
dentro del ciclo de devolución de propiedad para las protegidas.

## Open Questions

- **P58 (Alberto)** suma la pregunta de E18: si el interés acumulado de su Excel incluye el mes en curso
  al migrar. No bloquea: E13 lo muestra.
- **Formato del Excel real de Alberto**: la plantilla es nuestra; adaptar su Excel a la plantilla queda
  para el piloto (15).
