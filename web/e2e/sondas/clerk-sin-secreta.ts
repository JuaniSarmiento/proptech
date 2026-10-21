/** Sonda manual de 6.1: ejecuta el SDK real, sin red ni secretos de Clerk. */

import assert from "node:assert/strict";
import { generateKeyPairSync, sign } from "node:crypto";
import { clerkMiddleware } from "@clerk/nextjs/server";
import { NextRequest } from "next/server";

const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const ahora = Math.floor(Date.now() / 1000);
const cabecera = Buffer.from(JSON.stringify({ alg: "RS256", typ: "JWT", kid: "local" })).toString(
  "base64url",
);
const cuerpo = Buffer.from(
  JSON.stringify({
    sub: "user_prueba",
    sid: "sess_prueba",
    iss: "https://proptech-prueba.clerk.accounts.dev",
    azp: "http://localhost:3100",
    iat: ahora,
    nbf: ahora,
    exp: ahora + 60,
    v: 2,
    sts: "active",
  }),
).toString("base64url");
const firma = sign("RSA-SHA256", Buffer.from(`${cabecera}.${cuerpo}`), privateKey).toString(
  "base64url",
);
const token = `${cabecera}.${cuerpo}.${firma}`;
const middleware = clerkMiddleware({
  publishableKey: `pk_test_${Buffer.from("proptech-prueba.clerk.accounts.dev$").toString("base64")}`,
  jwtKey: publicKey.export({ type: "spki", format: "pem" }).toString(),
  authorizedParties: ["http://localhost:3100"],
});
const request = new NextRequest("http://localhost:3100/edificios", {
  headers: { cookie: `__session=${token}; __client_uat=${ahora}`, accept: "text/html" },
});
// No se imprime el token ni la clave. No se simula el middleware ni su verificador.
const respuesta = await middleware(request, {} as Parameters<typeof middleware>[1]);
assert.equal(respuesta?.status, 200, "la sesión local debe pasar sin handshake ni clave secreta");
assert.equal(respuesta?.headers.get("location"), null);
