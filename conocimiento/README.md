# PropTech · Base de conocimiento

Plataforma para administrar edificios en propiedad horizontal (y después barrios privados) en
Mendoza: liquidación de expensas, cuenta corriente de cada unidad, pagos y portal del vecino.
Proyecto de Alberto Cortez (lo trabaja también con el nombre **koris**) y Juan Ignacio Sarmiento.

Esta carpeta es **la fuente de verdad del MVP**. Todo lo que se construya sale de acá: si el código
contradice estos archivos, el error está en el código o hay que tomar una decisión nueva.

## Estado

- **Etapa**: diseño cerrado, sin código todavía (octubre de 2026).
- **El MVP arranca por edificios**; los barrios privados son la fase siguiente.
- **Preguntas abiertas**: cuál es el edificio piloto y el precio. Ver el final de `decisiones.md`.

## Cómo leerla

| Orden | Archivo | Qué tiene | Cómo se actualiza |
|---|---|---|---|
| 1 | [`mvp.md`](mvp.md) | Objetivo, usuarios, historias de usuario con criterios de aceptación, alcance, hitos y diferencias con la especificación original y con la arquitectura de koris | Se reescribe |
| 2 | [`reglas-de-negocio.md`](reglas-de-negocio.md) | Las 16 reglas de cálculo (R01 a R16), cada una con los tests mínimos que la verifican | Se reescribe |
| 3 | [`decisiones.md`](decisiones.md) | Las decisiones (D-001 en adelante) con su fecha, lo que se descartó, el porqué y quién decidió; preguntas abiertas al final | **Sólo se agrega** |
| 4 | [`glosario.md`](glosario.md) | El idioma común. El código usa estos mismos nombres, en español | Se reescribe |
| 5 | [`proyecto-final.md`](proyecto-final.md) | Las fases posteriores al MVP, cada una con su condición para arrancar | Se reescribe |
| 6 | [`forma-de-trabajo.md`](forma-de-trabajo.md) | Cómo se construye cada cambio: orquestador, constructor, rompedor y auditor | Se reescribe |

**Por qué dos formas de actualizar**: lo que describe cómo es el sistema hoy se reescribe para que
nunca convivan dos versiones; lo que cuenta cómo llegamos acá sólo se agrega, para no perder el
porqué de cada decisión. Si una decisión cambia, se escribe una nueva que la reemplaza.

## El MVP en diez líneas

1. **Meta**: que un administrador liquide y cobre un edificio mejor que con su Excel.
2. **Se valida** reproduciendo al centavo la última liquidación de un edificio piloto y corriendo un mes en paralelo.
3. **Usuarios**: titular, colaborador (por edificio asignado), consejo (sólo lectura) y vecino.
4. **Pagos**: el vecino sube su comprobante y el administrador lo confirma; la plata va directo a la cuenta del consorcio.
5. **Intereses simples** y configurables por edificio; nunca interés sobre interés.
6. **Cada peso de deuda vive en un solo lugar**: la cuenta corriente sólo agrega movimientos.
7. **Gastos** con grupo de reparto (quién paga), categoría (en qué se gasta) y tipo (ordinario o extraordinario).
8. **Facturas** leídas primero por el QR de ARCA y completadas por IA, siempre con confirmación humana.
9. **Stack**: Next.js, FastAPI, PostgreSQL con Row-Level Security, Redis con un worker, Caddy, Docker en un VPS.
10. **Hitos**: M1 Liquida, M2 Cobra, M3 Piloto.

## Material de origen (no incluido en este repositorio)

Algunos archivos citan rutas como `../especificacion/`. Corresponden al material de partida del
proyecto, que vive fuera de este repositorio:

- La **especificación funcional original** (19 módulos) y su **análisis de coherencia** (48 observaciones, H01 a H48).
- El documento **"Arquitectura de koris, contada a lo criollo"** de Alberto Cortez (7/10/2026).
- La **investigación de mercado** de octubre de 2026.

## Cómo se trabaja

El desarrollo sigue el ciclo OPSX (explorar, proponer, construir, verificar, archivar) sobre
`mvp.md`. Ningún cambio se programa sin estar escrito antes, y el núcleo financiero se construye con
TDD: cada regla de `reglas-de-negocio.md` tiene sus tests escritos antes que el código.
