// Cliente de la API FastAPI. La UI NO tiene lógica de simulación (ADR-0009):
// solo envía configs y consume lo que devuelve el motor.

export type Modo = "sandbox" | "analogico";
export type EspecieId = "ecoli" | "dradiodurans" | "mburtonii";
export type EntornoId = "tierra" | "marte" | "encelado";
export type Patron = "uniforme" | "cluster";

export interface EspecieInfo {
  id: EspecieId;
  label: string;
  t_min: number;
  t_opt: number;
  t_max: number;
  a_w_min: number;
  uv_max: number;
  mu_opt: number;
}

// --- Editor de reglas por bloques (ADR-0018) ---
export type ResultadoId = "MUERTA" | "LATENTE" | "ACTIVA";
export type ProbId = null | "contacto" | "mu";

export type Condicion =
  | { tipo: "estado"; cual: string }
  | { tipo: "ambiente"; cual: string; valor: boolean }
  | { tipo: "vecinos"; cual: string; op: string; n: number };

export interface Clausula {
  cuando: Condicion[];
  entonces: ResultadoId;
  prob?: ProbId;
}
export interface ReglaSpec {
  nombre: string;
  clausulas: Clausula[];
}
export interface PresetRegla {
  id: string;
  nombre: string;
  spec: ReglaSpec | null;   // null = regla fija no editable por bloques (p. ej. las de latencia)
  notacion: string;
}
export interface OpcionVoc {
  id: string | number | boolean | null;
  label: string;
}
export interface Vocabulario {
  condiciones: { tipo: string; label: string; campos: Record<string, OpcionVoc[]> }[];
  resultados: OpcionVoc[];
  probabilidades: OpcionVoc[];
}

export interface Catalogo {
  especies: EspecieInfo[];
  entornos: { id: EntornoId; label: string }[];
  estados: { MUERTA: number; LATENTE: number; ACTIVA: number };
  limites: { lado: [number, number]; iter_max: number; mc_max: number };
  reglas: PresetRegla[];
  vocabulario: Vocabulario;
}

export interface ConfigCorrida {
  modo: Modo;
  especie: EspecieId;
  entorno: EntornoId;
  T: number;
  R: number;
  A_w: number;
  m: number;
  n: number;
  fraccion_activa: number;
  patron: Patron;
  semilla: number | null;
  n_iteraciones: number | null;
  salmuera: boolean;
  n_corridas: number;
  // Regla de transición: id de preset, spec de bloques inline, o null (logística).
  regla?: string | ReglaSpec | null;
}

export interface Frame {
  type: "frame";
  tick: number;
  shape: [number, number];
  grid: string; // base64 de int8
  n: { m: number; l: number; a: number };
}
export type Mensaje =
  | Frame
  | { type: "done"; ticks: number }
  | { type: "error"; detail: string };

export interface Montecarlo {
  n_corridas: number;
  media: number[][]; // (ticks+1, 3) columnas [MUERTA, LATENTE, ACTIVA]
  desviacion: number[][];
}

export async function fetchCatalogo(): Promise<Catalogo> {
  const r = await fetch("/api/config");
  if (!r.ok) throw new Error(`config: ${r.status}`);
  return r.json();
}

export async function fetchMontecarlo(cfg: ConfigCorrida): Promise<Montecarlo> {
  const r = await fetch("/api/montecarlo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
  if (!r.ok) throw new Error(`montecarlo: ${r.status}`);
  return r.json();
}

export interface ValidacionRegla {
  valida: boolean;
  notacion: string | null;
  error: string | null;
}

/** Valida un spec de bloques en el backend y devuelve su notación o el error. */
export async function fetchValidarRegla(spec: ReglaSpec): Promise<ValidacionRegla> {
  const r = await fetch("/api/regla/validar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(spec),
  });
  if (!r.ok) throw new Error(`validar: ${r.status}`);
  return r.json();
}

/** Decodifica el grid base64 (int8) a un Uint8Array de valores 0/1/2. */
export function decodeGrid(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
