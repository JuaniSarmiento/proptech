# Exploración: roles de la empresa y login con Clerk (20/10/2026)

Conversación entre Juani y el orquestador, a partir de una imagen de Alberto con los roles que quiere
(super admin por empresa; admin principal y por edificio; contador principal y por edificio, lectura;
auxiliar por edificio, lectura; vecinos propietarios e inquilinos; una empresa que administra edificios y
barrios, algunos con partes adentro). Reabre D-096 (matriz de roles) y D-097 (método de login).

## Decidido por Juani (20/10/2026)

1. **Login con Clerk, sólo para la autenticación.** Clerk dice quién es la persona (contraseña, link
   mágico, recuperación, más adelante dos pasos). **La autorización sigue en nuestra base**: empresa,
   edificios, perfiles, alcances, RLS. El candado del 2a no se toca en su forma. Reemplaza el método de
   D-097 (que descartaba Clerk cuando sólo el personal tenía contraseña).
2. **Los vecinos también tienen usuario y contraseña** (además del link mágico, que Clerk da igual).
3. **Modelo de roles = perfil × alcance.** "Principal" y "por edificio" son alcances del mismo perfil,
   no roles distintos. Alcance "principal" = toda la empresa (hoy `complejo_id IS NULL`, sólo el titular).

   | Perfil | Alcance | Qué puede |
   |---|---|---|
   | Super admin | toda la empresa | todo, incluidos edificios, usuarios y roles |
   | Administrador | principal o por edificio | operar: padrón, gastos, preparar y **emitir** la liquidación, confirmar pagos, configuración |
   | Contador | principal o por edificio | sólo lectura de lo contable (luego exportar) |
   | Auxiliar | por edificio | sólo lectura del edificio |
   | Consejo | su edificio | **sólo lectura** de gastos, liquidaciones y comprobantes (se mantiene; control que da la ley) |
   | Vecino propietario | su unidad | todas sus expensas (ordinarias y extraordinarias), informar pagos |
   | Vecino inquilino | su unidad | sólo lo que paga el inquilino (ordinarias), informar pagos |

4. **Emitir y corregir**: emite la liquidación el super admin y todo administrador con alcance sobre ese
   edificio. **Anular la liquidación, revertir o reimputar pagos, condonar intereses, dar de baja deuda y
   aceptar alertas bloqueantes: sólo super admin y administrador principal.**
5. **Propietario/inquilino es un atributo de la relación persona-unidad, no de la persona**: una persona
   puede tener varias unidades (mismo edificio, distintos edificios, distintas empresas vía D-099), ser
   propietaria de una e inquilina de otra; propietario e inquilino del mismo depto ven cada uno lo suyo.

## Mapeo a lo que existe (2a, 3a)

Titular → super admin. Colaborador "editar" → administrador (ahora también con alcance principal).
Colaborador "ver" → auxiliar. Consejo se mantiene. Nuevos: contador y la división del vecino. Cambio de
modelo: migración de perfiles y de alcance principal, matriz rehecha, políticas RLS revisadas. Zona
CRITICAL (el candado): va en un **change propio, antes del login**, probado entero sin login como el 2a.
Después el 2b con Clerk sólo conecta la identidad de Clerk con estas asignaciones.

## Cerrado por Juani (20/10/2026, segunda ronda)

6. **Varios propietarios del mismo depto**: cada uno con su cuenta, todos ven la cuenta completa de la
   unidad y cualquiera puede informar un pago.
7. **El inquilino ve sólo las expensas ordinarias** (las extraordinarias son del propietario, la regla
   habitual del contrato de locación en Argentina).
8. **Un barrio con torres o sectores es un solo consorcio**, y los sectores son grupos de reparto (ya
   existen): sin cambio de modelo. Descartado: varios consorcios agrupados con una entidad nueva.
9. **Clerk se adopta con aviso de privacidad**: se declara en la política de privacidad (ley 25.326,
   transferencia internacional), Clerk guarda sólo lo mínimo (email y nombre), la identidad se vincula a
   `persona` por el id de Clerk (nunca por el email solo), y el costo real se verifica en la página de
   Clerk antes del piloto (change 15). Cierra P12 para la autenticación.

Con la segunda ronda no queda nada abierto de esta exploración. Siguiente paso: el propose del change de
roles de la empresa (CRITICAL, antes del login) y después el del 2b con Clerk. Con el login, el change
`acceso-de-desarrollo` se reduce a la carga del edificio de ejemplo.
