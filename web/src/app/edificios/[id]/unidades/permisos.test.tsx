/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it } from "vitest";
import { SesionDePantalla, type SesionVisible } from "../../../../componentes/SesionDePantalla";
import { PantallaConfiguracion } from "../configuracion/Pantalla";
import { PantallaSaldosPrevios } from "../saldos-previos/Pantalla";
import { PantallaPadron } from "./Pantalla";

afterEach(cleanup);
const accion = async () => null;
function sesion(acciones: string[], edificio = "1", administracion: string[] = []): SesionVisible {
  return {
    administracionId: "a",
    datos: {
      persona: { nombre: "Prueba" },
      administraciones: [
        {
          id: "a",
          nombre: "A",
          acciones: {
            administracion,
            todos_los_edificios: [],
            por_edificio: { [edificio]: acciones },
          },
        },
      ],
    },
  };
}
const padron = (
  <PantallaPadron
    id="1"
    nombreEdificio="Edificio"
    pisosDelEdificio={4}
    subsuelosDelEdificio={1}
    unidades={[
      {
        id: "u1",
        complejo_id: "1",
        identificador: "1A",
        tipo: "departamento",
        piso: "1",
        coeficiente: "1.000000",
        superficie_m2: "60.00",
      },
    ]}
    informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
    accionCrear={accion}
    accionEditar={accion}
    vecinosPorUnidad={new Map()}
  />
);

it.each([null, sesion(["ver_configuracion_del_edificio"]), sesion(["configurar_padron"], "otro")])(
  "R2D-R1: lectura conserva unidad sin controles de editar ni guardar (%j)",
  async (valor) => {
    render(<SesionDePantalla value={valor}>{padron}</SesionDePantalla>);
    expect(screen.getByText("1A")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "1A" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Guardar" })).toBeNull();
    expect(screen.queryByLabelText("Identificador")).toBeNull();
  },
);
it("R2D-R1: configurar padrón conserva edición y guardar", async () => {
  render(<SesionDePantalla value={sesion(["configurar_padron"])}>{padron}</SesionDePantalla>);
  await userEvent.setup().click(screen.getByRole("button", { name: "1A" }));
  expect(screen.getByRole("button", { name: "Guardar" })).toBeTruthy();
});
it.each([
  null,
  sesion(["ver_configuracion_del_edificio"]),
  sesion(["crear_version_de_configuracion"], "otro"),
])("R2D-R1: sin permiso de versión conserva lectura sin Cambiar configuración (%j)", (valor) => {
  render(
    <SesionDePantalla value={valor}>
      <PantallaConfiguracion
        id="1"
        nombreEdificio="Edificio"
        vigente={null}
        historial={[]}
        accionCrear={accion}
      />
    </SesionDePantalla>,
  );
  expect(screen.getByRole("region", { name: "Configuración vigente" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Cambiar configuración" })).toBeNull();
});
it("R2D-R1: permiso de versión permite cambiar y guardar", async () => {
  render(
    <SesionDePantalla value={sesion(["crear_version_de_configuracion"])}>
      <PantallaConfiguracion
        id="1"
        nombreEdificio="Edificio"
        vigente={null}
        historial={[]}
        accionCrear={accion}
      />
    </SesionDePantalla>,
  );
  await userEvent.setup().click(screen.getByRole("button", { name: "Cambiar configuración" }));
  expect(screen.getByRole("button", { name: "Guardar" })).toBeTruthy();
});
it.each([
  null,
  sesion(["ver_configuracion_del_edificio"]),
  sesion(["confirmar_sin_saldos_previos"], "otro"),
])("R2D-R1: pendiente sin permiso no ofrece confirmar ni casilla (%j)", (valor) => {
  render(
    <SesionDePantalla value={valor}>
      <PantallaSaldosPrevios
        id="1"
        nombreEdificio="Edificio"
        estadoMigracion="pendiente"
        accionConfirmar={accion}
      />
    </SesionDePantalla>,
  );
  expect(screen.queryByRole("button", { name: "Confirmar" })).toBeNull();
  expect(screen.queryByRole("checkbox")).toBeNull();
});
it("R2D-R1: permiso de saldos conserva casilla y confirmar", async () => {
  render(
    <SesionDePantalla value={sesion(["confirmar_sin_saldos_previos"])}>
      <PantallaSaldosPrevios
        id="1"
        nombreEdificio="Edificio"
        estadoMigracion="pendiente"
        accionConfirmar={accion}
      />
    </SesionDePantalla>,
  );
  await userEvent.setup().click(screen.getByRole("checkbox"));
  expect(screen.getByRole("button", { name: "Confirmar" })).toHaveProperty("disabled", false);
});
it("R2D-R2: GET personal exitoso no habilita Agregar vecino al principal", async () => {
  const valor = sesion(["configurar_padron"], "1", ["ver_personal"]);
  render(<SesionDePantalla value={valor}>{padron}</SesionDePantalla>);
  await userEvent.setup().click(screen.getByRole("button", { name: "1A" }));
  expect(screen.queryByRole("button", { name: "Agregar vecino" })).toBeNull();
  expect(screen.queryByRole("form", { name: "Agregar vecino" })).toBeNull();
});
it("R2D-R2: invitar habilita Agregar vecino", async () => {
  const valor = sesion(["configurar_padron"], "1", [
    "ver_personal",
    "invitar_usuarios_y_asignar_edificios",
  ]);
  render(<SesionDePantalla value={valor}>{padron}</SesionDePantalla>);
  await userEvent.setup().click(screen.getByRole("button", { name: "1A" }));
  expect(screen.getByRole("button", { name: "Agregar vecino" })).toBeTruthy();
});

it("R2D-R1: aun con permiso de invitar no monta editar ni guardar sin configurar padrón", async () => {
  render(
    <SesionDePantalla value={sesion([], "1", ["invitar_usuarios_y_asignar_edificios"])}>
      {padron}
    </SesionDePantalla>,
  );
  await userEvent.setup().click(screen.getByRole("button", { name: "1A" }));
  expect(screen.getByRole("button", { name: "Agregar vecino" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Guardar" })).toBeNull();
  expect(screen.queryByLabelText("Identificador")).toBeNull();
});
