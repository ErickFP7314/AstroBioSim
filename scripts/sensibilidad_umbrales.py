#!/usr/bin/env python3
"""Análisis de sensibilidad de los umbrales biológicos (tarea de Erick, ADR-0013).

Blinda el resultado del barrido frente a la incertidumbre de los umbrales de especie.
Barre cada umbral sobre su rango de incertidumbre (ancho según su procedencia en
``docs/parametros.md`` §1) dejando el resto en su valor nominal, y mide cómo cambia
la **probabilidad de persistencia** en el mismo escenario del barrido (misma especie,
entorno y salmuera cerca del umbral crítico).

Genera un **diagrama de tornado**: una barra por umbral, del extremo de menor al de
mayor persistencia dentro de su rango, ordenadas por amplitud (el de arriba domina).
La línea del nominal y el sombreado alrededor de 0.5 muestran si la conclusión
("persiste" ⇔ prob ≥ 0.5) se sostiene en todo el rango de incertidumbre.

Uso:
    python scripts/sensibilidad_umbrales.py                      # E. coli / Marte
    python scripts/sensibilidad_umbrales.py --especie dradiodurans --poblacion activa
    python scripts/sensibilidad_umbrales.py --frecuencia 0.0     # ambiente puro (sin refugios)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from astrobiosim.analysis.barrido import FabricaModoAnalogico
from astrobiosim.analysis.sensibilidad import analisis_sensibilidad
from astrobiosim.core.microorganism import DRadiodurans, EColi, MBurtonii
from astrobiosim.data.loaders import cargar_atacama, cargar_control_tierra, cargar_ventilas
from astrobiosim.data.resampling import Entorno

_DATA = RAIZ / "data" / "processed"
_ESPECIES = {"ecoli": EColi, "dradiodurans": DRadiodurans, "mburtonii": MBurtonii}
_ENTORNOS = {"tierra": Entorno.TIERRA, "marte": Entorno.MARTE, "encelado": Entorno.ENCELADO}
_LOADER = {
    "tierra": (cargar_control_tierra, "datos_tierra_control_2025.csv"),
    "marte": (cargar_atacama, "datos_atacama_2025_EXTREMOS_REALES.csv"),
    "encelado": (cargar_ventilas, "datos_ventilas_2025_procesados.csv"),
}
#: Color por procedencia (cuánto confiamos en el umbral).
_COLOR_PROC = {"LIT": "#0369a1", "ANA": "#7c3aed", "EST": "#dc2626", "DER": "#0891b2", "CONV": "#64748b"}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--especie", choices=list(_ESPECIES), default="ecoli")
    p.add_argument("--entorno", choices=list(_ENTORNOS), default="marte")
    p.add_argument("--poblacion", choices=["viva", "activa"], default="viva",
                   help="Qué población cuenta como persistencia (activa = viable). "
                        "Para D. radiodurans usar 'activa': con 'viva' persiste trivialmente.")
    p.add_argument("--n-puntos", type=int, default=7, help="Valores por umbral (default: 7).")
    p.add_argument("--n-corridas", type=int, default=40, help="Réplicas Montecarlo por punto (default: 40).")
    p.add_argument("--lado", type=int, default=36, help="Lado de la grilla (default: 36).")
    p.add_argument("--iteraciones", type=int, default=250, help="Ticks por corrida (default: 250).")
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--procesos", type=int, default=0, help="0 = auto (nº de CPUs).")
    # Salmuera cerca del umbral crítico del barrido (donde la sensibilidad importa).
    p.add_argument("--frecuencia", type=float, default=0.5, help="probabilidad_disparo de la salmuera (0 = sin refugios). "
                   "0.5 deja la persistencia nominal de E. coli/Marte cerca de la frontera 0.5 (máxima sensibilidad).")
    p.add_argument("--magnitud", type=float, default=0.98, help="a_w pico de la salmuera.")
    p.add_argument("--salmuera-radio", type=float, default=11.0)
    p.add_argument("--salmuera-duracion", type=float, default=15.0)
    p.add_argument("--salida", type=Path, default=RAIZ / "docs" / "toBePresented")
    return p.parse_args()


def _tornado(r, args, png: Path) -> None:
    ranking = r.ranking()
    y = np.arange(len(ranking))[::-1]           # el dominante arriba
    fig, ax = plt.subplots(figsize=(9.6, 5.4))

    ax.axvspan(0.45, 0.55, color="#94a3b8", alpha=0.18, zorder=0)   # zona de decisión
    ax.axvline(0.5, color="#334155", ls="--", lw=1.0, label="frontera de persistencia (0.5)")
    ax.axvline(r.prob_nominal, color="#f59e0b", ls=":", lw=1.4, label=f"nominal = {r.prob_nominal:.2f}")

    for yi, resp in zip(y, ranking):
        lo = float(np.nanmin(resp.prob_persistencia))
        hi = float(np.nanmax(resp.prob_persistencia))
        color = _COLOR_PROC.get(resp.procedencia, "#64748b")
        ax.barh(yi, hi - lo, left=lo, height=0.62, color=color, alpha=0.85,
                edgecolor="white", zorder=3)
        # marca del nominal dentro de la barra
        ax.plot([r.prob_nominal], [yi], marker="|", color="#1e293b", ms=14, mew=1.6, zorder=4)

    etiquetas = [f"{resp.nombre}  [{resp.procedencia}]" for resp in ranking]
    ax.set_yticks(y)
    ax.set_yticklabels(etiquetas, fontsize=9)
    ax.set_xlim(-0.02, 1.02)
    ax.set_xlabel("probabilidad de persistencia (barriendo el umbral en su rango de incertidumbre)")
    robusta = "SÍ" if r.conclusiones_robustas() else "NO"
    dom = r.dominante
    ax.set_title(
        f"Sensibilidad de umbrales — {args.entorno} · {args.especie} · población {args.poblacion}\n"
        f"domina: {dom.nombre} [{dom.procedencia}] (Δprob = {dom.rango_respuesta:.2f})   ·   "
        f"conclusión robusta en todo el rango: {robusta}",
        fontsize=10.5)

    # leyenda de procedencia + referencias
    from matplotlib.patches import Patch
    handles = [Patch(color=_COLOR_PROC[k], label=f"[{k}] {txt}") for k, txt in
               (("LIT", "publicado"), ("ANA", "por analogía"), ("EST", "estimado"))]
    leg1 = ax.legend(handles=handles, title="procedencia del umbral", loc="lower right", fontsize=8, title_fontsize=8)
    ax.add_artist(leg1)
    ax.legend(loc="lower left", fontsize=8, frameon=True)
    ax.grid(axis="x", color="#e2e8f0", lw=0.6)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(png, dpi=130)
    plt.close(fig)


def main() -> None:
    args = _parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    shape = (args.lado, args.lado)

    loader, archivo = _LOADER[args.entorno]
    df = loader(str(_DATA / archivo))
    construir_modo = FabricaModoAnalogico(df, _ENTORNOS[args.entorno], shape)
    especie = _ESPECIES[args.especie]()

    salmuera_base = {
        "radio_celdas": args.salmuera_radio,
        "duracion_min_ticks": args.salmuera_duracion,
        "duracion_max_ticks": args.salmuera_duracion,
    }
    procesos = args.procesos if args.procesos > 0 else (os.cpu_count() or 1)

    print(f"Análisis de sensibilidad: {args.especie}/{args.entorno}, "
          f"{args.n_puntos} puntos × {args.n_corridas} réplicas por umbral…")

    def progreso(hechos: int, total: int) -> None:
        print(f"\r  {hechos}/{total} corridas", end="", flush=True)

    r = analisis_sensibilidad(
        construir_modo, especie,
        n_puntos=args.n_puntos, frecuencia=args.frecuencia, magnitud=args.magnitud,
        eje_magnitud="a_w", salmuera_base=salmuera_base, shape=shape,
        n_corridas=args.n_corridas, semilla_base=args.semilla, n_iteraciones=args.iteraciones,
        poblacion=args.poblacion, n_procesos=procesos, progreso=progreso,
    )
    print()

    png = args.salida / f"sensibilidad_{args.entorno}_{args.especie}_{args.poblacion}.png"
    _tornado(r, args, png)

    print("\n=== Ranking de dominancia (Δprob = amplitud de respuesta) ===")
    for resp in r.ranking():
        marca = "  ⚠ cruza 0.5" if resp.cruza() else ""
        print(f"  {resp.nombre:22s} [{resp.procedencia}]  Δprob = {resp.rango_respuesta:.3f}{marca}")
    print(f"\n  Persistencia nominal:          {r.prob_nominal:.3f}")
    print(f"  Umbral dominante:              {r.dominante.nombre} [{r.dominante.procedencia}]")
    print(f"  ¿Conclusión robusta en el rango? {'sí' if r.conclusiones_robustas() else 'NO'}")
    criticos = r.umbrales_criticos()
    if criticos:
        print(f"  Umbrales que pueden invertirla:  {', '.join(x.nombre for x in criticos)}")

    try:
        destino = png.relative_to(RAIZ)
    except ValueError:
        destino = png
    print(f"\nEscrito: {destino}")


if __name__ == "__main__":
    main()
