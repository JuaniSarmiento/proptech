import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // D-051/D1 (tarea 2c 3.1): sin esto, Next.js agrega X-Powered-By: Next.js
  // a cada respuesta (el proxy no puede distinguirlo de una cabecera que
  // sí haga falta, así que se apaga en el origen).
  poweredByHeader: false,
};

export default nextConfig;
