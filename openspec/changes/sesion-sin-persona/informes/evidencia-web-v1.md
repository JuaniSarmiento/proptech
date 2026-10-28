# Mutantes web · vuelta 1

EVIDENCIA (constructor). Copias previas sin commit en `.atl/2d-v1/backup-<id>.tsx`, restauradas por finally. Mutantes focales usan el mismo Vitest y configuración que `test-web.sh`; RED/GREEN principales usan el wrapper completo.

## 3.1-a

```diff
--- web/src/lib/api/cliente.ts
+++ web/src/lib/api/cliente.ts
@@ -137,7 +137,7 @@
     const leido = await leerJson(respuesta);
     const cuerpo = leido.parseo === "ok" ? comoRegistro(leido.valor) : {};
     const detalle = comoRegistro(cuerpo.detail);
-    if (detalle.codigo === "sin_acceso") redirect("/sin-acceso");
+    if (true) redirect("/sin-acceso");
     const permiso =
       detalle.codigo === "sin_permiso"
         ? textoSeguro(detalle.permiso_faltante, "desconocido")
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/lib/api/cliente.test.ts
2026-10-28T11:24:22.758421-03:00
 FAIL  src/lib/api/cliente.test.ts > pedirApi > 403: el marcador de detail/msg nunca llega al resultado (L-007)
 ❯ src/lib/api/cliente.test.ts:226:25
 FAIL  src/lib/api/cliente.test.ts > 2d · discriminador y selector sin rebote > código desconocido undefined ignora permiso_faltante
 FAIL  src/lib/api/cliente.test.ts > 2d · discriminador y selector sin rebote > código desconocido otro ignora permiso_faltante
AssertionError: expected { estado: 'redirigio' } to deeply equal { estado: 'sin_permiso', …(1) }
 ❯ src/lib/api/cliente.test.ts:283:79
 FAIL  src/lib/api/cliente.test.ts > 2d · discriminador y selector sin rebote > sin cuerpo 403 es permiso desconocido
AssertionError: expected { estado: 'redirigio' } to deeply equal { estado: 'sin_permiso', …(1) }
 ❯ src/lib/api/cliente.test.ts:300:79
      Tests  5 failed | 28 passed (33)
exit=1
```

## 3.1-b

```diff
--- web/src/lib/api/cliente.ts
+++ web/src/lib/api/cliente.ts
@@ -137,7 +137,7 @@
     const leido = await leerJson(respuesta);
     const cuerpo = leido.parseo === "ok" ? comoRegistro(leido.valor) : {};
     const detalle = comoRegistro(cuerpo.detail);
-    if (detalle.codigo === "sin_acceso") redirect("/sin-acceso");
+    if (detalle.permiso_faltante === "sin_acceso") redirect("/sin-acceso");
     const permiso =
       detalle.codigo === "sin_permiso"
         ? textoSeguro(detalle.permiso_faltante, "desconocido")
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/lib/api/cliente.test.ts
2026-10-28T11:24:23.439126-03:00
 ❯ src/lib/api/cliente.test.ts (33 tests | 3 failed) 43ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 3 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/lib/api/cliente.test.ts > 2d · discriminador y selector sin rebote > sin_acceso redirige sin regreso
AssertionError: promise resolved "{ estado: 'sin_permiso', …(1) }" instead of rejecting
 ❯ src/lib/api/cliente.test.ts:274:41
 FAIL  src/lib/api/cliente.test.ts > 2d · discriminador y selector sin rebote > código desconocido undefined ignora permiso_faltante
 FAIL  src/lib/api/cliente.test.ts > 2d · discriminador y selector sin rebote > código desconocido otro ignora permiso_faltante
AssertionError: expected { estado: 'redirigio' } to deeply equal { estado: 'sin_permiso', …(1) }
 ❯ src/lib/api/cliente.test.ts:283:79
      Tests  3 failed | 30 passed (33)
exit=1
```

## 3.1-c

```diff
--- web/src/lib/api/cliente.ts
+++ web/src/lib/api/cliente.ts
@@ -127,7 +127,6 @@
   }
 
   if (respuesta.status === 401) {
-    if (opciones.alNoAutenticar === "devolver") return { estado: "sin_sesion" };
     return irAlIngreso(sesion.regreso);
   }
   if (respuesta.status === 404) {
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/lib/api/cliente.test.ts
2026-10-28T11:24:24.096337-03:00
 ❯ src/lib/api/cliente.test.ts (33 tests | 1 failed) 44ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/lib/api/cliente.test.ts > 2d · discriminador y selector sin rebote > devolver no redirige con 401
AssertionError: expected { estado: 'redirigio' } to deeply equal { estado: 'sin_sesion' }
 ❯ src/lib/api/cliente.test.ts:296:7
      Tests  1 failed | 32 passed (33)
exit=1
```

## 3.1-d

```diff
--- web/src/lib/api/cliente.ts
+++ web/src/lib/api/cliente.ts
@@ -98,7 +98,6 @@
 
   const sesion = await sesionActual();
   if (!sesion) {
-    if (opciones.alNoAutenticar === "devolver") return { estado: "sin_sesion" };
     return irAlIngreso();
   }
   const cabeceras = cabecerasHaciaLaApi(opciones.cabeceras ?? new Headers());
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/lib/api/cliente.test.ts
2026-10-28T11:24:24.738628-03:00
 ❯ src/lib/api/cliente.test.ts (33 tests | 1 failed) 43ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/lib/api/cliente.test.ts > 2d · discriminador y selector sin rebote > devolver no redirige con sin_sesion
AssertionError: expected { estado: 'redirigio' } to deeply equal { estado: 'sin_sesion' }
 ❯ src/lib/api/cliente.test.ts:296:7
      Tests  1 failed | 32 passed (33)
exit=1
```

## 3.2-a

```diff
--- web/src/lib/sesion.ts
+++ web/src/lib/sesion.ts
@@ -36,7 +36,7 @@
   } catch {
     return "/edificios";
   }
-  const pantallasDeAcceso = ["/ingresar", "/registrarse", "/elegir-administracion", "/sin-acceso"];
+  const pantallasDeAcceso = ["/ingresar", "/registrarse", "/sin-acceso"];
   if (pantallasDeAcceso.some((ruta) => camino === ruta || camino.startsWith(`${ruta}/`))) {
     return "/edificios";
   }
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/lib/sesion.test.ts
2026-10-28T11:24:25.409662-03:00
 ❯ src/lib/sesion.test.ts (37 tests | 2 failed) 55ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/lib/sesion.test.ts > 2d rechaza acceso normalizado /elegir-administracion?regreso=%2Fedificios
AssertionError: expected '/elegir-administracion?regreso=%2Fedi…' to be '/edificios' // Object.is equality
 ❯ src/lib/sesion.test.ts:105:78
 FAIL  src/lib/sesion.test.ts > 2d rechaza acceso normalizado /./elegir-administracion
AssertionError: expected '/elegir-administracion' to be '/edificios' // Object.is equality
 ❯ src/lib/sesion.test.ts:105:78
      Tests  2 failed | 35 passed (37)
exit=1
```

## 3.2-b

```diff
--- web/src/lib/sesion.ts
+++ web/src/lib/sesion.ts
@@ -32,7 +32,7 @@
   }
   let camino: string;
   try {
-    camino = decodeURIComponent(url.pathname).replace(/\/+$/, "");
+    camino = valor.replace(/\/+$/, "");
   } catch {
     return "/edificios";
   }
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/lib/sesion.test.ts
2026-10-28T11:24:26.069976-03:00
 FAIL  src/lib/sesion.test.ts > 2d rechaza acceso normalizado /edificios/../ingresar
AssertionError: expected '/ingresar' to be '/edificios' // Object.is equality
 ❯ src/lib/sesion.test.ts:105:78
 FAIL  src/lib/sesion.test.ts > 2d rechaza acceso normalizado /%69ngresar
AssertionError: expected '/%69ngresar' to be '/edificios' // Object.is equality
 ❯ src/lib/sesion.test.ts:105:78
 FAIL  src/lib/sesion.test.ts > 2d rechaza acceso normalizado /%ZZ
AssertionError: expected '/%ZZ' to be '/edificios' // Object.is equality
 ❯ src/lib/sesion.test.ts:105:78
      Tests  6 failed | 31 passed (37)
exit=1
```

## 3.2-c

```diff
--- web/src/lib/sesion.ts
+++ web/src/lib/sesion.ts
@@ -41,7 +41,7 @@
     return "/edificios";
   }
   const salida = `${url.pathname}${url.search}${url.hash}`;
-  return salida.length > 512 ? "/edificios" : salida;
+  return salida;
 }
 
 /**
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/lib/sesion.test.ts
2026-10-28T11:24:26.785254-03:00
 FAIL  src/lib/sesion.test.ts > 2d tope exacto de entrada y salida
AssertionError: expected '/edificios/%C3%B1%C3%B1%C3%B1%C3%B1%C…' to be '/edificios' // Object.is equality
 ❯ src/lib/sesion.test.ts:113:58
 FAIL  src/lib/sesion.test.ts > 2d normalizar es idempotente /edificios/{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{
AssertionError: expected '/edificios' to be '/edificios/%7B%7B%7B%7B%7B%7B%7B%7B%7…' // Object.is equality
 ❯ src/lib/sesion.test.ts:125:46
 FAIL  src/lib/sesion.test.ts > 2d normalizar es idempotente /edificios/{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{
AssertionError: expected '/edificios' to be '/edificios/%7B%7B%7B%7B%7B%7B%7B%7B%7…' // Object.is equality
 ❯ src/lib/sesion.test.ts:125:46
      Tests  3 failed | 34 passed (37)
exit=1
```

## 3.2-d

```diff
--- web/src/lib/sesion.ts
+++ web/src/lib/sesion.ts
@@ -19,7 +19,7 @@
 export function regresoSeguro(valor: string | null | undefined): string {
   if (
     !valor?.startsWith("/") ||
-    valor.length > 512 ||
+    valor.length >= 512 ||
     valor.startsWith("//") ||
     // biome-ignore lint/suspicious/noControlCharactersInRegex: rechazar controles evita URLs normalizadas a otro origen.
     /[\\\u0000-\u0020]/.test(valor)
@@ -41,7 +41,7 @@
     return "/edificios";
   }
   const salida = `${url.pathname}${url.search}${url.hash}`;
-  return salida.length > 512 ? "/edificios" : salida;
+  return salida.length >= 512 ? "/edificios" : salida;
 }
 
 /**
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/lib/sesion.test.ts
2026-10-28T11:24:27.433240-03:00
 ❯ src/lib/sesion.test.ts (37 tests | 1 failed) 37ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/lib/sesion.test.ts > 2d tope exacto de entrada y salida
AssertionError: expected '/edificios' to be '/edificios/aaaaaaaaaaaaaaaaaaaaaaaaaa…' // Object.is equality
 ❯ src/lib/sesion.test.ts:111:33
      Tests  1 failed | 36 passed (37)
exit=1
```

## 3.3-D3

```diff
--- web/src/lib/sesion.ts
+++ web/src/lib/sesion.ts
@@ -17,31 +17,15 @@
 }
 
 export function regresoSeguro(valor: string | null | undefined): string {
-  if (
-    !valor?.startsWith("/") ||
-    valor.length > 512 ||
-    valor.startsWith("//") ||
-    // biome-ignore lint/suspicious/noControlCharactersInRegex: rechazar controles evita URLs normalizadas a otro origen.
-    /[\\\u0000-\u0020]/.test(valor)
-  ) {
+  // biome-ignore lint/suspicious/noControlCharactersInRegex: rechazar controles evita URLs normalizadas a otro origen.
+  if (!valor?.startsWith("/") || valor.startsWith("//") || /[\\\u0000-\u0020]/.test(valor)) {
     return "/edificios";
   }
   const url = new URL(valor, "https://proptech.invalid");
   if (url.origin !== "https://proptech.invalid" || url.pathname.startsWith("//")) {
     return "/edificios";
   }
-  let camino: string;
-  try {
-    camino = decodeURIComponent(url.pathname).replace(/\/+$/, "");
-  } catch {
-    return "/edificios";
-  }
-  const pantallasDeAcceso = ["/ingresar", "/registrarse", "/elegir-administracion", "/sin-acceso"];
-  if (pantallasDeAcceso.some((ruta) => camino === ruta || camino.startsWith(`${ruta}/`))) {
-    return "/edificios";
-  }
-  const salida = `${url.pathname}${url.search}${url.hash}`;
-  return salida.length > 512 ? "/edificios" : salida;
+  return `${url.pathname}${url.search}${url.hash}`;
 }
 
 /**
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/app/ingresar/ciclo.test.tsx
2026-10-28T11:24:28.076940-03:00
 ❯ src/app/ingresar/ciclo.test.tsx (2 tests | 1 failed) 40ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/app/ingresar/ciclo.test.tsx > 50 vueltas del selector que redirige conservan tamaño sin regreso anidado
AssertionError: expected '/elegir-administracion?regreso=%2Fedi…' to be '/edificios' // Object.is equality
 ❯ src/app/ingresar/ciclo.test.tsx:46:83
      Tests  1 failed | 1 passed (2)
exit=1
```

## 3.3-D2

```diff
--- web/src/app/elegir-administracion/page.tsx
+++ web/src/app/elegir-administracion/page.tsx
@@ -12,7 +12,7 @@
   searchParams: Promise<{ regreso?: string; aceptada?: string }>;
 }) {
   const q = await searchParams;
-  const resultado = await pedirApi<DatosDeSesion>("/api/sesion", { alNoAutenticar: "devolver" });
+  const resultado = await pedirApi<DatosDeSesion>("/api/sesion");
   if (resultado.estado === "sin_sesion") return <SesionNoUtilizable />;
   if (resultado.estado !== "ok")
     return <ErrorDePantalla mensaje="No pudimos cargar tus administraciones." />;
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/app/ingresar/ciclo.test.tsx
2026-10-28T11:24:28.918548-03:00
 ❯ src/app/ingresar/ciclo.test.tsx (2 tests | 1 failed) 108ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/app/ingresar/ciclo.test.tsx > con D2 el selector no vuelve al ingreso
AssertionError: expected [ …(50) ] to deeply equal []
 ❯ src/app/ingresar/ciclo.test.tsx:63:25
      Tests  1 failed | 1 passed (2)
exit=1
```

## 3.4-a

```diff
--- web/src/app/elegir-administracion/page.tsx
+++ web/src/app/elegir-administracion/page.tsx
@@ -12,7 +12,7 @@
   searchParams: Promise<{ regreso?: string; aceptada?: string }>;
 }) {
   const q = await searchParams;
-  const resultado = await pedirApi<DatosDeSesion>("/api/sesion", { alNoAutenticar: "devolver" });
+  const resultado = await pedirApi<DatosDeSesion>("/api/sesion");
   if (resultado.estado === "sin_sesion") return <SesionNoUtilizable />;
   if (resultado.estado !== "ok")
     return <ErrorDePantalla mensaje="No pudimos cargar tus administraciones." />;
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/app/elegir-administracion/page.test.tsx
2026-10-28T11:24:29.824817-03:00
 ❯ src/app/elegir-administracion/page.test.tsx (7 tests | 2 failed) 50ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/app/elegir-administracion/page.test.tsx > rechazo 401 se queda con Cerrar sesión
 FAIL  src/app/elegir-administracion/page.test.tsx > rechazo sin_sesion se queda con Cerrar sesión
AssertionError: expected '' to contain 'No pudimos validar tu sesión'
 ❯ src/app/elegir-administracion/page.test.tsx:26:16
      Tests  2 failed | 5 passed (7)
exit=1
```

## 3.4-b

```diff
--- web/src/app/elegir-administracion/acciones.ts
+++ web/src/app/elegir-administracion/acciones.ts
@@ -9,7 +9,7 @@
   if (!esIdValido(id)) return false;
   const resultado = await pedirApi<{ administraciones: { id: string; nombre: string }[] }>(
     "/api/sesion",
-    { alNoAutenticar: "devolver" },
+    {},
   );
   if (resultado.estado !== "ok" || !resultado.datos.administraciones.some((a) => a.id === id)) {
     return false;
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/app/elegir-administracion/page.test.tsx
2026-10-28T11:24:30.713322-03:00
 ❯ src/app/elegir-administracion/page.test.tsx (7 tests | 1 failed) 48ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/app/elegir-administracion/page.test.tsx > la acción con 401 no redirige
AssertionError: expected 'redirigió' to be false // Object.is equality
 ❯ src/app/elegir-administracion/page.test.tsx:59:21
      Tests  1 failed | 6 passed (7)
exit=1
```

## 3.5-a

```diff
--- web/src/app/sin-acceso/page.tsx
+++ web/src/app/sin-acceso/page.tsx
@@ -6,5 +6,5 @@
 export default async function SinAcceso() {
   const sesion = await auth();
   if (!sesion.userId) redirect("/ingresar");
-  return <PantallaSinAcceso />;
+  return <PantallaSinAcceso email="servidor@ejemplo.invalid" />;
 }
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/app/sin-acceso/page.test.tsx
2026-10-28T11:24:31.586765-03:00
 ❯ src/app/sin-acceso/page.test.tsx (2 tests | 1 failed) 25ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/app/sin-acceso/page.test.tsx > con sesión dibuja sin prop email, sin currentUser, API ni fetch
AssertionError: expected { email: 'servidor@ejemplo.invalid' } to deeply equal {}
 ❯ src/app/sin-acceso/page.test.tsx:29:48
      Tests  1 failed | 1 passed (2)
exit=1
```

## 3.5-b

```diff
--- web/src/app/sin-acceso/page.tsx
+++ web/src/app/sin-acceso/page.tsx
@@ -6,5 +6,6 @@
 export default async function SinAcceso() {
   const sesion = await auth();
   if (!sesion.userId) redirect("/ingresar");
+  await (await import("../../lib/api/cliente")).pedirApi("/api/sesion");
   return <PantallaSinAcceso />;
 }
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/app/sin-acceso/page.test.tsx
2026-10-28T11:24:32.827550-03:00
 ❯ src/app/sin-acceso/page.test.tsx (2 tests | 1 failed) 22ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/app/sin-acceso/page.test.tsx > con sesión dibuja sin prop email, sin currentUser, API ni fetch
AssertionError: expected "vi.fn()" to not be called at all, but actually been called 1 times
 ❯ src/app/sin-acceso/page.test.tsx:31:28
      Tests  1 failed | 1 passed (2)
exit=1
```

## 3.5-c

```diff
--- web/src/app/layout.tsx
+++ web/src/app/layout.tsx
@@ -16,7 +16,7 @@
 export default async function RootLayout({ children }: { children: ReactNode }) {
   const ruta = (await headers()).get("x-proptech-ruta") ?? "/";
   const invitacion = ruta.startsWith("/invitacion/");
-  const protegida = ruta.startsWith("/edificios") || ruta.startsWith("/personal");
+  const protegida = ruta.startsWith("/sin-acceso") || ruta.startsWith("/edificios") || ruta.startsWith("/personal");
   const resultado = protegida ? await pedirApi<DatosDeSesion>("/api/sesion") : null;
   const valor =
     resultado?.estado === "ok"
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/app/layout.test.tsx
2026-10-28T11:24:34.052439-03:00
 ❯ src/app/layout.test.tsx (3 tests | 1 failed) 8ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/app/layout.test.tsx > layout /sin-acceso pide API sólo en dominio
AssertionError: expected "vi.fn()" to be called +0 times, but got 1 times
 ❯ src/app/layout.test.tsx:19:17
      Tests  1 failed | 2 passed (3)
exit=1
```

## 3.5-email

```diff
--- web/src/app/sin-acceso/Pantalla.tsx
+++ web/src/app/sin-acceso/Pantalla.tsx
@@ -8,7 +8,7 @@
 function EmailDeCuenta() {
   const { user } = useUser();
   const email = user?.primaryEmailAddress?.emailAddress;
-  return email ? <p>{email}</p> : null;
+  return <p>{String(email)}</p>;
 }
 
 export function PantallaSinAcceso() {
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/app/sin-acceso/Pantalla.test.tsx
2026-10-28T11:24:35.305195-03:00
 ❯ src/app/sin-acceso/Pantalla.test.tsx (5 tests | 1 failed) 308ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/app/sin-acceso/Pantalla.test.tsx > sin email no inventa ni vacío ni undefined
AssertionError: expected 'PropTechTu cuenta no tiene acceso tod…' not to contain 'undefined'
 ❯ src/app/sin-acceso/Pantalla.test.tsx:38:37
      Tests  1 failed | 4 passed (5)
exit=1
```

## 3.5-carga

```diff
--- web/src/app/sin-acceso/Pantalla.tsx
+++ web/src/app/sin-acceso/Pantalla.tsx
@@ -35,9 +35,9 @@
           </p>
           <ClerkLoaded>
             <EmailDeCuenta />
-          </ClerkLoaded>
           <a href="/ingresar?cerrar=1">Cerrar sesión</a>
           <a href="/elegir-administracion">Volver a intentar</a>
+          </ClerkLoaded>
         </Panel>
       </div>
     </Armazon>
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/app/sin-acceso/Pantalla.test.tsx
2026-10-28T11:24:37.045552-03:00
 ❯ src/app/sin-acceso/Pantalla.test.tsx (5 tests | 1 failed) 324ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/app/sin-acceso/Pantalla.test.tsx > las dos acciones existen aunque Clerk no cargue
AssertionError: expected null to be truthy
 ❯ src/app/sin-acceso/Pantalla.test.tsx:44:65
      Tests  1 failed | 4 passed (5)
exit=1
```

## 3.6

```diff
--- web/src/app/sin-acceso/Pantalla.tsx
+++ web/src/app/sin-acceso/Pantalla.tsx
@@ -37,7 +37,7 @@
             <EmailDeCuenta />
           </ClerkLoaded>
           <a href="/ingresar?cerrar=1">Cerrar sesión</a>
-          <a href="/elegir-administracion">Volver a intentar</a>
+          <a tabIndex={-1} href="/elegir-administracion">Volver a intentar</a>
         </Panel>
       </div>
     </Armazon>
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/app/sin-acceso/Pantalla.test.tsx
2026-10-28T11:24:38.868646-03:00
 ❯ src/app/sin-acceso/Pantalla.test.tsx (5 tests | 1 failed) 302ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/app/sin-acceso/Pantalla.test.tsx > Tab y Enter recorren y activan las dos acciones
AssertionError: expected <body><div>…(1)</div></body> to be <a tabindex="-1" …(1)></a> // Object.is equality
 ❯ src/app/sin-acceso/Pantalla.test.tsx:64:34
      Tests  1 failed | 4 passed (5)
exit=1
```

## 3.7 · D2 en navegador

```diff
--- web/src/app/elegir-administracion/page.tsx
+++ mutante
@@ -12,7 +12,7 @@
   searchParams: Promise<{ regreso?: string; aceptada?: string }>;
 }) {
   const q = await searchParams;
-  const resultado = await pedirApi<DatosDeSesion>("/api/sesion", { alNoAutenticar: "devolver" });
+  const resultado = await pedirApi<DatosDeSesion>("/api/sesion");
   if (resultado.estado === "sin_sesion") return <SesionNoUtilizable />;
   if (resultado.estado !== "ok")
     return <ErrorDePantalla mensaje="No pudimos cargar tus administraciones." />;
```

```text
COMMAND: bash infra/ci/test-web-navegador.sh sesion.spec.ts --grep 2d API rechaza
11:25:08–11:25:22 -03:00, 28/10/2026
expect(locator).toBeVisible failed; heading No pudimos validar tu sesión ausente.
sesion.spec.ts:118:85; 1 failed; exit 1.
```

## 3.5-axe · comprobación nacida verde

```diff
--- web/src/app/sin-acceso/Pantalla.tsx
+++ mutante
@@ -28,7 +28,7 @@
             />
           }
         />
-        <Panel titulo="Tu acceso a PropTech">
+        <Panel titulo="Tu acceso a PropTech"><button type="button" />
           <p>
             Pedile a tu administración que te invite. Si ingresaste con otra cuenta, cerrá la
             sesión.
```

```text
cd web && corepack pnpm@12.10.1 vitest run src/app/sin-acceso/Pantalla.test.tsx -t axe
2026-10-28T11:27:54.583709-03:00
AssertionError en Pantalla.test.tsx: axe informa button-name para botón sin nombre; 1 failed, 4 skipped; exit1.
```
