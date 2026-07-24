"""Carga de datos análogos — contrato de frontera §3.5 (dueño: Fidel).

Un adaptador por fuente (Tierra/Marte/Encelado) que aísla el esquema crudo del
CSV y devuelve el DataFrame **canónico**. Cada adaptador cae en un **fallback
sintético** reproducible si el archivo no existe (misma interfaz, mismas
columnas), pensado SOLO para pruebas.

Columnas canónicas EXACTAS:
    "t"            índice temporal (datetime64, sin zona horaria)
    "temperature"  (°C)
    "a_w"          (0..1, provista directamente — ya NO se calcula humidity/100)
    "radiation"    (W/m², irradiancia solar GLOBAL. La conversión a banda UV la
                    hace `resampling.mapear_radiacion` río abajo — ADR-0014.)

`cargar_atacama` añade "temperature_min" y "temperature_max" (amplitud diurna);
`temperature` es la media diaria, (min + max) / 2.

Notas de datos (ver `docs/parametros.md` §4):
- **Atacama** solo publica el MÍNIMO diario de `a_w`; se carga fiel como `a_w`,
  pero es una cota inferior pesimista (deuda #1).
- **Ventilas** trae `Salinidad_psu` (fuera del esquema canónico → se descarta) y
  un hueco real de 8 días (17–24 ago) que se **preserva como NaN**: rellenarlo es
  tarea de `resampling.limpiar_ventilas`, no del loader.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

#: Semilla por defecto del fallback, para que sea reproducible aun sin inyectar
#: un `rng` (regla de oro nº6). Pasá tu propio `Generator` para variar la serie.
SEMILLA_FALLBACK: int = 2025
N_DIAS_DEFECTO: int = 365

COLUMNAS_CANONICAS: tuple[str, ...] = ("t", "temperature", "a_w", "radiation")
COLUMNAS_ATACAMA: tuple[str, ...] = (
    *COLUMNAS_CANONICAS,
    "temperature_min",
    "temperature_max",
)


@dataclass(frozen=True)
class _Stats:
    """(media, sd, mín, máx) reales 2025 de una variable — solo para el fallback."""

    media: float
    sd: float
    minimo: float
    maximo: float


# Estadísticas reales 2025 de cada fuente (de los CSV en `data/processed/`). Se
# usan SOLO en el fallback sintético; los números documentan de dónde salen y por
# qué el fallback "parece" el dato real sin serlo.
_TIERRA: dict[str, _Stats] = {
    "temperature": _Stats(19.85, 9.10, 4.86, 36.45),
    # a_w corregida a suelo a capacidad de campo (constante); la columna original
    # era humedad del aire (media 0.55, sd 0.23) — ver data/README.md.
    "a_w": _Stats(0.99, 0.0, 0.99, 0.99),
    "radiation": _Stats(802.6, 362.5, 85.0, 1352.9),
}
_ATACAMA: dict[str, _Stats] = {
    "temperature_min": _Stats(7.82, 3.49, 0.26, 16.02),
    "temperature_max": _Stats(36.91, 4.49, 19.38, 44.61),
    "a_w": _Stats(0.187, 0.080, 0.020, 0.518),
    "radiation": _Stats(844.2, 210.4, 330.6, 1150.0),
}
_VENTILAS: dict[str, _Stats] = {
    "temperature": _Stats(2.40, 0.028, 2.31, 2.46),
    "a_w": _Stats(0.9817, 0.0, 0.9817, 0.9817),
    "radiation": _Stats(320.3, 0.13, 319.9, 320.6),
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _rng(rng: np.random.Generator | None) -> np.random.Generator:
    return np.random.default_rng(SEMILLA_FALLBACK) if rng is None else rng


def _fechas(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2025-01-01", periods=n, freq="D")


def _parse_fecha(serie: pd.Series) -> pd.Series:
    """Normaliza cualquier formato de fecha a datetime64 naive (sin tz)."""
    return pd.to_datetime(serie, utc=True).dt.tz_localize(None)


def _muestra(rng: np.random.Generator, s: _Stats, n: int) -> np.ndarray:
    """Normal(media, sd) recortada al rango físico observado."""
    return np.clip(rng.normal(s.media, s.sd, n), s.minimo, s.maximo)


def _finalizar(df: pd.DataFrame, columnas: tuple[str, ...]) -> pd.DataFrame:
    """Deja SOLO las columnas canónicas en orden, y valida `a_w` (ignora NaN)."""
    df = df[list(columnas)].reset_index(drop=True)
    if not df["a_w"].dropna().between(0.0, 1.0).all():
        raise ValueError("a_w fuera de [0, 1] tras la carga")
    return df


# --------------------------------------------------------------------------
# Adaptadores por fuente (con fallback automático si el archivo no existe)
# --------------------------------------------------------------------------
def cargar_control_tierra(
    ruta: str, *, rng: np.random.Generator | None = None
) -> pd.DataFrame:
    """Adaptador del control terrestre (Valles de Fresno) → DataFrame canónico.

    Parameters
    ----------
    ruta : str
        Ruta al CSV real. Si no existe, se genera un fallback sintético.
    rng : np.random.Generator, optional
        Generador para el fallback. Solo se usa si `ruta` no existe.
    """
    if not Path(ruta).exists():
        return _sintetico_tierra(rng=rng)
    c = pd.read_csv(ruta)
    df = pd.DataFrame(
        {
            "t": _parse_fecha(c["Fecha"]),
            "temperature": c["Temperatura_C"].astype(float),
            "a_w": c["Actividad_Agua_aw"].astype(float),
            "radiation": c["Radiacion_Solar_W_m2"].astype(float),
        }
    )
    return _finalizar(df, COLUMNAS_CANONICAS)


def cargar_atacama(
    ruta: str, *, rng: np.random.Generator | None = None
) -> pd.DataFrame:
    """Adaptador de Atacama (análogo Marte) → canónico + temperature_min/max.

    `temperature` es la media diaria (min + max) / 2; los extremos se conservan
    para que la UI pueda ofrecer el rango diurno como control (Modo Sandbox).
    """
    if not Path(ruta).exists():
        return _sintetico_atacama(rng=rng)
    c = pd.read_csv(ruta)
    tmin = c["Temp_Minima_Superficie_C"].astype(float)
    tmax = c["Temp_Maxima_Superficie_C"].astype(float)
    df = pd.DataFrame(
        {
            "t": _parse_fecha(c["Fecha"]),
            "temperature": (tmin + tmax) / 2.0,
            "a_w": c["Actividad_Agua_Minima_aw"].astype(float),
            "radiation": c["Radiacion_Solar_Maxima_W_m2"].astype(float),
            "temperature_min": tmin,
            "temperature_max": tmax,
        }
    )
    return _finalizar(df, COLUMNAS_ATACAMA)


def cargar_ventilas(
    ruta: str, *, rng: np.random.Generator | None = None
) -> pd.DataFrame:
    """Adaptador de ventilas hidrotermales (análogo Encelado) → canónico.

    Descarta `Salinidad_psu` (fuera del esquema) y **preserva** los 8 NaN del
    hueco de agosto: imputarlos es tarea de `resampling.limpiar_ventilas`.
    """
    if not Path(ruta).exists():
        return _sintetico_ventilas(rng=rng)
    c = pd.read_csv(ruta)
    df = pd.DataFrame(
        {
            "t": _parse_fecha(c["Fecha"]),
            "temperature": c["Temp_Ventila_C"].astype(float),
            "a_w": c["Actividad_Agua_aw"].astype(float),
            "radiation": c["Radiacion_Infrarroja_W_m2"].astype(float),
        }
    )
    return _finalizar(df, COLUMNAS_CANONICAS)


# --------------------------------------------------------------------------
# Fallbacks sintéticos (misma interfaz canónica; SOLO para pruebas)
# --------------------------------------------------------------------------
def _sintetico_tierra(
    *, rng: np.random.Generator | None = None, n: int = N_DIAS_DEFECTO
) -> pd.DataFrame:
    g = _rng(rng)
    df = pd.DataFrame(
        {
            "t": _fechas(n),
            "temperature": _muestra(g, _TIERRA["temperature"], n),
            "a_w": _muestra(g, _TIERRA["a_w"], n),
            "radiation": _muestra(g, _TIERRA["radiation"], n),
        }
    )
    return _finalizar(df, COLUMNAS_CANONICAS)


def _sintetico_atacama(
    *, rng: np.random.Generator | None = None, n: int = N_DIAS_DEFECTO
) -> pd.DataFrame:
    g = _rng(rng)
    a = _muestra(g, _ATACAMA["temperature_min"], n)
    b = _muestra(g, _ATACAMA["temperature_max"], n)
    tmin = np.minimum(a, b)  # garantiza min <= max aun con muestras independientes
    tmax = np.maximum(a, b)
    df = pd.DataFrame(
        {
            "t": _fechas(n),
            "temperature": (tmin + tmax) / 2.0,
            "a_w": _muestra(g, _ATACAMA["a_w"], n),
            "radiation": _muestra(g, _ATACAMA["radiation"], n),
            "temperature_min": tmin,
            "temperature_max": tmax,
        }
    )
    return _finalizar(df, COLUMNAS_ATACAMA)


def _sintetico_ventilas(
    *, rng: np.random.Generator | None = None, n: int = N_DIAS_DEFECTO
) -> pd.DataFrame:
    g = _rng(rng)
    df = pd.DataFrame(
        {
            "t": _fechas(n),
            "temperature": _muestra(g, _VENTILAS["temperature"], n),
            "a_w": _muestra(g, _VENTILAS["a_w"], n),
            "radiation": _muestra(g, _VENTILAS["radiation"], n),
        }
    )
    return _finalizar(df, COLUMNAS_CANONICAS)
