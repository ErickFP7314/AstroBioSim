import type { Modo } from "../api";
import type { EstadoCorrida } from "../hooks/useSimulation";

const ESTADO_TXT: Record<EstadoCorrida, string> = {
  idle: "en espera",
  cargando: "corriendo",
  listo: "lista",
  error: "error",
};

export function TopBar({
  modo, setModo, estado, tick, total, semilla,
}: {
  modo: Modo;
  setModo: (m: Modo) => void;
  estado: EstadoCorrida;
  tick: number;
  total: number;
  semilla: number | null;
}) {
  return (
    <header className="topbar">
      <div className="brand">Astro<span className="dotb">Bio</span>Sim</div>
      <div className="seg" role="tablist" aria-label="Modo de simulación">
        <button role="tab" aria-selected={modo === "sandbox"}
          className={modo === "sandbox" ? "on" : ""} onClick={() => setModo("sandbox")}>Sandbox</button>
        <button role="tab" aria-selected={modo === "analogico"}
          className={modo === "analogico" ? "on" : ""} onClick={() => setModo("analogico")}>Analógico</button>
      </div>
      <div className="status">
        <span>tick <b>{tick}</b>/{total > 0 ? total - 1 : 0}</span>
        <span>seed <b>{semilla ?? "—"}</b></span>
        <span className={"dot est-" + estado}>● {ESTADO_TXT[estado]}</span>
      </div>
    </header>
  );
}
