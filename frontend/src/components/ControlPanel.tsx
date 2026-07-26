import type { Catalogo, ConfigCorrida, EntornoId, EspecieId } from "../api";
import { ESTADO_COLOR } from "../theme";

interface Props {
  catalogo: Catalogo;
  cfg: ConfigCorrida;
  update: (patch: Partial<ConfigCorrida>) => void;
  onCorrer: () => void;
  cargando: boolean;
  // reproducción
  reproduciendo: boolean;
  hayFrames: boolean;
  alternar: () => void;
  paso: (d: number) => void;
  reset: () => void;
  fps: number;
  setFps: (n: number) => void;
}

const DOT: Record<EspecieId, string> = {
  ecoli: ESTADO_COLOR[2],
  dradiodurans: ESTADO_COLOR[1],
  mburtonii: "#a78bfa",
};

function Slider(props: {
  label: string; unidad: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void; fmt?: (v: number) => string;
}) {
  const { label, unidad, value, min, max, step, onChange, fmt } = props;
  return (
    <label className="sld">
      <div className="row">
        <span>{label}</span>
        <var>{(fmt ? fmt(value) : value.toString())} {unidad}</var>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

export function ControlPanel(p: Props) {
  const { catalogo, cfg, update } = p;
  const esAnalogico = cfg.modo === "analogico";

  return (
    <aside className="ctrl">
      <div>
        <p className="lbl">Especie</p>
        {catalogo.especies.map((e) => (
          <button key={e.id} className={"opt" + (cfg.especie === e.id ? " on" : "")}
            onClick={() => update({ especie: e.id })}>
            <span className="sw" style={{ background: DOT[e.id] }} />
            <span className="nm"><i>{e.label}</i></span>
          </button>
        ))}
      </div>

      {esAnalogico ? (
        <div>
          <p className="lbl">Entorno · datos 2025</p>
          <div className="chips">
            {catalogo.entornos.map((en) => (
              <button key={en.id} className={"chip" + (cfg.entorno === en.id ? " on" : "")}
                onClick={() => update({ entorno: en.id as EntornoId })}>{en.label}</button>
            ))}
          </div>
          {cfg.entorno === "marte" && (
            <label className="toggle">
              <input type="checkbox" checked={cfg.salmuera}
                onChange={(e) => update({ salmuera: e.target.checked })} />
              <span>Salmueras delicuescentes (microrefugios)</span>
            </label>
          )}
        </div>
      ) : (
        <div>
          <p className="lbl">Campo (Sandbox)</p>
          <Slider label="Temperatura" unidad="°C" value={cfg.T} min={-30} max={60} step={0.5}
            onChange={(v) => update({ T: v })} fmt={(v) => v.toFixed(1)} />
          <Slider label="UV" unidad="W/m²" value={cfg.R} min={0} max={60} step={0.5}
            onChange={(v) => update({ R: v })} fmt={(v) => v.toFixed(1)} />
          <Slider label="Actividad de agua" unidad="" value={cfg.A_w} min={0} max={1} step={0.01}
            onChange={(v) => update({ A_w: v })} fmt={(v) => v.toFixed(2)} />
        </div>
      )}

      <div>
        <p className="lbl">Grilla e inicio</p>
        <Slider label="Lado" unidad="celdas" value={cfg.m} min={catalogo.limites.lado[0]}
          max={catalogo.limites.lado[1]} step={2}
          onChange={(v) => update({ m: v, n: v })} fmt={(v) => `${v}×${v}`} />
        <Slider label="Siembra inicial" unidad="" value={cfg.fraccion_activa} min={0.02} max={0.6}
          step={0.01} onChange={(v) => update({ fraccion_activa: v })}
          fmt={(v) => `${Math.round(v * 100)}%`} />
        <label className="seed">
          <span className="lbl" style={{ margin: 0 }}>Semilla</span>
          <input type="number" value={cfg.semilla ?? 0}
            onChange={(e) => update({ semilla: Number(e.target.value) })} />
        </label>
      </div>

      <div className="run-block">
        <button className="run" onClick={p.onCorrer} disabled={p.cargando}>
          {p.cargando ? "Corriendo…" : "▶ Correr simulación"}
        </button>
        <p className="lbl">Reproducción</p>
        <div className="play">
          <button className="b" onClick={() => p.paso(-1)} disabled={!p.hayFrames} aria-label="Atrás">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h2v14H6zM18 5v14l-8-7z" /></svg>
          </button>
          <button className="b pri" onClick={p.alternar} disabled={!p.hayFrames}
            aria-label={p.reproduciendo ? "Pausar" : "Reproducir"}>
            {p.reproduciendo
              ? <svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h4v14H6zM14 5h4v14h-4z" /></svg>
              : <svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>}
          </button>
          <button className="b" onClick={() => p.paso(1)} disabled={!p.hayFrames} aria-label="Adelante">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M16 5h2v14h-2zM6 5v14l8-7z" /></svg>
          </button>
          <button className="b" onClick={p.reset} disabled={!p.hayFrames} aria-label="Reiniciar">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 5V2L7 6l5 4V7a5 5 0 1 1-5 5H5a7 7 0 1 0 7-7z" /></svg>
          </button>
        </div>
        <Slider label="Velocidad" unidad="fps" value={p.fps} min={1} max={30} step={1}
          onChange={p.setFps} />
      </div>
    </aside>
  );
}
