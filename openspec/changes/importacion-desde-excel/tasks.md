## Estado del orquestador

- Change: 5 `importacion-desde-excel` (C-08), CRITICAL. Base: `main` en `519e586` (4c mergeado).
- Firma por adelantado de Juani (11/11/2026, `04ebf1e`), sobre las elecciones E1 a E15 de `design.md` en
  su recomendación. Partido en H-007 a H-010 (`HISTORIAS.md`), sin rompedor (D-152), CI al cerrar el
  change (D-154).
- Constructor: Sonnet (`rein-constructor`) por tandas, con brief y relevo en
  `.git/informes-importacion-desde-excel/`.

<!-- El constructor anota debajo de cada tarea la evidencia (comando, hora, extracto) del RED y de cada
mutante, en un commit anterior al de producción (L-061). -->

# Tasks

## Antes de construir (no son tareas del constructor)

- Firma CRITICAL en `proposal.md` `## Aprobación` (hecha por adelantado). Aceptación de cada historia
  congelada en su SHA antes de construirla.
- Reglas comunes a todas las tareas: RED antes del código, leído en el traceback hasta la aserción del
  test (L-049) y commiteado antes del código de producción (L-061); cada aserción de plata, de seguridad
  o de "no escribe nada" lleva un mutante con copia previa y revertido, que dice qué defensa apaga y en
  qué aserción espera el rojo (L-013, L-019, L-034, L-036). Montos y coeficientes siempre `Dinero`,
  `Decimal` o `Coeficiente` desde texto, nunca `float`. Se corren sólo los tests tocados; las historias
  que agregan tablas protegidas corren además el barrido local de migraciones (L-083, D-154). Ningún id de
  test de `origin/main` cambia de nombre ni desaparece.

## 1. H-007 · Plantilla y padrón

- [ ] 1.1 **Módulo `importacion` y fronteras.** `backend/src/proptech_core/importacion/` (`dominio/`,
  `aplicacion/`, `adaptadores/`, `puertos.py`), `_DUENO_DE_TABLA` y la regla de importación permitida en
  `tests/unitarios/test_fronteras_de_modulos.py` (design D0). Mutante: `complejos` importando
  `importacion` → rojo en el test de ciclos.
  - **RED 1.1** (11/11/2026 20:45, antes de crear el módulo ni tocar `_DUENO_DE_TABLA`):
    `cd backend && uv run pytest tests/unitarios/test_fronteras_de_modulos.py -q -k importacion` →
    `10 failed, 66 deselected`. Cada rojo cae en su aserción: `assert 'importacion' in ['acceso',
    'complejos', 'cuenta_corriente', 'gastos']`; `assert None == 'importacion'` (`_DUENO_DE_TABLA`); y 8 veces
    `AssertionError: falta el módulo importacion` (ciclos x4, dominio vs `aplicacion` x3, SQL ajeno x1).
- [ ] 1.2 **Lector de la plantilla (adaptador).** `importacion/adaptadores/excel.py`: hojas y encabezados
  por nombre, 2 MiB y 2.000 filas, fórmulas por valor en caché y sin caché = error, celdas numéricas a
  `Decimal(repr())` en notación fija, fechas. Corregir el docstring de `gastos/adaptadores/excel.py` (D2
  del 6). Tests unitarios con archivos `.xlsx` armados en el test (`openpyxl`). Escenarios:
  importacion-de-padron "Columnas en otro orden", "Falta un encabezado", "No es un Excel", "Archivo
  enorme", "Fórmula sin valor en caché". Mutantes: leer por posición; `float()` sobre la celda; sin
  límite de bytes.
- [ ] 1.3 **Validación del padrón (dominio puro).** `importacion/dominio/padron.py`: todo o nada con
  todos los errores (hoja, fila, columna, motivo), números (E14), unidad repetida, tipo, piso exacto del
  vocabulario, coeficiente, superficie, email, suma de coeficientes con la tolerancia de R01 (E4: fuera
  rechaza, dentro y distinta de 1 advierte). Escenarios de importacion-de-padron. Mutantes: devolver sólo
  el primer error; recortar el piso; redondear un coeficiente de 7 decimales; aceptar la suma 0,9998;
  rechazar la 0,9999.
- [ ] 1.4 **Migración `0036_importacion`.** Tabla `importacion` (D5) con RLS forzada, FK compuestas a
  `complejo` y `persona`, único parcial de un `borrador` por edificio, único de huella por edificio; las
  acciones `importar_padron_y_saldos` en `Accion`, en la matriz (E6) y en `accion_de_auditoria`. Tests de
  esquema, de aislamiento y de cabeza (L-082: el test prueba la `0036`, no "la última").
- [ ] 1.5 **Caso de uso `importar` (padrón).** Permiso, tenant, `FOR UPDATE` del complejo, estado
  `pendiente`, validación completa antes de escribir, una sola lectura del padrón, `crear_unidad` por
  fila, grupo general, propietarios sin invitar (E3), padrón existente (E7), misma huella → conflicto,
  auditoría. Integración contra PostgreSQL real. Mutantes: escribir antes de validar todo; invitar al
  propietario; no bloquear el complejo.
- [ ] 1.6 **Ruta y pantalla.** `POST /api/complejos/{id}/importaciones` (multipart: archivo y fecha de
  migración) con 422 `{"detail": [{hoja, fila, columna, motivo}]}`, en `_RUTAS_CUBIERTAS`; descarga de la
  plantilla; pantalla `edificios/[id]/importar` (D11) con sus estados y e2e de Playwright (archivo válido,
  archivo con errores, sin permiso).

## 2. H-008 · Borrador de saldos y comparación

- [ ] 2.1 **Validación de `Saldos` y `Control` (dominio).** Contrato del saldo inicial (E11 y E16 del 4c),
  números, mezcla de detalle y total, unidad inexistente, vencimientos, crédito. Escenarios de
  borrador-de-saldos. Mutantes: aceptar un vencimiento posterior a la migración; aceptar dos vencimientos
  en un período.
- [ ] 2.2 **Migración `0037_borrador_de_saldos`.** `fila_de_saldo_importada`, `control_de_saldo`,
  `aceptacion_de_diferencias` (de sólo agregar, en `TABLAS_DE_SOLO_AGREGAR`) y la acción
  `aceptar_diferencias_de_saldos`. Matriz de mutantes de protección como la `0034`; ensayo de roles y
  barrido local de migraciones (L-083).
- [ ] 2.3 **Borrador y comparación (aplicación).** Guardar el borrador en la misma subida, descartar el
  anterior, sin tocar el libro; comparación por unidad con totales, signo opuesto, aviso de mes entero
  (E13). Mutantes: comparar sólo totales; sumar el crédito en vez de restarlo.
- [ ] 2.4 **Aceptar diferencias.** Permiso (E6), registro exacto de las diferencias, auditoría, la
  aceptación deja de valer con un borrador nuevo. Mutante: aceptar sin guardar la lista.
- [ ] 2.5 **Rutas y pantalla de comparación** (D11) con e2e de Playwright (diferencias visibles aunque el
  total coincida, aceptar, aviso de mes entero).

## 3. H-009 · Confirmar

- [ ] 3.1 **Migración `0038_confirmar_saldos`.** Acción `confirmar_saldos_iniciales` en `Accion`, matriz
  y `accion_de_auditoria`.
- [ ] 3.2 **Caso de uso `confirmar`.** Permiso, `FOR UPDATE` del complejo, estado `pendiente`, borrador
  vigente, diferencias aceptadas, traducción a los tipos del 4c, `registrar_saldo_inicial` con
  `operacion_id` = importación, estado `confirmada` del edificio (por un caso de uso de
  `complejos.aplicacion`), importación `confirmada`, auditoría, todo en una transacción. Concurrencia
  contra otra confirmación y contra "sin saldos previos" con dos conexiones reales. Mutantes: confirmar
  sin bloquear el complejo; confirmar con diferencias sin aceptar; no pasar el estado a `confirmada`.
- [ ] 3.3 **Web.** `textoDeEstados.ts` (`confirmada`), el paso 7 del resumen (E12), botón "Confirmar
  saldos" y su estado; e2e de Playwright.

## 4. H-010 · Ajuste de saldo inicial

- [ ] 4.1 **Migración `0039_ajuste_de_saldo_inicial`.** Tabla de sólo agregar (FK compuesta a la
  obligación de su misma cuenta, motivo 1 a 500 no en blanco, `operacion_id` único por administración),
  acción `ajustar_saldo_inicial`. Matriz de mutantes de protección, ensayo de roles y barrido local.
- [ ] 4.2 **Caso de uso `ajustar_saldo_inicial`** (en `importacion.aplicacion` o `cuenta_corriente.
  aplicacion`, el que respete las fronteras; la obligación la crea `cuenta_corriente`). Obligación sin
  emisión (E11), cuenta creada si falta, `bloquear_cuentas`, `imputar_pendientes`, registro y auditoría,
  replay por `operacion_id`. Interés desde el día siguiente contra la emisión real. Mutantes: vencimiento
  retroactivo; sin motivo; permitir con la migración pendiente.
- [ ] 4.3 **Ruta y pantalla** (D11) con e2e de Playwright.

## 5. Cierre

- [ ] 5.1 **Fronteras, calidad y suite completa** en el CI de GitHub del PR del change (D-154), con
  conteo propio; KB al día (Knowledge Base Impact de `proposal.md`).
