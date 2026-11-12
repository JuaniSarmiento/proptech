# Contrato que asume la aceptación de H-007

La aceptación de H-007 (`aceptacion/H-007/tests/` y `aceptacion/H-007/e2e/`) es de caja negra: entra
por la API real y por el navegador. Esto es exactamente lo que espera del código. Si el constructor
necesita cambiar algo de esta lista, frena y lo pide: cambiarlo obliga a congelar otra aceptación.

Fuente: `HISTORIAS.md` (H-007), `openspec/changes/importacion-desde-excel/design.md` (D0 a D11, E1 a E15
en su recomendación) y la spec `importacion-de-padron`.

## La plantilla

Un `.xlsx`. Hojas por **nombre exacto** (no por posición); encabezados en la fila 1 por **nombre exacto**
(no por posición; columnas extra se ignoran).

| Hoja | Encabezados, en el orden de la plantilla descargada |
|---|---|
| `Unidades` | `Unidad`, `Tipo`, `Piso`, `Coeficiente`, `Superficie m2`, `Propietario`, `Email` |
| `Saldos` | `Unidad`, `Período`, `Vencimiento`, `Concepto`, `Importe`, `Interés acumulado` |
| `Control` | `Unidad`, `Saldo según el administrador` |

- `Unidades` es obligatoria si el edificio no tiene unidades. Si ya tiene, tiene que faltar o venir sin
  filas de datos; una fila de datos es error (E7).
- H-007 no valida `Saldos` ni `Control` (son de H-008): un archivo que las trae vacías se acepta.
- Fila del Excel: el encabezado es la fila 1.
- Límites: 2 MiB por archivo y 2.000 filas de datos por hoja.
- Números (E14): una celda numérica se convierte con `Decimal(repr(valor))` a notación fija (`8.3e-05`
  → `0.000083`); un texto acepta coma decimal (`0,083333`, `1.234,56`) o punto decimal sin coma
  (`45.50`); un texto ambiguo (`1.234`) o con más decimales de los permitidos (6 en `Coeficiente`, 2 en
  `Superficie m2`) es error de fila, nunca se redondea. Una fórmula se lee por su valor en caché; sin
  valor en caché es error de fila.
- `Tipo` exacto en minúscula: `departamento`, `cochera`, `baulera`, `local`. `Piso` exacto del
  vocabulario del edificio (`SS1`…, `PB`, `1`…), sin recortar espacios ni traducir variantes; el
  edificio sin pisos configurados se rechaza nombrando `piso`.
- La suma de `Coeficiente` se compara con 1 con ±0,0001 (borde incluido): fuera, el archivo se rechaza
  con un error **de la hoja** (sin fila) que nombra la suma y la tolerancia; dentro y distinta de 1, se
  carga con una advertencia que nombra la suma (por ejemplo "los coeficientes suman 0,9999").
- `Propietario` y `Email` son opcionales. Con propietario se crea la persona (o se reusa por email en la
  administración) y su asignación `vecino` / `propietario` sobre la unidad, **sin invitar** (ninguna
  fila nueva en `invitacion`). El mismo email en dos filas es una sola persona.

## La API

### `POST /api/complejos/{complejo_id}/importaciones`

- Multipart: `archivo` (el `.xlsx`) y `fecha_de_migracion` (texto ISO `AAAA-MM-DD`, ≤ hoy, obligatoria).
- Orden de chequeo (D7): edificio inexistente o fuera de alcance → 404 `{"detail": "no encontrado"}`
  (también el administrador de **otro** edificio y otra administración); sin el permiso → 403 con el
  cuerpo de siempre (`{"detail": {"codigo": "sin_permiso", ..., "permiso_faltante":
  "importar_padron_y_saldos"}}`); sin sesión → 401.
- **201** con:

  ```json
  {
    "importacion_id": "<uuid>",
    "unidades_creadas": 12,
    "propietarios_creados": 8,
    "propietarios_reusados": 1,
    "filas_de_saldo": 0,
    "advertencias": [{"hoja": "Unidades", "fila": null, "columna": "Coeficiente", "motivo": "..."}]
  }
  ```

  `propietarios_creados` cuenta personas nuevas; `propietarios_reusados`, personas que ya existían en
  la administración antes de importar (repetir un email dentro del archivo no cuenta como reusada).
  `filas_de_saldo` es 0 en H-007.
- **422** (archivo o filas inválidos, o `fecha_de_migracion` faltante, futura o mal escrita):

  ```json
  {"detail": [{"hoja": "Unidades", "fila": 9, "columna": "Piso", "motivo": "..."}]}
  ```

  Cada error trae `hoja`, `fila`, `columna` y `motivo` (las cuatro claves siempre presentes; `null` donde
  no aplica). Errores de archivo (no es un `.xlsx`, supera un límite, falta una hoja obligatoria o un
  encabezado) llevan `fila: null` y cortan antes de leer filas; el motivo nombra el problema (el límite
  como `2 MiB` o `2.000 filas`, la hoja `Unidades`, la columna faltante). Un rechazo de
  `fecha_de_migracion` puede venir con la forma estándar de validación de FastAPI, pero su texto tiene que
  nombrar `fecha_de_migracion`. Una fila repetida nombra la otra fila en su motivo ("repetida, ya está en
  la fila 4"). **Todos** los errores juntos.
- **409** `{"detail": "conflicto", "campo": "archivo", "importacion_id": "<la anterior>"}` si el mismo
  archivo (misma huella SHA-256 de los bytes, cualquier nombre) ya se importó en el edificio (en un
  estado distinto de `descartada`); `{"detail": "conflicto", "campo": "estado_migracion"}` con la migración
  en `confirmada` o `sin_saldos_previos`. Dos subidas simultáneas del mismo padrón: una 201 y la otra
  409 (nunca 24 unidades).
- Cualquier rechazo no escribe nada: ni unidades, ni personas, ni asignaciones, ni `importacion`, ni
  auditoría, ni invitaciones.
- Con el archivo válido: una auditoría `crear_unidad` por unidad (vía `crear_unidad`) y una auditoría
  `importar_padron_y_saldos`.

### `GET /api/complejos/{complejo_id}/importaciones/plantilla`

- 200, `content-type` `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, la plantilla
  vacía con las tres hojas y sus encabezados (tabla de arriba). Completada con las 12 unidades, se
  importa sin cambios.

## La base

- Migración `0036` (revisión `"0036"`, sobre la `0035`), en `backend/migraciones/versions/0036_*.py`.
- Tabla `importacion` con al menos `id` (el `importacion_id` de la respuesta), `administracion_id`,
  `complejo_id`, `huella` (64 caracteres hexadecimales), `fecha_de_migracion` (date) y `estado`; RLS
  activada **y forzada**; otra administración no ve las filas.
- `importar_padron_y_saldos` en `Accion` (`acceso/dominio/permisos.py`), en la matriz para super admin,
  administrador principal y administrador por edificio (E6), y en `accion_de_auditoria`.
- Los tests estructurales siguen verdes: `tests/unitarios/test_fronteras_de_modulos.py` (módulo
  `importacion` con dueño de su tabla), `tests/integracion/test_rutas_protegidas.py` (las dos rutas en
  `_RUTAS_CUBIERTAS`) y `tests/integracion/test_vocabulario_configuracion.py`.

## La pantalla (`/edificios/{id}/importar`)

- Encabezado (`heading`) **"Importar desde Excel"**.
- Campo de archivo con etiqueta **"Archivo de Excel"**; campo de fecha con etiqueta **"Fecha de
  migración"** (acepta `2026-10-15` con `fill`, es decir un `input type="date"`); botón **"Importar"**.
- Enlace (`link`) **"Descargar plantilla"**: descarga `plantilla-padron.xlsx` (un `.xlsx`, empieza con
  `PK`). Lo sirve Next (el navegador nunca ve el token, D-036), por ejemplo en
  `/edificios/{id}/importar/plantilla`, que pide la plantilla a la API.
- Aceptada: una región (`role="region"`, nombre accesible **"Importación aceptada"**) con el resumen:
  "12 unidades creadas", "10 propietarios nuevos" (más reusados y advertencias si las hay).
- Rechazada (422): el texto "No se cargó nada" y una tabla con nombre accesible **"Errores del
  archivo"**, columnas **Hoja**, **Fila**, **Columna** y **Motivo**, una fila por error, en el orden en
  que llegan.
- 403: un `alert` con **"No podés importar en este edificio."**
- La web manda a la API un `POST /api/complejos/{id}/importaciones` multipart con `archivo` (con su
  nombre original) y `fecha_de_migracion`.

## La API falsa (`web/e2e/api-falsa.ts`)

La construye el constructor para estos tres edificios (ids fijos, como `escenarios-escritura.ts`):

| Edificio | `POST .../importaciones` |
|---|---|
| `00000000-0000-0000-0000-000000000701` | 201 con `unidades_creadas: 12`, `propietarios_creados: 10`, `propietarios_reusados: 0`, `filas_de_saldo: 0`, `advertencias: []` |
| `00000000-0000-0000-0000-000000000702` | 422 con tres errores, en este orden: (`Unidades`, 9, `Piso`), (`Unidades`, 3, `Tipo`), (`Unidades`, 7, `Superficie m2`) |
| `00000000-0000-0000-0000-000000000703` | 403 `sin_permiso` |

- Los tres responden las lecturas que necesite la pantalla como un edificio con la migración
  `pendiente`, y `GET .../importaciones/plantilla` con un `.xlsx` válido.
- El `POST` multipart queda en `/api/__debug/ultima-escritura` con su `content-type` y su cuerpo crudo.
