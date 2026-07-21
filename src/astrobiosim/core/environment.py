"""Campo ambiental — contrato de frontera §3.1 (dueño: Jose).

STUB de Hito 0: define la interfaz para que el resto del equipo pueda importar
y programar en paralelo. La implementación real va en `feat/env-campo-ambiental`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class CampoAmbiental:
    """Tres capas escalares alineadas a la grilla M×N.

    Parameters
    ----------
    T : np.ndarray
        Temperatura (°C), shape (M, N).
    R : np.ndarray
        Radiación: flujo (W/m²), proxy operativo — ver ADR-0010; shape (M, N).
    A_w : np.ndarray
        Actividad de agua (0..1), shape (M, N).
    """

    T: np.ndarray
    R: np.ndarray
    A_w: np.ndarray

    def __post_init__(self) -> None:
        # STUB: el stub permite instanciar; la validación de formas idénticas
        # la implementa Jose (§3.1).
        ...

    @property
    def shape(self) -> tuple[int, int]:
        """Forma (M, N) de las capas."""
        raise NotImplementedError("Jose: implementar en feat/env-campo-ambiental (§3.1)")
