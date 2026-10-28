"use client";
import { Building2 } from "lucide-react";
import { useActionState, useEffect, useRef } from "react";
import { Armazon } from "../../componentes/Armazon";
import { Ayuda } from "../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";
import { FilaConIcono } from "../../componentes/FilaConIcono";
import { Panel } from "../../componentes/Panel";
import type { DatosDeSesion } from "../../componentes/SesionDePantalla";
export function PantallaSelector({
  datos,
  aceptada,
  accion,
}: {
  datos: DatosDeSesion;
  aceptada: boolean;
  accion: (previo: string | null, form: FormData) => Promise<string | null>;
}) {
  const [error, enviar, pendiente] = useActionState(accion, null);
  const form = useRef<HTMLFormElement>(null);
  useEffect(() => {
    if (datos.administraciones.length === 1 && !aceptada) form.current?.requestSubmit();
  }, [datos, aceptada]);
  return (
    <Armazon publico>
      <EncabezadoDePantalla
        titulo="Elegí una administración"
        ayuda={
          <Ayuda
            paraQueSirve="Elegís con qué administración vas a trabajar."
            pasos={["Buscá el nombre de tu administración.", "Tocá su nombre para entrar."]}
            yDespues="Podés cambiarla desde tu cuenta en la barra superior."
          />
        }
      />
      {aceptada ? <p role="status">Invitación aceptada.</p> : null}
      <Panel titulo={datos.persona.nombre} descripcion="Tus administraciones">
        {error ? <p role="alert">{error}</p> : null}
        <form ref={form} action={enviar}>
          <ul className="lista-de-filas" aria-label="Administraciones">
            {datos.administraciones.map((a) => (
              <li key={a.id}>
                <FilaConIcono
                  icono={Building2}
                  titulo={
                    <button
                      type="submit"
                      className="boton-enlace"
                      name="administracion_id"
                      value={a.id}
                      disabled={pendiente}
                    >
                      {a.nombre}
                    </button>
                  }
                />
              </li>
            ))}
          </ul>
          {datos.administraciones.length === 1 ? (
            <input type="hidden" name="administracion_id" value={datos.administraciones[0]?.id} />
          ) : null}
        </form>
      </Panel>
    </Armazon>
  );
}

export function SesionNoUtilizable() {
  return (
    <Armazon publico>
      <div className="pagina-acceso">
        <EncabezadoDePantalla
          titulo="No pudimos validar tu sesión"
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
        <Panel titulo="Volvé a ingresar">
          <p>Cerrá la sesión para volver a ingresar con tu cuenta.</p>
          <a href="/ingresar?cerrar=1">Cerrar sesión</a>
        </Panel>
      </div>
    </Armazon>
  );
}
