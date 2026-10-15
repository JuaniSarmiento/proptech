## Why

Las auditorías de Alberto del 13/10 y el cierre del 1d dejaron deuda de infraestructura con dueño "2"
que no cambia quién ve qué dato: cabeceras del proxy, volúmenes de Caddy, el CI que sólo corre en
`push`, contenedores con más privilegios de los que necesitan, PID 1 no root probado en un solo
servicio, un humo que no dice qué paso falló y que nunca congela las dos dependencias a la vez, y una
tabla de variables del README que no existe. Al partir el cambio 2 (**D-097**, a partir de la revisión
del arquitecto del 15/10/2026), esa deuda sale del 2a (el candado) a este cambio, el **2c**, para que la
aprobación CRITICAL del candado no cargue con trabajo de otro perfil de riesgo.

Cubre: **D-051** (las notas de seguridad del 1a: `Via`, `X-Powered-By`, HEAD), **D-087** y **D-089**
(la deuda de las auditorías del 13/10), **D-095** (la deuda del cierre del 1d: F7 resto, la doble
congelada, PID 1 no root, el orden de la 8.1) y **D-097** (la partición). No toca reglas de negocio
(R..) ni historias (HU-..): es infraestructura.

## Gobernanza

**Nivel MEDIUM**: no toca datos de ninguna administración, ni credenciales, ni el esquema de la base.
Se construye con checkpoints y sin aprobación previa de un socio (D-094: MEDIUM no la necesita). Las
decisiones no obvias del design se muestran a Juani en el informe del constructor. Si al construir
aparece algo que cambia quién ve qué dato, se frena y pasa al 2a o a un cambio CRITICAL.

## What Changes

- **Cabeceras de seguridad en Caddy** (`nosniff`, `Referrer-Policy`, `X-Frame-Options`,
  `Permissions-Policy`), sin `Server`, `Via` ni `X-Powered-By` (también lo que viene de la web y la API),
  y HEAD con las mismas cabeceras que GET y sin cuerpo.
- **Volúmenes de Caddy** para `/data` y `/config`.
- **Contenedores endurecidos**: `no-new-privileges` en todos los servicios, `cap_drop: [ALL]` con sólo
  las capacidades que cada uno necesita, y PID 1 no root verificado **en cada** servicio que corre
  código del proyecto, con el rojo visto en cada uno.
- **CI**: también en `pull_request`, con `timeout-minutes` en cada trabajo y gitleaks fijado por
  digest.
- **Humo**: cada paso dice su número y su descripción al fallar; "aparece uno solo" se verifica como
  exactamente uno; la base y Redis congelados a la vez; las cabeceras de seguridad de punta a punta.
- **README**: la tabla completa de variables, con un test que la mantiene al día con
  `infra/.env.example`.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `entorno-de-ejecucion`: cabeceras del proxy, volúmenes de Caddy y contenedores endurecidos.
- `integracion-continua`: CI en pull requests con límite de tiempo y gitleaks por digest; pasos del
  humo con nombre, "uno solo" exacto y la doble congelada.

## Que intente romper el rompedor

- Una respuesta que se escapa sin cabeceras: un error 502 de Caddy, una redirección de Next, un 404 de
  la API, un HEAD.
- `Via` o `X-Powered-By` que vuelven desde atrás del proxy.
- Un servicio que arranca como root porque una imagen cambió su `USER`, y el chequeo que no lo ve
  (L-016).
- Una capacidad de más que nadie justificó, o una de menos que sólo rompe al reiniciar.
- Un trabajo del CI que cuelga sin límite, un pull request que no corre el CI, un tag de gitleaks
  re-publicado con otro contenido.
- Un paso del humo que falla sin decir cuál, uno que pasa con dos apariciones, y la doble congelada que
  deja `db` o `redis` pausados si el paso falla (L-014).
- Una variable de `.env.example` que no está en la tabla del README.

## Lecciones que aplican

| Lección | Tareas |
|---|---|
| L-001 · dependencia que no responde | 4.2 (base y Redis congelados a la vez) |
| L-003 · contar los tests | 1.1 y 6.1 |
| L-004 · otro camino | 2.1 (tests estáticos del `Caddyfile`) contra 4.3 (las cabeceras de punta a punta por el proxy) |
| L-005 · verde es todo el workflow | 3.1 y 6.1 |
| L-010 · la corrida de cierre va al final | 6.1 |
| L-013 · mutar sin commit exige copia | 2.2, 2.3, 4.1 |
| L-014 · `set -e` dentro de `||` | 4.1 y 4.2 (cada paso con su chequeo explícito y un `trap` que despausa) |
| L-016 · una observación tiene que poder dar otro resultado | 2.3 (PID 1 con el rojo en cada servicio), 4.1 (`exactamente_uno` visto fallar con dos) |

## Fuera del cambio

- **Todo lo que hace al candado** (2a): roles, RLS, credenciales por rol, la web fuera de la red de la
  base.
- **CSP en Next** (2b): una CSP sin pantallas no prueba nada.
- **HSTS** y el dominio real: con el despliegue (cambio 15).
- **Dependabot**: cambio 15 (E4 del 2a).
- **Secretos de Compose** (la contraseña del rol de arranque en el entorno del contenedor terminado de
  `migraciones`): con el despliegue (cambio 15).

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 15/10/2026): `01_vision_y_objetivos.md`,
`02_descripcion_general.md`, `03_actores_y_roles.md`, `04_modelo_de_datos.md`,
`05_reglas_de_negocio.md`, `06_funcionalidades.md`, `07_flujos_principales.md`,
`08_arquitectura_propuesta.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`,
`11_glosario.md`, `12_fichas_de_changes.md`, `13_motor_de_reglas.md`, `14_forma_de_trabajo.md`,
`15_lecciones.md`, `16_proyecto_final.md`, `README.md`.

- `12_fichas_de_changes.md`: **REWRITE** de la ficha 2c (cierre) y de las filas de deuda que resuelve.
- `08_arquitectura_propuesta.md`: **REWRITE** de la sección de seguridad (cabeceras, contenedores).
- `09_decisiones_y_supuestos.md`: **APPEND** de una decisión con las elecciones de código del 2c si el
  auditor las pide (capacidades por servicio, digest de gitleaks).
- `15_lecciones.md`: **APPEND** de lo que proponga el auditor al cerrar.
- `01` a `07`, `10`, `11`, `13`, `14`, `16` y `README.md` de la base: none. No cambia ninguna regla,
  historia, flujo, pregunta ni término.
- Fuera de `knowledge-base/`: `CHANGES.md` (**REWRITE** del estado de C-05c al archivar) y el `README.md`
  de la raíz (la tabla de variables).

## Impact

- **Infra**: `infra/compose.yaml`, `infra/Caddyfile`, `infra/ci/humo.sh`, `.github/workflows/ci.yml`,
  `web/next.config.ts`, `README.md`.
- **Tests**: `backend/tests/infra/` (`test_compose.py`, `test_caddyfile_seguridad.py`,
  `test_ci_workflow.py`, `test_humo.py`, `test_readme_variables.py`).
- **Dependencias nuevas**: ninguna. **Contrato de la API**: ninguno.
- **Depende de**: 2a (los dos tocan `compose.yaml` y `humo.sh`; en secuencia no se pisan).
