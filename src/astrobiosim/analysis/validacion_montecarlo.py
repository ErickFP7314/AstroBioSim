"""Validación estadística del Montecarlo (dueño: Erick).

Responde los tres criterios de la tarea de validación:

1. **¿Es suficiente el nº de réplicas?** — :func:`estudio_convergencia` corre `n_max`
   réplicas independientes y calcula la **media acumulada** y el **error estándar**
   ``SE = σ/√n`` en función de ``n``. Si la media se estabiliza y el ``SE`` cae por
   debajo de una tolerancia, `n` es suficiente (:meth:`ResultadoConvergencia.n_suficiente`).
2. **No confundir una corrida con la distribución** — se reporta siempre **media ± σ**
   (desviación muestral, ``ddof=1``, la que ya calcula `ResultadoMontecarlo`), más el
   intervalo de confianza del estimador (:meth:`ResultadoConvergencia.intervalo`).
3. **Reproducibilidad** — todo sale de `simular_montecarlo` con semillas explícitas: la
   misma ``semilla_base`` da exactamente la misma traza.

El estudio reusa las **mismas** ``n_max`` réplicas para todos los ``n`` (media acumulada
sobre las primeras ``n``), que es la forma estándar de exhibir la convergencia de un
estimador Montecarlo sin re-correr el ensamble para cada ``n``.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np

from astrobiosim.core.microorganism import Microorganismo
from astrobiosim.engine.transition_rules import ReglaTransicion
from astrobiosim.modes.base import ModoSimulacion
from astrobiosim.simulation import simular_montecarlo

#: Métrica escalar por réplica. Las tres primeras son fracciones al final de la
#: corrida; `persistencia` es binaria (1 si queda población viva > `umbral`, si no 0)
#: — su media es la **probabilidad de persistencia**, el estimador clave del barrido.
Metrica = Literal["viva", "activa", "muerta", "persistencia"]

# fracciones() devuelve columnas [MUERTA, LATENTE, ACTIVA].
_COL = {"muerta": (0,), "activa": (2,), "viva": (1, 2)}
_METRICAS = set(_COL) | {"persistencia"}
#: z de la normal para intervalos de confianza usuales.
_Z = {0.90: 1.6449, 0.95: 1.9600, 0.99: 2.5758}


def _metrica_final(corrida, metrica: Metrica, umbral: float) -> float:
    fr = corrida.fracciones()[-1]
    if metrica == "persistencia":
        return 1.0 if (fr[1] + fr[2]) > umbral else 0.0
    return float(sum(fr[c] for c in _COL[metrica]))


@dataclass(frozen=True)
class ResultadoConvergencia:
    """Traza de convergencia del estimador Montecarlo (por nº de réplicas)."""

    n: np.ndarray                     # (n_max,) = 1, 2, …, n_max
    metrica_por_corrida: np.ndarray   # (n_max,) valor de la métrica en cada réplica (en orden)
    media_acumulada: np.ndarray       # (n_max,) media sobre las primeras n réplicas
    desviacion_acumulada: np.ndarray  # (n_max,) desviación muestral (ddof=1) sobre las primeras n
    error_estandar: np.ndarray        # (n_max,) SE = desviacion/√n
    metrica: str
    semilla_base: int

    @property
    def media_final(self) -> float:
        return float(self.media_acumulada[-1])

    @property
    def desviacion_final(self) -> float:
        return float(self.desviacion_acumulada[-1])

    @property
    def error_final(self) -> float:
        return float(self.error_estandar[-1])

    def intervalo(self, nivel: float = 0.95) -> tuple[np.ndarray, np.ndarray]:
        """Banda del intervalo de confianza del estimador (media ± z·SE) por n."""
        z = _Z.get(nivel)
        if z is None:
            raise ValueError(f"nivel debe ser uno de {list(_Z)}")
        return self.media_acumulada - z * self.error_estandar, self.media_acumulada + z * self.error_estandar

    def n_suficiente(self, error_objetivo: float) -> int:
        """Menor N a partir del cual el error estándar **se mantiene** ≤ ``error_objetivo``.

        Se pide que se mantenga (no solo que lo toque una vez) porque con métricas de
        alta varianza el SE de las primeras réplicas puede caer a 0 por coincidencia;
        el estimador recién es fiable cuando ``SE = σ/√N`` queda bajo el objetivo y no
        vuelve a subir. Devuelve ``n_max`` si no se alcanza en el rango corrido.
        """
        insuficiente = ~(self.error_estandar <= error_objetivo)  # NaN (n=1) cuenta como insuf.
        idx = np.where(insuficiente)[0]
        ultimo = idx[-1]
        if ultimo == len(self.n) - 1:
            return int(self.n[-1])
        return int(self.n[ultimo + 1])


def estudio_convergencia(
    construir_modo: Callable[[np.random.Generator], ModoSimulacion],
    especie: Microorganismo,
    estado_inicial: np.ndarray | Callable[[np.random.Generator], np.ndarray],
    *,
    n_max: int = 200,
    semilla_base: int = 0,
    metrica: Metrica = "viva",
    umbral: float = 0.0,
    construir_eventos: Callable | None = None,
    re_sembrar: bool = True,
    n_iteraciones: int | None = None,
    regla: ReglaTransicion | None = None,
    dt: float = 1.0,
    borde: str = "muerta",
) -> ResultadoConvergencia:
    """Corre ``n_max`` réplicas y traza la convergencia de la media de ``metrica``.

    Parameters
    ----------
    construir_modo, especie, estado_inicial, construir_eventos, re_sembrar,
    n_iteraciones, regla, dt, borde
        Igual que en `simular_montecarlo`. Con ``re_sembrar=True`` (default),
        ``estado_inicial`` debe ser una factory ``construir_estado(rng)`` para que
        cada réplica sea independiente.
    n_max : int
        Nº de réplicas del ensamble.
    semilla_base : int
        Semilla base reproducible.
    metrica : {"viva", "activa", "muerta"}
        Fracción escalar al final de cada corrida sobre la que se estudia la media.

    Returns
    -------
    ResultadoConvergencia
    """
    if metrica not in _METRICAS:
        raise ValueError(f"metrica debe ser una de {sorted(_METRICAS)}")
    res = simular_montecarlo(
        construir_modo,
        especie,
        estado_inicial,
        n_corridas=n_max,
        semilla=semilla_base,
        construir_eventos=construir_eventos,
        re_sembrar=re_sembrar,
        n_iteraciones=n_iteraciones,
        regla=regla,
        dt=dt,
        borde=borde,
        guardar_corridas=True,
    )
    vals = np.array([_metrica_final(c, metrica, umbral) for c in res.corridas], dtype=float)

    n = np.arange(1, n_max + 1)
    suma = np.cumsum(vals)
    suma_sq = np.cumsum(vals**2)
    media = suma / n
    # varianza muestral acumulada: (Σx² − n·media²)/(n−1). Con n=1 es indefinida
    # (una sola muestra no estima dispersión) → NaN, para que no cuente como
    # "convergido" en n_suficiente.
    with np.errstate(invalid="ignore", divide="ignore"):
        var = (suma_sq - n * media**2) / (n - 1)
    var = np.where(n > 1, np.clip(var, 0.0, None), np.nan)
    desv = np.sqrt(var)
    se = desv / np.sqrt(n)

    return ResultadoConvergencia(
        n=n,
        metrica_por_corrida=vals,
        media_acumulada=media,
        desviacion_acumulada=desv,
        error_estandar=se,
        metrica=metrica,
        semilla_base=semilla_base,
    )
