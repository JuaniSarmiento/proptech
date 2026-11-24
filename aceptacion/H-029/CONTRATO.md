# Contrato que asume la aceptación de H-029

La pantalla de la morosidad en navegador real contra la API falsa (`web/e2e/api-falsa.ts`). Siguen vigentes los
contratos de H-027 (la lectura) y H-028 (el Excel). Si el constructor necesita cambiar algo de esto, frena y lo pide.
Locators exactos y alertas filtradas por texto (L-085).

Fuente: `HISTORIAS.md` (H-029), `openspec/changes/morosidad/design.md` (E8), D-036, D-167, HU-A8.

## El menú

`seccionesDelEdificio` suma "Morosidad" (`/edificios/{id}/morosidad`), en el grupo "Liquidación", con la acción
`ver_morosidad` (L-101): sólo se ve con esa acción en ese edificio.

## `/edificios/{id}/morosidad`

Dentro del edificio, con el menú lateral. Lee `GET /api/complejos/{id}/morosidad` desde el servidor de Next.

- Encabezado (`heading`) "Morosidad".
- Una región (`role="region"`) con nombre accesible "Resumen de la morosidad" que muestra, cada uno con su rótulo
  visible: "Unidades que deben" con `resumen.unidades_con_deuda`, "Morosos críticos" con `resumen.morosos_criticos` y
  "Total vencido" con `resumen.total_vencido`. Debajo, el texto "Intereses al dd/mm/aaaa" con `intereses_al`, o "Sin
  intereses registrados" si es nulo.
- Una lista (`role="list"`) con nombre accesible "Unidades con deuda" y un `listitem` por fila de la API, **en el
  mismo orden**, que muestra: el identificador de la unidad; los propietarios separados por coma (o "Sin
  propietarios cargados"); la situación en palabras ("Moroso crítico", "Con deuda vencida", "Deuda de intereses",
  "Bajo el umbral"); el total vencido, el capital y los intereses con su rótulo; las liquidaciones vencidas; y
  "Desde el dd/mm/aaaa · N días" con `vencida_desde` y `dias`. Cada dato en su propio bloque (L-101).
- Los montos se muestran con `dinero` de `lib/formato.ts` (punto de miles, coma decimal) **tal como vienen de la
  API**: la pantalla no suma, no resta ni redondea nada (N03).
- Sin filas: en lugar de la lista, un `role="status"` con "No hay unidades con deuda vencida".
- Con `exportar_morosidad` en ese edificio (de la sesión): un link "Exportar a Excel" a
  `/edificios/{id}/morosidad/excel` (un `<a>` común: la descarga sale del clic, L-099). Sin esa acción, el link no
  está.
- Sin `ver_morosidad` (la API responde 403): el estado "sin permiso" de `Estados` con lo que no puede hacer y el
  permiso faltante `ver_morosidad`.
- A 320 px sin scroll horizontal y sin errores de axe. Pasa por la skill **impeccable**.

## `/edificios/{id}/morosidad/excel` (ruta de Next)

Como `importar/plantilla/route.ts`: el servidor de Next pide `GET /api/complejos/{id}/morosidad/excel` con el token
de la sesión (D-036) y entrega los bytes con `Content-Type` de Excel y el mismo `Content-Disposition` (el nombre del
archivo) que devolvió la API, y `Cache-Control: no-store`. Sin sesión 401, sin permiso 403, no existe 404, otro error
502.

## API falsa

| Edificio | Qué tiene |
|---|---|
| `00000000-0000-0000-0000-000000002701` "Torre Ficticia" | `GET .../morosidad` devuelve `fecha` "2026-11-18", `intereses_al` "2026-10-31", `resumen` `{"unidades_con_deuda": 4, "morosos_criticos": 1, "total_vencido": "79112.35"}` (**a propósito un centavo más que la suma de las filas**, para N03) y cuatro filas en este orden: `1A` (`...027101`, ["Ana Prueba"], `moroso_critico`, total "30812.34", capital "30000.00", intereses "812.34", 3 liquidaciones, desde "2026-09-10", 69 días); `1B` (`...027102`, ["Carla Prueba"], `con_deuda_vencida`, "40000.00", "40000.00", "0.00", 1, "2026-11-10", 8); `2B` (`...027104`, ["Ana Prueba"], `con_deuda_vencida`, "8000.00", "8000.00", "0.00", 1, "2026-11-10", 8); `2A` (`...027103`, [], `bajo_umbral`, "300.00", "300.00", "0.00", 1, "2026-11-10", 8). `GET .../morosidad/excel` devuelve unos bytes que empiezan con `PK\x03\x04` y `Content-Disposition: attachment; filename="morosidad-torre-ficticia-2026-11-18.xlsx"`. |
| `00000000-0000-0000-0000-000000002702` "Edificio al día" | `GET .../morosidad` con `intereses_al` nulo, el resumen en cero y sin filas. |

Las dos rutas responden **403** con `permiso_faltante` (`ver_morosidad` o `exportar_morosidad`) a quien no tiene la
acción, igual que la API real. Sesiones: el super admin de siempre trae `ver_morosidad` y `exportar_morosidad` en
todos los edificios; **`user_consejo`** (nueva) trae en esos dos edificios sólo `ver_configuracion_del_edificio`,
`ver_liquidaciones` y `ver_morosidad`; `user_vecina` no trae ninguna de las dos acciones de la morosidad.
