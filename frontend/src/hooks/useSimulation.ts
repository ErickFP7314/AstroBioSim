import { useCallback, useEffect, useRef, useState } from "react";
import type { ConfigCorrida, Frame, Mensaje } from "../api";

export type EstadoCorrida = "idle" | "cargando" | "listo" | "error";

/**
 * Abre el WebSocket `/api/stream`, bufferea los frames que llegan y reproduce
 * la corrida (play / pausa / paso / velocidad) sobre ese buffer. La UI solo
 * renderiza el frame en `indice`; toda la simulación la hace el backend.
 */
export function useSimulation() {
  const [frames, setFrames] = useState<Frame[]>([]);
  const [indice, setIndice] = useState(0);
  const [reproduciendo, setReproduciendo] = useState(false);
  const [estado, setEstado] = useState<EstadoCorrida>("idle");
  const [error, setError] = useState<string | null>(null);
  const [fps, setFps] = useState(12);

  const wsRef = useRef<WebSocket | null>(null);
  const framesRef = useRef<Frame[]>([]);
  const estadoRef = useRef<EstadoCorrida>("idle");
  useEffect(() => void (framesRef.current = frames), [frames]);
  useEffect(() => void (estadoRef.current = estado), [estado]);

  const correr = useCallback((cfg: ConfigCorrida) => {
    wsRef.current?.close();
    setFrames([]);
    framesRef.current = [];
    setIndice(0);
    setReproduciendo(false);
    setError(null);
    setEstado("cargando");

    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/api/stream`);
    wsRef.current = ws;
    ws.onopen = () => ws.send(JSON.stringify(cfg));
    ws.onmessage = (ev) => {
      const msg: Mensaje = JSON.parse(ev.data);
      if (msg.type === "frame") {
        setFrames((f) => [...f, msg]);
        if (framesRef.current.length === 0) setReproduciendo(true); // auto-play
      } else if (msg.type === "done") {
        setEstado("listo");
      } else if (msg.type === "error") {
        setEstado("error");
        setError(msg.detail);
      }
    };
    ws.onerror = () => {
      setEstado("error");
      setError("no se pudo conectar con el backend (¿uvicorn corriendo en :8000?)");
    };
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

  useEffect(() => () => wsRef.current?.close(), []);

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
    wsRef.current?.close();
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
