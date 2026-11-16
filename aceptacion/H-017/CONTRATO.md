# Contrato que asume la aceptación de H-017

Siguen vigentes los contratos de H-011 a H-016. Si el constructor necesita cambiar algo, frena y lo pide.

## Backend

- `GET /api/complejos/{id}/liquidaciones/{liquidacion_id}`: cada elemento de `unidades` suma
  `"obligacion_id"`: el id de su obligación en el libro, o `null` si la unidad no tuvo obligación.
- `GET /api/documentos/descarga?token=...` responde con
  `Content-Disposition: attachment; filename="expensa-<AAAA-MM>-<identificador>-<variante>.pdf"`, con el
  identificador en minúscula y cualquier carácter fuera de `[a-z0-9]` cambiado por `-`
  (`expensa-2026-11-1b-completa.pdf`, `expensa-2026-11-1b-sin-extraordinaria.pdf`). Nunca el nombre de una
  persona. La ruta de Next que reenvía la descarga conserva esa cabecera.

## La pantalla

- **Menú del edificio**: el link "Liquidaciones" (`/edificios/{id}/liquidaciones`) aparece sólo si las acciones
  permitidas del edificio incluyen `ver_liquidaciones`.
- **`/edificios/{id}/liquidaciones`**: título "Liquidaciones"; una lista (`role=list`) con un `listitem` por
  liquidación de `GET .../liquidaciones` (la más nueva primero) con el período en palabras ("noviembre de
  2026"), el estado en texto ("Emitida", "Distribuida", "Anulada") y el total; las que no están anuladas
  tienen un link al período (`/edificios/{id}/liquidaciones/AAAA-MM`). Un link "Preparar la liquidación de
  <mes> de <año>" al mes siguiente al último período con una liquidación no anulada, o al mes actual (en
  Mendoza) si no hay ninguna.
- **Liquidación emitida** (`/edificios/{id}/liquidaciones/AAAA-MM` con el período emitido): además de lo de
  H-014 y H-015, una tabla (`role=table`) "Lo que paga cada unidad" con lo guardado: unidad, ordinaria, fondo
  de reserva, extraordinaria, cargos particulares, intereses, saldo anterior y total, con punto de miles.
  Cada unidad con `obligacion_id` y con la acción `corregir_movimiento` permitida tiene un botón
  "Cargo cobrado de menos de <identificador>" que abre un diálogo con "Importe", "Concepto" (Ordinaria, Fondo
  de reserva, Extraordinaria) y "Motivo"; "Confirmar" manda `POST
  /api/complejos/{id}/unidades/{unidad_id}/cargos-cobrados-de-menos` con `operacion_id` nuevo,
  `obligacion_origen_id` (el `obligacion_id` de la unidad), `importe` como texto con punto decimal
  (`"1500.00"`), `componente` y `motivo`.

### API falsa

| Edificio | Qué tiene |
|---|---|
| `00000000-0000-0000-0000-000000001401` | (H-014) la emitida de noviembre; ahora con `unidades` (los importes de la base de H-011, saldo anterior `0.00`, `1A` con `obligacion_id` `00000000-0000-0000-0000-000000140101` y `unidad_id` `00000000-0000-0000-0000-000000140111`) y todas las acciones |
| `00000000-0000-0000-0000-000000001701` | `GET .../liquidaciones`: noviembre de 2026 distribuida (`191500.00`) y octubre de 2026 anulada (`180000.00`); todas las acciones |
| `00000000-0000-0000-0000-000000001702` | como 1401 pero sin `ver_liquidaciones` ni `corregir_movimiento` entre las acciones del edificio |
| `00000000-0000-0000-0000-000000001703` | como 1401 con `ver_liquidaciones` y sin `corregir_movimiento` |
