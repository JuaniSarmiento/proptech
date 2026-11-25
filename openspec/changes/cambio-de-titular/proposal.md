# Proposal

> Acuerdo previo: D-168 (25/11/2026). Juani delegó por escrito en la sesión la firma de los changes CRITICAL y
> HIGH y la decisión de las preguntas que los traben; el orquestador resolvió P51 (entero) y P52 (la deuda a
> nombre del vendedor no genera interés nuevo, no entra a la morosidad y la cobra el administrador).

## Why

R32 está vigente desde D-109, pero el sistema no sabe que una unidad cambió de dueño: el padrón sólo borra y
agrega propietarios, sin fecha ni registro, y la deuda previa y la expensa del mes de la venta no tienen
dónde ir. El 4b dejó la `cuenta` polimórfica y el tipo `traslado` sembrado para esto.

## Gobernanza

**CRITICAL**: escribe en la cuenta corriente (traslados de deuda a la cuenta de persona del vendedor y
prorrateo de la expensa del mes) y cambia quién es propietario de una unidad.

## What Changes

- **H-030** registrar el cambio de titular con las opciones por defecto: tabla de sólo agregar
  `cambio_de_titular` (migración `0050`), acción `registrar_cambio_de_titular`, `POST` y `GET`
  `/api/complejos/{id}/unidades/{id}/cambios-de-titular`, reemplazo de propietarios y aviso de deuda sin bloqueo.
- **H-031** deuda previa a nombre del vendedor (traslado enlazado a su cuenta de persona, sin interés nuevo).
- **H-032** prorrateo por días de la expensa del mes del cambio, al registrar o al emitir el período.
- **H-033** la cuenta del vendedor: estado y cobro registrado por el administrador.
- **H-034** pantallas del cambio de titular y de la cuenta del vendedor (impeccable).

## Qué queda fuera

Que la deuda del vendedor devengue interés; que el vendedor aparezca en la morosidad; que el vendedor entre al
portal; el libre deuda (10b). SU-02 sigue sin verificar con abogado.

## Impact

Módulo nuevo `titularidad`; `acceso` (permiso, propietarios), `cuenta_corriente` (traslado, desde H-031),
`liquidacion` (emisión con prorrateo pendiente, H-032), `web/` (H-034). Detalle por historia en `HISTORIAS.md`.

## Knowledge Base Impact

`03_actores_y_roles.md`, `04_modelo_de_datos.md`, `05_reglas_de_negocio.md` (R32), `09` (D-168),
`10` (P51, P52), `12_fichas_de_changes.md` (4d), `15_lecciones.md` al cerrar.

## Aprobación

Firmado por el orquestador por delegación escrita de Juani, 25/11/2026 (D-168). **Desvío del método**: esta
propuesta se escribió después de construir H-030; la firma (D-168, `2fd631b`) y la aceptación congelada
(`abbc1e2`) sí fueron anteriores al código.
