Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN). "Verde"
quiere decir lint, formato, tipos y tests del lado tocado (L-005). Los tests de dependencias usan los
tres estados de L-001 con su cota de tiempo afirmada; los de configuración, las cinco formas de L-002.

## 1. Línea de base y deudas del cambio 1a

- [x] 1.1 Correr la suite completa antes de tocar nada (`bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh`) y anotar en el informe la cantidad de tests de cada lado como línea de base (L-003); si algo falla, frenar e informarlo como falla previa.
- [x] 1.2 Test en `tests/infra/test_compose.py` que exige que el healthcheck de `db` use `pg_isready -U "$${POSTGRES_USER}" -d "$${POSTGRES_DB}"` entrecomillado; verlo fallar, corregir `infra/compose.yaml` (D11) y verlo pasar.
- [x] 1.3 Borrar `test_imagen_del_fixture_coincide_con_la_de_compose_db`; agregar un test unitario que afirma que `tests/conftest.py` deriva la imagen de Compose (no tiene una imagen escrita a mano) y un test de integración que compara la imagen del contenedor de PostgreSQL que corrió (`get_wrapped_container().image.tags`) con la de Compose, nombrando las dos si difieren (D12). Verificar que el de integración falla si se fuerza otra imagen en el fixture y pasa con la real.

## 2. Configuración ampliada

- [x] 2.1 Tests en `tests/unitarios/test_configuracion.py` para `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` y `PROPTECH_PARAMETROS`: faltante, vacía, en blanco, tipo equivocado (`REDIS_PORT=abc`), fuera de rango (`0`, `70000`) y archivo de parámetros inexistente; cada error nombra la variable y ningún mensaje contiene el valor de la contraseña. Verlos fallar.
- [x] 2.2 Ampliar `Configuracion` (D11) y ajustar los fixtures de entorno de los tests existentes; verificar que pasan los nuevos y los de 1a (`test_arranque_api*`).

## 3. Tipo Dinero

- [x] 3.1 Tests unitarios de construcción: acepta `"20000"`, `"20000.5"`, `"-730.00"`, 12 dígitos enteros; rechaza `0.1` (float), `100` (int), `True`, `None`, `""`, `" 1.00"`, `"1,50"`, `"+1"`, `"1e3"`, `"NaN"`, `"Infinity"`, `"1.005"`, 13 dígitos enteros. Verlos fallar.
- [x] 3.2 Implementar `Dinero` y `MontoInvalido` en `proptech_core/compartido/dinero.py` (D5) hasta que pasen 3.1.
- [x] 3.3 Tests de serialización y comparación: `a_texto()` con dos decimales, `-0` a `"0.00"`, ida y vuelta por texto, igualdad y hash de `"5"` y `"5.00"`, `Dinero("0.10") != 0.1`, orden entre montos y `TypeError` al ordenar contra otro tipo, y que no existe `+` ni `-`. Verlos fallar, implementar, verlos pasar.
- [x] 3.4 Tests del adaptador pydantic: un modelo con campo monto rechaza `20000.0` y `20000` como número JSON (422 con el nombre del campo vía `TestClient`) y acepta `"20000.00"`; serializa a texto. Verlos fallar, implementar `__get_pydantic_core_schema__`, verlos pasar.
- [x] 3.5 Tests de integración de `TipoDinero` contra PostgreSQL real con una tabla temporal creada en el test: `"999999999999.99"` vuelve exacto y como `Dinero`; un `float`, un `Decimal` o un `str` en el bind fallan antes de la base. Verlos fallar, implementar, verlos pasar.

## 4. Parámetros del sistema

- [x] 4.1 Tests del cargador YAML: clave duplicada en cualquier nivel falla nombrándola; YAML mal formado y archivo vacío fallan con "mal formado" y línea; raíz que no es mapa falla; archivo inexistente o sin permiso de lectura falla. Verlos fallar e implementar el `SafeLoader` propio (D6).
- [x] 4.2 Tests del esquema con un archivo válido de referencia: tasa `"-1.00"`, `"10.01"` y `"3.005"` fallan; `"0.00"` y `"10.00"` pasan; días 32, `-1`, `"diez"` y `true` fallan, 0 y 31 pasan; tasa o fondo como número YAML (`3.5`, `3`) fallan pidiendo texto; forma de cálculo desconocida falla; nombre en blanco falla; campo desconocido y campo faltante fallan; claves de categoría repetidas, estado repetido y falta de `generales` fallan; `generales` con alcance `a_elegir` falla. Verlos fallar.
- [x] 4.3 Implementar los modelos y `leer_parametros` con el armado de un único `ParametrosInvalidos` que lista todos los problemas por ruta, sin valores; agregar un test con tres problemas a la vez que verifica las tres rutas en un mensaje. Verlos pasar.
- [x] 4.4 Test que lee `config/parametros.yaml` del repositorio y afirma cada default de D-042 (3.00, 0, proporcional por día, 0.00, nueve categorías, cuatro grupos con `generales` por coeficiente y todas las unidades, cuatro tipos, cuatro estados desactivados con factor 100.00 y cargo 0.00). Verlo fallar, escribir el archivo (D6), verlo pasar.
- [x] 4.5 Mover `pyyaml` a dependencias de ejecución en `pyproject.toml`, `uv lock`, y verificar `uv sync --locked` y que la imagen del backend importa `yaml`.
- [x] 4.6 Tests de arranque: la API con un archivo de parámetros con tasa negativa termina nombrando `intereses.tasa_mensual`; con `PROPTECH_PARAMETROS` faltante o vacía termina nombrando la variable. Verlos fallar, llamar a `leer_parametros` en `crear_app()`, verlos pasar.

## 5. Datos semilla

- [x] 5.1 Tests de `leer_semilla`: la semilla del repositorio es válida con los parámetros del repositorio y suma exactamente 1; fallan, nombrando unidad y campo: tipo `quincho`, grupo desconocido, identificador repetido, miembro de grupo inexistente, coeficiente `0.999999` de suma, coeficiente con 7 decimales o número YAML, superficie no positiva, `generales` distinto de `todas`, clave duplicada y campo desconocido. Más un test que recorre el archivo y no encuentra campos de persona ni textos con forma de email o teléfono. Verlos fallar.
- [x] 5.2 Escribir `config/semilla/edificio-ejemplo.yaml` (D10) e implementar `leer_semilla` reutilizando el cargador y el armado de errores de 4; verlos pasar.
- [x] 5.3 Test del comando `python -m proptech_core.compartido.semilla <ruta>`: código 0 con la semilla válida, 1 con una inválida mostrando los errores, y no abre conexión a la base (sin variables de PostgreSQL definidas igual funciona). Verlo fallar, implementar, verlo pasar.

## 6. Cierre de 1b: lo que la división dejó al descubierto

Sección nueva al dividir el cambio (ver design.md, "División del cambio"). Las secciones 1 a 5 están
hechas; estas cinco tareas cierran huecos entre ese código y sus specs, y son condición para archivar.

- [x] 6.1 Test de que Alembic (`migraciones/env.py`) corre con sólo las variables `POSTGRES_*` definidas (sin `REDIS_*` ni `PROPTECH_PARAMETROS`): hoy falla con `ConfiguracionInvalida`. Verlo fallar, separar la configuración de base de datos que usa Alembic de la de procesos (D11), verlo pasar junto con los de 2.1.
- [x] 6.2 Tests en `tests/infra/test_compose.py`: `api` recibe `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` (con `:?`) y `PROPTECH_PARAMETROS=/app/config/parametros.yaml`, monta `../config:/app/config:ro`; `migraciones` no recibe variables de Redis; `infra/.env.example` tiene `REDIS_PASSWORD` con un valor de ejemplo. Verlos fallar, cambiar `compose.yaml` y `.env.example`, verlos pasar.
- [x] 6.3 Tests de rangos de estados en `test_parametros.py`: factor `"-0.01"` y `"100.01"` fallan y `"0.00"`/`"100.00"` pasan; cargo fijo `"-1.00"` falla y `"0.00"` pasa; `estados: []` falla; fondo `"100.00"` pasa. Verlos fallar, ajustar los modelos (D6), verlos pasar.
- [x] 6.4 Test de que el error de `leer_parametros` con un factor o cargo fijo mal escrito (`"1,5"`) no contiene el valor recibido. Verlo fallar, sacar el valor del mensaje de `MontoInvalido` (D5), verlo pasar junto con los de 3.x.
- [x] 6.5 Corrida equivalente al CI desde un árbol limpio, con cada comando, su salida y la hora: `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `bash infra/ci/test-backend.sh`, `bash infra/ci/canario.sh backend`, los pasos de la web, `bash infra/ci/humo.sh` y gitleaks. Informar la cantidad de tests de cada lado contra la línea de base de 1.1 y explicar todo test salteado o deseleccionado (L-003, L-005).
