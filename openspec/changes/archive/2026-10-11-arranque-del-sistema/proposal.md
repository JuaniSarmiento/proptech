## Why

El cambio 1a dejó un esqueleto que arranca y se prueba solo, pero sin las piezas de datos que todos los
cambios siguientes dan por existentes: un lugar único con los parámetros con que arranca un edificio,
una representación de la plata que no admita `float` y un edificio de ejemplo para desarrollar. Si
cada cambio de M1 las inventa a su manera, el cambio 4 (cuenta corriente) y el 7 (liquidación) se
construyen sobre convenciones distintas. Es la primera mitad de la ficha
`1b · arranque-del-sistema` de `conocimiento/roadmap.md`.

**División**: el cambio original tenía además la cola con worker, los logs estructurados con
`request_id` y los backups. Resultó demasiado grande para una vuelta del constructor y se partió: esa
parte pasa al cambio `cola-logs-y-respaldos`. Este cambio queda con lo que ya está construido (las
secciones 1 a 5 de `tasks.md`) más una sección corta que cierra los huecos que la división dejó a la
vista (ver `design.md`, "División del cambio").

Decisiones que cubre: **D-042** (archivo de parámetros generales), **D-046** (montos `Decimal` desde
texto, `NUMERIC(14,2)`, texto en el JSON, nunca `float`), **D-047 punto 4** en su parte de parámetros
con su lector y edificio de ejemplo, y las "Notas para cambios siguientes" de **D-051** (comillas en
`pg_isready` y el test tautológico de la imagen del fixture). Reglas que toca sólo en su
representación o sus valores iniciales: **R01**, **R02** (desactivados en edificios por D-030),
**R03**, **R07** (representación de montos), **R15** y **R16**. Prepara **HU-A1** sin implementarla:
la copia de los valores a un edificio es del cambio 3.

## What Changes

- **`config/parametros.yaml`** con los valores iniciales de D-042 y un **lector validado** en
  `proptech_core/compartido` que rechaza el archivo mal formado con errores que nombran cada campo.
  La API no arranca con parámetros inválidos.
- **Tipo `Dinero`** sobre `Decimal` en `proptech_core/compartido`: se construye sólo desde texto, se
  serializa como texto, rechaza `float` (y `int`, `bool`, `NaN`, infinito, notación científica y más
  de dos decimales), con adaptadores para pydantic y para SQLAlchemy (`NUMERIC(14,2)`). Sin
  aritmética: el reparto es del cambio 4.
- **Datos semilla del edificio de ejemplo** como archivo versionado (`config/semilla/edificio-ejemplo.yaml`),
  ficticio, validado contra los parámetros, con un comando que lo verifica. No se inserta en la base.
- **Configuración ampliada**: `PROPTECH_PARAMETROS` y las variables de Redis (`REDIS_HOST`,
  `REDIS_PORT`, `REDIS_PASSWORD`) con la misma familia de errores de L-002. Redis llega en el cambio
  siguiente; ver en `design.md` (D11) por qué las variables quedan obligatorias desde ahora.
- Deudas de 1a: comillas en `pg_isready -U "${POSTGRES_USER}"`; el test tautológico de la imagen del
  fixture se reemplaza por uno que mira la imagen del contenedor de PostgreSQL que de verdad corre.

## Capabilities

### New Capabilities

- `parametros-del-sistema`: qué contiene `config/parametros.yaml` y qué hace el lector con un archivo
  válido, mal formado o fuera de rango.
- `representacion-de-montos`: cómo se construye, se compara, se serializa y se guarda un monto, y qué
  entradas se rechazan.
- `datos-semilla`: qué contiene el edificio de ejemplo y cómo se valida.

### Modified Capabilities

- `entorno-de-ejecucion`: la configuración suma `PROPTECH_PARAMETROS` y las variables de Redis, con la
  misma familia de errores; las migraciones no dependen de ellas.
- `integracion-continua`: el chequeo de versión desalineada de PostgreSQL mira el contenedor real en
  vez de compararse consigo mismo.

## Fuera del cambio

- **Cola, worker, idempotencia, logs estructurados, `request_id`, `/salud-web`, backups y el humo que
  los verifica**: cambio `cola-logs-y-respaldos`.
- **Reparto por mayor resto y cualquier aritmética de montos**: cambio 4 (R07).
- **Usuarios, login, roles, tenant y Row-Level Security**: cambio 2.
- **Tablas de edificios, unidades, grupos y categorías, y la copia de parámetros a un edificio
  (HU-A1)**: cambio 3, que también inserta el edificio de ejemplo en la base.
- **Pantallas**: ninguna.

## Knowledge Base Impact

- `conocimiento/decisiones.md`: **APPEND**. Una decisión con las elecciones de este cambio (esquema de
  `parametros.yaml` con porcentajes como texto y tope de tasa 10 %; `Dinero` sin aritmética y
  construido sólo desde texto; semilla como archivo sin persistir hasta el cambio 3; variables de
  Redis obligatorias desde 1b) y la división del cambio con su motivo.
- `conocimiento/roadmap.md`: **REWRITE** de la ficha 1b (dividida: 1b parámetros, montos y semilla;
  `cola-logs-y-respaldos` con el resto) y **REWRITE** de la ficha 3 para que inserte el edificio de
  ejemplo en la base y fije la precisión de los coeficientes.
- `conocimiento/glosario.md`: none en este cambio; los términos de cola, seguimiento y respaldo se
  mudan con su cambio.
- `conocimiento/lecciones.md`: lo propone el auditor al cerrar; este cambio no lo escribe.
- `conocimiento/reglas-de-negocio.md` y `conocimiento/mvp.md`: none. Los valores del archivo son los
  defaults que esas reglas ya fijan.

## Impact

- **Código**: `backend/src/proptech_core/compartido/` (`configuracion.py`, `dinero.py`,
  `dinero_sqlalchemy.py`, `cargador_yaml.py`, `parametros.py`, `semilla.py`),
  `backend/src/proptech_api/app.py`, `backend/migraciones/env.py` (tarea 6.1).
- **Config**: `config/parametros.yaml`, `config/semilla/edificio-ejemplo.yaml`.
- **Infra**: `infra/compose.yaml` (healthcheck de `db`; variables y montaje de `config/` en `api`),
  `infra/.env.example`.
- **Dependencias**: `pyyaml` pasa de desarrollo a ejecución. Sin dependencias nuevas en la web.
- **Configuración nueva**: `PROPTECH_PARAMETROS`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`.
- **Contrato HTTP**: sin cambios.
