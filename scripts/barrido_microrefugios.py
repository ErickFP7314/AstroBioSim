#!/usr/bin/env python3
"""Barrido frecuencia × magnitud de microrefugios: mapa de persistencia (ADR-0015).

Responde la pregunta de investigación del proyecto — ¿con qué frecuencia y magnitud
mínimas de salmueras delicuescentes una población persiste en vez de extinguirse? —
corriendo un ensamble Montecarlo por punto y midiendo la persistencia. Genera, de
forma **reproducible**, dos heatmaps (probabilidad de persistencia + fracción viva
media) con el **umbral crítico** (contorno 0.5) marcado, y un CSV con los datos.

La "magnitud" es un eje **elegible** (`--magnitud a_w|duracion|radio`), porque
ADR-0015 no lo fija.

Uso (rápido, para probar):
    python scripts/barrido_microrefugios.py --puntos 6 --corridas 8 --lado 32 --iteraciones 80

Uso (exhaustivo, el entregable):
    python scripts/barrido_microrefugios.py --puntos 16 --corridas 30 --lado 40
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from astrobiosim.analysis.barrido import (
    RANGO_FRECUENCIA,
    RANGOS_MAGNITUD,
    FabricaModoAnalogico,
    barrido_microrefugios,
)
from astrobiosim.core.microorganism import DRadiodurans, EColi, MBurtonii
from astrobiosim.data.loaders import (
    cargar_atacama,
    cargar_control_tierra,
    cargar_ventilas,
)
from astrobiosim.data.resampling import Entorno

_DATA = RAIZ / "data" / "processed"
_ESPECIES = {"ecoli": EColi, "dradiodurans": DRadiodurans, "mburtonii": MBurtonii}
_ENTORNOS = {"tierra": Entorno.TIERRA, "marte": Entorno.MARTE, "encelado": Entorno.ENCELADO}
_LOADER = {
    "tierra": (cargar_control_tierra, "datos_tierra_control_2025.csv"),
    "marte": (cargar_atacama, "datos_atacama_2025_EXTREMOS_REALES.csv"),
    "encelado": (cargar_ventilas, "datos_ventilas_2025_procesados.csv"),
}
_ETIQUETA_EJE = {
    "a_w": "Magnitud · A_w pico del refugio",
    "duracion": "Magnitud · duración del refugio (ticks)",
    "radio": "Magnitud · radio del refugio (celdas)",
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--magnitud", choices=list(RANGOS_MAGNITUD), default="a_w",
                   help="Qué parámetro del refugio es el eje de magnitud (default: a_w).")
    p.add_argument("--entorno", choices=list(_ENTORNOS), default="marte")
    p.add_argument("--especie", choices=list(_ESPECIES), default="dradiodurans")
    p.add_argument("--poblacion", choices=["viva", "activa"], default="viva",
                   help="Qué cuenta como persistencia: 'viva' (activa+latente) o "
                        "'activa' (solo creciendo). Para especies anhidrobióticas como "
                        "D. radiodurans usá 'activa' para ver el umbral (default: viva).")
    p.add_argument("--umbral", type=float, default=0.0,
                   help="Fracción de población por encima de la cual 'persiste' (default: 0).")
    # Fijan los parámetros del refugio que NO son el eje de magnitud.
    p.add_argument("--refugio-a-w", type=float, default=None, help="Fija el a_w pico del refugio.")
    p.add_argument("--refugio-duracion", type=float, default=None, help="Fija la duración (ticks).")
    p.add_argument("--refugio-radio", type=float, default=None, help="Fija el radio (celdas).")
    p.add_argument("--puntos", type=int, default=16, help="Lado de la malla del barrido (default: 16).")
    p.add_argument("--corridas", type=int, default=30, help="Réplicas Montecarlo por punto (default: 30).")
    p.add_argument("--lado", type=int, default=40, help="Lado de la grilla espacial (default: 40).")
    p.add_argument("--iteraciones", type=int, default=None,
                   help="Ticks por corrida (default: el dataset completo).")
    p.add_argument("--semilla", type=int, default=0, help="Semilla base reproducible (default: 0).")
    p.add_argument("--procesos", type=int, default=os.cpu_count(),
                   help="Procesos en paralelo (default: nº de CPUs).")
    p.add_argument("--freq-min", type=float, default=RANGO_FRECUENCIA[0])
    p.add_argument("--freq-max", type=float, default=RANGO_FRECUENCIA[1])
    p.add_argument("--mag-min", type=float, default=None, help="Default: según el eje.")
    p.add_argument("--mag-max", type=float, default=None, help="Default: según el eje.")
    p.add_argument("--salida", type=Path, default=RAIZ / "docs" / "toBePresented",
                   help="Directorio de salida (default: docs/toBePresented).")
    return p.parse_args()


def _progreso(hechos: int, total: int, t0: float) -> None:
    frac = hechos / total
    ancho = 28
    lleno = int(ancho * frac)
    transcurrido = time.time() - t0
    eta = transcurrido / frac - transcurrido if frac > 0 else 0.0
    barra = "█" * lleno + "·" * (ancho - lleno)
    sys.stdout.write(f"\r  [{barra}] {hechos}/{total}  ETA {eta:5.0f}s")
    sys.stdout.flush()
    if hechos == total:
        sys.stdout.write("\n")


def _figura(res, args, png: Path) -> None:
    frec, magn = res.frecuencias, res.magnitudes
    extent = [frec[0], frec[-1], magn[0], magn[-1]]
    F, M = np.meshgrid(frec, magn)
    curva = res.curva_critica(0.5)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 5.0))
    for ax, datos, titulo, cmap in (
        (ax1, res.prob_persistencia, f"Prob. de persistencia (población {res.poblacion})", "viridis"),
        (ax2, res.fraccion_media, f"Fracción media final ({res.poblacion})", "magma"),
    ):
        im = ax.imshow(datos, origin="lower", extent=extent, aspect="auto",
                       cmap=cmap, vmin=0.0, vmax=1.0)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        # umbral crítico: contorno 0.5 de la probabilidad, en ambos paneles
        ax.contour(F, M, res.prob_persistencia, levels=[0.5], colors="white",
                   linewidths=1.6, linestyles="--")
        ok = ~np.isnan(curva)
        ax.plot(frec[ok], curva[ok], "o-", color="white", ms=3, lw=1.0, alpha=0.9)
        ax.set_title(titulo)
        ax.set_xlabel("Frecuencia · probabilidad_disparo (por tick)")
        ax.set_ylabel(_ETIQUETA_EJE[args.magnitud])

    n_iter = args.iteraciones if args.iteraciones is not None else "dataset completo"
    fig.suptitle(
        f"Umbral crítico de microrefugios — {args.entorno} · {args.especie} · "
        f"N={args.corridas} · grilla {args.lado}×{args.lado} · {n_iter} ticks · "
        f"semilla {args.semilla}\n(línea blanca punteada = umbral crítico, prob. 0.5)",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(png, dpi=130)
    plt.close(fig)


def main() -> None:
    args = _parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)

    mag_min = args.mag_min if args.mag_min is not None else RANGOS_MAGNITUD[args.magnitud][0]
    mag_max = args.mag_max if args.mag_max is not None else RANGOS_MAGNITUD[args.magnitud][1]
    frecuencias = np.linspace(args.freq_min, args.freq_max, args.puntos)
    magnitudes = np.linspace(mag_min, mag_max, args.puntos)

    loader, archivo = _LOADER[args.entorno]
    df = loader(str(_DATA / archivo))
    shape = (args.lado, args.lado)
    construir_modo = FabricaModoAnalogico(df, _ENTORNOS[args.entorno], shape)
    especie = _ESPECIES[args.especie]()

    # Parámetros del refugio fijados (los que no son el eje de magnitud).
    salmuera_base: dict = {}
    if args.refugio_a_w is not None:
        salmuera_base["a_w_objetivo_min"] = salmuera_base["a_w_objetivo_max"] = args.refugio_a_w
    if args.refugio_duracion is not None:
        salmuera_base["duracion_min_ticks"] = salmuera_base["duracion_max_ticks"] = args.refugio_duracion
    if args.refugio_radio is not None:
        salmuera_base["radio_celdas"] = args.refugio_radio

    total = args.puntos * args.puntos
    print(f"Barrido {args.puntos}×{args.puntos} ({total} puntos) × {args.corridas} réplicas "
          f"| {args.entorno}/{args.especie} | eje magnitud = {args.magnitud} "
          f"| {args.procesos} procesos")
    t0 = time.time()
    res = barrido_microrefugios(
        construir_modo, especie,
        frecuencias=frecuencias, magnitudes=magnitudes,
        eje_magnitud=args.magnitud, shape=shape,
        n_corridas=args.corridas, semilla_base=args.semilla,
        n_iteraciones=args.iteraciones, poblacion=args.poblacion, umbral=args.umbral,
        salmuera_base=salmuera_base or None,
        n_procesos=args.procesos, progreso=lambda h, t: _progreso(h, t, t0),
    )
    print(f"  listo en {time.time() - t0:.0f}s")

    stem = f"barrido_microrefugios_{args.entorno}_{args.especie}_{args.magnitud}_{args.poblacion}"
    csv = args.salida / f"{stem}.csv"
    png = args.salida / f"{stem}.png"
    res.a_dataframe().to_csv(csv, index=False)
    _figura(res, args, png)

    # Resumen textual del umbral crítico.
    curva = res.curva_critica(0.5)
    print(f"\nUMBRAL CRÍTICO (prob. persistencia = 0.5), magnitud mínima ({args.magnitud}) por frecuencia:")
    for f, m in zip(frecuencias, curva, strict=True):
        txt = "nunca persiste en el rango" if np.isnan(m) else f"magnitud ≥ {m:.3f}"
        print(f"  frecuencia {f:.3f}  →  {txt}")
    print(f"\nEscrito:\n  {_rel(csv)}\n  {_rel(png)}")


def _rel(p: Path) -> Path | str:
    """Ruta relativa al repo si es posible; si no (p. ej. salida fuera), absoluta."""
    try:
        return p.relative_to(RAIZ)
    except ValueError:
        return p


if __name__ == "__main__":
    main()
