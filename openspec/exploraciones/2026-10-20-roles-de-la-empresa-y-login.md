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

## Abierto

- **Varios propietarios del mismo depto** (matrimonio, herederos): ¿todos ven todo y cualquiera informa
  el pago? (propuesta: sí).
- **Qué ve exactamente el inquilino**: la regla "ordinarias para el inquilino, extraordinarias para el
  propietario" es la habitual en Argentina por contrato de locación; confirmar si hay casos distintos.
- **El barrio con partes adentro** (Barrio 1, las flechas de edi2): ¿un consorcio con sectores (grupos
  de reparto, ya existen) o varios consorcios agrupados? Cambia el modelo de datos. **Lo decide Alberto.**
- **Clerk**: costo por usuario activo mensual con muchos vecinos; los mails de los vecinos en un tercero
  (P12, aprobación de Alberto); mapeo de la identidad de Clerk a `persona` (por id de Clerk, nunca por
  email solo); qué pasa con el link mágico del vecino y el change 13.
- Con el login, el change `acceso-de-desarrollo` queda reducido a la carga del edificio de ejemplo.
