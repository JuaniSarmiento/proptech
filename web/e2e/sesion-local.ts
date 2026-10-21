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

/** R2B-4 (rompedor 2b): el `__session` y el `__client_uat` de un contexto
 * de prueba tienen que salir de la MISMA lectura del reloj. Si se leyeran
 * por separado (una para `crearToken()`, otra después para
 * `__client_uat`), un cambio de segundo entre las dos deja `iat <
 * __client_uat`, y @clerk/backend responde con un handshake hacia el
 * emisor `.invalid` que esta suite no sabe resolver. `duracionS` (una
 * hora por defecto) cubre con margen cualquier test real: el token de
 * 60s por defecto de `crearToken()` vencía en cualquier test de más de
 * 65s desde que se armó el contexto. */
export function cookiesDeContextoDePrueba(duracionS = 3600) {
  const ahora = Math.floor(Date.now() / 1000);
  return {
    session: crearToken({ iat: ahora, nbf: ahora, exp: ahora + duracionS }),
    clientUat: String(ahora),
  };
}
