# Proposal

> La firma de esta propuesta es **por adelantado** (Juani, 11/11/2026, opción 1): aprueba las elecciones
> E1 a E15 de `design.md` en la recomendación del orquestador; lo que no le cierre en la demo vuelve a En
> proceso.

## Why

El 4c dejó listo el caso de uso de saldo inicial, pero un administrador todavía no puede cargar su
edificio: hay que tipear unidad por unidad y no hay forma de traer la deuda previa desde su Excel. El 5 es
el siguiente del camino crítico a M1 (`4c → 5 → 7`): carga el padrón y los saldos previos desde una
plantilla de Excel, los compara unidad por unidad antes de tocar el libro (D-068) y cierra la migración.
Además resuelve PA-1 con el ajuste de saldo inicial (D-155), sin el cual un saldo cargado de menos no
tiene arreglo.

## Gobernanza

**CRITICAL** (importación y saldo inicial, D-077, D-094, D-111): un error carga deuda falsa a vecinos
reales y el libro sólo agrega (R08). Requiere la aprobación escrita y fechada de Juani, Alberto o Emiliano
en `## Aprobación` antes de escribir código; está firmada por adelantado.

## What Changes

- **Plantilla y padrón (H-007)**: un módulo nuevo `importacion` (D0); la plantilla `.xlsx` con hojas
  `Unidades`, `Saldos` y `Control` leídas por nombre (D1); lectura sin `float` (D2, E14); validación todo
  o nada con todos los errores por hoja, fila, columna y motivo (D3); límites de 2 MiB y 2.000 filas
  (E9, D1 del 6); unidades creadas con `crear_unidad` y propietarios sin invitar (E3); suma de
  coeficientes con la tolerancia de R01 (E4); padrón existente y reimportación por huella (E7).
- **Borrador y comparación (H-008)**: los saldos quedan en un borrador que no toca el libro; la
  comparación unidad por unidad contra la hoja `Control`, con el aviso de mes entero (E13); la aceptación
  registrada de las diferencias.
- **Confirmar (H-009)**: con el complejo bloqueado (E8), llama a `registrar_saldo_inicial` (4c), pasa el
  edificio a `confirmada`, audita y cierra el importador; la web nombra el estado (E12).
- **Ajuste de saldo inicial (H-010)**: una obligación nueva con su motivo para un saldo cargado de menos
  (E11, D-155), con interés desde el día siguiente.
- **Permisos y auditoría**: cuatro acciones nuevas (E6). **Migraciones** `0036` a `0039`.

## Qué queda fuera

- Importar gastos o cargos (6); grupos parciales y sus coeficientes (D-100, en pantalla); inquilinos,
  copropietarios y teléfonos; invitar a los propietarios (acción existente); editar un padrón existente
  desde el Excel; corregir un saldo cargado de más (correcciones del 4b); reabrir una migración (R09);
  adaptar el Excel real de Alberto a la plantilla (15).

## Capabilities

### New Capabilities

- `importacion-de-padron`: plantilla, lectura, validación todo o nada y alta del padrón.
- `borrador-de-saldos`: saldos en borrador, comparación por unidad y aceptación de diferencias.
- `confirmacion-de-saldos`: confirmar, cerrar el importador y el estado en la web.
- `ajuste-de-saldo-inicial`: deuda nueva con motivo para un saldo cargado de menos.

### Modified Capabilities

Ninguna: el 5 usa `saldo-inicial` (4c) sin cambiar su contrato.

## Impact

- **Código**: `backend/src/proptech_core/importacion/` (nuevo), `acceso/dominio/permisos.py` (acciones y
  matriz), `complejos/aplicacion` (pasar el estado a `confirmada` con candado), `cuenta_corriente/
  aplicacion` (crear la obligación del ajuste), `gastos/adaptadores/excel.py` (docstring),
  `proptech_api/importacion.py` (rutas), `web/src/app/edificios/[id]/importar/` y el resumen del edificio.
- **Base**: migraciones `0036` a `0039`.
- **Tests existentes que cambian** (L-064): `_DUENO_DE_TABLA`, `_RUTAS_CUBIERTAS`, vocabulario de
  auditoría, matriz de permisos, tablas protegidas, ensayo de roles y los tests que bajan migraciones.
- **Consumidores**: el 7 (liquida sobre el padrón y los saldos importados), el 10a (moroso de lo migrado).

## Lecciones que aplican (`knowledge-base/15_lecciones.md`)

- **L-064, L-083**: tests estructurales y tablas protegidas nuevas: barrido local de migraciones y ensayo
  de roles en H-008 y H-010.
- **L-066**: fórmulas leídas por su valor en caché, no como texto.
- **L-082**: la aceptación prueba su migración, no "la última".
- **L-019, L-035, L-049, L-061**: RED por aserción, commiteado antes del código, mutante por aserción de
  plata o seguridad.
- **L-076**: números de D y L únicos al archivar.

## Knowledge Base Impact

| Documento | Acción | Qué |
|---|---|---|
| `knowledge-base/05_reglas_de_negocio.md` | REWRITE | R09 (importador, borrador, control, confirmar, ajuste), R01 (la carga del importador rechaza fuera de tolerancia, E4) |
| `knowledge-base/04_modelo_de_datos.md` | REWRITE | `importacion`, `fila_de_saldo_importada`, `control_de_saldo`, `aceptacion_de_diferencias`, `ajuste_de_saldo_inicial` |
| `knowledge-base/03_actores_y_roles.md` | REWRITE | las cuatro acciones nuevas en la matriz |
| `knowledge-base/06_funcionalidades.md` | REWRITE | HU-A2 con la plantilla real |
| `knowledge-base/07_flujos_principales.md` | REWRITE | Flujo 2 (importar) con sus permisos |
| `knowledge-base/08_arquitectura_propuesta.md` | REWRITE | módulo `importacion`, tablas protegidas nuevas |
| `knowledge-base/09_decisiones_y_supuestos.md` | APPEND | E1 a E15 firmadas; E11 refina D-155; E4 sobre R01 |
| `knowledge-base/11_glosario.md` | REWRITE | plantilla, borrador de saldos, control, ajuste de saldo inicial |
| `knowledge-base/12_fichas_de_changes.md` | REWRITE | ficha 5 cerrada, deuda del cierre; P24 ya no bloquea |
| `knowledge-base/15_lecciones.md` | APPEND | lo que enseñe |
| `CHANGES.md` | REWRITE | estado de C-08 |

## Aprobación` antes de escribir código.

## Aprobación

Gobernanza CRITICAL (D-094, D-111). La completa, a mano, Juani, Alberto o Emiliano, con fecha y alcance.
Ningún agente la escribe.

| Firmante (Juani, Alberto o Emiliano) | Fecha | Alcance aprobado |
|---|---|---|
| Juani Sarmiento | 11/11/2026 | Por adelantado: la propuesta completa del 5 y todas sus elecciones con la recomendación que escriba el orquestador, partida en H-007 a H-010 sin rompedor (D-152); lo que no me cierre en la demo vuelve a En proceso |
