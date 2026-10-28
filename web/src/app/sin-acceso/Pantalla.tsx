"use client";
import { ClerkLoaded, useUser } from "@clerk/nextjs";
import { Armazon } from "../../componentes/Armazon";
import { Ayuda } from "../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";
import { Panel } from "../../componentes/Panel";

function EmailDeCuenta() {
  const { user } = useUser();
  const email = user?.primaryEmailAddress?.emailAddress;
  return email ? <p>{email}</p> : null;
}

export function PantallaSinAcceso() {
  return (
    <Armazon publico>
      <div className="pagina-acceso">
        <EncabezadoDePantalla
          titulo="Tu cuenta no tiene acceso todavía"
          ayuda={
            <Ayuda
              paraQueSirve="Podés revisar con qué cuenta ingresaste y volver a entrar."
              pasos={[
                "Si usaste otra cuenta, cerrá la sesión.",
                "Pedile a tu administración que revise tu acceso.",
              ]}
              yDespues="Volvé a intentar cuando tu administración te dé acceso."
            />
          }
        />
        <Panel titulo="Tu acceso a PropTech">
          <p>
            Pedile a tu administración que te invite. Si ingresaste con otra cuenta, cerrá la
            sesión.
          </p>
          <ClerkLoaded>
            <EmailDeCuenta />
          </ClerkLoaded>
          <a href="/ingresar?cerrar=1">Cerrar sesión</a>
          <a href="/elegir-administracion">Volver a intentar</a>
        </Panel>
      </div>
    </Armazon>
  );
}
