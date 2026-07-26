import { useEffect, useRef } from "react";
import { decodeGrid, type Frame } from "../api";
import { ESTADO_COLOR, ESTADOS, GRID_BG } from "../theme";

/** La grilla del autómata en un <canvas>: protagonista de la vista. Debajo, la
 *  línea de tiempo (scrubber) para ver y mover el tick actual. */
export function AutomatonGrid({
  frame, indice, total, irA,
}: {
  frame: Frame | null;
  indice: number;
  total: number;
  irA: (i: number) => void;
}) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const ultimo = total > 0 ? total - 1 : 0;

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const size = 512;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.fillStyle = GRID_BG;
    ctx.fillRect(0, 0, size, size);
    if (!frame) return;

    const [rows, cols] = frame.shape;
    const grid = decodeGrid(frame.grid);
    const cw = size / cols;
    const ch = size / rows;
    const gap = cols > 48 ? 0 : 1;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const v = grid[r * cols + c];
        if (v === 0 && gap === 0) continue; // fondo hace de MUERTA en grillas densas
        ctx.fillStyle = ESTADO_COLOR[v] ?? GRID_BG;
        ctx.fillRect(c * cw, r * ch, Math.ceil(cw) - gap, Math.ceil(ch) - gap);
      }
    }
  }, [frame]);

  return (
    <div className="stage">
      <div className="gridwrap">
        <canvas
          ref={ref}
          className="grid-canvas"
          role="img"
          aria-label="Grilla del autómata celular: cada celda es Muerta, Latente o Activa."
        />
      </div>
      <div className="scrubber">
        <span className="tk-lbl">tick</span>
        <input
          type="range"
          min={0}
          max={ultimo}
          value={total > 0 ? indice : 0}
          disabled={total === 0}
          onChange={(e) => irA(Number(e.target.value))}
          aria-label="Línea de tiempo: mover al tick"
        />
        <span className="tk-val">
          <b>{total > 0 ? indice : 0}</b> <i>/ {ultimo}</i>
        </span>
      </div>

      <div className="legend">
        {ESTADOS.map((e) => (
          <span key={e.valor}>
            <b style={{ background: e.color }} />
            {e.nombre}
          </span>
        ))}
      </div>
    </div>
  );
}
