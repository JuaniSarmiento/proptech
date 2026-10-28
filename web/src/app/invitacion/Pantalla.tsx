"use client";
import { esES } from "@clerk/localizations";
import { ClerkLoaded, ClerkProvider, useClerk } from "@clerk/nextjs";
import { useActionState, useEffect, useState } from "react";
import { Armazon } from "../../componentes/Armazon";
import { Ayuda } from "../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";
import { Panel } from "../../componentes/Panel";

/**
 * B-3 (2d, 7.8, D10): con sesión, decir con qué cuenta se está entrando —
 * nunca el email del sobre (`destinatario`), que la API no expone (D-dev).
 * Sin el claim de email en el token de sesión, las dos formas quedan
 * genéricas, sin nombrar ningún email (ni vacío ni "undefined"). Los tests
 * de componente no verifican Clerk real; su recorrido y pendientes se
 * registran en la tarea 8.2 e.
 */
function mensajeDeCuenta(claimEmail: string | null): string {
  return claimEmail
    ? `Estás ingresado como ${claimEmail}.`
    : "Hay una sesión abierta en este navegador.";
}

function mensajeDeErrorConSesion(claimEmail: string | null): string {
  const cuenta = claimEmail ? `con la cuenta ${claimEmail}` : "con la cuenta con la que ingresaste";
  return (
    `Este enlace no sirve ${cuenta}. Si la invitación es para otro email, usá otra cuenta; ` +
    "si es para ésta, pedile a tu administración que te invite de nuevo."
  );
}

export function PantallaInvitacion({
  accion,
  ingreso,
  registro,
  claimEmail = null,
  volverAInvitacion,
}: {
  accion:
    | ((previo: { error: boolean } | null, form: FormData) => Promise<{ error: boolean }>)
    | null;
  ingreso: string;
  registro: string;
  volverAInvitacion: string;
  /** B-3 (D10): el email del claim firmado del token de sesión, leído en el
   * servidor — `null` sin sesión o sin ese claim. */
  claimEmail?: string | null;
}) {
  const [cerrandoSesion, setCerrandoSesion] = useState(false);
  const [estado, enviar, pendiente] = useActionState(accion ?? (async () => null), null);
  return (
    <Armazon publico>
      <div className="pagina-acceso">
        <EncabezadoDePantalla
          titulo="Aceptá tu invitación"
          ayuda={
            <Ayuda
              paraQueSirve="Este enlace te permite unirte a tu administración."
              pasos={["Ingresá con el email al que te invitaron.", "Tocá Aceptar e ingresar."]}
              yDespues="Cuando se acepte, vas a ver tu administración y podrás entrar."
            />
          }
        />
        <Panel
          titulo="Tu invitación"
          descripcion="Al aceptar, tu cuenta queda vinculada a la administración que te invitó."
        >
          {estado?.error ? (
            <p role="alert">{mensajeDeErrorConSesion(claimEmail)}</p>
          ) : accion ? (
            <>
              <p>{mensajeDeCuenta(claimEmail)}</p>
              <form action={enviar}>
                <button type="submit" className="boton-principal" disabled={pendiente}>
                  {pendiente ? "Aceptando…" : "Aceptar e ingresar"}
                </button>
              </form>
            </>
          ) : (
            <>
              <a className="boton-principal" href={ingreso}>
                Aceptar e ingresar
              </a>
              <p className="texto-secundario">
                Primero ingresá con tu cuenta. Si todavía no tenés una,{" "}
                <a href={registro}>creá tu cuenta desde esta invitación</a>.
              </p>
            </>
          )}
          {/* Enmienda E10: cerrar y volver directamente a la invitación
           * con el ticket. El proveedor local se carga al pedir salir;
           * los enlaces de ingreso y registro siguen siendo independientes. */}
          {accion ? (
            cerrandoSesion ? (
              <>
                <p role="status">Cerrando sesión…</p>
                <ClerkProvider dynamic localization={esES}>
                  <ClerkLoaded>
                    <CerrarSesionDeInvitacion destino={volverAInvitacion} />
                  </ClerkLoaded>
                </ClerkProvider>
              </>
            ) : (
              <button
                type="button"
                className="boton-enlace"
                onClick={() => setCerrandoSesion(true)}
              >
                Usar otra cuenta
              </button>
            )
          ) : null}
        </Panel>
        <a href="/privacidad">Aviso de privacidad</a>
      </div>
    </Armazon>
  );
}

function CerrarSesionDeInvitacion({ destino }: { destino: string }) {
  const clerk = useClerk();
  useEffect(() => {
    void clerk.signOut({ redirectUrl: destino });
  }, [clerk, destino]);
  return null;
}
