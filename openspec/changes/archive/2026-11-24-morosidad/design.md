# Design

## Context

- **Qué hay hoy en `main`** (`f2cbbd5`, después del 8):
  - `cuenta_corriente/dominio/cobranza.py::clasificar` suma, por cuenta, el residual de capital e interés de
    las obligaciones vencidas (`fecha > vencimiento + gracia`, sin emisión anulada) y cuenta las liquidaciones
    vencidas con capital residual; devuelve `SituacionDeCobranza` con `total_vencido`,
    `liquidaciones_vencidas`, las tres marcas y la `etiqueta` única (R20, R30, D-143). Capital e interés se
    calculan por dentro pero no se devuelven.
  - `cuenta_corriente/aplicacion/cobranza.py::situacion_del_edificio(sesion, complejo_id, fecha)`: la
    situación de cada cuenta de unidad del edificio con la configuración vigente a la fecha.
  - El interés de mora se registra al emitir, con su `corte` (último día del mes anterior), y pertenece a la
    obligación que lo generó (R03, R20).
  - `acceso/dominio/permisos.py`: la matriz perfil × alcance; cada `Accion` es también vocabulario de
    auditoría (`accion_de_auditoria`, una migración por acción nueva, como `0028` y `0041`).
  - `openpyxl` 3.1.5 ya es dependencia del backend (5, importación).
  - Web: el menú del edificio sale de `web/src/app/edificios/[id]/secciones.ts`, cada sección con su acción.
- **Fronteras**: sólo se importa entre módulos por `aplicacion`, sin ciclos (`test_fronteras_de_modulos.py`).
- **Decisiones que ya rigen**: D-058, D-074, D-106, D-143, D-152, D-154; D-167 (acuerdos de este change).

## Goals / Non-Goals

**Goals**
- Ver, a hoy, quién debe, cuánto (capital e intereses) y desde cuándo, con la etiqueta de R20/R30.
- Bajar la misma lista en Excel, con los mismos números.
- Que cada perfil vea y exporte sólo lo que le toca.

**Non-Goals**: ver `proposal.md`, "Qué queda fuera".

## Elecciones (E1 a E8)

Cada una lleva la recomendación del orquestador. La firma de la propuesta las aprueba.

### E1 · La situación devuelve capital, interés y el vencimiento más viejo

`SituacionDeCobranza` suma `capital_vencido`, `interes_vencido` y `vencida_desde` (fecha o nula), calculados
en el mismo recorrido de `clasificar`, sin cambiar la etiqueta ni el total (`total_vencido = capital_vencido +
interes_vencido`). `vencida_desde` es el vencimiento de la obligación vencida más vieja con residual mayor
que cero en cualquier componente (capital o interés). Los consumidores de hoy (8, 7) no cambian.

### E2 · La lectura de la morosidad vive en `cuenta_corriente/aplicacion`

`morosidad_del_edificio(sesion, complejo_id, fecha)` devuelve las cuentas de unidad con `total_vencido > 0`,
ordenadas, con el resumen y la fecha de los intereses. El nombre de la unidad y de sus propietarios lo pone
la ruta, pidiéndolo a `complejos` y `acceso` por su `aplicacion`, o la lectura si las fronteras lo permiten
sin ciclo; lo decide el constructor dentro de `test_fronteras_de_modulos.py`.

### E3 · Los intereses son los registrados

`interes_vencido` es el residual del componente interés de las obligaciones vencidas, es decir el interés
registrado en el libro, neto de ajustes y contra-asientos (L-096), menos lo imputado. No se estima el interés
corrido desde el último corte (D-167). `intereses_al` es el `corte` más reciente de un movimiento de interés
que cuenta en las cuentas de unidad del edificio, o nulo si no hay ninguno.

### E4 · La antigüedad se cuenta desde el vencimiento

`dias = fecha - vencida_desde`, en días. La obligación cuenta como vencida recién después de la gracia (R03),
pero los días se cuentan desde el vencimiento que figura en la expensa (D-167).

### E5 · El orden y el resumen

Primero las cuentas con etiqueta `moroso_critico`; dentro de cada grupo, `total_vencido` descendente y, ante
un empate, el identificador de la unidad ascendente. El resumen: `unidades_con_deuda` (las listadas),
`morosos_criticos` y `total_vencido` (la suma de las listadas, incluidas las de bajo el umbral).

### E6 · Dos acciones nuevas

`ver_morosidad`: SA, AP, AE, CP, CE, AX, CO. `exportar_morosidad`: SA, AP, AE, CP, CE. Una migración de
vocabulario cada una (`0048`, `0049`), como `0028`. Leer no se audita (como `ver_liquidaciones`).

### E7 · La ruta y la fecha

`proptech_api/morosidad.py`, con la dependencia `hoy()` (fecha de hoy en Mendoza), reemplazable en los tests
(L-090). Orden de chequeo de siempre (D7): edificio fuera de alcance u otra administración, 404; sin la acción,
403 con `permiso_faltante`. Sin parámetros de consulta: la lista es a hoy. Montos como texto con dos
decimales.

### E8 · El Excel

`openpyxl` en el backend, una hoja "Morosidad": edificio, fecha y fecha de los intereses arriba; una fila de
títulos; una fila por unidad en el mismo orden que la API; la fila de totales al pie. Los montos se escriben
como `Decimal` (número de la celda, nunca texto) con formato `"$ "#,##0.00` y los días como entero. Nombre del
archivo `morosidad-<edificio>-<AAAA-MM-DD>.xlsx`. La pantalla lo descarga sin perder el gesto (L-099).

## Risks / Trade-offs

- **Interés atrasado**: la lista no muestra el interés corrido desde el último corte; la pantalla dice "al
  {intereses_al}" para que no se lea como al día.
- **Datos personales en un archivo**: el Excel sale del sistema; por eso sólo lo exportan SA, AP, AE, CP y CE,
  y sin email, teléfono ni DNI.
- **Rendimiento**: `situacion_del_edificio` arma la foto de cada cuenta; con los edificios del MVP (decenas de
  unidades) alcanza. Si un barrio grande lo vuelve lento, se mide en el 12 o el 15.
