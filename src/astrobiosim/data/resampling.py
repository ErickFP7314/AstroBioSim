"""Limpieza, remuestreo y mapeo ambiental — contrato de frontera §3.5 (dueño: Fidel).

STUB de Hito 0. Toma el DataFrame CANÓNICO que devuelven los adaptadores de
`loaders.py` (`t, temperature, a_w, radiation`) y produce la **secuencia de
`CampoAmbiental`** que el orquestador inyecta iteración por iteración en el Modo
Analógico. Ver ADR-0010. Implementación real en `feat/data-loaders`.

Decisiones ya fijadas (NO reabrir sin ADR):

1. **`A_w` se usa tal cual** (0..1). Ya NO se calcula `humidity/100`.
2. **`R` se alimenta de `radiation` (W/m²)** como *proxy operativo* de flujo, no
   dosis en Gy. El mapeo depende del entorno (`mapear_radiacion`):
       - Superficies (Tierra, Marte): `R = radiation` (radiación solar incidente).
       - Encelado subglacial: `R ≈ 0`. Su columna es IR (calor de la ventila),
         NO dosis ionizante que dañe ADN. Mapear a cero es lo defendible.
3. **Hueco de 8 días en ventilas (2025-08-17 … 2025-08-24):** son NaN reales.
   `limpiar_ventilas` debe **enmascarar o imputar sin inventar** valores fuera de
   rango físico (interpolación acotada o exclusión de esas iteraciones). Nunca
   rellenar con constantes arbitrarias.

El gradiente térmico dentro de la grilla (cómo se reparte un escalar temporal en
las M×N celdas) lo coordina Fidel con Jose; por eso la construcción del
`CampoAmbiental` queda como stub hasta fijar la forma de la grilla (§3.1).
"""
from __future__ import annotations

from collections.abc import Iterator
from enum import Enum

import numpy as np
import pandas as pd

from astrobiosim.core.environment import CampoAmbiental

# Columnas canónicas que consume este módulo (las produce loaders.py).
COLUMNAS_CANONICAS: tuple[str, ...] = ("t", "temperature", "a_w", "radiation")


class Entorno(Enum):
    """Entorno análogo. Determina cómo se mapea `radiation` → `R`."""

    TIERRA = "tierra"      # control (Fresno): R = radiación solar
    MARTE = "marte"        # Atacama: R = radiación solar (superficie)
    ENCELADO = "encelado"  # subglacial: R ≈ 0 (el IR es calor, no dosis)


#: Entornos cuya radiación NO alimenta a `R` (se mapea a 0). Ver ADR-0010.
_ENTORNOS_SIN_RADIACION: frozenset[Entorno] = frozenset({Entorno.ENCELADO})


def mapear_radiacion(radiation: np.ndarray, entorno: Entorno) -> np.ndarray:
    """Mapea la columna `radiation` (W/m²) al campo `R` según el entorno.

    Superficies (Tierra, Marte) usan la radiación tal cual; Encelado subglacial
    se mapea a ``0`` porque su flujo es IR (calor), no dosis ionizante (ADR-0010).

    Parameters
    ----------
    radiation : np.ndarray
        Flujo radiativo en W/m² (columna `radiation` del DataFrame canónico).
    entorno : Entorno
        Entorno análogo que se está simulando.

    Returns
    -------
    np.ndarray
        Valores de `R` (W/m²). Ceros — con la misma forma — para Encelado.
    """
    radiation = np.asarray(radiation, dtype=float)
    if entorno in _ENTORNOS_SIN_RADIACION:
        return np.zeros_like(radiation)
    return radiation


def limpiar_ventilas(df: pd.DataFrame) -> pd.DataFrame:
    """Trata el hueco de 8 días (NaN) de ventilas SIN inventar valores.

    Enmascara o interpola de forma acotada las filas 2025-08-17 … 2025-08-24.
    Fidel decide la estrategia (exclusión vs. interpolación lineal acotada) y la
    justifica; nunca rellenar con constantes arbitrarias.
    """
    raise NotImplementedError("Fidel: implementar en feat/data-loaders (§3.5, ADR-0010)")


def secuencia_campos(
    df: pd.DataFrame, entorno: Entorno, shape: tuple[int, int]
) -> Iterator[CampoAmbiental]:
    """Convierte el DataFrame canónico en una secuencia de `CampoAmbiental`.

    Un `CampoAmbiental` por fila temporal: `A_w` tal cual, `R` vía
    `mapear_radiacion`, y `temperature` distribuida en la grilla `shape` (M, N)
    según el gradiente térmico acordado con Jose (§3.1).
    """
    raise NotImplementedError("Fidel: implementar en feat/data-loaders (§3.5, ADR-0010)")
