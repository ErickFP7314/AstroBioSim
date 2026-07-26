#!/usr/bin/env python3
"""Validación estadística del Montecarlo: convergencia de la media (tarea de Erick).

Genera la figura que responde el criterio *"el nº de réplicas es suficiente"*: la
**media acumulada ± intervalo de confianza** y el **error estándar ∝ 1/√N** en función
del nº de réplicas. Además reporta **media ± σ** (no una corrida sola) y confirma la
**reproducibilidad** con semillas fijas.

Por defecto corre el caso de MÁS varianza —*E. coli* en Marte con salmueras cerca del
umbral crítico del barrido—, que es justo donde importa tener suficientes réplicas.

Uso:
    python scripts/validacion_montecarlo.py                 # caso por defecto
    python scripts/validacion_montecarlo.py --n-max 400     # más réplicas
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
from astrobiosim.analysis.validacion_montecarlo import estudio_convergencia
from astrobiosim.core.microorganism import DRadiodurans, EColi, MBurtonii
from astrobiosim.data.loaders import cargar_atacama, cargar_control_tierra, cargar_ventilas
from astrobiosim.data.resampling import Entorno
from astrobiosim.engine.stochastic import SalmueraDelicuescente
from astrobiosim.simulation import sembrar_estado

_DATA = RAIZ / "data" / "processed"
_ESPECIES = {"ecoli": EColi, "dradiodurans": DRadiodurans, "mburtonii": MBurtonii}
_ENTORNOS = {"tierra": Entorno.TIERRA, "marte": Entorno.MARTE, "encelado": Entorno.ENCELADO}
_LOADER = {
    "tierra": (cargar_control_tierra, "datos_tierra_control_2025.csv"),
    "marte": (cargar_atacama, "datos_atacama_2025_EXTREMOS_REALES.csv"),
    "encelado": (cargar_ventilas, "datos_ventilas_2025_procesados.csv"),
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--especie", choices=list(_ESPECIES), default="ecoli")
    p.add_argument("--entorno", choices=list(_ENTORNOS), default="marte")
    p.add_argument("--metrica", choices=["viva", "activa", "muerta", "persistencia"],
                   default="persistencia",
                   help="'persistencia' (binaria: queda población viva) da la probabilidad "
                        "de persistencia, con varianza máxima cerca del umbral (default).")
    p.add_argument("--umbral", type=float, default=0.0,
                   help="Fracción viva por encima de la cual cuenta como 'persiste' (default: 0).")
    p.add_argument("--n-max", type=int, default=400, help="Nº de réplicas (default: 400).")
    p.add_argument("--lado", type=int, default=36, help="Lado de la grilla (default: 36).")
    p.add_argument("--iteraciones", type=int, default=250, help="Ticks por corrida (default: 250).")
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--error-objetivo", type=float, default=0.03,
                   help="SE objetivo para reportar el N suficiente (default: 0.03).")
    # Salmuera cerca del umbral crítico (caso de alta varianza). freq=0 la desactiva.
    p.add_argument("--salmuera-freq", type=float, default=0.4)
    p.add_argument("--salmuera-radio", type=float, default=11.0)
    p.add_argument("--salmuera-a-w", type=float, default=0.98)
    p.add_argument("--salmuera-duracion", type=float, default=15.0)
    p.add_argument("--salida", type=Path, default=RAIZ / "docs" / "toBePresented")
    return p.parse_args()


def _figura(r, args, n_suf: int, png: Path) -> None:
    n = r.n
    lo, hi = r.intervalo(0.95)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.8))

    # Panel 1: media acumulada ± IC 95 %.
    ax1.fill_between(n[1:], lo[1:], hi[1:], color="#38bdf8", alpha=0.25, label="IC 95 %")
    ax1.plot(n, r.media_acumulada, color="#0369a1", lw=1.6, label="media acumulada")
    ax1.axhline(r.media_final, color="#f59e0b", ls="--", lw=1.0, label=f"valor final = {r.media_final:.3f}")
    ax1.axvline(n_suf, color="#64748b", ls=":", lw=1.0, label=f"N suficiente = {n_suf}")
    ax1.set_title("Convergencia de la media")
    ax1.set_xlabel("N (nº de réplicas)")
    ax1.set_ylabel("probabilidad de persistencia" if r.metrica == "persistencia"
                   else f"fracción {r.metrica} media (final)")
    ax1.legend(fontsize=8, frameon=False)
    ax1.margins(x=0)

    # Panel 2: error estándar vs N (log-log) con la referencia 1/√N.
    ax2.loglog(n[1:], r.error_estandar[1:], color="#0369a1", lw=1.6, label="SE = σ/√N")
    ref = r.desviacion_final / np.sqrt(n[1:])
    ax2.loglog(n[1:], ref, color="#f59e0b", ls="--", lw=1.0, label="∝ 1/√N")
    ax2.axhline(args.error_objetivo, color="#64748b", ls=":", lw=1.0, label=f"objetivo = {args.error_objetivo}")
    ax2.set_title("Error estándar del estimador (∝ 1/√N)")
    ax2.set_xlabel("N (nº de réplicas, log)")
    ax2.set_ylabel("error estándar (log)")
    ax2.legend(fontsize=8, frameon=False)

    fig.suptitle(
        f"Validación estadística Montecarlo — {args.entorno} · {args.especie} · métrica {r.metrica} · "
        f"grilla {args.lado}×{args.lado} · {args.iteraciones} ticks · semilla {r.semilla_base}",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
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

    def estado_inicial(rng):
        return sembrar_estado(shape, rng=rng, fraccion_activa=0.15)

    def _eventos(_rng):  # factory por réplica (instancia fresca: la salmuera tiene estado)
        return [SalmueraDelicuescente(
            probabilidad_disparo=args.salmuera_freq, radio_celdas=args.salmuera_radio,
            a_w_objetivo_min=args.salmuera_a_w, a_w_objetivo_max=args.salmuera_a_w,
            duracion_min_ticks=args.salmuera_duracion, duracion_max_ticks=args.salmuera_duracion,
        )]

    construir_eventos = _eventos if args.salmuera_freq > 0.0 else None

    print(f"Corriendo {args.n_max} réplicas ({args.entorno}/{args.especie}, métrica {args.metrica})…")
    r = estudio_convergencia(
        construir_modo, especie, estado_inicial,
        n_max=args.n_max, semilla_base=args.semilla, metrica=args.metrica, umbral=args.umbral,
        construir_eventos=construir_eventos, n_iteraciones=args.iteraciones,
    )
    n_suf = r.n_suficiente(args.error_objetivo)

    # Criterio 3: reproducibilidad (misma semilla → misma traza).
    r2 = estudio_convergencia(
        construir_modo, especie, estado_inicial,
        n_max=min(20, args.n_max), semilla_base=args.semilla, metrica=args.metrica, umbral=args.umbral,
        construir_eventos=construir_eventos, n_iteraciones=args.iteraciones,
    )
    reproducible = np.array_equal(r.metrica_por_corrida[:len(r2.n)], r2.metrica_por_corrida)

    png = args.salida / f"validacion_montecarlo_{args.entorno}_{args.especie}_{args.metrica}.png"
    _figura(r, args, n_suf, png)

    print("\n=== Resultado ===")
    print(f"  Estimación (N={args.n_max}):   {r.metrica} = {r.media_final:.4f} ± {r.desviacion_final:.4f} (σ muestral)")
    print(f"  Error estándar de la media:   {r.error_final:.5f}")
    print(f"  N suficiente (SE ≤ {args.error_objetivo}):     {n_suf}")
    print(f"  Reproducible (semilla fija):  {'sí' if reproducible else 'NO'}")
    try:
        destino = png.relative_to(RAIZ)
    except ValueError:
        destino = png
    print(f"\nEscrito: {destino}")


if __name__ == "__main__":
    main()
