/// <reference lib="webworker" />
/*
 * Web Worker: corre el motor Python (paquete `astrobiosim`) dentro de Pyodide
 * (CPython compilado a WASM). Es lo que hace el deploy 100% estático (Cloudflare
 * Pages): NO hay backend — la simulación corre en el navegador del visitante.
 *
 * Protocolo (postMessage):
 *   ← { type: "init", baseUrl }            → carga Pyodide + numpy/pandas + wheel + datos
 *   → { type: "progress", msg } / { type: "ready" }
 *   ← { type: "catalogo"|"correr"|"montecarlo"|"validar", id, ... }
 *   → { type: "result", id, data } | { type: "error", id, detail }
 */
const PYODIDE_VER = "0.27.7";
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VER}/full/`;
const WHEEL = "astrobiosim-0.1.0-py3-none-any.whl";
const DATOS = [
  "datos_atacama_2025_EXTREMOS_REALES.csv",
  "datos_tierra_control_2025.csv",
  "datos_ventilas_2025_procesados.csv",
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let pyodide: any = null;

function post(m: unknown) {
  (self as unknown as Worker).postMessage(m);
}

async function init(baseUrl: string): Promise<void> {
  post({ type: "progress", msg: "descargando el motor (Pyodide)…" });
  // Método estándar de Pyodide para un worker clásico: importScripts carga el
  // UMD (define self.loadPyodide) de forma síncrona y confiable (más robusto que
  // un import() dinámico cross-origin en un módulo worker).
  const g = self as unknown as { importScripts: (u: string) => void; loadPyodide: (o: { indexURL: string }) => Promise<unknown> };
  g.importScripts(`${PYODIDE_URL}pyodide.js`);
  pyodide = await g.loadPyodide({ indexURL: PYODIDE_URL });

  post({ type: "progress", msg: "cargando NumPy y pandas…" });
  await pyodide.loadPackage(["numpy", "pandas"]);

  post({ type: "progress", msg: "instalando AstroBioSim…" });
  // El wheel es puro-Python (un zip): se importa directo desde sys.path, sin
  // micropip. Verificado en Pyodide (Node).
  const bytes = new Uint8Array(await (await fetch(new URL(`pyodide/${WHEEL}`, baseUrl).href)).arrayBuffer());
  pyodide.FS.writeFile("/astrobiosim.whl", bytes);
  await pyodide.runPythonAsync("import sys\nif '/astrobiosim.whl' not in sys.path:\n    sys.path.insert(0, '/astrobiosim.whl')");

  post({ type: "progress", msg: "cargando datos reales 2025…" });
  pyodide.FS.mkdirTree("/datos");
  for (const f of DATOS) {
    const txt = await (await fetch(new URL(`pyodide/data/${f}`, baseUrl).href)).text();
    pyodide.FS.writeFile(`/datos/${f}`, txt);
  }
  // Reapunta el motor a los CSV montados en el FS virtual de Pyodide.
  await pyodide.runPythonAsync(
    "from pathlib import Path\nfrom astrobiosim.web import engine\nengine.DATA_DIR = Path('/datos')",
  );
  post({ type: "ready" });
}

/** Corre un fragmento Python que termina en una expresión JSON-string y la parsea. */
function pyJson(codigo: string, cfg?: unknown): unknown {
  if (cfg !== undefined) pyodide.globals.set("_cfg_json", JSON.stringify(cfg));
  return JSON.parse(pyodide.runPython(codigo) as string);
}

const CODIGO = {
  catalogo: "import json\nfrom astrobiosim.web import engine\njson.dumps(engine.catalogo())",
  correr:
    "import json\nfrom astrobiosim.web import engine\njson.dumps(list(engine.iter_frames(json.loads(_cfg_json))))",
  montecarlo:
    "import json\nfrom astrobiosim.web import engine\njson.dumps(engine.montecarlo(json.loads(_cfg_json)))",
  validar:
    "import json\nfrom astrobiosim.web import engine\njson.dumps(engine.validar_regla(json.loads(_cfg_json)))",
};

self.onmessage = async (e: MessageEvent) => {
  const m = e.data;
  try {
    if (m.type === "init") {
      await init(m.baseUrl);
      return;
    }
    if (!pyodide) throw new Error("el motor todavía no está listo");
    if (m.type === "catalogo") post({ type: "result", id: m.id, data: pyJson(CODIGO.catalogo) });
    else if (m.type === "correr") post({ type: "result", id: m.id, data: pyJson(CODIGO.correr, m.cfg) });
    else if (m.type === "montecarlo") post({ type: "result", id: m.id, data: pyJson(CODIGO.montecarlo, m.cfg) });
    else if (m.type === "validar") post({ type: "result", id: m.id, data: pyJson(CODIGO.validar, m.spec) });
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    post({ type: "error", id: m?.id, detail });
  }
};
