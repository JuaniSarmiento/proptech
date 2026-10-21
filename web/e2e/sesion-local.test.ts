import { afterEach, describe, expect, it, vi } from "vitest";
import { cookiesDeContextoDePrueba, crearToken } from "./sesion-local";

function payloadDelToken(jwt: string): { iat: number; exp: number } {
  const cuerpo = jwt.split(".")[1];
  if (!cuerpo) throw new Error("token sin cuerpo");
  return JSON.parse(Buffer.from(cuerpo, "base64url").toString()) as { iat: number; exp: number };
}

/** La versión de `prueba.ts` ANTES del arreglo (R2B-4): dos lecturas del
 * reloj separadas, una para `crearToken()` y otra para `__client_uat`. */
function cookiesDeContextoViejas() {
  return { session: crearToken(), clientUat: String(Math.floor(Date.now() / 1000)) };
}

describe("cookiesDeContextoDePrueba (R2B-4, rompedor 2b)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("con dos lecturas del reloj, un cambio de segundo deja iat < __client_uat (rojo)", () => {
    const real = Date.now;
    let llamadas = 0;
    // La PRIMERA lectura (adentro de crearToken(), para el iat) cae en el
    // segundo T; la SEGUNDA (la de __client_uat, en prueba.ts) ya cayó en
    // T+1: exactamente lo que el rompedor reprodujo a mano con
    // `client_uat = ahora + 1`.
    vi.spyOn(Date, "now").mockImplementation(() => {
      llamadas += 1;
      return real() + (llamadas > 1 ? 1000 : 0);
    });

    const { session, clientUat } = cookiesDeContextoViejas();
    expect(payloadDelToken(session).iat).toBeLessThan(Number(clientUat));
  });

  it("con una sola lectura del reloj, iat y __client_uat siempre coinciden (verde)", () => {
    const real = Date.now;
    let llamadas = 0;
    vi.spyOn(Date, "now").mockImplementation(() => {
      llamadas += 1;
      return real() + (llamadas > 1 ? 1000 : 0);
    });

    const { session, clientUat } = cookiesDeContextoDePrueba();
    expect(payloadDelToken(session).iat).toBe(Number(clientUat));
  });

  it("el token vive más que cualquier test real (causa 2: el de 60s por defecto vencía pasados 65s)", () => {
    const { session } = cookiesDeContextoDePrueba();
    const { iat, exp } = payloadDelToken(session);
    expect(exp - iat).toBeGreaterThanOrEqual(3600);
  });
});
