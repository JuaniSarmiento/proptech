# PropTech — Instrucciones para Agentes

> Este archivo (y su copia `AGENTS.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a mano a partir de `knowledge-base/` y `CHANGES.md` (Active Stack v1, D-093). No editar
> uno sin editar el otro: tienen que quedar idénticos (`diff AGENTS.md CLAUDE.md` vacío).

Plataforma para administrar edificios en propiedad horizontal (y después barrios privados):
liquidación de expensas, cuenta corriente, pagos y portal del vecino. Proyecto con Alberto Cortez y
sus hijos; lo programaba Juani solo (D-022) y desde el 14/10/2026 Alberto también construye cambios propios
sobre este mismo repositorio con Active Stack v1 (D-093). El comprador es el **administrador**; el
mercado de arranque es **Mendoza**.

> Estado y avances del proyecto se registran en `knowledge-base/` (decisiones) y en la nota personal
> de Juani (`obsidian.md`, symlink local, fuera del repo).

## Estado

- **Cambio 1a `infraestructura-base` archivado** (09/10/2026): el proyecto levanta con
  `cd infra && docker compose up --build` (ver README), con CI en GitHub Actions. Todavía no hay
  dominio: sólo el esqueleto y `/api/salud`.
- **Cambio 1b `arranque-del-sistema` archivado** (11/10/2026): configuración, `Dinero`, parámetros y semilla validada.
- **Cambio 1c `cola-logs-y-respaldos` archivado** (14/10/2026): Redis, worker ARQ con reintentos e
  idempotencia, logs estructurados en JSON, número de seguimiento (`request_id`) de punta a punta,
  `/api/salud` con la cola y `/salud-web`. Cerrado con **OK con deuda anotada** (D-091); la deuda
  queda en `knowledge-base/12_fichas_de_changes.md` ("Deuda técnica de las auditorías del 13/10"), con dueño por
  ítem (mayormente el cambio 7, antes de su primera tarea real).
- **Cambio 1d `respaldos-y-restauracion` archivado** (14/10/2026): servicio `respaldos` con `pg_dump`
  al arrancar y a diario, 14 copias, salud por antigüedad; `restaurar.sh` con destino validado; humo
  ampliado (Redis, worker, `request_id`, backup, restauración); `shellcheck` en el CI. Cerrado con
  **OK con deuda anotada** en la vuelta 3 (D-095); la deuda queda en
  `knowledge-base/12_fichas_de_changes.md` ("Deuda del cierre del 1d"), con dueño por ítem (mayormente
  el cambio 15 y el cambio 2).
- **Cambio 2a `aislamiento-por-administracion` archivado** (15/10/2026): candado del multi-tenant.
  Cuatro roles de PostgreSQL (arranque, `proptech_migrador`, `proptech_app`, `proptech_respaldo`),
  Row-Level Security forzada con `SET LOCAL` por administración, tablas `administracion`, `complejo`,
  `unidad` (mínima), `persona`, `asignacion_rol`, `accion_de_auditoria` y `auditoria`, alcance por
  edificio (404) y permiso por acción (403, D-096), auditoría de acciones sensibles de sólo agregar
  (D-016), el tenant del worker, la web fuera de la red de la base. Se prueba sin login, con la
  identidad inyectada. Cerrado en cuatro vueltas (constructor, rompedor, auditor); Juani eligió la
  opción B en la vuelta 3 (D-098). **OK con deuda anotada**; la deuda queda en
  `knowledge-base/12_fichas_de_changes.md` ("Deuda del cierre del 2a"), con dueño por ítem (mayormente
  el 2b y el 15); la verificación de arranque de las políticas de las tablas de negocio queda prometida
  como deuda del 15, por decisión de Juani.
- **Cambio 2c `endurecimiento-de-infraestructura` archivado** (16/10/2026): cabeceras de seguridad en
  Caddy, `no-new-privileges` y capacidades mínimas, PID 1 no root en los siete servicios, CI en pull
  requests con límites de tiempo y gitleaks por digest, humo con pasos nombrados, tabla única de
  variables en el README. Cerrado sin vuelta 3 (D-101). **OK con deuda anotada**; la deuda queda en
  `knowledge-base/12_fichas_de_changes.md` ("Deuda del cierre del 2c"), con dueño por ítem (mayormente
  el 15).
- **Cambio 3a `configuracion-del-edificio` archivado** (19/10/2026, D-103, D-104): el modelo del
  edificio completo (`complejo` y `unidad` enteros, `grupo_de_reparto` con los dos modos de
  coeficientes de D-100, `grupo_unidad`, `categoria_de_gasto`, `configuracion_versionada` de sólo
  agregar, el vocabulario de auditoría ampliado), con la base frenando todo cruce de edificio o de
  administración, también por SQL (R3A-3, R3B-5, RF-D-1). Primer cambio construido con **Codex
  (GPT-6.1-Sol, `xhigh`) como constructor**, por bloques con brief propio (detalle en
  `knowledge-base/14_forma_de_trabajo.md`); rompedor y auditor en dos vueltas (6 hallazgos en la
  primera, 12 en la segunda) y revisores de rol de backend y DBA sobre el HEAD final. **OK**; la deuda
  queda en `knowledge-base/12_fichas_de_changes.md` ("Deuda del cierre del 3a"), con dueño por ítem
  (mayormente el 3b, el 2b, el 15 y el 7).
- **Cambio 3b `pantallas-del-edificio` archivado** (20/10/2026): las siete pantallas de la superficie
  del administrador (mis edificios, resumen del edificio, padrón de unidades, grupos de reparto,
  categorías de gasto, intereses y vencimiento, confirmar "sin saldos previos"), a todo el ancho, con
  menú lateral agrupado con íconos, barra superior y ayuda "?" acoplada que empuja el contenido en vez
  de tapar (D-105, enmienda del shape del 19/10/2026 sobre Mercado Pago como referencia). Construido
  con **Claude Sonnet como constructor** por bloques de TDD estricto, una vuelta de rompedor y auditor
  Claude Opus (detalle en `knowledge-base/14_forma_de_trabajo.md`). **OK**; el acceso de desarrollo sin
  login (grupo 7) y la carga del edificio de ejemplo quedaron **sin construir, a la espera de la firma
  HIGH y CRITICAL de Juani o Alberto (D-094)**, movidos a un change propio, `acceso-de-desarrollo`. La
  deuda del cierre queda en `knowledge-base/12_fichas_de_changes.md` ("Deuda del cierre del 3b"), con
  dueño por ítem (mayormente el 2b).
- **Cambio 2.2a `roles-de-la-empresa` archivado** (20/10/2026): perfil × alcance, matriz de D-106,
  propietario/inquilino por relación persona-unidad, migraciones 0017/0018, personal único por alcance
  y consejo único por persona y edificio. Codex construye, Claude rompe y audita; Juani firmó E1 a E8
  y RR-1 a RR-4 aparte (`610eb4a`). Las 17 tareas están hechas; 7.2 en `4c24333`. Deuda y límites en
  `knowledge-base/12_fichas_de_changes.md` ("Deuda del cierre del 2.2a").
- **Cambio 2b `login-y-usuarios` archivado** (22/10/2026, CRITICAL, D-107, D-108): Clerk sólo para
  autenticación (usuario y contraseña también para vecinos, link mágico y Google, E17); autorización
  en la base; `persona.clerk_usuario_id` único **por administración** (migración 0019); invitaciones
  (migración 0020, tabla `invitacion`) con worker que las envía y reintenta; el super admin invita al
  personal con perfil y alcance y da de alta vecinos desde el padrón; selector de administración,
  sesión del servidor de Next (con `CLERK_SECRET_KEY`, E16); CSP estricta con nonce; Caddy deja de
  publicar `/api/*` salvo `/api/salud`. Cierra deuda de 2a (R9, V2-7, D-1, D-6), 2c (CSP) y 3a (RF-B-4);
  usuario real en la barra superior (deuda del 3b). Construido con una vuelta de rompedor y auditor,
  más verificación real con Juani al teclado contra Clerk de desarrollo (acortada por decisión de
  Juani, D-108). **36 de 37 tareas**: la 7.2 (aviso de privacidad) queda **en borrador, sin marcar**, a
  la espera de los datos legales del responsable antes de producción (decisión de Juani). Deuda y
  límites, incluido SU-01 (invitar a un email con cuenta previa en Clerk, no verificado), en
  `knowledge-base/12_fichas_de_changes.md` ("Deuda del cierre del 2b").
- **Cambio `acceso-de-desarrollo` archivado** (24/10/2026, HIGH, D-110): la carga del edificio de
  ejemplo, reescrita sobre el camino de "alta inicial" (D10 del 2b) para correr como `proptech_app`
  (nunca `proptech_migrador`), sin ningún `GRANT` nuevo; recorrido verificado a mano de las siete
  pantallas del 3b contra la API real, entrando con Clerk de desarrollo, en 1280 px, 320 px y con
  teclado. Firmado por Emiliano Caceres, firma ratificada por D-111 (Juani, 25/10/2026), que lo suma
  como firmante HIGH/CRITICAL junto a Juani y Alberto. **OK**; deuda y hallazgos (fallas de portabilidad Windows en la suite de
  pytest, `humo.sh` sin forma de aislarse de un stack real levantado, el CVE de Next.js 16.4.0 resuelto
  con la actualización a 16.4.3) quedan en D-110 y en la ficha 3b-bis de
  `knowledge-base/12_fichas_de_changes.md`.
- **Cambio 4a `cimientos-del-libro` archivado** (26/10/2026, HIGH, D-115 a D-119): cinco reglas de
  fronteras sobre `cuenta_corriente/` vacío; las tablas de sólo agregar pasan al rol de arranque, con
  sonda por el efecto y chequeo de arranque (`compartido/tablas_protegidas.py`); reparto por mayor resto
  y redondeo medio hacia arriba en `compartido/reparto.py`, con `hypothesis`; suma y resta de `Dinero`;
  el umbral de R30 por versión de configuración (`0021`); siete eventos del padrón auditados (`0022`);
  deuda D-053 cerrada. Firmó Juani E1 a E8. **OK**; deuda en la ficha 4 de
  `knowledge-base/12_fichas_de_changes.md` ("4a · deuda del cierre").
- **Cambio 4b `libro-de-movimientos` archivado** (27/10/2026, CRITICAL, D-121 a D-126): el libro
  construido — ocho tablas (`0023`), candado por cuenta, orden de imputación con fondo de reserva
  provisorio, corrección por contra-asiento o crédito con su tope (enmienda RB4B-01), permiso y
  auditoría de `corregir_movimiento` (`0024`), vocabulario ampliable de movimientos. Firmó Juani E1 a
  E16, la enmienda E7 y la deuda D8 (que bloquea el 7). **OK salvo D8**, que Juani anotó como deuda en
  vez de resolverla ahora; deuda completa en la ficha 4 ("4b · deuda del cierre").
- **Cambio 3c `pulido-de-la-configuracion` archivado** (28/10/2026, HIGH, D-128, D-129): los
  hallazgos del QA del 23/10/2026 (errores de formulario en su campo, ayudas de identificador,
  coeficiente y clave, confirmar "Quitar" en Personal, la nota de `/privacidad`); la **ubicación** del
  edificio con listas encadenadas provincia/departamento/localidad desde un archivo de Georef en el
  repo (CC BY 4.0) y `PATCH /complejos/{id}` para editarla; la **cantidad de pisos y subsuelos** del
  edificio y `unidad.piso` acotado a ese vocabulario; grupos de reparto desactivables (nunca
  borrables, como las categorías) y clave autogenerada desde el nombre; el dueño de las funciones
  durante una migración (E11 y su Enmienda, D-129). Tres migraciones nuevas (`0025` a `0027`,
  renumeradas detrás de las `0023`/`0024` del 4b al integrarlo sobre `main`). Firmado por Emiliano
  Caceres el 26/10/2026; E11 y su Enmienda por Juani el 27/10/2026. La tarea 7.1 (recorrido manual) se
  hizo el 27/10/2026; el PR #2 (DBA, backend, frontend, integración y rompedor dedicado a E11) cerró
  antes de mergear a `main` (`de47f7c`). Deuda del cierre en la ficha 3c de
  `knowledge-base/12_fichas_de_changes.md`.
  **Quedó fuera del 3c**, para el change nuevo **`2d · sesion-sin-persona`** (CRITICAL, D-130): la
  invitación abierta con la sesión de otra cuenta (B-3), el menú que no se adapta al rol (2.3),
  reinvitar el mismo email (2.4), `/personal` jerárquica (2.5/P66, D-127) y el **loop infinito en
  `/elegir-administracion?regreso=...`** (diagnosticado con cuatro lecturas independientes por la
  regresión del 27/10/2026, `.git/informes-regresion/02-acceso.md`). Los cinco comparten el mismo
  motivo: tocarlos sube el change entero a CRITICAL.
- **Regresión del 27/10/2026** (`.git/informes-regresion/01` a `05`) y reparto de su deuda (D-130,
  28/10/2026): **4c** recibe el mutante de RF-01 y el test de RF-02 sin forma contra-asiento, del 4b;
  **6** recibe el mutante de RB-5, del 4a; **7** conserva D8; el change nuevo **`3d · pulido-2`**
  (MEDIUM) junta la deuda chica de 3b/3c sin e2e ni test (api-falsa sin PATCH/Georef, ayuda "0 de 6",
  orden de `vocabularioDePisos`, clave inválida sin test, CSP/nonce sin test, día 31 de vencimiento);
  el aviso de `/privacidad` queda **bloqueante del 15** (Juani y Alberto). Detalle completo en D-130.
- **Cambio 2d `sesion-sin-persona` archivado** (28/10/2026, CRITICAL, D-131 a D-137): el 403
  `sin_acceso`, el selector sin loop, `--clerk-usuario` para el ejemplo, el menú y los controles por
  rol, `ver_personal` (migración `0028`), reinvitar y la invitación que dice con qué cuenta se está.
  Deuda en la ficha 2d de `knowledge-base/12_fichas_de_changes.md`.
- **Cambio 3d `pulido-2` archivado** (30/10/2026, MEDIUM, D-139): la API falsa de e2e con `PATCH` de
  edificio y grupos y Georef, el orden de pisos por altura (`SS2, SS1, PB, 1..N`), la ayuda "4 de 7",
  la raíz `/` que redirige (a `/edificios` con sesión, a `/ingresar` sin sesión), CSP y axe con tests,
  y el 422 del día de vencimiento y de la clave. Construyó Gianfranco (PR #3, `73884d6`); revisión
  independiente con rompedor, constructor y auditor (APROBADO). Deuda a C-26 y C-28, en la ficha 3d de
  `knowledge-base/12_fichas_de_changes.md`.
- **Cambio 6 `gastos-y-cargos` archivado** (30/10/2026, MEDIUM, D-140 a D-142): proveedores, gastos con
  sus cuatro estados, notas de crédito topeadas a su factura, cargos particulares sueltos o por Excel, el
  gasto mensual obligatorio en la categoría y el período de imputación de un gasto aprobado tarde (P36 y
  P37, ratificadas por Juani). Sólo backend y API (D-140), sin escribir en el libro. Migraciones `0029`
  a `0033`. Construyó Emiliano (PR #4, `b94577d`); revisión independiente con rompedor (Codex),
  constructor y auditor (APROBADO), que corrigió el permiso de lectura de los detalles por id. Deuda en
  la ficha 6 de `knowledge-base/12_fichas_de_changes.md`.
- **Deuda adelantada** (D-138, 30/10/2026): la deuda viva, verificada contra `main` (`e29e36d`), pasa a
  siete changes propios, uno por desarrollador: C-23 `humo-y-ci` (Gianfranco), C-24 `respaldos-2`
  (Emiliano, HIGH), C-25 `worker-y-logs` (Neyen), C-26 `pulido-web-3` (Matías), C-27
  `ejemplo-robusto` (Giuliano), C-28 `revisiones-independientes` (Juan Cruz) y C-29 `base-y-rls`
  (CRITICAL, sin asignar). Quien recién se suma toma sólo LOW o MEDIUM.
- **6c `pantallas-de-gastos`** (C-30, MEDIUM, D-144, 31/10/2026): las pantallas de HU-A3 y HU-A3b sobre
  la API del 6, de Juan Cruz, por proponer; cierra D12 del 6. Juan Cruz hace C-28 después del 6c, y el
  bloque del libro de C-28 pasa al rompedor del 4c.
- **Próximo**: **4c `intereses-saldo-inicial-y-moroso`** (CRITICAL, por proponer; lo construye un
  firmante de D-111) en el camino crítico; los siete de deuda adelantada en paralelo; después 4d
  `cambio-de-titular` (CRITICAL).
  Antes de cada cambio, constructor y rompedor leen `knowledge-base/15_lecciones.md`.
- Preguntas abiertas (la lista P, completa en `knowledge-base/10_preguntas_abiertas.md`): el edificio piloto (P1), el precio (P8), los
  extractos de Mendoza (P9), el modo de redondeo (P10), el cambio de titular (P11), la inscripción
  ante la AAIP (P12), el acceso de soporte (P13), el plazo del libre deuda (P14), los ingresos mayores que los gastos
  (P15), la parte de las unidades del consorcio (P16), el IVA (P17), el doble vencimiento (P19), quién
  aprueba una condonación (P20), los umbrales de R23 y R30 (P21) quién usa el editor de reglas (P22),
  los casos de borde para decidir antes de su cambio (P24 a P41), la validación de los valores de
  plata (P42), el contenido derivado de ProTecc (P43), la licencia (P44), las entrevistas a
  administradores (P45) y los nombres propios en el repo (P46), ramas o turnos con dos desarrolladores
  (P47), doble factor para el personal (P49) y borrar el usuario de Clerk al quitar la última
  asignación (P50); las del 4 partido (P51 a P56 para Juani, P57 a P60 para Alberto) y P70 (mapa
  interactivo de ubicación, sin fecha). P48 resuelta en D-099 (selector); P61 a P69 (ubicación, pisos,
  `/personal` jerárquica, cuentas de Mailinator, alcance de acceso y grupos) resueltas en D-128 y
  D-127 al cerrar el 3c. P18 conserva D-096, acotado por D-108 a "única por administración"; la matriz
  de P23 fue reemplazada por D-106. P12 quedó cerrada para autenticación en D-107; sigue abierta para
  la base de negocio.

## Stack Tecnológico

- **Backend**: Python + FastAPI + SQLAlchemy + PostgreSQL, migraciones con Alembic. Redis + worker ARQ
  para PDFs, emails e IA (D-038).
- **Frontend**: Next.js (App Router) + TypeScript, áreas de super admin/administrador, contador, auxiliar, consejo y vecino,
  instalable como PWA. El servidor de Next guarda el token; el navegador nunca lo ve (D-036). Sin app nativa. Toda interfaz pasa por la skill **impeccable**.
- **Monolito modular** (D-040): `backend/src/proptech_core` con los módulos `complejos`, `acceso`,
  `gastos`, `liquidacion`, `cuenta_corriente`, `pagos`, `avisos`, `politicas` (el motor de reglas,
  `knowledge-base/13_motor_de_reglas.md`) y `compartido`, cada uno con
  `dominio/` (reglas puras) · `aplicacion/` (casos de uso) · `puertos.py` · `adaptadores/`. Lo usan
  `proptech_api` (routers FastAPI) y `proptech_worker` (tareas). Los módulos se hablan sólo por
  `aplicacion`. Frontend en `web/`, despliegue en `infra/`.
- **Puerto de políticas** (D-064): las reglas propias de cada edificio entran por un puerto en
  `proptech_core` que devuelve acciones propuestas; el núcleo valida y registra. En el MVP se
  implementa con GoRules ZEN y su editor visual (D-066): el motor devuelve la plata como texto, el
  núcleo redondea y registra (D-067), y un validador propio bloquea la emisión ante cualquier
  respuesta fuera de contrato.
- **Tests**: unitarios (reglas, sin base), integración (PostgreSQL real en Docker), aceptación
  (la liquidación del piloto al centavo).
- **Despliegue**: VPS con Docker y Caddy (D-043). PDFs con WeasyPrint, avisos por email.
- **Parámetros iniciales** en `config/parametros.yaml` (D-042), nunca escritos en el código.
- **Criterio de costo**: ante dos opciones equivalentes, la que no cobra licencia ni uso (D-043).
- Detalle completo, con las versiones exactas tomadas del código:
  `knowledge-base/02_descripcion_general.md`.

## Base de Conocimiento

**La fuente de verdad es `knowledge-base/`.** Todo lo que se construye sale de ahí. Esta carpeta es
el repositorio del proyecto, **público**: https://github.com/JuaniSarmiento/proptech. Nunca
subir secretos, datos personales ni el material de Alberto (`especificacion/` está en `.gitignore`).

| Archivo | Qué tiene | Cómo se actualiza |
|---|---|---|
| `knowledge-base/01_vision_y_objetivos.md` | Propósito, objetivos por actor, alcance, hitos M1 a M3, diferencias con la spec | Se reescribe |
| `knowledge-base/02_descripcion_general.md` | Stack, arquitectura general, integraciones externas | Se reescribe |
| `knowledge-base/03_actores_y_roles.md` | Actores, RBAC (perfil × alcance según D-106), rutas públicas | Se reescribe |
| `knowledge-base/04_modelo_de_datos.md` | Dominios, ERD (existente y planificado), entidades y seed data | Se reescribe |
| `knowledge-base/05_reglas_de_negocio.md` | R01 a R41 (agrupadas por dominio, estado vigente, propuesta o pendiente): prorrateo, estados, intereses, imputación, redondeo, pagos, facturas, ordinaria/extraordinaria, cargos particulares, fondo de reserva, categorías de gasto. **Cada regla vigente es un test** | Se reescribe |
| `knowledge-base/06_funcionalidades.md` | Historias de usuario (HU-\*) por épica, con criterios de aceptación y reglas relacionadas | Se reescribe |
| `knowledge-base/07_flujos_principales.md` | Flujos extremo a extremo, con sus casos de error | Se reescribe |
| `knowledge-base/08_arquitectura_propuesta.md` | Patrones, estructura de directorios, seguridad y variables de entorno | Se reescribe |
| `knowledge-base/09_decisiones_y_supuestos.md` | D-001 en adelante, con lo descartado y el porqué; supuestos (SU) | **Sólo se agrega** |
| `knowledge-base/10_preguntas_abiertas.md` | Inconsistencias (IN) y preguntas abiertas (P1 a P48), con la sección "Para Alberto" | Se reescribe |
| `knowledge-base/11_glosario.md` | El idioma común. El código usa estos nombres, en español | Se reescribe |
| `knowledge-base/12_fichas_de_changes.md` | El detalle de cada cambio del roadmap (objetivo, reglas, dependencias, qué prueba el rompedor) | Se reescribe |
| `knowledge-base/13_motor_de_reglas.md` | El puerto de políticas (D-064) y GoRules ZEN con editor visual y validador propio (D-066, D-067): contrato, qué hace bien ZEN y su riesgo real, versiones, fallas y dónde entra en el roadmap | Se reescribe |
| `knowledge-base/14_forma_de_trabajo.md` | **Cómo construye Juani cada cambio**: constructor, rompedor y auditor en secuencia; aprueba el auditor | Se reescribe |
| `knowledge-base/15_lecciones.md` | Lo que cada cambio enseñó sobre cómo se rompe el sistema; lo leen constructor y rompedor antes de empezar | **Sólo se agrega** |
| `knowledge-base/16_proyecto_final.md` | Fases posteriores al MVP con su criterio de entrada | Se reescribe |
| `CHANGES.md` | **Todos los cambios en orden, con su estado** (los del roadmap y los de deuda adelantada, D-138): arrancá cada propose desde ahí y desde la ficha de `12_fichas_de_changes.md` | Se reescribe |

Si algo que vas a hacer contradice uno de estos archivos, **pará y preguntale a Juani (o a Alberto,
si el cambio es de él)**. Si cambia una decisión, se escribe una decisión nueva; nunca se edita una
vieja.

`especificacion/` es el material de partida (19 módulos, un análisis con 48 observaciones y
`arquitectura-alberto/`, el documento de arquitectura de Alberto). Es
**insumo, no verdad**: cuando contradice a `knowledge-base/`, gana `knowledge-base/`. El código
original de la especificación se descartó (D-002) y no se usa.

> ⚠️ Resolver las preguntas de prioridad alta de `knowledge-base/10_preguntas_abiertas.md` (P1, P9 a
> P11, P19, entre otras) antes de arrancar un cambio que dependa de ellas: cada ficha de
> `12_fichas_de_changes.md` dice "Bloqueado por" con las que le tocan.

## Skills Disponibles

Este repositorio **no versiona `.atl/skill-registry.md`**: la skill `skill-registry` se puede correr
(sólo escribe `.atl/`, que está en `.gitignore`). Cada agente resuelve sus skills desde `.claude/skills/` del repo (las
`openspec-*` generadas por `openspec init` en su momento) y desde `~/.claude/skills/` de su propia
máquina.

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend** | FastAPI / SQLAlchemy / Alembic / dominio hexagonal | `fastapi-templates` o equivalente, `test-driven-development`, `postgresql-optimization` |
| **Frontend** | Next.js / TypeScript / PWA | `typescript-advanced-types`, `tailwind-design-system` o la que use el proyecto, **impeccable** para toda interfaz |
| **Motor de reglas** | GoRules ZEN / jdm-editor | sin skill dedicada hoy; ver `knowledge-base/13_motor_de_reglas.md` |
| **Orquestación** | OPSX / changes | `openspec-explore`, `openspec-propose`, `openspec-apply-change`, `openspec-verify-change`, `openspec-archive-change` (versionadas en `.claude/skills/` de este repo, openspec 1.13.0) |

Cargá la skill correspondiente al contexto ANTES de escribir código.

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md), con el detalle de cada cambio
en [knowledge-base/12_fichas_de_changes.md](knowledge-base/12_fichas_de_changes.md). Resumen:

- **Total**: 30 cambios (D-088, más el 2 partido en 2a, 2b y 2c por D-097, el 3 en 3a y 3b, el
  2.2a de roles agregado por Juani el 20/10/2026, el 4 partido en 4a a 4d por su exploración del
  22/10/2026, el 3c de pulido agregado por Juani el 26/10/2026, y `2d` `sesion-sin-persona` y `3d`
  `pulido-2`, agregados por Juani al archivar el 3c, D-130), repartidos en M1 Liquida, M2 Cobra
  y M3 Piloto. Más los siete changes de deuda adelantada, C-23 a C-29 (D-138).
- **Camino crítico a M1** (reproducir al centavo la última liquidación del piloto):
  `1a → 1b → 1c → 1d → 2a → 3a → 4a → 4b → 4c → 5 → 7` (6 en paralelo desde el 4a si no escribe en
  el libro; 2b, 2c, 3b, 3c, 3d y 2d fuera de la cadena de dependencias, aunque `2d` se adelanta lo
  antes posible por D-130; el 4d después del 7, sin bloquear M1).
- **Archivados**: 1a `infraestructura-base`, 1b `arranque-del-sistema`, 1c `cola-logs-y-respaldos`, 1d
  `respaldos-y-restauracion`, 2a `aislamiento-por-administracion` (OK con deuda anotada, D-098), 2c
  `endurecimiento-de-infraestructura` (OK con deuda anotada, D-101), 3a `configuracion-del-edificio`
  (OK, D-103, D-104), 3b `pantallas-del-edificio` (OK, 20/10/2026), 2.2a `roles-de-la-empresa`
  (20/10/2026, D-106), 2b `login-y-usuarios` (22/10/2026, D-108), `acceso-de-desarrollo`
  (24/10/2026, D-110, D-111), 4a `cimientos-del-libro` (26/10/2026, D-119), 4b
  `libro-de-movimientos` (27/10/2026, D-121 a D-126, OK salvo la deuda D8 que bloquea el 7) y 3c
  `pulido-de-la-configuracion` (28/10/2026, D-128, D-129, tras el PR #2 y la Enmienda E11), 2d
  `sesion-sin-persona` (28/10/2026, D-131 a D-137, migración `0028`) y 3d `pulido-2` (30/10/2026,
  D-139, PR #3, sin migraciones) y 6 `gastos-y-cargos` (30/10/2026, D-140 a D-142, PR #4, migraciones
  `0029` a `0033`).
  Las migraciones del 3c son `0025` a `0027`: van después de las del 4a (`0021`, `0022`) y de las del 4b
  (`0023`, `0024`), renumeradas al integrarlo sobre `main`. La numeración 3c y 4a a 4d no renumera los
  demás changes (precedente D-097).
- **Deuda adelantada, pendientes de proponer** (D-138, 30/10/2026): C-23 a C-29, uno por
  desarrollador; tabla en `CHANGES.md`.
- **Sigue**: el 4c `intereses-saldo-inicial-y-moroso` (CRITICAL, por proponer).

**Antes de cualquier `/opsx:propose`**: leé `CHANGES.md`, identificá las dependencias del cambio y los
archivos de "Leer antes" de su ficha en `knowledge-base/12_fichas_de_changes.md`.

## Reglas Duras

> Reglas **globales** ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram):
> el proyecto las **hereda**, no se repiten acá.

**Qué no se corre nunca en este repositorio** (D-093): la base ya existe, está escrita a mano y
tiene meses de decisiones y un roadmap de 22 cambios. Correr cualquiera de estas herramientas de
fundación la pisa o la regenera con contenido que no es el nuestro:

- `active-orchestrator`: **tampoco elegir "Regenerar"** si en algún momento lo pregunta. Si la
  detección de fundación dice que falta algo, la respuesta es "ya existe, no lo toques", nunca
  invocar la skill.
- `kb-creator`, `roadmap-generator`, `agent-instruction`: generarían `knowledge-base/`, `CHANGES.md`
  y este mismo archivo desde cero, pisando el trabajo ya hecho.
- `openspec init`: el repositorio ya tiene `openspec/` inicializado.
- `openspec update`: reescribe `.claude/skills/openspec-*` y `.claude/commands/opsx/*` con la
  versión de openspec que esté instalada, que puede no coincidir con la fijada acá.

**openspec fijado en 1.13.0**: instalar con `npm install -g @fission-ai/openspec@1.13.0`, sin rango
abierto. No instalar la última versión de npm sin verificar antes que coincide.

**Gobernanza CRITICAL y HIGH, a cargo de Juani, Alberto o Emiliano** (D-094, D-111): la propuesta de
un cambio CRITICAL o HIGH la aprueba **Juani, Alberto o Emiliano**, dejándolo por escrito y con fecha
en la propuesta. No hace falta que apruebe el que no programa ese cambio puntual.

- **La plata nunca pasa por una cuenta de PropTech** (D-005). En el MVP no hay pagos integrados:
  el vecino informa con su comprobante y el administrador confirma (D-017, R11).
- **Cobros y cuenta corriente son dominio CRITICAL** (governance global): se propone y se espera
  aprobación de Juani, Alberto o Emiliano antes de escribir código ahí.
- **Base congelada** (D-087, D-089): nada de R42 en adelante y la base no se reabre salvo por hallazgos
  del código o respuestas a las preguntas abiertas.
- **TDD estricto en el núcleo**: cada regla vigente tiene sus tests mínimos escritos en
  `knowledge-base/05_reglas_de_negocio.md`; se ven fallar antes de escribir el código.
- **Montos en `Decimal`** (desde texto), `NUMERIC(14,2)` en la base y texto en el JSON; nunca `float`;
  el frontend no calcula montos; reparto por mayor resto (R07, D-046).
- **La cuenta corriente sólo agrega movimientos**; una corrección es un movimiento nuevo con motivo (R08).
- **La administración sale del login**, nunca de un parámetro del cliente: es el tenant, y Row-Level
  Security es el segundo candado. El edificio es un alcance dentro de ella, controlado por rol (R10, D-076).
- **Intereses simples**, sin capitalización (art. 770 del CCyC) (R03).
- **Nunca secretos ni datos personales reales en el repo.** Los comprobantes y facturas de prueba
  se arman con datos inventados.
- Juani trabaja en español rioplatense; nada de `cat/grep/find/sed/ls` (usar `bat/rg/fdfind/sd/eza`).

## Flujo de Trabajo

Dos ciclos conviven sobre el mismo repositorio y la misma base; los dos terminan en `openspec
archive` y una actualización de `knowledge-base/` según su sección "Knowledge Base Impact":

**El de Alberto, ciclo OPSX de Active Stack v1**:

```
1. Leer la KB relevante (knowledge-base/) y CHANGES.md   → entender el dominio y las dependencias
2. /opsx:explore (si el cambio lo pide, ⓔ en 01)          → pensar antes de proponer
3. /opsx:propose <nombre-del-change>                      → proposal + design + specs + tasks
4. /opsx:apply                                            → implementar con TDD estricto
5. /opsx:verify                                           → chequear contra specs, tasks y design
6. /opsx:archive <nombre-del-change> + marcar [x] en CHANGES.md
```

**El de Juani, constructor/rompedor/auditor en secuencia** (detalle completo en
`knowledge-base/14_forma_de_trabajo.md`):

```
1. Proponer ──► 2. Construir (TDD) ──► 3. Romper ──► 4. Auditar ──► 5. Archivar (commit + push)
```

El proponente escribe `proposal.md`/`design.md`/`tasks.md`; el constructor implementa con TDD
estricto; el rompedor intenta romperlo y deja cada falla como un test; el auditor da el veredicto
final (**OK** o **NO con motivos**) y un cambio queda aprobado cuando lo da. Los cambios CRITICAL o
HIGH llevan además la aprobación escrita de Juani, Alberto o Emiliano antes de codear (D-094, D-111).

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas
duras prevalecen.

## Investigación de mercado

El informe "Discovery Kooris Mendoza" (octubre de 2026, fuera del repo). **Kooris (o koris) es este mismo
proyecto** (D-035), así que el informe aplica directo: ~150 barrios y ~20 administradores en la
Cámara de Mendoza, 75.124 departamentos ocupados en el Gran Mendoza (Censo 2022), líderes
nacionales a ARS 2.950 por unidad, **AccessIN** como competidor mendocino en barrios.


## Memoria del proyecto en Obsidian

Al iniciar, leé `obsidian.md` para recuperar el estado y los pendientes. Al completar trabajo significativo, actualizá esa nota con avances verificables, decisiones y próximos pasos, sin incluir secretos. La base técnica `knowledge-base/` mantiene su función y sus propias reglas.
