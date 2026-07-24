"""Modo Analógico — corrida guiada por datos reales 2025 (dueño: Fidel).

Envuelve la secuencia de `CampoAmbiental` que produce `data/resampling` y la
expone como un `ModoSimulacion` (`modes/base`), para que el orquestador la itere
igual que a cualquier otro modo (DRY con el futuro Modo Sandbox).

El pipeline es: `loaders.cargar_*` → DataFrame canónico → `limpiar_ventilas` →
`secuencia_campos` (que reusa el modelo espacial de Jose, ADR-0017).
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.data.resampling import Entorno, limpiar_ventilas, secuencia_campos


class ModoAnalogico:
    """Provee un `CampoAmbiental` por fila temporal del dataset real.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame canónico (de `loaders.cargar_*`).
    entorno : Entorno
        Entorno análogo; selecciona el modelo espacial de Jose.
    shape : tuple[int, int]
        Dimensiones (M, N) de la grilla.
    rng : np.random.Generator, optional
        Generador inyectado (regla de oro nº6); los entornos con dispersión lo usan.
    ciclico : bool
        Si es `True`, `campos()` reinicia la serie al terminar (corridas más largas
        que un año reciclan la temporada). Por defecto `False`: la secuencia es
        finita y el orquestador decide la duración.

    Notes
    -----
    El hueco de 8 días de ventilas se rellena al construir (interpolación lineal
    acotada, `limpiar_ventilas`); es inocuo para los datasets sin NaN.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        entorno: Entorno,
        shape: tuple[int, int] = (50, 50),
        *,
        rng: np.random.Generator | None = None,
        ciclico: bool = False,
    ) -> None:
        self._df = limpiar_ventilas(df)
        self._entorno = entorno
        self._shape = shape
        self._rng = rng
        self._ciclico = ciclico

    def __len__(self) -> int:
        return len(self._df)

    def campos(self) -> Iterator[CampoAmbiental]:
        """Itera los `CampoAmbiental` de la corrida (uno por tick)."""
        while True:
            yield from secuencia_campos(
                self._df, self._entorno, self._shape, rng=self._rng
            )
            if not self._ciclico:
                return

    def __iter__(self) -> Iterator[CampoAmbiental]:
        return self.campos()
