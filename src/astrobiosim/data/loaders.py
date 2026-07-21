"""Carga de datos análogos — contrato de frontera §3.5 (dueño: Fidel).

STUB de Hito 0. Datos reales 2025: un adaptador por fuente (Tierra/Marte/Encelado)
que aísla el esquema crudo y devuelve el DataFrame CANÓNICO. Ver ADR-0010.
Implementación real en `feat/data-loaders`.

Columnas canónicas EXACTAS que devuelve cada adaptador:
    "t"           índice temporal
    "temperature" (°C)
    "a_w"         (0..1, provista directamente — ya NO se calcula humidity/100)
    "radiation"   (W/m², flujo; proxy operativo de R, no dosis en Gy)
(cargar_atacama expone además "temperature_min"/"temperature_max".)
"""
from __future__ import annotations

import pandas as pd


def cargar_control_tierra(ruta: str) -> pd.DataFrame:
    """Adaptador del control terrestre (Valles de Fresno) → DataFrame canónico."""
    raise NotImplementedError("Fidel: implementar en feat/data-loaders (§3.5, ADR-0010)")


def cargar_atacama(ruta: str) -> pd.DataFrame:
    """Adaptador de Atacama (análogo Marte) → DataFrame canónico (+ temperature_min/max)."""
    raise NotImplementedError("Fidel: implementar en feat/data-loaders (§3.5, ADR-0010)")


def cargar_ventilas(ruta: str) -> pd.DataFrame:
    """Adaptador de ventilas hidrotermales (análogo Encelado) → DataFrame canónico."""
    raise NotImplementedError("Fidel: implementar en feat/data-loaders (§3.5, ADR-0010)")
