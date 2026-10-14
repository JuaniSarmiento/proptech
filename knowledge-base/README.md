# PropTech — Base de Conocimiento

Plataforma para administrar edificios en propiedad horizontal (y después barrios privados) en
Mendoza: liquidación de expensas, cuenta corriente de cada unidad, pagos y portal del vecino.
Proyecto de Alberto Cortez (lo trabaja también con el nombre **koris**) y Juan Ignacio Sarmiento.

Esta carpeta es **la fuente de verdad del MVP**. Todo lo que se construya sale de acá: si el código
contradice estos archivos, el error está en el código o hay que tomar una decisión nueva. Reemplaza a
`conocimiento/` desde la adopción de Active Stack v1 (D-093): misma fuente, estructura y nombres de
archivo del formato v1, sin renumerar ningún ID del proyecto (R, D, P, HU, L).

## Estado

- **Etapa**: construcción. Cambios 1a `infraestructura-base`, 1b `arranque-del-sistema` y 1c
  `cola-logs-y-respaldos` archivados (09, 11 y 14/10/2026); el próximo es el 1d
  `respaldos-y-restauracion`. Ver `CHANGES.md` para el estado de cada cambio y
  `12_fichas_de_changes.md` para su detalle.
- **El MVP arranca por edificios**; los barrios privados son la fase siguiente.
- **Preguntas abiertas**: el edificio piloto, el precio, el modo de redondeo y el cambio de titular,
  entre otras. Ver `10_preguntas_abiertas.md`; las que dependen de Alberto, con contexto y propuesta,
  están en su sección "Para Alberto".

## Índice de Archivos

| Archivo | Contenido | Cómo se actualiza |
|---------|-----------|--------------------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, objetivos por actor, alcance, hitos M1 a M3, diferencias con la especificación original | Se reescribe |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack tecnológico, arquitectura general, integraciones externas, API REST | Se reescribe |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores del sistema, RBAC, rutas públicas | Se reescribe |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Dominios, ERD, entidades, seed data | Se reescribe |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | Las reglas de cálculo (R01 a R41, agrupadas por dominio), cada una con su estado y los tests mínimos que la verifican | Se reescribe |
| [06_funcionalidades.md](06_funcionalidades.md) | Historias de usuario (HU-\*) por épica, con criterios de aceptación y reglas relacionadas | Se reescribe |
| [07_flujos_principales.md](07_flujos_principales.md) | Flujos extremo a extremo con sus casos de error | Se reescribe |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones aplicados, estructura de directorios, seguridad, variables de entorno | Se reescribe |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Las decisiones (D-001 en adelante) con su fecha, lo descartado, el porqué y quién decidió; supuestos (SU) | **Sólo se agrega** |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Inconsistencias (IN) y preguntas abiertas (P1 a P47) priorizadas, con la sección "Para Alberto" | Se reescribe: cada respuesta sale de acá y entra como decisión |
| [11_glosario.md](11_glosario.md) | El idioma común. El código usa estos mismos nombres, en español | Se reescribe |
| [12_fichas_de_changes.md](12_fichas_de_changes.md) | El detalle de cada cambio del roadmap (objetivo, reglas, dependencias, qué prueba el rompedor); el estado vive sólo en `CHANGES.md` | Se reescribe |
| [13_motor_de_reglas.md](13_motor_de_reglas.md) | Cómo entra el reglamento propio de cada edificio: el puerto de políticas, GoRules ZEN con su editor visual y el validador propio | Se reescribe |
| [14_forma_de_trabajo.md](14_forma_de_trabajo.md) | Cómo construye Juani cada cambio: constructor, rompedor y auditor en secuencia | Se reescribe |
| [15_lecciones.md](15_lecciones.md) | Lo que cada cambio enseñó sobre cómo se rompe el sistema; lo leen el constructor y el rompedor antes de empezar | **Sólo se agrega** |
| [16_proyecto_final.md](16_proyecto_final.md) | Las fases posteriores al MVP, cada una con su condición para arrancar | Se reescribe |

**Por qué dos formas de actualizar**: lo que describe cómo es el sistema hoy se reescribe para que
nunca convivan dos versiones; lo que cuenta cómo llegamos acá sólo se agrega, para no perder el
porqué de cada decisión. Si una decisión cambia, se escribe una nueva que la reemplaza.

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md)
6. Antes de codificar → [10](10_preguntas_abiertas.md), [12](12_fichas_de_changes.md) y `CHANGES.md`

## Cómo se trabaja

El desarrollo sigue el ciclo OPSX (explorar, proponer, construir, verificar, archivar) sobre esta
base. Ningún cambio se programa sin estar escrito antes, y el núcleo financiero se construye con
TDD: cada regla de `05_reglas_de_negocio.md` tiene sus tests escritos antes que el código. Juani
sigue su propio método (constructor, rompedor, auditor en secuencia, `14_forma_de_trabajo.md`);
Alberto trabaja con el ciclo OPSX de Active Stack v1. Los dos terminan en `openspec archive` y una
actualización de esta base.

## Material de origen (no incluido en este repositorio)

Algunos archivos citan rutas como `../especificacion/`. Corresponden al material de partida del
proyecto, que vive fuera de este repositorio:

- La **especificación funcional original** (19 módulos) y su **análisis de coherencia** (48 observaciones, H01 a H48).
- El documento **"Arquitectura de koris, contada a lo criollo"** de Alberto Cortez (7/10/2026).
- La **investigación de mercado** de octubre de 2026.

## Resumen Ejecutivo

PropTech liquida y cobra edificios en propiedad horizontal (y después barrios privados) en Mendoza:
el administrador configura su edificio, carga gastos y facturas, el sistema arma la liquidación y la
emite, el vecino paga por comprobante y el portal le muestra en qué se gasta su expensa. El resumen
en diez líneas, con el stack y los hitos, está al principio de
[01_vision_y_objetivos.md](01_vision_y_objetivos.md).
