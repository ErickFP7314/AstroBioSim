#!/usr/bin/env python3
"""Validación biológica de las salidas: trayectorias poblacionales de las 3 corridas.

Corre un ensamble Montecarlo del modo Analógico (datos reales 2025) para cada
especie en su entorno y grafica la composición poblacional
(\\MUERTA/\\LATENTE/\\ACTIVA) en el tiempo, con media ± desviación. Es la evidencia
visual de que las salidas son biológicamente plausibles —sin extinción instantánea
ni saturación irreal— y la lectura de cada entorno (tarea de Fidel).

Uso:
    python scripts/validacion_biologica.py
    python scripts/validacion_biologica.py --n-corridas 30 --iteraciones 120
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from astrobiosim.analysis.barrido import FabricaModoAnalogico
from astrobiosim.core.microorganism import ACTIVA, LATENTE, MUERTA, DRadiodurans, EColi, MBurtonii
from astrobiosim.data.loaders import cargar_atacama, cargar_control_tierra, cargar_ventilas
from astrobiosim.data.resampling import Entorno
from astrobiosim.simulation import sembrar_estado, simular_montecarlo

_DATA = RAIZ / "data" / "processed"
#: (nombre, loader, archivo, entorno, especie) por corrida.
CORRIDAS = [
    ("Tierra · E. coli", cargar_control_tierra, "datos_tierra_control_2025.csv", Entorno.TIERRA, EColi),
    ("Marte · D. radiodurans", cargar_atacama, "datos_atacama_2025_EXTREMOS_REALES.csv", Entorno.MARTE, DRadiodurans),
    ("Encelado · M. burtonii", cargar_ventilas, "datos_ventilas_2025_procesados.csv", Entorno.ENCELADO, MBurtonii),
]
#: Colores de estado (coinciden con los .tex de la defensa).
_COLOR = {MUERTA: ("#9AA0A6", "MUERTA"), LATENTE: ("#C9A227", "LATENTE"), ACTIVA: ("#2E7D32", "ACTIVA")}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n-corridas", type=int, default=25, help="Réplicas Montecarlo por entorno (default: 25).")
    p.add_argument("--lado", type=int, default=32, help="Lado de la grilla (default: 32).")
    p.add_argument("--iteraciones", type=int, default=100, help="Ticks por corrida (default: 100).")
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--salida", type=Path, default=RAIZ / "docs" / "toBePresented")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    shape = (args.lado, args.lado)

    fig, ejes = plt.subplots(1, 3, figsize=(13.5, 4.3), sharey=True)
    for ax, (titulo, loader, archivo, entorno, especie_cls) in zip(ejes, CORRIDAS):
        df = loader(str(_DATA / archivo))
        construir_modo = FabricaModoAnalogico(df, entorno, shape)
        print(f"Corriendo {args.n_corridas} réplicas — {titulo}…")
        res = simular_montecarlo(
            construir_modo, especie_cls(),
            lambda rng: sembrar_estado(shape, rng=rng, fraccion_activa=0.15),
            n_corridas=args.n_corridas, semilla=args.semilla, re_sembrar=True,
            n_iteraciones=args.iteraciones,
        )
        t = np.arange(len(res))
        for estado in (MUERTA, LATENTE, ACTIVA):
            media, desv = res.curva(estado)
            color, etiqueta = _COLOR[estado]
            ax.plot(t, media, color=color, lw=1.8, label=etiqueta)
            ax.fill_between(t, np.clip(media - desv, 0, 1), np.clip(media + desv, 0, 1),
                            color=color, alpha=0.18)
        ax.set_title(titulo, fontsize=10.5)
        ax.set_xlabel("tick")
        ax.set_ylim(-0.02, 1.02)
        ax.margins(x=0)
        ax.grid(color="#eef0f2", lw=0.6)
        ax.set_axisbelow(True)
    ejes[0].set_ylabel("fracción de la grilla")
    ejes[0].legend(loc="center right", fontsize=8, frameon=True)
    fig.suptitle(
        f"Validación biológica — composición poblacional en el tiempo (media ± σ, "
        f"{args.n_corridas} réplicas · grilla {args.lado}×{args.lado} · modo Analógico)",
        fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    png = args.salida / "validacion_biologica_3entornos.png"
    fig.savefig(png, dpi=130)
    plt.close(fig)

    try:
        destino = png.relative_to(RAIZ)
    except ValueError:
        destino = png
    print(f"\nEscrito: {destino}")


if __name__ == "__main__":
    main()
