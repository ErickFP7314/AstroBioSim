"""Paso del autómata celular — contrato de frontera §3.3 (dueño: Erick).

STUB de Hito 0. El conteo de vecinos de Moore vectorizado y el doble buffer
síncrono van en `feat/engine-transicion`.
"""
from __future__ import annotations

import numpy as np

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import Microorganismo


def paso(
    estado: np.ndarray,
    campo: CampoAmbiental,
    especie: Microorganismo,
    rng: np.random.Generator,
) -> np.ndarray:
    """Un tick del AC (actualización síncrona). Devuelve el nuevo estado (M, N) int8.

    El estado tiene **tres** valores (ADR-0012): `MUERTA=0`, `LATENTE=1`,
    `ACTIVA=2`. Clasificación por celda::

        dentro de especie.condiciones_crecimiento(campo)      -> ACTIVA
        fuera de crecimiento, dentro de condiciones_superv.   -> LATENTE
        fuera de condiciones_supervivencia                    -> MUERTA
        MUERTA                                               -> MUERTA

    `MUERTA` es **absorbente**: su máscara se aplica al final, pisando el resto.
    El conteo de vecinos de Moore para reproducir cuenta **solo** celdas `ACTIVA`,
    y la probabilidad de reproducción sale de la cinética de ADR-0013
    (`transition_rules`), muestreada con el `rng` inyectado.

    Parameters
    ----------
    estado : np.ndarray
        Estado (M, N) int8 en t. No se modifica (doble buffer).
    campo : CampoAmbiental
        Campo ambiental en t. `campo.R` es irradiancia UV (ADR-0014).
    especie : Microorganismo
        Especie simulada; aporta sus dos juegos de umbrales.
    rng : np.random.Generator
        Generador inyectado (regla de oro nº6). Nunca `np.random` global.

    Returns
    -------
    np.ndarray
        Nuevo estado (M, N) int8 con valores en {0, 1, 2}.
    """
    raise NotImplementedError(
        "Erick: implementar en feat/engine-transicion (§3.3, ADR-0012 y ADR-0013)"
    )
