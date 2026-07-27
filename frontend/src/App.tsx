import { useCallback, useEffect, useState } from "react";
import {
  fetchCatalogo,
  fetchMontecarlo,
  fetchValidarRegla,
  initRuntime,
  type Catalogo,
  type ConfigCorrida,
  type Modo,
  type Montecarlo,
  type PresetRegla,
  type ReglaSpec,
} from "./api";
import { ESTADO_COLOR, ESTADOS } from "./theme";
import { useSimulation } from "./hooks/useSimulation";
import { TopBar } from "./components/TopBar";
import { ControlPanel } from "./components/ControlPanel";
import { AutomatonGrid } from "./components/AutomatonGrid";
import { PopulationChart } from "./components/PopulationChart";
import { RuleEditor } from "./components/RuleEditor";
import { Notacion } from "./components/Notacion";

const CFG_INICIAL: ConfigCorrida = {
  modo: "sandbox", especie: "dradiodurans", entorno: "marte",
  T: 20, R: 0, A_w: 0.9, m: 60, n: 60,
  fraccion_activa: 0.15, patron: "uniforme", semilla: 42,
  n_iteraciones: 200, salmuera: true, n_corridas: 30, regla: "latencia_anhidro",
};

/** Spec editable con el que arrancar el editor de bloques. Si la regla actual es
 *  una fija no editable (spec null, p. ej. las de latencia), cae en la primera
 *  regla que sí tiene bloques (logística) como punto de partida. */
function specDeRegla(regla: ConfigCorrida["regla"], reglas: PresetRegla[]): ReglaSpec {
  if (regla && typeof regla === "object") return regla;
  const editables = reglas.filter((r): r is PresetRegla & { spec: ReglaSpec } => r.spec != null);
  const id = typeof regla === "string" ? regla : "logistica";
  return (editables.find((r) => r.id === id) ?? editables[0]).spec;
}

export default function App() {
  const [catalogo, setCatalogo] = useState<Catalogo | null>(null);
  const [errCat, setErrCat] = useState<string | null>(null);
  const [cfg, setCfg] = useState<ConfigCorrida>(CFG_INICIAL);
  const [mc, setMc] = useState<Montecarlo | null>(null);
  const [mcCargando, setMcCargando] = useState(false);
  const [editorRegla, setEditorRegla] = useState(false);
  const [notacion, setNotacion] = useState<string | null>(null);
  // Colores de los tres estados, editables por el usuario (color picker). Se
  // reflejan en vivo en la grilla, la leyenda y el gráfico.
  const [colores, setColores] = useState<Record<number, string>>(() => ({ ...ESTADO_COLOR }));
  const [mostrarBanda, setMostrarBanda] = useState(true);
  // Paneles redimensionables/colapsables (bug 4/5). Ancho en px + estado abierto.
  const [wCtrl, setWCtrl] = useState(264);
  const [wPanel, setWPanel] = useState(336);
  const [ctrlOpen, setCtrlOpen] = useState(true);
  const [panelOpen, setPanelOpen] = useState(true);
  // Modal "para editar hay que reiniciar": aparece si se toca un campo bloqueado
  // mientras hay una corrida cargada.
  const [modalEditar, setModalEditar] = useState(false);
  const [progresoMotor, setProgresoMotor] = useState("iniciando…");
  const sim = useSimulation();

  // Arranca Pyodide (el motor Python corre en el navegador) y recién ahí pide el
  // catálogo. `initRuntime` reporta el progreso de carga.
  useEffect(() => {
    initRuntime(setProgresoMotor)
      .then(() => fetchCatalogo())
      .then(setCatalogo)
      .catch((e) => setErrCat(String(e)));
  }, []);

  // Notación de la regla activa: si es un preset, sale del catálogo; si es un
  // spec de bloques, la pide al backend (única fuente de la notación).
  useEffect(() => {
    if (!catalogo) return;
    const r = cfg.regla;
    if (r && typeof r === "object") {
      let vivo = true;
      fetchValidarRegla(r).then((v) => vivo && setNotacion(v.notacion)).catch(() => vivo && setNotacion(null));
      return () => { vivo = false; };
    }
    const id = typeof r === "string" ? r : "logistica";
    setNotacion(catalogo.reglas.find((x) => x.id === id)?.notacion ?? null);
  }, [cfg.regla, catalogo]);

  const update = useCallback((patch: Partial<ConfigCorrida>) => {
    setCfg((c) => ({ ...c, ...patch }));
    setMc(null); // la banda deja de corresponder al cambiar la config
  }, []);

  const correr = useCallback(() => sim.correr(cfg), [sim, cfg]);
  const calcularMc = useCallback(() => {
    setMcCargando(true);
    setMostrarBanda(true);
    fetchMontecarlo(cfg).then(setMc).catch(() => setMc(null)).finally(() => setMcCargando(false));
  }, [cfg]);

  // Redimensionar un panel arrastrando su borde. Al cruzar el umbral de colapso
  // (como un imán) el panel se oculta y aparece una flecha para volver a abrirlo.
  const iniciarResize = (lado: "ctrl" | "panel") => (e: React.PointerEvent) => {
    e.preventDefault();
    const x0 = e.clientX;
    const w0 = lado === "ctrl" ? wCtrl : wPanel;
    const MIN = 210, MAX = 480, COLAPSO = 150;
    function fin() {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", fin);
      document.body.classList.remove("resizing");
    }
    function onMove(ev: PointerEvent) {
      const dx = ev.clientX - x0;
      let w = lado === "ctrl" ? w0 + dx : w0 - dx;
      if (w < COLAPSO) {                         // cruzó el umbral → colapsa
        if (lado === "ctrl") setCtrlOpen(false); else setPanelOpen(false);
        fin();
        return;
      }
      w = Math.max(MIN, Math.min(MAX, w));
      if (lado === "ctrl") setWCtrl(w); else setWPanel(w);
    }
    document.body.classList.add("resizing");
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", fin);
  };

  // Bloqueo de edición durante una corrida (requests 3 y 4): con una corrida
  // cargada, tocar un campo pausa y ofrece reiniciar para poder editar.
  const bloqueado = sim.total > 0;
  const onIntentoEditar = useCallback(() => {
    sim.pausar();
    setModalEditar(true);
  }, [sim]);
  const onReiniciarEditar = useCallback(() => {
    sim.limpiar();       // descarta la corrida → los campos vuelven a ser editables
    setModalEditar(false);
  }, [sim]);
  const onCancelarEditar = useCallback(() => {
    setModalEditar(false);
    sim.reproducir();    // cancelar = seguir la simulación (play automático)
  }, [sim]);

  if (errCat) return (
    <div className="fatal">
      No se pudo cargar el motor: {errCat}
      <br /><small>Revisá la conexión y recargá. El motor se descarga de un CDN la primera vez.</small>
    </div>
  );
  if (!catalogo) return (
    <div className="fatal">
      <div className="motor-load">
        <div className="spinner" />
        <p>Cargando el motor de simulación…</p>
        <small className="motor-paso">{progresoMotor}</small>
        <small className="motor-nota">
          Corre 100 % en tu navegador (Pyodide/WASM). La primera vez descarga unos MB; después queda en caché.
        </small>
      </div>
    </div>
  );

  const n = sim.frameActual?.n ?? null;
  const tot = n ? n.m + n.l + n.a : 0;
  const frac = (x: number) => (tot ? ((x / tot) * 100).toFixed(1) + " %" : "—");
  const nombreReglaActiva = ((): string => {
    const r = cfg.regla;
    if (r && typeof r === "object") return r.nombre;
    const id = typeof r === "string" ? r : "logistica";
    return catalogo.reglas.find((x) => x.id === id)?.nombre ?? id;
  })();

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
      <div
        className="body"
        style={{ "--w-ctrl": `${wCtrl}px`, "--w-panel": `${wPanel}px` } as React.CSSProperties}
      >
        {ctrlOpen ? (
          <>
            <ControlPanel
              catalogo={catalogo}
              cfg={cfg}
              update={update}
              onCorrer={correr}
              cargando={sim.estado === "cargando"}
              reproduciendo={sim.reproduciendo}
              hayFrames={sim.total > 0}
              bloqueado={bloqueado}
              onIntentoEditar={onIntentoEditar}
              alternar={sim.alternar}
              paso={sim.paso}
              reset={sim.reset}
              fps={sim.fps}
              setFps={sim.setFps}
              onEditarRegla={() => setEditorRegla(true)}
            />
            <div className="rz" onPointerDown={iniciarResize("ctrl")}
              title="Arrastrá para redimensionar · soltá al mínimo para ocultar" />
          </>
        ) : (
          <button className="rz-tab rz-tab-l" onClick={() => setCtrlOpen(true)}
            title="Mostrar controles" aria-label="Mostrar panel de controles">▸</button>
        )}

        <AutomatonGrid frame={sim.frameActual} indice={sim.indice} total={sim.total} irA={sim.irA} colores={colores} />

        {panelOpen ? (
          <>
            <div className="rz" onPointerDown={iniciarResize("panel")}
              title="Arrastrá para redimensionar · soltá al mínimo para ocultar" />
            <aside className="panel">
              <div className="card">
                <div className="card-head">
                  <p className="ttl">Dinámica poblacional</p>
                  <button
                    className={"mini" + (mc && mostrarBanda ? " on" : "")}
                    onClick={mc ? () => setMostrarBanda((b) => !b) : calcularMc}
                    disabled={mcCargando}
                    title="Banda de incertidumbre Montecarlo: media ± σ de N réplicas, superpuesta al gráfico"
                  >
                    {mcCargando ? "calculando…"
                      : mc ? (mostrarBanda ? `ocultar ±σ · N=${mc.n_corridas}` : `ver ±σ · N=${mc.n_corridas}`)
                        : "Banda Montecarlo"}
                  </button>
                </div>
                <PopulationChart frames={sim.frames} indice={sim.indice}
                  montecarlo={mostrarBanda ? mc : null} colores={colores} />
              </div>
              <div className="card">
                <div className="card-head">
                  <p className="ttl">Estado actual</p>
                  <span className="mini-txt">clic en el color para cambiarlo</span>
                </div>
                <div className="readout">
                  {ESTADOS.map((e) => (
                    <div className="r" key={e.valor}>
                      <span className="k">
                        <input
                          type="color"
                          className="sw-pick"
                          value={colores[e.valor]}
                          onChange={(ev) => setColores((c) => ({ ...c, [e.valor]: ev.target.value }))}
                          aria-label={`Color del estado ${e.nombre}`}
                          title={`Color del estado ${e.nombre}`}
                        />
                        {e.nombre}
                      </span>
                      <span className="v">{frac(e.valor === 2 ? n?.a ?? 0 : e.valor === 1 ? n?.l ?? 0 : n?.m ?? 0)}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="card">
                <div className="card-head">
                  <p className="ttl">Notación de la regla</p>
                  <span className="mini-txt">{nombreReglaActiva}</span>
                </div>
                <Notacion tex={notacion} />
              </div>
              {sim.error && <div className="card err">{sim.error}</div>}
            </aside>
          </>
        ) : (
          <button className="rz-tab rz-tab-r" onClick={() => setPanelOpen(true)}
            title="Mostrar datos" aria-label="Mostrar panel de datos">◂</button>
        )}
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

      {modalEditar && (
        <div className="modal-bg" onClick={onCancelarEditar}>
          <div className="modal modal-sm" onClick={(e) => e.stopPropagation()}>
            <p className="modal-ttl">Editar parámetros</p>
            <p className="modal-sub">
              Para cambiar los parámetros tenés que <b>reiniciar</b> la simulación
              (se descarta la corrida actual). Si no, seguí reproduciéndola.
            </p>
            <div className="modal-foot">
              <button className="ghost" onClick={onCancelarEditar}>Cancelar</button>
              <button className="run" onClick={onReiniciarEditar}>Reiniciar y ajustar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
