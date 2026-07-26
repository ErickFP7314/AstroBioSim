"""Limpieza, remuestreo y mapeo ambiental — contrato de frontera §3.5 (dueño: Fidel).

Toma el DataFrame CANÓNICO que devuelven los adaptadores de `loaders.py`
(`t, temperature, a_w, radiation`) y produce la **secuencia de `CampoAmbiental`**
que el orquestador inyecta iteración por iteración en el Modo Analógico. Ver
ADR-0010 y ADR-0017.

Decisiones ya fijadas (NO reabrir sin ADR):

1. **`A_w` se usa tal cual** (0..1). Ya NO se calcula `humidity/100`.
2. **`R` es irradiancia UV en W/m²** (ADR-0014, reemplaza el "proxy de flujo" de
   ADR-0010). Ni flujo solar total ni dosis en Gy: la insolación global es
   mayoritariamente visible e infrarroja y no esteriliza, mientras que el UV sí.
   El mapeo depende del entorno (`mapear_radiacion`):
       - **Marte**: `R = radiation × FRACCION_UV`. El factor queda **explícito y
         documentado**, nunca escondido en una constante. Es el único entorno
         cuyo subsuelo es parcialmente transparente al UV (se atenúa con la
         profundidad, no se bloquea de entrada).
       - **Tierra y Encelado subglacial: `R = 0`.** En Tierra el subsuelo
         bloquea el UV por completo (`TierraSubsuelo.UV_SUBSUELO`); en Encelado
         la columna es IR (calor de la ventila), NO UV ni dosis ionizante.
         Ninguno de los dos deja pasar radiación al campo, sea cual sea el valor
         de superficie — mapearlos a cero es lo defendible.
3. **Hueco de 8 días en ventilas (2025-08-17 … 2025-08-24):** son NaN reales.
   `limpiar_ventilas` las rellena por **interpolación lineal acotada** (decisión
   2026-07-24), sin inventar valores fuera de rango.

4. **El escalar temporal se reparte en la grilla reusando el modelo de Jose**
   (ADR-0017): `secuencia_campos` no aplana el campo, sino que llama a
   `PlanetaSubsuelo.campo_modulado`, que propaga el dato del día con la física del
   entorno (banda de profundidad en Marte, fumarolas en Encelado). Un campo
   uniforme dejaría el UV de superficie esterilizando toda la grilla.
"""
from __future__ import annotations

from collections.abc import Iterator
from enum import Enum

import numpy as np
import pandas as pd

from astrobiosim.core.environment import (
    FRACCION_UV,
    CampoAmbiental,
    EnceladoSubglacial,
    MarteSubsuelo,
    PlanetaSubsuelo,
    TierraSubsuelo,
)

# Columnas canónicas que consume este módulo (las produce loaders.py).
COLUMNAS_CANONICAS: tuple[str, ...] = ("t", "temperature", "a_w", "radiation")


class Entorno(Enum):
    """Entorno análogo. Determina cómo se mapea `radiation` → `R`."""

    TIERRA = "tierra"      # control (Fresno): subsuelo bloquea el UV -> R = 0
    MARTE = "marte"        # Atacama: R = irradiancia UV de superficie
    ENCELADO = "encelado"  # subglacial: R = 0 (el IR es calor, no dosis)


#: Entornos cuyo campo `R` queda en 0 sin importar la irradiancia de superficie
#: (ADR-0014): Tierra porque el subsuelo bloquea el UV por completo
#: (`TierraSubsuelo.UV_SUBSUELO`), Encelado porque su columna es calor, no UV.
#: Marte es el único cuyo regolito es parcialmente transparente al UV.
_ENTORNOS_SIN_RADIACION: frozenset[Entorno] = frozenset({Entorno.TIERRA, Entorno.ENCELADO})

#: Cada entorno análogo ↔ su modelo espacial (dueño Jose). El Modo Analógico reusa
#: la estructura de estas clases modulándola con la serie temporal (ADR-0017).
_PLANETA: dict[Entorno, type[PlanetaSubsuelo]] = {
    Entorno.TIERRA: TierraSubsuelo,
    Entorno.MARTE: MarteSubsuelo,
    Entorno.ENCELADO: EnceladoSubglacial,
}


def mapear_radiacion(radiation: np.ndarray, entorno: Entorno) -> np.ndarray:
    """Mapea la columna `radiation` (W/m²) al campo `R` = irradiancia UV.

    Solo **Marte** convierte la **irradiancia global** a la banda UV
    multiplicando por `FRACCION_UV`: es el único entorno cuyo regolito es
    parcialmente transparente al UV (se atenúa con la profundidad en vez de
    bloquearlo de entrada). **Tierra y Encelado se mapean a `0`**: en Tierra el
    subsuelo bloquea el UV por completo (mismo hecho físico que
    `TierraSubsuelo.UV_SUBSUELO`), y en Encelado la columna es IR (calor de la
    ventila), no UV (ADR-0014). Coincide con lo que produce
    `PlanetaSubsuelo.campo_modulado` para cada entorno (ADR-0017).

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
        Irradiancia UV en W/m². Ceros — con la misma forma — para Tierra y Encelado.
    """
    radiation = np.asarray(radiation, dtype=float)
    if entorno in _ENTORNOS_SIN_RADIACION:
        return np.zeros_like(radiation)
    return radiation * FRACCION_UV


def limpiar_ventilas(df: pd.DataFrame) -> pd.DataFrame:
    """Rellena el hueco de 8 días (NaN) por **interpolación lineal acotada**.

    Estrategia elegida (2026-07-24): interpolación lineal *interior*
    (`limit_area="inside"`), que rellena los NaN de agosto entre los bordes reales
    conocidos. Como el valor queda entre dos datos reales, nunca se sale de rango
    físico ni se inventan constantes. Solo toca columnas numéricas; `t` queda
    intacta. Encelado es muy estable (~2.4 °C, `a_w`≈0.982), así que el relleno es
    casi indistinguible del dato. No modifica el DataFrame de entrada.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame canónico (posiblemente con NaN interiores).

    Returns
    -------
    pd.DataFrame
        Copia con los NaN interiores interpolados linealmente.
    """
    salida = df.copy()
    columnas = salida.select_dtypes(include="number").columns
    salida[columnas] = salida[columnas].interpolate(
        method="linear", limit_area="inside"
    )
    return salida


def secuencia_campos(
    df: pd.DataFrame,
    entorno: Entorno,
    shape: tuple[int, int],
    rng: np.random.Generator | None = None,
) -> Iterator[CampoAmbiental]:
    """Convierte el DataFrame canónico en una secuencia de `CampoAmbiental`.

    Un `CampoAmbiental` por fila temporal. Cada fila inyecta sus escalares
    (`temperature`, `a_w`, `radiation` global) en el modelo espacial del entorno
    (`PlanetaSubsuelo.campo_modulado`, ADR-0017), que los propaga con su propia
    física: en Marte, la banda de profundidad de T y UV; en Encelado, las
    fumarolas; en Tierra, un campo uniforme. Así el análogo **no** aplana el
    subsuelo (un campo uniforme dejaría el UV de superficie esterilizando toda la
    grilla).

    Se itera sobre las filas temporales (no sobre celdas): la construcción de cada
    campo sigue siendo vectorizada.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame canónico ya limpio (ver `limpiar_ventilas`).
    entorno : Entorno
        Entorno análogo; selecciona el modelo espacial.
    shape : tuple[int, int]
        Dimensiones (M, N) de la grilla.
    rng : np.random.Generator, optional
        Generador inyectado; los entornos con dispersión lo usan.

    Yields
    ------
    CampoAmbiental
        Un campo por fila del DataFrame.
    """
    planeta = _PLANETA[entorno](shape=shape)
    for fila in df.itertuples(index=False):
        yield planeta.campo_modulado(
            temperature=fila.temperature,
            a_w=fila.a_w,
            radiation_global=fila.radiation,
            rng=rng,
        )
