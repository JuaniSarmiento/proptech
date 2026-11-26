# Contrato que asume la aceptación de H-042

Condonación de interés y marca de gestión judicial (change 10b `condonacion-judicial-y-libre-deuda`). Caja negra por la
API real, con la identidad inyectada. Fuente: `HISTORIAS.md` (H-042), R29, R31, R20, D-171 y D-172. Si el constructor
necesita cambiar algo de esto, frena y lo pide. Los nombres, rutas y claves de abajo los fija esta aceptación; las claves
de cada objeto son **exactamente** las listadas (los tests comparan el conjunto).

## El día de hoy

`proptech_api.condonaciones.hoy` y `proptech_api.gestion_judicial.hoy` son dependencias de FastAPI sin parámetros que
devuelven la fecha de hoy en Mendoza (`date`); la aceptación las reemplaza por el 18/11/2026 con
`app.dependency_overrides` (L-090), igual que `morosidad.hoy`, `libre_deuda.hoy` y `vecino.hoy`. `fecha_valor` de una
condonación y `fecha` de una marca son ese día.

## Quién puede, en qué orden

Acciones (`Accion` y `_MATRIZ`; cada una es a la vez permiso y vocabulario de auditoría, D-096; una migración suma las
tres nuevas a `accion_de_auditoria`, que sube y baja como la `0056`):

| Acción | Quién | Ruta |
|---|---|---|
| `condonar_intereses` (ya existe) | super admin y administrador principal (D-171.2) | `POST .../condonaciones` |
| `marcar_gestion_judicial` (nueva) | super admin y administrador principal | `POST .../gestion-judicial` |
| `desmarcar_gestion_judicial` (nueva) | super admin y administrador principal | `DELETE .../gestion-judicial` |
| `ver_condonaciones` (nueva) | super admin, administrador principal y por edificio, contador principal y por edificio, consejo; **no** el auxiliar ni el vecino | `GET /api/complejos/{c}/condonaciones` |

Orden de chequeo de las tres escrituras (D7, L-100): edificio inexistente, de otra administración o fuera del alcance de
la persona, **404** `{"detail": "no encontrado"}` (un administrador de otro edificio: 404; el alcance va antes que el
permiso); sin el permiso, **403** con `detail` `{"codigo": "sin_permiso", "detalle": "sin_permiso", "permiso_faltante":
"<la acción de la tabla>"}`; la unidad que no existe o es de otro edificio o administración, **404** con el mismo cuerpo
exacto; el cuerpo, **422**; (sólo la condonación) la obligación que no existe o no es de esa unidad, **404** con el
mismo cuerpo; el estado o el importe contra lo pendiente (422 en la condonación, 409 en la marca). Un pedido rechazado
no escribe en el libro ni audita nada. Leer no se audita.

## `POST /api/complejos/{c}/unidades/{u}/condonaciones`

Cuerpo `{"obligacion_id": "<uuid>", "importe": "100.00", "motivo": "..."}`, sólo esas tres claves (un campo de más,
como `componente` o `unidad_id`, da 422: sólo se condona interés y la unidad sale de la ruta). `importe` es **texto**
con a lo sumo dos decimales y mayor que cero (número, `"0.00"`, negativo, `"abc"` o tres decimales: 422); `motivo`
obligatorio, de 1 a 500 caracteres sin contar los extremos en blanco (ausente, nulo, vacío, en blanco, largo o que no es
texto: 422). `obligacion_id` es un UUID (si no lo es, 422).

Qué se condona: el **interés pendiente** de esa obligación (los intereses registrados con `tipo` `interes` menos lo que
ya está imputado a su componente `interes`, sea de pagos o de otras condonaciones). **422** si el importe es mayor que lo
pendiente (parcial o total, una condonación puede ser de cualquier monto hasta lo pendiente, y varias seguidas suman),
si la obligación no tiene interés pendiente (sólo capital, o sin interés registrado) o si ese interés ya está cobrado.
Lo cobrado de más sigue por el ajuste de interés (H-021, D-172.7).

**201** con `{"id", "unidad_id", "obligacion_id", "periodo", "importe", "motivo", "fecha_valor"}`: `id` es el del
movimiento; `periodo` es `AAAA-MM-01` de la obligación; `importe` texto con dos decimales; `fecha_valor` es hoy.

Lo que escribe (R29, una transacción con el candado de la cuenta): **un movimiento** `condonacion`, `sentido`
`credito`, `componente` `interes`, `obligacion_id` la elegida, `fecha_valor` hoy, `motivo` el pedido y `registrado_por` la
persona en sesión (`registrar_credito` con tipo `condonacion` y destino `(obligacion, interes)`, D-086), con su
imputación sólo a ese componente. **El recargo original no se borra ni se cambia**: los movimientos `interes` quedan
iguales. El saldo baja exactamente el importe. El motivo vive en `movimiento.motivo`: no hay tabla nueva para la
condonación.

Auditoría: una fila por condonación, `accion` `condonar_intereses`, `entidad` `movimiento`, `entidad_id` el movimiento,
`persona_id` quien condonó y `detalle` exactamente `{"unidad_id": "<uuid>", "obligacion_id": "<uuid>", "importe":
"200.00", "motivo": "..."}`.

## Dónde ve el vecino y el consejo el motivo (C02)

- **Vecino**: `GET /api/mis-unidades/{unidad_id}/condonaciones` (en `vecino.py`: la unidad tiene que ser una de sus
  asignaciones `vecino`; ajena, de otro edificio, inexistente o siendo sólo personal, **404** `no encontrado`). **200**
  con la lista de las condonaciones de esa unidad, la más nueva primero (por `registrado_en`, y ante empate por `id`
  descendente), cada una `{"id", "periodo", "importe", "motivo", "fecha_valor"}`. Lista vacía si no hay. Sólo lee.
- **Consejo y equipo**: `GET /api/complejos/{c}/condonaciones` con `ver_condonaciones`. **200** con la lista de las
  condonaciones del edificio, la más nueva primero, cada una `{"id", "unidad_id", "unidad", "obligacion_id", "periodo",
  "importe", "motivo", "fecha_valor"}` (`unidad` es el identificador, por ejemplo `1A`).

## R20 después de condonar (C03)

No hay nada que reevaluar: `situacion_de_cuenta`, `situacion_del_edificio` y la morosidad del 10a se derivan del libro
cada vez. Condonar baja el residual de interés, así que `interes_vencido` y `total_vencido` bajan lo condonado y la
etiqueta sale de la precedencia de siempre: sin interés ni capital vencido, `sin_deuda_vencida`; un total vencido de
sólo interés por debajo de 500,00, `bajo_umbral`; con capital impago en dos o más liquidaciones, la unidad sigue siendo
`moroso_critico` (condonar interés no paga capital).

## `POST` y `DELETE /api/complejos/{c}/unidades/{u}/gestion-judicial`

Cuerpo `{"motivo": "..."}` en los dos (el `DELETE` lleva cuerpo JSON), sólo esa clave, con las reglas del motivo de
arriba (422 por cualquier otra cosa, **antes** que el 409). **POST 201** marca; **DELETE 200** desmarca. Los dos
responden `{"id", "unidad_id", "en_gestion_judicial", "motivo", "fecha"}`: `id` es el de la fila del historial recién
agregada, `en_gestion_judicial` es `true` al marcar y `false` al desmarcar, `fecha` es hoy (`AAAA-MM-DD`).
**409** si ya está marcada (el `POST`) o si no lo está (el `DELETE`), sin cambios y sin auditoría.

### La tabla: `gestion_judicial_de_unidad`

De sólo agregar (D-016): `proptech_app` lee e inserta; `UPDATE` y `DELETE` fallan. Con RLS por administración,
registrada como tabla protegida (`compartido/tablas_protegidas.py`, con su sonda) y con migración que sube y baja como la
`0056`. Una fila por evento: `id`, `administracion_id`, `complejo_id`, `unidad_id`, `accion` (`marcar` o `desmarcar`),
`motivo`, `fecha` (`date`, la de hoy), `registrado_por` (la persona en sesión) y `registrado_en`, con FK compuestas a la
unidad de su edificio y a la persona. **El estado vigente de una unidad es su último evento**: marcada si es `marcar`;
desmarcada si es `desmarcar` o no tiene ninguno. Marcar, desmarcar y marcar de nuevo deja tres filas. Es historial, no una
bandera: nada se pisa.

Auditoría: una fila por evento. `marcar_gestion_judicial` (POST) o `desmarcar_gestion_judicial` (DELETE), `entidad`
`gestion_judicial_de_unidad`, `entidad_id` el `id` del evento, `persona_id` quien lo hizo y `detalle` exactamente
`{"unidad_id": "<uuid>", "motivo": "..."}`.

La marca **nunca** cambia el saldo ni escribe en el libro (`movimiento`, `imputacion`, `obligacion`, `cuenta` quedan
iguales), ni frena el interés: el interés corrido y el saldo de una unidad marcada son los de siempre (N03).

## La marca en R20 y en la morosidad (C06, C08)

Una unidad con la marca vigente **no cuenta como moroso crítico** (R31, R20, D-078): en `situacion_de_cuenta`,
`situacion_del_edificio` y la morosidad del 10a, su `etiqueta` pasa de `moroso_critico` a `con_deuda_vencida`, y
`moroso_critico` es `false`, aunque tenga dos o más liquidaciones vencidas. `total_vencido`, `capital_vencido`,
`interes_vencido` y `liquidaciones_vencidas` no cambian. Las demás etiquetas (`sin_deuda_vencida`, `bajo_umbral`,
`deuda_de_intereses`) no cambian por la marca. Desmarcada, vuelve a clasificarse como cualquier unidad.

`GET /api/complejos/{c}/morosidad`: sigue mostrando la unidad (debe plata) pero ya no suma en `resumen.morosos_criticos`
y se ordena entre las que no son críticas. **Su fila gana una clave nueva, `en_gestion_judicial: true`, sólo si la unidad
está marcada**: las filas de las demás conservan exactamente las diez claves de H-027 (la regresión de H-027 las
compara y no se toca).

## La consulta para el 13 (C07)

`proptech_core.cuenta_corriente.aplicacion.gestion_judicial.unidades_en_gestion_judicial(sesion, *, complejo_id: UUID)
-> frozenset[UUID]`: los `unidad_id` del edificio con la marca vigente, sin importar si deben plata. Sobre la sesión del
tenant (RLS): un edificio de otra administración da `frozenset()`. Los avisos automáticos de mora (R31, HU-V6) los
construye el cambio 13 consultando esta función para saltear esas unidades; esta aceptación no prueba un aviso porque
el módulo no existe todavía (es el único test mínimo de R31 que queda para el 13, anotado en su ficha).

## El certificado de H-041 (C08)

Con la unidad marcada **al emitir**, el certificado trae `en_gestion_judicial: true` y el PDF lleva la leyenda "en
gestión judicial"; sin la marca, `false` y sin leyenda. Es parte de la foto: un certificado emitido antes de marcar queda
en `false` y con el mismo PDF byte a byte; uno emitido tras desmarcar, en `false`. La marca no cambia `saldo`, `capital`,
`intereses` ni `interes_corrido` (N03). Los tests de H-041 no se tocan.

## Los datos de la aceptación

Los de H-041 (Torre Ficticia, `1A` a `2B`, 3% mensual proporcional, gracia 0, umbral 500,00, vencimiento el día 10),
septiembre, octubre y noviembre emitidos con `registrar_emision`, hoy el 18/11/2026. Sin pagos informados.

- `1A` no paga: interés registrado 510,00 sobre septiembre y 210,00 sobre octubre (720,00); capital vencido 20.000,00
  al 05/11 y 30.000,00 al 18/11; saldo 30.720,00; interés corrido al 18/11 de 440,00; moroso crítico (2 liquidaciones
  vencidas al 05/11, 3 al 18/11).
- `1B` paga a término, o con `b_tarde` el 25/09 (40.000,00) y el 25/10 (40.600,00): al 05/11 sólo debe 600,00 de interés
  sobre octubre (`deuda_de_intereses`).
- `2A` y `2B` no pagan: morosos críticos (saldos al 18/11 de 15.360,00 y 24.576,00). `1A` y `2B` son de Ana Prueba.
- En el 18/11 la morosidad ordena `1A` (30.720,00), `2B`, `2A` (los tres críticos) y `1B` (40.000,00, con deuda vencida).
