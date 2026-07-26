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

export interface Catalogo {
  especies: EspecieInfo[];
  entornos: { id: EntornoId; label: string }[];
  estados: { MUERTA: number; LATENTE: number; ACTIVA: number };
  limites: { lado: [number, number]; iter_max: number; mc_max: number };
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

/** Decodifica el grid base64 (int8) a un Uint8Array de valores 0/1/2. */
export function decodeGrid(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
