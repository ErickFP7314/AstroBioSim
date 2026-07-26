// Paleta "Espectro" (opción C): doble acento cian + ámbar atado a los estados.
// Estos colores se usan desde JS (canvas de la grilla, leyenda, gráfico). El resto
// del chrome vive como custom properties en styles.css con los mismos valores.

/** Colores de los tres estados del autómata (ADR-0012), indexados por valor. */
export const ESTADO_COLOR: Record<number, string> = {
  0: "#3a4658", // MUERTA  — slate
  1: "#f59e0b", // LATENTE — ámbar
  2: "#38bdf8", // ACTIVA  — cian (= acento)
};

export const ESTADOS = [
  { valor: 2, nombre: "Activa", color: ESTADO_COLOR[2] },
  { valor: 1, nombre: "Latente", color: ESTADO_COLOR[1] },
  { valor: 0, nombre: "Muerta", color: ESTADO_COLOR[0] },
];

export const ACENTO = "#38bdf8";
export const GRID_BG = "#090d14";
export const GRID_LINEA = "#141b26";
