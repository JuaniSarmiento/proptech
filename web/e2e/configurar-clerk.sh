#!/usr/bin/env bash
# Se fuentea sólo desde el runner de navegador. RSA efímera, nunca un secreto real.
export PROPTECH_CLAVE_PRIVADA_PRUEBA
PROPTECH_CLAVE_PRIVADA_PRUEBA="$(node --input-type=module -e '
import { generateKeyPairSync } from "node:crypto";
console.log(generateKeyPairSync("rsa", { modulusLength: 2048,
  privateKeyEncoding: { type: "pkcs8", format: "pem" },
  publicKeyEncoding: { type: "spki", format: "pem" } }).privateKey);
')"
export CLERK_JWT_KEY
CLERK_JWT_KEY="$(node --input-type=module -e '
import { createPublicKey } from "node:crypto";
console.log(createPublicKey(process.env.PROPTECH_CLAVE_PRIVADA_PRUEBA).export({ type: "spki", format: "pem" }));
')"
export CLERK_PARTES_AUTORIZADAS="$PROPTECH_URL_WEB"
export CLERK_SECRET_KEY="sk_test_sin_validez_solo_pruebas"
# pk_live con dominio .invalid: fixture del protocolo de producción; no es una instancia.
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="pk_live_$(printf '%s' 'clerk.proptech-prueba.invalid$' | base64 | tr -d '\n')"
export NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
export CLERK_TELEMETRY_DISABLED=1
