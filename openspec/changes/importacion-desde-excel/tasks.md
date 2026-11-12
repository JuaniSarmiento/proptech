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

- [x] 1.1 **Módulo `importacion` y fronteras.** `backend/src/proptech_core/importacion/` (`dominio/`,
  `aplicacion/`, `adaptadores/`, `puertos.py`), `_DUENO_DE_TABLA` y la regla de importación permitida en
  `tests/unitarios/test_fronteras_de_modulos.py` (design D0). Mutante: `complejos` importando
  `importacion` → rojo en el test de ciclos.
  - **RED 1.1** (11/11/2026 20:45, antes de crear el módulo ni tocar `_DUENO_DE_TABLA`):
    `cd backend && uv run pytest tests/unitarios/test_fronteras_de_modulos.py -q -k importacion` →
    `10 failed, 66 deselected`. Cada rojo cae en su aserción: `assert 'importacion' in ['acceso',
    'complejos', 'cuenta_corriente', 'gastos']`; `assert None == 'importacion'` (`_DUENO_DE_TABLA`); y 8 veces
    `AssertionError: falta el módulo importacion` (ciclos x4, dominio vs `aplicacion` x3, SQL ajeno x1).
  - **Verde 1.1** (`39db12d`, 20:46): `tests/unitarios/test_fronteras_de_modulos.py` → `76 passed`.
  - **Mutante 1.1** (árbol real, archivos nuevos borrados después; `git status` limpio): `complejos/
    mutante.py` con `import proptech_core.importacion.aplicacion` e `importacion/mutante.py` con `import
    proptech_core.complejos.aplicacion` → `test_sin_ciclos_entre_modulos` rojo (`Left contains one more
    item: 'complejos → importacion → complejos'`) y `test_importacion_figura_entre_los_modulos_
    recorridos_y_nadie_lo_importa` rojo (`{'complejos': ['complejos/mutante.py']}`). Sólo la arista
    `complejos → importacion`: rojo en el segundo test. Además, `test_un_modulo_que_importa_importacion_
    cierra_un_ciclo[x4]` es el mismo mutante sobre una copia temporal, permanente.
- [x] 1.2 **Lector de la plantilla (adaptador).** `importacion/adaptadores/excel.py`: hojas y encabezados
  por nombre, 2 MiB y 2.000 filas, fórmulas por valor en caché y sin caché = error, celdas numéricas a
  `Decimal(repr())` en notación fija, fechas. Corregir el docstring de `gastos/adaptadores/excel.py` (D2
  del 6). Tests unitarios con archivos `.xlsx` armados en el test (`openpyxl`). Escenarios:
  importacion-de-padron "Columnas en otro orden", "Falta un encabezado", "No es un Excel", "Archivo
  enorme", "Fórmula sin valor en caché". Mutantes: leer por posición; `float()` sobre la celda; sin
  límite de bytes.
  - **RED 1.2** (11/11/2026 20:47, contra un lector provisorio que devuelve las tres hojas vacías):
    `cd backend && uv run pytest tests/unitarios/test_importacion_lector_excel.py -q` →
    `32 failed, 1 passed`. Leído en el traceback: todos caen en la aserción del propio test, ninguno en
    un helper (`IndexError` iniciales reescritos como `assert len(...)`): `assert () == ('Unidad', 'T...',
    'Email')` (encabezados, x5), `assert [] == ['0.000083']` y las otras 7 celdas numéricas, `assert 0 ==
    2000` (x2, límite de filas), `Failed: DID NOT RAISE ArchivoInvalido` (x6: csv, pdf, truncado, vacío,
    2 MiB, justo en el límite), `assert 'Unidades' not in {...}` (x3, nombre de hoja parecido), fórmula
    sin caché `assert [] == [(2, frozenset(), ...)]`. El único verde, `test_una_hoja_con_solo_encabezados_
    no_tiene_filas`, coincide con el provisorio (sin filas): no cuenta como RED.
  - **RED 1.2 bis** (11/11/2026 20:50): descubierto al escribir 1.3: un `0.125` numérico no puede
    tomarse por el texto ambiguo `1.234`. `FilaLeida.numericas` (campo con default vacío) y la prueba
    `test_se_distingue_la_celda_numerica_del_texto_con_el_mismo_aspecto`: `uv run pytest
    tests/unitarios/test_importacion_lector_excel.py -q` → `1 failed, 32 passed`; aserción: `assert
    [frozenset(), frozenset()] == [frozenset({'Coeficiente'}), frozenset({'Superficie m2'})]`.
  - D2 del 6 (L-066): `tests/unitarios/test_lector_de_planilla_excel.py` suma dos pruebas de caracterización
    del lector de gastos (fórmula con caché entra por su valor; sin caché entra vacía). Pasan antes y
    después: documentan lo que el docstring corregido promete, no son un RED.
  - **Verde 1.2** (`ab8e17f`, `ca57c88`): `test_importacion_lector_excel.py` + `test_lector_de_planilla_
    excel.py` → `33 passed` y `6 passed`.
  - **Mutantes 1.2** (copia previa en el scratchpad, uno a la vez, `diff` vacío contra la copia al
    revertir; cada uno rojo en la aserción que se esperaba): (1) leer por posición en vez de por nombre
    → `test_columnas_en_otro_orden_se_leen_igual` (`'Unidad' != 'Email'`); (2) `str(valor)` sobre la
    celda `float` → `['8.3e-05'] == ['0.000083']`; (3) `f"{float(valor):.6f}"` → `['0.000000'] ==
    ['0.0000001']`; (4) sin límite de bytes → `assert '2 MiB' in 'El archivo no es un Excel (.xlsx)
    válido'`; (5) límite `>=` en bytes → `test_justo_en_el_limite_de_bytes...`; (6) límite de filas `>`
    en vez de `==` → `DID NOT RAISE` en 2.001; (7) límite de filas `- 1` → falla en 2.000; (8) sin
    reconocer la fórmula (`data_type == "f"`) → `test_una_formula_sin_valor_en_cache_queda_marcada`;
    (9) fila con sólo fórmula tratada como en blanco → `assert [] == [2]`; (10) `numericas` siempre
    vacío / contando textos → `test_se_distingue_la_celda_numerica...`.
- [x] 1.3 **Validación del padrón (dominio puro).** `importacion/dominio/padron.py`: todo o nada con
  todos los errores (hoja, fila, columna, motivo), números (E14), unidad repetida, tipo, piso exacto del
  vocabulario, coeficiente, superficie, email, suma de coeficientes con la tolerancia de R01 (E4: fuera
  rechaza, dentro y distinta de 1 advierte). Escenarios de importacion-de-padron. Mutantes: devolver sólo
  el primer error; recortar el piso; redondear un coeficiente de 7 decimales; aceptar la suma 0,9998;
  rechazar la 0,9999.
  - **RED 1.3** (11/11/2026 20:53, contra `padron.py` y `numeros.py` provisorios: `validar_padron`
    devuelve un padrón vacío sin rechazar nada y `leer_decimal` devuelve 0): `cd backend && uv run pytest
    tests/unitarios/test_importacion_padron.py -q` → `134 failed, 3 passed`. Por causa: `Failed: DID NOT
    RAISE PadronInvalido` x75, `AssertionError: el padrón válido no devolvió todas sus unidades` x27
    (aserción del helper `_aceptado`, explícita y propia del test, no un error de setup), `Failed: DID NOT
    RAISE NumeroInvalido` x19, `assert Decimal(0) == <esperado>` x13. Los 3 verdes
    (`test_edificio_con_unidades_acepta_un_archivo_sin_padron[...]`) coinciden con el provisorio, que
    acepta todo: no valen como RED; los cubre el mutante "edificio con unidades exige la hoja".
  - **Verde 1.3** (`ec37459`): `test_importacion_padron.py` → `137 passed`; con el lector y las fronteras,
    `252 passed`. `tests/unitarios` entero (por si otro test recorre el árbol) → `2614 passed`.
  - **Mutantes 1.3** (copia previa, uno a la vez, restaurado y `diff` vacío; rojo donde se esperaba):
    (1) devolver sólo el primer error → `test_varios_errores_juntos_en_el_orden_del_archivo`
    (`Right contains one more item: ('Unidades', 7, 'Superficie m2')`); (2) recortar el piso →
    `test_piso_fuera_del_vocabulario_o_con_espacios_no_se_recorta[ PB]` (`DID NOT RAISE`); (3) redondear
    el coeficiente de 7 decimales → `test_numero_invalido_desde_texto_nunca_se_redondea[0.0833333-6]`;
    (4) aceptar la suma 0,9998 (tolerancia 0,0002 a mano) → `..._fuera_de_la_tolerancia_...[0.083137-
    0,9998]` (`DID NOT RAISE`); (5) rechazar la 0,9999 (`estado != "ok"`) → `test_suma_dentro_de_la_
    tolerancia_distinta_de_uno_advierte[0.083237-0,9999]`; (6) edificio con unidades exige la hoja →
    `..._acepta_un_archivo_sin_padron[sin_hoja]`; (7) sin chequeo de ambiguo → `[1.234-6]`; (8) la celda
    numérica también ambigua → `test_una_celda_numerica_no_es_ambigua[0.125-0.125]`; (9) duplicado sin
    recortar → `test_una_unidad_repetida_se_detecta_aun_con_espacios_en_el_borde`; (10) informar la
    suma con errores de fila → `test_un_solo_error_nombra_hoja_fila_columna_y_motivo` (el primero en caer
    con `-x`: `assert ('Unidades', None, 'Coeficiente') == ('Unidades', 9, 'Piso')`).
  - Linters al cierre: `uv run ruff check .` (All checks passed), `uv run ruff format --check .`,
    `uv run mypy` (`Success: no issues found in 411 source files`).
- [x] 1.4 **Migración `0036_importacion`.** Tabla `importacion` (D5) con RLS forzada, FK compuestas a
  `complejo` y `persona`, único parcial de un `borrador` por edificio, único de huella por edificio; las
  acciones `importar_padron_y_saldos` en `Accion`, en la matriz (E6) y en `accion_de_auditoria`. Tests de
  esquema, de aislamiento y de cabeza (L-082: el test prueba la `0036`, no "la última").
  - **RED 1.4** (11/11/2026, antes de escribir la migración y el vocabulario): `cd backend && uv run pytest
    tests/integracion/test_migracion_0036_importacion.py tests/unitarios/acceso/test_permisos.py -q`. La
    migración: `14 failed, 1 passed` (el verde es `test_no_es_de_solo_agregar`, cierto antes y después). Por
    causa: `AssertionError: falta la tabla importacion (0036)` / `assert [(False,)] == [(True,)]` x8, `falta la
    migración 0036` x1, `assert [] == [columnas...]` x1 y `assert [] == [('importar_padron_y_saldos',)]` x2
    (vocabulario). Permisos: `test_la_matriz_de_prueba_cubre_exactamente_el_vocabulario` falla por aserción
    (la fila nueva de la tabla a mano no está en `Accion`) y 19 celdas de la matriz fallan con `ValueError:
    'importar_padron_y_saldos' is not a valid Accion` (el miembro que falta es justo lo que se prueba).
- [x] 1.5 **Caso de uso `importar` (padrón).** Permiso, tenant, `FOR UPDATE` del complejo, estado
  `pendiente`, validación completa antes de escribir, una sola lectura del padrón, `crear_unidad` por
  fila, grupo general, propietarios sin invitar (E3), padrón existente (E7), misma huella → conflicto,
  auditoría. Integración contra PostgreSQL real. Mutantes: escribir antes de validar todo; invitar al
  propietario; no bloquear el complejo.
  - **Decisión de la tanda 2** (el relevo de 1.3 la dejó abierta): un email repetido en dos filas con otro
    nombre es la misma persona; se conserva el nombre de la primera fila y la segunda suma una advertencia
    (hoja `Unidades`, su fila, columna `Propietario`; el motivo nombra la fila anterior y no repite el
    email). No es error: el contrato dice que el mismo email es la misma persona.
  - **RED 1.5** (11/11/2026, contra `importar` y `agrupar_propietarios` provisorios que no escriben nada y
    devuelven un resultado en cero; `ArchivoYaImportado` y `SinPermiso` son reales): `cd backend && uv run
    pytest tests/unitarios/test_importacion_propietarios.py tests/unitarios/test_fronteras_de_modulos.py
    tests/integracion/test_importar_padron.py -q`. Unitarios: 3 de 4 de propietarios fallan por aserción
    (`assert {} == {'uno@...': 'Persona Ficticia Uno'}`) y 1 de fronteras (`importar.py` todavía no importa
    `complejos.aplicacion` ni `acceso.aplicacion`). Integración: `36 failed` de 36. Por causa: `assert 0 ==
    12` x7 (el resultado en cero), `Failed: DID NOT RAISE` (SinPermiso x3, PadronInvalido x3, NoEncontrado
    x2, EntradaInvalida x2, Conflicto x2, ArchivoYaImportado x1, ArchivoInvalido x1), `assert (0, 0) == (9, 1)`
    y `(2, 0) == (1, 1)` (la carrera: las dos "ganan"), `el padrón se leyó 0 veces`, y los que miran la tabla
    `importacion` (`UndefinedTable` x8: la tabla es lo que falta; el mundo ya se sembró y el caso de uso ya
    corrió, así que no es un error de armado del test).
  - **Verde 1.4 y 1.5** (`2627ed8`): migración 15/15; `test_importar_padron.py` 36/36; propietarios, permisos y
    fronteras `1221 passed` (unitarios enfocados); `test_auditoria_transaccion.py` (barrido de casos sensibles con
    el invocador nuevo), `test_vocabulario_configuracion.py`, `tests/infra/test_ensayo_login.py`,
    `test_libro_rollback.py` y `test_conmutar_politicas_reales.py` (cabeza `0036`): `28 passed` + `3 passed`.
    **Barrido local de migraciones** (D-154, L-083; `uv run pytest -q $(rg -l "downgrade|\.migrar\(|alembic.*(up|down)grade|pg_restore" tests/integracion)`):
    `1330 passed in 575s`. `ruff check`, `ruff format --check` y `mypy` limpios.
  - **Mutantes 1.5** (sobre `2627ed8`, uno a la vez, restaurado con `git status` limpio; rojo donde se esperaba):
    (1) sin savepoint y registrando la importación antes de validar → `test_doce_unidades...` `assert (2 - 0) == 1`
    (la importación se escribió dos veces); (3) sin `FOR UPDATE` → `test_dos_importaciones_simultaneas...` (las dos
    "ganan"); (4) leer el padrón por fila → `test_el_padron_se_lee_una_sola_vez` (13 lecturas); (5) sin permiso →
    `DID NOT RAISE SinPermiso`; (6) sin chequeo de huella → `test_el_mismo_archivo_dos_veces...`; (7) no descartar el
    borrador → `uq_importacion_un_borrador`; (8) sin chequeo de estado → `DID NOT RAISE Conflicto`; (9) `reusadas`
    cuenta emails repetidos → `assert (9, 1) == (9, 0)`; (10) insertar una invitación por propietario →
    `AssertionError: importar no invita (E3)`. (Los primeros intentos de 6, 7 y 10 eran mutantes mal armados, error de
    sintaxis o de columna, y se descartaron: no cuentan.)
  - **Aceptación de H-007 contra `HEAD`** (`aceptar.py --codigo HEAD --sin-regresion --sin-navegador`): `87 ejecutados,
    3 pasados, 84 fallas, 0 errores, 0 skips`. Los 84 son `404 Not Found` de la ruta, que es de 1.6; pasan los 3 que no
    la necesitan (ciclo de la `0036`, RLS forzada, acción y matriz de E6). C19 (KB) queda para el cierre del change.
- [x] 1.6 **Ruta y pantalla.** `POST /api/complejos/{id}/importaciones` (multipart: archivo y fecha de
  migración) con 422 `{"detail": [{hoja, fila, columna, motivo}]}`, en `_RUTAS_CUBIERTAS`; descarga de la
  plantilla; pantalla `edificios/[id]/importar` (D11) con sus estados y e2e de Playwright (archivo válido,
  archivo con errores, sin permiso).
  - **RED 1.6** (11/11/2026, `python3 aceptacion/H-007/aceptar.py --codigo HEAD --sin-regresion`, HEAD `fdaf4e4`, sin la
    ruta ni la pantalla): `H-007.TESTS FALLA 87 ejecutados, 3 pasados, 84 fallas, 0 errores, 0 skips` (los 84 son
    `AssertionError: se esperaba 201/422/409/403, llegó 404 {"detail":"Not Found"}` o `la plantilla no se descarga: 404`)
    y `H-007.E2E FALLA 4 esperados; 4 ejecutados, 0 pasados, 4 fallas, 0 errores`; el propio `aceptar.py` informa
    `que no son por aserción (0)`: los cuatro e2e fallan en el `expect` del encabezado `Importar desde Excel` (la
    pantalla no existe). Los tests de componente y de cliente de la web se escribieron junto con el código; se validan
    con mutantes (ver abajo), no con un rojo previo: lo anoto como desvío del método.
  - **Verde 1.6** (`0270d62` y el test estructural siguiente): `aceptar.py --codigo HEAD` con regresión: TESTS 87/87, C01 a C15, C17 y
    C20 PASAN; E2E 3 de 4: **C16 (e2e) FALLA por el contrato, no por la pantalla**: el spec usa `getByRole("alert")` sin acotar y
    Next trae su propio `role="alert"` (`__next-route-announcer__`), así que Playwright da `strict mode violation: resolved to 2
    elements` (el 1 es nuestro "Resumen de errores", con el texto exacto). Se propone acotar el locator (ver relevo) y re-congelar.
    Tests de la web: vitest completo `617 passed` antes del route test (+`route.test.ts`), biome ci, tsc, ruff, format y mypy limpios;
    `test_rutas_protegidas.py` 613 passed; `test_altas_sin_id_del_cliente.py` 15 passed (el barrido de migraciones lo había marcado).
  - **Mutantes 1.6** (copia previa, restaurados): el 422 nunca es `rechazado` (`every(...)` -> `false`) y no mostrar los
    propietarios reusados -> fallan `importaciones.test.ts` (422 de archivo) y `Pantalla.test.tsx` (aceptada), 2 de 25.

## 2. H-008 · Borrador de saldos y comparación

- [x] 2.1 **Validación de `Saldos` y `Control` (dominio).** Contrato del saldo inicial (E11 y E16 del 4c),
  números, mezcla de detalle y total, unidad inexistente, vencimientos, crédito. Escenarios de
  borrador-de-saldos. Mutantes: aceptar un vencimiento posterior a la migración; aceptar dos vencimientos
  en un período.
  - **RED 2.1** (11/11/2026 22:07, contra un `validar_saldos` provisorio que devuelve `(None, ())`, es decir "no hay
    saldos"): `cd backend && uv run pytest tests/unitarios/test_importacion_saldos.py -q` -> `68 failed, 2 passed`. Cada
    rojo cae en una aserción de los helpers del propio test (no en armado): `AssertionError: se esperaban errores y el
    archivo se aceptó` x49 (todos los casos de rechazo) y `AssertionError: un archivo válido con saldos devolvió un
    borrador vacío` x19 (todos los de aceptación). Los 2 verdes (`sin saldos ni Control` y `las hojas de la plantilla
    descargada sin filas`) coinciden con el provisorio, que no devuelve nada: no valen como RED; los cubre el mutante
    "hojas vacías cuentan como borrador".
  - **Verde 2.1** (`dae84b6`): `uv run pytest tests/unitarios/test_importacion_saldos.py -q` -> `71 passed` (el último, la mezcla
    marcada una sola vez, se sumó después del RED para matar el mutante 12).
  - **Mutantes 2.1** (copia previa, uno a la vez, restaurado con `diff` vacío; rojo donde se esperaba): (1) vencimiento
    posterior a la migración aceptado -> `[vencimiento_posterior_a_la_migracion]` (`un archivo con errores no devuelve
    borrador`); (2) dos vencimientos en un período aceptados -> `test_dos_vencimientos_en_el_mismo_periodo_error_en_la_segunda_fila`;
    (3) sólo el primer error -> `test_importe_o_control_que_no_entran_en_numeric_14_2` (y `todos_los_errores_juntos`); (4) sin el
    chequeo de capital 0 -> `test_periodo_con_capital_cero_y_solo_interes`; (5) capital 0 medido por fila y no por período ->
    `test_periodo_con_capital_cero_se_suma_por_periodo_no_por_fila`; (6) sin el chequeo de mezcla -> `test_unidad_que_mezcla_detalle_y_total`;
    (7) el crédito cuenta en la mezcla de modos -> `test_el_credito_no_cuenta_en_la_mezcla_de_modos`; (8) hojas vacías devuelven
    un borrador vacío -> `test_las_hojas_de_la_plantilla_descargada_sin_filas_no_son_un_borrador`; (9) crédito guardado negativo ->
    `test_un_archivo_valido_devuelve_sus_filas_ya_tipadas` (`el crédito se guarda positivo`); (10) período posterior al mes de la
    migración aceptado -> `[periodo_posterior_al_mes_de_migracion]`; (11) unidad repetida en `Control` aceptada ->
    `test_control_con_unidad_repetida_nombra_la_otra_fila`; (12) la mezcla se marca en todas las filas que difieren, no sólo en la
    primera -> sobrevivió a los 70 tests de la primera tanda; se sumó `test_la_mezcla_se_marca_una_sola_vez_por_unidad` y ahora
    cae en `assert {('Saldos', 3, 'Período'), ('Saldos', 4, 'Período')} == {('Saldos', 3, 'Período')}`.
- [x] 2.2 **Migración `0037_borrador_de_saldos`.** `fila_de_saldo_importada`, `control_de_saldo`,
  `aceptacion_de_diferencias` (de sólo agregar, en `TABLAS_DE_SOLO_AGREGAR`) y la acción
  `aceptar_diferencias_de_saldos`. Matriz de mutantes de protección como la `0034`; ensayo de roles y
  barrido local de migraciones (L-083).
  - **RED 2.2** (11/11/2026, antes de escribir la migración, el `Accion` nuevo y la tabla protegida):
    `cd backend && uv run pytest tests/integracion/test_migracion_0037_borrador_de_saldos.py
    tests/integracion/test_migracion_0037_baja_y_sube.py -q` -> `64 failed, 0 passed`. Cada rojo es una aserción del propio
    test, ninguno de setup (la comprobación de que las tablas existen vive en cada test, no en el fixture): `AssertionError:
    falta la tabla <tabla> (0037)` x60 (`assert [(False,)] == [(True,)]`), `falta la migración 0037` x1, y las del
    vocabulario `la 0037 no cargó la acción en el vocabulario` x1 y `Right contains one more item:
    ('aceptar_diferencias_de_saldos',)` x2. Permisos: `uv run pytest tests/unitarios/acceso/test_permisos.py -q` ->
    `20 failed, 1136 passed`: `test_la_matriz_de_prueba_cubre_exactamente_el_vocabulario` falla por aserción (la fila nueva
    de la matriz a mano no está en `Accion`) y 19 celdas con `ValueError: 'aceptar_diferencias_de_saldos' is not a valid
    Accion` (el miembro que falta es justo lo que se prueba).
  - **Verde 2.2** (`7725804`; la FK a `complejo` que pide el guardián del catálogo, en el mismo commit): `uv run pytest
    tests/integracion/test_migracion_0037_borrador_de_saldos.py tests/integracion/test_migracion_0037_baja_y_sube.py
    tests/integracion/test_catalogo_rls.py tests/unitarios/acceso/test_permisos.py -q` -> todo verde (89 de migración y catálogo, 1.195 de permisos). Tests
    viejos que fijaban la cabeza o no devolvían la tabla protegida nueva (L-064, L-082, L-083; ningún id cambia de nombre):
    `test_libro_rollback` (cabeza `0037` y `POSTERIORES_AL_LIBRO`), `test_conmutar_politicas_reales` (la cabeza del `alembic heads`
    falso), `test_catalogo_rls` (`_SONDA_SIN_FILA`), `test_vocabulario_configuracion` (la 0037 no importa `Accion` y la acción sale del
    vocabulario al bajar a la `0004`), `test_migracion_0036_importacion` (`devolver_tablas_protegidas()` antes de bajar, porque ahora
    la `0037` baja primero) y `infra/ci/ensayo-roles.sh` (la tabla en la lista de filas y su `OWNER TO`).
    **Primer barrido** (`uv run pytest -q $(rg -l "downgrade|\.migrar\(|alembic.*(up|down)grade|pg_restore" tests/integracion)` +
    ensayo de login, fronteras y vocabulario): `1442 passed, 2 failed` en `test_catalogo_rls` (el guardián pedía la FK compuesta
    `(administracion_id, complejo_id) -> complejo` en las tres tablas: no la tenían, sólo la de `importacion`); se agregó en la `0037`
    y el test de FK quedó con `complejo` en su lista.
  - **Mutantes 2.2** (copia previa, restaurado; rojo donde se esperaba): `control_de_saldo` sin `FORCE ROW LEVEL SECURITY` ->
    `test_rls_forzada_con_su_politica[control_de_saldo]`; FK de la unidad sin el edificio -> `test_las_claves_foraneas_son_compuestas...`;
    sin el único de una aceptación por importación -> `test_hay_una_sola_aceptacion_por_importacion`; sin el CHECK de forma ->
    `[credito_con_periodo]`; sin el CHECK de crédito sin interés -> `[credito_con_interes]`; sin el CHECK de diferencias no vacías ->
    `[[]]`; sin la acción en el vocabulario -> `test_la_accion_esta_en_el_vocabulario_de_auditoria`; bajada que no mira
    `fila_de_saldo_importada`, `control_de_saldo` o `aceptacion_de_diferencias` (tres mutantes) -> `test_no_baja_con_filas` (`DID NOT
    RAISE AssertionError`); `aceptacion_de_diferencias` fuera de `TABLAS_DE_SOLO_AGREGAR` -> `test_permisos_de_la_app` (la app
    conserva `UPDATE`/`DELETE`); matriz con el administrador por edificio -> `test_matriz_entera_con_cada_celda_distinta_en_el_mensaje`
    (`aceptar_diferencias_de_saldos/AE: True != False`). **Triggers**: sacar uno de los tres de la aceptación **no cae en
    `test_trigger_por_fila_...` ni `test_trigger_por_sentencia_sin_filas`** sino antes, en el paso `roles despues`, que sondea por
    el efecto y lo rechaza (`la protección de aceptacion_de_diferencias no se pudo confirmar: admite TRUNCATE`; con el trigger de fila,
    tras sacarlo también de la declaración, cae en `test_solo_la_aceptacion_esta_declarada_de_solo_agregar`). Defensa doble: los
    tests de triggers quedan de segunda línea; no se demostró que caigan solos porque el guardián los tapa.
- [x] 2.3 **Borrador y comparación (aplicación).** Guardar el borrador en la misma subida, descartar el
  anterior, sin tocar el libro; comparación por unidad con totales, signo opuesto, aviso de mes entero
  (E13). Mutantes: comparar sólo totales; sumar el crédito en vez de restarlo.
  - **RED 2.3 y 2.4** (11/11/2026 22:30, contra `comparar_saldos`, `aviso_de_mes_entero`, `comparar_borrador` y
    `aceptar_diferencias` provisorios que devuelven una comparación vacía y una aceptación sin escribir nada, y contra el
    `importar` de H-007 que todavía no guarda `Saldos` ni `Control`; `aceptar_diferencias` ya está marcado con
    `@accion_sensible` para que el barrido de auditoría lo vea): `cd backend && uv run pytest
    tests/unitarios/test_importacion_comparacion.py tests/integracion/test_borrador_de_saldos.py
    tests/integracion/test_comparacion_de_saldos.py tests/integracion/test_aceptar_diferencias.py
    tests/integracion/test_auditoria_transaccion.py -q` -> `59 failed, 19 passed` (los 19 son 6 del barrido de auditoría
    ya existentes y 13 nuevos que coinciden con el provisorio, listados abajo). Por causa, todas aserciones del test: `Failed:
    DID NOT RAISE` x21 (`NoEncontrado` x8, `SinPermiso` x5, `Conflicto` x5, `PadronInvalido` x3: ni autoriza ni rechaza),
    `assert '' == 'El primer interés del sistema cubre ...'` x5 (el aviso), `assert {} == {...}`/`assert set() == {...}`
    sobre las unidades y las diferencias de la comparación y de la aceptación (el cuerpo vacío), `assert ('0.00', '0.00') ==
    ('320000.00', '320000.00')` (totales), `assert 0 == 7` (`filas_de_saldo`) y `assert 0 == 1` (la aceptación no escribe), y
    `AssertionError: aceptar_diferencias_de_saldos: se esperaba 1 fila de auditoría, hay 0` (el barrido). Un primer intento de
    estos tests fallaba con `KeyError`/`IndexError` sobre el resultado vacío (error de acceso, no de aserción): se reescribieron
    con `.get` y comparaciones de listas antes de dar el rojo por bueno. Los 13 verdes que no cuentan como RED, porque el
    provisorio o el `importar` actual ya los cumplen: `test_sin_filas_ni_control_la_comparacion_esta_vacia`,
    `test_el_borrador_no_toca_el_libro`, `test_la_auditoria_de_importar_sigue_siendo_una_sola`, `test_un_archivo_sin_saldos_no_deja_borrador`,
    `test_las_hojas_de_la_plantilla_descargada_sin_filas_no_son_un_borrador`, `test_el_mismo_archivo_de_saldos_dos_veces_es_conflicto`,
    `test_las_unidades_del_padron_con_error_igual_sirven_para_ubicar_los_saldos`, `test_proporcional_por_dia_no_avisa`,
    `test_sin_version_de_configuracion_no_avisa`, `test_vale_la_version_vigente_a_la_fecha_de_migracion_no_la_de_hoy`,
    `test_los_que_pueden_aceptar[super_admin|principal]` y `test_la_hora_de_la_aceptacion_es_la_del_reloj_con_zona`; los cubren los
    mutantes de la implementación (ver más abajo).
  - **Verde 2.3** (`e02474c`): `uv run pytest tests/unitarios/test_importacion_comparacion.py tests/unitarios/test_importacion_saldos.py
    tests/unitarios/test_fronteras_de_modulos.py tests/integracion/test_borrador_de_saldos.py tests/integracion/test_comparacion_de_saldos.py
    tests/integracion/test_aceptar_diferencias.py tests/integracion/test_auditoria_transaccion.py tests/integracion/test_importar_padron.py -q`
    -> `264 passed`. `importar` (H-007) valida `Unidades`, `Saldos` y `Control` y rechaza todo junto (un `PadronInvalido` con los errores de
    las tres hojas, en orden de hoja y fila) antes de escribir nada; guarda el borrador con `executemany`; `comparar_borrador` exige el
    permiso de importar (supuesto, ver relevo).
  - **Mutantes 2.3** (copia previa, restaurado; con `PYTHONDONTWRITEBYTECODE` y sin `.pyc` del archivo mutado: un par de mutantes del
    mismo tamaño dejó un `.pyc` viejo y dio una salida repetida, se rehicieron): comparar sólo totales (`unidades_con_diferencia` por
    totales) -> `test_dos_errores_de_signo_opuesto_coinciden_en_el_total_pero_no_por_unidad`; sumar el crédito en vez de restarlo ->
    `test_borrador_es_capital_mas_interes_menos_credito`; ignorar el control sin saldo -> `test_una_unidad_con_control_y_sin_saldo_y_al_reves`;
    no sumar el interés importado -> el mismo; deuda por interés -> `test_con_deuda_es_capital_mayor_que_cero_no_interes_ni_credito`;
    mes corrido -> `test_el_aviso_nombra_el_mes_de_la_migracion_en_minuscula`; diferencia invertida -> `test_dos_errores_de_signo_opuesto...`;
    total de control mal sumado -> `test_totales_y_cantidad_de_diferencias`; aviso sin mirar la forma de cálculo -> `test_proporcional_por_dia_no_avisa`;
    aviso a quien sólo tiene crédito -> `test_mes_entero_avisa_el_mes_de_la_migracion_a_las_unidades_con_deuda`; versión de otra fecha ->
    `test_vale_la_version_vigente_a_la_fecha_de_migracion_no_la_de_hoy`; permiso de comparar distinto -> `test_el_administrador_del_edificio_puede_ver...`
    y `test_sin_permiso_de_importar_no_ve_los_saldos[contador]`; guardar sin controles o sin filas -> `test_la_subida_guarda_las_filas_de_saldo_y_el_control`;
    no rechazar los errores de `Saldos` -> `test_una_fila_de_saldos_mala_rechaza_todo_incluido_el_padron`; sólo el primer grupo de errores ->
    `test_los_errores_del_padron_y_de_saldos_van_juntos`; sin `identificadores_declarados` -> el mismo y
    `test_las_unidades_del_padron_con_error_igual_sirven_para_ubicar_los_saldos`. No se hizo mutante de "el borrador toca el libro": nada del
    borrador escribe en `cuenta`, `obligacion` ni `movimiento` y `test_el_borrador_no_toca_el_libro` mira los conteos, pero no se lo vio
    fallar.
- [x] 2.4 **Aceptar diferencias.** Permiso (E6), registro exacto de las diferencias, auditoría, la
  aceptación deja de valer con un borrador nuevo. Mutante: aceptar sin guardar la lista.
  - **Verde 2.4** (`e02474c`, `d47d068`): los mismos 264 + el candado medido con `FOR NO KEY UPDATE NOWAIT` (el `FOR UPDATE NOWAIT` no
    distinguía: la FK de la aceptación toma un `KEY SHARE` que lo frena igual). **Barrido final** (el de las migraciones de arriba más
    los tests de esta tanda y la matriz de permisos): `2843 passed in 590s`. `ruff check`, `ruff format --check` y `mypy` limpios.
  - **Mutantes 2.4** (copia previa, restaurado): sólo la primera diferencia guardada -> `test_aceptar_registra_quien_cuando_y_la_lista_exacta`; sin chequeo
    de estado -> `test_con_la_migracion_cerrada[confirmada]`; sin chequeo de borrador vigente -> `test_una_importacion_que_no_es_el_borrador_vigente`;
    sin chequeo de aceptación previa -> `test_aceptar_dos_veces` (cae con `UniqueViolation` del único de la base, no con `Conflicto`); sin
    `FOR UPDATE` -> `test_aceptar_toma_el_candado_del_complejo` y `test_dos_aceptaciones_simultaneas_una_gana` (`(1, 0) == (1, 1)`); permiso de
    importar en vez del de aceptar -> `test_sin_el_permiso_de_aceptar[de_la_torre]`; sin auditoría -> `test_aceptar_audita_una_vez...` y el
    barrido de auditoría; todas las unidades en la lista -> `test_solo_se_guardan_las_unidades_con_diferencia`; hora del servidor en vez del
    reloj -> `test_aceptar_registra_quien_cuando_y_la_lista_exacta`.
  - **Aceptación de H-008 contra `HEAD`** (`python3 aceptacion/H-008/aceptar.py --codigo HEAD --sin-regresion --sin-navegador`, `d47d068`): `58
    ejecutados, 32 pasados, 26 fallas, 0 errores, 0 skips`; el propio script informa `que no son por aserción (0)`. Pasan C01 a C04 (el borrador y el
    libro), C13 y C14 (rechazos) porque la ruta de subir ya existe. Fallan por `404 Not Found` de las dos rutas nuevas, que son de la tanda 2:
    C05 a C11 y C15 (comparación y aceptar) y la parte de C16 que aceptar; C12 y los e2e no corrieron (`--sin-navegador`); C17 (la KB) queda
    para el cierre del change; C18 cae con C05 a C10.

- [x] 2.5 **Rutas y pantalla de comparación** (D11) con e2e de Playwright (diferencias visibles aunque el
  total coincida, aceptar, aviso de mes entero).
  - **RED 2.5** (11/11/2026 23:10; la ruta `GET .../importaciones/comparacion` y la `POST .../aceptacion-de-diferencias` todavía no
    existen, así que el rojo es un `404 Not Found` de FastAPI contra lo que cada test espera; en la web, stubs que compilan y
    devuelven lo equivocado: `dinero` y `fechaYHora` devuelven el texto tal cual, `comparacionDelBorrador` y `aceptarDiferencias`
    devuelven `fallo`, la pantalla no dibuja nada y la acción devuelve `null`):
    - Backend: `cd backend && uv run pytest tests/integracion/test_rutas_protegidas.py tests/integracion/test_altas_sin_id_del_cliente.py
      tests/integracion/test_importaciones_comparacion_api.py -q` -> `41 failed, 629 passed`. Por causa, todas aserciones: `assert 404 ==
      200/201/403/409/422/401` (35 + 18 + 5 + 5), `AssertionError: {"detail":"Not Found"}` / `!= {"detail": "no encontrado"}` (el cuerpo
      de las 404 de las rutas inexistentes no es el de `NoEncontrado`), y los barridos que exigen las rutas cubiertas (`cubiertas pero ya
      no existen`, `no depende de identidad_actual`, `sin identidad da 401`). Un primer intento de
      `test_despues_de_aceptar_la_comparacion_muestra_la_aceptacion_y_ya_no_pide_aceptar` fallaba con `KeyError: 'requiere_aceptacion'` (acceso
      al cuerpo de un 404): se reescribió con el `assert status_code` antes de leer el cuerpo.
      Nuevo `test_importaciones_comparacion_api.py` (19 tests, por HTTP con identidad inyectada y RLS real, subiendo el borrador por la ruta real
      de H-007), las dos rutas sumadas a `_RUTAS_CUBIERTAS` (con su cuerpo en `_pedido`) y a `_CUERPOS_DE_PRUEBA` del barrido de altas sin id.
    - Web: `npx vitest run src/lib/formato.test.ts src/lib/api/importaciones.test.ts "src/app/edificios/[id]/importar/comparacion"
      e2e/api-falsa.comparacion.test.ts` -> `5 failed` archivos, `47 failed | 26 passed`; todo `AssertionError` (`expected null not to be null`
      de la pantalla, `expected { estado: 'fallo' } to deeply equal ...`, `expected 404 to be 200` de la API falsa, `expected '169000.00' to be
      '169.000,00'`). Dos primeros intentos fallaban por un error de acceso (`SyntaxError: Unexpected end of JSON input` al leer el cuerpo de un 404 y
      `TestingLibraryElementError` de `getByRole`): se reescribieron con `expect` sobre el estado y sobre `queryBy` antes de dar el rojo por bueno.
      Los 26 que pasan son los tests que ya existían en `formato.test.ts` e `importaciones.test.ts` y los pocos nuevos que coinciden con un stub (`fechaYHora` de un texto que no es fecha, 404 del edificio fuera del contrato en la API falsa): no cuentan como RED.
  - **Verde 2.5** (`fdcb3b4`, `99eb6be`): `cd backend && uv run pytest tests/integracion/test_rutas_protegidas.py tests/integracion/test_altas_sin_id_del_cliente.py
    tests/integracion/test_importaciones_comparacion_api.py tests/integracion/test_identidad_antes_del_cuerpo.py
    tests/integracion/test_regresiones_de_aislamiento_y_grupos_vacios.py tests/integracion/test_borrador_de_saldos.py
    tests/integracion/test_comparacion_de_saldos.py tests/integracion/test_aceptar_diferencias.py -q` -> `767 passed`. `ruff check`, `ruff format --check` y `mypy src`
    limpios. Web: `npx vitest run "src/app/edificios/[id]/importar" src/lib e2e` -> `35 files, 358 passed` (antes de la región enfocable; `Pantalla.test.tsx` de la
    comparación quedó en 16), `biome ci` sin errores, `tsc --noEmit` limpio. Playwright en un clon temporal del commit (`next build`, API falsa, `next start`): los 4
    e2e congelados de la aceptación (`aceptacion-h008-comparacion.spec.ts`, C12 y C15) y mi `comparacion-de-saldos.spec.ts` (axe en navegador real, sin desborde y
    teclado de la confirmación, a 320 y 1280 px) -> `10 passed`. La primera corrida de mi spec dio rojo de verdad: a 320 px axe encontró `scrollable-region-focusable` en la
    caja de la tabla (sin controles adentro, el teclado no llega a su desplazamiento) -> la caja es ahora una región enfocable (`99eb6be`, con su test de jsdom); y el
    test del teclado asumía que el foco no sale del diálogo, pero el `PanelLateral` incluye el "?" de la ayuda a propósito en su trampa de foco (corregido en el spec).
  - **Hallazgo fuera de la 2.5** (arreglado): `test_regresiones_de_aislamiento_y_grupos_vacios::test_super_admin_de_otra_administracion_no_alcanza_nada_de_a` estaba
    rojo desde H-007 (la ruta multipart de subir recibía un JSON y daba 422 en lugar del 404 del aislamiento) y las dos rutas nuevas lo habrían roto igual: se le sumó el cuerpo
    de aceptar y la rama multipart de subir. Ningún id de test cambió.
  - **Mutantes 2.5** (copia previa, uno a la vez, restaurado, con `PYTHONDONTWRITEBYTECODE`): backend (`test_importaciones_comparacion_api.py`): `requiere_aceptacion` fijo en
    `True` -> `test_despues_de_aceptar_la_comparacion_muestra_la_aceptacion_y_ya_no_pide_aceptar`; aceptar con 200 -> `test_aceptar_da_201_con_la_lista_y_deja_una_fila_y_una_auditoria`;
    cuerpo sin `extra="forbid"` -> `test_aceptar_con_un_campo_de_mas_es_422_nombrandolo`; borrador y control intercambiados -> `test_la_comparacion_da_las_unidades_los_totales_y_lo_que_falta_aceptar`;
    sin devolver la aceptación vigente -> el mismo de "después de aceptar". **Sobrevive: aceptar sin `sesion.commit()` en la ruta** (19 pasan): `aceptar_diferencias` ya cierra su
    transacción con `begin()` (la sesión de la ruta no tiene una abierta), así que el `commit` de la ruta es redundante; se dejó por consistencia con las demás rutas. Web: sin el
    gate del permiso -> `sin el permiso de aceptar no hay botón...`; cancelar sin devolver el foco -> `aceptar abre una confirmación...`; sin columna de avisos -> `el aviso de mes
    entero va dentro de la fila...`; la confirmación abierta tras aceptar -> `confirmar manda el importacion_id...`; `importacion_id` fijo -> el mismo; sin mostrar la aceptación que ya venía
    -> `una aceptación que ya venía...`; siempre plural -> `cero y una diferencia...`; sin `tabIndex` en la caja de la tabla -> `la tabla se desplaza dentro de una región...`; la acción sin
    `revalidatePath`, el 403 como error genérico y el 409 de aceptación sin su texto -> `acciones.test.ts`; sin validar los montos de las unidades, mandando más campos, sin validar el
    id de importación -> `importaciones.test.ts`; `dinero` sin signo y `fechaYHora` en UTC -> `formato.test.ts`; la API falsa con el 803 aceptando y el 802 con diferencias ->
    `api-falsa.comparacion.test.ts`; el resumen de importar sin el enlace -> `Pantalla.test.tsx` de importar. **Sobrevivió y se arregló el test**: el total de control mostrado como el del borrador
    (la fixture tenía los dos totales iguales, justo el caso de H-008): se sumó `cada total va con su rótulo cuando los dos son distintos`, y entonces dio rojo.
  - **Mutante que faltaba de la tanda 1 (el borrador escribe en el libro)** (copia previa de `borrador.py`, uno a la vez, en `guardar_borrador`, restaurado): insertar una `cuenta` ->
    `test_el_borrador_no_toca_el_libro` rojo por aserción (`assert (1, 0, 0) == (0, 0, 0)`); una `cuenta` con una `obligacion` válida -> `(1, 1, 0) == (0, 0, 0)`; una `cuenta` con un
    `movimiento` válido (`saldo_inicial`) -> `(1, 0, 1) == (0, 0, 0)`. Los primeros intentos con una `obligacion` o un `movimiento` sueltos cayeron por restricciones de la base
    (`CheckViolation`, `ForeignKeyViolation`), no por la aserción: se rehicieron con su cuenta y los campos que las restricciones piden hasta que el rojo fue el del test. No se mutó
    `carga_de_saldo_inicial` (tabla de H-009), que el test también cuenta.
  - **Aceptación de H-008 contra `HEAD`** (`python3 aceptacion/H-008/aceptar.py --codigo HEAD`, `99eb6be`, aceptación `4c3525e`): `58 ejecutados, 58 pasados, 0 fallas,
    0 errores, 0 skips` de backend y `4 ejecutados, 4 pasados` de navegador (C12 y C15); C01 a C18 en PASA (C16 con la regresión de H-004 a H-007, el ensayo de roles y el barrido de
    migraciones; C17 con la KB que dejó el orquestador); `rojos (0); que no son por aserción (0)`.

## 3. H-009 · Confirmar

- [x] 3.1 **Migración `0038_confirmar_saldos`.** Acción `confirmar_saldos_iniciales` en `Accion`, matriz
  y `accion_de_auditoria`.
- [x] 3.2 **Caso de uso `confirmar`.** Permiso, `FOR UPDATE` del complejo, estado `pendiente`, borrador
  vigente, diferencias aceptadas, traducción a los tipos del 4c, `registrar_saldo_inicial` con
  `operacion_id` = importación, estado `confirmada` del edificio (por un caso de uso de
  `complejos.aplicacion`), importación `confirmada`, auditoría, todo en una transacción. Concurrencia
  contra otra confirmación y contra "sin saldos previos" con dos conexiones reales. Mutantes: confirmar
  sin bloquear el complejo; confirmar con diferencias sin aceptar; no pasar el estado a `confirmada`.
- [x] 3.3 **Web.** `textoDeEstados.ts` (`confirmada`), el paso 7 del resumen (E12), botón "Confirmar
  saldos" y su estado; e2e de Playwright.

  - **RED 3.1 a 3.3** (12/11/2026, commit `702fa7f`, contra un `confirmar` provisorio que no escribe nada, sin la
    migración `0038`, sin la acción `confirmar_saldos_iniciales`, sin la ruta, y contra `confirmarSaldos`, `confirmarSaldosAction`
    y `PantallaConfirmada` provisorios que no hacen nada). Backend: `cd backend && uv run pytest
    tests/unitarios/acceso/test_permisos.py tests/integracion/test_confirmar_saldos.py
    tests/integracion/test_migracion_0038_confirmar_saldos.py tests/integracion/test_vocabulario_configuracion.py
    tests/integracion/test_rutas_protegidas.py -q` -> `52 failed, 1832 passed`: 20 de permisos (`ValueError: 'confirmar_saldos_iniciales'
    is not a valid Accion` en las celdas y `test_la_matriz_de_prueba_cubre_exactamente_el_vocabulario` por aserción), 19 de
    `test_confirmar_saldos.py` (`DID NOT RAISE Conflicto/NoEncontrado/SinPermiso/EntradaInvalida`, `assert 'pendiente' == 'confirmada'`,
    `assert '0.00' == '320000.00'`, la auditoría vacía), 2 de la `0038` (`la 0038 no cargó la acción`, `falta la migración 0038`), 1 de
    vocabulario (`0038_confirmar_saldos.py` no existe) y 10 de rutas (la ruta cubierta ya no existe: 404). Web: `corepack pnpm exec
    vitest run textoDeEstados importaciones comparacion Pantalla.test acciones-confirmar api-falsa.confirmacion` -> 36 rojos, todos por
    `expect` (botón o región que no está, `estado: "fallo"` en vez del estado de la API, `revalidatePath` sin llamar, la API falsa que
    da 404 en 901 a 904 y `pendiente` en el 902).
    **Aceptación de H-009 contra `702fa7f`** (`python3 aceptacion/H-009/aceptar.py --codigo HEAD --sin-regresion --sin-navegador`,
    aceptación `4c3525e`): `32 ejecutados, 1 pasados, 31 fallas, 0 errores, 0 skips`; `rojos (31); que no son por aserción (0)`; C01 a C05,
    C07 a C12 caen en `llegó 404: {"detail":"Not Found"}` (la ruta no existe) y C13 en `falta confirmar_saldos_iniciales en
    accion_de_auditoria (0038)`.
  - **Verde 3.1 a 3.3** (`2492581` backend, `35e5fb6` web): migración `0038` (sólo la acción en `accion_de_auditoria`), `Accion.CONFIRMAR_SALDOS_INICIALES`
    (super admin y administrador principal), `importacion.aplicacion.confirmar`, `complejos.aplicacion.escritura.confirmar_saldos_iniciales_del_edificio` (pasa a
    `confirmada`, con su propio `FOR UPDATE` y reverificación), `POST .../importaciones/confirmacion`, `BorradorVigente.archivo`; web: `confirmarSaldos`,
    `confirmarSaldosAction` (revalida el resumen, no la comparación), "Confirmar saldos" con su confirmación "no se deshace", región "Saldos iniciales confirmados",
    `PantallaConfirmada` (la comparación deja de existir al confirmar; `page.tsx` consulta el resumen), paso 7 con dos links, `confirmada` en `textoDeEstados`, API falsa
    901 a 904 y `e2e/confirmar-saldos.spec.ts` (axe y teclado a 320 y 1280 px; **no lo corrí en navegador**, sólo corrió el de la aceptación). Tests viejos tocados (ningún id
    cambió): `test_auditoria_transaccion` (invocador de la acción nueva), cabezas `0038` en `test_libro_rollback` y `test_conmutar_politicas_reales`, vocabulario, matriz, rutas.
    Barrido local de migraciones + ensayo de login + fronteras + vocabulario + rutas + auditoría + confirmar + permisos: `2755 passed`. Web: vitest de lo tocado `227 passed`, `tsc`, `biome ci` y ruff/mypy limpios.
  - **Mutantes 3.2** (copia previa, uno a la vez, restaurado con `diff` vacío; suite de `test_confirmar_saldos.py` + la aceptación copiada): sin chequear diferencias aceptadas -> `test_diferencias_sin_aceptar`,
    `test_c07_diferencias_sin_aceptar`; sin pasar el edificio a `confirmada` -> `test_confirmar_devuelve_la_carga...`, `test_c01_confirmar_sin_diferencias`; sin cerrar la importación -> las mismas;
    sin auditar -> `test_confirmar_audita_una_vez...`, `test_c01...`; importación que no es la vigente -> `test_c07_la_importacion_no_es_el_borrador_vigente`; `operacion_id` nuevo ->
    `test_c01...`; crédito como deuda -> 7 rojos; sin el chequeo de saldos (E10) -> `test_c07_una_importacion_sin_hoja_de_saldos`; origen con otro archivo -> `test_c01`, `test_c04`.
    **Sin candado del complejo: sobrevivió** (54 passed) mientras quedaran el `FOR UPDATE` de `confirmar_saldos_iniciales_del_edificio` y la FK `KEY SHARE` de `cuenta` (que
    también esperan a otra transacción con el candado y releen el estado): defensa triple. Se sumaron dos tests de dos conexiones reales (`test_la_segunda_confirmacion_espera_a_la_primera_y_da_conflicto`,
    `test_confirmar_pierde_contra_un_sin_saldos_previos_que_ya_tenia_el_candado`), y el mutante **sin candado ni relectura del estado** cae en ambos y en `test_c11_dos_confirmaciones_simultaneas`.
    El C11 por HTTP de la aceptación no alcanzó solo para matar el mutante sin candado.
  - **Aceptación de H-009 contra `35e5fb6`** (`python3 aceptacion/H-009/aceptar.py --codigo HEAD`, aceptación `4c3525e`): tests `32 ejecutados, 32 pasados`, navegador `5 ejecutados, 5 pasados`; C01 a C13 y C15 en PASA
    (C13 con H-004 a H-008, el ensayo de roles y el barrido); C14 en FALLA sólo por la KB, que es del orquestador; `rojos (0); que no son por aserción (0)`.

## 4. H-010 · Ajuste de saldo inicial

- [x] 4.1 **Migración `0039_ajuste_de_saldo_inicial`.** Tabla de sólo agregar (FK compuesta a la
  obligación de su misma cuenta, motivo 1 a 500 no en blanco, `operacion_id` único por administración),
  acción `ajustar_saldo_inicial`. Matriz de mutantes de protección, ensayo de roles y barrido local.
- [x] 4.2 **Caso de uso `ajustar_saldo_inicial`** (en `importacion.aplicacion` o `cuenta_corriente.
  aplicacion`, el que respete las fronteras; la obligación la crea `cuenta_corriente`). Obligación sin
  emisión (E11), cuenta creada si falta, `bloquear_cuentas`, `imputar_pendientes`, registro y auditoría,
  replay por `operacion_id`. Interés desde el día siguiente contra la emisión real. Mutantes: vencimiento
  retroactivo; sin motivo; permitir con la migración pendiente.
  - **Rojo 4.1 y 4.2** (`ea65094`, 12/11/2026): `test_ajustar_saldo_inicial.py` (42 casos) y `test_migracion_0039_ajuste_de_saldo_inicial.py` (3) contra un `ajuste.py` provisorio que
    no escribe ni valida nada: `38 failed, 4 passed` (los 4 son controles: los dos roles que pueden ajustar, el motivo de 500 y la acción de un super admin). Todos caen por aserción:
    `DID NOT RAISE` (Conflicto 14, EntradaInvalida 18, NoEncontrado 8, SinPermiso 6, AssertionError 2), `la 0039 no creó ajuste_de_saldo_inicial`, `falta la tabla ... (0039)`,
    la obligación nueva que no aparece, el vencimiento y el crédito que no se imputa.
  - **Verde 4.1 y 4.2** (`1eca595`, 12/11/2026): migración `0039` (tabla de sólo agregar con CHECK de motivo 1 a 500 no en blanco, único `(administracion_id, operacion_id)`, FK compuesta a la obligación de su
    misma cuenta, FK a complejo y persona, tres triggers, RLS forzada, bajada que se niega con filas; sin `ALTER` sobre tablas protegidas), `Accion.AJUSTAR_SALDO_INICIAL` (super admin y administrador principal),
    detalle de auditoría `{complejo_id, unidad_id, obligacion_id, componente}` (sin importe ni motivo), `cuenta_corriente.aplicacion.ajustes.registrar_ajuste_de_saldo_inicial` (la obligación sin emisión, la
    cuenta si falta, `bloquear_cuentas`, `imputar_pendientes`, el replay antes de escribir y de nuevo con la cuenta bloqueada) e `importacion.aplicacion.ajuste.ajustar_saldo_inicial` (404 > 403 > 409
    `estado_migracion` > 422 > escritura; audita una vez, el replay no). `ajuste_de_saldo_inicial` es del libro en `_DUENO_DE_TABLA`. Tabla en `TABLAS_DE_SOLO_AGREGAR`, en `ensayo-roles.sh` y en los helpers de
    devolución de los tests (L-083). Tests viejos tocados (ningún id cambió): `test_auditoria_transaccion` (invocador), `test_libro_rollback` (cabeza y lista), `test_conmutar_politicas_reales` (cabeza),
    `test_migracion_0038_confirmar_saldos` (compara las tablas sin la de la `0039` y vuelve a la cabeza), vocabulario, matriz de permisos, catálogo de RLS y fronteras. `test_ajustar_saldo_inicial.py` +
    `test_migracion_0039_...`: `42 passed`; barrido local de migraciones + ensayo de login: `1406 passed` (10 min); con fronteras, vocabulario, catálogo, permisos y auditoría: `1534 passed`; ruff y format limpios,
    mypy limpio salvo 3 errores que ya estaban en `test_importaciones_comparacion_api.py` (no tocado).
  - **Aceptación de H-010 contra `1eca595`** (`aceptar.py --codigo HEAD --sin-regresion --sin-navegador`, aceptación `4c3525e`): `56 ejecutados, 19 pasados, 37 fallas, 0 errores`; sin la ruta (4.3) pasan C02, C03,
    C04, C05, C06 y C13; C01, C07 a C12 caen en `llegó 404: {"detail":"Not Found"}` (la ruta no existe) y C08 es de navegador; C14 y C15 quedan fuera de este corte (regresión no corrida; KB del orquestador);
    `rojos (37); que no son por aserción (0)`.
  - **Mutantes 4.2** (copia previa, uno a la vez, restaurado con `diff` vacío; `test_ajustar_saldo_inicial.py`): vencimiento retroactivo (la fecha de migración) -> 4 rojos
    (`test_el_vencimiento_es_el_dia_del_ajuste_nunca_la_migracion`, `..._sin_emision`, replay); sin normalizar el motivo -> 6; migración pendiente permitida -> 3 (`test_solo_con_la_migracion_confirmada`);
    sin auditar -> 2; el replay audita de nuevo -> 1; sin imputar el crédito -> 1; replay sin comparar los datos -> 4; importe siempre en ordinaria -> 2. **Mutantes 4.1** (migración mutada, con los tests de C13
    de la aceptación copiados a `tests/integracion/` por un rato): sin el trigger de TRUNCATE y sin RLS forzada caen en el paso de roles del arranque (`la protección de ajuste_de_saldo_inicial no se pudo
    confirmar`), antes de llegar a los tests; sin el CHECK del motivo -> `test_c13_el_check_frena_un_motivo_invalido` x3 (`DID NOT RAISE CheckViolation`). La FK a la obligación sin la cuenta no es un mutante
    válido: PostgreSQL rechaza la FK sin la unicidad que la respalda.
- [x] 4.3 **Ruta y pantalla** (D11) con e2e de Playwright.
  - **Rojo 4.3** (`113d85d` la ruta, `92d581c` la pantalla, 12/11/2026): `test_ajuste_de_saldo_inicial_api.py` (24 casos) contra la app sin la ruta: `24 failed`, todos por aserción
    (`assert 404 == 201/403/409/422`, `{'detail': 'Not Found'} == {'detail': 'no encontrado'}`); la ruta se sumó a `_RUTAS_CUBIERTAS` y a su despachador. Web, contra una `Pantalla.tsx`, una
    `acciones.ts` y un `ajustarSaldoInicial` provisorios que no hacen nada: `32 failed | 74 passed` (`Pantalla.test.tsx` 8, `acciones.test.ts` 20, `importaciones.test.ts` 3, `Pantalla.ajuste.test.tsx` 1;
    los 4 del padrón que pasan son los controles de "no ofrece ajustar"); todos caen en `expect` (`expected null not to be null`, `expected [] to deeply equal ['importe']`, `expected undefined to be ...`).
    Un caso del rojo de la ruta estaba mal armado (pedía 404 a un rol sin permiso sobre una unidad inexistente de su propio edificio: el orden es 404 > 403 > unidad) y se corrigió con el verde.
  - **Aceptación de H-010 contra `585e1d9`** (`aceptar.py --codigo HEAD`, aceptación `4c3525e`, primera corrida con ruta y pantalla): `56 ejecutados, 55 pasados, 1 falla`; e2e `4 ejecutados, 4 pasados`; C01 a C11,
    C13, C15 y C16 en PASA; **C12** cae en `test_c12_otra_administracion` (`409 == 404`: B ajusta una unidad de A desde su edificio, que todavía está pendiente, y el estado ganaba a la unidad) y **C14**
    en `test_toda_ruta_post_tiene_cuerpo_de_prueba` (la ruta nueva faltaba en `_CUERPOS_DE_PRUEBA` de `test_altas_sin_id_del_cliente.py`: mi barrido local de la ruta sólo había corrido `test_rutas_protegidas.py`).
    Rojo del arreglo: `test_la_unidad_que_no_es_del_edificio_gana_al_estado_de_la_migracion` (2 casos) cae con `se esperaba NoEncontrado, llegó Conflicto('conflicto')`; el orden queda alcance > permiso > unidad (404) > estado (409) > entrada (422).
  - **Verde 4.3** (`143821e` la ruta, `585e1d9` la pantalla, `ccb356d` el arreglo del orden, 12/11/2026): `POST /api/complejos/{complejo_id}/unidades/{unidad_id}/ajustes-de-saldo-inicial` en `proptech_api/importaciones.py`
    (`CuerpoAjuste` con `extra="forbid"`; `importe` positivo con dos decimales, `componente` `ordinaria|fondo_de_reserva|extraordinaria`, `motivo` de 1 a 500 recortado; 201 también para el replay; los errores de `complejos`,
    del libro y de `importacion` los traducen los tres manejadores que ya había), y en `ajustar_saldo_inicial` la unidad se chequea (404) antes que el estado (409). Web: `unidades/[unidadId]/ajuste-de-saldo-inicial/`
    (`page`, `Pantalla`, `acciones`, `validacion`, `ayuda`, `loading`), la columna "Saldo inicial" con el link "Ajustar saldo inicial de {identificador}" en el padrón (migración `confirmada` y permiso
    `ajustar_saldo_inicial`), `ajustarSaldoInicial` en `lib/api/importaciones.ts`, y la API falsa con los edificios 1001 a 1003. `test_ajuste_de_saldo_inicial_api.py` + `test_ajustar_saldo_inicial.py` + barridos
    (`test_rutas_protegidas`, `test_altas_sin_id_del_cliente`, fronteras): `818 passed`; web `vitest` de `src/app/edificios/[id]` + `src/lib` + `e2e`: `463 passed` y `118 passed`; `tsc`, ruff y mypy limpios; biome sin
    hallazgos nuevos (los que quedan son de `sesion.test.ts` y `edificios/page.tsx`, que no toqué).
  - **Aceptación de H-010 contra `ccb356d`** (`python3 aceptacion/H-010/aceptar.py --codigo HEAD`, aceptación `4c3525e`): tests `56 ejecutados, 56 pasados`, navegador `4 ejecutados, 4 pasados`; C01 a C16 en PASA
    (C14 con el ensayo de roles, H-004 a H-009 y el barrido de migraciones; C15 con la KB que ya estaba); `rojos (0); que no son por aserción (0)`.
  - **Mutantes 4.3** (copia previa, uno a la vez, restaurado con `diff` vacío). Ruta: sin `extra="forbid"` -> `test_un_cuerpo_invalido_es_422...[extra-extra]`; sin el chequeo de la unidad antes del estado ->
    los 2 casos de `test_la_unidad_que_no_es_del_edificio_gana_al_estado...`. **Sobrevivieron** (defensa en profundidad, el libro repite la regla con el mismo `loc`): motivo vacío, importe positivo y concepto libre
    en el cuerpo de la ruta; el `commit` de la ruta (el caso de uso ya cierra su transacción). Web: operación nueva en cada reintento -> `un reintento con los mismos datos reusa la operación`; importe sin pasar a
    punto -> 9 rojos de `acciones.test.ts`; sin confirmación -> 4 de `Pantalla.test.tsx`; padrón con la migración pendiente -> 2; padrón sin el permiso -> 1; el 403 como error genérico -> 1; `ok` sin el ajuste -> 1;
    la lib que manda campos de más -> 1.

## 5. Cierre

- [ ] 5.1 **Fronteras, calidad y suite completa** en el CI de GitHub del PR del change (D-154), con
  conteo propio; KB al día (Knowledge Base Impact de `proposal.md`).
