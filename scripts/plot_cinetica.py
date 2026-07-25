#!/usr/bin/env python3
"""Genera la figura de las curvas de crecimiento CTMI para la defensa.

Usa el código real del motor (`engine.transition_rules`), no una re-derivación:
la figura es, de hecho, una validación visual de que `cinetica_mu` produce las
curvas cardinales esperadas. Salida: `docs/toBePresented/cinetica_ctmi.pdf`.

Uso:
    python scripts/plot_cinetica.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from astrobiosim.core.environment import CampoAmbiental  # noqa: E402
from astrobiosim.core.microorganism import (  # noqa: E402
    DRadiodurans,
    EColi,
    MBurtonii,
)
from astrobiosim.engine.transition_rules import cinetica_mu  # noqa: E402

SALIDA = RAIZ / "docs" / "toBePresented" / "cinetica_ctmi.pdf"

ESPECIES = [
    (EColi(), "E. coli (Tierra)", "#2E7D32"),
    (DRadiodurans(), "D. radiodurans (Marte)", "#C0392B"),
    (MBurtonii(), "M. burtonii (Encelado)", "#2471A3"),
]


def _mu_vs_temperatura(especie, temperaturas: np.ndarray) -> np.ndarray:
    """μ(T) con a_w=1 y UV=0 (óptimos), es decir μ_opt·γ_T(T), vía el motor real."""
    n = temperaturas.size
    campo = CampoAmbiental(
        T=temperaturas.reshape(1, n),
        R=np.zeros((1, n)),
        A_w=np.ones((1, n)),
    )
    return cinetica_mu(especie, campo).ravel()


def main() -> None:
    temperaturas = np.linspace(-15.0, 55.0, 700)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))

    for especie, etiqueta, color in ESPECIES:
        mu = _mu_vs_temperatura(especie, temperaturas)
        ax.plot(temperaturas, mu, color=color, lw=2.0, label=etiqueta)
        # marca el óptimo (μ = μ_opt)
        ax.plot(especie.t_opt, especie.mu_opt, "o", color=color, ms=5)

    ax.set_xlabel("Temperatura (°C)")
    ax.set_ylabel(r"Tasa de crecimiento $\mu$ (h$^{-1}$)")
    ax.set_title("Cinética CTMI: μ(T) por especie (a$_w$=1, UV=0)")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, fontsize=9)
    ax.margins(x=0)
    fig.tight_layout()
    fig.savefig(SALIDA)
    print(f"escrito {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
