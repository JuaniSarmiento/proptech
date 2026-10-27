import { describe, expect, it } from "vitest";
import categoriasFixture from "./fixtures/categorias.json";
import edificioFixture from "./fixtures/edificio.json";
import grupoFixture from "./fixtures/grupos.json";
import listaFixture from "./fixtures/lista.json";
import resumenFixture from "./fixtures/resumen.json";
import unidadesFixture from "./fixtures/unidades.json";
import versionesFixture from "./fixtures/versiones.json";
import vigenteFixture from "./fixtures/vigente.json";
import type {
  Categoria,
  ConfiguracionVigente,
  Edificio,
  EdificioDeLista,
  Grupo,
  Padron,
  Resumen,
  VersionDelHistorial,
} from "./tipos";

/**
 * D4 (tarea 3.4): cada asignación de abajo es el "rojo, dos" del lado de
 * la web — si `tipos.ts` le pide a una ruta un campo que su fixture ya no
 * tiene, `tsc` falla ACÁ, antes que cualquier pantalla lo note. No es un
 * `as`: es una asignación directa, para que TypeScript compare de verdad
 * el tipo inferido del JSON contra el tipo declarado.
 */
const _lista: EdificioDeLista[] = listaFixture;
const _edificio: Edificio = edificioFixture;
const _resumen: Resumen = resumenFixture;
const _padron: Padron = unidadesFixture;
const _grupos: Grupo[] = grupoFixture;
const _categorias: Categoria[] = categoriasFixture;
const _vigente: ConfiguracionVigente = vigenteFixture;
const _versiones: VersionDelHistorial[] = versionesFixture;

describe("los tipos de web/src/lib/api/tipos.ts coinciden con los fixtures del contrato", () => {
  it("lista: un edificio con id, nombre y localidad", () => {
    expect(_lista[0]).toMatchObject({ nombre: expect.any(String) });
  });

  it("edificio: tiene administracion_id", () => {
    expect(_edificio.administracion_id).toBeTypeOf("string");
  });

  it("resumen: pasos tiene las siete claves fijas (D3, tarea 3.8: + ubicacion)", () => {
    expect(Object.keys(_resumen.pasos).sort()).toEqual(
      [
        "categorias",
        "coeficientes",
        "grupos",
        "intereses_y_vencimiento",
        "saldos_previos",
        "ubicacion",
        "unidades",
      ].sort(),
    );
  });

  it("padrón: cada unidad tiene coeficiente y superficie como texto", () => {
    expect(_padron.unidades[0]?.coeficiente).toBeTypeOf("string");
  });

  it("grupos: Generales viene con es_generales y un informe", () => {
    const generales = _grupos.find((g) => g.es_generales);
    expect(generales?.informe).not.toBeNull();
  });

  it("categorías: tienen orden y activa", () => {
    expect(_categorias[0]).toMatchObject({
      orden: expect.any(Number),
      activa: expect.any(Boolean),
    });
  });

  it("vigente: puede ser null (sin versión vigente) o traer tasa_mensual", () => {
    expect(_vigente === null || typeof _vigente.tasa_mensual === "string").toBe(true);
  });

  it("versiones: cada una trae autor_nombre (D5, tarea 2.2)", () => {
    expect(_versiones[0]?.autor_nombre).toBeTypeOf("string");
  });
});
