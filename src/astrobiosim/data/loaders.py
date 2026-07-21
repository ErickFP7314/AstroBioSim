"""Carga de datos análogos — contrato de frontera §3.5 (dueño: Fidel).

STUB de Hito 0. El parser real del dataset CRC1211DB (Atacama) y el fallback
sintético van en `feat/data-loaders`.
"""
from __future__ import annotations

import pandas as pd


def cargar_atacama(ruta: str) -> pd.DataFrame:
    """Devuelve el DataFrame canónico con columnas EXACTAS.

    Columnas: ``"t"`` (índice temporal), ``"temperature"`` (°C),
    ``"humidity"`` (0..100 %). El mapeo ``A_w = humidity / 100`` se aplica
    en el remuestreo, no aquí.
    """
    raise NotImplementedError("Fidel: implementar en feat/data-loaders (§3.5)")
