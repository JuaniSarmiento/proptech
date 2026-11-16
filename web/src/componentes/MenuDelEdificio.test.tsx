/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { sinViolaciones } from "../lib/test/accesibilidad";
import { Ayuda } from "./Ayuda";
import { MenuDelEdificio, type SeccionDelEdificio } from "./MenuDelEdificio";
import { SesionDePantalla, type SesionVisible } from "./SesionDePantalla";

afterEach(cleanup);

const secciones: SeccionDelEdificio[] = [
  {
    clave: "resumen",
    etiqueta: "Resumen",
    href: "/edificios/1",
    grupo: "El edificio",
    icono: "resumen",
  },
  {
    clave: "unidades",
    etiqueta: "Unidades",
    href: "/edificios/1/unidades",
    grupo: "El edificio",
    icono: "unidades",
  },
  {
    clave: "categorias",
    etiqueta: "Categorías",
    href: "/edificios/1/categorias",
    grupo: "Configuración",
    icono: "categorias",
  },
];

describe("MenuDelEdificio", () => {
  it("marca la sección actual con aria-current y no sólo con color (Sección actual)", () => {
    render(<MenuDelEdificio seccionActual="unidades" secciones={secciones} />);
    const actual = screen.getByRole("link", { name: /Unidades/ });
    expect(actual.getAttribute("aria-current")).toBe("page");
    const otra = screen.getByRole("link", { name: /Resumen/ });
    expect(otra.getAttribute("aria-current")).toBeNull();
    // marca de FORMA, no sólo color: el texto visible del enlace actual trae
    // un indicador de forma además de su etiqueta.
    expect(actual.textContent).toMatch(/[▸›]/);
  });

  it('despliega "Secciones" con el teclado, se recorre con Tab y se cierra con Esc (Menú plegado)', async () => {
    const usuario = userEvent.setup();
    render(<MenuDelEdificio seccionActual="resumen" secciones={secciones} />);
    const boton = screen.getByRole("button", { name: "Secciones" });
    expect(boton.getAttribute("aria-expanded")).toBe("false");

    boton.focus();
    await usuario.keyboard("{Enter}");
    expect(boton.getAttribute("aria-expanded")).toBe("true");
    const contenedor = document.getElementById(boton.getAttribute("aria-controls") ?? "");
    expect(contenedor?.getAttribute("data-abierto")).toBe("true");

    await usuario.keyboard("{Escape}");
    expect(boton.getAttribute("aria-expanded")).toBe("false");
    expect(contenedor?.getAttribute("data-abierto")).toBe("false");
    expect(document.activeElement).toBe(boton);
  });

  it("RF-F-1: un Escape cierra sólo el menú abierto encima de la ayuda en móvil", async () => {
    const usuario = userEvent.setup();
    // JSDOM no aplica media queries; 375px representa el menú plegado.
    const anchoAnterior = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 375 });
    try {
      render(
        <>
          <Ayuda paraQueSirve="Unidades" pasos={["Cargá una unidad"]} yDespues="Grupos" />
          <MenuDelEdificio seccionActual="resumen" secciones={secciones} />
        </>,
      );
      await usuario.click(screen.getByRole("button", { name: "Ayuda" }));
      const seccionesBoton = screen.getByRole("button", { name: "Secciones" });
      await usuario.click(seccionesBoton);
      await usuario.keyboard("{Escape}");
      expect(seccionesBoton.getAttribute("aria-expanded")).toBe("false");
      expect(document.activeElement).toBe(seccionesBoton);
      expect(
        screen.getByRole("region", { name: "Ayuda: para qué sirve esta pantalla" }),
      ).toBeTruthy();
      await usuario.keyboard("{Escape}");
      expect(screen.queryByRole("region")).toBeNull();
    } finally {
      Object.defineProperty(window, "innerWidth", { configurable: true, value: anchoAnterior });
    }
  });

  it("agrupa las secciones bajo su título, cada grupo como lista con nombre (enmienda 20/10)", () => {
    render(<MenuDelEdificio seccionActual="resumen" secciones={secciones} />);
    const edificio = screen.getByRole("list", { name: "El edificio" });
    const configuracion = screen.getByRole("list", { name: "Configuración" });
    expect(
      within(edificio)
        .getAllByRole("link")
        .map((a) => a.textContent),
    ).toEqual(["Resumen›", "Unidades"]);
    expect(within(configuracion).getByRole("link", { name: "Categorías" })).toBeTruthy();
  });

  it("cada sección lleva su ícono decorativo y el texto al lado, nunca sólo el ícono", () => {
    render(<MenuDelEdificio seccionActual="resumen" secciones={secciones} />);
    for (const enlace of screen.getAllByRole("link")) {
      const icono = enlace.querySelector("svg");
      expect(icono?.getAttribute("aria-hidden")).toBe("true");
      expect(enlace.textContent?.trim().length).toBeGreaterThan(0);
    }
  });

  it("sin violaciones de axe, abierto y cerrado", async () => {
    const usuario = userEvent.setup();
    const { container } = render(<MenuDelEdificio seccionActual="resumen" secciones={secciones} />);
    await sinViolaciones(container);
    await usuario.click(screen.getByRole("button", { name: "Secciones" }));
    await sinViolaciones(container);
  });
});

describe("MenuDelEdificio · secciones por permiso (H-017)", () => {
  const conLiquidaciones: SeccionDelEdificio[] = [
    ...secciones,
    {
      clave: "liquidaciones",
      etiqueta: "Liquidaciones",
      href: "/edificios/1/liquidaciones",
      grupo: "Liquidación",
      icono: "liquidaciones",
      accion: "ver_liquidaciones",
      complejoId: "1",
    },
  ];

  function sesionCon(porEdificio: Record<string, string[]>): SesionVisible {
    return {
      datos: {
        persona: { nombre: "Alguien" },
        administraciones: [
          {
            id: "a",
            nombre: "A",
            acciones: { administracion: [], todos_los_edificios: [], por_edificio: porEdificio },
          },
        ],
      },
      administracionId: "a",
    };
  }

  function pintar(sesion: SesionVisible | null) {
    render(
      <SesionDePantalla value={sesion}>
        <MenuDelEdificio seccionActual="resumen" secciones={conLiquidaciones} />
      </SesionDePantalla>,
    );
  }

  it("con el permiso en ese edificio, el link está", () => {
    pintar(sesionCon({ "1": ["ver_liquidaciones"] }));
    expect(screen.getByRole("link", { name: "Liquidaciones" }).getAttribute("href")).toBe(
      "/edificios/1/liquidaciones",
    );
  });

  it("sin el permiso, o con el de otro edificio, o sin sesión, no está", () => {
    for (const sesion of [sesionCon({}), sesionCon({ "2": ["ver_liquidaciones"] }), null]) {
      cleanup();
      pintar(sesion);
      expect(screen.queryByRole("link", { name: "Liquidaciones" })).toBeNull();
      expect(screen.getByRole("link", { name: /Resumen/ })).toBeTruthy();
    }
  });

  it("sin el link no queda el título vacío del grupo", () => {
    pintar(sesionCon({}));
    expect(screen.queryByText("Liquidación")).toBeNull();
  });
});
