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
  useEffect,
  useRef,
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

  const formularioRef = useRef<HTMLFormElement>(null);
  // R3C-3 (rompedor 3b): un `<form action={fn}>` con una acción función se
  // resetea solo cuando la acción TERMINA, sin importar si devuelve un
  // estado de error (React 19, mismo comportamiento que un submit nativo
  // exitoso) — y los `Campo` son no controlados (`defaultValue`), así que
  // vuelven a su valor por defecto. Guardamos lo tipeado ANTES de que la
  // acción corra y, si vuelve con error, lo reponemos: perder un 403/422/409
  // contradice la spec ("sin perder lo cargado").
  const ultimoEnvioRef = useRef<Record<string, string>>({});

  function alEnviar(evento: Parameters<NonNullable<typeof onSubmit>>[0]) {
    const formulario = evento.currentTarget;
    const valores: Record<string, string> = {};
    for (const [clave, valor] of new FormData(formulario).entries()) {
      if (typeof valor === "string") {
        valores[clave] = valor;
      }
    }
    ultimoEnvioRef.current = valores;
    onSubmit?.(evento);
  }

  // biome-ignore lint/correctness/useExhaustiveDependencies: depende de erroresPorCampo/erroresDesconocidos (cambian de identidad en cada resultado nuevo de la acción), no de hayErrores (sería el mismo `true` entre dos envíos fallidos seguidos y el efecto no volvería a correr).
  useEffect(() => {
    if (!hayErrores) {
      return;
    }
    const formulario = formularioRef.current;
    if (!formulario) {
      return;
    }
    for (const [nombre, valor] of Object.entries(ultimoEnvioRef.current)) {
      const campo = formulario.elements.namedItem(nombre);
      const esCampoDeTexto =
        campo instanceof HTMLInputElement ||
        campo instanceof HTMLTextAreaElement ||
        campo instanceof HTMLSelectElement;
      if (esCampoDeTexto) {
        campo.value = valor;
      }
    }
  }, [erroresPorCampo, erroresDesconocidos]);

  return (
    <_ContextoDeErrores.Provider value={erroresPorCampo}>
      <form
        ref={formularioRef}
        className="formulario"
        action={action}
        onSubmit={alEnviar}
        aria-label={ariaLabel}
      >
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

type PropsDeLista = {
  nombre: string;
  etiqueta: string;
  error?: string;
} & Omit<ComponentPropsWithoutRef<"select">, "id" | "aria-invalid" | "aria-describedby">;

/** D7 (tarea 6.0): mismo contrato que `Campo` (`id` de `idDelCampo`,
 * `aria-invalid` siempre presente, `aria-describedby` sólo con mensaje,
 * foco desde el mismo enlace del resumen) pero para un `<select>` — F1:
 * sin esto, cada lista encadenada nueva repite el patrón ya roto en 8 de
 * los 9 `<select>` que existían antes de esta tarea. */
export function CampoDeLista({
  nombre,
  etiqueta,
  error: errorExplicito,
  children,
  ...resto
}: PropsDeLista) {
  const erroresDelFormulario = useContext(_ContextoDeErrores);
  const error = errorExplicito ?? erroresDelFormulario[nombre];
  const idCampo = idDelCampo(nombre);
  const idError = `${idCampo}-error`;
  return (
    <div className="campo">
      <label htmlFor={idCampo}>{etiqueta}</label>
      <select
        id={idCampo}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? idError : undefined}
        {...resto}
      >
        {children}
      </select>
      {error ? (
        <p id={idError} className="campo__error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
