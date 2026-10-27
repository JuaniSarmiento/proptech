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
  localidad: string | null;
};

export type Edificio = {
  id: string;
  administracion_id: string;
  nombre: string;
  localidad: string | null;
  provincia_id: string | null;
  departamento_id: string | null;
  localidad_id: string | null;
  calle_y_numero: string | null;
  pisos: number | null;
  subsuelos: number | null;
};

export type Resumen = {
  nombre: string;
  localidad: string | null;
  /** D3 (tarea 6.1): `null` es "sin completar" (edificio migrado), nunca
   * un dato inventado — ni acá ni en `Edificio`. */
  provincia_id: string | null;
  departamento_id: string | null;
  localidad_id: string | null;
  calle_y_numero: string | null;
  pisos: number | null;
  subsuelos: number | null;
  cantidad_unidades: number;
  unidades_sin_piso_completo: number;
  estado_migracion: string;
  informe: InformeDeCoeficientes;
  pasos: {
    ubicacion: PasoDePuestaAPunto;
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
  /** D3 (tarea 3.3, 6.2): `null` es "sin completar" (unidad migrada),
   * nunca un valor inventado. */
  piso: string | null;
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
  /** 6.3: un grupo parcial se desactiva, nunca se borra (R16 de grupos);
   * "Generales" es siempre `true` (la base lo rechaza por SQL). */
  activo: boolean;
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
