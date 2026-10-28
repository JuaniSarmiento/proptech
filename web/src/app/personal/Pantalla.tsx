"use client";

/**
 * Personal de la administración (D5, shape del 21/10/2026, tarea 7.3): una
 * fila por persona con su perfil, su alcance y el estado de su invitación;
 * "Invitar a alguien" abre el panel lateral con nombre, email, perfil y
 * alcance (edificio sólo si el perfil lo permite). Sólo el super admin ve
 * los controles de invitar, revocar y quitar (D5); el resto ve la lista en
 * lectura si su perfil puede verla (acá: nunca, D5/L-030 — el GET exige
 * super admin, así que cualquier otro perfil ya ve "Sin permiso" antes de
 * llegar a esta pantalla).
 *
 * Mismo patrón que `edificios/[id]/unidades/Pantalla.tsx`: panel principal
 * con la tabla, panel lateral de apoyo con el resumen, panel lateral con el
 * formulario.
 */

import { UserPlus, Users } from "lucide-react";
import { useActionState, useEffect, useRef, useState } from "react";
import { Armazon } from "../../componentes/Armazon";
import { Ayuda } from "../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";
import { Estados } from "../../componentes/Estados";
import { FilaConIcono } from "../../componentes/FilaConIcono";
import { Campo, Formulario } from "../../componentes/Formulario";
import { MenuDelEdificio } from "../../componentes/MenuDelEdificio";
import { Panel } from "../../componentes/Panel";
import { PanelLateral } from "../../componentes/PanelLateral";
import type { AsignacionDePersona, Persona } from "../../lib/api/personal";
import type { EdificioDeLista } from "../../lib/api/tipos";
import { AYUDA_PERSONAL } from "./ayuda";
import { ESTADOS_REVOCABLES, textoDeEstadoDeInvitacion } from "./estados";
import {
  etiquetaDePerfil,
  queHaceElPerfil,
  ROLES_INVITABLES,
  ROLES_SOLO_EDIFICIO,
  type Rol,
} from "./perfiles";
import { seccionesDeLaAdministracion } from "./secciones";

export type EstadoFormularioPersonal = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
  ok?: boolean;
} | null;

export type EstadoAccionSimple = { ok?: boolean; error?: string } | null;

type AccionInvitar = (
  estadoPrevio: EstadoFormularioPersonal,
  formData: FormData,
) => Promise<EstadoFormularioPersonal>;

type AccionSimple = (
  estadoPrevio: EstadoAccionSimple,
  formData: FormData,
) => Promise<EstadoAccionSimple>;

type Props = {
  personas: Persona[];
  edificios: EdificioDeLista[];
  accionInvitar: AccionInvitar;
  accionRevocar: AccionSimple;
  accionQuitar: AccionSimple;
};

function nombreDeEdificio(edificios: EdificioDeLista[], id: string | null): string {
  if (!id) return "Toda la empresa";
  return edificios.find((e) => e.id === id)?.nombre ?? "Un edificio";
}

/** 6.4 (D10): lo que hace falta para armar la confirmación de "Quitar" —
 * la asignación en sí y el nombre de la persona a la que se le quita, que
 * la spec exige mostrar en el diálogo. */
export type AsignacionAQuitar = { asignacion: AsignacionDePersona; personaNombre: string };

function Asignaciones({
  personaNombre,
  asignaciones,
  edificios,
  quitadas,
  onQuitar,
}: {
  personaNombre: string;
  asignaciones: AsignacionDePersona[];
  edificios: EdificioDeLista[];
  quitadas: Set<string>;
  onQuitar: (objetivo: AsignacionAQuitar, evento: { currentTarget: HTMLElement }) => void;
}) {
  return (
    <ul className="lista-de-filas lista-de-filas--compacta" aria-label="Perfiles">
      {asignaciones.map((asignacion) => (
        <li key={asignacion.asignacion_id} className="fila-de-asignacion">
          <span>
            <strong>{etiquetaDePerfil(asignacion.rol)}</strong>
            <span className="texto-secundario">
              {" "}
              · {nombreDeEdificio(edificios, asignacion.complejo_id)}
            </span>
          </span>
          <BotonQuitar
            asignacion={asignacion}
            personaNombre={personaNombre}
            quitada={quitadas.has(asignacion.asignacion_id)}
            onQuitar={onQuitar}
          />
        </li>
      ))}
    </ul>
  );
}

/**
 * D10 (tarea 6.4): "Quitar" ya no manda nada por sí solo — abre la
 * confirmación de `PanelLateral` (`role="dialog"`, `Esc`, foco devuelto),
 * nunca el patrón inline de `saldos-previos/Pantalla.tsx` (sin `Esc`) ni
 * `window.confirm()` nativo (ninguno de los dos cumple el escenario "Quitar
 * y cancelar con teclado" de `pantallas-del-edificio`).
 */
function BotonQuitar({
  asignacion,
  personaNombre,
  quitada,
  onQuitar,
}: {
  asignacion: AsignacionDePersona;
  personaNombre: string;
  quitada: boolean;
  onQuitar: (objetivo: AsignacionAQuitar, evento: { currentTarget: HTMLElement }) => void;
}) {
  if (quitada) {
    return <span className="texto-secundario">Quitada</span>;
  }
  return (
    <button
      type="button"
      className="boton-enlace"
      onClick={(evento) => onQuitar({ asignacion, personaNombre }, evento)}
    >
      Quitar
    </button>
  );
}

function BotonRevocar({
  invitacionId,
  accionRevocar,
}: {
  invitacionId: string;
  accionRevocar: AccionSimple;
}) {
  const [estado, enviar] = useActionState(accionRevocar, null);
  if (estado?.ok) {
    return <span className="texto-secundario">Revocada</span>;
  }
  return (
    <form action={enviar}>
      <input type="hidden" name="invitacion_id" value={invitacionId} />
      <button type="submit" className="boton-enlace">
        Revocar
      </button>
      {estado?.error ? (
        <p role="alert" className="campo__error">
          {estado.error}
        </p>
      ) : null}
    </form>
  );
}

function FilaDePersona({
  persona,
  edificios,
  accionRevocar,
  quitadas,
  onQuitar,
}: {
  persona: Persona;
  edificios: EdificioDeLista[];
  accionRevocar: AccionSimple;
  quitadas: Set<string>;
  onQuitar: (objetivo: AsignacionAQuitar, evento: { currentTarget: HTMLElement }) => void;
}) {
  const invitacion = persona.invitacion;
  const estadoTexto = invitacion
    ? textoDeEstadoDeInvitacion(invitacion.estado)
    : persona.vinculado
      ? "Vinculada"
      : "—";
  const puedeRevocar = invitacion && ESTADOS_REVOCABLES.has(invitacion.estado);
  return (
    <tr>
      <td>
        <p>{persona.nombre}</p>
        <p className="texto-secundario">{persona.email}</p>
      </td>
      <td>
        <Asignaciones
          personaNombre={persona.nombre}
          asignaciones={persona.asignaciones}
          edificios={edificios}
          quitadas={quitadas}
          onQuitar={onQuitar}
        />
      </td>
      <td>{estadoTexto}</td>
      <td>
        {puedeRevocar && invitacion ? (
          <BotonRevocar invitacionId={invitacion.invitacion_id} accionRevocar={accionRevocar} />
        ) : null}
      </td>
    </tr>
  );
}

function FormularioInvitar({
  edificios,
  estado,
  enviar,
}: {
  edificios: EdificioDeLista[];
  estado: EstadoFormularioPersonal;
  enviar: (formData: FormData) => void;
}) {
  const [rol, setRol] = useState<Rol>("administrador");
  const soloEdificio = ROLES_SOLO_EDIFICIO.has(rol);
  const [alcance, setAlcance] = useState<string>("principal");
  const alcanceEfectivo = soloEdificio ? "edificio" : alcance;
  return (
    <Formulario
      erroresPorCampo={estado?.erroresPorCampo ?? {}}
      erroresDesconocidos={estado?.erroresDesconocidos ?? []}
      action={enviar}
    >
      <Campo nombre="nombre" etiqueta="Nombre" name="nombre" required />
      <Campo nombre="email" etiqueta="Email" name="email" type="email" required />
      <label className="campo">
        Perfil
        <select name="rol" value={rol} onChange={(e) => setRol(e.target.value as Rol)}>
          {ROLES_INVITABLES.map((r) => (
            <option key={r.valor} value={r.valor}>
              {r.etiqueta}
            </option>
          ))}
        </select>
      </label>
      {soloEdificio ? (
        <input type="hidden" name="alcance" value="edificio" />
      ) : (
        <label className="campo">
          Alcance
          <select name="alcance" value={alcance} onChange={(e) => setAlcance(e.target.value)}>
            <option value="principal">Toda la empresa</option>
            <option value="edificio">Un edificio</option>
          </select>
        </label>
      )}
      {alcanceEfectivo === "edificio" ? (
        <div className="campo">
          <label htmlFor="campo-complejo_id">Edificio</label>
          <select
            id="campo-complejo_id"
            name="complejo_id"
            required
            aria-invalid={Boolean(estado?.erroresPorCampo?.complejo_id)}
            aria-describedby={
              estado?.erroresPorCampo?.complejo_id ? "campo-complejo_id-error" : undefined
            }
          >
            {edificios.map((e) => (
              <option key={e.id} value={e.id}>
                {e.nombre}
              </option>
            ))}
          </select>
          {estado?.erroresPorCampo?.complejo_id ? (
            <p id="campo-complejo_id-error" className="campo__error">
              {estado.erroresPorCampo.complejo_id}
            </p>
          ) : null}
        </div>
      ) : null}
      <button type="submit" className="boton-principal">
        Invitar
      </button>
    </Formulario>
  );
}

export function PantallaPersonal({
  personas,
  edificios,
  accionInvitar,
  accionRevocar,
  accionQuitar,
}: Props) {
  const [panelAbierto, setPanelAbierto] = useState(false);
  const botonInvitarRef = useRef<HTMLButtonElement>(null);
  const [estado, enviar] = useActionState(accionInvitar, null);

  // Mismo patrón que `unidades/Pantalla.tsx` (RF-F-2): guardar cierra el
  // panel y devuelve el foco a quien lo abrió, sólo cuando la API confirmó.
  useEffect(() => {
    if (estado?.ok) {
      setPanelAbierto(false);
      botonInvitarRef.current?.focus();
    }
  }, [estado]);

  // D10 (tarea 6.4): "Quitar" abre esta confirmación en vez de mandar nada
  // directo a la API. `aperturaQuitarRef` es el botón "Quitar" que la abrió
  // (R3C-4/L-026: el mismo patrón de foco que el resto de los paneles),
  // para que cancelar (con "Cancelar" o con `Esc`, los dos pasan por
  // `alCerrar` de `PanelLateral`) le devuelva el foco.
  const [objetivoAQuitar, setObjetivoAQuitar] = useState<AsignacionAQuitar | null>(null);
  const aperturaQuitarRef = useRef<HTMLElement | null>(null);
  const [estadoQuitar, enviarQuitar] = useActionState(accionQuitar, null);
  const [quitadas, setQuitadas] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (estadoQuitar?.ok && objetivoAQuitar) {
      setQuitadas((previas) => new Set(previas).add(objetivoAQuitar.asignacion.asignacion_id));
      setObjetivoAQuitar(null);
      aperturaQuitarRef.current?.focus();
    }
  }, [estadoQuitar, objetivoAQuitar]);

  function abrirConfirmacionDeQuitar(
    objetivo: AsignacionAQuitar,
    evento: { currentTarget: HTMLElement },
  ) {
    aperturaQuitarRef.current = evento.currentTarget;
    setPanelAbierto(false);
    setObjetivoAQuitar(objetivo);
  }

  // FE-3 (revisión del PR #2): los dos `PanelLateral` de esta pantalla no
  // son modales y cada uno atrapa `Tab` con su propio listener; abiertos a
  // la vez, se roban el foco y `Tab` queda clavado en el primer control.
  // Abrir uno cierra el otro: nunca hay dos.
  function abrirInvitar() {
    setObjetivoAQuitar(null);
    setPanelAbierto(true);
  }

  function cerrarConfirmacionDeQuitar() {
    setObjetivoAQuitar(null);
  }

  // Corrección L-026 (mirada de `personal-1440.png`, 21/10/2026): Personal
  // y el padrón de vecinos (7.4) leen la misma fuente (`GET /api/personal`,
  // L-030), así que una fila con `rol: "vecino"` puede llegar acá. Esta
  // pantalla es sólo personal (super admin, administrador, contador,
  // auxiliar, consejo); los vecinos viven en el padrón de unidades. Se
  // descartan las asignaciones de vecino, y con ellas la persona entera si
  // no le queda ninguna otra: así nunca aparece en la tabla ni en "Por
  // perfil", y nunca con alcance "Toda la empresa" (que para un vecino ni
  // siquiera es una forma válida, D-106: su alcance es su unidad).
  const personal = personas
    .map((persona) => ({
      ...persona,
      asignaciones: persona.asignaciones.filter((a) => a.rol !== "vecino"),
    }))
    .filter((persona) => persona.asignaciones.length > 0);

  const porPerfil = new Map<string, number>();
  for (const persona of personal) {
    for (const asignacion of persona.asignaciones) {
      porPerfil.set(asignacion.rol, (porPerfil.get(asignacion.rol) ?? 0) + 1);
    }
  }

  const botonInvitar = (
    <button ref={botonInvitarRef} type="button" className="boton-principal" onClick={abrirInvitar}>
      Invitar a alguien
    </button>
  );

  return (
    <Armazon
      menu={
        <MenuDelEdificio
          seccionActual="personal"
          secciones={seccionesDeLaAdministracion()}
          nombreAccesible="Tu administración"
        />
      }
    >
      <EncabezadoDePantalla
        titulo="Personal"
        ayuda={<Ayuda {...AYUDA_PERSONAL} />}
        accionPrincipal={botonInvitar}
      />
      <div className="disposicion">
        <Panel
          titulo="Quién trabaja con vos"
          descripcion="Tocá Invitar a alguien para sumar a una persona."
        >
          {personal.length === 0 ? (
            <Estados
              tipo="vacio"
              mensaje="Todavía no invitaste a nadie"
              detalle="Empezá invitando a la primera persona de tu equipo."
              accion={
                <button type="button" onClick={abrirInvitar}>
                  Invitar a alguien
                </button>
              }
            />
          ) : (
            <div className="padron-de-unidades__scroll">
              <table className="padron-de-unidades padron-de-unidades--envuelto">
                <caption className="sr-only">Personal de la administración</caption>
                <thead>
                  <tr>
                    <th>Persona</th>
                    <th>Perfil y alcance</th>
                    <th>Invitación</th>
                    <th>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {personal.map((persona) => (
                    <FilaDePersona
                      key={persona.persona_id}
                      persona={persona}
                      edificios={edificios}
                      accionRevocar={accionRevocar}
                      quitadas={quitadas}
                      onQuitar={abrirConfirmacionDeQuitar}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <div className="disposicion__lateral">
          <Panel titulo="Por perfil" variante="apoyo">
            <ul className="lista-de-filas lista-de-filas--compacta" aria-label="Por perfil">
              {[...porPerfil.entries()].map(([rol, cantidad]) => (
                <li key={rol}>
                  <FilaConIcono
                    icono={Users}
                    titulo={etiquetaDePerfil(rol)}
                    fin={<span className="numero-tabular">{cantidad}</span>}
                  />
                </li>
              ))}
            </ul>
          </Panel>
          <Panel titulo="Qué puede cada perfil" variante="apoyo">
            <ul
              className="lista-de-filas lista-de-filas--compacta"
              aria-label="Qué puede cada perfil"
            >
              {ROLES_INVITABLES.map((r) => (
                <li key={r.valor}>
                  <FilaConIcono
                    icono={UserPlus}
                    titulo={r.etiqueta}
                    detalle={queHaceElPerfil(r.valor)}
                  />
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>

      <PanelLateral
        abierto={panelAbierto}
        titulo="Invitar a alguien"
        alCerrar={() => setPanelAbierto(false)}
        devolverFocoA={botonInvitarRef}
      >
        <FormularioInvitar edificios={edificios} estado={estado} enviar={enviar} />
      </PanelLateral>

      {/* D10 (tarea 6.4): la confirmación de "Quitar" vive en un
       * `PanelLateral` propio (no el patrón inline-con-casilla de
       * saldos-previos, que no tiene `Esc`), con el nombre de la persona y
       * el alcance que se le quita, como pide la spec. */}
      <PanelLateral
        abierto={objetivoAQuitar !== null}
        titulo="Quitar este perfil"
        alCerrar={cerrarConfirmacionDeQuitar}
        devolverFocoA={aperturaQuitarRef}
      >
        {objetivoAQuitar ? (
          <div className="panel-lateral__seccion">
            <p>
              ¿Querés quitarle a <strong>{objetivoAQuitar.personaNombre}</strong> el perfil{" "}
              <strong>{etiquetaDePerfil(objetivoAQuitar.asignacion.rol)}</strong> ·{" "}
              {nombreDeEdificio(edificios, objetivoAQuitar.asignacion.complejo_id)}? Deja de tener
              ese acceso.
            </p>
            <form action={enviarQuitar}>
              <input
                type="hidden"
                name="asignacion_id"
                value={objetivoAQuitar.asignacion.asignacion_id}
              />
              <div className="panel-lateral__acciones">
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={cerrarConfirmacionDeQuitar}
                >
                  Cancelar
                </button>
                <button type="submit" className="boton-principal">
                  Quitar
                </button>
              </div>
            </form>
            {estadoQuitar?.error ? (
              <p role="alert" className="campo__error">
                {estadoQuitar.error}
              </p>
            ) : null}
          </div>
        ) : null}
      </PanelLateral>
    </Armazon>
  );
}
