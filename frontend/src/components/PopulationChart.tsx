import { useMemo } from "react";
import type { Frame, Montecarlo } from "../api";
import { ESTADO_COLOR } from "../theme";

const W = 300;
const H = 168;
const PAD = 6;

function xAt(t: number, n: number) {
  return n <= 1 ? PAD : PAD + (t / (n - 1)) * (W - 2 * PAD);
}
function yAt(f: number) {
  return H - PAD - Math.max(0, Math.min(1, f)) * (H - 2 * PAD);
}
function linea(vals: number[]) {
  return vals.map((f, t) => `${xAt(t, vals.length).toFixed(1)},${yAt(f).toFixed(1)}`).join(" ");
}

/** Curvas de las tres fracciones del run en vivo + banda Montecarlo (media ± σ). */
export function PopulationChart({
  frames,
  indice,
  montecarlo,
}: {
  frames: Frame[];
  indice: number;
  montecarlo: Montecarlo | null;
}) {
  const series = useMemo(() => {
    const a: number[] = [], l: number[] = [], m: number[] = [];
    for (const f of frames) {
      const tot = f.n.m + f.n.l + f.n.a || 1;
      a.push(f.n.a / tot);
      l.push(f.n.l / tot);
      m.push(f.n.m / tot);
    }
    return { a, l, m };
  }, [frames]);

  const banda = useMemo(() => {
    if (!montecarlo) return null;
    const { media, desviacion } = montecarlo;
    const n = media.length;
    const up: string[] = [], lo: string[] = [];
    for (let t = 0; t < n; t++) {
      up.push(`${xAt(t, n).toFixed(1)},${yAt(media[t][2] + desviacion[t][2]).toFixed(1)}`);
    }
    for (let t = n - 1; t >= 0; t--) {
      lo.push(`${xAt(t, n).toFixed(1)},${yAt(media[t][2] - desviacion[t][2]).toFixed(1)}`);
    }
    return {
      poly: [...up, ...lo].join(" "),
      media: media.map((row) => row[2]),
    };
  }, [montecarlo]);

  const cursorX = xAt(indice, Math.max(series.a.length, 1));

  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true">
      <g className="grid-lines">
        <line x1="0" y1={yAt(0.25)} x2={W} y2={yAt(0.25)} />
        <line x1="0" y1={yAt(0.5)} x2={W} y2={yAt(0.5)} />
        <line x1="0" y1={yAt(0.75)} x2={W} y2={yAt(0.75)} />
      </g>
      {banda && (
        <>
          <polygon points={banda.poly} fill={ESTADO_COLOR[2]} opacity="0.14" />
          <polyline points={linea(banda.media)} fill="none" stroke={ESTADO_COLOR[2]}
            strokeWidth="1" strokeDasharray="3 3" opacity="0.5" />
        </>
      )}
      {series.m.length > 1 && (
        <>
          <polyline points={linea(series.l)} fill="none" stroke={ESTADO_COLOR[1]} strokeWidth="1.8" />
          <polyline points={linea(series.m)} fill="none" stroke={ESTADO_COLOR[0]} strokeWidth="1.8" />
          <polyline points={linea(series.a)} fill="none" stroke={ESTADO_COLOR[2]} strokeWidth="2.2" />
        </>
      )}
      {series.a.length > 0 && indice < series.a.length && (
        <>
          <line className="cursor" x1={cursorX} y1="0" x2={cursorX} y2={H} />
          <circle cx={cursorX} cy={yAt(series.a[indice])} r="3" fill={ESTADO_COLOR[2]} />
        </>
      )}
    </svg>
  );
}
