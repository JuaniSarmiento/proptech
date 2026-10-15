# Visión y Objetivos

> Alcance acordado entre el 08/10/2026 y hoy (decisiones D-003 a D-094). **El MVP arranca por
> edificios** (D-027); los barrios privados vienen después. Las reglas que citan las historias
> (R01 a R41) están en `05_reglas_de_negocio.md`; los términos, en `11_glosario.md`. Las reglas propias
> de cada edificio (bonificaciones, cargos recurrentes, controles propios) entran por el motor de
> reglas, GoRules ZEN con su editor visual (`13_motor_de_reglas.md`, D-064, D-066, D-067); los intereses y
> el fondo de reserva son menús cerrados de la configuración (D-080). **Se
> reescribe** cuando cambia una decisión.

## Propósito del sistema

Plataforma para administrar edificios en propiedad horizontal (y después barrios privados) en
Mendoza: liquidación de expensas, cuenta corriente de cada unidad, pagos y portal del vecino.
Proyecto de Alberto Cortez (lo trabaja también con el nombre **koris**) y Juan Ignacio Sarmiento.

Que un administrador de edificios en propiedad horizontal **liquide y cobre su edificio de punta
a punta, mejor que con su Excel**.

**Se da por cumplido cuando** un edificio piloto corre un mes en paralelo con su método actual y
el cierre da igual al centavo.

### El MVP en diez líneas

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

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|---|---|---|
| **Administrador titular** | Liquidar y cobrar el edificio de punta a punta, mejor que con su Excel | Configurar el edificio (HU-A1), cargar el edificio desde Excel (HU-A2), cargar gastos y cargos particulares (HU-A3, HU-A3b), revisar la preliquidación (HU-A4), emitir la liquidación (HU-A5), confirmar pagos informados (HU-A6), validar con el extracto del banco (HU-A7), ver la morosidad (HU-A8), corregir errores sin perder historial (HU-A9), emitir certificados de libre deuda (HU-A10), condonar intereses y marcar gestión judicial (HU-A11, propuesta) |
| **Colaborador** | Operar los edificios que le asignan, con nivel "ver" o "editar", sin cerrar ni anular liquidaciones ni pagos (D-037) | Las mismas acciones del titular dentro de su alcance, salvo las exclusivas del titular (matriz de permisos de D-096) |
| **Vecino** | Entender su expensa y pagarla desde el celular | Entrar al portal con todas sus unidades juntas (HU-V1), ver cuánto debe (HU-V2), entender en qué se gastó la plata (HU-V3), informar un pago con su comprobante (HU-V4), descargar comprobantes (HU-V5), recibir avisos antes del vencimiento y en mora (HU-V6) |
| **Consejo** (o comisión directiva) | Controlar las cuentas del edificio sin poder modificar nada | Ver morosidad, gastos aprobados y liquidaciones emitidas (HU-C1) |

## Para quién

- **Tipo de complejo**: edificios en propiedad horizontal (D-027). El modelo soporta barrios
  privados desde el día uno (estados de lote, cargos por estado), pero no se configuran ni se
  prueban en el MVP.
- **Desarrollo**: Juani empezó como único desarrollador (D-022); desde la adopción de Active Stack v1
  (D-093), Alberto también construye cambios propios sobre este mismo repositorio con el ciclo OPSX.
- **Piloto**: un edificio con contacto directo de Alberto (D-033). Mientras no estén sus datos se
  diseña con un edificio de ejemplo; M1 no se cumple sin datos reales.
- **Usuarios** (D-009, D-037): administrador titular, colaborador, vecino y consejo; ver la tabla de
  objetivos por actor arriba y la matriz de permisos (RBAC) en `03_actores_y_roles.md`. El inquilino
  como rol separado queda para después del MVP; en edificios es frecuente, así que se valida con el
  piloto que la persona de contacto alcance (D-032).

## Alcance v1.0 (MVP)

**Entra**: configuración del edificio, alta desde Excel con tipos de unidad (departamento, cochera,
baulera, local), archivo de parámetros iniciales, categorías de gasto parametrizables, gastos manuales y desde factura (QR de ARCA más IA, nunca aprobados sin la confirmación del administrador), sueldo
del encargado cargado como gasto, expensa ordinaria y extraordinaria, fondo de reserva como
concepto de liquidación, cargos particulares, reglas propias de cada edificio con el motor de reglas, preliquidación,
controles antes de emitir con alertas aceptadas, emisión con PDF y links de descarga firmados, cuenta corriente con
imputaciones e intereses, pagos por comprobante con confirmación del administrador, ayuda del
extracto bancario, morosidad, correcciones, portal del vecino con todas sus unidades juntas, vista
del consejo, avisos por email, login real, roles, aislamiento entre administraciones y alcance por edificio, auditoría y backups
probados.

## Fuera de alcance

**No entra**: barrios privados en producción, cálculo del sueldo del encargado (escala SUTERH),
inquilino como rol, Mercado Pago y otros medios de cobro integrados (MODO, débito, Red Link,
Rapipago, SIRO), reservas del SUM, bot de WhatsApp, consultas de reglamento con IA, asambleas,
órdenes de compra, tableros complejos, tesorería (saldo de caja y saldo acumulado del fondo de
reserva), contabilidad integral, cálculo de consumos por medidor (se cargan como cargos
particulares). El historial de activos y Mercado Pago van en la v1.1. El detalle de las fases
posteriores está en `16_proyecto_final.md`.

## Hitos

| Hito | Historias | Se demuestra cuando |
|---|---|---|
| **M1 · Liquida** | A1, A2, A3 (carga manual), A3b, A4, A5, A9 | Con los datos del edificio piloto, el sistema reproduce su última liquidación al centavo |
| **M2 · Cobra** | A6, A7, A8, A10, A11 (propuesta), V1 a V6, C1 | Un vecino informa un pago, el administrador lo confirma en un clic y queda imputado con la fecha correcta |
| **M3 · Piloto** | A3 (factura con QR e IA) | Un mes completo en paralelo con el método actual y el cierre coincide |

### Cambios de OPSX por hito (detalle y fichas en `12_fichas_de_changes.md` y `CHANGES.md`)

| Hito | Cambios, en orden |
|---|---|
| **M1** | 1a `infraestructura-base` · 1b `arranque-del-sistema` · 1c `cola-logs-y-respaldos` · 1d `respaldos-y-restauracion` · 2 `acceso-y-aislamiento` ⓔ · 3 `configuracion-del-edificio` · 4 `motor-de-cuenta-corriente` ⓔ · 5 `importacion-desde-excel` · 6 `gastos-y-cargos` · 7 `liquidacion-y-emision` ⓔ |
| **M2** | 8 `pagos-informados` · 6b `motor-de-reglas` ⓔ · 9 `extracto-bancario` · 10a `morosidad` · 10b `condonacion-judicial-y-libre-deuda` · 11 `portal-del-vecino` · 12 `vista-del-consejo` · 13 `avisos-por-email` |
| **M3** | 14 `lectura-de-facturas` · 15 `piloto-en-paralelo` |

ⓔ = lleva su propio explore antes del propose. En paralelo al cambio 1: conseguir los datos del edificio piloto (P1).

### Observaciones del análisis que cierra cada hito

El análisis de coherencia de la especificación (`../especificacion/analisis/Analisis_de_coherencia.md`)
marcó 48 observaciones. Así se reparten:

| Hito | Observaciones | Cómo |
|---|---|---|
| **M1** | H01, H02, H03, H04, H05, H06, H09, H10, H11, H12, H13, H14, H15, H16, H20, H43, H44, H45 | Migraciones ordenadas, aislamiento con RLS, cuenta corriente de movimientos con imputaciones, intereses simples registrados al emitir, montos en Decimal, login y permisos reales, secretos fuera del repo, importación validada y atómica |
| **M2** | H07, H08, H28, H41, H42 | Excedentes como crédito, extracto en lugar de rendiciones de recaudadores, avisos con destinatarios reales y sin duplicados, morosidad calculada desde imputaciones |
| **M3** | H21, H22, H46, H48 | Lectura por QR y borrador obligatorio, duplicados frenados, restauración de backup probada, piloto como evidencia antes de hablar de producción |
| **Fuera del MVP** | H17, H18, H19, H23 a H27, H29 a H40, H47 | Módulos que no entran (reservas, accesos, comunicación, cálculo de sueldos, asambleas, compras, activos) o el modelo comercial (P8, sin definir) |

## Cómo se valida

1. **Tests unitarios** de cada regla vigente: sus tests mínimos, escritos antes que el código. Las
   propuestas suman los suyos cuando se validan.
2. **Tests de integración** contra PostgreSQL real, incluidos dos pagos simultáneos de la misma unidad.
3. **Test de aceptación de M1**: la última liquidación del edificio piloto, reproducida al centavo.
4. **Mes en paralelo (M3)**: el cierre de PropTech coincide con el método actual del piloto.
5. **Métricas de soporte, después del MVP**: el principio 8 de Alberto ("cada problema se mide")
   queda sin mecanismo en el MVP. No hay entidad de excepción ni métricas todavía; cuando se
   construyan (ver `16_proyecto_final.md`, fase F6), son las que deciden si conviene pasar a la Etapa 2
   de identificación de pagos (CVU por unidad) de DEC-10.

## Diferencias con la especificación original

La especificación de Alberto (`../especificacion/`) es la base. Esto es lo que el MVP cambia o
posterga, para validarlo con él:

| Tema | Especificación | MVP | Por qué |
|---|---|---|---|
| Por dónde empezar | Barrios privados primero | Edificios primero | Pedido de Alberto: el contacto con edificios es más directo (D-027) |
| Medios de cobro | Recaudadores (Red Link, SIRO), Mercado Pago, MODO, CVU por unidad, rendiciones bancarias | Comprobante del vecino + confirmación del administrador | Valida el producto sin la consulta legal UIF ni integraciones (D-017). Posterga la comisión por procesamiento como ingreso |
| Sueldo del encargado | Liquidación completa con escala SUTERH | Se carga como gasto desde el recibo del contador | Es un módulo con riesgo laboral alto; el contador ya lo liquida hoy (D-028) |
| Historial de activos | Requerimiento explícito, parte de la visión | v1.1, apenas validado el MVP | Primero la plata tiene que funcionar (D-003) |
| Intereses | 3% mensual con capitalización diaria | Interés simple, configurable por edificio | Art. 770 del CCyC (D-010) |
| Coeficientes | Tres fijos por unidad | Grupos de reparto definidos por edificio | Cubre más casos con el mismo trabajo (D-013) |
| Lectura de facturas | Todo con IA | Primero el QR de ARCA, IA para el resto | Monto exacto y más barato (D-019) |
| Fondos y tesorería | Fondo operativo, de reserva y de obras con su saldo | Fondo de reserva sólo como concepto de la expensa, sin saldo de caja | Lo que el vecino paga se refleja; el saldo acumulado no hace falta para liquidar (D-031) |
| Roles | Inquilino, contador, proveedor, encargado, guardia | Titular, colaborador, consejo y vecino | Lo mínimo para validar (D-009, D-032, D-037) |
| Consumo de agua | Por rangos de litros | Cargo particular importado por Excel | Cubre el caso sin construir medidores (D-026) |
| Código | 48 fragmentos | Descartado | Errores verificados (D-002) |

Y respecto del documento de arquitectura de Alberto (`../especificacion/arquitectura-alberto/`), que
el MVP sigue en su forma (D-035 a D-039):

| Tema | Documento de Alberto | MVP | Por qué |
|---|---|---|---|
| Permisos | ~15 áreas con 3 niveles | Titular, colaborador, consejo y vecino, con las mismas tres capas | Lo mínimo para validar (D-037) |
| Montos | Decimal (NUMERIC 14,2) | Decimal (NUMERIC 14,2), igual que su documento | Alineado con Alberto (D-046) |
| Cifrado con índice ciego, outbox, copiloto, bandeja de WhatsApp | Incluidos | Después del MVP | Alcance (D-039) |
| Login | Clerk para el personal, enlace mágico para vecinos | Se define en el design del cambio 2 | No se decidió todavía (D-039) |

## Métricas de éxito

El criterio de éxito del MVP es el test de aceptación de M1 y M3 (arriba): reproducir al centavo la
última liquidación del edificio piloto y correr un mes completo en paralelo con el método actual del
administrador. No hay todavía métricas de producto (adopción, retención, soporte): el principio 8 de
Alberto ("cada problema se mide") se construye recién en la fase F6 de `16_proyecto_final.md`.
