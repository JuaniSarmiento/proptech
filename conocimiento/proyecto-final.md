# PropTech: el proyecto completo

> La visión a la que apunta PropTech después de validar el MVP. El orden de las fases es una
> propuesta: se confirma con lo que enseñe el piloto. **Se reescribe** cuando cambia el plan.

## Visión

La plataforma que reúne la plata, los documentos y la operación diaria de un edificio o un barrio
privado: el administrador deja el Excel y el WhatsApp, y el vecino entiende en qué se gasta su
expensa. Arranca en Mendoza y por los edificios (D-027); los barrios privados se suman cuando el
núcleo esté probado.

La especificación original describe 19 módulos (`../especificacion/funcionalidades/`). El MVP
(`mvp.md`) cubre el núcleo financiero; el resto se ordena en las fases de abajo.

## Regla general para pasar de fase

Ninguna fase arranca si la anterior dejó una regla de negocio sin tests, un piloto con diferencias
de cierre sin explicar, o un incidente con plata de un complejo sin resolver. **El núcleo financiero
correcto vale más que cualquier funcionalidad nueva.**

## Fases

| Fase | Contenido | Módulos de la spec | Criterio de entrada |
|---|---|---|---|
| **MVP** | Edificios: liquidación, cuenta corriente, pagos por comprobante, portal, consejo, avisos | 01 a 05, 08, 15 y 17 parciales | Decisiones cerradas (este archivo y `decisiones.md`) |
| **v1.1 · Pago integrado** | Mercado Pago por consorcio: link o QR que llega directo a su cuenta y se imputa solo | 04 | MVP validado en el piloto **y** consulta legal UIF resuelta (D-005, D-017) |
| **v1.1 · Mantenimiento** | Ficha de cada equipo, intervenciones vinculadas a la factura, aviso de reincidencia y de garantía | 13 | MVP validado; facturas ya cargadas por QR (R12) para vincularlas |
| **v1.2 · Barrios privados** | Activar estados de unidad (baldío, en obra), cargos por estado, grupos típicos de barrio y un barrio piloto | 02, 03 | MVP validado en edificios; el modelo ya lo soporta (D-027) |
| **F2 · Comunicación** | Bandeja unificada, reclamos con número, bot de WhatsApp con intervención humana, consultas del reglamento con IA citando la página, API oficial de WhatsApp Business con resguardo por email si el canal falla (ProTecc W1, W2) y respuesta automática que deriva al enlace de carga cuando el vecino contesta por el chat (ProTecc W5) | 09, 10 | Al menos 3 edificios en producción; verificación del negocio ante Meta para WhatsApp |
| **F3 · Comunidad** | Reservas del SUM y espacios comunes con reglas por complejo; asambleas con quórum y votación | 06, 14 | Pedido explícito de los edificios en producción; revisión legal de mayorías (art. 2060) antes de asambleas |
| **F4 · Operación** | Proveedores y órdenes de compra con cotejo de presupuesto, ejecución y factura; cálculo del sueldo del encargado con escala SUTERH | 11, 12 | Base estable con varios barrios; revisión de un laboralista antes de sueldos |
| **F5 · Acceso** | Invitaciones con QR y bitácora de guardia, o integración con un sistema de acceso existente | 07 | Decidir antes si se integra con AccessIN u otro proveedor ya instalado en lugar de competir con su hardware |
| **F6 · Escala** | Inquilino como rol, tesorería y saldo del fondo de reserva, fondos (reserva, obra) como subcuentas independientes (ProTecc C3, C7), consumos de agua por medidor, otros medios de cobro (MODO, débito, Red Link, Rapipago, SIRO), pago en efectivo con recibo numerado (ProTecc D5), plan de pago o convenio de deuda con sus cuotas como cargo mensual (ProTecc G1), conciliación completa de caja y banco con estado de caja por liquidación (ProTecc H3), centavos identificadores por unidad en el monto de la boleta si los extractos reales lo justifican (D-062), excepción como entidad propia con métricas de tiempo de resolución y cola de sugerencias con dos señales independientes (principios 3 y 8 de Alberto, DEC-12), tableros y reportes, exportaciones normativas, otras provincias | 02, 04, 15, 16 | Núcleo probado con edificios y barrios; reglas por jurisdicción relevadas para cada provincia nueva |

## Lo que la especificación proponía y queda descartado

- **Capitalización diaria de intereses**: choca con el art. 770 del Código Civil y Comercial (D-010).
- **Microservicios o "motores" separados**: un monolito modular alcanza para cientos de edificios (D-021).
- **Recaudar en una cuenta propia**: la plata va siempre directo a la cuenta del consorcio (D-005).
- **El código original**: descartado; sólo se conservó como antecedente (D-002).
- **El régimen informativo RG 3645**: fue abrogado por la RG 5698/2025 (análisis H33).

## Pendiente

- [ ] Modelo comercial por fase: qué se cobra aparte y qué entra en el abono (P8, sin definir).
- [ ] Confirmar el orden de F2 a F6 con lo que pida el piloto.
