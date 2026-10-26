Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el rojo
se anota en el informe con el comando, su salida y la hora. **El rojo cuenta sólo si cae en la aserción
que el test dice probar** (L-034): un `ModuleNotFoundError` o un `ImportError` no es un rojo. Cuando el
módulo todavía no existe, primero se crea vacío (la función existe y devuelve vacío o `None`) y el rojo
se mide contra eso. Un test que nace verde porque el comportamiento ya existe se declara como
**fijación** y se lo ve fallar con un mutante en una copia o un savepoint (L-013, L-019, L-035).
"Verde" en el backend es `bash infra/ci/test-backend.sh` sobre los archivos tocados, más `ruff check`,
`ruff format --check` y `mypy` (L-005). Cada tarea nombra los escenarios que cubre (`capability` ›
escenario) y las lecciones que aplica.

**NO CONSTRUIR**: el change es **HIGH**. Precondición: la sección "Aprobación" de `proposal.md`
firmada por Juani, Alberto o Emiliano, con nombre, fecha y la respuesta a cada elección (D-094, D-111).
Una regla nueva que entre después de la firma necesita firma propia (L-029).

**Orden obligatorio**: el grupo 3 (columna nueva y trigger por sentencia de `configuracion_versionada`)
va **antes** del grupo 5 (la tabla pasa al rol de arranque). Al revés, `0021` falla porque el migrador
ya no es el dueño (design D8).

**Cantidad**: 20 tareas, en el límite de `config.yaml`. Las dos que sumó la revisión salen de D-114:
1.4 (regla (e), D-114.7) y 4.3 (la auditoría partida en unidades y grupos, al sumar `crear_unidad` y
`crear_grupo`, D-114.3). Si en la
construcción alguna no entra en medio día, el corte natural es el grupo 4 como change propio (4a-bis),
que no depende de los grupos 1, 2 ni 5; se le avisa a Juani antes de partir.

## 1. Fronteras entre módulos (design D4)

- [x] 1.1 **Recolector de imports, paquete vacío y regla (a), sin ciclos.** Corregir el recolector de
  `tests/unitarios/test_fronteras_de_modulos.py` para que registre el submódulo en las tres formas
  (`import a.b.c`, `from a.b import c`, `from a import b`) y resuelva los relativos por `level`; RED:
  con el recolector de hoy, `from proptech_core.compartido import cola` no aparece como `compartido.cola`.
  Crear `proptech_core/cuenta_corriente/` con `__init__.py`, `dominio/__init__.py` y
  `aplicacion/__init__.py` vacíos. Test de ciclos de cualquier largo, que lista los módulos recorridos.
  RED: con la detección devolviendo "sin ciclos", los mutantes en copia pasan; con la detección, dan rojo
  el de dos nodos (`acceso → complejos → acceso`) y el de tres (`acceso → cuenta_corriente → complejos →
  acceso`, que un chequeo por pares no ve). Escenarios: `fronteras-de-modulos` › El código de hoy no
  tiene ciclos; › Un ciclo agregado a una copia; › Un ciclo de tres módulos. Lecciones: L-013, L-019,
  L-035.
- [x] 1.2 **Regla (b), entre módulos sólo `aplicacion`.** Diccionario de excepciones por destino, con
  su motivo (`acceso.dominio.identidad`, `acceso.dominio.permisos`, `acceso.dominio.eventos`), comparado
  por segmentos completos; `proptech_api` y `proptech_worker` fuera; imports relativos entre módulos
  prohibidos. RED: sin la excepción de `acceso.dominio.eventos`, el árbol real da rojo en
  `complejos/aplicacion/ejemplo.py:39`. Mutantes en copia: `acceso.dominio.token` en las tres formas de
  import; `acceso.adaptadores`; `acceso.dominio.identidad_x`; `from ...acceso.dominio import token`.
  Cada uno rojo nombrando archivo y destino. Escenarios: `fronteras-de-modulos` › Las excepciones de hoy
  pasan; › Un import de dominio ajeno sin excepción; › Las tres formas de escribir un import; › Un
  destino con prefijo parecido a una excepción; › Un import relativo entre módulos; › Un import de
  adaptadores ajenos. Lecciones: L-013, L-021, L-035.
- [x] 1.3 **Regla (c), `dominio/` sólo usa lo puro de `compartido`, y regla (d) de
  `cuenta_corriente`.** Lista permitida con `parametros` como excepción con motivo; `cuenta_corriente`
  no importa `compartido.cola` ni `liquidacion`. RED de (c): sin `parametros` en la excepción, el árbol
  real da rojo en `complejos/dominio/configuracion.py:11`. Mutantes en copia, cada uno en las tres
  formas de import: `dominio/` importando `compartido.base_de_datos`; un `compartido/nuevo.py` creado en
  la copia e importado desde `dominio/`; `cuenta_corriente/aplicacion` importando `compartido.cola`.
  Escenarios: `fronteras-de-modulos` › El dominio de hoy pasa (regla c); › El dominio importa la base
  (regla c); › Un submódulo nuevo de compartido; › El paquete existe y pasa; › La cuenta corriente
  importa la cola. Lecciones: L-013, L-022.
- [x] 1.4 **Regla (e), el dominio no depende de su propia infraestructura (D-114.7).** Un archivo de
  `dominio/` no importa la `aplicacion`, los `adaptadores` ni los `puertos` de su módulo, ni `sqlalchemy`
  ni `psycopg`. Nace verde sobre el árbol real (fijación); mutantes en copia: `complejos/dominio/`
  importando `sqlalchemy` y `complejos.aplicacion.escritura`, cada uno rojo nombrando el archivo.
  Escenarios: `fronteras-de-modulos` › El dominio de hoy pasa (regla e); › El dominio importa la base
  (regla e). Lecciones: L-013, L-035.


  **EVIDENCIA · 26/10/2026 · constructor**

  Fijación: el árbol actual ya cumple (e); RED mediante ambos mutantes en copia.


Mutante sqlalchemy, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/dominio/mutante.py': 'import sqlalchemy'}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_dominio_no_depende_de_infraestructura
time: 10:35:09
__________________ test_dominio_no_depende_de_infraestructura __________________

    def test_dominio_no_depende_de_infraestructura() -> None:
>       assert _dominio_sin_infraestructura(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/d...: sqlalchemy'] == []
E
E         Left contains one more item: 'complejos/dominio/mutante.py: sqlalchemy'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:398: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_dominio_no_depende_de_infraestructura
============================== 1 failed in 0.05s ===============================
```
Mutante proptech_core.complejos.aplicacion.escritura, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/dominio/mutante.py': 'import proptech_core.complejos.aplicacion.escritura'}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_dominio_no_depende_de_infraestructura
time: 10:35:10
__________________ test_dominio_no_depende_de_infraestructura __________________

    def test_dominio_no_depende_de_infraestructura() -> None:
>       assert _dominio_sin_infraestructura(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/d...on.escritura'] == []
E
E         Left contains one more item: 'complejos/dominio/mutante.py: proptech_core.complejos.aplicacion.escritura'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:398: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_dominio_no_depende_de_infraestructura
============================== 1 failed in 0.05s ===============================
```

```text
GREEN (mutantes descartados)
command: bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py
time: 10:35:26
.......                                                                  [100%]

============================== 34 passed in 0.78s ==============================
ruff check: All checks passed!
ruff format --check: 1 file already formatted
mypy tests/unitarios/test_fronteras_de_modulos.py: Success: no issues found in 1 source file
```


  **EVIDENCIA · 26/10/2026 · constructor**

```text
RED
command: bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py
time: 10:33:50
=================================== FAILURES ===================================
____________________ test_dominio_solo_usa_compartido_puro _____________________

    def test_dominio_solo_usa_compartido_puro() -> None:
>       assert _dominio_compartido(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/d...s.Parametros'] == []
E
E         Left contains 2 more items, first extra item: 'complejos/dominio/configuracion.py: proptech_core.compartido.parametros'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:356: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
========================= 1 failed, 30 passed in 0.72s =========================
```

Mutante base_de_datos-0, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/dominio/mutante.py': 'import proptech_core.compartido.base_de_datos', 'compartido/nuevo.py': ''}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
time: 10:35:04
____________________ test_dominio_solo_usa_compartido_puro _____________________

    def test_dominio_solo_usa_compartido_puro() -> None:
>       assert _dominio_compartido(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/d...ase_de_datos'] == []
E
E         Left contains one more item: 'complejos/dominio/mutante.py: proptech_core.compartido.base_de_datos'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:357: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
============================== 1 failed in 0.05s ===============================
```
Mutante base_de_datos-1, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/dominio/mutante.py': 'from proptech_core.compartido import base_de_datos', 'compartido/nuevo.py': ''}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
time: 10:35:04
____________________ test_dominio_solo_usa_compartido_puro _____________________

    def test_dominio_solo_usa_compartido_puro() -> None:
>       assert _dominio_compartido(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/d...ase_de_datos'] == []
E
E         Left contains one more item: 'complejos/dominio/mutante.py: proptech_core.compartido.base_de_datos'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:357: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
============================== 1 failed in 0.05s ===============================
```
Mutante base_de_datos-2, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/dominio/mutante.py': 'from proptech_core.compartido.base_de_datos import algo', 'compartido/nuevo.py': ''}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
time: 10:35:05
____________________ test_dominio_solo_usa_compartido_puro _____________________

    def test_dominio_solo_usa_compartido_puro() -> None:
>       assert _dominio_compartido(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/d...e_datos.algo'] == []
E
E         Left contains 2 more items, first extra item: 'complejos/dominio/mutante.py: proptech_core.compartido.base_de_datos'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:357: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
============================== 1 failed in 0.05s ===============================
```
Mutante nuevo-0, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/dominio/mutante.py': 'import proptech_core.compartido.nuevo', 'compartido/nuevo.py': ''}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
time: 10:35:05
____________________ test_dominio_solo_usa_compartido_puro _____________________

    def test_dominio_solo_usa_compartido_puro() -> None:
>       assert _dominio_compartido(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/d...artido.nuevo'] == []
E
E         Left contains one more item: 'complejos/dominio/mutante.py: proptech_core.compartido.nuevo'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:357: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
============================== 1 failed in 0.05s ===============================
```
Mutante nuevo-1, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/dominio/mutante.py': 'from proptech_core.compartido import nuevo', 'compartido/nuevo.py': ''}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
time: 10:35:06
____________________ test_dominio_solo_usa_compartido_puro _____________________

    def test_dominio_solo_usa_compartido_puro() -> None:
>       assert _dominio_compartido(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/d...artido.nuevo'] == []
E
E         Left contains one more item: 'complejos/dominio/mutante.py: proptech_core.compartido.nuevo'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:357: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
============================== 1 failed in 0.05s ===============================
```
Mutante nuevo-2, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/dominio/mutante.py': 'from proptech_core.compartido.nuevo import algo', 'compartido/nuevo.py': ''}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
time: 10:35:07
____________________ test_dominio_solo_usa_compartido_puro _____________________

    def test_dominio_solo_usa_compartido_puro() -> None:
>       assert _dominio_compartido(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/d...o.nuevo.algo'] == []
E
E         Left contains 2 more items, first extra item: 'complejos/dominio/mutante.py: proptech_core.compartido.nuevo'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:357: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_dominio_solo_usa_compartido_puro
============================== 1 failed in 0.05s ===============================
```
Mutante cola-0, copia temporal previa del árbol; se descarta al salir.
```text
{'cuenta_corriente/aplicacion/mutante.py': 'import proptech_core.compartido.cola', 'compartido/nuevo.py': ''}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_cuenta_corriente_no_encola_ni_liquida
time: 10:35:07
__________________ test_cuenta_corriente_no_encola_ni_liquida __________________

    def test_cuenta_corriente_no_encola_ni_liquida() -> None:
>       assert _cuenta_corriente(RAIZ_SRC) == []
E       AssertionError: assert ['cuenta_corr...partido.cola'] == []
E
E         Left contains one more item: 'cuenta_corriente/aplicacion/mutante.py: proptech_core.compartido.cola'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:361: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_cuenta_corriente_no_encola_ni_liquida
============================== 1 failed in 0.04s ===============================
```
Mutante cola-1, copia temporal previa del árbol; se descarta al salir.
```text
{'cuenta_corriente/aplicacion/mutante.py': 'from proptech_core.compartido import cola', 'compartido/nuevo.py': ''}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_cuenta_corriente_no_encola_ni_liquida
time: 10:35:08
__________________ test_cuenta_corriente_no_encola_ni_liquida __________________

    def test_cuenta_corriente_no_encola_ni_liquida() -> None:
>       assert _cuenta_corriente(RAIZ_SRC) == []
E       AssertionError: assert ['cuenta_corr...partido.cola'] == []
E
E         Left contains one more item: 'cuenta_corriente/aplicacion/mutante.py: proptech_core.compartido.cola'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:361: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_cuenta_corriente_no_encola_ni_liquida
============================== 1 failed in 0.04s ===============================
```
Mutante cola-2, copia temporal previa del árbol; se descarta al salir.
```text
{'cuenta_corriente/aplicacion/mutante.py': 'from proptech_core.compartido.cola import algo', 'compartido/nuevo.py': ''}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_cuenta_corriente_no_encola_ni_liquida
time: 10:35:08
__________________ test_cuenta_corriente_no_encola_ni_liquida __________________

    def test_cuenta_corriente_no_encola_ni_liquida() -> None:
>       assert _cuenta_corriente(RAIZ_SRC) == []
E       AssertionError: assert ['cuenta_corr...do.cola.algo'] == []
E
E         Left contains 2 more items, first extra item: 'cuenta_corriente/aplicacion/mutante.py: proptech_core.compartido.cola'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:361: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_cuenta_corriente_no_encola_ni_liquida
============================== 1 failed in 0.04s ===============================
```

```text
GREEN (mutantes descartados)
command: bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py
time: 10:35:26
.......                                                                  [100%]

============================== 34 passed in 0.78s ==============================
ruff check: All checks passed!
ruff format --check: 1 file already formatted
mypy tests/unitarios/test_fronteras_de_modulos.py: Success: no issues found in 1 source file
```


  **EVIDENCIA · 26/10/2026 · constructor**

```text
RED
command: bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py
time: 10:33:24
=================================== FAILURES ===================================
______________________ test_entre_modulos_solo_aplicacion ______________________

    def test_entre_modulos_solo_aplicacion() -> None:
>       assert _entre_modulos(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/a...entoDeAcceso'] == []
E
E         Left contains 2 more items, first extra item: 'complejos/aplicacion/ejemplo.py: proptech_core.acceso.dominio.eventos'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:312: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
========================= 1 failed, 19 passed in 0.57s =========================
```

Mutante import-0, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/aplicacion/mutante.py': 'import proptech_core.acceso.dominio.token'}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
time: 10:35:00
______________________ test_entre_modulos_solo_aplicacion ______________________

    def test_entre_modulos_solo_aplicacion() -> None:
>       assert _entre_modulos(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/a...ominio.token'] == []
E
E         Left contains one more item: 'complejos/aplicacion/mutante.py: proptech_core.acceso.dominio.token'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:314: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
============================== 1 failed in 0.06s ===============================
```
Mutante import-1, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/aplicacion/mutante.py': 'from proptech_core.acceso.dominio import token'}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
time: 10:35:01
______________________ test_entre_modulos_solo_aplicacion ______________________

    def test_entre_modulos_solo_aplicacion() -> None:
>       assert _entre_modulos(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/a...ominio.token'] == []
E
E         Left contains 2 more items, first extra item: 'complejos/aplicacion/mutante.py: proptech_core.acceso.dominio'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:314: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
============================== 1 failed in 0.06s ===============================
```
Mutante import-2, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/aplicacion/mutante.py': 'from proptech_core.acceso import dominio'}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
time: 10:35:01
______________________ test_entre_modulos_solo_aplicacion ______________________

    def test_entre_modulos_solo_aplicacion() -> None:
>       assert _entre_modulos(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/a...ceso.dominio'] == []
E
E         Left contains 2 more items, first extra item: 'complejos/aplicacion/mutante.py: proptech_core.acceso'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:314: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
============================== 1 failed in 0.06s ===============================
```
Mutante import-3, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/aplicacion/mutante.py': 'import proptech_core.acceso.adaptadores'}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
time: 10:35:02
______________________ test_entre_modulos_solo_aplicacion ______________________

    def test_entre_modulos_solo_aplicacion() -> None:
>       assert _entre_modulos(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/a....adaptadores'] == []
E
E         Left contains one more item: 'complejos/aplicacion/mutante.py: proptech_core.acceso.adaptadores'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:314: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
============================== 1 failed in 0.06s ===============================
```
Mutante import-4, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/aplicacion/mutante.py': 'import proptech_core.acceso.dominio.identidad_x'}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
time: 10:35:02
______________________ test_entre_modulos_solo_aplicacion ______________________

    def test_entre_modulos_solo_aplicacion() -> None:
>       assert _entre_modulos(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/a....identidad_x'] == []
E
E         Left contains one more item: 'complejos/aplicacion/mutante.py: proptech_core.acceso.dominio.identidad_x'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:314: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
============================== 1 failed in 0.06s ===============================
```
Mutante import-5, copia temporal previa del árbol; se descarta al salir.
```text
{'complejos/aplicacion/mutante.py': 'from ...acceso.dominio import token'}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
time: 10:35:03
______________________ test_entre_modulos_solo_aplicacion ______________________

    def test_entre_modulos_solo_aplicacion() -> None:
>       assert _entre_modulos(RAIZ_SRC) == []
E       AssertionError: assert ['complejos/a...ominio.token'] == []
E
E         Left contains 2 more items, first extra item: 'complejos/aplicacion/mutante.py: proptech_core.acceso.dominio'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:314: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_entre_modulos_solo_aplicacion
============================== 1 failed in 0.06s ===============================
```

```text
GREEN (mutantes descartados)
command: bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py
time: 10:35:26
.......                                                                  [100%]

============================== 34 passed in 0.78s ==============================
ruff check: All checks passed!
ruff format --check: 1 file already formatted
mypy tests/unitarios/test_fronteras_de_modulos.py: Success: no issues found in 1 source file
```


  **EVIDENCIA · 26/10/2026 · constructor**

```text
RED
command: bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py
time: 10:32:29
        "from proptech_core import compartido",
    ])
    def test_recolector_conserva_submodulo(tmp_path: Path, sentencia: str) -> None:
        archivo = tmp_path / "ejemplo.py"
        archivo.write_text(sentencia)
        destino = "proptech_core.compartido" if sentencia.endswith("import compartido") else "proptech_core.compartido.cola"
>       assert (0, destino) in _imports_de(archivo)
E       AssertionError: assert (0, 'proptech_core.compartido.cola') in [(0, 'proptech_core.compartido')]
E        +  where [(0, 'proptech_core.compartido')] = _imports_de(PosixPath('/tmp/pytest-of-juanisarmiento/pytest-5/test_recolector_conserva_submo1/ejemplo.py'))

tests/unitarios/test_fronteras_de_modulos.py:221: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_recolector_conserva_submodulo[from proptech_core.compartido import cola]
========================= 1 failed, 9 passed in 0.31s ==========================
```

```text
RED detección inicialmente vacía
time: 10:33:02
command: bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py
        archivo.write_text(f"import proptech_core.{destino}.aplicacion")
        if tres:
            (copia_core / "cuenta_corriente" / "mutante.py").write_text("import proptech_core.complejos.aplicacion")
        esperado = "acceso → cuenta_corriente → complejos → acceso" if tres else "acceso → complejos → acceso"
>       assert esperado in _ciclos(copia_core)
E       AssertionError: assert 'acceso → cuenta_corriente → complejos → acceso' in []
E        +  where [] = _ciclos(PosixPath('/tmp/pytest-of-juanisarmiento/pytest-7/test_ciclos_de_cualquier_largo1/proptech_core'))

tests/unitarios/test_fronteras_de_modulos.py:267: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_ciclos_de_cualquier_largo[False]
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_ciclos_de_cualquier_largo[True]
========================= 2 failed, 11 passed in 0.34s =========================
```

Mutante ciclo-dos, copia temporal previa del árbol; se descarta al salir.
```text
{'acceso/mutante.py': 'import proptech_core.complejos.aplicacion'}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_sin_ciclos_entre_modulos
time: 10:34:59
        print("Módulos recorridos:", modulos)
>       assert _ciclos(RAIZ_SRC) == []
E       AssertionError: assert ['acceso → co...jos → acceso'] == []
E
E         Left contains one more item: 'acceso → complejos → acceso'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:269: AssertionError
----------------------------- Captured stdout call -----------------------------
Módulos recorridos: ['acceso', 'complejos', 'cuenta_corriente']
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_sin_ciclos_entre_modulos
============================== 1 failed in 0.06s ===============================
```
Mutante ciclo-tres, copia temporal previa del árbol; se descarta al salir.
```text
{'acceso/mutante.py': 'import proptech_core.cuenta_corriente.aplicacion', 'cuenta_corriente/mutante.py': 'import proptech_core.complejos.aplicacion'}
command: FRONTERAS_RAIZ=<copia> bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py::test_sin_ciclos_entre_modulos
time: 10:34:59
        print("Módulos recorridos:", modulos)
>       assert _ciclos(RAIZ_SRC) == []
E       AssertionError: assert ['acceso → cu...jos → acceso'] == []
E
E         Left contains one more item: 'acceso → cuenta_corriente → complejos → acceso'
E         Use -v to get more diff

tests/unitarios/test_fronteras_de_modulos.py:269: AssertionError
----------------------------- Captured stdout call -----------------------------
Módulos recorridos: ['acceso', 'complejos', 'cuenta_corriente']
=========================== short test summary info ============================
FAILED tests/unitarios/test_fronteras_de_modulos.py::test_sin_ciclos_entre_modulos
============================== 1 failed in 0.06s ===============================
```

```text
GREEN (mutantes descartados)
command: bash infra/ci/test-backend.sh tests/unitarios/test_fronteras_de_modulos.py
time: 10:35:26
.......                                                                  [100%]

============================== 34 passed in 0.78s ==============================
ruff check: All checks passed!
ruff format --check: 1 file already formatted
mypy tests/unitarios/test_fronteras_de_modulos.py: Success: no issues found in 1 source file
```

## 2. Montos y reparto (design D5 a D7)

- [x] 2.1 **`hypothesis` y aritmética de `Dinero`.** Sumar `hypothesis` con versión exacta al grupo
  `dev` y a `uv.lock`, con los perfiles `ci` (`derandomize=True`, `deadline=None`) y local, elegidos por
  variable de entorno en `infra/ci/test-backend.sh`, más un test de infra que fije que el CI usa `ci`.
  Tests: suma y resta exactas, negación (incluido `"0.00"`), `sumar([])` da `"0.00"`, operandos `int`,
  `float`, `Decimal` y texto dan `TypeError`, desborde da `MontoInvalido`, multiplicar y dividir dan
  `TypeError`, y el resultado no cambia bajo un `localcontext` con precisión 10 y otro modo de redondeo.
  RED: con los métodos existiendo y devolviendo `Dinero("0.00")`, falla la aserción de valor. Actualizar
  el docstring de `dinero.py`. Escenarios: `representacion-de-montos` › Suma y resta exactas;
  › Negación; › Sumar un número que no es monto; › Desborde; › Sumar una lista vacía; › Sin
  multiplicación. Lecciones: L-034.
- [x] 2.2 **Redondeo medio hacia arriba para montos sueltos.** `redondear_al_centavo` en
  `compartido/reparto.py`. Tests: 0.125 → 0.13, 0.124999 → 0.12, -0.125 → -0.13, `float` rechazado,
  `NaN` e infinito rechazados, 999999999999.995 da `MontoInvalido`, mismo resultado bajo otro
  `localcontext`. RED: con la versión vacía usando `ROUND_HALF_EVEN` (mutante deliberado, anotado),
  0.125 da 0.12. Escenarios: `reparto-de-montos` › El medio sube; › Float rechazado. Lecciones: L-034,
  L-008.
- [x] 2.3 **Orden natural para el desempate, con tramos etiquetados.** `clave_de_orden_natural
  (identificador, id)`, cada tramo `(0, int)` o `(1, texto)`. Tests con el orden esperado escrito:
  "L-PB", "1A", "C1", "B1", "10A" dan "1A", "10A", "B1", "C1", "L-PB"; "PB", "1", "1A", "A1" dan "1",
  "1A", "A1", "PB", sin `TypeError`; "1" < "2" < "10"; "2B" < "10A"; "a2" y "A2" desempatan por el texto
  original y luego por el UUID; identificadores iguales ordenan por UUID; "١٠" (dígitos no ASCII) va
  como texto, después de "10". RED: con la clave devolviendo el texto plano, "10" queda antes que "2" y
  "L-PB" antes que "1A". Escenarios: `reparto-de-montos` › Orden natural, no de texto; › Identificadores
  que empiezan con letra y con número. Lecciones: L-008.
- [x] 2.4 **`repartir` por mayor resto, con ejemplos.** Tests: un millón entre 150 (100 de 6.666,67 y 50
  de 6.666,66); una sola parte; pesos 0.4999 y 0.5 dan **49,99 y 50,01**; total cero; $2,00 entre tres
  (y la comparación explícita con medio hacia arriba que daría 2,01); 0.333333/0.333333/0.333334;
  **$0,05 entre 0.6/0.25/0.15 da 0,03/0,01/0,01**; total negativo; "1", "2", "10" con el centavo por
  orden natural; el mismo reparto 100 veces con las partes en otro orden; $0,01 entre 150 da un centavo a
  la primera por orden; una parte con peso 0 recibe 0,00; y cada rechazo de `RepartoInvalido` (total
  `float`, sin partes, peso negativo, peso `float` o `int`, peso `NaN`, infinito o con más de 6
  decimales, pesos en cero, claves repetidas), con `Decimal("1E+2")` escalado sin `float`. El total cero
  nace verde contra el stub en cero: se declara fijación. RED: con `repartir` devolviendo cada parte en
  cero, falla la suma. Escenarios: `reparto-de-montos` › los de "El reparto suma exacto el total", "Cada
  parte se trunca...", "El empate se resuelve siempre igual" y "El reparto rechaza entradas...".
  Lecciones: L-034.
- [x] 2.5 **Propiedades del reparto con `hypothesis`, oráculo propio y un mutante por propiedad.** Test en
  `tests/unitarios/test_reparto_propiedades.py`: totales y pesos generados (borde de 12 dígitos, pesos de
  6 decimales), estrategia que **fuerza empates** (pesos de `sampled_from` de un conjunto chico, pesos
  iguales) y mezcla identificadores con letra y con número; oráculo con `fractions.Fraction` que no
  importa ni repite la producción. RED real, cada mutante en una copia de `reparto.py` (L-013), rojo en
  su propiedad: `ROUND_HALF_UP` por parte (suma exacta); desempate por posición de entrada (orden);
  centavo al mayor peso (restos); sin normalizar por la suma de pesos (distancia). Escenarios:
  `reparto-de-montos` › Un error de fórmula compartido no pasa; › Cada propiedad tiene su mutante.
  Lecciones: L-013, L-019, L-035.


**EVIDENCIA · 26/10/2026 · constructor**


Mutante suma. Respaldo previo `.git/4a-logs/reparto-previo.py`, aplicado al árbol y revertido.
```diff
--- respaldo previo
+++ mutante
@@ -62,7 +62,7 @@
     numerador, denominador = total.decimal.as_integer_ratio()
     centavos = abs(numerador) * 100 // denominador
     cocientes, restos = zip(*(divmod(centavos * peso, suma_pesos) for peso in pesos), strict=True)
-    asignados = list(cocientes)
+    asignados = [(2 * centavos * peso + suma_pesos) // (2 * suma_pesos) for peso in pesos]
     faltan = centavos - sum(asignados)
     prioridad = sorted(range(len(partes)), key=lambda i: (-restos[i], partes[i].orden))
     for i in prioridad[:faltan]:
```
```text
command: bash infra/ci/test-backend.sh tests/unitarios/test_reparto_propiedades.py::test_propiedad_suma
time: 10:40:42

    @example((200, [1000000, 1000000, 1000000]))
    @given(casos())
    def test_propiedad_suma(caso: tuple[int, list[int]]) -> None:
        total, pesos = caso
        actual, _ = calcular(total, pesos)
>       assert sum(actual) == Fraction(abs(total), 100)
E       assert Fraction(203, 100) == Fraction(2, 1)
E        +  where Fraction(203, 100) = sum([Fraction(17, 25), Fraction(67, 100), Fraction(17, 25)])
E        +  and   Fraction(2, 1) = Fraction(200, 100)
E        +    where 200 = abs(200)
E       Failing explicit example: test_propiedad_suma(
E           caso=(200, [1000000, 1000000, 1000000]),
E       )

tests/unitarios/test_reparto_propiedades.py:39: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_reparto_propiedades.py::test_propiedad_suma - ass...
============================== 1 failed in 0.16s ===============================
```

Mutante orden. Respaldo previo `.git/4a-logs/reparto-previo.py`, aplicado al árbol y revertido.
```diff
--- respaldo previo
+++ mutante
@@ -64,7 +64,7 @@
     cocientes, restos = zip(*(divmod(centavos * peso, suma_pesos) for peso in pesos), strict=True)
     asignados = list(cocientes)
     faltan = centavos - sum(asignados)
-    prioridad = sorted(range(len(partes)), key=lambda i: (-restos[i], partes[i].orden))
+    prioridad = sorted(range(len(partes)), key=lambda i: (-restos[i], i))
     for i in prioridad[:faltan]:
         asignados[i] += 1
     signo = "-" if numerador < 0 else ""
```
```text
command: bash infra/ci/test-backend.sh tests/unitarios/test_reparto_propiedades.py::test_propiedad_orden
time: 10:40:43
        total,pesos=caso
        partes = [ParteARepartir(str(i),Decimal(p)/Decimal(1000000),(i,)) for i,p in enumerate(pesos)]
        signo = "-" if total < 0 else ""
        monto = Dinero(f"{signo}{abs(total)//100}.{abs(total)%100:02d}")
>       assert repartir(monto,partes) == repartir(monto,list(reversed(partes)))
E       assert {'0': Dinero(...inero("0.00")} == {'1': Dinero(...inero("0.00")}
E
E         Differing items:
E         {'0': Dinero("0.01")} != {'0': Dinero("0.00")}
E         {'1': Dinero("0.00")} != {'1': Dinero("0.01")}
E         Use -v to get more diff
E       Failing explicit example: test_propiedad_orden(
E           caso=(1, [1000000, 1000000]),
E       )

tests/unitarios/test_reparto_propiedades.py:67: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_reparto_propiedades.py::test_propiedad_orden - as...
============================== 1 failed in 0.14s ===============================
```

Mutante restos. Respaldo previo `.git/4a-logs/reparto-previo.py`, aplicado al árbol y revertido.
```diff
--- respaldo previo
+++ mutante
@@ -64,7 +64,7 @@
     cocientes, restos = zip(*(divmod(centavos * peso, suma_pesos) for peso in pesos), strict=True)
     asignados = list(cocientes)
     faltan = centavos - sum(asignados)
-    prioridad = sorted(range(len(partes)), key=lambda i: (-restos[i], partes[i].orden))
+    prioridad = sorted(range(len(partes)), key=lambda i: (-pesos[i], partes[i].orden))
     for i in prioridad[:faltan]:
         asignados[i] += 1
     signo = "-" if numerador < 0 else ""
```
```text
command: bash infra/ci/test-backend.sh tests/unitarios/test_reparto_propiedades.py::test_propiedad_restos
time: 10:40:44
    @example((5, [600000, 250000, 150000]))
    @given(casos())
    def test_propiedad_restos(caso: tuple[int, list[int]]) -> None:
        actual, exacto = calcular(*caso)
        # floor racional del oráculo, independiente de divmod entero de producción.
        truncados = [Fraction(e // Fraction(1,100),100) for e in exacto]
        con_extra = [i for i,a in enumerate(actual) if a > truncados[i]]
        sin_extra = [i for i,a in enumerate(actual) if a == truncados[i]]
>       assert all(exacto[i]-truncados[i] >= exacto[j]-truncados[j] for i in con_extra for j in sin_extra)
E       assert False
E        +  where False = all(<generator object test_propiedad_restos.<locals>.<genexpr> at 0x766d5f429580>)
E       Failing explicit example: test_propiedad_restos(
E           caso=(5, [600000, 250000, 150000]),
E       )

tests/unitarios/test_reparto_propiedades.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_reparto_propiedades.py::test_propiedad_restos - a...
============================== 1 failed in 0.16s ===============================
```

Mutante distancia. Respaldo previo `.git/4a-logs/reparto-previo.py`, aplicado al árbol y revertido.
```diff
--- respaldo previo
+++ mutante
@@ -61,7 +61,7 @@
         raise RepartoInvalido("la suma de pesos debe ser positiva")
     numerador, denominador = total.decimal.as_integer_ratio()
     centavos = abs(numerador) * 100 // denominador
-    cocientes, restos = zip(*(divmod(centavos * peso, suma_pesos) for peso in pesos), strict=True)
+    cocientes, restos = zip(*(divmod(centavos * peso, 1_000_000) for peso in pesos), strict=True)
     asignados = list(cocientes)
     faltan = centavos - sum(asignados)
     prioridad = sorted(range(len(partes)), key=lambda i: (-restos[i], partes[i].orden))
```
```text
command: bash infra/ci/test-backend.sh tests/unitarios/test_reparto_propiedades.py::test_propiedad_distancia
time: 10:40:45
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

caso = (200, [1000000, 1000000])

    @example((200, [1000000, 1000000]))
    @given(casos())
    def test_propiedad_distancia(caso: tuple[int, list[int]]) -> None:
        actual, exacto = calcular(*caso)
>       assert all(abs(a-e) < Fraction(1,100) for a,e in zip(actual, exacto, strict=True))
E       assert False
E        +  where False = all(<generator object test_propiedad_distancia.<locals>.<genexpr> at 0x7079be9da110>)
E       Failing explicit example: test_propiedad_distancia(
E           caso=(200, [1000000, 1000000]),
E       )

tests/unitarios/test_reparto_propiedades.py:46: AssertionError
=========================== short test summary info ============================
FAILED tests/unitarios/test_reparto_propiedades.py::test_propiedad_distancia
============================== 1 failed in 0.14s ===============================
```

```text
GREEN, después de revertir todos los mutantes y refactorizar
command: bash infra/ci/test-backend.sh tests/unitarios/test_dinero.py tests/unitarios/test_dinero_aritmetica.py tests/unitarios/test_reparto.py tests/unitarios/test_reparto_propiedades.py tests/infra/test_perfil_hypothesis.py
time: 10:42:08
============================== 99 passed in 0.74s ==============================
command: uv run --project backend ruff check <8 archivos del grupo>
All checks passed!
command: uv run --project backend ruff format --check <8 archivos del grupo>
8 files already formatted
command: uv run --project backend mypy <7 archivos nuevos/modificados del grupo>
time: 10:41:58
Success: no issues found in 7 source files
```


**EVIDENCIA · 26/10/2026 · constructor**

```text
RED
command: bash infra/ci/test-backend.sh tests/unitarios/test_reparto.py
time: 10:39:30
    def test_ejemplos_reparto(total: str, pesos: list[str], esperado: list[str]) -> None:
        resultado = repartir(Dinero(total), partes_de(pesos))
>       assert sumar(resultado.values()) == Dinero(total)
E       assert Dinero("0.00") == Dinero("1000000.00")
E        +  where Dinero("0.00") = sumar(dict_values([Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0....00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00")]))
E        +    where dict_values([Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0....00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00"), Dinero("0.00")]) = <built-in method values of dict object at 0x70d059b1fec0>()
E        +      where <built-in method values of dict object at 0x70d059b1fec0> = {'0': Dinero("0.00"), '1': Dinero("0.00"), '2': Dinero("0.00"), '3': Dinero("0.00"), ...}.values
E        +  and   Dinero("1000000.00") = Dinero('1000000')

tests/unitarios/test_reparto.py:68: AssertionError
_______________ test_ejemplos_reparto[1234.56-pesos1-esperado1] ________________

total = '1234.56', pesos = ['1'], esperado = ['1234.56']
======================== 23 failed, 17 passed in 0.16s =========================
```

Fijación: el total cero ya pasaba contra el stub que devuelve todas las partes en cero. Los otros ejemplos mostraron el rojo de la suma.

```text
GREEN, después de revertir todos los mutantes y refactorizar
command: bash infra/ci/test-backend.sh tests/unitarios/test_dinero.py tests/unitarios/test_dinero_aritmetica.py tests/unitarios/test_reparto.py tests/unitarios/test_reparto_propiedades.py tests/infra/test_perfil_hypothesis.py
time: 10:42:08
============================== 99 passed in 0.74s ==============================
command: uv run --project backend ruff check <8 archivos del grupo>
All checks passed!
command: uv run --project backend ruff format --check <8 archivos del grupo>
8 files already formatted
command: uv run --project backend mypy <7 archivos nuevos/modificados del grupo>
time: 10:41:58
Success: no issues found in 7 source files
```


**EVIDENCIA · 26/10/2026 · constructor**

```text
RED
command: bash infra/ci/test-backend.sh tests/unitarios/test_reparto.py
time: 10:38:28
        from uuid import UUID
        from proptech_core.compartido.reparto import clave_de_orden_natural
>       assert sorted(entrada, key=lambda x: clave_de_orden_natural(x, UUID(int=1))) == esperado
E       AssertionError: assert ['10A', '1A',... 'C1', 'L-PB'] == ['1A', '10A',... 'C1', 'L-PB']
E
E         At index 0 diff: '10A' != '1A'
E         Use -v to get more diff

tests/unitarios/test_reparto.py:36: AssertionError
____________________ test_orden_natural[entrada2-esperado2] ____________________

entrada = ['10', '2', '1'], esperado = ['1', '2', '10']

========================= 3 failed, 13 passed in 0.07s =========================
```

```text
GREEN, después de revertir todos los mutantes y refactorizar
command: bash infra/ci/test-backend.sh tests/unitarios/test_dinero.py tests/unitarios/test_dinero_aritmetica.py tests/unitarios/test_reparto.py tests/unitarios/test_reparto_propiedades.py tests/infra/test_perfil_hypothesis.py
time: 10:42:08
============================== 99 passed in 0.74s ==============================
command: uv run --project backend ruff check <8 archivos del grupo>
All checks passed!
command: uv run --project backend ruff format --check <8 archivos del grupo>
8 files already formatted
command: uv run --project backend mypy <7 archivos nuevos/modificados del grupo>
time: 10:41:58
Success: no issues found in 7 source files
```


**EVIDENCIA · 26/10/2026 · constructor**

```text
RED
command: bash infra/ci/test-backend.sh tests/unitarios/test_reparto.py
time: 10:38:11
            contexto.prec = 10
            contexto.rounding = ROUND_DOWN
>           assert redondear_al_centavo(Decimal(entrada)) == esperado
E           assert Dinero("0.12") == Dinero("0.13")
E            +  where Dinero("0.12") = redondear_al_centavo(Decimal('0.125'))
E            +    where Decimal('0.125') = Decimal('0.125')

tests/unitarios/test_reparto.py:16: AssertionError
_________________________ test_redondeo[-0.125--0.13] __________________________

entrada = '-0.125', salida = '-0.13'

    @pytest.mark.parametrize("entrada,salida", [("0.125", "0.13"), ("0.124999", "0.12"), ("-0.125", "-0.13"), ("999999999999.994", "999999999999.99")])
========================= 2 failed, 7 passed in 0.06s ==========================
```

Mutante deliberado inicial ROUND_HALF_EVEN; sustituido por ROUND_HALF_UP después del rojo.

```text
GREEN, después de revertir todos los mutantes y refactorizar
command: bash infra/ci/test-backend.sh tests/unitarios/test_dinero.py tests/unitarios/test_dinero_aritmetica.py tests/unitarios/test_reparto.py tests/unitarios/test_reparto_propiedades.py tests/infra/test_perfil_hypothesis.py
time: 10:42:08
============================== 99 passed in 0.74s ==============================
command: uv run --project backend ruff check <8 archivos del grupo>
All checks passed!
command: uv run --project backend ruff format --check <8 archivos del grupo>
8 files already formatted
command: uv run --project backend mypy <7 archivos nuevos/modificados del grupo>
time: 10:41:58
Success: no issues found in 7 source files
```


**EVIDENCIA · 26/10/2026 · constructor**

```text
RED
command: bash infra/ci/test-backend.sh tests/unitarios/test_dinero_aritmetica.py tests/infra/test_perfil_hypothesis.py
time: 10:37:30
            ctx.prec = 10
            ctx.rounding = ROUND_DOWN
>           assert (x + y).a_texto() == suma
E           AssertionError: assert '0.00' == '0.30'
E
E             - 0.30
E             ?   -
E             + 0.00
E             ?    +

tests/unitarios/test_dinero_aritmetica.py:16: AssertionError
___ test_suma_y_resta[999999999999.98-0.01-999999999999.99-999999999999.97] ____

========================= 13 failed, 1 passed in 0.15s =========================
```

Baseline 10:36:17: `bash infra/ci/test-backend.sh tests/unitarios/test_dinero.py`: 41 passed. Stub inicial de tres métodos y sumar devolviendo cero. Perfil CI antes ausente.

```text
GREEN, después de revertir todos los mutantes y refactorizar
command: bash infra/ci/test-backend.sh tests/unitarios/test_dinero.py tests/unitarios/test_dinero_aritmetica.py tests/unitarios/test_reparto.py tests/unitarios/test_reparto_propiedades.py tests/infra/test_perfil_hypothesis.py
time: 10:42:08
============================== 99 passed in 0.74s ==============================
command: uv run --project backend ruff check <8 archivos del grupo>
All checks passed!
command: uv run --project backend ruff format --check <8 archivos del grupo>
8 files already formatted
command: uv run --project backend mypy <7 archivos nuevos/modificados del grupo>
time: 10:41:58
Success: no issues found in 7 source files
```

## 3. Umbral de saldos chicos (R30, design D8), antes del grupo 5

- [x] 3.1 **El umbral en `parametros.yaml`.** Sección `cuenta_corriente.umbral_saldo_chico: "500.00"`
  y su validación. Tests: el archivo del repositorio devuelve 500.00; el umbral faltante, vacío, en
  blanco, `"-0.01"`, con tres decimales, como número YAML, con espacio al principio o salto de línea al
  final falla nombrando `cuenta_corriente.umbral_saldo_chico` sin repetir el valor; `"0.00"` se acepta.
  RED: con el campo declarado y opcional, el archivo sin umbral pasa. Escenarios:
  `parametros-del-sistema` › El archivo del repositorio es válido y tiene los defaults; › Umbral de
  saldos chicos inválido; › Umbral en cero. Lecciones: L-002, L-007, L-008.
- [x] 3.2 **Migración `0021`: la columna, el trigger por sentencia, las versiones viejas y su bajada.**
  Tests de integración contra PostgreSQL real, leyendo **como rol de arranque** (como migrador sin tenant
  se comparan dos conjuntos vacíos, DB-3): subir sobre `0020` con versiones cargadas deja cada una en
  "500.00" y ninguna otra columna cambia (fila por fila); el trigger de `UPDATE` no se dispara al subir,
  con su mutante (`ADD COLUMN NULL` y después `UPDATE ... SET 500`, que como dueño da el error del
  trigger); no queda default (un `INSERT` sin umbral falla por `NOT NULL`); el `CHECK` rechaza "-0.01" y
  acepta "0.00"; `UPDATE ... WHERE false` y `DELETE ... WHERE false` como dueño fallan con el error del
  trigger por sentencia, igual que `INSERT ... ON CONFLICT DO UPDATE`; el `UPDATE` del umbral como
  `proptech_app` falla con SQLSTATE `42501`; bajar como dueño restaura el esquema de `0020` (comparado
  con `pg_dump -s` o `information_schema`, no `pg_attribute` crudo, DB-2) y volver a subir deja **todos**
  los umbrales en "500.00", también uno que estaba en "300.00". Antes de cerrar: `rg` de todo `INSERT INTO
  configuracion_versionada` en el repo entero y ajustar los que la columna sin default rompe (L-023).
  RED: con `0021` vacía, falla la aserción de la columna. Escenarios: `configuracion-versionada`
  › Versiones anteriores a este cambio; › El umbral no se edita por SQL; `aislamiento-por-administracion`
  › Sentencia sin filas; › Insertar con actualización ante conflicto. Lecciones: L-023, L-018.
- [x] 3.3 **El umbral en el dominio, las versiones, el alta del edificio y la API (D-114.1).**
  `ConfiguracionEdificio` con el campo opcional y no negativo; `desde_parametros` lo toma del archivo;
  `crear_version_de_configuracion` hereda el de la versión inmediatamente anterior por `vigente_desde`
  (aunque sea futura) o, si no hay, el de parámetros; `crear_edificio` sin umbral toma el de parámetros;
  lectura y API lo devuelven como texto. Tests: v1 (hoy, 300), v2 (diciembre, 700), v3 (enero, sin
  umbral) da 700, y v4 (noviembre, sin umbral) da 300; `null` explícito igual que ausente; "0.00" y
  "750.00" explícitos; `POST /api/complejos` con `configuracion_inicial` sin umbral responde 201 con
  "500.00"; `500` (número JSON), "-1.00", "1.001" y "abc" dan 422 nombrando el campo, en versiones y en
  el alta. Web: regenerar los fixtures que salen de la API real y sumar el campo al tipo de la respuesta;
  `pnpm biome ci`, `pnpm tsc --noEmit` y `bash infra/ci/test-web.sh` en verde, ninguna pantalla cambia.
  RED: con el campo existiendo y el caso de uso ignorándolo, v3 queda en 500. Escenarios:
  `configuracion-versionada` › Versión nueva sin umbral; › Hereda de la anterior por fecha, aunque sea
  futura; › Null explícito; › Primera versión de un edificio nuevo; › Umbral explícito; › Umbral
  inválido. Lecciones: L-027, L-009.


**EVIDENCIA · 26/10/2026 · constructor**

```text
RED
command: bash infra/ci/test-backend.sh tests/integracion/test_umbral_api.py
time: 10:48:45
            versiones=api.cliente.get(api.ruta("/configuracion/versiones")).json()
            nueva=next(v for v in versiones if v["vigente_desde"]==fecha)
>           assert nueva["umbral_saldo_chico"]==esperado
E           AssertionError: assert '500.00' == '700.00'
E
E             - 700.00
E             ? ^
E             + 500.00
E             ? ^

tests/integracion/test_umbral_api.py:22: AssertionError
---------------------------- Captured stdout setup -----------------------------
{"ts": "2026-10-26T13:48:51.390Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.app", "evento": "login_sin_configurar"}
----------------------------- Captured stdout call -----------------------------
=================== 1 failed, 11 passed, 1 warning in 6.42s ====================
```

DESVÍO operativo: `PROPTECH_ACTUALIZAR_FIXTURES=1 bash infra/ci/test-backend.sh tests/integracion/test_contrato_web.py` (10:49:44, 8 passed) genera ocho fixtures en ocho APIs distintas. La suite web detectó IDs de grupos ajenos al padrón (10:50:12, fixtures.test.ts:21, 1 failed / 394 passed). Se conservaron únicamente vigente.json y versiones.json, los dos contratos modificados, generados por la API real; los otros seis se restauraron de HEAD sin retocarlos a mano. No cambia diseño, generador ni pantallas.

```text
GREEN web
command: bash infra/ci/test-web.sh
time: 10:53:41
Test Files 60 passed (60)
Tests 395 passed (395)
command: pnpm biome ci (en web/)
time: 10:54:35
Checked 190 files. No fixes applied. Found 7 warnings. exit 0
command: pnpm tsc --noEmit (en web/)
time: 10:54:35
sin salida, exit 0
```

```text
GREEN backend
command: bash infra/ci/test-backend.sh tests/unitarios/test_umbral_parametros.py tests/unitarios/test_parametros.py tests/unitarios/test_parametros_archivo_del_repo.py tests/integracion/test_umbral_migracion.py tests/integracion/test_umbral_api.py tests/integracion/test_configuracion_versionada_db.py tests/integracion/test_configuracion_api.py tests/integracion/test_crear_edificio.py tests/integracion/test_catalogo_rls.py tests/integracion/test_contrato_web.py
time: 10:52:33
183 passed, 1 warning in 31.81s
command: bash infra/ci/test-backend.sh tests/integracion/test_umbral_migracion.py tests/integracion/test_umbral_api.py
time: 10:54:50 (después de partir literales SQL por formato)
13 passed, 1 warning
```


**EVIDENCIA · 26/10/2026 · constructor**

```text
RED
command: bash infra/ci/test-backend.sh tests/integracion/test_umbral_migracion.py
time: 10:44:39
            assert len(filas) == 2
            base.migrar("upgrade","0021")
>           assert any(col[0] == "umbral_saldo_chico" for col in esquema(c))
E           assert False
E            +  where False = any(<generator object test_0021_preserva_filas_y_restauracion.<locals>.<genexpr> at 0x717de3b87030>)

tests/integracion/test_umbral_migracion.py:47: AssertionError
=========================== short test summary info ============================
FAILED tests/integracion/test_umbral_migracion.py::test_0021_preserva_filas_y_restauracion
============================== 1 failed in 3.92s ===============================
============================== 1 failed in 3.92s ===============================
```

Baseline 10:43:49: `bash infra/ci/test-backend.sh tests/integracion/test_configuracion_versionada_db.py`, 30 passed. Lectura y comparación explícitas como arranque con dos filas, y sondas también con tabla vacía.

Mutante aplicado con respaldo previo `.git/4a-logs/0021-previa.py`, restaurado byte a byte:
```diff
--- respaldo
+++ mutante
@@ -15,7 +15,8 @@
 def upgrade() -> None:
     # Default constante histórico: no UPDATE, ni reescritura de las versiones existentes.
     op.execute("ALTER TABLE configuracion_versionada ADD COLUMN "
-               "umbral_saldo_chico NUMERIC(14,2) NOT NULL DEFAULT 500.00")
+               "umbral_saldo_chico NUMERIC(14,2) NULL")
+    op.execute("UPDATE configuracion_versionada SET umbral_saldo_chico = 500.00")
     op.execute("ALTER TABLE configuracion_versionada ADD CONSTRAINT "
                "ck_configuracion_umbral CHECK (umbral_saldo_chico >= 0)")
     op.execute("ALTER TABLE configuracion_versionada ALTER COLUMN umbral_saldo_chico DROP DEFAULT")
```

```text
command: bash infra/ci/test-backend.sh tests/integracion/test_umbral_migracion.py
time: 10:45:32
            assert len(filas) == 2
            base.migrar("upgrade","0021")
            assert any(col[0] == "umbral_saldo_chico" for col in esquema(c))
            despues=c.execute("SELECT to_jsonb(v) - 'umbral_saldo_chico', umbral_saldo_chico FROM configuracion_versionada v ORDER BY id").fetchall()
            assert [f[0] for f in despues] == [f[0] for f in filas]
>           assert [f[1] for f in despues] == [Decimal("500.00")]*2
E           AssertionError: assert [None, None] == [Decimal('500...mal('500.00')]
E
E             At index 0 diff: None != Decimal('500.00')
E             Use -v to get more diff

tests/integracion/test_umbral_migracion.py:50: AssertionError
=========================== short test summary info ============================
FAILED tests/integracion/test_umbral_migracion.py::test_0021_preserva_filas_y_restauracion
============================== 1 failed in 3.91s ===============================
```

```text
command: bash infra/ci/test-backend.sh tests/integracion/test_umbral_migracion.py
time: 10:47:31
E           ^
E         File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/sqlalchemy/engine/default.py", line 1192, in do_execute
E           cursor.execute(statement, parameters)
E           ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
E         File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/psycopg/cursor.py", line 117, in execute
E           raise ex.with_traceback(None)
E       sqlalchemy.exc.ProgrammingError: (psycopg.errors.RaiseException) configuracion_versionada no admite UPDATE (sólo agregar)
E       CONTEXT:  PL/pgSQL function public.fn_configuracion_versionada_bloqueada() line 3 at RAISE
E       [SQL: UPDATE configuracion_versionada SET umbral_saldo_chico = 500.00]
E       (Background on this error at: https://sqlalche.me/e/21/f405)

tests/integracion/_edificios.py:65: AssertionError
=========================== short test summary info ============================
FAILED tests/integracion/test_umbral_migracion.py::test_0021_preserva_filas_y_restauracion
============================== 1 failed in 3.85s ===============================
```

El primer mutante como migrador dejó NULL por RLS y cayó en la aserción del contenido. El segundo cambió sólo el entorno de upgrade a arranque (respaldo previo del test `.git/4a-logs/test-0021-previo.py`, restaurado), y reprodujo el RAISE del trigger.

`rg -n "INSERT INTO configuracion_versionada" .` recorrió todo el repo: producción en escritura.py (ajustado 3.3), helper de test_configuracion_versionada_db.py y sonda de test_catalogo_rls.py (ajustados), tabla sintética de dos columnas en test_roles_solo_agregar.py (no afectada), y el nuevo ensayo de migración que omite el umbral a propósito antes de 0021.

```text
GREEN backend
command: bash infra/ci/test-backend.sh tests/unitarios/test_umbral_parametros.py tests/unitarios/test_parametros.py tests/unitarios/test_parametros_archivo_del_repo.py tests/integracion/test_umbral_migracion.py tests/integracion/test_umbral_api.py tests/integracion/test_configuracion_versionada_db.py tests/integracion/test_configuracion_api.py tests/integracion/test_crear_edificio.py tests/integracion/test_catalogo_rls.py tests/integracion/test_contrato_web.py
time: 10:52:33
183 passed, 1 warning in 31.81s
command: bash infra/ci/test-backend.sh tests/integracion/test_umbral_migracion.py tests/integracion/test_umbral_api.py
time: 10:54:50 (después de partir literales SQL por formato)
13 passed, 1 warning
```


**EVIDENCIA · 26/10/2026 · constructor**

```text
RED
command: bash infra/ci/test-backend.sh tests/unitarios/test_umbral_parametros.py
time: 10:42:58
        archivo = tmp_path / "parametros.yaml"
        archivo.write_text(yaml.safe_dump(datos))
>       with pytest.raises(ParametrosInvalidos) as error:
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ParametrosInvalidos

tests/unitarios/test_umbral_parametros.py:22: Failed
=========================== short test summary info ============================
FAILED tests/unitarios/test_umbral_parametros.py::test_umbral_invalido[None]
========================= 1 failed, 9 passed in 0.24s ==========================
========================= 1 failed, 9 passed in 0.24s ==========================
```

Baseline 10:42:46: `bash infra/ci/test-backend.sh tests/unitarios/test_parametros.py tests/unitarios/test_parametros_archivo_del_repo.py`, 63 passed. GREEN 10:43:16: mismos archivos más test_umbral_parametros.py, 73 passed.

```text
GREEN backend
command: bash infra/ci/test-backend.sh tests/unitarios/test_umbral_parametros.py tests/unitarios/test_parametros.py tests/unitarios/test_parametros_archivo_del_repo.py tests/integracion/test_umbral_migracion.py tests/integracion/test_umbral_api.py tests/integracion/test_configuracion_versionada_db.py tests/integracion/test_configuracion_api.py tests/integracion/test_crear_edificio.py tests/integracion/test_catalogo_rls.py tests/integracion/test_contrato_web.py
time: 10:52:33
183 passed, 1 warning in 31.81s
command: bash infra/ci/test-backend.sh tests/integracion/test_umbral_migracion.py tests/integracion/test_umbral_api.py
time: 10:54:50 (después de partir literales SQL por formato)
13 passed, 1 warning
```

## 4. Auditoría de los cambios del padrón (design D9)

- [x] 4.1 **Vocabulario y detalle: migración `0022`, `EventoDelPadron` y sus modelos.** Los siete
  eventos al vocabulario y al enum; un modelo de detalle por evento (D9) con `extra="forbid"`. Tests: la
  base acepta cada evento y rechaza uno inventado; se rechazan antes de escribir, sin repetir el valor,
  `editar_grupo` con `campos: ["coeficiente"]` y `editar_unidad` con un valor del piso; bajar `0022`
  restaura el vocabulario de `0021`; con una fila `editar_unidad` en `auditoria`, bajar `0022` falla con
  `23503` (el punto de no retorno del Migration Plan). Los rechazos nacen verdes contra
  `_MODELOS_DE_DETALLE.get(..., _DetalleBase)`: fijación con un mutante de modelo permisivo
  (`extra="allow"`). RED de la aceptación: con el enum y `0022` vacía, la base rechaza `editar_unidad`.
  Escenarios: `auditoria-de-acciones` › Acción fuera de la lista; › Clave no permitida en el detalle;
  › Un campo que no es de ese evento. Lecciones: L-007, L-034, L-035.

JUICIO (constructor, confianza alta): la corrida cortada no dejó RED/GREEN pegados bajo esta tarea. Se preservó su código; se recuperó la vigilancia ejecutando mutantes respaldados, sin atribuirles horas previas. SUPUESTO no necesario para el verde: se volvió a ejecutar.

Fijación recuperada, mutante vocabulario; respaldo reanudacion-vocabulario-previo.py restaurado byte a byte.
```diff
--- respaldo
+++ mutante
@@ -20,8 +20,7 @@


 def upgrade() -> None:
-    op.bulk_insert(sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
-                   [{"nombre": evento} for evento in _EVENTOS])
+    pass


 def downgrade() -> None:
```
```text
command: bash infra/ci/test-backend.sh tests/integracion/test_eventos_padron_migracion.py
time: 11:06:19
>           assert {e.value for e in EventoDelPadron} <= vocabulario
E           AssertionError: assert {'crear_grupo...nidades', ...} <= {'aceptar_ale...idacion', ...}
E
E             Extra items in the left set:
E             'crear_unidad'
E             'fijar_unidades'
E             'editar_unidad'
E             'reordenar_categorias'
E             'editar_grupo'
E             'editar_categoria'
E             'crear_grupo'

tests/integracion/test_eventos_padron_migracion.py:21: AssertionError
=========================== short test summary info ============================
FAILED tests/integracion/test_eventos_padron_migracion.py::test_vocabulario_y_bajada
============================== 1 failed in 3.75s ===============================
```

Fijación recuperada, mutante permisivo; respaldo reanudacion-permisivo-previo.py restaurado byte a byte.
```diff
--- respaldo
+++ mutante
@@ -139,7 +139,9 @@


 def _detalle_validado(accion: Accion | EventoDeAcceso | EventoDelPadron, detalle: dict[str, Any]) -> dict[str, Any]:
-    modelo = _MODELOS_DE_DETALLE.get(accion, _DetalleBase)
+    class _Permisivo(BaseModel):
+        model_config = ConfigDict(extra="allow")
+    modelo = _Permisivo
     try:
         validado = modelo.model_validate(detalle)
     except ValidationError as error:
```
```text
command: bash infra/ci/test-backend.sh tests/unitarios/test_detalle_padron.py::test_rechazo_antes_de_escribir
time: 11:06:24
>       with pytest.raises(DetalleInvalido) as error:
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE DetalleInvalido

tests/unitarios/test_detalle_padron.py:18: Failed
_____________ test_rechazo_antes_de_escribir[editar_unidad-extra1] _____________

evento = <EventoDelPadron.EDITAR_UNIDAD: 'editar_unidad'>
extra = {'piso_anterior': 'VALOR_PRIVADO'}

    @pytest.mark.parametrize("evento,extra",[(EventoDelPadron.EDITAR_GRUPO,{"campos":["coeficiente"]}),(EventoDelPadron.EDITAR_UNIDAD,{"piso_anterior":"VALOR_PRIVADO"})])
    def test_rechazo_antes_de_escribir(evento: EventoDelPadron,extra: dict[str,object]) -> None:
        detalle={"complejo_id":str(uuid4()),"campos":["piso"],**extra}
>       with pytest.raises(DetalleInvalido) as error:
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
============================== 2 failed in 0.14s ===============================
```
**EVIDENCIA · 26/10/2026 · reanudación**
GREEN (mutantes revertidos)
```text
command: bash infra/ci/test-backend.sh tests/unitarios/test_detalle_padron.py tests/integracion/test_eventos_padron_migracion.py tests/integracion/test_auditoria_unidades_padron.py tests/integracion/test_vocabulario_configuracion.py tests/integracion/test_unidades_casos_de_uso.py
time: 11:06:45
26 passed, 1 warning in 16.44s
```


- [x] 4.2 **Unidades: `crear_unidad` y `editar_unidad` auditan en su transacción.** Reciben `identidad` y
  `request_id`, la API se los pasa, registran sólo si algo cambió comparando valores normalizados. Tests
  contra PostgreSQL real: el coeficiente de "0.050000" a "0.060000" y el piso dejan `editar_unidad` con
  `campos` `coeficiente` y `piso`, el anterior y el nuevo del coeficiente, y sin valores del piso; alta
  con "0.080000" deja `crear_unidad` con el nuevo; guardar los mismos valores, incluido "0.05" contra
  "0.050000", no deja fila (mutante: registrar siempre); un identificador repetido no deja fila y la
  unidad sigue igual (mutante que **sí** discrimina: registrar en otra sesión con commit propio, antes
  del `UPDATE`); si `registrar()` falla, la unidad sigue igual y la respuesta no repite ningún valor
  (mutante: `try/except` que se trague el error). Escenarios: `auditoria-de-acciones` › Cambiar el
  coeficiente de una unidad; › Alta de una unidad y de un grupo (unidad); › Guardar sin cambios; › El
  cambio que falla no deja auditoría; › Si la auditoría falla, el cambio no queda. Lecciones: L-019,
  L-034.

EVIDENCIA: al retomar quedó aplicado el mutante de sesión externa. El baseline 11:05:11 dio 1 failed, 13 passed en test_conflicto_no_deja_auditoria; se restauró unidades-previas.py y se ejecutaron los tres mutantes.

Mutante siempre, respaldo previo unidades-previas.py y restauración byte a byte.
```diff
--- respaldo
+++ mutante
@@ -142,8 +142,6 @@
         anterior = _datos({k: v for k, v in fila.items() if k != "complejo_id"})
         entrada = _datos({**anterior.model_dump(), **cambios})
         campos = sorted(k for k in type(entrada).model_fields if getattr(entrada, k) != getattr(anterior, k))
-        if not campos:
-            return
         detalle: dict[str, Any] = {"complejo_id": str(fila["complejo_id"]), "campos": campos}
         if "coeficiente" in campos:
             detalle["coeficiente"] = {"anterior": anterior.coeficiente.a_texto(), "nuevo": entrada.coeficiente.a_texto()}
```
```text
command: bash infra/ci/test-backend.sh tests/integracion/test_auditoria_unidades_padron.py::test_edicion_normalizada_solo_guarda_cambios
time: 11:03:01
>       assert filas(api,uid,"editar_unidad")==[]
E       AssertionError: assert [(UUID('71aa7...ff7d543139'})] == []
E
E         Left contains one more item: (UUID('71aa742d-0cad-4e59-9c8c-c281c1765cf7'), UUID('03357fa3-b775-491d-b208-8f8bce296557'), {'campos': [], 'complejo_id': 'cff4a259-ebdb-448d-9739-68ff7d543139'})
E         Use -v to get more diff

tests/integracion/test_auditoria_unidades_padron.py:39: AssertionError
---------------------------- Captured stdout setup -----------------------------
{"ts": "2026-10-26T14:03:06.775Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.app", "evento": "login_sin_configurar"}
----------------------------- Captured stdout call -----------------------------
{"ts": "2026-10-26T14:03:06.872Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "b5f42e6c-999a-4d8b-bb7b-2cbd58098dc9", "metodo": "POST", "ruta": "/api/complejos/{complejo_id}/unidades", "estado": 201, "duracion_ms": 22}
{"ts": "2026-10-26T14:03:06.873Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
{"ts": "2026-10-26T14:03:06.881Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "03357fa3-b775-491d-b208-8f8bce296557", "metodo": "PATCH", "ruta": "/api/unidades/{unidad_id}", "estado": 200, "duracion_ms": 7}
{"ts": "2026-10-26T14:03:06.881Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
========================= 1 failed, 1 warning in 5.53s =========================
```

Mutante sesión externa encontrado al retomar; respaldo previo de la corrida anterior unidades-previas.py. RED reproducido 11:05:11.
```diff
--- respaldo
+++ mutante
@@ -147,6 +147,9 @@
         detalle: dict[str, Any] = {"complejo_id": str(fila["complejo_id"]), "campos": campos}
         if "coeficiente" in campos:
             detalle["coeficiente"] = {"anterior": anterior.coeficiente.a_texto(), "nuevo": entrada.coeficiente.a_texto()}
+        with Session(sesion.get_bind()) as externa, externa.begin():
+            externa.execute(text("SELECT set_config('app.administracion_id', :id, true)"), {"id": str(identidad.administracion_id)})
+            registrar(externa, identidad, EventoDelPadron.EDITAR_UNIDAD, entidad="unidad", entidad_id=unidad_id, request_id=request_id, detalle=detalle)
         sesion.execute(
             text(
                 "UPDATE unidad SET identificador=:identificador, tipo=:tipo, piso=:piso, "
@@ -154,7 +157,4 @@
             ),
             {**entrada.model_dump(mode="json"), "id": unidad_id},
         )
-        registrar(
-            sesion, identidad, EventoDelPadron.EDITAR_UNIDAD,
-            entidad="unidad", entidad_id=unidad_id, request_id=request_id, detalle=detalle,
-        )
+
```
```text
command: bash infra/ci/test-backend.sh tests/unitarios/test_detalle_padron.py tests/integracion/test_eventos_padron_migracion.py tests/integracion/test_auditoria_unidades_padron.py
time: 11:05:11
>       assert filas(api,uid,"editar_unidad")==[]
E       AssertionError: assert [(UUID('0ecd0...b53b6815a3'})] == []
E
E         Left contains one more item: (UUID('0ecd0903-68eb-4286-803d-6bc83003803c'), UUID('a89a1e31-c8d1-4b26-91ce-04e40055ad52'), {'campos': ['identificador'], 'complejo_id': '8d73687b-6bf1-432d-94b2-6ab53b6815a3'})
E         Use -v to get more diff

tests/integracion/test_auditoria_unidades_padron.py:57: AssertionError
---------------------------- Captured stdout setup -----------------------------
{"ts": "2026-10-26T14:05:20.137Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.app", "evento": "login_sin_configurar"}
----------------------------- Captured stdout call -----------------------------
{"ts": "2026-10-26T14:05:20.205Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "4aa75221-d98d-4924-84f0-4c7a90c7cc31", "metodo": "POST", "ruta": "/api/complejos/{complejo_id}/unidades", "estado": 201, "duracion_ms": 21}
{"ts": "2026-10-26T14:05:20.206Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
{"ts": "2026-10-26T14:05:20.209Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "ad8722f1-1854-4ef4-ad61-904cd85ad6e2", "metodo": "GET", "ruta": "/api/unidades/{unidad_id}", "estado": 200, "duracion_ms": 3}
=================== 1 failed, 13 passed, 1 warning in 9.11s ====================
```

Mutante siempre, respaldo previo unidades-previas.py y restauración byte a byte.
```diff
--- respaldo
+++ mutante
@@ -142,8 +142,6 @@
         anterior = _datos({k: v for k, v in fila.items() if k != "complejo_id"})
         entrada = _datos({**anterior.model_dump(), **cambios})
         campos = sorted(k for k in type(entrada).model_fields if getattr(entrada, k) != getattr(anterior, k))
-        if not campos:
-            return
         detalle: dict[str, Any] = {"complejo_id": str(fila["complejo_id"]), "campos": campos}
         if "coeficiente" in campos:
             detalle["coeficiente"] = {"anterior": anterior.coeficiente.a_texto(), "nuevo": entrada.coeficiente.a_texto()}
```
```text
command: bash infra/ci/test-backend.sh tests/integracion/test_auditoria_unidades_padron.py::test_edicion_normalizada_solo_guarda_cambios
time: 11:05:46
>       assert filas(api,uid,"editar_unidad")==[]
E       AssertionError: assert [(UUID('e31ec...c4981b59e4'})] == []
E
E         Left contains one more item: (UUID('e31ec7f5-de48-4254-a9c1-3c8a76cc5ccc'), UUID('97f63062-f27d-46f3-9ca0-313c42062a4f'), {'campos': [], 'complejo_id': '0eca19fc-ae83-4c36-ad72-70c4981b59e4'})
E         Use -v to get more diff

tests/integracion/test_auditoria_unidades_padron.py:39: AssertionError
---------------------------- Captured stdout setup -----------------------------
{"ts": "2026-10-26T14:05:51.645Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.app", "evento": "login_sin_configurar"}
----------------------------- Captured stdout call -----------------------------
{"ts": "2026-10-26T14:05:51.742Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "f19be535-964e-4954-b06a-534e184a6903", "metodo": "POST", "ruta": "/api/complejos/{complejo_id}/unidades", "estado": 201, "duracion_ms": 22}
{"ts": "2026-10-26T14:05:51.743Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
{"ts": "2026-10-26T14:05:51.751Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "97f63062-f27d-46f3-9ca0-313c42062a4f", "metodo": "PATCH", "ruta": "/api/unidades/{unidad_id}", "estado": 200, "duracion_ms": 7}
{"ts": "2026-10-26T14:05:51.751Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
========================= 1 failed, 1 warning in 5.52s =========================
```

Mutante sesion-externa, respaldo previo unidades-previas.py y restauración byte a byte.
```diff
--- respaldo
+++ mutante
@@ -147,6 +147,9 @@
         detalle: dict[str, Any] = {"complejo_id": str(fila["complejo_id"]), "campos": campos}
         if "coeficiente" in campos:
             detalle["coeficiente"] = {"anterior": anterior.coeficiente.a_texto(), "nuevo": entrada.coeficiente.a_texto()}
+        with Session(sesion.get_bind()) as externa, externa.begin():
+            externa.execute(text("SELECT set_config('app.administracion_id', :id, true)"), {"id": str(identidad.administracion_id)})
+            registrar(externa, identidad, EventoDelPadron.EDITAR_UNIDAD, entidad="unidad", entidad_id=unidad_id, request_id=request_id, detalle=detalle)
         sesion.execute(
             text(
                 "UPDATE unidad SET identificador=:identificador, tipo=:tipo, piso=:piso, "
@@ -154,7 +157,4 @@
             ),
             {**entrada.model_dump(mode="json"), "id": unidad_id},
         )
-        registrar(
-            sesion, identidad, EventoDelPadron.EDITAR_UNIDAD,
-            entidad="unidad", entidad_id=unidad_id, request_id=request_id, detalle=detalle,
-        )
+
```
```text
command: bash infra/ci/test-backend.sh tests/integracion/test_auditoria_unidades_padron.py::test_conflicto_no_deja_auditoria
time: 11:05:52
>       assert filas(api,uid,"editar_unidad")==[]
E       AssertionError: assert [(UUID('a17a0...5a16d93862'})] == []
E
E         Left contains one more item: (UUID('a17a0892-37b5-4468-88cd-290fd4997f9d'), UUID('449f5568-0cdf-4cfa-a07e-f0f219f726c2'), {'campos': ['identificador'], 'complejo_id': 'dcce2523-815e-47ee-b982-075a16d93862'})
E         Use -v to get more diff

tests/integracion/test_auditoria_unidades_padron.py:57: AssertionError
---------------------------- Captured stdout setup -----------------------------
{"ts": "2026-10-26T14:05:58.403Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.app", "evento": "login_sin_configurar"}
----------------------------- Captured stdout call -----------------------------
{"ts": "2026-10-26T14:05:58.499Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "8767a2f2-e3e9-4c03-9b3e-7cecc5e62745", "metodo": "POST", "ruta": "/api/complejos/{complejo_id}/unidades", "estado": 201, "duracion_ms": 22}
{"ts": "2026-10-26T14:05:58.499Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
{"ts": "2026-10-26T14:05:58.503Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "90b6f974-d32e-4777-961e-3196aab38e42", "metodo": "GET", "ruta": "/api/unidades/{unidad_id}", "estado": 200, "duracion_ms": 3}
{"ts": "2026-10-26T14:05:58.503Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
========================= 1 failed, 1 warning in 5.58s =========================
```

Mutante tragar-error, respaldo previo unidades-previas.py y restauración byte a byte.
```diff
--- respaldo
+++ mutante
@@ -154,7 +154,10 @@
             ),
             {**entrada.model_dump(mode="json"), "id": unidad_id},
         )
-        registrar(
-            sesion, identidad, EventoDelPadron.EDITAR_UNIDAD,
-            entidad="unidad", entidad_id=unidad_id, request_id=request_id, detalle=detalle,
-        )
+        try:
+            registrar(
+                sesion, identidad, EventoDelPadron.EDITAR_UNIDAD,
+                entidad="unidad", entidad_id=unidad_id, request_id=request_id, detalle=detalle,
+            )
+        except Exception:
+            pass
```
```text
command: bash infra/ci/test-backend.sh tests/integracion/test_auditoria_unidades_padron.py::test_falla_auditoria_revierte_y_no_filtra
time: 11:05:59
>       assert r.status_code==500
E       assert 200 == 500
E        +  where 200 = <Response [200 OK]>.status_code

tests/integracion/test_auditoria_unidades_padron.py:75: AssertionError
---------------------------- Captured stdout setup -----------------------------
{"ts": "2026-10-26T14:06:05.154Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.app", "evento": "login_sin_configurar"}
----------------------------- Captured stdout call -----------------------------
{"ts": "2026-10-26T14:06:05.251Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "b67efd79-c0e8-4c00-850c-303e7b069482", "metodo": "POST", "ruta": "/api/complejos/{complejo_id}/unidades", "estado": 201, "duracion_ms": 22}
{"ts": "2026-10-26T14:06:05.251Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
{"ts": "2026-10-26T14:06:05.255Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "3778d02a-8305-41b9-af5b-36ed3c1fb064", "metodo": "GET", "ruta": "/api/unidades/{unidad_id}", "estado": 200, "duracion_ms": 4}
{"ts": "2026-10-26T14:06:05.256Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
{"ts": "2026-10-26T14:06:05.264Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "54607616-f16d-4b30-bb15-8c4d854f514c", "metodo": "PATCH", "ruta": "/api/unidades/{unidad_id}", "estado": 200, "duracion_ms": 7}
{"ts": "2026-10-26T14:06:05.264Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
========================= 1 failed, 1 warning in 5.60s =========================
```
**EVIDENCIA · 26/10/2026 · reanudación**
GREEN (mutantes revertidos)
```text
command: bash infra/ci/test-backend.sh tests/unitarios/test_detalle_padron.py tests/integracion/test_eventos_padron_migracion.py tests/integracion/test_auditoria_unidades_padron.py tests/integracion/test_vocabulario_configuracion.py tests/integracion/test_unidades_casos_de_uso.py
time: 11:06:45
26 passed, 1 warning in 16.44s
```


- [x] 4.3 **Grupos y categorías: `crear_grupo`, `editar_grupo`, `fijar_unidades`, `editar_categoria` y
  `reordenar_categorias`.** Mismo patrón que 4.2. Tests: en un grupo con coeficientes propios, cambiar
  uno, agregar otro y quitar un tercero deja `fijar_unidades` con las tres unidades, anterior y nuevo
  (vacío el anterior de la agregada y el nuevo de la quitada); fijar los mismos miembros con los mismos
  coeficientes no deja fila; `crear_grupo` con propios deja el nuevo de cada miembro; editar y reordenar
  categorías dejan sólo nombres de campos; los siete eventos una vez cada uno dejan siete filas
  distintas, y la suite de "una acción por caso de uso" sigue en verde. RED: con los parámetros nuevos y
  sin llamar a `registrar()`, falla la aserción de la fila. Escenarios: `auditoria-de-acciones`
  › Fijar las unidades de un grupo; › Coeficientes propios de un grupo; › Alta de una unidad y de un
  grupo (grupo); › Cada caso de uso con su evento; › Dos casos de uso con la misma acción. Lecciones:
  L-019, L-034.

## 5. Dueño de las tablas de sólo agregar (design D0 a D3), después del grupo 3


**EVIDENCIA · 26/10/2026 · constructor**
```text
RED
command: bash infra/ci/test-backend.sh tests/integracion/test_auditoria_grupos_categorias.py
time: 11:08:47
>       assert len(creados) == 1
E       assert 0 == 1
E        +  where 0 = len([])

tests/integracion/test_auditoria_grupos_categorias.py:27: AssertionError
---------------------------- Captured stdout setup -----------------------------
{"ts": "2026-10-26T14:08:53.146Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.app", "evento": "login_sin_configurar"}
----------------------------- Captured stdout call -----------------------------
{"ts": "2026-10-26T14:08:53.242Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "910dca21-f7b5-4575-b5e4-cff8a4aa9856", "metodo": "POST", "ruta": "/api/complejos/{complejo_id}/unidades", "estado": 201, "duracion_ms": 21}
{"ts": "2026-10-26T14:08:53.242Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
{"ts": "2026-10-26T14:08:53.249Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "217e5d61-755f-4b72-a904-f50d7735f46a", "metodo": "POST", "ruta": "/api/complejos/{complejo_id}/unidades", "estado": 201, "duracion_ms": 6}
{"ts": "2026-10-26T14:08:53.249Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
{"ts": "2026-10-26T14:08:53.255Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "3eda3df1-38c4-4266-93f2-0abcbd301c7f", "metodo": "POST", "ruta": "/api/complejos/{complejo_id}/unidades", "estado": 201, "duracion_ms": 6}
{"ts": "2026-10-26T14:08:53.255Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
{"ts": "2026-10-26T14:08:53.265Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.seguimiento", "evento": "pedido_atendido", "request_id": "9b9e3b7f-ba45-4850-b238-dae1fc04aec2", "metodo": "POST", "ruta": "/api/complejos/{complejo_id}/grupos", "estado": 201, "duracion_ms": 9}
{"ts": "2026-10-26T14:08:53.265Z", "nivel": "info", "servicio": "api", "logger": "httpx", "evento": "HTTP Request: %s %s \"%s %d %s\""}
------------------------------ Captured log call -------------------------------
INFO     proptech_api.seguimiento:seguimiento.py:114 pedido_atendido
FAILED tests/integracion/test_auditoria_grupos_categorias.py::test_grupo_coeficientes_y_no_op
FAILED tests/integracion/test_auditoria_grupos_categorias.py::test_siete_eventos_y_solo_nombres
========================= 2 failed, 1 warning in 5.67s =========================
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN
command: bash infra/ci/test-backend.sh tests/integracion/test_auditoria_grupos_categorias.py tests/integracion/test_grupos_casos_de_uso.py tests/integracion/test_categorias_casos_de_uso.py
time: 11:09:51

=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 22 passed, 1 warning in 12.40s ========================

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 22 passed, 1 warning in 12.40s ========================
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-registro
command: bash infra/ci/test-backend.sh tests/integracion/test_auditoria_transaccion.py
time: 11:10:49
rootdir: /home/juanisarmiento/Proyectos/PropTech/backend
configfile: pyproject.toml
plugins: hypothesis-6.170.11, anyio-4.15.1
collected 7 items

tests/integracion/test_auditoria_transaccion.py .......                  [100%]

============================== 7 passed in 4.23s ===============================
tests/integracion/test_auditoria_transaccion.py .......                  [100%]

============================== 7 passed in 4.23s ===============================
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-final-grupo
command: bash infra/ci/test-backend.sh tests/unitarios/test_detalle_padron.py tests/integracion/test_eventos_padron_migracion.py tests/integracion/test_auditoria_unidades_padron.py tests/integracion/test_auditoria_grupos_categorias.py tests/integracion/test_auditoria_transaccion.py tests/integracion/test_grupos_casos_de_uso.py tests/integracion/test_categorias_casos_de_uso.py tests/integracion/test_unidades_casos_de_uso.py tests/integracion/test_resumen_puesta_a_punto.py tests/integracion/test_vocabulario_configuracion.py tests/integracion/test_ejemplo.py
time: 11:12:31
rootdir: /home/juanisarmiento/Proyectos/PropTech/backend
configfile: pyproject.toml
plugins: hypothesis-6.170.11, anyio-4.15.1
collected 0 items

============================ no tests ran in 0.00s =============================
ERROR: file or directory not found: tests/integracion/test_ejemplo.py

============================ no tests ran in 0.00s =============================
ERROR: file or directory not found: tests/integracion/test_ejemplo.py

```


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-final-grupo-corregido
command: bash infra/ci/test-backend.sh tests/unitarios/test_detalle_padron.py tests/integracion/test_eventos_padron_migracion.py tests/integracion/test_auditoria_unidades_padron.py tests/integracion/test_auditoria_grupos_categorias.py tests/integracion/test_auditoria_transaccion.py tests/integracion/test_grupos_casos_de_uso.py tests/integracion/test_categorias_casos_de_uso.py tests/integracion/test_unidades_casos_de_uso.py tests/integracion/test_resumen_puesta_a_punto.py tests/integracion/test_vocabulario_configuracion.py tests/integracion/test_ejemplo_casos_de_uso.py
time: 11:12:45

=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 73 passed, 1 warning in 51.03s ========================

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 73 passed, 1 warning in 51.03s ========================
```


EVIDENCIA · 26/10/2026 · checks del grupo 4, 11:12:10
```text
command: cd backend && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src tests
All checks passed!
267 files already formatted
Success: no issues found in 267 source files
```
DESVÍO operativo: se corrigió sólo la indentación de dos tests de parámetros del grupo 3 que `ruff format --check` encontró sin formato al retomar. Sin cambio de comportamiento. La orden inicial de suite ampliada con test_ejemplo.py inexistente no ejecutó tests; se corrigió a test_ejemplo_casos_de_uso.py, verde 73 tests arriba.


- [x] 5.1 **Una sola fuente y el rol de arranque como dueño de `configuracion_versionada`.** Crear
  `compartido/tablas_protegidas.py` (D0) y hacer que `roles.py` y el test de dueño lo lean. Borrar el
  `xfail(strict=True)` de `test_dueno_de_tablas_solo_agregar.py`: RED, el caso `configuracion_versionada`
  da rojo en su aserción. Excluir el conjunto de la reasignación y transferir en `despues()` la tabla y
  las funciones de sus triggers; GREEN. Tests: volumen del 3a, armado devolviendo **la tabla y su
  función** al migrador (con el `despues()` nuevo, `0021` fallaría), migra y termina del rol de arranque;
  con la tabla ya del rol de arranque, una migración de prueba que hace un cambio que sale bien y después
  un `ALTER TABLE` falla con `must be owner`, el primer cambio no queda y `alembic_version` no cambia;
  bajar `0021` como migrador falla y, con tabla y función devueltas, baja y vuelve a subir con todo en
  500 (patrón de `test_auditoria_tabla.py:1052`). Adaptar los tests que bajan migraciones después de
  `despues()`. Escenarios: `aislamiento-por-administracion` › El migrador no es dueño de una tabla de
  sólo agregar; › Volumen del 3a, donde el migrador era dueño; › Una migración futura sobre una tabla
  protegida; › Bajar la migración que agrega el umbral; › Arranque repetido. Lecciones: L-036, L-035.

**EVIDENCIA · 26/10/2026 · constructor**
```text
RED
command: bash infra/ci/test-backend.sh tests/integracion/test_dueno_de_tablas_solo_agregar.py
time: 11:13:56
>       assert not puede_quitar_force, (
            f"proptech_migrador puede NO FORCE ROW LEVEL SECURITY sobre {tabla}: es su dueño (DBA-1)"
        )
E       AssertionError: proptech_migrador puede NO FORCE ROW LEVEL SECURITY sobre configuracion_versionada: es su dueño (DBA-1)
E       assert not True

tests/integracion/test_dueno_de_tablas_solo_agregar.py:160: AssertionError
=========================== short test summary info ============================
FAILED tests/integracion/test_dueno_de_tablas_solo_agregar.py::test_el_migrador_no_es_dueno_de_las_tablas_de_solo_agregar[configuracion_versionada]
========================= 1 failed, 1 passed in 3.59s ==========================
=========================== short test summary info ============================
FAILED tests/integracion/test_dueno_de_tablas_solo_agregar.py::test_el_migrador_no_es_dueno_de_las_tablas_de_solo_agregar[configuracion_versionada]
========================= 1 failed, 1 passed in 3.59s ==========================
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-dueno
command: bash infra/ci/test-backend.sh tests/integracion/test_dueno_de_tablas_solo_agregar.py
time: 11:14:46
rootdir: /home/juanisarmiento/Proyectos/PropTech/backend
configfile: pyproject.toml
plugins: hypothesis-6.170.11, anyio-4.15.1
collected 2 items

tests/integracion/test_dueno_de_tablas_solo_agregar.py ..                [100%]

============================== 2 passed in 3.50s ===============================
tests/integracion/test_dueno_de_tablas_solo_agregar.py ..                [100%]

============================== 2 passed in 3.50s ===============================
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-deploy-rollback
command: bash infra/ci/test-backend.sh tests/integracion/test_propiedad_protegida.py
time: 11:15:29
rootdir: /home/juanisarmiento/Proyectos/PropTech/backend
configfile: pyproject.toml
plugins: hypothesis-6.170.11, anyio-4.15.1
collected 2 items

tests/integracion/test_propiedad_protegida.py ..                         [100%]

============================== 2 passed in 8.19s ===============================
tests/integracion/test_propiedad_protegida.py ..                         [100%]

============================== 2 passed in 8.19s ===============================
```


DESVÍO de tests históricos: después de transferir la tabla al arranque, el migrador tampoco puede SELECT en ella: los tres casos de escritura del test antiguo fallaban en esa preparación, antes del ataque. Se lee la fila antes/después como app con tenant y se exige 42501 al escribir como migrador; el bloqueo como dueño sigue probado por la migración/sonda. La comparación del vocabulario de test_auditoria_tabla también suma el enum del padrón (otro consumidor de 4.1).



**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-consumidores-bajada
command: bash infra/ci/test-backend.sh tests/integracion/test_categorias_db.py tests/integracion/test_generales_alcance_sql.py tests/integracion/test_migracion_normaliza_textos.py tests/integracion/test_modo_de_coeficientes.py tests/integracion/test_reversion_login.py tests/integracion/test_rls_edificio.py tests/integracion/test_rls_grupos.py tests/integracion/test_unidad_edificio_inmutable.py
time: 11:34:29
>       comparar(cabeza, catalogo(base))

tests/integracion/test_reversion_login.py:34:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

esperado = {'persona': ('proptech_migrador', 'r', 'p', True, True, 'd', ...), 'persona.orden_columnas': ('id', 'administracion_id...'', None, 'gen_random_uuid()', ...), 'persona.columna.administracion_id': ('uuid', True, '', '', None, None, ...), ...}
obtenido = {'persona': ('proptech_migrador', 'r', 'p', True, True, 'd', ...), 'persona.orden_columnas': ('id', 'administracion_id...'', None, 'gen_random_uuid()', ...), 'persona.columna.administracion_id': ('uuid', True, '', '', None, None, ...), ...}

    def comparar(esperado: dict[str, Any], obtenido: dict[str, Any]) -> None:
        diferencias = sorted(
            clave
            for clave in esperado.keys() | obtenido.keys()
            if clave not in esperado or clave not in obtenido or esperado[clave] != obtenido[clave]
        )
>       assert diferencias == [], "Catálogo distinto: " + ", ".join(diferencias)
               ^^^^^^^^^^^^^^^^^
E       AssertionError: Catálogo distinto: vocabulario

=========================== short test summary info ============================
FAILED tests/integracion/test_reversion_login.py::test_catalogo_completo_en_cada_revision_y_segundo_upgrade
=================== 1 failed, 92 passed, 1 warning in 53.32s ===================
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-reversion-login
command: bash infra/ci/test-backend.sh tests/integracion/test_reversion_login.py
time: 11:36:18
rootdir: /home/juanisarmiento/Proyectos/PropTech/backend
configfile: pyproject.toml
plugins: hypothesis-6.170.11, anyio-4.15.1
collected 2 items

tests/integracion/test_reversion_login.py ..                             [100%]

============================== 2 passed in 10.92s ==============================
tests/integracion/test_reversion_login.py ..                             [100%]

============================== 2 passed in 10.92s ==============================
```


EVIDENCIA · 26/10/2026 · 11:36:40
Checks compartidos del grupo 5, después de restaurar y adaptar consumidores:
```text
command: cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
All checks passed!
297 files already formatted
Success: no issues found in 271 source files
```
GREEN del grupo: 5.3 / GREEN-grupo5-final 11:32:28, 102 passed; consumidores restantes 5.1 / GREEN-consumidores-bajada 11:34:29 (92 passed y un fallo histórico), corregido y reejecutado en GREEN-reversion-login 11:36:18 (2 passed). No hay fallos pendientes de esos conjuntos.


- [x] 5.2 **`despues()` verifica la protección por el efecto, sin armar filas (D-114.4).**
  `_verificar_tabla_protegida` para cada tabla del conjunto salvo `auditoria` (D2): RLS y `FORCE`,
  triggers declarados en D0 y sus funciones del rol de arranque, `UPDATE ... WHERE false`,
  `DELETE ... WHERE false` y `TRUNCATE` (con `CASCADE` si tiene FK entrante) en savepoints revertidos,
  exigiendo `P0001` y el texto de esa tabla. Tests, cada uno con su mutante sobre la base de prueba antes
  de `despues()`: trigger por sentencia deshabilitado; función reemplazada por una que devuelve sin
  error; `DISABLE ROW LEVEL SECURITY` con `FORCE` intacto; un `DELETE` frenado por otro error; con la
  tabla vacía la verificación igual prueba el bloqueo; una tabla de prueba con FK entrante prueba
  `TRUNCATE ... CASCADE` y no deja nada borrado; una tabla del conjunto que no existe se saltea y se dice
  en la salida. Los rojos nombran la tabla y no confirman ningún cambio de dueño. RED: con la
  verificación devolviendo "sin faltantes", el trigger deshabilitado pasa. Escenarios:
  `aislamiento-por-administracion` › Trigger deshabilitado; › Función de bloqueo reemplazada por una que
  no hace nada; › RLS deshabilitada con FORCE intacto; › Otro error frena el intento; › TRUNCATE con una
  FK entrante; › Una tabla del conjunto no existe. Lecciones: L-018, L-022, L-034.

**EVIDENCIA · 26/10/2026 · constructor**
```text
RED
command: bash infra/ci/test-backend.sh tests/integracion/test_sonda_tablas_protegidas.py::test_despues_rechaza_roturas_sin_confirmar[trigger]
time: 11:16:36
>               with pytest.raises(AssertionError, match="configuracion_versionada"):
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E               Failed: DID NOT RAISE AssertionError

tests/integracion/test_sonda_tablas_protegidas.py:29: Failed
=========================== short test summary info ============================
FAILED tests/integracion/test_sonda_tablas_protegidas.py::test_despues_rechaza_roturas_sin_confirmar[trigger]
============================== 1 failed in 3.64s ===============================
=========================== short test summary info ============================
FAILED tests/integracion/test_sonda_tablas_protegidas.py::test_despues_rechaza_roturas_sin_confirmar[trigger]
============================== 1 failed in 3.64s ===============================
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN
command: bash infra/ci/test-backend.sh tests/integracion/test_sonda_tablas_protegidas.py
time: 11:17:09
rootdir: /home/juanisarmiento/Proyectos/PropTech/backend
configfile: pyproject.toml
plugins: hypothesis-6.170.11, anyio-4.15.1
collected 6 items

tests/integracion/test_sonda_tablas_protegidas.py ......                 [100%]

============================== 6 passed in 8.25s ===============================
tests/integracion/test_sonda_tablas_protegidas.py ......                 [100%]

============================== 6 passed in 8.25s ===============================
```


Mutante de sonda omitida; respaldo previo .git/4a-logs/roles-pre-mutante.py, se restaura byte a byte. Cada rotura de base se aplica dentro del test antes de despues; el test espera rechazo y comprobación de dueño.
```diff
--- helper original (cuerpo)
+++ mutante
@@ -1,39 +1 @@
-    faltantes: list[str] = []
-    cur.execute("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid=to_regclass(%s)", (f"public.{tabla}",))
-    rls = cur.fetchone()
-    if rls is None or not all(rls):
-        faltantes.append("ROW LEVEL SECURITY habilitada y FORCE")
-    cur.execute("SELECT t.tgname, t.tgenabled, pg_get_userbyid(p.proowner) FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid WHERE t.tgrelid=to_regclass(%s) AND NOT t.tgisinternal", (f"public.{tabla}",))
-    triggers = {f[0]: (f[1], f[2]) for f in cur.fetchall()}
-    for nombre in sorted(declaracion.triggers):
-        if nombre not in triggers:
-            faltantes.append(f"trigger {nombre} no existe")
-        elif triggers[nombre] != ("O", arranque):
-            faltantes.append(f"trigger {nombre} deshabilitado o función con otro dueño")
-    cur.execute("SELECT attname FROM pg_attribute WHERE attrelid=to_regclass(%s) AND attnum>0 AND NOT attisdropped ORDER BY attnum LIMIT 1", (f"public.{tabla}",))
-    primera = cur.fetchone()
-    if primera is None:
-        faltantes.append("sin columna para probar UPDATE")
-    else:
-        cur.execute("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid=to_regclass(%s))", (f"public.{tabla}",))
-        fk = cur.fetchone()
-        cascada = sql.SQL(" CASCADE") if fk and fk[0] else sql.SQL("")
-        intentos = [
-            ("UPDATE", sql.SQL("UPDATE {} SET {}={} WHERE false").format(sql.Identifier("public", tabla), sql.Identifier(primera[0]), sql.Identifier(primera[0]))),
-            ("DELETE", sql.SQL("DELETE FROM {} WHERE false").format(sql.Identifier("public", tabla))),
-            ("TRUNCATE", sql.SQL("TRUNCATE {}{}").format(sql.Identifier("public", tabla), cascada)),
-        ]
-        for nombre, sentencia in intentos:
-            cur.execute("SAVEPOINT sonda_tabla_protegida")
-            try:
-                cur.execute(sentencia)
-            except psycopg.Error as error:
-                if error.sqlstate != "P0001" or declaracion.mensaje not in str(error):
-                    faltantes.append(f"no se pudo confirmar bloqueo de {nombre}: error distinto (SQLSTATE {error.sqlstate})")
-            else:
-                faltantes.append(f"admite {nombre}")
-            finally:
-                cur.execute("ROLLBACK TO SAVEPOINT sonda_tabla_protegida")
-                cur.execute("RELEASE SAVEPOINT sonda_tabla_protegida")
-    if faltantes:
-        raise AuditoriaNoProtegida(f"la protección de {tabla} no se pudo confirmar: " + "; ".join(faltantes))
+    pass
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
RED-mutantes-sonda-omitida
command: bash infra/ci/test-backend.sh tests/integracion/test_sonda_tablas_protegidas.py
time: 11:22:16
>               with pytest.raises(AssertionError, match="configuracion_versionada"):
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E               Failed: DID NOT RAISE AssertionError

tests/integracion/test_sonda_tablas_protegidas.py:31: Failed
_____________ test_despues_rechaza_roturas_sin_confirmar[funcion] ______________

base_para_migraciones = BaseDeEdificio(contenedor=<testcontainers.community.postgres.PostgresContainer object at 0x76ac717e5010>, nombre='prop...ece', 'POSTGRES_MIGRADOR_USER': 'proptech_migrador', 'POSTGRES_MIGRADOR_PASSWORD': 'clave-migrador-de-sesion-no-real'})
rotura = 'funcion'

    @pytest.mark.parametrize("rotura", ["trigger", "funcion", "rls", "otro_error", "texto_ajeno"])
    def test_despues_rechaza_roturas_sin_confirmar(base_para_migraciones: BaseDeEdificio, rotura: str) -> None:
        base = base_para_migraciones
        base.migrar("upgrade", "head")
        devolver_configuracion(base)
        with arranque(base) as c:
            definicion = c.execute("SELECT pg_get_functiondef('fn_configuracion_versionada_bloqueada()'::regprocedure)").fetchone()[0]
            try:
FAILED tests/integracion/test_sonda_tablas_protegidas.py::test_despues_rechaza_roturas_sin_confirmar[texto_ajeno]
FAILED tests/integracion/test_sonda_tablas_protegidas.py::test_tabla_vacia_pasa_y_fk_entrante_no_pierde_filas
========================= 6 failed, 1 passed in 9.31s ==========================
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-restaurado
command: bash infra/ci/test-backend.sh tests/integracion/test_sonda_tablas_protegidas.py tests/integracion/test_propiedad_protegida.py tests/integracion/test_dueno_de_tablas_solo_agregar.py tests/integracion/test_roles_solo_agregar.py
time: 11:22:26
collected 13 items

tests/integracion/test_sonda_tablas_protegidas.py .......                [ 53%]
tests/integracion/test_propiedad_protegida.py ..                         [ 69%]
tests/integracion/test_dueno_de_tablas_solo_agregar.py ..                [ 84%]
tests/integracion/test_roles_solo_agregar.py ..                          [100%]

============================= 13 passed in 27.58s ==============================
tests/integracion/test_roles_solo_agregar.py ..                          [100%]

============================= 13 passed in 27.58s ==============================
```


EVIDENCIA · 26/10/2026 · 11:36:40
Checks compartidos del grupo 5, después de restaurar y adaptar consumidores:
```text
command: cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
All checks passed!
297 files already formatted
Success: no issues found in 271 source files
```
GREEN del grupo: 5.3 / GREEN-grupo5-final 11:32:28, 102 passed; consumidores restantes 5.1 / GREEN-consumidores-bajada 11:34:29 (92 passed y un fallo histórico), corregido y reejecutado en GREEN-reversion-login 11:36:18 (2 passed). No hay fallos pendientes de esos conjuntos.


- [x] 5.3 **Los procesos no arrancan si una tabla protegida tiene otro dueño.**
  `verificar_tablas_de_solo_agregar(engine)` y `TablasDeSoloAgregarDesprotegidas` en `base_de_datos.py`,
  con `schemaname = 'public'`, llamada en la API, el worker, `alta_inicial` y `ejemplo`; la API y el worker
  la atrapan y registran `arranque_fallido`. Sin variable para saltearlo: los tests que levantan la app
  sin migrar usan `monkeypatch`. Tests: con `configuracion_versionada` del migrador no arrancan la API, el
  worker, `alta_inicial` ni `ejemplo`, y el log `arranque_fallido` nombra la tabla sin valores; con una
  tabla homónima del rol de arranque en otro esquema, tampoco; con una tabla del conjunto inexistente,
  tampoco; con todo en orden arrancan; el conjunto de D0 coincide con el catálogo (una tabla de prueba
  con `FORCE` y trigger de bloqueo fuera del conjunto da rojo nombrándola). RED: con la función sin
  consultar el catálogo, la API arranca con la tabla del migrador. Escenarios:
  `aislamiento-por-administracion` › Una tabla quedó del migrador; › Una tabla homónima en otro esquema;
  › El conjunto coincide con el catálogo; › Todo en orden. Lecciones: L-016, L-018, L-022, L-007.

## 6. Deuda D-053 (design D5, D10)


**EVIDENCIA · 26/10/2026 · constructor**
```text
RED
command: bash infra/ci/test-backend.sh tests/integracion/test_arranque_tablas_protegidas.py::test_cada_proceso_frena[api]
time: 11:18:09
>           with pytest.raises(TablasDeSoloAgregarDesprotegidas, match="configuracion_versionada"):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           Failed: DID NOT RAISE TablasDeSoloAgregarDesprotegidas

tests/integracion/test_arranque_tablas_protegidas.py:39: Failed
----------------------------- Captured stdout call -----------------------------
{"ts": "2026-10-26T14:18:14.771Z", "nivel": "info", "servicio": "api", "logger": "proptech_api.app", "evento": "login_sin_configurar"}
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integracion/test_arranque_tablas_protegidas.py::test_cada_proceso_frena[api]
========================= 1 failed, 1 warning in 5.84s =========================
=========================== short test summary info ============================
FAILED tests/integracion/test_arranque_tablas_protegidas.py::test_cada_proceso_frena[api]
========================= 1 failed, 1 warning in 5.84s =========================
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN
command: bash infra/ci/test-backend.sh tests/integracion/test_arranque_tablas_protegidas.py
time: 11:18:38
>               arranque.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(nombre)))

tests/integracion/conftest.py:84:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <psycopg.Connection [BAD] at 0x7a5d64fcf8c0>
query = Composed([SQL('DROP DATABASE '), Identifier('proptech_edificio_68b00df6944c4a3180ec74403cf98c17')])
params = None, prepare = None, binary = False

    def execute(
        self,
        query: Query,
        params: Params | None = None,
        *,
        prepare: bool | None = None,
        binary: bool = False,
    ) -> Cursor[Row]:
        """Execute a query and return a cursor to read its results."""
=========================== short test summary info ============================
ERROR tests/integracion/test_arranque_tablas_protegidas.py::test_esquema_exacto_y_tabla_ausente
==================== 5 passed, 1 warning, 1 error in 12.68s ====================
```


DESVÍO operativo reproducido: primera corrida 11:18:38: 5 passed y error de teardown ObjectInUse (1 sesión). El rechazo del worker dejaba su engine abierto; se libera en la rama de arranque fallido antes de propagar la excepción. No cambia permisos ni regla firmada.


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-recurso-liberado
command: bash infra/ci/test-backend.sh tests/integracion/test_arranque_tablas_protegidas.py
time: 11:19:31
>           assert candidatas == set(TABLAS_DE_SOLO_AGREGAR), f"tablas protegidas fuera del conjunto: {sorted(candidatas ^ set(TABLAS_DE_SOLO_AGREGAR))}"
E           AssertionError: tablas protegidas fuera del conjunto: ['grupo_de_reparto', 'grupo_unidad', 'unidad']
E           assert {'auditoria',...ad', 'unidad'} == {'auditoria',...n_versionada'}
E
E             Extra items in the left set:
E             'unidad'
E             'grupo_unidad'
E             'grupo_de_reparto'
E             Use -v to get more diff

tests/integracion/test_arranque_tablas_protegidas.py:97: AssertionError
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
=========================== short test summary info ============================
FAILED tests/integracion/test_arranque_tablas_protegidas.py::test_conjunto_coincide_con_catalogo
==================== 1 failed, 5 passed, 1 warning in 8.19s ====================
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
RED-tabla-olvidada
command: bash infra/ci/test-backend.sh tests/integracion/test_arranque_tablas_protegidas.py::test_conjunto_coincide_con_catalogo
time: 11:20:29
>           assert candidatas == set(TABLAS_DE_SOLO_AGREGAR), f"tablas protegidas fuera del conjunto: {sorted(candidatas ^ set(TABLAS_DE_SOLO_AGREGAR))}"
E           AssertionError: tablas protegidas fuera del conjunto: ['grupo_de_reparto', 'grupo_unidad', 'protegida_olvidada', 'unidad']
E           assert {'auditoria',...da', 'unidad'} == {'auditoria',...n_versionada'}
E
E             Extra items in the left set:
E             'unidad'
E             'grupo_unidad'
E             'grupo_de_reparto'
E             'protegida_olvidada'
E             Use -v to get more diff

tests/integracion/test_arranque_tablas_protegidas.py:97: AssertionError
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integracion/test_arranque_tablas_protegidas.py::test_conjunto_coincide_con_catalogo
========================= 1 failed, 1 warning in 5.83s =========================
```


**EVIDENCIA · 26/10/2026 · constructor**
```text
RED-tabla-olvidada-discriminante
command: bash infra/ci/test-backend.sh tests/integracion/test_arranque_tablas_protegidas.py::test_conjunto_coincide_con_catalogo
time: 11:21:09
>           assert candidatas == set(TABLAS_DE_SOLO_AGREGAR), f"tablas protegidas fuera del conjunto: {sorted(candidatas ^ set(TABLAS_DE_SOLO_AGREGAR))}"
E           AssertionError: tablas protegidas fuera del conjunto: ['protegida_olvidada']
E           assert {'auditoria',...ida_olvidada'} == {'auditoria',...n_versionada'}
E
E             Extra items in the left set:
E             'protegida_olvidada'
E             Use -v to get more diff

tests/integracion/test_arranque_tablas_protegidas.py:97: AssertionError
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integracion/test_arranque_tablas_protegidas.py::test_conjunto_coincide_con_catalogo
========================= 1 failed, 1 warning in 5.78s =========================
=========================== short test summary info ============================
FAILED tests/integracion/test_arranque_tablas_protegidas.py::test_conjunto_coincide_con_catalogo
========================= 1 failed, 1 warning in 5.78s =========================
```


DESVÍO operativo · 11:24–11:28: una automatización de formato de literales rompió paréntesis de llamadas y fue detectada por parser antes de commit. Se respaldó el árbol en .git/recuperacion-formato-5, se repuso backend versionado desde HEAD 9e62bc6 y se reaplicó sólo el grupo 5 (roles desde roles-pre-mutante.py). Parser, ruff y mypy recuperados; no se conservan cambios ajenos al alcance. No se cuenta ninguna salida de parser como RED de comportamiento.
JUICIO (constructor, confianza alta): el catálogo reconoce bloqueo incondicional por BEGIN seguido de RAISE EXCEPTION, para distinguirlo de validaciones condicionales de unidad/grupos. Comparado con 0004/0009 y mutante de tabla olvidada. Límite: una función de bloqueo escrita de otra forma exige ampliar ese discriminante.



**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-grupo5-restaurado
command: bash infra/ci/test-backend.sh tests/integracion/test_propiedad_protegida.py tests/integracion/test_sonda_tablas_protegidas.py tests/integracion/test_arranque_tablas_protegidas.py tests/integracion/test_dueno_de_tablas_solo_agregar.py tests/integracion/test_roles_solo_agregar.py tests/integracion/test_auditoria_tabla.py tests/integracion/test_auditoria_transaccion.py tests/integracion/test_configuracion_versionada_db.py tests/integracion/test_vocabulario_configuracion.py tests/unitarios/test_motor_unico.py tests/integracion/test_worker_tarea_de_prueba.py
time: 11:27:13
>           await self.retry.call_with_retry(
                lambda: self._connect(), lambda error: self.disconnect()
            )

.venv/lib/python3.14/site-packages/redis/asyncio/connection.py:290:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
.venv/lib/python3.14/site-packages/redis/asyncio/retry.py:59: in call_with_retry
    return await do()
           ^^^^^^^^^^
.venv/lib/python3.14/site-packages/redis/asyncio/connection.py:723: in _connect
    reader, writer = await asyncio.open_connection(
../../../.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/streams.py:48: in open_connection
    transport, _ = await loop.create_connection(
../../../.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/base_events.py:1119: in create_connection
    infos = await self._ensure_resolved(
../../../.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/base_events.py:1516: in _ensure_resolved
    return await loop.getaddrinfo(host, port, family=family, type=type,
../../../.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/base_events.py:936: in getaddrinfo
ERROR tests/integracion/test_worker_tarea_de_prueba.py::test_dos_fallas_tres_intentos_y_una_sola_fila[asyncio]
ERROR tests/integracion/test_worker_tarea_de_prueba.py::test_request_id_invalido_se_reemplaza_y_se_loguea[asyncio]
======== 4 failed, 95 passed, 1 warning, 3 errors in 101.79s (0:01:41) =========
```


DESVÍO de aislamiento de tests: recargar el módulo worker en las pruebas nuevas dejó su configuración de Redis de ejemplo cacheada para el fixture de sesión posterior (3 errores de conexión a redis:6379). Las pruebas nuevas guardan/restauran el módulo o lo sacan de sys.modules si no existía antes; no se cambia configuración de producción ni el fixture de sesión.



**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-grupo5-completo
command: bash infra/ci/test-backend.sh tests/integracion/test_propiedad_protegida.py tests/integracion/test_sonda_tablas_protegidas.py tests/integracion/test_arranque_tablas_protegidas.py tests/integracion/test_dueno_de_tablas_solo_agregar.py tests/integracion/test_roles_solo_agregar.py tests/integracion/test_auditoria_tabla.py tests/integracion/test_auditoria_transaccion.py tests/integracion/test_configuracion_versionada_db.py tests/integracion/test_vocabulario_configuracion.py tests/unitarios/test_motor_unico.py tests/integracion/test_worker_tarea_de_prueba.py
time: 11:30:10
>       await _correr_worker_burst(ajustes_del_worker, nombre_cola)

tests/integracion/test_worker_tarea_de_prueba.py:103:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests/integracion/test_worker_tarea_de_prueba.py:73: in _correr_worker_burst
    await worker.async_run()
.venv/lib/python3.14/site-packages/arq/worker.py:325: in async_run
    await self.main_task
.venv/lib/python3.14/site-packages/arq/worker.py:363: in main
    await self.on_startup(self.ctx)
tests/integracion/test_worker_tarea_de_prueba.py:55: in _on_startup_de_test
    await ajustes_del_worker.on_startup(ctx)
src/proptech_worker/ajustes.py:214: in on_startup
    verificar_tablas_de_solo_agregar(engine)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

engine = Engine(postgresql+psycopg://proptech_app:***@localhost:33002/test)

FAILED tests/integracion/test_worker_tarea_de_prueba.py::test_dos_fallas_tres_intentos_y_una_sola_fila[asyncio]
FAILED tests/integracion/test_worker_tarea_de_prueba.py::test_request_id_invalido_se_reemplaza_y_se_loguea[asyncio]
============= 3 failed, 99 passed, 4 warnings in 89.20s (0:01:29) ==============
```


DESVÍO de fixture real: esquema_migrado sólo ejecutaba Alembic, dejando protegidas del migrador; ahora completa roles despues, como deploy real. Reproducción 11:30:10: 99 passed y tres fallos del arranque worker nombrando ambas tablas. No se saltea el chequeo en este fixture.


**EVIDENCIA · 26/10/2026 · constructor**
```text
GREEN-grupo5-final
command: bash infra/ci/test-backend.sh tests/integracion/test_propiedad_protegida.py tests/integracion/test_sonda_tablas_protegidas.py tests/integracion/test_arranque_tablas_protegidas.py tests/integracion/test_dueno_de_tablas_solo_agregar.py tests/integracion/test_roles_solo_agregar.py tests/integracion/test_auditoria_tabla.py tests/integracion/test_auditoria_transaccion.py tests/integracion/test_configuracion_versionada_db.py tests/integracion/test_vocabulario_configuracion.py tests/unitarios/test_motor_unico.py tests/integracion/test_worker_tarea_de_prueba.py
time: 11:32:28
tests/integracion/test_worker_tarea_de_prueba.py::test_cero_fallas_registra_la_clave_en_un_intento[asyncio]
tests/integracion/test_worker_tarea_de_prueba.py::test_dos_fallas_tres_intentos_y_una_sola_fila[asyncio]
tests/integracion/test_worker_tarea_de_prueba.py::test_request_id_invalido_se_reemplaza_y_se_loguea[asyncio]
  /home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/arq/worker.py:877: DeprecationWarning: Call to deprecated close. (Use aclose() instead) -- Deprecated since version 5.0.1.
    await self.pool.close(close_connection_pool=True)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================== 102 passed, 4 warnings in 89.69s (0:01:29) ==================

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================== 102 passed, 4 warnings in 89.69s (0:01:29) ==================
```


EVIDENCIA · 26/10/2026 · 11:36:40
Checks compartidos del grupo 5, después de restaurar y adaptar consumidores:
```text
command: cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
All checks passed!
297 files already formatted
Success: no issues found in 271 source files
```
GREEN del grupo: 5.3 / GREEN-grupo5-final 11:32:28, 102 passed; consumidores restantes 5.1 / GREEN-consumidores-bajada 11:34:29 (92 passed y un fallo histórico), corregido y reejecutado en GREEN-reversion-login 11:36:18 (2 passed). No hay fallos pendientes de esos conjuntos.


- [x] 6.1 **`except TypeError` muerto y los ceros de más de `Dinero` (D-114.6).** Tests: en
  `leer_parametros`, raíz que no es un mapa y claves que no son texto fallan con `ParametrosInvalidos`
  cortados por `cargar_yaml`, sin traceback; el mismo par en el lector de la semilla (L-009);
  `desde_decimal(Decimal("1.0000"))` y `desde_decimal(Decimal("0.3000"))` dan `1.00` y `0.30`;
  `desde_decimal` de `1.005` y `1.0001` falla; `Dinero("1.0000")` y `Dinero("1.000")` fallan. Todos nacen
  verdes (fijación). Se borra el `except TypeError` y **después** se corre el mutante de `cargar_yaml`
  que deja pasar una raíz lista (con el `except` todavía, lo atraparía). Mutantes de `Dinero`, cada uno
  rojo en su aserción: `desde_decimal` sin la comparación `cuantizado != valor` (acepta `1.005`); el
  patrón del texto con `\d{1,4}` y `quantize` (acepta `"1.0000"`). Escenarios: `representacion-de-montos`
  › Ceros de más desde la base; › Un decimal que cambiaría; › Ceros de más en texto. Lecciones: L-009,
  L-013, L-007, L-035.

**EVIDENCIA · 26/10/2026 · constructor (codex)**
```text
GREEN-fijacion
command: bash infra/ci/test-backend.sh tests/unitarios/test_deuda_d053.py
time: 11:37:30
rootdir: /home/juanisarmiento/Proyectos/PropTech/backend
configfile: pyproject.toml
plugins: hypothesis-6.170.11, anyio-4.15.1
collected 10 items

tests/unitarios/test_deuda_d053.py ..........                            [100%]

============================== 10 passed in 0.09s ==============================
```

Mutante yaml-raiz (quita el `isinstance(datos, dict)` de `cargador_yaml.cargar_yaml`), con el
`except TypeError` ya borrado de `leer_parametros`:
```diff
--- respaldo
+++ mutante
@@ -102,8 +102,6 @@
 
     if datos is None:
         raise ErrorDeCarga("YAML mal formado: el archivo está vacío")
-    if not isinstance(datos, dict):
-        raise ErrorDeCarga(f"la raíz del YAML debe ser un mapa, no {type(datos).__name__}")
     return datos
```

RED-yaml-raiz (codex, 11:37:56): `assert isinstance(capturado, error)` → `AssertionError: se esperaba
ParametrosInvalidos, se obtuvo TypeError` (y lo mismo para `SemillaInvalida`), 2 failed / 2 passed.

**EVIDENCIA · 26/10/2026 · constructor (verificación propia, no confío en que lo de codex esté
completo — repito el mutante yo mismo)**
```text
RED-yaml-raiz (reproducido)
command: bash infra/ci/test-backend.sh tests/unitarios/test_deuda_d053.py
time: 11:41:13
AssertionError: se esperaba ParametrosInvalidos, se obtuvo TypeError
assert False
 +  where False = isinstance(TypeError('proptech_core.compartido.parametros.Parametros() argument after ** must be a mapping, not list'), <class 'proptech_core.compartido.parametros.ParametrosInvalidos'>)
AssertionError: se esperaba SemillaInvalida, se obtuvo TypeError
FAILED tests/unitarios/test_deuda_d053.py::test_yaml_corta_raiz_y_claves_sin_valores[- MARCADOR_PRIVADO-parametros]
FAILED tests/unitarios/test_deuda_d053.py::test_yaml_corta_raiz_y_claves_sin_valores[- MARCADOR_PRIVADO-semilla]
2 failed, 8 passed in 0.12s
```
Revertido a mano (mismo diff, en reversa) sobre `cargador_yaml.py`.
```text
GREEN-yaml-raiz (mutante revertido)
command: bash infra/ci/test-backend.sh tests/unitarios/test_deuda_d053.py
time: 11:41:28
10 passed in 0.09s
```

Mutante decimal-redondeado (quita `if cuantizado != valor: raise MontoInvalido(...)` en
`Dinero.desde_decimal`):
```diff
--- respaldo
+++ mutante
@@ -72,8 +72,6 @@
             cuantizado = valor.quantize(_CERO)
         except InvalidOperation:
             raise MontoInvalido("el monto está fuera de rango o tiene demasiados dígitos") from None
-        if cuantizado != valor:
-            raise MontoInvalido("el monto no puede tener más de dos decimales")
         return cls(str(cuantizado))
```

RED-decimal-redondeado (codex, 11:37:56): `pytest.raises(MontoInvalido)` → `Failed: DID NOT RAISE
MontoInvalido` para `1.005` y `1.0001`, 2 failed.

**EVIDENCIA · 26/10/2026 · constructor (verificación propia)**
```text
RED-decimal-redondeado (reproducido)
command: bash infra/ci/test-backend.sh tests/unitarios/test_deuda_d053.py
time: 11:40:51
FAILED tests/unitarios/test_deuda_d053.py::test_decimal_que_cambiaria_no_se_redondea[1.005] - Failed: DID NOT RAISE MontoInvalido
FAILED tests/unitarios/test_deuda_d053.py::test_decimal_que_cambiaria_no_se_redondea[1.0001] - Failed: DID NOT RAISE MontoInvalido
2 failed, 8 passed in 0.11s
```
Revertido (se repone el `if cuantizado != valor: raise MontoInvalido(...)`).
```text
GREEN-decimal-redondeado (mutante revertido)
command: bash infra/ci/test-backend.sh tests/unitarios/test_deuda_d053.py
time: 11:41:00
10 passed in 0.09s
```

Mutante texto-largo (afloja `_PATRON`/`_TEXTO_PATRON` de `\d{1,2}` a `\d{1,4}` en `dinero.py`). Codex
dejó este mutante **aplicado y sin revertir** en el árbol de trabajo al quedarse sin cuota (sin rojo
capturado). Lo completo yo:
```diff
--- respaldo
+++ mutante
@@ -1,6 +1,6 @@
 """Tipo Dinero (D5): representación de montos sobre Decimal, nunca float.
 
-Se construye sólo desde texto (`^-?\\d{1,12}(\\.\\d{1,2})?$`, 12 enteros = NUMERIC(14,2)),
+Se construye sólo desde texto (`^-?\\d{1,12}(\\.\\d{1,4})?$`, 12 enteros = NUMERIC(14,2)),
 se serializa siempre como texto con dos decimales. Sólo permite suma, resta y negación
 entre montos; el reparto y el redondeo viven en reparto.py (R07, D-046).
 """
@@ -23,8 +23,8 @@
 #   un `\n` final del string, así que `.match()` aceptaba "1.00\n" (auditor,
 #   cambio 1b vuelta 3; misma familia que L-002). `fullmatch` exige consumir
 #   el string entero, así que ese `\n` sobrante lo rechaza.
-_PATRON = re.compile(r"^-?\d{1,12}(\.\d{1,2})?$", re.ASCII)
-_TEXTO_PATRON = r"^-?\d{1,12}(\.\d{1,2})?$"
+_PATRON = re.compile(r"^-?\d{1,12}(\.\d{1,4})?$", re.ASCII)
+_TEXTO_PATRON = r"^-?\d{1,12}(\.\d{1,4})?$"
 _CERO = Decimal("0.00")
```

**EVIDENCIA · 26/10/2026 · constructor**
```text
RED-texto-largo (mutante seguía aplicado tal como lo dejó codex)
command: bash infra/ci/test-backend.sh tests/unitarios/test_deuda_d053.py
time: 11:40:13
FAILED tests/unitarios/test_deuda_d053.py::test_texto_con_ceros_sobrantes_se_rechaza[1.0000] - Failed: DID NOT RAISE MontoInvalido
FAILED tests/unitarios/test_deuda_d053.py::test_texto_con_ceros_sobrantes_se_rechaza[1.000] - Failed: DID NOT RAISE MontoInvalido
2 failed, 8 passed in 0.12s
```
Revertido a `\d{1,2}` en `_PATRON`, `_TEXTO_PATRON` y el docstring del módulo.
```text
GREEN-texto-largo (mutante revertido)
command: bash infra/ci/test-backend.sh tests/unitarios/test_deuda_d053.py
time: 11:40:33
10 passed in 0.09s
```

**EVIDENCIA · 26/10/2026 · constructor — cierre de 6.1, los tres mutantes revertidos**
```text
GREEN final (lint + tipos + safety net)
command: cd backend && uv run ruff check src/proptech_core/compartido/dinero.py src/proptech_core/compartido/parametros.py tests/unitarios/test_deuda_d053.py
time: 11:41:36 (primera corrida: I001 import sin ordenar + 2× E501 en el test nuevo; corregido a mano)
All checks passed!
command: uv run ruff format --check <los mismos 3 archivos>
(falta línea en blanco tras el docstring del módulo del test; corregido)
3 files already formatted
command: uv run mypy <los mismos 3 archivos>
time: 11:42:07
Success: no issues found in 3 source files

command: bash infra/ci/test-backend.sh tests/unitarios/test_deuda_d053.py tests/unitarios/test_dinero.py tests/unitarios/test_dinero_aritmetica.py tests/unitarios/test_parametros.py tests/unitarios/test_parametros_archivo_del_repo.py tests/unitarios/test_umbral_parametros.py tests/infra/test_perfil_hypothesis.py
time: 11:42:11
138 passed in 0.34s

command: bash infra/ci/test-backend.sh tests/unitarios/test_semilla.py tests/unitarios/test_semilla_comando.py tests/unitarios/test_semilla_configuracion.py tests/unitarios/test_semilla_texto_compartido.py
time: 11:42:19
47 passed in 0.80s
```
Estado final en el árbol: sólo quedan el borrado del `except TypeError` en `parametros.py` y la
aclaración del docstring de `desde_decimal` en `dinero.py` (sin cambio de lógica: la comparación
`cuantizado != valor` sigue intacta — ya aceptaba `1.0000`/`0.3000` porque `Decimal.__eq__` compara
valor, no representación). `cargador_yaml.py` queda sin diff contra HEAD.

## 7. Cierre

- [ ] 7.1 **Corrida de cierre después de la última vuelta.** Sobre el último commit del change, con el
  SHA anotado: `bash infra/ci/test-backend.sh` completo, `bash infra/ci/humo.sh`, la suite de web, y el
  número de tests comparado con el de `main` en `de3c710` (si bajó, explicar). Push de la rama y el CI
  completo de GitHub Actions leído en verde antes de decir "listo". Si el código cambia después, la
  corrida queda vencida y se repite. Lecciones: L-003, L-010, L-031, L-037.

**EVIDENCIA · 26/10/2026 · constructor — corrida de cierre, SIN push (no autorizado para este
constructor)**

SHA: `d562ac1` (commit de la 6.1, HEAD de `change/cimientos-del-libro` en este momento).

```text
EVIDENCIA — número de tests, HEAD vs main@de3c710
command: cd backend && uv run pytest --collect-only -q
time: 12:03:27
2840 tests collected (HEAD d562ac1)

command: (worktree temporal en /tmp, checkout de3c710) cd backend && uv sync --locked && uv run pytest --collect-only -q
time: 12:03:42
2689 tests collected (main@de3c710)
No bajó: +151 tests sobre main (los grupos 1 a 6 de este change). Nada que explicar por este lado.
```

```text
EVIDENCIA — ruff/mypy backend (como el CI)
command: cd backend && uv run ruff check . && uv run ruff format --check .
time: 12:03:56
All checks passed! / 298 files already formatted
command: uv run mypy
time: 12:04:01
Success: no issues found in 272 source files
```

```text
EVIDENCIA — web: Biome, tsc, vitest, Playwright (Chromium)
command: cd web && pnpm biome ci
time: 12:04:04
exit=0, Checked 190 files, Found 7 warnings (preexistentes, ningún archivo de web tocado por este
constructor — ni la 6.1 ni esta corrida escribieron nada bajo web/)
command: pnpm tsc --noEmit
time: 12:04:19
sin salida (0 errores)
command: bash infra/ci/test-web.sh
time: 12:04:23
Test Files 60 passed (60) / Tests 395 passed (395), 37.29s
command: bash infra/ci/test-web-navegador.sh
time: 12:05:10
172 passed (4.2m) — next build + next start + Playwright Chromium, sin Docker, nunca toca el compose
`proptech` ni blendpos-*/proxy-app-1.
```

```text
EVIDENCIA — bash infra/ci/test-backend.sh (suite completa) — ROJO
command: bash infra/ci/test-backend.sh
time inicio: 11:45:27  time fin: ~11:57 (716.66s, 0:11:56)
========= 22 failed, 2481 passed, 1 xfailed, 18 warnings, 336 errors in 716.66s (0:11:56) =========
(2481+22+336+1 = 2840, coincide con el collect-only de arriba: no es que falten tests, es que fallan
de verdad)
```

Diagnóstico de la causa (no es la 6.1; no toqué `roles.py`, `base_de_datos.py` ni migraciones):
```text
EVIDENCIA — reproducido aislado, con el mismo HEAD
command: bash infra/ci/test-backend.sh tests/integracion/test_rutas_protegidas.py
time: 11:59:35
================= 34 passed, 1 warning, 291 errors in 82.55s (0:01:22) =================

command: bash infra/ci/test-backend.sh tests/integracion/test_rutas_protegidas.py -x
time: 11:59:44
ERROR at setup of test_el_cliente_cierra_sus_conexiones_sin_depender_del_gc
  ... src/proptech_api/app.py:92: in lifespan -> verificar_tablas_de_solo_agregar(engine)
  proptech_core.compartido.base_de_datos.TablasDeSoloAgregarDesprotegidas:
  tablas de sólo agregar desprotegidas: auditoria: dueño no superusuario;
  configuracion_versionada: dueño no superusuario
```
```text
EVIDENCIA — el diff de la 6.1 no toca nada de esto
command: git diff --stat 1672614 HEAD
time: 12:03:xx
 backend/src/proptech_core/compartido/dinero.py     |   4 +-
 backend/src/proptech_core/compartido/parametros.py |   4 -
 backend/tests/unitarios/test_deuda_d053.py         |  50 +++++++
 openspec/changes/cimientos-del-libro/tasks.md      | 158 ++++++++++++++++++++-
(roles.py, base_de_datos.py y alembic/ no aparecen)
```

**JUICIO (constructor, confianza alta — reproducido dos veces de forma determinística, aislado, y
confirmado por `git diff --stat` que el único commit de la 6.1 no toca ninguno de los archivos
involucrados):** el fallo es de **antes de la 6.1**, nace en `1672614` ("proteger las tablas de sólo
agregar al arrancar", grupo 5.3). Esa tarea agregó `verificar_tablas_de_solo_agregar()` al lifespan de
arranque de la API; cualquier test que construye `app_real`/`TestClient` ahora pasa por esa
verificación. El cierre del grupo 5.3 (`GREEN-grupo5-final`, 102 passed) nunca corrió
`tests/integracion/test_rutas_protegidas.py` — no estaba en su lista de archivos — así que este hueco
quedó sin ver hasta esta corrida de cierre, que es justo lo que la 7.1 existe para atrapar. No
diagnostiqué la causa EXACTA dentro de `roles.py::despues()` (candidatos: el rol de arranque del
contenedor de test no queda `rolsuper` donde se espera, o algo en el orden
`alembic upgrade head` → `roles despues` no deja ambas tablas con el dueño correcto) — eso es trabajo
de otro constructor/rompedor sobre el grupo 5.3, fuera del alcance que se me dio (6.1 + 7.1).

**No ejecuté `bash infra/ci/humo.sh`.** Lee su propio código (`infra/ci/humo.sh:39-64`): define
`compose() { docker compose -p proptech ... }` y el `trap limpiar EXIT` hace SIEMPRE
`compose down -v --remove-orphans` sobre el proyecto `proptech` (pase o falle el resto del script).
Correrlo bajaría y borraría los volúmenes de ese proyecto Compose. Según la instrucción recibida, no lo
corrí.

**No pusheé la rama** (instrucción explícita) **ni leí CI de GitHub Actions** (no hay push). El resto
de la 7.1 tal como está escrita en la tarea (push + CI verde) queda sin cumplir a propósito.

Dejo el casillero sin marcar: la corrida de cierre existe y está documentada, pero no es verde — el
backend tiene 22 failed / 336 errors por una causa ajena a este constructor. No marco [x] una corrida
roja.

## Workflow follow-up

- Romper y auditar (ciclo completo, `14_forma_de_trabajo.md`); rompedor y auditor de una familia de
  modelo distinta del constructor (L-025).
- Archivar con el OK del auditor y actualizar `knowledge-base/` según "Knowledge Base Impact" de
  `proposal.md` (decisiones nuevas sólo se agregan).
