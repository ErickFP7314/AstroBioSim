import { useCallback, useEffect, useState } from "react";
import {
  fetchCatalogo,
  fetchMontecarlo,
  type Catalogo,
  type ConfigCorrida,
  type Modo,
  type Montecarlo,
  type PresetRegla,
  type ReglaSpec,
} from "./api";
import { ESTADOS } from "./theme";
import { useSimulation } from "./hooks/useSimulation";
import { TopBar } from "./components/TopBar";
import { ControlPanel } from "./components/ControlPanel";
import { AutomatonGrid } from "./components/AutomatonGrid";
import { PopulationChart } from "./components/PopulationChart";
import { RuleEditor } from "./components/RuleEditor";

const CFG_INICIAL: ConfigCorrida = {
  modo: "sandbox", especie: "dradiodurans", entorno: "marte",
  T: 20, R: 0, A_w: 0.9, m: 60, n: 60,
  fraccion_activa: 0.15, patron: "uniforme", semilla: 42,
  n_iteraciones: 200, salmuera: true, n_corridas: 30, regla: "logistica",
};

/** Devuelve el spec editable de la regla actual (resuelve preset id → spec). */
function specDeRegla(regla: ConfigCorrida["regla"], reglas: PresetRegla[]): ReglaSpec {
  if (regla && typeof regla === "object") return regla;
  const id = typeof regla === "string" ? regla : "logistica";
  return (reglas.find((r) => r.id === id) ?? reglas[0]).spec;
}

export default function App() {
  const [catalogo, setCatalogo] = useState<Catalogo | null>(null);
  const [errCat, setErrCat] = useState<string | null>(null);
  const [cfg, setCfg] = useState<ConfigCorrida>(CFG_INICIAL);
  const [mc, setMc] = useState<Montecarlo | null>(null);
  const [mcCargando, setMcCargando] = useState(false);
  const [editorRegla, setEditorRegla] = useState(false);
  const sim = useSimulation();

  useEffect(() => {
    fetchCatalogo().then(setCatalogo).catch((e) => setErrCat(String(e)));
  }, []);

  const update = useCallback((patch: Partial<ConfigCorrida>) => {
    setCfg((c) => ({ ...c, ...patch }));
    setMc(null); // la banda deja de corresponder al cambiar la config
  }, []);

  const correr = useCallback(() => sim.correr(cfg), [sim, cfg]);
  const calcularMc = useCallback(() => {
    setMcCargando(true);
    fetchMontecarlo(cfg).then(setMc).catch(() => setMc(null)).finally(() => setMcCargando(false));
  }, [cfg]);

  if (errCat) return <div className="fatal">No se pudo cargar la config: {errCat}<br /><small>¿Está corriendo <code>uvicorn astrobiosim.ui.api:app</code>?</small></div>;
  if (!catalogo) return <div className="fatal">Cargando…</div>;

  const n = sim.frameActual?.n ?? null;
  const tot = n ? n.m + n.l + n.a : 0;
  const frac = (x: number) => (tot ? ((x / tot) * 100).toFixed(1) + " %" : "—");

  return (
    <div className="app">
      <TopBar
        modo={cfg.modo}
        setModo={(m: Modo) => update({ modo: m })}
        estado={sim.estado}
        tick={sim.indice}
        total={sim.total}
        semilla={cfg.semilla}
      />
      <div className="body">
        <ControlPanel
          catalogo={catalogo}
          cfg={cfg}
          update={update}
          onCorrer={correr}
          cargando={sim.estado === "cargando"}
          reproduciendo={sim.reproduciendo}
          hayFrames={sim.total > 0}
          alternar={sim.alternar}
          paso={sim.paso}
          reset={sim.reset}
          fps={sim.fps}
          setFps={sim.setFps}
          onEditarRegla={() => setEditorRegla(true)}
        />

        <AutomatonGrid frame={sim.frameActual} />

        <aside className="panel">
          <div className="card">
            <div className="card-head">
              <p className="ttl">Dinámica poblacional</p>
              <button className="mini" onClick={calcularMc} disabled={mcCargando}>
                {mcCargando ? "…" : mc ? `± σ · N=${mc.n_corridas}` : "Banda Montecarlo"}
              </button>
            </div>
            <PopulationChart frames={sim.frames} indice={sim.indice} montecarlo={mc} />
          </div>
          <div className="card">
            <p className="ttl">Estado actual</p>
            <div className="readout">
              {ESTADOS.map((e) => (
                <div className="r" key={e.valor}>
                  <span className="k"><b style={{ background: e.color }} />{e.nombre}</span>
                  <span className="v">{frac(e.valor === 2 ? n?.a ?? 0 : e.valor === 1 ? n?.l ?? 0 : n?.m ?? 0)}</span>
                </div>
              ))}
            </div>
          </div>
          {sim.error && <div className="card err">{sim.error}</div>}
        </aside>
      </div>

      {editorRegla && (
        <RuleEditor
          vocabulario={catalogo.vocabulario}
          presets={catalogo.reglas}
          specInicial={specDeRegla(cfg.regla, catalogo.reglas)}
          onUsar={(spec) => { update({ regla: spec }); setEditorRegla(false); }}
          onCerrar={() => setEditorRegla(false)}
        />
      )}
    </div>
  );
}
