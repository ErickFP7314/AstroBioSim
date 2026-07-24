"""Limpieza, remuestreo y mapeo ambiental — contrato de frontera §3.5 (dueño: Fidel).

STUB de Hito 0. Toma el DataFrame CANÓNICO que devuelven los adaptadores de
`loaders.py` (`t, temperature, a_w, radiation`) y produce la **secuencia de
`CampoAmbiental`** que el orquestador inyecta iteración por iteración en el Modo
Analógico. Ver ADR-0010. Implementación real en `feat/data-loaders`.

Decisiones ya fijadas (NO reabrir sin ADR):

1. **`A_w` se usa tal cual** (0..1). Ya NO se calcula `humidity/100`.
2. **`R` es irradiancia UV en W/m²** (ADR-0014, reemplaza el "proxy de flujo" de
   ADR-0010). Ni flujo solar total ni dosis en Gy: la insolación global es
   mayoritariamente visible e infrarroja y no esteriliza, mientras que el UV sí.
   El mapeo depende del entorno (`mapear_radiacion`):
       - Superficies (Tierra, Marte): `R = radiation × FRACCION_UV`. El factor
         queda **explícito y documentado**, nunca escondido en una constante.
       - Encelado subglacial: `R = 0`. Su columna es IR (calor de la ventila),
         NO UV ni dosis ionizante. Mapear a cero es lo defendible.
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

from astrobiosim.core.environment import FRACCION_UV, CampoAmbiental

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
    """Mapea la columna `radiation` (W/m²) al campo `R` = irradiancia UV.

    Las superficies (Tierra, Marte) convierten la **irradiancia global** a la
    banda UV multiplicando por `FRACCION_UV`; Encelado subglacial se mapea a
    ``0`` porque su columna es IR (calor de la ventila), no UV (ADR-0014).

    El factor de conversión se aplica acá, a la vista, y no dentro de una
    constante por entorno: ADR-0014 lo exige explícito para que el informe pueda
    justificarlo.

    Parameters
    ----------
    radiation : np.ndarray
        Irradiancia solar **global** en W/m² (columna `radiation` del canónico).
    entorno : Entorno
        Entorno análogo que se está simulando.

    Returns
    -------
    np.ndarray
        Irradiancia UV en W/m². Ceros — con la misma forma — para Encelado.
    """
    radiation = np.asarray(radiation, dtype=float)
    if entorno in _ENTORNOS_SIN_RADIACION:
        return np.zeros_like(radiation)
    return radiation * FRACCION_UV


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
