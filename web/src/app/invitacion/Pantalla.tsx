"use client";
import { useActionState } from "react";
import { Armazon } from "../../componentes/Armazon";
import { Ayuda } from "../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";
import { Panel } from "../../componentes/Panel";
export function PantallaInvitacion({
  accion,
  ingreso,
  registro,
}: {
  accion:
    | ((previo: { error: boolean } | null, form: FormData) => Promise<{ error: boolean }>)
    | null;
  ingreso: string;
  registro: string;
}) {
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
            <p role="alert">
              Este enlace ya no sirve. Pedile a tu administración que te invite de nuevo.
            </p>
          ) : accion ? (
            <form action={enviar}>
              <button type="submit" className="boton-principal" disabled={pendiente}>
                {pendiente ? "Aceptando…" : "Aceptar e ingresar"}
              </button>
            </form>
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
          {accion ? <a href={ingreso}>Cerrar sesión</a> : null}
        </Panel>
        <a href="/privacidad">Aviso de privacidad</a>
      </div>
    </Armazon>
  );
}
