/** Sólo pruebas: las claves RSA se generan localmente y jamás pertenecen a Clerk. */
import { createPublicKey, generateKeyPairSync, sign } from "node:crypto";

export const ADMINISTRACION = "10000000-0000-0000-0000-000000000001";
export const EMISOR = "https://clerk.proptech-prueba.invalid";
export const PUBLICABLE = `pk_live_${Buffer.from("clerk.proptech-prueba.invalid$").toString("base64")}`;
export const SECRETA_FALSA = "sk_test_" + "sin_validez_solo_pruebas";
export const PRIVADA =
  process.env.PROPTECH_CLAVE_PRIVADA_PRUEBA ??
  generateKeyPairSync("rsa", {
    modulusLength: 2048,
    privateKeyEncoding: { type: "pkcs8", format: "pem" },
    publicKeyEncoding: { type: "spki", format: "pem" },
  }).privateKey;
export const PUBLICA = createPublicKey(PRIVADA).export({ type: "spki", format: "pem" }).toString();

export function crearToken(cambios: Record<string, unknown> = {}) {
  const ahora = Math.floor(Date.now() / 1000);
  const cabecera = Buffer.from(JSON.stringify({ alg: "RS256", typ: "JWT", kid: "local" })).toString(
    "base64url",
  );
  const cuerpo = Buffer.from(
    JSON.stringify({
      sub: "user_prueba",
      sid: "sess_prueba",
      iss: EMISOR,
      azp: process.env.PROPTECH_URL_WEB ?? "http://127.0.0.1:3100",
      iat: ahora,
      nbf: ahora,
      exp: ahora + 60,
      v: 2,
      sts: "active",
      ...cambios,
    }),
  ).toString("base64url");
  const firma = sign("RSA-SHA256", Buffer.from(`${cabecera}.${cuerpo}`), PRIVADA).toString(
    "base64url",
  );
  return `${cabecera}.${cuerpo}.${firma}`;
}

export function cabecerasDePrueba() {
  return { authorization: `Bearer ${crearToken()}`, "x-proptech-administracion": ADMINISTRACION };
}
