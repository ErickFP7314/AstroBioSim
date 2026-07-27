import { useCallback, useEffect, useRef, useState } from "react";
import { correrSim } from "../api";
import type { ConfigCorrida, Frame } from "../api";

export type EstadoCorrida = "idle" | "cargando" | "listo" | "error";

/**
 * Corre la simulación en el motor (Pyodide, en el navegador del visitante),
 * bufferea todos los frames del run y después reproduce (play / pausa / paso /
 * velocidad) sobre ese buffer. La UI solo renderiza el frame en `indice`.
 */
export function useSimulation() {
  const [frames, setFrames] = useState<Frame[]>([]);
  const [indice, setIndice] = useState(0);
  const [reproduciendo, setReproduciendo] = useState(false);
  const [estado, setEstado] = useState<EstadoCorrida>("idle");
  const [error, setError] = useState<string | null>(null);
  const [fps, setFps] = useState(12);

  const framesRef = useRef<Frame[]>([]);
  const estadoRef = useRef<EstadoCorrida>("idle");
  useEffect(() => void (framesRef.current = frames), [frames]);
  useEffect(() => void (estadoRef.current = estado), [estado]);

  const correr = useCallback((cfg: ConfigCorrida) => {
    setFrames([]);
    framesRef.current = [];
    setIndice(0);
    setReproduciendo(false);
    setError(null);
    setEstado("cargando");
    correrSim(cfg)
      .then((fr) => {
        framesRef.current = fr;
        setFrames(fr);
        setIndice(0);
        setEstado("listo");
        setReproduciendo(true); // auto-play al terminar de calcular
      })
      .catch((e) => {
        setEstado("error");
        setError(e instanceof Error ? e.message : String(e));
      });
  }, []);

  // Bucle de reproducción: avanza el índice a `fps` mientras haya frames por delante.
  useEffect(() => {
    if (!reproduciendo) return;
    const id = window.setInterval(() => {
      setIndice((i) => {
        if (i >= framesRef.current.length - 1) {
          if (estadoRef.current === "listo") setReproduciendo(false);
          return i;
        }
        return i + 1;
      });
    }, 1000 / fps);
    return () => window.clearInterval(id);
  }, [reproduciendo, fps]);

  const alternar = useCallback(() => setReproduciendo((p) => !p), []);
  const pausar = useCallback(() => setReproduciendo(false), []);
  const reproducir = useCallback(() => setReproduciendo(true), []);
  const paso = useCallback((d: number) => {
    setReproduciendo(false);
    setIndice((i) => Math.max(0, Math.min(framesRef.current.length - 1, i + d)));
  }, []);
  const reset = useCallback(() => {
    setReproduciendo(false);
    setIndice(0);
  }, []);
  // Descarta la corrida por completo (vuelve al estado editable, sin frames).
  const limpiar = useCallback(() => {
    setFrames([]);
    framesRef.current = [];
    setIndice(0);
    setReproduciendo(false);
    setError(null);
    setEstado("idle");
  }, []);
  const irA = useCallback((i: number) => {
    setReproduciendo(false); // arrastrar la línea de tiempo pausa la reproducción
    setIndice(Math.max(0, Math.min(framesRef.current.length - 1, i)));
  }, []);

  const frameActual = frames[indice] ?? null;
  return {
    frames,
    frameActual,
    indice,
    total: frames.length,
    reproduciendo,
    estado,
    error,
    fps,
    setFps,
    correr,
    alternar,
    pausar,
    reproducir,
    paso,
    reset,
    limpiar,
    irA,
  };
}
