"use client";
import { ClerkLoaded, ClerkLoading, SignIn, SignUp, useClerk } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { Armazon } from "../../componentes/Armazon";
import { Ayuda } from "../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";
import { Estados } from "../../componentes/Estados";
import { Panel } from "../../componentes/Panel";

const apariencia = {
  variables: {
    colorPrimary: "var(--color-terracota)",
    colorBackground: "var(--color-papel-claro)",
    colorText: "var(--color-tinta)",
    colorTextSecondary: "var(--color-grafito)",
    colorInputBackground: "var(--color-papel-claro)",
    colorInputText: "var(--color-tinta)",
    fontFamily: "var(--tipo-fuente-base)",
    fontSize: "var(--tipo-cuerpo)",
    borderRadius: "var(--radio-control)",
  },
  elements: {
    rootBox: "clerk-proptech",
    cardBox: "clerk-proptech",
    card: { boxShadow: "none", padding: "0", borderRadius: "0" },
    footer: { background: "var(--color-papel-claro)" },
    formButtonPrimary: "boton-principal",
    formFieldInput: "clerk-campo",
    headerTitle: { display: "none" },
  },
};
function EsperaDeClerk() {
  const [fallo, setFallo] = useState(false);
  useEffect(() => {
    const id = setTimeout(() => setFallo(true), 6000);
    return () => clearTimeout(id);
  }, []);
  return fallo ? (
    <div role="alert">
      <p>No pudimos conectar con el servicio de ingreso.</p>
      <p className="texto-secundario">Volvé a cargar esta página en unos minutos.</p>
      <button type="button" className="boton-enlace" onClick={() => window.location.reload()}>
        Volver a cargar
      </button>
    </div>
  ) : (
    <Estados tipo="cargando" />
  );
}
function CerrarSesion({ regreso }: { regreso: string }) {
  const clerk = useClerk();
  useEffect(() => {
    void clerk.signOut({ redirectUrl: `/ingresar?${new URLSearchParams({ regreso })}` });
  }, [clerk, regreso]);
  return <EsperaDeClerk />;
}
export function PantallaIngreso({
  regreso,
  registro = false,
  cerrar = false,
}: {
  regreso: string;
  registro?: boolean;
  cerrar?: boolean;
}) {
  const destino = `/elegir-administracion?${new URLSearchParams({ regreso })}`;
  return (
    <Armazon publico>
      <div className="pagina-acceso">
        <EncabezadoDePantalla
          titulo={registro ? "Creá tu cuenta" : "Ingresar"}
          ayuda={
            <Ayuda
              paraQueSirve="Entrás con la cuenta del email al que te invitaron."
              pasos={[
                "Usá tu contraseña o el enlace por email.",
                "Si recibiste una invitación, seguí el enlace de ese mail.",
              ]}
              yDespues="Vas a tu administración o elegís una si trabajás con varias."
            />
          }
        />
        <Panel
          titulo={registro ? "Tu cuenta en PropTech" : "Tu cuenta"}
          descripcion="Usá el email con el que te invitaron."
        >
          <ClerkLoading>
            <EsperaDeClerk />
          </ClerkLoading>
          <ClerkLoaded>
            {cerrar ? (
              <CerrarSesion regreso={regreso} />
            ) : registro ? (
              <SignUp
                appearance={apariencia}
                routing="hash"
                forceRedirectUrl={regreso}
                signInUrl={`/ingresar?${new URLSearchParams({ regreso })}`}
              />
            ) : (
              <SignIn
                appearance={apariencia}
                routing="hash"
                withSignUp={false}
                forceRedirectUrl={regreso.startsWith("/invitacion/") ? regreso : destino}
              />
            )}
          </ClerkLoaded>
        </Panel>
        <p className="texto-secundario">¿Te invitaron? Revisá tu mail: el enlace te trae acá.</p>
        {regreso.startsWith("/invitacion/") && !registro ? (
          <a href={`/registrarse?${new URLSearchParams({ regreso })}`}>
            Crear cuenta desde mi invitación
          </a>
        ) : null}
        <a href="/privacidad">Aviso de privacidad</a>
      </div>
    </Armazon>
  );
}
