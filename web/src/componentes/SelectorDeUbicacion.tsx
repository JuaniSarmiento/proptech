"use client";

/**
 * D3 (tarea 6.1): las tres listas encadenadas de ubicación (provincia →
 * departamento → localidad), con el vaciado en cascada al cambiar de
 * provincia/departamento y estado `cargando` (select deshabilitado) y
 * `error` con reintento por cada lista (D8, F3). El mensaje de error viaja
 * por la prop `error` de `CampoDeLista` (FE-1): así queda en el
 * `aria-describedby` y el `aria-invalid` del `<select>`, no sólo al lado; el
 * botón "Reintentar" va aparte, debajo. Cada `<select>` nativo:
 * operable con teclado sin nada adicional. Los tres valores viajan en el
 * `<form>` que lo contiene por su `name` (`provincia_id`/`departamento_id`/
 * `localidad_id`), nunca por un `fetch` desde el navegador (D11 del 3a).
 */

import { useEffect, useState } from "react";
import { departamentosDeAction, localidadesDeAction, provinciasAction } from "./accionesGeoref";
import { CampoDeLista } from "./Formulario";

type Opcion = { id: string; nombre: string };
type Carga<T> = { estado: "cargando" } | { estado: "ok"; datos: T } | { estado: "error" };

export type ValorDeUbicacion = {
  provinciaId: string;
  departamentoId: string;
  localidadId: string;
} | null;

type Props = {
  valorInicial?: ValorDeUbicacion;
};

export function SelectorDeUbicacion({ valorInicial = null }: Props) {
  const [provinciaId, setProvinciaId] = useState(valorInicial?.provinciaId ?? "");
  const [departamentoId, setDepartamentoId] = useState(valorInicial?.departamentoId ?? "");
  const [localidadId, setLocalidadId] = useState(valorInicial?.localidadId ?? "");

  const [provinciasC, setProvinciasC] = useState<Carga<Opcion[]>>({ estado: "cargando" });
  const [departamentosC, setDepartamentosC] = useState<Carga<Opcion[]>>({
    estado: "ok",
    datos: [],
  });
  const [localidadesC, setLocalidadesC] = useState<Carga<Opcion[]>>({ estado: "ok", datos: [] });

  function cargarProvincias() {
    setProvinciasC({ estado: "cargando" });
    provinciasAction().then((r) => {
      setProvinciasC(r.estado === "ok" ? { estado: "ok", datos: r.datos } : { estado: "error" });
    });
  }

  function cargarDepartamentos(deProvincia: string) {
    if (!deProvincia) {
      setDepartamentosC({ estado: "ok", datos: [] });
      return;
    }
    setDepartamentosC({ estado: "cargando" });
    departamentosDeAction(deProvincia).then((r) => {
      setDepartamentosC(r.estado === "ok" ? { estado: "ok", datos: r.datos } : { estado: "error" });
    });
  }

  function cargarLocalidades(deDepartamento: string) {
    if (!deDepartamento) {
      setLocalidadesC({ estado: "ok", datos: [] });
      return;
    }
    setLocalidadesC({ estado: "cargando" });
    localidadesDeAction(deDepartamento).then((r) => {
      setLocalidadesC(r.estado === "ok" ? { estado: "ok", datos: r.datos } : { estado: "error" });
    });
  }

  // biome-ignore lint/correctness/useExhaustiveDependencies: sólo al montar (provincias) y cuando cambia el valor inicial (completar el edificio viejo con un trío ya guardado) — nunca por cambios de provinciaId/departamentoId que el usuario ya dispara con los `onChange` de abajo.
  useEffect(() => {
    cargarProvincias();
    if (valorInicial) {
      cargarDepartamentos(valorInicial.provinciaId);
      cargarLocalidades(valorInicial.departamentoId);
    }
  }, [valorInicial]);

  return (
    <>
      <CampoDeLista
        nombre="provincia_id"
        error={provinciasC.estado === "error" ? "No pudimos cargar las provincias." : undefined}
        etiqueta="Provincia"
        name="provincia_id"
        value={provinciaId}
        disabled={provinciasC.estado === "cargando"}
        onChange={(evento) => {
          const nueva = evento.target.value;
          setProvinciaId(nueva);
          setDepartamentoId("");
          setLocalidadId("");
          setLocalidadesC({ estado: "ok", datos: [] });
          cargarDepartamentos(nueva);
        }}
      >
        <option value="">Elegí una provincia</option>
        {provinciasC.estado === "ok"
          ? provinciasC.datos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre}
              </option>
            ))
          : null}
      </CampoDeLista>
      {provinciasC.estado === "cargando" ? <p className="campo__ayuda">Cargando…</p> : null}
      {provinciasC.estado === "error" ? (
        <button type="button" onClick={cargarProvincias}>
          Reintentar
        </button>
      ) : null}

      <CampoDeLista
        nombre="departamento_id"
        error={
          departamentosC.estado === "error" ? "No pudimos cargar los departamentos." : undefined
        }
        etiqueta="Departamento"
        name="departamento_id"
        value={departamentoId}
        disabled={!provinciaId || departamentosC.estado === "cargando"}
        onChange={(evento) => {
          const nuevo = evento.target.value;
          setDepartamentoId(nuevo);
          setLocalidadId("");
          cargarLocalidades(nuevo);
        }}
      >
        <option value="">Elegí un departamento</option>
        {departamentosC.estado === "ok"
          ? departamentosC.datos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nombre}
              </option>
            ))
          : null}
      </CampoDeLista>
      {departamentosC.estado === "cargando" ? <p className="campo__ayuda">Cargando…</p> : null}
      {departamentosC.estado === "error" ? (
        <button type="button" onClick={() => cargarDepartamentos(provinciaId)}>
          Reintentar
        </button>
      ) : null}

      <CampoDeLista
        nombre="localidad_id"
        error={localidadesC.estado === "error" ? "No pudimos cargar las localidades." : undefined}
        etiqueta="Localidad"
        name="localidad_id"
        value={localidadId}
        disabled={!departamentoId || localidadesC.estado === "cargando"}
        onChange={(evento) => setLocalidadId(evento.target.value)}
      >
        <option value="">Elegí una localidad</option>
        {localidadesC.estado === "ok"
          ? localidadesC.datos.map((l) => (
              <option key={l.id} value={l.id}>
                {l.nombre}
              </option>
            ))
          : null}
      </CampoDeLista>
      {localidadesC.estado === "cargando" ? <p className="campo__ayuda">Cargando…</p> : null}
      {localidadesC.estado === "error" ? (
        <button type="button" onClick={() => cargarLocalidades(departamentoId)}>
          Reintentar
        </button>
      ) : null}
    </>
  );
}
