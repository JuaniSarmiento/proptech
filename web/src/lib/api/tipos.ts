/**
 * Tipos de las ocho rutas de lectura que usa la web (D4, tarea 3.4): la
 * FORMA real de la API, nunca inventada — `tipos.test.ts` asigna cada
 * fixture (generado por `tests/integracion/test_contrato_web.py` contra
 * la API real) a su tipo acá, y si este archivo le pide un campo que el
 * fixture no tiene, falla `tsc` antes que cualquier pantalla.
 */

/**
 * A propósito `string`, no un literal union ("hecho"/"falta",
 * "ok"/"advertencia"/"fuera_de_tolerancia"...): un fixture importado como
 * JSON infiere `string` para esos campos, y angostarlos acá exigiría un
 * `as` en `tipos.test.ts` que volvería a tapar justo lo que esta guarda
 * tiene que destapar (un campo que el fixture ya no tiene). La pantalla
 * que necesite el literal lo angosta ella misma al leerlo (4.x).
 */
export type PasoDePuestaAPunto = string;

export type InformeDeCoeficientes = {
  suma: string;
  diferencia: string;
  estado: string;
};

export type EdificioDeLista = {
  id: string;
  nombre: string;
  localidad: string;
};

export type Edificio = {
  id: string;
  administracion_id: string;
  nombre: string;
  localidad: string;
};

export type Resumen = {
  nombre: string;
  localidad: string;
  cantidad_unidades: number;
  estado_migracion: string;
  informe: InformeDeCoeficientes;
  pasos: {
    unidades: PasoDePuestaAPunto;
    coeficientes: PasoDePuestaAPunto;
    grupos: PasoDePuestaAPunto;
    categorias: PasoDePuestaAPunto;
    intereses_y_vencimiento: PasoDePuestaAPunto;
    saldos_previos: PasoDePuestaAPunto;
  };
  listo_para_liquidar: boolean;
};

export type Unidad = {
  id: string;
  complejo_id: string;
  identificador: string;
  tipo: string;
  piso: string;
  coeficiente: string;
  superficie_m2: string;
};

export type Padron = {
  unidades: Unidad[];
  informe: InformeDeCoeficientes;
};

export type MiembroDeGrupo = {
  unidad_id: string;
  coeficiente: string | null;
};

export type Grupo = {
  id: string;
  administracion_id: string;
  complejo_id: string;
  clave: string;
  nombre: string;
  metodo: string;
  es_generales: boolean;
  modo_de_coeficientes: string;
  informe: InformeDeCoeficientes | null;
  unidades: MiembroDeGrupo[];
};

export type Categoria = {
  id: string;
  complejo_id: string;
  clave: string;
  nombre: string;
  orden: number;
  activa: boolean;
};

export type VersionDeConfiguracion = {
  umbral_saldo_chico: string;
  id: string;
  complejo_id: string;
  vigente_desde: string;
  tasa_mensual: string;
  dias_de_gracia: number;
  forma_de_calculo: string;
  porcentaje_fondo: string;
  dia_de_vencimiento: number;
  modalidad_de_vencimiento: string;
  dia_segundo_vencimiento: number | null;
  recargo_segundo_vencimiento: string | null;
  autor_id: string;
  creada_en: string;
};

export type ConfiguracionVigente = VersionDeConfiguracion | null;

export type VersionDelHistorial = VersionDeConfiguracion & { autor_nombre: string };
