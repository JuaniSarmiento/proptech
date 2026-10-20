"use client";

/**
 * Formulario con resumen de errores enlazado y campos asociados por
 * programa (D8, tarea 3.7). Un 422/409 de la API llega al campo que nombra
 * su `loc`/`campo` (`erroresPorCampo`); uno para un campo que el formulario
 * no tiene (`erroresDesconocidos`) aparece sólo en el resumen, nunca
 * marcando un campo de más.
 */

import {
  type ComponentPropsWithoutRef,
  createContext,
  type FormHTMLAttributes,
  type ReactNode,
  useContext,
} from "react";

type Props = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos?: string[];
  /** Server action o URL del `<form>` (tarea 4.1): `Formulario` es dueño
   * del único `<form>` de la pantalla, así que el envío real pasa por acá,
   * nunca por un segundo `<form>` anidado. */
  action?: FormHTMLAttributes<HTMLFormElement>["action"];
  /** Validación previa a la acción (tarea 4.7): corre ANTES de `action`
   * (orden nativo del DOM); si llama a `preventDefault()`, la acción nunca
   * se dispara. Mismo motivo que `action`: un segundo `<form>` anidado es
   * inválido en HTML, así que esto también pasa por el único `<form>`. */
  onSubmit?: FormHTMLAttributes<HTMLFormElement>["onSubmit"];
  "aria-label"?: string;
  children: ReactNode;
};

function idDelCampo(nombre: string): string {
  return `campo-${nombre}`;
}

/** `Campo` lee su propio error acá por `nombre`, en vez de que cada
 * pantalla lo repita a mano en cada campo: un solo lugar sabe qué error
 * viene de la API (`Formulario`), y `Campo` sólo pregunta por el suyo. */
const _ContextoDeErrores = createContext<Record<string, string>>({});

export function Formulario({
  erroresPorCampo,
  erroresDesconocidos = [],
  action,
  onSubmit,
  "aria-label": ariaLabel,
  children,
}: Props) {
  const hayErrores = Object.keys(erroresPorCampo).length > 0 || erroresDesconocidos.length > 0;

  return (
    <_ContextoDeErrores.Provider value={erroresPorCampo}>
      <form className="formulario" action={action} onSubmit={onSubmit} aria-label={ariaLabel}>
        {hayErrores ? (
          <div role="alert" aria-label="Resumen de errores" className="formulario__resumen">
            <p>Revisá estos datos:</p>
            <ul>
              {Object.entries(erroresPorCampo).map(([campo, mensaje]) => (
                <li key={campo}>
                  <a
                    href={`#${idDelCampo(campo)}`}
                    onClick={(evento) => {
                      evento.preventDefault();
                      document.getElementById(idDelCampo(campo))?.focus();
                    }}
                  >
                    {mensaje}
                  </a>
                </li>
              ))}
              {erroresDesconocidos.map((mensaje) => (
                <li key={mensaje}>{mensaje}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {children}
      </form>
    </_ContextoDeErrores.Provider>
  );
}

type PropsDelCampo = {
  nombre: string;
  etiqueta: string;
  /** Error explícito; si se omite, `Campo` lo busca por `nombre` en el
   * `erroresPorCampo` del `Formulario` que lo contiene. */
  error?: string;
} & Omit<ComponentPropsWithoutRef<"input">, "id" | "aria-invalid" | "aria-describedby">;

/** Un campo asociado a su error por programa: siempre `aria-invalid`
 * (verdadero o falso, nunca ausente) y `aria-describedby` sólo cuando hay
 * mensaje que describir. */
export function Campo({ nombre, etiqueta, error: errorExplicito, ...resto }: PropsDelCampo) {
  const erroresDelFormulario = useContext(_ContextoDeErrores);
  const error = errorExplicito ?? erroresDelFormulario[nombre];
  const idCampo = idDelCampo(nombre);
  const idError = `${idCampo}-error`;
  return (
    <div className="campo">
      <label htmlFor={idCampo}>{etiqueta}</label>
      <input
        id={idCampo}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? idError : undefined}
        {...resto}
      />
      {error ? (
        <p id={idError} className="campo__error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
