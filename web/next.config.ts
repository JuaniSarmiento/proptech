import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // D-051/D1 (tarea 2c 3.1): sin esto, Next.js agrega X-Powered-By: Next.js
  // a cada respuesta (el proxy no puede distinguirlo de una cabecera que
  // sí haga falta, así que se apaga en el origen).
  poweredByHeader: false,
  // H-025: el comprobante de un pago (JPG, PNG o PDF de hasta 10 MB, el tope de la API) viaja por una
  // server action; el límite por defecto de Next (1 MB) cortaría casi toda foto de celular.
  experimental: { serverActions: { bodySizeLimit: "11mb" } },
};

export default nextConfig;
