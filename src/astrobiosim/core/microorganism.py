"""Especie microbiana — contrato de frontera §3.2 (dueña: Esmeralda).

STUB de Hito 0. La jerarquía de especies y la implementación vectorizada de
`condiciones_habitables` van en `feat/bio-especies`.
"""
from __future__ import annotations

from abc import ABC

import numpy as np

from astrobiosim.core.environment import CampoAmbiental


class Microorganismo(ABC):
    """Base abstracta de una especie definida por sus umbrales de tolerancia."""

    t_min: float  # °C
    t_max: float  # °C
    r_letal: float  # Gy (umbral letal de radiación acumulada)
    a_w_min: float  # actividad de agua mínima (0..1)
    mu_max: float  # tasa de reproducción óptima

    def condiciones_habitables(self, campo: CampoAmbiental) -> np.ndarray:
        """Máscara bool (M, N): True donde TODAS las variables están en umbral.

        Vectorizado:
            (campo.T >= t_min) & (campo.T <= t_max)
            & (campo.R <= r_letal) & (campo.A_w >= a_w_min)
        """
        raise NotImplementedError("Esmeralda: implementar en feat/bio-especies (§3.2)")
