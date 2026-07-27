// Runtime (hilo principal): envuelve el Web Worker de Pyodide y expone una API
// con Promesas, para que el resto de la UI no sepa que corre Python en WASM.
import type { Catalogo, ConfigCorrida, Frame, Montecarlo, ReglaSpec, ValidacionRegla } from "../api";

type Pendiente = { resolve: (v: unknown) => void; reject: (e: Error) => void };

let worker: Worker | null = null;
let readyPromise: Promise<void> | null = null;
let resolverReady: (() => void) | null = null;
let rechazarReady: ((e: Error) => void) | null = null;
let nextId = 1;
const pendientes = new Map<number, Pendiente>();
let onProgress: (msg: string) => void = () => {};

function crearWorker(): Worker {
  // Worker CLÁSICO (sin type:"module") para poder usar importScripts y cargar
  // Pyodide de la forma estándar/robusta.
  const w = new Worker(new URL("./worker.ts", import.meta.url));
  w.onmessage = (e: MessageEvent) => {
    const m = e.data;
    if (m.type === "progress") return onProgress(m.msg);
    if (m.type === "ready") return resolverReady?.();
    if (m.id == null) return;
    const p = pendientes.get(m.id);
    if (!p) return;
    pendientes.delete(m.id);
    if (m.type === "result") p.resolve(m.data);
    else if (m.type === "error") p.reject(new Error(m.detail));
  };
  w.onerror = (e) => rechazarReady?.(new Error(e.message || "fallo al cargar el motor"));
  return w;
}

/** Inicializa Pyodide en el worker. Idempotente. `progreso` recibe mensajes de carga. */
export function initRuntime(progreso: (msg: string) => void): Promise<void> {
  onProgress = progreso;
  if (readyPromise) return readyPromise;
  worker = crearWorker();
  readyPromise = new Promise<void>((res, rej) => {
    resolverReady = res;
    rechazarReady = rej;
  });
  const baseUrl = new URL(import.meta.env.BASE_URL, location.href).href;
  worker.postMessage({ type: "init", baseUrl });
  return readyPromise;
}

function llamar<T>(type: string, payload: Record<string, unknown>): Promise<T> {
  if (!worker) return Promise.reject(new Error("runtime no inicializado"));
  const id = nextId++;
  return new Promise<T>((resolve, reject) => {
    pendientes.set(id, { resolve: resolve as (v: unknown) => void, reject });
    worker!.postMessage({ type, id, ...payload });
  });
}

export const runtime = {
  catalogo: () => llamar<Catalogo>("catalogo", {}),
  correr: (cfg: ConfigCorrida) => llamar<Frame[]>("correr", { cfg }),
  montecarlo: (cfg: ConfigCorrida) => llamar<Montecarlo>("montecarlo", { cfg }),
  validarRegla: (spec: ReglaSpec) => llamar<ValidacionRegla>("validar", { spec }),
};
