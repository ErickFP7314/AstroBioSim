"""Paso del autómata celular — contrato de frontera §3.3 (dueño: Erick).

STUB de Hito 0. El conteo de vecinos de Moore vectorizado y el doble buffer
síncrono van en `feat/engine-transicion`.
"""
from __future__ import annotations

import numpy as np

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import Microorganismo


def paso(
    estado: np.ndarray, campo: CampoAmbiental, especie: Microorganismo
) -> np.ndarray:
    """Un tick del AC (actualización síncrona). Devuelve el nuevo estado (M, N) int8.

    Usa `especie.condiciones_habitables(campo)` y el conteo de vecinos de Moore.
    """
    raise NotImplementedError("Erick: implementar en feat/engine-transicion (§3.3)")
